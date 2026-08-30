# Golden example — `delivery-plan.md`

The filled example for `be-shared-delivery-plan`, from the **workshop-booking** toy initiative shared by all the planner examples. **Shapes and disciplines are normative; domain content is illustrative.** A real artifact writes a full block for *every* task — this example writes three representative ones (a foundation task, a capability task, the OpenAPI-asset task) and abbreviates the rest, saying so. Workshop booking is user-facing, so it is sequenced **feature-complete**: after the foundations the first capability needs, the tasks for one capability run back to back and the last of them makes it usable. The paired `NEXT-PROMPTS.md` example lives in `backend/_shared/session-budget/references/next-prompts-template.md`, already filled; the epic map these streams derive from is in `backend/_shared/epic-map/references/example-epic-map.md`.

Read for three things this example carries that a generic plan does not: every task names **one** stack, so the backend and screens of one capability are separate tasks; every task carries its **epic and story**; and every task carries an **`Est. context`** with the drivers behind it.

---

# Workshop Booking — Delivery Plan

**Date:** 2026-08-02 · **Written by:** `be-shared-delivery-plan`
**Pack:** `./epics.md` · `./stories.md` · `./blueprint.md` · `./data-model.md` · `./experience-plan.md` · `./api-surface.md` · `./integrations.md` · `./epic-map.md`
**Target repo:** `~/src/workshop-booking` · **Stack:** .NET 10 + PostgreSQL 18 (`src/`) · React 19 + Next 15 (`web/`)
**Build/test:** `dotnet build` / `dotnet test` for `be` tasks · `pnpm build` / `pnpm test` for `fe` tasks (greenfield — both become the project's own once scaffolded)

> **For agentic workers:** the tasks below are one flat sequence — work them in order. Each names
> the agent that should execute it, the skills to load, and the one deliverable that means it is done.
> Run them with `ep-executing-plans` inline, or hand the whole document to Mission Control.
> **Update this document as you work** — Status + Evidence in §2, the criterion checkboxes in §3,
> an append-only row in §6, and any decision or deviation in §7. **Then rewrite your lane's block in
> `NEXT-PROMPTS.md`** for the next task, per `be-shared-session-budget` Step 5.

## 1. Streams

Derived from `epic-map.md` §2, split by stack where a lane spans two — the one-stack rule turns
`foundations` into `foundations-api` + `foundations-ui`, and each capability lane into an `-api`
and a `-ui`. Both splits are recorded back into `epic-map.md` §2.

| Stream | Epic | Stack | Owns | Why it is internally sequential |
|---|---|---|---|---|
| `foundations-api` | `E0` | `be` | Solution root and everything shared: scaffold, config, CI, auth wiring, error middleware, the endpoint-module seam, the OpenAPI asset, telemetry base | Every task edits the solution root or `src/Api/Program.cs`. T0.1 sits here too — the Auth0 tenant is what T5 wires, so the provisioning belongs to the lane that consumes it |
| `schema` | `E0` | `be` | Migrations and the data-integrity work that follows from them — `src/Api/Migrations/*` | Migrations are ordered by definition, and T15's guard review reads the constraint T4 creates. Disjoint from `foundations-api`'s file set, so it is its own lane rather than part of it |
| `foundations-ui` | `E0` | `fe` | App shell, nav map, route tree, the typed API client — `web/app/layout.tsx`, `web/app/(nav)/*`, `web/lib/api-client.ts` | One root file set on the web side, exactly as `foundations-api` is on the API side |
| `timetable-api` | `E1` | `be` | Workshops + Sessions — `src/Scheduling/*` | One module, one file set |
| `timetable-ui` | `E1` | `fe` | The public timetable and the admin workshop editor — `web/app/timetable/*`, `web/app/admin/workshops/*` | Both screens share the session-card component |
| `booking-api` | `E2` | `be` | The Bookings resource — `src/Booking/*` | One module, one file set |
| `booking-ui` | `E2` | `fe` | Book and my-bookings — `web/app/bookings/*` | One screen set over one aggregate |
| `profile-api` / `profile-ui` | `E3` | `be` / `fe` | Member profile — `src/Membership/*` · `web/app/profile/*` | *(abbreviated in this example)* |
| `email` | `E4` | `be` | The confirmation email — `src/Notifications/*` | One story, one tree — a lane of one task |

`email` finishes T0.2 in minutes and then waits — not on a barrier, but on T13's own `dependsOn`
(T9, T11): the event it subscribes to does not exist until the booking API lands. Every such wait is
an edge in §2, not an implied rule.

**Note what the one-stack rule bought here.** `timetable-api` and `profile-api` are wave-2 lanes with
disjoint file sets, so they can run at the same time; under a mixed `scheduling` lane carrying both
endpoints and screens, `timetable-ui`'s dependency on `timetable-api` would have serialised all four.

## 2. Progress

One flat sequence, in the order the work is done — a valid serialization of `epic-map.md`'s
dependency graph, not a wave-by-wave march through it. Shown mid-execution, as an executing agent
maintains it: the timetable capability delivered, booking in flight.

| # | Task | Epic | Story | Stack | Stream | Title | Deliverable | Agent | Est. | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | T0.1 | `E0` | — | `human` | `foundations-api` | Auth0 tenant + per-env applications | Dev and prod Auth0 apps exist; their domain + audience are in the config keys T5 reads | `human` | — | — | Done | tenant `workshop-dev`, apps created 2026-08-03 |
| 2 | T0.2 | `E0` | — | `human` | `email` | SendGrid account + domain auth | A verified sending domain and an API key T13 can send with | `human` | — | — | Blocked | domain auth pending — studio owner |
| 3 | T1 | `E0` | — | `be` | `foundations-api` | Scaffold solution + module layout | `dotnet build` succeeds on an empty solution with the four module projects in place | `be-dotnet` | ~60k | — | Done | `WorkshopBooking.sln:1`; `dotnet build` clean |
| 4 | T2 | `E0` | — | `be` | `foundations-api` | Config + startup validation, CI skeleton | The app refuses to start on missing/invalid config, and CI runs build + test on every push | `be-dotnet` | ~75k | T1 | Done | `src/Api/Configuration/AppOptions.cs:1-42` |
| 5 | T5 | `E0` | — | `be` | `foundations-api` | Auth wiring (JWT bearer, two permissions) | A request without a valid token gets 401; one without the required permission gets 403 | `be-dotnet` | ~85k | T2, T0.1 | Done | `src/Api/Program.cs:18-40` |
| 6 | T9 | `E0` | — | `be` | `foundations-api` | Error middleware + shared DTOs + endpoint-module convention | Every failure returns the documented `application/problem+json` envelope, and a module can self-register its routes | `be-dotnet` | ~90k | T2 | Done | `src/Shared/ProblemDetailsMiddleware.cs:1-76` |
| 7 | T3 | `E0` | — | `be` | `schema` | Migrations 001–002 (workshops, sessions) + seeds | Migration head `002` applies on an empty database; `workshops` and `sessions` exist with their FKs and seed rows | `be-dotnet` | ~70k | T2 | Done | `src/Api/Migrations/002_Sessions.cs:1`; head `002` applied |
| 8 | T6 | `E0` | — | `fe` | `foundations-ui` | App shell, nav map, route tree, typed API client | The shell renders with every nav entry present, and `web/lib/api-client.ts` types every endpoint in `api-surface.md` §5 | `fe-react` | ~130k | T9 | Done | `web/app/layout.tsx:1-64`; `web/lib/api-client.ts:1-210` |
| 9 | T10 | `E1` | `US1`–`US3` | `be` | `timetable-api` | Workshops + Sessions resources | A studio admin can publish a workshop, add sessions to it, and list them via the API; nobody else can | `be-dotnet` | ~112k | T3, T5, T9 | Done | `src/Scheduling/SessionEndpoints.cs:1-140`; 24 tests green |
| 10 | T16 | `E1` | `US4`–`US5` | `fe` | `timetable-ui` | Timetable + admin workshop screens (S1, S2, S5) | **A member can browse the timetable and an admin can publish a workshop from the UI** — journey J1 complete | `fe-react` | ~140k | T6, T10 | Done | `web/app/timetable/page.tsx:1-118`; J1 walked by hand 2026-08-08 |
| 11 | T4 | `E0` | — | `be` | `schema` | Migration 003 (bookings) + capacity constraint | Migration head `003` applies; a second booking past capacity is rejected by the database itself | `be-dotnet` | ~65k | T3 | Done | `src/Api/Migrations/003_Bookings.cs:1-58`; head `003` applied |
| 12 | T11 | `E2` | `US6`–`US9` | `be` | `booking-api` | Bookings resource | The four booking endpoints implement their documented behaviour, validation and capacity guard | `be-dotnet` | ~105k | T4, T5, T9 | Partial | book + my-bookings in `src/Booking/BookingEndpoints.cs:1-88`; cancel + attend not written |
| 13 | T17 | `E2` | `US10` | `fe` | `booking-ui` | Book + my-bookings screens (S3, S4) | **A member can book a session, see it under their bookings, cancel it, and be told when a session is full** — journey J2 complete | `fe-react` | ~125k | T6, T16, T11 | Not started | — |
| 14 | T20 | `E3` | `US11`–`US12` | `be` | `profile-api` | Member profile resource | A member can read and update their own profile through the API, and cannot read anyone else's | `be-dotnet` | ~95k | T3, T5, T9 | Not started | — |
| 15 | T21 | `E3` | `US13` | `fe` | `profile-ui` | Profile screen (S6) | **A member can view and edit their own profile** — journey J3 complete | `fe-react` | ~100k | T6, T20 | Not started | — |
| 16 | T13 | `E4` | `US14` | `be` | `email` | Email sender (SendGrid + Mailpit lane) | A confirmed booking produces a confirmation email — deliverable in dev against Mailpit | `be-dotnet` | ~90k | T9, T11 | Blocked | T0.2 |
| 17 | T12 | `E0` | — | `be` | `foundations-api` | Generate + commit the OpenAPI asset | `docs/api/booking-api-openapi-2026-08-02.json` is committed and matches the implemented surface | `be-dotnet` | ~70k | T10, T11, T20 | Not started | — |
| 18 | T14 | `E0` | — | `be` | `foundations-api` | Telemetry base | Every request emits a trace and the standard metric set, with `traceId` matching the error envelope | `observability-engineer-dotnet` | ~95k | T10, T11 | Not started | — |
| 19 | T15 | `E0` | — | `data` | `schema` | Overbooking guard depth review | A written verdict on the capacity guard under concurrent booking, with any constraint change applied | `data-architect` | ~80k | T4 | Not started | — |

Status vocabulary: Not started · In progress · Done · Partial · Diverged · Blocked. A `Done`/`Partial` with an empty Evidence cell is a plan defect.

Note T5 and T9 sharing `foundations-api`: both modify `src/Api/Program.cs`, so they may not be separate lanes however independent they read. T12 and T14 are in the same lane for the same reason and run late in it — their `dependsOn` holds them behind the resource tasks without a lane needing to say so.

T16's deliverable was checked by hand on 2026-08-08: a member browsed the timetable, an admin published a workshop and added two sessions, and a member token got no admin controls. That check is what made T16 `Done` — not the ticked criteria, and not T10's green tests. **T10 alone did not deliver E1**: the API existed and nothing a person uses did, which is exactly what the one-stack rule makes visible in the plan instead of at demo time.

## 3. Tasks

*A real artifact writes every block; this example shows four — a foundation task, a backend capability task, the frontend task that actually delivers that capability, and the OpenAPI-asset task.*

### T9 — Error middleware + shared DTOs + endpoint-module convention

**Deliverable:** every failure returns the documented `application/problem+json` envelope, and a
module can self-register its routes without editing `Program.cs`.
**Epic:** `E0` Contract + foundations · **Story:** — · **Stack:** `be`
**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
**Stream:** `foundations-api` · **Order:** 6
**Est. context:** ~90k — 4 files created, 1 modified, 2 skills, 3 pack sections
**Depends on:** T2
**Files:**
- Create: `src/Shared/ProblemDetailsMiddleware.cs`, `src/Shared/PagedResult.cs`, `src/Shared/SessionSummary.cs`
- Create: `src/Shared/IEndpointModule.cs` (each module self-registers its routes — this is what lets `scheduling` and `booking` run as separate lanes)
- Modify: `src/Api/Program.cs`

**Intent:** the RFC 9457 error envelope per `api-surface.md` §1/§4 (stable `type` slugs, `traceId` from `traceparent`, all field errors at once), the shared schemas from §3, and the module registration seam.

**Acceptance criteria:**
- [ ] Every failure returns `application/problem+json` with the documented shape; no bare strings, no stack traces
- [ ] Unknown request fields are rejected with 400 per §4's stated choice
- [ ] `PagedResult<T>` and `SessionSummary` match `api-surface.md` §3 field-for-field
- [ ] `dotnet build` clean, 0 warnings; `dotnet test` green

**Out of scope:** any endpoint (T10/T11), auth (T5), and anything on the web side — the client's error
handling of this envelope is T6, stack `fe`.

### T11 — Bookings resource

**Deliverable:** the four booking endpoints implement their documented behaviour, validation and
capacity guard — book, my-bookings, cancel, attend.
**Epic:** `E2` Booking · **Story:** `US6`–`US9` · **Stack:** `be`
**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
**Stream:** `booking-api` · **Order:** 12
**Est. context:** ~105k — 5 files created, 3 skills, 4 pack sections, 2 existing files read
**Depends on:** T4, T5, T9
**Files:**
- Create: `src/Booking/Domain/Booking.cs`, `src/Booking/BookingService.cs`, `src/Booking/BookingEndpoints.cs`, `src/Booking/BookingConfiguration.cs`
- Create: `tests/Booking.Tests/BookingServiceTests.cs`

**Intent:** the four booking endpoints in `api-surface.md` §2/§5 (book, my-bookings, cancel, attend), with the DB-level capacity guard from `data-model.md` §3 and the cancellation decision table from `blueprint.md` §3b.

**Acceptance criteria:** *(ticked in place as the work lands — the unticked ones are the remaining list)*
- [ ] All four endpoints match `api-surface.md` exactly: paths, fields, status codes — book + my-bookings done, cancel + attend remain
- [x] The three documented deltas return their slugs: `session-full`, `already-booked`, `invalid-state`
- [x] The capacity check is the DB-level guard — no app-side count-then-insert
- [ ] `lateCancel` is computed server-side per the blueprint decision table (R1–R3), covered by unit tests per rule
- [ ] Every undrawn state transition returns 409 naming current and allowed states
- [x] `dotnet build` clean; `dotnet test` green

**Progress:** cancel and attend are unwritten; `lateCancel` and the 409 transition set land with cancel.

**Out of scope:** every screen (T17, stack `fe`, same epic — **the capability is not usable until T17
lands, and T17's deliverable is the one that says so**), the concurrency race test (QA pass,
`qa-api-dotnet`), email on booking (T13 — a booking that works without an email is still usable, and
T13 is blocked on provisioning this task must not wait for).

### T12 — Generate + commit the OpenAPI asset

**Deliverable:** `docs/api/booking-api-openapi-2026-08-02.json` is committed, canonicalized, and
matches the implemented surface endpoint for endpoint.
**Epic:** `E0` Contract + foundations · **Story:** — · **Stack:** `be`
**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
**Stream:** `foundations-api` · **Order:** 17
**Est. context:** ~70k — 1 file created, 1 modified, 2 skills, 1 pack section
**Depends on:** T10, T11, T20
**Files:**
- Create: `docs/api/booking-api-openapi-2026-08-02.json` (canonicalized: `jq -S`, 2-space)
- Modify: `src/Api/Program.cs` (OpenAPI generation wiring, if not already on)

**Intent:** emit the implemented surface as the committed OpenAPI asset so `qa/_shared/api-spec-assets` has its canonical input from day one — `qa-api-dotnet` ingests *this file*, and every later contract change flows through that skill's diff-driven lane instead of being reverse-engineered.

**Acceptance criteria:**
- [ ] The generated spec matches `api-surface.md`'s endpoint map: every path, method, and documented status per endpoint
- [ ] Committed under the `{service}-openapi-YYYY-MM-DD.json` naming `api-spec-assets` expects, canonicalized
- [ ] A drift between the spec and `api-surface.md` is reported, not silently reconciled — the plan may be stale (reconcile rules apply)

**Out of scope:** writing any test from the spec (`qa-api-dotnet`), maintaining the asset thereafter (`qa/_shared/api-spec-assets`).

### T17 — Book + my-bookings screens (S3, S4)

**Deliverable:** a member can book a session, see it under their bookings, cancel it, and be told when
a session is full — journey J2, end to end. **This is the task that delivers `E2`.**
**Epic:** `E2` Booking · **Story:** `US10` · **Stack:** `fe`
**Agent:** `fe-react` · **Skills:** `fe-react-component-writer`, `fe-react-data-fetching`, `design-ux-patterns`
**Stream:** `booking-ui` · **Order:** 13
**Est. context:** ~125k — 2 screens + 3 components created, 2 modified, 3 skills, 5 pack sections
**Depends on:** T6 (shell + typed client), T16 (the session detail page the Book action lives on), T11 (the endpoints)
**Files:**
- Create: `web/app/bookings/page.tsx`, `web/app/bookings/booking-list.tsx`, `web/app/bookings/cancel-dialog.tsx`
- Create: `web/app/timetable/[sessionId]/book-button.tsx`
- Modify: `web/app/timetable/[sessionId]/page.tsx`, `web/lib/api-client.ts`

**Intent:** screens S3 (My bookings) and S4 (Book a session) from `experience-plan.md` §4, completing
journey J2 (§3), against the four endpoints in `api-surface.md` §5.3.

**Acceptance criteria:**
- [ ] S3 and S4 match `experience-plan.md` §4: page type, primary action, and all four region states
- [ ] The full-session case renders the `session-full` delta from `api-surface.md` §5.3 as the screen's
      documented message — not a generic error, and not an empty list
- [ ] Every failure is scoped to the response-dependent subtree and also raises a persistent top-right
      notification; the filters and header keep rendering
- [ ] `experience-plan.md` §6's responsiveness budget holds at all three breakpoints
- [ ] Every interactive element and the bookings list container carry their `data-testid`
- [ ] Journey J2 walked by hand end to end, and the walk recorded in §6
- [ ] `pnpm build` clean; `pnpm test` green

**Out of scope:** the booking endpoints (T11, stack `be` — already landed), the confirmation email
(T13, stack `be`), E2E tests (`qa-ui-typescript`).

### T0.1–T21, remaining — abbreviated in this example
Each gets the same block shape, deliverable first. Notable: T0.x are human prerequisite tasks from `integrations.md` §5 (the three-places rule) — `Agent: human`, `Stack: human`, each block carrying an `**Owner:**` line (T0.1: the studio owner's Auth0 admin; T0.2: the studio owner), exempt from catalog-name resolution and from sizing per the skill's rules; T15 is `Stack: data` and executes `data-model.md` §9's routed decision; T20/T21 are the `E3` pair, one `be` and one `fe`, on the same shape as T11/T17.

## 4. Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| — | none — all settled at blueprint approval | | | |

## 5. Deliberately not planned

Contract/integration tests (`qa-api-dotnet`), the access-control proof (`qa-security`), pipeline beyond the CI skeleton (`devops-engineer`), both SPAs (`fe-react`).

## 6. Execution log

<!-- append-only, oldest first: one row per status change. Never edited, never deleted -->

| When | Task | Status | By | Note |
|---|---|---|---|---|
| 2026-08-03 | T0.1 | Done | Studio owner | Auth0 tenant `workshop-dev` + dev/prod apps |
| 2026-08-04 | T1, T2 | Done | `be-dotnet` | Scaffold + config; CI skeleton runs build+test |
| 2026-08-04 | T0.2 | Blocked | Studio owner | SendGrid domain authentication pending |
| 2026-08-05 | T5, T9 | Done | `be-dotnet` | Auth wiring + error envelope in place |
| 2026-08-06 | T3 | Done | `be-dotnet` | Migrations 001–002 applied, seeds loaded |
| 2026-08-06 | T6 | Done | `fe-react` | Shell, nav map and typed client; every nav entry present from the start |
| 2026-08-06 | T10 | Done | `be-dotnet` | API verified with tokens: admin publishes + lists, member gets 403. Both resources in one endpoint file — see D1 |
| 2026-08-08 | T16 | Done | `fe-react` | **E1 usable**: J1 walked by hand — member browses, admin publishes |
| 2026-08-08 | T4 | Done | `be-dotnet` | Migration 003 + `sessions_capacity` exclusion constraint |
| 2026-08-09 | T11 | In progress | `be-dotnet` | book + my-bookings done |
| 2026-08-09 | T11 | Partial | `be-dotnet` | Session ended; cancel + attend remain. `NEXT-PROMPTS.md` block kept on T11 with a `Picking up from:` line |

## 7. Decisions & deviations

| # | Task | Plan said | What was decided/built | Why | When |
|---|---|---|---|---|---|
| D1 | T10 | Separate `WorkshopEndpoints.cs` + `SessionEndpoints.cs` | One `SessionEndpoints.cs` carrying both resources (`src/Scheduling/SessionEndpoints.cs:1-140`) | One aggregate; a second file bought nothing. Escalated as `Diverged`, human accepted, plan amended | 2026-08-06 |
| D2 | T13 | Email sent as part of the bookings task | Its own task, ordered after the booking capability | Booking is usable without it and T0.2 is blocked; T11 must not wait on provisioning | 2026-08-02 |
| D3 | T11, T17 | *(no plan said — this is the shape, recorded once)* | The booking endpoints and the booking screens are two tasks, `be` and `fe`, and `E2` is not usable until T17 lands | One stack per task. The cost is stated rather than discovered: T11 `Done` is not a demo | 2026-08-02 |

## For Mission Control

Paste this document into the plan box and point the run at `~/src/workshop-booking`.
The task graph maps 1:1 — the nine streams in §1 become MC's lanes, each task keeps
its `stream` and `order` alongside its `deliverable`, `agent`, `skills`, `files` and
`dependsOn`, and the open questions above carry their options. `epic`, `story`, `stack`
and `estContext` travel with each task as additive fields — MC ignores what it does not
know, and losing them costs the whole epic and sizing story on a round trip. There is no grouping
level: ordering is the `order` sequence, and every prerequisite is an explicit
`dependsOn` edge. MC's planner re-reads the target repo, so it may split a task it
finds too large; that is expected and does not invalidate the sequence — the new
pieces belong in the split task's own lane, and each needs its own deliverable.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
| — | none | | |
