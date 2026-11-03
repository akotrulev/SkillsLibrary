---
paths:
  - "**/*.prisma"
  - "**/prisma/**"
  - "**/drizzle/**"
  - "**/drizzle.config.ts"
  - "**/*.{repository,entity}.ts"
  - "**/{persistence,repositories}/**/*.ts"
---

<!-- be-node rules v1 (2026-11-03): persistence. Installed by /be-node:rules; edit the paths above to where this project keeps its schema, migrations and data access. -->

# Node persistence standards (Prisma / Drizzle / TypeORM)

Severity tags as in the core be-node rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One ORM per project: Prisma by default, Drizzle where SQL composability matters; no new project on TypeORM. *major*
- Schema and migrations live in source control. `migrate dev` runs on a laptop only, `migrate deploy` (or `drizzle-kit`) from the pipeline; the app never migrates at startup. *major*
- Columns are snake_case (`@map`), money is `BigInt` minor units, timestamps are `timestamptz` with precision. *minor*
- One client per process; never a new client or a `$disconnect()` per request. Never two ORMs, or Prisma and a raw `pg` pool, sharing connections. *major*
- `select` what the read needs and `take` on every collection query, with cursor paging; no `include` three levels deep. *major*
- A multi-step write runs in `$transaction`; no `findFirst`-then-update outside one. *major*
- An aggregate with concurrent writers carries a `version` column, updated with `updateMany` where the version matches (`@VersionColumn` in TypeORM). *major*
- `PrismaClientKnownRequestError` is matched on `e.code`, never swallowed. *major*
- A `BigInt` is converted explicitly before it reaches `JSON.stringify`. *major*
- A repository wrapper only when it earns its keep; never a 1:1 `find`/`save`/`delete` over Prisma. *major*
- Raw SQL is a tagged template (`$queryRaw`, Drizzle `sql`) with bound parameters, never concatenated into `$queryRawUnsafe`. *blocker*
- Every DB call is traced (Prisma tracing or `instrumentation-pg`). *minor*
