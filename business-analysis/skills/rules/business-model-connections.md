---
paths:
  - "docs/business-model/{events,shared-data,invariants}.md"
---

<!-- business-analysis rules v1 (2026-11-03): connections. Installed by /business-analysis:rules; edit to fit this project. -->

# Connection-file standards (events, shared data, invariants)

Severity tags as in the core business-model rules: **blocker**, **major**, **minor**, **nit**. The KB wins where it consistently does otherwise. Templates and checks are `business-analysis:dependency-map`'s. QA reads these files as data, so the vocabularies below are closed.

- One `events.md`, `shared-data.md` and `invariants.md` per KB; new rows join them. *major*
- Trigger Kind is `command`, `schedule` (Fired by names the schedule and its timezone, or `?`), `timeout`, `external` or `event` (Fired by lists the emitting `RX-` ids). *major*
- Every reaction fills When, Guard, Owner, Effects, Emits, Mode, On failure and Source. *major*
- Effects use only `ENT-nnn From → To`, `DEC-nnn`, `Entity.field +n | −n | := v` or `creates <Entity>`, and `notifies <who>`, separated by `;`. No prose. *major*
- Mode is `in request`, `after commit, <at-least-once | at-most-once | exactly-once | ?>`, `scheduled`, or `best effort` with the decision that accepts loss. On failure is `rolls back`, `retried <n>× then <dead-letter | alert | drop>`, `compensates: <what>`, `unhandled` or `?`; the last two, and a `?` mode, are findings. *major*
- Every entity-grid column is a trigger here; every `event` trigger has a reaction or `terminal by decision`; every reaction's When is fired by something; a reaction cycle with no breaking guard is a circular-dependency finding. *major*
- A CRUD row only for an entity two or more features touch; a shared-field row only for a field with two writers, or a writer and a reader in different features. Cells are `RX-` ids or a plainly named human reader; a schedule's selection is a read; an empty cell is `by decision (<source>)` or a finding. *minor*
- Each invariant (an always/never or a resource limit) lists every reaction that writes its fields, with Enforced per reaction as `yes (<how>)`, `no` or `?`; the last two are findings. *major*
- An edge the source is silent on is `[TBD - source silent]`, never a guessed `yes` or `in request`. *blocker*
