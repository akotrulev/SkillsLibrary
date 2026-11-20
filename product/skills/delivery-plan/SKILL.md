---
name: plan-delivery
description: Use when a design pack must become an ordered task list, one deliverable, stack and agent per task. Triggers "what order do we build this in". Not for sizing or prompts (plan-session-budget).
disable-model-invocation: true
---

# Delivery Plan — the ordered, agent-bound task list

The artifact that turns the design pack into work, written in the library's plan format (`engineering-practices/writing-plans/references/plan-format.md`; read it first: this skill is the procedure, not the shape). It adds the streams table, the epic/story binding on every task, the reconcile procedure and the Mission Control ingestion block.

**Every task belongs to exactly one epic, one story, one stack and one agent, and runs in one session.** The task's id, deliverable, stack list and gate are `plan-format.md` §3–§5. The epic and story come from `epics.md` / `stories.md` by way of `epic-map.md`; `dev:plan-session-budget` derives the budget while the task is authored.

**Prerequisites:** `blueprint.md` (approved), `data-model.md`, `api-surface.md`, `integrations.md` and `epic-map.md`, whose lanes and waves this plan's streams and order derive from. **A plan and partly built code both exist → read `references/reconcile.md` first** and run it before re-sequencing anything.

The plan standards are the dev rule file `plans.md` (the project's copy in `.claude/rules/dev/`, else `engineering-practices/rules/`).

**Output:** one file, `docs/plans/<NNN>-<initiative>/delivery-plan.md`, beside the pack; the whole folder moves to `docs/plans/implemented/` when the last task lands (`plan-format.md` §8). `dev:plan-session-budget` fills the `**Budget:**` lines and the `## Prompts — one per task` section inside it. The filled golden example, with the header, streams table, task blocks and Mission Control block, is `references/example-delivery-plan.md`; the prompt-block shape is `backend/_shared/session-budget/references/prompts-section-template.md`.

## Procedure

### Step 1 — Derive the task list mechanically

Read the tasks out of the detail pack in this order; the order is the dependency graph. Done when every row that applies has produced its tasks.

| Source | Produces |
|---|---|
| Blueprint tech stack + repo state | Scaffold / layout / shared config tasks, only what does not exist. A modular monolith's first contract task also creates one folder per blueprint module, a schema per module and the **architecture test** (the stack's `patterns-apply` "Module boundaries") |
| `integrations.md` blocking unknowns | **Prerequisite tasks**: provisioning, accounts, sandbox access |
| Behaviour the plan must keep that no test pins | **Pin tasks**, one per untested area before the first task touching it: `qa-api-<stack>` pins what the API shows, the `be-<stack>` agent pins logic. Deliverable: "the current behaviour of <area> is pinned by N tests, green on today's code." Behaviour the plan *changes* gets `Q` tests instead |
| `data-model.md` migrations | One task per migration, in the stated order |
| `blueprint.md` cross-cutting concerns | Auth wiring, error envelope, config validation, and **the telemetry base** right after the scaffold (`observability-engineer-<stack>`, stack `be`): the OpenTelemetry SDK, structured logging with the trace id, resource attributes, a RED dashboard per service, the local Grafana stack in `deploy/local/`. Skipped only where a service already ships its signals |
| `api-surface.md` shared schemas + §4 | Shared DTOs and the validation/error middleware, once, before any endpoint |
| `api-surface.md` endpoint blocks | One task per resource. In a test-first plan, first **one stub task** routing every endpoint to the `501 not-implemented` response (validation catalog V8.6) with its real response types |
| `epics.md` + `stories.md` | **`TD` tasks** after the stub task and before the first `Q` task (`plan-format.md` §4); left out only on the user's opt-out, recorded in the header |
| Endpoint blocks + validation catalog + `Acceptance:` lines + the test plan's scenarios | **API acceptance tasks** (`Q`, `qa-api-<stack>`): one per resource group that fits a session, after the stub and test-plan tasks, before the resource tasks that turn them green |
| `integrations.md` dependencies, webhooks, background work | One client task per external system; job/consumer tasks |
| `experience-plan.md` §2 + §4 | The **app-shell task** (once; `fe-react` / `fe-blazor` with `design:app-structure`; a placeholder per screen route in a test-first plan), then one frontend task per screen or journey's screen set, each after the endpoints it calls |
| `experience-plan.md` journeys + `Test ids:` | **Journey tasks** (`Q`, `qa-ui-<stack>` / `qa-mobile-<stack>` / `qa-desktop-<lang>`) after the app shell and stubs, red on the placeholders |
| `api-surface.md` endpoint map | **The OpenAPI-asset task**: the stub task generates it from the stubs (test-first), or the `be-<stack>` agent after the last endpoint task (test-after); committed as `{service}-openapi-YYYY-MM-DD.json` and regenerated through `qa/_shared/api-spec-assets`' diff lane. Skipped only when the repo keeps the asset |
| The plan itself | **`DOC1`**, last (`plan-format.md` §5). It names the non-production environment for the screenshots and where its test logins are kept, or says there is none; the guides then land with screenshots pending and `Status:` lists them as built but unverified |

Anything not traceable to a row is missing from the design pack (add it there) or not needed.

**Bind every task to its epic, story and stack** before writing anything else about it. **Epic**: from `epic-map.md` §1; foundation and contract tasks are `E0`, the planner-created epic with no stories. **Story**: the `US` id the task serves, or `—` for `E0`; a task under `E1..En` serving no story is work the backlog is missing or work nobody asked for. **Stack**: one of the `plan-format.md` §4 list. A row yielding work in two trees yields two tasks (endpoints `be`, screens `fe`, generated client `ts`); the split costs an ordering, not a session.

**A user-facing capability is the sum of several rows.** Per capability, write down the set it needs to be usable: schema, entities and domain rules → service → endpoints and contracts → validation and error deltas → authorization → registration and wiring (DI, route module, config keys) → unit tests → the screens that carry it → whatever makes it **reachable** (migration applied, seed data, flag on, the OpenAPI asset). A capability missing any of it has been planned, not delivered.

### Step 2 — Put the tasks in workable order

One flat sequence, ids prefixed by the family of work. Adjacency is not a dependency claim: an edge not written as `Depends on` does not exist. Done when the order meets all five:

- **A valid serialization of `epic-map.md`'s dependency graph**, cross-epic edges included. Waves need not be worked one at a time. Where an edge makes the order impossible, the epic map is wrong: fix it there.
- **Startable at its position**: everything a task imports, calls, migrates against or registers with exists above it.
- **Self-contained at its boundary**: its deliverable written with its unit tests, its gate green, committed. Where the deliverable cannot exist until the next task lands, the two are one task.
- **Dependencies point backwards.** A higher-order `Depends on` is a plan defect, never fixed by renumbering.
- **Prerequisites first**: human-blocked provisioning leads the sequence.

**Test-first is an ordering rule inside every shape.** Wherever the plan delivers an API surface or a journey: pin tasks, then everything both sides bind to (schema, shared types, the stubs and the OpenAPI asset generated from them), then the `TD` tasks (documents, so once, right after the contract tasks), then the `Q` tasks against the stubs, then the implementation tasks that turn them green. A plan with no external contract stays test-after; ask once, with the shape question, whether the user opts out, and record the answer.

**Decide the sequencing shape**, an input and not an inference. Ask once, *"who runs this, and do you need a capability working before the whole plan lands?"*, and record the answer and the shape in the header. Then read the shape's file:

| Sequencing shape: | Use when | Read |
|---|---|---|
| **feature-complete** (default for user-facing work) | Someone wants a capability working before the rest exists, or several lanes run concurrently | `references/shape-feature-complete.md` |
| **agent-batched** | One operator runs the whole plan in back-to-back batches | `references/shape-agent-batched.md` |
| **platform-first** | A platform with no single user journey; the consumer is another system | `references/shape-platform-first.md` |

### Step 3 — Declare the streams

A **stream** is a named lane: tasks in one stream run one after another, different streams run at once. **Derive them from `epic-map.md` §2's lanes**: one lane, one stream, same id, same "internally sequential because" claim, defended now with task-level file sets ("T10 touches `src/Scheduling/*`, T11 touches `src/Booking/*`, no shared file"). A stream that is not a lane is a defect in one of the two documents. The one-stack rule usually splits a lane into `<lane>-api` and `<lane>-ui`, ordered by a `Depends on` edge; record the split back into `epic-map.md` §2. Done when the plan has a table `| Stream | Owns | Why it is internally sequential |` and every task names one of its streams.

- **Name a stream after what it owns** (`booking`, `schema`, `ui`) and keep it stable across the plan.
- **Two tasks whose `Files` overlap are ordered against each other**, in one stream or by a `Depends on` edge: concurrent lanes share one working tree, so an unsequenced overlap is a corrupted edit. An incidental shared edit (a DI module, a route table) goes into its own earlier task.
- **A stream is a claim, not a bucket**: each task needs the previous one's output or touches the same code. A task with no dependency and no shared file gets its own stream.
- **`order` is one sequence across the plan**, no repeats, no gaps; it decides who gets a slot when more lanes are eligible than the run allows.
- **Each prompt's `Depends on:` line** (Step 6) holds the stream predecessor, the cross-stream edges and every earlier task whose `Files` overlap or that builds the same tree (one solution, one Gradle build, one pnpm graph); `none` otherwise. Streams are what Mission Control reads and the line is what Plan Queue reads; the two must agree. Under agent-batched sequencing the lanes are the batches.

### Step 4 — Write each task

Use the plan format's task block (`plan-format.md` §4) plus the binding line `**Epic:** … · **Story:** … · **Stack:** … · **Stream:** … · **Order:** …`, the agent line with `**Skills:**`, and a `**Files:**` list; `references/example-delivery-plan.md` shows `Q1`, `B2`, `F2` and `B7` filled. A task `Not in <id>` names what belongs to a peer. Done when every block carries the binding line, `Skills`, `Files` and its `Not in <id>` bullet.

- **`Epic`, `Story` and `Stack` are on every task or on none**, and so are `Stream` and `Order`. A task naming two stacks, an undeclared stream, a repeated `Order` or an unresolved `Epic`/`Story` is reported as a plan defect, never resolved by guessing.
- **`Agent` is an exact catalog name** from the routing map in `blueprint.md` (`dev:plan-blueprint`), and so is every skill name: Mission Control and every executing session bind on the string. When the stack has no skill for a concern, bind the stack agent, write `— no <concern> skill for this stack; the agent works from the design pack` in `Skills` and open a question. A `human` task carries an `**Owner:**` line and is a gate to satisfy, never a lane to schedule.
- **`Files` are specific**: the stream check relies on them.
- **Size by coherence, not volume.** Split when the task delivers two independent behaviours, part of it is blocked while the rest is not, or two agents own the halves; under ~80k merge with the next same-story same-stack task only if one deliverable remains; over ~150k annotate it and name its split point.
- **A task bound to `fe-*`, a `be` task that adds an entry point, outbound call, job or business event, a batch or a `Q` / `TD` task → read `references/task-block-rules.md`.**

### Step 5 — The task table

The table at the top of `## Prompts — one per task`, sorted by `#`, is the index each prompt block is built from. `#` **is** the plan-wide `order` and must agree with every block's `Order:`. Columns: `| # | Task | Epic | Story | Stack | Stream | Deliverable | Agent | Budget | Depends on | Runs beside |`, the `Deliverable` cell shortened from the block's line. A step a person performs is a row too, with `the user` as the agent. There is no status column: progress is the `Status:` line, the `As built` notes and the prompt blocks that remain.

### Step 6 — Write `## Prompts — one per task`

`dev:plan-session-budget` writes the blocks. Done when every block opens with the Step 3 `Depends on:` line and the preamble says what runs together in one line: "After C1, B1 → B2 run beside Q1; F1 waits for both; F2 runs the whole set." The last runnable task waits for every task nothing else waits for. Write `## Close-out — every task` directly above the prompts, copied verbatim from `plan-format.md` §7. A prompt that cannot be written until an earlier task lands is `**Blocked on <id>** — <id> writes this prompt when it lands, from <what it will then know>.`, matched by a bullet on that task and a line in its prompt block.

### Step 7 — The Mission Control section

Close the document with `## For Mission Control` as `references/example-delivery-plan.md` writes it: a paste note, then the open questions that still block tasks. Mission Control consumes run-level `streams[]` (`id · name · description`), per-task `id · streamId · order · title · deliverable · intent · acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]` (the bullets are `acceptanceCriteria[]`), and `openQuestions[]` with 2–4 options and one recommended; `epic`, `story`, `stack` and `budget` travel as additive fields. A plan without streams runs strictly serially, one lane wide.

## Self-check before handing off

Read `references/self-check.md` and mark each item. Done when every item holds or is fixed.

## Version policy

The sequencing is version-agnostic; **the gate's commands are not**. Take the build, test, format and migration commands from the orientation pass, the project's own, never a guessed default. A runtime or framework major upgrade is its own task, per `CLAUDE.md`'s version policy.
