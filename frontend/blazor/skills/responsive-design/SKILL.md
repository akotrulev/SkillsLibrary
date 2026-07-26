---
name: fe-blazor-responsive-design
description: Use when making a Blazor app (.NET 8/9/10) responsive — the breakpoint contract (tokens + one C# mirror), library grid (MudGrid/FluentGrid/Radzen) vs your own CSS Grid/Flexbox, alignment across breakpoint flips, container queries, and the render-mode caveat (static SSR = CSS-only). Triggers: "make this page responsive", "define our breakpoints", "the layout breaks on tablet", "MudGrid or CSS grid". Do NOT use for token/dark-mode mechanics (`styling`) or testing (qa `responsive-testing`).
---

# Blazor — Responsive design (breakpoints, grids, cross-breakpoint alignment)

Owns **how a Blazor app adapts to viewport width**: the breakpoint contract, the layout system that reflows
(library grid vs your own CSS), the patterns (nav collapse, table→card, drawer), and the discipline that keeps
elements **aligned with each other when a breakpoint flips**. [`styling`](../styling/SKILL.md) owns the CSS
mechanics this rides on (isolation, tokens, mobile-first); this skill owns the responsive *strategy and layout*.

**Version rule:** everything here is CSS/markup-level and identical across net8/net9/net10. The one
version-sensitive edge: render modes (below) follow the project's TFM per [`basics`](../basics/SKILL.md).

## When to use / NOT use

- Use for: defining breakpoints, building/reflowing layouts, responsive component variants, alignment drift
  between breakpoints, hiding/showing per width, container queries.
- NOT for: CSS isolation, tokens, dark mode → [`styling`](../styling/SKILL.md) · library install/theme →
  [`component-library`](../component-library/SKILL.md) · zoom/reflow a11y (WCAG 1.4.10), touch targets →
  [`accessibility`](../accessibility/SKILL.md) · verifying it → qa `responsive-testing` (peer, see handshake).

## The breakpoint contract — one definition, three consumers

Breakpoints are a **contract**, not a per-file choice. Define them **once**, and make every consumer read that
one source: your CSS, your C# (when interactive components branch on width), and the QA suite.

```css
/* app.css — with the design tokens (styling skill). Media queries can't read var(), so these are
   the DOCUMENTED source of truth; the values are repeated in queries but never invented per file. */
:root { --bp-sm: 640px; --bp-md: 768px; --bp-lg: 1024px; --bp-xl: 1280px; }
```

```csharp
// Breakpoints.cs — the C# mirror, for interactive components and shared with the QA suite
public static class Breakpoints { public const int Sm = 640, Md = 768, Lg = 1024, Xl = 1280; }
```

Rules:
- **With a component library, adopt ITS breakpoints wholesale** (MudBlazor sm 600 / md 960 / lg 1280 / xl 1920;
  Fluent mirrors it; Radzen sm 576 / md 768 / lg 1024 / xl 1920 — verify against the installed version). Two
  breakpoint systems in one app = permanent near-boundary misalignment. Your tokens *mirror* the library's
  values; you never introduce a third set. (React counterpart, for `frontend/react/` later: Material UI's
  `theme.breakpoints.values` plays the same role.)
- **Breakpoints are content-driven, few, and named** — add one where the *layout* breaks, not per device
  ("tablet"). 3–4 is the norm; a 5th needs a reason.
- **Mobile-first `min-width` queries only** (per [`styling`](../styling/SKILL.md)); mixing `min-` and
  `max-width` on the same boundary creates the 1px overlap/gap bugs QA's boundary tests exist to catch.

## Layout system decision — off-the-shelf grid vs your own CSS

```
Component library present (MudBlazor / Fluent / Radzen)?
  YES → its 12-column grid + visibility helpers are the DEFAULT for page/section layout
        (MudGrid + MudItem xs/sm/md · FluentGrid + FluentGridItem · RadzenRow + RadzenColumn).
        Drop to raw CSS Grid/Flexbox (isolated CSS) for bespoke regions the 12-col model fights.
  NO  → CSS Grid for 2-D page layout, Flexbox for 1-D rows/toolbars — in isolated CSS, tokens for gaps.
Component must adapt to its CONTAINER (card in sidebar vs main)? → container query, either branch.
```

| Tool | Use for | Not for |
|---|---|---|
| Library grid (`MudGrid`/`FluentGrid`/`RadzenRow`) | Page/section scaffolding, forms, card grids | Pixel-precise bespoke regions; nested grids >2 deep |
| Library visibility (`MudHidden`, breakpoint props) | Hiding whole regions per breakpoint in library-heavy markup | Fine-grained styling (that's CSS) |
| **CSS Grid** (isolated) | 2-D bespoke layout; `auto-fit`/`minmax` self-reflowing card grids | — |
| **Flexbox** | 1-D rows: toolbars, nav, button groups | Whole-page 2-D layout |
| **Container queries** (`container-type: inline-size`) | Reusable components that must adapt to *where they sit* | Page-level layout (viewport queries) |

Prefer **intrinsically responsive** CSS that needs no breakpoint at all — it can't misalign at a boundary:

```css
/* ProductGrid.razor.css — reflows 4→3→2→1 with zero media queries */
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
  reading/tab order** ([`accessibility`](../accessibility/SKILL.md) owns why).
- No fixed pixel widths/heights on content regions — `minmax()`, `fr`, and content sizing; a fixed width is what
  *forces* overflow at the next width down.

## Responsive patterns

| Pattern | Recipe |
|---|---|
| **Nav collapse** (full bar ⇄ hamburger/drawer) | The **hamburger is a small-screen affordance, not a default** — show the top-level items as a visible horizontal bar wherever there's room ([`ui-rules`](../ui-rules/SKILL.md): don't hide nav when you can show it), collapse to the drawer only **below** the nav breakpoint. Both variants in markup, CSS swaps visibility at the breakpoint (works under static SSR); the drawer open state is the only interactive part. Library: `MudAppBar` + `MudDrawer` with its `Breakpoint` prop. |
| **Sticky header** | `position: sticky; top: 0` on the header (pure CSS, static-SSR-safe) improves reach to nav/actions on long pages; keep the sticky bar **short** and consider shrinking it on scroll (a class toggled from an `IntersectionObserver`/scroll interop — interactive-only, disposed like any resize interop). Don't make it so tall it eats the mobile viewport. |
| **Table → cards** on narrow | Prefer one structure restyled with CSS (grid-areas per row); a genuinely different mobile DOM is a per-surface decision — mind duplicate-content cost below. Library grids: column `Hidden`/breakpoint props drop low-value columns first ([`ui-rules`](../ui-rules/SKILL.md) owns which columns matter). |
| **Sidebar → drawer / stacked** | Grid container swaps `grid-template-areas` at the breakpoint; the sidebar component itself is unchanged. |
| **Form density** | Multi-column `MudGrid`/CSS grid collapsing to one column; labels stay above inputs at all widths (no layout-dependent label position). |
| **Images/media** | `max-width: 100%; height: auto;` always; `srcset`/`sizes` for weight → [`performance`](../performance/SKILL.md). |

## C# breakpoint logic and render modes — the Blazor-specific caveat

CSS handles ~90% responsive. For the rest (structurally different DOM per width) Blazor offers **C# breakpoint
services** — `MudBreakpointProvider`/`IBreakpointService`, Fluent's viewport callbacks, or your own
`matchMedia` JS interop. They are **interactive-only**:

- **Static SSR renders once on the server and knows nothing about the viewport.** On static-SSR surfaces (the
  default per [`project-setup`](../project-setup/SKILL.md)) responsive behavior must be **pure CSS**. A
  `MudHidden` on a static page silently renders its default state.
- **Prerendering**: an interactive component branching on width renders its default breakpoint state first, then
  swaps on interactivity → a layout flash. Pick the mobile-first default variant for prerender, or gate the
  width-dependent region on first interactive render (`basics`'s lifecycle patterns).
- **CSS-swap duplicates DOM; C#-swap runs only when interactive.** Duplicate both variants in markup (CSS swap)
  when the region is small (nav links); for big surfaces (two table layouts) prefer one restyled structure, and
  only reach for a C# swap on an already-interactive surface.
- Dispose `matchMedia`/resize interop subscriptions (`IAsyncDisposable`) — resize listeners leaking across
  navigations is the classic circuit-memory leak ([`performance`](../performance/SKILL.md)).

## The QA handshake

The qa peer skill `qa/{stack}/skills/responsive-testing` boundary-tests (bp−1/bp) whatever this skill defines.
Make that possible:

- **Publish the breakpoint contract** — the token block + `Breakpoints.cs` mirror above is exactly what the QA
  suite imports; changing a breakpoint without telling QA breaks the boundary matrix, so it lives in one
  reviewed place.
- **Both variants of a swap carry stable, variant-suffixed testids** (`nav-desktop` / `nav-hamburger`) — per
  [`test-ids`](../test-ids/SKILL.md). QA asserts the visible one **and** the hidden one; unlabeled
  variants make that impossible.
- Every width must hold the invariant QA checks everywhere: **no horizontal overflow**.

## Rules

- **One breakpoint set app-wide**, documented as tokens + a C# mirror; with a library, *its* values are the set.
- **Mobile-first `min-width` only**; never `min-`+`max-` on one boundary.
- **Intrinsic CSS (`auto-fit`/`minmax`, flex-wrap) before breakpoints; container queries for
  container-dependent components; media queries last.**
- **One grid container owns each region's geometry** — children span tracks, never self-position per breakpoint.
- **Static SSR surfaces are CSS-responsive only**; C# breakpoint services on interactive surfaces, disposed
  properly, with a prerender-safe default variant.
- **Variant swaps: both variants testid-labeled**; DOM order = reading order when visual order changes.
- No fixed dimensions on content regions; images `max-width: 100%`.

## What NOT to do

- No second (or third) breakpoint system next to the library's.
- No magic width numbers scattered in `.razor.css` files — boundary values appear only as the documented set.
- No per-sibling margin tuning to "re-align" elements at a breakpoint — restructure into one grid.
- No `MudHidden`/breakpoint services on static-SSR surfaces (renders its default, silently wrong).
- No duplicated full-page DOM variants for big surfaces — restyle one structure.
- No desktop-first `max-width` cascades bolted onto a mobile-first codebase.

## Validation

- Resize from 320px to 4k: no horizontal scrollbar at any width; every swap flips exactly at its documented
  boundary (check bp−1/bp by hand — QA automates it).
- Grep `.razor.css` for `@media` width values → only the documented set appears.
- View a static-SSR page with JS disabled → layout still correct at mobile and desktop widths.
- Prerender an interactive width-branching component → no jarring variant flash on hydrate.

## Handoffs

- CSS isolation mechanics, tokens, mobile-first authority → [`styling`](../styling/SKILL.md)
- Library grid component APIs, theming → [`component-library`](../component-library/SKILL.md)
- Which table columns/actions survive narrow widths → [`ui-rules`](../ui-rules/SKILL.md)
- Zoom/reflow (WCAG 1.4.10), touch targets, DOM-order-vs-visual-order → [`accessibility`](../accessibility/SKILL.md)
- Responsive image weight, circuit leaks from resize interop → [`performance`](../performance/SKILL.md)
- Verifying all of it by shrinking the browser → qa `responsive-testing` (peer agent's Phase 3)
