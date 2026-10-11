# Attributions — `design/`

Provenance for the borrowed artifacts shipped inside this domain. The `design/`
folder is bundled wholesale into the `fe-blazor` and `fe-react` plugins, so this
file ships wherever the borrowed material ships. One section per artifact.

---

## Anthropic brand fixture (`brand-import`)

`brand-import/SKILL.md` §"Example-brand fixture" uses the Anthropic brand as a
worked brownfield stand-in to exercise every gap-fill branch of the pipeline:

- Primitives: `#141413` (dark), `#faf9f5` (light), `#b0aea5` / `#e8e6dc` (grays),
  accents `#d97757` / `#6a9bcc` / `#788c5d`.
- Typefaces: **Poppins** (Arial fallback) for headings ≥24pt, **Lora** (Georgia
  fallback) for body.

These values originate from Anthropic's `brand-guidelines` skill. They are used
as a realistic worked example only — a brand with three accents but no status
set, faces but no scale, and no dark mode — **not** a claim of affiliation or
endorsement.

---

## `ui-code-audit` — Vercel Web Interface Guidelines

The review ruleset vendored at `ui-code-audit/references/guidelines.md`
is imported from Vercel.

- Upstream: `vercel-labs/web-interface-guidelines`,
  `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`
- Snapshot commit: `d0a657bfe87e86dd3a4753d7ec28c7e7dd7a88fe` (2026-04-06)
- Retrieved / vendored: **2026-07-12**
- License: MIT at import time.

The house SKILL.md reads the pinned snapshot first and optionally prefers a
fresh upstream fetch when the network is available, so behavior no longer
depends on a live network call. `metadata: author: vercel` is retained in the
skill frontmatter; the fork from upstream's always-fetch behavior is reflected
in its `version`.

---

## `theme-presets` — theme showcase + preset themes

The `theme-presets` skill (the `theme-showcase.pdf` and the 10 preset theme
files under `themes/`) is an Anthropic-provided import.

- Origin: Anthropic-provided theme showcase (PDF) + 10 theme definition files.
- Imported: **2026-07-12**.

The preset palettes and font pairings are used as primitive-tier starting
values for artifacts (slides, docs, HTML pages) and as a web-app quick-start.
The theme files' original PDF-rendering typefaces (DejaVu / Free* families) are
retained for the slide/doc lane; each theme additionally carries a web-font
substitution for the web-app lane (see `theme-presets/themes/*.md`).

---

## `ui-ux-pro-max` — the design-intelligence corpus

The whole of `design/ui-ux-pro-max/` — the CSV corpus under `data/`, the BM25
search engine and design-system generator under `scripts/`, and both reference
rulesets under `references/` — is vendored from the UI/UX Pro Max skill.

- Upstream: `nextlevelbuilder/ui-ux-pro-max-skill`,
  `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill`
- Snapshot commit: `8bd29e775453ebcae52b6e6514fbf134df0c5770` (2026-08-27)
- Upstream release: **v2.13.0**
- Retrieved / vendored: **2026-08-28**
- License: MIT at import time — the upstream notice is kept verbatim at
  `design/ui-ux-pro-max/LICENSE`.
- Vendored from the upstream paths `src/ui-ux-pro-max/{data,scripts}` and
  `.claude/skills/ui-ux-pro-max/references`.

**This corpus is the source of truth for design facts in this library.** Where
it and a house `design/*` skill disagree on a fact — which palette suits a
product type, which font pairing carries a mood, what the guideline for a
pattern is, which chart fits a data shape, what a stack's UI convention is —
the corpus wins, and the house skill supplies only the judgment layered on top.
Every consuming skill states this in its own **Corpus authority** block.

What was changed from upstream at import, and why:

| Fork | Reason |
|---|---|
| `SKILL.md` rewritten in house style, renamed `design:corpus` | The library's skills are `design-`-prefixed and carry a `## Review checklist` the `design-auditor` agent sweeps. The query contract, workflow, dials, domain/stack tables and zero-result rule are upstream's, unchanged in substance. |
| Script paths rewritten to `${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/…` | The skill sits under `design/` here, not at a plugin root. |
| `scripts/tests/`, `templates/`, the CLI, gallery and stack starter not vendored | Upstream repo tooling, not skill content. `scripts/validate_data.py` is kept so the corpus can be re-validated after a refresh. |
| All 22 stack files retained | Deliberate: the corpus ships whole. Blazor has no upstream stack file and takes its conventions from `frontend/blazor/`. |
| GSAP presets surfaced as a house skill (`design/motion`), landing patterns as `design/landing-patterns` | Two upstream domains had no home in `design/`; the data stays in the corpus, the judgment layer is house-written. |

Refreshing is a snapshot operation: copy those upstream paths at a new pinned
commit, run `python3 design/ui-ux-pro-max/scripts/validate_data.py`, and update
the commit, release and date above.
