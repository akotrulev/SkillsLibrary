---
name: ui-tests-appium
description: Use when scaffolding a TypeScript Appium 3 (WebdriverIO) page object or mobile UI test. Triggers "write an Appium test for X". Not for exploring a live screen (mobile-screen-explorer).
disable-model-invocation: true
---

# QA — Appium TypeScript Page Object & Test Generator

Scaffolds WebdriverIO + Appium page objects and Mocha mobile UI tests in TypeScript strict mode, mirroring the Java and .NET siblings. A thin `BasePage` with accessibility-id-first finders, components that re-resolve lazily, typed navigation, and one session per worker. The compilable reference is `assets/`.

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
| `BasePage.ts` | `byTestId` and the other ladder finders, `testIdSelector` (the platform finder, the one legal platform branch), the abstract `verifyPageLoaded` |
| `LoginPage.ts`, `OrdersPage.ts` | Screens; `signIn` returns the destination |
| `OrderRow.ts` | A row component: a row key, its root re-resolved on every call through a wait condition with a timeout message |
| `OrderSeeder.ts` | The seeder: creates an order through the API and deletes what it created (its own teardown registry) |
| `orders.spec.ts` | One test: seeding and reaching the screen in `beforeEach`, deletion in `afterEach`, a linear body |
| `package.json`, `tsconfig.json`, `env.ts` | Exact pins, strict config, the one `requiredEnv` env loader |

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

## Components

WDIO 10's `$` is strict: it throws `StrictSelectorError` when a selector matches more than one element, **at every step of a chain** (`$(a).$(b)`). A repeating row therefore cannot be found with a bare child selector.

1. A component holds a **row key**, never an element. The row is found again on every call, so a recycled list cell cannot go stale.
2. Find the row by a visible key inside it, with **element-scoped finds first**: `$$('~OrderRow').findSeries(...)` enumerates the rows and `row.$('~OrderRow.Number')` reads the key within each (see `assets/OrderRow.ts`). The ids are static; no index, no data in the locator.
3. Only when the platform can do the whole job in one query, scope there: an iOS class chain ``-ios class chain:**/XCUIElementTypeCell[`name == "OrderRow"`]/**/XCUIElementTypeStaticText[`name == "OrderRow.Title"`]``. Mind the `UiSelector` caveat above on Android.
4. Components do **not** extend `BasePage`. They use `$` and `$$` through a small set of scoped finds, expose intent methods and value queries (text, a boolean, a count) but never an element, and have no `verifyPageLoaded`; the host page owns the landmark.
5. A row that may not be rendered yet is waited for with `browser.waitUntil` and a `timeoutMsg` naming the row, never found once and checked with `if (!row) throw`.
   To check every row of a result, the page exposes a query returning one column's values (`orderStatuses(): Promise<string[]>`, a `map` over `$$`); the test asserts it is not empty, then asserts the whole array in one `expect`, never `[0]` standing for the result set.
6. A native control (a picker, a switch, a segmented control) gets its own component at first use, built from its root's test id: `DatePicker.select(date)` hides the wheel or calendar gestures.
7. `$(selector, { strict: false })` opts one call out, and `strictSelectors: false` the whole config. Treat both as a smell: a selector that matches twice is a locator bug. Fix it by narrowing the selector or scoping it to a container.

## Gestures

| Need | WDIO 10 |
|---|---|
| Tap an element or coordinates | `await $('~Cart.Checkout').tap()` · `browser.tap({ x, y })` |
| Scroll an element into view | `await $('~Orders.Footer').scrollIntoView()` |
| Swipe | `await browser.swipe({ direction: 'left', scrollableElement: $('~Gallery.Carousel') })` |
| Long press, drag, pinch, zoom | `longPress()`, `dragAndDrop()`, `pinch()`, `zoom()` |
| A path no command covers | `browser.action('pointer', { parameters: { pointerType: 'touch' } }).move({ x, y }).down().up().perform()` |
| A driver gesture | `await browser.execute('mobile: swipeGesture', { elementId, direction: 'left', percent: 0.75 })` on Android; `mobile: swipe` on iOS |

`touchAction`, on `browser` and on an element, is removed in WDIO 10 and the Appium 3 server dropped the `touch/*` routes. The gesture commands take a `scrollableElement` or a direction; coordinates are device-specific, so compute any target from `element.getRect()`. On iOS coordinates are in points, not screenshot pixels.

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

## Failure evidence
`BaseTest.ts` is the only failure hook. A spec adds none. What it keeps and where it lands is `evidence-capture/references/appium.md`.

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md`, `page-objects.md`, `mobile-tests.md` and `test-data.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Generation steps

1. Confirm the screen, platforms, landmark, elements with rungs, actions and destinations.
2. For each element with no test id, record it in `missing-testids.md`; do not silently fall back to XPath.
3. Write `src/pages/mobile/<Screen>Page.ts`: constants, private accessors, `verifyPageLoaded`, intent actions, a component for each repeating group, and a control component for each native control, reusing one from `components/controls/` when it exists.
4. Stub missing destination pages; write the spec with one `it` per scenario. Data the test reads is created in `beforeEach` by a seeder and deleted in `afterEach`; reaching the screen happens in `beforeEach`; the body is the action and its assertion.
5. Run `npx wdio run wdio.conf.ts` and expect zero failures. If the service fails to start, run `appium driver list --installed`. A server run by hand answers `curl -s http://127.0.0.1:4723/status`.

A visible element missing from the page source is usually an accessibility, app-state, active-app (a system alert) or native-versus-WebView problem; fix that before the locator. For doctor failures and driver questions the Appium docs tools (`mcp__appium-mcp__appium_documentation_query`, `mcp__appium-mcp__appium_skills`, on when `APPIUM_MCP_DOCS_ENABLED=true`) answer from the official docs.

Never use `appium_generate_tests`: it records the scenario through MCP calls and emits one flat test with the
locators inline (its code templates are Java PageFactory), bypassing the screen objects. Locators come from
`mobile-screen-explorer`; the code comes from this skill's assets.
