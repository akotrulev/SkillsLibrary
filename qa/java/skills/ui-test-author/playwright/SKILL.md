---
name: ui-tests-playwright
description: Use when scaffolding Playwright UI tests in Java/TestNG (specs, page objects, signed-in state, web-first assertions). Triggers "write a Playwright test for X". Not for Selenium (ui-tests-selenium).
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

The standards this skill's output must meet are the qa-java rule files, not a list here: `qa-java.md` (core) and `qa-java-ui.md`. Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

### Lifecycle

- Every test class extends the one `BaseTest`. A role, a device or a launch flag is an override of `contextOptions()` or `launchOptions()` on the class that needs it, never a second base class. Playwright Java is not thread-safe, and TestNG runs all of a class's methods on one thread under `parallel="classes"`.
- `BASE_URL` is required: `page.navigate("/login")` and `page.request()` resolve against it. `HEADED=1` runs headed. Read required variables with `requiredEnv(name)`; credentials are `E2E_USER` and `E2E_PASSWORD`.
- Failure evidence is `BaseTest`'s: screenshot, trace and video kept only on failure, in `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`, attached to Allure. The order is evidence, then `context.close()`, then `video.saveAs`; Java's `saveAs` throws before the close.

### Locators and page objects

- The ladder: `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → `getByText` → `getByAltText` / `getByTitle` → CSS. Test ids are PascalCase dot-separated (`Login.Submit`, `OrderRow.Title`), the format `fe-react` and `fe-blazor` generate; a row is picked by its content.
- `visible()` (1.63) instead of `:visible`; `frameLocator` / `contentFrame()` for iframes; `addLocatorHandler` for overlays that may appear; `describe()` on every locator a test asserts on, because Java's `assertThat(locator)` has no message parameter.
- Locators are `private final Locator` fields built in the constructor; tests reach them through accessors (`error()`). A page takes `(Page page)`; a component takes its root `Locator`, as `SignInForm` does. The page owns its URL in `goTo()`. Pages are built in the test class, never as fields of `BaseTest`.

### Tests and waiting

- One test class per feature; `@Test(groups = {"login", "smoke"})`, `@Feature("Login")` on the class where the project uses Allure. One long journey is one test with Allure `@Step` labels.
- Web-first assertions only (`references/assertions.md`); `Locator` has no `getText()`. A longer wait is a longer assertion timeout (`new LocatorAssertions.IsVisibleOptions().setTimeout(...)`; there is no `AssertOptions`), or `page.waitForCondition(...)` for a non-DOM condition.
- Navigate, then assert a landmark. `waitForURL` or `assertThat(page).hasURL(...)` replace `waitForNavigation`.
- `page.waitForResponse(predicate, action)` returns **`Response`**: start the wait and the action in one call, match on URL and method, then assert the status. API responses assert the exact status with the body: `assertThat(created.status()).as(created.text()).isEqualTo(201)`.

### Auth and data

- Sign in once per suite run per role (`AuthSetup`, `references/lifecycle.md` §6), save the storage state under `build/.auth/`, and point signed-in classes at it in `contextOptions()`.
- Records a test needs are created through `page.request()` in the class's `@BeforeMethod` and deleted in its `@AfterMethod(alwaysRun = true)`; builders from `qa/java/skills/test-data-builder`.

### Build

The build is `assets/build.gradle.kts`: the pins above, Allure on allure-java 3, `useTestNG` with `testng.xml`, `PLAYWRIGHT_JAVA_SRC=src/test/java` for trace sources, `installPlaywrightBrowsers` for CI and a `playwright` task for codegen and show-trace. Extend that file; never start a second one.

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
   `PWDEBUG=1`.

## Handoffs

- Page-object hierarchy → `qa/java/skills/page-object-design`
- Page objects and test ids from a live URL → `qa/java/skills/page-objects-from-url`
- Reviewing Playwright tests → `qa/java/skills/ui-test-author/review`
- Screenshots, video, screencast, trace, HAR → `qa/java/skills/evidence-capture`
- Test data builders → `qa/java/skills/test-data-builder`
- Breakpoint matrices → `qa/java/skills/responsive-testing`
- Real-device mobile web → `qa/java/skills/device-cloud`
- Allure reporting and CI → `qa/reporting/java/skills/test-reports`, `qa/cicd/java/skills/ci-pipelines`
