---
name: qa-chaos-testing-java
description: >-
  Write **fault-injection / resilience** tests in Java 21 with **Toxiproxy** (Shopify's TCP fault-injection
  proxy) + the **Testcontainers `ToxiproxyContainer`** + **toxiproxy-java** client + TestNG, proving the app under
  test **degrades gracefully** when a dependency (DB, HTTP API, broker, cache) misbehaves. Covers the trait that
  makes a chaos test the inverse of every other test: **you do NOT assert the dependency works — you INJECT a fault
  into the connection (latency, bandwidth cap, connection drop, timeout, partial/sliced response) and assert the
  app RETRIES / TRIPS A CIRCUIT BREAKER / HONORS A TIMEOUT / FALLS BACK instead of hanging, crashing, or corrupting
  state** ("assert the call succeeded" is the wrong reflex here). The mechanism: **Toxiproxy sits as a TCP proxy
  BETWEEN the app and its dependency — you point the app's connection string at the proxy listen port, not the real
  dependency** — and **toxics are added/removed at runtime over the REST API** so each test runs a lifecycle:
  **steady-state → inject the toxic → assert degraded behaviour → remove the toxic → assert recovery.** Covers the
  toxic types (`latency`+jitter, `bandwidth`, `timeout`, `reset_peer`, `slow_close`, `slicer`, `limitData`), the
  upstream/downstream **`ToxicDirection`**, the **`toxicity`** probability, asserting the **resilience pattern**
  (retry count, circuit-breaker open/half-open/closed via resilience4j, timeout honored, fallback served) not the
  fault, partial failures via `slicer`/`limitData`, and standing the dependency + proxy up with Testcontainers on a
  shared `Network`. Triggers: "test our app survives the database going slow", "inject latency / a connection drop
  and assert the circuit breaker opens", "assert the retry/fallback fires when the API times out", "Toxiproxy
  resilience test in Java", "add a fault-injection test with Testcontainers". Do NOT use for: the .NET stack (use
  qa-chaos-testing-dotnet), the TypeScript stack (use qa-chaos-testing-typescript), merely **observing/mocking**
  out-of-browser requests (use qa-network-monitoring-proxy-java — observe vs inject), conditioning the **device /
  client** network in a UI/mobile run (use qa-cloud-grid-config-java / qa-mobile-device-farm-java), standing
  dependencies up without faulting them (use qa-test-environments-java), **load/volume** testing (use
  qa-performance-gatling-java), or **production chaos engineering** on a live cluster (Gremlin / Litmus / Chaos Mesh
  — out of scope; this skill is functional fault-injection in a test).
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
>    drain-then-assert lifecycle of `qa-websocket-sse-testing-java`, applied to faults).
> 4. **Assert the resilience PATTERN, not the fault.** The toxic is the *given*, not the assertion. Assert the
>    **behaviour it provokes**: the retry count, the circuit-breaker state transition (closed → open → half-open →
>    closed via resilience4j), the honored timeout (fails *fast*, not hangs), the fallback payload served. This is
>    what `qa-network-monitoring-proxy-java` can *observe* but never *inject* — observe vs break.

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
  `ToxiproxyContainer` module) + the dependency module (e.g. `:postgresql`, `:kafka`) — `qa-test-environments-java`
- **toxiproxy-java** (`eu.rekawek.toxiproxy:toxiproxy-java`) — `ToxiproxyClient`, `Proxy`, `proxy.toxics()`,
  `ToxicDirection`
- **resilience4j** (`io.github.resilience4j:resilience4j-circuitbreaker` / `-retry` / `-timelimiter`) — the
  resilience patterns under test; assert their state/metrics (or assert your own retry/circuit code's effects)
- Layout: `src/test/java/<dep>/` (the fault tests), `src/test/java/support/chaos/` (the `ChaosProxy` helper +
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
    testImplementation("io.qameta.allure:allure-testng:2.29.0")
}
```

> **Why a proxy and not a mock?** A mock (`qa-api-mocking-wiremock-java`) makes the *dependency* return a canned
> error at the application layer; a Toxiproxy toxic faults the *transport* — latency, a dropped TCP connection, a
> half-sent response — the failures that exercise socket timeouts, connection pools, and retry/circuit code. Mock
> when you control the contract and want a specific status; **fault-inject when you want to prove the app survives
> the network/dependency misbehaving**. They compose: a WireMock upstream behind a Toxiproxy listener faults the
> transport to a controllable contract.

## The mechanism — proxy BETWEEN app and dependency (idea #2)

Stand the dependency and Toxiproxy up on a **shared Docker `Network`**, create a proxy whose **upstream** is the
dependency and whose **listen** side is what the app connects to, then **point the app at the proxy's mapped
port**. Everything downstream flows through the fault point.

```java
package support.chaos;

import eu.rekawek.toxiproxy.Proxy;
import eu.rekawek.toxiproxy.ToxiproxyClient;
import org.testcontainers.containers.Network;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.ToxiproxyContainer;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;

import java.io.IOException;

/** Stands the dependency + Toxiproxy up on one Network and exposes the proxied connection point. */
public abstract class BaseChaosTest {
    private static final Network NETWORK = Network.newNetwork();

    protected static PostgreSQLContainer<?> dependency;       // the dependency under fault (example)
    protected static ToxiproxyContainer toxiproxy;
    protected ChaosProxy chaos;                               // the intent-named toxic helper

    @BeforeClass(alwaysRun = true)
    public void startInfrastructure() throws IOException {
        dependency = new PostgreSQLContainer<>("postgres:16-alpine")
                .withNetwork(NETWORK)
                .withNetworkAliases("db");                    // the upstream host on the shared network
        toxiproxy = new ToxiproxyContainer("ghcr.io/shopify/toxiproxy:2.11.0")
                .withNetwork(NETWORK);
        dependency.start();
        toxiproxy.start();

        ToxiproxyClient client = new ToxiproxyClient(toxiproxy.getHost(), toxiproxy.getControlPort());
        // listen on 8666 inside the proxy; upstream = the dependency by its network alias + internal port.
        Proxy proxy = client.createProxy("db", "0.0.0.0:8666", "db:5432");

        // The app connects HERE — the proxy's mapped listen port, NOT the real dependency's port.
        String proxiedHost = toxiproxy.getHost();
        int proxiedPort = toxiproxy.getMappedPort(8666);
        chaos = new ChaosProxy(proxy, proxiedHost, proxiedPort);
    }

    @AfterClass(alwaysRun = true)
    public void stopInfrastructure() {
        if (toxiproxy != null) toxiproxy.stop();
        if (dependency != null) dependency.stop();
    }
}
```

> The app under test must be configured to talk to `chaos.host():chaos.port()` (the JDBC URL / base URL / broker
> bootstrap server pointed at the proxy), **not** the dependency directly. That redirection *is* the chaos setup —
> if the app bypasses the proxy, no toxic can reach it.

## The toxic helper — `support/chaos/ChaosProxy.java`

One helper owns the proxy handle and exposes **intent-named** fault operations and a **lifecycle** primitive, so
tests read `chaos.injectLatency(...)`, `chaos.cutConnection()`, `chaos.healed()` — never raw
`proxy.toxics().timeout(...)` scattered across `@Test` methods. Each injected toxic is named so it can be removed.

```java
package support.chaos;

import eu.rekawek.toxiproxy.Proxy;
import eu.rekawek.toxiproxy.model.Toxic;
import eu.rekawek.toxiproxy.model.ToxicDirection;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/** Intent-named fault injection over a single Toxiproxy proxy, with a remove-all "heal" for the lifecycle. */
public final class ChaosProxy {
    private final Proxy proxy;
    private final String host;
    private final int port;
    private final List<String> injected = new ArrayList<>();

    public ChaosProxy(Proxy proxy, String host, int port) {
        this.proxy = proxy; this.host = host; this.port = port;
    }

    public String host() { return host; }   // the app points its connection string here…
    public int port()    { return port; }   // …and at this port

    /** Slow every response by `millis` (+ jitter) — the "dependency is slow" fault. */
    public Toxic injectLatency(long millis, long jitter) throws IOException {
        Toxic t = proxy.toxics().latency("latency", ToxicDirection.DOWNSTREAM, millis).setJitter(jitter);
        injected.add("latency");
        return t;
    }

    /** Stop all data and close the connection after `millis` — the "dependency hangs then drops" fault. */
    public void injectTimeout(long millis) throws IOException {
        proxy.toxics().timeout("timeout", ToxicDirection.UPSTREAM, millis);
        injected.add("timeout");
    }

    /** Reset the TCP peer after `millis` — the "connection dropped" fault that exercises retry/breaker code. */
    public Toxic cutConnection(long millis) throws IOException {
        Toxic t = proxy.toxics().resetPeer("reset", ToxicDirection.DOWNSTREAM, millis);
        injected.add("reset");
        return t;
    }

    /** Throttle the backend dependency to `rateKbps` KB/s — bandwidth starvation (NOT device conditioning). */
    public void throttle(long rateKbps) throws IOException {
        proxy.toxics().bandwidth("bw", ToxicDirection.DOWNSTREAM, rateKbps);
        injected.add("bw");
    }

    /** Cut the response after `bytes` — a partial/truncated response the app must not persist as valid. */
    public void truncateAfter(long bytes) throws IOException {
        proxy.toxics().limitData("limit", ToxicDirection.DOWNSTREAM, bytes);
        injected.add("limit");
    }

    /** Make a toxic probabilistic (0..1) for an intermittent/flappy fault. */
    public Toxic withToxicity(Toxic toxic, float toxicity) throws IOException {
        toxic.setToxicity(toxicity);
        return toxic;
    }

    /** Remove ALL injected toxics — the dependency is "healed" (lifecycle step: assert recovery after this). */
    public void healed() throws IOException {
        for (String name : injected) proxy.toxics().get(name).remove();
        injected.clear();
    }
}
```

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
        // App is configured with a 2s query timeout; inject 5s latency so the dependency overruns it.
        chaos.injectLatency(5_000, 0);

        OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());  // app talks to the PROXY

        Instant start = Instant.now();
        OrderResult result = app.placeOrder("sku-1");          // must NOT hang for 5s
        Duration elapsed = Duration.between(start, Instant.now());

        assertThat(result.isFallback()).as("degrades to fallback under latency").isTrue();
        assertThat(elapsed).as("fails fast inside the timeout budget").isLessThan(Duration.ofSeconds(3));
    }
}
```

> The assertion is on the **timeout being honored + a fallback served** — the resilience pattern — not on the 5s
> delay. A test that asserts "the call took 5s" is asserting the *fault*, which proves nothing about the app.

## The full lifecycle — steady → inject → degraded → remove → recovered (idea #3)

One test proves the app **degrades under fault and heals when it clears**. This is the chaos analogue of the
drain-then-assert lifecycle in `qa-websocket-sse-testing-java`.

```java
@Test
public void shouldDegradeUnderConnectionDropThenRecoverWhenHealed() throws Exception {
    OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());

    // 1. steady state — no toxic, the call works.
    assertThat(app.placeOrder("sku-1").isSuccess()).isTrue();

    // 2. inject — drop the connection.
    chaos.cutConnection(0);

    // 3. assert degraded — the app serves its fallback, it does not throw an unhandled error.
    assertThat(app.placeOrder("sku-1").isFallback()).as("degrades while the connection is cut").isTrue();

    // 4. remove — the dependency is healed.
    chaos.healed();

    // 5. assert recovery — calls succeed again (await the breaker's half-open window, never Thread.sleep).
    Awaitility.await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
        .untilAsserted(() -> assertThat(app.placeOrder("sku-1").isSuccess()).isTrue());
}
```

> Step 5 uses **Awaitility** (a bounded condition-poll), *not* `Thread.sleep` — the recovery window (e.g.
> resilience4j's `waitDurationInOpenState`) is a real condition to await, not a guessed delay.

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

        assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.CLOSED);   // steady

        chaos.injectTimeout(0);                                 // every call to the dependency now hangs+drops
        for (int i = 0; i < 10; i++) app.placeOrderSafely("sku-1");  // drive enough calls past the threshold

        // The PATTERN: the breaker opened — later calls short-circuit WITHOUT hitting the dependency.
        assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.OPEN);

        chaos.healed();                                        // dependency recovers
        // OPEN → HALF_OPEN → CLOSED once the wait window elapses and a probe succeeds.
        Awaitility.await().atMost(Duration.ofSeconds(15))
            .untilAsserted(() -> {
                app.placeOrderSafely("sku-1");                 // a probe call in HALF_OPEN
                assertThat(breaker.getState()).isEqualTo(CircuitBreaker.State.CLOSED);
            });
    }
}
```

> Assert the **state transition** (CLOSED → OPEN → CLOSED) and the **short-circuit** (a call in OPEN throws
> `CallNotPermittedException` without reaching the proxy). That is the resilience contract; the `timeout` toxic is
> merely the sustained failure that should provoke it.

## Retry count — assert exactly the contracted attempts

A `reset_peer` on the connection makes attempts fail; assert the app makes **exactly** the contracted number of
tries (via the resilience4j `Retry` metrics, or by counting calls that reach the upstream), then succeeds/falls
back — not infinite, not one.

```java
@Test
public void shouldRetryExactlyThreeTimesThenFallBackOnConnectionResets() throws Exception {
    OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());
    chaos.cutConnection(0);                                   // every attempt's connection is reset

    OrderResult result = app.placeOrderWithRetry("sku-1");

    assertThat(result.isFallback()).isTrue();
    // The PATTERN: bounded retries, not a runaway loop — assert the configured attempt count.
    assertThat(app.retryMetrics().getNumberOfFailedCallsWithRetryAttempt()).isEqualTo(1);
    assertThat(app.lastAttemptCount()).as("maxAttempts honored").isEqualTo(3);
}
```

## Partial / garbled response — `slicer` / `limitData` (don't persist corruption)

A response cut mid-stream must surface as an error the app handles — it must **not** be parsed and persisted as a
valid (truncated) record. Inject `limitData` (cut after N bytes) or `slicer` (fragment the stream), drive a read,
and assert the app rejects the partial result and leaves state uncorrupted.

```java
@Test
public void shouldRejectAndNotPersistATruncatedResponse() throws Exception {
    chaos.truncateAfter(64);                                  // cut every response after 64 bytes
    CatalogService app = CatalogService.connectedTo(chaos.host(), chaos.port());

    CatalogResult result = app.loadCatalog();

    assertThat(result.isError()).as("partial response surfaces as an error").isTrue();
    assertThat(app.lastPersistedCatalog()).as("no truncated record persisted").isNull();
}
```

## Probabilistic faults — `toxicity` for flappy dependencies

A `toxicity` below 1.0 applies the toxic to only a *fraction* of connections — an intermittent, flappy dependency.
Assert the app's retries smooth over the failing fraction so the user-visible outcome stays correct.

```java
@Test
public void shouldTolerateAnIntermittentlyResettingDependency() throws Exception {
    chaos.withToxicity(chaos.cutConnection(0), 0.3f);       // reset the connection only 30% of the time
    OrderService app = OrderService.connectedTo(chaos.host(), chaos.port());

    // 20 calls; with retry-with-backoff the user-visible success rate should be ~100% despite a 30% fault rate.
    long succeeded = java.util.stream.IntStream.range(0, 20)
        .filter(i -> app.placeOrderWithRetry("sku-1").isSuccess()).count();

    assertThat(succeeded).as("retries absorb an intermittent fault").isEqualTo(20);
}
```

> Probabilistic faults are still **deterministic in intent** (a fixed toxicity), unlike real production chaos —
> that determinism is what makes them a *test*. For true randomized cluster chaos, see the boundary note below.

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
- **Treating this as production chaos engineering.** *Fix:* deterministic toxic in a test ≠ GameDay on a live
  cluster — see the boundary note; route prod-chaos requests to Gremlin/Litmus/Chaos Mesh.
- **Using a toxic where a mock fits.** Want a specific HTTP 503 from a contract? *Fix:* `qa-api-mocking-wiremock-java`.
  Toxiproxy is for **transport** faults (latency/drop/partial), not application-layer canned responses.

## Examples

**End-to-end: the inverted assertion.** A REST author writes `assertThat(response.statusCode()).isEqualTo(200)`. A
chaos author writes: inject `timeout`, then `assertThat(result.isFallback()).isTrue()` **and**
`assertThat(breaker.getState()).isEqualTo(OPEN)`. Same dependency, opposite question — *does the app survive it
failing?*

**Composing with the dependency families.** The thing you fault is stood up by `qa-test-environments-java`
(`ToxiproxyContainer` next to a `PostgreSQLContainer` / `KafkaContainer` on a shared `Network`); the dependency
itself is exercised happy-path by `qa-db-testing-java` / `qa-messaging-testing-kafka-java`. Chaos adds the proxy in
front and asserts the resilience layer — it **composes** with those skills, it doesn't replace them. A
data-driven fault matrix (toxic × parameter) binds cleanly via `qa-data-driven-testing-java`.

## Rules (hard constraints)

- **The assertion is the resilience PATTERN, never the dependency working or the fault itself.** Assert retry
  count, circuit-breaker state transitions, an honored timeout (fails fast), or fallback content. "Assert the call
  succeeded" is the wrong reflex here.
- **The app under test connects to the PROXY**, not the real dependency — rewire its connection string / base URL /
  bootstrap server to `chaos.host():chaos.port()`. If the app bypasses the proxy, the test is inert.
- **Every fault test runs the lifecycle** where recovery matters: steady → inject → assert degraded → `healed()`
  (remove) → assert recovery. Always remove injected toxics (between tests / in teardown) so faults don't leak.
- **No `Thread.sleep`.** Wait on real conditions with **Awaitility** (`await().atMost(...).untilAsserted(...)`) —
  breaker state, a successful probe call. A timeout/latency toxic is an *injected delay*, not a test wait.
- **Pick the toxic + `ToxicDirection` deliberately** to match the failure (latency/`bandwidth` for slow,
  `timeout`/`reset_peer` for drop, `slicer`/`limitData` for partial; DOWNSTREAM = responses, UPSTREAM = requests).
- **One Toxiproxy + dependency per suite** on a shared `Network` in `@BeforeClass`; reset toxics between tests, not
  the containers. Named toxics so they can be removed.
- **This is functional fault-injection, not production chaos engineering** — deterministic toxic in CI; route
  live-cluster chaos (Gremlin/Litmus/Chaos Mesh) elsewhere.
- **Wrap all toxic wiring in `ChaosProxy`** with intent names — no raw `proxy.toxics().timeout(...)` in `@Test`.
  TestNG + toxiproxy-java + Testcontainers + AssertJ + Awaitility.

## Cross-references

- `qa-chaos-testing-dotnet` · `qa-chaos-testing-typescript` — the sibling stacks (`Toxiproxy.Net` + Polly ·
  `toxiproxy-node-client` + Vitest); same four ideas, same lifecycle, different client lib + resilience library.
- `qa-network-monitoring-proxy-java` (#10) — the **closest neighbor and the inverse**: that stands up a MITM proxy
  to **observe/mock** out-of-browser requests; this stands up Toxiproxy to **inject transport faults**. Observe vs
  break. Read it for the proxy-in-the-middle model; draw the boundary cleanly.
- `qa-test-environments-java` (#14) — the **Testcontainers spine** the `ToxiproxyContainer` plugs into: stand the
  dependency up, put the proxy in front on a shared `Network`, point the app at the proxy port.
- `qa-api-mocking-wiremock-java` (#22) — **application-layer** canned responses (a specific 503) vs **transport**
  faults (latency/drop/partial). They compose: a WireMock upstream behind a Toxiproxy listener.
- `qa-data-driven-testing-java` (#39) — drive a **fault matrix** (toxic × parameter × expected pattern) via
  row-binding instead of copy-pasted `@Test` methods.
- `qa-db-testing-java` · `qa-messaging-testing-kafka-java` · `qa-messaging-testing-rabbitmq-java` — the
  dependencies you fault (DB / broker connections through the proxy); they cover the happy path this inverts.
- `qa-websocket-sse-testing-java` (#37) — shares the **lifecycle discipline** (steady → perturb → assert → recover)
  and bounded-condition waits (Awaitility, never sleep).
- `qa-performance-gatling-java` — behaviour under **load/volume** vs behaviour under **fault** (this skill); they
  answer different questions.
- `qa-allure-reporting-java` — render each fault scenario as a named result.
