---
paths:
  - "**/*{DbContext,Repository}.cs"
  - "**/{Persistence,Data,Entities,Configurations,Migrations}/**/*.cs"
  - "**/*.{Persistence,Data}/**/*.cs"
---

<!-- be-dotnet rules v1 (2026-11-03): persistence. Installed by /be-dotnet:rules; edit the paths above to where this project keeps its DbContext, entities and migrations. -->

# EF Core persistence standards

Severity tags as in the core .NET rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- `DbContext` is scoped, one per bounded context, never a singleton and never shared across threads or `Task.WhenAll` branches. *blocker*
- One provider per `DbContext`; one `IEntityTypeConfiguration<T>` per entity, `OnModelCreating` only applies them. *minor*
- Entities: a private parameterless constructor plus a factory method, `required`/`init` members, a private collection behind an `IReadOnlyList<T>`. *major*
- Columns snake_case with explicit names; indexes named explicitly. *minor*
- A concurrency token on every aggregate several actors write, matching the provider (`rowversion` on SQL Server, `xmin` as `uint` on Npgsql); `DbUpdateConcurrencyException` is handled, never swallowed. *major; blocker for a token that contradicts the provider*
- Lazy loading off. *major*
- Reads use `AsNoTracking()` and project to a DTO with `Select`; no `Include` before a projection, no `ToList` before `Where`, no query inside a loop over parents (N+1). *major*
- A `Find`/`FirstOrDefaultAsync` result is null-checked before it is changed. *major*
- No `SaveChangesAsync` in a loop; bulk changes use `ExecuteUpdateAsync`/`ExecuteDeleteAsync`. *major; minor for a bulk loop*
- Raw SQL is parameterized (`FromSqlInterpolated` or parameters), never concatenated. *blocker*
- Explicit transactions only where several writes must commit together, and never around an HTTP call. *major*
- Migrations are under source control, one logical change each, forward-only in production, applied by the pipeline: no `Database.Migrate()` or `EnsureCreated()` at startup, and one migration tool per project. *major*
- A repository earns its keep; one that mirrors `DbSet<T>` with `Get/Add/Update/Delete` is the `DbSet` again. *major*
