# Visual Regression — Playwright Snapshots (.NET / NUnit)

The .NET port of the canonical `qa-visual-regression-typescript`. Same concepts,
same flake-control discipline, same CI-container baseline rule — re-expressed in `Microsoft.Playwright`
+ `Microsoft.Playwright.NUnit` idioms. **One key difference from the TS runner:** .NET has **no
`--update-snapshots` CLI flag** — you regenerate a baseline by deleting it and re-running (inside the
CI container). That distinction is called out throughout.

## When to use this skill

Use when a Playwright **.NET / NUnit** test must detect **unintended visual change** — a CSS
regression, a broken layout, a shifted component — by comparing a fresh screenshot against a
committed baseline. This is the **built-in, free** layer: Playwright does the capture and the pixel
diff, baselines live in your repo, you own the flakiness budget. Reach for Percy or Applitools
(`applitools`) only for hosted baseline management, a review UI, or visual-AI diffing — see the matrix.

Visual regression is an **assertion layer** on top of your existing page objects and specs. You do
not author new page objects here — you add a screenshot assertion to a flow
`qa-ui-test-author-playwright-dotnet` already built.

## Decision matrix — which assertion, which tool

| Need | Use | Why |
|------|-----|-----|
| Visual diff of a page/element, auto-retried + stabilized | `await Expect(Page).ToHaveScreenshotAsync()` | Waits for the page to settle; retries until match or timeout |
| Visual diff of an element only | `await Expect(locator).ToHaveScreenshotAsync()` | Scopes the capture; far less flaky than full page |
| Compare an arbitrary buffer you produced | `await Expect(Page).ToMatchSnapshotAsync(bytes, "name.png")` | Raw byte snapshot you control (generated PDF/SVG, post-processed shot) |
| Free, baselines in your repo, you own diffing | **this skill** | No SaaS, no per-screenshot cost, full control |
| Hosted baselines + PR review UI | Percy | Offloads baseline mgmt + review; paid |
| Visual-AI diffing + cross-browser grid | Applitools | Ignores anti-aliasing noise via AI; paid |

**Rule of thumb:** `ToHaveScreenshotAsync()` for anything rendered in the browser (it stabilizes and
retries). `ToMatchSnapshotAsync()` only for bytes you generated. Prefer **element** screenshots over
**full-page** — they are dramatically less flaky.

## Setup

```xml
<!-- Tests.csproj -->
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.50.0" />
  <PackageReference Include="NUnit" Version="4.*" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.*" />
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
</ItemGroup>
```

```bash
pwsh bin/Debug/net8.0/playwright.ps1 install --with-deps chromium
```

Inheriting `PageTest` gives you `Page` and the `Expect` assertion entry point. There is no
`playwright.config.ts` equivalent — screenshot defaults are passed **per assertion** via the options
object, or centralized in a base test class. The expect timeout (how long `ToHaveScreenshotAsync`
auto-retries) is set globally:

```csharp
// BaseVisualTest.cs — centralize the screenshot policy so individual tests stay clean.
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;

public abstract class BaseVisualTest : PageTest
{
    // How long ToHaveScreenshotAsync auto-retries the capture+compare.
    public override BrowserNewContextOptions ContextOptions() => new() { BaseURL = "http://localhost:3000" };

    protected static LocatorAssertionsToHaveScreenshotOptions Defaults() => new()
    {
        MaxDiffPixelRatio = 0.01,                       // ≤1% of pixels may differ
        Animations = ScreenshotAnimations.Disabled,     // freeze CSS animations/transitions
        Scale = ScreenshotScale.Css,                    // CSS pixels, stable across DPI
    };
}
```

```csharp
// SetUp once (e.g. in a [SetUpFixture]) — global retry budget for screenshot assertions.
SetDefaultExpectTimeout(10_000);
```

## Where baselines live & how they're named

On first run Playwright writes a baseline; on later runs it compares against it. The naming carries a
platform suffix (`linux` / `darwin` / `windows`):

```
Tests/
  DashboardTests.cs
  DashboardTests.cs-snapshots/
    revenue-card-chromium-linux.png      ← {name}-{browser}-{platform}.png
```

The `-{platform}` suffix is the crux of the **cross-platform rendering problem**: a baseline
generated on a dev Mac (`...-darwin.png`) will not match — and is not even looked up — on a Linux
runner. The fix is in "The CI baseline discipline". Commit the `*-snapshots/` directories:
**baselines are versioned build artifacts, not secrets.**

## Core pattern 1 — element screenshot on a page-object-driven flow

The page object exposes intent and the locator; the test adds the visual assertion. No selectors in
the test.

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
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
[Parallelizable(ParallelScope.Self)]
public sealed class DashboardTests : BaseVisualTest
{
    [Test]
    public async Task Should_Match_RevenueCardBaseline_When_DashboardLoads()
    {
        var dashboard = new DashboardPage(Page);
        await dashboard.GotoAsync();
        await dashboard.WaitUntilLoadedAsync();   // stabilize on a condition first…

        await Expect(dashboard.RevenueCard).ToHaveScreenshotAsync("revenue-card.png", new()
        {
            MaxDiffPixelRatio = 0.01,
            Animations = ScreenshotAnimations.Disabled,
        });                                        // …then assert (auto-retries)
    }
}
```

`ToHaveScreenshotAsync()` auto-retries the capture+compare until it matches or the expect timeout
elapses, and waits for fonts/animations to settle. You still stabilize *application* state (data
loaded, spinners gone) yourself — Playwright cannot know your spinner is "done".

## Core pattern 2 — taming flakiness

The four sources of false diffs and the deterministic fix for each:

```csharp
[Test]
public async Task Should_Match_ProfilePage_When_DynamicRegionsNeutralized()
{
    await Page.GotoAsync("/profile");

    // 1) Fonts not yet rendered → wait on the condition, not a timeout.
    await Page.EvaluateAsync("document.fonts.ready");

    await Expect(Page).ToHaveScreenshotAsync("profile.png", new()
    {
        // 2) Dynamic content (timestamps, avatars) → mask it (painted as a solid box).
        Mask = new[] { Page.GetByTestId("last-seen"), Page.Locator("img.gravatar") },
        MaskColor = "#FF00FF",

        // 3) Anti-aliasing / sub-pixel noise → small tolerance. Prefer ratio over absolute.
        MaxDiffPixelRatio = 0.02,
        Threshold = 0.2,   // per-pixel color sensitivity (0 strict … 1 loose); default 0.2

        // 4) Animations / carets → freeze them.
        Animations = ScreenshotAnimations.Disabled,
        Caret = ScreenshotCaret.Hide,
    });
}
```

Knobs, precisely:

- **`MaxDiffPixels`** — absolute number of differing pixels allowed. Brittle across viewport sizes.
- **`MaxDiffPixelRatio`** — fraction (0–1) of differing pixels allowed. **Prefer this** — scales with
  image size.
- **`Threshold`** — per-pixel YIQ color-distance sensitivity (0 exact … 1 anything). Decides whether
  a pixel counts as different *at all* before the ratio is applied. Default `0.2`.
- **`Mask` / `MaskColor`** — overpaint dynamic regions so they can never diff.
- **`Animations = ScreenshotAnimations.Disabled`** — sets CSS animations/transitions to end state.
- **`Caret = ScreenshotCaret.Hide`** — hides the text caret (a classic 1px flake).
- **`StylePath`** — inject a CSS file to neutralize elements (carets, live widgets) across every shot.
- **`FullPage = true`** — whole scrollable page (flakier; mask aggressively).
- **`Clip`** — capture a fixed rectangle.

`StylePath` for repo-wide stabilization:

```css
/* snapshot.css */
*, *::before, *::after { transition: none !important; animation: none !important; }
[data-testid="live-clock"], .chat-widget { visibility: hidden !important; }
```

```csharp
await Expect(Page).ToHaveScreenshotAsync("home.png", new()
{
    StylePath = "snapshot.css",
    Animations = ScreenshotAnimations.Disabled,
    MaxDiffPixelRatio = 0.01,
});
```

## Core pattern 3 — `ToMatchSnapshotAsync()` for bytes you produced

Use only when you own the buffer — not for live page captures (those should use
`ToHaveScreenshotAsync()` so they stabilize and retry).

```csharp
[Test]
public async Task Should_Match_GeneratedInvoicePdf_Baseline()
{
    var pdf = await Page.PdfAsync(new() { Format = "A4" });
    await Expect(Page).ToMatchSnapshotAsync(pdf, new() { Name = "invoice.pdf" });
}
```

`ToMatchSnapshotAsync()` does **not** auto-retry and does **not** stabilize. For live pages
`ToHaveScreenshotAsync()` is strictly better.

## The CI baseline discipline (the part everyone gets wrong)

Baselines are platform-specific. The only reliable workflow:

1. **Never commit baselines generated on your dev box.** A `...-darwin.png` baseline is useless to a
   Linux runner.
2. **Generate/update baselines inside the same container CI uses.** Run CI's image locally, or a
   dedicated update step in CI. **.NET has no `--update-snapshots` flag** — you regenerate by
   **deleting the baseline PNG and re-running** (a missing baseline is auto-created on the next run):

   ```bash
   # Reproduce CI's exact rendering via the official image (tag must match your Microsoft.Playwright version):
   docker run --rm -v "$(pwd):/work" -w /work mcr.microsoft.com/playwright/dotnet:v1.50.0-noble bash -c '
     rm -f Tests/*.cs-snapshots/*-linux.png   # drop stale baselines
     dotnet test                              # missing baselines are regenerated, then compared
   '
   ```

3. **Regeneration discipline.** Delete-and-rerun deliberately when a change is *intended*, review the
   regenerated PNGs in the diff, and commit them in the same PR as the UI change. Never automate
   blanket baseline deletion in the normal test run — that makes every run "pass".
4. **Gate regeneration behind a manual/labelled CI job**, not a local push. See the github-actions
   cross-link for the gated `update-baselines` job pattern.

On a normal failure Playwright writes `*-actual.png`, `*-expected.png`, `*-diff.png` into the test
output. Upload them as artifacts and attach to the report:

```yaml
# inside your test job (see qa-ci-pipelines-dotnet for the full pipeline)
- name: Upload visual diff artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-visual-diffs
    path: '**/test-results/**/*-{actual,expected,diff}.png'
    retention-days: 7
```

Attach the diff into Allure so reviewers see it inline (cross-link `qa-allure-reporting-dotnet`):

```csharp
[TearDown]
public void AttachVisualDiff()
{
    if (TestContext.CurrentContext.Result.Outcome.Status != NUnit.Framework.Interfaces.TestStatus.Failed)
        return;
    foreach (var png in Directory.EnumerateFiles(TestContext.CurrentContext.WorkDirectory, "*-diff.png",
                 SearchOption.AllDirectories))
        AllureApi.AddAttachment("visual-diff", "image/png", png);
}
```

## Anti-patterns

- **Committing dev-box baselines.** `...-darwin.png` fails/flakes on Linux CI. *Fix:* the Docker
  delete-and-rerun workflow above.
- **`await Page.WaitForTimeoutAsync(500)` before the screenshot.** Flaky and slow. *Fix:* wait on a
  condition (`document.fonts.ready`, spinner hidden, `Locator.WaitForAsync`), then assert —
  `ToHaveScreenshotAsync()` auto-retries the rest.
- **Full-page screenshots of a page full of dynamic data.** Guaranteed flake. *Fix:* screenshot the
  **element**; `Mask` the dynamic bits; `StylePath` to neutralize globally.
- **Cranking `MaxDiffPixelRatio` to 0.2 to "make it pass".** Blinds the test to real regressions.
  *Fix:* `Mask` the specific flaky region; keep the ratio tight (≤0.02).
- **Auto-deleting baselines in the default test run.** Every run silently regenerates, so nothing is
  caught. *Fix:* delete only via a deliberate, gated step.
- **Using `ToMatchSnapshotAsync()` for a live page.** No stabilization, no retry → flaky. *Fix:*
  `ToHaveScreenshotAsync()` for anything the browser renders.
- **`.gitignore`-ing `*-snapshots/`.** Then CI has nothing to compare against. *Fix:* commit
  baselines; they are versioned artifacts.

## Examples

**End-to-end: a component visual gate that survives CI.**

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Self)]
public sealed class PricingTests : BaseVisualTest
{
    [Test]
    public async Task Should_Match_PricingTableBaseline_When_PlansLoaded()
    {
        var pricing = new PricingPage(Page);
        await pricing.GotoAsync();
        await pricing.WaitUntilPlansRenderedAsync();          // condition, not sleep
        await Page.EvaluateAsync("document.fonts.ready");      // fonts settled

        await Expect(pricing.Table).ToHaveScreenshotAsync("pricing-table.png", new()
        {
            Mask = new[] { pricing.PromoBanner },   // rotates daily — never diff it
            MaxDiffPixelRatio = 0.01,
            Animations = ScreenshotAnimations.Disabled,
            Caret = ScreenshotCaret.Hide,
        });
    }
}
```

Baseline lifecycle for this test:
1. Dev makes an intended CSS change.
2. In the CI image, `rm` the stale `pricing-table-chromium-linux.png` and `dotnet test` to regenerate.
3. Reviews the regenerated PNG in the diff, commits it with the CSS change.
4. CI compares against it on every PR; an *unintended* change now fails with a `-diff.png` artifact.

## Rules (hard constraints)

- Stabilize **application** state on a condition before asserting; never `WaitForTimeoutAsync`. Let
  `ToHaveScreenshotAsync()` auto-retry the rendering settle.
- Prefer **element** screenshots over full-page; `Mask` every dynamic region.
- Prefer `MaxDiffPixelRatio` over `MaxDiffPixels`; keep tolerance tight and mask noise rather than
  loosening the budget.
- **Generate baselines inside the CI container**, never on the dev box. Baselines are committed,
  versioned build artifacts — not secrets, not `.gitignore`-d.
- **.NET has no `--update-snapshots`** — regenerate by deleting the baseline and re-running, as a
  deliberate, reviewed, gated action; never blanket-delete in the default test run.
- On failure, upload `*-actual/-expected/-diff.png` as artifacts and attach the diff to the report.
- `ToHaveScreenshotAsync()` for browser-rendered content; `ToMatchSnapshotAsync()` only for bytes you
  produced.
- Page objects expose intent + locators; the test owns the visual assertion. No selectors in tests.
- Async all the way — `await` every Playwright call; no `.Result` / `.Wait()`.

## Cross-references

- `qa-visual-regression-typescript` — the **canonical** skill this ports
  (`@playwright/test` `toHaveScreenshot()`, `--update-snapshots`, `playwright.config.ts` defaults).
- `qa-visual-regression-java` — the Java / TestNG sibling
  (`assertThat(page).hasScreenshot()`).
- `qa-ui-test-author-playwright-dotnet` — the page objects/specs these assertions layer on top of.
- `references/percy.md` (`percy`, next) — hosted baseline management + PR review UI.
- `references/applitools.md` — visual-AI diffing + cross-browser grid.
- `qa-ci-pipelines-dotnet` — artifact upload, the container-baseline discipline, the
  gated `update-baselines` job.
- `qa-allure-reporting-dotnet` — attach `-diff.png` images to the test report.
