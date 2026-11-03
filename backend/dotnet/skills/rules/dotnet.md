---
paths:
  - "**/*.{Api,WebApi,Application,Domain,Infrastructure,Persistence,Data,Worker}/**/*.cs"
---

<!-- be-dotnet rules v1 (2026-11-03): core. Installed by /be-dotnet:rules; edit the paths above to where this project keeps its backend code, re-run to compare with the plugin's copy. -->

# C# / .NET backend code standards

Apply these to every backend C# file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Persistence, API, unit-test and appsettings rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect every project's `<TargetFramework>` before writing (EF Core's major matches it): never use an API the TFM lacks (`Activity.AddException` needs net9, so use the portable `RecordException`), and never flag a down-level project for lacking one.

## Simplicity and patterns

- Write the simplest thing that meets the requirement, then stop. No interface with one implementer, no abstract base with one subclass, no layer that only forwards, no god service, no config knob nothing sets. An abstraction is earned on the second real need. *major, fix by inlining*
- One pattern per problem. Repository + Unit-of-Work + Specification + Mediator + Decorator on one CRUD slice is stacking. *major*
- MediatR/CQRS only for a real read/write asymmetry, never on a CRUD slice; cross-cutting validation, logging and metrics go in one pipeline behavior, not in every handler. *major*
- A `switch` on type or mode repeated across services becomes a strategy or factory selected by key (keyed DI). *major*
- A decorator has one concern, and the registration order is explicit. *major*
- Cut structure, never correctness: validation, error handling, disposal, cancellation and tests stay.

## Dependency injection

- Constructor injection only; never `new` a dependency inside a class. *major*
- No service locator (`GetService<T>`/`GetRequiredService<T>`) in business code; only a factory that needs it. *major*
- A singleton never consumes a scoped service (`DbContext` above all). *blocker*
- Registrations live in one `Add<Module>(this IServiceCollection)` extension per module, not across `Program.cs`. *minor*
- Configuration through `IOptions<T>` bound with `ValidateOnStart()`, never `IConfiguration["…"]` in business code; `IOptionsMonitor<T>` in a singleton that must see changes. *major*
- `HttpClient` only as a typed client from `IHttpClientFactory`, with a timeout and a resilience handler; retries only on idempotent calls. *major*

## Async

- No `.Result`, `.Wait()` or `.GetAwaiter().GetResult()`. *blocker*
- No `async void` outside event handlers. *blocker*
- Every async method takes a `CancellationToken` and passes it down. *major*
- No `Task.Run` around I/O, no `lock` around an `await`, no fire-and-forget without a failure path; background work is a `BackgroundService` that honours its stopping token. *major*

## State and types

- No static mutable state; constants are `const` or `static readonly`. *blocker*
- Nullable enabled in every project; no `!` or `#nullable disable` to silence a warning. *major*
- Records for value-shaped data; DTOs and value objects immutable, read-only surfaces typed `IReadOnlyList<T>`. *major for an exposed mutable list, minor otherwise*
- Concrete classes `sealed`, implementations `internal`, unless the design needs otherwise. *minor*
- An aggregate enforces its invariants through a factory or guard, not through public setters. *major*
- No `dynamic` or `object` where a type exists. *major*
- One type per file; namespace matches the folder. *minor*

## Layering

- `Domain` references no EF Core, `HttpClient` or cloud SDK; application code never `new`s an infrastructure type; infrastructure implements interfaces the application owns. *major*
- A module or feature reaches another only through its public `I<Module>Api`: no `using` of its `Internal` namespace, no navigation or `Include` across modules, no join into its schema. *major*
- `DateTime.UtcNow`, `Guid.NewGuid()`, randomness and `Environment.*` are injected seams (`TimeProvider`, an id generator, options), never called in logic; no `if (env == "Test")` hooks. *major*

## Errors, logging and telemetry

- Catch specific exceptions; never swallow (`catch { return default; }`); rethrow with `throw;`, never `throw ex;`. *major*
- `ILogger<T>` with message templates (`LogInformation("Order {OrderId} placed", id)`), never interpolation; the exception is the first argument, logged once where it is handled. *major*
- New behaviour (an entry point, an outbound call, a background job, a business event) is instrumented as built: a log at each decision point, a span around the operation where auto-instrumentation misses it, a metric per business event. *major*
- One `ActivitySource` and one `Meter` per subsystem, `static readonly`; span names are operation names, never built from data; an error span gets `SetStatus(Error)` and the exception recorded. *major*
- Per-record ids are span attributes, never metric tags. *blocker*
- No secret or personal data in a log line, span attribute or metric tag; no secret, connection string or hard-coded URL in code. *blocker; major for a URL*

## Comments

- No comments inside method bodies: no step markers, no restating the next line, no commented-out code, no `TODO`. Extract and name the step instead. *minor; major when the comment is wrong*
- XML doc only where the name cannot carry the meaning: a non-obvious rule, a constraint on callers, a deliberate deviation and its reason, or a contract (`<exception>`). Never on properties, DTOs, records or a self-describing member. *nit*
- `#pragma warning disable` and `[SuppressMessage]` carry their justification; template and IDE header comments are removed. *minor*
