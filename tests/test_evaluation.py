from sre_lab.evaluation import RunRecord, aggregate_runs


def test_aggregate_reports_macro_accuracy_by_fault_class_without_token_ranking():
    records = [
        RunRecord("a", "httpError5xx", 1.0, 0.8, 1.0, 2.0, 3, 0, {"input_tokens": 100}),
        RunRecord("b", "httpError5xx", 0.0, 1.0, 0.0, 4.0, 5, 1, {"input_tokens": 1}),
        RunRecord("c", "networkLatency", 1.0, 1.0, 1.0, 3.0, 4, 0, {"input_tokens": 900}),
    ]
    report = aggregate_runs(records)
    assert report["overall"]["entity_accuracy"] == 2 / 3
    assert report["by_fault_type"]["httpError5xx"]["runs"] == 2
    assert report["by_fault_type"]["networkLatency"]["entity_accuracy"] == 1.0
    assert report["efficiency"]["wall_time_seconds_mean"] == 3.0
    assert report["safety"]["rejected_calls"] == 1
    assert report["ranking_fields"] == ["entity_accuracy", "fault_accuracy", "process_score"]
    assert "input_tokens" not in report["ranking_fields"]
