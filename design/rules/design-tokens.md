---
paths:
  - "**/tokens.{css,scss,json}"
  - "**/*.tokens"
  - "**/*.tokens.json"
  - "**/{tokens,design-tokens}/**/*.{css,scss,json,ts,js}"
---

<!-- design rules v1 (2026-11-03): design tokens and brand. Installed by /design:rules; add the file that holds this app's tokens (a globals.css :root block, a Tailwind @theme, a theme file) to the paths above. -->

# Design-token standards

Apply these to the file that defines the app's tokens, whatever the stack. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a hard rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. How a token becomes CSS, and how contrast is measured, are the stack's own styling and accessibility rules; this file is the system's structure. **The codebase wins** where it consistently does otherwise, as a deliberate convention.

## Tiers and names

- Every literal (hex, px, rem, ms) lives in a primitive; a semantic token points at a primitive and a component token at a semantic one, never at a raw value and never skipping a tier. *minor*
- Components read semantic (or component) tokens, never a primitive: `var(--blue-600)` in a component is an escaped literal. *minor*
- Primitives are named by appearance (`--blue-600`); semantic and component tokens by purpose (`--color-danger`, `--surface-raised`), never `--color-red`. *minor*
- One shape, `--<category>-<role>[-<variant>]` (or `color.text.muted` in DTCG JSON), never mixed in one system. *nit*
- Two tiers unless a component genuinely fights the semantic layer; no component token per property by reflex. *minor*
- One token set app-wide: a feature that needs a colour gets a semantic token in the shared set, never a palette fork. *minor*

## Categories

- Each category is a bounded scale: spacing off one base unit (commonly 4 px), type from one modular ratio and one base, a small named set for radius, elevation, motion durations and easings, breakpoints named once. No one-off values. *minor*
- The semantic status set (success, warning, danger, info) is disjoint from brand tokens, even where the brand offers a matching hue. *major*
- Chart colours are their own semantic group (`--viz-cat-*`, `--viz-seq-*`, `--viz-div-*`): at most 6 to 8 categorical hues, none equal to a status colour, the brand accent never an arbitrary data series. *major*
- Values come from the brand or the `design:corpus` `--design-system` output, motion values from the corpus row for the product's one intensity tier; never invented. *minor*

## Theming

- Dark mode and brand variants remap the semantic tier only: primitives never fork, no component style changes per theme, never `filter: invert()` or computed negation. *major*
- A dark palette is chosen, not derived: desaturated accents, no pure-black surface, every contrast pair re-checked in that theme. *major*

## Brand

- The fidelity mode (strict compliance or brand-inspired) is stated at the top of the token file. *minor*
- Every stated brand value is a primitive, reproduced exactly, its print value (Pantone, CMYK) kept beside it as provenance; nothing brand-visible changes silently. *major*
- The brand primary fills one role (`--color-accent`), not danger, link and focus at once; gap-filled values hold the brand's hue, temperature and saturation, never a generic default. *minor*
- A brand pair that fails contrast gets a darker or lighter primitive of the same hue for text; the brand colour is never recoloured, and under strict compliance the failure goes to the owner. *major*

## Delivery

- CSS custom properties by default; W3C DTCG JSON only when a real pipeline (Style Dictionary, Terrazzo, Tokens Studio, a Figma sync) generates more than one platform from it. *minor*
