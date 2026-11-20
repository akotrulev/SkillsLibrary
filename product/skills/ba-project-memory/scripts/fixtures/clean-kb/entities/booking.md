# Entity — Booking (ENT-001)

**Created:** 2026-08-02
**Owned by:** `product:state-grid`

**Sources**: US3, US4, US7 · **Features touching this lifecycle**: AREA-002 scheduling, AREA-003 bookings

## States
| State | Meaning | Initial? | Terminal? | Source |
|---|---|---|---|---|
| Confirmed | a seat is held for the member | yes | no | US3 AC1 |
| Cancelled | the seat is released | no | yes | US4 AC1 |

## Transition grid
Cell = target state `(owning feature id)` · `—` = illegal by decision · `?` = unspecified (finding)

| ↓ State \ Event → | EVT-001 member books | EVT-002 member cancels | EVT-003 staff cancels a session |
|---|---|---|---|
| Confirmed | — | Cancelled (AREA-003) | Cancelled (AREA-002) |
| Cancelled | — | — | ? |

## Open questions
- ❓ ENT-001: `Cancelled × EVT-003` = `?` [TBD - ask PO]
