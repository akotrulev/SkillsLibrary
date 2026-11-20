# The guide — shape, tasks and sections

Read by `SKILL.md` before a run writes or edits a guide body, area or feature. It holds the section skeleton, the order of the people, the task format, the sections around the tasks, the stamp and the length limit. The disciplines, the language rules and the screenshot rules stay in `SKILL.md`.

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

  <!-- guide · id: AREA-004 · owner: product:doc-business-model · source: documenter @ a3f9c21 · models: FLOW-004, ENT-003, DEC-002 · stories: US4, US7 · audience: shareable -->
  ```

  - `**Created:**` always; `**Last updated:**` once updated; `**Describes:**` the date the product was read.
  - `**Screenshots:**` is one of `captured from <environment name, never its address> on YYYY-MM-DD` · `pending — <why>` · `waived — <the person's reason>` · absent when the guide has no screen at all.
  - The stamp is `key: value` pairs separated by ` · `, opening with the word `guide`. Keys: `id` (area guides only, `AREA-nnn`), `owner` (area guides and the overview: `product:doc-business-model`), `source` (`documenter @ <sha>` or `feature-documenter @ <sha>`), `models` (KB runs: the FLOW/ENT/DEC ids, optional), `stories` (the story ids a purpose was taken from, optional), `audience` (`shareable`). It is the only place internal and story ids appear.

**Length.** Under about 2,500 words, counted outside fenced blocks, `## About this document` and the stamp comment. When over, cut in this order until it fits: (1) an outcome the person does not notice; (2) a rule nobody meets in a task, unless an administrator changes it — statement and row together; (3) a *Good to know* entry → one sentence in the closest task; (4) example lines beyond the one that shows the rule → `## A <period> in numbers`; (5) *See also* entries a person would not go to. Still over: split by person, the administrators' tasks becoming their own guide linked from *See also*. A fact a person meets in a task is never trimmed.
