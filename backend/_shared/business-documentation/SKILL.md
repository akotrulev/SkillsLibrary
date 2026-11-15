---
name: doc-business-model
description: Use when traced behavior must be written up as a user guide for every role, admins included, with a few screenshots. Triggers "turn this trace into docs". Not for tracing code (doc-feature-trace).
---

# Business Documentation — one trace, one guide, every user

Every area (and every feature) is written **once, as a guide**: what each person who uses it — customers, members, staff, **administrators** — can do there, step by step, in the words the product shows them, with a few screenshots of the running product where a picture saves a paragraph. There is no second, technical document: the guide is the documentation.

| File | Reader | Audience | Language | Answers |
|---|---|---|---|---|
| `<name>.md` | Every user of the product, the client, product owner, support | `shareable` | Plain. No technical talk at all | Who uses this, what can I do here, where do I do it, what happens when I do, show me with numbers |

**Load only when needed:**

| Writing | Load |
|---|---|
| An area or feature guide | nothing extra — the shape is below |
| `system-overview.md` | [`references/system-overview.md`](references/system-overview.md) |
| Checking tone or shape against a model | the golden example, [`references/example-area.md`](references/example-area.md) |

Six disciplines carry the whole skill:

1. **Write for the person, and stay plain.** The guide never says "handler", "endpoint" or a class name. If a sentence would make a non-technical user ask "what does that mean?", it does not belong here.
2. **Never let inference pass as fact.** The guide states what the product does — the trace read it in the code this session. What you think a rule is *for* is never stated: it is a row in *Open questions*. "The code enforces X; I could not determine why" is a complete answer.
3. **Simple, flows, examples.** Every guide reads the same way: who uses it → how it fits together → each person's tasks in lifecycle order → **examples beside the rule they show**.
4. **Every person, administrators included.** Every role the trace found acting in the area — the person who uses the product, the one who runs it, the administrator who configures it — is a row in *Who uses it* and has its own `## For <role>` section. Administration screens are tasks, not footnotes.
5. **A few screenshots, never one per step.** At most one per task, of the running product, where it saves words (see *Screenshots*).
6. **Describe, never judge.** Behaviour is stated factually and neutrally ("the credits are returned twice"). The words *bug, defect, flaw, broken, wrong, mistake, vulnerability* and *should have* never appear — the lint warns on each; text quoted verbatim from the product is exempt. A defect found while tracing goes to the run's report, routed to `code-auditor`, never into the guide.

**Prerequisites:** a confirmed area map (`dev:doc-codebase-survey`) or feature scope, per-area evidence (`dev:doc-feature-trace`) including its `Client vocabulary` table and the verbatim refusal texts in inventory 3, and **a running environment of the product with a test login for every role** (see *Screenshots*). **When `docs/business-model/` exists or is being written, load `business-analysis:knowledge-base` first** — it owns the KB layout, IDs, annotation grammar, and the read-first/update-after contract; a standalone feature run without a KB skips it.

**The golden example is an illustration, never a source.** Every fact, number, currency, message, actor and screenshot in a guide comes from this run's trace and this run's capture. A claim that appears in the example but that the trace did not find (a currency symbol, who sets a rate, a message text) is not written — it becomes an open question.

## When to use

- Steps 4–5 of a `be-documenter` run, and Step 3 of a `be-feature-documenter` run
- A traced area needs its guide refreshed after the code moved

## When NOT to use

- The code has not been traced yet → `dev:doc-feature-trace`
- The deliverable is requirements for work *to be done* → `requirements-author`
- The deliverable is defects → `dev:audit-feature`

## Output — into the KB, under its contract

Everything lands in **`docs/business-model/`**, per `business-analysis:knowledge-base`. A standalone feature (`be-feature-documenter`) writes one guide under `docs/features/` with `<NNN>-<slug>` as the name.

| File | Owner | This skill's role |
|---|---|---|
| `areas/<area>.md` (`AREA-nnn`) | **this skill** | The area's guide |
| `areas/screenshots/<area>/<task>.png` | **this skill** | The guide's screenshots |
| `system-overview.md` | **this skill** | The guide to the whole system |
| `glossary.md` | shared | Terms, the client's own words, and the business ↔ code mapping |
| `INDEX.md`, `active-context.md` | shared | Updated per the KB contract. **One `INDEX.md` line per area**, in this shape and no other (lint `index-line`): `- [<Area name>](areas/<name>.md) — AREA-nnn · <who, comma-separated> · <what a person does there, at most 20 words> · @ \`<sha>\``. The description is the area's row in the overview's `## Areas, by who uses them`. An existing line is edited into the shape together with its guide, never regenerated |
| `events.md`, `shared-data.md`, `invariants.md` | `business-analysis:dependency-map` | **Not yours.** |
| `flows/`, `entities/`, `decisions/` | `process-flow` · `state-grid` · `decision-table` | **Not yours.** You link to them by ID in *About this document* |

A feature guide's screenshots go in `docs/features/screenshots/<NNN>-<slug>/`.

**Golden example** — the `workshop-booking` toy system as an inherited codebase, one area: [`references/example-area.md`](references/example-area.md). Shape, tone, example discipline and screenshot discipline are normative; the domain content is illustrative.

---

## The guide

**Greenfield or brownfield.** A FULL run on a project with no documentation writes this shape directly. A run on existing documentation **updates it in place** into this shape and never recreates it — the *Reconcile procedure* says how.

It reads in the order a person meets the product: who uses it, the few ideas and one picture of how it fits together, then each person's tasks in the order life happens.

```markdown
# <Area name>

<One sentence, the client's words: what a person can do here.>

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

Optional sections are **dropped** when they do not apply — never padded.

**Order of the people.** `## Who uses it` lists people in the order they meet the area (the customer who places an order before the owner who accepts it, the owner before the administrator who configures the shop); the `## For <person>` sections follow that order, and inside each section the tasks follow the record's lifecycle (place → find again → cancel → rate → order again). The heading is `## For <plural or role>` — `## For customers`, `## For the owner`, `## For administrators`. The guide's open questions stay under `## Open questions`; a `## For …` heading is always a person's tasks.

**Administrators.** Settings, user and role management, approvals, imports and anything else a privileged person does on a back-office screen are tasks under `## For administrators` (or the role's own name), written exactly like any other person's: a `**Where:**` path, their steps, what happens next, a screenshot where it helps. *Rules and limits* says which values they can change ("on the <screen> screen") and links the task that changes them.

**The client's words.** Name things the way the client's own product names them — the button labels, screen titles, email wording and messages harvested in the trace's `Client vocabulary` table and seen on the running screen — not the way the code names them. In a KB run every term used goes to the glossary with its code name.

**A task:**

````markdown
### Cancel an order

You can cancel an order yourself until the shop starts working on it; after that you ask.

**Where:** **Your orders** → the order → **Cancel order**

![The order page, with the Cancel order button below the order summary](screenshots/ordering/cancel-an-order.png)

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
- **Bold is a screen label, and a label is evidence.** In a `**Where:**` line and in the person's steps, bold is only ever a label exactly as the running screen shows it — the same text the trace's `Client vocabulary` holds. Never invent a button.
- **`**Where:**`** is the arrow path from the trace's `Where in the product` column (screen › control), checked on the running screen. A task reached through another channel names it without bold (`**Where:** your own AI assistant, through the shop's order tool`).
- **No screen** — the person does this through an API, an email, an outside system, or the screen is not part of the product you were given: the task has no `**Where:**` line, no bold label and no screenshot, and its steps say what the person asks for in plain verbs ("Ask to cancel the booking"). When no screen was found for the whole area, one open question asks where people do this.
- **The person's steps are numbered; "What happens next" is a bulleted list of outcomes.** An outcome is something the person sees, receives or is charged; alternatives are separate bullets starting "If …". The system's internal checks and bookkeeping are not written. An outcome that computes keeps the formula block: `Name = expression` on its own line, then `Where:`. Plain-text math (`×`, `SUM`, `ROUNDUP(x, 2)`), never code; rounding, day-count conventions and currency conversion are part of the formula, and the number is exact.
- **At most seven steps and five outcomes**; a task that needs more is two tasks.
- **Task headings are unique in the guide**: a task two people do is named for each ("Cancel a booking" under members, "Cancel a member's booking" under staff), the second one short and pointing at the first by name.
- **Automatic work** — a `###` under `## What happens automatically` — keeps the flow shape, because nobody acts: `**Trigger:**`, numbered steps in business verbs, `**Result:**`. It has no screenshot.
- **"If it doesn't go through"** — only where the product refuses with a user-visible outcome. *What you see* **quotes the exact message** from the trace's inventory 3, never a paraphrase; the third column is what to do, not what the system does. Drop the table when nothing is refused.
- **An example sits inside the task that computes**, as `**Example**` and a few lines or a small table, numbers carried to the result. `## A <period> in numbers` exists only when one story's numbers carry across several tasks (credits spent on booking, returned on cancelling, posted at month end); it replaces a task example. Every number used as a rule is the code's exact value; every arithmetic line is shown and recomputed before handing off; invent only the incidental (names, dates, quantities) with one running cast; an example illustrates, never extends — where the code is silent, the example stops and the gap is an open question.
- **Callouts** are GFM alerts and only four kinds: `[!IMPORTANT]` (a rule that governs — never a bold **Important:**), `[!NOTE]` (a prerequisite or where something else is handled), `[!TIP]` (a shortcut), `[!WARNING]` (an action that cannot be undone or that charges money — nothing else). At most one inside a task.
- **`## How it fits together`** holds the key ideas, then the picture; it is left out only when the area has one task, no states and no term to explain.
  - **Key ideas** — up to six `**Term** — one line` entries: the words the tasks use that a new reader would not know, and any concept that is not a task.
  - **One Mermaid diagram**, nine nodes at most, labels in the client's words, node ids single lowercase words: a `stateDiagram-v2` of the area's main record when it has states, otherwise a `flowchart LR` (labels in double quotes) of the people and what passes between them. It is drawn from the trace's states and transitions and agrees with the `ENT-nnn` grid where the KB has one. **Every arrow is a task or automatic work in this guide** — the picture shows nothing the text does not say. Re-check it whenever a state or a transition changed.
- **`## Rules and limits`** — `| Rule | Value | Can it be changed? |`; layered configuration adds a `Level` column and one line naming the precedence ("the most specific wins — member, then plan"). The answer in *Can it be changed?* is "on the <screen> screen", "by a deployment setting" or "no — fixed in the system". A hard-coded value is still stated with its number, usually also an open question.
- **`## Good to know`** — `### <what the person wants to know, in their words>` and an answer that starts with the direct answer ("Yes.", "No.", "Up to 12 months.") and then says what to do instead. It holds only what has no task to live in: what the product does not do, a limit that spans tasks, an unhandled case. It never repeats a row of "If it doesn't go through" or *Rules and limits*, has six entries at most, and **never promises** ("Not yet.", "coming soon" are roadmap claims no code shows).
- **`## Related areas`** — **Starts from**, **Sets off**, **Shares**, each a short list linking the other area's guide **by name**, in business words from the Edges inventory.
- **`## Open questions`** — one line saying these are questions for the product owner that the code cannot answer, then `| # | Question | Why it matters |`, numbered `Q1…`. Every hard-coded number of unknown origin, every unhandled case — asked about the **rule**, not the code. **An inferred purpose appears here and nowhere else**: the body states what happens, never "appears to exist so that".
- **`## About this document`** — one per line, in this order: `**Id:**` (the `AREA-nnn`; a feature guide has none), `**Created:**`, `**Last updated:**` (once the guide has been updated), `**Owned by:**` (`dev:doc-business-model`), `**Derived from:**` (`code by be-documenter @ \`<commit sha>\` on YYYY-MM-DD`), `**Audience:** shareable`, `**Screenshots:**` (`captured from <environment name, never its address> on YYYY-MM-DD`), `**Models:**` (the FLOW/ENT/DEC links). A feature guide carries `**Generated by \`be-feature-documenter\` @ <commit> on <date>**` instead of `Owned by` / `Derived from`.

**Ids.** `AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-` ids appear only inside `## About this document`; `Q<n>` only in the first column of the open-questions table. The KB keeps every id — `INDEX.md` and the models carry them.

**Length.** Under about 2,500 words, counted outside fenced blocks and `## About this document`. When a guide is over, cut in this order until it fits: (1) an outcome the person does not notice; (2) a rule nobody meets in a task, unless an administrator changes it; (3) a *Good to know* entry → the task it is closest to, as one sentence; (4) example lines beyond the one that shows the rule → `## A <period> in numbers`. A guide still over splits by person: the administrators' tasks become their own guide, linked from *Related areas*. A fact a person meets in a task is never trimmed to pass.

---

## Screenshots

A screenshot shows a person where they are and what they are looking at. It replaces a paragraph of "on the left, below the summary…"; it never replaces the steps.

**Where they come from: the running product, captured by you.** Before writing, the run has the address of a running, **non-production** environment and a test login for every person in *Who uses it* that has a screen — administrators included. Without them the run **stops and asks**; it never captures from production, a design file, a mock-up or the code. Only the person can waive screenshots (for example, the screens live in a product nobody can run); a waived guide records `**Screenshots:** waived — <the person's reason>` in *About this document* and holds none. Logins are used in the browser and nowhere else: never written into a guide, the orientation cache, a plan, a trace or the report.

**How many — few.**

- **At most one per task**, and only for a task with a `**Where:**` line. Never one per step, never one of automatic work, never one in *Rules and limits*, *Good to know* or the overview.
- **Pick the tasks where the picture saves the most words**: the first time a person meets a screen, a form with several fields, a busy administration screen, a path with three or more arrows. Skip a task whose screen an earlier screenshot in the guide already shows.
- **Six per guide at most** (lint WARN beyond); a guide whose tasks have screens has at least one (lint ERROR when none and not waived).

**What it shows.**

- The task's screen in the state the task describes, with the control from the `**Where:**` line visible. When the task has an `**Example**`, the screen shows the example's values (Ana, the Basic plan, £6.00) so the picture and the text agree.
- Desktop viewport, 1280 × 800, the visible window only — not a full-page scroll. Crop to one region (a dialog, a form) when the rest of the screen is noise.
- **Test data only.** No real person's name, email or payment detail, no secret, key or token, no internal address. If a screen cannot be shown without one, choose another record or ask.
- Every bold label the task's steps name is visible on it and spelled the same. When the running screen's label differs from the code's text, the screen wins and the difference is an open question.

**How it is written and filed.**

- Right under the `**Where:**` line: `![<what the screen shows, one sentence in the client's words>](screenshots/<guide-name>/<task-slug>.png)`. The alt text is mandatory — it is what a screen reader and a reader without images get.
- The file sits beside the guide at that relative path: `areas/screenshots/<area>/`, `docs/features/screenshots/<NNN>-<slug>/`. `<task-slug>` is the task heading in kebab case. PNG.
- Capture with the browser tools the agent grants (`browser_navigate`, sign in, act, then `browser_take_screenshot`), and move the file into place when the tool saved it elsewhere.
- Screenshots are committed with the guide — they are part of it. On an update, a task whose screen or steps changed is captured again; a screenshot whose task is gone is deleted.

---

## Language discipline

The same fact, as the code says it and as the guide says it:

| In the code | In the guide |
|---|---|
| `POST /bookings/{id}/cancel` → 409 when `status != Pending` | You can only cancel an order that has not yet shipped |
| unique index `(tenant_id, order_number)` | Order numbers are unique within an organisation |
| `BookingConfirmed` via outbox after commit | Your credits are worked out after the booking is confirmed |
| `Math.Ceiling(qty * price * rate * 100) / 100` | SEC fee = ROUNDUP(Qty × Fill price × SEC rate, 2) |
| `[Authorize(Roles = "Admin")]` on `PUT /plans/{id}` | Only administrators can change a plan |

Banned in the guide: class, method, table and column names, file names, status codes, exception types, framework nouns, inline code, jargon such as *endpoint, payload, handler, middleware, idempotent, eventual consistency*, tier tags, `file:line`, the judging words of discipline 6, and internal ids (`AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-`, and `Q<n>` outside the open-questions table's first column) anywhere but `## About this document`. **Bold is only a screen label** as the screen shows it, never emphasis. A word that needs a definition is replaced, not defined. A client's own technical-sounding word ("API keys", "claims handler") stays when the product itself shows it — as a bold label, or a key idea.

**Guarantee words** — *exactly once, at most one / once, immediately, instantly, as soon as, in real time, right away* — are lint warnings: a timing or delivery guarantee is written only when the code shows it; otherwise reword or ask. **Roadmap promises** — "Not yet.", "coming soon", "in a future version" — are the same kind of claim: no code shows them, so the guide never writes them.

## Glossary (KB runs)

Every domain term found, with its business meaning and the **mapping between the vocabularies** — the client's own term (from the trace's `Client vocabulary` table), what it means, and what the code calls it:

| Term (client) | Means | Called in code | Where the client sees it | Notes |
|---|---|---|---|---|
| Order | A confirmed purchase, from placement to delivery | `Order`, `PurchaseOrder` (legacy) | order confirmation email | Two names for one concept `#observed` |
| Account | The billing relationship, not the login | `Customer` | invoice header | **Drift:** "customer" means the *person* in Identity, the *billing entity* in Billing `#observed` |

**Terminology drift is a finding, not a merge** — record both, flag it, and let `business-analyst` resolve it.

## Reconcile procedure (every run that finds an existing guide)

1. **Check staleness.** Read the guide's `Derived from` (or `Generated by`) sha, compare it with `HEAD` and the git delta for the area's paths, and report whether it is stale.
2. **Existing documentation is updated in place — never deleted and regenerated, never rewritten from a fresh trace and compared.**
   1. **Same file, same history.** The guide is edited. `Created` is kept, a `Last updated` line is added, and `~~old~~ → new` marks every changed fact.
   2. **An old-shape guide** (`## How it works` and no `## Who uses it`; an overview with `## The areas`) moves each statement under its new section: a flow to the `### <task>` under the `## For <person>` it belongs to; a system check the person does not notice is dropped; Setup to `## Rules and limits`; How it connects to `## Related areas`; Who can do what to `## Who uses it`; the end example to the task it illustrates, or `## A <period> in numbers`; inline ids to `## About this document`; inferred purposes to `## Open questions`. Wording changes only where the shape demands it.
   3. **Retired levels.** A `<name>.behind-the-scenes.md` or `<name>.technical*.md` beside the guide is from the three-level shape: read it as a lead for the update (a person or a screen it names that the guide lacks), then delete it — git keeps its history. The lint's `retired-level` WARN lists every one left.
   4. **Add only what the shape needs** — the `Who uses it` table (every role, administrators included), key ideas, `**Where:**` paths and labels, the diagram, callouts, screenshots — from a **targeted** lookup (the UI routes and labels per `feature-trace`'s recipes, the running screen), not a full re-trace.
   5. **Re-trace only the code delta** — `git diff <sha>..HEAD` over the area's paths. No delta, no re-trace.
   6. **Check it, do not trust it.** Close the update with `doc-lint.py --kept-from <the guide's old sha, or the commit before the update> --dir <folder>`: every `fact-kept` WARN is a number or quoted message the old guide had and the new one has not — restore it, or name in the report the code change that removed it. The `INDEX.md` line is edited into its shape in the same update.
3. **Verdict every statement** against the re-trace: **Agrees** · **New** · **Gone** · **Contradicts**.
4. **Update, don't rewrite** — `~~old~~ → new` keeps one generation of history inline and marks a changed **fact**; moving a statement to its new section is a layout move and is never struck through. Re-check the diagram whenever a state or a transition changed; re-run the example's arithmetic whenever a number it uses changed; re-capture the screenshot of every task whose screen or steps changed.
5. **`Gone` needs care.** Say whether the feature was removed or your trace did not find it; never delete a `#confirmed` KB statement on the strength of a failed search.
6. **`Contradicts` escalates.** Present the documented statement, the code's behaviour, and both readings — *stale documentation* vs *code defect*. Never silently pick one.
7. **Re-stamp** the guide with the new sha and a `Last updated` line, and log the session in `active-context.md` (KB runs).

## Self-check before handing off

1. **Lint passes:** `python3 ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/doc-lint.py --dir <folder>` exits 0. Fix every `ERROR`; fix every `WARN` or say in the report why it stands.

Then only what the lint cannot check:

2. Every area from the confirmed map has its guide, or is in "What is not documented" with a reason. **An `old-shape` or `retired-level` WARN means that guide is not done.**
3. **Every role is there.** Each role the trace found acting in the area — administrators included — is in *Who uses it* and has its `## For <role>` section.
4. **The worked example's arithmetic is recomputed** and every number it uses as a rule is the code's exact value.
5. **Five statements spot-checked against the code** at random (a threshold, a refusal message, a step, an outcome, a who-can-do-it); one wrong means re-checking its whole task.
6. **Every screenshot looked at** once more: it is this task's screen, its labels match the steps, its data is test data, and nothing secret shows.
7. The client's terms and the exact refusal messages are used.
8. `INDEX.md`, `active-context.md` and the glossary are updated (KB runs).
9. Nothing unreachable is documented as a capability.

## Sharing a guide

A client reads a page, not a markdown file. `render-html.py` turns guides into standalone pages — a table of contents, styled alerts, tables, the screenshots embedded, the diagram drawn — and never writes into the KB:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/render-html.py --out <dir> --dir docs/business-model
uv run ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/render-html.py --out <dir> docs/features/<NNN>-<slug>.md
```

- **Rendered on demand, never committed.** Markdown and its screenshots stay the only source. Render again after every update and send the new files.
- `--dir` renders every guide under it marked `**Audience:** shareable`; a named file is rendered as given.
- **One file per guide.** Screenshots are embedded in the page, so it can be sent on its own.
- **The page carries nothing internal:** the About section becomes "Last updated <date>"; a `~~old~~ → new` mark shows only `new`; links to other guides point to the matching `.html` file, so send a set's pages together.
- **Offline, the reader loses the diagram only.** The only request a page makes is the pinned Mermaid script; without it the diagram shows as "This diagram needs an internet connection" and every arrow is still a task in the text.

## Handoffs

- **→ `business-analyst`** — the open questions, the terminology drift, and any contradiction between two areas' rules. It resolves conflicts and records precedence; you never invent it.
- **→ `requirements-author`** — turns confirmed guides into epics and stories once the open questions are answered.
- **→ `qa-test-case-designer`** — the guide's tasks, refusals, formulas and worked examples are a test basis.
- **→ `solution-planner`** — the area map and the KB models are the inputs to an EXTEND run.
- **→ `code-auditor`** — the defects the trace found, from the run's report.

## Version policy

Version-agnostic — this skill writes prose, not code. The guide is valid against the commit in its `Derived from` stamp and the screenshots against the capture date in *About this document*; on a refresh, re-check both rather than carrying them forward.
