from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from typing import Any


class ProtocolError(ValueError):
    pass


class HmacAuthenticator:
    def __init__(self, secret: bytes, *, clock: Callable[[], float] = time.time, max_age: int = 60):
        if len(secret) < 16:
            raise ValueError("HMAC secret must be at least 16 bytes")
        self.secret = secret
        self.clock = clock
        self.max_age = max_age
        self._seen: set[str] = set()

    @staticmethod
    def _canonical(body: dict[str, Any]) -> bytes:
        return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

    def sign(self, body: dict[str, Any], *, nonce: str | None = None, timestamp: float | None = None) -> dict[str, str]:
        nonce = nonce or secrets.token_urlsafe(18)
        timestamp = self.clock() if timestamp is None else timestamp
        digest = hashlib.sha256(self._canonical(body)).hexdigest()
        message = f"{timestamp:.6f}.{nonce}.{digest}".encode()
        signature = hmac.new(self.secret, message, hashlib.sha256).digest()
        return {
            "X-Lab-Timestamp": f"{timestamp:.6f}", "X-Lab-Nonce": nonce,
            "X-Lab-Signature": base64.b64encode(signature).decode("ascii"),
        }

    def verify(self, body: dict[str, Any], headers: dict[str, str]) -> None:
        try:
            timestamp = float(headers["X-Lab-Timestamp"])
            nonce = headers["X-Lab-Nonce"]
            supplied = base64.b64decode(headers["X-Lab-Signature"], validate=True)
        except (KeyError, ValueError, base64.binascii.Error) as exc:
            raise ProtocolError("invalid signature headers") from exc
        if abs(self.clock() - timestamp) > self.max_age:
            raise ProtocolError("timestamp outside allowed window")
        if nonce in self._seen:
            raise ProtocolError("replay nonce")
        digest = hashlib.sha256(self._canonical(body)).hexdigest()
        expected = hmac.new(self.secret, f"{timestamp:.6f}.{nonce}.{digest}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            raise ProtocolError("invalid signature")
        self._seen.add(nonce)


def validate_agent_response(response: dict[str, Any], *, allowed_tools: set[str], max_bytes: int = 256_000) -> dict[str, Any]:
    if len(json.dumps(response, ensure_ascii=True).encode()) > max_bytes:
        raise ProtocolError("response exceeds size limit")
    response_type = response.get("type")
    if response_type == "tool_call":
        tool = response.get("tool")
        if not isinstance(tool, str) or tool not in allowed_tools:
            raise ProtocolError("unknown tool")
        if not isinstance(response.get("arguments", {}), dict):
            raise ProtocolError("tool arguments must be an object")
    elif response_type == "final_answer":
        for field in ("root_cause_entities", "fault_type", "causal_steps", "evidence_ids"):
            if field not in response:
                raise ProtocolError(f"missing final answer field: {field}")
        if not isinstance(response["root_cause_entities"], list) or not isinstance(response["evidence_ids"], list):
            raise ProtocolError("final answer list fields are invalid")
        usage = response.get("usage")
        if usage is not None:
            if not isinstance(usage, dict):
                raise ProtocolError("usage must be an object")
            response["usage"] = {**usage, "self_reported": True}
    else:
        raise ProtocolError("response type must be tool_call or final_answer")
    return response
