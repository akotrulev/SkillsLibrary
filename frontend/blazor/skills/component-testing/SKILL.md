---
name: component-testing
description: Use when writing dev-side tests for Blazor — bUnit v2 for anything that renders, plain NUnit/xUnit for anything that doesn't, to the ≥ 80% branch-coverage floor on changed code. Triggers: "unit-test this Blazor component", "write bUnit tests", "mock IJSRuntime in a component test", "test this validator", "test my state container". Do NOT use for E2E/browser journeys (the `qa-ui-dotnet` peer) or data-testid authoring (`test-ids`).
---

# Blazor — Component & Pure-Logic Testing (bUnit v2)

Owns **every dev-side test in the app**, at two altitudes: **component tests** (it renders → bUnit) and **pure-logic tests** (it doesn't render → plain NUnit/xUnit, no bUnit). The split is mechanical — *does the unit need a renderer?* — and both live in the same test project and runner.

Owns **dev-side component tests**: render a Blazor component in isolation, drive it, and assert on rendered markup and behavior. This is the unit layer under the component — it runs headless, with no browser and no real backend. **Boundary:** end-to-end user journeys, real navigation, and cross-page flows belong to the peer agent [`qa-ui-dotnet`](../../../../qa/dotnet/agents/qa-ui-dotnet.md) (Playwright/Selenium). If a test needs a running app and a real DOM, it is not a bUnit test.

**Runner — house-default deviation, stated once:** bUnit's templates and docs default to **xUnit**, and its examples/lifecycle assume it. The library's global rule is NUnit; bUnit works with NUnit and MSTest too (inherit `BunitContext`; NUnit disposes via `[TearDown]`), but xUnit is the path of least friction for a greenfield component-test project. **Use xUnit for bUnit component tests unless the project already standardizes on NUnit** — then use NUnit and don't fight it. Either way, this deviation from the house default is deliberate; note it once in the test project's README and move on.

## Version rule

bUnit **v2 was a rewrite** — the API moved. Detect the bUnit package version before writing or reviewing:

| v1 (do not use in new code) | v2 (current) |
|---|---|
| `class MyTests : TestContext` | `class MyTests : BunitContext` |
| `TestContext` implements `IDisposable` only | `BunitContext` implements `IDisposable` **and** `IAsyncDisposable` |
| `DisposeComponents()` | `DisposeComponentsAsync()` (async — `await` it) |
| `ctx.RenderComponent<T>(...)` | `Render<T>(...)` / `Render(@<T />)` on the context |

`.NET` TFM is separate from the bUnit version: bUnit v2 targets net8/net9/net10 alike. Author against v2 on any supported TFM; only flag a project for v1 patterns, never for its TFM.

## When to use

- A component has **logic**: conditional rendering, computed display, event handling that mutates state, validation, a state-machine of enabled/disabled actions.
- You want to prove a component reacts correctly to parameter changes, cascading values, injected service results, or JS interop responses.
- Regression-locking a fixed component bug at the unit level (cheaper than an E2E).

## When NOT to use

- **Markup-only components** (a static card, a layout shell with no branching) — a snapshot of hand-written markup asserts nothing but tautology. Test *logic-bearing* components only.
- **End-to-end journeys / real navigation / real backend** → `qa-ui-dotnet` (peer). bUnit fakes `NavigationManager`; it does not actually route.
- **Pure C# logic** with no rendering (a formatter, a validator, a state container) → **not bUnit, but still yours** — see **Pure-logic tests** below.
- **Authoring `data-testid`s** → `frontend/blazor/skills/test-ids`. (Tests here *consume* those testids as stable selectors — `cut.Find("[data-testid='Orders.Row']")`.)

## Test what has behavior — the selection matrix

| Component shape | Test with bUnit? | What to assert |
|---|---|---|
| Conditional render (`@if`, `@switch`) | Yes | Correct branch renders per parameter/state |
| Event handler mutates state | Yes | Click → state change → re-render reflects it |
| Computed/formatted display | Yes | Raw value in → humanized value out |
| `EditForm` + validation | Yes | Invalid input → `ValidationMessage` shown; `OnValidSubmit` not fired |
| Consumes an injected service | Yes | Fake service result drives the rendered output |
| Calls `IJSRuntime` | Yes | JS mock invoked with expected args; return value handled |
| `AuthorizeView` / `[Authorize]` | Yes | Authorized vs unauthorized branch renders |
| Static markup, no branches | No | Nothing — skip it |
| Wires up real HTTP + navigation | No | Belongs to `qa-ui-dotnet` |

## Setup (project)

- Test project references **bunit** (v2) + the runner (`xunit` + `xunit.runner.visualstudio`, or `NUnit` + `NUnit3TestAdapter`) + `Microsoft.NET.Test.Sdk`.
- `_Imports.razor` in the test project: `@using Bunit`, `@using Microsoft.AspNetCore.Components`, and the app namespaces — so `.razor` test files resolve components without per-file usings.
- Test class inherits `BunitContext`. `Services`, `JSInterop`, and `ComponentFactories` are available as members of the context.
- Prefer **`.razor` test files** (`*.razor` compiled test components) when the markup-under-test or expected markup is non-trivial — the expected fragment reads as real Razor rather than an escaped string. Use `.cs` test files for parameter-heavy, assertion-light cases.

## Core API (v2)

```csharp
public class CounterTests : BunitContext        // NOT TestContext (v1)
{
    [Fact]                                        // [Test] under NUnit
    public void Increments_count_when_button_clicked()
    {
        var cut = Render<Counter>();              // NOT RenderComponent<T> (v1)
        cut.Find("[data-testid='Counter.Increment']").Click();
        cut.Find("[data-testid='Counter.Value']").MarkupMatches("<span data-testid=\"Counter.Value\">1</span>");
    }
}
```

- **Render with parameters:** `Render<Card>(p => p.Add(c => c.Title, "Hello").AddChildContent("<p>body</p>"));` or, in a `.razor` test file, inline `Render(@<Card Title="Hello"><p>body</p></Card>)`.
- **`MarkupMatches`** does a **semantic** HTML comparison (whitespace/attribute-order insensitive) — always prefer it over raw string equality. Assert the **smallest node** that proves the behavior (`cut.Find(...).MarkupMatches(...)`), not the whole component's markup.
- **Inject fakes:** `Services.AddSingleton<IOrderService>(new FakeOrderService(...));` **before** `Render`. Constructor-inject the fake per the global rules — no service locator.
- **Cascading values:** `Render<T>(p => p.AddCascadingValue(theme).Add(c => c.Id, 42));`.
- **`EventCallback`:** assert the callback fires — `bool raised = false; Render<Child>(p => p.Add(c => c.OnSave, () => raised = true)); cut.Find(...).Click(); Assert.True(raised);`.

## JS interop mock

```csharp
JSInterop.Mode = JSRuntimeMode.Strict;                 // fail on any unconfigured call
JSInterop.Setup<string>("navigator.clipboard.readText").SetResult("copied");
JSInterop.SetupVoid("myModule.init").SetVoidResult();
// after render:
JSInterop.VerifyInvoke("myModule.init");
```

- **Strict mode by default** — an unconfigured JS call fails the test loudly, so interop drift is caught. Loosen only for components with incidental interop you don't assert.
- Mock **module** interop (`IJSObjectReference` from `import`) with `JSInterop.SetupModule("./script.js")` then set up calls on the returned module handle.

## Auth

```csharp
var authContext = AddTestAuthorization();              // returns TestAuthorizationContext
authContext.SetAuthorized("alice");
authContext.SetRoles("admin");
authContext.SetPolicies("CanEditOrders");
var cut = Render<OrdersToolbar>();
```

- `AddTestAuthorization()` adds the auth services + `CascadingAuthenticationState` to the render tree and returns the `TestAuthorizationContext`. Drive `SetAuthorized` / `SetNotAuthorized` / `SetAuthorizing` / `SetRoles` / `SetPolicies` and assert the `AuthorizeView` branch.
- Test **both** sides — authorized *and* unauthorized — of every gated component.

## Async rendering — never sleep

Renders and interop are async. Assert on a **condition**, never a delay (global rule: no `Thread.Sleep`).

- `cut.WaitForState(() => cut.Instance.Loaded)` — block until a predicate holds.
- `cut.WaitForAssertion(() => cut.Find("[data-testid='Orders.Row']"))` — retry an assertion until it passes or times out.
- `cut.WaitForElement("[data-testid='Toast']")`.
- For a component that fetches in `OnInitializedAsync`, drive the fake to completion and `WaitForState` on the loaded flag — don't assert on the loading markup and hope.

## Rules

- Inherit `BunitContext`; render with `Render<T>` / `Render(@<T/>)`; dispose with `DisposeComponentsAsync` when a test needs mid-test disposal (the context disposes at test end automatically).
- **Semantic assertions only** — `MarkupMatches` / `Find(...).TextContent`, never brittle full-string equality on rendered HTML.
- **Select by `data-testid`** (authored per `test-ids`), not by tag/class/nth-child — the same stable contract the E2E suite uses.
- **One behavior per test**, `Should_X_When_Y` / `Given_When_Then` naming, no `if`/`for` driving assertions (parameterize with `[Theory]`/`[TestCase]` instead) — the global test rules apply here.
- **Fakes/stubs over mocks-of-everything**; constructor-injected into `Services`. Fake the service the component depends on; don't reconstruct the whole app graph.
- **JS interop in Strict mode** so unasserted interop fails loudly.
- Test **logic**, not markup: if removing the assertion leaves a tautology, delete the test.
- **≥ 80% of the branches you wrote are covered** — see *Coverage floor* below.

## Coverage floor — ≥ 80% of the branches you wrote

The tests cover **at least 80% of the branches in the code the change wrote**: every component and class it created, whole, and the methods it changed in a file that already existed. The scope is the change, never the repo.

- **Design for every branch; 80% is what gets measured.** Before writing tests, list the branch outcomes in the code you wrote — `@if`/`else` and `@switch` in markup, each region state (loading / loaded / failed / empty), a `@foreach` over no items and many, event-handler `if`/`else`, `OnParametersSet` guards, `??` and `?.` — and give each a test or a `[TestCase]` row that asserts its effect. The slack under 100% is for branches no honest test reaches, such as compiler-generated ones in the Razor output.
- **Only an asserting test counts.** A render that executes a branch without asserting the markup or state it produced is a **major** finding — it moves the number and catches nothing. The tautology rule above applies.
- **Leave out what the matrix says not to test, by name.** Markup-only components, `_Imports.razor`, `App.razor`/`Routes.razor` and `Program.cs` stay out of the measured file list, and the report names each one left out. Never reach 80% by lowering the number or by `[ExcludeFromCodeCoverage]` on code that has behavior.
- **Measure.** The plan's gate runs this; outside a plan, run it before you report:

  ```bash
  dotnet test --collect:"XPlat Code Coverage" --results-directory TestResults
  dotnet tool run reportgenerator -reports:"TestResults/*/coverage.cobertura.xml" \
    -targetdir:TestResults/coverage -reporttypes:"TextSummary;Html" \
    -filefilters:"+*CartSummary.razor;+*CartSummary.razor.cs;+*CartState.cs"
  ```

  `Branch coverage` in `TestResults/coverage/Summary.txt` is the number; for a method changed in an existing file, that file's page in the HTML report shows its branches. `coverlet.collector` comes with the test project template — add it where it is missing; ReportGenerator is the local tool `dotnet-reportgenerator-globaltool`.
- **Below 80%, write the missing tests.** The report's uncovered branches are the list.
- **Gate.** Inside a plan task, `Gate: none` runs nothing and reports "written, not run"; `Gate: own tests` runs this task's tests — the red run, then green — and the *Coverage floor* measure over the files it wrote, and nothing else. The plan's gate task runs everything else.

## Anti-patterns to avoid

- **Inheriting `TestContext`** or calling `RenderComponent<T>` / `DisposeComponents()` — v1 API; obsolete in v2.
- **Snapshot-testing a markup-only component** — locks layout churn, proves no behavior. (This is what a *visual regression* test is for — `qa/dotnet/skills/visual-regression`, a peer.)
- **`Thread.Sleep` / `Task.Delay`** to wait for a render — use `WaitForState` / `WaitForAssertion`.
- **Asserting whole-component markup** — one selector change breaks dozens of tests; assert the smallest proving node.
- **Selecting by CSS class / tag / index** — couples the test to styling; use `data-testid`.
- **Re-implementing E2E in bUnit** — faking `NavigationManager` and pretending it's a journey test. Hand real navigation to `qa-ui-dotnet`.
- **Loose JS mode everywhere** — hides interop that silently no-ops.
- **Testing the framework** — asserting that `@bind` binds or `EditForm` submits; test *your* logic, not Blazor's.

## Pure-logic tests (no renderer)

A Blazor app is not only components. These units carry real rules and need **no bUnit, no `BunitContext`, no `Render<T>`** — a plain test class in the same test project.

**The rule:** if you are reaching for `Render<T>` to test a validator, you extracted the wrong thing. **Runner: the same one the project already uses** for component tests (see the xUnit/NUnit deviation note at the top) — do **not** introduce a second runner for non-component tests.

| Unit (and the skill that produces it) | Test it? | What to assert |
|---|---|---|
| **Scoped state container** (`state-management`) | **Yes** | A mutation raises `Changed` **exactly once**; subscribers see the new value; unsubscribe stops delivery (a leaked handler is a real Blazor bug) |
| **FluentValidation validator** (`forms`) | **Yes** | The rule fires on the invalid case; the error's property name and message key. Use the validator directly — no `EditForm` needed |
| **Formatter / culture helper** (`languages`) | **Yes** | Per-culture output with an explicit `CultureInfo`, never the ambient one |
| **Breakpoint C# mirror** (`responsive-design`) | **Yes** | The mirror matches the CSS token source — the test that catches drift |
| **Polly policy predicate / retry condition** (`error-handling`) | **Yes** | Which responses retry, which don't, and that the retry count is bounded |
| **DTO→view-model mapper** (`data-fetching`) | **Yes** | Each branch; an unmapped input doesn't become a silent default |
| **Error→UI state mapper** (`error-handling`) | **Yes** | Each failure maps to its three-state region value **without leaking the raw exception message** |
| Records/DTOs with no behavior, `@inject` wiring | **No** | Tautology / framework |

### The browser & ambient seams

The same five seams as everywhere, plus the one Blazor-specific trap:

| Seam | Untestable | Injectable |
|---|---|---|
| **Time** | `DateTime.Now`, `DateTimeOffset.Now` | `TimeProvider` (net8+) → `FakeTimeProvider` |
| **Identity** | `Guid.NewGuid()` | pass the id in, or inject a generator |
| **Config** | `IConfiguration` reads inside logic | `IOptions<T>` → `Options.Create(...)` |
| **JS interop** | a direct `IJSRuntime` call inside logic | keep interop at the component edge; the logic takes the value |
| **Ambient culture** | logic that depends on `CultureInfo.CurrentCulture` | pass the `CultureInfo` explicitly — an ambient-culture-dependent test passes on your machine and fails in CI |

```csharp
[Test]
public void Should_RaiseChangedOnce_When_ValueIsSet()
{
    var container = new CartState();
    var raised = 0;
    container.Changed += () => raised++;

    container.SetItemCount(3);

    Assert.Multiple(() =>
    {
        Assert.That(container.ItemCount, Is.EqualTo(3));
        Assert.That(raised, Is.EqualTo(1));      // not 0 (no notify), not 2 (double-fire)
    });
}
```

Conventions, seams, doubles policy and anti-patterns for this altitude are the same ones the backend stack documents in depth — see [`be-dotnet:unit-testing`](../../../../backend/dotnet/skills/unit-testing/SKILL.md) for the full treatment (NUnit constraint model, NSubstitute traps, `FakeTimeProvider`, parameterized cases, builders). Do not duplicate it here; the fence is only *where the code runs*, and the discipline is identical.

## Handoffs

- Non-rendering logic (state containers, validators, formatters, culture helpers) → **Pure-logic tests**, in this skill
- Data-testid authoring/audit → `frontend/blazor/skills/test-ids`
- End-to-end / real-browser journeys, POM → **peer** `qa-ui-dotnet`
- Visual/pixel regression → **peer** `qa/dotnet/skills/visual-regression`
- Component code smells / rewrites → `frontend/blazor/skills/code-review` / `component-writer`
- What a component *should* do (behavior spec) → the test-case suite from **peer** `qa-test-case-designer`
