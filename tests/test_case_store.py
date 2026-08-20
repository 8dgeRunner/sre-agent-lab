import json

import duckdb
import pytest

from sre_lab.case_store import CaseStore


def build_case(tmp_path):
    case = tmp_path / "t001"
    case.mkdir()
    (case / "task.json").write_text(json.dumps({
        "task_id": "t001",
        "alert_title": "checkout error count alert",
        "alert_window": {"start": "2026-04-25T05:18:00Z", "end": "2026-04-25T05:28:00Z"},
        "alert_entity": {"entity_name": "checkout::PlaceOrder"},
    }))
    (case / "topology.json").write_text(json.dumps({
        "entities": [
            {"id": "payment-id", "name": "payment", "type": "apm.service"},
            {"id": "checkout-id", "name": "checkout", "type": "apm.service"},
        ],
        "edges": [{"src": "checkout-id", "dst": "payment-id", "relation": "calls"}],
    }))
    con = duckdb.connect()
    con.execute("CREATE TABLE m(time BIGINT, entity_name VARCHAR, metric VARCHAR, value DOUBLE)")
    con.execute("INSERT INTO m VALUES (1, 'payment', 'error_rate', 0.49), (1, 'checkout', 'error_rate', 0.48)")
    con.execute("COPY m TO ? (FORMAT PARQUET)", [str(case / "metrics.parquet")])
    con.execute("CREATE TABLE l(time BIGINT, content VARCHAR, _pod_name_ VARCHAR)")
    con.execute("INSERT INTO l VALUES (1, 'Payment request failed. Invalid token', 'payment-1')")
    con.execute("COPY l TO ? (FORMAT PARQUET)", [str(case / "logs.parquet")])
    con.execute("CREATE TABLE t(traceId VARCHAR, spanName VARCHAR, serviceName VARCHAR, statusCode VARCHAR, statusMessage VARCHAR, startTime BIGINT)")
    con.execute("INSERT INTO t VALUES ('trace-ok', 'Convert', 'currency', '1', '', 1), ('trace-1', 'Charge', 'payment', '2', 'Invalid token', 1)")
    con.execute("COPY t TO ? (FORMAT PARQUET)", [str(case / "traces.parquet")])
    con.execute("CREATE TABLE e(time BIGINT, eventId VARCHAR)")
    con.execute("INSERT INTO e VALUES (1, '{\"reason\":\"Healthy\"}')")
    con.execute("COPY e TO ? (FORMAT PARQUET)", [str(case / "events.parquet")])
    con.execute("CREATE TABLE a(time BIGINT, content VARCHAR)")
    con.execute("INSERT INTO a VALUES (1, 'checkout error alert occurred')")
    con.execute("COPY a TO ? (FORMAT PARQUET)", [str(case / "alerts.parquet")])
    con.close()
    return case


def test_store_queries_six_modalities_and_returns_evidence_ids(tmp_path):
    store = CaseStore(build_case(tmp_path))
    assert store.task["task_id"] == "t001"
    assert store.query_metrics(entity="payment", metric="error_rate")[0].evidence_id
    assert store.search_logs("Invalid token")[0].source == "log"
    assert store.query_traces(service="payment", error_only=True)[0].source == "trace"
    assert store.list_events()[0].source == "event"
    assert store.get_alerts()[0].source == "alert"
    topology = store.get_topology("payment")
    assert topology[0].source == "topology"
    assert "checkout" in topology[0].detail


def test_store_rejects_missing_case_files(tmp_path):
    case = tmp_path / "missing"
    case.mkdir()
    with pytest.raises(FileNotFoundError):
        CaseStore(case)
