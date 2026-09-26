---
name: qa-api-test-writer-typescript
description: Use when the user asks to write TypeScript API tests using Vitest + native fetch + Zod against a REST backend. Triggers: "write a TS API test for X", "add a Vitest spec for endpoint Y", "automate these test cases in TypeScript". Do NOT use for API tests on the Playwright runner (`qa-api-test-playwright-typescript`), GraphQL or gRPC (`qa-api-test-graphql-typescript` / `qa-api-test-grpc-typescript`), or reviewing tests (`qa-api-test-review-typescript`).
---

# QA — API Test Writer (TypeScript / Vitest + fetch + Zod)

Authors `*.spec.ts` files on top of the **Schema/types + Client + Spec** layering: Zod schemas + inferred types (from `qa/typescript/skills/api-models`), `{resource}Client` factory modules with dual raw + typed methods (from `qa/typescript/skills/api-client-writer`), and spec files — written by this skill — that own scenario selection, test data, and assertions. Mirrors the .NET and Java skills in this folder.

## Stack

- Node 24 + TypeScript (strict mode)
- **Vitest** as the test runner (`vitest`) — the global default for the TS stack
- **Native `fetch`** (built into Node 24) — accessed only through `{resource}Client`; no axios/got/supertest
- **Zod** for request/response schemas and runtime validation — schemas double as the contract check
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
    // no try/catch — a cleanup that fails should fail the hook loudly
    for (const id of createdIds) await client.remove(id);
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
| 404 not found | **raw** | status assert; if the backend returns a `ProblemDetails`-style body, model it via `api-models` and parse it |
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
- **One expected condition per assertion — never an `OR`.** `expect(response.status).toBe(200)`, never `expect([200, 204]).toContain(response.status)` or `expect(s === 200 || s === 204).toBe(true)`; `toBe(400)`, never "400 or 409". The rule covers every assertion, not just status: field values, array lengths, error codes, and response-time budgets are asserted against the single value the test expects. No `||` inside an `expect`, no `toContain`/`toMatch` used to smuggle a set of acceptable values, no `expect.any(...)` where a concrete value is knowable. If two outcomes are both possible, the scenario is under-specified — split it into one `it` per expected outcome, drive it from `it.each([...])`, or establish which value is correct. The only exception is an explicit instruction to accept more than one value; when that happens, state the instruction in a comment on the assertion.
- Parse every 2xx body through the Zod schema (the typed method already does); error bodies are parsed in the spec via `ProblemDetailsSchema.parse(response.bodyJson)`. Never read `response.bodyJson.field` without parsing first; never `JSON.parse` — `baseClient` already populated `bodyJson`.
- Request bodies with 4+ fields come from builders (`qa/typescript/skills/test-data-builder`); simpler bodies use an object literal typed as the InDto.
- Tests are independent: per-test data setup, `afterEach`/`afterAll` cleanup of created entities (no `try/catch` — a failing cleanup should fail the hook loudly), no execution-order assumptions.
- Rows that differ only in data → parameterize via `it.each([...])` (`qa/typescript/skills/data-driven-testing`), never `if`/`for` driving assertions.
- **Never swallow an error, and never write a `try`/`catch` in a spec.** An `it(...)` body contains no catch blocks and no `.catch(...)` on a client call — not around the act, not around the assert, not for cleanup. An unexpected rejection must reach Vitest untouched. An **expected** rejection is asserted, not caught: `await expect(...).rejects.toThrow(...)` is an assertion, not error handling.
- **`afterEach` / `afterAll` get no `try`/`catch` either.** If the cleanup delete rejects, Vitest reports the hook failure and you go fix the leak — that is the system working. A swallowed cleanup failure means the suite quietly leaks data until the environment rots.
- **`try`/`catch` belongs in one place only: a helper that performs I/O**, where converting a specific failure into a useful message *is* the helper's contract (a parse helper, a polling probe). It narrows to the one error it understands, never a blanket catch, and rethrows or reports — it never returns a silent default.
- **Every failure message names the subject and carries the evidence.** `expect(dto.status, \`user ${dto.id} status after activation\`).toBe('active')` — a bare `expected 'pending' to be 'active'` with no id sends the reader hunting through logs for which record it was.
- **A Zod failure explains itself — inside the parse helper, not the spec.** Wrap `safeParse` in a small `parseOrFail(schema, response, label)` helper that, on `!success`, throws with `issues[].path` + `issues[].code` and the raw `response.bodyJson` — so the failure reads "`GET /orders` → `total` expected number, received string" rather than a wall of `ZodError`. Specs call the helper and never `catch` a `ZodError` themselves. Never soften a drifted contract with `.passthrough()` / `.optional()` to make the spec pass — that is a contract-drift **failure**, not a schema bug.

### What NOT to do

- No raw `fetch` in specs — every request goes through a `{resource}Client`. Missing client → `api-client-writer` first.
- No `axios` / `got` / `node-fetch` / `supertest` — native `fetch` only, via the client.
- No `JSON.parse(...)` / `as any` / `Record<string, any>` response parsing in specs — model the shape via `api-models` and `Schema.parse(response.bodyJson)`.
- No `setTimeout`-based waits (`await new Promise(r => setTimeout(r, n))`) — poll on a concrete condition with `vi.waitFor`.
- No missing `await` — every client call and async assertion is awaited; no floating promises.
- No `OR` in any assertion — no `||` inside an `expect`, no `expect([a, b]).toContain(actual)`. One expected value per assertion (see Test rules).
- No `try`/`catch` in a spec or in `afterEach`/`afterAll` — none, for any reason including cleanup; no `.catch(() => {})` anywhere. Expected rejections use `await expect(...).rejects`; catches live only in I/O helpers (see Test rules).
- No `try`/`finally` wrapping a test body for cleanup — track created ids and delete them in `afterEach`.
- No bare Zod failures — report `issues[].path` + `code` and the raw body; never loosen the schema to make a drifted contract pass.
- No inter-test dependencies or shared mutable module-level state.
- No hardcoded base URLs, credentials, or tokens — configuration via `getTestEnvironment()`, tokens via `authHelper`.
- No `// @ts-ignore` / `// eslint-disable` to silence Zod or strict-mode errors — fix the schema or type.

## Generation steps

1. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document, or verbal scenarios. From a spec, derive the scenario set per endpoint (happy, 401, 404, 400 validation, boundary). From a test-case document, map one `it(...)` per TC-ID and carry the id into the title (or `allure.tms`).
2. For each resource in scope, verify the Zod schema + inferred types (`models/{api}/{resource}/`) and the `{resource}Client` exist. Create missing ones via `qa/typescript/skills/api-models` then `qa/typescript/skills/api-client-writer` before writing any spec.
3. Author one spec file per operation, picking patterns from the scenario matrix. Body-manipulation cases (malformed JSON, extra/missing property) require the optional `createRaw` / `createUnchecked` client methods — add them via `api-client-writer`.
4. Verify every test title describes behavior (and carries the TC-ID when a document exists) and asserts one behavior; verify every TC-ID maps to a test or is explicitly deferred.
5. Run the project's own typecheck script (with the package manager `packageManager` names), then `npx vitest run` — expect 0 type errors and 0 failures. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Handoffs

- Schema / type scaffolding → `qa/typescript/skills/api-models`
- Client scaffolding → `qa/typescript/skills/api-client-writer`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Parameterized matrices → `qa/typescript/skills/data-driven-testing`
- Reviewing tests → `qa/typescript/skills/api-test-author/review`
- Allure reporting setup → `qa/reporting/typescript/skills/test-reports`
