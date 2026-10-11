# Deep-dive details — `qa-typescript:api-tests-graphql`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
