---
name: be-java-pattern-writer
description: Use when the user asks to scaffold a design pattern in Java 21 / Spring Boot 3 into the active repo. Triggers: "scaffold strategy in Spring Boot", "create a repository for X", "wire up a command handler for Y", "add a decorator for Z", "extract this if-else into a strategy", "type-safe @ConfigurationProperties for W". Do NOT use for explanations (use `backend/java/skills/pattern-guide`) or reviews (use `backend/java/skills/code-review`).
---

# Java Design Patterns — Generator

Scaffolds pattern implementations into a Java 21 + Spring Boot 3.x codebase. Constructor injection, records for value-shaped data, sealed types for state machines, Spring Data for repositories. Each generated file is one logical change; tests sit alongside.

## Version policy

**First act: detect the project's Java release and Spring Boot major** (`build.gradle(.kts)` toolchain / `pom.xml` `<java.version>`, and the Spring Boot BOM version) before scaffolding. Sealed types + pattern-matching switch and virtual threads assume Java 21+; if the project is on Java 17 / Spring Boot 2.x, fall back to `if`/`instanceof` chains and thread-pool `@Async` and say so rather than generating code that won't compile.

## When to use

- Replacing an `if`/`else` or `switch` chain with a strategy
- Wrapping a service with a decorator (logging, retry, caching, validation)
- Extracting CQRS for a slice with real read/write asymmetry
- Repository / Specification when there's a genuine abstraction need
- Factory / Abstract Factory when construction is non-trivial and reused
- Type-safe `@ConfigurationProperties` to replace scattered `@Value`

## When NOT to use

- Explanations → `backend/java/skills/pattern-guide`
- Reviewing existing code → `backend/java/skills/code-review`
- Scaffolding tests against the generated code → `qa/java/skills/api-test-author/writer` if API-facing

## Inputs needed

1. **Pattern** (Strategy, Decorator, Repository, Specification, Factory, Command/Query handler, Options, Pipeline, sealed-state-machine)
2. **Domain** + concrete variants
3. **Target package** and module layout (hexagonal / clean / vertical slice)
4. **Existing call site** to refactor (paste or path) — anchors the rename / extraction
5. **DI container** — Spring is the default

## Recipes

### Strategy with Spring `@Qualifier`

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

    public CheckoutService(List<PricingStrategy> strategies) {
        this.byMode = strategies.stream().collect(Collectors.toUnmodifiableMap(
            s -> s.getClass().getAnnotation(Qualifier.class).value(),
            s -> s));
    }

    public Money price(Cart cart, String mode) {
        var strategy = byMode.get(mode);
        if (strategy == null) throw new IllegalArgumentException("Unknown mode: " + mode);
        return strategy.calculate(cart);
    }
}
```

For fixed, closed variants prefer **sealed types + pattern matching** (see reference).

### Decorator

```java
@Service
@Primary
public class LoggingOrderService implements OrderService {
    private static final Logger log = LoggerFactory.getLogger(LoggingOrderService.class);
    private final OrderService inner;

    public LoggingOrderService(@Qualifier("real") OrderService inner) { this.inner = inner; }

    @Override
    public Order place(NewOrder o) {
        log.info("Placing order for customerId={}", o.customerId());
        var result = inner.place(o);
        log.info("Placed orderId={}", result.id());
        return result;
    }
}

@Service
@Qualifier("real")
public class OrderServiceImpl implements OrderService { /* ... */ }
```

One concern per decorator (logging / retry / caching / validation). Document the chain order in the package's `package-info.java`.

### Repository — only when it earns its keep

```java
public interface OrderRepository extends JpaRepository<Order, UUID> {
    @Query("SELECT o FROM Order o WHERE o.tenantId = :tenantId AND o.id = :id")
    Optional<Order> findByIdAndTenant(@Param("id") UUID id, @Param("tenantId") String tenantId);

    List<Order> findByCustomerIdOrderByPlacedAtDesc(UUID customerId, Limit limit);
}
```

For complex queries, prefer Spring Data's `Specification<T>` over hand-rolled JPQL strings. Drop to JdbcTemplate / `EntityManager` only when JPQL can't express it.

### Command / Query handler (lightweight CQRS)

```java
public sealed interface OrderCommand permits PlaceOrder, CancelOrder {}
public record PlaceOrder(UUID customerId, List<NewLine> lines) implements OrderCommand {}
public record CancelOrder(UUID id, String reason) implements OrderCommand {}

@Service
public class PlaceOrderHandler {
    private final OrderRepository repo;
    private final Clock clock;

    public PlaceOrderHandler(OrderRepository repo, Clock clock) {
        this.repo = repo; this.clock = clock;
    }

    @Transactional
    public UUID handle(PlaceOrder cmd) {
        var order = Order.place(cmd.customerId(), cmd.lines(), clock.instant());
        repo.save(order);
        return order.getId();
    }
}
```

Don't introduce Axon / mediator frameworks until you've measured the need.

### Factory

```java
@Component
public class PaymentGatewayFactory {
    private final EnumMap<PaymentProvider, PaymentGateway> gateways;

    public PaymentGatewayFactory(StripeGateway stripe, AdyenGateway adyen) {
        this.gateways = new EnumMap<>(Map.of(
            PaymentProvider.STRIPE, stripe,
            PaymentProvider.ADYEN, adyen));
    }

    public PaymentGateway create(PaymentProvider provider) {
        return Optional.ofNullable(gateways.get(provider))
            .orElseThrow(() -> new IllegalArgumentException("Unsupported provider: " + provider));
    }
}
```

### `@ConfigurationProperties` (Options)

```java
@ConfigurationProperties(prefix = "orders")
@Validated
public record OrdersOptions(
    @NotBlank String pricingMode,
    @Min(1) @Max(1000) int maxLines,
    @NotNull Duration cacheTtl
) {}

@Configuration
@ConfigurationPropertiesScan
public class OptionsConfig {}
```

Inject as `OrdersOptions opts`; never `@Value("${orders.pricingMode}")` scattered in services.

### Sealed-state machine

```java
public sealed interface OrderState permits Pending, Paid, Cancelled, Refunded {}
public record Pending(Instant placedAt) implements OrderState {}
public record Paid(Instant placedAt, Instant paidAt, String method) implements OrderState {}
public record Cancelled(Instant placedAt, Instant cancelledAt, String reason) implements OrderState {}
public record Refunded(Instant placedAt, Instant paidAt, Instant refundedAt) implements OrderState {}

@Service
public class OrderStateMachine {
    public OrderState pay(OrderState current, String method) {
        return switch (current) {
            case Pending p -> new Paid(p.placedAt(), Instant.now(), method);
            case Paid p -> throw new IllegalStateException("Already paid");
            case Cancelled c -> throw new IllegalStateException("Cannot pay a cancelled order");
            case Refunded r -> throw new IllegalStateException("Already refunded");
        };
    }
}
```

The compiler enforces exhaustiveness. Adding a new state breaks every switch — that's the point.

### Pipeline

```java
public sealed interface Stage permits AuthStage, ValidateStage, ProcessStage {
    Outcome handle(Request req, Context ctx);
}

@Component
public class RequestPipeline {
    private final List<Stage> stages;

    public RequestPipeline(List<Stage> stages) { this.stages = stages; }

    public Outcome run(Request req) {
        var ctx = new Context();
        for (Stage s : stages) {
            var outcome = s.handle(req, ctx);
            if (outcome.isTerminal()) return outcome;
        }
        return Outcome.success();
    }
}
```

For HTTP, use Spring's existing `HandlerInterceptor` / `OncePerRequestFilter` — don't reinvent middleware.

## Rules

- **Constructor injection** only; never `@Autowired` on fields/setters
- **`final` fields** in injected dependencies (becomes default for records / Lombok `@RequiredArgsConstructor`)
- **Records** for value-shaped data; **classes** for behavior-bearing services
- **`sealed`/`permits`** for closed sums / state machines; pattern matching for dispatch
- **No static mutable state** (constants fine)
- **Async**: virtual threads (`spring.threads.virtual.enabled=true` in Boot 3.2+) make blocking I/O viable; use `@Async` for fire-and-forget; reactive only when you've measured the need
- One DI registration block per module (`@Configuration` class), not scattered across the codebase
- One pattern per problem — flag stacking
- File per type; package by feature (vertical slice) preferred over package by layer

## What NOT to do

- No field injection (`@Autowired private XService x;`) — constructor only
- No `Optional` for fields — only return types
- No `null` returns where `Optional.empty()` or a sealed `Result` type fits
- No "I-have-one-impl" interfaces; wait for the second
- No `Repository` wrapping `JpaRepository` 1:1 with `Get/Save/Delete`
- No CQRS for CRUD slices — direct service + repository is fine
- No `Thread.sleep` in production code; no busy-waits
- No `RuntimeException` thrown to control flow when a sealed result type would do
- No mutable static fields (constants `static final` are fine)
- No `@Value("${prop}")` sprinkled — use `@ConfigurationProperties`
- No swallowing `InterruptedException` without re-interrupting — `Thread.currentThread().interrupt();`

## Generation outputs

For every pattern:

1. The contract (interface / sealed type / record) in the domain package
2. Concrete implementations (one per file) under the matching package
3. A `@Configuration` class registering the components (when not auto-component-scanned)
4. A TestNG test using the conventions from `qa/java/skills/api-test-author/writer` if API-facing, otherwise plain TestNG + AssertJ

## Validation

After scaffolding:

- `./gradlew build` — 0 warnings (Gradle `compileJava` set to `-Werror`)
- `./gradlew test` — generated tests pass
- `./gradlew checkstyleMain spotlessCheck` — formatting clean
- Sweep old call sites that the new pattern replaces; remove dead code

## Handoffs

- Conceptual lookup → `backend/java/skills/pattern-guide`
- Reviewing the result → `backend/java/skills/code-review`
- Tests for new API → `qa/java/skills/api-test-author/writer`
- POJOs/records → `qa/java/skills/api-models`
- .NET equivalent → `backend/dotnet/skills/pattern-writer`
- TypeScript equivalent → `backend/node/skills/pattern-writer`
