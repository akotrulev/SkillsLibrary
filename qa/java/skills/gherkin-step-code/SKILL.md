---
name: gherkin-step-code
description: Use when turning Gherkin .feature files into Cucumber-JVM steps in Java bound to page objects. Triggers "generate step definitions". Not for writing .feature files (feature-files).
---

# Cucumber-JVM Step Bindings + POM Implementation (Java 21)

Parses `.feature` files (and the **Step Catalog** from `feature-file-writer`) into Cucumber-JVM glue classes, **split by domain**, with parameterized Cucumber-Expression steps, and **implements each step by calling existing page-object intent methods**. Assertions live in `Then` steps; page objects only act and expose locators. The Cucumber project, DI (PicoContainer), hooks, and `TestContext` already exist (from `bdd-project-scaffold`).

## Stack

- Cucumber-JVM 7.34.x (`cucumber-java` + `cucumber-junit-platform-engine` + `cucumber-picocontainer`), pinned via the BOM
- Java 21; `@Given/@When/@Then` from `io.cucumber.java.en`
- Page objects from the existing UI/mobile project (`qa/java/skills/page-object-design`) — for web, the
  `ui-test-author/playwright` page objects, whose constructor takes a `Page`
- Playwright `assertThat` (web-first) or AssertJ for `Then` steps — match the existing UI project

## When to use

- `.feature` files exist (from `feature-file-writer`) and need step definitions.
- A scenario reports **undefined** or **ambiguous** steps and needs bindings written/fixed.
- Implementing the bodies of generated step skeletons against page objects.

## When NOT to use

- Authoring/canonicalizing `.feature` files → `qa/_shared/bdd/feature-file-writer`
- Project/DI/hooks scaffold → `qa/java/skills/bdd-project-scaffold`
- Building or extracting page objects → `qa/java/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Reviewing features + bindings → `qa/java/skills/bdd-reviewer`
- .NET/TS step glue → `qa/{dotnet,typescript}/skills/gherkin-step-code`

## Inputs needed

Confirm at most 2–3.

1. **The `.feature` files + Step Catalog** (from `feature-file-writer`) and the **Cleanup handoff** note.
2. **The page objects** available (paths) — which intent methods exist; what's missing.
3. **Platform** — Playwright/Selenium (web) or Appium (mobile).

## Rules

The standards this skill's output must meet are the qa-java rule files, not a list here: `qa-java-bdd.md` and `qa-java.md` (core). Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's recipes disagree, the rule files win.

How the bindings are built:

- Each canonical Step-Catalog row becomes exactly one step method; a step shared by many features goes in a `CommonSteps` glue class.
- Cucumber Expressions map cleanly to the catalog's params (`{string}`, `{int}`, `{word}`, `{double}`); enums and custom types come from a `@ParameterType` method in a glue class. Regex only for anchors or alternation.
- Every glue class takes `TestContext`, the per-scenario object PicoContainer builds, in its constructor. `TestContext` builds the page objects lazily from its `Page` and hands them to the steps; the page objects are the same classes the TestNG suite uses (`new LoginPage(page)`, `ui-test-author/playwright`), so the BDD layer reuses them unchanged.
- `Then` asserts with web-first `assertThat(...)` on a locator the page object exposes.
- The `feature-file-writer` Cleanup handoff becomes an `@After` hook in the support layer; the scaffold owns hook placement.
- A step that needs a page object or method that does not exist stops here: build it with `page-object-design` / `page-objects-from-url`, or hand it to `qa-ui-java` / `qa-mobile-java`.

## Templates

### Step definition — `steps/AuthenticationSteps.java` (Playwright/web)

```java
package com.example.steps;

import com.example.pages.LoginPage.Credentials;
import com.example.support.TestContext;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class AuthenticationSteps {
    private final TestContext context;

    public AuthenticationSteps(TestContext context) {
        this.context = context;
    }

    @Given("I am on the login page")
    public void iAmOnTheLoginPage() {
        context.login().goTo();
    }

    @When("I sign in as a registered customer")
    public void iSignInAsRegisteredCustomer() {
        context.login().signIn(context.registeredCustomer());
    }

    @When("I sign in with email {string} and password {string}")
    public void iSignInWith(String email, String password) {
        context.login().signIn(new Credentials(email, password));
    }

    @Then("I land on the home page")
    public void iLandOnTheHomePage() {
        assertThat(context.home().greeting()).isVisible();
    }

    @Then("I see the error {string}")
    public void iSeeTheError(String message) {
        assertThat(context.login().error()).hasText(message);
    }
}
```

PicoContainer constructor-injects the per-scenario `TestContext`. `LoginPage`, `HomePage` and `Credentials` are
`ui-test-author/playwright`'s asset classes; `context.registeredCustomer()` reads `E2E_USER` / `E2E_PASSWORD`
lazily, so no step reads the environment itself.

### Custom parameter type — `support/ParameterTypes.java`

```java
package com.example.support;

import io.cucumber.java.ParameterType;

import java.time.LocalDate;

public class ParameterTypes {
    @ParameterType("(\\d+) days? ago")
    public LocalDate daysAgo(String days) {
        return LocalDate.now().minusDays(Long.parseLong(days));
    }
}
```

A Cucumber Expression can now use `{daysAgo}`, e.g. "Given the order was placed 3 days ago".

### Data table step — typed via Cucumber's transformer

```java
@Given("the catalog contains")
public void theCatalogContains(java.util.List<java.util.Map<String, String>> rows) {
    rows.forEach(r -> context.catalog().add(r.get("sku"), Integer.parseInt(r.get("qty"))));
}
```

### Mobile variant (Appium)

Same shape; the screen objects take the **driver** (`context.driver()`), never `TestContext`, as the web page objects take the `Page`:

```java
@When("I sign in with email {string} and password {string}")
public void iSignInWith(String email, String password) {
    new LoginPage(context.driver()).signIn(email, password);
}
```

## Procedure

1. Read the `.feature` files + Step Catalog + Cleanup handoff and the available page objects.
2. For each distinct catalog step, write **one** step method in the right domain glue class; reuse for repeats.
3. Pick the binding annotation (`@Given`/`@When`/`@Then`) from the catalog; use Cucumber-Expression params matching the catalog's `{...}` placeholders and `Examples` columns.
4. Implement each body with page-object calls only; put assertions in `Then` with web-first `assertThat`.
5. For any missing page object/method, build it (`page-object-design`/`page-objects-from-url`) before binding the step.
6. Ensure the Cleanup is implemented as the `@After` hook (scaffold layer), not as steps.
7. `./gradlew test`, then run the features: every step bound (no undefined/ambiguous), the smoke scenario green.

## Handoffs

- `.feature` files / Step Catalog → `qa/_shared/bdd/feature-file-writer`
- Project/DI/hooks → `qa/java/skills/bdd-project-scaffold`
- Page objects → `qa/java/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Review features + bindings → `qa/java/skills/bdd-reviewer`
- Allure labels from tags → `qa/reporting/java/skills/test-reports`
