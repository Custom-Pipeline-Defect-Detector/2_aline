from __future__ import annotations
from typing import List

def _snippet(text: str, value: str) -> str:
    if not value:
        return text[:160]
    idx = text.lower().find(value.lower())
    if idx == -1:
        return text[:200]
    start = max(0, idx - 80)
    end = min(len(text), idx + len(value) + 80)
    return text[start:end]

def build_proposals(text: str, router: dict, intermediate: dict) -> List[dict]:
    proposals = []
    doc_type = router.get("doc_type", "unknown")
    entities = router.get("entities", {}) or {}
    customer_name = entities.get("customer_name")
    project_code = entities.get("project_code") or (intermediate.get("project", {}) or {}).get("project_code")

    if customer_name:
        proposals.append({
            "proposed_action":"create",
            "target_module":"crm",
            "target_table":"customers",
            "target_entity_id": None,
            "proposed_fields":{"name": customer_name},
            "field_confidence":{"name": float(router.get("confidence", 0.6) or 0.6)},
            "evidence":{"name":{"snippet": _snippet(text, customer_name), "location":"text", "source":"document"}},
            "questions":[]
        })

    pname = (intermediate.get("project", {}) or {}).get("name")
    if project_code or pname:
        proposed = {"project_code": project_code, "name": pname}
        conf = {"project_code": 0.6 if project_code else 0.4, "name": 0.6 if pname else 0.4}
        ev = {}
        if project_code:
            ev["project_code"] = {"snippet": _snippet(text, project_code), "location":"text", "source":"document"}
        if pname:
            ev["name"] = {"snippet": _snippet(text, pname), "location":"text", "source":"document"}
        proposals.append({
            "proposed_action":"create",
            "target_module":"projects",
            "target_table":"projects",
            "target_entity_id": None,
            "proposed_fields": proposed,
            "field_confidence": conf,
            "evidence": ev,
            "questions":[]
        })

    for a in (intermediate.get("actions") or [])[:50]:
        task = a.get("task")
        if not task:
            continue
        proposals.append({
            "proposed_action":"create",
            "target_module":"projects",
            "target_table":"tasks",
            "target_entity_id": None,
            "proposed_fields":{"title": task, "due_date": a.get("due_date"), "project_code": project_code},
            "field_confidence":{"title":0.75, "due_date":0.55, "project_code":0.6 if project_code else 0.3},
            "evidence":{"title":{"snippet": _snippet(text, task), "location":"text", "source":"document"}},
            "questions":[]
        })

    for i in (intermediate.get("issues") or [])[:50]:
        desc = i.get("description")
        if not desc:
            continue
        sev = i.get("severity") or "medium"
        proposals.append({
            "proposed_action":"create",
            "target_module":"projects",
            "target_table":"issues",
            "target_entity_id": None,
            "proposed_fields":{"description": desc, "severity": sev, "project_code": project_code},
            "field_confidence":{"description":0.75, "severity":0.6, "project_code":0.6 if project_code else 0.3},
            "evidence":{"description":{"snippet": _snippet(text, desc), "location":"text", "source":"document"}},
            "questions":[]
        })

    q = intermediate.get("quality") or {}
    ncr = (q.get("ncr") or {})
    ncr_desc = ncr.get("description")
    if doc_type == "inspection_report_ncr" or ncr_desc:
        if ncr_desc:
            proposals.append({
                "proposed_action":"create",
                "target_module":"quality",
                "target_table":"ncrs",
                "target_entity_id": None,
                "proposed_fields":{
                    "description": ncr_desc,
                    "root_cause": ncr.get("root_cause"),
                    "corrective_action": ncr.get("corrective_action"),
                    "project_code": project_code
                },
                "field_confidence":{
                    "description":0.75,
                    "root_cause":0.55,
                    "corrective_action":0.55,
                    "project_code":0.6 if project_code else 0.3
                },
                "evidence":{"description":{"snippet": _snippet(text, ncr_desc), "location":"text", "source":"document"}},
                "questions":[]
            })

    if not proposals:
        proposals.append({
            "proposed_action":"create",
            "target_module":"documents",
            "target_table":"notes",
            "target_entity_id": None,
            "proposed_fields":{"note":"No structured data found. Review extracted text."},
            "field_confidence":{"note":0.4},
            "evidence":{"note":{"snippet": text[:200], "location":"text", "source":"document"}},
            "questions":[]
        })
    return proposals
