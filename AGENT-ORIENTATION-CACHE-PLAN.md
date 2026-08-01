# Agent orientation cache — plan of action

**Date:** 2026-08-01
**Goal:** every agent in the library stops re-deriving the same orientation pass on every invocation. The first run writes a **current-state map** to a file in the target project; later runs **read-validate** it, re-deriving only what provably changed; every run **updates** it before finishing.
**Status:** ✅ **COMPLETE 2026-08-01.** All 5 phases done: the engine skill, the template, all **40** shipped agents, registration in all 11 plugins (marketplace `2.16.0`), and the verification pass — which found and fixed two real defects in the validation gate (see Phase 5).
**Scope:** all shipped agents across the 11 published plugins — **40** of them, not the 30 the CLAUDE.md brownfield note records (that count predates the observability, devops and BA agents). **Out of scope:** `frontend/react-native/` and the `meta/skill-creator/` agents (not shipped), and the `code-auditor` / `devops-auditor` / `standards-audit` lanes' own `docs/audits/` artifacts, which already persist state and are untouched by this.

---

## 1. The problem

Every agent's **mandatory brownfield orientation pass** (`.skill-template/agent.md` §"Orientation pass — always first") re-derives the same facts on every invocation: version lane, build/run/test commands, layout, and the inventory of **seams to reuse** (POMs, typed clients, DTOs, builders, fixtures, state containers, migrations, DI container, Step Catalog). On a large repo that is a substantial read-cost paid once per session, for an answer that changes rarely.

The orientation is **the same for every agent of a given type**, and mostly stable between runs. It should be computed once and cached.

## 2. The design

### 2.1 The artifact

`docs/agent-context/<agent-name>.md` in the **target** project — one file per agent *type* (`fe-react.md`, `be-dotnet.md`, `qa-api-typescript.md`, …), versioned with the code like `docs/app-map/` and `docs/business-model/`.

Per **agent type**, not per agent instance and not one shared file: `fe-react` records route topology and the `'use client'` boundary; `be-dotnet` records the DI container and `DbContext` design; `qa-api-typescript` records the client/DTO/builder layering. A shared file would be the union of 40 unrelated concerns and stale for everyone.

### 2.2 The three-part contract

**Read-validate → work → update-after.** Deliberately shaped like the existing `ba-project-memory` KB contract (read-first / update-after / refresh), so the library has one memory idiom rather than two.

**Read-validate** is the load-bearing half. A cached map that is silently wrong is worse than no map, so trust is *earned per run* by a cheap git-delta check, never assumed:

| Condition | Action |
|---|---|
| File missing, no `orientation-cache v1` marker, or unparseable header | **Full orientation**; write the file at the end |
| Not a git repo, or the baseline is **not an ancestor of `HEAD`** (rebase/squash/shallow) | **Full orientation** |
| `Last verified` older than **30 days** | **Full orientation** (backstop for drift git can't attribute) |
| The delta set is **empty** | **Trust in full** — skip re-derivation |
| Otherwise | **Delta pass** — refresh only the sections the changed paths touch |

The delta pass: `git diff --name-only <baseline>..HEAD` plus `git status --porcelain` paths, **excluding `docs/agent-context/` itself**. Any **fingerprint file** in the delta (manifests, lockfiles, tsconfig, build config) invalidates the whole version lane and everything keyed to it. Any changed path under a mapped area invalidates that section only. Nothing mapped in the delta → trust and note it.

**Never cached, re-derived every run:**
- **Green-on-arrival.** Build/test status is working-tree state, not layout — always re-verified through the agent's normal gate.
- **Anything the current change depends on directly.** Before editing a file the map names, confirm it still exists and still matches. *The map is a lead, not evidence* — the same rule the audit lane applies to "Resolved."
- **Live-resource facts.** `data-architect`'s server version probe and the `devops-*` cloud reads describe a system that can change without any commit. Recorded as `#volatile` and always re-probed.

**Update-after** closes every run: correct anything the run disproved, **add the seams the run created** (the highest-value delta — a new page object, typed client, migration, state container), re-stamp the baseline commit + fingerprint, prepend one session-log line (cap 10).

### 2.3 The fence — what the cache is not

It records **what the code is**. It never records what's *wrong* with it or what to do *next*: findings → `docs/audits/`, plans → `docs/plans/`, specs → `docs/specs/`, business model → `docs/business-model/`. It also never duplicates what the repo already states — a project CLAUDE.md convention is cited, not copied.

Size ceiling ~400 lines. A map, not a mirror: `page objects: tests/pages/, 34 classes, BasePage.cs:12 sets the convention` — not an enumeration of 34 classes.

### 2.4 Architecture — shared engine (**resolved**)

Same split that `ep-standards-audit-engine` proved: the **protocol** (file format, validation gate, staleness rules, write-back, fences) is 100% agent-agnostic; the **field list** (what this agent's orientation actually derives) is 100% agent-specific.

→ One skill, `engineering-practices/agent-orientation-cache/` → **`ep-agent-orientation-cache`**, registered in **all 11 plugins**. Each agent's orientation section shrinks to a pointer plus its own "what to record" list.

This adds the first `ep-*` skill to `data` and `business-analysis`, which previously bundled none (the template told them to inline `ep-*` discipline instead). Accepted deliberately: this protocol is mechanical and identical everywhere, so 3 inlined copies would drift on the first tuning of the staleness rules. `.skill-template/agent.md` §Skill-loading protocol gets updated to match.

## 3. Naming & wiring conventions (fixed)

| | Value |
|---|---|
| Skill dir | `engineering-practices/agent-orientation-cache/` |
| Frontmatter name | `ep-agent-orientation-cache` |
| Artifact | `docs/agent-context/<agent-name>.md` (target project) |
| Format marker | `<!-- orientation-cache v1 -->` (bumped only on a breaking format change; unknown version → full orientation) |
| Confidence tags | `#confirmed` (has `file:line`) · `#inferred` · `#volatile` (live resource, always re-probed) — the library's existing grammar |
| Command | **none** — reached only through an agent, per the CLAUDE.md slash-command rule (a direct call would skip the agent context that makes the fields meaningful) |

## 4. Phases

### Phase 0 — Sign-off *(no code)* ✅ **DONE 2026-08-01**
Design + architecture option confirmed (shared engine, all 11 plugins).

### Phase 1 — Author the engine skill ✅ **DONE 2026-08-01**
- [x] `engineering-practices/agent-orientation-cache/SKILL.md` — protocol, validation gate, staleness table, write-back, fences, output contract
- [x] `references/file-template.md` — the annotated artifact skeleton agents fill in
- [x] Registered in `.claude-plugin/marketplace.json` under all 11 plugins *(done in Phase 4)*

### Phase 2 — Update `.skill-template/agent.md` ✅ **DONE 2026-08-01**
- [x] §Skill-loading protocol: `ep-agent-orientation-cache` is loaded by **every** agent (not brownfield-only, and not gated on the plugin bundling `ep-*`) — retires the "inline it instead" carve-out for `data`/`business-analysis`
- [x] §Orientation pass: rewritten as read-the-cache → derive-the-gaps → re-verify-what-is-never-cached, plus the per-agent field-list table and the update-after close
- [x] §Output contract: `Orientation:` + `Orientation cache:` lines on both shapes

### Phase 3 — Roll out to every agent ✅ **DONE 2026-08-01** — 40 agents *(one family per pass, in this order)*
- [x] `fe-react` + `fe-blazor` (2) — ✅ **DONE 2026-08-01**. The shape proved out, now the pattern for the other 28: **4 edit sites per agent** — (1) the "First act" line, (2) an "Always loaded, every run" line in §Skill-loading protocol, (3) §Orientation pass rewritten as Step 1 read-the-cache / Step 2 derive-the-gaps / Step 3 re-verify-what-is-never-cached + the agent's field-list table, (4) `Orientation:` / `Orientation cache:` lines on both output shapes and an update-after line in §Branch & finish. Each agent also names its **highest-risk cached line** in Step 3 (fe-react: the `'use client'` boundary; fe-blazor: the render mode of the target surface) — the one whose staleness changes what the edit is *allowed* to do, not just where it goes.
- [x] `be-dotnet` · `be-java` · `be-node` (3) — ✅ **DONE 2026-08-01**. Highest-risk cached lines: DI lifetimes + `DbContext` registration (dotnet) · `@Transactional` boundaries + bean scopes (java) · the Prisma/Zod schema sources the types compile against (node). Each records *deliberately unadopted* patterns too — an absent CQRS is a recorded decision, not a gap the next run re-litigates.
- [x] `qa-{api,ui,mobile,performance,llm,bdd}-{java,dotnet,typescript}` (18) — one field list per *focus*, reused across the three stacks. **`qa-api-dotnet` done 2026-08-01** as the reference; the other 17 apply the same 4 edits with the stack's own version lane and commands.

  **Per-focus `Seams to reuse` + highest-risk cached line** (the only genuinely per-agent design; everything else is mechanical):

  | Focus | Seams to reuse | Highest-risk cached line | `#volatile` |
  |---|---|---|---|
  | **api** | typed clients (covered vs not) · DTOs · builders · fixtures/base classes · auth-token helper + identity set · tag/TC-ID convention · DB/messaging/email verification setup | the API's own shape | API base URL, environment, credentials source |
  | **ui** | page objects + the base-page convention · locator strategy and `data-testid` coverage · auth/storage-state setup · fixtures · waits helpers · tag/TC-ID convention | `data-testid` coverage — the app can add or drop one with no change in *this* repo | app URL, env, `missing-testids.md` staleness |
  | **mobile** | screen objects + base class · accessibility-id strategy · the `docs/app-map/` screen map (if present) · capabilities/driver setup · device-cloud config | the app build the map was captured against | device/emulator + installed build (always re-probed) |
  | **performance** | scenario/scripts layout · the shared load-model config · thresholds/SLO gates and where they live · test-data sources · results output path | the thresholds — a moved SLO silently changes pass/fail | target environment + its capacity |
  | **llm** | the eval spine (promptfoo/DeepEval/Ragas) and its config · golden set + reference contexts location · judge model **pinning** · red-team preset config · pass-rate thresholds | the pinned judge model + its version | the model endpoint and its deployed version |
  | **bdd** | the **Step Catalog** · `.feature` layout + Background/Outline conventions · step-definition domain split · the state model (Reqnroll `ScenarioState` / PicoContainer `TestContext` / Playwright fixtures / CucumberJS World) · hooks + teardown · the page objects steps bind to · tags | the Step Catalog — a duplicated step is exactly what it exists to prevent | app URL, env |

  For the four non-stack QA agents: **cicd** records the CI host + pipeline file layout, shard matrix, secret/OIDC wiring (`#volatile`: anything read from the CI service itself) · **reporting** records the Allure wiring, categories file, tag conventions, flake-quarantine state · **security** records which scanner gates exist and where their configs/baselines live (`#volatile`: every live scan result — the cache records *that a gate exists*, never a finding) · **test-case-designer** records the test-basis sources and suite layout only.
- [x] `qa-cicd-*` (3) · `qa-reporting-*` (3) · `qa-security` · `qa-test-case-designer` (8)
- [x] `observability-engineer-{dotnet,java,node}` (3)
- [x] `devops-engineer` · `devops-auditor` (2) — the Phase-0 Discover inventory *is* the cache; `#volatile` on every live-cloud read
- [x] `data-architect` (1) — `#volatile` on the server version probe; repo-side migration/schema layout is cacheable
- [x] `code-auditor` (1) — cache the surface decomposition only; verdicts stay in `docs/audits/`
- [x] `requirements-author` · `business-analyst` (2) — thin: the KB *is* their memory; cache only the repo-side doc layout

### Phase 4 — Registration & docs ✅ **DONE 2026-08-01**
- [x] `.claude-plugin/marketplace.json` — added to all 11 plugins' `skills` arrays (beside `ep-standards-audit-engine` where present)
- [x] `CLAUDE.md` — full entry in the engineering-practices cross-cutting list + the bundling-count note
- [x] `README.md` — the "16th `ep-*` skill, ships in all eleven plugins" paragraph
- [x] Bumped marketplace `metadata.version` → **2.16.0**

### Phase 5 — Verify ✅ **DONE 2026-08-01** — 10 of 11 checks executed against a git fixture; **2 real defects found and fixed**

Executed with a throwaway repo + an executable model of the gate (`scratchpad/gate.py`), all passing after the fixes:

| # | Case | Verdict |
|---|---|---|
| 1 | warm run, clean tree | TRUST — no changes since baseline |
| 2 | change outside every mapped area | TRUST — delta touches nothing mapped |
| 3 | mapped source changed, **uncommitted** | DELTA — `src/` |
| 4 | mapped source changed, committed | DELTA — `src/` |
| 5 | manifest/lockfile changed | DELTA — version lane + all keyed sections invalid |
| 6 | baseline not an ancestor of HEAD (squash/rebase) | FULL |
| 7 | `Last verified` 200+ days old | FULL |
| 8 | unknown format-marker version | FULL |
| 9 | header field missing | FULL |
| 10 | no cache file | FULL |
| 11 | not a git repo | FULL |

**Defect 1 — the TRUST path could never fire.** Update-after stamps the current `HEAD` into the cache, and committing that stamp is itself a change, so a literal `HEAD == baseline && clean tree` test is false forever once the cache is committed. **Fix:** the gate's TRUST condition is now "the delta set is empty", and `docs/agent-context/` is excluded from the delta set — the cache's own churn is not evidence about the code.

**Defect 2 — the rebase check tested the wrong thing.** `git cat-file -e <baseline>` asks whether the object *exists*, and after a rebase or squash the abandoned commit usually still sits in the local object store — so the check passed and `git diff <baseline>..HEAD` produced a large meaningless delta. It only behaved correctly on a fresh clone where the object had been gc'd. **Fix:** `git merge-base --is-ancestor <baseline> HEAD`, which asks the question that actually matters, plus an explicit note in the skill about why.

- [x] Not executable — **"a deliberately wrong line is corrected, not acted on"** is a behavioral guarantee of the *agent*, carried by the "map is a lead, not evidence" spot-check and the update-after "correct what the run disproved" step. It cannot be verified by a script; it needs a live agent run on a real project, which is the first real-world use of this feature.

## 5. Risks & fences

| Risk | Mitigation |
|---|---|
| **Stale cache acted on as fact** — the whole risk of the feature | Delta gate + 30-day expiry + "the map is a lead, not evidence" spot-check before editing any file it names |
| Cache drifts into a findings/plans dump | §2.3 fence, restated in the skill; size ceiling |
| Two parallel runs of the same agent type both write | Last writer wins; the next run's delta check self-heals. Documented, not engineered around |
| Non-git projects get no validation signal | Explicitly → full orientation every run (no cache benefit, no cache risk) |
| Agents skip the update-after step when a run ends early | Update-after is part of the Output contract, so an incomplete run reports it as skipped rather than silently dropping it |

## 6. Definition of done

All 30 agents load `ep-agent-orientation-cache`, carry their own field list, and report an `Orientation:` line; the skill ships in all 11 plugins; Phase 5 checks pass; `CLAUDE.md` + `README.md` + `.skill-template/agent.md` describe the contract.
