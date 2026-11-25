# The system plan format

**Contents:**

- 1. Path and number
- 2. The header
- 3. The sections, in order
- 4. The feature task block
- 5. ## Prompts — one per feature
- 6. Living text and filing
- 7. Never in a system plan
- 8. The close-out every feature runs
- 9. A filled example

The shape of the one file `/product:plan-system` writes for a whole system, in a new or an existing
repo: the vision, a thin technical skeleton, the epics and a flat list of features in the suggested
order of implementation, each with a prompt that runs `/product:plan-feature`. Plan Queue reads the
file as it reads any plan and runs one feature at a time, top to bottom. Each feature's session
interviews the user until no question about the feature is open, writes the feature's implementation
plan, and writes its result back here.

It is modelled on the implementation plan format,
[`plan-format.md`](../../writing-plans/references/plan-format.md). The same rules hold where this file
says nothing: one self-contained file with no companion, the narrative before the work, `Decisions`
with their costs, a maintained `**Status:**` line, append-only `As built` notes, living prompts, and
filing into `docs/plans/implemented/`. **What differs is the point of this file:**

| | Implementation plan | System plan |
|---|---|---|
| Unit of work | A task, one stack, one agent, one session | A feature, one interview session, any number of stacks |
| Task block | `Stack`, `Agent`, `Budget`, `Gate` | `Epic`, `Command`, `Deliverable`, `Depends on`, `Brief`; no `Stack`, `Agent`, `Budget` or `Gate` |
| Prompts heading | `## Prompts — one per task` | `## Prompts — one per feature` |
| A prompt's heading | `### <id> — <title> (<agent>, <stack>)` | `### F<n> — <title>`, no agent: the session runs the skill itself |
| A prompt's first lines | `Depends on: <ids>`, then `Agent: <agent> · Stack: <stack>` | `Depends on: <id>`, then `Skill: /product:plan-feature F<n> of <path> — <title>` |
| Queued by Plan Queue | Yes, in parallel where `Depends on:` allows | Yes, one feature at a time: each task is an interview the user answers in its session |
| Close-out section | `## Close-out — every task` | `## Close-out — every feature` |
| Done when | Every task's work is committed | Every feature has a committed spec and an implementation plan with no open question |

Four skills write its numbered sections, and `solution-planner` assembles them:

| Section | Written by |
|---|---|
| §2 Vision and scope | `product/skills/ba-scoping-writeup` |
| §3 The skeleton | `product/skills/solution-blueprint`, with the template [`skeleton-template.md`](skeleton-template.md) |
| §4 Epics | `product/skills/ba-epic-writer` |
| §5 Features side by side | `product/skills/epic-map` |

---

## 1. Path and number

**`docs/plans/<NNN>-<system>-system.md`** under the target project's root, never the skills-library
checkout and never a global directory. `<system>` is a short kebab-case noun phrase (`workshop-booking`).
The `-system` suffix is what the rule file `system-plans.md` keys on, and what tells a reader that the
file's tasks are interviews, not builds.

`NNN` is zero-padded and takes the high-water mark across `docs/plans/` **and**
`docs/plans/implemented/`, files and folders alike, as any plan does. A number is never reused.

The specs and implementation plans the features produce live where they always do,
`docs/specs/` and `docs/plans/`, each with a number of its own. Each feature's `As built` note links
them. There is no initiative folder.

## 2. The header

```markdown
# NNN — <System> — system plan (YYYY-MM-DD)

**Goal:** <what the system is for and who it serves, in one to three sentences.>

**Status:** <features specced (with their plan numbers), features on hold, the next feature to run,
and what is unverified.>

**Mode:** NEW | EXISTING | EXTEND — <what settled it>
```

- **`**Status:**` is maintained, not written once.** Every feature session rewrites it in place. Name
  which features are specced and planned, which are on hold and why, and which feature is next. "F1
  specced and planned (plan 022); F3 on hold; next F2" is the useful form.
- **`**Mode:**`** is how `solution-planner` entered: NEW (no meaningful code), EXISTING (code, no
  system plan) or EXTEND (this file already existed and gained features).

## 3. The sections, in order

| Section | Holds | Written from |
|---|---|---|
| Header | As §2 above | — |
| `## 1. What already exists, and what is missing` | `\| Need \| Today \| Gap \|`, one row per capability the system needs. In an existing repo `Today` cites `file:line`. A capability already built is a row with no gap and no feature. On a greenfield system `Today` is `—`, and the table is still written | the code |
| `## 2. Vision and scope` | The ask verbatim, the product in plain words (its journeys, each naming its features, and the choices the decision-maker is asked), the problem, actors and their goals, the decision-maker, what it must do with its quality targets, constraints, success measures, in / out / deferred, assumptions, risks | `ba-scoping-writeup` |
| `## 3. The skeleton` | Stack and versions (`detected` / `stated` / `proposed`), architecture style, functional areas with their file trees and agents, auth, the shared entities (name, owner, one line each), cross-cutting conventions | `solution-blueprint` |
| `## 4. Epics` | `E1…En`: a goal sentence each, a plain-English line, and the features that serve it | `ba-epic-writer` |
| `## 5. Features side by side` | `\| Feature \| Epic \| Areas and trees \| Depends on \| Refined beside \| Built beside \|` | `epic-map` |
| `## Decisions` · `## Answered questions (YYYY-MM-DD)` · `## Open questions` | As in `plan-format.md` §2: `D1…Dn` with what each costs, `O1…On` one line each, and the open-questions table `\| # \| Question \| Options \| Blocks \| Owner \|` | the interview |
| `## 6. Features` | One task block per feature, flat, `F1…Fn`, in the suggested order of implementation (§4 below) | — |
| `## Close-out — every feature` | The write-back duties every feature session runs, copied verbatim from §8 below | this file |
| `## Prompts — one per feature` | The feature table, then one prompt block per feature not yet specced (§5 below) | — |

- **§1 grounds everything.** Every feature traces to a row of it, and a row with a gap is covered by
  at least one feature.
- **§2 to §5 are read by every feature session.** Keep each one to what a feature designer needs:
  §3 especially is what every feature binds to, not a design of any feature.
- **`## Decisions` is the system's decision log.** The interview's decisions go here first; each
  feature session appends what its spec decided that changes §3.
- **No grouping layer sits over the features**, exactly as over a plan's tasks: not phases, waves,
  stages or milestones. §5 says what can run side by side; the list itself is flat.

## 4. The feature task block

````markdown
### F3 — Booking cancellation

**Epic:** E2 · **Command:** `/product:plan-feature`
**Deliverable:** an approved spec in `docs/specs/` and its implementation plan in `docs/plans/`, no question left open, both committed.
**Depends on:** F1 (the member entity and auth).
**Brief:** <one paragraph: what it does and for whom, what is in and out, and the skeleton decisions
(§3) it builds on.>
````

- **The features are listed in the suggested order of implementation**, and that is the order the
  queue runs them in: each feature is specced, then built, before the one below it needs it. The order is decided
  by three tests, in turn: the foundation feature first; a feature below everything it depends on;
  and among features free at the same point, the one that gives a person something usable soonest,
  the epic the decision-maker ranks highest first. §6's blocks, the prompt table and the prompt blocks
  all hold this one order.
- **Ids are `F1…Fn`, assigned in that order when the plan is written**, never renumbered. A feature
  the interview splits in two keeps its id for the first half; the second half gets the next free `F`
  id. In EXTEND mode new features take the next free ids after the highest one in the file. A block
  added later is placed where the feature is to be built, whatever its id.
- **No `Stack`, `Agent`, `Budget` or `Gate` line.** The session is the user's interview, and the
  implementation plan it produces carries those lines on every task it holds.
- **The `**Deliverable:**` is a plan ready to implement.** The session asks until every question about
  the feature is answered, the rows of `## Open questions` that block it included, and writes the
  implementation plan only then. A feature the user cannot finish answering goes on hold with no plan.
- **`**Epic:**`** names the one epic in §4 the feature serves. The foundation feature serves none and
  says `**Epic:** — (foundation)`.
- **`**Depends on:**`** points backwards only and names what it waits on in a few words, the same edge
  as §5. A feature whose spec needs a decision another feature makes depends on it.
- **The `**Brief:**`** is written so the feature session starts without reading the whole plan: what
  the feature lets someone do, what is in and what is deliberately out (naming the feature that owns
  it), and which §3 decisions and shared entities it builds on.
- **The foundation feature.** In a repo where the skeleton is not built yet, `F1` is the foundation:
  the scaffold, the auth wiring, the telemetry base, CI and the shared entities from §3. Every other
  feature depends on it. In an existing repo where the skeleton exists, there is no foundation feature
  and §1 says so.
- **Notes are appended, never edited.** A feature session appends
  `**As built (YYYY-MM-DD):** spec <path>, plan <path>` when it finishes, or
  `**On hold (YYYY-MM-DD):** <reason> — spec draft <path>` when the user puts it on hold (§8).

## 5. `## Prompts — one per feature`

The last section, and the one Plan Queue reads. It scans a plan for a `## Prompts` heading and takes
one task per `###` heading inside it, so the shape below is fixed. It opens with a short preamble: the
queue runs one block at a time, top to bottom, which is the suggested order of implementation; a block
runs the feature's interview, spec and plan; a block pasted into a fresh session does the same. Then
the feature table, in the same order:

```markdown
| # | Feature | Epic | Depends on | Refined beside | State |
|---|---|---|---|---|---|
| F1 | Foundation | — | none | — | specced (plan 022) |
| F2 | Booking a seat | E1 | F1 | F3 | live |
| F3 | Booking cancellation | E2 | F1 | F2 | on hold |
```

`State` is `live`, `specced (plan <NNN>)` or `on hold`. Then one line saying which prompts are gone,
then `---`, then one block per feature that is live or on hold.

**The heading is `### F<n> — <title>`**, with no trailing parenthetical: the queue reads one as the
agent to start, and a feature session runs as itself. The body follows after one blank line, fenced in
four backticks:

````markdown
Depends on: F2
Skill: /product:plan-feature F3 of docs/plans/004-workshop-booking-system.md — Booking cancellation

Run the `product:plan-feature` skill for F3 of this system plan: load it with the Skill tool and follow
it in SYSTEM mode. This task is an interview. Ask every round with AskUserQuestion and wait for the
answers; never settle a question for the user, whatever a queue's note about making the call says.

Members cancel their own bookings and staff cancel anyone's. In: cancellation, the refund rule, the
notification. Out: waiting lists (deferred). Builds on §3's Member and Booking entities and the Auth0
roles.

Read the system plan's §2, §3, §5, D1–D<n>, the open questions that block F3 and task F3 first. Close
out per its "Close-out — every feature" when the plan is written, or when the user puts F3 on hold.
````

- **Line 1 is `Depends on:` and one id: the block directly above**, or `Depends on: none` for the first
  block the plan was written with. It is the queue's order, not the feature's dependencies: every block
  waits on the one above it, so the interviews run one at a time, in the order of implementation. What
  a feature really waits on is its task block's `**Depends on:**` and §5. A block whose line names a
  feature already specced starts at once: the queue ignores an id the plan no longer has.
- **Line 2 is `Skill:`, the command, the id, the path and the title**, and nothing else.
  `/product:plan-feature` reads the id and the path from it.
- **Then the run paragraph, word for word**, with the feature's id in it. A queued session is told to
  make the call itself rather than ask; this paragraph is what makes the interview the task.
- **Then the brief**, copied from the task block, not paraphrased.
- **Then the reading line**, citing sections and decision ids, never the whole plan, and the close-out
  line.
- **Nothing else is a `###` inside `## Prompts`**, and nothing sits between a heading and its fence:
  the queue would list the first as a task and lose the second.
- **A feature on hold stops the queue at its block.** Mark it skipped in the queue to let the features
  below it run, and run it again when its question is answered.

## 6. Living text and filing

- **A feature's spec can change a later feature.** The session that settles something a later feature
  relies on (an entity it now owns, a convention it fixed, a part it moved out) rewrites that feature's
  brief and prompt block, in place, with no changelog appended.
- **A decision that changes §3** is appended to `## Decisions` as a dated `D<n>`, and the §3 line it
  changes is corrected in place, citing the `D<n>`. §3 always says what is true now; the decision log
  says when and why it changed.
- **A feature's prompt is deleted once its spec and plan are committed**, in a follow-up commit
  `docs: delete F<n>'s prompt (<system plan>)`. The live prompt set is the system's progress: what is
  left to spec is exactly what is still written down.
- **A feature on hold keeps its prompt.** Running it again resumes from the spec draft.
- **Where Plan Queue gives the plan a worktree and a branch**, each feature's spec and implementation
  plan are committed there, and reach the branch the system plan was cut from when the queue merges
  it: after the last feature is specced or skipped. The implementation plans are queued from then on,
  in the features' order. The system plan itself has to be committed before the queue can run it.
- **Filing.** The system plan moves to `docs/plans/implemented/`, same name and number, when its last
  prompt block is deleted. A plan with a feature on hold still has a block, so it stays in
  `docs/plans/`: moving it would hide the wait. A moved system plan is never edited; a system that
  grows again gets a new system plan in EXTEND mode, citing the old one.

## 7. Never in a system plan

- A feature block with a `Stack`, `Agent`, `Budget` or `Gate` line, or a feature that is a layer
  ("the API", "the screens") rather than something a person can do
- A per-feature design at system level: a table's columns, an endpoint list, a screen list, a key
  flow, an integration's retry policy. Those are the feature spec's
- A prompts heading other than `## Prompts — one per feature`, a prompt heading with a trailing
  parenthetical, or a block whose first line is not `Depends on:` and whose second is not the `Skill:`
  line
- A prompt's `Depends on:` line naming anything but the block directly above it, or `none`
- A feature with no epic and no `— (foundation)`, or an epic no feature serves
- A forward-pointing `Depends on`, a feature listed above one it depends on, or a renumbered `F` or
  `E` id
- A feature marked `specced` whose implementation plan holds an open question, or a row of
  `## Open questions` still naming a specced feature under `Blocks`
- A capability with a gap in §1 that no feature covers
- `TBD`, `TODO` or "decide later" without an owner and an open question
- A `**Status:**` line that does not say which features are specced, which are on hold and what is next
- A system plan left uncommitted: Plan Queue runs only what is committed

## 8. The close-out every feature runs

`/product:plan-feature` loads nothing the prompt does not name, so the write-back it owes the system
plan lives in the system plan itself, as a fixed section directly above the prompts, copied verbatim
from here:

````markdown
## Close-out — every feature

The session that `/product:plan-feature` runs for one feature does this before it stops, in this file.
Another feature session may be running beside you: re-read this file immediately before these edits,
and touch only your feature's task block and prompt block, the briefs and prompt blocks of later
features, `## Decisions`, §3 lines a decision changes, the `## Open questions` rows that block your
feature, `**Status:**`, the prompt table and the line above the blocks.

**When the implementation plan is written and committed.** It is written only when no question about
your feature is open: every row of `## Open questions` naming it under `Blocks` was put to the user and
answered, and the plan's own `## Open questions` is empty. A question the user cannot answer now puts
the feature on hold instead.

1. **As built** — append `**As built (YYYY-MM-DD):** spec <path>, plan <path>` to your feature's task
   block. Add any decision the spec made that changes §3, and append each one to `## Decisions` as a
   dated `D<n>`, correcting the §3 line it changes and citing the `D<n>`. Move each `## Open questions`
   row the interview answered to `## Answered questions` as `**O<n> — <question>: <answer>.**`, dated.
   Never edit an earlier note.
2. **Later features** — rewrite, in place, the brief and the prompt block of every later feature whose
   assumptions your spec changed. If the interview split your feature, give the second half the next
   free `F` id, its own task block, its rows in §5 and in the prompt table, and its own prompt block,
   each placed where the feature is to be built in the order of implementation.
3. **Status** — rewrite the header `**Status:**` line: the features specced and planned, the features
   on hold, the next feature to run. Set your row's `State` to `specced (plan <NNN>)`.
4. **Commit, then delete your prompt** — commit these edits with the spec and the plan, on the current
   branch, by path. Then delete your feature's prompt block and update the line above the blocks, in a
   follow-up commit `docs: delete F<n>'s prompt (<system plan>)`. If that leaves no block, rewrite
   `**Status:**` one last time and `git mv` this file into `docs/plans/implemented/`, same name, in the
   same commit, adding its row to that folder's README where there is one. When a queue says other
   tasks of this plan are running beside you, do not commit at all: make the deletion your last edit,
   and the queue commits everything together.

**When the user puts the feature on hold:**

1. **Draft** — write the answers so far into the spec draft in `docs/specs/`, with `**Status:** on hold`
   and the open question that stopped it.
2. **On hold** — append `**On hold (YYYY-MM-DD):** <reason> — spec draft <path>` to your feature's task
   block, set your row's `State` to `on hold`, and rewrite `**Status:**`. A question still open goes
   into `## Open questions` with your feature under `Blocks` and its owner.
3. **Keep the prompt** — leave the prompt block as it is, and commit the draft and these edits
   together. Running the prompt again resumes from the draft. When a queue runs this session, end
   with the line `PLAN_QUEUE: BLOCKED F<n> on hold: <reason>`, so the queue stops at your block
   instead of marking it done.
````

The section is the same in every system plan; a system plan does not edit it.

## 9. A filled example

A deliberately small greenfield system: a studio's workshop booking. Three features, one specced and
planned, one live, one on hold. The shapes are normative, the domain content illustrative.

`````markdown
# 004 — Workshop booking — system plan (2026-08-02)

**Goal:** Members of a pottery and drawing studio book and cancel seats in scheduled workshops
online, and staff stop keeping bookings in a spreadsheet.

**Status:** F1 specced and planned (plan 005). F3 on hold since 2026-08-09: the refund rule waits on
the owner's accountant. Next: F2. Unverified: nothing is built yet.

**Mode:** NEW — empty repo, one-page brief from the studio owner.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| Members sign in and the system knows who they are | — | F1 |
| A member books a seat in a published session | Phone calls and a spreadsheet | F2 |
| A member or staff cancels a booking within policy | Phone calls | F3 |

## 2. Vision and scope

### The ask, verbatim
> "I want people to book online instead of ringing me, and I never want two people in one seat."
> — studio owner, email of 2026-07-30

### The product, in plain words
Members book and cancel their own seats online, and staff see who is coming. It replaces the phone and
the spreadsheet; it takes no payments.

| Journey | Who | Does | Ends up with | Features |
|---|---|---|---|---|
| J1 | Member | Picks a session with room and books a seat | A seat, shown in their bookings | F1, F2 |
| J2 | Member or staff | Cancels a booking | The seat free for someone else | F3 |

**The owner is asked:** who may do what, the booking rules, what members are told. **Feature sessions
decide:** how it works inside, listed in each spec's engineering calls for review.

### Problem and why now
The owner spends about five hours a week on the phone and on the spreadsheet, and twice this year a
session was overbooked. The new term starts on 2026-09-15.

### Actors
| Actor | What they are trying to get done | Role |
|---|---|---|
| Studio owner | Stop running bookings by hand | decision-maker |
| Member | Get a seat in a session they want | primary user |
| Staff | Know who is coming, cancel for a member | primary user |

### What it must do
- A member books one seat in a published future session that has room.
- A member cancels their own booking; staff cancel anyone's.
- A session never holds more bookings than its capacity.
- Quality target: the schedule loads in under a second on a phone — stated by the owner.

### Constraints
- Live before the term starts on 2026-09-15 — stated by the owner.

### Success
- Bookings taken by phone fall from about 60 a month to under 10 within three months; the owner judges it.

### Scope
| In scope | Out of scope (refused) | Deferred (follow-up) |
|---|---|---|
| Booking and cancelling seats | Payments: sessions are in the membership | Waiting lists |

### Assumptions
1. Staff create members by invitation; nobody signs up on their own.

### Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Two members take the last seat at once | M | H | The seat limit is enforced by the database, not checked in code |

## 3. The skeleton

### Stack and versions
| Dimension | Choice | Version | Why | Evidence |
|---|---|---|---|---|
| Backend | .NET, ASP.NET Core minimal APIs | 10 | Greenfield; library default | proposed → approved |
| Frontend | React + TypeScript, Vite SPA | 19 | Library default | proposed → approved |
| Datastore | PostgreSQL | 18 | Relational fit; the seat limit is a constraint | proposed → approved |
| Hosting | Azure Container Apps | — | The owner already pays for Azure | stated |

### Architecture
**Style:** modular monolith, built to be split later. One team of two, one deployable, no split trigger met.
**Rejected:** a service per area: three network boundaries for one consumer.
**Repository layout:** one repo: `contracts/`, `src/` (one folder per module), `web/`, `deploy/local/`.

### Areas
| Area | Purpose | Serves | Trees | Agents |
|---|---|---|---|---|
| Foundation | Scaffold, config, auth wiring, telemetry base, CI, app shell | all | `src/Api/*`, `contracts/*`, `web/app/layout.tsx`, `.github/*` | `be-dotnet`, `fe-react`, `observability-engineer-dotnet`, `devops-engineer` |
| Membership | Who a member is | E1, E2 | `src/Membership/*` | `be-dotnet` |
| Booking | Seats, sessions, cancellations | E1, E2 | `src/Booking/*`, `web/app/bookings/*` | `be-dotnet`, `fe-react` |

### Auth
Auth0: Authorization Code + PKCE in the SPA, JWT bearer at the API. Roles `member` and `staff` from
the token's claims; every endpoint checks the role, and a member reads only their own bookings.

### Shared entities
| Entity | Owner area | One line |
|---|---|---|
| Member | Membership | A person who may book; keyed by the Auth0 `sub` (D3) |
| Session | Booking | A dated occurrence of a workshop with a seat capacity |
| Booking | Booking | One member's seat in one session |

### Cross-cutting conventions
| Concern | Convention |
|---|---|
| Error envelope | RFC 9457 problem details on every error |
| Ids | UUID v7, generated by the API |
| Pagination | Cursor-based, `?cursor=&limit=`, limit at most 100 |
| Tenancy | Single tenant: one studio, no tenant id anywhere |
| Telemetry base | OpenTelemetry to the local Grafana stack in `deploy/local/`, wired in F1 |
| App shell | Top nav: two actors, few areas |

## 4. Epics

| Epic | Goal | In plain English | Features |
|---|---|---|---|
| E1 | When this is done, **members** can **book a seat online** so that **phone bookings fall from about 60 to under 10 a month** | A member sees what is on and takes a seat without ringing anyone | F2 |
| E2 | When this is done, **members and staff** can **cancel a booking themselves** so that **freed seats are bookable again the same day** | Plans change; a member frees their seat, and staff can do it for them | F3 |

## 5. Features side by side

| Feature | Epic | Areas and trees | Depends on | Refined beside | Built beside |
|---|---|---|---|---|---|
| F1 Foundation | — | Foundation: `src/Api/*`, `contracts/*`, `web/app/layout.tsx`, `.github/*` | — | F2, F3 | — |
| F2 Booking a seat | E1 | Booking: `src/Booking/*`, `web/app/bookings/*` | F1 — the member entity and auth | F3 | — |
| F3 Booking cancellation | E2 | Booking: `src/Booking/*`, `web/app/bookings/*` | F1 — auth roles and the Booking entity | F2 | — |

F2 and F3 can be specced side by side: both bind to the Booking entity §3 fixes, so neither one's
decisions wait on the other's. They cannot be built side by side: both land in `src/Booking/*`.

## Decisions

**D1 — The seat limit is a database constraint, not a check in code.** Cost: the booking API maps a
constraint violation to a "session full" outcome.

**D2 — Members are created by staff invitation.** Cost: no self-signup until a later system plan.

**D3 (2026-08-05, F1) — A member is keyed by the Auth0 `sub`, not by an email.** Cost: a member who
changes identity provider is a new member.

## Answered questions (2026-08-02)

- **O1 — Can a member book more than one seat per session:** no, one seat each.

## Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| Q1 | Does a late cancellation refund the class credit? | A. always · B. only 24 h before | F3 | Studio owner |

## 6. Features

### F1 — Foundation

**Epic:** — (foundation) · **Command:** `/product:plan-feature`
**Deliverable:** an approved spec in `docs/specs/` and its implementation plan in `docs/plans/`, no question left open, both committed.
**Depends on:** —
**Brief:** The scaffold every feature builds on: the solution and module layout, config with startup
validation, the Auth0 wiring on both sides, the telemetry base, CI, the app shell with its top nav,
and the shared entities from §3. No booking behaviour.

**As built (2026-08-05):** spec `docs/specs/005-foundation-design.md`, plan `docs/plans/005-foundation.md`.
Added D3 (Member keyed by the Auth0 `sub`, not an email).

### F2 — Booking a seat

**Epic:** E1 · **Command:** `/product:plan-feature`
**Deliverable:** an approved spec in `docs/specs/` and its implementation plan in `docs/plans/`, no question left open, both committed.
**Depends on:** F1 (the Member entity and auth).
**Brief:** A member browses published future sessions and books one seat in a session with room; a
full session says so. Staff see who is booked. In: the schedule, booking, my bookings. Out:
cancelling (F3), waiting lists (deferred). Builds on §3's Member, Session and Booking entities and D1.

### F3 — Booking cancellation

**Epic:** E2 · **Command:** `/product:plan-feature`
**Deliverable:** an approved spec in `docs/specs/` and its implementation plan in `docs/plans/`, no question left open, both committed.
**Depends on:** F1 (auth roles and the Booking entity).
**Brief:** Members cancel their own bookings and staff cancel anyone's, and the seat is freed at once.
In: cancellation, the late-cancellation rule, the member's notification. Out: waiting lists. Builds on
§3's Booking entity and the `member` / `staff` roles.

**On hold (2026-08-09):** the refund rule for late cancellations waits on the owner's accountant (Q1)
— spec draft `docs/specs/006-booking-cancellation-design.md`.

## Close-out — every feature

<the section in §8 of the format, copied verbatim>

## Prompts — one per feature

Plan Queue runs one block at a time, top to bottom: the order of implementation. A block pasted into a
fresh session runs the same way. F2 is next; F3 waits for Q1.

| # | Feature | Epic | Depends on | Refined beside | State |
|---|---|---|---|---|---|
| F1 | Foundation | — | none | F2, F3 | specced (plan 005) |
| F2 | Booking a seat | E1 | F1 | F3 | live |
| F3 | Booking cancellation | E2 | F1 | F2 | on hold |

F1's prompt is deleted.

---

### F2 — Booking a seat

````
Depends on: F1
Skill: /product:plan-feature F2 of docs/plans/004-workshop-booking-system.md — Booking a seat

Run the `product:plan-feature` skill for F2 of this system plan: load it with the Skill tool and follow
it in SYSTEM mode. This task is an interview. Ask every round with AskUserQuestion and wait for the
answers; never settle a question for the user, whatever a queue's note about making the call says.

A member browses published future sessions and books one seat in a session with room; a full
session says so. Staff see who is booked. In: the schedule, booking, my bookings. Out: cancelling
(F3), waiting lists (deferred). Builds on §3's Member, Session and Booking entities and D1.

Read the system plan's §2, §3, §5, D1–D3, the open questions that block F2 and task F2 first. Close
out per its "Close-out — every feature" when the plan is written, or when the user puts F2 on hold.
````

### F3 — Booking cancellation

````
Depends on: F2
Skill: /product:plan-feature F3 of docs/plans/004-workshop-booking-system.md — Booking cancellation

Run the `product:plan-feature` skill for F3 of this system plan: load it with the Skill tool and follow
it in SYSTEM mode. This task is an interview. Ask every round with AskUserQuestion and wait for the
answers; never settle a question for the user, whatever a queue's note about making the call says.

Members cancel their own bookings and staff cancel anyone's, and the seat is freed at once. In:
cancellation, the late-cancellation rule, the member's notification. Out: waiting lists. Builds on
§3's Booking entity and the member / staff roles.

Read the system plan's §2, §3, §5, D1–D3, the open questions that block F3 and task F3 first. Close
out per its "Close-out — every feature" when the plan is written, or when the user puts F3 on hold.
````
`````
