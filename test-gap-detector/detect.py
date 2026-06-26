#!/usr/bin/env python3
"""Run the test gap detector against a diff file and write the report."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from anthropic import Anthropic


MODEL_NAME = "claude-sonnet-4-6"
DEFAULT_OUTPUT_PATH = "gap_report.md"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "test_gap_system.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an AI test gap report from a unified diff."
    )
    parser.add_argument("--diff", required=True, help="Path to the PR diff file.")
    parser.add_argument("--pr-title", required=True, help="Pull request title.")
    parser.add_argument("--pr-number", required=True, type=int, help="Pull request number.")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to write the gap report. Defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    return parser.parse_args()


def read_text_file(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {label} at {path}: {exc}") from exc


def build_user_message(diff_content: str, pr_title: str, pr_number: int) -> str:
    return (
        f"PR title: {pr_title}\n"
        f"PR number: {pr_number}\n\n"
        "Analyze this unified diff only:\n\n"
        "```diff\n"
        f"{diff_content}\n"
        "```"
    )


def call_claude(system_prompt: str, user_message: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required.")

    client = Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
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

    return "\n".join(text_blocks)


def write_report(output_path: Path, report_text: str) -> None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to write gap report at {output_path}: {exc}") from exc


def main() -> int:
    args = parse_args()
    diff_path = Path(args.diff)
    output_path = Path(args.output)

    try:
        system_prompt = read_text_file(PROMPT_PATH, "system prompt")
        diff_content = read_text_file(diff_path, "diff")
        user_message = build_user_message(diff_content, args.pr_title, args.pr_number)
        report_text = call_claude(system_prompt, user_message)
        write_report(output_path, report_text)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"GAP REPORT COMPLETE: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
