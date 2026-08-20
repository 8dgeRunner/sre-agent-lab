from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_ground_truth(path: str | Path) -> dict[str, Any]:
    document = json.loads(Path(path).read_text())
    raw = document.get("raw_ground_truth", {})
    if isinstance(raw, str):
        raw = json.loads(raw)
    steps = [step for step in raw.get("reasoning", {}).get("steps", []) if step.get("required", True)]
    entities = document.get("root_cause_entities", [])
    entity_names = [item.get("entity_name", "") if isinstance(item, dict) else str(item) for item in entities]
    fault_types = document.get("root_cause_types") or raw.get("metadata", {}).get("root_cause_types", [])
    required_evidence = sum(
        1 for step in steps for item in step.get("observability", []) if item.get("required", True)
    )
    checkpoints = []
    for step in steps:
        for item in step.get("observability", []):
            if item.get("required", True):
                checkpoints.append({**item, "target": step.get("target", "")})
    return {
        "case_id": document.get("case_id"),
        "root_cause_entities": entity_names,
        "root_cause_types": fault_types,
        "causal_targets": [step.get("target", "") for step in steps],
        "required_evidence_count": required_evidence,
        "checkpoints": checkpoints,
        "expected_conclusion": raw.get("outcome", {}).get("expected_conclusion", ""),
    }
