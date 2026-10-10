# Audit — Playwright in the .NET QA lane (Microsoft.Playwright + NUnit)

**Date:** 2026-10-10 · **Mode:** read-only, no repo file edited · **Root:** `/Users/aleksandarkotrulev/RiderProjects/SkillsLibrary`

**Scope:** `qa/dotnet/agents/*`, `qa/dotnet/commands/*`, every `qa/dotnet/skills/**` file mentioning Playwright (56 files from `grep -ril playwright`), plus the Playwright parts of `qa/reporting/dotnet/**` and `qa/cicd/dotnet/**`. The TypeScript siblings were read for the parity comparison.

**How API claims were checked.** Every claim about the Playwright API was checked against the current source:
- `microsoft/playwright-dotnet` `main` via `gh api`: `IWebSocket.cs`, `ICDPSessionEvent.cs`, `PageScreenshotOptions.cs`, `BrowserNewContextOptions.cs`, and `Playwright.TestAdapter/PlaywrightSettings*.cs`
- the `microsoft/playwright` `toHaveURL` matcher
- the playwright.dev/dotnet API pages: LocatorAssertions, PageAssertions, Request, WebSocketRoute, Locator, test-runners, trace-viewer, docker, release-notes
- the NuGet flat-container index
- the `@playwright/mcp` README
- `allure-csharp` `AllureApi.cs`

**Current reference versions (2026-10-10):**

| Thing | Current |
|---|---|
| `Microsoft.Playwright` / `.NUnit` | **1.63.0** (GitHub release 2026-09-21) |
| Docker image | `mcr.microsoft.com/playwright/dotnet:v1.63.0-{noble,jammy,resolute}` |
| `Deque.AxeCore.Playwright` | 4.13.0 |
| `Allure.NUnit` | 2.15.0 (3.0.0-preview.1 exists) |
| `PercyIO.Playwright` | 1.0.4 |
| Applitools Playwright package | `Eyes.Playwright` 1.37.49; **`Applitools.Playwright` does not exist** |
| `Reqnroll.NUnit` | 3.3.4 |
| `Microsoft.Playwright.CLI` | 1.2.3 (legacy) |
| Azure Playwright Workspaces | `Azure.Developer.Playwright.NUnit` 1.0.0 |

Classes: **Data issue** = a stale version or fact · **Code issue** = wrong example code · **Logical conflict** = two sources disagree.

---

## 0. Top findings

| # | Sev | Class | Finding | Where |
|---|---|---|---|---|
| T1 | blocker | Code | The "built-in" .NET visual-regression reference teaches **APIs that do not exist in Microsoft.Playwright**: `ToHaveScreenshotAsync`, `ToMatchSnapshotAsync`, `LocatorAssertionsToHaveScreenshotOptions`, `MaxDiffPixelRatio`/`Threshold`, `StylePath`, auto-created `*.cs-snapshots/` baselines, and `*-diff.png` output. The router calls it "start here". | `visual-regression/references/playwright-snapshots.md:25-27,67,143,169,196,209-214,227,258-268`; `visual-regression/SKILL.md:18,26` |
| T2 | blocker | Code | All three CI templates shard with `-- Playwright.Shard=i/N`. Microsoft.Playwright.NUnit has no sharding: the settings parser prints "Playwright>Shard is not implemented" and ignores it. **Every shard runs the whole suite**, so runtime and results are multiplied N×. | `ci-pipelines/references/azure-pipelines.md:37,176,245`; `github-actions.md:39,261`; `gitlab-ci.md:53,198` |
| T3 | blocker | Data | The NuGet package **`Applitools.Playwright` does not exist** (the real one is `Eyes.Playwright`), so restore fails. | `visual-regression/references/applitools.md:4,44,138`; `ui-project-setup/SKILL.md:40` |
| T4 | blocker | Code | The flagship template's `[SetUpFixture] AuthSetup` lives in namespace `Example.Tests.Support`, but the tests are in `Example.Tests.Specs`. NUnit scopes a SetUpFixture to its own namespace, so the storage-state file is never written and every `AuthenticatedBaseTest` fails. | `ui-test-author/playwright/SKILL.md:179` vs `:138,:205-206` |
| T5 | blocker in the flagship, major elsewhere | Code | **Relative navigation with no `BaseURL` anywhere.** `BaseTest`/`PageTest` subclasses never set `BaseURL`, so `GotoAsync("/login")` throws "Cannot navigate to invalid URL". The same holds for `Page.APIRequest.PostAsync("/api/orders")`. | See D-01 |
| T6 | major | Logical | **No skill `qa-ui-dotnet` can load teaches evidence capture** (trace/screenshot/video), yet its Step 0 gate requires it. The only recipe is in `qa/reporting` (outside the agent's load fence) and writes traces to `%TEMP%`. CI uploads `bin/.../playwright-traces`, which nothing writes, so the trace artifact is always empty. | `qa-ui-dotnet.md:18,97`; `ui-project-setup/SKILL.md:76,125,131,152`; `test-reports/SKILL.md:120-137`; `azure-pipelines.md:251`; `github-actions.md:268`; `gitlab-ci.md:207` |
| T7 | major | Data | **Five different Playwright versions, all 8–16 releases stale:** 1.47 (image), 1.49 (author + BDD), 1.50 (5 references + image), 1.55 (scaffold). The current version is 1.63.0. | §1 |
| T8 | major | Code | Several samples **do not compile**: the WebSocket mock (`OnMessage` gets an `IWebSocketFrame`, not a string), `ws.WaitForEventAsync(...)` (no such method on `IWebSocket`), the CDP `OnEvent` payload (`JsonElement?`), and `AllureApi.AddTestAttachment` (no such method). | D-04, D-05, D-06 |
| T9 | major | Code | The Accelerator convention `ToHaveURLAsync("**/dashboard")` **always fails**: a string is an exact match after BaseURL resolution, and globs are honoured by `WaitForURLAsync`, not the assertion. The page-level selector APIs (`Page.FillAsync(selector)`, `Page.InnerTextAsync(selector)`) are discouraged and turn assertions into one-shot reads. | `inhouse-framework-conventions/SKILL.md:92-98,126` |
| T10 | major | Logical | `// TODO: missing data-testid` inline markers are **mandated**, contradicting CLAUDE.md ("no TODO/FIXME left behind") and the agent's own "Emit no comments" rule. | `qa-ui-dotnet.md:35` vs `:44`; `ui-test-author/playwright/SKILL.md:227,232`; `page-objects-from-url/SKILL.md:8,115,138` |
| T11 | major | Data | `.runsettings` is **never taught**: 0 hits for `runsettings`, `BrowserName` config, `LaunchOptions` XML, `ExpectTimeout`, `TestIdAttribute` or `NumberOfTestWorkers`. Cross-browser runs, headed debugging, global expect timeout and the test-id attribute therefore have no documented home. | grep, lane-wide |
| T12 | major | Logical | The conformance checklist rates `Playwright.CreateAsync()` in a test or `[SetUp]` as a **blocker** (E11), but six library skills teach exactly that pattern. Lighthouse even does it inside a `[Test]`. | `conformance-checklist.md:112` vs D-11 |

---

## 1. Version-pin inventory

There are **50 inventory rows**. Rows 1–19 are the **19 Playwright version pins** (package, image or floor). Rows 20–31 are Playwright-ecosystem and companion pins. Rows 32–40 are test-infra pins inside Playwright templates. Rows 41–50 are TFM/SDK strings.

### 1a. Microsoft.Playwright packages, Docker images, version floors

| # | file:line | Exact string | Note |
|---|---|---|---|
| 1 | `qa/dotnet/skills/ui-test-author/playwright/SKILL.md:57` | `<PackageReference Include="Microsoft.Playwright" Version="1.49.0" />` | Redundant: `.NUnit` already pulls it in. |
| 2 | `qa/dotnet/skills/ui-test-author/playwright/SKILL.md:58` | `<PackageReference Include="Microsoft.Playwright.NUnit" Version="1.49.0" />` | Conflicts with row 4. |
| 3 | `qa/dotnet/skills/bdd-project-scaffold/SKILL.md:69` | `<PackageReference Include="Microsoft.Playwright" Version="1.49.0" />` | |
| 4 | `qa/dotnet/skills/ui-project-setup/SKILL.md:34` | `` `Microsoft.Playwright.NUnit` \| **1.55.0** `` | The setup owner's pin. |
| 5 | `qa/dotnet/skills/accessibility-testing/references/axe-playwright.md:29` | `Microsoft.Playwright.NUnit" Version="1.50.0"` | |
| 6 | `qa/dotnet/skills/accessibility-testing/references/lighthouse-ci.md:45` | `Microsoft.Playwright.NUnit" Version="1.50.0"` | |
| 7 | `qa/dotnet/skills/visual-regression/references/playwright-snapshots.md:41` | `Microsoft.Playwright.NUnit" Version="1.50.0"` | |
| 8 | `qa/dotnet/skills/visual-regression/references/percy.md:48` | `Microsoft.Playwright.NUnit" Version="1.50.0"` | |
| 9 | `qa/dotnet/skills/visual-regression/references/applitools.md:43` | `Microsoft.Playwright.NUnit" Version="1.50.0"` | |
| 10 | `qa/cicd/dotnet/skills/ci-pipelines/references/gitlab-ci.md:189` | `image: mcr.microsoft.com/playwright/dotnet:v1.47.0-jammy` | Skew against every package pin. A 2024 image has no .NET 10 SDK, yet the same job builds `net10.0` (`:206-207`). |
| 11 | `qa/dotnet/skills/visual-regression/references/playwright-snapshots.md:246` | `mcr.microsoft.com/playwright/dotnet:v1.50.0-noble` | Says "tag must match your Microsoft.Playwright version" (`:245`), which contradicts rows 1, 2 and 4. |
| 12 | `qa/dotnet/skills/realtime-stream-testing/SKILL.md:78` | `(≥ **1.48** for RouteWebSocketAsync)` | Correct floor (1.48). |
| 13 | `qa/dotnet/skills/realtime-stream-testing/SKILL.md:230` | `RouteWebSocketAsync, ≥ 1.48` | Correct. |
| 14 | `qa/dotnet/skills/realtime-stream-testing/SKILL.md:233` | `(added in Playwright **1.48**)` | Correct. |
| 15 | `qa/dotnet/skills/network-mocking/references/cdp.md:12` | `(Playwright ≥ 1.49)` | |
| 16 | `qa/dotnet/skills/network-mocking/references/playwright-routes.md:10` | `(Playwright ≥ 1.49)` | |
| 17 | `qa/dotnet/skills/bdd-project-scaffold/SKILL.md:19` | `Microsoft.Playwright (≥ 1.49)` | |
| 18 | `qa/dotnet/skills/network-mocking/references/playwright-routes.md:315` | `not supported** since Playwright 1.43` | **Wrong.** Glob `?`/`[]` were dropped in **1.52**, so they still work at the 1.49/1.50 pins. |
| 19 | `qa/dotnet/skills/network-mocking/references/playwright-routes.md:352` | `No glob ?/[abc] since 1.43` | Same error. |

### 1b. Playwright-ecosystem and companion packages

| # | file:line | Exact string | Note |
|---|---|---|---|
| 20 | `qa/dotnet/skills/page-objects-from-url/SKILL.md:31` | `claude mcp add playwright npx @playwright/mcp@latest -- --caps=testing,storage` | Unpinned `@latest`. The caps names are correct per the README. |
| 21 | `qa/dotnet/skills/browser-cloud-setup/references/details.md:75` | `["client.playwrightVersion"] = "1.x", // pin to the installed Playwright in real config` | Placeholder plus inline comment. |
| 22 | `qa/dotnet/skills/ui-project-setup/SKILL.md:50` | `dotnet tool install Microsoft.Playwright.CLI && playwright install` | Legacy tool, stalled at 1.2.3; not in current docs. Without `--global` it also needs the manifest. |
| 23 | `qa/dotnet/skills/ui-project-setup/SKILL.md:38` | `` `Deque.AxeCore.Playwright` \| **4.*** `` | Floating. |
| 24 | `qa/dotnet/skills/accessibility-testing/references/axe-playwright.md:30` | `Deque.AxeCore.Playwright" Version="4.*"` | Floating. |
| 25 | `qa/dotnet/skills/accessibility-testing/references/axe-playwright.md:39` | `Deque.AxeCore.Playwright 4.11.x bundles axe-core 4.11.x` | Current is 4.13.0. |
| 26 | `qa/dotnet/skills/ui-project-setup/SKILL.md:40` | `` `PercyIO.Playwright` 1.* / `Applitools.Playwright` 3.* `` | The Applitools package name does not exist. |
| 27 | `qa/dotnet/skills/visual-regression/references/percy.md:49` | `PercyIO.Playwright" Version="1.*"` | |
| 28 | `qa/dotnet/skills/visual-regression/references/applitools.md:44` | `Applitools.Playwright" Version="3.*"` | **Nonexistent package** (T3). |
| 29 | `qa/dotnet/skills/ui-project-setup/SKILL.md:37` | `` `Allure.NUnit` \| **2.12.1** `` | Current is 2.15.0. Same pin at `api-project-setup/SKILL.md:38,138`. |
| 30 | `qa/dotnet/skills/bdd-project-scaffold/SKILL.md:74` | `<!-- <PackageReference Include="Reqnroll.Allure" Version="..." /> -->` | Unversioned placeholder. |
| 31 | `qa/dotnet/skills/bdd-project-scaffold/SKILL.md:67-68` | `Reqnroll.NUnit" Version="3.3.4"` / `Reqnroll.Microsoft.Extensions.DependencyInjection" Version="3.3.4"` | Current. |

### 1c. Test-infrastructure pins inside Playwright templates

| # | file:line | Exact string | Note |
|---|---|---|---|
| 32 | `qa/dotnet/skills/ui-project-setup/SKILL.md:31-33` | `NUnit` **4.3.2** · `NUnit3TestAdapter` **5.0.0** · `Microsoft.NET.Test.Sdk` **17.14.1** | The CPM table. |
| 33 | `qa/dotnet/skills/ui-project-setup/SKILL.md:35-36` | `Selenium.WebDriver`+`Selenium.Support` **4.44.0** · `FluentAssertions` **6.12.1** | |
| 34 | `qa/dotnet/skills/ui-test-author/playwright/SKILL.md:59-61` | `NUnit" Version="4.2.2"` · `NUnit3TestAdapter" Version="4.6.0"` · `Microsoft.NET.Test.Sdk" Version="17.11.1"` | Drifts from row 32. Inline versions under CPM give NU1008. |
| 35 | `qa/dotnet/skills/bdd-project-scaffold/SKILL.md:70-72` | `4.2.2` / `4.6.0` / `17.11.1` | Same drift. |
| 36 | `qa/dotnet/skills/accessibility-testing/references/axe-playwright.md:31-33` | `NUnit 4.*` / `NUnit3TestAdapter 4.*` / `Microsoft.NET.Test.Sdk 17.*` | Floating, and contradicts checklist A8 (`conformance-checklist.md:34`). |
| 37 | `qa/dotnet/skills/accessibility-testing/references/lighthouse-ci.md:46-48` | same `4.* / 4.* / 17.*` | |
| 38 | `qa/dotnet/skills/visual-regression/references/playwright-snapshots.md:42-44` | same | |
| 39 | `qa/dotnet/skills/visual-regression/references/percy.md:50-52` | same | |
| 40 | `qa/dotnet/skills/visual-regression/references/applitools.md:45-47` | same | |

### 1d. TFM, SDK, `playwright.ps1` paths and CI images

| # | file:line | Exact string |
|---|---|---|
| 41 | `qa/dotnet/skills/ui-project-setup/SKILL.md:10,30,45,49,93,96-97,110` | `net10.0` · `**10.0 (LTS)**` · `--sdk-version 10.0.100` · `pwsh PlaywrightTests/bin/Debug/net10.0/playwright.ps1 install` |
| 42 | `qa/dotnet/skills/ui-test-author/playwright/SKILL.md:8,12,51,314` | `.NET 10 + NUnit` · `<TargetFramework>net10.0</TargetFramework>` · `pwsh bin/Debug/net10.0/playwright.ps1 install` |
| 43 | `qa/dotnet/skills/visual-regression/references/playwright-snapshots.md:49` | `pwsh bin/Debug/net10.0/playwright.ps1 install --with-deps chromium` |
| 44 | `qa/dotnet/skills/bdd-project-scaffold/SKILL.md:10,61` | `net10.0` |
| 45 | `qa/cicd/dotnet/skills/ci-pipelines/references/azure-pipelines.md:237,251` | `UiTests/bin/$(buildConfiguration)/net10.0/playwright.ps1 install --with-deps chromium` · `.../net10.0/playwright-traces` |
| 46 | `qa/cicd/dotnet/skills/ci-pipelines/references/github-actions.md:253,268` | `.../net10.0/playwright.ps1 install --with-deps chromium` · `.../net10.0/playwright-traces` |
| 47 | `qa/cicd/dotnet/skills/ci-pipelines/references/gitlab-ci.md:48,69,206-207` | `mcr.microsoft.com/dotnet/sdk:10.0` · `.../net10.0/allure-results/` · `.../net10.0/playwright-traces/` |
| 48 | `qa/reporting/dotnet/skills/test-reports/SKILL.md:205,213-214,236,243` | `bin/Debug/net10.0/allure-results` · `allure-2.27.0` · `mcr.microsoft.com/dotnet/sdk:10.0` |
| 49 | **Stale ".NET 8" labels** (Data, minor) — the library primary is .NET 10 | `network-mocking/SKILL.md:6` · `references/playwright-routes.md:3,9` · `references/cdp.md:3,11` · `references/proxy.md:3,13` · `visual-regression/SKILL.md:6` · `accessibility-testing/SKILL.md:6` · `page-objects-from-url/SKILL.md:10` · `responsive-testing/SKILL.md:53` (its own description `:3` says .NET 10) · `realtime-stream-testing/SKILL.md:6,68` · `api-test-author/playwright/SKILL.md:37` · `gherkin-step-code/SKILL.md:6,13` · `inhouse-framework-conventions/SKILL.md:8` (description `:3` says 10) · also `email-testing/SKILL.md:6`, `feature-flag-testing/SKILL.md:6,56`, `data-driven-testing/SKILL.md:6,54`, `test-data-builder/SKILL.md:6,8`, `device-cloud/SKILL.md:14`, `bdd-reviewer/SKILL.md:6`, `ui-test-author/selenium/SKILL.md:8,12` |
| 50 | Agents (correct, version-aware) | `qa-ui-dotnet.md:66,113` · `qa-bdd-dotnet.md:54,100`: `net8.0/9.0/10.0` lanes |

**Inconsistencies.**
- **Packages:** 1.49.0 (rows 1–3) vs 1.50.0 (rows 5–9) vs 1.55.0 (row 4) vs latest 1.63.0.
- **Images:** v1.47.0-jammy (row 10) vs v1.50.0-noble (row 11).
- **Floors** (1.48 / 1.49) are plausible. **"1.43" is wrong (it is 1.52).**
- **NUnit stack:** two pin sets (rows 32 vs 34–35) plus floating `4.*`/`17.*` (rows 36–40).
- **No single source of truth.** `ui-project-setup` declares CPM "the only version source" (`ui-project-setup/SKILL.md:26`), but every other template ships inline `Version=` attributes.

---

## 2. Capability coverage matrix

Legend:
- ✅ taught correctly
- ⚠ taught but stale or partly wrong
- ❌ wrong
- ∅ missing (0 grep hits in `qa/dotnet`, `qa/reporting/dotnet` and `qa/cicd/dotnet`)

### 2a. Locators

| Capability | Where taught | Status |
|---|---|---|
| `GetByRole(AriaRole.X, new() { Name = … })` | `ui-test-author/playwright/SKILL.md:113,228` · `network-mocking/references/playwright-routes.md:127,182` | ✅ |
| `GetByLabel` / `GetByPlaceholder` / `GetByText(Exact)` | `ui-test-author/playwright/SKILL.md:111-112,229-231,269` | ✅ |
| `GetByTestId` | `ui-test-author/playwright/SKILL.md:114,227`; `page-objects-from-url/SKILL.md:114` | ✅. House policy is testid-first, a deliberate inversion of Playwright's role-first guidance (`page-objects-from-url/SKILL.md:136`). |
| `GetByAltText` / `GetByTitle` | — | ∅ |
| `Filter(new() { Has / HasNot / HasText / HasNotText / Visible })` | — | ∅. Not in TS/Java either as a Locator idiom. `Visible` is 1.51; `Locator.Visible` is 1.63. |
| `And()` / `Or()` | — (only MailKit `SearchQuery.And` in `email-testing/references/gmail-imap.md:41,131`) | ∅ |
| Chaining / "within" scoping | `page-object-design/SKILL.md:91` (rule, prose only); review `ui-test-author/review/SKILL.md:109,143`; one inline chain at `visual-regression/references/playwright-snapshots.md:122` and `axe-playwright.md:87` | ⚠ The rule exists but there is no code pattern (no component class taking a parent `ILocator`). |
| `Describe()` (1.53) | — | ∅ |
| `FrameLocator` / `ContentFrame` (1.43) | — | ∅. A notable gap for payment iframes: `playwright-routes.md:253` mocks Stripe and `axe-playwright.md:124,131` excludes iframes. |
| Strictness | `ui-test-author/playwright/SKILL.md:269` ("strict-mode violation") | ✅ brief |
| `Nth` / `First` misuse | Only `cards.First` for a wait (`responsive-testing/SKILL.md:166`, fine) | ∅ guidance. Checklist F5 even sanctions "a static parent locator addressed by index" (`conformance-checklist.md:129`). |
| `SetTestIdAttribute` | `page-objects-from-url/SKILL.md:36` only | ⚠ It is not in the authoring skill, and the runsettings `TestIdAttribute` key (supported, see `PlaywrightSettingsXml.cs`) is never mentioned. Meanwhile review/selenium use `data-test` (D-14). |

### 2b. Assertions

| Capability | Where taught | Status |
|---|---|---|
| `Expect(...)` web-first assertions (`ToBeVisibleAsync`, `ToHaveTextAsync`, `ToHaveCountAsync`, `ToBeEnabledAsync`, `ToBeHiddenAsync`) | `ui-test-author/playwright/SKILL.md:126,153,164-166,250-251` | ✅ |
| `ToHaveAccessibleNameAsync` / `Description` / `ErrorMessage`, `ToHaveRoleAsync` | — | ∅ in all three lanes, though they were added in 1.44–1.50 |
| `ToContainClassAsync` (1.52) / `ToHaveClassAsync` | — | ∅ |
| `ToMatchAriaSnapshotAsync` (locator 1.49, page 1.60) | — | ∅ in all three lanes |
| `ToHaveURLAsync` | `inhouse-framework-conventions/SKILL.md:126` | ❌ The glob string never matches (T9) |
| `SetDefaultExpectTimeout` | `visual-regression/references/playwright-snapshots.md:78` | ⚠ Correct API, but taught only to serve a nonexistent assertion. No runsettings `ExpectTimeout`. |

### 2c. NUnit integration

| Capability | Where taught | Status |
|---|---|---|
| `PageTest` | `ui-test-author/playwright/SKILL.md:8,68-88` | ✅ |
| `ContextTest` / `BrowserTest` / `PlaywrightTest` | — | ∅ |
| `ContextOptions()` override | `ui-test-author/playwright/SKILL.md:205-206`; `playwright-routes.md:274,342`; `playwright-snapshots.md:65`; `cdp.md:156` (`/* shared options */`) | ⚠ The signature is right. Each subclass returns a fresh `new()`, so options never compose and `BaseURL` is lost. Only the visual reference sets `BaseURL`, and it is hardcoded `http://localhost:3000`. |
| `.runsettings` (`BrowserName`, `Headless`, `LaunchOptions`, `ExpectTimeout`, `TestIdAttribute`, `NumberOfTestWorkers`) | — | ∅ (T11) |
| `HEADED=1` | `ui-project-setup/SKILL.md:120` ("if your fixture reads HEADED"); `ui-test-author/playwright/SKILL.md:315` ("via LaunchOptions") | ⚠ The adapter reads `HEADED=1` natively (`PlaywrightSettingsProvider.cs:109`), so the hedge is wrong. The docs-preferred form is `dotnet test -- Playwright.LaunchOptions.Headless=false`. |
| Parallelism | `ui-test-author/playwright/SKILL.md:140` | ✅ `ParallelScope.Self` (the only supported scope). `data-driven-testing/SKILL.md:258` shows `ParallelScope.All` with no Playwright caveat (minor). |
| No static mutable state | `page-object-design/SKILL.md:73`; `bdd-project-scaffold/SKILL.md:188` | ✅ |
| MSTest / xUnit packages (`Microsoft.Playwright.MSTest[.v4]`, `.Xunit`, `.Xunit.v3`, added 1.50/1.55) | — | ∅. The audit still detects MSTest/xUnit lanes (`standards-audit/SKILL.md:77`). |

### 2d. Evidence capture

| Capability | Where taught | Status |
|---|---|---|
| Screenshot (`PageScreenshotOptions`: `Mask`, `Animations`, `Caret`, `Style`, `FullPage`, `Scale`) | `test-reports/SKILL.md:128` (bare `Page.ScreenshotAsync()`) | ⚠ The options are taught only inside the nonexistent `ToHaveScreenshotAsync` (`playwright-snapshots.md:172-197`). Real option names: `Style` (string), not `StylePath`. |
| Video (`RecordVideoDir` / `RecordVideoSize`, `Page.Video.SaveAsAsync` / `DeleteAsync` after context close) | — | ∅. CI promises video retention (`azure-pipelines.md:40,377`; `github-actions.md:43,411`; `gitlab-ci.md:57,312`). |
| Tracing `StartAsync` / `StopAsync` (Path only on failure) | `test-reports/SKILL.md:123-137` | ⚠ Start/stop are correct. On a pass it returns early without stopping (acceptable), but on failure it writes to `Path.GetTempPath()` (`:131`), not `TestContext.CurrentContext.WorkDirectory/playwright-traces`. It uses no `Title` and never calls `TestContext.AddTestAttachment`. |
| Tracing `StartChunkAsync` / `GroupAsync` (1.49) / HAR-on-tracing (1.60) | — | ∅ |
| HAR (`RecordHarPath`, `RouteFromHARAsync`) | `playwright-routes.md:52,245-274,336-339,344` | ✅ (names verified) |
| `TestContext.AddTestAttachment` | `browser-cloud-setup/references/details.md:276` | ✅, but only for a BrowserStack link. Not used for traces or screenshots. |
| Allure attachments | `test-reports/SKILL.md:129,133`; `axe-playwright.md:258,267`; `playwright-snapshots.md:282`; `lighthouse-ci.md:224-226` | ⚠ The byte[] overloads are used without `fileExtension`. `percy.md:230` and `applitools.md:266` call a nonexistent `AllureApi.AddTestAttachment` (D-06). `AllureApi.AddScreenDiff` exists and is never used. |

### 2e. Network, time, emulation

| Capability | Where taught | Status |
|---|---|---|
| `RouteAsync` (Fulfill / Abort / Continue / Fallback / Fetch) | `playwright-routes.md:42-54,62-133,215-243,311-360` | ✅ Accurate: handler order, `Json`, `ServiceWorkers = Block`, redirect note. The `PostDataJSON` property is correct. |
| `RouteFromHARAsync` | `playwright-routes.md:251-271` | ✅ |
| `RouteWebSocketAsync` | `realtime-stream-testing/SKILL.md:230-262` | ❌ The sample does not compile: `OnMessage(message => message.Contains(...))`, where the handler receives `IWebSocketFrame` (use `frame.Text`). See D-04. |
| WebSocket observe | `realtime-stream-testing/SKILL.md:206-228` | ❌ `ws.WaitForEventAsync("framereceived", …)` does not exist on `IWebSocket`, which exposes only events plus `IsClosed`/`Url`. `IsClosed()` is a property, not a method. |
| `APIRequestContext` | `api-test-author/playwright/SKILL.md:73-123`; `ui-test-author/playwright/SKILL.md:212-221` | ✅ (`DataObject`, `ExtraHTTPHeaders`, `StorageStatePath`, `FailOnStatusCode` off) |
| CDP (`NewCDPSessionAsync`) | `network-mocking/references/cdp.md:60-175` | ⚠ `OnEvent` gives `JsonElement?`, so `json.GetProperty` does not compile (`cdp.md:83-85`); the prose at `:5,:48` is wrong too. |
| Clock (`Page.Clock`, 1.45) | — | ∅. `visual-regression/SKILL.md:38` says "freeze … clocks" with no API. `language-testing` relies on seeded instants. |
| Emulation: `Playwright.Devices` | `responsive-testing/SKILL.md:49,211` | ⚠ It points to `ui-test-author/playwright` for device profiles, which never mentions them. |
| Emulation: viewport | `responsive-testing/SKILL.md:65,94,163,178-186` | ✅ (`SetViewportSizeAsync`). It contradicts its own rule "viewport via `ContextOptions()`" at `:65-66,228`. |
| Emulation: `ColorScheme` / `ReducedMotion` / `ForcedColors` | — | ∅ |
| Emulation: `Locale` / `TimezoneId` | `language-testing/references/details.md:38-42`; `language-testing/SKILL.md:59,272,304` | ✅ API (but see D-12 on the lifecycle) |
| Emulation: `Geolocation` / `Permissions` (browser) | — | ∅. Only Appium `autoGrantPermissions` (`device-cloud/SKILL.md:175`). |

### 2f. Tooling

| Capability | Where taught | Status |
|---|---|---|
| Aria snapshots | — | ∅ |
| Codegen (`pwsh bin/Debug/net10.0/playwright.ps1 codegen`) | — | ∅. It would be the natural fallback when the MCP server is unavailable (`page-objects-from-url/SKILL.md:28`). |
| Trace viewer | Mentions at `ui-test-author/playwright/SKILL.md:293`, `playwright-routes.md:369`, `cdp.md:351` | ⚠ `ui-project-setup/SKILL.md:125` uses `npx playwright show-trace`, which needs Node. The .NET docs use `pwsh bin/Debug/netX/playwright.ps1 show-trace` or trace.playwright.dev. |
| `PWDEBUG` | — | ∅ |
| Playwright MCP tools in agents | `qa-ui-dotnet.md:4` and `qa-bdd-dotnet.md:4`, each listing: `browser_navigate`, `browser_snapshot`, `browser_evaluate`, `browser_click`, `browser_type`, `browser_fill_form`, `browser_select_option`, `browser_handle_dialog`, `browser_wait_for`, `browser_take_screenshot`, `browser_generate_locator`, `browser_set_storage_state`, `browser_storage_state`. Skill usage: `page-objects-from-url/SKILL.md:28,61,62,67,69,84-86` (navigate, snapshot, evaluate, type, click, handle_dialog, set_storage_state, generate_locator). | ✅ All names exist. `generate_locator` needs `--caps=testing`; the two storage tools need `--caps=storage`, as documented at `page-objects-from-url/SKILL.md:31-35`. `target` param guidance (`:37`) matches the README. Gap: `browser_hover`, `browser_press_key`, `browser_tabs`, `browser_navigate_back` and `browser_resize` are not granted, yet `:49,:85` ask for hover/menu-revealed states. `@latest` is unpinned. |
| Playwright Test Agents (planner/generator/healer) | — | N/A for .NET (it is a `@playwright/test` runner feature). Not mentioned in TS either. |
| WebMCP (`navigator.modelContext`) | — | ∅ in all three lanes (0 hits for `WebMCP|webmcp|modelContext`) |

---

## 3. Anti-patterns and defects in examples

Format: `| Sev | Class | Location | Issue | Suggested fix |`. D-numbers continue from §0.

### 3a. Wrong or non-compiling example code

| ID | Sev | Class | Location | Issue | Suggested fix |
|---|---|---|---|---|---|
| D-01 | blocker / major | Code | **Flagship:** `ui-test-author/playwright/SKILL.md:77-88,117,194,216`. **Same family:** `axe-playwright.md:83,178,227,276`; `playwright-routes.md:116,125,177,205,282,305`; `responsive-testing/SKILL.md:95,164,179`; `realtime-stream-testing/SKILL.md:213,251`; `language-testing/references/details.md:38-44,68,77,138,149`; `bdd-project-scaffold/SKILL.md:161`; `production-uptime-checks/SKILL.md:162-166`; `browser-cloud-setup/references/details.md:103` | Relative `GotoAsync` / `APIRequest` with no `BaseURL` on any context. Only `playwright-snapshots.md:65` sets one, and it is hardcoded. | Put `BaseURL` (from env/appsettings) in the base `ContextOptions()`. Subclasses must call `base.ContextOptions()` and amend it, not return `new()`. |
| D-02 | blocker | Code | `ui-test-author/playwright/SKILL.md:179` vs `:138` | The SetUpFixture namespace does not cover the tests (T4). | Move `AuthSetup` to the root test namespace, or outside any namespace. |
| D-03 | blocker | Code | `visual-regression/references/playwright-snapshots.md` (whole file; key lines `:25-27,67,143,169-182,196,209-215,227,241-249,258-268`) | Nonexistent assertion API, options and baseline workflow (T1). | Rewrite: `await locator.ScreenshotAsync(new() { Animations = Disabled, Caret = Hide, Mask = […], Style = "…", Scale = Css })` + an image comparer (e.g. `Verify.Playwright`, or ImageSharp/Codeuctivity compare) + `AllureApi.AddScreenDiff(expected, actual, diff)`. Or route to Percy/Applitools. |
| D-04 | major | Code | `realtime-stream-testing/SKILL.md:219` (`ws.WaitForEventAsync("framereceived", new() { Predicate = … })`), `:228` (`IsClosed()`), `:244-246` (`message.Contains`), `:269,:356` (rules cite `WaitForEventAsync(predicate)`) | Does not compile against `IWebSocket` (events + `IsClosed`/`Url` only) or `IWebSocketRoute.OnMessage(Action<IWebSocketFrame>)`. | Use a `TaskCompletionSource<IWebSocketFrame>` set from `ws.FrameReceived += …` and `.WaitAsync(timeout)`. Use `frame.Text == "subscribe"`. Make `IsClosed` a property. |
| D-05 | major | Code | `network-mocking/references/cdp.md:83-85` (+ prose `:5,:48`) | The `OnEvent` payload is `JsonElement?`, so `json.GetProperty` is CS1061. | `json!.Value.GetProperty("response")`. Fix the prose. |
| D-06 | major | Code | `visual-regression/references/percy.md:230`; `visual-regression/references/applitools.md:266` | `AllureApi.AddTestAttachment` does not exist. The real methods are `AddAttachment`, `AddGlobalAttachment` and `AddScreenDiff`. It is also called in `[OneTimeTearDown]`, where no test is running. | `AllureApi.AddGlobalAttachment(...)`, or `AllureApi.AddLink`. |
| D-07 | major | Code | `inhouse-framework-conventions/SKILL.md:126` | `ToHaveURLAsync("**/dashboard")`: the string is an exact match after BaseURL resolution (`matchers.ts:461-462`), so it always fails. | `new Regex("/dashboard$")`, or `WaitForURLAsync("**/dashboard")` followed by an assertion. |
| D-08 | major | Code | `inhouse-framework-conventions/SKILL.md:92-98` | Page-level selector APIs (`Page.FillAsync(sel)`, `Page.ClickAsync(sel)`, `Page.InnerTextAsync(sel)`) are discouraged. `GetErrorMessageAsync` returns a one-shot string, losing web-first retry. The audit's own I3 grep (`conformance-checklist.md:182`) flags `InnerTextAsync()` as major. | `Page.Locator(Selector("key"))` fields; expose an `ILocator ErrorMessage` and assert with `Expect(...).ToHaveTextAsync`. |
| D-09 | major | Code | `ui-test-author/playwright/SKILL.md:254` (`Assert.That(banner.Text, …)`); `:253` (`IsDisplayed(By)`, `NoSuchElementException`) | Selenium API pasted into the Playwright skill: `ILocator` has no `.Text`, and a one-shot read contradicts `:250`. | `await Expect(banner).ToHaveTextAsync("Saved")`. Replace the Selenium probe example with a Playwright one, or drop it. |
| D-10 | major | Code | `responsive-testing/SKILL.md:99-108` | `if (width < Breakpoints.Md) { … } else { … }` drives assertions in the test body. This violates CLAUDE.md "No conditional logic in tests" and the skill's own `:230`. | Parameterize the expected variant: `[TestCase(767, "nav-hamburger", "nav-desktop")]`. |
| D-11 | major | Code / Logical | `lighthouse-ci.md:165-183` | The test owns `Playwright.CreateAsync()`. `--remote-debugging-port=9222` is a fixed, shared port (breaks parallel runs). It uses a hardcoded `http://localhost:5000/dashboard`. Lighthouse opens its tab in the **default** browser context, while `browser.NewPageAsync()` creates a separate incognito-like context, so the "signed-in" state never reaches the audited tab. | Use `LaunchPersistentContextAsync` (what `playwright-lighthouse` does for auth), a per-test free port, and a configured base URL. |
| D-12 | major | Code | `language-testing/references/details.md:18-45` | `I18nTestBase` creates one `IPage` in `[OneTimeSetUp]`, shared by every test in the fixture. That is shared mutable state and order dependence. It hardcodes Chromium and ignores runsettings. | Derive from `PageTest`, set `Locale`/`TimezoneId` in `ContextOptions()`, and use `[TestFixture("de-DE","Europe/Berlin")]` parameterization. |
| D-13 | major | Code | `reporting/.../flaky-test-quarantine/SKILL.md:240-241` | The categories bucket "Known flaky (quarantined)" matches `TimeoutException`, so every real Playwright action timeout is filed as known-flaky. | Match on the quarantine category/label, not exception text. |
| D-14 | major | Logical | `ui-test-author/review/SKILL.md:38,58,104`; `ui-test-author/selenium/SKILL.md:36,171,207,216` (`data-test`) vs `ui-test-author/playwright/SKILL.md:8,227` and `page-objects-from-url/SKILL.md:8,136` (`data-testid`) | Review suggests `GetByTestId("inventory-item")` for a `data-test` attribute. That only works after `SetTestIdAttribute("data-test")`, which no authoring skill teaches. | Standardize on `data-testid` (CLAUDE.md frontend rule). Document `SetTestIdAttribute` / runsettings `TestIdAttribute` for deviations. |

### 3b. Minor code defects

| ID | Sev | Class | Location | Issue | Suggested fix |
|---|---|---|---|---|---|
| D-15 | minor | Code | `ui-test-author/playwright/SKILL.md:218` (`Assert.That(res.Ok, Is.True)`) vs `api-test-author/playwright/SKILL.md:216-217,233` | The UI skill uses the exact pattern the API skill bans. No evidence in the message. No cleanup of `_seededOrderId` (the TS sibling deletes it, `qa/typescript/skills/ui-test-author/playwright/SKILL.md:164`). | Assert `(HttpStatusCode)res.Status` with the body in the message, and delete in `[TearDown]`. |
| D-16 | minor | Code | `ui-test-author/playwright/SKILL.md:253,290`; `ui-test-author/review/SKILL.md:159` | `Assert.Throws<T>` for async code. | `Assert.ThrowsAsync<T>` (CLAUDE.md test rules). |
| D-17 | minor | Code | `ui-test-author/playwright/SKILL.md:189-199` | `AuthSetup` hardcodes `pw.Chromium` (ignores `BrowserName`), creates no context `BaseURL`, and leaks the browser on failure (no `await using`). | `await using var browser`, `BaseURL` from config, and the browser chosen from settings. |
| D-18 | minor | Code | `playwright-routes.md:162-166` | `Assert.That(bodyMatches(…), Is.True, "request payload did not match")`: a boolean that drops the payload. Also an `if` chain inside an assertion helper. | Put `request.PostData` in the failure message, or assert fields individually. |
| D-19 | minor | Code | `responsive-testing/SKILL.md:150` | `Assert.That(separated, Is.True, …)` loses the two boxes. | Include the boxes in the message. |
| D-20 | minor | Code | `production-uptime-checks/SKILL.md:157-190` | Blanket `catch (Exception)` (CLAUDE.md: "never blanket-catches"). No screenshot/trace on a failed synthetic probe. `ct` is never passed on. Relative `GotoAsync` with no `BaseURL`. Nothing about installing browsers on the Functions host. | Capture a trace on failure, attach it to the telemetry/blob, and pass `ct`. Document a container/Premium host plus `playwright.ps1 install --with-deps`. |
| D-21 | minor | Code | `test-login-tokens/references/details.md:165-177` | Hardcoded `https://app.flexinvest.test` (product-specific). Path `.auth/user.json` vs `playwright/.auth/user.json` (`ui-test-author/playwright/SKILL.md:184`). No note that `StorageState` misses `sessionStorage` and in-memory tokens (the Auth0 SPA SDK default), or the `IndexedDB = true` option (1.51). | Use the configured base URL, one path convention, and document storage limits. |
| D-22 | minor | Code | `visual-regression/references/playwright-snapshots.md:64-65` | The comment "How long ToHaveScreenshotAsync auto-retries" sits above a `ContextOptions` override that hardcodes `BaseURL = "http://localhost:3000"`. | Remove the comment. Read the base URL from configuration. |
| D-23 | minor | Data | `lighthouse-ci.md:8-9,19,59` | Lists the `pwa` category, which Lighthouse 12 removed. | Drop `pwa`. |
| D-24 | minor | Data | `ui-project-setup/SKILL.md:125` | `npx playwright show-trace` needs Node. | `pwsh bin/Debug/<tfm>/playwright.ps1 show-trace <zip>`. |
| D-25 | minor | Data | `ui-project-setup/SKILL.md:50` | `Microsoft.Playwright.CLI` is legacy (1.2.3). | Install PowerShell (`dotnet tool install --global PowerShell`), per the docs. |
| D-26 | minor | Data | `page-object-design/SKILL.md:123` | `playwright.config.ts (if used)` in a .NET layout. | Replace with `.runsettings`. |
| D-27 | minor | Code | `page-object-design/SKILL.md:95` | Seeding in `[OneTimeSetUp]` of a `PageTest` base. No `Page` exists there, and per-worker state breaks test independence. | Use API seeding in `[SetUp]`, or a `[SetUpFixture]` that writes data/state files. |
| D-28 | minor | Code | `bdd-project-scaffold/SKILL.md:156-181` | `[AfterScenario]` captures no trace/screenshot on failure. It hardcodes Chromium headless and sets no `BaseURL`. | Start tracing in `[BeforeScenario]`; in `[AfterScenario]`, check `ScenarioContext.TestError` and save/attach. |
| D-29 | minor | Code | `axe-playwright.md:79`; `percy.md:110-119`; `playwright-snapshots.md:110-118` | Expression-bodied `ILocator Form => …` properties contradict `ui-test-author/playwright/SKILL.md:236` and `review/SKILL.md:82`. Note the rule's rationale ("re-query the DOM", `:236`) is factually wrong, since locators are lazy. | Pick one rule and correct the rationale. |
| D-30 | nit | Code | `ui-test-author/playwright/SKILL.md:57-58` | Both `Microsoft.Playwright` and `Microsoft.Playwright.NUnit` are referenced. | Reference `.NUnit` only. |
| D-31 | nit | Code | `test-reports/SKILL.md:129,133` | byte[] `AddAttachment` without `fileExtension`, so downloads lose `.png`/`.zip`. The temp trace file is never deleted. | Pass `".png"` / `".zip"`. |

### 3c. Contradictions between skills, or with CLAUDE.md

| ID | Sev | Class | Location | Issue |
|---|---|---|---|---|
| C-01 | major | Logical | `ui-project-setup/SKILL.md:26` (inline versions under CPM give NU1008) vs inline `Version=` in `ui-test-author/playwright/SKILL.md:57-61`, `bdd-project-scaffold/SKILL.md:67-72`, `axe-playwright.md:29-33`, `lighthouse-ci.md:45-48`, `playwright-snapshots.md:41-44`, `percy.md:48-52`, `applitools.md:43-47`; `mobile-project-setup/SKILL.md:153` and `performance-project-setup/SKILL.md:136` claim `PlaywrightTests` folds into CPM | Following the authoring skill inside the scaffolded solution breaks restore. |
| C-02 | major | Logical | `qa-ui-dotnet.md:35` ("Emit no comments") and CLAUDE.md ("no TODO/FIXME left behind") vs `qa-ui-dotnet.md:44`, `ui-test-author/playwright/SKILL.md:227,232`, `page-objects-from-url/SKILL.md:8,115,138` | Mandated `// TODO` markers (T10). |
| C-03 | major | Logical | `conformance-checklist.md:112` (E11 blocker: `Playwright.CreateAsync()` in a test or `[SetUp]`) vs `browser-cloud-setup/references/details.md:98` (`[SetUp]`), `lighthouse-ci.md:170,283` (inside `[Test]`), `bdd-project-scaffold/SKILL.md:159`, `language-testing/references/details.md:36`, `test-login-tokens/references/details.md:165`, `production-uptime-checks/SKILL.md:160`. Also `ui-test-author/review/SKILL.md:95` (major). | The audit would flag the library's own recipes. |
| C-04 | major | Logical | `qa-ui-dotnet.md:18` (never loads `qa/reporting`) + `:97` (Step 0 gate: "base fixture attaches trace/screenshot on failure") + `ui-project-setup/SKILL.md:131,152` (requires it, no code) + `conformance-checklist.md:239` (L4 major) vs the only recipe at `test-reports/SKILL.md:120-137` | Unreachable requirement (T6). |
| C-05 | major | Logical | `test-reports/SKILL.md:131` (trace goes to `%TEMP%`) vs `azure-pipelines.md:251`, `github-actions.md:268`, `gitlab-ci.md:207` (upload `bin/<cfg>/net10.0/playwright-traces`). `gitlab-ci.md:201,312` say "configure Playwright-for-.NET to keep traces on failure only (trace config)", but no such config exists in .NET; it must be coded. | The CI artifact is always empty. |
| C-06 | major | Logical | `api-test-author/playwright/SKILL.md:187` (no `try/finally`) vs `:223` ("cleanup in `try/finally` or `[TearDown]`") vs CLAUDE.md (teardown hook only) | Self-contradiction. |
| C-07 | major | Logical | `bdd-reviewer/SKILL.md:44-55` vs `ui-test-author/playwright/SKILL.md:252-253,256-259` | The BDD review omits no-OR, no-try/catch, NetworkIdle, Force, deprecated waits and failure evidence. |
| C-08 | major | Data / Logical | `gitlab-ci.md:189` image `v1.47.0-jammy` vs package pins 1.49–1.55 and the `net10.0` build (`:206-207`) | A browser revision mismatch gives "Executable doesn't exist". A 2024 image ships no .NET 10 SDK. |
| C-09 | minor | Logical | Test naming: `ui-test-author/playwright/SKILL.md:145,157,247` (`Signs_In_With_Valid_Credentials`); `api-test-author/playwright/SKILL.md:147,206,249` (`[Action]_[Condition]_[ExpectedOutcome]`) vs CLAUDE.md `Should_X_When_Y` / `Given_When_Then` (followed by `axe-playwright.md:362`, `inhouse-framework-conventions/SKILL.md:142`, `responsive-testing` samples) | Naming conventions disagree. |
| C-10 | minor | Logical | `ui-test-author/playwright/SKILL.md:291-292` (no `GotoAsync` or raw locators in test classes) vs samples in `playwright-routes.md:116-118`, `axe-playwright.md:124-125,178,231`, `responsive-testing/SKILL.md:94-98,163-166`, `realtime-stream-testing/SKILL.md:213,251`, `playwright-snapshots.md:164,172` | Samples break the authoring rules. Axe even violates its own `:68,:359`. |
| C-11 | minor | Logical | `responsive-testing/SKILL.md:65-66,228` (viewport via `ContextOptions`) vs `:94,163` (`SetViewportSizeAsync` in every test) | Self-contradiction. |
| C-12 | minor | Logical | `ui-test-author/playwright/SKILL.md:249` and `ui-test-author/review/SKILL.md:79` ("every test asserts", blocker) vs `percy.md:139-146` (a test whose only call is `Percy.Snapshot`) | Needs an explicit, recorded exception. |
| C-13 | minor | Logical | `gherkin-step-code/SKILL.md:89-90` (`Given` calls `ExpectLoadedAsync`) vs its anti-pattern `:156` ("`When`/`Given` doing assertions") | Self-contradiction. |
| C-14 | minor | Logical | `ui-test-author/review/SKILL.md:44` (hard-rule violations are blockers) vs `:63` (try/catch in a test = major) and `conformance-checklist.md:187` (I8 major) | CLAUDE.md makes "no try/catch in a test body" a hard rule. |
| C-15 | minor | Logical | `qa-api-dotnet.md:75,77` | Authors in `api-test-author/playwright` but reviews with `api-test-author/review` (RestSharp-only, `:3,:8`). It is mitigated by the cross-ref at `api-test-author/playwright/SKILL.md:262`, which the agent does not load. |
| C-16 | minor | Logical | `inhouse-framework-conventions/SKILL.md:69-75` (CSS `[data-testid='…']` strings in JSON) vs the `GetByTestId` policy | This is a documented project override. Make it explicit as a deviation for the audit (`standards-audit/SKILL.md:79`). |

### 3d. Broken cross-references

All path references resolve on disk (verified by script). The broken references are content-level:

| ID | Sev | Location | Issue |
|---|---|---|---|
| X-01 | minor | `playwright-routes.md:27-28,309,376-377`; `proxy.md:29,335-336`; `network-mocking/SKILL.md` siblings | They point to `qa/dotnet/skills/network-mocking` (themselves) for "CDP" and "proxy". This is a pre-merge leftover; they should name `references/cdp.md` / `references/proxy.md`. |
| X-02 | minor | `responsive-testing/SKILL.md:49` | "`Playwright.Devices["iPhone 15"]` profiles in `ui-test-author/playwright`", but that skill has no device coverage. |
| X-03 | minor | `test-login-tokens/SKILL.md:54,107,131` | Sends "seeding auth without the login UI" to `ui-test-author/playwright`, whose `AuthSetup` logs in **through the UI** (`:193-197`). |
| X-04 | minor | `ui-test-author/playwright/SKILL.md:299` | Recommends `[AllureStep]`, but Allure wiring is unreachable to the agent (see C-04). |

### 3e. Anti-pattern sweep

The sweep covered `Thread.Sleep`, `Task.Delay`, `WaitForTimeoutAsync`, `QuerySelectorAsync`, `ElementHandle`, `WaitForSelectorAsync`, `WaitForNavigationAsync`, `TypeAsync`, `IsVisibleAsync`-as-assertion, `NetworkIdle`, `.Result`/`.Wait()` and `try/catch` in a test.

- **Clean in Playwright samples.** Every hit is a "don't" rule, an anti-example, or the sanctioned latency-injection `Task.Delay` in a route handler (`playwright-routes.md:54,299`).
- **Exceptions:**
  - `inhouse-framework-conventions/SKILL.md:98` (`InnerTextAsync` one-shot)
  - `language-testing/references/details.md:139` (`AllInnerTextsAsync` one-shot scan, acceptable for a sweep)
  - `test-login-tokens/references/details.md:222-223` (`try/catch` in an I/O polling helper, acceptable under CLAUDE.md)
- **Review coverage gaps.** Deprecated-API coverage in review/checklist is limited to `WaitForNavigationAsync` (`review/SKILL.md:90`, `conformance-checklist.md:91`). There are no rows for `ElementHandle`/`QuerySelectorAsync`/`TypeAsync`/page-level selector APIs, relative URLs without `BaseURL`, `ToHaveURLAsync` globs, `Playwright.Shard`, or image/package version match.
- **Inline comments inside code samples.** These violate CLAUDE.md (minor; audit row B10 would flag them):
  - `playwright-snapshots.md:58,64,69-71,77,141,147,166-179,247-248,318-319,323`
  - `axe-playwright.md:106,108,112,124-126,185,195,258,260,278`
  - `playwright-routes.md:207,226,250,261-262,303`
  - `responsive-testing/SKILL.md:95,102,119,156,182-183,186`
  - `realtime-stream-testing/SKILL.md:211-236,241,247`
  - `bdd-project-scaffold/SKILL.md:61,73-74,77,116-118,132,136-137`
  - `test-reports/SKILL.md:87` (`// arrange / act / assert`, the banned AAA banner)

### 3f. Incidental findings outside the Playwright scope (verified)

- **blocker · Data:** `security-testing/passive-scan/SKILL.md:13` (and `:18,30,73,94,189,206,305,357`) calls the script `passive-scan.py`. The ZAP image ships `zap-baseline.py`, so every command fails.
- **major · Code:** `reporting/.../test-reports/SKILL.md:110-113` calls `AllureApi.AddAttachment("response.json","application/json", response.Content ?? "")`. The 3-string overload treats the third argument as a **file path** (`AllureApi.cs:469-485`), so the body is never attached. Use `Encoding.UTF8.GetBytes(...)` with `".json"`.

---

## 4. Parity with TypeScript

| Topic | TypeScript | .NET | Verdict |
|---|---|---|---|
| Authoring skill structure | Fixture-driven POM (`qa/typescript/skills/ui-test-author/playwright/SKILL.md:79-99`), `setup` project + `storageState` (`:125-151`), API-seed fixture **with cleanup** (`:153-167`) | Base class + `[SetUp]` (`ui-test-author/playwright/SKILL.md:66-89`); SetUpFixture auth that is namespace-broken (D-02); seed **without cleanup** (`:212-221`) | .NET is behind: no cleanup, and the auth template is broken |
| Trace/video config | Review checks `trace: 'retain-on-failure'` / `video` (`qa/typescript/skills/ui-test-author/review/SKILL.md:99,147`); `bdd-project-scaffold:104` sets `trace` | No trace/video config in authoring or review; only `qa/reporting` (C-04) | .NET is behind. The underlying cause is that .NET has no config file, so the skill must teach the `[SetUp]`/`[TearDown]` code. |
| Lint | `eslint-plugin-playwright` (`:17`) | No analyzer equivalent | Acceptable; no official one exists |
| Retry/poll | `expect.toPass`/`expect.poll` (`:212`) | NUnit `.After().PollEvery()` (`ui-test-author/playwright/SKILL.md:267`) | Parity is fine |
| Steps | `test.step` (`:217`) | `[AllureStep]` only (`:299`); `Tracing.GroupAsync` (1.49) unmentioned | Minor gap |
| UI mode / debug | `--ui` (`:264`) | No codegen, `PWDEBUG`, or `HEADED`/runsettings guidance | Gap |
| Visual regression | `toHaveScreenshot` / `--update-snapshots` / config defaults (`qa/typescript/skills/visual-regression/references/playwright-snapshots.md:20-27,49-52`), all correct for `@playwright/test` | **Ports the TS runner API verbatim into .NET, where it does not exist** (T1/D-03) | **Contradiction.** The .NET file says the only difference is the missing `--update-snapshots` flag (`playwright-snapshots.md:5-7`), but the whole assertion layer is missing. The Java sibling repeats the same error (`qa/java/skills/visual-regression/references/playwright-snapshots.md:25-27`, `assertThat(page).hasScreenshot()`, which Java Playwright also lacks). Worth a cross-lane fix. |
| CI sharding | TS uses native `--shard` + blob/merge-reports (`gitlab-ci.md:17`) | Claims `--shard`/`Playwright.Shard` works for .NET (T2) | .NET contradicts reality. It needs NUnit-side partitioning (category or fixture-hash `--filter`, or a precomputed list). |
| Setup skill | None. TS/Java agents have no Step 0 (`qa/typescript/agents/qa-ui-typescript.md:110-114`, `qa/java/agents/qa-ui-java.md:110-114`) | `ui-project-setup` (+ api/mobile/performance); Step 0 in `qa-ui-dotnet.md:97` | .NET-only, by design for CPM/TestCore |
| Missing everywhere | — | — | FrameLocator, aria snapshots, `Clock`, accessible-name/role assertions and WebMCP are missing in **all three** lanes (§2) |

**What the .NET visual-regression skill teaches instead of a built-in screenshot assertion:** nothing real. It presents the TS `toHaveScreenshot` model as a .NET API. A correct .NET skill would teach one of:
1. `ScreenshotAsync` (`PageScreenshotOptions`/`LocatorScreenshotOptions` with `Mask`, `MaskColor`, `Animations`, `Caret`, `Style`, `Scale`, `FullPage`) plus a comparer (e.g. `Verify.Playwright`, or ImageSharp-based compare), with baselines committed per OS/browser and `AllureApi.AddScreenDiff`
2. hosted Percy (`PercyIO.Playwright`)
3. Applitools (`Eyes.Playwright`)

Its "regenerate by deleting the PNG" workflow (`:241-249`) only makes sense once option 1 is built.

---

## 5. Structural observations

**How `qa-ui-dotnet` loads skills.**
- Bare names resolve to `qa/dotnet/skills/<name>/SKILL.md` and `ep-*` names to `engineering-practices/` (`qa-ui-dotnet.md:18`).
- It reads only the step's skills, and only the matching `references/<tool>.md` (`:20`).
- `ep-agent-orientation-cache` and `ep-code-comments` are always loaded (`:24`).
- **It never loads `qa/manual|reporting|cicd`** (`:18`).
- The steps table (`:95-101`) runs: Step 0 `ui-project-setup` → Step 1 `page-object-design` / `page-objects-from-url` / `test-data-builder` / `test-login-tokens` / `browser-cloud-setup` → Step 2 `ui-test-author/playwright` / `network-mocking` / `data-driven-testing` → Step 3 specialized → Step 4 `ui-test-author/review`. The audit lives in `standards-audit` (`:103`).
- **Consequence:** anything the UI agent must produce, such as failure evidence, has to live in a `qa/dotnet/skills/*` file it loads, not in `qa/reporting`.

**Who should own new topics.**

| Topic | Recommended owner | Why |
|---|---|---|
| **Evidence capture** (screenshot / video / trace / HAR on failure) | `qa/dotnet/skills/ui-test-author/playwright`, as a new `references/evidence-capture.md` loaded from its base-test section | `BaseTest` is authored there. Step 0 (`ui-project-setup`) and Step 4 review should link to it, not re-teach it. `qa-reporting-dotnet` keeps only the Allure-attachment wiring and links back. It should teach: `Context.Tracing.StartAsync(new() { Title, Screenshots, Snapshots, Sources })` in `[SetUp]`; `StopAsync(new() { Path = WorkDirectory/playwright-traces/<test>.zip })` only when `Result.Outcome.Status == Failed`, otherwise `StopAsync()`; `TestContext.AddTestAttachment`; screenshot options; `RecordVideoDir` via `ContextOptions()` plus `Page.Video.SaveAsAsync`/`DeleteAsync` after the context closes (PageTest closes it in base teardown, so override at `ContextTest` level or close explicitly); `GroupAsync`; HAR-on-tracing (1.60). Its paths must equal the CI upload paths (C-05). |
| **Locator scoping / "within"** | `ui-test-author/playwright` (the locator rules at `:225-232`), with the component pattern cross-referenced from `page-object-design:91` | It should teach component classes taking a parent `ILocator`, `Filter(Has/HasText/HasNot/HasNotText/Visible)`, `And`/`Or`, `Describe`, `FrameLocator`/`ContentFrame`, and when `Nth` is acceptable. Add review rows (`ui-test-author/review`) and audit rows to F (`conformance-checklist.md:125-133`). Mirror it in TS/Java. |
| **WebMCP testing** (`navigator.modelContext` tools a page exposes to agents) | A new tool-bound skill `qa/<stack>/skills/webmcp-testing`. TS is canonical; the .NET port drives it through `Page.EvaluateAsync`. Owner agent: `qa-ui-*`, with a cross-ref from `ai-feature-testing` (agent-facing behaviour) and `tooling` (`tool-mcp-builder` builds the server side). | It is a browser surface, so it belongs with the UI lane. Contract assertions (tool names, input schemas, invocation results, permission prompts) resemble `api-contract-testing`. Nothing exists today (0 hits). Verify the current Chromium/W3C status before authoring. |

**Is `ui-project-setup` the setup owner?** Yes:
- `qa-ui-dotnet.md:97` names it.
- The catalog lists it (`docs/skills-catalog.md:50`).
- `bdd-project-scaffold/SKILL.md:12` names it as its analogue.

But it is a shell without the files it promises:
- No `Directory.Packages.props` with the Playwright line; it defers to the API scaffold (`:114`).
- No base fixture code, though it requires one (`:76,131,152`).
- No `.runsettings`.
- No Dockerfile content (`:82`).

**TS and Java have no equivalent:** no `*project-setup` skill and no Step 0 (`ls qa/{typescript,java}/skills`; agents `:110-114`).

**Other structural notes.**
- **Duplicate MCP tool grants.** Agent MCP grants are duplicated verbatim in `qa-ui-dotnet.md:4`, `qa-bdd-dotnet.md:4` and `qa-ui-typescript.md:4`, and none grants hover/keyboard/tabs. Consider a shared list, and document that `--caps=testing,storage` must be set or three granted tools never resolve.
- **Missing review row.** `ui-test-author/review` has no "evidence on failure" row, while the TS review does (`qa/typescript/skills/ui-test-author/review/SKILL.md:99,147`).
- **Router claims.** Three tool-family routers (`network-mocking`, `visual-regression`, `accessibility-testing`) still say ".NET 8", and each claims "a project uses exactly one" tool. That is false for a11y and network, since the a11y router itself says "many teams run both" (`accessibility-testing/SKILL.md:30-32`).

---

## Evidence: the external facts used

| Fact | Source |
|---|---|
| Microsoft.Playwright latest 1.63.0 (2026-09-21) | nuget.org/packages/Microsoft.Playwright; `gh api repos/microsoft/playwright-dotnet/releases` |
| No `ToHaveScreenshotAsync`/`ToMatchSnapshotAsync` in .NET; LocatorAssertions list (`ToContainClassAsync` 1.52, `ToHaveAccessible*` 1.44/1.50, `ToMatchAriaSnapshotAsync` 1.49) | playwright.dev/dotnet/docs/api/class-locatorassertions |
| `ToHaveURLAsync(string)` is exact after BaseURL resolution | `microsoft/playwright` `packages/playwright/src/matchers/matchers.ts:448-467` |
| `IWebSocket` = 4 events + `IsClosed`/`Url`, no wait methods | `playwright-dotnet` `src/Playwright/API/Generated/IWebSocket.cs:40-55` |
| `WebSocketRoute.OnMessage(Action<WebSocketFrame>)` | playwright.dev/dotnet/docs/api/class-websocketroute |
| CDP `OnEvent` is `EventHandler<JsonElement?>` | `src/Playwright/API/Generated/ICDPSessionEvent.cs:42` |
| `Request.PostDataJSON` is a property (the skill is correct) | playwright.dev/dotnet/docs/api/class-request |
| runsettings keys: `BrowserName`, `LaunchOptions`, `ExpectTimeout`, `TestIdAttribute`; anything else prints "not implemented"; `HEADED=1` honoured | `src/Playwright.TestAdapter/PlaywrightSettingsXml.cs` (switch), `PlaywrightSettingsProvider.cs:109` |
| Screenshot options (`Style`, not `StylePath`); context options (`RecordVideoDir`, `ReducedMotion`, `ColorScheme`, …) | `src/Playwright/API/Generated/Options/PageScreenshotOptions.cs`, `BrowserNewContextOptions.cs` |
| Glob `?`/`[]` removed in 1.52; `RouteWebSocket` 1.48; `Clock` 1.45; `GroupAsync` 1.49; `Describe` 1.53; `Filter Visible` 1.51; `IndexedDB` 1.51; `Xunit.v3`/`MSTest.v4` 1.55 | playwright.dev/dotnet/docs/release-notes |
| Docker tags `v1.63.0-{noble,jammy,resolute}` | playwright.dev/dotnet/docs/docker |
| NUnit `ParallelScope.Self` only; MSTest/xUnit/xUnit.v3 packages | playwright.dev/dotnet/docs/test-runners |
| MCP tool names, caps, `target` param, `--test-id-attribute` | github.com/microsoft/playwright-mcp README |
| `AllureApi` has `AddAttachment`/`AddGlobalAttachment`/`AddScreenDiff`, no `AddTestAttachment`; 3-string overload = file path | `allure-csharp` `src/Allure.Net.Commons/AllureApi.cs:469-535` |
| NuGet: `Applitools.Playwright` not found, `Eyes.Playwright` 1.37.49, `Deque.AxeCore.Playwright` 4.13.0, `Allure.NUnit` 2.15.0, `Azure.Developer.Playwright.NUnit` 1.0.0, `Microsoft.Playwright.CLI` 1.2.3 | api.nuget.org v3-flatcontainer |
