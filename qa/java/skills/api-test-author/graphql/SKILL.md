---
name: qa-api-test-author-graphql-java
description: Scaffold black-box **GraphQL** API tests in Java 21 with RestAssured + TestNG and Jackson. Triggers: "write a Java GraphQL test for query/mutation X", "assert the errors array on a GraphQL response", "test partial GraphQL data + errors".
---

# QA — GraphQL API Test Writer (Java 21 / RestAssured + TestNG + Jackson)

> **Ported from the canonical `qa-api-test-author-graphql-typescript`.** The four ideas and the section order
> are identical; only the runner (TestNG instead of Vitest), the HTTP client (RestAssured instead of `fetch`),
> and the typing (Jackson POJOs + AssertJ/TestNG assertions instead of Zod `parse`) change. See the TypeScript
> file for the family rationale.

Scaffolds black-box API tests in Java against a deployed **GraphQL** backend. It reuses the **Action + POJO +
Test** layering of the REST sibling (`qa-api-test-author-generator-java`) but adapts every layer to the one fact
that makes GraphQL testing its own discipline: **a GraphQL response is one HTTP 200 carrying a `{ data, errors }`
envelope, and the assertion lives in that envelope, not in `response.getStatusCode()`.**

> **The discipline this skill encodes** — four ideas that separate a correct GraphQL test from a REST reflex:
>
> 1. **Status is (almost) always 200 — assert on the body's `errors`, not the status code.** A GraphQL error
>    surfaces as `{ "errors": [...] }` in a `200 OK` body. `assertEquals(getStatusCode(), SC_BAD_REQUEST)` is the
>    REST habit and it is **wrong here**. The action returns the raw `{ data, errors }` envelope and **never
>    throws** on a GraphQL error; the test decides whether errors were expected. (Transport failures — malformed
>    body, auth middleware rejecting before resolving — *can* be non-200; assert those too, but they're the
>    exception.)
> 2. **`data` and `errors` coexist — assert the whole envelope, both branches.** **Partial success** is a
>    first-class GraphQL outcome: some fields resolve into `data` while a failing field is `null` with an entry
>    in `errors[]` whose `path` names it. A real test asserts **both** — the fields that resolved *and* the error
>    (its `path`, its `extensions.code`).
> 3. **The response is query-shaped — model the typed `data` per operation.** You get back **exactly the fields
>    you selected**. So a `*Data` POJO models the *operation's selection set*, not a whole resource. Model the
>    `errors[]` envelope once and reuse it.
> 4. **Pick the operation type deliberately.** A **query** asserts shape + values. A **mutation** asserts the
>    returned payload **and round-trips a read** to prove the change persisted. A **subscription** is a
>    long-lived stream over WebSocket (`graphql-ws`) — that's `qa-websocket-sse-testing-java`; cross-link, don't
>    reimplement.

## Decision matrix — operation type → test shape

| Operation | What you're proving | Test shape |
|-----------|---------------------|------------|
| **Query** (read) | The right fields resolve with the right values | `POST { query, variables }` → assert `errors` null/empty → field checks on `data` |
| **Query — not found / forbidden** | A failure surfaces correctly | status **200** → assert `errors` non-empty → `errors[0].extensions.code` (`NOT_FOUND`/`FORBIDDEN`) + `data.<field>` is `null` |
| **Query — partial** | Partial success is handled | one resolved field asserted on `data` **and** the failing field's `errors[]` entry asserted by `path` |
| **Mutation** (write) | The change happened and persisted | assert the mutation payload → **round-trip a query** → assert the new state is readable |
| **Mutation — input validation** | Bad input rejected cleanly | `errors` non-empty with `extensions.code == "BAD_USER_INPUT"`; `data.<field>` null |
| **Subscription** (stream) | Server pushes events over time | **not this skill** → `qa-websocket-sse-testing-java` |
| **Introspection** | Schema exposes the expected types/fields | query `__schema`/`__type` → assert presence; in prod assert introspection **disabled** |
| **Persisted queries (APQ)** | Only registered hashes execute | hash-only → `PERSISTED_QUERY_NOT_FOUND` → register (query+hash) → hash-only now resolves |

## Stack

- Java 21, Gradle (Kotlin DSL)
- **TestNG** (`org.testng:testng`) — the global default Java runner
- **RestAssured** (`io.rest-assured:rest-assured`) — a GraphQL request is a `POST` of `{ query, variables }`
- **Jackson** (`jackson-databind` + `jackson-datatype-jsr310`) for (de)serialization
- **AssertJ** (`assertThat(...)`) for fluent assertions; **Allure TestNG** for reporting
- `org.apache.http.HttpStatus` for status constants; secrets via `SystemPropertyUtil` / env, never hardcoded
- Project layout: `src/main/java/operation/`, `src/main/java/action/`, `src/main/java/pojo/`,
  `src/test/java/<resource>/`

> **Why RestAssured `.post(...).as(...)` and not a typed GraphQL client?** Java GraphQL clients (e.g. the
> Netflix DGS client, Apollo Kotlin) **throw when the response contains `errors`**, which makes the *error path*
> (idea #2) awkward to assert. A black-box test needs the **raw envelope**, errors and all. So the canonical
> action POSTs the request via RestAssured and deserializes the full `{ data, errors }` envelope into a POJO —
> it never throws on a GraphQL error.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Three layers**.

## Partial response — `data` and `errors` together (idea #2)

A query selecting several fields can **partially succeed**: the authorized fields resolve, a forbidden/erroring
field comes back `null` with an `errors[]` entry pointing at its `path`. Assert **both halves**.

```java
public static final String GET_USER_WITH_BILLING = """
    query GetUserWithBilling($id: ID!) {
      user(id: $id) { id email }
      billingProfile(userId: $id) { plan balanceCents }   # requires elevated scope
    }
    """;

@Test
public void getUserWithBillingWhenForbiddenFieldResolvesUserAndErrorsOnBilling() {
    GraphQLResponse<UserWithBillingData> response = billingAction.getUserWithBilling("1");

    // half 1: the field that DID resolve
    assertThat(response.getData().getUser().getEmail()).isEqualTo("george.bluth@example.com");
    assertThat(response.getData().getBillingProfile()).isNull();        // forbidden field is null in data

    // half 2: the error that names the field that did NOT resolve
    assertThat(response.getErrors().get(0).getPath()).containsExactly("billingProfile");
    assertThat(response.getErrors().get(0).getExtensions().getCode()).isEqualTo("FORBIDDEN");
}
```

> Asserting only `data` would pass while the user silently lost their billing data; asserting only `errors` would
> miss that the rest of the query still worked. Partial success demands both.

## Mutation — assert the payload, then round-trip the read (idea #4)

A mutation returns a payload, but the payload alone doesn't prove the write **persisted**. Assert the returned
object, then query it back. Clean up created data in `@AfterMethod` (wrapped so a cleanup failure never masks a
test failure).

```java
@Test
public void createUserWhenValidPersistsAndIsReadable() {
    UserGraphQLAction userAction = new UserGraphQLAction(true);

    GraphQLResponse<CreateUserData> created =
        userAction.createUser(new CreateUserInput("neo@example.com", "Thomas", "Anderson"));

    assertThat(created.getErrors()).isNull();
    assertThat(created.getData().getCreateUser().getEmail()).isEqualTo("neo@example.com");

    // round-trip: prove it persisted, don't trust the mutation's own echo
    GraphQLResponse<GetUserData> fetched = userAction.getUser(created.getData().getCreateUser().getId());
    assertThat(fetched.getData().getUser().getEmail()).isEqualTo("neo@example.com");
}

@Test
public void createUserWhenEmailEmptyReturnsBadUserInput() {
    UserGraphQLAction userAction = new UserGraphQLAction(true);

    GraphQLResponse<CreateUserData> response =
        userAction.createUser(new CreateUserInput("", "A", "B"));

    assertThat(response.getErrors()).isNotEmpty();
    assertThat(response.getErrors().get(0).getExtensions().getCode()).isEqualTo("BAD_USER_INPUT");
    assertThat(response.getData() == null ? null : response.getData().getCreateUser()).isNull();
}
```

## Introspection — assert the schema contract, and that prod disables it

A single introspection query returns the schema's type system. Use it to assert a type/field exists — and, in a
production-config check, to assert introspection is **turned off** (a common hardening requirement).

```java
public static final String TYPE_INTROSPECTION = """
    query { __type(name: "User") { name fields { name } } }
    """;

@Test
public void introspectionExposesEmailFieldOnUserType() {
    GraphQLResponse<IntrospectionData> response = schemaAction.introspectType("User");

    assertThat(response.getData().getType().getFields())
        .extracting("name")
        .contains("email");
}

@Test
public void introspectionIsDisabledInProduction() {
    GraphQLResponse<IntrospectionData> response = prodSchemaAction.introspectType("User");

    assertThat(response.getData().getType()).isNull();   // hardened server returns null __type
    assertThat(response.getErrors()).isNotEmpty();
}
```

> Jackson maps the JSON `__type` field via `@JsonProperty("__type")` on a normally-named POJO getter
> (`getType()`), keeping the Java side readable.

## Persisted queries (Apollo APQ) — only registered hashes execute

APQ sends a **SHA-256 hash** of the operation instead of the full text. The deterministic test: a hash-only
request for an unregistered query returns `PERSISTED_QUERY_NOT_FOUND`; sending the full query **with** the hash
registers it; the hash-only request then resolves.

```java
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;

@Test
public void persistedQueryRejectsUnregisteredHashThenResolvesOnceRegistered() throws Exception {
    String query = UserOperations.GET_USER;
    byte[] digest = MessageDigest.getInstance("SHA-256").digest(query.getBytes(StandardCharsets.UTF_8));
    String sha256Hash = HexFormat.of().formatHex(digest);
    Map<String, Object> persistedQuery = Map.of("version", 1, "sha256Hash", sha256Hash);
    Map<String, Object> extensions = Map.of("persistedQuery", persistedQuery);

    // 1) hash only, query omitted → server doesn't know it yet
    GraphQLResponse<GetUserData> miss = action.executePersisted(
        Map.of("variables", Map.of("id", "1"), "extensions", extensions));
    assertThat(miss.getErrors().get(0).getExtensions().getCode()).isEqualTo("PERSISTED_QUERY_NOT_FOUND");

    // 2) register by sending query + hash together
    GraphQLResponse<GetUserData> register = action.executePersisted(
        Map.of("query", query, "variables", Map.of("id", "1"), "extensions", extensions));
    assertThat(register.getErrors()).isNull();

    // 3) hash only now resolves from the server-side registry
    GraphQLResponse<GetUserData> hit = action.executePersisted(
        Map.of("variables", Map.of("id", "1"), "extensions", extensions));
    assertThat(hit.getData().getUser().getId()).isEqualTo("1");
}
```

> `executePersisted` wraps `executeRaw` to forward `extensions` in the POST body. Compute the hash over the
> **exact** query string the server normalizes on — keep one canonical document constant per operation (don't
> reformat it between hashing and sending).

## Anti-patterns

- **Asserting `getStatusCode() == SC_BAD_REQUEST` for a GraphQL error.** GraphQL returns **200**; the error is in
  the body. *Fix:* assert `getErrors()` is non-empty and check `errors.get(0).getExtensions().getCode()`.
- **A typed client that throws on `errors` (DGS / Apollo-Kotlin default).** You can't assert the error path if
  the client already threw. *Fix:* the RestAssured action returns the raw envelope POJO.
- **Asserting only `data` (or only `errors`) on a partial response.** Half the truth. *Fix:* assert the resolved
  field on `data` **and** the failing field's `errors[]` entry by `path`.
- **String-interpolating input into the query** (`"{ user(id: \"" + id + "\") {...} }"`). Injection risk, breaks
  caching/APQ. *Fix:* always pass `variables` separately.
- **Trusting a mutation's echoed payload as proof of persistence.** *Fix:* round-trip a query and assert state.
- **A `*Data` POJO modelling the whole resource.** GraphQL returns only the **selected** fields. *Fix:* model the
  operation's selection set.
- **`assertThat(getErrors()).isNotEmpty()` and stopping.** "Some error" is not a contract. *Fix:* assert the
  specific `extensions.code` and `path`.
- **Deserializing inside the action / parsing `Map<String,Object>` in the test.** *Fix:* the action returns the
  typed envelope POJO via `response.as(new TypeRef<>(){})`; model the data with a POJO (`qa-api-dto-writer-java`).
- **`Thread.sleep`.** Banned by CLAUDE.md (and RestAssured is synchronous). Reaching for this skill for
  **subscriptions** → `qa-websocket-sse-testing-java`.
- **Hardcoding the endpoint / committing the token.** *Fix:* `SystemPropertyUtil` / env, read lazily; secrets
  via `qa-auth0-test-tokens-java`.

## Examples

**End-to-end: a not-found query proves the envelope discipline.** A REST author writes
`assertEquals(response.getStatusCode(), SC_NOT_FOUND)` and the test fails because the server answered `200`. The
GraphQL-correct version asserts `getStatus() == SC_OK`, then `errors.get(0).getExtensions().getCode() == "NOT_FOUND"`
and `data.user == null` — the status line carries no signal; the envelope carries all of it.

**Composing with the REST sibling's `ProblemDetails` instinct.** The REST sibling deserializes a
`ProblemDetails`-style POJO on a 4xx; here the analogue is the `GraphQLError` envelope on a 200 — same "validate
the error shape, don't settle for a status" discipline, different envelope.

## Rules (hard constraints)

- **The gate is the `errors` envelope, not the status code.** Assert `getStatus() == SC_OK` (it documents the
  contract) but make `assertThat(getErrors()).isNull()` (happy) / the `extensions.code` + `path` checks (error)
  the real assertion. The one exception — transport-level auth/parse failures — is pinned explicitly per the
  server's contract.
- **The action never throws on a GraphQL error.** `execute` returns `GraphQLResponse<T>` raw (deserialized via
  `TypeRef`); the test owns what counts as failure. No deserialization or assertion inside the action.
- **`data` and `errors` asserted together on partial responses** — the resolved field(s) on `data` **and** the
  failing field's `errors[]` entry by `path`/`extensions.code`.
- **Operations are parameterized — variables passed in a separate map, never interpolated into the query string.**
- **Model the typed `data` per operation** (selection set) as a Lombok POJO, plus the shared `GraphQLError`
  envelope; `@JsonIgnoreProperties(ignoreUnknown = true)` on every POJO. One logical assertion focus per test;
  assert specific `extensions.code` + `path`, never a bare `isNotEmpty()`.
- **A mutation test round-trips a read** to prove persistence; data created in a test is cleaned up in
  `@AfterMethod` (cleanup guarded so it can't mask a failure).
- **TestNG + RestAssured + Jackson + AssertJ**; `HttpStatus.SC_*` constants, never raw ints. Subscriptions →
  `qa-websocket-sse-testing-java`. Endpoint + token via `SystemPropertyUtil`/env, lazy, never logged. No
  `Thread.sleep`.

## Cross-references

- `qa-api-test-author-graphql-typescript` — **the canonical file**: same four ideas, Vitest + native `fetch` +
  Zod (`GetUserDataSchema.parse` / `GraphQLErrorsSchema`). Read it for the family rationale.
- `qa-api-test-author-graphql-dotnet` — the .NET sibling (NUnit + `HttpClient` + `System.Text.Json` records);
  same four ideas, different libs.
- `qa-api-test-author-generator-java` — the **REST sibling** this extends: the Action + POJO + Test layering,
  `RequestSpecBuilder`, `response.as(...)`, `SystemPropertyUtil`, and the cleanup discipline.
- `qa-websocket-sse-testing-java` — **GraphQL subscriptions** (graphql-ws over WebSocket) live here.
- `qa-api-dto-writer-java` — generate the typed `data` POJOs / operation models in isolation.
- `qa-auth0-test-tokens-java` — obtain the bearer token for authenticated operations.
- `qa-api-mocking-java` — **mock** a GraphQL dependency the SUT calls; this skill **tests** a real
  backend. `qa-performance-gatling-java` — GraphQL **load** + the N+1 pitfall. `qa-allure-reporting-java`.
