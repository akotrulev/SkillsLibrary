---
name: unit-testing
description: Use when backend Java logic needs a dev-side unit test — JUnit 5 + Mockito + AssertJ with no Spring context: what deserves a test, the five untestable seams (Clock, id, randomness, config, outbound I/O), fakes-over-mocks, parameterized cases, async, the ≥ 80% branch-coverage floor on changed code. In-process, no container, no real database. Triggers "unit-test this service", "test this validator/calculator", "how do I fake the clock in a Java test". Do NOT use for anything that boots a Spring context — that's the `qa-api-java` peer's.
---

# Java — Unit Testing (JUnit 5 + Mockito + AssertJ)

Owns **dev-side unit tests of backend logic**: construct a class with `new`, drive it, assert on its return value or its observable effect on a fake collaborator. **No Spring context, no container, no real database, no broker, no filesystem, no clock.**

**The boundary, one sentence:** if the test needs **any** annotation that starts an application context — `@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest`, `@JsonTest`, `@ExtendWith(SpringExtension.class)` — it is not a unit test and it belongs to the **peer** [`qa-api-java`](../../../../qa/java/agents/qa-api-java.md).

That line is worth stating twice, because Spring's slice-test annotations are routinely *called* unit tests. **A slice test is fast, not isolated.** It reads `application.yml`, builds a context, and fails for reasons unrelated to your logic. `@ExtendWith(MockitoExtension.class)` is this skill's extension; `SpringExtension` is the peer's.

**Runner — house-default deviation, stated once.** `CLAUDE.md`'s Java test-runner default is **TestNG**, and that is correct for the **QA suite**. Dev-side unit tests use **JUnit 5**, because `spring-boot-starter-test` ships JUnit 5 + Mockito + AssertJ + Spring's own test support as one managed dependency, and every Boot 3.x recipe assumes the Jupiter lifecycle. Introducing TestNG into a Boot service means a second runner, a second lifecycle, and a manual dependency graph for zero gain. **Use JUnit 5 here; if the service already standardizes on TestNG, match it and don't fight it.** (Same shape as `fe-blazor:component-testing`'s xUnit-for-bUnit deviation.) `pattern-writer` previously said "plain TestNG + AssertJ" for this lane — that has been corrected to point here.

**This skill is not a licence to replace integration tests with mocks.** `CLAUDE.md`'s preference for real-DB integration tests over mocks governs the integration lane, which is the peer's. Some things are only provable against a real dependency:

| Never unit-test this | Because | Belongs to |
|---|---|---|
| A Spring Data repository, `@Query`, a Criteria/Specification build | JPQL/SQL validity and the generated SQL are the thing under test | `qa-api-java` `db-testing/testcontainers` |
| Entity mappings, `@OneToMany` fetch behavior, lazy-loading, N+1 | Only a real `EntityManager` + DB shows the queries | `qa-api-java`, `data-architect` |
| `@Transactional` boundaries, propagation, rollback-on-exception | The proxy + a real tx manager are the mechanism | `qa-api-java` |
| A Flyway migration | Only a real engine proves it applies | `qa-api-java` + `data-architect` |
| The security filter chain, JWT decoding, `@PreAuthorize` end-to-end | The filter chain is the thing under test | `qa-api-java` `test-login-tokens`, `qa-security` |
| Request mapping, content negotiation, `@Valid` triggering at the boundary | Transport concerns | `qa-api-java` |

## Version policy

**First act: detect the Java release and the Spring Boot BOM version** (`build.gradle.kts` / `pom.xml`). **Java 21 + Spring Boot 3.x.** Let the Boot BOM manage JUnit/Mockito/AssertJ versions — **do not pin them independently**; a hand-pinned Mockito against a Boot-managed JUnit is the most common "works on my machine" break in this lane. `java.time.Clock` is JDK-native, so the time seam needs no dependency at all.

## When to use

- A class `pattern-writer` just generated has behavior: a strategy, a resolver, a decorator, a pipeline stage, a handler, a factory.
- A domain rule, invariant, or guard clause needs pinning before a refactor.
- A calculation: money (`BigDecimal`), rounding, proration, tax, date math.
- A mapper, a sealed-type state transition, an exception-to-response translation.
- A `jakarta.validation` constraint set (buildable without Spring — see below).
- Reproducing a bug at the unit level before fixing it (`dev:debugging` RED).

## When NOT to use

- Anything that boots a context (`@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest`, `@JsonTest`) → **peer** `qa-api-java`
- Contract / integration / E2E, Testcontainers, real-DB seed-assert-clean → **peer** `qa-api-java` (`db-testing/*`)
- Whether the tests actually catch faults (mutation score) → **peer** `qa-java:test-quality-check` (PIT/pitest)
- Suite-scale builders / ObjectMother → **peer** `qa-java:test-data-builder`
- **Records/DTOs with no behavior, entities, `@Configuration` classes, generated code** → don't test them at all

## Stack

```kotlin
// build.gradle.kts — versions come from the Boot BOM, not from here
dependencies {
    testImplementation("org.springframework.boot:spring-boot-starter-test") // JUnit 5 + Mockito + AssertJ
    testImplementation("org.mockito:mockito-junit-jupiter")                 // @ExtendWith(MockitoExtension.class)
}
tasks.test { useJUnitPlatform() }
```

| Concern | What | Notes |
|---|---|---|
| Runner | **JUnit 5 (Jupiter)** | Via `spring-boot-starter-test`; `useJUnitPlatform()` in the `test` task |
| Doubles | **Mockito** | `mockito-junit-jupiter` for the extension. Mockito 5 uses the **inline** mock maker by default — `final` classes/methods are technically mockable now, which does **not** make mocking them a good idea (see traps) |
| Assertions | **AssertJ** (`assertThat`) | House choice — fluent, one entry point, best `BigDecimal`/collection support |
| Time | **`java.time.Clock`** | JDK-native; `Clock.fixed` / `Clock.offset`. No dependency |
| Validation | `jakarta.validation` + the Hibernate Validator on the test classpath | Build a `Validator` directly — no Spring needed |

**`spring-boot-starter-test` pulls in Spring test support. Using the dependency is fine; using its context-starting annotations in this project is not** — that's the fence, and it's a review point.

## What deserves a unit test — the selection matrix

| Unit shape | Test it? | What to assert |
|---|---|---|
| Domain invariant / guard clause | **Yes** | Invalid input → the specific exception type; valid → accepted |
| Strategy implementation | **Yes** | Input → that algorithm's output |
| Strategy resolver / `Map<Type, Strategy>` lookup | **Yes** | Key → right implementation; unknown key → the defined failure, not `null` |
| Decorator | **Yes** | Delegate called once with the same args **and** the added behavior happened |
| Service / use-case orchestration | **Yes** | Collaborators driven correctly; returned value; the failure branch |
| Calculation (`BigDecimal` money, rounding, date math) | **Yes** | Boundaries, the rounding mode, the scale contract |
| Sealed-type state machine | **Yes** | Each permitted transition, and that a refused one throws |
| Mapper / DTO↔domain translation | **Yes** | Each branch; an unmapped input doesn't become a silent default |
| `jakarta.validation` constraint set | **Yes** | The violation's `propertyPath` and message key |
| `@ConfigurationProperties` record | **Yes**, for its *validation* | Construct it directly; assert the invalid case is rejected |
| Record/DTO with no behavior | **No** | Testing an accessor is a tautology |
| JPA entity / repository | **No** | Integration lane — `qa-api-java` |
| `@Configuration` / bean wiring | **No** | One context smoke test at most, and that's the peer's |
| Controller as pure transport | **No** | If there's logic in the controller, that's the defect — move it down |

**The tautology test:** if deleting the assertion leaves a passing test, delete the test.

## Project layout & setup

Match the repo first. Standard Gradle/Maven layout, mirroring the main source tree:

```
src/main/java/com/acme/ordering/PlaceOrderService.java
src/test/java/com/acme/ordering/PlaceOrderServiceTest.java     # this skill
src/test/java/com/acme/ordering/fakes/InMemoryOrderRepository.java
src/test/java/com/acme/ordering/builders/OrderBuilder.java
```

- **One test class per class under test**, same package (package-private access without `@VisibleForTesting` hacks), named `<ClassName>Test`. Reserve `<ClassName>IT` for the peer's integration tests, and keep them in a separate source set / Gradle task so `test` stays fast.
- Test classes and methods are **package-private** in JUnit 5 — no `public` needed.
- **No field injection into the class under test.** Construct it with `new` in `@BeforeEach` (or in the test). `@InjectMocks` is discouraged here: it fills fields reflectively, so a constructor-signature change compiles and silently leaves a `null` — the exact failure constructor injection exists to prevent.
- **No shared mutable state between tests.** JUnit 5 creates a fresh instance per test method by default — do not defeat that with `static` fields or `@TestInstance(PER_CLASS)` plus mutation.

## Naming

`should_<Outcome>_when_<Condition>` (or the repo's existing convention), optionally with `@DisplayName` for a full sentence. The name states behavior, never implementation:

```java
@Test
@DisplayName("rejects the order when the cart is empty")
void should_RejectOrder_when_CartIsEmpty() { … }

// bad
void testPlaceOrder()          // says nothing
void should_CallRepository()   // asserts a mechanism, not a behavior
```

## The five seams — what makes logic untestable

If you cannot write the test without one of these, **fix the seam first** — do not reach for `mockStatic`.

| Seam | Untestable | Injectable | Fake it with |
|---|---|---|---|
| **Time** | `Instant.now()`, `LocalDate.now()`, `System.currentTimeMillis()` | `java.time.Clock` (constructor-injected; register one `@Bean`) | `Clock.fixed(instant, ZoneOffset.UTC)`, `Clock.offset` to advance |
| **Identity** | `UUID.randomUUID()` | an `IdGenerator` interface (or pass the id in) | a stub returning a fixed sequence |
| **Randomness** | `new Random()`, `Math.random()` | an injected abstraction | a deterministic stub, or a seeded `Random` |
| **Config** | `@Value` reads inside logic, `System.getenv` | a `@ConfigurationProperties` **record** | construct the record directly in the test |
| **Outbound I/O** | `RestClient`/`WebClient`/`RestTemplate`, an SDK client, `Files.*` | your own port interface | a hand-written fake, or a Mockito mock of *your* interface |

```java
private static final Instant NOW = Instant.parse("2026-08-09T12:00:00Z");
private final Clock clock = Clock.fixed(NOW, ZoneOffset.UTC);

@Test
void should_ReportExpired_when_ClockPassesExpiry() {
    var service = new SubscriptionService(Clock.offset(clock, Duration.ofDays(31)));
    assertThat(service.isExpired(new Subscription(NOW.plus(Duration.ofDays(30))))).isTrue();
}
```

```java
// Validation without Spring
try (var factory = Validation.buildDefaultValidatorFactory()) {
    var violations = factory.getValidator().validate(new CreateOrderRequest(null, 0));
    assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                          .contains("customerId");
}
```

**Never mock a type you don't own** — no mocking `Clock` (use `Clock.fixed`), `EntityManager`, `RestClient`, or an SDK type. Wrap it in your own port and fake that.

## Test doubles

**Preference order: real object → hand-written fake → Mockito stub → `verify()`.**

| Use | When |
|---|---|
| **The real collaborator** | It's a pure value/calculator — faking it hides integration bugs between the two |
| **Hand-written fake** (an in-memory repository over a `HashMap`) | Stateful collaborator used across many tests. Clearer and cheaper than re-stubbing per test |
| **Mockito stub** (`when(...).thenReturn(...)`) | You feed a value in and don't care how it was called |
| **`verify()`** | The call *is* the observable behavior — an event published, an email sent, an audit written |

```java
@ExtendWith(MockitoExtension.class)
class PlaceOrderServiceTest {

    @Mock OrderRepository repository;
    @Mock EventPublisher publisher;

    private final Clock clock = Clock.fixed(Instant.parse("2026-08-09T12:00:00Z"), ZoneOffset.UTC);
    private PlaceOrderService service;

    @BeforeEach
    void setUp() {
        service = new PlaceOrderService(repository, publisher, clock);   // constructor, not @InjectMocks
    }

    @Test
    void should_PublishOrderPlaced_when_OrderIsAccepted() {
        var result = service.place(new PlaceOrder(CUSTOMER_ID, List.of("sku-1")));

        assertThat(result.accepted()).isTrue();
        verify(publisher).publish(argThat(e -> e.customerId().equals(CUSTOMER_ID)));
    }
}
```

**Prefer a state assertion over a `verify()`** where both work: asserting on a fake's recorded state survives a refactor that `verify(publisher).publish(...)` does not.

### Mockito traps

- **`MockitoExtension` is STRICT_STUBS by default** — an unused `when(...)` fails the test with `UnnecessaryStubbingException`. That is a **feature**: it means the stub was describing a call that no longer happens. Delete the stub; don't reach for `lenient()`.
- **`@InjectMocks` hides constructor changes** — prefer `new` (above).
- **Mocking `final` / static** — Mockito 5's inline maker makes it possible; it's still a design smell. `mockStatic` over your own static helper means the helper should be an injected collaborator.
- **Don't `verify()` the logger** — logs aren't the contract, unless the class's only job is producing an audit record.
- **`any()` matchers hide contracts** — `verify(publisher).publish(any())` proves almost nothing. Use `argThat` / an `ArgumentCaptor` and assert the payload.
- **Never `spy()` the class under test** to stub one of its own methods — that's two responsibilities in one class. Split it.

## Parameterized tests

`CLAUDE.md` forbids `if`/`for` driving assertions. Jupiter's data sources are the escape hatch:

```java
@ParameterizedTest
@CsvSource({ "0.005, 0.01", "0.004, 0.00", "-0.005, -0.01" })
void should_RoundHalfUp_when_ThirdDecimalPresent(BigDecimal input, BigDecimal expected) {
    assertThat(Money.round(input)).isEqualByComparingTo(expected);
}
```

`@MethodSource` for constructed cases, `@EnumSource` for exhausting an enum (which also fails when someone adds a constant — a useful alarm), `@ValueSource` for single values.

## `BigDecimal` — the Java-specific trap

**`assertThat(x).isEqualTo(y)` on `BigDecimal` compares scale too**: `2.50` is *not* equal to `2.5`. Use **`isEqualByComparingTo`** unless the scale itself is the contract — and when it is, assert it explicitly:

```java
assertThat(total).isEqualByComparingTo("2.5");        // value
assertThat(total.scale()).isEqualTo(2);               // scale, when it's part of the contract
```

Money: minor units or `BigDecimal` with an explicit `RoundingMode` — **never `double`**. The rounding mode is a business rule; assert it at the boundary (`.005`).

## Test data

- 1–3 fields: inline literals, named constants when the value carries meaning.
- **4+ fields: a builder** (`CLAUDE.md`) with sane defaults, so a test overrides only its subject:

```java
var order = anOrder().withStatus(SHIPPED).build();
```

- Java records make defaults awkward — a static factory (`anOrder()`) plus `withX` returning a new builder is the cheapest readable shape.
- Suite-scale data / ObjectMother → **peer** `qa-java:test-data-builder`.

## Async & concurrency

- `assertThatThrownBy(() -> …).isInstanceOf(X.class)` for expected failures; assert the **type**, not the message string.
- `CompletableFuture`: assert on `join()`/`get()` of an already-completed future, or use `assertThat(future).succeedsWithin(Duration.ofMillis(100))` (AssertJ). **No `Thread.sleep`.**
- Virtual threads (Java 21) change nothing about unit tests — a unit test shouldn't need concurrency at all. If it does, the concurrency itself is the subject and probably belongs to the peer's lane with a real executor.
- **Awaitility belongs to integration tests**, not here — if a unit needs polling, you're waiting on real I/O.

## Rules

- One logical assertion per test; `assertThat(x).satisfies(…)` or AssertJ's `assertAll`-style chaining to group related checks on one object.
- Arrange–Act–Assert, visibly separated. 20 lines of arrange = a coupling finding, not a fixture problem.
- Tests are independent and order-free; any test runs alone, in any order.
- The class under test is **real and constructed directly** — never resolved from a context.
- Verify RED once per new behavior.
- No `if`/`for` driving assertions; no `try/catch` standing in for `assertThatThrownBy`.
- **≥ 80% of the branches you wrote are covered** — see *Coverage floor* below. Assertion quality is still measured by mutation score (**peer** `qa-java:test-quality-check`, PIT).

## Coverage floor — ≥ 80% of the branches you wrote

The tests cover **at least 80% of the branches in the code the change wrote**: every class it created, whole, and the methods it changed in a class that already existed. The scope is the change, never the repo — a legacy module's low number is not the excuse, and the repo-wide number is not the target.

- **Design for every branch; 80% is what gets measured.** Before writing tests, list the branch outcomes in the code you wrote — each `if`/`else` arm, `switch` arm and its `default` (a pattern-matching `switch` with its `case null` too), ternary, short-circuit `&&`/`||`, guard-clause return, `catch`, a loop run zero times and many — and give each a test or a `@ParameterizedTest` row that asserts its effect. The slack under 100% is for branches no honest unit test reaches: the synthetic ones JaCoCo does not filter, and a guard the types already exclude.
- **Only an asserting test counts.** A test that runs a branch without asserting what it did is a **major** finding — it moves the number and catches nothing. The tautology test applies; mutation score is how hollow coverage gets caught.
- **Leave out what the matrix says not to test, by name.** Records and DTOs with no behavior, entities without rules, `@Configuration` classes, Flyway migrations and generated code (MapStruct implementations, Lombok output) stay out of the measured class list, and the report names each one left out. Never reach 80% by lowering the number or by a JaCoCo exclusion over code that has behavior.
- **Measure.** The plan's gate runs this; outside a plan, run it before you report:

  ```kotlin
  // build.gradle.kts — once per project
  plugins { jacoco }
  tasks.jacocoTestReport {
      dependsOn(tasks.test)
      reports { csv.required = true }
  }
  ```

  ```bash
  ./gradlew test jacocoTestReport
  grep -E ',(PlaceOrderHandler|PricingStrategyResolver),' build/reports/jacoco/test/jacocoTestReport.csv
  ```

  Branch coverage is `BRANCH_COVERED ÷ (BRANCH_COVERED + BRANCH_MISSED)` — the CSV's 7th and 6th columns — summed over the changed classes; for a method changed in an existing class, the class's page under `build/reports/jacoco/test/html/` shows its branches. On Maven, `jacoco-maven-plugin` (`prepare-agent` + `report`) writes the same CSV to `target/site/jacoco/jacoco.csv`.
- **Below 80%, write the missing tests.** The report's missed branches are the list.

## What NOT to do

- **`@SpringBootTest` / `@DataJpaTest` / `@WebMvcTest` in this project** — the fence has moved; that's the peer's suite.
- **H2 or any in-memory DB standing in for the real engine** — dialect differences make it a false-negative machine. Real engine, integration lane.
- **Mocking `EntityManager`/`JpaRepository` to "test the repository"** — you'd be asserting Mockito's behavior.
- **`@MockBean`** — it exists to replace a bean *in a context*; if you're using it, you're in the peer's lane.
- **`lenient()` sprinkled to silence strict stubs** — fix the stub.
- **`verify(...)` with `any()` everywhere** — proves the call happened, not that it was right.
- **`isEqualTo` on `BigDecimal`** — see above.
- **`@Disabled` without a linked issue** — quarantine is `qa-java:flaky-test-quarantine`'s process.
- **Testing the framework** — that records have equals, that Jackson serializes, that Spring injects.
- **Reflection to reach a private method** — extract the concept into its own class instead.

## Generation steps

1. **Detect** the Java release, the Boot BOM, the existing test source set, and the runner/doubles already in use — **the repo's choice wins** over this file's defaults.
2. **Identify the units** from the selection matrix — for each type `pattern-writer`/`database-code` just produced, decide test / no-test, and say why for the no-tests. For each tested unit, **list its branch outcomes**: that list is the test plan (*Coverage floor*).
3. **Fix the seams first** — a direct `Instant.now()`, `UUID.randomUUID()`, `@Value`, or outbound call is a `pattern-writer`-shaped edit to production code, done before the test.
4. **Write the failing test** (behavior name, AAA, one logical assertion), watch it fail for the right reason (the run a `Gate: own tests` task may make), make it pass.
5. **Add the boundary cases** as `@ParameterizedTest` rows — nulls, empties, min/max, the rounding boundary, the refused transition.
6. **Verify:** `./gradlew test` green, no `UnnecessaryStubbingException`, compiler warning-clean, branch coverage of the changed code ≥ 80% (*Coverage floor*). Report counts and the coverage figure. Inside a plan task, `Gate: none` runs nothing and reports "written, not run"; `Gate: own tests` runs this task's tests — step 4's red run, then green — and the *Coverage floor* measure over the files it wrote, and nothing else.
7. **Sweep:** a strategy family with one tested member is a gap.

## Handoffs

- Anything that boots a Spring context, contract/integration/E2E → **peer** [`qa-api-java`](../../../../qa/java/agents/qa-api-java.md)
- Real-DB verification, Testcontainers → **peer** `qa/java/skills/db-testing/*`
- Do the tests actually catch faults? → **peer** `qa/java/skills/test-quality-check` (PIT)
- Suite-scale builders / ObjectMother → **peer** `qa/java/skills/test-data-builder`
- Flaky triage / quarantine → **peer** `qa/reporting/java/skills/flaky-test-quarantine`
- The class needs a seam / a pattern → [`pattern-writer`](../pattern-writer/SKILL.md)
- Reviewing the tests with the change → [`code-review`](../code-review/SKILL.md)
- .NET equivalent → `backend/dotnet/skills/unit-testing` · TypeScript equivalent → `backend/node/skills/unit-testing`
