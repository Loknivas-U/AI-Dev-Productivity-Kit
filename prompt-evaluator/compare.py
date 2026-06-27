#!/usr/bin/env python3
"""Compare a candidate prompt evaluation report against production baseline scores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_PATH = "compare_report.json"
VALID_PROMPT_TYPES = ("pr_review", "test_gap")
ROOT_DIR = Path(__file__).resolve().parents[1]
SCORES_PATH = ROOT_DIR / "prompt-library" / "scores" / "eval_results.json"
METRIC_KEYS = ("precision", "recall", "false_positive_rate", "specificity", "consistency")
PROMPT_IDS = {
    "pr_review": "pr_review_v1",
    "test_gap": "test_gap_v1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare a candidate prompt against production.")
    parser.add_argument(
        "--candidate-report",
        required=True,
        help="Path to candidate eval_report.json.",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=VALID_PROMPT_TYPES,
        help="Prompt type to compare.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to write the comparison report. Defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    return parser.parse_args()


def read_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Unable to read {label} at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {label} at {path}: {exc}") from exc


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to write comparison report at {path}: {exc}") from exc


def find_production_prompt(scores: dict[str, Any], prompt_type: str) -> dict[str, Any]:
    expected_id = PROMPT_IDS[prompt_type]
    production_entries = [
        prompt
        for prompt in scores.get("prompts", [])
        if prompt.get("id") == expected_id and prompt.get("status") == "production"
    ]
    if not production_entries:
        production_entries = [
            prompt
            for prompt in scores.get("prompts", [])
            if prompt.get("id", "").startswith(prompt_type) and prompt.get("status") == "production"
        ]
    if not production_entries:
        raise RuntimeError(f"No production score found for prompt type {prompt_type}.")
    return production_entries[0]


def metric_value(metrics: dict[str, Any], metric: str, fallback: Any = None) -> float:
    value = metrics.get(metric, fallback)
    if value is None:
        return 0.0
    return float(value)


def build_verdict(candidate_score: float, production_score: float) -> str:
    if candidate_score > production_score + 0.005:
        return "beats-production"
    if abs(candidate_score - production_score) <= 0.005:
        return "matches-production"
    return "below-production"


def build_recommendation(verdict: str, candidate_passed: bool) -> str:
    if verdict == "beats-production" and candidate_passed:
        return "Candidate beat the production baseline and passed the threshold. Consider manual promotion after reviewing per-case reasoning."
    if verdict == "matches-production" and candidate_passed:
        return "Candidate matches production quality. Promote only if the prompt is clearer or addresses a specific known weakness."
    if candidate_passed:
        return "Candidate passed the threshold but remains below production. Keep experimenting unless it improves a targeted metric humans care about."
    return "Candidate did not pass the threshold. Do not promote; revise the staging prompt and rerun evaluation."


def main() -> int:
    args = parse_args()
    candidate_report_path = Path(args.candidate_report)
    output_path = Path(args.output)

    try:
        candidate_report = read_json_file(candidate_report_path, "candidate report")
        scores = read_json_file(SCORES_PATH, "production scores")
        production_prompt = find_production_prompt(scores, args.type)

        candidate_score = float(candidate_report.get("composite_score", 0.0))
        production_score = float(production_prompt.get("score", 0.0))
        candidate_metrics = candidate_report.get("metrics", {})
        production_metrics = production_prompt.get("metrics", {})

        metric_deltas = {
            metric: round(
                metric_value(candidate_metrics, metric)
                - metric_value(production_metrics, metric, production_prompt.get(metric)),
                4,
            )
            for metric in METRIC_KEYS
        }
        verdict = build_verdict(candidate_score, production_score)
        report = {
            "prompt_type": args.type,
            "candidate_score": candidate_score,
            "production_score": production_score,
            "delta": round(candidate_score - production_score, 4),
            "verdict": verdict,
            "recommendation": build_recommendation(
                verdict,
                bool(candidate_report.get("passed", False)),
            ),
            "candidate_metrics": {
                metric: metric_value(candidate_metrics, metric) for metric in METRIC_KEYS
            },
            "production_metrics": {
                metric: metric_value(production_metrics, metric, production_prompt.get(metric))
                for metric in METRIC_KEYS
            },
            "metric_deltas": metric_deltas,
        }
        write_json_file(output_path, report)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "COMPARE COMPLETE: "
        f"candidate={report['candidate_score']:.2f} "
        f"production={report['production_score']:.2f} "
        f"delta={report['delta']:.2f} "
        f"verdict={report['verdict']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
