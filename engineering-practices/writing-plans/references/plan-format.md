# The plan document format

The shape every plan in this library is written in — the one the Plan Queue VS Code plugin queues, and
the one `dev:plan-feature`, `dev:plan-delivery` and `dev:plan-session-budget` all produce.

**One file, self-contained.** The plugin queues whole plan documents, so everything a cold reader or a
fresh session needs is *in the file*: the context, the decisions, the tasks, and the paste-ready prompt
per task. There is no companion file — no `NEXT-PROMPTS.md`, no `HANDOFF.md`. Two files answering
"what do I run next" is one file and one thing that drifts.

**Path:** `docs/plans/NNN-<slug>.md` while the plan is live, `docs/plans/implemented/NNN-<slug>.md`
once every task in it has landed (§8) — under the **target project's** root, never the skills-library
checkout and never a global config directory. A `solution-planner` pack puts its plan at
`docs/plans/<NNN>-<initiative>/delivery-plan.md` beside the rest of its artifacts, and the whole folder
moves.

**`NNN` is zero-padded, and its high-water mark spans both folders** — `docs/plans/` *and*
`docs/plans/implemented/`, files and folders alike. List both before picking a number. A number is
never reused and never renumbered, so a moved plan's number stays spent: reusing it would give two
different plans the same id in every commit message, prompt block and `Depends on` that cites one.

---

## 1. The header

```markdown
# NNN — <Title> — plan (YYYY-MM-DD)

**Goal:** <what this builds, in one to three sentences.>

**Status:** <what is built, what is next, what is built-but-unverified, and anything only the user can run.>
```

- **The title carries the number, the name, the word `plan`, and the date it was written.** Cited
  elsewhere as `NNN`.
- **Lead with `**Question:**` instead of `**Goal:**`** where the plan exists to answer something rather
  than to build something ("which model at which effort should answer the shop's chat?").
- **`**Then (<stage>, §N):**`** — optional, where a second stage starts once this one lands.
- **`**Status:**` is maintained, not written once.** Every session that lands a task rewrites it in
  place. It is the first thing a cold reader needs and the last thing a session writes. Name what is
  built, what is next, and what is built but **unverified** — "B2 dry-run on shanks only; no real run
  has happened" is the sentence that stops someone trusting a green checkbox.
- **Where the plan spends something metered** — subscription usage, cloud credit, a rate-limited API —
  say so here, and say who starts it.

## 2. The numbered sections

`## 1.` … `## N.`, cited elsewhere as `§N`. **The narrative comes first and the tasks come last**,
because a task block is only readable against the context above it.

Four positions are fixed:

| Section | Holds |
|---|---|
| `## 1. What already exists, and what is missing` | A `\| Need \| Today \| Gap \|` table — one row per thing the plan must deliver, what the codebase does about it today (with `file:line` or the function name), and what is missing. On a greenfield plan `Today` is `—`, and the table is still written: it is the plan's grounding, and every task below traces to a row |
| `## N. Tasks` | The task blocks, last of the numbered sections |
| `## Close-out — every task` | The duties every task runs before it stops, copied verbatim from §7. Unnumbered, directly above the prompts |
| `## Prompts — one per task` | Last of all, unnumbered |

Between them go as many sections as the subject needs — the matrix, the data model, the script, what is
measured, how a run goes, what the report says. **This is the body of the plan, and it is where the
work is actually decided:** prose plus tables, exact paths, exact commands, real values. Two sections
earn their place near the end of every plan:

- **`## Decisions`** — `**D1 — <the decision, stated as a claim>.**` followed by why, and what it
  costs. Where the decision was a choice between options, it carries a `| Option | Verdict | Why |`
  table so the rejected ones stay rejected on the record. A decision made during execution is appended
  here with its date, not argued again in a task block.
- **`## Answered questions (YYYY-MM-DD)`** — `**O1 — <question>: <answer>.**` one line each. Questions
  still open live in an `## Open questions` table (`| # | Question | Options | Blocks | Owner |`) and
  every one of them names what it blocks.

**No grouping layer sits over the tasks** — not phases, not slices, not stages, not milestones, neither
as structure nor as vocabulary. A task's *internal* actions are its **steps**; that is the only thing
the word "step" names here. The one thing that looks like an exception is not one: a section may
describe a **later stage of the initiative that is gated on something outside the plan's tasks** — a
run the user starts, a decision they make — and name the tasks that live in it. The task list is still
one flat ordered sequence, and that section's tasks carry their `Depends on` edge to the human step
like any other.

## 3. Task ids

**A letter prefix naming the family of work, then a number** — `B1`, `B2`, `B3` for the build;
`P1` for a tuning round that follows it. Numbering runs within a prefix; the **execution order is
document order**, and every prerequisite that is not the task immediately above is written on the task
as `Depends on:` and points backwards. A forward-pointing dependency is an ordering defect, not a note.

Ids are assigned once and never renumbered — they are cited by every prompt block, every `Depends on`,
and every `As built` note. A task that turns out to be unnecessary is marked and kept, with why; a task
that vanishes reads as a task that was forgotten. Where nothing better fits, `T` is a fine prefix.

## 4. The task block

````markdown
### B2 — tools/model-bench: the harness that plays and records a run

**Stack:** `be` · **Agent:** `be-node`
**Deliverable:** `pnpm bench:agent` plays §3 and records §4 into `journal.jsonl`/`results.json`.
**Depends on:** B1.
**Budget:** ~140k — CLAUDE.md 25k, this plan 12k, `tools/assistant` as the package pattern ~12k,
the chat route's request shape and stream ~10k, writes ~40k, test output ~15k.
**Gate: none** — this plan gates once, in B3. Do not run the build, the test suite, lint or typecheck.

- New workspace package `tools/model-bench`, same shape as `tools/assistant` — its own `args.ts`, an
  injectable `fetch`, and a `main.ts` that is the only file that touches the process.
- `checks.ts`: §4's checks as pure functions over `(transcript, snapshots, specs)`, each with a unit
  test built from hand-written fixtures, including one that fails each check on purpose.
- **Not in B2:** the report and the screenshots (B3 — together they would push this session over
  budget), and any real run: the task ends at a green `--dry-run`.
- **As built (2026-09-16):** `--port` was added (default 3200) — on the deployment box the deployed
  service holds 3200. §3's words live in `apps/api` as `BENCH_CUSTOMER_TURNS` so the flows and the
  harness send one list.
````

| Line | Rule |
|---|---|
| `**Stack:**` | **Exactly one** of `be` (backend, database, migrations) · `fe` (the web client) · `mobile` (the native or React Native client app) · `ts` (shared TypeScript packages — CLI, MCP, generated clients) · `data` · `infra` · `qa` · `docs` · `human`. **A task that touches both the API tree and the web tree is two tasks** — at any size, for any reason. No estimate justifies a mixed task |
| `**Agent:**` | **Exactly one** exact catalog name — `be-dotnet`, `be-java`, `be-node`, `be-python`, `fe-react`, `fe-blazor`, `data-architect`, `devops-engineer`, `tooling-engineer`, `qa-api-<stack>`, … An invented agent name is the most damaging defect in a plan, because it is what an executing session binds on. A task whose agent you cannot name is a task whose stack you have not decided. `human` tasks name the person or role in an `**Owner:**` line |
| `**Deliverable:**` | **One** observable thing that exists when the task is done, stated as a fact about the world rather than as an activity, and checkable by someone who did not do the work. It is what `Done` means. Two deliverables is two tasks; no statable deliverable is a fragment of one |
| `**Depends on:**` | The ids this task needs that are not immediately above it, each with what it provides — or `—`. Backwards only. **It also names every earlier task whose `Files` overlap this task's or that builds the same tree** — one .NET solution, one Gradle build or one pnpm package graph shares build output — with the overlap as the reason: once the prompts carry `Depends on:` lines (§6), position orders nothing, and a task that leaves an overlapping predecessor out runs beside it in the same working tree |
| `**Budget:**` | `~<n>k` plus the **itemized drivers** — what the session actually loads: `CLAUDE.md`, the plan sections it reads, the files it must read as patterns, the files it writes, and the output it reads back. A bare `~140k` is unfalsifiable |
| `**Gate:**` | One of three forms — see §5. `**Gate: none**` naming the commands it must not run; `**Gate: own tests**` naming the one filtered command it runs (a `Q` task and the implementation tasks of a test-first plan); the whole gate, in run order, on the last task |
| The bullets | **The work, in the order it is done**, with exact paths, exact names, exact commands, and the real values the code will use. This is the task's body; it replaces a step list |
| `**Not in B2:**` | What belongs to another task or another agent, named. Mostly it keeps the executing agent out of a peer's lane. Where a stack-cut task cannot be demonstrated end to end on its own — a backend task whose screen arrives two tasks later — say so **here** rather than pretending the capability landed, and have the contract-first side return an explicit **not-implemented** response, never a fake success or an empty list |
| `**As built:**` | **Written by the task when it lands**, dated: what actually happened where it differed from the plan, the ids and names it assigned, and what is built but unverified. It is the plan's durable record, and it is what makes a re-read of the plan worth more than a re-read of the diff. Never edited backwards |

**A deliverable, concretely:**

| Not a deliverable | A deliverable |
|---|---|
| "Work on the orders API" | "`POST /orders` accepts a valid order and returns `201` with the created id" |
| "Refactoring done" | "`OrderService` no longer reads `HttpContext`; the request id arrives as a parameter" |
| "Tests added" | "`OrderServiceTests` covers all four validation branches" |
| "Migration work" | "`AddOrders` migration applied; `orders` and `order_lines` exist with their FKs" |

**Test-first plans add three rules to the task block:**

- **`Q` is the acceptance-test family:** ids `Q1…Qn`, stack `qa`, agent `qa-api-<stack>` / `qa-ui-<stack>` /
  `qa-mobile-<stack>`, skills including `qa-<stack>:test-first`.
- **Order:** everything both sides bind to — the schema, the contract, the shared types and **the
  stubs** — then **the acceptance tests written against them**, then the backend tasks, the
  shared-package tasks, and the frontend and mobile tasks.
- **A `Q` task's deliverable names its tests and their red reason** — "every endpoint in
  `api-surface.md` §5.2 and every AC of US7–US9 has an acceptance test in
  `services/orders/tests/Orders.AcceptanceTests/`, and each fails on `501 not-implemented`." **An
  implementation task's deliverable names the acceptance tests it turns green** — "the 14 Orders
  acceptance tests from Q1 pass, and B3's unit tests cover ≥ 80% of its branches."

**Acceptance tests are read-only to implementers.** A rule every implementation prompt repeats,
verbatim:

> The acceptance tests a `Q` task wrote are the spec, and they are **read-only** to every later task except the gate. Never edit, skip, delete or weaken one: not its assertion, its data or its timeout. A test you believe is wrong is a dated `D<n>` with both readings, and it stays red; the gate task resolves it with the user.

**Red for the right reason.** A `Q` test is red **on the `not-implemented` stub** — in Arrange or in
Act, since a setup call that reaches a stub is also the right reason — or, for a journey, **on the
screen's placeholder**. A test that passes against a stub asserts nothing. A test that is red on a
`404`, a compile error or a wrong URL has a wiring defect, which the `Q` task fixes before it stops.

## 5. The plan gates once, at the end

**Every task but the last writes its code and its tests, commits, and stops.** No build, no test run,
no lint, no format check, no typecheck, no eval, no integration suite, no e2e. Its `**Gate:**` line
says so and names what not to run. The one exception is a test-first plan's `Gate: own tests` task,
below, which runs exactly its own filtered tests.

**The last task runs the whole set, for every task in the plan together, and fixes what it finds rather
than handing it back** — a failure there may belong to any task above it. The last task also carries the
documentation and close-out work: it is the only session that knows what actually landed and what is
built but unverified, and a session that only writes markdown is the wasted agent switch this rule
exists to remove.

**The `Gate:` line takes one of three forms:**

| Form | On | Runs |
|---|---|---|
| `**Gate: none** — this plan gates once, in <id>. Do not run …` | contract tasks, docs tasks, journey tasks whose app cannot start in one command | nothing |
| ``**Gate: own tests** — run only `<command>`; this plan gates once, in <id>. Do not run the full suite, another tree's build, lint or typecheck.`` | `Q` tasks and the implementation tasks of a test-first plan | exactly the command |
| `**Gate (this is the last runnable task …):**` | the last runnable task | the whole set in run order, ending with the coverage floor |

- **The planner writes the command, filtered by file or class**, never the unfiltered suite:
  `dotnet test tests/Orders.AcceptanceTests --filter "FullyQualifiedName~Orders"`,
  `./gradlew test --tests '*OrdersApiTest'`, `npx vitest run src/orders`,
  `npx playwright test e2e/booking.spec.ts`.
- **A `Q` task's command runs the tests it writes and expects red. An implementation task's command
  runs its unit tests and the acceptance tests it must turn green, then the coverage-floor measure
  over the files it wrote** (the table below, scoped to those files), so a shortfall is closed in the
  session that wrote the code.
- **When the acceptance tests need a running service**, the command starts it the project's own way
  (a Testcontainers fixture, the compose file, Playwright's `webServer`), and the block says so. A
  journey suite that cannot start its app in one command is `Gate: none`, and its red check moves to
  the gate.
- **A failure outside the task's own tests is not its to fix**; it is noted in `As built`.
- **Every test-first plan restates the cost:** the tree is still not known to build at a task
  boundary; only each task's own tests are known to pass.

**The gate ends with the coverage floor** whenever the plan wrote code: unit tests cover **at least
80% of the branches in the code the plan wrote** — every file it created, whole, and the methods it
changed in files that already existed. The scope is the plan's change, never the repo. The gate takes
the file list from git, starting at the commit that added this plan (a `solution-planner` pack: its
`delivery-plan.md`):

```bash
git diff --name-only "$(git log --diff-filter=A --format=%h -1 -- docs/plans/NNN-<slug>.md)" HEAD
```

It measures those files with each stack's tool and **writes the missing tests until the floor holds**
— never by lowering the number, excluding a file that has logic, or marking code as excluded. Files the
stack's selection matrix does not test (DTOs, configuration, DI registration, migrations, generated
code) stay out of the measured list. The `As built` note records the figure per stack and names every
file left out.

| Stack | Collect, then read branch coverage for the changed files |
|---|---|
| .NET — NUnit / xUnit / bUnit | `dotnet test --collect:"XPlat Code Coverage" --results-directory TestResults`, then `dotnet tool run reportgenerator -reports:"TestResults/*/coverage.cobertura.xml" -targetdir:TestResults/coverage -reporttypes:"TextSummary;Html" -filefilters:"+*<File>.cs;+*<Component>.razor"` → `Branch coverage` in `Summary.txt` |
| Java — JaCoCo | `./gradlew test jacocoTestReport` with the CSV report on → `BRANCH_COVERED ÷ (BRANCH_COVERED + BRANCH_MISSED)` over the changed classes' rows of `build/reports/jacoco/test/jacocoTestReport.csv` |
| Kotlin / Android — Kover | `./gradlew :app:koverLogDebug`, its log grouped by class in branch units → the changed classes' lines |
| TypeScript — Vitest | `npx vitest run --coverage --coverage.reporter=text --coverage.include=<file> …` (one `--coverage.include` per file) → `% Branch` |
| React Native — Jest | `npx jest --coverage --collectCoverageFrom='{<file>,<file>}'` → `% Branch` |
| Python — pytest-cov | `uv run pytest --cov=src --cov-branch --cov-report=`, then `uv run coverage json --include="<file>,<file>"` → `totals.covered_branches ÷ totals.num_branches` |
| Swift — Xcode | `xcodebuild test … -enableCodeCoverage YES -resultBundlePath build/Unit.xcresult`, then `xcrun xccov view --report --json build/Unit.xcresult` → `lineCoverage` per file. **Xcode reports no branches, so the Swift floor is 80% of the changed lines** |

Each stack's testing skill carries the one-time setup its row needs, under `## Coverage floor`. For a
method changed in a file that already existed, read that file's page in the stack's HTML report rather
than its whole-file total.

**A plan that adds or changes a service's behaviour ends its gate with the telemetry smoke**, after the
coverage floor: the signals the implementation tasks named must reach the local stack while the acceptance
suite runs.

1. Start the stack the foundation's telemetry-base task committed — `docker compose -f deploy/local/docker-compose.yml up -d`
   (the OpenTelemetry Collector, Loki, Tempo, Prometheus and Grafana; the compose file belongs to the
   target project, the library ships none).
2. Run the service with `OTEL_EXPORTER_OTLP_ENDPOINT` pointing at the Collector, then run the
   acceptance suite against it.
3. Confirm, through Grafana's datasource proxy (`/api/datasources/proxy/uid/<uid>/…`, which works for five
   containers or one all-in-one image alike) or the backends' own query APIs:

| Signal | Backend | Query | Passes when |
|---|---|---|---|
| The spans the tasks named | Tempo | search by `service.name` and span name | each named span has a trace |
| A log line carrying one of those traces' id | Loki | `{service_name="<service>"} \| json \| trace_id="<id>"` | at least one line returns |
| The metrics the tasks named | Prometheus | `<metric>` instant query | each named metric has a series |

4. The `As built` note records the trace id and the three queries. A missing signal is fixed in the task that
   added it, like any gate failure.

With no container runtime on the machine, or a service the gate cannot start, the smoke is recorded as
**unverified** in `Status:` — never skipped silently.

**"The last task" means the last task that is not blocked.** Where a task waits on something outside
the plan — a run the user starts, a credential, a decision — the gate belongs to the last task that can
actually run, and the blocked tasks sit below it carrying their own gate for whenever they run.

**The cost, accepted and stated once in the plan rather than discovered:** intermediate commits are
ungated, so the tree is **not** known to build at every task boundary, and a plan cannot be stopped
halfway and trusted. Say it in the plan. It buys one verify-and-fix loop per plan instead of one per
task, which is the single largest line in a task's budget.

## 6. `## Prompts — one per task`

**One task is one session, so the plan closes with one paste-ready prompt per task, in task order.**
This section is why the file is queueable: it is the whole of what each next session is told.

It opens with a short preamble — run them in order, one session each, each block complete on its own;
where the gates run; and anything **no** prompt may do ("none of them may start a real run — the user
starts it"). Then the task table:

```markdown
| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| B1 | `be` | `be-node` | none | — | ~70k |
| B2 | `be` | `be-node` | B1 | Q1 | ~140k |
| Q1 | `qa` | `qa-api-typescript` | B1 | B2 | ~90k |
| B3 | `be` | `be-node` | B2, Q1 | — | ~85k |
| — | the pilot, then the drop decision | **the user** | B3 | — | subscription usage |
| P1 | `be` | `be-node` on **Opus 5** | the pilot and the choice | — | ~90k per round |
```

**Which tasks run in parallel is written down, not inferred.** The preamble says it in one line — *"After
B1, B2 runs beside Q1; B3 waits for both and is the gate."* — and the table's `Runs beside` column names,
per task, the tasks it can run in parallel with (`—` for none). Tasks that run together share one working
tree, so a pair may run beside each other only when their `Files` are disjoint and they build different
trees. **The gate task waits for every task that nothing else waits for**, so it starts last.

The table is the plan's index — it is how a reader sees the order, the routing and the cost without
opening a block — and it includes rows for the steps **the user** performs, because a plan that hides
the human step reads as a plan that runs itself. Its `Depends on` cells are the same ids as each block's
first line, below. Then one line saying which prompts are live, then `---`, then the blocks:

`````markdown
### B3 — the report, the screenshots and the close-out (be-node, be)

````
Depends on: B2, Q1

You are `be-node`. Task B3 of docs/plans/030-agent-model-effort-benchmark.md: turn a recorded run
into REPORT.md, with cost per quote first. Then close the work out.

**You never run it for real.** The pilot is the user's to start, after you finish.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4, §5a (the drop rules), §6, D6, task B3, and "Close-out — every task".
3. `tools/model-bench` as B2 left it: README, `journal.ts`, `results.ts` (the `Results` type is what
   `report.ts` reads), `checks.ts`, `args.ts` (add the `report` command there — B2 refuses it as
   unknown), and B2's "As built" notes in the plan.
4. `apps/api/src/llm/registry.ts` — the per-token rates, and which ones are verified.

Build:
- `report.ts` (pure, golden-tested) …

Traps:
- `$/quote` must come from token counts × the registry. The CLI's own cost is only a cross-check.
- The R-rules propose; nothing drops a configuration automatically.

Gate (this is the last task, so it carries the plan's only gate, in run order):
  pnpm install && pnpm build && pnpm test --continue && pnpm typecheck && pnpm lint
  pnpm bench:agent --dry-run --runs 1 --screenshots
Fix what it finds — a failure may belong to B1 or B2, not only to you.

Commit: `feat: bench:agent report, drop candidates and screenshots (bench B3)`.
Finish with the exact commands the user runs for the pilot, and every prerequisite still missing.
Close out per the plan's "Close-out — every task" before you stop.
````
`````

Rules:

- **The first line of every block is `Depends on: <ids>`** — ids only, comma-separated, or
  `Depends on: none` when the task can start at once. A program reads it to start the task as soon as
  those tasks are done, so prose on that line becomes ids nobody has, and a plan never relies on what a
  missing line means. It names the task's **prerequisites** (the block's `**Depends on:**`) **and every
  earlier task whose `Files` overlap its own or that builds the same tree** (§4); an edge already implied
  through another task may be left out of both.
- **Built from the task's own block, copied rather than paraphrased.** The deliverable, the files and
  the gate are the task's; the prompt adds only the **reading order** and the **traps** — the two to
  four things specific to that task: the convention that is easy to miss, the file that looks like the
  pattern but is not, the migration that must run before the test, the down-level API that does not
  exist here.
- **Cite sections, never whole artifacts.** `api-surface.md` §5.3, not `api-surface.md`. This is the
  single biggest lever on the budget holding: a session told to read the pack reads the pack.
- **No block says "see the task" or "as above".** A session opened from the block starts without
  scrolling up.
- **A prompt is living text.** A task that lands something different from what the plan predicted
  **rewrites the prompt blocks below it before it stops** — in place, with no changelog appended. A
  block that still names a file the previous task renamed is the most expensive kind of stale.
- **A prompt that cannot be written yet is not guessed.** Where a block genuinely depends on what an
  earlier task lands — the shape of a file it has not created, an id it will assign, a decision it will
  make — do not invent it at plan time. Leave the line
  `**Blocked on <id>** — <id> writes this prompt when it lands, from <what it will then know>.`
  and **the blocking task writes that prompt as part of finishing, before it stops.** The plan says so
  in the blocking task's bullets and in its own prompt block.
- **A landed task's prompt is deleted**, and the line above the blocks says which are gone:
  *"B1 and B2 have landed, and their prompts are deleted — a prompt for a finished task is a thing
  someone runs by mistake."* The live prompt set is the plan's progress indicator: what is left to run
  is exactly what is still written down.
- **Every block ends with the close-out.** Its reading list names `## Close-out — every task` last, and
  its final line is the close-out instruction — see §7. It is how a queued session learns to write
  its `As built` note, maintain the blocks below it, and file the plan.
- **When the last block goes, the plan moves.** See §8 — deleting the last prompt block is what
  finishes the plan, so the task that does it is the task that files it.
- **Fence the prompt in four backticks** (five around an example that contains four), so the prompt
  itself can carry fenced code and commands.

## 7. The close-out every task runs

**A session opened from a prompt block loads nothing the block does not name** — no execution skill,
no runner. So the duties every task performs before it stops live in the plan itself, as a fixed
section directly above the prompts, copied verbatim from here:

````markdown
## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit, adding only your own
   files, by path — never `git add -A`.
````

Every prompt block ends its reading list with this section and closes with the line
`Close out per the plan's "Close-out — every task" before you stop.` The section is the same in
every plan; a plan does not edit it, and a task does not skip a step because it "changed nothing" —
step 4 and step 5 always apply.

## 8. A finished plan is moved to `docs/plans/implemented/`

**Deleting the last prompt block is what finishes a plan**, so the task that deletes it is the task
that files the plan. Before it stops, it:

1. Rewrites the `**Status:**` line one last time — what the plan delivered, and what is still
   **unverified** (a journey nobody walked, a path only the gate's unit tests exercised, a capability
   built against a stub). This is the line the next person reads instead of the whole document.
2. `git mv`s the file into `docs/plans/implemented/`, **keeping its filename and its number** —
   `docs/plans/030-agent-model-effort-benchmark.md` → `docs/plans/implemented/030-agent-model-effort-benchmark.md`.
   A `solution-planner` pack moves its **whole initiative folder**:
   `docs/plans/003-workshop-booking/` → `docs/plans/implemented/003-workshop-booking/`, with every
   artifact in it, so the plan never loses the pack it cites.
3. Commits the move with the task's own commit, and says in its report where the plan went.

**`docs/plans/` is what is in flight; `docs/plans/implemented/` is what landed.** That is the whole
point of the move: the live folder answers "what is being built" by being listed, without anyone
reading a status line to find out.

**The test is the blocks, not the tasks.** The plan moves when no prompt block is left — no live
block, no `Blocked on <id>` placeholder, and no blocked task holding one. So:

- **A blocked task keeps the plan in `docs/plans/`.** Its block stays, naming its blocker and its
  owner; a plan whose only remaining work is waiting on a person is still in flight, and moving it
  would hide the wait. The filing duty then belongs to *that* block, not to the gate task's — say so
  in both.
- **A task marked unnecessary does not.** It keeps its id and its "why", per §3, but it has no prompt
  block, so it holds nothing up.

**Never delete a plan, and never edit one after it moves.** It is the record of why the code looks the
way it does, and its `Decisions` and `As built` notes are cited by later plans. A plan that turns out
to have been wrong gets a new plan saying so, not a rewrite of the old one.

## 9. Never in a plan

These are plan failures, not style:

- `TBD`, `TODO`, "implement later", "fill in details", "add appropriate error handling", "handle edge
  cases", "write tests for the above"
- "Similar to B2" instead of the content — the executing session may read the tasks out of order
- A `**Deliverable:**` naming an activity instead of a result
- A task with no `**Agent:**` line, or one naming two agents; a task naming two stacks
- A `**Budget:**` with no drivers behind it
- A task with no `**Gate:**` line, or an intermediate task that runs more than its own tests — the
  build, the whole suite, lint or typecheck (a filtered `Gate: own tests` run is not a defect)
- An implementation task that edits, skips or deletes an acceptance test
- A `Gate: own tests` line with no command, or with an unfiltered one
- A `Q` task that was allowed to run its tests and did not see them red on the stub
- A plan that writes code whose gate does not end with the coverage floor (§5)
- A prompt block that says "see the task", or one missing its reading list, its traps or its gate, or
  its close-out line; a plan with no `## Close-out — every task` section
- A reference to a type, function, file or command that no section and no task defines
- A `**Status:**` line that says "in progress" without saying what is built and what is unverified
