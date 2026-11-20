---
name: doc-business-model
description: Use when traced behavior must be written up as a user guide for every role, admins included, or as a plan's delivery note. Trigger "turn this trace into docs". Not for tracing code.
disable-model-invocation: true
---

# Business Documentation — one trace, one guide, every user

Every area (and every feature) is written **once, as a guide**: what each person who uses it — customers, members, staff, **administrators** — can do there, step by step, in the words the product shows them, which rules apply and how a figure is calculated, with a few screenshots where a picture saves a paragraph. There is no second, technical document. Three readers: **end users** (what do I do, what happens), **business analysts** (which rules apply, how is it calculated) and **product owners** (what was built, what changed, what is still open).

| File | Reader | Audience | Language | Answers |
|---|---|---|---|---|
| `<name>.md` | Every user of the product, business analysts, the client, product owner, support | `shareable` | Plain. No technical talk at all | Who uses this, what can I do here, where, what happens, which rules apply, how it is calculated, what is open |
| `docs/deliveries/<NNN>-<plan-slug>.md` | Product owner | `shareable` | Plain. Same language rules | What a plan delivered, what works differently now, what was planned and is not there |

**Load only when needed:** an area or feature guide needs nothing extra beyond the loads named in its sections below; `system-overview.md` → [`references/system-overview.md`](references/system-overview.md); a delivery note (the `DOC1` run of a plan) → [`references/delivery-note.md`](references/delivery-note.md); tone or shape against a model → the golden example, [`references/example-area.md`](references/example-area.md).

Six disciplines:

1. **Write for the person, and stay plain.** Never "handler", "endpoint" or a class name; a sentence that would make a non-technical user ask "what does that mean?" does not belong.
2. **Never let inference pass as fact.** The guide states what the product does, as the trace read it in the code this session. A purpose is stated only from the three sources in *Where a purpose may come from*; anything else a rule might be *for* is a row in *Open questions*. "The code enforces X; I could not determine why" is a complete answer.
3. **Simple, flows, examples.** Every guide reads: in short → who uses it → how it fits together → each person's tasks in lifecycle order → every rule in one table → the calculations, with **examples beside the rule they show**.
4. **Every person, administrators included.** Every role the trace found acting in the area is a row in *Who uses it* and has its own `## For <role>` section. Administration screens are tasks, not footnotes.
5. **A few screenshots, never one per step** (see *Screenshots*).
6. **Describe, never judge.** Behaviour is stated neutrally ("the credits are returned twice"). The words *bug, defect, flaw, broken, wrong, mistake, vulnerability* and *should have* never appear (lint WARN; text quoted verbatim from the product is exempt). A defect found while tracing goes to the run's report, routed to `code-auditor`, never into the guide; where the code and a story disagree the guide states what the code does and the difference goes to the delivery note's *Not delivered* and the report.

**Prerequisites:** a confirmed area map (`dev:doc-codebase-survey`) or feature scope, and per-area evidence (`dev:doc-feature-trace`) including its `Tasks` inventory, its `Client vocabulary` table and the verbatim refusal texts of its `Validations & gates`. A non-production environment with a test login per role is wanted for screenshots and never blocks the text. **When `docs/business-model/` exists or is being written, load `business-analysis:knowledge-base` first** — it owns the KB layout, IDs, annotation grammar, and the read-first/update-after contract; a standalone feature run without a KB skips it.

**The golden example** — the `workshop-booking` toy system as an inherited codebase, one area: [`references/example-area.md`](references/example-area.md). Shape, tone, example and screenshot discipline are normative; the domain content is an illustration, never a source. Every fact, number, currency, message, actor and screenshot in a guide comes from this run's trace and capture; a claim the trace did not find (a currency symbol, who sets a rate, a message text) becomes an open question.

## Output — into the KB, under its contract

Everything lands in **`docs/business-model/`**, per `business-analysis:knowledge-base`. A standalone feature (`be-feature-documenter`) writes one guide under `docs/features/<NNN>-<slug>.md`, its screenshots in `docs/features/screenshots/<NNN>-<slug>/`.

| File | Owner | This skill's role |
|---|---|---|
| `areas/<area>.md` (`AREA-nnn`) | **this skill** | The area's guide |
| `areas/screenshots/<area>/<task>.png` | **this skill** | The guide's screenshots |
| `docs/deliveries/<NNN>-<plan-slug>.md` | **this skill** | The delivery note — written only by a delivery plan's `DOC1` task, by both documenter agents; shape in [`references/delivery-note.md`](references/delivery-note.md) |
| `system-overview.md` | **this skill** | The guide to the whole system |
| `glossary.md` | shared | Terms, the client's own words, and the business ↔ code mapping |
| `INDEX.md`, `active-context.md` | shared | Updated per the KB contract. **One `INDEX.md` line per area**, in this shape and no other (lint `index-line`): `- [<Area name>](areas/<name>.md) — AREA-nnn · <who, comma-separated> · <what a person does there, at most 20 words> · @ \`<sha>\``. The description is the area's row in the overview's `## Areas, by who uses them`. An existing line is edited into the shape together with its guide, never regenerated |
| `events.md`, `shared-data.md`, `invariants.md` | `business-analysis:dependency-map` | **Not yours.** |
| `flows/`, `entities/`, `decisions/` | `process-flow` · `state-grid` · `decision-table` | **Not yours.** You link to them by ID in the stamp comment |

---

## The guide

**Greenfield or brownfield.** A FULL run on a project with no documentation writes this shape directly; a run on existing documentation **updates it in place** — see the *Reconcile procedure*. It reads in the order a person meets the product.

```markdown
# <Area name>

<One sentence, the client's words: what a person can do here.>

> [!IMPORTANT]
> <The one rule that governs everything below.>          ← optional

## In short                                                 ← three to five bullets, always first

## Who uses it
| Who | What they do here |

## How it fits together                                    ← key ideas, then one Mermaid diagram
## For <person>                                             ← one per person in "Who uses it", in that table's order
### <Task — what the person does: "Place an order">
## What happens automatically                               ← optional: scheduled and event-started work
### <Work — named by what it does: "Monthly posting">
## Rules and limits                                         ← every business rule the guide states
## How it is calculated                                     ← optional: the formulas live here
### <What is calculated, in the client's words>
## A <period> in numbers                                    ← optional: one story whose numbers carry across tasks
## Good to know                                             ← optional
## See also                                                 ← optional: other guides, one line each
## Open questions                                           ← for the product owner
## About this document                                      ← reader lines, then one stamp comment
```

Optional sections are **dropped** when they do not apply, never padded. *Rules and limits* is left out only when the trace found no rule at all (a pass-through) and the report says so.

**Order of the people.** `## Who uses it` lists people in the order they meet the area (customer, then owner, then the administrator who configures the shop); the `## For <person>` sections follow that order, and inside each the tasks follow the record's lifecycle (place → find again → cancel → rate → order again). The heading is `## For customers`, `## For the owner`, `## For administrators`; a `## For …` heading is always a person's tasks.

**Administrators.** Settings, user and role management, approvals, imports and anything else a privileged person does on a back-office screen are tasks under `## For administrators` (or the role's name), written like any person's. *Rules and limits* says which values they can change ("on the <screen> screen") and names the task that changes them.

**The client's words.** Name things the way the client's product names them — the labels, titles, email wording and messages in the trace's `Client vocabulary` table and on the running screen — not the way the code names them. In a KB run every term used goes to the glossary with its code name.

**The tasks come from what people do:** the `###` tasks are the rows of the trace's `Tasks` inventory, never one per endpoint. Work no task reaches is automatic work or a task with no screen.

**A task** is a `### <what the person does>` heading, then one sentence of when it applies, `**Where:**`, the screenshot (when it has one), numbered steps, `**What happens next**` (bullets), `**If it doesn't go through**` (a `| Situation | What you see | What to do |` table), and at most one callout. The golden example shows one in full.

- **Second person, imperative, to the person the section names.** Field names in *italics*. **One idea per sentence.**
- **Bold is a screen label, and a label is evidence:** in a `**Where:**` line and the steps, bold is only a label exactly as the trace's `Client vocabulary` holds it, confirmed on the running screen when there is one. Never invent a button.
- **`**Where:**`** is the arrow path from the trace's `Where in the product` column (screen › control), checked on the running screen when there is one. A task reached through another channel names it without bold (`**Where:** your own AI assistant, through the shop's order tool`).
- **No screen** — the person acts through an API, an email, an outside system, or the screen is not in the product you were given: no `**Where:**` line, no bold label, no screenshot, and the steps say what the person asks for in plain verbs ("Ask to cancel the booking"). When no screen was found for the whole area, one open question asks where people do this.
- **Steps are numbered; "What happens next" is bulleted outcomes** — something the person sees, receives or is charged; alternatives are separate bullets starting "If …". Internal checks and bookkeeping are not written. **A task holds no formula**: an outcome that computes says the result in one sentence and points at the calculation ("…the shortfall is charged as an overage — see *How it is calculated*").
- **At most seven steps and five outcomes**; a task that needs more is two tasks.
- **Task headings are unique in the guide**: a task two people do is named for each ("Cancel a booking" under members, "Cancel a member's booking" under staff), the second short and pointing at the first.
- **"If it doesn't go through"** — only where the product refuses with a user-visible outcome. *What you see* **quotes the exact message** from the trace's `Validations & gates`; the third column is what to do. Dropped when nothing is refused.
- **An example stays inside the task that computes**, as `**Example**` and a few lines or a small table, numbers carried to the result; arithmetic lines (`Name = expression = result`) appear only after that marker. `## A <period> in numbers` exists when one story's numbers carry across several tasks (spent on booking, returned on cancelling, posted at month end) and replaces a task example. Every rule number is the code's exact value and every arithmetic line is shown and recomputed; invent only the incidental (names, dates, quantities) with one running cast. An example illustrates, never extends: where the code is silent it stops and the gap is an open question.
- **Callouts** are GFM alerts, four kinds only: `[!IMPORTANT]` (a governing rule, never a bold **Important:**), `[!NOTE]` (a prerequisite, or where something else is handled), `[!TIP]` (a shortcut), `[!WARNING]` (an action that cannot be undone or that charges money, nothing else). At most one inside a task.

**The sections around the tasks:**

- **`## In short`** — three to five bullets, one sentence each, for a reader who reads nothing else: what people can do here, the rules that matter most **with their numbers**, and what happens without anyone acting. No bold, no links, no formula, nothing the body does not state again.
- **`## How it fits together`** holds the key ideas, then the picture; it is left out only when the area has one task, no states and no term to explain.
  - **Key ideas** — up to six `**Term** — one line` entries: words the tasks use that a new reader would not know, and concepts that are not tasks.
  - **One Mermaid diagram**, nine nodes at most, labels in the client's words, node ids single lowercase words. **Default: `flowchart LR`** (labels in double quotes) of the people and what happens in order — who does what, what follows. **`stateDiagram-v2` only when the product itself shows the person a status** (a status label on a screen or in a message, present in the trace's `Client vocabulary`): its states are those labels, spelled the same, and a bookkeeping state the person never sees is never drawn. **Every node and arrow label is something the guide says** (a task, automatic work, an outcome); re-check it whenever a task, state or transition changed.
- **`## What happens automatically`** — a `###` per piece of scheduled or event-started work, told from the person's side, with no screenshot: `**When:**` says the moment or the event, for whom (e.g. "the 1st of every month at 00:00, for every member"), then `**What people notice**` with at most five bullets, each something a named person sees, receives, is charged or loses. No numbered system steps, no bookkeeping ("mark as posted", "sum the accruals"); work nobody ever notices is not written.
- **`## Rules and limits`** — **the one place every business rule is listed.** Every rule the guide states anywhere (threshold, cut-off, limit, eligibility condition, what a change affects, configurable value) is a row, in the order a person meets them: `| Rule | Value | Where you meet it | Can it be changed? |`.
  - *Where you meet it* names the task or automatic work by its heading, in italics (`*Cancel a booking*`); a rule spanning several says "everywhere".
  - *Can it be changed?* is "on the <screen> screen", "by a deployment setting" or "no — fixed in the system". A hard-coded value is still stated with its number, usually also an open question.
  - Layered configuration adds a `Level` column after `Rule` and one line above the table naming the precedence ("the most specific wins — member, then plan").
- **`## How it is calculated`** — present whenever anything is calculated; left out otherwise. One `### <what is calculated, in the client's words>` per calculation, and under it the formula block: `Name = expression` on its own line, then `Where:`. Plain-text math (`×`, `SUM`, `ROUNDUP(x, 2)`), never code; rounding, day-count conventions and currency conversion are part of the formula, and the number is exact. The task that uses it keeps its `**Example**`.
- **`## Good to know`** — `### <what the person wants to know, in their words>`, answered directly first ("Yes.", "No.", "Up to 12 months.") and then what to do instead. Only what has no task to live in: what the product does not do, a limit spanning tasks, an unhandled case. Never repeats a row of "If it doesn't go through" or *Rules and limits*; six entries at most; **never promises** ("Not yet.", "coming soon").
- **`## See also`** — a plain list of six entries at most: `- [<Guide name>](<file>.md) — <why a person would go there, one line>`. Nothing about which area owns, reads or writes what: that lives in the KB's dependency map. Dropped when there is nothing to point at.
- **`## Open questions`** — one line saying these are questions for the product owner that the code cannot answer, then `| # | Question | Why it matters | Answer |`, numbered `Q1…`, never renumbered or reused. *Answer* stays empty until a person fills it, in the file or the request that starts a run; the next run folds it into the body (*Reconcile procedure*). Every hard-coded number of unknown origin, unhandled case and unsourced purpose is asked about the **rule**, not the code. **An inferred purpose appears here and nowhere else**: the body never says "appears to exist so that".
- **`## About this document`** — reader lines, then one stamp comment as the last line of the file:

  ```markdown
  ## About this document

  **Created:** 2026-08-02
  **Last updated:** 2026-09-14
  **Describes:** the product as it was on 2026-09-14
  **Screenshots:** captured from the staging environment on 2026-09-14

  <!-- guide · id: AREA-004 · owner: dev:doc-business-model · source: be-documenter @ a3f9c21 · models: FLOW-004, ENT-003, DEC-002 · stories: US4, US7 · audience: shareable -->
  ```

  - `**Created:**` always; `**Last updated:**` once updated; `**Describes:**` the date the product was read.
  - `**Screenshots:**` is one of `captured from <environment name, never its address> on YYYY-MM-DD` · `pending — <why>` · `waived — <the person's reason>` · absent when the guide has no screen at all.
  - The stamp is `key: value` pairs separated by ` · `, opening with the word `guide`. Keys: `id` (area guides only, `AREA-nnn`), `owner` (area guides and the overview: `dev:doc-business-model`), `source` (`be-documenter @ <sha>` or `be-feature-documenter @ <sha>`), `models` (KB runs: the FLOW/ENT/DEC ids, optional), `stories` (the story ids a purpose was taken from, optional), `audience` (`shareable`). It is the only place internal and story ids appear.

**Where a purpose may come from.** Behaviour comes from the code and only from the code. A purpose is stated in the body, in one plain sentence, only when one of these says it:

1. a person's answer in *Open questions* (folded in by the next run);
2. the stories of the plan that built it — `docs/plans/<NNN>-<initiative>/requirements.md`, `epics.md`, `stories.md` (`US<n>`, `AC<k>`), also under `docs/plans/implemented/`, which the product owner approved;
3. a `#confirmed` entry in the KB.

Otherwise it is an open question. Where the code and a story disagree, the guide states what the code does; the difference goes to the delivery note and the report, never into the guide as intended behaviour or as a judging word. Story ids never appear in the body; the ones used go in the stamp's `stories`.

**Length.** Under about 2,500 words, counted outside fenced blocks, `## About this document` and the stamp comment. When over, cut in this order until it fits: (1) an outcome the person does not notice; (2) a rule nobody meets in a task, unless an administrator changes it — statement and row together; (3) a *Good to know* entry → one sentence in the closest task; (4) example lines beyond the one that shows the rule → `## A <period> in numbers`; (5) *See also* entries a person would not go to. Still over: split by person, the administrators' tasks becoming their own guide linked from *See also*. A fact a person meets in a task is never trimmed.

---

## Screenshots

A screenshot replaces a paragraph of "on the left, below the summary…", never the steps. **Load [`references/screenshots.md`](references/screenshots.md) when the run has an environment to capture from, or is a capture pass** — it holds the capture mechanics, what a screenshot shows and how it is filed.

- **Source:** the running **non-production** environment, signed in with a test login for the task's role, administrators included — never production, a design file, a mock-up or the code. Logins stay in the browser, never in a guide, cache, plan, trace or report.
- **Screenshots never block the text.** The run asks **once** for the environment and a test login per role, in the message of the scope or area-split gate it already shows, and never waits on the answer.
- **With no environment** (nobody gave one, or a plan task whose prompt names none): write the guide in full — `**Where:**` paths and bold labels from `Client vocabulary` — hold no image, and record `**Screenshots:** pending — <why>`. The report says so and repeats what is needed.
- **Capture pass.** A later run given the environment, for a pending guide: sign in as each role, check every bold label against the screen (the screen wins; a difference is fixed in the guide and is an open question), capture, replace `pending` with `captured from …`. No re-trace.
- **Waived** is only the person's decision: `**Screenshots:** waived — <the person's reason>`; the guide holds none.
- **Few:** at most **one per task**, only for a task with a `**Where:**` line, where the picture saves the most words; **six per guide** (lint WARN beyond). A guide whose tasks have screens has at least one unless `pending` or `waived` (lint ERROR otherwise; `pending` raises a WARN).
- **Test data only**; every bold label the steps name is visible on it and spelled the same. Right under the `**Where:**` line: `![<what the screen shows, one sentence in the client's words>](screenshots/<guide-name>/<task-slug>.png)` — alt text mandatory, PNG, the file beside the guide.

---

## Language discipline

A table of the same fact as code and as guide is in [`references/glossary.md`](references/glossary.md); load it when unsure how to turn code into the client's words.

Banned in the guide: class, method, table and column names, file names, status codes, exception types, framework nouns, inline code, jargon such as *endpoint, payload, handler, middleware, idempotent, eventual consistency*, tier tags, `file:line`, the judging words of discipline 6, and internal ids (`AREA-`, `FLOW-`, `ENT-`, `DEC-`, `EVT-`, `RX-`, `INV-`, story ids, `Q<n>` outside the open-questions table's first column) anywhere but the stamp comment. **Bold is only a screen label**, never emphasis. A word that needs a definition is replaced, not defined; a client's own technical-sounding word ("API keys") stays when the product shows it, as a bold label or a key idea.

**Guarantee words** — *exactly once, at most one / once, immediately, instantly, as soon as, in real time, right away* — are lint warnings: a timing or delivery guarantee is written only when the code shows it; otherwise reword or ask. **Roadmap promises** — "Not yet.", "coming soon", "in a future version" — no code shows, so the guide never writes them.

## Glossary (KB runs)

Load [`references/glossary.md`](references/glossary.md) when a KB run writes `glossary.md`. Every domain term found goes in with its business meaning and the mapping between the client's own term (the trace's `Client vocabulary`) and the code's name. **Terminology drift is a finding, not a merge** — record both, flag it, and let `business-analyst` resolve it.

## Reconcile procedure (every run that finds an existing guide)

**Load [`references/reconcile.md`](references/reconcile.md) before the first step** — each step's detail under the same numbers, including the old-shape conversions.

1. **Fold the answers — the first act of the run.** Each *Open questions* row with a filled *Answer* goes into the body (and *Rules and limits* when it changes a row) as one plain sentence, and its row is removed; its id is never reused. Count it in the report (`Answers folded: <n>`); you never write `#confirmed`. An answer the code contradicts is not folded: the row stays and the report escalates both readings to `code-auditor`.
2. **Check staleness.** Compare the stamp's `source:` sha with `HEAD` and the git delta for the area's paths; report whether it is stale.
3. **Existing documentation is updated in place** — never deleted and regenerated. The same file keeps `Created`, gains `Last updated`, and marks changed facts `~~old~~ → new`. **A guide in an earlier shape is brought into the current shape in the same file**, every fact kept; a layout move is never struck through. Retired `behind-the-scenes` / `technical*` files are read as leads, then deleted. Add only what the shape needs, from a targeted lookup. Re-trace only the code delta; a `pending` guide given an environment gets only the capture pass. Close with `doc-lint.py --kept-from <old sha> --dir <folder>` and restore or account for every `fact-kept` WARN; edit the `INDEX.md` line into its shape.
4. **Verdict every statement** against the re-trace: **Agrees** · **New** · **Gone** · **Contradicts**.
5. **Update, don't rewrite.** `~~old~~ → new` keeps one generation of history on a changed fact. Re-check the diagram when a task, state or transition changed, the example's arithmetic when a number changed, and the screenshot of every task whose screen or steps changed.
6. **`Gone` needs care.** Say whether the feature was removed or your trace missed it; never delete a `#confirmed` KB statement on a failed search.
7. **`Contradicts` escalates.** Present the documented statement, the code's behaviour and both readings — *stale documentation* vs *code defect*. Never silently pick one.
8. **Re-stamp** with the new sha, a `Last updated` line and the `Describes` date; log the session in `active-context.md` (KB runs).

## Self-check before handing off

1. **Lint passes:** `python3 ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/doc-lint.py --dir <folder>` exits 0. Fix every `ERROR`; fix every `WARN` or say in the report why it stands (`screenshots-pending` stands until the capture pass).

Then only what the lint cannot check:

2. Every area from the confirmed map has its guide, or is in "What is not documented" with a reason. **An `old-shape`, `retired-level`, `renamed-section` or `about-shape` WARN means that guide is not done.**
3. **Every role is there** — administrators included — in *Who uses it*, each with its `## For <role>` section.
4. **Every rule the body states is a row of *Rules and limits*,** and every formula is in *How it is calculated*, not in a task.
5. **Every stated purpose has its source** (an answer, a story named in the stamp, a `#confirmed` entry); the rest are open questions. Every answered question is folded and its row gone.
6. **The worked example's arithmetic is recomputed**; every rule number is the code's exact value.
7. **Five statements spot-checked against the code** at random (a threshold, a refusal message, a step, an outcome, a who-can-do-it); one wrong means re-checking its whole task.
8. **Every screenshot looked at** once more: this task's screen, labels matching the steps, test data, nothing secret. A `pending` guide says in the report what is needed to capture.
9. The client's terms and the exact refusal messages are used.
10. `INDEX.md`, `active-context.md` and the glossary are updated (KB runs).
11. Nothing unreachable is documented as a capability.

## Sharing a guide

Load [`references/sharing.md`](references/sharing.md) when a guide or delivery note goes to a client. `render-html.py` turns guides into standalone pages, renders on demand, is never committed and never writes into the KB:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/render-html.py --out <dir> --dir docs/business-model
uv run ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/render-html.py --out <dir> docs/features/<NNN>-<slug>.md
uv run ${CLAUDE_PLUGIN_ROOT}/backend/_shared/business-documentation/scripts/render-html.py --out <dir> --dir docs/deliveries
```

## Version policy

Version-agnostic — this skill writes prose, not code. The guide is valid against the commit in the stamp's `source` and the screenshots against the capture date in *About this document*; a refresh re-checks both.
