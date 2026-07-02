---
name: security
description: Security rules for the BMW Wallbox integration — secrets/credentials, SSL/TLS, OCPP input handling, safe logging, and dependency hygiene.
user-invocable: false
---

# Security Rules

This integration runs inside Home Assistant and exposes an OCPP 2.0.1 WebSocket server that the wallbox connects to. The main risk surfaces are **secrets**, **TLS**, and **untrusted OCPP input**.

## 1. Secrets & credentials

**FAIL — never:**

```python
RFID_TOKEN = "04a125f2fc1194"          # hardcoded literal
password = "hunter2"
```

**PASS — always from config:**

```python
token = self.config.get("rfid_token")
if not token:
    _LOGGER.error("No RFID token configured")
    return {"success": False, "message": "No RFID token configured"}
```

- No hardcoded RFID tokens, passwords, or API keys.
- SSL private keys (`privkey.pem`, `*.key`) are referenced by **path from config** — never committed, never inlined.
- `.env` and key material stay out of git (already covered by `.gitignore`).

## 2. Safe logging

```python
# FAIL — leaks a secret
_LOGGER.info("Using RFID token %s", rfid_token)
_LOGGER.debug("Config: %s", self.config)   # config may contain keys/paths

# PASS — log identifiers and status, not secrets
_LOGGER.info("Starting transaction on evse_id=%s", evse_id)
_LOGGER.debug("SetChargingProfile response: %s", response.status)
```

- Logging connection URLs, ports, EVSE/connector IDs, and OCPP status is fine.
- Never log RFID tokens, keys, or full config/message payloads that may contain credentials.
- `_LOGGER` only — `print()` is banned (ruff `T20`).

## 3. TLS / transport

- The OCPP server uses SSL cert + key paths from config; validate they exist at setup (`os.path.isfile`).
- Never disable certificate validation (`ssl.CERT_NONE`, `verify=False`) to "make it work".
- `S104` (binding to all interfaces) is intentionally allowed for the OCPP server — do not "fix" it.

## 4. Untrusted OCPP input

Treat everything arriving from the wallbox (message fields, `meter_value`, `kwargs`, identifiers) as untrusted:

- Never pass message-derived data to `eval`, `exec`, `os.system`, `subprocess(..., shell=True)`, or `pickle.loads`.
- Guard numeric conversions (`float`/`int`) so a malformed value can't crash the handler loop.
- Never build filesystem paths from message/config data without validation (path traversal).

## 5. Dependency hygiene

- **bandit** runs in pre-commit (`.pre-commit-config.yaml`) and via ruff `S` rules.
- Keep `requirements-*.txt` pinned; the OCPP/HA versions matter for protocol behavior.
- Run `.venv/bin/ruff check custom_components/ tests/ --select S` to surface bandit findings on demand.

## Automated enforcement

- **ruff `S` rules** (flake8-bandit) — flagged in lint on edit and in CI.
- **bandit pre-commit hook** — `pyproject.toml`-configured, excludes tests.
- **detect-private-key pre-commit hook** — blocks committing key material.
- **protect-files hook** (`.claude/hooks/protect-files.sh`) — blocks Claude from editing `.env`, private keys, and venv/cache/VCS internals.

## Verification checklist

- [ ] No hardcoded tokens/passwords/keys
- [ ] No secrets in `_LOGGER` output or committed files
- [ ] TLS validation not disabled
- [ ] Untrusted OCPP fields never reach an exec/deserialization/path sink
- [ ] `ruff --select S` clean on changed code
