---
name: be-shared-experience-plan
description: Use when an approved blueprint with user-facing areas needs its EXPERIENCE planned before the API surface — actors and their primary tasks, journeys (task → screens → endpoints, steps-to-goal counted), the screen map and information architecture, the app shell, a per-screen spec (page type, surface, primary action, region states, data needed), and the screen ↔ endpoint matrix. Triggers "plan the screens", "what does the user actually see", "design the navigation for this system". Do NOT use to build the UI (`fe-<stack>`), judge a built UI (`design-ux-review`), plan tables (`be-shared-data-model-plan`) or endpoints (`be-shared-api-surface-plan`).
---

# Experience Plan — what the user sees, before the API exists

The plan altitude for the user's side of the system: **who uses it, what they are trying to get done, which screens carry each task, how those screens are reached, and what each screen needs from the API** — written so the `fe-<stack>` agent builds the shell and the pages without inventing the navigation, and so the API surface is planned against real screens instead of guessed from tables. It states decisions; it draws no mockups and writes no components.

**Announce at start:** "I'm using the `be-shared-experience-plan` skill to plan the experience."

**Prerequisites:** an **approved** `blueprint.md` whose routing map binds at least one area to `fe-react` / `fe-blazor`, and a written `data-model.md`. The blueprint's *User-facing capabilities* and *Primary actors* columns and its §3b flows are the inputs; the entity catalog is what the screens display. Runs **before** `api-surface.md` — the screens' data needs are one of that step's inputs.

**Discipline:** load [`design/ux-patterns`](../../../design/ux-patterns/SKILL.md) (`design-ux-patterns`) before writing — its task-inventory → IA method, shell decision table, page-type anatomy and responsiveness budget are the rules this artifact applies. This skill owns the *artifact and its place in the pack*; that skill owns the *UX rules*. Neither loads a `fe-*` stack skill.

## When to use

- Step 3 of a `be-planner` run — after the data model, before the API surface — whenever the routing map names a frontend agent
- A new user-facing area is added to a planned system (`EXTEND` — plan the delta screens, reuse the existing shell and nav)
- An existing frontend needs its screens documented as the baseline a plan will extend (`RESUME` — read routes and nav out of the code, mark `#observed`, then plan the delta)

## When NOT to use

- The blueprint routes nothing to a frontend agent → skip the step and say so in the report (`Experience plan: skipped — no user-facing area`)
- The blueprint is not approved → the screens will be rewritten; wait
- The ask is to *build* the screens → `fe-<stack>`; to *review* a built UI → `design/ux-review`; to *draw* it → a design canvas, outside this pack

## Output

**`docs/plans/<NNN>-<initiative>/experience-plan.md`** in the initiative folder.

**A filled golden example is at `references/example-experience-plan.md`** (the shared `001-workshop-booking` pack — shapes normative, domain content illustrative).

---

## Procedure

### Step 1 — Actors and primary tasks

One row per task, derived from the blueprint's *User-facing capabilities* column — every capability there becomes at least one task here, and a task with no capability behind it is a scope question for the blueprint, not a quiet addition.

| Id | Actor | Task (verb + object + outcome) | Frequency | Stakes | Source |
|---|---|---|---|---|---|
| U1 | Member | book a seat on a session so it is held for me | weekly | money-adjacent | blueprint §2 Booking · FLOW-002 |

Frequency is *many times a day · daily · weekly · rare*; stakes are *routine · money/compliance · irreversible*. Rank by frequency first — the top three to five tasks per actor decide the home screen and the primary navigation (`ux-patterns` §1). Mark evidence: a task read from a story or the blueprint is `#confirmed`; one you derived from a flow is `#inferred`.

### Step 2 — App shell and information architecture

Decide the shell **once** for the whole initiative with `ux-patterns` §2's table, and record the rejected alternative in one line. Then write the **nav map** — one row per destination, its placement, the actor(s), the tasks it serves, and its page type. Apply the depth budget: every top-ranked task within one click of the shell, everything else within two. A task that lands at depth three goes back to Step 1 as a ranking question.

Where several actors share the app (member vs staff), state whether the nav differs by role (hidden destinations) or the app has separate entry points — the auth model in the blueprint decides which is honest.

`RESUME` / `EXTEND`: the existing shell and nav are `#observed` facts — new destinations slot into them, and a change to the shell itself is its own open question.

### Step 3 — Journeys

One per primary task: the ordered screens, the action on each, and the endpoint each step calls (named by resource and verb now, path once `api-surface.md` exists). **Count the steps** and state the target; every step must be load-bearing (`ux-review`'s flow-friction rule, applied before the flow exists). Model the failure exit the blueprint's flowchart already labelled — where does the user land when the seat is gone?

```markdown
**J1 — U1 Book a seat** (target: 3 steps)
1. S2 Sessions — filter by date → `GET sessions`
2. S3 Session detail — **Book seat** → `POST sessions/{id}/bookings`
3. S3 (same screen) — confirmation inline, toast "Seat booked" with Undo → cancel path
Failure: capacity reached → S3 shows the failed state with "Join waitlist" `[TBD - owner]` or "Pick another session"
```

Link to the blueprint's flow by id (`FLOW-nnn`) where a business-model KB exists.

### Step 4 — Screen catalog

One block per screen, ids `S1…Sn`, in nav order. This is what the frontend task binds to and what the API step reads.

```markdown
### S3 — Session detail

**Route:** `/sessions/{sessionId}` · **Nav:** Sessions › (breadcrumb) · **Actors:** member, staff
**Page type:** detail · **Surface:** page (shareable, bookmarkable)
**Primary action:** Book seat (member) · Mark attendance (staff — same screen, role-gated)
**Regions:** header (title, starts-at, capacity left) · description · attendee list (staff only)
**States:** loading skeleton · loaded · failed (region-scoped, retry) · empty attendee list — "No bookings yet"
**Data needed:** session (title, startsAt, capacity, bookedCount, workshop title) · my booking on this session, if any · attendee list with member names (staff)
**Serves:** U1, U3, U5 · **Journeys:** J1, J3
```

Rules:

- **Title = nav label = route title** (`ui-rules`' one-name rule) — state it once, here.
- **Page type and surface come from `ux-patterns` §3**; a modal is written down only where the interruption is the value.
- **Every region names its four states.** A screen with a data region and no failed state is a plan defect, not a build detail.
- **Data needed is written in the user's nouns**, resolved against `data-model.md` entities — this is the line `api-surface.md` turns into response fields, and the one place a screen can ask for an aggregate (`bookedCount`) the tables do not store, so the API step can decide computed-vs-stored deliberately.
- **Role differences live on the screen block**, never as a duplicate screen.

### Step 5 — Screen ↔ endpoint matrix

Once `api-surface.md` is written (the API step fills this in and hands the file back), one row per screen-endpoint pair:

| Screen | Endpoint | Purpose on this screen |
|---|---|---|
| S3 | `GET /api/v1/sessions/{sessionId}` | header + description |
| S3 | `POST /api/v1/sessions/{sessionId}/bookings` | primary action (member) |

Two checks run on it, and both are `be-planner` Step-7 coverage lines: **every user-facing endpoint appears on at least one screen** (an endpoint no screen calls is either a machine-to-machine one — say so — or dead), and **every screen's data-needed line resolves to an endpoint** (a screen with a need no endpoint meets is the gap the build would have discovered).

### Step 6 — Cross-cutting decisions

Once, at the end, from `ux-patterns` §5–§9: **density** (and why) · **accelerators** (global search / shortcuts / saved views, or "none — under threshold") · **notification surface** (inline + toast, or + a notification centre because of which asynchronous events) · **first run** (the setup-checklist items) · the **responsiveness budget** as acceptance criteria the frontend tasks inherit verbatim.

---

## Experience plan template

```markdown
# <Initiative> — Experience Plan

**Date:** YYYY-MM-DD · **Written by:** `be-shared-experience-plan` · **Discipline:** `design-ux-patterns`
**Inputs:** `./blueprint.md` (§2 capabilities, §3b flows, §6 routing) · `./data-model.md`
**Frontend agent:** `fe-react` | `fe-blazor` — per the routing map

## 1. Actors & primary tasks
| Id | Actor | Task | Frequency | Stakes | Source |
|---|---|---|---|---|---|

## 2. App shell & navigation
**Shell:** sidebar | top nav | hybrid — <why> · **Rejected:** <the alternative, one line> · **Mobile:** drawer | bottom tabs
**Role handling:** <one nav with role-hidden destinations | separate entry points — and why>

| Destination | Nav placement | Actor(s) | Tasks it serves | Page type |
|---|---|---|---|---|

## 3. Journeys
<!-- one per primary task: numbered steps, screen + action + endpoint per step, step target, failure exit -->

## 4. Screens
<!-- one block per screen, S1…Sn, in nav order — route, nav, actors, page type, surface, primary action, regions, states, data needed, serves, journeys -->

## 5. Screen ↔ endpoint matrix
<!-- filled by the API step; every user-facing endpoint on ≥ 1 screen, every data need resolved -->
| Screen | Endpoint | Purpose on this screen |
|---|---|---|

## 6. Cross-cutting
**Density:** … · **Accelerators:** … · **Notification surface:** … · **First run:** …
**Responsiveness budget (acceptance criteria for every frontend task):**
- [ ] every press acknowledged ≤ 100 ms (pressed state; submit disables with in-flight state)
- [ ] a region still loading at 300 ms shows a content-shaped skeleton, never a blank or page-centre spinner
- [ ] a region still loading at ~4 s says so; a timed-out region fails with retry, scoped to itself
- [ ] no layout shift on load; independent regions load independently

## 7. Open questions
<!-- the [TBD] items above, each with an owner -->
```

## What NOT to put in an experience plan

- **Mockups, colours, type, spacing** — the look is `design/visual-identity`'s and the tokens `design/design-tokens`'; the plan says *detail page with a header and three regions*, not what it looks like.
- **Component names, routes' file paths, library choices** — the `fe-<stack>` agent's Step-1 decision record; the plan says the route *path* and the page *type*.
- **Copy** — labels and messages are `design/ux-writing`'s at build time; the plan names the action ("Book seat") because the name is an IA decision, and stops there.
- **Endpoint bodies** — `api-surface.md`; the plan says what the screen *needs*, in the user's nouns.
- **A screen per role** — role differences are lines on one screen block.

## Self-check

1. Every *User-facing capability* in `blueprint.md` §2 maps to ≥ 1 task in §1; every task serves ≥ 1 screen; every primary task has a journey.
2. The shell is decided once, with its rejected alternative; every top-ranked task is within one click of it, nothing is at depth three.
3. Every screen block has route, page type, surface, primary action, regions with four states, and a data-needed line resolved against `data-model.md`.
4. Every journey counts its steps against a stated target and names its failure exit.
5. After the API step: the matrix covers every user-facing endpoint and every data need — the two Step-7 coverage lines read `n/n`.
6. No `[TBD]` without an owner; no colour, component or copy decision leaked in.

## Handoffs

- **→ `be-shared-api-surface-plan`** (next step) — §4's data-needed lines are its input; it returns to fill §5.
- **→ `be-shared-delivery-plan`** — every frontend task binds `fe-react` / `fe-blazor` with `design-ux-patterns` in its skills, cites the screen ids it delivers, and inherits §6's budget as acceptance criteria; a capability's last task is worded from its journey.
- **→ `fe-react` / `fe-blazor`** — takes §2–§4 as the IA decision in its Step 1 (validates, does not redesign; disagreement is a `delivery-plan.md` §7 deviation) and applies `design-ux-patterns` per page in Step 2.
- **→ `design/ux-review`** — at build review, cites the screen id / nav-map row a finding contradicts.
- **→ `be-shared-plain-language-companion`** — `experience-plan-explained.md`: the journeys as stories a stakeholder can walk.
- **→ `qa-test-case-designer` / `qa-ui-<stack>`** — the journeys are their end-to-end test basis.

## Version policy

Stack-agnostic — the plan names the frontend agent from the routing map and nothing version-bound; the agent's own version detection (React/Next major · Blazor render mode per TFM) governs the build.
