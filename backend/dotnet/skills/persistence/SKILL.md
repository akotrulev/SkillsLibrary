---
name: be-dotnet-persistence
description: Use when setting up or refactoring persistence in .NET (10 primary, 8-9) — EF Core `DbContext` design, configurations, migrations, query patterns, transactions, optimistic concurrency, tuning. Triggers: "set up EF Core for X", "AsNoTracking vs tracking", "EF migrations workflow", "row version concurrency", "this LINQ query is slow". Do NOT use for raw-SQL data access (`data/<db>`), cross-engine migrations (`data/_shared/migrations`), or Java / Node persistence.
---

# .NET — Persistence with EF Core

The library's default persistence layer for .NET — **.NET 10 / EF Core 10 primary, .NET 8-9 / EF Core 8-9 supported**. Code-first models against PostgreSQL / SQL Server providers, explicit configurations via `IEntityTypeConfiguration<T>`, migrations under source control, opt-in tracking, row-version optimistic concurrency, and AOT-friendly compiled queries for hot paths. The recipes below are current EF Core 8/9/10 API; version-specific divergence is called out where it exists (primarily around `ExecuteUpdate`/`ExecuteDelete`, available since EF Core 7, and `Timestamp`/`ComplexProperty` behavior).

## When to use

- New .NET service needs persistence
- Adding a new aggregate / entity to an existing `DbContext`
- Tuning a slow query (LINQ pattern, missing index, N+1)
- Wiring optimistic concurrency
- Setting up the migrations workflow

## When NOT to use

- Schema / DDL / engine-specific tuning → `data/postgresql` / `data/sqlserver`
- Cross-engine migration patterns → `data/_shared/migrations`
- Cross-engine query optimization → `data/_shared/query-optimization`
- Raw ADO.NET / Dapper when EF is overkill — for read-heavy reporting paths, Dapper is fine; this skill is about EF

## Version policy

**First act: detect the project's `<TargetFramework>`** and match the corresponding EF Core major (EF Core 8 ↔ net8.0, EF Core 9 ↔ net9.0, EF Core 10 ↔ net10.0 — EF Core does not skip-version support an unrelated TFM). Never up-level a net8/net9 project's EF Core package reference to 10 as part of an unrelated change; never flag a net8/net9 project for lacking a net10-only EF Core feature.

## Stack

- **EF Core 10 primary; EF Core 8 / 9 supported** — match the package major to the project's TFM
- Provider: `Npgsql.EntityFrameworkCore.PostgreSQL` (default per `data/postgresql`) or `Microsoft.EntityFrameworkCore.SqlServer` (per `data/sqlserver`)
- `Microsoft.EntityFrameworkCore.Design` for `dotnet ef` tooling
- Migrations via `dotnet ef migrations` (preferred) or DbUp for raw SQL projects

## DbContext design

```csharp
public sealed class OrdersDbContext(DbContextOptions<OrdersDbContext> options) : DbContext(options)
{
    public DbSet<Order>     Orders    => Set<Order>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
    public DbSet<Customer>  Customers => Set<Customer>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        builder.ApplyConfigurationsFromAssembly(typeof(OrdersDbContext).Assembly);
    }

    protected override void ConfigureConventions(ModelConfigurationBuilder configurationBuilder)
    {
        // Default text columns to a reasonable max length unless overridden
        configurationBuilder.Properties<string>().HaveMaxLength(255);
        // Money in minor units (long) — never decimal as a default
    }
}
```

Rules:

- One `DbContext` per **bounded context**; not one per service unless the service is one BC
- **Sealed**; primary constructor (`(DbContextOptions<>...) : DbContext(options)`) for clean DI
- `DbSet<T>` properties use the modern `=> Set<T>()` expression-body
- `OnModelCreating` only applies configurations; no inline `builder.Entity<T>()` calls — that's `IEntityTypeConfiguration<T>`'s job

## Entity types

```csharp
public sealed class Order
{
    public required Guid Id { get; init; }
    public required Guid CustomerId { get; init; }
    public required string Status { get; set; }      // mutable — state transitions
    public required long TotalMinor { get; init; }
    public required string Currency { get; init; }
    public required DateTimeOffset PlacedAt { get; init; }
    public DateTimeOffset? PaidAt { get; set; }

    // Concurrency token (xmin in Postgres, rowversion in SQL Server)
    [Timestamp]
    public byte[] RowVersion { get; private set; } = [];

    // Owned collection / navigation
    private readonly List<OrderLine> _lines = new();
    public IReadOnlyList<OrderLine> Lines => _lines;

    private Order() { }  // EF Core needs a parameterless ctor; private + read via init-only

    public static Order Place(Guid customerId, IEnumerable<NewOrderLine> lines, DateTimeOffset now)
    {
        var order = new Order
        {
            Id = Guid.NewGuid(),
            CustomerId = customerId,
            Status = "Pending",
            PlacedAt = now,
            Currency = "EUR",
            TotalMinor = lines.Sum(l => l.PriceMinor * l.Quantity),
        };
        order._lines.AddRange(lines.Select(l => new OrderLine { /* ... */ }));
        return order;
    }
}
```

- `required` for fields that must be set; `init` for immutability after construction
- **Private parameterless constructor** for EF + factory methods for legitimate construction
- **Private collection backing field** + public `IReadOnlyList<>` — never expose `List<T>`
- **`[Timestamp]` for optimistic concurrency** — works on both Postgres (`xmin` mapped) and SQL Server (`rowversion`)

## Configurations

One file per entity:

```csharp
public sealed class OrderConfiguration : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> builder)
    {
        builder.ToTable("orders");

        builder.HasKey(o => o.Id);
        builder.Property(o => o.Id).HasColumnName("id");

        builder.Property(o => o.CustomerId).HasColumnName("customer_id").IsRequired();

        builder.Property(o => o.Status).HasColumnName("status").HasMaxLength(20).IsRequired();
        builder.HasCheckConstraint("ck_orders_status", "status IN ('Pending','Paid','Cancelled','Refunded')");

        builder.Property(o => o.TotalMinor).HasColumnName("total_minor").IsRequired();
        builder.Property(o => o.Currency).HasColumnName("currency").HasMaxLength(3).IsRequired();
        builder.Property(o => o.PlacedAt).HasColumnName("placed_at").IsRequired();
        builder.Property(o => o.PaidAt).HasColumnName("paid_at");

        builder.Property(o => o.RowVersion)
            .HasColumnName("xmin")
            .HasColumnType("xid")        // Postgres
            .ValueGeneratedOnAddOrUpdate()
            .IsConcurrencyToken();

        // Owned collection
        builder.HasMany(o => o.Lines)
            .WithOne()
            .HasForeignKey("order_id")
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasIndex(o => o.CustomerId).HasDatabaseName("idx_orders_customer_id");
        builder.HasIndex(o => o.PlacedAt).IsDescending().HasDatabaseName("idx_orders_placed_at");
    }
}
```

- **Snake_case columns** to match the schema design rule in `data/_shared/schema-design`
- **Indexes named explicitly** (matches `data/postgresql` / `data/sqlserver` conventions)
- **Check constraints** for value sets — defense in depth alongside `enum` on the C# side

## Query patterns

### `AsNoTracking` is the default for reads

```csharp
public async Task<Order?> GetAsync(Guid id, CancellationToken ct)
{
    return await _db.Orders.AsNoTracking().FirstOrDefaultAsync(o => o.Id == id, ct);
}

public async Task<IReadOnlyList<Order>> ListByCustomerAsync(Guid customerId, int take, CancellationToken ct)
{
    return await _db.Orders.AsNoTracking()
        .Where(o => o.CustomerId == customerId)
        .OrderByDescending(o => o.PlacedAt)
        .Take(take)
        .ToListAsync(ct);
}
```

Tracking is for **state changes you intend to save**. For pure reads, `AsNoTracking` cuts memory + CPU substantially.

### Projections — never `SELECT *`

```csharp
public async Task<IReadOnlyList<OrderListDto>> ListSummaryAsync(Guid customerId, CancellationToken ct)
{
    return await _db.Orders.AsNoTracking()
        .Where(o => o.CustomerId == customerId)
        .OrderByDescending(o => o.PlacedAt)
        .Select(o => new OrderListDto(o.Id, o.Status, o.TotalMinor, o.Currency, o.PlacedAt))
        .ToListAsync(ct);
}
```

Project to a DTO; the SQL fetches only those columns. Matches the `SELECT *` ban from `data/_shared/query-optimization`.

### Keyset pagination (large tables)

```csharp
public async Task<IReadOnlyList<Order>> NextPageAsync(
    DateTimeOffset cursorPlacedAt, Guid cursorId, int take, CancellationToken ct)
{
    return await _db.Orders.AsNoTracking()
        .Where(o => o.PlacedAt < cursorPlacedAt
                 || (o.PlacedAt == cursorPlacedAt && o.Id.CompareTo(cursorId) < 0))
        .OrderByDescending(o => o.PlacedAt).ThenByDescending(o => o.Id)
        .Take(take)
        .ToListAsync(ct);
}
```

### Avoiding N+1

```csharp
// ❌ N+1 — N queries for N orders' lines
var orders = await _db.Orders.AsNoTracking().Take(50).ToListAsync(ct);
foreach (var o in orders) { var lines = o.Lines; /* triggers lazy load */ }

// ✅ Eager load
var orders = await _db.Orders.AsNoTracking()
    .Include(o => o.Lines)
    .Take(50)
    .ToListAsync(ct);

// ✅ Split query — for many-to-many fan-outs (cartesian explosion otherwise)
var orders = await _db.Orders.AsNoTracking()
    .Include(o => o.Lines)
    .AsSplitQuery()
    .Take(50)
    .ToListAsync(ct);
```

Add **OTel tracing** for DB calls (`AddSqlClientInstrumentation` / `AddEntityFrameworkCoreInstrumentation` per `observability/opentelemetry-dotnet`); N+1 shows up as a fan of identical short spans on a parent span.

### Compiled queries (hot paths)

```csharp
public static class CompiledQueries
{
    public static readonly Func<OrdersDbContext, Guid, Task<Order?>> GetById =
        EF.CompileAsyncQuery((OrdersDbContext db, Guid id) =>
            db.Orders.AsNoTracking().FirstOrDefault(o => o.Id == id));
}

// usage
var order = await CompiledQueries.GetById(_db, id);
```

For queries called thousands of times per minute, compilation cost vanishes. Profile first; not every query benefits.

## Writes & concurrency

```csharp
public async Task<Result<Guid, string>> CancelAsync(Guid id, CancellationToken ct)
{
    var order = await _db.Orders.FirstOrDefaultAsync(o => o.Id == id, ct);
    if (order is null) return Result.Err("not-found");
    if (order.Status != "Pending") return Result.Err("invalid-state");

    order.Status = "Cancelled";
    try
    {
        await _db.SaveChangesAsync(ct);
        return Result.Ok(order.Id);
    }
    catch (DbUpdateConcurrencyException)
    {
        // The row was modified by someone else between read and write
        return Result.Err("concurrency-conflict");
    }
}
```

The `[Timestamp]` byte[] property + `IsConcurrencyToken()` make every save check the row version. On conflict, EF throws `DbUpdateConcurrencyException`.

For Postgres, use `xmin` mapping instead of `rowversion`:

```csharp
builder.Property<uint>("xmin")
    .HasColumnType("xid")
    .ValueGeneratedOnAddOrUpdate()
    .IsConcurrencyToken();
```

## Transactions

For multi-aggregate writes that must commit together:

```csharp
using var tx = await _db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, ct);
try
{
    await _db.SaveChangesAsync(ct);                  // changes to aggregate A
    await _someOtherWork(...);
    await _db.SaveChangesAsync(ct);                  // changes to aggregate B
    await tx.CommitAsync(ct);
}
catch
{
    await tx.RollbackAsync(ct);
    throw;
}
```

Most write paths in well-designed aggregates need only the default `SaveChangesAsync` boundary. Reach for explicit transactions only when there's a real reason.

## Bulk operations (EF Core 7+)

```csharp
// Single SQL UPDATE — no tracking, no SaveChanges
await _db.Orders
    .Where(o => o.PlacedAt < cutoff && o.Status == "Pending")
    .ExecuteUpdateAsync(s => s.SetProperty(o => o.Status, "Cancelled"), ct);

// Single SQL DELETE
await _db.OrderLines
    .Where(l => l.OrderId == orderId)
    .ExecuteDeleteAsync(ct);
```

For batched maintenance / cleanup, `ExecuteUpdate` / `ExecuteDelete` outperform load-modify-save by orders of magnitude.

## Migrations

```bash
dotnet ef migrations add Add_Orders_PaidAt --project src/Orders.Infrastructure --startup-project src/Orders.Api
dotnet ef database update --project src/Orders.Infrastructure --startup-project src/Orders.Api
```

Rules:

- Migrations live under source control; reviewed in PRs
- One logical change per migration
- Application doesn't run `Database.Migrate()` at startup — pipelines run migrations as a pre-deploy step
- For online-safe DDL (NOT NULL adds, index creates), wrap the `Up` method with `migrationBuilder.Sql(..., suppressTransaction: true)` for Postgres `CREATE INDEX CONCURRENTLY` or SQL Server `ONLINE = ON`
- Forward-only in production; corrective migrations beat `Down`

See `data/_shared/migrations` for the cross-engine recipes; this skill covers the EF-side mechanics.

## DI registration

```csharp
builder.Services.AddDbContext<OrdersDbContext>(opt =>
{
    opt.UseNpgsql(builder.Configuration.GetConnectionString("Postgres"),
        npg => npg.EnableRetryOnFailure(maxRetryCount: 3));
    if (builder.Environment.IsDevelopment())
    {
        opt.EnableSensitiveDataLogging();
        opt.LogTo(Console.WriteLine, LogLevel.Information);
    }
});
```

`AddDbContextPool` is available for high-throughput scenarios; profile to confirm the gain before adopting (the pool's lifetime quirks can bite).

## Common anti-patterns

- **Lazy loading** enabled — sneaks N+1 in everywhere
- **`Update`** on a tracked entity ("save my changes") then a separate `Update` for the same entity in the same UoW
- **`Find`/`First` then mutate** without checking if it was found
- **`AsNoTracking` skipped on read paths** — measurable perf cost
- **`Include` + projection** — defeats projection (load the included nav, then project)
- **`ToList` before filter** — pulls everything into memory then filters in app
- **`DbContext` reused across threads** — `DbContext` is not thread-safe
- **Long-running `DbContext`** scope — keep them request-scoped
- **`SaveChanges()` in a tight loop** — batch or use `ExecuteUpdate`

## Rules

- One `DbContext` per bounded context
- Sealed entities + factory methods + private collection backing fields
- `[Timestamp]` / `xmin` concurrency tokens on every shared-write aggregate
- `IEntityTypeConfiguration<T>` per entity; never inline configuration
- `AsNoTracking()` for every read query
- Projections (`Select(o => new XDto(...))`) instead of full entity hydration
- Migrations under source control; run from pipeline, not app startup
- DB calls instrumented via OTel; logs structured (matches `observability/structured-logging-dotnet`)
- Connection strings from env / Key Vault (see `devops/environment-config`)

## What NOT to do

- No lazy loading enabled
- No `DbContext` as singleton / per-app-lifetime (scoped only)
- No `SaveChangesAsync` in loops
- No `Database.Migrate()` in `Program.cs`
- No `Find()` on a tracked context as a substitute for `FirstOrDefaultAsync` (silently inconsistent)
- No raw SQL strings concatenated with user input (use `FromSqlInterpolated` parameter binding)
- No mixing two providers in one `DbContext`
- No mixing migration tools (EF migrations + DbUp + Flyway) in one project

## Generation steps

1. Detect the target framework and matching EF Core major; confirm DB engine (Postgres / SQL Server), workload shape.
2. Generate the `DbContext` with primary constructor + sealed.
3. Generate entities with `required` / `init` + factory methods + private collections.
4. Generate `IEntityTypeConfiguration<T>` per entity with explicit column names, constraints, indexes.
5. Wire DI registration with `UseNpgsql` / `UseSqlServer`.
6. Add the first migration; review the SQL it generates.
7. Add read repositories / query helpers; default `AsNoTracking()`.
8. Add concurrency tokens on aggregates with shared writes.

## Handoffs

- DB engine specifics → `data/postgresql` / `data/sqlserver`
- Migration mechanics across engines → `data/_shared/migrations`
- Query optimization principles → `data/_shared/query-optimization`
- Caching in front of the DB → `data/_shared/caching-patterns` + `data/redis`
- API contracts that read from this layer → `qa/dotnet/skills/api-dto-writer`
- Java equivalent → `backend/java/skills/persistence`
- Node equivalent → `backend/node/skills/persistence`
