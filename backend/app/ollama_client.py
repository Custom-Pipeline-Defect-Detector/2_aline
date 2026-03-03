import json
import logging
import requests
from typing import Dict, Any, List, Optional, Iterator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException, Timeout, ConnectionError

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME

# Configure logging
logger = logging.getLogger(__name__)

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
  "  \"organizations\": [{\"name\":\"...\", \"type\":\"customer|supplier|internal\", \"aliases\": []}],\n"
  "  \"people\": [{\"name\":\"...\", \"role\":\"optional\"}],\n"
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

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RequestException, Timeout, ConnectionError))
)
def _make_api_request(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """Make API request with retry logic and proper error handling."""
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out to {url}")
        raise
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to {url}")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {str(e)}")
        raise

def _chat(messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: Optional[int] = None) -> str:
    """Chat with the OpenAI-compatible API with enhanced error handling and retry logic."""
    # Using OpenAI-compatible API
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
        
    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    logger.info(f"Making request to OpenAI-compatible API: {MODEL_NAME}")
    try:
        response_data = _make_api_request(url, headers, payload)
        return response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from API: {response_data}")
        raise ValueError(f"Invalid API response format: {str(e)}")


def _chat_stream(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> Iterator[str]:
    """Stream chat deltas from OpenAI-compatible API."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    logger.info(f"Streaming request to OpenAI-compatible API: {MODEL_NAME}")

    try:
        with requests.post(url, headers=headers, json=payload, timeout=120, stream=True) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                if not line:
                    continue
                if line == "[DONE]":
                    break

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = delta.get("content")
                if text:
                    yield str(text)
    except Exception as exc:
        logger.error(f"Streaming chat failed: {exc}")
        raise

def _json_or_retry(content: str, max_retries: int = 3) -> dict:
    """Parse JSON with retry logic for fixing malformed responses."""
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error: {str(e)}. Attempting to fix...")
        if max_retries <= 0:
            logger.error(f"Failed to parse JSON after retries: {content[:200]}...")
            raise ValueError(f"Unable to parse JSON after multiple attempts: {str(e)}")
            
        # Try to extract JSON from the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            try:
                extracted_json = content[start:end]
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                pass  # Continue to AI fix attempt
        
        # Use AI to fix the JSON
        try:
            fixed = _chat(
                [{"role": "system", "content": "Return only valid JSON. Remove any extra text, explanations, or markdown. Fix any formatting issues."},
                 {"role": "user", "content": content}],
                temperature=0.0
            )
            # Recursively call with reduced retry count
            return _json_or_retry(fixed, max_retries - 1)
        except Exception as fix_error:
            logger.error(f"Failed to fix JSON with AI: {str(fix_error)}")
            raise

def run_router(text: str, filename: str, folder_hint: str | None) -> Dict[str, Any]:
    """Route document with enhanced error handling."""
    try:
        user = f"FILENAME: {filename}\nFOLDER_HINT: {folder_hint or ''}\nTEXT:\n{text[:12000]}"
        content = _chat(
            [{"role":"system","content": ROUTER_PROMPT},
             {"role":"user","content": user}],
            temperature=0.2
        )
        return _json_or_retry(content)
    except Exception as e:
        logger.error(f"Error in run_router: {str(e)}")
        # Return a default response in case of failure
        return {
            "doc_type": "unknown",
            "language": "unknown",
            "entities": {
                "customer_name": None,
                "project_code": None,
                "po_no": None,
                "quote_no": None,
                "dates": [],
                "people": []
            },
            "confidence": 0.0
        }

def run_extractor(text: str, doc_type: str) -> Dict[str, Any]:
    """Extract document content with enhanced error handling."""
    try:
        user = f"DOC_TYPE: {doc_type}\nTEXT:\n{text[:12000]}"
        content = _chat(
            [{"role":"system","content": EXTRACTOR_PROMPT},
             {"role":"user","content": user}],
            temperature=0.2
        )
        return _json_or_retry(content)
    except Exception as e:
        logger.error(f"Error in run_extractor: {str(e)}")
        # Return a default response in case of failure
        return {
            "organizations": [],
            "people": [],
            "references": [],
            "items": [],
            "events": [],
            "issues": [],
            "actions": [],
            "project": {"project_code": None, "name": None, "milestones": []},
            "quality": {"inspection_result": None, "ncr": {"description": None, "root_cause": None, "corrective_action": None}}
        }
