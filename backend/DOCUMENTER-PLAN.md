# `be-documenter` — build plan

**Date:** 2026-08-02 · **Domain:** `backend/_shared/` · **Status:** ✅ complete — all 8 phases executed 2026-08-02
**Goal:** the **reverse** of `be-planner`. Given an existing backend implementation and no requirements, read the code, split it into functional areas, plan the reading pass, then trace each area and write **business documentation from the end user's perspective** — what the system does, for whom, under what rules — into the project's BA knowledge base, modelled with flowcharts, decision tables, and state grids.

**Decisions locked** (2026-08-02, with the user):
- **Placement:** `backend/_shared/agents/be-documenter.md` + 3 skills, bundled into `be-dotnet` / `be-java` / `be-node` **and** `business-analysis`. The three `ba-*` modelling skills (+ `ba-project-memory`) get bundled into the `be-*` plugins so the diagrams have real rigor behind them.
- **Skill split:** 3 — `codebase-survey` · `feature-trace` · `business-documentation`. Modelling is **delegated** to the existing `ba-*` skills, never re-authored.
- **Artifacts:** straight into **`docs/business-model/`**, the BA knowledge base, obeying `ba-project-memory`'s contract.

---

## The central discipline — the three-tier evidence rule

Reverse documentation fails in exactly one way: stating business intent the code cannot support. The whole agent is built around keeping those tiers apart, reusing the KB's existing confidence grammar:

| Tier | Marker | Means | Example |
|---|---|---|---|
| **What the code does** | `#observed` + `file:line` | Read out of the implementation this session | "Orders older than 30 days cannot be refunded (`RefundService.cs:88`)" `#observed` |
| **What it is for** | `#inferred` | Your reading of the business intent behind that behavior | "The 30-day window aligns with the card-scheme chargeback period" `#inferred` |
| **What the business confirmed** | `#confirmed` | A human confirmed it, or a requirement document says so | — |

**A `be-documenter` run produces `#observed` and `#inferred` only.** It never emits `#confirmed`; promoting an entry is a human act. Every `#inferred` line is *also* a row in the open-questions list, which is the run's real deliverable to the business.

## Shape

```
backend/_shared/
  agents/be-documenter.md              # phased orchestrator, 7 phases, confirmation gate at Phase 1
  commands/be-documenter.md            # /be-documenter
  codebase-survey/SKILL.md             # be-shared-codebase-survey       -> area-map.md + reading plan
  feature-trace/SKILL.md               # be-shared-feature-trace         -> per-area evidence (file:line)
    references/trace-recipes.md        #   where the business rules hide, per stack + per surface
  business-documentation/SKILL.md      # be-shared-business-documentation-> the KB writes
```

### Agent phases

| # | Phase | Skill | Exit gate |
|---|---|---|---|
| 0 | Orient | — (`ep-agent-orientation-cache`, `ba-project-memory`) | Stack/version detected; **existing KB read**; run mode declared (FULL / AREA / REFRESH) |
| 1 | Survey | `codebase-survey` | **BLOCKING** — human confirms the area split, the reading order, and the depth |
| 2 | Trace | `feature-trace` | One evidence file per area; every capability has `file:line` |
| 3 | Model | `ba-process-flow-diagram` · `ba-decision-table` · `ba-entity-state-grid` | Flows, decision tables, state grids in the KB, each `**Owned by:**` its `ba-*` skill |
| 4 | Write | `business-documentation` | `areas/<area>.md` end-user narrative + use cases per area |
| 5 | Consolidate | `business-documentation` | `system-overview.md`, `glossary.md`, `INDEX.md`, `active-context.md`, open questions |
| 6 | Self-review | — | Coverage: every endpoint/job/consumer traced or explicitly deferred; every claim carries its tier marker |

### Run modes

- **FULL** — document the whole system. Phases 0→6, area by area in the confirmed reading order.
- **AREA** — one named area (the common re-invocation). Phases 0→6 scoped to it, reusing the existing area map.
- **REFRESH** *(brownfield)* — a KB already exists and the code has moved. Re-trace, then **reconcile**: `Agrees` / `New` / `Gone` / **`Contradicts`**. A contradiction between code and a `#confirmed` KB entry is escalated, never silently overwritten — the code may be the bug.

### Hard fences

- **Read-only on code.** Write reach is `docs/business-model/**` + `docs/agent-context/be-documenter.md`. `Bash` is read-only.
- **Business documentation, not technical documentation.** `ba-project-memory`'s "skip what the repo already records" rule binds: no endpoint tables, no schema dumps, no class diagrams. Those are `api-surface.md` / the OpenAPI asset / the code.
- **vs `ep-feature-audit`** — same tracing technique, opposite purpose and audience. That skill asks *"what's wrong with it"* and outputs findings for engineers into `docs/audits/`; this asks *"what does it do and for whom"* and outputs business documentation for stakeholders into `docs/business-model/`. A feature-audit report is a **first-class input** here.
- **vs `code-auditor`** — needs a spec or produces findings; this produces the documentation a spec-vs-code audit would later verify against.
- **vs `business-analyst`** — owns the KB and cross-feature conflict reasoning. `be-documenter` **populates** the KB from code and hands off; it never resolves a conflict or invents precedence.
- **vs `be-planner`** — the forward direction. A `be-documenter` run over a legacy system is the natural input to a `be-planner` EXTEND run.
- **Never emits `#confirmed`.**

---

## Phases

### Phase A — the agent + command
- [x] `backend/_shared/agents/be-documenter.md` per `.skill-template/agent.md`: frontmatter, skill-loading protocol (incl. the `ba-*` skills it loads but does not own), operating rules, brownfield section (orientation + cache field table + Mode A/B), 7-phase table, peers, both output contracts, When-uncertain.
- [x] `backend/_shared/commands/be-documenter.md`.

### Phase B — `be-shared-codebase-survey`
- [x] Breadth-first inventory: entry points (routes/controllers/handlers), scheduled jobs, queue consumers, domain modules, entities, external clients, auth surfaces, feature flags.
- [x] **Area derivation** — group by business capability, not by technical layer; the naming rule (a user would recognise the name); the size rule (an area is one sitting to trace).
- [x] **The reading plan** — order (foundational/identity areas first, they define the actors), evidence sources per area, depth per area, what is deliberately out of scope.
- [x] **The confirmation gate** — present the area table + reading order + effort, blocking. Areas named from code are the most likely thing to be wrong.
- [x] Coverage ledger: every entry point assigned to exactly one area, or explicitly parked.

### Phase C — `be-shared-feature-trace`
- [x] The trace path: entry point → authorization → input validation → orchestration → domain rules → persistence → external calls → emitted events → response/failure modes.
- [x] **What to extract** (the six inventories): capabilities · business rules & their conditions · validations & gates · entity states & transitions · decision points with their inputs · integrations with their failure behavior.
- [x] `references/trace-recipes.md` — where business rules actually hide, per stack (.NET / Spring / Node) and per surface: guard clauses, domain-service conditionals, DB constraints, config/feature flags, scheduled jobs, event handlers, migration backfills, and the "silent rule" catalogue (defaults, ordering, rounding, timezone, retry).
- [x] Evidence rules: every extracted item carries `file:line` read **this session**; negative claims name the search; the tier marker is mandatory.
- [x] Dead-code and unreachable-branch handling — documenting a capability nobody can invoke is a defect in the documentation.

### Phase D — `be-shared-business-documentation`
- [x] `areas/<area>.md` template: **what a user can do here** (plain-language capability list) · **who uses it** (actor table) · **the end-to-end use cases** (trigger → steps → outcome → what can go wrong, in user words) · **the rules that govern it** (with tier markers) · **what the user sees when it fails** · **boundaries** (what this area does *not* do) · **open questions for the business**.
- [x] The register-of-intent rule: every `#inferred` intent statement is duplicated into `open-questions.md` as a confirmable question with the evidence attached.
- [x] Language discipline: end-user vocabulary from `glossary.md`, never class names; no HTTP status codes, no table names, no framework nouns in the narrative sections.
- [x] Consolidation: `system-overview.md` (what the system is, for whom, the area map, the cross-area journeys), `glossary.md` (terms found in code, with the code name → business name mapping and drift findings), `INDEX.md`, `active-context.md`.
- [x] **The reconcile procedure** (REFRESH mode): `Agrees` / `New` / `Gone` / `Contradicts`, with the escalation rule.

### Phase E — extend `ba-project-memory`
- [x] Add `areas/<area>.md` (`AREA-nnn`, owned by `be-shared-business-documentation`) and `system-overview.md` to the KB layout, the INDEX format, and the initialization list.
- [x] Add the **provenance rule**: a code-derived artifact stamps `**Derived from:** code by \`be-documenter\` @ <commit> on <date>`, so a reader can tell generated from hand-authored.
- [x] Reconcile the "do not backfill speculatively" rule with `be-documenter`'s deliberate bulk backfill — evidence-based backfill is the stated exception; speculation is still forbidden.
- [x] Note it in the handoffs list.

### Phase F — modelling in the forward planner (the second ask)
- [x] `be-shared-solution-blueprint`: new **Step 3.5 — Model the key flows and decisions**, with a Mermaid process-flow example (named actors/swimlanes, every decision exit labeled *including* the failure exit) and a decision-table example with a declared DMN hit policy + the completeness/overlap check; route to `ba-process-flow-diagram` / `ba-decision-table` for depth, and note that state diagrams live in `data-model-plan`.
- [x] Add the produced models to the blueprint template and its approval checklist.
- [x] `be-shared-data-model-plan`: cross-reference the state-grid skill alongside its state diagrams.
- [x] `be-planner` agent: name the modelling skills in its loaded-not-owned list and its Phase 1 row.

### Phase G — wiring
- [x] `.claude-plugin/marketplace.json`: `be-*` gain the 3 new skills + `ba-project-memory` + `ba-process-flow-diagram` + `ba-decision-table` + `ba-entity-state-grid` + the agent + the command; `business-analysis` gains the 3 new skills + agent + command.
- [x] Root `CLAUDE.md`: the reverse-documentation lane in the Backend catalog, the command table row (`/be-documenter` — 71 commands), the business-analysis catalog note about the new KB artifact types.
- [x] `README.md` parity.
- [x] Verify every cited agent/skill name resolves and every path exists.

### Post-review improvements (2026-08-02, after evaluation)
- [x] **Golden example** — `business-documentation/references/example-area.md`: a filled `areas/bookings.md` for the shared `workshop-booking` toy system, demonstrating tiering, language discipline, and the six sections; SKILL.md points to it.
- [x] **Multi-session trace persistence** — `feature-trace` now persists per-area evidence to `docs/business-model/.trace/<area>.md` when a FULL run spans sessions (working files, never indexed, spot-checked as leads on resume, deleted at Consolidate); the agent's write fence names them.
- [x] **Description headroom** — agent description trimmed (1022 → ~958 chars, ~65 headroom under the 1024 limit).

### Phase H — self-review
- [x] Frontmatter names match folders; descriptions < 1024 chars with Triggers + Do-NOT.
- [x] Agent template-compliant; both output contracts present.
- [x] The `ep-feature-audit` fence is stated in the agent **and** in the two skills most likely to be confused with it.
- [x] No placeholders; every template is fillable without invention.
