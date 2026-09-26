---
name: qa-inhouse-framework-conventions-java
description: Use when working in the Java 21 Accelerator test automation framework (Gradle + TestNG + RestAssured + Playwright + Appium, JSON-driven screens) or any consumer of it. Triggers: "add a test to the Java Accelerator", "scaffold a screen for the Java Appium suite", "create a Playwright page object for X in Accelerator". Not for a suite outside the Accelerator (`qa-page-object-design-java`, `qa-ui-test-writer-playwright-java`).
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
      "emailInput": "[data-testid='email']",
      "passwordInput": "[data-testid='password']",
      "signInButton": "[data-testid='sign-in']",
      "errorMessage": "[data-testid='login-error']"
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

**Page class example**:

```java
public final class LoginPage extends PageBase {

    public LoginPage(Page page) {
        super(page, "LoginScreen");
    }

    @Step("Sign in as {email}")
    public void signIn(String email, String password) {
        page.fill(selector("emailInput"), email);
        page.fill(selector("passwordInput"), password);
        page.click(selector("signInButton"));
    }

    public String getErrorMessage() {
        return page.innerText(selector("errorMessage"));
    }
}
```

Rules:
- **No literal selectors in page methods.** Always go through `selector("key")`.
- **Method names describe user intent**, not mechanics. `signIn`, not `clickSignInButton`.
- **One page object per screen.** Composite flows live in test code or in flow helpers, not in page objects.
- **No assertions inside page objects.** They expose state; tests assert.
- **Locators in JSON are `data-testid`-first for web** — `data-testid` is the standing contract with the dev team.

### Test structure

```java
@Epic("Authentication")
@Feature("Login")
public final class LoginTests extends PlaywrightTestBase {

    @Test
    @Story("Successful login")
    public void should_redirect_to_dashboard_when_credentials_valid() {
        User user = UserBuilder.aValidUser().build();
        LoginPage login = new LoginPage(page);

        login.goTo();
        login.signIn(user.email(), user.password());

        assertThat(page).hasURL(Pattern.compile(".*/dashboard"));
    }
}
```

Rules:
- Test class per feature or screen, not per AC
- Test name reads `should_<outcome>_when_<condition>` (Java method-name casing)
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
- Attach evidence on failure: screenshot, page source, network HAR (wire via a TestNG `ITestListener` in `test-core`)
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
- [ ] No `Thread.sleep` in tests
- [ ] Test name follows `should_<outcome>_when_<condition>`
- [ ] Test data via a builder
- [ ] Allure annotations present
- [ ] One logical assertion per test
- [ ] Page object methods describe intent, not mechanics
- [ ] Builders provide valid defaults
- [ ] No conditional logic in tests (`if`, `for` driving assertions) — use `@DataProvider`
- [ ] Tests are independent and order-agnostic

## Anti-examples

```java
// BAD: literal selector in page object
public void signIn() {
    page.click("button.signin-btn");  // ❌ selector in code
}

// BAD: sleep
Thread.sleep(2000);  // ❌

// BAD: implementation-named test
public void test_clickLoginButton() { ... }  // ❌

// BAD: inline test data
login.signIn("user@test.com", "Password1!");  // ❌ use a builder

// BAD: conditional in test
if (env.equals("staging")) { ... } else { ... }  // ❌ use @DataProvider or fixtures
```
