---
name: qa-chaos-testing-dotnet
description: >-
  Write **fault-injection / resilience** tests in .NET 8 with **Toxiproxy** (Shopify's TCP fault-injection proxy)
  + the **Testcontainers `ToxiproxyContainer`** (`Testcontainers.Toxiproxy`) + the **Toxiproxy.Net** client +
  **NUnit**, proving the app under test **degrades gracefully** when a dependency (DB, HTTP API, broker, cache)
  misbehaves. Covers the trait that makes a chaos test the inverse of every other test: **you do NOT assert the
  dependency works — you INJECT a fault into the connection (latency, bandwidth cap, connection drop, timeout,
  partial/sliced response) and assert the app RETRIES / TRIPS A CIRCUIT BREAKER / HONORS A TIMEOUT / FALLS BACK
  instead of hanging, crashing, or corrupting state** ("assert the call succeeded" is the wrong reflex here). The
  mechanism: **Toxiproxy sits as a TCP proxy BETWEEN the app and its dependency — you point the app's connection
  string at the proxy listen port, not the real dependency** — and **toxics are added/removed at runtime over the
  REST API** so each test runs a lifecycle: **steady-state → inject the toxic → assert degraded behaviour → remove
  the toxic → assert recovery.** Covers the toxic types (`Latency`+jitter, `Bandwidth`, `Timeout`, `ResetPeer`,
  `SlowClose`, `Slicer`, `LimitData`), the upstream/downstream **`ToxicDirection`**, the **`Toxicity`** probability,
  asserting the **resilience pattern** (retry count, circuit-breaker Closed/Open/HalfOpen via **Polly**, timeout
  honored, fallback served) not the fault, partial failures via `Slicer`/`LimitData`, and standing the dependency +
  proxy up with Testcontainers on a shared `Network`. Triggers: "test our .NET app survives the database going
  slow", "inject latency / a connection drop and assert the Polly circuit breaker opens", "assert the retry/fallback
  fires when the API times out", "Toxiproxy resilience test in C#", "add a fault-injection test with Testcontainers
  .NET". Do NOT use for: the Java stack (use qa-chaos-testing-java), the TypeScript stack (use
  qa-chaos-testing-typescript), merely **observing/mocking** out-of-browser requests (use
  qa-network-monitoring-proxy-dotnet — observe vs inject), conditioning the **device / client** network in a
  UI/mobile run (use qa-cloud-grid-config-dotnet), standing dependencies up without faulting them (use
  qa-test-environments-dotnet), **load/volume** testing (use qa-performance-nbomber-dotnet), or **production chaos
  engineering** on a live cluster (Gremlin / Litmus / Chaos Mesh — out of scope; this skill is functional
  fault-injection in a test).
---

# QA — Chaos / Fault-Injection Testing (.NET 8 / Toxiproxy + Testcontainers + NUnit)

Scaffolds **fault-injection resilience tests** in .NET against a deployed service and its dependencies, using
[**Toxiproxy**](https://github.com/Shopify/toxiproxy) — Shopify's TCP fault-injection proxy — stood up via the
`Testcontainers.Toxiproxy` `ToxiproxyContainer` and driven by the `Toxiproxy.Net` client. It is the **inverse** of
every happy-path skill in this library: the REST/gRPC authors assert *the dependency answered correctly*; a chaos
test **breaks the dependency on purpose and asserts the app under test copes**.

This is the **.NET port of the canonical** `qa/java/skills/chaos-testing`. The four ideas, the proxy-between mechanism, and
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
>    not hangs), the fallback payload served. This is what `qa-network-monitoring-proxy-dotnet` can *observe* but
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
  dependency module (e.g. `Testcontainers.PostgreSql`) — `qa-test-environments-dotnet`
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

> **Why a proxy and not a mock?** A mock (`qa-api-mocking-wiremock-dotnet`) makes the *dependency* return a canned
> error at the application layer; a Toxiproxy toxic faults the *transport* — latency, a dropped TCP connection, a
> half-sent response — the failures that exercise socket timeouts, connection pools, and Polly's retry/circuit
> pipelines. Mock when you control the contract and want a specific status; **fault-inject when you want to prove
> the app survives the network/dependency misbehaving**. They compose.

## The mechanism — proxy BETWEEN app and dependency (idea #2)

Stand the dependency and Toxiproxy up on a **shared Docker `Network`**, create a proxy whose **upstream** is the
dependency and whose **listen** side is what the app connects to, then **point the app at the proxy's mapped
port**.

```csharp
namespace Tests.Support.Chaos;

using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Networks;
using Testcontainers.PostgreSql;
using Testcontainers.Toxiproxy;
using Toxiproxy.Net;
using Toxiproxy.Net.Toxics;

public abstract class BaseChaosTest
{
    private static readonly INetwork Network = new NetworkBuilder().Build();

    protected static PostgreSqlContainer Dependency = null!;   // the dependency under fault (example)
    protected static ToxiproxyContainer Toxiproxy = null!;
    protected ChaosProxy Chaos = null!;                        // the intent-named toxic helper

    [OneTimeSetUp]
    public async Task StartInfrastructure()
    {
        Dependency = new PostgreSqlBuilder()
            .WithImage("postgres:16-alpine")
            .WithNetwork(Network)
            .WithNetworkAliases("db")                          // the upstream host on the shared network
            .Build();
        Toxiproxy = new ToxiproxyBuilder()
            .WithImage("ghcr.io/shopify/toxiproxy:2.11.0")
            .WithNetwork(Network)
            .Build();
        await Dependency.StartAsync();
        await Toxiproxy.StartAsync();

        var connection = new Connection(Toxiproxy.Hostname, Toxiproxy.GetMappedPublicPort(ToxiproxyBuilder.ControlPort));
        var client = connection.Client();
        var proxy = client.Add(new Proxy
        {
            Name = "db",
            Listen = "0.0.0.0:8666",                           // proxy listen side
            Upstream = "db:5432",                              // the dependency by its network alias + internal port
            Enabled = true,
        });

        // The app connects HERE — the proxy's mapped listen port, NOT the real dependency's port.
        var proxiedHost = Toxiproxy.Hostname;
        var proxiedPort = Toxiproxy.GetMappedPublicPort(8666);
        Chaos = new ChaosProxy(proxy, proxiedHost, proxiedPort);
    }

    [OneTimeTearDown]
    public async Task StopInfrastructure()
    {
        if (Toxiproxy is not null) await Toxiproxy.DisposeAsync();
        if (Dependency is not null) await Dependency.DisposeAsync();
    }
}
```

> The app under test must be configured to talk to `Chaos.Host:Chaos.Port` (the connection string / base URL /
> bootstrap server pointed at the proxy), **not** the dependency directly. That redirection *is* the chaos setup.

## The toxic helper — `Support/Chaos/ChaosProxy.cs`

One helper owns the proxy handle and exposes **intent-named** fault operations and a **heal** for the lifecycle, so
tests read `Chaos.InjectLatency(...)`, `Chaos.CutConnection()`, `Chaos.Healed()` — never raw `proxy.Add(new
TimeoutToxic { ... })` scattered across `[Test]` methods. Each injected toxic is named so it can be removed.

```csharp
namespace Tests.Support.Chaos;

using Toxiproxy.Net;
using Toxiproxy.Net.Toxics;

/// Intent-named fault injection over a single Toxiproxy proxy, with a remove-all "heal" for the lifecycle.
public sealed class ChaosProxy(Proxy proxy, string host, int port)
{
    private readonly List<string> _injected = [];

    public string Host => host;   // the app points its connection string here…
    public int Port => port;      // …and at this port

    /// Slow every response by `millis` (+ jitter) — the "dependency is slow" fault.
    public ToxicBase InjectLatency(int millis, int jitter) =>
        Add(new LatencyToxic { Name = "latency", Stream = ToxicDirection.DownStream,
            Attributes = { Latency = millis, Jitter = jitter } });

    /// Stop all data and close the connection after `millis` — the "dependency hangs then drops" fault.
    public ToxicBase InjectTimeout(int millis) =>
        Add(new TimeoutToxic { Name = "timeout", Stream = ToxicDirection.UpStream,
            Attributes = { Timeout = millis } });

    /// Reset the TCP peer after `millis` — the "connection dropped" fault that exercises retry/breaker code.
    public ToxicBase CutConnection(int millis) =>
        Add(new ResetPeerToxic { Name = "reset", Stream = ToxicDirection.DownStream,
            Attributes = { Timeout = millis } });

    /// Throttle the backend dependency to `rateKbps` KB/s — bandwidth starvation (NOT device conditioning).
    public ToxicBase Throttle(int rateKbps) =>
        Add(new BandwidthToxic { Name = "bw", Stream = ToxicDirection.DownStream,
            Attributes = { Rate = rateKbps } });

    /// Cut the response after `bytes` — a partial/truncated response the app must not persist as valid.
    public ToxicBase TruncateAfter(int bytes) =>
        Add(new LimitDataToxic { Name = "limit", Stream = ToxicDirection.DownStream,
            Attributes = { Bytes = bytes } });

    /// Make a toxic probabilistic (0..1) for an intermittent/flappy fault.
    public ToxicBase WithToxicity(ToxicBase toxic, double toxicity)
    {
        toxic.Toxicity = toxicity;
        proxy.UpdateToxic(toxic.Name, toxic);
        return toxic;
    }

    /// Remove ALL injected toxics — the dependency is "healed" (lifecycle step: assert recovery after this).
    public void Healed()
    {
        foreach (var name in _injected) proxy.RemoveToxic(name);
        _injected.Clear();
    }

    private ToxicBase Add(ToxicBase toxic)
    {
        proxy.Add(toxic);
        _injected.Add(toxic.Name);
        return toxic;
    }
}
```

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
- **Using a toxic where a mock fits.** Want a specific HTTP 503 from a contract? *Fix:*
  `qa-api-mocking-wiremock-dotnet`. Toxiproxy is for **transport** faults, not application-layer canned responses.

## Examples

**End-to-end: the inverted assertion.** A REST author writes `response.StatusCode.Should().Be(200)`. A chaos author
writes: inject `Timeout`, then `result.IsFallback.Should().BeTrue()` **and**
`app.CircuitState.Should().Be(CircuitState.Open)`. Same dependency, opposite question — *does the app survive it
failing?*

**Composing with the dependency families.** The thing you fault is stood up by `qa-test-environments-dotnet`
(`ToxiproxyContainer` next to a `PostgreSqlContainer` on a shared `Network`); the dependency itself is exercised
happy-path by `qa-db-testing-dotnet` / `qa-messaging-testing-service-bus-dotnet`. Chaos adds the proxy in front and
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

- `qa-chaos-testing-java` · `qa-chaos-testing-typescript` — the sibling stacks (Toxiproxy + Testcontainers +
  resilience4j · toxiproxy-node-client + Vitest); this is the **port of the Java canonical**. Same four ideas, same
  lifecycle, different client lib + resilience library (Polly).
- `qa-network-monitoring-proxy-dotnet` (#10) — the **closest neighbor and the inverse**: that stands up a MITM proxy
  (`Titanium.Web.Proxy`) to **observe/mock** out-of-browser requests; this stands up Toxiproxy to **inject transport
  faults**. Observe vs break.
- `qa-test-environments-dotnet` (#14) — the **Testcontainers spine** the `ToxiproxyContainer` plugs into.
- `qa-api-mocking-wiremock-dotnet` (#22) — **application-layer** canned responses vs **transport** faults. They
  compose: a WireMock upstream behind a Toxiproxy listener.
- `qa-data-driven-testing-dotnet` (#39) — drive a **fault matrix** (toxic × parameter × expected pattern) via
  `[TestCaseSource]` instead of copy-pasted `[Test]` methods.
- `qa-db-testing-dotnet` · `qa-messaging-testing-service-bus-dotnet` — the dependencies you fault (DB / broker
  connections through the proxy); they cover the happy path this inverts.
- `qa-websocket-sse-testing-dotnet` (#37) — shares the **lifecycle discipline** (steady → perturb → assert →
  recover) and bounded-condition waits (never `Task.Delay`-as-a-wait).
- `qa-performance-nbomber-dotnet` — behaviour under **load/volume** vs behaviour under **fault** (this skill).
- `qa-allure-reporting-dotnet` — render each fault scenario as a named result.
