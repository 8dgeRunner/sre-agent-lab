from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from .case_store import CaseStore
from .grader import Rca100Grader
from .ground_truth import load_ground_truth
from .models import AgentConclusion, Evidence
from .protocol import ProtocolError, validate_agent_response
from .report import write_report


class PlatformError(ValueError):
    pass


@dataclass
class RunState:
    run_id: str
    case_id: str
    agent_id: str
    store: CaseStore
    ground_truth: dict[str, Any]
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float = 0.0
    status: str = "running"
    evidence: dict[str, Evidence] = field(default_factory=dict)
    tool_calls: int = 0
    rejected_calls: int = 0
    answer: dict[str, Any] | None = None
    score: dict[str, Any] | None = None
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def metrics(self) -> dict[str, Any]:
        end = self.finished_at or time.monotonic()
        return {
            "wall_time_seconds": round(end - self.started_at, 6),
            "tool_calls": self.tool_calls,
            "rejected_calls": self.rejected_calls,
            "usage": (self.answer or {}).get("usage", {}),
        }


class PlatformApp:
    """Contabo-hosted control-plane core; HTTP transport is in serve.py."""

    ALLOWED_TOOLS = {
        "query_metrics", "search_logs", "query_traces", "list_events", "get_alerts", "get_topology",
    }
    LIMITS = {"query_metrics": 200, "search_logs": 100, "query_traces": 200,
              "list_events": 100, "get_alerts": 100}

    def __init__(self, case_root: str | Path, ground_truth_root: str | Path, *, reports_dir: str | Path = "reports",
                 access_tokens: set[str] | None = None,
                 token_validator: Callable[[str, str | None], bool] | None = None):
        self.case_root = Path(case_root)
        self.ground_truth_root = Path(ground_truth_root)
        self.reports_dir = Path(reports_dir)
        self.access_tokens = access_tokens
        self.token_validator = token_validator
        self._runs: dict[str, RunState] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _required_scope(method: str, path: str) -> str | None:
        if method == "GET" and path == "/v1/cases":
            return "run:create"
        if method == "POST" and path == "/v1/runs":
            return "run:create"
        if path.endswith("/tools") or (method == "GET" and path.startswith("/v1/runs/")):
            return "evidence:read"
        if path.endswith("/answer"):
            return "answer:submit"
        return None

    def _authorize(self, method: str, path: str, headers: dict[str, str]) -> None:
        if self.access_tokens is None and self.token_validator is None:
            return
        token = headers.get("Authorization", "").removeprefix("Bearer ")
        static_ok = self.access_tokens is not None and token in self.access_tokens
        required_scope = self._required_scope(method, path)
        dynamic_ok = self.token_validator is not None and self.token_validator(token, required_scope)
        if static_ok or dynamic_ok:
            return
        if token and required_scope and self.token_validator is not None and self.token_validator(token, None):
            raise PlatformError("forbidden")
        raise PlatformError("unauthorized")

    def _case_dir(self, case_id: str) -> Path:
        path = self.case_root / case_id
        if not path.is_dir() or not (path / "task.json").is_file():
            raise PlatformError("unknown case")
        return path

    def _get_run(self, run_id: str) -> RunState:
        with self._lock:
            if run_id not in self._runs:
                raise PlatformError("unknown run")
            return self._runs[run_id]

    def handle(self, method: str, path: str, body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        self._authorize(method, path, headers or {})
        if method == "GET" and path == "/v1/cases":
            cases = []
            for directory in sorted(self.case_root.glob("t*")):
                task_file = directory / "task.json"
                if task_file.is_file():
                    task = json.loads(task_file.read_text())
                    cases.append({"case_id": directory.name, "title": task.get("alert_title", ""),
                                  "available_modalities": task.get("available_modalities", [])})
            return {"protocol_version": "lab.platform/v1", "cases": cases}
        if method == "POST" and path == "/v1/runs":
            return self.start_run(body)
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["v1", "runs"]:
            run = self._get_run(parts[2])
            if method == "GET":
                return self.result(run)
        if len(parts) == 4 and parts[:2] == ["v1", "runs"]:
            run = self._get_run(parts[2])
            if method == "POST" and parts[3] == "tools":
                return self.tool(run, body)
            if method == "POST" and parts[3] == "answer":
                return self.answer(run, body)
        raise PlatformError("route not found")

    def start_run(self, body: dict[str, Any]) -> dict[str, Any]:
        case_id = body.get("case_id")
        if not isinstance(case_id, str):
            raise PlatformError("case_id is required")
        case_dir = self._case_dir(case_id)
        gt_path = self.ground_truth_root / f"{case_id}.gt.json"
        if not gt_path.is_file():
            raise PlatformError("ground truth unavailable")
        run_id = str(uuid4())
        state = RunState(run_id, case_id, str(body.get("agent_id", "anonymous")),
                         CaseStore(case_dir), load_ground_truth(gt_path))
        with self._lock:
            self._runs[run_id] = state
        return {"protocol_version": "lab.platform/v1", "run_id": run_id, "status": "running",
                "task": state.store.task, "allowed_tools": sorted(self.ALLOWED_TOOLS)}

    def tool(self, run: RunState, body: dict[str, Any]) -> dict[str, Any]:
        with run.lock:
            if run.status != "running":
                raise PlatformError("run is not active")
            name = body.get("tool")
            if name not in self.ALLOWED_TOOLS:
                run.rejected_calls += 1
                raise PlatformError("unknown tool")
            args = dict(body.get("arguments") or {})
            if not isinstance(args, dict):
                run.rejected_calls += 1
                raise PlatformError("arguments must be an object")
            if name == "get_topology" and not args.get("entity"):
                alert_entity = run.store.task.get("alert_entity", {})
                args["entity"] = alert_entity.get("entity_name", "")
                if not args["entity"]:
                    run.rejected_calls += 1
                    raise PlatformError("get_topology requires entity")
            if "limit" in args:
                args["limit"] = min(int(args["limit"]), self.LIMITS.get(name, 100))
            elif name != "get_topology":
                args["limit"] = self.LIMITS.get(name, 100)
            allowed = {
                "query_metrics": {"entity", "metric", "limit"}, "search_logs": {"text", "limit"},
                "query_traces": {"service", "error_only", "limit"}, "list_events": {"limit"},
                "get_alerts": {"limit"}, "get_topology": {"entity"},
            }[name]
            if set(args) - allowed:
                run.rejected_calls += 1
                raise PlatformError("arguments outside allowlist")
            try:
                evidence = getattr(run.store, name)(**args)
            except (TypeError, ValueError) as exc:
                run.rejected_calls += 1
                raise PlatformError(str(exc)) from exc
            run.tool_calls += 1
            for item in evidence:
                run.evidence[item.evidence_id] = item
            return {"run_id": run.run_id, "tool": name,
                    "evidence": [item.to_dict() for item in evidence]}

    def answer(self, run: RunState, body: dict[str, Any]) -> dict[str, Any]:
        with run.lock:
            if run.status != "running":
                raise PlatformError("run is not active")
            try:
                answer = validate_agent_response({"type": "final_answer", **body}, allowed_tools=self.ALLOWED_TOOLS)
            except ProtocolError as exc:
                run.rejected_calls += 1
                raise PlatformError(str(exc)) from exc
            invalid_ids = [item for item in answer["evidence_ids"] if item not in run.evidence]
            conclusion = AgentConclusion(
                root_cause_entity=answer["root_cause_entities"][0] if answer["root_cause_entities"] else "",
                fault_type=answer["fault_type"], summary=answer.get("summary", ""),
                causal_steps=answer["causal_steps"], evidence_ids=answer["evidence_ids"],
                tool_calls=run.tool_calls, evidence=list(run.evidence.values()),
            )
            score = Rca100Grader().grade(conclusion, run.ground_truth)
            run.answer = {**answer, "invalid_evidence_ids": invalid_ids}
            run.score = score.to_dict()
            run.status = "completed"
            run.finished_at = time.monotonic()
            report_path = self.reports_dir / f"{run.run_id}.md"
            write_report(report_path, conclusion, score, run.ground_truth)
            return self.result(run)

    def result(self, run: RunState) -> dict[str, Any]:
        return {"run_id": run.run_id, "case_id": run.case_id, "agent_id": run.agent_id,
                "status": run.status, "score": run.score, "metrics": run.metrics(),
                "answer": run.answer if run.status == "completed" else None}
