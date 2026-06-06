---
name: qa-allure-reporting-java
description: Use when the user asks to set up Allure reporting for a Java test suite (TestNG + RestAssured, TestNG + Playwright Java, TestNG + Selenium Java, TestNG + Appium Java, JUnit 5) — install `allure-testng` / `allure-junit5` via Gradle, wire failure attachments (request/response body, screenshots, traces), feature/story/severity hierarchy with `@Feature` / `@Story` / `@Severity`, AspectJ weaver, and publish to GitHub Pages / GitLab Pages / Azure Pipelines. Triggers: "set up Allure for our Gradle TestNG project", "wire Allure attachments in Java", "publish Allure report from our Java CI", "design Allure feature/story for TestNG tests". Do NOT use for .NET reporting (use `qa/dotnet/skills/allure-reporting`), TypeScript reporting (use `qa/typescript/skills/allure-reporting`), writing tests (use the matching `qa/<topic>` skill), or test strategy (use `qa/manual/test-strategy`).
---

# QA — Allure Reporting (Java / TestNG & JUnit 5)

Wires Allure into a Java 21 test project (TestNG primary, JUnit 5 secondary) — `io.qameta.allure:allure-testng` / `allure-junit5`, AspectJ weaver for step capture, failure-path attachments, behavior-first hierarchy (`@Feature` / `@Story` / `@Severity`), CI publish, history, and triage categories.

## When to use

- A new Java test project (Gradle Kotlin DSL preferred) needs a reporting story
- An existing TestNG / JUnit 5 suite emits plain test XML and the team wants richer reports with attachments + history
- CI does not publish reports; PRs have no test artifacts

## When NOT to use

- .NET reporting → `qa/dotnet/skills/allure-reporting`
- TypeScript reporting → `qa/typescript/skills/allure-reporting`
- Writing tests → `qa/java/skills/api-test-author/generator` / `qa/java/skills/ui-test-author/<stack>/java`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`

## Stack adapters

| Runner | Allure dependency |
|---|---|
| TestNG (default) | `io.qameta.allure:allure-testng:2.+` |
| JUnit 5 | `io.qameta.allure:allure-junit5:2.+` |
| RestAssured (HTTP filter) | `io.qameta.allure:allure-rest-assured:2.+` |

Both runners write `build/allure-results/` (Gradle convention). The Allure CLI converts that into HTML (`allure generate build/allure-results -o build/allure-report --clean`).

## Install (Gradle Kotlin DSL, TestNG)

```kotlin
plugins {
    id("io.qameta.allure") version "2.12.0"
    java
}

allure {
    version.set("2.27.0")
    adapter {
        autoconfigure.set(true)
        aspectjWeaver.set(true)
    }
}

dependencies {
    testImplementation("io.qameta.allure:allure-testng:2.27.0")
    testImplementation("io.qameta.allure:allure-rest-assured:2.27.0") // API tests
    testImplementation("org.testng:testng:7.10.+")
}

tasks.test {
    useTestNG()
    systemProperty("allure.results.directory", "build/allure-results")
}
```

`aspectjWeaver = true` is what makes `@Step("…")` on page-object methods appear as step nodes in the report.

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
| `@Tag("smoke")` / `@Tag("regression")` (JUnit 5) or `@Test(groups = {...})` (TestNG) | Filters |

```java
@Feature("Refunds")
public class RefundTests extends BaseApiTest {

    @Test(groups = "regression")
    @Story("Issue partial refund")
    @Severity(SeverityLevel.CRITICAL)
    @Issue("ORDERS-512")
    public void shouldIssuePartialRefund() {
        // arrange / act / assert
    }
}
```

Severity = **test** severity. `BLOCKER` = "ship is blocked if this fails"; `NORMAL` = "regression on a non-critical flow".

## Attachments (mandatory on failure path)

| Attachment | When |
|---|---|
| Request + response body | Every API test (auto via `AllureRestAssured` filter) |
| Screenshot | UI tests, on failure (Playwright Java / Selenium Java) |
| Playwright `trace.zip` | UI tests, on failure |
| Server logs around the test window | Optional, from Loki LogQL |

### API tests — `AllureRestAssured` filter

Register once in `BaseApiClient`:

```java
public abstract class BaseApiClient {
    protected RequestSpecification spec() {
        return RestAssured.given()
            .baseUri(baseUri)
            .header("Authorization", "Bearer " + jwt)
            .filter(new AllureRestAssured()); // request + response auto-attached
    }
}
```

Request URL, headers, body, response status, headers, body all attach automatically — no per-test code needed.

### Playwright Java — screenshot + trace on failure

```java
@AfterMethod(alwaysRun = true)
public void attachOnFailure(ITestResult result) throws IOException {
    if (result.getStatus() != ITestResult.FAILURE) return;

    byte[] screenshot = page.screenshot();
    Allure.addAttachment("screenshot", "image/png", new ByteArrayInputStream(screenshot), "png");

    Path tracePath = Files.createTempFile("trace-", ".zip");
    context.tracing().stop(new Tracing.StopOptions().setPath(tracePath));
    Allure.addAttachment("trace.zip", "application/zip",
        new FileInputStream(tracePath.toFile()), "zip");
}
```

Start tracing in `@BeforeMethod` with `context.tracing().start(new Tracing.StartOptions().setScreenshots(true).setSnapshots(true).setSources(true));`.

### Selenium Java — screenshot on failure

```java
@AfterMethod(alwaysRun = true)
public void screenshotOnFailure(ITestResult result) {
    if (result.getStatus() != ITestResult.FAILURE) return;
    byte[] png = ((TakesScreenshot) driver).getScreenshotAs(OutputType.BYTES);
    Allure.addAttachment("screenshot", "image/png", new ByteArrayInputStream(png), "png");
}
```

## Steps — `@Step` on page object methods

```java
public class LoginPage {
    @Step("Sign in as {user.email}")
    public ProductListPage signIn(User user) {
        emailField.fill(user.email());
        passwordField.fill(user.password());
        submitButton.click();
        return new ProductListPage(page);
    }
}
```

`{user.email}` is interpolated via AspectJ from the method's arguments. This is why `aspectjWeaver = true` is non-negotiable.

For inline steps: `Allure.step("Sign in", () -> loginPage.signIn(user));`.

## CI integration

The pattern is identical regardless of CI:

1. `./gradlew test` → `build/allure-results/` written.
2. Upload `build/allure-results/` as an artifact, **always** (even on failure).
3. Concatenate with previous run's `history/`.
4. `allure generate build/allure-results -o build/allure-report --clean`.
5. Publish to GitHub Pages / GitLab Pages / Azure static page.

### GitHub Actions

```yaml
- name: Run tests
  run: ./gradlew test
  continue-on-error: true

- name: Upload Allure results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: allure-results
    path: '**/build/allure-results/'

- name: Publish Allure report
  if: github.ref == 'refs/heads/main'
  uses: simple-elf/allure-report-action@v1.9
  with:
    gh_pages: gh-pages
    allure_results: build/allure-results
    allure_history: allure-history
    keep_reports: 30
```

### Azure Pipelines

```yaml
- task: Gradle@3
  inputs:
    gradleWrapperFile: gradlew
    tasks: test
    publishJUnitResults: true
    testResultsFiles: '**/build/test-results/test/TEST-*.xml'
  condition: succeededOrFailed()

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: $(System.DefaultWorkingDirectory)/build/allure-results
    ArtifactName: allure-results

- task: CmdLine@2
  displayName: Generate Allure report
  condition: succeededOrFailed()
  inputs:
    script: |
      curl -L https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz | tar -xz
      ./allure-2.27.0/bin/allure generate $(System.DefaultWorkingDirectory)/build/allure-results -o $(Build.ArtifactStagingDirectory)/allure-report --clean

- task: PublishHtmlReport@1
  inputs:
    reportDir: $(Build.ArtifactStagingDirectory)/allure-report
    tabName: Allure
```

### GitLab CI

```yaml
test:
  image: eclipse-temurin:21-jdk
  script:
    - ./gradlew test || true
  artifacts:
    when: always
    paths: ['**/build/allure-results/']
    expire_in: 30 days
    reports:
      junit: '**/build/test-results/test/TEST-*.xml'

publish:allure:
  stage: package
  image: eclipse-temurin:21-jdk
  needs: [test]
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  before_script:
    - curl -L https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz | tar -xz
  script:
    - mkdir -p build/allure-results/history
    - cp -r public/history build/allure-results/history || true
    - ./allure-2.27.0/bin/allure generate build/allure-results --clean -o public
  artifacts:
    paths: [public/]
```

## History & trends

Trend graphs require an `history/` folder inside `build/allure-results/` populated from the previous run. Each CI snippet preserves it; the smoke test is "does the trend chart in the published report show > 1 bar".

Keep last 20–30 runs.

## Categories for triage — `categories.json`

Place at `src/test/resources/categories.json` (the Allure adapter picks it up automatically):

```json
[
  { "name": "Backend 5xx",       "matchedStatuses": ["broken", "failed"], "messageRegex": ".*Status.*5\\d\\d.*" },
  { "name": "Auth issues",       "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*UnauthorizedException.*|.*ForbiddenException.*" },
  { "name": "Flaky timeouts",    "matchedStatuses": ["broken"],           "traceRegex":   ".*TimeoutException.*|.*PlaywrightException.*Timeout.*" },
  { "name": "Element not found", "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*NoSuchElementException.*|.*ElementNotFound.*" }
]
```

## Rules

- `io.qameta.allure:allure-testng` (or `allure-junit5`) installed; `aspectjWeaver = true` enabled.
- `AllureRestAssured` filter wired in `BaseApiClient` — request/response attach automatically.
- Every test has `@Feature` + `@Story` + `@Severity`.
- UI tests attach screenshot **and** trace (`trace.zip`) on failure via `@AfterMethod(alwaysRun = true)`.
- `build/allure-results/` uploaded as a CI artifact on **every** run, even on test failure.
- History preserved across runs (last 20–30 retained).
- Report published from `main` to a stable URL; PR builds publish to a PR-scoped URL or skip publish.
- `categories.json` in `src/test/resources/` tuned to the project's failure modes.
- Gradle Kotlin DSL preferred; Maven only if mandated.

## What NOT to do

- No "always pass" wrappers around `./gradlew test` — use `continue-on-error: true` (GHA) / `condition: succeededOrFailed()` (Azure) instead.
- No committing `build/allure-results/` to Git — it's an artifact.
- No `@Feature("misc")` catch-all bucket.
- No `@Description` that paraphrases the test name — describe behavior or link the spec.
- No attaching secrets / PII / auth tokens — sanitize before `Allure.addAttachment(...)`.
- No `aspectjWeaver = false` — `@Step` annotations silently fail to capture without it.
- No multiple Allure adapters in the same Gradle module (e.g. `allure-testng` and `allure-junit5` together) — pick one.
- No 5-MB-per-test logs attached — link to Loki instead.
- No mixing `AllureRestAssured` filter with manually-attached request/response bodies — duplicates entries.

## Generation steps

1. Confirm runner (TestNG vs JUnit 5), CI, publishing target, feature/severity taxonomy.
2. Apply the Gradle Kotlin DSL plugin block above; enable `aspectjWeaver`.
3. Add `AllureRestAssured` filter to `BaseApiClient`.
4. Add `@Feature` + `@Story` + `@Severity` annotations to existing tests.
5. Implement `@AfterMethod(alwaysRun = true)` failure attachers (screenshot + trace) on UI base test.
6. Drop `categories.json` into `src/test/resources/`.
7. Wire CI per the snippet for the team's CI platform; configure history retention.
8. Smoke a green build + a deliberate failing test; confirm trend, categories, attachments populate.

## Handoffs

- .NET Allure → `qa/dotnet/skills/allure-reporting`
- TypeScript Allure → `qa/typescript/skills/allure-reporting`
- API test generation → `qa/java/skills/api-test-author/generator`
- UI test generation → `qa/java/skills/ui-test-author/playwright` / `qa/java/skills/ui-test-author/selenium` / `qa/java/skills/ui-test-author/appium`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`
- CI pipeline syntax → `qa/java/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
