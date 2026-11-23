---
name: plan-experience
description: Use when a feature spec needs its ## Experience section (tasks, journeys, screens, SSR/CSR per route). Triggers "plan the screens", "SSR or CSR for this route". Not for endpoints (plan-api-surface).
disable-model-invocation: true
user-invocable: false
---

# Experience — the feature spec's `## Experience` section

The design altitude for the user's side of one feature: **who uses it, what they are trying to get done, which screens carry each task, how those screens are reached, and what each screen needs from the API**, written so the `fe-<stack>` agent builds the pages without inventing the navigation, and so the `## API surface` is designed against real screens instead of guessed from tables. It states decisions; it draws no mockups and writes no components.

`/product:plan-feature` reads this file in its step 8 when the feature adds or changes a screen or a journey, after the `## Data model` and before the `## API surface` (the screens' data needs are one of that section's inputs), and presents the result as one section of the spec. The user's approval of that section, then of the spec, is the gate; there is no other.

**Discipline:** load [`design/ux-patterns`](../../../design/ux-patterns/SKILL.md) (`design:app-structure`) before writing: its task-inventory → IA method, shell decision table, page-type anatomy and responsiveness budget are the rules this section applies. This skill owns the *section and its place in the spec*; that skill owns the *UX rules*. Neither loads a `fe-*` stack skill.

## Input

- **The spec so far:** the goal, the decisions from the interview, `## Acceptance criteria` (the tasks and journeys derive from them) and the `## Data model` (the entities the screens display).
- **The system plan's §3, when the feature came from one:** the frontend stack and its agent (from the areas), the auth roles, and the app shell. Read the specs of the features this one depends on: their `## Experience` holds the navigation and the screens already designed.
- **Standalone (no system plan):** the existing app's routes, navigation and pages, `#observed` with `file:line`.

## Output

The `## Experience` section of `docs/specs/NNN-<feature>-design.md`, with these subsections in this order: `### Builds on` · `### Actors and tasks` · `### Navigation` · `### Journeys` · `### Screens` · `### Rendering plan` · `### Screen ↔ endpoint matrix` · `### Cross-cutting` · `### Open questions`. A subsection with nothing to say is one line saying so.

[`references/example-experience-section.md`](references/example-experience-section.md) is a filled section from the toy spec all four design skills share: its shapes are normative, its domain content illustrative.

## Scope

**This feature only, on top of what exists.** The app shell is §3's, decided once for the system. A screen or a nav destination an earlier feature's spec designed is **referenced, never redefined**: a row in `### Builds on` naming where it is defined (`007 S3`), and a change the feature makes to it is a delta block under `### Screens`, holding only what changes. A change to §3 itself (a different shell, a new frontend) is put to the user as "this changes the system plan's §3 <line>: keep it or change it?", and `plan-feature`'s close-out records an approved change.

---

## Procedure

### Step 1 — Actors and tasks

One row per task, derived from the spec's acceptance criteria and interview decisions; every criterion with an outcome a person sees becomes at least one task, and a task with no criterion behind it is a scope question for the interview, not a quiet addition.

| Id | Actor | Task (verb + object + outcome) | Frequency | Stakes | Source |
|---|---|---|---|---|---|
| U1 | Member | cancel my own booking so the seat is released | rare | money-adjacent | AC1, AC2 |

Frequency is *many times a day · daily · weekly · rare*; stakes are *routine · money/compliance · irreversible*. Rank by frequency first: the most frequent tasks earn the shortest path (`ux-patterns` §1).

### Step 2 — Navigation

**The shell is given.** Name it from §3 (or the existing app) in one line, then write only what this feature changes: each new destination with its placement, actor(s), tasks and page type, and each existing destination it changes. Apply the depth budget: a top-ranked task within one click of the shell, everything else within two. A task at depth three goes back to Step 1 as a ranking question.

Where no shell exists yet (the system plan's foundation feature, or a standalone feature in a new app), decide it here with `ux-patterns` §2's table and record the rejected alternative in one line. Where several actors share the app, say whether the nav differs by role (hidden destinations) or the app has separate entry points; §3's auth model decides which is honest.

### Step 3 — Journeys

One per primary task: the ordered screens, the action on each, and the endpoint each step calls (named by resource and verb now, by path once `## API surface` exists). **Count the steps** and state the target; every step must be load-bearing (`ux-review`'s flow-friction rule, applied before the flow exists). Model the failure exit: where does the user land when the action is refused?

```markdown
**J1 — U1 Cancel my booking** (target: 3 steps)
1. 007 S3 My bookings — row action **Cancel booking** → opens S1
2. S1 Cancel booking — **Cancel booking** → `POST bookings/{id}/cancel`
3. 007 S3 — the row shows "Cancelled"; toast "Booking cancelled"
Failure: `session-started` → S1 shows the failed state "This session has already started" with **Close**
**Acceptance:** AC1, AC2, AC5
```

**Every journey names the acceptance criteria it proves** on an `**Acceptance:**` line, citing the spec's own `AC<k>`; every criterion with an outcome a person sees lands on at least one journey. A `qa-ui-<stack>` / `qa-mobile-<stack>` task writes the journey test from this line before the screens exist, citing `<spec path> AC<k>`. Link to a business-model flow by id (`FLOW-nnn`) where a KB exists.

### Step 4 — Screens

One block per new screen, ids `S1…Sn` in this spec, in nav order; one delta block per changed screen another spec defined. This is what the frontend task binds to and what the API step reads.

```markdown
#### S1 — Cancel booking

**Route:** none: a dialog over 007 S3 and 007 S2 · **Actors:** member, staff
**Page type:** confirmation · **Surface:** modal (the interruption is the value: the action cannot be undone)
**Primary action:** Cancel booking · secondary: Keep booking
**Regions:** summary (workshop title, starts-at) · late warning (member, inside 24 h) · reason (staff only)
**States:** loaded · submitting (button in-flight) · failed (inside the dialog, retry or close)
**Data needed:** the booking's session title and starts-at · whether cancelling now is late
**Test ids:** `CancelBooking.Dialog` · `CancelBooking.ConfirmButton` · `CancelBooking.ReasonInput`
**Serves:** U1, U2 · **Journeys:** J1, J2
```

Rules:

- **Title = nav label = route title** (`ui-rules`' one-name rule); state it once, here.
- **Page type and surface come from `ux-patterns` §3**; a modal is written down only where the interruption is the value.
- **Every region names its four states.** A screen with a data region and no failed state is a design defect, not a build detail.
- **Data needed is written in the user's nouns**, resolved against the `## Data model` entities: this is the line `## API surface` turns into response fields, and the one place a screen can ask for an aggregate the tables do not store, so the API step decides computed-vs-stored deliberately.
- **Role differences live on the screen block**, never as a duplicate screen.
- **Every screen names its test ids:** the PascalCase dot-separated ids of its interactive elements and list containers, static and never carrying an index, id or state, per the stack's `test-ids` rules. The journey tests' page objects and the screen both bind to these names, which is what lets a journey test exist before its screen.
- **A delta block** is headed with the spec that defines the screen (`#### 007 S3 — My bookings — changed`) and holds only the changed lines: a new action, a new state, new test ids, a new data need.

### Step 5 — Rendering plan (web only)

**Rendering is decided per route, here, before any code.** Load [`references/rendering-strategy.md`](references/rendering-strategy.md) and run its decision procedure on every route this feature adds, and on every existing route whose content it changes: record the signals, the mode (`ssg` · `isr` · `ssr` · `ssr-streaming` · `csr`), the cache, the content that must be in the raw HTML, the islands and the deferred sections. Then write the `rendering_plan` block in that file's output contract under `### Rendering plan`.

- **An existing route keeps its mode** unless the procedure says otherwise; a change is an open question to the user, never a silent rewrite.
- **The default when signals conflict** is server-rendered first view plus islands; a route is `csr` only when it is signed-in **and** a long-session working tool.
- **A Vite SPA fits only when every route is `csr`.** One route that must be found by search puts the app on Next.js (or Blazor) with a route split, and that is a §3 question.
- **Reject any anti-pattern** in the file's last table before presenting the section.
- A mobile or desktop frontend writes `Rendering plan: n/a — native client`.

### Step 6 — Screen ↔ endpoint matrix

Filled by the API step once `## API surface` is written: one row per screen-endpoint pair this feature adds or changes.

| Screen | Endpoint | Purpose on this screen |
|---|---|---|
| S1 | `POST /api/v1/bookings/{bookingId}/cancel` | primary action |

Two checks run on it, and both are lines of `plan-feature`'s spec self-review: **every user-facing endpoint the feature adds appears on at least one screen** (one no screen calls is machine-to-machine, said so, or dead), and **every data-needed line resolves to an endpoint**.

### Step 7 — Cross-cutting

From `ux-patterns` §5–§9, only what this feature changes: **density** · **accelerators** · **notification surface** (inline + toast, or a notification centre because of which asynchronous events) · **first run**. Everything else is "per §3 / <spec>". The **responsiveness budget** is listed every time, as acceptance criteria the frontend tasks inherit verbatim.

---

## Section template

````markdown
## Experience

**Frontend agent:** `fe-react` | `fe-blazor` — per §3's areas · **Discipline:** `design:app-structure`

### Builds on
| What | Defined in | This feature |
|---|---|---|

### Actors and tasks
| Id | Actor | Task | Frequency | Stakes | Source |
|---|---|---|---|---|---|

### Navigation
**Shell:** per §3 (<the shell, one line>). <new or changed destinations, or "No destination added: …">

### Journeys
<one per primary task: numbered steps, screen + action + endpoint per step, step target, failure exit, acceptance>

### Screens
<one block per new screen, S1…Sn; one delta block per changed screen, headed with its spec>

### Rendering plan
**Pattern:** <route split | islands | streaming sections | SSR shell + client fetch | all csr> — <why, one line>
```yaml
rendering_plan:
  stack: <nextjs-app-router | vite-spa | blazor>
  routes: []   # one entry per added or changed route, per references/rendering-strategy.md's output contract
  acceptance: []
```

### Screen ↔ endpoint matrix
| Screen | Endpoint | Purpose on this screen |
|---|---|---|

### Cross-cutting
**Density:** … · **Accelerators:** … · **Notification surface:** … · **First run:** …
**Responsiveness budget (acceptance criteria for every frontend task):**
- [ ] every press acknowledged ≤ 100 ms (pressed state; submit disables with in-flight state)
- [ ] a region still loading at 300 ms shows a content-shaped skeleton, never a blank or page-centre spinner
- [ ] a region still loading at ~4 s says so; a timed-out region fails with retry, scoped to itself
- [ ] no layout shift on load; independent regions load independently

### Open questions
| # | Question | Owner |
|---|---|---|
````

## What NOT to put in the section

- **Mockups, colours, type, spacing:** the look is `design/visual-identity`'s and the tokens `design/design-tokens`'; the section says *detail page with a header and three regions*, not what it looks like.
- **Component names, file paths, library choices:** the `fe-<stack>` agent's Step-1 decision record; the section says the route *path* and the page *type*.
- **Copy:** labels and messages are `design/ux-writing`'s at build time; the section names the action ("Cancel booking") because the name is an IA decision, and stops there.
- **Endpoint bodies:** `## API surface`; this section says what the screen *needs*, in the user's nouns.
- **A screen per role:** role differences are lines on one screen block.

A test id is not a component name: `Test ids:` lines name the elements a person or a test touches, never the components that render them.

## Self-check before presenting the section

1. Every acceptance criterion with an outcome a person sees maps to ≥ 1 task and ≥ 1 journey; every task serves ≥ 1 screen.
2. Nothing §3 or an earlier spec defined is redefined: the shell is cited, and every changed screen is a delta block naming its spec.
3. Every new screen has route, page type, surface, primary action, regions with four states, a data-needed line resolved against `## Data model`, and a `Test ids:` line.
4. Every journey counts its steps against a stated target, names its failure exit and carries an `Acceptance:` line; no top-ranked task is at depth three.
5. After the API step: the matrix covers every user-facing endpoint the feature adds and every data need.
6. Web: every added or changed route has a `rendering_plan` entry with its signals, mode and cache; every non-`csr` route lists its `server_rendered_content`; no route shows an anti-pattern from `references/rendering-strategy.md`.
7. No `[TBD]` without an owner; no colour, component or copy decision leaked in.

## Version policy

Stack-agnostic: the section names the frontend agent from §3's areas and nothing version-bound; the agent's own version detection (React/Next major · Blazor render mode per TFM) governs the build.
