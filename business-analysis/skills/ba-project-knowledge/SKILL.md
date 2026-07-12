---
name: ba-project-knowledge
description: Use when reading or updating a project's persistent business-model knowledge base (docs/business-model/) — the shared protocol every business-analysis skill loads before modeling flows, states, decisions, or sweeping for feature conflicts. Triggers: "set up the business model KB", "read the project's business model first", "update the business model with what we learned", "refresh the business model". Do NOT use for code/architecture memory (that's the repo's CLAUDE.md) or test artifacts (qa/*).
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
- One-off analysis of a single story with no project KB and no desire for one → plain `qa/manual/test-basis-analyzer`

## The KB layout

Lives **in the target repo**, versioned with the code, diffable and PR-reviewable:

```
docs/business-model/
├── INDEX.md              # loaded first, every session — one line per artifact + relevance hook
├── glossary.md           # canonical terms; the terminology-drift defense
├── flows/<flow>.md       # one business flow per file (FLOW-nnn) — owned by ba-flow-mapper
├── entities/<entity>.md  # one state model per business entity (ENT-nnn) — owned by ba-state-modeler
├── decisions/<point>.md  # one merged decision table per shared decision point (DEC-nnn) — owned by ba-decision-modeler
├── interaction-map.md    # known feature interactions + their resolution decisions (CONF-nnn) — owned by ba-feature-conflict-sweep
└── active-context.md     # dynamic tier: last sessions' changes + open questions/hotspots
```

**Two tiers:**

| Tier | Files | Changes |
|---|---|---|
| **Stable** | `glossary.md`, `flows/`, `entities/`, `decisions/`, `interaction-map.md` | deliberately, when the business model actually changes |
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
- **Stable IDs + traceability.** Every artifact carries an ID (`FLOW-`, `ENT-`, `DEC-`, `CONF-` + number); flow nodes are `FLOW-nnn.k`, decision-table rule rows are table-local `R1, R2…` under their `DEC-` id. Everything cites its source requirement (story ID, BRD section, contract path). IDs are never reused after deletion.
- **Annotation grammar** (uniform across artifacts):
  - `[TBD - reason]` — known unknown, waiting on a decision
  - `⚠️ Assumption:` — stated but unconfirmed; must be resolvable to a source or removed at refresh
  - `~~old~~ → new` — versioned change, keep one generation of history inline
  - Confidence tags: `#confirmed` (sourced to a requirement/stakeholder decision) · `#inferred` (derived by analysis, plausible but unverified) · `#observed` (seen in the live system, not in any doc)
- **Record decisions with rationale.** A conflict resolution in `interaction-map.md` is a *business decision* — record who/what decided and why, not just the outcome.
- **Skip what the repo already records.** Code structure, API shapes derivable from contracts in-repo, git history. The KB records what the software must *do* and how features *interact* — nothing else.

## INDEX.md format

```markdown
# Business Model — <Project>

Read this file first, every session. One line per artifact; read the ones your task touches.

## Entities
- [Order](entities/order.md) — ENT-001; lifecycle Draft→…→Refunded; owners: checkout, fulfillment, refunds
## Flows
- [Checkout](flows/checkout.md) — FLOW-001; happy path + payment-failure/timeout branches
## Decisions
- [Order pricing](decisions/order-pricing.md) — DEC-001; hit policy C+ (stacking); contributed by promos, loyalty, shipping
## Cross-cutting
- [Glossary](glossary.md) — canonical terms; "customer" ≠ "account" here
- [Interaction map](interaction-map.md) — 4 resolved conflicts, 1 open (CONF-005)
- [Active context](active-context.md) — last touched 2026-07-12; 3 open questions
```

## Initializing a KB

When no `docs/business-model/` exists and the user wants one:

1. Confirm the path (default `docs/business-model/`; respect an existing docs convention if the project has one).
2. Create `INDEX.md`, `glossary.md`, `active-context.md`, `interaction-map.md` with headers and empty sections — plus the three directories.
3. Do **not** backfill the whole model speculatively. The KB accretes as features are analyzed; seed it only with what the current task's analysis actually produces.

## Anti-example

Bad: a session models a new refund feature, finds it collides with the loyalty-points flow, resolves it in chat — and writes nothing. The next session re-derives (or misses) the same conflict. The KB exists precisely to make that impossible.

Also bad: dumping the full BRD into `flows/` verbatim. The KB is a distilled model with traceability links back to sources — not a copy of them.

## Handoffs

- Build/extend a flow → `business-analysis/skills/ba-flow-mapper`
- Build/extend an entity state model → `business-analysis/skills/ba-state-modeler`
- Build/extend a decision table → `business-analysis/skills/ba-decision-modeler`
- Sweep a new/changed feature against the model → `business-analysis/skills/ba-feature-conflict-sweep`
- Orchestrate the whole loop → `business-analysis/agents/business-analyst`
- Distill one story for testing (consumes these artifacts as test basis) → `qa/manual/test-basis-analyzer`
