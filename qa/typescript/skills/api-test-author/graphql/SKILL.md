---
name: qa-api-test-author-graphql-typescript
description: >-
  Scaffold black-box **GraphQL** API tests in Node 20 / TypeScript with Vitest, native `fetch`, and Zod —
  against a deployed GraphQL endpoint (one `POST /graphql` with `{ query, variables }`). Covers the trait that
  makes GraphQL testing different from REST: **the HTTP status is almost always 200, even on error — you assert
  on the response body's `errors` envelope, not the status code**; `data` and `errors` **coexist** (partial
  success — some fields resolve, others return `null` with an `errors[]` entry naming the `path`); the response
  is **query-shaped** so each operation gets its own Zod schema for the selection set; and **queries / mutations
  / subscriptions each test differently** (query = assert shape+values, mutation = assert result + round-trip
  read, subscription = a stream → `qa-websocket-sse-testing-typescript`). Also covers variables (never
  string-interpolate input into the query), `extensions.code` error assertions, schema introspection, and
  Apollo automatic persisted queries (APQ). Triggers: "write a GraphQL test for query/mutation X", "assert the
  errors array on a GraphQL response", "test partial GraphQL data + errors", "add a Vitest spec for a GraphQL
  endpoint", "test GraphQL introspection / persisted queries". Do NOT use for: REST/JSON endpoints (use
  qa-api-test-author-generator-typescript), the Java stack (use qa-api-test-author-graphql-java), the .NET stack
  (use qa-api-test-author-graphql-dotnet), GraphQL **subscriptions** over WebSocket (use
  qa-websocket-sse-testing-typescript), GraphQL load/N+1 performance (use qa-performance-k6-typescript), UI tests (use
  qa-ui-test-author-playwright-typescript), or generating the typed `data` schema in isolation (use
  qa-api-dto-writer-typescript).
---

# QA — GraphQL API Test Writer (TypeScript / Vitest + fetch + Zod)

Scaffolds black-box API tests in TypeScript against a deployed **GraphQL** backend. It reuses the
**Operation + Client + Spec** layering of the REST sibling (`qa-api-test-author-generator-typescript`) — Zod
schemas model the response and double as runtime validators, a thin client wraps `fetch`, `*.spec.ts` files own
the assertions — but adapts every layer to the one fact that makes GraphQL testing its own discipline: **a
GraphQL response is one HTTP 200 carrying a `{ data, errors }` envelope, and the assertion lives in that
envelope, not in the status line.**

> **The discipline this skill encodes** — four ideas that separate a correct GraphQL test from a REST reflex:
>
> 1. **Status is (almost) always 200 — assert on the body's `errors` field, not the HTTP code.** A GraphQL
>    error surfaces as `{ "errors": [...] }` in a `200 OK` body. `expect(res.status).toBe(400)` is the REST
>    habit and it is **wrong here**. The client must return the raw `{ data, errors }` and **never throw** on a
>    GraphQL error; the spec decides whether errors were expected. (Transport-level failures — a malformed JSON
>    body, auth middleware that rejects before resolving — *can* be non-200; assert those too, but they're the
>    exception.)
> 2. **`data` and `errors` coexist — assert the whole envelope, both branches.** **Partial success** is a
>    first-class GraphQL outcome: some fields resolve into `data` while a failing field is `null` with an entry
>    in `errors[]` whose `path` names it. A real test asserts **both** — the fields that resolved *and* the
>    error (its `path`, its `extensions.code`) — never just one.
> 3. **The response is query-shaped — validate the typed `data` with a per-operation Zod schema.** You get back
>    **exactly the fields you selected**, nothing more. So a response schema models the *operation's selection
>    set*, not a whole resource. Tighten the `errors[]` envelope schema too (`message`, `path`,
>    `extensions.code`).
> 4. **Pick the operation type deliberately — query / mutation / subscription test differently.** A **query**
>    asserts shape + values. A **mutation** asserts the returned payload **and round-trips a read** to prove the
>    change persisted. A **subscription** is a long-lived stream over WebSocket (`graphql-ws`) — that's
>    `qa-websocket-sse-testing-typescript`'s job; cross-link, don't reimplement.

## Decision matrix — operation type → test shape

| Operation | What you're proving | Test shape |
|-----------|---------------------|------------|
| **Query** (read) | The right fields resolve with the right values | `POST { query, variables }` → assert `errors` absent → Zod-parse `data` → field checks |
| **Query — not found / forbidden** | A failure surfaces correctly | status **200** → assert `errors` **present** → assert `errors[0].extensions.code` (`NOT_FOUND`/`FORBIDDEN`) + `data.<field>` is `null` |
| **Query — partial** | Partial success is handled | one resolved field asserted on `data` **and** the failing field's `errors[]` entry asserted by `path` |
| **Mutation** (write) | The change happened and persisted | assert the mutation payload → **round-trip a query** → assert the new state is readable |
| **Mutation — input validation** | Bad input is rejected cleanly | `errors[]` present with `extensions.code === 'BAD_USER_INPUT'` (or the server's code); `data.<field>` null |
| **Subscription** (stream) | Server pushes events over time | **not this skill** → `qa-websocket-sse-testing-typescript` (graphql-ws over WebSocket) |
| **Introspection** | The schema exposes the expected types/fields | query `__schema`/`__type` → assert type & field presence; in prod, assert introspection is **disabled** |
| **Persisted queries (APQ)** | Only registered query hashes execute | hash-only → `PERSISTED_QUERY_NOT_FOUND` → register (query+hash) → hash-only now resolves |

## Stack

- Node 20 + TypeScript (strict mode)
- **Vitest** as test runner (`allure-vitest` where the project uses Allure)
- **Native `fetch`** (Node 20) — no axios/got. A GraphQL request is just a `POST` of `{ query, variables }`.
- **Zod** for the per-operation `data` schema **and** the `errors[]` envelope schema
- Project layout: `tests/operations/` (query/mutation documents), `tests/clients/`, `tests/schemas/`,
  `tests/specs/`, `tests/setup.ts`
- Endpoint + token via env (`GRAPHQL_ENDPOINT`, `GRAPHQL_TOKEN`) — never hardcoded

> **Why plain `fetch` and not `graphql-request`/Apollo?** Typed clients like `graphql-request` **throw a
> `ClientError` when the response contains `errors`** (and `rawRequest` still throws when `data` is null) — which
> makes the *error path* (idea #2) awkward to assert. A black-box test needs the **raw envelope**, errors and
> all. So the canonical client is a thin `fetch` wrapper that never throws on GraphQL errors. If the project
> already uses codegen (GraphQL Code Generator), generate the operation **types** and feed them to the same
> client — keep the envelope-returning behavior.

## Three layers

### 1. Operation — `tests/operations/user.ts`

Operations are **parameterized documents**: the variable values live in a separate `variables` object, **never
interpolated into the query string** (interpolation invites injection and defeats server-side query caching/APQ).
Co-locate the document with its variables type.

```typescript
// tests/operations/user.ts
export const GET_USER = /* GraphQL */ `
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      email
      firstName
      lastName
    }
  }
`;

export const CREATE_USER = /* GraphQL */ `
  mutation CreateUser($input: CreateUserInput!) {
    createUser(input: $input) {
      id
      email
      firstName
      lastName
    }
  }
`;

export type GetUserVars = { id: string };
export type CreateUserInput = { email: string; firstName: string; lastName: string };
```

### 2. Client — `tests/clients/GraphQLBaseClient.ts` + `UserGraphQLClient.ts`

`execute` POSTs `{ query, variables }` and **always returns the raw `{ status, data, errors }`** — it never
throws on a GraphQL error, because the spec decides whether errors are expected.

```typescript
// tests/clients/GraphQLBaseClient.ts
export type GraphQLError = {
  message: string;
  path?: (string | number)[];
  locations?: { line: number; column: number }[];
  extensions?: { code?: string; [k: string]: unknown };
};

export type GraphQLResponse<T> = {
  status: number;            // HTTP — almost always 200, even on a GraphQL error
  data?: T | null;           // present on success AND on partial success
  errors?: GraphQLError[];   // present on full OR partial failure
};

export abstract class GraphQLBaseClient {
  protected endpoint = process.env.GRAPHQL_ENDPOINT!;   // e.g. https://api.example.com/graphql
  protected headers: Record<string, string> = { 'content-type': 'application/json' };

  protected async execute<T>(
    query: string,
    variables?: Record<string, unknown>,
  ): Promise<GraphQLResponse<T>> {
    const res = await fetch(this.endpoint, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ query, variables }),   // variables passed separately — never string-spliced in
    });
    const body = (await res.json()) as { data?: T | null; errors?: GraphQLError[] };
    return { status: res.status, data: body.data, errors: body.errors };
    // NOTE: no throw on body.errors — returning the envelope is the whole point.
  }
}
```

```typescript
// tests/clients/UserGraphQLClient.ts
import { GraphQLBaseClient, GraphQLResponse } from './GraphQLBaseClient';
import { GET_USER, CREATE_USER, CreateUserInput } from '../operations/user';
import { User } from '../schemas/user';

export class UserGraphQLClient extends GraphQLBaseClient {
  constructor(authenticated: boolean) {
    super();
    if (authenticated) this.headers['authorization'] = `Bearer ${process.env.GRAPHQL_TOKEN!}`;
  }

  getUser(id: string): Promise<GraphQLResponse<{ user: User | null }>> {
    return this.execute(GET_USER, { id });
  }

  createUser(input: CreateUserInput): Promise<GraphQLResponse<{ createUser: User }>> {
    return this.execute(CREATE_USER, { input });
  }
}
```

### 3. Schema — `tests/schemas/user.ts`

The `data` schema models the **operation's selection set** (only the fields the query asked for). A shared
`GraphQLErrorSchema` validates the envelope's `errors[]`.

```typescript
// tests/schemas/user.ts
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.string(),               // GraphQL ID serializes as a string
  email: z.string().email(),
  firstName: z.string(),
  lastName: z.string(),
});
export type User = z.infer<typeof UserSchema>;

// data for the GetUser selection set — `user` is nullable (not-found returns null + an errors[] entry)
export const GetUserDataSchema = z.object({ user: UserSchema.nullable() });

// the GraphQL error envelope — reused across every spec
export const GraphQLErrorSchema = z.object({
  message: z.string(),
  path: z.array(z.union([z.string(), z.number()])).optional(),
  locations: z.array(z.object({ line: z.number(), column: z.number() })).optional(),
  extensions: z.object({ code: z.string().optional() }).passthrough().optional(),
});
export const GraphQLErrorsSchema = z.array(GraphQLErrorSchema).min(1);
```

### 4. Spec — `tests/specs/user.spec.ts`

Status first (it's 200 — assert it, but it is *not* the gate), then the **envelope** is the gate.

```typescript
import { describe, it, expect } from 'vitest';
import { UserGraphQLClient } from '../clients/UserGraphQLClient';
import { UserSchema, GetUserDataSchema, GraphQLErrorsSchema } from '../schemas/user';
import { z } from 'zod';

describe('query GetUser', () => {
  it('returns the user when it exists', async () => {
    const res = await new UserGraphQLClient(true).getUser('1');

    expect(res.status).toBe(200);              // GraphQL answers 200 even when wrong — assert, but it's not the gate
    expect(res.errors).toBeUndefined();        // THE gate for a happy path: no errors envelope
    const { user } = GetUserDataSchema.parse(res.data);
    expect(user?.email).toBe('george.bluth@example.com');
  });

  it('returns a NOT_FOUND error (still HTTP 200) for an unknown id', async () => {
    const res = await new UserGraphQLClient(true).getUser('999999');

    expect(res.status).toBe(200);              // NOT a 404 — GraphQL keeps the 200
    const [err] = GraphQLErrorsSchema.parse(res.errors);   // assert on the ENVELOPE
    expect(err.extensions?.code).toBe('NOT_FOUND');
    expect(err.path).toEqual(['user']);        // the error names the field that failed
    expect(res.data?.user).toBeNull();         // data is present; the failing field is null
  });

  it('returns an UNAUTHENTICATED error when the token is missing', async () => {
    const res = await new UserGraphQLClient(false).getUser('1');

    // Two valid server designs: a 200 with an errors[] code, OR a transport 401. Assert the contract you have.
    if (res.status === 200) {
      expect(GraphQLErrorsSchema.parse(res.errors)[0].extensions?.code).toBe('UNAUTHENTICATED');
    } else {
      expect(res.status).toBe(401);
    }
  });
});
```

> The unauthenticated test shows the **one place a GraphQL response legitimately varies its HTTP status** —
> auth middleware may reject at the transport (401) before any resolver runs, or the schema may surface
> `UNAUTHENTICATED` in `errors[]` with a 200. This is the *only* conditional you'll see in these specs; pin it
> to your server's actual contract and delete the branch you don't use.

## Partial response — `data` and `errors` together (idea #2)

A query selecting several fields can **partially succeed**: the authorized fields resolve, a forbidden/erroring
field comes back `null` with an `errors[]` entry pointing at its `path`. Assert **both halves**.

```typescript
const GET_USER_WITH_BILLING = /* GraphQL */ `
  query GetUserWithBilling($id: ID!) {
    user(id: $id) { id email }
    billingProfile(userId: $id) { plan balanceCents }   # requires elevated scope
  }
`;

it('resolves the user but errors on the forbidden billing field', async () => {
  const res = await client.execute(GET_USER_WITH_BILLING, { id: '1' });

  // half 1: the field that DID resolve
  const data = z.object({
    user: z.object({ id: z.string(), email: z.string().email() }),
    billingProfile: z.null(),                  // the forbidden field is null in data
  }).parse(res.data);
  expect(data.user.email).toBe('george.bluth@example.com');

  // half 2: the error that names the field that did NOT resolve
  const [err] = GraphQLErrorsSchema.parse(res.errors);
  expect(err.path).toEqual(['billingProfile']);
  expect(err.extensions?.code).toBe('FORBIDDEN');
});
```

> Asserting only `res.data` would pass while the user silently lost their billing data; asserting only
> `res.errors` would miss that the rest of the query still worked. Partial success demands both.

## Mutation — assert the payload, then round-trip the read (idea #4)

A mutation returns a payload, but the payload alone doesn't prove the write **persisted**. Assert the returned
object, then query it back.

```typescript
it('creates a user and the change is readable', async () => {
  const client = new UserGraphQLClient(true);

  const created = await client.createUser({
    email: 'neo@example.com', firstName: 'Thomas', lastName: 'Anderson',
  });
  expect(created.errors).toBeUndefined();
  const { createUser } = z.object({ createUser: UserSchema }).parse(created.data);
  expect(createUser.email).toBe('neo@example.com');

  // round-trip: prove it persisted, don't trust the mutation's own echo
  const fetched = await client.getUser(createUser.id);
  expect(GetUserDataSchema.parse(fetched.data).user?.email).toBe('neo@example.com');
});

it('rejects invalid input with BAD_USER_INPUT (HTTP 200)', async () => {
  const res = await new UserGraphQLClient(true).createUser({
    email: '', firstName: 'A', lastName: 'B',
  });
  const [err] = GraphQLErrorsSchema.parse(res.errors);
  expect(err.extensions?.code).toBe('BAD_USER_INPUT');
  expect(res.data?.createUser ?? null).toBeNull();
});
```

Clean up data created inside a spec with `afterEach`/`afterAll` (wrap cleanup in `try/catch` so a cleanup error
never masks a test failure) — same discipline as the REST sibling.

## Introspection — assert the schema contract, and that prod disables it

A single introspection query returns the schema's type system. Use it to assert a type/field exists — and, in a
production-config check, to assert introspection is **turned off** (a common hardening requirement: an exposed
schema widens the attack surface).

```typescript
const TYPE_INTROSPECTION = /* GraphQL */ `
  query { __type(name: "User") { name fields { name } } }
`;

it('exposes the email field on the User type', async () => {
  const res = await schemaClient.execute(TYPE_INTROSPECTION);
  const t = z.object({
    __type: z.object({ name: z.string(), fields: z.array(z.object({ name: z.string() })) }).nullable(),
  }).parse(res.data).__type;
  expect(t?.fields.map(f => f.name)).toContain('email');
});

it('has introspection DISABLED in production', async () => {
  const res = await prodSchemaClient.execute(TYPE_INTROSPECTION);
  // hardened servers return an errors[] entry and a null __type rather than the schema
  expect(res.data?.__type ?? null).toBeNull();
  expect(res.errors).toBeDefined();
});
```

## Persisted queries (Apollo APQ) — only registered hashes execute

Automatic Persisted Queries send a **SHA-256 hash** of the operation instead of the full text (smaller requests,
and a server can be locked to *only* known hashes). The deterministic test: a hash-only request for an
unregistered query returns `PERSISTED_QUERY_NOT_FOUND`; sending the full query **with** the hash registers it;
the hash-only request then resolves.

```typescript
import { createHash } from 'node:crypto';

const query = GET_USER;
const sha256Hash = createHash('sha256').update(query).digest('hex');
const persistedQuery = { version: 1 as const, sha256Hash };

it('rejects an unregistered persisted-query hash, then resolves once registered', async () => {
  // 1) hash only, query omitted → server doesn't know it yet
  const miss = await client.executeRaw({ variables: { id: '1' }, extensions: { persistedQuery } });
  expect(GraphQLErrorsSchema.parse(miss.errors)[0].extensions?.code).toBe('PERSISTED_QUERY_NOT_FOUND');

  // 2) register by sending query + hash together
  const reg = await client.executeRaw({ query, variables: { id: '1' }, extensions: { persistedQuery } });
  expect(reg.errors).toBeUndefined();

  // 3) hash only now resolves from the server-side registry
  const hit = await client.executeRaw({ variables: { id: '1' }, extensions: { persistedQuery } });
  expect(GetUserDataSchema.parse(hit.data).user?.id).toBe('1');
});
```

> `executeRaw` is a thin variant of `execute` that forwards `extensions` in the POST body alongside
> `query`/`variables`. The hash must be computed over the **exact** query string the server normalizes on —
> keep one canonical document string per operation (don't reformat it between hashing and sending).

## Anti-patterns

- **Asserting `expect(res.status).toBe(400)` for a GraphQL error.** GraphQL returns **200**; the error is in the
  body. *Fix:* assert `res.errors` is present and check `errors[0].extensions.code`.
- **A client that throws on `errors` (default `graphql-request`/Apollo behavior).** You can't assert the error
  path if the client already threw. *Fix:* the thin `fetch` client returns the raw `{ data, errors }` envelope;
  the spec decides.
- **Asserting only `data` (or only `errors`) on a partial response.** Half the truth. *Fix:* assert the resolved
  field on `data` **and** the failing field's `errors[]` entry by `path`.
- **String-interpolating input into the query** (`` `{ user(id: "${id}") {...} }` ``). Injection risk, breaks
  caching/APQ, and a typed variable would have caught a wrong type at the boundary. *Fix:* always pass
  `variables` separately.
- **Trusting a mutation's echoed payload as proof of persistence.** The resolver can return an object it never
  saved. *Fix:* round-trip a query and assert the new state.
- **A response Zod schema that models the whole resource.** GraphQL returns only the **selected** fields; a
  full-resource schema fails `parse` on the missing ones. *Fix:* model the operation's selection set.
- **`expect(res.errors).toBeDefined()` and stopping there.** "Some error happened" is not a contract. *Fix:*
  assert the specific `extensions.code` and `path`.
- **Reaching for this skill for subscriptions.** A subscription is a WebSocket stream. *Fix:*
  `qa-websocket-sse-testing-typescript` (graphql-ws transport).
- **Hardcoding the endpoint / committing the token.** *Fix:* `process.env.GRAPHQL_ENDPOINT` / `GRAPHQL_TOKEN`,
  read lazily; secrets via `qa-auth0-test-tokens-typescript`.

## Examples

**End-to-end: a not-found query proves the envelope discipline.** A REST author writes
`expect(res.status).toBe(404)` and the test fails because the server answered `200`. The GraphQL-correct version
asserts `res.status === 200`, then `errors[0].extensions.code === 'NOT_FOUND'` and `data.user === null` — the
status line carries no signal; the envelope carries all of it.

**Composing with the REST generator's `ProblemDetails` instinct.** The REST sibling parses `ProblemDetailsSchema`
on a 4xx; here the analogue is `GraphQLErrorsSchema` on a 200 — same "validate the error shape, don't settle for
a status" discipline, different envelope. The two skills share the Schema + Client + Spec spine; only the
transport contract differs.

## Rules (hard constraints)

- **The gate is the `errors` envelope, not the HTTP status.** Assert `res.status === 200` (it documents the
  GraphQL contract) but make `expect(res.errors).toBeUndefined()` (happy) / `GraphQLErrorsSchema.parse(res.errors)`
  (error) the real assertion. The one exception — transport-level auth/parse failures — is pinned explicitly per
  the server's contract, not assumed.
- **The client never throws on a GraphQL error.** `execute` returns `{ status, data, errors }` raw; the spec
  owns what counts as a failure. No `graphql-request`/Apollo throw-on-error in the assertion path.
- **`data` and `errors` are asserted together on partial responses** — the resolved field(s) on `data` **and**
  the failing field's `errors[]` entry by `path`/`extensions.code`. Never assert one half.
- **Operations are parameterized — variables passed separately, never interpolated into the query string.** A
  typed `variables` object; no string-splicing of input.
- **Validate the typed `data` with a per-operation Zod schema** modelling the **selection set**, plus the shared
  `GraphQLErrorSchema` for the envelope. One logical assertion per test; assert specific `extensions.code` +
  `path`, never a bare `errors` presence.
- **A mutation test round-trips a read** to prove persistence; data created in a spec is cleaned up in
  `afterEach`/`afterAll` (cleanup in `try/catch`).
- **Subscriptions are out of scope** → `qa-websocket-sse-testing-typescript`. **Endpoint + token via env**, read
  lazily, never logged. No `waitForTimeout`/sleeps; `strict: true`.

## Cross-references

- `qa-api-test-author-generator-typescript` — the **REST sibling** this extends: the Schema + Client + Spec
  layering, `BaseClient`-over-`fetch`, `ProblemDetailsSchema` (the REST analogue of `GraphQLErrorSchema`), and
  the env/cleanup discipline. Read it for the shared spine.
- `qa-api-test-author-graphql-java` · `qa-api-test-author-graphql-dotnet` — the sibling stacks (RestAssured+TestNG
  treating `/graphql` as a POST · NUnit+RestSharp); same four ideas, different runner/client/assertion libs.
- `qa-websocket-sse-testing-typescript` (#37) — **GraphQL subscriptions** (graphql-ws over WebSocket) live here;
  this skill stops at queries + mutations.
- `qa-api-dto-writer-typescript` — generate the typed `data` Zod schema / operation types (GraphQL Code Generator)
  in isolation; this skill consumes them.
- `qa-auth0-test-tokens-typescript` (#16) — obtain the `GRAPHQL_TOKEN` bearer for authenticated operations.
- `qa-api-mocking-msw-typescript` (#23) — MSW's `graphql.query`/`graphql.mutation` handlers **mock** a GraphQL
  dependency the app under test calls; this skill **tests** a real GraphQL backend. Inverse jobs.
- `qa-performance-k6-typescript` — GraphQL **load** + the **N+1 / DataLoader** performance pitfall; out of scope for this
  functional skill. `qa-allure-reporting-typescript` — each operation renders as a named result.
