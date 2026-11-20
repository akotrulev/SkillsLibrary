---
paths:
  - "**/*DesktopTests/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-15): desktop UI. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its desktop suite. -->

# .NET desktop test standards (Appium 3 + NUnit, or FlaUI 5 on Windows)

Severity tags as in the core rules. Electron and Tauri apps are out of scope.

- One lane per suite: `Appium.WebDriver` 9 (macOS, Windows) or `FlaUI.UIA3` 5.0.0 (Windows), not both. *blocker*
- A window extends `BaseWindow`; lookups go through its finders, never `Driver.FindElement` or `FindFirstDescendant`, `PageFactory`, `[FindsBy]` or `AppiumBy`. *major*
- Locator ladder: the test id (`MobileBy.AccessibilityId`, FlaUI `ByAutomationId`), a native query, then XPath. Each is a `private const string {Element}Id` (fallback: `{Element}Fallback`), never inline; a fallback, a `label`, `title` or `Name` locator included, is a `missing-testids.md` row. *major*
- Never the `id` strategy on Windows (`RuntimeId` changes every run). *blocker*
- `AutomationId` is unique among siblings only: containers carry their own id, rows are found inside them and re-resolved on each call, never from `GetDesktop()`. *major*
- Every window overrides `VerifyWindowLoaded()` on one landmark id, its only assertion; elements stay private, never exposed as an `AppiumElement` or `AutomationElement`. *major*
- Platform differences live in a locator map, not an `if` on `PLATFORM`. *major*
- Waits are `BaseWindow.Wait` or FlaUI's `Retry.WhileNull`, implicit wait zero; no `Thread.Sleep`, `Task.Delay` or `UntilInputIsProcessed`. *blocker*
- A window is a scope: switch to it before finding an id (`desktop-window-objects`). *major*
- One driver (or one `UIA3Automation` and `Application`) per fixture, an instance field made in `[OneTimeSetUp]` and released in `[OneTimeTearDown]`; `NumberOfTestWorkers` is 1 (one Mac2 session, exclusive Windows focus). *major*
- Options come from `Env.Required`, `appium:`-prefixed for additional options; no credentials or app paths in source. *blocker*
- Drivers install with an explicit `@version` (`desktop-project-setup`), never the legacy Appium Windows driver or WinAppDriver. *blocker*
- Each test starts from a clean app state; an unsaved-work prompt is asserted, not skipped by killing the app. *blocker*
- Failure evidence comes only from `BaseDesktopTest`. *major*
- WebView2 content is located by `data-testid` through Playwright `ConnectOverCDPAsync`, never the UIA tree. *major*
