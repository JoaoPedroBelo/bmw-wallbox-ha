---
description: Run comprehensive verification checks on the codebase. Use before committing or creating PRs.
---

# Verification Command

Run comprehensive verification on the current codebase state, using the project venv (`.venv/bin`).

## Instructions

Execute in this order. Stop on critical failures (ruff / tests).

1. **Lint** — `.venv/bin/ruff check custom_components/ tests/`
2. **Format check** — `.venv/bin/ruff format custom_components/ tests/ --check`
3. **Type check** — `.venv/bin/mypy custom_components/bmw_wallbox --show-error-codes` (advisory — CI runs it `continue-on-error`)
4. **Tests** — `.venv/bin/pytest tests/ -q`
5. **Print/debug audit** — search `custom_components/` for `print(` / `breakpoint(`
6. **Git status** — show uncommitted changes

## Output Format

```
VERIFICATION: [PASS/FAIL]

Lint:       [OK/X issues]
Format:     [OK/X unformatted]
Types:      [OK/X errors]  (advisory)
Tests:      [X/Y passed]
Debug logs: [OK/X print/breakpoint]

Ready for PR: [YES/NO]
```

## Modes

$ARGUMENTS can be:

- `quick` — ruff check + format check only
- `full` — all checks (default)
- `pre-commit` — ruff check + format + tests
