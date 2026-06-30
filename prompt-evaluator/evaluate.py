#!/usr/bin/env python3
"""Evaluate a staged prompt against curated prompt evaluator test cases."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from anthropic import Anthropic


MODEL_NAME = "claude-sonnet-4-6"
PASS_THRESHOLD = 0.75
DEFAULT_OUTPUT_PATH = "eval_report.json"
VALID_PROMPT_TYPES = ("pr_review", "test_gap")
ROOT_DIR = Path(__file__).resolve().parents[1]
EVALUATOR_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "evaluator_system.md"
TEST_CASES_DIR = Path(__file__).resolve().parent / "test-cases"
METRIC_KEYS = ("precision", "recall", "false_positive_rate", "specificity", "consistency")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a candidate prompt.")
    parser.add_argument("--prompt", required=True, help="Path to candidate prompt markdown file.")
    parser.add_argument(
        "--type",
        required=True,
        choices=VALID_PROMPT_TYPES,
        help="Prompt type to evaluate.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to write the evaluation report. Defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    return parser.parse_args()


def read_text_file(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {label} at {path}: {exc}") from exc


def read_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Unable to read {label} at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {label} at {path}: {exc}") from exc


def load_test_cases(prompt_type: str) -> list[dict[str, Any]]:
    case_dir = TEST_CASES_DIR / prompt_type
    diff_paths = sorted(case_dir.glob("case_*_diff.txt"))
    if not diff_paths:
        raise RuntimeError(f"No test case diffs found in {case_dir}.")

    cases: list[dict[str, Any]] = []
    for diff_path in diff_paths:
        expected_path = diff_path.with_name(diff_path.name.replace("_diff.txt", "_expected.json"))
        if not expected_path.exists():
            raise RuntimeError(f"Missing expected findings file for {diff_path}: {expected_path}")
        expected = read_json_file(expected_path, "expected findings")
        cases.append(
            {
                "case_id": expected.get("case_id", diff_path.stem),
                "diff_path": str(diff_path.relative_to(ROOT_DIR)),
                "expected_path": str(expected_path.relative_to(ROOT_DIR)),
                "diff": read_text_file(diff_path, "test diff"),
                "expected": expected,
            }
        )
    return cases


def build_user_message(candidate_prompt: str, diff_content: str, expected: dict[str, Any]) -> str:
    return (
        "Candidate system prompt:\n\n"
        "```markdown\n"
        f"{candidate_prompt}\n"
        "```\n\n"
        "Unified diff test case:\n\n"
        "```diff\n"
        f"{diff_content}\n"
        "```\n\n"
        "Expected findings JSON:\n\n"
        "```json\n"
        f"{json.dumps(expected, indent=2)}\n"
        "```"
    )


def parse_json_response(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Evaluator returned invalid JSON: {exc}\nResponse: {response_text}") from exc


def call_claude(system_prompt: str, user_message: str) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required.")

    client = Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as exc:
        raise RuntimeError(f"Claude API request failed: {exc}") from exc

    text_blocks = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    if not text_blocks:
        raise RuntimeError("Claude API response did not contain any text content.")

    return parse_json_response("\n".join(text_blocks))


def coerce_score(value: Any, metric: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Evaluator metric {metric} is not numeric: {value}") from exc
    if score < 0.0 or score > 1.0:
        raise RuntimeError(f"Evaluator metric {metric} must be between 0.0 and 1.0: {score}")
    return score


def normalize_case_score(case_id: str, raw_score: dict[str, Any]) -> dict[str, Any]:
    metrics = {metric: coerce_score(raw_score.get(metric), metric) for metric in METRIC_KEYS}
    composite_score = (
        metrics["precision"] + metrics["recall"] + metrics["specificity"] + metrics["consistency"]
    ) / 4
    return {
        "case_id": case_id,
        **metrics,
        "composite_score": round(composite_score, 4),
        "reasoning": str(raw_score.get("reasoning", "")),
        "strengths": raw_score.get("strengths", []),
        "weaknesses": raw_score.get("weaknesses", []),
    }


def aggregate_scores(per_case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_case_scores:
        raise RuntimeError("Cannot aggregate an empty evaluation result set.")

    metrics = {
        metric: round(
            sum(float(case_score[metric]) for case_score in per_case_scores) / len(per_case_scores),
            4,
        )
        for metric in METRIC_KEYS
    }
    composite_score = round(
        (
            metrics["precision"]
            + metrics["recall"]
            + metrics["specificity"]
            + metrics["consistency"]
        )
        / 4,
        4,
    )
    reasoning = " ".join(
        f"{case_score['case_id']}: {case_score.get('reasoning', '').strip()}"
        for case_score in per_case_scores
        if case_score.get("reasoning")
    )
    test_cases_passed = sum(
        1
        for case_score in per_case_scores
        if float(case_score["composite_score"]) >= PASS_THRESHOLD
    )

    return {
        "metrics": metrics,
        "composite_score": composite_score,
        "passed": composite_score >= PASS_THRESHOLD,
        "reasoning": reasoning,
        "test_cases_passed": test_cases_passed,
    }


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to write JSON report at {path}: {exc}") from exc


def main() -> int:
    args = parse_args()
    candidate_prompt_path = Path(args.prompt)
    output_path = Path(args.output)

    try:
        system_prompt = read_text_file(EVALUATOR_PROMPT_PATH, "evaluator system prompt")
        candidate_prompt = read_text_file(candidate_prompt_path, "candidate prompt")
        test_cases = load_test_cases(args.type)

        per_case_scores = []
        for test_case in test_cases:
            raw_score = call_claude(
                system_prompt,
                build_user_message(candidate_prompt, test_case["diff"], test_case["expected"]),
            )
            normalized_score = normalize_case_score(test_case["case_id"], raw_score)
            normalized_score["diff_path"] = test_case["diff_path"]
            normalized_score["expected_path"] = test_case["expected_path"]
            per_case_scores.append(normalized_score)

        aggregate = aggregate_scores(per_case_scores)
        report = {
            "prompt_type": args.type,
            "eval_date": date.today().isoformat(),
            "candidate_prompt_file": str(candidate_prompt_path),
            "composite_score": aggregate["composite_score"],
            "passed": aggregate["passed"],
            "pass_threshold": PASS_THRESHOLD,
            "metrics": aggregate["metrics"],
            "reasoning": aggregate["reasoning"],
            "per_case_scores": per_case_scores,
            "test_cases_run": len(test_cases),
            "test_cases_passed": aggregate["test_cases_passed"],
            "iterations": len(per_case_scores),
        }
        write_json_file(output_path, report)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"EVAL COMPLETE: score={report['composite_score']:.2f} passed={report['passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
