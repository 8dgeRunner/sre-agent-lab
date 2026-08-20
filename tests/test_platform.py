import json
import threading

import pytest

from sre_lab.platform import PlatformApp, PlatformError

from test_case_store import build_case


def make_app(tmp_path):
    case = build_case(tmp_path)
    gt_dir = tmp_path / "answer_key"
    gt_dir.mkdir()
    (gt_dir / "t001.gt.json").write_text(json.dumps({
        "case_id": "t001", "root_cause_entities": ["payment"],
        "root_cause_types": ["httpError5xx"],
        "raw_ground_truth": json.dumps({"reasoning": {"steps": [
            {"target": "payment", "observability": [{"source_type": "metric", "signal": "error_rate",
                "required": True, "expected": {"comparator": ">=", "value": 0.49}}]}
        ]}}),
    }))
    return PlatformApp(tmp_path, gt_dir, reports_dir=tmp_path / "reports")


def test_platform_provides_case_run_tools_and_score(tmp_path):
    app = make_app(tmp_path)
    cases = app.handle("GET", "/v1/cases", {})
    assert cases["cases"][0]["case_id"] == "t001"
    started = app.handle("POST", "/v1/runs", {"case_id": "t001", "agent_id": "alice"})
    run_id = started["run_id"]
    assert "answer_key" not in json.dumps(started)
    evidence = app.handle("POST", f"/v1/runs/{run_id}/tools", {
        "tool": "query_metrics", "arguments": {"entity": "payment", "metric": "error_rate", "limit": 5}
    })
    assert evidence["evidence"]
    answer = app.handle("POST", f"/v1/runs/{run_id}/answer", {
        "root_cause_entities": ["payment"], "fault_type": "httpError5xx",
        "causal_steps": ["payment"], "evidence_ids": [evidence["evidence"][0]["evidence_id"]],
        "remediation_proposal": {},
    })
    assert answer["status"] == "completed"
    assert answer["score"]["total"] == 100.0
    assert app.handle("GET", f"/v1/runs/{run_id}", {})["score"]["total"] == 100.0


def test_topology_defaults_to_alert_entity(tmp_path):
    app = make_app(tmp_path)
    run_id = app.handle("POST", "/v1/runs", {"case_id": "t001"})["run_id"]
    result = app.handle("POST", f"/v1/runs/{run_id}/tools", {
        "tool": "get_topology", "arguments": {}
    })
    assert result["evidence"]


def test_platform_rejects_unknown_tools_and_reuses_run_isolation(tmp_path):
    app = make_app(tmp_path)
    a = app.handle("POST", "/v1/runs", {"case_id": "t001", "agent_id": "a"})["run_id"]
    b = app.handle("POST", "/v1/runs", {"case_id": "t001", "agent_id": "b"})["run_id"]
    with pytest.raises(PlatformError, match="unknown tool"):
        app.handle("POST", f"/v1/runs/{a}/tools", {"tool": "shell", "arguments": {}})
    assert a != b
    assert app.handle("GET", f"/v1/runs/{b}", {})["status"] == "running"


def test_platform_supports_concurrent_runs(tmp_path):
    app = make_app(tmp_path)
    run_ids = [app.handle("POST", "/v1/runs", {"case_id": "t001", "agent_id": str(i)})["run_id"] for i in range(4)]
    errors = []

    def call(run_id):
        try:
            app.handle("POST", f"/v1/runs/{run_id}/tools", {"tool": "get_alerts", "arguments": {}})
        except Exception as exc:  # pragma: no cover - failure path asserted by list
            errors.append(exc)

    threads = [threading.Thread(target=call, args=(run_id,)) for run_id in run_ids]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert errors == []


def test_platform_optional_access_token(tmp_path):
    app = make_app(tmp_path)
    app.access_tokens = {"invite-token"}
    with pytest.raises(PlatformError, match="unauthorized"):
        app.handle("GET", "/v1/cases", {})
    result = app.handle("GET", "/v1/cases", {}, {"Authorization": "Bearer invite-token"})
    assert result["cases"]


def test_platform_requests_route_specific_token_scope(tmp_path):
    requested = []

    def validate(token, scope):
        requested.append((token, scope))
        return token == "scoped-token" and scope == "run:create"

    app = make_app(tmp_path)
    app.token_validator = validate
    assert app.handle("GET", "/v1/cases", {}, {"Authorization": "Bearer scoped-token"})["cases"]
    assert requested == [("scoped-token", "run:create")]
