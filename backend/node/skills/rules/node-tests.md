---
paths:
  - "apps/api/**/*.{test,spec}.ts"
  - "**/{server,backend}/**/*.{test,spec}.ts"
  - "**/*.{controller,service,guard,interceptor,resolver,repository}.{test,spec}.ts"
---

<!-- be-node rules v1 (2026-11-03): tests. Installed by /be-node:rules; edit the paths above to where this project keeps its backend tests. -->

# Node backend test standards (Vitest)

Severity tags as in the core be-node rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- A unit test calls the function or constructs the class with `new`, never through a DI container, and never calls `app.init()` or `listen()`. Supertest, a booted app, a container or a live dependency make it an integration test, under its own include pattern. *major*
- No Prisma/Drizzle query, migration or transaction is unit-tested with a mock: `mockDeep<PrismaClient>()` and SQLite standing in for Postgres prove nothing. A real engine, in the integration lane. *major*
- `describe` names the unit; `it('should <outcome> when <condition>')` states behaviour. *minor*
- One logical assertion per test, and each expects one value, never "this or that". *major*
- No `try`/`catch` in a test (`await expect(p).rejects.toThrow(Type)`), no `if`/`for` driving assertions (`it.each`), no `setTimeout` waiting (inject the clock or `await vi.advanceTimersByTimeAsync`); every promise is awaited. *major*
- Inject the clock, ids, randomness, config and outbound ports instead of `vi.mock`. Never mock a type you don't own (`fetch`, `PrismaClient`, an SDK), the module under test, or a method of the class under test. *major*
- No `any` or `as unknown as` to force a fake; narrow the interface instead. *major*
- Both branches of every `Result` are tested. A Zod test asserts `issues[].path` and `code`, never the message. *major*
- No snapshot as the only assertion, no assertion on the logger, no test of the framework, no `@ts-expect-error` into private state. *minor*
- `vi.useFakeTimers()` is paired with `vi.useRealTimers()`; no `it.skip` without a linked issue. *minor*
- Test data with four or more fields comes from a builder or a factory with a partial override. *minor*
- New code ships with unit tests covering at least 80% of the branches it wrote, measured with `vitest --coverage`; only an asserting test counts, and no `/* v8 ignore */` over code with behaviour. *major*
