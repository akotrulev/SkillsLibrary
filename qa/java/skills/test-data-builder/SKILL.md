---
name: test-data-builder
description: Use when the user asks to create test data builders or ObjectMothers in a Java 21 test project (TestNG primary, JUnit 5 OK) to replace duplicated inline literals across tests with named, intention-revealing factories. Triggers: "create a builder for User in Java", "set up test data for X in Gradle TestNG", "extract this fixture into an OrderBuilder". Do NOT use for driving one test from an external data file (`qa-java:data-driven-testing`).
---

# QA — Test Data Builder / ObjectMother (Java 21)

Eliminates repeated inline test data literals in Java 21 test projects (Gradle Kotlin DSL + TestNG primary) by generating Lombok-record builders and ObjectMother static factories. Required by `CLAUDE.md`: "Builder pattern for test data objects with 4+ fields" and "Test data via builders or ObjectMother, not inline literals duplicated across tests."

## When to use

- Two or more tests construct the "same" object with slightly different fields → extract a builder
- One test sets 6 fields just to test one behavior → extract a builder that defaults the other 5
- A complex aggregate (Order → Lines → Customer → Address) needs assembling for many tests
- Reading a test is hard because half the body is data setup
- API tests need a known-shape DTO with one varying field per scenario

## When NOT to use

- .NET test data → `qa/dotnet/skills/test-data-builder`
- TypeScript test data → `qa/typescript/skills/test-data-builder`
- Production-code builders → the `backend/java` dev stack's generator, if installed
- Test data for performance scenarios (volume) → `qa/java/skills/load-testing`
- One-off fixture used by a single test → inline is fine; only extract on duplication

## Builder vs ObjectMother

| Pattern | When to choose |
|---|---|
| **Builder** (`TestOrder.builder()`) | Many fields, many variations, fluent assembly reads naturally |
| **ObjectMother** (`Orders.paid()`) | A few **named, canonical** instances with no per-test variation |
| **Both together** | Mother returns a pre-configured builder; tests refine via setters then call `.build()` |

If `TestOrder.builder().build()` with no chained calls covers 90% of cases → ObjectMother is what you actually want.

## Layout

```
src/test/java/com/example/orders/
├── builders/
│   ├── TestOrder.java
│   ├── TestCustomer.java
│   └── TestOrderLine.java
└── mothers/
    ├── Orders.java
    └── Customers.java
```

`builders/` and `mothers/` live under `src/test/java/`, never in `src/main/java/`. The test-only types are prefixed `Test*` to make leakage into production code obvious in code review.

## Lombok-record builder template

```java
package com.example.orders.builders;

import lombok.Builder;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Builder(toBuilder = true)
public record TestOrder(
    String id,
    String customerId,
    String status,
    long totalMinor,
    String currency,
    Instant placedAt,
    List<TestOrderLine> lines
) {
    public static TestOrderBuilder pending() {
        return TestOrder.builder()
            .id(UUID.randomUUID().toString())
            .customerId(TestCustomers.ALICE_ID)
            .status("PENDING")
            .totalMinor(9_999L)
            .currency("EUR")
            .placedAt(Instant.parse("2026-01-01T12:00:00Z"))
            .lines(List.of(TestOrderLine.builder().sku("A").qty(1).priceMinor(9_999L).build()));
    }

    public static TestOrderBuilder paid() {
        return pending().status("PAID");
    }
}
```

Lombok `@Builder` on a record generates the fluent setter API for free. Static factory methods are the ObjectMother layer (or you can keep them in a separate `Orders` class — see below).

### Build setup (Gradle Kotlin DSL)

```kotlin
dependencies {
    compileOnly("org.projectlombok:lombok:1.18.32")
    annotationProcessor("org.projectlombok:lombok:1.18.32")
    testCompileOnly("org.projectlombok:lombok:1.18.32")
    testAnnotationProcessor("org.projectlombok:lombok:1.18.32")
}
```

## ObjectMother on top (separate class)

```java
package com.example.orders.mothers;

import com.example.orders.builders.TestOrder;

public final class Orders {
    private Orders() {}

    public static TestOrder.TestOrderBuilder pending()   { return TestOrder.pending(); }
    public static TestOrder.TestOrderBuilder paid()      { return TestOrder.paid(); }
    public static TestOrder                  refunded() { return TestOrder.pending().status("REFUNDED").build(); }
}
```

## Usage in TestNG

```java
@Test
public void cancellingPendingOrderSucceeds() {
    TestOrder order = Orders.pending().build();
    // arrange / act / assert
}

@Test
public void cancellingPaidOrderRefundsToCard() {
    TestOrder order = Orders.paid().totalMinor(15_000L).build();
    // ...
}
```

Same shape works under JUnit 5; the runner doesn't care.

## Conventions

- **Sensible default for every field** — a test never has to know about fields it doesn't care about.
- **Setter names follow Lombok** (`status(...)`, `totalMinor(...)`); the readable side comes from the static factory names (`Orders.paid()`).
- **`.build()` is the only terminal** and returns an immutable record.
- **Records** for produced test types.
- **`Test*` prefix** on every test-only type to make accidental leakage to production code visible in PRs.
- **`final` ObjectMother classes** with private constructors and `static` methods — never instantiate a mother.
- **AssertJ** (`assertThat(...)`) is preferred when writing follow-on assertions on built objects.

## Random vs deterministic data

- **Default to deterministic literal defaults** (`"cus_alice"`, `Instant.parse("2026-01-01T12:00:00Z")`).
- Use `DataFaker` (`net.datafaker:datafaker`) **only** when uniqueness matters per test (ids) and any value is acceptable.
- Seed DataFaker deterministically per test run (`new Faker(new Random(42))`) when randomness touches assertions.
- **Never** assert on a random field — assert on the field you set; defaults are scaffolding.

## Aggregate / child relationships

```java
TestCustomer customer = Customers.alice().build();
TestOrder order = Orders.paid()
    .customerId(customer.id())
    .lines(List.of(
        TestOrderLine.builder().sku("B").qty(2).priceMinor(5_000L).build()
    ))
    .build();
```

- For incremental list building, expose a helper like `addLine(...)` via a custom static method on the builder, or build the list outside and pass it in.
- Use `List.of(...)` / `List.copyOf(...)` — never expose internal `ArrayList` references.

## Persistence-aware builders

Separate **shape building** from **persistence**:

```java
// Shape only — pure.
TestOrder order = Orders.pending().build();

// Persistence — through the same client production uses.
OrderDto created = ordersClient.create(toDto(order), 201);
```

Don't build "an order in the DB" inside the builder — that couples the builder to a particular persistence path and hides the API call dependency. Persistence is the test's job; the builder is shape.

## Rules

- Builders live under `src/test/java/.../builders/`; ObjectMothers under `src/test/java/.../mothers/`.
- Every field has a sensible default — adding a non-nullable field doesn't ripple through 50 tests.
- One builder per aggregate; child aggregates have their own builders.
- Defaults are deterministic literals; only id-like fields use random with reason (seeded DataFaker).
- `.build()` returns the real record / domain type, never the builder.
- `.build()` is idempotent — calling it twice produces equal but independent instances.
- ObjectMother helpers return a builder (so tests can refine); return a built object only when no test ever varies it.
- Tests never construct domain objects with raw `new SomeRecord(...)` literals across more than 1–2 places — extract to a builder.
- Constructor injection only — builders never use a service locator.
- No async / `CompletableFuture` in the builder; building is pure.
- Lombok `@Builder` on records is the default; only switch to a hand-written builder when generic type bounds defeat Lombok.

## What NOT to do

- No inline test data literals duplicated across test files.
- No `null` for required fields in defaults — pick a real default.
- No randomness on fields the test asserts against.
- No "god builder" with 30 chained methods covering 4 unrelated aggregates — split per aggregate.
- No persistence in the builder — shape and save are separate concerns.
- No production-code builders disguised as test builders ("we'll reuse this in prod too") — separate them; remove `Test*` prefix only when promoting deliberately.
- No exposing `ArrayList`/mutable collections through getters — `List.copyOf` in `.build()`.
- No defaults that violate domain invariants (e.g. negative `totalMinor`) — the default builder must produce a valid object.
- No mixing `@Builder` with hand-written setters in the same record — pick one.
- No AutoFixture-style "build me anything" reflection libraries on top of these builders — predictability matters.
- No builders that throw checked exceptions from `.build()` — the default path must compile cleanly.

## Generation steps

1. Grep the test tree for repeated literal patterns (`new Order(`, `new User(`, repeated map/list builders for request bodies).
2. Per aggregate, list the fields, the sensible defaults, and the variant-producing helpers (`pending`/`paid`/`cancelled` etc.).
3. Generate the record + `@Builder` under `src/test/java/.../builders/` following the template.
4. Add a `final` ObjectMother class under `mothers/` with the canonical variants.
5. Replace inline literals in 2–3 representative tests so the pattern is set; leave the rest as a follow-up sweep.
6. Run `./gradlew test` — every test still passes with the new defaults. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Handoffs

- .NET test data → `qa/dotnet/skills/test-data-builder`
- TypeScript test data → `qa/typescript/skills/test-data-builder`
- API tests where these feed into request bodies → `qa/java/skills/api-test-author/writer`
- UI tests where they back form-fill helpers → `qa/java/skills/ui-test-author/playwright` / `qa/java/skills/ui-test-author/selenium` / `qa/java/skills/ui-test-author/appium`
- Test reviewers (verify builders used, not literals) → `qa/java/skills/api-test-author/review` / `qa/java/skills/ui-test-author/review`
- Test strategy / pyramid → `qa/manual/test-strategy`
- Production-code builders → the `backend/java` dev stack's generator, if installed
