---
name: knowledge-base
description: Use when reading or updating the business-model knowledge base (docs/business-model/) before any BA modeling. Triggers "read the KB first". Not for the connection map (dependency-map).
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
├── system-overview.md    # what the system is, for whom, the area map + cross-area journeys — owned by dev:doc-business-model
├── areas/<area>.md       # one functional area per file (AREA-nnn): overview, setup, how it works, worked example, open questions, closing evidence table — owned by dev:doc-business-model
├── flows/<flow>.md       # one business flow per file (FLOW-nnn) — owned by business-analysis:process-flow
├── entities/<entity>.md  # one state model per business entity (ENT-nnn) — owned by business-analysis:state-grid
├── decisions/<point>.md  # one merged decision table per shared decision point (DEC-nnn) — owned by business-analysis:decision-table
├── events.md             # triggers and reactions (EVT-, RX-) — owned by business-analysis:dependency-map
├── shared-data.md        # CRUD matrix + shared fields — owned by business-analysis:dependency-map
├── invariants.md         # what must always hold (INV-) — owned by business-analysis:dependency-map
├── interaction-map.md    # known feature interactions + their resolution decisions (CONF-nnn) — owned by business-analysis:conflict-check
└── active-context.md     # dynamic tier: last sessions' changes + open questions/hotspots
```

**Two tiers:**

| Tier | Files | Changes |
|---|---|---|
| **Stable** | `glossary.md`, `system-overview.md`, `areas/`, `flows/`, `entities/`, `decisions/`, `events.md`, `shared-data.md`, `invariants.md`, `interaction-map.md` | deliberately, when the business model actually changes |
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

## Authoring standards

The standards every KB file must meet (what the KB holds, ids and traceability, feature identity, the annotation grammar, headers, provenance, recording decisions) are the business-analysis rule files, not a list here: `business-model.md` for every file under `docs/business-model/`, plus `business-model-flows.md`, `business-model-entities.md`, `business-model-decisions.md`, `business-model-connections.md` and `business-model-interactions.md` for those files. Read the project's copy in `.claude/rules/business-analysis/`, or the plugin's in `business-analysis/skills/rules/` when the project has not installed them (`/business-analysis:rules` does). Where they and this skill disagree, the rule files win. Installed, they load in any session that touches the KB, so a plan task or `be-documenter` editing a KB file keeps it consistent without loading this skill.

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
## Dependencies
- [Events & reactions](events.md) — 7 triggers, 7 reactions; 1 unconsumed event, 2 reactions with `?` failure
- [Shared data](shared-data.md) — 2 entities, 2 shared fields
- [Invariants](invariants.md) — INV-001…INV-004; 3 not enforced or unknown
## Cross-cutting
- [Glossary](glossary.md) — canonical terms; "customer" ≠ "account" here
- [Interaction map](interaction-map.md) — 4 resolved conflicts, 1 open (CONF-005)
- [System overview](system-overview.md) — 6 areas, 3 cross-area journeys; 2 areas not yet documented
- [Active context](active-context.md) — last touched 2026-07-12; 3 open questions
```

## Feature slice

The slice is the set of connections that matter for one feature. The input is an owner id (`E<n>`, `AREA-nnn`) or a trigger id (`EVT-nnn`). It is eight lookups, each a grep, because every row carries ids under the feature-identity rule.

| # | Lookup | Where | What it yields |
|---|---|---|---|
| 1 | Own triggers and reactions | `events.md`, rows with *Owner* = id | What can start this feature, and what it does |
| 2 | Downstream | follow *Emits* → reactions whose *When* is that event, repeated | What it sets off in other features |
| 3 | Upstream | other owners' reactions whose *Emits* reach this feature's reactions | Who else can start it |
| 4 | States depended on | for each `ENT` transition this feature makes, the target state's row in the grid | Other owners' triggers that are legal in that state, plus every `—` and `?` in the row |
| 5 | Decisions | `decisions/` files this feature contributes rows to | The other contributors' rows |
| 6 | Shared data | `shared-data.md` rows naming this feature's reactions | The other writers and readers |
| 7 | Invariants | `invariants.md` rows whose *Threatened by* includes this feature's reactions | What it can break, and whether it guards against it |
| 8 | Known interactions | `interaction-map.md` entries with this feature in *Pair* | Resolved and open conflicts, each with its boundary condition |

**Depth:** two hops past the feature's own reactions. Go further where an effect moves money or cannot be undone. `business-analysis:conflict-check` uses the slice as its pair list when the map exists. QA reads it through `qa/manual/requirements-breakdown/references/connections.md`.

## Initializing a KB

When no `docs/business-model/` exists and the user wants one:

1. Confirm the path (default `docs/business-model/`; respect an existing docs convention if the project has one).
2. Create `INDEX.md`, `glossary.md`, `active-context.md`, `interaction-map.md` with headers and empty sections (`events.md`, `shared-data.md` and `invariants.md` are created by `business-analysis:dependency-map` on first use) — plus the `areas/`, `flows/`, `entities/`, `decisions/` directories.
3. Do **not** backfill the whole model speculatively. The KB accretes as features are analyzed; seed it only with what the current task's analysis actually produces.
4. Offer `/business-analysis:rules`, so the KB's standards load in every later session that edits it.

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
- Build/extend the triggers, reactions, shared data and invariants → `business-analysis/skills/ba-dependency-map`
- Sweep a new/changed feature against the model → `business-analysis/skills/ba-feature-conflict-check`
- Orchestrate the whole loop → `business-analysis/agents/business-analyst`
- Populate the KB from an existing backend implementation (areas, system overview, and the evidence behind the flows/entities/decisions) → the `be-documenter` agent and `backend/_shared/business-documentation`
- Distill one story for testing (consumes these artifacts as test basis) → `qa/manual/requirements-breakdown`
