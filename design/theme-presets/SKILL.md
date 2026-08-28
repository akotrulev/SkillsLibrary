---
name: design-theme-presets
description: Use to apply one of 10 preset color+font themes as primitive-tier starting values for an artifact (deck, doc, HTML page) or a quick-start web-app palette — when a brief does not warrant a bespoke identity. Triggers: "apply a preset theme", "style this deck/page with a theme", "quick theme". Do NOT use to INVENT a bespoke identity (`design/visual-identity`), match an EXISTING brand (`design/brand-import`), or for token tier discipline (`design/design-tokens`).
metadata:
  version: "1.1.0"
---

# Theme Factory Skill

A curated collection of 10 professional color + font themes, each a cohesive
palette (hex codes) paired with header/body typefaces and a distinct visual
identity. Once a theme is chosen, apply it to any artifact — a slide deck, a
doc, an HTML page — or use it as a quick-start palette for a web app.

> **In a web-app token system:** a theme's palette hexes and font pairing are
> **primitive-tier starting values** — feed them into [`design/design-tokens`](../design-tokens/SKILL.md)'s
> tier model (assign semantic roles: which hue is `--color-accent`, `--surface`,
> `--text`) rather than referencing the raw theme hexes in components. Theme
> Factory is the quick-start when a brief doesn't warrant a bespoke
> [`design/visual-identity`](../visual-identity/SKILL.md) system.

**Corpus authority.** The facts this skill decides with come from the vendored [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** The 10 presets below remain the artifact/quick-start lane, but for a **web app** the corpus's 192 product palettes are the larger and better-matched set — query it before settling for a preset:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<product type> <mood>" --domain color
```

Each corpus palette ships all 17 semantic slots (primary/on-primary … ring), which a preset does not. Use a preset when the target is a deck, doc, or HTML artifact, or when the user asked for one by name; use the corpus for anything that ships as product UI.

## Purpose

To apply consistent, professional styling to an artifact without a bespoke
design pass, use this skill. Each theme includes:
- A cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- A distinct visual identity suitable for different contexts and audiences

## Usage Instructions

To apply a theme to an artifact:

1. **Show the theme showcase** *(slide/doc lane only)*: display the
   `theme-showcase.pdf` file so users can see all themes visually. Do not modify
   it; simply show it for viewing. A web app doesn't need the PDF ritual —
   describe the themes and their palettes instead.
2. **Ask for their choice**: ask which theme to apply.
3. **Wait for selection**: get explicit confirmation of the chosen theme.
4. **Apply the theme**: apply the selected theme's colors and fonts to the
   artifact. On a web app, follow the web-app lane below.

## Themes Available

The following 10 themes are available, each showcased in `theme-showcase.pdf`:

1. **Ocean Depths** - Professional and calming maritime theme
2. **Sunset Boulevard** - Warm and vibrant sunset colors
3. **Forest Canopy** - Natural and grounded earth tones
4. **Modern Minimalist** - Clean and contemporary grayscale
5. **Golden Hour** - Rich and warm autumnal palette
6. **Arctic Frost** - Cool and crisp winter-inspired theme
7. **Desert Rose** - Soft and sophisticated dusty tones
8. **Tech Innovation** - Bold and modern tech aesthetic
9. **Botanical Garden** - Fresh and organic garden colors
10. **Midnight Galaxy** - Dramatic and cosmic deep tones

## Theme Details

Each theme is defined in the `themes/` directory with complete specifications:
- Cohesive color palette with hex codes
- Complementary font pairings for headers and body text (plus a **web font
  suggestion** for the web-app lane — see below)
- Distinct visual identity suitable for different contexts and audiences

## Application Process (slide/doc lane)

After a preferred theme is selected:
1. Read the corresponding theme file from the `themes/` directory
2. Apply the specified colors and fonts consistently throughout the artifact
3. Ensure proper contrast and readability
4. Maintain the theme's visual identity across all slides/pages

## Using a theme on a web app

A theme is a *starting point*, not a component-ready token system. To use one in
a web app:

1. **Hexes enter as primitives.** Assign semantic roles per
   [`design/design-tokens`](../design-tokens/SKILL.md) — decide which hue is
   `--color-accent`, which fills `--surface` / `--surface-raised`, which is
   `--text` / `--text-muted`. **Never reference a raw theme hex in a component**;
   components read the semantic tokens.
2. **Substitute a web font.** The theme files name PDF-rendering faces (DejaVu /
   Free* families) for the slide/doc lane — on the web, use each theme's
   **`Web font suggestion:`** line instead (one character-matched web stack per
   theme, listed in that theme's `themes/*.md`). Load them as real web fonts
   with `font-display: swap`.
3. **Status colors are NOT part of a theme.** The status set
   (success / warning / danger / info) is a **disjoint** group owned by
   [`design/design-tokens`](../design-tokens/SKILL.md) — a theme supplies brand
   and neutral hues only. Don't press a theme accent into service as the danger
   color.

Beyond the palette/font quick-start, everything else (composition, dark mode,
the full neutral ramp) is `design-tokens` / `visual-identity` work — a preset
theme gets you started, it doesn't finish the system.

## Create your Own Theme

To handle cases where none of the existing themes work for an artifact, create a
custom theme. Based on provided inputs, generate a new theme similar to the ones
above. Give the theme a similar name describing what the font/color combinations
represent. Use any basic description provided to choose appropriate colors/fonts
(include a `Web font suggestion:` line if it may be used on the web). After
generating the theme, show it for review and verification, then apply it as
described above.
