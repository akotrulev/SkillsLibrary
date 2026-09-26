---
name: qa-api-test-playwright-typescript
description: Use when the user asks to write TypeScript API tests on the Playwright runner (@playwright/test `request` fixture / APIRequestContext + Zod) — usually because the project already runs Playwright for UI and wants one runner, one report, one trace. Triggers: "write API tests with Playwright", "use the request fixture for endpoint X". Do NOT use for plain Node API suites without Playwright (`qa-api-test-writer-typescript`) or UI tests (`qa-ui-test-writer-playwright-typescript`).
---

# QA — API Test Writer (TypeScript / Playwright + APIRequestContext + Zod)

Authors `*.spec.ts` files that test a REST backend through **Playwright's own HTTP client** —
`APIRequestContext` — instead of a browser. It reuses the **Schema/types + Client + Spec** layering of the
Vitest sibling (`qa-api-test-writer-typescript`): Zod schemas from `qa/typescript/skills/api-models`,
a `{resource}Client` factory with dual raw + typed methods, spec files that own scenarios and assertions. Only
the transport and the runner change; the discipline does not.

> **The discipline this skill encodes** — four ideas that separate a correct Playwright API suite from a
> `fetch` reflex ported into the wrong runner:
>
> 1. **The `APIRequestContext` is the auth boundary, not the call site.** Base URL and the `Authorization`
>    header are set **once, at context creation** (`playwright.config.ts` `use.baseURL` /
>    `request.newContext({ extraHTTPHeaders })`). One context per identity — standard user, admin, anonymous —
>    never a token argument threaded through every call. Every context you create yourself is disposed
>    (`await ctx.dispose()`), in the fixture's teardown.
> 2. **The per-test `request` fixture is free; custom identities come from fixtures.** `@playwright/test`
>    hands every test a fresh, config-respecting, auto-disposed `APIRequestContext` — that is the default
>    identity. Additional identities (admin, anonymous, wrong-role) are **worker/test fixtures** that create,
>    yield, and dispose a context — never module-level singletons, never per-call `newContext()` litter.
> 3. **You are here for one runner, one report, one trace.** The value of Playwright API testing is that API
>    specs share the UI suite's config, projects, HTML/Allure report, tracing, and CI wiring — and that a
>    cookie-authenticated app can share **`storageState`** between a logged-in browser and API calls. If the
>    project has no Playwright UI suite, the stack default is `api-test-author/writer` (Vitest + fetch).
> 4. **The layering survives the runner swap.** Specs still never touch HTTP directly: a `{resource}Client`
>    factory wraps the context (`create{Resource}Client(ctx: APIRequestContext)`), the raw method returns the
>    Playwright `APIResponse` unasserted, the typed method asserts the **exact** status and `Schema.parse`s
>    the body. The only signature change from the fetch client: the factory takes a **context**, because the
>    context — not a `jwt` string — now carries the identity.

## Stack

- Node 24 + TypeScript (strict mode)
- **@playwright/test** as the test runner — API specs live beside the UI specs, same `playwright.config.ts`
- **`APIRequestContext`** for HTTP — the built-in `request` fixture for the default identity, fixture-created
  contexts for other identities; no `fetch`/axios/supertest in a Playwright project
- **Zod** for request/response schemas and runtime validation (`qa/typescript/skills/api-models`)
- **Allure** via `allure-playwright` where the project uses Allure
- Project layout: `src/clients/{api}/`, `src/models/{api}/{resource}/`, `tests/api/{resource}/`,
  `tests/fixtures.ts`, `playwright.config.ts` (a dedicated `api` project with `use.baseURL` pointing at the API)

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `models/{api}/{resource}/{resource}.schema.ts` (Zod) + `.types.ts` (`z.infer`) | `qa/typescript/skills/api-models` | Body shapes, JSON-key mapping, runtime validation |
| `clients/{api}/{resource}Client.ts` — `create{Resource}Client(ctx: APIRequestContext)` | `qa/typescript/skills/api-client-writer` conventions, context-based variant | Request building on the context; raw method returns `APIResponse` unasserted; typed method asserts exact status + `Schema.parse(await res.json())` |
| `tests/fixtures.ts` | **this skill** | Identity fixtures: token via `authHelper` → `request.newContext({ extraHTTPHeaders })` → yield client → `dispose()` |
| `tests/api/{resource}/{operation}{Resource}.spec.ts` | **this skill** | Scenario choice, arrange/act/assert, test data, cleanup |

If a schema/type or client a spec needs is missing, run the owner skill first — never call `request.get(...)`
inline in a spec to avoid generating a client.

## When to use

- The project already runs Playwright for UI and wants API coverage in the same suite/report
- Hybrid suites where API specs and UI specs must share config, projects, tracing, and `storageState`
- New `{operation}{Resource}.spec.ts` under `tests/api/`, or new scenarios on an existing one

## When NOT to use

- No Playwright in the project → `qa/typescript/skills/api-test-author/writer` (Vitest + fetch + Zod, the stack default)
- API calls **inside a UI test** (seed data, then drive the browser) → that is the UI suite's arrange step; conventions in `qa/typescript/skills/ui-test-author/playwright`
- Mocking/intercepting the browser's network traffic → `qa/typescript/skills/network-mocking` (`page.route` is not API testing)
- GraphQL / gRPC → the protocol siblings under `qa/typescript/skills/api-test-author/`
- Reviewing existing tests → `qa/typescript/skills/api-test-author/review` (cross-stack checklist applies; add this skill's anti-patterns below)

## Fixtures template — identities as contexts

`tests/fixtures.ts` extends the base test with one fixture per identity. Tokens come from `authHelper`;
every created context is disposed after use.

```ts
import { test as base, APIRequestContext } from '@playwright/test';
import { createUserClient, UserClient } from '../src/clients/user/userClient.js';
import { authHelper, TestUsers } from '../src/clients/authHelper.js';

type ApiFixtures = {
  userClient: UserClient;       // standard identity
  adminClient: UserClient;      // elevated identity
  anonymousClient: UserClient;  // no Authorization header at all
};

export const test = base.extend<ApiFixtures>({
  userClient: async ({ playwright, baseURL }, use) => {
    const ctx = await playwright.request.newContext({
      baseURL,
      extraHTTPHeaders: { Authorization: `Bearer ${await authHelper.getToken(TestUsers.STANDARD)}` },
    });
    await use(createUserClient(ctx));
    await ctx.dispose();
  },
  adminClient: async ({ playwright, baseURL }, use) => {
    const ctx = await playwright.request.newContext({
      baseURL,
      extraHTTPHeaders: { Authorization: `Bearer ${await authHelper.getToken(TestUsers.ADMIN)}` },
    });
    await use(createUserClient(ctx));
    await ctx.dispose();
  },
  anonymousClient: async ({ request }, use) => {
    // the built-in fixture has no auth header when the config sets none — reuse it, no dispose needed
    await use(createUserClient(request));
  },
});
export { expect } from '@playwright/test';
```

## Spec template

```ts
import { test, expect } from '../../fixtures.js';
import { ProblemDetailsSchema } from '../../../src/models/user/users/user.types.js';
import { validUser } from '../../../src/fixtures/user.js';

test.describe('GET /api/users', () => {
  test('TC-USER-001: returns all users when authorized', async ({ userClient }) => {
    const users = await userClient.getAllTyped(200);

    expect(users.length).toBeGreaterThan(0);
  });

  test('TC-USER-002: returns 401 when the token is missing', async ({ anonymousClient }) => {
    const response = await anonymousClient.getAll();

    expect(response.status()).toBe(401);
  });

  test('TC-USER-004: returns 404 when the user does not exist', async ({ userClient }) => {
    const response = await userClient.getById('999999');

    expect(response.status()).toBe(404);
    const problem = ProblemDetailsSchema.parse(await response.json());
    expect(problem.title).toBeTruthy();
  });
});

test.describe('POST /api/users', () => {
  const createdIds: string[] = [];

  // Cleanup is registered, never inlined: the test body stays linear with no
  // try/finally, and the hook carries no try/catch — a failing cleanup fails loudly.
  test.afterEach(async ({ adminClient }) => {
    for (const id of createdIds) await adminClient.remove(id);
    createdIds.length = 0;
  });

  test('TC-USER-010: creates a user when the body is valid', async ({ adminClient }) => {
    const body = validUser().build(); // builder — see qa/typescript/skills/test-data-builder

    const created = await adminClient.createTyped(body, 201);
    createdIds.push(String(created.id));

    expect.soft(created.email).toBe(body.email);
    expect.soft(created.firstName).toBe(body.firstName);
  });

  test('TC-USER-011: returns 400 with a field error when email is missing', async ({ adminClient }) => {
    const body = validUser().email(null).build();

    const response = await adminClient.create(body);

    expect(response.status()).toBe(400);
    const problem = ProblemDetailsSchema.parse(await response.json());
    expect(problem.errors?.email?.length).toBeGreaterThan(0);
  });
});
```

## Scenario → pattern matrix

| Scenario | Client method / identity | Assertion pattern |
|----------|--------------------------|-------------------|
| 2xx happy path | **typed** on `userClient`/`adminClient` | DTO returned already status-asserted + Zod-validated; verify fields with `expect.soft(...)` |
| 401 unauthorized | **raw** on `anonymousClient` | single `expect(response.status()).toBe(401)` |
| 403 forbidden | **raw** on a wrong-role identity fixture | single `expect(response.status()).toBe(403)` |
| 404 not found | **raw** | status assert + `ProblemDetailsSchema.parse(await response.json())` when the backend emits one |
| 400 validation | **raw** | status assert + `ProblemDetailsSchema.parse(...)`; assert the field key in `errors` |
| Malformed JSON / extra-missing property | **raw** via the client's `createRaw(string)` / `createUnchecked(...)` | status assert only — add these methods via `api-client-writer` when the plan requires them |
| Eventually-consistent state | **raw/typed** inside `expect.poll` | `await expect.poll(async () => (await client.getById(id)).status(), { timeout: 10_000 }).toBe(200)` |

## Rules

### Spec structure & naming

- API specs live in `tests/api/{resource}/`, one file per operation: `{operation}{Resource}.spec.ts`, run by a
  dedicated `api` **project** in `playwright.config.ts` (no browser, `use.baseURL` = the API root; UI projects
  don't pick them up and vice versa).
- One `test.describe(...)` per endpoint; titles read like behavior sentences and carry the TC-ID when a
  test-case document drives generation (or `allure.tms(...)` where `allure-playwright` is wired).
- Identities are **fixtures**, not setup code: a spec asks for `adminClient` in its parameter list. No
  `beforeAll` creating shared contexts, no module-level clients.

### Test rules

- Assert the **exact** status code, always, before reading the body — `expect(response.status()).toBe(201)`,
  never `expect(response).toBeOK()` (it passes on any 2xx, so a 204 from a broken create still "passes").
  Never set `failOnStatusCode: true` — a thrown error is not an assertion and kills the 4xx tests.
- Happy path uses the **typed** client method; negative scenarios use the **raw** method. Never re-assert the
  status after a typed call.
- Parse every 2xx body through the Zod schema (the typed method already does); error bodies are parsed in the
  spec via `ProblemDetailsSchema.parse(await response.json())`. Never read `(await response.json()).field`
  without a parse.
- One logical behavior per test; `expect.soft(...)` for multiple fields of one response.
- Tests are independent: per-test data, cleanup in `finally` (or `afterEach`) wrapped so it never masks a
  failure, no execution-order assumptions — the suite must survive `--workers=4 --shard=2/2`.
- Rows that differ only in data → a `for (const …)` over a **const test-case table generating `test(...)` calls**
  (the Playwright-idiomatic parameterization), never conditionals inside one test body.
- No `page`, no `browser` — an API spec that asks for the `page` fixture is a UI test in the wrong folder.
- Eventual consistency → `expect.poll` / `expect(...).toPass()`, never `waitForTimeout`.

### What NOT to do

- No raw `request.get(...)` / `ctx.post(...)` in specs — every request goes through a `{resource}Client`.
- No `fetch` / axios / supertest inside a Playwright project — one HTTP client, one trace.
- No token threading per call — identity lives in the context (`extraHTTPHeaders` at creation) or in
  `storageState` for cookie-auth apps (share the UI suite's logged-in state file; see
  `qa/typescript/skills/test-login-tokens`).
- No undisposed contexts — every `newContext()` has a `dispose()` in the fixture teardown.
- No `toBeOK()` as the status assertion; no `failOnStatusCode: true`.
- No hardcoded base URLs or tokens — `baseURL` from the config/env, tokens via `authHelper`.
- No mixing UI steps and API assertions in one test — pure API specs stay in the `api` project; API-as-arrange
  inside a UI test belongs to the UI suite's conventions.

## Generation steps

1. Confirm the project runs Playwright (a `playwright.config.ts` and `@playwright/test` dependency). If not,
   stop and route to `api-test-author/writer` — say why.
2. Determine the **source of truth**: OpenAPI/Swagger spec, test-case document (map one `test(...)` per TC-ID,
   id in the title), or verbal scenarios.
3. Ensure the `api` project exists in `playwright.config.ts` (`use.baseURL`, no browser); add it if missing.
4. For each resource in scope, verify the Zod schema + types and the context-based `{resource}Client` exist —
   create missing ones via `api-models`, then the client following `api-client-writer` conventions with the
   `(ctx: APIRequestContext)` factory signature.
5. Add the identity fixtures the planned scenarios need (standard / admin / anonymous / wrong-role) to
   `tests/fixtures.ts`.
6. Author one spec file per operation from the scenario matrix.
7. Run the project's own typecheck script (with the package manager `packageManager` names), then `npx playwright test --project=api` — expect 0 type errors, 0 failures. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- `qa-api-test-writer-typescript` — the **stack default** (Vitest + fetch + Zod); this skill is the
  variant for Playwright-first projects. Shared spine: Schema + Client + Spec, dual raw/typed methods,
  `ProblemDetails` discipline, builder-based test data.
- `qa-api-test-playwright-java` · `qa-api-test-playwright-dotnet` — the sibling stacks
  (playwright-java + TestNG · Microsoft.Playwright + NUnit); same four ideas, different bindings.
- `qa-api-models-typescript` / `qa-api-client-writer-typescript` — schemas / the client layer this skill consumes.
- `qa-ui-test-writer-playwright-typescript` — the UI suite this skill shares a runner with; API-as-arrange lives there.
- `qa-network-mocking-typescript` — `page.route` mocking/asserting of browser traffic (not API testing).
- `qa-api-test-review-typescript` — review; its cross-stack checklist applies verbatim, plus this
  skill's What-NOT-to-do list as Playwright-specific findings.
- `qa-test-login-tokens-typescript` — the tokens the identity fixtures inject.
- `qa-test-reports-typescript` — `allure-playwright` wiring so API and UI results land in one report.
