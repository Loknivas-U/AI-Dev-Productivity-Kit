# AI Dev Productivity Kit

Open-source toolkit for embedding AI into engineering workflows — automated PR review, test gap detection, and a self-improving prompt library with a full eval-to-production pipeline.

## What It Does

This kit embeds Claude into the pull request lifecycle and prompt management workflow. Every PR automatically receives a structured AI code review and test gap report posted as comments. A separate 5-stage prompt pipeline (evaluate → compare → promote) ensures the AI's own instructions are versioned, scored, and improved over time — the AI reviews code, and the system reviews the AI.

## Architecture — 5 Layers

| Layer | Component | What It Does |
|-------|-----------|--------------|
| 1 | AGENTS.md | Agent identity, behavioral rules, scope boundaries per layer, secret handling rules |
| 2 | PR Reviewer | Claude-powered review posted as PR comment + conditional Merge Risk Advisory on High findings |
| 3 | Test Gap Detector | LLM-driven test coverage analysis on every PR diff |
| 4 | Prompt Library | Versioned production prompts with SkillOpt eval scores, staging/archive/failed folders |
| 5 | Prompt Evaluator | Automated scoring pipeline: evaluate → compare → promote with `--confirm` guard |

## How It Works

### PR Review Flow

1. Developer opens a PR targeting `main`
2. `pr-review.yml` and `test-gap.yml` trigger automatically (parallel)
3. Claude reviews the diff and posts a structured comment (Summary / High / Medium / Low / What Looks Good)
4. If High priority findings exist, `risk_advisor.py` posts a Merge Risk Advisory as a second comment
5. `test-gap.yml` posts a coverage gap report
6. Required status checks (`pr-review`, `test-gap`) must pass before the merge button activates
7. Human reads the output and decides to merge — AI never approves or blocks

### Prompt Improvement Flow

1. Developer puts a candidate prompt in `prompt-library/staging/`
2. `prompt-eval.yml` triggers, runs `evaluate.py` against 5 synthetic test cases, commits timestamped score files back to the branch using `PAT_TOKEN`
3. `prompt-compare.yml` triggers if eval passes, compares candidate vs production score
4. Developer runs `prompt-promote.yml` (`workflow_dispatch`, manual only) with `--confirm` flag
5. `promote.py` validates a committed eval report exists, archives current production prompt, promotes candidate, opens a PR into `main`
6. PR Reviewer and Test Gap Detector run on the promotion PR — human reviews and merges

## Branch Protection & Workflow Gates

The `main` branch is protected with a GitHub Ruleset that enforces:

- **Required status checks**: `pr-review` and `test-gap` must pass before any PR can be merged
- **Block force pushes**: prevents history rewriting on `main`
- **Restrict deletions**: `main` cannot be deleted

Bypass is granted to Repository Admin and Deploy Keys only.

The AI workflows post results as PR comments. The merge decision always belongs to the human — the gate holds the button, not the merge.

**Note on workflow authentication:** PR comment workflows use the default `GITHUB_TOKEN` (read + PR write). The eval report commit and promotion PR creation use `PAT_TOKEN` (repo + workflow scopes) to push to branches and create PRs with full permissions, since `GITHUB_TOKEN` cannot push to protected branches or create PRs that trigger downstream workflows.

## Setup

1. Fork the repo
2. Generate an Anthropic API key at [console.anthropic.com](https://console.anthropic.com) and add it as repo secret: `ANTHROPIC_API_KEY`
3. Generate a GitHub PAT (classic) with `repo` + `workflow` scopes and add it as repo secret: `PAT_TOKEN`
4. Enable GitHub Actions (Actions tab → enable)
5. Open a PR — AI review and test gap run automatically
6. To use the prompt eval pipeline: put a candidate in `prompt-library/staging/`, push to a feature branch, trigger `prompt-eval.yml` from that branch

## Prompt Evaluation Pipeline (Detail)

- Candidate prompts live in `prompt-library/staging/`
- `evaluate.py` scores the candidate against 5 synthetic test cases using a critic AI (Claude) — outputs `composite_score`, per-metric breakdown, and per-case reasoning
- `compare.py` checks if candidate beats the production baseline score
- Timestamped eval and compare reports are committed to the branch automatically (not ephemeral — full audit trail in git history)
- `promote.py` requires a committed eval report with valid `composite_score`, `metrics`, and positive `iterations` count before promotion is allowed — no report, no promotion
- Promotion requires explicit `--confirm` flag — no auto-promotion ever
- All score history lives in `prompt-library/scores/`

## Tech Stack

- **Claude (Anthropic)** — PR review, test gap detection, prompt evaluation critic
- **GitHub Actions** — all automation (5 workflows)
- **Python 3.11**
- **GitHub Rulesets** — branch protection and merge gates
- **SkillOpt-inspired scoring methodology** — automated prompt optimization loop

## Eval Results (Real Numbers)

| Metric | v1.0 (baseline) | v1.2 (promoted) | Delta |
|--------|-----------------|-----------------|-------|
| Composite Score | 0.81 | 0.9225 | +0.1125 |
| Precision | 0.84 | 0.90 | +0.06 |
| Recall | 0.79 | 0.98 | +0.19 |
| False Positive Rate | 0.16 | 0.06 | -0.10 |
| Specificity | null | 0.90 | — |
| Consistency | null | 0.91 | — |

The false positive rate drop (0.16 → 0.06) reflects the priority calibration fix: the v1.2 prompt no longer flags undocumented exceptions in simple utility functions as High priority unless they risk production outage or data corruption.

Source: [`prompt-library/scores/eval_results.json`](prompt-library/scores/eval_results.json)

## Test Coverage (10 End-to-End Scenarios)

| # | Scenario | Result |
|---|----------|--------|
| 1 | Buggy code — hardcoded secrets + SQL injection | ✅ High priority flagged |
| 2 | New functions with no tests | ✅ Test gaps detected |
| 3 | Clean code with existing tests | ✅ No false positives (v1.2 fix) |
| 4 | Bad staging prompt submitted | ✅ Scored 0.28, rejected |
| 5 | Good staging prompt submitted | ✅ Scored 0.92, beats production |
| 6 | Manual promotion via `promote.py` | ✅ Full eval → compare → promote pipeline |
| 7 | Empty diff PR (`.gitkeep` only) | ✅ Graceful no-op output |
| 8 | YAML-only changes | ✅ Correctly identified as no code gaps |
| 9 | No API key set | ✅ Fails visibly with clear error, exit code 1 |
| 10 | AGENTS.md structure audit | ✅ Updated to v1.2.0, all layers accurate |

## Project Status

Complete — all 5 layers built, tested across 10 scenarios, and documented. Built as a working demonstration of AI-augmented developer productivity tooling.

## Author

Loknivas Upputholla

- GitHub: [Loknivas-U](https://github.com/Loknivas-U)
- LinkedIn: [loknivasupputholla](https://linkedin.com/in/loknivasupputholla)
