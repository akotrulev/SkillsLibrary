---
name: be-shared-delivery-plan
description: Use when a planned backend (blueprint + data model + API surface + integrations) needs turning into an ordered task list — one flat sequence of tasks, each with a deliverable and an executing agent, plus named streams, a HANDOFF.md pointer, and a reconcile against half-built code. Triggers "what order do we build this in", "turn the plan into tasks", "pick up where we left off". Do NOT use to write code (`be-<stack>`), run a plan (`ep-executing-plans`), or audit code vs spec (`code-auditor`).
---

# Delivery Plan — the ordered, agent-bound task list

The artifact that turns four design documents into work. Two things make it different from a generic plan:

- **Every task names its executor** — an exact agent name from this library plus the skills it should load. That binding is what lets the plan run unattended, inline or through Mission Control.
- **It survives interruption.** `HANDOFF.md` says what to pick up next, and the reconcile procedure re-derives the state from the code when the plan's own record is stale — because a plan whose status you have to trust is a plan you have to redo.
- **It is the progress record.** Once implementation starts, status, evidence, ticked criteria and an append-only execution log are maintained **in this document** — not only in `HANDOFF.md`, and not only in someone's memory of the session. See *Tracking execution in the plan document*.

**The unit of work is a task, and the plan is one flat list of them.** Tasks are numbered `T1…Tn` in the order they are done, and there is no grouping layer above them — no phases, no slices, no stages, no milestones. What used to be carried by a grouping is carried by three things on the task itself: its position in the order, its `Depends on` edges, and its stream. Use the word **task** everywhere — in this document, in `HANDOFF.md`, in status reports, and when talking to the human.

**Every task states one deliverable** — the observable thing that exists once it is done. See Step 4.

And one property decides the shape of the sequence: **how the plan will be executed**. User-facing work is sequenced *feature-complete* by default — the tasks for one capability run consecutively and the last of them makes the capability usable, rather than a layer being finished across every area first — but a plan one operator will run in back-to-back batches is sequenced *agent-batched* instead: a contract wave, then one batch per backend module, then one per frontend area. See Step 2.

**Announce at start:** "I'm using the `be-shared-delivery-plan` skill to sequence the work."

**Prerequisites:** `blueprint.md` (approved), `data-model.md`, `api-surface.md`, `integrations.md`. Sequencing without the detail pack produces task titles, not tasks.

## When to use

- Step 6 of a `be-planner` run
- `RESUME` — reconciling an existing plan against partially-built code and re-sequencing what remains
- `EXTEND` — appending tasks for a new functional area

## When NOT to use

- Executing the plan → `ep-executing-plans` (inline, the default) or the named `be-<stack>` agent per task
- A generic non-backend multi-step task → `ep-writing-plans`
- Auditing what got built against what was specified → `code-auditor`

## Output

**`docs/plans/<NNN>-<initiative>/delivery-plan.md`** and **`docs/plans/<NNN>-<initiative>/HANDOFF.md`**.

**A filled golden example is at `references/example-delivery-plan.md`** (the shared `001-workshop-booking` pack — shapes normative, domain content illustrative); the filled `HANDOFF.md` example is inside `references/handoff-template.md`.

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

**A user-facing capability is not a row — it is the sum of several.** Where the initiative delivers something a person does (place an order, book a session, reset a password), the table gives you the *pieces*; what makes them a feature is that all of them exist at once. Before sequencing, write down, per capability, the full set it needs to be usable end to end:

> schema + entities + the domain rules → the service/orchestration → the endpoints and their request/response contracts → the validation & error deltas → the authorization rule → registration and wiring (DI, route module, config keys) → unit tests → the screens that carry it (`experience-plan.md`'s journey for the capability) → and whatever makes it **reachable**: the migration applied, seed/reference data, a feature flag defaulted to on, the OpenAPI asset when a consumer is generated from it.

That set is what Step 2 sequences. A capability missing any of it has been planned, not delivered — and "the endpoints exist but nothing registers them" is the way this fails most often.

### Step 2 — Put the tasks in workable order

**One flat sequence, `T1…Tn`, in the order the work is done.** No grouping layer sits above the tasks: what makes the order safe is that each task's inputs are produced by tasks above it, and that every such prerequisite is written on the task as a `Depends on` edge. There is no barrier to hide behind — **adjacency is not a dependency claim, so an edge that is not written down does not exist.**

The order must satisfy four things:

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

A **stream** is a named lane. Tasks in one stream run strictly one after another; different streams run at the same time. The question to answer is **"which lanes does this work actually have, and why is each one internally sequential?"**, which is answerable from the file sets you just wrote down.

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
**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
**Stream:** `ordering` · **Order:** 12
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

**Out of scope:** contract/integration tests (`qa-api-dotnet`), the stock-reservation client (T18).
```

Rules:

- **`Deliverable` is the one observable thing that exists when the task is done**, stated as a fact about the world rather than as an activity. "Implement the Orders service" is not a deliverable; "`POST /orders` accepts a valid order and returns `201` with the created id" is. It is one line, it is checkable by someone who did not do the work, and it is the first thing written — a task whose deliverable you cannot state is not yet one task. The acceptance criteria say how it is verified in detail; the deliverable says what it *is*. Where the task is the last of a capability's run, its deliverable is the behavioural sentence for the whole capability (see Step 2).
- **`Agent` is an exact catalog name**, picked from the routing-map catalog in `blueprint.md` (authored by `be-shared-solution-blueprint` — that catalog is the single authoritative list; `be-dotnet`, `data-architect`, `qa-api-<stack>` are the shape). An invented name is the most damaging defect in the pack, because Mission Control binds on this string. Same for skill names. When the chosen stack has no skill for a concern the task needs (e.g. `be-node` currently ships no service-side auth skill), bind the task to the stack agent anyway, note the gap in the Skills cell (`— no <concern> skill for this stack; the agent works from the design pack`), and add an open question — never invent a skill name to fill the hole.
- **Human prerequisite tasks use `Agent: human`.** Provisioning work from `integrations.md`'s blocking unknowns — accounts, tenants, sandbox access — is a real task with a real id, but its executor is a person: the Agent cell is the literal `human` and the task block carries an `**Owner:**` line naming who does it. `human` is exempt from catalog-name resolution, and Mission Control treats these tasks as gates to satisfy, never lanes to schedule.
- **`Files` must be specific.** This is what the stream check relies on, and it is the difference between a plan and a wish.
- **`Stream` is one of the ids declared in Step 3**, and `Order` is that task's slot in the plan-wide sequence. **Every task carries both, or no task does** — half-authored lanes are rejected rather than completed, because back-filling the rest would scatter tasks into lanes nobody planned. A `Stream` naming an undeclared lane and two tasks claiming one `Order` are both reported as plan defects, and the undeclared lane also costs you the lanes you did author: the whole plan falls back to derived ones.
- **Acceptance criteria are checkable**, and they cite the design pack by section rather than restating it. "Handles errors properly" is not a criterion; "returns the documented `type` slug for each of the three deltas" is.
- **The build/test command is the project's own**, taken from the orientation pass — never a guessed default.
- **Size a task by coherence, not by volume.** A task is one thing, done once — a resource, a migration set, an external client, a capability's endpoint surface — and it is exactly as big as that thing is. File counts and criterion counts are not a limit: work that genuinely needs fourteen files is one task, and cutting it into "the entity" and "the service" produces two tasks neither of which can be verified alone. **The deliverable is the test**: one task, one deliverable. Two deliverables means two tasks; no statable deliverable means it is a fragment of one. **Split when it stops being one thing**: it delivers two independent behaviours; a natural intermediate point exists where the work is meaningfully complete *and* checkable on its own; part of it is blocked while the rest is not; or two different agents own the halves. Every piece of a split must still build, still pass its own tests, and still be independently verifiable — a split that leaves the tree broken between the pieces was a bad seam, and the two pieces are one task. When a task is large, its **acceptance-criteria list is its step breakdown**, ticked off in place as the work lands.
- **A batch is still one task, and it still states one deliverable.** Under agent-batched sequencing a task is the whole module or the whole screen area, its acceptance-criteria list is the per-piece breakdown (one criterion per endpoint, per screen, per rule), and its deliverable is the one sentence that covers the set — *"every endpoint under `/bookings` implements its documented behaviour and validation"*, not a list of five. A batch whose deliverable takes two sentences was two batches; a batch of unrelated leftovers grouped because one agent happens to own them is a bucket, not a task, and it is split.
- **Frontend tasks cite their screens.** A task bound to `fe-react` / `fe-blazor` names the `experience-plan.md` screen ids it delivers (`S3`, `S4`) and the journey it completes (`J1`), lists `design-ux-patterns` in its skills, and carries `experience-plan.md` §6's responsiveness budget as acceptance criteria verbatim; the capability's last task is usually this one, and its deliverable is the journey's behavioural sentence.
- **`Out of scope` per task** — mostly to keep the executing agent from wandering into a peer's lane.
- **Tasks are implementation.** Live/E2E/integration test runs, starting servers, and manual verification belong to a separate QA pass owned by a `qa-*` peer. Unit tests are part of the implementation task, not a separate one.

### Step 5 — The progress table

The scannable index, and the thing `HANDOFF.md` points at. Rows sorted by `#`, which makes the sequence auditable at a glance — a repeat or a gap is visible without cross-reading the task blocks, and the whole plan reads top to bottom as "what gets delivered, in what order". `#` **is** the plan-wide `order` Mission Control consumes; the task blocks repeat it as `Order:`, and the two must agree. The `Deliverable` cell is the task block's deliverable line, shortened to fit — same claim, fewer words:

| # | Task | Stream | Title | Deliverable | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 12 | T12 | `ordering` | Orders resource | The five Orders endpoints are live and reachable | `be-dotnet` | T4, T9, T10 | Not started | — |

Status vocabulary — six values, no others: **Not started · In progress · Done · Partial · Diverged · Blocked**. `Evidence` holds the `file:line` or command output that justifies a `Done` or `Partial`. An empty Evidence cell on a `Done` row is a defect in the plan, not a formatting gap.

### Step 6 — Write `HANDOFF.md`

The pointer file — see `references/handoff-template.md` for the full template and its rules. **It answers one question: what does the next agent do next.** The next unblocked task per lane, where to start inside it, what is blocking, and the working-tree state that goes stale fastest. It is **rewritten each session, never appended**.

**Progress does not live here.** Status, evidence, ticked criteria, the execution log, the decisions and the deviations all live in `delivery-plan.md` — one record, in the document that defines the work. The handoff cites task ids and never restates their history; anything it would duplicate is a line the two files will eventually disagree about.

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

**Streams are mandatory, not an optimization.** With no grouping level in the plan, `streams[]` + `order` + `dependsOn[]` are the whole concurrency story: the streams say what may run at the same time, and the dependencies say what must not. A pack that omits them leaves MC nothing to derive lanes from but the raw sequence, and it will run the plan strictly serially — correct, but one lane wide. Author the streams.

---

## Tracking execution in the plan document

Once implementation starts, **this document is the record of what has been done.** `HANDOFF.md` says only what to do next and is rewritten each session; the plan carries the durable per-task history and is never rewritten backwards. Where the two touch, the plan is the record.

The executing agent (or the human) updates the plan **as part of the task**, not as a write-up afterwards:

| When | Update in `delivery-plan.md` |
|---|---|
| Starting a task | Progress row → `In progress`; one execution-log row |
| Meeting an acceptance criterion | Tick its checkbox in the task block, in place |
| Finishing a task | Progress row → `Done`, with `file:line` or command output in the Evidence cell; every criterion ticked; one execution-log row |
| Stopping mid-task | Progress row → `Partial`, plus a `**Progress:**` line in the task block naming what remains — the unticked criteria are that list |
| Building it differently | Progress row → `Diverged`; both readings in the task block; the resolution recorded in §7 once the human picks |
| Hitting a blocker | Progress row → `Blocked`, naming what on and who owns it; one execution-log row |
| Finishing a capability's last task | Record that its behavioural deliverable now holds, with how it was checked |

Rules:

- **The deliverable is what `Done` means.** A task is `Done` when its stated deliverable exists, not when its steps were performed. Every criterion ticked with the deliverable absent is a `Partial`.
- **Evidence, not assertion.** `Done` and `Partial` carry the `file:line` or command output that proves them, produced in the session that wrote the status. The rule the reconcile runs on applies first to the person writing the status.
- **The execution log is append-only.** Rows are added, never edited or deleted — a task that regresses gets a new row, not a corrected one. It is the one part of the pack that is history rather than a statement of now, and it is what makes *"what has been done"* answerable without reading git.
- **Decisions and deviations are recorded in the plan** (§7), because they outlive the session that made them. A deviation that lives only in a rewritten handoff is gone by Monday.
- **Never delete a task that turned out to be unnecessary.** Mark it, say why, keep the id. A task that vanishes reads as a task that was forgotten.
- **The status is still a lead to a cold agent.** A `Done` written last month is re-verified against the code on a RESUME, per the reconcile procedure below. Recording status well makes that reconcile cheap; it does not replace it.
- **Regenerate `delivery-plan-explained.md` when the plan is re-sequenced**, not on every status tick — the companion explains the sequence, not the progress.

---

## The reconcile procedure (RESUME mode)

Run this **before** re-sequencing anything, when a plan and partially-built code both exist. It is the mode this skill earns its keep in.

**The governing rule: the plan is a lead, not evidence.** A checked box, a green pipeline, a commit message, this plan's own execution log, and a previous `HANDOFF.md` are all claims. Status is assigned only after reading the code **this session**.

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
7. **Re-sequence what remains**, then rewrite `HANDOFF.md`.

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
**Pack:** `./blueprint.md` · `./data-model.md` · `./experience-plan.md` (when user-facing) · `./api-surface.md` · `./integrations.md`
**Target repo:** `<path>` · **Stack:** <stack + version> · **Build/test:** `<the project's own commands>`
**Sequencing shape:** feature-complete | agent-batched | platform-first — <the execution model that selected it>

> **For agentic workers:** the tasks below are one flat sequence — work them in order. Each names
> the agent that should execute it, the skills to load, and the one deliverable that means it is done.
> Run them with `ep-executing-plans` inline, or hand the whole document to Mission Control.
> **Update this document as you work** — the Status and Evidence cells in §2, the criterion
> checkboxes in §3, an append-only row in §6, and any decision or deviation in §7.
> `HANDOFF.md` says only what to pick up next.

## 1. Streams
| Stream | Owns | Why it is internally sequential |
|---|---|---|

## 2. Progress
| # | Task | Stream | Title | Deliverable | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|

## 3. Tasks
<!-- one block per task, in order: deliverable, agent, skills, stream + order, depends on, files, intent, acceptance criteria, out of scope -->

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
6. Every `dependsOn` id exists, and every one points backwards in `order`.
7. Every task names a declared stream and carries a unique `order`; every stream's row says why it is internally sequential; every pair of tasks whose `Files` overlap is ordered against each other — same stream or a `dependsOn` edge between them.
8. Every task's acceptance criteria are checkable and cite the design pack by section.
9. The build/test commands are the project's own, from the orientation pass.
10. `HANDOFF.md` exists, names the next task per unblocked lane and every blocker — and carries no progress record of its own.
11. Every `Done`/`Partial` status carries `file:line` evidence read this session.
12. Sections 6 and 7 exist (empty before execution starts), and the header note tells the executing agents to maintain §2, §3, §6 and §7 as they work.

## Handoffs

- **→ `be-dotnet` / `be-java` / `be-node`** — execute the tasks bound to them, and update this document's §2/§3/§6/§7 as each task moves.
- **→ `ep-executing-plans`** — the task-by-task execution loop, with checkpoints; its per-task checkpoint is where this plan's status, evidence and execution log get written. `ep-delegate-to-subagents` runs the same tasks through subagents — the controller, not the subagent, owns the plan update.
- **→ Mission Control** — paste the document, point at the repo.
- **→ `data-architect` / `devops-engineer` / `observability-engineer-<stack>` / `qa-*`** — the tasks bound to them, run as peers.
- **→ `code-auditor`** — when a reconcile finds systemic drift rather than a handful of divergences, that is an audit, not a reconcile.
- **→ `be-shared-plain-language-companion`** — writes `delivery-plan-explained.md` beside this document for the stakeholders who need the order, the deliverables and the blockers without the task ids and agent bindings. Regenerate it whenever this plan is re-sequenced.

## Version policy

The sequencing discipline is version-agnostic; the **commands in acceptance criteria are not**. Take the build, test, format, and migration commands from the orientation pass — the project's own — never a guessed default (`dotnet build`/`dotnet test`/`dotnet format` · `./gradlew build`/`./gradlew test` · `npm|pnpm run build`/`test`, with the package manager read from `packageManager` in `package.json`). Where a task upgrades a runtime or framework major, it is its own task with its own justification, per `CLAUDE.md`'s version policy — never a side effect of a feature task.
