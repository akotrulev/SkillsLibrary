---
name: inhouse-framework-conventions
description: Use when working in the Java 21 Accelerator test automation framework (Gradle + TestNG + RestAssured + Playwright + Appium, JSON-driven screens) or any consumer of it. Triggers: "add a test to the Java Accelerator", "scaffold a screen for the Java Appium suite", "create a Playwright page object for X in Accelerator". Not for a suite outside the Accelerator (`qa-java:page-object-design`, `qa-java:ui-tests-playwright`).
---

# Accelerator Conventions (Java)

The Accelerator is a Java 21 test automation framework with separate Gradle modules for `appium-tests`, `playwright-tests`, `api-tests`, and `test-core`. It uses a JSON-driven screen pattern, TestNG, Allure for reporting, BrowserStack for cloud execution, and a two-agent Claude Code workflow (Opus planner + Sonnet implementer).

This skill encodes the conventions that distinguish "Accelerator code" from generic test automation.

## When to use

- The user is adding or modifying code inside the Java Accelerator repo
- The user is consuming Accelerator from another project and asks how to wire it up
- The user wants to know whether a piece of code follows Accelerator conventions

## When NOT to use

- The user wants generic Playwright / Appium / RestAssured tutorials → use the generic skills
- The user is starting a brand-new automation framework from scratch (Accelerator might be the wrong choice)

## Project layout

A Gradle (Kotlin DSL) multi-module build. `test-core` is the shared library; each suite is its own module.

```
accelerator/
├── settings.gradle.kts        # includes the modules below
├── build.gradle.kts           # shared plugins, Java 21 toolchain, version catalog
├── gradle/libs.versions.toml  # centralized dependency versions
├── test-core/                 # shared abstractions, helpers, base classes
│   └── src/main/java/com/accelerator/core/
│       ├── config/            # env config, BrowserStack creds, run options
│       ├── reporting/         # Allure attachments, step helpers
│       ├── screens/           # JSON loader, screen base class
│       └── waits/             # explicit wait helpers
├── api-tests/                 # RestAssured-based API tests
│   └── src/test/java/com/accelerator/api/
│       ├── clients/           # typed API clients (one per service)
│       ├── builders/          # test data builders
│       └── tests/             # grouped by service / feature
├── playwright-tests/          # Web UI tests (com.microsoft.playwright)
│   └── src/test/java/com/accelerator/web/
│       ├── pages/             # page objects, one per screen, JSON-driven
│       └── tests/             # grouped by feature
├── appium-tests/              # Mobile tests (appium java-client)
│   └── src/test/java/com/accelerator/mobile/
│       ├── screens/           # screen objects, JSON-driven
│       └── tests/             # grouped by feature
├── screen-definitions/        # *.screen.json files — selectors + metadata (shared by web + mobile)
└── .claude/
    ├── commands/              # planner + implementer slash commands
    └── settings.json
```

## Conventions

### Screen / Page object pattern

Page and screen objects are **JSON-driven**. Selectors live in `*.screen.json` files under `screen-definitions/`, not in code. The Java class reads its selectors from the JSON at construction time.

Why: changing a selector doesn't recompile. The same JSON can drive both Playwright (web) and Appium (mobile) when the screen exists in both contexts.

**Screen JSON example** (`LoginScreen.screen.json`):

```json
{
  "name": "LoginScreen",
  "platforms": {
    "web": {
      "emailInput": "[data-testid='Login.Email']",
      "passwordInput": "[data-testid='Login.Password']",
      "signInButton": "[data-testid='Login.Submit']",
      "errorMessage": "[data-testid='Login.Error']"
    },
    "ios": {
      "emailInput": "//XCUIElementTypeTextField[@name='email']",
      "passwordInput": "//XCUIElementTypeSecureTextField[@name='password']",
      "signInButton": "//XCUIElementTypeButton[@name='Sign in']"
    },
    "android": {
      "emailInput": "//*[@resource-id='com.app:id/email']",
      "passwordInput": "//*[@resource-id='com.app:id/password']",
      "signInButton": "//*[@resource-id='com.app:id/sign_in']"
    }
  }
}
```

**Page class example** (web, Playwright). `PageBase.locator(key)` turns the JSON key into
`page.locator(selector(key))` and throws, naming the screen and the key, when the key is missing. Every action
goes through a `Locator`, so it auto-waits and is strict; the page-level selector methods (`page.fill(selector)`,
`page.click(selector)`, `page.innerText(selector)`) are discouraged by Playwright and are not used. State a test
asserts on is exposed as a `Locator`, never a `String` read once.

```java
public final class LoginPage extends PageBase {
    private final Locator errorMessage;

    public LoginPage(Page page) {
        super(page, "LoginScreen");
        this.errorMessage = locator("errorMessage");
    }

    @Step("Sign in as {user.email}")
    public void signIn(User user) {
        locator("emailInput").fill(user.email());
        locator("passwordInput").fill(user.password());
        locator("signInButton").click();
    }

    public Locator errorMessage() {
        return errorMessage;
    }
}
```

Rules:
- **No literal selectors in page methods.** Always go through `locator("key")`.
- **Actions run on a `Locator`**, never on the page-level selector API; anything a test asserts is returned as a
  `Locator` so the assertion is web-first.
- **Method names describe user intent**, not mechanics. `signIn`, not `clickSignInButton`.
- **One page object per screen.** Composite flows live in test code or in flow helpers, not in page objects.
- **No assertions inside page objects.** They expose state; tests assert.
- **Locators in JSON are `data-testid`-first for web** — `data-testid` is the standing contract with the dev team.

### Test structure

```java
@Epic("Authentication")
@Feature("Login")
public final class LoginTests extends BaseTest {
    private LoginPage loginPage;
    private DashboardPage dashboardPage;

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        loginPage = new LoginPage(page);
        dashboardPage = new DashboardPage(page);
    }

    @Test
    @Story("Successful login")
    public void Should_ShowDashboard_When_CredentialsAreValid() {
        User user = UserBuilder.aValidUser().build();

        loginPage.goTo();
        loginPage.signIn(user);

        assertThat(dashboardPage.heading()).isVisible();
    }

    @Test
    @Story("Rejected login")
    public void Should_ShowError_When_PasswordIsWrong() {
        User user = UserBuilder.aValidUser().withPassword("Wrong-" + UUID.randomUUID()).build();

        loginPage.goTo();
        loginPage.signIn(user);

        assertThat(loginPage.errorMessage()).hasText("Invalid email or password");
    }
}
```

`test-core`'s `BaseTest` is the Java lane's one Playwright lifecycle
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`): instance fields, a browser per class, a
context and page per test, `BASE_URL`, `parallel="classes"`, and failure evidence. Page objects are built in the
test class's own `@BeforeMethod`; tests never call `page` directly.

Rules:
- Test class per feature or screen, not per AC
- Test name reads `Should_<Outcome>_When_<Condition>`
- Three-section body: Arrange / Act / Assert — single blank line between, no comments needed
- Test data via builders (`UserBuilder.aValidUser().build()`), never inline literals
- One logical assertion per test
- Use `org.testng.annotations.Test`; assertions via Playwright's `assertThat` or AssertJ — never raw TestNG `assertEquals` chains that hide intent

### Test data builders

Every domain object gets a builder. Builders:

- Live in `*-tests/.../builders/`
- Use the `a<Name>` / `an<Name>` naming for the fluent entry: `UserBuilder.aValidUser()`, `OrderBuilder.anOrderWith(...)`
- Provide sensible defaults — calling `.build()` with no chained methods produces a valid object
- Return `this` from each `with*` method for fluent chaining

```java
public final class UserBuilder {
    private String email = "user-" + UUID.randomUUID() + "@test.local";
    private String password = "Valid123!";
    private int yearsActive = 1;

    public static UserBuilder aValidUser() {
        return new UserBuilder();
    }

    public UserBuilder withEmail(String email) {
        this.email = email;
        return this;
    }

    public UserBuilder withPassword(String password) {
        this.password = password;
        return this;
    }

    public UserBuilder withYearsActive(int years) {
        this.yearsActive = years;
        return this;
    }

    public User build() {
        return new User(email, password, yearsActive);
    }
}
```

### Waits

- **Never** use `Thread.sleep(...)` in test code
- Use Playwright's auto-waiting (`click`, `fill`, `assertThat(...).isVisible()`)
- For Appium, use the helpers in `test-core` `waits` package — `waitUntilVisible`, `waitUntilStable` (backed by `WebDriverWait` / `Awaitility`, never fixed sleeps)
- If you need a wait that doesn't exist, add it to `test-core` `waits`, don't inline it

### Allure reporting

- Decorate every test with at least `@Epic`, `@Feature`, `@Story`
- Failure evidence (trace, video, full-page screenshot) comes from `BaseTest`'s `@AfterMethod` and lands in
  `build/playwright-artifacts/`, attached with allure-java 3.0's `Allure.attachment(..., AttachmentOptions)` —
  no second `ITestListener` for the same evidence (`qa/java/skills/evidence-capture`)
- Use `@Step` on page object methods so steps appear in the Allure tree

### API tests

- One typed client per service in `api-tests/.../clients/`
- Clients return strongly typed responses (deserialized POJOs/records), not raw `Response`
- Test data via builders, same convention as UI
- Contract tests (Pact) run before integration tests in the pipeline

### Configuration & environments

- All config lives in `application.yml` + per-env overrides (`application-staging.yml`) loaded by the `config` helper in `test-core`
- BrowserStack creds, base URLs, and feature flags come from env vars
- Never commit `.env` files; commit `.env.example` only

### Claude Code workflow

The Accelerator uses a two-agent pattern:

- **Planner** (Opus): reads the task, produces a numbered plan with files to create/modify and a verification step. Does not write code.
- **Implementer** (Sonnet): executes the plan, one step at a time. After each step, runs the relevant tests (`./gradlew :playwright-tests:test --tests ...`).

Slash commands:
- `/plan <task>` — invokes the planner
- `/implement` — invokes the implementer against the last plan
- `/review` — invokes a reviewer pass against the current branch

When rate-limited on one model, switch to another (Opus → Sonnet → Haiku) — the workflow is designed to degrade gracefully.

## Quality bar (reviewer checklist)

- [ ] No literal selectors in page/screen methods
- [ ] Page actions run on `locator("key")`, never `page.fill/click/innerText(selector)`
- [ ] No `Thread.sleep` in tests
- [ ] Test name follows `Should_X_When_Y`
- [ ] Test data via a builder
- [ ] Allure annotations present
- [ ] One logical assertion per test
- [ ] Page object methods describe intent, not mechanics
- [ ] Builders provide valid defaults
- [ ] No conditional logic in tests (`if`, `for` driving assertions) — use `@DataProvider`
- [ ] Tests are independent and order-agnostic

## Anti-examples

| Anti-example | Why it's wrong | Instead |
|---|---|---|
| `page.click("button.signin-btn")` in a page object | A selector in code, and a page-level selector method | `locator("signInButton").click()` with the selector in `*.screen.json` |
| `String getErrorMessage()` returning `page.innerText(...)`, then `assertEquals(text, ...)` | A one-shot read races the page | expose `Locator errorMessage()`; `assertThat(loginPage.errorMessage()).hasText(...)` |
| `Thread.sleep(2000)` | A sleep | auto-wait, web-first assertions, `test-core` `waits` |
| `public void test_clickLoginButton()` | Names the mechanics, not the behaviour | `Should_ShowDashboard_When_CredentialsAreValid` |
| `loginPage.signIn(new User("user@test.com", "Password1!"))` | Inline test data | `UserBuilder.aValidUser().build()` |
| `if (env.equals("staging")) { ... } else { ... }` in a test | Conditional logic in a test | `@DataProvider` or a class per environment |
| `assertThat(page).hasURL(...)` in a test | A raw `page` in the test | assert on a page object's locator (`dashboardPage.heading()`) |
