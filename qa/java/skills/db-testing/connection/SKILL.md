---
name: db-connection
description: Use when the user asks to connect from Java 21 tests to a real database (Postgres / MySQL / SQL Server / Mongo) to seed fixtures, run read-only assertion queries, and clean up safely. Triggers: "connect from our TestNG tests to Postgres", "JdbcTemplate probe for the orders table", "seed and clean a SQL fixture without leaks". Do NOT use for container lifecycle (`qa-java:db-testcontainers`) or query guardrails (`qa-java:db-verification-queries`).
---

# QA — DB Testing Client (Java 21 + Spring Boot 3)

Wires Java 21 TestNG tests to talk to a **real** database — seed fixtures via builders, run read-only assertion queries via Spring `JdbcTemplate` / jOOQ, wait for eventual consistency, and clean state safely. Pairs with `qa/java/skills/db-testing/testcontainers` for the container lifecycle and `qa/java/skills/db-testing/verification-queries` for SQL safety.

## When to use

- A test must verify a row was written, an FK held, a trigger fired, or a soft-delete column was set.
- Test setup needs to seed reference data (currencies, countries, plan tiers) that production reads.
- Async write flows need a "wait until the projection catches up" helper.
- Test suite leaks data between tests and needs a deterministic cleanup strategy.

## When NOT to use

- Production data-access code → the `backend/java` dev stack's generator, if installed (Spring Data JPA, jOOQ patterns).
- Container booting itself → `qa/java/skills/db-testing/testcontainers`.
- SQL guardrails (parameterization, no `SELECT *` in assertions) → `qa/java/skills/db-testing/verification-queries`.
- Pure unit tests with no SQL surface — keep them mock-driven.
- .NET / TypeScript stacks → `qa/{dotnet,typescript}/skills/db-testing/connection`.

## Stack

- **Runtime**: Java 21
- **Framework**: Spring Boot 3.x
- **Build**: Gradle (Kotlin DSL)
- **Test runner**: **TestNG** (library default; JUnit 5 only when forced by Pact-JVM or Spring slice tests)
- **DB clients**:
  - **`JdbcTemplate` / `NamedParameterJdbcTemplate`** — preferred for assertion queries; minimal surface, parameterized by default.
  - **jOOQ** — type-safe query DSL when probe queries grow joins / windowing.
  - **Spring Data JPA repositories (read-only)** — only when the production repository already exists; mark `@Transactional(readOnly = true)`.
  - **`MongoTemplate`** — Mongo assertions.
- **Migration**: **Flyway** — applied once on Spring context startup (auto via `spring-boot-starter-data-jdbc`).
- **Cleanup**: transactional rollback per test (`@Rollback` via `AbstractTestNGSpringContextTests`) when feasible; per-table `TRUNCATE … CASCADE` otherwise.

```
src/test/java/com/example/orders/
├── fixtures/
│   ├── PostgresFixture.java              ← see qa/java/skills/db-testing/testcontainers
│   └── OrdersIntegrationTest.java
├── dbclients/
│   ├── DbProbeConfig.java                ← JdbcTemplate / DSLContext beans
│   └── OrdersDbProbe.java                 ← read-only assertion queries
├── builders/                              ← test data builders (qa/java/skills/test-data-builder)
└── seeders/
    └── OrdersSeeder.java                  ← writes seeded rows via builders
```

## Connection management

Spring Boot manages the `DataSource`. Tests **never** new their own `HikariDataSource`. Inject `NamedParameterJdbcTemplate` / `DSLContext` / `MongoTemplate` directly into seeders / probes.

```java
@TestConfiguration
public class DbProbeConfig {
    @Bean
    public NamedParameterJdbcTemplate jdbc(DataSource ds) {
        return new NamedParameterJdbcTemplate(ds);
    }
}
```

The container DataSource itself is wired by `PostgresFixture` (see `qa/java/skills/db-testing/testcontainers`), using `@DynamicPropertySource` to inject `spring.datasource.url` from the Testcontainer.

## Seeding fixtures via builders

Test data shape comes from `qa/java/skills/test-data-builder` (Lombok `@Builder` records); the seeder takes the built record and persists it. Shape and persistence stay separate.

```java
public class OrdersSeeder {
    private final NamedParameterJdbcTemplate jdbc;

    public OrdersSeeder(NamedParameterJdbcTemplate jdbc) { this.jdbc = jdbc; }

    public String insert(TestOrder order) {
        jdbc.update(
            """
            INSERT INTO orders (id, customer_id, status, total_minor, currency, placed_at)
            VALUES (:id, :customerId, :status, :totalMinor, :currency, :placedAt)
            """,
            Map.of(
                "id",         order.id(),
                "customerId", order.customerId(),
                "status",     order.status(),
                "totalMinor", order.totalMinor(),
                "currency",   order.currency(),
                "placedAt",   Timestamp.from(order.placedAt())
            ));
        return order.id();
    }
}
```

```java
@Test
public void cancellingPaidOrderWritesRefundRow() {
    TestOrder order = Orders.paid().totalMinor(15_000L).build();
    ordersSeeder.insert(order);

    sut.cancel(order.id());

    OrdersDbProbe.RefundRow refund = ordersProbe.getRefundFor(order.id());
    assertThat(refund).isNotNull();
    assertThat(refund.amountMinor()).isEqualTo(15_000L);
}
```

## Read-only assertion queries — DB probes

A **probe** is a small read-only class. One method per assertion. Each method names the columns it reads.

```java
public class OrdersDbProbe {
    private final NamedParameterJdbcTemplate jdbc;

    public OrdersDbProbe(NamedParameterJdbcTemplate jdbc) { this.jdbc = jdbc; }

    public RefundRow getRefundFor(String orderId) {
        return jdbc.query(
            """
            SELECT id, order_id, amount_minor, currency, refunded_at
            FROM   refunds
            WHERE  order_id = :orderId
            """,
            Map.of("orderId", orderId),
            rs -> rs.next()
                ? new RefundRow(
                    rs.getString("id"),
                    rs.getString("order_id"),
                    rs.getLong("amount_minor"),
                    rs.getString("currency"),
                    rs.getTimestamp("refunded_at").toInstant())
                : null);
    }

    public record RefundRow(
        String id,
        String orderId,
        long amountMinor,
        String currency,
        Instant refundedAt) {}
}
```

Probe rules:
- **Read-only** — probes never write. Writes go through the SUT or a seeder.
- **Project explicit columns** — no `SELECT *`. The probe's record type documents what the test cares about.
- **Parameterized** — every value is a named parameter; no string concatenation.
- **One method per assertion** — `getRefundFor`, `countActiveOrdersForCustomer`, `hasAuditEventOfType`.

## Waiting for eventual consistency

Async write flows (Debezium CDC, outbox → projection, Kafka consumer) don't surface the new row instantly. Use Awaitility or a small custom poll, **not** `Thread.sleep`.

```java
public class DbWaits {
    public static <T> T waitFor(
        Supplier<T> probe,
        Predicate<T> predicate,
        Duration timeout,
        Duration interval)
    {
        return Awaitility.await()
            .atMost(timeout)
            .pollInterval(interval)
            .pollDelay(Duration.ZERO)
            .until(probe::get, value -> value != null && predicate.test(value));
    }
}

// Usage
RefundRow refund = DbWaits.waitFor(
    () -> ordersProbe.getRefundFor(orderId),
    r  -> r.amountMinor() == 15_000L,
    Duration.ofSeconds(5),
    Duration.ofMillis(100));
```

`Duration.ofSeconds(5)` is a sane default for projection lag locally; bump in CI if needed but **never** `Thread.sleep(5000)`.

## Cleanup strategies

| Strategy | When | Notes |
|---|---|---|
| **Transactional rollback** | Default — most Spring slice / context tests | Extend `AbstractTestNGSpringContextTests`; annotate fixture class `@Rollback(true)`. Fast; doesn't work across HTTP boundaries. |
| **Per-test TRUNCATE … CASCADE** | When the SUT call crosses an HTTP boundary (RestAssured calls the running app, the test's own transaction can't roll back the server's writes) | `@AfterMethod` runs `TRUNCATE schema.table_a, schema.table_b CASCADE`. |
| **Schema-per-test** | Cross-test mutation is unavoidable (schema migrations, multi-tenant) | Slowest; reserve for the few tests that need it. |
| **Mongo: drop collections** | `@AfterMethod` drops every collection except indexes-bearing system ones. |

### Transactional rollback (preferred)

```java
@ContextConfiguration(initializers = PostgresFixture.Initializer.class)
@Rollback(true)
@TransactionConfiguration(defaultRollback = true)
public class OrdersIntegrationTest extends AbstractTransactionalTestNGSpringContextTests {
    // ...
}
```

### Truncate (when transactional rollback isn't an option)

```java
@AfterMethod(alwaysRun = true)
public void truncate() {
    jdbc.getJdbcTemplate().execute(
        "TRUNCATE orders, refunds, audit_events RESTART IDENTITY CASCADE");
}
```

List tables explicitly. Don't loop over `information_schema.tables` — that touches Flyway metadata too.

## Secrets

- Connection details come from `@DynamicPropertySource` against the Testcontainer (test-time) or `application-test.yml` (rare); **never** committed credentials.
- Never log the JDBC URL with credentials.
- `application-test.yml` does **not** contain raw passwords — use placeholder env vars (`${DB_PASSWORD}`).

## Rules

- Spring-managed `DataSource`; tests never new their own.
- Seeders write; probes read; SUT does the business action. Each class has one job.
- Probes are read-only and explicitly project columns (no `SELECT *`).
- Every parameter is a **named parameter** (`NamedParameterJdbcTemplate`) — no string concatenation.
- `Thread.sleep` is forbidden as an assertion wait — Awaitility (or the polling helper) with a predicate.
- Transactional rollback by default; truncate when the SUT crosses an HTTP boundary.
- Constructor injection only — seeders / probes never use field injection (`@Autowired` on fields).
- Records for probe row types.
- Java records for test data shapes (from `qa/java/skills/test-data-builder`).
- Gradle Kotlin DSL preferred for new projects; Maven only when forced.
- `@TestConfiguration` on probe / seeder bean wiring so it doesn't leak into production context.

## What NOT to do

- No `Thread.sleep(5000)` as the assertion wait — Awaitility with a predicate.
- No `SELECT * FROM orders WHERE id = '…'` with the value inlined — bind a parameter, project the columns you need.
- No raw `INSERT` SQL duplicated across tests — go through a seeder backed by `qa/java/skills/test-data-builder`.
- No `JdbcTemplate.execute("...")` with a request body literal — use `NamedParameterJdbcTemplate.update(..., Map.of(...))`.
- No `entityManager.createNativeQuery(...)` in tests when `JdbcTemplate` would do — pick one.
- No `EntityManagerFactory#createEntityManager` opened by the test — Spring manages it.
- No `@Sql("classpath:seed/orders.sql")` for shaping per-test data — that hides what the test does. Use seeders + builders.
- No `Flyway.clean()` between tests — it drops the schema. Truncate row data instead.
- No `@Transactional` on test methods that hit the running app via HTTP — the server's transaction is separate; rollback won't undo the server's writes.
- No reading credentials from `System.getenv` inside a test class — go through Spring properties.
- No probe method that returns the full ORM entity for a small assertion — return a projected record.
- No catching `DataAccessException` to assert failure modes — failures should surface and fail the test.

## Generation steps

1. Confirm engine (Postgres default), schema-source (Flyway default), and which assertion queries each new test needs.
2. Add `DbProbeConfig` `@TestConfiguration` with `NamedParameterJdbcTemplate` (and `DSLContext` if using jOOQ) — wire in `PostgresFixture`.
3. For each new test set, scaffold a `<Aggregate>Seeder.java` (write) and `<Aggregate>DbProbe.java` (read), reusing builders from `qa/java/skills/test-data-builder`.
4. Add `DbWaits` (Awaitility wrapper) if the SUT involves async projections.
5. Pick a cleanup strategy (transactional rollback default); annotate / wire `@AfterMethod`.
6. Run `./gradlew test` — every test passes; no leaks between tests. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Handoffs

- Container lifecycle → `qa/java/skills/db-testing/testcontainers`
- SQL guardrails on assertion queries → `qa/java/skills/db-testing/verification-queries`
- Test data builders feeding seeders → `qa/java/skills/test-data-builder`
- .NET DB testing client → `qa/dotnet/skills/db-testing/connection`
- TypeScript DB testing client → `qa/typescript/skills/db-testing/connection`
- API tests that own the SUT call → `qa/java/skills/api-test-author/writer`
- Test strategy where DB tests fit → `qa/manual/test-strategy`
- Production data access patterns → the `backend/java` dev stack's generator, if installed
