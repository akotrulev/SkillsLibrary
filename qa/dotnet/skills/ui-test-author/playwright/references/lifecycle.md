# Lifecycle — Microsoft.Playwright.NUnit 1.63

`assets/BaseTest.cs` is the one Playwright lifecycle in the .NET lane. Every .NET skill that drives a
browser — visual regression, accessibility, network mocking, responsive, language, BDD — derives from it
and amends it by overriding `ContextOptions()`; none calls `Playwright.CreateAsync()` in a test or a
`[SetUp]`. This file explains why it is shaped the way it is and how to run it. Every type and member
below was checked against the `microsoft/playwright-dotnet` v1.63.0 sources.

## 1. The base classes

`Microsoft.Playwright.NUnit` ships four, each deriving from the one above it in this table:

| Class | Each test gets | Use for |
|---|---|---|
| `PlaywrightTest` | `Playwright`, `BrowserType`, `BrowserName`, and the `Expect(...)` overloads | A suite that launches and closes browsers itself. Rare |
| `BrowserTest` | `Browser` (shared by the tests on one worker) and `NewContext(options)`; the test closes what it opens | Several contexts in one test — two users chatting |
| `ContextTest` | `Context`, built from `ContextOptions()` | Several pages or tabs in one test |
| `PageTest` | `Page`, a new page in that context | Everything else. `BaseTest` derives from it |

The same base classes exist for MSTest (`Microsoft.Playwright.MSTest`, `.MSTest.v4`) and xUnit
(`Microsoft.Playwright.Xunit`, `.Xunit.v3`), all at 1.63.0. This library covers **NUnit** only; a project on
another runner keeps it, and these skills do not translate.

Reference `Microsoft.Playwright.NUnit` only. It pulls in `Microsoft.Playwright`,
`Microsoft.Playwright.TestAdapter`, NUnit and the adapter at their floors; the project's own references
raise NUnit to 4.x.

## 2. What runs when

NUnit runs `[SetUp]` methods from the base class down and `[TearDown]` methods from the derived class up.

| Order | `[SetUp]` | Does |
|---|---|---|
| 1 | `WorkerAwareTest.WorkerSetup` | Takes a worker from the pool; applies `ExpectTimeout` from the runsettings |
| 2 | `PlaywrightTest.PlaywrightSetup` | The process-wide `Playwright`; `BrowserName`; `Selectors.SetTestIdAttribute(TestIdAttribute)` |
| 3 | `BrowserTest.BrowserSetup` | The worker's browser, launched once with the runsettings `LaunchOptions` and reused |
| 4 | `ContextTest.ContextSetup` | `Context = NewContext(ContextOptions())` |
| 5 | `PageTest.PageSetup` | `Page = Context.NewPageAsync()` |
| 6 | `BaseTest.StartTracing` | Tracing with screenshots, DOM snapshots and sources |
| 7 | the test class's `[SetUp]` | Builds page objects, seeds records — it sees an open, traced page |

| Order | `[TearDown]` | Does |
|---|---|---|
| 1 | the test class's `[TearDown]` | Deletes what it seeded — the context is still open |
| 2 | `BaseTest.KeepEvidenceOnFailure` | Evidence, then `Context.CloseAsync()`, then the video (§6) |
| 3 | `BrowserTest.BrowserTearDown` | Closes the test's contexts **only if the test passed** |
| 4 | `WorkerAwareTest.WorkerTeardown` | Passed: returns the worker, browser included, to the pool. Failed: disposes the browser |

- A class level's `[TearDown]` runs only if that level's `[SetUp]` started, and one level's teardown
  exception does not stop the levels above it.
- Each level has one `[SetUp]` and one `[TearDown]`. Two in one class run in no defined order.
- Page objects are built in the test class's `[SetUp]`, never as properties of `BaseTest`; a base class
  that knows every page grows without bound.

## 3. Parallelism: `ParallelScope.Self` is the only supported scope

`BaseTest` carries `[Parallelizable(ParallelScope.Self)]`, which NUnit applies to every derived fixture:
fixtures run in parallel, the tests inside one fixture run one after another.

- **Never `ParallelScope.All`, `Children` or `Fixtures` on a Playwright fixture.** NUnit runs every test
  of a fixture on **one instance**, and `PageTest` keeps `Page` and `Context` in instance properties, so two
  tests of one fixture running at once overwrite each other's page. Playwright's docs: "Only
  `ParallelScope.Self` is supported."
- Worker count is NUnit's: `dotnet test -- NUnit.NumberOfTestWorkers=4`. Each worker holds one browser
  process; size it to the agent's memory.
- A slow fixture is one worker for its whole length. Split a large fixture by feature.

## 4. `ContextOptions()` and launch options

**Every override of `ContextOptions()` starts from `base.ContextOptions()` and amends it:**

```csharp
public override BrowserNewContextOptions ContextOptions()
{
    var options = base.ContextOptions();
    options.StorageStatePath = AuthSetup.UserState;
    return options;
}
```

`ContextTest.ContextOptions()` returns `Locale = "en-US"` and `ColorScheme = Light`; `BaseTest` adds
`BaseURL` from `BASE_URL` and the raw-video folder. An override that returns `new()` drops all of it:
`GotoAsync("/login")` then throws "Cannot navigate to invalid URL", and `BaseTest`'s teardown fails with
"No video recorded". Device and media emulation are amendments too (`emulation-and-mobile-web.md`).

**Launch options come from the runsettings, not from code.** `BrowserTest` registers the browser as a
per-worker service under one name: the first fixture on a worker launches it, and every later fixture on
that worker reuses it, whatever its own `LaunchOptionsAsync()` override returns. So a suite that needs
different launch arguments (a feature flag, a proxy) gets its **own `.runsettings` file and its own
`dotnet test` run**; `LaunchOptions` accepts `Args` as a JSON array, `<Args>['--flag']</Args>`.

## 5. Environment and runsettings

| Variable | Read by | Effect |
|---|---|---|
| `BASE_URL` | `BaseTest.ContextOptions()`, `AuthSetup` | `BaseURL`, so `GotoAsync("/login")` and `Page.APIRequest.PostAsync("/api/…")` resolve. Missing → `InvalidOperationException` naming it |
| `HEADED` | the Playwright adapter | `1` runs headed, overriding the runsettings `Headless` |
| `BROWSER` | the Playwright adapter | `chromium`, `firefox` or `webkit`; overrides `BrowserName` |
| `E2E_USER`, `E2E_PASSWORD` | `LoginTests`, `AuthSetup` | The test account |
| `PWDEBUG` | Playwright | `1` opens the Inspector, headed, with no timeouts |
| `DEBUG` | Playwright | `pw:api` logs every Playwright call to stderr |

`BaseTest.RequiredEnv(name)` is the one way to read a required variable.

**`assets/ui.runsettings`** is found by `dotnet test` through `<RunSettingsFilePath>` in `UiTests.csproj`.
The adapter (`Microsoft.Playwright.TestAdapter`, `PlaywrightSettingsXml.cs`) reads exactly four keys under
`<Playwright>`; any other key prints "Playwright>X is not implemented" and is ignored:

| Key | Holds |
|---|---|
| `BrowserName` | `chromium` (default), `firefox` or `webkit` |
| `LaunchOptions` | Any `BrowserTypeLaunchOptions` property as a child element: `Headless`, `Channel`, `Args`, `SlowMo`. **`Headless` belongs here** — a top-level `<Headless>` is one of the ignored keys |
| `ExpectTimeout` | The default web-first assertion timeout in milliseconds, for the whole process |
| `TestIdAttribute` | The attribute `GetByTestId` reads. `PlaywrightSetup` sets it before every test, so a `Playwright.Selectors.SetTestIdAttribute` call in code is overwritten |

Override any of them for one run after `--`: `dotnet test -- Playwright.BrowserName=firefox
Playwright.LaunchOptions.Headless=false`. There is no shard key: `Playwright.Shard` is one of the ignored
keys, so CI splits work with NUnit filters (`qa/cicd/dotnet/skills/ci-pipelines`).

## 6. Failure evidence and the teardown order

| Evidence | Kept when | Path |
|---|---|---|
| Trace (screenshots, DOM snapshots, sources) | the test failed | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.zip` |
| Full-page screenshot | the test failed | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.png` |
| Video | the test failed | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.webm` |

`WorkDirectory` is NUnit's `TestContext.CurrentContext.WorkDirectory`, the test assembly's folder
(`bin/<cfg>/net10.0`) unless the runsettings `NUnit.WorkDirectory` moves it. The test name has every
character outside `A–Z a–z 0–9 . _ -` replaced, so `[TestCase]` rows keep separate files and CI uploaders
accept them. "Failed" is `ResultState.Status == TestStatus.Failed`, which includes errors and a failed
`[SetUp]`. Each kept file is attached twice: `TestContext.AddTestAttachment` (the TRX and the IDE) and
`AllureApi.AddAttachment(name, type, path)`; the trace's type is `application/vnd.allure.playwright-trace`.
A passing test keeps nothing: `StopAsync()` with no path discards the trace, and `DeleteAsync()` removes
the raw recording from `<WorkDirectory>/playwright-videos/`.

**The order inside `KeepEvidenceOnFailure` is fixed:**

1. Read `Page.Video` and keep the reference.
2. On failure, `Tracing.StopAsync(new() { Path })` — it needs the open context.
3. On failure, `Page.ScreenshotAsync(new() { Path, FullPage = true })` — it needs the live page.
4. `Context.CloseAsync()`. The video file is complete only after the context closes, and **the derived
   teardown must close it itself**: `BrowserTearDown` closes contexts only after a pass, and after a
   failure `WorkerTeardown` disposes the whole browser, so nothing else finalizes the video
   deterministically. `CloseAsync` is idempotent, so the later close after a pass is harmless.
5. On failure, `video.SaveAsAsync(path)`.
6. `video.DeleteAsync()` always.

- The video API is **`PathAsync()`**, `SaveAsAsync(path)` and `DeleteAsync()`. playwright.dev's C# sample
  shows `Page.Video.GetPathAsync()`; that is a doc bug, and it does not compile.
- **There is no catch in `BaseTest`.** A screenshot of a crashed page throws; NUnit records it as a
  teardown error on that test, still runs `BrowserTearDown` and `WorkerTeardown`, and the next test gets a
  fresh browser. The trace is already saved by then (step 2 comes first for that reason); only the video
  of that test is lost.
- Screencasts, HAR, aria snapshots in traces and deliberate recordings belong to
  `qa/dotnet/skills/evidence-capture`, which builds on these defaults rather than adding a second hook. A
  recording names and attaches its file with `BaseTest`'s protected `EvidenceName()`, `Artifact(name, ext)` and
  `Attach(name, type, path)`.

## 7. Signed-in state: `AuthSetup`

`assets/AuthSetup.cs` signs in once per run and saves the storage state to
`<WorkDirectory>/auth-user.json`. A signed-in fixture points at it in its `ContextOptions()` (§4).

- **NUnit scopes a `[SetUpFixture]` to its own namespace.** `AuthSetup` sits in the root test namespace
  (`Example.UiTests`), so it runs before every fixture in `Example.UiTests.*`. Put it in
  `Example.UiTests.Support` and the fixtures in `Example.UiTests.Tests` never trigger it: the state file is
  never written and every signed-in test fails.
- It honours the runsettings browser: `playwright[PlaywrightSettingsProvider.BrowserName]
  .LaunchAsync(PlaywrightSettingsProvider.LaunchOptions)`, the same values `PageTest` uses.
- `await using var browser` closes the browser even when sign-in fails; `using var playwright` disposes the
  driver after it.
- The assertion before `StorageStateAsync` waits for the sign-in to finish; saving straight after the
  click saves a signed-out state. `StorageStateAsync` does not create folders, which is why the file sits
  directly in `WorkDirectory`.
- A second role is a second file written by the same method and chosen in that fixture's
  `ContextOptions()`. A project with no signed-in fixture deletes `AuthSetup.cs`: it needs a reachable app
  and real credentials before any test in the namespace runs.
- This `[OneTimeSetUp]` is the one place outside the base classes that calls `Playwright.CreateAsync()`.

## 8. API-seeded data

A record a test needs is created through the API in the test class's own `[SetUp]` and deleted in its
`[TearDown]`, which run inside the `BaseTest` hooks (§2). `Page.APIRequest` shares the context's
`BaseURL` and cookies.

```csharp
private string _orderLocation = null!;

[SetUp]
public async Task SeedOrder()
{
    var created = await Page.APIRequest.PostAsync("/api/orders",
        new() { DataObject = new { Sku = $"SKU-{Guid.NewGuid()}", Qty = 1 } });
    Assert.That(created.Status, Is.EqualTo(201), await created.TextAsync());
    _orderLocation = created.Headers["location"];
}

[TearDown]
public async Task DeleteOrder()
{
    var deleted = await Page.APIRequest.DeleteAsync(_orderLocation);
    Assert.That(deleted.Status, Is.EqualTo(204), await deleted.TextAsync());
}
```

The status is asserted exactly, with the body as the message. Never `Assert.That(res.Ok, Is.True)` or
`Expect(response).ToBeOKAsync()` — both accept any 2xx and print nothing useful. Never seed in
`[OneTimeSetUp]`: no `Page` exists there, and a record shared by a fixture's tests couples them.

## 9. Commands

`playwright.ps1` appears under the project's `bin/` after the first build; the path carries the TFM.

| Task | Command |
|---|---|
| Install the browser on CI | `pwsh bin/Debug/net10.0/playwright.ps1 install --with-deps chromium` (`--with-deps` installs OS packages, so it needs root or sudo on Linux) |
| Install locally | `pwsh bin/Debug/net10.0/playwright.ps1 install chromium` |
| No `pwsh` on the machine | `dotnet tool install --global PowerShell`, then the commands above |
| Run headed | `HEADED=1 dotnet test`, or `dotnet test -- Playwright.LaunchOptions.Headless=false` |
| Debug with the Inspector | `PWDEBUG=1 dotnet test` — headed, no timeouts, step through each call |
| Another browser | `BROWSER=firefox dotnet test`, or `dotnet test -- Playwright.BrowserName=firefox` |
| Record a flow | `pwsh bin/Debug/net10.0/playwright.ps1 codegen --target csharp-nunit --test-id-attribute data-testid -o Recorded.cs https://app.example.test/login` |
| Open a trace | `pwsh bin/Debug/net10.0/playwright.ps1 show-trace bin/Debug/net10.0/playwright-artifacts/LoginTests.Should_GreetUser_When_CredentialsAreValid.zip` |

- **Browsers are pinned per Playwright version.** In a container, use
  `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` (.NET SDK 10, browsers preinstalled); its tag
  always equals the package version, and there is no `-jammy` .NET image since 1.60.
- **Codegen output is a draft.** `--target csharp-nunit` writes a `PageTest` class; move its locators into
  page objects on the ladder, rename the test `Should_X_When_Y`, derive it from `BaseTest`, and never
  commit the recording. The recorder's **Assert snapshot** button emits `ToMatchAriaSnapshotAsync`.
- **Traces also open at trace.playwright.dev**, which loads the zip in the browser without uploading it.
  `npx playwright show-trace` needs Node. The trace analysis CLI an agent reads a failure with runs through
  Node or `playwright.ps1`: `qa/dotnet/skills/evidence-capture`, "Reading a failure".
