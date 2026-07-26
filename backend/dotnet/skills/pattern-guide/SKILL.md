---
name: be-dotnet-pattern-guide
description: Use when the user asks to explain, describe, or look up a design pattern in C#/.NET (10 primary, 8-9 supported). Triggers: "what is the strategy pattern in C#", "explain CQRS with MediatR", "when should I use the repository pattern in .NET". Do NOT use for scaffolding code into a repo (use backend/dotnet/skills/pattern-writer) or for reviewing existing code (use backend/dotnet/skills/code-review).
---

# .NET Design Patterns — Reference

Conceptual reference for design patterns as applied in C# / .NET. **.NET 10 is primary; 8 and 9 are supported.** Pattern cards explain intent, when to use, when not to, and show canonical minimal examples — the DI/records/primary-constructor idioms shown are current across all three; version-specific divergence is called out inline where it exists.

## Version policy

Detect the project's `<TargetFramework>` (`net8.0` / `net9.0` / `net10.0`) before answering — never up-level a down-level project's examples, and never flag a down-level project for lacking a net10-only API. Primary constructors, `required`/`init`, keyed DI services, and `sealed` defaults apply across 8/9/10; nothing in this file below is net10-exclusive.

## When to use

- The user asks "what is pattern X in .NET"
- The user wants a comparison between two patterns
- The user wants a small canonical example, not scaffolding into their repo

## When NOT to use

- The user wants code generated into their project — use `backend/dotnet/skills/pattern-writer`
- The user wants their code critiqued — use `backend/dotnet/skills/code-review`
- The user wants the language-agnostic "what & when" of a pattern, not the C# code — use `backend/_shared/pattern-guide`

---

## Strategy

**Intent**: Encapsulate interchangeable algorithms behind a common interface so the caller can swap them without changing call-site code.

**When to use**:
- You have an `if`/`else` or `switch` chain that selects behavior based on a type or flag
- New variants are added regularly
- Variants share a clear shape (same inputs and outputs)

**When NOT to use**:
- There are only two variants and you don't expect more — a simple `bool` or method overload is cheaper
- The variants don't share a clean input/output contract — you'll bend the interface

**Minimal example**:

```csharp
public interface IPricingStrategy
{
    decimal Apply(decimal listPrice, Customer customer);
}

public sealed class StandardPricing : IPricingStrategy
{
    public decimal Apply(decimal listPrice, Customer _) => listPrice;
}

public sealed class LoyaltyPricing : IPricingStrategy
{
    public decimal Apply(decimal listPrice, Customer customer) =>
        customer.YearsActive >= 5 ? listPrice * 0.9m : listPrice;
}

// Registration (Program.cs)
builder.Services.AddKeyedSingleton<IPricingStrategy, StandardPricing>("standard");
builder.Services.AddKeyedSingleton<IPricingStrategy, LoyaltyPricing>("loyalty");

// Consumer
public sealed class CheckoutService(
    [FromKeyedServices("loyalty")] IPricingStrategy pricing)
{
    public decimal Quote(Order o) => pricing.Apply(o.ListPrice, o.Customer);
}
```

**Common mistakes**:
- Making the strategy interface huge ("god strategy"). One method is the norm; two is the limit.
- Selecting strategies inside the strategy itself (then it's not a strategy, it's a chain).
- Forgetting to register all variants in DI — fails at runtime, not compile time.

**Related patterns**:
- `Factory` — often used to pick the right strategy
- `Chain of Responsibility` — when the variants form a sequence, not a choice

---

## Repository

**Intent**: Provide a collection-like abstraction over data access so business code is unaware of the storage mechanism.

**When to use**:
- You need to swap the storage implementation (real DB ↔ in-memory ↔ external API)
- Domain logic needs to be testable without spinning up a database
- The abstraction adds something — e.g. multiple data sources composed into one view

**When NOT to use**:
- You're just wrapping `DbContext` to "be clean." EF Core's `DbSet<T>` is already a repository. Wrapping it adds indirection with no abstraction gain.
- The repository ends up with one method per query — at that point it's a query class, not a repository.

**Minimal example**:

```csharp
public interface IOrderRepository
{
    Task<Order?> GetAsync(OrderId id, CancellationToken ct);
    Task AddAsync(Order order, CancellationToken ct);
    Task<IReadOnlyList<Order>> FindRecentByCustomerAsync(CustomerId id, CancellationToken ct);
}

public sealed class OrderRepository(AppDbContext db) : IOrderRepository
{
    public Task<Order?> GetAsync(OrderId id, CancellationToken ct) =>
        db.Orders.FirstOrDefaultAsync(o => o.Id == id, ct);

    public async Task AddAsync(Order order, CancellationToken ct)
    {
        await db.Orders.AddAsync(order, ct);
    }

    public async Task<IReadOnlyList<Order>> FindRecentByCustomerAsync(
        CustomerId id, CancellationToken ct) =>
        await db.Orders
            .Where(o => o.CustomerId == id && o.PlacedAt > DateTime.UtcNow.AddDays(-30))
            .ToListAsync(ct);
}
```

**Common mistakes**:
- Exposing `IQueryable<T>` from the repository. That leaks EF semantics back to the caller.
- Calling `SaveChangesAsync()` inside `AddAsync()`. Persistence is a unit-of-work concern; the repository just stages changes.
- Generic `IRepository<T>` with `Find(Expression<...>)`. That's just `DbContext` with extra steps.

**Related patterns**:
- `Unit of Work` — coordinates commit across repositories
- `Specification` — encapsulates query criteria, useful with repository

---

## Mediator (with MediatR)

**Intent**: Route requests through an intermediary so senders and handlers don't reference each other directly.

**When to use**:
- You're applying CQRS and want commands/queries handled by isolated handlers
- You want cross-cutting concerns (logging, validation, transactions) added as pipeline behaviors
- You have a thick controller / endpoint and want to thin it out

**When NOT to use**:
- A simple service injection would do. MediatR adds a layer of indirection that costs readability.
- Your handlers are calling each other through the mediator — that's hidden coupling.

**Minimal example**:

```csharp
public sealed record GetOrder(OrderId Id) : IRequest<Order?>;

public sealed class GetOrderHandler(IOrderRepository repo) : IRequestHandler<GetOrder, Order?>
{
    public Task<Order?> Handle(GetOrder request, CancellationToken ct) =>
        repo.GetAsync(request.Id, ct);
}

// Endpoint
app.MapGet("/orders/{id}", async (Guid id, IMediator mediator) =>
{
    var order = await mediator.Send(new GetOrder(new OrderId(id)));
    return order is null ? Results.NotFound() : Results.Ok(order);
});
```

**Common mistakes**:
- Putting business logic in pipeline behaviors. Behaviors are for cross-cutting concerns only.
- One handler calling `mediator.Send` to invoke another handler — couples them invisibly.
- Skipping validation pipeline and validating inside the handler — duplicated across handlers.

**Related patterns**:
- `CQRS` — Mediator is the usual implementation vehicle
- `Pipeline` (Chain of Responsibility) — what behaviors actually are

---

## Coverage checklist

Patterns this skill covers (or should cover — expand over time):

- [x] Strategy
- [x] Repository
- [x] Mediator
- [ ] Factory
- [ ] Builder
- [ ] Decorator
- [ ] Adapter
- [ ] Facade
- [ ] Observer
- [ ] Command
- [ ] Chain of Responsibility
- [ ] Template Method
- [ ] Specification
- [ ] Unit of Work
- [ ] CQRS (full)
