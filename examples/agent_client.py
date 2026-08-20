from __future__ import annotations

import argparse
import json
import os
import urllib.request
from typing import Any


class SreLabClient:
    """Small dependency-free client for an Agent running outside the lab."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.token}")
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    def cases(self) -> dict[str, Any]:
        return self.request("GET", "/v1/cases")

    def start(self, case_id: str, agent_id: str) -> dict[str, Any]:
        return self.request("POST", "/v1/runs", {"case_id": case_id, "agent_id": agent_id})

    def tool(self, run_id: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/v1/runs/{run_id}/tools", {"tool": tool, "arguments": arguments})

    def answer(self, run_id: str, answer: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/v1/runs/{run_id}/answer", answer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal external Agent against SRE Lab")
    parser.add_argument("--base-url", default="https://sre-lab.8dgerunner.xyz")
    parser.add_argument("--case", default="t001")
    parser.add_argument("--agent-id", default="example-agent")
    args = parser.parse_args()
    token = os.environ.get("SRE_LAB_TOKEN")
    if not token:
        parser.error("set SRE_LAB_TOKEN to the participant API token")

    client = SreLabClient(args.base_url, token)
    run = client.start(args.case, args.agent_id)
    run_id = run["run_id"]
    evidence: list[dict[str, Any]] = []
    for tool, arguments in (
        ("get_alerts", {"limit": 10}),
        ("get_topology", {}),
        ("query_traces", {"service": "payment", "error_only": True, "limit": 20}),
        ("search_logs", {"text": "Invalid token", "limit": 20}),
    ):
        evidence.extend(client.tool(run_id, tool, arguments)["evidence"])

    # Replace this deterministic baseline with the colleague's own LLM/Agent decision.
    result = client.answer(run_id, {
        "root_cause_entities": ["payment"],
        "fault_type": "httpError5xx",
        "causal_steps": ["payment", "checkout", "checkout::/oteldemo.CheckoutService/PlaceOrder"],
        "evidence_ids": [item["evidence_id"] for item in evidence[:20]],
        "summary": "payment returned 5xx and propagated to checkout",
        "remediation_proposal": {},
    })
    print(json.dumps({"run_id": run_id, "status": result["status"], "score": result["score"]}, indent=2))


if __name__ == "__main__":
    main()
