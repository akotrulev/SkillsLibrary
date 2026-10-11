---
name: styling
description: Use when styling a Blazor app (.NET 8/9/10) with CSS — CSS isolation (`.razor.css`) and `::deep`, design tokens as CSS custom properties, a type scale (`clamp()`), dark mode, and the CSS-isolation-vs-Tailwind decision. Triggers: "scope this component's CSS", "why doesn't my `::deep` selector work", "set up design tokens in Blazor", "dark mode with CSS". Do NOT use for a component library's own theme system (`component-library`) or the palette/font design itself (`design/visual-identity`).
---

# Blazor — Styling (CSS isolation, tokens, dark mode)

Owns how a Blazor app is styled with **CSS you write**: component-scoped isolation, design tokens, dark mode, responsive rules. It does **not** own a component library's theme system — that's [`component-library`](../component-library/SKILL.md); this skill layers your own CSS *on top of or instead of* a library.

**Version rule:** CSS isolation, `::deep`, and `.razor.css` bundling behave the same across net8/net9/net10 — this skill is largely version-agnostic. The one delta: net10's fingerprinted/precompressed static assets change how the bundled `{Project}.styles.css` is served (perf, not authoring) — see [`performance`](../performance/SKILL.md).

## When to use

- Scoping a component's CSS so it can't leak or collide
- Reaching a child element's DOM from scoped CSS (`::deep`)
- Setting up design tokens (CSS custom properties) from a `design/theme-presets` palette
- Dark mode, responsive breakpoints
- Deciding CSS isolation vs Tailwind (or how they coexist)

## When NOT to use

- A component library's theme/token system (MudBlazor `MudTheme`, Fluent tokens, Radzen `--rz-*`) → [`component-library`](../component-library/SKILL.md)
- Picking the palette, fonts, visual direction, type *treatment* → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) (primary theming authority), `design/theme-presets` (optional quick-start)
- Contrast/WCAG auditing of the colors you chose → [`accessibility`](../accessibility/SKILL.md)
- Layout *component* structure (templates, slots) → [`basics`](../basics/SKILL.md) layering

## The styling authority decision

Pick **one** primary styling authority per app. Mixing them uncontrolled is the top cause of specificity wars and dark-mode drift.

```
Are you using a component library (MudBlazor/Fluent/Radzen)?
  YES → library theme is the authority; your CSS is ISOLATION-ONLY for gaps/layout.
        Do NOT bolt Tailwind on top — its reset + utilities fight the library theme.
  NO ↓
Is the design a bespoke design system with heavy custom layout?
  YES + team fluent in utility CSS → Tailwind (global build) as the authority.
  YES + prefer component-scoped C#-adjacent CSS → CSS isolation + design tokens (default).
```

| Approach | Scope | Use when | Cost |
|---|---|---|---|
| **CSS isolation** (`.razor.css`) | Per component, auto-scoped | **Default.** Any Blazor app; especially alongside a component library | Verbose for cross-cutting utilities |
| **Design tokens** (CSS custom properties) | Global vars, consumed everywhere | **Always** — the theming backbone under either approach | None; do this regardless |
| **Tailwind** (utility-first, global build) | Global utilities | Bespoke design, no component library, team wants utilities | Reset fights component libraries; build step; `::deep` interplay |
| **Global stylesheet dumping** | Global, unscoped | **Never** for component styles | Collisions, dead CSS, no ownership |

**Default = CSS isolation + design tokens.** Add Tailwind only in the "no component library + bespoke" branch. Never mix Tailwind *with* a component library.

## CSS isolation — `.razor.css`

A `Counter.razor.css` next to `Counter.razor` is auto-scoped: the build rewrites its selectors with a generated `[b-xxxxxxxxxx]` attribute so they match only that component's elements. Blazor bundles all of them into `{Project}.styles.css`, referenced once in `App.razor`:

```html
<link rel="stylesheet" href="@Assets["MyApp.styles.css"]" />   @* net8+: <link href="MyApp.styles.css"> — net10 Assets[] adds fingerprinting *@
```

Rules:
- **Scoped selectors only match this component's own markup** — not child components' markup (that's what `::deep` is for) and not raw HTML rendered by a child.
- **Don't over-qualify.** Inside `Card.razor.css`, `.title { }` already scopes to this component — no need for `.card .title`.
- **No `@page`/route knowledge in CSS** — style by structure, not by URL.
- Keep the isolated file to *this component's* concerns; shared primitives go in the design-token layer, not copied into each `.razor.css`.

## `::deep` — reaching child DOM from scoped CSS

The scope attribute lands on **your component's own** elements. To style DOM rendered by a *child* component (or a library control) from your scoped file, use `::deep` — it applies the scope to a **parent** you own, then matches descendants unscoped:

```css
/* Parent.razor.css — style a child component's rendered button */
::deep .child-action { color: var(--color-primary); }   /* matches descendants of Parent's scoped root */
```

Rules + gotchas:
- **`::deep` must follow an element your component actually renders.** A bare `::deep .x` at the top of the file needs your component to have a single scoped root wrapping the children; if your component renders a `RenderFragment` with no owned wrapper, there's no scoped ancestor for `::deep` to hang off and it silently matches nothing. Wrap children in an owned element (`<div class="host">`) and write `.host ::deep .x`.
- **`::deep` reaches into child components — that's coupling.** Prefer giving the child a `[Parameter] class`/`Class` or a CSS-variable hook it consumes internally. Use `::deep` when you don't own the child's API (a library control) — not to reach past your own components' contracts.
- `::deep` only works in **isolated** (`.razor.css`) files, not global CSS.

## Design tokens — the theming backbone

Define the palette/spacing/typography once as **CSS custom properties**, and reference `var(--token)` everywhere (isolated files and global). This is the seam where the visual direction enters the codebase — map [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s per-brief token system (the primary authority; or a `design/theme-presets` preset for a quick-start) — palette hex + font pairing — to tokens. The *system* rules below (tier model, purpose-naming, categories, theming-as-swap-set) are the stack-agnostic discipline owned by [`design/design-tokens`](../../../../design/design-tokens/SKILL.md) — this section is the Blazor **mechanics** that render that system as CSS; defer the structure questions (how many tiers, how to name, DTCG-or-not) there and keep only CSS-isolation specifics here:

```css
/* app.css (global) — the ONLY thing that legitimately lives global */
:root {
  --color-primary: #1867c0;
  --color-surface: #ffffff;
  --color-text: #1a1a27;
  --color-text-muted: #5a5a6e;
  --space-1: .25rem; --space-2: .5rem; --space-4: 1rem;
  --font-body: "Roboto", system-ui, sans-serif;
  --radius: .5rem;
}
```

Rules:
- **Isolated component CSS consumes tokens, never hardcoded hex.** `color: var(--color-text)` — a literal `#333` in a `.razor.css` is a token that escaped.
- **Name functional tokens by purpose, not value.** `--color-danger` / `--color-surface-raised` / `--color-action-primary`, never `--color-red` / `--color-blue-500`. Purpose-named tokens keep meaning stable when the theme changes and make an accessibility fix a one-line edit; a value-named token is a literal wearing a variable's clothes. Keep the semantic set (success / warning / danger / info) separate from brand tokens so the two can't collide (the brand-vs-functional split is [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s decision).
- **One token set app-wide.** No per-feature palette forks.
- When a component library is present, **bridge**: set your tokens *from* the library's variables (or vice-versa) at `:root` so there's one source of truth, not two color systems (see [`component-library`](../component-library/SKILL.md)).

## Type scale & hierarchy

Typography is where `design/visual-identity`'s taste ("the type treatment is a memorable part of the design") becomes tokens. That skill decides the *treatment* — the display/body pairing, the personality; this section is the *mechanics* that encode it: a scale, a hierarchy, responsive sizing, and weight/tracking discipline. Layer it on the `--font-*` seam the token block already has — a single `--font-body` value is a font, not a type *system*.

**A modular scale as tokens.** Pick one ratio (1.2 minor-third for dense UI, 1.25 major-third, 1.333 perfect-fourth for editorial) and generate steps from one base, so every size is a deliberate rung, not an ad-hoc `px`:

```css
:root {
  --font-display: "Fraunces", Georgia, serif;   /* the characterful face, used with restraint */
  --font-body:    "Inter", system-ui, sans-serif;
  --font-mono:    ui-monospace, "SF Mono", monospace;   /* captions/data if the brief needs it */

  --text-base: 1rem;              /* the anchor; everything derives from it */
  --ratio: 1.25;
  --text-sm:   calc(var(--text-base) / var(--ratio));
  --text-lg:   calc(var(--text-base) * var(--ratio));
  --text-xl:   calc(var(--text-lg)   * var(--ratio));
  --text-2xl:  calc(var(--text-xl)   * var(--ratio));
  --text-3xl:  calc(var(--text-2xl)  * var(--ratio));

  --leading-tight: 1.15;   /* headings */
  --leading-body:  1.5;    /* body — looser for readability */
  --tracking-tight: -0.02em;   /* large display sizes need negative tracking */
}
```

**Heading hierarchy is structural, not cosmetic.** Map the scale steps onto real heading levels once, globally, so `<h1>`–`<h4>` carry the hierarchy and components don't re-pick sizes. One `<h1>` per page (also the [`accessibility`](../accessibility/SKILL.md) `FocusOnNavigate` target); never skip a level for size — restyle, don't relabel.

```css
h1 { font-family: var(--font-display); font-size: var(--text-3xl); line-height: var(--leading-tight); letter-spacing: var(--tracking-tight); }
h2 { font-family: var(--font-display); font-size: var(--text-2xl); line-height: var(--leading-tight); }
h3 { font-size: var(--text-xl); line-height: var(--leading-tight); font-weight: 600; }
body { font-family: var(--font-body); font-size: var(--text-base); line-height: var(--leading-body); }
```

**Responsive type with `clamp()`** — the display sizes should fluidly scale between mobile and desktop instead of stepping at each breakpoint. Bound both ends so it never gets illegibly small or absurdly large:

```css
:root { --text-3xl: clamp(2rem, 1.4rem + 3vw, 3.5rem); }   /* min, preferred (fluid), max */
```

**Weight & tracking discipline.**
- Two or three weights, not six — a display weight, a body weight, and maybe a medium for emphasis. Every extra weight is a font-load cost and a decision to keep consistent.
- Large display text wants **negative** letter-spacing (`--tracking-tight`); small caps/labels want slightly **positive** tracking. Body text: leave tracking at `0`.
- Body line-height looser (~1.5) than headings (~1.15). Cap measure at ~66ch (`max-width: 66ch`) on long-form text so lines don't sprawl.
- Load only the weights/styles you use (`font-display: swap`, subset if self-hosting) — an unused weight is dead bytes, a [`performance`](../performance/SKILL.md) concern.

Rules:
- **Sizes come from the scale tokens**, never a literal `font-size: 17px` in a `.razor.css` (same escape as a hex literal).
- **Headings carry hierarchy globally** — components consume `<h2>`/`<h3>`, they don't set heading sizes locally.
- **One ratio, one base** app-wide; a per-feature type scale fork is the typographic version of a palette fork.

## Dark mode

Dark mode is a **token swap**, not a per-component `dark:` sprinkle. Toggle a `data-theme` attribute on `<html>` and redefine the tokens:

```css
:root { --color-surface: #ffffff; --color-text: #1a1a27; }              /* light (default) */
:root[data-theme="dark"] { --color-surface: #1a1a27; --color-text: #f2f2f7; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --color-surface: #1a1a27; --color-text: #f2f2f7; }  /* follow OS unless user pinned light */
}
```

Rules:
- **Dark mode is a second palette, not an inversion.** Never programmatically flip the light values (`filter: invert()`, or an algorithm that negates each hex). Author the dark tokens deliberately: **desaturate accents** (fully-saturated brand colors vibrate on dark surfaces), **avoid pure `#000`** surfaces (a very dark neutral like `#1a1a27` reads better and lets shadows show), and **re-verify every contrast pair** — a ratio that passes on white routinely fails on a dark surface, so this needs its own [`accessibility`](../accessibility/SKILL.md) pass, not a reuse of the light-mode result. (The *taste* decision that dark mode is a separate palette is [`design/visual-identity`](../../../../design/visual-identity/SKILL.md)'s; this is the mechanics.)
- **Follow OS preference by default (`prefers-color-scheme`), let the user override, persist the override.** The persisted choice wins over the media query (hence `:not([data-theme="light"])`).
- **Set the attribute before first paint** to avoid a light→dark flash — a tiny inline script in `App.razor` `<head>` that reads localStorage/`prefers-color-scheme` and stamps `data-theme` synchronously. (This is the one place a pre-render inline script is justified.)
- Because everything reads tokens, dark mode needs **zero** changes in component CSS — if a component needs a `dark:`-specific rule, its color escaped into a literal. Fix the token, not the component.
- With a component library, drive dark mode from **its** theme toggle (`MudThemeProvider IsDarkMode`, `FluentDesignTheme Mode`, Radzen `ThemeService`) and mirror the `data-theme` attribute so your isolated CSS and the library agree.

## Responsive

This skill owns only the CSS *authority* rules responsive design rides on: **mobile-first** (base styles for narrow, `min-width` media queries to add for wider), no fixed pixel heights on content regions, respect `prefers-reduced-motion`. The responsive *strategy* — the breakpoint contract, grid systems (library vs CSS Grid/Flexbox), cross-breakpoint alignment, container queries, responsive patterns — is owned by [`responsive-design`](../responsive-design/SKILL.md).

## Rules

- **One styling authority** (library theme · CSS isolation+tokens · Tailwind) — never Tailwind *and* a component library.
- **CSS isolation by default**; global stylesheet holds *only* tokens + a minimal reset, never component styles.
- **`::deep` only off an element you own**, and prefer a child `Class`/CSS-var API over reaching in.
- **Design tokens as CSS custom properties**, sourced from `design/visual-identity` (primary) / `design/theme-presets` (quick-start); isolated CSS consumes `var(--token)`, never literals; functional tokens **named by purpose** (`--color-danger`), not value (`--color-red`), and kept distinct from brand tokens.
- **Type as a system, not a font** — one modular scale + one base as tokens, headings carry hierarchy globally (`<h1>`–`<h4>`, one `<h1>` per page), display sizes fluid via `clamp()`, two–three weights, sizes from scale tokens never literal `px`.
- **Dark mode = a deliberately-authored second palette** (desaturated accents, no pure black, contrast re-verified) swapped via `data-theme` + `prefers-color-scheme` — never an inversion; set before first paint, user override persisted and winning.
- **Mobile-first responsive**, breakpoints consistent app-wide (the breakpoint contract itself → [`responsive-design`](../responsive-design/SKILL.md)).

## What NOT to do

- No component styles in the global stylesheet ("global-stylesheet dumping") — scope them.
- No hardcoded hex/px colors in `.razor.css` — use tokens.
- No `::deep` at the top of a file with no owned scoped ancestor (matches nothing).
- No `::deep` to reach past your *own* components' parameter contracts (coupling) — expose a `Class`/variable.
- No Tailwind layered onto MudBlazor/Fluent/Radzen — pick one authority.
- No two color systems (library tokens *and* your own diverging) — bridge to one source.
- No value-named functional tokens (`--color-red` for danger) — name by purpose so a theme swap keeps meaning.
- No dark mode by inversion (`filter: invert()` / negated hex) — author a second palette and re-check contrast.
- No dark-mode flash — stamp `data-theme` before first paint.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- `dotnet build` — the bundled `{Project}.styles.css` is generated and linked once in `App.razor`.
- Toggle dark mode → colors flip with **no** component CSS changes and **no** light→dark flash on reload.
- Grep isolated `.razor.css` files for hex literals and `px` colors → none (all `var(--token)`).
- No component-specific rules in the global stylesheet (only tokens + reset).
- Resize to mobile width → layout reflows via `min-width` queries, no horizontal scroll.

## Handoffs

- Component library's own theme (MudTheme, Fluent tokens, Radzen themes) → [`component-library`](../component-library/SKILL.md)
- Palette, fonts, visual direction, the *type treatment* (which faces, what personality) → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) (primary), `design/theme-presets` (quick-start)
- Contrast/WCAG check of chosen colors, focus-visible styling → [`accessibility`](../accessibility/SKILL.md)
- Breakpoint contract, grids, cross-breakpoint alignment, container queries → [`responsive-design`](../responsive-design/SKILL.md)
- Static-asset fingerprinting/compression of the styles bundle → [`performance`](../performance/SKILL.md)
- Component/layout structure (templates, slots) → [`basics`](../basics/SKILL.md)
