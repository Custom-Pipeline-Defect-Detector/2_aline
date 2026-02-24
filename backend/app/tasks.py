from pathlib import Path
from sqlalchemy.orm import Session
from app.celery_app import celery
from app.database import SessionLocal
from app import models
from app.services.extraction import extract_text
from app.services.ollama import route_document, extract_document
from app.services.mapper import map_to_proposals
from app.doc_agent import run_document_agent
from app.core.config import settings


def _write_text_file(doc_id: int, version: int, text: str) -> str:
    base = Path(settings.file_storage_root)
    base.mkdir(parents=True, exist_ok=True)
    text_path = base / f"doc_{doc_id}_v{version}.txt"
    text_path.write_text(text, encoding="utf-8")
    return str(text_path)


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

        router_json = route_document(text[:6000])
        doc_version.router_json = router_json
        doc_type = router_json.get("doc_type", "unknown")

        extractor_json = extract_document(text[:8000], doc_type)
        doc_version.extractor_json = extractor_json

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
