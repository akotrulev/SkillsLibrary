---
name: ui-project-setup
description: Use when starting a web-UI test project from zero in Java (Playwright or Selenium, TestNG, Gradle, pins). Triggers "scaffold a UI test project". Not for writing tests (ui-tests-playwright).
disable-model-invocation: true
---

# UI Test Project Scaffold (Java 21)

This skill stands up a **runnable, empty web-UI test project from zero**: the Gradle Kotlin DSL build with the exact pins, the layout, the browser install, the `Env` config loader with its override order, the one `BaseTest`, a smoke run, a fat test jar and a container. It owns the **project shell**. The Playwright project files themselves (`build.gradle.kts`, `settings.gradle.kts`, `testng.xml`, `BaseTest.java`, a sample page and test) are the assets of [`ui-test-author/playwright`](../ui-test-author/playwright/SKILL.md): copy them, never re-type them here. This skill adds only `Env`, its defaults file and two build blocks.

**Version rule:** Java 21 (17 minimum), Gradle with the Kotlin DSL; an existing Maven project stays on Maven with the same coordinates. Detect a project's Playwright version and keep it.

Default driver is **Playwright** (auto-waiting, trace viewer, browsers pinned with the library). **Selenium** is the lane for a project that mandates it or needs a Grid; it is authored with `qa/java/skills/ui-test-author/selenium`.

## When to use

- A fresh repo with no Java web-UI test project, and the user wants browser coverage.
- The user asks which versions, layout or setup a Java UI test framework should use.

## When NOT to use

- The project exists → author into it with `qa/java/skills/ui-test-author/playwright` (or `selenium`), `page-object-design`, `page-objects-from-url`.
- API, mobile or desktop scaffolding → `qa/java/skills/api-project-setup`, `mobile-project-setup`, `desktop-project-setup`.
- BDD (Cucumber-JVM) → `qa/java/skills/bdd-project-scaffold`.
- .NET / TypeScript → `qa/dotnet/skills/ui-project-setup` / `qa/typescript/skills/ui-project-setup`.

## Tooling & versions

The Playwright rows are the **Versions** table of `ui-test-author/playwright/SKILL.md`, and its `assets/build.gradle.kts` holds them; `tools/qa-version-check.py` enforces the Playwright and Allure pins.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Language | Java toolchain | **21** | 17 minimum on a down-level repo |
| Build | Gradle (wrapper) | **9.6** | Kotlin DSL |
| Browser driver (default) | `com.microsoft.playwright:playwright` | **1.63.0** | Java 1.64 is not on Maven yet; no 1.64-only API (`within()`: write `parent.locator(child)`) |
| Container | `mcr.microsoft.com/playwright/java` | **v1.63.0-noble** | Browsers preinstalled; the tag always equals the package version |
| Browser driver (alt) | `org.seleniumhq.selenium:selenium-java` | **4.51.0** | Only when mandated; driver setup is `ui-test-author/selenium`'s |
| Test runner | `org.testng:testng` | **7.12.0** | |
| Assertions | `org.assertj:assertj-core` | **3.27.7** | UI state is asserted with Playwright's `assertThat(locator)`, values with AssertJ |
| Reporting | `io.qameta.allure:allure-testng` | **3.0.0** | Gradle plugin `io.qameta.allure` **4.3.0**, `allureJavaVersion.set("3.0.0")` |
| Report generator | `allure-commandline` | **2.46.1** | `allure.version` in the build; the CLI pin on a runner and in the image |

## Prerequisites & local setup

```bash
java --version
docker --version
```

- `java --version` prints 21 (or the repo's 17). Create the wrapper once with a local Gradle (`gradle wrapper --gradle-version 9.6`).
- **Browsers are required** after the first build, or every test errors with "Executable doesn't exist": `./gradlew installPlaywrightBrowsers` (the asset's task; `--with-deps` installs OS packages, so on Linux it needs root or sudo). The container image already has them.
- Docker only for the container run. Selenium needs the real browser on the machine, no install task.

## Project layout

```
ui-tests/
├── build.gradle.kts                 # ui-test-author/playwright/assets/build.gradle.kts + the two blocks below
├── settings.gradle.kts              # assets/settings.gradle.kts: rootProject.name = "ui-tests"
├── testng.xml                       # assets/testng.xml: parallel="classes"
├── Dockerfile · run-tests.sh · .dockerignore   # fat-jar-and-container.md
├── gradlew · gradle/wrapper/
├── .gitignore
└── src/test/
    ├── resources/env.properties     # this skill's assets/env.properties
    └── java/com/example/uitests/
        ├── support/
        │   ├── Env.java             # this skill's assets/Env.java
        │   └── BaseTest.java        # the one lifecycle, failure evidence
        ├── pages/                   # LoginPage.java, HomePage.java; region components beside their page
        ├── components/controls/     # design-system widgets, added at first use
        └── tests/                   # LoginTest.java: the smoke
```

Everything lives in the test source set and every library is `testImplementation`. The folder name `ui-tests` is the one the qa-java rule files match for the build file; as a module of a larger build, `include("ui-tests")` from the root settings.

## Create from zero

```bash
mkdir ui-tests && cd ui-tests
git init
gradle wrapper --gradle-version 9.6
mkdir -p src/test/resources src/test/java/com/example/uitests/{support,pages,tests}
```

Copy from `qa/java/skills/ui-test-author/playwright/assets/`:

| Asset | Goes to |
|---|---|
| `build.gradle.kts`, `settings.gradle.kts`, `testng.xml` | the project root |
| `BaseTest.java` | `support/` |
| `LoginPage.java`, `HomePage.java` | `pages/` |
| `LoginTest.java` | `tests/` |

and from this skill's `assets/`: `Env.java` to `support/`, `env.properties` to `src/test/resources/`. The controls (`DatePicker`, `Dropdown`, `Combobox`, `DataGrid`, `GridRow`) and the orders example are copied when a screen first uses them. Rename the package root `com.example.uitests` in every file and in `testng.xml`.

Point the copied classes at `Env`, three line edits:

| File | Change |
|---|---|
| `BaseTest.java` | `.setBaseURL(requiredEnv("BASE_URL"))` → `.setBaseURL(Env.baseUrl())` |
| `BaseTest.java` | the body of `requiredEnv(name)` → `return Env.required(name);` (the author skills' later code, such as `AuthSetup`, keeps calling it) |
| `LoginTest.java` | `new Credentials(requiredEnv("E2E_USER"), requiredEnv("E2E_PASSWORD"))` → `new Credentials(Env.e2eUser(), Env.e2ePassword())`, importing `support.Env` |

Append the two build blocks: the `-D` forwarding below, and the `fatJar` task from [`fat-jar-and-container.md`](../../../cicd/java/skills/ci-pipelines/references/fat-jar-and-container.md) (it needs `import java.util.Properties` at the top of the file for the forwarding block). Then:

```bash
./gradlew compileTestJava
./gradlew installPlaywrightBrowsers
BASE_URL=https://staging.example.test E2E_USER=qa@example.test E2E_PASSWORD="$E2E_PASSWORD" ./gradlew test --tests '*LoginTest'
```

The exit gate: it compiles, and `LoginTest` is green against a reachable app with a disposable test account. A project whose landing screen is not a login replaces `LoginPage` / `HomePage` with its own pages and keeps the shape: pages built in `@BeforeMethod(alwaysRun = true)`, one behaviour per test, `Should_X_When_Y`.

## Configuration: `Env`

One config class, one constant and one typed getter per key: `BASE_URL`, `E2E_USER`, `E2E_PASSWORD`. **Precedence:** the environment variable, then the JVM system property (`-DBASE_URL=…`), then `src/test/resources/env.properties` read from the classpath. The file holds `BASE_URL`'s local default only; the test account is a secret and comes only from the environment, so `Env` names it when it is missing. `HEADED=1` stays an environment switch read by `BaseTest`.

Gradle forks the test JVM, so the build forwards the `-D` keys the file declares:

```kotlin
val envKeys: Set<String> = Properties()
    .apply { file("src/test/resources/env.properties").inputStream().use { load(it) } }
    .stringPropertyNames()

tasks.test {
    useTestNG {
        suites("testng.xml")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
    envKeys.forEach { key -> System.getProperty(key)?.let { systemProperty(key, it) } }
}
```

This replaces the asset's `tasks.test` block (it keeps its two lines). A new key goes into `Env`, the file (none for a secret) and its caller in one change.

## The base test

`BaseTest` (the asset) is the only Playwright lifecycle: a browser per class, a context and page per test with `BaseURL` from `Env`, tracing started per test, and a screenshot, trace and video kept **only for a failed test** in `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`, each attached to Allure. Instance fields and `parallel="classes"`; no static Playwright, no `ThreadLocal`. Details: `ui-test-author/playwright/references/lifecycle.md`.

## Run

```bash
./gradlew test
./gradlew test -DBASE_URL=https://staging.example.test
HEADED=1 ./gradlew test --tests '*LoginTest'
PWDEBUG=1 ./gradlew test --tests '*LoginTest'
./gradlew playwright --args="show-trace build/playwright-artifacts/LoginTest.Should_GreetUser_When_CredentialsAreValid.zip"
./gradlew clean test allureReport
./gradlew fatJar
java -jar build/libs/ui-tests.jar -testjar build/libs/ui-tests.jar -xmlpathinjar testng.xml -groups smoke
```

- `PWDEBUG=1` opens the Inspector with no timeouts; the `playwright` task runs Playwright's CLI (codegen, show-trace).
- The fat jar, the Dockerfile on `mcr.microsoft.com/playwright/java:v1.63.0-noble` that writes the single-file Allure report and the failure evidence to a mounted volume, and the CI container lane: [`fat-jar-and-container.md`](../../../cicd/java/skills/ci-pipelines/references/fat-jar-and-container.md). Run it with `--ipc=host`.
- The report pin and the single-file option: `qa/reporting/java/skills/test-reports`.

## Selenium lane

Only when the project mandates Selenium: replace the Playwright dependency with `org.seleniumhq.selenium:selenium-java:4.51.0`, drop `installPlaywrightBrowsers` and `playwright`, and build `BasePage`, the `ThreadLocal<WebDriver>` `DriverFactory` and the pages from `qa/java/skills/ui-test-author/selenium` (its driver-setup dependency included). That skill's `pom` package goes under `src/test/java` in a new project, so every library stays `testImplementation`; an existing `src/main/java/pom` stays where it is. `Env`, `env.properties`, the forwarding block, `fatJar` and the container keep their shape; the runtime image is then a JRE plus the browser, or a Selenium Grid reached by URL from `Env`.

## `.gitignore`

```
build/
.gradle/
allure-results/
allure-report/
reports/
.env
```

`build/` covers `build/playwright-artifacts/` and `build/.auth/` (signed-in state, which carries a session and is never committed).

## Conventions (the shell only)

The standards the shell must meet are the qa-java rule files, not a list here: `qa-java.md` (core), `qa-java-ui.md`, `qa-java-page-objects.md` and `qa-java-suite.md`. Tell the user to install them with the shell (`/qa-java:rules` copies them into `.claude/rules/qa-java/`); until then read the plugin's copies in `qa/java/skills/rules/`. Where they and this skill's recipes disagree, the rule files win.

- **Sign in once per role per run** (`AuthSetup`, or `TokenAuthSetup` from `qa/java/skills/test-login-tokens`), never per test.
- Page-object architecture, controls and selectors are `page-object-design` and `ui-test-author/playwright`; reporting is `qa/reporting/java/skills/test-reports`; pipelines are `qa/cicd/java/skills/ci-pipelines`.

## Setup checklist

- [ ] JDK 21 (or the repo's 17); `gradlew` committed with Gradle 9.6
- [ ] Build, settings and `testng.xml` from the Playwright assets; `playwright` 1.63.0; `parallel="classes"`
- [ ] Framework code under `src/test/java`; every library `testImplementation`; package root renamed in code and `testng.xml`
- [ ] `Env` and `env.properties` added; `BaseTest` and `LoginTest` read through `Env`; secrets only in the environment
- [ ] `-D` forwarding block and `fatJar` task appended to the build
- [ ] Browsers installed, or the run uses `mcr.microsoft.com/playwright/java:v1.63.0-noble`
- [ ] Driver chosen deliberately (Playwright default; Selenium only if mandated)
- [ ] `./gradlew compileTestJava` clean; `LoginTest` green against the app
