---
name: qa-api-mocking-msw-dotnet
description: >-
  API-mocking with MSW (Mock Service Worker) from a .NET 8 + NUnit SUT — the **sidecar port** of the
  TS-native canonical. MSW **cannot** intercept in-process in the .NET runtime, so here it runs as a
  **standalone Node sidecar mock server**: MSW handlers (`http.get`/`http.post` → `HttpResponse.json`)
  wrapped in an Express server by `@mswjs/http-middleware`'s `createServer(...handlers)` (started as a
  process or a Testcontainers Node container), and the .NET SUT's **constructor-injected** typed
  `HttpClient` points at the sidecar's base URL. Async all the way (`HttpClient`, `await`). Use when a
  .NET team wants to reuse MSW handlers (shared with a front-end) to fake a downstream HTTP dependency for
  an integration test. Covers the sidecar lifecycle, per-test handler overrides (a `/__mocks` control
  route), closure-state staged responses, condition-wait polling (no `Task.Delay`), and verifying the call
  via the sidecar's exposed event log. Triggers: "run MSW as a sidecar for our .NET integration test",
  "fake the payments API with MSW handlers from C#", "point HttpClient at an MSW mock server". Do NOT use
  for: the in-process app's-own-fetch interception MSW is built for (that's TS — use
  qa-api-mocking-msw-typescript, the canonical); a .NET-native standalone mock server with in-process
  scenarios + a request journal (use qa-api-mocking-wiremock-dotnet — usually the better fit for a pure
  .NET shop); the Java sidecar port (use qa-api-mocking-msw-java); an out-of-browser MITM proxy (use
  qa-network-monitoring-proxy-dotnet).
---

# API Mocking — MSW / Mock Service Worker (.NET 8 — sidecar port)

The **.NET port** of the canonical `qa-api-mocking-msw-typescript`. **Read that first** — it explains the
MSW model (handlers → resolvers → responses) and the events API in MSW's native, in-runtime form.

> **⚠️ The port inverts the tool's nature — read this before anything else.** MSW's whole point is
> intercepting the app's **own** HTTP **in-runtime** (a Service Worker / Node `http` patch). **That cannot
> happen in the .NET runtime** — MSW is a JavaScript tool and there is no in-process .NET interception. So
> in .NET, MSW only makes sense run as a **standalone Node sidecar mock server**:
> `@mswjs/http-middleware`'s `createServer(...handlers)` wraps the MSW handlers in an Express server you
> start as a **separate process** (or a Testcontainers Node container), and your .NET SUT's
> `HttpClient`-based typed client points at its base URL. **This is the inverse of WireMock (#22):**
> `WireMock.Net` is .NET-native (in-process server) with a *thin TS client*; MSW is TS-native
> (in-runtime) with a *sidecar-only* .NET port. It is the same shape as
> `qa-accessibility-testing-lighthouse-ci-dotnet` (#21) — a Node tool the .NET stack drives out-of-process.

> **Honest recommendation.** For a **pure .NET** shop with no front-end MSW handlers to reuse, the
> canonical .NET mock server is **`WireMock.Net`** (`qa-api-mocking-wiremock-dotnet`) — in-process,
> scenarios, a real request journal (`FindLogEntries`), no Node dependency. Choose the MSW sidecar
> specifically when you want **one set of handlers shared** between the front-end (where MSW runs natively
> in-runtime) and a .NET integration test, so the mock contract lives in exactly one place. Otherwise
> prefer `WireMock.Net`.

## Decision matrix — MSW sidecar vs the rest of the `api-mocking` family

| Need | Use | Why |
|------|-----|-----|
| Reuse **front-end MSW handlers** to fake a downstream dependency for a .NET test | **MSW sidecar (this skill)** | One handler set shared FE + .NET; the contract lives once |
| A .NET-native standalone mock server, in-process, scenarios + request journal, no Node | **`WireMock.Net`** (`qa-api-mocking-wiremock-dotnet`, #22) | Native, richer, no sidecar — the default for pure .NET |
| Mock the **app's own** `fetch` **in-runtime** (front-end/Node) | MSW native (`qa-api-mocking-msw-typescript`) | That's MSW's real home — in-process, no server |
| **Protocol-agnostic** over-the-wire imposters | Mountebank (#24) | Multi-protocol `mb` server |
| Mock derived **from an OpenAPI spec** | Prism (#25) | Spec-driven |
| Out-of-browser MITM on a *real* service's traffic | `qa-network-monitoring-proxy-dotnet` (#10) | `Titanium.Web.Proxy` on the wire; MSW *replaces* the service |

**Rule of thumb (.NET):** want a .NET mock server? → **`WireMock.Net`**, unless you specifically need to
**share MSW handlers with a front-end** — then run them as this **sidecar**.

## Stack

- .NET 8 + NUnit + the built-in async `HttpClient` (async all the way — never `.Result`/`.Wait()`)
- The **MSW sidecar** — a tiny Node project: `msw` + `@mswjs/http-middleware` (`createServer(...handlers)`),
  run as a process or a [Testcontainers for .NET](https://dotnet.testcontainers.org/) container Node image
  (cross-link `qa-test-environments-dotnet` / `qa-db-testing-testcontainers-dotnet`)
- The SUT is a typed `HttpClient`-based client (`qa-api-client-writer-dotnet`) — **constructor-injected**
  with the sidecar's base URL (never a static URL; the mapped port is dynamic)

```bash
dotnet add package Testcontainers
dotnet add package NUnit
```

## The MSW sidecar — handlers + a control surface

The sidecar is a small Node entrypoint (identical to the Java port's — the sidecar is stack-agnostic). It
registers the shared MSW handlers via `createServer(...)` and adds two **control routes** so the .NET test
can (a) override handlers per test and (b) read which requests were seen — because over an HTTP boundary
.NET can't call `server.use(...)` or subscribe to `server.events` directly (those are in-process JS APIs).

```javascript
// msw-sidecar/server.mjs  (shared with the Java port — the sidecar is language-agnostic)
import { http, HttpResponse } from 'msw';
import { createServer } from '@mswjs/http-middleware';
import express from 'express';

const seen = [];                                   // the "journal" MSW itself doesn't keep — we add one
const dynamic = new Map();                          // per-test overrides keyed by "METHOD path"

const baseHandlers = [
  http.get('/api/widgets/:id', ({ params, request }) => {
    seen.push({ method: 'GET', url: request.url });
    const override = dynamic.get(`GET /api/widgets/${params.id}`) ?? dynamic.get('GET /api/widgets/:id');
    if (override) return HttpResponse.json(override.body, { status: override.status });
    return HttpResponse.json({ id: Number(params.id), name: 'Sprocket', priceMinor: 1999 });
  }),
  http.post('/api/orders', async ({ request }) => {
    const body = await request.clone().json().catch(() => undefined);
    seen.push({ method: 'POST', url: request.url, body });
    const override = dynamic.get('POST /api/orders');
    return HttpResponse.json(override?.body ?? { orderId: 'ord-7' }, { status: override?.status ?? 201 });
  }),
];

const app = createServer(...baseHandlers);          // Express app with MSW handlers applied
app.use(express.json());
app.post('/__mocks/override', (req, res) => { dynamic.set(req.body.key, req.body); res.sendStatus(204); });
app.post('/__mocks/reset',    (_req, res) => { dynamic.clear(); seen.length = 0; res.sendStatus(204); });
app.get('/__mocks/seen',      (_req, res) => res.json(seen));

app.listen(Number(process.env.PORT ?? 0), () => console.log(`msw-sidecar:${app.address?.()?.port}`));
```

> The control routes (`/__mocks/*`) are how .NET reaches MSW's in-process features (`server.use`,
> `server.events`) **across the process boundary**. In the native TS skill these are method calls; here
> they must be exposed over HTTP — the unavoidable cost of the port.

## Sidecar lifecycle — Testcontainers Node image (default) or a process

One sidecar per fixture (a sidecar per test is far too slow — the same trade-off as
`qa-db-testing-testcontainers-dotnet`). The SUT's client is injected with the mapped base URL; reset the
sidecar's overrides + journal between tests via `/__mocks/reset`. Async all the way.

```csharp
public sealed class MswSidecar : IAsyncDisposable
{
    private readonly IContainer _container;
    private readonly HttpClient _http = new();

    private MswSidecar(IContainer container) => _container = container;

    public static async Task<MswSidecar> StartAsync()
    {
        var container = new ContainerBuilder()
            .WithImage("msw-sidecar:local")                       // Node image with the sidecar built in
            .WithPortBinding(8080, assignRandomHostPort: true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilMessageIsLogged("msw-sidecar"))
            .Build();
        await container.StartAsync();
        return new MswSidecar(container);
    }

    public string BaseUrl => $"http://{_container.Hostname}:{_container.GetMappedPublicPort(8080)}";

    public async Task OverrideJsonAsync(string key, int status, string jsonBody)
    {
        var payload = $$"""{ "key": "{{key}}", "status": {{status}}, "body": {{jsonBody}} }""";
        using var content = new StringContent(payload, Encoding.UTF8, "application/json");
        await _http.PostAsync($"{BaseUrl}/__mocks/override", content);
    }

    public async Task ResetAsync() =>
        await _http.PostAsync($"{BaseUrl}/__mocks/reset", new StringContent(""));

    public async Task<IReadOnlyList<SeenRequest>> SeenAsync()
    {
        var json = await _http.GetStringAsync($"{BaseUrl}/__mocks/seen");
        return JsonSerializer.Deserialize<List<SeenRequest>>(json, JsonOpts.Web)!;
    }

    public async ValueTask DisposeAsync() => await _container.DisposeAsync();
}

public sealed record SeenRequest(string Method, string Url, JsonElement? Body);
```

```csharp
[TestFixture]
public abstract class MswSidecarTest
{
    protected static MswSidecar Sidecar = null!;
    protected WidgetApiClient Client = null!;

    [OneTimeSetUp] public async Task StartSidecar() => Sidecar = await MswSidecar.StartAsync();
    [OneTimeTearDown] public async Task StopSidecar() => await Sidecar.DisposeAsync();

    [SetUp] public void WireClient() =>
        // Constructor-injected base URL — never a static one; the mapped port is dynamic.
        Client = new WidgetApiClient(new HttpClient { BaseAddress = new Uri(Sidecar.BaseUrl) });

    [TearDown] public async Task ResetSidecar() => await Sidecar.ResetAsync();   // keep tests independent
}
```

## Core pattern — exercise, assert outcome, verify via the sidecar journal

```csharp
public sealed class WidgetLookupTest : MswSidecarTest
{
    [Test]
    public async Task Should_return_the_widget_When_the_sidecar_responds_200()
    {
        // Uses the sidecar's default handler.
        var widget = await Client.GetWidgetAsync(42);

        Assert.That(widget, Is.EqualTo(new Widget(42, "Sprocket", 1999)));   // one logical assertion
    }
}
```

## Per-test overrides — the `/__mocks/override` control route

The MSW-native `server.use(...)` becomes an async call to the sidecar's control route. The `[TearDown]`
reset (already wired) drops it so tests stay independent.

```csharp
[Test]
public async Task Should_surface_an_error_When_the_dependency_returns_500()
{
    await Sidecar.OverrideJsonAsync("GET /api/widgets/42", 500, """{ "message": "upstream down" }""");

    Assert.That(async () => await Client.GetWidgetAsync(42),
        Throws.TypeOf<UpstreamException>().With.Message.Contains("upstream"));
}
```

## Stateful behavior — closure state in the sidecar (the Scenarios analogue)

Staged responses (first call pending, then done) live as **closure state in the handler** (a JS variable
in `server.mjs`), exactly as in the native skill — .NET just polls the client until it sees the final
state. **Wait on the condition, never `Task.Delay`** (the global no-sleep rule). The sidecar's delay (if
any) *simulates* latency; the condition-poll *asserts* it.

```csharp
[Test]
public async Task Should_poll_until_the_order_is_DONE()
{
    // The /api/orders/7/status handler in server.mjs returns PENDING then DONE via a closure counter.
    await PollUntil(async () => (await Client.GetOrderStatusAsync(7)).State == "DONE",
                    timeout: TimeSpan.FromSeconds(5), interval: TimeSpan.FromMilliseconds(100));
}

// A condition-poll helper with a deadline — NOT a fixed sleep. (NUnit has no built-in expect.poll.)
private static async Task PollUntil(Func<Task<bool>> condition, TimeSpan timeout, TimeSpan interval)
{
    var deadline = DateTime.UtcNow + timeout;
    while (DateTime.UtcNow < deadline)
    {
        if (await condition()) return;
        await Task.Delay(interval);          // polling cadence between checks, not a fixed test wait
    }
    Assert.Fail($"Condition not met within {timeout}");
}
```

> The `Task.Delay(interval)` here is the **poll cadence between condition checks** (bounded by a deadline),
> not a fixed "wait N seconds then assume done" sleep — the same shape as Awaitility's `pollInterval` or
> Vitest's `expect.poll` `interval`. Never `await Task.Delay(5000)` then assert blindly.

## Verification — the sidecar's exposed event log (MSW has no journal)

The native skill subscribes to `server.events.on('request:match', ...)`; **MSW keeps no queryable request
journal**, so the sidecar collects intercepted requests into `seen[]` and exposes them at `/__mocks/seen`.
.NET reads that log to assert the call happened with the right payload.

```csharp
[Test]
public async Task Should_POST_the_order_once_with_the_right_body()
{
    await Client.SubmitOrderAsync(OrderRequestMother.Standard());

    var posts = (await Sidecar.SeenAsync())
        .Where(r => r.Method == "POST" && r.Url.EndsWith("/api/orders"))
        .ToList();

    Assert.That(posts, Has.Count.EqualTo(1));
    Assert.That(posts[0].Body!.Value.GetProperty("sku").GetString(), Is.EqualTo("SPR-1"));
}
```

Prefer asserting on the **SUT's resulting state** (a persisted row via `qa-db-testing-client-dotnet`, a
returned value) when you can — it's stronger than "the call was made"; reach for the journal when the call
itself is the contract (idempotency key, exact payload).

## Run modes

| Mode | How | When |
|------|-----|------|
| **Testcontainers Node image** (default) | `ContainerBuilder().WithImage("msw-sidecar:local")` exposing the Express port | CI-parity, reachable on the Docker network, no host Node needed |
| **Local Node process** | `node msw-sidecar/server.mjs` on a fixed port, started in `[OneTimeSetUp]` | Fast local iteration; needs Node on the box |
| **In-process** | n/a in .NET | MSW can't intercept in-process here — that's the TS canonical only |

## Anti-patterns

- **Treating the .NET MSW sidecar as the default .NET mock server.** It carries a Node dependency + a
  bespoke control surface. *Fix:* use **`WireMock.Net`** (`qa-api-mocking-wiremock-dotnet`) for pure .NET;
  pick the MSW sidecar only to **share handlers with a front-end**.
- **`Task.Delay(...)` as a fixed wait for a staged/async flow.** Races the sidecar. *Fix:* a bounded
  condition-poll on the client's visible state; sidecar `delay` only *simulates* latency.
- **A static/hard-coded sidecar URL.** The mapped port is dynamic. *Fix:* constructor-inject
  `Sidecar.BaseUrl` into the typed client.
- **`.Result`/`.Wait()` on the sidecar HTTP calls.** Blocks and can deadlock. *Fix:* `await` all the way.
- **Forgetting `/__mocks/reset` between tests.** Overrides + the journal leak. *Fix:* `[TearDown]` reset.
- **Starting a sidecar per test.** Too slow. *Fix:* one per fixture (`[OneTimeSetUp]`), reset state between.
- **Asserting only the outcome when the call is the contract.** *Fix:* read `/__mocks/seen` and assert
  body/headers/count.

## Examples

**End-to-end: a retry-then-succeed flow via sidecar closure state + a verify on the POST count.**

```csharp
public sealed class OrderSubmissionTest : MswSidecarTest
{
    [Test]
    public async Task Should_retry_then_succeed_When_orders_API_is_briefly_unavailable()
    {
        // The sidecar's /api/orders handler returns 503 on the first call then 201 (closure counter).
        var order = await Client.SubmitOrderAsync(OrderRequestMother.Standard());   // SUT retries

        Assert.That(order.OrderId, Is.EqualTo("ord-7"));                            // outcome

        var attempts = (await Sidecar.SeenAsync())
            .Count(r => r.Method == "POST" && r.Url.EndsWith("/api/orders"));
        Assert.That(attempts, Is.EqualTo(2));                                       // retried once
    }
}
```

**Test-data builder for request payloads (4+ fields → builder, per the global rules).**

```csharp
public static class OrderRequestMother
{
    public static OrderRequest Standard() =>
        new OrderRequestBuilder()
            .WithSku("SPR-1").WithQty(3).WithCurrency("EUR").WithIdempotencyKey("idem-123").Build();
}
```

## Rules (hard constraints)

- MSW **cannot** intercept in-process in .NET — it runs as a **standalone Node sidecar**; the SUT's typed
  `HttpClient` is **constructor-injected** with the sidecar's mapped base URL (never static).
- One sidecar per fixture (`[OneTimeSetUp]`) + `/__mocks/reset` in `[TearDown]` — keep tests independent.
  Never a sidecar per test.
- Per-test overrides via the `/__mocks/override` control route; staged responses via closure state in the
  sidecar handler.
- **Async all the way** (`await`, never `.Result`/`.Wait()`). **No fixed `Task.Delay` waits** — a bounded
  condition-poll on the client's visible state; sidecar `delay` only to *simulate* latency.
- Verify via the sidecar's `/__mocks/seen` log (MSW has **no journal**); prefer asserting the SUT's
  resulting state when you can.
- Assert both sides: the **outcome** (one logical assertion) **and**, when the call is the contract, the
  **request** (body/headers/count) from `/__mocks/seen`.
- Builders/ObjectMother for request payloads with 4+ fields; test names `Should_X_When_Y`; structured
  logging (message templates); no secrets in handlers or sidecar config.
- Prefer **`WireMock.Net`** for a pure .NET mock server; use the MSW sidecar to **share handlers with a
  front-end**.

## Cross-references

- `qa-api-mocking-msw-typescript` — the **canonical**, TS-native stack: MSW intercepts the app's own
  `fetch` **in-runtime** (`setupServer`/`setupWorker`), no sidecar. Structure ported from there; the
  interception model becomes a server here.
- `qa-api-mocking-msw-java` — the **Java sidecar port**, same shape (Node sidecar + injected base URL,
  TestNG + Awaitility). The sidecar `server.mjs` is shared between this port and the Java one.
- `qa-api-mocking-wiremock-dotnet` (#22) — the .NET-native standalone mock server (in-process
  `WireMock.Net`, scenarios, `FindLogEntries` journal). **Usually the better fit for a pure .NET shop**;
  the key contrast: `WireMock.Net` is .NET-native, MSW is a Node sidecar here. The inverse of this node's
  port story.
- `qa-api-client-writer-dotnet` + `qa-api-test-author-generator-dotnet` — the typed `HttpClient` client /
  API tests pointed at the sidecar base URL (constructor injection).
- `qa-test-environments-dotnet` + `qa-db-testing-testcontainers-dotnet` — the Node-sidecar run mode
  (process or Testcontainers Node image) + the per-fixture-vs-per-test lifecycle trade-off mirrored here.
- `qa-network-monitoring-proxy-dotnet` (#10) — `Titanium.Web.Proxy` out-of-browser MITM on a *real*
  service's traffic; MSW *replaces* the service. Mirror its fault-injection framing.
- `qa-ci-pipelines-github-actions-dotnet` — runs these tests; needs Node available in the job for the
  sidecar (process) or Docker for the Testcontainers Node image.
