---
name: qa-api-test-playwright-dotnet
description: Use when writing .NET API tests through Playwright's `IAPIRequestContext` (Microsoft.Playwright + NUnit) — usually because the project already runs Playwright for UI and wants one dependency and one report. Triggers "write API tests with Playwright in C#", "use IAPIRequestContext for endpoint X", "add API coverage to our Playwright .NET suite". Do NOT use for API suites without Playwright (`qa-api-test-writer-dotnet`, the RestSharp default).
---

# QA — API Test Writer (.NET / Playwright IAPIRequestContext + NUnit)

Authors NUnit fixtures that test a REST backend through **Microsoft.Playwright's HTTP client** —
`IAPIRequestContext` — instead of RestSharp. It reuses the layering and templates of the RestSharp sibling
(`qa-api-test-writer-dotnet`): DTOs from `qa/dotnet/skills/api-models`, a `{Resource}Client` with
dual raw + typed overloads, fixtures that own scenarios, the rich happy-path template for 2xx and the strict
`ProblemDetails` template for 4xx. Only the HTTP transport changes; the discipline does not.

> **The discipline this skill encodes** — four ideas that separate a correct Playwright .NET API suite from a
> RestSharp reflex ported onto the wrong client:
>
> 1. **The `IAPIRequestContext` is the auth boundary, not the call site.** Base URL and the `Authorization`
>    header are set **once, at context creation** (`playwright.APIRequest.NewContextAsync(new() { BaseURL,
>    ExtraHTTPHeaders })`). One context per identity — standard, admin, anonymous — never a token argument
>    threaded through every call.
> 2. **Contexts are resources with an async lifecycle, and `PlaywrightTest` owns the driver.** The base fixture
>    derives from `Microsoft.Playwright.NUnit`'s `PlaywrightTest`, which provides the process-wide `Playwright`
>    in its own `[SetUp]` — no `Playwright.CreateAsync()` in a fixture. Each test builds the identity contexts
>    it needs in `[SetUp]`, and the base `[TearDown]` disposes every one. Everything is `async Task` — never
>    `.Result` / `.Wait()`.
> 3. **You are here for one dependency and one report.** A project already running Microsoft.Playwright for UI
>    gets API tests with no extra HTTP stack, the same NUnit + Allure wiring and — for cookie-authenticated
>    apps — a shared **storage state**. Without a Playwright UI suite, the default is RestSharp
>    (`api-test-author/writer`).
> 4. **The layering survives the client swap.** `{Resource}Client` wraps the context; its raw overload returns
>    `IAPIResponse` unasserted, its typed overload asserts the **exact** status and deserializes the body. The
>    constructor takes an **`IAPIRequestContext`**, because the context now carries the identity.

## Stack

- .NET 10 (8/9 supported — match the TFM), nullable reference types enabled
- **NUnit** — the global default runner (same as the UI suite); `Assert.That` / `Assert.Multiple` only, no FluentAssertions
- **Microsoft.Playwright.NUnit** at the pins in the **Versions** table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing) — `PlaywrightTest`, `IAPIRequestContext` / `IAPIResponse`; no RestSharp dependency in a Playwright-first project. API fixtures launch no browser, so they need no browser install
- **System.Text.Json** — deserialization lives in the client's typed overloads and `BasePlaywrightApiTest.Deserialize<T>`, never inline in tests
- **Allure NUnit**; `HttpStatusCode` constants
- Layout mirrors the RestSharp sibling: `ApiTests/Models/`, `ApiTests/Clients/`, `ApiTests/Tests/`,
  `ApiTests/Base/BasePlaywrightApiTest.cs`

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `Models/{Resource}Dto.cs` | `qa/dotnet/skills/api-models` | Body shapes, `JsonPropertyName` mapping, `ProblemDetailsDto` |
| `Clients/{Resource}Client.cs` — constructor takes `IAPIRequestContext` | `qa/dotnet/skills/api-client-writer` conventions, context-based variant | Request building on the context; raw `IAPIResponse` overload + typed overload (asserts exact status, deserializes) |
| `Base/BasePlaywrightApiTest.cs` | **this skill** | `PlaywrightTest` base, per-test identity contexts (`NewContextAsync(token)`, disposed in `[TearDown]`), `ParallelScope.Self`, `Deserialize<T>`, `AttachBody` |
| `Tests/{Resource}Tests.cs` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

If a DTO or client a test needs is missing, run the owner skill first — never call `context.GetAsync(...)`
inline in a test to avoid creating a client.

## When to use

- The project already runs Microsoft.Playwright for UI and wants API coverage without adding RestSharp
- Hybrid suites where API setup/assertions and UI flows must share one Playwright installation, report, and storage state
- New `{Resource}Tests.cs` under a Playwright-based API suite, or new test methods on an existing fixture

## When NOT to use

- No Playwright in the project → `qa/dotnet/skills/api-test-author/writer` (NUnit + RestSharp, the stack default)
- API calls **inside a UI test** (seed data, then drive the browser) → the UI suite's arrange step; conventions in `qa/dotnet/skills/ui-test-author/playwright`
- Mocking/intercepting the browser's network traffic (`page.RouteAsync`) → `qa/dotnet/skills/network-mocking`
- GraphQL / gRPC → the protocol siblings under `qa/dotnet/skills/api-test-author/`
- Reviewing existing tests → `qa/dotnet/skills/api-test-author/review` for the cross-stack rows, plus this skill's § Review for the transport rows

## Base class template — the lifecycle lives here once

```csharp
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

namespace ApiTests.Base;

[Parallelizable(ParallelScope.Self)]
public abstract class BasePlaywrightApiTest : PlaywrightTest
{
    private readonly List<IAPIRequestContext> createdContexts = [];

    protected async Task<IAPIRequestContext> NewContextAsync(string token)
    {
        Dictionary<string, string> headers = new();
        if (token != string.Empty)
        {
            headers["Authorization"] = $"Bearer {token}";
        }

        IAPIRequestContext context = await Playwright.APIRequest.NewContextAsync(new()
        {
            BaseURL = ConfigurationLoader.Settings.ApiBaseUrl,
            ExtraHTTPHeaders = headers,
        });
        createdContexts.Add(context);
        return context;
    }

    [TearDown]
    public async Task DisposeContextsAsync()
    {
        foreach (IAPIRequestContext context in createdContexts)
        {
            await context.DisposeAsync();
        }
        createdContexts.Clear();
    }
}
```

- `PlaywrightTest` sets `Playwright` in its own `[SetUp]`, before the fixture's, so a fixture's `[SetUp]` can open
  contexts; the fixture's `[TearDown]` runs before `DisposeContextsAsync`, so cleanup still has its contexts.
- **Contexts are per test**, from a cached token (`qa/dotnet/skills/test-login-tokens`) — cheap. In
  `[OneTimeSetUp]` there is no `Playwright` yet, and a shared context would couple the tests.
- **`ParallelScope.Self`**: the contexts are instance fields on the one fixture instance. `string.Empty` as the
  token sends no `Authorization` header.

`Deserialize<T>(IAPIResponse)` (System.Text.Json over `await response.TextAsync()`) and
`AttachBody(IAPIResponse)` (Allure attachment for error tests) live here too — same roles as in `BaseApiTest`
of the RestSharp sibling.

## Fixture template

[`references/templates.md`](references/templates.md) holds the resource fixture (`UserTests`: identity clients
built in `[SetUp]`, the typed 2xx call, the raw 401 and the strict 404 `ProblemDetails` template) and the
create/round-trip test with its cleanup. Cleanup is the fixture's **`[TearDown]` only**: each test records the
ids it created, and the teardown deletes them through the client with `Assert.MultipleAsync`, asserting each
delete's exact status with the body as the message. No `try`/`catch`/`finally` in a test or a hook.

## Request-context options

| Option | Use | Since |
|---|---|---|
| `BaseURL`, `ExtraHTTPHeaders` | the identity, set once at creation | — |
| `FailOnStatusCode` | stays **off** (the default): the test asserts the exact status with the body; a throw would hide both | 1.51 |
| `MaxRedirects` | set it (or `0`) where the test asserts a `3xx` itself | 1.52 |
| `StorageStatePath` | cookie-authenticated apps: share the UI suite's signed-in state | — |

From 1.64: `IAPIRequestContext` cookie methods. On 1.63, cookies come from `StorageStatePath` or from a browser
context (`Page.APIRequest` shares the page's cookies).

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

- `ApiTests/Tests/{Resource}Tests.cs`, one class per resource, **`Should_X_When_Y` names** (CLAUDE.md; the
  RestSharp sibling's older `[Action]_[Condition]_[ExpectedOutcome]` shape is not used here),
  `[AllureFeature]` on the class and `[AllureStory]`/`[AllureSeverity]` on every test, TC-ID carried in
  `[AllureStory]` / `[Property("TmsLink", …)]`.
- Every fixture extends `BasePlaywrightApiTest`; identity clients are built in the fixture's `[SetUp]` from
  `NewContextAsync(token)`. Never `Playwright.CreateAsync()`, and never a context inside a test method.
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
- Tests are independent: per-test data, cleanup in the fixture's `[TearDown]` only — never a `try`/`finally` in a
  test — and no execution-order assumptions.
- Rows that differ only in data → `[TestCase]` / `[TestCaseSource]` (`qa/dotnet/skills/data-driven-testing`).

### What NOT to do

- No `context.GetAsync(...)` / `playwright.APIRequest` calls in tests — every request goes through a `{Resource}Client`.
- No RestSharp *and* Playwright HTTP in one suite — one client stack; if RestSharp is already established, stay on the generator sibling.
- No token threading per call — identity lives in the context (`ExtraHTTPHeaders` at creation), or in a storage
  state shared with the UI suite for cookie-auth apps (`APIRequestNewContextOptions.StorageStatePath`).
- No leaked resources — every context made through `NewContextAsync`, disposed by the base `[TearDown]`.
- No `response.Ok` as the status assertion; no `Thread.Sleep`; no `.Result`/`.Wait()`.
- No `JsonSerializer.Deserialize` in test code — typed overloads for positive tests, `Deserialize<T>(response)` for raw access. No `Newtonsoft.Json`.
- No `var`; no FluentAssertions; no hardcoded base URLs or tokens — `ConfigurationLoader` + `Tokens`.

## Review

Step 4 of `qa-api-dotnet` reviews a suite this skill wrote with **`qa/dotnet/skills/api-test-author/review`'s
cross-stack rows plus these rows** — its RestSharp-specific rows do not apply to an `IAPIRequestContext` client.
Same table format and severities.

| Check | Bad sign | Severity |
|---|---|---|
| One lifecycle | `Playwright.CreateAsync()` in a fixture, a `[SetUp]` or a `[OneTimeSetUp]`; a base class not derived from `PlaywrightTest` | blocker |
| Requests go through a client | `context.GetAsync(...)` / `Playwright.APIRequest` in a test body | major |
| Identity lives in the context | A token argument threaded through every client call | major |
| Contexts are disposed | A context created outside `NewContextAsync`, or a base with no disposing `[TearDown]` | major |
| Exact status, body in the message | `response.Ok`, `Expect(response).ToBeOKAsync()`, `FailOnStatusCode = true` | major |
| Cleanup in `[TearDown]` only | `try`/`finally` (or any `catch`) in a test; a delete whose status is not asserted | major |
| Parallelism is `ParallelScope.Self` | `ParallelScope.All`/`Children` on a fixture whose clients are instance fields | blocker |
| Names and comments | Not `Should_X_When_Y`; an inline comment in a test or client body | minor |

## Generation steps

1. Confirm the project uses Microsoft.Playwright (the package reference). If not, stop and route to
   `api-test-author/writer` — say why.
2. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document (one test per TC-ID, tagged for
   traceability), or verbal scenarios.
3. Ensure `BasePlaywrightApiTest` exists with the lifecycle above (plus `Deserialize<T>` / `AttachBody`); create it if missing.
4. For each resource in scope, verify the DTOs and the context-based `{Resource}Client` exist — create missing
   ones via `api-models`, then the client following `api-client-writer` conventions with the
   `(IAPIRequestContext)` constructor.
5. Author one fixture per resource from the scenario matrix: rich happy-path template for 2xx, strict
   `ProblemDetails` template for 4xx, single status assert for 401.
6. Verify every test name follows `Should_X_When_Y` and every TC-ID maps to a test or is explicitly deferred; review with § Review.
7. Run `dotnet build ApiTests/ApiTests.csproj` then `dotnet test` — expect 0 errors, 0 failures. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- `qa-api-test-writer-dotnet` — the **stack default** (NUnit + RestSharp); this skill is its Playwright-first
  variant with the same layering, overloads and templates.
- `qa-api-test-playwright-typescript` · `qa-api-test-playwright-java` — the sibling stacks.
- `qa-api-models-dotnet` / `qa-api-client-writer-dotnet` — DTOs / the client layer this skill consumes.
- `qa-ui-test-writer-playwright-dotnet` — the UI suite this skill shares the Playwright dependency with.
- `qa-network-mocking-dotnet` — browser traffic mocking, not API testing.
- `qa-api-test-review-dotnet` — review; its cross-stack checklist applies verbatim, and this skill's § Review
  replaces its RestSharp rows (`qa-api-dotnet` Step 4 loads both).
- `qa-test-login-tokens-dotnet` — the tokens `NewContextAsync(token)` injects.
- `qa-test-reports-dotnet` — Allure NUnit wiring shared with the UI suite.
