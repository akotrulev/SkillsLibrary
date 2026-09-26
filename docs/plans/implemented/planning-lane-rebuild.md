# Planning-lane rebuild — change plan

**Date:** 2026-08-30 · **Status:** implemented 2026-08-30 · **Scope:** the planning lane only (`backend/_shared/`, `business-analysis/agents/requirements-author.md`, `engineering-practices/{writing,executing}-plans`, and the references to them)

> **Implementation state:** T1–T12 are applied. Three deviations from this document, all deliberate:
>
> 1. **T3 — the wave rule was loosened.** §3.3 read as though the task order had to march wave by wave, which would forbid feature-complete sequencing. The rule shipped as *"the order is a valid serialization of `epic-map.md`'s dependency graph"* — the waves stay the concurrency claim, carried by the streams table, and a wave-3 lane's task may sit above a wave-2 lane's when its own dependencies are met.
> 2. **T6 vs §8 — the security lane.** T6 asked that nothing reference a `-explained.md` companion, while §8 leaves the security lane untouched. `security-architect` and `security-test-planner` keep writing their companions; only their citation of the now-deleted skill by name was removed, so T12's sweep finds nothing dangling.
> 3. **Added on request — the plain-English epic section.** `ba-epic-writer` gained an `epics.md` §2 carrying an *as-a / I-want / so-that* line, **what gets built**, and **how it fits with everything else**, with no technology in it at all; `requirements-author` gates on it, `solution-blueprint` areas carry the epic ids they serve, and `epic-map.md`'s dependency reasons compress that paragraph rather than inventing their own.

---

## 1. Why

The library can already plan a build. What it cannot do is hand that plan to an operator as a series of sessions that each fit in a context window, run the independent parts at the same time, and carry their own next instruction.

The requested flow is:

> Describe roughly what needs building → an agent refines it into requirements → the requirements are scoped into work → the work is split into tasks **per tech stack**, so one agent owns each → the tasks are sized so a session runs one of them → tasks that can run at the same time are marked as such → each lane always carries a ready-to-paste prompt for its next task, regenerated as tasks land.

Four of those seven steps have no owner today:

| Step | Today |
|---|---|
| Refine a loose ask into requirements | `requirements-author` exists, but runs a 3-artifact backlog chain rather than a refinement conversation |
| Scope into epics and stories | `ba-epic-writer` / `ba-story-writer` exist as skills; nothing drives them as one flow |
| Split tasks per stack | Tasks bind to an agent, but nothing forbids a task spanning `fe` and `be` |
| **Size a task to one session** | **Missing entirely** |
| **Mark what runs in parallel** | Partly — the streams table says which lanes may run concurrently, but at task level, not at epic level |
| **Generate the next task's prompt** | **Missing entirely** — `HANDOFF.md` describes what is next in prose |
| Regenerate that prompt after each task | **Missing entirely** |

---

## 2. Target state

### 2.1 The ladder

```
requirements  →  epics  →  stories  →  tasks  →  sessions
                  E1..En    US1..USn   T1..Tn    1 task = 1 session
```

One task belongs to exactly one story, one epic, one stack, and one agent. Ids: epics `E1`, stories `US1`, tasks `T1`. Screens keep their existing `S1` prefix — `US` was chosen for stories specifically so the experience plan and API surface do not have to be renumbered.

### 2.2 Agents

| Agent | Change | Job |
|---|---|---|
| `requirements-author` | **rewritten in place** (name kept — 20+ files route to it) | The front door. Refines a loose description through batched questions into `requirements.md`, then `epics.md`, then `stories.md`. |
| `solution-planner` | **renamed** from `be-planner` | Whole-app planner: blueprint → approval gate → detail pack → epic map → tasks → sizing → prompts. The old name said "backend" while the agent already planned screens, journeys and frontend tasks. |
| `be-dotnet` · `be-java` · `be-node` · `fe-react` · `fe-blazor` | **edited** | Executors. Gain one duty: on finishing a task, write status back **and** regenerate their lane's prompt block. |
| `business-analyst` | unchanged | The reasoning lane (KB, cross-feature conflicts) is untouched. |

No new executor agents. Nothing outside this table gains a planning role.

### 2.3 Skills

| Skill | Status | Artifact |
|---|---|---|
| `ba-scoping-writeup` · `ba-epic-writer` · `ba-story-writer` | unchanged, newly driven by `requirements-author` | `requirements.md` · `epics.md` · `stories.md` |
| `ba-story-quality-review` | unchanged, no longer agent-driven | invoked directly when a backlog needs auditing |
| `be-shared-solution-blueprint` | edit — drop companion step, carry epic ids | `blueprint.md` |
| `be-shared-data-model-plan` | unchanged | `data-model.md` |
| `be-shared-experience-plan` | light edit — drop companion handoff | `experience-plan.md` |
| `be-shared-api-surface-plan` | unchanged | `api-surface.md` |
| `be-shared-integration-plan` | unchanged | `integrations.md` |
| **`be-shared-epic-map`** | **new** | `epic-map.md` |
| `be-shared-delivery-plan` | substantial rewrite | `delivery-plan.md` |
| **`be-shared-session-budget`** | **new** | task estimates + `NEXT-PROMPTS.md` |
| `be-shared-plain-language-companion` | **deleted** | — (the six `-explained.md` companions go away) |

### 2.4 Artifacts per initiative

```
docs/plans/<NNN>-<initiative>/
  requirements.md      the refined ask — actors, rules, constraints, out-of-scope
  epics.md             E1..En, each a WHO / DO WHAT / SO THAT MEASURABLE outcome
  stories.md           US1..USn under their epics, with acceptance criteria
  blueprint.md         areas, architecture, stack, routing map     ██ approval gate
  data-model.md        entities, specs, migrations
  experience-plan.md   actors, journeys, screens, app shell
  api-surface.md       endpoints, contracts, validation catalog
  integrations.md      external dependencies, secrets, failure modes
  epic-map.md          epic dependencies + parallel waves
  delivery-plan.md     T1..Tn — one epic, one story, one stack, one agent, one session
  NEXT-PROMPTS.md      one ready-to-paste prompt per lane runnable right now
```

`HANDOFF.md` is retired. `NEXT-PROMPTS.md` answers the same question — *what next* — as something runnable rather than something to read.

---

## 3. The three new mechanics

### 3.1 One stack per task

Every task block gains a `**Stack:**` field taking exactly one of `be` · `fe` · `ts` · `data` · `infra` · `qa` · `docs` · `human` — a superset of the global task rules' `be`/`fe`/`ts`/`docs` (shared TypeScript packages stay their own `ts` lane, documentation passes are `docs`; `data`/`infra`/`qa`/`human` are the ops lanes this flow adds) — and one hard rule:

> A task that touches both the API tree and the web tree is two tasks. There is no mixed task at any size, and no estimate justifies one.

This is what makes a task handable to a single stack agent without it wandering across a boundary it does not own. It also makes the batching mechanical rather than a judgement call: the tasks of one stack within one epic are already adjacent.

### 3.2 Sizing to a session

**One task is executed in one session**, so its context cost is a property of the task. The cost is estimated while the task is being authored — not measured afterwards, which would make it trivia.

**The floor — every session pays it, once:**

| Line | Estimate |
|---|---|
| System prompt + tool schemas | 12k |
| `CLAUDE.md` and project instructions | 6k |
| The executing agent's own definition | 7k |
| **Floor** | **25k** |

**Loaded once per session:**

| Line | Estimate |
|---|---|
| Each distinct skill the task loads | 8k |
| The task block itself | 1k |
| Each design-pack **section** cited (`api-surface.md` §5.3, one entity block, one screen) | 2k |
| Orientation — repo survey + orientation cache (brownfield only) | 8k |

**Per file the task touches:**

| Line | Estimate |
|---|---|
| An existing file the task must read | `bytes ÷ 3.5`, or **3k** when it cannot be measured |
| A source file created | 2k |
| A UI component or screen created | 3k |
| A test file created | 2k |
| A file modified in place | 1.5k |
| A registration, config key, or migration entry | 0.5k |

**Per task, once:** build + test run and the fix loop it triggers, **12k**; then **× 1.2** on the whole sum for conversation and tool churn.

`Est. = (floor + skills + sections + orientation + files + verify) × 1.2`

**Worked example** — a `be-dotnet` Orders resource task: 25k floor + 24k (3 skills) + 1k task block + 6k (3 sections) + 10k (4 source files + 1 test) + 1.5k (1 modified) + 12k verify = 79.5k × 1.2 = **~95k**.

**The target, and what it is not.** Aim for **~80k–150k**, centred on ~130k. Under ~80k, look at the next task in the same story and same stack — merge only if the result still states **one** deliverable. Over ~150k, annotate the task with its estimate and name its natural split point.

> **The estimate is a guide, never a gate.** Three rules outrank it, always: one deliverable; one stack and one agent; a green tree at every task boundary. A task that overshoots with all three satisfied is a large task correctly authored — it is labelled, not filed as a defect. Never split something coherent to hit a number, and never pad a task to fill one.

The estimate is recorded on the task and in the progress table, with its drivers, so a 95k of many small files is distinguishable from a 95k of one large one:

```markdown
**Est. context:** ~95k — 5 files created, 1 modified, 3 skills, 3 pack sections
```

### 3.3 Parallel epics and regenerated prompts

**`epic-map.md`** marks two epics parallel only when their task **file sets are disjoint** and neither depends on the other — the same hard rule the streams table already applies at task level. Foundation and contract work is `E0`, which everything waits on. `E0` is **planner-created**: it never appears in `epics.md` (which stays `E1..En` from `requirements-author`), carries no stories, and exists only in `epic-map.md` and `delivery-plan.md` — a cross-artifact check must not expect a backlog entry for it. The output is waves:

```
Wave 1   E0  contract + foundations           1 session, must land first
Wave 2   E1 ∥ E3 ∥ E4                          3 sessions, concurrently
Wave 3   E2  (depends on E1)                   1 session
```

Within an epic, stories that share no files run concurrently too — so a lane is a story, not always a whole epic.

**`NEXT-PROMPTS.md`** carries one block per lane that is runnable **right now** — at the start of a run, the first task of every wave-1 epic, which is exactly the set of sessions the operator can open at once. Each block is a prompt, not a summary: the agent to adopt, the skills to load, **the exact pack sections to read** (`api-surface.md` §5.3 — never the whole artifact, which is the single biggest lever on the estimate holding), the deliverable, the files, the acceptance criteria, what is out of scope, and the closing duty.

**The regeneration loop** is the executing agent's, as part of finishing the task:

1. Status, evidence and ticked criteria into `delivery-plan.md` §2/§3/§6 — the durable record.
2. Replace that lane's block in `NEXT-PROMPTS.md` with the next task's prompt.
3. If that was the lane's last task, close the lane and check `epic-map.md` — completing an epic usually unblocks a wave, and every newly runnable lane needs a block.
4. `Partial` / `Blocked` / `Diverged` keeps the block on the **same** task, with a `Picking up from:` line. A blocked lane keeps its block and names its blocker and owner — deleting it loses the lane.

---

## 4. The flow, end to end

```
/dev-refine  "a booking app for a gym — members book classes, staff manage the timetable"
    ├─ batched questions, at most two rounds
    ├─ requirements.md
    ├─ epics.md      E1 Membership · E2 Timetable · E3 Booking · E4 Staff admin
    └─ stories.md    US1..US14

/dev-plan-solution  docs/plans/003-gym/
    ├─ blueprint.md          ██ BLOCKING — you approve areas, architecture, stack, routing
    ├─ data-model.md
    ├─ experience-plan.md
    ├─ api-surface.md
    ├─ integrations.md
    ├─ epic-map.md           E0 → (E1 ∥ E2) → E3 → E4
    ├─ delivery-plan.md      T1..T23, each one stack, one session, with its estimate
    └─ NEXT-PROMPTS.md       blocks for E0's first task

you: open a session, paste the E0 block
    agent runs T1 → updates delivery-plan.md → rewrites NEXT-PROMPTS.md
    E0 completes → wave 2 opens → two blocks appear → two sessions run at once
```

---

## 5. Rebuild tasks

Flat, ordered, workable. The library builds and its catalog resolves at every boundary.

### T1 — `be-shared-epic-map` skill

**Deliverable:** `backend/_shared/epic-map/SKILL.md` plus a filled example, defining `epic-map.md`: epics with their stories and tasks, cross-epic dependencies, the disjoint-file-set parallelism rule, and the wave table.
**Files:** create `backend/_shared/epic-map/SKILL.md`, `backend/_shared/epic-map/references/example-epic-map.md`

### T2 — `be-shared-session-budget` skill

**Deliverable:** `backend/_shared/session-budget/SKILL.md` plus the prompt template, defining the cost model, the sizing procedure, `NEXT-PROMPTS.md`, and the post-task regeneration protocol.
**Files:** create `backend/_shared/session-budget/SKILL.md` *(drafted)*, `backend/_shared/session-budget/references/next-prompts-template.md`

### T3 — Rewrite `be-shared-delivery-plan`

**Deliverable:** the delivery-plan skill produces tasks carrying `Epic` / `Story` / `Stack` / `Est. context`, enforces one stack per task, derives lanes from `epic-map.md`, and points at `NEXT-PROMPTS.md` instead of `HANDOFF.md`.
**Depends on:** T1, T2
**Files:** modify `backend/_shared/delivery-plan/SKILL.md`, `backend/_shared/delivery-plan/references/example-delivery-plan.md`; delete `backend/_shared/delivery-plan/references/handoff-template.md`

### T4 — Rewrite the `requirements-author` agent

**Deliverable:** `/dev-refine` takes a loose description, asks batched questions, and writes `requirements.md` + `epics.md` + `stories.md` into the initiative folder, ready for `/dev-plan-solution`.
**Files:** modify `business-analysis/agents/requirements-author.md`, `business-analysis/commands/requirements-author.md`

### T5 — Create the `solution-planner` agent

**Deliverable:** `/dev-plan-solution` runs the nine-step pipeline (orient → blueprint gate → data model → experience → API surface → integrations → epic map → delivery plan → sizing & prompts → self-review) and `be-planner` no longer exists.
**Depends on:** T1, T2, T3, T4
**Files:** create `backend/_shared/agents/solution-planner.md`, `backend/_shared/commands/solution-planner.md`; delete `backend/_shared/agents/be-planner.md`, `backend/_shared/commands/be-planner.md`

### T6 — Delete the plain-language companion lane

**Deliverable:** `backend/_shared/plain-language-companion/` is gone and no skill, agent or manifest references a `-explained.md` companion; `be-shared-solution-blueprint` carries the epic ids from `epics.md` on its areas (the §2.3 "carry epic ids" edit lands here).
**Depends on:** T3, T5
**Files:** delete `backend/_shared/plain-language-companion/`; modify `backend/_shared/experience-plan/SKILL.md`, `backend/_shared/delivery-plan/SKILL.md`, `backend/_shared/solution-blueprint/SKILL.md`

### T7 — Give the executor agents the regeneration duty

**Deliverable:** each of the five stack agents, on finishing a plan task, updates `delivery-plan.md` and regenerates its lane's block in `NEXT-PROMPTS.md`; their output contracts name both files, no longer reference `HANDOFF.md`, and name `solution-planner` instead of `be-planner` (their share of the T9 rename lands here — one pass per file, not two).
**Depends on:** T2, T5
**Files:** modify `backend/{dotnet,java,node}/agents/be-*.md`, `frontend/{react,blazor}/agents/fe-*.md`

### T8 — Fold sizing into the `ep-*` plan skills

**Deliverable:** `ep-writing-plans` sizes its tasks with the same cost model and types them by stack; `ep-executing-plans` performs the regeneration step at its per-task checkpoint.
**Depends on:** T2
**Files:** modify `engineering-practices/writing-plans/SKILL.md`, `engineering-practices/executing-plans/SKILL.md`

### T9 — Rename `be-planner` across the library

**Deliverable:** no live file refers to `be-planner`; every peer agent, skill handoff and doc names `solution-planner`. Historical records are exempt (D9): the root `*-PLAN.md` archive, `docs/plans/*.md` other than this one, and `docs/audits/*.md` keep their references as written, and T12's sweep skips them.
**Depends on:** T5, T7
**Files:** modify `README.md`, `CLAUDE.md`, `design/ux-review/SKILL.md`, `design/agents/design-auditor.md`, `tooling/agents/tooling-engineer.md`, `tools/MISSION-CONTROL-MOVED.md`, `security/agents/security-test-planner.md`, `backend/node/skills/unit-testing/SKILL.md`, `backend/_shared/agents/be-{documenter,feature-documenter}.md`, `backend/_shared/{api-surface-plan,integration-plan,solution-blueprint,business-documentation,codebase-survey,data-model-plan,experience-plan}/SKILL.md` *(the five stack agents are renamed in T7)*

### T10 — Update the plugin manifest

**Deliverable:** `be-dotnet`, `be-java` and `be-node` ship `epic-map` and `session-budget`, drop `plain-language-companion`, and reference `solution-planner`; **`fe-react` and `fe-blazor` also ship `session-budget`** (today they ship no `backend/_shared` skill — verified — and T7 makes their agents consumers of its regeneration protocol and prompt template); the `business-analysis` plugin description matches the rewritten agent.
**Depends on:** T5, T6, T9
**Files:** modify `.claude-plugin/marketplace.json`

### T11 — Update the catalog and README

**Deliverable:** `docs/skills-catalog.md` and `README.md` describe the planning lane as built — the ladder, the eleven artifacts, the two new skills, the renamed agent.
**Depends on:** T9, T10
**Files:** modify `docs/skills-catalog.md`, `README.md`

### T12 — Self-review sweep

**Deliverable:** every agent and skill name cited anywhere in the planning lane resolves to a file on disk; no artifact references a deleted one; the manifest's skill paths all exist.
**Depends on:** T1–T11
**Files:** none (report only)

---

## 6. Decisions already taken

| # | Decision | Why |
|---|---|---|
| D1 | Rename `be-planner` → `solution-planner` | It plans frontend, data and integrations too; the name was wrong and the confusion compounds |
| D2 | Keep the full detail pack, drop the `-explained.md` companions | The engineering detail is what makes each task cheap to run; the six plain-language translations were writing time with no consumer in this flow |
| D3 | Rewrite `requirements-author` rather than adding a new agent | One front door. The epic and story layers stay because the ladder needs them |
| D4 | `US` for story ids | `S` is already the screen prefix across `experience-plan.md` and `api-surface.md`; `US` avoids renumbering them |
| D5 | Retire `HANDOFF.md` in favour of `NEXT-PROMPTS.md` | Same question, answered as something runnable. Two files answering it would drift |
| D6 | The estimate is a target, not a gate | Coherence decides what a task is. A number that can split a coherent task produces unverifiable fragments |
| D7 | `epic-map.md` is a separate artifact, not a `delivery-plan.md` section | Reviewable on its own, which is where the parallelism decision actually gets checked; T1 and §2.4 are written against this |
| D8 | The 12k verify constant stays, and the first real session's orientation pass calibrates it | The drafted skill's version policy already says measure-and-adjust; one real run replaces the guess without blocking authoring on a measurement |
| D9 | Historical records keep their `be-planner` references | The root `*-PLAN.md` archive, `docs/plans/*.md` (other than this plan) and `docs/audits/*.md` are records of decisions as made; T9 exempts them and T12's sweep skips them |

## 7. Open questions

None — Q1–Q3 were resolved into D7–D9.

## 8. Deliberately not changing

- **`business-analyst`** and the `docs/business-model/` KB — the reasoning lane is orthogonal to this flow.
- **The detail-pack skills** `data-model-plan` and `api-surface-plan` — they already produce what the tasks need.
- **The streams table** in `delivery-plan.md` — epic waves sit above it; task-level concurrency and file-overlap safety stay exactly as they are.
- **Mission Control ingestion** — the field vocabulary is preserved; `epic`, `story`, `stack` and `estContext` are additive.
- **`qa-test-planner`, `security-test-planner`** and the other domain planners — different lanes, not part of this flow.
- **The root `*-PLAN.md` archive, prior `docs/plans/*.md` and `docs/audits/*.md`** — historical records, left as written (D9).
