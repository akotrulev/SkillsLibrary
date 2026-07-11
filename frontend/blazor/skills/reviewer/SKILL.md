---
name: fe-blazor-reviewer
description: Use when the user asks to review Blazor code (.NET 8/9/10) for component misuse, lifecycle bugs, missing dispose, double-fetch on prerender, `Action` instead of `EventCallback`, mis-scoped or hardcoded render modes, missing data-testids, UI-correctness smells, or JS interop pitfalls. Triggers: "review this Blazor page", "why does this fetch twice", "spot smells in this state container", "audit JS interop", "audit the testids". Do NOT use for explanations (use `frontend/blazor/skills/reference`), generating code (use `frontend/blazor/skills/generator`), non-Blazor .NET (use `design-patterns/dotnet/reviewer`), or auth (use `auth/auth0-blazor`).
---

# Blazor Design Patterns — Reviewer

Reviews Blazor code (.NET 8/9/10 — Static SSR / Server / WASM / Interactive Auto) against the patterns enforced by `frontend/blazor/skills/generator` and the global rules in `CLAUDE.md`. Findings in the standard table; does **not** rewrite.

**Version rule:** identify the project's `TargetFramework` before flagging. Manual `PersistentComponentState` boilerplate is a finding only on net10 (where `[PersistentState]` replaces it); on net8/net9 it's the correct pattern. Same for `NotFoundPage`, `AddValidation()`, and `ReconnectModal` — never flag a down-level project for not using a net10-only API.

## When to use

- A `.razor` / `.razor.cs` diff submitted
- Pre-merge gate on PRs touching `Components/` / `Pages/` / `App.razor`
- "Why does this page fetch twice?" / "Why does my event not re-render?"
- Audit JS interop / dispose hygiene

## When NOT to use

- Conceptual lookup → `frontend/blazor/skills/reference`
- Generating new code → `frontend/blazor/skills/generator`
- Non-Blazor .NET review → `design-patterns/dotnet/reviewer`
- Auth wiring review → `auth/auth0-blazor` + general code review

## Review checklist

### Render mode & prerender

| Check | Bad sign | Severity |
|---|---|---|
| `@rendermode` declared deliberately | Whole-app interactivity when only one button needs it | major |
| Static pages stay static | `@rendermode InteractiveAuto` on content pages without event handlers | minor |
| Render mode set by the consumer | `@rendermode` hardcoded **inside** a reusable component | major |
| Prerender fetch persisted — `[PersistentState]` (net10) / `PersistentComponentState` (net8/9) | Page makes the same HTTP call twice (network panel shows duplicate) | major |
| `[PersistentState]` used where it fits (net10 only) | Manual `PersistentComponentState` register/take/dispose boilerplate on a net10 project | minor |
| `NotFoundPage` wired on the Router (net10 only) | Unknown routes fall through to a blank/default page; `<NotFound>` fragment carried into net10 (unsupported there) | minor |
| `NavLink` matching audited on upgrade | Code assumes `NavLink` matches query strings/fragments (net10 ignores them by default) | minor |
| Server-only secrets never fetched in WASM path | Secret read in code that compiles into WASM bundle | blocker |
| No JS interop in `OnInitializedAsync` | `IJSRuntime.InvokeAsync` before first render | major |

### Event handling

| Check | Bad sign | Severity |
|---|---|---|
| `[Parameter] EventCallback<T>` for component events | `[Parameter] Action<T>` for an event | major |
| Two-way bind matches `@bind-Foo` / `Foo` + `FooChanged` | Component exposes `Value` + `ValueChanged` but consumer uses `@bind-Value` mismatched | minor |
| `@bind:event="oninput"` when input-time updates expected | Field only updates on blur (`onchange`) when UX wants live | minor |
| No `Action.Invoke` on the UI thread without explicit re-render | Handler updates state without `StateHasChanged` and Blazor doesn't notice | major |

### Lifecycle & dispose

| Check | Bad sign | Severity |
|---|---|---|
| `IDisposable` / `IAsyncDisposable` implemented when subscribing | Subscribed to a state container without `Dispose` | major |
| Subscription `+=` matched by `-=` in `Dispose` | One-way bind to a `Changed` event with no unsubscribe | major |
| `_module?.DisposeAsync()` on collocated JS modules | `IJSObjectReference` never disposed | major |
| `ShouldRender` overrides justified | `ShouldRender => false` hiding re-render bugs | major |
| `OnAfterRenderAsync(firstRender)` guard present where needed | DOM JS interop attempted on every render | minor |

### State containers

| Check | Bad sign | Severity |
|---|---|---|
| Scoped DI service for shared state | Singleton state container in Server (shared across connections) | blocker |
| `Changed` event raised on mutation | Mutation methods without notification | major |
| Container immutable from outside (`IReadOnlyList<T>` etc.) | Public `List<T>` allowing external mutation | major |
| No god container | One container mixing cart + nav + user + theme | major |

### Components

| Check | Bad sign | Severity |
|---|---|---|
| One responsibility per component | Page component handling fetch + form + modal + analytics | major |
| Code-behind for components > ~50 lines | All logic in `@code` block in a 300-line file | minor |
| Cascading split by concern | One `CascadingValue` carrying 12 fields | major |
| `IsFixed="true"` on cascading values that don't change | Re-render storms because cascade re-renders mark descendants | minor |
| Parameters have sensible nullability | `[Parameter] public string Foo { get; set; }` (non-nullable, never assigned) without `required` or default | minor |
| `RenderFragment` parameters named `ChildContent` for default | Custom `Content` parameter that breaks the `<Tag>...</Tag>` syntax | nit |

### Forms & validation

| Check | Bad sign | Severity |
|---|---|---|
| `<EditForm>` + `<DataAnnotationsValidator>` (or FluentValidation) | Form submitted without validation wired | major |
| `OnValidSubmit` used, not `OnSubmit` | `OnSubmit` ignoring validation results | major |
| `<ValidationMessage For="..." />` per field | Errors only shown via `<ValidationSummary>` | nit |

### Auth & authorization

| Check | Bad sign | Severity |
|---|---|---|
| `<AuthorizeView>` or `[Authorize]` gates protected UI | Sensitive UI rendered before auth state resolves | major |
| Permission checks via policy, not string compare | `if (user.HasClaim(...))` inline business decisions | minor |
| AuthenticationStateProvider not consumed outside provider context | Component reading auth state without the right cascading parameter | major |

### Performance

| Check | Bad sign | Severity |
|---|---|---|
| `[Parameter]` types are reference-stable where consumers use `ShouldRender` | New array/list literal per render forcing children to re-render | minor |
| Heavy work off the UI thread | Long sync work in `OnInitializedAsync` blocking SignalR | major |
| `@key` used on lists with reordering | Lists rebuild instead of reorder | major |
| No `Console.WriteLine` on hot paths | Verbose console logs in render path | nit |

### Testability (convention: `frontend/blazor/skills/testability`)

| Check | Bad sign | Severity |
|---|---|---|
| Interactive elements / grids carry `data-testid` | Button, input, or grid container without a testid | minor |
| Locators unique per screen | Same testid on two distinct elements (collision) | major |
| Row locators static | Per-row key, numeric id, or GUID inside a locator value | major |
| Locators derived from render-time data | Hand-maintained `Dictionary<TEnum, string>` enum→testid lookup table | minor |
| PascalCase dot-separated segments | kebab-case or snake_case segments | nit |

### UI correctness

| Check | Bad sign | Severity |
|---|---|---|
| Errors mapped to friendly messages | Raw `ex.Message` or response body rendered to the user | major |
| Three-state data regions (loading/loaded/failed) | Failure swallowed into a blank section indistinguishable from "no data" | major |
| In-app navigation is a real anchor | Click-handler-only button calling `NavigateTo` | major |
| Destructive actions confirm by naming the object | Generic "Are you sure?" or no confirmation on delete | major |
| Form fields all persist | Editable field the update path ignores | major |
| Display values humanized | Raw enum int or bare GUID displayed where a name exists | minor |
| Grids sort deterministically | No default server-side sort with a unique tiebreaker | minor |
| Every page has a `<PageTitle>` | Browser tab shows the app default on a content page | minor |
| Nav marks the current location (not by color alone) | No active-item indicator / `aria-current`, or the only cue is a color change | minor |
| Nav visible on desktop; hamburger only below the breakpoint | Menu hidden behind a hamburger at desktop widths where the bar fits | minor |
| Semantic `<footer>` with explicitly-labeled columns | `<div>` footer, or a vague "Resources" column label | minor |
| Links open in the same tab by default | `target="_blank"` on an internal route, or without `rel="noopener"` + an "opens in new tab" cue | major |
| Surface chosen deliberately | Long/multi-step flow trapped in a modal; a modal opened without user action; a blocking modal over data the user must reference | major |
| Dark mode is an authored palette | Dark theme via `filter: invert()` or negated hex, contrast not re-checked | major |

### Cross-cutting

| Check | Bad sign | Severity |
|---|---|---|
| Logging via `ILogger<T>`, structured | `Console.WriteLine` in components | minor |
| Telemetry / tracing instrumentation | Components without `Activity` span when calling backend | minor |
| No mutable static fields | `static List<Foo>` holding "shared" component state | blocker |
| HTTP calls through typed clients / `IHttpClientFactory` | `new HttpClient()` per call | major |

## Procedure

1. Identify the **render mode** and **hosting model** of the component first — half the bugs depend on it
2. Walk the checklists; dispose hygiene, prerender double-fetch, and `EventCallback` misuse are the top three
3. For each finding: file + line, concrete issue, one-sentence fix
4. Hand off to `frontend/blazor/skills/generator` for the rewrite

## Output format

```
| Severity | Location                              | Issue                                                              | Suggested fix                                                              |
|----------|---------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------|
| blocker  | App/Pages/Orders.razor.cs:14         | `CartState` registered as Singleton in Blazor Server                 | Switch to `AddScoped<CartState>()` — Server scopes per SignalR connection   |
| major    | App/Pages/Orders.razor:22            | `OnInitializedAsync` calls `Http.GetFromJsonAsync` without persisting | Wrap with `PersistentComponentState` to avoid double-fetch on Interactive Auto |
| major    | Components/Cart.razor:18             | Subscribes to `Cart.Changed` without `IDisposable`                   | Implement `IDisposable` and unsubscribe in `Dispose`                       |
| major    | Components/InputCurrency.razor:9     | `[Parameter] public Action<long> OnChange` — should be EventCallback  | Change to `[Parameter] EventCallback<long> OnChange`                        |
```

Severities per `CLAUDE.md`.

## Anti-patterns to always flag

- **Singleton state container in Blazor Server** — shared across users, not just connections
- **Same HTTP call fires twice** on InteractiveAuto / Server prerender → InteractiveServer transition (no `[PersistentState]` / `PersistentComponentState`)
- **Render mode hardcoded inside a reusable component** — kills render-mode agnosticism
- **Raw exception text or response body shown to users** — friendly message + correlation id; detail stays in server logs
- **`Action` / `Func` as event parameter** — bypasses re-render
- **Subscription without dispose** — leaks across navigations
- **JS interop in `OnInitializedAsync`** — no JS runtime during prerender
- **One fat `CascadingValue`** carrying every app concern
- **`ShouldRender => false`** masking re-render bugs
- **`@bind` without `@bind:event="oninput"`** when input-time updates matter
- **Business logic inside `.razor` `@code`** — push to services
- **`new HttpClient()`** per call — use `IHttpClientFactory` typed clients
- **`@key={index}` on reorderable lists** — reuse confused with rerender
- **Server-only secrets in code that compiles to WASM** (the WASM bundle is public)

## Handoffs

- Rewrite → `frontend/blazor/skills/generator`
- Conceptual lookup → `frontend/blazor/skills/reference`
- Non-Blazor .NET review → `design-patterns/dotnet/reviewer`
- Auth0 wiring review → `auth/auth0-blazor`
