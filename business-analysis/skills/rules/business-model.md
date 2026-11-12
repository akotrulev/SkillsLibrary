---
paths:
  - "docs/business-model/**/*.md"
---

<!-- business-analysis rules v1 (2026-11-03): core. Installed by /business-analysis:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Business-model knowledge base standards

Apply these to every file you write, edit or review under `docs/business-model/`, whoever writes it: a BA session, `be-documenter`, a plan task or a person. The tag after a rule is the severity a review reports: **blocker** states something no source supports or loses a recorded decision, **major** is a gap or a broken trace that hides a cross-feature conflict, **minor** is shape or format, **nit** is wording. Flow, entity, decision, connection and interaction-map rules are separate files that load with those files. How to build each artifact, and its template, belongs to the owning skill (`business-analysis:knowledge-base` names them).

**The KB wins over its defaults.** Where this KB consistently does something another way (another folder, another id width), follow it and do not flag it.

## What the KB holds

- What the software must do and how features interact. Never code architecture, API shapes the repo already records, test bases, test cases, techniques or coverage. *major*
- A distilled model that links to its sources, never a copy of a BRD or a story. *minor*
- One artifact per thing: extend the existing flow, entity grid, decision table or connection file; never a second file for the same flow, entity or decision point. *blocker*
- No speculative backfill: write only what this task's analysis produced, or what code read this session evidences (`#observed` with its `file:line`). *major*
- Read `INDEX.md` in full, and the files it names for the ids you touch, before changing any KB file. *major*
- A change is finished only with its bookkeeping: the artifact's `INDEX.md` line (one line per artifact: link, id, relevance hook), a new entry at the **top** of `active-context.md` (1 to 3 bullets), and the single consolidated "Open questions" list there kept current. *major*
- Stable files change only when the business model does; `active-context.md` changes every session that touches the model. *minor*

## Ids and traceability

- Every artifact has an id: `AREA-`, `FLOW-`, `ENT-`, `DEC-`, `CONF-`, `EVT-`, `RX-`, `INV-` plus a number. Flow nodes are `FLOW-nnn.k`; decision rows are table-local `R1, R2…`. Never renumber an id, never reuse one after deletion. *blocker*
- Every statement cites its source: a story as `US<n>` (plus `AC<k>`), an epic as `E<n>`, otherwise the BRD section or contract path. *major*
- A feature that owns a step, transition, rule or reaction is an id with a label (`E2 booking`, `AREA-003 ordering`), with the initiative folder where two initiatives share the number (`E2 booking · 004-workshop`). A bare feature name is a traceability gap. *major*

## Annotation grammar

- `[TBD - reason]` is a known unknown awaiting a decision; `⚠️ Assumption:` is stated but unconfirmed and is resolved to a source or removed at refresh; `~~old~~ → new` keeps one generation of history inline. *minor*
- Confidence tags: `#confirmed` (sourced to a requirement or a stakeholder decision), `#inferred` (derived, unverified), `#observed` (seen in the code or the live system, in no document). *major*
- What a source does not say is `[TBD]`, `?` or an open question, never a filled-in guess. *blocker*
- Only a person promotes an entry to `#confirmed`. A code trace never writes it and never overwrites a `#confirmed` entry; a contradiction goes to `active-context.md` and is escalated. *blocker*
- `areas/<area>.md` and `system-overview.md` (owned by `dev:doc-business-model`) are the plain-language guide and carry no tags, `file:line` or code names; `<name>.behind-the-scenes.md` is plain language about how the parts connect; tags and `file:line` sit only in `<name>.technical.md`, in its evidence index. The three files of an area are one artifact: one `INDEX.md` line names all three, each carries `**Audience:**` (`shareable` on the guide, `internal` on the other two; only a person promotes one) and its own `Derived from` stamp, and when any one changes all three are re-checked and re-stamped with the same sha. *minor*

## Headers and provenance

- Every file under `areas/`, `flows/`, `entities/`, `decisions/`, and `system-overview.md`, `events.md`, `shared-data.md`, `invariants.md`, opens with `**Created:** <YYYY-MM-DD>` and `**Owned by:** <owning skill>`. Each later update adds `**Last updated:** <YYYY-MM-DD> by <skill>` beneath; the creation line is never overwritten. *minor*
- An artifact derived from code carries `**Derived from:** code by be-documenter @ <commit sha> on <YYYY-MM-DD>` beneath its header; a refresh re-verifies the citations against the current commit and re-stamps. *major*

## Writing and deciding

- Short declarative statements with their source ("Refunds allowed within 30 days (BRD §6)"), critical facts near the top of each file. *minor*
- A file nearing about 2,000 words splits by topic; a `.technical.md` file may run to about 4,000. *minor*
- Glossary terms only. A term used with two meanings is a terminology-drift finding, never a silent merge; a new term goes to `glossary.md` with its source. *major*
- Precedence, stacking operators and exclusions are business decisions: present the options, record who decided, when and why in `interaction-map.md`. Never pick one yourself. *blocker*
- Every finding names its boundary condition: the concrete scenario where it bites. Without one it is a suspicion, not a finding. *major*
