# `BrowserHooks.cs` — `qa-dotnet:bdd-project-setup`

The per-scenario Playwright lifecycle and failure evidence for a Reqnroll web project. The contract it
implements is in `SKILL.md` § `Support/BrowserHooks.cs`; the evidence rules are
`qa/dotnet/skills/evidence-capture`'s ("Reqnroll scenarios"), the same ones `BaseTest` follows for NUnit
fixtures (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`).

`Support/BrowserHooks.cs`:

```csharp
using System.Text.RegularExpressions;
using Allure.Net.Commons;
using Example.UiTests.Support;
using Microsoft.Playwright;
using Microsoft.Playwright.TestAdapter;
using NUnit.Framework;
using Reqnroll;

namespace Example.BddTests.Support;

[Binding]
public sealed class BrowserHooks(ScenarioState state, FeatureContext feature, ScenarioContext scenario)
{
    private const int AfterEveryOtherHook = 20_000;

    private static string ArtifactsDirectory => Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-artifacts");

    private static string RawVideoDirectory => Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-videos");

    private IPlaywright _playwright = null!;
    private IBrowser _browser = null!;
    private IBrowserContext _context = null!;

    [BeforeScenario(Order = 0)]
    public async Task OpenBrowserAsync()
    {
        _playwright = await Playwright.CreateAsync();
        _browser = await _playwright[PlaywrightSettingsProvider.BrowserName].LaunchAsync(PlaywrightSettingsProvider.LaunchOptions);
        _context = await _browser.NewContextAsync(new()
        {
            BaseURL = BaseTest.RequiredEnv("BASE_URL"),
            RecordVideoDir = RawVideoDirectory,
            Locale = "en-US",
            ColorScheme = ColorScheme.Light,
        });
        await _context.Tracing.StartAsync(new()
        {
            Title = $"{feature.FeatureInfo.Title}: {scenario.ScenarioInfo.Title}",
            Screenshots = true,
            Snapshots = true,
            Sources = true,
        });
        state.Open(await _context.NewPageAsync());
    }

    [AfterScenario(Order = AfterEveryOtherHook)]
    public async Task KeepEvidenceAndCloseAsync()
    {
        using var playwright = _playwright;
        await using var browser = _browser;
        var failed = scenario.TestError is not null;
        var name = EvidenceName();
        var video = state.Page.Video ?? throw new InvalidOperationException("No video recorded: the scenario's context needs RecordVideoDir");
        if (failed)
        {
            await KeepTraceAsync(name);
            await KeepScreenshotAsync(name);
        }
        else
        {
            await _context.Tracing.StopAsync();
        }
        await _context.CloseAsync();
        if (failed)
        {
            await KeepVideoAsync(video, name);
        }
        await video.DeleteAsync();
    }

    private async Task KeepTraceAsync(string name)
    {
        var path = Artifact(name, "zip");
        await _context.Tracing.StopAsync(new() { Path = path });
        Attach("trace", "application/vnd.allure.playwright-trace", path);
    }

    private async Task KeepScreenshotAsync(string name)
    {
        var path = Artifact(name, "png");
        await state.Page.ScreenshotAsync(new() { Path = path, FullPage = true });
        Attach("screenshot", "image/png", path);
    }

    private static async Task KeepVideoAsync(IVideo video, string name)
    {
        var path = Artifact(name, "webm");
        await video.SaveAsAsync(path);
        Attach("video", "video/webm", path);
    }

    private string EvidenceName() =>
        Regex.Replace($"{feature.FeatureInfo.Title}.{scenario.ScenarioInfo.Title}", "[^A-Za-z0-9._-]", "_");

    private static string Artifact(string name, string extension) =>
        Path.Combine(ArtifactsDirectory, $"{name}.{extension}");

    private static void Attach(string name, string contentType, string path)
    {
        TestContext.AddTestAttachment(path, name);
        AllureApi.AddAttachment(name, contentType, path);
    }
}
```

## Why it is shaped this way

- **One scenario, one browser.** A Reqnroll binding cannot derive from `BaseTest`, and a browser kept between
  scenarios would need a static field (no static mutable state) or a container lifetime the hooks cannot see.
  Launching per scenario is the simplest correct baseline; the hook reads the **same runsettings** as the UI
  suite through `PlaywrightSettingsProvider` (`BrowserName`, `LaunchOptions` with `Headless`), as `AuthSetup`
  does, because the scaffold's csproj points `RunSettingsFilePath` at `../UiTests/ui.runsettings`.
- **The context matches `BaseTest`'s**: `BaseURL` from `BASE_URL` (`BaseTest.RequiredEnv` fails naming the
  variable), the raw-video folder, `Locale` en-US and `ColorScheme` Light — so a page object behaves the same
  under a scenario as under a fixture.
- **Failed is `ScenarioContext.TestError` set** — a failed assertion or a thrown step sets it.
- **The order is `BaseTest`'s** — stop the trace to a path (it needs the open context), the full-page
  screenshot (it needs the live page), close the context (the video is complete only then), `SaveAsAsync`, and
  always `DeleteAsync` the raw recording. A pass calls `StopAsync()` with no path, which discards the trace.
- **No catch** (plan D31's reasoning). A screenshot of a crashed page throws; the trace is already saved, only
  the video is lost. `using var playwright` and `await using var browser` close the driver and the browser on
  the way out whatever happened, without a `try`/`finally`.
- **It runs after every other `[AfterScenario]`.** Reqnroll runs hooks of one kind in ascending `Order`
  (default 10000), so the data cleanup hooks `gherkin-step-code` adds still have an open page when they run.
- **The evidence name** is `<Feature>.<Scenario>` — the `Feature:` and `Scenario:` titles — with every character
  outside `[A-Za-z0-9._-]` replaced by `_`: `Sign in.Wrong password` → `Sign_in.Wrong_password.{zip,png,webm}`.
  The hook writes its own sanitizer because `BaseTest`'s protected helpers are not reachable from a binding.
  Scenario Outline rows share one title, so two failing rows of one outline overwrite each other's files on
  disk; NUnit and Allure keep each row's result.
- **Each kept file is attached twice**, like `BaseTest`'s: `TestContext.AddTestAttachment` (the TRX and the IDE)
  and `AllureApi.AddAttachment(name, type, path)` (Allure, through the `Allure.Reqnroll` plugin), the trace as
  `application/vnd.allure.playwright-trace`.
- **Raw videos** go to `<WorkDirectory>/playwright-videos/`, which is scratch — never uploaded. CI uploads
  `Bdd.Tests/bin/<cfg>/net10.0/playwright-artifacts/` on failure, as it does for `UiTests`.
