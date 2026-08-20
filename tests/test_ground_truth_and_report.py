import json

from sre_lab.ground_truth import load_ground_truth
from sre_lab.models import AgentConclusion, Evidence, RcaScore
from sre_lab.report import write_report


def test_ground_truth_accepts_structured_entities(tmp_path):
    path = tmp_path / "gt.json"
    path.write_text(json.dumps({
        "root_cause_entities": [{"entity_name": "payment"}],
        "root_cause_types": ["httpError5xx"],
        "raw_ground_truth": json.dumps({"reasoning": {"steps": []}}),
    }))
    assert load_ground_truth(path)["root_cause_entities"] == ["payment"]


def test_report_writes_markdown_and_machine_readable_json(tmp_path):
    evidence = Evidence("trace", "payment", "Charge", "Invalid token")
    conclusion = AgentConclusion(
        "payment", "httpError5xx", "payment failed", ["payment", "checkout"],
        [evidence.evidence_id], evidence=[evidence], timeline=[],
    )
    markdown, json_path = write_report(tmp_path / "report.md", conclusion, RcaScore(1, 1, 1, 100), {})
    text = markdown.read_text()
    assert "payment" in text
    assert "```mermaid" in text
    assert "## Tool Timeline" not in text
    assert "## 关键证据" in text
    assert len(text) < 2500
    assert json.loads(json_path.read_text())["score"]["total"] == 100
