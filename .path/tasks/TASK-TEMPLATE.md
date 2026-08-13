---
# Every value here is filled in by `path new task`. Square-bracket placeholders
# are fine in the body below, but not up here: `[like this]` is a YAML flow
# sequence, not a blank to fill in, and a `?` inside one is a parse error.
type: Task
title:
description:
tags: []
timestamp:
path:
  id:
  status: pending
  effort:
  created:
  updated:
  completed:
  project:
  drafted_by:
  completed_by: []
  requires: []
  implements: []
  change_log: []
  drift_log: []
  issues: []
  proof:
    checked_at:
    result:
---

# [Short Descriptive Title]

## Objective

[One paragraph. What does this task accomplish? What will be true when it's done that isn't true now?]

## Context

[Background the executor needs to understand the task. Do not reproduce requirements or blueprints — link to them.]

Relevant documentation:

- [Link to relevant requirement(s)](../requirements/03-functional.md#section)
- [Link to relevant blueprint(s)](../blueprints/01-architecture.md#section)

## Prerequisites

[Prerequisite tasks belong in `path.requires`, where they are checked. Note any other condition here.]

## Scope

[What is explicitly IN scope. Be specific enough that an executor knows when they've done enough.]

### Out of Scope

[What is explicitly NOT part of this task. Prevents scope creep and clarifies boundaries.]

## Tasks

- [ ] [Task 1 — specific and actionable]
- [ ] [Task 2]

## Acceptance Criteria

- [ ] [Criterion 1 — observable, verifiable, testable, specific, and independent; a condition that confirms the work is done correctly through measurability]
- [ ] [Criterion 2]

## Validation

[The conditions that will be verified by testing, tied to the acceptance criteria. Tests should be comprehensive to the scope of the task, based on specific requirements, and should mix unit and integration patterns to validate from functions through to architecture. An error found after this task is complete is a fault in the validation, and should lead to a refinement of it.]

- [ ] [Validation 1]
- [ ] [Validation 2]

## Notes

[Anything else the executor should know: known risks, edge cases, relevant decisions from the build log, preferred approach where several are valid.]

---

*The change log, drift log, and issues found live in this task's frontmatter, not in this body. Append to them with `path log change|drift|issue` — see `blueprints/03-conventions.md`.*

*When complete, write a `RETROSPECTIVE` build log entry naming this task's id, and update `AGENTS.md`. `path check` verifies both.*
