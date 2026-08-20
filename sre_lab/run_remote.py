from __future__ import annotations

import argparse
import os

from .case_store import CaseStore
from .ground_truth import load_ground_truth
from .models import AgentConclusion
from .grader import Rca100Grader
from .remote import HttpTurnTransport, RemoteAgentRunner
from .report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a remote HTTPS Agent against one offline case")
    parser.add_argument("--case", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--secret-env", default="LAB_AGENT_HMAC_SECRET")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    secret = os.environ.get(args.secret_env, "").encode()
    if len(secret) < 16:
        parser.error(f"{args.secret_env} must contain at least 16 bytes")
    result = RemoteAgentRunner(CaseStore(args.case), HttpTurnTransport(args.endpoint), secret).run()
    if not result.answer:
        raise SystemExit(f"Agent run did not complete: {result.status}")
    answer = result.answer
    conclusion = AgentConclusion(
        root_cause_entity=answer["root_cause_entities"][0] if answer["root_cause_entities"] else "",
        fault_type=answer["fault_type"], summary="remote Agent final answer",
        causal_steps=answer["causal_steps"], evidence_ids=answer["evidence_ids"],
        tool_calls=result.metrics.tool_calls, evidence=result.evidence, timeline=result.timeline,
    )
    truth = load_ground_truth(args.ground_truth)
    score = Rca100Grader().grade(conclusion, truth)
    write_report(args.output, conclusion, score, truth)
    print(f"status={result.status} score={score.total} seconds={result.metrics.wall_time_seconds}")


if __name__ == "__main__":
    main()
