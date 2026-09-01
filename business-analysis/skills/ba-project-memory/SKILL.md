---
name: ba-project-memory
description: Use when reading or updating a project's persistent business-model knowledge base (docs/business-model/) — the shared protocol every business-analysis skill loads before modeling flows, states, decisions, or sweeping for feature conflicts. Triggers: "read the KB before answering", "check what the KB already says about X", "initialise docs/business-model/ for this repo". Do NOT use for code/architecture memory (that's the repo's CLAUDE.md) or test artifacts (qa/*).
---

# BA — Project Knowledge (the KB protocol)

Every other `business-analysis/` skill reasons **against the whole project's business model, not just the task at hand**. That model lives as a small, versioned knowledge base in the target project. This skill defines where it lives, what goes in it, and the read/write contract — so a session that starts cold reconstructs the project's business reality from files, and every analysis leaves the model better than it found it.

The shape is a deliberate port of Cline's Memory Bank (read-all-first, update-on-trigger, stable-vs-dynamic tiers) applied to a *business domain* model instead of a coding-agent's context.

## When to use

- At the **start** of any `business-analysis/*` task — read the KB before modeling or conflict reasoning (the other skills invoke this contract; it is not optional)
- At the **end** of any analysis that changed the model — persist the changes
- Initializing the KB in a project that doesn't have one yet
- The user says "refresh / update the business model"

## When NOT to use

- Recording *how the code is built* (architecture, stack, conventions) → the project's own CLAUDE.md / docs
- Recording *test* artifacts (test bases, cases, charters) → `qa/manual/*`
- One-off analysis of a single story with no project KB and no desire for one → plain `qa/manual/requirements-breakdown`

## The KB layout

Lives **in the target repo**, versioned with the code, diffable and PR-reviewable — i.e. under the project root of whatever repo the session is actually working in (resolve `docs/business-model/` against the current working directory), **never** under this skills-library checkout or a global config directory (`~/.claude/...`), unless the user explicitly asks for a shared/global copy:

```
docs/business-model/
├── INDEX.md              # loaded first, every session — one line per artifact + relevance hook
├── glossary.md           # canonical terms; the terminology-drift defense
├── system-overview.md    # what the system is, for whom, the area map + cross-area journeys — owned by be-shared-business-documentation
├── areas/<area>.md       # one functional area per file (AREA-nnn): overview, setup, how it works, worked example, open questions, closing evidence table — owned by be-shared-business-documentation
├── flows/<flow>.md       # one business flow per file (FLOW-nnn) — owned by ba-process-flow-diagram
├── entities/<entity>.md  # one state model per business entity (ENT-nnn) — owned by ba-entity-state-grid
├── decisions/<point>.md  # one merged decision table per shared decision point (DEC-nnn) — owned by ba-decision-table
├── interaction-map.md    # known feature interactions + their resolution decisions (CONF-nnn) — owned by ba-feature-conflict-check
└── active-context.md     # dynamic tier: last sessions' changes + open questions/hotspots
```

**Two tiers:**

| Tier | Files | Changes |
|---|---|---|
| **Stable** | `glossary.md`, `system-overview.md`, `areas/`, `flows/`, `entities/`, `decisions/`, `interaction-map.md` | deliberately, when the business model actually changes |
| **Dynamic** | `active-context.md` (+ the INDEX line-items) | every session that touches the model |

## The contract

### Read-first (before any modeling or conflict reasoning)

1. `Read` **`INDEX.md`** — always, in full. If it doesn't exist, offer to initialize the KB (below) before proceeding.
2. From the INDEX, `Read` the **topic files relevant to the task**: the entities/flows/decisions the new feature touches, `glossary.md` when new terms appear, `interaction-map.md` before any conflict sweep, and `active-context.md` for open questions that may already cover the task.
3. Never reason about a feature against an empty mental model when a KB exists — an analysis that ignores the KB is wrong by construction, because the conflicts live *between* the new feature and what's already recorded.

### Update-after (part of closing the work, not an afterthought)

1. Update every **touched artifact** — new flow file, extended state table, new decision-table rows, new interaction-map entries.
2. Update **`active-context.md`**: a new session entry **at the top** (newest first — critical facts near the top applies here too), 1–3 bullets on what changed; keep **one** consolidated "Open questions" list current rather than per-session copies that go stale.
3. Update **`INDEX.md`**: add/adjust the one-line entry for anything added or materially changed.
4. New terms encountered → `glossary.md`, with the source. A term used with *two meanings* is a finding (terminology drift), not a silent merge.

### Refresh (on the explicit command "refresh the business model")

Re-read **all** files, reconcile drift against the current requirements/codebase reality the user points at, prune stale entries, and re-verify `#inferred` items. Report what changed.

## Authoring rules (apply to every artifact)

- **Size discipline.** Any file approaching ~2,000 words splits by topic; `INDEX.md` stays one line per artifact. Critical facts near the top of each file.
- **Short declarative statements**, not essays. "Refunds allowed within 30 days (BRD §6)" — not a paragraph.
- **Stable IDs + traceability.** Every artifact carries an ID (`AREA-`, `FLOW-`, `ENT-`, `DEC-`, `CONF-` + number); flow nodes are `FLOW-nnn.k`, decision-table rule rows are table-local `R1, R2…` under their `DEC-` id. Everything cites its source requirement — a story as `US<n>` (plus `AC<k>` where one criterion is meant), an epic as `E<n>`, otherwise the BRD section or contract path. IDs are never reused after deletion.
- **Feature identity.** Wherever an artifact names the feature that *owns* a transition, rule or step, the feature is an id with a label, never a bare word: the epic from the initiative that introduced it (`E2 booking`), or the area for code-derived artifacts (`AREA-003 ordering`). Two initiatives may both have an `E2`, so the label carries the initiative folder when it is not obvious (`E2 booking · 004-workshop`). A free-text feature name with no id is a traceability gap, because nothing downstream can find the story set behind it.
- **Annotation grammar** (uniform across artifacts):
  - `[TBD - reason]` — known unknown, waiting on a decision
  - `⚠️ Assumption:` — stated but unconfirmed; must be resolvable to a source or removed at refresh
  - `~~old~~ → new` — versioned change, keep one generation of history inline
  - Confidence tags: `#confirmed` (sourced to a requirement/stakeholder decision) · `#inferred` (derived by analysis, plausible but unverified) · `#observed` (seen in the implementation or the live system, not in any doc)
- **Record decisions with rationale.** A conflict resolution in `interaction-map.md` is a *business decision* — record who/what decided and why, not just the outcome.
- **Skip what the repo already records.** Code structure, API shapes derivable from contracts in-repo, git history. The KB records what the software must *do* and how features *interact* — nothing else.
- **Header on every artifact file.** Each `areas/<area>.md`, `flows/<flow>.md`, `entities/<entity>.md`, `decisions/<point>.md` file (and `system-overview.md`) opens with `**Created:** <YYYY-MM-DD>` and `**Owned by:** \`<the owning skill>\`` (e.g. `ba-process-flow-diagram`; `be-shared-business-documentation` for `areas/` and `system-overview.md`); on every later update, add `**Last updated:** <YYYY-MM-DD> by \`<skill>\`` beneath it rather than overwriting the creation line.

## INDEX.md format

```markdown
# Business Model — <Project>

Read this file first, every session. One line per artifact; read the ones your task touches.

## Areas
- [Ordering](areas/ordering.md) — AREA-003; place/cancel/track orders; actors: customer, support agent · derived from code
## Entities
- [Order](entities/order.md) — ENT-001; lifecycle Draft→…→Refunded; owners: checkout, fulfillment, refunds
## Flows
- [Checkout](flows/checkout.md) — FLOW-001; happy path + payment-failure/timeout branches
## Decisions
- [Order pricing](decisions/order-pricing.md) — DEC-001; hit policy C+ (stacking); contributed by promos, loyalty, shipping
## Cross-cutting
- [Glossary](glossary.md) — canonical terms; "customer" ≠ "account" here
- [Interaction map](interaction-map.md) — 4 resolved conflicts, 1 open (CONF-005)
- [System overview](system-overview.md) — 6 areas, 3 cross-area journeys; 2 areas not yet documented
- [Active context](active-context.md) — last touched 2026-07-12; 3 open questions
```

## Initializing a KB

When no `docs/business-model/` exists and the user wants one:

1. Confirm the path (default `docs/business-model/`; respect an existing docs convention if the project has one).
2. Create `INDEX.md`, `glossary.md`, `active-context.md`, `interaction-map.md` with headers and empty sections — plus the `areas/`, `flows/`, `entities/`, `decisions/` directories.
3. Do **not** backfill the whole model speculatively. The KB accretes as features are analyzed; seed it only with what the current task's analysis actually produces.

**The one exception — evidence-based backfill from code.** The `be-documenter` agent deliberately populates the KB in bulk by reading an existing implementation. That does not violate the rule above, because the rule forbids *speculation*, not *volume*: every statement it writes is `#observed` with a `file:line` read that session, or `#inferred` and simultaneously raised as an open question. In `areas/` documents those tags and citations sit in the **closing evidence table** rather than inline — the body reads as a product spec (overview · setup · how it works · worked example · open questions) — but the tag per statement is still mandatory there. It never writes `#confirmed` — promotion is a human act — and it never overwrites a `#confirmed` entry, since a human's confirmation outranks a trace. See `backend/_shared/business-documentation`.

## Provenance — telling generated from hand-authored

An artifact derived from code rather than from requirements carries, beneath its header:

```markdown
**Derived from:** code by `be-documenter` @ `<commit sha>` on YYYY-MM-DD
```

Without it a generated `#inferred` line is indistinguishable from a business decision someone actually made — and the whole value of the KB is that a reader can tell which is which. On refresh, re-verify the citations against the current commit and re-stamp; a `file:line` that has silently drifted is worse than none, because it still looks checkable.

## Anti-example

Bad: a session models a new refund feature, finds it collides with the loyalty-points flow, resolves it in chat — and writes nothing. The next session re-derives (or misses) the same conflict. The KB exists precisely to make that impossible.

Also bad: dumping the full BRD into `flows/` verbatim. The KB is a distilled model with traceability links back to sources — not a copy of them.

## Handoffs

- Build/extend a flow → `business-analysis/skills/ba-process-flow-diagram`
- Build/extend an entity state model → `business-analysis/skills/ba-entity-state-grid`
- Build/extend a decision table → `business-analysis/skills/ba-decision-table`
- Sweep a new/changed feature against the model → `business-analysis/skills/ba-feature-conflict-check`
- Orchestrate the whole loop → `business-analysis/agents/business-analyst`
- Populate the KB from an existing backend implementation (areas, system overview, and the evidence behind the flows/entities/decisions) → the `be-documenter` agent and `backend/_shared/business-documentation`
- Distill one story for testing (consumes these artifacts as test basis) → `qa/manual/requirements-breakdown`
