---
name: doc-business-model
description: Use when traced backend behavior must be written up at three levels — a plain-language client guide, a plain-language "behind the scenes" account of how the parts connect, and a technical reference for developers and AI — one set per area in docs/business-model/. Triggers "turn this trace into docs", "write the client guide and the technical reference". Not for tracing code (doc-feature-trace).
---

# Business Documentation — one trace, three documents, three readers

The same accurate evidence has to serve a client who has never seen the code, a project or support lead who needs to know how the pieces hang together, and a developer or AI agent who must change it safely. One document cannot serve all three. So every area (and every feature) is written **three times, from one trace, at three levels**:

| Level | File | Reader | Audience | Language | Answers |
|---|---|---|---|---|---|
| **1 — Guide** | `<name>.md` | Client, product owner, support | `shareable` | Plain. No technical talk at all | What is this, how is it set up, what happens when I use it, show me with numbers |
| **2 — Behind the scenes** | `<name>.behind-the-scenes.md` | Project manager, analyst, ops | `internal` | Plain, with a few everyday technical words | Which parts are involved, who tells whom, what happens now and later, what is kept where, what happens when a part fails |
| **3 — Technical reference** | `<name>.technical.md` | Developers and AI agents | `internal` | Fully technical: code names, paths, contracts, `file:line`, tiers | Where is it, what exactly does it do, what breaks if I change it, how do I know |

Each level links to the other two from its header. A higher level never repeats the lower one's explanations — it links to them.

**Load the level references only when writing that level:**

| Writing | Load |
|---|---|
| Level 1 (any set) | nothing extra — the shape is below |
| Level 2 | [`references/level-2-behind-the-scenes.md`](references/level-2-behind-the-scenes.md) |
| Level 3 | [`references/level-3-technical.md`](references/level-3-technical.md) |
| `system-overview*.md` | [`references/system-overview.md`](references/system-overview.md) |
| Checking tone or shape against a model | the matching golden example (below) |

Six disciplines carry the whole skill:

1. **Write for the level's reader, and stay at that level.** Level 1 never says "handler"; Level 2 never says `OrderService.Cancel`; Level 3 never says "the part that looks after bookings" without the class name beside it.
2. **Never let inference pass as fact — and keep the grammar in Level 3.** `#observed` is what the code does; `#inferred` is what you think it is for. Tiers and every `file:line` live in Level 3's **evidence index**; in Levels 1 and 2 an inferred purpose reads as uncertainty ("appears to exist so that…") and is a row in Open questions.
3. **Simple, flows, examples.** Level 1 reads the same way every time: what it is → how it is set up → what happens, step by step → **a full worked example with real numbers**.
4. **One fact, one home.** A statement is explained at the level where its reader needs it and cited at the others. The three levels never contradict each other; when evidence changes one, all three are re-checked and re-stamped.
5. **Level 3 carries the proof for all three.** Every parameter, formula, threshold, step, branch, connection, timing and failure claim in Levels 1 and 2 has a row in Level 3's evidence index. Level 3 is never skipped.
6. **Levels 1 and 2 describe; only Level 3 judges.** Behaviour is stated factually and neutrally ("the credits are returned twice"). The words *bug, defect, flaw, broken, wrong, mistake, vulnerability* and *should have* never appear in Levels 1 or 2; classifying something as a defect happens only in Level 3's Findings, and a Level 2 statement that is also a finding has an evidence-index row citing it (`see **F1**`). Level 2 is `internal` because it is frank about failure, not because it is allowed to editorialise.

**Prerequisites:** a confirmed area map (`dev:doc-codebase-survey`) and per-area evidence (`dev:doc-feature-trace`), including its `Client vocabulary` table and the verbatim refusal texts in inventory 3. **When `docs/business-model/` exists or is being written, load `business-analysis:knowledge-base` first** — it owns the KB layout, IDs, annotation grammar, and the read-first/update-after contract; a standalone feature run without a KB skips it.

**The golden examples are illustrations, never sources.** Every fact, number, currency, message and actor in a document comes from this run's trace. A claim that appears in an example but that the trace did not find (a currency symbol, who sets a rate, a message text) is not written — it becomes an open question.

## When to use

- Steps 4–5 of a `be-documenter` run, and Step 3 of a `be-feature-documenter` run
- A traced area needs its write-up refreshed after the code moved

## When NOT to use

- The code has not been traced yet → `dev:doc-feature-trace`
- The deliverable is requirements for work *to be done* → `requirements-author`
- The deliverable is defects → `dev:audit-feature`. Defects found while tracing go in Level 3's Findings, never into Levels 1 or 2

## Output — into the KB, under its contract

Everything lands in **`docs/business-model/`**, per `business-analysis:knowledge-base`. A standalone feature (`be-feature-documenter`) uses the same three-file set under `docs/features/` with `<NNN>-<slug>` as the name.

| File | Owner | This skill's role |
|---|---|---|
| `areas/<area>.md` (`AREA-nnn`) | **this skill** | Level 1 — the guide |
| `areas/<area>.behind-the-scenes.md` | **this skill** | Level 2 |
| `areas/<area>.technical.md` | **this skill** | Level 3 |
| `system-overview.md`, `.behind-the-scenes.md`, `.technical.md` | **this skill** | The same three levels for the whole system |
| `glossary.md` | shared | Terms, the client's own words, and the business ↔ code mapping |
| `INDEX.md`, `active-context.md` | shared | Updated per the KB contract. **One `INDEX.md` line per area**, naming all three files |
| `events.md`, `shared-data.md`, `invariants.md` | `business-analysis:dependency-map` | **Not yours.** Levels 2 and 3 cite them by id |
| `flows/`, `entities/`, `decisions/` | `process-flow` · `state-grid` · `decision-table` | **Not yours.** You link to them by ID |

### Header block

Mandatory on **every file** of a set, in this order:

```markdown
**Created:** YYYY-MM-DD
**Owned by:** `dev:doc-business-model`
**Derived from:** code by `be-documenter` @ `<commit sha>` on YYYY-MM-DD
**Audience:** shareable | internal
**Levels:** [Guide](<name>.md) · [Behind the scenes](<name>.behind-the-scenes.md) · [Technical reference](<name>.technical.md)
```

- **Audience** is `shareable` on Level 1 and `internal` on Levels 2 and 3. A person may promote Level 2 to `shareable` after reading it; an agent never does. Feature documents use the feature header (`**Generated by …**`) and carry the same `**Audience:**` line.
- **Each file carries its own `Derived from` stamp.** The three files of a set always carry the **same sha** after a run: when any one is updated, all three are re-checked and re-stamped, and each gets `**Last updated:** YYYY-MM-DD by \`<skill>\`` beneath its creation line (the creation line is never overwritten).
- **Never overwrite a `#confirmed` entry.** If your evidence contradicts it, record the contradiction in `active-context.md` and escalate it.

**Golden examples** — the `workshop-booking` toy system as an inherited codebase, one area at all three levels: [`references/example-area.md`](references/example-area.md) (Level 1), [`references/example-behind-the-scenes.md`](references/example-behind-the-scenes.md) (Level 2), [`references/example-technical.md`](references/example-technical.md) (Level 3). Shape, tone, example discipline and the evidence index are normative; the domain content is illustrative.

---

## Level 1 — the guide

The client-facing document. If a sentence would make a non-technical client ask "what does that mean?", it does not belong here.

```markdown
# AREA-nnn — <Area name>
<header block — Audience: shareable>
**Models:** [FLOW-nnn …] · [ENT-nnn …] · [DEC-nnn …]

## Overview
## Scope                      ← only when the feature applies selectively
## Setup                      ← only when something is configurable
## How it works
### <Flow — named by its trigger or by what the user does>
## How it connects             ← only when something crosses the area boundary
## Example
## Who can do what            ← only when more than one kind of user, or admin actions exist
## Open questions
## Going deeper               ← links to Level 2 and Level 3
```

Optional sections are **dropped** when they do not apply — never padded. The negative search that proved it is one row in Level 3's evidence index. **There is no evidence table in Level 1.** Under about 2,000 words.

**The client's words.** Name things the way the client's own product names them — the button labels, screen titles, email wording and messages harvested in the trace's `Client vocabulary` table — not the way the code names them. "Credits", "session", "Cancel booking" if that is what the screen says. Every term used goes to the glossary with its code name.

- **Overview** — two to four sentences: what it is and why it exists, in the client's words. One rule that governs everything below is stated as **Important:**. An inferred purpose reads as uncertainty and is an open question.
- **Scope** — what it applies to and what it does not, as short bullets, closed by **Boundaries** ("Does not decide prices — that is **Catalog** (AREA-002)").
- **Setup** — a `| Parameter | Description | Example |` table. Layered configuration names its levels and precedence in one line ("the most specific wins — member, then plan"); validations as a short list under the table; a **hard-coded** value is still stated with its number (Level 3 records that it is fixed, usually also an open question).
- **How it connects** — three short lists in business words, from the Edges inventory: **Starts from**, **Sets off**, **Shares**. Areas by `AREA-nnn` and label. The *how* is Level 2; ids and delivery mode are Level 3.

### How it works

One sub-section per **flow** — one trigger: something a user does, a schedule, or an event. Each has the same shape:

```markdown
### Daily accrual

**Trigger:** end of day, for every account holding a margin loan.

1. Work out the loaned amount per instrument for the day.
2. Pick the account's markup tier from the total loaned amount in that currency.
3. Base & account interest = Total loaned amount × (Base rate + Account markup) / Day count

   Where: *Day count* is the currency's convention (360 or 365); *Account markup* is the tier matched in step 2.

**Result:** one accrual line per currency on the account's ledger. Nothing is charged yet.
```

- **Numbered steps, business verbs**, in the order the code runs them. The evidence index cites them as `<Flow heading> · step N`, so keep the numbering stable.
- **A computing step shows its formula on its own line** — `Name = expression`, then `Where:`. Plain-text math (`×`, `SUM`, `MIN`, `ROUNDUP(x, 2)`), never code. Rounding, day-count conventions and currency conversion are part of the formula; the exact number, never a rounding of it.
- **Branches inline.** "If the deficit is 0, stop here." A combination the code never handles is stated as such.
- **Result is mandatory** — what changes for the user: the charge posted, the state the record ends in, the message shown.
- **What stops it** — only where the code refuses with a user-visible outcome: a `Situation | What the user sees | What happens` table. *What the user sees* **quotes the exact message** from the trace's inventory 3 ("“This session is full”"), never a paraphrase. Drop the table when nothing is refused.
- **One flow per trigger, not per endpoint.** Link a `FLOW-nnn` / `DEC-nnn` where the path branches heavily; never duplicate the diagram.

### Example

**Mandatory** whenever there is a calculation, a threshold, a tiered or layered configuration, or anything time-based; otherwise a short scenario walk-through.

1. **Setup** — the concrete configuration and data, as small tables mirroring *Setup* with values filled in.
2. **The steps, with real numbers carried through** — "Stock group NAV = 27,500 + 11,025 = 38,525" — to the final result.
3. **Time-based flows as a timeline** — one row per day or event.

Every number used as a rule is the code's exact value; every arithmetic line is shown and recomputed before handing off; invent only the incidental (names, dates, quantities), one running cast and one data set; an example illustrates, never extends — where the code is silent, the example stops and the gap is an open question.

### Who can do what, Open questions, Going deeper

- **Who can do what** — `| Who | Can |`, only when there is more than one kind of user or admin actions exist. How the system recognises each actor is Level 3.
- **Open questions** — `| # | Question | Why it matters |`, numbered `Q1…` (Level 2 continues the numbering). Every inferred purpose, every hard-coded number of unknown origin, every unhandled case — asked about the **rule**, not the code.
- **Going deeper** — two lines, last in the document, linking Level 2 and Level 3.

---

## Language discipline — by level

The same fact, three ways:

| Level 3 (technical) | Level 2 (behind the scenes) | Level 1 (guide) |
|---|---|---|
| `POST /bookings/{id}/cancel` → 409 when `status != Pending` | The booking service refuses the cancellation and the page shows a message | You can only cancel an order that has not yet shipped |
| unique index `(tenant_id, order_number)` | The order number is checked for clashes when the order is saved | Order numbers are unique within an organisation |
| `BookingConfirmed` via outbox after commit; consumer retried 3× then dead-lettered | Once the booking is saved, the pricing step is told in the background; if it fails it is tried three times and then set aside | Your credits are worked out as soon as the booking is confirmed |
| F1: no idempotency key — redelivery double-prices | The same message can arrive twice, and the booking is then priced twice | — (not a client-facing rule) |
| `Math.Ceiling(qty * price * rate * 100) / 100` | — (Level 2 links to Level 1) | SEC fee = ROUNDUP(Qty × Fill price × SEC rate, 2) |

Banned in **Level 1** (and in Level 2, beyond its allowed everyday words): class, method, table and column names, file names, status codes, exception types, framework nouns, inline code, jargon such as *endpoint, payload, handler, middleware, idempotent, eventual consistency*, tier tags, `file:line`, and the defect words of discipline 6. A word that needs a definition is replaced, not defined; a word the client uses themselves stays.

## Glossary

Every domain term found, with its business meaning and the **mapping between the vocabularies** — the client's own term (from the trace's `Client vocabulary` table), what it means, and what the code calls it:

| Term (client) | Means | Called in code | Where the client sees it | Notes |
|---|---|---|---|---|
| Order | A confirmed purchase, from placement to delivery | `Order`, `PurchaseOrder` (legacy) | order confirmation email | Two names for one concept `#observed` |
| Account | The billing relationship, not the login | `Customer` | invoice header | **Drift:** "customer" means the *person* in Identity, the *billing entity* in Billing `#observed` |

**Terminology drift is a finding, not a merge** — record both, flag it, and let `business-analyst` resolve it. Level 2's plain part names are in the glossary too.

## Reconcile procedure (every run that finds an existing set)

1. **Check staleness per file.** Read each existing file's `Derived from` sha, compare it with `HEAD` and the git delta for the area's paths, and report which of the three levels are stale. If any one is stale, all three are reconciled together.
2. **Re-trace first.** The existing documents are a lead; the code is the evidence.
3. **Verdict every statement**: **Agrees** · **New** · **Gone** · **Contradicts**.
4. **Update, don't rewrite** — `~~old~~ → new` keeps one generation of history inline. Re-run the example's arithmetic whenever a number it uses changed; re-check Level 2's timing and failure statements; re-verify every `file:line` at the current commit and every evidence-index `Flow · step N` citation against the renumbered steps.
5. **`Gone` needs care.** Say whether the feature was removed or your trace did not find it; never delete a `#confirmed` statement on the strength of a failed search.
6. **`Contradicts` escalates.** Present the documented statement, the code evidence, and both readings — *stale documentation* vs *code defect*. Never silently pick one.
7. **Re-stamp all three files** with the same sha and a `Last updated` line, and log the session in `active-context.md`. A REFRESH that deliberately re-traced only part of a set says so in the report.

## Self-check before handing off

1. **Lint passes:** `python3 ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/doc-lint.py --dir <folder>` exits 0. Fix every `ERROR`; read every `WARN` and either fix it or say in the report why it stands.
2. Every area from the confirmed map has all three documents, or is in "What is not documented" with a reason.
3. **Level 1** has Overview, How it works, Example, Open questions and Going deeper; optional sections only where they apply, absence backed by a Level 3 negative-search row. No evidence table, tier tag, code noun, jargon or defect word. It uses the client's terms, and every *What stops it* row quotes the exact message.
4. **Level 2** matches its reference: diagram, parts, a flow per Level 1 flow with only the lanes it uses, *What the person notices* only where there is a later step, remembered / timing / failure sections. No banned word, no defect word — behaviour stated neutrally, and every statement that is also a finding has an index row citing it. In a KB run, no FLOW is redrawn.
5. **Level 3** matches its reference: every heading (empty ones state their search), local ids on every row, Mermaid for each state machine and multi-participant flow, Findings routed with a boundary condition.
6. Every flow has a trigger and a result; every computing step shows its formula with rounding and conventions; **the example's arithmetic is recomputed and correct**, and every number matches Level 3.
7. No `#confirmed` anywhere you wrote; every inferred purpose reads as uncertainty in Levels 1 and 2 and is an open question.
8. **Evidence index complete:** every qualifying statement in Levels 1 and 2 has a row; Section cells read `<Flow heading> · step N` (or the section name); every `###` flow of both plain levels is cited; every `see **X**` resolves to a row id in Level 3; every `#observed` row carries `file:line` read this session.
9. **The three levels agree** — spot-check five facts that appear at more than one level (a threshold, a retry count, a trigger, a name mapping, an actor).
10. Every file carries the full header block with its `Audience` line, and all three carry the same `Derived from` sha; `INDEX.md` has one line per area naming all three files; `active-context.md` has this session at the top.
11. The glossary records the client's terms, the code names and every drift; Level 2's part names are in it.
12. Flows, state grids and decision tables are linked by ID, not duplicated; nothing unreachable is documented as a capability.

## Handoffs

- **→ `business-analyst`** — the open questions, the terminology drift, and any contradiction between two areas' rules. It resolves conflicts and records precedence; you never invent it.
- **→ `requirements-author`** — turns confirmed Level 1 documentation into epics and stories once the open questions are answered.
- **→ `qa-test-case-designer`** — Level 1's flows, formulas and worked example are a test basis; Level 3's rules, errors and refused transitions are the negative-test matrix.
- **→ `solution-planner`** — the area map and Level 3 are the inputs to an EXTEND run.
- **→ `code-auditor`** — Level 3's Findings.
- **→ any `be-<stack>` agent or AI assistant about to change the code** — start from Level 3's *Quick facts* and *Code map*; read *Changing this safely* before editing.

## Version policy

Version-agnostic — this skill writes prose, not code. The one version-sensitive input is the **evidence**: `file:line` references are valid only against the commit in each file's `Derived from` stamp. On a refresh, re-verify every citation against the current commit rather than carrying it forward; a citation that has silently drifted to a different line is worse than no citation.
