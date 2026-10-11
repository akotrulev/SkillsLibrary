# Visual Regression — Screenshot plus Comparer (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

Microsoft.Playwright has **no screenshot assertion**: `toHaveScreenshot` is a Node test-runner feature, and
the .NET `IPageAssertions` / `ILocatorAssertions` in 1.63 have no screenshot or snapshot member, no options
class for one, and no `--update-snapshots`. This reference builds the free lane from three parts that do
exist:

1. `Locator.ScreenshotAsync(...)` with the determinism options, taken after the page object has reached a
   stable state;
2. an image comparer, `Codeuctivity.ImageSharpCompare`, against a PNG baseline committed in the repo;
3. an NUnit assertion on the measured difference, with the expected, actual and diff images kept and shown
   in Allure's image-diff widget when they differ.

Baselines are written **only** in `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`, the image whose tag
equals the Playwright version. The samples derive from `Example.UiTests.Support.BaseTest`
(`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`), which already keeps a trace, screenshot and
video for every failed test.

## 1. Setup

The comparer, checked on NuGet on 2026-10-11:

| Package | Version | Facts |
|---|---|---|
| `Codeuctivity.ImageSharpCompare` | **4.1.390** | The latest release (published 2026-05-13). Targets net8.0, net9.0 and net10.0. Apache-2.0. One dependency: `SixLabors.ImageSharp` 3.1.12 |

It is a recommendation, not a Playwright fact (plan D9): Playwright names no comparer. `Verify.Playwright`
(3.1.1) was the other candidate; it is a snapshot framework (received/verified files beside the source,
DiffEngine, a byte comparison unless another comparer package is added) rather than a comparison function,
so it would replace this lane's baseline store and update command instead of serving them (plan D58).

**The ImageSharp licence.** `SixLabors.ImageSharp` is under the Six Labors Split License: Apache-2.0 when
it is a *transitive* dependency (installed by a package unrelated to Six Labors, as here), or a direct
dependency of open-source software or of a company under USD 1M annual revenue; otherwise a commercial
licence. Reference only `Codeuctivity.ImageSharpCompare` — a direct `PackageReference` to
`SixLabors.ImageSharp` brings the revenue clause into play.

Add the pin beside the writer's in `Directory.Packages.props`:

```xml
<PackageVersion Include="Codeuctivity.ImageSharpCompare" Version="4.1.390" />
```

and two items to `UiTests.csproj` — the reference (no `Version=` under central package management) and the
project folder, written into the test assembly at build time:

```xml
<ItemGroup>
  <PackageReference Include="Codeuctivity.ImageSharpCompare" />
  <AssemblyAttribute Include="System.Reflection.AssemblyMetadataAttribute">
    <_Parameter1>ProjectDirectory</_Parameter1>
    <_Parameter2>$(MSBuildProjectDirectory)</_Parameter2>
  </AssemblyAttribute>
</ItemGroup>
```

```csharp
using System.Reflection;

namespace Example.UiTests.Support;

public static class ProjectPaths
{
    public static readonly string Root = typeof(ProjectPaths).Assembly
        .GetCustomAttributes<AssemblyMetadataAttribute>()
        .Single(attribute => attribute.Key == "ProjectDirectory")
        .Value!;
}
```

- `dotnet test` runs from `bin/<cfg>/net10.0/`, so a relative baseline path would read and write copies under
  `bin/`, and an update would never reach the repository. The `AssemblyMetadata` item records the project's
  folder when the project builds; `ProjectPaths.Root` reads it back. `qa/dotnet/skills/network-mocking`
  resolves its committed HAR files through the same helper.
- The path is the build machine's. Build and run on the same filesystem — the commands in §7 and §8 do both
  inside the container.

## 2. The baseline store

```
UiTests/Baselines/
└── linux-chromium/
    ├── Pricing.PlanTable.png
    └── Checkout.Summary.png
```

- The folder is `<os>-<browser>`: `<os>` is `linux`, `macos` or `windows`; `<browser>` is `PlaywrightTest.BrowserName`
  (`chromium` from `ui.runsettings`).
- Only `linux-chromium/` is ever written, because baselines come only from the pinned image (§7). A run on a
  Mac looks up `macos-chromium/`, finds nothing and fails with "no baseline" — instead of comparing a macOS
  rendering against a Linux one and failing with a diff nobody can act on.
- File names are the PascalCase dot-separated subject (`Pricing.PlanTable`), the same shape as the test ids.
- Baselines are **committed**: versioned test inputs, not secrets and not build output.

## 3. Capture options — `LocatorScreenshotOptions`

`Locator.ScreenshotAsync(new LocatorScreenshotOptions { ... })` returns `byte[]` (PNG by default); `Path` also
writes the file and creates its folder. It waits for the element to be visible and stable, scrolls it into
view and clips to it, and the screenshotter waits for web fonts. It does **not** wait for the app's data, and
unlike the Node runner it takes **one** capture — there is no retry-until-two-captures-match. The page object
waits for the ready state first. Spellings as in `qa/dotnet/skills/evidence-capture/references/playwright.md` §1.1:

| Option | Use |
|---|---|
| `Animations = ScreenshotAnimations.Disabled` | Finite animations jump to their end, infinite ones reset |
| `Caret = ScreenshotCaret.Hide` | The text caret, a classic 1-px flake (already the default) |
| `Scale = ScreenshotScale.Css` | One image pixel per CSS pixel, whatever the device scale factor |
| `Mask = IEnumerable<ILocator>` | Paints each match with a solid box (`#FF00FF`; `MaskColor` [1.35]) in actual and baseline alike, so the region can never differ |
| `Style = "<css>"` [1.41] | CSS applied only during the capture; pierces shadow DOM and iframes. There is no `StylePath` in .NET |
| `OmitBackground = true` | A transparent background (not for JPEG) |
| `Type = ScreenshotType.Png` | The default. WebP [1.62] works, but a PNG baseline is what a reviewer opens in a PR diff, and what `AddScreenDiff` shows |

- `LocatorScreenshotOptions` has no `FullPage` or `Clip`; those are `PageScreenshotOptions`. Prefer an
  element: a full-page baseline changes with every unrelated edit and needs masks everywhere.
- Viewport, time zone and reduced motion are context settings: the test class amends `base.ContextOptions()`
  (§5). The clock is frozen with `Page.Clock.SetFixedTimeAsync(...)` in the class's `[SetUp]`, before the page
  object navigates (`ui-test-author/playwright/references/emulation-and-mobile-web.md` §4, §6).

## 4. The helper — `Support/VisualCheck.cs`

One helper captures, compares, keeps and attaches. The test builds it in its own `[SetUp]` with `BaseTest`'s
evidence paths, calls `CompareAsync`, and asserts on the result.

```csharp
using Allure.Net.Commons;
using Codeuctivity.ImageSharpCompare;
using Microsoft.Playwright;
using NUnit.Framework;
using SixLabors.ImageSharp;

namespace Example.UiTests.Support;

public sealed class VisualCheck(string browserName, string actualPath, string diffPath)
{
    public const double AllowedDifferentPixelsPercent = 0.05;
    private const int PixelColorShiftTolerance = 12;
    private const string HideLiveWidgets = "[data-testid='Chat.Launcher'] { visibility: hidden !important; }";
    private static readonly bool UpdateBaselines = Environment.GetEnvironmentVariable("UPDATE_BASELINES") == "1";

    private readonly string _baselineDirectory = Path.Combine(ProjectPaths.Root, "Baselines", $"{OperatingSystemName()}-{browserName}");

    public async Task<VisualDiff> CompareAsync(ILocator target, IEnumerable<ILocator> masked, string subject)
    {
        await target.ScreenshotAsync(new()
        {
            Path = actualPath,
            Animations = ScreenshotAnimations.Disabled,
            Caret = ScreenshotCaret.Hide,
            Scale = ScreenshotScale.Css,
            Mask = masked,
            Style = HideLiveWidgets,
        });
        var baseline = Path.Combine(_baselineDirectory, $"{subject}.png");
        if (UpdateBaselines)
        {
            Directory.CreateDirectory(_baselineDirectory);
            File.Copy(actualPath, baseline, overwrite: true);
        }
        if (!File.Exists(baseline))
        {
            throw new InvalidOperationException($"No baseline at {baseline}; this run's capture is {actualPath}. Baselines are written only in the pinned image (playwright-snapshots.md §7)");
        }
        var diff = Measure(subject, baseline);
        if (diff.DifferentPixelsPercent <= AllowedDifferentPixelsPercent)
        {
            File.Delete(actualPath);
            return diff;
        }
        using var mask = ImageSharpCompare.CalcDiffMaskImage(actualPath, baseline, ResizeOption.Resize, PixelColorShiftTolerance);
        await mask.SaveAsPngAsync(diffPath);
        AllureApi.AddScreenDiff(baseline, actualPath, diffPath);
        TestContext.AddTestAttachment(actualPath, "actual");
        TestContext.AddTestAttachment(diffPath, "diff");
        return diff;
    }

    private VisualDiff Measure(string subject, string baseline) =>
        ImageSharpCompare.ImagesHaveEqualSize(actualPath, baseline)
            ? new VisualDiff(subject, true, ImageSharpCompare.CalcDiff(actualPath, baseline, ResizeOption.DontResize, PixelColorShiftTolerance).PixelErrorPercentage)
            : new VisualDiff(subject, false, 100);

    private static string OperatingSystemName() =>
        OperatingSystem.IsLinux() ? "linux" : OperatingSystem.IsMacOS() ? "macos" : "windows";
}

public sealed record VisualDiff(string Subject, bool SameSize, double DifferentPixelsPercent);
```

- **Kept files** sit beside `BaseTest`'s failure evidence: the test passes `Artifact(EvidenceName(), "actual.png")`
  and `Artifact(EvidenceName(), "diff.png")` — `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{actual,diff}.png`,
  the folder the CI references upload on failure. On a match the capture is deleted, so a green run keeps
  nothing.
- **The diff image** is ImageSharpCompare's mask: black where the images agree, the per-channel difference
  where they do not. A size mismatch grows both images to the larger size first (`ResizeOption.Resize`), so
  the diff still shows where the box changed.
- **Allure** gets one `application/vnd.allure.image.diff` attachment from `AllureApi.AddScreenDiff(expectedPngPath,
  actualPngPath, diffPngPath)` — expected first, checked against the Allure.NUnit 2.15.0 source
  (`AllureApi.cs`; its doc comments swap "actual" and "expected", the parameter names and the JSON it writes
  do not). It is attached **before** the test's assertion fails, so the report carries it. The TRX and the
  IDE get the actual and diff files through `TestContext.AddTestAttachment`.
- **No baseline is a failure, never a silent pass.** The capture is kept so a reviewer can see what the
  missing baseline would be.
- **`UPDATE_BASELINES=1`** writes every capture as its baseline before comparing, so the run passes and the
  new PNGs show in `git diff`. It is set only by §7's command — never in CI (`qa/cicd/ci-conventions`).
- The comparer's API is synchronous (file I/O and pixel loops); only the screenshot and the PNG write are
  awaited. The `if`s live in the helper; the test stays a straight line.

## 5. The page object and the test

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class PricingPage
{
    private readonly IPage _page;

    public PricingPage(IPage page)
    {
        _page = page;
        PlanTable = page.GetByTestId("Pricing.PlanTable").Describe("Plan table");
        PromoBadge = PlanTable.GetByTestId("Pricing.PromoBadge").Describe("Promo badge");
        PromoPrice = PlanTable.GetByTestId("Pricing.PromoPrice").Describe("Promo price");
        RotatingContent = [PromoBadge];
    }

    public ILocator PlanTable { get; }

    public ILocator PromoBadge { get; }

    public ILocator PromoPrice { get; }

    public IReadOnlyList<ILocator> RotatingContent { get; }

    public async Task OpenAsync()
    {
        await _page.GotoAsync("/pricing");
        await PlanTable.WaitForAsync();
    }
}
```

`OpenAsync()` returns once the plan table is visible; the app renders it only after the plans arrive (its
skeleton has its own test id). `RotatingContent` names what changes daily, so the page object — not the test
— owns which regions are masked. `GotoAsync("/pricing")` resolves against the `BaseURL` that `BaseTest` reads
from `BASE_URL`; nothing here hard-codes a host.

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[Category("visual")]
public class PricingVisualTests : BaseTest
{
    private PricingPage _pricingPage = null!;
    private VisualCheck _visual = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.ViewportSize = new() { Width = 1280, Height = 720 };
        options.TimezoneId = "UTC";
        options.ReducedMotion = ReducedMotion.Reduce;
        return options;
    }

    [SetUp]
    public async Task PrepareVisualCheck()
    {
        await Page.Clock.SetFixedTimeAsync(new DateTime(2026, 10, 10, 9, 0, 0, DateTimeKind.Utc));
        _pricingPage = new PricingPage(Page);
        _visual = new VisualCheck(BrowserName, Artifact(EvidenceName(), "actual.png"), Artifact(EvidenceName(), "diff.png"));
    }

    [Test]
    public async Task Should_MatchApprovedPlanTable_When_PlansLoad()
    {
        await _pricingPage.OpenAsync();

        var diff = await _visual.CompareAsync(_pricingPage.PlanTable, _pricingPage.RotatingContent, "Pricing.PlanTable");

        Assert.That(diff.DifferentPixelsPercent, Is.LessThanOrEqualTo(VisualCheck.AllowedDifferentPixelsPercent), $"{diff}; expected, actual and diff are attached");
    }
}
```

- `ContextOptions()` amends `base.ContextOptions()`, which already carries `BaseURL`, the video folder,
  `Locale = "en-US"` and `ColorScheme = Light`. Returning `new()` would drop them and fail `BaseTest`'s
  teardown. A signed-in page adds `options.StorageStatePath = AuthSetup.UserState` here
  (`ui-test-author/playwright/references/lifecycle.md` §4, §7).
- The class's `[SetUp]` runs after `BaseTest.StartTracing`, so the page exists; the clock is frozen before
  the page object navigates, so the app's first `Date.now()` already reads the fixed instant.
- `Artifact(...)` and `EvidenceName()` are `BaseTest`'s protected helpers (plan D42); they name the files
  exactly as the failure evidence is named.
- One logical assertion: the difference is within the allowance. The message is the `VisualDiff` record
  (subject, same size, percentage), and the three images are already in Allure.
- One comparison per test, so `<Class>.<Test>` identifies the images. `[Category("visual")]` keeps the class
  out of the PR gate.

## 6. Tolerance — the comparer's knobs

| Knob | Meaning | Here |
|---|---|---|
| `pixelColorShiftTolerance` (the last parameter of `CalcDiff` / `CalcDiffMaskImage`) | A pixel counts as different only when \|ΔR\| + \|ΔG\| + \|ΔB\| exceeds it (0–765) | `12` |
| `ICompareResult.PixelErrorPercentage` | The share of differing pixels, 0–100 | gated at `0.05` |
| `ICompareResult.PixelErrorCount` / `MeanError` / `AbsoluteError` | The count, and the mean and summed colour error | for messages |
| `ResizeOption.DontResize` / `Resize` | Throw `ImageSharpCompareException("Size of images differ.")` on a size mismatch, or grow both images first | `DontResize` for the measure, `Resize` for the diff image |
| A mask image (`CalcDiff(actual, expected, maskPath, …)`) | A third PNG whose pixels state the tolerated difference per pixel | not used — `Mask` at capture time follows the element |

- **Gate on `PixelErrorPercentage`**, after checking the sizes: a size mismatch is reported as 100 % and
  `SameSize = false`, never as an exception from inside the comparer.
- Keep the allowance tight (≤ 0.1 %). Mask the noisy region instead of loosening the whole image.
- Prefer `Mask` over a mask image: a locator mask follows the element wherever the layout puts it; a mask
  image is a set of coordinates that breaks on the next layout change.
- A size mismatch means the element's box changed — a real layout change, or a viewport the class forgot to
  fix in `ContextOptions()`.

## 7. Generating and updating baselines — only in the pinned image

Rendering differs by OS, fonts, GPU and browser build, so a baseline is valid only where it was made. The
pinned image (`mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`) carries the .NET 10 SDK and the 1.63
browsers, so the container builds and runs the project itself:

```bash
docker run --rm --platform linux/amd64 --ipc=host \
  -v "$PWD":/work -w /work \
  -e BASE_URL -e E2E_USER -e E2E_PASSWORD -e UPDATE_BASELINES=1 \
  mcr.microsoft.com/playwright/dotnet:v1.63.0-noble \
  dotnet test UiTests -c Release --filter TestCategory=visual
```

- `--platform linux/amd64` matches the CI runners; on an Apple-silicon Mac it emulates amd64 instead of
  pulling the arm64 image, whose rendering is not guaranteed to match.
- `--ipc=host` is Playwright's Docker recommendation for Chromium.
- The build inside the container records `ProjectDirectory` as `/work/UiTests`, which is the mounted
  repository — so the update lands in the working tree.
- `BASE_URL` must be reachable **from inside** the container: a deployed test environment, or
  `host.docker.internal` for an app on the developer's machine. `E2E_USER` / `E2E_PASSWORD` are needed
  whenever `AuthSetup.cs` is in the project — the root-namespace `[SetUpFixture]` signs in before any fixture
  under `Example.UiTests` runs.
- The container restores into its own NuGet cache on every run; mount one
  (`-v "$HOME/.nuget/packages":/root/.nuget/packages`) to skip the download. It runs as root, so on a Linux
  host the new PNGs and `bin/`/`obj/` come out root-owned — `chown` them, and delete `UiTests/bin` and
  `UiTests/obj` before the next host build.
- Then review every changed PNG in `git diff` and commit them in the PR that changed the UI.
- Drop `UPDATE_BASELINES=1` and the same command **verifies** in the image — the way to reproduce a nightly
  failure locally.

## 8. The nightly visual job

The job runs §7's command without `UPDATE_BASELINES`. It is a `docker run` step on the runner, not a
container job, so the credential fetch stays on the runner, where the cloud CLI is (plan D60):

```yaml
  visual:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v6
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: Fetch test credentials from Key Vault
        run: |
          echo "BASE_URL=$(az keyvault secret show --vault-name kv-qa --name base-url --query value -o tsv)" >> "$GITHUB_ENV"
          echo "E2E_USER=$(az keyvault secret show --vault-name kv-qa --name e2e-user --query value -o tsv)" >> "$GITHUB_ENV"
          PASSWORD=$(az keyvault secret show --vault-name kv-qa --name e2e-password --query value -o tsv)
          echo "::add-mask::$PASSWORD"
          echo "E2E_PASSWORD=$PASSWORD" >> "$GITHUB_ENV"
      - name: Visual tests in the pinned image
        run: |
          docker run --rm --ipc=host -v "$PWD":/work -w /work \
            -e BASE_URL -e E2E_USER -e E2E_PASSWORD \
            mcr.microsoft.com/playwright/dotnet:v1.63.0-noble \
            dotnet test UiTests -c Release --filter TestCategory=visual
      - name: Upload visual evidence
        uses: actions/upload-artifact@v5
        if: failure()
        with:
          name: playwright-artifacts-visual
          path: UiTests/bin/Release/net10.0/playwright-artifacts
          retention-days: 14
      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-visual
          path: UiTests/bin/Release/net10.0/allure-results
          retention-days: 30
```

- **GitHub Actions** — as above; the job sits in the workflow `qa-dotnet:ci-pipelines` gates to the schedule.
  A `container:` job would run `azure/login` inside the image, which has no Azure CLI.
- **Azure Pipelines** — the same `docker run` in a `script` step on the Microsoft-hosted `ubuntu-latest` agent,
  after the `AzureCLI@2` fetch; a secret variable reaches the step only through its `env:` mapping
  (`E2E_PASSWORD: $(E2E_PASSWORD)`).
- **GitLab CI** — `image: mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` with `rules: - if:
  $CI_PIPELINE_SOURCE == "schedule"`; the `script` is the `dotnet test` line. The image has no cloud CLI, so
  `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come from masked, protected CI/CD variables.
- **The PR gate excludes the category**: its filter carries `&TestCategory!=visual` beside
  `TestCategory!=Flaky` (`qa/cicd/dotnet/skills/ci-pipelines`).

## 9. A generated PDF is not a visual target

`Page.PdfAsync()` embeds a creation date and a document ID, so its bytes never equal a baseline, and a byte
comparison is no visual check. Assert the document's text with a PDF library in the suite that owns the
document, or screenshot the HTML the PDF is printed from — with this reference's helper.

## Anti-patterns

- **A screenshot assertion on `Expect(Page)` or `Expect(locator)`, an options class for one, or a
  delete-and-rerun baseline workflow.** None exists in Microsoft.Playwright. *Fix:* §4.
- **A baseline made on a dev box or a CI runner without the image.** *Fix:* §7, nowhere else.
- **A missing baseline that silently becomes the new baseline.** Every run then passes. *Fix:* fail on a
  missing baseline; write baselines only with `UPDATE_BASELINES=1` in the image.
- **Baselines read relative to `bin/`.** An update never reaches the repo. *Fix:* `ProjectPaths.Root` and the
  `ProjectDirectory` metadata (§1).
- **`Task.Delay` or `WaitForTimeoutAsync` before the capture.** *Fix:* the page object's ready signal, the
  frozen clock, masks.
- **A full-page capture of a data-heavy page.** *Fix:* the element, with its rotating regions masked.
- **Raising the allowance until it passes.** *Fix:* mask the noisy region; keep the tolerance tight.
- **A `ContextOptions()` override that returns `new()`, or a hard-coded `BaseURL`.** *Fix:* amend
  `base.ContextOptions()`; `BASE_URL` reaches it through `BaseTest`.
- **`Playwright.CreateAsync()` or a second browser in a visual class.** *Fix:* derive from `BaseTest`.
- **A `try`/`finally` or a re-attaching `[TearDown]` in the test class.** *Fix:* the helper attaches;
  `BaseTest` keeps the failure evidence.
- **A direct `SixLabors.ImageSharp` package reference.** *Fix:* reach it through the comparer (§1).
- **Visual tests in the PR gate.** *Fix:* `[Category("visual")]` and the nightly job.

## Rules

- .NET has no screenshot assertion: capture with `Locator.ScreenshotAsync`, compare with
  `Codeuctivity.ImageSharpCompare` 4.1.390, assert the percentage with NUnit and a message.
- Baselines live in `UiTests/Baselines/<os>-<browser>/`, are committed, and are written only in
  `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`, by a person, with `UPDATE_BASELINES=1`.
- Stabilize through the page object, the frozen clock, `ContextOptions()` and masks — never a sleep.
- Actual and diff images land in `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{actual,diff}.png` and
  are shown with `AllureApi.AddScreenDiff(expected, actual, diff)`.
- Visual classes carry `[Category("visual")]` and run nightly.

## Cross-references

- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest`, page objects, `Directory.Packages.props` and its
  Versions table.
- `qa/dotnet/skills/ui-test-author/playwright/references/emulation-and-mobile-web.md` — viewport, media
  features and `Page.Clock`.
- `qa/dotnet/skills/evidence-capture` — screenshot options in full, the failure evidence, `AddScreenDiff`.
- `references/percy.md`, `references/applitools.md` — the hosted siblings, which remove the pinned-image
  discipline.
- `qa/cicd/dotnet/skills/ci-pipelines` — the UI job, its artifact upload and the schedule gate.
- `qa/reporting/dotnet/skills/test-reports` — Allure.NUnit wiring.
- `qa-typescript:visual-regression` — the Node runner's `toHaveScreenshot`, which this lane cannot use;
  `qa-java:visual-regression` — the same lane with a Java comparator.
