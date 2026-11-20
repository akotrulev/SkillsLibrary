# 001 — Session credits — plan (2026-10-05)

**Goal:** Members spend a monthly allowance of session credits on bookings and pay only for the overage; staff set up plans; the month's overage is charged once. Built in the Workshops service, E1 and E2 of `epics.md`.

**Status:** B1, B2 and G1 have landed and their tests are green. DOC1 is next: the first area guides, the delivery note and the filing of this plan. The product's screens are not in this repository and no non-production environment exists, so the guides' screenshots will be pending.

**Test design:** none — opted out by the studio owner on 2026-10-05; this plan has acceptance criteria but no `TD` or `Q` tasks.

**Documentation:** none yet; DOC1 starts the business model in `docs/business-model/`. The delivery note goes in `docs/deliveries/`.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| Spend credits on a booking, by tier (US1 AC1, AC2) | — | Pricing after a booking is confirmed |
| Personal overage rate and the credits page (US1 AC3, AC4) | — | The rate lookup and the page |
| Cancelling for credits, and cancelling a session (US2) | — | The 24-hour rule and the staff path |
| Plans and rates set by staff (US3) | — | Plan update with its refusals; the member's personal rate |
| The month end (US4) | — | One charge per member; credits starting again |

## 2. Decisions

**D1 — DOC1 starts the business model.** The studio keeps no documentation yet; `documenter` runs DOC1 and documents only the areas this plan touched, so the rest of the system stays undocumented. Cost: a knowledge base with one or two areas, not a full survey.

## 3. Tasks

### B1 — Booking pricing, the credits page and cancelling

**Stack:** `be` · **Agent:** `be-dotnet`
**Deliverable:** a confirmed booking is priced from the member's credits and the session's tier, the credits page answers, and a cancellation returns credits by the 24-hour rule (US1, US2).
**Depends on:** —
**Budget:** ~90k — CLAUDE.md 5k, this plan 6k, the stories 8k, writes ~40k, test output ~10k.
**Gate: own tests** — `dotnet test tests/Workshops.Api.Tests --filter "FullyQualifiedName~CreditPricing"`.

- Pricing runs after the booking is confirmed; cancelling and cancelling a session raise the same cancellation.
- **As built (2026-10-14):** pricing is a pure function with three unit tests; the cancellation rule lives in its own handler.

### B2 — Plan settings and the monthly posting

**Stack:** `be` · **Agent:** `be-dotnet`
**Deliverable:** staff update a plan with the refusals of US3, and a monthly job charges each member's overage and starts the month again (US3, US4).
**Depends on:** B1.
**Budget:** ~80k — CLAUDE.md 5k, this plan 6k, the stories 8k, writes ~35k, test output ~10k.
**Gate: own tests** — `dotnet test tests/Workshops.Api.Tests --filter "FullyQualifiedName~OverageChargeJob"`.

- Plan update validates before it saves; the job runs on a schedule.
- **As built (2026-10-16):** plan update and the monthly posting job built; US3 and US4 covered.

### G1 — Gate: the whole set

**Stack:** `be` · **Agent:** `be-dotnet`
**Deliverable:** the whole test set is green across the plan.
**Depends on:** B1, B2.
**Budget:** ~40k — this plan 6k, test output ~20k.
**Gate (this is the last runnable task):** `dotnet build` and `dotnet test`.

- **As built (2026-10-18):** `dotnet test` green, 4 tests. No telemetry smoke: the plan adds no new entry point.

### DOC1 — Documentation: the area guides, the delivery note and the filing

**Stack:** `docs` · **Agent:** `documenter`
**Deliverable:** `docs/business-model/` holds the guides of the areas this plan touched, with the overview, `INDEX.md` and the models, describing what the code at HEAD does; `docs/deliveries/001-session-credits.md` states what people can do now and which stories were not delivered; this plan is filed in `docs/plans/implemented/`.
**Depends on:** G1.
**Budget:** ~130k — this plan 6k, the stories 10k, the code under `src/Workshops.Api` ~70 lines per file over about 20 files 17k, the guides, the overview, the models and the delivery note ~35k writes, lint output 3k.
**Gate: own tests** — `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/doc-lint.py --dir docs/business-model` and `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/doc-lint.py --dir docs/deliveries`.

- Environment for screenshots: none; the guides land with `**Screenshots:** pending`.

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, gate task only** — if you are the task that ran the whole set and this plan runs on its own
   branch, merge the default branch into it now, resolve every conflict by keeping both sides' rows,
   re-run the failing suites if code conflicted, and commit the merge, so the plan merges back cleanly
   and the documentation task after you documents the merged code.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number — a `solution-planner` pack moves its whole initiative folder — and add its row to that
   folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

Run the prompts in order, one session each; each block is complete on its own. DOC1 runs the doc lint locally and never starts the application.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| DOC1 | `docs` | `documenter` | G1 | — | ~130k |

B1, B2 and G1 have landed, and their prompts are deleted.

---

### DOC1 — Documentation: the area guides, the delivery note and the filing (documenter, docs)

````
Depends on: G1
Agent: documenter · Stack: docs

You are `documenter`. Task DOC1 of docs/plans/001-session-credits/delivery-plan.md: the project has no documentation yet. Start the business model with the areas this plan built — the credit pricing and overage charges of the Workshops service — from the code that landed, write the delivery note, and file the plan. This task runs unattended under Plan Queue: nobody will answer a question.

Read, in this order:
1. The plan: the header, §1, task DOC1 and "Close-out — every task".
2. The initiative's stories: docs/plans/001-session-credits/stories.md, then epics.md and requirements.md. They are the source of purpose and the baseline for what was planned, never evidence of what was built.
3. B1's and B2's "As built" notes in the plan. An As built note says what a task believed it built; the code at HEAD is the evidence.
4. The delivery note's shape: `${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/references/delivery-note.md`.

Traps:
- Nothing the plan intended and the code does not do is written as built: it goes to the delivery note's *Not delivered* table and the report.
- Screenshots: there is no non-production environment for this plan. Write every guide in full, hold no image, record `**Screenshots:** pending — <why>`, and say in the report what is needed.

Gate: `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/doc-lint.py --dir docs/business-model` and `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/doc-lint.py --dir docs/deliveries`. Fix every ERROR; only `screenshots-pending` may stand.

Commit: `docs: session credits business model and delivery note (DOC1)`.
Close out per the plan's "Close-out — every task" before you stop.
````
