---
name: qa-visual-regression-percy-dotnet
description: >-
  Hosted visual regression for Playwright UI tests in .NET / NUnit using Percy (by BrowserStack):
  the `PercyIO.Playwright` NuGet + `@percy/cli`, `Percy.Snapshot(page, name, options)` run under
  `percy exec -- dotnet test`. Use when visual baselines should live in Percy's cloud with a web
  review UI (approve/reject, auto-approve on the base branch, git-branch baseline tracking) and
  diffing happens server-side after a DOM-snapshot upload — so the dev-Mac-vs-Linux-CI rendering
  problem that dominates the built-in snapshots skill disappears. Covers `PERCY_TOKEN` (the only
  secret, env, read lazily), `.percy.yml` (widths/min-height/percy-css/enable-javascript/discovery),
  snapshot options (widths, minHeight, percyCSS, scope, enableJavaScript via anonymous object /
  Percy.Options), hiding dynamic regions via percyCSS, the GitHub/GitLab status-check review gate, and
  the free-vs-Percy-vs-Applitools decision.
  Do NOT use for: free in-repo baselines you diff yourself (see
  qa-visual-regression-playwright-snapshots-dotnet), visual-AI cross-browser diffing (see
  qa-visual-regression-applitools-dotnet), the page objects/specs `Percy.Snapshot` is called inside
  (see qa-ui-test-author-playwright-dotnet), TypeScript (see qa-visual-regression-percy-typescript),
  or Java (see qa-visual-regression-percy-java).
---

# Visual Regression — Percy (.NET / NUnit)

The .NET port of the canonical `qa-visual-regression-percy-typescript`. Same hosted model, same review
workflow, same `percy exec` agent — re-expressed in `PercyIO.Playwright` + `Microsoft.Playwright.NUnit`
idioms. Percy (by BrowserStack) **uploads a DOM snapshot** of the page and **renders + diffs it
server-side**; baselines live in Percy's cloud, keyed by git branch, and are reviewed/approved in a
web UI. The build is gated on that review, not on a local artifact.

This is an **assertion layer** on top of the page objects and specs
`qa-ui-test-author-playwright-dotnet` already authored. You do not write new page objects here — you
add a `Percy.Snapshot(page, name)` call and wrap `dotnet test` in `percy exec`.

## Why graduate from built-in snapshots to Percy

The biggest pain in the free `playwright-snapshots` skill (#17) is the **cross-platform rendering
problem**: a baseline rendered on a dev Mac (`...-darwin.png`) never matches Linux CI, so you must
generate baselines *inside the CI container* (and .NET can't even `--update-snapshots` — you
delete-and-rerun). Percy makes that problem **disappear** by rendering server-side:

| | Built-in snapshots (#17) | **Percy (this skill)** |
|---|---|---|
| What leaves the test | Nothing — a PNG is diffed locally | A **DOM snapshot** is uploaded |
| Where rendering happens | Your machine / CI container | **Percy's servers**, consistently |
| Where baselines live | Committed `*-snapshots/*.png` in your repo | **Percy cloud**, keyed by git branch |
| `-{platform}` baselines | Yes — the whole headache | **None** |
| Baseline-in-CI-container rule | Mandatory | **Not needed** |
| Updating a baseline | delete-and-rerun (no `--update-snapshots` in .NET) | **Approve in the review UI** |
| Diff budget | `MaxDiffPixelRatio` etc. per assertion | No per-call pixel knob — **`percyCSS` + region ignores** |
| Gate | Local pass/fail + `-diff.png` artifact | **Status check** linking the visual review |
| Cost | Free | Paid (per snapshot) |

State this contrast plainly: with Percy there are **no in-repo baselines, no `-{platform}` naming, no
in-CI-container baseline generation, and no delete-and-rerun** — baselines are managed in Percy and
auto-established from the **base branch**.

## Decision matrix — which visual-regression tool

| Need | Use | Why |
|------|-----|-----|
| Free, baselines in your repo, you own diffing + the CI-container discipline | built-in snapshots (#17) | No SaaS, no per-snapshot cost, full control |
| Hosted baselines + human review UI + server-side cross-browser render | **Percy (this skill)** | Kills the platform-rendering problem; team review workflow |
| Visual-AI diffing (ignore anti-aliasing) + a full cross-browser rendering grid | Applitools (#19) | AI diff tolerance + broad browser/viewport matrix; most expensive |

**Graduation path:** start **free** with built-in snapshots; move to **Percy** when in-repo baselines
and the platform-rendering discipline become a bottleneck and you want a review workflow; move to
**Applitools** when anti-aliasing noise across many browsers makes even Percy's pixel diff too chatty.

## Setup

The Percy CLI (the local agent) is a Node tool — install it even in a .NET repo — plus the NuGet
binding:

```bash
npm install --save-dev @percy/cli      # the agent that renders + uploads
```

```xml
<!-- Tests.csproj -->
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.50.0" />
  <PackageReference Include="PercyIO.Playwright" Version="1.*" />
  <PackageReference Include="NUnit" Version="4.*" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.*" />
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
</ItemGroup>
```

`PERCY_TOKEN` is the **only secret** — a per-project write token. In CI it comes from the secret store
(see the ci-pipelines cross-link), never committed. Locally `export PERCY_TOKEN=<token>`.

## How you run the suite — `percy exec`

You do **not** call Percy's API to start a build. Wrap your existing test command in `percy exec`,
which starts the local Percy agent (a proxy that receives DOM snapshots, runs asset discovery, and
uploads to Percy), runs the suite, then finalizes the build:

```bash
PERCY_TOKEN=<token> npx percy exec -- dotnet test
```

**Percy no-ops gracefully when the agent isn't running.** If you run `dotnet test` *without*
`percy exec` (or `PERCY_TOKEN` is absent), `Percy.Snapshot()` detects Percy is not running, logs a
warning, **skips the snapshot, and the test still passes**. A developer without the token runs the
functional suite untouched — the visual assertions simply don't fire. That's why `Percy.Snapshot` is
safe to leave in shared specs.

## `.percy.yml` — project-wide snapshot config

Set rendering width(s), min height, global CSS, and discovery once, in repo (identical schema across
all three stacks — it's the agent's config, not the language binding's):

```yaml
# .percy.yml
version: 2
snapshot:
  widths:
    - 375    # mobile
    - 1280   # desktop
  min-height: 1024
  percy-css: |
    .intercom-launcher, [data-testid="live-clock"] { visibility: hidden !important; }
  enable-javascript: false
discovery:
  allowed-hostnames:
    - cdn.flexinvest.test
  network-idle-timeout: 250
```

`percy exec --config ./.percy.yml -- dotnet test` if the file isn't at the default location.

## Core pattern — `Percy.Snapshot` on a page-object-driven flow

The page object exposes intent; the test stabilizes **application** state on a condition, then calls
`Percy.Snapshot`. No selectors in the test, no fixed waits.

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
using PercyIO.Playwright;

[TestFixture]
[Parallelizable(ParallelScope.Self)]
public sealed class DashboardTests : PageTest
{
    [Test]
    public async Task Should_Capture_DashboardPercySnapshot_When_Loaded()
    {
        var dashboard = new DashboardPage(Page);
        await dashboard.GotoAsync();
        await dashboard.WaitUntilLoadedAsync();          // stabilize on a condition first…

        Percy.Snapshot(Page, "Dashboard — revenue card");  // …then snapshot (DOM uploaded, rendered server-side)
    }
}
```

`Percy.Snapshot` is a **static, synchronous** call that takes the `IPage` — it does not assert
pass/fail in the test; it uploads a snapshot. Percy decides pass/fail later, server-side, against the
branch baseline, and surfaces it as an **unreviewed status check**, not a thrown assertion. Note it is
*not* awaited (no async overload) — but every Playwright navigation/wait around it still is
(async-all-the-way for the page interactions). Stabilize before snapshotting: Percy captures the DOM
*at call time*, so a half-loaded page uploads a half-loaded snapshot.

## Snapshot options — `Percy.Snapshot(page, name, options)`

Options are an **anonymous object** or a `Percy.Options` dictionary:

```csharp
// Anonymous object
Percy.Snapshot(Page, "Pricing page", new
{
    widths = new[] { 375, 768, 1280 },                  // override .percy.yml per snapshot
    minHeight = 1024,
    scope = "[data-testid=\"pricing-table\"]",          // snapshot only this element's subtree
    enableJavaScript = false,
    percyCSS = "[data-testid=\"promo-banner\"] { visibility: hidden !important; } " +
               "[data-testid=\"last-seen\"] { visibility: hidden !important; }",
});

// Or the typed dictionary
var options = new Percy.Options { { "minHeight", 1280 }, { "widths", new[] { 1280 } } };
Percy.Snapshot(Page, "Pricing page (typed)", options);
```

The options, precisely:

- **`widths`** — viewport widths Percy renders at, server-side. Overrides `.percy.yml`.
- **`minHeight`** — minimum render height (default 1024).
- **`scope`** — CSS selector; Percy snapshots only that element's subtree (the analogue of an element
  screenshot — less noise than full page).
- **`enableJavaScript`** — run JS in Percy's renderer. Off by default (Percy renders the captured DOM
  statically). Turn on only when the page needs client-side JS to paint correctly.
- **`percyCSS`** — CSS injected **only in Percy's renderer**, applied right before the diff. Your
  primary stabilization lever — there is **no per-call pixel-ratio knob**. Hide dynamic regions with
  `visibility: hidden`.

### Hiding dynamic regions is `percyCSS`, not a pixel budget

The built-in skill tames flakiness with `MaxDiffPixelRatio` / `Mask`. **Percy has neither.** The lever
is `percyCSS` (per-snapshot or global in `.percy.yml`). Neutralize the *specific* dynamic region; don't
loosen the whole diff:

```csharp
Percy.Snapshot(Page, "Profile header", new
{
    percyCSS = "img.gravatar { visibility: hidden !important; } " +
               "[data-testid=\"last-seen\"] { visibility: hidden !important; }",
});
```

## CI integration + the review gate

In CI, `percy exec` wraps `dotnet test` exactly as locally; `PERCY_TOKEN` comes from the secret store.
After the build finalizes, Percy posts a **GitHub/GitLab status check** linking the visual review. The
build is **green only once the diffs are approved** in Percy's UI (or auto-approved). Baselines
auto-establish from the **base branch**, so a PR diffs against `main`'s last approved snapshots.

```yaml
# inside your test job — see qa-ci-pipelines-github-actions-dotnet for the full pipeline
- name: Visual tests (Percy)
  env:
    PERCY_TOKEN: ${{ secrets.PERCY_TOKEN }}   # from the secret store; never inline
  run: npx percy exec -- dotnet test
```

Contrast with built-in snapshots: there is **no `-diff.png` artifact to upload** — the diff lives in
Percy's UI. Link the Percy build URL into Allure so reviewers jump straight to it (cross-link
`qa-allure-reporting-dotnet`):

```csharp
[OneTimeTearDown]
public void LinkPercyBuild()
{
    // percy exec exports the build URL in recent CLI versions.
    var url = Environment.GetEnvironmentVariable("PERCY_BUILD_URL");
    if (!string.IsNullOrEmpty(url))
        AllureApi.AddTestAttachment("Percy visual review", "text/uri-list",
            System.Text.Encoding.UTF8.GetBytes(url));
}
```

The review-UI workflow, concretely:
1. PR runs `percy exec -- dotnet test`; Percy renders + diffs against the base-branch baseline.
2. Percy posts a status check: **changes detected** (needs review) or **no changes** (auto-green).
3. A reviewer approves/rejects in Percy's UI. Approving updates the branch baseline.
4. On merge, the approved snapshots become `main`'s baseline for the next PR.

## Anti-patterns

- **Committing `*-snapshots/` PNGs alongside Percy.** Percy keeps baselines in the cloud — in-repo
  PNGs are the built-in-snapshots model and don't apply. *Fix:* delete them; rely on the Percy
  baseline.
- **`await Page.WaitForTimeoutAsync(500)` before `Percy.Snapshot`.** Percy captures the DOM at call
  time; a sleep is flaky and slow. *Fix:* wait on a condition (`document.fonts.ready`, spinner hidden,
  `Locator.WaitForAsync`), then snapshot.
- **Trying to "loosen the diff" to stop flakes.** Percy has no per-call pixel budget. *Fix:* hide the
  specific dynamic region with `percyCSS` (`visibility: hidden`).
- **Running `dotnet test` without `percy exec` and expecting visual coverage.** `Percy.Snapshot`
  silently no-ops when the agent isn't running. *Fix:* run via `percy exec -- dotnet test` with
  `PERCY_TOKEN` set; reserve bare `dotnet test` for functional-only runs.
- **Hardcoding / logging `PERCY_TOKEN`.** It's a write credential. *Fix:* env only, from the CI secret
  store, read lazily, never echoed.
- **Treating a Percy "diff" as a thrown test failure.** It's an unreviewed **status check**, not an
  in-test assertion. *Fix:* gate the merge on the Percy status check; review in the UI.
- **Full-page snapshots of a dynamic page.** Noisy reviews. *Fix:* `scope` to the element under test;
  `percyCSS` away the rotating bits.

## Examples

**End-to-end: a pricing-table visual gate reviewed in Percy.**

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Self)]
public sealed class PricingTests : PageTest
{
    [Test]
    public async Task Should_Capture_PricingTable_When_PlansLoaded()
    {
        var pricing = new PricingPage(Page);
        await pricing.GotoAsync();
        await pricing.WaitUntilPlansRenderedAsync();         // condition, not sleep
        await Page.EvaluateAsync("document.fonts.ready");     // fonts settled before DOM capture

        Percy.Snapshot(Page, "Pricing — plan table", new
        {
            scope = "[data-testid=\"pricing-table\"]",        // element subtree, not full page
            widths = new[] { 375, 1280 },                     // mobile + desktop, rendered server-side
            percyCSS = "[data-testid=\"promo-banner\"] { visibility: hidden !important; }", // rotates daily
        });
    }
}
```

Lifecycle for this test:
1. Dev makes an intended CSS change to the pricing table.
2. CI runs `percy exec -- dotnet test`; Percy renders at 375px + 1280px and diffs vs `main`.
3. Percy's status check flags the change; the dev reviews + approves the diff in Percy's UI.
4. On merge, the approved render becomes `main`'s baseline — the next PR diffs against it.

## Rules (hard constraints)

- Visual regression is an assertion layer on existing page objects/specs — add `Percy.Snapshot`, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- Stabilize **application** state on a condition before `Percy.Snapshot`; never `WaitForTimeoutAsync` —
  Percy captures the DOM at call time. Async-all-the-way on the surrounding Playwright calls.
- Run the suite under `percy exec -- dotnet test`; `Percy.Snapshot` no-ops gracefully without the agent.
- `PERCY_TOKEN` is the **only** secret: env-only, from the CI secret store, read lazily, never logged
  or committed.
- No in-repo `*-snapshots/` baselines, no `-{platform}` naming, no delete-and-rerun — baselines live in
  Percy and are managed via the **review UI**, auto-established from the base branch.
- Stabilize/neutralize dynamic regions with **`percyCSS`** (`visibility: hidden`) and `scope`, not a
  diff budget — Percy has no per-call pixel-ratio knob.
- Prefer `scope`d element snapshots over full-page; render responsive widths via `widths` /
  `.percy.yml`, not extra tests.
- The gate is the **Percy status check** (review/approve), not a thrown assertion or a local artifact.

## Cross-references

- `qa-visual-regression-percy-typescript` — the **canonical** skill this ports (`@percy/playwright`
  `percySnapshot`, `.percy.yml`, `percy exec`).
- `qa-visual-regression-percy-java` — the Java / TestNG sibling (`io.percy.playwright.Percy`,
  `new Percy(page).snapshot(name, ...)`).
- `qa-visual-regression-playwright-snapshots-dotnet` (#17) — the **free** sibling: in-repo baselines
  you diff yourself, with the CI-container discipline Percy removes. Start here; graduate to Percy.
- `qa-visual-regression-applitools-dotnet` (#19, next) — the visual-AI sibling: AI diff tolerance +
  a cross-browser rendering grid.
- `qa-ui-test-author-playwright-dotnet` — the page objects/specs `Percy.Snapshot` is called inside.
- `qa-ci-pipelines-github-actions-dotnet` — where `PERCY_TOKEN` is sourced and `percy exec` wraps
  `dotnet test`.
- `qa-allure-reporting-dotnet` — link the Percy build URL into the report.
