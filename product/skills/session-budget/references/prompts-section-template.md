# `## Prompts — one per task` — the paste-and-go section

**Contents:**
- The contract
- Template
- Filled example
- Writing rules

The last section of the plan document, and the reason the document is queueable whole. It answers one
question — **what do I paste into a fresh session** — and it answers it as something runnable rather
than something to read. It lives **inside** the plan, the feature's implementation plan
(`docs/plans/<NNN>-<feature>.md`). There is no `NEXT-PROMPTS.md`.

**One block per task that has not landed.** No fewer: a task with no block is a session nobody knows
they can open. No more: **a landed task's block is deleted**, because a prompt for finished work is a
thing someone runs by mistake — and because the live prompt set is the plan's progress indicator.

**It is not the progress record.** That is the dated `**As built:**` note on each task block, the
header `**Status:**` line, and `## Decisions`. Those are append-only; this section is rewritten. Where
they disagree, the `As built` notes are right.

## The contract

| Rule | Why |
|---|---|
| **A block's second line is `Agent: <agent> · Stack: <stack>`** | The same pair as the heading's parenthetical. Plan Queue reads it to pick the agent, and a block pasted without its heading still says who runs it |
| **A block opens with `Depends on: <ids>`** | Ids only, comma-separated, or `none` — a program starts the task when those are done. It holds the task's prerequisites and every earlier task it shares files or a build tree with (a stream task adds its stream predecessor and cross-stream edges); a missing line is never relied on |
| **A block is a prompt, not a summary** | It is pasted verbatim into an empty session. Anything the session needs that is not in the block is something it will invent or go looking for |
| **One block names one task** | A block handing over two tasks gets half-done, and the second half is re-derived from scratch by whoever picks it up |
| **Sections, never whole artifacts** | The spec's `## API surface` endpoint block, not the spec. This is the single biggest lever on the budget holding — a session told to read the spec reads the spec |
| **Exact agent name, exact skill names** | The block is a binding, not a suggestion. An invented name is the most damaging defect here, same as in the plan |
| **Every block carries its traps** | The two to four things specific to that task. This is what the prompt adds to the task block, and it is what earns it its place |
| **Every block carries a gate line** | `Gate: own tests` with its filtered commands on every block that writes code or tests: a `Q` block expects red, any other expects green, and every block runs its own work and the work landed above it: the tests it wrote, the acceptance tests bound to its own deliverable, the tests of the landed tasks above it and the coverage floor over the files they touched, on a small core budget and ports of its own, never under the test lock, and never another plan's tests, the smoke suite or the unfiltered suite. `Gate: none` only on a block with nothing runnable, saying so. The last block carries the whole set, in run order, its fix loop, and the instruction to fix what it finds |
| **An implementation block in a test-first plan repeats the read-only rule** | The acceptance tests are the spec; a block that omits the rule invites the session to pass a test by editing it |
| **Every block ends with the close-out line** | `Close out per the plan's "Close-out — every task" before you stop.` — pointing at the section directly above this one, copied verbatim from plan format §7. Without it the section rots after the first session |
| **A blocked task keeps its block** | It states its blocker and its owner. A deleted block reads as finished work — and it would file a plan that is still waiting |
| **The block that deletes the last one files the plan** | Deleting it is what finishes the plan: `Status:` rewritten, then the plan moved to `docs/plans/implemented/`. Without that duty, finished plans sit in the live folder and it stops meaning anything |
| **A block that cannot be written yet is written by the task that unblocks it** | Guessing it produces the one kind of stale that reads as current |
| **The budget travels with the prompt** | The session about to spend the context should know what it was authored against |

## Template

`````markdown
## Close-out — every task

<copied verbatim from product/skills/writing-plans/references/plan-format.md §7 — never edited per plan>

## Prompts — one per task

Run them in order, one session each. Every block is complete on its own — it names the agent, the
skills, and the exact sections to read. **Every task gates its own work and the work landed above it:** each block's `Gate:` line
names its commands, and `<the last runnable task>` is the plan's one run under the test lock: the smoke suite plus every test the plan wrote, then the whole set once more. <Anything no prompt may
do — "none of them may start a real run; the user starts it.">

**What runs together:** <one line — "After C1, B1 → B2 run beside Q1; F1 waits for both; F2 runs the whole set." Tasks that run together share one working tree: each commits only its own files, by path, and re-reads the plan before its close-out edits.>

**Gates run <where>.** <Where to commit, and whether to ask before pushing.>

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| C1 | `be` | `be-dotnet` | none | — | ~120k |
| B1 | `be` | `be-dotnet` | C1 | — | ~112k |
| — | the sandbox credentials | **the user** | — | — | — |

**`<ids>` have landed, and their prompts are deleted** — a prompt for a finished task is a thing
someone runs by mistake. `<ids>` are live.

---

### B1 — <title> (<agent>, <stack>)

````
Depends on: <ids only, or none>
Agent: <exact agent name> · Stack: <stack>

You are `<exact agent name>`. Task B1 of docs/plans/<NNN>-<feature>.md:
<the mission in one sentence>.

Read your agent definition, then load exactly these skills: `<skill>`, `<skill>`, `<skill>`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md, including <the rule that bites this task>.
2. The plan: §3 task B1 (your task block); the spec `docs/specs/<NNN>-<feature>-design.md`:
   <its section and block> — <what it gives you>, and <…>.
3. <exact paths to the existing code this task must match> — <the seam, the convention, the sibling
   module, and why: "match them, do not introduce a second convention">.
4. The plan's "Close-out — every task".

Deliverable: <copied verbatim from the task block>.

Build:
- <the task's bullets, copied — the work and its checks>

Out of scope: <what belongs to a peer or a later task, named with its id and owner>.

Traps:
- <the convention that is easy to miss here>
- <the file that looks like the pattern but is not>
- <the down-level API that does not exist in this project's version lane>

Gate: own tests — before you commit, run `<the scoped build>` and `<the filtered tests you wrote>`, then
`<the filtered tests the landed tasks above you wrote>` and `<the coverage floor over the files you and those tasks touched>`,
then `<typecheck, lint and format over the files you touched>`. Run them on a small core budget
and ports of your own, never under the test lock: not another plan's tests, the smoke suite or the unfiltered suite. Leave them green, fixing what stands in the way whichever task
caused it, and name that task in `As built`. Do not run the unfiltered suite.
<A frontend or mobile block runs spec files — its own, its bound acceptance specs and the landed tasks' (usually a
few, on one or two workers, its own port, after the production build) instead of a backend's unit tests.>
<In a test-first plan, an implementation block also names, under Deliverable, the `Q` tests bound to its
own deliverable that it turns green, adds their filter to its commands (only those files), and carries the
read-only paragraph below, verbatim. A block with
nothing runnable, such as a docs-only task, says instead: `Gate: none — <why nothing here is runnable>.`>

The acceptance tests a `Q` task wrote are the spec, and they are **read-only** to every later task
except the gate. Never edit, skip, delete or weaken one: not its assertion, its data or its timeout. A
test you believe is wrong is a dated `D<n>` with both readings, and it stays red; the gate task
resolves it with the user.

Commit: `<the commit message>`.

<Which block below binds to what you land.> Write `<Bn>`'s prompt block — it was left
`Blocked on B1`. <What B1 will then know that it needs.>
Close out per the plan's "Close-out — every task" before you stop.
````

---

### TD1 — <title: the test plan for <the feature>> (qa-test-planner, qa)

````
Depends on: <the stub task's id; ids only>
Agent: qa-test-planner · Stack: qa

You are `qa-test-planner`. Task TD1 of docs/plans/<NNN>-<feature>.md: write the test
plan for <the feature>, one document, before the acceptance tests exist.

Read your agent definition, then load exactly these skills: `<qa-stack>:requirements-breakdown`,
`<qa-stack>:test-strategy`, `<qa-stack>:test-design-techniques`, `<qa-stack>:test-plan-writer`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md.
2. The plan: §3 task TD1; the spec `docs/specs/<NNN>-<feature>-design.md`: its goal and decisions,
   and `## Acceptance criteria` whole — the criteria are the scope items and the trace targets.
3. The spec's `## API surface` endpoint map and `## Experience` `### Journeys` <J ids> — what surfaces
   exist.
4. The repo, for the harness: the test projects and their manifests, the CI lane, the OpenAPI asset
   (its path is in <the stub task>'s `As built` note), any page objects and fixtures.
5. The plan's "Close-out — every task".

Deliverable: <copied verbatim from the task block — it names each plan file and what it holds>.

Build:
- One `docs/test-plans/<NNN>-<feature-slug>-test-plan.md`, in `test-plan-writer`'s shape: `Covers`
  (the spec) and plan version; §2 Versions; §3 scope closed over every acceptance criterion; §6–§7
  harness and existing automation as `detected` rows with paths; §10 a scenario for every AC, each with
  its executor; §11 the Definition of Ready and the Definition of Done.
- <the task's own bullets, copied>

Out of scope: the test cases with steps (<TD2>, `qa-test-case-designer`); the automated acceptance tests
(<the Q tasks>); editing the spec — a gap in a criterion is an open question in the test plan's §12
and a Definition-of-Ready line.

Traps:
- Versions are detected or stated, never guessed: the build under test is `[TBD — <who>]` until a build
  exists, and that is a Definition-of-Ready line, not a blank.
- Executors must be the agents this plan actually binds: a scenario for the API goes to
  <qa-api-stack>, a journey to <qa-ui-stack | qa-mobile-stack>, a manual case to `qa-test-case-designer`.
- <the per-task trap: the greenfield repo with no harness yet (rows are `proposed`, and say so), the
  `[TBD]` criterion, the platform matrix nobody has stated>

Gate: none — a test plan is a document; your step-5 review (scope closed, every AC traced, every executor
resolves, every Ready and Done line checkable) is the check.

Commit: `<the commit message>`.

Your `As built` note lists each plan's path, its scenario count by executor, and every open question.
Write into the `Q` blocks below the `TP-` rows each one automates — they were left unfilled for this reason.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### TD2 — <title: the test cases for <the feature>> (qa-test-case-designer, qa)

````
Depends on: <TD1; ids only>
Agent: qa-test-case-designer · Stack: qa

You are `qa-test-case-designer`. Task TD2 of docs/plans/<NNN>-<feature>.md: write the
test-case suite for <the feature>, from the spec's acceptance criteria and the test plan.

Read your agent definition, then load exactly these skills: `<qa-stack>:requirements-breakdown`,
`<qa-stack>:test-design-techniques`, `<qa-stack>:cross-feature-test-design`, `<qa-stack>:test-case-writer`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md.
2. The plan: §3 task TD2; the spec `docs/specs/<NNN>-<feature>-design.md`: `## Acceptance criteria`
   whole, and `## Experience` `### Journeys`.
3. The test plan — its path is in TD1's `As built` note: §2 versions and §8
   environment (they become each suite's Setup), §10 the `TP-` rows bound to `qa-test-case-designer`.
4. `docs/business-model/` for the feature's entities and decisions, where it exists.
5. The plan's "Close-out — every task".

Deliverable: <copied verbatim from the task block — it names the suites>.

Build:
- A basis `docs/test-cases/<NNN>-<slug>-basis.md` and a suite `docs/test-cases/<NNN>-<slug>.md`:
  journeys first (one per journey the spec describes), then rules and calculations, states,
  connections, fields last.
- Every case's `Source` carries the `AC<k>` it proves (the spec named once in the header) and its `TP-`
  row; every AC has a case.
- <the task's own bullets, copied>

Out of scope: executing the cases; automation (<the Q tasks>); Gherkin (`qa-bdd-<stack>`).

Traps:
- One suite per feature: a suite that covers two specs cannot be traced or re-run alone.
- An expected figure is computed from the spec's rule, with its working; a number the spec does not
  give is a question for the author, never invented.
- <the per-task trap>

Gate: none — a test-case suite is a document; your step-5 review and depth gate are the check.

Commit: `<the commit message>`.

Your `As built` note lists each suite's path, its case counts by layer, and any AC with no case and why.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### Q1 — <title> (<qa-api-stack | qa-ui-stack | qa-mobile-stack>, qa)

````
Depends on: <ids only, or none>
Agent: <exact qa agent name> · Stack: qa

You are `<exact qa agent name>`. Task Q1 of docs/plans/<NNN>-<feature>.md: write the
acceptance tests for <the resource group or journeys>, against the stubs, before the implementation.

Read your agent definition, then load exactly these skills: `<qa-stack>:test-first`,
`<qa-stack>:api-spec-assets`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md, including the Test code rules.
2. The plan: §3 task Q1; the spec `docs/specs/<NNN>-<feature>-design.md`: `## API surface` — the
   endpoint blocks this task tests; `docs/specs/validation-catalog.md` — the standard set (V8.6 is the
   stub response); `## Acceptance criteria` <AC ids> — each test is tagged `SPEC<NNN>-AC<k>`; for
   journeys, `## Experience` `### Journeys` <J ids> and the screens' `Test ids:` lines.
   Where the plan has `TD` tasks: the test plan's §10 — the `TP-` rows bound to you (the path is
   in the test-plan task's `As built` note); each test carries its `TP-` id beside its AC id.
3. The OpenAPI asset the contract task generated from the stubs — its path is in <the contract task>'s
   `As built` note — and the existing acceptance-test project, if any, as the fixture pattern.
4. The plan's "Close-out — every task".

Deliverable: <copied verbatim from the task block — it names the tests and their red reason>.

Build:
- <the task's bullets, copied — one test per endpoint outcome and per AC, each carrying its AC id>

Out of scope: <the implementation task that turns these green, with its id and agent>.

Traps:
- Red for the right reason: every test is red on `501 not-implemented` (in Arrange or in Act) or on the
  screen's placeholder. A test red on a `404`, a compile error or a wrong URL has a wiring defect — fix it
  before you stop. A test that passes against a stub asserts nothing.
- Never assert the stub, `501` or the placeholder text: bind to the generated client, the documented
  slugs and the agreed test ids, never to the service's code, which does not exist yet.
- <the per-task trap: the fixture that needs a token, the setup call that reaches a stub, the AC with no
  visible outcome on this surface>

Gate: own tests — before you commit, run `<the filtered command that runs the tests this task writes>`;
expect every test red, and record each one's red reason in `As built`. Do not run the unfiltered suite.
<A journey suite that cannot start its app in one command proves its tests load and list instead —
`<npx playwright test --list e2e/…>` — and the task that serves each journey turns it green.>

Commit: `<the commit message>`.

Your `As built` note lists each AC with no test and why, and each implementation task's own-tests filter
(the test classes or files per resource group or journey). Write those filters into the blocks of the
tasks below — they were left unfilled for this reason.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### F3 — <title> (<agent>, <stack>)

````
Depends on: <every task nothing else waits for>
Agent: <exact agent name> · Stack: <stack>

You are `<exact agent name>`. Task F3 of docs/plans/<NNN>-<feature>.md:
<the mission>. **You are the gate task, the last task that builds and runs code, so you run the whole set.**

… (the same reading list / deliverable / build / traps shape) …

Gate (this is the gate task, so it runs the whole set once more across the plan, in run order):
  <the project's own install, build, test, typecheck, lint and format commands>
  <the coverage floor — plan-format.md §5: the changed-file list from git, then each stack's
   coverage command; ≥ 80% of the branches the plan wrote (Swift: lines)>
**Fix what it finds rather than handing it back** — a failure may belong to any task above you, and
attributing it is part of this task. Say in your `As built` note which task each failure belonged to.
The fix loop: run the whole set once; reproduce each failure with `<the narrowest rerun — one spec, one
filter>`, fix it and see it green there; then `<the project's rerun-failed command>`; then the whole set
once more to close. Never rerun the whole set to check one fix. A failure that moves between runs is a
defect in isolation (shared data, test order) or in the gate's scheduling: fix it in the code, shared
setup you own or the gate script, never rerun until it happens to pass. Inside an acceptance test or
fixture a `Q` task wrote it is read-only: record a dated `D<n>` with both readings and leave the test.
The coverage floor is measured here, once, over the whole plan's change. A shortfall is fixed by writing the missing tests — never by excluding a file that has logic
or lowering the number; record the figure per stack and every file left out.

<Where the plan has `TD` tasks:> Check each test plan's §11 Definition of Done against what the run
showed, tick what holds, and name every item that does not in your `As built` note.

Write no product documentation: `DOC1` below does that from the code you leave. Your `As built` note
is its lead, so say what landed, where, and what is built but unverified. Merge the default branch
into the plan's branch (close-out step 6) so `DOC1` documents the merged code. `DOC1` files the plan.
<In a plan whose header says `Documentation task: none`, this block deletes the last one and files
the plan itself.>

Commit: `<the commit message>`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### DOC1 — <title: the documentation for <areas | features>> (<documenter | feature-documenter>, docs)

````
Depends on: <the gate task's id; ids only>
Agent: <documenter | feature-documenter> · Stack: docs

You are `<documenter | feature-documenter>`. Task DOC1 of
docs/plans/<NNN>-<feature>.md, the plan's last task: update the documentation to
describe what this plan landed, from the code.

Read your agent definition and run it in <REFRESH mode over the areas below | update mode for the
features below>; load the skills its steps name.

Read, in this order:
1. CLAUDE.md.
2. The plan: its `Status:` line, §3 task DOC1, and the `As built` notes of every task above — they say
   what landed and where. They are leads: every statement you write is backed by code you read this session.
3. The existing documents for <the areas | the features> in <docs/business-model/ | docs/features/>.
4. The spec `docs/specs/<NNN>-<feature>-design.md` (or the story backlog the plan was built from) — the
   source of purpose (what a rule is for, what a capability is for) and the words the business uses;
   never evidence of what was built.
5. The plan's "Close-out — every task".

Deliverable: <copied verbatim from the task block — it names the documents and the delivery note>.

Screens: <the guides' screenshots come from <the environment, by name>; its address and the test logins
per role are <where the person keeps them — never their values>. | none: this plan has no non-production
environment — the guides carry `**Screenshots:** pending — no environment`, `Status:` says so under
built-but-unverified, and a later "capture the screenshots for <guide>" run closes it.> Either way, ask
once and write on; screenshots never block the text.

Build:
- Fold the answered open questions of every existing guide in scope, before anything else is written.
- Re-trace <AREA ids | the features> over the files `git diff --stat <the plan's first commit>..HEAD` lists.
- Update each existing guide in place; write the guide for an area or feature that has none. Every role,
  administrators included, has its section; with an environment, re-capture the screenshot of every task
  whose screen changed.
- Write the delivery note `docs/deliveries/<NNN>-<plan-slug>.md` last, from the code at HEAD and the
  guides just written, per the documenter skill's `references/delivery-note.md`.
- <the task's own bullets, copied>

Out of scope: any change to source, tests or configuration — a defect the trace finds goes in your
report, never into a guide. Documenting in a guide what the plan intended and did not build.

Traps:
- The plan is not the evidence. Where an `As built` note and the code disagree, the code wins and the
  disagreement is a line in your report.
- What `Status:` lists as built but unverified is documented as built, with the unverified part said.
- An acceptance criterion the code does not meet, or meets differently, is a row of the delivery note's *Not delivered*
  table and a line of your report — never a sentence of a guide, and never a judging word.
- <the per-task trap: the area whose worked example changes because a rule's number changed, the feature
  that moved between areas>

Gate: own tests — `<the documenter's doc-lint command over the documents this task touched>` and over
`docs/deliveries`; expect clean (a `screenshots-pending` WARN stands when no environment was given).

Commit: `<the commit message>`.

You delete the last prompt block, so the filing is yours: rewrite `Status:` one final time and move
this plan to `docs/plans/implemented/`. <Where a blocked task still holds a
block below: the plan stays in `docs/plans/` until it clears.>
Close out per the plan's "Close-out — every task" before you stop.
````

---

### B4 — <title>

**Blocked on B2** — B2 writes this prompt when it lands, from the file layout and the exported type
names it actually settles on. Writing it is a bullet on B2 and a line in B2's own block.

---

### H1 — <title> (the user)

**Blocked on** the SendGrid sending domain being verified (the spec's `## Integrations` X1) — owned by the studio
owner, since 2026-08-04. Nothing to start here until that clears.
`````

## Filled example

The **workshop-booking** plan, caught after the contract task has landed (its
`## Close-out — every task` section, verbatim from plan format §7, sits directly above this one):

`````markdown
## Prompts — one per task

Run them one session each. Every block is complete on its own and opens with its `Depends on:` line.
B1 and B2 share the .NET solution, so B2 waits for B1 and nothing runs beside anything. **Every task gates
its own work and the work landed above it:** each block's `Gate:` line names its commands. No block but F4's runs the unfiltered suite —
F4 is the gate task: the plan's one run under the test lock, the smoke suite plus every test the plan wrote and then the whole set once more, and it fixes what it catches. DOC1 then
updates the documentation from the merged code and files the plan.

**Gates run locally.** Commit locally; ask before `git push`.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| H1 | the SendGrid domain | **the user** | none | — | — |
| C1 | `be` | `be-dotnet` | none | — | ~120k |
| B1 | `be` | `be-dotnet` | C1 | — | ~112k |
| B2 | `be` | `be-dotnet` | B1 | — | ~95k |
| F4 | `fe` | `fe-react` | B1, B2 | — | ~150k |
| DOC1 | `docs` | `documenter` | F4 | — | ~110k |

**H1 and C1 have landed, and their prompts are deleted.** B1, B2, F4 and DOC1 are live.

---

### B1 — the Timetable resource (be-dotnet, be)

````
Depends on: C1
Agent: be-dotnet · Stack: be

You are `be-dotnet`. Task B1 of docs/plans/003-workshop-booking.md: implement the
Workshops and Sessions resources so a studio admin can publish a workshop and add sessions to it.

Read your agent definition, then load exactly these skills: `be-dotnet:patterns-apply`,
`be-dotnet:persistence`, `be-dotnet:unit-testing`.

Read, in this order — these sections only, not the whole artifacts:
1. CLAUDE.md, including the Backend code rules and the Comments rules.
2. The plan: §3 task B1; the spec `docs/specs/003-workshop-booking-design.md`: `## API surface` —
   the Workshops and Sessions endpoint blocks; `docs/specs/validation-catalog.md` (the standard
   validation set — the deltas are in those blocks); `## Data model` — the `workshops` and `sessions`
   table blocks.
3. `src/Shared/IEndpointModule.cs` and `src/Shared/ProblemDetailsMiddleware.cs` — the seam and the
   error envelope C1 built. Match them; do not introduce a second convention.
4. The plan's "Close-out — every task".

Deliverable: a studio admin can publish a workshop, add sessions to it, and see them listed; nobody
else can.

Build:
- Create `src/Scheduling/Domain/Workshop.cs`, `Domain/Session.cs`, `SchedulingService.cs`,
  `SessionEndpoints.cs`, `SchedulingConfiguration.cs`; modify `src/Scheduling/DependencyInjection.cs`.
- Every endpoint matches the spec's Workshops and Sessions blocks exactly: paths, request/response fields, status
  codes.
- The standard validation set applies; the two deltas (`session-overlaps`,
  `workshop-not-published`) return their documented `type` slugs.
- A non-admin token gets 403 on every write; reads are public, per the Workshops block's auth line.
- Sessions register through `IEndpointModule` — no edit to `src/Api/Program.cs`.
- Unit tests in `tests/Scheduling.Tests/SchedulingServiceTests.cs` cover every validation branch and
  the publish state transition. In-process: no `WebApplicationFactory`, no container, no real DB.

Out of scope: the timetable and admin screens (F4, `fe-react`), contract and integration tests
(`qa-api-dotnet`), the booking side of a session's capacity (B3).

Traps:
- `Session` overlaps are checked in local studio time, not UTC — the spec's `sessions` block says why, and
  the existing `src/Shared/StudioClock.cs` is how.
- `ProblemDetailsMiddleware` already owns the envelope. Returning `BadRequest(new { error })` from an
  endpoint bypasses it and produces a second error shape.
- This project is on .NET 8, not 10: no `[FromServices]`-free minimal-API injection.

Gate: own tests — before you commit, run `dotnet build src/Scheduling` and `dotnet test
tests/Scheduling.Tests --collect:"XPlat Code Coverage"`, then read branch coverage over `src/Scheduling/*`
(plan-format.md §5) and write the tests a shortfall needs. Leave them green, fixing what stands in the way
whichever task caused it. Do not run the unfiltered suite or `dotnet format`.

Commit: `feat: workshops and sessions resources (B1)`.

Your `As built` note carries the `file:line` that proves an admin can publish and add. F4 binds to
the response field names, so a rename there is a rewrite of F4's block.
Close out per the plan's "Close-out — every task" before you stop.
````
`````

## Writing rules

- **Write the block from the task, not from memory of the task.** Its deliverable, files, bullets and
  out-of-scope are copied from the task block. A block that paraphrases drifts, and the session trusts
  the block.
- **Name the sections you actually checked exist.** A prompt pointing at an endpoint block the spec
  does not have sends the session hunting, and it will read the whole file to find it.
- **Cite existing code the task must match**, with paths — the seam, the convention, the sibling
  module. This is what stops a session inventing a second way of doing something the repo already does,
  and it is the cheapest few thousand tokens in the block.
- **The traps are per-task, not a house-rules recital.** "Follow CLAUDE.md" is not a trap. "This
  project is on .NET 8, so the API you would reach for does not exist" is.
- **The gate line is on every block, and it names real commands.** A code block whose gate runs nothing
  pushes its failure to the last task, where it is slowest to fix. An intermediate block that tells its
  session to run the unfiltered suite spends its context on work that belongs to the last task.
- **When the next task binds to a different agent, say so above the close-out line.** The agent writing the
  repair is not the agent who will run it, and a block that quietly changes hands is one nobody adopts.
- **The filing duty goes on whichever block will be the last.** Normally that is the documentation task's (`DOC1`), but a task that was blocked on a person outlives it — then the duty is on *that* block, and the documentation task's says the plan stays in `docs/plans/` until it clears. Getting this wrong leaves a finished plan in the live folder, or files one that is still waiting.
- **Partial / blocked / diverged keeps the block on the same task**, with a `**Picking up from:**` line
  naming what remains and where inside the task to start. The task's unfinished bullets are that list.
