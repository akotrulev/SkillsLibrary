# design/ audit-fix plan — 2026-07-12

Source: audit of the 9 `design/` skills (session 2026-07-12). The seven house-authored
skills passed; the fixes concentrate in the two third-party imports
(`theme-factory`, `web-design-guidelines`), stale Blazor-only cross-links, and a
missing attributions file. Work one phase at a time, top to bottom — phases are
ordered by severity and so that earlier phases never have to be re-touched by
later ones. Check off items as they land; each phase ends with its own verify step.

**Conventions that bind every phase**

- Frontmatter `description` follows the house shape: what/when → explicit
  trigger phrases → "Do NOT use for …" fence naming the sibling skill that owns
  each excluded concern.
- Cross-links are repo-relative markdown links that must resolve
  (`](../x/SKILL.md)` from inside `design/<skill>/`).
- No behavior/scope changes to the seven house-authored skills beyond what a
  finding names — this is a repair pass, not a rewrite.
- After every phase: re-run the link check (see Verify blocks) and `git diff`
  review before moving on.

---

## Phase 1 — ATTRIBUTIONS.md (major: broken promise shipped in two plugins)

`design/brand-intake/SKILL.md:80` says "Provenance noted in `ATTRIBUTIONS.md`"
but the file exists nowhere in the repo.

- [ ] Create **`design/ATTRIBUTIONS.md`** (domain folder, not repo root — the
  `fe-blazor`/`fe-react` plugins bundle `design/` wholesale, so the file ships
  wherever the claim ships). Contents, one section per borrowed artifact:
  - **Anthropic brand fixture** — the example-brand values in
    `brand-intake/SKILL.md` §"Example-brand fixture" (hexes `#141413`,
    `#faf9f5`, `#b0aea5`, `#e8e6dc`, `#d97757`, `#6a9bcc`, `#788c5d`; Poppins /
    Lora) originate from Anthropic's `brand-guidelines` skill. Used as a worked
    brownfield example only; not a claim of affiliation.
  - **`web-design-guidelines`** — imported from Vercel
    (`vercel-labs/web-interface-guidelines`, MIT check at import time; record
    upstream URL + the commit/date of the snapshot vendored in Phase 2).
  - **`theme-factory`** — Anthropic-provided import (theme showcase PDF +
    10 theme files). Record origin and import date.
- [ ] Update `design/brand-intake/SKILL.md:80` to point at the real path:
  `(Provenance noted in ../ATTRIBUTIONS.md)` — keep it a plain path mention or
  a resolving relative link, either is fine as long as the file exists.
- [ ] **Verify:** `ls design/ATTRIBUTIONS.md` succeeds; grep for
  `ATTRIBUTIONS` under `design/` shows only resolving references.

---

## Phase 2 — web-design-guidelines: vendor the ruleset + house description (2 majors)

Today the skill is a 39-line shell that WebFetches its entire ruleset from
`https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`
on every run — unpinned and dead offline — and its description claims the
"review UX" / "check accessibility" triggers that `ux-heuristics` and qa
`accessibility-testing` own.

- [ ] **Vendor a pinned snapshot.** Fetch the upstream `command.md` once, save
  verbatim as `design/web-design-guidelines/references/guidelines.md` with a
  3-line provenance header (upstream URL, retrieval date, upstream commit SHA
  if obtainable). Mirror the pattern already used by
  `frontend/react/vendor/reference` for the Vercel perf rules.
- [ ] **Rewrite the SKILL.md body** to a local-first flow:
  1. Read `references/guidelines.md` (always works, the pinned baseline).
  2. *Optional freshness step:* if network is available, WebFetch the upstream
     URL and prefer it when it parses; on any failure, silently fall back to
     the vendored copy. Never hard-fail on fetch.
  3. Keep the existing review mechanics (read target files → apply rules →
     terse `file:line` findings output).
- [ ] **Rewrite the frontmatter description** to house shape. It must state the
  altitude — the **CODE-level** UI audit (markup, attributes, interaction
  handlers in source files) — plus triggers ("audit my UI code against web
  interface guidelines", "pre-ship UI code audit", "check this component's
  markup against best practices") and the Do-NOT fence:
  - experience-level review (flows, heuristics, IA) → `design/ux-heuristics`
  - automated a11y scanning (axe/Lighthouse) → qa `accessibility-testing`
  - visual taste / identity → `design/frontend-design`
  - copy wording → `design/ux-writing`
  Drop "review UX" and bare "check accessibility" from its trigger list — those
  route to ux-heuristics / qa per the fences the rest of the folder already
  declares.
- [ ] Keep `metadata: author: vercel` and bump `version` to reflect the fork
  from upstream behavior (e.g. `"1.1.0"`), note the vendoring in ATTRIBUTIONS
  (Phase 1 stub → fill in the actual snapshot SHA/date now).
- [ ] **Check the ripple:** grep `web-design-guidelines` across
  `frontend/blazor/agents/fe-blazor.md`, `frontend/react/agents/fe-react.md`,
  `CLAUDE.md`, and `.claude-plugin/marketplace.json` — the agents call it the
  "code-level audit" already, so no wording change expected; confirm nothing
  references the always-fetch behavior.
- [ ] **Verify:** description contains a Do-NOT fence; `references/guidelines.md`
  exists and is non-trivial (> 100 lines expected); SKILL.md instructs
  local-first with fetch fallback; simulate the review flow mentally against a
  sample file to confirm the instructions are executable offline.

---

## Phase 3 — theme-factory: house description + web-app lane (1 major, 1 minor)

The frontmatter description is unadapted upstream text with typos ("themes
themes", "that has been creating", "reportings") and no trigger/Do-NOT
structure — and the description is the string the router matches on. The body
is slide-deck-centric and every theme names **DejaVu Sans** (a PDF-rendering
font) though the skill ships in two web frontend plugins.

- [ ] **Rewrite the frontmatter description** (fix all typos, house shape):
  what it is — 10 preset palette + font-pairing themes used as
  **primitive-tier starting values** for artifacts (slides, docs, HTML pages)
  or as a web-app quick-start; triggers ("apply a preset theme", "style this
  deck/page with a theme", "quick theme without a bespoke design"); Do-NOT
  fence — bespoke identity → `design/frontend-design`, existing brand →
  `design/brand-intake`, tier/naming discipline → `design/design-tokens`.
- [ ] **Generalize the body's process wording** from deck-only to
  artifact-general: "apply to the deck/artifact", keep the showcase-PDF step
  but mark it slide/doc-lane (a web app doesn't need the PDF ritual). Keep the
  existing token-system blockquote (it's correct and already links
  `design-tokens` / `frontend-design`).
- [ ] **Add a web-app lane section** ("Using a theme on a web app"):
  1. Theme hexes enter as **primitives**; assign semantic roles per
     `design/design-tokens` (which hue is `--color-accent`, `--surface`,
     `--text`) — never reference raw theme hexes in components.
  2. **Font substitution table**: DejaVu Sans / DejaVu Serif are PDF-rendering
     faces — substitute a real web stack per theme. Either add a
     `Web font suggestion:` line to each of the 10 `themes/*.md` files
     (preferred — one edit per file, e.g. Ocean Depths → `"Source Sans 3",
     system-ui` or similar character-matched picks), or centralize a 10-row
     mapping table in SKILL.md. Pick ONE location; do not duplicate.
  3. Note that the status-color set (success/warning/danger/info) is NOT part
     of a theme — it comes from `design-tokens`' disjoint status group.
- [ ] Do NOT touch `theme-showcase.pdf` or restructure `themes/` — the
  showcase flow stays for the slides/docs lane.
- [ ] **Verify:** description reads clean (no typos), has triggers + fence;
  each theme has exactly one web-font mapping; blockquote links still resolve.

---

## Phase 4 — cross-link currency: add React siblings (minor, mechanical)

Stack-agnostic skills link "a stack's X" only to the Blazor implementation;
all React counterparts exist (verified: `frontend/react/skills/{ui-conventions,
error-resilience,component-library,accessibility,seo-discoverability,styling}`).
Pattern per link: `([Blazor](../../frontend/blazor/skills/<s>/SKILL.md) ·
[React](../../frontend/react/skills/<s>/SKILL.md))`.

- [ ] `ux-writing/SKILL.md` — lines ~8 ("Blazor today, React next" → "written
  once and reused across stacks (Blazor, React)"), ~30–31 (When-NOT links for
  `ui-conventions`, `error-resilience`), ~111–112 (Handoffs links for the same
  two).
- [ ] `iconography/SKILL.md` — line ~38 (`component-library` in the library
  table), ~51 (`accessibility` / `ui-conventions`), Related list ~84–87
  (`component-library`, `ui-conventions`, `accessibility`,
  `seo-discoverability`).
- [ ] `dataviz/SKILL.md` — line ~96 (Related: stack `error-resilience`; example
  currently `fe-blazor-error-resilience` — add the React sibling).
- [ ] `design-tokens/SKILL.md` — line ~91 (Related: stack `styling`; example
  currently `fe-blazor-styling` — add `fe-react-styling`).
- [ ] `ux-heuristics/SKILL.md` — line ~80 (Related: stack `ui-conventions`).
- [ ] **Verify:** re-run the relative-link check over all `design/*/SKILL.md`
  (every `](../…)` target exists); grep `design/` for `React next` → no hits.

  ```bash
  cd design && for f in */SKILL.md; do dir=$(dirname "$f"); \
    grep -o '](\.\./[^)]*)' "$f" | sed 's/](\(.*\))/\1/' | while read -r l; do \
    [ -e "$dir/$l" ] || echo "BROKEN in $f: $l"; done; done
  ```

---

## Phase 5 — CLAUDE.md "Design catalog" section (minor)

The domain has no central catalog; it's described only piecemeal inside the
fe-blazor / fe-react catalogs.

- [ ] Add a **"Design catalog"** section to the project `CLAUDE.md`, placed
  between the Frontend-React and Backend catalogs. Content (short — mirror the
  density of the other catalogs, not their length):
  - One-paragraph scope: stack-agnostic aesthetic-craft layer, bundled into
    `fe-blazor` + `fe-react` (not a standalone plugin), loaded-not-owned by the
    `fe-*` agents.
  - The routing triangle, stated explicitly: **greenfield identity** →
    `frontend-design` (primary theme authority) · **existing brand** →
    `brand-intake` · **preset quick-start** → `theme-factory`; all three feed
    `design-tokens`' tier discipline.
  - One line per remaining skill: `dataviz` (product charts/dashboards — ops
    dashboards stay with `observability/grafana-dashboards`), `iconography`
    (icon family + OG imagery), `ux-writing` (voice filling stack-defined
    slots), `ux-heuristics` (experience-level review, house severity table),
    `web-design-guidelines` (code-level audit, vendored Vercel ruleset).
  - The two review altitudes named as a pair (code-level vs experience-level)
    since that fence is the one users will trip on.
- [ ] Cross-check the fe-blazor / fe-react catalog paragraphs still read
  correctly against the new section (they name the same skills; no
  contradiction expected — adjust only if one appears).
- [ ] **Verify:** CLAUDE.md section lists all 9 skills exactly once; no claim
  contradicts a skill's own description.

---

## Phase 6 — deferred / decision-needed (nits — do NOT execute without a check-in)

- [ ] **`design-*` name-prefix pass** (`dataviz` → `design-dataviz`, etc.).
  Deferred: renames ripple through both fe agents, marketplace.json, CLAUDE.md,
  and any installed-plugin muscle memory. Needs an explicit go/no-go decision.
  If approved, it's a separate session: rename frontmatter `name:` in all 9
  skills → update `frontend/{blazor,react}/agents/fe-*.md` → marketplace
  descriptions → CLAUDE.md catalogs → grep-sweep for old names.
- [ ] **`dataviz`'s "future stack `charts` skill"** — either add a line to the
  relevant gap-analysis/backlog doc (there is no `frontend/GAP-ANALYSIS.md`
  today; the qa one is domain-scoped) or soften `dataviz/SKILL.md:10` to "a
  stack charting concern" without promising a skill. Small either way; decide
  when touching dataviz next.

---

## Definition of done (phases 1–5)

- [ ] All relative links across `design/*/SKILL.md` resolve (script in Phase 4).
- [ ] `ATTRIBUTIONS.md` exists and covers all three borrowed artifacts with the
  final vendored-snapshot metadata from Phase 2.
- [ ] `web-design-guidelines` works with no network; its description fences
  cleanly against `ux-heuristics` / qa `accessibility-testing`.
- [ ] `theme-factory`'s description is typo-free house shape; every theme maps
  to a web font.
- [ ] No "React next" staleness; every "a stack's X" link offers both stacks.
- [ ] CLAUDE.md has the Design catalog section.
- [ ] `git diff` reviewed; commit per phase or one commit for 1–5 with a body
  listing the findings addressed.
