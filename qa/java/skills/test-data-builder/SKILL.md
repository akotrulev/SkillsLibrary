---
name: test-data-builder
description: Use when creating test data builders/ObjectMothers in a Java test project to replace duplicated literals. Triggers "create a builder for User". Not for row data files (data-driven-testing).
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

## Production-shaped data and PII

- **Never copy production rows** into a builder default, a seed script, a fixture file or a test asset. A
  dump, an export or a pasted record is personal data the moment it lands in the repo, a CI log or a report.
- **Defaults are obviously synthetic but realistic**: a valid format and a plausible length, so validation and
  layout are exercised, and nobody owns the value — `Mira Kovac`, `mira.kovac@example.com`,
  `+44 7700 900123`. Reserved names only: `example.com` / `.test` domains (RFC 2606), Ofcom's
  `07700 900000–900999` drama range or the US `555-0100–0199` range. Never `test@test.com`, `foo` or
  `John Doe`: they hide the formats the field really accepts.
- **When a test needs production shape** (real distributions, edge-case values, volume), mask a copy outside
  the repo with a **deterministic pseudonymiser**: one keyed hash per field class, so a real value always maps
  to the same fake one. Referential integrity survives — a customer id masked in `customers` and in `orders`
  still joins — and a rerun rebuilds the same dataset. The key comes from the secret store, never the repo;
  without it the mapping cannot be rebuilt by hashing a phone book.

| Field class | Masked as |
|---|---|
| Email | `user.<token>@example.com` |
| Phone | a number in the fictional range, picked by the hash |
| Name, address | a faker seeded from the hash |
| Ids, account numbers | a prefix plus the token, same length and format where the API validates it |
| Free text (notes, comments) | replaced whole — it carries PII no pattern finds |
| Date of birth | shifted by a hash-derived number of days, same age band |

```java
public final class Pseudonymizer {
    private static final HexFormat HEX = HexFormat.of();
    private final Mac mac;

    public Pseudonymizer(byte[] key) throws GeneralSecurityException {
        mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
    }

    public String email(String real) { return "user." + token(real, "email") + "@example.com"; }
    public String phone(String real) { return "+44 7700 900%03d".formatted(number(real, "phone", 1000)); }
    public String fullName(String real) { return seeded(real, "name").name().fullName(); }
    public String streetAddress(String real) { return seeded(real, "address").address().streetAddress(); }
    public String customerId(String real) { return "cus_" + token(real, "customer"); }

    private Faker seeded(String real, String fieldClass) {
        return new Faker(new Random(number(real, fieldClass, Integer.MAX_VALUE)));
    }

    private String token(String real, String fieldClass) { return HEX.formatHex(hash(real, fieldClass), 0, 6); }

    private int number(String real, String fieldClass, int bound) {
        return Math.floorMod(ByteBuffer.wrap(hash(real, fieldClass)).getInt(), bound);
    }

    private byte[] hash(String real, String fieldClass) {
        return mac.doFinal((fieldClass + ":" + real).getBytes(StandardCharsets.UTF_8));
    }
}
```

`Mac` is not thread-safe: one `Pseudonymizer` per masking thread. `Faker` is DataFaker's `net.datafaker.Faker`.

Mask every column that identifies a person on its own or combined (postcode + date of birth + gender); amounts,
enums and timestamps that carry no identity stay as they are. Before the set is used, grep it for the source's
email domains and phone prefixes — a hit fails the masking job.

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

The standards a builder must meet are the qa-java rule files, not a list here: `qa-java-data.md` and `qa-java.md` (core). Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- Builders live under `src/test/java/.../builders/`, ObjectMothers under `src/test/java/.../mothers/`; child aggregates have their own builders.
- Lombok `@Builder` on records is the default; a hand-written builder only where generic type bounds defeat Lombok, and never `@Builder` mixed with hand-written setters in one record.
- A test builder is not a production builder: promote one deliberately, dropping the `Test*` prefix, never by reuse.

## Generation steps

1. Grep the test tree for repeated literal patterns (`new Order(`, `new User(`, repeated map/list builders for request bodies).
2. Per aggregate, list the fields, the sensible defaults, and the variant-producing helpers (`pending`/`paid`/`cancelled` etc.).
3. Generate the record + `@Builder` under `src/test/java/.../builders/` following the template.
4. Add a `final` ObjectMother class under `mothers/` with the canonical variants.
5. Replace inline literals in 2–3 representative tests so the pattern is set; leave the rest as a follow-up sweep.
6. Run `./gradlew test` — every test still passes with the new defaults.

## Handoffs

- .NET test data → `qa/dotnet/skills/test-data-builder`
- TypeScript test data → `qa/typescript/skills/test-data-builder`
- API tests where these feed into request bodies → `qa/java/skills/api-test-author/writer`
- UI tests where they back form-fill helpers → `qa/java/skills/ui-test-author/playwright` / `qa/java/skills/ui-test-author/selenium` / `qa/java/skills/ui-test-author/appium`
- Test reviewers (verify builders used, not literals) → `qa/java/skills/api-test-author/review` / `qa/java/skills/ui-test-author/review`
- Test strategy / pyramid → `qa/manual/test-strategy`
- Production-code builders → the `backend/java` dev stack's generator, if installed
