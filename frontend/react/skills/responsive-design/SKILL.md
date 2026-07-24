---
name: fe-react-responsive-design
description: Use when a layout must adapt across screen sizes — the breakpoint contract (theme values + one TS mirror), library grid/`useMediaQuery` vs your own CSS Grid/Flexbox, alignment across breakpoint flips, container queries, and the SSR caveat (JS breakpoint hooks mismatch on hydrate). Triggers: "make this page responsive", "define our breakpoints", "the layout breaks on tablet", "horizontal scrollbar on mobile". Do NOT use for token/dark-mode mechanics (`styling`) or testing breakpoints (qa `responsive-testing`, a peer).
---

# React — Responsive design (breakpoints, grids, cross-breakpoint alignment)

Owns **how a React app adapts to viewport width**: the breakpoint contract, the layout system that reflows
(library grid vs your own CSS), the patterns (nav collapse, table→card, drawer), and the discipline that keeps
elements **aligned with each other when a breakpoint flips**. [`styling`](../styling/SKILL.md) owns the CSS
mechanics this rides on (CSS Modules, tokens, mobile-first); this skill owns the responsive *strategy and layout*.

**Version rule:** everything here is CSS/markup-level and identical across React 18/19 and Next 14/15. The one
version-sensitive edge is the **RSC/SSR caveat** (below): a JS breakpoint hook must run in a Client Component and
guard against the server↔client hydration mismatch — the React analog of Blazor's static-SSR-knows-no-viewport rule.

## When to use / NOT use

- Use for: defining breakpoints, building/reflowing layouts, responsive component variants, alignment drift
  between breakpoints, hiding/showing per width, container queries.
- NOT for: CSS Modules, tokens, dark mode → [`styling`](../styling/SKILL.md) · library install/theme →
  [`component-library`](../component-library/SKILL.md) · zoom/reflow a11y (WCAG 1.4.10), touch targets →
  [`accessibility`](../accessibility/SKILL.md) · verifying it → qa `responsive-testing` (peer, see handshake).

## The breakpoint contract — one definition, three consumers

Breakpoints are a **contract**, not a per-file choice. Define them **once**, and make every consumer read that
one source: your CSS, your TS (when client components branch on width), and the QA suite.

```css
/* globals.css — with the design tokens (styling skill). Media queries can't read var(), so these are
   the DOCUMENTED source of truth; the values are repeated in queries but never invented per file. */
:root { --bp-sm: 640px; --bp-md: 768px; --bp-lg: 1024px; --bp-xl: 1280px; }
```

```ts
// breakpoints.ts — the TS mirror, for client components and shared with the QA suite
export const breakpoints = { sm: 640, md: 768, lg: 1024, xl: 1280 } as const;
```

Rules:
- **With a component library, adopt ITS breakpoints wholesale** — MUI's `theme.breakpoints.values`
  (`xs 0 / sm 600 / md 900 / lg 1200 / xl 1536`), Mantine's `theme.breakpoints`, Chakra's tokens. Your CSS-var
  block and `breakpoints.ts` **mirror the library values**; you never introduce a third set. Two breakpoint
  systems in one app = permanent near-boundary misalignment. When there's no library, the block above is the set.
- **Breakpoints are content-driven, few, and named** — add one where the *layout* breaks, not per device
  ("tablet"). 3–4 is the norm; a 5th needs a reason.
- **Mobile-first `min-width` queries only** (per [`styling`](../styling/SKILL.md)); mixing `min-` and
  `max-width` on the same boundary creates the 1px overlap/gap bugs QA's boundary tests exist to catch.

## Layout system decision — off-the-shelf grid vs your own CSS

```
Component library present (MUI / Mantine / Chakra)?
  YES → its responsive grid + visibility props are the DEFAULT for page/section layout
        (MUI `<Grid size={{ xs: 12, md: 6 }}>` · Mantine `<Grid>`/`<SimpleGrid>` · Chakra `<SimpleGrid>`).
        Drop to raw CSS Grid/Flexbox (CSS Modules) for bespoke regions the 12-col model fights.
  NO  → CSS Grid for 2-D page layout, Flexbox for 1-D rows/toolbars — in CSS Modules, tokens for gaps.
Component must adapt to its CONTAINER (card in sidebar vs main)? → container query, either branch.
```

| Tool | Use for | Not for |
|---|---|---|
| Library grid (`MUI Grid`/`Mantine Grid`/`Chakra SimpleGrid`) | Page/section scaffolding, forms, card grids | Pixel-precise bespoke regions; nested grids >2 deep |
| Library visibility (`sx={{ display: { xs: 'none', md: 'block' } }}`, Mantine `visibleFrom`/`hiddenFrom`) | Hiding whole regions per breakpoint in library-heavy markup | Fine-grained styling (that's CSS) |
| **CSS Grid** (CSS Modules) | 2-D bespoke layout; `auto-fit`/`minmax` self-reflowing card grids | — |
| **Flexbox** | 1-D rows: toolbars, nav, button groups | Whole-page 2-D layout |
| **Container queries** (`container-type: inline-size`) | Reusable components that must adapt to *where they sit* | Page-level layout (viewport queries) |

Prefer **intrinsically responsive** CSS that needs no breakpoint at all — it can't misalign at a boundary, and it
works in a Server Component with zero JS:

```css
/* ProductGrid.module.css — reflows 4→3→2→1 with zero media queries, no JS */
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: var(--space-4); }
```

## Cross-breakpoint alignment — one grid owns the layout

The "elements drift apart when the screen shrinks" bug has one root cause: **siblings each carrying their own
media queries** instead of one parent owning the geometry. The fix is structural:

- **One grid container per region owns columns and gaps; children only span tracks.** When the breakpoint flips,
  the *container's* `grid-template-columns` changes once and every child reflows together — nothing can drift.
- **Shared edges come from shared tracks/tokens**, never per-child margins tuned per breakpoint. Gutters are
  `gap: var(--space-*)` on the container; a child with its own `margin-left` compensation is the smell.
- **Never reposition siblings independently at a breakpoint** (`.a { margin-top: 12px }` at `md` to "line up"
  with `.b`). If two elements must stay aligned, put them in the same grid and let `grid-row`/`grid-column`
  express it.
- Reordering at a breakpoint uses `grid-template-areas` (or grid `order` sparingly) — **DOM order stays the
  reading/tab order** ([`accessibility`](../accessibility/SKILL.md) owns why; visual `order` never reorders focus).
- No fixed pixel widths/heights on content regions — `minmax()`, `fr`, and content sizing; a fixed width is what
  *forces* overflow at the next width down.

## Responsive patterns

| Pattern | Recipe |
|---|---|
| **Nav collapse** (full bar ⇄ hamburger/drawer) | The **hamburger is a small-screen affordance, not a default** — show top-level items as a visible horizontal bar wherever there's room ([`ui-conventions`](../ui-conventions/SKILL.md): don't hide nav when you can show it), collapse to the drawer only **below** the nav breakpoint. Prefer a **CSS visibility swap** (both variants in markup, media query flips them) so it works in a Server Component with no JS; the drawer open state is the only `'use client'` part. Library: MUI `Drawer` + `useMediaQuery`, Mantine `Burger` + `Drawer`. |
| **Sticky header** | `position: sticky; top: 0` (pure CSS, SSR-safe) improves reach to nav/actions on long pages; keep it **short**, optionally shrink on scroll (an `IntersectionObserver` in a `'use client'` component, listener cleaned up in the effect's return). Don't make it so tall it eats the mobile viewport. |
| **Table → cards** on narrow | Prefer one structure restyled with CSS (grid-areas per row); a genuinely different mobile DOM is a per-surface decision — mind duplicate-content cost. Library grids: hide low-value columns first per breakpoint ([`ui-conventions`](../ui-conventions/SKILL.md) owns which columns matter). |
| **Sidebar → drawer / stacked** | Grid container swaps `grid-template-areas` at the breakpoint; the sidebar component itself is unchanged. |
| **Form density** | Multi-column library/CSS grid collapsing to one column; labels stay above inputs at all widths (no layout-dependent label position). |
| **Images/media** | Next `<Image>` with `sizes` (or `max-width: 100%; height: auto` for plain `<img>`); weight/`srcset` → [`performance`](../performance/SKILL.md). |

## JS breakpoint logic, SSR and hydration — the React-specific caveat

CSS handles ~90% of responsive. For the rest (structurally different DOM per width) React offers **JS breakpoint
hooks** — MUI `useMediaQuery`, Mantine `useMatches`/`use-media-query`, or your own `matchMedia` hook. They are
**client-only and hydration-sensitive**:

- **Server Components / SSR know nothing about the viewport.** They render once on the server with no window. Any
  width-dependent branching must be **pure CSS** on a server-rendered surface, or gated to run after mount in a
  Client Component. A `useMediaQuery` called during SSR returns its default (usually `false`) on the server.
- **Hydration mismatch.** If the server renders the `false` branch and the client's first render (before effects
  run) disagrees, React logs a hydration mismatch and may flash the wrong variant. Fixes: prefer the **CSS
  visibility swap** (no JS, no mismatch); or in MUI set `useMediaQuery(query, { defaultMatches, ssrMatchMedia })`
  / render the width-dependent region only after a mount guard (`useState(false)` → `useEffect(() => setMounted(true))`),
  accepting a one-frame mobile-first default. Pick the **mobile-first default variant** for the server render.
- **CSS-swap duplicates DOM; JS-swap runs only after mount.** Duplicate both variants in markup (CSS swap) when
  the region is small (nav links); for big surfaces (two table layouts) prefer one restyled structure, and only
  reach for a JS swap in an already-`'use client'` surface.
- **Clean up `matchMedia` listeners** in the effect's return — a resize/`matchMedia` listener leaking across
  navigations is a classic memory leak ([`performance`](../performance/SKILL.md)); the library hooks do this for you.

## The QA handshake

The qa peer skill `qa/typescript/skills/responsive-testing` boundary-tests (bp−1/bp) whatever this skill defines.
Make that possible:

- **Publish the breakpoint contract** — the token block + `breakpoints.ts` mirror above is exactly what the QA
  suite imports (or reads from `theme.breakpoints.values`); changing a breakpoint without telling QA breaks the
  boundary matrix, so it lives in one reviewed place.
- **Both variants of a swap carry stable, variant-suffixed testids** (`Nav.Desktop` / `Nav.Hamburger`) — per
  [`testability`](../testability/SKILL.md). QA asserts the visible one **and** the hidden one; unlabeled variants
  make that impossible.
- Every width must hold the invariant QA checks everywhere: **no horizontal overflow**.

## Rules

- **One breakpoint set app-wide**, documented as CSS vars + a TS mirror; with a library, *its* values are the set.
- **Mobile-first `min-width` only**; never `min-`+`max-` on one boundary.
- **Intrinsic CSS (`auto-fit`/`minmax`, flex-wrap) before breakpoints; container queries for
  container-dependent components; media queries last; JS breakpoint hooks only when DOM must differ.**
- **One grid container owns each region's geometry** — children span tracks, never self-position per breakpoint.
- **Server-rendered surfaces are CSS-responsive only**; JS breakpoint hooks run in `'use client'` with a
  hydration-safe, mobile-first default and cleaned-up listeners.
- **Variant swaps: both variants testid-labeled**; DOM order = reading order when visual order changes.
- No fixed dimensions on content regions; images responsive (`sizes`/`max-width: 100%`).

## What NOT to do

- No second (or third) breakpoint system next to the library's.
- No magic width numbers scattered in modules — boundary values appear only as the documented set (or `theme.breakpoints`).
- No per-sibling margin tuning to "re-align" elements at a breakpoint — restructure into one grid.
- No `useMediaQuery` driving layout on an SSR surface without a mount guard / `ssrMatchMedia` (hydration mismatch, wrong-variant flash).
- No duplicated full-page DOM variants for big surfaces — restyle one structure.
- No desktop-first `max-width` cascades bolted onto a mobile-first codebase.
- No visual `order`/`grid-area` reshuffle that leaves focus order wrong — DOM order is the reading order.

## Validation

- Resize from 320px to 4k: no horizontal scrollbar at any width; every swap flips exactly at its documented
  boundary (check bp−1/bp by hand — QA automates it).
- Grep modules for `@media` width values → only the documented set appears.
- View a server-rendered page with JS disabled → layout still correct at mobile and desktop widths.
- A `useMediaQuery`-branching client component → no hydration-mismatch warning, no wrong-variant flash on load.

## Handoffs

- CSS Modules mechanics, tokens, mobile-first authority → [`styling`](../styling/SKILL.md)
- Library grid component APIs, theming, `useMediaQuery` setup → [`component-library`](../component-library/SKILL.md)
- Which table columns/actions survive narrow widths → [`ui-conventions`](../ui-conventions/SKILL.md)
- Zoom/reflow (WCAG 1.4.10), touch targets, DOM-order-vs-visual-order → [`accessibility`](../accessibility/SKILL.md)
- Responsive image weight, listener leaks from resize hooks → [`performance`](../performance/SKILL.md)
- Verifying all of it by shrinking the browser → qa `responsive-testing` (peer agent's Phase 3)
