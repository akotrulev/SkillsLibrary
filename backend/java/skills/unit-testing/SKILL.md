---
name: unit-testing
description: Use when Java backend logic needs a unit test with JUnit 5 + Mockito, no Spring context (seams, fakes, coverage floor). Triggers "unit-test this service". Not for HTTP tests (api-tests).
disable-model-invocation: true
---

# Java — Unit Testing (JUnit 5 + Mockito + AssertJ)

Owns **dev-side unit tests of backend logic**: construct a class with `new`, drive it, assert on its return value or its observable effect on a fake collaborator. **No Spring context, no container, no real database, no broker, no filesystem, no clock.**

**The boundary:** if the test needs **any** annotation that starts an application context — `@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest`, `@JsonTest`, `@ExtendWith(SpringExtension.class)` — it is not a unit test and it belongs to the **peer** [`qa-api-java`](../../../../qa/java/agents/qa-api-java.md).

**A slice test is fast, not isolated**: it reads `application.yml`, builds a context, and fails for reasons unrelated to your logic. `@ExtendWith(MockitoExtension.class)` is this skill's extension; `SpringExtension` is the peer's.

**Runner — house-default deviation, stated once.** `CLAUDE.md`'s Java test-runner default is **TestNG**, correct for the **QA suite**. Dev-side unit tests use **JUnit 5**: `spring-boot-starter-test` ships JUnit 5 + Mockito + AssertJ as one managed dependency, and a second runner in a Boot service buys nothing. **Use JUnit 5 here; if the service already standardizes on TestNG, match it.**

**This skill is not a licence to replace integration tests with mocks.** Some things are only provable against a real dependency:

| Never unit-test this | Because | Belongs to |
|---|---|---|
| A Spring Data repository, `@Query`, a Criteria/Specification build | JPQL/SQL validity and the generated SQL are the thing under test | `qa-api-java` `db-testing/testcontainers` |
| Entity mappings, `@OneToMany` fetch behavior, lazy-loading, N+1 | Only a real `EntityManager` + DB shows the queries | `qa-api-java`, `data-architect` |
| `@Transactional` boundaries, propagation, rollback-on-exception | The proxy + a real tx manager are the mechanism | `qa-api-java` |
| A Flyway migration | Only a real engine proves it applies | `qa-api-java` + `data-architect` |
| The security filter chain, JWT decoding, `@PreAuthorize` end-to-end | The filter chain is the thing under test | `qa-api-java` `test-login-tokens`, `qa-security` |
| Request mapping, content negotiation, `@Valid` triggering at the boundary | Transport concerns | `qa-api-java` |

## Version policy

The lane per `CLAUDE.md` 'Version policy'. Let the Boot BOM manage JUnit/Mockito/AssertJ versions — **do not pin them independently**; a hand-pinned Mockito against a Boot-managed JUnit is the most common break in this lane.

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
| Doubles | **Mockito** | `mockito-junit-jupiter` for the extension; Mockito 5's inline maker can mock `final` types, which does not make it a good idea (traps) |
| Assertions | **AssertJ** (`assertThat`) | House choice — one entry point, best `BigDecimal`/collection support |
| Time | **`java.time.Clock`** | JDK-native; no dependency |
| Validation | `jakarta.validation` + Hibernate Validator | Build a `Validator` directly — no Spring |

Using `spring-boot-starter-test` is fine; its context-starting annotations are not — a review point.

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

Match the repo first. Mirror the main source tree:

```
src/main/java/com/acme/ordering/PlaceOrderService.java
src/test/java/com/acme/ordering/PlaceOrderServiceTest.java     # this skill
src/test/java/com/acme/ordering/fakes/InMemoryOrderRepository.java
src/test/java/com/acme/ordering/builders/OrderBuilder.java
```

- **One test class per class under test**, same package, named `<ClassName>Test`. `<ClassName>IT` is the peer's, in a separate source set so `test` stays fast.
- **No field injection into the class under test.** Construct it with `new` in `@BeforeEach` (or in the test). `@InjectMocks` is discouraged here: it fills fields reflectively, so a constructor-signature change compiles and silently leaves a `null` — the exact failure constructor injection exists to prevent.
- **No shared mutable state between tests**: no `static` fields, no `@TestInstance(PER_CLASS)` plus mutation.

## Naming

`should_<Outcome>_when_<Condition>` (or the repo's existing convention), optionally with `@DisplayName`. The name states behavior (`should_CallRepository` asserts a mechanism):

```java
@Test
@DisplayName("rejects the order when the cart is empty")
void should_RejectOrder_when_CartIsEmpty() { … }
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

A fixed-clock test and validation without Spring → read `references/seam-examples.md`.

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

**Prefer a state assertion over a `verify()`** where both work: a fake's recorded state survives a refactor that `verify(...)` does not.

### Mockito traps

- **`MockitoExtension` is STRICT_STUBS by default** — an unused `when(...)` fails with `UnnecessaryStubbingException` because the stub describes a call that no longer happens. Delete the stub.
- **Mocking `final` / static** — Mockito 5's inline maker makes it possible; it's still a design smell. `mockStatic` over your own static helper means the helper should be an injected collaborator.
- **Don't `verify()` the logger** — logs aren't the contract, unless the class's only job is producing an audit record.
- **`any()` hides the contract** — use `argThat` / an `ArgumentCaptor` and assert the payload.
- **Never `spy()` the class under test** — that's two responsibilities in one class. Split it.

## Parameterized tests

Jupiter's data sources replace `if`/`for` around assertions:

```java
@ParameterizedTest
@CsvSource({ "0.005, 0.01", "0.004, 0.00", "-0.005, -0.01" })
void should_RoundHalfUp_when_ThirdDecimalPresent(BigDecimal input, BigDecimal expected) {
    assertThat(Money.round(input)).isEqualByComparingTo(expected);
}
```

`@MethodSource` for constructed cases, `@EnumSource` for exhausting an enum (it fails when someone adds a constant), `@ValueSource` for single values.

## Beyond example tests

- [`references/snapshot-testing.md`](references/snapshot-testing.md) — a large output's whole shape is the contract (ApprovalTests).

## `BigDecimal` — the Java-specific trap

**`assertThat(x).isEqualTo(y)` on `BigDecimal` compares scale too**: `2.50` is *not* equal to `2.5`. Use **`isEqualByComparingTo`** unless the scale itself is the contract — and when it is, assert it explicitly:

```java
assertThat(total).isEqualByComparingTo("2.5");        // value
assertThat(total.scale()).isEqualTo(2);               // scale, when it's part of the contract
```

Money: minor units or `BigDecimal` with an explicit `RoundingMode`, never `double`; assert the rounding at the boundary (`.005`).

## Test data

- 1–3 fields: inline literals, named constants when the value carries meaning.
- **4+ fields: a builder** with sane defaults, so a test overrides only its subject:

```java
var order = anOrder().withStatus(SHIPPED).build();
```

- Suite-scale data → **peer** `qa-java:test-data-builder`.

## Async & concurrency

- `assertThatThrownBy(() -> …).isInstanceOf(X.class)` for expected failures; assert the **type**, not the message.
- `CompletableFuture`: assert on `join()`/`get()` of an already-completed future, or use `assertThat(future).succeedsWithin(Duration.ofMillis(100))` (AssertJ). **No `Thread.sleep`.**
- A unit test shouldn't need concurrency; if it does, the concurrency is the subject and belongs to the peer's lane with a real executor. **Awaitility belongs there too**: a unit that needs polling is waiting on real I/O.

## Rules

The standards a test must meet are the be-java rule file `java-tests.md`, not a list here. Read the project's copy in `.claude/rules/be-java/`, or the plugin's in `backend/java/skills/rules/` when the project has not installed them (`/be-java:rules` does). Where it and this skill disagree, the rule file wins. The coverage floor below is how its 80% rule is measured.

## Coverage floor — ≥ 80% of the branches you wrote

The tests cover **at least 80% of the branches in the code the change wrote**: every class it created, whole, and the methods it changed in a class that already existed. The scope is the change, never the repo — a legacy module's low number is not the excuse, and the repo-wide number is not the target.

- **Design for every branch; 80% is what gets measured.** Before writing tests, list the branch outcomes in the code you wrote — each `if`/`else` arm, `switch` arm and its `default` (a pattern-matching `switch` with its `case null` too), ternary, short-circuit `&&`/`||`, guard-clause return, `catch`, a loop run zero times and many — and give each a test or a `@ParameterizedTest` row that asserts its effect. The slack under 100% is for branches no honest unit test reaches: the synthetic ones JaCoCo does not filter, and a guard the types already exclude.
- **Only an asserting test counts.** A test that runs a branch without asserting what it did is a **major** finding; mutation score catches hollow coverage.
- **Leave out what the matrix says not to test, by name.** Records and DTOs with no behavior, entities without rules, `@Configuration` classes, Flyway migrations and generated code (MapStruct implementations, Lombok output) stay out of the measured class list, and the report names each one left out. Never reach 80% by lowering the number or by a JaCoCo exclusion over code that has behavior.
- **Measure.** Inside a plan task, the `Gate:` line runs this over the files the task and the landed tasks above it touched. Outside a plan, run it before you report:

  The JaCoCo setup, the CSV command and the branch formula → read `references/jacoco-coverage.md`.
- **Below 80%, write the missing tests.** The report's missed branches are the list.

## Generation steps

1. **Detect** the Java release, the Boot BOM, the existing test source set, and the runner/doubles already in use — **the repo's choice wins** over this file's defaults.
2. **Identify the units** from the selection matrix — for each type `pattern-writer`/`database-code` just produced, decide test / no-test, and say why for the no-tests. For each tested unit, **list its branch outcomes**: that list is the test plan (*Coverage floor*).
3. **Fix the seams first** — a direct `Instant.now()`, `UUID.randomUUID()`, `@Value`, or outbound call is a `pattern-writer`-shaped edit to production code, done before the test.
4. **Write the failing test** (behavior name, AAA, one logical assertion), watch it fail for the right reason (the run a `Gate: own tests` task may make), make it pass.
5. **Add the boundary cases** as `@ParameterizedTest` rows — nulls, empties, min/max, the rounding boundary, the refused transition.
6. **Verify:** `./gradlew test` green, no `UnnecessaryStubbingException`, compiler warning-clean, branch coverage of the changed code ≥ 80% (*Coverage floor*). Report counts and the coverage figure. Inside a plan task, `Gate: own tests` runs this task's tests — step 4's red run, then green —, the tests of the landed tasks above it, and the *Coverage floor* measure over the files the task and those tasks touched; the last runnable task runs everything else.
7. **Sweep:** a strategy family with one tested member is a gap.
