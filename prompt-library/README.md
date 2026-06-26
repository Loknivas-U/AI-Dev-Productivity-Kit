# Prompt Library

The prompt library stores scored, production-ready system prompts used by `ai-dev-productivity-kit`. Each prompt captures the best-performing version from the PR Reviewer and Test Gap Detector layers, along with evaluation metadata that explains how it performed.

## SkillOpt Scoring

SkillOpt is an automated prompt optimization loop. An AI attempts a set of representative tasks, a critic AI observes failures, writes improved rules into the system prompt, and the revised prompt is tested again. Changes are kept only when they improve the evaluation score. Scores range from `0.0` to `1.0`, where higher means stronger performance on the evaluation set.

## Using A Prompt

Open one of the versioned prompt files and copy the content under `## Prompt` into your system prompt. The metadata above that section explains the score, evaluation set, known weaknesses, and changes made during optimization.

## Contributing A Prompt

To contribute a new prompt, write the prompt, run it against at least 10 representative test cases, score the results, and submit a pull request with the prompt and evaluation metadata. Include enough detail for maintainers to understand the task mix, failure modes, and why the prompt should be promoted.

## Machine-Readable Scores

Machine-readable prompt scores are stored in [`scores/eval_results.json`](scores/eval_results.json).

## Agent Access

Per `AGENTS.md` section 5, prompt-library prompts are read-only for agents. Agents may reference these prompts, but prompt scoring and updates are performed by human maintainers.
