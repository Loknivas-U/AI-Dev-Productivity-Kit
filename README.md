# ai-dev-productivity-kit

> Open-source AI developer productivity kit — AGENTS.md templates, Claude-powered PR reviewer, test gap detector, and a scored prompt library for engineering teams.

## What This Is

`ai-dev-productivity-kit` is a practical reference implementation for adding AI review workflows to engineering repositories. It includes an `AGENTS.md` operating contract, GitHub Actions workflows, Python 3.11 CLI scripts, and Anthropic Claude API integrations for pull request review and test gap detection. It is built for maintainers and engineering teams who want repeatable AI assistance without hiding the prompts, scoring data, or workflow logic. The prompt library stores production prompts evaluated with the SkillOpt prompt scoring method.

## Architecture

| Layer | What it does | Key files |
|---|---|---|
| AGENTS.md | Defines agent behavior, repository boundaries, output formats, and secret handling rules. | `AGENTS.md` |
| PR Reviewer | Reviews PR diffs with Claude and posts a structured review comment through GitHub Actions. | `pr-reviewer/review.py`, `pr-reviewer/.github/workflows/pr-review.yml` |
| Test Gap Detector | Checks changed functions and methods in a PR diff for matching tests added in the same diff. | `test-gap-detector/detect.py`, `test-gap-detector/.github/workflows/test-gap.yml` |
| Prompt Library | Stores scored production prompts and machine-readable SkillOpt evaluation results. | `prompt-library/`, `prompt-library/scores/eval_results.json` |

## How It Works

The PR Reviewer runs from a GitHub Actions workflow on `pull_request` events. It generates a `git diff origin/main...HEAD`, sends that diff to Claude with the PR review system prompt, and posts the resulting structured review comment back to the pull request.

The Test Gap Detector also runs on pull requests after a diff is generated. Claude identifies new or modified functions and methods in the diff, checks whether corresponding tests appear in the same diff, and produces a candidate gap report as a PR comment.

The Prompt Library stores the versioned system prompts used by the active layers. Each prompt includes SkillOpt evaluation metadata, known weaknesses, and the exact production prompt content so teams can inspect or reuse it directly.

## Setup

1. Clone the repo.
2. Add `ANTHROPIC_API_KEY` to GitHub repo secrets (`Settings` → `Secrets` → `Actions`).
3. The workflows trigger automatically on every PR — no other config needed.
4. To run locally: `pip install anthropic`, then `python pr-reviewer/review.py --diff <path> --pr-title "title" --pr-number 1`.

## Prompt Library

SkillOpt scoring measures how well a prompt performs across representative review tasks. An AI attempts the task, a critic AI identifies failures and proposes prompt changes, then the revised prompt is retested and scored from `0.0` to `1.0`. Machine-readable scores are available in [`prompt-library/scores/eval_results.json`](prompt-library/scores/eval_results.json).

## Built With

- Python 3.11
- Anthropic Claude API (`claude-sonnet-4-6`)
- GitHub Actions
- SkillOpt prompt evaluation method

## Author

Loknivas Upputholla
- GitHub: https://github.com/Loknivas-U
- LinkedIn: https://linkedin.com/in/loknivasupputholla
