---
name: patterns-apply
description: Use when the user asks to scaffold a design pattern in C# / .NET (10 primary, 8-9 supported) into the active repo. Triggers: "scaffold strategy in C#", "create a repository pattern for X", "wire up a MediatR command handler for Y", "add a decorator for Z", "extract this if-else chain into a strategy". Do NOT use for explanations (use `backend/dotnet/skills/pattern-guide`) or reviews (use `backend/dotnet/skills/code-review`).
---

# .NET Design Patterns — Generator

Scaffolds pattern implementations into a .NET codebase — **.NET 10 primary, 8/9 supported**. Each pattern lands as constructor-injected services with nullable reference types on, immutable records where applicable, and one logical change per file. Hooks into the project's DI container and produces tests alongside the implementation.

## Version policy

**First act: detect the target project's `<TargetFramework>`** (check the `.csproj`) and key generated code to what's detected — never up-level a net8/net9 project to a net10-only API, and never flag a down-level project for lacking one. Everything in this file (primary constructors, keyed DI, records, `required`/`init`) works unmodified on 8, 9, and 10 unless noted otherwise.

## When to use

- Replacing an `if`/`else` or `switch` chain with a strategy
- Wrapping a service with a decorator (logging, retry, caching, validation)
- Introducing CQRS with MediatR for a slice that has earned the complexity
- Adding a repository or specification pattern when there is a genuine abstraction need
- Building a factory / abstract factory when construction is non-trivial and reused
- Extracting an Options pattern from scattered configuration reads

## When NOT to use

- Explaining a pattern → `backend/dotnet/skills/pattern-guide`
- Critiquing existing code → `backend/dotnet/skills/code-review`
- Scaffolding tests against a generated pattern → `backend/dotnet/skills/unit-testing` for the class-level tests; `qa/dotnet/skills/api-test-author/writer` (peer) once it's reachable over HTTP

## Inputs needed

1. **Pattern** to scaffold (Strategy, Decorator, Repository, Specification, Factory, Mediator/Handler, Options, Pipeline/Chain)
2. **Domain** + **concrete variants** (for Strategy: which algorithms; for Decorator: which behaviors)
3. **Target project** and folder layout (`Application/` vs `Domain/` vs `Infrastructure/` — Onion / Clean Arch boundaries)
4. **DI container** in use (`Microsoft.Extensions.DependencyInjection`, Autofac, etc.) — Microsoft default unless told otherwise
5. **Existing call site** to refactor (paste or path) — anchors the rename / extraction

## Generation steps (per pattern)

### Strategy

1. Define the abstraction: `public interface I<Verb>Strategy { Task<TResult> ExecuteAsync(TInput input, CancellationToken ct); }`
2. One file per concrete strategy under `Application/Strategies/{Domain}/`
3. Register all in DI with **named** or **keyed** services (`AddKeyedScoped`, available since .NET 8)
4. Replace the `switch` at the call site with a resolver: `_strategies[input.Type]`
5. Add a test fixture per strategy + one for the resolver — conventions in `backend/dotnet/skills/unit-testing`

```csharp
public interface IPricingStrategy
{
    Task<Money> CalculateAsync(Cart cart, CancellationToken ct);
}

services.AddKeyedScoped<IPricingStrategy, StandardPricing>("standard");
services.AddKeyedScoped<IPricingStrategy, B2BPricing>("b2b");

// Call site
var strategy = _provider.GetRequiredKeyedService<IPricingStrategy>(cart.PricingMode);
var price = await strategy.CalculateAsync(cart, ct);
```

### Decorator

1. Decorator implements the same interface and takes the inner instance via the constructor
2. Register inner first, then decorate via `Scrutor` (`services.Decorate<IFoo, FooLoggingDecorator>()`) or manual factory
3. One concern per decorator — logging, retry, caching, validation, metrics; don't fuse two
4. Order matters and must be documented: cache → retry → logging → real impl (cache outermost, real impl innermost)

```csharp
public sealed class OrderServiceLoggingDecorator(IOrderService inner, ILogger<IOrderService> log) : IOrderService
{
    public async Task<Order> PlaceAsync(NewOrder o, CancellationToken ct)
    {
        log.LogInformation("Placing order for {CustomerId}", o.CustomerId);
        var result = await inner.PlaceAsync(o, ct);
        log.LogInformation("Placed order {OrderId}", result.Id);
        return result;
    }
}

services.AddScoped<IOrderService, OrderService>();
services.Decorate<IOrderService, OrderServiceLoggingDecorator>();
services.Decorate<IOrderService, OrderServiceRetryDecorator>();
```

### Repository (only when there is a real abstraction need)

Do **not** wrap EF Core just to "have a repository". Only generate when:
- There are multiple data sources behind one logical store (EF + cache + API), OR
- The query language is too leaky for the domain layer to call directly, OR
- A clear set of named queries earns the type

```csharp
public interface IOrderRepository
{
    Task<Order?> GetAsync(OrderId id, CancellationToken ct);
    Task<IReadOnlyList<Order>> FindByCustomerAsync(CustomerId customerId, int take, CancellationToken ct);
    Task AddAsync(Order order, CancellationToken ct);
}
```

Implementation file uses `DbContext` via constructor injection. Add a unit-of-work only when crossing multiple repositories in one transaction is a real requirement.

### Specification

For repository queries that combine in non-trivial ways (`active && in-region && not-recently-contacted`), generate `Specification<T>` with `And`/`Or`/`Not` composition. Compile to `Expression<Func<T, bool>>` for EF Core to translate.

### Factory / Abstract Factory

When `new X(...)` requires non-trivial decisions (which subtype, which dependencies), wrap in a factory interface that the call site asks. The factory itself uses DI for its dependencies.

```csharp
public interface IPaymentGatewayFactory
{
    IPaymentGateway Create(PaymentProvider provider);
}

internal sealed class PaymentGatewayFactory(IServiceProvider sp) : IPaymentGatewayFactory
{
    public IPaymentGateway Create(PaymentProvider provider) => provider switch
    {
        PaymentProvider.Stripe => sp.GetRequiredService<StripeGateway>(),
        PaymentProvider.Adyen  => sp.GetRequiredService<AdyenGateway>(),
        _ => throw new ArgumentOutOfRangeException(nameof(provider)),
    };
}
```

### Mediator + Command/Query Handler (MediatR)

Only when the project has earned CQRS — a real read-vs-write asymmetry, > ~30 endpoints, or cross-cutting concerns that benefit from pipeline behaviors. State the reason in a comment on the request.

```csharp
public sealed record PlaceOrder(CustomerId Customer, IReadOnlyList<Line> Lines) : IRequest<OrderId>;

internal sealed class PlaceOrderHandler(IOrderRepository repo, IClock clock) : IRequestHandler<PlaceOrder, OrderId>
{
    public async Task<OrderId> Handle(PlaceOrder request, CancellationToken ct)
    {
        var order = Order.Place(request.Customer, request.Lines, clock.UtcNow);
        await repo.AddAsync(order, ct);
        return order.Id;
    }
}
```

Pipeline behaviors (`IPipelineBehavior<,>`) are the right place for cross-cutting validation / logging / metrics — not the handler.

### Options pattern

Replace scattered `IConfiguration["..."]` reads with strongly-typed options bound from configuration, validated at startup.

```csharp
public sealed class OrdersOptions
{
    [Required] public required string PricingMode { get; init; }
    [Range(1, 1000)] public int MaxLines { get; init; } = 100;
}

services.AddOptions<OrdersOptions>()
    .Bind(configuration.GetSection("Orders"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

Inject as `IOptions<OrdersOptions>` (root scope), `IOptionsSnapshot<>` (per-scope reload), or `IOptionsMonitor<>` (singletons that need live updates) — pick based on the consumer's lifetime.

### Pipeline / Chain of Responsibility

For request preprocessing (auth → throttle → validate → handle): use ASP.NET Core middleware for HTTP-shaped pipelines, MediatR `IPipelineBehavior<,>` for command pipelines, or a hand-rolled chain for in-process stages. Don't reinvent middleware.

## Module boundaries

For a modular monolith built to be split later (blueprint `Modules:` line) — one folder per module, one schema, one public surface, one architecture test. An existing codebase keeps the architecture it has; apply this to new modules only where the project already has module folders.

- **One public API per module.** `I<Module>Api` and its DTO records live in the module's root namespace (`Shop.Modules.Orders`); an entity never crosses it. Every other type is `internal` and sits in `Shop.Modules.Orders.Internal`. `internal` only stops a reach-in across assemblies, so a single-assembly monolith leans on the architecture test below; split a module into its own project when the compiler should enforce it.
- **One schema and one `DbContext` per module.** `modelBuilder.HasDefaultSchema("orders")` and `o.MigrationsHistoryTable("__EFMigrationsHistory", "orders")`. A module holds another module's id as a plain column — no navigation property to a foreign entity, no foreign key into its schema, no `Include` across modules.
- **A call between modules** is a constructor-injected `I<Other>Api`. **An event** is a record in the publisher's root namespace, raised through a plain in-process dispatcher, and only when a second consumer or "must not fail the publisher" earns it; no message bus.
- **One DI extension per module** (`AddOrdersModule`) and one test folder per module.
- **The architecture test** fails the build on a reach-in. It uses `TngTech.ArchUnitNET` with `TngTech.ArchUnitNET.NUnit`, loads the architecture once, and runs with the unit tests. (NetArchTest.Rules has had no release since 2021 — do not use it.) `ResideInNamespace` is shown with the full namespace; confirm in the installed ArchUnitNET version whether sub-namespaces match, which is why the internals stay in one flat `.Internal` namespace per module.

```csharp
using ArchUnitNET.Domain;
using ArchUnitNET.Loader;
using ArchUnitNET.NUnit;
using static ArchUnitNET.Fluent.ArchRuleDefinition;

[TestFixture]
public sealed class ModuleBoundaryTests
{
    private static readonly Architecture Architecture =
        new ArchLoader().LoadAssemblies(typeof(Program).Assembly).Build();

    [TestCase("Billing", "Orders")]
    [TestCase("Orders", "Billing")]
    public void Should_NotDependOnInternals_When_ModuleCallsAnotherModule(string caller, string owner)
    {
        var callerTypes = Types().That().ResideInNamespace($"Shop.Modules.{caller}")
            .Or().ResideInNamespace($"Shop.Modules.{caller}.Internal");
        var ownerInternals = Types().That().ResideInNamespace($"Shop.Modules.{owner}.Internal");

        Types().That().Are(callerTypes).Should().NotDependOnAny(ownerInternals)
            .Because($"{caller} may use {owner} only through its public API")
            .Check(Architecture);
    }
}
```

Add one `TestCase` per ordered module pair when a module is added; the first contract task writes the fixture, and a later task that needs a new dependency calls the owner's public API instead of editing the test.

## Rules

- Constructor injection only — primary constructors (`public sealed class Foo(IDep dep)`, available since .NET 8) keep boilerplate down
- No service locator (`IServiceProvider.GetService<T>`) except in factories that legitimately need it
- Nullable reference types enabled; no `!` to silence the compiler — fix the type
- Records for value-shaped data, classes for behavior-bearing services
- `sealed` by default on concrete classes — open them only when inheritance is part of the design
- Async all the way — `CancellationToken` on every async method, threaded through
- DI registration goes in a single `IServiceCollection` extension per area (`AddOrdersModule(this IServiceCollection)`) — never sprinkled across `Program.cs`
- One pattern per problem — flag stacking (Repository + Specification + UoW + Mediator + Decorator on one slice) as a smell; only stack when each layer earns its keep
- File per type; namespace matches folder; `internal` by default for implementations, `public` only on contracts the consumer needs

## What NOT to do

- No abstract base classes when an interface + composition does the job
- No "I-have-one-implementation" interfaces just to "decouple" — wait for the second
- No Repository wrapping `DbContext` 1:1 with `Get/Add/Update/Delete` — that's the `DbSet` again with extra cost
- No CQRS without a real read/write asymmetry — the ceremony hurts more than it helps for CRUD
- No `Task.Result` / `.Wait()` / `.GetAwaiter().GetResult()` in production code
- No static service locator (`ServiceLocator.Current.Resolve<T>`)
- No mutable static state in pattern implementations (constants are fine)
- No `params object[]` on a pattern interface to "make it flexible" — design the contract for the real callers
- No newing up dependencies inside a class — they go through the constructor
- No `if (provider == "stripe") ... else if (provider == "adyen")` in a service when there's a factory for that

## Generation outputs

For every pattern, produce:

1. The contract (interface or abstract record) in `Domain/` or `Application/Contracts/`
2. Concrete implementations one per file in the matching `Application/<Pattern>/` or `Infrastructure/`
3. A DI extension `Add<Feature>(this IServiceCollection)` registering all of them
   - **In a modular monolith** the first scaffold also produces the module folders, the `I<Module>Api` per module, a `DbContext` with its schema each, and the architecture-test fixture (Module boundaries)
4. Unit-test fixture(s) for every logic-bearing type produced — **conventions, seams, and doubles policy live in `backend/dotnet/skills/unit-testing`** (NUnit 4 + NSubstitute, `Assert.That` + `Assert.Multiple`). Once the pattern is reachable over HTTP, the contract/integration layer is the **peer** `qa-api-dotnet`'s

## Validation

After scaffolding, run the checks below — unless you are inside a plan task marked `Gate: none`, which runs none of them and reports "written, not run":

- `dotnet build` — 0 warnings (treat warnings as errors in `Directory.Build.props`)
- `dotnet test` — the generated tests must pass
- `dotnet format --verify-no-changes` — no style drift
- Sweep call sites that the new pattern was supposed to replace; if any old `if`/`else` / `switch` chains remain, finish the refactor

## Handoffs

- Conceptual explanation → `backend/dotnet/skills/pattern-guide`
- Reviewing the result → `backend/dotnet/skills/code-review`
- Unit-testing the generated classes → `backend/dotnet/skills/unit-testing`
- Generating tests for the new API (contract/integration) → **peer** `qa/dotnet/skills/api-test-author/writer`
- DTOs for new endpoints → `qa/dotnet/skills/api-models`
- Java equivalent → `backend/java/skills/pattern-writer`
- TypeScript equivalent → `backend/node/skills/pattern-writer`
