---
name: be-shared-delivery-plan
description: Use when a planned build (blueprint + data model + API surface + integrations + epic map) needs turning into an ordered task list — one flat sequence of tasks, each with a deliverable, one stack, one executing agent and a context estimate, plus named streams derived from the epic map and a reconcile against half-built code. Triggers "what order do we build this in", "turn the plan into tasks", "pick up where we left off". Do NOT use to write code (`be-<stack>`), size tasks or write the next prompts (`be-shared-session-budget`), decide what runs in parallel at epic level (`be-shared-epic-map`), run a plan (`ep-executing-plans`), or audit code vs spec (`code-auditor`).
---

# Delivery Plan — the ordered, agent-bound task list

The artifact that turns the design pack into work. Three things make it different from a generic plan:

- **Every task names its executor and its stack** — exactly one stack, exactly one agent name from this library, plus the skills it should load. That binding is what lets the plan run unattended, inline or through Mission Control, and it is what makes a task handable to a single agent without it wandering across a boundary it does not own.
- **It survives interruption.** `NEXT-PROMPTS.md` says what to run next — as a prompt, not a description — and the reconcile procedure re-derives the state from the code when the plan's own record is stale, because a plan whose status you have to trust is a plan you have to redo.
- **It is the progress record.** Once implementation starts, status, evidence, ticked criteria and an append-only execution log are maintained **in this document** — not only in `NEXT-PROMPTS.md`, and not only in someone's memory of the session. See *Tracking execution in the plan document*.

**The unit of work is a task, and the plan is one flat list of them.** Tasks are numbered `T1…Tn` in the order they are done, and there is no grouping layer above them — no phases, no slices, no stages, no milestones. What used to be carried by a grouping is carried by four things on the task itself: its position in the order, its `Depends on` edges, its stream, and the epic and story it serves. Use the word **task** everywhere — in this document, in `NEXT-PROMPTS.md`, in status reports, and when talking to the human.

**Every task states one deliverable** — the observable thing that exists once it is done. See Step 4.

**Every task belongs to exactly one epic, one story, one stack and one agent, and is executed in one session.** The epic and story come from `epics.md` / `stories.md` by way of `epic-map.md`; the stack is one of `be` · `fe` · `ts` · `data` · `infra` · `qa` · `docs` · `human`; and the session estimate is derived by `be-shared-session-budget` while the task is being authored, not measured afterwards.

> **A task that touches both the API tree and the web tree is two tasks.** There is no mixed task at any size, and no estimate justifies one.

And one property decides the shape of the sequence: **how the plan will be executed**. User-facing work is sequenced *feature-complete* by default — the tasks for one capability run consecutively and the last of them makes the capability usable, rather than a layer being finished across every area first — but a plan one operator will run in back-to-back batches is sequenced *agent-batched* instead: a contract wave, then one batch per backend module, then one per frontend area. See Step 2.

**Announce at start:** "I'm using the `be-shared-delivery-plan` skill to sequence the work."

**Prerequisites:** `blueprint.md` (approved), `data-model.md`, `api-surface.md`, `integrations.md`, and `epic-map.md` — whose lanes and waves this plan's streams and order are derived from, not re-decided. Sequencing without the detail pack produces task titles, not tasks; sequencing without the epic map produces a plan that is one lane wide.

## When to use

- Step 7 of a `solution-planner` run
- `RESUME` — reconciling an existing plan against partially-built code and re-sequencing what remains
- `EXTEND` — appending tasks for a new functional area

## When NOT to use

- Executing the plan → `ep-executing-plans` (inline, the default) or the named stack agent per task
- Deciding which epics run at the same time → `be-shared-epic-map`, which this skill consumes
- Sizing the tasks and writing `NEXT-PROMPTS.md` → `be-shared-session-budget`, which runs on this skill's output
- A generic non-backend multi-step task → `ep-writing-plans`
- Auditing what got built against what was specified → `code-auditor`

## Output

**`docs/plans/<NNN>-<initiative>/delivery-plan.md`**. `NEXT-PROMPTS.md` sits beside it and is written by `be-shared-session-budget` from these tasks — this skill produces the tasks and points at that file; it does not author it.

**A filled golden example is at `references/example-delivery-plan.md`** (the shared `001-workshop-booking` pack — shapes normative, domain content illustrative); the paired `NEXT-PROMPTS.md` example is in `backend/_shared/session-budget/references/next-prompts-template.md`.

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

**One flat sequence, `T1…Tn`, in the order the work is done.** No grouping layer sits above the tasks: what makes the order safe is that each task's inputs are produced by tasks above it, and that every such prerequisite is written on the task as a `Depends on` edge. There is no barrier to hide behind — **adjacency is not a dependency claim, so an edge that is not written down does not exist.**

The order must satisfy five things:

- **The order is a valid serialization of `epic-map.md`'s dependency graph.** No task is ordered before anything it transitively depends on, cross-epic edges included. That is the whole constraint the epic map places on the order — **it does not require the waves to be worked one at a time.** A wave-3 lane's task may sit above a wave-2 lane's task when its own dependencies are already met, and under feature-complete sequencing it usually will: the order is the single sequence one person would work through, while the waves are the claim about what *could* be open at once, which the streams table carries. Where a dependency edge makes the order impossible, the epic map is wrong — report it and fix it there.
- **Startable at its position.** Everything a task imports, calls, migrates against, registers with, or configures exists by the time its turn comes. If it does not, the task is in the wrong place — move it, don't annotate it.
- **Working tree at every task boundary.** Each task ends with the project building and its tests green, so the plan can stop after any task and what exists still runs. A task that leaves the build red until the next one lands is not a boundary; the two are one task.
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
- **Nothing about task discipline relaxes.** A batch *is* a task, so the tree still builds and its unit tests still pass at every task boundary, and those unit tests are still written inside the batch that writes the code. The only thing this shape defers to the end is the live/integration/E2E pass — which was already a separate `qa-*` pass, not a licence to ship untested code.

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

Give the plan a streams table, before the progress table:

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

```markdown
### T12 — Orders resource

**Deliverable:** the five Orders endpoints are live and reachable — a caller with the `orders:write`
permission can place, cancel and close an order, and list or get their own.
**Epic:** `E2` Ordering · **Story:** `US7` · **Stack:** `be`
**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
**Stream:** `ordering-api` · **Order:** 12
**Est. context:** ~110k — 6 files created, 1 modified, 3 skills, 4 pack sections
**Depends on:** T4 (schema), T9 (auth wiring), T10 (shared DTOs + error middleware)
**Files:**
- Create: `src/Ordering/Domain/Order.cs`, `src/Ordering/Domain/OrderLine.cs`
- Create: `src/Ordering/Infrastructure/OrderConfiguration.cs`
- Create: `src/Ordering/Application/OrderService.cs`
- Create: `src/Ordering/Api/OrdersEndpoints.cs`
- Create: `tests/Ordering.Tests/OrderServiceTests.cs`
- Modify: `src/Ordering/DependencyInjection.cs`

**Intent:** implement the Orders resource — entity, EF Core configuration, service, and the five
endpoints in `api-surface.md` §5 (list, get, place, cancel, close), with the standard validation set.

**Acceptance criteria:**
- [ ] All five endpoints match `api-surface.md` §5 exactly: paths, request/response fields, status codes
- [ ] The standard validation set applies; the three endpoint-specific deltas (`insufficient-stock`,
      `idempotency-conflict`, `currency-not-enabled`) return the documented `type` slugs
- [ ] Cross-tenant access returns 404, per the API's V5.3 disclosure choice
- [ ] Illegal state transitions return 409 naming the current and allowed states
- [ ] Unit tests cover every validation branch and every state transition
- [ ] `dotnet build` clean, 0 warnings; `dotnet test` green; `dotnet format --verify-no-changes`

**Out of scope:** the Orders screens (T19, stack `fe`, same epic — the endpoints are not reachable from
the UI until it lands), contract/integration tests (`qa-api-dotnet`), the stock-reservation client (T18).
```

Rules:

- **`Epic`, `Story` and `Stack` are on every task, or on none.** `Epic` is an `E` id from `epic-map.md` (`E0` for foundation and contract work); `Story` is a `US` id from `stories.md`, or `—` for an `E0` task; `Stack` is exactly one of `be` · `fe` · `ts` · `data` · `infra` · `qa` · `docs` · `human`. A task naming two stacks is two tasks, reported as a plan defect rather than resolved by picking the larger one. A `Story` id that does not exist in `stories.md`, or an `Epic` that does not exist in `epic-map.md`, is a defect in the citation, not licence to invent the backlog entry.
- **`Est. context` is derived by `be-shared-session-budget` while the task is authored**, and it carries its drivers — `~110k — 6 files created, 1 modified, 3 skills, 4 pack sections` — so a reader can tell a 110k of many small files from a 110k of one large one. It is a target, never a gate: one deliverable, one stack and one agent, and a green tree at the boundary all outrank it. Re-derive it whenever the task's `Files`, `Skills` or cited sections change; a stale estimate is worse than none, because it is a number someone will trust.
- **`Deliverable` is the one observable thing that exists when the task is done**, stated as a fact about the world rather than as an activity. "Implement the Orders service" is not a deliverable; "`POST /orders` accepts a valid order and returns `201` with the created id" is. It is one line, it is checkable by someone who did not do the work, and it is the first thing written — a task whose deliverable you cannot state is not yet one task. The acceptance criteria say how it is verified in detail; the deliverable says what it *is*. Where the task is the last of a capability's run, its deliverable is the behavioural sentence for the whole capability (see Step 2).
- **`Agent` is an exact catalog name**, picked from the routing-map catalog in `blueprint.md` (authored by `be-shared-solution-blueprint` — that catalog is the single authoritative list; `be-dotnet`, `data-architect`, `qa-api-<stack>` are the shape). An invented name is the most damaging defect in the pack, because Mission Control binds on this string. Same for skill names. When the chosen stack has no skill for a concern the task needs (e.g. `be-node` currently ships no service-side auth skill), bind the task to the stack agent anyway, note the gap in the Skills cell (`— no <concern> skill for this stack; the agent works from the design pack`), and add an open question — never invent a skill name to fill the hole.
- **Human prerequisite tasks use `Agent: human`.** Provisioning work from `integrations.md`'s blocking unknowns — accounts, tenants, sandbox access — is a real task with a real id, but its executor is a person: the Agent cell is the literal `human` and the task block carries an `**Owner:**` line naming who does it. `human` is exempt from catalog-name resolution, and Mission Control treats these tasks as gates to satisfy, never lanes to schedule.
- **`Files` must be specific.** This is what the stream check relies on, and it is the difference between a plan and a wish.
- **`Stream` is one of the ids declared in Step 3**, and `Order` is that task's slot in the plan-wide sequence. **Every task carries both, or no task does** — half-authored lanes are rejected rather than completed, because back-filling the rest would scatter tasks into lanes nobody planned. A `Stream` naming an undeclared lane and two tasks claiming one `Order` are both reported as plan defects, and the undeclared lane also costs you the lanes you did author: the whole plan falls back to derived ones.
- **Acceptance criteria are checkable**, and they cite the design pack by section rather than restating it. "Handles errors properly" is not a criterion; "returns the documented `type` slug for each of the three deltas" is.
- **The build/test command is the project's own**, taken from the orientation pass — never a guessed default.
- **Size a task by coherence, not by volume.** A task is one thing, done once — a resource, a migration set, an external client, a capability's endpoint surface — and it is exactly as big as that thing is. File counts and criterion counts are not a limit: work that genuinely needs fourteen files is one task, and cutting it into "the entity" and "the service" produces two tasks neither of which can be verified alone. **The deliverable is the test**: one task, one deliverable. Two deliverables means two tasks; no statable deliverable means it is a fragment of one. **Split when it stops being one thing**: it delivers two independent behaviours; a natural intermediate point exists where the work is meaningfully complete *and* checkable on its own; part of it is blocked while the rest is not; or two different agents own the halves. Every piece of a split must still build, still pass its own tests, and still be independently verifiable — a split that leaves the tree broken between the pieces was a bad seam, and the two pieces are one task. When a task is large, its **acceptance-criteria list is its step breakdown**, ticked off in place as the work lands. The session estimate informs this and never decides it: under ~80k, look at the next task in the same story and same stack and merge only if the result still states one deliverable; over ~150k, annotate the task and name its natural split point. A task that overshoots with one deliverable, one stack and a green boundary is a large task correctly authored — label it, do not file it as a defect.
- **A batch is still one task, and it still states one deliverable.** Under agent-batched sequencing a task is the whole module or the whole screen area, its acceptance-criteria list is the per-piece breakdown (one criterion per endpoint, per screen, per rule), and its deliverable is the one sentence that covers the set — *"every endpoint under `/bookings` implements its documented behaviour and validation"*, not a list of five. A batch whose deliverable takes two sentences was two batches; a batch of unrelated leftovers grouped because one agent happens to own them is a bucket, not a task, and it is split.
- **Frontend tasks cite their screens.** A task bound to `fe-react` / `fe-blazor` names the `experience-plan.md` screen ids it delivers (`S3`, `S4`) and the journey it completes (`J1`), lists `design-ux-patterns` in its skills, and carries `experience-plan.md` §6's responsiveness budget as acceptance criteria verbatim; the capability's last task is usually this one, and its deliverable is the journey's behavioural sentence.
- **`Out of scope` per task** — mostly to keep the executing agent from wandering into a peer's lane.
- **Tasks are implementation.** Live/E2E/integration test runs, starting servers, and manual verification belong to a separate QA pass owned by a `qa-*` peer. Unit tests are part of the implementation task, not a separate one.

### Step 5 — The progress table

The scannable index, and the row a `NEXT-PROMPTS.md` block is built from. Rows sorted by `#`, which makes the sequence auditable at a glance — a repeat or a gap is visible without cross-reading the task blocks, and the whole plan reads top to bottom as "what gets delivered, in what order". `#` **is** the plan-wide `order` Mission Control consumes; the task blocks repeat it as `Order:`, and the two must agree. The `Deliverable` cell is the task block's deliverable line, shortened to fit — same claim, fewer words:

| # | Task | Epic | Story | Stack | Stream | Title | Deliverable | Agent | Est. | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | T12 | `E2` | `US7` | `be` | `ordering-api` | Orders resource | The five Orders endpoints are live and reachable | `be-dotnet` | ~110k | T4, T9, T10 | Not started | — |

Status vocabulary — six values, no others: **Not started · In progress · Done · Partial · Diverged · Blocked**. `Evidence` holds the `file:line` or command output that justifies a `Done` or `Partial`. An empty Evidence cell on a `Done` row is a defect in the plan, not a formatting gap. The `Est.` cell repeats the task block's `Est. context` figure and must agree with it; the drivers stay on the block.

The table is scannable by epic and by stack on purpose: **every runnable lane's next task is one filter away**, which is exactly what `be-shared-session-budget` needs to rewrite a `NEXT-PROMPTS.md` block without re-reading the whole plan.

### Step 6 — Point at `NEXT-PROMPTS.md`

**This skill does not author it.** `be-shared-session-budget` writes `NEXT-PROMPTS.md` from these tasks — one ready-to-paste prompt block per lane that is runnable right now, with the exact agent, the exact skills, the exact pack **sections**, the deliverable, the files, the criteria, and the closing duty. What this skill owes it is what a block is built from: a task block with `Epic` / `Story` / `Stack` / `Agent` / `Skills` / `Files` / `Est. context` filled in, and a streams table that says which lanes exist.

Close this document's header note by naming that file, so an executing agent knows both halves of its duty: **the record goes in `delivery-plan.md`; the next prompt goes in `NEXT-PROMPTS.md`.**

**Progress lives here, and only here.** Status, evidence, ticked criteria, the execution log, the decisions and the deviations all stay in this document. `NEXT-PROMPTS.md` is rewritten as each task lands and holds nothing durable; where the two disagree, this plan is right.

There is no `HANDOFF.md`. It answered the same question in prose and is retired — two files answering "what next" is one file and one thing that drifts.

### Step 7 — The Mission Control section

Close the document with an ingestion block so the plan can be pasted into Mission Control and produce a near-identical task graph:

```markdown
## For Mission Control

Paste this document into the plan box and point the run at `<target repo path>`.
The task graph maps 1:1 — the streams in §1 become MC's lanes, each task keeps its
`stream` and `order` alongside its `deliverable`, `agent`, `skills`, `files` and
`dependsOn`, and the open questions below carry their options. There is no grouping
level: ordering is the `order` sequence, and every prerequisite is an explicit
`dependsOn` edge. MC's planner re-reads the target repo, so it may split a task it
finds too large; that is expected and does not invalidate the sequence — the new
pieces belong in the split task's own lane, and each needs its own deliverable.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
```

Mission Control's planner consumes exactly these fields — run-level `streams[]` (`id · name · description`), per-task `id · streamId · order · title · deliverable · intent · acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]`, and `openQuestions[]` with 2–4 options each and one recommended. Writing them in that vocabulary is the entire compatibility requirement.

**`epic`, `story`, `stack` and `estContext` are additive** — MC ignores fields it does not know, so carrying them costs nothing and losing them costs the whole epic and sizing story on a round trip. Write them per task alongside the fields above.

**Streams are mandatory, not an optimization.** With no grouping level in the plan, `streams[]` + `order` + `dependsOn[]` are the whole concurrency story: the streams say what may run at the same time, and the dependencies say what must not. A pack that omits them leaves MC nothing to derive lanes from but the raw sequence, and it will run the plan strictly serially — correct, but one lane wide. Author the streams.

---

## Tracking execution in the plan document

Once implementation starts, **this document is the record of what has been done.** `NEXT-PROMPTS.md` says only what to run next and is rewritten as each task lands; the plan carries the durable per-task history and is never rewritten backwards. Where the two touch, the plan is the record.

The executing agent (or the human) updates the plan **as part of the task**, not as a write-up afterwards:

| When | Update in `delivery-plan.md` | And in `NEXT-PROMPTS.md` |
|---|---|---|
| Starting a task | Progress row → `In progress`; one execution-log row | — |
| Meeting an acceptance criterion | Tick its checkbox in the task block, in place | — |
| Finishing a task | Progress row → `Done`, with `file:line` or command output in the Evidence cell; every criterion ticked; one execution-log row | Replace this lane's block with the next task's prompt |
| Finishing a lane's last task | As above | Replace the block with a closed-lane line; check `epic-map.md` — a finished lane usually opens a wave, and every newly runnable lane needs a block |
| Stopping mid-task | Progress row → `Partial`, plus a `**Progress:**` line in the task block naming what remains — the unticked criteria are that list | Block stays on the **same** task, with a `Picking up from:` line |
| Building it differently | Progress row → `Diverged`; both readings in the task block; the resolution recorded in §7 once the human picks | Block stays on the same task until the human resolves it |
| Hitting a blocker | Progress row → `Blocked`, naming what on and who owns it; one execution-log row | Block stays, and names the blocker and its owner. Deleting it loses the lane |
| Finishing a capability's last task | Record that its behavioural deliverable now holds, with how it was checked | — |

The `NEXT-PROMPTS.md` half is `be-shared-session-budget`'s Step 5, and it is part of finishing the task rather than a write-up afterwards. The block is built from the next task's own block in §3 — deliverable, files, criteria and out-of-scope copied, never paraphrased.

Rules:

- **The deliverable is what `Done` means.** A task is `Done` when its stated deliverable exists, not when its steps were performed. Every criterion ticked with the deliverable absent is a `Partial`.
- **Evidence, not assertion.** `Done` and `Partial` carry the `file:line` or command output that proves them, produced in the session that wrote the status. The rule the reconcile runs on applies first to the person writing the status.
- **The execution log is append-only.** Rows are added, never edited or deleted — a task that regresses gets a new row, not a corrected one. It is the one part of the pack that is history rather than a statement of now, and it is what makes *"what has been done"* answerable without reading git.
- **Decisions and deviations are recorded in the plan** (§7), because they outlive the session that made them. A deviation that lives only in a rewritten handoff is gone by Monday.
- **Never delete a task that turned out to be unnecessary.** Mark it, say why, keep the id. A task that vanishes reads as a task that was forgotten.
- **The status is still a lead to a cold agent.** A `Done` written last month is re-verified against the code on a RESUME, per the reconcile procedure below. Recording status well makes that reconcile cheap; it does not replace it.

---

## The reconcile procedure (RESUME mode)

Run this **before** re-sequencing anything, when a plan and partially-built code both exist. It is the mode this skill earns its keep in.

**The governing rule: the plan is a lead, not evidence.** A checked box, a green pipeline, a commit message, this plan's own execution log, and a previous `NEXT-PROMPTS.md` block are all claims. Status is assigned only after reading the code **this session**.

1. **Read the design pack**, so you know what was supposed to exist.
2. **Walk each task** in the progress table and look for its artifacts — the files it names, the migration, the endpoint, the registration.
3. **Assign a verdict** with `file:line` evidence:

| Verdict | Means |
|---|---|
| **Done** | The deliverable exists and every acceptance criterion is satisfied by code you read this session |
| **Partial** | Some criteria satisfied; name exactly which are missing |
| **Not started** | No artifacts found. Say what you searched for — a negative claim needs its search named |
| **Diverged** | Built, but differently from the plan. **Both readings recorded; the human decides** |
| **Blocked** | Cannot proceed — a prerequisite, a missing credential, a red build |

4. **Escalate every divergence.** Usually the code is right and the plan is stale — but you never silently rewrite the plan to match, because the other possibility is a defect. Present both readings, recommend one, and record the resolution in the plan's §7 Decisions & deviations.
5. **Sweep the class.** If one task diverged because the plan assumed a convention the project does not use, every other pending task assuming it is also wrong. Fix them together.
6. **Check the baseline.** Does the repo build and do its tests pass *right now*? A plan that assumes a green baseline while the build is red is wrong from task one. Report a red state as a finding — it is not yours to silently fix.
7. **Re-sequence what remains**, then have `be-shared-session-budget` re-derive the estimates that changed and rewrite `NEXT-PROMPTS.md` from what you found — not from what it previously said.

Report the reconcile as counts plus the divergences in full:

```
Reconcile: 7 Done · 2 Partial · 11 Not started · 1 Diverged · 0 Blocked
Diverged — T9 (auth wiring): plan specifies policy-based authorization;
  code uses role attributes directly (src/Api/Program.cs:44-58).
  Recommend adopting the code and amending the plan — policies buy nothing
  here with three flat roles. Your call.
```

---

## Delivery plan template

```markdown
# <Initiative> — Delivery Plan

**Date:** YYYY-MM-DD · **Written by:** `be-shared-delivery-plan`
**Pack:** `./epics.md` · `./stories.md` · `./blueprint.md` · `./data-model.md` · `./experience-plan.md` (when user-facing) · `./api-surface.md` · `./integrations.md` · `./epic-map.md`
**Target repo:** `<path>` · **Stack:** <stack + version> · **Build/test:** `<the project's own commands>`
**Sequencing shape:** feature-complete | agent-batched | platform-first — <the execution model that selected it>

> **For agentic workers:** the tasks below are one flat sequence — work them in order. Each names
> the agent that should execute it, the skills to load, and the one deliverable that means it is done.
> Run them with `ep-executing-plans` inline, or hand the whole document to Mission Control.
> **Update this document as you work** — the Status and Evidence cells in §2, the criterion
> checkboxes in §3, an append-only row in §6, and any decision or deviation in §7.
> **Then rewrite your lane's block in `NEXT-PROMPTS.md`** for the next task, per
> `be-shared-session-budget` Step 5. The record lives here; the next prompt lives there.

## 1. Streams
<!-- one per `epic-map.md` §2 lane, split by stack where the lane spans two -->
| Stream | Epic | Stack | Owns | Why it is internally sequential |
|---|---|---|---|---|

## 2. Progress
| # | Task | Epic | Story | Stack | Stream | Title | Deliverable | Agent | Est. | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## 3. Tasks
<!-- one block per task, in order: deliverable, epic + story + stack, agent + skills, stream + order,
     est. context, depends on, files, intent, acceptance criteria, out of scope -->

## 4. Open questions
| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|

## 5. Deliberately not planned
<!-- what this initiative excludes and which agent/peer owns it instead -->

## 6. Execution log
<!-- append-only, oldest first: one row per status change. Never edited, never deleted -->
| When | Task | Status | By | Note |
|---|---|---|---|---|

## 7. Decisions & deviations
<!-- answered questions, resolved divergences, and what got built differently from the plan -->
| # | Task | Plan said | What was decided/built | Why | When |
|---|---|---|---|---|---|

## For Mission Control
<!-- ingestion note + blocking open questions -->
```

## Self-check before handing off

1. Every functional area in `blueprint.md` has at least one task; every migration, every resource, every screen in `experience-plan.md`, every external client, every blocking unknown is a task.
2. Reading the tasks in `order`, each one could be started at its position: everything it needs was produced by a task above it.
3. The sequencing shape is stated in the plan header, with the execution model that selected it. Under agent-batched: every batch is one agent against one file tree, every contract-wave stub names the batch that fills it, and the plan says which capability becomes usable at which batch.
4. Every task states one `Deliverable`, as a result rather than an activity. Every user-facing capability has a last task whose deliverable says behaviourally what a user can then do, and the run of tasks ending there covers everything on the Step-1 capability set — including its screens and what makes it reachable, not only its endpoints. Every frontend task cites its screen ids and inherits the responsiveness budget.
5. Every task binds to an **exact** catalog agent name and exact skill names.
6. Every task carries `Epic`, `Story` and `Stack`; every `Stack` is exactly one of the eight values; every `Epic` resolves in `epic-map.md` and every non-`E0` `Story` resolves in `stories.md`. No task names two stacks, and no task touches both the API tree and the web tree.
7. Every task carries an `Est. context` line with its drivers, the §2 `Est.` cell agrees with it, and every estimate over ~150k either names its natural split point or says why the task is one thing anyway.
8. Every `dependsOn` id exists, and every one points backwards in `order`.
9. Every task names a declared stream and carries a unique `order`; every stream's row says why it is internally sequential; every pair of tasks whose `Files` overlap is ordered against each other — same stream or a `dependsOn` edge between them. Every stream traces to an `epic-map.md` §2 lane (or to a stack split of one, recorded back into that document), and the order is a valid serialization of that document's dependency graph.
10. Every task's acceptance criteria are checkable and cite the design pack by section.
11. The build/test commands are the project's own, from the orientation pass.
12. `NEXT-PROMPTS.md` exists beside this plan, with one block per currently-runnable lane and a line for every blocked one — and carries no progress record of its own.
13. Every `Done`/`Partial` status carries `file:line` evidence read this session.
14. Sections 6 and 7 exist (empty before execution starts), and the header note tells the executing agents to maintain §2, §3, §6 and §7 as they work.

## Handoffs

- **← `be-shared-epic-map`** — supplies the epics, the lanes and the waves. The streams table is its §2 at task altitude, and the order respects its §3.
- **→ `be-shared-session-budget`** — sizes these tasks, writes the `Est. context` lines back onto them, and authors `NEXT-PROMPTS.md` from them.
- **→ `be-dotnet` / `be-java` / `be-node` / `fe-react` / `fe-blazor`** — execute the tasks bound to them, update this document's §2/§3/§6/§7 as each task moves, and rewrite their lane's block in `NEXT-PROMPTS.md`.
- **→ `ep-executing-plans`** — the task-by-task execution loop, with checkpoints; its per-task checkpoint is where this plan's status, evidence and execution log get written. `ep-delegate-to-subagents` runs the same tasks through subagents — the controller, not the subagent, owns the plan update.
- **→ Mission Control** — paste the document, point at the repo.
- **→ `data-architect` / `devops-engineer` / `observability-engineer-<stack>` / `qa-*`** — the tasks bound to them, run as peers.
- **→ `code-auditor`** — when a reconcile finds systemic drift rather than a handful of divergences, that is an audit, not a reconcile.

## Version policy

The sequencing discipline is version-agnostic; the **commands in acceptance criteria are not**. Take the build, test, format, and migration commands from the orientation pass — the project's own — never a guessed default (`dotnet build`/`dotnet test`/`dotnet format` · `./gradlew build`/`./gradlew test` · `npm|pnpm run build`/`test`, with the package manager read from `packageManager` in `package.json`). Where a task upgrades a runtime or framework major, it is its own task with its own justification, per `CLAUDE.md`'s version policy — never a side effect of a feature task.
