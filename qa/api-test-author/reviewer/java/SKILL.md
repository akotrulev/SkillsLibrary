---
name: qa-api-test-author-reviewer-java
description: Use when the user asks to review existing Java API test code (RestAssured + TestNG) for quality. Triggers: "review this RestAssured test", "look at OrderTest.java", "spot issues in this *Action class", "is this TestNG API test any good". Do NOT use for generating new tests (use `qa/api-test-author/generator/java`), for the .NET sibling (use `qa/api-test-author/reviewer/dotnet`), for the TypeScript sibling (use `qa/api-test-author/reviewer/typescript`), or for UI tests (use `qa/ui-test-author/reviewer`).
---

# QA — API Test Reviewer (Java / RestAssured + TestNG)

Reviews Java API test code against the patterns enforced by `qa/api-test-author/generator/java`. Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (TestNG class, `*Action`, POJO)
- Pre-merge gate on a PR that touches `src/test/java/`
- The user wants a second opinion on assertion strategy or error-body coverage

## When NOT to use

- Generating new Java tests → `qa/api-test-author/generator/java`
- .NET reviews → `qa/api-test-author/reviewer/dotnet`
- TypeScript reviews → `qa/api-test-author/reviewer/typescript`
- POJO scaffolding → `qa/api-dto-writer/java`
- UI tests → `qa/ui-test-author/reviewer`
- Reviewing the overall test strategy / pyramid → `qa/_shared/test-strategy`

## Inputs needed

1. **Files** under review — TestNG test class, `*Action`, POJO
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
| Test names describe behavior | `test1`, `testGet`, `it_works` | minor |
| Deserialization uses a typed POJO | `Map<String,Object>` / `jsonPath().get(...)` in assertions | major |
| Status codes via named constants | Raw integers (`200`, `401`) | minor |
| Error responses asserted beyond status | A 400/404/422 test that only asserts the code, ignoring the body | major |

### Java (RestAssured + TestNG) specifics

| Check | Bad sign | Severity |
|---|---|---|
| Test extends `BaseTest`; action extends `BaseAction` | A test that calls `RestAssured.given()` directly | major |
| Action returns `RestAssuredResponseImpl` only | Action deserializes and returns a POJO | major |
| Deserialization happens in the test via `response.as(Pojo.class)` | Test inspects `response.getBody().jsonPath().get(...)` | major |
| `HttpStatus.SC_*` constants (Apache HttpClient) — never raw ints | `assertEquals(200, response.getStatusCode())` | minor |
| `SoftAssert` for multi-field checks, with `soft.assertAll()` at the end | Multiple hard `Assert.assertEquals` calls that stop at the first failure | major |
| Header / auth state set in the action constructor (`new UserAction(true/false)`) | Auth header added inside a per-method `RequestSpecBuilder` only sometimes | minor |
| Path constants declared as `private static final String` | Inline path strings in action methods | minor |
| `@JsonProperty` on POJO fields whose JSON name differs from the Java name | Field-name mismatch caused by missing annotation | major |
| POJOs use Lombok `@Data @NoArgsConstructor @AllArgsConstructor @Builder` | Hand-rolled getters/setters duplicating Lombok behavior | minor |
| Test name describes behavior in camelCase | `test1`, `testGetUser` (no behavior) | minor |
| `@Test(groups = ...)` used so suites can filter | Untagged tests that always run | nit |
| `JavaTimeModule` registered in `BaseTest` for `ZonedDateTime` / `LocalDate` | Date fields fail to deserialize and the test silently passes with `null` | major |

## Procedure

1. Confirm imports show TestNG + RestAssured (`import org.testng.annotations.Test;`, `import io.restassured.*;`).
2. Read the whole file (test + action + POJO) before writing findings — cross-file issues are usually the real bugs.
3. Walk the cross-stack checklist, then the Java-specific list.
4. For each finding, capture: file + line, the issue (concrete, not "looks weird"), and a one-sentence fix.
5. **Do not rewrite the code.** Hand off to `qa/api-test-author/generator/java` if the user wants the rewrite.

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | src/test/java/order/OrderTest.java:67             | `Thread.sleep(2000)` between create and read                | Remove — the create is synchronous; rely on response body              |
| major    | src/main/java/action/OrderAction.java:55          | Action deserializes and returns `OrderPojo`                 | Return `RestAssuredResponseImpl`; let the test call `.as(...)`         |
| minor    | src/main/java/action/OrderAction.java:42          | Inline path literal `"/orders/{id}"` repeated in 3 methods  | Extract `private static final String BY_ID = "/orders/{id}"`           |
| nit      | src/test/java/order/GetOrderTest.java:14          | Test name `test1`                                           | Rename to behavior: `getOrderByIdReturnsOk`                            |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, hard rule violation (sleeps, leaked credentials, shared state)
- **major** — design / correctness issue that will hurt soon (silent failures, lost coverage, wrong layering)
- **minor** — style / small inconsistency (naming, constants)
- **nit** — optional preference

## Anti-patterns to always flag

- **Status-code-only 4xx test.** When the backend emits an error body, asserting just the code throws away the highest-signal failure information.
- **Happy-path test that asserts one field.** Round-trip persistence (GET-after-POST) is cheap and catches most regressions; one-field tests pass through real bugs.
- **Action that deserializes.** Couples response shape to the action layer and removes the test's ability to assert on the raw `Response` for error paths.
- **Shared mutable test data.** Tests must remain independent; pre-seeded shared rows always end up being mutated by some test eventually.
- **401 test that deserializes a body.** Auth middleware returns no body — wasting effort and producing flaky `null` checks.
- **Cleanup that can mask failures.** A `finally` that throws on cleanup error replaces the real assertion error with a cleanup error. Wrap cleanup in try/catch inside `finally`.
- **Forgetting `JavaTimeModule`.** Date fields fail to deserialize and the test silently passes with `null`.
- **Tests tightly coupled to specific data ids.** "Order 42 exists in staging" tests fail the day someone reseeds.

## Handoffs

- Need a rewrite → `qa/api-test-author/generator/java`
- POJO is wrong → `qa/api-dto-writer/java`
- Action layer needs refactor → `qa/api-client-writer`
- Whole test pyramid is the issue → `qa/_shared/test-strategy`
- .NET sibling → `qa/api-test-author/reviewer/dotnet`
- TypeScript sibling → `qa/api-test-author/reviewer/typescript`

## Changelog

- 2026-05-28: Split out of the monolithic `qa/api-test-author/reviewer/SKILL.md` to align with the three-stack convention. Content unchanged from the original Java section.
