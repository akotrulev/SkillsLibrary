---
paths:
  - "**/.editorconfig"
  - "**/Directory.Build.props"
  - "**/BannedSymbols*.txt"
---

<!-- be-dotnet rules v1 (2026-11-21): analyzers. Ids checked against the analyzers' documentation on 2026-11-21 (SDK 10.0, EF Core 10, Threading.Analyzers 18, BannedApiAnalyzers 5, NUnit.Analyzers 4). Installed by /be-dotnet:rules; edit the paths above to where this project keeps its analyzer config, re-run to compare with the plugin's copy. -->

# .NET analyzer standards (backend)

Severity tags as in the core .NET rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `dotnet.md`, `dotnet-persistence.md` or `dotnet-tests.md` that an analyzer detects, so the build catches it before a review does. Rules no stock analyzer detects stay in those files and get no row: constructor injection, a service locator, static mutable state, `CancellationToken` on every async method.

## Enforced by the build

| House rule | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` (`dotnet.md`, Async) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD002` | error |
| No `async void` (`dotnet.md`, Async) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD100` | error |
| A `CancellationToken` is passed on to the calls that take one (`dotnet.md`, Async) | .NET SDK analyzers | `CA2016` | error |
| Log calls use message templates, never interpolation (`dotnet.md`, Errors, logging and telemetry) | .NET SDK analyzers | `CA2254` | error |
| Rethrow with `throw;`, never `throw ex;` (`dotnet.md`, Errors, logging and telemetry) | .NET SDK analyzers | `CA2200` | error |
| Catch specific exceptions, never `catch (Exception)` or a bare `catch` (`dotnet.md`, Errors, logging and telemetry) | .NET SDK analyzers | `CA1031` | error |
| `HttpClient` comes from `IHttpClientFactory`, never `new HttpClient()` (`dotnet.md`, Dependency injection) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `HttpClient` constructor in `BannedSymbols.txt` | error |
| Time and ids are injected seams: no `DateTime.Now`/`UtcNow`, `DateTimeOffset.Now`/`UtcNow`, `Guid.NewGuid()` (`dotnet.md`, Layering) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, those members in `BannedSymbols.txt` | error |
| Raw SQL is parameterized, never interpolated or concatenated (`dotnet-persistence.md`) | EF Core analyzers (`Microsoft.EntityFrameworkCore.Analyzers`, installed with EF Core) | `EF1002`; `EF1003` too from EF Core 10 | error |
| Lazy loading stays off (`dotnet-persistence.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `ProxiesExtensions` in `BannedSymbols.txt` | error |
| No `Database.Migrate()` or `EnsureCreated()` in the app (`dotnet-persistence.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, those members in `BannedSymbols.txt` | error |
| Nullable is enabled in every project (`dotnet.md`, State and types) | MSBuild | `<Nullable>enable</Nullable>` in `Directory.Build.props` | setting |
| A unit test never sleeps or delays; it advances a `FakeTimeProvider` (`dotnet-tests.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `Thread.Sleep` and `Task.Delay` in `BannedSymbols.Tests.txt` | error |
| A unit test never uses `UseInMemoryDatabase` (`dotnet-tests.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `InMemoryDbContextOptionsExtensions` in `BannedSymbols.Tests.txt` | error |
| A test method returns `Task`, never `void` (`dotnet-tests.md`) | `NUnit.Analyzers` | `NUnit1012` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `dotnet_diagnostic.<id>.severity = error` in `.editorconfig`. The analyzer packages are `PackageReference`s with `PrivateAssets="all"` in `Directory.Build.props`.
- Every `RS0030` row is one line in a `BannedSymbols` file, added to the project as `<AdditionalFiles Include="BannedSymbols.txt" />`. Production projects get `BannedSymbols.txt`, test projects add `BannedSymbols.Tests.txt`.
- `VSTHRD100` flags an event handler too, and `Microsoft.VisualStudio.Threading.Analyzers` turns on `VSTHRD200` (the `Async` suffix) as a warning, which `TreatWarningsAsErrors` makes an error. No house rule asks for either: a handler carries a `[SuppressMessage]` with its `Justification`, and the project sets `VSTHRD200` to `suggestion`.
- A boundary that must catch everything (a global exception handler) suppresses `CA1031` with a `Justification`; the same goes for the one place that applies migrations.

`BannedSymbols.txt`:

```
M:System.Net.Http.HttpClient.#ctor;Use a typed client from IHttpClientFactory
P:System.DateTime.Now;Inject TimeProvider
P:System.DateTime.UtcNow;Inject TimeProvider
P:System.DateTimeOffset.Now;Inject TimeProvider
P:System.DateTimeOffset.UtcNow;Inject TimeProvider
M:System.Guid.NewGuid;Inject an id generator
T:Microsoft.EntityFrameworkCore.ProxiesExtensions;Lazy loading stays off
M:Microsoft.EntityFrameworkCore.RelationalDatabaseFacadeExtensions.Migrate(Microsoft.EntityFrameworkCore.Infrastructure.DatabaseFacade);The pipeline applies migrations
M:Microsoft.EntityFrameworkCore.RelationalDatabaseFacadeExtensions.MigrateAsync(Microsoft.EntityFrameworkCore.Infrastructure.DatabaseFacade,System.Threading.CancellationToken);The pipeline applies migrations
M:Microsoft.EntityFrameworkCore.Infrastructure.DatabaseFacade.EnsureCreated;The pipeline applies migrations
M:Microsoft.EntityFrameworkCore.Infrastructure.DatabaseFacade.EnsureCreatedAsync(System.Threading.CancellationToken);The pipeline applies migrations
```

`BannedSymbols.Tests.txt`:

```
M:System.Threading.Thread.Sleep(System.Int32);Advance a FakeTimeProvider
M:System.Threading.Thread.Sleep(System.TimeSpan);Advance a FakeTimeProvider
M:System.Threading.Tasks.Task.Delay(System.Int32);Advance a FakeTimeProvider
M:System.Threading.Tasks.Task.Delay(System.TimeSpan);Advance a FakeTimeProvider
T:Microsoft.EntityFrameworkCore.InMemoryDbContextOptionsExtensions;Use the real engine in the integration lane
```
