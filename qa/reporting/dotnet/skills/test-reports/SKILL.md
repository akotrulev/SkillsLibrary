---
name: test-reports
description: Use when setting up Allure reporting for a .NET test suite (NUnit + RestSharp, NUnit + Playwright .NET, NUnit + Appium .NET, xUnit). Triggers: "set up Allure for our NUnit project", "wire Allure attachments in .NET", "publish Allure report from our .NET CI". Not for flaky-test quarantine (`qa-dotnet:flaky-test-quarantine`) or pipeline YAML (`qa-dotnet:ci-pipelines`).
---

# QA — Allure Reporting (.NET / NUnit & xUnit)

Wires Allure into a .NET test project (NUnit primary, xUnit secondary) — the `Allure.NUnit` adapter,
`allureConfig.json`, failure-path attachments, the behavior-first hierarchy (`AllureFeature` / `AllureStory` /
`AllureSeverity`), history, triage categories and the report CLI.

## When to use

- A new .NET test project needs a reporting story
- An existing NUnit / xUnit suite emits TRX or plain test output and the team wants richer reports with attachments + history
- CI does not publish reports; PRs have no test artifacts

## When NOT to use

- Java reporting → `qa/reporting/java/skills/test-reports`
- TypeScript reporting → `qa/reporting/typescript/skills/test-reports`
- Writing tests → `qa/dotnet/skills/api-test-author/writer` / `qa/dotnet/skills/ui-test-author/<tool>`
- What Playwright evidence a UI run keeps, and how it is read → `qa/dotnet/skills/evidence-capture`
- Pipeline YAML, including the Allure publish job → `qa/cicd/dotnet/skills/ci-pipelines`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`

## Versions

| Artifact | Version |
|---|---|
| `Allure.NUnit` | `2.15.0` (central package management — the `PackageVersion` lives in `Directory.Packages.props`) |
| NUnit | `4.x` (`4.6.1`) — not NUnit 5 |
| Allure report CLI | `allure-commandline@2.46.1` (npm; needs a Java runtime) — the one pin in `qa/cicd/ci-conventions` |

## Stack adapters

| Runner | Allure dependency |
|---|---|
| NUnit | `Allure.NUnit` |
| xUnit | `Allure.XUnit` (community) |

Both write `allure-results/` into the test host's working directory, which `dotnet test` sets to the test
assembly's folder: `<Project>/bin/<cfg>/net10.0/allure-results/`. That is the path CI uploads.

## Install (NUnit)

```xml
<PackageVersion Include="Allure.NUnit" Version="2.15.0" />
```

```xml
<PackageReference Include="Allure.NUnit" />
```

The first line goes in `Directory.Packages.props`, the second in the test project, with no `Version=`. For a
UI project, `qa/dotnet/skills/ui-test-author/playwright/assets/` already carries both.

`allureConfig.json` in the test project root, copied to the output folder:

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
<ItemGroup>
  <Content Include="allureConfig.json">
    <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
  </Content>
</ItemGroup>
```

**`[AllureNUnit]` is required** on every fixture, or on the base class they share — without it NUnit runs
the tests and Allure writes nothing for them. The UI lane's `BaseTest` carries it.

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
[AllureNUnit]
[AllureFeature("Refunds")]
public class RefundTests
{
    [Test]
    [AllureStory("Issue partial refund")]
    [AllureSeverity(SeverityLevel.critical)]
    [AllureIssue("ORDERS-512")]
    public async Task Should_IssuePartialRefund_When_OrderPaid()
    {
        var refund = await _refunds.IssueAsync(RefundRequests.Partial().Build());

        Assert.That(refund.Status, Is.EqualTo(RefundStatus.Issued));
    }
}
```

Severity = **test** severity, not bug severity. `blocker` = "if this fails, ship is blocked"; `normal` =
"regression on a non-critical flow".

## Attachments (the failure path is non-negotiable)

| Attachment | When | Owner |
|---|---|---|
| Request + response body | Every API test, before its assertions | the API base class below |
| Playwright trace, full-page screenshot, video | UI tests, on failure | `BaseTest` — nothing to add here |
| Selenium screenshot | UI tests on Selenium, on failure | the `[TearDown]` below |
| Server logs around the test window | Optional | a link to Loki, not a file |

`AllureApi.AddAttachment` has three overloads, and the plain-string one is the trap:

| Call | Third argument is |
|---|---|
| `AddAttachment(name, type, string path)` | **a file path** — the file is copied into the results |
| `AddAttachment(name, type, byte[] content, string fileExtension)` | the content; the extension (`".json"`, `".png"`) names the downloaded file |
| `AddAttachment(string path, string? name)` | — the type is inferred from the extension |

Passing a response body as the third string attaches nothing: Allure looks for a file with that name.

### API tests — base class helper

```csharp
public abstract class BaseApiTest
{
    protected static void AttachBody(RestResponse response) =>
        AllureApi.AddAttachment(
            "response.json",
            "application/json",
            Encoding.UTF8.GetBytes(response.Content ?? string.Empty),
            ".json");
}
```

Call `AttachBody(response)` **before** assertions on 4xx/5xx responses so the body is visible in the failure
attachment.

### Playwright .NET — `BaseTest` owns it

A UI fixture derives from `qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`. On a failed test
its `[TearDown]` keeps three files in `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}`
and attaches each with `TestContext.AddTestAttachment` and `AllureApi.AddAttachment(name, type, path)`:

| Name | Type |
|---|---|
| `trace` | `application/vnd.allure.playwright-trace` — Allure opens it in the trace viewer |
| `screenshot` | `image/png` |
| `video` | `video/webm` |

There is no second attacher: no `[TearDown]` that screenshots again, no trace written to `Path.GetTempPath()`
(CI never uploads it), no `trace.zip` typed `application/zip`. A recording made on purpose (screencast,
HAR, a screenshot at a point) uses `BaseTest`'s `Attach` helper — `qa/dotnet/skills/evidence-capture`.

### Selenium .NET — screenshot on failure

```csharp
[TearDown]
public void AttachScreenshotOnFailure()
{
    if (TestContext.CurrentContext.Result.Outcome.Status != TestStatus.Failed) return;
    var png = ((ITakesScreenshot)Driver).GetScreenshot().AsByteArray;
    AllureApi.AddAttachment("screenshot", "image/png", png, ".png");
}
```

## Steps — `AllureApi.Step(...)`

Wrap non-trivial workflows so the report shows a step tree, not a wall of actions:

```csharp
await AllureApi.Step("Sign in", async () =>
{
    await _loginPage.SignInAsync(user);
});
```

For attribute-style step decoration on page methods, use `[AllureStep("Sign in")]`.

## The report

1. Run tests → `bin/<cfg>/net10.0/allure-results/` written.
2. Upload `allure-results/` as a CI artifact on **every** run, even on failure; each shard uploads its own.
3. The publish job merges every shard's results into one `allure-results/`, copies `categories.json` into
   it, and copies the previous report's `history/` into `allure-results/history/`.
4. `allure generate allure-results -o allure-report --clean` with the pinned CLI.
5. Publish to GitHub Pages / GitLab Pages / an Azure artifact, and keep `allure-report/history/` for the next
   run.

Locally:

```bash
npm i -g allure-commandline@2.46.1
allure generate UiTests/bin/Debug/net10.0/allure-results -o allure-report --clean
allure open allure-report
```

The CLI needs a Java runtime. The publish job for each CI — artifact names, the history home, the Pages
step — is in `qa/cicd/dotnet/skills/ci-pipelines` (`references/<ci>.md`).

## History & trends

Trend graphs require a `history/` folder inside `allure-results/` populated from the previous report. The
smoke test is "does the trend chart show > 1 bar in the published report". Keep the last 20–30 runs.

## Categories for triage — `categories.json`

The report generator reads `categories.json` from the results folder, so the publish job copies it from the
test project into the merged `allure-results/` before `allure generate`. A result takes the **first**
category that matches, so the quarantine bucket comes first:

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"], "flaky": true },
  { "name": "Backend 5xx",       "matchedStatuses": ["broken", "failed"], "messageRegex": ".*Status.*5\\d\\d.*" },
  { "name": "Auth issues",       "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*Unauthorized.*|.*Forbidden.*" },
  { "name": "Timeouts",          "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*TimeoutException.*|.*TaskCanceledException.*" },
  { "name": "Element not found", "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*NoSuchElement.*|.*Timeout.*locator.*" }
]
```

A timeout is a failure class, not a flakiness verdict: "Timeouts" is a triage bucket, and what counts as
known-flaky is `qa/reporting/dotnet/skills/flaky-test-quarantine`'s.

## Rules

- `Allure.NUnit` (or `Allure.XUnit`) installed per test project; `allureConfig.json` copied to output;
  `[AllureNUnit]` on every fixture or its base class.
- Every test has `[AllureFeature]` + `[AllureStory]` + `[AllureSeverity]`.
- API tests call `AttachBody(response)` **before** assertions on the failure path, with bytes and `".json"`.
- UI tests on Playwright get their trace, screenshot and video from `BaseTest` — no second attacher.
- A byte-array attachment always passes its file extension.
- `allure-results/` uploaded as a CI artifact on **every** run, even on test failure.
- History preserved across runs (last 20–30 retained).
- The report is generated with `allure-commandline@2.46.1`; no second Allure CLI, no action that bundles its
  own.
- Report published from `main` to a stable URL; PR builds publish to a PR-scoped URL or skip publish.
- `categories.json` tuned to the project's failure modes, with the quarantine bucket first.
- One reporter convention across the entire .NET test project — never mix `Allure.NUnit` and `Allure.XUnit`
  writing into the same `allure-results/`.
- No `Thread.Sleep` in `[TearDown]` waiting for attachments to flush — adapter is sync.

## What NOT to do

- No "always pass the build" wrappers around `dotnet test` — no `continue-on-error` / `continueOnError` / `|| true` on the test step. The test step fails the build; the upload and publish steps run anyway (`if: ${{ !cancelled() }}` / `condition: succeededOrFailed()` / `when: always`).
- No committing `allure-results/` to Git — it's an artifact.
- No `[AllureFeature("misc")]` catch-all bucket.
- No `[AllureDescription]` that paraphrases the test name — describe behavior or link the spec.
- No attaching secrets / PII / auth tokens — sanitize before `AddAttachment`.
- No mixed reporters writing to the same `allure-results/` from parallel test projects without separate output dirs.
- No 5-MB-per-test logs attached — link to Loki / Azure Log Analytics instead.
- No `.Wait()` / `.Result` in `[TearDown]` attachment helpers — make tear-down async (`[TearDown] public async Task ...`).

## Generation steps

1. Confirm runner (NUnit vs xUnit), CI (GitHub / Azure / GitLab), publishing target, feature/severity taxonomy.
2. Add `Allure.NUnit` `2.15.0` to `Directory.Packages.props` and a versionless reference to the test project
   (or `Allure.XUnit`).
3. Create `allureConfig.json` and `categories.json` in the test project; mark `allureConfig.json`
   `CopyToOutputDirectory=PreserveNewest`.
4. Put `[AllureNUnit]` on each fixture or its base class; add `[AllureFeature]` + `[AllureStory]` +
   `[AllureSeverity]` to existing tests.
5. Implement `AttachBody(...)` on `BaseApiTest` (API). UI on Playwright: derive from `BaseTest`; UI on
   Selenium: the `[TearDown]` above.
6. Wire CI per `qa/cicd/dotnet/skills/ci-pipelines` for the team's CI platform; configure history retention.
7. Smoke a green build + a deliberate failing test; confirm trend, categories, attachments populate.

Inside a `Gate: none` plan task, skip the smoke run in the last step and report the wiring as "written, not run".

## Handoffs

- Java Allure → `qa/reporting/java/skills/test-reports`
- TypeScript Allure → `qa/reporting/typescript/skills/test-reports`
- API test generation → `qa/dotnet/skills/api-test-author/writer`
- UI test generation and `BaseTest` → `qa/dotnet/skills/ui-test-author/playwright` / `qa/dotnet/skills/ui-test-author/selenium` / `qa/dotnet/skills/ui-test-author/appium`
- Playwright evidence (what is kept, deliberate recordings, reading a trace) → `qa/dotnet/skills/evidence-capture`
- Flaky detection and the quarantine lane → `qa/reporting/dotnet/skills/flaky-test-quarantine`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`
- CI pipeline syntax and the Allure publish job → `qa/cicd/dotnet/skills/ci-pipelines` (its `references/<ci>.md`) or `devops/<ci>`
