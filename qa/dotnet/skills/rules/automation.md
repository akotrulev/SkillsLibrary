---
paths:
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests}/**/*.cs"
  - "**/TestCore/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): core. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its automated suites, re-run to compare with the plugin's copy. -->

# .NET test-automation standards (NUnit)

Apply these to every C# file of an automated suite you write, edit or review (tests, fixtures, clients, page objects, steps). The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a hard rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. API, web, mobile, BDD, data, database and config rules are separate files that load with their files.

**The codebase wins.** Where the suite consistently does something another way (a naming shape, an assertion library), follow it and do not flag it. Detect versions before writing: the TFM (`net10.0` primary, `net8.0`/`net9.0` supported), NUnit 4.x, `Microsoft.Playwright` 1.63 (no 1.64-only API), `Appium.WebDriver` 9 for Appium 3 or 8.x for an Appium 2 device cloud. Never up-level a package, the SDK pin or the TFM as a side effect; never flag a down-level suite for lacking a newer API.

## Test shape

- Write the simplest test that proves the behaviour: no wrapper or DSL over the runner, driver or HTTP client, no base class, factory or builder with one caller. Extract on the second real need; cut structure, never rigour. *major, fix by inlining*
- Names state behaviour: `Should_<Outcome>_When_<Condition>`. *minor*
- One logical behaviour per test; several assertions on that one behaviour go in `Assert.Multiple`. *major*
- Every test asserts something. *blocker*
- Every assertion states one expected value: no `.Or.`, `Is.AnyOf(...)`, `||` in `Assert.That` or `"a|b"` regex, on any status, field, count, text or duration. Split the test or use `[TestCase]`; only an explicit instruction, recorded on the assertion, allows more. *major*
- No `if`, `for` or `foreach` driving assertions; one `[TestCase]` / `[TestCaseSource]` row per case. *major*
- Tests run alone and in any order: no `[Order]` chains, no shared mutable state, no data another test made, no seeded id assumed to exist. *blocker*
- NUnit constraint assertions (`Assert.That`, `Assert.Multiple`), no FluentAssertions. *major*
- A failure names its subject and carries the evidence: `Assert.That(dto.Status, Is.EqualTo("Active"), $"account {dto.Id}")`. *minor*
- A skip carries a reason and a ticket (no `[Ignore("")]`, no bare `[Explicit]`); a flaky test is quarantined with `[Category("Flaky")]` plus `[AllureIssue]`, never `[Ignore]`. *minor*
- `[AllureFeature]`, `[AllureStory]` and `[AllureSeverity]` on every test (feature may sit on the class); a TC-ID links back when a test-case document exists. *minor*

## Errors and cleanup

- No `try`, `catch` or `finally` in a test, `[SetUp]`, `[TearDown]` or hook. An expected exception is `Assert.ThrowsAsync<T>`, never `Assert.Throws<T>` around a `Task`; an unexpected one reaches NUnit untouched. *major*
- Cleanup is registered, not inlined: track what the test created and delete it in `[TearDown]`, which does not catch either. *major*
- A `catch` lives only in an I/O helper (a delete, a driver quit, a probe turning one named exception into `false`), catches one named type, never `Exception`, and logs or rethrows; never a silent default. *major*
- A failed deserialization names the property path, the target type and the body (attached to the report), inside the helper. *major*

## Async and waiting

- Async all the way: every call awaited; never `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` or `async void`. *blocker*
- No `Thread.Sleep`, `Task.Delay` or `WaitForTimeoutAsync` as a wait; wait on a condition (auto-wait, web-first assertion, `WebDriverWait`, a polling probe with a predicate). A job test triggers the job, never waits for its schedule. *blocker*
- No hand-rolled retry loop; no retry attribute except `[Retry(2)]` on a documented, dated hotspot. *major*

## Data, config and secrets

- Test data with four or more fields comes from a builder; no literals duplicated across tests; values unique per test. *minor*
- No hardcoded base URL, host, credential or token: config and environment variables, secrets read lazily (never in a static initializer), never logged, committed or attached to a report. *blocker*
- Constructor injection; no static mutable state (a static driver, page or browser breaks parallel runs); nullable reference types honoured, no scattered `!`. *major*
- `System.Text.Json`, not `Newtonsoft.Json`; no `Console.WriteLine`, log with templates or use the trace. *major; minor for logging*

## Page objects (web and mobile)

- A page object exposes intent (`SignInAsync`), never selectors; locators are built once and stay private. *major*
- No assertion in a page object beyond its one landmark check; no business logic or API calls. *major*
- An action that always lands on another screen returns that page object. One page object per screen; a reused region is a component scoped to its root; composition over inheritance, no base page until three pages share real behaviour. *minor*
- Tests reach the app through page objects, never the raw `Page` or driver. *major*

## Comments

- No comments in test bodies, page-object methods, steps or hooks: no `// Arrange` / `// Act` / `// Assert` banners, no narration, no commented-out code or scenarios, no `TODO`. Extract a named method instead. *minor; major when the comment is wrong*
- A test may carry only a linked defect id behind a skip or workaround, an explicitly instructed deviation, or the source of a magic value the domain fixes. A locator that needs a comment is positional: fix the locator. *minor*
- XML doc only where the name cannot carry a contract, never on locator fields, DTOs or trivia; a suppression states its reason. *nit*
