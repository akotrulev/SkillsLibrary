---
paths:
  - "**/*.razor"
  - "**/*.razor.cs"
---

<!-- fe-blazor rules v1 (2026-11-03): core. Installed by /fe-blazor:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Blazor component standards

Apply these to every Razor component and code-behind you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Markup, forms, data-driven UI, styles, JS modules, tests and config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the `TargetFramework` and the render mode of the surface before writing: `[PersistentState]`, `NotFoundPage`, `AddValidation()`, `ReconnectModal` and circuit pause/resume are net10 only, `HybridCache` needs net9. Never emit one into a lower TFM, and never flag a net8/9 project for using the fallback (`PersistentComponentState`, `Router.NotFound`).

## Simplicity

- Write the simplest thing that meets the requirement. No wrapper that only forwards parameters, no shared store for state one component owns, no base component with one caller, no abstraction over what the framework or the component library already does. Earned on the second real need. *major, fix by inlining*
- Cut structure, never correctness: validation, the three-state region, accessibility, disposal and tests stay.
- One responsibility per component; business logic lives in services, components render and dispatch. *major*
- Code-behind once a component passes ~50 lines; feature folders, a shared component extracted on its second consumer. *minor*

## Render modes and prerender

- Static SSR by default, interactivity opt-in per surface; never whole-app interactivity for one button. *major*
- `@rendermode` is set by the consumer, never inside a reusable component. *major*
- Every prerendered fetch is persisted (`[PersistentState]` on net10, `PersistentComponentState` on net8/9) with a `??=` guard; the same call never fires twice. *major*
- Nothing server-only (EF Core, server services, secrets) in code that compiles to WASM; the bundle is public. *blocker*
- A handler on a static-SSR page does nothing: make the island interactive. Library dialog/snackbar providers render once, in the interactive layout. *major*

## Component contract and lifecycle

- `EventCallback<T>` for every event parameter, never `Action` or `Func`. *major*
- `@bind:event="oninput"` where input-time updates are wanted. *minor*
- A component that subscribes implements `IDisposable`/`IAsyncDisposable`; every `+=` has its `-=`, and its `CancellationToken` is cancelled on dispose. *major*
- `@key` on the entity id in every rendered list, never the loop index; `<Virtualize>` past ~100 rows. *major*
- `CascadingValue` split by concern, `IsFixed="true"` when the reference never changes. *major; minor for IsFixed*
- No new object or lambda allocated per render for a child parameter; no heavy work in `OnParametersSet` or render; no `async void` handler. *major*
- No `StateHasChanged()` after a state-container update or per stream item; `ShouldRender` only on a measured hot path with a real comparison. *major*

## State

- Shared state is a scoped service, never a singleton in Interactive Server (shared across users); no static mutable state. *blocker*
- A container raises `Changed` on every mutation, exposes read-only collections and holds one concern: no god `AppState`. *major*
- Sensitive client-side state goes in `ProtectedBrowserStorage`. *major*

## Data, errors and background work

- Components depend on one render-mode-agnostic data interface. The server lane calls services in-process (no HTTP hop to its own API) and uses `IDbContextFactory`, never a captured `DbContext`. *major*
- HTTP through `IHttpClientFactory` typed clients with `AddStandardResilienceHandler()`; retry idempotent calls only; never `new HttpClient()`. *major*
- Async all the way: no `.Result` or `.Wait()`; a `CancellationToken` threads through to the client or EF Core. *major*
- Every data region renders loading, loaded and failed (inline, with retry); a failure never reads as an empty section. *major*
- A user sees friendly text plus a correlation id; `ex.Message`, response bodies and stack traces go to the log only. *major*
- Route lookups use `TryGetValue` with a diagnosable message; a URL with an unsubstituted `{placeholder}` throws; the response is deserialized to the endpoint's real shape. *major*
- A global `ErrorBoundary` around `@Body` plus per-feature boundaries that log and `Recover()`. *major*
- Background work (broker, hub, timer, `[JSInvokable]`) updates the UI only via `InvokeAsync(StateHasChanged)`. *major*
- Interactive Server reaches its own UI through the circuit and a server broker, never a SignalR client. *major*

## JS interop

- C# first: interop only for a browser API or JS library with no .NET equivalent. *major*
- A collocated `.razor.js` module behind `IJSObjectReference`, loaded in `OnAfterRenderAsync(firstRender)`, never in `OnInitializedAsync`. *major*
- `DisposeAsync` disposes the module and every `DotNetObjectReference`, catching `JSDisconnectedException` on Server. *major*

## Logging, auth and comments

- `ILogger<T>` with message templates, no `Console.WriteLine`; WASM client errors reach the server log. *minor*
- No secret in code. *blocker*
- Protected UI behind `<AuthorizeView>` or `[Authorize]`; permission checks are policies, not inline claim compares. *major; minor for policies*
- No comments inside method bodies or markup (`@* *@`, `<!-- -->`) and no template remnants; XML doc only for a constraint the name cannot carry ("only valid under an interactive render mode"), never on `[Parameter]` properties. *minor; major when wrong*
