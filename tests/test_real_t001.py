from pathlib import Path

import pytest

from sre_lab.case_store import CaseStore
from sre_lab.ground_truth import load_ground_truth


CASE = Path("data/rca100/t001")
GT = Path("data/rca100/answer_key/t001.gt.json")


pytestmark = pytest.mark.skipif(not CASE.exists(), reason="RCA100 t001 fixture not downloaded")


def test_real_t001_modalities_match_published_ground_truth():
    store = CaseStore(CASE)
    metrics = store.query_metrics("payment", "error_rate", limit=200)
    traces = store.query_traces("payment", error_only=True, limit=5000)
    topology = store.get_topology("payment")
    alerts = store.get_alerts(limit=1)

    assert max(float(item.value) for item in metrics) >= 0.49
    assert any("invalid token" in str(item.value).lower() for item in traces)
    assert "checkout calls payment" in topology[0].detail
    assert "6180" in str(alerts[0].value)


def test_real_ground_truth_loader_extracts_scoring_contract():
    truth = load_ground_truth(GT)
    assert truth["root_cause_entities"] == ["payment"]
    assert truth["root_cause_types"] == ["httpError5xx"]
    assert truth["causal_targets"] == [
        "payment", "checkout", "checkout::/oteldemo.CheckoutService/PlaceOrder"
    ]
    assert truth["required_evidence_count"] == 6
