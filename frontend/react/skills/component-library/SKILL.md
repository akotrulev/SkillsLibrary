---
name: fe-react-component-library
description: Use when picking or wiring the UI component library an app is built on — shadcn/ui + Tailwind (default) vs Mantine vs MUI vs Chakra vs none — plus theme/`ThemeProvider` + dark mode, DataGrid, dialog/toast surface, and the RSC `'use client'` boundary each forces. Triggers "which component library", "set up MUI/Mantine/Chakra/shadcn", "why do MUI components error in a Server Component". Not for hand-written CSS/tokens (`styling`) or forms (`forms`).
---

# React — Component Library (one-of-N family)

Picks and wires the UI component library that supplies your grids, dialogs, inputs, and theming. **One** library per app — mixing two doubles the CSS surface, the JS payload, and the theming story. This SKILL.md is the **decision matrix + shared rules**; the per-library setup/theming/DataGrid/service/RSC-boundary depth lives in `references/<library>.md` — read exactly one after you've chosen.

**Version rule:** detect the React/Next major first (`package.json`). Libraries move fast against the RSC model — a library's App-Router story (which components are client-only, whether it ships a Next integration package, how the theme survives Server Components) differs by *library* major. Current majors: **MUI v7** ([MUI v7 is here](https://mui.com/blog/material-ui-v7-is-here/)), **Mantine v8/v9** ([Mantine v8.0.0](https://mantine.dev/changelog/8-0-0/)), **Chakra UI v3** (full rewrite on Ark UI — [Announcing v3](https://chakra-ui.com/blog/announcing-v3)), **shadcn/ui on Tailwind v4**. Pin the library major to your React/Next line and read the reference's version notes — never assume a v-latest App-Router fix exists in the major a React 18 app is pinned to.

## When to use

- Choosing a component library for a new React app (or justifying a change)
- Wiring the chosen library's provider(s), theme, and services into an existing app
- Adding a DataGrid, dialog, or toast/snackbar and needing the library-native way (building the grid itself → [`data-grid`](../data-grid/SKILL.md))
- Diagnosing why library components throw or render dead in a Server Component

## When NOT to use

- Hand-written styling, CSS Modules, design tokens, dark-mode CSS → [`styling`](../styling/SKILL.md)
- `data-testid` placement mechanics per library → [`test-ids`](../test-ids/SKILL.md) (its per-library attribute matrix is the companion to this one)
- Atom/molecule/organism layering + when a molecule owns state → [`basics`](../basics/SKILL.md)
- Forms + validation → [`forms`](../forms/SKILL.md)
- Rendering-strategy / `'use client'` placement per route → [`project-setup`](../project-setup/SKILL.md)

## The decision

```
Is this an EXISTING app already on a component library?
  YES → keep it. The library in the repo is the authority; changing it is a wholesale
        migration with its own justification, never a side effect of a feature.
  NO  ↓
Do you need a rich FREE component set (DataTable, DatePicker, Charts, 100+ hooks)
WITHOUT owning the component source?
  YES → Mantine         (largest free set + free DataTable, superb DX)            → references/mantine.md
  NO  ↓
Is Material Design itself the requirement (a brand or spec mandates it)?
  YES → MUI             (Material, largest ecosystem, MUI X DataGrid + paid tiers) → references/mui.md
  NO  ↓
Prefer an accessible style-props / recipe DX (Ark UI under the hood)?
  YES → Chakra UI v3                                                              → references/chakra.md
  NO  ↓
Is the design fully bespoke / minimal, with a design system you own end-to-end?
  YES → none            (headless: Radix / React Aria + TanStack Table + your CSS) → references/none.md
  NO  → shadcn/ui       (DEFAULT — Radix primitives + Tailwind; you own the code)  → references/shadcn.md
```

| Library | Cost | Look | Strength | RSC reality | Reference |
|---|---|---|---|---|---|
| **shadcn/ui** *(default)* | Free (you own the code) | Tailwind, fully themeable | Copy-in components on Radix; **no runtime dependency**, total control | Components are client where they use hooks (`'use client'` at the file top, generated for you); styling authority flips to **Tailwind** | [`shadcn`](references/shadcn.md) |
| **MUI (Material UI)** | Free (MIT); MUI X has a Pro tier | Material Design | Largest ecosystem, `theme` + `sx`, MUI X DataGrid (free + Pro), `@mui/material-nextjs` App-Router integration | Emotion runtime → interactive components are **client**; wrap in `'use client'` islands, use the Next integration for SSR style flush | [`mui`](references/mui.md) |
| **Mantine** | Free (MIT) | Neutral, modern | **Richest free set** + free `mantine-datatable`, 100+ hooks, best-in-class DX | Needs `'use client'` provider + `ColorSchemeScript` in the root layout; components are client | [`mantine`](references/mantine.md) |
| **Chakra UI v3** | Free (MIT) | Neutral, accessible | Style-props + recipes, Ark UI a11y primitives, strong theming | v3 provider is `'use client'`; `next-themes` for color mode | [`chakra`](references/chakra.md) |
| **none** | — | Fully custom | Zero component dep/payload; you own every primitive | You own the RSC boundary; headless primitives (Radix/React Aria) are client; pairs with [`styling`](../styling/SKILL.md) | [`none`](references/none.md) |

**Default = shadcn/ui on Tailwind** unless a row above clearly fits better. It is the default because there is **no runtime component dependency and no paid tier** — the source is yours, Radix carries the a11y, and everything MUI X gates behind Pro/Premium (multi-sort, column pinning, row grouping, aggregation, tree data) is free in the TanStack engine the [`data-grid`](../data-grid/SKILL.md) skill builds on. The cost is real and stated up front: **you own the component code forever** — upgrading a component means re-running `shadcn add` and merging your edits by hand, and you build the grid toolbar yourself. Pick **Mantine** when a rich free component set out of the box matters more than owning the source; **MUI** when Material Design is the requirement; **Chakra** for the style-props DX; **none** when the design is bespoke and any library would fight it.

**Brownfield never re-litigates this.** An existing MUI/Mantine/Chakra app keeps its library and its styling authority — the default applies to *new* apps. Introducing Tailwind alongside a CSS-in-JS library to "start migrating" is the G1 violation, not a migration plan.

## Cross-cutting rules (every library)

These hold regardless of which reference you read:

- **One library per app.** Two libraries = two CSS resets fighting, two theme systems, two JS bundles. Migrate wholesale, never surface-by-surface.
- **The theme provider is a `'use client'` island mounted once at the root, not per page.** MUI's `ThemeProvider`, Mantine's `MantineProvider`, Chakra's `Provider` (and their dialog/toast portals) go once in a client `Providers` component rendered from `app/layout.tsx`. Because they rely on React Context + Emotion/CSS-in-JS runtime, they **cannot** render inside a Server Component — a `<Button onClick>` dropped into an RSC is a build/runtime error, not a no-op. This is the #1 App-Router gotcha; each reference states its exact form (and the Vite SPA lane has no RSC, so the provider just wraps `<App>`).
- **Interactive components live in Client Components.** A library button/menu/dialog with an `onClick`/state must sit under a `'use client'` boundary. Server Components render library components only when they're purely presentational (no hooks, no handlers). Decide the boundary in [`project-setup`](../project-setup/SKILL.md) — push `'use client'` to the leaves, never blanket a route.
- **Theme once, centrally.** One theme object / token set at the root; per-component color overrides are a smell. Dark mode is a theme concern — drive it from one toggle + system-preference detection (`next-themes` or the library's color-mode API), never per-component `dark:` guessing. The design source (palette, fonts) comes from [`design/visual-identity`](../../../../design/visual-identity/SKILL.md); [`styling`](../styling/SKILL.md) owns mapping it into the theme + CSS variables.
- **`data-testid` on library controls forwards through the component's rest-props / slot props** to the rendered root. The exact prop per library (`data-testid` passthrough, `slotProps`, `component`) and the caveats live in [`test-ids`](../test-ids/SKILL.md)'s matrix — this skill and that one are kept consistent on purpose.
- **DataGrid: server-side paging/sort/filter by default.** Every library's grid can drive paging/sorting/filtering off a server callback — use it for anything past a few hundred rows; client-side load of a full table is the default anti-pattern. The grid calls a [`data-fetching`](../data-fetching/SKILL.md) function — it's a consumer, not a data owner. Deterministic default sort with a unique tiebreaker is a [`ui-rules`](../ui-rules/SKILL.md) rule.
- **Don't wrap library controls in `App*` wrappers** just to set defaults or carry test ids — pass `data-testid` inline (testability Rule 1); use the theme for defaults.

## Anti-patterns

| Smell | Fix |
|---|---|
| Two component libraries in one app | One library; migrate wholesale if changing |
| Library `<Button onClick>` / `useDialog` in a Server Component | Move it under a `'use client'` boundary; provider is a client island |
| `ThemeProvider`/`MantineProvider` added per page | Once, in a client `Providers` component off the root layout |
| Per-component color overrides scattered across pages | One central theme / token set; dark mode from one toggle |
| Full table loaded client-side, then paged in the browser | Server-side callback (`onPaginationModelChange`/`onSortChange`) → `data-fetching` query |
| `AppButton` wrapper introduced to carry a `data-testid` | Inline `data-testid` on the library control (testability Rule 1) |
| Tailwind utility classes mixed *with* a CSS-in-JS library's theme | Pick one styling authority — library theme *or* Tailwind (see [`styling`](../styling/SKILL.md)) |
| Library major not pinned to the React/Next line | Pin the major; read the reference's version notes |

## Workflow

1. **Choose** via the decision tree. State the reason (one line) in the architecture decision record ([`project-setup`](../project-setup/SKILL.md) Step-1 output).
2. **Read the one `references/<library>.md`** — packages, provider/`'use client'` wiring, theme + dark mode, DataGrid, dialog/toast services, RSC gotchas.
3. **Wire the provider once** as a client island off the root layout; register the Next integration where the library ships one (MUI).
4. **Theme centrally** from the [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) output via [`styling`](../styling/SKILL.md); wire the dark-mode toggle + system-preference watch.
5. **Verify:** a themed page renders; a dialog/toast fires from a client island; the DataGrid pages server-side; dark mode toggles cleanly; `data-testid`s land on rendered roots (testability).

## Validation

- `pnpm build` + typecheck clean; the theme/dialog/toast providers resolve at the root.
- A dialog and a toast/snackbar fire from a `'use client'` island (they can't be called from an RSC — that's the test your boundary is right).
- The DataGrid pages, sorts, and filters **server-side** (Network shows one page's rows, not the whole table).
- Dark mode toggles from one control and follows system preference (`next-themes` / library color-mode API), with no light→dark flash on reload.
- `data-testid` set inline on a library control appears on the rendered root in DevTools.

## Handoffs

- CSS Modules, design tokens as CSS vars, dark-mode CSS plumbing, Tailwind-vs-library → [`styling`](../styling/SKILL.md)
- `data-testid` per-library mechanics → [`test-ids`](../test-ids/SKILL.md)
- Component layering (atom/molecule/organism), prop-drilling limits, when a molecule owns state → [`basics`](../basics/SKILL.md)
- `'use client'` boundary + rendering strategy per route, provider placement → [`project-setup`](../project-setup/SKILL.md)
- Building the app's own grid (Tailwind/shadcn lane) + the full feature surface → [`data-grid`](../data-grid/SKILL.md)
- The grid's data function (server-side paging/sort/filter) → [`data-fetching`](../data-fetching/SKILL.md)
- Forms/validation with library inputs → [`forms`](../forms/SKILL.md)
- Theme palette/fonts source → [`design/visual-identity`](../../../../design/visual-identity/SKILL.md) (primary), `design/theme-presets` (quick-start)
- Breakpoint contract, grids, cross-breakpoint alignment → [`responsive-design`](../responsive-design/SKILL.md)
