---
name: be-shared-business-documentation
description: Use when traced backend behavior must be written up as business documentation a non-engineer can read, into the docs/business-model/ knowledge base under ba-project-memory's contract — one simple document per functional area in a fixed shape (overview · scope · setup parameters · how it works as triggers → numbered steps → formulas · a full worked example with real numbers · open questions · a closing file:line evidence table tiered #observed / #inferred). Triggers "write up what this system does for users", "turn this trace into business documentation". Do NOT use to trace the code first (`be-shared-feature-trace`), author requirements (`requirements-author`), or write findings (`ep-feature-audit`).
---

# Business Documentation — the write-up a non-engineer can use

The last mile, and the one where reverse documentation usually fails: turning accurate technical evidence into something a product manager, support lead, or new stakeholder can actually read — without inventing anything the evidence does not support.

Three disciplines carry the whole skill:

1. **Write in the user's words, not the code's.** The reader does not know what a handler is. "An order cannot be cancelled once it has shipped" — never "`CancelOrderHandler` throws when `status == Shipped`".
2. **Never let inference pass as fact — but keep the grammar out of the prose.** `#observed` is what the code does; `#inferred` is what you think it is for. Both tiers, and every `file:line`, live in the **closing evidence table** — the body reads like a product spec. In the body an inferred purpose is written as uncertainty ("appears to exist so that…"), and every inferred purpose is *also* a row in the open-questions list — which, for a business reader, is often the most valuable output of the whole run.
3. **Simple, flows, examples.** Every document reads the same way: what the feature is → how it is set up → what happens, step by step, when it runs → **a full worked example with real numbers**. A reader who reads only the example still understands the feature. Short sections, plain headings, no apparatus.

**Announce at start:** "I'm using the `be-shared-business-documentation` skill to write up the traced areas."

**Prerequisites:** a confirmed area map (`be-shared-codebase-survey`) and per-area evidence (`be-shared-feature-trace`). **Load `ba-project-memory` first** — it owns the KB layout, IDs, annotation grammar, and the read-first/update-after contract that governs every file written here.

## When to use

- Steps 4–5 of a `be-documenter` run
- A traced area needs its write-up refreshed after the code moved

## When NOT to use

- The code has not been traced yet → `be-shared-feature-trace`. Writing documentation from a skim is how invented rules get into a document people then trust
- The deliverable is requirements for work *to be done* → `requirements-author` (it authors intent; this recovers it)
- The deliverable is defects → `ep-feature-audit`
- The deliverable is one feature as a standalone file outside the KB → `be-feature-documenter` (same shape, `docs/features/`)

## Output — into the KB, under its contract

Everything lands in **`docs/business-model/`** in the target repo, per `ba-project-memory`:

| File | Owner | This skill's role |
|---|---|---|
| `areas/<area>.md` (`AREA-nnn`) | **this skill** | One document per area, in the shape below |
| `system-overview.md` | **this skill** | What the system is, for whom, the area map, the end-to-end flows that cross areas |
| `glossary.md` | shared | Terms found in code + the code-name → business-name mapping |
| `INDEX.md`, `active-context.md` | shared | Updated per the KB's update-after contract |
| `flows/`, `entities/`, `decisions/` | `ba-process-flow-diagram` · `ba-entity-state-grid` · `ba-decision-table` | **Not yours.** Produced by those skills in Step 3; you link to them by ID |

**The header block and provenance stamp are mandatory** on every file this skill writes — the `Created`/`Owned by` lines per `ba-project-memory`'s header rule, then the stamp:

```markdown
**Created:** YYYY-MM-DD
**Owned by:** `be-shared-business-documentation`
**Derived from:** code by `be-documenter` @ `<commit sha>` on YYYY-MM-DD
```

On a later update, add `**Last updated:** YYYY-MM-DD by \`<skill>\`` beneath the creation line rather than overwriting it. A reader must be able to tell generated content from hand-authored content at a glance; the stamp is the only apparatus the document carries above the evidence table.

**Never overwrite a `#confirmed` entry.** A human confirmed it; it outranks your trace. If your evidence contradicts it, record the contradiction in `active-context.md` and escalate it in the report.

**A filled golden example area document is at `references/example-area.md`** — the shared `workshop-booking` toy system, imagined as an inherited codebase. Shape, tone, example discipline and the evidence table there are normative; the domain content and citations are illustrative.

---

## The area document — the shape

```markdown
# AREA-nnn — <Area name>
**Created:** … · **Owned by:** … · **Derived from:** …
**Models:** [FLOW-nnn …] · [ENT-nnn …] · [DEC-nnn …]

## Overview
## Scope                      ← only when the feature applies selectively
## Setup                      ← only when something is configurable
## How it works
### <Flow — named by its trigger or by what the user does>
### <Flow …>
## Example
## Who can do what            ← only when more than one kind of user, or admin actions exist
## Open questions
## Where this lives in the code
```

Optional sections are **dropped** when they do not apply — never padded. The negative search that proved it ("no configuration: searched `options`, `settings`, `config` under `src/`") is one row in the evidence table, so absence still reads as verified.

### Overview

Two to four sentences. What the feature is and why it exists, in the user's words. If one rule governs everything below, state it here as **Important:** — "Fees are calculated per fill, not per order", "Short positions are not supported today; the formula accounts for them anyway". An inferred purpose reads as uncertainty here and is a row in Open questions.

### Scope

What the feature applies to and what it does not — instrument types, account kinds, countries, user kinds — as short bullets. Eligibility rules belong here ("applies only to companies incorporated in the UK, not merely listed there"). **Boundaries** close the section: "Does not decide product prices — that is **Catalog** (AREA-002)". Boundaries are the cheapest lines to write and the ones that prevent the most wrong assumptions.

### Setup

The configurable parameters, as a table:

| Parameter | Description | Example |
|---|---|---|
| Stress % drop | Simulated fall applied to a net long position | 50% |
| Exposure fee % | Annualised fee charged on the resulting deficit | 25% |

Rules for the section:

- Where configuration is **layered**, name the levels and the precedence in one line: "the most specific plan wins — account, then account group, then default".
- **Validations** as a short list under the table: "Group name must be unique", "An instrument can belong to one group only".
- A value that is **hard-coded** rather than configured is still stated, with its number, where it applies in *How it works*; the evidence table says it is fixed in code — which is usually also an open question (*should it be configurable?*).

### How it works

One sub-section per **flow**. A flow is one trigger: something a user does, a schedule (end of day, first business day of the month), or an event (a fill, a withdrawal). Each flow has the same shape:

```markdown
### Daily accrual

**Trigger:** end of day, for every account holding a margin loan.

1. Work out the loaned amount per instrument for the day — the amount at start of day plus any amount opened during the day.
2. Pick the account's markup tier from the total loaned amount in that currency.
3. Base & account interest = Total loaned amount × (Base rate + Account markup) / Day count
4. Instrument interest = SUM over instruments of (Loaned amount for the instrument × Instrument markup) / Day count
5. Accrued daily interest = Base & account interest + Instrument interest

   Where: *Day count* is the currency's convention (360 or 365); *Account markup* is the tier matched in step 2.

**Result:** one accrual line per currency on the account's ledger. Nothing is charged yet.
**Does not run when:** the account has no loan in that currency — nothing is recorded.
```

- **Numbered steps, business verbs.** A step says what happens to the business, not which service was called. Steps are ordered as the code runs them.
- **A step that computes something shows the formula on its own line**: `Name = expression`, then `Where:` defining each term the first time it appears. Plain-text math — `×` or `*`, `SUM`, `MIN`, `ABS`, `ROUNDUP(x, 2)` — never code. **Rounding, day-count conventions and currency conversion are part of the formula**, never left implicit; the exact number, never a rounding of it.
- **Branches inline.** "If the deficit is 0, stop here — no fee is charged." A combination the code never handles is stated as such ("a sell with no fill price is not handled"), not papered over.
- **Result is mandatory.** What changes for the user or the account: the transaction posted, the state the record ends in, the message shown. It is the payoff of the flow and the line support will quote.
- **What stops it / what the user sees** — only where the code refuses with a user-visible outcome — a short table: Situation · What the user sees · What happens. Drop it when there is nothing to show.
- **One flow per trigger, not per endpoint.** Three endpoints that make up one checkout are one flow. Link a `FLOW-nnn` / `DEC-nnn` by ID where the path branches heavily; never duplicate the diagram.

### Example

**Mandatory** whenever the area has a calculation, a threshold, a tiered or layered configuration, or anything time-based; otherwise a short scenario walk-through. It is not decoration — it is how the reader checks they understood the rule, and how you check you understood the code.

Shape:

1. **Setup** — the concrete configuration and data the example uses, as small tables mirroring the *Setup* section with values filled in (the plans, the rates, the positions, the account).
2. **The steps from *How it works*, each with real numbers carried through** — "Stock group NAV = 27,500 + 11,025 = 38,525" — down to the final result.
3. **Time-based flows as a timeline** — one row per day or event: what happened, the running values, what was accrued or posted.

Rules:

- **Every number used as a rule is the code's exact value.** A rounded or invented threshold is a new rule, stated to a reader who cannot check it.
- **Every arithmetic line is shown and is correct** — recompute the whole example before handing off. A wrong example teaches a wrong rule with great confidence.
- **Invent only the incidental** — names, dates, quantities. One running cast and one data set across the whole document; the reader learns them once.
- **An example illustrates, it never extends.** If the code does not say what happens on day 31, the example stops at day 30 and the gap is an open question.

### Who can do what

Only when more than one kind of user reaches the area, or admin actions exist:

| Who | Can |
|---|---|
| Member | Book and cancel own sessions; sees own credit balance |
| Staff | Cancel anyone's booking; define plans, session tiers, member overrides; upload the FTT list from CSV |

Admin actions as a short list when there are several. How the system recognises each actor (a permission string, a role claim) is evidence-table material, not body.

### Open questions

Everything the code cannot answer, phrased so a business person can answer it:

| # | Question | Why it matters |
|---|---|---|
| Q1 | Is the 30-day refund window a policy decision, a legal requirement, or a card-scheme constraint? | Determines whether it can be changed and by whom |
| Q2 | Late cancellations are recorded but nothing uses them — is a consequence planned? | Members are flagged with no effect; either build the consequence or stop recording |

Every inferred purpose, every hard-coded number whose origin is unknown, every case the code leaves unhandled. Ask about the **rule**, not the code — "Is the 30-day window ours to change?" is exactly what the reader knows.

### Where this lives in the code

The evidence table — the only place in the file for `file:line`, tier tags, class names, table names, status codes and framework nouns. A reader can hide this section and lose nothing but the proof.

| Section | Statement | Evidence | Tier |
|---|---|---|---|
| Setup | Exposure fee % is defined per group | `ExposureGroup.cs:14` | `#observed` |
| How it works — Fee | Deficit = ABS(MIN(0, Equity − Total exposure risk)) | `ExposureFeeCalculator.cs:62` | `#observed` |
| How it works — Fee | Day base comes from the currency's margin-interest setup | `ExposureFeeCalculator.cs:71` → `CurrencySettings.cs:30` | `#observed` |
| Overview | The fee exists to cover losses on margin loans in volatile markets | comment at `ExposureFeeCalculator.cs:9`; **Q1** | `#inferred` |
| Setup | No per-account override of the fee % | search: `AccountExposure`, `FeeOverride` under `src/` — none | `#observed` |

Rules: **every parameter, formula, threshold, step and branch in the body has a row**; an `#observed` row carries `file:line` read this session; an `#inferred` row names its open question; a negative claim names its search. One row per statement, short — this table is an index, not a second document.

---

## Language discipline

The rule that makes the difference between documentation the business uses and documentation it politely ignores:

| Do not write | Write |
|---|---|
| "Returns 409 when the status is not Pending" | "You can only cancel an order that has not yet shipped" |
| "`OrderService.Cancel` validates `TenantId`" | "Agents can only cancel orders belonging to their own organisation" |
| "The `orders` table has a unique index on `(tenant_id, order_number)`" | "Order numbers are unique within an organisation" |
| "Throws `InsufficientStockException`" | "The order is rejected and the customer is told the item is unavailable" |
| "`Math.Ceiling(qty * price * rate * 100) / 100`" | "SEC fee = ROUNDUP(Qty × Fill price × SEC rate, 2)" |

Banned everywhere above the evidence table: class names, method names, table and column names, HTTP status codes, exception types, framework nouns. Formulas are plain-text math, not code. Sentences short; headings plain; no tier tags in prose.

## System overview

`system-overview.md` — the entry point for a reader who knows nothing:

```markdown
# <System> — What it does
**Created:** YYYY-MM-DD
**Owned by:** `be-shared-business-documentation`
**Derived from:** code by `be-documenter` @ `<sha>` on YYYY-MM-DD

## Overview
<One paragraph: what the system is for, who uses it, and what it produces. Business terms only.>

## The areas
| ID | Area | What it does for users | Document | Depth |
|---|---|---|---|---|
| AREA-001 | Identity & access | … | [areas/identity.md](areas/identity.md) | full |

## End-to-end flows
<!-- The user journeys that cross several areas, as numbered steps naming the area at each step.
     This is what a reader needs and no single area document can give them. -->

### New customer's first order
1. **Identity & access** — the customer registers and verifies their email
2. **Catalog** — they browse and add items to a basket
3. **Ordering** — they place the order
4. **Billing** — payment is taken
5. **Notifications** — they receive confirmation
6. **Fulfilment** — the warehouse ships it

## Foundations
<!-- Cross-cutting concerns from the survey: how sign-in and permissions work, how failures reach
     users, how organisations' data is kept apart. One or two lines each, business-level. -->

## What is not documented
| Area / surface | Why | Revisit when |
|---|---|---|

## Coverage
<!-- The survey's full coverage ledger — every surface assigned to an area or parked with a
     reason — so this file can back its own coverage claim. -->
| Surface | Kind | Area | Note |
|---|---|---|---|
```

**"What is not documented" is mandatory.** A documentation set that does not state its own limits gets read as complete, and the parts nobody traced become the parts everyone assumes are fine.

## Glossary

Every domain term found in the code, with its business meaning and — the valuable part — the **mapping between the two vocabularies**:

| Term (business) | Means | Called in code | Notes |
|---|---|---|---|
| Order | A confirmed purchase, from placement to delivery | `Order`, `PurchaseOrder` (legacy) | Two names for one concept `#observed` |
| Account | The billing relationship, not the login | `Customer` | **Drift:** "customer" means the *person* in Identity, the *billing entity* in Billing `#observed` |

**Terminology drift is a finding, not a merge.** Two meanings for one word is exactly the kind of thing that causes an expensive misunderstanding later — record both, flag it, and let `business-analyst` resolve it.

## Reconcile procedure (REFRESH mode)

When the KB already holds documentation for an area and the code has moved:

1. **Re-trace first.** The existing document is a lead; the code is the evidence.
2. **Verdict every statement**: **Agrees** · **New** · **Gone** · **Contradicts**.
3. **Update, don't rewrite** — per the KB's grammar, `~~old~~ → new` keeps one generation of history inline, so a reader can see what changed. Re-run the example's arithmetic whenever a number it uses changed.
4. **`Gone` needs care.** A statement with no code behind it means the feature was removed *or* your trace did not find it. Say which, and never delete a `#confirmed` statement on the strength of a failed search.
5. **`Contradicts` escalates.** Present the documented statement, the code evidence, and both readings — *the documentation is stale* vs *the code has a defect*. Never silently pick one.
6. **Re-stamp provenance** and log the session in `active-context.md`.

## Self-check before handing off

1. Every area from the confirmed map has a document, or is listed in "What is not documented" with a reason.
2. Every document has Overview, How it works, Example, Open questions and the evidence table; optional sections are present only where they apply, and their absence is backed by a negative-search row.
3. Every flow has a trigger and a result; every computing step shows its formula with rounding and conventions stated.
4. **The example's arithmetic is recomputed and correct**, every number used as a rule matches the evidence table, and the same cast and data run through the whole document.
5. No `#confirmed` anywhere in what you wrote; every inferred purpose reads as uncertainty in the body and appears in Open questions.
6. **Every parameter, formula, threshold, step and branch in the body has an evidence row**, and every `#observed` row carries `file:line` read this session.
7. Nothing above the evidence table contains class names, table names, status codes, exception types, framework nouns or tier tags — grep your own output.
8. Flows, state grids, and decision tables are **linked by ID**, not duplicated.
9. Every file carries its `Created`/`Owned by` header and provenance stamp; `INDEX.md` has a line for everything added; `active-context.md` has this session at the top.
10. The glossary records both vocabularies and flags every drift.
11. Nothing unreachable is documented as a capability.

## Handoffs

- **→ `business-analyst`** — owns the KB. Hand off the open questions, the terminology drift, and any contradiction between two areas' rules. It resolves conflicts and records precedence; you never invent it.
- **→ `requirements-author`** — turns confirmed area documentation into epics and INVEST stories, once the business has answered the open questions.
- **→ `qa-test-case-designer`** — the flows, formulas and the worked example are a test basis; the thresholds are BVA seeds and the example is the first expected-value test.
- **→ `be-planner`** — the area map and documented behavior are the inputs to an EXTEND run against this system.
- **→ `code-auditor`** — the findings the trace produced but this documentation deliberately excludes.

## Version policy

Version-agnostic — this skill writes prose, not code. The one version-sensitive input is the **evidence** it cites: `file:line` references are valid only against the commit recorded in the provenance stamp, which is why that stamp is mandatory. On a `REFRESH`, re-verify every citation against the current commit rather than carrying it forward; a citation that has silently drifted to a different line is worse than no citation, because it looks checkable.
