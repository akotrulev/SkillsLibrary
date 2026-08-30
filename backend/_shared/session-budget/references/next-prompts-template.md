# `NEXT-PROMPTS.md` — the paste-and-go file

One file per initiative, living beside the plan at `docs/plans/<NNN>-<initiative>/NEXT-PROMPTS.md`. It answers one question — **what do I paste into a fresh session right now** — and it answers it as something runnable rather than something to read.

**One block per lane that is runnable right now.** No more: a lane whose dependencies are unmet has no block, because a prompt for work that cannot start is a session someone wastes. No fewer: a runnable lane with no block is a session nobody knows they can open, and that is the whole cost of a wave table nobody acts on. `epic-map.md`'s current wave says which lanes those are.

**It is not the progress record and not the plan.** Status, evidence, ticked criteria, the execution log, decisions and deviations live in `delivery-plan.md` (§2, §3, §6, §7). This file is rewritten as each task lands and holds only what is next. Where the two disagree, the plan is right.

## The contract

| Rule | Why |
|---|---|
| **A block is a prompt, not a summary** | It is pasted verbatim into an empty session. Anything the session needs that is not in the block is something it will invent or go looking for |
| **One block names one task** | A block handing over two tasks gets half-done, and the second half is re-derived from scratch by whoever picks it up |
| **Sections, never whole artifacts** | `api-surface.md` §5.3, not `api-surface.md`. This is the single biggest lever on the estimate holding — a session told to read the pack reads the pack |
| **Exact agent name, exact skill names** | The block is a binding, not a suggestion. An invented name is the most damaging defect here, same as in the plan |
| **Every block ends with the closing duty** | Update `delivery-plan.md`, then rewrite this block for the next task. Without it the file rots after the first session |
| **Rewritten, never appended** | History lives in `delivery-plan.md` §6. An appended file becomes an archive with the current answer buried in it |
| **A blocked lane keeps its block** | It states its blocker and its owner. A deleted block reads as a finished lane |
| **The estimate travels with the prompt** | The session that is about to spend the context should know the budget it was authored against |

## Template

```markdown
# <Initiative> — Next Prompts

**Updated:** YYYY-MM-DD · **Updated by:** `<agent that last finished a task>` · **Plan:** `./delivery-plan.md`
**Wave:** <n> of <n> (`epic-map.md` §3) · **Lanes open:** <n>

> Paste one block below into a fresh session. Each block is complete — it names the agent, the skills,
> and the exact sections to read. Progress, evidence and decisions live in `delivery-plan.md` §2/§3/§6/§7;
> this file only says what to run next, and it is rewritten as each task lands.

---

## Lane `<lane-id>` — <epic id> <epic title>  ·  <task id>

<!-- everything from here to the next `---` is the prompt: pasted verbatim, nothing above it -->

You are **`<exact agent name>`**. Read your agent definition, then load exactly these skills:
`<skill>`, `<skill>`, `<skill>`.

**Read only these sections** — not the whole artifacts:
- `docs/plans/<NNN>-<initiative>/delivery-plan.md` §3, task `<Tn>` — your task block
- `docs/plans/<NNN>-<initiative>/<artifact>.md` §<n.n> — <what it gives you, in a few words>
- `docs/plans/<NNN>-<initiative>/<artifact>.md` §<n.n> — <…>

**Deliverable:** <the one observable thing that exists when you are done, copied from the task block>

**Files:**
- Create: `<path>`, `<path>`
- Modify: `<path>`

**Acceptance criteria:**
- [ ] <criterion, citing the pack by section>
- [ ] <criterion>
- [ ] `<the project's own build command>` clean; `<the project's own test command>` green

**Out of scope:** <what belongs to a peer or a later task, named with its owner>

**Est. context:** ~<n>k — <the drivers>

**When the task is done, before you report:**
1. `delivery-plan.md` — §2 status + `file:line` evidence, §3 criteria ticked in place, one append-only §6 row,
   and §7 if anything was built differently from the plan.
2. Rewrite this lane's block in `NEXT-PROMPTS.md` for `<the next task in this lane>`, per
   `be-shared-session-budget` Step 4. If `<Tn>` was this lane's last task, replace the block with a
   closed-lane line and check `epic-map.md` §3 — a finished lane usually opens a wave, and every lane
   that just became runnable needs a block.

---

## Lane `<lane-id>` — blocked

**`<Tn>` — <title>** is blocked on <what>, owned by <who>, since <YYYY-MM-DD>.
Nothing to start in this lane until that clears.

---
```

## Filled example

The **workshop-booking** pack (the shared example initiative), caught at the start of wave 2 — `E0` has landed, so two lanes opened at once. The `email` lane is in the file too, blocked, because a lane with nothing startable is worth one line.

```markdown
# Workshop Booking — Next Prompts

**Updated:** 2026-08-06 · **Updated by:** `be-dotnet` · **Plan:** `./delivery-plan.md`
**Wave:** 2 of 4 (`epic-map.md` §3) · **Lanes open:** 2

> Paste one block below into a fresh session. Each block is complete — it names the agent, the skills,
> and the exact sections to read. Progress, evidence and decisions live in `delivery-plan.md` §2/§3/§6/§7;
> this file only says what to run next, and it is rewritten as each task lands.

---

## Lane `timetable-api` — E1 Timetable  ·  T10

You are **`be-dotnet`**. Read your agent definition, then load exactly these skills:
`be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`.

**Read only these sections** — not the whole artifacts:
- `docs/plans/003-workshop-booking/delivery-plan.md` §3, task `T10` — your task block
- `docs/plans/003-workshop-booking/api-surface.md` §5.1–§5.2 — the Workshops and Sessions endpoint blocks
- `docs/plans/003-workshop-booking/api-surface.md` §4 — the standard validation set (the deltas are in §5.1/§5.2)
- `docs/plans/003-workshop-booking/data-model.md` §2.1–§2.2 — the `Workshop` and `Session` entity specs
- `src/Shared/IEndpointModule.cs` and `src/Shared/ProblemDetailsMiddleware.cs` — the seam and the error
  envelope T9 built; match them, do not introduce a second convention

**Deliverable:** a studio admin can publish a workshop, add sessions to it, and see them listed; nobody else can.

**Files:**
- Create: `src/Scheduling/Domain/Workshop.cs`, `src/Scheduling/Domain/Session.cs`
- Create: `src/Scheduling/SchedulingService.cs`, `src/Scheduling/SessionEndpoints.cs`,
  `src/Scheduling/SchedulingConfiguration.cs`
- Create: `tests/Scheduling.Tests/SchedulingServiceTests.cs`
- Modify: `src/Scheduling/DependencyInjection.cs`

**Acceptance criteria:**
- [ ] Every endpoint matches `api-surface.md` §5.1–§5.2 exactly: paths, request/response fields, status codes
- [ ] The standard validation set applies; the two deltas (`session-overlaps`, `workshop-not-published`)
      return their documented `type` slugs
- [ ] A non-admin token gets 403 on every write; reads are public per §5.1's auth column
- [ ] Sessions register through `IEndpointModule` — no edit to `src/Api/Program.cs`
- [ ] Unit tests cover every validation branch and the publish state transition
- [ ] `dotnet build` clean, 0 warnings; `dotnet test` green

**Out of scope:** the timetable and admin screens (`T16`, lane `timetable-ui`, wave 3), contract and
integration tests (`qa-api-dotnet`), the booking side of a session's capacity (`T11`, lane `booking`).

**Est. context:** ~112k — 6 files created, 1 modified, 3 skills, 4 pack sections, 2 existing files read

**When the task is done, before you report:**
1. `delivery-plan.md` — §2 status + `file:line` evidence, §3 criteria ticked in place, one append-only §6 row,
   and §7 if anything was built differently from the plan.
2. Rewrite this lane's block in `NEXT-PROMPTS.md` for `T12` (the OpenAPI asset), per
   `be-shared-session-budget` Step 4. If `T10` was this lane's last task, replace the block with a
   closed-lane line and check `epic-map.md` §3 — a finished lane usually opens a wave, and every lane
   that just became runnable needs a block.

---

## Lane `profile` — E3 Member profile  ·  T20

You are **`be-dotnet`**. Read your agent definition, then load exactly these skills:
`be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`.

**Read only these sections** — not the whole artifacts:
- `docs/plans/003-workshop-booking/delivery-plan.md` §3, task `T20` — your task block
- `docs/plans/003-workshop-booking/api-surface.md` §5.4 — the Members endpoint block
- `docs/plans/003-workshop-booking/data-model.md` §2.4 — the `Member` entity spec
- `src/Shared/IEndpointModule.cs` — the registration seam

**Deliverable:** a member can read and update their own profile, and cannot read anyone else's.

**Files:**
- Create: `src/Membership/Domain/Member.cs`, `src/Membership/MembershipService.cs`,
  `src/Membership/MemberEndpoints.cs`, `src/Membership/MemberConfiguration.cs`
- Create: `tests/Membership.Tests/MembershipServiceTests.cs`
- Modify: `src/Membership/DependencyInjection.cs`

**Acceptance criteria:**
- [ ] Both endpoints match `api-surface.md` §5.4 exactly: paths, fields, status codes
- [ ] A member requesting another member's profile gets 404, per the API's disclosure choice in §5.4
- [ ] The email field is immutable through this surface — the documented `field-immutable` slug on attempt
- [ ] Unit tests cover the ownership check and every validation branch
- [ ] `dotnet build` clean, 0 warnings; `dotnet test` green

**Out of scope:** the profile screen (`T21`, same lane, next task), Auth0 user-metadata sync (`T22`),
contract tests (`qa-api-dotnet`).

**Est. context:** ~95k — 5 files created, 1 modified, 3 skills, 2 pack sections, 1 existing file read

**When the task is done, before you report:**
1. `delivery-plan.md` — §2 status + `file:line` evidence, §3 criteria ticked in place, one append-only §6 row,
   and §7 if anything was built differently from the plan.
2. Rewrite this lane's block in `NEXT-PROMPTS.md` for `T21` (the profile screen — note it binds to
   `fe-react`, not to you), per `be-shared-session-budget` Step 4.

---

## Lane `email` — E4 Confirmation email — blocked

**`T13` — Email sender (SendGrid + Mailpit lane)** is blocked on `T0.2` — the SendGrid sending domain
is not verified (`integrations.md` §5) — owned by the studio owner, since 2026-08-04.
It also waits on `T11` (lane `booking`, wave 3) for the `BookingConfirmed` event it subscribes to.
Nothing to start in this lane.

---
```

## Writing rules

- **Write the block from the task, not from memory of the task.** Its deliverable, files, criteria and out-of-scope are copied from `delivery-plan.md` §3. A block that paraphrases drifts, and the session trusts the block.
- **Name the sections you actually checked exist.** A prompt pointing at `api-surface.md` §5.7 when the artifact stops at §5.4 sends the session hunting, and it will read the whole file to find it.
- **Cite existing code the task must match**, with paths — the seam, the convention, the sibling module. This is what stops a session inventing a second way of doing something the repo already does, and it is the cheapest few thousand tokens in the block.
- **The next-task pointer in the closing duty is specific.** `T12`, not "the next task". The agent finishing `T10` should not have to re-derive the lane order.
- **When the next task binds to a different agent, say so in the closing duty.** The agent writing the block is not the agent who will run it, and a block that quietly changes hands is one nobody adopts.
- **A lane's last task closes the lane and checks the wave.** That check is how wave 2 ever starts; without it the file stalls at the wave it was written in.
- **`Partial` / `Blocked` / `Diverged` keeps the block on the same task**, with a `**Picking up from:**` line naming what remains and where inside the task to start. The unticked criteria in `delivery-plan.md` §3 are that list.
