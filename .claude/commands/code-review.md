---
description: Review staged/unstaged changes for quality, HA conventions, OCPP correctness, and project patterns
allowed-tools: Bash, Read, Grep, Glob, Agent
model: sonnet
---

Orchestrate a code review of all current changes using the `code-reviewer` agent.

## Steps

1. Run `git diff --stat` to get an overview of changed files.
2. Identify what's affected based on file paths:
   - `coordinator.py` → OCPP handlers / charging commands (highest risk)
   - `sensor.py` / `binary_sensor.py` → sensor entities
   - `button.py` / `switch.py` / `number.py` → control entities
   - `config_flow.py` / `__init__.py` → setup / configuration
   - `const.py` → constants
   - `tests/` → test coverage
3. Launch the `code-reviewer` agent (which preloads `general`, `security`, and `testing` skills, and reads the relevant `docs/`) to perform the full review.
4. For changes touching `coordinator.py` async/OCPP/command code, also launch the `silent-failure-hunter` agent.
5. Present findings organized by severity:
   - **Critical** — must fix before merge
   - **High** — should fix
   - **Medium** — worth addressing
   - **Suggestions** — nice to have

If all changes pass review, confirm they are ready to commit.
