from sre_lab.case_store import CaseStore
from sre_lab.remote import RemoteAgentRunner

from test_case_store import build_case


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def send(self, payload, headers):
        self.requests.append((payload, headers))
        return next(self.responses)


def test_remote_runner_executes_allowed_tools_and_returns_final_answer(tmp_path):
    transport = ScriptedTransport([
        {"type": "tool_call", "tool": "query_metrics",
         "arguments": {"entity": "payment", "metric": "error_rate", "limit": 5}},
        {"type": "final_answer", "root_cause_entities": ["payment"],
         "fault_type": "httpError5xx", "causal_steps": ["payment", "checkout"],
         "evidence_ids": [], "remediation_proposal": {"rollback": "remove fault"},
         "usage": {"input_tokens": 100, "output_tokens": 20}},
    ])
    runner = RemoteAgentRunner(CaseStore(build_case(tmp_path)), transport, b"0123456789abcdef")
    result = runner.run()
    assert result.answer["root_cause_entities"] == ["payment"]
    assert result.metrics.tool_calls == 1
    assert result.metrics.turns == 2
    assert result.metrics.usage["self_reported"] is True
    assert transport.requests[1][0]["message"]["type"] == "tool_result"
    assert transport.requests[0][1]["X-Lab-Signature"]


def test_remote_runner_rejects_unknown_tool_without_executing_it(tmp_path):
    transport = ScriptedTransport([
        {"type": "tool_call", "tool": "shell", "arguments": {"cmd": "id"}},
    ])
    runner = RemoteAgentRunner(CaseStore(build_case(tmp_path)), transport, b"0123456789abcdef")
    result = runner.run()
    assert result.answer is None
    assert result.metrics.rejected_calls == 1
    assert result.status == "protocol_error"


def test_remote_runner_stops_at_turn_budget(tmp_path):
    transport = ScriptedTransport([
        {"type": "tool_call", "tool": "get_alerts", "arguments": {}} for _ in range(3)
    ])
    runner = RemoteAgentRunner(
        CaseStore(build_case(tmp_path)), transport, b"0123456789abcdef", max_turns=2
    )
    result = runner.run()
    assert result.status == "turn_limit"
    assert result.metrics.turns == 2
