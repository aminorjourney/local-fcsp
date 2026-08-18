---
type: Task
title: 'Add config-flow reconfigure support for host/port/devkey'
description: ''
tags: [v2, config-flow, ux]
timestamp: 2026-08-17T00:00:00Z
path:
  id: T-002
  status: pending
  effort: 2
  created: 2026-08-17
  updated: 2026-08-17
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

# Add config-flow reconfigure support for host/port/devkey

## Objective

Let a user change an existing config entry's `host`, `port`, or `devkey` in the HA UI, without
deleting and re-adding the integration. Today `host`/`port`/`devkey` are write-once — set only in
`async_step_user` at initial setup — and `OptionsFlowHandler` never exposes them. Changing any of
the three currently means remove + re-add, which mints a new `entry_id` and therefore new
unique_ids ([sensor.py](../../custom_components/local_fcsp/sensor.py) and
[binary_sensor.py](../../custom_components/local_fcsp/binary_sensor.py) both key `unique_id` off
`entry_id`), breaking any dashboard, automation, or history tied to the old entity IDs.

## Context

Surfaced directly from real use: TranquilityBase gained a second, more stable IP
(`192.168.20.66`, Ethernet, vs. the flaky `192.168.20.65` WiFi it was originally configured with —
see `fcsp-re`'s `AGENTS.md` Unit Naming section and Finding 20). Wanting to just point the
existing config entry at the new IP surfaced that there's currently no in-place way to do that at
all.

Relevant code:

- [config_flow.py](../../custom_components/local_fcsp/config_flow.py) — `async_step_user` (lines
  31-81) sets `host`/`port`/`devkey` once; `OptionsFlowHandler` (lines 87-143) only ever exposed
  `scan_interval`/`timeout`/`debug`/`time_format`.
- [__init__.py](../../custom_components/local_fcsp/__init__.py) — reads `host`/`devkey`/`port`
  from `entry.data` at `async_setup_entry`, so a reconfigure needs to trigger a reload of the
  entry afterward for the new values to actually take effect.

Not gated on any `fcsp-re` finding — this is a pure `local-fcsp`/Home Assistant config-flow UX
gap, unrelated to write-capability gating (NF-06). No dependency on F-07/F-08/F-09/F-10.

## Prerequisites

None. Independent of T-001 and of any `fcsp-re` gating.

## Scope

- Implement `async_step_reconfigure` (HA's standard reconfigure-flow hook) on `ConfigFlow`,
  pre-filled with the entry's current `host`/`port`/`devkey`, reusing the same validation already
  in `async_step_user` (devkey non-empty, etc.).
- On successful reconfigure, update the entry's data and trigger a reload
  (`async_update_reload_and_abort` or equivalent) so `__init__.py`'s `FCSP(...)` client picks up
  the new values without requiring a manual HA restart.
- Add a "Reconfigure" affordance reachable from the integration's entry in Settings → Devices &
  Services (HA surfaces this automatically once `async_step_reconfigure` exists).

### Out of Scope

- Changing `unique_id`/device-identifier scheme — this task exists specifically to avoid touching
  those; `entry_id` stays stable across a reconfigure.
- Any change to `OptionsFlowHandler`'s existing fields (`scan_interval`, `timeout`, `debug`,
  `time_format`) — those already work today via Options, untouched by this task.
- Auto-discovery of a device that moved IPs (e.g. via mDNS/zeroconf) — this task is purely "let the
  user manually re-enter connection details," not automatic detection of a changed address.

## Tasks

- [ ] Add `async_step_reconfigure` to `ConfigFlow` in `config_flow.py`, prefilled from
      `self._get_reconfigure_entry().data`.
- [ ] Reuse `async_step_user`'s validation logic (devkey required) rather than duplicating it.
- [ ] On success, call HA's reconfigure-completion helper to update entry data and reload the
      entry.
- [ ] Confirm `async_setup_entry` in `__init__.py` correctly re-reads the updated `host`/`devkey`/
      `port` on that reload (no stale client left over from the old connection).
- [ ] Update `README.md` if it documents the setup/config flow, to mention reconfigure is now
      possible.

## Acceptance Criteria

- [ ] From Settings → Devices & Services, an existing Local FCSP entry offers a reconfigure
      option.
- [ ] Changing `host` via reconfigure connects to the new address without deleting/recreating the
      entry — same `entry_id`, same entity unique_ids/entity_ids, same history, before and after.
- [ ] Changing `devkey` via reconfigure takes effect on the next poll without requiring a manual HA
      restart.
- [ ] Reconfigure form's validation matches initial setup (empty devkey rejected, etc.).

## Validation

- [ ] Set up a test entry, reconfigure its `host` to a second reachable address, confirm sensors
      keep their existing entity IDs and history continues on the same graphs/logbook.
- [ ] Reconfigure with an invalid `host` (unreachable), confirm a clear error rather than a broken
      silent state.
- [ ] Reconfigure `devkey` to an intentionally wrong value, confirm the entry surfaces a connection
      error rather than silently failing.

## Notes

Real-world trigger for this task: switching TranquilityBase's configured IP from its original WiFi
address to a newer, more stable Ethernet one, and finding no way to do that short of remove/
re-add. See `fcsp-re`'s Finding 20 for the unrelated device-firmware fix that made the Ethernet IP
usable at all — this task is purely the `local-fcsp`-side follow-on gap that surfaced during that
work, not a continuation of it.

---

*The change log, drift log, and issues found live in this task's frontmatter, not in this body. Append to them with `path log change|drift|issue` — see `blueprints/03-conventions.md`.*

*When complete, write a `RETROSPECTIVE` build log entry naming this task's id, and update `AGENTS.md`. `path check` verifies both.*
