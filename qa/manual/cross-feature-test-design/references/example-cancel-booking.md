# Golden example — "a member cancels a booking"

The filled example for `cross-feature-test-design`: the slice for `EVT-002`, the basis's §8 as `requirements-breakdown` writes it, the coverage-item list, and the suite. The system is the **workshop-booking** toy of `backend/_shared/business-documentation/references/example-area.md` (Ana's month, AREA-004), and the connections are the map in `business-analysis/skills/ba-dependency-map/references/example-dependency-map.md`. **Shape and ids are normative; domain content is illustrative.** Facts: Basic plan = 8 credits, £6.00 per overage credit; tiers Standard 1, Workshop 2, Masterclass 3; cut-off 24 h; staff cancellations always return credits; posting on the 1st at 00:00; session capacity 6 in case 6 `#assumption`.

## Before — what the field-level pipeline produces

Input: `DELETE /bookings/{id}` plus the story. Seven cases: id missing, id malformed, id unknown, another member's booking, already cancelled, happy path, maybe one late cancellation. None looks at credits, the freed seat, a staff session cancellation or the monthly job, and every AC is "covered".

## 1. The slice for EVT-002

| # | Lookup | Result |
|---|---|---|
| 1 | Own | EVT-002 → RX-002 (AREA-003): guard session not started; ENT-002 Confirmed → Cancelled, Session.seats_taken −1; emits EVT-006; in request |
| 2 | Downstream | EVT-006 → RX-006 (AREA-004): DEC-003; Member.credits_used −returned; ENT-003 Accrued → Removed; after commit, at-least-once, failure `?` |
| 3 | Upstream | EVT-006 is also emitted by RX-003 (staff cancels a booking) and RX-005 (staff cancels a session, one per booking) |
| 4 | States | ENT-003 row Accrued (EVT-007 → Posted) and row Posted (EVT-006 = `?`); ENT-002 Cancelled, reachable by EVT-004 |
| 5 | Decisions | DEC-003 R1, R2, R3 |
| 6 | Shared data | Session.seats_taken (RX-001, RX-002, RX-003), Member.credits_used (RX-004, RX-006, RX-007), ENT-003 (RX-004, RX-006, RX-007, screen: my balance) |
| 7 | Invariants | INV-001 (RX-001), INV-002, INV-003, INV-004 |
| 8 | Interactions | four open findings, listed in §8 |

## 2. §8 as `requirements-breakdown` writes it

## 8. Connections
**Built from:** KB slice @ 2026-08-02 (`events.md`, `shared-data.md`, `invariants.md`, `entities/accrued-charge.md`, `decisions/credit-return.md`)

### Triggers and chains
| Trigger | Reaction (owner) | Effects | Emits → next | Mode | On failure | Source |
|---|---|---|---|---|---|---|
| EVT-002 | RX-002 (AREA-003) | ENT-002 Confirmed → Cancelled; Session.seats_taken −1 | EVT-006 → RX-006 | in request | rolls back | RX-002 |
| EVT-006 | RX-006 (AREA-004) | DEC-003; Member.credits_used −returned; ENT-003 Accrued → Removed | — | after commit, at-least-once | ? | RX-006 |
| EVT-003 | RX-003 (AREA-003) | ENT-002 Confirmed → Cancelled (by staff); Session.seats_taken −1 | EVT-006 → RX-006 | in request | rolls back | RX-003 |
| EVT-004 | RX-005 (AREA-002) | ENT-001 Scheduled → Cancelled; each Confirmed booking Confirmed → Cancelled (by staff) | EVT-006 per booking → RX-006 | in request | rolls back | RX-005 |
| EVT-005 | RX-004 (AREA-004) | DEC-002; Member.credits_used +spent; creates Accrued charge when short | — | after commit, at-least-once | retried 3× then dead-letter | RX-004 |
| EVT-007 | RX-007 (AREA-004) | ENT-003 Accrued → Posted; creates Charge; Member.credits_used := 0 | — | scheduled, 1st 00:00, timezone `?` | ? | RX-007 |

### States this feature relies on
| Entity · state | Other owners' triggers legal here | `—` / `?` cells | Source |
|---|---|---|---|
| ENT-003 · Accrued | EVT-007 (AREA-004) → Posted | `—` for EVT-005 | ENT-003 grid |
| ENT-003 · Posted | none | **?** Posted × EVT-006; `—` for EVT-005, EVT-007 | ENT-003 grid |
| ENT-002 · Cancelled | EVT-004 (AREA-002) reaches only Confirmed bookings (RX-005) | **?** Cancelled × EVT-004 `#assumption` | RX-005 effects; the ENT-002 grid is not in the map excerpt |

### Shared data
| Field / entity | Other writers | Other readers | Source |
|---|---|---|---|
| Session.seats_taken | RX-001 (+1), RX-003 (−1) | RX-001 guard | shared-data.md |
| Member.credits_used | RX-004 (+), RX-007 (:= 0) | DEC-002 in RX-004, screen: my balance | shared-data.md |
| Accrued charge (ENT-003) | RX-004 (create), RX-007 (posted) | RX-007, screen: my balance | shared-data.md |

### Invariants
| INV | Statement | Threatened here by | Enforced? | Source |
|---|---|---|---|---|
| INV-001 | Seats taken never exceed capacity | RX-001, the reaction that retakes a freed seat | RX-001: yes (conditional update) | invariants.md |
| INV-002 | Credits used is never negative | RX-006, RX-007 | RX-006: **no** | invariants.md |
| INV-003 | An accrual is charged at most once, and never after its booking was refunded | RX-006, RX-007 | **?** | invariants.md |
| INV-004 | A booking's credits are spent exactly once and returned at most once | RX-004, RX-006 | **?** (both at-least-once, no idempotency key found) | invariants.md |

### Known interactions
| CONF | Pair | Boundary condition | Status |
|---|---|---|---|
| — | AREA-003 × AREA-004 (INV-002) | a booking priced on 28 Feb and cancelled on 3 Mar, after the 1 Mar reset, leaves credits used at −2 | open, blocker |
| — | AREA-004 posting × refund (INV-003) | an accrual posted on 1 Apr 00:00 and its booking cancelled free of charge at 00:05 | open, major |
| — | AREA-004 RX-004 / RX-006 (INV-004) | EVT-006 delivered twice for one booking | open, major |
| — | AREA-004 RX-007 | the posting runs in an unrecorded timezone | open, minor |

The four findings sit in `example-dependency-map.md` without CONF ids, so the id column is `—`.

### KB candidates
- The ENT-002 grid has no column for EVT-004 or EVT-006: what a staff session cancellation does to a booking that is already Cancelled is unspecified. Source: RX-005 effects name Confirmed bookings only. `#assumption`

## 3. The coverage-item list

Slice ids: `L<n>` is the lookup of §1. Layers per the depth gate. Cases are listed in §4.

| Slice id | Condition | Technique (layer) | Coverage items | Cases |
|---|---|---|---|---|
| L1 L2 RX-002 → EVT-006 → RX-006 | A member cancels with 24 h or more of notice | scenario, main (interaction) | the path, DEC-003 R1 | 1 |
| L1 L2 RX-002 | The session has started, the booking is unknown, not the member's, or already cancelled | scenario, exception exits; rule / state | RX-002 guard, the rolls-back exits | 14–16 |
| L2 RX-006 failure `?` | The credit return fails after commit | scenario, exception | stated deferral: failing the handler needs a fault-injection seam, so hand `qa-api-<stack>` the case and ask `be-<stack>` and the owner what happens; open question OQ-1 | — |
| L3 RX-003, RX-005 → EVT-006 | Staff cancel a booking, or a whole session | scenario, extension and fan-out (interaction); decision table | DEC-003 R3; one EVT-006 per booking | 5, 7 |
| L5 DEC-003 threshold | The 24 h cut-off | BVA 3-value (rule) | cut-off − 1 s, at, + 1 s | 2–4 |
| L4 ENT-003 Accrued × EVT-006 | The cancelled booking has an accrual | state transition across owners (interaction) | Accrued → Removed | 5 |
| L4 ENT-003 Posted × EVT-006 `?` | The month was posted before the cancellation | state transition across owners; 1-switch (interaction) | the `?` cell | 8 |
| L4 ENT-002 Cancelled × EVT-004 `?` | Staff cancel a session after a late cancellation | state transition across owners (interaction) | the `?` cell | 12 |
| L6 Session.seats_taken RX-002 → RX-001 | The freed seat is retaken | def-use, CRUD (data) | (writer RX-002, reader RX-001); INV-001 × RX-001 | 6 |
| L6 Member.credits_used RX-004, RX-006 | The same event delivered twice | concurrency and delivery (concurrency) | one duplicate per at-least-once reaction | 9, 10 |
| L6 Member.credits_used RX-006 × RX-007 | A cancellation and the posting at the same instant | concurrency, race with a schedule (concurrency) | the concurrent pair | 11 |
| L7 INV-002, INV-003 | A return after the reset; a refund after posting | invariant attack (interaction) | (INV-002, RX-006), (INV-002, RX-007), (INV-003, RX-006) | 8 |
| L7 INV-004 | Credits spent and returned once | invariant attack (concurrency) | (INV-004, RX-004), (INV-004, RX-006) | 9, 10 |
| L2 EVT-007 | The posting runs twice | temporal, idempotency (temporal) | one idempotency case per job; (INV-003, RX-007) | 13 |
| L2 EVT-007 | Other boundary instants, DST, a late or missed run | temporal | stated deferral: blocked by the unrecorded timezone, open question OQ-2 | — |
| L8 four findings | Open conflicts | conflict boundary | each boundary condition: INV-002 → 8, INV-003 → 11, INV-004 → 9, timezone → OQ-2 | 8, 9, 11 |

Not taken, P3: an EVT-005 that arrives after its booking was already cancelled (out-of-order delivery).

Open questions raised by §8 and handed back: **OQ-1** what happens to a member's credits when the return fails; **OQ-2** in which timezone the posting runs.

## 4. The suite — headlines

Prefix `TC-CANCEL-`. Dates are March and April of the example year.

| ID | Case | Priority | Technique (layer) | Slice id |
|---|---|---|---|---|
| 001 | Ana cancels *Glazing workshop* on 15 Mar 09:00, 25 h ahead: 2 credits come back, credits used 8 → 6, and the £6.00 accrued on 11 Mar stays | P1 | scenario + DEC-003 R1 (interaction) | L1 L2 RX-002 → EVT-006 → RX-006 |
| 002 | Session starts 16 Mar 10:00. Ana cancels at 15 Mar 10:00:00 (24 h 00 m 00 s): the credits come back | P1 | BVA 3-value, at the boundary (rule) | L5 DEC-003 |
| 003 | Same session, cancelled at 15 Mar 10:00:01 (23 h 59 m 59 s): nothing is returned | P1 | BVA 3-value, boundary + 1 s (rule) | L5 DEC-003 |
| 004 | Same session, cancelled at 15 Mar 09:59:59 (24 h 00 m 01 s): the credits come back. The 1 s step is `#assumption` | P1 | BVA 3-value, boundary − 1 s (rule) | L5 DEC-003 |
| 005 | Staff cancel Ana's *Sculpture masterclass* booking (session 28 Mar 14:00) at 28 Mar 04:00, 10 h ahead: 2 credits come back, credits used 7 → 5, the £6.00 accrual is removed | P1 | decision table R3 + foreign state (rule, interaction) | L3 RX-003 · L4 ENT-003 Accrued × EVT-006 |
| 006 | *Glazing workshop II* is full (6 of 6): Ana cancels, then Ben books the freed seat and is confirmed, seats taken 6 | P2 | def-use, INV-001 (data) | L6 RX-002 → RX-001 |
| 007 | Staff cancel *Wheel basics II* (Standard) on 30 Mar at 08:00, 10 h ahead, with Ana, Ben and Cara booked: each gets 1 credit back | P1 | scenario fan-out (interaction) | L3 RX-005 → EVT-006 ×3 → RX-006 |
| 008 | Ana, at credits used 7, books *Raku masterclass II* (3 Apr 14:00) on 30 Mar and cancels on 1 Apr 10:00 after the posting. **Expected: open question** — see the full row | P1 | foreign state + invariant attack (interaction) | L4 ENT-003 Posted × EVT-006 · L7 INV-002, INV-003 |
| 009 | EVT-006 for case 001 is delivered twice: credits used ends at 6, not 4 | P1 | concurrency and delivery (concurrency) | L6 RX-006 · L7 INV-004 |
| 010 | EVT-005 for Ana's 2 Mar *Wheel basics* booking is delivered twice: credits used is 1, not 2 | P1 | concurrency and delivery (concurrency) | L6 RX-004 · L7 INV-004 |
| 011 | Ana's *Raku masterclass II* booking (£12.00 accrued) is cancelled at 1 Apr 00:00:00 while posting runs. **Expected: open question: is the £12.00 accrual removed or charged?** | P1 | concurrency, race with a schedule (concurrency) | L6 RX-006 × RX-007 · L8 INV-003 |
| 012 | Ana late-cancels *Raku masterclass* on 20 Mar 20:00, 18 h ahead, and forfeits 3 credits. Staff cancel the session on 21 Mar 09:00. **Expected: open question: are the 3 forfeited credits returned for a session that never ran?** | P1 | foreign state (interaction) | L4 ENT-002 Cancelled × EVT-004 |
| 013 | The posting runs twice on 1 Apr: Ana is charged £6.00 once | P1 | temporal, idempotency (temporal) | L2 EVT-007 · L7 INV-003 |
| 014 | An unknown booking id is refused as not found (`404`, `#assumption`) | P2 | rule | L1 RX-002 |
| 015 | Another member's booking is refused (`403`, `#assumption`) | P2 | rule (authorization) | L1 RX-002 |
| 016 | Parameterized, one refusal per row: an already-cancelled booking → `409`; a session that has already started → `409` (both `#assumption`; Cancelled × EVT-002 is `—`; RX-002 guard) | P2 | state / rule | L1 RX-002 |

Cases 008, 011 and 012 are the most valuable output: business decisions nobody made, which no field-level technique reaches. Cases 011 and 013 are triggered on demand, so the unrecorded timezone does not decide them; their *Environment needs* name the hook.

## 5. Full rows — cases 001, 008, 009

Setup (shared): staging; member Ana on the Basic plan (8 credits, £6.00 overage), credits used 0 on 1 Mar; tiers Standard 1, Workshop 2, Masterclass 3; Ana's bookings and cancellations as in her month, up to the case's date. Each case lists only its delta.

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-CANCEL-001 | A member who cancels with 25 h notice gets the credits back and keeps the earlier accrual | P1 | positive | scenario (main) + DEC-003 R1 | L1 L2 RX-002 → EVT-006 → RX-006 | Clock at 15 Mar 09:00. Credits used 8; £6.00 accrued on 11 Mar | 1. Ana cancels her *Glazing workshop* booking (starts 16 Mar 10:00)<br>2. Wait for the return<br>3. Open "my balance" | Within 10 s (`#assumption`, the budget for an after-commit reaction), "my balance" shows credits used 6 and £6.00 accrued. The booking is Cancelled and the session shows one seat free | Ana; *Glazing workshop* (Workshop, 2 credits); notice 25 h |
| TC-CANCEL-008 | A cancellation after the monthly posting would take credits used below zero | P1 | negative | foreign state + invariant attack | L4 ENT-003 Posted × EVT-006 `?` · L7 INV-002, INV-003 | On 30 Mar: credits used 7, so *Raku masterclass II* (Masterclass, 3 credits, starts 3 Apr 14:00) spends 1 credit and accrues 2 × £6.00 = £12.00, credits used 8. Posting has run on 1 Apr 00:00: £6.00 + £12.00 = £18.00 charged, credits used 0 | 1. Set the clock to 1 Apr 10:00 (52 h before the session)<br>2. Ana cancels *Raku masterclass II*<br>3. Wait for the return<br>4. Open "my balance" and her account charges | **Open question:** the cancellation takes credits used from 0 to −1 (INV-002) and the £12.00 is already charged (INV-003): what is the intended outcome? | Ana; DEC-003 R1; credits used 0; charged £18.00 |
| TC-CANCEL-009 | A duplicate delivery of the cancellation event returns the credits once | P1 | negative | concurrency and delivery, duplicate | L6 RX-006 · L7 INV-004 | As TC-CANCEL-001 before step 1: credits used 8; RX-006 is at-least-once. *Environment needs:* deliver the same `BookingCancelled` message twice with the same business id | 1. Ana cancels her *Glazing workshop* booking<br>2. Deliver the resulting EVT-006 a second time with a new broker message id<br>3. Wait for both to be processed<br>4. Open "my balance" | Within 10 s (`#assumption`), credits used is 6, and not 4 | Ana; booking id of *Glazing workshop*; 2 credits |

All other cases use the same form. Every id above exists in `example-dependency-map.md` or in `example-area.md`.

## 6. Arithmetic, recomputed

| Number | Working |
|---|---|
| Case 001: 8 → 6 | Ana's credits used after 11 Mar is 8; the workshop spent 2; 8 − 2 = 6 |
| Case 001: notice 25 h | 15 Mar 09:00 to 16 Mar 10:00 |
| Cases 002–004 | 15 Mar 10:00:00 to 16 Mar 10:00 = 24 h 00 m 00 s; +1 s = 23 h 59 m 59 s; −1 s = 24 h 00 m 01 s |
| Case 005: 7 → 5, £6.00 removed | credits used 7 after 25 Mar; the 11 Mar booking spent 2 and accrued 1 × £6.00; 7 − 2 = 5 |
| Case 007 | Standard costs 1 credit per member |
| Case 008: 1 credit, £12.00 | remaining 8 − 7 = 1; cost 3; spent 1; overage credits 3 − 1 = 2; 2 × £6.00 = £12.00; credits used 7 + 1 = 8 |
| Case 008: £18.00, −1, 52 h | £6.00 + £12.00 = £18.00; posting resets to 0; return of 1 gives 0 − 1 = −1; 1 Apr 10:00 to 3 Apr 14:00 = 52 h |
| Case 009: 6, not 4 | 8 − 2 = 6; a second return gives 6 − 2 = 4 |
| Case 010 | 2 Mar *Wheel basics* costs 1; credits used 1; a second pricing gives 2 |
| Case 012 | 20 Mar 20:00 to 21 Mar 14:00 = 18 h; Masterclass costs 3 |
| Case 013 | one posting charges £6.00 (the 11 Mar overage); a second run charges nothing |
