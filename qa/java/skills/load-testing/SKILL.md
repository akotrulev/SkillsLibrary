---
name: qa-load-testing-java
description: Use when the user asks to design or author Gatling performance / load tests in Java 21 (Gatling 3.11+ Java DSL). Triggers: "write a Gatling simulation for X", "Gatling spike test for our Java service", "ramp profile in Gatling Java DSL". For end-to-end suite work prefer the phased agent `qa-performance-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Performance Testing with Gatling (Java 21)

Authors Gatling 3.11+ simulations using the **Java DSL** against deployed services. Gatling is the right tool when the team strongly prefers a JVM-native author experience (shared DTOs / clients with the production Spring Boot project) and wants Gatling's expressive injection / scenario combinators. For all other cases default to k6 (`qa/typescript/skills/load-testing`).

## When to use

- JVM-heavy teams that want to share DTOs / clients with the production Spring Boot project.
- Perf tests that need rich scenario combinators (looped flows, conditional steps, dynamic feeders).
- Teams already familiar with the JVM build / IDE story who would rather not learn k6's JS API.

## When NOT to use

- New perf work without a strong JVM preference → `qa/typescript/skills/load-testing`
- .NET-native author experience → `qa/dotnet/skills/load-testing`
- Functional behavior tests → `qa/java/skills/api-test-author/writer`
- Microbenchmarks (loop bodies, parsing speed) → JMH (`openjdk-jmh`)
- Defining the SLO itself → `qa/manual/quality-metrics`

Load `qa/_shared/performance` for workload models, open-loop vs closed-loop guidance, environment policy, and the reporting template.

## Stack

- **Runtime**: Java 21
- **Gatling**: 3.11+ Java DSL (`io.gatling.javaapi.*`) — modern Java-first; Scala remains supported but is no longer the default.
- **Build**: Gradle (Kotlin DSL) with `io.gatling.gradle` plugin.
- **Layout**: simulations live in `src/gatling/java/` (Gradle plugin convention); resources (feeder CSVs, request bodies) in `src/gatling/resources/`.

```
perf-tests/
├── build.gradle.kts            ← applies io.gatling.gradle
└── src/
    └── gatling/
        ├── java/
        │   └── com/example/orders/
        │       ├── OrdersSmokeSimulation.java
        │       ├── OrdersAverageSimulation.java
        │       ├── OrdersSpikeSimulation.java
        │       └── OrdersSoakSimulation.java
        └── resources/
            ├── feeders/
            │   └── order-ids.csv
            └── bodies/
                └── checkout.json
```

### Gradle Kotlin DSL

```kotlin
plugins {
    id("io.gatling.gradle") version "3.11.5"
}

repositories { mavenCentral() }

gatling {
    // optional — override default report dir, system props, etc.
    systemProperties = mapOf(
        "baseUrl"   to (System.getenv("BASE_URL")   ?: "https://api-staging.yourco.com"),
        "authToken" to (System.getenv("AUTH_TOKEN") ?: "")
    )
}
```

Run: `./gradlew gatlingRun-com.example.orders.OrdersAverageSimulation`.

## Average-load simulation

```java
// src/gatling/java/com/example/orders/OrdersAverageSimulation.java
package com.example.orders;

import io.gatling.javaapi.core.Simulation;
import io.gatling.javaapi.core.ScenarioBuilder;
import io.gatling.javaapi.http.HttpProtocolBuilder;

import java.time.Duration;
import java.util.concurrent.ThreadLocalRandom;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class OrdersAverageSimulation extends Simulation {

    private final HttpProtocolBuilder httpProtocol = http
        .baseUrl(System.getProperty("baseUrl"))
        .acceptHeader("application/json")
        .authorizationHeader("Bearer " + System.getProperty("authToken"));

    private final ScenarioBuilder ordersAverage = scenario("orders_average")
        .exec(session -> {
            int id = ThreadLocalRandom.current().nextInt(1, 6);
            return session.set("orderId", String.format("o-%03d", id));
        })
        .group("GET /orders/{id}", () -> exec(
            http("get order")
                .get(session -> "/orders/" + session.getString("orderId"))
                .check(status().is(200))
        ));

    {
        setUp(
            ordersAverage.injectOpen(
                rampUsersPerSec(5).to(50).during(Duration.ofMinutes(1)),
                constantUsersPerSec(50).during(Duration.ofMinutes(5)),
                rampUsersPerSec(50).to(0).during(Duration.ofSeconds(30))
            )
        )
        .protocols(httpProtocol)
        .assertions(
            details("GET /orders/{id}").responseTime().percentile(95.0).lt(300),
            details("GET /orders/{id}").responseTime().percentile(99.0).lt(800),
            global().failedRequests().percent().lt(0.5)
        );
    }
}
```

`injectOpen` with `constantUsersPerSec` / `rampUsersPerSec` is the **open-loop** profile — right for "we want N RPS regardless of VU performance". `injectClosed` is closed-loop (concurrency-targeted) — only use for fixed-concurrency models.

`group("…")` is the equivalent of k6's route tag — assertions targeted at `details("group name")` give per-route SLO gates.

## Smoke (1-minute PR gate)

```java
setUp(
    ordersSmoke.injectOpen(constantUsersPerSec(5).during(Duration.ofMinutes(1)))
)
.protocols(httpProtocol)
.assertions(
    details("GET /orders/{id}").responseTime().percentile(95.0).lt(400),
    global().failedRequests().percent().lt(0.1)
);
```

## Spike

```java
setUp(
    ordersSpike.injectOpen(
        constantUsersPerSec(10).during(Duration.ofMinutes(1)),    // baseline
        rampUsersPerSec(10).to(500).during(Duration.ofSeconds(10)), // spike
        constantUsersPerSec(500).during(Duration.ofMinutes(1)),    // hold
        rampUsersPerSec(500).to(10).during(Duration.ofMinutes(1))  // recovery
    )
).protocols(httpProtocol);
```

## Soak (4-hour endurance)

```java
setUp(
    ordersSoak.injectOpen(constantUsersPerSec(100).during(Duration.ofHours(4)))
)
.protocols(httpProtocol)
.assertions(
    details("GET /orders/{id}").responseTime().percentile(95.0).lt(300),
    global().failedRequests().percent().lt(1.0)
);
```

Watch the **slope** in the Gatling report — latency drifting upward over the 4 hours is the leak the soak is meant to catch.

## SLO-shaped assertions

Gatling's `assertions(...)` block is what fails the build:

| SLO | Assertion |
|---|---|
| p95 latency ≤ 300ms on a route | `details("group").responseTime().percentile(95.0).lt(300)` |
| Error rate < 0.5% overall | `global().failedRequests().percent().lt(0.5)` |
| Throughput ≥ 100 RPS on a route | `details("group").requestsPerSec().gt(100)` |

When any assertion fails, Gatling exits non-zero — the CI step fails the build automatically.

## Feeders (parameterized data)

```java
import io.gatling.javaapi.core.FeederBuilder;

FeederBuilder<String> orderIds = csv("feeders/order-ids.csv").random();

ScenarioBuilder s = scenario("orders_average")
    .feed(orderIds)
    .group("GET /orders/{id}", () -> exec(
        http("get order").get("/orders/#{orderId}").check(status().is(200))
    ));
```

CSV at `src/gatling/resources/feeders/order-ids.csv`:

```csv
orderId
o-001
o-002
o-003
```

Use `.circular()` / `.random()` / `.shuffle()` depending on the desired access pattern.

## Multi-step scenarios

```java
private final ScenarioBuilder checkout = scenario("checkout")
    .group("auth", () -> exec(
        http("login").post("/auth/login")
            .body(StringBody("{\"user\":\"perf-001\",\"pwd\":\"perf\"}"))
            .check(status().is(200))
            .check(jsonPath("$.token").saveAs("token"))
    ))
    .group("checkout", () -> exec(
        http("post checkout").post("/checkout")
            .header("Authorization", session -> "Bearer " + session.getString("token"))
            .body(RawFileBody("bodies/checkout.json"))
            .check(status().is(201))
    ));
```

Per-group latencies appear in the HTML report — diagnose where the time goes.

## Seeded fixtures

Gatling has no `setup/teardown` lifecycle equivalent to k6's. Use a small **bootstrap class** invoked via Gradle `dependsOn` before the simulation runs, and a **cleanup task** after:

```kotlin
// build.gradle.kts
tasks.register("seedPerfFixtures", JavaExec::class) {
    mainClass.set("com.example.perf.SeedFixtures")
    classpath = sourceSets["main"].runtimeClasspath
    args = listOf("50")
}

tasks.named("gatlingRun-com.example.orders.OrdersAverageSimulation") {
    dependsOn("seedPerfFixtures")
    finalizedBy("cleanupPerfFixtures")
}
```

Where `SeedFixtures` uses the production HTTP client to create namespaced perf data (`perf-<uuid>` ids) and `CleanupPerfFixtures` deletes them. Never share fixture ids across parallel runs.

## Tool version pinning

Pin the Gatling plugin version in `build.gradle.kts`:

```kotlin
plugins {
    id("io.gatling.gradle") version "3.11.5"
}
```

Never use `+` or `latest.release`.

## CI integration

### GitHub Actions

```yaml
perf-smoke:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-java@v4
      with: { distribution: temurin, java-version: '21' }
    - name: Gatling smoke
      env:
        BASE_URL:   ${{ secrets.STAGING_URL }}
        AUTH_TOKEN: ${{ secrets.STAGING_TOKEN }}
      run: ./gradlew gatlingRun-com.example.orders.OrdersSmokeSimulation
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: gatling-report
        path: build/reports/gatling
```

### Azure Pipelines

```yaml
- task: JavaToolInstaller@0
  inputs: { versionSpec: '21', jdkArchitectureOption: 'x64', jdkSourceOption: 'PreInstalled' }

- task: Gradle@3
  inputs:
    gradleWrapperFile: gradlew
    tasks: gatlingRun-com.example.orders.OrdersSmokeSimulation
  env:
    BASE_URL:   $(STAGING_URL)
    AUTH_TOKEN: $(STAGING_TOKEN)

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: build/reports/gatling
    ArtifactName: gatling-report
```

For the HTML report, use the `PublishHtmlReport@1` task pointing at the timestamped subdirectory under `build/reports/gatling/`.

## Gatling Enterprise (formerly FrontLine)

For distributed runs, dashboards, history, and trends:

```kotlin
plugins {
    id("io.gatling.enterprise") version "1.8.0"
}
```

Push a simulation: `./gradlew gatlingEnterprisePackage gatlingEnterpriseUpload`.

Pair with Grafana for service-side correlation (`observability/dashboards`).

## Rules (Gatling-specific)

- **Open-loop (`injectOpen` with `constantUsersPerSec` / `rampUsersPerSec`)** by default. `injectClosed` only when modelling a fixed concurrency cap.
- **`group("…")`** around every logical endpoint — assertions target `details("group")` for per-route SLO gates. No assertions on `global()` alone for latency.
- **System properties** (`System.getProperty("baseUrl")`) wired from environment variables via the `gatling { systemProperties = ... }` block — never hardcode URLs / tokens.
- **Feeders** for parameterized data (`csv(...).random()`); avoid baking long literal lists into the scenario body.
- **`exec(session -> ...)` to mutate the session map**, then reference via `#{key}` placeholders in URLs / bodies — keeps simulations DRY.
- **`StringBody` / `RawFileBody` / `ElFileBody`** for request payloads; never embed JSON via `+` string concatenation.
- **One simulation class per scenario** named `<Name>Simulation` so Gradle's `gatlingRun-<FQN>` task name is predictable.
- **`details("…")` per route + `global().failedRequests()`** in the `assertions(...)` block — non-zero exit fails CI.
- **Pin `io.gatling.gradle` plugin version**; never `+`.
- **Resources under `src/gatling/resources/`** — Gradle plugin auto-includes them on the classpath.

## What NOT to do

- No `injectClosed` (closed-loop) for an RPS-target test — use `injectOpen` with `*UsersPerSec`.
- No assertions on `global().responseTime().percentile(95.0)` only — global mixes fast and slow routes; assert per-`details("group")`.
- No hardcoded base URLs / tokens — system properties from env vars only.
- No `Thread.sleep` in scenario bodies — use Gatling's `pause(Duration.ofMillis(...))` and only when closed-loop pacing demands it.
- No persistence-mutating tests against prod — staging or dedicated perf env only.
- No reusing the same seeded fixture id across parallel runs — namespace per run id via `perf-<uuid>`.
- No floating Gatling plugin versions (`+` / `latest.release`).
- No Scala simulations mixed with Java simulations in the same module — pick one.
- No simulations without an `assertions(...)` block — that's a graph, not a gate.
- No `repeat(1000) { exec(...) }` to fake throughput — use the injection profile for RPS targeting.
- No mixing `http(...)` (Gatling DSL) with `RestAssured` calls inside the same scenario — wire all HTTP through Gatling so metrics are captured.

## Generation steps

1. Confirm tool (Gatling chosen over k6 because team prefers JVM), workload model, SLO targets, target environment. (See `_shared`.)
2. Add `io.gatling.gradle` plugin pinned in `build.gradle.kts`; configure `systemProperties` from env vars.
3. Author `<Name>Simulation.java` under `src/gatling/java/...` with one `HttpProtocolBuilder`, one `ScenarioBuilder`, `group(...)` per route, `injectOpen(...)` profile, and `assertions(...)` per route.
4. Add CSV feeders / body files under `src/gatling/resources/` as needed.
5. Wire seed / cleanup Gradle tasks if the test mutates state; chain via `dependsOn` / `finalizedBy`.
6. Add CI step (smoke on PR; full on release). Publish `build/reports/gatling/` as a CI artifact.
7. Run locally with `./gradlew gatlingRun-<FQN>`; confirm per-route assertions; confirm the test fails when an SLO is breached.
8. Add the report to the release / change notes (see `_shared` template).

## Handoffs

- Workload models, environment policy, reporting → `qa/_shared/performance`
- k6 (TypeScript) → `qa/typescript/skills/load-testing`
- NBomber (.NET) → `qa/dotnet/skills/load-testing`
- SLO targets the test validates → `qa/manual/quality-metrics`
- Grafana dashboards for server-side correlation → `observability/dashboards`
- Pipeline integration → `qa/cicd/java/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for perf reports → `qa/reporting/java/skills/test-reports`
- Bug filings discovered during perf → `qa/manual/bug-report-writer`
