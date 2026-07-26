---
name: qa-api-test-graphql-dotnet
description: Use when scaffolding black-box GraphQL API tests in .NET 10 (8-9) with NUnit + `HttpClient` + `System.Text.Json` — POST /graphql, assert on the `{data, errors}` envelope (status is 200 even on error), typed records per selection set. Triggers "write GraphQL API tests", "test this mutation", "assert the errors envelope". Not for REST (`api-test-author/generator`) or gRPC (`api-test-author/grpc`).
---

# QA — GraphQL API Test Writer (.NET 8 / NUnit + HttpClient + System.Text.Json)

> **Ported from the canonical `qa-api-test-graphql-typescript`.** The four ideas and the section order
> are identical; only the runner (NUnit instead of Vitest), the client (`HttpClient`, async-all-the-way), and
> the typing (`System.Text.Json` records + tightened `Assert.That` instead of Zod `parse`) change. See the
> TypeScript file for the family rationale.

Scaffolds black-box API tests in .NET against a deployed **GraphQL** backend. It reuses the **Operation + Client
+ Model + Test** layering of the REST sibling (`qa-api-test-writer-dotnet`) but adapts every layer to
the one fact that makes GraphQL testing its own discipline: **a GraphQL response is one HTTP 200 carrying a
`{ data, errors }` envelope, and the assertion lives in that envelope, not in `response.StatusCode`.**

> **The discipline this skill encodes** — four ideas that separate a correct GraphQL test from a REST reflex:
>
> 1. **Status is (almost) always 200 — assert on the body's `errors`, not `StatusCode`.** A GraphQL error
>    surfaces as `{ "errors": [...] }` in a `200 OK` body. `Assert.That(response.StatusCode, Is.EqualTo(BadRequest))`
>    is the REST habit and it is **wrong here**. The client returns the raw `{ Data, Errors }` envelope and
>    **never throws** on a GraphQL error; the test decides whether errors were expected. (Transport failures —
>    malformed body, auth middleware rejecting before resolving — *can* be non-200; assert those too, but they're
>    the exception.)
> 2. **`data` and `errors` coexist — assert the whole envelope, both branches.** **Partial success** is a
>    first-class GraphQL outcome: some fields resolve into `Data` while a failing field is `null` with an entry
>    in `Errors` whose `Path` names it. A real test asserts **both** — the fields that resolved *and* the error
>    (its `Path`, its `Extensions.Code`).
> 3. **The response is query-shaped — model the typed `Data` per operation.** You get back **exactly the fields
>    you selected**. So a `Data` record models the *operation's selection set*, not a whole resource. Model the
>    `errors[]` envelope once and reuse it.
> 4. **Pick the operation type deliberately.** A **query** asserts shape + values. A **mutation** asserts the
>    returned payload **and round-trips a read** to prove the change persisted. A **subscription** is a
>    long-lived stream over WebSocket (`graphql-ws`) — that's `qa-realtime-stream-testing-dotnet`; cross-link,
>    don't reimplement.

## Decision matrix — operation type → test shape

| Operation | What you're proving | Test shape |
|-----------|---------------------|------------|
| **Query** (read) | The right fields resolve with the right values | `POST { query, variables }` → assert `Errors` null/empty → field checks on `Data` |
| **Query — not found / forbidden** | A failure surfaces correctly | status **200** → assert `Errors` non-empty → `Errors[0].Extensions.Code` (`NOT_FOUND`/`FORBIDDEN`) + `Data.<field>` is `null` |
| **Query — partial** | Partial success is handled | one resolved field asserted on `Data` **and** the failing field's `Errors[]` entry asserted by `Path` |
| **Mutation** (write) | The change happened and persisted | assert the mutation payload → **round-trip a query** → assert the new state is readable |
| **Mutation — input validation** | Bad input rejected cleanly | `Errors` non-empty with `Extensions.Code == "BAD_USER_INPUT"`; `Data.<field>` null |
| **Subscription** (stream) | Server pushes events over time | **not this skill** → `qa-realtime-stream-testing-dotnet` |
| **Introspection** | Schema exposes the expected types/fields | query `__schema`/`__type` → assert presence; in prod assert introspection **disabled** |
| **Persisted queries (APQ)** | Only registered hashes execute | hash-only → `PERSISTED_QUERY_NOT_FOUND` → register (query+hash) → hash-only now resolves |

## Stack

- .NET 8, C# (nullable reference types enabled)
- **NUnit** (`Assert.That` / `Assert.Multiple` — **no FluentAssertions**)
- **`HttpClient`** for transport — a GraphQL request is a `POST` of `{ query, variables }`; **async all the way**
- **`System.Text.Json`** for (de)serialization — **never Newtonsoft**
- **Allure.NUnit** for reporting; secrets via `ConfigurationLoader` / env, never hardcoded
- Project layout: `ApiTests/Operations/`, `ApiTests/Clients/`, `ApiTests/Models/`, `ApiTests/Tests/`

> **Why `HttpClient` and not Strawberry Shake / a typed GraphQL client?** Generated clients **throw on a
> `GraphQLException` when the response contains `errors`**, which makes the *error path* (idea #2) awkward to
> assert. A black-box test needs the **raw envelope**, errors and all. So the canonical client is a thin
> `HttpClient` wrapper that never throws on GraphQL errors. RestSharp (the REST sibling's client) works too —
> the envelope-returning behavior is what matters, not the transport library.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Three layers**.

## Partial response — `Data` and `Errors` together (idea #2)

A query selecting several fields can **partially succeed**: the authorized fields resolve, a forbidden/erroring
field comes back `null` with an `Errors[]` entry pointing at its `Path`. Assert **both halves**.

```csharp
public const string GetUserWithBilling = """
    query GetUserWithBilling($id: ID!) {
      user(id: $id) { id email }
      billingProfile(userId: $id) { plan balanceCents }   # requires elevated scope
    }
    """;

public sealed record UserWithBillingData(User User, BillingProfile? BillingProfile);
public sealed record BillingProfile(string Plan, long BalanceCents);

[Test]
public async Task GetUserWithBilling_WhenForbiddenField_ResolvesUserAndErrorsOnBilling()
{
    GraphQLResponse<UserWithBillingData> response =
        await billingClient.GetUserWithBillingAsync("1");

    Assert.Multiple(() =>
    {
        // half 1: the field that DID resolve
        Assert.That(response.Data!.User.Email, Is.EqualTo("george.bluth@example.com"));
        Assert.That(response.Data.BillingProfile, Is.Null);                 // forbidden field is null in data

        // half 2: the error that names the field that did NOT resolve
        Assert.That(response.Errors![0].Path, Is.EqualTo(new object[] { "billingProfile" }));
        Assert.That(response.Errors[0].Extensions!.Code, Is.EqualTo("FORBIDDEN"));
    });
}
```

> Asserting only `Data` would pass while the user silently lost their billing data; asserting only `Errors` would
> miss that the rest of the query still worked. Partial success demands both.

## Mutation — assert the payload, then round-trip the read (idea #4)

A mutation returns a payload, but the payload alone doesn't prove the write **persisted**. Assert the returned
object, then query it back. Clean up created data in `[TearDown]` (or `try/finally`), cleanup wrapped in
`try/catch` so it never masks a test failure.

```csharp
[Test]
public async Task CreateUser_WhenValid_PersistsAndIsReadable()
{
    UserGraphQLClient userClient = new(AuthToken);

    GraphQLResponse<CreateUserData> created = await userClient.CreateUserAsync(
        new CreateUserInput("neo@example.com", "Thomas", "Anderson"));

    Assert.That(created.Errors, Is.Null);
    Assert.That(created.Data!.CreateUser.Email, Is.EqualTo("neo@example.com"));

    // round-trip: prove it persisted, don't trust the mutation's own echo
    GraphQLResponse<GetUserData> fetched = await userClient.GetUserAsync(created.Data.CreateUser.Id);
    Assert.That(fetched.Data!.User!.Email, Is.EqualTo("neo@example.com"));
}

[Test]
public async Task CreateUser_WhenEmailEmpty_ReturnsBadUserInput()
{
    UserGraphQLClient userClient = new(AuthToken);

    GraphQLResponse<CreateUserData> response = await userClient.CreateUserAsync(
        new CreateUserInput(string.Empty, "A", "B"));

    Assert.Multiple(() =>
    {
        Assert.That(response.Errors, Is.Not.Null.And.Not.Empty);
        Assert.That(response.Errors![0].Extensions!.Code, Is.EqualTo("BAD_USER_INPUT"));
        Assert.That(response.Data?.CreateUser, Is.Null);
    });
}
```

## Introspection — assert the schema contract, and that prod disables it

A single introspection query returns the schema's type system. Use it to assert a type/field exists — and, in a
production-config check, to assert introspection is **turned off** (a common hardening requirement).

```csharp
public const string TypeIntrospection = """
    query { __type(name: "User") { name fields { name } } }
    """;

public sealed record IntrospectionData(TypeInfo? __Type);   // map "__type" via JsonPropertyName in the record
public sealed record TypeInfo(string Name, IReadOnlyList<FieldInfo> Fields);
public sealed record FieldInfo(string Name);

[Test]
public async Task Introspection_ExposesEmailFieldOnUserType()
{
    GraphQLResponse<IntrospectionData> response = await schemaClient.IntrospectTypeAsync("User");

    IReadOnlyList<FieldInfo> fields = response.Data!.__Type!.Fields;
    Assert.That(fields.Select(f => f.Name), Does.Contain("email"));
}

[Test]
public async Task Introspection_IsDisabledInProduction()
{
    GraphQLResponse<IntrospectionData> response = await prodSchemaClient.IntrospectTypeAsync("User");

    Assert.Multiple(() =>
    {
        Assert.That(response.Data?.__Type, Is.Null);          // hardened server returns null __type
        Assert.That(response.Errors, Is.Not.Null.And.Not.Empty);
    });
}
```

> Map `__type` to the C# property with `[JsonPropertyName("__type")]` on a normally-named record member — C#
> identifiers starting with `__` are legal but `[JsonPropertyName]` keeps the mapping explicit and readable.

## Persisted queries (Apollo APQ) — only registered hashes execute

APQ sends a **SHA-256 hash** of the operation instead of the full text. The deterministic test: a hash-only
request for an unregistered query returns `PERSISTED_QUERY_NOT_FOUND`; sending the full query **with** the hash
registers it; the hash-only request then resolves.

```csharp
using System.Security.Cryptography;
using System.Text;

[Test]
public async Task PersistedQuery_RejectsUnregisteredHash_ThenResolvesOnceRegistered()
{
    string query = UserOperations.GetUser;
    string sha256Hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(query))).ToLowerInvariant();
    object persistedQuery = new { version = 1, sha256Hash };

    // 1) hash only, query omitted → server doesn't know it yet
    GraphQLResponse<GetUserData> miss = await client.ExecutePersistedAsync(
        new { variables = new { id = "1" }, extensions = new { persistedQuery } });
    Assert.That(miss.Errors![0].Extensions!.Code, Is.EqualTo("PERSISTED_QUERY_NOT_FOUND"));

    // 2) register by sending query + hash together
    GraphQLResponse<GetUserData> register = await client.ExecutePersistedAsync(
        new { query, variables = new { id = "1" }, extensions = new { persistedQuery } });
    Assert.That(register.Errors, Is.Null);

    // 3) hash only now resolves from the server-side registry
    GraphQLResponse<GetUserData> hit = await client.ExecutePersistedAsync(
        new { variables = new { id = "1" }, extensions = new { persistedQuery } });
    Assert.That(hit.Data!.User!.Id, Is.EqualTo("1"));
}
```

> `ExecutePersistedAsync` wraps `ExecuteRawAsync` to forward `extensions` in the POST body. Compute the hash over
> the **exact** query string the server normalizes on — keep one canonical document constant per operation (don't
> reformat it between hashing and sending).

## Anti-patterns

- **Asserting `Is.EqualTo(HttpStatusCode.BadRequest)` for a GraphQL error.** GraphQL returns **200**; the error
  is in the body. *Fix:* assert `response.Errors` is non-empty and check `Errors[0].Extensions.Code`.
- **A typed client that throws on `errors` (Strawberry Shake / generated-client default).** You can't assert the
  error path if the client already threw. *Fix:* the thin `HttpClient` client returns the raw envelope.
- **Asserting only `Data` (or only `Errors`) on a partial response.** Half the truth. *Fix:* assert the resolved
  field on `Data` **and** the failing field's `Errors[]` entry by `Path`.
- **String-interpolating input into the query** (`$"{{ user(id: \"{id}\") {{...}} }}"`). Injection risk, breaks
  caching/APQ. *Fix:* always pass `variables` separately.
- **Trusting a mutation's echoed payload as proof of persistence.** *Fix:* round-trip a query and assert state.
- **A `Data` record modelling the whole resource.** GraphQL returns only the **selected** fields. *Fix:* model
  the operation's selection set.
- **`Assert.That(response.Errors, Is.Not.Empty)` and stopping.** "Some error" is not a contract. *Fix:* assert
  the specific `Extensions.Code` and `Path`.
- **`var`, `Newtonsoft.Json`, FluentAssertions, `Thread.Sleep`, `.Result`/`.Wait()`.** All banned by CLAUDE.md.
  *Fix:* explicit types, `System.Text.Json`, `Assert.That`/`Assert.Multiple`, async-all-the-way.
- **Reaching for this skill for subscriptions.** *Fix:* `qa-realtime-stream-testing-dotnet`.
- **Hardcoding the endpoint / committing the token.** *Fix:* `ConfigurationLoader` / env, read lazily; secrets
  via `qa-test-login-tokens-dotnet`.

## Examples

**End-to-end: a not-found query proves the envelope discipline.** A REST author writes
`Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.NotFound))` and the test fails because the server
answered `200`. The GraphQL-correct version asserts `Status == OK`, then `Errors[0].Extensions.Code == "NOT_FOUND"`
and `Data.User is null` — the status line carries no signal; the envelope carries all of it.

**Composing with the REST sibling's `ProblemDetails` instinct.** The REST sibling parses `ProblemDetailsDto` on
a 4xx; here the analogue is the `GraphQLError` envelope on a 200 — same "validate the error shape, don't settle
for a status" discipline, different envelope.

## Rules (hard constraints)

- **The gate is the `errors` envelope, not `StatusCode`.** Assert `Status == OK` (it documents the contract) but
  make `Assert.That(response.Errors, Is.Null)` (happy) / the `Errors[0].Extensions.Code` + `Path` checks (error)
  the real assertion. The one exception — transport-level auth/parse failures — is pinned explicitly per the
  server's contract.
- **The client never throws on a GraphQL error.** `ExecuteAsync` returns `GraphQLResponse<T>` raw; the test owns
  what counts as failure. **Async all the way** — `await Http.SendAsync(...)`, never `.Result`/`.Wait()`.
- **`Data` and `Errors` asserted together on partial responses** — the resolved field(s) on `Data` **and** the
  failing field's `Errors[]` entry by `Path`/`Extensions.Code`.
- **Operations are parameterized — variables passed separately, never interpolated into the query string.**
- **Model the typed `Data` per operation** (selection set) as a record, plus the shared `GraphQLError` envelope.
  Wrap related checks in `Assert.Multiple`; assert specific `Extensions.Code` + `Path`, never a bare presence.
- **A mutation test round-trips a read** to prove persistence; data created in a test is cleaned up in
  `[TearDown]`/`try-finally` (cleanup in `try/catch`).
- **NUnit + `System.Text.Json` only** (no FluentAssertions, no Newtonsoft, no `var`). Subscriptions →
  `qa-realtime-stream-testing-dotnet`. Endpoint + token via `ConfigurationLoader`/env, lazy, never logged. No
  `Thread.Sleep`.

## Cross-references

- `qa-api-test-graphql-typescript` — **the canonical file**: same four ideas, Vitest + native `fetch` +
  Zod (`GetUserDataSchema.parse` / `GraphQLErrorsSchema`). Read it for the family rationale.
- `qa-api-test-graphql-java` — the Java sibling (RestAssured + TestNG treating `/graphql` as a POST,
  Jackson POJOs); same four ideas, different libs.
- `qa-api-test-writer-dotnet` — the **REST sibling** this extends: the Client + Model + Test layering,
  NUnit conventions, `ProblemDetailsDto` (the REST analogue of `GraphQLError`), and the cleanup discipline.
- `qa-realtime-stream-testing-dotnet` — **GraphQL subscriptions** (graphql-ws over WebSocket) live here.
- `qa-api-models-dotnet` — generate the typed `Data` records / operation models in isolation.
- `qa-test-login-tokens-dotnet` — obtain the bearer token for authenticated operations.
