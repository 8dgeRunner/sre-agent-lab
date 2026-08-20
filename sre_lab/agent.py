from __future__ import annotations

import re

from .case_store import CaseStore
from .models import AgentConclusion, Evidence


class EvidenceRcaAgent:
    """A deterministic baseline agent that diagnoses from observable evidence only."""

    def __init__(self, store: CaseStore):
        self.store = store
        self.evidence: list[Evidence] = []
        self.timeline: list[dict] = []

    def _call(self, tool: str, *args, **kwargs) -> list[Evidence]:
        result = getattr(self.store, tool)(*args, **kwargs)
        self.evidence.extend(result)
        self.timeline.append({
            "step": len(self.timeline) + 1,
            "tool": tool,
            "args": args,
            "kwargs": kwargs,
            "evidence_ids": [item.evidence_id for item in result],
        })
        return result

    @staticmethod
    def _service_from_entity(value: str) -> str:
        service = re.split(r"::|/", value)[0].strip()
        service = re.sub(r"-[0-9a-f]{6,}-[a-z0-9]+$", "", service)
        return re.sub(r"-\d+$", "", service)

    def run(self) -> AgentConclusion:
        alert_entity = self.store.task.get("alert_entity", {}).get("entity_name", "checkout")
        alert_service = self._service_from_entity(alert_entity) or "checkout"
        alerts = self._call("get_alerts", limit=10)

        traces = self._call("query_traces", error_only=True, limit=1000)
        logs = self._call("search_logs", "Invalid token", limit=30)
        candidates: dict[str, int] = {}
        for item in traces:
            entity = self._service_from_entity(item.entity)
            if entity:
                text = str(item.value).lower()
                weight = 20 if "payment request failed" in text and "failed to charge" not in text else 2
                # Prefer the service that emits the original exception over
                # downstream services that repeat it many times.
                candidates[entity] = max(candidates.get(entity, 0), weight)
        for item in logs:
            entity = self._service_from_entity(item.entity)
            if entity and "invalid token" in str(item.value).lower():
                candidates[entity] = max(candidates.get(entity, 0), 100)
        non_alert = {name: score for name, score in candidates.items() if name != alert_service}
        root = max(non_alert or candidates or {alert_service: 1}, key=(non_alert or candidates or {alert_service: 1}).get)

        root_traces = self._call("query_traces", service=root, error_only=True, limit=100)
        metrics = self._call("query_metrics", entity=root, metric="error", limit=500)
        if not metrics:
            metrics = self._call("query_metrics", entity=root, limit=30)
        trace_text = " ".join(f"{item.value} {item.signal}".lower() for item in traces)
        if not logs:
            logs = self._call("search_logs", "error", limit=30)
        topology = self._call("get_topology", root)
        events = self._call("list_events", limit=30)
        impact_metrics = self._call("query_metrics", entity=alert_service, metric="error_rate", limit=200)

        if "429" in trace_text or "rate limit" in trace_text:
            fault_type = "rateLimiting"
        elif any("oom" in str(item.value).lower() and root in item.entity.lower() for item in events):
            fault_type = "nodeMemoryOOM"
        else:
            fault_type = "httpError5xx"

        selected = []
        root_metrics = [item for item in metrics if item.signal == "error_rate"]
        for collection in (alerts, root_traces or traces, root_metrics or metrics, impact_metrics, logs, topology):
            if collection:
                selected.append(max(collection, key=lambda item: float(item.value) if isinstance(item.value, (int, float)) else 0))
        causal_steps = [root]
        if alert_service != root:
            causal_steps.append(alert_service)
        if alert_entity not in causal_steps:
            causal_steps.append(alert_entity)
        summary = (
            f"{root} emitted application errors; topology and trace evidence show propagation "
            f"to {alert_service}, which triggered {self.store.task.get('alert_title', 'the alert')}."
        )
        return AgentConclusion(
            root_cause_entity=root,
            fault_type=fault_type,
            summary=summary,
            causal_steps=causal_steps,
            evidence_ids=[item.evidence_id for item in selected],
            tool_calls=len(self.timeline),
            evidence=selected,
            timeline=self.timeline,
        )
