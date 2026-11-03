---
paths:
  - "**/*.UnitTests/**/*.cs"
  - "**/*.{Application,Domain,Infrastructure}.Tests/**/*.cs"
---

<!-- be-dotnet rules v1 (2026-11-03): unit tests. Installed by /be-dotnet:rules; edit the paths above to this project's unit-test projects (integration and E2E suites belong to qa-dotnet). -->

# .NET unit test standards

Severity tags as in the core .NET rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- A unit test constructs the class under test directly (NUnit, NSubstitute, `Assert.That`). No `WebApplicationFactory`, Testcontainers or real connection string; that is the `qa-api-dotnet` suite. *major*
- Never `UseInMemoryDatabase` to test a repository or a query; the integration lane uses the real engine. *major*
- Names state behaviour: `Should_<Outcome>_When_<Condition>`. *minor*
- One logical assertion per test, grouped with `Assert.Multiple`, and each assertion expects one value, never "this or that". *major*
- No `try`/`catch` in a test (use `Assert.ThrowsAsync<T>`, asserting the type, not the message), no `if`/`for` driving assertions (use `[TestCase]`), no `Task.Delay` or `Thread.Sleep` (advance a `FakeTimeProvider`). *major*
- Tests return `Task`, never `async void`, never `.Result`; no shared mutable state across tests. *major*
- Fake only types you own: never substitute `DbContext`, `HttpClient`, `TimeProvider` or an SDK client, and never a concrete class. *major*
- No `InternalsVisibleTo` or reflection to reach private behaviour; extract the class. *major*
- Do not test the framework, records or DTOs, and assert the field a test is about, not a whole record. *minor*
- No `[Ignore]` without a linked issue. *minor*
- Test data with four or more fields comes from a builder. *minor*
- New code ships with unit tests covering at least 80% of the branches it wrote (coverlet + ReportGenerator); only an asserting test counts. *major*
