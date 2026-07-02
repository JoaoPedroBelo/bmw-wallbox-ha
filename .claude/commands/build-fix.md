---
description: Incrementally fix lint, type, and test errors with minimal, safe changes. One error at a time.
---

# Build and Fix

Incrementally fix lint / type / test errors with minimal, safe changes.

## Step 1: Detect Scope

| Check        | Command                                                        |
| ------------ | -------------------------------------------------------------- |
| Lint         | `.venv/bin/ruff check custom_components/ tests/`               |
| Format       | `.venv/bin/ruff format custom_components/ tests/ --check`      |
| Types        | `.venv/bin/mypy custom_components/bmw_wallbox --show-error-codes` |
| Tests        | `.venv/bin/pytest tests/ -q`                                   |

If $ARGUMENTS names a scope (a file or `lint`/`types`/`tests`), only run that.

## Step 2: Auto-fix the safe stuff first

- `.venv/bin/ruff check custom_components/ tests/ --fix` (safe autofixes)
- `.venv/bin/ruff format custom_components/ tests/`

Re-run the checks; only the non-trivial issues should remain.

## Step 3: Fix Loop (One Error at a Time)

1. **Read the file** — see error context (~10 lines around the reported line).
2. **Diagnose** — identify the root cause (don't just silence with `# noqa` / `# type: ignore`).
3. **Fix minimally** — smallest change that resolves the error.
4. **Re-run the check** — verify it's gone and no new errors appeared.
5. **Move to next.**

## Step 4: Guardrails

Stop and ask the user if:

- A fix introduces **more errors than it resolves**.
- The **same error persists after 3 attempts**.
- The fix requires **architectural changes** or changes charging-control behavior.

Never suppress an error with `# noqa` / `# type: ignore` without an inline comment explaining why.

## Step 5: Summary

```
BUILD FIX RESULTS: Fixed [X], Remaining [Y], New [Z]
Files modified:
- [file]: [what was fixed]
```

## Arguments

$ARGUMENTS — optional scope (a file path, or `lint`/`types`/`tests`) or a specific error description.
