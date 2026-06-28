#!/usr/bin/env python3
"""Post a non-blocking merge risk advisory when high priority findings exist."""

from __future__ import annotations

import argparse
import os

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from risk_advisor import (
    build_advisory_comment,
    parse_high_priority_findings,
    should_post_advisory,
)


GITHUB_API_URL = "https://api.github.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post a merge risk advisory comment.")
    parser.add_argument(
        "--review-file",
        required=True,
        help="Path to the generated PR review markdown file.",
    )
    parser.add_argument("--pr-title", required=True, help="Pull request title.")
    parser.add_argument("--pr-number", required=True, type=int, help="Pull request number.")
    return parser.parse_args()


def read_text_file(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {label} at {path}: {exc}") from exc


def post_pr_comment(repository: str, pr_number: int, body: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is required.")

    url = f"{GITHUB_API_URL}/repos/{repository}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json={"body": body},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc


def main() -> int:
    args = parse_args()

    try:
        repository = os.environ.get("REPOSITORY")
        if not repository:
            raise RuntimeError("REPOSITORY environment variable is required.")

        review_text = read_text_file(Path(args.review_file), "review output")
        findings = parse_high_priority_findings(review_text)

        if not should_post_advisory(findings):
            print("NO ADVISORY: no high priority findings detected")
            return 0

        advisory_comment = build_advisory_comment(
            args.pr_title,
            args.pr_number,
            findings,
        )
        post_pr_comment(repository, args.pr_number, advisory_comment)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"ADVISORY POSTED: {len(findings)} high priority findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
