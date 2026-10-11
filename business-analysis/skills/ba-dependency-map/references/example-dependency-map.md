# Golden example — the dependency map

The filled example for `business-analysis:dependency-map`: the three files as a `be-documenter` run would write them into `docs/business-model/`, plus the two artifacts they join to (the ENT-003 grid and DEC-003). The system is the **workshop-booking** toy of `backend/_shared/business-documentation/references/example-area.md`, imagined as an inherited codebase: AREA-002 Scheduling, AREA-003 Bookings, AREA-004 Session credits & charges. **Shape and the ids are normative; domain content and citations are illustrative.**

What it demonstrates: one trigger, "a member cancels a booking" (EVT-002), reaches three features through EVT-006; a second path into the same event (staff cancel, session cancel) means the credit reaction cannot assume a member cancelled; and the `?` and `no` cells are the findings, each with the concrete sequence that breaks it.

---

## `events.md`

# Events & reactions

**Created:** 2026-08-02
**Owned by:** `business-analysis:dependency-map`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02

### Triggers

| ID | Trigger | Kind | Fired by | Owner | Source |
|---|---|---|---|---|---|
| EVT-001 | Member books a seat | command | Member | AREA-003 Bookings | `BookingEndpoints.cs:34` `#observed` |
| EVT-002 | Member cancels a booking | command | Member | AREA-003 Bookings | `BookingEndpoints.cs:58` `#observed` |
| EVT-003 | Staff cancels a booking | command | Staff | AREA-003 Bookings | `BookingEndpoints.cs:77` `#observed` |
| EVT-004 | Staff cancels a session | command | Staff | AREA-002 Scheduling | `SessionEndpoints.cs:49` `#observed` |
| EVT-005 | Booking confirmed | event | RX-001 | AREA-003 Bookings | `BookingConfirmed.cs:6` `#observed` |
| EVT-006 | Booking cancelled (by member/staff, hours of notice) | event | RX-002, RX-003, RX-005 | AREA-003 Bookings | `BookingCancelled.cs:8` `#observed` |
| EVT-007 | Monthly posting | schedule | 1st of the month 00:00, timezone `?` | AREA-004 Credits & charges | `OverageChargeJob.cs:12` `#observed` · [TBD - timezone not configured anywhere] |

### Reactions

| ID | When | Guard | Owner | Effects | Emits | Mode | On failure | Source |
|---|---|---|---|---|---|---|---|---|
| RX-001 | EVT-001 | seats taken < capacity | AREA-003 | ENT-002 — → Confirmed; Session.seats_taken +1 | EVT-005 | in request | rolls back ("session full") | `BookingService.cs:41-63` `#observed` |
| RX-002 | EVT-002 | session not started | AREA-003 | ENT-002 Confirmed → Cancelled; Session.seats_taken −1 | EVT-006 | in request | rolls back | `BookingService.cs:88-104` `#observed` |
| RX-003 | EVT-003 | — | AREA-003 | ENT-002 Confirmed → Cancelled (by staff); Session.seats_taken −1 | EVT-006 | in request | rolls back | `BookingService.cs:112-127` `#observed` |
| RX-004 | EVT-005 | — | AREA-004 | DEC-002; Member.credits_used +spent; creates Accrued charge (ENT-003 — → Accrued) when short | — | after commit, at-least-once | retried 3× then dead-letter — the booking stays confirmed and unpriced | `CreditPricingService.cs:31-61` `#observed` · retry count `Outbox.cs:22` `#observed` |
| RX-005 | EVT-004 | — | AREA-002 | ENT-001 Scheduled → Cancelled; each Confirmed booking ENT-002 Confirmed → Cancelled (by staff) | EVT-006 per booking | in request | rolls back | `SessionService.cs:70-96` `#observed` |
| RX-006 | EVT-006 | — | AREA-004 | DEC-003; Member.credits_used −returned; ENT-003 Accrued → Removed | — | after commit, at-least-once | ? | `BookingCancelledHandler.cs:19-33` `#observed` · [TBD - no failure path found] |
| RX-007 | EVT-007 | every member | AREA-004 | ENT-003 Accrued → Posted; creates Charge; Member.credits_used := 0 | — | scheduled | ? (a re-run's behaviour is unknown) | `OverageChargeJob.cs:40-58` `#observed` · [TBD - no run marker found] |

---

## `shared-data.md`

# Shared data

**Created:** 2026-08-02
**Owned by:** `business-analysis:dependency-map`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02

### CRUD matrix — entities touched by two or more features

| Entity | Create | Read | Update | Delete | Completeness |
|---|---|---|---|---|---|
| Booking (ENT-002) | RX-001 | RX-001 (capacity), RX-004, RX-005, RX-006 | RX-002, RX-003, RX-005 | none | by decision (cancelled is a state — `BookingService.cs:88`) |
| Accrued charge (ENT-003) | RX-004 | RX-007, screen: my balance | RX-006 (removed), RX-007 (posted) | none | by decision (removed is a state — `ENT-003`) |

### Shared fields

| Field | Written by | Read by | Note |
|---|---|---|---|
| Member.credits_used | RX-004 (+), RX-006 (−), RX-007 (:= 0) | DEC-002 in RX-004, screen: my balance | three writers in two features; see INV-002 |
| Session.seats_taken | RX-001 (+1), RX-002 / RX-003 (−1) | RX-001 guard | see INV-001 |

---

## `invariants.md`

# Invariants

**Created:** 2026-08-02
**Owned by:** `business-analysis:dependency-map`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02

| ID | Invariant | Fields | Threatened by | Enforced | Source |
|---|---|---|---|---|---|
| INV-001 | Seats taken never exceed capacity | Session.seats_taken | RX-001 | RX-001: yes (conditional update) | `BookingService.cs:52` `#observed` |
| INV-002 | Credits used is never negative | Member.credits_used | RX-006, RX-007 | RX-006: **no** — a booking priced last month and cancelled after RX-007's reset drives it below 0 | `BookingCancelledHandler.cs:30`; no floor (search: `Math.Max`, `NonNegative` under `src/Credits/`) `#observed` |
| INV-003 | An accrual is charged at most once, and never after its booking was refunded | ENT-003 | RX-006, RX-007 | RX-006: **?** (Posted × EVT-006) · RX-007: **?** (re-run) | `OverageChargeJob.cs:44`, `BookingCancelledHandler.cs:33` `#inferred` · [TBD - confirm intended behaviour of a refund after posting] |
| INV-004 | A booking's credits are spent exactly once and returned at most once | Member.credits_used, ENT-003 | RX-004, RX-006 | **?** — both are at-least-once, and no idempotency key was found | `Outbox.cs:22`; no key (search: `IdempotencyKey`, `Processed` under `src/`) `#observed` |

---

## Joined artifacts

### `entities/accrued-charge.md` — transition grid (ENT-003)

Columns are trigger ids from `events.md`. Cell = target state `(owning feature id)` · `—` = illegal by decision · `?` = unspecified (finding).

| State \ Trigger | EVT-005 (via RX-004) | EVT-006 | EVT-007 |
|---|---|---|---|
| (none) | Accrued (AREA-004), when short | — | — |
| Accrued | — | Removed (AREA-004), when DEC-003 returns | Posted (AREA-004) |
| Posted | — | **?** | — |
| Removed | — | — | — |

The `Posted × EVT-006` cell is the grid's side of INV-003: a member cancels free of charge after the month was posted, and the grid has no answer.

### `decisions/credit-return.md` — DEC-003, credit return on cancellation (hit policy U)

| Rule | Cancelled by | Notice | Credits returned and the booking's accrual removed |
|---|---|---|---|
| R1 | member | ≥ 24 h | yes |
| R2 | member | < 24 h | no |
| R3 | staff | − | yes |

Source: `BookingCancelledHandler.cs:19-33` `#observed` · contributed by AREA-004 Session credits & charges.

### What the findings look like

Handed to `business-analysis:conflict-check`, each with its boundary condition:

| Severity | Kind | Pair | Finding (+ boundary condition) |
|---|---|---|---|
| blocker | conflict | AREA-003 Bookings × AREA-004 Credits (INV-002) | a booking priced on 28 Feb and cancelled on 3 Mar, after the 1 Mar reset, returns 2 credits to a balance of 0 and leaves it at −2 |
| major | conflict | AREA-004 posting × AREA-004 refund (INV-003) | an accrual is posted on 1 Apr 00:00 and its booking is cancelled free of charge at 00:05: the accrual is `Posted`, the grid cell is `?` |
| major | gap | AREA-004 RX-004 / RX-006 (INV-004) | `EVT-006` is delivered twice for one booking: the credits are returned twice |
| minor | ambiguity | AREA-004 RX-007 | the posting runs at 00:00 in an unrecorded timezone; a member in another zone sees the month roll over at a different hour |
