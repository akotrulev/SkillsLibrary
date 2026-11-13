---
name: doc-business-model
description: Use when traced behavior must be written up as a client guide, a behind-the-scenes account and a technical reference. Triggers "turn this trace into docs". Not for tracing code (doc-feature-trace).
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
3. **Simple, flows, examples.** Level 1 reads the same way every time: who uses it → how it fits together → each person's tasks in lifecycle order → **examples beside the rule they show**.
4. **One fact, one home.** A statement is explained at the level where its reader needs it and cited at the others. The three levels never contradict each other; when evidence changes one, all three are re-checked and re-stamped.
5. **Level 3 carries the proof for all three.** Every parameter, formula, threshold, step, branch, connection, timing and failure claim in Levels 1 and 2 has a row in Level 3's evidence index. Level 3 is never skipped. **Write order:** Level 3's body, then Level 1, then Level 2, then Level 3's evidence index last — it cites the step numbers of the other two. Level 3 runs up to about 4,000 words, not counting the index, then splits by topic (see its reference).
6. **Levels 1 and 2 describe; only Level 3 judges.** Behaviour is stated factually and neutrally ("the credits are returned twice"). The words *bug, defect, flaw, broken, wrong, mistake, vulnerability* and *should have* never appear in Levels 1 or 2 — the lint warns on each, and each is fixed or explained in the report; text quoted verbatim from the product is exempt; classifying something as a defect happens only in Level 3's Findings, and a Level 2 statement that is also a finding has an evidence-index row citing it (`see **F1**`). Level 2 is `internal` because it is frank about failure, not because it is allowed to editorialise.

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

The lines below are mandatory on **every file** of a set, in this order:

```markdown
**Created:** YYYY-MM-DD
**Owned by:** `dev:doc-business-model`
**Derived from:** code by `be-documenter` @ `<commit sha>` on YYYY-MM-DD
**Audience:** shareable | internal
**Levels:** [Guide](<name>.md) · [Behind the scenes](<name>.behind-the-scenes.md) · [Technical reference](<name>.technical.md)
```

- **Where the block sits.** In **Levels 1 and 2** the reader meets one line on top — `**Levels:**` — and the rest closes the file in `## About this document` (Level 1's opens with `**Id:** AREA-nnn`; see Level 1 below). Level 2 keeps `**Audience:** internal` on top beside `**Levels:**`, because its job is to stop the file being forwarded. **Level 3 keeps the whole block on top**: its reader is an agent that needs the sha first.
- **Audience** is `shareable` on Level 1 and `internal` on Levels 2 and 3. A person may promote Level 2 to `shareable` after reading it; an agent never does. Feature documents use the feature header (`**Generated by …**`) and carry the same `**Audience:**` line.
- **Each file carries its own `Derived from` stamp.** The three files of a set always carry the **same sha** after a run: when any one is updated, all three are re-checked and re-stamped, and each gets `**Last updated:** YYYY-MM-DD by \`<skill>\`` beneath its creation line (the creation line is never overwritten).
- **Never overwrite a `#confirmed` entry.** If your evidence contradicts it, record the contradiction in `active-context.md` and escalate it.

**Golden examples** — the `workshop-booking` toy system as an inherited codebase, one area at all three levels: [`references/example-area.md`](references/example-area.md) (Level 1), [`references/example-behind-the-scenes.md`](references/example-behind-the-scenes.md) (Level 2), [`references/example-technical.md`](references/example-technical.md) (Level 3). Shape, tone, example discipline and the evidence index are normative; the domain content is illustrative.

---

## Level 1 — the guide

The client-facing document. If a sentence would make a non-technical client ask "what does that mean?", it does not belong here. It reads in the order a person meets the product: who uses it, the few ideas and one picture of how it fits together, then each person's tasks in the order life happens.

```markdown
# <Area name>

<One sentence, the client's words: what a person can do here.>

**Levels:** [Guide](<name>.md) · [Behind the scenes](<name>.behind-the-scenes.md) · [Technical reference](<name>.technical.md)

> [!IMPORTANT]
> <The one rule that governs everything below.>          ← optional

## Who uses it
| Who | What they do here |

## How it fits together                                    ← key ideas, then one Mermaid diagram
## For <person>                                             ← one per person in "Who uses it", in that table's order
### <Task — what the person does: "Place an order">
## What happens automatically                               ← optional: scheduled and event-started work
### <Work — named by what it does: "Monthly posting">
## Rules and limits                                         ← optional
## A <period> in numbers                                    ← optional: one story whose numbers carry across tasks
## Good to know                                             ← optional
## Related areas                                            ← optional
## Open questions                                           ← for the product owner
## About this document                                      ← the metadata, last
```

Optional sections are **dropped** when they do not apply — never padded. The negative search that proved it is one row in Level 3's evidence index. **There is no evidence table in Level 1.**

**Order of the people.** `## Who uses it` lists people in the order they meet the area (the customer who places an order before the owner who accepts it); the `## For <person>` sections follow that order, and inside each section the tasks follow the record's lifecycle (place → find again → cancel → rate → order again). The heading is `## For <plural or role>` — `## For customers`, `## For the owner`, `## For makers`. The guide's open questions stay under `## Open questions`; a `## For …` heading is always a person's tasks.

**The client's words.** Name things the way the client's own product names them — the button labels, screen titles, email wording and messages harvested in the trace's `Client vocabulary` table — not the way the code names them. Every term used goes to the glossary with its code name.

**A task:**

````markdown
### Cancel an order

You can cancel an order yourself until the shop starts working on it; after that you ask.

**Where:** **Your orders** → the order → **Cancel order**

1. Open the order and press **Cancel order**.
2. Give a reason if you like, and press **Confirm**.

**What happens next**

- If nobody at the shop has accepted the order yet, it is cancelled and the timeline shows it.
- If it has been accepted, **Cancel order** becomes **Ask to cancel**: your request, with a reason, waits for the owner.

**If it doesn't go through**

| Situation | What you see | What to do |
|---|---|---|
| The owner accepted it a moment earlier | “This order was accepted while you were deciding.” | Press **Ask to cancel** |

> [!NOTE]
> Any money you paid comes back as a refund — see **Online payments & maker payouts**.
````

- **Second person, imperative, to the person the section names.** Field names in *italics*. **One idea per sentence.**
- **Bold is a screen label, and a label is evidence.** In a `**Where:**` line and in the person's steps, bold is only ever a label exactly as the screen shows it, and every such label is in the first column of Level 3's *Business ↔ code vocabulary*. Never invent a button.
- **`**Where:**`** is the arrow path from the trace's `Where in the product` column (screen › control). A task reached through another channel names it without bold (`**Where:** your own AI assistant, through the shop's order tool`).
- **No screen found** — the UI is not in this codebase, or the search came back empty: the task has no `**Where:**` line and no bold label, and its steps say what the person asks for in plain verbs ("Ask to cancel the booking"). The negative search is a Level 3 row. When no screen was found for the whole area, one open question asks where people do this.
- **The person's steps are numbered; "What happens next" is a bulleted list of outcomes.** An outcome is something the person sees, receives or is charged; alternatives are separate bullets starting "If …". Everything else the system does — its checks, what it records, what it tells other parts — is Level 2's. The evidence index cites `<Task> · step N` and `<Task> · outcome N`, counted from the top of each list, so keep the order stable. An outcome that computes keeps the formula block: `Name = expression` on its own line, then `Where:`. Plain-text math (`×`, `SUM`, `ROUNDUP(x, 2)`), never code; rounding, day-count conventions and currency conversion are part of the formula, and the number is exact.
- **At most seven steps and five outcomes**; a task that needs more is two tasks.
- **Task headings are unique in the guide**: a task two people do is named for each ("Cancel a booking" under members, "Cancel a member's booking" under staff), the second one short and pointing at the first by name.
- **Automatic work** — a `###` under `## What happens automatically` — keeps the flow shape, because nobody acts: `**Trigger:**`, numbered steps in business verbs, `**Result:**`. Its steps are cited `· step N`.
- **"If it doesn't go through"** — only where the code refuses with a user-visible outcome. *What you see* **quotes the exact message** from the trace's inventory 3, never a paraphrase; the third column is what to do, not what the system does. Drop the table when nothing is refused.
- **An example sits inside the task that computes**, as `**Example**` and a few lines or a small table, numbers carried to the result. `## A <period> in numbers` exists only when one story's numbers carry across several tasks (credits spent on booking, returned on cancelling, posted at month end); it replaces a task example. Every number used as a rule is the code's exact value; every arithmetic line is shown and recomputed before handing off; invent only the incidental (names, dates, quantities) with one running cast; an example illustrates, never extends — where the code is silent, the example stops and the gap is an open question.
- **Callouts** are GFM alerts and only four kinds: `[!IMPORTANT]` (a rule that governs — never a bold **Important:**), `[!NOTE]` (a prerequisite or where something else is handled), `[!TIP]` (a shortcut), `[!WARNING]` (an action that cannot be undone or that charges money — nothing else). At most one inside a task.
- **`## How it fits together`** holds the key ideas, then the picture; it is left out only when the area has one task, no states and no term to explain.
  - **Key ideas** — up to six `**Term** — one line` entries: the words the tasks use that a new reader would not know, and any concept that is not a task. The detail is Level 2's.
  - **One Mermaid diagram**, nine nodes at most, labels in the client's words, node ids single lowercase words: a `stateDiagram-v2` of the area's main record when it has states, otherwise a `flowchart LR` (labels in double quotes) of the people and what passes between them. It is drawn from the trace's states and transitions and agrees with the `ENT-nnn` grid where the KB has one. **Every arrow is a task or automatic work in this guide** — the picture shows nothing the text does not say. It is the one place a model is redrawn; re-check it whenever a state or a transition changed.
- **`## Rules and limits`** — `| Rule | Value | Can it be changed? |`; layered configuration adds a `Level` column and one line naming the precedence ("the most specific wins — member, then plan"). The answer in *Can it be changed?* is "on the <screen> screen", "by a deployment setting" or "no — fixed in the system". A hard-coded value is still stated with its number; Level 3 records that it is fixed, usually also an open question.
- **`## Good to know`** — `### <what the person wants to know, in their words>` and an answer that starts with the direct answer ("Yes.", "No.", "Up to 12 months.") and then says what to do instead. It holds only what has no task to live in: what the product does not do, a limit that spans tasks, an unhandled case. It never repeats a row of "If it doesn't go through" or *Rules and limits*, has six entries at most, and **never promises** ("Not yet.", "coming soon" are roadmap claims no code shows). Every answer has an evidence-index row.
- **`## Related areas`** — **Starts from**, **Sets off**, **Shares**, each a short list linking the other area's guide **by name**, in business words from the Edges inventory. The *how* is Level 2.
- **`## Open questions`** — one line saying these are questions for the product owner that the code cannot answer, then `| # | Question | Why it matters |`, numbered `Q1…` (Level 2 continues the numbering). Every hard-coded number of unknown origin, every unhandled case — asked about the **rule**, not the code. **An inferred purpose appears here and nowhere else in Level 1**: the body states what happens, never "appears to exist so that".
- **`## About this document`** — one per line, in this order: `**Id:**` (the `AREA-nnn`; a feature document has none), `**Created:**`, `**Last updated:**` (once the set has been updated), `**Owned by:**`, `**Derived from:**`, `**Audience:**`, `**Models:**` (the FLOW/ENT/DEC links). A feature document carries its `**Generated by …**` line here instead of `Owned by` / `Derived from`.

**Ids.** `AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-` ids appear in Level 1 only inside `## About this document`; `Q<n>` only in the first column of the open-questions table. The KB keeps every id — `INDEX.md`, Level 3 and the models carry them.

**Length.** Under about 2,500 words, counted outside fenced blocks and `## About this document`. When a guide is over, detail moves out in this order until it fits: (1) an outcome the person does not notice → Level 2; (2) a rule nobody meets in a task → Level 3's *Configuration*; (3) a *Good to know* entry → the task it is closest to, as one sentence, or Level 2; (4) example lines beyond the one that shows the rule → `## A <period> in numbers`, or Level 3. Nothing is dropped; it moves down a level. Facts are never trimmed to pass.

---

## Language discipline — by level

The same fact, three ways:

| Level 3 (technical) | Level 2 (behind the scenes) | Level 1 (guide) |
|---|---|---|
| `POST /bookings/{id}/cancel` → 409 when `status != Pending` | The booking service refuses the cancellation and the page shows a message | You can only cancel an order that has not yet shipped |
| unique index `(tenant_id, order_number)` | The order number is checked for clashes when the order is saved | Order numbers are unique within an organisation |
| `BookingConfirmed` via outbox after commit; consumer gets 3 attempts in all, then dead-lettered | Once the booking is saved, the pricing step is told in the background; if it fails it is tried three times in all and then set aside | Your credits are worked out after the booking is confirmed |
| F1: no idempotency key — redelivery double-prices | The same message can arrive twice, and the booking is then priced twice | — (not a client-facing rule) |
| `Math.Ceiling(qty * price * rate * 100) / 100` | — (Level 2 links to Level 1) | SEC fee = ROUNDUP(Qty × Fill price × SEC rate, 2) |

Banned in **Level 1** (and in Level 2, beyond its allowed everyday words): class, method, table and column names, file names, status codes, exception types, framework nouns, inline code, jargon such as *endpoint, payload, handler, middleware, idempotent, eventual consistency*, tier tags, `file:line`, the defect words of discipline 6, and — in Level 1 — internal ids (`AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-`, and `Q<n>` outside the open-questions table's first column) anywhere but `## About this document`. **Bold in Level 1 is only a screen label** as the screen shows it, never emphasis. A word that needs a definition is replaced, not defined. A client's own technical-sounding word ("API keys", "claims handler") stays only when it is listed in the first column of Level 3's *Business ↔ code vocabulary*.

**Guarantee words** — *exactly once, at most one / once, immediately, instantly, as soon as, in real time, right away* — are lint warnings in Levels 1–2: a timing or delivery guarantee is written only when the code shows it and it has an evidence-index row; otherwise reword or ask. **Roadmap promises** — "Not yet.", "coming soon", "in a future version" — are the same kind of claim: no code shows them, so Level 1 never writes them.

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

1. **Lint passes:** `python3 ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/doc-lint.py --dir <folder>` exits 0. Fix every `ERROR`; fix every `WARN` or say in the report why it stands.

Then only what the lint cannot check:

2. Every area from the confirmed map has its set, or is in "What is not documented" with a reason.
3. **The worked example's arithmetic is recomputed** and every number in it equals Level 3's.
4. Every qualifying statement of Levels 1–2 has an evidence-index row — spot-check five.
5. **The three levels agree** — cross-check five facts that appear at more than one level (a threshold, a retry count, a trigger, a name mapping, an actor).
6. The client's terms and the exact refusal messages are used.
7. `INDEX.md`, `active-context.md` and the glossary are updated.
8. Nothing unreachable is documented as a capability.

## Handoffs

- **→ `business-analyst`** — the open questions, the terminology drift, and any contradiction between two areas' rules. It resolves conflicts and records precedence; you never invent it.
- **→ `requirements-author`** — turns confirmed Level 1 documentation into epics and stories once the open questions are answered.
- **→ `qa-test-case-designer`** — Level 1's flows, formulas and worked example are a test basis; Level 3's rules, errors and refused transitions are the negative-test matrix.
- **→ `solution-planner`** — the area map and Level 3 are the inputs to an EXTEND run.
- **→ `code-auditor`** — Level 3's Findings.
- **→ any `be-<stack>` agent or AI assistant about to change the code** — start from Level 3's *Quick facts* and *Code map*; read *Changing this safely* before editing.

## Version policy

Version-agnostic — this skill writes prose, not code. The one version-sensitive input is the **evidence**: `file:line` references are valid only against the commit in each file's `Derived from` stamp. On a refresh, re-verify every citation against the current commit rather than carrying it forward; a citation that has silently drifted to a different line is worse than no citation.
