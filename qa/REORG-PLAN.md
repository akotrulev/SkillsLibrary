# QA skills reorganization plan

> **Status (2026-06):** Phases 0, 1, 2, and 3A are **implemented** (Phase 1 found nothing left to
> hoist — the duplication lived in the families Phase 3A consolidated). Phase 4 deliberately skipped.
> Results: 62 → 45 registered skills per stack; library-wide description load ~21.9k → ~7.2k words;
> all SKILL.mds ≤ ~420 lines with deep dives in `references/` (`<tool>.md` for families,
> `details.md` for split singles); marketplace regenerated (65 skills + 6 agents per stack plugin)
> and `claude plugin validate .` passing. Revert point: commit 3125862.

Analysis of `qa/java/skills/` (2026-06-11). The three stacks are fully mirrored (identical node
trees and section skeletons), so every change below applies ×3 (java / dotnet / typescript) and the
effort estimates assume that. Each phase is independently shippable — tick what to implement.

## Findings

| # | Finding | Evidence |
|---|---------|----------|
| F1 | **Always-loaded context is heavy.** Frontmatter descriptions total ~4,100 words (≈5.5k tokens) for the 62 java skills alone; a stack plugin registers 82 skills (incl. manual + _shared) → ~7k tokens in every user session before any work starts. Avg description 66 words; worst 246 (`mobile-device-farm`). | `awk '/^description:/'` totals |
| F2 | **No progressive disclosure.** All 62 skills are single monolithic SKILL.md files — zero `references/`, `scripts/`, or `templates/` anywhere. 23 skills exceed 400 lines (worst: `azure-blob` 576, `rabbitmq` 572, `grpc` 570). Best practice is SKILL.md ≤ ~500 lines with deep content split out and loaded on demand. | `find -type f ! -name SKILL.md` → empty |
| F3 | **Family content duplicated per sibling.** Every messaging sibling embeds the same family decision matrix (227–345 words × 4 ≈ 1.2k words duplicated per stack, ×3 stacks; drift risk). Same pattern in email ("Mailpit vs Mailosaur"), api-mocking, network-monitoring. | section word counts |
| F4 | **Top-level sprawl.** 35 top-level nodes, 23 of them single-skill. Related capabilities are scattered: the API workflow spans 3 nodes (`api-dto-writer` → `api-client-writer` → `api-test-author/*`); page objects span 4 (`page-object-architect`, `pom-builder`, `appium-explore`, `appium-page-object`). | `ls` counts |
| F5 | **Three different section schemas.** messaging uses a bespoke skeleton (model → decision matrix → core patterns → anti-patterns → rules); email uses When-to-use/Templates/Generation-steps; ui-test-author uses Stack/Patterns/Handoffs. Agents reading skills phase-by-phase benefit from one predictable skeleton. | heading diffs |
| F6 | **Cross-references are repo paths** (`qa/java/skills/...`) inside bodies and descriptions — they work in-repo and (after the `${CLAUDE_PLUGIN_ROOT}` agent fix) in the plugin cache, but skill-name references (`qa-db-testing-client-java`) would be robust everywhere and enable Skill-tool invocation. | grep |

## Phases

### Phase 0 — Trim frontmatter descriptions  *(recommended — do first)*
- Target ≤ ~55 words each: one "Use when" sentence, 2–3 concrete trigger phrases, compressed routing tail (`Siblings: kafka/sqs/rabbitmq — see body`). Keep the trigger phrases — they drive auto-invocation.
- Impact: cuts the always-loaded plugin context roughly in half (~3k tokens per stack plugin).
- Effort: 1–2 sessions, mechanical, ×3 stacks + manual + _shared. Risk: low (over-trimming weakens triggering — keep concrete verbs/tool names).

### Phase 1 — Hoist duplicated family content  *(recommended)*
- Move each family's decision matrix / sibling-comparison into one `<family>/README.md` (ships in the plugin cache, not registered as a skill); siblings replace their embedded copy with a one-line pointer.
- Families: messaging-testing, email-testing, api-mocking, network-monitoring, visual-regression, db-testing (audit each).
- Impact: ~1–3k words removed per family per stack; single source of truth, no drift. Effort: 1 session.

### Phase 2 — Progressive disclosure for oversized skills  *(recommended)*
- For every SKILL.md > ~350 lines: keep workflow, rules, and core patterns in SKILL.md; move Examples, API cheat-sheets, and full code templates to `references/examples.md` / `references/cheatsheet.md`, linked with "read when you need X".
- 23 skills per stack qualify. Orthogonal to Phase 3 — apply to whatever stays unconsolidated.
- Impact: faster skill loads, bodies stay under the recommended size. Effort: 2–3 sessions.

### Phase 3 — Consolidate one-of-N tool families  *(decision required)*
A project uses exactly one broker, one email sink, one mock server, one CI system — the sibling
skills are variants, not complements.

- **Option A (recommended): family → one registered skill + `references/<tool>.md`.**
  Candidates: messaging (4→1), email (4→1), api-mocking (4→1), network-monitoring (3→1),
  ci-pipelines (3→1), visual-regression (3→1), accessibility (2→1), file-storage (2→1).
  **62 → 41 registered skills per stack** (−34% description load on top of Phase 0). The family
  description names every tool so "kafka" still triggers it; SKILL.md holds the decision matrix +
  shared patterns; the chosen tool's reference loads on demand.
  Keep per-tool: `api-test-author/*` and `ui-test-author/*` (primary authoring surfaces — keep
  trigger precision), `db-testing/*` (client/testcontainers/query-author are different concerns,
  not tool variants), `security-testing/*` (different gates).
- **Option B: keep all 62 registered skills**, rely on Phases 0–2 only. Zero churn, weaker context win.
- Tradeoffs of A: one description covers all variants (slightly less precise routing); `/plugin` skill
  list is shorter but less self-documenting. Effort: 3–4 sessions (8 families ×3 stacks).
- Follow-up for A: regenerate `.claude-plugin/marketplace.json`, update agents' phase tables,
  CLAUDE.md catalog, README.

### Phase 4 — Top-level domain regrouping  *(suggest: defer)*
- Collapse 35 nodes into ~7 domains: `api/` (dto, client, test-author, mocking, contract),
  `ui/` (test-author, page-object-architect, pom-builder, visual, accessibility),
  `mobile/` (appium-explore, appium-page-object, device-farm, native-features),
  `verification/` (db, messaging, email, file-storage, websocket, network),
  `infra/` (test-environments, ci-pipelines, cloud-grid, auth0, allure),
  `quality/` (i18n, llm-app, chaos, feature-flag, flaky, synthetic, data-driven), `performance/`.
- Purely ergonomic; touches every path in agents, CLAUDE.md, marketplace.json, and all
  cross-references, ×3 stacks. Phase 3 already removes most sprawl. Effort: 2–3 sessions, highest
  regression risk for lowest functional gain.

### Phase 5 — Normalize schema & cross-references  *(fold into whichever phases run)*
- One canonical SKILL.md skeleton (align with `.skill-template/`): When to use / When NOT /
  Stack / Inputs / Core patterns / Rules / Anti-patterns / Generation steps / Cross-references.
- Convert cross-references from repo paths to skill names (`qa-db-testing-client-java`), optionally
  dual-form with the path in parentheses. Plugin-safe and Skill-tool invocable.
- Do opportunistically while files are open in Phases 0–3; not a separate pass.

## Execution notes

- Mirror every change java → dotnet → typescript in the same session (one family/node per session,
  per the established handoff loop), then update `qa/GAP-ANALYSIS.md` / `qa/HANDOFF.md`.
- After structural changes: regenerate marketplace.json, run `claude plugin validate .`, and spot-check
  one agent's phase table for dead paths.
- Suggested order: **0 → 1 → 3(A) → 2 (remainder) → 5 folded in; skip 4.**
