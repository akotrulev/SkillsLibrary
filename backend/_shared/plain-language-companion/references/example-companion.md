# Golden example — the `-explained.md` companion

One filled companion for `be-shared-plain-language-companion`, over the shared **workshop-booking** toy system used across the `backend/_shared/` examples: `docs/plans/001-workshop-booking/delivery-plan-explained.md` — the companion to a `be-planner` delivery plan.

Read it **against its source**. The point of the example is not the prose — it is that every date, dependency and blocker below traces to a line in the source, and that nothing else does. **Shape and disciplines are normative; domain content is illustrative.**

(`be-documenter` / `be-feature-documenter` documents get no companion — they are written in the plain, example-first shape to begin with; see `backend/_shared/business-documentation/references/example-area.md`.)

---

## `delivery-plan-explained.md`

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
