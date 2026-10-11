---
name: api-client-writer
description: Use when the user asks to create a new API client class (`{Resource}Client.java`) in a Java API test project (RestAssured + TestNG + Gradle, Java 21). Triggers: "write an API client for X", "add a {Resource}Client", "scaffold the Java client for /api/{path}". Do NOT use for DTOs (`qa-java:api-models`) or the tests themselves (`qa-java:api-tests`).
---

# qa-java:api-client-writer

Generator skill. Scaffolds a single `{Resource}Client.java` file in the Java API test project under `src/test/java/.../clients/{api}/`, following the conventions below.

## When to use

- The user asks to add a new client class under `clients/{api}/`.
- A new endpoint group has been added to the API under test and needs a typed wrapper for tests to call.
- The user is extending an existing client with new endpoints in the same style.

## When NOT to use

- Writing the test fixture / `@Test` methods — use `qa/java/skills/api-test-author/writer`.
- Reviewing an existing client for convention drift — use `qa/java/skills/api-test-author/review`.
- Authoring DTOs the client returns — use `qa/java/skills/api-models` first.
- Reacting to a **new version of a swagger/OpenAPI spec** — start at `qa/_shared/api-spec-assets` (`qa-<stack>:api-spec-assets`): it replaces the stored spec asset in place and derives from `git diff` exactly which client methods changed. Come back here for those methods only.
- .NET stack (RestSharp) — use `qa/dotnet/skills/api-client-writer`.
- TypeScript stack (`fetch` + Zod) — use `qa/typescript/skills/api-client-writer`.
- Any non-RestAssured / non-Java stack not covered by the siblings above.

## Folder & naming convention

Clients are organized by API group. **One client per resource**; user-facing and admin operations live in the same class.

```
src/test/java/com/{org}/apitests/
├── clients/
│   ├── BaseApiClient.java
│   ├── AuthHelper.java
│   ├── AuthConfigClient.java         ← root, no auth required
│   └── {api}/
│       └── {Resource}Client.java     ← one file per resource
├── config/
│   └── ConfigurationLoader.java
└── models/
    └── {api}/
        └── {resource}/
            └── {Resource}Dto.java
```

### API group reference

| API Group  | Clients                                                          |
|------------|------------------------------------------------------------------|
| user       | UserClient, KycClient, ConsentClient, PreferencesClient          |
| assessment | AssessmentClient                                                 |
| legal      | DocumentClient                                                   |
| reference  | ReferenceClient                                                  |
| auth       | AuthConfigClient (root package, unauthenticated)                 |

When a resource has both user-facing (`/api/{resource}/...`) and admin (`/api/management/{resource}/...`) endpoints, both live in the same client. Distinguish them via the path constants (e.g. `GET_ALL_PATH` vs `GET_ALL_MANAGEMENT_PATH`).

## Dual-method pattern

Every endpoint that returns a DTO gets **two overloads**:

1. **Raw** — returns `Response` (RestAssured). No assertion, no deserialization. Used in negative tests where the caller inspects the status code.
2. **Typed** — same signature plus a trailing `int expectedStatus` parameter. Calls the raw overload, asserts the status with TestNG, and returns the deserialized DTO. Used for happy-path convenience.

```java
// Raw — caller handles assertion and deserialization.
public Response getById(String id) {
    return execute(spec()
        .pathParam("id", id)
        .get(GET_BY_ID_PATH));
}

// Typed — asserts status, returns deserialized DTO.
public {Resource}Dto getById(String id, int expectedStatus) {
    Response response = getById(id);
    assertEquals(response.statusCode(), expectedStatus);
    return deserialize(response, {Resource}Dto.class);
}
```

For collection responses, deserialize into a list:

```java
public Response getAll() {
    return execute(spec().get(GET_ALL_PATH));
}

public List<{Resource}Dto> getAll(int expectedStatus) {
    Response response = getAll();
    assertEquals(response.statusCode(), expectedStatus);
    return deserializeList(response, {Resource}Dto.class);
}
```

Endpoints with **no response body** (DELETE → 204, PATCH → 204) get only the raw method.

## Template

```java
package com.{org}.apitests.clients.{api};

import com.{org}.apitests.clients.BaseApiClient;
import com.{org}.apitests.config.ConfigurationLoader;
import com.{org}.apitests.models.{api}.{resource}.{Resource}Dto;
import com.{org}.apitests.models.{api}.{resource}.{Resource}InDto;
import com.{org}.apitests.models.{api}.{resource}.{Resource}ModDto;
import io.restassured.response.Response;

import java.util.List;

import static org.testng.Assert.assertEquals;

public class {Resource}Client extends BaseApiClient {

    // User-facing endpoints
    private static final String GET_ALL_PATH      = "/api/{basePath}";
    private static final String GET_BY_ID_PATH    = "/api/{basePath}/{id}";
    private static final String POST_PATH         = "/api/{basePath}";

    // Management endpoints (only when this resource exposes admin operations)
    private static final String GET_ALL_MANAGEMENT_PATH = "/api/management/{basePath}";
    private static final String PUT_MANAGEMENT_PATH     = "/api/management/{basePath}/{id}";
    private static final String PATCH_MANAGEMENT_PATH   = "/api/management/{basePath}/{id}";
    private static final String DELETE_MANAGEMENT_PATH  = "/api/management/{basePath}/{id}";

    public {Resource}Client(String jwt) {
        super(ConfigurationLoader.getTestEnvironment().apiUri(), jwt);
    }

    // Returns all {resource}s (user-facing).
    public Response getAll() {
        return execute(spec().get(GET_ALL_PATH));
    }

    public List<{Resource}Dto> getAll(int expectedStatus) {
        Response response = getAll();
        assertEquals(response.statusCode(), expectedStatus);
        return deserializeList(response, {Resource}Dto.class);
    }

    // Returns a single {resource} by id.
    public Response getById(String id) {
        return execute(spec()
            .pathParam("id", id)
            .get(GET_BY_ID_PATH));
    }

    public {Resource}Dto getById(String id, int expectedStatus) {
        Response response = getById(id);
        assertEquals(response.statusCode(), expectedStatus);
        return deserialize(response, {Resource}Dto.class);
    }

    // Creates a new {resource}.
    public Response create({Resource}InDto body) {
        return execute(spec()
            .contentType("application/json")
            .body(body)
            .post(POST_PATH));
    }

    public {Resource}Dto create({Resource}InDto body, int expectedStatus) {
        Response response = create(body);
        assertEquals(response.statusCode(), expectedStatus);
        return deserialize(response, {Resource}Dto.class);
    }

    // --- Management operations (only if applicable) ---

    public Response getAllManagement() {
        return execute(spec().get(GET_ALL_MANAGEMENT_PATH));
    }

    public List<{Resource}Dto> getAllManagement(int expectedStatus) {
        Response response = getAllManagement();
        assertEquals(response.statusCode(), expectedStatus);
        return deserializeList(response, {Resource}Dto.class);
    }

    // Replaces the {resource} with the given id.
    public Response update(String id, {Resource}InDto body) {
        return execute(spec()
            .pathParam("id", id)
            .contentType("application/json")
            .body(body)
            .put(PUT_MANAGEMENT_PATH));
    }

    // Partially updates the {resource} with the given id.
    public Response patchById(String id, {Resource}ModDto body) {
        return execute(spec()
            .pathParam("id", id)
            .contentType("application/json")
            .body(body)
            .patch(PATCH_MANAGEMENT_PATH));
    }

    // Deletes the {resource} with the given id.
    public Response remove(String id) {
        return execute(spec()
            .pathParam("id", id)
            .delete(DELETE_MANAGEMENT_PATH));
    }
}
```

Omit any block that does not apply — a read-only reference client has no `create`/`update`/`remove`; a public-only resource has no management section.

### Requests with query parameters

```java
// Returns a paginated list of {resource}s.
public Response getAll(int page, int resultsPerPage) {
    return execute(spec()
        .queryParam("page", page)
        .queryParam("per_page", resultsPerPage)
        .get(GET_ALL_PATH));
}
```

## Rules

### Class structure

- Class name: `{Resource}Client` — PascalCase resource noun + `Client`. **No `P`/`M` suffix.**
- Always extend `BaseApiClient` (never use `RestAssured.given()` directly inside the class — go through inherited `spec()` / `execute()`).
- Package follows folder: `com.{org}.apitests.clients.{api}` (or root `com.{org}.apitests.clients` for `AuthConfigClient`).
- Imports: `BaseApiClient`, `ConfigurationLoader`, the resource's DTOs, `io.restassured.response.Response`, `java.util.List`, and `org.testng.Assert.assertEquals`. No other imports unless strictly required.

### Constructor

- Constructor takes a single `String jwt`.
- Always calls `super(ConfigurationLoader.getTestEnvironment().apiUri(), jwt)` — `BaseApiClient` is responsible for building the `RequestSpecification` with base URI and Authorization header.
- Pass `""` (empty string) for unauthenticated clients (`AuthConfigClient`) — `BaseApiClient` must skip the header when blank.
- Never call `AuthHelper.getToken(...)` inside the client — the test fetches the token and passes it in.
- Never hardcode a URI string or credentials.

### Path constants

- One `private static final String` per distinct path pattern at the top of the class, in `SCREAMING_SNAKE_CASE`.
- Name after purpose: `GET_ALL_PATH`, `GET_BY_ID_PATH`, `POST_PATH`, `DELETE_PATH`, etc.
- For resources with both user-facing and admin endpoints, suffix the management variants: `GET_ALL_MANAGEMENT_PATH`, `PUT_MANAGEMENT_PATH`, etc.
- User-facing paths start with `/api/`; admin paths start with `/api/management/`.

### Method signatures

- Every endpoint that returns a DTO gets two overloads: raw `Response` + typed (`int expectedStatus`, asserts, returns DTO).
- Endpoints with no response body get only the raw overload.
- The typed overload calls the raw overload — do not duplicate request-building logic.
- Use inherited `spec()` to obtain the `RequestSpecification` and call `execute(...)` for logging + base behavior.
- Use `.pathParam("name", value)` for path placeholders, `.queryParam(...)` for query strings, `.body(dto)` for JSON bodies.
- Body parameters are strongly-typed DTOs (e.g. `{Resource}InDto body`), not `Object`.
- One-line comment on the raw method only; not repeated on the typed overload.
- Deserialization uses inherited `deserialize(response, Class<T>)` and `deserializeList(response, Class<T>)` — never call `objectMapper.readValue` directly.

### Method naming

| Operation             | Method name                                |
|-----------------------|--------------------------------------------|
| Fetch collection      | `getAll()`                                 |
| Fetch admin collection| `getAllManagement()`                       |
| Fetch by id           | `getById(String id)`                       |
| Fetch by other key    | `getBy{Key}({Type} key)`                   |
| Create                | `create({Resource}InDto body)`             |
| Full replace          | `update(String id, {Resource}InDto body)`  |
| Partial update        | `patchById(String id, {Resource}ModDto body)` |
| Delete                | `remove(String id)`                        |

### Raw body and Object overloads (body manipulation tests only)

When the test plan includes **malformed JSON** scenarios:

```java
// Sends a raw string body (for malformed JSON testing).
public Response createRaw(String rawJson) {
    return execute(spec()
        .contentType("application/json")
        .body(rawJson)
        .post(POST_PATH));
}
```

When the test plan includes **extra/missing property** scenarios:

```java
// Accepts a pre-built body (e.g. a Map from JsonBodyHelper) for body manipulation tests.
public Response create(Map<String, Object> body) {
    return execute(spec()
        .contentType("application/json")
        .body(body)
        .post(POST_PATH));
}
```

Only add these overloads when the test plan requires them — not by default.

### What NOT to do

- No `Thread.sleep()` or manual delays.
- No `RestAssured.given()` directly — always go through inherited `spec()` so base URI, auth header, and logging filter are applied.
- No `RestAssured.baseURI = ...` mutation; do not touch the static config.
- No hardcoded base URLs or credentials.
- No try/catch around HTTP calls — `BaseApiClient`'s logging filter handles failure reporting.
- No `Object` body parameters on the default overloads — always strongly-typed DTOs.
- Do not deserialize inside raw `Response` methods — only in typed overloads.
- No `P`/`M` class-name suffix; no `public/` or `management/` subpackages.
- No static mutable state on the client.
- No `@BeforeClass` / `@BeforeMethod` lifecycle inside the client — clients are pure helpers, not test fixtures.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource + base path segment from the paths, operations from the methods defined) — do not ask.
1. Ask the user: which **API group** does this client belong to? (user / assessment / legal / reference / auth)
2. Ask the user: resource name (noun) and base URL path segment (e.g. `users`).
3. Ask which **operations** are needed, and whether they are user-facing, admin, or both. Default to full CRUD on the user-facing surface.
4. Ensure the required DTOs exist under `models/{api}/{resource}/`. If not, run `qa/java/skills/api-models` first.
5. Generate the file at `src/test/java/com/{org}/apitests/clients/{api}/{Resource}Client.java`.
6. Run `./gradlew :apitests:compileTestJava` — expect 0 errors. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
