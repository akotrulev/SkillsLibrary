---
name: qa-allure-reporting-dotnet
description: Use when the user asks to set up Allure reporting for a .NET test suite (NUnit + RestSharp, NUnit + Playwright .NET, NUnit + Appium .NET, xUnit) — install `Allure.NUnit` / `Allure.XUnit`, configure `allureConfig.json`, wire failure attachments (request/response body, screenshots, traces), feature/story/severity hierarchy, and publish to GitHub Pages / GitLab Pages / Azure Pipelines. Triggers: "set up Allure for our NUnit project", "wire Allure attachments in .NET", "publish Allure report from our .NET CI", "design Allure feature/story for NUnit tests". Do NOT use for Java reporting (use `qa/allure-reporting/java`), TypeScript reporting (use `qa/allure-reporting/typescript`), writing tests (use the matching `qa/<topic>` skill), or test strategy (use `qa/_shared/test-strategy`).
---

# QA — Allure Reporting (.NET / NUnit & xUnit)

Wires Allure into a .NET test project (NUnit primary, xUnit secondary) — `Allure.NUnit` adapter, `allureConfig.json`, failure-path attachments, behavior-first hierarchy (`AllureFeature` / `AllureStory` / `AllureSeverity`), CI publish, history, and triage categories.

## When to use

- A new .NET test project needs a reporting story
- An existing NUnit / xUnit suite emits TRX or plain test output and the team wants richer reports with attachments + history
- CI does not publish reports; PRs have no test artifacts

## When NOT to use

- Java reporting → `qa/allure-reporting/java`
- TypeScript reporting → `qa/allure-reporting/typescript`
- Writing tests → `qa/api-test-author/generator/dotnet` / `qa/ui-test-author/<stack>/dotnet`
- Test strategy → `qa/_shared/test-strategy`
- Quality metrics dashboards → `qa/_shared/quality-metrics`

## Stack adapters

| Runner | Allure dependency |
|---|---|
| NUnit | `Allure.NUnit` |
| xUnit | `Allure.XUnit` (community) |

Both write `allure-results/` under the test project's working directory. The Allure CLI converts that into HTML (`allure generate allure-results -o allure-report --clean`).

## Install (NUnit)

```bash
dotnet add tests/ApiTests/ApiTests.csproj package Allure.NUnit
```

`allureConfig.json` in the test project root (copy to output via csproj `CopyToOutputDirectory`):

```json
{
  "allure": {
    "directory": "allure-results",
    "links": [
      "https://yourco.atlassian.net/browse/{issue}",
      "https://yourco.atlassian.net/browse/{tms}"
    ]
  }
}
```

```xml
<!-- ApiTests.csproj -->
<ItemGroup>
  <Content Include="allureConfig.json">
    <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
  </Content>
</ItemGroup>
```

## Hierarchy: Feature → Story → Test

Behavior view (stakeholders): **Epic → Feature → Story**. Suite view (engineers): **Suite → Class → Method**.

| Attribute | Use |
|---|---|
| `[AllureEpic("Orders")]` | Cross-feature theme (rare) |
| `[AllureFeature("Refunds")]` | User-facing feature under test |
| `[AllureStory("Issue partial refund")]` | User-story slice |
| `[AllureSeverity(SeverityLevel.blocker / critical / normal / minor / trivial)]` | Triage signal |
| `[AllureDescription("…")]` | Long description / link to spec |
| `[AllureIssue("JIRA-1234")]` / `[AllureTms("TC-456")]` | Bidirectional links |
| `[AllureTag("smoke")]` / `[AllureTag("regression")]` | Filters for selective runs |

```csharp
[TestFixture]
[AllureFeature("Refunds")]
public class RefundTests
{
    [Test]
    [AllureStory("Issue partial refund")]
    [AllureSeverity(SeverityLevel.critical)]
    [AllureIssue("ORDERS-512")]
    public void Should_IssuePartialRefund_When_OrderPaid()
    {
        // arrange / act / assert
    }
}
```

Severity = **test** severity, not bug severity. `blocker` = "if this fails, ship is blocked"; `normal` = "regression on a non-critical flow".

## Attachments (the failure-path is non-negotiable)

| Attachment | When |
|---|---|
| Request + response body | Every API test (per `qa/api-test-author/generator/dotnet`) |
| Screenshot | UI tests, on failure (Playwright .NET / Selenium .NET) |
| Playwright `trace.zip` | UI tests, on failure |
| Server logs around the test window | Optional, from Loki LogQL |

### API tests — base class helper

```csharp
public abstract class BaseApiTest
{
    protected void AttachBody(RestResponse response)
    {
        AllureApi.AddAttachment(
            "response.json",
            "application/json",
            response.Content ?? string.Empty);
    }
}
```

Call `AttachBody(response)` **before** assertions on 4xx/5xx responses so the body is visible in the failure attachment.

### Playwright .NET — screenshot + trace on failure

```csharp
[TearDown]
public async Task AttachOnFailure()
{
    if (TestContext.CurrentContext.Result.Outcome.Status != TestStatus.Failed) return;

    var screenshot = await Page.ScreenshotAsync();
    AllureApi.AddAttachment("screenshot.png", "image/png", screenshot);

    var tracePath = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.zip");
    await Context.Tracing.StopAsync(new() { Path = tracePath });
    AllureApi.AddAttachment("trace.zip", "application/zip", await File.ReadAllBytesAsync(tracePath));
}
```

Start tracing in `[SetUp]` with `await Context.Tracing.StartAsync(new() { Screenshots = true, Snapshots = true, Sources = true });`.

### Selenium .NET — screenshot on failure

```csharp
[TearDown]
public void AttachScreenshotOnFailure()
{
    if (TestContext.CurrentContext.Result.Outcome.Status != TestStatus.Failed) return;
    var png = ((ITakesScreenshot)Driver).GetScreenshot().AsByteArray;
    AllureApi.AddAttachment("screenshot.png", "image/png", png);
}
```

## Steps — `AllureApi.Step(...)`

Wrap non-trivial workflows so the report shows a step tree, not a wall of actions:

```csharp
await AllureApi.Step("Sign in", async () =>
{
    await LoginPage.SignInAsync(user);
});
```

For attribute-style step decoration on page methods, use `[AllureStep("Sign in")]`.

## CI integration (pattern is identical regardless of CI)

1. Run tests → `allure-results/` written.
2. Upload `allure-results/` as an artifact, **always** (even on failure).
3. Concatenate with previous run's `history/`.
4. `allure generate allure-results -o allure-report --clean`.
5. Publish to GitHub Pages / GitLab Pages / Azure static page.

### GitHub Actions

```yaml
- name: Run tests
  run: dotnet test --logger "trx;LogFileName=test.trx"
  continue-on-error: true

- name: Upload Allure results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: allure-results
    path: '**/allure-results/'

- name: Publish Allure report
  if: github.ref == 'refs/heads/main'
  uses: simple-elf/allure-report-action@v1.9
  with:
    gh_pages: gh-pages
    allure_results: allure-results
    allure_history: allure-history
    keep_reports: 30
```

### Azure Pipelines

```yaml
- task: DotNetCoreCLI@2
  inputs: { command: test, arguments: '--logger "trx;LogFileName=test.trx"' }
  condition: succeededOrFailed()

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: $(System.DefaultWorkingDirectory)/tests/ApiTests/bin/Debug/net8.0/allure-results
    ArtifactName: allure-results

- task: CmdLine@2
  displayName: Generate Allure report
  condition: succeededOrFailed()
  inputs:
    script: |
      curl -L https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz | tar -xz
      ./allure-2.27.0/bin/allure generate $(System.DefaultWorkingDirectory)/tests/ApiTests/bin/Debug/net8.0/allure-results -o $(Build.ArtifactStagingDirectory)/allure-report --clean

- task: PublishHtmlReport@1
  inputs:
    reportDir: $(Build.ArtifactStagingDirectory)/allure-report
    tabName: Allure
```

### GitLab CI

```yaml
test:
  script:
    - dotnet test --logger "trx;LogFileName=test.trx" || true
  artifacts:
    when: always
    paths: ['**/allure-results/']
    expire_in: 30 days

publish:allure:
  stage: package
  image: mcr.microsoft.com/dotnet/sdk:8.0
  needs: [test]
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  before_script:
    - apt-get update && apt-get install -y openjdk-17-jre-headless
    - curl -L https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz | tar -xz
  script:
    - mkdir -p allure-results/history
    - cp -r public/history allure-results/history || true
    - ./allure-2.27.0/bin/allure generate allure-results --clean -o public
  artifacts:
    paths: [public/]
```

## History & trends

Trend graphs require an `history/` folder inside `allure-results/` populated from the previous run. Each CI snippet above does this differently; the smoke test is "does the trend chart show > 1 bar in the published report".

Keep last 20–30 runs.

## Categories for triage — `categories.json`

Place in the test project root and copy to output alongside `allureConfig.json`:

```json
[
  { "name": "Backend 5xx",      "matchedStatuses": ["broken", "failed"], "messageRegex": ".*Status.*5\\d\\d.*" },
  { "name": "Auth issues",      "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*Unauthorized.*|.*Forbidden.*" },
  { "name": "Flaky timeouts",   "matchedStatuses": ["broken"],           "traceRegex":   ".*TimeoutException.*|.*TaskCanceledException.*" },
  { "name": "Element not found","matchedStatuses": ["broken", "failed"], "traceRegex":   ".*NoSuchElement.*|.*Timeout.*locator.*" }
]
```

## Rules

- `Allure.NUnit` (or `Allure.XUnit`) installed per test project; `allureConfig.json` + `categories.json` copied to output.
- Every test has `[AllureFeature]` + `[AllureStory]` + `[AllureSeverity]`.
- API tests call `AttachBody(response)` **before** assertions on the failure path.
- UI tests attach screenshot **and** trace (`trace.zip`) on failure.
- `allure-results/` uploaded as a CI artifact on **every** run, even on test failure.
- History preserved across runs (last 20–30 retained).
- Report published from `main` to a stable URL; PR builds publish to a PR-scoped URL or skip publish.
- `categories.json` tuned to the project's failure modes (5xx, timeouts, auth, missing element).
- One reporter convention across the entire .NET test project — never mix `Allure.NUnit` and `Allure.XUnit` writing into the same `allure-results/`.
- No `Thread.Sleep` in `[TearDown]` waiting for attachments to flush — adapter is sync.

## What NOT to do

- No "always pass the build" wrappers around `dotnet test` — use `continue-on-error: true` / `condition: succeededOrFailed()` instead.
- No committing `allure-results/` to Git — it's an artifact.
- No `[AllureFeature("misc")]` catch-all bucket.
- No `[AllureDescription]` that paraphrases the test name — describe behavior or link the spec.
- No attaching secrets / PII / auth tokens — sanitize before `AddAttachment`.
- No mixed reporters writing to the same `allure-results/` from parallel test projects without separate output dirs.
- No 5-MB-per-test logs attached — link to Loki / Azure Log Analytics instead.
- No `.Wait()` / `.Result` in `[TearDown]` attachment helpers — make tear-down async (`[TearDown] public async Task ...`).

## Generation steps

1. Confirm runner (NUnit vs xUnit), CI (GitHub / Azure / GitLab), publishing target, feature/severity taxonomy.
2. `dotnet add … package Allure.NUnit` (or `Allure.XUnit`).
3. Create `allureConfig.json` and `categories.json` in the test project; mark `CopyToOutputDirectory=PreserveNewest`.
4. Add `[AllureFeature]` + `[AllureStory]` + `[AllureSeverity]` to existing tests.
5. Implement `AttachBody(...)` on `BaseApiTest` (API) and `[TearDown]` failure attachers (UI).
6. Wire CI per the snippet for the team's CI platform; configure history retention.
7. Smoke a green build + a deliberate failing test; confirm trend, categories, attachments populate.

## Handoffs

- Java Allure → `qa/allure-reporting/java`
- TypeScript Allure → `qa/allure-reporting/typescript`
- API test generation → `qa/api-test-author/generator/dotnet`
- UI test generation → `qa/ui-test-author/playwright/dotnet` / `qa/ui-test-author/selenium/dotnet` / `qa/ui-test-author/appium/dotnet`
- Test strategy → `qa/_shared/test-strategy`
- Quality metrics dashboards → `qa/_shared/quality-metrics`
- CI pipeline syntax → `qa/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`

## Changelog

- 2026-05-29: Split from monolithic `qa/allure-reporting/SKILL.md` into the .NET-specific sibling. `Allure.NUnit` primary adapter (xUnit secondary), `allureConfig.json` + `categories.json` shipped to bin, mandatory `AttachBody` on API tests + screenshot/trace on UI tests, per-CI publish recipes for GitHub Actions / Azure Pipelines / GitLab CI.
