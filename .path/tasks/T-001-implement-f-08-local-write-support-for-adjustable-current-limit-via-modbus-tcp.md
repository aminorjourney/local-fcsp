---
type: Task
title: 'Implement F-08: local write support for adjustable current limit via Modbus/TCP'
description: ''
tags: [v2, modbus, write-capability]
timestamp: 2026-08-17T01:05:32Z
path:
  id: T-001
  status: pending
  effort: 5
  created: 2026-08-16
  updated: 2026-08-16
  completed: null
  project: local-fcsp
  drafted_by: Human
  completed_by: []
  requires: []
  implements: []
  change_log: []
  drift_log: []
  issues: []
  proof:
    checked_at: null
    result: null
---

# Implement F-08: local write support for adjustable current limit via Modbus/TCP

## Objective

Add an opt-in HA `number` entity that lets a user set the FCSP's charging current ceiling locally,
via Modbus/TCP (`SYSTEM_POWER_LEVEL`, register 73), instead of only through FordPass. Disabled by
default; when enabled, writes fail closed and never leave the entity showing a value that wasn't
actually confirmed on the device.

## Context

- [F-08](../requirements/03-functional.md#f-08-gated) — the functional requirement this implements.
- [NF-05](../requirements/04-non-functional.md#nf-05--write-operations-are-opt-in-and-fail-closed) —
  opt-in, fail-closed.
- [NF-06](../requirements/04-non-functional.md#nf-06--v2-gating) — this task exists *because* the
  gating finding below now exists; do not treat this as license to also start F-07/F-09/F-10, which
  remain gated on their own separate findings.
- [Architecture](../blueprints/01-architecture.md) — single shared coordinator, never poll
  side-effecting endpoints automatically. A write triggered by this entity is user-initiated, not
  part of the poll cycle, and must not be folded into the existing `DataUpdateCoordinator`.
- **Cross-project finding this is gated on** (PATH's `requires` only tracks same-project task IDs,
  recorded here in prose per that convention):
  [`fcsp-re` Finding 17](../../../fcsp-re/findings/17-modbus-tcp-write-path-validated.md) — validates
  the write path live, and documents a real protocol quirk this implementation must account for:
  **the device's TCP server only accepts function code 16 (Write Multiple Registers) for writes,
  even for a single register.** A naive client using function code 6 (single write) will get
  `IllegalFunction` back. Any Modbus client library used here (e.g. `pymodbus`) must call its
  "write multiple" method, not "write single," regardless of writing just one register.
- [`fcsp-re` Finding 18](../../../fcsp-re/findings/18-full-register-scan-only-two-live-registers.md)
  — a full scan of every address in the Demand Response, System Status, and Device Control blocks
  found **only two live registers on this unit**: `SYSTEM_POWER_LEVEL` (73) and `DELAY_STATUS` (74).
  This settles two things definitively, not provisionally: **F-07 (start/stop) has no Modbus path
  on this unit at all** (`PAUSE_STATUS` is confirmed absent, not just unconfirmed), and there is no
  bonus read-only telemetry available from Modbus beyond what the REST API already provides. This
  task's scope — current limit only — is not an arbitrary v1 slice of a larger opportunity; per
  Finding 18, it is currently the *entire* opportunity this protocol offers on this unit.

## Prerequisites

None blocking — Finding 17 already exists and is validated. Nothing in this repo currently touches
Modbus at all, so this is greenfield within `local-fcsp`.

## Scope

- A `ModbusClient` wrapper (new module, e.g. `modbus_client.py`) that talks to the FCSP's own
  `502/tcp`, encapsulating the FC16-for-writes quirk so no call site can accidentally use FC6.
- Config flow: a new opt-in step/toggle (default off) to enable Modbus write support, only shown/
  usable if the toggle is on. Do not add a Modbus host/port field distinct from the FCSP's existing
  configured host — same device, same LAN, just a different port (502).
- One `number` entity: current limit, exposed as amps in the UI (convert to/from the device's
  20-100% `SYSTEM_POWER_LEVEL` scale internally). Min/max amps must derive from this unit's actual
  rated ceiling, not be hardcoded to 80A — `RATED_AMPS` itself lives in the Modbus password-
  protected config range (out of reach, and out of scope to even attempt), so pull the ceiling from
  wherever the existing REST API already surfaces it (check `fcsp-api`'s device info fields before
  assuming it's unavailable), or a manual config-flow field as a fallback if it genuinely isn't
  exposed anywhere.
- Write behavior: write, then immediately read back to confirm (matches Finding 17's tested
  pattern) before updating the entity's displayed state. On any exception, Modbus error response,
  or a read-back mismatch, leave the entity showing its last-confirmed value and log an error — the
  device's actual state is the source of truth, not what the user requested.
- Rate-limit writes at the entity level (debounce rapid slider changes). **Not just prudent —
  confirmed load-bearing**: [`fcsp-re` Finding 19](../../../fcsp-re/findings/19-power-level-write-flash-persistence-traced.md)
  traced every genuinely-different `SYSTEM_POWER_LEVEL` write to an immediate, unbatched flash file
  write (`/home/root/wifi/power2`, real eMMC). An undebounced slider dragged through ten
  intermediate values is ten flash writes. Writing the *same* value as current is confirmed free
  (short-circuited on-device before any file touch) — but don't rely on that path instead of simply
  not writing when the value hasn't changed; simpler and unambiguous.

### Out of Scope

- F-07 (start/stop) — per Finding 18, `PAUSE_STATUS` is **confirmed absent** from this unit's live
  Modbus map (not merely unconfirmed). There is currently no known Modbus path to F-07 on this
  unit. Would need new evidence (different firmware, different unit/model, or some undiscovered
  enable step) before this is worth reopening — not a "todo," a settled dead end for now.
- `PAUSE_STATUS` for any purpose — dead per Finding 18, and would have been separately hard to
  validate even if live: unlike `SYSTEM_POWER_LEVEL` (a passive ceiling, valid to read/write
  regardless of charging state), pause/stop is only meaningful during an active charging session —
  worth remembering if a future unit/firmware ever does expose it.
- `DELAY_STATUS` (74) — live, reads `0`, but purpose unknown and not investigated. Not part of this
  task; flagged in Finding 18 as an open question for a future session, not something to guess at
  or write to here.
- Any "extra telemetry" ambition beyond `SYSTEM_POWER_LEVEL`, **for now** — Finding 18's scan found
  nothing else live over TCP. Correction on that finding (2026-08-17): the scan only tested TCP; a
  third-party forum report over RS485/RTU shows real charging-status/current-draw/max-rate data on
  the same Demand Response block TCP shows as dead. Genuinely promising, genuinely untested on our
  own hardware — RTU needs `/dev/ttyO2`, contended by `bpt_application` on the live unit, so this
  stays out of scope for T-001 specifically until tested on an uncontended bench unit (Second Base,
  gated on `fcsp-re` T-023). Don't scope entities against it yet; do keep it in mind as the likely
  next real expansion once that's safe to test.
- RTU/serial Modbus — TCP only; this project has no reason to touch `/dev/ttyO2`.
- Anything in the password-protected config range or the RFID block — not just unimplemented,
  explicitly never in scope regardless of technical reachability (factory calibration and
  access-control key material, respectively — see Finding 17's register-map breakdown).
- F-09/F-10 — separate gated requirements, unrelated to this task.

## Tasks

- [ ] Add `pymodbus` (Python 3, HA's runtime — not the device's Python 2 version referenced in
      Finding 17) to `manifest.json` requirements, pinned appropriately.
- [ ] Build `modbus_client.py`: connect/read/write wrapper, FC16-only writes, read-back-to-confirm
      helper, clear exceptions distinguishing "device said no" from "couldn't reach device."
- [ ] Extend `config_flow.py` with the opt-in toggle (default off) and, if needed, the rated-amps
      fallback field.
- [ ] Add `number.py` (new platform file, matching the existing per-platform file convention) for
      the current-limit entity, percent-to-amp conversion, debounce, fail-closed update logic.
- [ ] Wire entity registration into `__init__.py` behind the config flow's opt-in flag — entity
      must not exist at all (not just be disabled) when the user hasn't opted in.
- [ ] Update `README.md`'s FAQ (`Can I change the current limit?`) to reflect the new capability,
      once it's real.

## Acceptance Criteria

- [ ] With the opt-in toggle off (default), no current-limit entity exists in HA at all.
- [ ] With it on, the entity's initial value matches a live read of `SYSTEM_POWER_LEVEL` converted
      to amps, not a cached/assumed value.
- [ ] Changing the entity writes via FC16, reads back to confirm, and only then reflects the new
      value — verified against the live reference unit (Tranquility Base), matching Finding 17's
      exact write/read-back/revert test pattern.
- [ ] A forced write failure (e.g. wrong port, device unreachable) leaves the entity showing its
      last-confirmed value, not the requested-but-unconfirmed one, and logs clearly.
- [ ] Rapid successive changes (e.g. dragging a slider) do not produce a write per intermediate
      value — debounced to a single write per settled value.

## Validation

- [ ] Manual test against Tranquility Base (no bench unit currently available — Second Base is
      gated on `fcsp-re` T-023). Repeat Finding 17's exact sequence through the HA entity itself,
      not a raw script: read, write to a new value, confirm entity reflects it, revert.
- [ ] Config flow test: toggle off → on, entity appears; toggle on → off, entity disappears.
- [ ] Error-path test: point the client at an unreachable port/host temporarily, confirm fail-closed
      behavior (no state change, clear log entry) rather than a stuck or incorrect displayed value.
- [ ] Confirm no change to existing v1 read-only behavior — this must be additive only.

## Notes

- The FC16-vs-FC6 quirk (Finding 17) is the single most likely source of a confusing bug if missed
  — a generic Modbus library's "write single register" convenience method will silently produce an
  `IllegalFunction` response, not a normal error, if not routed through the "write multiple" call.
- **Project owner's explicit direction: the HA-facing entity must speak real amps, never raw
  percent.** `SYSTEM_POWER_LEVEL` on the wire is 20-100%; the entity's `native_unit_of_measurement`
  is amps, `native_min_value`/`native_max_value`/`native_step` are amp values, and every read/write
  converts through `amps = round(percent / 100.0 * rated_amps)` /
  `percent = round(amps / rated_amps * 100.0)` at the boundary. No percent value should ever reach
  the HA entity layer or a user-facing attribute — percent is purely `ModbusClient`'s wire format,
  fully hidden by the conversion layer described above. On Tranquility Base specifically, rated
  ceiling is 80A (confirmed separately, not via Modbus — see below), so 100% ↔ 80A, current value
  100% ↔ 80A.
- Percent-to-amp conversion depends on the unit's actual rated ceiling, which varies by
  installation (not all units are 80A) — do not hardcode 80A as a global constant.
- No bench unit is currently available for this work (Second Base gated on `fcsp-re` T-023) — all
  live testing during this task happens against Tranquility Base, the project owner's own live,
  in-service unit, with the same care Finding 17's original test used (read-back-and-revert
  pattern, avoid testing while a vehicle is actively charging).
- This is the first Modbus-anything in `local-fcsp` — the `ModbusClient` wrapper built here is
  likely the right foundation for any future F-07-style capability too, once that has its own
  validated finding, rather than a one-off tied only to this entity.

---

*The change log, drift log, and issues found live in this task's frontmatter, not in this body. Append to them with `path log change|drift|issue` — see `blueprints/03-conventions.md`.*

*When complete, write a `RETROSPECTIVE` build log entry naming this task's id, and update `AGENTS.md`. `path check` verifies both.*
