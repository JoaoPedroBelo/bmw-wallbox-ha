---
description: Run all CI checks locally before creating a PR
allowed-tools: Bash, Read, Grep, Glob, Agent
model: sonnet
---

Run all CI/CD checks locally, then review code quality. Two phases.

## Phase 1 — CI Checks

Run these sequentially (using the project venv), reporting pass/fail for each. These mirror `.github/workflows/tests.yml`:

1. `.venv/bin/ruff check custom_components/ tests/` — linter (blocks CI)
2. `.venv/bin/ruff format custom_components/ tests/ --check` — formatting (blocks CI)
3. `.venv/bin/mypy custom_components/bmw_wallbox --show-error-codes --pretty` — type check (advisory in CI)
4. `.venv/bin/pytest tests/ -v --tb=short` — full test suite
5. `.venv/bin/pytest tests/ --cov=custom_components.bmw_wallbox --cov-report=term-missing` — coverage
6. `.venv/bin/pre-commit run --all-files` — pre-commit hooks (ruff, bandit, prettier, manifest validation) if available

Also confirm, if the change bumps a release: the version in `custom_components/bmw_wallbox/manifest.json` matches the intended tag, and `CHANGELOG.md` has an entry (the release workflow enforces both).

## Phase 2 — Code Review

Launch the `code-reviewer` agent to review all changes for quality, HA conventions, OCPP correctness, and project patterns. For coordinator/async/OCPP changes, also launch `silent-failure-hunter`.

## Output

Print a summary table with pass/fail per CI step, followed by code review findings by severity. If any step fails, explain what went wrong and suggest fixes. If everything passes, confirm the PR is ready.
