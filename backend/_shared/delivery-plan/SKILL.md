---
name: be-shared-delivery-plan
description: Use when a planned backend (blueprint + data model + API surface + integrations) needs turning into an ordered, executable task list — phases with parallel-safety calls, one task per unit of work bound to an exact library agent and the skills it loads, files touched, dependencies, and acceptance criteria — plus the HANDOFF.md session-state file that lets work stop and resume across sessions, and a reconcile procedure that re-verifies a plan against half-built code. Directly ingestible by Mission Control. Triggers "what order do we build this in", "turn the plan into tasks", "which agent builds what", "pick up where we left off", "reconcile the plan against the code". Do NOT use to write the code (`be-dotnet`/`be-java`/`be-node`), to execute a generic step-by-step plan (`ep-executing-plans`), or to audit built code against a spec (`code-auditor`).
---

# Delivery Plan — the ordered, agent-bound task list

The artifact that turns four design documents into work. Two things make it different from a generic plan:

- **Every task names its executor** — an exact agent name from this library plus the skills it should load. That binding is what lets the plan run unattended, inline or through Mission Control.
- **It survives interruption.** `HANDOFF.md` carries the live state, and the reconcile procedure re-derives that state from the code when the handoff is stale or absent — because a plan whose status you have to trust is a plan you have to redo.

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

### Step 2 — Group into phases

A **phase** is a set of tasks that can start once the previous phase is done. Phases run strictly in order; tasks within a phase may run in parallel **only if** they touch disjoint files and none consumes another's output.

The shape that works, and why:

| Phase | Contains | Parallel-safe? |
|---|---|---|
| **P0 Prerequisites** | Human-blocked provisioning from `integrations.md` | Yes — nobody is editing code |
| **P1 Foundations** | Scaffold, project layout, config + validation, CI skeleton | **No** — everything touches the same root files |
| **P2 Schema** | Migrations in their stated order | **No** — migrations are ordered by definition |
| **P3 Cross-cutting** | Auth wiring, error middleware, shared DTOs, telemetry base | **No** — shared surfaces, and every later task depends on them |
| **P4 Feature slices** | One task per resource: entity → persistence → service → endpoints → unit tests | **Usually yes** — disjoint files, once P3 is stable |
| **P5 Integrations** | External clients, webhook handlers, background jobs | Usually yes — one file set per dependency |
| **P6 Hardening** | Rate limiting, observability, performance, docs | Mixed — call it per task |

**The parallel-safety call is a claim you must defend in one concrete sentence.** Not "these are independent" but "T7 touches `Orders/*`, T8 touches `Products/*`, no shared file". If two tasks in a phase would edit the same file — a DI registration module, a route table, a `DbContext` — the phase is **not** parallel-safe, or that shared edit is pulled out into its own earlier task. Foundational work is almost never parallel-safe, and claiming otherwise produces merge conflicts that look like agent failures.

### Step 3 — Write each task

```markdown
### T12 — Orders resource (P4)

**Agent:** `be-dotnet` · **Skills:** `be-dotnet-pattern-writer`, `be-dotnet-database-code`, `be-dotnet-unit-testing`
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

- **`Agent` is an exact catalog name.** `be-dotnet`, `be-java`, `be-node`, `data-architect`, `devops-engineer`, `observability-engineer-<stack>`, `qa-api-<stack>`, `qa-security`, `fe-react`, `fe-blazor`. An invented name is the most damaging defect in the pack, because Mission Control binds on this string. Same for skill names.
- **`Files` must be specific.** This is what the parallel-safety check relies on, and it is the difference between a plan and a wish.
- **Acceptance criteria are checkable**, and they cite the design pack by section rather than restating it. "Handles errors properly" is not a criterion; "returns the documented `type` slug for each of the three deltas" is.
- **The build/test command is the project's own**, taken from the orientation pass — never a guessed default.
- **A task is one sitting.** If it touches more than ~8 files or has more than ~8 acceptance criteria, split it. Tasks that span days hide their own failure.
- **`Out of scope` per task** — mostly to keep the executing agent from wandering into a peer's lane.
- **Tasks are implementation.** Live/E2E/integration test runs, starting servers, and manual verification belong to a separate QA pass owned by a `qa-*` peer. Unit tests are part of the implementation task, not a separate one.

### Step 4 — The progress table

The scannable index, and the thing `HANDOFF.md` points at:

| Task | Phase | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|
| T12 | P4 | Orders resource | `be-dotnet` | T4, T9, T10 | Not started | — |

Status vocabulary — five values, no others: **Not started · In progress · Done · Partial · Diverged · Blocked**. `Evidence` holds the `file:line` or command output that justifies a `Done` or `Partial`. An empty Evidence cell on a `Done` row is a defect in the plan, not a formatting gap.

### Step 5 — Write `HANDOFF.md`

The live session-state file — see `references/handoff-template.md` for the full template and its rules. It is **rewritten each session, not appended**, except for the short session-log tail. Its whole purpose is that a cold agent (or a human on Monday) can read one file and know exactly where things stand and what to do next.

### Step 6 — The Mission Control section

Close the document with an ingestion block so the plan can be pasted into Mission Control and produce a near-identical task graph:

```markdown
## For Mission Control

Paste this document into the plan box and point the run at `<target repo path>`.
The task graph maps 1:1 — phases keep their `parallelSafe` calls, tasks keep their
`agent`, `skills`, `files`, and `dependsOn`, and the open questions below carry
their options. MC's planner re-reads the target repo, so it may split a task it
finds too large; that is expected and does not invalidate the sequence.

**Open questions still blocking tasks**
| # | Question | Options | Blocks |
|---|---|---|---|
```

Mission Control's planner consumes exactly these fields — `id · phaseId · title · intent · acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]`, per-phase `parallelSafe` + `parallelRationale`, and `openQuestions[]` with 2–4 options each and one recommended. Writing them in that vocabulary is the entire compatibility requirement.

---

## The reconcile procedure (RESUME mode)

Run this **before** re-sequencing anything, when a plan and partially-built code both exist. It is the mode this skill earns its keep in.

**The governing rule: the plan is a lead, not evidence.** A checked box, a green pipeline, a commit message, and a previous `HANDOFF.md` are all claims. Status is assigned only after reading the code **this session**.

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

4. **Escalate every divergence.** Usually the code is right and the plan is stale — but you never silently rewrite the plan to match, because the other possibility is a defect. Present both readings, recommend one, and record the resolution in `HANDOFF.md`'s Decisions section.
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
> Steps use checkbox syntax; `HANDOFF.md` carries live state between sessions.

## 1. Phases
| Phase | Goal | Parallel-safe | Rationale |
|---|---|---|---|

## 2. Progress
| Task | Phase | Title | Agent | Depends on | Status | Evidence |
|---|---|---|---|---|---|---|

## 3. Tasks
<!-- one block per task: agent, skills, depends on, files, intent, acceptance criteria, out of scope -->

## 4. Open questions
| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|

## 5. Deliberately not planned
<!-- what this initiative excludes and which agent/peer owns it instead -->

## For Mission Control
<!-- ingestion note + blocking open questions -->
```

## Self-check before handing off

1. Every functional area in `blueprint.md` has at least one task; every migration, every resource, every external client, every blocking unknown is a task.
2. Every task binds to an **exact** catalog agent name and exact skill names.
3. No task depends on a later phase. Every `dependsOn` id exists.
4. Every phase marked parallel-safe has a concrete disjoint-files rationale; no two of its tasks share a file.
5. Every task's acceptance criteria are checkable and cite the design pack by section.
6. The build/test commands are the project's own, from the orientation pass.
7. `HANDOFF.md` exists, names the next task, and lists every blocker.
8. Every `Done`/`Partial` status carries `file:line` evidence read this session.

## Handoffs

- **→ `be-dotnet` / `be-java` / `be-node`** — execute the tasks bound to them.
- **→ `ep-executing-plans`** — the task-by-task execution loop, with checkpoints; `ep-delegate-to-subagents` runs the same tasks through subagents.
- **→ Mission Control** — paste the document, point at the repo.
- **→ `data-architect` / `devops-engineer` / `observability-engineer-<stack>` / `qa-*`** — the tasks bound to them, run as peers.
- **→ `code-auditor`** — when a reconcile finds systemic drift rather than a handful of divergences, that is an audit, not a reconcile.

## Version policy

The sequencing discipline is version-agnostic; the **commands in acceptance criteria are not**. Take the build, test, format, and migration commands from the orientation pass — the project's own — never a guessed default (`dotnet build`/`dotnet test`/`dotnet format` · `./gradlew build`/`./gradlew test` · `npm|pnpm run build`/`test`, with the package manager read from `packageManager` in `package.json`). Where a task upgrades a runtime or framework major, it is its own task with its own justification, per `CLAUDE.md`'s version policy — never a side effect of a feature task.
