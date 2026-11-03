---
name: db-testcontainers
description: Use when scaffolding Java integration tests on a real database via Testcontainers. Triggers "spin up Postgres for these tests". Not for an existing DB (db-connection).
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
- Performance against the DB → `qa/java/skills/load-testing`
- SQL safety review → `qa/java/skills/db-testing/verification-queries`

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

The standards a Testcontainers fixture must meet are the qa-java rule files, not a list here: `qa-java-data.md`, `qa-java-suite.md` (TestNG parallelism) and `qa-java.md` (core). Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- One container per JVM through a `static final` field; fixtures inherit a base that injects through `@DynamicPropertySource`. Parallel classes get one container each in `@BeforeClass`, and prove their isolation.
- Pin the image (`postgres:17.2`) and record the production version beside it.
- Flyway or Liquibase runs once at context start-up; the test profile sets `ddl-auto: validate` or `none`.
- Row reset: db-rider `@DataSet(cleanBefore = true)` per test by default; Spring `@Sql(scripts = "cleanup.sql", executionPhase = AFTER_TEST_METHOD)` for trivial cleanups; drop Mongo collections in `@AfterMethod`.
- On failure, attach the container logs to Allure (`POSTGRES.getLogs()` through `Allure.attachment`, allure-java 3) from a TestNG `IInvokedMethodListener`.

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

- **`qa/java/skills/db-testing/verification-queries`** — SQL guardrails for assertion queries.
- **`qa/java/skills/test-data-builder`** — builders / ObjectMother for seed data.
- **`qa/cicd/java/skills/ci-pipelines`** — DinD enablement and Allure publish.
- **`qa/reporting/java/skills/test-reports`** — attach container logs on failure.
