---
paths:
  - "**/src/{test,integrationTest,testFixtures}/java/**/{builders,mothers,db,probes,seeders}/**/*.java"
  - "**/src/{test,integrationTest,testFixtures}/java/**/*{Builder,Mother,Probe,Seeder}.java"
---

<!-- qa-java rules v1 (2026-11-03): test data and DB verification. Installed by /qa-java:rules; edit the paths above to where this project keeps its builders, seeders and probes. -->

# Test data and database verification standards

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Builders

- One builder per aggregate; every field has a valid, deterministic default (no `null` for a required field). Randomness only on id-like fields, seeded, never on a field a test asserts. *major*
- `.build()` returns the real type, is pure and idempotent, throws no checked exception, and copies collections (`List.copyOf`). *minor*
- An ObjectMother returns a builder unless no test varies the object. No persistence in a builder, no reflection "build anything" library. *minor*

## Seeders and probes

- Seeders write, probes read, the system under test acts; each class has one job, takes its `DataSource` by constructor. *major*
- SQL binds named parameters only, never concatenation, `String.join` for `IN`, or a runtime-built `WHERE`. *blocker*
- A probe projects explicit columns (no `SELECT *`) into a record; `SELECT EXISTS` for booleans, `COUNT(*)` as `Long`; `timestamptz` maps to `Instant` / `OffsetDateTime`. *major*
- No destructive SQL outside the designated cleanup, no `Flyway.clean()`, no `@Sql` shaping per-test data. *major*
- An eventually consistent row is polled with Awaitility on the probe. *blocker for a sleep*
- No `@Transactional` rollback on a test that calls the app over HTTP; the server's writes are not undone. *major*
- Log the probe name and ids, never SQL with bound values or a JDBC URL. *blocker*

## Testcontainers

- A pinned image tag, never `latest`; one container per JVM or class, never per method; no H2 beside it. *major*
- Connection via `@DynamicPropertySource`; the schema comes from migrations, never `ddl-auto=create`. *major*
