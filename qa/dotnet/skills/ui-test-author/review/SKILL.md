---
name: ui-tests-review
description: Use when the user asks to review existing .NET UI test code or page objects. Triggers: "review this Playwright C# spec", "look at this NUnit page object", "is this Appium .NET test any good". Do NOT use for writing new tests (`qa-dotnet:ui-tests-playwright`) or a whole-suite audit (`qa-dotnet:standards-audit`).
---

# QA — UI Test & Page Object Reviewer (.NET / C#)

Reviews .NET UI test code (Playwright .NET, Selenium .NET, Appium .NET) against the patterns enforced by the matching generator skills. Produces a findings table in the format defined in `CLAUDE.md`. **Does not rewrite the code** — points to the fix and lets the human apply it.

## When to use

- A diff or file (page object, `[Test]` class, fixture, `BaseTest`, `BasePage`, `.runsettings`, `.csproj`) is submitted for review
- Pre-merge gate on a PR touching `Pages/`, `Tests/`, `AppiumTests/Pages/`, or any NUnit/xUnit UI test

## When NOT to use

- Generating new code → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, `qa/dotnet/skills/ui-test-author/appium`
- Architecting the POM → `qa/dotnet/skills/page-object-design`
- Reviewing API tests → `qa/dotnet/skills/api-test-author/review`
- Reviewing Java or TypeScript UI code → `qa/java/skills/ui-test-author/review`, `qa/typescript/skills/ui-test-author/review`

## Inputs needed

1. **Stack** — Playwright .NET, Selenium .NET, or Appium .NET
2. **Files** to review (page objects, `[Test]` classes, fixtures, `BaseTest`/`BasePage`, `.runsettings`, `.csproj`)
3. **Context** — new feature, refactor, or bug fix?
4. **Project conventions** — anything overriding the stack defaults (a different test-id attribute, banned XPath, required `[AllureStep]`)

## Output format

```
| Severity | Location                | Issue                                  | Suggested fix                                               |
|----------|-------------------------|----------------------------------------|-------------------------------------------------------------|
| blocker  | Pages/LoginPage.cs:42   | `Task.Delay(2000)` used as UI sync     | Replace with `Expect(locator).ToBeVisibleAsync()` auto-wait |
| major    | Pages/ProductPage.cs:18 | XPath where a `data-testid` exists     | Switch to `GetByTestId("Inventory.Item")`                   |
| minor    | Pages/CartPage.cs:55    | Inline `Page.Locator("...")` repeated  | Promote to `private readonly ILocator _summary` field       |
```

Severities follow `CLAUDE.md`: **blocker** (a bug, a broken build, a hard rule — `.Result`/`.Wait()`, `Task.Delay` as sync, shared driver, raw credentials), **major**, **minor**, **nit**.

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator skill.

## Cross-stack smells (apply to every .NET UI review)

| Check | Bad sign | Severity |
|---|---|---|
| Async all the way down | `.Result`, `.Wait()`, `.GetAwaiter().GetResult()`, or `async void` outside an event handler | blocker |
| No `Task.Delay` as UI sync | `await Task.Delay(2000)` waiting on DOM state | blocker |
| Constructor injection | Service locator / static `Driver.Current` / property injection in pages | major |
| Locators are semantic | XPath/CSS where a test id, role, or label exists | major |
| Test ids follow the contract | Kebab-case or dynamic ids (`login-submit`, `row-42`) instead of PascalCase dot-separated static ids (`Login.Submit`, `OrderRow`) | minor |
| A fallback is recorded, not marked | A `// TODO: missing data-testid` marker or comment on a fallback locator instead of a `missing-testids.md` row | minor |
| Assertions live in tests, not page objects | `Assert.*` / `Expect(...)` inside page action methods | major |
| No business logic in page objects | Price calculation, JSON parsing, branching on app state inside POM | major |
| Tests are independent | `[Order(...)]` chained `[Test]` methods modelling a flow | blocker |
| One logical behavior per test | One `[Test]` verifies login + cart + checkout | major |
| No `try`/`catch` in a test or a hook | Any catch in a `[Test]`, `[SetUp]` or `[TearDown]`; a blanket `catch (Exception)` in a page helper | major |
| Expected exceptions from async code | `Assert.Throws<T>(() => SomethingAsync())` — the exception lives in the discarded `Task`, so it reports "no exception"; `Assert.Throws` with an `async` lambda is `async void`. Use `Assert.ThrowsAsync<T>` | major |
| Failures identify the subject | A Playwright assertion on a locator with no `Describe()` and no `Expect(locator, "message")`; an NUnit value assertion with no message | minor |
| Every assertion states one expected condition | `Is.EqualTo(a).Or.EqualTo(b)`, `Is.AnyOf(...)`, `\|\|` inside `Assert.That`, `Does.Match("a\|b")` or `new Regex("a\|b")` in a text/URL assertion, an assertion on an `Or()` locator | major |
| Test names are `Should_X_When_Y` | `Test1`, `LoginTest`, `Signs_In_With_Valid_Credentials` | minor |
| No hardcoded credentials / base URLs | Literal `admin@example.com`, hardcoded `https://staging.x.y` | major |
| Locators built once | Inline locator strings re-typed across methods; public locator fields | minor |
| No conditional logic driving assertions | `if (x) Assert.That(...)` or a `foreach` in a `[Test]` instead of `[TestCase]` / `[TestCaseSource]` | major |
| One version source under CPM | `Version=` on a `PackageReference` while `Directory.Packages.props` manages versions — restore fails with NU1008 | blocker |
| Nullable reference types honored | `string?` ignored, `!`-bangs scattered through page object fields | minor |

## Playwright .NET smells

The writer's rules and mechanics are in `qa/dotnet/skills/ui-test-author/playwright` (`references/lifecycle.md`, `locators.md`, `assertions.md`).

| Check | Bad sign | Severity |
|---|---|---|
| Tests derive from the one `BaseTest` | `Playwright.CreateAsync()` in a `[Test]`, a `[SetUp]` or a fixture's `[OneTimeSetUp]`; a second base class per role or device. The root `AuthSetup` `[SetUpFixture]` is the one exception | blocker |
| A base URL is set | Relative `GotoAsync("/x")` / `APIRequest.PostAsync("/api/x")` with no `BaseURL` in `ContextOptions()`, or a hardcoded host instead of `BASE_URL` | blocker |
| `ContextOptions()` amends the base | An override that returns `new()` / `new BrowserNewContextOptions { ... }` instead of amending `base.ContextOptions()` — it drops `BaseURL`, the video folder and the defaults | major |
| The `[SetUpFixture]` covers the tests | `AuthSetup` in `X.Support` while tests live in `X.Tests` — NUnit runs it only for its own namespace, so the state file is never written | blocker |
| Parallelism is `ParallelScope.Self` | `ParallelScope.All` / `Children` / `Fixtures` on a Playwright fixture — tests of one fixture share its `Page` | blocker |
| Launch settings in the `.runsettings` | Browser, headless or test-id attribute hardcoded in code; `<Headless>` or `<Shard>` directly under `<Playwright>` (ignored: "not implemented") | major |
| Failure evidence survives | The context left open in the derived `[TearDown]` (`PageTest` closes it only after a pass); `SaveAsAsync` before `Context.CloseAsync()` | major |
| Code compiles on the pinned version | `Page.Video.GetPathAsync()` (the API is `PathAsync()`); `Within(`, `GetByRef` or `RecordVideoFps` on 1.63; `Visible()` called as a method | blocker |
| `ILocator` has no `.Text` | `Assert.That(banner.Text, ...)` — Selenium's `IWebElement` API pasted into Playwright; it does not compile | blocker |
| Every test asserts something | `[Test]` body ends with an action and no `Expect(...)` | blocker |
| Web-first assertions used | `Assert.That(await loc.IsVisibleAsync(), Is.True)` / `TextContentAsync()` / `CountAsync()` one-shots | major |
| URL assertions match | `ToHaveURLAsync("**/dashboard")` — the string is an exact match after `BaseURL` resolution; use a `Regex` or `WaitForURLAsync` | major |
| Exact HTTP status | `Assert.That(res.Ok, Is.True)` or `Expect(res).ToBeOKAsync()` when seeding | major |
| Locator ladder | `Page.Locator("css...")` where a test id or role exists, or in a test class | major |
| No page-level selector or deprecated APIs | `Page.ClickAsync(selector)`, `Page.FillAsync(selector)`, `Page.InnerTextAsync(selector)`, `QuerySelectorAsync`, `WaitForNavigationAsync` | major |
| Scoped, not positional | `.First` / `Nth()` silencing a strictness error with no reason in the name | major |
| `Visible` over `:visible` | `:visible` in a selector on 1.63+ | minor |
| No sleeps or retry loops | `Page.WaitForTimeoutAsync(...)`, `Task.Delay(...)` or `while (retries-- > 0)` waiting on UI state | blocker |
| Actions wait for themselves | `WaitUntil = WaitUntilState.NetworkIdle`; `Force = true`; `WaitForAsync()` right before an action; `WaitForFunctionAsync` for visible/text state | major |
| `RunAndWaitForResponseAsync` wraps the trigger | `WaitForResponseAsync(...)` started after the action (race) | major |
| `Exact = true` for ambiguous names | `GetByText("Submit")` matching `Submit Order`, `Submitting…` | minor |
| Auth via storage state | Every test calls `SignInAsync(...)` before its real behaviour | major |
| No seeding in `[OneTimeSetUp]` | A record shared by a fixture's tests, created where no `Page` exists | major |
| Pages built in the test class | Page objects as properties of `BaseTest` | minor |

## Selenium .NET smells

| Check | Bad sign | Severity |
|---|---|---|
| All page objects inherit `BasePage` | Pages calling `_driver.FindElement(...)` directly without a base abstraction | major |
| Locator order honored: test id (`data-testid`) → `id` → `css` → `class` → `xpath` | XPath used where a test id exists | major |
| Driver lifecycle via `IDriverFactory` + DI / `AsyncLocal<IWebDriver>` | `new ChromeDriver()` in a test or `[SetUp]` directly | blocker |
| `BaseTest` provides driver via `[SetUp]` / `[TearDown]` | Per-test driver instantiation or shared static driver | major |
| `WebDriverWait` + `ExpectedConditions` for conditional waits | `Thread.Sleep` for synchronization | blocker |
| No `PageFactory` / `[FindsBy]` (legacy, deprecated) | `PageFactory.InitElements(driver, this)` calls | major |
| Component classes scoped to a parent `IWebElement` for repeating items | One page object that re-queries the DOM for every row | major |
| Multi-step flows live in sub-folders (`Pages/Checkout/`) | Flat `Pages/` with 30 unrelated pages | minor |
| Navigation methods return the destination page object | Navigation method returns `void`; test instantiates the next page | minor |
| No implicit + explicit waits mixed | `driver.Manage().Timeouts().ImplicitWait = ...` combined with `WebDriverWait` | major |
| No `IJavaScriptExecutor` `.click()` workarounds | `((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click()", el)` | major |
| Element accessors return `IWebElement` (or wrapped), not pre-asserted booleans | `public bool IsLoginButtonVisible()` returning the assertion | minor |

## Appium .NET smells

| Check | Bad sign | Severity |
|---|---|---|
| Page objects subclass `BaseAppiumPage` | Class extends `AppiumDriver` directly or uses raw `IWebDriver` | major |
| Per-platform ladder honored: `TestId` (iOS `AccessibilityId`, Android `Id`) → native query → XPath | XPath where a test id exists; `AccessibilityId` on Android for a React Native `testID` | major |
| Elements stay private; the page exposes intent methods and queries | A public method returns `AppiumElement` or `IWebElement` | minor |
| `VerifyPageLoaded()` present and asserts a landmark | Missing or empty implementation | major |
| Navigation actions return the destination page object | Navigation method returns `void` | minor |
| Locator strings declared as `private const string` | Locator literals inline in action methods | minor |
| Platform branching abstracted behind a strategy / locator map | `if (Platform == "iOS") … else …` scattered across pages | major |
| App state reset between tests (fresh driver / `mobile: clearApp` / `TerminateApp` + `ActivateApp`) | Shared app state leaks between tests, or the removed `ResetApp()` / `CloseApp()` is called | blocker |
| One platform switch (`PLATFORM`); devices, app path and URL from env through the factory | `new AppiumOptions { … }` with `DeviceName = "Pixel_6"` in a test or base, or a second selection mechanism | major |
| Gestures via `ExecuteScript("mobile: …")` or W3C Actions; network via `mobile: setConnectivity` | `TouchAction` / `MultiAction` (removed in 6.0), `ToggleWifi`, `SetConnectionType` (removed in 8.0) | major |
| No `Thread.Sleep` between gestures | `Thread.Sleep(1500)` after a swipe waiting for animation | blocker |
| Failure evidence comes from `BaseMobileTest` only | No screenshot or page source on failure, or a second capture hook | major |

## Good signals (.NET)

- Playwright: one `BaseTest : PageTest` with `BaseURL` and failure evidence, a `.runsettings`, CPM; Selenium: a thin base page and an `AsyncLocal` driver factory; Appium: a thin base page, a driver factory, `BaseMobileTest`
- Locators built once on the highest ladder rung; components take a parent `ILocator` / `IWebElement`
- One `[Test]` per behavior named `Should_X_When_Y`, web-first assertions, `[TestCase]` parameterization

## Always-flag anti-patterns

Each is a row above; flag it whatever else the review finds.

- **`OR` in an assertion**, including a `"Saved|Success"` regex inside `ToHaveTextAsync(new Regex(...))` or `Does.Match` — it passes on the wrong state.
- **A test that asserts nothing, or a page object that asserts.**
- **`Thread.Sleep` / `Task.Delay` for sync, `.Result` / `.Wait()`, `async void`**, and any `try`/`catch` in a `[Test]` or a hook — an expected exception is `Assert.ThrowsAsync<T>`.
- **Relative navigation with no `BaseURL`, a `ContextOptions()` that returns `new()`, or an `AuthSetup` outside the tests' namespace** — each makes every test fail before its first assertion.
- **Static or shared browser state** — `static IWebDriver`, `ParallelScope.All` with Playwright.
- **Any inline comment in a test body or a page-object method**, and any stale comment — rename or extract, never reword.

## Comments in test code

Load **[`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** for the rule, the complex-flow test that earns a doc comment, the trivia list, the severity mapping and its **test-code** section. Here it covers **page-object and screen-object bodies** as well as tests — an intent-revealing method name is the page object's documentation.

| .NET mechanic | What to check |
|---|---|
| Doc syntax | XML doc (`/// <summary>`) — a doc block on a locator field, or restating `ClickSave`, is trivia |
| Skips needing a reason and a ticket | `[Ignore("")]` / a bare `[Explicit]` — a silently disabled test |
| Where an unclear interaction goes instead | Into a named page-object method, not a comment above the locator chain |

**The locator corollary.** A comment explaining a locator (`// the third span is the price`) is evidence the locator is **positional and brittle**. Fix the locator: request a `data-testid` and record it in `missing-testids.md`.

## Procedure

1. Identify the **stack** from imports and file location, and read each file end-to-end before writing findings.
2. Walk the cross-stack list, then the stack-specific list.
3. For each finding: file path + line, issue, one-sentence fix. **Do not rewrite the code**; hand off to the matching generator.

## Handoffs

- Need to rewrite → the matching generator under `qa/dotnet/skills/ui-test-author/`
- Architecture is the real problem → `qa/dotnet/skills/page-object-design`
- Test data shape is wrong → `qa/dotnet/skills/test-data-builder`
- API tests in the same PR → `qa/dotnet/skills/api-test-author/review`
- Allure reporting questions → `qa/reporting/dotnet/skills/test-reports`
