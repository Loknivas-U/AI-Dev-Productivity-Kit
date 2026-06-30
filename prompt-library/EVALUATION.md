# Prompt Evaluation Methodology

This document explains how `ai-dev-productivity-kit` evaluates staged prompts before a human decides whether to promote them to production.

## Metrics

### Precision

Precision measures how many findings produced by a candidate prompt match the expected findings for a test case. It matters because noisy AI review comments reduce developer trust quickly; a prompt that flags many non-issues should not be promoted even if it catches some real problems.

### Recall

Recall measures how many expected findings the candidate prompt catches. It matters because these agents exist to surface useful review and test coverage signals that humans might miss. A prompt with low recall may look quiet and polished while failing to catch important defects.

### False Positive Rate

False positive rate estimates how often the prompt flags non-issues. It is tracked separately from the composite score because it is already indirectly reflected in precision, but high false positives still deserve explicit attention in the evaluator reasoning. This helps humans distinguish a cautious prompt from a noisy one.

### Specificity

Specificity measures whether the prompt produces concrete file and line references instead of vague warnings. The review and gap detector workflows are only useful when developers can act on the output without searching through the diff manually. Specificity also discourages generic comments that sound plausible but are not grounded in evidence.

### Consistency

Consistency measures whether the prompt is likely to produce similar output across repeated runs on the same diff. Prompt changes that rely on ambiguous wording can make an evaluator pass once but behave unpredictably later. A production prompt should be stable enough for teams to trust in automated workflows.

## Test Case Design

The PR review test cases cover five failure modes: hardcoded secrets, missing file read error handling, SQL injection through string concatenation, a clean diff with tests that should produce no findings, and a YAML workflow using `pull_request_target` with unsanitized pull request input. Together they exercise security, correctness, maintainability, and false positive behavior.

The test gap cases cover five coverage patterns: multiple new Python functions with no tests, a new Python function with a matching `test_` function, a new async JavaScript function without a Jest test, a modified Python function with a matching updated test, and three new Python functions where only two are tested. These cases are intentionally small so evaluator failures can be traced to prompt behavior rather than fixture complexity.

## Pass Threshold

The pass threshold is a `0.75` composite score. This is high enough to reject prompts that are merely plausible, while leaving room for human judgment when a candidate improves one metric at the cost of another. The composite score averages precision, recall, specificity, and consistency; false positive rate is reported separately because lower is better and it needs human interpretation alongside precision.

## SkillOpt Influence

SkillOpt informed this evaluation loop by separating prompt experimentation from production promotion. A candidate prompt is tested against known cases, the evaluator explains failures, and humans can revise the prompt based on those observations. Unlike a fully automated optimization loop, this repo never promotes a prompt automatically; the final step requires a human-triggered `workflow_dispatch` and the `--confirm` flag in `promote.py`.

## Known Limitations

Automated prompt evaluation is still an approximation. The critic model may overestimate how another model will behave, especially on ambiguous diffs or prompts with subtle wording changes. The current fixtures are synthetic and intentionally focused, so they do not represent every framework, language, or repository convention. The evaluator also scores likely behavior rather than executing the candidate prompt end to end as a separate model call.

## Adding New Test Cases

Add new cases under `prompt-evaluator/test-cases/pr_review/` or `prompt-evaluator/test-cases/test_gap/`. Each case needs a `case_NN_diff.txt` unified diff and a matching `case_NN_expected.json` file with `case_id`, `description`, `expected_findings`, `expected_finding_count`, and `false_positive_threshold`. Keep cases focused on one primary behavior so regressions are easy to diagnose. When adding enough new cases to change baseline interpretation, update `prompt-library/scores/eval_results.json` metadata after a human review.

## Promotion Data Contract

Prompt promotion requires a saved evaluation report for the same prompt type and staging candidate file. The report must include a numeric `composite_score`, a `metrics` object, and a positive integer `iterations` count from `evaluate.py`. If no matching report exists under `prompt-library/scores/`, `promote.py` refuses to promote and asks the user to run evaluation first.

## Estimated Cost Per Evaluation Run

Each evaluation run sends one candidate prompt, one diff, and one expected-findings file for each of five cases. A typical run is expected to use roughly 20k to 35k input tokens and 4k to 8k output tokens, depending on prompt length and evaluator reasoning. Actual cost depends on the Anthropic pricing in effect for `claude-sonnet-4-6` at runtime.
