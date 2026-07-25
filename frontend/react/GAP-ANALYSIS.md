# `frontend/react/` — Gap Analysis

**Date:** 2026-07-24
**Scope audited:** `frontend/react/agents/fe-react.md`, all 21 `frontend/react/skills/*/SKILL.md`, the 3 vendored `frontend/react/vendor/*/SKILL.md`, the `fe-react` entry in `.claude-plugin/marketplace.json`, and the bundled `auth/auth0-react` + `design/*` skills — compared against `fe-blazor` as the reference port source.
**Driving question:** why is the `fe-react` agent not invoked when the plugin is installed, and are the skills' trigger words good enough to fire?

---

## A. Why the agent doesn't fire — structural, not lexical

The `fe-react` agent description is well-formed. It carries persona + scope + five quoted trigger phrases + a `Do NOT use` fence, the same shape as the `qa-*` agents that do get selected. **Rewording it will not fix invocation**, because the cause is structural:

1. **The harness suppresses auto-delegation.** The current Agent-tool contract states *"Do not spawn agents unless the user asks… Only use this tool when the user explicitly says to use a subagent, or names one of the available agent types."* No description wording overcomes that policy. In practice the agent fires when the user types `fe-react`, and essentially not otherwise.
2. **No plugin in this library ships a `commands/` directory.** All 10 marketplace plugins were checked; none declares a `commands` key. There is no `/fe-react` entry point, so the only deterministic invocation path is the user remembering the agent's name.
3. **Consequence:** the *skills* are the real trigger surface, and the agent's pipeline — phase exit gates, the design-critique loop, the brownfield orientation pass — is unreachable from a plain prompt. Nothing in the 21 skills signals that an orchestrator owns the workflow.

---

## B. Skill trigger problems

| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker | `vendor/{reference,composition-patterns,view-transitions}` | All three are registered as first-class plugin skills, yet their own descriptions say *"Do NOT use directly."* Their triggers are **broader** than the house skills they shadow. `vercel-react-best-practices`: *"writing, reviewing, or refactoring React/Next.js code… React components, Next.js pages, data fetching, bundle optimization"* — outranks `fe-react-performance`, `-reviewer`, `-generator` and `-data-access` at once. `vercel-react-view-transitions` (776 chars, the longest description in the plugin) claims *"animate enter/exit of components, animate list reorder"* — the exact triggers `fe-react-motion` lists. | Remove all three from the `fe-react` `skills:` array in `marketplace.json`. They stay reachable as files — `reviewer`, `motion`, `generator`, `performance` and `reference` already link them by path. `fe-blazor` has no vendor entries; this is a port artifact. |
| major | bundled `design/*` skills | Nine skills enter the global skill namespace **unprefixed**: `dataviz`, `frontend-design`, `design-tokens`, `theme-factory`, `ux-writing`, `web-design-guidelines`, `brand-intake`, `iconography`, `ux-heuristics`. At least two collide with skills already present in a typical environment (`frontend-design`, `dataviz` ship independently). A React plugin should not claim the bare name `dataviz`. | Prefix to `design-*` (`design-dataviz`, `design-frontend-design`, …), consistent with the existing `fe-react-*` / `ep-*` / `auth-*` prefixing. Affects `fe-blazor` too — both plugins bundle the same 9. |
| major | `auth/auth0-react/SKILL.md` | The plugin's primary lane is Next.js App Router, but this skill is **React 18 + SPA** and defers App Router four separate times to `@auth0/nextjs-auth0` — **which it never documents**. Its description never says "Next.js", so *"add login to our Next app"* matches weakly; when it does match, it delivers a pointer rather than a recipe. | Add an App Router lane (`@auth0/nextjs-auth0` middleware, `auth0.getSession()` in RSC, Server Action auth) or split out `auth/auth0-nextjs`. Update the description to React 19/18 and name Next.js. |
| minor | all 21 house skills | 20 of 21 descriptions gate the lead clause on the literal word "React" (*"Use when making a React app…"*). The `Triggers:` clauses are symptom-based and good — the lead sentence is the weaker half. | Lead with the symptom/artifact and qualify with the stack: *"Use when a data region shows blank on API failure — React/Next…"* |
| minor | all 21 house skills | **Zero verbatim React/Next error strings** anywhere in the folder — not in descriptions, not in bodies. Grepped for `Hydration failed`, `Text content does not match`, `Maximum update depth exceeded`, `You're importing a component that needs useState`, `Event handlers cannot be passed to Client Component props`, `Rendered more hooks than during the previous render`, `Each child in a list should have a unique "key"` → **0 hits each**. Pasting a stack trace is the most common brownfield opening move, and nothing matches it. | Seed the 2–3 canonical error strings into the descriptions of `reference`, `reviewer`, `performance`, `data-access`. |

### Measurements

- Description lengths: house skills 454–500 chars (consistent, well within limits); vendored `view-transitions` 776.
- Keyword coverage across the 21 house descriptions: `Next.js` 4/21 · `App Router` 4/21 · `TypeScript` 3/21 · `.tsx` 2/21 · `hydrat*` 3/21 · `use client` 4/21 · `RSC` 3/21 · `Vite` 5/21 · `MUI` 3/21 · `pnpm`/`npm` 0/21.
- `React` within the first 10 words: 20/21.

---

## C. Content gaps

### C1. No routing / navigation skill — the biggest port artifact

Blazor routing is `@page`, so the Blazor skill list had nothing to port. In Next.js, App Router routing is a whole domain. Current coverage is scattered and thin:

- `route group` → **0 files**
- `template.tsx` → **0 files**
- `parallel route`, `intercepting` → 1 passing mention each, in `ui-conventions`
- `middleware` → 2 incidental mentions (`localization`, `state-management`)

Nothing owns nested layouts, `generateStaticParams`, `redirect()` / `notFound()`, route handlers as an API surface, or the `useRouter` / `usePathname` / `useSearchParams` triad. Prompts like *"add a modal route"*, *"why does my layout remount on navigation"*, *"protect these routes with middleware"* hit nothing.

### C2. No migration / upgrade skill

`upgrade` → 0 files. `codemod` → 0 files. Missing: React 18→19, **Next 14→15 async `params`/`searchParams`** (a breaking change users will hit), Pages Router → App Router. The version policy names React 18 a "tagged fallback", but nothing owns getting from 18 to 19.

### C3. Correctly handled (not gaps)

`js-interop` was rightly dropped (React has no interop barrier) and `localization` rightly added. The port was not mechanical — C1 and C2 are the remaining holes.

---

## D. Remediation — **all six items implemented 2026-07-24**

| # | Fix | Status | What landed |
|---|-----|--------|-------------|
| 1 | Un-register the 3 vendor skills | ✅ | `fe-react` skills 50 → 47; `vendor/{reference,composition-patterns,view-transitions}` still ship as files and stay reachable by path from `reviewer`/`motion`/`generator`/`performance`/`reference` |
| 2 | Prefix the 9 `design/*` skills | ✅ | `design-brand-intake` · `design-dataviz` · `design-frontend-design` · `design-iconography` · `design-theme-factory` · `design-tokens` · `design-ux-heuristics` · `design-ux-writing` · `design-web-guidelines`. Folder names unchanged (marketplace paths intact); two stutter names avoided (`design-tokens`, not `design-design-tokens`) |
| 3 | `/fe-react` command entry point | ✅ | `frontend/react/commands/fe-react.md` + `commands` key on the plugin. Loads the agent definition and runs the phased workflow **inline** — no subagent spawn |
| 4 | `fe-react-routing` | ✅ | New skill: file conventions, `layout` vs `template`, route groups + private folders, dynamic/catch-all segments, parallel `@slot` + intercepting `(.)` modal routes, `middleware.ts`, route handlers, React Router 7 lane, 12-row anti-pattern table |
| 5 | Symptom-first description leads + error strings | ✅ | All 21 rewritten (~500–690 chars). Verbatim error strings seeded: `reference` (Hydration failed…, You're importing a component that needs useState, Event handlers cannot be passed…), `reviewer` (Rendered more hooks…, Each child in a list should have a unique key prop), `performance` (Maximum update depth exceeded), `data-access` (Dynamic server usage…), plus 17 more symptom triggers |
| 6 | `fe-react-migration` + App-Router auth | ✅ | New migration skill (React 18→19, Next 14→15 async request APIs + flipped caching defaults, Pages→App Router). `auth/auth0-react` grew a real `@auth0/nextjs-auth0` lane (~125 lines: middleware, `auth0.getSession()` in RSC, route protection, server-side token forwarding, 6-row anti-pattern table) and a lane-selection table at the top |

**Also updated:** `frontend/react/agents/fe-react.md` (routing in Phase 1 + 2 and their exit gates, migration named in the version-detection rule, route topology in the brownfield orientation pass), `CLAUDE.md` (23-skill catalog, `design-*` prefix rationale, two-lane auth, `/fe-react` command, vendored-seeds note), and the `fe-react` plugin description.

**Verified:** marketplace JSON parses; all 49 registered skill paths + 1 command + 2 agents resolve on disk; 23 skill folders present; no stale bare-name `design/*` references left in any description.

---

## E. Notes for whoever picks this up

- The house skills' **bodies** are not the problem — sizes are healthy (104–362 lines, 4,638 total) and the agent's phase table, brownfield modes, and output contract are complete and consistent with `.skill-template/agent.md`.
- The `fe-blazor` plugin is the control: same 21-skill shape, same description discipline, **no vendor registrations**, so the vendor collision (B, blocker) is unique to React.
- Fixes 1, 2, 3 and 5 all touch shared files (`marketplace.json`, `CLAUDE.md`, cross-references across domains) and should be applied serially, not fanned out.
