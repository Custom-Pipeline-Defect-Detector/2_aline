import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.celery_app import celery
from app.core.config import settings
from app.database import SessionLocal
from app.doc_agent import run_document_agent
from app.extraction.chunker import chunk_text
from app.extraction.schemas import SCHEMA_MAP
from app.extraction.validator import validate_json
from app.services.extraction import extract_text
from app.services.mapper import map_to_proposals
from app.services.ollama import call_ollama

logger = logging.getLogger("extraction")
logger.setLevel(logging.INFO)

MAX_RETRIES = 2


def _write_text_file(doc_id: int, version: int, text: str) -> str:
    base = Path(settings.file_storage_root)
    base.mkdir(parents=True, exist_ok=True)
    text_path = base / f"doc_{doc_id}_v{version}.txt"
    text_path.write_text(text, encoding="utf-8")
    return str(text_path)


def build_extraction_prompt(document_text: str, schema: dict) -> str:
    return f"""
You are a structured data extraction engine.

Extract from the document below and return ONLY valid JSON.
The output MUST match this SCHEMA exactly.
If a field is missing, use null.
Do NOT add any explanations, comments, or markdown.

SCHEMA:
{json.dumps(schema, indent=2)}

DOCUMENT:
{document_text}
""".strip()


def _safe_json_loads(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def classify_document(text: str) -> str:
    prompt = f"""
Classify this document into one of:
- invoice
- purchase_order
- technical_report
- contract
- unknown

Return ONLY valid JSON with:
{{"document_type": "..."}}

DOCUMENT:
{text}
""".strip()

    try:
        response = call_ollama(prompt)
        parsed = _safe_json_loads(response)
    except Exception:
        return "unknown"
    return parsed.get("document_type", "unknown")


def run_extraction(document_text: str, document_type: str) -> dict[str, Any]:
    schema = SCHEMA_MAP.get(document_type)
    if not schema:
        raise Exception(f"No extraction schema for {document_type}")

    for attempt in range(MAX_RETRIES + 1):
        prompt = build_extraction_prompt(document_text, schema)
        response_text = call_ollama(prompt)
        logger.info("Attempt %s, raw AI response: %s", attempt, response_text)

        try:
            parsed = _safe_json_loads(response_text)
        except json.JSONDecodeError:
            if attempt < MAX_RETRIES:
                continue
            raise

        valid, error = validate_json(parsed, schema)
        if valid:
            logger.info("Validated JSON: %s", parsed)
            return parsed
        if attempt == MAX_RETRIES:
            raise Exception(f"Schema validation failed: {error}")

    raise Exception("Extraction failed after retries")


def add_confidence(data: dict[str, Any]) -> dict[str, Any]:
    confidence = {}
    for key, value in data.items():
        confidence[key] = 0.95 if value not in [None, "", []] else 0.2
    data["_confidence"] = confidence
    return data


def _merge_chunk_results(results: list[dict[str, Any]], doc_type: str) -> dict[str, Any]:
    schema = SCHEMA_MAP[doc_type]
    merged: dict[str, Any] = {}
    for field in schema.get("required", []):
        merged[field] = None

    for result in results:
        for key, value in result.items():
            if key not in merged:
                continue
            current = merged.get(key)
            if isinstance(value, list):
                if not isinstance(current, list):
                    current = []
                merged[key] = current + [item for item in value if item not in current]
            elif current in (None, "") and value not in (None, ""):
                merged[key] = value

    for key, value in merged.items():
        if value is None and schema.get("properties", {}).get(key, {}).get("type") == "array":
            merged[key] = []

    return merged


@celery.task(name="extract_and_propose")
def extract_and_propose(doc_version_id: int) -> None:
    db: Session = SessionLocal()
    try:
        doc_version = db.query(models.DocumentVersion).filter_by(id=doc_version_id).first()
        if not doc_version:
            return
        document = db.query(models.Document).filter_by(id=doc_version.doc_id).first()
        if not document:
            return

        file_path = Path(document.storage_path)
        text, _ = extract_text(file_path)
        text_path = _write_text_file(document.id, doc_version.version, text)
        doc_version.extracted_text_path = text_path

        doc_type = classify_document(text[:4000])
        if doc_type not in SCHEMA_MAP:
            doc_type = "unknown"
        logger.info("Document type: %s", doc_type)

        chunk_results = []
        for chunk in chunk_text(text):
            chunk_results.append(run_extraction(chunk, doc_type))

        merged_extraction = _merge_chunk_results(chunk_results, doc_type)
        extractor_json = add_confidence(merged_extraction)

        doc_version.router_json = {"document_type": doc_type}
        doc_version.extractor_json = extractor_json

        document.document_type = doc_type
        document.extracted_fields = extractor_json
        document.classification_confidence = 0.95 if doc_type != "unknown" else 0.4

        proposals = map_to_proposals(extractor_json, text, document.filename)
        for proposal in proposals:
            db.add(
                models.Proposal(
                    doc_version_id=doc_version.id,
                    proposed_action=proposal["proposed_action"],
                    target_module=proposal["target_module"],
                    target_table=proposal["target_table"],
                    proposed_fields=proposal["proposed_fields"],
                    field_confidence=proposal["field_confidence"],
                    evidence=proposal["evidence"],
                    questions=proposal["questions"],
                )
            )
        db.commit()
    finally:
        db.close()


@celery.task(name="process_document")
def process_document(document_id: int) -> None:
    db: Session = SessionLocal()
    try:
        document = db.query(models.Document).filter_by(id=document_id).first()
        if not document:
            return
        if document.processing_status == "processing":
            return
        document.processing_status = "processing"
        document.processing_error = None
        db.commit()
        run_document_agent(document_id)
    finally:
        db.close()
