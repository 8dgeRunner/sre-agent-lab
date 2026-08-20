from __future__ import annotations

import argparse

from .agent import EvidenceRcaAgent
from .case_store import CaseStore
from .grader import Rca100Grader
from .ground_truth import load_ground_truth
from .report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the evidence-backed RCA baseline")
    parser.add_argument("--case", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    conclusion = EvidenceRcaAgent(CaseStore(args.case)).run()
    truth = load_ground_truth(args.ground_truth)
    score = Rca100Grader().grade(conclusion, truth)
    markdown_path, json_path = write_report(args.output, conclusion, score, truth)
    print(f"root={conclusion.root_cause_entity} fault={conclusion.fault_type} score={score.total}")
    print(f"reports={markdown_path},{json_path}")


if __name__ == "__main__":
    main()
