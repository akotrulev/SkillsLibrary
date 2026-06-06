---
name: qa-api-test-author-generator-typescript
description: Use when the user asks to write TypeScript API tests using Vitest + native fetch + Zod against a REST backend — from an OpenAPI/Swagger spec, a formal test-case document, or a verbal scenario list. Triggers: "write a TS API test for X", "add a Vitest spec for endpoint Y", "automate these test cases in TypeScript", "generate API tests from this swagger". Do NOT use for UI tests (use `qa/typescript/skills/ui-test-author/playwright`), for the .NET / Java stacks (use the matching generator subdir), for GraphQL/gRPC (use the protocol siblings), or for writing the schema/DTO or client layers themselves (use `qa/typescript/skills/api-dto-writer` / `qa/typescript/skills/api-client-writer`).
---

# QA — API Test Writer (TypeScript / Vitest + fetch + Zod)

Authors `*.spec.ts` files on top of the **Schema/types + Client + Spec** layering: Zod schemas + inferred types (from `qa/typescript/skills/api-dto-writer`), `{resource}Client` factory modules with dual raw + typed methods (from `qa/typescript/skills/api-client-writer`), and spec files — written by this skill — that own scenario selection, test data, and assertions. Mirrors the .NET and Java skills in this folder.

## Stack

- Node 20 + TypeScript (strict mode)
- **Vitest** as the test runner (`vitest`) — the global default for the TS stack
- **Native `fetch`** (built into Node 20) — accessed only through `{resource}Client`; no axios/got/supertest
- **Zod** for request/response schemas and runtime validation — schemas double as the contract check
- **Allure** via `allure-vitest` where the project uses Allure
- Project layout: `src/clients/{api}/`, `src/models/{api}/{resource}/`, `src/specs/{api}/{resource}/`, `src/config/`, `tests/setup.ts`

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `models/{api}/{resource}/{resource}.schema.ts` (Zod) + `.types.ts` (`z.infer`) | `qa/typescript/skills/api-dto-writer` | Body shapes, JSON-key mapping, runtime validation |
| `clients/{api}/{resource}Client.ts` | `qa/typescript/skills/api-client-writer` | Request building; raw `ApiResponse` method + typed method (asserts status, `Schema.parse`) |
| `specs/{api}/{resource}/{operation}{Resource}.spec.ts` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

This skill writes **only the spec files**. If a schema/type or client a test needs is missing, run the owner skill first — never call `fetch` directly or inline a one-off client to avoid generating one.

## When to use

- New `{operation}{Resource}.spec.ts` for an endpoint that has (or will get) a client
- Adding scenarios to an existing spec
- Automating cases from a `qa/manual/test-case-writer` document or an OpenAPI/Swagger spec

## When NOT to use

- UI / browser tests → `qa/typescript/skills/ui-test-author/playwright`
- .NET API tests → `qa/dotnet/skills/api-test-author/generator`
- Java API tests → `qa/java/skills/api-test-author/generator`
- GraphQL / gRPC → the protocol siblings under `qa/typescript/skills/api-test-author/`
- Schema/type-only scaffolding → `qa/typescript/skills/api-dto-writer`
- Client-only scaffolding → `qa/typescript/skills/api-client-writer`
- Reviewing existing tests → `qa/typescript/skills/api-test-author/reviewer`

## Inputs needed

1. **Source of truth** — one of: an OpenAPI/Swagger spec, a formal test-case document (TC-IDs), or a verbal scenario list. When a spec or test-case document is provided, derive resources, endpoints, body shapes, and scenarios from it — do not re-ask.
2. **Resource(s) and endpoints in scope** — method, path, auth requirements
3. **Auth model** — which test user / token each scenario needs (token fetched via `authHelper`, passed into the client factory)
4. **Scenarios** — happy path, 401/403, 404, 400 validation, boundary/edge

## Spec template

Specs live at `src/specs/{api}/{resource}/`, one file per operation. Each `it(...)` builds its own client from a token fetched via `authHelper`; `''` builds an unauthenticated client.

```ts
import { describe, it, expect, afterEach } from 'vitest';
import { createUserClient } from '../../../clients/user/userClient.js';
import { authHelper, TestUsers } from '../../../clients/authHelper.js';
import { UserSchema } from '../../../models/user/users/user.types.js';

describe('GET /api/users', () => {
  it('TC-USER-001: returns all users when authorized', async () => {
    const client = createUserClient(await authHelper.getToken(TestUsers.STANDARD));

    const users = await client.getAllTyped(200);

    expect(users.length).toBeGreaterThan(0);
  });

  it('TC-USER-002: returns 401 when the token is missing', async () => {
    const response = await createUserClient('').getAll();

    expect(response.status).toBe(401);
  });

  it('TC-USER-003: returns the matching user when fetched by id', async () => {
    const client = createUserClient(await authHelper.getToken(TestUsers.STANDARD));
    const fromList = (await client.getAllTyped(200)).at(-1)!;

    const fetched = await client.getByIdTyped(String(fromList.id), 200);

    expect.soft(fetched.id).toBe(fromList.id);
    expect.soft(fetched.email).toBe(fromList.email);
  });

  it('TC-USER-004: returns 404 when the user does not exist', async () => {
    const client = createUserClient(await authHelper.getToken(TestUsers.STANDARD));

    const response = await client.getById('999999');

    expect(response.status).toBe(404);
  });
});
```

For create/update flows, track created ids and clean them up in `afterEach` (wrapped so cleanup never masks a test failure):

```ts
import { describe, it, expect, afterEach } from 'vitest';
import { createUserClient } from '../../../clients/user/userClient.js';
import { authHelper, TestUsers } from '../../../clients/authHelper.js';
import { UserSchema, ProblemDetailsSchema } from '../../../models/user/users/user.types.js';
import { validUser } from '../../../fixtures/user.js';

describe('POST /api/users', () => {
  const createdIds: string[] = [];

  afterEach(async () => {
    const client = createUserClient(await authHelper.getToken(TestUsers.ADMIN));
    for (const id of createdIds) {
      try { await client.remove(id); } catch { /* cleanup must not mask failures */ }
    }
    createdIds.length = 0;
  });

  it('TC-USER-010: creates a user when the body is valid', async () => {
    const client = createUserClient(await authHelper.getToken(TestUsers.ADMIN));
    const body = validUser().build(); // builder — see qa/typescript/skills/test-data-builder

    const created = await client.createTyped(body, 201);
    createdIds.push(String(created.id));

    expect.soft(created.email).toBe(body.email);
    expect.soft(created.firstName).toBe(body.firstName);
  });

  it('TC-USER-011: returns 400 with a field error when email is missing', async () => {
    const client = createUserClient(await authHelper.getToken(TestUsers.ADMIN));
    const body = validUser().email(null).build();

    const response = await client.create(body);

    expect(response.status).toBe(400);
    const problem = ProblemDetailsSchema.parse(response.bodyJson);
    expect(problem.errors?.email?.length).toBeGreaterThan(0);
  });
});
```

## Scenario → pattern matrix

| Scenario | Client method | Assertion pattern |
|----------|---------------|-------------------|
| 2xx happy path | **typed** (`…Typed(…, expectedStatus)`) | DTO returned already status-asserted + Zod-validated; verify fields with `expect.soft(...)` |
| 401 unauthorized | **raw** on a client built with `''` jwt | single `expect(response.status).toBe(401)` |
| 403 forbidden | **raw** on a client built with a wrong-role token | single `expect(response.status).toBe(403)` |
| 404 not found | **raw** | status assert; if the backend returns a `ProblemDetails`-style body, model it via `api-dto-writer` and parse it |
| 400 validation | **raw** | status assert + `ProblemDetailsSchema.parse(response.bodyJson)`; assert the field key in `errors` |
| Malformed JSON / extra-missing property | **raw** via `createRaw(string)` / `createUnchecked(Record<string, unknown>)` | status assert only — add these methods via `api-client-writer` when the plan requires them |

## Rules

### Spec structure & naming

- Specs go in `src/specs/{api}/{resource}/`; one file per operation: `{operation}{Resource}.spec.ts` (e.g. `getUser.spec.ts`, `postUser.spec.ts`).
- One `describe(...)` per endpoint or scenario family; titles read like behavior sentences. When a test-case document drives generation, prefix the title with the TC-ID (`'TC-USER-001: returns all users when authorized'`) so Allure traces test → case — or call `allure.tms('TC-USER-001', '<link>')` where `allure-vitest` is wired.
- Each `it(...)` builds its own client; tokens come from `authHelper`, never read inside the client. Never reassign module-level state across tests.

### Test rules

- Always assert the status code before reading the body — the typed method does this for you; raw responses get an explicit `expect(response.status).toBe(...)` first.
- Happy path uses the **typed** method; negative scenarios use the **raw** method. Never re-assert the status after a typed call.
- One logical behavior per test. Use `expect.soft(...)` for multiple fields of one response so Vitest reports every mismatch; never assert multiple unrelated behaviors in one `it`.
- Parse every 2xx body through the Zod schema (the typed method already does); error bodies are parsed in the spec via `ProblemDetailsSchema.parse(response.bodyJson)`. Never read `response.bodyJson.field` without parsing first; never `JSON.parse` — `baseClient` already populated `bodyJson`.
- Request bodies with 4+ fields come from builders (`qa/typescript/skills/test-data-builder`); simpler bodies use an object literal typed as the InDto.
- Tests are independent: per-test data setup, `afterEach`/`afterAll` cleanup of created entities wrapped in `try/catch`, no execution-order assumptions.
- Rows that differ only in data → parameterize via `it.each([...])` (`qa/typescript/skills/data-driven-testing`), never `if`/`for` driving assertions.

### What NOT to do

- No raw `fetch` in specs — every request goes through a `{resource}Client`. Missing client → `api-client-writer` first.
- No `axios` / `got` / `node-fetch` / `supertest` — native `fetch` only, via the client.
- No `JSON.parse(...)` / `as any` / `Record<string, any>` response parsing in specs — model the shape via `api-dto-writer` and `Schema.parse(response.bodyJson)`.
- No `setTimeout`-based waits (`await new Promise(r => setTimeout(r, n))`) — poll on a concrete condition with `vi.waitFor`.
- No missing `await` — every client call and async assertion is awaited; no floating promises.
- No inter-test dependencies or shared mutable module-level state.
- No hardcoded base URLs, credentials, or tokens — configuration via `getTestEnvironment()`, tokens via `authHelper`.
- No `// @ts-ignore` / `// eslint-disable` to silence Zod or strict-mode errors — fix the schema or type.

## Generation steps

1. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document, or verbal scenarios. From a spec, derive the scenario set per endpoint (happy, 401, 404, 400 validation, boundary). From a test-case document, map one `it(...)` per TC-ID and carry the id into the title (or `allure.tms`).
2. For each resource in scope, verify the Zod schema + inferred types (`models/{api}/{resource}/`) and the `{resource}Client` exist. Create missing ones via `qa/typescript/skills/api-dto-writer` then `qa/typescript/skills/api-client-writer` before writing any spec.
3. Author one spec file per operation, picking patterns from the scenario matrix. Body-manipulation cases (malformed JSON, extra/missing property) require the optional `createRaw` / `createUnchecked` client methods — add them via `api-client-writer`.
4. Verify every test title describes behavior (and carries the TC-ID when a document exists) and asserts one behavior; verify every TC-ID maps to a test or is explicitly deferred.
5. Run `pnpm exec tsc --noEmit` then `npx vitest run` — expect 0 type errors and 0 failures.

## Handoffs

- Schema / type scaffolding → `qa/typescript/skills/api-dto-writer`
- Client scaffolding → `qa/typescript/skills/api-client-writer`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Parameterized matrices → `qa/typescript/skills/data-driven-testing`
- Reviewing tests → `qa/typescript/skills/api-test-author/reviewer`
- Allure reporting setup → `qa/typescript/skills/allure-reporting`
