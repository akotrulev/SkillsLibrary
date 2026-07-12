---
name: ba-state-modeler
description: Use when modeling a business entity's lifecycle (Order, Subscription, User…) as one state × event table shared across ALL features, with each transition annotated by its owning feature — persisted to the project's business-model KB. Triggers: "what states can an order be in", "model the subscription lifecycle", "which feature moves it to Cancelled", "can feature X do this while it's Archived". Do NOT use for process/step flows (ba-flow-mapper), rule tables (ba-decision-modeler), or deriving state-transition TEST cases (qa/manual/test-design-techniques owns those mechanics).
---

# BA — State Modeler

Models a business entity's lifecycle as **one state model per entity — never per feature**. Each feature's transitions are *overlaid* on the shared model and annotated with the feature that owns them. That overlay is the point: lifecycle conflicts between features are invisible when each spec keeps its own private picture of the entity, and unmissable when they all write into one grid.

**Grid over diagram.** A state table forces every *event × state* cell to be answered — legal, illegal, or unspecified. A state diagram only shows the arrows someone remembered to draw.

## When to use

- Requirements reveal an entity with a lifecycle (states, and events that move it between them)
- A new feature adds, reads, or removes entity states — overlay it on the existing model
- A conflict sweep flagged suspected state interference and needs the grid to localize it
- The user asks "what can happen to X while it's in state Y"

## When NOT to use

- Multi-step process paths between actors → `ba-flow-mapper`
- Input-combination → outcome rules → `ba-decision-modeler`
- Deriving state-transition **test cases**, n-switch coverage, transition-pair mechanics → `qa/manual/test-design-techniques` §4 owns those; this skill produces the model they consume
- An "entity" with two states and one transition — note it in the flow file instead; a grid earns its keep at ≥3 states or ≥2 features touching the lifecycle

## Contract with the KB

Per `business-analysis/skills/ba-project-knowledge`: **read first** (`INDEX.md` + the existing `entities/<entity>.md` — extending the shared model is the whole discipline; creating a second model for the same entity is the anti-pattern), **update after** (entity file + INDEX + active-context).

## Procedure

1. **Identify the entity and enumerate its states** from the requirements *and* the existing KB model. States are business-meaningful conditions ("Submitted", "Suspended"), not implementation flags. A new feature inventing a near-synonym of an existing state ("Deactivated" vs "Suspended") is terminology drift → glossary check before adding.
2. **Enumerate the events** — everything any feature does that can move the entity: user actions, system events, timeouts, lifecycle jobs (archival, cleanup, expiry — the classically forgotten writers).
3. **Fill the grid — every cell.** For each `state × event`: the target state, `—` (illegal by decision), or `?` (unspecified — a finding). Never leave a cell blank.
4. **Annotate every legal transition with its owning feature** — the feature whose requirements define it. One transition claimed by two features is a **double-fire** finding; a transition no feature owns is an orphan.
5. **Overlay the new feature** (the common case): add its events/states to the existing grid, then read the *whole* grid again — the conflicts are in the cells the new feature changed *and* the cells it silently assumed.
6. **Run the conflict-surface checklist** (below) and log findings.

## Conflict surfaces (what the grid is for)

| Surface | What it looks like in the grid | Taxonomy class |
|---|---|---|
| **Double-fire** | two features own the same `state × event` transition — or two events from different features fire on the same real-world trigger | trigger overlap |
| **State interference** | feature B's behavior requires state S; feature A has a transition out of S (or deletes the entity) with no rule for B's in-flight work | state interference |
| **Orphan transition** | a transition present in the model that no feature's requirements own — who does this? | gap |
| **Silent `—` assumption** | a new feature's flow implies a transition the grid marks `—` or `?` | contradiction / gap |
| **Unreachable / dead state** | a state with no inbound transitions, or no outbound ones that isn't terminal by decision | gap |
| **Guard conflict** | same transition, two features demand different guards ("only admin" vs "any owner") | contradictory rules / permission |

Each finding gets a **boundary condition** — the concrete scenario where it bites ("subscription expires (A) while the upgrade payment (B) is mid-capture") — and goes to `ba-feature-conflict-sweep` for the severity table + resolution recording.

## Entity file format (`docs/business-model/entities/<entity>.md`)

```markdown
# Entity — Order (ENT-001)

**Sources**: <refs> · **Features touching this lifecycle**: checkout, fulfillment, refunds, archival
**Last updated**: <date> — <one line what changed>

## States
| State | Meaning | Terminal? | Source |
|---|---|---|---|
| Draft | in cart, not submitted | no | STORY-40 |

## Transition grid
Cell = target state `(owning feature)` · `—` = illegal by decision · `?` = unspecified (finding)

| ↓ State \ Event → | submit | payment captured | refund requested | 90d inactivity |
|---|---|---|---|---|
| Draft | Submitted (checkout) | — | — | Deleted (archival) |
| Submitted | — | Confirmed (checkout) | ? | ? |
| Confirmed | — | — | Refunding (refunds) | Archived (archival) |

## Guards
| Transition | Guard | Feature | Source |
|---|---|---|---|
| Confirmed → Refunding | within 30 days of purchase | refunds | BRD §6 |

## Open questions
- ❓ ENT-001: `Submitted × refund requested` = `?` — refunds spec only covers Confirmed. [TBD - ask PO]
- ⚠️ Assumption: archival skips Submitted orders `#inferred`
```

## Quality bar

- [ ] One model per entity — the new feature was overlaid, not given its own copy
- [ ] Every `state × event` cell filled: target, `—`, or `?` — no blanks
- [ ] Every legal transition names its owning feature; double-owners and orphans flagged
- [ ] Lifecycle jobs (expiry, archival, cleanup) included as events — not just user actions
- [ ] Guards recorded with owner + source; guard conflicts flagged
- [ ] Every finding carries a boundary condition
- [ ] States are business terms, glossary-checked
- [ ] KB updated per the contract (entity file + INDEX + active-context)

## Anti-example

Bad: the refunds feature gets its own tidy three-state diagram (`Confirmed → Refunding → Refunded`) in its own spec. It never learns the archival feature moves Confirmed orders to Archived after 90 days — so "refund an archived order" ships as a production surprise. One shared grid with both features overlaid makes that cell (`Archived × refund requested = ?`) impossible to not see.

## Handoffs

- Findings → severity + resolution recording → `business-analysis/skills/ba-feature-conflict-sweep`
- A guard hides a multi-input rule set → `business-analysis/skills/ba-decision-modeler`
- The process *between* transitions → `business-analysis/skills/ba-flow-mapper`
- KB mechanics → `business-analysis/skills/ba-project-knowledge`
- State-transition test design (n-switch, transition pairs) from this model → `qa/manual/test-design-techniques`
