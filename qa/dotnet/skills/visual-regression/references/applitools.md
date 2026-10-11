# Visual Regression — Applitools Eyes (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

Applitools Eyes uploads the page to the **Ultrafast Grid**, re-renders it server-side across a configured
browser, viewport and device matrix, and compares each render with **visual AI** that ignores anti-aliasing
and sub-pixel noise. **Match levels** (Strict, Layout, Content) decide how strictly a region is compared.
That control is what Percy's pixel diff and the comparer lane lack. Baselines live in the Applitools
dashboard; a person accepts or rejects differences there.

The .NET SDK is the NuGet package **`Eyes.Playwright`** (the assembly `Eyes.Playwright.DotNet`, namespaces
`Applitools.Playwright` and `Applitools.Playwright.Fluent`). A package named after the vendor plus
`.Playwright` does not exist on NuGet, and restore fails on it. An Eyes class derives from
`Example.UiTests.Support.BaseTest` (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`) and adds
`Check(...)` to a flow the page objects drive.

## Why graduate from Percy to Applitools

| | Percy | **Applitools Eyes** |
|---|---|---|
| What leaves the test | A DOM snapshot, through the `percy exec` agent | The page, uploaded by the **SDK itself** — no agent |
| How the diff is judged | Server-side **pixel** diff | Server-side **visual AI** |
| Tolerance lever | `percyCSS` hide and `scope` | **Match levels** per region, plus ignore and floating regions |
| Dynamic content | Hide it | **`Layout(locator)`** — the structure must match, the text may change |
| Browsers and devices | Re-rendered at configured widths | **Ultrafast Grid** — a real browser/viewport/device matrix from one run |
| Gate | A status check | The runner's results fail the run; the dashboard holds the review |
| Cost | Paid | Paid, usually the most expensive |

## 1. Setup

`Eyes.Playwright` 1.37.49 (published 2026-10-01; checked on NuGet on 2026-10-11) is already in the writer's
`Directory.Packages.props`, so the project only references it:

```xml
<ItemGroup>
  <PackageReference Include="Eyes.Playwright" />
</ItemGroup>
```

It targets .NET Standard 2.0 and brings `Eyes.Images` 3.68.9 (the `Configuration`, `BatchInfo`, runner and
results types) and `Eyes.Core` 4.71.0. No agent to launch. `APPLITOOLS_API_KEY` is the **only** secret; the SDK
reads it from the environment. It comes from the CI secret store and is never committed or logged.

## 2. The model — every call is synchronous

The public API of `Eyes.Playwright` 1.37.49, read from the package's assembly metadata (the SDK publishes no
sources):

| Type | Members used here |
|---|---|
| `Applitools.VisualGrid.VisualGridRunner` | `new VisualGridRunner(new RunnerOptions().TestConcurrency(5))`; `GetAllTestResults(bool shouldThrowException)` → `TestResultsSummary` |
| `Applitools.Playwright.Eyes` | `new Eyes(runner)`; `SetConfiguration(IConfiguration)`; `Open(IPage, string appName, string testName, RectangleSize viewportSize)` → `IPage`; `Check(string tag, ICheckSettings)`; `CloseAsync()`; `AbortAsync()` |
| `Applitools.Playwright.Fluent.Target` | `Window()`, `Region(ILocator)` (also `string` selector, `IElementHandle`, `Region`), `Frame(ILocator)` |
| `Applitools.TestResultsSummary` | `GetAllResults()` → `TestResultContainer[]`, each with `TestResults` (`Name`, `Status`, `Url`, `AppUrls.Batch`) and `Exception` |

- **`Open`, `Check` and `Close` return no `Task`.** `CloseAsync()` and `AbortAsync()` return `void` — the
  name means "close without waiting for the grid", not a task to await. `Close(bool)` blocks for that test's
  results; the runner's `GetAllTestResults` blocks for all of them. There is nothing to `await` on the Eyes
  side and no `OpenAsync`/`CheckAsync` to look for.
- **`VisualGridRunner`** ships checkpoints to the grid. Its sibling `ClassicRunner` renders locally in one
  environment — use the grid, which is the reason to choose Applitools.
- **`GetAllTestResults(false)`** waits until every checkpoint of every `Eyes` on that runner has been rendered
  and compared, and returns them; `true` throws instead when any differs. §4 takes the results and asserts
  on them, so the failure message carries each checkpoint's link.

## 3. The render matrix and the results — `Support/EyesConfig.cs`

```csharp
using System.Text;
using Allure.Net.Commons;
using Applitools;
using Applitools.VisualGrid;

namespace Example.UiTests.Support;

public static class EyesConfig
{
    public static Configuration ForGrid()
    {
        var config = new Configuration();
        config.SetAppName("Shop Web");
        config.SetBatch(new BatchInfo("Shop Web — Visual") { Id = BaseTest.RequiredEnv("APPLITOOLS_BATCH_ID") });
        config.AddBrowser(1280, 800, BrowserType.CHROME);
        config.AddBrowser(1280, 800, BrowserType.FIREFOX);
        config.AddBrowser(1280, 800, BrowserType.SAFARI);
        config.AddDeviceEmulation(DeviceName.Pixel_5, ScreenOrientation.Portrait);
        return config;
    }

    public static IReadOnlyList<string> Unresolved(TestResultsSummary summary)
    {
        var results = summary.GetAllResults();
        var lines = results.Select(Describe).ToList();
        AllureApi.AddGlobalAttachment("applitools-results", "text/plain", Encoding.UTF8.GetBytes(string.Join('\n', lines)), ".txt");
        return results
            .Where(result => result.Exception is not null || result.TestResults?.Status != TestResultsStatus.Passed)
            .Select(Describe)
            .ToList();
    }

    private static string Describe(TestResultContainer result) =>
        $"{result.TestResults?.Name}: {result.TestResults?.Status} {result.TestResults?.Url} {result.Exception?.Message}";
}
```

- Every `AddBrowser` / `AddDeviceEmulation` is one more render of every checkpoint — one `Check` here
  produces four comparisons. `BrowserType` (`Applitools`) and `DeviceName`, `ScreenOrientation`
  (`Applitools.VisualGrid`) are enums of the SDK, not Playwright's.
- **One batch per run.** Each test class has its own runner (§4), so the classes share a batch only through a
  stable id. CI sets `APPLITOOLS_BATCH_ID` to the run id (GitHub: `${{ github.run_id }}-${{ github.run_attempt }}`);
  locally, export any value. `BaseTest.RequiredEnv` fails with the variable's name when it is missing.
- **The results are attached with `AllureApi.AddGlobalAttachment`**, because they arrive in
  `[OneTimeTearDown]`, where no test is running: `AddAttachment` and `AddLink` record nothing there (both
  check for a running test or fixture in Allure.NUnit 2.15.0), while a global attachment belongs to the run.
  Each line carries the checkpoint's dashboard URL.
- The matrix is code in the repository, not a secret; only the API key is.

## 4. The core pattern

```csharp
using Applitools.Playwright;
using Applitools.Playwright.Fluent;
using Applitools.Utils.Geometry;
using Applitools.VisualGrid;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[Category("visual")]
public class PricingEyesTests : BaseTest
{
    private VisualGridRunner _runner = null!;
    private Eyes _eyes = null!;
    private PricingPage _pricingPage = null!;

    [OneTimeSetUp]
    public void CreateRunner() => _runner = new VisualGridRunner(new RunnerOptions().TestConcurrency(5));

    [SetUp]
    public async Task OpenEyes()
    {
        await Page.Clock.SetFixedTimeAsync(new DateTime(2026, 10, 10, 9, 0, 0, DateTimeKind.Utc));
        _pricingPage = new PricingPage(Page);
        _eyes = new Eyes(_runner);
        _eyes.SetConfiguration(EyesConfig.ForGrid());
        _eyes.Open(Page, "Shop Web", EvidenceName(), new RectangleSize(1280, 800));
    }

    [Test]
    [Description("No assertion: the Ultrafast Grid compares this checkpoint; this class's [OneTimeTearDown] fails the run on any difference, reviewed in the Applitools dashboard.")]
    public async Task Should_MatchApprovedPlanTable_When_PlansLoad()
    {
        await _pricingPage.OpenAsync();

        _eyes.Check("Pricing.PlanTable", Target.Region(_pricingPage.PlanTable)
            .Layout(_pricingPage.PromoPrice)
            .Ignore(_pricingPage.PromoBadge));
    }

    [TearDown]
    public void CloseEyes() => _eyes.CloseAsync();

    [OneTimeTearDown]
    public void GateOnEyesResults()
    {
        var unresolved = EyesConfig.Unresolved(_runner.GetAllTestResults(false));

        Assert.That(unresolved, Is.Empty, "Applitools checkpoints that differ from their baseline — accept or reject them in the dashboard");
    }
}
```

- `PricingPage` is the page object from `references/playwright-snapshots.md` §5. Eyes captures **at `Check`
  time**, so `OpenAsync()` returning on the visible table is what makes the checkpoint stable.
- **Cleanup lives in the hooks**, never in a `try`/`finally` in the test: `CloseAsync()` in the class's
  `[TearDown]` ends the Eyes test whether the test passed or threw, and NUnit runs it before `BaseTest`'s
  teardown closes the context.
- **The runner is an instance field built in `[OneTimeSetUp]`.** NUnit runs a fixture's tests on one instance,
  one after another (`BaseTest`'s `ParallelScope.Self`), and parallel fixtures each own their runner — no
  `static` runner shared across workers. The cost: the gate fires once per class, and `TestConcurrency` applies
  per class, so size it to the account's limit divided by the worker count.
- **The gate is `GateOnEyesResults`.** NUnit reports a failed `[OneTimeTearDown]` against the fixture, and the
  run fails; the message lists each unresolved checkpoint with its dashboard URL. Never `Close(true)` per test:
  it waits for that test alone and serializes the grid.
- The Eyes test name is `BaseTest`'s `EvidenceName()` (`<Class>.<Test>`), the same name as the failure
  evidence.
- **The test has no assertion, and says so** in `[Description("No assertion: …")]` — the NUnit form of the
  TS lane's `no-assertion` annotation (plan D50).

## 5. Match levels — the real differentiator

`Target.Window()` (the viewport; `.Fully()` for the whole page) or `Target.Region(locator)` starts the check
settings. Each region call takes an `ILocator`, a CSS selector string, an `IElementHandle`, or a `Region`:

| Call | Effect |
|---|---|
| (default) Strict | Visual AI: "would a person call these the same?" — the right default for stable UI |
| `.Layout(locator)` / `.Layout()` | Only the structure and position must match; text, numbers and images may change |
| `.Content(locator)` / `.Content()` | Structure and text must match; colours and exact pixels may not |
| `.Strict(locator)` | A Strict region inside a looser check |
| `.IgnoreColors(locator)` / `.IgnoreColors()` | Structure and content, colours ignored |
| `.Ignore(locator)` | Not compared at all |
| `.Floating(locator, maxUp, maxDown, maxLeft, maxRight)` | May move by that many pixels in each direction |
| `.Accessibility(locator, AccessibilityRegionType.LargeText)` | Marks a region for Applitools' contrast checks |
| `.WithName(name)` | Names the checkpoint when `Check(settings)` is called without a tag |

**There is no pixel-ratio knob.** Reach for `Layout` before `Ignore`: an ignored region drops coverage, a
Layout region keeps its structure under test while its data changes.

## 6. CI and the review

The SDK talks to the cloud, so the nightly job runs `dotnet test UiTests -c Release --filter TestCategory=visual`
with `APPLITOOLS_API_KEY` and `APPLITOOLS_BATCH_ID` set — on the UI job's runner, with its browser install and
credential fetch (`qa/cicd/dotnet/skills/ci-pipelines`). Rendering happens on the grid, so it does not need the
pinned image.

1. The run uploads each checkpoint; the grid renders every configured environment and compares each with
   its baseline.
2. A class with a difference fails its `[OneTimeTearDown]`, and the run fails.
3. A reviewer accepts or rejects in the dashboard — once for all environments of a checkpoint. Accepting
   updates the baseline.
4. On merge, the accepted renders are the branch baseline for the next run.

A functional failure in an Eyes class still gets `BaseTest`'s trace, screenshot and video.

## Anti-patterns

- **The package named after the vendor plus `.Playwright`.** It is not on NuGet. *Fix:* `Eyes.Playwright`.
- **`await` on an Eyes call, or a hunt for `OpenAsync` / `CheckAsync`.** The SDK is synchronous; `CloseAsync()`
  returns `void`. *Fix:* §2.
- **`try { … } finally { _eyes.Close(false); }` in a test.** *Fix:* `CloseAsync()` in the class's `[TearDown]`.
- **A `static` runner shared by every class.** Static mutable state across parallel workers. *Fix:* one runner
  per class, built in `[OneTimeSetUp]`, gated in `[OneTimeTearDown]`.
- **`Close(true)` per test as the gate.** *Fix:* the runner's results, once per class.
- **`AllureApi.AddLink` or `AddAttachment` in `[OneTimeTearDown]`.** No test is running; nothing is recorded.
  *Fix:* `AllureApi.AddGlobalAttachment`.
- **`ClassicRunner` and expecting a cross-browser grid.** *Fix:* `VisualGridRunner` and the `Configuration`
  matrix.
- **`Task.Delay` or `WaitForTimeoutAsync` before `Check`.** *Fix:* the page object's ready signal.
- **`Ignore` where `Layout` would do.** *Fix:* Layout keeps the structure asserted.
- **A new batch per class or shard.** *Fix:* one `APPLITOOLS_BATCH_ID` per run.
- **An Eyes test without the `[Description("No assertion: …")]`.** It reads as a forgotten assertion.
- **A `Version=` on the `PackageReference` or a floating `3.*`.** *Fix:* `Directory.Packages.props` pins 1.37.49.

## Rules

- Derive from `BaseTest`; reach the state through page objects; freeze the clock in `[SetUp]`.
- `VisualGridRunner` per class in `[OneTimeSetUp]`; `Eyes` per test in `[SetUp]`; `CloseAsync()` in
  `[TearDown]`; `GetAllTestResults(false)` and an assertion on the unresolved list in `[OneTimeTearDown]`.
- Prefer a match level (`Layout`) over hiding a region; there is no pixel budget.
- `APPLITOOLS_API_KEY` from the secret store only; one batch id per run.
- The test states its missing assertion in `[Description("No assertion: …")]`.
- `Eyes.Playwright` 1.37.49 through central package management.

## Cross-references

- `references/playwright-snapshots.md` — the free sibling, and `PricingPage`.
- `references/percy.md` — the hosted pixel-diff sibling.
- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest` and page objects.
- `qa/cicd/dotnet/skills/ci-pipelines` — the schedule gate and the secret store.
- `qa/reporting/dotnet/skills/test-reports` — Allure.NUnit wiring, global attachments.
- `qa-typescript:visual-regression` (`@applitools/eyes-playwright`), `qa-java:visual-regression`
  (`eyes-playwright-java5`).
