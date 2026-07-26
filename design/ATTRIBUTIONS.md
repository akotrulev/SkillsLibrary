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
