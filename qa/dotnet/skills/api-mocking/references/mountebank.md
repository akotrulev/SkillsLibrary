# API Mocking — Mountebank (.NET 8 / NUnit)

The .NET port of the canonical `qa-api-mocking-typescript`. Mountebank is **stack-agnostic** —
there is **no native in-process Mountebank in any runtime** (unlike `WireMock.Net`, which the
`references/wiremock.md` sibling runs in-process). Every stack does the identical thing: it is a
**thin HTTP client to a running `mb` server** driven over an **HTTP REST control API**. So this file ports the
canonical almost 1:1 — same `POST /imposters` → exercise → `GET /imposters/:port` → `DELETE /imposters` REST
calls; only the HTTP-client idioms change (here, `HttpClient` + `System.Text.Json`, async-all-the-way).

Mountebank is a **standalone, protocol-agnostic service-virtualization server**: stand up `mb` (here a
container), `POST` an **imposter** to it (a fake service bound to a port speaking a chosen protocol), point
the SUT's typed client at the imposter's port, exercise, then read the imposter's recorded `requests` to
verify, and `DELETE` imposters between tests.

> **The boundary that defines this skill.** Mountebank is a **standalone server you point a client at** — it
> *replaces* the dependency, the same end of the wire as WireMock. That is the line against the
> `network-monitoring` family: `qa-network-monitoring-dotnet` is an *out-of-browser MITM proxy* on a
> *real* client's live traffic. Mountebank, like WireMock, **is** the dependency — but it adds **multiple
> protocols** and is driven purely over a REST API.

## Stack

- .NET 8 + NUnit + `HttpClient` (async-all-the-way) + `System.Text.Json`
- [Testcontainers for .NET](https://dotnet.testcontainers.org/) running the
  [`bbyars/mountebank`](https://hub.docker.com/r/bbyars/mountebank) image — the default run mode (cross-link
  `qa-test-environments-dotnet` / `qa-db-testing-testcontainers-dotnet`)
- A thin REST client to the `mb` **admin API** (port `2525`) and to the imposter
- A typed client (`qa-api-client-writer-dotnet`) is the SUT — **constructor-injected** with the imposter base URL

```bash
dotnet add package Testcontainers
dotnet add package NUnit
```

## The Mountebank model — imposters, stubs, lifecycle

Mountebank's whole model is three nested concepts, all JSON over the REST API:

- An **imposter** = a fake service bound to a `port`, speaking a `protocol` (`http`/`https`/`tcp`/`smtp`),
  holding an ordered list of **stubs**.
- A **stub** = `{ predicates, responses }`. The **first stub whose predicates all match** answers the request.
- **Predicates** decide *whether* a stub matches; **responses** decide *what* it returns.

The lifecycle of every suite that uses `mb`:

1. **Start** the `mb` server — a Testcontainers container exposing the admin port `2525`.
2. **Connect** the admin client — an `HttpClient` pointed at `http://<host>:<adminPort>`.
3. **Create an imposter** — `POST /imposters` with `{ port, protocol, stubs, recordRequests: true }`.
4. **Point the SUT at the imposter's base URL** — injected into the typed client's constructor.
5. **Exercise** the SUT so it calls the dependency.
6. **Verify** via the imposter's recorded `requests` — `GET /imposters/:port`.
7. **Reset** between tests — `DELETE /imposters`; **stop** the container at teardown.

### The admin client + container fixture (per-fixture)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-dotnet`: **one container per fixture**
(`[OneTimeSetUp]`/`[OneTimeTearDown]`), delete imposters in `[TearDown]` so they don't leak. A container per
test is far too slow.

```csharp
// Tests/Support/MbClient.cs — a thin async REST client to the mb admin API (port 2525).
using System.Net.Http.Json;
using System.Text.Json;

namespace Tests.Support;

public sealed class MbClient
{
    private readonly HttpClient _http;
    private readonly string _adminUrl;

    public MbClient(string adminUrl)
    {
        _adminUrl = adminUrl;
        _http = new HttpClient();
    }

    // POST /imposters — the spec is an anonymous/record object serialized by System.Text.Json.
    public async Task CreateImposterAsync(object imposter, CancellationToken ct = default)
    {
        using var res = await _http.PostAsJsonAsync($"{_adminUrl}/imposters", imposter, ct);
        if (!res.IsSuccessStatusCode)
            throw new InvalidOperationException(
                $"CreateImposter failed: {(int)res.StatusCode} {await res.Content.ReadAsStringAsync(ct)}");
    }

    // GET /imposters/:port — the recorded-request journal (needs recordRequests:true on the imposter).
    public async Task<IReadOnlyList<JsonElement>> RecordedRequestsAsync(int imposterPort, CancellationToken ct = default)
    {
        using var doc = JsonDocument.Parse(await _http.GetStringAsync($"{_adminUrl}/imposters/{imposterPort}", ct));
        return doc.RootElement.TryGetProperty("requests", out var reqs)
            ? reqs.EnumerateArray().Select(e => e.Clone()).ToList()
            : [];
    }

    public async Task DeleteAllImpostersAsync(CancellationToken ct = default)
    {
        using var res = await _http.DeleteAsync($"{_adminUrl}/imposters", ct);
    }
}
```

```csharp
// Tests/Support/MountebankFixture.cs
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;

namespace Tests.Support;

public sealed class MountebankFixture
{
    public const int ImposterPort = 4545;   // the imposter's own port — distinct from admin (2525)

    public IContainer Container { get; private set; } = null!;
    public MbClient Mb { get; private set; } = null!;
    public WidgetApiClient Client { get; private set; } = null!;

    public async Task StartAsync()
    {
        Container = new ContainerBuilder()
            .WithImage("bbyars/mountebank:2.9.1")
            .WithPortBinding(2525, true)            // expose BOTH admin and imposter ports
            .WithPortBinding(ImposterPort, true)
            .WithCommand("mb", "start", "--allowInjection")   // --allowInjection only if you use `inject`
            .WithWaitStrategy(Wait.ForUnixContainer().UntilPortIsAvailable(2525))
            .Build();
        await Container.StartAsync();

        var adminUrl = $"http://{Container.Hostname}:{Container.GetMappedPublicPort(2525)}";
        Mb = new MbClient(adminUrl);

        // The SUT's typed client is constructor-injected with the imposter's mapped base URL — never static.
        var imposterBaseUrl = $"http://{Container.Hostname}:{Container.GetMappedPublicPort(ImposterPort)}";
        Client = new WidgetApiClient(imposterBaseUrl);
    }

    public Task ResetImpostersAsync() => Mb.DeleteAllImpostersAsync();   // keep tests independent

    public async Task StopAsync()
    {
        if (Container is not null) await Container.DisposeAsync();
    }
}
```

> **Two ports, one container.** The **admin port** (`2525`) is where you POST imposters; each **imposter**
> binds its own port (`4545`) that the SUT talks to. Expose and map both. Re-creating the imposter in each
> test (after `[TearDown]` deletes it) keeps tests independent. Everything is `async`/`await` — never `.Result`
> or `.Wait()`.

## Core pattern — create the imposter, point the client, exercise, verify

The SUT is a typed client constructor-injected with the imposter's base URL (cross-link
`qa-api-client-writer-dotnet`). The test creates an imposter, drives the client, asserts the **response** (one
logical assertion), and verifies the **request** via the recorded-request journal.

```csharp
using NUnit.Framework;
using Tests.Support;

[TestFixture]
public class WidgetLookupTests
{
    private readonly MountebankFixture _fx = new();

    [OneTimeSetUp] public Task StartMb() => _fx.StartAsync();
    [TearDown] public Task Reset() => _fx.ResetImpostersAsync();
    [OneTimeTearDown] public Task StopMb() => _fx.StopAsync();

    [Test]
    public async Task Should_return_the_widget_When_the_imposter_responds_200()
    {
        // 1. Create the imposter: a stub = predicates (match) → responses (return).
        var imposter = new
        {
            port = MountebankFixture.ImposterPort,
            protocol = "http",
            recordRequests = true,
            stubs = new[]
            {
                new
                {
                    predicates = new object[] { new { equals = new { method = "GET", path = "/api/widgets/42" } } },
                    responses = new object[]
                    {
                        new { @is = new {
                            statusCode = 200,
                            headers = new { ContentType = "application/json" },
                            body = "{\"id\":42,\"name\":\"Sprocket\",\"priceMinor\":1999}",
                        } },
                    },
                },
            },
        };
        await _fx.Mb.CreateImposterAsync(imposter);

        // 2. Exercise the SUT (already pointed at the imposter's base URL).
        var widget = await _fx.Client.GetWidgetAsync(42);

        // 3. Assert the response (one logical assertion).
        Assert.That(widget, Is.EqualTo(new Widget(42, "Sprocket", 1999)));

        // 4. Verify the request the SUT actually sent (the recorded-request journal).
        Assert.That(await _fx.Mb.RecordedRequestsAsync(MountebankFixture.ImposterPort), Has.Count.EqualTo(1));
    }
}
```

> **`is` is a C# keyword — use `@is`.** When building the response object in C#, `is` must be escaped as `@is`;
> `System.Text.Json` serializes it back to `is`. (Likewise the `headers` `Content-Type` is best built via a
> `Dictionary<string,string>` so the hyphenated key survives — shown below — rather than the anonymous-type
> shortcut above.) An HTTP `is` `body` is a **string**: serialize JSON yourself and set `Content-Type`.

## Predicates — which requests this stub answers

A stub's `predicates` are **ANDed**; the **first stub** whose predicates all match wins. Predicates match over
`method`, `path`, `query`, `headers`, `body`:

```csharp
var predicates = new object[]
{
    new { equals = new { method = "POST", path = "/api/orders" } },
    new { contains = new { headers = new Dictionary<string, string> { ["Content-Type"] = "application/json" } } },
    new { matches = new { body = "\"sku\"\\s*:\\s*\"SPR-1\"" } },   // regex over the raw body
};
```

Predicate cheatsheet (the analogue of WireMock matchers):

| Match on | Predicate |
|----------|-----------|
| Exact equality (case-insensitive by default) | `new { equals = new { path = "/a/b" } }` |
| Deep/exact object equality | `new { deepEquals = new { query = new { k = "v" } } }` |
| Substring | `new { contains = new { body = "needle" } }` |
| Regex | `new { matches = new { path = "/api/widgets/[0-9]+" } }` |
| Field present | `new { exists = new { headers = new { Authorization = true } } }` |
| Prefix / suffix | `new { startsWith = ... }` / `new { endsWith = ... }` |
| JSON-body selector | add `jsonpath = new { selector = "$..sku" }` to a predicate |
| XML-body selector | add `xpath = new { selector = "//sku" }` to a predicate |
| Case-sensitive match | add `caseSensitive = true` to the predicate |
| Boolean combination | `new { and = new[] {...} }` / `new { or = new[] {...} }` / `new { not = ... }` |

**Ordering is the catch-all.** Mountebank serves the **first matching stub**, so put specific stubs first and a
**predicate-less stub last** as a deterministic fallback (a stub with **no** `predicates` matches everything):

```csharp
stubs = new[]
{
    new { predicates = specificPredicates, responses = ok200 },
    new { predicates = Array.Empty<object>(), responses = new object[]   // last = catch-all
        { new { @is = new { statusCode = 404, body = "no stub matched" } } } },
},
```

## Responses — `is` canned, the multiple-responses cycle, `proxy`, `inject`

A stub's `responses` is an **array**. On repeated matching requests Mountebank **cycles through the array**,
repeating the last entry once exhausted — Mountebank's **stateful / staged analogue** of WireMock Scenarios,
**no state machine needed**:

```csharp
// 503 on the first call, 201 on every call after — a transient-failure-then-recovery flow.
responses = new object[]
{
    new { @is = new { statusCode = 503 } },                                       // 1st call
    new { @is = new { statusCode = 201, body = "{\"orderId\":\"ord-7\"}" } },     // 2nd call onward
},
```

Response types:

| Type | What it does | Analogue |
|------|--------------|----------|
| `is` (`@is` in C#) | A canned response (`statusCode`/`headers`/`body`) | WireMock response definition |
| `proxy` | Record-and-replay against a **real upstream** (`{ to, mode }`) | WireMock recording |
| `inject` | A **JS function** computing the response — requires `--allowInjection` | WireMock Handlebars templating |

`inject` is a **sharp edge**: it needs `mb start --allowInjection`, runs arbitrary JS server-side, and is
harder to review. Prefer `@is` + the response cycle; reach for `inject` only when the response must be computed
from the request.

## Fault & latency — `_behaviors`

`_behaviors` decorate a response before it is sent. The headline for resilience tests is **`wait`** — it makes
the imposter respond slowly so you can exercise the SUT's timeout/retry paths. **`wait` SIMULATES latency — it
is never a test sleep (never `Task.Delay` as a wait):**

```csharp
// Latency: the imposter itself is slow — SIMULATE slowness here, never Task.Delay-as-wait in the test.
responses = new object[]
{
    new
    {
        @is = new { statusCode = 200, body = "{}" },
        _behaviors = new { wait = 2000 },   // 2s server-side delay
    },
},
```

Other `_behaviors`: `repeat` (serve the same response N times before advancing the cycle), `decorate` (a JS
post-processor, also needs `--allowInjection`), `copy`/`lookup` (inject request data into the response). For
**hard faults** (dropped/garbled connection) use the `tcp` protocol and close the socket.

Cross-link the fault-injection framing of `qa-network-monitoring-dotnet` — the proxy injects faults onto
a *real* service's traffic; Mountebank injects them **as** the (fake) service, like WireMock. Assert on the
SUT's **visible outcome** (a thrown exception, a fallback, a retry count) — and when you wait for an async
result, **wait on the condition** with a bounded async poll, never `Task.Delay`-as-wait:

```csharp
// Tests/Support/Wait.cs — a bounded async condition-poll helper (async-all-the-way, no fixed Task.Delay-as-wait).
public static class Wait
{
    public static async Task UntilAsync(Func<Task<bool>> condition, TimeSpan timeout, TimeSpan interval)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            if (await condition()) return;
            await Task.Delay(interval);   // poll interval between condition checks — NOT a fixed test sleep
        }
        Assert.Fail($"Condition not met within {timeout}.");
    }
}

await Wait.UntilAsync(
    async () => (await _fx.Client.GetOrderStatusAsync(7)).State == "DONE",
    TimeSpan.FromSeconds(10), TimeSpan.FromMilliseconds(200));
```

## Multi-protocol — the headline (a `tcp` imposter)

Mountebank's reason to exist alongside WireMock is that an imposter can speak more than HTTP. Stand up a
**`tcp`** imposter to fake a non-HTTP dependency — exactly what `WireMock.Net` cannot do. A `tcp` imposter's
`is` response uses a `data` field (the bytes to send back) instead of HTTP `statusCode`/`body`:

```csharp
// A second imposter on protocol 'tcp' — fake a raw socket service with a canned response.
var tcpImposter = new
{
    port = 5555,                     // expose+map this port on the container too
    protocol = "tcp",
    recordRequests = true,
    stubs = new[]
    {
        new
        {
            predicates = new object[] { new { contains = new { data = "PING" } } },
            responses = new object[] { new { @is = new { data = "PONG\n" } } },
        },
    },
};
await _fx.Mb.CreateImposterAsync(tcpImposter);
```

The *same* REST control API, predicate/response/journal model serve `http`, `tcp`, and `smtp`; only the `is`
payload shape changes (`statusCode`/`body` for HTTP, `data` for TCP).

## Verification — the recorded-request journal

Mountebank **keeps a request journal per imposter** when created with `recordRequests: true` — `GET
/imposters/:port` returns a `requests` array. The server-side "was X called, with what" assertion, decoupled
from the stub. **Make the contrast explicit: Mountebank *keeps* a journal (like WireMock); MSW does
*not*.**

```csharp
// Called exactly once, with the right body and header.
var calls = await _fx.Mb.RecordedRequestsAsync(MountebankFixture.ImposterPort);
var posts = calls.Where(r =>
    r.GetProperty("method").GetString() == "POST" &&
    r.GetProperty("path").GetString() == "/api/orders").ToList();
Assert.That(posts, Has.Count.EqualTo(1));
Assert.That(posts[0].GetProperty("body").GetString(), Does.Contain("\"sku\":\"SPR-1\""));
Assert.That(posts[0].GetProperty("headers").TryGetProperty("Idempotency-Key", out _), Is.True);

// Never called (negative assertion).
Assert.That(calls.Any(r => r.GetProperty("path").GetString() == "/api/legacy-pricing"), Is.False);
```

Verification reads the journal **separately** from the stub — return a generic `201` and still assert the exact
body the SUT POSTed. `recordRequests: true` is required for the journal to populate.

## Run modes — container / standalone CLI

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | a `ContainerBuilder` for `bbyars/mountebank` exposing `2525` + imposter ports | The default — CI-parity, reachable on the Docker network; identical run mode across all three stacks |
| **Standalone `mb` CLI** | `mb start --configfile imposters.json` | A shared mock across processes; manual exploration; declarative config |

There is **no in-process mode** in any stack (contrast `WireMock.Net`, which runs in-process) — that is exactly
why this .NET port is a thin REST client nearly identical to the TS canonical.

## Anti-patterns

- **`Task.Delay`-as-wait (or `Thread.Sleep`) to wait for an async / staged flow.** Races the server and is
  slow. *Fix:* the **response cycle** for staged responses + a bounded **condition-poll** on the client's
  visible state. `_behaviors.wait` only to *simulate* latency.
- **`.Result` / `.Wait()` on the REST or SUT calls.** Blocks and risks deadlock. *Fix:* `await` throughout —
  async all the way.
- **Forgetting `recordRequests: true`.** The `requests` array stays empty and verification silently passes.
  *Fix:* set it on every imposter you verify against.
- **Not deleting imposters between tests.** Imposters and journals leak; ports collide. *Fix:* `DELETE
  /imposters` in `[TearDown]`, re-create per test.
- **Starting a container per test.** Far too slow. *Fix:* one container per fixture (`[OneTimeSetUp]`), delete
  imposters between tests.
- **Hard-coding the SUT's base URL instead of injecting the mapped imposter port.** The port is dynamic. *Fix:*
  construct the typed client with the mapped imposter URL.
- **Putting the catch-all stub first.** Mountebank serves the *first* matching stub, so a leading
  predicate-less stub shadows everything. *Fix:* specific stubs first, predicate-less fallback last.
- **Forgetting `@is` (using `is`).** `is` is a C# keyword and won't compile. *Fix:* `@is`; it serializes back
  to `is`.
- **Asserting only the response, never the request.** A passing response can hide a wrong payload. *Fix:* read
  the recorded `requests` and assert body/headers/count.
- **Reaching for Mountebank to mock the app's own outbound HTTP.** That's in-runtime interception. *Fix:* MSW
  (`references/msw.md`, a Node sidecar port); Mountebank is a separate server.

## Examples

**End-to-end: a retry-then-succeed flow via the response cycle, with a verify on the recorded POSTs.**

```csharp
using NUnit.Framework;
using Tests.Support;

[TestFixture]
public class OrderSubmissionTests
{
    private readonly MountebankFixture _fx = new();

    [OneTimeSetUp] public Task StartMb() => _fx.StartAsync();
    [TearDown] public Task Reset() => _fx.ResetImpostersAsync();
    [OneTimeTearDown] public Task StopMb() => _fx.StopAsync();

    [Test]
    public async Task Should_retry_then_succeed_When_orders_API_is_briefly_unavailable()
    {
        // The response array cycles: 503 first, then 201 — the staged analogue of a WireMock scenario.
        var imposter = new
        {
            port = MountebankFixture.ImposterPort,
            protocol = "http",
            recordRequests = true,
            stubs = new[]
            {
                new
                {
                    predicates = new object[] { new { equals = new { method = "POST", path = "/api/orders" } } },
                    responses = new object[]
                    {
                        new { @is = new { statusCode = 503 } },                                   // 1st attempt
                        new { @is = new { statusCode = 201, body = "{\"orderId\":\"ord-7\"}" } }, // retry onward
                    },
                },
            },
        };
        await _fx.Mb.CreateImposterAsync(imposter);

        // SUT has a retry policy; it should transparently recover.
        var order = await _fx.Client.SubmitOrderAsync(OrderRequestMother.Standard());

        Assert.That(order.OrderId, Is.EqualTo("ord-7"));          // one logical assertion: outcome
        var attempts = (await _fx.Mb.RecordedRequestsAsync(MountebankFixture.ImposterPort))
            .Count(r => r.GetProperty("method").GetString() == "POST");
        Assert.That(attempts, Is.EqualTo(2));                     // retried once
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` starts the `mb` container; the typed client is injected with the mapped imposter base URL.
2. One stub stages a 503 → 201 cycle on the same endpoint (no state machine — the response array cycles).
3. The SUT's retry policy turns the transient 503 into success — the test asserts the **outcome** and verifies
   the dependency was hit exactly twice via the recorded-request journal.
4. `[TearDown]` deletes all imposters; the next test re-creates a clean one.

**Test-data builder for stub payloads (4+ fields → builder).**

```csharp
public static class OrderRequestMother
{
    public static OrderRequest Standard() =>
        new OrderRequestBuilder()
            .WithSku("SPR-1").WithQty(3).WithCurrency("EUR").WithIdempotencyKey("idem-123").Build();
}
```

## Rules (hard constraints)

- Mountebank is a **standalone, protocol-agnostic server you point a client at** — inject the imposter's mapped
  base URL into the typed client (`qa-api-client-writer-dotnet`); never hard-code the dynamic port.
- Create the imposter **before** the action that triggers the request; the **first matching stub** wins, so
  order stubs specific-first, predicate-less catch-all last.
- One container per fixture (`[OneTimeSetUp]`) + `DELETE /imposters` in `[TearDown]`, re-create per test — keep
  tests independent. Never a container per test.
- Set `recordRequests: true` on any imposter you verify against; assert both the **response** (one logical
  assertion) **and** the **request** (recorded `requests`).
- **Async all the way** — `await` every REST/SUT call; never `.Result`/`.Wait()`. **No `Task.Delay`/
  `Thread.Sleep` as a wait** — the **response cycle** for staged responses, `_behaviors.wait` to *simulate*
  latency, a bounded **condition-poll** to *assert*.
- Prefer `@is` + the response cycle; reserve `proxy` for record-replay and `inject` (needs `--allowInjection`)
  for genuinely computed responses. Remember `@is` (the C# keyword escape).
- Builders/ObjectMother for imposter/stub/predicate/response payloads with 4+ fields.
- Test names `Should_X_When_Y`; constructor injection; structured logging; no secrets in imposter specs.
- Prefer **WireMock** for the richest HTTP-only server or in-process .NET; **MSW** (sidecar) for the app's own
  in-runtime HTTP; the MITM proxy for real-service traffic — use Mountebank for multi-protocol or one tool
  across many stacks.

## Cross-references

- `qa-api-mocking-typescript` — the **canonical** stack, Node/Vitest (`fetch` REST client +
  `bbyars/mountebank` container). Structure ported from there; this .NET port makes the same REST calls.
- `qa-api-mocking-java` — same skill, Java/TestNG (`java.net.http.HttpClient` + Jackson). Same REST
  choreography.
- `references/wiremock.md` — the **standalone-server peer** and the in-process one
  (`WireMock.Net`). Both replace the dependency and keep a journal; **Mountebank adds multiple protocols and is
  stack-agnostic**, **WireMock is richer on HTTP and runs in-process** (Mountebank never does).
- `references/msw.md` — the **in-runtime vs standalone-server** contrast (MSW is a Node sidecar
  in .NET; keeps **no** journal; Mountebank is a separate server that *does*).
- Prism — the **OpenAPI-spec-driven** member; same stack-agnostic CLI/container + thin-client port
  story as Mountebank.
- `qa-network-monitoring-dotnet` — out-of-browser MITM proxy on a *real* service's traffic;
  Mountebank *replaces* the service. Mirror its fault-injection framing.
- `qa-api-client-writer-dotnet` + `qa-api-test-author-generator-dotnet` — the typed client / API tests pointed
  at the imposter base URL (constructor injection).
- `qa-test-environments-dotnet` + `qa-db-testing-testcontainers-dotnet` — the container run mode + the
  per-fixture-vs-per-test lifecycle trade-off mirrored here.
- `qa-ci-pipelines-dotnet` — runs these tests; the container run mode needs Docker available.
