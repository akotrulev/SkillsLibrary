# Visual Regression — Applitools Eyes (.NET / NUnit)

The .NET port of the canonical `qa-visual-regression-typescript`. Same visual-AI model, same
Ultrafast Grid matrix, same dashboard review workflow — re-expressed in `Applitools.Playwright` +
`Microsoft.Playwright.NUnit` idioms. Applitools Eyes uploads the rendered page to the **Ultrafast
Grid**, re-renders it server-side across a configured browser/viewport/device matrix, and diffs with
**AI-based matching** that ignores anti-aliasing / sub-pixel noise — plus **match levels** (Strict /
Layout / Content / Ignore-colors). That match-level control is the real differentiator versus Percy's
server-side **pixel** diff and the built-in **byte/pixel** diff.

This is an **assertion layer** on top of the page objects and specs
`qa-ui-test-writer-playwright-dotnet` already authored. You do not write new page objects here — you
add `Eyes.Open` / `Eyes.Check` / `Eyes.Close` around an existing flow.

## Why graduate from Percy (pixel) to Applitools (visual-AI)

Percy already solved the cross-platform rendering problem by rendering server-side. Applitools
goes further on **how the diff is judged** and **how many environments render at once**:

| | Percy | **Applitools Eyes (this skill)** |
|---|---|---|
| What leaves the test | A DOM snapshot, uploaded by the `percy exec` agent | The rendered page, uploaded by the **SDK directly** (no agent) |
| How the diff is judged | Server-side **pixel** diff | Server-side **AI** match — ignores anti-aliasing / sub-pixel noise |
| Tolerance lever | `percyCSS` hide + `scope` (no pixel knob) | **Match levels** (Strict / Layout / Content / Ignore-colors) + region ignores |
| Dynamic content | Hide it with `percyCSS` | **`Target.Layout(region)`** — structure matches, text may differ |
| Cross-browser/device | Re-renders at configured widths | **Ultrafast Grid** — a real browser/viewport/device **matrix** from one run |
| Process model | Local `percy exec` agent wraps the run | **None** — SDK calls the cloud; just `APPLITOOLS_API_KEY` in env |
| Baselines | Percy cloud, keyed by git branch, review UI | **Applitools dashboard**, keyed by app/test/branch, review UI |
| Gate | GitHub/GitLab status check | Runner's **aggregated results** fail the build; dashboard link |
| Cost | Paid | Paid (typically the most expensive of the three) |

State the contrast plainly: **Applitools is AI match (not pixel), match levels (not just hide-or-fail),
and a real cross-browser grid (not just widths)** — and there's **no agent process** to wrap the run.

## Setup

There is **no agent to launch** (the difference from Percy's Node `@percy/cli`): the .NET SDK talks to
the Applitools cloud directly, so the only dependency is the NuGet package.

```xml
<!-- Tests.csproj -->
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.50.0" />
  <PackageReference Include="Applitools.Playwright" Version="3.*" />
  <PackageReference Include="NUnit" Version="4.*" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.*" />
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
</ItemGroup>
```

`APPLITOOLS_API_KEY` is the **only secret** — the SDK reads it from the environment automatically. In CI
it comes from the secret store (see the ci-pipelines cross-link), never committed. Locally `export
APPLITOOLS_API_KEY=<key>`.

## The Eyes model + the Ultrafast Grid

Three objects, one lifecycle:

- **`VisualGridRunner`** — the runner that ships checkpoints to the **Ultrafast Grid**, which renders
  them server-side across your configured browser/viewport/device matrix. Construct it with a
  concurrency cap: `new VisualGridRunner(new RunnerOptions().TestConcurrency(5))`. (Its sibling
  `ClassicRunner` renders locally with one environment — use `VisualGridRunner` to get the grid, the
  whole point of Applitools over `playwright-snapshots`/`percy`.)
- **`Eyes`** — one visual test session, bound to a runner: `new Eyes(runner)`. `Eyes.Open(page, app,
  test, viewport)` starts it; `Eyes.Check(...)` adds a checkpoint; `Eyes.Close(false)` ends it
  **without throwing inline**.
- **`runner.GetAllTestResults(true)`** — called **once at suite end**, it blocks until every checkpoint
  across every `Eyes` has rendered + diffed on the grid, aggregates the results, and (with `true`)
  throws if any test had a mismatch or error. **This is the gate** — not `Eyes.Close`.

A `Configuration` with `AddBrowser(width, height, BrowserType)` / `AddDeviceEmulation(...)` is what
makes **one local run fan out to a cross-browser/device render matrix** server-side — the thing neither
`playwright-snapshots` nor `percy` does natively.

## Configuration — the render matrix

```csharp
// Support/EyesConfig.cs
using Applitools;
using Applitools.VisualGrid;

public static class EyesConfig
{
    public static Configuration Build()
    {
        var config = new Configuration();
        // One batch groups every test in this run in the dashboard (see "Batching" below).
        config.SetBatch(new BatchInfo("FlexInvest Web — Visual"));

        // Each AddBrowser/AddDeviceEmulation adds an environment the Ultrafast Grid renders + diffs.
        // One Eyes.Check() therefore produces N checkpoints — the cross-browser/device matrix.
        config.AddBrowser(1280, 800, BrowserType.CHROME);
        config.AddBrowser(1280, 800, BrowserType.FIREFOX);
        config.AddBrowser(1280, 800, BrowserType.SAFARI);
        config.AddBrowser(375, 812, BrowserType.EDGE_CHROMIUM);
        config.AddDeviceEmulation(DeviceName.iPhone_11, ScreenOrientation.Portrait);
        config.AddDeviceEmulation(DeviceName.Pixel_5, ScreenOrientation.Portrait);
        return config;
    }
}
```

`eyes.SetConfiguration(EyesConfig.Build())` before `Eyes.Open` applies it. The matrix lives in code, in
the repo — it's not a secret; only the API key is.

## Core pattern — `Open` / `Check` / `Close` + `GetAllTestResults`

The page object exposes intent; the test stabilizes **application** state on a condition, then checks.
No selectors in the test, no fixed waits. `Eyes.Close(false)` per test; the runner gates at suite end.
Share **one runner** across the fixture via `[OneTimeSetUp]`/`[OneTimeTearDown]`.

```csharp
// Pages/DashboardPage.cs
using Microsoft.Playwright;

public sealed class DashboardPage
{
    private readonly IPage _page;
    public ILocator RevenueCard { get; }

    public DashboardPage(IPage page)
    {
        _page = page;
        RevenueCard = page.GetByTestId("revenue-card");
    }

    public Task GotoAsync() => _page.GotoAsync("/dashboard");

    /// <summary>Resolves once the card's data has rendered — a condition, never a fixed wait.</summary>
    public Task WaitUntilLoadedAsync() =>
        RevenueCard.GetByRole(AriaRole.Status).WaitForAsync(new() { State = WaitForSelectorState.Hidden });
}
```

```csharp
// DashboardTests.cs
using Applitools;
using Applitools.Playwright;
using Applitools.VisualGrid;
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
[Parallelizable(ParallelScope.Self)]
public sealed class DashboardTests : PageTest
{
    private static readonly VisualGridRunner Runner =
        new(new RunnerOptions().TestConcurrency(5));   // one runner for the suite

    [Test]
    public async Task Should_Match_Dashboard_When_Loaded()
    {
        var eyes = new Eyes(Runner);
        eyes.SetConfiguration(EyesConfig.Build());     // API key read from env automatically
        await eyes.OpenAsync(Page, "FlexInvest Web", "Dashboard — revenue card",
            new RectangleSize(1280, 800));

        try
        {
            var dashboard = new DashboardPage(Page);
            await dashboard.GotoAsync();
            await dashboard.WaitUntilLoadedAsync();    // stabilize on a condition first…

            await eyes.CheckAsync("Dashboard", Target.Window().Fully());  // …then capture the checkpoint
        }
        finally
        {
            await eyes.CloseAsync(false);              // end session WITHOUT throwing inline
        }
    }

    [OneTimeTearDown]
    public void GateOnVisualResults()
    {
        // Blocks until the grid finishes; `true` throws if any test mismatched — THE GATE.
        Runner.GetAllTestResults(true);
    }
}
```

Why `Eyes.Close(false)` then `GetAllTestResults(true)`: `Close(true)` would throw the *first* time any
single test mismatches, aborting the rest before they render on the grid. Passing `false` lets every
test finish; the runner then aggregates **all** results and fails the build once, at suite end, with a
complete picture. The `Eyes`/`Target` calls have async overloads (`OpenAsync`/`CheckAsync`/`CloseAsync`)
— use them, async-all-the-way; `GetAllTestResults` is the one blocking call (a deliberate barrier at
teardown). Eyes captures **at `Check` time**, like Percy — so stabilize before each `Check`.

## Match levels — the real differentiator

A match level tells the AI *how* to compare a checkpoint against its baseline. Set it per-check via the
`Target` fluent API; this is the analogue of Percy's `percyCSS`-hide, but richer — prefer a **region
match level** over hiding the region entirely:

```csharp
await eyes.CheckAsync("Account summary", Target.Window().Fully()
    // Whole-page level: Strict is the default ("looks the same to a human").
    .Layout("[data-testid=\"balance-figures\"]")    // structure must match; the NUMBERS may change
    .Ignore("[data-testid=\"last-login\"]")         // ignore entirely (timestamp)
    .Floating("[data-testid=\"toast\"]", 5, 5, 5, 5)); // may shift up to 5px in any direction
```

The levels, precisely:

- **Strict** (default) — AI match: "would a human call these the same?" Ignores anti-aliasing /
  rendering noise but catches real visual changes. The right default for stable UI.
- **Layout** — only the **structure/position** of elements must match; their **content** (text,
  numbers, images) may differ. *The killer feature for dynamic data* — baseline a populated page once
  and it stays green as the data changes, while a broken layout still fails.
- **Content** — like Layout but also compares text content (structure + text, not exact pixels/colors).
- **Ignore-colors** — match structure + content but ignore color (theme/branding churn).

Region levels are the surgical version: `Target.Window().Fully().Layout(locator)` keeps the page Strict
but treats one region as Layout. Region ignores — `.Ignore(locator)` (drop entirely), `.Layout(locator)`,
`.Floating(locator, ...)` (element may shift within a pixel margin), `.Accessibility(locator,
AccessibilityRegionType.LargeText)` — are the analogue of masking, but expressed as intent.

**There is no per-call pixel-ratio knob** (no `MaxDiffPixelRatio` like `playwright-snapshots`). The AI plus the match level
*is* the tolerance lever. Reach for **Layout** before you reach for ignore.

## Batching + the dashboard

`BatchInfo` groups one run's tests under a single entry in the **Applitools dashboard** (set it on the
`Configuration`, as above). The dashboard is the hosted **baseline store + review UI** — the analogue of
Percy's. Baselines are keyed by **app / test / branch**; you accept or reject diffs there, and an accept
updates the baseline. Same "no in-repo baselines, no `-{platform}` naming" story as Percy: the repo
holds no PNGs.

To group a sharded CI run into one dashboard batch, set a stable batch id across shards:

```csharp
var batch = new BatchInfo("FlexInvest Web — Visual");
var batchId = Environment.GetEnvironmentVariable("APPLITOOLS_BATCH_ID");
if (!string.IsNullOrEmpty(batchId)) batch.Id = batchId;   // same value across all shards → one batch
config.SetBatch(batch);
```

## CI integration + the gate

There's **no agent to wrap the command** (the difference from Percy's `percy exec`): the SDK talks to
the cloud directly, so CI just runs `dotnet test` with `APPLITOOLS_API_KEY` in env. The build fails when
`runner.GetAllTestResults(true)` throws because an **unresolved diff** exists in the dashboard.

```yaml
# inside your test job — see qa-ci-pipelines-dotnet for the full pipeline
- name: Visual tests (Applitools)
  env:
    APPLITOOLS_API_KEY: ${{ secrets.APPLITOOLS_API_KEY }}   # from the secret store; never inline
    APPLITOOLS_BATCH_ID: ${{ github.run_id }}-${{ github.run_attempt }}  # one batch across shards
  run: dotnet test
```

Link the dashboard batch URL into Allure so reviewers jump straight to it (cross-link
`qa-test-reports-dotnet`):

```csharp
[OneTimeTearDown]
public void LinkAndGate()
{
    var summary = Runner.GetAllTestResults(false);   // false: collect without throwing here…
    foreach (var c in summary.GetAllResults())
    {
        var url = c.TestResults?.AppUrls?.Batch;
        if (!string.IsNullOrEmpty(url))
        {
            AllureApi.AddTestAttachment("Applitools dashboard", "text/uri-list",
                System.Text.Encoding.UTF8.GetBytes(url));
            break;
        }
    }
    if (summary.GetAllResults().Any(r => r.Exception != null ||
        r.TestResults?.Status == TestResultsStatus.Unresolved))
        throw new Exception("Applitools: unresolved visual diffs — review the dashboard batch."); // …gate
}
```

The review-UI workflow, concretely:
1. PR runs `dotnet test`; the SDK uploads to the Ultrafast Grid, which renders + diffs against the
   branch baseline.
2. `GetAllTestResults(true)` fails the build if any environment is **Unresolved** (new diff).
3. A reviewer accepts/rejects in the Applitools dashboard. Accepting updates the baseline.
4. On merge, the accepted checkpoints become the branch baseline for the next PR.

## Anti-patterns

- **`Eyes.Close(true)` (or `Eyes.Close()`) per test as the gate.** It throws on the first mismatch and
  aborts the rest before they render. *Fix:* `Eyes.Close(false)` per test; gate once at suite end with
  `runner.GetAllTestResults(true)`.
- **Using `ClassicRunner` and expecting a cross-browser grid.** ClassicRunner renders one local
  environment. *Fix:* `VisualGridRunner` + `Configuration.AddBrowser`/`AddDeviceEmulation`.
- **`await Page.WaitForTimeoutAsync(500)` before `Eyes.Check`.** Eyes captures at call time; a sleep is
  flaky and slow. *Fix:* wait on a condition (`document.fonts.ready`, spinner hidden, `Locator.WaitForAsync`).
- **`.Result` / `.Wait()` on the async Eyes calls.** Violates async-all-the-way. *Fix:* `await
  OpenAsync`/`CheckAsync`/`CloseAsync`; only `GetAllTestResults` is the deliberate teardown barrier.
- **Hiding a dynamic region when Layout would do.** Ignoring drops coverage. *Fix:* `Target.Layout(
  region)` — structure stays asserted, only content is allowed to vary.
- **Committing `*-snapshots/` PNGs alongside Applitools.** Baselines live in the dashboard. *Fix:*
  delete them; rely on the dashboard baseline.
- **Hardcoding / logging `APPLITOOLS_API_KEY`.** It's a write credential. *Fix:* env only, from the CI
  secret store, read lazily by the SDK, never echoed.
- **A new `BatchInfo` per shard.** Splits one run across many dashboard batches. *Fix:* one stable
  `APPLITOOLS_BATCH_ID` env var shared across shards.
- **Full-page Strict checks on a page full of live data.** Chatty reviews. *Fix:* `Target.Region(
  locator)` for the stable part, `Layout`/`Ignore` regions for the live bits.

## Examples

**End-to-end: a pricing-table visual gate across a browser/device grid, reviewed in the dashboard.**

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Self)]
public sealed class PricingTests : PageTest
{
    private static readonly VisualGridRunner Runner =
        new(new RunnerOptions().TestConcurrency(5));

    [Test]
    public async Task Should_Match_PricingTable_When_PlansLoaded()
    {
        var eyes = new Eyes(Runner);
        eyes.SetConfiguration(EyesConfig.Build());
        await eyes.OpenAsync(Page, "FlexInvest Web", "Pricing — plan table",
            new RectangleSize(1280, 800));

        try
        {
            var pricing = new PricingPage(Page);
            await pricing.GotoAsync();
            await pricing.WaitUntilPlansRenderedAsync();          // condition, not sleep
            await Page.EvaluateAsync("document.fonts.ready");      // fonts settled before capture

            await eyes.CheckAsync("Pricing table",
                Target.Region("[data-testid=\"pricing-table\"]")  // element, not full page
                    .Layout("[data-testid=\"promo-price\"]")      // price A/B-tests → Layout, not ignore
                    .Ignore("[data-testid=\"promo-banner\"]"));   // rotates daily → ignore entirely
        }
        finally
        {
            await eyes.CloseAsync(false);                         // don't throw inline
        }
    }

    [OneTimeTearDown]
    public void GateOnVisualResults() => Runner.GetAllTestResults(true);  // grid finishes → gate
}
```

Lifecycle for this test:
1. Dev makes an intended CSS change to the pricing table.
2. CI runs `dotnet test`; the SDK ships one checkpoint per configured browser/device to the grid, which
   renders + AI-diffs each vs the branch baseline.
3. `GetAllTestResults(true)` fails the build; the dev reviews + accepts the diff in the dashboard
   (accepting it on **all** environments at once).
4. On merge, the accepted renders become the branch baseline — the next PR diffs against them.

## Rules (hard constraints)

- Visual regression is an assertion layer on existing page objects/specs — add `Eyes.Check`, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- `VisualGridRunner` (not `ClassicRunner`) + `Configuration.AddBrowser`/`AddDeviceEmulation` — the grid
  is the reason to choose Applitools.
- `Eyes.Close(false)` per test (never inline-throw); gate **once** at suite end with
  `runner.GetAllTestResults(true)`. Async-all-the-way on `OpenAsync`/`CheckAsync`/`CloseAsync`.
- Stabilize **application** state on a condition before `Eyes.Check`; never `WaitForTimeoutAsync` — Eyes
  captures at call time.
- Prefer a **match level** (especially `Target.Layout(region)`) over hiding dynamic content; there is
  **no per-call pixel-ratio knob** — the AI + match level is the lever.
- `APPLITOOLS_API_KEY` is the **only** secret: env-only, from the CI secret store, read lazily by the
  SDK, never logged or committed. No agent process to launch (unlike Percy's `percy exec`).
- No in-repo `*-snapshots/` baselines — baselines live in the **dashboard**, keyed by app/test/branch,
  managed via the review UI. One stable `BatchInfo` id across shards.
- The gate is the runner's **aggregated results**; link the dashboard batch URL into Allure.

## Cross-references

- `qa-visual-regression-typescript` — the **canonical** skill this ports
  (`@applitools/eyes-playwright`, `eyes.check(Target.window().fully())`, `runner.getAllTestResults`).
- `qa-visual-regression-java` — the Java / TestNG sibling (`com.applitools:eyes-playwright-java5`,
  `eyes.check(Target.window().fully())`, `runner.getAllTestResults(false)`).
- `references/percy.md` — the **hosted pixel-diff** sibling: DOM-upload agent +
  server-side pixel diff + review UI. Applitools is the "graduate to visual-AI + match levels + grid" step.
- `references/playwright-snapshots.md` — the **free** sibling: in-repo baselines you
  diff yourself, with the CI-container discipline both Percy and Applitools remove.
- `qa-ui-test-writer-playwright-dotnet` — the page objects/specs `Eyes.Check` is called inside.
- `qa-ci-pipelines-dotnet` — where `APPLITOOLS_API_KEY` is sourced; no agent wrapper needed.
- `qa-test-reports-dotnet` — link the Applitools dashboard batch URL into the report.
