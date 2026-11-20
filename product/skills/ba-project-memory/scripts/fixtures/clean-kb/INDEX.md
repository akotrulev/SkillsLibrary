# Business Model — Workshop booking

Read this file first, every session. One line per artifact; read the ones your task touches.

## Entities
- [Booking](entities/booking.md) — ENT-001; lifecycle Confirmed→Cancelled; owners: AREA-002 scheduling, AREA-003 bookings
## Flows
- [Book a seat](flows/book-a-seat.md) — FLOW-001; full-session branch
## Decisions
- [Credit return](decisions/credit-return.md) — DEC-001; hit policy U; contributed by AREA-004 credits
## Dependencies
- [Events & reactions](events.md) — 5 triggers, 5 reactions
- [Shared data](shared-data.md) — 1 entity, 1 shared field
- [Invariants](invariants.md) — INV-001
## Cross-cutting
- [Glossary](glossary.md) — canonical terms
- [Interaction map](interaction-map.md) — 1 resolved conflict, 1 open (CONF-002)
- [Active context](active-context.md) — last touched 2026-11-17; 2 open questions
