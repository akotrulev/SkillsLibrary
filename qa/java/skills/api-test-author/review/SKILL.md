---
name: qa-api-test-review-java
description: Use when the user asks to review existing Java API test code (RestAssured + TestNG) for quality. Triggers: "review this RestAssured test", "look at OrderTest.java", "spot issues in this {Resource}Client class". Not for generating new tests → `api-test-author/generator`. For end-to-end suite work prefer the staged agent `qa-api-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — API Test Reviewer (Java / RestAssured + TestNG)

Reviews Java API test code against the patterns enforced by `qa/java/skills/api-test-author/writer`, `qa/java/skills/api-client-writer`, and `qa/java/skills/api-models` (the DTO-records + `{Resource}Client` dual-overload layering). Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (TestNG class, `{Resource}Client`, record DTO)
- Pre-merge gate on a PR that touches `src/test/java/`
- The user wants a second opinion on assertion strategy or error-body coverage

## When NOT to use

- Generating new Java tests → `qa/java/skills/api-test-author/writer`
- .NET reviews → `qa/dotnet/skills/api-test-author/review`
- TypeScript reviews → `qa/typescript/skills/api-test-author/review`
- DTO scaffolding → `qa/java/skills/api-models`
- UI tests → `qa/java/skills/ui-test-author/review`
- Reviewing the overall test strategy / pyramid → `qa/manual/test-strategy`

## Inputs needed

1. **Files** under review — TestNG test class, `{Resource}Client`, record DTOs
2. **Endpoint contract** if available (OpenAPI snippet, sample 4xx body) — needed to grade error-body assertions
3. **Project conventions** that override defaults (e.g. project standardized on `ErrorPojo` rather than `ProblemDetailsDto`)

## Review checklist

### Cross-stack (applies to all API tests)

| Check | Bad sign | Severity |
|---|---|---|
| Each test asserts something | Test ends after the request with no assertion | blocker |
| Status code is always asserted first | Test reads body before checking status | major |
| Tests are independent | Test B reads a row that Test A creates | blocker |
| No hardcoded credentials, base URLs, tokens | Literal `"https://staging..."` or `"x-api-key: abc123"` | blocker |
| No `Thread.sleep` | Any literal millisecond sleep | blocker |
| Resource cleanup on resources the test created | Created records left in the system if the test fails mid-way | major |
| One logical behavior per test | A single test asserts 200 path AND 404 path AND 401 path | major |
| No `try`/`catch` anywhere in a test or `@AfterMethod` | Any catch block in a `@Test`; a `try/finally` wrapping the body for cleanup; a swallowing teardown | major |
| Created resources tracked and deleted in `@AfterMethod(alwaysRun = true)` | Cleanup inlined in the test body instead of registered | major |
| Unexpected errors fail loudly with an identifying message | Empty `catch`, catch-and-continue, or an assertion whose failure names no id/subject | major |
| Deserialization failures name the Jackson path and body | A bare `MismatchedInputException` trace with no attached body | major |
| Every assertion states one expected condition | `assertTrue(s == SC_OK \|\| s == SC_NO_CONTENT)`, `anyOf(...)` / `either().or()` matchers — on a status, a field, a size, or a duration | major |
| Test names describe behavior | `test1`, `testGet`, `it_works` | minor |
| Deserialization uses a typed DTO | `Map<String,Object>` / `jsonPath().get(...)` in assertions | major |
| Status codes via named constants | Raw integers (`200`, `401`) | minor |
| Error responses asserted beyond status | A 400/404/422 test that only asserts the code, ignoring the body | major |

### Java (RestAssured + TestNG) specifics

| Check | Bad sign | Severity |
|---|---|---|
| Test extends `BaseTest`; client extends `BaseApiClient` | A test that calls `RestAssured.given()` directly instead of going through a `{Resource}Client` | major |
| Dual-overload pattern intact: raw returns `Response` with no assertion; typed (`int expectedStatus`) asserts status and deserializes, delegating to the raw overload | Raw method that deserializes; typed overload that rebuilds the request instead of calling the raw one | major |
| Happy path uses the **typed** overload; negative tests use the **raw** overload | Negative test calling the typed overload (forces deserialization of an error body into the resource DTO); test re-asserting status after a typed call | major |
| Token fetched in the test via `AuthHelper` and passed to the client constructor; `""` for unauthenticated | Client fetching its own token internally; token literal in the test | major |
| Error bodies deserialized in the test via `response.as(ErrorDto.class)` with a modeled DTO | Test inspects `response.getBody().jsonPath().get(...)` | major |
| `HttpStatus.SC_*` constants (Apache HttpClient) — never raw ints | `assertEquals(200, response.getStatusCode())` | minor |
| `SoftAssert` for multi-field checks, with `soft.assertAll()` at the end | Multiple hard `Assert.assertEquals` calls that stop at the first failure; `SoftAssert` without `assertAll()` (silently passes) | major |
| Path constants declared as `private static final String` in `SCREAMING_SNAKE_CASE` at the top of the client | Inline path strings in client methods | minor |
| DTOs are records with `@JsonProperty` on **every** component | Mutable Lombok `@Data` POJO used as a DTO; missing annotation relying on field-name reflection | major |
| Test method names follow `Should_X_When_Y` | `test1`, `testGetUser` (no behavior) | minor |
| TC-ID traceability via `@Test(description = "TC-…")` when a test-case document exists | Tests with no link back to the planned cases | nit |
| `@Test(groups = ...)` used so suites can filter | Untagged tests that always run | nit |
| `JavaTimeModule` registered on the `ObjectMapper` (`BaseTest` / `RestAssuredConfig`) for `OffsetDateTime` | Date fields fail to deserialize and the test silently passes with `null` | major |

### Comments in test code

Load **[`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** for the rule itself, the complex-flow test that earns a doc comment, the never-comment trivia list, and the severity mapping. Its **test-code** section carries the AAA-banner rule and the exactly-three-permitted-comments list. This section supplies only the mechanics that differ here.

| Java mechanic | What to check |
|---|---|
| Doc syntax | Javadoc (`/** … */`) — a doc block restating the test name is trivia |
| Skips needing a reason and a ticket | `@Test(enabled = false)` / `@Ignore` with nothing recorded — a silently disabled test |
| Where an unclear step goes instead | Into a named client method, not a comment above the request-building chain |

**The API-test corollary:** an instruction to accept more than one value is permitted comment #2 — but only alongside a real parameterized case (`@DataProvider`) or a split test. A comment alone does not license the `OR`.

## Procedure

1. Confirm imports show TestNG + RestAssured (`import org.testng.annotations.Test;`, `io.restassured.response.Response`).
2. Read the whole vertical slice (test + client + DTOs) before writing findings — cross-file issues are usually the real bugs.
3. Walk the cross-stack checklist, then the Java-specific list.
4. For each finding, capture: file + line, the issue (concrete, not "looks weird"), and a one-sentence fix.
5. **Do not rewrite the code.** Hand off to `qa/java/skills/api-test-author/writer` if the user wants the rewrite.

## Output format

```
| Severity | Location                                                | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | tests/order/orders/PostOrderTest.java:67                | `Thread.sleep(2000)` between create and read                | Remove — the create is synchronous; rely on response body              |
| major    | clients/order/OrderClient.java:55                       | Raw `getById` deserializes and returns `OrderDto`           | Return `Response`; deserialization belongs in the typed overload       |
| minor    | clients/order/OrderClient.java:42                       | Inline path literal `"/api/orders/{id}"` repeated in 3 methods | Extract `private static final String GET_BY_ID_PATH`                |
| nit      | tests/order/orders/GetOrderTest.java:14                 | Test name `test1`                                           | Rename to behavior: `Should_ReturnOrder_When_FetchedById`              |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, hard rule violation (sleeps, leaked credentials, shared state)
- **major** — design / correctness issue that will hurt soon (silent failures, lost coverage, wrong layering)
- **minor** — style / small inconsistency (naming, constants)
- **nit** — optional preference

## Anti-patterns to always flag

- **Status-code-only 4xx test.** When the backend emits an error body, asserting just the code throws away the highest-signal failure information.
- **`OR` in an assertion.** `assertTrue(status == SC_OK || status == SC_NO_CONTENT)` (or a Hamcrest `anyOf` / `either().or()`) means the author did not know what the endpoint returns, so the test passes on the wrong behavior and never fails when the API changes between the two. Applies to fields, sizes, and time budgets as much as to status codes. Fix by splitting into one test per expected outcome, driving it from a `@DataProvider`, or pinning the correct value.
- **Happy-path test that asserts one field.** Round-trip persistence (GET-after-POST) is cheap and catches most regressions; one-field tests pass through real bugs.
- **Raw overload that deserializes.** Couples response shape to the request layer and removes the test's ability to assert on the raw `Response` for error paths.
- **Negative test through the typed overload.** Forces deserialization of an error body into the resource DTO — either a misleading exception or a DTO full of nulls.
- **Shared mutable test data.** Tests must remain independent; pre-seeded shared rows always end up being mutated by some test eventually.
- **401 test that deserializes a body.** Auth middleware returns no body — wasting effort and producing flaky `null` checks.
- **A `try`/`catch` inside a test.** There is no legitimate one: an expected exception is asserted with `assertThrows`, an unexpected one must reach TestNG, and cleanup belongs in `@AfterMethod(alwaysRun = true)`. A catch in a test body is either hiding a failure or substituting for an assertion.
- **A `try`/`finally` wrapping a test body for cleanup.** Track the created id and delete it in `@AfterMethod` — the test body stays linear and cleanup runs whether the test passed, failed, or threw.
- **A swallowing `@AfterMethod`.** An empty catch around the delete means the suite leaks data silently until the environment rots. Let it throw; TestNG reports the configuration failure.
- **Deserialization failure with no context.** A raw `Cannot deserialize value of type int from String ""` with no attached body and no Jackson path makes the reader reproduce the call by hand to learn what the test already knew.
- **Forgetting `JavaTimeModule`.** Date fields fail to deserialize and the test silently passes with `null`.
- **Tests tightly coupled to specific data ids.** "Order 42 exists in staging" tests fail the day someone reseeds.

## Handoffs

- Need a rewrite → `qa/java/skills/api-test-author/writer`
- DTO is wrong → `qa/java/skills/api-models`
- Client layer needs refactor → `qa/java/skills/api-client-writer`
- Whole test pyramid is the issue → `qa/manual/test-strategy`
- .NET sibling → `qa/dotnet/skills/api-test-author/review`
- TypeScript sibling → `qa/typescript/skills/api-test-author/review`
