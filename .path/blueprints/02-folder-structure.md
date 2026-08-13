---
type: Blueprint
title: Folder Structure
description: Repo layout and what belongs where
tags: [ha-integration]
timestamp: 2026-08-12T00:00:00Z
---

# Folder Structure

## Layout

```
local-fcsp/
  AGENTS.md                          # PATH entry point
  .path/                             # requirements, blueprints, tasks, build-log (this system)
  README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE
  hacs.json, bump_version.sh
  custom_components/
    local_fcsp/
      __init__.py
      config_flow.py
      coordinator.py
      cache.py
      sensor.py
      binary_sensor.py
      const.py
      manifest.json
      translations/en.json
```

## What does *not* live here

- **Disk images / firmware dumps** (e.g. `FCSP_20260812.img`) — moved to the sibling
  [`fcsp-re`](../../../fcsp-re/) project's `images/` directory (git-ignored there too; never
  committed anywhere). This repo is HACS-distributed and must stay small and clean of binary
  research artifacts. Enforced by `.gitignore` (`*.img`, `*.bin`, `*.img.gz`).
- **Protocol research, packet captures, RE findings** — live in `fcsp-re/findings/` and
  `fcsp-re/captures/`. This repo links to them from task Context sections rather than
  reproducing them.
- **A permanent `v2/` folder or branch** — see `blueprints/01-architecture.md` for why v2 scope
  is tracked as gated PATH tasks in the same tree instead.

## Origin note

This repo's git history was previously hosted with a working copy that had drifted from what was
actually tagged/released (`2026.4.0`) on GitHub — the canonical remote. That drift was resolved by
resetting to the released state on 2026-08-12; see the build log for detail. `origin` now points
at `github.com/Aminorjourney/local-fcsp` (canonical, HACS-facing); `forgejo` is a second remote
used for day-to-day development pushes.
