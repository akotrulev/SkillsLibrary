---
name: fe-react-styling
description: Use when writing the CSS yourself — CSS Modules + `composes`, design tokens as CSS custom properties bridged to the library theme, type scale (`clamp()`, `next/font`), dark mode via next-themes, and the one-authority decision (Tailwind on the default shadcn lane vs MUI `theme`+`sx` vs CSS Modules — never two at once). Triggers "scope this component's CSS", "dark mode with next-themes", "my styles leak between components". Not for the library's own theme object (`component-library`).
---

# React — Styling (CSS Modules, tokens, dark mode, the styling authority)

Owns how a React app is styled with **CSS you write**: component-scoped CSS Modules, design tokens, dark mode, responsive rules, and the one decision that keeps a codebase coherent — **which styling authority owns the app**. It does **not** own a component library's theme system (MUI `theme`, Mantine/Chakra tokens) — that's [`component-library`](../component-library/SKILL.md); this skill layers your own CSS *on top of or instead of* a library and defines when the authority flips.

**Version rule:** CSS Modules, CSS custom properties, and `composes` behave identically across React 18/19 and Next 14/15 — this skill is largely version-agnostic. The version-sensitive edges live in the sibling skills: which library owns the theme (v-major differences → [`component-library`](../component-library/SKILL.md)) and static-asset handling ([`performance`](../performance/SKILL.md)).

## When to use

- Scoping a component's CSS so it can't leak or collide (CSS Modules)
- Sharing rules between modules (`composes`) without a global dump
- Setting up design tokens (CSS custom properties) from a `design/visual-identity` palette
- Dark mode, responsive breakpoints (the CSS mechanics)
- Deciding the styling authority: library `sx`/`theme` vs Tailwind vs CSS Modules

## When NOT to use

- A component library's theme/token object (MUI `createTheme`, Mantine/Chakra `createSystem`/tokens) → [`component-library`](../component-library/SKILL.md)
- Picking the palette, fonts, visual direction, type *treatment* → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) (primary theming authority), `design/theme-presets` (optional quick-start)
- Contrast/WCAG auditing of the colors you chose → [`accessibility`](../accessibility/SKILL.md)
- Layout *component* structure (composition, slots) → [`basics`](../basics/SKILL.md); the breakpoint contract + grids → [`responsive-design`](../responsive-design/SKILL.md)

## The styling authority decision

Pick **one** primary styling authority per app. Mixing them uncontrolled is the top cause of specificity wars and dark-mode drift. This decision is driven by the component-library choice ([`component-library`](../component-library/SKILL.md)):

```
On the default lane — shadcn/ui, or bespoke on a headless kit?
  YES → Tailwind is the authority (shadcn REQUIRES it); the CSS-variable token block in
        `globals.css` IS the theme; CSS Modules for the rare escape hatch.
  NO ↓
On a CSS-in-JS component library (MUI / Mantine / Chakra) — usually an existing codebase?
  YES → the library theme + its style API (MUI `sx`/`styled`, Mantine style props, Chakra style props)
        is the authority. Your CSS Modules are gap-only (bespoke layout the library fights).
        Do NOT bolt Tailwind on top — its reset + utilities fight the library.
  NO ↓
Bespoke design, no library, team prefers scoped CSS over utilities?
  YES → CSS Modules + design tokens.
```

| Approach | Scope | Use when | Cost |
|---|---|---|---|
| **Tailwind** (utility-first) | Global utilities | **The default lane** — shadcn (requires it); bespoke on a headless kit | Reset fights CSS-in-JS libraries; **the authority when chosen** |
| **Library style API** (`sx`/`styled`, style props) | Per component, themed | With MUI/Mantine/Chakra — **the authority there** | Coupled to the library; runtime CSS-in-JS cost |
| **CSS Modules** (`*.module.css`) | Per file, auto-scoped | Escape hatch on the Tailwind lane; gap-only alongside a CSS-in-JS library; primary for bespoke-no-utilities | Verbose for cross-cutting utilities |
| **Design tokens** (CSS custom properties) | Global vars, consumed everywhere | **Always** — the theming backbone under any approach | None; do this regardless |
| **Global stylesheet dumping** | Global, unscoped | **Never** for component styles | Collisions, dead CSS, no ownership |

**One authority, always.** Never Tailwind *and* a CSS-in-JS library; never two of {sx, Tailwind, CSS Modules} fighting for the same element. [`component-library`](../component-library/SKILL.md) picks the authority; this skill enforces it.

## CSS Modules — `*.module.css`

A `Card.module.css` imported as `import styles from './Card.module.css'` compiles every class to a locally-unique name (`Card_title__x7f2`), so `className={styles.title}` matches only this component — the React analog of Blazor's CSS isolation. Rules:

- **Scoped by import, not by selector nesting.** `.title { }` in a module is already local — no need for `.card .title`. Don't over-qualify.
- **No route/URL knowledge in CSS** — style by structure, not by page.
- **Keep the module to this component's concerns**; shared primitives go in the token layer or a shared module via `composes`, not copied into each file.
- **`:global(...)`** escapes scoping for a genuinely global selector — use sparingly (e.g. targeting a third-party class you don't control), never as a shortcut to dump global rules.

## Sharing styles — `composes`, not `::deep`

Blazor's `::deep` reached into a child component's DOM from scoped CSS. React's model is different and cleaner: you don't reach *in* — you either **pass a `className`** down (the child spreads it onto its root) or **`composes`** shared declarations from another module:

```css
/* Button.module.css */
.base { padding: var(--space-2) var(--space-4); border-radius: var(--radius); font: inherit; }
.primary { composes: base; background: var(--color-action-primary); color: var(--color-on-action); }
```

```css
/* shared: compose from another file */
.card { composes: surface from './tokens.module.css'; padding: var(--space-4); }
```

Rules + gotchas:
- **To style a child, give it a `className` prop** it spreads onto its root (`<Child className={styles.slot} />`) — the explicit contract, not reaching past it. Library components take `className`/`sx`/`slotProps` for the same purpose ([`component-library`](../component-library/SKILL.md)).
- **`composes` only works inside CSS Modules**, and only `from` another module or the same file — not from global CSS.
- **Never reach a child's internals with a descendant selector from a parent module** (`.parent :global(.child-btn)`) to override it — that's the coupling `::deep` warned about. Expose a prop.

## Design tokens — the theming backbone

Define the palette/spacing/typography once as **CSS custom properties**, and reference `var(--token)` everywhere (modules, Tailwind config, and the library theme). This is the seam where the visual direction enters the codebase — map [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s per-brief token system (the primary authority; or a `design/theme-presets` preset for a quick-start) — palette hex + font pairing — to tokens. The *system* rules (tier model, purpose-naming, categories, theming-as-swap-set) are the stack-agnostic discipline owned by [`design/design-tokens`](../../../../design/design-tokens/SKILL.md) — this section is the React **mechanics**; defer the structure questions there.

```css
/* app/globals.css — the ONLY thing that legitimately lives global */
:root {
  --color-action-primary: #1867c0;
  --color-surface: #ffffff;
  --color-text: #1a1a27;
  --color-text-muted: #5a5a6e;
  --color-danger: #c62828;
  --space-1: .25rem; --space-2: .5rem; --space-4: 1rem;
  --font-body: "Inter", system-ui, sans-serif;
  --radius: .5rem;
}
```

Rules:
- **Modules consume tokens, never hardcoded hex.** `color: var(--color-text)` — a literal `#333` in a `.module.css` is a token that escaped.
- **Name functional tokens by purpose, not value.** `--color-danger` / `--color-surface-raised` / `--color-action-primary`, never `--color-red` / `--color-blue-500`. Purpose-named tokens keep meaning stable across a theme change and make an accessibility fix a one-line edit. Keep the semantic set (success / warning / danger / info) separate from brand tokens (the brand-vs-functional split is [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s decision).
- **One token set app-wide.** No per-feature palette forks.
- **Bridge to the library, one source of truth.** With MUI/Mantine/Chakra, set the *library theme* from these CSS vars (`palette.primary.main: 'var(--color-action-primary)'`) — or emit the library's CSS vars and have your modules read *those*. Never run two diverging color systems ([`component-library`](../component-library/SKILL.md)). With Tailwind/shadcn, the tokens *are* the theme (`--primary` in `globals.css`, referenced by Tailwind).

## Type scale & hierarchy

Typography is where `design/visual-identity`'s taste becomes tokens. That skill decides the *treatment* (the display/body pairing, the personality); this section is the *mechanics*: a scale, a hierarchy, responsive sizing, weight/tracking discipline. A single `--font-body` value is a font, not a type *system*.

**A modular scale as tokens.** Pick one ratio (1.2 minor-third for dense UI, 1.25 major-third, 1.333 perfect-fourth for editorial) and generate steps from one base:

```css
:root {
  --font-display: "Fraunces", Georgia, serif;   /* the characterful face, used with restraint */
  --font-body:    "Inter", system-ui, sans-serif;
  --font-mono:    ui-monospace, "SF Mono", monospace;

  --text-base: 1rem; --ratio: 1.25;
  --text-sm:  calc(var(--text-base) / var(--ratio));
  --text-lg:  calc(var(--text-base) * var(--ratio));
  --text-xl:  calc(var(--text-lg)   * var(--ratio));
  --text-2xl: calc(var(--text-xl)   * var(--ratio));
  --text-3xl: clamp(2rem, 1.4rem + 3vw, 3.5rem);   /* fluid display — min, preferred, max */

  --leading-tight: 1.15; --leading-body: 1.5;
  --tracking-tight: -0.02em;
}
```

In **Next.js load fonts with `next/font`** (`next/font/google` or `next/font/local`) — it self-hosts, subsets, and sets `font-display: swap` with zero layout shift, exposing a CSS variable you point `--font-body`/`--font-display` at. Never a raw `<link>` to Google Fonts (render-blocking, a [`performance`](../performance/SKILL.md) + privacy issue).

**Heading hierarchy is structural, not cosmetic.** Map the scale onto real heading levels once, globally, so `<h1>`–`<h4>` carry hierarchy and components don't re-pick sizes. One `<h1>` per page (also the [`accessibility`](../accessibility/SKILL.md) focus target on route change); never skip a level for size — restyle, don't relabel.

```css
h1 { font-family: var(--font-display); font-size: var(--text-3xl); line-height: var(--leading-tight); letter-spacing: var(--tracking-tight); }
h2 { font-family: var(--font-display); font-size: var(--text-2xl); line-height: var(--leading-tight); }
h3 { font-size: var(--text-xl); line-height: var(--leading-tight); font-weight: 600; }
body { font-family: var(--font-body); font-size: var(--text-base); line-height: var(--leading-body); }
```

**Weight & tracking discipline.** Two or three weights, not six (each is a font-load cost). Large display text wants **negative** tracking; small caps/labels slightly **positive**; body at `0`. Body line-height looser (~1.5) than headings (~1.15). Cap measure at ~66ch on long-form text. Load only the weights you use (`next/font` subsetting) — an unused weight is dead bytes ([`performance`](../performance/SKILL.md)).

Rules: sizes come from scale tokens (never a literal `fontSize: 17` in `sx` or `font-size: 17px` in a module); headings carry hierarchy globally; one ratio + one base app-wide.

## Dark mode

Dark mode is a **token swap**, not a per-component `dark:` sprinkle. Toggle a class/attribute on `<html>` (driven by **`next-themes`**, or the library's color-mode API) and redefine the tokens:

```css
:root { --color-surface: #ffffff; --color-text: #1a1a27; }              /* light (default) */
.dark { --color-surface: #1a1a27; --color-text: #f2f2f7; }             /* next-themes attribute="class" */
@media (prefers-color-scheme: dark) {
  :root:not(.light) { --color-surface: #1a1a27; --color-text: #f2f2f7; }  /* follow OS unless user pinned light */
}
```

Rules:
- **Dark mode is a deliberately-authored second palette, not an inversion.** Never `filter: invert()` or algorithmically negate hex. **Desaturate accents** (saturated brand colors vibrate on dark surfaces), **avoid pure `#000`** (a very dark neutral reads better and lets shadows show), and **re-verify every contrast pair** — a ratio that passes on white routinely fails on dark, so it needs its own [`accessibility`](../accessibility/SKILL.md) pass. (The taste decision is [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s; this is mechanics.)
- **Follow OS by default (`prefers-color-scheme`), let the user override, persist it.** `next-themes` with `defaultTheme="system"` does exactly this; the persisted choice wins over the media query.
- **Stamp the class before first paint.** `next-themes` injects a tiny pre-hydration script and you set `suppressHydrationWarning` on `<html>` — this is what prevents the light→dark flash. Don't hand-roll it.
- **Zero component changes.** Because everything reads tokens, dark mode needs no per-component CSS — if a component needs a dark-specific rule, its color escaped into a literal. Fix the token.
- **With a library, drive dark mode from its color-mode toggle** (MUI `useColorScheme`, Mantine `useMantineColorScheme`, Chakra via `next-themes`) and keep the `.dark` attribute in sync so your modules and the library agree.

## Responsive (the CSS authority only)

This skill owns only the CSS *authority* rules responsive design rides on: **mobile-first** (base styles for narrow, `min-width` media queries to add for wider), no fixed pixel heights on content regions, respect `prefers-reduced-motion`. The responsive *strategy* — the breakpoint contract, grids (library vs CSS Grid/Flexbox), cross-breakpoint alignment, container queries, patterns — is owned by [`responsive-design`](../responsive-design/SKILL.md).

## Rules

- **One styling authority** (library style API · Tailwind · CSS Modules) — never Tailwind *and* a CSS-in-JS library; [`component-library`](../component-library/SKILL.md) picks it.
- **CSS Modules by default for hand-written CSS**; `globals.css` holds *only* tokens + a minimal reset, never component styles.
- **Share via `composes` or a `className` prop**, never a descendant selector reaching a child's internals; use `:global` sparingly.
- **Design tokens as CSS custom properties**, sourced from `design/visual-identity` (primary) / `design/theme-presets` (quick-start); modules consume `var(--token)`, never literals; functional tokens **named by purpose** (`--color-danger`), distinct from brand tokens; **bridged to one source** with the library theme.
- **Type as a system, not a font** — one modular scale + base as tokens, headings carry hierarchy globally, display sizes fluid via `clamp()`, fonts via `next/font`, two–three weights, sizes from scale tokens.
- **Dark mode = a deliberately-authored second palette** (desaturated accents, no pure black, contrast re-verified) swapped via `next-themes`/the library toggle — never an inversion; stamped before paint, user override persisted and winning.
- **Mobile-first responsive** (the breakpoint contract itself → [`responsive-design`](../responsive-design/SKILL.md)).

## What NOT to do

- No component styles in `globals.css` ("global-stylesheet dumping") — scope them in a module.
- No hardcoded hex/px colors in `*.module.css` or `sx` — use tokens.
- No descendant selector reaching past a child's contract — expose a `className`/prop.
- No Tailwind layered onto MUI/Mantine/Chakra — pick one authority.
- No two color systems (library tokens *and* your own diverging) — bridge to one source.
- No value-named functional tokens (`--color-red` for danger) — name by purpose.
- No dark mode by inversion (`filter: invert()` / negated hex) — author a second palette and re-check contrast.
- No hand-rolled theme flash-guard — use `next-themes`; no raw `<link>` Google Fonts — use `next/font`.

## Validation

- `pnpm build` + typecheck clean; `globals.css` holds only tokens + reset (no component rules).
- Toggle dark mode → colors flip with **no** component CSS changes and **no** light→dark flash on reload.
- Grep `*.module.css` (and `sx` literals) for hex/`px` colors → none (all `var(--token)`).
- Only one styling authority present (no Tailwind + CSS-in-JS library together).
- Resize to mobile width → layout reflows via `min-width` queries, no horizontal scroll.

## Handoffs

- Component library's own theme object (MUI `createTheme`, Mantine/Chakra tokens, Tailwind-as-authority for shadcn) → [`component-library`](../component-library/SKILL.md)
- Palette, fonts, visual direction, the *type treatment* → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) (primary), `design/theme-presets` (quick-start)
- Contrast/WCAG check of chosen colors, focus-visible styling → [`accessibility`](../accessibility/SKILL.md)
- Breakpoint contract, grids, cross-breakpoint alignment, container queries → [`responsive-design`](../responsive-design/SKILL.md)
- Font/static-asset performance, bundle → [`performance`](../performance/SKILL.md)
- Component/layout structure (composition, slots) → [`basics`](../basics/SKILL.md)
