---
name: qa-ui-test-author-reviewer-dotnet
description: Use when the user asks to review existing .NET UI test code or page objects. Triggers: "review this Playwright C# spec", "look at this NUnit page object", "is this Appium .NET test any good".
---

# QA — UI Test & Page Object Reviewer (.NET / C#)

Reviews .NET UI test code (Playwright .NET, Selenium .NET, Appium .NET) against the patterns enforced by the matching generator skills. Produces a findings table in the format defined in `CLAUDE.md`. **Does not rewrite the code** — points to the fix and lets the human apply it.

## When to use

- A diff or file (page object, `[Test]` class, fixture, `BaseTest`, `BasePage`) is submitted for review
- Pre-merge gate on a PR touching `Pages/`, `Tests/`, `AppiumTests/Pages/`, or any NUnit/xUnit UI test
- Second opinion on whether a .NET page object is well-structured

## When NOT to use

- Generating new code → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, `qa/dotnet/skills/ui-test-author/appium`
- Architecting the POM → `qa/dotnet/skills/page-object-architect`
- Reviewing API tests → `qa/dotnet/skills/api-test-author/reviewer`
- Reviewing Java UI code → `qa/java/skills/ui-test-author/reviewer`
- Reviewing TypeScript UI code → `qa/typescript/skills/ui-test-author/reviewer`

## Inputs needed

1. **Stack** — Playwright .NET, Selenium .NET, or Appium .NET
2. **Files** to review (page objects, `[Test]` classes, fixtures, `BaseTest`/`BasePage`)
3. **Context** — new feature, refactor, or bug fix?
4. **Project conventions** — anything overriding the stack defaults (e.g. project mandates `Microsoft.Playwright.NUnit.PageTest`, bans XPath, requires `[AllureStep]`)

## Output format

```
| Severity | Location                       | Issue                                                  | Suggested fix                                                |
|----------|--------------------------------|--------------------------------------------------------|--------------------------------------------------------------|
| blocker  | Pages/LoginPage.cs:42          | `Task.Delay(2000)` used as UI sync                     | Replace with `Expect(locator).ToBeVisibleAsync()` auto-wait  |
| blocker  | Pages/CartPage.cs:88           | `.Result` on async call inside page object             | Make method `async Task` all the way down                    |
| major    | Pages/ProductPage.cs:18        | XPath where a `data-test` attribute exists             | Switch to `GetByTestId("inventory-item")`                    |
| minor    | Pages/CheckoutPage.cs:55       | Inline `Page.Locator("[data-test='...']")` repeated    | Promote to `private readonly ILocator _summary` field        |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, or violates a hard rule (`.Result`/`.Wait()`, `Task.Delay` as sync, shared driver, raw credentials)
- **major** — design or correctness issue that will hurt soon (brittle locators, assertions in page objects, NetworkIdle waits)
- **minor** — style or small inconsistency (naming, missing field promotion)
- **nit** — optional preference

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator skill.

## Cross-stack smells (apply to every .NET UI review)

| Check | Bad sign | Severity |
|---|---|---|
| Async all the way down | `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` in tests or pages | blocker |
| No `Task.Delay` as UI sync | `await Task.Delay(2000)` waiting on DOM state | blocker |
| Constructor injection | Service locator / static `Driver.Current` / property injection in pages | major |
| Locators are semantic | XPath/CSS where `data-test`, role, or label exists | major |
| Assertions live in tests, not page objects | `Assert.*` / `Expect(...)` inside page action methods | major |
| No business logic in page objects | Price calculation, JSON parsing, branching on app state inside POM | major |
| Tests are independent | `[Order(...)]` chained `[Test]` methods modelling a flow | blocker |
| One logical behavior per test | One `[Test]` verifies login + cart + checkout | major |
| Test names describe behavior | `Test1`, `LoginTest`, `ClickButtonTest` | minor |
| No hardcoded credentials / base URLs | Literal `admin@example.com`, hardcoded `https://staging.x.y` | major |
| Locators promoted to `readonly ILocator` / `private const string` fields | Inline locator strings re-typed across methods | minor |
| No conditional logic driving assertions | `if (x) Assert.That(...)` instead of `[TestCase]` parameterization | major |
| `[TestCase]` / `[TestCaseSource]` used for parameterization, not `foreach` in `[Test]` | Loop-driven multi-case test that hides which case failed | major |
| Nullable reference types honored | `string?` ignored, `!`-bang scattered through page object fields | minor |
| `records` / immutable models for test data | Mutable DTOs with public setters used as test fixtures | minor |
| No `async void` outside event handlers | `public async void DoStuff()` on a page or test class | blocker |

## Playwright .NET smells

| Check | Bad sign | Severity |
|---|---|---|
| Every test asserts something | `[Test]` body ends with an action and no `Expect(...)` / `Assertions.Expect(...)` | blocker |
| Web-first assertions used | `Assert.That(await loc.IsVisibleAsync(), Is.True)` / `Assert.That(await loc.TextContentAsync(), Is.EqualTo(...))` / count-based one-shots | major |
| `GetByRole` / `GetByLabel` / `GetByTestId` preferred | `Page.Locator("css...")` in test classes | major |
| Locators are `private readonly ILocator` fields initialized in constructor | Properties that call `Page.Locator(...)` per access | minor |
| No hardcoded sleeps | `Page.WaitForTimeoutAsync(...)` or `Task.Delay(...)` to wait on UI state | blocker |
| No `WaitUntil = WaitUntilState.NetworkIdle` | `GotoAsync(url, new() { WaitUntil = WaitUntilState.NetworkIdle })` | major |
| No `Force = true` to bypass actionability | `.ClickAsync(new() { Force = true })` / same on `FillAsync`/`CheckAsync` | major |
| No redundant pre-waits before auto-waiting actions | `locator.WaitForAsync()` immediately before `locator.ClickAsync()` | minor |
| `RunAndWaitForResponseAsync` wraps the trigger | `await page.WaitForResponseAsync(...)` placed before/after the action (race) | major |
| Custom retry loops replaced by raised assertion timeouts | `while (retries-- > 0) { … Task.Delay … }` | major |
| `WaitForFunctionAsync` not used for plain UI state | `page.WaitForFunctionAsync("() => ...")` for visible/text checks | minor |
| Deprecated APIs removed | `page.WaitForNavigationAsync(...)` in code | major |
| Positive matchers preferred over `.Not` | `Not.ToBeVisibleAsync()` where `ToBeHiddenAsync()` exists | nit |
| `Exact = true` set for ambiguous text/role names | `GetByText("Submit")` matching multiple labels (`Submit Order`, `Submitting…`) | minor |
| Auth via `StorageState`, not per-test login | Every test calls `loginPage.SignInAsync(...)` | major |
| `ExpectLoadedAsync()` exists on every page object | No landmark assertion method | minor |
| Tests inherit `PageTest` / project `BaseTest` — no manual `Playwright.CreateAsync` | Test class owns its Playwright/browser lifecycle | major |
| Browser/context lifecycle per worker, not per test, when project allows it | `[SetUp]` re-launches the browser every test (slow) | minor |
| Allure `[AllureStep]` used for non-trivial workflows | A test with 12 actions and no step labels | nit |

## Selenium .NET smells

| Check | Bad sign | Severity |
|---|---|---|
| All page objects inherit `BasePage` | Pages calling `_driver.FindElement(...)` directly without a base abstraction | major |
| Locator preference order (`data-test` → `id` → `css` → `class` → `xpath`) honored | XPath used where `data-test` exists | major |
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
| `FindByAccessibilityId` → `FindById` → `FindByXPath` priority honored | XPath used where a `testID` / `accessibilityIdentifier` exists | major |
| `AppiumElement` returned by accessors — no raw `IWebElement` | Method returns `IWebElement` | minor |
| `VerifyPageLoaded()` present and asserts a landmark | Missing or empty implementation | major |
| Navigation actions return the destination page object | Navigation method returns `void` | minor |
| Locator strings declared as `private const string` | Locator literals inline in action methods | minor |
| Platform branching abstracted behind a strategy / locator map | `if (Platform == "iOS") … else …` scattered across pages | major |
| App state reset between tests (`driver.ResetApp()` / fresh install / `noReset:false`) | Tests leak data into each other through shared app state | blocker |
| Capabilities loaded from `appsettings*.json`, not hardcoded in `[SetUp]` | `new AppiumOptions { … }` literal `deviceName = "Pixel_6"` in base | major |
| Gestures via W3C Actions / `ExecuteScript("mobile: ...")` (Appium 2.x) | Deprecated `TouchAction` / `MultiTouchAction` calls | major |
| No `Thread.Sleep` between gestures | `Thread.Sleep(1500)` after a swipe waiting for animation | blocker |
| Test names describe user behavior on device | `Screen1Test`, `TapButton2` | minor |

## Good signals (.NET)

Code that looks well-written in this stack tends to share these traits:

- Every page object inherits a thin base (`BasePage` / `BaseAppiumPage`) with one synchronization helper
- Locators are `private readonly ILocator` fields (Playwright) or `private static readonly By` (Selenium) — not magic strings
- One `[Test]` per behavior with descriptive name (`Should_SignIn_When_CredentialsValid`), no `[Order(...)]`
- Driver / Playwright lifecycle owned by `BaseTest` via a factory with `AsyncLocal` or per-worker fixtures — parallel-safe
- `WebDriverWait` + `ExpectedConditions` (Selenium) or Playwright auto-waits — no `Thread.Sleep`/`Task.Delay` for UI sync
- Multi-step flows live in a sub-folder with each step returning the next page
- Reusable components (cards, rows) take a parent `ILocator` / `IWebElement` and query inside it
- `[TestCase]` / `[TestCaseSource]` for parameterization; failure message identifies the failing case
- Constructor injection — no `Driver.Current` / static mutable state
- Nullable reference types enabled; no scattered `!`-bangs
- Allure `[AllureStep]` annotations on non-trivial workflows for human-readable reports

## Always-flag anti-patterns

- **Test that asserts nothing.** A `[Test]` ending after a `ClickAsync()` with no `Expect`/`Assert` is not a test.
- **Page object that asserts.** Move every `Assert.*` / `Expect(...)` out of the POM and into the test.
- **`Thread.Sleep` / `Task.Delay` for UI sync.** Always a blocker, regardless of duration.
- **`.Result` / `.Wait()` / `.GetAwaiter().GetResult()`.** Causes deadlocks under NUnit + Playwright. Always async.
- **`async void`** outside event handlers — exceptions escape and crash the runner.
- **Brittle locator chain.** `Page.Locator("div > div > span:nth-child(3) > a")` will break on the next DOM tweak.
- **Login-in-every-test.** Use `StorageState` (Playwright), a seeded session (Selenium), or a token-injecting `[OneTimeSetUp]`.
- **`try/catch` wrapping the whole `[Test]` body.** Hides failures. Cleanup belongs in `[TearDown]`.
- **`PageFactory` + explicit `FindElement` mixed.** Pick one (prefer explicit; `PageFactory` is deprecated).
- **Shared static `IWebDriver`** across tests. Breaks parallel execution.
- **Comments restating what the code does** (`// click login`). Comment the *why*.

## Procedure

1. Identify the **stack** (Playwright / Selenium / Appium) from imports and file location.
2. Read the file end-to-end before writing findings — context matters for severity.
3. Walk the cross-stack list, then the stack-specific list.
4. For each finding, capture: file path + line, issue, one-sentence suggested fix.
5. **Do not rewrite the code.** Hand off to the matching generator if the user asks for a rewrite.

## Handoffs

- Need to rewrite → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, or `qa/dotnet/skills/ui-test-author/appium`
- Architecture is the real problem (not the code) → `qa/dotnet/skills/page-object-architect`
- Test data shape is wrong → `qa/dotnet/skills/test-data-builder`
- API tests in the same PR → `qa/dotnet/skills/api-test-author/reviewer`
- Allure reporting questions → `qa/dotnet/skills/allure-reporting`
