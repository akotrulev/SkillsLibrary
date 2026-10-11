---
name: patterns
description: Use when the user asks to explain, describe, or look up a design pattern in Java 21 / Spring Boot 3. Triggers: "what is the strategy pattern in Java", "explain CQRS in Spring Boot", "when should I use the repository pattern in Spring Data", "Java records as DTOs", "sealed types for state machines". Do NOT use for scaffolding code into a repo (use `backend/java/skills/pattern-writer`) or for reviewing existing code (use `backend/java/skills/code-review`).
---

# Java Design Patterns — Reference

Conceptual reference for design patterns as applied in Java 21 + Spring Boot 3.x. Each pattern card explains intent, when to use, when not to, and shows a minimal canonical example using modern Java (records, sealed types, pattern matching, virtual threads). The library's global rules (`CLAUDE.md`) apply: constructor injection, no static mutable state, async via `CompletableFuture` / virtual threads — no thread blocking in reactive paths.

## Version policy

Confirm the project's Java release (`sourceCompatibility` / `java.toolchain` in `build.gradle(.kts)` or `<java.version>` in `pom.xml`) and Spring Boot major before answering. This file targets Java 21 + Spring Boot 3.x; if the project sits on an older Java (17) or Spring Boot 2.x, note which recipes below need a fallback (sealed types and virtual threads are Java 21+; records are Java 16+) rather than applying them unmodified.

## When to use

- The user asks "what is pattern X in Java"
- The user wants a comparison between two patterns
- The user wants a small canonical example, not scaffolding

## When NOT to use

- Scaffolding into a project → `backend/java/skills/pattern-writer`
- Reviewing code → `backend/java/skills/code-review`

---

## Strategy

**Intent**: Encapsulate interchangeable algorithms behind a common interface so the caller can swap them without changing call-site code.

**When to use**:
- An `if`/`else` or `switch` chain selects behavior based on a type / mode field
- Variants are added regularly
- All variants share a clear input/output shape

**When NOT to use**:
- Two variants with no growth signal → method overload is fine
- Variants have different shapes — bending the interface is worse than the switch

**Minimal example**:

```java
public interface PricingStrategy {
    Money calculate(Cart cart);
}

@Component
@Qualifier("standard")
public class StandardPricing implements PricingStrategy { /* ... */ }

@Component
@Qualifier("b2b")
public class B2bPricing implements PricingStrategy { /* ... */ }

@Service
public class CheckoutService {
    private final Map<String, PricingStrategy> byMode;

    public CheckoutService(List<PricingStrategy> all) {
        // Spring injects all beans; map by the qualifier or type
        this.byMode = all.stream().collect(Collectors.toMap(
            p -> p.getClass().getAnnotation(Qualifier.class).value(), p -> p));
    }

    public Money price(Cart cart, String mode) {
        return byMode.get(mode).calculate(cart);
    }
}
```

Modern alternative — **sealed types + pattern matching** when the variants are fixed and known:

```java
public sealed interface Pricing permits Standard, B2b, Promotional {}
public record Standard() implements Pricing {}
public record B2b(String contractId) implements Pricing {}
public record Promotional(String code) implements Pricing {}

Money price = switch (p) {
    case Standard ignored          -> standardPricing(cart);
    case B2b(var contractId)       -> b2bPricing(cart, contractId);
    case Promotional(var code)     -> promoPricing(cart, code);
};
```

## Repository (Spring Data style)

**Intent**: Domain-shaped access to persistence, decoupled from the engine.

**When to use**:
- Multiple data sources behind one logical store (DB + cache + API)
- The query language is too leaky for domain code (raw JPQL in services)
- A named-query set earns the type (`findByStatusAndPlacedAtBetween`)

**When NOT to use**:
- A 1:1 `Get/Save/Delete` wrapper around `JpaRepository<Foo, Long>` — that's `JpaRepository<Foo, Long>` with a different name

**Minimal example**:

```java
public interface OrderRepository extends JpaRepository<Order, UUID> {
    List<Order> findByCustomerIdOrderByPlacedAtDesc(UUID customerId, Limit limit);
    Optional<Order> findByIdAndTenantId(UUID id, String tenantId);
}
```

Spring Data generates the implementation. Add `@Query` only when the derivation can't express the query.

## Builder

**Intent**: Construct complex objects step-by-step; fluent and readable at the call site.

**When to use**:
- Domain object with 4+ fields, especially when some are optional
- Test data factory (see `qa/java/skills/test-data-builder`)
- Construction has invariants that the builder can enforce

**When NOT to use**:
- Simple value classes — use a record with named parameters

**Minimal example with Lombok**:

```java
@Builder
public record Order(UUID id, UUID customerId, String status, long totalMinor, String currency) {}

Order o = Order.builder()
    .id(UUID.randomUUID())
    .customerId(customer)
    .status("PENDING")
    .totalMinor(9999)
    .currency("EUR")
    .build();
```

## Factory / Abstract Factory

**Intent**: Encapsulate non-trivial construction decisions.

```java
@Component
public class PaymentGatewayFactory {
    private final Map<PaymentProvider, PaymentGateway> gateways;

    public PaymentGatewayFactory(StripeGateway stripe, AdyenGateway adyen) {
        this.gateways = Map.of(PaymentProvider.STRIPE, stripe, PaymentProvider.ADYEN, adyen);
    }

    public PaymentGateway create(PaymentProvider provider) {
        return Optional.ofNullable(gateways.get(provider))
            .orElseThrow(() -> new IllegalArgumentException("Unknown: " + provider));
    }
}
```

## Decorator

**Intent**: Wrap a service with cross-cutting behavior (logging, retry, caching) without modifying it.

```java
public class LoggingOrderService implements OrderService {
    private final OrderService inner;
    private final MeterRegistry metrics;

    public LoggingOrderService(@Qualifier("real") OrderService inner, MeterRegistry metrics) {
        this.inner = inner;
        this.metrics = metrics;
    }

    @Override
    public Order place(NewOrder o) {
        var sample = Timer.start(metrics);
        try { return inner.place(o); }
        finally { sample.stop(metrics.timer("orders.place")); }
    }
}
```

One concern per decorator. Order them deliberately: cache → retry → logging → real impl.

## CQRS + Command / Query Handler

**Intent**: Separate read and write models when their shapes diverge.

**When to use**:
- Real read/write asymmetry (read model joins many tables; write model is small + transactional)
- > ~30 endpoints, cross-cutting concerns benefiting from a pipeline
- Event-driven projection of read models

**When NOT to use**:
- CRUD over one aggregate — MediatR/CQRS is tax

```java
public sealed interface OrderCommand {}
public record PlaceOrder(UUID customerId, List<NewLine> lines) implements OrderCommand {}
public record CancelOrder(UUID id) implements OrderCommand {}

@Service
public class PlaceOrderHandler {
    private final OrderRepository repo;
    private final Clock clock;

    @Transactional
    public UUID handle(PlaceOrder cmd) {
        var order = Order.place(cmd.customerId(), cmd.lines(), clock.instant());
        repo.save(order);
        return order.getId();
    }
}
```

Spring's `@Async` + `CompletableFuture` covers most async needs without a full mediator framework.

## Specification (predicates over data)

**Intent**: Compose query predicates.

```java
public interface Specification<T> {
    boolean test(T t);
    default Specification<T> and(Specification<T> other) { return t -> test(t) && other.test(t); }
    default Specification<T> or(Specification<T> other)  { return t -> test(t) || other.test(t); }
}
```

For JPA, use the built-in `org.springframework.data.jpa.domain.Specification<T>` which compiles to a `CriteriaQuery`.

## Pipeline / Chain of Responsibility

**Intent**: Stage-based processing where each stage decides to handle or pass.

```java
public sealed interface Stage permits AuthStage, ValidateStage, ProcessStage {
    Outcome handle(Request req, Context ctx);
}

@Component
public class Pipeline {
    private final List<Stage> stages;
    public Outcome run(Request req) {
        var ctx = new Context();
        for (var stage : stages) {
            var outcome = stage.handle(req, ctx);
            if (outcome.isTerminal()) return outcome;
        }
        return Outcome.empty();
    }
}
```

Spring Security's filter chain, MVC interceptors, and `HandlerInterceptor` are all instances of this pattern — don't reinvent them.

## Options / Type-safe configuration

**Intent**: Replace scattered `${some.prop}` reads with a typed config bean.

```java
@ConfigurationProperties(prefix = "orders")
@Validated
public record OrdersOptions(
    @NotBlank String pricingMode,
    @Min(1) @Max(1000) int maxLines
) {}

@Service
public class OrdersService {
    private final OrdersOptions options;
    public OrdersService(OrdersOptions options) { this.options = options; }
}
```

Enable via `@ConfigurationPropertiesScan` (Spring Boot 3) or `@EnableConfigurationProperties(OrdersOptions.class)`.

## Sealed types for state machines

Java's `sealed`/`permits` plus pattern matching makes state machines first-class:

```java
public sealed interface OrderState permits Pending, Paid, Cancelled, Refunded {}
public record Pending(Instant placedAt) implements OrderState {}
public record Paid(Instant placedAt, Instant paidAt, String method) implements OrderState {}
public record Cancelled(Instant placedAt, Instant cancelledAt, String reason) implements OrderState {}
public record Refunded(Instant placedAt, Instant paidAt, Instant refundedAt) implements OrderState {}

OrderState next = switch (current) {
    case Pending p          -> new Paid(p.placedAt(), Instant.now(), "card");
    case Paid p             -> new Refunded(p.placedAt(), p.paidAt(), Instant.now());
    case Cancelled c        -> c;          // terminal
    case Refunded r         -> r;          // terminal
};
```

Exhaustive switch — adding a new state forces every consumer to update.

## Virtual threads & async

Spring Boot 3.2+ auto-uses **virtual threads** when configured (`spring.threads.virtual.enabled=true`). Implications:

- **Blocking I/O is fine** in virtual-thread-backed handlers — pool exhaustion is no longer the bottleneck
- **`@Async`** still useful for fire-and-forget; backed by virtual threads when enabled
- Reactive (`Mono`/`Flux`) is no longer the default answer for scaling I/O — keep it for stream processing, backpressure-shaped APIs

## Records as DTOs

```java
public record OrderDto(UUID id, UUID customerId, String status, long totalMinor, String currency, Instant placedAt) {}
```

- Immutable by default; canonical constructor; `equals` / `hashCode` / `toString` generated
- Jackson serializes records natively
- Use for DTOs, value objects, immutable domain events; not for behavior-bearing services

## Handoffs

- Scaffolding patterns into a project → `backend/java/skills/pattern-writer`
- Reviewing code for misuse → `backend/java/skills/code-review`
- .NET equivalents → `backend/dotnet/skills/pattern-guide`
- TypeScript equivalents → `backend/node/skills/pattern-guide`
- API DTO scaffolding → `qa/java/skills/api-models`
