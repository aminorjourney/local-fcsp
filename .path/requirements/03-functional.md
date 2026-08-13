---
type: Requirement
title: Functional Requirements
description: v1 shipped behavior and v2 gated capability
tags: [ha-integration]
timestamp: 2026-08-12T00:00:00Z
---

# Functional Requirements

## v1 — Shipped (read-only, `2026.4.0`)

### F-01

Config flow collects host, dev-key, port, poll interval, API timeout, debug flag, and time
format; enforces a minimum 30s scan interval and 30s API timeout to avoid destabilizing the FCSP
(short polling has been observed to cause `CF` fault codes on-device).

### F-02

A single shared `DataUpdateCoordinator` polls four FCSP endpoints per cycle — charger info,
inverter info, config status, network info — and derives all sensor state from those four
responses. `get_status()` and `get_device_summary()` are deliberately not polled (redundant with
the above). WiFi-scan and BLE-pairing endpoints are never polled automatically — both are POST
requests with device-side side effects.

### F-03

Individual HA sensor entities (not attribute blobs) are exposed for charger status, hardware/
firmware versions, serial number, network info, and — where a real inverter is present — inverter
model/vendor/firmware/state, grouped under two HA devices: the charge station itself and the Home
Integration System.

### F-04

The integration detects the FCSP's placeholder inverter response (`vendor="Supreme Electronics"`,
`model="Star"`) and suppresses HIS entity creation entirely for standalone installs with no real
inverter attached, rather than exposing dummy sensors.

### F-05

A grid-status-style sensor derives power-cut / grid-connected state from the HIS inverter state
field, with a fallback path for older FCSP firmware that reports inverter state as text rather
than a numeric code.

### F-06

Last-known-good data is cached locally so HA shows real data immediately on restart rather than
"unavailable" while waiting for the first poll.

## v2 — Gated on `fcsp-re` findings (not started)

These are documented now so scope is visible, but **none of these tasks are ready to start**
until the linked `fcsp-re` work has produced a validated finding. See
`blueprints/01-architecture.md` for the gating mechanism.

### F-07 (gated)

Local write support for start/stop charging, once `fcsp-re` documents the control-plane protocol
and confirms it can be exercised safely from a third-party client without risking the unit or the
vehicle.

### F-08 (gated)

Local write support for adjustable current limit, same gating as F-07.

### F-09 (gated)

BLE-free V2H/V2G activation via the CCS-based channel, once `fcsp-re` validates that PLC/CCS
signaling alone can trigger V2H/V2G without Ford's BLE pairing flow (`fcsp-re` F-04).

### F-10 (gated)

Any hardening changes `fcsp-re` validates on the bench unit (e.g. rotating the shared dev-key,
disabling unneeded services) that have a corresponding change required in this integration's
config flow or defaults (e.g. `const.py`'s `DEFAULT_DEVKEY`).
