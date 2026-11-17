# Shared data

**Created:** 2026-08-02
**Owned by:** `business-analysis:dependency-map`

## CRUD matrix — entities touched by two or more features
| Entity | Create | Read | Update | Delete | Completeness |
|---|---|---|---|---|---|
| Booking (ENT-001) | RX-001 | RX-004 | RX-002, RX-003 | none | by decision (cancelled is a state — ENT-001) |

## Shared fields
| Field | Written by | Read by | Note |
|---|---|---|---|
| Member.credits_used | RX-004 (−), RX-005 (:= 0) | screen: my balance | see INV-001 |
