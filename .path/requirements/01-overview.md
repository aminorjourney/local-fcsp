---
type: Requirement
title: Overview
description: Local, cloud-free Home Assistant integration for the Ford Charge Station Pro
tags: [ha-integration, hacs, v1-stable]
timestamp: 2026-08-12T00:00:00Z
---

# Overview

## What this is

`local-fcsp` is a Home Assistant custom integration (HACS domain `local_fcsp`) that polls a
Ford Charge Station Pro (FCSP) — and, where present, its attached Delta-built Home Integration
System (HIS) inverter — entirely over the local network. It wraps [Eric Pullen's `fcsp-api`]
(https://github.com/ericpullen/fcsp-api) Python library, which talks to the FCSP's local HTTPS
REST API (port 443, shared/public dev-key auth), and surfaces the data as native HA sensor and
binary-sensor entities.

Today (**v1**, currently released as `2026.4.0`) it is **read-only**: charger status, V2H/IBP
state, network info, and raw debug JSON. It does not start/stop charging, adjust current limits,
or touch BLE/V2H/V2G activation.

## Why it exists

Ford's own path for this hardware runs through the FordPass cloud app and (for V2H/V2G) a BLE
pairing flow that is unreliable and offline-fragile. Owners with Home Assistant want visibility
into — and eventually control of — their charge station and V2H setup without a round trip to
Ford's servers, and without depending on BLE working correctly.

`local-fcsp` is the **consumer-facing half** of a two-project effort:

- **`local-fcsp`** (this project) — the HACS-distributed HA integration. Small, stable,
  read-only today. Anything it does must be safe to run against a live, production FCSP powering
  someone's home.
- **[`fcsp-re`](../../../fcsp-re/AGENTS.md)** — a sibling research project doing the actual protocol
  reverse engineering, firmware/security analysis, and BLE-removal work on a bench unit. This
  project consumes `fcsp-re`'s documented, validated findings — it does not do its own RE.

**Current phase decision:** feature work on control/write capability in this integration is
**paused** until `fcsp-re` has mapped and validated the relevant protocol surface. See
`blueprints/01-architecture.md` for how v1/v2 are tracked side by side.
