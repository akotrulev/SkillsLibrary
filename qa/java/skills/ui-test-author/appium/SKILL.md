---
name: ui-tests-appium
description: Use when the user asks to scaffold a Java + Appium 3 (java-client 11) page object or TestNG mobile UI test, following the base-page / driver-factory / TestNG pattern. Triggers: "create an Appium page object for X in Java", "add a Java mobile page for screen Y", "write an Appium TestNG test for Z", "swipe / WebView / failure evidence in Appium Java". Do NOT use for exploring a live screen (`qa-java:mobile-screen-explorer`) or OS-surface features (`qa-java:mobile-native-features`).
---

# QA — Appium Java Page Object & Test Generator

Scaffolds Appium page objects and TestNG mobile UI tests in Java, mirroring the .NET and TypeScript siblings. A thin `BaseAppiumPage` with `WebDriverWait`, a per-platform test-id finder, scoped components that re-resolve on every call, typed navigation, and one driver per test class. The compilable reference is `assets/`.

## Versions

| Artifact | Primary | Supported |
|---|---|---|
| `io.appium:java-client` | **11.0.0** | 10.x |
| `org.seleniumhq.selenium:selenium-support` | ≥ 4.50 (asset pins 4.51.0) | 4.42–4.49 with java-client 10.1 |
| Appium server | **3.8.0** | 2.19 (frozen) |
| `appium-uiautomator2-driver` / `appium-xcuitest-driver` | 8.x / 12.x | 4.x / 9.x |
| TestNG · AssertJ · `allure-testng` | 7.12.0 · 3.27.7 · **3.0.0** | — |
| Java | 21 | 17 minimum |

- **Detect the project's lane first** (`java-client` in `build.gradle.kts` or `pom.xml`, `appium -v`) and keep it. java-client 11 needs Appium 3, so a project on a device cloud that still runs Appium 2 stays on 10.x (`device-cloud` says how to check). Everything below holds on 10.x except the three differences in the next list.
- **`AppiumDriver` is no longer a `RemoteWebDriver`** in 11: it extends `AppiumRemoteWebDriver`, and elements are `AppiumWebElement`. Code typed against `WebDriver` and `WebElement` needs no change. A `RemoteWebDriver` cast or parameter breaks; `SeleniumBridge.asRemoteWebDriver(driver)` from the optional `java-client-selenium-bridge` artifact is the way out.
- **`selenium-support` is no longer pulled in.** java-client 11 depends on `selenium-api` only, so `WebDriverWait` and `ExpectedConditions` need `selenium-support` declared.
- `TouchAction`, `MultiTouchAction` and `io.appium.java_client.touch.*` are removed; use W3C `PointerInput` or a `mobile:` gesture. `PageFactory.initElements(driver, page)` is gone too, and these pages do not use a page factory at all.
- **Migrating a 10.x project:** run the OpenRewrite recipe `io.appium.java_client.MigrateToV11` **before** raising the version (it fixes most imports), then `FindV11Breakages` to mark the rest. Driver methods such as `installApp` and `lockDevice` now call only `mobile:` extensions, so an `UnsupportedCommandException` is no longer swallowed.
- Capabilities go through `UiAutomator2Options` (Android) and `XCUITestOptions` (iOS); `MobileCapabilityType`, `MobileBy` and `MobileElement` are long gone.

## When to use

- New page object under `src/main/java/pom/mobile/`, a scoped component (list row, card, sheet), or a TestNG test under `src/test/java/`
- Gestures, WebView switching, app state or failure evidence in an Appium Java suite

## When NOT to use

- Appium .NET → `qa/dotnet/skills/ui-test-author/appium`; TypeScript → `qa/typescript/skills/ui-test-author/appium`
- Selenium / web → `qa/java/skills/ui-test-author/selenium` or `…/playwright`
- Reviewing an existing page object → `qa/java/skills/ui-test-author/review`
- Designing the whole POM architecture → `qa/java/skills/page-object-design`

## Inputs needed

1. **Screen name** (PascalCase) and **platform** — Android, iOS or both
2. **Elements** — name plus the ladder rung from `mobile-screen-explorer`
3. **Landmark element** for `verifyPageLoaded`
4. **Actions** and whether each navigates, plus the destination pages

## The assets

`assets/` is one runnable Gradle project (package `com.example.mobiletests`); copy it, do not retype it.

| File | Holds |
|---|---|
| `build.gradle.kts`, `settings.gradle.kts`, `testng.xml` | Exact pins, `selenium-support`, allure-java 3.0, `parallel="classes"` |
| `AppiumDriverFactory.java` | One `AppiumDriver` per call from env (`PLATFORM`, `DEVICE_NAME`, `APP_PATH`, `PLATFORM_VERSION`, `APPIUM_URL`); the Android capabilities set `appium:settings[disableIdLocatorAutocompletion]` |
| `Env.java` | The one `required(name)` helper |
| `BaseMobileTest.java` | Driver per class, the recording per test and, on failure, a screenshot, page source, device log and the recording; see `qa/java/skills/evidence-capture/references/appium.md` |
| `BaseAppiumPage.java` | `testId` and the other ladder finders, `isTestIdVisible`, the abstract `verifyPageLoaded` |
| `LoginPage.java`, `OrdersPage.java` | Screens; `signIn` returns the destination |
| `OrderRow.java` | A scoped component: a row key, re-resolved on every call |
| `OrdersTest.java` | One test |

## Locator ladder

A React Native `testID` is the iOS `accessibilityIdentifier` (the element's `name`) and the Android `resource-id`. The accessibility label (`content-desc`) is screen-reader text, never a test id.

| Rung | iOS | Android |
|---|---|---|
| 1 — the test id | `AppiumBy.accessibilityId("Login.Submit")` | `AppiumBy.id("Login.Submit")` |
| 2 — a native query | `AppiumBy.iOSNsPredicateString` · `AppiumBy.iOSClassChain` | `AppiumBy.androidUIAutomator` |
| 3 — XPath | last resort | last resort |

- `BaseAppiumPage.testId` picks the rung-1 form for the running platform, so a page has one accessor per element on both platforms. `byContentDescription` is the Android `accessibilityId` lookup for an app that exposes only a `content-desc`.
- Android prefixes every `id` lookup with `<package>:id/`. A React Native or Compose `testTag` id has no prefix, so the capability `appium:settings[disableIdLocatorAutocompletion]` set to `true` switches the prefixing off (the factory sets it). Compose also needs `testTagsAsResourceId` in the app, or the `mapTestTagToResourceId` setting on driver 8.4+. A Views app whose ids carry the package leaves the setting off. Check the live page source before choosing.
- `AppiumBy.accessibilityId` on Android matches `content-desc`. It finds a test id only where developers put the id in `accessibilityLabel`, which they should not.
- `UiSelector` is secondary. Google is deprecating `UiSelector`, `UiScrollable`, `UiObject` and `UiCollection`, and the UiAutomator2 driver warns this will invalidate every `androidUIAutomator` locator. Reach for it only for a query no other rung can express.
- A working XPath proves the node exists, not that it is the final locator. Downgrade it as soon as the source exposes a stronger rung. Each XPath row goes into `missing-testids.md` (page, element, fallback in use); the code carries no marker, and the constant's name says it is a fallback (`PASSWORD_REVEAL_XPATH_FALLBACK`).

## Scoped components

A repeating row cannot be found with a bare child locator, and a held element goes stale when a RecyclerView or table view recycles its cells.

1. A component holds a **row key**, never an element. The row is found again on every call (`OrderRow.root()`).
2. Find the row by a visible key inside it, with **element-scoped finds first**: enumerate the rows with `findElements`, then read the key with `row.findElement(...)`. The ids are static; no index, no data in the locator.
3. Only when the platform can do the whole job in one query, scope there: an iOS class chain ``**/XCUIElementTypeCell[`name == "OrderRow"`]/**/XCUIElementTypeStaticText[`name == "OrderRow.Title"`]``. Mind the `UiSelector` caveat on Android.
4. Components do **not** extend `BaseAppiumPage`. They use a small set of scoped finds and have no `verifyPageLoaded`; the host page owns the landmark.
5. An Android XPath from an element starts with `.` (`.//x`); a bare `//x` can escape the element's scope.

## Gestures

| Need | Java |
|---|---|
| Tap, long press, double tap, drag, swipe, scroll | `driver.executeScript("mobile: clickGesture", Map.of("elementId", id))`; Android `mobile: longClickGesture`, `doubleClickGesture`, `dragGesture`, `swipeGesture`, `scrollGesture`; iOS `mobile: tap`, `touchAndHold`, `doubleTap`, `swipe`, `scroll` |
| A path no `mobile:` gesture covers | W3C `PointerInput` and `Sequence` through `driver.perform(List.of(sequence))` |

```java
PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
Rectangle area = carousel.getRect();
int y = area.y + area.height / 2;
Sequence swipeLeft = new Sequence(finger, 0)
        .addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), area.x + area.width * 4 / 5, y))
        .addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()))
        .addAction(finger.createPointerMove(Duration.ofMillis(600), PointerInput.Origin.viewport(), area.x + area.width / 5, y))
        .addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));
driver.perform(List.of(swipeLeft));
```

- A gesture lives in a page method named for its intent (`swipeToNextPhoto`), never in a test. The element id for a `mobile:` gesture is `((AppiumWebElement) element).getId()`.
- Compute coordinates from `element.getRect()`, never a literal. On iOS coordinates are points, not screenshot pixels.
- `scrollGesture` scrolls by a percent and returns whether more content remains; it does not stop at an element. To reach one, repeat it on a bounded wait, or use iOS `mobile: scrollToElement`.

## WebView

A hybrid app exposes more than one context. Switch by what the context is, and come back:

```java
SupportsContextSwitching contexts = (SupportsContextSwitching) driver;
String webView = new WebDriverWait(driver, Duration.ofSeconds(10))
        .until(d -> contexts.getContextHandles().stream().filter(c -> c.startsWith("WEBVIEW")).findFirst().orElse(null));
contexts.context(webView);
driver.findElement(By.id("card-number")).sendKeys(card);
contexts.context("NATIVE_APP");
```

- UiAutomator2's `mobile: getContexts` lists each WebView with its pages' titles and URLs, for an app with more than one.
- If the element is missing from the native page source, check the context before the locator.
- Android WebViews need a Chromedriver that matches the WebView. Start the server with `--allow-insecure=uiautomator2:chromedriver_autodownload`, or point `appium:chromedriverExecutableDir` at a folder of drivers. A `chromedriverAutodownload` capability does not exist.

## App state between tests

`resetApp`, `closeApp` and `launchApp` are gone with the removed `/appium/app/*` routes. Use, in this order:

1. A fresh driver per class (the asset's default, with `appium:noReset` false).
2. `driver.executeScript("mobile: clearApp", Map.of("appId", id))` (`bundleId` on iOS) on an emulator or simulator.
3. `terminateApp(id)` then `activateApp(id)` on `InteractsWithApps` for a cold start.

Other removed endpoints have `mobile:` replacements that java-client 11's driver methods call for you.

## Rules

### Page object rules
- Extend `BaseAppiumPage`; pass `driver` to `super(driver)`. Pages take the driver, never a test context.
- Accessors stay private; a page exposes intent (`signIn`, `title()`) and queries (`isTestIdVisible`), never a `WebElement`.
- **One locator-constant style:** each id is `private static final String {ELEMENT}_ID` at the top of the class; a fallback is `{ELEMENT}_XPATH_FALLBACK`. Never inline a locator string in an action.
- **Locator order:** the test id, a native query, XPath. On iOS `id`, `name` and `accessibility id` are synonyms over the element's `name`.
- One class per screen; flows in a sub-package; repeating items as scoped components.
- Navigation returns the destination page; same-screen actions return `void`.
- Every page implements `verifyPageLoaded()` on its landmark. That is the only assertion in a page.
- `isTestIdVisible` returns `false` when the element is not displayed within the timeout, and rethrows anything else.
- Per-platform differences sit in the finder, never in an `if` inside an action.

### Test rules
- Extend `BaseMobileTest`; it provides `driver`. Names are `Should_X_When_Y`. Tag with `@Test(groups = ...)`.
- Assertions live in the test and use AssertJ (`assertThat(...).as(subject).isEqualTo(...)`); `assertSoftly` for several fields after one action. The one exception is the page's own `verifyPageLoaded`.
- **One expected condition per assertion — never an `OR`.** No `||`, no `anyOf`, no `"a|b"` regex. When Android and iOS show different copy, that is two platform-scoped expectations. If two outcomes are both reachable, split into one `@Test` per outcome.
- No `try`/`catch` in a test or a hook that runs a test body; expected exceptions use `assertThatThrownBy`. A catch lives only in an I/O helper that narrows one named exception (`isTestIdVisible`, `BaseMobileTest.fromDevice`).
- No `if` or loop driving an assertion; one `@Test` per data row.
- **Failures name the subject:** `.as("title of order %s", orderNumber)`.

### Waits
- `WebDriverWait` with `ExpectedConditions` (10 s) for conditions. No `Thread.sleep` anywhere, including for transitions and animations.

### Driver lifecycle
- **Instance fields and `parallel="classes"`, no `ThreadLocal` (D8).** `BaseMobileTest` owns one `AppiumDriver` per class in `@BeforeClass(alwaysRun = true)` and quits it in `@AfterClass(alwaysRun = true)`. TestNG creates one instance per class, so each class has its own driver. A `@DataProvider(parallel = true)` is banned.
- Parallel classes need one device each and unique `appium:systemPort`, `appium:mjpegServerPort` and `appium:wdaLocalPort` per session; `thread-count` never exceeds the device count.
- Never instantiate `AndroidDriver` or `IOSDriver` in a test; the factory does. The server URL is `APPIUM_URL`, never hardcoded.

### Failure evidence
`BaseMobileTest` is the only failure hook. A test adds none. What it keeps and where it lands is `evidence-capture/references/appium.md`; every Allure call is allure-java 3.0 (`Allure.attachment` with `AttachmentOptions`).

### What NOT to do
- No `driver.findElement` outside `BaseAppiumPage` and components.
- No `PageFactory`, `@FindBy` or `@AndroidFindBy`; no `TouchAction`, `resetApp` or `AppiumDriver<MobileElement>`.
- No raw `RemoteWebElement` returns; no assertions inside actions beyond the landmark.
- No business logic or API calls inside a page object.

## Generation steps

1. Confirm the screen, platforms, landmark, elements with rungs, actions and destinations.
2. For each element with no test id, record it in `missing-testids.md`; do not silently fall back to XPath.
3. Write `src/main/java/pom/mobile/<Screen>Page.java`: constants, `verifyPageLoaded`, intent actions, and a scoped component for each repeating group.
4. Stub missing destination pages; write the test with one `@Test` per scenario.
5. Outside a `Gate: none` plan task, run `./gradlew test` with `PLATFORM` set and expect zero failures. For a remote session, `curl -s http://127.0.0.1:4723/status` answers and `appium driver list --installed` lists the driver.

A visible element missing from the page source is usually an accessibility, app-state, active-app (a system alert) or native-versus-WebView problem; fix that before the locator. For doctor failures and driver questions the Appium docs tools (`mcp__appium-mcp__appium_documentation_query`, `mcp__appium-mcp__appium_skills`, on when `APPIUM_MCP_DOCS_ENABLED=true`) answer from the official docs.

## Handoffs

- Selectors on the live app → `qa/java/skills/mobile-screen-explorer`
- A class from an inventory → `qa/java/skills/mobile-screen-objects`
- POM architecture → `qa/java/skills/page-object-design`
- Test data → `qa/java/skills/test-data-builder`
- Failure evidence → `qa/java/skills/evidence-capture`
- Allure → `qa/reporting/java/skills/test-reports`
- Cloud farms → `qa/java/skills/device-cloud`
- Review → `qa/java/skills/ui-test-author/review`
