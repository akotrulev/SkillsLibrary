---
paths:
  - "**/*{AppiumTests,MobileTests}/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): mobile UI. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its Appium suites. -->

# .NET mobile test standards (Appium)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- A screen extends `BaseAppiumPage` and takes the driver; every lookup goes through the base finders, never `Driver.FindElement`. No `PageFactory`, `[FindsBy]` or `AppiumBy`. *major*
- Locator ladder per platform: the test id (iOS `AccessibilityId`, Android `Id`), a native query, then XPath. Each is a `private const string {Element}Id` (a fallback `{Element}XPathFallback`), never inline; a fallback is a `missing-testids.md` row. *major*
- Every screen overrides `VerifyPageLoaded()` on its landmark, its only assertion. Elements stay private: a screen exposes intent methods and queries, never an `AppiumElement`. *major*
- Platform differences live in the finder or locator map, never in an `if` inside an action. *major*
- One driver per fixture, made by `AppiumDriverFactory` in `[OneTimeSetUp]` and quit in `[OneTimeTearDown]`; an instance field, never static, never `new AndroidDriver` in a test; `ParallelScope.Self`. *major*
- Parallel fixtures get a device each and unique `systemPort`, `mjpegServerPort` and `wdaLocalPort`; `NumberOfTestWorkers` never exceeds the device count. *major*
- `PLATFORM`, device, app path and `APPIUM_URL` come from the environment through the factory. A cloud app is its uploaded id, never a local path. *major*
- Waits are `BaseAppiumPage.Wait` (`WebDriverWait`), implicit wait zero; no sleep after a gesture, animation, background or injection. *blocker*
- No removed APIs (`TouchAction`, `ResetApp`, `CloseApp`, `ToggleWifi`, `SetConnectionType`, `DesiredCapabilities`): use `mobile:` commands and W3C actions. App state never leaks between tests. *major; blocker for leaked state*
- OS surfaces (permission and biometric dialogs, deep links) go through device calls and `mobile:` commands, never a screen selector; deny and reject paths are tested too. *major*
- Failure evidence comes only from `BaseMobileTest`. *major*
