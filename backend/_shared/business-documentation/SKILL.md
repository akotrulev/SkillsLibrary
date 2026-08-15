---
name: be-shared-business-documentation
description: Use when traced backend behavior must be written up as business documentation a non-engineer can read — per-area capabilities, actors, end-to-end use cases, the rules that govern them, what users see when things fail, and boundaries — plus the system overview, glossary and open-questions list, written into the docs/business-model/ knowledge base under ba-project-memory's contract. Every statement tiered as #observed (what the code does, with file:line) or #inferred (what it is probably for, which becomes a question for the business). Triggers "write up what this system does for users", "turn this trace into business documentation", "document the areas we just traced". Do NOT use to trace the code first (`be-shared-feature-trace`), to author requirements for new work (`requirements-author`), or to write findings (`ep-feature-audit`).
---

# Business Documentation — the write-up a non-engineer can use

The last mile, and the one where reverse documentation usually fails: turning accurate technical evidence into something a product manager, support lead, or new stakeholder can actually read — without inventing anything the evidence does not support.

Two disciplines carry the whole skill:

1. **Write in the user's words, not the code's.** The reader does not know what a handler is. "An order cannot be cancelled once it has shipped" — never "`CancelOrderHandler` throws when `status == Shipped`". The `file:line` citation carries the technical anchor so an engineer can verify; the prose does not.
2. **Never let inference pass as fact.** `#observed` is what the code does. `#inferred` is what you think it is for. Every `#inferred` intent statement is *also* a row in the open-questions list — which, for a business reader, is often the most valuable output of the whole run.

**Announce at start:** "I'm using the `be-shared-business-documentation` skill to write up the traced areas."

**Prerequisites:** a confirmed area map (`be-shared-codebase-survey`) and per-area evidence (`be-shared-feature-trace`). **Load `ba-project-memory` first** — it owns the KB layout, IDs, annotation grammar, and the read-first/update-after contract that governs every file written here.

## When to use

- Phases 4–5 of a `be-documenter` run
- A traced area needs its write-up refreshed after the code moved

## When NOT to use

- The code has not been traced yet → `be-shared-feature-trace`. Writing documentation from a skim is how invented rules get into a document people then trust
- The deliverable is requirements for work *to be done* → `requirements-author` (it authors intent; this recovers it)
- The deliverable is defects → `ep-feature-audit`

## Output — into the KB, under its contract

Everything lands in **`docs/business-model/`** in the target repo, per `ba-project-memory`:

| File | Owner | This skill's role |
|---|---|---|
| `areas/<area>.md` (`AREA-nnn`) | **this skill** | The per-area end-user documentation |
| `system-overview.md` | **this skill** | What the system is, for whom, the area map, cross-area journeys |
| `glossary.md` | shared | Terms found in code + the code-name → business-name mapping |
| `INDEX.md`, `active-context.md` | shared | Updated per the KB's update-after contract |
| `flows/`, `entities/`, `decisions/` | `ba-process-flow-diagram` · `ba-entity-state-grid` · `ba-decision-table` | **Not yours.** Produced by those skills in Phase 3; you link to them by ID |

**The header block and provenance stamp are mandatory** on every file this skill writes — the `Created`/`Owned by` lines per `ba-project-memory`'s header rule, then the stamp:

```markdown
**Created:** YYYY-MM-DD
**Owned by:** `be-shared-business-documentation`
**Derived from:** code by `be-documenter` @ `<commit sha>` on YYYY-MM-DD
```

On a later update, add `**Last updated:** YYYY-MM-DD by \`<skill>\`` beneath the creation line rather than overwriting it.

A reader must be able to tell generated content from hand-authored content at a glance. Without it, a generated `#inferred` line is indistinguishable from a business decision someone actually made.

**Never overwrite a `#confirmed` entry.** A human confirmed it; it outranks your trace. If your evidence contradicts it, record the contradiction in `active-context.md` and escalate it in the report.

**A filled golden example area document is at `references/example-area.md`** — the shared `workshop-booking` toy system, imagined as an inherited codebase. Shapes, tiering, and language discipline there are normative; the domain content and citations are illustrative.

---

## The area document

### Section 1 — What you can do here

The capability list, in plain language, as things a person does. This is the section most readers will read and nothing else, so it goes first and it contains no jargon.

```markdown
## What you can do here

- Place an order from the items in your basket
- Cancel an order, up until it ships
- Track an order's progress through fulfilment
- Request a refund on a delivered order, within 30 days
```

One line per capability. If a line needs a caveat, the caveat goes in the line — a reader should not have to cross-reference to learn that cancellation has a deadline.

### Section 2 — Who uses it

| Actor | Who they are | What they can do here | How they are recognised |
|---|---|---|---|
| Customer | A signed-in buyer | Place, view, cancel own orders | `orders:write` permission on their token `#observed` |
| Support agent | Internal staff handling queries | View and cancel **any** order in their tenant | `support` role `#observed` |
| Fulfilment system | Warehouse integration | Mark orders shipped | Machine credential `#observed` |

Actors come from the authorization inventory of the trace. An area with only one actor is worth double-checking — the trace may have missed an admin path, which is the most commonly under-documented class of user.

### Section 3 — How it works, end to end

The use cases. One per meaningful thing a user does, in this shape:

```markdown
### Placing an order

**Who:** Customer
**Starts when:** the customer confirms their basket at checkout.

1. The system checks every item is still available and still sold to this customer's region.
2. It prices the order — item prices, then any promotions, then shipping.
3. It reserves stock for each item.
4. It creates the order in a *pending* state and asks the payment provider to take payment.
5. Once payment succeeds the order becomes *paid* and a confirmation email is sent.

**Ends with:** a *paid* order the customer can track, and a confirmation email.

**What can go wrong:**
| Situation | What the customer sees | What happens to the order |
|---|---|---|
| An item sold out while they were checking out | "One or more items are no longer available" | No order is created |
| Payment declined | "Your payment could not be taken" | Order stays *pending* and is cancelled automatically after 30 minutes `#observed` |
| The payment provider is unreachable | "We can't take payments right now — please try again shortly" | No order is created; nothing is charged `#observed` |
```

Rules for this section:

- **Numbered steps, business verbs.** Steps say what happens to the business, not which service was called.
- **"What can go wrong" is not optional.** It is where a support lead learns what to tell a customer, and it is the section that only exists because someone read the failure paths.
- **Link the flow diagram by ID** (`FLOW-012`) rather than duplicating it — one representation, referenced.
- **Use cases are per capability, not per endpoint.** Three endpoints that make up one checkout are one use case.

### Section 4 — The rules that apply

Every business rule from the trace, in business language, with its tier and evidence:

| # | Rule | Applies when | Tier | Evidence |
|---|---|---|---|---|
| R1 | Refunds are only possible within 30 days of delivery | Refund requested | `#observed` | `RefundService.cs:88` |
| R2 | Orders over £50 ship free | Order total calculated | `#observed` | `ShippingCalculator.cs:41` |
| R3 | The 30-day window most likely tracks the card scheme's chargeback period | — | `#inferred` | comment at `RefundService.cs:85`; **open question Q4** |

Keep `#observed` and `#inferred` rows visually adjacent but distinctly marked — a reader scanning for "what are our rules" must not accidentally read your inference as policy. Exact numbers, never rounded. Link decision tables by ID (`DEC-003`) where a rule has more than two inputs.

### Section 5 — Boundaries

What this area explicitly does **not** do, and where that lives instead. The cheapest section to write and the one that prevents the most wrong assumptions:

```markdown
## Boundaries

- Does not handle payment method storage — that is **Billing** (AREA-004)
- Does not decide product pricing — prices come from **Catalog** (AREA-002); this area only applies promotions
- Does not notify anyone directly — it emits events that **Notifications** (AREA-006) acts on
```

### Section 6 — Open questions

Everything the code cannot answer, phrased so a business person can answer it:

```markdown
| # | Question | Why it matters | Evidence |
|---|---|---|---|
| Q4 | Is the 30-day refund window a policy decision, a legal requirement, or a card-scheme constraint? | Determines whether it can be changed and by whom | `RefundService.cs:88` |
| Q5 | Should support agents be able to cancel a shipped order? Today they cannot. | Support currently escalate these manually | `OrdersController.cs:120` |
```

Ask about the **rule**, not the code. "Why does `RefundService` check `PlacedAt`?" is unanswerable by the person you are asking; "Is the 30-day refund window ours to change?" is exactly what they know.

---

## System overview

`system-overview.md` — the entry point for a reader who knows nothing:

```markdown
# <System> — What it does
**Created:** YYYY-MM-DD
**Owned by:** `be-shared-business-documentation`
**Derived from:** code by `be-documenter` @ `<sha>` on YYYY-MM-DD

## In one paragraph
<What the system is for, who uses it, and what it produces. Business terms only.>

## The functional areas
| ID | Area | What it does for users | Documented | Depth |
|---|---|---|---|---|
| AREA-001 | Identity & access | … | [areas/identity.md](areas/identity.md) | full |

## Cross-area journeys
<!-- The journeys that cross several areas, as step lists naming the area at each step.
     This is what a reader needs and no single area document can give them. -->

### New customer's first order
1. **Identity & access** — the customer registers and verifies their email
2. **Catalog** — they browse and add items to a basket
3. **Ordering** — they place the order
4. **Billing** — payment is taken
5. **Notifications** — they receive confirmation
6. **Fulfilment** — the warehouse ships it

## Foundations
<!-- Cross-cutting concerns from the survey: how authorization works, how failures surface
     to users, how tenancy separates data. One or two lines each, business-level. -->

## What is not documented
| Area / surface | Why | Revisit when |
|---|---|---|

## Coverage
<!-- The survey's full coverage ledger — every surface assigned to an area or parked with a
     reason — so this file can back its own coverage claim without the reader opening the
     orientation cache. -->
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

## Language discipline

The rule that makes the difference between documentation the business uses and documentation it politely ignores:

| Do not write | Write |
|---|---|
| "Returns 409 when the status is not Pending" | "You can only cancel an order that has not yet shipped" |
| "`OrderService.Cancel` validates `TenantId`" | "Agents can only cancel orders belonging to their own organisation" |
| "The `orders` table has a unique index on `(tenant_id, order_number)`" | "Order numbers are unique within an organisation" |
| "Throws `InsufficientStockException`" | "The order is rejected and the customer is told the item is unavailable" |
| "Nullable `ShippedAt`" | "An order that has not shipped yet has no shipping date" |

Banned from narrative sections (sections 1, 2, 3, 5): class names, method names, table and column names, HTTP status codes, exception types, framework nouns. They are welcome in the **Evidence** columns, where they belong. The final column of the Section-2 "How they are recognised" table and of each "What can go wrong" table is an evidence column for this purpose — permission strings and `file:line` citations belong there, exempt from the ban just like Section 4's Evidence column.

## Reconcile procedure (REFRESH mode)

When the KB already holds documentation for an area and the code has moved:

1. **Re-trace first.** The existing document is a lead; the code is the evidence.
2. **Verdict every statement**: **Agrees** · **New** · **Gone** · **Contradicts**.
3. **Update, don't rewrite** — per the KB's grammar, `~~old~~ → new` keeps one generation of history inline, so a reader can see what changed.
4. **`Gone` needs care.** A statement with no code behind it means the feature was removed *or* your trace did not find it. Say which, and never delete a `#confirmed` statement on the strength of a failed search.
5. **`Contradicts` escalates.** Present the documented statement, the code evidence, and both readings — *the documentation is stale* vs *the code has a defect*. Never silently pick one.
6. **Re-stamp provenance** and log the session in `active-context.md`.

## Self-check before handing off

1. Every area from the confirmed map has a document, or is listed in "What is not documented" with a reason.
2. No `#confirmed` anywhere in what you wrote; every `#inferred` intent appears in open questions.
3. Every `#observed` statement carries `file:line`.
4. Narrative sections contain no class names, table names, status codes, or exception types — grep your own output.
5. Every area document has all six sections; "What can go wrong" and "Boundaries" are the ones most likely to be skipped.
6. Flows, state grids, and decision tables are **linked by ID**, not duplicated.
7. Every file carries its `Created`/`Owned by` header and provenance stamp; `INDEX.md` has a line for everything added; `active-context.md` has this session at the top.
8. The glossary records both vocabularies and flags every drift.
9. Nothing unreachable is documented as a capability.

## Handoffs

- **→ `business-analyst`** — owns the KB. Hand off the open questions, the terminology drift, and any contradiction between two areas' rules. It resolves conflicts and records precedence; you never invent it.
- **→ `requirements-author`** — turns confirmed area documentation into epics and INVEST stories, once the business has answered the open questions.
- **→ `qa-test-case-designer`** — the rules and "what can go wrong" tables are a test basis; the thresholds are BVA seeds.
- **→ `be-planner`** — the area map and documented behavior are the inputs to an EXTEND run against this system.
- **→ `code-auditor`** — the findings the trace produced but this documentation deliberately excludes.
- **→ `be-shared-plain-language-companion`** — writes `areas/<area>-explained.md` and `system-overview-explained.md` beside these documents: the same facts in shorter sentences with worked examples, for the stakeholder who has to answer the open questions. It adds nothing; anything it exposes as missing gets fixed **here**. Regenerate a companion whenever its source is refreshed.

## Version policy

Version-agnostic — this skill writes prose, not code. The one version-sensitive input is the **evidence** it cites: `file:line` references are valid only against the commit recorded in the provenance stamp, which is why that stamp is mandatory. On a `REFRESH`, re-verify every citation against the current commit rather than carrying it forward; a citation that has silently drifted to a different line is worse than no citation, because it looks checkable.
