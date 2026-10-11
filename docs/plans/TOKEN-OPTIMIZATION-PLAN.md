# Token-usage optimization plan (library-wide)

**Goal:** cut the context cost of installing/using any plugin, without deleting content — relocate depth to lazy-loaded `references/`, trim always-on catalog text, slim agent prompts.

**Status (2026-09-26, `python3 tools/token-audit.py`, folded from the retired `docs/plans/token-optimization-progress.md`):** live. Budgets: skill `description` ≤ 500 chars · agent `description` ≤ 650 · SKILL.md body ≤ 16,000 · agent file ≤ 14,000. Skill descriptions over budget **0** · agent descriptions **0** (plan 001 cleared the last 45) · SKILL.md bodies **109** · agent files **51** — **160** size violations, all relocation-to-`references/` work. The script exits non-zero until they are gone. Next: its own numbered plan (plan 001, O7).

**Current (2026-07-25) — the two plugins worked so far:**

| Plugin | Skills | Always-on desc | Agents | Status |
|---|---|---|---|---|
| **qa-dotnet** | 91 | **8,982 tok** (was 12,500) | **41,988 tok** (was 45,281) | desc ✅ · 5 of 9 agents ✅ |
| **fe-react** | 50 | **5,786 tok** (was 7,019) | **6,818 tok** (was 9,261) | desc ✅ · agent ✅ |

**Measured baseline (2026-07-16, `python3 tools/token-audit.py`):**

| Plugin | Skills | Always-on desc tokens | Bodies (tok) | Agents (tok) |
|---|---|---|---|---|
| qa-java / qa-dotnet / qa-ts | 84–89 | ~8,000–8,400 | ~260–270k | ~45k |
| fe-react / fe-blazor | 50 / 48 | ~10,000 / ~9,600 | ~143k / ~136k | ~8k |
| be-dotnet / be-java / be-node | 27–31 | ~3,900–4,600 | ~68–78k | ~8k |
| data / business-analysis | 12 / 9 | ~2,200 / ~1,400 | ~39k / ~17k | ~4.5k / ~7k |

Three cost layers: (1) **always-on** — every registered skill's `description` + every agent's description is injected into every session; (2) **per-invocation** — the SKILL.md body; (3) **agent-run compounding** — agent prompt + 2–5 full skills per phase. `references/` are lazy — already correct, don't touch that design.

**Budgets (enforced by the audit script):**
- skill `description` ≤ 500 chars (trigger phrases + one-line fence stay; enumerations move to the body)
- SKILL.md body ≤ 16,000 chars (deep sections → `references/details.md`, per the existing library rule). *Recalibrated from 12K during Phase 2: the library's router-shape skills run 12–16K by design; 16K catches the genuine outliers without churning the healthy middle.*
- agent file ≤ 14,000 chars

---

## Phase 0 — Audit tooling ✅ this session

- [x] `tools/token-audit.py` — per-plugin totals + budget-violation lists (desc>500, body>12KB, agent>14KB). Run: `python3 tools/token-audit.py`.

## Phase 1 — Trim descriptions (always-on tax; biggest leverage) — this session

Rewrite every `description` > 800 chars down to ≤ 500, preserving: (a) the "Use when" sentence, (b) 3–5 quoted trigger phrases, (c) the one-line "Do NOT use → sibling" fence. Cut: enumerated feature lists, multi-sentence scope prose, per-version details (all live in the body).

Batches (59 files — ✅ all done 2026-07-16):
- [x] `design/` (8): ux-review, brand-import, iconography, design:tokens, charts, ux-writing, visual-identity, ui-code-audit
- [x] `frontend/react/skills/` (20): ui-rules, installable-offline-app, animation, error-handling, basics, performance, seo, accessibility, component-testing, component-library, languages, responsive-design, code-review, styling, data-fetching, realtime, component-writer, forms, project-setup, testability
- [x] `frontend/blazor/skills/` (16): basics, installable-offline-app, ui-rules, animation, accessibility, seo, component-testing, languages, javascript-calls, responsive-design, error-handling, styling, data-fetching, performance, component-library, realtime
- [x] `data/` (3): elasticsearch, redis, mongodb
- [x] `qa/*/skills/responsive-testing` (3: dotnet, java, typescript)
- [x] `engineering-practices/` (3): requesting-code-review, spec-vs-code-audit, feature-audit
- [x] misc (6): business-analysis/ba-feature-conflict-check, backend/{dotnet,java}/skills/cognito, auth/_shared/oidc-concepts (extras/xlsx out of plugin scope — skipped)

**Result:** always-on desc tokens — fe-react 10,055→6,426 · fe-blazor 9,597→6,467 (−33%/−36%); qa-* −4%; data −16%. 67 files remain in the 500–800 band (next node).

- [x] **500–800 band (66 files, 2026-07-16):** all trimmed to ≤500 (`frontend/react/vendor/view-transitions` deliberately skipped — vendored upstream, excluded from the audit). Final always-on desc tokens: fe-react 5,953 (−41% vs baseline) · fe-blazor 5,681 (−41%) · qa-java 7,281 / qa-dotnet 7,631 / qa-ts 7,131 (−9%) · be-* 2,979–3,470 (−23%) · data 1,452 (−33%) · business-analysis 1,051 (−26%). Description gate is GREEN.

Then (follow-up node): the 500–800 char band (70 files) — same recipe, lower priority.

- [x] **Agent descriptions (2026-07-16):** all 38 in-scope agents trimmed to ≤650 chars (target relaxed from 600 — agents carry heavier routing weight). Total: 34,707 → 22,386 chars (−36%, ~3.1k tokens off the Agent-tool listing). Stack triples templated for sibling parity (qa-api/ui/mobile/llm/bdd/perf/cicd/reporting ×3, be-*, observability-engineer-*).

**Phase 1 was COMPLETE 2026-07-16 — then regressed.** All three always-on surfaces were trimmed: skill descriptions ≤500, agent descriptions ≤650, vendor files excluded by policy.

### Phase 1 regression + repair (2026-07-25)

The conformance-audit rollout (`2c36d80`) re-inflated descriptions under `CONFORMANCE-AUDIT-PLAN.md`'s **≤1000-char** budget, which contradicted this plan's **≤500**. Damage: qa-dotnet **7,631 → 12,500 tok (+64%)**, fe-react 5,953 → 7,019 (+18%). The single largest cause was a **byte-identical 209-char agent-routing sentence** appended to 45 qa-dotnet descriptions ("For end-to-end suite work prefer the phased agent …") — 9,392 chars / 2,348 tokens, 19% of that plugin's whole always-on budget, carrying zero routing signal because it cannot discriminate between skills.

**Resolved:** ≤500 is now the single library-wide budget; `CONFORMANCE-AUDIT-PLAN.md:221` amended to point here. The recipe, applied to 79 files across the two plugins:
1. cut the repeated agent-routing sentence entirely (the agent's own description already claims end-to-end work);
2. cut `or for non-<stack> projects (use <sibling>)` — those siblings are not registered in a single-plugin install, so the clause can never fire;
3. compress the `Do NOT use` fence to one clause naming **same-plugin** siblings only;
4. keep the Use-when sentence, 3–5 trigger phrases, and one fence.

| | baseline 07-16 | after regression | **now** |
|---|---|---|---|
| qa-dotnet desc | 7,631 | 12,500 | **8,982** (91 skills — 2 more than baseline) |
| fe-react desc | 5,953 | 7,019 | **5,786** |

Both plugins are **green** on descriptions. Untouched: `qa-java`, `qa-typescript`, `fe-blazor`, `be-*`, `data`, `devops` still carry the same regression (~10,900 tok each for the qa siblings) — same recipe applies, one plugin per node.

## Phase 2 — Oversized SKILL.md bodies → `references/details.md` (per-invocation cost)

151 bodies > 12KB. Work worst-first; one stack-triple per node (matches the sibling-parity discipline). Keep in the body: decision matrix, hard rules, core recipe, references-routing table. Move out: per-scenario deep dives, long code listings for secondary paths, appendix-grade tables.

Priority order (top band, >18KB):
- [ ] ai-feature-testing (ts 28.4K, dotnet 23.3K, java 23.0K)
- [ ] mobile-native-features (java 26.0K, ts 24.9K, dotnet 24.7K) + device-cloud (ts 27.2K, dotnet 18.1K, java 17.1K)
- [ ] ui-rules (react 25.7K, blazor 24.7K)
- [ ] realtime-stream-testing (dotnet 24.4K, ts 22.0K, java 21.5K)
- [ ] failure-injection-testing (java 21.6K, ts 21.4K, dotnet 18.8K)
- [ ] api-test-author/grpc (java 21.4K, dotnet 20.1K, ts 19.2K)
- [ ] security-testing/passive-scan ×3 (~21K) + `_shared/security-testing/*` (container-iac 20.3K, sast 19.8K, nuclei 19.3K, zap-af 17.9K, secrets 17.8K, tls 17.1K, api-fuzzing 17.0K)
- [ ] production-uptime-checks ×3 (~20–21K), data-driven-testing ×3 (~18–21K), language-testing ×3 (~18–19K)
- [ ] api-contract-testing (java 22.1K), dependency-scan ×3 (~18–19K), permission-testing (dotnet/java ~18.7K)
- [ ] data/dynamodb 20.6K, data/elasticsearch 19.4K, data/cosmosdb 18.2K
- [ ] frontend reference (blazor 19.1K, react 18.6K), react accessibility 18.7K, react performance 18.1K
- [ ] flaky-test-quarantine (java/dotnet ~18.4K), test-quality-check java 18.6K, qa/manual/{test-case-writer 18.9K, test-design-techniques 18.1K}
- [ ] remaining 12–18KB band (~100 files) — sweep by folder in later nodes

## Phase 3 — Slim agents

**The recipe (validated on 4 agents, 2026-07-25).** In leverage order:
1. **Compress the brownfield block to `.skill-template/agent.md` shape** — it runs 4.1–5.2 KB inlined in every agent and compresses to ~2.0 KB with no loss: keep the orient / Mode A triage fork / Mode B / branch-finish structure and the agent's *distinctive* content (the per-family failure-class fork is the real value), drop the restated preamble and the numbered-list scaffolding. **Biggest single win: 2.0–3.2 KB per agent.**
2. **Declare a path shorthand once, then use bare skill names** — `a bare name is <root>/<name>/SKILL.md; an ep-* name is engineering-practices/<name>/SKILL.md`. Collapsing `[`x`](../skills/x/SKILL.md)` and `` `qa/dotnet/skills/x/SKILL.md` `` to `` `x` `` saves 25–55 chars per mention, ~0.5–1.0 KB per agent.
3. **Compress the skill-loading protocol paragraph** (~1.0 KB → ~0.6 KB) and fold its 4-item numbered list into 3, adding *"where a skill routes to one of several `references/<tool>.md`, read only the one matching the project's tool"* — the one-of-N instruction this phase called for.
4. **Merge the two output-contract blocks** — hoist the shared `Versions/Stack detected` line above both.
5. **Stop restating `CLAUDE.md`'s code rules in full** — the loaded skills carry them; keep only what the agent gates on each phase.

Note: steps 2–5 are worth ~1 KB combined. **If an agent is >3 KB over budget, step 1 alone will not close it** — the phase table's exit gates need real trimming too (keep the decision, drop the enumeration the owning skill already carries).

**Done (2026-07-25):**
- [x] `fe-react` 23,765 → **13,994** (−41%)
- [x] `qa-api-dotnet` 18,323 → **13,922** (−24%)
- [x] `qa-bdd-dotnet` 15,896 → **13,855** (−13%)
- [x] `qa-performance-dotnet` 14,900 → **13,768** (−8%)

**Still over budget (partially compressed — steps 1–5 applied, phase tables not yet trimmed):**
- [ ] `qa-test-case-designer` 22,910 → 22,568 — needs a **38% cut**; a genuine restructure, not squeezing. Its 5.4 KB phases block and 4.1 KB brownfield block both need rewriting
- [ ] `qa-security` 18,967 → 18,514 — needs 24%; the OWASP layer map is the bulk
- [ ] `qa-ui-dotnet` 18,822 → 17,041 — needs 18%
- [ ] `qa-mobile-dotnet` 17,395 → 14,522 — needs 4% (the Appium-MCP operational section is the remaining bulk)
- [ ] `qa-llm-dotnet` 16,447 → 14,325 — needs 2%

**Open question for the owner:** the last two are within 4% of budget and their remaining content is all load-bearing. Either finish the phase-table trim, or recalibrate the agent budget to 15,000 — precedent exists: this plan already recalibrated the SKILL.md body budget 12K → 16K in Phase 2 for exactly this reason ("the library's router-shape skills run 12–16K by design").

- [ ] Remaining out-of-scope agents (same recipe): fe-blazor 20.3K, data-architect 17.6K, business-analyst 17.7K, the qa-java / qa-typescript stack agents (~16–17K each), devops-engineer 14.9K

## Phase 4 — Packaging & install guidance

- [ ] README + marketplace docs: install **one** stack plugin per project; siblings buy nothing and double the shared-skill catalog tax
- [ ] Decision (user call): split `ep-*` (+ code-auditor + requirements-breakdown) into a tiny shared plugin the stack plugins depend on, to kill duplicate registration on multi-plugin installs — currently CLAUDE.md mandates bundling into all eight

## Phase 5 — Verify

- [ ] Re-run `tools/token-audit.py`; all budgets green
- [ ] Spot-check one real agent run (e.g. qa-api-dotnet on a sample project) comparing context consumption before/after
- [ ] Update CLAUDE.md scope note + this plan's baseline table with the new numbers
