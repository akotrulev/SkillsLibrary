---
paths:
  - "apps/api/**/*.ts"
  - "**/{server,backend}/**/*.ts"
  - "**/*.{controller,service,module,guard,interceptor,resolver}.ts"
---

<!-- be-node rules v1 (2026-11-03): core. Installed by /be-node:rules; the paths above are where this project keeps its backend TypeScript, so add its backend packages; re-run to compare with the plugin's copy. -->

# Node / TypeScript backend code standards

Apply these to every backend TypeScript file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Persistence, test and config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the Node major (`engines`, `.nvmrc`, the lockfile) and the framework (NestJS, Express, Fastify, bare) before writing. Node 24 is primary and 22 maintenance; Node 20 is past end of life, so flag it and do not target it.

## Simplicity

- Write the simplest thing that meets the requirement, then stop. No interface with one implementer, no layer that only forwards, no config knob nothing sets, no generic parameter with one instantiation. An abstraction is earned on the second real need. *major, fix by inlining*
- One pattern per problem. Repository + service + mapper + mediator + decorator on one CRUD slice is stacking. *major*
- Command/query handlers only where reads and writes really differ, never for a two-endpoint service. *major*
- A class with no state and one method is a function. *minor*
- A higher-order-function decorator has one concern, not `withLoggingRetryCaching`. *major*
- Cut structure, never correctness: validation, error handling, disposal, cancellation and tests stay.

## Types

- No `any`, `as any` or `as unknown as X`; take `unknown` and narrow. *major*
- No `!` non-null assertion to quiet the compiler, and no indexed access used unnarrowed. *major*
- A closed set of cases is a discriminated union; its `switch` ends in `const _exhaustive: never = x`, never a fallback `default`. *major*
- No `enum`, `namespace`, `Function` or `Object` type: use a string-literal union or `as const`, modules, and real signatures. *minor*
- Ids that cross a boundary are branded types, not raw `string`. *minor*
- No nullable boolean; pick a default. `T | null` or a `Result`, never an Optional-style wrapper. *minor*
- Money is integer minor units or a decimal library, never a float `number`. *major*

## Errors and async

- A failure the caller is expected to handle is a `Result<T, E>`; throw only for bugs and true exceptions, and never both in one function. *major*
- No `catch` that swallows (`catch { return null }`); a caught `unknown` is narrowed before `.message`. *major*
- `async`/`await`; no `.then().catch()` chains in new code. *minor*
- No `new Promise` around an API that already returns one. *major*
- No floating promise: every promise is awaited or given an error path. *major*
- Independent awaits run in `Promise.all` (`allSettled` when partial failure is fine); dependent ones run in sequence. *major*
- No `Promise<T> | T` signature. *major*
- Long-running HTTP and DB calls take an `AbortSignal`. *minor*

## Boundaries, DI and state

- External input is parsed with Zod (or the project's equivalent) at the boundary, never `req.body as Dto`; a third-party response body too, never `await res.json() as Foo`. *major*
- Config is read once through a Zod-validated `loadConfig()`; no `process.env` outside it. *major*
- Constructor injection for classes, closures for functional modules; never a service locator (`container.resolve`) in business code. *major*
- No mutable module-level state (`let cache = new Map()`); constants are fine. *major*
- A request-scoped NestJS provider is never consumed by a singleton. *major*
- ESM imports; no `require` in new code. *minor*

## Logging, telemetry and secrets

- One logger (pino), object first: `logger.info({ orderId }, 'order placed')`. No `console.log`, no interpolated message, no `JSON.stringify` in a log call. *major*
- An error is logged once, where it is handled, as `{ err }` so the stack survives; never `err.toString()`. *major*
- New behaviour (an entry point, an outbound call, a background job, a business event) is instrumented as it is built: a log at each decision point, a span around the operation where auto-instrumentation misses it, and a business metric with low-cardinality labels. *major*
- No secret or personal data in a log line, span attribute or metric label, and no secret in code; read it from the environment or a secret store. *blocker*

## Architecture

- A controller or route handler is transport only; logic in it moves down to a service or function. *major*
- In a modular monolith a module reaches another only through that module's `index.ts`: no deep import, no relation or join into its schema. *major*

## Comments

- No comments inside function bodies: no step markers, no restating the next line, no commented-out code, no `TODO`. Extract and name the step instead. *minor; major when the comment is wrong*
- TSDoc only where the name cannot carry the meaning: a non-obvious business rule, a constraint on callers, a deliberate deviation and its reason, or a contract the signature cannot state. Error cases belong in the `Result` type, not a comment listing them. *nit*
- `@ts-expect-error` and `eslint-disable` state their reason; a bare one is *major*. Scaffold comments from `create-*` or the Nest CLI are removed. *minor*
