---
paths:
  - "**/tests/{api,integration,clients,schemas,operations,proto}/**/*.ts"
  - "**/{api-tests,apitests}/**/*.ts"
  - "**/src/specs/**/*.ts"
  - "**/*{Seeder,Probe}.ts"
---

<!-- qa-typescript rules v1 (2026-11-03): API tests. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its API suite. -->

# API test standards (Vitest + fetch + Zod, Playwright `request`, GraphQL, gRPC)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Every request goes through a `{resource}Client`; no raw `fetch` or `request.get` in a spec. Native `fetch` under Vitest, the `request` fixture under Playwright; no axios, got or supertest. *major*
- A raw client method returns the envelope unparsed and unasserted; the typed one calls it, asserts the status and Zod-parses. A client never fetches a token (the spec passes one, `''` for anonymous), reads `process.env` or catches around `execute`. *major*
- Assert the exact status first (`toBe(201)`, never `toBeOK()`). Typed method for the happy path, raw for negative cases; error bodies are parsed (`ProblemDetailsSchema`) and asserted beyond the status. *major*
- Parse every body before reading a field; no `JSON.parse`, `as any`, or `toBeDefined()` as the only check. Types come from `z.infer`, primitives tightened (`.email()`, `.uuid()`); DTOs are types, never classes. *major; minor for tightening*
- A write is proven by reading it back, not by the echoed payload. *major*
- GraphQL: the gate is the `errors` envelope; the client returns `{ data, errors }` and never throws; variables are never interpolated; a partial response asserts `data` and the `errors[]` entry by `path` and `extensions.code`. *major*
- gRPC: assert the gRPC status and `google.rpc.Status` details, never an HTTP code; a call resolves on success and failure; one client per file, closed in `afterAll`. *major*
- A scheduled job is triggered, never awaited on its real schedule; a time boundary runs on a controlled clock; a race uses a barrier and repeats. *blocker for waiting on a schedule, else major*
- SQL in a probe or seeder binds every value (`$1`). *blocker*
- Probes are read-only with explicit columns and typed projections; seeders write through builders; one shared pool. *major*
- Databases come from Testcontainers: pinned image, mapped port, the app's own migrations; never a shared dev database or a logged connection string. *major*
