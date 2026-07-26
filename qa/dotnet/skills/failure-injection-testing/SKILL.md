---
name: qa-failure-injection-testing-dotnet
description: Use when writing fault-injection / resilience tests in .NET 10 (8-9) / NUnit with Toxiproxy via Testcontainers (`Toxiproxy.Net`) — inject latency, drops, and bandwidth caps on a dependency (DB, API, broker, cache) and assert the app degrades gracefully. Triggers "test the app survives a slow database", "inject a connection drop", "assert the circuit breaker opens". Not for load/throughput testing (`performance/nbomber`).
---

# QA — Chaos / Fault-Injection Testing (.NET 8 / Toxiproxy + Testcontainers + NUnit)

Scaffolds **fault-injection resilience tests** in .NET against a deployed service and its dependencies, using
[**Toxiproxy**](https://github.com/Shopify/toxiproxy) — Shopify's TCP fault-injection proxy — stood up via the
`Testcontainers.Toxiproxy` `ToxiproxyContainer` and driven by the `Toxiproxy.Net` client. It is the **inverse** of
every happy-path skill in this library: the REST/gRPC authors assert *the dependency answered correctly*; a chaos
test **breaks the dependency on purpose and asserts the app under test copes**.

This is the **.NET port of the canonical** `qa/java/skills/failure-injection-testing`. The four ideas, the proxy-between mechanism, and
the steady→inject→degraded→remove→recovered lifecycle are identical; only the client lib (`Toxiproxy.Net`), the
resilience library (**Polly**), and the runner (NUnit) change.

> **The discipline this skill encodes** — four ideas that separate a correct chaos test from a happy-path reflex:
>
> 1. **A chaos test does NOT assert the dependency works — it INJECTS a fault and asserts the app DEGRADES
>    GRACEFULLY.** The happy-path reflex "assert the call succeeded" is *exactly wrong* here. You add a **toxic**
>    (latency, bandwidth cap, `Timeout`, `ResetPeer`, sliced/partial response) to the dependency connection and
>    assert the app **retries / trips a circuit breaker / honors a timeout / serves a fallback** — the
>    failure-handling path normal tests never exercise.
> 2. **The proxy sits BETWEEN the app and the dependency — point the app at the proxy port, not the real
>    dependency.** Toxiproxy is a TCP proxy with a *listen* side (the app connects here) and an *upstream* side (the
>    real DB/API/broker). The app's connection string / base URL is rewired to `container.Host:mappedPort` so
>    **all** its traffic to that dependency flows through a fault point you control.
> 3. **Toxics are added and removed at runtime over the REST API — every test is a lifecycle.** `steady-state →
>    inject → assert degraded → remove → assert recovery.` Toxiproxy's control API (port 8474) lets you mutate the
>    fault mid-test via `proxy.Add(...)` / `proxy.RemoveToxic(...)`, so one test proves **both** that the app
>    degrades under fault **and** that it heals once the fault clears.
> 4. **Assert the resilience PATTERN, not the fault.** Assert the **behaviour it provokes**: the retry count, the
>    Polly circuit-breaker state transition (Closed → Open → HalfOpen → Closed), the honored timeout (fails *fast*,
>    not hangs), the fallback payload served. This is what `qa-network-mocking-dotnet` can *observe* but
>    never *inject* — observe vs break.

## Decision matrix — fault scenario → toxic → what you assert

| You want to prove | Inject (toxic) | Assert (the resilience pattern) |
|---|---|---|
| **App survives a slow dependency** | `Latency` (+ `Jitter`), Downstream | the call completes within the app's timeout via retry/fallback, OR fails *fast* — never hangs |
| **A timeout is honored (no hang)** | `Timeout` (ms) or large `Latency` > the app's deadline | the call fails as a *timeout* inside the budget; the path returns an error/fallback, not a 30s hang |
| **A circuit breaker opens under sustained failure** | `Timeout` / `ResetPeer` held across N calls | the Polly breaker goes **Closed → Open**; later calls short-circuit (`BrokenCircuitException`) without hitting the dependency |
| **The breaker recovers when the dependency heals** | inject, drive calls to Open, then **`RemoveToxic`** | after the break duration the breaker goes **Open → HalfOpen → Closed**; calls succeed again (lifecycle) |
| **Retry-with-backoff fires the contracted number of times** | `ResetPeer` / `Timeout` on the first N attempts | the app makes exactly *MaxRetryAttempts* tries (assert via upstream call count or Polly telemetry), then succeeds or falls back |
| **A fallback is served, not an error page** | `Timeout` / connection cut | the degraded response is the contracted fallback (cached value, default, friendly message) |
| **A partial / garbled response is handled** | `Slicer` (fragment) or `LimitData` (cut after N bytes) | the app surfaces a parse/IO error and recovers — does NOT persist a truncated record or corrupt state |
| **Bandwidth starvation degrades, not crashes** | `Bandwidth` (KB/s) Downstream | the app stays responsive (timeout/fallback) under a throttled backend (distinct from device-network conditioning) |
| **Probabilistic / flappy faults** | any toxic with `Toxicity = 0.3` | the app tolerates an intermittent fault — retries smooth over the fraction that fail |

## Stack

- .NET 8, **NUnit** (the global default .NET runner) + **FluentAssertions** + **Allure.NUnit**
- **Testcontainers .NET** — `Testcontainers` + `Testcontainers.Toxiproxy` (the `ToxiproxyContainer`) + the
  dependency module (e.g. `Testcontainers.PostgreSql`)
- **Toxiproxy.Net** — `Connection`, `Client`, `Proxy`, the typed toxics (`LatencyToxic`, `TimeoutToxic`,
  `ResetPeerToxic`, `BandwidthToxic`, `LimitDataToxic`, `SlicerToxic`), `ToxicDirection`
- **Polly** (`Polly` / `Microsoft.Extensions.Http.Resilience`) — the resilience patterns under test; assert their
  effects / circuit state
- Layout: `Tests/<Dep>/` (the fault tests), `Tests/Support/Chaos/` (the `ChaosProxy` helper + `BaseChaosTest`
  container lifecycle)

```xml
<!-- Tests.csproj (excerpt) -->
<ItemGroup>
  <PackageReference Include="Testcontainers" Version="4.1.0" />
  <PackageReference Include="Testcontainers.Toxiproxy" Version="4.1.0" />
  <PackageReference Include="Testcontainers.PostgreSql" Version="4.1.0" />
  <PackageReference Include="Toxiproxy.Net" Version="2.1.0" />
  <PackageReference Include="Polly" Version="8.5.0" />
  <PackageReference Include="NUnit" Version="4.2.2" />
  <PackageReference Include="FluentAssertions" Version="6.12.1" />
</ItemGroup>
```

> **Why a proxy and not a mock?** A mock (e.g. WireMock.Net) makes the *dependency* return a canned
> error at the application layer; a Toxiproxy toxic faults the *transport* — latency, a dropped TCP connection, a
> half-sent response — the failures that exercise socket timeouts, connection pools, and Polly's retry/circuit
> pipelines. Mock when you control the contract and want a specific status; **fault-inject when you want to prove
> the app survives the network/dependency misbehaving**. They compose.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The toxic helper — `Support/Chaos/ChaosProxy.cs`**; **The mechanism — proxy BETWEEN app and dependency (idea #2)**.

## Inject-a-fault, assert-degradation (idea #1)

With no toxic the call succeeds; **with the toxic injected the app must fail fast or fall back — never hang**.
Assert the *degraded behaviour*, not the fault.

```csharp
namespace Tests.Db;

using System.Diagnostics;
using FluentAssertions;
using NUnit.Framework;
using Tests.Support.Chaos;

[TestFixture]
public class SlowDependencyTests : BaseChaosTest
{
    [Test]
    public async Task ShouldFailFastWhenTheDatabaseIsSlowerThanTheTimeout()
    {
        // App has a 2s query timeout; inject 5s latency so the dependency overruns it.
        Chaos.InjectLatency(5_000, 0);

        var app = OrderService.ConnectedTo(Chaos.Host, Chaos.Port);   // app talks to the PROXY

        var sw = Stopwatch.StartNew();
        var result = await app.PlaceOrderAsync("sku-1");              // must NOT hang for 5s
        sw.Stop();

        result.IsFallback.Should().BeTrue("the app degrades to a fallback under latency");
        sw.Elapsed.Should().BeLessThan(TimeSpan.FromSeconds(3), "it fails fast inside the timeout budget");
    }
}
```

> The assertion is on the **timeout being honored + a fallback served** — the resilience pattern — not on the 5s
> delay. Asserting "the call took 5s" asserts the *fault*, which proves nothing about the app.

## The full lifecycle — steady → inject → degraded → remove → recovered (idea #3)

```csharp
[Test]
public async Task ShouldDegradeUnderConnectionDropThenRecoverWhenHealed()
{
    var app = OrderService.ConnectedTo(Chaos.Host, Chaos.Port);

    // 1. steady state — no toxic, the call works.
    (await app.PlaceOrderAsync("sku-1")).IsSuccess.Should().BeTrue();

    // 2. inject — drop the connection.
    Chaos.CutConnection(0);

    // 3. assert degraded — the app serves its fallback, it does not throw an unhandled error.
    (await app.PlaceOrderAsync("sku-1")).IsFallback.Should().BeTrue("degrades while the connection is cut");

    // 4. remove — the dependency is healed.
    Chaos.Healed();

    // 5. assert recovery — calls succeed again, polling the breaker's half-open window (no Task.Delay-as-a-wait).
    await Assert.That(async () => (await app.PlaceOrderAsync("sku-1")).IsSuccess)
        .Within(TimeSpan.FromSeconds(10)).EventuallyBecomesTrue();   // bounded condition-poll helper
}
```

> Step 5 uses a bounded condition-poll (a small `EventuallyBecomesTrue` retry-until-deadline helper, e.g. backed by
> a Polly wait-and-retry), *not* `Task.Delay` — the recovery window (Polly's break duration) is a real condition to
> await, not a guessed delay.

## Assert the resilience PATTERN — circuit breaker via Polly (idea #4)

Hold a fault across several calls and assert the **circuit-breaker state machine**, not the fault.

```csharp
namespace Tests.Db;

using FluentAssertions;
using NUnit.Framework;
using Polly.CircuitBreaker;
using Tests.Support.Chaos;

[TestFixture]
public class CircuitBreakerChaosTests : BaseChaosTest
{
    [Test]
    public async Task ShouldOpenTheBreakerWhenTheDependencySustainsFailures()
    {
        var app = OrderService.ConnectedTo(Chaos.Host, Chaos.Port);

        app.CircuitState.Should().Be(CircuitState.Closed);            // steady

        Chaos.InjectTimeout(0);                                       // every call to the dependency now hangs+drops
        for (var i = 0; i < 10; i++) await app.PlaceOrderSafelyAsync("sku-1");  // drive past the threshold

        // The PATTERN: the breaker opened — later calls short-circuit WITHOUT hitting the dependency.
        app.CircuitState.Should().Be(CircuitState.Open);

        Chaos.Healed();                                              // dependency recovers
        // Open → HalfOpen → Closed once the break duration elapses and a probe succeeds.
        await Assert.That(async () =>
        {
            await app.PlaceOrderSafelyAsync("sku-1");                // a probe call in HalfOpen
            return app.CircuitState == CircuitState.Closed;
        }).Within(TimeSpan.FromSeconds(15)).EventuallyBecomesTrue();
    }
}
```

> Assert the **state transition** (Closed → Open → Closed) and the **short-circuit** (a call in Open throws
> `BrokenCircuitException` without reaching the proxy). That is the resilience contract; the `Timeout` toxic is
> merely the sustained failure that should provoke it.

## Retry count — assert exactly the contracted attempts

```csharp
[Test]
public async Task ShouldRetryExactlyThreeTimesThenFallBackOnConnectionResets()
{
    var app = OrderService.ConnectedTo(Chaos.Host, Chaos.Port);
    Chaos.CutConnection(0);                                          // every attempt's connection is reset

    var result = await app.PlaceOrderWithRetryAsync("sku-1");

    result.IsFallback.Should().BeTrue();
    // The PATTERN: bounded retries, not a runaway loop — assert the configured attempt count.
    app.LastAttemptCount.Should().Be(3, "MaxRetryAttempts is honored");
}
```

## Partial / garbled response — `Slicer` / `LimitData` (don't persist corruption)

```csharp
[Test]
public async Task ShouldRejectAndNotPersistATruncatedResponse()
{
    Chaos.TruncateAfter(64);                                         // cut every response after 64 bytes
    var app = CatalogService.ConnectedTo(Chaos.Host, Chaos.Port);

    var result = await app.LoadCatalogAsync();

    result.IsError.Should().BeTrue("a partial response surfaces as an error");
    app.LastPersistedCatalog.Should().BeNull("no truncated record persisted");
}
```

## Probabilistic faults — `Toxicity` for flappy dependencies

```csharp
[Test]
public async Task ShouldTolerateAnIntermittentlyResettingDependency()
{
    Chaos.WithToxicity(Chaos.CutConnection(0), 0.3);                // reset the connection only 30% of the time
    var app = OrderService.ConnectedTo(Chaos.Host, Chaos.Port);

    var succeeded = 0;
    for (var i = 0; i < 20; i++)
        if ((await app.PlaceOrderWithRetryAsync("sku-1")).IsSuccess) succeeded++;

    succeeded.Should().Be(20, "retries absorb an intermittent fault");
}
```

> Probabilistic faults are still **deterministic in intent** (a fixed toxicity), unlike real production chaos —
> that determinism is what makes them a *test*.

## The boundary — functional fault-injection vs production chaos engineering

This skill is **functional fault-injection inside a test**: a deterministic toxic on a dependency connection,
asserted against the app's Polly resilience pipelines, in CI. It is **not production chaos engineering** — Gremlin /
Litmus / Chaos Mesh injecting faults into a *live* cluster (pod kills, node drain, real network partitions) with
steady-state hypotheses and blast-radius control. If the request is "run a GameDay on prod" or "kill pods in the
cluster", that is out of scope — flag it and point at the chaos-engineering platforms.

## Anti-patterns

- **Asserting the dependency works (or asserting the fault).** "The call succeeded" / "the call took 5s" proves
  nothing about resilience. *Fix:* assert the app's **degraded behaviour** — retry count, breaker state, honored
  timeout, fallback content.
- **Pointing the app at the real dependency instead of the proxy.** No proxy in the path → the toxic reaches
  nothing. *Fix:* rewire the app's connection string / base URL / bootstrap server to `Chaos.Host:Chaos.Port`.
- **Injecting a toxic and never removing it.** You prove degradation but not **recovery**, and you leak the fault
  into the next test. *Fix:* run the full lifecycle — `Healed()` then assert recovery; remove in teardown.
- **`Task.Delay` / `Thread.Sleep` to wait for the breaker to open/close.** Banned by CLAUDE.md and flaky. *Fix:* a
  bounded condition-poll (`EventuallyBecomesTrue` / Polly wait-and-retry) on the real state.
- **A `Latency` so small it doesn't exceed the app's timeout** (or so large the suite hangs). *Fix:* inject latency
  *deliberately past* the app's deadline; bound the test with the app's own timeout + a condition-poll.
- **Faulting the wrong direction.** `DownStream` faults dependency→app responses; `UpStream` faults app→dependency
  requests. *Fix:* pick the `ToxicDirection` that matches the failure you mean to simulate.
- **One Toxiproxy/dependency per `[Test]`.** Slow and churns ports. *Fix:* stand them up once in `[OneTimeSetUp]` on
  a shared `Network`; reset toxics (`Healed()`) between tests, not the containers.
- **Treating this as production chaos engineering.** *Fix:* deterministic toxic in a test ≠ GameDay on a live
  cluster — route prod-chaos requests to Gremlin/Litmus/Chaos Mesh.

## Examples

**End-to-end: the inverted assertion.** A REST author writes `response.StatusCode.Should().Be(200)`. A chaos author
writes: inject `Timeout`, then `result.IsFallback.Should().BeTrue()` **and**
`app.CircuitState.Should().Be(CircuitState.Open)`. Same dependency, opposite question — *does the app survive it
failing?*

**Composing with the dependency families.** The thing you fault is stood up by Testcontainers
(`ToxiproxyContainer` next to a `PostgreSqlContainer` on a shared `Network`); the dependency itself is exercised
happy-path by `qa-db-testing-dotnet` / `qa-messaging-testing-dotnet`. Chaos adds the proxy in front and
asserts the resilience layer — it **composes**. A data-driven fault matrix binds via `qa-data-driven-testing-dotnet`.

## Rules (hard constraints)

- **The assertion is the resilience PATTERN, never the dependency working or the fault itself** — retry count,
  Polly circuit-breaker state transitions, an honored timeout (fails fast), or fallback content.
- **The app under test connects to the PROXY**, not the real dependency — rewire its connection string / base URL /
  bootstrap server to `Chaos.Host:Chaos.Port`. If the app bypasses the proxy, the test is inert.
- **Every fault test runs the lifecycle** where recovery matters: steady → inject → assert degraded → `Healed()` →
  assert recovery. Always remove injected toxics (between tests / in teardown) so faults don't leak.
- **No `Task.Delay` / `Thread.Sleep` as a wait.** Use a bounded condition-poll (`EventuallyBecomesTrue` / Polly
  wait-and-retry) on the real condition — breaker state, a successful probe call.
- **Pick the toxic + `ToxicDirection` deliberately** (latency/`Bandwidth` for slow, `Timeout`/`ResetPeer` for drop,
  `Slicer`/`LimitData` for partial; DownStream = responses, UpStream = requests).
- **One Toxiproxy + dependency per fixture** on a shared `Network` in `[OneTimeSetUp]`; reset toxics between tests,
  not the containers. Named toxics so they can be removed.
- **This is functional fault-injection, not production chaos engineering** — route live-cluster chaos elsewhere.
- **Wrap all toxic wiring in `ChaosProxy`** with intent names — no raw `proxy.Add(new TimeoutToxic …)` in `[Test]`.
  NUnit + Toxiproxy.Net + Testcontainers + FluentAssertions.

## Cross-references

- `qa-failure-injection-testing-java` · `qa-failure-injection-testing-typescript` — the sibling stacks (Toxiproxy + Testcontainers +
  resilience4j · toxiproxy-node-client + Vitest); this is the **port of the Java canonical**. Same four ideas, same
  lifecycle, different client lib + resilience library (Polly).
- `qa-network-mocking-dotnet` — the **closest neighbor and the inverse**: that stands up a MITM proxy
  (`Titanium.Web.Proxy`) to **observe/mock** out-of-browser requests; this stands up Toxiproxy to **inject transport
  faults**. Observe vs break.
- `qa-data-driven-testing-dotnet` — drive a **fault matrix** (toxic × parameter × expected pattern) via
  `[TestCaseSource]` instead of copy-pasted `[Test]` methods.
- `qa-db-testing-dotnet` · `qa-messaging-testing-dotnet` — the dependencies you fault (DB / broker
  connections through the proxy); they cover the happy path this inverts.
- `qa-realtime-stream-testing-dotnet` — shares the **lifecycle discipline** (steady → perturb → assert →
  recover) and bounded-condition waits (never `Task.Delay`-as-a-wait).
- `qa-load-testing-dotnet` — behaviour under **load/volume** vs behaviour under **fault** (this skill).
- `qa-test-reports-dotnet` — render each fault scenario as a named result.
