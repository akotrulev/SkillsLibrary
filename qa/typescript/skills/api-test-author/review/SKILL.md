---
name: api-tests-review
description: Use when the user asks to review existing TypeScript API test code (Vitest + native fetch + Zod) for quality. Triggers: "review this Vitest API spec", "look at getUser.spec.ts", "spot issues in this {resource}Client.ts". Do NOT use for writing new tests (`qa-typescript:api-tests`) or reviewing UI tests (`qa-typescript:ui-tests-review`).
---

# QA — API Test Reviewer (TypeScript / Vitest + fetch + Zod)

Reviews TypeScript API test code against the patterns enforced by `qa/typescript/skills/api-test-author/writer`, `qa/typescript/skills/api-client-writer`, and `qa/typescript/skills/api-models` (the Zod schema/types + `{resource}Client` factory with dual raw/typed methods layering). Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (`*.spec.ts`, `{resource}Client.ts`, Zod schema/types module)
- Pre-merge gate on a PR that touches `src/specs/`, `src/clients/`, or `src/models/`
- The user wants a second opinion on schema coverage, `ProblemDetails` handling, or async assertion style

## When NOT to use

- Generating new TS tests → `qa/typescript/skills/api-test-author/writer`
- .NET reviews → `qa/dotnet/skills/api-test-author/review`
- Java reviews → `qa/java/skills/api-test-author/review`
- Schema/client scaffolding → `qa/typescript/skills/api-models` / `qa/typescript/skills/api-client-writer`
- UI tests → `qa/typescript/skills/ui-test-author/review`
- Reviewing the overall test strategy / pyramid → `qa/manual/test-strategy`

## Inputs needed

1. **Files** under review — Vitest spec, `{resource}Client.ts`, Zod schema/types module
2. **Endpoint contract** if available (OpenAPI snippet, sample 4xx body) — needed to grade `ProblemDetails` / error-body assertions
3. **Project conventions** that override defaults (e.g. project uses `safeParse` everywhere, custom error schema name)
4. **`tsconfig.json` strict flags** if questionable — needed to grade `any` / nullable usage

## Review checklist

### Cross-stack (applies to all API tests)

| Check | Bad sign | Severity |
|---|---|---|
| Each test asserts something | Test ends after the request with no assertion | blocker |
| Status code is always asserted first | Test reads body before checking status | major |
| Tests are independent | Test B reads a row that Test A creates | blocker |
| No hardcoded credentials, base URLs, tokens | Literal `"http://localhost:3000"` or inline token | blocker |
| No `setTimeout` / `await new Promise(r => setTimeout(r, n))` waits | Any sleep-style synchronization | blocker |
| Resource cleanup on resources the test created | Created records left in the system if the test fails mid-way | major |
| One logical behavior per test | A single `it(...)` asserts 200 path AND 404 path AND 401 path | major |
| Every assertion states one expected condition | `expect([200, 204]).toContain(status)`, `expect(s === 200 \|\| s === 204).toBe(true)` — on a status, a field, a length, or a duration | major |
| Test names describe behavior | `it('test 1')`, `it('works')` | minor |
| Deserialization uses a typed schema | `JSON.parse(...) as any` followed by ad-hoc property reads | major |
| Status codes consistent from a single source | Magic numbers sprinkled and inconsistent | minor |
| Error responses asserted beyond status | A 400/404/422 test that only asserts the code, ignoring the body | major |

### TypeScript (Vitest + fetch + Zod) specifics

| Check | Bad sign | Severity |
|---|---|---|
| Spec calls go through a `{resource}Client` factory — never raw `fetch` | A spec that calls `fetch(...)` directly instead of a client | major |
| Dual-method pattern intact: raw returns the `ApiResponse` envelope (`{ status, headers, bodyText, bodyJson }`) with no assertion; the `…Typed` method asserts status and `Schema.parse`s, delegating to the raw method | Raw method that parses/validates; typed method that rebuilds the request instead of calling the raw one | major |
| Happy path uses the **typed** method; negative tests use the **raw** method | Negative test calling the typed method (forces Zod-parsing an error body into the resource schema); test re-asserting status after a typed call | major |
| Auth via the factory's `jwt` param; token fetched in the spec via `authHelper` and passed to `create{Resource}Client(token)`; `''` for unauthenticated | Client fetching its own token; auth chosen by an `authenticated: boolean` flag or a hardcoded `x-api-key`; token literal in the spec | major |
| Error bodies parsed in the spec via `ProblemDetailsSchema.parse(response.bodyJson)` | Spec reads `response.bodyJson.field` without `Schema.parse` first | major |
| `await` present on every async client call / assertion | `expect(promise).resolves.toBe(x)` with no `await`, or an unawaited client call | blocker |
| No `any` in schemas, types, client, or spec | `as any`, `: any`, `Record<string, any>` (outside the deliberate `createUnchecked` body) | major |
| Base URL + env resolved via `getTestEnvironment()` | Hardcoded `http://...` or direct `process.env` reads in spec/client | blocker |
| No `setTimeout`-based waits | `await new Promise(r => setTimeout(r, 1000))` | blocker |
| `expect.soft(...)` for multi-field checks of one response | A happy-path body asserted via `toBeDefined()` only; every assertion soft so nothing fails | major |
| No mutation of module-level state across tests | Top-level `let currentUser = ...` reassigned inside `it(...)` blocks | major |
| `describe` grouping per resource / endpoint | Flat list of `it(...)` with no `describe` | minor |
| Schemas tighten primitives + types inferred via `z.infer` | Hand-written `interface` duplicating a schema; loose `z.string()` where `.email()`/`.uuid()` applies | minor |
| `it.each([...])` for parameterized cases instead of `if`/`for` | Conditional logic driving assertions inside an `it(...)` | major |
| TC-ID traceability when a test-case document exists (TC-ID in the title or `allure.tms(...)`) | Tests generated from a TC document with no link back to the planned cases | nit |
| No `try`/`catch` anywhere in a spec or hook | Any catch block in an `it(...)`; `.catch(() => {})` on a client call; a `try/finally` wrapping the body for cleanup | major |
| Created resources tracked and deleted in `afterEach` | Cleanup inlined in the spec body instead of registered | major |
| Unexpected errors fail loudly with an identifying message | Empty `catch`, catch-and-continue, or an assertion whose failure names no id/subject | major |
| Zod failures name `issues[].path` + `code` and the body | A wall of raw `ZodError`, or a loosened schema hiding contract drift | major |
| A job test never waits for the real schedule (`qa/typescript/skills/time-and-concurrency-testing`) | A sleep or long poll until the cron fires, or the production schedule edited so the job fires soon | blocker |
| A boundary test runs with a controlled clock or a stated skew margin | A cut-off / DST / month-end test with no replaced clock, no test-clock endpoint, and no margin larger than skew plus latency named in the test | major |
| A race test has a barrier and the runner's `repeats`; a duplicate-delivery test is not defeated by broker deduplication | Sequential `await`s called a race; a `for` loop repeating it; asserting which request won; a duplicate publish with the same broker message / deduplication id | major |

### Comments in test code

Load **[`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** for the rule itself, the complex-flow test that earns a doc comment, the never-comment trivia list, and the severity mapping. Its **test-code** section carries the AAA-banner rule and the exactly-three-permitted-comments list. This section supplies only the mechanics that differ here.

| TypeScript mechanic | What to check |
|---|---|
| Doc syntax | TSDoc (`/** … */`) — a doc block restating the test name is trivia |
| Skips needing a reason and a ticket | a bare `it.skip(...)` / `.todo` — a silently disabled test |
| Suppressions needing a reason | `@ts-expect-error` / `eslint-disable` — a bare one usually hides a genuine mismatch between the DTO and the response |
| Where an unclear step goes instead | Into a named client method, not a comment above the request-building chain |

**The API-test corollary:** an instruction to accept more than one value is permitted comment #2 — but only alongside a real parameterized case (`it.each`) or a split test. A comment alone does not license the `OR`.

## Smells to flag (TypeScript-specific quick list)

1. Raw `fetch` in a spec instead of a `{resource}Client` — **major**
2. Skipping `Schema.parse(response.bodyJson)` on 2xx responses — **major** (the typed method should already do this)
3. Missing `await` on a client call or `expect(...).resolves.X` chain — **blocker**
4. Raw method that parses/validates, or a typed method that rebuilds the request — **major**
5. Negative test routed through the typed method — **major**
6. Auth via `authenticated: boolean` / `x-api-key` instead of the factory `jwt` + `authHelper` — **major**
7. Hardcoded URLs / tokens / direct `process.env` reads — **blocker**
8. `setTimeout`-based waits — **blocker**
9. Loose `expect(x).toBeDefined()` instead of structural assertions — **major**
10. Mutating shared module-level state across tests — **major**
11. `any` to silence strict mode — **major**
12. Conditional logic (`if`/`for`) driving assertions instead of `it.each` — **major**
13. Missing `describe` grouping per resource / endpoint — **minor**

## Good signals (counter-list)

- Every spec call goes through a `create{Resource}Client(token)` factory; raw methods return `ApiResponse` and never assert, `…Typed` methods assert status + `Schema.parse(response.bodyJson)`.
- Happy path uses the typed method (no re-asserting status); 4xx tests use the raw method and parse with `ProblemDetailsSchema`, asserting `title`, `status`, and `errors[field]`.
- Auth state is the factory `jwt`: the spec fetches it via `authHelper.getToken(...)` and passes it in; `''` for unauthenticated. No token literals, no `x-api-key`.
- Each `it(...)` constructs its own client; no top-level `let` reassigned between tests.
- Test titles read like behavior sentences and carry the TC-ID when a document exists.
- `it.each([...])` for parameterized cases; `tsc --noEmit` passes; `strict: true` is on; no `any` in the diff.
- Cleanup runs in `afterEach` / `afterAll` over ids tracked as they were created — with no `try/catch`, so a failing cleanup fails the hook loudly.

## Procedure

1. Confirm imports show Vitest + the client factory + the Zod types module (`import { describe, it, expect } from 'vitest';`, `import { create{Resource}Client } from '../../../clients/...';`).
2. Read the whole vertical slice (spec **plus** the imported `{resource}Client.ts` **plus** the schema/types module) before writing findings — most real bugs are cross-file (e.g. a raw method that parses, so the negative spec is dead code).
3. Walk the cross-stack checklist, then the TS-specific list, then the smells quick list.
4. For each finding, capture: file + line, the issue (concrete, not "looks weird"), and a one-sentence fix.
5. **Do not rewrite the code.** Hand off to `qa/typescript/skills/api-test-author/writer` if the user wants the rewrite.

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | src/specs/user/users/getUser.spec.ts:42           | `expect(client.getAllTyped(200)).resolves...` not awaited   | Add `await` — unawaited `.resolves` chains pass on failures            |
| major    | src/clients/user/userClient.ts:60                 | Raw `getById` runs `Schema.parse` and returns the DTO       | Return `ApiResponse`; parsing belongs in the `…Typed` method           |
| major    | src/specs/user/users/getUser.spec.ts:18           | Auth chosen via `new UserClient(true)` flag                 | Build via `createUserClient(await authHelper.getToken(...))`           |
| minor    | src/specs/user/users/getUser.spec.ts:10           | All `it(...)` flat, no `describe`                            | Wrap in `describe('GET /api/users', () => { ... })`                    |
| nit      | src/specs/user/users/getUser.spec.ts:14           | Test title `'test 1'`                                       | Rename to behavior: `'returns the first page of users'`                |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, hard rule violation (missing `await`, hardcoded secrets, `setTimeout` waits, shared state)
- **major** — design / correctness issue that will hurt soon (silent failures, lost coverage, `any` types, wrong layering)
- **minor** — style / small inconsistency (naming, grouping)
- **nit** — optional preference

## Anti-patterns to always flag

- **A `try`/`catch` inside a spec.** There is no legitimate one: an expected rejection is asserted with `await expect(...).rejects`, an unexpected one must reach Vitest, and cleanup belongs in `afterEach`. A catch in a spec body — or a `.catch(() => {})` on a client call — is either hiding a failure or substituting for an assertion.
- **A `try`/`finally` wrapping a spec body for cleanup.** Track the created id and delete it in `afterEach` — the body stays linear and cleanup runs whether the test passed, failed, or threw.
- **A swallowing cleanup hook.** An empty catch around the delete means the suite leaks data silently until the environment rots. Let it throw; Vitest reports the hook failure.
- **Zod failure with no context.** A raw `ZodError` dump, or a `.passthrough()`/`.optional()` added to make a drifted contract pass — report `issues[].path` + `code` and the raw body instead, and let the drift fail the spec.
- **Unawaited async assertion.** `expect(promise).resolves.toBe(x)` without `await` is a no-op — Vitest cannot fail the test.
- **Status-code-only 4xx test.** When the backend emits `ProblemDetails`, asserting just the status throws away the highest-signal failure information.
- **`OR` in an assertion.** `expect([200, 204]).toContain(response.status)` (or `||` inside an `expect`, or a `toMatch`/`toContain` smuggling a set of acceptable values) means the author did not know what the endpoint returns, so the test passes on the wrong behavior and never fails when the API changes between the two. Applies to fields, lengths, and time budgets as much as to status codes. Fix by splitting into one `it` per expected outcome, driving it from `it.each([...])`, or pinning the correct value.
- **`toBeDefined()` as the only happy-path assertion.** It passes on any non-`undefined` body, including a wrong-shape one — parse with the Zod schema and assert structural fields.
- **Raw method that validates.** Couples the response shape to the request layer and removes the spec's ability to assert on the raw `ApiResponse` for error paths. Parse in the typed method (happy path) or the spec (error path).
- **Negative test through the typed method.** Forces Zod-parsing of an error body into the resource schema — either a thrown ZodError or a wrong-shape parse.
- **Auth as a boolean flag / `x-api-key`.** The current architecture passes a real `jwt` into the factory; the spec fetches it via `authHelper`. A boolean flag or hardcoded key is the retired pattern.
- **`any` to silence strict mode.** Defeats the point of Zod + TS. Tighten the schema and let `z.infer` produce the type.
- **Hardcoded base URL or token.** Always `getTestEnvironment()` + `authHelper`; the setup file should fail fast if config is missing.
- **Mutating module-level state.** Top-level `let` reassigned by tests destroys independence — each `it` builds its own state.
- **`setTimeout`-based waits.** Use `vi.waitFor` polling on a concrete condition.

## Handoffs

- Need a rewrite → `qa/typescript/skills/api-test-author/writer`
- Schemas / types need fixing → `qa/typescript/skills/api-models`
- Client layer needs refactor → `qa/typescript/skills/api-client-writer`
- Whole test pyramid is the issue → `qa/manual/test-strategy`
- .NET sibling → `qa/dotnet/skills/api-test-author/review`
- Java sibling → `qa/java/skills/api-test-author/review`
