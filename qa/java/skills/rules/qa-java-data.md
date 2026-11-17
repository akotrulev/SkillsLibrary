---
paths:
  - "**/src/{test,integrationTest,testFixtures}/java/**/{builders,mothers,db,probes,seeders}/**/*.java"
  - "**/src/{main,test}/java/**/{factory,factories}/**/*.java"
  - "**/src/{test,integrationTest,testFixtures}/java/**/*{Builder,Mother,Probe,Seeder}.java"
---

<!-- qa-java rules v2 (2026-11-17): test data and DB verification. Installed by /qa-java:rules; fit the paths above to the project. -->

# Test data and database verification standards

Severity tags as in the core qa-java rules; the codebase wins.

## Data a test uses

- Read-only reference data (search, filter) is curated, named in the test or feature, never modified; assert a row came back before asserting on rows. *blocker for no guard*
- A precondition may delete a leftover first (setup or a `Given … does not exist` step), via API or seeder. *minor*
- Keep on failure: teardown deletes on pass and logs kept ids on fail (a legal branch); names are unique per run. *major*

## Builders

- One builder per aggregate; every field has a valid, deterministic default (never `null` when required). Randomness only on seeded id-like fields no test asserts. *major*
- `.build()` returns the real type, is pure and idempotent, throws no checked exception, copies collections (`List.copyOf`). *minor*
- An ObjectMother returns a builder unless no test varies the object. No persistence in a builder, no reflection "build anything" library. *minor*

## Seeders and probes

- Seeders write, probes read, the system under test acts; one job per class, its `DataSource` or HTTP client by constructor. *major*
- SQL binds named parameters only, never concatenation, `String.join` for `IN`, or a runtime-built `WHERE`. *blocker*
- A probe projects named columns (no `SELECT *`) into a record; `SELECT EXISTS` for booleans, `COUNT(*)` as `Long`; `timestamptz` maps to `Instant` / `OffsetDateTime`. *major*
- No destructive SQL outside the designated cleanup, no `Flyway.clean()`, no `@Sql` shaping per-test data. *major*
- An eventually consistent row is polled with Awaitility on the probe. *blocker for a sleep*
- No `@Transactional` rollback on a test that calls the app over HTTP. *major*
- Log the probe name and ids, never SQL with bound values or a JDBC URL. *blocker*

## Testcontainers

- A pinned image tag, never `latest`; one container per JVM or class, never per method; no H2 beside it. *major*
- Connection via `@DynamicPropertySource`; schema from migrations, never `ddl-auto=create`. *major*
