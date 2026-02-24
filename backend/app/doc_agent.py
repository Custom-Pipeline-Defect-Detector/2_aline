import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database import SessionLocal
from app import models
from app.services.extraction import extract_text
from app.agent_tools import run_tool, TOOL_REGISTRY


DOCUMENT_TAXONOMY = [
    "contract",
    "nda",
    "invoice",
    "purchase_order",
    "proposal",
    "sow_statement_of_work",
    "drawing",
    "spec",
    "report",
    "email_like",
    "other",
]


def _parse_json(text: str) -> Dict[str, Any]:
    """
    Robustly parse the FIRST JSON object found in text.
    Handles extra leading/trailing junk and multiple JSON objects.
    """
    text = (text or "").strip()

    decoder = json.JSONDecoder()

    # 1) Try direct parse first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
        return {"final": obj}
    except json.JSONDecodeError:
        pass

    # 2) Find first "{" and raw-decode from there
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    # Skip forward until we can decode
    for i in range(start, len(text)):
        if text[i] != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
            return {"final": obj}
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Could not decode JSON object", text, start)



def _call_ollama(prompt: str, model: str) -> Dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    with httpx.Client(timeout=180.0) as client:
        response = client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        output = data.get("response", "")
    return _parse_json(output)


def _tool_manifest() -> str:
    lines = []
    for name, (model, _) in TOOL_REGISTRY.items():
        lines.append(f"- {name}: args schema {model.model_json_schema()}")
    return "\n".join(lines)


def run_document_agent(document_id: int, model: str = "gpt-oss:20b", prompt_version: str = "v1") -> None:
    db: Session = SessionLocal()
    agent_run = None
    document = None
    try:
        document = db.query(models.Document).filter_by(id=document_id).first()
        if not document:
            return
        text, _ = extract_text(Path(document.storage_path))
        document.extracted_text = text
        db.commit()

        agent_run = models.AgentRun(document_id=document.id, model=model, prompt_version=prompt_version)
        db.add(agent_run)
        db.commit()
        db.refresh(agent_run)

        tool_calls: List[Dict[str, Any]] = []
        final_result: Dict[str, Any] | None = None
        context_snippet = text[:8000]
        system_prompt = (
            "You are an offline document automation agent. "
            "Classify documents into one of the taxonomy values and extract structured fields. "
            "Use tools to search for existing customers/projects before creating new ones. "
            "If a similar name exists, update that record and add the new name as an alias. "
            "Link the document to the best matching customer/project when possible. "
            "You must use the provided tools to take actions. "
            "Respond only with JSON. "
            "To call a tool, respond with: {\"tool\": \"name\", \"args\": {...}}. "
            "When done, respond with: {\"final\": {\"document_type\": \"...\", \"confidence\": 0.0-1.0, "
            "\"extracted_fields\": {...}, \"actions_taken\": [...], \"agent_summary\": \"...\", "
            "\"needs_review_reason\": \"...\"}}"
        )
        tool_manifest = _tool_manifest()

        for _ in range(10):
            history = json.dumps(tool_calls[-6:], default=str)
            prompt = (
                f"{system_prompt}\n"
                f"Document taxonomy: {DOCUMENT_TAXONOMY}\n"
                f"Tools:\n{tool_manifest}\n"
                f"Document context:\nFilename: {document.filename}\n"
                f"Content snippet:\n{context_snippet}\n"
                f"Recent tool calls/results:\n{history}\n"
                "JSON:"
            )
            response = _call_ollama(prompt, model)
            if "tool" in response:
                name = response.get("tool")
                args = response.get("args", {})
                result = run_tool(name, args)
                tool_calls.append({"tool": name, "args": args, "result": result.model_dump()})
                continue
            if "final" in response:
                final_result = response["final"]
                break
            final_result = response
            break

        final_result = final_result or {}
        document_type = final_result.get("document_type") or "other"
        confidence = final_result.get("confidence")
        extracted_fields = final_result.get("extracted_fields") or {}
        agent_summary = final_result.get("agent_summary")

        run_tool(
            "set_document_classification",
            {
                "document_id": document.id,
                "document_type": document_type,
                "confidence": confidence,
                "extracted_fields_json": extracted_fields,
                "agent_summary": agent_summary,
            },
        )

        needs_review = confidence is None or confidence < 0.75 or not extracted_fields
        if needs_review:
            reason = final_result.get("needs_review_reason") or "Low confidence or missing required fields."
            role = "Sales" if document_type in {"proposal", "contract", "invoice", "purchase_order", "sow_statement_of_work"} else "Admin"
            run_tool(
                "create_notification",
                {
                    "message": f"Document {document.filename} needs review: {reason}",
                    "role": role,
                    "entity_table": "documents",
                    "entity_id": document.id,
                    "type": "needs_review",
                },
            )
            if document.project_id:
                run_tool(
                    "create_task",
                    {
                        "project_id": document.project_id,
                        "title": f"Review document {document.filename}",
                        "priority": "high",
                        "type": "doc",
                    },
                )

        run_tool(
            "append_audit_event",
            {
                "entity_table": "documents",
                "entity_id": document.id,
                "action": "classified",
                "payload_json": {
                    "document_type": document_type,
                    "confidence": confidence,
                    "needs_review": needs_review,
                },
            },
        )

        document.processing_status = "done"
        document.needs_review = needs_review
        document.last_processed_at = datetime.utcnow()
        document.processing_error = None
        db.commit()

        agent_run.tool_calls_json = tool_calls
        agent_run.final_result_json = final_result
        agent_run.ended_at = datetime.utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001
        if document:
            document.processing_status = "failed"
            document.processing_error = str(exc)
            db.commit()
        if agent_run:
            agent_run.error = str(exc)
            agent_run.ended_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()
