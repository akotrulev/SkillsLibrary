---
paths:
  - "**/*.{css,scss}"
  - "**/tailwind.config.{js,ts,mjs,cjs}"
  - "**/theme/**/*.{ts,tsx}"
  - "**/theme.{ts,tsx}"
---

<!-- fe-react rules v1 (2026-11-03): styling. Installed by /fe-react:rules; edit to fit this project. -->

# React styling standards

Severity tags as in the core React rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One styling authority: Tailwind on the shadcn/ui lane, the library theme on MUI / Mantine / Chakra, CSS Modules for hand-written CSS. Never Tailwind on top of a CSS-in-JS library. *minor*
- `globals.css` holds only tokens and a minimal reset, never component styles. *minor*
- Tokens are CSS custom properties, named by purpose (`--color-danger`), bridged to one source with the library theme; no hard-coded hex or px colour in a module or `sx`. *minor*
- Share styles through `composes` or a `className` prop, never a descendant selector into a child's internals; `:global` sparingly. *minor*
- Type sizes come from one scale of tokens, display sizes fluid with `clamp()`; fonts load through `next/font`. *minor*
- Dark mode is an authored second palette swapped by `next-themes` or the library toggle, contrast re-checked; never `filter: invert()`. *major*
- Mobile-first `min-width` queries on one breakpoint set; no magic widths; intrinsic layout and container queries before media queries. *minor*
- Visual reordering never breaks focus order: DOM order is reading order. Logical properties, not `left` / `right`, so RTL needs no second sheet. *major*
- Motion respects `prefers-reduced-motion` (opt in under `no-preference`) and animates only `opacity` and `transform`. *major*
- A removed focus outline always gets a visible replacement. *major*
