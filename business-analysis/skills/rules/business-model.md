---
paths:
  - "docs/business-model/**/*.md"
---

<!-- business-analysis rules v4 (2026-11-20): core. Installed by /business-analysis:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Business-model knowledge base standards

Apply these to every file you write, edit or review under `docs/business-model/`, whoever writes it: a BA session, `be-documenter`, a plan task or a person. The tag after a rule is the severity a review reports: **blocker** states something no source supports or loses a recorded decision, **major** is a gap or a broken trace that hides a cross-feature conflict, **minor** is shape or format, **nit** is wording. Flow, entity, decision, connection and interaction-map rules are separate files that load with those files. How to build each artifact belongs to the owning skill (`dev:knowledge-base` names them; to use one, delegate to the `business-analyst` agent, which loads it).

**The KB wins over its defaults.** Where this KB consistently does something another way, follow it and do not flag it.

## What the KB holds

- What the software must do and how features interact. Never code architecture, API shapes the repo already records, test bases, test cases, techniques or coverage. *major*
- A distilled model that links to its sources, never a copy of a BRD or a story. *minor*
- One artifact per thing: extend the existing flow, entity grid, decision table or connection file; never a second file for the same flow, entity or decision point. *blocker*
- No speculative backfill: write only what this task's analysis produced, or what code read this session evidences (`#observed` with its `file:line`). *major*
- Read `INDEX.md` in full, and the files it names for the ids you touch, before changing any KB file. *major*
- A change is finished only with its bookkeeping: the artifact's `INDEX.md` line (link, id, relevance hook), a new entry at the **top** of `active-context.md` (1 to 3 bullets), and its one consolidated "Open questions" list kept current. *major*
- Stable files change only when the business model does; `active-context.md` changes every session that touches the model. *minor*

## Ids and traceability

- Every artifact has an id: `AREA-`, `FLOW-`, `ENT-`, `DEC-`, `CONF-`, `EVT-`, `RX-`, `INV-` plus a number. Flow nodes are `FLOW-nnn.k`; decision rows are table-local `R1, R2…`. Never renumber an id, never reuse one after deletion. *blocker*
- Every statement cites its source: a story as `US<n>` (plus `AC<k>`), an epic as `E<n>`, otherwise the BRD section or contract path. *major*
- A feature that owns a step, transition, rule or reaction is an id with a label (`E2 booking`), with the initiative folder where two initiatives share the number (`E2 booking · 004-workshop`). A bare feature name is a traceability gap. *major*

## Annotation grammar

- `[TBD - reason]` is a known unknown awaiting a decision; `⚠️ Assumption:` is stated but unconfirmed and is resolved to a source or removed at refresh; `~~old~~ → new` keeps one generation of history inline. *minor*
- Confidence tags: `#confirmed` (sourced to a requirement or a stakeholder decision), `#inferred` (derived, unverified), `#observed` (seen in the code or the live system, in no document). *major*
- What a source does not say is `[TBD]`, `?` or an open question, never a filled-in guess. *blocker*
- Only a person promotes an entry to `#confirmed`. A code trace never writes it and never overwrites one; a contradiction goes to `active-context.md` and is escalated. An answer folded into a guide is not a promotion: `business-analyst` decides. *blocker*
- `areas/<area>.md` and `system-overview.md` are the plain-language guide for end users, analysts and the product owner, owned by `dev:doc-business-model` (which `be-documenter` runs): its `references/guide-shape.md` holds the sections and the stamp. They carry no tags, `file:line` or code names, and internal ids only in the closing stamp comment. A `*.behind-the-scenes.md` or `*.technical*.md` file is retired: read as a lead, deleted when its guide is next updated. *minor*

## Headers and provenance

- A guide closes with `## About this document` and one stamp comment as the last line (shape in `guide-shape.md`), which alone carries the id, owner, source sha, models, stories and audience: there is no `**Id:**`, `**Owned by:**`, `**Derived from:**`, `**Models:**` or `**Audience:**` line. A guide in an earlier shape is updated in place, never regenerated, keeping `**Created:**`, adding `**Last updated:**`, and leaving `#confirmed` statements untouched. *minor*
- Every other artifact (`flows/`, `entities/`, `decisions/`, `events.md`, `shared-data.md`, `invariants.md`) opens with its metadata block and carries `**Created:** <YYYY-MM-DD>` and `**Owned by:** <owning skill>`. Each later update adds `**Last updated:** <YYYY-MM-DD> by <skill>` beneath; the creation line is never overwritten. *minor*
- An artifact other than a guide, derived from code, carries `**Derived from:** code by be-documenter @ <commit sha> on <YYYY-MM-DD>` beneath its header; a refresh re-verifies the citations against the current commit and re-stamps (a guide's source sha is its stamp's `source:`). *major*

## Writing and deciding

- Short declarative statements with their source ("Refunds allowed within 30 days (BRD §6)"), critical facts near the top of each file. *minor*
- A file nearing about 2,000 words splits by topic (the area-guide length is in `guide-shape.md`). *minor*
- Glossary terms only. A term used with two meanings is a terminology-drift finding, never a silent merge; a new term goes to `glossary.md` with its source. *major*
- Precedence, stacking operators and exclusions are business decisions: present the options, record who decided, when and why in `interaction-map.md`. Never pick one yourself. *blocker*
- Every finding names its boundary condition: the concrete scenario where it bites. Without one it is a suspicion, not a finding. *major*
