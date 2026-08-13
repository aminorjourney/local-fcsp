---
type: Requirement
title: User Stories
description: Who uses local-fcsp and what they need from it
tags: [ha-integration]
timestamp: 2026-08-12T00:00:00Z
---

# User Stories

## Who uses this, and how

- **As an FCSP owner running Home Assistant**, I want live charger status, connectivity, and
  device info as native sensors, so I can build dashboards and automations without depending on
  FordPass or Ford's cloud being reachable.

- **As an FCSP owner with a Home Integration System (Delta inverter) installed**, I want to see
  IBP (Intelligent Backup Power) state and grid status locally, so I can trigger automations
  (e.g. notifications, load shedding) the moment a power cut is detected — not whenever FordPass
  next syncs.

- **As an FCSP owner *without* a Home Integration System**, I want the integration to correctly
  detect that no real inverter is attached and *not* create phantom/dummy HIS entities.

- **As a maintainer of this integration**, I want a stable, minimal-surface-area v1 that stays
  HACS-compliant and safe to run unattended on production units, so that ongoing RE work on
  `fcsp-re` never has to worry about breaking someone's live charger.

- **As a future user (post-RE)**, I want local control — start/stop charging, current limit,
  eventually BLE-free V2H/V2G activation — once `fcsp-re` has proven the underlying protocol is
  safe to act on. I do not want to be an unwitting beta tester for unvalidated write operations
  against my only home charger.

- **As a contributor**, I want to know at a glance whether a given capability is "v1: shipped and
  safe" or "v2: gated on RE findings" so I don't propose PRs for functionality this project has
  deliberately deferred.
