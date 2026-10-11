---
name: bdd-project-setup
description: Use when adding the Cucumber-JVM BDD layer onto a Java 21 UI/mobile test project, or standing up a Cucumber-JVM + JUnit 5 project from zero. Triggers: "set up Cucumber", "add a BDD layer to our Playwright/Selenium/Appium tests in Java", "wire Cucumber DI and hooks". Do NOT use to write feature files (`feature-file-writer`), generate step definitions (`gherkin-step-code`), or build page objects (`page-object-design`).
---

# Cucumber-JVM BDD Project Scaffold (Java 21)

Wires **Cucumber-JVM** into a Java 21 + Gradle (Kotlin DSL) test project: the `io.cucumber:*` BOM and packages, the **JUnit 5 Platform** runner (a `@Suite` class + `junit-platform.properties`), the `features/` resource folder, the DI container (**PicoContainer**, zero-config), the per-scenario browser/driver lifecycle hooks, and the shared per-scenario context object that step classes inject. It produces the **empty rig** — no feature files, no step logic; those come from `feature-file-writer` and `gherkin-step-code`.

This is the BDD analogue of the UI project scaffold; it assumes a Playwright (web), Selenium (web), or Appium (mobile) page-object project either exists or will be built by `qa-ui-java` / `qa-mobile-java`.

## Stack (pinned, verify latest at author time)

- Java 21, Gradle (Kotlin DSL `build.gradle.kts`)
- `io.cucumber:cucumber-bom` (pins every `io.cucumber:*`; latest line **7.34.4**)
- `io.cucumber:cucumber-java` (the `@Given/@When/@Then` annotations + Cucumber Expressions)
- `io.cucumber:cucumber-junit-platform-engine` (the idiomatic runner — **not** the deprecated JUnit 4 `@RunWith(Cucumber.class)`)
- `io.cucumber:cucumber-picocontainer` (DI — constructor injection, zero config: just add the dependency)
- `org.junit:junit-bom` + `org.junit.platform:junit-platform-suite` + `junit-platform-launcher` (runtime)
- Web: `com.microsoft.playwright:playwright` (**1.63.0**, sync API — the pin in the **Versions** table of `qa/java/skills/ui-test-author/playwright/SKILL.md`) or Selenium 4 — there is no Playwright Test runner on the JVM, you drive the automation library from step defs. The Cucumber `Hooks` class mirrors J1's `BaseTest` (it cannot extend a TestNG class): `HEADED`, `BASE_URL`, the test-id attribute and the R7 failure evidence
- Mobile: `io.appium:java-client` **11.0.0** (Appium 3) with `selenium-support` ≥ 4.50, the pins in the **Versions** table of `qa/java/skills/ui-test-author/appium/SKILL.md`; java-client 10.x on Appium 2 is the supported lane
- Assertions in `Then` steps: AssertJ / Playwright `assertThat` (match the existing UI project)
- Features under `src/test/resources/features/`; step defs + hooks + context under `src/test/java/.../steps` and `.../support`
- `io.qameta.allure:allure-cucumber7-jvm` **3.0.0** when the project reports through Allure (the library default) — allure-java 3.0, the same major as every other `allure-*` module (Java 17+; the Allure Gradle plugin 4.3.0 rejects mixed 2.x/3.x adapters)

## When to use

- A Java UI/mobile project needs Cucumber-JVM added (BOM, packages, runner, config, hooks, DI).
- Starting a Cucumber-JVM suite from zero.

## When NOT to use

- Writing `.feature` files → `qa/_shared/bdd/feature-file-writer`
- Generating step-definition classes → `qa/java/skills/gherkin-step-code`
- Building page objects → `qa/java/skills/page-object-design` / `page-objects-from-url`
- BDD in .NET/TS → `qa/{dotnet,typescript}/skills/bdd-project-scaffold` (those use Reqnroll / playwright-bdd)

## Inputs needed

Confirm at most 2–3.

1. **Target project path** and whether a Playwright/Selenium/Appium page-object project already exists (reuse it; don't duplicate page objects).
2. **Platform** — web (Playwright/Selenium), mobile (Appium), or both (two hook/context pairs).
3. **Reporting** — Cucumber's built-in HTML formatter (default) or Allure (the library standard).

## Procedure

1. Read 2–3 existing files (the `build.gradle.kts`, an existing page object, `BaseTest`) to match the package, runner, and conventions.
2. Add the Cucumber packages to the test source set via the **BOM** (one pinned version), plus the JUnit Platform suite + launcher and `cucumber-picocontainer`. Set `tasks.test { useJUnitPlatform() }`.
3. Create the runner: a JUnit 5 `@Suite` class (`RunCucumberTest`) that **selects** the features, and `src/test/resources/junit-platform.properties` carrying glue, plugins and the tag filter. **One discovery mechanism**: the `@SelectClasspathResource("features")` selector — never also `cucumber.features`, which makes the engine ignore every discovery selector.
4. Create `support/` : the per-scenario `TestContext` (holds the Playwright `Page` / Selenium `WebDriver` + lazily-built page objects), and the lifecycle `Hooks` class (`@Before`/`@After` that own the browser/driver and the failure evidence — **with teardown**). PicoContainer is zero-config — adding the dependency is the whole wiring step.
5. Create the empty `src/test/resources/features/` folder and one throwaway smoke `.feature` to prove the rig parses and runs.
6. `./gradlew test` (the engine must discover the feature and bind the smoke step) and run the smoke scenario. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
7. Report files created and hand off to `feature-file-writer` (features) + `gherkin-step-code` (steps).

## Templates

### `build.gradle.kts`

```kotlin
plugins {
    java
    id("io.qameta.allure") version "4.3.0"
}

repositories { mavenCentral() }

dependencies {
    testImplementation(platform("io.cucumber:cucumber-bom:7.34.4"))
    testImplementation("io.cucumber:cucumber-java")
    testImplementation("io.cucumber:cucumber-junit-platform-engine")
    testImplementation("io.cucumber:cucumber-picocontainer")

    testImplementation(platform("org.junit:junit-bom:5.11.4"))
    testImplementation("org.junit.platform:junit-platform-suite")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")

    testImplementation("com.microsoft.playwright:playwright:1.63.0")

    testImplementation("org.assertj:assertj-core:3.27.7")
    testImplementation("io.qameta.allure:allure-cucumber7-jvm:3.0.0")
}

allure {
    version.set("2.46.1")
    adapter {
        allureJavaVersion.set("3.0.0")
    }
}

tasks.test {
    useJUnitPlatform()
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
}

tasks.register<JavaExec>("installPlaywrightBrowsers") {
    classpath = sourceSets["test"].runtimeClasspath
    mainClass.set("com.microsoft.playwright.CLI")
    args("install", "--with-deps", "chromium")
}

java {
    toolchain { languageVersion.set(JavaLanguageVersion.of(21)) }
}
```

- The `io.cucumber` BOM pins every `io.cucumber:*` artifact to one version; `cucumber-picocontainer` is the whole
  DI wiring; `junit-platform-suite` provides the `@Suite` runner.
- The driver layer reuses whatever the UI project already uses — Playwright here, or Selenium 4.
- The Allure plugin, report generator (`allure-commandline` 2.46.1) and allure-java 3.0 opt-in are the same as
  J1's build (`ui-test-author/playwright/assets/build.gradle.kts`, plan D38); `allure-cucumber7-jvm` 3.0.0 is the
  Cucumber adapter on that major.
- Headed runs are `HEADED=1 ./gradlew test`; there is no `-Dplaywright.headless` property. The CI references install
  the browser with `./gradlew installPlaywrightBrowsers`.

> Reuse the existing page-object project rather than copying pages. If pages live in a separate Gradle module, add it as `testImplementation(project(":ui-tests"))`; if the BDD layer lives in the same module, the `pom/`/`pages/` classes are already on the test classpath.

### Runner — `src/test/java/com/example/RunCucumberTest.java`

```java
package com.example;

import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
public class RunCucumberTest {
}
```

The idiomatic Cucumber 7 runner: the JUnit 5 Platform engine, not `@RunWith(Cucumber.class)` (JUnit 4,
deprecated). The suite only **selects** the features; every engine setting lives in one file below.

### `src/test/resources/junit-platform.properties` — engine config

```properties
cucumber.glue=com.example.steps,com.example.support
cucumber.plugin=pretty, html:build/cucumber-report.html, json:build/cucumber.json, io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm
cucumber.filter.tags=not @wip
cucumber.execution.parallel.enabled=false
```

- **No `cucumber.features`.** When it is set, the Cucumber engine ignores the discovery selectors — the suite's
  `@SelectClasspathResource` among them — so the suite and the property would be two competing discovery
  mechanisms. The selector is the one.
- Reports land under `build/`, the Gradle output folder, next to `build/allure-results/` and
  `build/playwright-artifacts/`; never `target/`.
- Filter at runtime with `./gradlew test -Dcucumber.filter.tags="@smoke and not @wip"`.
- Drop `io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm` from `cucumber.plugin` when the project does not report
  through Allure; `qa-reporting-java` owns that wiring.
- Scenarios run sequentially. Each one creates and closes its own `Playwright` on its thread, so turning on
  `cucumber.execution.parallel.enabled` later keeps Playwright's thread rule; size the pool to the agent's memory.

> Living documentation: Cucumber's built-in `html:` formatter writes a self-contained report. For CI dashboards, Allure via `allure-cucumber7-jvm` maps Gherkin tags to Allure labels via `@allure.label.<key>:<value>`.

### `support/TestContext.java` — shared per-scenario state (web)

```java
package com.example.support;

import com.example.pages.HomePage;
import com.example.pages.LoginPage;
import com.example.pages.LoginPage.Credentials;
import com.microsoft.playwright.Page;

public class TestContext {
    private Page page;
    private LoginPage loginPage;
    private HomePage homePage;

    public Page page() {
        return page;
    }

    public void setPage(Page page) {
        this.page = page;
    }

    public LoginPage login() {
        if (loginPage == null) loginPage = new LoginPage(page);
        return loginPage;
    }

    public HomePage home() {
        if (homePage == null) homePage = new HomePage(page);
        return homePage;
    }

    public Credentials registeredCustomer() {
        return new Credentials(Hooks.requiredEnv("E2E_USER"), Hooks.requiredEnv("E2E_PASSWORD"));
    }
}
```

One graph per scenario: PicoContainer builds it fresh and disposes it after. It holds the `Page` and the
lazily-built page objects so every step class shares the same `Page` — just state, no assertions. Cucumber does
**not** support step-class inheritance, so shared state flows through this object, constructor-injected into
every glue class. The page objects are the UI suite's own (`ui-test-author/playwright` assets): their constructor
takes the `Page`, never `TestContext`.

### `support/Hooks.java` — per-scenario lifecycle and failure evidence (web, with teardown)

PicoContainer injects the same `TestContext` instance into this class **and** every step class for the current
scenario. The hook owns the Playwright lifecycle and keeps the failure evidence exactly as
`qa/java/skills/evidence-capture` (§ Cucumber scenarios) and J1's `BaseTest` do:

- **`@Before(order = 0)`** — the first hook: `Playwright.create()`, the `data-testid` attribute, Chromium
  headless unless `HEADED=1`, a context on `BASE_URL` recording raw video to `build/playwright-videos/`, tracing
  started (screenshots, DOM snapshots, sources), a page.
- **`@After(order = 0)`** — the last hook (Cucumber runs `@After` hooks from the highest order down, so
  cleanup hooks at the default order still see the page). On `scenario.isFailed()`: a full-page screenshot and
  `tracing().stop(setPath)` **before** `context.close()`; a pass calls `tracing().stop()` with no path, which
  discards the trace. Then `context.close()`, which writes the video; on failure `video.saveAs(...)` — Java's
  `saveAs` throws until the context is closed; `video.delete()` always; `playwright.close()`.
- **Files** are `build/playwright-artifacts/<Feature>.<Scenario>.{png,zip,webm}` — the feature file's name and the
  scenario name, every character outside `[A-Za-z0-9._-]` replaced by `_` — the folder the CI references upload.
  Each kept file is attached with `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`;
  the trace as `application/vnd.allure.playwright-trace`.
- **The one catch** is `keepScreenshot`'s: a narrow `PlaywrightException` catch, logged with a message template,
  in a private helper (plan D29) — a crashed page cannot be photographed, and its trace and video must still be
  kept. No other catch, and none in the hook bodies.

The class — `requiredEnv`, `openBrowser`, `closeBrowser(Scenario)` and the private `keep*` helpers mirroring
`BaseTest`'s — is in [`references/hooks.md`](references/hooks.md), with the Scenario Outline and parallel notes.
`<Feature>` is the feature file's name: Cucumber-JVM's `Scenario` exposes the file's URI, not the `Feature:` title.

### Smoke feature — `src/test/resources/features/smoke.feature`

```gherkin
@smoke
Feature: BDD rig smoke
  Scenario: the rig parses and runs
    Given the BDD rig is wired
    Then it runs a scenario
```

A one-line `SmokeSteps` class (in `gherkin-step-code`) binds these two steps; the goal is only to prove the engine discovers features, the glue path resolves, and PicoContainer builds the graph.

### Mobile variant (`TestContext` + hook)

For Appium, `TestContext` holds the scenario's `AppiumDriver`, built in `@Before("@mobile")` through the project's `AppiumDriverFactory` and quit in `@After("@mobile")`. A mobile project replaces the Playwright line of the `build.gradle.kts` above with:

```kotlin
    testImplementation("io.appium:java-client:11.0.0")
    testImplementation("org.seleniumhq.selenium:selenium-support:4.51.0")
```

Page objects extend the existing `BaseAppiumPage` and take the **driver**, never `TestContext`. The hook, its failure evidence and its `<feature file>.<scenario>` names (D72) are in `references/hooks.md` § Mobile hook: the files land in `build/appium-artifacts/`. Spring users would swap `cucumber-picocontainer` for `cucumber-spring` and `@CucumberContextConfiguration` instead — mention as the alternative; PicoContainer is the zero-config default.

## Anti-patterns to flag

- Putting browser/driver lifecycle in step-class constructors instead of `@Before`/`@After` hooks.
- Static mutable state for the page/driver — share it through the injected `TestContext` (library rule: no static mutable state).
- Missing `@After` teardown — leaks browsers/drivers.
- Re-declaring page objects in the BDD layer instead of reusing the existing UI project's classes.
- The deprecated JUnit 4 runner (`@RunWith(Cucumber.class)` / `@Cucumber`) — use the JUnit 5 Platform engine `@Suite`.
- Trying to share state via step-class inheritance — Cucumber does not support it; inject `TestContext`.
- Manually registering glue/DI — PicoContainer is zero-config; the BOM-pinned `cucumber-picocontainer` dependency is the entire wiring.

## Handoffs

- Feature files → `qa/_shared/bdd/feature-file-writer`
- Step definitions + POM wiring → `qa/java/skills/gherkin-step-code`
- Page objects → `qa/java/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Allure reporting → `qa/reporting/java/skills/test-reports`
- Failure-evidence rules the `Hooks` class follows, and reading a scenario's trace → `qa/java/skills/evidence-capture`
- CI (feature/tag shard, publish report) → `qa/cicd/java/skills/ci-pipelines`
