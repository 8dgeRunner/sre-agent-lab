import json
import time

import pytest

from sre_lab.protocol import HmacAuthenticator, ProtocolError, validate_agent_response


def test_hmac_round_trip_and_replay_protection():
    auth = HmacAuthenticator(b"test-secret-123456", clock=lambda: 1000.0)
    body = {"protocol_version": "lab.agent/v1", "run_id": "r1", "turn_id": 1}
    headers = auth.sign(body, nonce="n1", timestamp=1000.0)
    auth.verify(body, headers)
    with pytest.raises(ProtocolError, match="replay"):
        auth.verify(body, headers)


def test_hmac_rejects_tampered_body_and_expired_request():
    auth = HmacAuthenticator(b"test-secret-123456", clock=lambda: 2000.0, max_age=30)
    body = {"run_id": "r1"}
    headers = auth.sign(body, nonce="n1", timestamp=2000.0)
    with pytest.raises(ProtocolError, match="signature"):
        auth.verify({"run_id": "tampered"}, headers)
    old = auth.sign(body, nonce="n2", timestamp=1900.0)
    with pytest.raises(ProtocolError, match="timestamp"):
        auth.verify(body, old)


def test_response_schema_allows_final_answer_and_rejects_unknown_tool():
    valid = {
        "type": "final_answer", "root_cause_entities": ["payment"],
        "fault_type": "httpError5xx", "causal_steps": ["payment"],
        "evidence_ids": ["ev_1"], "remediation_proposal": {},
    }
    assert validate_agent_response(valid, allowed_tools={"query_metrics"})["type"] == "final_answer"
    with pytest.raises(ProtocolError, match="unknown tool"):
        validate_agent_response({"type": "tool_call", "tool": "shell", "arguments": {}},
                                allowed_tools={"query_metrics"})


def test_token_usage_is_optional_and_self_reported():
    response = {"type": "final_answer", "root_cause_entities": ["x"],
                "fault_type": "y", "causal_steps": [], "evidence_ids": [],
                "usage": {"input_tokens": 10, "output_tokens": 4, "provider": "local"}}
    assert validate_agent_response(response, allowed_tools=set())["usage"]["self_reported"] is True
