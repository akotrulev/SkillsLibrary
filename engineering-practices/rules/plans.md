---
paths:
  - "docs/plans/*.md"
  - "docs/plans/*/delivery-plan.md"
---

<!-- dev rules v3 (2026-11-06): plans. Installed by /dev:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Plan document standards

Apply to every plan you write, edit, run a task from, or review. Severity: **blocker** makes a session or the queue act wrongly, **major** misleads or loses the record, **minor** is shape. The full format is the dev plugin's `writing-plans/references/plan-format.md`.

**The project wins.** Where the project's `CLAUDE.md`, a `docs/plans/README.md` or the plan itself states its own plan rules, follow the project and do not flag it. A plan's own `## Close-out — every task` is the close-out its tasks run.

## The document

- One self-contained file: context, decisions, tasks and one prompt per task. No `NEXT-PROMPTS.md` or `HANDOFF.md`. *major*
- `docs/plans/NNN-<slug>.md`, or a `solution-planner` pack's `docs/plans/NNN-<initiative>/delivery-plan.md`. `NNN` is zero-padded and its high-water mark spans `docs/plans/` and `docs/plans/implemented/`; never reused, never renumbered. *blocker*
- Title `# NNN — <Title> — plan (YYYY-MM-DD)`, then `**Goal:**`, then `**Status:**`: built, next, built but unverified (never just "in progress"); who starts anything metered. *major*
- Narrative first: `## 1. What already exists, and what is missing` (`| Need | Today | Gap |`), the deciding sections, `## Decisions` (`D<n>`, why, cost), open questions naming what each blocks, the tasks, `## Close-out — every task`, `## Prompts — one per task`. *major*
- One flat ordered list of **tasks**: no phases, slices, stages or milestones. "Step" names only a task's internal actions. *minor*
- No `TODO`, "handle edge cases", "similar to B2", or an undefined type, file or command. An unknown is `[TBD — <who decides, by when>]` plus an open question. *major*

## Tasks

- Ids are a family letter and a number (`C1`, `B2`, `Q1`, `F3`, `H1`), in execution order, never renumbered. An unnecessary task is marked with why, never deleted. *blocker*
- Exactly one `**Stack:**` (`be` · `fe` · `mobile` · `ts` · `data` · `infra` · `qa` · `docs` · `human`) and one exact catalog `**Agent:**`; a `human` task names its `**Owner:**`. A task touching the API tree and the web tree is two tasks, at any size. *blocker*
- One `**Deliverable:**`: a checkable result, not an activity. Done means it exists, not that the bullets ran. *major*
- `**Depends on:**` points backwards only and names every earlier task whose files overlap or that builds the same tree. *blocker*
- `**Budget:**` is `~<n>k` with its drivers itemized; over ~150k it names a split inside its own stack. *minor*
- `**Gate: own tests**` names filtered commands (scoped build, its tests, coverage over its files), never the whole suite; `**Gate: none**` says why. The last task runs the whole set, the ≥ 80% branch floor over the plan's code and the telemetry smoke when service behaviour changed, fixes what it finds, and holds no feature work. *major*
- An implementation task's gate also reruns every acceptance test an earlier task of the plan turned green in the same app, and runs acceptance tests through the runner the last task's gate uses (the project's gate script, scoped), never a bespoke command whose build, data or load differs. *major*
- The last task's gate carries the fix loop: the whole set once; each failure reproduced and fixed with the narrowest command; only the failed rerun; the whole set once more to close. Never a full run to check one fix; a failure that moves between runs is an isolation or scheduling defect to fix in the code, owned setup or gate script, never retried until green; inside a `Q` test or fixture it is a `D<n>`, the test left as it is. *major*
- Order: contract, schema, shared types and stubs answering `501 not-implemented`; then the `Q` acceptance tests, red on the stubs; then backend, shared packages, frontend and mobile. Human prerequisites come first. *major*
- `**Not in <id>:**` names what belongs elsewhere. A stack-cut task that cannot be demonstrated says so; never a fake success or an empty list. *major*
- Acceptance tests a `Q` task wrote are read-only to every later task but the gate. A test you believe wrong stays red, recorded as a dated `D<n>` with both readings. *blocker*

## Prompts

- One block per unlanded task, in order, under the table (`# · Stack · Agent · Depends on · Runs beside · Budget`, human steps included) and a "what runs together" line. *major*
- Heading `### <id> — <title> (<agent>, <stack>)`: id first, no `Prompt`/`Task` prefix, no other trailing parenthetical. The body (fenced or blockquote) follows after one blank line, nothing between. No other `###` inside `## Prompts`. *blocker*
- Body line 1 `Depends on: <ids>` or `Depends on: none`, this plan's ids only (`114 B1` reads as `B1`); line 2 `Agent: <agent> · Stack: <stack>`. *blocker*
- A block copies the task's deliverable, files and gate, adds the reading order (sections, never whole artifacts) and the task's traps, and never says "see the task". Gates run locally: never `ssh`, push before a gate, or copy the tree. *major*
- Every block reads `## Close-out — every task` last and ends `Close out per the plan's "Close-out — every task" before you stop.` That section is copied verbatim from plan-format §7. *blocker*
- A block that cannot be written yet is `**Blocked on <id>** — <id> writes this prompt when it lands, from …`; that task writes it before it stops, in another plan too. Never guess it. *major*

## Running a task: the close-out

- Re-read the plan just before your close-out edits; touch only your task block, your prompt block and the landed line. Commit on the current branch, your own files by path, never `git add -A`; never check out the default branch. *blocker*
- Append a dated `**As built:**` with `file:line` or command output; never edit an earlier note. A divergence is a dated `D<n>`, never absorbed. Rewrite every block below yours that your work invalidated. *major*
- Delete your prompt only after the work is committed, in a follow-up commit `docs: delete <id>'s prompt (<plan>)`; never stop between the two. With other tasks of the plan running beside you under Plan Queue, do not commit, stash, reset or check out: delete it as your last edit. Stopping mid-task or blocked: keep it, with `Picking up from:` or the blocker and its owner. *blocker*
- The last task merges the default branch into the plan's branch before deleting its prompt, keeping both sides' rows. Deleting the last block files the plan: final `Status:`, `git mv` into `docs/plans/implemented/`, its row in that README. Never edit a plan after it moves. *major*
