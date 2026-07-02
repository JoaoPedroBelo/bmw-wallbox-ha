---
description: Save current session state so work can be resumed in a future session with full context.
---

# Save Session

Capture everything from this session and write it to a dated file.

## Process

1. Review all files modified (use `git diff` or conversation recall).
2. Create `~/.claude/session-data/YYYY-MM-DD-<short-id>-session.md`.
3. Write every section below — use "N/A" for empty sections, never skip them.
4. Show the file to the user and ask for confirmation.

```bash
mkdir -p ~/.claude/session-data
```

## Template

```markdown
# Session: YYYY-MM-DD

**Project:** BMW Wallbox (Home Assistant / OCPP 2.0.1)
**Topic:** [one-line summary]

## What We Are Building

[1-3 paragraphs with full context]

## What WORKED (with evidence)

- **[thing]** — confirmed by: [specific evidence, e.g. test name, wallbox log line]

## What Did NOT Work (and why)

- **[approach]** — failed because: [exact reason / error message]

## What Has NOT Been Tried Yet

- [approach / idea]

## Current State of Files

| File                | Status                           | Notes   |
| ------------------- | -------------------------------- | ------- |
| `coordinator.py`    | Complete/In Progress/Not Started | [notes] |

## Decisions Made

- **[decision]** — reason: [why]

## Blockers & Open Questions

- [blocker / question]

## Exact Next Step

[The single most important thing to do when resuming]
```

## Notes

- Each session gets its own file.
- "What Did NOT Work" is the most critical section — it prevents re-treading dead ends (especially around OCPP command behavior).
- Read by `/resume-session` at the start of the next session.
