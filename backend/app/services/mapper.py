from typing import Any, Dict, List


def _build_evidence(full_text: str, value: str, source: str) -> Dict[str, str]:
    if not value:
        snippet = ""
    else:
        idx = full_text.lower().find(value.lower())
        if idx == -1:
            snippet = value
        else:
            start = max(idx - 60, 0)
            end = min(idx + 60, len(full_text))
            snippet = full_text[start:end]
    return {"snippet": snippet, "location": "text", "source": source}


def map_to_proposals(intermediate: Dict[str, Any], full_text: str, source: str) -> List[Dict[str, Any]]:
    proposals: List[Dict[str, Any]] = []

    for org in intermediate.get("organizations", []):
        if org.get("type") == "customer" and org.get("name"):
            name = org.get("name")
            proposals.append(
                {
                    "proposed_action": "create",
                    "target_module": "crm",
                    "target_table": "customers",
                    "proposed_fields": {"name": name, "aliases": org.get("aliases", [])},
                    "field_confidence": {"name": 0.7, "aliases": 0.5},
                    "evidence": {
                        "name": _build_evidence(full_text, name, source),
                        "aliases": _build_evidence(full_text, name, source),
                    },
                    "questions": {},
                }
            )

    project = intermediate.get("project", {})
    if project.get("project_code") or project.get("name"):
        proposals.append(
            {
                "proposed_action": "create",
                "target_module": "pm",
                "target_table": "projects",
                "proposed_fields": {
                    "project_code": project.get("project_code"),
                    "name": project.get("name") or project.get("project_code") or "New Project",
                },
                "field_confidence": {"project_code": 0.6, "name": 0.6},
                "evidence": {
                    "project_code": _build_evidence(full_text, project.get("project_code") or "", source),
                    "name": _build_evidence(full_text, project.get("name") or "", source),
                },
                "questions": {},
            }
        )

    for action in intermediate.get("actions", []):
        if action.get("task"):
            task = action.get("task")
            proposals.append(
                {
                    "proposed_action": "create",
                    "target_module": "pm",
                    "target_table": "tasks",
                    "proposed_fields": {"title": task, "description": task},
                    "field_confidence": {"title": 0.6, "description": 0.6},
                    "evidence": {
                        "title": _build_evidence(full_text, task, source),
                        "description": _build_evidence(full_text, task, source),
                    },
                    "questions": {},
                }
            )

    for issue in intermediate.get("issues", []):
        if issue.get("description"):
            desc = issue.get("description")
            proposals.append(
                {
                    "proposed_action": "create",
                    "target_module": "quality",
                    "target_table": "issues",
                    "proposed_fields": {"description": desc, "severity": issue.get("severity", "medium")},
                    "field_confidence": {"description": 0.6, "severity": 0.5},
                    "evidence": {
                        "description": _build_evidence(full_text, desc, source),
                        "severity": _build_evidence(full_text, issue.get("severity", "medium"), source),
                    },
                    "questions": {},
                }
            )

    quality = intermediate.get("quality", {})
    ncr = quality.get("ncr", {}) if isinstance(quality, dict) else {}
    if ncr.get("description"):
        desc = ncr.get("description")
        proposals.append(
            {
                "proposed_action": "create",
                "target_module": "quality",
                "target_table": "ncrs",
                "proposed_fields": {
                    "description": desc,
                    "root_cause": ncr.get("root_cause"),
                    "corrective_action": ncr.get("corrective_action"),
                },
                "field_confidence": {"description": 0.7, "root_cause": 0.5, "corrective_action": 0.5},
                "evidence": {
                    "description": _build_evidence(full_text, desc, source),
                    "root_cause": _build_evidence(full_text, ncr.get("root_cause") or "", source),
                    "corrective_action": _build_evidence(full_text, ncr.get("corrective_action") or "", source),
                },
                "questions": {},
            }
        )

    return proposals
