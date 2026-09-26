# `be-planner` — build plan

**Date:** 2026-08-02 · **Domain:** `backend/_shared/` · **Status:** ✅ complete — all 8 phases executed 2026-08-02
**Goal:** a stack-agnostic backend **planning** agent that turns a business case or loose requirements into (1) an approved high-level blueprint and (2) a detailed, executable plan pack — DB structure, service→resource→endpoint surface with request/response bodies, a shared validation catalog, an external-dependency register, and an ordered task list with a plan+handoff loop. Runs standalone (`/be-planner`) or feeds Mission Control.

**Decisions locked** (2026-08-02, with the user):
- **Placement:** `backend/_shared/` — agent + 5 skills, bundled into **all three** `be-*` plugins (the planner picks the stack, so it cannot live under one).
- **Skill split:** 5 skills, one per artifact.
- **Artifacts:** one folder per initiative — `docs/plans/NNN-<initiative>/{blueprint,data-model,api-surface,integrations,delivery-plan}.md` + `HANDOFF.md`, resolved under the **target project's** root.

---

## Shape

```
backend/_shared/
  agents/be-planner.md                 # phased orchestrator, 7 phases, blocking gate at Phase 1
  commands/be-planner.md               # /be-planner
  solution-blueprint/SKILL.md          # be-shared-solution-blueprint   -> blueprint.md
  data-model-plan/SKILL.md             # be-shared-data-model-plan      -> data-model.md
  api-surface-plan/SKILL.md            # be-shared-api-surface-plan     -> api-surface.md
    references/validation-catalog.md   #   the shared validation/error set (the big reusable piece)
  integration-plan/SKILL.md            # be-shared-integration-plan     -> integrations.md
  delivery-plan/SKILL.md               # be-shared-delivery-plan        -> delivery-plan.md + HANDOFF.md
    references/handoff-template.md
```

### Agent phases

| # | Phase | Skill | Exit gate |
|---|---|---|---|
| 0 | Discover & orient | — (`ep-agent-orientation-cache`) | Entry mode declared (NEW / DETAIL / RESUME / EXTEND) + current-state map |
| 1 | Blueprint | `solution-blueprint` | **BLOCKING** — human approves `blueprint.md`; open questions answered |
| 2 | Data model | `data-model-plan` | `data-model.md` — every functional area's entities covered |
| 3 | API surface | `api-surface-plan` | `api-surface.md` — every endpoint typed + mapped to the validation catalog |
| 4 | Integrations | `integration-plan` | `integrations.md` — every external system has auth, config keys, failure mode, test strategy |
| 5 | Delivery plan | `delivery-plan` | `delivery-plan.md` + `HANDOFF.md` — every task has an agent, files, deps, AC |
| 6 | Self-review | — | Coverage table: area→tasks, endpoint→tables, integration→task; zero placeholders |

### Entry modes

- **NEW** — nothing exists. Phases 0→6.
- **DETAIL** — a high-level plan already exists (human-written or a prior `blueprint.md`). Phase 1 validates + normalizes it instead of authoring it, then 2→6.
- **RESUME** *(brownfield Mode A)* — plan artifacts + partial implementation exist. Reconcile plan against code (`Done / Partial / Not started / Diverged`, `file:line` evidence, read this session), rewrite `HANDOFF.md`, re-enter only the touched phases.
- **EXTEND** *(brownfield Mode B)* — new functional area onto an existing plan/codebase. Append with the next free IDs, never renumber.

### Hard fences

- **Writes plan artifacts only** — `docs/plans/NNN-<initiative>/**` plus its orientation cache. Never production code, never a migration, never a `.csproj`/`package.json`. Execution belongs to `be-dotnet`/`be-java`/`be-node`.
- **vs `ep-brainstorming` + `ep-writing-plans`** — those are the generic stack-agnostic chain. `be-planner` is the backend specialization producing a multi-artifact pack with API/DB/integration depth. Its Phase-1 gate satisfies `ep-brainstorming`'s HARD-GATE (that skill's own scope clause exempts phased agents with their own design gate).
- **vs `data-architect`** — the planner produces the **logical** model + migration ordering; `data-architect` owns engine selection depth, DDL, indexing strategy, RLS, partitioning, cross-engine migration.
- **vs `business-analyst` / `requirements-author`** — they own requirements and cross-feature conflict analysis; the planner **consumes** their artifacts (`docs/business-model/`, epics, stories) and never authors them.
- **vs Mission Control's own planner** — MC splits a plan into a task graph; `be-planner` *produces* the plan. `delivery-plan.md` is shaped so MC ingests it near-1:1.

### Mission Control contract

`delivery-plan.md` task rows carry exactly the fields MC's planner prompt consumes: `id · phaseId · title · intent · acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]`, plus per-phase `parallelSafe` + `parallelRationale`, plus `openQuestions[]` with 2–4 options each and one marked recommended. Agent and skill names must be **exact catalog names**.

---

## Phases

### Phase 1 — the agent + command
- [x] `backend/_shared/agents/be-planner.md` per `.skill-template/agent.md`: frontmatter (name, description with triggers + Do-NOT routing, `tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch`, `model: inherit`), skill-loading protocol, operating rules, brownfield section (orientation pass + cache field table + Mode A/B), phase table, peer list, both output contracts, When-uncertain.
- [x] `backend/_shared/commands/be-planner.md` mirroring `backend/dotnet/commands/be-dotnet.md`.

### Phase 2 — `be-shared-solution-blueprint`
- [x] Functional-area decomposition · architecture-style decision with the earned-complexity rule · tech-stack table with `detected`/`stated`/`proposed` evidence marks · external systems at architecture altitude · **routing map** (area/concern → exact library agent + skills) · non-functional targets · risks & assumptions.
- [x] **Question discipline:** batch into one message, 2–4 concrete options each with a real trade-off, one marked recommended, only where the answer materially changes the work. Blocking approval gate procedure.
- [x] Annotation grammar reused from `ba-project-memory`: `#confirmed` / `#inferred` / `[TBD - reason]` / `⚠️ Assumption:`.

### Phase 3 — `be-shared-data-model-plan`
- [x] Entity catalog (entity → owning service/module → purpose → lifecycle states) · per-table spec (columns, types, nullability, defaults, PK/FK/unique, indexes each justified by the query it serves) · cross-cutting conventions (UUIDv7 ids, money as minor units/decimal, UTC timestamps, soft-delete policy, tenancy pattern, audit columns, concurrency token) · Mermaid ER diagram · reference/seed data · **migration sequence** mapped to delivery tasks.
- [x] Fence block to `data-architect`.

### Phase 4 — `be-shared-api-surface-plan`
- [x] Three-level **service → resource → endpoint** table (method, path, name, one-line description, auth requirement, idempotency, success status).
- [x] Per-endpoint contract blocks — request path/query/body and response body as compact typed field tables (field, type, required, constraints, notes); the swagger-equivalent without hand-writing OpenAPI.
- [x] `references/validation-catalog.md` — the **shared** set defined once and referenced per endpoint as "standard set + deltas": malformed body · field validation (required/type/format/range/length/enum) · 401 missing/expired/malformed token · 403 not-permitted incl. tenant-scoped · 404 not-found + the not-found-vs-forbidden disclosure rule · 409 duplicate-unique / version-mismatch / illegal-state-transition · 412/428 precondition · 415 · 429 · 5xx · **referential-integrity rules** (referenced id exists, is visible to the caller, is in a valid state) · pagination/sort/filter contract + list envelope · RFC 9457 ProblemDetails error body · idempotency keys · ETag/If-Match.
- [x] Versioning + deprecation policy. Handoff: `qa-api-<stack>` writes contract tests from this table; if an OpenAPI asset already exists, route to `qa/_shared/api-spec-assets`.

### Phase 5 — `be-shared-integration-plan`
- [x] Dependency register (system → purpose → direction → protocol → criticality → owner) · per-dependency block (auth method, config keys + secret-store location **never values**, sandbox vs prod, rate limits/quotas, timeout/retry/circuit-breaker, failure mode + degradation, PII crossing the boundary) · category guidance (email/notification, payments, storage, IdP, search, brokers, third-party APIs, **inbound webhooks** — signature verification, replay, idempotency).
- [x] Local-dev + test strategy per dependency, naming the qa skills (`network-mocking`, `email-testing`, `messaging-testing`, `file-storage-testing`).
- [x] Secrets checklist (name, store, who provisions, needed by which task, rotation) and the **blocking-unknown** rule: anything needing human-provisioned credentials becomes both an open question and a prerequisite task.
- [x] Fence to `devops-engineer` (owns the actual store + config wiring).

### Phase 6 — `be-shared-delivery-plan`
- [x] Phase/task breakdown with the MC-compatible row schema · parallel-safety call + rationale (disjoint-files rule) · sequencing rules (foundations sequential: scaffold → config → auth → shared types → schema; feature slices parallel after; per-slice order migration → domain/persistence → service → endpoint → contract test → wiring) · per-task DoD.
- [x] `references/handoff-template.md` — the **plan + handoff loop**: initiative, current phase, last completed task, next task, decisions made (with the question each answered), blocked-on, **deviations** (built differently + why), artifacts touched, how to verify current state, resume instructions, session-log tail. Rewritten each session, not appended.
- [x] **Reconcile procedure** for RESUME: per-task `Done / Partial / Not started / Diverged` with `file:line` evidence — *the plan is a lead, not evidence*; status claimed only after reading the code this session.
- [x] "Paste into Mission Control" section.

### Phase 7 — wiring
- [x] `.claude-plugin/marketplace.json`: add the 5 skills + agent + command to `be-dotnet`, `be-java`, `be-node`; extend the three plugin descriptions.
- [x] Root `CLAUDE.md`: Backend catalog entry, the slash-command table row (`/be-planner` — 70 commands total), the `_shared` line.
- [x] `README.md` parity pass.
- [x] Verify every agent/skill name the blueprint routing map and delivery-plan examples cite resolves in the catalog.

### Post-review improvements (2026-08-02, after evaluation)
- [x] **Golden example pack** — one filled example per artifact skill (`references/example-{blueprint,data-model,api-surface,integrations,delivery-plan}.md`), all describing the same toy initiative `001-workshop-booking`; each SKILL.md points to its example (shapes normative, domain illustrative).
- [x] **OpenAPI-asset task** — `delivery-plan` Step 1 gains a standard derivation row: after the last endpoint slice, a `be-<stack>` task generates + commits the canonical `{service}-openapi-YYYY-MM-DD.json` so `qa/_shared/api-spec-assets` has its input from day one; `api-surface-plan`'s handoff notes it.
- [x] **Description headroom** — agent description trimmed (~65 chars under the 1024 limit → ~930).
- [x] **Grammar drift** — blueprint's `#observed` row now names `ba-project-memory`'s grammar as canonical.

### Phase 8 — self-review
- [x] Frontmatter `name` matches folder for all 5 skills; descriptions carry Triggers + Do-NOT and are < 1024 chars.
- [x] Agent is `.skill-template/agent.md`-compliant (two modes, orientation pass, cache field table, phase table with exit gates, peers, both output contracts, When-uncertain).
- [x] Every cross-reference resolves on disk; no pointers to under-construction folders.
- [x] No placeholders; the artifact templates are complete enough to fill in without invention.
