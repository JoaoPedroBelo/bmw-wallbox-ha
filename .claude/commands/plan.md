---
description: Restate requirements, read the relevant docs, assess risks, and create a step-by-step plan. WAIT for user CONFIRM before touching any code.
---

# Plan Command

Create a comprehensive implementation plan before writing any code.

## Process

1. **Restate Requirements** — Clarify what needs to be built in your own words.
2. **Read the docs** — This project is documentation-first. Read the relevant files in `custom_components/bmw_wallbox/docs/` before planning:
   | Task | Read first |
   |------|-----------|
   | Add a sensor | `docs/ENTITIES.md`, `docs/DATA_SCHEMAS.md` |
   | Add a button/switch/number | `docs/ENTITIES.md`, `docs/COORDINATOR.md` |
   | Add an OCPP message handler | `docs/OCPP_HANDLERS.md`, `docs/PATTERNS.md` |
   | Add an outgoing OCPP command | `docs/COORDINATOR.md`, `docs/PATTERNS.md`, `docs/CONTEXT.md` |
   | Debug an issue | `docs/TROUBLESHOOTING.md`, `docs/PATTERNS.md` |
   | Write tests | `docs/TESTING.md`, `tests/conftest.py` |
3. **Identify Risks** — Surface blockers and dependencies. Flag anything touching charging control (EVCC-style pause/resume), transactions, or OCPP timeouts.
4. **Check Existing Code** — Search for related handlers/commands/entities and reusable constants in `const.py`.
5. **Create Step Plan** — Ordered phases with specific files.
6. **Wait for Confirmation** — MUST receive explicit user approval before proceeding.

## Output Format

```
# Implementation Plan: [Feature Name]

## Requirements
[2-3 sentences restating the goal]

## Docs Read
- [doc] — [what it told us]

## Existing Code to Reuse
- [handler/command/entity] in [file] — [how it applies]

## Implementation Phases

### Phase 1: [Name]
- [ ] [specific task with file path]

### Phase 2: [Name]
- [ ] [specific task with file path]

## Risks
- HIGH/MEDIUM/LOW: [risk description]

## Estimated Complexity: [HIGH/MEDIUM/LOW]

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## Important

- **NEVER** write code until the user confirms.
- Charging-control changes MUST follow EVCC-style control (`SetChargingProfile`, never `RequestStopTransaction`).
- Tests are mandatory — include a test task in every phase that adds behavior.

## Arguments

$ARGUMENTS — describe the feature or task to plan.
