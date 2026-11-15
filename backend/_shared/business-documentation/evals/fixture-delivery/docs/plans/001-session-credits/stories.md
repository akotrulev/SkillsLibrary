# Stories — Session credits

## US1 — Booking a session with credits

**Epic:** E1

### Goal
A member needs to book sessions against a monthly allowance of credits and keep booking when the credits run out, so that a busy month never turns them away.

### How we get there
Credits are spent first and only the shortfall is charged, at the plan's rate, so a member pays for what they use beyond the allowance and nothing more.

### What is included
- **The cost of a seat**: a seat costs credits by the session's tier.
- **The overage**: what the credits do not cover is charged per credit.
- **Seeing your credits**: a member can see where they stand.

### Acceptance criteria

**The cost of a seat**
- **AC1** A booking of a Standard session spends 1 credit, a Workshop 2 and a Masterclass 3, while the member has credits left.

**The overage**
- **AC2** A booking is never refused for lack of credits: the credits the member has left are spent and the shortfall is charged as overage at the plan's rate, £6.00 per credit on Basic and £5.00 on Plus.
- **AC3** A member's personal overage rate, when one is set, is used instead of the plan's rate.

**Seeing your credits**
- **AC4** A member can see their plan, its monthly credits, the credits used, the credits left and the overage waiting on their account.

**Across the feature**
- **AC5** A booking is priced once, with the tier cost and rate in force when it is confirmed; a later change to a plan does not re-price it.

### Not included
- Taking the payment: out of scope for the initiative.

### Depends on
- none

### Source
requirements.md §4, lines 1–4 and 11.

## US2 — Cancelling a booking

**Epic:** E1

### Goal
A member needs to give a seat back and get their credits when they cancel in good time. The 24-hour cut-off gives the studio a day to offer the seat to another member.

### How we get there
The cut-off is measured from the moment of cancelling to the session's start, and staff cancelling a whole session is always in good time.

### What is included
- **Cancelling your booking**: a member cancels their own booking.
- **Cancelling a session**: staff cancel a session and every booking on it.

### Acceptance criteria

**Cancelling your booking**
- **AC6** A member who cancels 24 hours or more before the session starts gets back the credits the booking spent, and the overage for that booking is removed.
- **AC7** A member who cancels less than 24 hours before the session starts gets nothing back.

**Cancelling a session**
- **AC8** When staff cancel a session, every booked member gets their credits back, however close the session is.

### Not included
- A fee for a late cancellation: not asked for.

### Depends on
- US1 (the credits a booking spends)

### Source
requirements.md §4, lines 5–6.

## US3 — Plans and rates

**Epic:** E2

### Goal
Studio staff need to set up the plans and the overage rates, so that the studio can change its prices without a developer.

### How we get there
Staff change a plan on one screen, and a member's personal rate is set on the member.

### What is included
- **Plan settings**: the name, the monthly credits and the overage rate of a plan.
- **A member's personal rate**: staff set or clear a rate for one member.

### Acceptance criteria

**Plan settings**
- **AC9** Staff can change a plan's name, monthly credits and overage rate, and the change applies to future bookings.
- **AC10** A plan name already used by another plan is refused with “That plan name is already taken” and nothing is saved.
- **AC11** Monthly credits below 0 and an overage rate below 0 are refused and nothing is saved.

**A member's personal rate**
- **AC12** Staff can set a member's personal overage rate and clear it again.

### Not included
- Changing the credits a tier costs: deferred to a follow-up.

### Depends on
- none

### Source
requirements.md §4, lines 7–8.

## US4 — The month end

**Epic:** E2

### Goal
A member needs to be charged once for the month's overage, and to start the new month with their credits, so that nothing is collected booking by booking.

### How we get there
The month's accrued overage is posted together, once, and credits start again.

### What is included
- **The month's charge**: one charge per member.
- **Credits for the new month**: the allowance starts again, with unused credits carried over.

### Acceptance criteria

**The month's charge**
- **AC13** Each member with overage for the month sees one charge for the month's total.
- **AC14** The charge is posted on the last day of the month.
- **AC15** A member with no overage sees no charge.

**Credits for the new month**
- **AC16** Credits not used by the end of the month carry over to the next month, up to 4.

### Not included
- Taking the payment: out of scope for the initiative.

### Depends on
- US1 (the overage that accrues)

### Source
requirements.md §4, lines 9–10.
