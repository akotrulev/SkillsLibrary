# Accessibility Testing — Lighthouse (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

Lighthouse is Google's Chrome auditor. It scores a page per **category** — `accessibility`,
`best-practices`, `seo`, `performance` — from 0 to 1, and a gate fails when a score drops below its threshold.
It is the **broad-audit and trend** sibling of `references/axe-playwright.md`: axe asserts the exact failing
rules **inside** the functional run; Lighthouse runs a separate full-page pass and gives one number per
category. Its accessibility category runs axe-core underneath, so a perfect score is still the automated
floor, not proof.

> **Lighthouse is a Node tool.** There is no NuGet Lighthouse package. .NET runs it as a pipeline step
> (`lhci autorun`) or as a subprocess (`npx lighthouse`) from a test, and parses the JSON report.

## 1. Setup

Node 24 on the runner, plus the two CLIs as exact dev dependencies in the repository's `package.json`
(checked on npm on 2026-10-11; `lighthouse` 13.5.0 needs Node ≥ 22.19):

```bash
npm install --save-dev --save-exact @lhci/cli@0.15.1 lighthouse@13.5.0
```

`@lhci/cli` needs no key for the `temporary-public-storage` upload target. The only optional secret is an
LHCI-server token (`LHCI_TOKEN`) — from the secret store, never committed or logged. The PWA category was
removed in Lighthouse 12; never configure or assert it. The JSON parsing below uses `System.Text.Json` from the
BCL, so no package is added.

## 2. Two ways to run it

| Way | What it audits | Gate |
|---|---|---|
| `lhci autorun` with `lighthouserc.cjs` (§3) | A list of public URLs, each run three times, median kept | `lhci`'s assertions; a pipeline step |
| An NUnit fixture that launches its own Chromium and runs `npx lighthouse` against it (§4) | One page per test — signed in or public — reported in the TRX and Allure | NUnit on the parsed scores |

The first is the default for public pages: it needs no .NET at all. Use the second for a signed-in page, or
when the score belongs in the test report beside the suite's other results.

## 3. `lhci autorun` — the URL-list gate

```js
module.exports = {
  ci: {
    collect: {
      url: [`${process.env.BASE_URL}/`, `${process.env.BASE_URL}/pricing`],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.9 }],
        'categories:performance': ['warn', { minScore: 0.8 }],
        'color-contrast': ['error', { minScore: 1 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
```

```bash
npx lhci autorun --config=lighthouserc.cjs
```

- `'categories:<name>': [level, { minScore }]` — `error` fails the step, `warn` reports only. An audit id
  (`color-contrast`) can be asserted on its own.
- `numberOfRuns: 3` and the median fight Lighthouse's variance.
- `BASE_URL` is the deployed test environment the UI job already uses — never a hard-coded
  `http://localhost:5000`. `lhci` launches its own Chrome, found through `CHROME_PATH` when it is not on the
  default path.

## 4. A Lighthouse fixture with its own Chromium

Lighthouse attaches to a running Chromium through a **remote-debugging port** and audits in **its own tab, in
the browser's default context**. `BaseTest` cannot provide either:

- its browser is `BrowserTest`'s per-worker service, launched once from the runsettings `LaunchOptions` and
  shared by every fixture on that worker (plan D32) — one fixed port per worker at best, and parallel workers
  on one machine collide on it;
- its context is a new, isolated context per test, so a sign-in there is not what Lighthouse's tab sees.

So the Lighthouse fixture derives from **`PlaywrightTest`** — the base class that gives `Playwright` and
`BrowserName` and launches nothing — and launches a **persistent context** itself: a Chromium whose one
context *is* the default context, on a port chosen per test. `Playwright.CreateAsync()` never appears in it
(plan D61).

```csharp
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using Allure.Net.Commons;
using NUnit.Framework;

namespace Example.UiTests.Support;

public static class Lighthouse
{
    public static readonly IReadOnlyList<string> GatedCategories = ["accessibility", "best-practices", "seo"];
    private static readonly TimeSpan AuditTimeout = TimeSpan.FromMinutes(2);

    public static int FreePort()
    {
        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        return ((IPEndPoint)listener.LocalEndpoint).Port;
    }

    public static async Task<IReadOnlyDictionary<string, double>> AuditAsync(string url, int port, string reportPath)
    {
        var logPath = Path.ChangeExtension(reportPath, ".log");
        Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);
        var start = new ProcessStartInfo("npx")
        {
            ArgumentList =
            {
                "--no-install", "lighthouse", url,
                $"--port={port}",
                $"--only-categories={string.Join(',', GatedCategories)}",
                "--output=json", $"--output-path={reportPath}",
                "--quiet",
            },
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        using var lighthouse = Process.Start(start) ?? throw new InvalidOperationException("npx did not start; Node 24 must be on PATH");
        var output = lighthouse.StandardOutput.ReadToEndAsync();
        var errors = lighthouse.StandardError.ReadToEndAsync();
        using var deadline = new CancellationTokenSource(AuditTimeout);
        using (deadline.Token.Register(() => lighthouse.Kill(entireProcessTree: true)))
        {
            await lighthouse.WaitForExitAsync();
        }
        await File.WriteAllTextAsync(logPath, await output + await errors);
        Attach("lighthouse-log", "text/plain", logPath);
        if (lighthouse.ExitCode != 0)
        {
            throw new InvalidOperationException($"Lighthouse exited {lighthouse.ExitCode} (it is killed after {AuditTimeout}); log: {logPath}");
        }
        Attach("lighthouse-report", "application/json", reportPath);
        using var report = JsonDocument.Parse(await File.ReadAllTextAsync(reportPath));
        var categories = report.RootElement.GetProperty("categories");
        return GatedCategories.ToDictionary(category => category, category => categories.GetProperty(category).GetProperty("score").GetDouble());
    }

    private static void Attach(string name, string contentType, string path)
    {
        AllureApi.AddAttachment(name, contentType, path);
        TestContext.AddTestAttachment(path, name);
    }
}
```

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class AccountPage
{
    private readonly IPage _page;

    public AccountPage(IPage page)
    {
        _page = page;
        Header = page.GetByTestId("Account.Header").Describe("Account header");
    }

    public ILocator Header { get; }

    public string Url => _page.Url;

    public async Task OpenAsync()
    {
        await _page.GotoAsync("/account");
        await Header.WaitForAsync();
    }
}
```

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using Microsoft.Playwright.TestAdapter;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[Category("lighthouse")]
[Parallelizable(ParallelScope.Self)]
public class AccountLighthouseTests : PlaywrightTest
{
    private const double MinimumScore = 0.9;
    private int _debuggingPort;
    private IBrowserContext _chromium = null!;
    private AccountPage _accountPage = null!;

    [SetUp]
    public async Task LaunchAuditableChromium()
    {
        _debuggingPort = Lighthouse.FreePort();
        _chromium = await Playwright.Chromium.LaunchPersistentContextAsync(string.Empty, new()
        {
            BaseURL = BaseTest.RequiredEnv("BASE_URL"),
            Headless = PlaywrightSettingsProvider.LaunchOptions.Headless,
            Args = [$"--remote-debugging-port={_debuggingPort}"],
        });
        await _chromium.SetStorageStateAsync(AuthSetup.UserState);
        _accountPage = new AccountPage(_chromium.Pages[0]);
    }

    [TearDown]
    public async Task CloseChromium() => await _chromium.CloseAsync();

    [Test]
    public async Task Should_ScoreAtLeast90InEveryGatedCategory_When_AccountPageIsAudited()
    {
        await _accountPage.OpenAsync();

        var scores = await Lighthouse.AuditAsync(_accountPage.Url, _debuggingPort, ReportPath());

        Assert.That(scores.Where(score => score.Value < MinimumScore), Is.Empty, "Lighthouse categories under 0.9 on the signed-in account page");
    }

    private string ReportPath() =>
        Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-artifacts", $"{GetType().Name}.{TestContext.CurrentContext.Test.Name}.lighthouse.json");
}
```

- **`LaunchPersistentContextAsync(string.Empty, …)`** creates a temporary profile and returns its context,
  which already holds one page (`Pages[0]`). Chrome honours `--remote-debugging-port` only with a non-default
  profile, which the temporary one is. `Playwright.Chromium` is explicit: Lighthouse audits Chromium whatever
  the runsettings `BrowserName` says. `Headless` follows the runsettings and `HEADED=1` through
  `PlaywrightSettingsProvider` — the values `AuthSetup` uses.
- **The port is per test.** `FreePort()` asks the OS for a free loopback port; fixtures run in parallel on
  different ports. The OS can hand the port to another process between the check and the launch; the window
  is short, and a collision fails the launch loudly.
- **Signed in through the shared state.** `SetStorageStateAsync(AuthSetup.UserState)` [1.59] loads the cookies
  and local storage `AuthSetup` saved before any fixture under `Example.UiTests` ran. Lighthouse's tab opens in
  this same context, and Lighthouse 13.5.0 clears only file systems, the shader cache, service workers and
  cache storage before it audits (`clearStorageTypes` in `core/config/constants.js`) — cookies and local
  storage survive. A public page drops the `SetStorageStateAsync` line.
- **`OpenAsync()` first, then the audit.** The page object navigates and waits for the signed-in header, so a
  broken sign-in fails as a visible assertion instead of a good score for the login page. Its `Url` property
  is the absolute URL Lighthouse loads in its own tab.
- **Every gated category is one assertion.** The categories under 0.9 must be empty; the message names the
  page and NUnit prints each failing pair. Performance is not gated here (§5). Scores are **0–1** in the JSON
  report (the TS `playwright-lighthouse` thresholds are 0–100).
- **The subprocess has a deadline**, not a sleep: after `AuditTimeout` the registration kills the process
  tree, the exit code is non-zero, and the failure names the log. Both streams are read while the process
  runs, so a full pipe cannot block it. `npx --no-install` runs the pinned `lighthouse` from `node_modules` and
  never downloads another version. On Windows the executable is `npx.cmd`.
- **The evidence is the report.** This fixture is not `BaseTest`, so there is no trace, screenshot or video;
  the JSON report (with Lighthouse's own final screenshot) and the log go to
  `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.lighthouse.{json,log}` — the folder CI uploads on
  failure — and are attached to Allure and the TRX before the assertion.
- **`[Category("lighthouse")]`** keeps the class out of the PR gate; a scheduled job runs
  `--filter TestCategory=lighthouse`, like the `visual` category in `qa/dotnet/skills/visual-regression`.
- A second Lighthouse class moves the two hooks into a shared base on that second need, not before.

## 5. Performance variance

Performance scores are noisy — CPU contention, network jitter, cold caches — and parallel fixtures make them
noisier. Accessibility, best-practices and SEO are deterministic rule checks.

- `error` on the deterministic categories, `warn` on performance in `lhci`; the NUnit fixture does not audit
  performance at all.
- `numberOfRuns: 3` and the median in `lhci`; a single cold run is never a performance gate.
- Audit a page that is fully served — the page object's ready signal — never after a sleep.

## 6. Reporting

- **Allure and the TRX** — the fixture attaches the JSON report and the log before it asserts.
- **CI artifact** — `lhci autorun` writes `.lighthouseci/` (HTML, JSON, `manifest.json`); upload it from the
  step (`qa/cicd/dotnet/skills/ci-pipelines`). The fixture's report and log are already in
  `playwright-artifacts/`, which the UI job uploads on failure.
- **Status check** — the LHCI GitHub App posts one linking the report; with `temporary-public-storage` the
  report URL is in the job log.

## Anti-patterns

- **Looking for a NuGet Lighthouse SDK.** There is none. *Fix:* `lhci autorun`, or §4's subprocess.
- **`Playwright.CreateAsync()` in a test or `[SetUp]`.** A review blocker. *Fix:* derive from `PlaywrightTest`
  and use its `Playwright`.
- **`Browser.NewPageAsync()` for a signed-in audit.** It opens a new, isolated context; Lighthouse audits the
  default one, signed out. *Fix:* a persistent context.
- **A fixed `--remote-debugging-port=9222`.** Parallel fixtures collide. *Fix:* `FreePort()` per test.
- **The debugging port in `ui.runsettings` for `BaseTest`'s browser.** One port per worker, and still the
  wrong context. *Fix:* §4.
- **A hard-coded `http://localhost:5000`.** *Fix:* `BASE_URL`.
- **Hard-gating performance.** *Fix:* `warn` and trend it.
- **The `pwa` category.** Removed in Lighthouse 12.
- **`Task.Delay` before the audit, or a wait with no deadline.** *Fix:* a fully served page; the deadline.
- **`.Result`, `.Wait()` or `.GetAwaiter().GetResult()` on the process or the file reads.** *Fix:* await them.
- **Committing `LHCI_TOKEN`.**

## Rules

- `@lhci/cli@0.15.1` and `lighthouse@13.5.0`, exact dev dependencies; Node 24.
- The public URL-list gate is `lhci autorun`. An NUnit audit derives from `PlaywrightTest`, launches a
  persistent Chromium context on a free port, loads `AuthSetup`'s state for a signed-in page, and bounds the
  subprocess.
- Gate accessibility, best-practices and SEO (`≥ 0.9`); warn on performance; no PWA.
- Scores are 0–1; one assertion per audited page — the categories under the minimum are empty.
- Reports and logs land in `<WorkDirectory>/playwright-artifacts/` and are attached before the assertion.

## Cross-references

- `references/axe-playwright.md` — the per-component gate inside the UI run.
- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest`, `AuthSetup`, page objects, `references/lifecycle.md`
  §1 (the base classes) and §4 (why launch options are per worker).
- `qa/cicd/dotnet/skills/ci-pipelines` — the `lhci autorun` step and artifact upload.
- `qa-accessibility-testing-typescript` — `playAudit` on a persistent context, the same idea in TS.
- `qa-accessibility-testing-java` — the Java sibling, which audits public pages only.
- `qa-exploratory-charter-writer` — the manual and assistive-technology testing no score covers.
