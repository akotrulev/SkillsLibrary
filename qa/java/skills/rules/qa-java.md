---
paths:
  - "**/{apitests,api-tests,uitests,ui-tests,mobiletests,mobile-tests,e2e,e2e-tests,acceptance-tests,test-automation}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/{tests,pages,pom,screens,components,flows,clients,models,steps,stepdefs,hooks,support,builders,mothers,probes,seeders,llm}/**/*.java"
  - "**/src/main/java/**/pom/**/*.java"
  - "**/src/gatling/**/*.java"
---

<!-- qa-java rules v1 (2026-11-03): core. Installed by /qa-java:rules; edit the paths above to where this project keeps its test suites, re-run to compare with the plugin's copy. -->

# Java test-automation standards

Apply these to every file of a TestNG, RestAssured, Playwright, Selenium, Appium, Cucumber or Gatling suite you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a false result or breaks a security rule, **major** is a design or reliability problem, **minor** is style, **nit** is preference. API, UI, BDD, test-data, performance, suite-config and CI rules are separate files that load with those files; where the be-java `java-tests.md` is installed it still governs unit tests.

**The codebase wins.** Where this suite consistently does something another way, follow it and do not flag it. Detect the versions first: JDK, TestNG, Playwright Java (1.63: no 1.64-only API), Selenium, Appium 3 / java-client 11 (Appium 2 clouds: java-client 10), allure-java, Gatling, Gradle or Maven. Never use a construct the version lacks, and never flag a down-level suite for lacking one.

## Simplicity

- Write the simplest test that proves the behaviour, then stop. No wrapper or DSL over the runner, driver or HTTP client, no base-class hierarchy where a helper does, no fixture with one caller; extract on the second need. *major, fix by inlining*
- Cut structure, never rigour.
- Composition over inheritance. A test never extends a page object; a base class owns infrastructure (driver, context, clients), never domain workflow. *major*

## Lifecycle and isolation

- One base class per suite owns setup; every test class extends it. Constructor injection; no static mutable state (`static WebDriver`, `static Playwright`, a static client); `static final` constants are fine. *blocker for shared driver state, otherwise major*
- Every TestNG configuration method is `alwaysRun = true`. *major*
- Tests are independent: each runs alone and in any order. No `dependsOnMethods`, no shared mutable data, no environment-owned ids ("order 42 exists in staging"). *blocker*
- Data a test needs is created per test with a unique value, tracked, and deleted in `@AfterMethod(alwaysRun = true)`; never an inline `try`/`finally`. *major*

## Assertions and errors

- Every test asserts; one logical behaviour per test. Several assertions on one behaviour go through `SoftAssert` ending in `assertAll()`, or `assertSoftly`. *blocker for none, otherwise major*
- One expected condition per assertion, on a status, field, count, text, URL or duration: no `||` in `assertTrue`, no `anyOf` / `either().or()`, no `"a|b"` regex. Split the test, use a `@DataProvider`, or pin the value. An explicit instruction to accept two values is recorded on the assertion. *major*
- Failures name the subject and carry the evidence: a message argument, AssertJ `.as(...)`, a locator `describe(...)`. *major*
- No `if` or `for` driving assertions; rows that differ only in data are a `@DataProvider`. *major*
- No `try`/`catch` in a `@Test` or a configuration method. An expected exception is `assertThrows` / `assertThatThrownBy`; an unexpected one reaches TestNG. A catch lives only in an I/O helper, narrows one named exception, logs it and never returns a silent default. *major*
- A product defect is reported, never made green by weakening an assertion. *blocker*
- Names state behaviour (`Should_Return401_When_TokenMissing`), never `test1` or `testGetUser`; keep the project's casing. *minor*

## Waiting

- No `Thread.sleep`, `waitForTimeout`, fixed delay or hand-rolled retry loop: wait on a condition (a web-first assertion, `WebDriverWait`, Awaitility). *blocker*
- A job or cut-off test never waits for the real schedule; it drives a controlled clock or a test hook. *blocker*

## Configuration, data and secrets

- No hard-coded base URL, host, credential or token: read config from the environment through the project's loader. A token is fetched once per identity in setup, never inside a test method, client or page. *blocker*
- No secret, token or personal data in a log line, attachment, trace or committed case; test data is synthetic or redacted, and UI runs use a disposable test user. *blocker*
- Objects with four or more fields come from a builder; no literals duplicated across tests. *minor*
- SLF4J placeholders; no `System.out` or `printStackTrace()`. *minor*

## Reporting and flakes

- Tests carry Allure `@Feature`, `@Story` and `@Severity`, groups for area and tier, and the case id in `@Test(description = "TC-…")` when a case document exists. *nit*
- No suite-wide retry (an `IAnnotationTransformer`, a retry listener, Surefire `rerunFailingTestsCount`). `RetryOnce` only on a documented, dated, linked hotspot. *major*
- A flaky test is quarantined, not disabled: `@Test(groups = "flaky")` with `@Issue` and `@Flaky`, still running in a non-gating lane. `enabled = false` only with a linked ticket. A deterministic failure is a bug, never a flake. *major*

## Comments

- No comments in method bodies: no `// Arrange` / `// Act` / `// Assert` banners, step markers, commented-out code or `TODO`. Extract and name the step instead. *minor; major when the comment is wrong*
- A test carries at most three one-line comments: a linked defect id beside a skip or quarantine, an instructed deviation from these rules, the source of a magic value the domain fixes. Javadoc only for a rule, constraint or contract the name cannot carry. *minor*
- A suppression states its reason; scaffold and template comments are removed. *minor*
