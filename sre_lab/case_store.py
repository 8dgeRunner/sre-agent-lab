from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from .models import Evidence


class CaseStore:
    REQUIRED = (
        "task.json",
        "topology.json",
        "metrics.parquet",
        "logs.parquet",
        "traces.parquet",
        "events.parquet",
        "alerts.parquet",
    )

    def __init__(self, case_dir: str | Path):
        self.case_dir = Path(case_dir)
        missing = [name for name in self.REQUIRED if not (self.case_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(f"case is missing required files: {', '.join(missing)}")
        self.task = json.loads((self.case_dir / "task.json").read_text())
        self.topology = json.loads((self.case_dir / "topology.json").read_text())
        self._con = duckdb.connect()
        self._cache: dict[tuple[Any, ...], list[Evidence]] = {}

    def _rows(
        self, filename: str, where: str = "TRUE", params: list[Any] | None = None,
        limit: int = 20, order_by: str = "",
    ):
        path = str(self.case_dir / filename)
        ordering = f" ORDER BY {order_by}" if order_by else ""
        query = f"SELECT * FROM read_parquet(?) WHERE {where}{ordering} LIMIT {int(limit)}"
        cursor = self._con.execute(query, [path, *(params or [])])
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def _columns(self, filename: str) -> set[str]:
        path = str(self.case_dir / filename)
        return {row[0] for row in self._con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [path]).fetchall()}

    @staticmethod
    def _first(row: dict[str, Any], *names: str, default: Any = "") -> Any:
        for name in names:
            if name in row and row[name] is not None:
                return row[name]
        return default

    def query_metrics(self, entity: str | None = None, metric: str | None = None, limit: int = 20) -> list[Evidence]:
        cache_key = ("metrics", entity, metric, limit)
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        cols = self._columns("metrics.parquet")
        clauses, params = [], []
        if entity and "entity_name" in cols:
            clauses.append("lower(entity_name) LIKE ?")
            params.append(f"%{entity.lower()}%")
        if metric and "metric" in cols:
            clauses.append("lower(metric) LIKE ?")
            params.append(f"%{metric.lower()}%")
        rows = self._rows("metrics.parquet", " AND ".join(clauses) or "TRUE", params, limit)
        result = [Evidence(
            "metric",
            str(self._first(row, "entity_name", "service")),
            str(self._first(row, "metric")),
            self._first(row, "value"),
            timestamp=self._first(row, "time"),
            detail=json.dumps(row, default=str, ensure_ascii=True),
        ) for row in rows]
        self._cache[cache_key] = result
        return list(result)

    def search_logs(self, text: str, limit: int = 20) -> list[Evidence]:
        cache_key = ("logs", text.lower(), limit)
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        cols = self._columns("logs.parquet")
        content_col = "content" if "content" in cols else "message"
        rows = self._rows("logs.parquet", f"lower({content_col}) LIKE ?", [f"%{text.lower()}%"], limit)
        result = [Evidence(
            "log",
            str(self._first(row, "_pod_name_", "service", "entity_name")),
            "message",
            str(self._first(row, content_col)),
            timestamp=self._first(row, "time", "timestamp", "_time_"),
        ) for row in rows]
        self._cache[cache_key] = result
        return list(result)

    def query_traces(self, service: str | None = None, error_only: bool = False, limit: int = 20) -> list[Evidence]:
        cache_key = ("traces", service, error_only, limit)
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        cols = self._columns("traces.parquet")
        clauses, params = [], []
        if service and "serviceName" in cols:
            clauses.append("lower(serviceName) LIKE ?")
            params.append(f"%{service.lower()}%")
        if error_only:
            error_parts = []
            if "statusCode" in cols:
                # OTLP status codes are UNSET=0, OK=1, ERROR=2.
                error_parts.append("lower(cast(statusCode as varchar)) IN ('2', 'error')")
            if "statusMessage" in cols:
                error_parts.append("coalesce(statusMessage, '') <> ''")
            if error_parts:
                clauses.append(f"({' OR '.join(error_parts)})")
        order_by = "length(coalesce(events, '')) DESC" if error_only and "events" in cols else ""
        rows = self._rows("traces.parquet", " AND ".join(clauses) or "TRUE", params, limit, order_by)
        result = [Evidence(
            "trace",
            str(self._first(row, "serviceName")),
            str(self._first(row, "spanName")),
            self._trace_message(row),
            timestamp=self._first(row, "startTime"),
            detail=f"trace_id={self._first(row, 'traceId')}; status={self._first(row, 'statusCode')}",
        ) for row in rows]
        self._cache[cache_key] = result
        return list(result)

    @staticmethod
    def _json(value: Any) -> dict[str, Any] | list[Any] | None:
        if not isinstance(value, str):
            return value if isinstance(value, (dict, list)) else None
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, (dict, list)) else None
        except json.JSONDecodeError:
            return None

    def _trace_message(self, row: dict[str, Any]) -> str:
        message = str(self._first(row, "statusMessage", default=""))
        events = self._json(row.get("events"))
        if isinstance(events, list):
            event_text = []
            for event in events:
                if isinstance(event, dict):
                    event_text.append(str(event.get("name", "")))
                    attrs = event.get("attributes", {})
                    if isinstance(attrs, dict):
                        event_text.extend(str(value) for value in attrs.values())
            message = " ".join(part for part in [message, *event_text] if part)
        return message or str(self._first(row, "statusCode"))

    def list_events(self, limit: int = 20) -> list[Evidence]:
        rows = self._rows("events.parquet", limit=limit)
        result = []
        for row in rows:
            payload = self._json(row.get("eventId"))
            payload = payload if isinstance(payload, dict) else {}
            involved = payload.get("involvedObject", {})
            entity = self._first(row, "pod_name", "entity_name") or involved.get("name", "")
            result.append(Evidence(
                "event", str(entity), str(payload.get("reason", self._first(row, "reason", default="k8s_event"))),
                str(payload.get("message", self._first(row, "message", "eventId"))),
                timestamp=payload.get("lastTimestamp", self._first(row, "time", "timestamp")),
                detail=json.dumps(payload, ensure_ascii=True, default=str),
            ))
        return result

    def get_alerts(self, limit: int = 20) -> list[Evidence]:
        rows = self._rows("alerts.parquet", limit=limit)
        return [Evidence(
            "alert",
            str(self._first(row, "entity_name", "service", default=self.task.get("alert_entity", {}).get("entity_name", ""))),
            str(self._first(row, "subject", default="alert")),
            str(self._first(row, "annotations", "content", "data", "status", default=row)),
            timestamp=self._first(row, "time", "timestamp", "time_s"),
            detail=f"status={self._first(row, 'status')}; data={self._first(row, 'data')}",
        ) for row in rows]

    def get_topology(self, entity: str) -> list[Evidence]:
        entities = self.topology.get("entities", [])
        edges = self.topology.get("edges", [])
        names = {item.get("id"): item.get("name", item.get("entity_name", "")) for item in entities}
        matched_ids = {key for key, value in names.items() if entity.lower() in str(value).lower()}
        relations = []
        for edge in edges:
            if edge.get("src") in matched_ids or edge.get("dst") in matched_ids:
                relations.append(f"{names.get(edge.get('src'), edge.get('src'))} {edge.get('relation')} {names.get(edge.get('dst'), edge.get('dst'))}")
        detail = "; ".join(relations) or f"entity={entity}; no adjacent edges"
        return [Evidence("topology", entity, "relations", len(relations), detail=detail)]
