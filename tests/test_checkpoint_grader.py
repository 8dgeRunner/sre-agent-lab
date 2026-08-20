import pytest

from sre_lab.checkpoints import match_checkpoints
from sre_lab.models import AgentConclusion, Evidence
from sre_lab.grader import Rca100Grader


def test_checkpoint_matching_requires_entity_signal_and_value():
    checkpoints = [{
        "source_type": "metric", "target": "payment", "signal": "error_rate",
        "expected": {"comparator": ">=", "value": 0.49},
    }]
    good = Evidence("metric", "payment", "error_rate", 0.51)
    wrong_entity = Evidence("metric", "checkout", "error_rate", 0.51)
    wrong_value = Evidence("metric", "payment", "error_rate", 0.1)
    result = match_checkpoints(checkpoints, [good, wrong_entity, wrong_value])
    assert result.matched_count == 1
    assert result.matched_ids == [good.evidence_id]
    assert result.precision == pytest.approx(1 / 3)


def test_grader_does_not_reward_six_irrelevant_evidence_ids():
    evidence = [Evidence("log", "unrelated", "message", "healthy") for _ in range(6)]
    conclusion = AgentConclusion(
        "payment", "httpError5xx", "guess", ["payment"],
        [item.evidence_id for item in evidence], evidence=evidence,
    )
    truth = {
        "root_cause_entities": ["payment"], "root_cause_types": ["httpError5xx"],
        "causal_targets": ["payment"],
        "checkpoints": [{"source_type": "metric", "target": "payment", "signal": "error_rate",
                         "expected": {"comparator": ">=", "value": 0.49}}],
    }
    score = Rca100Grader().grade(conclusion, truth)
    assert score.process == 0
    assert score.total == 70


def test_grader_reports_evidence_precision_and_recall():
    good = Evidence("metric", "payment", "error_rate", 0.5)
    unrelated = Evidence("log", "other", "message", "noise")
    conclusion = AgentConclusion(
        "payment", "httpError5xx", "supported", ["payment"],
        [good.evidence_id, unrelated.evidence_id], evidence=[good, unrelated],
    )
    truth = {
        "root_cause_entities": ["payment"], "root_cause_types": ["httpError5xx"],
        "causal_targets": ["payment"],
        "checkpoints": [{"source_type": "metric", "target": "payment", "signal": "error_rate",
                         "expected": {"comparator": ">=", "value": 0.49}}],
    }
    score = Rca100Grader().grade(conclusion, truth)
    assert score.evidence_precision == 0.5
    assert score.evidence_recall == 1.0
