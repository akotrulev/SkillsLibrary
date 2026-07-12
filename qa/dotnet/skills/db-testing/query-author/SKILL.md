---
name: qa-db-testing-query-author-dotnet
description: Use when the user asks to write a safe verification query for tests in .NET 8, assert this row exists from a test, review my test SQL for guardrails, add a `COUNT(*)` check from an integration test, or wait for an eventually-consistent row.
---

# QA — DB Testing Query Author (.NET 8)

Guardrails for the **SQL string itself** when a .NET 8 integration test reaches into the database to verify behaviour. The connection, seeder, and probe scaffolding live in `qa/dotnet/skills/db-testing/client`; this skill owns *what the SQL is allowed to look like* — parameter-only binding, explicit column lists, safe `LIKE`, type-correct parsing, exists / not-exists / count helpers, a poller that re-runs the same safe query, and a hard refusal list for destructive verbs outside cleanup.

## When to use

- A test is about to embed a SQL string (Dapper `QuerySingleAsync<>` / `ExecuteAsync` / raw `DbCommand`) and you need it reviewed or generated.
- An existing probe / seeder uses string interpolation, `SELECT *`, or unbounded `DELETE` and needs a rewrite.
- A test needs an "assert exactly one row matches these columns" or "assert no row matches" helper.
- An async flow needs a wait-for-eventual-consistency poll that re-runs the verification query.

## When NOT to use

- Opening connections / fixture lifecycle / Respawn cleanup → `qa/dotnet/skills/db-testing/client`.
- Container boot, schema migrations on startup → `qa/dotnet/skills/db-testing/testcontainers`.
- Production data-access SQL → `code-patterns/dotnet/generator`.
- Java SQL guardrails → `qa/java/skills/db-testing/query-author`.
- TypeScript SQL guardrails → `qa/typescript/skills/db-testing/query-author`.
- Pure unit tests with no SQL surface — keep them mock-driven.

## Inputs needed (≤2 questions)

1. **Engine + client**: Postgres + Dapper/Npgsql (default), SQL Server + Dapper/`Microsoft.Data.SqlClient`, or SQLite?
2. **Assertion shape**: exists / not-exists / single-row projection / count / poll-until-row-appears?

## Decision matrix

| Need | Use | Notes |
|---|---|---|
| "Row exists with these columns" | `QuerySingleOrDefaultAsync<TRow>` + record projection | Returns `null` if missing; assert `Is.Not.Null`. |
| "Exactly one row matches" | `QuerySingleAsync<TRow>` | Throws if zero or > 1 — surfaces fixture leaks immediately. |
| "No row matches" | `ExecuteScalarAsync<bool>` over `EXISTS (...)` | Cheaper than `COUNT(*)`; short-circuits. |
| "How many rows match" | `ExecuteScalarAsync<long>` over `SELECT COUNT(*)` | Always `long` (Postgres `bigint`); never `int`. |
| "Wait until row appears" | `WaitForRowAsync` poller (below) | Re-runs the same parameterized query; never `Task.Delay` as the assertion. |
| Free-text contains | `LIKE @pattern ESCAPE '\'` + manual escape of `% _ \` | Treat user input as data; see helper below. |
| `IN (...)` of N values | `WHERE col = ANY(@ids)` (Postgres) / table-valued parameter (SQL Server) | Never interpolate the list. |
| Soft-delete check | Explicit `WHERE deleted_at IS NULL` | Don't rely on a view abstraction in tests. |

## Stack

- **Runtime**: .NET 8, NUnit 4.x
- **Clients**: Dapper (default), `Npgsql` / `Microsoft.Data.SqlClient` for raw `DbCommand` when Dapper is overkill
- **Connection**: shared `DbConnectionFactory` from `qa/dotnet/skills/db-testing/client` — never `new NpgsqlConnection(...)` in the query helper
- **Logging**: `Microsoft.Extensions.Logging` with structured templates — log the query *name*, not the query text with parameter values

## Parameterized read — the only allowed shape

```csharp
public sealed record OrderRow(Guid Id, Guid CustomerId, string Status, long TotalMinor, string Currency);

public sealed class OrdersDbProbe
{
    private readonly DbConnectionFactory _db;
    private readonly ILogger<OrdersDbProbe> _log;

    public OrdersDbProbe(DbConnectionFactory db, ILogger<OrdersDbProbe> log)
    {
        _db  = db;
        _log = log;
    }

    public async Task<OrderRow?> GetOrderAsync(Guid orderId, CancellationToken ct = default)
    {
        await using var conn = await _db.OpenAsync(ct);
        _log.LogDebug("Probe {Probe} running for {OrderId}", nameof(GetOrderAsync), orderId);

        return await conn.QuerySingleOrDefaultAsync<OrderRow>(
            new CommandDefinition(
                """
                SELECT id            AS Id,
                       customer_id   AS CustomerId,
                       status        AS Status,
                       total_minor   AS TotalMinor,
                       currency      AS Currency
                FROM   orders
                WHERE  id = @orderId
                """,
                new { orderId },
                cancellationToken: ct));
    }
}
```

Rules baked in:
- Explicit column list — every column is named and aliased to the record property.
- Single parameter `@orderId`, bound through Dapper's anonymous object — no interpolation, no `+ orderId.ToString() +`.
- `Guid` stays a `Guid` end-to-end; never `.ToString()` it into SQL.
- `CommandDefinition` carries the `CancellationToken` — async all the way.

## Exists / not-exists helpers

```csharp
public static class DbAssertions
{
    public static async Task<bool> ExistsAsync(
        IDbConnection conn,
        string        whereClause,    // e.g. "order_id = @orderId AND status = @status"
        object        parameters,
        string        table,
        CancellationToken ct = default)
    {
        // table & whereClause come from trusted call sites only; never user input.
        var sql = $"SELECT EXISTS (SELECT 1 FROM {table} WHERE {whereClause})";
        return await conn.ExecuteScalarAsync<bool>(new CommandDefinition(sql, parameters, cancellationToken: ct));
    }
}

// Usage
var paid = await DbAssertions.ExistsAsync(
    conn,
    whereClause: "order_id = @orderId AND status = @status",
    parameters: new { orderId, status = "PAID" },
    table:      "orders");
Assert.That(paid, Is.True, "expected a PAID row for the seeded order");
```

`table` and `whereClause` are **literal strings owned by the test code**, never composed from runtime input. Values *always* travel as parameters.

## `COUNT(*)` patterns

```csharp
public async Task<long> CountActiveOrdersForCustomerAsync(Guid customerId, CancellationToken ct = default)
{
    await using var conn = await _db.OpenAsync(ct);
    return await conn.ExecuteScalarAsync<long>(new CommandDefinition(
        """
        SELECT COUNT(*)
        FROM   orders
        WHERE  customer_id = @customerId
          AND  status      = ANY (@activeStatuses)
        """,
        new { customerId, activeStatuses = new[] { "PLACED", "PAID", "SHIPPED" } },
        cancellationToken: ct));
}
```

- Return type is `long` — Postgres `COUNT(*)` is `bigint`. Don't cast to `int`.
- Status list is bound as a parameter (`ANY (@activeStatuses)`), never string-joined.

## Safe `LIKE` escaping

```csharp
public static string EscapeLike(string raw) =>
    raw.Replace(@"\", @"\\").Replace("%", @"\%").Replace("_", @"\_");

public async Task<long> CountOrdersWithReferenceContainingAsync(string fragment, CancellationToken ct = default)
{
    var pattern = $"%{EscapeLike(fragment)}%";   // pattern is built in C#, then bound
    await using var conn = await _db.OpenAsync(ct);
    return await conn.ExecuteScalarAsync<long>(new CommandDefinition(
        """
        SELECT COUNT(*)
        FROM   orders
        WHERE  reference LIKE @pattern ESCAPE '\'
        """,
        new { pattern },
        cancellationToken: ct));
}
```

`%`, `_`, and `\` are escaped before binding so a fragment of `100%` doesn't accidentally match every row.

## Integer / `Guid` parsing

- `Guid orderId` flows as `Guid` — Npgsql maps to `uuid` natively. No `Guid.Parse` on values returned from the DB unless the column is `text` (smell — fix the schema).
- `long` for `bigint` columns. `int` for `integer`. Mismatched types throw at materialisation, which is what we want.
- `DateTimeOffset` for `timestamptz`. `DateTime` is forbidden in probe records — the timezone ambiguity bites later.

## Wait-for-eventual-consistency poller

```csharp
public static class DbWaits
{
    public static async Task<T> WaitForRowAsync<T>(
        Func<CancellationToken, Task<T?>> probe,
        Func<T, bool>                     predicate,
        TimeSpan                          timeout,
        TimeSpan                          interval,
        ILogger                           logger,
        [CallerMemberName] string         callerName = "",
        CancellationToken                 ct = default) where T : class
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(timeout);

        var attempts = 0;
        while (!cts.IsCancellationRequested)
        {
            attempts++;
            var value = await probe(cts.Token);
            if (value is not null && predicate(value))
            {
                logger.LogDebug("Wait {Caller} satisfied after {Attempts} attempts", callerName, attempts);
                return value;
            }
            await Task.Delay(interval, cts.Token);
        }
        throw new TimeoutException(
            $"Wait '{callerName}' did not satisfy predicate within {timeout.TotalSeconds:0.##}s ({attempts} attempts).");
    }
}
```

Caller passes the **same** safe probe method — the poller never builds SQL itself. `Thread.Sleep` is forbidden; we use `Task.Delay` only as the inter-poll backoff, never as the assertion wait.

## Refusal patterns — destructive verbs

If a generated or reviewed query contains any of the following **outside** a designated cleanup helper, refuse and require an explicit cleanup path:

| Verb | Refused when | Allowed only in |
|---|---|---|
| `DROP TABLE` / `DROP SCHEMA` | Ever, in a test body | Never. Migrations own schema. |
| `TRUNCATE` | Inside a `[Test]` method | `[TearDown]` / `[OneTimeTearDown]` cleanup helpers; or Respawn from `qa/dotnet/skills/db-testing/client`. |
| `DELETE` without `WHERE` | Anywhere | Never. `TRUNCATE` is the right primitive. |
| `UPDATE` without `WHERE` | Anywhere | Never. |
| `ALTER TABLE` | Test body | Migration only. |

The reviewer should produce the standard finding table (from `CLAUDE.md`) and mark these **blocker**.

## Anti-patterns

- **String concatenation / interpolation of values**:
  `conn.QueryAsync($"SELECT id FROM orders WHERE id = '{orderId}'")` — even with a `Guid`, this trains the wrong habit and breaks the moment the value is a string.
- **`SELECT *` in an assertion**: hides which columns the test actually depends on; every schema change touches every test.
- **`DELETE FROM orders;` in a test**: no `WHERE`, no cleanup helper. Use `TRUNCATE` in `[TearDown]` or Respawn.
- **Hidden ORM lazy-loading in assertions**: pulling an EF `Order` entity and reading `.Customer.Name` issues a second query the test author can't see. Probe with explicit SQL.
- **`Task.Delay(5000)` before the assertion**: not deterministic; use `WaitForRowAsync`.
- **`int` for `COUNT(*)`**: silently truncates on large fixtures.
- **Logging the SQL with parameter values**: leaks PII / secrets into structured logs. Log the probe *name* and IDs you already trust.
- **Building `IN (...)` by `string.Join(",", ids)`**: classic injection vector even in tests. Use `ANY (@ids)` (Postgres) or a TVP (SQL Server).
- **`whereClause` parameter built from runtime input**: only literal strings owned by the test code may flow into the SQL shape.
- **`DateTime` in a probe record where the column is `timestamptz`**: timezone drift will make the test flaky in CI.

## Examples

### Example 1 — assert one row exists with these columns

```csharp
[Test]
public async Task Cancellation_writes_refund_row_with_original_total()
{
    var order = Orders.Paid().WithTotal(15_000).Build();
    await _ordersSeeder.InsertAsync(order);

    await _sut.CancelAsync(order.Id);

    var refund = await _ordersProbe.GetRefundForAsync(order.Id);
    Assert.That(refund,             Is.Not.Null);
    Assert.That(refund!.AmountMinor, Is.EqualTo(15_000));
    Assert.That(refund.Currency,    Is.EqualTo("EUR"));
}
```

### Example 2 — assert no row matches

```csharp
[Test]
public async Task Failed_payment_does_not_create_order()
{
    await _sut.AttemptPaymentAsync(failingCardToken);

    var exists = await DbAssertions.ExistsAsync(
        await _db.OpenAsync(),
        whereClause: "customer_id = @customerId",
        parameters:  new { customerId = _customerId },
        table:       "orders");
    Assert.That(exists, Is.False);
}
```

### Example 3 — poll until projection catches up

```csharp
var refund = await DbWaits.WaitForRowAsync(
    ct => _ordersProbe.GetRefundForAsync(order.Id, ct),
    r   => r.AmountMinor == 15_000,
    timeout:  TimeSpan.FromSeconds(5),
    interval: TimeSpan.FromMilliseconds(100),
    logger:   _log);
Assert.That(refund.Currency, Is.EqualTo("EUR"));
```

## Anti-examples

```csharp
// BLOCKER — string-interpolated value, no parameter
var refund = await conn.QuerySingleAsync<RefundRow>(
    $"SELECT * FROM refunds WHERE order_id = '{orderId}'");

// BLOCKER — DELETE without WHERE in a test body
await conn.ExecuteAsync("DELETE FROM orders");

// MAJOR — SELECT *, hides what the assertion depends on
var row = await conn.QuerySingleAsync<dynamic>("SELECT * FROM orders WHERE id = @id", new { id });

// MAJOR — int for COUNT(*)
var count = await conn.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM orders");

// MAJOR — Task.Delay as the assertion wait
await Task.Delay(5000);
var refund = await _ordersProbe.GetRefundForAsync(orderId);

// MAJOR — IN list built by string.Join
var ids = string.Join(",", orderIds.Select(i => $"'{i}'"));
var rows = await conn.QueryAsync<OrderRow>($"SELECT id, status FROM orders WHERE id IN ({ids})");

// MAJOR — hidden lazy-load in the assertion
var order = await _db.Orders.FirstAsync(o => o.Id == orderId);   // EF
Assert.That(order.Customer.Name, Is.EqualTo("Alice"));            // second query, surprise
```

## Rules

- Parameterized binding only — every value flows through Dapper's anonymous object or `DynamicParameters`.
- Explicit column lists in every assertion query; records (`public sealed record`) for projection types.
- `EXISTS (...)` for boolean checks; `COUNT(*)` returns `long`.
- `LIKE` patterns built in C# with `EscapeLike` before binding, with `ESCAPE '\'`.
- `Guid` / `long` / `DateTimeOffset` for `uuid` / `bigint` / `timestamptz` — no `.ToString()` round-trips.
- No `Task.Delay` as an assertion wait — use `WaitForRowAsync` with the same probe.
- No destructive verbs outside designated cleanup; refuse with the reviewer finding table.
- Constructor injection on probe classes; `ILogger<T>` via DI; structured logs using message templates (`{OrderId}`, never `$"{orderId}"`).
- Async all the way — `await using`, `CancellationToken` threaded through every call.

## Handoffs

- Connection / fixture / Respawn cleanup → `qa/dotnet/skills/db-testing/client`
- Container lifecycle → `qa/dotnet/skills/db-testing/testcontainers`
- Test data builders feeding seeders → `qa/dotnet/skills/test-data-builder`
- Java SQL guardrails → `qa/java/skills/db-testing/query-author`
- TypeScript SQL guardrails → `qa/typescript/skills/db-testing/query-author`
- Production data access SQL → `code-patterns/dotnet/generator`
- Test strategy where DB tests fit → `qa/manual/test-strategy`
