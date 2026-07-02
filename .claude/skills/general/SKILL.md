---
name: general
description: Core project conventions for the BMW Wallbox Home Assistant integration — architecture, OCPP/EVCC rules, Python/HA style, coordinator pattern, git, and testing standards.
user-invocable: false
---

# BMW Wallbox — General Rules

## Architecture (read this first)

- Home Assistant custom integration for BMW EV wallboxes using **OCPP 2.0.1**.
- **HA is the OCPP server (CSMS)** — the wallbox connects TO Home Assistant, not the other way around.
- The `BMWWallboxCoordinator` owns all state in `coordinator.data`. `WallboxChargePoint` (inside `coordinator.py`) handles incoming OCPP messages. Entities are thin views over `coordinator.data`.
- Full docs live in `custom_components/bmw_wallbox/docs/`. **Read the relevant doc before changing coordinator/entity/OCPP logic** (`CONTEXT`, `ARCHITECTURE`, `COORDINATOR`, `ENTITIES`, `OCPP_HANDLERS`, `PATTERNS`, `DATA_SCHEMAS`, `CONSTANTS`, `ENERGY_SENSORS`, `TESTING`, `TROUBLESHOOTING`).

## Critical OCPP / charging rules

1. **EVCC-style control** — pause/resume charging with `SetChargingProfile` (set limit to `0A` to pause, restore to resume). **Never** use `RequestStopTransaction` (causes stuck transaction states).
2. **Transaction required** — `SetChargingProfile` (tx_profile) only works with an active transaction. Check `self.current_transaction_id` first.
3. **Timeouts everywhere** — every outgoing OCPP `call(...)` is wrapped in `asyncio.wait_for(..., timeout=15.0)`.
4. **All state flows through the coordinator** — entities read `self.coordinator.data.get(...)`; never store mutable state on the entity.
5. **Refresh after updates** — after mutating `coordinator.data` in a handler, call `self.coordinator.async_set_updated_data(self.coordinator.data)`.
6. **Handlers** — decorate with `@on("MessageType")`, accept `**kwargs`, return the matching `call_result.*`, and log received data with `_LOGGER.debug`.
7. **Commands** — coordinator command methods return a `dict` with `success` (bool) and `message` (str); handle `asyncio.TimeoutError` and generic `Exception` separately.

## Python / Home Assistant style

- Python 3.11+; line length 88; formatted and linted by **ruff** (config in `pyproject.toml`).
- Type hints on public methods; `mypy` strict config (advisory in CI).
- `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants (typed `Final`).
- Constants (entity suffixes, config keys) live in `const.py` — no inline string literals for entity keys.
- Log via the module `_LOGGER` — **never `print()`** (ruff `T20` enforces this).
- Return `None` (not `0` / `""`) for missing sensor values.

## Testing (MANDATORY)

- Every new sensor, control, handler, or command MUST have a test in `tests/`.
- Use the `mock_coordinator`, `mock_config_entry`, `mock_wallbox_charge_point` fixtures (`tests/conftest.py`).
- Cover value, properties, `unique_id`, `None`/missing handling, availability, and error paths.
- Run with the project venv: `.venv/bin/pytest tests/ -q`.

## Git

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`.
- **No AI attribution** anywhere (commits, PRs, comments, docs). **No commits unless explicitly asked.**
- Version lives in `custom_components/bmw_wallbox/manifest.json`; releases are tagged `vX.Y.Z` and the tag must match the manifest version (enforced by `release.yml`). Add a `CHANGELOG.md` entry per release.

## Tooling quick reference

```bash
make lint      # ruff check + ruff format --check + mypy
make format    # ruff --fix + ruff format
make test      # pytest tests/ -v
make coverage  # pytest with coverage report
make check     # lint + test
```

Prefer `.venv/bin/<tool>` directly in this environment (e.g. `.venv/bin/pytest`, `.venv/bin/ruff`).
