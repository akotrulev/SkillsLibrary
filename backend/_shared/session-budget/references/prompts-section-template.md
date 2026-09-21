# `## Prompts — one per task` — the paste-and-go section

The last section of the plan document, and the reason the document is queueable whole. It answers one
question — **what do I paste into a fresh session** — and it answers it as something runnable rather
than something to read. It lives **inside** the plan (`docs/plans/<NNN>-<initiative>/delivery-plan.md`,
or the single-file plan an `ep-writing-plans` run produced). There is no `NEXT-PROMPTS.md`.

**One block per task that has not landed.** No fewer: a task with no block is a session nobody knows
they can open. No more: **a landed task's block is deleted**, because a prompt for finished work is a
thing someone runs by mistake — and because the live prompt set is the plan's progress indicator.

**It is not the progress record.** That is the dated `**As built:**` note on each task block, the
header `**Status:**` line, and `## Decisions`. Those are append-only; this section is rewritten. Where
they disagree, the `As built` notes are right.

## The contract

| Rule | Why |
|---|---|
| **A block is a prompt, not a summary** | It is pasted verbatim into an empty session. Anything the session needs that is not in the block is something it will invent or go looking for |
| **One block names one task** | A block handing over two tasks gets half-done, and the second half is re-derived from scratch by whoever picks it up |
| **Sections, never whole artifacts** | `api-surface.md` §5.3, not `api-surface.md`. This is the single biggest lever on the budget holding — a session told to read the pack reads the pack |
| **Exact agent name, exact skill names** | The block is a binding, not a suggestion. An invented name is the most damaging defect here, same as in the plan |
| **Every block carries its traps** | The two to four things specific to that task. This is what the prompt adds to the task block, and it is what earns it its place |
| **Every block carries a gate line** | `Gate: none` with what not to run, on every block but the last runnable task's. That block carries the whole gate, in run order, and the instruction to fix what it finds |
| **Every block ends with the closing duty** | The `As built` note, the `Status:` line, delete this block, repair the ones below. Without it the section rots after the first session |
| **A blocked task keeps its block** | It states its blocker and its owner. A deleted block reads as finished work — and it would file a plan that is still waiting |
| **The block that deletes the last one files the plan** | Deleting it is what finishes the plan: `Status:` rewritten, then the plan moved to `docs/plans/implemented/`. Without that duty, finished plans sit in the live folder and it stops meaning anything |
| **A block that cannot be written yet is written by the task that unblocks it** | Guessing it produces the one kind of stale that reads as current |
| **The budget travels with the prompt** | The session about to spend the context should know what it was authored against |

## Template

`````markdown
## Prompts — one per task

Run them in order, one session each. Every block is complete on its own — it names the agent, the
skills, and the exact sections to read. **This plan gates once, in `<the last runnable task>`:** every
block before it says `Gate: none` and names what not to run. <Anything no prompt may do — "none of
them may start a real run; the user starts it.">

**Gates run <where>.** <Where to commit, and whether to ask before pushing.>

| # | Task | Epic | Story | Stack | Stream | Agent | Budget | Depends on |
|---|---|---|---|---|---|---|---|---|
| 1 | C1 | `E0` | — | `be` | `contract` | `be-dotnet` | ~120k | — |
| 2 | B1 | `E1` | `US3` | `be` | `timetable-api` | `be-dotnet` | ~112k | C1 |
| — | the sandbox credentials | — | — | `human` | — | **the user** | — | — |

**`<ids>` have landed, and their prompts are deleted** — a prompt for a finished task is a thing
someone runs by mistake. `<ids>` are live.

---

### B1 — <title> (<agent>, <stack>)

````
You are `<exact agent name>`. Task B1 of docs/plans/<NNN>-<initiative>/delivery-plan.md:
<the mission in one sentence>.

Read your agent definition, then load exactly these skills: `<skill>`, `<skill>`, `<skill>`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md, including <the rule that bites this task>.
2. The plan: §3 task B1 (your task block), §<n.n> of <artifact> — <what it gives you>, and
   §<n.n> — <…>.
3. <exact paths to the existing code this task must match> — <the seam, the convention, the sibling
   module, and why: "match them, do not introduce a second convention">.

Deliverable: <copied verbatim from the task block>.

Build:
- <the task's bullets, copied — the work and its checks>

Out of scope: <what belongs to a peer or a later task, named with its id and owner>.

Traps:
- <the convention that is easy to miss here>
- <the file that looks like the pattern but is not>
- <the down-level API that does not exist in this project's version lane>

Gate: none — this plan gates once, in `<the last runnable task>`. Do not run <the build, test, lint
and typecheck commands>. Write the tests; leave running them to that task.

Commit: `<the commit message>`.

Before you stop:
1. Write a dated `**As built:**` note onto task B1 with the `file:line` that proves the deliverable
   exists, and rewrite the plan's `**Status:**` line.
2. Delete this prompt block and update the "have landed" line above.
3. Repair the blocks below yours wherever what you landed differs from what they assume.
4. Write `<Bn>`'s prompt block — it was left `Blocked on B1`. <What B1 will then know that it needs.>
````

---

### F3 — <title> (<agent>, <stack>) — the last runnable task, so it carries the gate

````
You are `<exact agent name>`. Task F3 of docs/plans/<NNN>-<initiative>/delivery-plan.md:
<the mission>. **You are the plan's gate and its close-out.**

… (the same reading list / deliverable / build / traps shape) …

Gate (this is the last runnable task, so it carries the plan's only gate, in run order):
  <the project's own install, build, test, typecheck, lint and format commands>
**Fix what it finds rather than handing it back** — a failure may belong to any task above you, and
attributing it is part of this task. Say in your `As built` note which task each failure belonged to.

Close-out:
- <the docs this plan owes>, and the repository-state note.
- The honest list of what is built but **unverified**, into the plan's `**Status:**` line.
- **File the plan.** This deletes the last prompt block, so the plan is finished:
  `git mv docs/plans/<NNN>-<slug>.md docs/plans/implemented/` — or the whole initiative folder,
  artifacts and all — same name, same number, in this commit. (If `<blocked id>` is still holding a
  block, do **not** move it: say so in `Status:` and leave the plan in `docs/plans/`.)

Commit: `<the commit message>`.
````

---

### B4 — <title>

**Blocked on B2** — B2 writes this prompt when it lands, from the file layout and the exported type
names it actually settles on. Writing it is a bullet on B2 and a line in B2's closing duty.

---

### H1 — <title> (the user)

**Blocked on** the SendGrid sending domain being verified (`integrations.md` §5) — owned by the studio
owner, since 2026-08-04. Nothing to start here until that clears.
`````

## Filled example

The **workshop-booking** pack, caught after the contract wave has landed:

`````markdown
## Prompts — one per task

Run them in order, one session each. Every block is complete on its own. **This plan gates once, in
F4:** every block before it says `Gate: none`. No prompt may run `dotnet test` — F4 runs the suite for
the whole plan and fixes what it catches.

**Gates run locally.** Commit locally; ask before `git push`.

| # | Task | Epic | Story | Stack | Stream | Agent | Budget | Depends on |
|---|---|---|---|---|---|---|---|---|
| 1 | H1 | — | — | `human` | — | **the user** | — | — |
| 2 | C1 | `E0` | — | `be` | `contract` | `be-dotnet` | ~120k | — |
| 3 | B1 | `E1` | `US3` | `be` | `timetable-api` | `be-dotnet` | ~112k | C1 |
| 4 | B2 | `E3` | `US9` | `be` | `profile` | `be-dotnet` | ~95k | C1 |
| 5 | F4 | `E1` | `US3` | `fe` | `timetable-ui` | `fe-react` | ~150k | B1, B2 |

**H1 and C1 have landed, and their prompts are deleted.** B1, B2 and F4 are live.

---

### B1 — the Timetable resource (be-dotnet, be)

````
You are `be-dotnet`. Task B1 of docs/plans/003-workshop-booking/delivery-plan.md: implement the
Workshops and Sessions resources so a studio admin can publish a workshop and add sessions to it.

Read your agent definition, then load exactly these skills: `be-dotnet-pattern-writer`,
`be-dotnet-database-code`, `be-dotnet-unit-testing`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md, including the Backend code rules and the Comments rules.
2. The plan: §3 task B1; `api-surface.md` §5.1–§5.2 (the Workshops and Sessions endpoint blocks);
   `api-surface.md` §4 (the standard validation set — the deltas are in §5.1/§5.2);
   `data-model.md` §2.1–§2.2 (the `Workshop` and `Session` entity specs).
3. `src/Shared/IEndpointModule.cs` and `src/Shared/ProblemDetailsMiddleware.cs` — the seam and the
   error envelope C1 built. Match them; do not introduce a second convention.

Deliverable: a studio admin can publish a workshop, add sessions to it, and see them listed; nobody
else can.

Build:
- Create `src/Scheduling/Domain/Workshop.cs`, `Domain/Session.cs`, `SchedulingService.cs`,
  `SessionEndpoints.cs`, `SchedulingConfiguration.cs`; modify `src/Scheduling/DependencyInjection.cs`.
- Every endpoint matches `api-surface.md` §5.1–§5.2 exactly: paths, request/response fields, status
  codes.
- The standard validation set applies; the two deltas (`session-overlaps`,
  `workshop-not-published`) return their documented `type` slugs.
- A non-admin token gets 403 on every write; reads are public, per §5.1's auth column.
- Sessions register through `IEndpointModule` — no edit to `src/Api/Program.cs`.
- Unit tests in `tests/Scheduling.Tests/SchedulingServiceTests.cs` cover every validation branch and
  the publish state transition. In-process: no `WebApplicationFactory`, no container, no real DB.

Out of scope: the timetable and admin screens (F4, `fe-react`), contract and integration tests
(`qa-api-dotnet`), the booking side of a session's capacity (B3).

Traps:
- `Session` overlaps are checked in local studio time, not UTC — `data-model.md` §2.2 says why, and
  the existing `src/Shared/StudioClock.cs` is how.
- `ProblemDetailsMiddleware` already owns the envelope. Returning `BadRequest(new { error })` from an
  endpoint bypasses it and produces a second error shape.
- This project is on .NET 8, not 10: no `[FromServices]`-free minimal-API injection.

Gate: none — this plan gates once, in F4. Do not run `dotnet build`, `dotnet test` or
`dotnet format`. Write the tests; leave running them to F4.

Commit: `feat: workshops and sessions resources (B1)`.

Before you stop:
1. Write a dated `**As built:**` note onto task B1 with the `file:line` that proves an admin can
   publish and add, and rewrite the plan's `**Status:**` line.
2. Delete this prompt block and update the "have landed" line above.
3. Repair B2's and F4's blocks wherever what you landed differs from what they assume — F4 binds to
   the response field names, so a rename there is a rewrite here.
````
`````

## Writing rules

- **Write the block from the task, not from memory of the task.** Its deliverable, files, bullets and
  out-of-scope are copied from the task block. A block that paraphrases drifts, and the session trusts
  the block.
- **Name the sections you actually checked exist.** A prompt pointing at `api-surface.md` §5.7 when the
  artifact stops at §5.4 sends the session hunting, and it will read the whole file to find it.
- **Cite existing code the task must match**, with paths — the seam, the convention, the sibling
  module. This is what stops a session inventing a second way of doing something the repo already does,
  and it is the cheapest few thousand tokens in the block.
- **The traps are per-task, not a house-rules recital.** "Follow CLAUDE.md" is not a trap. "This
  project is on .NET 8, so the API you would reach for does not exist" is.
- **The gate line is on every block.** The most expensive violation of this format is an intermediate
  block that tells its session to run the suite: it pays for a verify loop whose failures belong to
  tasks nobody has written yet, and it reports a red tree as its own failure.
- **When the next task binds to a different agent, say so in the closing duty.** The agent writing the
  repair is not the agent who will run it, and a block that quietly changes hands is one nobody adopts.
- **The filing duty goes on whichever block will be the last.** Normally that is the gate task's, but a task that was blocked on a person outlives it — then the duty is on *that* block, and the gate task's says the plan stays in `docs/plans/` until it clears. Getting this wrong leaves a finished plan in the live folder, or files one that is still waiting.
- **Partial / blocked / diverged keeps the block on the same task**, with a `**Picking up from:**` line
  naming what remains and where inside the task to start. The task's unfinished bullets are that list.
