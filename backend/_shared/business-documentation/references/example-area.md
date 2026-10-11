# Golden example — `areas/<area>.md`

The filled example for `dev:doc-business-model`: one area document as a `be-documenter` run would write it into `docs/business-model/areas/credits-and-charges.md`. The system is the same **workshop-booking** toy the planner examples build — imagined here as an *inherited* codebase being documented after the fact. **Shape, tone, the example discipline and the evidence table are normative; domain content and citations are illustrative.**

Note what the example demonstrates: a body that reads like a product spec — plain headings, numbered steps, formulas written as plain-text math with `Where:`, one running cast, and a worked example whose arithmetic carries through to the final result — with every `file:line`, tier tag and code noun confined to the closing table. Optional sections that do not apply (there is no *Scope* section here because the area applies to every member) are dropped, and the search that proved it is a row in the table.

---

# AREA-004 — Session credits & charges

**Created:** 2026-08-02
**Owned by:** `dev:doc-business-model`
**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02
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

## Where this lives in the code

| Section | Statement | Evidence | Tier |
|---|---|---|---|
| Overview | Overage accrues during the month, posted once at month start | `OverageChargeJob.cs:40` | `#observed` |
| Overview | Bookings are priced at the moment they are made and never re-priced | `CreditPricingService.cs:31`; no re-pricing path (search: `Reprice`, `Recalculate` under `src/Credits/`) | `#observed` |
| Overview | The feature exists so that members can book beyond their plan without being refused | comment at `CreditPricingService.cs:9`; **Q1** | `#inferred` |
| Setup | Plan: name, monthly credits, overage rate | `MembershipPlan.cs:8-14` | `#observed` |
| Setup | Member overage override; precedence member → plan | `CreditPricingService.cs:48` | `#observed` |
| Setup | Credits per seat on the session tier | `SessionTier.cs:11` | `#observed` |
| Setup | Plan name unique | `migrations/007:22` | `#observed` |
| Setup | Credits whole number ≥ 0; rates ≥ 0 | `MembershipPlanValidator.cs:15-19` | `#observed` |
| Setup | Tier/rate changes affect future bookings only | `CreditPricingService.cs:31` (cost copied onto the booking at pricing time) | `#observed` |
| Setup | 24 h cut-off, posting at 00:00 on the 1st, no roll-over — fixed in code | `BookingCancelledHandler.cs:19` · `OverageChargeJob.cs:12` · `OverageChargeJob.cs:58`; **Q1**, **Q3** | `#observed` |
| Setup | No *Scope* section — the area applies to every member | search: `Eligib`, `AppliesTo` under `src/Credits/` — none | `#observed` |
| Booking a seat | Steps 1–5, including the partial-cover split | `CreditPricingService.cs:31-61`; [DEC-002] | `#observed` |
| Booking a seat | A booking is never refused for lack of credits | `CreditPricingService.cs:55` (no refusal branch) | `#observed` |
| Cancelling | ≥ 24 h or staff → credits returned and the booking's accrual removed | `BookingCancelledHandler.cs:19-33` | `#observed` |
| Cancelling | Member < 24 h → nothing returned | `BookingCancelledHandler.cs:27` | `#observed` |
| Cancelling | Returned credits never re-price an earlier accrual | no reader of returned credits outside future pricing (search: `ReturnedCredits` under `src/`); **Q2** | `#observed` |
| Monthly posting | One charge per member; accruals marked posted; credits used reset to 0 | `OverageChargeJob.cs:40-58`; [ENT-003] | `#observed` |
| Monthly posting | Zero-sum months post nothing | `OverageChargeJob.cs:44` | `#observed` |
| How it connects | A confirmed booking is priced (EVT-005 → RX-004) | `CreditPricingService.cs:31`; `BookingConfirmed.cs:6` | `#observed` |
| How it connects | A cancelled booking, by member or staff, has its credits returned (EVT-006 → RX-006) | `BookingCancelledHandler.cs:19-33`; `BookingCancelled.cs:8` | `#observed` |
| How it connects | A staff session cancellation cancels each confirmed booking and emits one cancellation per booking (EVT-004 → RX-005 → EVT-006) | `SessionService.cs:70-96` | `#observed` |
| How it connects | Pricing and returns run after the booking change is saved; pricing is retried 3 times and then parked, the return has no failure path; at-least-once, no idempotency key found (RX-004, RX-006; INV-004) | `Outbox.cs:22`; `BookingCancelledHandler.cs:19-33`; no key (search: `IdempotencyKey`, `Processed` under `src/`) | `#observed` |
| How it connects | Nothing outside the area is set off | search: `Publish`, `Emit`, `Outbox.Add` under `src/Credits/` — none | `#observed` |
| How it connects | This area only reads bookings owned by Bookings (RX-004, RX-006); credits used is written only by pricing, return and posting (RX-004, RX-006, RX-007) | `CreditPricingService.cs:31`, `BookingCancelledHandler.cs:19`, `OverageChargeJob.cs:58`; no other writer (search: `CreditsUsed` under `src/`) | `#observed` |
| Who can do what | Member sees own balances only | `CreditEndpoints.cs:21` (`credits:own`) | `#observed` |
| Who can do what | Staff manage plans, tiers, overrides; staff cancellations always return credits | `PlanAdminEndpoints.cs:17` (`workshops:manage`) · `BookingCancelledHandler.cs:21` | `#observed` |
| Open questions | Late cancellation forfeits credits, no fee | `BookingCancelledHandler.cs:27`; no fee path (search: `LateFee`, `Penalty` under `src/`); **Q4** | `#observed` |
