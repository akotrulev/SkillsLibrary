# Blazor FE skillset — gap analysis vs the `frontend-design` plugin

**Date:** 2026-07-11
**Evaluated:** `frontend/blazor/skills/*` (17 skills) + the planned `fe-blazor` agent (PLAN §5; agent not yet built — Session F)
**Benchmark:** the installed **`frontend-design`** plugin skill (`claude-plugins-official/frontend-design`) and the two design helpers the agent is planned to load (`design/frontend-design`, `design/web-design-guidelines`, `design/theme-factory`).

---

## TL;DR

The two bodies of knowledge are **complementary, not overlapping**. The `frontend-design` plugin owns *visual craft and distinctiveness* — palette, typography, motion, spatial composition, UX copy, and a deliberate anti-generic ("no AI slop") point of view. The Blazor stack owns *engineering correctness* — render modes, transport, state, testability, display correctness, a11y mechanics, resilience, SEO, performance.

The gaps are almost entirely **one-directional**: design-craft dimensions the plugin treats as first-class have **no owner** in the Blazor stack, and the `design/` skills meant to carry them are either **stale** (a superseded copy of the plugin) or **built for the wrong medium** (slide decks). The Blazor stack's engineering depth is *not* mirrored back as a gap in the plugin — the plugin simply doesn't touch that territory.

Net: the Blazor stack builds UIs that are **correct, testable, and resilient** but has no skill that makes them **distinctive or aesthetically deliberate**. That job is currently delegated to `design/` helpers that under-deliver against the installed plugin.

---

## Severity summary

| Severity | Gap | Owner today | Recommendation |
|----------|-----|-------------|----------------|
| **major** | Stale design skill: `design/frontend-design` is a 41-line superseded copy of the installed plugin | `design/frontend-design` (loaded Phase 1/5) | Refresh from the plugin, or have the agent load the plugin skill directly |
| **major** | Motion & animation craft has no owner | one `prefers-reduced-motion` line in `styling` | New `motion` skill (or a first-class Motion section in `styling`) |
| **major** | UX writing / microcopy voice has no owner | structure-only in `ui-conventions` + `error-resilience` | New `ux-writing` skill, or a Voice section in `ui-conventions` |
| **major** | No design-plan-first + self-critique gate in the agent | planned Phase 1 just "loads theme-factory + frontend-design" | Bake the plugin's brainstorm→critique-against-generic→build→screenshot-critique loop into Phase 1 & 5 |
| **minor** | Typographic craft is thin (token only, no scale/hierarchy/pairing) | `--font-body` token in `styling`; deferred to theme-factory | Add a type-scale/hierarchy section (styling or a new `typography` skill) |
| **minor** | `theme-factory` is slide-deck oriented, not a web-app token/brand source | `theme-factory` (loaded Phase 1) | Replace with a web-native brand/token skill, or scope theme-factory out |
| **minor** | Spatial composition / layout-as-design has no owner | responsive *mechanics* only in `styling`; *structure* in `reference` | Layout-composition section in `styling` or the design refresh |
| **nit** | Backgrounds / atmosphere / depth (gradient mesh, noise, texture) unaddressed | none | Subset of the layout/composition fix above |

---

## What the Blazor stack already covers well (not gaps)

The plugin does **not** cover — and the stack owns cleanly:

- **Render-mode architecture** (static-SSR-default islands, render-mode-agnostic components) — `project-scaffold`, `reference`.
- **Transport** (request/response vs live push behind one interface) — `data-access`, `realtime`.
- **Testability** (`data-testid` authoring + audit, the qa handshake) — `testability`.
- **Display correctness** (enum humanization, canonical formats, GUID→name, table ergonomics, CRUD/edit semantics, confirmations) — `ui-conventions`.
- **A11y *mechanics*** (focus under enhanced nav, ARIA APG, live regions) — `accessibility`.
- **Error/empty-state *structure*** (three-state regions, inline grid errors) — `error-resilience`.
- **Forms, state, performance, SEO** — respective skills.

These make the stack a strong *engineering* complement to the plugin's *craft*. The recommendation is never to duplicate the plugin's design opinion into these skills — it is to give the craft dimensions an explicit owner and wire the agent to it.

---

## Gap detail

### 1. `design/frontend-design` is stale relative to the installed plugin — **major**

The agent (PLAN §5, Phases 1 & 5) loads `design/frontend-design`. That file (`design/frontend-design/SKILL.md`, 41 lines) is an **older, thinner** version of the installed plugin skill. The installed plugin adds material the repo copy entirely lacks:

- The **three-AI-look calibration** (cream+serif+terracotta / near-black+acid accent / broadsheet hairlines) and the instruction to *not* spend free design axes on those defaults.
- The **signature-element** concept ("the single unique element this page will be remembered by").
- **Hero-as-thesis** ("open with the most characteristic thing in the subject's world").
- The **brainstorm → critique-against-generic → build → critique-again** two-pass process with a compact token system (color / type / layout / signature).
- A full **"writing in design"** section (see gap #3).
- Subject-grounding ("name one concrete subject, its audience, and the page's single job").

**Impact:** Phase 1 of the agent draws on the weaker vendored copy while a materially better version is installed on the machine.

**Recommendation:** refresh `design/frontend-design/SKILL.md` from the plugin (preserving repo frontmatter conventions), **or** change the agent's skill-loading protocol to load the plugin skill directly. Record the provenance in `ATTRIBUTIONS.md`. Because this skill is stack-agnostic, keeping it in the shared `design/` family (per PLAN's "visual `_shared`" decision) is correct — just un-stale it.

### 2. Motion & animation craft has no owner — **major**

The plugin treats motion as a **first-class design tool**: an orchestrated page-load sequence with staggered reveals, scroll-triggered reveals, hover micro-interactions, ambient atmosphere, and "an orchestrated moment usually lands harder than scattered effects," all over a `prefers-reduced-motion` floor.

The Blazor stack's total motion coverage is defensive, not generative: one `prefers-reduced-motion` line in `styling`, and mentions in `reviewer`/`ui-conventions` that amount to "don't overdo it." **No skill teaches how to author tasteful motion in Blazor** — CSS transitions/keyframes over isolated styles, staggered `animation-delay` reveals, scroll-triggered reveals (IntersectionObserver via JS interop or `@onscroll`), enhanced-navigation view transitions, and where motion is worth the interop cost vs. pure CSS.

**Recommendation:** add `frontend/blazor/skills/motion` (or a first-class Motion section in `styling`), scoped to Blazor mechanics (CSS-isolation keyframes, reduced-motion as a hard floor, JS-interop only where CSS can't reach, view-transition API under enhanced nav). Keep the *taste* (where/whether to animate) in the refreshed `design/frontend-design`; own the *implementation* here.

### 3. UX writing / microcopy voice has no owner — **major**

The plugin dedicates a full section to copy as design material: write from the user's side of the screen, active voice ("Save changes," not "Submit"), an action keeps its name through the whole flow (a "Publish" button yields a "Published" toast), sentence case, errors that explain what went wrong and how to fix it "in the interface's voice," empty screens as invitations to act.

The Blazor stack owns the **structure** of these moments but not the **voice**:
- `ui-conventions` owns empty-state *taxonomy* (no-records vs no-filter vs filter-matched-nothing) and IA consistency ("one verb per operation app-wide") — but not the wording discipline.
- `error-resilience` owns error *categorization* (ProblemDetails → friendly message + correlation id) — but not how the friendly message reads.

So the *slots* are defined and the *copy craft that fills them* is unowned.

**Recommendation:** add a small `frontend/blazor/skills/ux-writing` (stack-agnostic enough it could live in `design/`), **or** add a "Voice & microcopy" section to `ui-conventions` that cross-links `error-resilience`'s error slots and the generator's button/label emission. Rules: active-voice control labels, label-persistence through a flow, sentence case, error/empty voice. This pairs naturally with the existing "one name → one concept, one verb per operation" IA rule.

### 4. No design-plan-first + self-critique gate in the (planned) agent — **major**

The plugin prescribes a **process**, not just principles: brainstorm a compact token system (4–6 named hex, 2+ typeface roles, a layout concept with ASCII wireframes, a signature element) → **review it against the generic default you'd produce for any similar brief and revise** → build exactly to the revised plan → **critique again, taking screenshots**.

The agent's planned Phase 1 (PLAN §5) is "Architecture foundations … load `design/theme-factory`, `design/frontend-design`" with an exit gate of "walking-skeleton page renders styled + authenticated." There is **no critique-against-generic gate** and no explicit visual self-review, even though the agent is planned to carry the Playwright MCP for exactly that.

**Impact:** the agent can produce architecturally-correct, on-token, but visually *generic* UIs and still pass its gates.

**Recommendation:** since the agent isn't built yet (Session F), bake the loop in now:
- **Phase 1 exit gate** — add "a written design plan (palette / type / layout / signature) that has been critiqued against the three AI-default looks and revised, with the revision noted."
- **Phase 5 (Review)** — add a visual self-critique pass (screenshot via Playwright MCP, apply the plugin's restraint check: "remove one accessory") alongside the existing `web-design-guidelines` audit.

### 5. Typographic craft is thin — **minor**

The plugin: "Typography carries the personality of the page … set a clear type scale with intentional weights, widths, and spacing … make the type treatment a memorable part of the design." The Blazor `styling` skill exposes a single `--font-body` token and explicitly defers font *pairing* to `theme-factory`. But no skill in the FE path owns the app's **type scale, heading hierarchy, responsive type, or display+body pairing** as a system — `theme-factory` gives a font *pair* per theme but not a scale, and it targets slides.

**Recommendation:** add a type-scale/hierarchy subsection to `styling` (modular scale as tokens, heading hierarchy, `clamp()` responsive type, weight/tracking discipline) or a dedicated `typography` skill. Low urgency — the token seam exists; it just needs a scale system layered on.

### 6. `theme-factory` is slide-deck oriented, not a web-app token source — **minor**

`design/theme-factory` is explicitly a toolkit for "slides, docs, reportings, HTML landing pages" — 10 fixed themes shown via `theme-showcase.pdf`, an ask-user-to-pick flow. As the **web-app palette/token source** the plan wires into Phase 1, it's a weak fit: it isn't web-token-shaped, its themes are presentation-oriented, and picking from 10 presets is the opposite of the plugin's "make deliberate, opinionated choices specific to *this* brief."

**Recommendation:** treat `theme-factory` as an optional quick-start, not the primary theming authority. The primary should be the refreshed `design/frontend-design` (per-brief token system) feeding `styling`'s CSS custom properties. Consider a web-native brand/token skill later; for now, downgrade theme-factory's role in the agent's Phase 1 wording.

### 7. Spatial composition / layout-as-design has no owner — **minor**

The plugin values unexpected layouts, asymmetry, overlap, diagonal flow, grid-breaking, generous negative space *or* controlled density — and atmosphere/depth via gradient meshes, noise, texture, layered transparency, dramatic shadows. The Blazor stack covers **responsive mechanics** (`styling`: mobile-first, breakpoints, container queries) and **component structure** (`reference`: layering, slots) — but nothing owns *visual composition* as a design decision.

**Recommendation:** fold a "Composition & atmosphere" note into the refreshed `design/frontend-design` (taste) with a thin implementation cross-link from `styling` (CSS grid/backgrounds mechanics). Lowest urgency; largely subsumed by fixing gap #1.

---

## Recommended sequencing

1. **Refresh `design/frontend-design`** from the installed plugin (gap #1) — highest leverage, unblocks #4, #5, #7 by giving the taste layer a strong home. Add `ATTRIBUTIONS.md` entry.
2. **Wire the critique loop into the `fe-blazor` agent** (gap #4) while authoring it in Session F — cheapest to do before the agent exists.
3. **Author `motion`** (gap #2) and a **`ux-writing`** owner (gap #3) — the two genuinely unowned craft domains.
4. **Type-scale in `styling`** (gap #5) and **re-scope `theme-factory`** (gap #6) — incremental.
5. **Composition note** (gap #7) — rolls up into #1.

None of these change the stack's engineering skills; they add the craft layer the plugin exposes and re-point the agent's design phases at a non-stale source.
