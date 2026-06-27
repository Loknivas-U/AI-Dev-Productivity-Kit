#!/usr/bin/env python3
"""Promote a staged prompt to production after explicit human confirmation."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any


VALID_PROMPT_TYPES = ("pr_review", "test_gap")
ROOT_DIR = Path(__file__).resolve().parents[1]
SCORES_PATH = ROOT_DIR / "prompt-library" / "scores" / "eval_results.json"
STAGING_PATHS = {
    "pr_review": ROOT_DIR / "prompt-library" / "staging" / "pr_review_candidate.md",
    "test_gap": ROOT_DIR / "prompt-library" / "staging" / "test_gap_candidate.md",
}
PROMPT_IDS = {
    "pr_review": "pr_review",
    "test_gap": "test_gap",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a staged prompt to production.")
    parser.add_argument(
        "--type",
        required=True,
        choices=VALID_PROMPT_TYPES,
        help="Prompt type to promote.",
    )
    parser.add_argument(
        "--version",
        required=True,
        help='New version string, for example "1.1".',
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually promote the staged prompt. Without this flag, the command is a dry run.",
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
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to write {path}: {exc}") from exc


def find_current_production(scores: dict[str, Any], prompt_type: str) -> dict[str, Any]:
    candidates = [
        prompt
        for prompt in scores.get("prompts", [])
        if prompt.get("id", "").startswith(PROMPT_IDS[prompt_type])
        and prompt.get("status") == "production"
    ]
    if not candidates:
        raise RuntimeError(f"No production prompt entry found for {prompt_type}.")
    return candidates[0]


def archive_path_for(production_file: Path, version: str) -> Path:
    safe_version = version.replace(".", "_")
    return ROOT_DIR / "prompt-library" / "archive" / f"{production_file.stem}_v{safe_version}{production_file.suffix}"


def latest_eval_report(prompt_type: str) -> dict[str, Any] | None:
    reports = sorted((ROOT_DIR / "prompt-library" / "scores").glob(f"{prompt_type}_eval_*.json"))
    for report_path in reversed(reports):
        report = read_json_file(report_path, "evaluation report")
        if report.get("prompt_type") == prompt_type:
            return report
    return None


def build_new_entry(
    prompt_type: str,
    version: str,
    production_file: Path,
    old_entry: dict[str, Any],
) -> dict[str, Any]:
    eval_report = latest_eval_report(prompt_type)
    version_id = version.replace(".", "_")
    if eval_report:
        score = eval_report.get("composite_score")
        metrics = eval_report.get("metrics", {})
        reasoning = eval_report.get("reasoning", "")
        eval_date = eval_report.get("eval_date", date.today().isoformat())
        eval_set_size = eval_report.get("test_cases_run")
    else:
        score = old_entry.get("score")
        metrics = old_entry.get("metrics", {})
        reasoning = "Promoted from staging by human workflow; no timestamped eval report was found."
        eval_date = date.today().isoformat()
        eval_set_size = old_entry.get("eval_set_size")

    return {
        "id": f"{prompt_type}_v{version_id}",
        "file": str(production_file.relative_to(ROOT_DIR)),
        "version": version,
        "score": score,
        "eval_date": eval_date,
        "eval_set_size": eval_set_size,
        "iterations": None,
        "metrics": metrics,
        "specificity": metrics.get("specificity"),
        "consistency": metrics.get("consistency"),
        "reasoning": reasoning,
        "verdict": "promoted-by-human",
        "production_score": old_entry.get("score"),
        "status": "production",
    }


def promote_prompt(prompt_type: str, version: str) -> None:
    scores = read_json_file(SCORES_PATH, "score registry")
    current_entry = find_current_production(scores, prompt_type)
    production_file = ROOT_DIR / current_entry["file"]
    staging_file = STAGING_PATHS[prompt_type]

    if not production_file.exists():
        raise RuntimeError(f"Current production prompt does not exist: {production_file}")
    if not staging_file.exists():
        raise RuntimeError(f"Staging prompt does not exist: {staging_file}")

    archive_file = archive_path_for(production_file, str(current_entry.get("version", "unknown")))
    archive_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(production_file, archive_file)
    shutil.copy2(staging_file, production_file)

    current_entry["status"] = "archived"
    current_entry["archived_file"] = str(archive_file.relative_to(ROOT_DIR))
    scores.setdefault("prompts", []).append(
        build_new_entry(prompt_type, version, production_file, current_entry)
    )
    write_json_file(SCORES_PATH, scores)


def main() -> int:
    args = parse_args()

    try:
        if not args.confirm:
            print("DRY RUN: pass --confirm to actually promote")
            return 0

        promote_prompt(args.type, args.version)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"PROMOTED: {args.type} v{args.version} is now production")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
