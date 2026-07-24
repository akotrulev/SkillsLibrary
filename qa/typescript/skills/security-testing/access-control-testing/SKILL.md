---
name: qa-security-testing-access-control-testing-typescript
description: Use when authoring **functional access-control tests** in Node 24 (22 supported) / TypeScript (Vitest + fetch) that cover the OWASP scanner blind spot — **BOLA/IDOR** (object-level), **BFLA** (function-level), and property-level authorization — driven as an identity x endpoint x object matrix that asserts 403/404 for every unauthorized combination. Maps to OWASP A01:2025 and API1/API3/API5:2023. Triggers "test for IDOR", "check broken object-level authorization", "can user A read user B's records", "build an authorization matrix", "test our role permissions", "cross-tenant leak test". Do NOT use for scanner-driven DAST (use `qa-security-testing-zap-baseline-typescript` or `qa-security-testing-zap-automation-framework`), for minting test identities/tokens (use `qa-auth0-test-tokens-typescript`), or for non-TypeScript projects (use the `{java,dotnet}` siblings).
---

# Security Testing — Access Control / Authorization Matrix (TypeScript / Vitest)

The **canonical** stack for this skill (`qa/{dotnet,java}` siblings port from here). This is the highest-value
security testing most teams are missing, and the one security concern you **cannot** delegate to a scanner.

> **⚠️ Why this is a functional test, not a scan.** A scanner authenticated as Alice has no way to know that
> invoice `42` belongs to Bob — the malicious request `GET /invoices/42` is *perfectly well-formed HTTP*.
> Broken access control is a **logic** flaw, not a **syntax** flaw, so DAST/SAST/fuzzers miss it by design
> (see `qa/_shared/security/SKILL.md` → "the scanner blind spot"). You catch it by writing tests that **act
> as one user against another user's objects and assert the request is denied** — in your normal API test
> framework, reusing your clients, DTOs, and multi-user tokens. OWASP A01:2025 is **#1** and API1/API3/API5
> are three of the API Top 10 for exactly this reason.

## Stack

- Node 20 + TypeScript (strict), **Vitest** as the runner, native `fetch` through the project's
  `{resource}Client` (from `qa/typescript/skills/api-client-writer`) — never a one-off `fetch`.
- Multi-user/role tokens via `qa/typescript/skills/auth0-test-tokens` (ROPG to mint a token *as a specific
  seeded test user*; M2M for service roles). Tokens cached per user, secrets via env read lazily.
- Zod schemas (`qa/typescript/skills/api-dto-writer`) to assert the *owner's* happy path returns the real
  body — proving a test isn't trivially always-deny.
- `it.each` parameterized tables for the matrix (CLAUDE.md: no conditional logic in tests — use parameterized
  tests).

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
and **one elevated role** (Admin) to catch BFLA. Drive the table with `it.each` so every cell is one
independent, named test.

### Fixtures — seeded users and their tokens (cached per user)

```ts
// src/security/access-control/actors.ts
import { getUserToken, getM2MToken } from "../../auth/auth0TestTokens"; // qa/.../auth0-test-tokens

/** A test actor = a seeded identity + a lazily-cached bearer token for it. */
export interface Actor {
  readonly name: string;
  /** Resolve a Bearer token for this actor (cached for its lifetime by the auth0 helper). */
  token(): Promise<string>;
}

// Credentials come from env, read lazily — never inline (CLAUDE.md: no secrets in code).
export const ALICE: Actor = { name: "alice", token: () => getUserToken("ALICE") };
export const BOB:   Actor = { name: "bob",   token: () => getUserToken("BOB") };
export const ADMIN: Actor = { name: "admin", token: () => getUserToken("ADMIN") };
export const ANON:  Actor = { name: "anonymous", token: async () => "" }; // no Authorization header
```

### Seed data each actor owns (builders, not inline literals)

```ts
// src/security/access-control/fixtures.ts
import { invoicesClient } from "../../clients/billing/invoicesClient";
import { ALICE, BOB } from "./actors";

export interface OwnedResource { ownerName: string; id: string; }

/**
 * Create one invoice owned by each peer user, returning their ids. Run once in beforeAll; torn down in
 * afterAll. Each test reads these — no test mutates another's fixture (CLAUDE.md: tests are independent).
 */
export async function seedInvoices(): Promise<{ alice: OwnedResource; bob: OwnedResource }> {
  const alice = await invoicesClient.create(await ALICE.token(), { amount: 100, currency: "EUR" });
  const bob   = await invoicesClient.create(await BOB.token(),   { amount: 200, currency: "EUR" });
  return {
    alice: { ownerName: ALICE.name, id: alice.id },
    bob:   { ownerName: BOB.name,   id: bob.id },
  };
}
```

### The deny helper — codify the policy

```ts
// src/security/access-control/assertDenied.ts
import { expect } from "vitest";
import type { ApiResponse } from "../../clients/http"; // the raw response from {resource}Client

/**
 * Assert a request was DENIED at the configured status, and — critically — that **no resource body leaked**.
 * A 403 that still returns the object in the body is still a BOLA. Pass the project's chosen denial status
 * (403 to deny-and-confirm-existence, 404 to deny-without-disclosure).
 */
export function expectDenied(res: ApiResponse<unknown>, expectedStatus: 401 | 403 | 404): void {
  expect(res.status, "denied requests must use the project's documented status").toBe(expectedStatus);
  // The body must not carry the protected resource. Adjust the predicate to your envelope.
  expect(res.body, "a denied response must not leak the resource body").not.toHaveProperty("amount");
}
```

## BOLA / IDOR — the headline test (horizontal)

```ts
// src/security/access-control/invoices.bola.spec.ts
import { beforeAll, afterAll, describe, it } from "vitest";
import { invoicesClient } from "../../clients/billing/invoicesClient";
import { ALICE, BOB, ANON } from "./actors";
import { seedInvoices, type OwnedResource } from "./fixtures";
import { expectDenied } from "./assertDenied";

describe("API1:2023 BOLA — invoice object-level authorization (WSTG-ATHZ-04)", () => {
  let alice: OwnedResource;
  let bob: OwnedResource;
  beforeAll(async () => { ({ alice, bob } = await seedInvoices()); });
  afterAll(async () => {
    await invoicesClient.delete(await ALICE.token(), alice.id);
    await invoicesClient.delete(await BOB.token(), bob.id);
  });

  // POSITIVE control — the owner CAN read their own invoice. Proves the suite isn't trivially always-deny.
  it("Should_return_invoice_When_owner_reads_own", async () => {
    const res = await invoicesClient.getTyped(await ALICE.token(), alice.id); // getTyped → Schema.parse
    expect(res.amount).toBe(100);
  });

  // The matrix of cross-user / privilege rows. 404 here = this project hides existence cross-tenant.
  it.each([
    { caller: ALICE, target: () => bob,   action: "GET",    expected: 404 as const },
    { caller: ALICE, target: () => bob,   action: "PUT",    expected: 404 as const },
    { caller: ALICE, target: () => bob,   action: "DELETE", expected: 404 as const },
    { caller: BOB,   target: () => alice, action: "GET",    expected: 404 as const },
    { caller: ANON,  target: () => alice, action: "GET",    expected: 401 as const },
  ])(
    "Should_deny_$expected_When_$caller.name_does_$action_on_others_invoice",
    async ({ caller, target, action, expected }) => {
      const token = await caller.token();
      const id = target().id;
      const res =
        action === "GET"    ? await invoicesClient.getRaw(token, id) :
        action === "PUT"    ? await invoicesClient.updateRaw(token, id, { amount: 1 }) :
                              await invoicesClient.deleteRaw(token, id);
      expectDenied(res, expected);
    },
  );
});
```

The `getRaw`/`updateRaw`/`deleteRaw` variants return the `ApiResponse` *without* asserting `200` (that's what
the client's typed methods do) — access-control tests assert the **status themselves**, so use the raw
overloads (see `qa/typescript/skills/api-client-writer`).

## BFLA — function-level (vertical privilege escalation)

```ts
// src/security/access-control/admin.bfla.spec.ts
import { describe, it } from "vitest";
import { adminClient } from "../../clients/admin/adminClient";
import { ALICE, ADMIN } from "./actors";
import { expectDenied } from "./assertDenied";

describe("API5:2023 BFLA — admin-only functions reject regular users (WSTG-ATHZ-02)", () => {
  // POSITIVE control — admin CAN.
  it("Should_list_all_users_When_admin", async () => {
    const res = await adminClient.listUsersRaw(await ADMIN.token());
    expect(res.status).toBe(200);
  });

  it.each([
    { fn: "listUsers",   call: (t: string) => adminClient.listUsersRaw(t) },
    { fn: "deleteUser",  call: (t: string) => adminClient.deleteUserRaw(t, "u_123") },
    { fn: "setUserRole", call: (t: string) => adminClient.setUserRoleRaw(t, "u_123", "admin") },
  ])("Should_deny_403_When_regular_user_calls_admin_$fn", async ({ call }) => {
    expectDenied(await call(await ALICE.token()), 403); // a normal user must not reach admin functions
  });
});
```

## Object Property Level — API3 (mass-assignment & over-read)

```ts
// src/security/access-control/invoices.property.spec.ts
describe("API3:2023 — object property level authorization", () => {
  // Mass-assignment: a client must NOT be able to set a privileged field via the normal write path.
  it("Should_ignore_ownerId_When_user_attempts_mass_assignment", async () => {
    const created = await invoicesClient.createRaw(await ALICE.token(), {
      amount: 50, currency: "EUR", ownerId: BOB.name, // attacker-controlled privileged field
    } as Record<string, unknown>);
    expect(created.status).toBe(201);
    // The server must have ignored ownerId — the invoice belongs to Alice, not Bob.
    const readBack = await invoicesClient.getTyped(await ALICE.token(), (created.body as { id: string }).id);
    expect(readBack.ownerId).not.toBe(BOB.name);
  });

  // Over-read: a sensitive property must not be serialized to a caller who may not see it.
  it("Should_not_expose_internalNotes_When_non_owner_role_reads", async () => {
    const res = await invoicesClient.getRaw(await ALICE.token(), /* a shared, readable id */ "inv_shared");
    expect(res.body).not.toHaveProperty("internalNotes");
  });
});
```

## Building the matrix from a policy table (scales past a few endpoints)

For a real API, express the policy once as data and generate the rows — one source of truth that doubles as
documentation of intended access:

```ts
// src/security/access-control/policy.ts
export interface PolicyRow {
  endpoint: string;                          // for the test name
  call: (token: string, id: string) => Promise<ApiResponse<unknown>>;
  owner: Actor;                              // who may (200)
  others: { actor: Actor; expected: 401 | 403 | 404 }[]; // who may not, and how it's denied
}
// One PolicyRow per protected operation; a small loop emits describe/it.each per row.
// Adding an endpoint = adding a row. A new endpoint with no row is a visible coverage gap.
```

## Anti-patterns

- **Asserting "any 4xx" instead of the policy's exact status.** Hides a `403`-that-leaks-existence when the
  policy is `404`. *Fix:* `expectDenied(res, 404 | 403 | 401)` — pin it.
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
  `waitForTimeout`.
- **Hardcoding credentials/tokens.** *Fix:* env, read lazily.
- **Treating a green access-control suite as "access control is secure."** It covers the rows you wrote;
  business-logic abuse (API6) still needs a manual pentest. *Fix:* say so; track endpoint coverage.

## Rules (hard constraints)

- Cover **BOLA (API1)**, **object-property (API3)**, and **BFLA (API5)** — horizontal *and* vertical
  escalation — plus an anonymous `401` baseline and a **positive control** per resource.
- Assert the **project's documented denial status** (`403` vs `404` leak policy) **and** that **no resource
  body leaks**. One logical assertion per test; test names `Should_X_When_Y`; parameterized matrix via
  `it.each` (no conditional logic in tests).
- Seed **≥2 peer users + 1 elevated role**; each owns its own fixture; tests are independent. Matrix the
  **verbs** (`GET`/`PUT`/`PATCH`/`DELETE`), not just reads.
- Reuse the project's `{resource}Client` **raw** overloads (status asserted by the test) and
  `qa/typescript/skills/auth0-test-tokens` for per-actor tokens (cached, secrets via env read lazily).
- Tag cases with their **OWASP API id** and **WSTG-ATHZ** test-id; a new protected endpoint with no matrix
  row is a visible coverage gap. A green suite ≠ "secure" — business-logic abuse needs manual pentest.

## Cross-references

- `qa/_shared/security/SKILL.md` — the OWASP backbone + the scanner-blind-spot rationale; **load alongside**.
- `qa/{dotnet,java}/skills/security-testing/access-control-testing` — the NUnit / TestNG ports of this
  canonical skill.
- `qa/typescript/skills/auth0-test-tokens` — mint per-actor tokens (ROPG as a specific test user; M2M for
  service roles), cached for their lifetime.
- `qa/typescript/skills/api-client-writer` / `api-dto-writer` — the `{resource}Client` raw/typed overloads
  and Zod schemas the matrix reuses.
- `qa/typescript/skills/api-test-author/generator` — generic functional API tests (this skill is the
  authorization slice of the same suite).
- `qa/_shared/security-testing/api-fuzzing` — complementary spec-driven fuzzing (finds malformed-input bugs;
  does **not** find BOLA).
- `qa/manual/bug-report-writer` — write up a confirmed BOLA/BFLA with the caller, target object, and response.
