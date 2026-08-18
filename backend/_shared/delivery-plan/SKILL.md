---
name: be-shared-delivery-plan
description: Use when a planned backend (blueprint + data model + API surface + integrations) needs turning into an ordered, executable task list — phases as hard barriers with named streams (lanes of sequential work) inside them, one task per unit of work bound to an exact library agent and the skills it loads, files touched, dependencies, and acceptance criteria — plus the HANDOFF.md pointer file that says only what to pick up next, and a reconcile procedure that re-verifies a plan against half-built code. Sequences user-facing work feature-complete, so each phase closes on a capability a user can actually exercise, and carries the live execution record — status, evidence, ticked criteria, append-only log — in the plan document itself. Directly ingestible by Mission Control. Triggers "what order do we build this in", "turn the plan into tasks", "which agent builds what", "pick up where we left off", "reconcile the plan against the code", "track what has been done in the plan". Do NOT use to write the code (`be-dotnet`/`be-java`/`be-node`), to execute a generic step-by-step plan (`ep-executing-plans`), or to audit built code against a spec (`code-auditor`).
---

# Delivery Plan — the ordered, agent-bound task list

The artifact that turns four design documents into work. Two things make it different from a generic plan:

- **Every task names its executor** — an exact agent name from this library plus the skills it should load. That binding is what lets the plan run unattended, inline or through Mission Control.
- **It survives interruption.** `HANDOFF.md` says what to pick up next, and the reconcile procedure re-derives the state from the code when the plan's own record is stale — because a plan whose status you have to trust is a plan you have to redo.
- **It is the progress record.** Once implementation starts, status, evidence, ticked criteria and an append-only execution log are maintained **in this document** — not only in `HANDOFF.md`, and not only in someone's memory of the session. See *Tracking execution in the plan document*.

And one property decides the shape of the sequence: **user-facing work is sequenced feature-complete**, so a phase closes on something a person can actually do, rather than on a layer finished across every area. See Step 2.

**Announce at start:** "I'm using the `be-shared-delivery-plan` skill to sequence the work."

**Prerequisites:** `blueprint.md` (approved), `data-model.md`, `api-surface.md`, `integrations.md`. Sequencing without the detail pack produces task titles, not tasks.

## When to use

- Phase 5 of a `be-planner` run
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
| `api-surface.md` endpoint blocks | One task per resource (not per endpoint — a resource's CRUD set is one coherent slice) |
| `integrations.md` dependency blocks | One client task per external system |
| `api-surface.md` outbound webhooks + background work | Job/consumer tasks |
| `api-surface.md` endpoint map (once the resource slices exist) | **The OpenAPI-asset task** — one standard task, after the last endpoint slice: the `be-<stack>` agent generates the spec from the implemented surface and commits it canonicalized as `{service}-openapi-YYYY-MM-DD.json`, so `qa/_shared/api-spec-assets` has its canonical input from day one and every later contract change flows through that skill's diff-driven lane instead of being reverse-engineered. Greenfield plans include it by default; skip only when the repo already keeps the asset |

Anything not traceable to a row above is either missing from the design pack (go add it there) or is not needed.

**A user-facing capability is not a row — it is the sum of several.** Where the initiative delivers something a person does (place an order, book a session, reset a password), the table gives you the *pieces*; what makes them a feature is that all of them exist at once. Before sequencing, write down, per capability, the full set it needs to be usable end to end:

> schema + entities + the domain rules → the service/orchestration → the endpoints and their request/response contracts → the validation & error deltas → the authorization rule → registration and wiring (DI, route module, config keys) → unit tests → and whatever makes it **reachable**: the migration applied, seed/reference data, a feature flag defaulted to on, the OpenAPI asset when a consumer is generated from it.

That set is what Step 2 sequences. A capability missing any of it has been planned, not delivered — and "the endpoints exist but nothing registers them" is the way this fails most often.

### Step 2 — Group into phases

A **phase** is a set of tasks that can start once the previous phase is done. Phases are **hard barriers**: nothing in phase N+1 starts until every task in phase N is finished, even when a particular task's own dependencies are already satisfied. The barrier is what makes the ordering safe on plans that encode prerequisites structurally — schema before the slice that maps it, foundations before the capability built on them — rather than enumerating every edge.

**First decide the sequencing shape**, because it changes what a phase *means*:

| Shape | Use when | A phase ends with |
|---|---|---|
| **Feature-complete** (the default for user-facing work) | The initiative delivers capabilities a person uses, and someone will want to see one working before the rest exists | **A capability a user can exercise, end to end** |
| **Platform-first** (the layered shape) | The initiative is a service or platform with no single user journey at stake — several areas land together and the consumer is another system | A layer completed across every area |

Feature-complete sequencing keeps the same barriers and the same task sources; what changes is what goes into each phase. Foundations still come first — but only the foundations the **first** capability needs, never every foundation every capability will eventually want:

| Phase | Contains | Streams inside it |
|---|---|---|
| **P0 Prerequisites** | Human-blocked provisioning the first capability needs | One per provisioning track |
| **P1 Foundations** | Scaffold, layout, config + validation, CI skeleton, and the cross-cutting surfaces (auth, error envelope, shared DTOs) the first capability actually depends on — nothing speculative | **One** — shared root files |
| **P2 Capability A** | A's whole set from Step 1, in its natural order: migration → entities + rules → service → endpoints → wiring → unit tests | **One** — the steps of one feature are sequential by construction |
| **P3 Capability B** | B's own set, plus only the foundations B is the first to need | One per capability built concurrently, when their file sets are disjoint |
| **…** | One phase per remaining capability, most valuable first | |
| **Pn Close-out** | The OpenAPI asset, telemetry, rate limiting, performance, docs | Group by what they touch |

Three rules keep it honest:

- **A capability phase closes only when the capability works.** Its exit condition is behavioural — *"a user with the `booker` permission can book a session and then see it under their bookings"* — not "the tasks are checked off". Write that sentence into the phase row's Goal, and make the last task in the phase the one that makes it true.
- **Deferred foundations are named, not forgotten.** Where a capability's phase deliberately stops short of a shared surface a later one will need — a generic error envelope, a pagination convention, a caching layer — say so in the phase rationale and place the generalization in the phase that first needs it. An implied deferral is indistinguishable from an oversight.
- **Schema order stays global.** Migrations run in the order `data-model.md` states even when phases are per-capability; a capability phase owns the migrations for its own entities, at their stated position in that sequence.

**The platform-first shape**, and the lanes it falls into:

| Phase | Contains | Streams inside it |
|---|---|---|
| **P0 Prerequisites** | Human-blocked provisioning from `integrations.md` | One per provisioning track — nobody is editing code |
| **P1 Foundations** | Scaffold, project layout, config + validation, CI skeleton | **One** — scaffold, config and CI all edit the same root files |
| **P2 Schema** | Migrations in their stated order | **One** — migrations are ordered by definition |
| **P3 Cross-cutting** | Auth wiring, error middleware, shared DTOs, telemetry base | **One** — shared surfaces, and every later task depends on them |
| **P4 Feature slices** | One task per resource: entity → persistence → service → endpoints → unit tests | **One per resource** — disjoint file sets, once P3 is stable |
| **P5 Integrations** | External clients, webhook handlers, background jobs | One per dependency — one file set each |
| **P6 Hardening** | Rate limiting, observability, performance, docs | Group by what they touch; often one per subsystem |

A lane that finishes its phase work early **idles at the barrier** until the phase closes. That is the cost of the conservatism, and it is worth stating in the plan rather than leaving someone to read it as a stall.

Each phase's row in the plan carries **`Parallel-safe: Yes | No` — strictly boolean**, because the streams-absent fallback (Step 7) ingests it as one. A "partly" or "mixed" phase is `No`, with the safe pairs named in the Rationale column — the streams carry the pairwise answer, so nothing is lost by the conservative call.

### Step 3 — Declare the streams

A **stream** is a named lane. Tasks in one stream run strictly one after another; different streams run at the same time. So the question to answer is not a per-phase yes/no — it is **"which lanes does this work actually have, and why is each one internally sequential?"**, which is answerable from the file sets you just wrote down.

Give the plan a streams table, before the progress table:

| Stream | Owns | Why it is internally sequential |
|---|---|---|
| `foundation` | Scaffold, config, CI, the shared surfaces every slice builds on | One root file set — every task edits the solution root or `Program.cs` |
| `booking` | The Bookings resource and the email it sends on confirm | `src/Booking/*` throughout; T13 sends on the event T11 raises |

Rules:

- **Name a stream after what it owns** — `booking`, `schema`, `infra`, `ui`. Never `stream1`, and never one lane per phase.
- **Stream identity is stable across phases.** If P1 and P3 both hold foundation work, that is one `foundation` lane running down the whole plan, not two.
- **Two tasks in the same phase whose `Files` overlap MUST share a stream.** This is the hard rule and the one that is machine-checked: concurrent lanes execute against a single working tree, so two lanes writing one path is a corrupted edit, not a merge conflict to resolve later. Across phases the barrier already serialises them, so two tasks in different phases may share a file across different streams safely. If the shared edit is incidental — a DI registration module, a route table — pull it out into its own earlier task instead of collapsing two good lanes into one.
- **A stream is a claim, not a bucket.** Each task in it needs the previous one's output, or touches the same code. Spreading independent tasks across lanes to look parallel is the failure mode in one direction; dumping unrelated work into one lane to look safe is the failure mode in the other, and it serialises a plan that did not need to be.
- **A task that depends on nothing and shares no file gets its own stream.**
- **`order` is one sequence across the whole plan** — 1, 2, 3, … no repeats, no gaps. Within a stream it fixes execution sequence; across the plan it records the order you would have done the work in yourself, which is what decides who gets a slot when more lanes are eligible than the run allows to be concurrent.
- **`Depends on` still points backwards in `order`.** Streams say "same lane, therefore sequential"; `dependsOn` says "across lanes, this waits on that". Both are needed and a task waits on both — but a dependency on a task with a *higher* order is a contradiction between the two, and it is reported as a defect rather than resolved.

Keep the per-phase parallel-safety line in the phases table for the reader, and defend it the same concrete way as before — "T10 touches `src/Scheduling/*`, T11 touches `src/Booking/*`, no shared file". But the streams table is now the load-bearing statement: a phase whose tasks all sit in one stream *is* what `parallelSafe: false` used to say, derived rather than asserted.

### Step 4 — Write each task

```markdown
### T12 — Orders resource (P4)

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

- **`Agent` is an exact catalog name**, picked from the routing-map catalog in `blueprint.md` (authored by `be-shared-solution-blueprint` — that catalog is the single authoritative list; `be-dotnet`, `data-architect`, `qa-api-<stack>` are the shape). An invented name is the most damaging defect in the pack, because Mission Control binds on this string. Same for skill names. When the chosen stack has no skill for a concern the task needs (e.g. `be-node` currently ships no service-side auth skill), bind the task to the stack agent anyway, note the gap in the Skills cell (`— no <concern> skill for this stack; the agent works from the design pack`), and add an open question — never invent a skill name to fill the hole.
- **Human prerequisite tasks use `Agent: human`.** Provisioning work from `integrations.md`'s blocking unknowns — accounts, tenants, sandbox access — is a real task with a real id, but its executor is a person: the Agent cell is the literal `human` and the task block carries an `**Owner:**` line naming who does it. `human` is exempt from catalog-name resolution, and Mission Control treats these tasks as gates to satisfy, never lanes to schedule.
- **`Files` must be specific.** This is what the stream check relies on, and it is the difference between a plan and a wish.
- **`Stream` is one of the ids declared in Step 3**, and `Order` is that task's slot in the plan-wide sequence. **Every task carries both, or no task does** — half-authored lanes are rejected rather than completed, because back-filling the rest would scatter tasks into lanes nobody planned. A `Stream` naming an undeclared lane and two tasks claiming one `Order` are both reported as plan defects, and the undeclared lane also costs you the lanes you did author: the whole plan falls back to derived ones.
- **Acceptance criteria are checkable**, and they cite the design pack by section rather than restating it. "Handles errors properly" is not a criterion; "returns the documented `type` slug for each of the three deltas" is.
- **The build/test command is the project's own**, taken from the orientation pass — never a guessed default.
- **Size a task by coherence, not by volume.** A task is one thing, done once — a resource, a migration set, an external client, a capability's endpoint surface — and it is exactly as big as that thing is. File counts and criterion counts are not a limit: a slice that genuinely needs fourteen files is one task, and cutting it into "the entity" and "the service" produces two tasks neither of which can be verified alone. **Split when it stops being one thing**: it delivers two independent behaviours; a natural intermediate point exists where the work is meaningfully complete *and* checkable on its own; part of it is blocked while the rest is not; or two different agents own the halves. Every piece of a split must still build, still pass its own tests, and still be independently verifiable — a split that leaves the tree broken between the pieces was a bad seam, and the two pieces are one task. When a task is large, its **acceptance-criteria list is its step breakdown**, ticked off in place as the work lands.
- **`Out of scope` per task** — mostly to keep the executing agent from wandering into a peer's lane.
- **Tasks are implementation.** Live/E2E/integration test runs, starting servers, and manual verification belong to a separate QA pass owned by a `qa-*` peer. Unit tests are part of the implementation task, not a separate one.

### Step 5 — The progress table

The scannable index, and the thing `HANDOFF.md` points at. Rows sorted by `#`, which makes the sequence auditable at a glance — a repeat or a gap is visible without cross-reading the task blocks. `#` **is** the plan-wide `order` Mission Control consumes; the task blocks repeat it as `Order:`, and the two must agree:

| # | Task | Phase | Stream | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 12 | T12 | P4 | `ordering` | Orders resource | `be-dotnet` | T4, T9, T10 | Not started | — |

Status vocabulary — six values, no others: **Not started · In progress · Done · Partial · Diverged · Blocked**. `Evidence` holds the `file:line` or command output that justifies a `Done` or `Partial`. An empty Evidence cell on a `Done` row is a defect in the plan, not a formatting gap.

### Step 6 — Write `HANDOFF.md`

The pointer file — see `references/handoff-template.md` for the full template and its rules. **It answers one question: what does the next agent do next.** The next unblocked task per lane, where to start inside it, what is blocking, and the working-tree state that goes stale fastest. It is **rewritten each session, never appended**.

**Progress does not live here.** Status, evidence, ticked criteria, the execution log, the decisions and the deviations all live in `delivery-plan.md` — one record, in the document that defines the work. The handoff cites task ids and never restates their history; anything it would duplicate is a line the two files will eventually disagree about.

### Step 7 — The Mission Control section

Close the document with an ingestion block so the plan can be pasted into Mission Control and produce a near-identical task graph:

```markdown
## For Mission Control

Paste this document into the plan box and point the run at `<target repo path>`.
The task graph maps 1:1 — the streams in §2 become MC's lanes, each task keeps its
`stream` and `order` alongside its `agent`, `skills`, `files` and `dependsOn`,
phases stay hard barriers, and the open questions below carry their options.
MC's planner re-reads the target repo, so it may split a task it finds too large;
that is expected and does not invalidate the sequence — the new pieces belong in
the split task's own lane.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
```

Mission Control's planner consumes exactly these fields — run-level `streams[]` (`id · name · description`), per-task `id · phaseId · streamId · order · title · intent · acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]`, per-phase `parallelSafe` + `parallelRationale`, and `openQuestions[]` with 2–4 options each and one recommended. Writing them in that vocabulary is the entire compatibility requirement.

**A pack without streams still imports.** MC derives lanes from the phases' parallel-safety calls — a sequential phase becomes one lane, a parallel-safe one becomes a lane per task — and orders from position in the list. That is why `parallelSafe` stays in the artifact. But a derivation is a guess at the shape you already know: it cannot tell that P1's foundation lane and P3's shared-surfaces lane are the same continuous lane, and it will fan a parallel-safe phase out to the width of its task count. Author the streams.

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
| Building it differently | Progress row → `Diverged`; both readings in the task block; the resolution recorded in §8 once the human picks |
| Hitting a blocker | Progress row → `Blocked`, naming what on and who owns it; one execution-log row |
| Closing a capability phase | Record that the phase's behavioural goal now holds, with how it was checked |

Rules:

- **Evidence, not assertion.** `Done` and `Partial` carry the `file:line` or command output that proves them, produced in the session that wrote the status. The rule the reconcile runs on applies first to the person writing the status.
- **The execution log is append-only.** Rows are added, never edited or deleted — a task that regresses gets a new row, not a corrected one. It is the one part of the pack that is history rather than a statement of now, and it is what makes *"what has been done"* answerable without reading git.
- **Decisions and deviations are recorded in the plan** (§8), because they outlive the session that made them. A deviation that lives only in a rewritten handoff is gone by Monday.
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
| **Done** | Every acceptance criterion is satisfied by code you read this session |
| **Partial** | Some criteria satisfied; name exactly which are missing |
| **Not started** | No artifacts found. Say what you searched for — a negative claim needs its search named |
| **Diverged** | Built, but differently from the plan. **Both readings recorded; the human decides** |
| **Blocked** | Cannot proceed — a prerequisite, a missing credential, a red build |

4. **Escalate every divergence.** Usually the code is right and the plan is stale — but you never silently rewrite the plan to match, because the other possibility is a defect. Present both readings, recommend one, and record the resolution in the plan's §8 Decisions & deviations.
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
**Pack:** `./blueprint.md` · `./data-model.md` · `./api-surface.md` · `./integrations.md`
**Target repo:** `<path>` · **Stack:** <stack + version> · **Build/test:** `<the project's own commands>`

> **For agentic workers:** each task names the agent that should execute it and the skills to load.
> Run them with `ep-executing-plans` inline, or hand the whole document to Mission Control.
> **Update this document as you work** — the Status and Evidence cells in §3, the criterion
> checkboxes in §4, an append-only row in §7, and any decision or deviation in §8.
> `HANDOFF.md` says only what to pick up next.

## 1. Phases
| Phase | Goal | Parallel-safe | Rationale |
|---|---|---|---|

## 2. Streams
| Stream | Owns | Why it is internally sequential |
|---|---|---|

## 3. Progress
| # | Task | Phase | Stream | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|---|---|

## 4. Tasks
<!-- one block per task: agent, skills, stream + order, depends on, files, intent, acceptance criteria, out of scope -->

## 5. Open questions
| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|

## 6. Deliberately not planned
<!-- what this initiative excludes and which agent/peer owns it instead -->

## 7. Execution log
<!-- append-only, oldest first: one row per status change. Never edited, never deleted -->
| When | Task | Status | By | Note |
|---|---|---|---|---|

## 8. Decisions & deviations
<!-- answered questions, resolved divergences, and what got built differently from the plan -->
| # | Task | Plan said | What was decided/built | Why | When |
|---|---|---|---|---|---|

## For Mission Control
<!-- ingestion note + blocking open questions -->
```

## Self-check before handing off

1. Every functional area in `blueprint.md` has at least one task; every migration, every resource, every external client, every blocking unknown is a task.
2. Every task binds to an **exact** catalog agent name and exact skill names.
3. No task depends on a later phase. Every `dependsOn` id exists.
4. Every task names a declared stream and carries a unique `order`; every stream's row says why it is internally sequential; no two tasks in the same phase but different streams share a file; no `dependsOn` points at a higher `order`.
5. Every task's acceptance criteria are checkable and cite the design pack by section.
6. The build/test commands are the project's own, from the orientation pass.
7. `HANDOFF.md` exists, names the next task per unblocked lane and every blocker — and carries no progress record of its own.
8. Every `Done`/`Partial` status carries `file:line` evidence read this session.
9. Every user-facing capability has a phase whose Goal states behaviourally what a user can do once it closes, and that phase's tasks cover everything on the Step-1 capability set — including what makes it reachable, not only its endpoints.
10. Sections 7 and 8 exist (empty before execution starts), and the header note tells the executing agents to maintain §3, §4, §7 and §8 as they work.

## Handoffs

- **→ `be-dotnet` / `be-java` / `be-node`** — execute the tasks bound to them, and update this document's §3/§4/§7/§8 as each task moves.
- **→ `ep-executing-plans`** — the task-by-task execution loop, with checkpoints; its per-task checkpoint is where this plan's status, evidence and execution log get written. `ep-delegate-to-subagents` runs the same tasks through subagents — the controller, not the subagent, owns the plan update.
- **→ Mission Control** — paste the document, point at the repo.
- **→ `data-architect` / `devops-engineer` / `observability-engineer-<stack>` / `qa-*`** — the tasks bound to them, run as peers.
- **→ `code-auditor`** — when a reconcile finds systemic drift rather than a handful of divergences, that is an audit, not a reconcile.
- **→ `be-shared-plain-language-companion`** — writes `delivery-plan-explained.md` beside this document for the stakeholders who need the sequence, the deliverables and the blockers without the task ids and agent bindings. Regenerate it whenever this plan is re-sequenced.

## Version policy

The sequencing discipline is version-agnostic; the **commands in acceptance criteria are not**. Take the build, test, format, and migration commands from the orientation pass — the project's own — never a guessed default (`dotnet build`/`dotnet test`/`dotnet format` · `./gradlew build`/`./gradlew test` · `npm|pnpm run build`/`test`, with the package manager read from `packageManager` in `package.json`). Where a task upgrades a runtime or framework major, it is its own task with its own justification, per `CLAUDE.md`'s version policy — never a side effect of a feature task.
