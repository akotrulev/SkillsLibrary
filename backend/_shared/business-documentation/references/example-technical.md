# Golden example, Level 3 — `areas/<area>.technical.md`

The Level 3 example for `dev:doc-business-model`: the same **Session credits & charges** area as [example-area.md](example-area.md) (Level 1) and [example-behind-the-scenes.md](example-behind-the-scenes.md) (Level 2), written for developers and AI agents. Every code name, path, status code and tier tag the other two levels keep out is here. **Shape, heading names, local ids and the evidence index are normative; domain content, paths and line numbers are illustrative.**

Note what the example demonstrates: tables over prose; one fact per row with its evidence on the same row; local ids (`EP1`, `R4`, `DB2`…) the evidence index and other agents can cite; Mermaid for the state machine and the multi-participant flow; the same plain part names as Level 2 mapped to class names; a section with nothing to report (*Configuration*, *Telemetry*) stating the search that found nothing; a Finding carrying its boundary condition — the only place in the set where behaviour is called a defect; and an evidence index whose Section cells cite `Flow · step N` for every flow of Levels 1 and 2.

---

# Session credits & charges — Technical reference

**Created:** 2026-08-02
**Owned by:** `dev:doc-business-model`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02
**Audience:** internal
**Levels:** [Guide](credits-and-charges.md) · [Behind the scenes](credits-and-charges.behind-the-scenes.md) · [Technical reference](credits-and-charges.technical.md)
**Commit:** `a3f9c21` · **Stack:** .NET 8, ASP.NET Core minimal APIs, EF Core 8, PostgreSQL, in-process outbox · **Depth:** full · **Traced:** 2026-08-02

## How to read this

- Tiers: `#observed` = code read this session at the cited `path:line`; `#inferred` = intent, always tied to an open question (`Q` in Levels 1–2, `T` here). Never `#confirmed`.
- Paths are repo-relative; `a-b` after a colon is a line range. Citations are valid only at the commit above.
- Local ids: `EP` entry point · `R` rule · `DB` data · `EV` event/reaction · `INT` integration · `CFG` configuration · `F` finding.
- Models: [FLOW-004] · [ENT-003] · [DEC-002]. Dependency map: EVT-004–006, RX-004–007, INV-004.

## Quick facts

| Area id | Modules | Entry points | Entities | Events in / out | Integrations | Flags |
|---|---|---|---|---|---|---|
| AREA-004 | `src/Credits/` | 2 HTTP · 1 job · 2 consumers | `MembershipPlan`, `SessionTier`, `Member.CreditsUsed`, `AccruedOverage` | in: `BookingConfirmed`, `BookingCancelled` · out: none | none | none |

## Code map

| Concern | Path | Notes |
|---|---|---|
| Routing | `src/Credits/CreditEndpoints.cs`, `src/Credits/PlanAdminEndpoints.cs` | Minimal API route groups |
| Pricing and returns | `src/Credits/CreditPricingService.cs`, `src/Credits/BookingCancelledHandler.cs` | Plain-language name: *credits service* |
| Monthly posting | `src/Credits/OverageChargeJob.cs` | Plain-language name: *monthly billing job* |
| Domain | `src/Credits/MembershipPlan.cs`, `SessionTier.cs`, `AccruedOverage.cs` | |
| Validation | `src/Credits/MembershipPlanValidator.cs` | FluentValidation |
| Persistence | `src/Credits/Migrations/`, `migrations/007` | |
| Outbox | `src/Shared/Outbox.cs` | Shared with Bookings |

## Entry points

| Id | Trigger | Handler | Auth | Contract | Evidence |
|---|---|---|---|---|---|
| EP1 | `GET /members/me/credits` | `CreditEndpoints.cs:21` | policy `credits:own` | → `{creditsUsed, creditsRemaining, accruedOverage}` | `CreditEndpoints.cs:21` |
| EP2 | `PUT /plans/{id}` | `PlanAdminEndpoints.cs:17` | policy `workshops:manage` | `{name, monthlyCredits, overageRate}` → `204` | `PlanAdminEndpoints.cs:17` |
| EP3 | consumer: `BookingConfirmed` | `CreditPricingService.cs:31` | internal | event `BookingConfirmed.cs:6` | `CreditPricingService.cs:31` |
| EP4 | consumer: `BookingCancelled` | `BookingCancelledHandler.cs:19` | internal | event `BookingCancelled.cs:8` | `BookingCancelledHandler.cs:19-33` |
| EP5 | job: cron `0 0 1 * *` | `OverageChargeJob.cs:12` | internal | — | `OverageChargeJob.cs:12` |

## Rules, validations and decisions

| Id | Rule | Condition | Effect | Evidence | Tier |
|---|---|---|---|---|---|
| R1 | Credit cost | always | `cost = SessionTier.CreditsPerSeat`, copied onto the booking | `CreditPricingService.cs:31` | `#observed` |
| R2 | Spend or overage | `cost <= plan.MonthlyCredits - member.CreditsUsed` | spend `cost`, no overage; else spend remainder, `overage = (cost - remaining) * rate` | `CreditPricingService.cs:31-61`, [DEC-002] | `#observed` |
| R3 | Rate precedence | `member.OverageRateOverride != null` | member rate, else `plan.OverageRate` | `CreditPricingService.cs:48` | `#observed` |
| R4 | Never refuse | credits exhausted | no refusal branch | `CreditPricingService.cs:55` | `#observed` |
| R5 | Return on cancel | `hoursBeforeStart >= 24` or `cancelledBy == Staff` | return booking's credits, delete its `AccruedOverage` | `BookingCancelledHandler.cs:19-33` | `#observed` |
| R6 | Late forfeit | member cancels `< 24 h` before start | nothing returned, accrual kept; no fee path | `BookingCancelledHandler.cs:27` | `#observed` |
| R7 | Monthly post | unposted accruals sum `> 0` | one ledger charge, accruals marked posted | `OverageChargeJob.cs:40-58`, `:44` | `#observed` |
| R8 | Monthly reset | every member, every run | `CreditsUsed = 0`; no roll-over | `OverageChargeJob.cs:58` | `#observed` |
| R9 | Plan validation | save plan | `MonthlyCredits >= 0` integer; rates `>= 0` | `MembershipPlanValidator.cs:15-19` | `#observed` |
| R10 | Constants | — | cut-off 24 h at `BookingCancelledHandler.cs:19`; posting time at `OverageChargeJob.cs:12`; fixed in code, Q1, Q3 | as cited | `#observed` |

## Data

| Id | Entity / table | Reads | Writes | Also written by | Constraints / migration |
|---|---|---|---|---|---|
| DB1 | `MembershipPlan` / `membership_plans` | pricing, EP1 | EP2 | — | unique `name`, `migrations/007:22` |
| DB2 | `Member.CreditsUsed` | R2, EP1 | R2, R5, R8 | no other writer (search: `CreditsUsed` under `src/`) | none |
| DB3 | `AccruedOverage` | R7, EP1 | R2 (add), R5 (delete), R7 (mark posted) | — | FK to `Booking`, `migrations/009` |
| DB4 | `Booking.CreditCost` | R5 | R1 | — | copied at pricing time, `CreditPricingService.cs:31` |

```mermaid
stateDiagram-v2
  [*] --> Accrued: R2 shortfall
  Accrued --> Removed: R5 early or staff cancel
  Accrued --> Posted: R7 monthly job
  Posted --> [*]
```

Refused: `Posted → Removed` (a posted accrual is never reversed; no code path), `Removed → Posted`. `[ENT-003]`

## Control flow

```mermaid
sequenceDiagram
  participant B as BookingService
  participant O as Outbox
  participant P as CreditPricingService
  participant M as Member / AccruedOverage
  B->>B: save booking (transaction)
  B->>O: add BookingConfirmed (same transaction)
  O-->>P: deliver after commit (at-least-once)
  P->>M: R2: update CreditsUsed, add AccruedOverage
```

- **Transaction boundary:** booking save and outbox row commit together; pricing runs after commit (`Outbox.cs:22`).
- **Retries:** pricing consumer retried 3×, then parked; the cancellation handler has no failure path (`Outbox.cs:22`, `BookingCancelledHandler.cs:19-33`).
- **Idempotency:** none found (search: `IdempotencyKey`, `Processed` under `src/`); see **F1**.
- **Concurrency:** no lock or version column on `Member.CreditsUsed`; ordering between `BookingConfirmed` and `BookingCancelled` for one booking is `?` — **T1**.

## Events and reactions

| Id | Entry point | Kind | Reads | Writes | Also written by | Emits | Reacted to by | Mode | On failure | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| EV1 | `BookingService.Confirm` | command | `Booking`, `SessionTier` | `Booking.CreditCost` | — | `BookingConfirmed` (EVT-005) | `CreditPricingService.cs:31` (RX-004) | after commit, at-least-once | retried 3×, parked | `Outbox.cs:22` |
| EV2 | `BookingService.Cancel` | command | `Booking` | `Booking.Status` | — | `BookingCancelled` (EVT-006) | `BookingCancelledHandler.cs:19` (RX-006) | after commit, `?` | unhandled | `BookingCancelledHandler.cs:19-33` |
| EV3 | `SessionService.CancelSession` | command | `Booking` | `Booking.Status` | — | one `BookingCancelled` per booking (EVT-004 → RX-005 → EVT-006) | RX-006 | after commit, `?` | `?` | `SessionService.cs:70-96` |
| EV4 | `OverageChargeJob` | schedule | `AccruedOverage` | `AccruedOverage.Posted`, `Member.CreditsUsed`, ledger | — | none (search: `Publish`, `Emit`, `Outbox.Add` under `src/Credits/`) | — | scheduled | unhandled | `OverageChargeJob.cs:40-58` (RX-007) |

## Integrations

None. Search: `HttpClient`, `IHttpClientFactory`, `*Client` under `src/Credits/` — no match.

## Configuration

None. Search: `IOptions<`, `Configuration[`, `appsettings` keys `Credits:*` — no match; all values are constants (R10).

## Errors

| Condition | Status / problem type | Body | User-visible text | Evidence |
|---|---|---|---|---|
| Plan name not unique | `409` `plan-name-taken` | problem details | “That plan name is already taken.” | `migrations/007:22` → `PlanAdminEndpoints.cs:31` |
| Invalid plan values (R9) | `400` `validation-failed` | field errors | “Monthly credits must be 0 or more.” · “Overage rate must be 0 or more.” | `MembershipPlanValidator.cs:15-19` |
| `credits:own` missing | `403` | empty | — | `CreditEndpoints.cs:21` |

## Telemetry

None found. Search: `ActivitySource`, `Meter`, `ILogger` calls in `src/Credits/` — only a start-up log line at `OverageChargeJob.cs:9`; no span, metric or log at R2, R5, R7 — **F2**.

## Tests

| Test | Covers | Gaps |
|---|---|---|
| `tests/Credits/CreditPricingServiceTests.cs:18-90` | R1–R4 | boundary `cost == remaining`; override precedence |
| `tests/Credits/OverageChargeJobTests.cs:12-44` | R7 | partial failure; R8 |
| — | R5, R6 untested | late-cancel boundary at exactly 24 h |

## Business ↔ code vocabulary

| Business / Level 2 name | Code |
|---|---|
| Credits service | `CreditPricingService`, `BookingCancelledHandler` |
| Monthly billing job | `OverageChargeJob` |
| Booking service | `BookingService` (`src/Bookings/`) |
| Scheduling service | `SessionService` (`src/Scheduling/`) |
| Overage note | `AccruedOverage` |
| Plan (client term on the staff screen) | `MembershipPlan` |
| Session tier: Standard · Workshop · Masterclass | `SessionTier` enum display names |
| Credits used | `Member.CreditsUsed` |

## Changing this safely

| Item | Why | Evidence |
|---|---|---|
| Keep `CreditsUsed` single-writer | the monthly reset assumes no other writer | search: `CreditsUsed` under `src/` |
| Every cancellation path must emit `BookingCancelled` | it is the only trigger for returns | `BookingCancelledHandler.cs:19` |
| Copy the cost at pricing time | later tier changes must not re-price | `CreditPricingService.cs:31` |

## Findings

| # | Finding | Boundary condition | Evidence | Kind | Route to |
|---|---|---|---|---|---|
| F1 | No idempotency on pricing or returns | A redelivered `BookingConfirmed` for a 3-credit booking spends 6 credits and accrues the overage twice | `Outbox.cs:22`; no key (search above) | defect | `be-dotnet` / `code-auditor` |
| F2 | No telemetry at decision points | A mis-priced booking leaves nothing to trace in Grafana | search under *Telemetry* | gap | `be-dotnet` |
| F3 | Monthly job has no failure path or re-run | A crash after member 40 of 100 leaves 60 members unposted and unreset | `OverageChargeJob.cs:40-58` | defect | `be-dotnet` |

## Technical open questions

| # | Question |
|---|---|
| T1 | Is `BookingCancelled` guaranteed to follow `BookingConfirmed` for the same booking? Nothing in the outbox ordering shows it. |

## Evidence index

| Level | Section | Statement | Evidence | Tier |
|---|---|---|---|---|
| Guide | Overview | Overage accrues during the month, posted once at month start | see **R7**, **EV4** | `#observed` |
| Guide | Overview | Bookings are priced when made and never re-priced | `CreditPricingService.cs:31`; no re-pricing path (search: `Reprice`, `Recalculate` under `src/Credits/`) | `#observed` |
| Guide | Overview | Exists so members can book beyond their plan without being refused | comment at `CreditPricingService.cs:9`; Q1 | `#inferred` |
| Guide | Setup | Plan, tier, member override and precedence | see **DB1**, **R3**, `SessionTier.cs:11` | `#observed` |
| Guide | Setup | Validations and the messages staff see | see **R9**, **DB1**; text at `PlanAdminEndpoints.cs:31`, `MembershipPlanValidator.cs:15-19` | `#observed` |
| Guide | Setup | Cut-off, posting time, no roll-over fixed in code | see **R10**; Q1, Q3 | `#observed` |
| Guide | Setup | No *Scope* section — applies to every member | search: `Eligib`, `AppliesTo` under `src/Credits/` — none | `#observed` |
| Guide | Booking a seat · steps 1–2 | Credit cost from tier; credits remaining | see **R1**, **R2** | `#observed` |
| Guide | Booking a seat · steps 3–4 | Spend or overage; rate precedence | see **R2**, **R3** | `#observed` |
| Guide | Booking a seat · step 5 | Overage accrued, never refused | see **R2**, **R4** | `#observed` |
| Guide | Cancelling a booking · step 1 | Early or staff cancellation returns credits and removes the accrual | see **R5** | `#observed` |
| Guide | Cancelling a booking · step 2 | Late member cancellation returns nothing | see **R6**; Q4 | `#observed` |
| Guide | Cancelling a booking · step 1 | Returned credits never re-price an accrual | no reader of returned credits outside future pricing (search: `ReturnedCredits` under `src/`); Q2 | `#observed` |
| Guide | Monthly posting · steps 1–2 | One charge per member; zero sum posts nothing | see **R7** | `#observed` |
| Guide | Monthly posting · step 3 | Credits reset, no roll-over | see **R8** | `#observed` |
| Guide | How it connects | Starts from Bookings and Scheduling; sets off nothing; shares bookings read-only | see **EV1**, **EV2**, **EV3**, **EV4**, **DB2** | `#observed` |
| Guide | Who can do what | Member sees own balances; staff manage plans and always return credits | see **EP1**, **EP2**, **R5** | `#observed` |
| Behind the scenes | At a glance | Nothing here talks to an outside service | search under Integrations | `#observed` |
| Behind the scenes | Booking a seat · step 1 | Booking saved and confirmed before pricing | see **EV1** | `#observed` |
| Behind the scenes | Booking a seat · step 2 | How soon the credits service is told is not shown | no delay, poll interval or schedule visible at `Outbox.cs:22`; Q8 | `#observed` |
| Behind the scenes | Booking a seat · steps 3–4 | Cost copied onto the booking; overage note added | see **R1**, **R2**, **DB4** | `#observed` |
| Behind the scenes | Cancelling a booking · steps 1–2 | Cancellation saved, then the credits service is told who cancelled | see **EV2** | `#observed` |
| Behind the scenes | Cancelling a booking · step 3 | A repeated cancellation message returns the credits twice | see **F1** | `#observed` |
| Behind the scenes | Cancelling a booking · step 3 | Staff cancelling a session cancels each booking one by one | see **EV3** | `#observed` |
| Behind the scenes | Monthly posting · steps 1–3 | Runs at 00:00 on the 1st; one charge; reset for everyone | see **EP5**, **R7**, **R8** | `#observed` |
| Behind the scenes | Timing and ordering | A redelivered confirmation is priced again | see **F1** | `#observed` |
| Behind the scenes | Timing and ordering | Order of booking and cancellation not guaranteed | no ordering key or sequence number (search: `Sequence`, `OrderingKey`, `Version` in `src/Credits/` and `src/Shared/Outbox.cs`); **T1**, Q5 | `#observed` |
| Behind the scenes | Timing and ordering | Monthly reset and a booking at the same moment are not coordinated | no lock or version column (search: `RowVersion`, `Lock`, `ConcurrencyToken` under `src/Credits/`) | `#observed` |
| Behind the scenes | When parts fail or are slow | Pricing retried 3×; returns and monthly job have no failure path | see **EV1**, **EV2**, **EV4**, **F3** | `#observed` |
| Behind the scenes | Settings and switches | No configuration | search under Configuration | `#observed` |
