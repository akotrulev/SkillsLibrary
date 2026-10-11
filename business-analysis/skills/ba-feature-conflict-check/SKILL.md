---
name: conflict-check
description: Use when checking a new or changed feature against the WHOLE project's business model for conflicts — normalize into trigger/actor/action/data/constraint/state tuples, sweep pairwise against the KB with the 11-class taxonomy; every finding gets a boundary condition. Triggers: "does this feature conflict with anything", "sweep this story against the model", "cross-feature impact check". Do NOT use for single-doc ambiguity flagging (`requirements-breakdown`) or scoping (`scoping`).
---

# BA — Feature Conflict Sweep

The quality gate of the `business-analysis/` family: takes a **new or changed feature** and sweeps it **pairwise against the persisted project model**, asking a fixed taxonomy of conflict questions per pair. The classic feature-interaction lesson (telecom's call-waiting × call-forwarding) applies to every product: two features, each correct alone, collide at a shared trigger, state, or resource — and the right resolution is a **business decision**, not a technical default. This skill's job is to surface each collision *at requirements time* with the concrete scenario where it bites, then get the decision made and **recorded**.

Without the KB there is nothing to sweep against — the value scales with what previous sessions persisted.

## When to use

- A new feature/story arrives in a project with a business-model KB — before it's built or test-designed
- An existing feature changes (new rule, new state, new trigger)
- Periodic audit: "sweep the whole model for unresolved interactions"
- Another `business-analysis` skill logged conflict-shaped findings that need severity + resolution

## When NOT to use

- No KB and no wish for one — single-story flagging is `qa/manual/requirements-breakdown`
- The input is a vague, unscoped initiative rather than concrete requirements — scope it first with `business-analysis/skills/ba-scoping-writeup`
- The conflict is already visible and localized — go straight to the owning model skill
- Code-level dependency/impact analysis — this is requirements-level

## Contract with the KB

Per `business-analysis/skills/ba-project-memory`: **read first** — `INDEX.md`, `interaction-map.md` (don't re-litigate resolved conflicts), `glossary.md`, and every flow/entity/decision file the new feature plausibly touches. **Update after** — findings and resolutions into `interaction-map.md`, plus `active-context.md` + INDEX.

## Procedure

> **Audit form (no new feature).** On the "periodic audit / refresh the model" trigger there is no feature to normalize, so **§1 is skipped** and the pair list (§2) is the KB's own **open surface** rather than a feature × KB cross: unresolved `CONF-` entries, `?` cells in entity grids, `[TBD]`/undeclared hit policies in decision tables, and unverified `#inferred` items. §3 (taxonomy), §4 (boundary condition per finding), and §5 (severity table + recorded resolutions) are unchanged. Pair the refresh procedure in `business-analysis:knowledge-base` first (reconcile drift, prune, re-verify `#inferred`), then sweep that open surface.

### 1. Normalize the new feature

Decompose each of its requirements into one comparison tuple — the same six elements for every requirement, so two features' requirements can be compared element by element:

| Element | Meaning |
|---|---|
| **trigger** | the event/condition that fires it ("on order submit", "when total ≥ $100", "nightly") |
| **actor** | who/what performs it |
| **action** | what it does (+ mode: does / must-not / may) |
| **data in / out** | what it reads and writes |
| **constraints** | restrictions on it (frequency, window, amount, role) |
| **state touched** | entity states it reads, sets, or removes |

Also classify each requirement as **behavior**, **invariant** (a global "always/never" axiom), or **resource** claim (quota, budget, slot, lock) — invariant- and resource-mediated conflicts are invisible if you only compare behaviors to behaviors.

Glossary-check every term during normalization: a term used differently than `glossary.md` defines it is finding material *before* any pair is compared.

### 2. Build the pair list

New feature's tuples × the KB: features sharing a **trigger**, touching the same **entity/states**, writing into the same **decision point**, consuming the same **resource**, or adjacent on a flow's **event timeline**. Everything else is a non-pair — don't brute-force the full cross product; the KB's structure prunes it.

### 3. Sweep each pair with the taxonomy

| # | Class | The question per pair |
|---|---|---|
| 1 | **Contradictory rules** | do they demand incompatible outcomes on the same trigger/entity? |
| 2 | **Trigger overlap / double-fire** | can one event satisfy both features' conditions, with precedence undefined? |
| 3 | **State interference** | does A move an entity into/out of a state B depends on (incl. mid-flight)? |
| 4 | **Resource contention** | do both consume a shared quota/budget/slot/lock, with no combined-load rule? |
| 5 | **Ordering / race** | does the outcome depend on which runs first, with requirements silent on order? |
| 6 | **Circular dependency** | does A's action trigger B whose action re-triggers A (or circular data flow)? |
| 7 | **Policy stacking** | do two benefits/penalties combine on one transaction with no combination rule? |
| 8 | **Permission / authority** | do role composition or entity-vs-member state give contradictory access answers? |
| 9 | **Duplication / subsumption** | does one requirement quietly contain or override the other? |
| 10 | **Terminology drift** | same word, different meaning — false agreement between the specs? |
| 11 | **Boundary divergence** | jointly unsatisfiable only in an edge region (both fire at exactly the threshold)? |

### 4. Boundary condition per finding — mandatory

Every finding states the **concrete scenario where the two features collide**: "customer redeems loyalty points (B) on an order at exactly $100.00 (A's free-shipping threshold, computed *post*-discount → total drops to $87 → does shipping revert?)". A finding without a boundary condition is a suspicion, not a finding. Boundary conditions double as BVA seeds for QA.

**Escalation tools** when a pair needs deeper analysis (the selection matrix): outcome-per-combination unclear → merge into a decision table (`business-analysis:decision-table`); lifecycle unclear → extend the entity grid (`business-analysis:state-grid`); paths/timeouts unclear → the flow (`business-analysis:process-flow`); **timing/interleaving between actors** → a Mermaid `sequenceDiagram` of that specific boundary scenario — the one place sequence diagrams are used, as an investigation tool, not a default artifact.

### 5. Report — the severity table

Standard CLAUDE.md review format, typed by kind:

```
| Severity | Kind | Pair | Finding (+ boundary condition) | Resolution needed |
|----------|------|------|--------------------------------|-------------------|
| blocker  | conflict  | promos × loyalty (CONF-006) | both discount the same order, no stacking rule; at $100 + 20% + 500pts the total is ambiguous | business decision: stack (operator?) or best-offer-wins |
| major    | gap       | refunds × archival (CONF-007) | refund on an Archived order unspecified; order archived on day 91, refund window is 90d — but paid-return edge… | define behavior for Archived × refund |
| minor    | ambiguity | promos (—) | "total" pre- vs post-discount per glossary | confirm + glossary update |
```

- **blocker** = ships a wrong outcome on a realistic scenario · **major** = will bite soon / blocks test design · **minor** = ambiguity with a cheap fix · **nit** = wording/glossary hygiene.
- **Resolution is the business's, not yours.** Present the options (priority, exclusion, merge, operator); when the user decides, record the decision *with rationale* in `interaction-map.md`. Never silently auto-resolve; an unresolved finding stays open in `active-context.md`.

## Interaction-map entry format

```markdown
## CONF-006 — promotions × loyalty-points: stacking undefined  `#resolved`
- **Class**: policy stacking (7) · **Severity**: blocker
- **Boundary condition**: order $100.00, 20% promo + 500 loyalty pts — combined outcome undefined
- **Resolution (2026-07-12, PO)**: best-offer-wins, no stacking; DEC-001 hit policy → P, promo priority > loyalty. Why: finance forbids double-discounting.
- **Pair**: E5 promotions × E6 loyalty · **Sources**: US88, US102 · **Artifacts updated**: decisions/order-pricing.md
```

## Quality bar

- [ ] KB read first — including `interaction-map.md` (no re-litigating resolved conflicts, no missing that a "new" conflict is a resolved one violated)
- [ ] New feature normalized into tuples; behavior/invariant/resource classified; glossary-checked
- [ ] Pair list justified by shared trigger/state/decision/resource/timeline — not vibes, not brute force
- [ ] All 11 taxonomy questions asked per pair (a "none found" sweep says so per class, not by omission)
- [ ] Every finding has a concrete boundary condition
- [ ] Findings in the severity table; resolutions escalated as business decisions, recorded with rationale
- [ ] KB updated (interaction-map + active-context + INDEX)

## Anti-example

Bad: reading the new story alone and listing its internal ambiguities — that's `requirements-breakdown`'s job, and it finds nothing *between* features. Also bad: "these might conflict somehow" with no boundary condition, or quietly deciding the promo wins because it "seems right" — undecided precedence is the finding; inventing the decision destroys it.

## Handoffs

- Deeper analysis of a pair → `business-analysis:decision-table` / `business-analysis:state-grid` / `business-analysis:process-flow` per the escalation matrix
- KB mechanics → `business-analysis/skills/ba-project-memory`
- Findings resolved → the feature is ready for `qa/manual/requirements-breakdown` (boundary conditions = BVA seeds) and `qa/manual/agents/qa-test-case-designer`
- Full orchestration → `business-analysis/agents/business-analyst`
