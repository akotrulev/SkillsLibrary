---
name: qa-api-test-author-generator-typescript
description: Use when the user asks to scaffold TypeScript API tests against a REST backend using Vitest + native fetch + Zod. Triggers: "write a TS API test for X", "add a Vitest spec for endpoint Y", "scaffold an API client for resource Z", "create a Zod schema for response W". Do NOT use for UI tests (use `qa/ui-test-author/playwright`), the .NET / Java stacks (use the matching generator subdir), or unit tests inside the app under test.
---

# QA — API Test Writer (TypeScript / Vitest + fetch + Zod)

Scaffolds black-box API tests in TypeScript against a deployed REST backend. Uses the **Schema + Client + Spec** layering: Zod schemas model bodies and double as runtime validators, thin `*Client` classes wrap `fetch` for one resource, and `*.spec.ts` files own the assertions. Mirrors the structure of the .NET and Java skills in this folder.

## Stack

- Node 20 + TypeScript (strict mode)
- **Vitest** as test runner (`vitest` + `@vitest/ui` optional) — Jest also works, but defaults below assume Vitest
- **Native `fetch`** (built into Node 20) — no axios/got
- **Zod** for request/response schemas and runtime validation
- **Allure** via `allure-vitest` where the project uses Allure
- Project layout: `tests/clients/`, `tests/schemas/`, `tests/specs/`, `tests/fixtures/`, `tests/setup.ts`

## When to use

- New `*.spec.ts` under `tests/specs/`
- New `*Client.ts` under `tests/clients/` for a new endpoint family
- New Zod schema under `tests/schemas/`
- Adding scenarios (happy path, 4xx, 401) to an existing spec

## When NOT to use

- UI / browser tests → `qa/ui-test-author/playwright`
- .NET API tests → `qa/api-test-author/generator/dotnet`
- Java API tests → `qa/api-test-author/generator/java`
- In-process unit tests of the app under test → out of scope (this skill is for black-box tests against a deployed API)
- Schema-only scaffolding without a test → `qa/api-dto-writer/typescript`

## Inputs needed

1. **Resource** (e.g. `User`, `Order`) — PascalCase
2. **Endpoints** in scope — method, path, headers/auth
3. **Request body shape** and **response body shape** per endpoint
4. **Scenarios** — happy path, 401, 404, 400 validation

## Three layers

### 1. Schema — `tests/schemas/user.ts`

Zod schemas live next to each resource. Export both the schema and the inferred type. The same schema validates response bodies in the spec via `.parse()`.

```typescript
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.number().int().positive(),
  email: z.string().email(),
  firstName: z.string(),
  lastName: z.string(),
  avatar: z.string().url(),
  createdAt: z.string().datetime(),
});
export type User = z.infer<typeof UserSchema>;

export const CreateUserBodySchema = z.object({
  email: z.string().email(),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
});
export type CreateUserBody = z.infer<typeof CreateUserBodySchema>;

export const GetUsersResponseSchema = z.object({
  page: z.number().int(),
  perPage: z.number().int(),
  total: z.number().int(),
  data: z.array(UserSchema),
});
export type GetUsersResponse = z.infer<typeof GetUsersResponseSchema>;

export const ProblemDetailsSchema = z.object({
  type: z.string().optional(),
  title: z.string(),
  status: z.number().int(),
  detail: z.string().optional(),
  errors: z.record(z.array(z.string())).optional(),
  traceId: z.string().optional(),
});
export type ProblemDetails = z.infer<typeof ProblemDetailsSchema>;
```

### 2. Client — `tests/clients/UserClient.ts`

Extends `BaseClient`. One method per endpoint. **Always returns `ApiResponse<T>`** (status + raw body + parsed body) — never throws on 4xx/5xx; the spec decides what's expected.

```typescript
import { BaseClient, ApiResponse } from './BaseClient';
import { CreateUserBody, User, GetUsersResponse } from '../schemas/user';

export class UserClient extends BaseClient {
  constructor(authenticated: boolean) {
    super();
    if (authenticated) {
      this.headers['x-api-key'] = process.env.API_KEY!;
    }
  }

  get(page: number, perPage: number): Promise<ApiResponse<GetUsersResponse>> {
    return this.request('GET', `/users?page=${page}&per_page=${perPage}`);
  }

  getById(id: number): Promise<ApiResponse<User>> {
    return this.request('GET', `/users/${id}`);
  }

  create(body: CreateUserBody): Promise<ApiResponse<User>> {
    return this.request('POST', '/users', body);
  }

  delete(id: number): Promise<ApiResponse<void>> {
    return this.request('DELETE', `/users/${id}`);
  }
}
```

A minimal `BaseClient`:

```typescript
// tests/clients/BaseClient.ts
export type ApiResponse<T> = {
  status: number;
  body: unknown;       // raw — for error assertions
  data?: T;            // present only on 2xx, populated by the spec via schema.parse
};

export abstract class BaseClient {
  protected baseUrl = process.env.API_BASE_URL!;
  protected headers: Record<string, string> = { 'content-type': 'application/json' };

  protected async request<T>(method: string, path: string, body?: unknown): Promise<ApiResponse<T>> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: this.headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await res.text();
    const parsed = text ? JSON.parse(text) : undefined;
    return { status: res.status, body: parsed };
  }
}
```

### 3. Spec — `tests/specs/user.spec.ts`

Owns assertions. Uses the Zod schema to validate AND narrow the type in one step.

```typescript
import { describe, it, expect } from 'vitest';
import { UserClient } from '../clients/UserClient';
import {
  UserSchema,
  GetUsersResponseSchema,
  ProblemDetailsSchema,
} from '../schemas/user';

describe('GET /users', () => {
  it('returns 401 when the api key is invalid', async () => {
    const res = await new UserClient(false).get(1, 12);
    expect(res.status).toBe(401);
  });

  it('returns the first page of users', async () => {
    const res = await new UserClient(true).get(1, 12);

    expect(res.status).toBe(200);
    const body = GetUsersResponseSchema.parse(res.body);
    expect(body.data.length).toBeGreaterThan(0);
    expect(body.page).toBe(1);
  });

  it('returns the same user when fetched by id', async () => {
    const client = new UserClient(true);
    const list = GetUsersResponseSchema.parse((await client.get(1, 10)).body);
    const first = list.data.at(-1)!;

    const res = await client.getById(first.id);

    expect(res.status).toBe(200);
    const fetched = UserSchema.parse(res.body);
    expect(fetched).toEqual(first);
  });
});

describe('POST /users — validation', () => {
  it('returns 400 with field-level errors when email is missing', async () => {
    const res = await new UserClient(true).create({
      email: '',
      firstName: 'A',
      lastName: 'B',
    });

    expect(res.status).toBe(400);
    const problem = ProblemDetailsSchema.parse(res.body);
    expect(problem.title.toLowerCase()).toContain('validation');
    expect(problem.errors).toBeDefined();
    expect(problem.errors!.email?.length).toBeGreaterThan(0);
  });
});
```

## Rules

### Project structure
- Schemas in `tests/schemas/{resource}.ts` — exported `*Schema` + `type *` via `z.infer`
- Clients in `tests/clients/{Resource}Client.ts`, extending `BaseClient`
- Specs in `tests/specs/{resource}.spec.ts`, one `describe` per endpoint or scenario family

### Schema rules
- One Zod schema per JSON shape; never hand-write a TypeScript `interface` that duplicates a schema — infer with `z.infer<typeof Schema>`
- Tighten primitives (`.email()`, `.url()`, `.datetime()`, `.uuid()`, `.int()`, `.min(...)`) so schemas double as runtime contract checks
- Response wrappers (`GetXResponseSchema`) are separate schemas, not inlined in the client
- A shared `ProblemDetailsSchema` lives in `tests/schemas/problem-details.ts` and is reused across resources

### Client rules
- Authentication state is decided in the constructor (`new UserClient(true)` / `new UserClient(false)`), not per call
- One method per endpoint; the method name maps to the HTTP verb plus the action (`get`, `getById`, `create`, `delete`, `update`)
- **Never throws on 4xx/5xx** — return `ApiResponse<T>` with the raw body; the spec decides what's an error
- **Never validates the schema inside the client** — that is the spec's job, because the expected schema differs by status (success body vs `ProblemDetails`)
- Path / query are built with template literals or `URLSearchParams`; no string concatenation across multiple lines

### Spec rules
- Test titles describe behavior: `'returns 401 when the api key is invalid'`, `'returns the first page of users'`, `'returns 400 with field-level errors when email is missing'` — never `'test 1'` or `'works'`
- Always assert the status code first, before parsing the body
- Use the Zod schema to parse and validate in one call: `const body = UserSchema.parse(res.body)`. The parse both narrows the type and catches contract drift.
- For multi-field happy-path checks, group related expectations under one `it(...)` — Vitest does not have a soft-assert equivalent of TestNG's `SoftAssert`; if you need one, use `expect.soft(...)` deliberately and end the test with `expect.assertions(n)` or rely on Vitest reporting all failures
- For 4xx tests, parse with `ProblemDetailsSchema` (or the project's error schema) and assert the `errors`/`type`/`status` fields — never settle for a single `expect(res.status).toBe(400)`
- For 401, a single status-code assertion is enough; auth middleware returns no body in most stacks
- Set the base URL and credentials via env vars (`API_BASE_URL`, `API_KEY`) — never hardcode

### Setup / teardown
- Global setup in `tests/setup.ts` registered via `vitest.config.ts` (`setupFiles: ['./tests/setup.ts']`) — load `.env`, fail fast if `API_BASE_URL` is missing
- For test data created inside a spec, clean it up with `afterEach` / `afterAll` — wrap cleanup in `try/catch` so cleanup errors do not mask test failures
- One Vitest project per environment (`dev`, `staging`) if the suite needs to run against multiple targets

### What NOT to do

- No axios / got / node-fetch — use built-in `fetch` (Node 20+)
- No `expect(res.body).toEqual(...)` against raw bodies for 2xx — always parse with the Zod schema first so the test fails clearly on contract drift
- No throwing inside clients on non-2xx — the spec must be able to assert the failure path
- No `Promise.all` for sequential test steps just to "go faster" — race conditions break independence
- No shared mutable client/test state — each `it(...)` constructs its own client
- No hardcoded `http://localhost:3000` — `process.env.API_BASE_URL` only
- No `// eslint-disable` to silence Zod or strict-mode errors — fix the schema or the type
- No `JSON.parse(res.body as string)` after the client already parsed it — `res.body` is `unknown` and ready for `Schema.parse`
- No `expect(true).toBe(...)` boolean dance — use real matchers
- No conditional logic driving assertions (`if (x) expect(...)`) — use Vitest's `it.each([...])` for parameterized cases

## Generation steps

1. Confirm **resource**, **endpoints**, **scenarios**, and **auth model** with the user.
2. For a new resource:
   - Generate `tests/schemas/{resource}.ts` via `qa/api-dto-writer/typescript` (entity schema, request schemas, response-wrapper schema)
   - Generate `tests/clients/{Resource}Client.ts` — constructor takes `authenticated: boolean`, one method per endpoint
   - Generate `tests/specs/{resource}.spec.ts` — one `describe` block per endpoint family, one `it` per scenario
3. Apply the right template per scenario:
   - **2xx happy path** → status assertion → `Schema.parse(res.body)` → field/equality checks on the parsed object → for create flows, follow with a `getById` round-trip and `expect(fetched).toEqual(created)`
   - **400 validation** → status → `ProblemDetailsSchema.parse(res.body)` → assert `errors[field]` contains the expected message fragment
   - **404 not found** → status → `ProblemDetailsSchema.parse(res.body)` → assert `type`/`title`/error code per the project's contract
   - **401 unauthorized** → single status assertion against a `new XClient(false)` instance
4. If a request body must come from a builder, create one under `tests/fixtures/{resource}.ts` (defer to `qa/test-data-builder` when authored).
5. Run `npx vitest run` — expect 0 failures. If `tsc --noEmit` is wired up, run it too.

## Handoffs

- Schemas / DTOs → `qa/api-dto-writer/typescript`
- Client implementation review or refactor → `qa/api-client-writer`
- Test reviews → `qa/api-test-author/reviewer`
- Test data builders → `qa/test-data-builder`
- Allure reporter setup → `qa/allure-reporting`

## Changelog

- 2026-05-27: Authored. Three-layer Schema (Zod) + Client (`BaseClient` + fetch) + Spec (Vitest) pattern aligned with the .NET and Java skills in this folder.
