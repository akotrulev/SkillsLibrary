---
name: be-shared-delivery-plan
description: Use when a planned build (blueprint + data model + API surface + integrations + epic map) needs turning into an ordered task list — one flat sequence of tasks, each with a deliverable, one stack, one executing agent and a context estimate, plus named streams derived from the epic map and a reconcile against half-built code. Triggers "what order do we build this in", "turn the plan into tasks", "pick up where we left off". Do NOT use to write code (`be-<stack>`), size tasks or write the next prompts (`be-shared-session-budget`), decide what runs in parallel at epic level (`be-shared-epic-map`), run a plan (`ep-executing-plans`), or audit code vs spec (`code-auditor`).
---

# Delivery Plan — the ordered, agent-bound task list

The artifact that turns the design pack into work. It is written in **the library's plan document
format** — the header, the numbered sections, the task block, the gate-once rule and the
`## Prompts — one per task` section are all specified in
`engineering-practices/writing-plans/references/plan-format.md`, and this skill produces that shape
with four additions a `solution-planner` pack needs: the streams table, the epic/story binding on every
task, the reconcile procedure, and the Mission Control ingestion block. Read the format reference
first; this skill is the procedure, not the shape.

Three things make it different from a generic plan:

- **Every task names its executor and its stack** — exactly one stack, exactly one agent name from this
  library, plus the skills it should load. That binding is what lets the plan run unattended, inline or
  through Mission Control, and it is what makes a task handable to a single agent without it wandering
  across a boundary it does not own.
- **It survives interruption, in one file.** The plan carries its own `## Prompts — one per task`
  section: one paste-ready prompt per task, deleted as each task lands, so what is left to run is
  exactly what is still written down. There is no `NEXT-PROMPTS.md` and no `HANDOFF.md` — the document
  is queued and handed over whole. The reconcile procedure re-derives the state from the code when the
  plan's own record is stale, because a plan whose status you have to trust is a plan you have to redo.
- **It is the progress record.** The `**Status:**` line in the header, the dated `**As built:**` note on
  each landed task, and the `## Decisions` section are maintained **in this document** as the work
  lands — not in someone's memory of the session. See *Tracking execution in the plan document*.

**The unit of work is a task, and the plan is one flat list of them.** Ids carry a letter prefix naming
the family of work and a number within it — `C1` for the contract wave, `B1…Bn` for the backend
batches, `F1…Fn` for the frontend areas, `H1` for a human prerequisite — in the order they are done,
with no grouping layer above them: no phases, no slices, no stages, no milestones. What a grouping
would have carried is carried by four things on the task itself: its position in the order, its
`Depends on` edges, its stream, and the epic and story it serves. Use the word **task** everywhere —
in this document, in status reports, and when talking to the human.

**Every task states one deliverable** — the observable thing that exists once it is done. See Step 4.

**Every task belongs to exactly one epic, one story, one stack and one agent, and is executed in one
session.** The epic and story come from `epics.md` / `stories.md` by way of `epic-map.md`; the stack is
one of `be` · `fe` · `ts` · `data` · `infra` · `qa` · `docs` · `human`; and the session budget is
derived by `be-shared-session-budget` while the task is being authored, not measured afterwards.

> **A task that touches both the API tree and the web tree is two tasks.** There is no mixed task at
> any size, and no estimate justifies one.

**The plan gates once, in its last runnable task.** Every task before it writes its code and its unit
tests, commits, and stops — no build, no test run, no lint, no format check, no typecheck. The last
runnable task runs the whole set for every task in the plan together and **fixes what it finds rather
than handing it back**, because a failure there may belong to any task above it; it also carries the
documentation and close-out work. The cost is stated in the plan rather than discovered: intermediate
commits are ungated, so the tree is **not** known to build at every task boundary and the plan cannot
be stopped halfway and trusted. See Step 4.

And one property decides the shape of the sequence: **how the plan will be executed**. User-facing work
is sequenced *feature-complete* by default — the tasks for one capability run consecutively and the last
of them makes the capability usable, rather than a layer being finished across every area first — but a
plan one operator will run in back-to-back batches is sequenced *agent-batched* instead: a contract
wave, then one batch per backend module, then one per frontend area. See Step 2.

**Announce at start:** "I'm using the `be-shared-delivery-plan` skill to sequence the work."

**Prerequisites:** `blueprint.md` (approved), `data-model.md`, `api-surface.md`, `integrations.md`, and
`epic-map.md` — whose lanes and waves this plan's streams and order are derived from, not re-decided.
Sequencing without the detail pack produces task titles, not tasks; sequencing without the epic map
produces a plan that is one lane wide.
## When to use

- Step 7 of a `solution-planner` run
- `RESUME` — reconciling an existing plan against partially-built code and re-sequencing what remains
- `EXTEND` — appending tasks for a new functional area

## When NOT to use

- Executing the plan → `ep-executing-plans` (inline, the default) or the named stack agent per task
- Deciding which epics run at the same time → `be-shared-epic-map`, which this skill consumes
- Sizing the tasks and writing `## Prompts — one per task` → `be-shared-session-budget`, which runs on this skill's output
- A generic non-backend multi-step task → `ep-writing-plans`
- Auditing what got built against what was specified → `code-auditor`

## Output

**One self-contained file: `docs/plans/<NNN>-<initiative>/delivery-plan.md`**, beside the rest of the pack. **The whole initiative folder moves to `docs/plans/implemented/<NNN>-<initiative>/` once every task has landed** — done by the task that deletes the last prompt block, per the format reference §7 — so `docs/plans/` lists what is in flight. `NNN`'s high-water mark spans both folders; a moved plan's number stays spent. It carries the context,
the streams, the tasks, the decisions and the paste-ready prompt per task. `be-shared-session-budget`
derives the `**Budget:**` lines and authors the `## Prompts — one per task` section inside this
document — there is no companion prompt file.

**A filled golden example is at `references/example-delivery-plan.md`** (the shared
`001-workshop-booking` pack — shapes normative, domain content illustrative); the prompt-block shape is
in `backend/_shared/session-budget/references/prompts-section-template.md`.
---

## Procedure

### Step 1 — Derive the task list mechanically

Do not brainstorm tasks. Read them out of the detail pack, in this order — the order is itself the dependency graph:

| Source | Produces |
|---|---|
| Blueprint tech stack + repo state | Scaffold / project structure / shared config tasks (only what does not exist) |
| `integrations.md` blocking unknowns | **Prerequisite tasks** — provisioning, accounts, sandbox access |
| `data-model.md` migration sequence | One task per migration, in its stated order |
| `blueprint.md` cross-cutting concerns | Auth wiring, error envelope, logging/telemetry, config validation |
| `api-surface.md` shared schemas + section 4 | Shared DTOs and the validation/error middleware — **once**, before any endpoint |
| `api-surface.md` endpoint blocks | One task per resource (not per endpoint — a resource's CRUD set is one coherent task) |
| `integrations.md` dependency blocks | One client task per external system |
| `experience-plan.md` §2 + §4 screen catalog | The **app-shell task** (shell, nav, home — once, bound to `fe-react` / `fe-blazor` with `design-ux-patterns`), then one frontend task per screen or per journey's screen set (a list and its detail are one coherent task), each after the endpoints it calls and citing its screen ids |
| `api-surface.md` outbound webhooks + background work | Job/consumer tasks |
| `api-surface.md` endpoint map (once the resource tasks exist) | **The OpenAPI-asset task** — one standard task, after the last endpoint task: the `be-<stack>` agent generates the spec from the implemented surface and commits it canonicalized as `{service}-openapi-YYYY-MM-DD.json`, so `qa/_shared/api-spec-assets` has its canonical input from day one and every later contract change flows through that skill's diff-driven lane instead of being reverse-engineered. Greenfield plans include it by default; skip only when the repo already keeps the asset |

Anything not traceable to a row above is either missing from the design pack (go add it there) or is not needed.

**Then bind every task to its epic, its story and its stack**, before anything else is written about it:

- **Epic** — from `epic-map.md` §1. Foundation and contract tasks are `E0`, the planner-created epic that carries no stories; every other task names an `E` id from `epics.md`.
- **Story** — the `US` id from `stories.md` the task serves. `E0` tasks have no story and say `—`. A task under `E1..En` that serves no story is either work the backlog is missing (go add it there) or work nobody asked for.
- **Stack** — exactly one of `be` (backend, database, migrations) · `fe` (the web client) · `ts` (shared TypeScript packages — CLI, MCP, generated clients) · `data` · `infra` · `qa` · `docs` · `human`.

**One stack per task is a hard rule, and it is what makes the batching mechanical rather than a judgement call.** A row above that yields work in two trees yields two tasks: the endpoints are `be`, the screens that call them are `fe`, and the generated client between them is `ts`. Splitting them is not a cost — the tasks of one stack within one epic are already adjacent, so the split costs an ordering, not a session.

Where a stack-cut task cannot be demonstrated end to end on its own — a backend task whose screen arrives two tasks later — say so in its `Out of scope` rather than pretending the capability landed, and have the contract-first side return an explicit not-implemented response, never a fake success.

**A user-facing capability is not a row — it is the sum of several.** Where the initiative delivers something a person does (place an order, book a session, reset a password), the table gives you the *pieces*; what makes them a feature is that all of them exist at once. Before sequencing, write down, per capability, the full set it needs to be usable end to end:

> schema + entities + the domain rules → the service/orchestration → the endpoints and their request/response contracts → the validation & error deltas → the authorization rule → registration and wiring (DI, route module, config keys) → unit tests → the screens that carry it (`experience-plan.md`'s journey for the capability) → and whatever makes it **reachable**: the migration applied, seed/reference data, a feature flag defaulted to on, the OpenAPI asset when a consumer is generated from it.

That set is what Step 2 sequences. A capability missing any of it has been planned, not delivered — and "the endpoints exist but nothing registers them" is the way this fails most often.

### Step 2 — Put the tasks in workable order

**One flat sequence, ids prefixed by the family of work, in the order the work is done.** No grouping layer sits above the tasks: what makes the order safe is that each task's inputs are produced by tasks above it, and that every such prerequisite is written on the task as a `Depends on` edge. There is no barrier to hide behind — **adjacency is not a dependency claim, so an edge that is not written down does not exist.**

The order must satisfy five things:

- **The order is a valid serialization of `epic-map.md`'s dependency graph.** No task is ordered before anything it transitively depends on, cross-epic edges included. That is the whole constraint the epic map places on the order — **it does not require the waves to be worked one at a time.** A wave-3 lane's task may sit above a wave-2 lane's task when its own dependencies are already met, and under feature-complete sequencing it usually will: the order is the single sequence one person would work through, while the waves are the claim about what *could* be open at once, which the streams table carries. Where a dependency edge makes the order impossible, the epic map is wrong — report it and fix it there.
- **Startable at its position.** Everything a task imports, calls, migrates against, registers with, or configures exists by the time its turn comes. If it does not, the task is in the wrong place — move it, don't annotate it.
- **Self-contained work at every task boundary.** Each task ends having written everything its deliverable needs, including its unit tests, and having committed. It does **not** end with a verified green tree: the plan gates once, in its last runnable task, so a task that leaves the build red is expected and the failure is fixed there. What is still a defect is a task that leaves the *work* half-done — a service with no caller, an endpoint nobody registered — because the next task cannot start on it. Where the deliverable genuinely cannot exist until the following task lands, the two are one task.
- **Dependencies point backwards, always.** A `Depends on` naming a task with a higher order is a contradiction, and it is reported as a plan defect rather than resolved by reordering the ids.
- **Prerequisites first.** Human-blocked provisioning from `integrations.md` leads the sequence as its own tasks, so nothing downstream stalls on a credential nobody requested.

**Then decide the sequencing shape**, because it changes what runs consecutively:

| Shape | Use when | The order reads as |
|---|---|---|
| **Feature-complete** (the default for user-facing work) | The initiative delivers capabilities a person uses, and someone will want to see one working before the rest exists | One capability at a time, each usable end to end before the next begins |
| **Agent-batched** (the one-operator shape) | One operator will execute the whole plan in back-to-back batches, and nobody needs a capability demonstrable before the last batch lands | One agent against one file tree at a time: a contract wave, then backend module by module, then frontend area by area |
| **Platform-first** (the layered shape) | The initiative is a service or platform with no single user journey at stake — several areas land together and the consumer is another system | One layer at a time, completed across every area |

**The shape is chosen from how the plan will be executed, and that is an input, not an inference.** Ask it once — *"who runs this, and do you need a capability working before the whole plan lands?"* — and record the answer and the shape it selected in the plan header. One operator running batches sequentially, with the integration and E2E pass at the end, selects **agent-batched**; several lanes running concurrently, or a stakeholder who wants the first capability demonstrable early, selects **feature-complete**. Guessing this wrong is expensive in both directions: feature-complete sequencing under one operator pays an agent switch and a context reload per capability for a property nobody is using, and agent-batching under a demo deadline hides every capability behind the last batch.

**Feature-complete sequencing** puts the foundation tasks first — but only the foundations the **first** capability needs, never every foundation every capability will eventually want — and then runs each capability's tasks back to back:

| Order | Tasks |
|---|---|
| First | Human-blocked provisioning the first capability needs — one task per provisioning track |
| Then | Scaffold, layout, config + validation, CI skeleton, and the cross-cutting surfaces (auth, error envelope, shared DTOs) the first capability actually depends on — nothing speculative |
| Then | Capability A's whole set from Step 1, in its natural order: migration → entities + rules → service → endpoints → wiring → unit tests → its screens (the app-shell task precedes the first capability's screens) |
| Then | Capability B's own set, plus only the foundations B is the first to need |
| Then | One run of tasks per remaining capability, most valuable first |
| Last | The OpenAPI asset, telemetry, rate limiting, performance, docs |

Three rules keep it honest:

- **A capability's last task delivers the capability.** Its `Deliverable` is the behavioural sentence — *"a user with the `booker` permission can book a session and then see it under their bookings"* — not "the tasks are done". Order the capability's tasks so exactly one of them makes that true, and make it the last of the run.
- **Deferred foundations are named, not forgotten.** Where a capability's run deliberately stops short of a shared surface a later one will need — a generic error envelope, a pagination convention, a caching layer — say so in that task's `Out of scope` and place the generalization in the task that first needs it. An implied deferral is indistinguishable from an oversight.
- **Schema order stays global.** Migrations run in the order `data-model.md` states even when the sequence is per-capability; a capability's tasks own the migrations for its own entities, at their stated position in that sequence.

**Agent-batched sequencing** trades the "one capability at a time" property for the smallest number of agent switches and file-tree reloads. It groups the same tasks by **who executes them and what they touch**, so each batch is one agent working one tree once:

| Order | Tasks |
|---|---|
| First | Human-blocked provisioning from `integrations.md` — unchanged, and still one task per provisioning track |
| Then | **The contract wave** — one batch carrying everything both sides bind to, for the **whole initiative** rather than the first capability: the full migration sequence, the entity/model types, the shared DTOs and the error envelope, auth wiring, config keys, the typed endpoint signatures with their request/response contracts (stubbed where the behaviour lands later), the generated or hand-written API client the frontend imports, and the app shell + nav map + route tree. Once this lands, no later batch waits on a different agent |
| Then | **Backend, one batch per module** — a module is a file tree one agent owns (`src/Booking/*`): its entities, domain rules, service, endpoint bodies, registration and unit tests, in a single task. Most-depended-on module first |
| Then | **Frontend, one batch per screen area** — an area is one nav section of `experience-plan.md` §2 and the screens under it: their components, routes, states and wiring, in a single task, ordered by the nav map |
| Last | The OpenAPI asset, telemetry, rate limiting, docs — and the **verification batch**: the full build, the test run, and the QA pass the plan defers to the end |

**What may be merged into one batch — all four, or it stays separate:**

- **Same agent.** A batch spanning two agents is not a batch, it is two tasks. This is the rule the shape exists for.
- **Same file tree**, or trees that no other batch touches. The Step-3 overlap rule is unchanged and still hard.
- **No gate between them** — no human prerequisite, no approval, no open question either one waits on.
- **Every dependency already satisfied by an earlier batch.** A merge that pulls a `Depends on` forward is a reordering, not a merge.

**And two things never merge:** work on opposite sides of the contract wave (a capability's screens do not join its backend module batch because they are one feature), and two tasks whose deliverables cannot be stated as one sentence — that is still the test of whether something is one task.

**What the shape costs, stated in the plan rather than discovered:**

- **No capability is usable until both its batches have landed.** The plan says which capabilities become usable at which batch, and the frontend batch that completes each one still carries the behavioural deliverable — the sentence just arrives later than it would under feature-complete sequencing.
- **Stubs must be unmistakable.** A contract-wave endpoint with no behaviour yet returns an explicit not-implemented response, never a fake success or an empty list, and the batch's `Out of scope` names the module batch that fills it. An indistinguishable stub is the failure mode of this shape.
- **Nothing about task discipline relaxes.** A batch *is* a task, so it states one deliverable, names one agent, and writes its own unit tests inside the batch that writes the code. What is deferred to the last runnable task is **running** them — the build, the suite, the lint and the typecheck for the whole plan at once, plus the live/integration/E2E pass. That is a deferred verification, not a licence to ship untested code: the tests are written, committed and read by the gate task, which fixes what they catch.

**Where several plan packs are executed as one delivery** — three initiative folders that together make one working application — the shape is decided once across all of them and the batching is derived across the packs, not inside each: one contract wave covering every pack's schema and contracts, then the module batches, then the area batches. Tasks keep their own pack's ids and are cited as `<NNN-initiative>/T<n>`; the batch order lives in the pack that owns the contract wave, and the others' delivery plans point at it rather than restating it.

**The platform-first shape** runs the same tasks in layer order instead:

| Order | Tasks |
|---|---|
| First | Human-blocked provisioning from `integrations.md` |
| Then | Scaffold, project layout, config + validation, CI skeleton |
| Then | Migrations, in their stated order |
| Then | Auth wiring, error middleware, shared DTOs, telemetry base — every later task depends on these |
| Then | One task per resource: entity → persistence → service → endpoints → unit tests |
| Then | External clients, webhook handlers, background jobs — one per dependency |
| Last | Rate limiting, observability, performance, docs |

**What runs concurrently is decided in Step 3, not here.** The order is a single sequence — the one you would work through yourself, alone. Streams say which parts of it can be worked at the same time, and `Depends on` says what must not be.

### Step 3 — Declare the streams

A **stream** is a named lane. Tasks in one stream run strictly one after another; different streams run at the same time. The question to answer is **"which lanes does this work actually have, and why is each one internally sequential?"** — and `epic-map.md` §2 has already answered it at story altitude.

**Derive the streams from the epic map's lanes; do not re-decide them.** One epic-map lane is one stream, with the same id and the same "internally sequential because" claim, now defended with the task-level file sets instead of the story-level ones. Two things follow:

- **A stream that is not an epic-map lane is a defect in one of the two documents.** Say which — usually the map missed a split the task file sets make obvious, and the fix is upstream in `epic-map.md`.
- **The one-stack rule usually splits a lane in two.** An epic-map lane covering a story's backend and its screens becomes a `be` stream and an `fe` stream, ordered against each other by a `Depends on` edge rather than merged. Name them `<lane>-api` and `<lane>-ui`, and record the split back into `epic-map.md` §2 so the two documents keep agreeing.

Give the plan a streams table, before the task blocks:

| Stream | Owns | Why it is internally sequential |
|---|---|---|
| `foundation` | Scaffold, config, CI, the shared surfaces every task builds on | One root file set — every task edits the solution root or `Program.cs` |
| `booking` | The Bookings resource and the email it sends on confirm | `src/Booking/*` throughout; T13 sends on the event T11 raises |

Rules:

- **Name a stream after what it owns** — `booking`, `schema`, `infra`, `ui`. Never `stream1`.
- **Stream identity is stable across the whole plan.** Foundation work at T2 and foundation work at T14 is one `foundation` lane running down the plan, not two.
- **Two tasks whose `Files` overlap MUST be ordered against each other — same stream, or a `Depends on` edge between them.** This is the hard rule and the one that is machine-checked: concurrent lanes execute against a single working tree, so two lanes writing one path with nothing sequencing them is a corrupted edit, not a merge conflict to resolve later. With no barrier in the plan, this rule is the only thing standing between an overlapping pair and a lost write. If the shared edit is incidental — a DI registration module, a route table — pull it out into its own earlier task instead of collapsing two good lanes into one.
- **A stream is a claim, not a bucket.** Each task in it needs the previous one's output, or touches the same code. Spreading independent tasks across lanes to look parallel is the failure mode in one direction; dumping unrelated work into one lane to look safe is the failure mode in the other, and it serialises a plan that did not need to be.
- **A task that depends on nothing and shares no file gets its own stream.**
- **`order` is one sequence across the whole plan** — 1, 2, 3, … no repeats, no gaps. Within a stream it fixes execution sequence; across the plan it records the order you would have done the work in yourself, which is what decides who gets a slot when more lanes are eligible than the run allows to be concurrent.
- **`Depends on` still points backwards in `order`.** Streams say "same lane, therefore sequential"; `dependsOn` says "across lanes, this waits on that". Both are needed and a task waits on both — but a dependency on a task with a *higher* order is a contradiction between the two, and it is reported as a defect rather than resolved.

Defend each lane concretely — "T10 touches `src/Scheduling/*`, T11 touches `src/Booking/*`, no shared file". The streams table is the load-bearing statement about what may run at the same time; there is no plan-level parallel-safety flag behind it.

**Under agent-batched sequencing the lanes are the batches**: `contract` (the whole wave, one lane, everything downstream depends on it), one lane per backend module, one per frontend area, and `verification` last. They are still declared and still defended — a one-operator run executes them serially by choice, and the same document handed to Mission Control or to a second operator must still say truthfully which of them could run at the same time.

### Step 4 — Write each task

The block is the plan format's task block (`plan-format.md` §4) plus the epic/story/stream binding:

```markdown
### B3 — Orders resource

**Epic:** `E2` Ordering · **Story:** `US7` · **Stack:** `be` · **Stream:** `ordering-api` · **Order:** 12
**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
**Deliverable:** the five Orders endpoints are live and reachable — a caller with the `orders:write`
permission can place, cancel and close an order, and list or get their own.
**Depends on:** C1 (schema, auth wiring, shared DTOs + error middleware)
**Budget:** ~110k — CLAUDE.md 25k, `api-surface.md` §5 and two `data-model.md` entity blocks 6k,
3 skills 24k, `src/Billing/*` as the module pattern ~14k, 6 files created and 1 modified 13.5k,
commit and diff read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in F4. Do not run `dotnet build`, `dotnet test` or `dotnet format`.

**Files:**
- Create: `src/Ordering/Domain/Order.cs`, `src/Ordering/Domain/OrderLine.cs`
- Create: `src/Ordering/Infrastructure/OrderConfiguration.cs`
- Create: `src/Ordering/Application/OrderService.cs`
- Create: `src/Ordering/Api/OrdersEndpoints.cs`
- Create: `tests/Ordering.Tests/OrderServiceTests.cs`
- Modify: `src/Ordering/DependencyInjection.cs`

- All five endpoints match `api-surface.md` §5 exactly: paths, request/response fields, status codes.
- The standard validation set applies; the three endpoint-specific deltas (`insufficient-stock`,
  `idempotency-conflict`, `currency-not-enabled`) return the documented `type` slugs.
- Cross-tenant access returns 404, per the API's V5.3 disclosure choice.
- Illegal state transitions return 409 naming the current and the allowed states.
- Unit tests cover every validation branch and every state transition — in-process, no HTTP, no
  container, no real DB.
- **Not in B3:** the Orders screens (F2, stack `fe`, same epic — the endpoints are not reachable from
  the UI until it lands), contract/integration tests (`qa-api-dotnet`), the stock-reservation
  client (B5).
- **As built:** <written by B3 when it lands>
```

Rules:

- **`Epic`, `Story` and `Stack` are on every task, or on none.** `Epic` is an `E` id from
  `epic-map.md` (`E0` for foundation and contract work); `Story` is a `US` id from `stories.md`, or
  `—` for an `E0` task; `Stack` is exactly one of `be` · `fe` · `ts` · `data` · `infra` · `qa` ·
  `docs` · `human`. A task naming two stacks is two tasks, reported as a plan defect rather than
  resolved by picking the larger one. A `Story` id that does not exist in `stories.md`, or an `Epic`
  that does not exist in `epic-map.md`, is a defect in the citation, not licence to invent the backlog
  entry.
- **`Budget` is derived by `be-shared-session-budget` while the task is authored**, and it carries its
  drivers itemized — what the session actually loads — so a reader can tell a 110k of many small files
  from a 110k of one large one. It is a target, never a gate: one deliverable, one stack and one agent
  all outrank it. Re-derive it whenever the task's `Files`, `Skills` or cited sections change; a stale
  budget is worse than none, because it is a number someone will trust.
- **`Deliverable` is the one observable thing that exists when the task is done**, stated as a fact
  about the world rather than as an activity. "Implement the Orders service" is not a deliverable;
  "`POST /orders` accepts a valid order and returns `201` with the created id" is. It is checkable by
  someone who did not do the work, and it is the first thing written — a task whose deliverable you
  cannot state is not yet one task. Where the task is the last of a capability's run, its deliverable
  is the behavioural sentence for the whole capability (see Step 2).
- **The bullets are the work and the checks at once.** Each one is concrete and checkable, cites the
  design pack **by section** rather than restating it, and uses the real paths and the real slugs.
  "Handles errors properly" is not a bullet; "returns the documented `type` slug for each of the three
  deltas" is. Where the task is a batch, the bullets **are** its per-piece breakdown — one per
  endpoint, per screen, per rule.
- **`Gate: none` on every task but the last runnable one**, naming the commands it must not run. The
  last runnable task carries the whole gate, in run order, with the project's own commands from the
  orientation pass — and it fixes what the gate finds rather than handing it back, because a failure
  there may belong to any task above it. It also carries the close-out: the docs, the repository-state
  note, and the honest list of what is built but unverified.
- **`As built`** is written by the task when it lands, dated: what differed from the plan, the ids and
  names it assigned, and what is built but unverified. It is the durable record, appended and never
  edited backwards.
- **`Agent` is an exact catalog name**, picked from the routing-map catalog in `blueprint.md` (authored
  by `be-shared-solution-blueprint` — that catalog is the single authoritative list; `be-dotnet`,
  `data-architect`, `qa-api-<stack>` are the shape). An invented name is the most damaging defect in
  the pack, because Mission Control and every executing session bind on this string. Same for skill
  names. When the chosen stack has no skill for a concern the task needs (e.g. `be-node` currently
  ships no service-side auth skill), bind the task to the stack agent anyway, note the gap in the
  Skills line (`— no <concern> skill for this stack; the agent works from the design pack`), and add an
  open question — never invent a skill name to fill the hole.
- **Human prerequisite tasks use `Agent: human`.** Provisioning work from `integrations.md`'s blocking
  unknowns — accounts, tenants, sandbox access — is a real task with a real id, but its executor is a
  person: the Agent line is the literal `human` and the block carries an `**Owner:**` line naming who
  does it. `human` is exempt from catalog-name resolution, and Mission Control treats these tasks as
  gates to satisfy, never lanes to schedule.
- **`Files` must be specific.** This is what the stream check relies on, and it is the difference
  between a plan and a wish.
- **`Stream` is one of the ids declared in Step 3**, and `Order` is that task's slot in the plan-wide
  sequence. **Every task carries both, or no task does** — half-authored lanes are rejected rather than
  completed, because back-filling the rest would scatter tasks into lanes nobody planned. A `Stream`
  naming an undeclared lane and two tasks claiming one `Order` are both reported as plan defects, and
  the undeclared lane also costs you the lanes you did author: the whole plan falls back to derived
  ones.
- **Size a task by coherence, not by volume.** A task is one thing, done once — a resource, a migration
  set, an external client, a capability's endpoint surface — and it is exactly as big as that thing is.
  File counts and bullet counts are not a limit: work that genuinely needs fourteen files is one task,
  and cutting it into "the entity" and "the service" produces two tasks neither of which can be
  verified alone. **The deliverable is the test**: one task, one deliverable. Two deliverables means
  two tasks; no statable deliverable means it is a fragment of one. **Split when it stops being one
  thing**: it delivers two independent behaviours; part of it is blocked while the rest is not; or two
  different agents own the halves. **Split along a seam inside the same stack**, never by handing part
  of it to another stack. The session budget informs this and never decides it: under ~80k, look at the
  next task in the same story and same stack and merge only if the result still states one deliverable;
  over ~150k, annotate the task and name its natural split point. A task that overshoots with one
  deliverable, one stack and one agent is a large task correctly authored — label it, do not file it as
  a defect.
- **A batch is still one task, and it still states one deliverable.** Under agent-batched sequencing a
  task is the whole module or the whole screen area, and its deliverable is the one sentence that
  covers the set — *"every endpoint under `/bookings` implements its documented behaviour and
  validation"*, not a list of five. A batch whose deliverable takes two sentences was two batches; a
  batch of unrelated leftovers grouped because one agent happens to own them is a bucket, not a task,
  and it is split.
- **Frontend tasks cite their screens.** A task bound to `fe-react` / `fe-blazor` names the
  `experience-plan.md` screen ids it delivers (`S3`, `S4`) and the journey it completes (`J1`), lists
  `design-ux-patterns` in its skills, and carries `experience-plan.md` §6's responsiveness budget as
  bullets verbatim; the capability's last task is usually this one, and its deliverable is the journey's
  behavioural sentence.
- **`Not in <id>` per task** — mostly to keep the executing agent out of a peer's lane, and to name
  what a contract-first stub is waiting for. A stub with no behaviour yet returns an explicit
  not-implemented response, never a fake success or an empty list.
- **Tasks are implementation.** Live/E2E/integration test runs, starting servers, and manual
  verification belong to a separate QA pass owned by a `qa-*` peer. Unit tests are part of the
  implementation task, not a separate one.

### Step 5 — The task table

The scannable index, and the row a prompt block is built from. It lives at the top of
`## Prompts — one per task`, sorted by `#` — which makes the sequence auditable at a glance: a repeat
or a gap is visible without cross-reading the task blocks. `#` **is** the plan-wide `order` Mission
Control consumes; the task blocks repeat it as `Order:`, and the two must agree. The `Deliverable` cell
is the block's deliverable line shortened to fit — same claim, fewer words:

| # | Task | Epic | Story | Stack | Stream | Deliverable | Agent | Budget | Depends on |
|---|---|---|---|---|---|---|---|---|---|
| 12 | B3 | `E2` | `US7` | `be` | `ordering-api` | The five Orders endpoints are live and reachable | `be-dotnet` | ~110k | C1 |
| — | the sandbox credentials | — | — | `human` | — | Stripe test keys in the team vault | **the user** | — | — |

**Rows for the steps a person performs are in the table too**, with `the user` as the agent — a plan
that hides the human step reads as a plan that runs itself.

**There is no status column, and that is deliberate.** What has landed is carried by three things that
cannot drift apart from the work: the `**Status:**` line in the header, the dated `**As built:**` note
on each landed task, and the fact that **a landed task's prompt block is deleted**. The live prompt set
is the progress indicator — what is left to run is exactly what is still written down.

### Step 6 — Write `## Prompts — one per task`

**`be-shared-session-budget` authors this section, inside this document.** What this skill owes it is
what a block is built from: a task block with `Epic` / `Story` / `Stack` / `Agent` / `Skills` /
`Files` / `Budget` / `Gate` filled in, and a streams table that says which lanes exist.

Close the header note by naming the two duties an executing agent has, so neither is a surprise: **the
record goes into its task's `As built` note and the header `Status:` line; the next session's prompt is
the block in `## Prompts — one per task` — rewritten where what landed differs from what it assumes,
and deleted when its own task lands.**

**Where a prompt cannot be written at plan time** — because it depends on what an earlier task actually
lands, an id it will assign, or a decision it will make — the block is the line
`**Blocked on <id>** — <id> writes this prompt when it lands, from <what it will then know>.`, and
writing it is a bullet on the blocking task and a closing duty in the blocking task's own prompt.
Guessing the block produces the one kind of stale that reads as current.

### Step 7 — The Mission Control section

Close the document with an ingestion block so the plan can be pasted into Mission Control and produce
a near-identical task graph:

```markdown
## For Mission Control

Paste this document into the plan box and point the run at `<target repo path>`.
The task graph maps 1:1 — the streams in §2 become MC's lanes, each task keeps its
`stream` and `order` alongside its `deliverable`, `agent`, `skills`, `files` and
`dependsOn`, and the open questions below carry their options. There is no grouping
level: ordering is the `order` sequence, and every prerequisite is an explicit
`dependsOn` edge. This plan gates once, in <the last runnable task> — the earlier
tasks deliberately run no build or test command, so a lane that reports green
without one is behaving as planned. MC's planner re-reads the target repo, so it may
split a task it finds too large; that is expected and does not invalidate the
sequence — the new pieces belong in the split task's own lane, and each needs its own
deliverable.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
```

Mission Control's planner consumes exactly these fields — run-level `streams[]`
(`id · name · description`), per-task `id · streamId · order · title · deliverable · intent ·
acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]`, and `openQuestions[]` with 2–4
options each and one recommended. Writing them in that vocabulary is the entire compatibility
requirement: the task block's bullets are its `acceptanceCriteria[]`.

**`epic`, `story`, `stack` and `budget` are additive** — MC ignores fields it does not know, so
carrying them costs nothing and losing them costs the whole epic and sizing story on a round trip.
Write them per task alongside the fields above.

**Streams are mandatory, not an optimization.** With no grouping level in the plan, `streams[]` +
`order` + `dependsOn[]` are the whole concurrency story: the streams say what may run at the same time,
and the dependencies say what must not. A pack that omits them leaves MC nothing to derive lanes from
but the raw sequence, and it will run the plan strictly serially — correct, but one lane wide. Author
the streams.
---

## Tracking execution in the plan document

Once implementation starts, **this document is the record of what has been done** — there is no second
file to keep in step with it. Three things carry the record, and every executing agent maintains them
**as part of the task**, not as a write-up afterwards:

| When | What the executing agent writes |
|---|---|
| Finishing a task | A dated `**As built:**` note on the task block — what differed from the plan, the ids and names it assigned, what is built but unverified, and the `file:line` or command output that proves the deliverable exists. Then it **deletes its own prompt block**, and rewrites the prompt blocks below it wherever what it landed differs from what they assume |
| Finishing a task another task's prompt was blocked on | The blocked prompt block itself, from what it now knows — that duty is a bullet on this task and a line in its own prompt |
| Finishing the last runnable task | The gate, in run order, with the failures **fixed here** rather than handed back; then the close-out: the docs, the repository-state note, and the honest list of what is built but unverified |
| Stopping mid-task | The header `**Status:**` line names the task and what remains; a `**Progress:**` line on the task block lists the bullets not yet done. The prompt block **stays** and gains a `Picking up from:` line |
| Building it differently | Both readings on the task block, and the resolution appended to `## Decisions` as a dated `D<n>` once the human picks. A divergence is escalated, never absorbed |
| Hitting a blocker | The `**Status:**` line and the task block name what it waits on and who owns it. The prompt block **stays** and names the blocker and its owner — deleting it loses the lane |
| Finishing a capability's last task | That its behavioural deliverable now holds, and how it was checked |
| Deleting the **last** prompt block | The plan is finished. The `Status:` line rewritten one last time — what the pack delivered, and what is still **unverified** — then `git mv docs/plans/<NNN>-<initiative> docs/plans/implemented/`, the whole folder with every artifact in it, in that task's own commit. **A plan still holding a blocked task's block does not move** |

And the header `**Status:**` line is rewritten by **every** session that lands anything: what is built,
what is next, and what is built but unverified.

Rules:

- **The deliverable is what done means.** A task is done when its stated deliverable exists, not when
  its bullets were performed. Every bullet satisfied with the deliverable absent is a partial — say so
  in `Status:` and leave the prompt block in place.
- **Evidence, not assertion.** An `As built` note carries the `file:line` or the command output that
  proves it, produced in the session that wrote it. The rule the reconcile runs on applies first to the
  person writing the note.
- **`As built` notes are append-only.** They are added, never edited or deleted — a task that regresses
  gets a second dated note, not a corrected one. Distributed across the tasks, they are what makes
  *"what has been done"* answerable without reading git.
- **Decisions and deviations go in `## Decisions`**, because they outlive the session that made them. A
  deviation that lives only in a rewritten prompt is gone by Monday.
- **Never delete a task that turned out to be unnecessary.** Mark it, say why, keep the id. A task that
  vanishes reads as a task that was forgotten. (A task's *prompt* is deleted when the task lands —
  that is the opposite case, and it is the point.)
- **An `As built` note is still a lead to a cold agent.** One written last month is re-verified against
  the code on a RESUME, per the reconcile procedure below. Recording it well makes that reconcile
  cheap; it does not replace it.

---

## The reconcile procedure (RESUME mode)

Run this **before** re-sequencing anything, when a plan and partially-built code both exist. It is the mode this skill earns its keep in.

**The governing rule: the plan is a lead, not evidence.** An `As built` note, a green pipeline, a commit message, a deleted prompt block and the header `Status:` line are all claims. A verdict is assigned only after reading the code **this session**.

**One thing this format changes about the reconcile:** because the plan gates once, an unfinished plan's tree may not build, and a red build is **not** by itself evidence that a task failed. Establish which it is before assigning verdicts — run the gate yourself, and attribute each failure to the task that owns the file.

1. **Read the design pack**, so you know what was supposed to exist.
2. **Walk each task** in the task table and look for its artifacts — the files it names, the migration, the endpoint, the registration.
3. **Assign a verdict** with `file:line` evidence:

| Verdict | Means |
|---|---|
| **Done** | The deliverable exists and every bullet on the task is satisfied by code you read this session |
| **Partial** | Some bullets satisfied; name exactly which are missing |
| **Not started** | No artifacts found. Say what you searched for — a negative claim needs its search named |
| **Diverged** | Built, but differently from the plan. **Both readings recorded; the human decides** |
| **Blocked** | Cannot proceed — a prerequisite, a missing credential, a red build |

4. **Escalate every divergence.** Usually the code is right and the plan is stale — but you never silently rewrite the plan to match, because the other possibility is a defect. Present both readings, recommend one, and append the resolution to the plan's `## Decisions` as a dated `D<n>`.
5. **Sweep the class.** If one task diverged because the plan assumed a convention the project does not use, every other pending task assuming it is also wrong. Fix them together.
6. **Check the baseline.** Does the repo build and do its tests pass *right now*? A plan that assumes a green baseline while the build is red is wrong from task one. Report a red state as a finding — it is not yours to silently fix.
7. **Re-sequence what remains**, then have `be-shared-session-budget` re-derive the budgets that changed and rewrite `## Prompts — one per task` **from what you found** — not from what it previously said. Delete the blocks of tasks the reconcile found `Done`; restore a block for a task whose prompt was deleted on a claim the code does not support, and say so in `Status:`.

Report the reconcile as counts plus the divergences in full:

```
Reconcile: 7 Done · 2 Partial · 11 Not started · 1 Diverged · 0 Blocked
Diverged — C1 (auth wiring): plan specifies policy-based authorization;
  code uses role attributes directly (src/Api/Program.cs:44-58).
  Recommend adopting the code and amending the plan — policies buy nothing
  here with three flat roles. Your call.
```

---

## Delivery plan template

`````markdown
# NNN — <Initiative> — delivery plan (YYYY-MM-DD)

**Goal:** <the one-to-three-sentence statement of what this initiative delivers.>

**Status:** <what is built, what is next, what is built but unverified. Rewritten by every session
that lands anything.>

**Pack:** `./epics.md` · `./stories.md` · `./blueprint.md` · `./data-model.md` · `./experience-plan.md` (when user-facing) · `./api-surface.md` · `./integrations.md` · `./epic-map.md`
**Target repo:** `<path>` · **Stack:** <stack + version> · **Build/test:** `<the project's own commands>`
**Sequencing shape:** feature-complete | agent-batched | platform-first — <the execution model that selected it>

> **For agentic workers:** the tasks below are one flat sequence — work them in order. Each names the
> agent that should execute it, the skills to load, and the one deliverable that means it is done.
> **This plan gates once, in <the last runnable task>:** every task before it writes its code and its
> unit tests, commits, and stops — no build, no test run, no lint, no typecheck. The tree is therefore
> not known to build at every task boundary, and the plan cannot be stopped halfway and trusted.
> **Update this document as you work** — the dated `As built` note on your task, the `Status:` line
> above, and `## Decisions` for anything you built differently — then **delete your own prompt block**
> and rewrite the ones below yours wherever what you landed differs from what they assume.

## 1. What already exists, and what is missing
<!-- | Need | Today (file:line, or — on greenfield) | Gap | — one row per thing this plan delivers -->

## 2. Streams
<!-- one per `epic-map.md` §2 lane, split by stack where the lane spans two -->
| Stream | Epic | Stack | Owns | Why it is internally sequential |
|---|---|---|---|---|

## 3. Tasks
<!-- one block per task, in order: epic + story + stack + stream + order, agent + skills,
     deliverable, depends on, budget, gate, files, the work-and-checks bullets, Not in <id>,
     and the As built note once it lands -->

## 4. Open questions
| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|

## 5. Deliberately not planned
<!-- what this initiative excludes and which agent/peer owns it instead -->

## 6. Decisions
<!-- D1..Dn: the decision as a claim, why, what it costs. Answered questions, resolved divergences,
     and anything built differently from the plan, appended with its date. Never argued twice -->

## Prompts — one per task
<!-- the preamble (one session each, where the gates run, what no prompt may do), the task table,
     the line saying which prompts have been deleted, then one fenced block per live task -->

| # | Task | Epic | Story | Stack | Stream | Deliverable | Agent | Budget | Depends on |
|---|---|---|---|---|---|---|---|---|---|

## For Mission Control
<!-- ingestion note + blocking open questions -->
`````

## Self-check before handing off

1. Every row of §1's gap table traces to a task, and every task traces back to a row. Every functional
   area in `blueprint.md` has at least one task; every migration, every resource, every screen in
   `experience-plan.md`, every external client, every blocking unknown is a task.
2. Reading the tasks in `order`, each one could be started at its position: everything it needs was
   produced by a task above it.
3. The sequencing shape is stated in the header, with the execution model that selected it. Under
   agent-batched: every batch is one agent against one file tree, every contract-wave stub names the
   batch that fills it, and the plan says which capability becomes usable at which batch.
4. Every task states one `Deliverable`, as a result rather than an activity. Every user-facing
   capability has a last task whose deliverable says behaviourally what a user can then do, and the run
   of tasks ending there covers everything on the Step-1 capability set — including its screens and what
   makes it reachable, not only its endpoints. Every frontend task cites its screen ids and inherits the
   responsiveness budget.
5. Every task binds to an **exact** catalog agent name and exact skill names.
6. Every task carries `Epic`, `Story` and `Stack`; every `Stack` is exactly one of the eight values;
   every `Epic` resolves in `epic-map.md` and every non-`E0` `Story` resolves in `stories.md`. No task
   names two stacks, and no task touches both the API tree and the web tree.
7. Every task carries a `Budget` line with its drivers itemized, the task table's `Budget` cell agrees
   with it, and every estimate over ~150k either names its natural split point — inside its own stack —
   or says why the task is one thing anyway.
8. Every `dependsOn` id exists, and every one points backwards in `order`.
9. Every task names a declared stream and carries a unique `order`; every stream's row says why it is
   internally sequential; every pair of tasks whose `Files` overlap is ordered against each other — same
   stream or a `dependsOn` edge between them. Every stream traces to an `epic-map.md` §2 lane (or to a
   stack split of one, recorded back into that document), and the order is a valid serialization of that
   document's dependency graph.
10. Every task's bullets are checkable and cite the design pack by section.
11. **Exactly one task carries the gate**, it is the last runnable one, its commands are the project's
    own from the orientation pass and in run order, and it is told to fix what the gate finds rather
    than hand it back. Every other task says `Gate: none` and names what not to run. The
    ungated-boundary cost is stated in the header note.
12. `## Prompts — one per task` exists inside this document, with one block per task that has not
    landed, each naming one task, an exact agent, exact skills, and pack **sections** rather than
    artifacts — and every `Blocked on <id>` placeholder is matched by a bullet on that task and a line
    in its prompt's closing duty.
13. Every `As built` note carries `file:line` or command output read this session. §1, §2, §6 and the
    task table exist, §6 empty before execution starts.
14. The header `Status:` line says what is built, what is next, and what is built but unverified.
15. The prompt block that will delete the last block carries the filing duty — rewrite `Status:`, then move the whole initiative folder into `docs/plans/implemented/` — and this pack's `NNN` was taken from the high-water mark across `docs/plans/` **and** `docs/plans/implemented/`.

## Handoffs

- **← `be-shared-epic-map`** — supplies the epics, the lanes and the waves. The streams table is its §2
  at task altitude, and the order respects its §3.
- **← `ep-writing-plans`** — owns the plan document format this skill writes in
  (`engineering-practices/writing-plans/references/plan-format.md`). Where the two disagree on the
  shape of the document, that reference wins; this skill owns only the additions above.
- **→ `be-shared-session-budget`** — sizes these tasks, writes the `Budget:` lines back onto them, and
  authors `## Prompts — one per task` inside this document.
- **→ `be-dotnet` / `be-java` / `be-node` / `be-python` / `fe-react` / `fe-blazor`** — execute the
  tasks bound to them, write the `As built` note and the `Status:` line, delete their own prompt block
  and rewrite the ones below it.
- **→ `ep-executing-plans`** — the task-by-task execution loop, with checkpoints; its per-task
  checkpoint is where the `As built` note and the prompt maintenance get written.
  `ep-delegate-to-subagents` runs the same tasks through subagents — the controller, not the subagent,
  owns the plan update.
- **→ Mission Control** — paste the document, point at the repo.
- **→ `data-architect` / `tooling-engineer` / `devops-engineer` / `observability-engineer-<stack>` /
  `qa-*`** — the tasks bound to them, run as peers.
- **→ `code-auditor`** — when a reconcile finds systemic drift rather than a handful of divergences,
  that is an audit, not a reconcile.


## Version policy

The sequencing discipline is version-agnostic; the **commands in the gate are not**. Take the build, test, format, and migration commands from the orientation pass — the project's own — never a guessed default (`dotnet build`/`dotnet test`/`dotnet format` · `./gradlew build`/`./gradlew test` · `npm|pnpm run build`/`test`, with the package manager read from `packageManager` in `package.json`). Where a task upgrades a runtime or framework major, it is its own task with its own justification, per `CLAUDE.md`'s version policy — never a side effect of a feature task.
