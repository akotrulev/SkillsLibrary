---
paths:
  - "**/{apitests,api-tests}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/{clients,models}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/*{Client,Dto}.java"
---

<!-- qa-java rules v1 (2026-11-03): API tests. Installed by /qa-java:rules; edit the paths above to where this project keeps its API clients, DTOs and API tests. -->

# Java API test standards (RestAssured / Playwright APIRequestContext)

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Every request goes through a typed `{Resource}Client` on the project's base client. No `RestAssured.given()`, `RestAssured.baseURI = …` or raw `APIRequestContext` call in a test; one HTTP stack per suite. *major*
- Dual overloads: the raw one returns the response, unasserted and undeserialized; the typed one takes the expected status, asserts it, deserializes and delegates to the raw one. Happy paths use the typed overload, negative tests the raw one; never re-assert after a typed call. *major*
- A client takes its token in the constructor (`""` when anonymous), declares paths as `private static final` `SCREAMING_SNAKE_CASE` constants, takes typed DTO bodies, and holds no state, lifecycle annotation or `try`/`catch`. *major; minor for constants*
- Assert the exact status first, with a named constant (`HttpStatus.SC_*`); never `ok()`, `isOK()` or "any 2xx". *major; minor for a raw int*
- An error response is asserted beyond its status through a modeled `ErrorDto`; a 401 with no body is not deserialized. *major*
- A happy path checks more than one field; a create is read back. *major*
- DTOs are records with `@JsonProperty` on every component, no behaviour; boxed types on `*ModDto`; `BigDecimal` for money; `OffsetDateTime` with `JavaTimeModule` registered once. No Lombok `@Data` DTO. *major*
- No `Map<String, Object>`, `JsonNode`, `jsonPath().get(...)` or `ObjectMapper` in a test. *major*
- A deserialization failure attaches the raw body first, then fails naming the JSON path, target type and payload, from one helper; never a skip. *major*
- The HTTP exchange reaches Allure through the client's filter, not hand-attached bodies. *minor*
