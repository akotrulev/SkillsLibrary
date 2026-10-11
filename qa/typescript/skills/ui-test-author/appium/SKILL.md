---
name: ui-tests-appium
description: Use when the user asks to scaffold a TypeScript + WebdriverIO 10 (Appium 3) page object or Mocha mobile UI test. Triggers: "create an Appium page object for X in TS", "add a WebdriverIO mobile page for screen Y", "write an Appium TS test for Z", "swipe / WebView / failure evidence in WDIO". Do NOT use for web UI (`qa-typescript:ui-tests-playwright`) or live-screen discovery (`qa-typescript:mobile-screen-explorer`).
---

# QA — Appium TypeScript Page Object & Test Generator

Scaffolds WebdriverIO + Appium page objects and Mocha mobile UI tests in TypeScript strict mode, mirroring the Java and .NET siblings. A thin `BasePage` with accessibility-id-first helpers, scoped components that re-resolve lazily, typed navigation, and one session per worker. The compilable reference is `assets/`.

> WebdriverIO with `@wdio/appium-service` is the TypeScript client for Appium: it starts the Appium server, takes the capabilities, and exposes `browser`, `$` and `$$` over the WebDriver protocol.

## Versions

| Artifact | Primary | Supported |
|---|---|---|
| `appium` | **3.8.0** | 2.19 (frozen) |
| `appium-uiautomator2-driver` / `appium-xcuitest-driver` | 8.7.0 / 12.17.1 | 4.x / 9.x |
| `webdriverio`, `@wdio/cli`, `@wdio/appium-service`, `@wdio/globals` | **10.0.2** | 9.x |
| `@wdio/mocha-framework` / `@wdio/types` / `@wdio/allure-reporter` | 10.0.1 | 9.x |
| `expect-webdriverio` (the required peer of `@wdio/globals`) / `@wdio/logger` | 8.0.0 / 10.0.0 | 8.x / 9.x |
| Node | 24 (WDIO 10 needs ≥ 22.19) | 22 |

- **Detect the project's lane first** (`webdriverio` major in `package.json`, `appium -v`) and keep it. WDIO 10 refuses an Appium 2 server, so a project on a device cloud that still runs Appium 2 stays on WDIO 9 (`device-cloud` says how to check).
- A WDIO 9 project differs in three places: `$` is not strict, `touchAction` still exists (never use it), and `stopRecordingScreen` takes positional arguments. Everything else here holds.
- Capabilities carry the `appium:` prefix (`'appium:automationName'`, `'appium:app'`); unprefixed `automationName` and `deviceName` select nothing in WDIO 10.
- Install the drivers once: `appium driver install uiautomator2`, `appium driver install xcuitest`, then `appium driver doctor uiautomator2`.
- Mocha (`@wdio/mocha-framework`) is the runner; Cucumber is the BDD alternative (`gherkin-step-code/references/cucumberjs-appium.md`). WDIO's runner has no Vitest framework.

## When to use

- A page object under `src/pages/mobile/`, a scoped component, or a Mocha test under `test/specs/`
- Gestures, WebView switching, app lifecycle or failure evidence in a WDIO mobile suite

## When NOT to use

- Appium .NET / Java → `qa/dotnet/skills/ui-test-author/appium` / `qa/java/skills/ui-test-author/appium`
- Web TS → `qa/typescript/skills/ui-test-author/playwright` or `…/selenium`
- Reviewing a page object → `qa/typescript/skills/ui-test-author/review`
- POM architecture → `qa/typescript/skills/page-object-design`

## Inputs needed

1. **Screen name** (PascalCase) and **platform** — Android, iOS or both
2. **Elements** — name plus the ladder rung from `mobile-screen-explorer`
3. **Landmark element** for `verifyPageLoaded`
4. **Actions** and whether each navigates, plus the destination pages

## The assets

`assets/` is one runnable project; copy it, do not retype it.

| File | Holds |
|---|---|
| `wdio.conf.ts` | Mocha, the `appium` service, capabilities per `PLATFORM` from env, the evidence hooks |
| `BaseTest.ts` | `beforeTest` / `afterTest`: a recording started per test, and on failure a screenshot, page source, device log and the recording; see `qa/typescript/skills/evidence-capture/references/appium.md` |
| `BasePage.ts` | `byTestId` and the other ladder helpers, `testIdSelector`, `isElementVisible`, the abstract `verifyPageLoaded` |
| `LoginPage.ts`, `OrdersPage.ts` | Screens; `signIn` returns the destination |
| `OrderRow.ts` | A scoped component: a row key, re-resolved on every call |
| `orders.spec.ts` | One test |
| `package.json`, `tsconfig.json`, `env.ts` | Exact pins, strict config, the one `requiredEnv` helper |

## Locator ladder

A React Native `testID` is the iOS `accessibilityIdentifier` (the element's `name`) and the Android `resource-id`. The accessibility label (`content-desc`) is screen-reader text, never a test id.

| Rung | iOS | Android |
|---|---|---|
| 1 — the test id | `$('~Login.Submit')` | `$('id=Login.Submit')` |
| 2 — a native query | `-ios predicate string:` · `-ios class chain:` | `android=new UiSelector()…` |
| 3 — XPath | last resort | last resort |

- `BasePage.byTestId` (and `testIdSelector` for components) pick the rung-1 form for the running platform, so a page has one accessor per element on both platforms. `byContentDescription` is the Android `~` lookup for an app that exposes only a `content-desc`.
- Android prefixes every `id` lookup with `<package>:id/`. A React Native or Compose `testTag` id has no prefix, so the capability `'appium:settings[disableIdLocatorAutocompletion]': true` switches the prefixing off (the asset sets it). Compose also needs `testTagsAsResourceId` in the app, or the `mapTestTagToResourceId` setting on driver 8.4+. A Views app whose ids carry the package leaves the setting off. Check the live page source before choosing.
- `~id` on Android matches `content-desc`. It finds a test id only where the developers put the id in `accessibilityLabel`, which they should not; use it (`byContentDescription`) only for an app that exposes nothing else.
- `UiSelector` is secondary: Google is deprecating `UiSelector`, `UiScrollable`, `UiObject` and `UiCollection`, and the UiAutomator2 driver warns it will invalidate every `android=` locator. Reach for it only for a query no other rung can express, and plan for its removal.
- A working XPath proves the node exists, not that it is the final locator. Downgrade it as soon as the source exposes a stronger rung. Each XPath row goes into `missing-testids.md` (page, element, fallback in use); the code carries no marker, and the constant's name says it is a fallback (`PASSWORD_REVEAL_XPATH_FALLBACK`).
- Discover and verify ids on the live app through `mobile-screen-explorer`, and emit classes through `mobile-screen-objects`.

## Scoped components

WDIO 10's `$` is strict: it throws `StrictSelectorError` when a selector matches more than one element, **at every step of a chain** (`$(a).$(b)`). A repeating row therefore cannot be found with a bare child selector.

1. A component holds a **row key**, never an element. The row is found again on every call, so a recycled list cell cannot go stale.
2. Find the row by a visible key inside it, with **element-scoped finds first**: `$$('~OrderRow').findSeries(...)` enumerates the rows and `row.$('~OrderRow.Number')` reads the key within each (see `assets/OrderRow.ts`). The ids are static; no index, no data in the locator.
3. Only when the platform can do the whole job in one query, scope there: an iOS class chain ``-ios class chain:**/XCUIElementTypeCell[`name == "OrderRow"`]/**/XCUIElementTypeStaticText[`name == "OrderRow.Title"`]``. Mind the `UiSelector` caveat above on Android.
4. Components do **not** extend `BasePage`. They use `$` and `$$` through a small set of scoped finds, and have no `verifyPageLoaded`; the host page owns the landmark.
5. `$(selector, { strict: false })` opts one call out, and `strictSelectors: false` the whole config. Treat both as a smell: a selector that matches twice is a locator bug. Fix it by narrowing the selector or scoping it to a container.

## Gestures

| Need | WDIO 10 |
|---|---|
| Tap an element or coordinates | `await $('~Cart.Checkout').tap()` · `browser.tap({ x, y })` |
| Scroll an element into view | `await $('~Orders.Footer').scrollIntoView()` |
| Swipe | `await browser.swipe({ direction: 'left', scrollableElement: $('~Gallery.Carousel') })` |
| Long press, drag, pinch, zoom | `longPress()`, `dragAndDrop()`, `pinch()`, `zoom()` |
| A path no helper covers | `browser.action('pointer', { parameters: { pointerType: 'touch' } }).move({ x, y }).down().up().perform()` |
| A driver gesture | `await browser.execute('mobile: swipeGesture', { elementId, direction: 'left', percent: 0.75 })` on Android; `mobile: swipe` on iOS |

`touchAction`, on `browser` and on an element, is removed in WDIO 10 and the Appium 3 server dropped the `touch/*` routes. The helpers take a `scrollableElement` or a direction; coordinates are device-specific, so compute any target from `element.getRect()`. On iOS coordinates are in points, not screenshot pixels.

## WebView

A hybrid app exposes more than one context. Read them, switch by what the page says, and come back:

```ts
await browser.switchContext({ title: 'Checkout' });
await $('#card-number').setValue(card);
await browser.switchContext('NATIVE_APP');
```

- `switchContext({ title })` and `switchContext({ url })` take a string or a regular expression, match inside the app under test, and on Android select the right page of the WebView. `browser.getContexts()` lists the candidates with their titles and URLs.
- If the element is missing from the native page source, check the context before the locator.
- Android WebViews need a Chromedriver that matches the WebView. Start the server with `--allow-insecure=uiautomator2:chromedriver_autodownload`, or point `appium:chromedriverExecutableDir` at a folder of drivers. The capability does not exist.

## App state between tests

The old `reset` and `resetApp` calls are gone with the removed `/appium/app/*` routes. Use, in this order:

1. A fresh session per spec file (the default, with `appium:noReset: false`).
2. `await browser.execute('mobile: clearApp', { appId })` (`bundleId` on iOS) on an emulator or simulator.
3. `terminateApp` then `activateApp` for a cold start.

Other removed endpoints have `mobile:` replacements: `mobile: backgroundApp`, `mobile: getClipboard` and `mobile: setClipboard` (base64), `mobile: lock`, `mobile: setConnectivity`, `mobile: pressKey`, `mobile: startActivity`. WDIO's wrappers call them; do not hand-roll HTTP.

## Rules

### Page object rules
- Extend `BasePage`; pages take no driver (WDIO's `browser` is implicit); `$` appears only in `BasePage` and in components.
- Accessors return `ChainablePromiseElement`, are `private`, and each id is a `private static readonly` constant at the top of the class. A page exposes intent (`signIn`, `title()`), never an element.
- One class per screen; flows in a sub-folder; repeating items as scoped components.
- Navigation returns the destination page; same-screen actions return `Promise<void>`.
- Every page implements `verifyPageLoaded()` on its landmark. That is the only assertion in a page.
- `isElementVisible` returns `false` when the element is not displayed within the timeout, and rethrows anything else.
- Per-platform differences sit in a locator map in the page, never an `if (browser.isIOS)` inside an action.

### Test rules
- Mocha `describe` / `it`; no inheritance. Names are `Should_X_When_Y`.
- Tag by file path or `--mochaOpts.grep "@smoke"`.
- Assertions live in the test. An element matcher carries a message: `toBeDisplayed({ message: '…' })`. A value matcher takes none, so the subject goes into the value: `expect({ orderNumber, title }).toEqual({ orderNumber, title: expected })`.
- **One expected condition per assertion — never an `OR`.** No `||`, no `/a|b/`, no `expect([a, b]).toContain(x)`. When Android and iOS show different copy, that is two platform-scoped expectations. If two outcomes are both reachable, split into one `it` per outcome.
- No `try`/`catch` in a test or a cleanup hook. Expected rejections use `await expect(promise).rejects`. A catch lives only in an I/O helper that narrows one named error (`isElementVisible`, `BaseTest.tolerate`).
- No `if` or loop driving an assertion; one `it` per data row.
- Tests and hooks are `async`, every promise awaited.

### Waits
- WDIO auto-waits element commands. For a condition use `waitForDisplayed`, `waitForEnabled` or `browser.waitUntil(...)`.
- No `browser.pause(n)` and no `setTimeout` for synchronization, including for transitions and animations.

### Session
- Capabilities live in `wdio.conf.ts`, from env (`PLATFORM`, `DEVICE_NAME`, `APP_PATH`); no hardcoded device, path or URL.
- The `appium` service starts the server; never start one by hand. A device cloud swaps the service (`device-cloud`).
- `appium:settings[<name>]` capabilities start a session with a setting already set.

### Failure evidence
`BaseTest.ts` is the only failure hook. A spec adds none. What it keeps and where it lands is `evidence-capture/references/appium.md`.

### What NOT to do
- No `browser.$` outside `BasePage` and components; no assertions in page actions beyond the landmark.
- No `any`, no casts such as `as unknown as ChainablePromiseElement`.
- No shared mutable state on pages; instantiate per test.
- No business logic or API calls in a page object.
- No `setTimeout`, `browser.pause`, `touchAction`, `resetApp` or `driver.reset()`.

## Generation steps

1. Confirm the screen, platforms, landmark, elements with rungs, actions and destinations.
2. For each element with no test id, record it in `missing-testids.md`; do not silently fall back to XPath.
3. Write `src/pages/mobile/<Screen>Page.ts`: constants, private accessors, `verifyPageLoaded`, intent actions, and a scoped component for each repeating group.
4. Stub missing destination pages; write the spec with one `it` per scenario.
5. Outside a `Gate: none` plan task, run `npx wdio run wdio.conf.ts` and expect zero failures. If the service fails to start, run `appium driver list --installed`. A server run by hand answers `curl -s http://127.0.0.1:4723/status`.

A visible element missing from the page source is usually an accessibility, app-state, active-app (a system alert) or native-versus-WebView problem; fix that before the locator. For doctor failures and driver questions the Appium docs tools (`mcp__appium-mcp__appium_documentation_query`, `mcp__appium-mcp__appium_skills`, on when `APPIUM_MCP_DOCS_ENABLED=true`) answer from the official docs.

## Handoffs

- Selectors on the live app → `qa/typescript/skills/mobile-screen-explorer`
- A class from an inventory → `qa/typescript/skills/mobile-screen-objects`
- POM architecture → `qa/typescript/skills/page-object-design`
- Test data → `qa/typescript/skills/test-data-builder`
- Failure evidence → `qa/typescript/skills/evidence-capture`
- Allure → `qa/reporting/typescript/skills/test-reports`
- Cloud farms → `qa/typescript/skills/device-cloud`
- Review → `qa/typescript/skills/ui-test-author/review`
