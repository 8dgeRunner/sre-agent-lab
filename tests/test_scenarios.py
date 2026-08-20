import pytest

from sre_lab.scenario import Scenario, ScenarioError, validate_contract
from sre_lab.models import Evidence


def test_scenario_requires_behavioral_reproduction_and_cleanup():
    scenario = Scenario.from_dict({
        "problem_id": "x", "source_case_id": "t001", "reproduction_level": "behavioral",
        "fault_type": "httpError5xx", "target": "payment", "workload": {"name": "demo"},
        "injector": {"type": "chaos-mesh"}, "steady_state": [], "symptom_contract": [],
        "stop_conditions": [], "cleanup": {"ttl_seconds": 60}, "grading": {},
    })
    assert scenario.injector_type == "chaos-mesh"


def test_scenario_rejects_chaosblade_and_missing_cleanup():
    data = {"problem_id": "x", "source_case_id": "t001", "reproduction_level": "behavioral",
            "fault_type": "x", "target": "x", "workload": {}, "injector": {"type": "chaosblade"},
            "steady_state": [], "symptom_contract": [], "stop_conditions": [],
            "cleanup": {"ttl_seconds": 60}, "grading": {}}
    with pytest.raises(ScenarioError, match="injector"):
        Scenario.from_dict(data)


def test_contract_requires_all_required_evidence():
    contract = [
        {"source_type": "metric", "target": "payment", "signal": "error_rate",
         "expected": {"comparator": ">=", "value": 0.49}},
        {"source_type": "log", "target": "payment", "contains": "invalid token"},
    ]
    evidence = [Evidence("metric", "payment-abc", "error_rate", 0.5),
                Evidence("log", "payment", "message", "Invalid token")]
    result = validate_contract(contract, evidence)
    assert result.passed is True
    assert result.recall == 1.0
