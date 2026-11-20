---
paths:
  - "**/desktop-tests/**/*.java"
  - "**/src/{test,integrationTest}/java/**/windows/**/*.java"
  - "**/src/main/java/**/windows/**/*.java"
  - "**/src/{test,integrationTest}/java/**/*{Window,Dialog}.java"
  - "**/src/{test,integrationTest}/java/**/DesktopDriverFactory.java"
---

<!-- qa-java rules v2 (2026-11-17): desktop tests. Installed by /qa-java:rules; edit the paths above to where this project keeps its TestNG + Appium desktop suite. -->

# Java desktop test standards (TestNG, java-client 11, Appium 3)

Severity tags as in the core rules; the codebase wins where it consistently differs. Electron and Tauri are out of scope. Window objects follow `qa-java-page-objects.md`; recipes: `desktop-window-objects`, `desktop-screen-explorer` (Mac2 strategies), `desktop-project-setup`.

- Window objects take the driver only; ids are `private static final String` constants; `verifyWindowLoaded()` asserts one landmark container id. *major*
- Locator ladder: the test id as `AppiumBy.accessibilityId`, then a native query, then XPath as a named `*_FALLBACK` with a `missing-testids.md` row. A `label`, `title` or `Name` locator is a fallback. *major*
- WinCore's `AppiumBy.id` is the `RuntimeId`, new every run: locate by `accessibilityId`. *blocker*
- `AutomationId` is unique among siblings only: lists and containers carry their own id, rows are found inside them, a search starts at a window. *major*
- Explicit waits only: `WebDriverWait` in the base window, with a message naming the element and window. No `Thread.sleep`, implicit wait or forced click. *blocker*
- Switch to a window before finding an id; the action that opens one returns its window object. *major*
- The driver comes from `DesktopDriverFactory` and `BaseDesktopTest`: instance fields, `parallel="classes"`, `thread-count="1"`, no `ThreadLocal`, no parallel `@DataProvider` (Mac2 runs one session at a time; Windows focus is exclusive). *blocker*
- Options come from environment variables through one `Env.required`, `appium:`-prefixed; `WindowsOptions` hard-sets `automationName` to `Windows`, so set `Wincore` or use `BaseOptions`. *blocker*
- Drivers are installed with an explicit `@version`, never the legacy Appium Windows driver or WinAppDriver. *blocker*
- Each test starts from a clean app state; an unsaved-work prompt is asserted, not skipped by killing the app. *blocker*
- WebView2 content is found by `data-testid` through Playwright Java `connectOverCDP`, never the UIA tree. *major*
