---
name: qa-api-test-author-playwright-dotnet
description: Use when the user asks to write .NET API tests through Playwright's IAPIRequestContext (Microsoft.Playwright + NUnit) — usually because the project already runs Playwright for UI and wants one dependency and one report. Triggers: "write API tests with Playwright in C#", "use IAPIRequestContext for endpoint X", "add API coverage to our Playwright .NET suite". Plain .NET API suites without Playwright → `api-test-author/generator` (NUnit + RestSharp, the stack default).
---

# QA — API Test Writer (.NET / Playwright IAPIRequestContext + NUnit)

Authors NUnit fixtures that test a REST backend through **Microsoft.Playwright's HTTP client** —
`IAPIRequestContext` — instead of RestSharp. It reuses the layering and templates of the RestSharp sibling
(`qa-api-test-author-generator-dotnet`): DTOs from `qa/dotnet/skills/api-dto-writer`, a `{Resource}Client` with
dual raw + typed overloads, fixtures that own scenarios, the rich happy-path template for 2xx and the strict
`ProblemDetails` template for 4xx. Only the HTTP transport changes; the discipline does not.

> **The discipline this skill encodes** — four ideas that separate a correct Playwright .NET API suite from a
> RestSharp reflex ported onto the wrong client:
>
> 1. **The `IAPIRequestContext` is the auth boundary, not the call site.** Base URL and the `Authorization`
>    header are set **once, at context creation** (`playwright.APIRequest.NewContextAsync(new() { BaseURL,
>    ExtraHTTPHeaders })`). One context per identity — standard, admin, anonymous — never a token argument
>    threaded through every call.
> 2. **Contexts and `IPlaywright` are resources with an async lifecycle.** `Playwright.CreateAsync()` once per
>    fixture in `[OneTimeSetUp]`, one context per identity next to it, `DisposeAsync()` for every context and
>    `playwright.Dispose()` in `[OneTimeTearDown]`. Everything is `async Task` — never `.Result` / `.Wait()`.
> 3. **You are here for one dependency and one report.** The value is that a project already running
>    Microsoft.Playwright for UI gets API tests with zero extra HTTP stack, the same NUnit + Allure wiring,
>    and — for cookie-authenticated apps — a **storage state** shared between a logged-in browser context and
>    API calls. If the project has no Playwright UI suite, the stack default is RestSharp
>    (`api-test-author/generator`).
> 4. **The layering survives the client swap.** Tests still never touch HTTP directly: `{Resource}Client`
>    wraps the context, the raw overload returns Playwright's `IAPIResponse` unasserted, the typed overload
>    asserts the **exact** status and `System.Text.Json`-deserializes `await response.TextAsync()` into the
>    DTO. The only signature change from the RestSharp client: the constructor takes an
>    **`IAPIRequestContext`**, because the context — not an `AuthToken` string — now carries the identity.

## Stack

- .NET 8, nullable reference types enabled
- **NUnit** — the global default runner (same as the UI suite); `Assert.That` / `Assert.Multiple` only, no FluentAssertions
- **Microsoft.Playwright** — `IAPIRequestContext` / `IAPIResponse`; no RestSharp dependency in a Playwright-first project
- **System.Text.Json** — deserialization lives in the client's typed overloads and `BasePlaywrightApiTest.Deserialize<T>`, never inline in tests
- **Allure NUnit**; `System.Net.HttpStatusCode` for status constants
- Layout mirrors the RestSharp sibling: `ApiTests/Models/`, `ApiTests/Clients/`, `ApiTests/Tests/`,
  `ApiTests/Base/BasePlaywrightApiTest.cs`

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `Models/{Resource}Dto.cs` | `qa/dotnet/skills/api-dto-writer` | Body shapes, `JsonPropertyName` mapping, `ProblemDetailsDto` |
| `Clients/{Resource}Client.cs` — constructor takes `IAPIRequestContext` | `qa/dotnet/skills/api-client-writer` conventions, context-based variant | Request building on the context; raw `IAPIResponse` overload + typed overload (asserts exact status, deserializes) |
| `Base/BasePlaywrightApiTest.cs` | **this skill** | `IPlaywright` + per-identity context lifecycle (`[OneTimeSetUp]`/`[OneTimeTearDown]`), `NewContextAsync(token)` helper, `AuthToken`, `Deserialize<T>`, `AttachBody` |
| `Tests/{Resource}Tests.cs` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

If a DTO or client a test needs is missing, run the owner skill first — never call `context.GetAsync(...)`
inline in a test to avoid creating a client.

## When to use

- The project already runs Microsoft.Playwright for UI and wants API coverage without adding RestSharp
- Hybrid suites where API setup/assertions and UI flows must share one Playwright installation, report, and storage state
- New `{Resource}Tests.cs` under a Playwright-based API suite, or new test methods on an existing fixture

## When NOT to use

- No Playwright in the project → `qa/dotnet/skills/api-test-author/generator` (NUnit + RestSharp, the stack default)
- API calls **inside a UI test** (seed data, then drive the browser) → the UI suite's arrange phase; conventions in `qa/dotnet/skills/ui-test-author/playwright`
- Mocking/intercepting the browser's network traffic (`page.RouteAsync`) → `qa/dotnet/skills/network-monitoring`
- GraphQL / gRPC → the protocol siblings under `qa/dotnet/skills/api-test-author/`
- Reviewing existing tests → `qa/dotnet/skills/api-test-author/reviewer` (cross-stack checklist applies; add this skill's anti-patterns below)

## Base class template — the lifecycle lives here once

```csharp
namespace ApiTests.Base;

public abstract class BasePlaywrightApiTest
{
    private IPlaywright playwright = null!;
    private readonly List<IAPIRequestContext> createdContexts = [];

    protected string AuthToken { get; private set; } = string.Empty;

    [OneTimeSetUp]
    public async Task SetUpPlaywrightAsync()
    {
        playwright = await Playwright.CreateAsync();
        AuthToken = await AuthHelper.GetTokenAsync(TestUsers.Standard);
    }

    /// One context per identity. string.Empty → no Authorization header at all.
    protected async Task<IAPIRequestContext> NewContextAsync(string token)
    {
        Dictionary<string, string> headers = new();
        if (token != string.Empty)
        {
            headers["Authorization"] = $"Bearer {token}";
        }

        IAPIRequestContext context = await playwright.APIRequest.NewContextAsync(new()
        {
            BaseURL = ConfigurationLoader.Settings.ApiBaseUrl,
            ExtraHTTPHeaders = headers,
        });
        createdContexts.Add(context);
        return context;
    }

    [OneTimeTearDown]
    public async Task TearDownPlaywrightAsync()
    {
        foreach (IAPIRequestContext context in createdContexts)
        {
            await context.DisposeAsync();
        }
        createdContexts.Clear();
        playwright.Dispose();
    }
}
```

`Deserialize<T>(IAPIResponse)` (System.Text.Json over `await response.TextAsync()`) and
`AttachBody(IAPIResponse)` (Allure attachment for error tests) live here too — same roles as in `BaseApiTest`
of the RestSharp sibling.

## Fixture template

```csharp
namespace ApiTests.Tests;

[TestFixture]
public class UserTests : BasePlaywrightApiTest
{
    private UserClient userClient = null!;
    private UserClient anonymousClient = null!;

    [OneTimeSetUp]
    public async Task SetUpClientsAsync()
    {
        userClient = new UserClient(await NewContextAsync(AuthToken));
        anonymousClient = new UserClient(await NewContextAsync(string.Empty));
    }

    [Test]
    [AllureFeature("Users")]
    [AllureStory("TC-USER-001 — list users")]
    [AllureSeverity(SeverityLevel.critical)]
    public async Task GetUsers_WhenAuthorized_ReturnsAll()
    {
        List<UserDto> users = await userClient.GetAllAsync(HttpStatusCode.OK);

        Assert.That(users, Is.Not.Empty, "Expected at least one user.");
    }

    [Test]
    [AllureFeature("Users")]
    [AllureStory("TC-USER-002 — unauthorized")]
    [AllureSeverity(SeverityLevel.critical)]
    public async Task GetUsers_WhenNotAuthenticated_ReturnsUnauthorized()
    {
        IAPIResponse response = await anonymousClient.GetAllAsync();

        Assert.That((HttpStatusCode)response.Status, Is.EqualTo(HttpStatusCode.Unauthorized));
    }

    [Test]
    [AllureFeature("Users")]
    [AllureStory("TC-USER-004 — not found")]
    [AllureSeverity(SeverityLevel.normal)]
    public async Task GetUser_WhenIdDoesNotExist_ReturnsNotFoundProblem()
    {
        IAPIResponse response = await userClient.GetByIdAsync("999999");

        AttachBody(response);
        Assert.That((HttpStatusCode)response.Status, Is.EqualTo(HttpStatusCode.NotFound));
        ProblemDetailsDto problem = Deserialize<ProblemDetailsDto>(response);
        Assert.Multiple(() =>
        {
            Assert.That(problem.Type, Is.EqualTo("BusinessViolation"));
            Assert.That(problem.ErrorCode, Is.EqualTo("USER_NOT_FOUND"));
        });
    }
}
```

Create/update flows keep the RestSharp sibling's discipline unchanged: the rich happy-path template (request
fields + server-generated fields + `GetById` round-trip in `Assert.Multiple`), per-test cleanup via
`try { … } finally { try { await client.DeleteAsync(...); } catch { } }`, `[TearDown]` for data created in
`[SetUp]`.

## Scenario → pattern matrix

| Scenario | Client overload / identity | Assertion pattern |
|----------|----------------------------|-------------------|
| 2xx happy path | **typed** (`HttpStatusCode expected`) on the standard/admin context | DTO returned already status-asserted; apply the rich happy-path template in `Assert.Multiple` |
| 401 unauthorized | **raw** on the `NewContextAsync(string.Empty)` client | single status assertion — auth middleware emits no `ProblemDetails` |
| 403 forbidden | **raw** on a wrong-role context | single status assertion |
| 400 / 404 / 422 | **raw** | `AttachBody` → status → `Deserialize<ProblemDetailsDto>` → the strict `ProblemDetails` template from the generator sibling |
| Malformed JSON / extra-missing property | **raw** via `CreateRawAsync(string)` overload | status assert only — add these overloads following `api-client-writer` when the plan requires them |
| Eventually-consistent state | **raw/typed** inside a polling helper | poll on the condition with a timeout — never `Thread.Sleep` / `Task.Delay` loops without a condition |

## Rules

### Fixture structure & naming

- Same as the RestSharp sibling: `ApiTests/Tests/{Resource}Tests.cs`, `[TestFixture]`, one class per resource,
  `[Action]_[Condition]_[ExpectedOutcome]` names, `[AllureFeature]`/`[AllureStory]`/`[AllureSeverity]` on every
  test, TC-ID carried in `[AllureStory]` / `[Property("TmsLink", …)]`.
- Every fixture extends `BasePlaywrightApiTest`; identity clients are built in `[OneTimeSetUp]` from
  `NewContextAsync(token)`. Never create an `IPlaywright` or a context inside a test method.
- **No `var`** — explicit types (`IAPIResponse response`, `UserDto user`, `List<UserDto> users`).
- Meaningful client field names per identity (`userClient`, `adminClient`, `anonymousClient`) — never a generic `client`.

### Test rules

- Everything is `async Task` — no `.Result`, `.Wait()`, or `GetAwaiter().GetResult()` anywhere.
- Assert the **exact** status code, always, before reading the body — `(HttpStatusCode)response.Status`, never
  `response.Ok` (it passes on any 2xx). Never rely on Playwright throwing for you (`FailOnStatusCode` stays off).
- Happy path uses the **typed** overload; 4xx tests use the **raw** overload with `AttachBody` first, then the
  strict `ProblemDetails` template. Never re-assert the status after a typed call.
- NUnit assertions only; `Assert.Multiple` for two or more related assertions.
- Request bodies with 4+ fields come from builders (`qa/dotnet/skills/test-data-builder`); DTOs are passed via
  `DataObject` in the client (`context.PostAsync(url, new() { DataObject = dto })`) — never hand-built JSON strings in tests.
- Tests are independent: per-test data, cleanup in `try/finally` or `[TearDown]`, no execution-order assumptions.
- Rows that differ only in data → `[TestCase]` / `[TestCaseSource]` (`qa/dotnet/skills/data-driven-testing`).

### What NOT to do

- No `context.GetAsync(...)` / `playwright.APIRequest` calls in tests — every request goes through a `{Resource}Client`.
- No RestSharp *and* Playwright HTTP in one suite — one client stack; if RestSharp is already established, stay on the generator sibling.
- No token threading per call — identity lives in the context (`ExtraHTTPHeaders` at creation), or in a storage
  state shared with the UI suite for cookie-auth apps (`APIRequestNewContextOptions.StorageStatePath`).
- No leaked resources — every context `DisposeAsync`d, `playwright.Dispose()` in `[OneTimeTearDown]`.
- No `response.Ok` as the status assertion; no `Thread.Sleep`; no `.Result`/`.Wait()`.
- No `JsonSerializer.Deserialize` in test code — typed overloads for positive tests, `Deserialize<T>(response)` for raw access. No `Newtonsoft.Json`.
- No `var`; no FluentAssertions; no hardcoded base URLs or tokens — `ConfigurationLoader` + `AuthHelper`.

## Generation steps

1. Confirm the project uses Microsoft.Playwright (the package reference). If not, stop and route to
   `api-test-author/generator` — say why.
2. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document (one test per TC-ID, tagged for
   traceability), or verbal scenarios.
3. Ensure `BasePlaywrightApiTest` exists with the lifecycle above (plus `Deserialize<T>` / `AttachBody`); create it if missing.
4. For each resource in scope, verify the DTOs and the context-based `{Resource}Client` exist — create missing
   ones via `api-dto-writer`, then the client following `api-client-writer` conventions with the
   `(IAPIRequestContext)` constructor.
5. Author one fixture per resource from the scenario matrix: rich happy-path template for 2xx, strict
   `ProblemDetails` template for 4xx, single status assert for 401.
6. Verify every test name follows `[Action]_[Condition]_[ExpectedOutcome]` and every TC-ID maps to a test or is explicitly deferred.
7. Run `dotnet build ApiTests/ApiTests.csproj` then `dotnet test` — expect 0 errors, 0 failures.

## Cross-references

- `qa-api-test-author-generator-dotnet` — the **stack default** (NUnit + RestSharp); this skill is the variant
  for Playwright-first projects. Shared spine: layering, dual raw/typed overloads, rich happy-path + strict
  `ProblemDetails` templates, cleanup discipline.
- `qa-api-test-author-playwright-typescript` · `qa-api-test-author-playwright-java` — the sibling stacks
  (@playwright/test `request` fixture · playwright-java + TestNG); same four ideas, different bindings.
- `qa-api-dto-writer-dotnet` / `qa-api-client-writer-dotnet` — DTOs / the client layer this skill consumes.
- `qa-ui-test-author-playwright-dotnet` — the UI suite this skill shares the Playwright dependency with.
- `qa-network-monitoring-dotnet` — `page.RouteAsync` mocking/asserting of browser traffic (not API testing).
- `qa-api-test-author-reviewer-dotnet` — review; its cross-stack checklist applies verbatim, plus this skill's
  What-NOT-to-do list as Playwright-specific findings.
- `qa-auth0-test-tokens-dotnet` — the tokens `NewContextAsync(token)` injects.
- `qa-allure-reporting-dotnet` — Allure NUnit wiring shared with the UI suite.
