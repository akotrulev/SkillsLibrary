---
name: qa-failure-injection-testing-typescript
description: Use when writing fault-injection / resilience tests in Node 24 (22 supported) / TypeScript / Vitest with Toxiproxy via Testcontainers (toxiproxy-node-client) — inject latency, drops, and bandwidth caps on a dependency (DB, API, broker, cache) and assert the app degrades gracefully. Triggers: "test the app survives a slow database", "inject a connection drop", "assert the circuit breaker opens". For end-to-end suite work prefer the phased agent `qa-api-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Chaos / Fault-Injection Testing (TypeScript / Toxiproxy + Testcontainers + Vitest)

Scaffolds **fault-injection resilience tests** in TypeScript against a deployed service and its dependencies, using
[**Toxiproxy**](https://github.com/Shopify/toxiproxy) — Shopify's TCP fault-injection proxy — stood up via the
Testcontainers `ToxiProxyContainer` and driven by the `toxiproxy-node-client`. It is the **inverse** of every
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
>    `proxy.host:proxy.port` so **all** its traffic to that dependency flows through a fault point you control. No
>    proxy in the path → nothing to fault.
> 3. **Toxics are added and removed at runtime over the REST API — every test is a lifecycle.** `steady-state →
>    inject the toxic → assert degraded → remove the toxic → assert recovery.` Toxiproxy's control API (port 8474)
>    lets you mutate the fault mid-test via `proxy.addToxic(...)` / `proxy.removeToxic(name)`, so one test proves
>    **both** that the app degrades under fault **and** that it heals once the fault clears (the drain-then-assert
>    lifecycle of `qa-realtime-stream-testing-typescript`, applied to faults).
> 4. **Assert the resilience PATTERN, not the fault.** The toxic is the *given*, not the assertion. Assert the
>    **behaviour it provokes**: the retry count, the circuit-breaker state transition (Closed → Open → HalfOpen →
>    Closed via cockatiel), the honored timeout (fails *fast*, not hangs), the fallback payload served. This is what
>    `qa-network-mocking-typescript` can *observe* but never *inject* — observe vs break.

## Decision matrix — fault scenario → toxic → what you assert

| You want to prove | Inject (toxic) | Assert (the resilience pattern) |
|---|---|---|
| **App survives a slow dependency** | `latency` (+ `jitter`), downstream | the call completes within the app's timeout via retry/fallback, OR fails *fast* — never hangs the request |
| **A timeout is honored (no hang)** | `timeout` (ms) or large `latency` > the app's deadline | the call fails as a *timeout* inside the app's budget; the user-facing path returns an error/fallback, not a 30s hang |
| **A circuit breaker opens under sustained failure** | `timeout` / `reset_peer` held across N calls | cockatiel breaker goes **Closed → Open**; subsequent calls short-circuit (`BrokenCircuitError`) without hitting the dependency |
| **The breaker recovers when the dependency heals** | inject, drive calls to Open, then **`removeToxic(...)`** | after the half-open window the breaker goes **Open → HalfOpen → Closed**; calls succeed again (idea #3 lifecycle) |
| **Retry-with-backoff fires the contracted number of times** | `reset_peer` / `timeout` on the first N attempts | the app makes exactly *maxAttempts* tries (assert via the dependency-side call count or a cockatiel `onRetry` counter), then succeeds or falls back |
| **A fallback is served, not an error** | `timeout` / connection cut | the degraded response is the contracted fallback (cached value, default, friendly message) — assert its content |
| **A partial / garbled response is handled** | `slicer` (fragment the stream) or `limit_data` (cut after N bytes) | the app surfaces a parse/IO error and recovers — does NOT persist a truncated record or corrupt state |
| **Bandwidth starvation degrades, not crashes** | `bandwidth` (KB/s) downstream | the app stays responsive (timeout/fallback) under a throttled backend dependency (distinct from device-network conditioning) |
| **Probabilistic / flappy faults** | any toxic with `toxicity: 0.3` | the app tolerates an intermittent fault — retries smooth over the fraction that fail |

## Stack

- Node 20 + TypeScript (strict), **Vitest** (the global default TS runner) + Allure via `allure-vitest` where used
- **Testcontainers for Node** — `testcontainers` + `@testcontainers/toxiproxy` (the `ToxiProxyContainer` module) +
  the dependency module (e.g. `@testcontainers/postgresql`, `@testcontainers/kafka`)
- **toxiproxy-node-client** — the REST client the container module returns as `proxy.instance` (`addToxic`,
  `removeToxic`, `getToxics`); toxic `type` + `stream` (`upstream` / `downstream`) + `toxicity`
- **cockatiel** — the resilience patterns under test (`circuitBreaker`, `retry`, `timeout`, `fallback`,
  `CircuitState`); assert their state/metrics (or assert your own retry/circuit code's effects). `opossum` is an
  alternative circuit-breaker lib if the project already uses it
- Layout: `tests/chaos/` (the fault tests), `tests/support/chaos/` (the `ChaosProxy` helper + `startChaos` container
  lifecycle)

```jsonc
// package.json (devDependencies excerpt)
{
  "devDependencies": {
    "vitest": "^2.1.8",
    "testcontainers": "^10.16.0",
    "@testcontainers/toxiproxy": "^10.16.0",
    "@testcontainers/postgresql": "^10.16.0",   // the dependency you fault (example)
    "toxiproxy-node-client": "^2.2.7",
    "cockatiel": "^3.2.1"                        // the resilience library under test
  }
}
```

> **Why a proxy and not a mock?** A mock (e.g. MSW) makes the *dependency* return a canned
> error at the application layer; a Toxiproxy toxic faults the *transport* — latency, a dropped TCP connection, a
> half-sent response — the failures that exercise socket timeouts, connection pools, and retry/circuit code. Mock
> when you control the contract and want a specific status; **fault-inject when you want to prove the app survives
> the network/dependency misbehaving**. They compose: an MSW/WireMock upstream behind a Toxiproxy listener faults
> the transport to a controllable contract.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The mechanism — proxy BETWEEN app and dependency (idea #2)**; **The toxic helper — `tests/support/chaos/ChaosProxy.ts`**.

## Inject-a-fault, assert-degradation (idea #1)

The simplest chaos test: with no toxic the call succeeds; **with the toxic injected the app must fail fast or fall
back — never hang**. Assert the *degraded behaviour*, not the fault.

```ts
// tests/chaos/slowDependency.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startChaos, type ChaosFixture } from '../support/chaos/startChaos.js';
import { OrderService } from '../../src/orderService.js';

describe('slow dependency', () => {
  let fixture: ChaosFixture;
  beforeAll(async () => { fixture = await startChaos(); }, 120_000);
  afterAll(async () => { await fixture.stop(); });

  it('fails fast when the database is slower than the timeout', async () => {
    const { chaos } = fixture;
    // App is configured with a 2s query timeout; inject 5s latency so the dependency overruns it.
    await chaos.injectLatency(5_000);

    const app = OrderService.connectedTo(chaos.host(), chaos.port());   // app talks to the PROXY

    const start = performance.now();
    const result = await app.placeOrder('sku-1');                       // must NOT hang for 5s
    const elapsedMs = performance.now() - start;

    expect(result.isFallback, 'degrades to fallback under latency').toBe(true);
    expect(elapsedMs, 'fails fast inside the timeout budget').toBeLessThan(3_000);

    await chaos.healed();
  });
});
```

> The assertion is on the **timeout being honored + a fallback served** — the resilience pattern — not on the 5s
> delay. A test that asserts "the call took 5s" is asserting the *fault*, which proves nothing about the app.

## The full lifecycle — steady → inject → degraded → remove → recovered (idea #3)

One test proves the app **degrades under fault and heals when it clears**. This is the chaos analogue of the
drain-then-assert lifecycle in `qa-realtime-stream-testing-typescript`.

```ts
it('degrades under a connection drop then recovers when healed', async () => {
  const { chaos } = fixture;
  const app = OrderService.connectedTo(chaos.host(), chaos.port());

  // 1. steady state — no toxic, the call works.
  expect((await app.placeOrder('sku-1')).isSuccess).toBe(true);

  // 2. inject — drop the connection.
  await chaos.cutConnection();

  // 3. assert degraded — the app serves its fallback, it does not throw an unhandled error.
  expect((await app.placeOrder('sku-1')).isFallback, 'degrades while the connection is cut').toBe(true);

  // 4. remove — the dependency is healed.
  await chaos.healed();

  // 5. assert recovery — calls succeed again (await the breaker's half-open window, never setTimeout).
  await vi.waitFor(async () => {
    expect((await app.placeOrder('sku-1')).isSuccess).toBe(true);
  }, { timeout: 10_000, interval: 200 });
});
```

> Step 5 uses **`vi.waitFor`** (a bounded condition-poll), *not* a `setTimeout` sleep — the recovery window (e.g.
> cockatiel's `halfOpenAfter`) is a real condition to await, not a guessed delay.

## Assert the resilience PATTERN — circuit breaker via cockatiel (idea #4)

Hold a fault across several calls and assert the **circuit-breaker state machine**, not the fault. The breaker is
the unit under test; Toxiproxy just supplies the sustained failure that should trip it.

```ts
// tests/chaos/circuitBreaker.test.ts
import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { CircuitState } from 'cockatiel';
import { startChaos, type ChaosFixture } from '../support/chaos/startChaos.js';
import { OrderService } from '../../src/orderService.js';

describe('circuit breaker under sustained failure', () => {
  let fixture: ChaosFixture;
  beforeAll(async () => { fixture = await startChaos(); }, 120_000);
  afterAll(async () => { await fixture.stop(); });

  it('opens the breaker when the dependency sustains failures', async () => {
    const { chaos } = fixture;
    const app = OrderService.connectedTo(chaos.host(), chaos.port());
    const breaker = app.breaker;                       // the cockatiel CircuitBreakerPolicy

    expect(breaker.state).toBe(CircuitState.Closed);   // steady

    await chaos.injectTimeout(0);                       // every call to the dependency now hangs+drops
    for (let i = 0; i < 10; i++) await app.placeOrderSafely('sku-1');  // drive calls past the threshold

    // The PATTERN: the breaker opened — later calls short-circuit WITHOUT hitting the dependency.
    expect(breaker.state).toBe(CircuitState.Open);

    await chaos.healed();                               // dependency recovers
    // Open → HalfOpen → Closed once the wait window elapses and a probe succeeds.
    await vi.waitFor(async () => {
      await app.placeOrderSafely('sku-1');             // a probe call in HalfOpen
      expect(breaker.state).toBe(CircuitState.Closed);
    }, { timeout: 15_000, interval: 250 });
  });
});
```

> Assert the **state transition** (Closed → Open → Closed) and the **short-circuit** (a call in Open rejects with
> `BrokenCircuitError` without reaching the proxy). That is the resilience contract; the `timeout` toxic is merely
> the sustained failure that should provoke it.

## Retry count — assert exactly the contracted attempts

A `reset_peer` on the connection makes attempts fail; assert the app makes **exactly** the contracted number of
tries (via a cockatiel `onRetry` counter, or by counting calls that reach the upstream), then succeeds/falls back —
not infinite, not one.

```ts
it('retries exactly three times then falls back on connection resets', async () => {
  const { chaos } = fixture;
  const app = OrderService.connectedTo(chaos.host(), chaos.port());
  await chaos.cutConnection();                          // every attempt's connection is reset

  const result = await app.placeOrderWithRetry('sku-1');

  expect(result.isFallback).toBe(true);
  // The PATTERN: bounded retries, not a runaway loop — assert the configured attempt count.
  expect(app.lastAttemptCount, 'maxAttempts honored').toBe(3);

  await chaos.healed();
});
```

## Partial / garbled response — `slicer` / `limit_data` (don't persist corruption)

A response cut mid-stream must surface as an error the app handles — it must **not** be parsed and persisted as a
valid (truncated) record. Inject `limit_data` (cut after N bytes) or `slicer` (fragment the stream), drive a read,
and assert the app rejects the partial result and leaves state uncorrupted.

```ts
it('rejects and does not persist a truncated response', async () => {
  const { chaos } = fixture;
  await chaos.truncateAfter(64);                        // cut every response after 64 bytes
  const app = CatalogService.connectedTo(chaos.host(), chaos.port());

  const result = await app.loadCatalog();

  expect(result.isError, 'partial response surfaces as an error').toBe(true);
  expect(app.lastPersistedCatalog, 'no truncated record persisted').toBeNull();

  await chaos.healed();
});
```

## Probabilistic faults — `toxicity` for flappy dependencies

A `toxicity` below 1.0 applies the toxic to only a *fraction* of connections — an intermittent, flappy dependency.
Assert the app's retries smooth over the failing fraction so the user-visible outcome stays correct.

```ts
it('tolerates an intermittently resetting dependency', async () => {
  const { chaos } = fixture;
  await chaos.cutConnection(0, 0.3);                    // reset the connection only 30% of the time
  const app = OrderService.connectedTo(chaos.host(), chaos.port());

  // 20 calls; with retry-with-backoff the user-visible success rate should be ~100% despite a 30% fault rate.
  let succeeded = 0;
  for (let i = 0; i < 20; i++) {
    if ((await app.placeOrderWithRetry('sku-1')).isSuccess) succeeded++;
  }

  expect(succeeded, 'retries absorb an intermittent fault').toBe(20);

  await chaos.healed();
});
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
  nothing. *Fix:* rewire the app's connection string / base URL / bootstrap to `chaos.host():chaos.port()`.
- **Injecting a toxic and never removing it.** You prove degradation but not **recovery**, and you leak the fault
  into the next test. *Fix:* run the full lifecycle — `healed()` (remove) then assert recovery; remove in teardown /
  `afterEach`.
- **`setTimeout`/`browser`-style sleeps to wait for the breaker to open/close or the dependency to "settle".** Banned
  by CLAUDE.md and flaky. *Fix:* **`vi.waitFor`** on the real state (breaker state, a successful call).
- **A `latency` so small it doesn't exceed the app's timeout** (or so large the suite hangs). *Fix:* inject a
  latency *deliberately past* the app's deadline; bound the test with the app's own timeout + `vi.waitFor`, never an
  open-ended wait.
- **Faulting the wrong direction.** `downstream` faults dependency→app responses; `upstream` faults app→dependency
  requests. *Fix:* pick the `stream` that matches the failure you mean to simulate.
- **One Toxiproxy/dependency per `it(...)`.** Slow and churns ports. *Fix:* stand them up once in `beforeAll` on a
  shared `Network`; reset toxics (`healed()`) between tests, not the containers.
- **Treating this as production chaos engineering.** *Fix:* deterministic toxic in a test ≠ GameDay on a live
  cluster — see the boundary note; route prod-chaos requests to Gremlin/Litmus/Chaos Mesh.

## Examples

**End-to-end: the inverted assertion.** A REST author writes `expect(response.status).toBe(200)`. A chaos author
writes: inject `timeout`, then `expect(result.isFallback).toBe(true)` **and**
`expect(breaker.state).toBe(CircuitState.Open)`. Same dependency, opposite question — *does the app survive it
failing?*

**Composing with the dependency families.** The thing you fault is stood up by Testcontainers
(`ToxiProxyContainer` next to a `PostgreSqlContainer` / `KafkaContainer` on a shared `Network`); the dependency
itself is exercised happy-path by `qa-db-testing-typescript` / `qa-messaging-testing-typescript`. Chaos adds
the proxy in front and asserts the resilience layer — it **composes** with those skills, it doesn't replace them. A
data-driven fault matrix (toxic × parameter) binds cleanly via `qa-data-driven-testing-typescript` (`it.each`).

## Rules (hard constraints)

- **The assertion is the resilience PATTERN, never the dependency working or the fault itself.** Assert retry
  count, circuit-breaker state transitions, an honored timeout (fails fast), or fallback content. "Assert the call
  succeeded" is the wrong reflex here.
- **The app under test connects to the PROXY**, not the real dependency — rewire its connection string / base URL /
  bootstrap to `chaos.host():chaos.port()`. If the app bypasses the proxy, the test is inert.
- **Every fault test runs the lifecycle** where recovery matters: steady → inject → assert degraded → `healed()`
  (remove) → assert recovery. Always remove injected toxics (between tests / in teardown) so faults don't leak.
- **No `setTimeout`/`browser.pause` sleeps.** Wait on real conditions with **`vi.waitFor`** — breaker state, a
  successful probe call. A timeout/latency toxic is an *injected delay*, not a test wait.
- **Pick the toxic + `stream` deliberately** to match the failure (latency/`bandwidth` for slow, `timeout`/`reset_peer`
  for drop, `slicer`/`limit_data` for partial; `downstream` = responses, `upstream` = requests).
- **One Toxiproxy + dependency per suite** on a shared `Network` in `beforeAll`; reset toxics between tests, not the
  containers. Named toxics so they can be removed.
- **This is functional fault-injection, not production chaos engineering** — deterministic toxic in CI; route
  live-cluster chaos (Gremlin/Litmus/Chaos Mesh) elsewhere.
- **Wrap all toxic wiring in `ChaosProxy`** with intent names — no raw `proxy.addToxic({...})` in `it(...)`.
  Vitest + toxiproxy-node-client + Testcontainers + cockatiel.

## Cross-references

- `qa-failure-injection-testing-java` · `qa-failure-injection-testing-dotnet` — the sibling stacks (`toxiproxy-java` + resilience4j ·
  `Toxiproxy.Net` + Polly); same four ideas, same lifecycle, different client lib + resilience library.
- `qa-network-mocking-typescript` — the **closest neighbor and the inverse**: that stands up a MITM
  proxy to **observe/mock** out-of-browser requests; this stands up Toxiproxy to **inject transport faults**.
  Observe vs break. Read it for the proxy-in-the-middle model; draw the boundary cleanly.
- `qa-data-driven-testing-typescript` — drive a **fault matrix** (toxic × parameter × expected pattern) via
  `it.each` instead of copy-pasted tests.
- `qa-db-testing-typescript` · `qa-messaging-testing-typescript` · `qa-messaging-testing-typescript` —
  the dependencies you fault (DB / broker connections through the proxy); they cover the happy path this inverts.
- `qa-realtime-stream-testing-typescript` — shares the **lifecycle discipline** (steady → perturb → assert →
  recover) and bounded-condition waits (`vi.waitFor`, never sleep).
- `qa-load-testing-typescript` — behaviour under **load/volume** vs behaviour under **fault** (this skill); they
  answer different questions.
- `qa-test-reports-typescript` — render each fault scenario as a named result.
