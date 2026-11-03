---
paths:
  - "**/{mobile-tests,.maestro}/**"
  - "**/tests/mobile/**/*.ts"
  - "**/test/specs/**/*.ts"
  - "**/src/pages/mobile/**/*.ts"
  - "**/wdio*.conf.ts"
---

<!-- qa-typescript rules v1 (2026-11-03): mobile tests. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its WebdriverIO/Appium or Maestro suite. -->

# Mobile test standards (WebdriverIO + Appium, Maestro)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Screen objects take no driver; `$` appears only in `BasePage` and scoped components. Ids are `private static readonly` constants, accessors are `private` and typed; a screen exposes intent, never an element. *major*
- `verifyPageLoaded()` asserts the landmark; it is the only assertion in a screen object. No business logic or API calls there. *blocker for other assertions, else major*
- Locator ladder: test id per platform (iOS `~id`, Android `id=`), native query, then XPath as a named fallback with a `missing-testids.md` row. *major*
- Platform differences live in a locator map, never `if (browser.isIOS)` in an action. *major*
- A repeating row is a scoped component re-resolved on each call; never `strict: false` to silence a strict-selector error. *major*
- Wait with `waitForDisplayed`, `waitForEnabled` or `browser.waitUntil`; no `browser.pause`, including between gestures. *blocker*
- Capabilities come from an env-driven `wdio.conf.ts` with the `appium:` prefix; the appium service starts the server. *major*
- No removed Appium 2 or WebdriverIO 10 calls (`driver.reset`, `resetApp`, `closeApp`, `touchAction`); clipboard content is base64. *blocker for a removed route, else major*
- Each test starts from clean app state (fresh session, `mobile: clearApp`, or terminate + activate). *blocker*
- Mocha (or Cucumber) runs under `wdio run`, never Vitest or Jest. Failure evidence comes from `BaseTest`'s hook only. *major*
- OS surfaces (permission dialogs, push, deep links, biometrics) are driven through device and `mobile:` APIs, then the effect is asserted on the app's screen. *major*
- Maestro: one flow per journey named `Should_X_When_Y.yaml` with `tags:`; each flow resets state (`launchApp`/`clearState`); test id before `text:`, never `point:`; repeated steps are a subflow in `subflows/`, kept out of discovery (`!subflows/**`); no fixed waits; no credentials in a flow. *blocker for waits, reset and credentials, else major*
