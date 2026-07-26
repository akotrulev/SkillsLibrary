# frontend/ audit — findings & plan of action

**Date:** 2026-07-12
**Scope audited:** `frontend/blazor/` (22 skills + `fe-blazor` agent), `frontend/react/` (21 skills + `fe-react` agent + 3 vendored seeds), `frontend/react-native/` (under construction), plus the `fe-blazor`/`fe-react` marketplace wiring.
**Method:** structural + wiring checks inline; one deep read-only audit per shipped stack (frontmatter, cross-references, agent↔skills contract, version-awareness, size, consistency).

---

## Overall assessment

Both shipped stacks are in **very good shape** — no blockers, zero dead cross-references found across a wide spot-check, airtight agent↔skills contracts (all skills loaded by their agent, no orphans, 6-phase structure matches CLAUDE.md including the design-critique loop and visual self-critique), uniform version-awareness (net10/net8-9 and React 19/18 fallbacks correctly tagged; reviewers explicitly forbid flagging down-level projects), and consistent cross-skill rules (data-testid convention, severity tables, dark-mode/token ownership, MUI/never-Tailwind-atop-MUI).

The issues found are concentrated in four areas: **(1)** skill descriptions at or over the 1024-char hard limit, **(2)** leftover authoring artifacts shipping inside the `fe-blazor` plugin (one leaking a real client project name), **(3)** the three vendored Vercel seeds registering as independently-routable skills whose triggers shadow the curated house skills, and **(4)** small parity/metadata gaps.

---

## Findings

| # | Severity | Location | Issue | Suggested fix |
|---|----------|----------|-------|---------------|
| F1 | major | `blazor/skills/reference/SKILL.md` | Description is **1034 chars** — over the 1024-char hard limit on skill descriptions; risks truncation/rejection by the loader | Trim ≥ 34 chars (drop one redundant trigger phrase) |
| F2 | major | `blazor/skills/testability/SOURCE.md`, `blazor/skills/ui-rules/SOURCE.md` | Consumed seed material ("SEED MATERIAL — do not register as a skill") ships inside the published MIT `fe-blazor` plugin; `test-ids/SOURCE.md` **leaks a real client project name** (`FlexInvest.AdminService.API`, internal paths, REFLEX framework) and contains a stray frontmatter fragment; both reference a `frontend/PLAN.md` that no longer exists | Remove from the shippable tree (archive outside the repo or delete — content is fully absorbed into the SKILL.md files) |
| F3 | major | `blazor/DESIGN-GAP-ANALYSIS.md` | Stale working artifact (2026-07-11): says "17 skills" (now 22) and "agent not yet built" (it exists); referenced by nothing | Delete |
| F4 | major | `react/vendor/{reference,composition-patterns,view-transitions}/SKILL.md` | The three Vercel seeds ship as **independently-routable plugin skills** (`vercel-*` names, trigger-bearing descriptions, no "Do NOT use" routing). Their triggers shadow the curated house skills: `vercel-react-best-practices` ↔ `fe-react-performance`; `vercel-react-view-transitions` ↔ `fe-react-animation`; `vercel-composition-patterns` ↔ `fe-react-basics`/`component-writer`. A raw request can route straight to the seed and bypass the house version-policy/curation layer | Decide: (a) stop registering them as skills (drop from the `fe-react` plugin `skills` array; house skills keep pointing into their files), or (b) add an explicit "Do NOT use directly — load via `fe-react-{performance,motion,reference}`; deep-dive seed" clause to each vendor description. **(b) is the lighter, recommended fix** — keeps them discoverable for deep dives while preserving routing discipline |
| F5 | minor | ~16 descriptions across both stacks | Descriptions sit at or within ~3% of the 1024 cap — fragile against any edit. Blazor: `ui-rules` + `languages` (exactly 1024), `styling` 1020, `accessibility` 1014, `seo` 1012, `error-handling` 1005, `animation`/`installable-offline-app`/`component-testing`/`javascript-calls`/`responsive-design` 970–995. React: `animation` 1022, `ui-rules` 1022, `error-handling` 1021, `installable-offline-app` 1020, `seo` 1014, `component-testing` 1011, `styling` 1010, `accessibility` 1006, `responsive-design` 1002 (rest &lt; 1000) | One editing pass trimming every frontend description to **≤ 1000 chars** for headroom |
| F6 | minor | `react/skills/generator/SKILL.md` | Owns compound-component + container/presentation recipes but doesn't point at the `vendor/composition-patterns` deep-dive seed (sibling `basics` does, at its L125) | Add the "deep treatment → `frontend/react/vendor/composition-patterns`" pointer in those two sections |
| F7 | minor | `react/skills/testability/` | No `references/` at all — blazor's counterpart has `references/static-html.md` (hybrid/static-HTML surfaces). Real parity delta beyond the documented `javascript-calls` drop; plausibly intentional | Either add a short hybrid/static-surface note or state in-skill that non-React surfaces are out of scope |
| F8 | minor | `react/vendor/composition-patterns/metadata.json` | `"organization": "Engineering"` vs siblings' `"Vercel Engineering"` | Normalize to `"Vercel Engineering"` |
| F9 | nit | `react/vendor/*/README.md`, `react/vendor/*/AGENTS.md` | Standalone-repo scaffolding ("maintaining this repo") ships in the plugin bundle — dead weight for consumers; `metadata.json` alone carries provenance | Optionally strip `README.md`/`AGENTS.md` from the bundled copies |
| F10 | info | `frontend/react-native/` | Raw, unadapted Vercel import (`name: vercel-react-native-skills`, upstream `rules/`/`AGENTS.md`/`metadata.json` layout). Correctly fenced: under construction per CLAUDE.md and **not** referenced by any plugin. No action required now — captured as the future work item below | See Phase 5 |

**Verified clean (no action):** frontmatter names all match folders with full Triggers + Do-NOT routing (43/43 house skills); all spot-checked cross-references resolve (design/*, auth/*, qa/* peers, ep-* bundle paths, intra-domain links, references/ files); both agents brownfield-compliant (`Mode: FIX | EXTEND`, orientation pass, minimal-change rule) per `.skill-template/agent.md`; version policies correctly applied (incl. `forwardRef`-only-a-finding-on-19, `useActionState` vs `useFormState`, net10 `NotFoundPage`/`[PersistentState]`/`ReconnectModal` with down-level fallbacks); no SKILL.md over 500 lines; vendor skill names don't collide; marketplace `skills`/`agents` arrays for `fe-blazor`/`fe-react` all resolve on disk.

---

## Plan of action

Run phases in order; each is independently committable. Phases 1–3 are quick hygiene (≈ one short session together); Phase 4 is small content work; Phase 5 is a future multi-session effort with its own gate.

### Phase 1 — remove shipping artifacts (F2, F3)
- [ ] Delete `frontend/blazor/DESIGN-GAP-ANALYSIS.md` (stale, unreferenced)
- [ ] Delete `frontend/blazor/skills/test-ids/SOURCE.md` and `frontend/blazor/skills/ui-rules/SOURCE.md` (consumed seeds; the testability one leaks the FlexInvest client name into the published plugin — if the seeds must be kept, move them outside the repo, not just outside `skills/`)
- [ ] Grep the repo for any remaining `FlexInvest` / client-specific strings under shipped folders: `grep -ri flexinvest --include='*.md' .`

### Phase 2 — description-length pass (F1, F5)
- [ ] Fix `fe-blazor-basics` first (1034 chars — the only one confirmed over the limit)
- [ ] Trim every frontend skill description listed in F5 to ≤ 1000 chars: cut redundant trigger phrasings first, never the Do-NOT routing targets
- [ ] Re-run the length check over `frontend/**/SKILL.md` (fold whitespace, count chars) and confirm all ≤ 1000
- [ ] Optional: extend the same check to the other domains (qa/, backend/, data/, …) — likely the same authoring style produced the same crowding there

### Phase 3 — vendor-seed routing discipline (F4, F8, F9)
- [ ] **Decision (recommended: option b):** keep the three `vercel-*` seeds registered but append to each description: "Do NOT use directly — load via `frontend/react/skills/{performance | motion | reference}`; this is the deep-dive seed those skills route into." (If instead choosing option a, remove the three `./frontend/react/vendor/*` entries from `fe-react`'s `skills` array in `.claude-plugin/marketplace.json` — the house skills reference the files by path, which still resolves in-bundle)
- [ ] Fix `vendor/composition-patterns/metadata.json` organization → `"Vercel Engineering"`
- [ ] Optional: strip `README.md` + `AGENTS.md` from the three vendor dirs (keep `SKILL.md`, `rules/`/`references/`, `metadata.json` for provenance)
- [ ] Note: whichever option is chosen, keep the upstream-import provenance line in `fe-react.md` (agent line 20) accurate

### Phase 4 — small content/parity fixes (F6, F7)
- [ ] `react/skills/generator/SKILL.md`: add the `vendor/composition-patterns` deep-dive pointer in the compound-component and container/presentation sections (mirror `basics` L125's phrasing)
- [ ] `react/skills/testability/SKILL.md`: add either a short "hybrid/static-HTML surfaces" appendix (rows-by-index rule, hardcoded parent locator consts — mirror blazor's `references/static-html.md`) **or** an explicit out-of-scope statement; the current silence is the only unexplained blazor↔react delta

### Phase 5 — react-native adaptation (F10 — IN PROGRESS, multi-session; tracked in `frontend/react-native/PLAN.md`)
- [x] **Decision (2026-07-12):** adapt the Vercel rules into a proper **`fe-react-native` stack** (agent + `fe-react-native-*` skills), mirroring the react port pattern — one node per session, `HANDOFF.md` between sessions. Build plan + node breakdown live in `frontend/react-native/PLAN.md`.
- [x] Node 0 (groundwork): restructured the raw Vercel import into `frontend/react-native/vendor/react-native-guidelines/` (fenced seed — "Do NOT use directly" clause, `organization → "Vercel Engineering"`, this closes the F8 parity + F10 fencing items for RN).
- [x] Node 1 (foundations A): `basics` + `project-setup` skills authored (Expo SDK 56 / New-Architecture version policy locked).
- [ ] Nodes 2–7: remaining skills, phased `fe-react-native` agent, marketplace + CLAUDE.md wiring, verification — see `frontend/react-native/PLAN.md`.
- [ ] Until Node 7: stays **unregistered** (no plugin references it) and listed as under-construction in CLAUDE.md's scope fence.
- [ ] When built (Node 7): update CLAUDE.md scope + catalog, marketplace.json, and the new-project-setup line.

### Verification (after Phases 1–4)
- [ ] `python3` length check: all frontend descriptions ≤ 1000 chars
- [ ] `grep -ri flexinvest .` → no hits in shipped folders
- [ ] Marketplace paths still resolve: every `skills`/`agents` entry for `fe-blazor`/`fe-react` exists on disk
- [ ] `git status` clean of authoring artifacts under `frontend/`
- [ ] Spot-reinstall (or dry-run validate) the two plugins if the vendor-seed registration changed
