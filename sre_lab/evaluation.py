from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    fault_type: str
    entity_score: float
    fault_score: float
    process_score: float
    wall_time_seconds: float
    tool_calls: int
    rejected_calls: int
    usage: dict[str, Any]


def _summary(records: list[RunRecord]) -> dict[str, Any]:
    if not records:
        return {"runs": 0, "entity_accuracy": 0.0, "fault_accuracy": 0.0,
                "process_score": 0.0}
    return {
        "runs": len(records),
        "entity_accuracy": mean(item.entity_score for item in records),
        "fault_accuracy": mean(item.fault_score for item in records),
        "process_score": mean(item.process_score for item in records),
    }


def aggregate_runs(records: list[RunRecord]) -> dict[str, Any]:
    groups: dict[str, list[RunRecord]] = {}
    for record in records:
        groups.setdefault(record.fault_type, []).append(record)
    return {
        "overall": _summary(records),
        "by_fault_type": {fault: _summary(items) for fault, items in sorted(groups.items())},
        "efficiency": {
            "wall_time_seconds_mean": mean(item.wall_time_seconds for item in records) if records else 0.0,
            "tool_calls_mean": mean(item.tool_calls for item in records) if records else 0.0,
        },
        "safety": {
            "rejected_calls": sum(item.rejected_calls for item in records),
            "runs_with_rejection": sum(bool(item.rejected_calls) for item in records),
        },
        "usage": {
            "self_reported": True,
            "runs_with_usage": sum(bool(item.usage) for item in records),
            "total_input_tokens_reported": sum(int(item.usage.get("input_tokens", 0)) for item in records),
            "total_output_tokens_reported": sum(int(item.usage.get("output_tokens", 0)) for item in records),
        },
        "ranking_fields": ["entity_accuracy", "fault_accuracy", "process_score"],
    }
