---
paths:
  - "**/*{ApiTests,IntegrationTests,E2ETests,AcceptanceTests,TestCore}/**/{Db,Database,Probes,Seeders}/**"
  - "**/*{ApiTests,IntegrationTests,E2ETests,AcceptanceTests,TestCore}/**/*{Probe,Seeder,DbFixture,ConnectionFactory}.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): database verification. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its seeders, probes and database fixtures. -->

# Database verification standards (tests that seed and probe a real database)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Seeders write, probes read, the system under test acts. One `DbConnectionFactory` per fixture, a connection opened per call; no `new NpgsqlConnection` in a test. *major*
- Every value is a bound parameter: never interpolated, never `string.Join` into `IN (...)`; only literals owned by the test shape the SQL. *blocker*
- A probe projects explicit columns into a `sealed record`, never `SELECT *` or an ORM entity; `EXISTS` for a boolean, `COUNT(*)` as `long`, `Guid` / `long` / `DateTimeOffset` for uuid / bigint / timestamptz. *major*
- No destructive verb outside the designated cleanup; reset rows with Respawn between tests. *major*
- An eventually-consistent row is awaited with the polling helper, never `Task.Delay`. *blocker*
- The schema comes from the production migrations, never `EnsureCreated()` or a test schema. *major*
- A container is pinned to the production version tag, never `latest`; started in `[OneTimeSetUp]`, never per test; host and port read from the container. *major*
- Fixtures sharing a database are `ParallelScope.None` unless isolation is proven. *major*
- One data-access library per concern (Dapper or EF, not both); rows the tests write are namespaced (`tenant=test`). *minor*
- Never log or attach a connection string or parameter values. *blocker*
