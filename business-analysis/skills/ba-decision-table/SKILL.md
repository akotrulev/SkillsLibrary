---
name: ba-decision-table
description: Use when a business decision point is touched by rules from one or more features — build ONE merged DMN-style decision table per decision point with a declared hit policy, run completeness and overlap checks, persist to the KB. Triggers: "what price does this order pay", "do these discounts stack", "which rule wins when both match". Do NOT use for process flows (`ba-process-flow-diagram`), entity lifecycles (`ba-entity-state-grid`), or decision-table TEST design.
---

# BA — Decision Modeler

Models each **shared decision point** — one question the business must answer ("what price does this order pay?", "is this user eligible?") — as **one merged decision table with rules contributed by *all* features that touch it**. Per-feature specs each answer the question for their own slice; conflicts between the slices hide in the seams. Merged into one table, two mechanical checks turn those seams into findings:

- **Completeness** — an input combination no rule matches = a **gap**. The spec is silent there; the prose hid it, the table can't.
- **Overlap** — two rules matching the same combination with different outputs = a **contradiction**, unless a declared hit policy resolves it.

Overlap/completeness checking **is** conflict detection. That's the whole reason this skill exists.

## When to use

- Requirements contain ≥2 rules bearing on the same outcome (a decision node in a flow with multiple inputs; "if X then A, if Y then B" prose)
- A new feature adds rules to a decision point another feature already touches (promos + loyalty + shipping all writing into "order price")
- Benefits/penalties can combine and no one has said how (stacking)
- A conflict sweep flagged contradictory rules and needs them tabled to localize

## When NOT to use

- Single-rule decisions with no foreseeable second contributor — a line in the flow's steps table suffices
- Process paths → `ba-process-flow-diagram`; lifecycles → `ba-entity-state-grid`
- Deriving **test cases** from a decision table (rule coverage, collapsed tables) → `qa/manual/test-design-techniques` owns those mechanics; this skill produces the table they consume

## Contract with the KB

Per `business-analysis/skills/ba-project-memory`: **read first** (`INDEX.md` + the existing `decisions/<point>.md` — new rules join the existing merged table; a second table for the same decision point is the anti-pattern), **update after** (decision file + INDEX + active-context).

## Hit policies (DMN semantics, markdown form — declare one per table)

The hit policy is the table's declared rule about **multiple matches**. Choosing it forces the precedence/stacking decision the feature-interaction problem demands — and the absence of a needed one is itself a finding.

| Policy | Meaning | When to reason with it |
|---|---|---|
| **Unique (U)** | no two rules may overlap | **default authoring target** — every overlap found while building is a latent conflict to resolve, not to paper over |
| **Any (A)** | overlap allowed only if outputs are identical | detects redundant/duplicated rules across features (subsumption) |
| **First (F)** | rules evaluated top-down, first match wins | order IS a business decision — if the business never stated the order, that's the finding |
| **Priority (P)** | declared priority among outputs wins | same, with explicit priorities instead of row order |
| **Collect (C, C+, C<, C>, C#)** | all matches combine via an aggregation operator (list, sum, min, max, count) | **stacking policies** — discounts, fees, limits. The operator IS the stacking rule; two benefit-granting features writing into one Collect table with no declared operator = the missing-stacking-rule conflict |

**Rules of use:**
- Author toward **U**. Escalate to F/P only when the business has *actually decided* precedence (record the source); escalate to C only when combination is *actually intended* (record the operator and its source).
- A needed-but-undeclared precedence or operator is a **business decision to escalate**, never a technical default to invent. `[TBD - needs business decision]` in the table header, finding filed.

## Procedure

1. **Name the decision point** and its output(s) ("order shipping cost: money"). One table = one question.
2. **Collect every contributing rule from every feature** — the KB's existing table plus the new feature's requirements. Tag each rule row with its owning feature + source.
3. **Enumerate the inputs** and their value ranges/partitions. Inputs must be glossary-checked (two features using "total" differently — pre- vs post-discount — is terminology drift that fakes agreement).
4. **Build the merged table**; declare the hit policy.
5. **Run the completeness check**: sweep the input-combination space (collapse with `-` don't-cares); every combination matching no rule → a **gap** finding with the concrete combination as its boundary condition.
6. **Run the overlap check**: every pair of rules that can match the same combination → identical outputs (redundancy/subsumption finding, mark for merge) or different outputs (**contradiction** finding unless the declared hit policy resolves it — and if the policy was invented rather than sourced, it doesn't resolve anything).
7. **Log findings** and update the KB.

## Decision file format (`docs/business-model/decisions/<point>.md`)

```markdown
# Decision — Order shipping cost (DEC-002)

**Question**: what shipping does an order pay? **Output**: money
**Hit policy**: F (business decided: free-shipping beats flat-rate — BRD §5.1)
**Contributed by**: shipping (STORY-31), promotions (STORY-88)
**Last updated**: <date> — <one line what changed>

## Inputs
| Input | Type | Partitions | Glossary |
|---|---|---|---|
| order_total | money | <$100 · ≥$100 | post-discount total (glossary: "total") |
| promo_free_ship | bool | true · false | |

## Rules
| # | order_total | promo_free_ship | → shipping | Feature | Source |
|---|---|---|---|---|---|
| R1 | ≥$100 | - | $0 | shipping | STORY-31 AC2 |
| R2 | - | true | $0 | promotions | STORY-88 AC1 |
| R3 | <$100 | false | $5.99 | shipping | STORY-31 AC1 |

## Checks
- Completeness: ✅ all combinations covered (R1–R3)
- Overlap: R1×R2 overlap at (≥$100, true) — outputs identical ($0) → benign; policy F resolves order anyway

## Open questions
- ❓ DEC-002: is "total" pre- or post-discount for the $100 threshold? Sources disagree. [TBD] ⚠️ Assumption: post-discount `#inferred`
```

## Quality bar

- [ ] One merged table per decision point — new rules joined the existing table
- [ ] Hit policy declared, **sourced to a business decision** (or `[TBD]` + finding, never invented)
- [ ] Every rule row tagged with owning feature + source
- [ ] Inputs glossary-checked; partitions explicit
- [ ] Completeness check run — every gap filed with its concrete input combination
- [ ] Overlap check run — every contradiction filed; redundancies marked for merge
- [ ] Collect tables name their aggregation operator with a source
- [ ] KB updated per the contract (decision file + INDEX + active-context)

## Anti-example

Bad: promotions' spec says "promo code gives free shipping", shipping's spec says "orders over $100 ship free", and each keeps its own table. Both fire on a $120 order with a code — harmless here (both say $0), but the same structure with a *percentage discount* and a *loyalty discount* silently double-discounts, or worse, each spec assumes it wins. Merging into one table forces the question at authoring time: hit policy? operator? — and "nobody has decided" becomes a filed finding instead of a production incident.

Also bad: noticing the overlap and quietly picking First-match order yourself. Precedence is a business decision; invent nothing.

## Handoffs

- Findings → severity + resolution recording → `business-analysis/skills/ba-feature-conflict-check`
- The decision sits inside a process → `business-analysis/skills/ba-process-flow-diagram`
- Rule guards touch entity states → `business-analysis/skills/ba-entity-state-grid`
- KB mechanics → `business-analysis/skills/ba-project-memory`
- Decision-table test design (rule coverage) from this table → `qa/manual/test-design-techniques`
