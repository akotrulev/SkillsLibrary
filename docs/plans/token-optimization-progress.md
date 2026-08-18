# Token-optimization run — progress & handoff

**Last updated:** 2026-08-18. Source of truth for all counts: `python3 tools/token-audit.py`.
Nothing is committed — all changes are unstaged in the working tree (`git diff` / `git checkout` to review or revert).

Governing plan: `TOKEN-OPTIMIZATION-PLAN.md`. Budgets (enforced by the audit script, which exits non-zero on any violation):
skill `description` ≤ 500 chars · SKILL.md body ≤ 16,000 chars · agent `description` ≤ 650 chars · agent file ≤ 14,000 chars.

## Current audit state

| Category | Violations | Status |
|---|---|---|
| Skill descriptions > 500 | **0** | ✅ DONE (was 127) |
| Agent descriptions > 650 | **0** | ✅ DONE (was 16) |
| Agent files > 14,000 | **41** | 🟡 partial (was 45) |
| SKILL.md bodies > 16,000 | **104** | ⬜ not started |

## What was done this session

1. **`tools/token-audit.py` fixed/improved** (committed to working tree):
   - Added the **agent-description budget check** (≤650) — previously the script was blind to agent descriptions entirely.
   - Agent size now measured in **decoded chars**, not bytes (was overcounting multibyte glyphs · → ≤ ✅).
   - Each violation line names its **owning plugin**; added a "Violations by plugin" rollup.
   - Exits non-zero on any violation → usable as a CI / pre-commit gate.

2. **Wave 1 — Phase 1 descriptions: COMPLETE & audit-verified.**
   - 127 skill descriptions trimmed to ≤500, 16 agent descriptions to ≤650.
   - Recipe: preserved the "Use when" opener + 3–5 quoted trigger phrases + same-plugin "Do NOT use → sibling" fence; cut enumerated feature lists, scope prose, cross-plugin fence clauses, and the generic phased-agent routing sentence. Only frontmatter `description:` touched.
   - **Low-risk — safe to commit on its own** before any riskier work.

3. **Wave 2 — Phase 3 agent files: STARTED, then stopped mid-flight (user request).**
   - 9 subagents were applying the plan's Phase-3 recipe to all 45 over-budget agents. Killed partway → **4 reached budget (45→41)**; several files are in a **partially-slimmed, UNVERIFIED** state.
   - ⚠️ These partial edits have NOT been checked for lost phases/gates. **Review `git diff -- '**/agents/*.md'` before trusting or committing them.**
   - The qa-reporting triple was reported fully under 14K by its subagent; qa-test-case-designer was mid-restructure (hardest file).

## Agent files still > 14,000 (41 — worst first)

```
28971  backend/_shared/agents/be-planner.md
26920  devops/agents/devops-engineer.md
22610  qa/java/agents/qa-api-java.md
22507  devops/agents/infra-security-tester.md
22461  qa/typescript/agents/qa-api-typescript.md
21895  security/agents/penetration-tester.md
21641  backend/_shared/agents/be-documenter.md
21620  qa/_shared/agents/qa-security.md
21558  data/agents/data-architect.md
21441  qa/typescript/agents/qa-mobile-typescript.md
21321  qa/java/agents/qa-mobile-java.md
20769  business-analysis/agents/business-analyst.md
20673  qa/typescript/agents/qa-bdd-typescript.md
20511  qa/typescript/agents/qa-ui-typescript.md
20443  qa/java/agents/qa-ui-java.md
19769  qa/manual/agents/qa-test-case-designer.md
19706  qa/java/agents/qa-llm-java.md
19597  qa/typescript/agents/qa-llm-typescript.md
19503  qa/java/agents/qa-bdd-java.md
19240  backend/java/agents/be-java.md
18888  frontend/react/agents/fe-react.md
18690  backend/node/agents/be-node.md
18028  devops/agents/devops-auditor.md
17880  qa/typescript/agents/qa-performance-typescript.md
17454  qa/dotnet/agents/qa-ui-dotnet.md
17236  qa/dotnet/agents/qa-llm-dotnet.md
16991  qa/dotnet/agents/qa-performance-dotnet.md
16939  qa/manual/agents/qa-test-planner.md
16885  observability/agents/observability-engineer-node.md
16619  qa/dotnet/agents/qa-mobile-dotnet.md
16295  observability/agents/observability-engineer-dotnet.md
16274  qa/cicd/agents/qa-cicd-typescript.md
16200  qa/dotnet/agents/qa-api-dotnet.md
16123  qa/cicd/agents/qa-cicd-java.md
16094  training-data/agents/dataset-engineer.md
16011  qa/cicd/agents/qa-cicd-dotnet.md
15889  frontend/blazor/agents/fe-blazor.md
14612  backend/dotnet/agents/be-dotnet.md
14215  qa/dotnet/agents/qa-bdd-dotnet.md
14115  observability/agents/observability-engineer-java.md
14072  qa/java/agents/qa-performance-java.md
```

## Phase-3 recipe (validated — for finishing Wave 2)

Shape models: `.skill-template/agent.md` (brownfield-block shape), `business-analysis/agents/requirements-author.md` (green ~11.6K), `security/agents/security-test-planner.md` (green ~12.7K).

1. Compress the **brownfield/orientation block** to `.skill-template/agent.md` shape (~2 KB) — keep orient → Mode A triage fork → Mode B → branch-finish + the agent's distinctive per-family fork; drop restated preamble + numbered scaffolding. **Biggest win (2–3 KB).**
2. Declare a **path shorthand once**, then bare skill names instead of full markdown links/paths.
3. Compress the **skill-loading protocol** paragraph to 3 items + the one-of-N "read only the matching `references/<tool>.md`" note.
4. Merge duplicate **output-contract** blocks.
5. Stop restating **CLAUDE.md code rules** in full — loaded skills carry them.
6. If still over: trim **phase-table exit gates** — keep the decision, drop enumerations the owning skill carries.

Never drop a phase, gate, decision rule, skill-loading instruction, or fence. On security agents (penetration-tester, infra-security-tester, devops-*) never weaken the authorization/scope-file gate. Edit stack-triples identically for parity. Don't touch frontmatter `description`/`name`/`tools`/`model`.

## Most impactful remaining work

1. **Verify the partial Wave-2 agent edits** (`git diff -- '**/agents/*.md'`) for lost behavioral content, then finish the 41 remaining agents with the recipe above. Several (be-planner 29K, devops-engineer 27K, qa-api/qa-mobile/qa-ui/qa-bdd/qa-llm triples ~20–22K) likely can't reach 14K without cutting load-bearing content → **decide the 15,000 agent-budget recalibration the plan already raised as an open question** (`TOKEN-OPTIMIZATION-PLAN.md:117`).
2. **Wave 3 — 104 SKILL.md bodies > 16K:** relocate deep sections into lazy-loaded `references/`, keeping decision matrix + hard rules + core recipe + routing table in the body; verify each still routes correctly. Largest and riskiest wave, not started.
3. **Commit Wave 1 (descriptions) separately now** — it's audit-verified and low-risk — before the riskier agent/body work lands.

## Notes / gotchas

- The plan's own status tables (`TOKEN-OPTIMIZATION-PLAN.md`) are **stale** — they predate the orientation-cache, code-comments, unit-testing, planner/MC, and 3 security-expansion rollouts, and don't mention the `training-data` plugin (13th) at all. Update its baseline table when done.
- Some backend descriptions trip strict PyYAML (`mapping values not allowed`, colon-space in plain scalars) — this is **pre-existing** (unchanged from HEAD); the harness uses a lenient parser. Not a regression.
- Recurring failure mode this plan keeps hitting: completed trims get **re-inflated** by later feature rollouts (Phase 1 regressed once already; Phase 3's earlier slimming was fully reverted). The durable fix is wiring `tools/token-audit.py` into CI as a gate — it already exits non-zero on violations.
