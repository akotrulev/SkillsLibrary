---
paths:
  - "docs/plans/*-system.md"
---

<!-- product rules v3 (2026-11-25): system plans. Installed by /product:rules; edit to fit this project. -->

# System plan standards

For `docs/plans/<NNN>-<system>-system.md`, the one file `/product:plan-system` writes for a whole
system. The tag after a rule is the severity a review reports: **blocker** a feature session cannot
start from it or acts wrongly, **major** will mislead a feature or lose the record, **minor** is shape
or format, **nit** is wording. The project's own convention wins where it consistently does otherwise.
The full format is the `product` plugin's `solution-blueprint/references/system-plan-format.md`.
`plans.md` also loads for this file: its document rules hold, and its task and prompt rules give way to
the feature rules below. Plan Queue queues this file like any plan.

## The document

- Sections in order: header (`**Goal:**`, `**Status:**`, `**Mode:**`), `## 1. What already exists, and what is missing`, `## 2. Vision and scope`, `## 3. The skeleton`, `## 4. Epics`, `## 5. Features side by side`, `## Decisions`, `## Answered questions`, `## Open questions`, `## 6. Features`, `## Close-out — every feature`, `## Prompts — one per feature`. *major*
- `**Status:**` names the features specced and planned, the features on hold and why, and the next feature. *major*
- Every §1 row with a gap is covered by a feature, and every feature traces to a §1 row. *major*
- No grouping layer over the features: no phases, waves, stages or milestones. *minor*

## §2 Vision and scope

- Ten subsections in order, none dropped (an empty one says why): the ask verbatim, the product in plain words, problem and why now, actors, what it must do, constraints, success, scope, assumptions, risks. Open questions go to the plan's `## Open questions`. *minor*
- The ask is quoted verbatim, never paraphrased; everything below is checked against it. *major*
- The product in plain words: what a person gets, in sentences anyone outside the team reads; one journey row per thing an actor does, each naming its features, every feature in at least one; and the kinds of choice the decision-maker is asked. No code identifier, library or decision id. *major*
- The problem is stated in the business's terms before any solution wording. "Add a button" is a solution: the requirement is the workflow it unblocks. *major*
- "What it must do" states capabilities as outcomes an actor gets, business rules with their numbers, and quality targets. No technology: no stack, table, endpoint, screen or component. *major*
- A quality target carries its number and who stated it, or `[TBD - <who decides>]` plus an open question. Never an invented number. *blocker*
- Every actor has a goal, and one is named the decision-maker who approves scope. *major*
- Success is a measure with baseline and target, or a qualitative signal and who judges it. An unknown is an open question, never an invented number. *blocker*
- Scope has three columns: in, out (refused) and deferred (a follow-up commitment). *minor*
- Every inference made because the stakeholder did not say is one line in Assumptions. *major*
- Risks carry likelihood and impact separately (L/M/H), with a mitigation. *minor*

## §3 The skeleton

- Stack rows carry a version and an evidence mark (`detected` with `file:line`, `stated`, `proposed`, `proposed → approved`). In an existing repo `detected` wins over every default; an upgrade is its own feature, never a side effect. *blocker*
- Architecture states the style, why it is earned, what was rejected and a reason per pattern in play. *major*
- Every area names its trees as path globs and its agents by exact catalog name. *blocker*
- Shared entities are only those two or more features bind to, each with exactly one owner area. *major*
- Cross-cutting conventions cover the error envelope, ids, pagination, dates, tenancy, config and secrets, the telemetry base, and the app shell when anything is user-facing; a row that does not apply says why. *major*
- No per-feature design: no table columns, endpoints, screens, key flows or integration detail. *major*
- §3 says what is true now: a feature's decision that changes it is a dated `D<n>`, and the §3 line is corrected citing it. *major*

## §4 Epics

- Epics are `E1..En`; every §2 capability is covered by exactly one, and a system has at least one. Ids are never renumbered; new epics take the next free id. *blocker*
- One goal per epic: **who** can **do what** so that **measurable change**. Two goals are two epics. An unknown measure is `[TBD - <who decides>]` plus an open question. *blocker*
- Each epic has a plain-English line with no technology. An epic that cannot be described without one is a technical task. *major*
- No goal-less or tech-only epic ("migrate to v3"). *major*
- Each epic lists the `F` ids that serve it, at least one; every feature but the foundation serves exactly one epic. *blocker*

## §5 Features side by side

- One row per feature: `Feature | Epic | Areas and trees | Depends on | Refined beside | Built beside`. *major*
- Trees are path globs from §3, never area names alone. *major*
- Every dependency points backwards and names what it waits on. *major*
- Built beside only when neither depends on the other and their trees are disjoint. *blocker*
- Refined beside only when neither spec waits on a decision the other makes. *major*

## §6 Features

- The features are listed in the suggested order of implementation, which is the order Plan Queue runs them in: the foundation first, each feature below everything it depends on, then the one that gives a person something usable soonest. §6, the prompt table and the prompt blocks hold the same order. *major*
- Ids are `F1..Fn`, assigned in that order when the plan is written and never renumbered; a split feature's second half takes the next free id, and its block is placed where the feature is to be built. *blocker*
- Each block carries `**Epic:**` (or `— (foundation)`), `**Command:** /product:plan-feature`, `**Deliverable:**`, `**Depends on:**` and `**Brief:**`, and **no** `Stack`, `Agent`, `Budget` or `Gate` line. *major*
- A feature is something a person can do, never a layer ("the API", "the screens"). *major*
- In a repo where the skeleton is not built, `F1` is the foundation feature and every other feature depends on it. *major*
- The brief says what the feature does and for whom, what is in and out (naming the feature that owns what is out), and the §3 decisions it builds on. *major*
- `As built` and `On hold` notes are dated and appended, never edited. *major*
- A feature is `specced` only when its implementation plan holds no open question and no row of `## Open questions` still names it under `Blocks`; a feature the user cannot finish answering is `on hold`, with no plan. *blocker*

## Prompts and close-out

- The prompts heading is `## Prompts — one per feature`: Plan Queue reads the system plan as it reads any plan, and nothing else is a `###` under that heading. *blocker*
- Each block's heading is `### F<n> — <title>` with no trailing parenthetical (the queue reads one as an agent to start), followed after one blank line by a four-backtick fence. *blocker*
- Each block's first line is `Depends on:` with one id, the block directly above it, or `none` on the first: the interviews run one at a time, in the order of implementation. *blocker*
- Each block's second line is `Skill: /product:plan-feature F<n> of <system plan path> — <title>`. Then the run paragraph from the format file word for word, the brief, the reading line (sections and decision ids, never the whole plan) and the close-out line. *blocker*
- The system plan is committed once written: Plan Queue runs only a committed plan. *major*
- A feature session that puts its feature on hold under a queue ends with `PLAN_QUEUE: BLOCKED F<n> on hold: <reason>`, after committing the draft. *major*
- `## Close-out — every feature` is copied verbatim from the format file. *blocker*
- A feature's prompt is deleted only after its spec and plan are committed, in the follow-up commit `docs: delete F<n>'s prompt (<system plan>)`. A feature on hold keeps its prompt. *blocker*
- The system plan moves to `docs/plans/implemented/` when its last prompt block is deleted, and not before; a held feature keeps it in `docs/plans/`. *major*
