---
name: qa-test-environments-java
description: Use when the user asks to spin up a whole multi-service environment (not just one database) for Java 21 + Spring Boot 3 integration/E2E tests via Testcontainers — `ComposeContainer` (Compose V2) driving a committed `docker-compose.test.yml` (app + DB + queue/cache/mailcatcher) with `withExposedService` + per-service wait strategies, or a hand-built `GenericContainer` topology sharing a `Network.newNetwork()` with `withNetworkAliases` for inter-container DNS, explicit waits (`Wait.forHttp` / `forListeningPort` / `forLogMessage` / `forHealthcheck` — never a `Thread.sleep`), `withReuse(true)` for fast local loops vs fresh-per-suite in CI, the Ryuk reaper, and surfacing host+mapped-port connection details to tests through a TestNG fixture. Triggers: "spin up the whole stack (api + postgres + kafka) for these tests", "Testcontainers ComposeContainer in TestNG", "boot app + DB + Kafka together and wait for all of them", "give my service a network alias so the container can reach the DB", "reuse the containers between local test runs". Do NOT use for a single database container with Flyway migrations + row reset (use `qa/java/skills/db-testing/testcontainers`), for TypeScript (`qa/typescript/skills/test-environments`), for .NET (`qa/dotnet/skills/test-environments`), for the CI runner that hosts these tests (`qa/java/skills/ci-pipelines/github-actions`), or for in-browser network mocking (`qa/java/skills/network-monitoring/playwright-routes`).
---

# QA — Test Environments with Testcontainers + docker-compose (Java)

Boots a **whole dependency topology** — application-under-test plus its real backing services (DB, cache, queue, object store, mail catcher, third-party stub) — for Java 21 + Spring Boot 3 integration/E2E tests, using `org.testcontainers`. This is the **general environment spin-up** skill: multi-container `ComposeContainer` orchestration and hand-built multi-container networks. For a *single* database container with Flyway migrations and per-test row reset, that is the narrower `qa/java/skills/db-testing/testcontainers` skill — this one owns everything from two containers up.

Every service is waited on by an **explicit readiness condition**, never a `Thread.sleep`. Connection details (host + dynamically-mapped port) are read off the started environment and surfaced to tests through a TestNG **fixture** — tests never hardcode `localhost:5432`. Because **TestNG has no JUnit 5 `@Testcontainers`/`@Container` extension**, the lifecycle is driven manually from `@BeforeSuite`/`@AfterSuite`.

## Stack

- Java 21 + Spring Boot 3.x, Gradle (Kotlin DSL)
- `org.testcontainers:testcontainers` (≥ 1.20 — `ComposeContainer`, `Network`, `Wait`, `withReuse`) + module artifacts (`:postgresql`, `:kafka`, …) where one exists
- TestNG — **manual** lifecycle via `@BeforeSuite`/`@AfterSuite` (no `@Testcontainers` extension; that is JUnit 5 only)
- Compose files under `src/test/resources/compose/`, fixtures under `src/test/java/.../fixtures/`
- These suites run on `ubuntu-latest` (Docker pre-installed) under `qa/java/skills/ci-pipelines/github-actions`

## When to use

- You need **more than one** container per suite: app + DB + Redis, or DB + Kafka + a third-party stub
- A committed `docker-compose.yml` already describes the dev topology and you want tests to reuse it verbatim
- The app-under-test must run *as a container* and reach its dependencies by hostname (inter-container DNS)
- You want fast local re-runs by **reusing** already-running containers, but a clean fresh environment in CI
- You're booting a mail catcher / object store / message broker that has no dedicated db-testing skill

## When NOT to use

- A single DB with Flyway migrations + per-test reset → `qa/java/skills/db-testing/testcontainers`
- TypeScript / .NET stacks → `qa/{typescript,dotnet}/skills/test-environments`
- The CI workflow that runs these (Docker enablement, artifact upload) → `qa/java/skills/ci-pipelines/github-actions`
- In-browser HTTP mocking/interception (no real services) → `qa/java/skills/network-monitoring/playwright-routes`
- Pure unit tests with no out-of-process dependency

## Inputs needed

Ask at most 3 questions; infer the rest from the build.

1. **Topology** — which services make up the environment (app, DB engine, cache, queue, mail, stubs)?
2. **Source of truth** — is there an existing `docker-compose.yml` to drive (`ComposeContainer`), or should the topology be built in code with `GenericContainer` + a shared `Network`?
3. **Scope** — one environment per *suite* (default, via `@BeforeSuite`) or per test class?

Infer the test framework (TestNG per CLAUDE.md), package, and app image source from the Gradle build.

## Decision matrix

| Decision | Default | Override when |
|---|---|---|
| Orchestration | **`ComposeContainer`** driving a committed `docker-compose.test.yml` | Hand-built `GenericContainer` + `Network` when there's no compose file or you need per-container control (reuse, code) |
| Compose engine | **`withLocalCompose(false)`** (bundled compose in a container — no host binary needed, CI-portable) | `withLocalCompose(true)` only when the runner has a known compatible `docker compose` and you need its exact behavior |
| Environment scope | **Per suite** via `@BeforeSuite` | Per class (`@BeforeClass`) only when classes genuinely cannot share an environment |
| Inter-container DNS | Compose service names (built-in network) / `withNetworkAliases("db")` on a shared `Network` | — (never hardcode container IPs) |
| Wait strategy | **Per service**: `Wait.forHttp("/health")` for the app, `forListeningPort`/`forLogMessage` for deps | `Wait.forHealthcheck()` when the compose service defines a `healthcheck` |
| Reuse | **`.withReuse(true)` locally** (+ `testcontainers.reuse.enable=true`); **fresh per suite in CI** | Never reuse in CI — a leaked dirty container makes runs non-deterministic |
| Image tags | **Pinned** (`postgres:17.2`, `redis:7.4`) | Never `latest` |
| Connection details | **Read from the started env** (`getServiceHost`/`getServicePort`, `getMappedPort`) and surfaced via the fixture | Never hardcode `localhost:5432` — ports are dynamic |
| Teardown | `environment.stop()` in `@AfterSuite` (Ryuk as backstop) | Skip `stop()` only for a reused local environment (leave it running) |

## Patterns

### Multi-service environment from a committed compose file — `src/test/resources/compose/docker-compose.test.yml`

Drive the same compose topology dev uses. Define a `healthcheck` per service so Testcontainers can wait on it directly.

```yaml
services:
  postgres:
    image: postgres:17.2
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d appdb"]
      interval: 1s
      retries: 30

  redis:
    image: redis:7.4
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1s
      retries: 30

  api:
    build: ../../../..          # the app-under-test image
    environment:
      DATABASE_URL: postgres://test:test@postgres:5432/appdb   # service-name DNS, not localhost
      REDIS_URL: redis://redis:6379
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    ports:
      - "8080"                 # host port assigned dynamically; read it back, never assume 8080
```

### Environment fixture with manual TestNG lifecycle — `Stack.java`

TestNG has no `@Testcontainers` extension, so `start()`/`stop()` are called by hand from `@BeforeSuite`/`@AfterSuite`. Expose **intent** (`apiBaseUrl()`, `databaseUrl()`), not raw container handles.

```java
package com.example.it.fixtures;

import org.testcontainers.containers.ComposeContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import java.io.File;

public final class Stack {

    private static final File COMPOSE_FILE =
            new File("src/test/resources/compose/docker-compose.test.yml");

    // CI never reuses — a leaked dirty container would make the run non-deterministic.
    private static final boolean REUSE = !"true".equals(System.getenv("CI"));

    private final ComposeContainer environment =
            new ComposeContainer(COMPOSE_FILE)
                    .withExposedService("postgres", 5432, Wait.forHealthcheck())
                    .withExposedService("redis", 6379, Wait.forHealthcheck())
                    .withExposedService("api", 8080,
                            Wait.forHttp("/health").forStatusCode(200))
                    .withLocalCompose(false);   // bundled compose — no host binary needed

    public void start() {
        environment.start();
    }

    public void stop() {
        // In CI, tear the environment down. Locally with reuse on, leave it running.
        if (!REUSE) {
            environment.stop();
        }
    }

    public String apiBaseUrl() {
        return "http://%s:%d".formatted(
                environment.getServiceHost("api", 8080),
                environment.getServicePort("api", 8080));
    }

    public String databaseUrl() {
        return "jdbc:postgresql://%s:%d/appdb".formatted(
                environment.getServiceHost("postgres", 5432),
                environment.getServicePort("postgres", 5432));
    }

    public String redisUri() {
        return "redis://%s:%d".formatted(
                environment.getServiceHost("redis", 6379),
                environment.getServicePort("redis", 6379));
    }
}
```

> `ComposeContainer` is the **Compose V2** class (reference services by their plain name — `"postgres"`, not the legacy `"postgres_1"` of the older `DockerComposeContainer`). `withLocalCompose(false)` runs compose inside a container so no host `docker compose` binary is required — the CI-portable default.

### TestNG base class wiring the suite lifecycle — `IntegrationTestBase.java`

```java
package com.example.it;

import com.example.it.fixtures.Stack;
import org.testng.annotations.AfterSuite;
import org.testng.annotations.BeforeSuite;

public abstract class IntegrationTestBase {

    protected static final Stack STACK = new Stack();

    @BeforeSuite(alwaysRun = true)
    public void startStack() {
        STACK.start();
    }

    @AfterSuite(alwaysRun = true)
    public void stopStack() {
        STACK.stop();
    }
}
```

```java
package com.example.it;

import org.testng.annotations.Test;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.assertj.core.api.Assertions.assertThat;

public class CheckoutIntegrationTest extends IntegrationTestBase {

    private final HttpClient http = HttpClient.newHttpClient();

    @Test
    public void Should_persist_order_and_publish_event_When_checkout_succeeds() throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(STACK.apiBaseUrl() + "/checkout"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString("{\"sku\":\"ABC\",\"qty\":2}"))
                .build();

        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());

        assertThat(response.statusCode()).isEqualTo(201);
    }
}
```

### Hand-built topology with a shared network — `NetworkStack.java`

No compose file? Build the topology in code. A user-defined `Network` + `withNetworkAliases` gives containers **DNS names** to reach each other; the app talks to `db:5432`, the host talks to the app's mapped port.

```java
package com.example.it.fixtures;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.Network;
import org.testcontainers.containers.wait.strategy.Wait;

public final class NetworkStack {

    private final Network network = Network.newNetwork();

    private final GenericContainer<?> db = new GenericContainer<>("postgres:17.2")
            .withNetwork(network)
            .withNetworkAliases("db")                 // the app reaches it as host "db"
            .withEnv("POSTGRES_DB", "appdb")
            .withEnv("POSTGRES_USER", "test")
            .withEnv("POSTGRES_PASSWORD", "test")
            .withExposedPorts(5432)
            .waitingFor(Wait.forListeningPort());

    private final GenericContainer<?> api = new GenericContainer<>("myorg/api:test")
            .withNetwork(network)
            .withEnv("DATABASE_URL", "postgres://test:test@db:5432/appdb") // alias, not host:port
            .withExposedPorts(8080)
            .waitingFor(Wait.forHttp("/health").forStatusCode(200));

    public void start() {
        db.start();   // start dependencies before the app that needs them
        api.start();
    }

    public void stop() {
        api.stop();
        db.stop();
        network.close();   // Ryuk also reaps these if the JVM dies first
    }

    public String apiBaseUrl() {
        return "http://%s:%d".formatted(api.getHost(), api.getMappedPort(8080));
    }
}
```

### Container reuse for fast local loops

`withReuse(true)` keeps a `GenericContainer` running between runs; the next run with an identical config hash attaches to it instead of booting fresh. Gate it off in CI.

```java
GenericContainer<?> db = new GenericContainer<>("postgres:17.2")
        .withEnv("POSTGRES_DB", "appdb")
        .withExposedPorts(5432)
        .waitingFor(Wait.forListeningPort())
        .withReuse(true);                  // no-op unless reuse is enabled (see below)
```

Reuse only activates when `testcontainers.reuse.enable=true` is set in `~/.testcontainers.properties` (or `TESTCONTAINERS_REUSE_ENABLE=true`). With reuse on, **do not** call `.stop()` — leave the container running for the next run. CI sets neither, so the same code boots fresh and Ryuk reaps it. (Reuse is a `GenericContainer` feature — `ComposeContainer` is not reusable across runs.)

### Custom wait strategy for a bespoke service

```java
GenericContainer<?> broker = new GenericContainer<>("confluentinc/cp-kafka:7.6.1")
        .withExposedPorts(9092)
        .waitingFor(Wait.forLogMessage(".*started \\(kafka.server.KafkaServer\\).*", 1));
```

`Wait.forLogMessage(regex, times)`, `Wait.forListeningPort()`, `Wait.forHttp(path).forStatusCode(n)`, `Wait.forHealthcheck()` (Docker `HEALTHCHECK`). **Never** `Thread.sleep` to wait for readiness.

## Rules

### Topology & orchestration
- Prefer driving a **committed `docker-compose.test.yml`** via `ComposeContainer` so tests and dev share one topology. Build it in code (`GenericContainer` + `Network`) only when there's no compose file or you need per-container control (reuse, custom waits).
- Use **`ComposeContainer`** (Compose V2; plain service names), not the deprecated `DockerComposeContainer` (`service_1` suffixes).
- Boot the environment **once per suite** via `@BeforeSuite` — TestNG has no `@Testcontainers` extension, so the lifecycle is manual. Never `start()` in `@BeforeMethod` (that's per-test).
- Containers talk to each other by **service name** (compose) or **network alias** (`withNetworkAliases`) — never by hardcoded container IP.

### Wait strategies (no sleeps)
- Every service gets an **explicit readiness condition**. App → `Wait.forHttp("/health")`; DB/broker → `forListeningPort`/`forLogMessage`/`forHealthcheck`.
- Define a `healthcheck` in compose and wait with `Wait.forHealthcheck()` so the readiness contract lives next to the service.
- **No `Thread.sleep`** as a readiness wait, anywhere (global rule).

### Connection details
- Read host + port off the **started** environment (`getServiceHost`/`getServicePort` for compose; `getHost`/`getMappedPort` for `GenericContainer`); ports are assigned dynamically by Docker.
- Surface them through the fixture as intent-named methods (`apiBaseUrl()`, `databaseUrl()`); tests call those, never `getMappedPort` directly.
- **Never** hardcode `localhost:5432` or the compose-internal port — that's the container-to-container port, not the host-mapped one.
- Never log a credentialed connection string (secrets policy).

### Reuse vs fresh
- `.withReuse(true)` + `testcontainers.reuse.enable=true` for **fast local loops** (`GenericContainer` only); with reuse on, do not stop.
- **CI always boots fresh and tears down** — gate reuse on `!"true".equals(System.getenv("CI"))`. A reused dirty container makes CI non-deterministic.
- `ComposeContainer` is not reusable across runs — use the `GenericContainer` topology when you need cross-run reuse.

### Teardown & the reaper
- Call `environment.stop()` / `container.stop()` + `network.close()` in `@AfterSuite(alwaysRun = true)` (CI). The **Ryuk** reaper is the backstop that kills leaked containers if the JVM dies — never the primary cleanup.
- Don't disable Ryuk except on a runner that forbids the sidecar — then you own teardown entirely.

### Images & scope
- Pin every image (`postgres:17.2`, not `latest`/`17`). Document the prod version in a comment.
- Default to a single shared environment per suite; one environment *per class* only with proven isolation (TestNG parallel settings off for the integration suite otherwise).

### Diagnostics
- On failure, attach service logs to Allure: stream `container.getLogs()` to an attachment. Pair with `qa/java/skills/allure-reporting`.

### What NOT to do
- No `Thread.sleep` to wait for a service — use a `Wait.*` strategy.
- No `latest`/floating image tags.
- No hardcoded `localhost:<fixed-port>` — read `getServicePort()`/`getMappedPort()` from the started env.
- No container-to-container traffic via IP — use compose service names / `withNetworkAliases`.
- No `@Testcontainers`/`@Container` annotations with TestNG — they're JUnit-5 only; drive `start()`/`stop()` manually.
- No `withReuse(true)` left active in CI (gate on `CI`), and no `stop()` when reuse is on locally.
- No `start()` in `@BeforeMethod` — that's a fresh environment per test; use `@BeforeSuite`.
- No Flyway migrations / per-test row reset in here — that's `qa/java/skills/db-testing/testcontainers`'s job; this skill stops at booting the topology.
- No credentialed connection string in logs or test names (secrets policy).
- No swallowing a `@BeforeSuite` boot exception — let it propagate so TestNG fails the suite loudly.

## Generation steps

1. Read the Gradle build and any existing `docker-compose.yml` / fixtures to learn the topology, package, and app image source.
2. Confirm the **topology**, the **source of truth** (compose vs code), and the **scope** (per-suite vs per-class).
3. Generate:
   - `src/test/resources/compose/docker-compose.test.yml` (if driving compose) with a `healthcheck` per service.
   - `.../fixtures/Stack.java` (or `NetworkStack.java`) exposing intent-named accessors, explicit per-service waits, CI-gated reuse.
   - `.../IntegrationTestBase.java` wiring `@BeforeSuite`/`@AfterSuite` to the fixture.
   - A concrete `.../CheckoutIntegrationTest.java` hitting the booted stack.
   - `build.gradle.kts`: add `org.testcontainers:testcontainers` (+ module artifacts), `org.testng:testng`, `org.assertj:assertj-core`.
4. Run `./gradlew integrationTest` (or `test`) — expect green or a real assertion failure, not a boot/wait crash.
5. Confirm reuse works locally (`testcontainers.reuse.enable=true`, run twice — the second is fast) and that CI (`CI=true`) boots fresh and tears down.

## Cross-references

- **`qa/typescript/skills/test-environments`** (canonical) + **`qa/dotnet/skills/test-environments`** — the sibling stacks; this file ports the canonical TS skill into `org.testcontainers`/TestNG idioms.
- **`qa/java/skills/db-testing/testcontainers`** — the narrower skill for a *single* DB container with Flyway migrations + per-test reset; this environment skill is what you graduate to when the suite needs the app + DB + other services together. It cross-links back here for multi-container orchestration.
- **`qa/java/skills/db-testing/client`** — the DB client/query wiring that runs against the `databaseUrl()` this fixture surfaces.
- **`qa/java/skills/ci-pipelines/github-actions`** — runs these suites on `ubuntu-latest` (Docker pre-installed, Ryuk works out of the box); uploads JUnit + logs.
- **`qa/java/skills/test-data-builder`** — seeds data into the booted services.
- **`qa/java/skills/allure-reporting`** — attach per-service container logs on failure.
