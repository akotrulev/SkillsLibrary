---
name: qa-bdd-project-scaffold-java
description: Use when adding the Cucumber-JVM BDD layer onto a Java 21 UI/mobile test project, or standing up a Cucumber-JVM + JUnit 5 project from zero. Triggers: "set up Cucumber", "add a BDD layer to our Playwright/Selenium/Appium tests in Java", "scaffold a Cucumber-JVM feature project", "wire Cucumber DI and hooks". Do NOT use to write feature files (use `qa/_shared/bdd/gherkin-authoring`), to generate step definitions (use `qa/java/skills/bdd-step-bindings`), or to build the page objects (use `qa/java/skills/page-object-architect`).
---

# Cucumber-JVM BDD Project Scaffold (Java 21)

Wires **Cucumber-JVM** into a Java 21 + Gradle (Kotlin DSL) test project: the `io.cucumber:*` BOM and packages, the **JUnit 5 Platform** runner (a `@Suite` class + `junit-platform.properties`), the `features/` resource folder, the DI container (**PicoContainer**, zero-config), the per-scenario browser/driver lifecycle hooks, and the shared per-scenario context object that step classes inject. It produces the **empty rig** — no feature files, no step logic; those come from `gherkin-authoring` and `bdd-step-bindings`.

This is the BDD analogue of the UI project scaffold; it assumes a Playwright (web), Selenium (web), or Appium (mobile) page-object project either exists or will be built by `qa-ui-java` / `qa-mobile-java`.

## Stack (pinned, verify latest at author time)

- Java 21, Gradle (Kotlin DSL `build.gradle.kts`)
- `io.cucumber:cucumber-bom` (pins every `io.cucumber:*`; latest line **7.34.4**)
- `io.cucumber:cucumber-java` (the `@Given/@When/@Then` annotations + Cucumber Expressions)
- `io.cucumber:cucumber-junit-platform-engine` (the idiomatic runner — **not** the deprecated JUnit 4 `@RunWith(Cucumber.class)`)
- `io.cucumber:cucumber-picocontainer` (DI — constructor injection, zero config: just add the dependency)
- `org.junit:junit-bom` + `org.junit.platform:junit-platform-suite` + `junit-platform-launcher` (runtime)
- Web: `com.microsoft.playwright:playwright` (**1.60.0**, sync API) or Selenium 4 — there is no Playwright Test runner on the JVM, you drive the automation library from step defs
- Mobile: `io.appium:java-client` **10.1.1** (Appium 2.x) on Selenium 4
- Assertions in `Then` steps: AssertJ / Playwright `assertThat` (match the existing UI project)
- Features under `src/test/resources/features/`; step defs + hooks + context under `src/test/java/.../steps` and `.../support`
- `io.qameta.allure:allure-cucumber7-jvm` when the project reports through Allure (the library default)

## When to use

- A Java UI/mobile project needs Cucumber-JVM added (BOM, packages, runner, config, hooks, DI).
- Starting a Cucumber-JVM suite from zero.

## When NOT to use

- Writing `.feature` files → `qa/_shared/bdd/gherkin-authoring`
- Generating step-definition classes → `qa/java/skills/bdd-step-bindings`
- Building page objects → `qa/java/skills/page-object-architect` / `pom-builder`
- BDD in .NET/TS → `qa/{dotnet,typescript}/skills/bdd-project-scaffold` (those use Reqnroll / playwright-bdd)

## Inputs needed

Confirm at most 2–3.

1. **Target project path** and whether a Playwright/Selenium/Appium page-object project already exists (reuse it; don't duplicate page objects).
2. **Platform** — web (Playwright/Selenium), mobile (Appium), or both (two hook/context pairs).
3. **Reporting** — Cucumber's built-in HTML formatter (default) or Allure (the library standard).

## Procedure

1. Read 2–3 existing files (the `build.gradle.kts`, an existing page object, `BaseTest`) to match the package, runner, and conventions.
2. Add the Cucumber packages to the test source set via the **BOM** (one pinned version), plus the JUnit Platform suite + launcher and `cucumber-picocontainer`. Set `tasks.test { useJUnitPlatform() }`.
3. Create the runner: a JUnit 5 `@Suite` class (`RunCucumberTest`) **and/or** `src/test/resources/junit-platform.properties` carrying glue, features path, plugins, and the tag filter.
4. Create `support/` : the per-scenario `TestContext` (holds the Playwright `Page` / Selenium `WebDriver` + lazily-built page objects), and the lifecycle `Hooks` class (`@Before`/`@After` that own the browser/driver — **with teardown**). PicoContainer is zero-config — adding the dependency is the whole wiring step.
5. Create the empty `src/test/resources/features/` folder and one throwaway smoke `.feature` to prove the rig parses and runs.
6. `./gradlew test` (the engine must discover the feature and bind the smoke step) and run the smoke scenario.
7. Report files created and hand off to `gherkin-authoring` (features) + `bdd-step-bindings` (steps).

## Templates

### `build.gradle.kts`

```kotlin
plugins {
    java
    id("io.qameta.allure") version "2.12.0"
}

repositories { mavenCentral() }

dependencies {
    // BOM pins every io.cucumber:* artifact to one version
    testImplementation(platform("io.cucumber:cucumber-bom:7.34.4"))
    testImplementation("io.cucumber:cucumber-java")
    testImplementation("io.cucumber:cucumber-junit-platform-engine")
    testImplementation("io.cucumber:cucumber-picocontainer")          // DI — zero config

    testImplementation(platform("org.junit:junit-bom:5.11.4"))
    testImplementation("org.junit.platform:junit-platform-suite")     // the @Suite runner
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")

    // Driver layer — reuse whatever the UI project already uses
    testImplementation("com.microsoft.playwright:playwright:1.60.0")  // web (or Selenium 4)
    // testImplementation("io.appium:java-client:10.1.1")             // mobile

    testImplementation("org.assertj:assertj-core:3.26.3")
    // Allure (library default reporting):
    // testImplementation("io.qameta.allure:allure-cucumber7-jvm:2.35.3")
}

tasks.test {
    useJUnitPlatform()
    // Surface step counts; the engine reports per-scenario
    systemProperty("playwright.headless", System.getProperty("playwright.headless", "true"))
}

java {
    toolchain { languageVersion.set(JavaLanguageVersion.of(21)) }
}
```

> Reuse the existing page-object project rather than copying pages. If pages live in a separate Gradle module, add it as `testImplementation(project(":ui-tests"))`; if the BDD layer lives in the same module, the `pom/`/`pages/` classes are already on the test classpath.

### Runner — `src/test/java/com/example/RunCucumberTest.java`

```java
package com.example;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.GLUE_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.PLUGIN_PROPERTY_NAME;

// Idiomatic Cucumber 7 runner: the JUnit 5 Platform engine, NOT @RunWith(Cucumber.class) (JUnit 4, deprecated).
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "com.example.steps,com.example.support")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "pretty, html:target/cucumber-report.html, json:target/cucumber.json")
public class RunCucumberTest {
}
```

### `src/test/resources/junit-platform.properties` — engine config (alternative / complement to the suite)

```properties
cucumber.glue=com.example.steps,com.example.support
cucumber.features=src/test/resources/features
cucumber.plugin=pretty, html:target/cucumber-report.html, json:target/cucumber.json
# Filter at runtime: ./gradlew test -Dcucumber.filter.tags="@smoke and not @wip"
cucumber.filter.tags=not @wip
# Enable the Allure plugin when the project reports through Allure (qa-reporting-java owns this):
# cucumber.plugin=io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm
cucumber.execution.parallel.enabled=false
```

> Living documentation: Cucumber's built-in `html:` formatter writes a self-contained report. For CI dashboards, prefer Allure via `io.qameta.allure:allure-cucumber7-jvm` (plugin `io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm`; Gherkin tags map to Allure labels via `@allure.label.<key>:<value>`) — `qa-reporting-java` owns that wiring.

### `support/TestContext.java` — shared per-scenario state (web)

```java
package com.example.support;

import com.example.pages.DashboardPage;
import com.example.pages.LoginPage;
import com.microsoft.playwright.Page;

// One graph per scenario (PicoContainer builds it fresh, disposes after).
// Holds the Page + lazily-built page objects so every step class shares the same Page.
// No assertions, no logic — just state. Cucumber does NOT support step-class inheritance;
// shared state flows through this object, constructor-injected everywhere.
public class TestContext {
    private Page page;
    private LoginPage loginPage;
    private DashboardPage dashboardPage;

    public Page getPage() {
        return page;
    }

    public void setPage(Page page) {
        this.page = page;
    }

    public LoginPage login() {
        if (loginPage == null) loginPage = new LoginPage(page);
        return loginPage;
    }

    public DashboardPage dashboard() {
        if (dashboardPage == null) dashboardPage = new DashboardPage(page);
        return dashboardPage;
    }
}
```

### `support/Hooks.java` — per-scenario lifecycle (web, with teardown)

```java
package com.example.support;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Playwright;
import io.cucumber.java.After;
import io.cucumber.java.Before;

// PicoContainer injects the same TestContext instance into this Hooks class AND every
// step class for the current scenario. The hook owns the Playwright lifecycle.
public class Hooks {
    private final TestContext context;
    private Playwright playwright;
    private Browser browser;
    private BrowserContext browserContext;

    public Hooks(TestContext context) {
        this.context = context;
    }

    @Before(order = 0)
    public void startBrowser() {
        playwright = Playwright.create();
        boolean headless = Boolean.parseBoolean(System.getProperty("playwright.headless", "true"));
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(headless));
        browserContext = browser.newContext();
        context.setPage(browserContext.newPage());
    }

    @After
    public void stopBrowser() {
        if (browserContext != null) browserContext.close();
        if (browser != null) browser.close();
        if (playwright != null) playwright.close();
    }
}
```

> Tagged hooks scope setup to platform: `@Before("@web")` / `@Before("@mobile")` let one project carry both a web and a mobile hook class without clashing. Always close `context → browser → playwright` in `@After` — a missing teardown leaks browsers/drivers. Launch one `Browser` per run and a fresh `BrowserContext`+`Page` per scenario for speed + isolation once the suite grows; the per-scenario form above is the simplest correct baseline.

### Smoke feature — `src/test/resources/features/smoke.feature`

```gherkin
@smoke
Feature: BDD rig smoke
  Scenario: the rig parses and runs
    Given the BDD rig is wired
    Then it runs a scenario
```

A one-line `SmokeSteps` class (in `bdd-step-bindings`) binds these two steps; the goal is only to prove the engine discovers features, the glue path resolves, and PicoContainer builds the graph.

### Mobile variant (`TestContext` + hook)

For Appium, `TestContext` holds an `AppiumDriver` built in `@Before("@mobile")` via the existing `AppiumDriverFactory`, and quit with `driver.quit()` in `@After("@mobile")`. Page objects extend the existing `BaseAppiumPage`. Spring users would swap `cucumber-picocontainer` for `cucumber-spring` and `@CucumberContextConfiguration` instead — mention as the alternative; PicoContainer is the zero-config default.

## Anti-patterns to flag

- Putting browser/driver lifecycle in step-class constructors instead of `@Before`/`@After` hooks.
- Static mutable state for the page/driver — share it through the injected `TestContext` (library rule: no static mutable state).
- Missing `@After` teardown — leaks browsers/drivers.
- Re-declaring page objects in the BDD layer instead of reusing the existing UI project's classes.
- The deprecated JUnit 4 runner (`@RunWith(Cucumber.class)` / `@Cucumber`) — use the JUnit 5 Platform engine `@Suite`.
- Trying to share state via step-class inheritance — Cucumber does not support it; inject `TestContext`.
- Manually registering glue/DI — PicoContainer is zero-config; the BOM-pinned `cucumber-picocontainer` dependency is the entire wiring.

## Handoffs

- Feature files → `qa/_shared/bdd/gherkin-authoring`
- Step definitions + POM wiring → `qa/java/skills/bdd-step-bindings`
- Page objects → `qa/java/skills/page-object-architect` / `pom-builder` / `appium-page-object`
- Allure reporting → `qa/reporting/java/skills/allure-reporting`
- CI (feature/tag shard, publish report) → `qa/cicd/java/skills/ci-pipelines`
