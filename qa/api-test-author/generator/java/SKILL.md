---
name: qa-api-test-author-generator-java
description: Use when the user asks to scaffold Java API tests using RestAssured + TestNG against a REST backend (reference repo pattern). Triggers: "write a Java API test for X", "add a TestNG test method", "scaffold a `*Action` class for resource Y", "create a POJO for response Z". Do NOT use for UI tests (use `qa/ui-test-author/selenium-java`), for the .NET stack (use `qa/api-test-author/generator/dotnet`), or for non-REST tests.
---

# QA — API Test Writer (Java / RestAssured + TestNG)

Scaffolds Java API tests against a REST backend using the **Action + POJO + Test** layering: thin `*Action` classes wrap RestAssured request building, Jackson POJOs model the bodies, and `*Test` classes own assertions. Mirrors the structure of [`akotrulev/EndavaApi`](https://github.com/akotrulev/EndavaApi).

## Stack

- Java 21
- Gradle (`build.gradle`) — see Endava reference for plugins
- **TestNG** (`org.testng:testng`) — the global default for Java test runners
- **RestAssured** (`io.rest-assured:rest-assured`) for HTTP
- **Jackson** (`jackson-databind` + `jackson-datatype-jsr310`) for (de)serialization
- **Lombok** for POJO boilerplate
- **Allure TestNG** for reporting
- `org.apache.http.HttpStatus` for status code constants

## When to use

- New `*Test.java` class under `src/test/java/<resource>/`
- New `*Action.java` wrapper under `src/main/java/action/` for a new endpoint
- New `*Pojo.java` model under `src/main/java/pojo/`
- Adding test methods for additional scenarios on an existing resource

## When NOT to use

- UI / Selenium tests → `qa/ui-test-author/selenium-java`
- .NET API tests → `qa/api-test-author/generator/dotnet`
- POJO-only scaffolding without a test → `qa/api-dto-writer/java`
- Reviewing existing tests → `qa/api-test-author/reviewer`

## Inputs needed

1. **Resource** (e.g. `User`, `Order`) — PascalCase
2. **Endpoints** in scope — method, path, and required headers/auth
3. **Request body shape** (for POST/PUT) and **response body shape** for each endpoint
4. **Scenarios** — happy path, 401 unauthorized, 404 not found, validation errors

## Three layers

### 1. POJO — `src/main/java/pojo/{Resource}Pojo.java`

Plain data class. Use Lombok + Jackson annotations. Field names in Java are camelCase; map snake_case JSON via `@JsonProperty`.

```java
package pojo;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.ZonedDateTime;

@AllArgsConstructor
@NoArgsConstructor
@Builder
@Data
public class UserPojo {
    private int id;
    private String email;
    @JsonProperty("first_name")
    private String firstName;
    @JsonProperty("last_name")
    private String lastName;
    private String avatar;
    private ZonedDateTime createdAt;
}
```

For wrapped collection responses, add a separate `Get{Resource}sResponsePojo` with a `data` list and metadata fields.

### 2. Action — `src/main/java/action/{Resource}Action.java`

Extends `BaseAction`. One method per endpoint. Always returns `RestAssuredResponseImpl` — never deserializes inside the action. Header / auth handling lives in the constructor.

```java
package action;

import io.restassured.builder.RequestSpecBuilder;
import io.restassured.internal.RestAssuredResponseImpl;
import io.restassured.specification.RequestSpecification;
import pojo.UserPojo;
import utility.SystemPropertyUtil;

import java.util.HashMap;
import java.util.Map;

public class UserAction extends BaseAction {
    private static final String GET_ALL = "/users";
    private static final String GET_BY_ID = "/users/{id}";
    private static final String POST = "/users";
    private static final String DELETE = "/users/{id}";

    private final Map<String, String> headers;

    public UserAction(boolean isAuthenticated) {
        headers = new HashMap<>();
        if (isAuthenticated) {
            headers.put("x-api-key", SystemPropertyUtil.getApiKey());
        }
    }

    public RestAssuredResponseImpl get(int page, int resultsPerPage) {
        RequestSpecification spec = new RequestSpecBuilder()
                .addHeaders(headers)
                .addQueryParam("page", page)
                .addQueryParam("per_page", resultsPerPage)
                .build();
        return super.get(spec, GET_ALL);
    }

    public RestAssuredResponseImpl getById(int id) {
        RequestSpecification spec = new RequestSpecBuilder()
                .addPathParam("id", id)
                .addHeaders(headers)
                .build();
        return super.get(spec, GET_BY_ID);
    }

    public RestAssuredResponseImpl post(UserPojo body) {
        RequestSpecification spec = new RequestSpecBuilder()
                .setBody(body)
                .addHeaders(headers)
                .build();
        return super.post(spec, POST);
    }

    public RestAssuredResponseImpl delete(int id) {
        RequestSpecification spec = new RequestSpecBuilder()
                .addPathParam("id", id)
                .addHeaders(headers)
                .build();
        return super.delete(spec, DELETE);
    }
}
```

### 3. Test — `src/test/java/{resource}/{Scenario}{Resource}Test.java`

Extends `BaseTest`. One test method per scenario. Deserialization happens in the test via `response.as(...)`.

```java
package user;

import action.UserAction;
import base.BaseTest;
import io.restassured.internal.RestAssuredResponseImpl;
import org.apache.http.HttpStatus;
import org.testng.Assert;
import org.testng.annotations.Test;
import org.testng.asserts.SoftAssert;
import pojo.GetAllUsersResponsePojo;
import pojo.GetUserByIdResponsePojo;
import pojo.UserPojo;

import java.util.List;

public class GetUserTest extends BaseTest {

    @Test
    public void cannotGetUserWhenApiKeyIsInvalid() {
        UserAction userAction = new UserAction(false);
        RestAssuredResponseImpl response = userAction.get(1, 12);
        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_UNAUTHORIZED);
    }

    @Test
    public void getAllUsersReturnsOk() {
        UserAction userAction = new UserAction(true);
        RestAssuredResponseImpl response = userAction.get(1, 12);

        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_OK);
        List<UserPojo> users = response.as(GetAllUsersResponsePojo.class).getData();
        Assert.assertFalse(users.isEmpty(), "Expected at least one user in page 1.");
    }

    @Test
    public void getUserByIdMatchesListEntry() {
        UserAction userAction = new UserAction(true);

        RestAssuredResponseImpl listResponse = userAction.get(1, 10);
        Assert.assertEquals(listResponse.getStatusCode(), HttpStatus.SC_OK);
        UserPojo fromList = listResponse.as(GetAllUsersResponsePojo.class).getData().getLast();

        RestAssuredResponseImpl byIdResponse = userAction.getById(fromList.getId());

        SoftAssert soft = new SoftAssert();
        soft.assertEquals(byIdResponse.getStatusCode(), HttpStatus.SC_OK);
        UserPojo fetched = byIdResponse.as(GetUserByIdResponsePojo.class).getData();
        soft.assertEquals(fetched, fromList, "GET /users/{id} must match the entry from GET /users.");
        soft.assertAll();
    }
}
```

## Rules

### Class structure
- POJOs go in `src/main/java/pojo/` and are named `{Resource}Pojo` for entities, `Get{Resource}ResponsePojo` for response envelopes
- Actions go in `src/main/java/action/`, extend `BaseAction`, and are named `{Resource}Action`
- Tests go in `src/test/java/{resource}/`, extend `BaseTest`, and are named `{Action}{Resource}Test` (e.g. `GetUserTest`, `PostUserTest`)

### Action rules
- One `private static final String` per endpoint path at the top of the class — never inline path literals in methods
- Authentication state is decided in the constructor (`new UserAction(true)` / `new UserAction(false)`), not per call
- Methods build a `RequestSpecification` via `RequestSpecBuilder` and delegate to the inherited `super.get/post/put/delete`
- Always return `RestAssuredResponseImpl` — **never** deserialize inside an action; that is the test's job
- Path / query / header / body are added through builder methods (`addPathParam`, `addQueryParam`, `addHeaders`, `setBody`) — no string concatenation

### POJO rules
- `@Data @NoArgsConstructor @AllArgsConstructor @Builder` on every POJO
- Use `@JsonProperty("snake_case")` for any JSON field whose name differs from the Java field
- Use `java.time.ZonedDateTime` / `LocalDate` for timestamps — register `JavaTimeModule` in `BaseTest` (already done in the reference repo)
- No business logic in POJOs — they are pure data

### Test rules
- Test method names describe behavior: `getAllUsersReturnsOk`, `cannotGetUserWhenApiKeyIsInvalid`, `postUserWith{Field}Missing_Returns400`
- Every test must have `@Test`. Add `@Test(groups = "Smoke")` etc. where the project uses test groups.
- Single assertion per test for simple status checks; use `SoftAssert` + `soft.assertAll()` when verifying multiple fields from one response
- Always assert the status code first — never assume a 200 before reading the body
- Use `HttpStatus.SC_OK` / `SC_UNAUTHORIZED` / `SC_NOT_FOUND` / `SC_BAD_REQUEST` constants from `org.apache.http.HttpStatus` — never raw integers
- For deserialization use `response.as(Pojo.class)` — never call `ObjectMapper` directly in a test

### What NOT to do

- No `Thread.sleep` — RestAssured is synchronous; if a backend needs polling, use a helper, not sleeps
- No inter-test dependencies — each `@Test` is self-contained; use `@BeforeMethod` / `@AfterMethod` for per-test setup
- No deserialization inside `*Action` classes — actions return `RestAssuredResponseImpl`, tests call `.as(Pojo.class)`
- No hardcoded base URLs, ports, or API keys — read from `SystemPropertyUtil`
- No `System.out.println` for production assertions — use TestNG `Assert.assertEquals` with a message
- No `JsonNode` / `Map<String,Object>` parsing in tests — model the response with a POJO via `qa/api-dto-writer/java`
- No mixing of `@Test(expectedExceptions = ...)` with assertions on the response — pick one or the other
- No raw integer status codes (`200`, `401`) — use `HttpStatus.SC_*`

## Generation steps

1. Ask: **new resource** (POJO + Action + Test) or **adding a method/scenario to an existing one**?
2. For a new resource: scaffold the POJO via `qa/api-dto-writer/java`, then the Action, then the Test.
3. For each test scenario:
   - **2xx happy path** → status assertion + deserialize → field-by-field check with `SoftAssert`
   - **401 unauthorized** → single `assertEquals(SC_UNAUTHORIZED)` against an action constructed with `isAuthenticated=false`
   - **404 not found** → single `assertEquals(SC_NOT_FOUND)`; if backend returns a `ProblemDetails`-style body, model it as a POJO and assert the error code
   - **400 validation** → status assertion + deserialize the error body; assert the field name in the `errors` map
4. Verify each test name describes behavior, not mechanics (`getAllUsersReturnsOk`, not `testGetAll`).
5. Run `./gradlew test` — expect 0 failures.

## Handoffs

- POJO scaffolding → `qa/api-dto-writer/java`
- Test data builders → `qa/test-data-builder`
- Reviewing tests → `qa/api-test-author/reviewer`
- Allure reporting setup → `qa/allure-reporting`

## Changelog

- 2026-05-27: Authored from the [`akotrulev/EndavaApi`](https://github.com/akotrulev/EndavaApi) reference repo (RestAssured + TestNG + Lombok + Jackson).
