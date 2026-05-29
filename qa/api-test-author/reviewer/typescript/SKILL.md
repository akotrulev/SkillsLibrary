---
name: qa-api-test-author-reviewer-typescript
description: Use when the user asks to review existing TypeScript API test code (Vitest + native fetch + Zod) for quality. Triggers: "review this Vitest API spec", "look at user.spec.ts", "spot issues in this *Client.ts", "is this Zod schema test any good". Do NOT use for generating new tests (use `qa/api-test-author/generator/typescript`), for the .NET sibling (use `qa/api-test-author/reviewer/dotnet`), for the Java sibling (use `qa/api-test-author/reviewer/java`), or for UI tests (use `qa/ui-test-author/reviewer`).
---

# QA — API Test Reviewer (TypeScript / Vitest + fetch + Zod)

Reviews TypeScript API test code against the patterns enforced by `qa/api-test-author/generator/typescript`. Produces a findings table in the `CLAUDE.md` review format. Does **not** rewrite — points to the fix and lets the human apply it.

## When to use

- A diff or file is submitted for review (`*.spec.ts`, `*Client.ts`, Zod schema)
- Pre-merge gate on a PR that touches `tests/specs/`, `tests/clients/`, or `tests/schemas/`
- The user wants a second opinion on schema coverage, `ProblemDetails` handling, or async assertion style

## When NOT to use

- Generating new TS tests → `qa/api-test-author/generator/typescript`
- .NET reviews → `qa/api-test-author/reviewer/dotnet`
- Java reviews → `qa/api-test-author/reviewer/java`
- Schema-only review (no test) → `qa/api-dto-writer/typescript`
- UI tests → `qa/ui-test-author/reviewer`
- Reviewing the overall test strategy / pyramid → `qa/_shared/test-strategy`

## Inputs needed

1. **Files** under review — Vitest spec, `*Client.ts`, Zod schema module
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
| No hardcoded credentials, base URLs, tokens | Literal `"http://localhost:3000"` or inline API key | blocker |
| No `setTimeout` / `await new Promise(r => setTimeout(r, n))` waits | Any sleep-style synchronization | blocker |
| Resource cleanup on resources the test created | Created records left in the system if the test fails mid-way | major |
| One logical behavior per test | A single `it(...)` asserts 200 path AND 404 path AND 401 path | major |
| Test names describe behavior | `it('test 1')`, `it('works')` | minor |
| Deserialization uses a typed schema | `JSON.parse(...) as any` followed by ad-hoc property reads | major |
| Status codes via named constants or literals from a single source | Magic numbers sprinkled and inconsistent (`200` here, `HTTP_OK` there) | minor |
| Error responses asserted beyond status | A 400/404/422 test that only asserts the code, ignoring the body | major |

### TypeScript (Vitest + fetch + Zod) specifics

| Check | Bad sign | Severity |
|---|---|---|
| No `any` in DTOs, schemas, or response handling | `as any`, `: any`, `Record<string, any>` in spec or client | major |
| Response bodies validated with the Zod schema in the spec | Spec reads `res.body.someField` without `Schema.parse(res.body)` first | major |
| `await` present on every async assertion / call | `expect(promise).resolves.toBe(x)` with no `await`, or unawaited `fetch(...)` | blocker |
| `fetch` calls set `Content-Type: application/json` for bodied requests | POST/PUT without a `content-type` header | major |
| Every request has a status-code assertion | Spec parses body but never checks `res.status` | major |
| Base URL and auth pulled from `process.env.API_BASE_URL` / `process.env.API_KEY` | Hardcoded `http://...` or literal API key in spec/client | blocker |
| No `setTimeout`-based waits | `await new Promise(r => setTimeout(r, 1000))` | blocker |
| Structural assertions, not bare `toBeDefined()` | `expect(body).toBeDefined()` as the only check on a happy-path body | major |
| No mutation of module-level state across tests | Top-level `let currentUser = ...` reassigned inside `it(...)` blocks | major |
| `describe` grouping per resource / endpoint | Flat list of `it(...)` with no `describe` | minor |
| Token rotation respected where required | One auth token harvested in `beforeAll` and reused across all tests when rotation matters | major |
| Client never throws on 4xx/5xx — returns `ApiResponse<T>` | Client throws inside `request(...)` on `!res.ok` | major |
| Client never validates schemas internally | `Schema.parse(...)` inside the client instead of the spec | major |
| `expect.soft(...)` used deliberately, not as a default | Every assertion is soft, so nothing actually fails the test | minor |
| `it.each([...])` for parameterized cases instead of `if`/`for` | Conditional logic driving assertions inside an `it(...)` | major |
| Test titles describe behavior | `'works'`, `'test 1'`, `'returns ok'` (no behavior or input named) | minor |
| Use `safeParse` (or `parse`) consistently per project convention | Mixed `parse` / `safeParse` without a stated reason | nit |
| 401 test uses a single status-code assertion | A 401 test that tries to `ProblemDetailsSchema.parse(res.body)` on an empty body | minor |
| Cleanup in `afterEach` / `afterAll` wrapped in `try/catch` | Bare cleanup that swallows test failures if it throws | major |

## Smells to flag (TypeScript-specific quick list)

1. `any` in DTOs / response handling — **major**
2. Skipping `Schema.parse(res.body)` on 2xx responses — **major**
3. Missing `await` in `expect(...).resolves.X` chains — **blocker**
4. `fetch` without `Content-Type` on POST/PUT — **major**
5. Missing `expect(res.status).toBe(...)` assertion — **major**
6. Hardcoded URLs / tokens — **blocker**
7. `setTimeout`-based waits — **blocker**
8. Loose `expect(x).toBeDefined()` instead of structural assertions — **major**
9. Mutating shared module-level state across tests — **major**
10. Missing `describe` grouping per resource / endpoint — **minor**
11. Reusing one auth token across tests where token rotation matters — **major**
12. Client throws on 4xx/5xx instead of returning `ApiResponse<T>` — **major**
13. Schema validation done inside the client instead of the spec — **major**
14. Conditional logic (`if`/`for`) driving assertions — **major**
15. `// eslint-disable` to silence Zod / strict-mode errors — **minor**

## Good signals (counter-list)

- Every response body on a 2xx path goes through `Schema.parse(res.body)` and the parsed object — not `res.body` — is asserted against.
- 4xx tests parse with `ProblemDetailsSchema` and assert `title`, `status`, and the relevant `errors[field]` entries.
- Clients return `ApiResponse<T>` with `{ status, body }`; nothing throws on non-2xx.
- Auth state is fixed in the client constructor (`new UserClient(true)`) — not per call, not via shared module state.
- Test titles read like behavior sentences: `'returns 401 when the api key is invalid'`, `'returns 400 with field-level errors when email is missing'`.
- Each `it(...)` constructs its own client; no top-level `let` reassigned between tests.
- `it.each([...])` is used for parameterized cases — no `if (x) expect(...)`.
- `tsc --noEmit` passes; `strict: true` is on in `tsconfig.json`; no `any` in the diff.
- Cleanup in `afterEach` / `afterAll` is wrapped in `try/catch` so cleanup errors do not mask test failures.

## Procedure

1. Confirm imports show Vitest + Zod (`import { describe, it, expect } from 'vitest';`, `import { z } from 'zod';`).
2. Read the whole spec **plus** the imported `*Client.ts` **plus** the Zod schema module before writing findings — most real bugs are cross-file (e.g. client throws on 4xx so the 4xx spec is dead code).
3. Walk the cross-stack checklist, then the TS-specific list, then the smells quick list.
4. For each finding, capture: file + line, the issue (concrete, not "looks weird"), and a one-sentence fix.
5. **Do not rewrite the code.** Hand off to `qa/api-test-author/generator/typescript` if the user wants the rewrite.

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------|
| blocker  | tests/specs/user.spec.ts:42                       | `expect(client.get(1, 12)).resolves.toBeDefined()` not awaited | Add `await` — unawaited `.resolves` chains pass on failures            |
| blocker  | tests/clients/UserClient.ts:18                    | `baseUrl = 'http://localhost:3000'` hardcoded               | Read from `process.env.API_BASE_URL`; fail fast in `tests/setup.ts`    |
| major    | tests/specs/user.spec.ts:67                       | Happy-path body asserted via `toBeDefined()` only           | `UserSchema.parse(res.body)` then assert structural fields             |
| major    | tests/clients/UserClient.ts:34                    | Client throws when `!res.ok`                                | Return `ApiResponse<T>`; spec asserts the failure path                 |
| minor    | tests/specs/user.spec.ts:10                       | All `it(...)` flat, no `describe`                           | Wrap in `describe('GET /users', () => { ... })`                        |
| nit      | tests/specs/user.spec.ts:14                       | Test title `'test 1'`                                       | Rename to behavior: `'returns the first page of users'`                |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, hard rule violation (missing `await`, hardcoded secrets, `setTimeout` waits, shared state)
- **major** — design / correctness issue that will hurt soon (silent failures, lost coverage, `any` types, wrong layering)
- **minor** — style / small inconsistency (naming, grouping)
- **nit** — optional preference

## Anti-patterns to always flag

- **Unawaited async assertion.** `expect(promise).resolves.toBe(x)` without `await` is a no-op — Vitest cannot fail the test.
- **Status-code-only 4xx test.** When the backend emits `ProblemDetails`, asserting just the status throws away the highest-signal failure information.
- **`toBeDefined()` as the only happy-path assertion.** It will pass on any non-`undefined` body, including a wrong-shape one.
- **Schema validation inside the client.** Couples the client to a response shape and prevents the spec from asserting on raw error bodies. Parse in the spec.
- **Client that throws on 4xx/5xx.** The 4xx spec then becomes dead `try/catch` and never asserts the body.
- **`any` to silence strict mode.** Defeats the entire point of Zod + TS. Tighten the schema and let `z.infer` produce the type.
- **Hardcoded base URL or API key.** Always `process.env.*`; the setup file should fail fast if env vars are missing.
- **Mutating module-level state.** Top-level `let` reassigned by tests destroys independence — tests must build their own state.
- **Reusing one bootstrapped auth token across the suite** when the backend rotates tokens. Authenticate per-test (or per fixture) to match real client behavior.
- **`setTimeout`-based waits.** Use Vitest retry helpers (`vi.waitFor`) or polling on a concrete condition.

## Generation / Review steps

1. Identify whether the file is a spec, client, or schema. Each layer has its own rules.
2. For a **spec** review:
   - Status code asserted first?
   - Body parsed with the Zod schema (`Schema.parse(res.body)`) before being read?
   - Structural assertions on the parsed object — not `toBeDefined()`?
   - Test title describes behavior?
   - `describe` grouping per resource / endpoint?
   - Each `it` constructs its own client (no shared mutable state)?
3. For a **client** review:
   - Returns `ApiResponse<T>` and never throws on 4xx/5xx?
   - Auth chosen via constructor flag (`new XClient(true)`), not per call?
   - Base URL from `process.env.API_BASE_URL`?
   - No schema validation in the client?
   - `Content-Type: application/json` set on bodied requests?
4. For a **schema** review:
   - Tightened primitives (`.email()`, `.url()`, `.datetime()`, `.int()`, `.min(...)`)?
   - Types inferred via `z.infer<typeof Schema>` — no hand-written `interface` duplicating the schema?
   - `ProblemDetailsSchema` reused from a shared module, not copy-pasted?
5. Produce findings in the table above. **Do not rewrite.** Hand off to `qa/api-test-author/generator/typescript`.

## Handoffs

- Need a rewrite → `qa/api-test-author/generator/typescript`
- Schemas / DTOs need fixing → `qa/api-dto-writer/typescript`
- Client layer needs refactor → `qa/api-client-writer`
- Whole test pyramid is the issue → `qa/_shared/test-strategy`
- .NET sibling → `qa/api-test-author/reviewer/dotnet`
- Java sibling → `qa/api-test-author/reviewer/java`

## Changelog

- 2026-05-28: Authored as a TypeScript sibling to the .NET and Java reviewers. Rules align with `qa/api-test-author/generator/typescript` (Vitest + native fetch + Zod, Schema/Client/Spec layering).
- References consulted while authoring:
  - [How to Test Your Node.js RESTful API with Vitest: Unit & Integration Testing — danioshi.substack.com](https://danioshi.substack.com/p/how-to-test-your-nodejs-restful-api)
  - [Request Validation at the Edge: Zod Schemas, OpenAPI, and Type-Safe APIs (2026) — dev.to](https://dev.to/young_gao/request-validation-at-the-edge-zod-schemas-openapi-and-type-safe-apis-1kib)
