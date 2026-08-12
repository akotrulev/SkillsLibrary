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

## Template

```markdown
# <Initiative> — Handoff

**Updated:** YYYY-MM-DD · **Updated by:** `<agent or human>` · **Plan:** `./delivery-plan.md`
**Repo:** `<path>` · **Branch:** `<branch>` · **Baseline commit:** `<sha>`

## Where we are

**Phase:** P4 — Feature slices (3 of 6 tasks done)
**Overall:** 11 of 24 tasks done · 1 partial · 1 blocked

<2–4 sentences a human can read in ten seconds: what works end-to-end right now,
what is half-built, and what the next session should do first.>

## Repo state on last check

| Check | Result | When |
|---|---|---|
| Build | `dotnet build` — clean | 2026-08-02 |
| Tests | `dotnet test` — 84 passed, 0 failed | 2026-08-02 |
| Migrations | head `004_orders`, applied to local + staging | 2026-08-02 |
| Uncommitted work | none | 2026-08-02 |

> Re-verify this before trusting it — it is working-tree state, not layout, and it goes stale fastest.

## Next task

<!-- One entry per unblocked stream, lowest `order` first. Inline execution takes them
     in that order; Mission Control starts them concurrently, so a second entry here is
     not a choice between two tasks — it is two lanes about to run. -->

**T12 — Orders resource** (`ordering`, order 12 · `be-dotnet`; loads `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`)
Unblocked: T4, T9, T10 all Done.
Start with: `src/Ordering/Domain/Order.cs`, following the shape already set by
`src/Catalog/Domain/Product.cs:1-60` (T11's output — match it, do not invent a second convention).

## Blocked

| Task | Blocked on | Owner | Since |
|---|---|---|---|
| T18 | Stripe sandbox credentials not provisioned (`integrations.md` §5, X2) | Finance | 2026-07-28 |

## Decisions made

| # | Decision | Answered | Why | Recorded in |
|---|---|---|---|---|
| Q3 | Cross-tenant reads return **404**, not 403 | 2026-07-24 | Avoids the id-enumeration oracle | `api-surface.md` §4 |
| D1 | Role attributes kept over policy-based auth (T9 divergence) | 2026-07-30 | Three flat roles; policies bought nothing | `delivery-plan.md` T9 |

<!-- Every answered open question and every resolved divergence lands here.
     This is the institutional memory the design documents do not carry. -->

## Deviations from the plan

| Task | Plan said | Code does | Resolution |
|---|---|---|---|
| T9 | Policy-based authorization | `[Authorize(Roles=...)]` attributes (`src/Api/Program.cs:44-58`) | Accepted; plan amended 2026-07-30 |
| T11 | `products.sku` unique globally | Unique per tenant (`migrations/003:22`) | Accepted — correct for the tenancy model; `data-model.md` amended |

<!-- Empty is a fine answer. A missing section when deviations exist is not. -->

## Open questions still outstanding

| # | Question | Blocks | Owner | Asked |
|---|---|---|---|---|
| Q7 | Order retention: 7 years for closed, or per-tenant policy? | T20 | Legal | 2026-07-24 |

## How to verify current state

```bash
git log --oneline -5
dotnet build && dotnet test
dotnet ef migrations list --project src/Infrastructure
```

Expected: build clean, 84 tests pass, head migration `004_orders`.

## Resume instructions

1. Read `delivery-plan.md` §3 T12 for the full task spec.
2. Re-verify the repo state table above — it is a lead, not evidence.
3. Run T12 as `be-dotnet`. Match `src/Catalog/` conventions; do not introduce a second pattern.
4. Update this file at the end of the session: status, evidence, decisions, deviations, next task.

## Session log

<!-- Newest first. One line per session. This is the only part that appends. -->
- 2026-08-02 — T11 Products resource done; T12 next. Q7 raised with Legal.
- 2026-07-30 — T9 divergence resolved (role attributes accepted); T10 shared DTOs done.
- 2026-07-28 — T18 blocked on Stripe sandbox; escalated to Finance.
```

## Writing rules

- **"Where we are" is prose, on purpose.** The tables carry precision; those two to four sentences carry judgment — what actually works, what is fragile, what the next person should be careful about. That is the part that cannot be re-derived from the repo.
- **Never claim a status you did not verify this session.** If you did not re-run the build, say when it was last checked rather than restating yesterday's result as today's fact.
- **Deviations outlive the people who made them.** A deviation recorded without its reason becomes a mystery that gets "fixed" back six months later.
- **Blocked rows carry an owner and a date.** A blocker with neither is a blocker nobody is clearing.
- **Keep it under two screens.** When it grows past that, the detail belongs in `delivery-plan.md` and this file should point at it.
- **On a `RESUME` reconcile, rewrite this file from what you found**, not from what it previously said. The old file is a lead; the code is the evidence.
