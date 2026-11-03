---
paths:
  - "**/*.razor.css"
  - "**/wwwroot/**/*.css"
---

<!-- fe-blazor rules v1 (2026-11-03): styles. Installed by /fe-blazor:rules; edit to fit this project. -->

# Blazor styling standards

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One styling authority: the component library's theme, CSS isolation with tokens, or Tailwind; never Tailwind on a component library, never two colour systems. *major*
- Component styles live in `.razor.css`; the global stylesheet holds only tokens and a minimal reset. *major*
- `::deep` only beneath an element the component owns; prefer a `Class` or CSS-variable parameter. *minor*
- Colours, sizes and type come from `var(--token)`, never hex or `px` literals; functional tokens are named by purpose (`--color-danger`). *minor*
- Dark mode is a second authored palette set via `data-theme` before first paint, never `filter: invert()`. *major*
- Text contrast is at least 4.5:1 (3:1 for large text and UI boundaries) on the real background, re-checked in dark mode; no `outline: none` without a visible replacement. *major*
- Mobile-first `min-width` queries from the one documented breakpoint set; no magic widths. *minor*
- Intrinsic layout first (`auto-fit`, `minmax`, wrap); one grid container owns a region; no fixed sizes on content regions. *minor*
- Logical properties (`margin-inline-start`), never `left`/`right`, so RTL works. *minor*
- Motion is opt-in under `@media (prefers-reduced-motion: no-preference)`. *major*
- Animate `transform` and `opacity` only; a stagger is capped at about 8 items. *minor*
