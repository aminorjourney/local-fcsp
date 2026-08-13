---
type: Blueprint
title: Architecture
description: How local-fcsp is built, and how v1/v2 coexist
tags: [ha-integration]
timestamp: 2026-08-12T00:00:00Z
---

# Architecture

## System design

```
Home Assistant
  └─ custom_components/local_fcsp/   (this repo)
       __init__.py       — entry setup, wires coordinator + cache
       config_flow.py     — host/devkey/port/timeout/scan-interval UI
       coordinator.py      — single DataUpdateCoordinator, 4 GET/POST endpoints per poll
       cache.py            — last-known-good data, survives HA restarts
       sensor.py            — per-field sensor entities (charge station + HIS devices)
       binary_sensor.py    — online status, grid/power-cut style sensors
       const.py             — DOMAIN, DEFAULT_DEVKEY (public/shared), poll-interval floors
            │
            ▼  pip dependency, pinned fcsp-api>=0.1.3,<0.2
       fcsp_api (Eric Pullen's library, external)
            │
            ▼  local HTTPS REST, port 443, shared dev-key auth, no cloud
       Ford Charge Station Pro (Siemens-manufactured hardware)
            │
            ▼  (present only if a Home Integration System is installed)
       Delta-built HIS inverter — vendor/model/firmware surfaced via inverter_info
```

Two HA devices are registered: the charge station itself, and — conditionally, only when a real
inverter is detected (`coordinator.real_inverter_connected`) — the Home Integration System.

## Key decisions

- **Single shared coordinator.** Fixed in v0.3.5 after a duplicate-coordinator bug meant sensor
  attributes never populated. `sensor.py` must never instantiate its own coordinator again.

- **Four endpoints, not six.** `get_status()` and `get_device_summary()` are excluded — both
  re-fetch data the other four endpoints already provide, doubling network traffic for no new
  information.

- **Never poll side-effecting endpoints.** WiFi scan and BLE pairing are POST requests with
  device-side effects and must never be called from the polling loop, only from an explicit,
  user-initiated future action (if ever).

- **v1/v2 live in the same repo, gated by readiness, not by branch.** Rather than splitting into
  a permanent `v2` branch that drifts from `main`, v2 functional requirements
  (`requirements/03-functional.md`, F-07 through F-10) are documented now but their PATH tasks
  stay unopened until a corresponding `fcsp-re` finding exists. When a finding lands:
  1. Read the relevant `fcsp-re` build-log / findings entry.
  2. Open a task here referencing it by path/URL in Context (PATH's `requires` field only tracks
     same-project task IDs — cross-project dependencies are recorded in prose, in both the task's
     Context section and this file if the dependency is architecturally significant).
  3. Implement behind an opt-in config option (see NF-05), never as a default-on change.
  This keeps `main` always shippable and keeps the "what's proven vs what's speculative" line
  visible in the requirements themselves rather than buried in branch state.

- **This project does not do its own reverse engineering.** Anything requiring packet capture,
  disk image analysis, or experimentation against undocumented endpoints happens in
  [`fcsp-re`](../../../fcsp-re/AGENTS.md), on a bench unit. This repo only implements against
  findings already written down and validated there.
