---
name: be-dotnet-reviewer
description: Use when the user asks to review C# / .NET (10 primary, 8-9 supported) code for design-pattern misuse, over-abstraction, hidden coupling, async violations, or DI anti-patterns. Triggers: "review this for pattern misuse", "is this CQRS justified", "check for service-locator usage", "spot smells in this service", "review my DI registration". Do NOT use for explanations (use `backend/dotnet/skills/reference`) or for generating new code (use `backend/dotnet/skills/generator`).
---

# .NET Design Patterns — Reviewer

Reviews C# / .NET code — **10 primary, 8/9 supported** — against the patterns and rules enforced by `backend/dotnet/skills/generator` and the global rules in `CLAUDE.md`. Produces a findings table in the format defined in `CLAUDE.md`. Does **not** rewrite — points to the fix and lets the human apply it.

## Version policy

Detect the reviewed project's `<TargetFramework>` first. Don't flag a net8/net9 project for lacking a net10-only feature (e.g. a newer `[Timestamp]`/collection-expression idiom); do flag a net10 project that ignores one available to it as a `minor`/`nit` per the usual severity rules.

## When to use

- A diff or file is submitted for review (service, handler, DI registration, decorator, repository)
- Pre-merge gate on a PR that touches `Application/` / `Infrastructure/` / `Program.cs` / `*Module.cs`
- The user wants a second opinion on whether a pattern is earning its complexity
- A pattern feels "off" and the user wants the smell named

## When NOT to use

- Conceptual lookup → `backend/dotnet/skills/reference`
- Generating new code → `backend/dotnet/skills/generator`
- Reviewing API tests → `qa/dotnet/skills/api-test-author/reviewer`
- Reviewing UI tests → `qa/dotnet/skills/ui-test-author/reviewer`

## Inputs needed

1. **Files** under review (service, handler, registration, decorator)
2. **Context** — new feature, refactor, bug fix?
3. **Surrounding architecture** if it matters (Onion / Clean / vertical slices) — affects severity of layer-crossings
4. **Project conventions** that override defaults (e.g. project standardized on Autofac instead of MS DI)

## Review checklist

Severity column maps directly to the output table.

### Async & threading

| Check | Bad sign | Severity |
|---|---|---|
| No sync-over-async | `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` | blocker |
| `CancellationToken` threaded through every async method | A `Task` method that takes no `CancellationToken` argument | major |
| No `async void` outside event handlers | `public async void HandleX(...)` | blocker |
| No `Task` returned from a method named `*Sync` | `public Task DoSync()` | major |
| No `Task.Run` to "make it async" | `await Task.Run(() => SyncWork())` for I/O | major |

### Dependency injection

| Check | Bad sign | Severity |
|---|---|---|
| Constructor injection only | Field/property injection without a constructor source | major |
| No service locator | `IServiceProvider.GetService<T>()` inside business code | major |
| Lifetimes match dependency lifetimes | Singleton consuming Scoped (captures stale scope) | blocker |
| One registration block per module | DI calls sprinkled across `Program.cs` | minor |
| Decorators registered in the right order | Order undocumented or inverted (real impl outside cache) | major |
| `IOptions<T>` over `IConfiguration[...]` reads | Stringly-typed configuration in business code | major |
| `IOptionsSnapshot<>` / `IOptionsMonitor<>` chosen for the right lifetime | Singleton holding an `IOptions<T>` that ships changes | major |

### Pattern application

| Check | Bad sign | Severity |
|---|---|---|
| One pattern per problem — no stacking | Repository + UoW + Specification + Mediator + Decorator on a CRUD slice | major |
| Repository earns its keep | `IFooRepository` that mirrors `DbSet<Foo>` 1:1 with `Get/Add/Update/Delete` | major |
| CQRS justified | MediatR adopted on a service with one read + one write | major |
| Strategy / Factory replace `switch` chains | `switch (type) { case ... }` repeated across the codebase | major |
| Decorators have one responsibility | One class doing logging + retry + caching | major |
| Mediator pipeline behaviors for cross-cutting | Validation, logging, metrics duplicated in each handler | major |

### Nullability & types

| Check | Bad sign | Severity |
|---|---|---|
| Nullable reference types enabled per project | `<Nullable>` missing or `disable` | major |
| No `!` to silence the compiler | `x!.Foo` instead of `?.`, `ArgumentNullException.ThrowIfNull`, or a real fix | major |
| `record` for value-shaped data, `class` for behavior | A mutable `class` with public init-only props pretending to be a value type | minor |
| `sealed` by default on concretes | Public concrete class with no `sealed` and no real subclass | minor |
| Primary constructors used where appropriate | Boilerplate `private readonly Foo _foo; public Bar(Foo foo) { _foo = foo; }` for a trivial DI ctor | nit |

### Static state & mutability

| Check | Bad sign | Severity |
|---|---|---|
| No static mutable state | `private static List<Foo> _cache = new();` | blocker |
| Constants explicitly `const` / `static readonly` | Mutable `static` field used as if it were a constant | major |
| Immutability for DTOs / value objects | `class Order { public List<Line> Lines { get; set; } }` exposing mutable lists | major |
| `IReadOnlyList<>` / `IReadOnlyCollection<>` on read-only surfaces | `List<T>` returned where callers shouldn't mutate | minor |

### Logging & exceptions

| Check | Bad sign | Severity |
|---|---|---|
| Message templates, not interpolation | `_logger.LogInformation($"Order {id}")` | major |
| `ILogger<T>` injected, not `Log.Logger` static | Direct `Serilog.Log.*` calls in service code | minor |
| Exceptions passed as the first arg | `_logger.LogError(ex.ToString(), ...)` | major |
| Specific exception types caught | `catch (Exception ex)` swallowing everything | major |
| No re-throw losing stack trace | `catch (Exception ex) { throw ex; }` | major |

### Architecture / dependencies

| Check | Bad sign | Severity |
|---|---|---|
| Domain has no infra dependencies | `Domain/` referencing `Microsoft.EntityFrameworkCore` | major |
| Application orchestrates, doesn't know HTTP | Controllers calling `DbContext` directly | major |
| Infrastructure adapters implement Application interfaces | Application code newing up infrastructure types | major |
| Cross-feature references go through public contracts | Feature A reaching into Feature B's `Internal/` | major |

## Procedure

1. Read the whole file before writing findings.
2. Walk the checklists, top to bottom. Lifetime and async issues are usually the highest-severity ones — start there.
3. For each finding: file path + line, the issue (concrete), one-sentence fix.
4. **Do not rewrite the code.** Hand off to `backend/dotnet/skills/generator` if the user wants the rewrite.

## Output format

```
| Severity | Location                          | Issue                                                              | Suggested fix                                                              |
|----------|-----------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------|
| blocker  | Application/Orders/OrderService.cs:54 | `_repo.GetAsync(id).Result` — sync-over-async                  | `await _repo.GetAsync(id, ct)`; thread `CancellationToken` through         |
| blocker  | Application/Modules.cs:18         | Singleton `OrderService` depends on Scoped `AppDbContext`          | Register `OrderService` as Scoped, or extract a Scoped accessor service    |
| major    | Application/Pricing/PricingService.cs:33 | `switch (cart.Mode)` selects pricing algorithm inline       | Extract to `IPricingStrategy` + keyed DI; remove the switch                |
| minor    | Application/Orders/OrderService.cs:12 | Concrete `OrderService` is not `sealed`                       | Mark `sealed` unless inheritance is part of the design                     |
```

Severities (from `CLAUDE.md`):
- **blocker** — ships a bug, violates a hard rule (sync-over-async, lifetime mismatch, static mutable state)
- **major** — design / correctness issue that will hurt soon (wrong pattern choice, leaky abstraction, missing nullability)
- **minor** — style / small inconsistency (naming, missing `sealed`, hand-rolled boilerplate)
- **nit** — optional preference

## Anti-patterns to always flag

- **Anemic interface that has one implementation forever.** Wait for the second concrete before extracting the interface.
- **Repository that wraps `DbSet<T>` 1:1.** It pays the abstraction cost without delivering any indirection value.
- **Mediator on a CRUD slice.** If your handler is `_db.Add(...); await _db.SaveChangesAsync();`, MediatR is a tax.
- **God service.** `IOrderService` with 22 methods spanning 3 bounded contexts.
- **`Task.Run` to wrap I/O.** Drops to a thread for no reason; the I/O was already async.
- **Singleton consuming Scoped.** The scope captured at construction is wrong forever after.
- **`catch (Exception)` followed by `return default`.** Swallows the failure; the test passes; production silently corrupts.
- **`DbContext` injected into every service.** A `DbContext` injected widely tends to become the "service" — push behind a real abstraction or keep it in a thin data layer.
- **Decorators with two concerns.** "LoggingAndRetryDecorator" — split.
- **`public abstract class XBase` with one subclass.** Subclassing isn't the pattern; composition is.

## Handoffs

- Need a rewrite → `backend/dotnet/skills/generator`
- Conceptual lookup → `backend/dotnet/skills/reference`
- Java review of similar issues → `backend/java/skills/reviewer`
- TypeScript review → `backend/node/skills/reviewer`
- Test-side reviews → `qa/dotnet/skills/api-test-author/reviewer` / `qa/dotnet/skills/ui-test-author/reviewer`
- Language-agnostic pattern/architecture altitude review → `backend/_shared/reviewer`
