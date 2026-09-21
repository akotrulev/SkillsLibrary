# The plan document format

The shape every plan in this library is written in — the one the Plan Queue VS Code plugin queues, and
the one `ep-writing-plans`, `be-shared-delivery-plan` and `be-shared-session-budget` all produce.

**One file, self-contained.** The plugin queues whole plan documents, so everything a cold reader or a
fresh session needs is *in the file*: the context, the decisions, the tasks, and the paste-ready prompt
per task. There is no companion file — no `NEXT-PROMPTS.md`, no `HANDOFF.md`. Two files answering
"what do I run next" is one file and one thing that drifts.

**Path:** `docs/plans/NNN-<slug>.md`, under the **target project's** root — never the skills-library
checkout, never a global config directory. `NNN` is zero-padded and scoped to `docs/plans/` (files and
folders both count toward the high-water mark); never reuse or renumber. A `solution-planner` pack puts
its plan at `docs/plans/<NNN>-<initiative>/delivery-plan.md` beside the rest of its artifacts.

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

Three positions are fixed:

| Section | Holds |
|---|---|
| `## 1. What already exists, and what is missing` | A `\| Need \| Today \| Gap \|` table — one row per thing the plan must deliver, what the codebase does about it today (with `file:line` or the function name), and what is missing. On a greenfield plan `Today` is `—`, and the table is still written: it is the plan's grounding, and every task below traces to a row |
| `## N. Tasks` | The task blocks, last of the numbered sections |
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
| `**Stack:**` | **Exactly one** of `be` (backend, database, migrations) · `fe` (the web client) · `ts` (shared TypeScript packages — CLI, MCP, generated clients) · `data` · `infra` · `qa` · `docs` · `human`. **A task that touches both the API tree and the web tree is two tasks** — at any size, for any reason. No estimate justifies a mixed task |
| `**Agent:**` | **Exactly one** exact catalog name — `be-dotnet`, `be-java`, `be-node`, `be-python`, `fe-react`, `fe-blazor`, `data-architect`, `devops-engineer`, `tooling-engineer`, `qa-api-<stack>`, … An invented agent name is the most damaging defect in a plan, because it is what an executing session binds on. A task whose agent you cannot name is a task whose stack you have not decided. `human` tasks name the person or role in an `**Owner:**` line |
| `**Deliverable:**` | **One** observable thing that exists when the task is done, stated as a fact about the world rather than as an activity, and checkable by someone who did not do the work. It is what `Done` means. Two deliverables is two tasks; no statable deliverable is a fragment of one |
| `**Depends on:**` | The ids this task needs that are not immediately above it, each with what it provides — or `—`. Backwards only |
| `**Budget:**` | `~<n>k` plus the **itemized drivers** — what the session actually loads: `CLAUDE.md`, the plan sections it reads, the files it must read as patterns, the files it writes, and the output it reads back. A bare `~140k` is unfalsifiable |
| `**Gate:**` | `**Gate: none**` on every task but the last, naming the commands it must not run — see §5. The last task carries the whole gate, in run order |
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

## 5. The plan gates once, at the end

**Every task but the last writes its code and its tests, commits, and stops.** No build, no test run,
no lint, no format check, no typecheck, no eval, no integration suite, no e2e. Its `**Gate:**` line
says so and names what not to run.

**The last task runs the whole set, for every task in the plan together, and fixes what it finds rather
than handing it back** — a failure there may belong to any task above it. The last task also carries the
documentation and close-out work: it is the only session that knows what actually landed and what is
built but unverified, and a session that only writes markdown is the wasted agent switch this rule
exists to remove.

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
| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| B1 | `be` | `be-node` | — | ~70k |
| B2 | `be` | `be-node` | B1 | ~140k |
| B3 | `be` | `be-node` | B2 | ~85k |
| — | the pilot, then the drop decision | **the user** | B3 | subscription usage |
| P1 | `be` | `be-node` on **Opus 5** | the pilot and the choice | ~90k per round |
```

The table is the plan's index — it is how a reader sees the order, the routing and the cost without
opening a block — and it includes rows for the steps **the user** performs, because a plan that hides
the human step reads as a plan that runs itself. Then one line saying which prompts are live, then
`---`, then the blocks:

`````markdown
### B3 — the report, the screenshots and the close-out (be-node, be)

````
You are `be-node`. Task B3 of docs/plans/030-agent-model-effort-benchmark.md: turn a recorded run
into REPORT.md, with cost per quote first. Then close the work out.

**You never run it for real.** The pilot is the user's to start, after you finish.

Read, in this order:
1. CLAUDE.md, including the close-out rule at the end.
2. The plan: §4, §5a (the drop rules), §6, D6, and task B3.
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
````
`````

Rules:

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
- **Fence the prompt in four backticks** (five around an example that contains four), so the prompt
  itself can carry fenced code and commands.

## 7. Never in a plan

These are plan failures, not style:

- `TBD`, `TODO`, "implement later", "fill in details", "add appropriate error handling", "handle edge
  cases", "write tests for the above"
- "Similar to B2" instead of the content — the executing session may read the tasks out of order
- A `**Deliverable:**` naming an activity instead of a result
- A task with no `**Agent:**` line, or one naming two agents; a task naming two stacks
- A `**Budget:**` with no drivers behind it
- A task with no `**Gate:**` line, or an intermediate task that runs the build or the suite
- A prompt block that says "see the task", or one missing its reading list, its traps or its gate
- A reference to a type, function, file or command that no section and no task defines
- A `**Status:**` line that says "in progress" without saying what is built and what is unverified
