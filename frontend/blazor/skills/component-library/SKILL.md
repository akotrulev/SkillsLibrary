---
name: fe-blazor-component-library
description: Use when choosing or wiring a Blazor UI component library (.NET 8/9/10) — MudBlazor (default) vs Fluent UI vs Radzen vs enterprise vs none — plus setup, theming/dark mode, DataGrid, dialog/snackbar services, and each library's render-mode gotchas. Triggers: "which Blazor component library", "set up MudBlazor / Fluent UI / Radzen", "why don't my MudBlazor components render under static SSR". Do NOT use for hand-rolled CSS/tokens/`::deep` (`styling`) or `data-testid` mechanics (`testability`).
---

# Blazor — Component Library (one-of-N family)

Picks and wires the UI component library that supplies your grids, dialogs, inputs, and theming. **One** library per app — mixing two doubles the CSS surface, the JS payload, and the theming story. This SKILL.md is the **decision matrix + shared rules**; the per-library setup/theming/DataGrid/service/gotcha depth lives in `references/<library>.md` — read exactly one after you've chosen.

**Version rule:** detect the `TargetFramework` first. Component libraries move fast against the Blazor render model — a library's static-SSR support and interactive-registration story differ by *library* version, and some capabilities (e.g. system-preference dark-mode watching, static-SSR-safe rendering) only exist in recent majors. Pin the library major to your `net8/net9/net10` target and read the reference's version notes. Never assume a net10 render-mode fix backported to the library version a net8 app is pinned to.

## When to use

- Choosing a component library for a new Blazor Web App (or justifying a change)
- Wiring the chosen library's provider(s), theme, and services into an existing app
- Adding a DataGrid, dialog, or snackbar/toast and needing the library-native way
- Diagnosing why library components render dead under static SSR or don't survive prerender

## When NOT to use

- Hand-rolled styling, CSS isolation, `::deep`, design tokens → [`styling`](../styling/SKILL.md)
- `data-testid` placement mechanics per library → [`testability`](../testability/SKILL.md) (its per-library attribute matrix is the companion to this one)
- Atom/molecule/organism layering + when a molecule owns state → [`reference`](../reference/SKILL.md)
- Forms + validation → [`forms`](../forms/SKILL.md)
- Render-mode selection per surface → [`project-scaffold`](../project-scaffold/SKILL.md)

## The decision

```
Do you need rich data components (DataGrid, Scheduler, Charts, TreeView) for FREE?
  YES → Radzen         (145+ components, strongest free DataGrid)
  NO  ↓
Is this a Microsoft-ecosystem / Fluent-design product (Teams, M365 look)?
  YES → Fluent UI Blazor
  NO  ↓
Is a paid support SLA + the widest enterprise component set a hard requirement?
  YES → Telerik / Syncfusion (paid enterprise)   → references/enterprise.md
  NO  ↓
Is the design fully custom / minimal, with a design system you own end-to-end?
  YES → none (CSS-isolation only + your own primitives)   → references/none.md
  NO  → MudBlazor      (DEFAULT — Material, free, largest community)
```

| Library | License | Look | Strength | Render-mode reality | Reference |
|---|---|---|---|---|---|
| **MudBlazor** | Free (MIT) | Material Design | Largest free community, cleanest C# API, `MudThemeProvider` + system-preference watch | Historically interactive-first; static-SSR support arrived in recent majors — **verify against your version** | [`mudblazor`](references/mudblazor.md) |
| **Fluent UI Blazor** | Free (MIT) | Microsoft Fluent | Native M365/Teams look, design-token theming, Microsoft-maintained | Built on Fluent Web Components (JS); static SSR works but tokens/JS init need care | [`fluent-ui`](references/fluent-ui.md) |
| **Radzen** | Free (MIT) components; paid Studio/themes | Material / Fluent / Standard | **Strongest free DataGrid**, 145+ components, EF-friendly | Interactive components need an interactive render mode; theme CSS + `Radzen*` providers must be wired | [`radzen`](references/radzen.md) |
| **Telerik / Syncfusion** | **Paid** (Syncfusion has a community license) | Themeable | Widest component set, vendor support SLA, accessibility certs | Mature render-mode support; license key wiring is a gate | [`enterprise`](references/enterprise.md) |
| **none** | — | Fully custom | Zero dependency/payload, total control | No library render-mode issues — you own every primitive; pairs with [`styling`](../styling/SKILL.md) | [`none`](references/none.md) |

**Default = MudBlazor** unless a row above clearly fits better. Pick Radzen the moment a rich free DataGrid is the deciding factor; pick Fluent UI when the product must *look* like Microsoft; pick paid only when a support SLA is a procurement requirement; pick none when the design is bespoke and a component library would fight it.

## Cross-cutting rules (every library)

These hold regardless of which reference you read:

- **One library per app.** Two component libraries = two CSS resets fighting, two theme systems, two JS bundles. If you must migrate, do it wholesale, not surface-by-surface.
- **Providers render at the interactive root, not per page.** `MudThemeProvider`/`MudDialogProvider`/`MudSnackbarProvider` (and the Radzen/Fluent equivalents) go once in the layout under an interactive render mode. Dialog/snackbar **services** only work when their provider is alive in an interactive context — calling `DialogService.Show(...)` from a static-SSR page throws or no-ops. This is the #1 render-mode gotcha; each reference states its exact form.
- **Interactive components need an interactive render mode.** A `MudButton`/`RadzenButton` with an `@onclick` on a static-SSR page renders but does nothing — the island must be `@rendermode InteractiveServer/WebAssembly/Auto`. Static SSR gets you library-styled *markup*, not interactivity. Decide the render mode in [`project-scaffold`](../project-scaffold/SKILL.md), not here.
- **Theme once, centrally.** One theme object / token set at the root; per-component color overrides are a smell. Dark mode is a theme concern — drive it from one toggle + system-preference detection, never per-component `dark:` guessing. The design source (palette, fonts) comes from `design/theme-factory`; [`styling`](../styling/SKILL.md) owns mapping it to CSS variables the library theme reads.
- **`data-testid` on library controls uses the library's unmatched-attribute capture** — inline `data-testid="..."` on the component tag forwards to the rendered root. The exact parameter name per library (`Attributes`/`UserAttributes`/`AdditionalAttributes`) and the `MudTabPanel` caveat live in [`testability`](../testability/SKILL.md)'s matrix — this skill and that one are kept consistent on purpose.
- **DataGrid: server-side paging/sort by default.** Every library's grid can bind an `IQueryable`/`LoadData` callback for server-side paging, filtering, and sorting — use it for anything past a few hundred rows; client-side load of a full table is the default anti-pattern. Deterministic default sort with a unique tiebreaker is a [`ui-conventions`](../ui-conventions/SKILL.md) rule; the grid *mechanics* are in each reference.
- **Don't wrap library controls in `App*` wrappers** just to set defaults or carry test ids — set attributes inline (testability Rule 1); use the theme for defaults.

## Anti-patterns

| Smell | Fix |
|---|---|
| Two component libraries in one app | One library; migrate wholesale if changing |
| `DialogService.Show()` / `Snackbar.Add()` from a static-SSR page | Provider must live under an interactive render mode; the calling island must be interactive |
| Provider (`MudThemeProvider` etc.) added per page | Once, in the interactive layout root |
| Per-component color overrides scattered across pages | One central theme / token set; dark mode from one toggle |
| Full table loaded client-side, then paged in the browser | Server-side `LoadData`/`IQueryable` paging + sort + filter |
| `AppButton` wrapper introduced to carry a `data-testid` | Inline `data-testid` on the library control (testability Rule 1) |
| Mixing Tailwind utility classes *with* a component library's theme | Pick one styling authority — library theme *or* utility CSS (see [`styling`](../styling/SKILL.md)) |
| Library major not pinned to the TFM's supported line | Pin the major; read the reference's version notes |

## Workflow

1. **Choose** via the decision tree above. State the reason (one line) in the architecture decision record ([`project-scaffold`](../project-scaffold/SKILL.md) Phase-1 output).
2. **Read the one `references/<library>.md`** for the chosen library — setup packages, provider wiring, theme + dark mode, DataGrid, dialog/snackbar services, render-mode gotchas.
3. **Wire providers once** at the interactive layout root; register services in DI per the reference.
4. **Theme centrally** from the `design/theme-factory` output via [`styling`](../styling/SKILL.md); wire the dark-mode toggle + system-preference watch.
5. **Verify:** a themed page renders; dialog/snackbar fire from an interactive island; the DataGrid pages server-side; dark mode toggles cleanly; `data-testid`s land on rendered roots (testability).

## Validation

- `dotnet build` — 0 warnings; the theme/dialog/snackbar providers resolve at startup.
- A dialog and a snackbar/toast fire from an interactive island (they no-op/throw from static SSR — that's the test that your render mode is right).
- The DataGrid pages, sorts, and filters **server-side** (Network shows one page's rows, not the whole table).
- Dark mode toggles from one control and follows system preference where supported.
- `data-testid` set inline on a library control appears on the rendered root in DevTools.

## Handoffs

- CSS isolation, `::deep`, design tokens, dark-mode CSS plumbing, Tailwind-vs-isolation → [`styling`](../styling/SKILL.md)
- `data-testid` per-library mechanics → [`testability`](../testability/SKILL.md)
- Component layering (atom/molecule/organism), prop-drilling limits, when a molecule owns state → [`reference`](../reference/SKILL.md)
- Render-mode selection per surface, provider placement in the layout → [`project-scaffold`](../project-scaffold/SKILL.md)
- Forms/validation with library inputs → [`forms`](../forms/SKILL.md)
- Theme palette/fonts source → `design/theme-factory` (loaded in agent Phase 1)
