---
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git show:*), Bash(.venv/bin/ruff:*), Read, Glob, Grep, Agent
description: Security review of the pending changes on the current branch
---

You are a senior security engineer conducting a focused security review of the changes on this branch.

GIT STATUS:

```
!`git status`
```

FILES MODIFIED:

```
!`git diff --name-only origin/HEAD... 2>/dev/null || git diff --name-only`
```

DIFF CONTENT:

```
!`git diff --merge-base origin/HEAD 2>/dev/null || git diff HEAD`
```

## Objective

Identify HIGH-CONFIDENCE security issues newly introduced by this diff. Only flag things you are >80% confident are real and exploitable. This integration runs inside Home Assistant and speaks OCPP 2.0.1 over a WebSocket the wallbox connects to.

## What to examine (this codebase)

**Secrets & credentials**
- Hardcoded RFID tokens, passwords, or API keys (should come from config, not literals).
- SSL private keys committed to the repo, or key/cert contents logged.
- Secrets written to `_LOGGER` (logging URLs/ports/status is fine; logging keys/tokens is not).

**OCPP / input handling**
- Untrusted data from OCPP messages (`meter_value`, identifiers, `kwargs`) used unsafely — e.g. passed to `eval`/`exec`, `os.system`, `subprocess` with `shell=True`, or `pickle.loads`.
- Path traversal from any config/message-derived path in file operations.
- `float(...)` / `int(...)` on message fields without guarding malformed input in a way that could crash the handler loop.

**Command execution / deserialization**
- `eval`, `exec`, `os.system`, `subprocess(..., shell=True)`, `pickle`, `yaml.load` (non-safe), unsafe `json` sinks.

**TLS / transport**
- Certificate validation disabled (`ssl.CERT_NONE`, `verify=False`), weak TLS config for the OCPP server.

**Data exposure**
- Debug logging that dumps full config (including keys) or full message payloads containing credentials.

## Also run

- `.venv/bin/ruff check custom_components/ tests/ --select S` — surface bandit (`S`) findings in the changed code.

## Exclusions (do NOT report)

- Denial-of-service / resource-exhaustion / rate-limiting concerns.
- Secrets stored on disk that are otherwise access-controlled (e.g. `/ssl/privkey.pem` referenced by path).
- Findings in documentation (`*.md`) or test-only files.
- Theoretical race conditions or timing attacks without a concrete path.
- `S104` (bind all interfaces) — intentional for the OCPP server.

## Output Format

Markdown, one section per finding: file:line, severity (HIGH/MEDIUM/LOW), category, description, exploit scenario, and fix recommendation. If nothing qualifies, say so explicitly.

Focus on HIGH and MEDIUM. Better to miss a theoretical issue than to flood the report with false positives.
