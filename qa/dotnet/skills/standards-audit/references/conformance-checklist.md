# qa-dotnet Conformance Checklist — the 14 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`D1`, `F3`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number.

**Every row is about TEST CODE.** If a row tempts you toward the application under test, stop — that belongs to `be-dotnet-standards-audit` / the `fe-*` audits (see the skill's scope fence).

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — `bin/`, `obj/`, `TestResults/` are skipped without flags. Without ripgrep, `grep -rn --include='*.cs' --exclude-dir=bin --exclude-dir=obj` is equivalent. Scope to the test projects:

```bash
TESTS=$(ls -d **/*Tests **/*.Tests 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" --glob '*.cs' $TESTS
```

**The tool lane gates everything.** Rows tagged **[NUnit]**, **[PW]** (Playwright .NET), **[Sel]** (Selenium 4), **[Appium]**, **[RestSharp]**, **[Reqnroll]**, **[TC]** (Testcontainers) apply only when that tool is in use. A suite that doesn't use a tool is **N/A** for its rows, never in violation. Where the project has a documented house convention that differs from a plugin default, record a **deviation**, not a finding.

**Owning skills:** `qa/dotnet/skills/{api-test-author/*,ui-test-author/*,evidence-capture,visual-regression,accessibility-testing,network-mocking,page-object-design,page-objects-from-url,mobile-screen-explorer,mobile-screen-objects,api-client-writer,api-models,test-data-builder,data-driven-testing,db-testing/*,test-login-tokens,test-quality-check,load-testing,bdd-*}` · `qa/reporting/dotnet/skills/{test-reports,flaky-test-quarantine}` · `qa/cicd/{ci-conventions,dotnet/skills/ci-pipelines}` · `qa/_shared/performance` · `qa/manual/{test-strategy,quality-metrics}`.

---

## A — Build health & suite lane
*Owning skills: `api-project-setup`, `ui-project-setup`, `mobile-project-setup`, `performance-project-setup`, `ui-test-author/playwright` (A9, A10)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The suite compiles and runs | Red on arrival; a project excluded from the solution to keep CI green | Opt-in run only (`dotnet build`); otherwise CI history. Report as arrival state | major |
| A2 | One runner across the suite | NUnit and xUnit both present, writing into the same results directory | `rg -n "NUnit\|xunit\|MSTest" --glob '*Tests.csproj'` | major |
| A3 | One assertion library, per the project's stated convention | `Assert.That` and `.Should()` (FluentAssertions) mixed in the same project — two idioms, two failure-message styles | `rg -c "Assert\.That\|\.Should\(\)" --glob '*.cs'` | major |
| A4 | One JSON stack | `System.Text.Json` and `Newtonsoft.Json` both used for deserialization | `rg -n "JsonConvert\|JsonSerializer\." --glob '*.cs'` | major |
| A5 | No disabled tests without a ticketed reason | `[Ignore]` / `[Explicit]` with no issue link or date | `rg -n "\[Ignore\(\|\[Explicit\(" --glob '*.cs'` | major |
| A6 | `Nullable` enabled in test projects too | `<Nullable>` missing, so `!`-bangs and null surprises spread through fixtures | `rg -n "<Nullable>" --glob '*Tests.csproj' --glob '*.props'` | minor |
| A7 | Shared infrastructure lives in one place | Every test project re-implementing its own base fixture / driver factory / config reader | `rg -l "class Base\w*Test" --glob '*.cs'` | minor |
| A8 | Tooling versions pinned | Floating package versions or `latest` container tags in fixtures | `rg -o "Version=\"[^\"]+\"" --glob '*Tests.csproj' \| sort -u`; `rg -n ":latest" --glob '*.cs'` | minor |
| A9 | **[PW]** Only APIs that exist in the pinned binding (1.63) | `ToHaveScreenshotAsync` / `ToMatchSnapshotAsync` (no .NET screenshot assertion exists); `Page.Video.GetPathAsync()` (the API is `PathAsync()`); `Within(`, `GetByRef`, `RecordVideoFps` (1.64-only); `new AxeBuilder(` (`Deque.AxeCore.Playwright` 4.13.0 has `page.RunAxe(...)` / `locator.RunAxe(...)`); `AllureApi.AddTestAttachment` (does not exist); Eyes `OpenAsync` / `CheckAsync` / an awaited `CloseAsync()` (`Eyes.Playwright` is synchronous); `request.PostDataJSON` without `()` (a method); `ws.WaitForEventAsync(...)` or `IsClosed()` on `IWebSocket` (events, plus the `IsClosed` and `Url` properties) | `rg -n "ToHaveScreenshotAsync\|ToMatchSnapshotAsync\|GetPathAsync\|AxeBuilder\|AddTestAttachment\|[Ee]yes\w*\.(Open\|Check)Async\|PostDataJSON[^(]\|WaitForEventAsync\|IsClosed\(" --glob '*.cs'` | blocker |
| A10 | **[PW]** One Playwright version across packages and images | The `mcr.microsoft.com/playwright/dotnet:v<x>-noble` tag in a Dockerfile or pipeline ≠ the `Microsoft.Playwright.NUnit` version (the image's browsers are built for its own version); a floating `Microsoft.Playwright*` version (`1.*`); `Microsoft.Playwright` and `Microsoft.Playwright.NUnit` both referenced by one project; a `-jammy` .NET image (none since 1.60) | `rg -n "playwright/dotnet:v" .`; `rg -n "Microsoft\.Playwright" --glob '*.props' --glob '*.csproj'` — compare the two | major |

---

## B — Test naming, structure & comments
*Owning skills: global Test-code + Comments rules (`CLAUDE.md`), `api-test-author/review`, `ui-test-author/review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | Names describe behaviour | `Test1`, `TestGet`, `LoginTest`, `It_Works` | `rg -n "public (async )?(Task\|void) (Test\d\|Test[A-Z]\w*\(\|\w*Test\(\)" --glob '*.cs'` | minor |
| B2 | Naming follows `Should_X_When_Y` / `Given_Y_When_X_Then_Z` | Free-form sentences with no consistent shape across the suite | `rg -o "public (async )?(Task\|void) \w+" --glob '*.cs' \| sort -u \| head -40` | nit |
| B3 | One logical behaviour per test | One `[Test]` asserting the 200 path **and** the 404 **and** the 401; login + cart + checkout in one test | `rg -c "Assert\.That\|Expect\(" --glob '*.cs' \| sort -t: -k2 -rn \| head` then read the heaviest | major |
| B4 | **No conditional logic driving assertions** | `if (x) Assert.That(...)`; a `foreach` looping cases inside one `[Test]` (hides which case failed) | `rg -n "^\s*(if\|foreach\|for) " -A6 --glob '*.cs' \| rg "Assert\.\|Expect\("` | major |
| B5 | Parameterization via `[TestCase]` / `[TestCaseSource]` **[NUnit]** | Copy-pasted near-identical tests, or loop-driven multi-case tests | `rg -c "\[TestCase" --glob '*.cs'` vs duplicated test bodies | major |
| B6 | Arrange-Act-Assert is legible | 80-line test bodies with setup, action, and assertions interleaved | `rg -n "public (async )?Task \w+" -A60 --glob '*.cs'` — scan the longest | minor |
| B7 | No `async void` test or helper | `public async void ...` — exceptions escape and can crash the runner | `rg -n "async void" --glob '*.cs'` | blocker |
| B8 | Tests live in the layer they belong to | Integration concerns inside a "unit" project; UI assertions inside the API project | Read the project layout vs test contents | minor |
| B9 | No commented-out tests shipped | Large commented `[Test]` blocks left in place of deletion or `[Ignore]` with a ticket | `rg -n "^\s*//\s*\[Test" --glob '*.cs'` | nit |
| B10 | No inline comments in test bodies, page objects, or step definitions | `// Arrange` / `// Act` / `// Assert` banners; `// log in`; `// wait for the grid` inside a page-object method; a line restating the call below; a leftover `TODO`/`FIXME` with no ticket | `rg -n "^\s+//" --glob '*.cs'` then read the hits inside a body — a hit is never a finding | minor |
| B11 | XML doc only where the name genuinely cannot carry the meaning | `/// <summary>Tests the get endpoint.</summary>` above `Should_Return_200_When_…`; `///` on every locator field or builder property | `rg -n -B1 "^\s*/// <summary>" --glob '*.cs'` — check what each sits above | minor |
| B12 | Surviving comments are true and load-bearing | A comment describing an assertion or a flow the test no longer performs | Read the code around every comment B10/B11 surfaced; grep cannot decide this one | major |

**B10–B12 are the audit face of [`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** — read it for the rule, the exactly-three-permitted-comments list for test code, the AAA-banner rule, and the family-vs-per-finding reporting split (B10 is one family with a count and 3–5 cited sites; each **B12** stale comment is its own finding). Three local notes: **B9 already owns commented-out tests**, a skip carrying no reason stays **A5**, and **a comment explaining a locator is an F-section finding** — `// the third span is the price` means the locator is positional, so fix the locator and cross-reference rather than filing it here.

---

## C — Independence & isolation
*Owning skills: global Test-code rules, `api-test-author/review`, `ui-test-author/review`, `db-testing/testcontainers`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | Any test runs alone, in any order | `[Order(...)]` chaining tests into a flow; Test B reading a row Test A created | `rg -n "\[Order\(" --glob '*.cs'` | blocker |
| C2 | No shared mutable state between tests | `static` fields holding ids/entities mutated by tests; a `[OneTimeSetUp]`-created record that tests modify | `rg -n "static (?!readonly\|const)\w" --glob '*.cs'` | blocker |
| C3 | No shared static driver / client | `public static IWebDriver Driver` — breaks parallel execution | `rg -n "static (IWebDriver\|IPage\|IBrowser\|AppiumDriver)" --glob '*.cs'` | blocker |
| C4 | App/DB state reset between tests | No Respawn/reset in `[SetUp]`; **[Appium]** app state shared between tests — a driver reused across tests with no `mobile: clearApp` or `TerminateApp` + `ActivateApp` between them, or the removed `ResetApp()` / `CloseApp()` | `rg -n "Respawn\|ResetApp\|CloseApp\|noReset\|clearApp" --glob '*.cs'` | blocker |
| C5 | Tests create the data they depend on | "Order 42 exists in staging" tests that die on the next reseed | `rg -n "= \d{2,}\b.*Id\|\"TC-\|Guid.Parse\(\"" --glob '*.cs'` | major |
| C6 | Cleanup is deterministic and can't mask failures | Bare cleanup in `finally` that throws and replaces the real assertion error | `rg -n "finally" -A6 --glob '*.cs'` | major |
| C7 | Parallelism settings match the fixtures **[NUnit]** | `[Parallelizable]` + `LevelOfParallelism > 1` on fixtures that own a container or share a driver | `rg -n "Parallelizable\|LevelOfParallelism" --glob '*.cs'` | major |
| C8 | Resources the test created are cleaned up | Records/files/queues left behind when a test fails mid-way | Read the write-path tests | major |
| C9 | No cross-test dependency through the report | A test asserting on another test's Allure output or a shared results file | `rg -n "allure-results\|TestContext.CurrentContext" --glob '*.cs'` | minor |

---

## D — Waits & timing
*Owning skills: `ui-test-author/{playwright,selenium,appium}`, `db-testing/connection`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | **No `Thread.Sleep`** | Any literal sleep, any duration, anywhere in the suite | `rg -n "Thread\.Sleep" --glob '*.cs'` | blocker |
| D2 | **No `Task.Delay` as a wait** | `await Task.Delay(2000)` waiting on DOM/DB/queue state (the server-dictated device-code poll interval is the one sanctioned exception) | `rg -n "Task\.Delay" --glob '*.cs'` | blocker |
| D3 | **[PW]** No `WaitForTimeoutAsync` | `page.WaitForTimeoutAsync(...)` standing in for a condition | `rg -n "WaitForTimeoutAsync" --glob '*.cs'` | blocker |
| D4 | **[Sel]** Explicit `WebDriverWait` + conditions, never implicit-wait soup | `ImplicitWait` set **and** `WebDriverWait` used — the two compound unpredictably | `rg -n "ImplicitWait\|WebDriverWait" --glob '*.cs'` | major |
| D5 | **[PW]** No `NetworkIdle` as a synchronization strategy | `GotoAsync(url, new() { WaitUntil = WaitUntilState.NetworkIdle })` | `rg -n "NetworkIdle" --glob '*.cs'` | major |
| D6 | **[PW]** No `Force = true` bypassing actionability | `ClickAsync(new() { Force = true })` / same on `FillAsync`/`CheckAsync` | `rg -n "Force = true" --glob '*.cs'` | major |
| D7 | No hand-rolled retry loops | `while (retries-- > 0) { … Task.Delay … }` instead of raising the assertion timeout | `rg -n "while \(retries\|for \(int (i\|attempt)" -A6 --glob '*.cs'` | major |
| D8 | Async waits for eventual consistency poll a predicate | A fixed sleep between a write and a DB/queue read instead of polling a probe | `rg -n "Task\.Delay" -B6 --glob '*.cs'` — check what follows | major |
| D9 | **[PW]** Response waits wrap the trigger | `WaitForResponseAsync` placed before/after the action instead of `RunAndWaitForResponseAsync` (race) | `rg -n "WaitForResponseAsync\|RunAndWaitForResponseAsync" --glob '*.cs'` | major |
| D10 | No deprecated navigation waits **[PW]** | `page.WaitForNavigationAsync(...)` still in the code | `rg -n "WaitForNavigationAsync" --glob '*.cs'` | major |
| D11 | No sync-over-async | `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` — deadlocks under NUnit + Playwright | `rg -n "\.Result\b\|\.Wait\(\)\|GetAwaiter\(\)\.GetResult\(\)" --glob '*.cs'` | blocker |
| D12 | **[Appium]** No sleep between gestures | `Thread.Sleep(1500)` or `Task.Delay` after a swipe waiting for animation, instead of a `WebDriverWait` on the next screen | covered by D1; read gesture helpers | blocker |

---

## E — Page / screen objects
*Owning skills: `page-object-design`, `ui-test-author/{playwright,selenium,appium}`, `mobile-screen-objects`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | Page objects expose **intent**, not selectors | Methods named `ClickButton3`, or tests reaching `page.Locator(...)` directly | `rg -n "\.Locator\(\|FindElement\(" --glob '*Test*.cs'` — driver calls in test files | major |
| E2 | **No assertions inside page objects** | `Assert.*` / `Expect(...)` inside a page action method | `rg -n "Assert\.\|Expect\(" --glob '*Page*.cs' --glob '*Screen*.cs'` | major |
| E3 | No business logic in page objects | Price math, JSON parsing, or branching on app state inside the POM | Read the largest page objects | major |
| E4 | Waits and mechanics live in the POM, not the test | `WebDriverWait`/`WaitForAsync` written inline in tests | `rg -n "WebDriverWait\|WaitForAsync" --glob '*Test*.cs'` | major |
| E5 | No god page | A 300+ line page object holding every selector in the app | `find . -name '*Page*.cs' -not -path '*/obj/*' -exec wc -l {} + \| sort -rn \| head` | major |
| E6 | Composition over inheritance for reuse | Deep page-object inheritance chains; a test class extending a page object | `rg -n "class \w+Page ?: ?\w+Page\|class \w+Test ?: ?\w+Page" --glob '*.cs'` | major |
| E7 | A landmark load assertion exists | No `ExpectLoadedAsync()` / `VerifyPageLoaded()`, so tests act on a half-rendered page | `rg -n "ExpectLoadedAsync\|VerifyPageLoaded" --glob '*.cs'` vs page count | major |
| E8 | Navigation methods return the destination page | Navigation returns `void` and the test news up the next page itself | `rg -n "public (async )?(Task\|void) (GoTo\|Navigate\|Open)\w*" --glob '*.cs'` | minor |
| E9 | Repeating rows/cards are scoped components | One page object re-querying the whole DOM per row instead of a component scoped to a parent locator | Read list/table page objects | major |
| E10 | Locators are fields, not re-created per access | Properties calling `Page.Locator(...)` on every get; locator strings re-typed across methods | `rg -n "=> (Page\|_page)\.Locator\(" --glob '*.cs'` | minor |
| E11 | Driver/browser lifecycle owned by one base fixture | **[Sel]** `new ChromeDriver()` in a test or `[SetUp]`. **[PW]** `Playwright.CreateAsync()` in a `[Test]`, a `[SetUp]` or a fixture's `[OneTimeSetUp]` — the root-namespace `AuthSetup` `[SetUpFixture]` is the one exception; a UI fixture not derived from the one `BaseTest : PageTest` (`ui-test-author/playwright/assets/BaseTest.cs`); a second base class per role, device or locale (those are `ContextOptions()` overrides) | `rg -n "new ChromeDriver\(\|Playwright\.CreateAsync\(" --glob '*.cs'`; `rg -n "class \w+ ?(\(.*\))? ?: ?(PageTest\|ContextTest\|BrowserTest\|PlaywrightTest)\b" --glob '*.cs'` — every hit but `BaseTest` itself needs a reason | blocker |
| E12 | Constructor injection — no ambient statics | `Driver.Current` / service-locator lookups inside pages | `rg -n "Driver\.Current\|ServiceProvider\.GetRequiredService" --glob '*.cs'` | major |
| E13 | **[Sel]** No deprecated `PageFactory` / `[FindsBy]` | `PageFactory.InitElements(driver, this)` | `rg -n "PageFactory\|FindsBy" --glob '*.cs'` | major |
| E14 | **[Appium]** Platform branching abstracted | `if (Platform == "iOS") … else …` scattered across screens; a second platform-selection mechanism beside the `PLATFORM` variable (per-platform `appsettings` files, a `--filter "Platform=…"`) | `rg -n "\"iOS\"\|\"android\"\|PLATFORM" --glob '*.cs'` | major |
| E15 | **[Reqnroll]** Steps delegate to page objects | Selectors, waits, or driver calls inside step definitions | `rg -n "\.Locator\(\|FindElement\(\|WaitFor" --glob '*Steps.cs'` | major |
| E16 | **[PW]** `ContextOptions()` amends the base; parallelism is `ParallelScope.Self` | An override returning `new()` / `new BrowserNewContextOptions { … }` (drops `BaseURL`, the video folder, `Locale` and `ColorScheme`); `ParallelScope.All` / `Children` / `Fixtures` on a Playwright fixture (its tests share one `Page`); launch arguments in a `LaunchOptionsAsync()` override instead of a `.runsettings` (the browser is per worker — the first fixture wins) | `rg -n "ContextOptions\(\)" -A3 --glob '*.cs' \| rg "return new"`; `rg -n "ParallelScope\.(All\|Children\|Fixtures)" --glob '*.cs'`; `rg -n "LaunchOptionsAsync" --glob '*.cs'` | blocker |
| E17 | **[PW]** Signed-in state from the root-namespace `AuthSetup` | `AuthSetup` (`[SetUpFixture]`) in a sub-namespace such as `X.Support` while the tests live in `X.Tests` — NUnit runs it only for its own namespace, so the state file is never written; every test signing in through the UI; a state path relative to the current directory instead of `<WorkDirectory>/auth-user.json` | `rg -n "\[SetUpFixture\]" -A3 --glob '*.cs'` — compare each namespace with the tests'; `rg -n "SignInAsync" --glob '*Tests.cs'` | blocker |
| E18 | **[Appium]** No removed Appium client APIs | `TouchAction` / `MultiAction` (removed in client 6.0), `ToggleWifi` / `ToggleData` / `ToggleAirplaneMode` / `SetConnectionType` (removed in 8.0), `ResetApp` / `CloseApp` / `LaunchApp`, `DesiredCapabilities`, or `AppiumBy` (it does not exist in .NET; the class is `MobileBy`) — each fails to compile or throws against Appium 3. The replacements are W3C actions or a `mobile:` gesture, `mobile: setConnectivity`, and `mobile: clearApp` | `rg -n "TouchAction\|MultiAction\|ToggleWifi\|ToggleData\|ToggleAirplaneMode\|SetConnectionType\|ResetApp\|CloseApp\|LaunchApp\|DesiredCapabilities\|AppiumBy" --glob '*.cs'` | major |

**E11 is not a finding on these documented owners of their own lifecycle:** the Reqnroll `[BeforeScenario]` hook
from `bdd-project-scaffold` (a binding cannot derive from `BaseTest`, so it owns the scenario's browser and keeps
`BaseTest`'s evidence); the Lighthouse fixture on `PlaywrightTest` from `accessibility-testing`, which calls
`Playwright.Chromium.LaunchPersistentContextAsync` on a free port (plan 003 D61) — not `Playwright.CreateAsync()`;
`BasePlaywrightApiTest : PlaywrightTest` from `api-test-author/playwright` (API-only, no browser); a grid fixture
that derives from a test class and overrides `ConnectOptionsAsync()` (`browser-cloud-setup`); and a production
probe from `production-uptime-checks`, which is monitoring code, not a test fixture.

---

## F — Locator hygiene
*Owning skills: `page-objects-from-url`, `mobile-screen-explorer`, `ui-test-author/*`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | `data-testid` / accessibility-id first | CSS or XPath used where a testid exists | `rg -n "GetByTestId\|By\.CssSelector\|By\.XPath\|FindByAccessibilityId" --glob '*.cs'` — compare the ratios | major |
| F2 | **[PW]** Semantic locators preferred | `Page.Locator("css…")` in test classes where `GetByRole`/`GetByLabel`/`GetByTestId` fits | `rg -n "\.Locator\(\"" --glob '*.cs'` | major |
| F3 | No brittle structural chains | `div > div > span:nth-child(3) > a`; long absolute XPath | `rg -n "nth-child\|//\*\[\|/div/div" --glob '*.cs'` | major |
| F4 | No volatile values inside locators | A GUID, numeric id, or state value interpolated into a selector | `rg -n "By\.\w+\(\\$\"\|Locator\(\\$\"" --glob '*.cs'` | major |
| F5 | Row addressing uses the sanctioned pattern | Per-row testids passed as props / row selectors built from row data, instead of a static parent locator addressed by index | Read list/table page objects | major |
| F6 | Locator strings are named constants | Literals re-typed across methods and files | `rg -o "\"[#.][A-Za-z0-9_-]{4,}\"" --glob '*.cs' \| sort \| uniq -c \| sort -rn \| head` | minor |
| F7 | No `IJavaScriptExecutor` click workarounds **[Sel]** | `ExecuteScript("arguments[0].click()", el)` papering over actionability | `rg -n "arguments\[0\]\.click" --glob '*.cs'` | major |
| F8 | Ambiguous text/role matches disambiguated **[PW]** | `GetByText("Submit")` matching `Submit Order` and `Submitting…` with no `Exact = true` | `rg -n "GetByText\(" --glob '*.cs'` | minor |
| F9 | A `missing-testids.md` report exists where testids are absent | The suite works around missing testids silently instead of handing the list to the FE team | `ls missing-testids.md **/missing-testids.md 2>/dev/null` | minor |
| F10 | A fallback locator is recorded, not marked | A `// TODO: missing data-testid` marker — or any comment — on a fallback locator instead of a `missing-testids.md` row naming the page, the element, the suggested id and the fallback in use | `rg -n "TODO.*testid\|missing data-testid" --glob '*.cs'` | minor |
| F11 | Test ids are PascalCase dot-separated and static | Kebab-case (`login-submit`) or dynamic ids (`row-42`, a GUID, an index, a state) in `GetByTestId(...)` instead of `Login.Submit` / `OrderRow` with the row picked by its content | `rg -n "GetByTestId\(\"[a-z]" --glob '*.cs'`; `rg -n "GetByTestId\(\\$\"" --glob '*.cs'` | minor |

---

## G — Test data
*Owning skills: `test-data-builder`, `data-driven-testing`, `db-testing/connection`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | Builders / ObjectMothers for objects with 4+ fields | Inline object literals duplicated across test files | `rg -n "new \w+(Request\|Dto\|Model\|Entity)\s*\{" --glob '*.cs' \| wc -l` vs builder count | major |
| G2 | Every builder field has a sensible default | A new required field rippling through 50 tests | `rg -n "class \w+Builder" -A25 --glob '*.cs'` | minor |
| G3 | Defaults are deterministic | Randomized values on fields the test asserts against | `rg -n "Random\|Guid\.NewGuid\(\)\|Faker\|Bogus" --glob '*.cs'` | major |
| G4 | `Build()` is pure and idempotent | `Build()` writing to the DB, logging, or returning the builder itself | `rg -n "public \w+ Build\(\)" -A12 --glob '*.cs'` | major |
| G5 | No god builder | One builder with 30 chained methods spanning unrelated aggregates | `rg -c "public \w+Builder With" --glob '*.cs' \| sort -t: -k2 -rn \| head` | minor |
| G6 | Defaults satisfy domain invariants | A default builder producing an invalid object (negative totals, empty required strings) | Read the builders' defaults | major |
| G7 | One fixture library, not two | AutoFixture/`IFixture` stacked on top of hand-written builders — unpredictable in combination | `rg -n "AutoFixture\|IFixture" --glob '*.csproj' --glob '*.cs'` | major |
| G8 | External data files are versioned and typed | CSV/JSON test data read with no schema and no validation, or living outside the repo | `rg -n "\.csv\"\|\.json\"" --glob '*.cs'` | minor |
| G9 | Data-driven cases are identifiable on failure | A source that yields 200 unnamed cases, so a red run names nothing | `rg -n "TestCaseSource" -A10 --glob '*.cs'` | minor |
| G10 | No production data in fixtures | Real customer names, emails, or ids in test data | `rg -ni "@gmail\|@outlook\|\+\d{9,}" --glob '*.cs' --glob '*.json'` | blocker |

---

## H — API test layering
*Owning skills: `api-test-author/{generator,reviewer,playwright,graphql,grpc}`, `api-client-writer`, `api-models`, `test-login-tokens`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | DTO + typed client + test are separate layers | Raw HTTP built inside test bodies | `rg -n "new RestRequest\(\|HttpRequestMessage\|\.GetAsync\(\"" --glob '*Test*.cs'` | major |
| H2 | Fixtures inherit the project's base API test | Hand-built RestSharp clients per fixture | `rg -n "class \w+Tests ?: ?" --glob '*.cs'` | major |
| H3 | Responses deserialize into typed DTOs | `JsonNode`/dictionary digging inside assertions | `rg -n "JsonNode\|JObject\|Dictionary<string, object>" --glob '*.cs'` | major |
| H4 | The client doesn't own deserialization for error paths | A client that always deserializes, so error-body assertions become impossible | `rg -n "Deserialize<" --glob '*Client*.cs'` | major |
| H5 | Status codes via `HttpStatusCode`, not raw ints | `Is.EqualTo(200)` | `rg -n "EqualTo\((200\|201\|204\|400\|401\|403\|404\|409\|422\|500)\)" --glob '*.cs'` | minor |
| H6 | 4xx tests assert the `ProblemDetails` body, not just the code | A 400/404/422 test asserting only `StatusCode` | `rg -n "(400\|404\|422\|BadRequest\|NotFound\|UnprocessableEntity)" -A6 --glob '*.cs'` | major |
| H7 | Auth tokens come from the token provider, cached per fixture | A hardcoded bearer string, or a token fetched per test | `rg -n "Bearer \|GetTokenAsync" --glob '*.cs'` | major |
| H8 | ROPG only against a test tenant with seeded users | Real credentials, or ROPG pointed at production | `rg -n "password\|Realm\|ResourceOwner" --glob '*.cs' --glob '*.json'` | blocker |
| H9 | Round-trip verification on writes | A POST test asserting one field and never reading the resource back | Read the write-path tests | major |
| H10 | **[GraphQL]** The `{data, errors}` envelope is asserted | A GraphQL test asserting HTTP 200 only, ignoring `errors` | `rg -n "errors\b" --glob '*.cs'` in GraphQL tests | major |
| H11 | **[gRPC]** Status codes asserted via `RpcException.StatusCode` | Message-string matching instead of the status code | `rg -n "RpcException" --glob '*.cs'` | major |
| H12 | One HTTP stack per project | RestSharp **and** Playwright `APIRequestContext` **and** raw `HttpClient` all in use with no rule | `rg -l "RestSharp\|APIRequestContext\|HttpClient" --glob '*.cs'` | minor |

---

## I — Assertion quality
*Owning skills: `api-test-author/review`, `ui-test-author/review`, `visual-regression` (I12), `accessibility-testing` (I13)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | Every test asserts something | A `[Test]` ending after an action with no assertion | `rg -n "public (async )?Task \w+" -A30 --glob '*.cs'` — scan for bodies with no `Assert`/`Expect` | blocker |
| I2 | Status asserted before the body is read | The test deserializes and asserts fields, then checks the status (or never does) | Read the happy-path tests | major |
| I3 | **[PW]** Web-first assertions used | `Assert.That(await loc.IsVisibleAsync(), Is.True)` / `TextContentAsync()` one-shots instead of `Expect(loc).ToBeVisibleAsync()` | `rg -n "IsVisibleAsync\(\)\|TextContentAsync\(\)\|InnerTextAsync\(\)" --glob '*.cs'` | major |
| I4 | Assertions verify behaviour, not implementation | Asserting on internal ids, ordering artefacts, or DOM structure that isn't the user-visible contract | Read a sample across the suite | major |
| I5 | Multi-assert grouped so all failures surface **[NUnit]** | Sequential asserts where the first failure hides the rest (`Assert.Multiple` fits) | `rg -n "Assert\.Multiple" --glob '*.cs'` vs multi-assert tests | minor |
| I6 | Negative and boundary cases exist | Only happy paths across a whole feature area | Compare positive/negative test counts per area | major |
| I7 | Failure messages identify the case | Bare `Assert.That(x, Is.True)` with no message on a parameterized test | `rg -n "Is\.True\)\s*;" --glob '*.cs'` | minor |
| I8 | No `try/catch` around the test body | A catch swallowing the assertion failure | `rg -n "try" -A4 --glob '*Test*.cs'` | major |
| I9 | Error-path assertions don't over-reach | A 401 test trying to deserialize a body the middleware never returns | `rg -n "401\|Unauthorized" -A6 --glob '*.cs'` | minor |
| I10 | No snapshot/approval file standing in for a real assertion | An approval test as the only coverage of a behaviour, with the file never reviewed | `rg -n "Approvals\|Verify\(\|\.approved\." --glob '*.cs'` | minor |
| I11 | **[PW]** URL assertions can pass | `ToHaveURLAsync("**/dashboard")` — the string is an exact match of the whole URL after `BaseURL` resolution, so a glob never matches; a glob belongs in `WaitForURLAsync`, a partial match in `ToHaveURLAsync(new Regex("/dashboard$"))` | `rg -n "ToHaveURLAsync\(\"[^\"]*\*" --glob '*.cs'` | major |
| I12 | **[PW]** Visual regression is a screenshot plus a comparer | A fabricated screenshot assertion (`ToHaveScreenshotAsync`, `ToMatchSnapshotAsync`) presented as built-in, instead of `Locator.ScreenshotAsync` + a comparer (`Codeuctivity.ImageSharpCompare`) + `AllureApi.AddScreenDiff`; baselines read relative to `bin/` instead of `ProjectPaths.Root`; baselines recorded outside the pinned `mcr.microsoft.com/playwright/dotnet` image; the `Applitools.Playwright` package id (the package is `Eyes.Playwright`) | `rg -n "ToHaveScreenshotAsync\|ToMatchSnapshotAsync\|ImageSharpCompare\|AddScreenDiff\|ProjectPaths" --glob '*.cs'`; `rg -n "Applitools\.Playwright\"" --glob '*.csproj' --glob '*.props'` | major |
| I13 | **[PW]** Accessibility scans assert at WCAG 2.2 AA through `RunAxe` | A scan with no tags (every rule, every level) or below 2.2 AA; `RunAxeLegacy`; violations filtered with no recorded reason; a Lighthouse `pwa` category (removed upstream) | `rg -n "RunAxe\|Tags\(\|wcag" --glob '*.cs'`; `rg -n "pwa" --glob '*.cs' --glob '*.json'` | major |

---

## J — External verification (DB, containers, brokers, storage, mail)
*Owning skills: `db-testing/{client,testcontainers,verification-queries}`, `messaging-testing`, `file-storage-testing`, `email-testing`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | Real engine, not a substitute **[TC]** | H2/SQLite/in-memory provider standing in for Postgres/SQL Server — production drift never caught | `rg -n "InMemory\|Sqlite\|H2" --glob '*.cs' --glob '*.csproj'` | major |
| J2 | Schema via real migrations | `EnsureCreated()` or a bespoke "test schema" | `rg -n "EnsureCreated\(\)" --glob '*.cs'` | major |
| J3 | Container started once per fixture/assembly **[TC]** | A container started in `[SetUp]` — one per test | `rg -n "\[SetUp\]" -A8 --glob '*.cs' \| rg "Container\|StartAsync"` | major |
| J4 | Images pinned to the production version **[TC]** | `postgres:latest` / an unpinned major | `rg -n "postgres:\|mssql\|mongo:\|redis:" --glob '*.cs'` | major |
| J5 | Connection details derived from the container | Hardcoded `Host=localhost;Port=5432` | `rg -n "Host=localhost\|Port=5432\|Server=\(local\)" --glob '*.cs' --glob '*.json'` | major |
| J6 | Probes are read-only and project explicit columns | `SELECT *`; a probe returning whole entities for a one-field assertion | `rg -n "SELECT \*" --glob '*.cs'` | minor |
| J7 | Every SQL parameter is bound | Values concatenated/interpolated into SQL | `rg -n "\\$\"SELECT\|\\$\"INSERT\|\" \+ \w+ \+ \"" --glob '*.cs'` | blocker |
| J8 | Seeding goes through builders/seeders, not duplicated raw SQL | The same `INSERT` copy-pasted across fixtures | `rg -n "INSERT INTO" --glob '*.cs' \| sort \| uniq -c \| sort -rn \| head` | minor |
| J9 | Row reset between tests | No Respawn/truncate/drop step, so tests inherit each other's rows | `rg -n "Respawn\|TRUNCATE\|DeleteAll" --glob '*.cs'` | major |
| J10 | Connections opened per call, not held across tests | A long-lived `_connection` field shared by a fixture | `rg -n "private .*Connection \w+;" --glob '*.cs'` | minor |
| J11 | Async all the way on data access | `.Result` on `OpenAsync`/`QueryAsync` (see D11) | covered by D11 | blocker |
| J12 | Broker/queue assertions poll a condition | A sleep between publish and consume assertion | covered by D2/D8 | major |
| J13 | No connection string or secret in logs, test names, or Allure attachments | A connection string echoed into output on failure | `rg -n "ConnectionString" --glob '*.cs'` — check log/attachment paths | blocker |
| J14 | Container diagnostics attached on failure **[TC]** | Container logs discarded, so a CI-only failure is unexplainable | `rg -n "GetLogsAsync" --glob '*.cs'` | minor |

---

## K — Config, secrets & environments
*Owning skills: `qa/cicd/ci-conventions`, `test-login-tokens`, `db-testing/connection`, `ui-test-author/playwright` (K9)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| K1 | No credentials in source | Literal passwords, API keys, tokens, or `x-api-key` values in test code or `appsettings*.json` | `rg -ni "password\s*=\s*\"\|apikey\|api_key\|secret\s*=\s*\"\|Bearer [A-Za-z0-9]{10}" --glob '*.cs' --glob '*.json'` | blocker |
| K2 | No hardcoded environment URLs | `https://staging.example.com` inline in tests or page objects | `rg -n "https?://" --glob '*.cs'` | major |
| K3 | Secrets read from env vars, lazily | A secret read in a static field initializer (breaks tests that don't need it) | `rg -n "static.*GetEnvironmentVariable" --glob '*.cs'` | major |
| K4 | Config flows through one typed reader | `Configuration["..."]` string lookups scattered through tests | `rg -n "Configuration\[" --glob '*.cs'` | minor |
| K5 | Per-environment settings are layered, not branched in code | `if (env == "staging")` choosing behaviour inside tests | `rg -n "== \"staging\"\|== \"prod" --glob '*.cs'` | minor |
| K6 | **[Appium]** Devices, app path and server URL come from env or configuration | `DeviceName = "Pixel_6"` or a device list written in a C# file outside the factory; a literal `APP_PATH` or `http://127.0.0.1:4723` in a test | `rg -n "DeviceName = \"\|\.apk\|\.ipa\|4723" --glob '*.cs'` | major |
| K7 | No user-secrets / local settings committed | `secrets.json` or a filled-in `appsettings.Local.json` in git | `git ls-files \| rg -i "secret\|\.local\."` | blocker |
| K8 | Tokens never logged | A token written to console/Allure on failure | `rg -n "AccessToken" --glob '*.cs'` — check log/attachment paths | blocker |
| K9 | **[PW]** A base URL is set, from `BASE_URL` | Relative `GotoAsync("/x")` / `APIRequest.PostAsync("/api/x")` with no `BaseURL` in `ContextOptions()` (they throw "Cannot navigate to invalid URL"); a hardcoded host instead of `BASE_URL`; a required variable read with `GetEnvironmentVariable(...)!` instead of `BaseTest.RequiredEnv` | `rg -n "BaseURL" --glob '*.cs'` vs `rg -n "GotoAsync\(\"/" --glob '*.cs'`; `rg -n "GetEnvironmentVariable\(.*\)!" --glob '*.cs'` | blocker |

---

## L — Reporting & flake management
*Owning skills: `qa/reporting/dotnet/skills/{test-reports,flaky-test-quarantine}`, `evidence-capture` (L4, L15)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| L1 | Allure is wired per test project | No `Allure.NUnit`, no `allureConfig.json` copied to output — CI produces no human-readable report | `rg -n "Allure" --glob '*Tests.csproj'`; `ls **/allureConfig.json` | major |
| L2 | Every test carries feature/story/severity metadata | Missing `[AllureFeature]`/`[AllureStory]`/`[AllureSeverity]`, or an `[AllureFeature("misc")]` catch-all | `rg -c "AllureFeature" --glob '*.cs'` vs test count; `rg -n "AllureFeature\(\"misc" --glob '*.cs'` | minor |
| L3 | API failures attach the response body **before** asserting | A red build showing a status-code message and no body | `rg -n "AttachBody" --glob '*.cs'` vs error-path tests | minor |
| L4 | UI failures keep trace, full-page screenshot **and** video | **[PW]** Only a screenshot, or nothing, on a failure; evidence anywhere but `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}` (Reqnroll: `<Feature>.<Scenario>`); a second `[TearDown]`, base class or action attribute for the same evidence beside `BaseTest`'s; a `catch` in the evidence teardown; `SaveAsAsync` before `Context.CloseAsync()`; each file not attached to both NUnit (`TestContext.AddTestAttachment`) and Allure | `rg -n "AddAttachment\|AddTestAttachment\|Tracing\.\|SaveAsAsync" --glob '*.cs'` | major |
| L5 | Allure history is preserved across runs | A trendless report — flake detection impossible | CI config: history restore/publish step | major |
| L6 | One reporter convention | `Allure.NUnit` and `Allure.XUnit` writing into the same `allure-results/` | `rg -n "Allure\.(NUnit\|XUnit)" --glob '*.csproj'` | major |
| L7 | `allure-results/` is an artifact, not committed | The results directory tracked in git | `git ls-files \| rg "allure-results"` | minor |
| L8 | Attachments carry no secrets/PII, and aren't huge | Tokens, connection strings, or 5 MB logs attached per test | `rg -n "AddAttachment" -B4 --glob '*.cs'` | blocker |
| L9 | Retries only on a documented hotspot | Any `[Retry]` on a test with no dated `[AllureIssue]` / description naming the hotspot (`qa/cicd/ci-conventions`: no retries otherwise); `[Retry(3+)]`; `[Retry(1)]` believed to retry (NUnit counts attempts — it is one run, no retry; `[Retry(2)]` is one retry); a retry hiding a deterministic failure | `rg -n "\[Retry\(\|RetryOnFailure" -B3 --glob '*.cs'` | major |
| L10 | One retry mechanism only | `[Retry]` **and** a CI-level rerun (caps multiply, flake hidden twice over) | compare L9 with the CI config | major |
| L11 | Quarantine is a category + non-gating lane, never `[Ignore]` | Flaky tests silently `[Ignore]`d — coverage lost with no trail | `rg -n "\[Category\(\"Flaky\|\[Ignore\(" --glob '*.cs'` | major |
| L12 | Every quarantined test carries a ticket and gets reviewed | A `Flaky` category that only ever grows | `rg -n "Flaky" -A3 --glob '*.cs'` — check for issue links | major |
| L13 | No sleeps in teardown/attachment helpers | `Thread.Sleep` in `[TearDown]` "waiting for attachments to flush" | covered by D1; read teardowns | blocker |
| L14 | Allure attachments and links are recorded where a result exists | `AllureApi.AddTestAttachment` (no such method); `AllureApi.AddLink` / `AddAttachment` in `[OneTimeSetUp]` / `[OneTimeTearDown]`, where no test result is running and nothing is recorded — use `AddGlobalAttachment` there | `rg -n "AllureApi\." -B8 --glob '*.cs' \| rg "OneTime\|AllureApi"` | major |
| L15 | **[Appium]** A failed mobile test keeps a screenshot, the page source, a device-log tail and the recording | Nothing attached on failure; evidence anywhere but `<WorkDirectory>/appium-artifacts/<Class>.<Test>.{png,xml,log,mp4}`; a second `[TearDown]` capture beside `BaseMobileTest`'s; a recording started and not stopped in the teardown (it blocks the next start); the recording kept for passing tests; a `catch` in the evidence teardown; `AllureApi.AddAttachment(name, type, body)` with a string body (three strings is a path) | `rg -n "StartRecordingScreen\|StopRecordingScreen\|GetScreenshot\|PageSource\|appium-artifacts" --glob '*.cs'` | major |

---

## M — CI wiring
*Owning skills: `qa/cicd/ci-conventions`, `qa/cicd/dotnet/skills/ci-pipelines`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| M1 | A pipeline runs the suite | No CI definition — the suite only ever runs locally | `ls .github/workflows azure-pipelines.yml .gitlab-ci.yml` | major |
| M2 | Two lanes: a fast PR lane and a full scheduled lane | Everything on every PR (slow, so people skip it), or nothing scheduled | read the triggers | major |
| M3 | **No green-washing on test steps** | `continue-on-error` / `allow_failure` / `\|\| true` on a test step | `rg -n "continue-on-error\|allow_failure\|\|\| true" .github azure-pipelines.yml .gitlab-ci.yml` | blocker |
| M4 | Shard membership computed once, upstream | Each shard re-discovering tests at runtime | read the matrix/fan-out step | major |
| M5 | One shard failing doesn't cancel the others | `fail-fast: true` on the test matrix — sibling reports lost | `rg -n "fail-fast" .github` | major |
| M6 | Both reporters emitted (TRX/JUnit **and** Allure) | Only one — either no PR widget or no history/trend | read the publish steps | minor |
| M7 | **OIDC, not long-lived secrets** | PATs / static cloud keys stored as CI variables where OIDC exists | `rg -ni "PAT\|_TOKEN\|AWS_SECRET\|CLIENT_SECRET" .github azure-pipelines.yml .gitlab-ci.yml` | major |
| M8 | Secrets never echoed or artifact-collected | A step printing a fetched secret, or writing it into a collected path | `rg -n "echo .*SECRET\|echo .*TOKEN" .github` | blocker |
| M9 | No pipeline-level retry of assertions | A rerun-failed-tests step masking flakes | `rg -ni "rerun\|retry" .github azure-pipelines.yml .gitlab-ci.yml` | major |
| M10 | Tool and image versions pinned | Floating `latest` for the runner tooling, Allure CLI, or containers | `rg -n "latest" .github azure-pipelines.yml .gitlab-ci.yml` | minor |
| M11 | Linux runners for Testcontainers work **[TC]** | Windows runners with Linux container modules | read the runner declarations | major |
| M12 | Runner parallelism doesn't fight fixture-owned containers | Matrix parallelism plus `LevelOfParallelism > 1` on container fixtures | compare CI config with C7 | major |
| M13 | Perf gate honours the tool's exit code **[NBomber]** | YAML interpreting perf metrics, or softening the exit code | read the perf stage | major |
| M14 | Artifact retention matches the convention | Traces/videos kept always (cost) or results kept 1 day (no forensics) | read the upload steps | nit |
| M15 | **[NUnit]** Shards split by class filters computed once | `Playwright.Shard` (the adapter ignores it — "not implemented" — so every shard runs the whole suite) or an `NUnit.Where` modulo predicate instead of class filters from one `ci/nunit-shards.sh` (`qa/cicd/dotnet/skills/ci-pipelines`) | `rg -n "Playwright\.Shard\|NUnit\.Where" .github azure-pipelines.yml .gitlab-ci.yml`; `rg -n "Shard" --glob '*.runsettings'` | major |
| M16 | **[PW]** Nightly-only and separate-run categories stay out of the PR gate | The UI gate filter runs `visual`, `lighthouse` or `grid` fixtures (they need the pinned image, a free port or cloud credentials); visual baselines updated outside the `mcr.microsoft.com/playwright/dotnet` image job; no upload of `playwright-artifacts/` on failure | `rg -n "TestCategory" .github azure-pipelines.yml .gitlab-ci.yml`; `rg -n "playwright-artifacts" .github azure-pipelines.yml .gitlab-ci.yml` | major |

---

## N — Coverage shape
*Owning skills: `qa/manual/{test-strategy,quality-metrics}`, `test-quality-check`, `qa/_shared/performance`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| N1 | Contract tests exist before integration tests on each public API | Only end-to-end tests through the UI for API behaviour | compare API test count with endpoint count | major |
| N2 | The pyramid isn't inverted | Hundreds of UI tests, a handful of API tests, no unit-level coverage | count tests per project | major |
| N3 | Critical flows are covered | The login/checkout/payment path has no end-to-end coverage | read the test inventory against the app's key flows | major |
| N4 | No duplicated coverage across layers | The same validation asserted in unit, API, and UI tests | scan for repeated assertion targets | minor |
| N5 | Mutation score gate where the tool exists **[Stryker.NET]** | Coverage reported as a quality claim with no mutation testing behind it | `ls stryker-config.json`; `rg -n "dotnet-stryker" .` | minor |
| N6 | Coverage is a signal, not a target | A coverage percentage gate with assert-nothing tests inflating it | compare I1 findings with the coverage gate | major |
| N7 | Perf/security lanes exist where the domain owns them | No perf suite for a latency-sensitive service; no security stage at all | `ls **/*Perf* **/*Load*`; read the CI stages | minor |
| N8 | Test inventory traces to planned cases where a TC document exists | Tests generated from a test-case suite with no `[AllureTms]`/`TmsLink`/TC-id link back | `rg -n "AllureTms\|TmsLink\|TC-" --glob '*.cs'` | nit |

---

## Section index — for the report's applicability matrix

`Discipline` is which `scope:` value (see the skill's Discipline scope section) keeps this section in play. `all` means every scope runs it; `api`/`ui`/`mobile` means it's skipped by choice outside that scope (on top of the tool-presence probe in `Conditional?`).

| Letter | Section | Conditional? | Discipline |
|---|---|---|---|
| A | Build health & suite lane | always (A9, A10 **[PW]** follow the driver) | all — A9, A10 **[PW]** only under `ui`/`all` |
| B | Test naming, structure & comments | always | all |
| C | Independence & isolation | always | all |
| D | Waits & timing | always (tool-tagged rows follow the driver) | all — but PW/Sel-tagged rows only run under `ui`/`all`, Appium-tagged rows only under `mobile`/`all` |
| E | Page / screen objects | UI or mobile suite present | `ui`, `mobile` — E14, E18 **[Appium]** only under `mobile`/`all`; E13 **[Sel]**, E16, E17 **[PW]** only under `ui`/`all` |
| F | Locator hygiene | UI or mobile suite present | `ui`, `mobile` — F2 **[PW]**, F7 **[Sel]** only under `ui`/`all` |
| G | Test data | always | all |
| H | API test layering | API suite present | `api` only |
| I | Assertion quality | always | all — I3, I11–I13 **[PW]** only under `ui`/`all` |
| J | External verification | suite touches a DB / broker / storage / mail | all — discipline-independent, gated only by its own probe |
| K | Config, secrets & environments | always | all — K9 **[PW]** only under `ui`/`all`; K6 **[Appium]** only under `mobile`/`all` |
| L | Reporting & flake management | always — **absence is L1**, not N/A | all — L15 **[Appium]** only under `mobile`/`all` |
| M | CI wiring | always — **absence is M1**, not N/A | all — M16 **[PW]** only under `ui`/`all` |
| N | Coverage shape | always (mutation row needs Stryker.NET) | all |
