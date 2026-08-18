---
name: qa-ui-test-writer-playwright-java
description: Use when the user asks to scaffold Playwright UI tests in Java — new test classes, page objects under `src/test/java/<pkg>/pages/`, or a specific scenario (login, form, accessibility, visual). Triggers: "write a Playwright test for X in Java", "add a Playwright Java page object for screen Y", "scaffold a Playwright Java spec".
---

# QA — Playwright Test & Page Object Generator (Java)

Scaffolds Playwright tests and page objects in **Java 21 + Gradle + TestNG** using the official `com.microsoft.playwright` library (sync API). Uses a **base-test class pattern**: a `BaseTest` constructs `Browser` / `BrowserContext` / `Page` in `@BeforeMethod` and exposes page objects to subclasses; tests do not instantiate browsers themselves. Locators use `getByTestId` first (`data-testid` is the standing contract with the dev team — see `qa/java/skills/page-objects-from-url` for extraction and the missing-testid report), falling back to role/label semantics — never raw CSS where anything better exists.

## Stack

- Java 21
- Gradle (Kotlin DSL `build.gradle.kts`)
- TestNG 7.x
- `com.microsoft.playwright:playwright` (sync API)
- Page objects under `src/test/java/<group>/pages/`, tests under `src/test/java/<group>/tests/`
- Base test class under `src/test/java/<group>/support/`
- `io.qameta.allure:allure-testng` where the project uses Allure

## When to use

- New `*Test.java` under `src/test/java/<group>/tests/`
- New page object under `src/test/java/<group>/pages/`
- New base class or helper under `src/test/java/<group>/support/`
- Adding a scenario to an existing test class

## When NOT to use

- Playwright TypeScript → `qa/typescript/skills/ui-test-author/playwright`
- Playwright .NET → `qa/dotnet/skills/ui-test-author/playwright`
- Mobile / Appium → `qa/java/skills/ui-test-author/appium`
- Java Selenium → `qa/java/skills/ui-test-author/selenium`
- Reviewing existing Playwright code → `qa/java/skills/ui-test-author/review`
- Designing the overall page-object hierarchy → `qa/java/skills/page-object-design`

## Inputs needed

1. **Feature / page** under test (e.g. `Login`, `CheckoutCart`)
2. **User journey** — concrete steps + the user-visible outcome to assert
3. **Locators** — for each element: `getByTestId` whenever the element has a `data-testid`; otherwise `getByRole` / `getByLabel`, then `getByText`; CSS only as last resort. Missing testids are reported via `qa/java/skills/page-objects-from-url`'s `missing-testids.md`
4. **Auth requirement** — anonymous, or signed-in (which user role + how the session is established)
5. **Test data** — seeded by API, by helper, or inline

## Patterns

### `build.gradle.kts`

```kotlin
plugins {
    java
    id("io.qameta.allure") version "2.11.2"
}

repositories { mavenCentral() }

dependencies {
    testImplementation("com.microsoft.playwright:playwright:1.49.0")
    testImplementation("org.testng:testng:7.10.2")
    testImplementation("io.qameta.allure:allure-testng:2.27.0")
    testImplementation("org.assertj:assertj-core:3.26.3")
}

tasks.test {
    useTestNG()
    systemProperty("playwright.headless", System.getProperty("playwright.headless", "true"))
}

java {
    toolchain { languageVersion.set(JavaLanguageVersion.of(21)) }
}
```

### Base test — `src/test/java/com/example/support/BaseTest.java`

```java
package com.example.support;

import com.example.pages.HomePage;
import com.example.pages.LoginPage;
import com.microsoft.playwright.*;
import org.testng.annotations.*;

public abstract class BaseTest {
    private static Playwright playwright;
    private static Browser browser;

    protected BrowserContext context;
    protected Page page;
    protected LoginPage loginPage;
    protected HomePage homePage;

    @BeforeSuite(alwaysRun = true)
    public void launchBrowser() {
        playwright = Playwright.create();
        boolean headless = Boolean.parseBoolean(System.getProperty("playwright.headless", "true"));
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(headless));
    }

    @BeforeMethod(alwaysRun = true)
    public void createContext() {
        context = browser.newContext();
        page = context.newPage();
        loginPage = new LoginPage(page);
        homePage = new HomePage(page);
    }

    @AfterMethod(alwaysRun = true)
    public void closeContext() {
        if (context != null) context.close();
    }

    @AfterSuite(alwaysRun = true)
    public void closeBrowser() {
        if (browser != null) browser.close();
        if (playwright != null) playwright.close();
    }
}
```

### Page object — `src/test/java/com/example/pages/LoginPage.java`

```java
package com.example.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class LoginPage {
    private final Page page;
    private final Locator email;
    private final Locator password;
    private final Locator submit;
    final Locator errorBanner;

    public LoginPage(Page page) {
        this.page = page;
        this.email = page.getByTestId("login-email");
        this.password = page.getByTestId("login-password");
        // TODO: missing data-testid 'login-submit' — see missing-testids.md
        this.submit = page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Sign in"));
        this.errorBanner = page.getByTestId("login-error");
    }

    public void goTo() {
        page.navigate("/login");
    }

    public void signIn(String emailValue, String passwordValue) {
        email.fill(emailValue);
        password.fill(passwordValue);
        submit.click();
    }

    public void expectLoaded() {
        assertThat(email).isVisible();
    }

    public Locator errorBanner() {
        return errorBanner;
    }
}
```

### Test — `src/test/java/com/example/tests/LoginTest.java`

```java
package com.example.tests;

import com.example.support.BaseTest;
import org.testng.annotations.Test;

import java.util.regex.Pattern;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

@io.qameta.allure.Feature("Login")
public class LoginTest extends BaseTest {

    @Test(groups = {"login", "smoke"})
    public void signsInWithValidCredentials() {
        loginPage.goTo();
        loginPage.signIn(System.getenv("E2E_USER"), System.getenv("E2E_PASSWORD"));

        homePage.expectLoaded();
        assertThat(homePage.greeting()).containsText("Welcome");
    }

    @Test(groups = "login")
    public void showsErrorForInvalidPassword() {
        loginPage.goTo();
        loginPage.signIn(System.getenv("E2E_USER"), "wrong");

        assertThat(loginPage.errorBanner()).isVisible();
        assertThat(loginPage.errorBanner()).hasText(Pattern.compile("invalid credentials", Pattern.CASE_INSENSITIVE));
    }
}
```

### Authenticated state via `storageState`

For tests that need a signed-in session, sign in once and persist `storageState` to a file. Reuse it in a separate base class:

```java
public abstract class AuthenticatedBaseTest extends BaseTest {
    private static final Path STATE = Path.of("build/.auth/user.json");

    @BeforeSuite(alwaysRun = true, dependsOnMethods = "launchBrowser")
    public void authenticate() {
        if (Files.exists(STATE)) return;
        try (BrowserContext setupCtx = browser.newContext()) {
            Page setupPage = setupCtx.newPage();
            LoginPage login = new LoginPage(setupPage);
            login.goTo();
            login.signIn(System.getenv("E2E_USER"), System.getenv("E2E_PASSWORD"));
            setupCtx.storageState(new BrowserContext.StorageStateOptions().setPath(STATE));
        }
    }

    @Override
    @BeforeMethod(alwaysRun = true)
    public void createContext() {
        context = browser.newContext(new Browser.NewContextOptions().setStorageStatePath(STATE));
        page = context.newPage();
        // re-init page objects
    }
}
```

### API-seeded data

```java
@BeforeMethod(dependsOnMethods = "createContext")
public void seedOrder() {
    APIResponse res = context.request().post("/api/orders",
        RequestOptions.create().setData(Map.of("sku", "ABC", "qty", 1)));
    assertThat(res).isOK();
    this.seededOrder = res.text();
}
```

## Rules

### Locator preference order (strict)

1. `page.getByTestId("...")` — **preferred whenever the element carries a `data-testid`**; the attribute is the agreed contract with the app team. Elements missing it go in the `missing-testids.md` dev-team report (see `qa/java/skills/page-objects-from-url`) and use a fallback below with `// TODO: missing data-testid '<suggested>'`
2. `page.getByRole(AriaRole.X, new Page.GetByRoleOptions().setName(...))` — best fallback
3. `page.getByLabel("...")` — for form inputs
4. `page.getByPlaceholder("...")` — only when there is no label
5. `page.getByText("...", new Page.GetByTextOptions().setExact(true))` — for assertions on visible text
6. CSS / XPath via `page.locator("...")` — **last resort**; add `// TODO: replace with data-testid locator` and a brief reason

### Page object rules

- Locators are `private final Locator` fields initialized in the constructor — **not** methods that re-query the DOM
- Constructor signature is `(Page page)` — never take strings or config
- Action methods return `void` for same-page actions; for navigation return the next page object (e.g. `HomePage`)
- An `expectLoaded()` method must exist and assert one landmark locator is visible
- **No assertions inside actions** — actions perform; tests and `expectLoaded` assert
- **No `page.locator("css selector")` in test classes** — wrap inside a page object

### Test rules

- One test class per feature; group scenarios with TestNG `groups = {...}`
- Method names describe behavior: `signsInWithValidCredentials`, `showsErrorForInvalidPassword`
- One logical behavior per `@Test`. Multiple `assertThat(...)` calls are fine if they verify one behavior; otherwise split.
- **Every test asserts something.** A test that ends after an action with no assertion is not a test.
- Use web-first assertions: `PlaywrightAssertions.assertThat(locator).isVisible() / .hasText(...) / .hasCount(n) / .isEnabled()`. They retry until timeout. Never call `locator.isVisible()` and pass the boolean to `Assert.assertTrue` — one-shot checks lose auto-waiting.
- Prefer positive assertions over negated ones: `isHidden()` over `not().isVisible()`, `isDisabled()` over `not().isEnabled()`.
- **One expected condition per assertion — never an `OR`.** Assert the one thing the flow produces: `hasText("Saved")`, never `hasText(Pattern.compile("Saved|Success"))`; `hasCount(3)`, never "3 or more"; `assertEquals(actual, expected)`, never `assertTrue(a || b)` or a Hamcrest `anyOf(...)` / `either(...).or(...)`. **A regex alternation in a text or URL assertion is an `OR` in disguise** — the commonest form of this in UI tests. The rule covers text, counts, URLs, attribute values, and visible/enabled state alike. If both outcomes are genuinely reachable the test does not know what the app should do — split it into one `@Test` per expected outcome, drive it from a `@DataProvider`, or pin down the correct behavior. The only exception is an explicit instruction to accept more than one value; record that instruction in a comment on the assertion.
- **No `try`/`catch` in a test — and none in `@AfterMethod`.** An unexpected exception must reach TestNG; an expected one is asserted with `assertThrows`, which is an assertion, not error handling. Anything the test created is tracked and deleted in `@AfterMethod(alwaysRun = true)` with no catch — a cleanup that fails should fail loudly rather than leak state into the next run. The suite's only catches live in **I/O helpers where narrowing one named exception is the contract** — an `isDisplayed(By)` probe converting `NoSuchElementException` into `false`, a driver-quit helper — never a blanket `catch (Exception)`, and never a catch that lets a failed action continue into the assertions.
- **Failures name the subject.** `assertEquals(banner.getText(), "Saved", "success banner after saving order " + orderId)`. A UI failure reported as `expected [Saved] but found []` with no subject is indistinguishable from a locator that matched the wrong element.
- **No `page.waitForTimeout(ms)`** — use a web-first assertion or `assertThat(...).isVisible(new AssertOptions().setTimeout(...))`.
- **Do not pass `setWaitUntil(WaitUntilState.NETWORKIDLE)` to `navigate(...)`.** Brittle on SPAs with long-polling / WebSockets. Navigate, then assert a user-visible landmark.
- **Do not pre-wait before auto-waiting actions.** `click` / `fill` / `check` already wait for actionability — `locator.waitFor()` immediately before `locator.click()` is redundant.
- **Do not use `setForce(true)`.** It skips actionability checks and hides real bugs. Fix the flow — close the overlay, scroll into view — instead of forcing.
- **`waitForNavigation` is deprecated.** Use `page.waitForURL("**/path")` or a web-first URL/landmark assertion.
- **`waitForResponse` ordering** uses `page.waitForResponse(predicate, Runnable)`:
  ```java
  APIResponse resp = page.waitForResponse(
      r -> r.url().contains("/api/data") && r.status() == 200,
      () -> submit.click()
  );
  ```
  Never call `waitForResponse` after the action — the response can arrive first.
- **Retry loops:** never hand-roll `while (retries-- > 0) { ... sleep ... }`. Use `assertThat(locator)` with a longer timeout, or wrap the retry inside `Awaitility` (if added) — but prefer raising the assertion timeout via `setTimeout`.
- Prefer web-first assertions over `page.waitForFunction(...)` for UI state.
- Pass `setExact(true)` to `getByText` / `getByRole.setName(...)` when the expected text is a substring of other labels on the page — otherwise a future label change causes a strict-mode violation.
- **Tag every test with the area under test** plus its suite tier: `@Test(groups = {"login", "smoke"})` — the area group (`login`, `checkout`, `search`, …) matches the feature/page the test exercises so CI can filter by area; the tier (`smoke` / `regression`) is added where it applies. Mirror the area in Allure via `@Feature("Login")` on the class and `@Story("...")` per test where the project uses Allure, so the report groups by the same areas.

### Auth & storage state

- Sign in **once** per suite, persist `storageState` to a file, and load it in `BrowserContext.NewContextOptions().setStorageStatePath(...)`; do not log in inside every test
- For tests that need a different role, create a separate base class per role with its own state file
- Anonymous tests use a context without `storageStatePath`

### What NOT to do

- No `page.waitForTimeout(ms)` — every wait must be conditional on a Locator or response
- No `setWaitUntil(WaitUntilState.NETWORKIDLE)` — assert a landmark instead
- No `setForce(true)` on `click` / `fill` / `check` — fix the underlying flow
- No `locator.waitFor(...)` immediately before an auto-waiting action — it is redundant
- No `waitForNavigation` (deprecated) — use `waitForURL` or a URL assertion
- No hand-rolled retry loops with `Thread.sleep` — extend the assertion timeout
- No `page.waitForFunction` for state covered by a web-first assertion
- No `not().isVisible()` when `isHidden()` exists; no `not().isEnabled()` when `isDisabled()` exists
- No `OR` in any assertion — no `||` inside `assertTrue`, no `anyOf`/`either().or()` matchers, no `Pattern.compile("a|b")` alternation in a text/URL assertion. One expected value per assertion (see Test rules)
- No `try`/`catch` in a `@Test` or `@AfterMethod` — expected exceptions use `assertThrows`; catches live only in I/O helpers narrowing one named exception (see Test rules)
- No `page.locator("div.foo > span:nth-child(3)")` in test classes — promote to a page object with a semantic locator
- No `page.navigate(...)` directly in test classes — put it in the page object's `goTo()` so it owns its URL
- No `System.out.println` for debugging in committed tests — use Allure steps and the trace viewer instead
- No assertions in action methods — `expectLoaded()` is the only assertion that belongs on a page object
- No `if`/`for` driving assertions — use TestNG `@DataProvider` for parameterization
- No shared mutable state between tests — each test gets a fresh `BrowserContext` and fresh page objects
- No hardcoded credentials, base URLs, or environment hostnames — read from env vars / system properties
- No test without at least one assertion — actions without assertions verify nothing
- No TestNG `dependsOnMethods` chains across `@Test` methods to model multi-step flows. Each test sets up its own state. For one journey, put the whole flow in a single test and group steps with Allure `@Step`.

## Generation steps

1. Confirm **feature**, **scenarios**, **locators**, **auth requirement**, and **data source** with the user.
2. For each new screen, generate or extend `src/test/java/<pkg>/pages/{Name}Page.java`:
   - One `private final Locator` per element, initialized in the constructor with the best-available semantic locator
   - `goTo()` method that owns the URL
   - `expectLoaded()` that asserts one landmark
   - One action method per user-intent action
3. Add the page object as a `protected` field on `BaseTest` and initialize it in `@BeforeMethod`.
4. Generate `src/test/java/<pkg>/tests/{Feature}Test.java` extending `BaseTest`:
   - One `@Test` per scenario
   - Use Allure `@Step` for non-trivial substeps
5. For authenticated flows, ensure an `AuthenticatedBaseTest` exists and the test extends it.
6. Run `./gradlew test` — expect 0 failures. Run `./gradlew test -Dplaywright.headless=false` to debug visually.

## Handoffs

- Designing the page-object hierarchy → `qa/java/skills/page-object-design`
- Reviewing existing Playwright tests → `qa/java/skills/ui-test-author/review`
- Test data builders → `qa/java/skills/test-data-builder`
- Allure reporter setup → `qa/reporting/java/skills/test-reports`
