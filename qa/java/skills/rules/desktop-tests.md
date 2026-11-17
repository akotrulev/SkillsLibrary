---
paths:
  - "**/desktop-tests/**/*.java"
  - "**/src/{test,integrationTest}/java/**/windows/**/*.java"
  - "**/src/main/java/**/windows/**/*.java"
  - "**/src/{test,integrationTest}/java/**/*{Window,Dialog}.java"
  - "**/src/{test,integrationTest}/java/**/DesktopDriverFactory.java"
---

<!-- qa-java rules v2 (2026-11-17): desktop tests. Installed by /qa-java:rules; edit the paths above to where this project keeps its TestNG + Appium desktop suite. -->

# Java desktop test standards (TestNG + java-client 11 + Appium 3, native macOS and Windows)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise. Electron and Tauri apps are out of scope. Window objects, their components and what they expose follow `qa-java-page-objects.md`.

- Window objects take the driver and nothing else. Ids are `private static final String` constants. *major*
- `verifyWindowLoaded()` asserts one landmark container id. *major*
- Locator ladder: the test id as `AppiumBy.accessibilityId` (the XCTest `identifier` on macOS, the `AutomationId` on Windows), then a native query, then XPath as a named `*_FALLBACK` with a `missing-testids.md` row. A locator on `label`, `title` or `Name` is a label locator and a fallback. *major*
- Never WinCore's `id` strategy (`AppiumBy.id`: the `RuntimeId`, new every run). *blocker*
- Mac2's native strategies are `predicate string` and `class chain`: send them with `driver.findElement("predicate string", …)`, never `AppiumBy.iOSNsPredicateString` or `iOSClassChain` (they send the `-ios` names). *major*
- `AutomationId` is unique among siblings only: lists and containers carry their own id, rows are found inside their container, and a search never starts at the desktop root. A repeating row is a scoped component re-resolved on each call. *major*
- Platform differences live in a locator map, never `if` on the platform inside an action. *major*
- Explicit waits only: `WebDriverWait` in the base window, with a message naming the element and the window. No `Thread.sleep`, no implicit wait, no forced click, including after a click or a window open. *blocker*
- A window is a scope: switch to it (`macos: listWindows`, `windows: getWindows`, `driver.switchTo().window(handle)`) before finding an id, and return the destination's window object from the action that opens it. *major*
- The driver comes from `DesktopDriverFactory` and `BaseDesktopTest`, never `new Mac2Driver()` or `new WindowsDriver()` in a test. Instance fields, `parallel="classes"`, `thread-count="1"`, no `ThreadLocal`, no `parallel="methods"`, no parallel `@DataProvider`: Mac2 runs one session at a time and Windows focus is exclusive. *blocker*
- Options come from environment variables through one `Env.required`, with the `appium:` prefix (`platformName` unprefixed). `WindowsOptions` hard-sets `automationName` to `Windows`: override it to `Wincore` (or `NovaWindows`), or use `BaseOptions`. *blocker*
- Drivers are installed with an explicit `@version` (`mac2@4.6.1`, `wincore@3.3.2`, fallback `novawindows@1.5.0`) on Appium 3.8.0. Never the legacy Appium Windows driver or WinAppDriver. *blocker*
- Each test starts from a clean app state (a fresh session, or terminate and activate); an unsaved-work prompt is asserted, never skipped by killing the app. *blocker*
- Failure evidence (screenshot, page source) comes from the base test's `@AfterMethod` only. *minor*
- Embedded WebView2 content is located by the page's `data-testid` through Playwright Java `connectOverCDP`, never through the UIA tree. *major*
- No credentials or app paths in source: environment variables only. *blocker*
