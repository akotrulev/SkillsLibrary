---
name: fe-blazor-project-setup
description: Use when standing up a Blazor Web App in .NET 8/9/10 — choose the interactivity model, lay out the server + `.Client` split, pick a render mode per surface, wire nullable/warnings-as-errors/CPM/`.editorconfig`. Triggers: "create a new Blazor project", "scaffold a Blazor Web App", "which render mode should this app use". Do NOT use to scaffold components into an existing solution (`component-writer`), wire data fetching (`data-fetching`), or add a component library (`component-library`).
---

# Blazor — Project Scaffold

Stands up a **Blazor Web App** (.NET 8/9/10) from zero: the interactivity choice at `dotnet new`, the server + `.Client` project split, the **render-mode decision made per surface** (not per app), and the quality gates every project ships with (nullable, warnings-as-errors, central package management, `.editorconfig`).

**Version rule:** detect the project's `TargetFramework` **first** — it drives every version-sensitive recipe below. net10 is the primary target; net8 (LTS, supported to Nov 2026) and net9 (STS, out of Microsoft support May 2026 — support existing apps but flag the upgrade) are tagged fallbacks. Never emit a net10-only template flag or API into a down-level project.

## When to use

- New Blazor Web App solution
- Deciding the interactivity model (`--interactivity` flag) and its location (global vs per-page)
- Deciding the render mode for a specific surface
- Setting up the server + `.Client` layout, feature folders, CPM, `.editorconfig`

## When NOT to use

- Adding a component / page to an existing solution → `frontend/blazor/skills/component-writer`
- Request/response data fetching → `frontend/blazor/skills/data-fetching`
- Live/push data → `frontend/blazor/skills/realtime`
- Component library + theming → `frontend/blazor/skills/component-library`, `frontend/blazor/skills/styling`
- Auth0 wiring → `auth/auth0-blazor`
- Non-Blazor .NET project layout → the `backend/dotnet` dev stack, if installed

## Inputs needed

0. **TargetFramework** — net8.0 / net9.0 / net10.0 (drives template flags + recipe variants)
1. **Interactivity model** — None (static SSR only) / Server / WebAssembly / Auto
2. **Interactivity location** — Global (whole app) or Per-page/component (islands, recommended)
3. **Surfaces** — the routes/features and their data shape (content · API-consuming · live/push · offline)
4. **Auth** — needed at scaffold time? (pairs with `auth/auth0-blazor`)

## Create the solution

```bash
# net10 / net9 — interactivity opt-in per component (islands), both hosting models available
dotnet new blazor -o MyApp --interactivity Auto --all-interactive false

# Static SSR only (content site, no .Client project)
dotnet new blazor -o MyApp --interactivity None
```

| Flag | Meaning | Default choice |
|---|---|---|
| `--interactivity` | `None` · `Server` · `WebAssembly` · `Auto` | **`Auto`** unless you know the app is single-mode; `None` for a pure content site |
| `--all-interactive` (`-ai`) | `true` = interactivity set **globally** on `HeadOutlet`+`Routes`; `false` = **per-page/component** | **`false`** — islands. Global interactivity opts every page into a circuit/WASM payload, including static content pages |
| `--empty` | skip the sample pages | `true` on a real app |
| `--use-program-main` | top-level statements vs explicit `Main` | team preference |

> **net8 note:** the template flag is `--interactivity` in the .NET 8 SDK too, but the per-page render-mode ergonomics (and `[PersistentState]`, `NotFoundPage`) are net10 — the [generator](../component-writer/SKILL.md) and [state-management](../state-management/SKILL.md) skills emit the correct variant per TFM.

## Render-mode decision — per surface, not per app

**Static SSR is the default. Interactivity is opt-in per surface.** A content page, an API-consuming dashboard, and a live ticker do not share a render mode. Decide per route:

```
Does this surface need client interactivity at all?
  NO  → Static SSR            (no payload, no circuit; add streaming rendering for slow queries)
  YES → what is its transport shape?
        ├─ live / server-pushed data (dashboards, tickers, chat, presence)
        │     → InteractiveServer   — the circuit is ALREADY a WebSocket; see `../realtime`
        ├─ API-consuming, latency-tolerant first load acceptable, offline/CDN wanted
        │     → InteractiveWebAssembly
        └─ API-consuming, fast first paint AND client richness both matter
              → InteractiveAuto      — pay the cost below, deliberately
```

| Mode | First load | Runs where | Best for | Cost |
|---|---|---|---|---|
| **Static SSR** *(default)* | fastest | server, per request | content, public pages, forms that post | no interactivity without an island |
| **InteractiveServer** | fast | server, over the circuit | live/push surfaces, server-resource-heavy admin | one WebSocket per user; sticky sessions on scale-out |
| **InteractiveWebAssembly** | slow (runtime download) | browser | offline-capable, CDN-served, chatty client logic | initial payload; needs an API to reach the server |
| **InteractiveAuto** | fast (server first) → browser | both, over time | broad apps wanting fast first paint + client richness | **every data path implemented twice** — see below |

### The Auto-mode cost, stated

Auto renders on the **server first** (fast paint), then silently downloads the WASM runtime and **switches to the browser** on the next visit. Because the same component runs in *both* places, its data access must work in both — a server-direct service call **and** a typed `HttpClient` behind one interface (this is exactly the split [`data-fetching`](../data-fetching/SKILL.md) owns). That duplication is Auto's real price. Choose Auto only when both fast-first-paint *and* client-side richness genuinely matter for that surface; otherwise pick Server or WASM outright and skip the double implementation.

### Transport shape weighs in

Render mode is not only a UX call — it fixes your transport:
- **Live/push-heavy** surface → **InteractiveServer**. The circuit is already a persistent WebSocket; server-originated updates need no SignalR client (see [`realtime`](../realtime/SKILL.md)).
- **API/request-response** surface → **WASM or static SSR**. A WASM client owns a typed `HttpClient`; a static SSR page fetches server-side and streams.

## Project layout — server + `.Client` split

Auto/WASM produce two projects. **WASM-executable components live in `.Client`**; anything server-only (EF Core, secrets, server services) lives in the server project and can never be referenced from `.Client`.

```
MyApp/                         # server project — entry point, static SSR host, server services
  Components/
    App.razor                  # document root; <Routes @rendermode="..."> only if global
    Routes.razor               # router; NotFoundPage (net10)
    Layout/
    _Imports.razor
  Features/                    # feature folders (see below) — server-side surfaces
  Program.cs
MyApp.Client/                  # WASM project — components that run in the browser
  Features/                    # interactive WASM surfaces
  Program.cs                   # WASM DI (HttpClient, client services)
  _Imports.razor
```

**Feature folders over type folders.** Group by capability, not by artifact type — `Features/Orders/{OrderList.razor, OrderDetail.razor, IOrderData.cs, OrderState.cs}`, not `Pages/`, `Services/`, `Models/` split apart. A feature is deletable and reviewable as one unit.

**Where a component lives = where it can run.** A component in `.Client` can render under WASM or Auto; a component in the server project is Server or Static only. Shared render-mode-agnostic components go in `.Client` (the server project references it) so both can use them.

### Component layering — reuse levels inside feature folders

Feature folders answer *"which capability owns this?"*; a **reuse-level taxonomy** answers *"how widely is this component shared?"*. Use both — the level decides *where the file lives*, not a competing top-level folder tree. The atomic-design vocabulary maps cleanly onto Blazor:

| Level | What it is (Blazor) | Reuse scope → where it lives | Interactivity |
|---|---|---|---|
| **Atom** | One indivisible control — `Button`, `InputCurrency`, `Badge`, `Spinner`. Wraps a raw element or a library primitive; owns no domain logic. | App-wide → shared `Components/` in `.Client` | render-mode-agnostic; takes `[Parameter]`s + `EventCallback`s only |
| **Molecule** | A few atoms bound to one small job — `SearchBox` (input + button), `LabeledField`, `Pagination`. | App-wide if generic, else the feature folder | render-mode-agnostic |
| **Organism** | A domain-aware section — `OrderTable`, `CustomerCard`, `CheckoutSummary`. Composes molecules/atoms and knows a slice of the model. | Feature folder (`Features/Orders/OrderTable.razor`) | render-mode-agnostic; data comes in via parameters or an injected `data-fetching` interface |
| **Template** | A layout arrangement with slots and no real data — `MainLayout`, `TwoPaneLayout`, page shells with `RenderFragment` regions. | `Components/Layout/` | usually Static |
| **Page** | A routable `@page` component that fills a template with organisms and owns the data fetch + render mode. | Feature folder, next to its organisms | the **consumer** of the render mode; sets it at the route |

Reconciling the two axes:
- **Cross-feature atoms/molecules → one shared `Components/` in the `.Client` project** (the server project references it, so both hosting models compose the same primitives). This is the horizontal, reuse-first slice.
- **Feature-specific organisms + pages → the feature folder** (`Features/<Capability>/`). This is the vertical, capability-first slice.
- **Promote on the second reuse, not the first.** A component earns a move up to shared `Components/` when a *second* feature needs it — premature "atomization" produces a library of one-consumer atoms nobody can find. Duplicating once and extracting on the second use is cheaper than a wrong abstraction.
- **Atoms and molecules stay render-mode-agnostic and domain-free** — no `@rendermode`, no injected data services, no domain types. Domain awareness starts at the organism level; the render mode is decided at the page. This is what lets the same atom run under Static SSR, Server, and WASM (the Auto-mode requirement above).

```
MyApp.Client/
  Components/                    # shared, reuse-first (atoms + generic molecules)
    Button.razor
    InputCurrency.razor
    SearchBox.razor
  Features/
    Orders/                      # capability-first (organisms + pages + feature molecules)
      OrderList.razor            #   page  (@page, sets render mode, fetches data)
      OrderTable.razor           #   organism
      OrderRow.razor             #   feature molecule
```

> **Don't build a global `Atoms/` `Molecules/` `Organisms/` tree.** It fights feature folders, scatters one capability across three directories, and forces a naming call on every trivial component. Keep the *taxonomy as a placement heuristic*, not as the folder structure. The deeper conceptual treatment (naming, prop-drilling limits, when a molecule should own state) lives in [`basics`](../basics/SKILL.md) and [`component-library`](../component-library/SKILL.md).

## Quality gates (every project)

`Directory.Build.props` at the solution root — applies to every project:

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>   <!-- or net8.0 / net9.0 -->
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  </PropertyGroup>
</Project>
```

**Central Package Management** — `Directory.Packages.props` at the root; project files carry `<PackageReference Include="..." />` with **no** `Version`:

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="10.0.0" />
  </ItemGroup>
</Project>
```

**`.editorconfig`** at the root — one style contract shared by the server and `.Client` projects (indentation, `var` rules, `this.` preferences, analyzer severities). With `TreatWarningsAsErrors` + `EnforceCodeStyleInBuild`, style drift fails the build, not review.

## Config hygiene (folds in ui-rules seed §18)

- **No hardcoded URLs or localhost fallbacks in components.** `http://localhost:5001` fallbacks diverge from the deployed path and break quietly. Base addresses come from configuration (`appsettings.json` + environment overrides), injected via typed `HttpClient` (see [`data-fetching`](../data-fetching/SKILL.md)).
- **External-system links come from configuration** — back-office consoles, vendor dashboards, doc sites are config keys, never string literals in `.razor`.
- **No secrets in `appsettings.json`.** Env vars + secret store (global rule); `appsettings.Development.json` is git-ignored for local-only, non-secret overrides.
- **Mind external asset dependencies** (fonts/CDNs) if the app may run air-gapped — self-host or make them a config toggle.

## Rules

- **Static SSR default; interactivity opt-in per surface.** Prefer `--all-interactive false` (islands) over global interactivity.
- **Decide render mode per route from the transport shape**, using the matrix above; document the decision (Phase-1 decision record).
- **`.Client` holds only browser-runnable components**; server-only dependencies (EF Core, secrets, server services) never leak into it.
- **Feature folders**, not type folders. Layer components by reuse level (atom → molecule → organism → template → page) as a **placement heuristic**: shared atoms/molecules in `.Client/Components/`, feature-specific organisms/pages in the feature folder. Promote to shared on the *second* consumer, not the first.
- **Nullable + warnings-as-errors + CPM + `.editorconfig`** from commit one — retrofitting is painful.
- **`<PageTitle>` on every page**, `NotFoundPage` on the router (net10) / `Router.NotFound` fragment (net8/net9) — see [`component-writer`](../component-writer/SKILL.md).
- **Base addresses and external links from config**, never literals.
- **TFM keyed** — guidance follows the detected `TargetFramework`; don't emit net10-only flags/APIs into net8/net9.

## What NOT to do

- No global interactivity (`--all-interactive true`) "to keep it simple" — it opts every static page into a circuit/WASM payload.
- No one-render-mode-for-the-whole-app decision; no `@rendermode` hardcoded inside a reusable component (the consumer sets it — see [`component-writer`](../component-writer/SKILL.md)).
- No EF Core / server service reference from `.Client`.
- No global `Atoms/`/`Molecules/`/`Organisms/` folder tree competing with feature folders; no domain types or `@rendermode` inside an atom/molecule; no extracting a shared component before a second consumer exists.
- No `Version=` on `PackageReference` when CPM is on.
- No hardcoded URLs / localhost fallbacks / secrets in `appsettings.json`.
- No choosing **Auto** without accepting the double data-path cost; if only one mode is needed, pick it outright.
- No net10-only template flags/APIs in a net8/net9 project.

## Validation (exit gate)

- `dotnet build` — **0 warnings** (warnings-as-errors makes this real).
- App **boots**: `dotnet run`, home page renders.
- **One page per chosen render mode renders** — a static SSR page, and one interactive page per interactivity model in use (confirm the WASM page hydrates and the Server page opens a circuit).
- CPM resolves (no version on any `PackageReference`); `.editorconfig` present and enforced.

## Handoffs

- Fetch data into these surfaces → [`data-fetching`](../data-fetching/SKILL.md) (request/response) · [`realtime`](../realtime/SKILL.md) (live/push)
- Scaffold pages/components → [`component-writer`](../component-writer/SKILL.md)
- Component library + theme → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md), `design/theme-presets`
- Auth → `auth/auth0-blazor`
- Concepts/render-mode explanation → [`basics`](../basics/SKILL.md)
- CI pipeline for the solution → `qa/cicd/dotnet` (peer, invoked separately)
