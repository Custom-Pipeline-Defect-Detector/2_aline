from pathlib import Path
from app.services.mapper import map_to_proposals


def test_map_to_proposals_creates_core_items():
    fixture = Path(__file__).parent / "fixtures" / "sample_meeting.txt"
    text = fixture.read_text(encoding="utf-8")
    intermediate = {
        "organizations": [{"name": "Nanjing Aline Automation Company", "type": "customer", "aliases": []}],
        "people": [],
        "references": [],
        "items": [],
        "events": [],
        "issues": [{"description": "Motor overheating during test.", "severity": "high", "owner": None, "due_date": None}],
        "actions": [{"task": "Prepare wiring diagram by next week.", "owner": None, "due_date": None}],
        "project": {"project_code": "AL-001", "name": "Aline Project", "milestones": []},
        "quality": {"inspection_result": None, "ncr": {"description": "Paint defect on panel.", "root_cause": None, "corrective_action": None}},
    }

    proposals = map_to_proposals(intermediate, text, "sample_meeting.txt")
    targets = {p["target_table"] for p in proposals}
    assert "customers" in targets
    assert "projects" in targets
    assert "tasks" in targets
    assert "issues" in targets
    assert "ncrs" in targets
