import json

from sre_lab.agent import EvidenceRcaAgent
from sre_lab.grader import Rca100Grader
from sre_lab.models import AgentConclusion, Evidence

from test_case_store import build_case


def test_agent_solves_payment_5xx_with_causal_evidence(tmp_path):
    from sre_lab.case_store import CaseStore

    result = EvidenceRcaAgent(CaseStore(build_case(tmp_path))).run()

    assert result.root_cause_entity == "payment"
    assert result.fault_type == "httpError5xx"
    assert len(result.causal_steps) == 3
    assert len(result.evidence_ids) >= 4
    assert result.tool_calls >= 4


def test_agent_ignores_unrelated_historical_oom_event(tmp_path):
    from sre_lab.case_store import CaseStore

    result = EvidenceRcaAgent(CaseStore(build_case(tmp_path))).run()
    assert result.fault_type == "httpError5xx"


def test_rca100_grader_scores_entity_fault_and_process():
    evidence = [
        Evidence("metric", "payment", "error_rate", 0.5),
        Evidence("metric", "checkout", "error_rate", 0.5),
        Evidence("alert", "checkout::PlaceOrder", "alert", "occurred"),
    ]
    conclusion = AgentConclusion(
        root_cause_entity="payment",
        fault_type="httpError5xx",
        summary="Payment 5xx propagates to checkout.",
        causal_steps=["payment", "checkout", "checkout::PlaceOrder"],
        evidence_ids=[item.evidence_id for item in evidence],
        evidence=evidence,
    )
    ground_truth = {
        "root_cause_entities": ["payment"],
        "root_cause_types": ["httpError5xx"],
        "causal_targets": ["payment", "checkout", "checkout::PlaceOrder"],
        "checkpoints": [
            {"source_type": "metric", "target": "payment", "signal": "error_rate",
             "expected": {"comparator": ">=", "value": 0.49}},
            {"source_type": "metric", "target": "checkout", "signal": "error_rate",
             "expected": {"comparator": ">=", "value": 0.49}},
            {"source_type": "alert", "target": "checkout::PlaceOrder", "signal": "alert"},
        ],
    }
    score = Rca100Grader().grade(conclusion, ground_truth)
    assert score.entity == 1
    assert score.fault == 1
    assert score.process == 1
    assert score.total == 100


def test_grader_does_not_reward_unreferenced_reasoning():
    conclusion = AgentConclusion(
        root_cause_entity="payment",
        fault_type="httpError5xx",
        summary="Correct guess without evidence.",
        causal_steps=["payment", "checkout"],
        evidence_ids=["ev_1"],
    )
    ground_truth = {
        "root_cause_entities": ["payment"],
        "root_cause_types": ["httpError5xx"],
        "causal_targets": ["payment", "checkout", "checkout::PlaceOrder"],
        "required_evidence_count": 3,
    }
    score = Rca100Grader().grade(conclusion, ground_truth)
    assert score.entity == 1
    assert score.fault == 1
    assert score.process < 0.5
    assert score.total < 85
