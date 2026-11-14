---
name: api-tests
description: Use when writing Java REST API tests with RestAssured + TestNG. Triggers "write an API test for X", "automate these test cases". Not for Playwright-runner API tests (api-tests-playwright).
---

# QA — API Test Writer (Java / RestAssured + TestNG)

Authors `*Test` classes on top of the **DTO + Client + Test** layering: record DTOs (from `qa/java/skills/api-models`), `{Resource}Client` classes with dual raw + typed overloads (from `qa/java/skills/api-client-writer`), and test classes — written by this skill — that own scenario selection, test data, and assertions.

## Stack

- Java 21
- Gradle (Kotlin DSL for new projects)
- **TestNG** (`org.testng:testng`) — the global default for Java test runners
- **RestAssured** (`io.rest-assured:rest-assured`) for HTTP — accessed only through `{Resource}Client`
- **Jackson** (`jackson-databind` + `jackson-datatype-jsr310`) with **record DTOs** — no Lombok
- **Allure TestNG** for reporting
- `org.apache.http.HttpStatus` for status code constants

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `models/{api}/{resource}/{Resource}Dto.java` (records) | `qa/java/skills/api-models` | Body shapes, `@JsonProperty` mapping |
| `clients/{api}/{Resource}Client.java` | `qa/java/skills/api-client-writer` | Request building; raw `Response` overload + typed overload (asserts status, deserializes) |
| `tests/{api}/{resource}/{Operation}{Resource}Test.java` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

This skill writes **only the test classes**. If a DTO or client a test needs is missing, run the owner skill first — never hand-roll HTTP calls or inline `RestAssured.given()` to avoid creating a client.

## When to use

- New `{Operation}{Resource}Test.java` class for an endpoint that has (or will get) a client
- Adding test methods for additional scenarios on an existing resource
- Automating cases from a `qa/manual/test-case-writer` document or an OpenAPI/Swagger spec

## When NOT to use

- UI / Selenium tests → `qa/java/skills/ui-test-author/selenium`
- .NET API tests → `qa/dotnet/skills/api-test-author/writer`
- DTO-only scaffolding → `qa/java/skills/api-models`
- Client-only scaffolding → `qa/java/skills/api-client-writer`
- Reviewing existing tests → `qa/java/skills/api-test-author/review`

## Inputs needed

1. **Source of truth** — one of: an OpenAPI/Swagger spec, a formal test-case document (TC-IDs), or a verbal scenario list. When a spec or test-case document is provided, derive resources, endpoints, body shapes, and scenarios from it — do not re-ask.
2. **Resource(s) and endpoints in scope** — method, path, auth requirements
3. **Auth model** — which test user / token each scenario needs (token fetched via `AuthHelper`, passed to the client constructor)
4. **Scenarios** — happy path, 401/403, 404, 400 validation, boundary/edge

## Test class template

Tests live at `apitests/src/test/java/com/{org}/apitests/tests/{api}/{resource}/`, one class per operation, extending `BaseTest` (registers `JavaTimeModule`, Allure listener, loads configuration).

```java
package com.{org}.apitests.tests.user.users;

import com.{org}.apitests.base.BaseTest;
import com.{org}.apitests.clients.AuthHelper;
import com.{org}.apitests.clients.user.UserClient;
import com.{org}.apitests.models.user.users.UserDto;
import io.restassured.response.Response;
import org.apache.http.HttpStatus;
import org.testng.Assert;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import org.testng.asserts.SoftAssert;

import java.util.List;

public class GetUserTest extends BaseTest {

    private UserClient userClient;
    private UserClient anonymousClient;

    @BeforeClass
    public void setUpClients() {
        // AuthHelper caches tokens per test user — fetching here is cheap and per-class.
        userClient = new UserClient(AuthHelper.getToken(TestUsers.STANDARD));
        anonymousClient = new UserClient("");
    }

    @Test(description = "TC-USER-001")
    public void Should_ReturnAllUsers_When_Authorized() {
        List<UserDto> users = userClient.getAll(HttpStatus.SC_OK);
        Assert.assertFalse(users.isEmpty(), "Expected at least one user.");
    }

    @Test(description = "TC-USER-002")
    public void Should_Return401_When_TokenMissing() {
        Response response = anonymousClient.getAll();
        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_UNAUTHORIZED);
    }

    @Test(description = "TC-USER-003")
    public void Should_ReturnMatchingUser_When_FetchedById() {
        UserDto fromList = userClient.getAll(HttpStatus.SC_OK).getLast();

        UserDto fetched = userClient.getById(String.valueOf(fromList.id()), HttpStatus.SC_OK);

        SoftAssert soft = new SoftAssert();
        soft.assertEquals(fetched.id(), fromList.id());
        soft.assertEquals(fetched.email(), fromList.email());
        soft.assertAll();
    }

    @Test(description = "TC-USER-004")
    public void Should_Return404_When_UserDoesNotExist() {
        Response response = userClient.getById("999999");
        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_NOT_FOUND);
    }
}
```

For create/update flows, track created ids and clean up in `@AfterMethod`:

```java
public class PostUserTest extends BaseTest {

    private UserClient userClient;
    private final List<String> createdIds = new ArrayList<>();

    @BeforeClass
    public void setUpClients() {
        userClient = new UserClient(AuthHelper.getToken(TestUsers.ADMIN));
    }

    @AfterMethod(alwaysRun = true)
    public void cleanUpCreatedUsers() {
        createdIds.forEach(id -> userClient.remove(id));
        createdIds.clear();
    }

    @Test(description = "TC-USER-010")
    public void Should_CreateUser_When_BodyIsValid() {
        // ObjectMother returns a pre-filled builder — see qa/java/skills/test-data-builder.
        UserInDto body = Users.valid().build();

        UserDto created = userClient.create(body, HttpStatus.SC_CREATED);
        createdIds.add(String.valueOf(created.id()));

        SoftAssert soft = new SoftAssert();
        soft.assertEquals(created.email(), body.email());
        soft.assertEquals(created.firstName(), body.firstName());
        soft.assertAll();
    }

    @Test(description = "TC-USER-011")
    public void Should_Return400_When_EmailIsMissing() {
        UserInDto body = Users.valid().email(null).build();

        Response response = userClient.create(body);

        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_BAD_REQUEST);
        ValidationErrorDto error = response.as(ValidationErrorDto.class);
        Assert.assertTrue(error.errors().containsKey("email"), "Expected a validation error on 'email'.");
    }
}
```

## Scenario → pattern matrix

| Scenario | Client overload | Assertion pattern |
|----------|-----------------|-------------------|
| 2xx happy path | **typed** (`int expectedStatus`) | DTO returned already status-asserted; verify fields with `SoftAssert` + `assertAll()` |
| 401 unauthorized | **raw** on a client built with `""` jwt | single `assertEquals(SC_UNAUTHORIZED)` |
| 403 forbidden | **raw** on a client built with a wrong-role token | single `assertEquals(SC_FORBIDDEN)` |
| 404 not found | **raw** | status assert; if the backend returns a `ProblemDetails`-style body, model it via `api-models` and assert the error code |
| 400 validation | **raw** | status assert + `response.as(ValidationErrorDto.class)`; assert the field name in the errors map |
| Malformed JSON / extra-missing property | **raw** via `createRaw(String)` / `Map<String, Object>` overload | status assert only — add these overloads via `api-client-writer` when the plan requires them |

## Generation checks

Two checks bracket the code, both in [`references/generation-checks.md`](references/generation-checks.md):
**oracles first** — a scenario × oracle table (response, data, negative, side effect), taken from the
contract or the requirement and never from the code, before any test is written; and a **hallucination gate**
after — every endpoint (and test id) the new tests use is looked up in the stored OpenAPI spec (and the app
source) and reported `MISSING` instead of guessed.

## Rules

The standards this skill's output must meet are the qa-java rule files, not a list here: `qa-java.md` (core) and `qa-java-api.md`. Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Layout

- Tests go in `apitests/src/test/java/com/{org}/apitests/tests/{api}/{resource}/`; package follows folder.
- One class per operation: `{Operation}{Resource}Test` (`GetUserTest`, `PostUserTest`), extending `BaseTest`. Clients are built in `@BeforeClass` with tokens from `AuthHelper`.
- Error bodies are read in the test with `response.as(ErrorDto.class)`; happy-path DTOs come from the typed overload.
- Request bodies with four or more fields come from `qa/java/skills/test-data-builder`; rows that differ only in data use `qa/java/skills/data-driven-testing`.
- When automating from a test-case document, the TC-ID goes in `@Test(description = "TC-…")` so Allure traces test → case.

## Generation steps

1. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document, or verbal scenarios. From a spec, derive the scenario set per endpoint (happy, 401, 404, 400 validation, boundary). From a test-case document, map one test method per TC-ID.
2. Write the scenario × oracle table (`references/generation-checks.md` §1) — no test code before it exists.
3. For each resource in scope, verify the record DTOs (`models/{api}/{resource}/`) and the `{Resource}Client` exist. Create missing ones via `qa/java/skills/api-models` then `qa/java/skills/api-client-writer` before writing any test.
4. Author one test class per operation, picking patterns from the scenario matrix. Body-manipulation cases (malformed JSON, extra/missing property) require the optional raw/`Map` client overloads — add them via `api-client-writer`.
5. Verify every test name follows `Should_X_When_Y` and asserts one behavior; verify every TC-ID (when given) maps to a test or is explicitly deferred.
6. Run the hallucination gate (`references/generation-checks.md` §2); report every `MISSING` endpoint and write no test against it.
7. Run `./gradlew :apitests:test` — expect 0 failures.

## Handoffs

- DTO scaffolding → `qa/java/skills/api-models`
- Client scaffolding → `qa/java/skills/api-client-writer`
- Test data builders → `qa/java/skills/test-data-builder`
- Parameterized matrices → `qa/java/skills/data-driven-testing`
- Reviewing tests → `qa/java/skills/api-test-author/review`
- Allure reporting setup → `qa/reporting/java/skills/test-reports`
