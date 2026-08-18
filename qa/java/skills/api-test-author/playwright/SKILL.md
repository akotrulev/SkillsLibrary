---
name: qa-api-test-playwright-java
description: Use when the user asks to write Java API tests through Playwright's APIRequestContext (playwright-java + TestNG + Jackson) — usually because the project already runs Playwright-Java for UI and wants one dependency and one report. Triggers: "write API tests with Playwright in Java", "use APIRequestContext for endpoint X", "add API coverage to our Playwright Java suite". Plain Java API suites without Playwright → `api-test-author/generator` (RestAssured + TestNG, the stack default).
---

# QA — API Test Writer (Java / Playwright APIRequestContext + TestNG)

Authors `*Test` classes that test a REST backend through **playwright-java's HTTP client** —
`APIRequestContext` — instead of RestAssured. It reuses the **DTO + Client + Test** layering of the RestAssured
sibling (`qa-api-test-writer-java`): record DTOs from `qa/java/skills/api-models`, a
`{Resource}Client` with dual raw + typed overloads, test classes that own scenarios and assertions. Only the
HTTP transport changes; the discipline does not.

> **The discipline this skill encodes** — four ideas that separate a correct Playwright-Java API suite from a
> RestAssured reflex ported onto the wrong client:
>
> 1. **The `APIRequestContext` is the auth boundary, not the call site.** Base URL and the `Authorization`
>    header are set **once, at context creation** (`playwright.request().newContext(new
>    APIRequest.NewContextOptions().setBaseURL(...).setExtraHTTPHeaders(...))`). One context per identity —
>    standard, admin, anonymous — never a token parameter threaded through every call.
> 2. **Contexts and `Playwright` are resources with a lifecycle.** `Playwright.create()` once per class (or
>    suite) in `@BeforeClass`, one context per identity next to it, `ctx.dispose()` for every context and
>    `playwright.close()` in `@AfterClass(alwaysRun = true)`. A leaked context is a leaked driver process.
> 3. **You are here for one dependency and one report.** The value is that a project already running
>    Playwright-Java for UI gets API tests with zero extra HTTP stack, the same TestNG + Allure wiring, and —
>    for cookie-authenticated apps — a **`storageState`** shared between a logged-in browser context and API
>    calls. If the project has no Playwright UI suite, the stack default is RestAssured
>    (`api-test-author/generator`).
> 4. **The layering survives the client swap.** Tests still never touch HTTP directly: `{Resource}Client`
>    wraps the context, the raw overload returns Playwright's `APIResponse` unasserted, the typed overload
>    asserts the **exact** status and Jackson-deserializes `response.text()` into the record DTO. The only
>    signature change from the RestAssured client: the constructor takes an **`APIRequestContext`**, because
>    the context — not a `jwt` string — now carries the identity.

## Stack

- Java 21, Gradle (Kotlin DSL)
- **TestNG** — the global default runner (same as the UI suite)
- **playwright-java** (`com.microsoft.playwright:playwright`) — `APIRequest` / `APIRequestContext` /
  `APIResponse`; no RestAssured dependency in a Playwright-first project
- **Jackson** (`jackson-databind` + `jackson-datatype-jsr310`) with **record DTOs** — deserialization lives in
  the client's typed overloads, never in tests
- **Allure TestNG**; `org.apache.http.HttpStatus` for status constants
- Layout mirrors the RestAssured sibling: `models/{api}/{resource}/`, `clients/{api}/`,
  `tests/{api}/{resource}/`, `base/BaseApiTest.java`

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `models/{api}/{resource}/{Resource}Dto.java` (records) | `qa/java/skills/api-models` | Body shapes, `@JsonProperty` mapping |
| `clients/{api}/{Resource}Client.java` — constructor takes `APIRequestContext` | `qa/java/skills/api-client-writer` conventions, context-based variant | Request building on the context; raw `APIResponse` overload + typed overload (asserts exact status, Jackson-deserializes) |
| `base/BaseApiTest.java` | **this skill** | `Playwright` + per-identity context lifecycle (`@BeforeClass`/`@AfterClass`), `newContext(token)` helper, config via `ConfigurationLoader` |
| `tests/{api}/{resource}/{Operation}{Resource}Test.java` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

If a DTO or client a test needs is missing, run the owner skill first — never call `ctx.get(...)` inline in a
test to avoid creating a client.

## When to use

- The project already runs Playwright-Java for UI and wants API coverage without adding RestAssured
- Hybrid suites where API setup/assertions and UI flows must share one Playwright installation, report, and
  `storageState`
- New `{Operation}{Resource}Test.java` under a Playwright-based API suite, or new scenarios on an existing one

## When NOT to use

- No Playwright in the project → `qa/java/skills/api-test-author/writer` (RestAssured + TestNG, the stack default)
- API calls **inside a UI test** (seed data, then drive the browser) → the UI suite's arrange phase; conventions in `qa/java/skills/ui-test-author/playwright`
- Mocking/intercepting the browser's network traffic (`page.route`) → `qa/java/skills/network-mocking`
- GraphQL / gRPC → the protocol siblings under `qa/java/skills/api-test-author/`
- Reviewing existing tests → `qa/java/skills/api-test-author/review` (cross-stack checklist applies; add this skill's anti-patterns below)

## Base class template — the lifecycle lives here once

```java
package com.{org}.apitests.base;

import com.microsoft.playwright.APIRequest;
import com.microsoft.playwright.APIRequestContext;
import com.microsoft.playwright.Playwright;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public abstract class BaseApiTest {

    protected Playwright playwright;
    private final List<APIRequestContext> createdContexts = new ArrayList<>();

    @BeforeClass(alwaysRun = true)
    public void setUpPlaywright() {
        playwright = Playwright.create();
    }

    /** One context per identity. Empty token → no Authorization header at all. */
    protected APIRequestContext newContext(String token) {
        APIRequest.NewContextOptions options = new APIRequest.NewContextOptions()
                .setBaseURL(ConfigurationLoader.get().apiBaseUrl());
        if (!token.isEmpty()) {
            options.setExtraHTTPHeaders(Map.of("Authorization", "Bearer " + token));
        }
        APIRequestContext context = playwright.request().newContext(options);
        createdContexts.add(context);
        return context;
    }

    @AfterClass(alwaysRun = true)
    public void tearDownPlaywright() {
        createdContexts.forEach(APIRequestContext::dispose);
        createdContexts.clear();
        if (playwright != null) {
            playwright.close();
        }
    }
}
```

## Test class template

```java
package com.{org}.apitests.tests.user.users;

import com.microsoft.playwright.APIResponse;
import com.{org}.apitests.base.BaseApiTest;
import com.{org}.apitests.clients.AuthHelper;
import com.{org}.apitests.clients.user.UserClient;
import com.{org}.apitests.models.user.users.UserDto;
import org.apache.http.HttpStatus;
import org.testng.Assert;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import org.testng.asserts.SoftAssert;

import java.util.List;

public class GetUserTest extends BaseApiTest {

    private UserClient userClient;
    private UserClient anonymousClient;

    @BeforeClass
    public void setUpClients() {
        userClient = new UserClient(newContext(AuthHelper.getToken(TestUsers.STANDARD)));
        anonymousClient = new UserClient(newContext(""));
    }

    @Test(description = "TC-USER-001")
    public void Should_ReturnAllUsers_When_Authorized() {
        List<UserDto> users = userClient.getAll(HttpStatus.SC_OK);
        Assert.assertFalse(users.isEmpty(), "Expected at least one user.");
    }

    @Test(description = "TC-USER-002")
    public void Should_Return401_When_TokenMissing() {
        APIResponse response = anonymousClient.getAll();
        Assert.assertEquals(response.status(), HttpStatus.SC_UNAUTHORIZED);
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
        APIResponse response = userClient.getById("999999");
        Assert.assertEquals(response.status(), HttpStatus.SC_NOT_FOUND);
    }
}
```

Create/update flows keep the RestAssured sibling's cleanup discipline: track created ids, delete them in
`@AfterMethod(alwaysRun = true)`, error bodies deserialized in the test via the client's
`problem(APIResponse)` helper (Jackson behind the scenes — never `new ObjectMapper()` in a test).

## Scenario → pattern matrix

| Scenario | Client overload / identity | Assertion pattern |
|----------|----------------------------|-------------------|
| 2xx happy path | **typed** (`int expectedStatus`) on the standard/admin context | DTO returned already status-asserted; verify fields with `SoftAssert` + `assertAll()` |
| 401 unauthorized | **raw** on the `newContext("")` client | single `assertEquals(response.status(), SC_UNAUTHORIZED)` |
| 403 forbidden | **raw** on a wrong-role context | single `assertEquals(SC_FORBIDDEN)` |
| 404 not found | **raw** | status assert; deserialize the `ProblemDetails`-style body via the client helper and assert the error code |
| 400 validation | **raw** | status assert + error DTO; assert the field name in the errors map |
| Malformed JSON / extra-missing property | **raw** via `createRaw(String)` / `Map<String, Object>` overload | status assert only — add these overloads following `api-client-writer` when the plan requires them |
| Eventually-consistent state | **raw/typed** inside an Awaitility `await().untilAsserted(...)` | poll on the condition, never `Thread.sleep` |

## Rules

### Class structure & naming

- Same as the RestAssured sibling: one class per operation (`{Operation}{Resource}Test`), package follows
  folder, `Should_X_When_Y` method names, TC-ID in `@Test(description = "TC-…")`.
- Every class extends `BaseApiTest`; clients are built in `@BeforeClass` from `newContext(token)` with tokens
  from `AuthHelper`. Never create a `Playwright` or a context inside a test method.
- Identities are contexts: one client field per identity (`userClient`, `adminClient`, `anonymousClient`) —
  never a token argument on a call, never a shared mutable client rebuilt mid-test.

### Test rules

- Assert the **exact** status code, always, before reading the body — `response.status()`, never
  `response.ok()` (it passes on any 2xx). Never rely on Playwright throwing for you.
- Happy path uses the **typed** overload; negative scenarios use the **raw** `APIResponse` overload. Never
  re-assert the status after a typed call.
- `HttpStatus.SC_*` constants — never raw integers. `SoftAssert` + `assertAll()` for multi-field checks.
- Request bodies with 4+ fields come from builders (`qa/java/skills/test-data-builder`); JSON bodies are passed
  as DTOs via `RequestOptions.create().setData(dto)` inside the client — never hand-built JSON strings in tests.
- Tests are independent: per-test data, `@AfterMethod(alwaysRun = true)` cleanup, no `dependsOnMethods`.
- Rows that differ only in data → `@DataProvider` (`qa/java/skills/data-driven-testing`).

### What NOT to do

- No `ctx.get(...)` / `playwright.request()` calls in tests — every request goes through a `{Resource}Client`.
- No RestAssured *and* Playwright HTTP in one suite — one client stack; if RestAssured is already established,
  stay on the generator sibling.
- No token threading per call — identity lives in the context (`setExtraHTTPHeaders` at creation), or in a
  `storageState` file shared with the UI suite for cookie-auth apps (`APIRequest.NewContextOptions.setStorageStatePath`).
- No leaked resources — every context disposed, `playwright.close()` in `@AfterClass(alwaysRun = true)`.
- No `response.ok()` as the status assertion; no `Thread.sleep`.
- No `ObjectMapper` in test code — deserialization lives in the client's typed overloads and error helper.
- No hardcoded base URLs, credentials, or tokens — `ConfigurationLoader` + `AuthHelper`.

## Generation steps

1. Confirm the project uses playwright-java (the `com.microsoft.playwright:playwright` dependency). If not,
   stop and route to `api-test-author/generator` — say why.
2. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document (one test method per TC-ID), or
   verbal scenarios.
3. Ensure `BaseApiTest` exists with the `Playwright`/context lifecycle above; create it if missing.
4. For each resource in scope, verify the record DTOs and the context-based `{Resource}Client` exist — create
   missing ones via `api-models`, then the client following `api-client-writer` conventions with the
   `(APIRequestContext)` constructor.
5. Author one test class per operation from the scenario matrix, one client field per identity in `@BeforeClass`.
6. Verify every test name follows `Should_X_When_Y` and every TC-ID maps to a test or is explicitly deferred.
7. Run `./gradlew :apitests:test` — expect 0 failures.

## Cross-references

- `qa-api-test-writer-java` — the **stack default** (RestAssured + TestNG); this skill is the variant
  for Playwright-first projects. Shared spine: DTO + Client + Test, dual raw/typed overloads, cleanup discipline.
- `qa-api-test-playwright-typescript` · `qa-api-test-playwright-dotnet` — the sibling stacks
  (@playwright/test `request` fixture · Microsoft.Playwright + NUnit); same four ideas, different bindings.
- `qa-api-models-java` / `qa-api-client-writer-java` — DTOs / the client layer this skill consumes.
- `qa-ui-test-writer-playwright-java` — the UI suite this skill shares the Playwright dependency with.
- `qa-network-mocking-java` — `page.route` mocking/asserting of browser traffic (not API testing).
- `qa-api-test-review-java` — review; its cross-stack checklist applies verbatim, plus this skill's
  What-NOT-to-do list as Playwright-specific findings.
- `qa-test-login-tokens-java` — the tokens `newContext(token)` injects.
- `qa-test-reports-java` — Allure TestNG wiring shared with the UI suite.
