---
name: api-tests
description: Use when writing TypeScript REST API tests with Vitest + fetch + Zod. Triggers "write an API test for X", "automate these test cases". Not for Playwright-runner API tests (api-tests-playwright).
disable-model-invocation: true
---

# QA — API Test Writer (TypeScript / Vitest + fetch + Zod)

Authors `*.spec.ts` files on top of the **Schema/types + Client + Spec** layering: Zod schemas + inferred types (from `qa/typescript/skills/api-models`), `{resource}Client` factory modules with dual raw + typed methods (from `qa/typescript/skills/api-client-writer`), and spec files — written by this skill — that own scenario selection, test data, and assertions. Mirrors the .NET and Java skills in this folder.

## Stack

- Node 24 + TypeScript (strict mode)
- **Vitest** as the test runner (`vitest`) — the global default for the TS stack
- **Native `fetch`** (built into Node 24) — accessed only through `{resource}Client`; no axios/got/supertest
- **Zod** for request/response schemas and runtime validation — schemas double as the contract check; response object schemas are `.strict()`, so a field the contract does not declare fails the parse
- **Allure** via `allure-vitest` where the project uses Allure
- Project layout: `src/clients/{api}/`, `src/models/{api}/{resource}/`, `src/specs/{api}/{resource}/`, `src/config/`, `tests/setup.ts`

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `models/{api}/{resource}/{resource}.schema.ts` (Zod) + `.types.ts` (`z.infer`) | `qa/typescript/skills/api-models` | Body shapes, JSON-key mapping, runtime validation |
| `clients/{api}/{resource}Client.ts` | `qa/typescript/skills/api-client-writer` | Request building; raw `ApiResponse` method + typed method (asserts status, `Schema.parse`) |
| `specs/{api}/{resource}/{operation}{Resource}.spec.ts` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

This skill writes **only the spec files**. If a schema/type or client a test needs is missing, run the owner skill first — never call `fetch` directly or inline a one-off client to avoid generating one.

## When to use

- New `{operation}{Resource}.spec.ts` for an endpoint that has (or will get) a client
- Adding scenarios to an existing spec
- Automating cases from a `qa/manual/test-case-writer` document or an OpenAPI/Swagger spec

## When NOT to use

- UI / browser tests → `qa/typescript/skills/ui-test-author/playwright`
- .NET API tests → `qa/dotnet/skills/api-test-author/writer`
- Java API tests → `qa/java/skills/api-test-author/writer`
- GraphQL / gRPC → the protocol siblings under `qa/typescript/skills/api-test-author/`
- Schema/type-only scaffolding → `qa/typescript/skills/api-models`
- Client-only scaffolding → `qa/typescript/skills/api-client-writer`
- Reviewing existing tests → `qa/typescript/skills/api-test-author/review`
- A new project from zero (layout, pins, config loader, base client) → `qa/typescript/skills/api-project-setup`

## Inputs needed

1. **Source of truth** — one of: an OpenAPI/Swagger spec, a formal test-case document (TC-IDs), or a verbal scenario list. When a spec or test-case document is provided, derive resources, endpoints, body shapes, and scenarios from it — do not re-ask.
2. **Resource(s) and endpoints in scope** — method, path, auth requirements
3. **Auth model** — which test user / token each scenario needs (token from that user's provider, `testUserTokens.getAccessToken()`, passed into the client factory)
4. **Scenarios** — happy path, 401/403, 404, 400 validation, boundary/edge; the CRUD or the read-only/search set below

## Spec template

Specs live at `src/specs/{api}/{resource}/`, one file per operation. Each `it(...)` builds its own client from a token the spec fetches through the token providers `qa/typescript/skills/test-login-tokens` generates (`src/auth/tokens.ts`, one cached provider per test user); `''` builds an unauthenticated client.

```ts
import { describe, it, expect } from 'vitest';
import { createUserClient } from '../../../clients/user/userClient.js';
import { testUserTokens } from '../../../auth/tokens.js';

describe('GET /api/users', () => {
  it('TC-USER-002: returns 401 when the token is missing', async () => {
    const response = await createUserClient('').getAll();

    expect(response.status).toBe(401);
  });

  it('TC-USER-004: returns 404 when the user does not exist', async () => {
    const client = createUserClient(await testUserTokens.getAccessToken());

    const response = await client.getById('999999');

    expect(response.status).toBe(404);
  });
});
```

## Setup and cleanup

The default: a test creates what it changes, with a value unique to it, and registers the id for teardown in `afterEach`. No `try`/`catch` in the hook: a cleanup that fails fails the hook loudly.

```ts
import { describe, it, expect, afterEach } from 'vitest';
import { createUserClient } from '../../../clients/user/userClient.js';
import { adminTokens } from '../../../auth/tokens.js';
import { ProblemDetailsSchema } from '../../../models/user/users/user.types.js';
import { validUser } from '../../../builders/user.js';

describe('POST /api/users', () => {
  const createdIds: string[] = [];

  afterEach(async () => {
    const client = createUserClient(await adminTokens.getAccessToken());
    for (const id of createdIds.splice(0)) await client.remove(id);
  });

  it('TC-USER-010: creates a user when the body is valid', async () => {
    const client = createUserClient(await adminTokens.getAccessToken());
    const body = validUser().build();

    const created = await client.createTyped(body, 201);
    createdIds.push(String(created.id));

    const stored = await client.getByIdTyped(String(created.id), 200);
    expect(stored).toEqual(created);
  });

  it('TC-USER-011: returns 400 with a field error when email is missing', async () => {
    const client = createUserClient(await adminTokens.getAccessToken());
    const body = validUser().email(null).build();

    const response = await client.create(body);

    expect(response.status).toBe(400);
    const problem = ProblemDetailsSchema.parse(response.bodyJson);
    expect(problem.errors?.email?.length).toBeGreaterThan(0);
  });
});
```

Three more data patterns are sanctioned (`test-data.md`); pick per spec, never per test by a branch:

- **Read-only reference data.** A read or search spec may use curated records already in the environment, named in the spec (a constant from `src/mothers/reference.ts`), never modified. The spec asserts the result is not empty before asserting on its items.
- **Pre-clean.** When a test needs a fixed natural key (an email, an external reference), `beforeEach` removes a leftover through the seeder first, `await userSeeder.deleteByEmail(email)`, so a crashed run cannot poison the next. Teardown still runs.
- **Keep on failure.** A suite that keeps a failed test's records for investigation deletes in `afterEach` only when the test passed: `afterEach(async ({ task }) => …)` reads `task.result?.state`, deletes on `'pass'` and logs the kept ids otherwise. That check belongs to the one teardown function the suite shares, the legal infrastructure branch; names are then unique per run (`randomUUID()`).

## Scenario sets

### CRUD (a resource the suite writes)

| Scenario | How it is proven |
|---|---|
| Create | typed create, then a GET reads it back and is compared with the created DTO (`toEqual`) |
| Update one field | one test per changed field: clone the seeded body, change that field (`{ ...seeded, email: 'new@example.test' }`), PUT or PATCH it, and GET it back; the changed field has the new value and the rest are unchanged |
| Full update | where the DTO has value equality (a plain Zod-parsed object), compare the whole object read back with the sent one, `expect(stored).toEqual({ ...sent, id })`, never field by field |
| Delete | the delete returns its exact status, then a following GET of the same id returns `404` |

### Read-only and search (a resource the suite only reads)

| Scenario | How it is proven |
|---|---|
| Page size | `search({ pageSize: 5 })` returns exactly 5 items, against reference data known to hold more than 5 |
| Filter | the result is not empty, then the filter holds on every item: `expect(items.filter((i) => i.status !== 'Shipped'), 'items not Shipped').toEqual([])` (one assertion over the whole list, the offenders as evidence) |
| Get by id | the item fetched by id equals the same item in the list (`toEqual`) |

```ts
describe('GET /api/orders (search)', () => {
  it('TC-ORD-021: returns only shipped orders when filtered by status', async () => {
    const client = createOrderClient(await testUserTokens.getAccessToken());
    const params = new OrderSearchParamsBuilder().status('Shipped').placedFrom(ReferenceOrders.januaryShipped.placedFrom).build();

    const page = await client.searchTyped(params, 200);

    expect(page.items.length, 'orders returned for the shipped filter').toBeGreaterThan(0);
    expect(page.items.filter((order) => order.status !== 'Shipped'), 'orders not Shipped').toEqual([]);
  });
});
```

The parameter object comes from a typed builder (`test-data-builder`, "Typed query-parameter builder"), never positional strings.

## Scenario → pattern matrix

| Scenario | Client method | Assertion pattern |
|----------|---------------|-------------------|
| 2xx happy path | **typed** (`…Typed(…, expectedStatus)`) | DTO returned already status-asserted + Zod-validated (a strict schema, so an undeclared field fails the parse); verify fields with `expect.soft(...)` |
| 401 unauthorized | **raw** on a client built with `''` jwt | single `expect(response.status).toBe(401)` |
| 403 forbidden | **raw** on a client built with a wrong-role token | single `expect(response.status).toBe(403)` |
| 404 not found | **raw** | status assert; if the backend returns a `ProblemDetails`-style body, model it via `api-models` and parse it |
| 400 validation | **raw** | status assert + `ProblemDetailsSchema.parse(response.bodyJson)`; assert the field key in `errors` |
| Malformed JSON / extra-missing property | **raw** via `createRaw(string)` / `createUnchecked(Record<string, unknown>)` | status assert only — add these methods via `api-client-writer` when the plan requires them |

## Spec structure & naming

- Specs go in `src/specs/{api}/{resource}/`; one file per operation: `{operation}{Resource}.spec.ts` (e.g. `getUser.spec.ts`, `postUser.spec.ts`).
- One `describe(...)` per endpoint or scenario family; titles read like behavior sentences. When a test-case document drives generation, prefix the title with the TC-ID (`'TC-USER-001: returns all users when authorized'`) so Allure traces test → case — or call `allure.tms('TC-USER-001', '<link>')` where `allure-vitest` is wired.
- Each `it(...)` builds its own client; tokens come from the per-user providers (`test-login-tokens`), never read inside the client. Never reassign module-level state across tests.

## Generation checks

Two checks bracket the code, both in [`references/generation-checks.md`](references/generation-checks.md):
**oracles first** — a scenario × oracle table (response, data, negative, side effect), taken from the
contract or the requirement and never from the code, before any test is written; and a **hallucination gate**
after — every endpoint (and test id) the new tests use is looked up in the stored OpenAPI spec (and the app
source) and reported `MISSING` instead of guessed.

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md`, `api-tests.md` and `test-data.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Generation steps

1. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document, or verbal scenarios. From a spec, derive the scenario set per endpoint (happy, 401, 404, 400 validation, boundary) plus the CRUD or read-only/search set. From a test-case document, map one `it(...)` per TC-ID and carry the id into the title (or `allure.tms`).
2. Write the scenario × oracle table (`references/generation-checks.md` §1) — no test code before it exists.
3. For each resource in scope, verify the Zod schema + inferred types (`models/{api}/{resource}/`) and the `{resource}Client` exist. Create missing ones via `qa/typescript/skills/api-models` then `qa/typescript/skills/api-client-writer` before writing any spec.
4. Author one spec file per operation, picking patterns from the scenario matrix. Body-manipulation cases (malformed JSON, extra/missing property) require the optional `createRaw` / `createUnchecked` client methods — add them via `api-client-writer`.
5. Verify every test title describes behavior (and carries the TC-ID when a document exists) and asserts one behavior; verify every TC-ID maps to a test or is explicitly deferred.
6. Run the hallucination gate (`references/generation-checks.md` §2); report every `MISSING` endpoint and write no test against it.
7. Run the project's own typecheck script (with the package manager `packageManager` names), then `npx vitest run` — expect 0 type errors and 0 failures.

## Handoffs

- Schema / type scaffolding → `qa/typescript/skills/api-models`
- Client scaffolding → `qa/typescript/skills/api-client-writer`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Parameterized matrices → `qa/typescript/skills/data-driven-testing`
- Reviewing tests → `qa/typescript/skills/api-test-author/review`
- Allure reporting setup → `qa/reporting/typescript/skills/test-reports`
