# BMW Wallbox — Home Assistant Integration

Home Assistant custom integration for BMW EV wallboxes using **OCPP 2.0.1**.

**Key concept:** Home Assistant acts as the OCPP **server (CSMS)** — the wallbox connects TO Home Assistant, not the other way around.

## Documentation-first

Read the relevant doc in `custom_components/bmw_wallbox/docs/` **before** changing coordinator/entity/OCPP logic:

| Doc | Read when |
|-----|-----------|
| `CONTEXT.md` | First-time orientation |
| `ARCHITECTURE.md` | Component relationships, data flow |
| `COORDINATOR.md` | Coordinator API, adding commands |
| `ENTITIES.md` | Adding/modifying sensors, buttons, numbers, switches |
| `OCPP_HANDLERS.md` | Adding handlers for OCPP message types |
| `PATTERNS.md` | Decision trees, best practices, anti-patterns |
| `DATA_SCHEMAS.md` | `coordinator.data` structure, config schema |
| `CONSTANTS.md` | Naming conventions for constants |
| `ENERGY_SENSORS.md` | Energy tracking, period counters |
| `TESTING.md` | Writing tests, available fixtures |
| `TROUBLESHOOTING.md` | Debugging common problems |

## Core files

| File | Purpose |
|------|---------|
| `coordinator.py` | **Core.** OCPP server, message handlers (`WallboxChargePoint`), charging commands (`BMWWallboxCoordinator`) |
| `const.py` | Constants, entity suffixes, config keys (`Final`-typed) |
| `sensor.py` / `binary_sensor.py` | Sensor entities |
| `button.py` / `switch.py` / `number.py` | Control entities |
| `config_flow.py` / `__init__.py` | Configuration UI / entry point |

## Critical rules

1. **EVCC-style control** — pause/resume via `SetChargingProfile` (limit `0A` to pause, restore to resume). **Never `RequestStopTransaction`** (stuck transaction states).
2. **Transaction required** — `SetChargingProfile` (tx_profile) needs an active transaction; check `self.current_transaction_id` first.
3. **All state in the coordinator** — entities read `self.coordinator.data.get(...)`; never store mutable state on the entity. Return `None` for missing values.
4. **Timeouts everywhere** — wrap every OCPP `call(...)` in `asyncio.wait_for(..., timeout=15.0)`; handle `asyncio.TimeoutError` and generic `Exception` separately.
5. **Refresh after updates** — after mutating `coordinator.data`, call `self.coordinator.async_set_updated_data(self.coordinator.data)`.
6. **Log via `_LOGGER`** — never `print()` (ruff `T20`).
7. Coordinator command methods return a `dict` with `success` (bool) and `message` (str).

## Development

Prefer the project venv directly (`.venv/bin/...`):

```bash
.venv/bin/ruff check custom_components/ tests/        # lint (blocks CI)
.venv/bin/ruff format custom_components/ tests/       # format
.venv/bin/mypy custom_components/bmw_wallbox          # types (advisory in CI)
.venv/bin/pytest tests/ -q                            # tests
```

Or via Make: `make lint`, `make format`, `make test`, `make coverage`, `make check`.

**Tests are mandatory** for every new sensor, control, handler, or command — use the `mock_coordinator` / `mock_config_entry` fixtures in `tests/conftest.py`.

## Git & releases

- Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`).
- **No AI attribution** anywhere. **No commits unless explicitly asked.**
- Releases: bump `custom_components/bmw_wallbox/manifest.json`, add a `CHANGELOG.md` entry, tag `vX.Y.Z` (the tag must match the manifest version — enforced by `release.yml`).

## Claude Code setup (`.claude/`)

- **Hooks** — auto `ruff format` + `ruff check` after edits; warn on `print()`/`breakpoint()`; block edits to secrets/keys; block `git --no-verify`.
- **Agents** — `code-reviewer`, `silent-failure-hunter` (Bash/Read/Grep/Glob, preload `general`/`security`/`testing` skills).
- **Commands** — `/verify`, `/code-review`, `/plan`, `/pre-pr`, `/build-fix`, `/security-review`, `/save-session`, `/resume-session`.
- **Skills** — `general`, `testing`, `security`, `search-first`, `strategic-compact`.

`.claude/settings.local.json` (personal permissions) and `.claude/agent-memory/` are gitignored.
