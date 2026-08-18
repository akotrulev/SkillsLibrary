---
name: qa-db-verification-queries-java
description: Use when writing or reviewing a safe verification query for tests in Java 21 / Spring Boot 3 — assert a row exists, add a `COUNT(*)` check, review test SQL for guardrails, or poll for an eventually-consistent row. Triggers "write a verification query for this test", "assert this row exists", "review my test SQL", "wait for an eventually-consistent row". Do NOT use for connection/seeding/cleanup (use `qa-db-connection-java`), or container lifecycle (use `qa-db-testing-testcontainers-java`).
---

# QA — DB Testing Query Author (Java 21 + Spring Boot 3)

Guardrails for the **SQL string itself** when a Java 21 TestNG integration test reaches into the database to verify behaviour. Connection wiring, seeder, and probe scaffolding live in `qa/java/skills/db-testing/connection`; this skill owns *what the SQL is allowed to look like* — named parameter binding only, explicit column lists, safe `LIKE`, type-correct parsing, exists / not-exists / count helpers, an Awaitility-based poller that re-runs the safe query, and a hard refusal list for destructive verbs outside cleanup.

## When to use

- A test is about to embed a SQL string (`NamedParameterJdbcTemplate.query(...)`, `DSLContext.fetch(...)`, raw `JdbcTemplate.queryForObject`) and you need it reviewed or generated.
- An existing probe / seeder uses string concatenation, `SELECT *`, or unbounded `DELETE` and needs a rewrite.
- A test needs an "assert exactly one row matches these columns" or "assert no row matches" helper.
- An async flow needs an Awaitility wait that re-runs the verification query until the projection catches up.

## When NOT to use

- Spring `DataSource` wiring / fixture lifecycle / `@Rollback` cleanup → `qa/java/skills/db-testing/connection`.
- Container boot, Flyway migrations on startup → `qa/java/skills/db-testing/testcontainers`.
- Production data-access SQL (Spring Data JPA, jOOQ in production) → the `backend/java` dev stack's generator, if installed.
- .NET SQL guardrails → `qa/dotnet/skills/db-testing/verification-queries`.
- TypeScript SQL guardrails → `qa/typescript/skills/db-testing/verification-queries`.
- Pure unit tests with no SQL surface — keep them mock-driven.

## Inputs needed (≤2 questions)

1. **Engine + client**: Postgres + `NamedParameterJdbcTemplate` (default), Postgres + jOOQ (when joins/windowing earn it), MySQL, or SQL Server?
2. **Assertion shape**: exists / not-exists / single-row projection / count / poll-until-row-appears?

## Decision matrix

| Need | Use | Notes |
|---|---|---|
| "Row exists with these columns" | `jdbc.query(..., rs -> rs.next() ? new Row(...) : null)` | Returns `null` if missing; assert `isNotNull`. |
| "Exactly one row matches" | `jdbc.queryForObject(..., RowMapper)` | Throws `EmptyResultDataAccessException` / `IncorrectResultSizeDataAccessException` — surfaces fixture leaks immediately. |
| "No row matches" | `jdbc.queryForObject("SELECT EXISTS (...)", ..., Boolean.class)` | Cheaper than `COUNT(*)`. |
| "How many rows match" | `jdbc.queryForObject("SELECT COUNT(*)", ..., Long.class)` | Always `Long` (Postgres `bigint`); never `Integer`. |
| Joins / windowing get ugly in SQL strings | jOOQ `DSLContext.select(...).from(...).where(...).fetch()` | Type-safe; keeps parameters parameterized by construction. |
| "Wait until row appears" | `Awaitility.await().until(probe::call, predicate)` | Re-runs the same parameterized query; never `Thread.sleep` as the assertion. |
| Free-text contains | `LIKE :pattern ESCAPE '\'` + manual escape of `% _ \` | Treat user input as data. |
| `IN (...)` of N values | `WHERE col = ANY (:ids)` (Postgres array) / `IN (:ids)` with `Map.of("ids", List.of(...))` | Never concatenate the list. |
| Soft-delete check | Explicit `WHERE deleted_at IS NULL` | Don't rely on a view abstraction in tests. |

## Stack

- **Runtime**: Java 21, Spring Boot 3.x, Gradle (Kotlin DSL)
- **Test runner**: TestNG (library default)
- **Clients**: `NamedParameterJdbcTemplate` (default), jOOQ DSL when joins / windowing earn it
- **Connection**: Spring-managed `DataSource` from `qa/java/skills/db-testing/connection` — probe / seeder receive `NamedParameterJdbcTemplate` / `DSLContext` via constructor injection only
- **Logging**: SLF4J with structured templates — log the probe *name*, not the SQL text with parameter values

## Parameterized read — the only allowed shape

```java
public record OrderRow(
    UUID    id,
    UUID    customerId,
    String  status,
    long    totalMinor,
    String  currency) {}

public class OrdersDbProbe {

    private static final Logger log = LoggerFactory.getLogger(OrdersDbProbe.class);

    private final NamedParameterJdbcTemplate jdbc;

    public OrdersDbProbe(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public OrderRow getOrder(UUID orderId) {
        log.debug("Probe {} running for {}", "getOrder", orderId);
        return jdbc.query(
            """
            SELECT id, customer_id, status, total_minor, currency
            FROM   orders
            WHERE  id = :orderId
            """,
            Map.of("orderId", orderId),
            rs -> rs.next()
                ? new OrderRow(
                    rs.getObject("id",          UUID.class),
                    rs.getObject("customer_id", UUID.class),
                    rs.getString("status"),
                    rs.getLong("total_minor"),
                    rs.getString("currency"))
                : null);
    }
}
```

Rules baked in:
- Explicit column list — every column is named.
- Single named parameter `:orderId`, bound through `Map.of(...)` — no concatenation, no `+ orderId +`.
- `UUID` stays a `UUID` end-to-end (`rs.getObject("id", UUID.class)`); never `.toString()` it into SQL.
- Probe returns a `record`, not the production entity.

## Exists / not-exists helpers

```java
public final class DbAssertions {

    private DbAssertions() {}

    public static boolean exists(
        NamedParameterJdbcTemplate jdbc,
        String                     table,
        String                     whereClause,        // literal, owned by test code
        Map<String, ?>             parameters) {

        var sql = "SELECT EXISTS (SELECT 1 FROM %s WHERE %s)".formatted(table, whereClause);
        return Boolean.TRUE.equals(jdbc.queryForObject(sql, parameters, Boolean.class));
    }
}

// Usage
boolean paid = DbAssertions.exists(
    jdbc,
    "orders",
    "id = :orderId AND status = :status",
    Map.of("orderId", orderId, "status", "PAID"));
assertThat(paid).as("expected a PAID row for the seeded order").isTrue();
```

`table` and `whereClause` are **literal strings owned by the test code**, never composed from runtime input. Values *always* travel as named parameters.

## `COUNT(*)` patterns

```java
public long countActiveOrdersForCustomer(UUID customerId) {
    return jdbc.queryForObject(
        """
        SELECT COUNT(*)
        FROM   orders
        WHERE  customer_id = :customerId
          AND  status      = ANY (:activeStatuses)
        """,
        Map.of(
            "customerId",     customerId,
            "activeStatuses", List.of("PLACED", "PAID", "SHIPPED").toArray(String[]::new)),
        Long.class);
}
```

- Return type is `long` / `Long.class` — Postgres `COUNT(*)` is `bigint`. Don't bind to `Integer.class`.
- Status list is bound as a `String[]` parameter (`ANY (:activeStatuses)`), never string-joined.

## Safe `LIKE` escaping

```java
public final class LikeEscape {

    private LikeEscape() {}

    public static String escape(String raw) {
        return raw
            .replace("\\", "\\\\")
            .replace("%",  "\\%")
            .replace("_",  "\\_");
    }
}

public long countOrdersWithReferenceContaining(String fragment) {
    var pattern = "%" + LikeEscape.escape(fragment) + "%";
    return jdbc.queryForObject(
        """
        SELECT COUNT(*)
        FROM   orders
        WHERE  reference LIKE :pattern ESCAPE '\\'
        """,
        Map.of("pattern", pattern),
        Long.class);
}
```

`%`, `_`, and `\` are escaped in Java before binding so a fragment of `100%` doesn't match every row.

## `Long` / `UUID` / timestamp parsing

- `UUID id` flows as `java.util.UUID` — Postgres `uuid` maps natively via `rs.getObject("id", UUID.class)`. No `UUID.fromString` on values coming back unless the column is `text` (smell — fix the schema).
- `long` for `bigint`, `int` for `integer`. Mismatched types throw at materialisation; that's the signal.
- `Instant` for `timestamptz` (via `rs.getObject("col", OffsetDateTime.class).toInstant()` or `rs.getTimestamp("col").toInstant()`). `LocalDateTime` is forbidden in probe records — timezone ambiguity.

## jOOQ tasteful subset

Use jOOQ only when SQL strings start to compose joins / window functions and the type safety earns the dependency. Keep it to a small surface:

```java
public Optional<RefundRow> getRefundFor(UUID orderId) {
    return dsl
        .select(REFUNDS.ID, REFUNDS.ORDER_ID, REFUNDS.AMOUNT_MINOR, REFUNDS.CURRENCY, REFUNDS.REFUNDED_AT)
        .from(REFUNDS)
        .where(REFUNDS.ORDER_ID.eq(orderId))
        .fetchOptional(r -> new RefundRow(
            r.get(REFUNDS.ID),
            r.get(REFUNDS.ORDER_ID),
            r.get(REFUNDS.AMOUNT_MINOR),
            r.get(REFUNDS.CURRENCY),
            r.get(REFUNDS.REFUNDED_AT).toInstant()));
}
```

Rules:
- Explicit `select(col, col, col)` — **no `select()` / `selectFrom()` without an explicit column list** in tests (those project everything).
- `.eq(value)` / `.in(values)` — values become bind parameters by construction.
- No `DSL.field("raw sql " + var)` shortcuts — that bypasses parameterisation.

## Awaitility wait-for-row poller

```java
public final class DbWaits {

    private static final Logger log = LoggerFactory.getLogger(DbWaits.class);

    private DbWaits() {}

    public static <T> T waitForRow(
        String                       waitName,
        java.util.concurrent.Callable<T> probe,
        java.util.function.Predicate<T>  predicate,
        Duration                         timeout,
        Duration                         interval) {

        return Awaitility.await(waitName)
            .atMost(timeout)
            .pollInterval(interval)
            .pollDelay(Duration.ZERO)
            .ignoreException(EmptyResultDataAccessException.class)
            .until(probe, value -> value != null && predicate.test(value));
    }
}

// Usage
RefundRow refund = DbWaits.waitForRow(
    "refund-for-" + orderId,
    () -> ordersProbe.getRefundFor(orderId),
    r  -> r.amountMinor() == 15_000L,
    Duration.ofSeconds(5),
    Duration.ofMillis(100));
```

Caller passes the **same** safe probe method — the poller never builds SQL itself. `Thread.sleep` is forbidden; Awaitility owns the backoff.

## Refusal patterns — destructive verbs

If a generated or reviewed query contains any of the following **outside** a designated cleanup helper, refuse and require an explicit cleanup path:

| Verb | Refused when | Allowed only in |
|---|---|---|
| `DROP TABLE` / `DROP SCHEMA` | Ever, in a test body | Never. Flyway owns schema. |
| `TRUNCATE` | Inside a `@Test` method | `@AfterMethod` cleanup helpers in `qa/java/skills/db-testing/connection`. |
| `DELETE` without `WHERE` | Anywhere | Never. `TRUNCATE` is the right primitive. |
| `UPDATE` without `WHERE` | Anywhere | Never. |
| `ALTER TABLE` | Test body | Flyway migration only. |
| `Flyway.clean()` | Anywhere in tests | Never — drops the schema. |

Reviewer produces the standard finding table (see `CLAUDE.md`) and marks these **blocker**.

## Anti-patterns

- **String concatenation of values**: `jdbc.queryForObject("SELECT id FROM orders WHERE id = '" + orderId + "'", ...)` — even with a `UUID`, breaks the moment the value is a string. Use `:orderId`.
- **`SELECT *`**: hides which columns the test depends on; every schema change touches every test.
- **`DELETE FROM orders` in a test body**: no `WHERE`, no cleanup helper. Use the cleanup strategy from `qa/java/skills/db-testing/connection`.
- **Hidden ORM lazy-loading in assertions**: pulling a JPA `Order` entity and reading `order.getCustomer().getName()` triggers a second query inside `@Transactional` test scope. Probe with explicit SQL.
- **`Thread.sleep(5000)` before the assertion**: use Awaitility.
- **`Integer.class` for `COUNT(*)`**: silently truncates on large fixtures.
- **Logging the SQL with bound values**: leaks PII / secrets into structured logs. Log the probe *name* and IDs you already trust.
- **`IN (...)` built by `String.join(",", ids)`**: classic injection vector even in tests. Use `ANY (:ids)` with `String[]` or `IN (:ids)` with `List`.
- **`whereClause` parameter built from runtime input** in `DbAssertions.exists`: only literal strings owned by the test code may flow into the SQL shape.
- **`LocalDateTime` in a probe record where the column is `timestamptz`**: timezone drift causes flakiness in CI.
- **`@Sql("seed/orders.sql")` for per-test data**: hides what the test does; use builders + seeders.

## Examples

### Example 1 — assert one row exists with these columns

```java
@Test
public void cancellationWritesRefundRowWithOriginalTotal() {
    TestOrder order = Orders.paid().totalMinor(15_000L).build();
    ordersSeeder.insert(order);

    sut.cancel(order.id());

    RefundRow refund = ordersProbe.getRefundFor(order.id()).orElse(null);
    assertThat(refund).isNotNull();
    assertThat(refund.amountMinor()).isEqualTo(15_000L);
    assertThat(refund.currency()).isEqualTo("EUR");
}
```

### Example 2 — assert no row matches

```java
@Test
public void failedPaymentDoesNotCreateOrder() {
    sut.attemptPayment(failingCardToken);

    boolean exists = DbAssertions.exists(
        jdbc,
        "orders",
        "customer_id = :customerId",
        Map.of("customerId", customerId));
    assertThat(exists).isFalse();
}
```

### Example 3 — Awaitility poll until projection catches up

```java
RefundRow refund = DbWaits.waitForRow(
    "refund-for-" + order.id(),
    () -> ordersProbe.getRefundFor(order.id()).orElse(null),
    r  -> r.amountMinor() == 15_000L,
    Duration.ofSeconds(5),
    Duration.ofMillis(100));
assertThat(refund.currency()).isEqualTo("EUR");
```

## Anti-examples

```java
// BLOCKER — string-concatenated value, no parameter
var refund = jdbc.getJdbcTemplate().queryForObject(
    "SELECT * FROM refunds WHERE order_id = '" + orderId + "'",
    refundMapper);

// BLOCKER — DELETE without WHERE in a test body
jdbc.getJdbcTemplate().execute("DELETE FROM orders");

// MAJOR — SELECT *, hides what the assertion depends on
jdbc.queryForMap("SELECT * FROM orders WHERE id = :id", Map.of("id", id));

// MAJOR — Integer for COUNT(*)
int count = jdbc.queryForObject("SELECT COUNT(*) FROM orders", Map.of(), Integer.class);

// MAJOR — Thread.sleep as the assertion wait
Thread.sleep(5000);
RefundRow refund = ordersProbe.getRefundFor(orderId).orElse(null);

// MAJOR — IN list built by String.join
String ids = orderIds.stream().map(i -> "'" + i + "'").collect(Collectors.joining(","));
jdbc.queryForList("SELECT id, status FROM orders WHERE id IN (" + ids + ")", Map.of());

// MAJOR — hidden lazy-load in the assertion
Order order = orderRepository.findById(orderId).orElseThrow();   // JPA
assertThat(order.getCustomer().getName()).isEqualTo("Alice");     // second query, surprise
```

## Rules

- Named-parameter binding only — every value flows through `Map.of(...)` or `MapSqlParameterSource`.
- Explicit column lists in every assertion query; `record` types for projections.
- `SELECT EXISTS (...)` for boolean checks; `COUNT(*)` returns `Long`.
- `LIKE` patterns built in Java with `LikeEscape.escape` before binding, with `ESCAPE '\\'`.
- `UUID` / `long` / `Instant` for `uuid` / `bigint` / `timestamptz` — no `.toString()` round-trips.
- No `Thread.sleep` as an assertion wait — use Awaitility with the same probe.
- No destructive verbs outside designated cleanup; refuse with the reviewer finding table.
- Constructor injection on probe classes — no field `@Autowired`. SLF4J with message templates (`{}`), never string interpolation.
- jOOQ only when joins / windowing earn it; always explicit `select(col, col, ...)`.

## Handoffs

- `DataSource` wiring / fixture / `@Rollback` cleanup → `qa/java/skills/db-testing/connection`
- Container lifecycle → `qa/java/skills/db-testing/testcontainers`
- Test data builders feeding seeders → `qa/java/skills/test-data-builder`
- .NET SQL guardrails → `qa/dotnet/skills/db-testing/verification-queries`
- TypeScript SQL guardrails → `qa/typescript/skills/db-testing/verification-queries`
- Production data access SQL → the `backend/java` dev stack's generator, if installed
- Test strategy where DB tests fit → `qa/manual/test-strategy`
