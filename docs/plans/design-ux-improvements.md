# Design plugin — UX improvement plan

**Goal:** apps built by `fe-react` / `fe-blazor` come out looking modern, easy to use, and easy to navigate — by default, not only when a reviewer catches it afterwards.

**Date:** 2026-08-27 · **Status:** T1–T8 executed 2026-08-27 (uncommitted in the working tree)

## What the design layer covers today

| Skill | Altitude | Fires at | Verdict |
|---|---|---|---|
| `design/ux-review` | experience — Nielsen, flow friction, IA | Step 5 (after build) | solid, but review-only |
| `design/ux-writing` | words / voice | Step 2 | solid |
| `design/ui-code-audit` | code — vendored Vercel ruleset | Step 5 | solid; one house conflict (below) |
| `design/visual-identity` | taste — palette, type, layout, motion | Step 1 | biased to marketing/landing pages |
| `design/design-tokens` | token structure | Step 1 | solid |
| `design/theme-presets` · `brand-import` · `charts` · `iconography` | values / assets | Step 1 | fine as-is |
| stack `ui-rules` (React + Blazor) | data-driven **correctness** + IA + nav + modal-vs-route | Step 2 | the best UX content in the repo, but framed as defect classes, not as "how the app should feel" |

## Findings

### Gaps

1. **No generative UX-pattern skill.** Everything UX-shaped is either *review* (`ux-review`, Step 5) or *correctness* (`ui-rules`). Nothing tells the agent, while it is designing the app in Step 1, how to shape the app shell and the pages: sidebar vs top nav vs both, page-header anatomy (title · breadcrumb · primary action), list→detail layout, dashboard composition, form layout, density, global search, command palette / keyboard shortcuts, notification surface, first-run onboarding, progressive disclosure. `sidebar` appears only as a reflow mechanic in `responsive-design`; `command palette` / `keyboard shortcut` / `focus restore` / `perceived performance` have **zero** hits across `design/` and both frontend stacks.
2. **IA is designed by nobody.** The Step-1 decision record has "route topology" but no user-task inventory driving it. `ux-review` then measures nav depth, label predictability and steps-to-goal — *after* the routes exist. The review finds the problem the plan should have prevented.
3. **`visual-identity` is the wrong brief for a system.** Its principles are "the hero is a thesis", "signature element", "asymmetry, overlap, diagonal flow", "take one real aesthetic risk", gradient meshes and custom cursors. For a landing page that is right; for a grid-and-forms application it pushes toward a poster. The skill never mentions dashboard, admin, product, or application UI, and nothing in the repo codifies what makes an *app* look modern (neutral surface scale, one accent, tonal text hierarchy, hairline borders over heavy shadows, 4/8-px rhythm, one radius scale, restrained elevation, a single icon family, dark mode as a first-class surface set).
4. **Perceived responsiveness is scattered, not owned.** Skeleton-vs-spinner lives in `error-handling`, optimistic updates in `data-fetching`/`forms`, hover/press micro-interactions in `animation`. No single place states the feedback budget (instant acknowledgement on press · skeleton within the first second · "still loading…" at ~4 s · no layout shift on load · optimistic where reversible) as a UX requirement the build must meet.
5. **`ux-review` has no capture procedure.** It reviews "a built UI, screenshot, mockup" but the agent's Step 5 is the only place that says *how* (Playwright MCP screenshot). Running the review from the command alone leaves the evaluator without evidence.

### Logical conflicts

6. **Title Case vs sentence case.** The vendored Vercel ruleset (`ui-code-audit/references/guidelines.md` → *Content & Copy*) mandates "Title Case for headings/buttons (Chicago style)"; `ux-writing` §5 mandates "sentence case (not Title Case)". Both load on the same build (Step 2 and Step 5), so the audit will flag exactly the labels the writing skill produced. The house rule (sentence case) needs to override the vendored section explicitly.

### Planning gaps (system design — fe + be + db)

7. **The system planner has no experience artifact.** `be-planner` is the whole-system planner in practice — its routing map binds `fe-react` / `fe-blazor`, `data-architect`, `devops-engineer`, `qa-*` — but its pack is `blueprint → data-model → api-surface → integrations → delivery-plan`. Nothing in it says who uses the system, what they do, which screens exist, how they are navigated, or which endpoint each screen consumes. Frontend tasks therefore reach the `fe-*` agent with flows and endpoints but no user tasks, journeys, screen map or IA — and the fe agent designs the experience alone, per task, disconnected from the approved blueprint.
8. **The approval gate never covers the experience.** The human approves functional areas, architecture, stack and routing (`blueprint.md` §1–§11) without seeing actors, their primary tasks, or the app shell. UX is the one dimension of the system the stakeholder can judge unaided, and it is the one the gate omits.
9. **Step-7 self-review cannot see UI gaps.** Coverage checks areas↔tasks, endpoints↔model, names, dependencies. It cannot catch a user-facing endpoint no screen reaches, or a screen whose data no endpoint provides — the two defects a screen↔endpoint matrix would make mechanical.
10. **The planner's skill fence blocks the fix by accident.** `be-planner` never loads `fe-*` skills (correct — it must not author frontend code), but the `design/` layer is stack-agnostic discipline, exactly like the `ba-*` modelling skills it already loads. The fence needs one named exception, not a hole.

## Plan

**T1 — `design/ux-patterns` exists.**
Deliverable: a new skill `design-ux-patterns` (with `design/commands/design-ux-patterns.md`) that, given a task inventory, produces the app-shell and page-pattern decisions for a product UI. Sections: task inventory → IA (nav map, page map, one-name-one-concept); app-shell selection (sidebar / top nav / hybrid, with the rule for each); page anatomy (header with title · breadcrumb · one primary action, secondary in overflow; list→detail; dashboard composition); form layout (single column, label-above, grouped sections, primary action placement); density; expert accelerators (global search, command palette, shortcuts); notification surface; first-run / empty-state onboarding and progressive disclosure; the responsiveness budget (instant press feedback · skeleton · ~4 s acknowledgement · no CLS · optimistic where reversible). Every mechanic already owned elsewhere is cross-linked, not restated (`ui-rules` correctness, `error-handling` states, `responsive-design` reflow, `animation` motion, `accessibility`). Written to be loadable by both the `fe-*` builders and the planner (T5) — it states the decisions and their rules, and carries no stack code.

**T2 — `visual-identity` has a product-UI lane.**
Deliverable: the skill opens by classifying the brief — *marketing page* or *application* — and the hero/signature/asymmetry/"take a risk" guidance applies only to the marketing lane. The application lane carries the modern-app recipe (neutral surface scale with raised/overlay tiers, one accent spent on the primary action, three text tones, hairline borders over heavy shadows, 4/8-px spacing rhythm, one radius scale, restrained elevation, one icon family, deliberate dark palette). The three-AI-default-looks critique stays for both lanes.
Depends on: T1 (the lane hands layout decisions to `ux-patterns`, not to its own composition section).

**T3 — the Title-Case conflict is resolved.**
Deliverable: `ui-code-audit/SKILL.md` states that the vendored *Content & Copy* section is superseded by `design/ux-writing` (sentence case, active verbs) and the audit does not emit findings from it; `ux-writing` cross-links the override. A build that follows `ux-writing` passes `ui-code-audit` clean on copy.

**T4 — `ux-review` captures its own evidence and measures feel.**
Deliverable: the skill has a capture step (Playwright MCP screenshot per primary task, or the user-supplied screenshot/mockup) and a *responsiveness* pass alongside heuristics, flow and IA — the budget from T1 as review questions (does a press acknowledge instantly, does a load skeleton rather than blank, does anything shift on load). Where an `experience-plan.md` exists (T5), every IA / steps-to-goal finding names the plan decision the build contradicts.
Depends on: T1.

**T5 — `backend/_shared/experience-plan` exists.**
Deliverable: a new planning skill `be-shared-experience-plan`, sibling of `data-model-plan` / `api-surface-plan`, producing `experience-plan.md` in the initiative folder with the pack's annotation grammar and evidence marks. Contents: **actors & primary tasks** (from the blueprint's areas and flows — each task an observable outcome, not a feature name); **journeys** (task → ordered screens → the endpoints each screen calls, with steps-to-goal counted); **screen map + IA** (`S1…Sn` with title, route, nav placement, app-shell choice, one-name-one-concept vocabulary); **per-screen spec** (pattern — list / detail / form / dashboard / wizard; surface — page / drawer / modal per `ux-patterns`' rule; primary action; loading / empty / failed states named; the data it needs); the **screen ↔ endpoint matrix**. It loads `design/ux-patterns` as its discipline (the way the blueprint loads `ba-*`) and writes screens, never code. Skipped, with the reason stated, when the blueprint routes no area to `fe-*`.
Depends on: T1.

**T6 — `be-planner` designs the experience with the system.**
Deliverable: `be-planner.md` and `solution-blueprint/SKILL.md` updated so that: (a) the blueprint gains **§2b Actors & primary tasks** and an **app-shell proposal** (marked `proposed`), so the approval gate covers who uses the system and how it is laid out; (b) a new planner step **Experience plan** runs after the data model and *before* the API surface, loading `experience-plan` (T5), so screens drive which endpoints exist rather than the reverse; (c) `api-surface-plan` accepts the screen data needs as an input and the API step's exit gate adds "every screen's data need resolves to an endpoint"; (d) delivery-plan frontend tasks bind `fe-react` / `fe-blazor` with `design-ux-patterns` in their skill list and cite the screen ids they deliver, and each user-facing capability's last-task deliverable is written against its journey; (e) Step-7 self-review gains *screen ↔ endpoint consistency* (every user-facing endpoint reached by a screen; every screen's data provided) and *journey coverage* (every actor task has a journey ending in a delivery task); (f) `plain-language-companion` produces `experience-plan-explained.md` (six companions); (g) the orientation cache's *Seams to reuse* records the existing app shell, nav and screen inventory for brownfield runs; (h) the "Never loaded" fence names `design/ux-patterns` as the one design-layer exception (discipline only — `fe-*` stack skills stay fenced). The output contract reports `Screens: <n> · journeys: <n>` and the coverage line adds `screens↔endpoints <n/n>`.
Depends on: T5.

**T7 — the `fe-*` agents consume the plan instead of re-inventing it.**
Deliverable: in both `fe-react.md` and `fe-blazor.md`, Step 1 loads `design/ux-patterns`; when the initiative folder holds an `experience-plan.md` the agent takes its screen map, app shell and journeys as the IA decision (validating, not redesigning — a disagreement is a §7 deviation in `delivery-plan.md`), and when it does not, the agent runs the `ux-patterns` task-inventory → IA step itself and writes the result into its decision record; Step 2 loads `ux-patterns` for per-page patterns; Step 5's `ux-review` runs per T4.
Depends on: T1, T5.

**T8 — the catalog and plugin manifests know about the new skills.**
Deliverable: `docs/skills-catalog.md` (design catalog = 10 skills / 10 `design-*` commands; the `be-planner` pack = 6 artifacts; both `fe-*` "loaded" lists), and `.claude-plugin/marketplace.json` bundles `design/ux-patterns` + its command into `fe-blazor` / `fe-react`, and `design/ux-patterns` + `backend/_shared/experience-plan` into `be-dotnet` / `be-java` / `be-node` (where `be-planner` ships). `CLAUDE.md`'s repository map is unchanged.
Depends on: T1, T5, T6, T7.
