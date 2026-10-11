---
name: api-tests-playwright
description: Use when the user asks to write TypeScript API tests on the Playwright runner (@playwright/test `request` fixture / APIRequestContext + Zod) — usually because the project already runs Playwright for UI and wants one runner, one report, one trace. Triggers: "write API tests with Playwright", "use the request fixture for endpoint X". Do NOT use for plain Node API suites without Playwright (`qa-typescript:api-tests`) or UI tests (`qa-typescript:ui-tests-playwright`).
---

# QA — API Test Writer (TypeScript / Playwright 1.64 + APIRequestContext + Zod)

Authors `*.spec.ts` files that test a REST backend through **Playwright's own HTTP client** —
`APIRequestContext` — instead of a browser. It reuses the **Schema/types + Client + Spec** layering of the
Vitest sibling (`qa-typescript:api-tests`): Zod schemas from `qa/typescript/skills/api-models`, a
`{resource}Client` factory with dual raw + typed methods, spec files that own scenarios and assertions. Only the
transport and the runner change; the discipline does not. This skill pins nothing: the Playwright version is the
**Versions** table of `qa/typescript/skills/ui-test-author/playwright/SKILL.md`; each API below carries the
version it shipped in.

> **The discipline this skill encodes:**
>
> 1. **The `APIRequestContext` is the auth boundary, not the call site.** Base URL and the `Authorization`
>    header are set **once, at context creation** (`use.baseURL` / `request.newContext({ extraHTTPHeaders })`),
>    or the session cookie is added to the context. One context per identity — standard user, admin, anonymous —
>    never a token argument threaded through every call. Every context you create is disposed in its fixture's
>    teardown.
> 2. **The per-test `request` fixture is free; custom identities come from fixtures.** `@playwright/test` hands
>    every test a fresh, config-respecting, auto-disposed `APIRequestContext` — the default identity. Other
>    identities are fixtures that create, yield, and dispose a context.
> 3. **You are here for one runner, one report, one trace.** API specs share the UI suite's config, projects,
>    HTML/Allure report, tracing, and CI wiring. If the project has no Playwright UI suite, the stack default is
>    `api-test-author/writer` (Vitest + fetch).
> 4. **The layering survives the runner swap.** Specs never touch HTTP directly: `create{Resource}Client(ctx)`
>    wraps the context, the raw method returns the `APIResponse` unasserted, the typed method asserts the
>    **exact** status and `Schema.parse`s the body.

## Stack

- Node 24 (22 maintenance) + TypeScript (strict mode)
- **@playwright/test** as the runner — API specs live beside the UI specs, same `playwright.config.ts`
- **`APIRequestContext`** for HTTP — no `fetch`/axios/supertest in a Playwright project
- **Zod** for request/response schemas (`qa/typescript/skills/api-models`)
- **Allure** via `allure-playwright` where the project uses Allure; calls from `allure-js-commons`, awaited
- Layout: `src/clients/{api}/`, `src/models/{api}/{resource}/`, `tests/api/{resource}/`, `tests/fixtures.ts`,
  and a dedicated `api` project in `playwright.config.ts` with `use.baseURL` pointing at the API

## Layering contract — who does what

| Layer | Owner skill | Responsibility |
|-------|-------------|----------------|
| `models/{api}/{resource}/{resource}.schema.ts` (Zod) + `.types.ts` | `qa/typescript/skills/api-models` | Body shapes, JSON-key mapping, runtime validation |
| `clients/{api}/{resource}Client.ts` — `create{Resource}Client(ctx: APIRequestContext)` | `qa/typescript/skills/api-client-writer` conventions | Raw method returns `APIResponse` unasserted; typed method asserts exact status + `Schema.parse(await res.json())` |
| `tests/fixtures.ts` | **this skill** | Identity fixtures (token or cookie → context → client → `dispose()`) and created-data cleanup |
| `tests/api/{resource}/{operation}{Resource}.spec.ts` | **this skill** | Scenario choice, arrange/act/assert, test data |

If a schema or client a spec needs is missing, run the owner skill first — never call `request.get(...)` inline.

## When to use

- The project already runs Playwright for UI and wants API coverage in the same suite/report
- Hybrid suites where API specs and UI specs share config, projects, tracing, and signed-in state
- New `{operation}{Resource}.spec.ts` under `tests/api/`, or new scenarios on an existing one

## When NOT to use

- No Playwright in the project → `qa/typescript/skills/api-test-author/writer` (Vitest + fetch + Zod)
- API calls **inside a UI test** (seed, then drive the browser) → the UI suite's arrange step
  (`qa/typescript/skills/ui-test-author/playwright`)
- Mocking the browser's network traffic → `qa/typescript/skills/network-mocking`
- GraphQL / gRPC → the protocol siblings under `qa/typescript/skills/api-test-author/`
- Reviewing existing tests → `qa/typescript/skills/api-test-author/review`

## Fixtures template — identities as contexts, cleanup as teardown

`userClient` is the standard identity, `adminClient` the elevated one, `anonymousClient` sends no
`Authorization` header (it reuses the built-in `request` fixture, which needs no dispose). `createdUsers`
collects ids a test creates and deletes them in its teardown — the test body has no `try`/`finally`, and a
failing delete fails the test loudly with every status as evidence.

```ts
import { test as base, expect } from '@playwright/test';
import { authHelper, TestUsers } from '../src/clients/authHelper.js';
import { createUserClient, type UserClient } from '../src/clients/user/userClient.js';

type ApiFixtures = {
  userClient: UserClient;
  adminClient: UserClient;
  anonymousClient: UserClient;
  createdUsers: string[];
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
    await use(createUserClient(request));
  },
  createdUsers: async ({ adminClient }, use) => {
    const ids: string[] = [];
    await use(ids);
    const statuses = await Promise.all(ids.map(async (id) => (await adminClient.remove(id)).status()));
    expect(statuses, `cleanup of users ${ids.join(', ')}`).toEqual(ids.map(() => 204));
  },
});

export { expect };
```

## Spec template

The case id rides in the test's details as a tag, so the title stays `Should_X_When_Y`.

```ts
import { ProblemDetailsSchema } from '../../../src/models/user/users/user.types.js';
import { validUser } from '../../../src/fixtures/user.js';
import { expect, test } from '../../fixtures.js';

test.describe('GET /api/users', () => {
  test('Should_ReturnUsers_When_TokenIsValid', { tag: '@TC-USER-001' }, async ({ userClient }) => {
    const users = await userClient.getAllTyped(200);

    expect(users.length).toBeGreaterThan(0);
  });

  test('Should_Return401_When_TokenIsMissing', { tag: '@TC-USER-002' }, async ({ anonymousClient }) => {
    const response = await anonymousClient.getAll();

    expect(response.status()).toBe(401);
  });

  test('Should_Return404WithProblem_When_UserDoesNotExist', { tag: '@TC-USER-004' }, async ({ userClient }) => {
    const response = await userClient.getById('999999');

    expect(response.status(), await response.text()).toBe(404);
    expect(ProblemDetailsSchema.parse(await response.json()).status).toBe(404);
  });
});

test.describe('POST /api/users', () => {
  test('Should_CreateUser_When_BodyIsValid', { tag: '@TC-USER-010' }, async ({ adminClient, createdUsers }) => {
    const body = validUser().build();

    const created = await adminClient.createTyped(body, 201);
    createdUsers.push(String(created.id));

    expect(created).toMatchObject({ email: body.email, firstName: body.firstName });
  });

  test('Should_Return400WithEmailError_When_EmailIsMissing', { tag: '@TC-USER-011' }, async ({ adminClient }) => {
    const response = await adminClient.create(validUser().email(null).build());

    expect(response.status(), await response.text()).toBe(400);
    expect(ProblemDetailsSchema.parse(await response.json()).errors).toHaveProperty('email');
  });
});
```

## Context options, cookies and the response's own evidence

| Need | API | Notes |
|---|---|---|
| Statuses come back, never thrown | `failOnStatusCode` on `request.newContext` [1.51] (and per request) — leave it `false`, the default | `true` turns a 4xx into an exception: an assertion never runs and every negative test dies. Never set it in `use` or a context the specs assert through |
| Assert a redirect itself | `maxRedirects: 0` on the context [1.52] or the request | The response **is** the `302`; assert its status and `location` header. The default follows the redirect chain |
| Cookie-authenticated app | `ctx.addCookies([{ name, value, url }])`, `ctx.cookies()`, `ctx.clearCookies()` [1.64] | Add the session cookie in the identity fixture instead of a header; read `cookies()` to assert the server set one (`Set-Cookie`). Below 1.64: pass `storageState` (the UI suite's signed-in file, `qa/typescript/skills/test-login-tokens`) to `newContext` |
| Latency budget on one call | `await response.timing()` [1.62] | The request's timing phases in ms; assert the total against the endpoint's budget with the value in the message. A load profile is `qa-typescript:load-testing`, not this |
| TLS on the API host | `await response.securityDetails()` [1.61] | `{ protocol, issuer, subjectName, validFrom, validTo }`, or `null` over plain HTTP; assert the protocol |

```ts
test('Should_IssueSessionCookie_When_UserSignsIn', { tag: '@TC-AUTH-003' }, async ({ sessionClient }) => {
  await sessionClient.signIn(validUser().build());

  expect(await sessionClient.cookieNames()).toContain('session');
});
```

`sessionClient` is a client over a fixture-owned context whose `cookieNames()` reads `ctx.cookies()` [1.64].
The context's trace (`APIRequestContext.tracing` [1.60]) and the runner's `trace: 'retain-on-failure'` record the
calls of a failed test (`qa/typescript/skills/evidence-capture`).

## Scenario → pattern matrix

| Scenario | Client method / identity | Assertion pattern |
|----------|--------------------------|-------------------|
| 2xx happy path | **typed** on `userClient`/`adminClient` | DTO already status-asserted + Zod-validated; `toMatchObject` on the fields |
| 401 / 403 | **raw** on `anonymousClient` / a wrong-role identity | one exact `expect(response.status()).toBe(...)` |
| 404 / 400 | **raw** | exact status + `ProblemDetailsSchema.parse(await response.json())` |
| Malformed JSON / extra-missing property | **raw** via `createRaw(string)` / `createUnchecked(...)` | exact status — add the methods via `api-client-writer` |
| Redirect | **raw** on a `maxRedirects: 0` context | exact `302` + the `location` header |
| Eventually-consistent state | **raw/typed** inside `expect.poll` | `await expect.poll(async () => (await client.getById(id)).status(), { timeout: 10_000 }).toBe(200)` |

## Rules

### Spec structure & naming

- API specs live in `tests/api/{resource}/`, one file per operation, run by a dedicated `api` **project**
  (no browser, `use.baseURL` = the API root).
- One `test.describe(...)` per endpoint; names are `Should_X_When_Y`; the TC-ID is a `{ tag }` in the test's
  details (or `await allure.tms(...)` from `allure-js-commons` where Allure is wired).
- Identities are **fixtures**: a spec asks for `adminClient` in its parameter list. No `beforeAll` creating
  shared contexts, no module-level clients.

### Test rules

- Assert the **exact** status code before reading the body — `toBe(201)`, never `toBeOK()` (any 2xx passes).
  `failOnStatusCode` stays `false` (§ Context options).
- Happy path uses the **typed** client method; negative scenarios use the **raw** method.
- Parse every body through its Zod schema; never read `(await response.json()).field` unparsed.
- One logical behavior per test; `toMatchObject` (or `expect.soft`) for several fields of one response.
- Tests are independent: per-test data, **cleanup in a fixture's teardown** (`createdUsers`) or `afterEach` —
  never a `try`/`finally` in the test body. The suite must survive `--workers=4 --shard=2/2`.
- Rows that differ only in data → a `for` over a const case table **generating `test(...)` calls**, outside
  every test body (`qa/typescript/skills/data-driven-testing`) — never conditionals inside one test.
- No `page`, no `browser` — an API spec that asks for `page` is a UI test in the wrong folder.
- Eventual consistency → `expect.poll` / `expect(...).toPass()`, never `waitForTimeout`.

### What NOT to do

- No raw `request.get(...)` / `ctx.post(...)` in specs — every request goes through a `{resource}Client`.
- No `fetch` / axios / supertest inside a Playwright project — one HTTP client, one trace.
- No token threading per call — identity lives in the context (headers or cookies at creation).
- No undisposed contexts; no `toBeOK()`; no `failOnStatusCode: true`; no `finally`.
- No hardcoded base URLs or tokens — `baseURL` from the config/env, tokens via `authHelper`.

## Generation steps

1. Confirm the project runs Playwright (a `playwright.config.ts` and `@playwright/test`). If not, route to
   `api-test-author/writer` — say why.
2. Determine the **source of truth**: OpenAPI, a test-case document (one `test(...)` per TC-ID, the id as a
   tag), or verbal scenarios.
3. Ensure the `api` project exists in `playwright.config.ts` (`use.baseURL`, no browser).
4. Verify the Zod schemas and the context-based `{resource}Client` exist — create missing ones via `api-models`
   and `api-client-writer` with the `(ctx: APIRequestContext)` factory signature.
5. Add the identity and cleanup fixtures the planned scenarios need to `tests/fixtures.ts`.
6. Author one spec file per operation from the scenario matrix.
7. Run the project's own typecheck script, then `npx playwright test --project=api` — expect 0 type errors, 0
   failures. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- `qa-typescript:api-tests` — the **stack default** (Vitest + fetch + Zod); same Schema + Client + Spec
  spine.
- `qa-java:api-tests-playwright` · `qa-dotnet:api-tests-playwright` — the sibling stacks; same four ideas.
- `qa-typescript:api-models` / `qa-typescript:api-client-writer` — schemas / the client layer.
- `qa-typescript:ui-tests-playwright` — the UI suite this skill shares a runner with.
- `qa-typescript:network-mocking` — `page.route` mocking of browser traffic (not API testing).
- `qa-typescript:api-tests-review` — review; plus this skill's What-NOT-to-do list.
- `qa-typescript:test-login-tokens` — the tokens and signed-in state the identity fixtures inject.
- `qa-typescript:test-reports` — `allure-playwright` wiring so API and UI results land in one report.
