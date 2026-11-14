---
name: distributed-app-testing
description: Use when a Java/TestNG suite must boot the whole multi-service system and its dependencies (compose, Testcontainers). Triggers "test the services together". Not for one service (db-testcontainers).
---

# QA — Distributed App Testing (Testcontainers + TestNG, Java 21)

Scaffolds TestNG fixtures that boot the **whole system** — every service, worker and dependency the compose file
declares — once per suite with Testcontainers `ComposeContainer`, wait until each service is healthy, resolve each
service's URL from the running containers, and drive the system over HTTP with a `traceparent` on every request.

**The fence.** This is a **process-boundary test**: each service runs in its own container, so a test cannot swap a
bean or reach a class. It belongs to the `qa-api-java` lane, never to a `be-*` unit-test task. A class's logic is
`be-java` `unit-testing`; one service with its database is `db-testing/testcontainers`, which is lighter and lets
the test replace beans. Reach for this skill when the behaviour spans the services the compose file wires together.

## When to use

- The repo has a compose file (`compose.yaml`, `docker-compose.yml`) that runs the system, and the test must
  exercise two or more of its services together: an API and its worker, an API and the email it sends, a gateway
  and the services behind it.
- The wiring itself is under test: service-to-service URLs, broker topology, health checks.

## When NOT to use

- One service plus its database → `db-testing/testcontainers`
- A unit of logic → `be-java` `unit-testing`
- Broker, blob or email assertions on one service → `messaging-testing`, `file-storage-testing`, `email-testing`
- A deployed environment the suite only calls → the suite's configured base URL, no containers
- Load → `load-testing`; microbenchmarks → `benchmarks`

## Inputs needed

1. The compose file and the service names the journey touches, and which are built from this repo (`build:`).
2. What varies the stack (interpolated variables such as `${PAYMENTS_MODE:-live}`, profiles, override files).

## Version lane

| Dependency | Version | Rule |
|---|---|---|
| Testcontainers in a standalone QA suite | **2.0.5** via `org.testcontainers:testcontainers-bom` (verified on Maven Central, 2026-11) | 2.x module artifacts are `testcontainers-<module>` and their classes live in `org.testcontainers.<module>`; `ComposeContainer` stays in `org.testcontainers.containers` |
| Testcontainers inside a Spring Boot 3.x service repo | **Managed by the Boot BOM** — 1.21.4 on Boot 3.5.16 | Never pin it beside the BOM; moving a Boot 3 project to Testcontainers 2 is an upgrade of its own, never a side effect |
| `org.springframework.boot:spring-boot-testcontainers` | Boot BOM | Only for the in-process mode (§ One Spring service in-process) |

Docker must run on the machine and the CI agent. `new ComposeContainer(File...)` drives the **local**
`docker compose` v2 CLI, so the agent needs the Compose plugin; builds then use the repo's normal build context.

```kotlin
// build.gradle.kts — standalone QA suite
dependencies {
    testImplementation(platform("org.testcontainers:testcontainers-bom:2.0.5"))
    testImplementation("org.testcontainers:testcontainers")
}
```

## Procedure

1. Detect the JDK, TestNG, whether a Boot BOM manages Testcontainers, and the compose services, health checks and
   published ports; match them.
2. Add a `compose.test.yaml` override (below) beside the suite: no published host ports, no named volumes, test
   profiles on.
3. Write one `SystemUnderTest` holder per compose stack from the template. **One stack per suite, started in
   `@BeforeSuite`, stopped in `@AfterSuite(alwaysRun = true)`** — never per class or per test: a stack start builds
   images and boots every container, which takes tens of seconds to minutes.
4. Make each test independent of the others sharing the stack: unique data per test (a builder with a unique email
   or key), never a global wipe of a shared store.
5. Run `./gradlew test --tests "*SystemTest"`; the first run builds and pulls images, so budget the startup timeout
   for it.

## Templates

### Test override — `src/test/resources/compose.test.yaml`

```yaml
services:
  api:
    ports: !reset []
    environment:
      SPRING_PROFILES_ACTIVE: test
  postgres:
    ports: !reset []
    volumes: !reset []
```

Published host ports collide when two CI jobs share a Docker host, and named volumes carry one run's data into the
next. Testcontainers reaches each exposed service on a random host port, so the stack needs no published ports.
`!reset` needs Docker Compose 2.24.4+.

### `SystemUnderTest` — `src/test/java/com/{org}/apitests/system/SystemUnderTest.java`

```java
package com.{org}.apitests.system;

import java.io.File;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.testcontainers.containers.ComposeContainer;
import org.testcontainers.containers.output.Slf4jLogConsumer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testng.annotations.AfterSuite;
import org.testng.annotations.BeforeSuite;

public abstract class SystemUnderTest {
    private static final Logger LOG = LoggerFactory.getLogger(SystemUnderTest.class);
    private static final Duration STARTUP_BUDGET = Duration.ofMinutes(3);
    private static final int API_PORT = 8080;
    private static final int MAILPIT_HTTP_PORT = 8025;
    private static final int POSTGRES_PORT = 5432;

    private static final ComposeContainer SYSTEM = new ComposeContainer(
            new File("../compose.yaml"),
            new File("src/test/resources/compose.test.yaml"))
        .withBuild(true)
        .withEnv("PAYMENTS_MODE", "sandbox")
        .withExposedService("api", API_PORT, Wait.forHttp("/actuator/health").forStatusCode(200))
        .withExposedService("mailpit", MAILPIT_HTTP_PORT, Wait.forHttp("/api/v1/info").forStatusCode(200))
        .withExposedService("postgres", POSTGRES_PORT, Wait.forHealthcheck())
        .waitingFor("worker", Wait.forHealthcheck())
        .withLogConsumer("api", new Slf4jLogConsumer(LOG).withPrefix("api"))
        .withLogConsumer("worker", new Slf4jLogConsumer(LOG).withPrefix("worker"))
        .withStartupTimeout(STARTUP_BUDGET);

    @BeforeSuite(alwaysRun = true)
    public void startSystem() {
        SYSTEM.start();
    }

    @AfterSuite(alwaysRun = true)
    public void stopSystem() {
        SYSTEM.stop();
    }

    protected static String apiBaseUrl() {
        return httpUrl("api", API_PORT);
    }

    protected static String mailpitBaseUrl() {
        return httpUrl("mailpit", MAILPIT_HTTP_PORT);
    }

    protected static String postgresJdbcUrl(String database) {
        return "jdbc:postgresql://" + SYSTEM.getServiceHost("postgres", POSTGRES_PORT) + ":"
            + SYSTEM.getServicePort("postgres", POSTGRES_PORT) + "/" + database;
    }

    private static String httpUrl(String service, int port) {
        return "http://" + SYSTEM.getServiceHost(service, port) + ":" + SYSTEM.getServicePort(service, port);
    }
}
```

- **Wait for healthy, not for started**: an HTTP wait on the health endpoint, or `Wait.forHealthcheck()` on a
  service whose compose entry has a `healthcheck:`. A service the test never calls (the worker) still gets a wait
  through `waitingFor`, or the first test races it.
- **Service names are the compose names**; `"api"` resolves to the first instance (`api-1`).
- **One startup budget** for the whole stack (`withStartupTimeout`); the first run on a clean agent builds and pulls,
  so 3 minutes, not 30 s.
- **`withBuild(true)`** builds this repo's services from the working tree — the code under review, not an old image.
- **Logs stream to the test log** (`Slf4jLogConsumer`, prefixed per service), so a failed run carries every
  service's output. `stop()` removes the volumes by default, and the random project name per `ComposeContainer` keeps
  parallel CI jobs apart.
- **No retry filter on the test's HTTP client** — a retry turns a real 5xx into a pass; the health wait already
  removes the startup race.
- `postgresJdbcUrl` is for seeding or verifying rows (`db-testing/verification-queries`). Expose only what a test
  reads; the services reach each other by service name.

### Overriding the stack for tests

| Need | How |
|---|---|
| Switch a behaviour the compose file interpolates | `withEnv("PAYMENTS_MODE", "sandbox")` against `${PAYMENTS_MODE:-live}` in the file |
| Change one service's environment or profile | An entry in `compose.test.yaml` (a second file passed to the constructor) |
| Run only the services the suite needs | `withServices("api", "worker", "postgres", "mailpit")` |
| Replace an external dependency (a payment provider) | A stub service (WireMock) in `compose.test.yaml`, with the API's base-URL variable pointed at it; never edit the main compose file per test |

A test cannot replace a bean inside a running service. Behaviour that needs a fake belongs in the stack's
configuration or in the in-process mode below.

### A test — trace context on every request

Requests go through the suite's typed clients, whose spec carries the `TraceparentFilter` from
`api-client-writer/references/trace-context.md`: one trace id per test. The API's span, the broker hop and the
worker's span then land in one trace in Tempo, and `test-reports` links it from the failed result. The clients
take the resolved base URI through a constructor overload that passes it to `BaseApiClient`; the token comes from
`test-login-tokens` (`TestTokens.buyer()` below).

```java
package com.{org}.apitests.system.orders;

import static org.testng.Assert.assertEquals;

import com.{org}.apitests.clients.orders.OrdersClient;
import com.{org}.apitests.system.SystemUnderTest;
import io.restassured.response.Response;
import org.testng.annotations.Test;

public class PlaceOrderSystemTest extends SystemUnderTest {

    @Test
    public void Should_ReturnCreated_When_AValidOrderIsPosted() {
        var request = new PlaceOrderRequestBuilder().build();

        Response response = new OrdersClient(apiBaseUrl(), TestTokens.buyer()).create(request);

        assertEquals(response.statusCode(), 201, response.asPrettyString());
    }
}
```

Spans reach Tempo only when the stack's `OTEL_EXPORTER_OTLP_ENDPOINT` points at a collector (`deploy/local/` on a
laptop); the header is sent either way.

## Email — Mailpit as a compose service

When the system sends mail, Mailpit is a service in the stack (in `compose.test.yaml`), and the API's SMTP host is
its service name:

```yaml
services:
  mailpit:
    image: axllent/mailpit:v1.33.1
  api:
    environment:
      SPRING_MAIL_HOST: mailpit
      SPRING_MAIL_PORT: "1025"
```

The test waits on the `MailpitClient` from `email-testing/references/mailpit.md`, built on `mailpitBaseUrl()`:

```java
@Test
public void Should_SendTheConfirmation_When_AnOrderIsPlaced() {
    String email = "buyer-" + UUID.randomUUID() + "@test.local";
    var request = new PlaceOrderRequestBuilder().withEmail(email).build();

    Response response = new OrdersClient(apiBaseUrl(), TestTokens.buyer()).create(request);
    assertEquals(response.statusCode(), 201, response.asPrettyString());

    var confirmation = new MailpitClient(mailpitBaseUrl()).waitFor(email, "Order confirmation", Duration.ofSeconds(30));

    assertEquals(confirmation.to().get(0).address(), email);
}
```

The shared email rules apply (unique recipient, condition-wait, no global wipe). Snapshotting the rendered email is
`email-testing/references/html-snapshots.md`.

## One Spring service in-process

When the test must replace a bean in one Spring service, or step through it in a debugger, run that service in the
test JVM and only its dependencies and siblings in containers. `@ServiceConnection` binds a container bean to the
service's connection properties; a `DynamicPropertyRegistrar` points it at a sibling:

```java
package com.{org}.ordering.system;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.RabbitMQContainer;
import org.testcontainers.containers.wait.strategy.Wait;

@TestConfiguration(proxyBeanMethods = false)
class SystemContainers {
    private static final int PRICING_PORT = 8080;

    @Bean
    @ServiceConnection
    PostgreSQLContainer<?> postgres() {
        return new PostgreSQLContainer<>("postgres:18.7-alpine");
    }

    @Bean
    @ServiceConnection
    RabbitMQContainer rabbit() {
        return new RabbitMQContainer("rabbitmq:4.4.0-management-alpine");
    }

    @Bean
    GenericContainer<?> pricing() {
        return new GenericContainer<>("{registry}/pricing:{released-tag}")
            .withExposedPorts(PRICING_PORT)
            .waitingFor(Wait.forHttp("/actuator/health").forStatusCode(200));
    }

    @Bean
    DynamicPropertyRegistrar pricingUrl(GenericContainer<?> pricing) {
        return registry -> registry.add("pricing.base-url",
            () -> "http://" + pricing.getHost() + ":" + pricing.getMappedPort(PRICING_PORT));
    }
}
```

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(SystemContainers.class)
public class PlaceOrderInProcessTest extends AbstractTestNGSpringContextTests {
    @LocalServerPort private int port;
    // tests call http://localhost:{port} through the typed clients, as above
}
```

- Boot starts the container beans before the context needs them and stops them when it closes; the context cache
  shares them across classes. The classes are the Testcontainers 1.x ones the Boot 3 BOM manages.
- `DynamicPropertyRegistrar` needs Spring Framework 6.2 (Boot 3.4+); before that, a static `@DynamicPropertySource`.
- This mode tests one service with real neighbours; only the compose run proves the services' own wiring.

## Rules

The standards this skill's output must meet are the qa-java rule files, not a list here: `qa-java-api.md`,
`qa-java.md` and `qa-java-data.md`. Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in
`qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's
recipes disagree, the rule files win.

## Output format

```
Created: src/test/resources/compose.test.yaml                    Purpose: no host ports, no volumes, test profiles
Created: src/test/java/.../system/SystemUnderTest.java          Purpose: one stack per suite, healthy before tests
Created: src/test/java/.../system/<area>/<Feature>SystemTest.java  Purpose: Should_X_When_Y tests across services
```

Then: the services waited for and how, the overrides set, and the `./gradlew test` result.

## Anti-examples

- **`ComposeContainer` started in `@BeforeMethod`** — a full stack start per test; the suite takes minutes per
  class. Start it once in `@BeforeSuite`.
- **`Thread.sleep(30_000)` until the API answers** — wait on the health endpoint or the compose health check.
- **Fixed host ports in the compose file the test uses** — two CI jobs on one host collide; reset them in the
  override and resolve ports from the container.
- **`docker compose up` in a CI step before `./gradlew test`** — nothing tears it down when the suite fails.
- **A retry filter on the test client** — it hides the first failure the test exists to see.

## Handoffs

- Database seeding and row verification → `db-testing/verification-queries`
- Mailpit client and email assertions → `email-testing`
- Typed clients and the `traceparent` filter → `api-client-writer`
- Trace links on failed results → `qa/reporting/java/skills/test-reports`
- The CI job (Docker and the Compose plugin on the agent, image builds) → `qa/cicd/java/skills/ci-pipelines`
- Unit tests of the logic inside a service → `be-java` `unit-testing`
