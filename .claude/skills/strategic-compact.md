---
name: strategic-compact
description: Guidance on when to manually compact context for optimal token management during long sessions.
---

# Strategic Compact

Compact at logical task boundaries rather than letting auto-compaction trigger mid-work.

## When to Compact

| Phase Transition           | Compact? | Why                                                            |
| -------------------------- | -------- | -------------------------------------------------------------- |
| Research -> Planning       | Yes      | Doc-reading context is bulky; the plan is the distilled output |
| Planning -> Implementation | Yes      | Plan is in a todo list or file; free up context for code       |
| Implementation -> Testing  | Maybe    | Keep if tests reference recently written code                  |
| Debugging -> Next feature  | Yes      | OCPP/log traces pollute context for unrelated work             |
| Mid-implementation         | No       | Losing variable names, file paths, and partial state is costly |
| After a failed approach    | Yes      | Clear the dead-end reasoning before trying a new approach      |

## What Survives Compaction

| Persists                      | Lost                                |
| ----------------------------- | ----------------------------------- |
| CLAUDE.md instructions        | Intermediate reasoning and analysis |
| Todo list                     | File contents you previously read   |
| Memory files                  | Multi-step conversation context     |
| Git state (commits, branches) | Tool call history and counts        |
| Files on disk                 | Nuanced preferences stated verbally |

## Best Practices

1. **Compact after planning** — once the plan is finalized, compact to start implementation fresh.
2. **Compact after debugging** — clear error-resolution and log context before continuing.
3. **Don't compact mid-implementation** — preserve context for related changes across `coordinator.py`/`const.py`/entity files.
4. **Write before compacting** — save important findings to a file, memory, or a `/save-session` note first.
5. **Use /compact with a summary** — e.g. `/compact Focus on adding the current-limit number entity next`.

## Signs You Should Compact

- Responses are getting slower or less coherent.
- You've been in the session for 30+ tool calls.
- You just finished a major phase (doc research, planning, debugging).
- You're about to switch to a completely different area of the integration.
