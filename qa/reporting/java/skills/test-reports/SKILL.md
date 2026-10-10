---
name: qa-test-reports-java
description: Use when setting up Allure reporting for a Java test suite (TestNG + RestAssured, TestNG + Playwright Java, TestNG + Selenium Java, TestNG + Appium Java, JUnit Jupiter) on allure-java 3.0. Triggers: "set up Allure for our Gradle TestNG project", "wire Allure attachments in Java", "publish Allure report from our Java CI". Not for flaky-test quarantine (`qa-flaky-test-quarantine-java`), pipeline YAML (`qa-ci-pipelines-java`) or Playwright failure evidence (`qa-evidence-capture-java`).
---

# QA — Allure Reporting (Java / TestNG & JUnit Jupiter)

Wires Allure into a Java 21 test project (TestNG primary, JUnit Jupiter secondary) on **allure-java 3.0** —
adapter, `@Step` weaving, attachments, the `@Feature` / `@Story` / `@Severity` hierarchy, CI publish, history,
triage categories. Playwright's failure evidence is not wired here: J1's `BaseTest` keeps and attaches it.

## When to use

- A new Java test project (Gradle Kotlin DSL preferred) needs a reporting story
- A suite emits plain test XML and the team wants attachments + history
- An existing suite moves from allure-java 2.x to 3.0
- CI does not publish reports; PRs have no test artifacts

## When NOT to use

- .NET reporting → `qa/reporting/dotnet/skills/test-reports`
- TypeScript reporting → `qa/reporting/typescript/skills/test-reports`
- Playwright screenshots, traces, video, HAR → `qa/java/skills/evidence-capture` (owned by `BaseTest`)
- Writing tests → `qa/java/skills/api-test-author/writer` / `qa/java/skills/ui-test-author/<tool>`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`

## Versions

One pin set. Every Allure coordinate in this skill, and in every Java skill, uses these.

| Artifact | Version | Note |
|---|---|---|
| `io.qameta.allure` Gradle plugin | **4.3.0** | The first release with Allure Java 3 support (2026-09-17). Its adapter default stays 2.x, so the build opts in with `allureJavaVersion.set("3.0.0")` |
| Every `io.qameta.allure:allure-*` module (`allure-testng`, `allure-jupiter`, `allure-rest-assured`, `allure-cucumber7-jvm`, …) | **3.0.0** | Java 17+ for the test JVM; TestNG 7.10+. One major per test runtime — the plugin rejects 2.x and 3.x adapters on one classpath |
| Report generator | **allure2 `allure-commandline` 2.46.1** (Allure Report 2) | `allure.version` in Gradle; `npm i -g allure-commandline@2.46.1` in CI, on a runner with a Java runtime. The same pin as `qa/cicd/ci-conventions` |
| TestNG | 7.12.0 | |

Checked 2026-10-10: Allure's *Migrating to Allure Java 3* guide says Allure Java 3 results open in Allure Report
2 and 3 and the file format is unchanged; allure2 2.46.0 renders the run-level errors 3.0 writes. So Java keeps
the one cross-stack generator pin, not the plugin's default (Allure Report 3).

Adapters: `allure-testng` (TestNG, the default), `allure-jupiter` (JUnit 5 and 6), `allure-rest-assured` (the
HTTP filter), `allure-cucumber7-jvm` (Cucumber-JVM 7). Each writes `build/allure-results/`.

## Install (Gradle Kotlin DSL, TestNG)

The Playwright UI module already has this in `qa/java/skills/ui-test-author/playwright/assets/build.gradle.kts`;
an API module adds the same block:

```kotlin
plugins {
    java
    id("io.qameta.allure") version "4.3.0"
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("io.qameta.allure:allure-testng:3.0.0")
    testImplementation("io.qameta.allure:allure-rest-assured:3.0.0")
    testImplementation("org.testng:testng:7.12.0")
}

allure {
    version.set("2.46.1")
    adapter {
        allureJavaVersion.set("3.0.0")
    }
}

tasks.test {
    useTestNG()
}
```

- `allure.version` selects the report generator: `2.x` is allure2's `allure-commandline`, `3.x` Allure Report
  3. It is set to the cross-stack pin so `./gradlew allureReport` and `allureServe` build the same report as
  CI.
- The plugin's `autoconfigure` and `aspectjWeaver` are on by default; the weaver makes `@Step("…")` work —
  never turn it off.
- allure-java 3.0 no longer cleans the results folder: locally run `./gradlew clean test`.

## Moving from allure-java 2.x

| 2.x | 3.0 |
|---|---|
| `Allure.addAttachment(name, type, stream, "png")` | `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension("png"))` |
| `Allure.addAttachment(name, content)` | `Allure.attachment(name, content)` |
| `Allure.addDescription(...)` / `addLabels(...)` / `addLinks(...)` | `Allure.description(...)` / `Allure.label(name, value)` / `Allure.link(name, type, url)` |
| `allure-junit5` | `allure-jupiter` |
| Request and response as two HTML attachments, customized with templates | One HTTP exchange attachment (an interactive viewer); templates removed — redact with `configureHttpExchange()` |
| `allure.results.clean.before.run` | Removed; the build tool cleans |

- **History restarts once for TestNG.** allure-java 3.0 computes TestNG, JUnit 4 and JBehave test
  identifiers differently, so the first report after the upgrade shows those tests as new. JUnit Jupiter,
  Cucumber-JVM and Spock keep their history.
- **A runtime parameter now changes a test's identity.** A value that changes every run (a timestamp, a
  random id) is excluded: `Allure.parameter("startedAt", startedAt, true)`.
- **Attachments are shown as steps**, in the order they were created among the other steps.

## Hierarchy: Feature → Story → Test

Behavior view (stakeholders): **Epic → Feature → Story**. Suite view (engineers): **Suite → Class → Method**.

| Annotation | Use |
|---|---|
| `@Epic("Orders")` | Cross-feature theme (rare) |
| `@Feature("Refunds")` | User-facing feature under test |
| `@Story("Issue partial refund")` | User-story slice |
| `@Severity(SeverityLevel.BLOCKER / CRITICAL / NORMAL / MINOR / TRIVIAL)` | Triage signal |
| `@Description("…")` | Long description / link to spec |
| `@Issue("ORDERS-512")` / `@TmsLink("TC-456")` | Bidirectional links |
| `@Tag("smoke")` (JUnit Jupiter) or `@Test(groups = {...})` (TestNG) | Filters |

```java
@Feature("Refunds")
public class RefundTests extends BaseApiTest {

    @Test(groups = "regression")
    @Story("Issue partial refund")
    @Severity(SeverityLevel.CRITICAL)
    @Issue("ORDERS-512")
    public void Should_IssuePartialRefund_When_AmountIsBelowOrderTotal() {
        Refund refund = refunds.issue(Orders.paid().withTotal(2000).build(), 500);

        assertThat(refund.status()).as(refund.toString()).isEqualTo(RefundStatus.ISSUED);
    }
}
```

Severity = **test** severity. `BLOCKER` = "ship is blocked if this fails"; `NORMAL` = "regression on a non-critical flow".

## Attachments (mandatory on failure path)

| Attachment | When | Who attaches it |
|---|---|---|
| HTTP exchange (request + response) | Every API test | The `AllureRestAssured` filter, automatically |
| Screenshot, trace, video | Playwright UI tests, on failure | J1's `BaseTest` — nothing to add here |
| Screenshot | Selenium UI tests, on failure | The Selenium base test's `@AfterMethod` |
| Server logs around the test window | Optional | A link to Loki (LogQL), never a multi-MB file |

### API tests — `AllureRestAssured` filter

Register once in `BaseApiClient`:

```java
public abstract class BaseApiClient {
    protected RequestSpecification spec() {
        return RestAssured.given()
            .baseUri(baseUri)
            .header("Authorization", "Bearer " + jwt)
            .filter(new AllureRestAssured());
    }
}
```

Each exchange attaches automatically.

### Playwright Java — defer to `BaseTest`

**Write no failure attacher for Playwright.** `qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`
starts tracing in `@BeforeMethod` and, in its one `@AfterMethod`, keeps a full-page screenshot, the trace and
the video of a failed test in `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}` and attaches each:

| File | Allure type | Shown as |
|---|---|---|
| `.png` | `image/png` | Inline image |
| `.zip` | `application/vnd.allure.playwright-trace` | Opens in the Playwright trace viewer (allure2 2.44+; the viewer page needs internet access, the trace is not uploaded) |
| `.webm` | `video/webm` | Inline video |

A second attacher runs in an undefined order against `BaseTest.closeContext`, photographs a closed page or
stops a stopped trace, and its exception hides the real failure. Recordings and reading a trace:
`qa/java/skills/evidence-capture`.

### Selenium Java — screenshot on failure

```java
@AfterMethod(alwaysRun = true)
public void screenshotOnFailure(ITestResult result) {
    if (result.getStatus() == ITestResult.FAILURE) {
        byte[] png = ((TakesScreenshot) driver).getScreenshotAs(OutputType.BYTES);
        Allure.attachment("screenshot", "image/png", new ByteArrayInputStream(png), AttachmentOptions.withFileExtension("png"));
    }
}
```

## Steps — `@Step` on page object methods

```java
public final class LoginPage {
    @Step("Sign in as {credentials.email}")
    public void signIn(Credentials credentials) {
        goTo();
        signInForm.submit(credentials);
    }
}
```

`{credentials.email}` is interpolated via AspectJ from the method's arguments, which is why the weaver stays
on. The page object is J1's `assets/LoginPage.java`; only the annotation is added.

For inline steps: `Allure.step("Sign in", () -> loginPage.signIn(credentials));`.

## Report CLI

One pin: `allure-commandline@2.46.1`. In Gradle, `allure.version` above; in CI,
`npm i -g allure-commandline@2.46.1` on a runner with a Java runtime, then:

```bash
allure generate allure-results -o allure-report --clean
```

A shard matrix copies every shard's `build/allure-results/` into one folder before `generate`; new files are
added to the existing ones.

## CI integration

The pattern is identical regardless of CI:

1. `./gradlew test` → `build/allure-results/` written.
2. Upload `build/allure-results/` as an artifact, **always** (even on failure).
3. Copy the previous report's `history/` into `allure-results/history/`.
4. `allure generate allure-results -o allure-report --clean`.
5. Publish to GitHub Pages / GitLab Pages / an Azure static page.

The full platform YAML — sharding, the `build/playwright-artifacts/` failure upload, and the Azure Pipelines
and GitLab CI publish jobs — lives in `qa/cicd/java/skills/ci-pipelines`. The GitHub Actions publish step,
for reference:

```yaml
- uses: actions/setup-java@v5
  with: { distribution: temurin, java-version: '21' }

- name: Restore prior history from gh-pages
  uses: actions/checkout@v6
  with: { ref: gh-pages, path: gh-pages-prior }
  continue-on-error: true

- name: Generate Allure report with history
  if: always()
  run: |
    npm i -g allure-commandline@2.46.1
    mkdir -p allure-results/history
    cp -r gh-pages-prior/history/. allure-results/history/ 2>/dev/null || true
    allure generate allure-results -o allure-report --clean

- name: Publish Allure report
  if: always() && github.ref == 'refs/heads/main'
  uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_branch: gh-pages
    publish_dir: allure-report
```

## History & trends

Trend graphs require a `history/` folder inside `allure-results/` populated from the previous run. The smoke
test is "does the trend chart in the published report show > 1 bar". Keep the last 20–30 runs.

## Categories for triage — `categories.json`

Place at `src/test/resources/categories.json`. The Allure Gradle plugin detects it there and its
`copyCategories` task copies it into the raw results folder:

```json
[
  { "name": "Backend 5xx",       "matchedStatuses": ["broken", "failed"], "messageRegex": ".*Status.*5\\d\\d.*" },
  { "name": "Auth issues",       "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*UnauthorizedException.*|.*ForbiddenException.*" },
  { "name": "Timeouts",          "matchedStatuses": ["broken"],           "traceRegex":   ".*TimeoutException.*|.*PlaywrightException.*Timeout.*" },
  { "name": "Element not found", "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*NoSuchElementException.*|.*ElementNotFound.*" }
]
```

A timeout is a failure class, not a flakiness verdict. The quarantine bucket (`"flaky": true`) is
`qa/reporting/java/skills/flaky-test-quarantine`'s, and it goes first, because the first matching category
wins.

## Rules

- allure-java **3.0.0** on every `allure-*` module, opted in through the plugin's `allureJavaVersion`; no 2.x
  module beside it.
- `Allure.attachment(..., AttachmentOptions.withFileExtension(ext))` for every attachment. `Allure.addAttachment(...)`
  does not exist in 3.0.
- One report generator: `allure-commandline` 2.46.1, as `allure.version` in Gradle and the npm pin in CI,
  equal to `qa/cicd/ci-conventions`.
- `AllureRestAssured` filter wired in `BaseApiClient` — the HTTP exchange attaches automatically.
- Every test has `@Feature` + `@Story` + `@Severity`.
- Playwright failure evidence is `BaseTest`'s; this skill adds no Playwright hook, listener or attacher.
- `build/allure-results/` uploaded as a CI artifact on **every** run, even on test failure.
- History preserved across runs (last 20–30 retained).
- Report published from `main` to a stable URL; PR builds publish to a PR-scoped URL or skip publish.
- Gradle Kotlin DSL preferred; Maven only if mandated.

## What NOT to do

- No "always pass" wrappers around `./gradlew test` — no `continue-on-error` / `continueOnError` / `|| true` on the test step. The test step fails the build; the upload and publish steps run anyway (`if: always()` / `condition: succeededOrFailed()` / `when: always`).
- No committing `build/allure-results/` to Git — it's an artifact.
- No `@Feature("misc")` catch-all bucket.
- No `@Description` that paraphrases the test name — describe behavior or link the spec.
- No attaching secrets / PII / auth tokens — sanitize before `Allure.attachment(...)`; redact the HTTP exchange with `configureHttpExchange()`.
- No multiple Allure adapters in the same Gradle module (e.g. `allure-testng` and `allure-jupiter` together) — pick one.
- No 5-MB-per-test logs attached — link to Loki instead.
- No mixing the `AllureRestAssured` filter with manually-attached request/response bodies — duplicates entries.
- No unpinned or second Allure generator (an allure2 tarball download, a `simple-elf/allure-report-action` that bundles its own, `allure.version` left at the plugin default).

## Generation steps

1. Confirm runner (TestNG vs JUnit Jupiter), CI, publishing target, feature/severity taxonomy.
2. Apply the Gradle Kotlin DSL block above (plugin 4.3.0, `allure.version` 2.46.1, `allureJavaVersion` 3.0.0).
3. Add the `AllureRestAssured` filter to `BaseApiClient`.
4. Add `@Feature` + `@Story` + `@Severity` annotations to existing tests.
5. UI: confirm the project's `BaseTest` matches J1's; add nothing for Playwright evidence.
6. Drop `categories.json` into `src/test/resources/`.
7. Wire CI per the snippet for the team's CI platform; configure history retention.
8. Smoke a green build + a deliberate failing test; confirm trend, categories, attachments populate.

Inside a `Gate: none` plan task, skip the smoke run in the last step and report the wiring as "written, not run".

## Handoffs

- Playwright failure evidence, recordings, reading a trace → `qa/java/skills/evidence-capture`
- .NET Allure → `qa/reporting/dotnet/skills/test-reports`
- TypeScript Allure → `qa/reporting/typescript/skills/test-reports`
- Flaky detection and quarantine → `qa/reporting/java/skills/flaky-test-quarantine`
- API test generation → `qa/java/skills/api-test-author/writer`
- UI test generation → `qa/java/skills/ui-test-author/playwright` / `qa/java/skills/ui-test-author/selenium` / `qa/java/skills/ui-test-author/appium`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`
- CI pipeline syntax → `qa/cicd/java/skills/ci-pipelines` (its `references/<ci>.md`) or `devops/<ci>`
