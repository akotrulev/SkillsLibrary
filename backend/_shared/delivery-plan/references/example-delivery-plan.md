# Golden example — `delivery-plan.md`

The filled example for `be-shared-delivery-plan`, from the **workshop-booking** toy initiative shared by all five planner examples. **Shapes and disciplines are normative; domain content is illustrative.** A real artifact writes a full block for *every* task — this example writes three representative ones (a foundation task, a feature slice, the OpenAPI-asset task) and abbreviates the rest, saying so. The paired `HANDOFF.md` example lives in `handoff-template.md`, already filled.

---

# Workshop Booking — Delivery Plan

**Date:** 2026-08-02 · **Written by:** `be-shared-delivery-plan`
**Pack:** `./blueprint.md` · `./data-model.md` · `./api-surface.md` · `./integrations.md`
**Target repo:** `~/src/workshop-booking` · **Stack:** .NET 10 + PostgreSQL 18 · **Build/test:** `dotnet build` / `dotnet test` (greenfield — becomes the project's own once scaffolded)

> **For agentic workers:** each task names the agent that should execute it and the skills to load.
> Run them with `ep-executing-plans` inline, or hand the whole document to Mission Control.
> Steps use checkbox syntax; `HANDOFF.md` carries live state between sessions.

## 1. Phases

| Phase | Goal | Parallel-safe | Rationale |
|---|---|---|---|
| P0 | Prerequisites (provisioning) | Yes | Human tasks; nobody edits code |
| P1 | Foundations (scaffold, config, CI skeleton) | **No** | Every task touches the solution root |
| P2 | Schema (migrations 001–003) | **No** | Migrations are ordered by definition |
| P3 | Cross-cutting (auth wiring, error middleware, shared DTOs) | **No** | Shared surfaces every P4 task depends on |
| P4 | Feature slices (workshops+sessions, bookings) + the OpenAPI asset | **Partly** — T10 ∥ T11 (T10 touches `src/Scheduling/*`, T11 touches `src/Booking/*`, no shared file; both register routes via per-module `IEndpointModule` self-registration created in T9, so no shared route table is edited). T12 follows both | |
| P5 | Integrations (email sender) | Yes | One file set, one task |
| P6 | Hardening (telemetry, race test support, docs) | Mixed | Called per task |

## 2. Streams

| Stream | Owns | Why it is internally sequential |
|---|---|---|
| `foundation` | The solution root and everything shared: scaffold, config, CI, auth wiring, error middleware, the endpoint-module seam, the OpenAPI asset, telemetry base | Every task edits the solution root or `src/Api/Program.cs`. T0.1 sits here too — the Auth0 tenant is what T5 wires, so the provisioning belongs to the lane that consumes it |
| `schema` | Migrations and the data-integrity work that follows from them | Migrations are ordered by definition, and T15's guard review reads the constraint T3 creates |
| `scheduling` | Workshops + Sessions — `src/Scheduling/*` | One module, one file set |
| `booking` | Bookings and the confirmation email — `src/Booking/*`, `src/Notifications/*` | T13 sends on the event T11 raises, so it cannot start until T11 exists; T0.2 provisions the sender it uses |

Lanes idle at phase barriers by design: `booking` finishes T0.2 in minutes and then waits for the whole of P1–P3, because `foundation` is building the surfaces T11 is written against.

## 3. Progress

| # | Task | Phase | Stream | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | T0.1 | P0 | `foundation` | Auth0 tenant + per-env applications | *(human — owner)* | — | Not started | — |
| 2 | T0.2 | P0 | `booking` | SendGrid account + domain auth | *(human — owner)* | — | Not started | — |
| 3 | T1 | P1 | `foundation` | Scaffold solution + module layout | `be-dotnet` | — | Not started | — |
| 4 | T2 | P1 | `foundation` | Config + startup validation, CI skeleton | `be-dotnet` | T1 | Not started | — |
| 5 | T3 | P2 | `schema` | Migrations 001–003 + seeds | `be-dotnet` | T2 | Not started | — |
| 6 | T5 | P3 | `foundation` | Auth wiring (JWT bearer, two permissions) | `be-dotnet` | T2, T0.1 | Not started | — |
| 7 | T9 | P3 | `foundation` | Error middleware + shared DTOs + endpoint-module convention | `be-dotnet` | T2 | Not started | — |
| 8 | T10 | P4 | `scheduling` | Workshops + Sessions resources | `be-dotnet` | T3, T5, T9 | Not started | — |
| 9 | T11 | P4 | `booking` | Bookings resource | `be-dotnet` | T3, T5, T9 | Not started | — |
| 10 | T12 | P4 | `foundation` | Generate + commit the OpenAPI asset | `be-dotnet` | T10, T11 | Not started | — |
| 11 | T13 | P5 | `booking` | Email sender (SendGrid + Mailpit lane) | `be-dotnet` | T9, T11 | Not started | — |
| 12 | T14 | P6 | `foundation` | Telemetry base | `observability-engineer-dotnet` | T10, T11 | Not started | — |
| 13 | T15 | P6 | `schema` | Overbooking guard depth review | `data-architect` | T3 | Not started | — |

Status vocabulary: Not started · In progress · Done · Partial · Diverged · Blocked. A `Done`/`Partial` with an empty Evidence cell is a plan defect.

Note T5 and T9 sharing `foundation`: both modify `src/Api/Program.cs`, so they may not be separate lanes however independent they read. T12 is in `foundation` for the same reason and runs alone in that lane during P4 — its `dependsOn` holds it behind T10 and T11 without a lane needing to say so.

## 4. Tasks

*A real artifact writes every block; this example shows three.*

### T9 — Error middleware + shared DTOs + endpoint-module convention (P3)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
**Stream:** `foundation` · **Order:** 7
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

### T11 — Bookings resource (P4)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
**Stream:** `booking` · **Order:** 9
**Depends on:** T3, T5, T9
**Files:**
- Create: `src/Booking/Domain/Booking.cs`, `src/Booking/BookingService.cs`, `src/Booking/BookingEndpoints.cs`, `src/Booking/BookingConfiguration.cs`
- Create: `tests/Booking.Tests/BookingServiceTests.cs`

**Intent:** the four booking endpoints in `api-surface.md` §2/§5 (book, my-bookings, cancel, attend), with the DB-level capacity guard from `data-model.md` §3 and the cancellation decision table from `blueprint.md` §3b.

**Acceptance criteria:**
- [ ] All four endpoints match `api-surface.md` exactly: paths, fields, status codes
- [ ] The three documented deltas return their slugs: `session-full`, `already-booked`, `invalid-state`
- [ ] The capacity check is the DB-level guard — no app-side count-then-insert
- [ ] `lateCancel` is computed server-side per the blueprint decision table (R1–R3), covered by unit tests per rule
- [ ] Every undrawn state transition returns 409 naming current and allowed states
- [ ] `dotnet build` clean; `dotnet test` green

**Out of scope:** the concurrency race test (QA pass, `qa-api-dotnet`), email on booking (T13).

### T12 — Generate + commit the OpenAPI asset (P4)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
**Stream:** `foundation` · **Order:** 10
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
Each gets the same block shape. Notable: T0.x are human prerequisite tasks from `integrations.md` §5 (the three-places rule); T15 executes `data-model.md` §9's routed decision.

## 5. Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| — | none — all settled at blueprint approval | | | |

## 6. Deliberately not planned

Contract/integration tests (`qa-api-dotnet`), the access-control proof (`qa-security`), pipeline beyond the CI skeleton (`devops-engineer`), both SPAs (`fe-react`).

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
