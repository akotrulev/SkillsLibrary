---
name: qa-permission-testing-dotnet
description: Use when authoring functional access-control tests in .NET (NUnit + RestSharp) that cover the OWASP scanner blind spot — BOLA/IDOR (object-level), BFLA (function-level), and property-level authorization — as an identity × endpoint × object matrix asserting 403/404. Maps to OWASP A01:2025 / API1·3·5:2023. Triggers "test for IDOR", "can user A read user B's records", "build an authorization matrix", "cross-tenant leak test". Not for scanner DAST (`zap-*`) or minting tokens (`test-login-tokens`).
---

# Security Testing — Access Control / Authorization Matrix (.NET / NUnit)

The **.NET port** of the canonical `qa/typescript/skills/security-testing/permission-testing` skill. This
is the highest-value security testing most teams are missing, and the one security concern you **cannot**
delegate to a scanner.

> **⚠️ Why this is a functional test, not a scan.** A scanner authenticated as Alice has no way to know that
> invoice `42` belongs to Bob — the malicious request `GET /invoices/42` is *perfectly well-formed HTTP*.
> Broken access control is a **logic** flaw, not a **syntax** flaw, so DAST/SAST/fuzzers miss it by design
> (see `qa/_shared/security/SKILL.md` → "the scanner blind spot"). You catch it by writing tests that **act
> as one user against another user's objects and assert the request is denied** — in your normal API test
> framework, reusing your clients, DTOs, and multi-user tokens. OWASP A01:2025 is **#1** and API1/API3/API5
> are three of the API Top 10 for exactly this reason.

## Stack

- .NET 8, C# (nullable reference types enabled), **NUnit** as the runner, calling through the project's
  `{Resource}Client` (RestSharp, from `qa/dotnet/skills/api-client-writer`) — never a one-off `RestClient`.
- Multi-user/role tokens via `qa/dotnet/skills/test-login-tokens` (ROPG to mint a token *as a specific
  seeded test user*; M2M for service roles). Tokens cached per user for their `ExpiresIn` lifetime, secrets
  via env read lazily (`Environment.GetEnvironmentVariable`).
- Record DTOs (`qa/dotnet/skills/api-models`) to assert the *owner's* happy path returns the real
  body — proving a test isn't trivially always-deny.
- `[TestCaseSource]` / `[TestCase]` parameterized matrices (CLAUDE.md: no conditional logic in tests — use
  parameterized tests).

## The three authorization flaws this covers

| OWASP | Flaw | The test | Expected |
|-------|------|----------|----------|
| **API1:2023 / A01** | **BOLA / IDOR** (object-level) | Alice requests **Bob's** object by id | `403`/`404` — denied |
| **API3:2023** | **Object Property Level** (mass-assignment / over-read) | Alice sets a field she may not (`Role`, `IsAdmin`, `OwnerId`) or reads a field she may not (`Ssn`) | field ignored/rejected; sensitive field absent |
| **API5:2023 / A01** | **BFLA** (function-level) | a regular user calls an **admin-only** endpoint | `403` — denied |
| (baseline) | **Authentication** | **anonymous** calls a protected endpoint | `401` |
| (control) | **positive** | the **owner / authorized role** calls their own endpoint | `200` + real body |

Two axes of privilege escalation, both covered by the matrix:
- **Horizontal** — same role, *another user's* data (Alice → Bob's invoice). BOLA.
- **Vertical** — *higher privilege* than granted (user → admin function). BFLA.

> **403 vs 404 — pin the project's leak policy.** Returning `403 Forbidden` for someone else's object
> *confirms the object exists* (an enumeration/info leak). Many threat models prefer `404 Not Found` for
> cross-tenant access so existence isn't disclosed. **Decide the policy per project and assert it
> explicitly** — don't accept "either 4xx". The helper below takes the expected status so the policy is
> codified, not assumed.

## The matrix model — the core of the skill

An access-control suite is a **table**, not a pile of ad-hoc tests. Each row is `(caller, action, target,
expected)`. Seed at least: **two peer users** (Alice, Bob — same role, different ownership) to catch BOLA,
and **one elevated role** (Admin) to catch BFLA. Drive the table with `[TestCaseSource]` so every cell is
one independent, named test.

### Fixtures — seeded users and their tokens (cached per user)

```csharp
// Tests/Security/AccessControl/Actor.cs
using Tests.Support.Auth; // qa/dotnet/skills/test-login-tokens

namespace Tests.Security.AccessControl;

/// <summary>A test actor = a seeded identity + a lazily-cached bearer token for it.</summary>
public sealed record Actor(string Name, Func<Task<string>> Token)
{
    // Credentials come from env, read lazily — never inline (CLAUDE.md: no secrets in code).
    // Each provider caches the token for its lifetime (see test-login-tokens).
    public static readonly Actor Alice = new("alice", () => Tokens.ForUser("ALICE").GetAccessTokenAsync());
    public static readonly Actor Bob   = new("bob",   () => Tokens.ForUser("BOB").GetAccessTokenAsync());
    public static readonly Actor Admin = new("admin", () => Tokens.ForUser("ADMIN").GetAccessTokenAsync());
    public static readonly Actor Anon  = new("anonymous", () => Task.FromResult(string.Empty)); // no header

    public override string ToString() => Name; // → readable test-case names
}
```

`Tokens.ForUser("ALICE")` returns a per-user cached `TestUserTokenProvider` (ROPG as that seeded user); see
`qa/dotnet/skills/test-login-tokens` for the provider + caching. An empty token means no `Authorization`
header is sent.

### Seed data each actor owns (builders, not inline literals)

```csharp
// Tests/Security/AccessControl/OwnedResource.cs
namespace Tests.Security.AccessControl;

public sealed record OwnedResource(string OwnerName, string Id);
```

```csharp
// Tests/Security/AccessControl/InvoiceFixtures.cs
using ApiTests.Clients;
using ApiTests.Models.Billing.InvoiceModels;

namespace Tests.Security.AccessControl;

/// <summary>
/// Create one invoice owned by each peer user, returning their ids. Run once in [OneTimeSetUp]; torn down
/// in [OneTimeTearDown]. Each test reads these — no test mutates another's fixture (CLAUDE.md: tests are
/// independent).
/// </summary>
public static class InvoiceFixtures
{
    public static async Task<(OwnedResource Alice, OwnedResource Bob)> SeedInvoicesAsync()
    {
        InvoiceDto alice = new InvoiceClient(await Actor.Alice.Token())
            .Create(new InvoiceInDto(Amount: 100, Currency: "EUR"), HttpStatusCode.Created);
        InvoiceDto bob = new InvoiceClient(await Actor.Bob.Token())
            .Create(new InvoiceInDto(Amount: 200, Currency: "EUR"), HttpStatusCode.Created);

        return (
            new OwnedResource(Actor.Alice.Name, alice.Id),
            new OwnedResource(Actor.Bob.Name, bob.Id));
    }
}
```

### The deny helper — codify the policy

```csharp
// Tests/Security/AccessControl/AccessControlAsserts.cs
using System.Net;
using NUnit.Framework;
using RestSharp;

namespace Tests.Security.AccessControl;

public static class AccessControlAsserts
{
    /// <summary>
    /// Assert a request was DENIED at the configured status, and — critically — that **no resource body
    /// leaked**. A 403 that still returns the object in the body is still a BOLA. Pass the project's chosen
    /// denial status (403 to deny-and-confirm-existence, 404 to deny-without-disclosure).
    /// </summary>
    public static void ExpectDenied(RestResponse response, HttpStatusCode expectedStatus)
    {
        Assert.Multiple(() =>
        {
            Assert.That(response.StatusCode, Is.EqualTo(expectedStatus),
                "denied requests must use the project's documented status.");
            // The body must not carry the protected resource. Adjust the predicate to your envelope.
            Assert.That(response.Content ?? string.Empty, Does.Not.Contain("\"amount\""),
                "a denied response must not leak the resource body.");
        });
    }
}
```

## BOLA / IDOR — the headline test (horizontal)

```csharp
// Tests/Security/AccessControl/InvoiceBolaTests.cs
using System.Net;
using ApiTests.Clients;
using ApiTests.Models.Billing.InvoiceModels;
using NUnit.Framework;
using RestSharp;
using static Tests.Security.AccessControl.AccessControlAsserts;

namespace Tests.Security.AccessControl;

[TestFixture]
public class InvoiceBolaTests // API1:2023 BOLA — invoice object-level authorization (WSTG-ATHZ-04)
{
    private static OwnedResource _alice = null!;
    private static OwnedResource _bob = null!;

    [OneTimeSetUp]
    public async Task SeedAsync() => (_alice, _bob) = await InvoiceFixtures.SeedInvoicesAsync();

    [OneTimeTearDown]
    public async Task TearDownAsync()
    {
        // no try/catch — a cleanup that fails should fail the teardown loudly
        await new InvoiceClient(await Actor.Alice.Token()).Delete(_alice.Id);
        await new InvoiceClient(await Actor.Bob.Token()).Delete(_bob.Id);
    }

    // POSITIVE control — the owner CAN read their own invoice. Proves the suite isn't trivially always-deny.
    [Test]
    public async Task Should_ReturnInvoice_When_OwnerReadsOwn()
    {
        InvoiceDto invoice = new InvoiceClient(await Actor.Alice.Token())
            .GetById(_alice.Id, HttpStatusCode.OK); // typed overload → asserts 200 + deserializes
        Assert.That(invoice.Amount, Is.EqualTo(100));
    }

    // The matrix of cross-user / privilege rows. 404 here = this project hides existence cross-tenant.
    private static IEnumerable<TestCaseData> CrossUserRows()
    {
        yield return new TestCaseData(Actor.Alice, nameof(Verb.Get),    "bob",   HttpStatusCode.NotFound);
        yield return new TestCaseData(Actor.Alice, nameof(Verb.Put),    "bob",   HttpStatusCode.NotFound);
        yield return new TestCaseData(Actor.Alice, nameof(Verb.Delete), "bob",   HttpStatusCode.NotFound);
        yield return new TestCaseData(Actor.Bob,   nameof(Verb.Get),    "alice", HttpStatusCode.NotFound);
        yield return new TestCaseData(Actor.Anon,  nameof(Verb.Get),    "alice", HttpStatusCode.Unauthorized);
    }

    private enum Verb { Get, Put, Delete }

    [TestCaseSource(nameof(CrossUserRows))]
    public async Task Should_Deny_When_CallerActsOnOthersInvoice(
        Actor caller, string verb, string targetName, HttpStatusCode expected)
    {
        string token = await caller.Token();
        string id = targetName == "alice" ? _alice.Id : _bob.Id;
        InvoiceClient client = new InvoiceClient(token);

        RestResponse response = verb switch
        {
            nameof(Verb.Get)    => client.GetByIdRaw(id),
            nameof(Verb.Put)    => client.UpdateRaw(id, new InvoiceInDto(Amount: 1, Currency: "EUR")),
            _                   => client.DeleteRaw(id),
        };

        ExpectDenied(response, expected);
    }
}
```

The `GetByIdRaw`/`UpdateRaw`/`DeleteRaw` variants return the `RestResponse` *without* asserting `200` (that's
what the client's typed `(args, HttpStatusCode expected)` overloads do) — access-control tests assert the
**status themselves**, so use the raw overloads (see `qa/dotnet/skills/api-client-writer`). The `switch`
expression selects the verb's call from the parameterized row; it drives no assertions, so it stays within
the "no conditional logic in tests" rule.

## BFLA — function-level (vertical privilege escalation)

```csharp
// Tests/Security/AccessControl/AdminBflaTests.cs
using System.Net;
using ApiTests.Clients;
using NUnit.Framework;
using RestSharp;
using static Tests.Security.AccessControl.AccessControlAsserts;

namespace Tests.Security.AccessControl;

[TestFixture]
public class AdminBflaTests // API5:2023 BFLA — admin-only functions reject regular users (WSTG-ATHZ-02)
{
    // POSITIVE control — admin CAN.
    [Test]
    public async Task Should_ListAllUsers_When_Admin()
    {
        RestResponse response = new AdminClient(await Actor.Admin.Token()).ListUsersRaw();
        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.OK));
    }

    private static IEnumerable<TestCaseData> AdminFunctions()
    {
        yield return new TestCaseData("ListUsers",
            (Func<AdminClient, RestResponse>)(c => c.ListUsersRaw()));
        yield return new TestCaseData("DeleteUser",
            (Func<AdminClient, RestResponse>)(c => c.DeleteUserRaw("u_123")));
        yield return new TestCaseData("SetUserRole",
            (Func<AdminClient, RestResponse>)(c => c.SetUserRoleRaw("u_123", "admin")));
    }

    [TestCaseSource(nameof(AdminFunctions))]
    public async Task Should_Deny403_When_RegularUserCallsAdminFunction(
        string function, Func<AdminClient, RestResponse> call)
    {
        AdminClient client = new AdminClient(await Actor.Alice.Token()); // a normal user
        ExpectDenied(call(client), HttpStatusCode.Forbidden); // must not reach admin functions
    }
}
```

## Object Property Level — API3 (mass-assignment & over-read)

```csharp
// Tests/Security/AccessControl/InvoicePropertyTests.cs
using System.Net;
using ApiTests.Clients;
using ApiTests.Models.Billing.InvoiceModels;
using NUnit.Framework;
using RestSharp;

namespace Tests.Security.AccessControl;

[TestFixture]
public class InvoicePropertyTests // API3:2023 — object property level authorization
{
    // Mass-assignment: a client must NOT be able to set a privileged field via the normal write path.
    [Test]
    public async Task Should_IgnoreOwnerId_When_UserAttemptsMassAssignment()
    {
        InvoiceClient client = new InvoiceClient(await Actor.Alice.Token());

        // The attacker-controlled privileged field is carried as a raw extra property.
        RestResponse created = client.CreateRaw(new InvoiceCreateWithOwner(
            Amount: 50, Currency: "EUR", OwnerId: Actor.Bob.Name));
        Assert.That(created.StatusCode, Is.EqualTo(HttpStatusCode.Created));

        // The server must have ignored OwnerId — the invoice belongs to Alice, not Bob.
        string id = Deserialize<InvoiceDto>(created).Id;
        InvoiceDto readBack = client.GetById(id, HttpStatusCode.OK);
        Assert.That(readBack.OwnerId, Is.Not.EqualTo(Actor.Bob.Name));
    }

    // Over-read: a sensitive property must not be serialized to a caller who may not see it.
    [Test]
    public async Task Should_NotExposeInternalNotes_When_NonOwnerRoleReads()
    {
        RestResponse response = new InvoiceClient(await Actor.Alice.Token())
            .GetByIdRaw(/* a shared, readable id */ "inv_shared");
        Assert.That(response.Content ?? string.Empty, Does.Not.Contain("\"internalNotes\""));
    }
}
```

`InvoiceCreateWithOwner` is a throwaway record carrying the privileged `OwnerId` the legitimate
`InvoiceInDto` deliberately omits — that is the whole point of mass-assignment: send a field the contract
does not expose and prove the server drops it.

## Building the matrix from a policy table (scales past a few endpoints)

For a real API, express the policy once as data and generate the rows — one source of truth that doubles as
documentation of intended access:

```csharp
// Tests/Security/AccessControl/PolicyRow.cs
namespace Tests.Security.AccessControl;

public sealed record DeniedCaller(Actor Actor, HttpStatusCode Expected);

public sealed record PolicyRow(
    string Endpoint,                                       // for the test name
    Func<string, string, RestResponse> Call,              // (token, id) → raw response
    Actor Owner,                                           // who may (200)
    IReadOnlyList<DeniedCaller> Others);                  // who may not, and how it's denied
// One PolicyRow per protected operation; a [TestCaseSource] expands each row into owner + denied cells.
// Adding an endpoint = adding a row. A new endpoint with no row is a visible coverage gap.
```

## Anti-patterns

- **Asserting "any 4xx" instead of the policy's exact status.** Hides a `403`-that-leaks-existence when the
  policy is `404`. *Fix:* `ExpectDenied(response, HttpStatusCode.NotFound | Forbidden | Unauthorized)` — pin it.
- **Checking the status but not the body.** A `403` that still returns the object in the body is still a
  BOLA. *Fix:* assert the resource body did not leak.
- **No positive control.** A suite that only asserts denials passes even if the endpoint is *down* for
  everyone. *Fix:* always include the owner-can / admin-can happy path.
- **Reusing one user for everything.** You can't catch *horizontal* escalation with a single identity. *Fix:*
  seed ≥2 peers + 1 elevated role.
- **Sharing a mutable fixture across tests** (Alice deletes the invoice Bob's test reads). *Fix:* each peer
  owns its own seeded row; independent tests (CLAUDE.md).
- **Testing only `GET`.** IDOR lives in `PUT`/`PATCH`/`DELETE` too — often worse (cross-tenant *mutation*).
  *Fix:* matrix the verbs.
- **Minting a token per test / sleeping for auth.** *Fix:* cache per actor via `test-login-tokens`; never
  `Thread.Sleep` / `Task.Delay` for auth.
- **Hardcoding credentials/tokens.** *Fix:* env, read lazily via `Environment.GetEnvironmentVariable`.
- **Treating a green access-control suite as "access control is secure."** It covers the rows you wrote;
  business-logic abuse (API6) still needs a manual pentest. *Fix:* say so; track endpoint coverage.

## Rules (hard constraints)

- Cover **BOLA (API1)**, **object-property (API3)**, and **BFLA (API5)** — horizontal *and* vertical
  escalation — plus an anonymous `401` baseline and a **positive control** per resource.
- Assert the **project's documented denial status** (`403` vs `404` leak policy) **and** that **no resource
  body leaks**. One logical assertion per test; test names `Should_X_When_Y`; parameterized matrix via
  `[TestCaseSource]` / `[TestCase]` (no conditional logic in tests).
- Seed **≥2 peer users + 1 elevated role**; each owns its own fixture; tests are independent. Matrix the
  **verbs** (`GET`/`PUT`/`PATCH`/`DELETE`), not just reads.
- Reuse the project's `{Resource}Client` **raw** overloads (status asserted by the test) and
  `qa/dotnet/skills/test-login-tokens` for per-actor tokens (cached, secrets via env read lazily). Async all
  the way — never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` on a token or HTTP call.
- Tag cases with their **OWASP API id** and **WSTG-ATHZ** test-id; a new protected endpoint with no matrix
  row is a visible coverage gap. A green suite ≠ "secure" — business-logic abuse needs manual pentest.

## Cross-references

- `qa/_shared/security/SKILL.md` — the OWASP backbone + the scanner-blind-spot rationale; **load alongside**.
- `qa/typescript/skills/security-testing/permission-testing` — the **canonical** (Vitest + fetch) skill
  this .NET port mirrors; `qa/java/skills/security-testing/permission-testing` — the TestNG sibling.
- `qa/dotnet/skills/test-login-tokens` — mint per-actor tokens (ROPG as a specific test user; M2M for
  service roles), cached for their lifetime.
- `qa/dotnet/skills/api-client-writer` / `api-models` — the `{Resource}Client` raw/typed overloads
  and record DTOs the matrix reuses.
- `qa/dotnet/skills/api-test-author/writer` — generic functional API tests (this skill is the
  authorization slice of the same suite).
- `qa/_shared/security-testing/api-fuzzing` — complementary spec-driven fuzzing (finds malformed-input bugs;
  does **not** find BOLA).
- `qa/manual/bug-report-writer` — write up a confirmed BOLA/BFLA with the caller, target object, and response.
