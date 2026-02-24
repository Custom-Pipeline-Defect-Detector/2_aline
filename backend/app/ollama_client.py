import json
import requests
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL

ROUTER_PROMPT = (
  "You are a strict JSON generator.\n"
  "Classify the document into one of these doc_type enums:\n"
  "rfq_quote_po, contract_tech_agreement, bom_parts_list, drawings_revision, meeting_minutes,\n"
  "project_schedule, debug_test_report, inspection_report_ncr, fat_sat_report, delivery_commissioning, unknown.\n\n"
  "Return ONLY valid JSON with:\n"
  "{\n"
  "  \"doc_type\": \"<enum>\",\n"
  "  \"language\": \"zh\"|\"en\"|\"mixed\",\n"
  "  \"entities\": {\n"
  "    \"customer_name\": null|string,\n"
  "    \"project_code\": null|string,\n"
  "    \"po_no\": null|string,\n"
  "    \"quote_no\": null|string,\n"
  "    \"dates\": [],\n"
  "    \"people\": []\n"
  "  },\n"
  "  \"confidence\": 0.0\n"
  "}\n\n"
  "If unsure: doc_type=\"unknown\" and low confidence."
)

EXTRACTOR_PROMPT = (
  "You are a strict JSON generator.\n"
  "Extract the document into the INTERMEDIATE schema EXACTLY:\n"
  "{\n"
  "  \"organizations\": [{\"name\": \"...\", \"type\": \"customer|supplier|internal\", \"aliases\": []}],\n"
  "  \"people\": [{\"name\":\"...\", \"role\": \"optional\"}],\n"
  "  \"references\": [{\"type\":\"project|po|quote|contract\", \"value\":\"...\"}],\n"
  "  \"items\": [{\"name\":\"...\", \"part_no\":\"...\", \"qty\":null, \"unit_price\":null, \"total\":null}],\n"
  "  \"events\": [{\"type\":\"meeting|inspection|test|shipment|fat|sat\", \"date\":null, \"result\":null, \"location\":null}],\n"
  "  \"issues\": [{\"description\":\"...\", \"severity\":\"low|medium|high\", \"owner\":null, \"due_date\":null}],\n"
  "  \"actions\": [{\"task\":\"...\", \"owner\":null, \"due_date\":null}],\n"
  "  \"project\": {\"project_code\":null, \"name\":null, \"milestones\":[]},\n"
  "  \"quality\": {\"inspection_result\":null, \"ncr\": {\"description\":null, \"root_cause\":null, \"corrective_action\":null}}\n"
  "}\n\n"
  "Return ONLY valid JSON. If not found, use null/empty arrays. Do not invent numbers."
)

def _chat(messages, temperature=0.2):
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    return r.json()["message"]["content"]

def _json_or_retry(content: str) -> dict:
    try:
        return json.loads(content)
    except Exception:
        fixed = _chat(
            [{"role": "system", "content": "Fix into valid JSON only. No extra text."},
             {"role": "user", "content": content}],
            temperature=0.0
        )
        return json.loads(fixed)

def run_router(text: str, filename: str, folder_hint: str | None):
    user = f"FILENAME: {filename}\nFOLDER_HINT: {folder_hint or ''}\nTEXT:\n{text[:12000]}"
    content = _chat(
        [{"role":"system","content": ROUTER_PROMPT},
         {"role":"user","content": user}],
        temperature=0.2
    )
    return _json_or_retry(content)

def run_extractor(text: str, doc_type: str):
    user = f"DOC_TYPE: {doc_type}\nTEXT:\n{text[:12000]}"
    content = _chat(
        [{"role":"system","content": EXTRACTOR_PROMPT},
         {"role":"user","content": user}],
        temperature=0.2
    )
    return _json_or_retry(content)
