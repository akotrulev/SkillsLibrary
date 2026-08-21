# `HANDOFF.md` — the what-next file

One file per initiative, living beside the plan at `docs/plans/<NNN>-<initiative>/HANDOFF.md`. Its job is **one question: what does the next agent (or the human on Monday) pick up, and where inside it do they start** — without re-deriving it from git history or re-reading four design documents.

**It is not the progress record.** Status, evidence, ticked criteria, the execution log, decisions and deviations all live in `delivery-plan.md` (§2, §3, §6, §7), because they outlive the session that produced them and a rewritten file cannot hold history. This file points at that record; it never restates it. Everything here goes stale within a session — which is exactly why it is rewritten every time and why nothing durable is stored in it.

## The contract

| Rule | Why |
|---|---|
| **Rewritten every session, wholly** | It describes *now*. An appended file becomes an archive nobody reads |
| **Answers "what next", nothing else** | Progress lives in the plan. Two records of the same fact is one record and one lie |
| **Names the next task by id, always** | "Continue where we left off" is not a resumable instruction |
| **One entry per unblocked lane** | Concurrent execution needs to know all the lanes it can start, not just the first |
| **Says where *inside* the task to start** | The plan says what the task is and what it must deliver; this says which end of it is already done |
| **Blockers carry an owner and a date** | A blocker with neither is a blocker nobody is clearing |
| **Working-tree state is stamped with when it was checked** | It is the fastest-rotting fact in the pack, and the one most often trusted |
| **Under one screen** | Anything longer is plan content that drifted into the wrong file |

## Template — shown filled

The example below is the paired `HANDOFF.md` for the **workshop-booking** pack in `example-delivery-plan.md`, caught mid-execution at T11:

```markdown
# Workshop Booking — Handoff

**Updated:** 2026-08-09 · **Updated by:** `be-dotnet` · **Plan:** `./delivery-plan.md`
**Repo:** `~/src/workshop-booking` · **Branch:** `main` · **Baseline commit:** `9d4b7e2`

> Progress, evidence, decisions and deviations live in `delivery-plan.md` §2 and §6–7.
> This file only says what to do next. Current position: **T11 — Bookings resource**, plan §2.

## Next task

<!-- One entry per unblocked stream, lowest `order` first. Inline execution takes them
     in that order; Mission Control starts them concurrently, so a second entry here is
     not a choice between two tasks — it is two lanes about to run. -->

**T11 — Bookings resource, continued** (`booking`, order 10 · `be-dotnet`; loads `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`)
Start with: the cancel endpoint — book and my-bookings are already in (`src/Booking/BookingEndpoints.cs:1-88`),
cancel and attend are not. Apply the blueprint §3b decision table (R1–R3) for `lateCancel`, and follow the
endpoint shape already set by `src/Scheduling/SessionEndpoints.cs:1-60` — match it, do not invent a second
convention. The unticked criteria in plan §3 T11 are the remaining list.
**Deliverable:** a member can book a session, see it under their bookings, cancel it, and be refused
when the session is full.

The `scheduling` lane is out of work — T14 is its next task and it waits on T11 — so there is nothing
to start there.

## Blocked

| Task | Blocked on | Owner | Since |
|---|---|---|---|
| T13 | T0.2 — SendGrid account + domain auth not provisioned (`integrations.md` §5) | Studio owner | 2026-08-04 |

## Watch out for

<!-- Two or three sentences at most: what is fragile, what the last session learned the hard way,
     what the next person will otherwise trip over. Judgment that cannot be re-derived from the repo.
     Anything that is a decision or a deviation goes in the plan (§7) instead of here. -->

Bookings and Scheduling both touch the session's remaining-capacity read; the overbooking guard is the
DB constraint from migration `003`, not application code — do not add a second check in the service.

## Repo state on last check

| Check | Result | When |
|---|---|---|
| Build | `dotnet build` — clean | 2026-08-09 |
| Tests | `dotnet test` — 61 passed, 0 failed | 2026-08-09 |
| Migrations | head `003`, applied to local | 2026-08-09 |
| Uncommitted work | none | 2026-08-09 |

> Re-verify before trusting it — this is working-tree state, and it goes stale fastest.

## How to verify current state

```bash
git log --oneline -5
dotnet build && dotnet test
dotnet ef migrations list --project src/Api
```

Expected: build clean, 61 tests pass, head migration `003`.

## Resume instructions

1. Re-verify the repo state table above — it is a lead, not evidence.
2. Read `delivery-plan.md` §3 T11 for the full task spec, its deliverable, and its unticked criteria.
3. Finish T11 as `be-dotnet`. Match `src/Scheduling/` conventions; do not introduce a second pattern.
4. Update the plan as you go — §2 status + evidence, §3 checkboxes, a §6 row, §7 if anything diverges.
5. Chase T0.2 with the studio owner — T13 cannot start without it.
6. Rewrite this file at the end of the session: next task, blockers, repo state.
```

## Writing rules

- **Everything durable goes to the plan, not here.** If you find yourself writing what got done, what was decided, or what got built differently, that is a `delivery-plan.md` §6/§7 entry — write it there and let this file stay short.
- **Never claim a status you did not verify this session.** If you did not re-run the build, stamp when it was last checked rather than restating yesterday's result as today's fact.
- **"Watch out for" is prose, on purpose.** The tables carry precision; those two or three sentences carry judgment — what is fragile and what the next person should be careful about. That is the part that cannot be re-derived from the repo.
- **A lane with nothing startable is worth one line.** "Waiting on T11" tells the reader it was considered; silence reads as an oversight.
- **On a `RESUME` reconcile, rewrite this file from what you found**, not from what it previously said. The old file is a lead; the code is the evidence — and the reconcile's findings land in the plan.
