---
paths:
  - "**/desktop-tests/**"
  - "**/tests/desktop/**/*.ts"
  - "**/src/windows/**/*.ts"
  - "**/wdio*.desktop.conf.ts"
---

<!-- qa-typescript rules v2 (2026-11-17): desktop tests. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its desktop suite. -->

# Desktop test standards (WebdriverIO + Appium 3, native macOS and Windows)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise. Objects: `page-objects.md`. Electron and Tauri are out of scope.

- Window objects take no driver; `$` appears only in `BaseWindow` and components. Ids are `private static readonly` constants, accessors `private` and typed; `verifyWindowLoaded()` asserts one landmark container id. *major*
- Locator ladder: the test id as `accessibility id` (`~id`: XCTest `identifier` on macOS, `AutomationId` on Windows), a native query, then XPath as a named fallback with a `missing-testids.md` row. A `label`, `title` or `Name` locator is a fallback. *major*
- Never WinCore's `id` strategy (`RuntimeId`, new each run). *blocker*
- `AutomationId` is unique among siblings only: lists and containers carry their own id, rows are found inside them, and no search starts at the desktop root. A row component re-resolves its root on each call. *major*
- Wait with `waitForDisplayed`, `waitForEnabled` or `browser.waitUntil`, the message naming element and window; no `browser.pause`, even after a click or window open. *blocker*
- A window is a scope: switch to it (`macos: listWindows`, `windows: getWindows`, `switchToWindow`) before finding an id; the action that opens a window returns its object. *major*
- Capabilities come from an env-driven `wdio.conf.ts` with the `appium:` prefix (`platformName` unprefixed); `maxInstances: 1` (Mac2 runs one session; Windows focus is exclusive). *major*
- Drivers are installed with an explicit `@version` (`mac2@4.6.1`, `wincore@3.3.2`, fallback `novawindows@1.5.0`) on Appium 3.8.0. Never the legacy Appium Windows driver or WinAppDriver. *blocker*
- Each test starts from clean app state (fresh session, or terminate and activate); an unsaved-work prompt is asserted, never killed. *blocker*
- Mocha runs under `wdio run`, not Vitest or Jest. Failure evidence comes from the `afterTest` hook only. *major*
- WebView2 content is found by `data-testid` through Playwright `connectOverCDP`, never the UIA tree. *major*
- No credential or app path in source; read env through one `requiredEnv`. *blocker*
