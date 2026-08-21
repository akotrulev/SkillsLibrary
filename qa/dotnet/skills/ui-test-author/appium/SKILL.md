---
name: qa-ui-test-writer-appium-dotnet
description: Use when scaffolding a .NET (C#) + Appium 2.x page object or NUnit mobile UI test, following the BaseAppiumPage / AppiumDriverFactory pattern. Triggers "create a C# Appium page object for X", "add a .NET mobile page for screen Y", "write an Appium NUnit test for Z". Not for exploring a live screen (`mobile-screen-explorer`) or OS-surface features (`mobile-native-features`).
---

# QA — Appium .NET Page Object & Test Generator

Scaffolds Appium 2.x page objects and NUnit mobile UI tests in C#, mirroring the Java and TypeScript siblings. Uses a thin `BaseAppiumPage` with `WebDriverWait`, accessibility-id-first locators, typed return values for navigation, and an `AppiumDriverFactory` that produces one driver per test for parallel-safe runs.

> The .NET Appium client ships as the **`Appium.WebDriver`** NuGet package (namespace `OpenQA.Selenium.Appium`), built on top of Selenium 4. Its major version tracks Selenium's (8.x as of 2026). The v4→v5 jump was the big breaking change — `DesiredCapabilities` → `AppiumOptions`, `AppiumWebElement` → `AppiumElement`, generic `AndroidDriver<T>` → non-generic `AndroidDriver`. Everything below targets v5+ (verified against 8.x).

## Stack

- .NET 8, nullable reference types enabled
- **Appium .NET client** `Appium.WebDriver` 8.x (`OpenQA.Selenium.Appium`, `.Android`, `.iOS`, `.Enums`) on Selenium 4
- **Appium server** 2.x (started locally on `:4723`, or hit via Selenium Grid / a cloud provider)
- **NUnit** for tests (the global default for .NET test runners)
- **Allure NUnit** for reporting
- `AndroidDriver` / `IOSDriver` selected by capability profile (`AppiumOptions`)

## When to use

- New page object under `AppiumTests/Pages/`
- Component-level page object scoped to a parent `AppiumElement` (list row, card, sheet)
- New NUnit mobile UI test under `AppiumTests/Tests/`

## When NOT to use

- Appium Java → `qa/java/skills/ui-test-author/appium`
- Appium TypeScript / WebdriverIO → `qa/typescript/skills/ui-test-author/appium`
- Selenium / web → `qa/dotnet/skills/ui-test-author/selenium` or `qa/dotnet/skills/ui-test-author/playwright`
- Reviewing an existing page object → `qa/dotnet/skills/ui-test-author/review`
- Designing the whole POM architecture → `qa/dotnet/skills/page-object-design`

## Inputs needed

Ask only what's missing:

1. **Screen name** (PascalCase, e.g. `Login`, `Home`, `OrderConfirmation`)
2. **Platform** — Android, iOS, or both (decides which locator strategies are allowed)
3. **Elements** — for each: name + `accessibility id` (preferred), platform id, iOS predicate / Android UiAutomator selector, or XPath (last resort)
4. **Actions** — what the test will do, and whether each navigates to a different screen
5. **Landmark element** — the one element that proves the page is currently visible (used in `VerifyPageLoaded`)
6. **Next pages** — destination page object class names for navigation actions

## Locator strategy decision matrix

Pick the highest row that applies. Lower rows are progressively more brittle.

| Strategy | API | When to use | Cross-platform? |
|----------|-----|-------------|-----------------|
| Accessibility id | `AppiumBy.AccessibilityId("login-email")` | **Default.** Maps to React Native `testID`, Android `content-desc`, iOS `accessibilityIdentifier` | ✅ same id both platforms |
| Resource / native id | `By.Id("com.app:id/email")` (Android) / `AppiumBy.Id` | A stable native id exists but no accessibility id | ❌ platform-specific |
| iOS predicate | `AppiumBy.IosNsPredicateString("type == 'XCUIElementTypeButton' AND name == 'Submit'")` | iOS-only, no accessibility id | ❌ iOS only |
| iOS class chain | `AppiumBy.IosClassChain("**/XCUIElementTypeCell[`name == \"row\"`]")` | Deep iOS hierarchy traversal | ❌ iOS only |
| Android UiAutomator | `AppiumBy.AndroidUIAutomator("new UiSelector().text(\"Submit\")")` | Android-only, no accessibility id, need scroll-into-view | ❌ Android only |
| XPath | `By.XPath("//android.widget.Button[@text='Submit']")` | **Last resort.** Leave a `// TODO: replace with AccessibilityId` | ✅ but slow + fragile |

Per the Appium team, treat a working XPath as **proof the node exists, not the final locator** — use it to learn the tree, then downgrade to a native strategy (`AppiumBy.AndroidUIAutomator` / `AppiumBy.IosClassChain`) the moment the source exposes one, and drop the TODO. On iOS, `id` / `name` / `accessibility id` are synonyms over the element's `name` attribute. **Discover and verify these locators against the live app via `qa/dotnet/skills/mobile-screen-explorer` before hand-writing them**, and let `qa/dotnet/skills/mobile-screen-objects` emit the class from that inventory — this skill owns the conventions both of those defer to.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Patterns**.

## Capabilities

Capabilities are expressed via `AppiumOptions` — never `DesiredCapabilities` (removed in v4). Use the strongly-typed properties for the common ones and `AddAdditionalAppiumOption` (which namespaces vendor caps under `appium:` automatically) for the rest. Keep profiles in `AppiumTests/Capabilities/` and load them by `-p:Platform=android|ios` / env var, never hardcoded inline.

```csharp
// Android — UiAutomator2 driver
var android = new AppiumOptions
{
    AutomationName = AutomationName.AndroidUIAutomator2,   // "UiAutomator2"
    PlatformName   = "Android",
    DeviceName     = Env.DeviceName,                       // e.g. "Pixel_7_API_34"
};
android.AddAdditionalAppiumOption("appPackage", "com.example.app");
android.AddAdditionalAppiumOption("appActivity", ".MainActivity");
android.AddAdditionalAppiumOption("app", Env.AppPath);    // absolute path or cloud URL
android.AddAdditionalAppiumOption("noReset", true);
android.AddAdditionalAppiumOption("newCommandTimeout", 120);

// iOS — XCUITest driver
var ios = new AppiumOptions
{
    AutomationName = AutomationName.iOSXCUITest,           // "XCUITest"
    PlatformName   = "iOS",
    DeviceName     = "iPhone 15",
};
ios.AddAdditionalAppiumOption("platformVersion", "17.4");
ios.AddAdditionalAppiumOption("app", Env.AppPath);
ios.AddAdditionalAppiumOption("autoAcceptAlerts", true);
```

## Driver lifecycle — `AppiumDriverFactory`

One driver per test, created in `[SetUp]` and disposed in `[TearDown]`. Never instantiate `AndroidDriver` / `IOSDriver` inside a test or page. See [`assets/AppiumDriverFactory.cs`](assets/AppiumDriverFactory.cs).

```csharp
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;
using OpenQA.Selenium.Appium.Enums;
using OpenQA.Selenium.Appium.iOS;

namespace AppiumTests;

public static class AppiumDriverFactory
{
    public static AppiumDriver Create(string platform)
    {
        var serverUri = new Uri(Env.AppiumServerUrl);          // never hardcoded
        return platform.ToLowerInvariant() switch
        {
            "android" => new AndroidDriver(serverUri, AndroidOptions(), TimeSpan.FromSeconds(180)),
            "ios"     => new IOSDriver(serverUri, IosOptions(), TimeSpan.FromSeconds(180)),
            _         => throw new ArgumentException($"Unknown platform: {platform}"),
        };
    }
    // AndroidOptions() / IosOptions() build the AppiumOptions shown above.
}
```

```csharp
public abstract class BaseMobileTest
{
    protected AppiumDriver Driver = null!;

    [SetUp]
    public void StartDriver()
    {
        var platform = Env.Platform;                            // "android" | "ios"
        Driver = AppiumDriverFactory.Create(platform);
        Driver.Manage().Timeouts().ImplicitWait = TimeSpan.Zero; // explicit waits only
    }

    [TearDown]
    public void QuitDriver() => Driver?.Quit();
}
```

> Keep the implicit wait at **zero** and rely on explicit `WebDriverWait` — mixing implicit + explicit waits compounds unpredictably. Parallel runs: NUnit `[Parallelizable(ParallelScope.Fixtures)]` gives each fixture its own `Driver` instance because the field is per-fixture, not static.

## Explicit waits (no `Thread.Sleep`)

`Thread.Sleep` is a hard CLAUDE.md violation. Use `WebDriverWait` (in `BaseAppiumPage`) for the common case, or `DefaultWait<AppiumDriver>` when you need to ignore specific exceptions or tune the polling interval — and to avoid the `DotNetSeleniumExtras` dependency.

```csharp
using OpenQA.Selenium.Support.UI;

protected AppiumElement WaitForElement(By locator, int seconds = 10)
{
    var wait = new DefaultWait<AppiumDriver>(Driver)
    {
        Timeout = TimeSpan.FromSeconds(seconds),
        PollingInterval = TimeSpan.FromMilliseconds(300),
    };
    wait.IgnoreExceptionTypes(typeof(NoSuchElementException), typeof(StaleElementReferenceException));
    return wait.Until(d =>
    {
        var el = d.FindElement(locator);
        return el.Displayed ? (AppiumElement)el : null;
    })!;
}

// Wait for a condition, not an element — e.g. a spinner disappearing:
protected void WaitUntilGone(By locator, int seconds = 10)
{
    var wait = new DefaultWait<AppiumDriver>(Driver) { Timeout = TimeSpan.FromSeconds(seconds) };
    wait.Until(d => d.FindElements(locator).Count == 0);
}
```

## Gestures (W3C Actions + `mobile:` commands)

Two idioms, prefer the second when the driver supports it:

**1. Driver-native `mobile:` gesture commands (preferred).** UiAutomator2 and XCUITest expose high-level gesture endpoints via `ExecuteScript` — more reliable than hand-built coordinates because the driver computes the geometry.

```csharp
// Android (UiAutomator2): scroll a container until an element is found
Driver.ExecuteScript("mobile: scrollGesture", new Dictionary<string, object>
{
    ["left"] = 100, ["top"] = 300, ["width"] = 400, ["height"] = 800,
    ["direction"] = "down",
    ["percent"] = 3.0,
});

// Android: swipe within an element's bounds
Driver.ExecuteScript("mobile: swipeGesture", new Dictionary<string, object>
{
    ["elementId"] = element.Id,
    ["direction"] = "left",
    ["percent"] = 0.75,
});

// Android: long press
Driver.ExecuteScript("mobile: longClickGesture", new Dictionary<string, object>
{
    ["elementId"] = element.Id,
    ["duration"] = 1500,
});

// iOS (XCUITest) equivalents: "mobile: scroll", "mobile: swipe", "mobile: pinch", "mobile: touchAndHold"
Driver.ExecuteScript("mobile: scroll", new Dictionary<string, object>
{
    ["elementId"] = list.Id,
    ["direction"] = "down",
});
```

**2. W3C Actions API (cross-platform, coordinate-based).** Use when there is no `mobile:` command for the gesture (custom multi-touch, precise drag paths). Build a touch `PointerInputDevice`, assemble an `ActionSequence`, and call `Driver.PerformActions(...)`.

```csharp
using OpenQA.Selenium.Interactions;

protected void Swipe(int startX, int startY, int endX, int endY)
{
    var finger = new PointerInputDevice(PointerKind.Touch, "finger");
    var swipe = new ActionSequence(finger);

    swipe.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, startX, startY, TimeSpan.Zero));
    swipe.AddAction(finger.CreatePointerDown(MouseButton.Touch));
    swipe.AddAction(finger.CreatePause(TimeSpan.FromMilliseconds(200)));
    swipe.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, endX, endY, TimeSpan.FromMilliseconds(600)));
    swipe.AddAction(finger.CreatePointerUp(MouseButton.Touch));

    Driver.PerformActions(new List<ActionSequence> { swipe });
}

protected void Tap(AppiumElement element)
{
    var finger = new PointerInputDevice(PointerKind.Touch, "finger");
    var tap = new ActionSequence(finger);
    tap.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport,
        element.Location.X + element.Size.Width / 2,
        element.Location.Y + element.Size.Height / 2, TimeSpan.Zero));
    tap.AddAction(finger.CreatePointerDown(MouseButton.Touch));
    tap.AddAction(finger.CreatePointerUp(MouseButton.Touch));
    Driver.PerformActions(new List<ActionSequence> { tap });
}
```

> `TouchAction` / `MultiAction` (the old `OpenQA.Selenium.Appium.MultiTouch` API) is **deprecated** — do not use it for new code. The reusable gesture helpers above belong in [`assets/GestureExtensions.cs`](assets/GestureExtensions.cs), not duplicated into each page.

## Context switching (native ↔ webview)

Hybrid apps embed a WebView. Switch context to drive the web content with web locators (CSS), then switch back to native. The driver exposes `Contexts` (all available) and `Context` (the current one).

```csharp
protected void RunInWebView(Action webActions)
{
    var native = Driver.Context;                                 // "NATIVE_APP"
    try
    {
        var webview = new DefaultWait<AppiumDriver>(Driver) { Timeout = TimeSpan.FromSeconds(10) }
            .Until(d => d.Contexts.FirstOrDefault(c => c.StartsWith("WEBVIEW")))
            ?? throw new InvalidOperationException("No WEBVIEW context became available.");

        Driver.Context = webview;                                // switch in
        webActions();                                            // CSS selectors valid here
    }
    finally
    {
        Driver.Context = native;                                 // always switch back
    }
}

// Usage in a hybrid page object:
public void AcceptCookiesInWebView() => RunInWebView(() =>
    Driver.FindElement(By.CssSelector("#cookie-accept")).Click());
```

> Don't assume `Contexts` is populated immediately — the WebView is created asynchronously; **wait** for the `WEBVIEW*` context to appear (above) rather than reading `Contexts` once. On Android, ChromeDriver must match the WebView's Chromium version (or set `chromedriverAutodownload=true` in caps).

### Test — `AppiumTests/Tests/{Name}Test.cs`

```csharp
using AppiumTests.Pages;
using Allure.NUnit.Attributes;
using NUnit.Framework;

namespace AppiumTests.Tests;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public class AuthenticationTest : BaseMobileTest
{
    [Test]
    [Category("Smoke")]
    [AllureStory("Successful login from cold start")]
    public void Should_LandOnHome_When_CredentialsAreValid()
    {
        var login = new LoginPage(Driver);
        login.VerifyPageLoaded();

        var home = login.Login(Seed.Users[0], Seed.Password);
        home.VerifyPageLoaded();

        Assert.That(home.ProfileAvatar().Displayed, Is.True,
            "Profile avatar not visible after login.");
    }
}
```

`BaseMobileTest` owns the per-test `AppiumDriver` via `AppiumDriverFactory` (`[SetUp]` to start, `[TearDown]` to quit). Capabilities come from `Env` (env vars / `-p:Platform=`), never hardcoded.

## Rules

### Page object rules
- Always extend `BaseAppiumPage`; pass `driver` to `base(driver)`. Override `VerifyPageLoaded()`.
- Element accessors return `AppiumElement` (or `IReadOnlyList<AppiumElement>`) — keep them one-liners
- **Locator preference order**: `AppiumBy.AccessibilityId` → `By.Id` (resource-id) → `AppiumBy.IosNsPredicateString` / `AppiumBy.AndroidUIAutomator` → `By.XPath` (last resort, leave a `// TODO`). See the decision matrix.
- **Locator constants** — declare each as `private const string {Element}Id` at the top of the class. Never inline a locator string inside an action method.
- One class per screen; multi-step flows live in a sub-namespace
- Reusable components take a parent `AppiumElement` and query inside it
- Navigation methods return the next page object; same-screen actions return `void`
- **Every page object must override `VerifyPageLoaded()`** asserting the landmark element is displayed
- Method naming describes user intent (`Login`, `TapPrimaryAction`, `EnterEmail`), not Appium mechanics

### Test rules
- Extend `BaseMobileTest` — it provides the per-test `AppiumDriver Driver` and any shared seed data
- Test method names describe behavior: `Should_LandOnHome_When_CredentialsAreValid`, `Should_ShowErrorBanner_When_UserLocked`
- Use `[Category("Smoke" | "Regression" | ...)]` to enable selective runs
- Assertions live in the test class, **never** inside page methods (except the `VerifyPageLoaded()` landmark assertion)
- One logical assertion per test; use NUnit `Assert.Multiple` only when verifying one behavior across several fields after a single user action
- **One expected condition per assertion — never an `OR`.** `Assert.That(banner.Text, Is.EqualTo("Saved"))`, never `Is.EqualTo("Saved").Or.EqualTo("Success")`, `Is.AnyOf(...)`, `Does.Match("Saved|Success")`, or a `||` inside the condition. The rule covers label text, element counts, screen landmarks, attribute values, and displayed/enabled state alike — and applies per platform: when Android and iOS legitimately show different copy, that is two platform-scoped expectations, never one `OR`. If both outcomes are genuinely reachable on one platform the test does not know what the app should do — split it into one `[Test]` per expected outcome, parameterize with `[TestCase]`, or pin down the correct behavior. The only exception is an explicit instruction to accept more than one value; record that instruction in a comment on the assertion.
- **No `try`/`catch` in a test — and none in `[TearDown]`.** An unexpected exception must reach NUnit; an expected one is asserted with `Assert.Throws<T>`, which is an assertion, not error handling. Anything the test created is tracked and deleted in `[TearDown]` with no catch — a cleanup that fails should fail loudly rather than leak state into the next run. The suite's only catches live in **I/O helpers where narrowing one named exception is the contract** — an `IsDisplayed(By)` probe converting `NoSuchElementException` into `false`, a driver-quit helper — never a blanket `catch (Exception)`, and never a catch that lets a failed action continue into the assertions.
- **Failures name the subject.** `Assert.That(banner.Text, Is.EqualTo("Saved"), $"success banner after saving order {orderId}")`. A UI failure reported as `Expected: "Saved" But was: ""` with no subject is indistinguishable from a locator that matched the wrong element.
- No conditional logic in tests — use `[TestCase]` / `[TestCaseSource]` parameterization

### Waits
- Default 10s `WebDriverWait` baked into `BaseAppiumPage`; `DefaultWait<AppiumDriver>` for tuned polling / ignored exceptions
- Keep `ImplicitWait = TimeSpan.Zero` — explicit waits only; never mix the two
- **No `Thread.Sleep`** anywhere — including for screen transitions, animations, or WebView creation; wait on a condition

### Capabilities & driver lifecycle
- Capabilities via `AppiumOptions` + `AddAdditionalAppiumOption` — never `DesiredCapabilities`
- Always go through `AppiumDriverFactory.Create(platform)` — never `new AndroidDriver(...)` / `new IOSDriver(...)` in a test or page
- Platform selected by `Env.Platform` (`-p:Platform=android|ios` / env var); profiles in `AppiumTests/Capabilities/`
- One driver per test; dispose in `[TearDown]`. The Appium server URL comes from `Env.AppiumServerUrl` — never hardcoded

### Gestures & contexts
- Prefer `mobile:` gesture commands (`ExecuteScript`) over hand-built coordinates; fall back to W3C `PointerInputDevice` / `ActionSequence` / `PerformActions`
- **No deprecated `TouchAction` / `MultiAction`**
- Context switching always restores the native context in a `finally`; wait for the `WEBVIEW*` context to appear before switching

## What NOT to do

- No `Thread.Sleep` / arbitrary delays — `WebDriverWait` / `DefaultWait` on a condition
- No `Driver.FindElement(...)` outside `BaseAppiumPage` / a component scoped to its parent
- No raw `IWebElement` returns — `AppiumElement` is the contract
- No locator strings inline in actions — promote to a `private const string`
- No `DesiredCapabilities` — `AppiumOptions` only (removed in client v4)
- No deprecated `TouchAction` / `MultiAction` — W3C Actions or `mobile:` commands
- No mixing implicit + explicit waits — keep `ImplicitWait` at zero
- No assertions inside actions — assertions live in `VerifyPageLoaded()` and in test methods, never inside `Tap*` / `Enter*` actions
- No `OR` in any assertion — no `.Or.`, no `Is.AnyOf(...)`, no `||` inside `Assert.That`, no `Does.Match("a|b")` alternation, and no OR-ing Android and iOS copy into one expectation. One expected value per assertion (see Test rules)
- No `try`/`catch` in a `[Test]` or `[TearDown]` — expected exceptions use `Assert.Throws<T>`; catches live only in I/O helpers narrowing one named exception (see Test rules)
- No multi-screen page objects — one class per screen. Tabs/sheets → their own component or sub-page.
- No business logic / API calls inside a page object — page objects model the screen, not the workflow
- No hardcoded device names, app paths, or server URLs — go through `Env` / `AppiumOptions`
- No static mutable `AppiumDriver` — per-fixture instance field, so parallel fixtures stay isolated

## Generation steps

1. Confirm the **screen name**, **platform(s)**, **landmark element**, and the list of **elements + actions** with the user.
2. For every element: capture the `accessibility id` (preferred) or platform resource-id. Flag any element that has neither — those become predicate / UiAutomator / XPath locators with a `// TODO` to replace once the app exposes a stable `testID`.
3. For every action that navigates: confirm the **destination page** class name (and stub it if it doesn't exist).
4. Generate `AppiumTests/Pages/{ScreenName}Page.cs`:
   - One `private const string` per element
   - Constructor passes `driver` to `base(driver)`
   - `VerifyPageLoaded()` asserts the landmark element is displayed
   - One action method per user-intent action, returning `void` or the destination `*Page` type
   - One query method per piece of data the test needs to read
5. If a destination page doesn't exist yet, create a stub or recursively generate it.
6. Generate the test class extending `BaseMobileTest`; one `[Test]` per scenario, with assertions on user-visible outcomes.
7. Run `dotnet test AppiumTests/AppiumTests.csproj -p:Platform=android` (or `ios`) — expect 0 failures. If the Appium server isn't reachable, check `Env.AppiumServerUrl`, that `appium server` is running (`curl -s http://127.0.0.1:4723/status` succeeds), and that the server log's `Available drivers:` line lists your driver (`uiautomator2` / `xcuitest`; `appium driver list --installed`).

> **A test that can't find a visible element is usually not a locator bug.** Per the Appium team, an element absent from page source is most often an accessibility, app-state, active-app (system alert/overlay), or native-vs-WebView context problem — fix that before rewriting the selector. For environment/doctor failures and driver-specific locator questions, the `@appium/mcp-documentation` server (`appium_skills`, `appium_documentation_query`) answers authoritatively; prefer it over community forums.

## Handoffs

- Discovering / verifying locators on the live app → `qa/dotnet/skills/mobile-screen-explorer`
- Emitting / updating the page object from a discovered inventory → `qa/dotnet/skills/mobile-screen-objects`
- Architecting the POM structure (sub-namespaces, base classes, capabilities) → `qa/dotnet/skills/page-object-design`
- Test data builders → `qa/dotnet/skills/test-data-builder`
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/review`
- Authoring the test that uses this page object → `qa/manual/test-case-writer`
- Allure reporting → `qa/reporting/dotnet/skills/test-reports`

## Cross-references

- Java sibling (TestNG + `io.appium:java-client`) → `qa/java/skills/ui-test-author/appium`
- TypeScript sibling (WebdriverIO + `@wdio/appium-service`) → `qa/typescript/skills/ui-test-author/appium`
- Web UI (.NET) → `qa/dotnet/skills/ui-test-author/selenium`, `qa/dotnet/skills/ui-test-author/playwright`
- Cloud device grid (BrowserStack / Sauce / Device Farm) → `qa/dotnet/skills/browser-cloud-setup` (Step 2)
- Network capture for non-Playwright stacks → `qa/dotnet/skills/network-mocking`
