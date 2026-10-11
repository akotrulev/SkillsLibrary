---
name: api-client-writer
description: Use when the user asks to create a new API client module (`{resource}Client.ts`) in a TypeScript API test project (Vitest + native `fetch` + Zod, Node 24 (22 supported), strict TS). Triggers: "write an API client for X", "add a {resource}Client", "scaffold the TS client for /api/{path}". Do NOT use for the Zod schemas / DTO types (`qa-typescript:api-models`) or the specs that call the client (`qa-typescript:api-tests`).
---

# qa-typescript:api-client-writer

Generator skill. Scaffolds a single `{resource}Client.ts` file in the TypeScript API test project under `src/clients/{api}/`, following the conventions below. Uses **native `fetch`** (built into Node 22 and 24) and **Zod** for response validation.

## When to use

- The user asks to add a new client module under `src/clients/{api}/`.
- A new endpoint group has been added to the API under test and needs a typed wrapper for tests.
- The user is extending an existing client with new endpoints in the same style.

## When NOT to use

- Writing the test spec — use `qa/typescript/skills/api-test-author/writer`.
- Reviewing an existing client for convention drift — use `qa/typescript/skills/api-test-author/review`.
- Authoring Zod schemas / DTO types — use `qa/typescript/skills/api-models` first.
- Reacting to a **new version of a swagger/OpenAPI spec** — start at `qa/_shared/api-spec-assets` (`qa-<stack>:api-spec-assets`): it replaces the stored spec asset in place and derives from `git diff` exactly which client methods changed. Come back here for those methods only.
- .NET stack (RestSharp) — use `qa/dotnet/skills/api-client-writer`.
- Java stack (RestAssured) — use `qa/java/skills/api-client-writer`.
- Projects standardized on axios / got / supertest — these conventions assume native `fetch`.

## Folder & naming convention

Clients are organized by API group. **One module per resource**; user-facing and admin operations live in the same module. Each module exports a factory function that returns a strongly-typed client object — no class-per-client unless the project explicitly prefers classes.

```
src/
├── clients/
│   ├── baseClient.ts                 ← shared fetch wrapper, auth, logging
│   ├── authHelper.ts
│   ├── authConfigClient.ts           ← root, unauthenticated
│   └── {api}/
│       └── {resource}Client.ts       ← one file per resource
├── config/
│   └── environment.ts
└── models/
    └── {api}/
        └── {resource}/
            ├── {resource}.schema.ts  ← Zod schema
            └── {resource}.types.ts   ← inferred TS types
```

### API group reference

| API Group  | Clients                                                            |
|------------|--------------------------------------------------------------------|
| user       | userClient, kycClient, consentClient, preferencesClient            |
| assessment | assessmentClient                                                   |
| legal      | documentClient                                                     |
| reference  | referenceClient                                                    |
| auth       | authConfigClient (root, unauthenticated)                           |

When a resource has both user-facing (`/api/{resource}/...`) and admin (`/api/management/{resource}/...`) endpoints, both live in the same module. Distinguish them via the path constants (e.g. `GET_ALL_PATH` vs `GET_ALL_MANAGEMENT_PATH`).

## Dual-method pattern

Every endpoint that returns a DTO gets **two methods**:

1. **Raw** — returns `ApiResponse` (the shared envelope: `{ status: number; headers: Headers; bodyText: string; bodyJson: unknown }`). No assertion, no schema validation. Used in negative tests where the caller asserts the status.
2. **Typed** — same input, plus a trailing `expectedStatus: number` argument. Calls the raw method, asserts the status via Vitest `expect`, parses the body with the Zod schema, and returns the typed DTO. Used for happy-path convenience.

```ts
// Raw — caller handles assertion and parsing.
async function getById(id: string): Promise<ApiResponse> {
  return execute({
    method: 'GET',
    path: GET_BY_ID_PATH.replace('{id}', encodeURIComponent(id)),
  });
}

// Typed — asserts status, validates with Zod, returns DTO.
async function getByIdTyped(id: string, expectedStatus: number): Promise<ResourceDto> {
  const response = await getById(id);
  expect(response.status).toBe(expectedStatus);
  return ResourceSchema.parse(response.bodyJson);
}
```

Endpoints with **no response body** (DELETE → 204, PATCH → 204) get only the raw method.

## Template

```ts
import { z } from 'zod';
import { expect } from 'vitest';
import { createBaseClient, type ApiResponse } from '../baseClient.js';
import { getTestEnvironment } from '../../config/environment.js';
import {
  ResourceSchema,
  ResourceListSchema,
  type ResourceDto,
  type ResourceInDto,
  type ResourceModDto,
} from '../../models/{api}/{resource}/{resource}.types.js';

// User-facing endpoints
const GET_ALL_PATH   = '/api/{basePath}';
const GET_BY_ID_PATH = '/api/{basePath}/{id}';
const POST_PATH      = '/api/{basePath}';

// Management endpoints (only when this resource exposes admin operations)
const GET_ALL_MANAGEMENT_PATH = '/api/management/{basePath}';
const PUT_MANAGEMENT_PATH     = '/api/management/{basePath}/{id}';
const PATCH_MANAGEMENT_PATH   = '/api/management/{basePath}/{id}';
const DELETE_MANAGEMENT_PATH  = '/api/management/{basePath}/{id}';

export function create{Resource}Client(jwt: string) {
  const env = getTestEnvironment();
  const { execute } = createBaseClient({
    baseUrl: env.apiUri,
    authToken: jwt,
  });

  // --- User-facing ---

  // Returns all {resource}s.
  async function getAll(): Promise<ApiResponse> {
    return execute({ method: 'GET', path: GET_ALL_PATH });
  }

  async function getAllTyped(expectedStatus: number): Promise<ResourceDto[]> {
    const response = await getAll();
    expect(response.status).toBe(expectedStatus);
    return ResourceListSchema.parse(response.bodyJson);
  }

  // Returns a single {resource} by id.
  async function getById(id: string): Promise<ApiResponse> {
    return execute({
      method: 'GET',
      path: GET_BY_ID_PATH.replace('{id}', encodeURIComponent(id)),
    });
  }

  async function getByIdTyped(id: string, expectedStatus: number): Promise<ResourceDto> {
    const response = await getById(id);
    expect(response.status).toBe(expectedStatus);
    return ResourceSchema.parse(response.bodyJson);
  }

  // Creates a new {resource}.
  async function create(body: ResourceInDto): Promise<ApiResponse> {
    return execute({ method: 'POST', path: POST_PATH, jsonBody: body });
  }

  async function createTyped(body: ResourceInDto, expectedStatus: number): Promise<ResourceDto> {
    const response = await create(body);
    expect(response.status).toBe(expectedStatus);
    return ResourceSchema.parse(response.bodyJson);
  }

  // --- Management operations (only if applicable) ---

  async function getAllManagement(): Promise<ApiResponse> {
    return execute({ method: 'GET', path: GET_ALL_MANAGEMENT_PATH });
  }

  async function getAllManagementTyped(expectedStatus: number): Promise<ResourceDto[]> {
    const response = await getAllManagement();
    expect(response.status).toBe(expectedStatus);
    return ResourceListSchema.parse(response.bodyJson);
  }

  // Replaces the {resource} with the given id.
  async function update(id: string, body: ResourceInDto): Promise<ApiResponse> {
    return execute({
      method: 'PUT',
      path: PUT_MANAGEMENT_PATH.replace('{id}', encodeURIComponent(id)),
      jsonBody: body,
    });
  }

  // Partially updates the {resource} with the given id.
  async function patchById(id: string, body: ResourceModDto): Promise<ApiResponse> {
    return execute({
      method: 'PATCH',
      path: PATCH_MANAGEMENT_PATH.replace('{id}', encodeURIComponent(id)),
      jsonBody: body,
    });
  }

  // Deletes the {resource} with the given id.
  async function remove(id: string): Promise<ApiResponse> {
    return execute({
      method: 'DELETE',
      path: DELETE_MANAGEMENT_PATH.replace('{id}', encodeURIComponent(id)),
    });
  }

  return {
    getAll, getAllTyped,
    getById, getByIdTyped,
    create, createTyped,
    getAllManagement, getAllManagementTyped,
    update, patchById, remove,
  } as const;
}

export type {Resource}Client = ReturnType<typeof create{Resource}Client>;
```

Omit any block that does not apply — a read-only reference client has no `create`/`update`/`remove`; a public-only resource has no management section.

### Requests with query parameters

```ts
async function getAll(page: number, perPage: number): Promise<ApiResponse> {
  return execute({
    method: 'GET',
    path: GET_ALL_PATH,
    query: { page, per_page: perPage },
  });
}
```

`createBaseClient` is responsible for serializing `query` into a URL query string (skip undefined values, encode each key/value).

## Rules

### Module structure

- File name: `{resource}Client.ts` — camelCase, no `Client` casing on the file.
- One module per resource. Export a factory function `create{Resource}Client(jwt: string)` returning a `Readonly<{ … }>` object — **not** a class, unless the project mandates classes.
- Export the resulting type as `{Resource}Client = ReturnType<typeof create{Resource}Client>`.
- Imports: Zod schemas from the models module, `expect` from Vitest, the base client factory, and `getTestEnvironment` from config. Avoid pulling in `axios`, `node-fetch`, `got`, or `supertest`.

### Factory function

- Accepts a single `jwt: string`; pass `''` for unauthenticated clients (`authConfigClient`) — `baseClient` must skip the Authorization header when empty.
- Resolves `apiUri` from `getTestEnvironment()` exactly once on construction.
- Delegates HTTP to `createBaseClient({ baseUrl, authToken })` and uses only the returned `execute(...)` helper.
- Never calls `authHelper.getToken(...)` inside the client — tests fetch the token and pass it in.
- Never reads env vars directly; always go through the config loader.
- Never mutates global state (no monkey-patching `fetch`, no global headers).

### Path constants

- One `const` per distinct path pattern at the top of the module, in `SCREAMING_SNAKE_CASE`.
- Name after purpose: `GET_ALL_PATH`, `GET_BY_ID_PATH`, `POST_PATH`, `DELETE_PATH`.
- Path templates use `{id}` (or `{key}`) placeholders, substituted with `encodeURIComponent(value)` at call site.
- For resources with admin endpoints, suffix `_MANAGEMENT_PATH`.
- User-facing paths start with `/api/`; admin paths start with `/api/management/`.

### Method signatures

- Every endpoint that returns a DTO gets two methods: raw (`Promise<ApiResponse>`) + typed (`Typed` suffix, `expectedStatus: number`).
- Endpoints with no body get only the raw method.
- The typed method calls the raw method — never duplicate request building.
- Bodies are strongly-typed (`ResourceInDto`, `ResourceModDto`), not `unknown` / `Record<string, any>`.
- Use Zod's `parse(response.bodyJson)` in typed methods — never `JSON.parse` directly; `baseClient` already parses JSON into `bodyJson: unknown`.
- One-line comment on the raw method only; not repeated on the typed overload.

### Method naming

| Operation             | Raw method                    | Typed method                       |
|-----------------------|-------------------------------|------------------------------------|
| Fetch collection      | `getAll()`                    | `getAllTyped(expectedStatus)`      |
| Fetch admin collection| `getAllManagement()`          | `getAllManagementTyped(...)`       |
| Fetch by id           | `getById(id)`                 | `getByIdTyped(id, expectedStatus)` |
| Fetch by other key    | `getBy{Key}(key)`             | `getBy{Key}Typed(...)`             |
| Create                | `create(body)`                | `createTyped(body, expectedStatus)`|
| Full replace          | `update(id, body)`            | (raw only — 204)                   |
| Partial update        | `patchById(id, body)`         | (raw only — 204)                   |
| Delete                | `remove(id)`                  | (raw only — 204)                   |

### Raw and unknown-body overloads (body manipulation tests only)

When the test plan includes **malformed JSON** scenarios:

```ts
// Sends a raw string body (for malformed JSON testing).
async function createRaw(rawJson: string): Promise<ApiResponse> {
  return execute({
    method: 'POST',
    path: POST_PATH,
    rawBody: rawJson,
    contentType: 'application/json',
  });
}
```

When the test plan includes **extra/missing property** scenarios:

```ts
// Accepts a pre-built body (e.g. from jsonBodyHelper) for body manipulation tests.
async function createUnchecked(body: Record<string, unknown>): Promise<ApiResponse> {
  return execute({ method: 'POST', path: POST_PATH, jsonBody: body });
}
```

Only add these overloads when the test plan requires them — not by default.

### What NOT to do

- No `setTimeout(..., n)` or manual delays as sync.
- No `axios`, `got`, `node-fetch`, `superagent`, or `supertest` — native `fetch` only.
- No `// @ts-ignore` / `// @ts-expect-error` to silence type errors — fix the type.
- No `any` in client method signatures or return types; Zod-inferred DTOs everywhere.
- No hardcoded base URLs, secrets, or JWTs.
- No try/catch around `execute(...)` — `baseClient` handles logging + network error rethrow.
- No JSON parsing in raw methods — that's `baseClient`'s job; raw method returns `ApiResponse` unchanged.
- No `expect` calls in raw methods — assertions belong in typed methods only.
- No `P`/`M` class-name suffix; no `public/` or `management/` subfolders.
- No top-level `await` for token fetching inside the client module.
- No floating promises — every `execute(...)` must be `await`ed or `return`ed.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource + base path segment from the paths, operations from the methods defined) — do not ask.
1. Ask the user: which **API group** does this client belong to? (user / assessment / legal / reference / auth)
2. Ask the user: resource name (noun) and base URL path segment (e.g. `users`).
3. Ask which **operations** are needed, and whether they are user-facing, admin, or both. Default to full CRUD on the user-facing surface.
4. Ensure the required Zod schemas and inferred types exist under `src/models/{api}/{resource}/`. If not, run `qa/typescript/skills/api-models` first.
5. Generate the file at `src/clients/{api}/{resource}Client.ts`.
6. Run the project's own typecheck script with the package manager `packageManager` names — expect 0 errors.
7. Run the project's own lint script on `src/clients/{api}/{resource}Client.ts` — expect 0 errors. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
