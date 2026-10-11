# Visual Regression — Percy (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

Percy (BrowserStack) **uploads a DOM snapshot** of the page and **renders and diffs it server-side**.
Baselines live in Percy's cloud, keyed by git branch, and a person approves changes in its review UI. The
build is gated on that review — a status check — not on anything the test asserts. The .NET binding is
`PercyIO.Playwright`; the agent that receives snapshots is the Node `@percy/cli`, wrapped around `dotnet test`
with `percy exec`.

This is an **assertion layer** on page objects that already exist. A Percy class derives from
`Example.UiTests.Support.BaseTest` (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`) and adds
one snapshot call to a flow the page objects drive.

## Why graduate from screenshot plus comparer to Percy

| | Screenshot plus comparer | **Percy** |
|---|---|---|
| What leaves the test | Nothing — a PNG is compared locally | A **DOM snapshot** is uploaded |
| Where rendering happens | The pinned image | **Percy's renderers**, the same for everyone |
| Where baselines live | `UiTests/Baselines/<os>-<browser>/` | **Percy cloud**, per branch |
| Baselines made in the pinned image | Mandatory | **Not needed** |
| Updating a baseline | `UPDATE_BASELINES=1` in the image, reviewed in the PR diff | **Approve in the review UI** |
| Tolerance | Comparer settings and masks | `percyCSS`, `scope`, regions — no pixel ratio |
| Gate | An NUnit assertion on the measured difference | **The Percy status check** |
| Cost | Free | Paid, per snapshot |

## 1. Setup

Pins checked on 2026-10-11 (NuGet, npm). `PercyIO.Playwright` 1.0.4 is already in the writer's
`Directory.Packages.props`, so the project only references it:

```xml
<ItemGroup>
  <PackageReference Include="PercyIO.Playwright" />
</ItemGroup>
```

```bash
npm install --save-dev --save-exact @percy/cli@1.32.11
```

`PercyIO.Playwright` 1.0.4 targets .NET Standard 2.0 and depends on `Microsoft.Playwright` ≥ 1.43, which the
writer's 1.63.0 satisfies. `PERCY_TOKEN` is the **only** secret — a per-project write token from the CI secret
store, never committed or logged. Locally: `export PERCY_TOKEN=<token>`.

## 2. Running the suite — `percy exec`

`percy exec` starts the local agent (it receives snapshots, discovers assets and uploads them), runs the
command, then finalizes the build:

```bash
npx percy exec -- dotnet test UiTests -c Release --filter TestCategory=visual
```

- **Without the agent, a snapshot is a no-op.** `Percy.Snapshot` calls the agent's `/percy/healthcheck`
  once; when that fails it logs "Percy is not running, disabling snapshots" and every later call returns
  `null` — the test passes. A developer without the token runs the functional suite untouched, and a CI job
  that forgets `percy exec` gets no visual coverage at all, so the visual job always runs under it.
- **A failed upload does not fail the test either.** The binding catches every error inside
  `Percy.Snapshot`, logs "Could not take DOM snapshot", and returns `null` (`Percy.cs`, v1.0.4). The status
  check is the only gate.
- `percy exec` exports `PERCY_BUILD_URL` (and `PERCY_BUILD_ID`) to the command it runs (`@percy/cli` 1.32.11,
  `cli-exec/src/exec.js`); §4's helper links it into Allure.
- The `visual` category is the same as the comparer lane's (`references/playwright-snapshots.md` §5, §8):
  visual tests run nightly, not in the PR gate.

## 3. `.percy.yml` — project-wide snapshot config

The agent's config, identical for every language binding:

```yaml
version: 2
snapshot:
  widths:
    - 375
    - 1280
  min-height: 1024
  percy-css: |
    [data-testid="Chat.Launcher"] { visibility: hidden !important; }
discovery:
  allowed-hostnames:
    - cdn.example.test
  network-idle-timeout: 250
```

`percy exec --config ./config/.percy.yml -- …` when it is not at the repository root. Per-snapshot options
merge over it; the binding sends them to the agent unchanged.

## 4. The core pattern

`Percy.Snapshot(IPage, …)` is a **static** method that takes the page, so a small helper holds the page —
the test never passes `Page` around — and adds the Percy build link to the test's Allure result:

```csharp
using Allure.Net.Commons;
using Microsoft.Playwright;
using PercyIO.Playwright;

namespace Example.UiTests.Support;

public sealed class PercySnapshots(IPage page)
{
    private static readonly string? BuildUrl = Environment.GetEnvironmentVariable("PERCY_BUILD_URL");

    public void Capture(string name, object options)
    {
        Percy.Snapshot(page, name, options);
        if (BuildUrl is not null)
        {
            AllureApi.AddLink("Percy build", BuildUrl);
        }
    }
}
```

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[Category("visual")]
public class PricingPercyTests : BaseTest
{
    private PricingPage _pricingPage = null!;
    private PercySnapshots _percy = null!;

    [SetUp]
    public async Task CreatePages()
    {
        await Page.Clock.SetFixedTimeAsync(new DateTime(2026, 10, 10, 9, 0, 0, DateTimeKind.Utc));
        _pricingPage = new PricingPage(Page);
        _percy = new PercySnapshots(Page);
    }

    [Test]
    [Description("No assertion: Percy renders and diffs this snapshot server-side; the build's Percy status check, approved in Percy's review UI, is the verdict.")]
    public async Task Should_UploadPlanTableSnapshot_When_PlansLoad()
    {
        await _pricingPage.OpenAsync();

        _percy.Capture("Pricing.PlanTable", new
        {
            widths = new[] { 375, 1280 },
            scope = "[data-testid='Pricing.PlanTable']",
            percyCSS = "[data-testid='Pricing.PromoBadge'] { visibility: hidden !important; }",
        });
    }
}
```

- `PricingPage` is the page object from `references/playwright-snapshots.md` §5; `OpenAsync()` returns once
  the plan table is visible. Percy captures the DOM **at call time**, so a half-loaded page uploads a
  half-loaded snapshot.
- **`Percy.Snapshot` is synchronous** and has no async overload: it evaluates the DOM serializer and reads the
  context's cookies by blocking on Playwright's async calls internally. That blocking lives in the vendor's
  binding; the test awaits every Playwright call of its own around it. Call it from a test or a page-object
  flow, never from a route handler or an event handler.
- `AllureApi.AddLink(name, url)` adds to the **running test** only; outside a test (a `[OneTimeTearDown]`) it
  does nothing, which is why the link is added here, during the test.
- One helper per test, built in the class's own `[SetUp]`, where the page `BaseTest` opened already exists.
  Nothing to close: there is no Percy session per test.
- **The test has no assertion, and says so** in `[Description("No assertion: …")]` — the NUnit form of the
  TS lane's `no-assertion` annotation (plan D50). The description reaches the TRX and the Allure result.

## 5. Snapshot options

`Percy.Snapshot(page, name, options)` takes the options as an anonymous object (its public properties
become the keys) or as a `Percy.Options` dictionary (`new Percy.Options { { "minHeight", 1280 } }`):

| Key | Meaning |
|---|---|
| `widths` | Viewport widths Percy renders at, server-side. Overrides `.percy.yml` |
| `minHeight` | Minimum render height (default 1024) |
| `enableJavaScript` | Run JS in Percy's renderer. Off by default: the captured DOM renders statically |
| `percyCSS` | CSS injected **only in Percy's renderer**, before the diff — the stabilization lever |
| `scope` | A CSS selector; only that subtree is snapshotted — the element snapshot. Build it from a test id |
| `regions` | Ignore / consider regions built with `Percy.CreateRegion(...)` — for a region a selector cannot isolate |

**Percy has no per-call pixel budget.** Hide the specific dynamic region with `percyCSS`
(`visibility: hidden`) and narrow the snapshot with `scope`; do not try to loosen the diff.

## 6. CI and the review gate

The nightly visual job runs `npx percy exec -- dotnet test UiTests -c Release --filter TestCategory=visual`
with `PERCY_TOKEN` from the secret store. Percy renders server-side, so this job does **not** need the pinned
image: the normal UI job's runner, its browser install and its credential fetch
(`qa/cicd/dotnet/skills/ci-pipelines`) are enough, plus Node for `@percy/cli`.

1. The run uploads snapshots; Percy diffs them against the base branch's approved baseline.
2. Percy posts a status check on the commit: **changes detected** (needs review) or **no changes**.
3. A reviewer approves or rejects in Percy's UI. Approving updates the branch baseline.
4. On merge, the approved snapshots become the base branch's baseline for the next PR.

There is no diff image to upload: the diff lives in Percy, linked from the status check, the `percy exec`
log and each test's Allure link. A functional failure in a Percy class still gets `BaseTest`'s trace,
screenshot and video.

## Anti-patterns

- **`Playwright.CreateAsync()`, a browser or a failure hook in a Percy class.** *Fix:* derive from `BaseTest`.
- **`Task.Delay` or `WaitForTimeoutAsync` before the snapshot.** *Fix:* the page object's ready signal.
- **Loosening the diff to stop a flake.** *Fix:* `percyCSS` on the specific region; `scope` to the element.
- **Running the visual category without `percy exec` and expecting coverage.** Every snapshot is a no-op.
- **A Percy test without the `[Description("No assertion: …")]`.** It reads as a forgotten assertion.
- **An Allure link added in `[OneTimeTearDown]`.** No test is running there, so nothing is recorded.
  *Fix:* add it while the test runs, as the helper does.
- **Committing baseline PNGs beside Percy.** *Fix:* Percy keeps the baselines; delete them.
- **Logging or committing `PERCY_TOKEN`.** It is a write credential.
- **A `Version=` on the `PackageReference`, a floating `1.*`, or an unpinned `@percy/cli`.** *Fix:* the exact
  versions in §1, the NuGet one in `Directory.Packages.props`.

## Rules

- Derive from `BaseTest`; build the helper in the class's `[SetUp]`; reach the state through page objects.
- Stabilize on the page object's condition and the frozen clock; never a sleep.
- Run under `percy exec`; `PERCY_TOKEN` comes from the secret store only.
- Hide dynamic regions with `percyCSS`, narrow with `scope`, built from test ids.
- The test has no assertion and states it in `[Description("No assertion: …")]`; the Percy status check is
  the gate.
- `PercyIO.Playwright` 1.0.4 (central package management) and `@percy/cli@1.32.11`, exact.

## Cross-references

- `references/playwright-snapshots.md` — the free sibling, and `PricingPage`.
- `references/applitools.md` — visual AI, match levels and a browser/device grid.
- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest` and page objects.
- `qa/cicd/dotnet/skills/ci-pipelines` — the schedule gate, the secret store, the UI job's runner setup.
- `qa/reporting/dotnet/skills/test-reports` — Allure.NUnit wiring.
- `qa-typescript:visual-regression` (`@percy/playwright`), `qa-java:visual-regression` (`percy-playwright-java`).
