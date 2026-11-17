---
paths:
  - "**/{apitests,api-tests,uitests,ui-tests,mobiletests,mobile-tests,desktop-tests,e2e,e2e-tests,acceptance-tests,test-automation}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/{tests,pages,screens,components,flows,clients,models,steps,stepdefs,hooks,support,builders,mothers,probes,seeders,llm}/**/*.java"
  - "**/src/{main,test,integrationTest}/java/**/{pom,windows,action*,pojo*,poco*,factory,factories}/**/*.java"
  - "**/src/gatling/**/*.java"
---

<!-- qa-java rules v2 (2026-11-17): core. Installed by /qa-java:rules; fit the paths above to the project. -->

# Java test-automation standards

Apply to every test-suite file you write, edit or review. A rule's tag is its review severity: **blocker** ships a false result or breaks a security rule, **major** is a design or reliability problem, **minor** is style, **nit** is preference. be-java's `java-tests.md`, where installed, governs unit tests.

**The codebase wins**: follow what this suite consistently does; do not flag it. Detect versions first: JDK, TestNG, Playwright Java (1.63: no 1.64-only API), Selenium, Appium 3 / java-client 11, allure-java, Gatling, Gradle or Maven. Never use a construct the version lacks, nor flag a down-level suite for lacking one.

## Simplicity

- The simplest test that proves the behaviour: no wrapper or DSL over the runner, driver or HTTP client, no speculative base class; cut structure, never rigour. *major*
- Page objects, components, clients, builders and fixtures are the suite's structure: created at first use, never inlined; a review does not count callers. *major*
- Each reusable piece is named for its role (page, component, client, flow, builder, ObjectMother, fixture, seeder, probe, token provider, driver factory, `Env`, wait condition, assertions), never `Helper`, `Util(s)`, `Utility`, `Common` or `Misc`; third-party names stay. *major*
- Composition over inheritance: a test never extends a page object; a base class owns infrastructure, not domain workflow. *major*

## Lifecycle and isolation

- One base class per suite owns setup; every test class extends it. Constructor injection; no static mutable state (`static WebDriver`, `static Playwright`). *blocker for shared driver state, otherwise major*
- Every TestNG configuration method is `alwaysRun = true`. *major*
- Tests are independent: each runs alone and in any order. No `dependsOnMethods`, no shared mutable data, no environment record but `qa-java-data.md` reference data. *blocker*
- Data a test changes is created per test with a unique value, tracked, and deleted in `@AfterMethod(alwaysRun = true)` (kept on failure: `qa-java-data.md`), never an inline `finally`. *major*

## Assertions and errors

- Every test asserts; one logical behaviour per test. Several checks of one behaviour: `SoftAssert` + `assertAll()` or `assertSoftly`. *blocker for none, otherwise major*
- One expected condition per assertion: no `||`, `anyOf`, `either().or()` or `"a|b"` regex; split the test, use a `@DataProvider` or pin the value; an instruction to accept two values is recorded on it. *major*
- Failures name the subject and carry evidence: a message, AssertJ `.as(...)`, `describe(...)`. *major*
- A test body is linear: no `if`, `else`, `switch`, ternary, loop or `try`. Setup reaches the screen, signs in, creates data; the body is the action and outcome. Vary by `@DataProvider` row, second method or class, or setup. Only infrastructure branches: base test, config loader, driver factory, platform finder, teardown registry, row source. A test class holds tests, setup, teardown and fields, never a private method that drives the app or builds data. *major*
- No `try`/`catch` in a test or configuration method: an expected exception is `assertThatThrownBy`, others reach TestNG. Only a client, seeder, probe, base class, driver factory or teardown registry catches: one named exception, logged, no silent default. *major*
- A product defect is reported, never greened by weakening an assertion. *blocker*
- Names state behaviour (`Should_Return401_When_TokenMissing`), never `test1` or `testGetUser`; keep the project's casing. *minor*

## Waiting

- No `Thread.sleep`, `waitForTimeout`, fixed delay or hand-rolled retry loop: wait on a condition (web-first assertion, `WebDriverWait`, Awaitility). *blocker*
- A job or cut-off test drives a controlled clock or test hook, never the real schedule. *blocker*

## Config, data and secrets

- No hard-coded URL, host, credential or token: read it through `Env` or the config class. A token is fetched once per identity in setup, never in a test, client or page. *blocker*
- No secret, token or personal data in a log, attachment, trace or committed case; test data is synthetic or redacted; UI runs use a disposable user. *blocker*
- Objects with 4+ fields come from a builder; no literals duplicated across tests. *minor*
- SLF4J placeholders, no `System.out` or `printStackTrace()`. *minor*

## Reporting and flakes

- Tests carry Allure `@Feature`, `@Story` and `@Severity`, groups for area and tier, and the case id in `description = "TC-…"` if any. *nit*
- No suite-wide retry (a transformer, listener or `rerunFailingTestsCount`). `RetryOnce` only on a documented, dated, linked hotspot. *major*
- A flaky test is quarantined, not disabled: `@Test(groups = "flaky")` with `@Issue` and `@Flaky`, in a non-gating lane. `enabled = false` only with a linked ticket. A deterministic failure is a bug, never a flake. *major*

## Comments

- No comments in method bodies: no Arrange/Act/Assert banners, step markers, commented-out code or `TODO`. Move the step onto the object that owns it. *minor; major when the comment is wrong*
- A test's only comments (one line each, at most three): a defect id by a skip or quarantine, an instructed deviation, the source of a domain-fixed magic value. Javadoc only for a rule, constraint or contract the name cannot carry. *minor*
- A suppression states its reason; scaffold comments are removed. *minor*
