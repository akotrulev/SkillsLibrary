---
paths:
  - "**/testng*.xml"
  - "**/src/test/resources/{allure,junit-platform,cucumber}.properties"
  - "**/src/test/resources/categories.json"
  - "**/{apitests,api-tests,uitests,ui-tests,mobiletests,mobile-tests,e2e,e2e-tests,acceptance-tests,test-automation,perf-tests}/{build.gradle.kts,build.gradle,pom.xml}"
  - "**/config/checkstyle/*.xml"
---

<!-- qa-java rules v2 (2026-11-21): suite config, build and lint. Ids checked against the tools' documentation on 2026-11-21 (Checkstyle 14.4, Error Prone 2.53, Gradle 9.6). Installed by /qa-java:rules; add this project's test-module build files and Checkstyle config to the paths above, re-run to compare with the plugin's copy. -->

# Test suite configuration standards

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## TestNG

- Playwright and Appium suites run `parallel="classes"`, never `parallel="methods"`. Appium `thread-count` never exceeds the device count. *blocker*
- Suites sharing one Testcontainers instance run `parallel="false"`. *major*
- The gating run excludes the `flaky` group; a separate non-gating task runs it with `ignoreFailures = true`. *major*

## Allure

- allure-java 3 on every `allure-*` module, no 2.x module beside it; one adapter per module (never `allure-testng` with `allure-jupiter`). *major*
- One pinned report generator, the same version in the build and in CI. *major*
- `categories.json` lists the quarantine category first, matching `"flaky": true`, never an exception type. *minor*
- `build/allure-results/` is an artifact, never committed. *minor*

## Build

- Every plugin and dependency is pinned: no `+`, `latest.release` or floating Gatling plugin. *major*
- Gradle Kotlin DSL for a new suite; Maven only where the project uses it; never both in one module. Extend the suite's build file, never start a second one. *minor*
- Appium java-client 11 declares `selenium-support` for `WebDriverWait`. *major*
- Cucumber modules come from one BOM, with `cucumber-picocontainer` as the whole DI wiring. *minor*

## Enforced by the build

Each row is a rule of `qa-java.md` that Checkstyle detects, so the build catches it before a review does. Rules no stock check detects stay in that file and get no row: one expected condition per assertion, intent-named page objects, static mutable state, `enabled = false` without a ticket. Error Prone gets no row: its `EmptyCatch` passes a block that holds only a comment, so it sees less than `EmptyCatchBlock` below, and `CatchFail` did not fire on TestNG's `Assert.fail`.

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `Thread.sleep`, `TimeUnit.<unit>.sleep` or `waitForTimeout` (`qa-java.md`, Waiting) | Checkstyle | `RegexpSinglelineJava`, id `NoSleep` | error |
| A test body has no `if`, `else`, `switch`, ternary or loop (`qa-java.md`, Assertions and errors) | Checkstyle | `IllegalToken`, id `TestBodyLinear`, with the `@Test` suppression below | error |
| A test or configuration method has no `try` (`qa-java.md`, Assertions and errors) | Checkstyle | `IllegalToken`, id `TestHasNoTry`, with the suppression below | error |
| No empty `catch`; a block holding only a comment is empty (`qa-java.md`, Assertions and errors) | Checkstyle | `EmptyCatchBlock`, `commentFormat` `^$` | error |
| A `catch` names one exception, never `Exception`, `Throwable`, `RuntimeException` or `Error` (`qa-java.md`, Assertions and errors) | Checkstyle | `IllegalCatch` | error |
| No `dependsOnMethods` (`qa-java.md`, Lifecycle and isolation) | Checkstyle | `RegexpSinglelineJava`, id `NoDependsOnMethods` | error |
| Every TestNG configuration method is `alwaysRun = true` (`qa-java.md`, Lifecycle and isolation) | Checkstyle | `RegexpSinglelineJava`, id `ConfigAlwaysRun` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each row is a module in `config/checkstyle/checkstyle.xml` at `severity` `error`, and the Gradle `checkstyle` plugin runs it as `checkstyleTest` with `toolVersion = "14.4.0"`.
- The two `IllegalToken` rows flag every method, so each carries a `SuppressionXpathSingleFilter` that keeps its violations only inside a method annotated `@Test` (`TestBodyLinear`) or `@Test` and the TestNG configuration annotations (`TestHasNoTry`). A page object, client, driver factory or teardown registry branches and loops as the house rules allow, and the same code in a `@Test` method fails. The query matches the annotation's simple name. A configuration method may branch and may not `try`.
- `IllegalToken` has no message property, so its violation reads `Using 'if' is not allowed.` and carries the row's id in brackets.
- The `RegexpSinglelineJava` rows match one line at a time, with comments skipped. `NoSleep` misses a statically imported `sleep(…)`. `ConfigAlwaysRun` reads the annotation's own line, so `alwaysRun = true` on the next line is a false positive: write the annotation on one line.
- A base class, driver factory or teardown registry that must catch broadly carries `@SuppressWarnings("checkstyle:IllegalCatch")`, which needs the `SuppressWarningsFilter` and `SuppressWarningsHolder` modules in the config below.
- Checkstyle lints every directory the source set names, generated sources included: a generated client added with `srcDir` reported `NoSleep` and `IllegalCatch`. The Gradle task excludes the generated package by its path inside the source directory, as `tasks.checkstyleTest { exclude("gen/**") }`, and the report then lists nothing from it.

`config/checkstyle/checkstyle.xml`:

```xml
<?xml version="1.0"?>
<!DOCTYPE module PUBLIC "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN" "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker">
  <property name="severity" value="error"/>
  <module name="SuppressWarningsFilter"/>
  <module name="TreeWalker">
    <module name="SuppressWarningsHolder"/>
    <module name="SuppressionXpathSingleFilter">
      <property name="id" value="TestBodyLinear"/>
      <property name="query" value="//*[not(ancestor-or-self::METHOD_DEF/MODIFIERS/ANNOTATION/IDENT[@text='Test'])]"/>
    </module>
    <module name="SuppressionXpathSingleFilter">
      <property name="id" value="TestHasNoTry"/>
      <property name="query" value="//*[not(ancestor-or-self::METHOD_DEF/MODIFIERS/ANNOTATION/IDENT[@text=('Test','BeforeMethod','AfterMethod','BeforeClass','AfterClass','BeforeSuite','AfterSuite','BeforeTest','AfterTest')])]"/>
    </module>
    <module name="IllegalToken">
      <property name="id" value="TestBodyLinear"/>
      <property name="tokens" value="LITERAL_IF, LITERAL_ELSE, LITERAL_SWITCH, QUESTION, LITERAL_FOR, LITERAL_WHILE, LITERAL_DO"/>
    </module>
    <module name="IllegalToken">
      <property name="id" value="TestHasNoTry"/>
      <property name="tokens" value="LITERAL_TRY"/>
    </module>
    <module name="EmptyCatchBlock">
      <property name="commentFormat" value="^$"/>
    </module>
    <module name="IllegalCatch"/>
    <module name="RegexpSinglelineJava">
      <property name="id" value="NoSleep"/>
      <property name="format" value="\bThread\.sleep\s*\(|\bTimeUnit\.\w+\.sleep\s*\(|\.waitForTimeout\s*\("/>
      <property name="ignoreComments" value="true"/>
      <property name="message" value="Wait on a condition, never sleep"/>
    </module>
    <module name="RegexpSinglelineJava">
      <property name="id" value="NoDependsOnMethods"/>
      <property name="format" value="\bdependsOnMethods\b"/>
      <property name="ignoreComments" value="true"/>
      <property name="message" value="A test runs alone and in any order"/>
    </module>
    <module name="RegexpSinglelineJava">
      <property name="id" value="ConfigAlwaysRun"/>
      <property name="format" value="@(Before|After)(Method|Class|Suite|Test|Groups)\b(?!\s*\(.*\balwaysRun\s*=\s*true)"/>
      <property name="ignoreComments" value="true"/>
      <property name="message" value="A TestNG configuration method is alwaysRun = true"/>
    </module>
  </module>
</module>
```
