---
name: be-java-persistence
description: Use when setting up or refactoring persistence in a Spring Boot 3 service — JPA/Hibernate, Spring Data, entity design, transactions, optimistic locking, query patterns, tuning. Triggers: "set up JPA for X", "Spring Data repository", "@Transactional boundaries", "@Version optimistic locking", "N+1 in Hibernate". Do NOT use for raw-SQL data access (`data/<db>`), cross-engine migrations (`data/_shared/migrations`), or .NET / Node persistence.
---

# Java — Persistence with JPA / Hibernate + Spring Data

The library's default persistence layer for Java 21 + Spring Boot 3.x. JPA via Hibernate, Spring Data JPA repositories, code-first entities, Flyway-driven schema, explicit `@Transactional` boundaries, `@Version` optimistic locking, opt-in tracking via projections, N+1 prevention as a default review check.

## Version policy

Confirm the project's Java release and Spring Boot / Hibernate major before generating or reviewing. Records-as-DTOs and pattern-matching switch assume Java 21; Hibernate 6.x ships with Spring Boot 3.x (Spring Boot 2.x pairs with Hibernate 5.x, which has different `@Type` / naming-strategy defaults) — don't apply Boot-3-only config keys to a Boot 2.x project.

## When to use

- New Spring Boot service needs persistence
- Adding an entity / aggregate to an existing schema
- Tuning a slow query / fixing an N+1
- Wiring optimistic locking on a contested resource
- Deciding between JPA, Spring Data JDBC, and raw JdbcTemplate

## When NOT to use

- Schema / DDL / engine-specific → `data/postgresql` / `data/sqlserver` / `data/mysql`
- Cross-engine migrations → `data/_shared/migrations`
- Cross-engine query optimization → `data/_shared/query-optimization`
- Reads where JPA's overhead isn't worth it — `JdbcTemplate` or Spring Data JDBC for reporting / projections
- .NET → `backend/dotnet/skills/persistence`
- Node → `backend/node/skills/persistence`

## Stack

- Java 21 + Spring Boot 3.x
- Spring Data JPA + Hibernate 6.x
- HikariCP connection pool (Spring Boot default)
- Flyway for migrations (preferred; per `data/_shared/migrations`)
- Lombok for entity boilerplate (sparingly — getters/setters/builder; avoid `@Data` on entities)
- `org.openjdk.jol` for tuning if needed

## Entity design

```java
package com.yourco.orders.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.*;

@Entity
@Table(name = "orders")
@NoArgsConstructor(access = AccessLevel.PROTECTED)   // JPA needs no-args ctor, hide it
@Getter
public class Order {

    @Id
    @Column(name = "id")
    private UUID id;

    @Column(name = "customer_id", nullable = false)
    private UUID customerId;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 20, nullable = false)
    private OrderStatus status;

    @Column(name = "total_minor", nullable = false)
    private long totalMinor;

    @Column(name = "currency", length = 3, nullable = false)
    private String currency;

    @Column(name = "placed_at", nullable = false)
    private Instant placedAt;

    @Column(name = "paid_at")
    private Instant paidAt;

    @Version
    @Column(name = "version", nullable = false)
    private long version;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private final List<OrderLine> lines = new ArrayList<>();

    public List<OrderLine> getLines() { return Collections.unmodifiableList(lines); }

    public static Order place(UUID customerId, List<NewOrderLine> requestedLines, Instant now) {
        Order order = new Order();
        order.id = UUID.randomUUID();
        order.customerId = customerId;
        order.status = OrderStatus.PENDING;
        order.placedAt = now;
        order.currency = "EUR";
        order.totalMinor = requestedLines.stream().mapToLong(l -> l.priceMinor() * l.quantity()).sum();
        for (var l : requestedLines) order.addLine(l);
        return order;
    }

    public void cancel() {
        if (status != OrderStatus.PENDING) throw new IllegalStateException("Cannot cancel order in state " + status);
        this.status = OrderStatus.CANCELLED;
    }

    public void markPaid(Instant now) {
        if (status != OrderStatus.PENDING) throw new IllegalStateException("Already " + status);
        this.status  = OrderStatus.PAID;
        this.paidAt  = now;
    }

    private void addLine(NewOrderLine l) {
        var line = new OrderLine(this, l.sku(), l.quantity(), l.priceMinor());
        lines.add(line);
    }
}
```

Rules:

- **Protected no-args constructor** (Lombok `@NoArgsConstructor(access = PROTECTED)`) — JPA-only entry point
- **Factory methods** (`place`, `cancel`, `markPaid`) — the only legitimate ways to construct or mutate
- **`@Version`** field — optimistic locking is on by default
- **Unmodifiable collections** exposed; private list mutated via factory / domain methods
- **Enum for status** + `EnumType.STRING` (never ORDINAL — fragile to reordering)
- **`UUID id` assigned in the factory**, not by the DB — distributed-safe and avoids the "save twice to get the id" trap
- **Snake_case columns** (matches `data/_shared/schema-design`)

For pure value records (DTOs / projections), use Java records:

```java
public record OrderSummaryDto(UUID id, String status, long totalMinor, String currency, Instant placedAt) {}
```

But **entities are classes**, not records — JPA needs setters / proxies that records don't support cleanly.

## Spring Data repositories

```java
public interface OrderRepository extends JpaRepository<Order, UUID> {

    // Derived query — Spring Data generates the SQL
    List<Order> findByCustomerIdOrderByPlacedAtDesc(UUID customerId, Limit limit);

    @Query("""
        SELECT new com.yourco.orders.application.OrderSummaryDto(
            o.id, o.status, o.totalMinor, o.currency, o.placedAt)
        FROM Order o
        WHERE o.customerId = :customerId
        ORDER BY o.placedAt DESC
        """)
    List<OrderSummaryDto> findSummariesByCustomer(@Param("customerId") UUID customerId, Pageable pageable);

    @EntityGraph(attributePaths = "lines")
    Optional<Order> findWithLinesById(UUID id);
}
```

Use:

- **Derived queries** (`findByXxxOrderByYyy`) for simple cases
- **`@Query`** when derivation isn't expressive or you want a projection
- **`@EntityGraph`** to eagerly fetch associations for a specific query (avoids N+1 without `FetchType.EAGER` global)
- **`Pageable` / `Limit`**: paging primitives
- **DTO constructor expressions** (`new com.x.Dto(...)`) for projections — fetches only the columns you need

## Transactions

`@Transactional` belongs on **service methods**, not on controllers or repositories.

```java
@Service
public class OrderService {

    private final OrderRepository repo;
    private final Clock clock;

    public OrderService(OrderRepository repo, Clock clock) { this.repo = repo; this.clock = clock; }

    @Transactional
    public UUID place(UUID customerId, List<NewOrderLine> lines) {
        Order order = Order.place(customerId, lines, clock.instant());
        repo.save(order);
        return order.getId();
    }

    @Transactional
    public void cancel(UUID id) {
        Order order = repo.findById(id).orElseThrow(() -> new NotFoundException(id));
        order.cancel();
        // save() not needed inside a managed transaction — dirty checking handles it
    }

    @Transactional(readOnly = true)
    public List<OrderSummaryDto> listForCustomer(UUID customerId, Pageable pageable) {
        return repo.findSummariesByCustomer(customerId, pageable);
    }
}
```

Rules:

- `readOnly = true` for pure reads — Hibernate skips dirty checking and flush
- **No self-invocation** of `@Transactional` methods — Spring AOP can't intercept (the proxy isn't called). Refactor into a separate service.
- **No `@Transactional` on the controller** — the entry point should orchestrate; transactions are domain-side
- **No long transactions** — never make external HTTP / Kafka / Redis calls inside a TX boundary; the DB connection is held the whole time

## Optimistic locking with `@Version`

```java
@Version
@Column(name = "version", nullable = false)
private long version;
```

On every save, Hibernate adds `WHERE version = ?` and increments the version. If the row was updated between read and write, the `UPDATE` affects 0 rows, Hibernate throws `OptimisticLockException`:

```java
@Transactional
public void cancel(UUID id) {
    try {
        Order order = repo.findById(id).orElseThrow();
        order.cancel();
    } catch (OptimisticLockingFailureException e) {
        throw new ConflictException("Order " + id + " was modified concurrently; retry");
    }
}
```

For high-contention rows (counters, leaderboards), prefer **pessimistic locking** via `LockModeType.PESSIMISTIC_WRITE`:

```java
@Query("SELECT o FROM Order o WHERE o.id = :id")
@Lock(LockModeType.PESSIMISTIC_WRITE)
Optional<Order> findByIdForUpdate(@Param("id") UUID id);
```

Use sparingly — pessimistic locking serializes access.

## N+1 prevention

The Hibernate footgun. Symptoms:

- One query to load N parents, then N queries to lazy-load each parent's children

Fixes:

1. **`@EntityGraph(attributePaths = "...")`** on the specific repository method that needs the children
2. **`JOIN FETCH`** in JPQL for one-off cases
3. **`@BatchSize(size = N)`** on the collection / entity to load children in batches (cuts N down)
4. **DTO projection** — never fetch the entity, fetch just what you need

Detect via:

- `spring.jpa.show-sql=true` in dev — eyeball the count of queries per request
- **OpenTelemetry tracing** (`observability/opentelemetry-java`) — N+1 is a fan of identical short DB spans on a parent
- A test: assert query count using a `@DataJpaTest` with a `StatementInspector` or a third-party tool

## Repository pattern: when to roll your own

Spring Data interfaces are the default. Roll a custom repository only when:

- You need a real abstraction across multiple stores (JPA + Redis + external API)
- The "named-queries" surface is large enough to deserve a type

Avoid creating an `IFooRepository` that wraps `JpaRepository<Foo, UUID>` 1:1 with `Get/Save/Delete`. That's the underlying repository again with extra ceremony.

## Spring Data JDBC vs JPA

For services that own a clear set of aggregates with no complex graph traversal, **Spring Data JDBC** is lighter and faster than JPA:

- No lazy loading; no proxies; no `@Transactional` self-invocation traps
- DTO-style aggregates
- More predictable performance

Use JDBC when the domain is "store and fetch aggregates"; JPA when the domain has rich graph navigation or you're already invested.

## Bulk operations

```java
@Modifying
@Transactional
@Query("UPDATE Order o SET o.status = 'CANCELLED' WHERE o.placedAt < :cutoff AND o.status = 'PENDING'")
int cancelStalePending(@Param("cutoff") Instant cutoff);
```

`@Modifying` for UPDATE / DELETE / INSERT-from-SELECT. For very large batches, drop to JDBC + `BatchPreparedStatementSetter`.

## DI registration

`application.yml` (per `devops/environment-config`):

```yaml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST}:5432/orders
    username: app
    password: ${DB_PASSWORD}
    hikari:
      maximum-pool-size: 20
      connection-timeout: 5000
      leak-detection-threshold: 60000
  jpa:
    hibernate:
      ddl-auto: validate                    # Flyway owns DDL, not Hibernate
    properties:
      hibernate.jdbc.batch_size: 50
      hibernate.order_inserts: true
      hibernate.order_updates: true
      hibernate.query.fail_on_pagination_over_collection_fetch: true
```

`ddl-auto: validate` is non-negotiable — Hibernate validates the schema at startup; Flyway owns changes.

## Common anti-patterns

- **`FetchType.EAGER` globally** — turns every read into a multi-table query
- **`@ManyToMany`** with no `@JoinTable` — Hibernate's default join table naming bites; declare it
- **Bidirectional associations** without managing both sides — orphan inconsistencies
- **`@Entity` on a class with `equals` / `hashCode` based on the generated id** — equal-before-save semantics break
- **`@OneToOne` with the wrong owning side** — extra queries on every read
- **`@Transactional` self-invocation** — proxy bypasses; the TX never starts
- **Loading entities to update a single field** when `@Modifying` / JDBC would do
- **Pagination over a fetch-joined collection** — Hibernate errors are noisy; fail at startup with `fail_on_pagination_over_collection_fetch=true`
- **`ddl-auto: update`** in production — silent schema drift

## Rules

- One repository per aggregate; derived queries + `@Query` for projections; `@EntityGraph` for eager-where-needed
- `@Transactional` on services only; `readOnly = true` for reads
- `@Version` on every shared-write aggregate
- `ddl-auto: validate`; Flyway owns DDL
- `EnumType.STRING` always
- Snake_case columns; explicit names; explicit indexes via migrations (not Hibernate annotations)
- Unmodifiable collections exposed from entities
- Factory methods + protected no-args ctor on entities
- DTO projections for reads that don't need the full entity
- OTel-traced DB calls; N+1 surfaced via tracing + dev SQL logging

## What NOT to do

- No `FetchType.EAGER` globally
- No `@Data` Lombok on entities — generates broken `equals`/`hashCode` and `toString` that pulls lazy associations
- No `cascade = ALL` on `@ManyToOne` — destroys parents you didn't intend to
- No `@Transactional` on controllers
- No self-invocation of `@Transactional` methods within the same class
- No long-running transactions (no HTTP / Kafka / Redis inside `@Transactional`)
- No `ddl-auto: update` / `create` in any environment beyond a developer laptop
- No string-concat SQL in `JdbcTemplate` — parameter binding only
- No mixing Flyway and Hibernate-DDL ownership
- No swallowing `OptimisticLockingFailureException` silently

## Generation steps

1. Confirm DB engine, Spring Boot version, migration tool (Flyway preferred).
2. Generate the entity class with `@Version`, factory methods, unmodifiable collections.
3. Generate the Spring Data repository interface with derived queries + `@Query` projections + `@EntityGraph` where needed.
4. Generate the service with `@Transactional` boundaries; map `OptimisticLockingFailureException` to a domain conflict.
5. Author the first Flyway migration `V<datetime>__create_orders.sql`.
6. Configure `application.yml` with `ddl-auto: validate` and HikariCP sizing.
7. Add OTel instrumentation + structured logging for DB observability.
8. Smoke test repository methods (`@DataJpaTest`).

## Handoffs

- DB engine specifics → `data/postgresql` / `data/sqlserver` / `data/mysql`
- Migrations across engines → `data/_shared/migrations`
- Query optimization principles → `data/_shared/query-optimization`
- Caching → `data/_shared/caching-patterns` + `data/redis`
- API DTOs / POJOs the layer exposes → `qa/java/skills/api-dto-writer`
- .NET equivalent → `backend/dotnet/skills/persistence`
- Node equivalent → `backend/node/skills/persistence`
