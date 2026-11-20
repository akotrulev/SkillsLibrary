---
name: unit-testing
description: Use when Windows app logic needs a dev-side unit test (view models, services, NUnit, fakes, TimeProvider, WinUI Unit Test App). Triggers "unit-test this view model". Not for E2E (qa-desktop-dotnet).
disable-model-invocation: true
---

# Windows — Unit Testing (NUnit + fakes)

Owns **every dev-side test of logic the agent writes**: view models, services, mappers, validators, state machines, the request policy. In-process, no UI automation, no real backend. **NUnit is the default** (house runner); the **MSTest WinUI Unit Test App** is used only for code that needs XAML types (D8, a recorded deviation). Audit rows: section S of `desktop-windows:standards-audit`. Test rules: CLAUDE.md § Test code rules.

**Boundary.** Real windows, real navigation, Narrator, activation and cross-screen journeys belong to `qa-desktop-<lang>` (WinCore / FlaUI by `AutomationId`, `desktop-windows:test-ids`). A unit test fakes the platform, so it can never stand in for them.

## Version lane

| Concern | Primary | Note |
|---|---|---|
| Runner | **NUnit** (the project's 4.x line) + `NUnit3TestAdapter` + `Microsoft.NET.Test.Sdk` | Keep the version the solution already pins |
| Test project TFM | **Matches the app's**: `net10.0-windows10.0.26100.0` (`net11.0-windows…` on 11) | A plain `net10.0` project cannot reference a WinUI project (Learn, 2026-09-10) |
| Pure logic | A **class library with no UI types** (`net10.0`, no Windows suffix) holds view models, services, models; the app and the tests reference it | The seam that makes most tests plain NUnit; the Learn guidance says the same |
| Test project that loads WinAppSDK types | `<RuntimeIdentifiers>win-x86;win-x64;win-arm64</RuntimeIdentifiers>`, `<WindowsAppSdkBootstrapInitialize>true</WindowsAppSdkBootstrapInitialize>`, the Windows App SDK runtime installed on the machine | Only when a test touches `Microsoft.WindowsAppSDK` types that are not XAML |
| XAML types | **WinUI Unit Test App** (`winapp new --template winui-unittest`, or the Visual Studio *WinUI Unit Test App* template): MSTest, `[UITestMethod]` runs on the XAML UI thread | **D8 deviation: MSTest here, NUnit everywhere else**; the project stays a separate test app |
| Time | `TimeProvider`; `FakeTimeProvider` from `Microsoft.Extensions.TimeProvider.Testing` | `DateTime.Now` in logic is a finding |
| Fakes | Hand-written fakes; `NSubstitute` only where a call sequence is the behaviour | No mock of a type you own that a fake serves |
| Coverage | `coverlet.collector` (`dotnet test --collect:"XPlat Code Coverage"`) writes Cobertura with **branch** rate; ReportGenerator prints a summary | The floor is **80% of branches** of the changed code |
| `[WPF]` `[WinForms]` | NUnit over the logic library; view models and presenters tested the same way | Windows controls are not unit-tested; the E2E suite covers them |
| `[C++]` | GoogleTest over a XAML-free core library, floor 80% of lines | Section below |

Detect first: the runner already in use (`NUnit`, `xunit`, `MSTest`), whether a logic library exists, existing fakes and builders, and the coverage tool. Extend them; never migrate a stable suite to NUnit as a side effect.

## When to use

- A view model, service, mapper, validator, formatter or state machine has logic
- "Add tests for this", "how do I test a `RelayCommand`?", "this needs a `Dispatcher`"

## When NOT to use

- Real UI journeys, activation, WebView2 content → `qa-desktop-typescript` / `-java` / `-dotnet`
- Contract tests of the HTTP API → the `qa-api-<stack>` peer
- Accessibility and High Contrast → `desktop-windows:accessibility` (a manual and E2E concern)

---

## Where tests live

| Code | Test with |
|---|---|
| View models, services, validators, mappers, state machines | NUnit in a project that references the logic library |
| A type that needs `Microsoft.UI.Xaml` (a `UserControl`'s code, a custom control's template parts, a converter returning `Visibility`) | The WinUI Unit Test App, `[UITestMethod]` |
| XAML-bound code-behind | **Kept thin and forwarded to a view model**; left out of the measurement by name (recorded in the report), covered by the E2E suite |
| `[C++]` core | GoogleTest (below) |

The first row is nearly everything. **A view model has no `DispatcherQueue`, `Window` or `XamlRoot` in it**: the view marshals to the UI thread, so the view model is plain C# and plain NUnit. A view model that needs the dispatcher is a design defect fixed in `desktop-windows:architecture`, not a test seam to invent.

## Test shape

```csharp
[TestFixture]
public sealed class OrdersViewModelTests
{
    private FakeTimeProvider time = null!;
    private FakeOrderService orders = null!;

    [SetUp]
    public void SetUp()
    {
        time = new FakeTimeProvider(new DateTimeOffset(2026, 11, 15, 10, 0, 0, TimeSpan.Zero));
        orders = new FakeOrderService();
    }

    [Test]
    public async Task Should_ShowRows_When_LoadSucceeds()
    {
        orders.Returns(OrderBuilder.Default().Build(), OrderBuilder.Default().WithTitle("Second").Build());
        var viewModel = new OrdersViewModel(orders, time);

        await viewModel.LoadCommand.ExecuteAsync(null);

        Assert.That(viewModel.State, Is.TypeOf<Load<IReadOnlyList<OrderRow>>.Loaded>());
    }

    [Test]
    public async Task Should_BeFailedAndOpenBanner_When_ServerFails()
    {
        orders.Fails(FailureKind.Server);
        var viewModel = new OrdersViewModel(orders, time);

        await viewModel.LoadCommand.ExecuteAsync(null);

        Assert.That(viewModel.BannerOpen, Is.True);
    }

    [TestCase(FailureKind.Offline)]
    [TestCase(FailureKind.Timeout)]
    [TestCase(FailureKind.Drifted)]
    public async Task Should_BeFailed_When_LoadFailsWith(FailureKind kind)
    {
        orders.Fails(kind);
        var viewModel = new OrdersViewModel(orders, time);

        await viewModel.LoadCommand.ExecuteAsync(null);

        Assert.That(((Load<IReadOnlyList<OrderRow>>.Failed)viewModel.State).Kind, Is.EqualTo(kind));
    }
}
```

- **Names are behaviour:** `Should_X_When_Y`. **One logical assertion** (`Assert.That` once, or several that verify one behaviour). **No `if`, no `for` driving an assertion**: use `[TestCase]` / `[TestCaseSource]`.
- **Data through builders** (`OrderBuilder`) once an object has four or more fields; no inline literals duplicated across tests.
- **No `try`/`catch` in a test body.** An expected exception is `Assert.ThrowsAsync<T>`; an unexpected one reaches the runner untouched. Cleanup of what the test created is a `[TearDown]`.
- **Every assertion states one expected condition:** never `Is.EqualTo(200).Or.EqualTo(204)`.
- **No inline comments;** the name and the arrange / act / assert shape are the explanation.
- **No `Thread.Sleep`, `Task.Delay` to wait.** Await the command (`ExecuteAsync`), or advance the `FakeTimeProvider` (`time.Advance(TimeSpan.FromSeconds(30))`).
- Tests are independent and run in any order; no shared static state; the `[SetUp]` builds fresh fakes.

## Commands and observable state

- A `RelayCommand` (CommunityToolkit.Mvvm 8.4.2) is tested through `ExecuteAsync` on the generated `IAsyncRelayCommand`; assert the property it changed, not that a method ran.
- `CanExecute` is asserted with `viewModel.SaveCommand.CanExecute(null)` before and after the input changes.
- `[ObservableProperty]` change notification: subscribe to `PropertyChanged` in the test and assert the name once; the toolkit's generated code needs no test of its own.
- `ObservableValidator`: set the property, assert `viewModel.GetErrors(nameof(...))` for the rule; one `[TestCase]` per rule and per boundary value.

## Fakes over mocks

- A fake is a small class implementing the interface the view model actually depends on, with `Returns(...)` and `Fails(kind)` methods. An interface that has the real service and one fake has two implementations: it is earned (CLAUDE.md § Simplicity).
- A mock library is for **a call sequence that is the behaviour** (the order of save then notify). Never a mock of `HttpClient`; fake the `HttpMessageHandler` (a `StubHandler` returning a canned `HttpResponseMessage`) for the typed client's own tests.
- **No in-memory substitute for a database you ship against** (EF `UseInMemoryDatabase`, SQLite standing in for another engine): a unit test over a data layer uses a fake of the data interface; the real-engine behaviour is an integration test in the `be-*` / `qa-api-<stack>` lane, or a local SQLite test only where SQLite is the shipped store (`desktop-windows:offline-and-storage`).
- Time and random go through `TimeProvider` and an injected seed; `Guid.NewGuid()` in logic goes behind the same seam if a test reads it.

## The WinUI Unit Test App (code that needs XAML types)

```csharp
[TestClass]
public class PriceBadgeTests
{
    [UITestMethod]
    public void Should_ShowSaleBrush_When_PriceIsReduced()
    {
        var badge = new PriceBadge { Price = 8m, ListPrice = 10m };

        Assert.IsTrue(badge.IsOnSale);
    }
}
```

- Create it with `winapp new --template winui-unittest` (needs `winapp` 0.8.0, preview) or Visual Studio's *WinUI Unit Test App* template. It is a **separate MSTest project** that hosts a XAML UI thread.
- **`[UITestMethod]` runs on the UI thread; `[TestMethod]` does not.** Anything that creates a `Grid`, `UserControl` or `DependencyObject` needs the former.
- Pull the code under test out of the app project into a library the app and the test app both reference (Learn's own advice); the test app never references the app project.
- The same rules apply: `Should_X_When_Y`, one logical assertion, no conditionals (`[DataRow]` for variants), no inline comments. **Using MSTest here is the D8 deviation** and is stated in the test project's folder name (`*.UiTests`) so a reader knows why a second runner is present.
- Coverage inside the test app is **not verified** for this release: do not claim a measured number for XAML-bound code; say it is left out by name and covered by the E2E suite.

## Coverage — the floor

CLAUDE.md § Test code rules: **≥ 80% of the branches of the code the change wrote** (a created file whole; in an existing file, the changed methods). Designed branch by branch, not to move a number: every `if`/`else` arm, `switch` case and default, ternary, `??` / `?.`, short-circuit operand, guard return, `catch`, and loop run zero and many times gets a test that asserts its effect.

```powershell
dotnet test tests/Orders.Tests --collect:"XPlat Code Coverage" --results-directory artifacts/cov
dotnet tool run reportgenerator -reports:"artifacts/cov/**/coverage.cobertura.xml" -targetdir:artifacts/cov/report -reporttypes:TextSummary
```

- Read the **branch** rate for the files the change touched, not the repo total. Repo-wide coverage is never a target.
- **Left out by name:** DTOs and records without logic, generated code (`*.g.cs`, `*.g.i.cs`, `Generated Files`), DI registration in `Program` / `App`, XAML code-behind that only forwards. A skipped file is listed in the report, never hidden by lowering the number or by an exclusion marker on code with behaviour.
- Only an asserting test counts: a test with no assertion, written to move the number, is a major finding (`test-quality-check` catches it by mutation score).
- Report the unit: "branches".

## The C++/WinRT lane

C++ logic is tested with **GoogleTest over a XAML-free core library**, with a floor of **80% of lines** (80% of branches where the project reports them with `llvm-cov`). The framework choice, the coverage tools and the commands are decision D16 and live in [`../cpp-winrt/references/testing-and-coverage.md`](../cpp-winrt/references/testing-and-coverage.md); this skill does not repeat them. A C# solution that also has a C++ core runs both families: NUnit for the C#, GoogleTest for the C++, each to its own floor.

## What to test, and what not

| Test | Do not test |
|---|---|
| Branches of logic: validation rules, mapping, state transitions, the `Load<T>` machine, retry policy, formatting, plural selection | The toolkit's source-generated code, `INotifyPropertyChanged` plumbing |
| Failure paths: each `FailureKind`, timeout, cancellation, a drifted response | A getter that returns a field |
| Time-dependent behaviour with `FakeTimeProvider` | Control layout or visuals (E2E and screenshots) |
| That every resource key the code names exists in the default `.resw` (`desktop-windows:languages`) | A third-party library's behaviour |

## Telemetry

Tests assert behaviour, not telemetry. A test that proves a failure raises the banner is the failure rule's test; the gate's telemetry smoke proves spans and metrics arrive (`desktop-shared:observability`).

## Rules

1. NUnit by default; the WinUI Unit Test App (MSTest, `[UITestMethod]`) only for code that needs XAML types, recorded as D8.
2. Logic lives in a library with no UI types; view models never touch the dispatcher.
3. Names `Should_X_When_Y`; one logical assertion; no `if` or loop driving an assertion; no `try`/`catch` in a body; no `OR` in an assertion; no inline comments.
4. Fakes over mocks; no in-memory substitute for a shipped database; time through `TimeProvider`.
5. Test data through builders for four or more fields.
6. ≥ 80% of the changed branches (lines on the C++ lane), measured on the changed files, designed branch by branch.
7. Tests are independent; no `Thread.Sleep`; no shared static state.

## Generation steps

1. Detect runner, test projects, the logic library, fakes and the coverage tool.
2. If the logic is in the app project, extract it to a library first (a recorded step), then reference it from tests.
3. Write the happy path, then each failure and each branch; use `[TestCase]` for variants.
4. For XAML-type code, add or extend the WinUI Unit Test App with `[UITestMethod]`.
5. Run the project's own tests with the narrowest filter (`dotnet test --filter "FullyQualifiedName~OrdersViewModelTests"`), then the coverage command on the changed files; read branches.
6. Add tests until each changed method's branches are covered; list what was left out by name.

## Validation

- `rg -n "Thread\.Sleep|Task\.Delay" -g '*Tests*.cs'` — none.
- `rg -n "\btry\b|\bcatch\b" -g '*Tests*.cs'` — none in a test body (helpers doing I/O only).
- `rg -n "\.Or\." -g '*Tests*.cs'` — none (`Is.EqualTo(a).Or…`).
- `rg -n "DispatcherQueue|XamlRoot|Microsoft\.UI\.Xaml" -g '*ViewModel*.cs'` — none.
- The coverage report lists the changed files at ≥ 80% branches.

## Common gotchas

- **`net10.0` test project referencing a WinUI project** — restore fails; use the Windows TFM or reference a UI-free library.
- **A `Dispatcher` inside a view model** — untestable and a layering defect.
- **`[TestMethod]` on a test that creates a `Grid`** — a `COMException` (wrong thread); it needs `[UITestMethod]`.
- **`async void` test** — passes before it runs; return `Task`.
- **`DateTime.UtcNow` in logic** — the test depends on the clock.
- **A loop of asserts over a collection** — use `[TestCaseSource]`, or one assertion on the whole collection.
- **Coverage reported for the whole solution** — the changed files are the scope.
- **MSTest used for plain logic** — the deviation is for XAML types only.

## Handoffs

- View-model shape, DI and where logic lives → `desktop-windows:architecture`
- `Load<T>` states and the banner under test → `desktop-windows:error-handling`; validation rules → `desktop-windows:forms`
- Ids the E2E suite uses → `desktop-windows:test-ids`; the E2E suites → `qa-desktop-typescript`, `qa-desktop-java`, `qa-desktop-dotnet`
- C++ tests and coverage commands → `desktop-windows:cpp-winrt`; the macOS twin → `desktop-macos:unit-testing`
