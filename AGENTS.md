# local-fcsp — AI Navigation Guide

`local-fcsp` is a HACS-distributed Home Assistant custom integration for the Ford Charge Station
Pro (FCSP): local, cloud-free polling of charger and Home Integration System (Delta inverter)
status. It currently ships **v1: read-only** (`2026.4.0`). Write/control capability (v2) is
deliberately paused — gated on findings from the sibling
[`fcsp-re`](../fcsp-re/AGENTS.md) reverse-engineering project. See
`.path/requirements/01-overview.md` and `.path/blueprints/01-architecture.md` for the full
picture and the gating mechanism.

## How to Navigate This Project

| Need | Location |
|------|----------|
| What it does and why | `.path/requirements/01-overview.md` |
| Who uses it and how | `.path/requirements/02-user-stories.md` |
| Functional requirements | `.path/requirements/03-functional.md` |
| Non-functional requirements | `.path/requirements/04-non-functional.md` |
| System architecture | `.path/blueprints/01-architecture.md` |
| Folder structure | `.path/blueprints/02-folder-structure.md` |
| Document conventions | see the Path repository's `blueprints/03-conventions.md` |
| Task template | `.path/tasks/TASK-TEMPLATE.md` |
| Decision and build history | `.path/build-log/` |

## Executing a Task

1. Read this file first for orientation.
2. Read the referenced task in `.path/tasks/`.
3. Follow the Context links in the task to read the relevant requirements and blueprints.
4. Complete every item in the task's task list.
5. Verify all acceptance criteria before marking complete.
6. Write a `RETROSPECTIVE` build log entry naming the task id, and update this file.
7. Run `path check T-NNN` — it verifies the completion claim mechanically.

## Available Commands

Path is a single command on `$PATH`. This project contains no Path code.

```bash
path status                  # project status and task queue
path check [T-NNN]           # proof of done: validate a task, or the whole project
path metrics                 # burn-up, volatility, drift — read from frontmatter
path new task "<title>" --effort N
path task start|block|complete T-NNN
path log change|drift|issue T-NNN "<note>"
path close                   # session-close entry, then regenerate status.html
```

## Current Task

None assigned. See `.path/tasks/` for available tasks.

## Project Status

**Phase:** v1 stable/shipped (`2026.4.0`, read-only); v2 paused pending validated `fcsp-re` findings.
**Last updated:** 2026-08-12

## Global Profile

If `$LCP_HOME` is set, read `$LCP_HOME/profile/index.md` (or run `path profile`) for the
project owner's working preferences. **Anything in this repository overrides it.**

Standing order: when you learn something true of the project owner, not this project —
a working preference, a stack default, a personal convention — persist it immediately
with `path profile add <doc> "<text>"` (`doc`: identity, working-style, conventions, or
stack). Never hand-edit the profile files.
