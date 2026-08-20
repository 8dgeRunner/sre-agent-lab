from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from .case_store import CaseStore
from .models import Evidence
from .protocol import HmacAuthenticator, ProtocolError, validate_agent_response


class TurnTransport(Protocol):
    def send(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]: ...


class HttpTurnTransport:
    def __init__(self, endpoint: str, *, timeout: float = 30.0):
        if not endpoint.startswith("https://"):
            raise ValueError("Agent endpoint must use HTTPS")
        self.endpoint, self.timeout = endpoint, timeout

    def send(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=True).encode()
        request = urllib.request.Request(self.endpoint, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        for key, value in headers.items():
            request.add_header(key, value)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            if response.status != 200:
                raise ProtocolError(f"Agent returned HTTP {response.status}")
            result = json.loads(response.read())
            if not isinstance(result, dict):
                raise ProtocolError("Agent response must be an object")
            return result


@dataclass
class RunMetrics:
    started_at: float
    finished_at: float = 0.0
    turns: int = 0
    tool_calls: int = 0
    rejected_calls: int = 0
    response_bytes: int = 0
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def wall_time_seconds(self) -> float:
        end = self.finished_at or time.monotonic()
        return round(end - self.started_at, 6)


@dataclass
class RemoteRunResult:
    status: str
    answer: dict[str, Any] | None
    metrics: RunMetrics
    timeline: list[dict[str, Any]]
    evidence: list[Evidence] = field(default_factory=list)


class RemoteAgentRunner:
    ALLOWED_TOOLS = {
        "query_metrics", "search_logs", "query_traces", "list_events", "get_alerts", "get_topology",
    }
    LIMITS = {"query_metrics": 200, "search_logs": 100, "query_traces": 200, "list_events": 100, "get_alerts": 100}

    def __init__(
        self, store: CaseStore, transport: TurnTransport, secret: bytes,
        *, run_id: str | None = None, max_turns: int = 50,
    ):
        self.store, self.transport = store, transport
        self.auth = HmacAuthenticator(secret)
        self.run_id, self.max_turns = run_id or str(uuid4()), max_turns
        self.observed: dict[str, Evidence] = {}

    def _task_payload(self) -> dict[str, Any]:
        return {
            "protocol_version": "lab.agent/v1", "run_id": self.run_id, "turn_id": 1,
            "message": {"type": "task", "task": self.store.task,
                         "allowed_tools": sorted(self.ALLOWED_TOOLS)},
        }

    def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.transport.send(payload, self.auth.sign(payload))

    def _tool(self, name: str, arguments: dict[str, Any]) -> list[Evidence]:
        if name not in self.ALLOWED_TOOLS:
            raise ProtocolError("unknown tool")
        args = dict(arguments)
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
            raise ProtocolError("tool arguments outside allowlist")
        if name in {"search_logs", "get_topology"} and not args.get("text", args.get("entity")):
            raise ProtocolError("tool requires a target")
        return getattr(self.store, name)(**args)

    def run(self) -> RemoteRunResult:
        metrics = RunMetrics(started_at=time.monotonic())
        timeline: list[dict[str, Any]] = []
        try:
            response = self._send(self._task_payload())
            for turn in range(1, self.max_turns + 1):
                metrics.turns = turn
                response = validate_agent_response(response, allowed_tools=self.ALLOWED_TOOLS)
                if response["type"] == "final_answer":
                    metrics.usage = dict(response.get("usage", {}))
                    valid_ids = set(self.observed)
                    response["invalid_evidence_ids"] = [item for item in response["evidence_ids"] if item not in valid_ids]
                    metrics.finished_at = time.monotonic()
                    return RemoteRunResult("completed", response, metrics, timeline, list(self.observed.values()))
                try:
                    evidence = self._tool(response["tool"], response.get("arguments", {}))
                except (KeyError, TypeError, ValueError, ProtocolError) as exc:
                    metrics.rejected_calls += 1
                    metrics.finished_at = time.monotonic()
                    timeline.append({"turn": turn, "tool": response.get("tool"), "status": "rejected", "error": str(exc)})
                    return RemoteRunResult("protocol_error", None, metrics, timeline, list(self.observed.values()))
                metrics.tool_calls += 1
                for item in evidence:
                    self.observed[item.evidence_id] = item
                timeline.append({"turn": turn, "tool": response["tool"], "status": "completed",
                                 "evidence_ids": [item.evidence_id for item in evidence]})
                result = {
                    "protocol_version": "lab.agent/v1", "run_id": self.run_id, "turn_id": turn + 1,
                    "message": {"type": "tool_result", "tool": response["tool"],
                                 "result": [item.to_dict() for item in evidence]},
                }
                response = self._send(result)
            metrics.finished_at = time.monotonic()
            return RemoteRunResult("turn_limit", None, metrics, timeline, list(self.observed.values()))
        except (ProtocolError, OSError, ValueError, json.JSONDecodeError) as exc:
            if "unknown tool" in str(exc):
                metrics.rejected_calls += 1
            metrics.finished_at = time.monotonic()
            timeline.append({"status": "error", "error": str(exc)})
            return RemoteRunResult("protocol_error", None, metrics, timeline, list(self.observed.values()))
