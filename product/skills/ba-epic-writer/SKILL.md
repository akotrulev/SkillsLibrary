---
name: epics
description: Use when writing a system plan's §4, the capability-sized epics, each a measurable goal and the features that serve it. Triggers "slice this into epics". Not for the vision (scoping).
disable-model-invocation: true
user-invocable: false
---

# Epics — the system plan's §4

Writes **§4 of a system plan, `## 4. Epics`**, and nothing else: `E1…En`, each one capability a
person gets, with a goal sentence, a plain-English line and the features (`F` ids) that serve it.
`solution-planner` loads it for `/product:plan-system`; the file around it is defined by
`product/skills/solution-blueprint/references/system-plan-format.md`.

**An epic is a capability, not a calendar unit.** "Accounts" is an epic; signing in is a feature
inside it. Every system gets epics, however small: a system with one capability has one epic, never
zero.

**A feature, not a story, is the unit an epic lists.** A feature is one whole thing a person would
name, with the parts it holds ("Booking a seat: see the schedule, book, see my bookings"). Each one
becomes a task block in §6 with its own `/product:plan-feature` prompt, and its acceptance criteria
are written in its spec, not here.

## Inputs needed

1. **The system plan's §2**: its "What it must do" lines are what the epics cover, exactly once each;
   its success measures feed the goal lines; its constraints shape the order of the features.
2. **§1**, in an existing repo: a capability already built has no gap and needs no epic.
3. **§3's areas**, where written: they help cut features along real boundaries, never along layers.

## Procedure

1. **Cut epics by goal, then by actor.** Two epics each delivering a usable capability beat one epic
   where one half blocks the other.
2. **One goal per epic**: **who** can **do what** so that **measurable change**. If it cannot be one
   sentence with a business term and a measurable change, it is two epics. Where §2 carries no measure,
   the goal carries `[TBD - <who decides>]` and the gap is an open question in the plan; never an
   invented number, and never a reason to stop.
3. **Then the plain-English line**: who it is for and what they will be able to do, said the way the
   person who asked would say it. **If it cannot be written without naming a technology, it is not an
   epic** but a technical task, and the fix is upstream in §2.
4. **List the features that serve it**, in the order that gives a person something usable first. Each
   is one whole feature a person would name, usable end to end when it lands. Layers ("the API", "the
   screens") are never features: they are cut into tasks by each feature's implementation plan.
5. **Every §2 capability reaches exactly one epic, and every epic at least one feature.** A
   capability no epic covers is a gap the system forgot; a feature serving no epic is work nobody
   asked for, unless it is the foundation feature.
6. **Ids are never renumbered.** In EXTEND mode new epics take the next free `E` id and new features
   the next free `F` id; an existing epic gains a feature by adding its id to the row.
7. **Hand the feature list to `solution-planner`**: id, title and the epic it serves. It writes each
   one's task block in §6, and `epic-map` places them in §5.

## Output format

````markdown
## 4. Epics

| Epic | Goal | In plain English | Features |
|---|---|---|---|
| E1 | When this is done, **<who>** can **<do what>** so that **<measurable change>** | <one or two sentences, no technology> | F2, F4 |
| E2 | … | … | F3 |
````

The foundation feature, where there is one, serves no epic and appears in no row here; its §6 block
says `**Epic:** — (foundation)`.

## Standards

What §4 must and must never contain is the product rule file `system-plans.md`, not a list here. Read
the project's copy in `.claude/rules/product/`, or the plugin's in `product/skills/rules/` when the
project has not installed them (`/product:rules` does). Where they and this skill disagree, the rule
file wins.

## Examples — goal lines

| ✅ Strong | ❌ Weak |
|---|---|
| When this is done, **finance ops** can **reconcile partner payouts** so that **monthly reconciliation drops from 5 days to <1 day** | We will improve the payouts area |
| When this is done, **mobile users** can **complete onboarding offline** so that **drop-off on signup step 3 falls from 22% to <10%** | Offline support for mobile |
| When this is done, **support agents** can **issue partial refunds in one click** so that **refund time-to-resolution p95 drops from 12 min to <3 min** | Refund flow improvements |

The pattern: **who** + **can do what** + **so that measurable change**. If any of the three is missing,
the epic is not ready.

## Example — one epic, filled

`E1 Booking`, from the workshop-booking system in the format file's §9:

| Epic | Goal | In plain English | Features |
|---|---|---|---|
| E1 | When this is done, **members** can **book a seat online** so that **phone bookings fall from about 60 to under 10 a month** | A member sees what is on and takes a seat without ringing anyone | F2 |

Read what it does not contain: no endpoint, no table, no screen name, no capacity constraint. The
mechanism is §3's and each feature spec's; the studio owner can tell from this row whether it is the
thing they asked for.

## Sizing

| Symptom | Shape |
|---|---|
| One capability, one or a few features | **One epic**; small is fine, the epic still exists so §5 and §6 can cite it |
| One capability with several actors or data variations | **One epic**, its features cut by actor or variation |
| Two capabilities that happen to share an area | **Two epics**, one goal each |
| A capability spanning several delivery windows | **Split by window**, each part usable on its own with its own goal |
