from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class Evidence:
    source: str
    entity: str
    signal: str
    value: Any
    unit: str = ""
    timestamp: Any = None
    detail: str = ""
    evidence_id: str = field(init=False)

    def __post_init__(self) -> None:
        payload = json.dumps(
            [self.source, self.entity, self.signal, self.value, self.unit, self.timestamp, self.detail],
            sort_keys=True,
            default=str,
            ensure_ascii=True,
        )
        object.__setattr__(self, "evidence_id", f"ev_{hashlib.sha256(payload.encode()).hexdigest()[:16]}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentConclusion:
    root_cause_entity: str
    fault_type: str
    summary: str
    causal_steps: list[str]
    evidence_ids: list[str]
    tool_calls: int = 0
    evidence: list[Evidence] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.evidence_ids:
            raise ValueError("conclusion requires evidence")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result


@dataclass(frozen=True)
class RcaScore:
    entity: float
    fault: float
    process: float
    total: float
    chain_coverage: float = 0.0
    evidence_precision: float = 0.0
    evidence_recall: float = 0.0
    matched_checkpoints: int = 0
    total_checkpoints: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
