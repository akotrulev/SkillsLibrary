# Golden example — `delivery-plan.md`

The filled example for `be-shared-delivery-plan`, from the **workshop-booking** toy initiative shared by all five planner examples. **Shapes and disciplines are normative; domain content is illustrative.** A real artifact writes a full block for *every* task — this example writes three representative ones (a foundation task, a feature slice, the OpenAPI-asset task) and abbreviates the rest, saying so. Workshop booking is user-facing, so it is sequenced **feature-complete**: after the foundations the first capability needs, each phase closes on something a person can actually do. The paired `HANDOFF.md` example lives in `handoff-template.md`, already filled.

---

# Workshop Booking — Delivery Plan

**Date:** 2026-08-02 · **Written by:** `be-shared-delivery-plan`
**Pack:** `./blueprint.md` · `./data-model.md` · `./api-surface.md` · `./integrations.md`
**Target repo:** `~/src/workshop-booking` · **Stack:** .NET 10 + PostgreSQL 18 · **Build/test:** `dotnet build` / `dotnet test` (greenfield — becomes the project's own once scaffolded)

> **For agentic workers:** each task names the agent that should execute it and the skills to load.
> Run them with `ep-executing-plans` inline, or hand the whole document to Mission Control.
> **Update this document as you work** — Status + Evidence in §3, the criterion checkboxes in §4,
> an append-only row in §7, and any decision or deviation in §8. `HANDOFF.md` says only what's next.

## 1. Phases

Sequencing shape: **feature-complete** — this is a user-facing product, and the studio owner wants to see scheduling working before bookings exist. Goals are written behaviourally; a capability phase closes only when its sentence is true.

| Phase | Goal | Parallel-safe | Rationale |
|---|---|---|---|
| P0 | Prerequisites (provisioning) | Yes | Human tasks; nobody edits code |
| P1 | Foundations: scaffold, config, CI skeleton, auth wiring, error envelope + shared DTOs + the endpoint-module seam | **No** | Every task touches the solution root. Scoped to what P2 needs — pagination generalization is deferred to P3, which is the first phase to list anything |
| P2 | **A studio admin can publish a workshop, add sessions to it, and see them listed; nobody else can.** Migrations 001–002, then the Scheduling resources | **No** | T10 depends on T3 — schema before the module that maps it |
| P3 | **A member can book a session, see it under their bookings, cancel it, and be refused when the session is full.** Migration 003 + capacity constraint, then the Bookings resources | **No** | T11 depends on T4, same reason |
| P4 | Close-out: OpenAPI asset, the confirmation email deferred out of P3, telemetry, constraint review | **No** | T12 follows T10 and T11; T13 ∥ T14 ∥ T15 are pairwise safe (disjoint file sets). The streams carry the pairwise answer |

**Deferred on purpose:** booking confirmation email (T13) is part of the booking *experience* but not of the booking *capability* — a booking that works without an email is usable, and T13 is blocked on provisioning (T0.2) that P3 must not wait for. It is named here, in P4, rather than left implied.

## 2. Streams

| Stream | Owns | Why it is internally sequential |
|---|---|---|
| `foundation` | The solution root and everything shared: scaffold, config, CI, auth wiring, error middleware, the endpoint-module seam, the OpenAPI asset, telemetry base | Every task edits the solution root or `src/Api/Program.cs`. T0.1 sits here too — the Auth0 tenant is what T5 wires, so the provisioning belongs to the lane that consumes it |
| `schema` | Migrations and the data-integrity work that follows from them | Migrations are ordered by definition, and T15's guard review reads the constraint T3 creates |
| `scheduling` | Workshops + Sessions — `src/Scheduling/*` | One module, one file set |
| `booking` | Bookings and the confirmation email — `src/Booking/*`, `src/Notifications/*` | T13 sends on the event T11 raises, so it cannot start until T11 exists; T0.2 provisions the sender it uses |

Lanes idle at phase barriers by design: `booking` finishes T0.2 in minutes and then waits for the whole of P1–P2, because `foundation` is building the surfaces T11 is written against and `scheduling` is delivering the capability that ships first.

## 3. Progress

Shown mid-execution, as an executing agent maintains it — P1 and P2 done, P3 in flight:

| # | Task | Phase | Stream | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | T0.1 | P0 | `foundation` | Auth0 tenant + per-env applications | `human` | — | Done | tenant `workshop-dev`, apps created 2026-08-03 |
| 2 | T0.2 | P0 | `booking` | SendGrid account + domain auth | `human` | — | Blocked | domain auth pending — studio owner |
| 3 | T1 | P1 | `foundation` | Scaffold solution + module layout | `be-dotnet` | — | Done | `WorkshopBooking.sln:1`; `dotnet build` clean |
| 4 | T2 | P1 | `foundation` | Config + startup validation, CI skeleton | `be-dotnet` | T1 | Done | `src/Api/Configuration/AppOptions.cs:1-42` |
| 5 | T5 | P1 | `foundation` | Auth wiring (JWT bearer, two permissions) | `be-dotnet` | T2, T0.1 | Done | `src/Api/Program.cs:18-40` |
| 6 | T9 | P1 | `foundation` | Error middleware + shared DTOs + endpoint-module convention | `be-dotnet` | T2 | Done | `src/Shared/ProblemDetailsMiddleware.cs:1-76` |
| 7 | T3 | P2 | `schema` | Migrations 001–002 (workshops, sessions) + seeds | `be-dotnet` | T2 | Done | `src/Api/Migrations/002_Sessions.cs:1`; head `002` applied |
| 8 | T10 | P2 | `scheduling` | Workshops + Sessions resources | `be-dotnet` | T3, T5, T9 | Done | `src/Scheduling/SessionEndpoints.cs:1-140`; 24 tests green |
| 9 | T4 | P3 | `schema` | Migration 003 (bookings) + capacity constraint | `be-dotnet` | T3 | Done | `src/Api/Migrations/003_Bookings.cs:1-58`; head `003` applied |
| 10 | T11 | P3 | `booking` | Bookings resource | `be-dotnet` | T4, T5, T9 | Partial | book + my-bookings in `src/Booking/BookingEndpoints.cs:1-88`; cancel + attend not written |
| 11 | T12 | P4 | `foundation` | Generate + commit the OpenAPI asset | `be-dotnet` | T10, T11 | Not started | — |
| 12 | T13 | P4 | `booking` | Email sender (SendGrid + Mailpit lane) | `be-dotnet` | T9, T11 | Blocked | T0.2 |
| 13 | T14 | P4 | `foundation` | Telemetry base | `observability-engineer-dotnet` | T10, T11 | Not started | — |
| 14 | T15 | P4 | `schema` | Overbooking guard depth review | `data-architect` | T4 | Not started | — |

Status vocabulary: Not started · In progress · Done · Partial · Diverged · Blocked. A `Done`/`Partial` with an empty Evidence cell is a plan defect.

Note T5 and T9 sharing `foundation`: both modify `src/Api/Program.cs`, so they may not be separate lanes however independent they read. T12 is in `foundation` for the same reason and runs alone in that lane during P4 — its `dependsOn` holds it behind T10 and T11 without a lane needing to say so.

P2's goal sentence held on 2026-08-06: an admin token published a workshop, added two sessions, and listed them; a member token got 403. That check is what closed the phase — not the two ticked rows.

## 4. Tasks

*A real artifact writes every block; this example shows three.*

### T9 — Error middleware + shared DTOs + endpoint-module convention (P1)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
**Stream:** `foundation` · **Order:** 6
**Depends on:** T2
**Files:**
- Create: `src/Shared/ProblemDetailsMiddleware.cs`, `src/Shared/PagedResult.cs`, `src/Shared/SessionSummary.cs`
- Create: `src/Shared/IEndpointModule.cs` (each module self-registers its routes — this is what makes T10 ∥ T11 parallel-safe)
- Modify: `src/Api/Program.cs`

**Intent:** the RFC 9457 error envelope per `api-surface.md` §1/§4 (stable `type` slugs, `traceId` from `traceparent`, all field errors at once), the shared schemas from §3, and the module registration seam.

**Acceptance criteria:**
- [ ] Every failure returns `application/problem+json` with the documented shape; no bare strings, no stack traces
- [ ] Unknown request fields are rejected with 400 per §4's stated choice
- [ ] `PagedResult<T>` and `SessionSummary` match `api-surface.md` §3 field-for-field
- [ ] `dotnet build` clean, 0 warnings; `dotnet test` green

**Out of scope:** any endpoint (T10/T11), auth (T5).

### T11 — Bookings resource (P3)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
**Stream:** `booking` · **Order:** 10
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

**Out of scope:** the concurrency race test (QA pass, `qa-api-dotnet`), email on booking (T13).

### T12 — Generate + commit the OpenAPI asset (P4)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
**Stream:** `foundation` · **Order:** 11
**Depends on:** T10, T11
**Files:**
- Create: `docs/api/booking-api-openapi-2026-08-02.json` (canonicalized: `jq -S`, 2-space)
- Modify: `src/Api/Program.cs` (OpenAPI generation wiring, if not already on)

**Intent:** emit the implemented surface as the committed OpenAPI asset so `qa/_shared/api-spec-assets` has its canonical input from day one — `qa-api-dotnet` ingests *this file*, and every later contract change flows through that skill's diff-driven lane instead of being reverse-engineered.

**Acceptance criteria:**
- [ ] The generated spec matches `api-surface.md`'s endpoint map: every path, method, and documented status per endpoint
- [ ] Committed under the `{service}-openapi-YYYY-MM-DD.json` naming `api-spec-assets` expects, canonicalized
- [ ] A drift between the spec and `api-surface.md` is reported, not silently reconciled — the plan may be stale (reconcile rules apply)

**Out of scope:** writing any test from the spec (`qa-api-dotnet`), maintaining the asset thereafter (`qa/_shared/api-spec-assets`).

### T0.1–T15, remaining — abbreviated in this example
Each gets the same block shape. Notable: T0.x are human prerequisite tasks from `integrations.md` §5 (the three-places rule) — `Agent: human`, each block carrying an `**Owner:**` line (T0.1: the studio owner's Auth0 admin; T0.2: the studio owner), exempt from catalog-name resolution per the skill's rules; T15 executes `data-model.md` §9's routed decision.

## 5. Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| — | none — all settled at blueprint approval | | | |

## 6. Deliberately not planned

Contract/integration tests (`qa-api-dotnet`), the access-control proof (`qa-security`), pipeline beyond the CI skeleton (`devops-engineer`), both SPAs (`fe-react`).

## 7. Execution log

<!-- append-only, oldest first: one row per status change. Never edited, never deleted -->

| When | Task | Status | By | Note |
|---|---|---|---|---|
| 2026-08-03 | T0.1 | Done | Studio owner | Auth0 tenant `workshop-dev` + dev/prod apps |
| 2026-08-04 | T1, T2 | Done | `be-dotnet` | Scaffold + config; CI skeleton runs build+test |
| 2026-08-04 | T0.2 | Blocked | Studio owner | SendGrid domain authentication pending |
| 2026-08-05 | T5, T9 | Done | `be-dotnet` | Auth wiring + error envelope; P1 closed |
| 2026-08-06 | T3 | Done | `be-dotnet` | Migrations 001–002 applied, seeds loaded |
| 2026-08-06 | T10 | Done | `be-dotnet` | Both resources in one endpoint file — see D1 |
| 2026-08-06 | P2 | Closed | `be-dotnet` | Goal verified by hand: admin publishes + lists, member gets 403 |
| 2026-08-08 | T4 | Done | `be-dotnet` | Migration 003 + `sessions_capacity` exclusion constraint |
| 2026-08-09 | T11 | In progress | `be-dotnet` | book + my-bookings done |
| 2026-08-09 | T11 | Partial | `be-dotnet` | Session ended; cancel + attend remain |

## 8. Decisions & deviations

| # | Task | Plan said | What was decided/built | Why | When |
|---|---|---|---|---|---|
| D1 | T10 | Separate `WorkshopEndpoints.cs` + `SessionEndpoints.cs` | One `SessionEndpoints.cs` carrying both resources (`src/Scheduling/SessionEndpoints.cs:1-140`) | One aggregate; a second file bought nothing. Escalated as `Diverged`, human accepted, plan amended | 2026-08-06 |
| D2 | T13 | Email sent inside the booking slice | Deferred to P4 as its own task | Booking is usable without it and T0.2 is blocked; P3 must not wait on provisioning | 2026-08-02 |

## For Mission Control

Paste this document into the plan box and point the run at `~/src/workshop-booking`.
The task graph maps 1:1 — the four streams in §2 become MC's lanes, each task keeps
its `stream` and `order` alongside its `agent`, `skills`, `files` and `dependsOn`,
phases stay hard barriers, and the open questions above carry their options.
MC's planner re-reads the target repo, so it may split a task it finds too large;
that is expected and does not invalidate the sequence — the new pieces belong in
the split task's own lane.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
| — | none | | |
