---
name: qa-ui-test-writer-playwright-java
description: Use when the user asks to scaffold Playwright UI tests in Java — TestNG test classes, page objects, the parallel-safe BaseTest, signed-in state, locator scoping, web-first assertions, or device emulation. Triggers "write a Playwright test for X in Java", "add a Playwright Java page object for screen Y", "set up Playwright with TestNG". Do NOT use for Selenium (`qa-ui-test-writer-selenium-java`), Appium (`qa-ui-test-writer-appium-java`) or reviewing tests (`qa-ui-test-review-java`).
---

# QA — Playwright Test & Page Object Generator (Java)

Scaffolds Playwright for Java tests and page objects on **Java 21 + Gradle (Kotlin DSL) + TestNG**, with the
sync API. Every test class extends **one `BaseTest`** that is safe under TestNG `parallel="classes"`,
locators climb **one ladder** with `data-testid` first, and every check is a **web-first assertion**. The
code lives in `assets/`; the mechanics live in `references/`.

## Versions

These are the only Playwright pins in this skill. Every other file links here.

| Artifact | Version | Note |
|---|---|---|
| `com.microsoft.playwright:playwright` | **1.63.0** | Java 1.64 is not on Maven yet; stay on 1.63 until it is |
| Docker image | `mcr.microsoft.com/playwright/java:v1.63.0-noble` | The tag always equals the package version |
| `io.qameta.allure:allure-testng` | 3.0.0 | Java 17+ test JVM; `Allure.attachment(..., AttachmentOptions)` |
| `io.qameta.allure` Gradle plugin | 4.3.0 | First release that supports allure-java 3 (`allureJavaVersion.set("3.0.0")`) |
| Allure report generator | `allure-commandline` 2.46.1 | `allure.version` in the build; the cross-stack pin in `qa/cicd/ci-conventions` |
| `org.testng:testng` / `org.assertj:assertj-core` | 7.12.0 / 3.27.7 | allure-testng 3 needs TestNG ≥ 7.10 |
| `com.deque.html.axe-core:playwright` | 4.13.0 | Owned by `accessibility-testing` |

**Version lane.** Detect the project's Playwright version first and keep it — never up-level a project as a
side effect. A 1.64-only API does not compile on 1.63, and playwright.dev's Java pages already list some of
them (`setFps`, `recordVideoFps`, `getByRef`), so trust the installed version over the docs page. The 1.63
forms: **from 1.64: `child.within(parent)`** — on 1.63 write `parent.locator(child)`; `getByRef`, video fps
and screencast style have no 1.63 form. Each reference tags an API with the version it shipped in.

## Stack and layout

- Java 21 toolchain, Gradle Kotlin DSL (Maven only where the project already uses it), TestNG, AssertJ for
  non-locator values, Allure through `allure-testng`.

```
ui-tests/
├── build.gradle.kts         settings.gradle.kts     testng.xml
└── src/test/java/com/example/uitests/
    ├── support/   BaseTest.java (the one lifecycle), AuthSetup.java when signed-in classes exist
    ├── pages/     LoginPage.java, HomePage.java, components shared by several pages
    └── tests/     LoginTest.java — one test class per feature
```

The assets are flat; each `.java` file goes under `src/test/java` at its package path, and the three build
files go at the project root.

## When to use

- A new test class, page object, component object, or the `BaseTest` itself.
- A new or rewritten `build.gradle.kts`, `testng.xml`, browser install task or signed-in state.
- Scoping or fixing locators, replacing one-shot reads with web-first assertions.
- Running a class per device, viewport, colour scheme, locale or time.

## When NOT to use

- Native mobile apps → `qa/java/skills/ui-test-author/appium`
- Selenium → `qa/java/skills/ui-test-author/selenium`
- Reviewing Playwright code → `qa/java/skills/ui-test-author/review`
- Designing the page-object hierarchy → `qa/java/skills/page-object-design`
- Extracting page objects and test ids from a live URL → `qa/java/skills/page-objects-from-url`
- Screenshots, video, traces and HAR beyond the `BaseTest` defaults → `qa/java/skills/evidence-capture`
- Visual regression, accessibility scans, network mocking → `visual-regression`, `accessibility-testing`,
  `network-mocking`
- Playwright TypeScript or .NET → `qa/typescript/skills/ui-test-author/playwright`,
  `qa/dotnet/skills/ui-test-author/playwright`

## Inputs needed

1. **Feature or page** under test (`Login`, `CheckoutCart`).
2. **User journey** — the steps and the one user-visible outcome to assert.
3. **Locators** — the test id for each element, or the fallback rung and a `missing-testids.md` row.
4. **Auth** — signed out, or signed in as which role.
5. **Test data** — seeded through the API in the class's `@BeforeMethod`, or a builder.
6. **Devices and media** — which classes run on which emulated device.

## What ships with this skill

| File | Holds |
|---|---|
| [`references/lifecycle.md`](references/lifecycle.md) | Why instance fields plus `parallel="classes"`, the hook order, the hooks, environment, failure evidence, signed-in state, API seeding, install / codegen / show-trace / headed commands |
| [`references/locators.md`](references/locators.md) | The ladder, `getBy*`, `filter` / `and` / `or`, chaining from a component root, `parent.locator(child)` and the 1.64 `within()` line, `visible()`, frames, strictness, `describe()`, `addLocatorHandler`, the test-id attribute, agent-facing locators |
| [`references/assertions.md`](references/assertions.md) | The web-first set (accessible name, role, `containsClass`, URL, aria snapshots), one expected condition, the one-shot-read ban, timeouts, `waitForCondition`, subject naming without a message parameter, HTTP responses |
| [`references/emulation-and-mobile-web.md`](references/emulation-and-mobile-web.md) | Explicit device options, touch, viewport, media features, locale and geolocation, `page.clock()`, offline, and why emulation is not a device |
| [`assets/build.gradle.kts`](assets/build.gradle.kts) | The pins, Allure 3, TestNG with `testng.xml`, `PLAYWRIGHT_JAVA_SRC`, `installPlaywrightBrowsers` and a `playwright` CLI task |
| [`assets/settings.gradle.kts`](assets/settings.gradle.kts), [`assets/testng.xml`](assets/testng.xml) | The project name; the suite with `parallel="classes"` |
| [`assets/BaseTest.java`](assets/BaseTest.java) | The lifecycle: browser per class, context and page per test, `BASE_URL`, `HEADED`, `launchOptions()` / `contextOptions()`, failure evidence to Allure |
| [`assets/LoginPage.java`](assets/LoginPage.java) | A page with intent methods and a `SignInForm` component; the error scoped with `parent.locator(child)` |
| [`assets/HomePage.java`](assets/HomePage.java) | The landing page the journeys assert on |
| [`assets/LoginTest.java`](assets/LoginTest.java) | Tests with `Should_X_When_Y` names, groups, and pages built per test |

Start from the assets: copy them, rename, and keep their shape.

## Rules

### Lifecycle

- **Every test class extends the one `BaseTest`.** No test or specialised skill calls `Playwright.create()`
  or declares a second base class; a role, a device or a launch flag is an override of `contextOptions()` or
  `launchOptions()` on the class that needs it.
- **Instance fields only, and the suite runs `parallel="classes"`.** Playwright Java is not thread-safe, and
  TestNG runs all of a class's methods on one thread in that mode. Never `static Playwright` / `Browser`,
  never `ThreadLocal`, never `parallel="methods"`, never `@DataProvider(parallel = true)`.
- Every configuration method is `alwaysRun = true`, so group-filtered runs keep the hooks.
- `BASE_URL` is required: `page.navigate("/login")` and `page.request()` resolve against it. `HEADED=1` runs
  headed. Read required variables with `requiredEnv(name)`.
- Failure evidence is `BaseTest`'s: screenshot, trace and video kept only on failure, in
  `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`, attached to Allure. The order is evidence,
  then `context.close()`, then `video.saveAs` — Java's `saveAs` throws before the close.

### Locators

1. **The ladder:** `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → `getByText` →
   `getByAltText` / `getByTitle` → CSS. The first rung the element supports wins.
2. **Test ids are PascalCase dot-separated and static** — `Login.Submit`, `OrderRow`, `OrderRow.Title` — the
   format `fe-react` and `fe-blazor` generate. A row is picked by its content, never by an id that embeds a
   key, an index or a state.
3. **A fallback carries no marker in the code.** Record it in `missing-testids.md` (page, element,
   suggested id, fallback in use). The report is the contract; no `TODO`, no comment on the locator.
4. **Scope instead of picking.** A locator that matches many is narrowed by its component root,
   `parent.locator(child)`, or `filter(new Locator.FilterOptions().setHas(...) / .setHasText(...))`.
   `nth()` / `first()` only where order is the behaviour, and then the field name says so.
5. `visible()` (1.63) instead of `:visible`; `frameLocator` / `contentFrame()` for iframes;
   `addLocatorHandler` for overlays that may appear; `describe()` on every locator a test asserts on.
6. **Never assert on an `or()` locator** — it passes on either state.

### Page objects

- Locators are `private final Locator` fields built in the constructor, never methods that re-query. Tests
  reach them through accessors (`error()`), never through public fields.
- A page takes `(Page page)`. A **component** (a region reused across pages — a form, a row, a menu) takes
  its root `Locator` and builds its children from it, as `SignInForm` does.
- Methods name user intent (`signIn`, `addToCart`), never the widget (`clickButton`). An action that always
  lands on another page may return that page object; otherwise `void`.
- The page owns its URL in `goTo()`. Test classes never call `page.navigate`, `page.locator` or any other
  raw `page` method.
- **No assertions in page objects.** They expose locators; tests assert. An optional `expectLoaded()` that
  asserts one landmark is the only exception.
- Pages are built in the test class (a `@BeforeMethod` or the test), never as fields of `BaseTest`. No shared
  `BasePage` until three pages share real behaviour (`page-object-design`).

### Tests

- **Names are `Should_X_When_Y`** (`Should_ShowInvalidCredentialsError_When_PasswordIsWrong`), one test class
  per feature.
- **Groups tag the area and the tier:** `@Test(groups = {"login", "smoke"})`; `@Feature("Login")` on the
  class where the project uses Allure.
- One logical behaviour per test; every test asserts. Several assertions are fine when they check one
  behaviour.
- **Web-first assertions only** (`references/assertions.md`). No one-shot read compared later
  (`assertEquals(loc.textContent(), …)`, `assertTrue(loc.isVisible())`); `Locator` has no `getText()`.
- **One expected condition per assertion — never an `OR`**, and a regex alternation is an `OR`. Split the
  outcomes, or drive them from a `@DataProvider` (sequential).
- **Failures name the subject.** Java's `assertThat(locator)` has no message parameter, so the locator
  carries `describe("…")`. AssertJ assertions on values carry `.as(...)` with the evidence.
- **No `try` / `catch` / `finally` in a test** and none in a hook body. An expected exception is
  `assertThrows`; cleanup is the class's `@AfterMethod(alwaysRun = true)`. The only catch in the suite is
  a narrow, logged one inside an I/O helper (`BaseTest.keepScreenshot`).
- No `if` or `for` driving assertions. Tests are independent: no `dependsOnMethods` chains, no shared mutable
  state. One long journey is one test with Allure `@Step` labels.
- API responses assert the exact status with the body:
  `assertThat(created.status()).as(created.text()).isEqualTo(201)` — never `assertThat(response).isOK()`.
- No hardcoded credentials, URLs or hostnames — `BASE_URL`, `E2E_USER`, `E2E_PASSWORD`. No
  `System.out.println`; use Allure steps and the trace.

### Waiting

- No `page.waitForTimeout` and no `Thread.sleep` — in a test, a page object or a route handler (a sleep on
  the Playwright thread stops all event dispatch). Wait on a web-first assertion with a longer timeout
  (`new LocatorAssertions.IsVisibleOptions().setTimeout(...)` — there is no `AssertOptions`).
- No `NETWORKIDLE` — not as `setWaitUntil` on `navigate`, not in `waitForLoadState`. Navigate, then assert a
  landmark.
- No `locator.waitFor()` before an action that already auto-waits; no `setForce(true)` (close the overlay
  with `addLocatorHandler`, scroll, wait for the state).
- No `waitForNavigation` (deprecated); `waitForURL` or `assertThat(page).hasURL(...)`. No page-level selector
  APIs (`page.click(selector)`, `page.fill(selector)`, `page.type`, `waitForSelector`, `querySelector`).
- `page.waitForResponse(predicate, action)` returns **`Response`**; start the wait and the action in one
  call, match on URL and method, then assert the status.
- No hand-rolled retry loops; raise the assertion timeout, or `page.waitForCondition(...)` for a non-DOM
  condition.

### Auth and data

- Sign in **once per suite run per role** (`AuthSetup`, `references/lifecycle.md` §6), save the storage state
  under `build/.auth/`, and point signed-in classes at it in `contextOptions()`. Never sign in inside every
  test.
- Records a test needs are created through `page.request()` in the class's `@BeforeMethod`, with a unique
  value per test, and deleted in its `@AfterMethod(alwaysRun = true)`.
- Builders for any record with four or more fields (`qa/java/skills/test-data-builder`).

### Build

The build is `assets/build.gradle.kts`: the pins above, Allure on allure-java 3, `useTestNG` with
`testng.xml`, `PLAYWRIGHT_JAVA_SRC=src/test/java` for trace sources, `installPlaywrightBrowsers` for CI and a
`playwright` task for codegen and show-trace. Extend that file; never start a second one.

## Generation steps

1. Detect the installed Playwright, TestNG and Allure versions and the project layout; match them.
2. Confirm the feature, scenarios, locators, auth, data and devices with the user.
3. If the project has no `BaseTest`, add `assets/BaseTest.java`, `testng.xml` and the build files. If it has
   one with static Playwright fields or `parallel="methods"`, migrate it to the asset's shape first.
4. For each screen, write or extend `pages/<Name>Page.java` from `assets/LoginPage.java`: one
   `private final Locator` per element on the highest ladder rung, components for reused regions, `goTo()`,
   intent methods, `describe()` on asserted locators. Add a `missing-testids.md` row for every fallback.
5. Write `tests/<Feature>Test.java` from `assets/LoginTest.java`: extends `BaseTest`, pages built in a
   `@BeforeMethod`, one `@Test` per scenario with a `Should_X_When_Y` name and groups.
6. For signed-in classes, add `AuthSetup` and override `contextOptions()`; for devices, override it with the
   device's options.
7. Run `./gradlew installPlaywrightBrowsers test` (0 failures) and debug with `HEADED=1` or
   `PWDEBUG=1`. In a `Gate: none` plan task, run neither; report the files as "written, not run".

## Handoffs

- Page-object hierarchy → `qa/java/skills/page-object-design`
- Page objects and test ids from a live URL → `qa/java/skills/page-objects-from-url`
- Reviewing Playwright tests → `qa/java/skills/ui-test-author/review`
- Screenshots, video, screencast, trace, HAR → `qa/java/skills/evidence-capture`
- Test data builders → `qa/java/skills/test-data-builder`
- Breakpoint matrices → `qa/java/skills/responsive-testing`
- Real-device mobile web → `qa/java/skills/device-cloud`
- Allure reporting and CI → `qa/reporting/java/skills/test-reports`, `qa/cicd/java/skills/ci-pipelines`
