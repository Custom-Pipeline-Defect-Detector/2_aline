import json
from typing import Any, Dict

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from app.ollama_client import _chat, _json_or_retry

def _parse_json(content: str) -> Dict[str, Any]:
    """Parse JSON from content that may have noise around it."""
    try:
        return _json_or_retry(content)
    except Exception as e:
        # Return a default response in case of failure
        return {}


def route_document(content: str) -> Dict[str, Any]:
    """Route document using OpenAI API."""
    prompt = f"CONTENT:\n{content[:4000]}\nJSON:"
    messages = [
        {"role": "system", "content": """You are a strict JSON generator.\nClassify the document into one of these doc_type enums:\ninvoice, purchase_order, technical_report, contract, unknown.\n\nReturn ONLY valid JSON with:\n{"document_type": "..."}\n\nIf unsure: document_type="unknown"."""},
        {"role": "user", "content": prompt}
    ]
    try:
        content_response = _chat(messages, temperature=0.2)
        return _json_or_retry(content_response)
    except Exception as e:
        # Return a default response in case of failure
        return {"document_type": "unknown"}


def extract_document(content: str, doc_type: str) -> Dict[str, Any]:
    """Extract document content using OpenAI API."""
    prompt = f"Document type: {doc_type}\nCONTENT:\n{content[:4000]}\nJSON:"
    messages = [
        {"role": "system", "content": """You are a structured data extraction engine.\nExtract from the document below and return ONLY valid JSON.\nThe output MUST match the expected schema for the document type.\nIf a field is missing, use null.\nDo NOT add any explanations, comments, or markdown."""},
        {"role": "user", "content": prompt}
    ]
    try:
        content_response = _chat(messages, temperature=0.2)
        return _json_or_retry(content_response)
    except Exception as e:
        # Return a default response in case of failure
        return {}
