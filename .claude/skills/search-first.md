---
name: search-first
description: Research-before-coding workflow. Read the docs and search for existing handlers, commands, entities, and constants before writing custom code.
---

# Search First — Research Before You Code

## When to Use

- Starting a new sensor, control, OCPP handler, or coordinator command.
- When asked to "add X" and you're about to write code.
- Before introducing a new dependency or a new abstraction.

## Workflow

1. **NEED ANALYSIS** — Define exactly what data/behavior is needed.
2. **READ THE DOCS** — This project is documentation-first. Read the relevant file(s) in `custom_components/bmw_wallbox/docs/`:
   - Adding a sensor → `ENTITIES.md`, `DATA_SCHEMAS.md`, `CONSTANTS.md`
   - Adding a control → `ENTITIES.md`, `COORDINATOR.md`
   - Adding an OCPP handler → `OCPP_HANDLERS.md`, `PATTERNS.md`
   - Adding an outgoing command → `COORDINATOR.md`, `PATTERNS.md`, `CONTEXT.md`
3. **SEARCH THE CODEBASE** (in this order):
   a. `const.py` — is there already a constant/suffix/key?
   b. `coordinator.py` — is there an existing handler (`@on(...)`) or command method that does most of this?
   c. `sensor.py` / `binary_sensor.py` / `button.py` / `switch.py` / `number.py` — an existing entity or base class to extend?
   d. `coordinator.data` fields (see `DATA_SCHEMAS.md`) — is the value already tracked?
   e. Home Assistant core — is there a built-in device class / unit / entity mixin for this?
   f. The `ocpp` library — is there an existing `call` / `call_result` / datatype for the message?
4. **EVALUATE** — Extend an existing pattern vs. add new. Prefer extending the established base classes and the coordinator command shape.
5. **IMPLEMENT** — Follow the step-by-step template from the matching doc; add the constant, the data field, the extraction, the entity/command, and the test.

## Decision Matrix

| Signal                                            | Action                                             |
| ------------------------------------------------- | -------------------------------------------------- |
| Value already in `coordinator.data`               | **Reuse** — just add an entity reading it          |
| Existing base class fits (`BMWWallboxSensorBase`) | **Extend** — subclass and set attributes           |
| Similar handler/command exists                    | **Mirror** — copy the pattern, adjust the message  |
| Genuinely new OCPP message / behavior             | **Build** — from the doc template, with a test     |

## Anti-Patterns

- **Jumping to code** without reading the relevant `docs/` file.
- **Storing state on an entity** instead of in `coordinator.data`.
- **Inline string keys** instead of a `Final` constant in `const.py`.
- **New OCPP call without a timeout** or without checking `charge_point` / `current_transaction_id`.
- **Reinventing** a base class or command shape that already exists.
