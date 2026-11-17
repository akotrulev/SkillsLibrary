---
paths:
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,DesktopTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests}/**/*.cs"
  - "**/TestCore/**/*.cs"
---

<!-- qa-dotnet rules v2 (2026-11-17): core. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its automated suites. -->

# .NET test-automation standards (NUnit)

Apply these to every C# file of an automated suite you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a hard rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Page-object, API, web, mobile, BDD, data, database and config rules are separate files loaded with their files.

**The codebase wins.** Where the suite consistently does otherwise, follow it and do not flag it. Detect versions first: the TFM (`net10.0` primary, `net8.0`/`net9.0` supported), NUnit 4.x, `Microsoft.Playwright` 1.63 (no 1.64-only API), `Appium.WebDriver` 9 for Appium 3 or 8.x for an Appium 2 device cloud, `FlaUI.UIA3` 5.0.0 for a Windows-only desktop suite. Never up-level a package, the SDK pin or the TFM as a side effect; never flag a down-level suite for lacking a newer API.

## Test shape

- Write the simplest test that proves the behaviour: no wrapper or DSL over the runner, driver or HTTP client, no speculative base class; cut structure, never rigour. *major*
- Page objects, components, clients, builders and fixtures are the suite's structure: created at first use, never inlined into a test; a review does not count their callers. *major*
- Names state behaviour: `Should_<Outcome>_When_<Condition>`. *minor*
- One logical behaviour per test; several assertions on that one behaviour go in `Assert.Multiple`. *major*
- Every test asserts something. *blocker*
- Every assertion states one expected value: no `.Or.`, `Is.AnyOf(...)`, `||` in `Assert.That` or `"a|b"` regex, on any value. Split the test or use `[TestCase]`; only an explicit instruction, recorded on the assertion, allows more. *major*
- A test body is linear: no `if`, `else`, `switch`, ternary, loop or `try`. Reaching the screen, signing in and seeding happen in `[SetUp]` or a fixture; variation is a `[TestCase]` / `[TestCaseSource]` row, a second test or setup. Branching lives only in infrastructure: the base test, env loader, driver factory, platform finder, teardown registry, a row source. *major*
- Every reusable piece is named for its role (page object, component, client, flow, builder, fixture, seeder, probe, token provider, driver factory, wait condition); no class, folder, file or method named `Helper(s)`, `Util(s)`, `Utility`, `Common` or `Misc` (third-party names stay). A test class holds tests, setup, teardown and fields, never a private method that drives the app or builds data. *major*
- Tests run alone and in any order: no `[Order]` chains, no shared mutable state, no data another test made; reference data only per `test-data.md`. *blocker*
- NUnit constraint assertions (`Assert.That`, `Assert.Multiple`), no FluentAssertions. *major*
- A failure names its subject and carries the evidence: `Is.EqualTo("Active"), $"account {dto.Id}"`. *minor*
- A skip carries a reason and a ticket (no `[Ignore("")]`, no bare `[Explicit]`); a flaky test is quarantined with `[Category("Flaky")]` plus `[AllureIssue]`, never `[Ignore]`. *minor*
- `[AllureFeature]`, `[AllureStory]` and `[AllureSeverity]` on every test (feature may sit on the class); a TC-ID links back when a test-case document exists. *minor*

## Errors and cleanup

- No `try`, `catch` or `finally` in a test, `[SetUp]`, `[TearDown]` or hook. An expected exception is `Assert.ThrowsAsync<T>`, never `Assert.Throws<T>` around a `Task`; an unexpected one reaches NUnit untouched. *major*
- Cleanup is registered, not inlined: track what the test created and delete it in `[TearDown]`, which never catches; pre-clean and keep-on-failure: `test-data.md`. *major*
- Only a client, seeder, probe, base class, driver factory or teardown registry catches (a delete, a driver quit, a probe turning one named exception into `false`): one named type, never `Exception`, logged or rethrown; never a silent default. *major*
- A failed deserialization names the property path, the target type and the body (attached to the report), inside the client. *major*

## Async and waiting

- Async all the way: every call awaited; never `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` or `async void`. *blocker*
- No `Thread.Sleep`, `Task.Delay` or `WaitForTimeoutAsync` as a wait; wait on a condition (auto-wait, web-first assertion, `WebDriverWait`, a probe's wait condition). A job test triggers the job, never waits for its schedule. *blocker*
- No hand-rolled retry loop; no retry attribute except `[Retry(2)]` on a documented, dated hotspot. *major*

## Data, config and secrets

- Test data with four or more fields comes from a builder; no literals duplicated across tests; values unique per test. *minor*
- No hardcoded base URL, host, credential or token: config and environment variables, secrets read lazily (never in a static initializer), never logged, committed or attached to a report. *blocker*
- Constructor injection; no static mutable state; nullable reference types honoured, no scattered `!`. *major*
- `System.Text.Json`, not `Newtonsoft.Json`; no `Console.WriteLine`, log with templates or use the trace. *major; minor for logging*

## Comments

- No comments in test bodies, page-object methods, steps or hooks: no Arrange/Act/Assert banners, narration, commented-out code or `TODO`. Move the step onto its owning object instead. *minor; major when the comment is wrong*
- A test may carry only a linked defect id behind a skip or workaround, an explicitly instructed deviation, or the source of a magic value the domain fixes. *minor*
- XML doc only where the name cannot carry a contract, never on locator fields, DTOs or trivia; a suppression states its reason. *nit*
