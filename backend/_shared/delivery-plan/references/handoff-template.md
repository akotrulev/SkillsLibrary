# `HANDOFF.md` — the session-state file

One file per initiative, living beside the plan at `docs/plans/<NNN>-<initiative>/HANDOFF.md`. Its job: **a cold agent or a human returning after two weeks reads this one file and knows exactly where things stand and what to do next** — without re-deriving it from git history or re-reading four design documents.

## The contract

| Rule | Why |
|---|---|
| **Rewritten, not appended** — except the session-log tail | An appended file becomes an archive nobody reads. The top of this file is always *now* |
| **Updated at the end of every session that touched the initiative** | A handoff written only when work "finishes" is never written |
| **Status claims carry `file:line` evidence** | The whole file is worthless if its status has to be trusted rather than checked |
| **Deviations are recorded, not smoothed over** | What got built differently is the single most valuable thing here, and the first thing lost |
| **It points at the plan; it does not duplicate it** | Task detail lives in `delivery-plan.md`. Copying it guarantees the two drift |
| **Names the next task by id, always** | "Continue where we left off" is not a resumable instruction |

## Template — shown filled

The example below is the paired `HANDOFF.md` for the **workshop-booking** pack in `example-delivery-plan.md`, caught mid-execution during P4. The section structure is the template; the content shows each section doing its job:

```markdown
# Workshop Booking — Handoff

**Updated:** 2026-08-09 · **Updated by:** `be-dotnet` · **Plan:** `./delivery-plan.md`
**Repo:** `~/src/workshop-booking` · **Branch:** `main` · **Baseline commit:** `9d4b7e2`

## Where we are

**Phase:** P4 — Feature slices (1 of 3 tasks done)
**Overall:** 7 of 13 tasks done · 1 in progress · 1 blocked

Scheduling works end-to-end: workshops and sessions can be created, listed and cancelled,
behind auth. Bookings (T11) is half-built — the book and my-bookings endpoints exist and
pass their tests; cancel and attend do not exist yet. Finish T11 first; T13 (email) stays
blocked until the SendGrid account (T0.2) is provisioned.

## Repo state on last check

| Check | Result | When |
|---|---|---|
| Build | `dotnet build` — clean | 2026-08-09 |
| Tests | `dotnet test` — 61 passed, 0 failed | 2026-08-09 |
| Migrations | head `003`, applied to local | 2026-08-09 |
| Uncommitted work | none | 2026-08-09 |

> Re-verify this before trusting it — it is working-tree state, not layout, and it goes stale fastest.

## Next task

<!-- One entry per unblocked stream, lowest `order` first. Inline execution takes them
     in that order; Mission Control starts them concurrently, so a second entry here is
     not a choice between two tasks — it is two lanes about to run. -->

**T11 — Bookings resource, continued** (`booking`, order 9 · `be-dotnet`; loads `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`)
In progress: book + my-bookings done (`src/Booking/BookingEndpoints.cs:1-88`); cancel and attend remain.
Start with: the cancel endpoint, applying the blueprint §3b decision table (R1–R3) for `lateCancel`,
following the endpoint shape already set by `src/Scheduling/SessionEndpoints.cs:1-60` (T10's
output — match it, do not invent a second convention). The `scheduling` lane is finished with
P4 and idles at the barrier.

## Blocked

| Task | Blocked on | Owner | Since |
|---|---|---|---|
| T13 | T0.2 — SendGrid account + domain auth not provisioned (`integrations.md` §5) | Studio owner | 2026-08-04 |

## Decisions made

| # | Decision | Answered | Why | Recorded in |
|---|---|---|---|---|
| D1 | Sessions embedded in the Scheduling module, not a third module (T10 divergence) | 2026-08-06 | One aggregate; a separate module bought nothing | `delivery-plan.md` T10 |

<!-- Every answered open question and every resolved divergence lands here.
     This is the institutional memory the design documents do not carry. -->

## Deviations from the plan

| Task | Plan said | Code does | Resolution |
|---|---|---|---|
| T10 | Separate `WorkshopEndpoints.cs` + `SessionEndpoints.cs` | One `SessionEndpoints.cs` carrying both resources (`src/Scheduling/SessionEndpoints.cs:1-140`) | Accepted; plan amended 2026-08-06 (D1) |

<!-- Empty is a fine answer. A missing section when deviations exist is not. -->

## Open questions still outstanding

| # | Question | Blocks | Owner | Asked |
|---|---|---|---|---|
| Q1 | Departing staff member's authored sessions — reassign, or SET NULL with an audit note? (`data-model.md` §8) | nothing yet — becomes real at the first staff offboarding | Studio owner | 2026-07-21 |

## How to verify current state

```bash
git log --oneline -5
dotnet build && dotnet test
dotnet ef migrations list --project src/Api
```

Expected: build clean, 61 tests pass, head migration `003`.

## Resume instructions

1. Read `delivery-plan.md` §4 T11 for the full task spec.
2. Re-verify the repo state table above — it is a lead, not evidence.
3. Finish T11 as `be-dotnet`. Match `src/Scheduling/` conventions; do not introduce a second pattern.
4. Chase T0.2 with the studio owner — T13 cannot start without it.
5. Update this file at the end of the session: status, evidence, decisions, deviations, next task.

## Session log

<!-- Newest first. One line per session. This is the only part that appends. -->
- 2026-08-09 — T11 book + my-bookings done; cancel/attend next.
- 2026-08-06 — T10 done; divergence resolved (sessions embedded in Scheduling, D1).
- 2026-08-04 — P1–P3 done (T1, T2, T3, T5, T9); T13 flagged blocked on T0.2, chased with studio owner.
```

## Writing rules

- **"Where we are" is prose, on purpose.** The tables carry precision; those two to four sentences carry judgment — what actually works, what is fragile, what the next person should be careful about. That is the part that cannot be re-derived from the repo.
- **Never claim a status you did not verify this session.** If you did not re-run the build, say when it was last checked rather than restating yesterday's result as today's fact.
- **Deviations outlive the people who made them.** A deviation recorded without its reason becomes a mystery that gets "fixed" back six months later.
- **Blocked rows carry an owner and a date.** A blocker with neither is a blocker nobody is clearing.
- **Keep it under two screens.** When it grows past that, the detail belongs in `delivery-plan.md` and this file should point at it.
- **On a `RESUME` reconcile, rewrite this file from what you found**, not from what it previously said. The old file is a lead; the code is the evidence.
