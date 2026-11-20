---
name: permission-testing
description: Use when writing access-control tests in Java (TestNG + RestAssured) for BOLA/IDOR and BFLA. Triggers "test for IDOR", "can user A read user B's data". Not for scanner DAST (passive-scan).
disable-model-invocation: true
---

# Security Testing — Access Control / Authorization Matrix (Java / TestNG)

The TypeScript skill (`qa/typescript/skills/security-testing/permission-testing`) is the **canonical**;
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
- Multi-user/role tokens via `qa/java/skills/test-login-tokens` (ROPG to mint a token *as a specific seeded
  test user*; M2M for service roles). Tokens cached per user, secrets via env read lazily (`System.getenv`).
- Record DTOs (`qa/java/skills/api-models`) to assert the *owner's* happy path returns the real body —
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
> explicitly** — don't accept "either 4xx". The assertion below takes the expected status so the policy is
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

import support.auth.Tokens; // qa/java/skills/test-login-tokens

/** A test actor = a seeded identity + a lazily-cached bearer token for it. */
public record Actor(String name, TokenSupplier token) {

    @FunctionalInterface
    public interface TokenSupplier {
        /** Resolve a Bearer token for this actor (cached by the token provider). */

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
`expires_in`; see `qa/java/skills/test-login-tokens`. The provider is fetched **once** and reused — never
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

### The deny assertion — codify the policy

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
import models.billing.InvoiceInDto;
import io.restassured.response.Response;
import org.apache.http.HttpStatus;
import org.testng.annotations.*;
import security.accesscontrol.InvoiceFixtures.OwnedResource;
import security.accesscontrol.InvoiceFixtures.SeededInvoices;

import java.util.function.Supplier;

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

    @Test(description = "WSTG-ATHZ-04 positive control")
    public void Should_ReturnInvoice_When_OwnerReadsOwn() throws Exception {
        InvoiceDto invoice = InvoicesClient.using(Actor.ALICE.token().get())
            .getById(seeded.alice().id(), HttpStatus.SC_OK);
        assertThat(invoice.amount()).isEqualTo(100);
    }

    @FunctionalInterface
    interface InvoiceCall { Response invoke(InvoicesClient client, String id) throws Exception; }

    private static final InvoiceCall GET = (client, id) -> client.getByIdRaw(id);
    private static final InvoiceCall PUT = (client, id) -> client.updateRaw(id, new InvoiceInDto(1, "EUR"));
    private static final InvoiceCall DELETE = (client, id) -> client.deleteRaw(id);

    @DataProvider(name = "crossUserRows")
    public Object[][] crossUserRows() {
        return new Object[][] {
            { Actor.ALICE, (Supplier<OwnedResource>) () -> seeded.bob(),   GET,    HttpStatus.SC_NOT_FOUND },
            { Actor.ALICE, (Supplier<OwnedResource>) () -> seeded.bob(),   PUT,    HttpStatus.SC_NOT_FOUND },
            { Actor.ALICE, (Supplier<OwnedResource>) () -> seeded.bob(),   DELETE, HttpStatus.SC_NOT_FOUND },
            { Actor.BOB,   (Supplier<OwnedResource>) () -> seeded.alice(), GET,    HttpStatus.SC_NOT_FOUND },
            { Actor.ANON,  (Supplier<OwnedResource>) () -> seeded.alice(), GET,    HttpStatus.SC_UNAUTHORIZED },
        };
    }

    @Test(dataProvider = "crossUserRows")
    public void Should_DenyCrossUserAccess_When_CallerActsOnOthersInvoice(
            Actor caller, Supplier<OwnedResource> target, InvoiceCall call, int expected) throws Exception {
        Response response = call.invoke(InvoicesClient.using(caller.token().get()), target.get().id());

        expectDenied(response, expected);
    }
}
```

The owner-reads-own test is the positive control: the suite is not always-deny. `404` is the cross-user status because this project hides existence across tenants.

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

## Building the matrix from a policy table

An API past a few endpoints expresses the policy once as data and generates the rows (one `PolicyRow` per protected operation) → read `references/policy-matrix.md`.

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
- **Minting a token per test / sleeping for auth.** *Fix:* cache per actor via `test-login-tokens`; never
  `Thread.sleep`.
- **Hardcoding credentials/tokens.** *Fix:* env, read lazily (`System.getenv`).
- **Untagged cases and rowless endpoints.** *Fix:* tag each case with its OWASP API id and WSTG-ATHZ id; a new protected endpoint with no matrix row is a visible coverage gap.
- **Treating a green access-control suite as "access control is secure."** It covers the rows you wrote;
  business-logic abuse (API6) still needs a manual pentest. *Fix:* say so; track endpoint coverage.
