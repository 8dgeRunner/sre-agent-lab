import pytest

from sre_lab.models import AgentConclusion, Evidence


def test_conclusion_requires_evidence():
    with pytest.raises(ValueError, match="evidence"):
        AgentConclusion(
            root_cause_entity="payment",
            fault_type="httpError5xx",
            summary="Payment fails.",
            causal_steps=[],
            evidence_ids=[],
        )


def test_evidence_has_stable_id():
    first = Evidence("metric", "payment", "error_rate", 0.49, "ratio", 1_000)
    second = Evidence("metric", "payment", "error_rate", 0.49, "ratio", 1_000)
    assert first.evidence_id == second.evidence_id
    assert first.evidence_id.startswith("ev_")

