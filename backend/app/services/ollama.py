import json
from typing import Any, Dict

import httpx

from app.core.config import settings
from app.core.prompts import EXTRACTOR_PROMPT, ROUTER_PROMPT


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def call_ollama(prompt: str) -> str:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("response", "")


def _call_ollama(prompt: str, content: str) -> Dict[str, Any]:
    output = call_ollama(f"{prompt}\nCONTENT:\n{content}\nJSON:")
    try:
        return _parse_json(output)
    except json.JSONDecodeError:
        correction_prompt = f"Return valid JSON only. Fix formatting issues.\n{prompt}\nCONTENT:\n{content}\nJSON:"
        retry_output = call_ollama(correction_prompt)
        return _parse_json(retry_output)


def route_document(content: str) -> Dict[str, Any]:
    return _call_ollama(ROUTER_PROMPT, content)


def extract_document(content: str, doc_type: str) -> Dict[str, Any]:
    prompt = f"{EXTRACTOR_PROMPT}\nDocument type: {doc_type}"
    return _call_ollama(prompt, content)
