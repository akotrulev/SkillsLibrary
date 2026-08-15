# Golden example — `areas/<area>.md`

The filled example for `be-shared-business-documentation`: one area document as a `be-documenter` run would write it into `docs/business-model/areas/bookings.md`. The system is the same **workshop-booking** toy the planner examples build — imagined here as an *inherited* codebase being documented after the fact, so the tiers and open questions are visible. **Shapes and disciplines are normative; domain content and citations are illustrative.**

Note what the example demonstrates: business language in every narrative section (no class names, status codes, or table names outside Evidence columns), `#observed` always with `file:line`, every `#inferred` doubled into the open questions, and a "What can go wrong" table per use case.

---

# AREA-003 — Bookings

**Created:** 2026-08-02
**Owned by:** `be-shared-business-documentation`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02
**Entry points:** 4 HTTP · 0 jobs · 0 consumers — all traced
**Models:** [FLOW-001 booking a seat] · [ENT-002 booking lifecycle] · [DEC-001 cancellation outcome]

## What you can do here

- Book a seat on an upcoming published session, if seats are left
- See all your bookings, newest first
- Cancel a booking before the session starts — cancelling less than a day before is recorded against you
- Staff can cancel anyone's booking and mark members as attended

## Who uses it

| Actor | Who they are | What they can do here | How they are recognised |
|---|---|---|---|
| Member | A signed-in studio member | Book, view own, cancel own | `bookings:own` permission on their token `#observed` (`BookingEndpoints.cs:21`) |
| Staff | Studio staff | Cancel any booking, mark attendance | `workshops:manage` permission `#observed` (`BookingEndpoints.cs:58`) |

## How it works, end to end

### Booking a seat

**Who:** Member
**Starts when:** the member picks an upcoming session and confirms.

1. The system checks the session is open for booking and has not started.
2. It checks a seat is still available and that this member does not already hold one.
3. The seat is confirmed, and the count of remaining seats goes down by one.
4. A confirmation email is sent — after the booking is safe, so a mail problem never loses a seat.

**Ends with:** a confirmed seat the member can see in their bookings, and a confirmation email.

**What can go wrong:**
| Situation | What the member sees | What happens to the booking |
|---|---|---|
| The last seat went to someone else moments earlier | "This session is now full" | No booking is created `#observed` (`BookingService.cs:44`) |
| They already have a seat on this session | "You already have a booking for this session" | No second booking `#observed` (`BookingService.cs:39`) |
| The session was cancelled or already started | "This session can no longer be booked" | No booking is created `#observed` (`BookingService.cs:31`) |
| The confirmation email cannot be sent | Nothing — the booking stands | Email is retried in the background `#observed` (`EmailQueue.cs:27`) |

Two members racing for the last seat cannot both win — the seat count is guarded at the point of record, not merely checked beforehand `#observed` (`BookingService.cs:44`, `migrations/003:18`).

### Cancelling a booking

**Who:** Member (own) or Staff (any)
**Starts when:** a cancellation is requested before the session starts.

1. The system releases the seat, making it available to others immediately.
2. If a member cancels less than 24 hours before start, the cancellation is marked "late" on their record. Staff cancellations are never marked late.
3. A cancellation email is sent.

**What can go wrong:**
| Situation | What the requester sees | Outcome |
|---|---|---|
| The session has already started or been attended | "This booking can no longer be cancelled" | Booking unchanged `#observed` (`BookingService.cs:71`) |
| The booking was already cancelled | Same message | Nothing changes twice `#observed` (`BookingService.cs:71`) |

## The rules that apply

| # | Rule | Applies when | Tier | Evidence |
|---|---|---|---|---|
| R1 | One live seat per member per session | Booking | `#observed` | `migrations/003:14` |
| R2 | A session never holds more confirmed seats than its capacity | Booking | `#observed` | `BookingService.cs:44` |
| R3 | Cancelling under 24 hours before start is recorded as a late cancellation | Member cancels | `#observed` | `BookingService.cs:66` |
| R4 | A late cancellation carries no consequence today — it is recorded and nothing reads it | — | `#observed` | recorded at `BookingService.cs:66`; no reader found (search: `late_cancel` across `src/`) |
| R5 | The 24-hour threshold most likely exists to let another member take the seat | — | `#inferred` | no comment or document found; **open question Q1** |

## Boundaries

- Does not decide what sessions exist or their capacity — that is **Scheduling** (AREA-002)
- Does not take payment — nothing in the system does; sessions appear to be included in membership `#inferred`, **open question Q2**
- Does not send email itself — it hands off to the shared email queue (Foundations, `system-overview.md`)

## Open questions for the business

| # | Question | Why it matters | Evidence |
|---|---|---|---|
| Q1 | Is the 24-hour late-cancellation threshold a policy you chose, and is it yours to change? | It is enforced but undocumented; changing it is a one-line decision if it is policy | `BookingService.cs:66` |
| Q2 | Late cancellations are recorded but nothing ever uses them — is a consequence planned, or is this dead weight? | Members are being flagged with no effect; either build the consequence or stop recording | `BookingService.cs:66`; no reader found |
| Q3 | Is booking genuinely free for members, or is missing payment a gap? | Determines whether AREA-003 is complete or awaiting a payments feature | no payment path anywhere (search: `payment`, `price`, `charge` across `src/`) |
