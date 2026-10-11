---
name: gherkin-step-code
description: Use when turning Gherkin .feature files into Cucumber-JVM step definitions in Java, implementing each step against existing Page Object Models. Triggers: "generate Cucumber step definitions for these features", "bind these Gherkin steps to our page objects", "split the step definitions by domain". Do NOT use to write the .feature files (`feature-file-writer`), scaffold the Cucumber project/hooks/DI (`bdd-project-scaffold`), or build page objects (`page-object-design`).
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

## Core rules

### 1. One glue class per domain, mapped to the Step Catalog

Group steps by feature/domain (`AuthenticationSteps`, `CartSteps`), **not** one giant `Steps.java`. Each canonical Step-Catalog row becomes exactly one step method — reuse across scenarios, never duplicate. A step shared by many features goes in a `CommonSteps` glue class.

### 2. Cucumber Expressions, not regex

Default to Cucumber Expressions (`{string}`, `{int}`, `{word}`, `{double}`, enums via a registered `ParameterType`). Plain text with `{...}` placeholders maps cleanly to the catalog params; reach for regex only when matching genuinely needs it (anchors / alternation). Custom types via a `@ParameterType` method in a glue class.

### 3. Inject shared state via the constructor — never new up the page or use static state

Step classes take `TestContext` (the per-scenario object PicoContainer builds) in the constructor. The page/driver was created in the `@Before` hook; steps reach page objects through the context. **Cucumber does not support step-class inheritance** — every **glue class** gets `TestContext` injected through its constructor; no static fields, no `ThreadLocal` in the glue, no string-keyed bag.

**Page objects take the `Page`, never `TestContext`.** They are the same classes the TestNG suite uses (`new LoginPage(page)`, `ui-test-author/playwright/SKILL.md` — constructor `(Page page)`, never config), so the BDD layer reuses them unchanged. `TestContext` builds them lazily from its `Page` and hands them to the steps; a page object that knew `TestContext` could not run outside Cucumber.

### 4. Steps are thin; mechanics live in page objects

A step body is one or two page-object calls. **No selectors, no `page.locator(...)`, no `findElement`, no waits in step definitions** — those belong in the page object. `Given`/`When` act; `Then` asserts with web-first `assertThat(...)` on a locator the page object exposes. Page objects never assert.

### 5. No fixed waits (web)

Rely on Playwright auto-waiting and web-first assertions (or Selenium `WebDriverWait` inside the page object). Never `Thread.sleep` / `page.waitForTimeout(...)` in a step.

### 6. Implement the Cleanup as a hook, not steps

The `feature-file-writer` Cleanup handoff becomes an `@After` hook in the support layer (the scaffold owns hook placement) — never Gherkin steps and never a step definition.

### 7. Missing page objects → build them first

If a step needs a page object/method that doesn't exist, stop and build it via `page-object-design`/`page-objects-from-url` (or hand to `qa-ui-java`/`qa-mobile-java`). Do not inline locators into the step to "make it pass."

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
7. `./gradlew test`, then run the features: every step bound (no undefined/ambiguous), the smoke scenario green. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Anti-patterns to flag

- One mega step-definition file instead of per-domain classes.
- Duplicate step methods for steps the catalog already unified — parameterize and reuse.
- `page.locator(...)`, `findElement`, CSS, or waits inside step definitions — promote to a page object.
- `new LoginPage(page)` or static state inside a step — inject `TestContext`, which builds the page objects.
- A page object whose constructor takes `TestContext` — page objects take the `Page`, so the TestNG suite and the BDD layer share them.
- An `expectLoaded()` or any other assertion inside a page object — the `Then` step asserts on the locator it exposes.
- A string-keyed `Map`/`ThreadLocal` bag for typed state — use the injected `TestContext`.
- Trying to share state via a `BaseSteps` superclass — Cucumber doesn't support step inheritance; inject `TestContext`.
- `When`/`Given` doing assertions.
- `Thread.sleep` / `page.waitForTimeout(...)` in a step.
- Regex step expressions where a Cucumber Expression reads cleaner.
- Implementing Cleanup as Gherkin/steps instead of an `@After` hook.

## Handoffs

- `.feature` files / Step Catalog → `qa/_shared/bdd/feature-file-writer`
- Project/DI/hooks → `qa/java/skills/bdd-project-scaffold`
- Page objects → `qa/java/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Review features + bindings → `qa/java/skills/bdd-reviewer`
- Allure labels from tags → `qa/reporting/java/skills/test-reports`
