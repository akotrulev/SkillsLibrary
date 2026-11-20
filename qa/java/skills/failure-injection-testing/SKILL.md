---
name: failure-injection-testing
description: Use when writing fault-injection tests in Java/TestNG with Toxiproxy via Testcontainers to assert graceful degradation. Triggers "survive a slow database". Not for load (load-testing).
disable-model-invocation: true
---

# QA — Chaos / Fault-Injection Testing (Java 21 / Toxiproxy + Testcontainers + TestNG)

Scaffolds **fault-injection resilience tests** in Java against a deployed service and its dependencies, using
[**Toxiproxy**](https://github.com/Shopify/toxiproxy) — Shopify's TCP fault-injection proxy — stood up via the
Testcontainers `ToxiproxyContainer` and driven by the `toxiproxy-java` client. It is the **inverse** of every
happy-path skill in this library: the REST/gRPC authors assert *the dependency answered correctly*; a chaos test
**breaks the dependency on purpose and asserts the app under test copes**.

> **The discipline this skill encodes** — four ideas that separate a correct chaos test from a happy-path reflex:
>
> 1. **A chaos test does NOT assert the dependency works — it INJECTS a fault and asserts the app DEGRADES
>    GRACEFULLY.** The happy-path reflex "assert the call succeeded" is *exactly wrong* here (the way "assert a
>    hardcoded literal" is wrong for i18n and "find the element and tap it" is wrong for native features). You add a
>    **toxic** (latency, bandwidth cap, `timeout`, `reset_peer`, sliced/partial response) to the dependency
>    connection and assert the app **retries / trips a circuit breaker / honors a timeout / serves a fallback** —
>    the failure-handling path normal tests never exercise.
> 2. **The proxy sits BETWEEN the app and the dependency — point the app at the proxy port, not the real
>    dependency.** This is the whole mechanism. Toxiproxy is a TCP proxy with a *listen* side (the app connects
>    here) and an *upstream* side (the real DB/API/broker). The app's connection string / base URL is rewired to
>    `toxiproxy.getHost():mappedPort` so **all** its traffic to that dependency flows through a fault point you
>    control. No proxy in the path → nothing to fault.
> 3. **Toxics are added and removed at runtime over the REST API — every test is a lifecycle.** `steady-state →
>    inject the toxic → assert degraded → remove the toxic → assert recovery.` Toxiproxy's control API (port 8474)
>    lets you mutate the fault mid-test via `proxy.toxics().latency(...)` / `.timeout(...)` and `toxic.remove()`, so
>    one test proves **both** that the app degrades under fault **and** that it heals once the fault clears (the
>    drain-then-assert lifecycle of `qa-java:realtime-stream-testing`, applied to faults).
> 4. **Assert the resilience PATTERN, not the fault.** The toxic is the *given*, not the assertion. Assert the
>    **behaviour it provokes**: the retry count, the circuit-breaker state transition (closed → open → half-open →
>    closed via resilience4j), the honored timeout (fails *fast*, not hangs), the fallback payload served. This is
>    what `qa-java:network-mocking` can *observe* but never *inject* — observe vs break.

## Decision matrix — fault scenario → toxic → what you assert

| You want to prove | Inject (toxic) | Assert (the resilience pattern) |
|---|---|---|
| **App survives a slow dependency** | `latency` (+ `jitter`), DOWNSTREAM | the call completes within the app's timeout via retry/fallback, OR fails *fast* — never hangs the request thread |
| **A timeout is honored (no hang)** | `timeout` (ms) or large `latency` > the app's deadline | the call fails as a *timeout* inside the app's budget; the user-facing path returns an error/fallback, not a 30s hang |
| **A circuit breaker opens under sustained failure** | `timeout` / `reset_peer` held across N calls | resilience4j breaker goes **CLOSED → OPEN**; subsequent calls short-circuit (`CallNotPermittedException`) without hitting the dependency |
| **The breaker recovers when the dependency heals** | inject, drive calls to OPEN, then **`toxic.remove()`** | after the wait window the breaker goes **OPEN → HALF_OPEN → CLOSED**; calls succeed again (idea #3 lifecycle) |
| **Retry-with-backoff fires the contracted number of times** | `reset_peer` / `timeout` on the first N attempts | the app makes exactly *maxAttempts* tries (assert via the dependency-side call count or resilience4j `Retry` metrics), then succeeds or falls back |
| **A fallback is served, not an error page** | `timeout` / connection cut | the degraded response is the contracted fallback (cached value, default, friendly message) — assert its content |
| **A partial / garbled response is handled** | `slicer` (fragment the stream) or `limitData` (cut after N bytes) | the app surfaces a parse/IO error and recovers — does NOT persist a truncated record or corrupt state |
| **Bandwidth starvation degrades, not crashes** | `bandwidth` (KB/s) DOWNSTREAM | the app stays responsive (timeout/fallback) under a throttled backend dependency (distinct from device-network conditioning) |
| **Probabilistic / flappy faults** | any toxic with `setToxicity(0.3)` | the app tolerates an intermittent fault — retries smooth over the fraction that fail |

## Stack

- Java 21, Gradle (Kotlin DSL), **TestNG** (the global default Java runner) + **AssertJ** + **Allure TestNG**
- **Testcontainers** — `org.testcontainers:testcontainers` + `org.testcontainers:toxiproxy` (the
  `ToxiproxyContainer` module) + the dependency module (e.g. `:postgresql`, `:kafka`)
- **toxiproxy-java** (`eu.rekawek.toxiproxy:toxiproxy-java`) — `ToxiproxyClient`, `Proxy`, `proxy.toxics()`,
  `ToxicDirection`
- **resilience4j** (`io.github.resilience4j:resilience4j-circuitbreaker` / `-retry` / `-timelimiter`) — the
  resilience patterns under test; assert their state/metrics (or assert your own retry/circuit code's effects)
- Layout: `src/test/java/<dep>/` (the fault tests), `src/test/java/support/chaos/` (the `ChaosProxy` fixture +
  `BaseChaosTest` container lifecycle)

```kotlin
// build.gradle.kts (excerpt)
dependencies {
    testImplementation("org.testcontainers:testcontainers:1.20.4")
    testImplementation("org.testcontainers:toxiproxy:1.20.4")
    testImplementation("org.testcontainers:postgresql:1.20.4")        // the dependency you fault (example)
    testImplementation("eu.rekawek.toxiproxy:toxiproxy-java:2.1.7")
    testImplementation("io.github.resilience4j:resilience4j-circuitbreaker:2.2.0")
    testImplementation("io.github.resilience4j:resilience4j-retry:2.2.0")
    testImplementation("org.testng:testng:7.10.2")
    testImplementation("org.assertj:assertj-core:3.26.3")
    testImplementation("org.awaitility:awaitility:4.2.2")             // bounded condition-poll — never Thread.sleep
    testImplementation("io.qameta.allure:allure-testng:3.0.0")
}
```

> **Why a proxy and not a mock?** A mock (e.g. WireMock) makes the *dependency* return a canned
> error at the application layer; a Toxiproxy toxic faults the *transport* — latency, a dropped TCP connection, a
> half-sent response — the failures that exercise socket timeouts, connection pools, and retry/circuit code. Mock
> when you control the contract and want a specific status; **fault-inject when you want to prove the app survives
> the network/dependency misbehaving**. They compose: a WireMock upstream behind a Toxiproxy listener faults the
> transport to a controllable contract.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The mechanism — proxy BETWEEN app and dependency (idea #2)**; **The toxic fixture — `support/chaos/ChaosProxy.java`**; **Partial / garbled response — `slicer` / `limitData`**; **Probabilistic faults — `toxicity`**.

## Inject-a-fault, assert-degradation (idea #1)

The simplest chaos test: with no toxic the call succeeds; **with the toxic injected the app must fail fast or fall
back — never hang**. Assert the *degraded behaviour*, not the fault.

```java
package db;

import support.chaos.BaseChaosTest;
import org.testng.annotations.Test;

import java.time.Duration;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

public class SlowDependencyTest extends BaseChaosTest {

    @Test
    public void shouldFailFastWhenTheDatabaseIsSlowerThanTheTimeout() throws Exception {
        chaos.injectLatency(5_000, 0);

        OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());

        Instant start = Instant.now();
        OrderResult result = app.placeOrder("sku-1");
        Duration elapsed = Duration.between(start, Instant.now());

        assertThat(result.isFallback()).as("degrades to fallback under latency").isTrue();
        assertThat(elapsed).as("fails fast inside the timeout budget").isLessThan(Duration.ofSeconds(3));
    }
}
```

## The full lifecycle — steady → inject → degraded → remove → recovered (idea #3)

One test proves the app **degrades under fault and heals when it clears**. This is the chaos analogue of the
drain-then-assert lifecycle in `qa-java:realtime-stream-testing`.

```java
@Test
public void shouldDegradeUnderConnectionDropThenRecoverWhenHealed() throws Exception {
    OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());

    assertThat(app.placeOrder("sku-1").isSuccess()).isTrue();

    chaos.cutConnection(0);

    assertThat(app.placeOrder("sku-1").isFallback()).as("degrades while the connection is cut").isTrue();

    chaos.healed();

    Awaitility.await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
        .untilAsserted(() -> assertThat(app.placeOrder("sku-1").isSuccess()).isTrue());
}
```

## Assert the resilience PATTERN — circuit breaker via resilience4j (idea #4)

Hold a fault across several calls and assert the **circuit-breaker state machine**, not the fault. The breaker is
the unit under test; Toxiproxy just supplies the sustained failure that should trip it.

```java
package db;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import support.chaos.BaseChaosTest;
import org.testng.annotations.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

public class CircuitBreakerChaosTest extends BaseChaosTest {

    @Test
    public void shouldOpenTheBreakerWhenTheDependencySustainsFailures() throws Exception {
        OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());
        CircuitBreaker breaker = app.breaker();

        assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.CLOSED);

        chaos.injectTimeout(0);
        new OrderLoad(app, "sku-1").placeSafely(10);

        assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.OPEN);

        chaos.healed();
        Awaitility.await().atMost(Duration.ofSeconds(15))
            .untilAsserted(() -> {
                app.placeOrderSafely("sku-1");
                assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.CLOSED);
            });
    }
}
```

`OrderLoad` is a test-side load driver, not application API: it calls the real `OrderService` method the given number of times and returns the outcomes, so the test body stays linear.

```java
public final class OrderLoad {
    private final OrderService app;
    private final String sku;

    public OrderLoad(OrderService app, String sku) {
        this.app = app;
        this.sku = sku;
    }

    public List<OrderResult> placeSafely(int times) {
        return IntStream.range(0, times).mapToObj(call -> app.placeOrderSafely(sku)).toList();
    }

    public List<OrderResult> placeWithRetry(int times) {
        return IntStream.range(0, times).mapToObj(call -> app.placeOrderWithRetry(sku)).toList();
    }
}
```

## Retry count — assert exactly the contracted attempts

A `reset_peer` on the connection makes attempts fail; assert the app makes **exactly** the contracted number of
tries (via the resilience4j `Retry` metrics, or by counting calls that reach the upstream), then succeeds/falls
back — not infinite, not one.

```java
@Test
public void shouldRetryExactlyThreeTimesThenFallBackOnConnectionResets() throws Exception {
    OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());
    chaos.cutConnection(0);

    OrderResult result = app.placeOrderWithRetry("sku-1");

    assertThat(result.isFallback()).isTrue();
    assertThat(app.retryMetrics().getNumberOfFailedCallsWithRetryAttempt()).isEqualTo(1);
    assertThat(app.lastAttemptCount()).as("maxAttempts honored").isEqualTo(3);
}
```

## The boundary — functional fault-injection vs production chaos engineering

This skill is **functional fault-injection inside a test**: a deterministic toxic on a dependency connection,
asserted against the app's resilience code, in CI. It is **not production chaos engineering** — Gremlin / Litmus /
Chaos Mesh injecting faults into a *live* cluster (pod kills, node drain, real network partitions) with steady-state
hypotheses and blast-radius control. Those run against running infrastructure; this runs in your test suite. If the
request is "run a GameDay on prod" or "kill pods in the cluster", that is out of scope — flag it and point at the
chaos-engineering platforms.

## Anti-patterns

- **Asserting the dependency works (or asserting the fault).** "The call succeeded" / "the call took 5s" proves
  nothing about resilience. *Fix:* assert the app's **degraded behaviour** — retry count, breaker state, honored
  timeout, fallback content.
- **Pointing the app at the real dependency instead of the proxy.** No proxy in the path → the toxic reaches
  nothing. *Fix:* rewire the app's connection string / base URL / bootstrap server to `chaos.host():chaos.port()`.
- **Injecting a toxic and never removing it.** You prove degradation but not **recovery**, and you leak the fault
  into the next test. *Fix:* run the full lifecycle — `healed()` (remove) then assert recovery; remove in teardown.
- **`Thread.sleep` to wait for the breaker to open/close or the dependency to "settle".** Banned by CLAUDE.md and
  flaky. *Fix:* **Awaitility** `await().atMost(...).untilAsserted(...)` on the real state (breaker state, a
  successful call).
- **A `latency` so small it doesn't exceed the app's timeout** (or so large the suite hangs). *Fix:* inject a
  latency *deliberately past* the app's deadline; bound the test with the app's own timeout + Awaitility, never an
  open-ended wait.
- **Faulting the wrong direction.** `DOWNSTREAM` faults dependency→app responses; `UPSTREAM` faults app→dependency
  requests. *Fix:* pick the `ToxicDirection` that matches the failure you mean to simulate.
- **One Toxiproxy/dependency per `@Test` method.** Slow and churns ports. *Fix:* stand them up once in
  `@BeforeClass` on a shared `Network`; reset toxics (`healed()`) between tests, not the containers.
- **Raw `proxy.toxics().timeout(...)` in a `@Test`.** *Fix:* wrap all toxic wiring in `ChaosProxy` with intent names, and name each toxic so it can be removed.
- **Treating this as production chaos engineering.** *Fix:* deterministic toxic in a test ≠ GameDay on a live
  cluster — see the boundary note; route prod-chaos requests to Gremlin/Litmus/Chaos Mesh.

## Examples

**Composing with the dependency families.** The thing you fault is stood up by Testcontainers
(`ToxiproxyContainer` next to a `PostgreSQLContainer` / `KafkaContainer` on a shared `Network`); the dependency
itself is exercised happy-path by `qa-java:db-testcontainers` / `qa-java:messaging-testing`. Chaos adds the proxy in
front and asserts the resilience layer — it **composes** with those skills, it doesn't replace them. A
data-driven fault matrix (toxic × parameter) binds cleanly via `qa-java:data-driven-testing`.
