---
name: qa-security-testing-access-control-testing-java
description: >-
  Author **functional access-control tests** in Java (TestNG + AssertJ + RestAssured) that cover the OWASP
  scanner blind spot — **Broken Object Level Authorization (BOLA/IDOR, API1:2023)**, **Broken Object Property
  Level Authorization (API3:2023)**, and **Broken Function Level Authorization (BFLA, API5:2023)** — i.e.
  A01:2025 Broken Access Control. The model is an **authorization matrix**: seed multiple users/roles (via
  `qa/java/skills/auth0-test-tokens`), then assert each caller × target-object × endpoint resolves to the
  right outcome — owner/authorized → 200, cross-tenant/under-privileged → **403/404**, anonymous → 401 —
  reusing the project's `{Resource}Client`. Use when the user wants IDOR / BOLA / privilege-escalation /
  horizontal-or-vertical access-control coverage, an authz test matrix, or to prove tenant isolation.
  DAST/scanners cannot find these (well-formed requests, logic flaws) — this is a functional test, not a scan.
  Do NOT use for: scanner-based DAST (see qa-security-testing-zap-automation-framework), spec-driven fuzzing
  (qa-security-testing-api-fuzzing — won't find BOLA), generic functional API tests
  (qa/java/skills/api-test-author), business-logic abuse (manual pentest), or the TypeScript / .NET stacks
  (`qa/typescript/skills/security-testing/access-control-testing` is the **canonical**;
  `qa/dotnet/skills/security-testing/access-control-testing` is the .NET sibling). Load qa/_shared/security
  alongside.
---

# Security Testing — Access Control / Authorization Matrix (Java / TestNG)

The TypeScript skill (`qa/typescript/skills/security-testing/access-control-testing`) is the **canonical**;
this is its Java/TestNG port. This is the highest-value security testing most teams are missing, and the one
security concern you **cannot** delegate to a scanner.

> **⚠️ Why this is a functional test, not a scan.** A scanner authenticated as Alice has no way to know that
> invoice `42` belongs to Bob — the malicious request `GET /invoices/42` is *perfectly well-formed HTTP*.
> Broken access control is a **logic** flaw, not a **syntax** flaw, so DAST/SAST/fuzzers miss it by design
> (see `qa/_shared/security/SKILL.md` → "the scanner blind spot"). You catch it by writing tests that **act
> as one user against another user's objects and assert the request is denied** — in your normal API test
> framework, reusing your clients, DTOs, and multi-user tokens. OWASP A01:2025 is **#1** and API1/API3/API5
> are three of the API Top 10 for exactly this reason.

## Stack

- Java 21, **TestNG** as the runner, **AssertJ** for assertions, RestAssured through the project's
  `{Resource}Client` (from `qa/java/skills/api-client-writer`) — never a one-off `RestAssured.given()`.
- Multi-user/role tokens via `qa/java/skills/auth0-test-tokens` (ROPG to mint a token *as a specific seeded
  test user*; M2M for service roles). Tokens cached per user, secrets via env read lazily (`System.getenv`).
- Record DTOs (`qa/java/skills/api-dto-writer`) to assert the *owner's* happy path returns the real body —
  proving a test isn't trivially always-deny.
- TestNG `@DataProvider` parameterized tables for the matrix (CLAUDE.md: no conditional logic in tests — use
  parameterized tests).

## The three authorization flaws this covers

| OWASP | Flaw | The test | Expected |
|-------|------|----------|----------|
| **API1:2023 / A01** | **BOLA / IDOR** (object-level) | Alice requests **Bob's** object by id | `403`/`404` — denied |
| **API3:2023** | **Object Property Level** (mass-assignment / over-read) | Alice sets a field she may not (`role`, `isAdmin`, `ownerId`) or reads a field she may not (`ssn`) | field ignored/rejected; sensitive field absent |
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
and **one elevated role** (Admin) to catch BFLA. Drive the table with a `@DataProvider` so every cell is one
independent, named test.

### Fixtures — seeded actors and their tokens (cached per actor)

```java
// src/test/java/.../security/accesscontrol/Actors.java
package security.accesscontrol;

import support.auth.Tokens; // qa/java/skills/auth0-test-tokens

/** A test actor = a seeded identity + a lazily-cached bearer token for it. */
public record Actor(String name, TokenSupplier token) {

    @FunctionalInterface
    public interface TokenSupplier {
        /** Resolve a Bearer token for this actor (cached for its lifetime by the auth0 helper). */
        String get() throws Exception;
    }

    // Credentials come from env, read lazily — never inline (CLAUDE.md: no secrets in code).
    public static final Actor ALICE = new Actor("alice", () -> Tokens.userToken("ALICE"));
    public static final Actor BOB   = new Actor("bob",   () -> Tokens.userToken("BOB"));
    public static final Actor ADMIN = new Actor("admin", () -> Tokens.userToken("ADMIN"));
    public static final Actor ANON  = new Actor("anonymous", () -> ""); // no Authorization header
}
```

`Tokens.userToken("ALICE")` resolves a `TestUserTokenProvider` (ROPG, per seeded user) cached for its
`expires_in`; see `qa/java/skills/auth0-test-tokens`. The provider is fetched **once** and reused — never
per test.

### Seed data each actor owns (builders, not inline literals)

```java
// src/test/java/.../security/accesscontrol/InvoiceFixtures.java
package security.accesscontrol;

import clients.billing.InvoicesClient;
import models.billing.InvoiceInDto;

public final class InvoiceFixtures {
    private InvoiceFixtures() {}

    public record OwnedResource(String ownerName, String id) {}

    public record SeededInvoices(OwnedResource alice, OwnedResource bob) {}

    /**
     * Create one invoice owned by each peer user, returning their ids. Run once in @BeforeClass; torn down in
     * @AfterClass. Each test reads these — no test mutates another's fixture (CLAUDE.md: tests are independent).
     */
    public static SeededInvoices seed() throws Exception {
        var alice = InvoicesClient.using(Actor.ALICE.token().get())
            .create(new InvoiceInDto(100, "EUR"), HttpStatus.SC_CREATED);
        var bob = InvoicesClient.using(Actor.BOB.token().get())
            .create(new InvoiceInDto(200, "EUR"), HttpStatus.SC_CREATED);
        return new SeededInvoices(
            new OwnedResource(Actor.ALICE.name(), alice.id()),
            new OwnedResource(Actor.BOB.name(), bob.id()));
    }
}
```

### The deny helper — codify the policy

```java
// src/test/java/.../security/accesscontrol/AccessControlAssertions.java
package security.accesscontrol;

import io.restassured.response.Response;
import static org.assertj.core.api.Assertions.assertThat;

public final class AccessControlAssertions {
    private AccessControlAssertions() {}

    /**
     * Assert a request was DENIED at the configured status, and — critically — that **no resource body
     * leaked**. A 403 that still returns the object in the body is still a BOLA. Pass the project's chosen
     * denial status (403 to deny-and-confirm-existence, 404 to deny-without-disclosure).
     */
    public static void expectDenied(Response response, int expectedStatus) {
        assertThat(response.statusCode())
            .as("denied requests must use the project's documented status")
            .isEqualTo(expectedStatus);
        // The body must not carry the protected resource. Adjust the path to your envelope.
        assertThat(response.jsonPath().get("amount"))
            .as("a denied response must not leak the resource body")
            .isNull();
    }
}
```

## BOLA / IDOR — the headline test (horizontal)

```java
// src/test/java/.../security/accesscontrol/InvoiceBolaTest.java
package security.accesscontrol;

import clients.billing.InvoicesClient;
import models.billing.InvoiceDto;
import org.apache.http.HttpStatus;
import org.testng.annotations.*;
import security.accesscontrol.InvoiceFixtures.OwnedResource;
import security.accesscontrol.InvoiceFixtures.SeededInvoices;

import static org.assertj.core.api.Assertions.assertThat;
import static security.accesscontrol.AccessControlAssertions.expectDenied;

/** API1:2023 BOLA — invoice object-level authorization (WSTG-ATHZ-04). */
public class InvoiceBolaTest extends BaseTest {

    private SeededInvoices seeded;

    @BeforeClass
    public void seedInvoices() throws Exception { seeded = InvoiceFixtures.seed(); }

    @AfterClass(alwaysRun = true)
    public void teardown() throws Exception {
        InvoicesClient.using(Actor.ALICE.token().get()).delete(seeded.alice().id());
        InvoicesClient.using(Actor.BOB.token().get()).delete(seeded.bob().id());
    }

    // POSITIVE control — the owner CAN read their own invoice. Proves the suite isn't trivially always-deny.
    @Test(description = "WSTG-ATHZ-04 positive control")
    public void Should_ReturnInvoice_When_OwnerReadsOwn() throws Exception {
        InvoiceDto invoice = InvoicesClient.using(Actor.ALICE.token().get())
            .getById(seeded.alice().id(), HttpStatus.SC_OK); // typed → status asserted + deserialized
        assertThat(invoice.amount()).isEqualTo(100);
    }

    // The matrix of cross-user / privilege rows. 404 here = this project hides existence cross-tenant.
    @DataProvider(name = "crossUserRows")
    public Object[][] crossUserRows() {
        return new Object[][] {
            { Actor.ALICE, (java.util.function.Supplier<OwnedResource>) () -> seeded.bob(),   "GET",    HttpStatus.SC_NOT_FOUND },
            { Actor.ALICE, (java.util.function.Supplier<OwnedResource>) () -> seeded.bob(),   "PUT",    HttpStatus.SC_NOT_FOUND },
            { Actor.ALICE, (java.util.function.Supplier<OwnedResource>) () -> seeded.bob(),   "DELETE", HttpStatus.SC_NOT_FOUND },
            { Actor.BOB,   (java.util.function.Supplier<OwnedResource>) () -> seeded.alice(), "GET",    HttpStatus.SC_NOT_FOUND },
            { Actor.ANON,  (java.util.function.Supplier<OwnedResource>) () -> seeded.alice(), "GET",    HttpStatus.SC_UNAUTHORIZED },
        };
    }

    @Test(dataProvider = "crossUserRows")
    public void Should_DenyCrossUserAccess_When_CallerActsOnOthersInvoice(
            Actor caller, java.util.function.Supplier<OwnedResource> target, String action, int expected)
            throws Exception {
        String token = caller.token().get();
        String id = target.get().id();
        var client = InvoicesClient.using(token);
        Response response = switch (action) {
            case "GET"    -> client.getByIdRaw(id);
            case "PUT"    -> client.updateRaw(id, new InvoiceInDto(1, "EUR"));
            default       -> client.deleteRaw(id);
        };
        expectDenied(response, expected);
    }
}
```

The `getByIdRaw`/`updateRaw`/`deleteRaw` variants return the `Response` *without* asserting `200` (that's what
the client's typed overloads do) — access-control tests assert the **status themselves**, so use the raw
overloads (see `qa/java/skills/api-client-writer`).

## BFLA — function-level (vertical privilege escalation)

```java
// src/test/java/.../security/accesscontrol/AdminBflaTest.java
package security.accesscontrol;

import clients.admin.AdminClient;
import io.restassured.response.Response;
import org.apache.http.HttpStatus;
import org.testng.annotations.*;

import static org.assertj.core.api.Assertions.assertThat;
import static security.accesscontrol.AccessControlAssertions.expectDenied;

/** API5:2023 BFLA — admin-only functions reject regular users (WSTG-ATHZ-02). */
public class AdminBflaTest extends BaseTest {

    // POSITIVE control — admin CAN.
    @Test(description = "WSTG-ATHZ-02 positive control")
    public void Should_ListAllUsers_When_Admin() throws Exception {
        Response response = AdminClient.using(Actor.ADMIN.token().get()).listUsersRaw();
        assertThat(response.statusCode()).isEqualTo(HttpStatus.SC_OK);
    }

    @FunctionalInterface
    interface AdminCall { Response invoke(String token) throws Exception; }

    @DataProvider(name = "adminFunctions")
    public Object[][] adminFunctions() {
        return new Object[][] {
            { "listUsers",   (AdminCall) t -> AdminClient.using(t).listUsersRaw() },
            { "deleteUser",  (AdminCall) t -> AdminClient.using(t).deleteUserRaw("u_123") },
            { "setUserRole", (AdminCall) t -> AdminClient.using(t).setUserRoleRaw("u_123", "admin") },
        };
    }

    @Test(dataProvider = "adminFunctions")
    public void Should_Deny403_When_RegularUserCallsAdminFunction(String fn, AdminCall call) throws Exception {
        // a normal user must not reach admin functions
        expectDenied(call.invoke(Actor.ALICE.token().get()), HttpStatus.SC_FORBIDDEN);
    }
}
```

## Object Property Level — API3 (mass-assignment & over-read)

```java
// src/test/java/.../security/accesscontrol/InvoicePropertyTest.java
package security.accesscontrol;

import java.util.Map;
import org.apache.http.HttpStatus;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** API3:2023 — object property level authorization. */
public class InvoicePropertyTest extends BaseTest {

    // Mass-assignment: a client must NOT be able to set a privileged field via the normal write path.
    @Test
    public void Should_IgnoreOwnerId_When_UserAttemptsMassAssignment() throws Exception {
        var alice = InvoicesClient.using(Actor.ALICE.token().get());
        // attacker-controlled privileged field, sent via the loose Map overload (see api-client-writer)
        Response created = alice.createRaw(Map.of(
            "amount", 50, "currency", "EUR", "ownerId", Actor.BOB.name()));
        assertThat(created.statusCode()).isEqualTo(HttpStatus.SC_CREATED);

        // The server must have ignored ownerId — the invoice belongs to Alice, not Bob.
        String id = created.jsonPath().getString("id");
        InvoiceDto readBack = alice.getById(id, HttpStatus.SC_OK);
        assertThat(readBack.ownerId()).isNotEqualTo(Actor.BOB.name());
    }

    // Over-read: a sensitive property must not be serialized to a caller who may not see it.
    @Test
    public void Should_NotExposeInternalNotes_When_NonOwnerRoleReads() throws Exception {
        Response response = InvoicesClient.using(Actor.ALICE.token().get())
            .getByIdRaw(/* a shared, readable id */ "inv_shared");
        assertThat(response.jsonPath().get("internalNotes"))
            .as("a sensitive property must not leak to a non-owner")
            .isNull();
    }
}
```

## Building the matrix from a policy table (scales past a few endpoints)

For a real API, express the policy once as data and generate the rows — one source of truth that doubles as
documentation of intended access:

```java
// src/test/java/.../security/accesscontrol/PolicyRow.java
package security.accesscontrol;

import io.restassured.response.Response;
import java.util.List;

@FunctionalInterface
interface ProtectedCall { Response invoke(String token, String id) throws Exception; }

/** One PolicyRow per protected operation; a @DataProvider emits one test per (row × denied actor). */
public record PolicyRow(
    String endpoint,                 // for the test name
    ProtectedCall call,
    Actor owner,                     // who may (200)
    List<Denied> others) {           // who may not, and how it's denied

    public record Denied(Actor actor, int expected) {} // 401 | 403 | 404
}
// Adding an endpoint = adding a row. A new endpoint with no row is a visible coverage gap.
```

## Anti-patterns

- **Asserting "any 4xx" instead of the policy's exact status.** Hides a `403`-that-leaks-existence when the
  policy is `404`. *Fix:* `expectDenied(response, SC_NOT_FOUND | SC_FORBIDDEN | SC_UNAUTHORIZED)` — pin it.
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
- **Minting a token per test / sleeping for auth.** *Fix:* cache per actor via `auth0-test-tokens`; never
  `Thread.sleep`.
- **Hardcoding credentials/tokens.** *Fix:* env, read lazily (`System.getenv`).
- **Treating a green access-control suite as "access control is secure."** It covers the rows you wrote;
  business-logic abuse (API6) still needs a manual pentest. *Fix:* say so; track endpoint coverage.

## Rules (hard constraints)

- Cover **BOLA (API1)**, **object-property (API3)**, and **BFLA (API5)** — horizontal *and* vertical
  escalation — plus an anonymous `401` baseline and a **positive control** per resource.
- Assert the **project's documented denial status** (`403` vs `404` leak policy) **and** that **no resource
  body leaks**. One logical assertion per test; test names `Should_X_When_Y`; parameterized matrix via
  `@DataProvider` (no conditional logic in tests).
- Seed **≥2 peer users + 1 elevated role**; each owns its own fixture; tests are independent. Matrix the
  **verbs** (`GET`/`PUT`/`PATCH`/`DELETE`), not just reads.
- Reuse the project's `{Resource}Client` **raw** overloads (status asserted by the test) and
  `qa/java/skills/auth0-test-tokens` for per-actor tokens (cached, secrets via env read lazily).
- Tag cases with their **OWASP API id** and **WSTG-ATHZ** test-id; a new protected endpoint with no matrix
  row is a visible coverage gap. A green suite ≠ "secure" — business-logic abuse needs manual pentest.

## Cross-references

- `qa/_shared/security/SKILL.md` — the OWASP backbone + the scanner-blind-spot rationale; **load alongside**.
- `qa/typescript/skills/security-testing/access-control-testing` — the **canonical** (Vitest + fetch) this
  skill ports from. `qa/dotnet/skills/security-testing/access-control-testing` — the NUnit sibling.
- `qa/java/skills/auth0-test-tokens` — mint per-actor tokens (ROPG as a specific test user; M2M for service
  roles), cached for their lifetime.
- `qa/java/skills/api-client-writer` / `api-dto-writer` — the `{Resource}Client` raw/typed overloads and
  record DTOs the matrix reuses.
- `qa/java/skills/api-test-author/generator` — generic functional API tests (this skill is the authorization
  slice of the same suite).
- `qa/_shared/security-testing/api-fuzzing` — complementary spec-driven fuzzing (finds malformed-input bugs;
  does **not** find BOLA).
- `qa/manual/bug-report-writer` — write up a confirmed BOLA/BFLA with the caller, target object, and response.
