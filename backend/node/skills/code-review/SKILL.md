---
name: conventions-review
description: Use when reviewing TypeScript code (Node / NestJS / Express, strict mode) for type-safety leaks, async correctness, pattern misuse, missing discriminated-union exhaustiveness, or runtime-validation gaps. Triggers: "review this TS service", "audit for `any` usage", "is this CQRS justified", "check runtime validation at boundaries". Do NOT use for explanations (`pattern-guide`), generating code (`pattern-writer`), or React (`frontend/react/skills/code-review`).
---

# TypeScript Design Patterns — Reviewer

Reviews TypeScript code (strict mode) against the patterns in `backend/node/skills/pattern-writer`, the global rules in `CLAUDE.md`, and TS-specific idioms (discriminated unions, `Result` types, branded ids, Zod at boundaries). Produces a findings table; does not rewrite.

## When to use

- Diff / file submitted (service, handler, repository, config)
- Pre-merge gate on PRs touching `src/features/`, `src/shared/`, `src/api/`
- Audit for type-safety leaks (`any`, `as`)
- Sanity-check whether CQRS / repository / etc. are earning their cost

## When NOT to use

- Conceptual lookup → `backend/node/skills/pattern-guide`
- Generating code → `backend/node/skills/pattern-writer`
- React → `frontend/react/skills/code-review`
- API tests → `qa/typescript/skills/api-test-author/review`

## Review checklist

### Strict-mode hygiene

| Check | Bad sign | Severity |
|---|---|---|
| No `any` | `: any`, `as any`, `as unknown as X` | major |
| No `@ts-ignore` / `@ts-expect-error` without comment + fix date | Bare suppressions | major |
| `noUncheckedIndexedAccess` honored | Direct `arr[i]` access then `.foo` without narrowing | major |
| `strictNullChecks` honored | `value!` non-null assertions everywhere | major |
| `exactOptionalPropertyTypes` honored | `foo?: T` accepting `undefined` and `T \| undefined` interchangeably | minor |
| No `Function` / `Object` types | Use specific signatures | minor |
| Discriminated unions over enums | `enum Status` instead of `'pending' \| 'paid' \| ...` | minor |

### Discriminated unions & exhaustiveness

| Check | Bad sign | Severity |
|---|---|---|
| `switch` on a discriminator has `never` exhaustiveness check | Missing default that asserts `const _: never = x` | major |
| New union member breaks every consumer (good) | Adding a member without compile-error cascade — narrowing snuck in | major |
| Class hierarchy where a tagged union would do | `abstract class Pricing` with two subclasses, no dynamic dispatch needed | minor |

### Errors & control flow

| Check | Bad sign | Severity |
|---|---|---|
| Domain failures → `Result<T, E>` | `throw new Error('not found')` for a domain case the caller expects | major |
| Thrown errors are unrecoverable bugs / boundaries | `try { ... } catch { return null }` everywhere | major |
| No `.then().catch()` chains for new code | Promise chains instead of `async/await` | minor |
| No `new Promise` wrapping promise-returning APIs | Unnecessary promise-pyramid | major |
| `unknown` in `catch` narrowed before use | `catch (e) { console.log(e.message) }` without narrowing | major |
| Rejected promises not orphaned | `void someAsync()` with no error path | major |
| `AbortController` / `signal` threaded through long-running calls | No cancellation path for HTTP / DB calls | minor |

### Runtime validation at boundaries

| Check | Bad sign | Severity |
|---|---|---|
| External input parsed via Zod (or equivalent) | `req.body as MyDto` | major |
| Config validated at startup | `process.env.X` read in business code | major |
| Branded ids used across boundaries | `UserId` and `OrderId` typed as raw `string` | minor |
| Response bodies validated when consuming third-party APIs | `await fetch(...).json() as Foo` | major |

### Pattern application

| Check | Bad sign | Severity |
|---|---|---|
| One pattern per problem | Repository + Service + Mapper + Mediator + Decorator on a CRUD slice | major |
| Modules reach each other only through the owner's public API (the exported `index.ts` facade) | A module reading another module's table, entity or non-`index.ts` file — a cross-schema join, a deep import past `index.ts` | major |
| Repository earns its keep | Wrapping Prisma 1:1 with `find/save/delete` | major |
| CQRS justified | Lightweight CQRS for a 2-endpoint service | major |
| Class vs function appropriate | Class with no state / one method | minor |
| HOF decorators have one concern | `withLoggingRetryCachingMetrics` | major |

### Async & concurrency

| Check | Bad sign | Severity |
|---|---|---|
| `Promise.all` for independent work | Sequential `await` of independent fetches | major |
| `Promise.allSettled` when partial failure is OK | `Promise.all` failing whole batch on one error | minor |
| No mixed sync / async signatures | `function foo(): Promise<T> \| T` | major |
| `for await ... of` for async iteration | Mixed manual iteration + promise chains | minor |

### Module / project hygiene

| Check | Bad sign | Severity |
|---|---|---|
| ESM imports (`type: "module"` in package.json) | Mixing `require` and `import` | minor |
| No mutable module-level state | `let cache = new Map()` at module scope used as a singleton | major |
| Configuration loaded once via `loadConfig()` | `process.env.X` reads scattered | major |
| Files exporting one thing per file when reasonable | Catch-all `index.ts` exporting everything | nit |

### DI (when present)

| Check | Bad sign | Severity |
|---|---|---|
| Constructor injection | Service locator (`container.resolve('X')`) in business code | major |
| Dependencies passed explicitly | Globals / singletons consumed implicitly | major |
| NestJS providers have correct scope | Request-scoped service consumed by a singleton without `REQUEST_SCOPE` | major |

### Comments & TSDoc

Load **[`engineering-practices/code-comments`](../../../../engineering-practices/code-comments/SKILL.md)** for the rule itself, the complex-flow test that earns a doc comment, the never-comment trivia list, and the severity mapping. This section supplies only the mechanics that differ here.

| TypeScript mechanic | What to check |
|---|---|
| Doc syntax | TSDoc (`/** … */`) |
| Suppressions needing a reason | `@ts-expect-error`, `eslint-disable` — a bare one is **major**, it usually hides a real type defect |
| Directives, not comments — these stay | Decorators, Zod schemas, lint/TS pragmas |
| Scaffolding to remove | `create-*` / Nest CLI scaffold comments in hand-written files |

**The `Result<T, E>` corollary:** the error variants belong in the *type*, not in a comment listing them. A comment enumerating failure modes means the union should be widened — the type is the documentation.

## Procedure

1. Read the file end-to-end before findings
2. Walk the checklists; strict-mode hygiene and runtime-validation first
3. Per finding: file + line, concrete issue, one-sentence fix
4. Hand off to `backend/node/skills/pattern-writer` if a rewrite is requested

## Output format

```
| Severity | Location                                          | Issue                                                       | Suggested fix                                                                          |
|----------|---------------------------------------------------|-------------------------------------------------------------|----------------------------------------------------------------------------------------|
| blocker  | src/api/order-routes.ts:42                       | `req.body as CreateOrderDto` — no runtime validation        | Parse with `CreateOrderDto.parse(req.body)`; reject 400 on schema error                |
| major    | src/features/orders/create-order.ts:33           | Throws `Error('out-of-stock')` for a domain case            | Return `Result<OrderId, 'out-of-stock'>` so callers handle without try/catch          |
| major    | src/features/orders/pricing.ts:14                | `switch (mode.kind)` has no exhaustiveness check             | Add `const _: never = mode.kind;` after the switch                                     |
| minor    | src/shared/types.ts:9                            | `enum OrderStatus` with 4 members                            | Use string literal union: `type OrderStatus = 'pending' \| 'paid' \| ...`              |
```

Severities per `CLAUDE.md`.

## Anti-patterns to always flag

- **`any` / `as any` / `as unknown as X`** — fix the type
- **`req.body as DTO`** — unvalidated external input
- **`process.env.X` in business code** — load via `loadConfig`
- **Throwing for domain failures the caller expects to handle** — `Result<T, E>`
- **`switch` without exhaustiveness** — add the `never` check
- **`Promise.all` on dependent work** — should be sequential
- **Sequential `await` on independent work** — should be `Promise.all`
- **Mutable module-level state** masquerading as a singleton
- **`new Promise((res, rej) => ...)` wrapping a promise-returning API** — just return the promise
- **Class with one method and no state** — that's a function
- **`enum`** in new code — use string union types
- **`!` non-null assertion** to "tell TS it's not null" — usually means a real bug
- **`for...in` over arrays** — use `for...of` / `.forEach` / `.map`
- **`.toString()` swallowing `Error.stack`** — pass the error to the logger
- **`unknown` in `catch` accessed as `e.message`** — narrow first
- **Comments compensating for naming, and stale comments** — per `engineering-practices/code-comments`; a comment enumerating error cases means the `Result` union should be widened

## Handoffs

- Need a rewrite → `backend/node/skills/pattern-writer`
- Conceptual lookup → `backend/node/skills/pattern-guide`
- React review → `frontend/react/skills/code-review`
- API test review → `qa/typescript/skills/api-test-author/review`
