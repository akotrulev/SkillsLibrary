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

## 2. Progress

| Task | Phase | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|
| T0.1 | P0 | Auth0 tenant + per-env applications | *(human — owner)* | — | Not started | — |
| T0.2 | P0 | SendGrid account + domain auth | *(human — owner)* | — | Not started | — |
| T1 | P1 | Scaffold solution + module layout | `be-dotnet` | — | Not started | — |
| T2 | P1 | Config + startup validation, CI skeleton | `be-dotnet` | T1 | Not started | — |
| T3 | P2 | Migrations 001–003 + seeds | `be-dotnet` | T2 | Not started | — |
| T5 | P3 | Auth wiring (JWT bearer, two permissions) | `be-dotnet` | T2, T0.1 | Not started | — |
| T9 | P3 | Error middleware + shared DTOs + endpoint-module convention | `be-dotnet` | T2 | Not started | — |
| T10 | P4 | Workshops + Sessions resources | `be-dotnet` | T3, T5, T9 | Not started | — |
| T11 | P4 | Bookings resource | `be-dotnet` | T3, T5, T9 | Not started | — |
| T12 | P4 | Generate + commit the OpenAPI asset | `be-dotnet` | T10, T11 | Not started | — |
| T13 | P5 | Email sender (SendGrid + Mailpit lane) | `be-dotnet` | T9, T11 | Not started | — |
| T14 | P6 | Telemetry base | `observability-engineer-dotnet` | T10, T11 | Not started | — |
| T15 | P6 | Overbooking guard depth review | `data-architect` | T3 | Not started | — |

Status vocabulary: Not started · In progress · Done · Partial · Diverged · Blocked. A `Done`/`Partial` with an empty Evidence cell is a plan defect.

## 3. Tasks

*A real artifact writes every block; this example shows three.*

### T9 — Error middleware + shared DTOs + endpoint-module convention (P3)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-unit-testing`
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

## 4. Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| — | none — all settled at blueprint approval | | | |

## 5. Deliberately not planned

Contract/integration tests (`qa-api-dotnet`), the access-control proof (`qa-security`), pipeline beyond the CI skeleton (`devops-engineer`), both SPAs (`fe-react`).

## For Mission Control

Paste this document into the plan box and point the run at `~/src/workshop-booking`.
The task graph maps 1:1 — phases keep their `parallelSafe` calls, tasks keep their
`agent`, `skills`, `files`, and `dependsOn`, and the open questions above carry
their options. MC's planner re-reads the target repo, so it may split a task it
finds too large; that is expected and does not invalidate the sequence.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
| — | none | | |
