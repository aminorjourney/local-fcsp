---
type: Requirement
title: Non-Functional Requirements
description: Constraints this integration must always respect
tags: [ha-integration, safety, hacs]
timestamp: 2026-08-12T00:00:00Z
---

# Non-Functional Requirements

## NF-01 — Poll discipline

Scan interval and API timeout must never be settable below 30 seconds. This is an empirically
observed hardware constraint (aggressive polling has produced `CF` fault codes on real units),
not an arbitrary default — do not relax it without a validated finding from `fcsp-re`.

## NF-02 — No cloud dependency

All communication stays local (device LAN, HTTPS to the FCSP's own IP). This integration never
calls FordPass, Ford's cloud APIs, or any third-party telemetry endpoint. This is the entire
reason the project exists — a regression here is a P0.

## NF-03 — HACS compliance

`manifest.json` and `hacs.json` must stay valid and internally consistent (matching
documentation/issue-tracker URLs, correct `homeassistant`/`hacs_min_version` floors, valid
`requirements` pin on `fcsp-api`). See build-log for the known drift between the two files'
documentation URLs, logged for correction.

## NF-04 — Repo hygiene

No firmware binaries, disk images, or extracted filesystem content ever get committed to this
repo — that material belongs in `fcsp-re`. Enforced via `.gitignore` (`*.img`, `*.bin`, etc.).

## NF-05 — Write operations are opt-in and fail closed

Any future (v2) capability that writes to the device — start/stop charging, current limit, V2H/
V2G activation — must default to disabled, require explicit user opt-in during config, and fail
closed (no action taken) on ambiguous or unexpected device responses. This integration must never
be the reason someone's charging session or V2H backup power behaves unexpectedly.

## NF-06 — v2 gating

No v2 (write-capable) functional requirement (see `03-functional.md`) may move from "gated" to
"in progress" without a corresponding validated finding recorded in `fcsp-re`'s build log. This
project does not re-derive protocol safety independently — it consumes `fcsp-re`'s conclusions.
