import json
from app.services.ollama import _parse_json


def test_parse_json_extracts_payload():
    raw = "noise {\"doc_type\": \"meeting_minutes\", \"entities\": [], \"confidence\": 0.8} trailing"
    parsed = _parse_json(raw)
    assert parsed["doc_type"] == "meeting_minutes"
    assert parsed["confidence"] == 0.8
