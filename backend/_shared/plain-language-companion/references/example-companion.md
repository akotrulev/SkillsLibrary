# Golden example — the `-explained.md` companions

Two filled companions for `be-shared-plain-language-companion`, both over the shared **workshop-booking** toy system used across the `backend/_shared/` examples:

1. `docs/business-model/areas/bookings-explained.md` — the companion to the area document in `be-shared-business-documentation`'s `references/example-area.md`
2. `docs/plans/001-workshop-booking/delivery-plan-explained.md` — the companion to a delivery plan

Read them **against their sources**. The point of the example is not the prose — it is that every rule, threshold and blocker below traces to a line in the source, and that nothing else does. **Shapes and disciplines are normative; domain content is illustrative.**

---

## 1. `areas/bookings-explained.md`

```markdown
# Bookings — in plain language

> **This is a plain-language companion to [`bookings.md`](bookings.md).**
> It explains the same thing in simpler words, with examples. It adds nothing new.
> **If the two ever disagree, `bookings.md` is right and this file is out of date.**

**Explains:** `bookings.md` (as of 2026-08-02, commit `a3f9c21`) · **Written by:** `be-shared-plain-language-companion`
**Examples in this document are made up** to illustrate the rules. The names, dates and figures in them are not real data.

## What this part of the system is for

This is where members book a seat on a workshop session, and where those bookings get cancelled.

It does not decide which sessions exist, and it does not take any money. It only manages seats.

## Who uses it

**Members** — signed-in people who book seats. A member can book a seat, see their own bookings, and cancel their own bookings. They cannot see or touch anyone else's.

**Staff** — studio staff. Staff can cancel anyone's booking, and can mark who actually turned up.

## Booking a seat

A member picks a session that hasn't started yet and confirms. The system then checks three things, in order: the session is still open, there is a seat left, and this member doesn't already have a seat on it. If all three are fine, the seat is theirs and the number of remaining seats drops by one. A confirmation email follows.

The email is sent *after* the seat is safely recorded. That ordering is deliberate: an email problem can never cost someone their seat.

**An example.** A Tuesday pottery session has 12 seats and 11 are taken.

- Ana books at 9:02 and gets the twelfth seat. The session now shows as full.
- Ben tries at 9:03. He is told the session is now full, and no booking is made for him.
- Ana tries to book the same session a second time by accident. She is told she already has a
  booking for it, and no second seat is taken from anyone.

Two people going for the last seat at the same instant cannot both get it. The seat count is protected at the moment the booking is written down, not just checked a moment earlier.

## Cancelling a booking

A booking can be cancelled any time before the session starts. The seat is released straight away, so someone else can take it.

If a **member** cancels **less than 24 hours** before the session starts, that is recorded as a late cancellation on their record. If **staff** cancel, it is never recorded as late.

**An example.** Ana has a seat on a session that starts Thursday at 18:00.

- She cancels on Wednesday at 10:00 — more than 24 hours ahead, so nothing is recorded against her.
- Had she cancelled on Thursday at 09:00 — nine hours ahead — it would have been recorded as a late cancellation.
- Had she cancelled at 18:30, after the session started, she could not have cancelled at all.

**One thing worth knowing:** late cancellations are recorded, but nothing in the system currently does anything with that record. No warning, no limit, no fee. See the open questions below.

## When things go wrong

| What happened | What the person is told | What happens to the booking |
|---|---|---|
| Someone else took the last seat moments earlier | "This session is now full" | No booking is made |
| They already have a seat on that session | "You already have a booking for this session" | No second seat is taken |
| The session was cancelled, or has already started | "This session can no longer be booked" | No booking is made |
| The confirmation email can't be sent | Nothing — the booking still stands | The email is retried quietly in the background |
| They try to cancel a session that has already started | "This booking can no longer be cancelled" | Nothing changes |

## What we don't know

These came out of reading the software. Nobody wrote down *why* these rules exist, so they are questions for you, not for the engineers.

| # | Question | Why it matters |
|---|---|---|
| Q1 | Is the 24-hour late-cancellation cut-off a policy you chose? | It is enforced today but written down nowhere. If it is your policy, changing it is a small job |
| Q2 | Late cancellations are recorded and never used. Was a consequence intended? | Right now members are being marked with no effect at all — either the consequence is missing, or the record is pointless |
| Q3 | Is booking genuinely free for members? | There is no payment anywhere in this part of the system. Either that is correct, or something is missing |

## What this doesn't cover

The full rules, the exact places in the software each one comes from, and the diagrams of the booking lifecycle are in [`bookings.md`](bookings.md). Which sessions exist and how many seats they have is a different area — see [`scheduling.md`](scheduling.md).
```

---

## 2. `delivery-plan-explained.md`

Note what it keeps and what it drops: **every date, dependency and blocker survives; task ids, file lists and agent names do not.**

```markdown
# Workshop Booking — delivery plan in plain language

> **This is a plain-language companion to [`delivery-plan.md`](delivery-plan.md).**
> It explains the same thing in simpler words, with examples. It adds nothing new.
> **If the two ever disagree, `delivery-plan.md` is right and this file is out of date.**

**Explains:** `delivery-plan.md` (as of 2026-08-02, commit `7c1e480`) · **Written by:** `be-shared-plain-language-companion`
**Examples in this document are made up** to illustrate the rules. The names, dates and figures in them are not real data.

## What we're building, and in what order

Thirteen pieces of work, grouped into seven stages. The order is not a preference — each stage needs the one before it to exist.

**Stage 1 — Paperwork.** Two accounts only a person can set up: the sign-in service, and the email provider. No software is written here, but stage 4 cannot start without the first account and stage 6 cannot start without the second — so this stage starts now, not when the work that needs it arrives.

**Stage 2 — Groundwork.** The empty shell of the system: it starts up, it can be run locally, and it knows how to talk to a database. Nothing a person can use yet.

**Stage 3 — Storing the information.** The tables that hold members, workshops, sessions and bookings. After this the system can remember things, but still can't do anything with them.

**Stage 4 — Knowing who's who, and the shared plumbing.** Signing in, the difference between a member and a staff member, and the standard way the system reports a problem. Every feature depends on all of it, which is why it comes before any feature.

**Stage 5 — The features.** Scheduling workshops and sessions, and booking seats. Two separate pieces of work that don't touch each other, so two people could build them at the same time. A third piece follows both: writing down, precisely, everything the finished system can be asked — the record the testing work is built from.

**Stage 6 — Email.** The booking confirmation. It comes after the features because there is nothing to send an email about until booking exists.

**Stage 7 — Finishing touches.** Making failures visible to the people running the system, and having a specialist double-check the protection that stops a session being overbooked.

## What you'll be able to see, and when

| After stage | What you could demo |
|---|---|
| 4 | Someone signs in and is recognised as a member or as staff. Not exciting, but it proves the front door works |
| 5 | The real thing: staff schedule a session, a member books a seat, and the session shows one fewer seat left |
| 6 | The same, plus the confirmation email arriving |
| 7 | A failure somewhere in the system showing up where the people running it can see it |

**An example of how the ordering bites.** Booking a seat needs two things already in place: somewhere to record the booking (stage 3), and a way to know which member is asking (stage 4). Starting the booking work before those exist doesn't make it arrive sooner — it just means it gets built twice.

## What's holding us up

| What's blocked | What it's waiting for | Who can unblock it |
|---|---|---|
| Signing in — and every feature after it | The sign-in service account (stage 1). Not set up yet | The studio owner |
| Sending any email | The email provider account (stage 1). Not set up yet | The studio owner |

Neither of these stops stages 2 and 3. The sign-in account stops stage 4 and everything after it; the email account stops only stage 6. Accounts like these take days to arrange rather than minutes, so both are worth starting now even though the work that needs them is weeks away.

## Still to be decided

Nothing. Every open question was answered when the plan's blueprint was approved.

## What this doesn't cover

The individual pieces of work, who or what builds each one, which files they touch, and how we'll know each is finished are all in [`delivery-plan.md`](delivery-plan.md). What the system will do is in [`blueprint-explained.md`](blueprint-explained.md).
```
