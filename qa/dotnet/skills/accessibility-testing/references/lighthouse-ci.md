# Accessibility Testing — Lighthouse CI (.NET / NUnit)

The .NET port of the canonical `qa-accessibility-testing-typescript`. Same Lighthouse
auditing model, same score-threshold gate, same perf-variance discipline — but re-expressed for a .NET
shop, which forces the honest shape of this node.

Lighthouse is Google's headless-Chrome auditing tool; **Lighthouse CI** runs it as a gated step that
produces a **category score** (0–1) for `performance`, `accessibility`, `best-practices`, `seo`, and
`pwa`, and **fails the build when a score drops below a threshold**. This is the **broad-audit +
score-trend** sibling of `references/axe-playwright.md`: where axe gives you
per-component `Violations` to assert empty **inside** your functional E2E run, Lighthouse runs a
**separate full-page pass** and gives you one number per category to gate and trend. Run both.

> **Lighthouse a11y is axe-powered — but reported as a *score*, not as `Violations`.** Under the hood
> Lighthouse's accessibility category runs axe-core, yet it surfaces the result as
> `categories.accessibility.score` (a 0–1 number derived from weighted audit pass/fail), **not** as an
> assertable list of failing nodes. That is exactly why you run both: axe-playwright gives you the
> per-element rule id + selector to *fix*; Lighthouse CI gives you the whole-page *trend* and the
> perf/SEO/PWA context axe doesn't cover. A Lighthouse a11y score is still the automated **floor**
> (~30–40% of WCAG) — pair with manual + assistive-tech testing (`qa-exploratory-charter-writer`).

> **⚠️ Node-only tool — the defining nuance of this node.** Lighthouse is a **Node** tool. **There is no
> native .NET Lighthouse SDK and no NuGet binding.** So unlike axe-playwright, where
> `Deque.AxeCore.Playwright` was a first-class .NET package, here .NET is a **thinner, CLI-driven** stack:
> you **invoke the Lighthouse/lhci CLI as a subprocess** (`npx lhci autorun` / `npx lighthouse <url>
> --output=json`) and **parse the JSON report** (`categories.*.score`) to gate the pipeline. The
> structure (collect → assert on score → report) ports from the TS canonical; the *invocation* is a
> `Process`, not an SDK call. Say this plainly to anyone reaching for a NuGet — there isn't one.

## Setup

There is no NuGet package — Lighthouse runs via Node. Your CI image needs Node + Chrome; install the CLI
once per job:

```bash
npm install --save-dev @lhci/cli      # the CI runner: collect → assert → upload (language-agnostic)
# stateful-page audits shell out to: npx lighthouse <url> --output=json
```

Your test project just needs Playwright + NUnit + a JSON parser (`System.Text.Json`, already in the BCL):

```xml
<!-- Tests.csproj -->
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.50.0" />
  <PackageReference Include="NUnit" Version="4.*" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.*" />
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
</ItemGroup>
```

`@lhci/cli` needs no API key for the default `temporary-public-storage` upload target. The only optional
secret is an **LHCI-server token** (`LHCI_TOKEN`) — read it lazily from the environment, never commit it.

## The Lighthouse model — category scores, not a violations list

A Lighthouse run loads a URL in headless Chrome and produces five **category scores** in `[0, 1]`:
`categories.performance.score`, `categories.accessibility.score`, `categories.best-practices.score`,
`categories.seo.score`, `categories.pwa.score`. Each is a **weighted aggregate of individual `audits`**
(e.g. `color-contrast`, `image-alt`, `first-contentful-paint`). The **gate is a threshold per category**
(`minScore`) — **not** a pass/fail list of DOM violations (that's `axe-playwright`'s axe).

Two ways to run it from a .NET pipeline — cover both:

1. **`lhci autorun` + `lighthouserc`** — a **language-agnostic** CI step that audits a list of URLs and
   gates on score. The same `lighthouserc` as the TS canonical; .NET doesn't change it.
2. **Shell out to `npx lighthouse` from a test** — drive a **stateful page** with Playwright .NET, then
   run Lighthouse against the page's debugging port, parse the JSON, and assert the score in NUnit.

## `lhci autorun` + `lighthouserc` — the URL-list CI gate (language-agnostic)

`lhci autorun` does **collect** (run Lighthouse N times per URL, keep the median), **assert** (apply your
score thresholds — the build-fail mechanism), and **upload** (store the report), all from one CLI command
your .NET pipeline calls. The config is identical to the TS canonical — .NET doesn't own it, the CLI does:

```js
// lighthouserc.cjs
module.exports = {
  ci: {
    collect: {
      startServerCommand: 'dotnet run --project src/Web',   // boot YOUR app (any stack)
      url: ['http://localhost:5000/', 'http://localhost:5000/checkout'],
      numberOfRuns: 3,                 // ≥3 and take the median — fights Lighthouse perf variance
    },
    assert: {
      assertions: {
        'categories:accessibility':   ['error', { minScore: 0.9 }],   // deterministic → fail build
        'categories:seo':             ['error', { minScore: 0.9 }],
        'categories:best-practices':  ['error', { minScore: 0.9 }],
        'categories:performance':     ['warn',  { minScore: 0.8 }],    // noisy → report only
        'color-contrast':             ['error', { minScore: 1 }],      // per-audit assertion
      },
    },
    upload: {
      target: 'temporary-public-storage',   // free, no API key — public link, kept a few days
      // target: 'lhci', serverBaseUrl: process.env.LHCI_SERVER_URL, token: process.env.LHCI_TOKEN,
    },
  },
};
```

```bash
npx lhci autorun --config=lighthouserc.cjs
```

`'categories:<name>': [level, { minScore }]` where `level` is `'error'` (fail build) or `'warn'` (report
only). This is the same gate as the TS canonical — reach for it whenever you're auditing public URLs.

## Shelling out to `npx lighthouse` — auditing a stateful page driven by Playwright .NET

For authenticated/stateful pages, drive the app with the page objects the
`qa-ui-test-writer-playwright-dotnet` skill already authored, then run Lighthouse against the page's
**remote-debugging port** and assert the parsed score. Launch Chromium with the port, drive to state,
then shell out — **async all the way down** (no `.Result`/`.Wait()`):

```csharp
// Support/Lighthouse.cs — the CLI-port helper: subprocess + JSON parse (no SDK exists)
using System.Diagnostics;
using System.Text.Json;

public sealed record LighthouseReport(JsonElement Root)
{
    /// <summary>The 0–1 score for a category, e.g. "accessibility", "performance", "seo".</summary>
    public double CategoryScore(string category) =>
        Root.GetProperty("categories").GetProperty(category).GetProperty("score").GetDouble();
}

public static class Lighthouse
{
    /// <summary>Runs `npx lighthouse` against an already-open Chrome on <paramref name="port"/>, parses the JSON.</summary>
    public static async Task<LighthouseReport> AuditAsync(string url, int port)
    {
        var outPath = Path.Combine(Path.GetTempPath(), $"lh-{Guid.NewGuid():N}.json");
        var psi = new ProcessStartInfo
        {
            FileName = "npx",
            ArgumentList = { "lighthouse", url, "--output=json", $"--output-path={outPath}",
                             $"--port={port}", "--quiet", "--only-categories=accessibility,seo,best-practices,performance" },
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Could not start `npx lighthouse` — is Node on PATH?");
        var stderr = await proc.StandardError.ReadToEndAsync();
        await proc.WaitForExitAsync();
        if (proc.ExitCode != 0)
            throw new InvalidOperationException($"lighthouse exited {proc.ExitCode}: {stderr}");

        await using var stream = File.OpenRead(outPath);
        using var doc = await JsonDocument.ParseAsync(stream);
        return new LighthouseReport(doc.RootElement.Clone());
    }
}
```

```csharp
// Tests/DashboardLighthouseTests.cs
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
public class DashboardLighthouseTests
{
    private const int Port = 9222;

    [Test]
    public async Task Should_meet_a11y_score_When_dashboard_loaded_for_signed_in_user()
    {
        using var pw = await Playwright.CreateAsync();
        // The debugging port Lighthouse attaches to.
        await using var browser = await pw.Chromium.LaunchAsync(
            new() { Args = new[] { $"--remote-debugging-port={Port}" } });
        var page = await browser.NewPageAsync();

        var dashboard = new DashboardPage(page);
        await dashboard.GotoAsSignedInUserAsync();        // page-object intent reused from `axe-playwright`'s skill
        await dashboard.WaitUntilReadyAsync();            // stabilize on a CONDITION, never Task.Delay/Thread.Sleep

        var report = await Lighthouse.AuditAsync("http://localhost:5000/dashboard", Port);

        Assert.That(report.CategoryScore("accessibility"), Is.GreaterThanOrEqualTo(0.9));  // the gate
    }
}
```

> **Scale note:** Lighthouse JSON `categories.*.score` is **0–1** (assert `>= 0.9`). The TS
> `playwright-lighthouse` `thresholds` are 0–100; you're parsing raw Lighthouse JSON here, so it's 0–1.

## Perf variance discipline — median the noise, gate the deterministic categories

Lighthouse **performance** scores are **noisy** (CPU contention, network jitter, cold caches). The a11y,
SEO, and best-practices categories are **deterministic** (a11y is axe-powered rule checks). So:

- **`numberOfRuns: 3`+ and median** in `lighthouserc`; for the shell-out path, audit a stable page and
  don't hard-gate a single cold run's perf number — assert perf with a margin or trend it instead.
- **`'error'` on a11y / SEO / best-practices** (deterministic — a regression is real); **`'warn'` on
  performance** (noisy — a hard-fail on a flaky number trains the team to ignore the gate).
- Stabilize the page on a **condition** before auditing (`Locator.WaitForAsync`, spinner hidden), never a
  fixed `Task.Delay` / `Thread.Sleep` — a half-loaded page tanks the score for the wrong reason.

## Reporting the gate — Lighthouse report into Allure + CI artifact

`lhci autorun` writes reports under `.lighthouseci/` (HTML + JSON + `manifest.json` naming the median
run) and prints a public report URL with `temporary-public-storage`. The shell-out path writes the JSON
you parsed. Attach it to Allure so a failing gate names the dropped category without re-running
(cross-link `qa-test-reports-dotnet`):

```csharp
// Support/LighthouseReportAttachment.cs
using Allure.Net.Commons;

public static class LighthouseReportAttachment
{
    public static void Attach(string jsonPath, string? htmlPath = null)
    {
        AllureApi.AddAttachment("lighthouse-report.json", "application/json", File.ReadAllBytes(jsonPath));
        if (htmlPath is not null)
            AllureApi.AddAttachment("lighthouse-report.html", "text/html", File.ReadAllBytes(htmlPath));
    }
}
```

- **Allure** — attach the HTML + JSON report so a failing gate names the dropped category and failing
  audits without anyone re-running locally.
- **CI artifact** — upload `.lighthouseci/` as a build artifact (cross-link
  `qa-ci-pipelines-dotnet`); the .NET pipeline calls the same Node CLI.
- **Status check** — the LHCI GitHub App posts a status check linking the report; with
  `temporary-public-storage` the report URL is in the job log.

**No API key required** for `temporary-public-storage` — same "no secret" theme as `axe-playwright` (axe). The only
secret is an optional `LHCI_TOKEN` for a private LHCI server, read lazily from the environment, never
logged or committed.

## Anti-patterns

- **Looking for a NuGet Lighthouse SDK.** There isn't one — Lighthouse is Node-only. *Fix:* shell out to
  `npx lighthouse` / `npx lhci autorun` and parse the JSON.
- **Hard-`error` gating the performance score.** Perf is noisy. *Fix:* `'warn'` on performance, `'error'`
  on the deterministic categories; trend perf.
- **`numberOfRuns: 1`.** A single run rides the variance. *Fix:* `numberOfRuns: 3`+ and median.
- **Blocking on the subprocess with `.Result` / `.Wait()` / `Thread.Sleep` before the audit.** Violates
  async-all-the-way and races the DOM. *Fix:* `await proc.WaitForExitAsync()`; stabilize on a condition
  (`Locator.WaitForAsync`) first.
- **Running multiple audits concurrently on one debugging port.** They collide. *Fix:* serialize the
  Lighthouse fixture (no `[Parallelizable]` on those tests) or use distinct ports.
- **Treating a 1.0 a11y score as "accessible."** Lighthouse a11y is axe-powered → ~30–40% automated
  floor. *Fix:* pair with manual + assistive-tech testing; run axe-playwright for assertable
  per-node fixes.
- **Committing an `LHCI_TOKEN`.** *Fix:* env var, read lazily; `temporary-public-storage` needs no key.

## Examples

**End-to-end: `lhci autorun` gating public pages, plus a Playwright .NET shell-out for an authenticated
page.**

```js
// lighthouserc.cjs — the public-pages CI gate (language-agnostic; the .NET pipeline calls the CLI)
module.exports = {
  ci: {
    collect: { startServerCommand: 'dotnet run --project src/Web', url: ['http://localhost:5000/', 'http://localhost:5000/pricing'], numberOfRuns: 3 },
    assert: { assertions: {
      'categories:accessibility':  ['error', { minScore: 0.9 }],
      'categories:seo':            ['error', { minScore: 0.9 }],
      'categories:best-practices': ['error', { minScore: 0.9 }],
      'categories:performance':    ['warn',  { minScore: 0.8 }],
    } },
    upload: { target: 'temporary-public-storage' },
  },
};
```

```csharp
// Tests/AccountLighthouseTests.cs — the authenticated-page gate (reuses `axe-playwright`'s page objects)
[TestFixture]
public class AccountLighthouseTests
{
    private const int Port = 9222;

    [Test]
    public async Task Should_meet_a11y_and_seo_scores_When_account_page_loaded()
    {
        using var pw = await Playwright.CreateAsync();
        await using var browser = await pw.Chromium.LaunchAsync(
            new() { Args = new[] { $"--remote-debugging-port={Port}" } });
        var page = await browser.NewPageAsync();

        var account = new AccountPage(page);
        await account.GotoAsSignedInUserAsync();          // intent, not selectors
        await account.WaitUntilReadyAsync();              // condition, not sleep

        var report = await Lighthouse.AuditAsync("http://localhost:5000/account", Port);

        Assert.Multiple(() =>                             // one logical gate: "scores meet thresholds"
        {
            Assert.That(report.CategoryScore("accessibility"), Is.GreaterThanOrEqualTo(0.9));
            Assert.That(report.CategoryScore("seo"),           Is.GreaterThanOrEqualTo(0.9));
        });
    }
}
```

Lifecycle for this gate:
1. A dev ships a redesign that drops color contrast on the pricing page and removes a `<main>` landmark.
2. CI runs `lhci autorun`; Lighthouse audits each URL 3× and medians the result.
3. `categories.accessibility.score` falls below `0.9` → the assertion fails → **the build fails**, with
   the dropped category and failing audits in the uploaded report (linked from the status check / job
   log, and attached to Allure).
4. The dev fixes contrast + the landmark; the score climbs back over the threshold; the gate goes green.
   Perf stays a `warn` and is trended rather than hard-failing the PR.

## Rules (hard constraints)

- **No native .NET SDK** — invoke the Lighthouse/lhci CLI as a subprocess and parse `categories.*.score`
  from the JSON. The gate is a **score threshold per category** (`minScore` / `Is.GreaterThanOrEqualTo`),
  one logical assertion per category under test. Test names `Should_X_When_Y`.
- Async all the way: `await proc.WaitForExitAsync()`, `await JsonDocument.ParseAsync(...)` — never
  `.Result`/`.Wait()`/`Thread.Sleep`.
- `'error'` (hard-fail) on the **deterministic** categories (accessibility / SEO / best-practices);
  `'warn'` on the **noisy** performance category — trend perf, don't hard-gate a flaky run.
- `numberOfRuns` ≥ 3 and take the **median**.
- Shell-out audits reuse existing page objects (intent, not selectors); stabilize on a **condition**
  before auditing, never `Task.Delay`/`Thread.Sleep`; serialize tests sharing a debugging port.
- Lighthouse JSON `categories.*.score` is **0–1** (assert `>= 0.9`).
- **No API key** for `temporary-public-storage` (contrast `percy` `PERCY_TOKEN` / `applitools` `APPLITOOLS_API_KEY`);
  an optional `LHCI_TOKEN` for a private server is the only secret — env, lazy, never logged.
- A Lighthouse a11y score is axe-powered = the automated **floor** (~30–40% of WCAG), not proof. Pair
  with manual + assistive-tech testing, and run axe-playwright for assertable per-node fixes.

## Cross-references

- `qa-accessibility-testing-typescript` — the **canonical** skill, TS (first-class
  `@lhci/cli` + `playwright-lighthouse`). This .NET sibling is the CLI-driven port of it.
- `qa-accessibility-testing-java` — same skill, Java / TestNG. Same CLI-port shape
  (`ProcessBuilder` + Jackson + AssertJ).
- `references/axe-playwright.md` — the **per-component assertion** sibling: gate
  on `Violations` empty **inside** the E2E run (`Deque.AxeCore.Playwright`, a real NuGet). Run both — axe
  to *fix* nodes, Lighthouse to *trend* whole-page scores + gate perf/SEO/PWA.
- `qa-ui-test-writer-playwright-dotnet` — the page objects the shell-out audit reuses to reach a stateful
  page. Author the flow there; add the audit here.
- `qa-ci-pipelines-dotnet` — the `lhci autorun` job (the .NET pipeline calls the Node CLI),
  artifact upload, and LHCI status check.
- `qa-test-reports-dotnet` — attach the Lighthouse HTML + JSON report to the run.
- `qa-exploratory-charter-writer` — the manual/assistive-tech testing that covers the ~60% no automated
  a11y score can.
