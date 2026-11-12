# Golden example, Level 1 — `areas/<area>.md` (the guide)

The Level 1 example for `dev:doc-business-model`: one area guide as a `be-documenter` run would write it into `docs/business-model/areas/credits-and-charges.md`. The system is the same **workshop-booking** toy the planner examples build — imagined here as an *inherited* codebase being documented after the fact. **Shape, tone and the example discipline are normative; domain content and citations are illustrative.**

Note what the example demonstrates: a document a client can read top to bottom — plain headings, numbered steps, formulas written as plain-text math with `Where:`, one running cast, and a worked example whose arithmetic carries through to the final result — with **no** `file:line`, tier tag, code noun, defect word or evidence table, and with the client's own words throughout (credits, sessions, the exact messages staff see) (those are Level 3: [example-technical.md](example-technical.md); the connections and failure handling are Level 2: [example-behind-the-scenes.md](example-behind-the-scenes.md)). Optional sections that do not apply (there is no *Scope* section here because the area applies to every member) are dropped, and the search that proved it is a row in Level 3's evidence index.

---

# AREA-004 — Session credits & charges

**Created:** 2026-08-02
**Owned by:** `dev:doc-business-model`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02
**Audience:** shareable
**Levels:** [Guide](credits-and-charges.md) · [Behind the scenes](credits-and-charges.behind-the-scenes.md) · [Technical reference](credits-and-charges.technical.md)
**Models:** [FLOW-004 pricing a booking] · [ENT-003 accrued charge lifecycle] · [DEC-002 credit / overage split]

## Overview

Every membership plan comes with a number of session credits per month. Booking a session spends credits according to the session's tier; when a member runs out, the booking still goes ahead and the shortfall is charged as an **overage** at a per-credit rate. Overage charges build up during the month and are charged once, at the start of the next month, when credits reset.

**Important:** credits and charges are worked out at the moment a booking is made or cancelled — never re-priced afterwards. A credit returned by a later cancellation is available for future bookings; it does not reduce an overage already accrued.

## Setup

Plans and session tiers are configured by staff. A member may carry a personal overage rate that overrides the plan's.

| Parameter | Level | Description | Example |
|---|---|---|---|
| Plan name | Plan | The name of the membership plan | Basic |
| Monthly credits | Plan | Credits granted on the 1st of every month | 8 |
| Overage rate | Plan | Price per credit booked beyond the monthly allowance | £6.00 |
| Overage rate override | Member | A member-specific price per overage credit — the most specific rate wins: member, then plan | £4.50 |
| Credits per seat | Session tier | How many credits one seat on a session of this tier costs | Standard 1 · Workshop 2 · Masterclass 3 |

Validations:

- Plan name must be unique.
- Monthly credits is a whole number, 0 or more; both overage rates are 0 or more.
- Every session has exactly one tier.
- Changing a tier's cost or a plan's rate affects future bookings only — nothing already booked is re-priced.

| Situation | What staff see | What happens |
|---|---|---|
| A plan is saved with a name another plan already has | “That plan name is already taken.” | Nothing is saved |
| Monthly credits or a rate is below 0 | “Monthly credits must be 0 or more.” / “Overage rate must be 0 or more.” | Nothing is saved |

Fixed in the system today, not configurable: the late-cancellation cut-off (24 hours before the session starts), the posting moment (the 1st of the month at 00:00), and the rule that unused credits do not carry over.

## How it works

### Booking a seat

**Trigger:** a member's booking is confirmed (the seat itself is allocated by **Bookings**, AREA-003 — this flow prices it).

1. Credit cost = the session tier's *Credits per seat*.
2. Credits remaining = Monthly credits − Credits used this month.
3. If Credits remaining ≥ Credit cost: the booking spends *Credit cost* credits and nothing is charged.
4. Otherwise the booking spends whatever credits remain, and the shortfall becomes an overage:

   Overage credits = Credit cost − Credits remaining
   Overage charge = Overage credits × Overage rate

   Where: *Overage rate* is the member's override if one is set, otherwise the plan's rate.
5. The overage charge is accrued against the member — recorded, not yet charged.

**Result:** the member's credits used goes up by the credits spent; if there was a shortfall, an accrued overage line is attached to the booking. A booking is never refused for lack of credits.

### Cancelling a booking

**Trigger:** a booking is cancelled before the session starts.

1. If the cancellation is **24 hours or more** before the session starts, or is made by **staff**: the credits the booking spent are returned, and any overage accrued for *that booking* is removed.
2. If a **member** cancels **less than 24 hours** before the start: nothing is returned. The credits stay spent and any overage accrued for the booking stays.

**Result:** credits used goes down by the credits returned (case 1) or is unchanged (case 2). Returned credits are available for future bookings only.

### Monthly posting

**Trigger:** the 1st of every month at 00:00, for every member.

1. Sum the member's accrued overage charges that have not yet been posted.
2. If the sum is greater than 0, post it as **one charge** to the member's account and mark those accruals as posted.
3. Set Credits used to 0 — the new month starts with the plan's full allowance. Unused credits from the previous month are lost.

**Result:** at most one overage charge per member per month on their account, and a fresh credit balance.

## How it connects

**Starts from:**

- **Bookings** (AREA-003): a confirmed booking is priced here, and a cancelled booking — by the member or by staff — has its credits returned here.
- **Scheduling** (AREA-002): when staff cancel a whole session, every confirmed booking on it is cancelled by staff, one cancellation per booking, so each member's credits come back.

**Sets off:** nothing outside this area. Pricing, returns and posting finish here; no other area is told.

**Shares:** this area reads bookings, which **Bookings** owns. Credits used is changed only by this area's three flows.

## Example

**Setup**

| Plan | Monthly credits | Overage rate |
|---|---|---|
| Basic | 8 | £6.00 |

| Tier | Credits per seat |
|---|---|
| Standard | 1 |
| Workshop | 2 |
| Masterclass | 3 |

Ana is on the Basic plan with no personal override. Ben is also on Basic but carries a personal overage rate of £4.50. It is March; both start the month with 0 credits used.

**Ana's month**

| Date | What happens | Credit cost | Credits remaining before | Spent from credits | Overage | Credits used after |
|---|---|---|---|---|---|---|
| 2 Mar | Books *Wheel basics* (Standard, starts 9 Mar 18:00) | 1 | 8 | 1 | — | 1 |
| 4 Mar | Books *Glazing workshop* (Workshop, starts 16 Mar 10:00) | 2 | 7 | 2 | — | 3 |
| 6 Mar | Books *Raku masterclass* (Masterclass, starts 21 Mar 14:00) | 3 | 5 | 3 | — | 6 |
| 11 Mar | Books *Sculpture masterclass* (Masterclass, starts 28 Mar 14:00) | 3 | 2 | 2 | 1 credit × £6.00 = **£6.00 accrued** | 8 |
| 15 Mar 09:00 | Cancels *Glazing workshop* — 25 hours before it starts | — | 0 | 2 returned | — | 6 |
| 20 Mar 20:00 | Cancels *Raku masterclass* — 18 hours before it starts | — | 2 | nothing returned (late) | — | 6 |
| 25 Mar | Books *Wheel basics II* (Standard, starts 30 Mar 18:00) | 1 | 2 | 1 | — | 7 |
| 1 Apr 00:00 | Monthly posting | — | — | — | **£6.00 charged** to Ana's account | 0 |

Walking through the two lines that matter:

- **11 Mar.** Credit cost 3, credits remaining 8 − 6 = 2. 2 is less than 3, so 2 credits are spent and the shortfall is 3 − 2 = 1 overage credit. Overage charge = 1 × £6.00 = £6.00, accrued.
- **15 Mar.** The workshop's 2 credits come back, so Ana has 2 credits again — but the £6.00 accrued on 11 Mar stays, because a returned credit never re-prices an earlier booking.
- **1 Apr.** One charge of £6.00 is posted. Ana's 1 unused credit is lost; she starts April with 8.

**Ben's override.** Had Ben made the 11 Mar booking in Ana's position, his shortfall would have been charged at his personal rate: 1 × £4.50 = £4.50.

## Who can do what

| Who | Can |
|---|---|
| Member | Book and cancel own sessions (priced automatically); see own credits used, credits remaining and accrued overage |
| Staff | Cancel anyone's booking — always returns the credits; define plans and tiers; set or clear a member's overage override |

## Open questions

| # | Question | Why it matters |
|---|---|---|
| Q1 | Unused credits are lost at month end. Is that the intended policy, or is roll-over missing? | Members on lighter months pay for credits they cannot use; either is a valid policy, but nobody wrote it down |
| Q2 | A credit returned by a cancellation does not reduce an overage already accrued that month. Intended? | It is the rule most likely to generate a support query ("I cancelled, why was I still charged?") |
| Q3 | Is the 24-hour late-cancellation cut-off a policy you chose, and is it yours to change? | It is fixed in the system, not configurable |
| Q4 | A late cancellation forfeits the credits but carries no fee. Was a fee intended? | The forfeiture is the only consequence today |

## Going deeper

**Behind the scenes:** how the parts connect, what runs when, what happens when something fails — [credits-and-charges.behind-the-scenes.md](credits-and-charges.behind-the-scenes.md)
**Technical reference:** for developers — [credits-and-charges.technical.md](credits-and-charges.technical.md)
