# Golden example — `delivery-plan.md`

The filled example for `dev:plan-delivery`, from the **workshop-booking** toy initiative shared
by all the planner examples. **Shapes and disciplines are normative; domain content is illustrative.**
A real artifact writes a full block for *every* task — this example writes four representative ones (a
foundation task, a backend capability task, the frontend task that actually delivers that capability,
and the gate-and-close-out task) and abbreviates the rest, saying so.

The document format is `engineering-practices/writing-plans/references/plan-format.md`; the prompts
section's shape is `backend/_shared/session-budget/references/prompts-section-template.md`; the epic
map these streams derive from is `backend/_shared/epic-map/references/example-epic-map.md`.

Workshop booking is user-facing, so it is sequenced **feature-complete**: after the foundations the
first capability needs, the tasks for one capability run back to back and the last of them makes it
usable.

Read for five things this example carries that a generic plan does not: every task names **one**
stack, so the backend and screens of one capability are separate tasks; every task carries its **epic
and story**; every task carries a **`Budget`** with the drivers behind it; **exactly one task carries
the gate** (`B7`, the last runnable one) and every other says `Gate: none`; and the plan's **progress
is the `As built` notes plus the prompt blocks that are left**, not a status column. Note also where the
filing duty sits: `B4` is blocked on a person and outlives the gate task, so **`B4`'s block carries the
move to `docs/plans/implemented/`**, not `B7`'s.

---

# 003 — Workshop Booking — delivery plan (2026-08-02)

**Goal:** a studio can publish workshops and sessions, and a member can browse the timetable, book a
session, manage their bookings and edit their profile — with a confirmation email once the sending
domain is verified.

**Status:** *(2026-08-09)* `H1`, `C1`–`C7`, `B1` and `F1` have landed — **E1 is usable**: a member
browses the timetable and an admin publishes a workshop (J1 walked by hand 2026-08-08). `B2`
(bookings) is **partial**: book and my-bookings are written, cancel and attend are not. Nothing has
been built or tested as a whole yet — **this plan gates once, in `B7`**, which has not run, so the
tree is not known to build. `H2` (SendGrid domain authentication) is blocked on the studio owner, and
`B4` sits below the gate because of it.

**Pack:** `./epics.md` · `./stories.md` · `./blueprint.md` · `./data-model.md` · `./experience-plan.md` · `./api-surface.md` · `./integrations.md` · `./epic-map.md`
**Target repo:** `~/src/workshop-booking` · **Stack:** .NET 10 + PostgreSQL 18 (`src/`) · React 19 + Next 15 (`web/`)
**Build/test:** `dotnet build` / `dotnet test` / `dotnet format` for `be` tasks · `pnpm build` / `pnpm test` for `fe` tasks — **run once, by `B7`**
**Sequencing shape:** feature-complete — the studio owner wants the timetable demonstrable before booking exists

> **For agentic workers:** the tasks in §3 are one flat sequence — work them in order. Each names the
> agent that should execute it, the skills to load, and the one deliverable that means it is done.
> **This plan gates once, in `B7`:** every task before it writes its code and its unit tests, commits,
> and stops — no `dotnet build`, no `dotnet test`, no `pnpm build`, no lint. The tree is therefore not
> known to build at every task boundary, and the plan cannot be stopped halfway and trusted; `B7` runs
> the whole set and fixes what it finds, whichever task it belongs to.
> **Update this document as you work** — a dated `As built` note on your task, the `Status:` line
> above, and `## 6. Decisions` for anything you built differently — then **delete your own prompt
> block**, repair the ones below yours, and write any block that was `Blocked on` you.

## 1. What already exists, and what is missing

Greenfield: the repo is an empty git checkout, so every `Today` is `—`. The table is still the plan's
grounding — every task below traces to a row, and a row with no task is something the plan forgot.

| Need | Today | Gap |
|---|---|---|
| A solution that builds, with module boundaries | — | Scaffold + module layout (`C1`), config validation + CI skeleton (`C2`) |
| Authenticated requests with two permissions | — | Auth0 tenant and apps (`H1`), JWT bearer + policy wiring (`C3`) |
| One error shape, one set of shared schemas, a route-registration seam | — | `C4`. Without the seam, `src/Scheduling` and `src/Booking` cannot be separate lanes |
| Workshops, sessions and bookings in the database, with capacity enforced | — | Migrations 001–002 (`C5`), migration 003 + the exclusion constraint (`C7`), guard review (`DA1`) |
| A web shell a member can navigate, and a typed client | — | `C6` — the shell, the nav map, the route tree, `web/lib/api-client.ts` |
| Publishing workshops and sessions | — | `B1` (API) + `F1` (screens). **`B1` alone does not deliver it** |
| Booking, cancelling, seeing your bookings | — | `B2` (API) + `F2` (screens) |
| A member profile | — | `B3` (API) + `F3` (screen) |
| A confirmation email | — | `B4`, blocked on `H2` (verified sending domain) |
| A committed OpenAPI asset for the QA lane | — | `B5`, after the last endpoint task |
| Traces and the standard metric set | — | `B6` |
| One verified build, suite and format pass, plus the docs | — | `B7`, the plan's only gate |

## 2. Streams

Derived from `epic-map.md` §2, split by stack where a lane spans two — the one-stack rule turns
`foundations` into `foundations-api` + `foundations-ui`, and each capability lane into an `-api` and a
`-ui`. Both splits are recorded back into `epic-map.md` §2.

| Stream | Epic | Stack | Owns | Why it is internally sequential |
|---|---|---|---|---|
| `foundations-api` | `E0` | `be` | Solution root and everything shared: scaffold, config, CI, auth wiring, error middleware, the endpoint-module seam, the OpenAPI asset, telemetry base, the gate | Every task edits the solution root or `src/Api/Program.cs`. `H1` sits here too — the Auth0 tenant is what `C3` wires |
| `schema` | `E0` | `be` / `data` | Migrations and the data-integrity work that follows — `src/Api/Migrations/*` | Migrations are ordered by definition, and `DA1`'s review reads the constraint `C7` creates. Disjoint from `foundations-api`'s file set, so its own lane |
| `foundations-ui` | `E0` | `fe` | App shell, nav map, route tree, typed API client — `web/app/layout.tsx`, `web/app/(nav)/*`, `web/lib/api-client.ts` | One root file set on the web side, exactly as `foundations-api` is on the API side |
| `timetable-api` | `E1` | `be` | Workshops + Sessions — `src/Scheduling/*` | One module, one file set |
| `timetable-ui` | `E1` | `fe` | The public timetable and the admin workshop editor — `web/app/timetable/*`, `web/app/admin/workshops/*` | Both screens share the session-card component |
| `booking-api` | `E2` | `be` | The Bookings resource — `src/Booking/*` | One module, one file set |
| `booking-ui` | `E2` | `fe` | Book and my-bookings — `web/app/bookings/*` | One screen set over one aggregate |
| `profile-api` / `profile-ui` | `E3` | `be` / `fe` | Member profile — `src/Membership/*` · `web/app/profile/*` | *(abbreviated in this example)* |
| `email` | `E4` | `be` | The confirmation email — `src/Notifications/*` | One story, one tree — a lane of one task |

`email` finishes `H2` in minutes and then waits — not on a barrier, but on `B4`'s own `Depends on`
(`C4`, `B2`): the event it subscribes to does not exist until the booking API lands. Every such wait
is an edge on the task, not an implied rule.

**Note what the one-stack rule bought here.** `timetable-api` and `profile-api` are wave-2 lanes with
disjoint file sets, so they can run at the same time; under a mixed `scheduling` lane carrying both
endpoints and screens, `timetable-ui`'s dependency on `timetable-api` would have serialised all four.

## 3. Tasks

One flat sequence, in the order the work is done — a valid serialization of `epic-map.md`'s dependency
graph, not a wave-by-wave march through it. The scannable index is the task table in
`## Prompts — one per task`.

*A real artifact writes every block; this example shows four.*

### C4 — Error middleware + shared DTOs + endpoint-module convention

**Epic:** `E0` Contract + foundations · **Story:** — · **Stack:** `be` · **Stream:** `foundations-api` · **Order:** 6
**Agent:** `be-dotnet` · **Skills:** `be-dotnet:patterns-apply`, `be-dotnet:unit-testing`
**Deliverable:** every failure returns the documented `application/problem+json` envelope, and a module
can self-register its routes without editing `Program.cs`.
**Depends on:** C2 (config + startup validation)
**Budget:** ~90k — CLAUDE.md 25k, `api-surface.md` §1/§3/§4 6k, 2 skills 16k, `src/Api/Program.cs` as
written by C2 ~4k, 4 files created and 1 modified 9.5k, commit and diff read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in `B7`. Do not run `dotnet build`, `dotnet test` or
`dotnet format`.

**Files:**
- Create: `src/Shared/ProblemDetailsMiddleware.cs`, `src/Shared/PagedResult.cs`, `src/Shared/SessionSummary.cs`
- Create: `src/Shared/IEndpointModule.cs` — each module self-registers its routes; this is what lets `scheduling` and `booking` run as separate lanes
- Modify: `src/Api/Program.cs`

- The RFC 9457 error envelope per `api-surface.md` §1/§4: stable `type` slugs, `traceId` taken from
  `traceparent`, and **all** field errors reported at once.
- Every failure returns `application/problem+json` with the documented shape — no bare strings, no
  stack traces, no second error shape reachable from an endpoint.
- Unknown request fields are rejected with 400, per §4's stated choice.
- `PagedResult<T>` and `SessionSummary` match `api-surface.md` §3 field-for-field.
- Unit tests in `tests/Shared.Tests/ProblemDetailsMiddlewareTests.cs` cover the envelope shape, the
  `traceId` propagation and the unknown-field rejection. In-process: no `WebApplicationFactory`.
- **Not in C4:** any endpoint (`B1`/`B2`), auth (`C3`), and anything on the web side — the client's
  handling of this envelope is `C6`, stack `fe`.
- **As built (2026-08-05):** `IEndpointModule` registers through an assembly scan in
  `src/Api/ModuleRegistration.cs` rather than an explicit list, so a new module needs no `Program.cs`
  edit at all (`src/Shared/ProblemDetailsMiddleware.cs:1-76`, `src/Api/ModuleRegistration.cs:1-31`).
  Tests written, not run — `B7` owns the gate.

### B2 — Bookings resource

**Epic:** `E2` Booking · **Story:** `US6`–`US9` · **Stack:** `be` · **Stream:** `booking-api` · **Order:** 12
**Agent:** `be-dotnet` · **Skills:** `be-dotnet:patterns-apply`, `be-dotnet:persistence`, `be-dotnet:unit-testing`
**Deliverable:** the four booking endpoints implement their documented behaviour, validation and
capacity guard — book, my-bookings, cancel, attend.
**Depends on:** C7 (the capacity constraint), C3 (auth), C4 (envelope + seam)
**Budget:** ~105k — CLAUDE.md 25k, `api-surface.md` §2/§5.3, `data-model.md` §3 and `blueprint.md` §3b
8k, 3 skills 24k, `src/Scheduling/*` as the module pattern ~12k, 5 files created 10k, commit and diff
read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in `B7`. Do not run `dotnet build`, `dotnet test` or
`dotnet format`.

**Files:**
- Create: `src/Booking/Domain/Booking.cs`, `src/Booking/BookingService.cs`, `src/Booking/BookingEndpoints.cs`, `src/Booking/BookingConfiguration.cs`
- Create: `tests/Booking.Tests/BookingServiceTests.cs`

- All four endpoints match `api-surface.md` §5.3 exactly: paths, fields, status codes.
- The three documented deltas return their slugs: `session-full`, `already-booked`, `invalid-state`.
- The capacity check is the DB-level guard from `data-model.md` §3 — **no app-side
  count-then-insert**.
- `lateCancel` is computed server-side per `blueprint.md` §3b's decision table (R1–R3), with one unit
  test per rule.
- Every undrawn state transition returns 409 naming the current and the allowed states.
- **Not in B2:** every screen (`F2`, stack `fe`, same epic — **the capability is not usable until
  `F2` lands, and `F2`'s deliverable is the one that says so**), the concurrency race test (QA pass,
  `qa-api-dotnet`), email on booking (`B4` — a booking that works without an email is still usable,
  and `B4` is blocked on provisioning this task must not wait for).
- **Progress (2026-08-09):** book and my-bookings are written
  (`src/Booking/BookingEndpoints.cs:1-88`), with the three deltas and the DB-level guard. Cancel and
  attend are unwritten; `lateCancel` and the 409 transition set land with cancel. The prompt block
  stays on `B2` with a `Picking up from:` line.

### F2 — Book + my-bookings screens (S3, S4)

**Epic:** `E2` Booking · **Story:** `US10` · **Stack:** `fe` · **Stream:** `booking-ui` · **Order:** 13
**Agent:** `fe-react` · **Skills:** `fe-react:component-writer`, `fe-react:data-fetching`, `design:app-structure`
**Deliverable:** a member can book a session, see it under their bookings, cancel it, and be told when
a session is full — journey J2, end to end. **This is the task that delivers `E2`.**
**Depends on:** C6 (shell + typed client), F1 (the session detail page the Book action lives on), B2 (the endpoints)
**Budget:** ~125k — CLAUDE.md 25k, `experience-plan.md` §3/§4 (S3, S4)/§6 and `api-surface.md` §5.3
10k, 3 skills 24k, `web/app/timetable/*` as the screen pattern ~14k, 2 screens + 3 components created
and 2 modified 15k, commit and diff read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in `B7`. Do not run `pnpm build` or `pnpm test`.

**Files:**
- Create: `web/app/bookings/page.tsx`, `web/app/bookings/booking-list.tsx`, `web/app/bookings/cancel-dialog.tsx`
- Create: `web/app/timetable/[sessionId]/book-button.tsx`
- Modify: `web/app/timetable/[sessionId]/page.tsx`, `web/lib/api-client.ts`

- S3 (My bookings) and S4 (Book a session) match `experience-plan.md` §4: page type, primary action,
  and all four region states.
- The full-session case renders the `session-full` delta from `api-surface.md` §5.3 as the screen's
  documented message — not a generic error, and not an empty list.
- Every failure is scoped to the response-dependent subtree and also raises a persistent top-right
  notification; the filters and the header keep rendering.
- `experience-plan.md` §6's responsiveness budget holds at all three breakpoints.
- Every interactive element and the bookings list container carry their `data-testid`.
- Vitest + RTL tests for the three components, queried by role and label.
- **Not in F2:** the booking endpoints (`B2`, stack `be`), the confirmation email (`B4`, stack `be`),
  E2E tests and the J2 walk-through (`qa-ui-typescript`, and `B7`'s close-out records whether the
  journey has been walked).

### B7 — the gate and the close-out

**Epic:** `E0` Contract + foundations · **Story:** — · **Stack:** `be` · **Stream:** `foundations-api` · **Order:** 20
**Agent:** `be-dotnet` · **Skills:** `be-dotnet:conventions-review`
**Deliverable:** the whole solution builds, the whole suite passes, the format check is clean, unit
tests cover ≥ 80% of the branches this plan wrote in each stack, and `docs/repository-state.md` says
what is built and what is unverified.
**Depends on:** every task above it — this is the plan's only gate
**Budget:** ~140k — CLAUDE.md 25k, this plan 12k, the `As built` notes of 17 tasks 10k, the gate output
and the fix loop 12k plus 4k per earlier task whose failures land here (~40k budgeted for six),
the coverage reports and the tests a shortfall needs ~10k, the docs written 8k, churn ×1.2
**Gate (this is the last runnable task, so it carries the plan's only gate, in run order):**
```
dotnet build   →  dotnet test   →  dotnet format --verify-no-changes
pnpm install   →  pnpm build    →  pnpm test
coverage floor (plan-format.md §5) over the files git lists since this plan's first commit:
  dotnet test --collect:"XPlat Code Coverage"  →  dotnet tool run reportgenerator … -filefilters:<the .cs files>
  pnpm vitest run --coverage --coverage.reporter=text --coverage.include=<each web file>
```
**Fix what it finds rather than handing it back.** A failure may belong to any task above this one;
attributing it is part of this task, and the `As built` note says which task each one belonged to.

**Files:**
- Modify: whatever the gate proves wrong, in whichever task's tree it lives
- Create: `docs/repository-state.md`, `docs/api/README.md`

- Run the gate in the order above. Do not reorder it: a format failure after a red build wastes the run.
- Every failure is fixed here, and attributed in the `As built` note to the task that introduced it.
- The coverage floor runs last: ≥ 80% of the branches the plan wrote, per stack. A shortfall is closed
  by writing the missing tests in the owning task's test project and attributed like any failure; the
  `As built` note records each stack's figure and names every file left out (DTOs, EF configurations,
  the DI modules, migrations).
- `docs/repository-state.md` names what is built, and separately what is **built but unverified** —
  at minimum: journey J2 has not been walked by a person, the concurrency race on the capacity guard
  has not been exercised, and no email has been sent (`B4` is blocked on `H2`).
- The plan's `**Status:**` line is rewritten from what the gate actually showed.
- **The plan is not filed here.** `B4` is blocked on `H2` and still holds a prompt block, so
  `docs/plans/003-workshop-booking/` stays in `docs/plans/`. Say so in `Status:`. `B4` is the task
  that will delete the last block, and its prompt carries the move to `docs/plans/implemented/`.
- **Not in B7:** the contract and integration suites (`qa-api-dotnet`), the E2E journeys
  (`qa-ui-typescript`), the access-control proof (`qa-security`) — and `B4`, which is blocked on `H2`
  and carries its own gate whenever it runs.

### H1, H2, C1–C3, C5–C7, B1, B3–B6, F1, F3, DA1 — abbreviated in this example

Each gets the same block shape, deliverable first, `Gate: none` on every one. Notable:

- **`H1` and `H2` are human prerequisite tasks** from `integrations.md` §5 — `Agent: human`,
  `Stack: human`, each block carrying an `**Owner:**` line (`H1`: the studio owner's Auth0 admin;
  `H2`: the studio owner), exempt from catalog-name resolution and from budgeting.
- **`C6` is `Stack: fe`** despite being foundations — the app shell, the nav map and the typed client
  are the web tree, so they are their own task with `fe-react` as the agent.
- **`DA1` is `Stack: data`**, agent `data-architect`, and executes `data-model.md` §9's routed
  decision: a written verdict on the capacity guard under concurrent booking, with any constraint
  change applied.
- **`B6` is agent `observability-engineer-dotnet`**, not `be-dotnet` — same stack, different peer.
- **`B4` sits below `B7`**, because it is blocked on `H2`. `B7` is the last *runnable* task and
  therefore the gate; `B4` carries its own gate for whenever the sending domain clears.

## 4. Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| — | none — all settled at blueprint approval | | | |

## 5. Deliberately not planned

Contract/integration tests (`qa-api-dotnet`), the access-control proof (`qa-security`), E2E journeys
(`qa-ui-typescript`), pipeline beyond the CI skeleton (`devops-engineer`).

## 6. Decisions

**D1 — the Workshops and Sessions endpoints live in one file.** `B1` was planned as separate
`WorkshopEndpoints.cs` + `SessionEndpoints.cs`; it built one `SessionEndpoints.cs` carrying both
(`src/Scheduling/SessionEndpoints.cs:1-140`). One aggregate, and a second file bought nothing.
Escalated as a divergence, accepted by the studio owner, plan amended. *(2026-08-06)*

**D2 — the confirmation email is its own task, ordered after the booking capability.** Booking is
usable without it, and `H2` is blocked; folding the email into `B2` would have made a working
capability wait on provisioning. *(2026-08-02)*

**D3 — the booking endpoints and the booking screens are two tasks, and `E2` is not usable until `F2`
lands.** This is the one-stack rule, recorded once rather than re-argued per capability. The cost is
stated rather than discovered: `B2` finished is not a demo. *(2026-08-02)*

**D4 — the plan gates once, in `B7`.** Seventeen tasks × a 12k verify loop each is ~200k of context
spent proving the same tree, and a failure in task 6 is usually only diagnosable once task 12 exists.
The accepted cost: the tree is not known to build at any boundary before `B7`, and this plan cannot be
stopped halfway and trusted. `C4`'s and `B2`'s `As built` notes say "tests written, not run" for
exactly this reason. *(2026-08-02)*

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one session each. Every block is complete on its own — it names the agent, the
skills, and the exact sections to read. **This plan gates once, in `B7`:** every block before it says
`Gate: none` and names what not to run. No block may run `dotnet test` or `pnpm test`.

**Gates run locally.** Commit locally; ask before `git push`.

| # | Task | Epic | Story | Stack | Stream | Deliverable | Agent | Budget | Depends on |
|---|---|---|---|---|---|---|---|---|---|
| 1 | H1 | `E0` | — | `human` | `foundations-api` | Dev and prod Auth0 apps exist; their domain + audience are in the config keys `C3` reads | **the user** | — | — |
| 2 | H2 | `E0` | — | `human` | `email` | A verified sending domain and an API key `B4` can send with | **the user** | — | — |
| 3 | C1 | `E0` | — | `be` | `foundations-api` | An empty solution with the four module projects in place | `be-dotnet` | ~60k | — |
| 4 | C2 | `E0` | — | `be` | `foundations-api` | The app refuses to start on missing/invalid config; CI runs build + test on every push | `be-dotnet` | ~75k | C1 |
| 5 | C3 | `E0` | — | `be` | `foundations-api` | A request without a valid token gets 401; one without the permission gets 403 | `be-dotnet` | ~85k | C2, H1 |
| 6 | C4 | `E0` | — | `be` | `foundations-api` | Every failure returns the documented envelope; a module self-registers its routes | `be-dotnet` | ~90k | C2 |
| 7 | C5 | `E0` | — | `be` | `schema` | Migration head `002` applies; `workshops` and `sessions` exist with their FKs and seeds | `be-dotnet` | ~70k | C2 |
| 8 | C6 | `E0` | — | `fe` | `foundations-ui` | The shell renders with every nav entry present, and the typed client covers `api-surface.md` §5 | `fe-react` | ~130k | C4 |
| 9 | B1 | `E1` | `US1`–`US3` | `be` | `timetable-api` | An admin can publish a workshop, add sessions and list them via the API; nobody else can | `be-dotnet` | ~112k | C5, C3, C4 |
| 10 | F1 | `E1` | `US4`–`US5` | `fe` | `timetable-ui` | **A member browses the timetable and an admin publishes a workshop** — J1 complete | `fe-react` | ~140k | C6, B1 |
| 11 | C7 | `E0` | — | `be` | `schema` | Migration head `003` applies; a booking past capacity is rejected by the database itself | `be-dotnet` | ~65k | C5 |
| 12 | B2 | `E2` | `US6`–`US9` | `be` | `booking-api` | The four booking endpoints implement their documented behaviour, validation and capacity guard | `be-dotnet` | ~105k | C7, C3, C4 |
| 13 | F2 | `E2` | `US10` | `fe` | `booking-ui` | **A member books, sees, cancels, and is told when a session is full** — J2 complete | `fe-react` | ~125k | C6, F1, B2 |
| 14 | B3 | `E3` | `US11`–`US12` | `be` | `profile-api` | A member can read and update their own profile, and cannot read anyone else's | `be-dotnet` | ~95k | C5, C3, C4 |
| 15 | F3 | `E3` | `US13` | `fe` | `profile-ui` | **A member views and edits their own profile** — J3 complete | `fe-react` | ~100k | C6, B3 |
| 16 | B5 | `E0` | — | `be` | `foundations-api` | The committed OpenAPI asset matches the implemented surface endpoint for endpoint | `be-dotnet` | ~70k | B1, B2, B3 |
| 17 | B6 | `E0` | — | `be` | `foundations-api` | Every request emits a trace and the standard metric set, `traceId` matching the envelope | `observability-engineer-dotnet` | ~95k | B1, B2 |
| 18 | DA1 | `E0` | — | `data` | `schema` | A written verdict on the capacity guard under concurrent booking, with any constraint change applied | `data-architect` | ~80k | C7 |
| 19 | B7 | `E0` | — | `be` | `foundations-api` | The solution builds, the suite passes, the format check is clean, and the repository-state note is written | `be-dotnet` | ~140k | all of the above |
| 20 | B4 | `E4` | `US14` | `be` | `email` | A confirmed booking produces a confirmation email, deliverable in dev against Mailpit | `be-dotnet` | ~90k | C4, B2, H2 |

**`H1`, `C1`–`C7`, `B1` and `F1` have landed, and their prompts are deleted** — a prompt for a
finished task is a thing someone runs by mistake. `B2` (held, partial), `F2`, `B3`, `F3`, `B5`, `B6`,
`DA1`, `B7` and `B4` (blocked) are live.

---

### B2 — Bookings resource (be-dotnet, be) — held, partial

````
You are `be-dotnet`. Task B2 of docs/plans/003-workshop-booking/delivery-plan.md: finish the Bookings
resource.

**Picking up from:** book and my-bookings are written and correct (`src/Booking/BookingEndpoints.cs:1-88`).
**Cancel and attend are unwritten**, and `lateCancel` plus the 409 transition set land with cancel.
The task's unfinished bullets are that list.

Read your agent definition, then load exactly these skills: `be-dotnet:patterns-apply`,
`be-dotnet:persistence`, `be-dotnet:unit-testing`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md — the Backend code rules, the Test code rules and the Comments rules.
2. The plan: §3 task B2 (including its `Progress` line), `api-surface.md` §5.3 (the cancel and attend
   endpoint blocks), `blueprint.md` §3b (the cancellation decision table R1–R3), `data-model.md` §3
   (the capacity guard).
3. `src/Booking/BookingEndpoints.cs` and `src/Booking/BookingService.cs` as you left them, and
   `src/Shared/ProblemDetailsMiddleware.cs` + `src/Api/ModuleRegistration.cs` — the envelope and the
   assembly-scan seam C4 built (see C4's `As built` note: there is no explicit module list).
4. The plan's "Close-out — every task".

Deliverable: the four booking endpoints implement their documented behaviour, validation and capacity
guard — book, my-bookings, cancel, attend.

Build:
- Cancel and attend match `api-surface.md` §5.3 exactly: paths, fields, status codes.
- `lateCancel` is computed server-side per `blueprint.md` §3b (R1–R3), one unit test per rule.
- Every undrawn state transition returns 409 naming the current and the allowed states.
- `invalid-state` is the documented slug; the envelope comes from the middleware, never from the
  endpoint.

Out of scope: the screens (F2, `fe-react`), the concurrency race test (`qa-api-dotnet`), email on
booking (B4, blocked on H2).

Traps:
- The capacity guard is the DB exclusion constraint from C7. Do not add an app-side count-then-insert
  "for a nicer error" — catch the constraint violation and map it to `session-full`.
- `lateCancel` is a server-side computation, not a client-supplied flag. The request body in §5.3 has
  no such field.
- `blueprint.md` §3b's R3 is the one people miss: a cancellation inside the window on a session that
  has already started is `invalid-state`, not a late cancel.

Gate: none — this plan gates once, in B7. Do not run `dotnet build`, `dotnet test` or `dotnet format`.
Write the tests; leave running them to B7.

Commit: `feat: booking cancel and attend (B2)`.

Your `As built` note carries the `file:line` for cancel, attend and the `lateCancel` computation.
F2's block binds to the cancel response fields, so a rename there is a rewrite of F2's block. B4's
block was left `Blocked on B2`: write it from the exact name and payload of the domain event you
raise on a confirmed booking, which does not exist until this task lands.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### B4 — the confirmation email (be-dotnet, be)

**Blocked on B2** for the prompt — B2 writes this block when it lands, from the exact name and payload
of the `BookingConfirmed` domain event it raises. **And blocked on H2** to run at all: the SendGrid
sending domain is not verified (`integrations.md` §5), owned by the studio owner, since 2026-08-04.
`B4` sits below `B7`, so it carries its own gate whenever it runs — **and, as the task that will delete
the last prompt block, it carries the filing duty:** rewrite `Status:` with what the pack finally
delivered and what is still unverified, then
`git mv docs/plans/003-workshop-booking docs/plans/implemented/`, the whole folder, in its own commit.

---

*(The remaining live blocks — `F2`, `B3`, `F3`, `B5`, `B6`, `DA1`, `B7` — are abbreviated in this
example. `B7`'s block is the one that carries the gate, in run order, with the instruction to fix what
it finds and attribute each failure to the task that introduced it.)*

## For Mission Control

Paste this document into the plan box and point the run at `~/src/workshop-booking`.
The task graph maps 1:1 — the nine streams in §2 become MC's lanes, each task keeps
its `stream` and `order` alongside its `deliverable`, `agent`, `skills`, `files` and
`dependsOn`, and the open questions in §4 carry their options. `epic`, `story`, `stack`
and `budget` travel with each task as additive fields — MC ignores what it does not
know, and losing them costs the whole epic and sizing story on a round trip. There is
no grouping level: ordering is the `order` sequence, and every prerequisite is an
explicit `dependsOn` edge. **This plan gates once, in `B7`** — every earlier task
deliberately runs no build or test command, so a lane that reports green without one is
behaving as planned. MC's planner re-reads the target repo, so it may split a task it
finds too large; that is expected and does not invalidate the sequence — the new pieces
belong in the split task's own lane, and each needs its own deliverable.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
| — | none | | |
