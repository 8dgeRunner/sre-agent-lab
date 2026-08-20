from __future__ import annotations

from .checkpoints import match_checkpoints
from .models import AgentConclusion, RcaScore


class Rca100Grader:
    def grade(self, conclusion: AgentConclusion, ground_truth: dict) -> RcaScore:
        expected_entities = {str(item).lower() for item in ground_truth.get("root_cause_entities", [])}
        expected_faults = {str(item).lower() for item in ground_truth.get("root_cause_types", [])}
        entity = float(conclusion.root_cause_entity.lower() in expected_entities)
        fault = float(conclusion.fault_type.lower() in expected_faults)

        expected_steps = [str(item).lower() for item in ground_truth.get("causal_targets", [])]
        actual_steps = [str(item).lower() for item in conclusion.causal_steps]
        chain_coverage = (
            self._ordered_coverage(expected_steps, actual_steps)
            if expected_steps else 0.0
        )
        cited = {item.evidence_id: item for item in conclusion.evidence}
        evidence = [cited[item] for item in conclusion.evidence_ids if item in cited]
        checkpoints = ground_truth.get("checkpoints", [])
        match = match_checkpoints(checkpoints, evidence)
        if checkpoints:
            process = chain_coverage * match.recall * match.precision
        else:
            process = 0.0
        total = round((0.4 * entity + 0.3 * fault + 0.3 * process) * 100, 2)
        return RcaScore(
            entity=entity, fault=fault, process=process, total=total,
            chain_coverage=chain_coverage, evidence_precision=match.precision,
            evidence_recall=match.recall, matched_checkpoints=match.matched_count,
            total_checkpoints=len(checkpoints),
        )

    @staticmethod
    def _ordered_coverage(expected: list[str], actual: list[str]) -> float:
        position = 0
        matched = 0
        for step in expected:
            try:
                index = actual.index(step, position)
            except ValueError:
                continue
            matched += 1
            position = index + 1
        return matched / len(expected) if expected else 0.0
