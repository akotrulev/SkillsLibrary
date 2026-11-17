# Events & reactions

**Created:** 2026-08-02
**Owned by:** `business-analysis:dependency-map`

## Triggers
| ID | Trigger | Kind | Fired by | Owner | Source |
|---|---|---|---|---|---|
| EVT-001 | Member books a seat | command | Member | AREA-003 bookings | US3 AC1 |
| EVT-002 | Member cancels a booking | command | Member | AREA-003 bookings | US4 AC1 |
| EVT-003 | Staff cancels a session | command | Staff | AREA-002 scheduling | US7 AC1 |
| EVT-004 | Booking cancelled | event | RX-002, RX-003 | AREA-003 bookings | US4 AC2 |
| EVT-005 | Monthly posting | schedule | 1st of the month 00:00 Europe/London | AREA-004 credits | US9 AC1 |

## Reactions
| ID | When | Guard | Owner | Effects | Emits | Mode | On failure | Source |
|---|---|---|---|---|---|---|---|---|
| RX-001 | EVT-001 | seats taken < capacity | AREA-003 bookings | ENT-001 — → Confirmed; Session.seats_taken +1 | — | in request | rolls back ("session full") | US3 AC2 |
| RX-002 | EVT-002 | session not started | AREA-003 bookings | ENT-001 Confirmed → Cancelled; Session.seats_taken −1 | EVT-004 | in request | rolls back | US4 AC1 |
| RX-003 | EVT-003 | — | AREA-002 scheduling | ENT-001 Confirmed → Cancelled | EVT-004 per booking | in request | rolls back | US7 AC1 |
| RX-004 | EVT-004 | — | AREA-004 credits | DEC-001; Member.credits_used −returned | — | after commit, at-least-once | retried 3× then dead-letter | US8 AC1 |
| RX-005 | EVT-005 | every member | AREA-004 credits | Member.credits_used := 0 | — | scheduled | ? | US9 AC1 |
