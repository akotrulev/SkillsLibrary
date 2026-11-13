# Worked example — a member books a session

The filled example for `test-case-writer`: a basis excerpt in, a business-first suite out. The system is the **workshop-booking** toy of `backend/_shared/business-documentation/references/example-area.md`; `cross-feature-test-design/references/example-cancel-booking.md` covers cancelling in the same system. **Shape is normative; domain content is illustrative.**

Thirteen cases: three journeys, five rule and calculation cases, three state and permission cases, one concurrency case and **one** field case. The request carries a single field, and the suite is still thirteen cases long, because the work is in what a booking costs and what it sets off.

## Input — the basis, in short

> **Actors.** A member books seats for themselves.
> **BR-1** Credit cost = the session tier's credits per seat: Standard 1, Workshop 2, Masterclass 3.
> **BR-2** When credits remaining ≥ credit cost, the booking spends that many credits and nothing is charged.
> **BR-3** Otherwise it spends the credits that remain, and the shortfall is an overage.
> **BR-4** A booking is never refused for lack of credits.
> **BR-5** Accrued overage is charged once, at the start of the next month, and credits used go back to 0.
> **C-1** Credits remaining = Monthly credits − Credits used.
> **C-2** Overage credits = Credit cost − Credits remaining.
> **C-3** Overage charge = Overage credits × Overage rate (the member's personal rate when set, else the plan's).
> **V-1** A session takes no booking beyond its capacity.
> **V-2** Only a signed-in member can book. `#assumption`
> **J-1** Member · book a session within the plan → booked, credits spent, nothing owed.
> **J-2** Member · book beyond the plan → booked, overage accrued, charged once at month end.
> **J-3** Member · take a seat another member frees → booked on a session that was full.
> **Data.** `sessionId` — uuid, required.
> **Notes.** Pricing runs after the booking commits. The posting runs on the 1st at 00:00.
> **OQ-1** Can a member book a session that has already started? **OQ-2** Refusal texts and status codes are not specified.

## Output

```markdown
## Test Cases: Book a session

**Source**: STORY-3310 — basis `docs/test-cases/012-book-a-session-basis.md`
**Coverage**: full
**Techniques applied**: use-case (main, alternate, exception with recovery), BVA 3-value on BR-2's threshold, decision table 3/3 on the tier, calculation branches of C-2/C-3 (covered, partly, not at all, personal rate, accumulation), state (capacity), concurrency checklist (last seat), EP on `sessionId`
**Balance**: journeys 3 · rules and calculations 5 · states and permissions 3 · connections 1 · field 1 (8 %)
**Generated**: 2026-11-13

### Setup (shared preconditions)
- **Environment**: staging, build `<sha>`; `ASYNC_BUDGET = 10 s` `#assumption` (pricing runs after the booking commits)
- **Plan and tiers**: Basic = 8 monthly credits, £6.00 per overage credit; Standard 1, Workshop 2, Masterclass 3 credits per seat
- **Members, all on Basic**: Ana (credits used 6) · Ben (credits used 6, personal overage rate £4.50) · Cara (credits used 0) · Dan (credits used 8). Nobody has an accrual
- **Sessions, capacity 6**: *Wheel basics* (Standard, 2 taken) · *Wheel basics II* (Standard, 2 taken) · *Glazing workshop* (Workshop, 2 taken) · *Glazing workshop II* (Workshop, **6 taken**, one seat is Ana's, starts in 3 days) · *Raku masterclass* (Masterclass, 2 taken) · *Sculpture masterclass* (Masterclass, 4 taken) · *Open studio* (Standard, started 10 minutes ago)
- **Reset before each case**: the members' credits used and the sessions' seats back to the values above; no accruals
- **Environment needs**: run the monthly posting on demand; send two requests at the same instant

### Cases

#### Journeys

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-BOOK-001 | A member with credits to spare books a session and owes nothing | P1 | positive | use-case (main) | J-1, BR-2, C-1 | — | 1. Cara opens the session list and opens *Wheel basics* → Standard, 1 credit, 2 of 6 seats taken<br>2. She books a seat → the booking is Confirmed<br>3. She opens *My bookings* → *Wheel basics* is listed as Confirmed<br>4. She opens *My balance* | Within `ASYNC_BUDGET`, *My balance* shows credits used 1, credits remaining 7 and nothing accrued. *Wheel basics* shows 3 of 6 seats taken | Cara; *Wheel basics* |
| TC-BOOK-002 | A member who books beyond her credits is charged the overage once, at month end | P1 | positive | use-case (alternate) | J-2, BR-3, BR-5, C-2, C-3 | — | 1. Ana opens the session list and books *Sculpture masterclass* → Confirmed, listed under *My bookings*<br>2. She opens *My balance* → within `ASYNC_BUDGET`: credits used 8, £6.00 accrued, nothing charged<br>3. Run the monthly posting<br>4. She opens *My balance* and her account | One charge of £6.00 on Ana's account; credits used 0; no accrual left. *Sculpture masterclass* shows 5 of 6 seats taken | Ana; *Sculpture masterclass* |
| TC-BOOK-003 | A member refused on a full session books it once another member frees a seat | P2 | positive | use-case (exception, then recovery) | J-3, V-1 | — | 1. Cara opens *Glazing workshop II* (6 of 6) and books a seat → refused as full; *My bookings* does not list it<br>2. Ana cancels her booking on *Glazing workshop II* → the session shows 5 of 6<br>3. Cara books a seat → Confirmed<br>4. Cara opens *My balance* | Cara's booking is Confirmed and listed under *My bookings*; within `ASYNC_BUDGET` her credits used is 2; *Glazing workshop II* shows 6 of 6 seats taken | Cara, Ana; *Glazing workshop II* |

#### Rules and calculations

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-BOOK-004 | Credits that cover the cost exactly, or with one to spare, are spent and nothing is accrued | P1 | positive | BVA 3-value on BR-2 (at and above; below is TC-BOOK-002) | BR-2, C-1 | — | 1. Set Cara's credits used to the row's value<br>2. Cara books *Raku masterclass* (3 credits)<br>3. She opens *My balance* | Within `ASYNC_BUDGET`, per row: credits used and accrued as listed | credits used 4 → used 7, accrued none · credits used 5 → used 8, accrued none |
| TC-BOOK-005 | A member with no credits left is still booked, and the whole cost becomes overage | P1 | positive | calculation (not covered) + BR-4 | BR-3, BR-4, C-2, C-3 | — | 1. Dan books *Raku masterclass* (3 credits) → Confirmed, not refused<br>2. He opens *My balance* | Within `ASYNC_BUDGET`: credits used still 8, £18.00 accrued. The booking is listed under *My bookings* as Confirmed | Dan; *Raku masterclass* |
| TC-BOOK-006 | A member's personal overage rate is used instead of the plan's | P1 | positive | calculation (personal rate) | C-3 | — | 1. Ben books *Sculpture masterclass* (3 credits)<br>2. He opens *My balance* | Within `ASYNC_BUDGET`: credits used 8, £4.50 accrued, and not £6.00 | Ben; *Sculpture masterclass* |
| TC-BOOK-007 | Two overage bookings in one month are charged as one sum | P1 | positive | calculation (accumulation) | BR-5, C-3 | — | 1. Ana books *Sculpture masterclass* → within `ASYNC_BUDGET`, £6.00 accrued, credits used 8<br>2. Ana books *Wheel basics II* (1 credit) → within `ASYNC_BUDGET`, £12.00 accrued, credits used 8<br>3. Run the monthly posting<br>4. She opens her account | Exactly one charge, of £12.00; credits used 0; no accrual left | Ana |
| TC-BOOK-008 | The session's tier decides what a seat costs | P2 | positive | decision table 3/3 | BR-1 | — | 1. Cara books the row's session<br>2. She opens *My balance* | Within `ASYNC_BUDGET`, per row: credits used as listed, nothing accrued | *Wheel basics* (Standard) → used 1 · *Glazing workshop* (Workshop) → used 2 · *Raku masterclass* (Masterclass) → used 3 |

#### States and permissions

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-BOOK-009 | A full session takes no booking and costs the member nothing | P1 | negative | state (capacity guard) | V-1 | — | 1. Dan books *Glazing workshop II* (6 of 6)<br>2. He opens *My bookings*, then *My balance*, after `ASYNC_BUDGET` | Refused as full (`409` `#assumption`, OQ-2). *My bookings* does not list the session; credits used still 8 and nothing accrued; the session still shows 6 of 6 | Dan; *Glazing workshop II* |
| TC-BOOK-010 | A visitor who is not signed in cannot book | P2 | negative | permission | V-2 `#assumption` | Signed out | 1. Open *Wheel basics* and book a seat | Sent to sign in (`401` on the API, `#assumption`). *Wheel basics* still shows 2 of 6 seats taken | — |
| TC-BOOK-011 | Booking a session that has already started | P1 | negative | state (guard) | OQ-1 `#assumption` | — | 1. Cara books *Open studio*, which started 10 minutes ago<br>2. She opens *My bookings* and *My balance* | **open question: OQ-1 — is the booking refused, or accepted and priced as usual?** | Cara; *Open studio* |

#### Concurrency

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-BOOK-012 | The last seat goes to exactly one of two members who book at the same instant | P1 | negative | concurrency (pair of writers on seats taken) | V-1 | *Glazing workshop II* at 5 of 6 (Ana's seat freed) | 1. Cara and Ben each send a booking for *Glazing workshop II* at the same instant<br>2. Open the session, then both members' *My bookings* and *My balance* | Exactly one booking is Confirmed and the other is refused as full. The session shows 6 of 6. The confirmed member's credits used went up by 2; the other member's did not move | Cara (used 0), Ben (used 6) |

#### Field validation

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-BOOK-013 | A booking request without a usable session id is refused and books nothing | P2 | negative | EP on `sessionId` (invalid classes) | §6 `sessionId` | Signed in as Cara | 1. Send `POST /bookings` with the row's `sessionId`<br>2. Open *My bookings* | Per row, the status listed (`#assumption`, OQ-2). *My bookings* is unchanged | missing → `400` · `not-a-uuid` → `400` · `00000000-0000-4000-8000-000000000000` (no such session) → `404` |

### Worked numbers

| Case | Inputs | Working | Expected |
|---|---|---|---|
| TC-BOOK-001 | credits 8, used 0, cost 1; seats 2 | remaining 8 − 0 = 8; 8 ≥ 1, so spent 1; used 0 + 1 = 1; remaining 8 − 1 = 7; seats 2 + 1 = 3 | used 1, remaining 7, 3 of 6 |
| TC-BOOK-002 | credits 8, used 6, cost 3, rate £6.00; seats 4 | remaining 8 − 6 = 2; 2 < 3, so spent 2; overage 3 − 2 = 1; 1 × £6.00 = £6.00; used 6 + 2 = 8; seats 4 + 1 = 5 | £6.00 accrued, then one charge of £6.00; used 8, then 0 |
| TC-BOOK-003 | Cara used 0, cost 2; seats 6 | seats 6 − 1 = 5, then 5 + 1 = 6; used 0 + 2 = 2 | used 2, 6 of 6 |
| TC-BOOK-004 | credits 8, cost 3; used 4, then used 5 | used 4: remaining 4 ≥ 3, spent 3, used 7 · used 5: remaining 3 ≥ 3, spent 3, used 8 | used 7; used 8; no accrual |
| TC-BOOK-005 | credits 8, used 8, cost 3, rate £6.00 | remaining 0; spent 0; overage 3 − 0 = 3; 3 × £6.00 = £18.00 | £18.00 accrued, used 8 |
| TC-BOOK-006 | credits 8, used 6, cost 3, personal rate £4.50 | remaining 2; spent 2; overage 1; 1 × £4.50 = £4.50; used 6 + 2 = 8 | £4.50 accrued, used 8 |
| TC-BOOK-007 | after the first booking: used 8, £6.00 accrued; then cost 1 | remaining 0; overage 1 − 0 = 1; 1 × £6.00 = £6.00; £6.00 + £6.00 = £12.00 | one charge of £12.00, used 0 |
| TC-BOOK-008 | used 0; cost 1, 2, 3 | 0 + 1 = 1 · 0 + 2 = 2 · 0 + 3 = 3 | used 1 · 2 · 3 |
| TC-BOOK-012 | cost 2; Cara used 0, Ben used 6 | Cara 0 + 2 = 2, or Ben: remaining 2 ≥ 2, 6 + 2 = 8 | the winner's used goes up by 2 |

### Cleanup (always runs)
- Cancel every booking the run created; restore Ana's seat on *Glazing workshop II*
- Remove the accruals and the posted charges of TC-BOOK-002, -005, -006 and -007
- Set every member's credits used back to the Setup values
- Log the members out

## Coverage Summary

| Basis line | Test Cases | Covered? |
|---|---|---|
| J-1: book within the plan | TC-BOOK-001 | ✅ |
| J-2: book beyond the plan, pay at month end | TC-BOOK-002, TC-BOOK-007 | ✅ |
| J-3: take a freed seat | TC-BOOK-003 | ✅ |
| BR-1: the tier sets the cost | TC-BOOK-008 | ✅ |
| BR-2 / C-1: credits cover the cost | TC-BOOK-001, TC-BOOK-004 | ✅ |
| BR-3 / C-2 / C-3: shortfall × rate | TC-BOOK-002, TC-BOOK-005, TC-BOOK-006 | ✅ |
| BR-4: never refused for lack of credits | TC-BOOK-005 | ✅ |
| BR-5: charged once at month end | TC-BOOK-002, TC-BOOK-007 | ✅ |
| V-1: capacity | TC-BOOK-003, TC-BOOK-009, TC-BOOK-012 | ✅ |
| V-2: signed-in members only | TC-BOOK-010 | ✅ `#assumption` |
| §6 `sessionId` | TC-BOOK-013 | ✅ |
| OQ-1: a session that has started | TC-BOOK-011 | ⚠️ expected result waits on the answer |
```

## What to notice

- **The suite opens with what a member gets, not with what the form rejects.** TC-BOOK-002 ends on a charge that appears a month after the click, on another screen. A case that stopped at "Booking confirmed" would pass with the overage never charged.
- **Every figure is in Worked numbers.** BR-2's threshold has its three values: one credit to spare and exactly enough (TC-BOOK-004), one short (TC-BOOK-002).
- **A refusal asserts that nothing changed** (TC-BOOK-009: no booking, no credits spent, the seat count as it was).
- **The undecided rule is a case** (TC-BOOK-011): the day OQ-1 is answered, only its expected result is written.
- **One field case.** `sessionId` has three invalid classes and they share a parameterized row.
- What pricing and posting set off elsewhere (the same event delivered twice, the posting run twice, a cancellation after posting) is derived by `cross-feature-test-design`; see its cancel-booking example.
