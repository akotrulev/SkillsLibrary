---
name: plan-blueprint
description: Use when turning requirements into an approved high-level backend plan (areas, architecture, stack, agent routing). Triggers "plan the backend for X". Not for the detail pack (plan-data-model).
disable-model-invocation: true
---

# Solution Blueprint — the high-level backend plan

The blueprint is the document the human approves, and everything downstream (data model, API surface, integrations, task sequence) derives from it. It makes the *consequential* decisions visible and confirmable in one page-sized pass, and the uncertain ones explicit.

## Output

**`docs/plans/<NNN>-<initiative>/blueprint.md`** under the **target project's** root, never the skills-library checkout or a global directory. `NNN` is zero-padded and takes the high-water mark across `docs/plans/` **and** `docs/plans/implemented/` (a finished pack's number stays spent). `<initiative>` is a short kebab-case noun phrase (`billing-service`), stable for the life of the initiative: every artifact and prompt block cites it.

`references/example-blueprint.md` is a filled golden example (the toy initiative `001-workshop-booking`, shared by the planner examples). Its shapes are normative, its domain content illustrative.

## Annotation grammar and evidence marks (the whole plan pack)

| Marker | Means |
|---|---|
| `#confirmed` | Stated by the human, in this session or in a requirements document. Never read out of code (that is `#observed`) |
| `#inferred` | Your reasoning from indirect evidence; the human should scan these |
| `#observed` | Read out of existing code or behavior, per `business-analysis:knowledge-base`; in the documenter lane it always carries `file:line` |
| `[TBD - <owner>, <by when>]` | Genuinely unknown, with a named owner; never a synonym for vague |
| `⚠️ Assumption:` | You proceeded on an unconfirmed premise; each is also a line in Open Questions |

An unmarked claim reads as `#confirmed`. Tech-stack and architecture table cells use the one-word form of the same axis: `detected` (found in the repo: a TFM, a lockfile, a migration, a route) ≈ `#observed` · `stated` (the human said so) ≈ `#confirmed` · `proposed` (your inference from the workload) ≈ `#inferred`, the rows the human must look at · `proposed → approved` (confirmed at the gate). In an existing repo `detected` beats the Stack defaults; in a greenfield one the `CLAUDE.md` defaults are the proposal, marked `proposed`.

---

## Procedure

### Step 1 — Frame the initiative

Three to five sentences answering: what business problem, for whom, what changes when it ships, and what success looks like. Raw prose input (a BRD, a transcript, an email thread) is distilled first with `qa/manual/requirements-breakdown`, which flags silent and contradictory items.

When these sentences need an invented business fact, stop, name the missing facts and route to `requirements-author`. Done when they rest on stated facts.

### Step 2 — Decompose into functional areas

A **functional area** is a coherent slice of business capability that one person could own and test as a unit (`Identity & access`, `Catalog`, `Ordering`, `Billing`). It is not a technical layer and not a single endpoint.

| Column | Content |
|---|---|
| Area | Short noun phrase |
| Epics | The `E` ids from `epics.md` this area serves (`E1, E3`, or `E0` for a cross-cutting foundation). The join the whole pack is checked on |
| Purpose | One sentence, the capability in business terms |
| User-facing capabilities | What a person can *do* here, one short sentence each in the user's voice (*"a member books a session"*); empty where nothing user-facing sits. `dev:plan-delivery` sequences user-facing work one capability at a time on this column |
| Primary actors | Who or what drives it (end user, admin, scheduled job, external system) |
| Key entities | The 2–5 nouns it owns, the seed of `data-model.md` |
| In scope / Out of scope | What this initiative builds for it; what it excludes and where that work lives instead |
| Depends on | Other areas or external systems |

- **Every area names the epic ids it serves, and every epic is served by an area.** The ids come from `epics.md` as `requirements-author` wrote them, read and never renumbered or invented. An area serving no epic is work nobody asked for; an epic no area serves is a capability the architecture forgot. Cross-cutting foundations (auth, config, the error envelope, the app shell) serve `E0`, the planner-created epic that carries no stories and never appears in `epics.md`.
- **Name capabilities in the user's voice**: *"A member books a session"* is a capability; *"exposes the bookings endpoint"* is an implementation of one. The delivery plan closes each on a person actually doing it.
- **6–8 areas is a lot.** Beyond that, split into separate initiatives (own folder, own plan) or merge areas, and say which. **Out of scope is mandatory**: an unstated boundary is the most common plan defect.
- An area owning no entity is a cross-cutting concern, and belongs in the architecture section.
- **When anything is user-facing, name the actors and propose the shell** in a short §2b: one line per actor with their two or three most frequent tasks (*verb + object + outcome*), and the **app shell** (sidebar / top nav / hybrid, from `design/ux-patterns` §2) as a `proposed` row with its reason. The nav map, journeys and screens are `dev:plan-experience`'s in Step 3. With no user-facing capability write "no user-facing area".
- **Ask about existing data.** An area that replaces a system of record (a spreadsheet, a legacy app) puts that data in scope or out, and says which. Whether it comes across once or stays in sync is usually an open question; the mapping belongs to `dev:plan-data-model`'s backfill section.

Done when every area names its epics, every epic is served, and each area states its scope boundary.

### Step 3 — Decide the architecture style

State the decision, the reason it is **earned for this system**, and what you rejected. Default toward the least structure that works: a modular monolith built to be split later, with one team, one deployable and no split trigger met. An existing codebase keeps the architecture it has. **A greenfield system or a live architecture decision → read `references/architecture-style.md`** (the styles table, the four split-later rules, the split triggers, the repository layout, the context diagram).

For each *pattern* in play (CQRS, event sourcing, Saga, Outbox, Repository over the ORM) write one line stating it is earned, loading `backend/_shared/pattern-guide` for the concept card when the decision is live. **One pattern per problem**; a pattern with no stated reason is a finding against your own blueprint.

Done when the blueprint holds the style, its reason, what was rejected, a reason per pattern, the repository layout and a context diagram.

### Step 3.5 — Model the key flows and decisions

Prose hides the questions a diagram forces, and this is the cheapest place in the pack to find a missing requirement. Model only what is load-bearing: a **process flowchart** per primary business flow (the 2–5 journeys the system exists to serve), a **decision table** per rule where 3+ inputs combine to select an outcome. Entity lifecycles belong in `data-model.md`. A single-step CRUD path and a two-branch `if` need neither.

**A flow or a multi-input rule in the initiative → read `references/key-flows-and-decisions.md`** for the diagram and table shapes, and load `business-analysis:process-flow` and `business-analysis:decision-table` by path for the full discipline. Where the project keeps a business-model KB, the models live there as `FLOW-nnn` / `DEC-nnn` and the blueprint links them by ID.

**The hit policy is never invented.** When nobody has decided what happens if two rules both apply, it is a `[TBD]` and an open question.

Done when every primary flow has a flowchart with each failure exit labelled, and every multi-input rule a decision table with a declared hit policy.

### Step 4 — Settle the tech stack

One evidence-marked row per dimension this initiative needs, with columns `Dimension | Choice | Version | Why | Evidence`. Draw dimensions from: runtime / language, web framework, primary datastore, cache, messaging / queue, ORM / data access, auth provider and flow, background jobs, hosting target, CI host, observability. An unused row invites a decision nobody has to make.

**Detected wins.** An upgrade is its own task in the delivery plan, never a side effect of a feature; an up-level-only API is never planned onto a down-level project. Greenfield defaults come from `CLAUDE.md`'s Stack defaults.

Done when every needed dimension has a row with a version and an evidence mark.

### Step 5 — Name the external systems (architecture altitude only)

One line each: system, what it does for us, direction (we call it / it calls us / both), and criticality (does the feature fail without it, or degrade?). Depth (auth method, config keys, retry policy, sandbox strategy) belongs to `dev:plan-integrations`; here only enough to make the architecture and the risk list honest.

### Step 6 — Build the routing map

**This section makes the plan executable.** Each functional area and cross-cutting concern binds to the exact library agent that builds it, plus the skills that agent loads. Mission Control binds tasks on these strings, so an invented name is the pack's most damaging defect.

| Area / concern | Agent | Skills it will load | Note |
|---|---|---|---|
| Screens, shell, navigation (`experience-plan.md` S1–Sn) | `fe-react` | `design:app-structure`, `fe-react:component-writer`, `fe-react:routing` | Builds from the experience plan; IA is decided there |
| Ordering domain + persistence | `be-dotnet` | `be-dotnet:patterns-apply`, `be-dotnet:persistence`, `be-dotnet:unit-testing` | Unit tests ship with the task |
| Schema, indexes, tenancy enforcement | `data-architect` | `data:postgresql`, `data:schema-design` | Beyond ORM mechanics |
| Telemetry base | `observability-engineer-dotnet` | `be-dotnet:opentelemetry`, `be-dotnet:structured-logging` | Runs in the foundation, right after the scaffold; each `be` task then instruments what it builds |
| Contract + integration tests | `qa-api-dotnet` | `qa-dotnet:api-tests` | Test basis is `api-surface.md` |

**The agent catalog** — pick only from these names:

| Domain | Agents |
|---|---|
| Backend build | `be-dotnet` · `be-java` · `be-node` · `be-python` (the isolated upload-processing worker only) · `be-rust` |
| Solution planning | `solution-planner` (this one) |
| Data | `data-architect` |
| Frontend | `fe-blazor` · `fe-react` |
| Observability | `observability-engineer-dotnet` · `observability-engineer-java` · `observability-engineer-node` |
| DevOps | `devops-engineer` · `devops-auditor` |
| Agent tooling (MCP server / CLI over the project) | `tooling-engineer` |
| QA — per stack (`{dotnet,java,typescript}`) | `qa-api-<stack>` · `qa-ui-<stack>` · `qa-mobile-<stack>` · `qa-performance-<stack>` · `qa-llm-<stack>` · `qa-bdd-<stack>` · `qa-cicd-<stack>` · `qa-reporting-<stack>` |
| QA — stack-agnostic | `qa-security` · `qa-test-case-designer` · `qa-test-planner` |
| Requirements | `requirements-author` · `business-analyst` |
| Audit | `code-auditor` |

A capability with no agent is said so, naming the skill or human step that covers it.

**Then record the execution model, one line, as an answer and not an inference.** The routing map says *which* agents build the system; the execution model says *how the run happens*, and selects the delivery plan's sequencing shape. Ask it in the Step-9 batch:

| Execution model | Recognized by | Selects (in `dev:plan-delivery` Step 2) |
|---|---|---|
| **One operator, sequential batches** | One person drives one session at a time; integration/E2E happens once at the end; nothing must be demonstrable before the last batch | `agent-batched` |
| **Concurrent lanes / Mission Control** | Several lanes run at once, or a stakeholder wants the first capability early | `feature-complete` |
| **No user journey at stake** | A service or platform whose consumer is another system | `platform-first` |

Write it into §6 as `**Execution model:** <which> — <what settled it>`.

Done when every area and concern has an agent from the catalog and the execution model is recorded.

### Step 7 — Non-functional targets

Only what is known or decidable now; the rest are `[TBD - <owner>]` lines. Where `requirements.md` exists, its §4 quality targets are the source, cited in *Evidence*; a target it leaves `[TBD]` stays `[TBD]`. Cover expected scale, latency on the paths that matter, availability, data retention and deletion, compliance (PII, PCI, residency, audit trail) and the security posture.

**The tenancy model is load-bearing**: it decides table shape, every query, the auth model and a class of security test. In a multi-tenant system the isolation approach is a blueprint decision.

Done when every dimension has a target or a `[TBD]` with an owner, and the tenancy model is stated.

### Step 8 — Risks and assumptions

A table of `Risk | Likelihood | Impact | Mitigation / early signal`, including risks from the plan itself: an unconfirmed integration, a `[TBD]` on the critical path, an area whose requirements are `#inferred`, an upgrade the plan depends on. Then every `⚠️ Assumption:` in the document, listed in one place so a wrong one is caught in thirty seconds.

### Step 9 — Open questions, then the gate

**Ask only what materially changes the work.** A question the repo answers is not a question, and ordinary engineering judgment is decided and marked `⚠️ Assumption:`. Aim for **three to six** questions; a dozen means you are outsourcing the thinking. **The execution-model question is always one of them** (Step 6), unless the human already stated how the plan gets run: it cannot be read off the repo and it decides the delivery plan's shape.

```markdown
**Q1 — <the question>?**
*Context:* <one or two sentences on why it matters and what it blocks>
- **A. <option>** *(recommended)* — <the real trade-off>
- **B. <option>** — <the real trade-off>
*Blocks:* <the areas or decisions that cannot be detailed until this is answered>
```

Options are genuinely different, each with a real trade-off. Use the harness's structured-question tool when there is one; otherwise present the block above.

**The gate blocks:**

> "Blueprint saved to `docs/plans/<NNN>-<initiative>/blueprint.md`. Review it — particularly the `proposed` rows in the tech stack, the architecture decision, and the assumptions list — and answer the open questions. I'll build the detail pack (data model → API surface → integrations → delivery plan) once you approve."

Write nothing past the blueprint (`data-model.md` and on) until the human approves. A deferred question is a valid answer: record it with its owner and mark what it leaves `[TBD]`. In `DETAIL` mode the gate is shorter but still blocks: present your normalized reading of their plan (the same sections, inferences marked `#inferred`) plus the gaps to settle.

Done when the questions are asked, the gate message is shown and the run has stopped for approval.

---

## Blueprint template

**Read [`references/blueprint-template.md`](references/blueprint-template.md) before writing `blueprint.md`.** Its numbered sections, in order, are the contract.

## What stays out of a blueprint

- **Nav maps, routes, screen lists, page layouts** — `experience-plan.md` (Step 3) owns them; the blueprint names actors, their tasks and the shell.
- **Table columns, endpoint paths, field-level schemas** — Steps 2 and 4 own them; a blueprint that specifies columns is wrong before it is approved.
- **Task lists or estimates** — the delivery plan owns sequencing, once the detail exists.
- **Code**, beyond the diagrams and tables, and **silent decisions** — every consequential decision carries a `why` and an evidence mark.

## Version policy

Version-aware, keyed to `CLAUDE.md`'s Stack defaults and its Version policy. In an existing repo the **detected** version wins over every default, and the blueprint records it as `detected`.
