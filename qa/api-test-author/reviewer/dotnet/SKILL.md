---
name: qa-api-test-author-reviewer-dotnet
description: Use when the user asks to review existing .NET API test code (NUnit + RestSharp) for quality. Triggers: "review this API test", "look at OrderTests.cs", "spot issues in this *Action / client class", "is this NUnit RestSharp test any good". Do NOT use for generating new tests (use `qa/api-test-author/generator/dotnet`), for the Java sibling (use `qa/api-test-author/reviewer/java`), for the TypeScript sibling (use `qa/api-test-author/reviewer/typescript`), or for UI tests (use `qa/ui-test-author/reviewer`).
---

# QA — API Test Reviewer (.NET / NUnit + RestSharp)

Reviews .NET API test code against the patterns enforced by `qa/api-test-author/generator/dotnet`. Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (test fixture, RestSharp client, DTO)
- Pre-merge gate on a PR that touches `ApiTests/`
- The user wants a second opinion on assertion strategy or `ProblemDetails` coverage

## When NOT to use

- Generating new .NET tests → `qa/api-test-author/generator/dotnet`
- Java reviews → `qa/api-test-author/reviewer/java`
- TypeScript reviews → `qa/api-test-author/reviewer/typescript`
- DTO scaffolding → `qa/api-dto-writer/dotnet`
- UI tests → `qa/ui-test-author/reviewer`
- Reviewing the overall test strategy / pyramid → `qa/_shared/test-strategy`

## Inputs needed

1. **Files** under review — test fixture, RestSharp client, DTO
2. **Endpoint contract** if available (OpenAPI snippet, sample 4xx body) — needed to grade `ProblemDetails` / error-body assertions
3. **Project conventions** that override defaults (e.g. project standardized on `ErrorDto` rather than `ProblemDetailsDto`)

## Review checklist

### Cross-stack (applies to all API tests)

| Check | Bad sign | Severity |
|---|---|---|
| Each test asserts something | Test ends after the request with no assertion | blocker |
| Status code is always asserted first | Test reads body before checking status | major |
| Tests are independent | Test B reads a row that Test A creates | blocker |
| No hardcoded credentials, base URLs, tokens | Literal `"https://staging..."` or `"x-api-key: abc123"` | blocker |
| No `Thread.Sleep` | Any literal millisecond sleep | blocker |
| Resource cleanup on resources the test created | Created records left in the system if the test fails mid-way | major |
| One logical behavior per test | A single test asserts 200 path AND 404 path AND 401 path | major |
| Test names describe behavior | `Test1`, `TestGet`, `It_Works` | minor |
| Deserialization uses a typed DTO | `JsonNode` / dictionary parsing in assertions | major |
| Status codes via named constants | Raw integers (`200`, `401`) | minor |
| Error responses asserted beyond status | A 400/404/422 test that only asserts the code, ignoring the body | major |

### .NET (NUnit + RestSharp) specifics

| Check | Bad sign | Severity |
|---|---|---|
| Fixture inherits `BaseApiTest` | Direct test class with hand-built RestSharp clients | major |
| Single `AuthToken` convention (post P/M-client collapse) | `*PClient` / `*MClient` types or `UserAuthToken` / `AdminAuthToken` references | minor |
| Positive tests use the typed client overload with `HttpStatusCode expected` | Test reads `response.StatusCode` then calls `Deserialize<T>` manually for a happy path | major |
| 4xx tests apply the strict `ProblemDetails` template | A 400/404/422 that asserts only `response.StatusCode` | major |
| `AttachBody(response)` called before asserting an error body | Failure produces a status-code message but no body in Allure | minor |
| `Assert.That` + `Assert.Multiple` only — no FluentAssertions | `.Should()`, `AssertionScope` | major |
| `System.Text.Json` only — no Newtonsoft | `JsonConvert.DeserializeObject` | major |
| Explicit types — no `var` for known types | `var dto = client.Create(...)` | minor |
| Client variable named after concrete type in camelCase | Generic `client` variable | nit |
| Resources created in the test wrapped in `try { ... } finally { try { cleanup; } catch { } }` | Bare cleanup that swallows test failures if it throws | major |
| 401 test uses a single status-code assertion | A 401 test that tries to deserialize a `ProblemDetails` body | minor |
| `[AllureFeature]` + `[AllureStory]` + `[AllureSeverity]` on every test | Missing Allure attributes | minor |
| No `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` | Sync-over-async on an async RestSharp call | blocker |

## Procedure

1. Confirm imports show NUnit + RestSharp (`using NUnit.Framework;`, `using RestSharp;`).
2. Read the whole file (test + client + DTO) before writing findings — cross-file issues are usually the real bugs.
3. Walk the cross-stack checklist, then the .NET-specific list.
4. For each finding, capture: file + line, the issue (concrete, not "looks weird"), and a one-sentence fix.
5. **Do not rewrite the code.** Hand off to `qa/api-test-author/generator/dotnet` if the user wants the rewrite.

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | ApiTests/Tests/OrderTests.cs:67                   | `Thread.Sleep(2000)` between create and read                | Remove — the create is synchronous; rely on response body              |
| major    | ApiTests/Tests/OrderTests.cs:88                   | 400 test asserts only `StatusCode`, ignores ProblemDetails  | Apply strict template: assert Type/Title/Status + `Errors["Amount"]`   |
| minor    | ApiTests/Clients/OrderClient.cs:42                | Raw integer `200` in expected status                        | Use `HttpStatusCode.OK`                                                |
| nit      | ApiTests/Tests/OrderTests.cs:14                   | Test name `Test1`                                           | Rename to behavior: `GetOrderByIdReturnsOk`                            |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, hard rule violation (sleeps, leaked credentials, shared state, sync-over-async)
- **major** — design / correctness issue that will hurt soon (silent failures, lost coverage, wrong layering)
- **minor** — style / small inconsistency (naming, constants)
- **nit** — optional preference

## Anti-patterns to always flag

- **Status-code-only 4xx test.** When the backend emits a `ProblemDetails` body, asserting just the code throws away the highest-signal failure information.
- **Happy-path test that asserts one field.** Round-trip persistence (GET-after-POST) is cheap and catches most regressions; one-field tests pass through real bugs.
- **Client that deserializes.** Couples response shape to the client layer and removes the test's ability to assert on raw `RestResponse` for error paths.
- **Shared mutable test data.** Tests must remain independent; pre-seeded shared rows always end up being mutated by some test eventually.
- **401 test that deserializes a body.** Auth middleware returns no body — wasting effort and producing flaky `null` checks.
- **Cleanup that can mask failures.** A `finally` that throws on cleanup error replaces the real assertion error with a cleanup error. Wrap cleanup in try/catch inside `finally`.
- **Reading dates as strings.** Forgetting `JsonSerializerOptions` for dates causes silent `null` reads.
- **Tests tightly coupled to specific data ids.** "Order 42 exists in staging" tests fail the day someone reseeds.

## Handoffs

- Need a rewrite → `qa/api-test-author/generator/dotnet`
- DTO is wrong → `qa/api-dto-writer/dotnet`
- Client layer needs refactor → `qa/api-client-writer`
- Whole test pyramid is the issue → `qa/_shared/test-strategy`
- Java sibling → `qa/api-test-author/reviewer/java`
- TypeScript sibling → `qa/api-test-author/reviewer/typescript`

## Changelog

- 2026-05-28: Split out of the monolithic `qa/api-test-author/reviewer/SKILL.md` to align with the three-stack convention. Content unchanged from the original .NET section.
