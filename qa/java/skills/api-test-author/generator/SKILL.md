---
name: qa-api-test-author-generator-java
description: Use when the user asks to write Java API tests using RestAssured + TestNG against a REST backend. Triggers: "write a Java API test for X", "add a TestNG test method", "automate these test cases in Java".
---

# QA — API Test Writer (Java / RestAssured + TestNG)

Authors `*Test` classes on top of the **DTO + Client + Test** layering: record DTOs (from `qa/java/skills/api-dto-writer`), `{Resource}Client` classes with dual raw + typed overloads (from `qa/java/skills/api-client-writer`), and test classes — written by this skill — that own scenario selection, test data, and assertions.

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
| `models/{api}/{resource}/{Resource}Dto.java` (records) | `qa/java/skills/api-dto-writer` | Body shapes, `@JsonProperty` mapping |
| `clients/{api}/{Resource}Client.java` | `qa/java/skills/api-client-writer` | Request building; raw `Response` overload + typed overload (asserts status, deserializes) |
| `tests/{api}/{resource}/{Operation}{Resource}Test.java` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

This skill writes **only the test classes**. If a DTO or client a test needs is missing, run the owner skill first — never hand-roll HTTP calls or inline `RestAssured.given()` to avoid creating a client.

## When to use

- New `{Operation}{Resource}Test.java` class for an endpoint that has (or will get) a client
- Adding test methods for additional scenarios on an existing resource
- Automating cases from a `qa/manual/test-case-writer` document or an OpenAPI/Swagger spec

## When NOT to use

- UI / Selenium tests → `qa/java/skills/ui-test-author/selenium`
- .NET API tests → `qa/dotnet/skills/api-test-author/generator`
- DTO-only scaffolding → `qa/java/skills/api-dto-writer`
- Client-only scaffolding → `qa/java/skills/api-client-writer`
- Reviewing existing tests → `qa/java/skills/api-test-author/reviewer`

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
| 404 not found | **raw** | status assert; if the backend returns a `ProblemDetails`-style body, model it via `api-dto-writer` and assert the error code |
| 400 validation | **raw** | status assert + `response.as(ValidationErrorDto.class)`; assert the field name in the errors map |
| Malformed JSON / extra-missing property | **raw** via `createRaw(String)` / `Map<String, Object>` overload | status assert only — add these overloads via `api-client-writer` when the plan requires them |

## Rules

### Class structure & naming

- Tests go in `apitests/src/test/java/com/{org}/apitests/tests/{api}/{resource}/`; package follows folder.
- One class per operation: `{Operation}{Resource}Test` (e.g. `GetUserTest`, `PostUserTest`, `DeleteUserTest`).
- Every class extends `BaseTest`. Clients are built in `@BeforeClass` with tokens from `AuthHelper`; never fetch tokens inside a test method or a client.
- Test method names follow `Should_X_When_Y` (global rule): `Should_Return401_When_TokenMissing`, not `testGetAllUnauthorized`.
- When automating from a test-case document, put the TC-ID in `@Test(description = "TC-…")` so Allure traces test → case.

### Test rules

- Always assert the status code before reading the body — the typed overload does this for you; raw responses get an explicit `assertEquals` first.
- Happy path uses the **typed** client overload; negative scenarios use the **raw** overload. Never re-assert the status after a typed call.
- One logical assertion per test. Use `SoftAssert` + `soft.assertAll()` when verifying multiple fields of one response; never multiple unrelated behaviors.
- Use `HttpStatus.SC_*` constants — never raw integers.
- Error bodies are deserialized in the test via `response.as(ErrorDto.class)`; happy-path DTOs come from the typed overload. Never call `ObjectMapper` directly.
- Request bodies with 4+ fields come from builders (`qa/java/skills/test-data-builder`); simpler bodies use the record's canonical constructor.
- Tests are independent: per-test data setup, `@AfterMethod(alwaysRun = true)` cleanup of created entities, no execution-order assumptions.
- Rows that differ only in data → parameterize via `@DataProvider` (`qa/java/skills/data-driven-testing`), not copy-pasted methods.

### What NOT to do

- No `RestAssured.given()` in tests — every request goes through a `{Resource}Client`. Missing client → `api-client-writer` first.
- No deserialization helpers in tests beyond `response.as(...)` for error bodies — no `JsonNode`, no `Map<String, Object>` response parsing; model the shape via `api-dto-writer`.
- No `Thread.sleep` — if a backend needs polling, use an explicit-wait helper on a condition.
- No inter-test dependencies (`dependsOnMethods`, shared mutable state between tests).
- No hardcoded base URLs, credentials, or tokens — configuration via `ConfigurationLoader`, tokens via `AuthHelper`.
- No conditional logic (`if`/`for`) driving assertions — use `@DataProvider`.
- No raw integer status codes.
- No `@Test(expectedExceptions = ...)` mixed with response assertions — pick one.

## Generation steps

1. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document, or verbal scenarios. From a spec, derive the scenario set per endpoint (happy, 401, 404, 400 validation, boundary). From a test-case document, map one test method per TC-ID.
2. For each resource in scope, verify the record DTOs (`models/{api}/{resource}/`) and the `{Resource}Client` exist. Create missing ones via `qa/java/skills/api-dto-writer` then `qa/java/skills/api-client-writer` before writing any test.
3. Author one test class per operation, picking patterns from the scenario matrix. Body-manipulation cases (malformed JSON, extra/missing property) require the optional raw/`Map` client overloads — add them via `api-client-writer`.
4. Verify every test name follows `Should_X_When_Y` and asserts one behavior; verify every TC-ID (when given) maps to a test or is explicitly deferred.
5. Run `./gradlew :apitests:test` — expect 0 failures.

## Handoffs

- DTO scaffolding → `qa/java/skills/api-dto-writer`
- Client scaffolding → `qa/java/skills/api-client-writer`
- Test data builders → `qa/java/skills/test-data-builder`
- Parameterized matrices → `qa/java/skills/data-driven-testing`
- Reviewing tests → `qa/java/skills/api-test-author/reviewer`
- Allure reporting setup → `qa/java/skills/allure-reporting`
