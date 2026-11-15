---
paths:
  - "**/desktop-tests/**"
  - "**/tests/desktop/**/*.ts"
  - "**/src/windows/**/*.ts"
  - "**/wdio*.desktop.conf.ts"
---

<!-- qa-typescript rules v1 (2026-11-15): desktop tests. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its WebdriverIO + Appium desktop suite. -->

# Desktop test standards (WebdriverIO + Appium 3, native macOS and Windows)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise. Electron and Tauri apps are out of scope.

- Window objects take no driver; `$` appears only in `BaseWindow` and scoped components. Ids are `private static readonly` constants, accessors are `private` and typed; a window exposes intent, never an element. *major*
- `verifyWindowLoaded()` asserts one landmark container id; it is the only assertion in a window object. No business logic or API calls there. *blocker for other assertions, else major*
- Locator ladder: the test id as `accessibility id` (`~id`: the XCTest `identifier` on macOS, the `AutomationId` on Windows), then a native query, then XPath as a named fallback with a `missing-testids.md` row. A locator on `label`, `title` or `Name` is a label locator and a fallback. *major*
- Never WinCore's `id` strategy (the `RuntimeId`, new every run). *blocker*
- `AutomationId` is unique among siblings only: lists and containers carry their own id, rows are found inside their container, and a search never starts at the desktop root. A repeating row is a scoped component re-resolved on each call. *major*
- Platform differences live in a locator map, never `if (isMac)` in an action. *major*
- Wait with `waitForDisplayed`, `waitForEnabled` or `browser.waitUntil`, with a message naming the element and the window; no `browser.pause`, including after a click or a window open. *blocker*
- A window is a scope: switch to it (`macos: listWindows`, `windows: getWindows`, `switchToWindow`) before finding an id, and return the destination's window object from the action that opens it. *major*
- Capabilities come from an env-driven `wdio.conf.ts` with the `appium:` prefix (`platformName` unprefixed); `maxInstances: 1`, because Mac2 runs one session at a time and Windows focus is exclusive. *major*
- Drivers are installed with an explicit `@version` (`mac2@4.6.1`, `wincore@3.3.2`, fallback `novawindows@1.5.0`) on Appium 3.8.0. Never the legacy Appium Windows driver or WinAppDriver. *blocker*
- Each test starts from a clean app state (a fresh session, or terminate and activate); an unsaved-work prompt is asserted, never skipped by killing the app. *blocker*
- Mocha runs under `wdio run`, never Vitest or Jest. Failure evidence (screenshot, page source) comes from the `afterTest` hook only. *major*
- Embedded WebView2 content is located by the page's `data-testid` through Playwright `connectOverCDP`, never through the UIA tree. *major*
- No credentials or app paths in source: environment variables read through one `requiredEnv`. *blocker*
