from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .checkpoints import match_checkpoints
from .models import Evidence


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Scenario:
    problem_id: str
    source_case_id: str
    reproduction_level: str
    fault_type: str
    target: str
    workload: dict[str, Any]
    injector: dict[str, Any]
    steady_state: list[dict[str, Any]]
    symptom_contract: list[dict[str, Any]]
    stop_conditions: list[dict[str, Any]]
    cleanup: dict[str, Any]
    grading: dict[str, Any]

    @property
    def injector_type(self) -> str:
        return str(self.injector.get("type", ""))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        required = ("problem_id", "source_case_id", "reproduction_level", "fault_type", "target",
                    "workload", "injector", "steady_state", "symptom_contract", "stop_conditions",
                    "cleanup", "grading")
        missing = [key for key in required if key not in data]
        if missing:
            raise ScenarioError(f"missing fields: {', '.join(missing)}")
        if data["reproduction_level"] != "behavioral":
            raise ScenarioError("reproduction_level must be behavioral")
        if data["injector"].get("type") not in {"chaos-mesh", "kubernetes-api", "fault-service", "synthetic-database"}:
            raise ScenarioError("injector type is not allowed")
        cleanup = data["cleanup"]
        if not isinstance(cleanup, dict) or int(cleanup.get("ttl_seconds", 0)) <= 0:
            raise ScenarioError("cleanup.ttl_seconds must be positive")
        return cls(**{key: data[key] for key in required})


@dataclass(frozen=True)
class ContractResult:
    passed: bool
    matched: int
    total: int
    precision: float
    recall: float


def validate_contract(contract: list[dict[str, Any]], evidence: list[Evidence]) -> ContractResult:
    match = match_checkpoints(contract, evidence)
    return ContractResult(
        passed=match.recall == 1.0 and match.precision == 1.0,
        matched=match.matched_count, total=len(contract),
        precision=match.precision, recall=match.recall,
    )
