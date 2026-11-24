---
paths:
  - "docs/plans/*.md"
---

<!-- product rules v6 (2026-11-24): plans. Installed by /product:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Plan document standards

Apply to every plan you write, edit, run a task from, or review. Severity: **blocker** makes a session or the queue act wrongly, **major** misleads or loses the record, **minor** is shape. The full format is the `product` plugin's `writing-plans/references/plan-format.md`.

**The project wins.** Where the project's `CLAUDE.md`, a `docs/plans/README.md` or the plan itself states its own plan rules, follow the project and do not flag it. A plan's own `## Close-out — every task` is the close-out its tasks run.

## The document

- One self-contained file: context, decisions, tasks and one prompt per task; no companion file. *major*
- `docs/plans/NNN-<slug>.md`. `NNN` is zero-padded and its high-water mark spans `docs/plans/` and `docs/plans/implemented/`; never reused, never renumbered. *blocker*
- Title `# NNN — <Title> — plan (YYYY-MM-DD)`, `**Goal:**`, then `**Status:**`: built, next, built but unverified (never just "in progress"). *major*
- Narrative first, tasks last, in the order of plan-format §2, ending in `## Close-out — every task` and `## Prompts — one per task`. *major*
- One flat ordered list of **tasks**: no phases, slices, stages or milestones. "Step" names only a task's internal actions. *minor*
- No `TODO`, "handle edge cases", "similar to B2", or an undefined type, file or command. An unknown is `[TBD — <who decides, by when>]` plus an open question. *major*
- A system plan (`docs/plans/*-system.md`) follows `system-plans.md` for its feature blocks and prompts: its features carry no `Stack`, `Agent`, `Budget` or `Gate`, and Plan Queue runs them one at a time, each a `/product:plan-feature` interview. *major*

## Tasks

- Ids are a family letter and a number (`C1`, `B2`, `Q1`, `F3`, `H1`), in execution order, never renumbered. An unnecessary task is marked with why, never deleted. *blocker*
- Exactly one `**Stack:**` (plan-format §4's list) and one exact catalog `**Agent:**`; a `human` task names its `**Owner:**`. A task touching the API tree and the web tree is two tasks, at any size. *blocker*
- One `**Deliverable:**`: a checkable result, not an activity. Done means it exists, not that the bullets ran. *major*
- `**Depends on:**` points backwards only and names every earlier task whose files overlap or that builds the same tree. *blocker*
- `**Budget:**` is `~<n>k` with its drivers itemized; over ~150k it names a split inside its own stack. *minor*
- `**Gate: own tests**` names filtered commands that run the task's own tests (the tests it wrote plus the acceptance tests bound to its own deliverable, usually one to three files), the tests the landed tasks above it in the same plan wrote (acceptance tests bound to a deliverable no landed task has built yet first run in the task that builds it, or in the gate task), and the branch-coverage floor over the files it and those tasks touched, on a small core budget, on ports of its own, under no machine-wide lock; `**Gate: none**` says why. What each stack runs is plan-format §5's. A task never runs another plan's tests, the smoke suite or the unfiltered suite. *major*
- The last task is the plan's one run under the project's test lock: the smoke suite plus every test the plan wrote, then the whole set, the ≥ 80% branch floor over the plan's code and the telemetry smoke when service behaviour changed; it fixes what it finds and holds no feature work. A runbook run plan says `Gate task: none — <why>` in its header instead (plan-format §5). The project's whole e2e suite runs in its nightly CI run; each test red there goes on the project's tracked list with an owner and comes off it only when a nightly run is green for it. *major*
- The last task's gate carries the fix loop of plan-format §5. Never a full run to check one fix; a failure that moves between runs is an isolation or scheduling defect fixed in the code, never retried until green; inside a `Q` test or fixture it is a `D<n>`, the test left as it is. *major*
- Order is plan-format §4's: contract and stubs answering `501 not-implemented`, then `TD`, then `Q`, then implementation; human prerequisites first. *major*
- The plan's last task is `DOC1`, stack `docs`, agent `documenter` or `feature-documenter`, depending on the gate task (plan-format §5); the gate task writes no product documentation. Left out only with `Documentation task: none — <why>`. *major*
- A plan that delivers a feature plans its testing: `TD` tasks (the test plan, then the test cases) keyed to the feature spec's `## Acceptance criteria`, each case citing `<spec> AC<k>`, before the `Q` tasks (plan-format §4). A plan built from a story backlog qualifies the same way, citing `US<n> AC<k>`. One with acceptance criteria and no `TD` tasks says in its header who opted out and why. *major*
- `**Not in <id>:**` names what belongs elsewhere. A stack-cut task that cannot be demonstrated says so; never a fake success or an empty list. *major*
- Acceptance tests a `Q` task wrote are read-only to every later task but the gate. A test you believe wrong stays red, recorded as a dated `D<n>` with both readings. *blocker*

## Prompts

- One block per unlanded task, in order, under the table (`# · Stack · Agent · Depends on · Runs beside · Budget`) and a "what runs together" line. *major*
- Heading `### <id> — <title> (<agent>, <stack>)`: id first, no `Prompt`/`Task` prefix, no other trailing parenthetical. The body (fenced or blockquote) follows after one blank line, nothing between. No other `###` inside `## Prompts`. *blocker*
- Body line 1 `Depends on: <ids>` or `Depends on: none`, this plan's ids only (`114 B1` reads as `B1`); line 2 `Agent: <agent> · Stack: <stack>`. *blocker*
- A block copies the task's deliverable, files and gate, adds the reading order (sections, never whole artifacts) and the task's traps, and never says "see the task". Gates run locally: never `ssh`, push before a gate, or copy the tree. *major*
- Every block reads `## Close-out — every task` last and ends `Close out per the plan's "Close-out — every task" before you stop.` That section is copied verbatim from plan-format §7. *blocker*
- A block that cannot be written yet is `**Blocked on <id>** — <id> writes this prompt when it lands, from …`; that task writes it before it stops, in another plan too. Never guess it. *major*

## Running a task: the close-out

The steps are plan-format §7's and the plan's own `## Close-out — every task`. The constraints:

- Commit on the current branch, your own files by path, never `git add -A`; never check out the default branch. With other tasks of the plan running beside you under Plan Queue, do not commit, stash, reset or check out. *blocker*
- Re-read the plan just before the close-out edits; touch only your task block, your prompt block and the landed line. *blocker*
- Delete your prompt only after the work is committed (under Plan Queue with tasks beside you, as your last edit); a stopped or blocked task keeps it, with `Picking up from:` or the blocker and its owner. *blocker*
- `As built` is dated and append-only; a divergence is a dated `D<n>`, never absorbed. *major*
- A plan is never edited after it moves to `docs/plans/implemented/`. *major*
