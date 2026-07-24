---
name: qa-db-testing-testcontainers-java
description: Use when the user asks to scaffold Java 21 + Spring Boot 3 + TestNG (or JUnit 5) integration tests backed by a real database (Postgres / SQL Server / MongoDB / Redis) via Testcontainers-Java. Triggers: "spin up Postgres for the integration tests", "Testcontainers for the Spring Boot tests", "stop using H2 in tests". For end-to-end suite work prefer the phased agent `qa-api-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — DB Testing with Testcontainers (Java)

Scaffolds TestNG fixtures (per CLAUDE.md default) or JUnit 5 classes that boot a real database container per suite, run Flyway / Liquibase migrations once, and clean rows between tests. Uses Spring Boot 3 `@DynamicPropertySource` to inject the container's connection details into the SUT.

## When to use

- New `src/test/java/.../integration/{Feature}IT.java` that hits a real DB
- Replacing H2 / in-memory DBs with the production engine
- Spring Boot integration tests asserting DB side-effects
- Cross-version checks (Postgres 16 vs 17)

## When NOT to use

- Unit tests with no SQL surface
- Non-JVM stacks — see siblings
- Performance against the DB → `qa/java/skills/performance/gatling`
- SQL safety review → `qa/java/skills/db-testing/query-author`

## Inputs needed

1. Engine? (Postgres default; SQL Server / Mongo / Redis on request)
2. Schema source: Flyway, Liquibase, or Spring's `schema.sql` / `data.sql`?

Infer the rest: Gradle Kotlin DSL (per CLAUDE.md), TestNG (per CLAUDE.md), Spring Boot 3.x.

## Decision matrix

| Question | Default | Override when |
|---|---|---|
| Container scope | **Per suite** (`@Suite` shared static) | Per class only if state can't be cleaned |
| Image tag | **Pinned** (`postgres:17.2`) | Never `latest` |
| Schema lifecycle | **Migrate once** via Flyway at suite init | Per test only for migration rollback tests |
| Row reset | **db-rider `@DataSet(cleanBefore=true)`** or Spring `@Sql` script | Transactional rollback when test is single-thread non-HTTP |
| Connection injection | `@DynamicPropertySource` into Spring `Environment` | Never hardcoded |
| Parallelism | TestNG `parallel="false"` for integration | Higher only with one container per class + proven isolation |

## Templates

### Gradle additions — `build.gradle.kts`

```kotlin
dependencies {
    testImplementation(platform("org.testcontainers:testcontainers-bom:1.20.4"))
    testImplementation("org.testcontainers:testcontainers")
    testImplementation("org.testcontainers:postgresql")
    testImplementation("org.testcontainers:testng")
    testImplementation("org.springframework.boot:spring-boot-starter-test") {
        exclude(group = "org.junit.jupiter")
    }
    testImplementation("org.testng:testng:7.10.2")
    testImplementation("com.github.database-rider:rider-spring:1.44.0")
    testImplementation("org.flywaydb:flyway-core")
    testImplementation("org.flywaydb:flyway-database-postgresql")
}

tasks.named<Test>("test") {
    useTestNG {
        parallel = "false"
    }
}
```

### Suite-shared container — `src/test/java/.../support/PostgresSupport.java`

```java
package com.flexinvest.support;

import org.testcontainers.containers.PostgreSQLContainer;

public final class PostgresSupport {

    public static final PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:17.2")
            .withDatabaseName("appdb")
            .withUsername("test")
            .withPassword("test");

    static {
        POSTGRES.start();
        Runtime.getRuntime().addShutdownHook(new Thread(POSTGRES::stop));
    }

    private PostgresSupport() {}
}
```

A `static` singleton is the Java idiom for "one container per JVM" — Testcontainers' Ryuk container cleans it on JVM exit; the shutdown hook accelerates teardown in CI.

### Spring Boot integration test base — `IntegrationTestBase.java`

```java
package com.flexinvest.support;

import com.github.database.rider.spring.api.DBRider;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.testng.AbstractTestNGSpringContextTests;

@DBRider
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public abstract class IntegrationTestBase extends AbstractTestNGSpringContextTests {

    @DynamicPropertySource
    static void registerDatasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", PostgresSupport.POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", PostgresSupport.POSTGRES::getUsername);
        registry.add("spring.datasource.password", PostgresSupport.POSTGRES::getPassword);
        registry.add("spring.flyway.enabled", () -> "true");
    }
}
```

### Concrete test — `TransactionsIT.java`

```java
package com.flexinvest.transactions;

import com.flexinvest.support.IntegrationTestBase;
import com.github.database.rider.core.api.dataset.DataSet;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;

public class TransactionsIT extends IntegrationTestBase {

    @Autowired
    private TestRestTemplate http;

    @Autowired
    private TransactionRepository repo;

    @Test
    @DataSet(value = "datasets/empty.yml", cleanBefore = true)
    public void should_persist_transaction_when_post_returns_created() {
        var body = new CreateTransactionRequest(1250L, "EUR");

        ResponseEntity<Void> response = http.postForEntity("/transactions", body, Void.class);

        assertEquals(response.getStatusCode(), HttpStatus.CREATED);
        assertEquals(repo.count(), 1L);
    }
}
```

### SQL Server variant

```java
public static final MSSQLServerContainer<?> MSSQL =
    new MSSQLServerContainer<>("mcr.microsoft.com/mssql/server:2022-CU14-ubuntu-22.04")
        .acceptLicense();
```

### MongoDB

```java
public static final MongoDBContainer MONGO = new MongoDBContainer("mongo:7.0");

@DynamicPropertySource
static void mongoProps(DynamicPropertyRegistry registry) {
    registry.add("spring.data.mongodb.uri", MONGO::getReplicaSetUrl);
}

// Per-test cleanup: drop all collections.
@AfterMethod
public void clearMongo(MongoTemplate template) {
    template.getDb().listCollectionNames().forEach(template::dropCollection);
}
```

### Custom wait strategy (generic container only)

```java
new GenericContainer<>("ghcr.io/myco/legacy-app:1.4.0")
    .withExposedPorts(8080)
    .waitingFor(Wait.forHttp("/health").forPort(8080).forStatusCode(200));
```

**Never** `Thread.sleep` — every module ships a correct wait strategy.

## Rules

### Fixture structure
- One container per JVM via `static final` field. Test fixtures inherit a base that injects via `@DynamicPropertySource`.
- Per-test reset via `@DataSet(cleanBefore = true)` (db-rider) is the default; `@Sql` scripts are fine for simple cases.
- Never use Spring's `@Transactional` rollback for HTTP integration tests — the SUT's TX runs in a separate connection from the test thread.

### Image pinning
- Specific tags only (`postgres:17.2`). Document production version in a comment.

### Schema lifecycle
- Flyway / Liquibase runs once at Spring context startup. Disable JPA `ddl-auto: validate` (or `none`) in the test profile — schema comes from migrations.
- Never `hibernate.hbm2ddl.auto=create-drop` in integration tests.

### Row reset
- Default: db-rider `@DataSet(cleanBefore=true)` per test. Faster and FK-safe.
- Spring `@Sql(scripts="cleanup.sql", executionPhase=AFTER_TEST_METHOD)` for trivial cleanups.
- For Mongo, drop collections in `@AfterMethod`.

### Connection injection
- `@DynamicPropertySource` only. No `application-test.yml` with hardcoded URLs.
- Never log the JDBC URL (secrets policy).

### Parallelism
- TestNG `parallel="false"` at the suite level for integration tests. Containers are expensive.
- If parallelising: one container per class via `@BeforeClass` (no shared static), and prove isolation.

### Diagnostics
- On failure, attach container logs to the report: `POSTGRES.getLogs()` → Allure via `Allure.addAttachment(...)` in a TestNG `IInvokedMethodListener`.

### What NOT to do
- No `Thread.sleep` — use the module's wait strategy.
- No `latest` image tags.
- No hardcoded JDBC URLs — always via `@DynamicPropertySource`.
- No H2 mixed with Testcontainers in the same suite.
- No `hbm2ddl.auto=create` — drift from production schema.
- No connection strings in log lines.
- No starting a container in `@BeforeMethod` — that's per-test container; use static or `@BeforeClass`.

## Generation steps

1. Read existing `src/test/java/.../integration` for base-class and naming conventions.
2. Confirm migration tool (Flyway / Liquibase) and migration scripts location.
3. Generate:
   - `support/PostgresSupport.java` (or sibling for other engines)
   - `support/IntegrationTestBase.java`
   - `support/datasets/empty.yml` (db-rider seed reset)
   - Concrete `{Feature}IT.java`
   - `build.gradle.kts` dependency additions.
4. Run `./gradlew test --tests "*IT"` — expect green or real assertion failure.

## Cross-references

- **`qa/java/skills/db-testing/query-author`** — SQL guardrails for assertion queries.
- **`qa/java/skills/test-data-builder`** — builders / ObjectMother for seed data.
- **`qa/cicd/java/skills/ci-pipelines`** — DinD enablement and Allure publish.
- **`qa/reporting/java/skills/allure-reporting`** — attach container logs on failure.
