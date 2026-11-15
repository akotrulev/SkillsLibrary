---
paths:
  - "**/*DesktopTests/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-15): desktop UI. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its desktop suite. -->

# .NET desktop test standards (Appium 3 + NUnit, or FlaUI 5 on Windows)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise. Electron and Tauri apps are out of scope.

- One lane per suite: `Appium.WebDriver` 9 (macOS and Windows) or `FlaUI.UIA3` 5.0.0 (Windows only), never both in one suite. *blocker*
- A window extends `BaseWindow`; every lookup goes through its finders, never `Driver.FindElement` or `FindFirstDescendant` in a window or test. No `PageFactory`, `[FindsBy]` or `AppiumBy`. *major*
- Locator ladder: the test id (`MobileBy.AccessibilityId`: the XCTest `identifier` on macOS, the `AutomationId` on Windows; FlaUI `ByAutomationId`), then a native query, then XPath. Each is a `private const string {Element}Id` (a fallback `{Element}Fallback`), never inline; a fallback is a `missing-testids.md` row. A locator on `label`, `title` or `Name` is a label locator and a fallback. *major*
- Never the `id` strategy on Windows (WinCore's `RuntimeId`, new every run). *blocker*
- `AutomationId` is unique among siblings only: lists and containers carry their own id, rows are found inside their container, a search never starts at the desktop root (`GetDesktop()`), and a repeating row is a scoped component re-resolved on each call. *major*
- Every window overrides `VerifyWindowLoaded()` on one landmark id, its only assertion. Elements stay private: a window exposes intent methods and queries, never an `AppiumElement` or `AutomationElement`. *major*
- Platform differences live in a locator map, never an `if` on `PLATFORM` inside an action. *major*
- Waits are `BaseWindow.Wait` (`WebDriverWait`) or FlaUI's `Retry.WhileNull`, implicit wait zero; no `Thread.Sleep`, `Task.Delay` or `Wait.UntilInputIsProcessed` as a wait, including after a click or a window open. *blocker*
- A window is a scope: switch to it (`macos: listWindows`, `windows: getWindows`, `SwitchTo().Window`; FlaUI `GetAllTopLevelWindows` or `ModalWindows`) before finding an id, and return the destination's window object from the action that opens it. *major*
- One driver (or one `UIA3Automation` and `Application`) per fixture, made in `[OneTimeSetUp]` and released in `[OneTimeTearDown]`; an instance field, never static; `NumberOfTestWorkers` is 1, because Mac2 runs one session at a time and Windows focus is exclusive. *major*
- Options come from the environment through `Env.Required` (`PLATFORM`, `APP_ID`, `APP_ARGUMENTS`, `APPIUM_URL`), with the `appium:` prefix on additional options. No credentials or app paths in source. *blocker*
- Drivers are installed with an explicit `@version` (`mac2@4.6.1`, `wincore@3.3.2`, fallback `novawindows@1.5.0`) on Appium 3.8.0. Never the legacy Appium Windows driver or WinAppDriver. *blocker*
- Each test starts from a clean app state; an unsaved-work prompt is asserted, never skipped by killing the app. *blocker*
- Failure evidence (screenshot, page source or element-tree dump) comes only from `BaseDesktopTest`. *major*
- Embedded WebView2 content is located by the page's `data-testid` through Playwright `ConnectOverCDPAsync` (1.63, a unique `WEBVIEW2_USER_DATA_FOLDER` per worker), never through the UIA tree. *major*
