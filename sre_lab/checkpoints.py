from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Evidence


@dataclass(frozen=True)
class CheckpointMatch:
    matched_ids: list[str] = field(default_factory=list)
    unmatched_checkpoints: int = 0
    invalid_ids: list[str] = field(default_factory=list)
    precision: float = 0.0
    recall: float = 0.0

    @property
    def matched_count(self) -> int:
        return len(self.matched_ids)


def _same_entity(actual: str, expected: str) -> bool:
    a, e = str(actual).lower(), str(expected).lower()
    return a == e or a.startswith(e + "::") or a.startswith(e + "-") or (e in a and "::" not in e)


def _compare(actual: Any, expected: dict[str, Any]) -> bool:
    try:
        left, right = float(actual), float(expected.get("value"))
    except (TypeError, ValueError):
        return str(actual).lower() == str(expected.get("value", "")).lower()
    comparator = expected.get("comparator", "==")
    return {
        ">=": left >= right, ">": left > right, "<=": left <= right,
        "<": left < right, "==": left == right, "=": left == right,
    }.get(comparator, False)


def _matches(checkpoint: dict[str, Any], evidence: Evidence) -> bool:
    source = checkpoint.get("source_type", checkpoint.get("source", ""))
    if source and str(source).lower() not in {evidence.source.lower(), "trace" if evidence.source == "trace" else evidence.source.lower()}:
        return False
    target = checkpoint.get("target") or checkpoint.get("entity")
    if target and not _same_entity(evidence.entity, str(target)):
        return False
    signal = checkpoint.get("signal")
    if signal and signal.lower() not in evidence.signal.lower():
        return False
    expected = checkpoint.get("expected")
    if expected and not _compare(evidence.value, expected):
        return False
    text = checkpoint.get("text") or checkpoint.get("contains")
    return not text or str(text).lower() in str(evidence.value).lower()


def match_checkpoints(checkpoints: list[dict[str, Any]], evidence: list[Evidence]) -> CheckpointMatch:
    matched_ids: list[str] = []
    matched_indexes: set[int] = set()
    for item in evidence:
        for index, checkpoint in enumerate(checkpoints):
            if index not in matched_indexes and _matches(checkpoint, item):
                matched_indexes.add(index)
                matched_ids.append(item.evidence_id)
                break
    valid = len(matched_ids)
    cited = len(evidence)
    total = len(checkpoints)
    invalid = [item.evidence_id for item in evidence if item.evidence_id not in matched_ids]
    return CheckpointMatch(
        matched_ids=matched_ids,
        unmatched_checkpoints=max(total - valid, 0),
        invalid_ids=invalid,
        precision=valid / cited if cited else 0.0,
        recall=valid / total if total else 0.0,
    )
