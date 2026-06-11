# QA — Out-of-Browser MITM Proxy (C# / .NET, `Titanium.Web.Proxy`)

Stands up an **out-of-process MITM HTTP(S) proxy** with [`Titanium.Web.Proxy`](https://github.com/justcoding121/titanium-web-proxy) on .NET 8 + NUnit to capture, assert, and fault-inject traffic when **there is no Playwright in the picture** — the client under test is a Selenium WebDriver, an Appium driver, an `HttpClient`, or a multi-process system. The proxy sits between the client and the network; you point the client at the proxy endpoint, then **record** what it sent, **assert** a specific request fired, and **inject faults** (abort, rewrite a response). Cross-browser and cross-client by construction — the cost is **TLS interception**: the client must trust the proxy's root certificate.

This is the **.NET port of the canonical** `qa/typescript/skills/network-monitoring`. ⚠ Unlike the `playwright-routes`/`cdp` siblings (which all drive the *same* Playwright API), the three proxy stacks use **genuinely different libraries** — there is no line-by-line port. What carries over is the **structure and the five moves**: start proxy → point client at it → record/assert → fault-inject → trust CA. The binding difference here: `Titanium.Web.Proxy` is **event-driven** — you subscribe `proxy.BeforeRequest` / `proxy.BeforeResponse` (`async Task` handlers over `SessionEventArgs`) rather than registering match→response rules.

Built on the same wrapper discipline as `qa/dotnet/skills/network-monitoring` and `cdp/dotnet`: the proxy and every capture/fault handler are wrapped in one intent-revealing `ProxyControls` helper exposed through `BaseTest`, never raw `proxy.BeforeRequest += …` scattered across `[Test]` methods. Async all the way; every wait is conditional on a captured-request signal or a real client signal; there is **no `Thread.Sleep` / `Task.Delay`-as-a-wait** anywhere in this skill.

> **Why this skill exists.** `playwright-routes` and `cdp` both require a Playwright `IPage`. The moment your stack is Selenium / Appium / `HttpClient` / multiple processes, neither applies. An external MITM proxy works for **any** client that honors proxy settings, across **any** browser. You pay with CA-trust setup and an extra process to start/stop.

## Stack

- .NET 8, C# (nullable reference types enabled), async all the way (`*Async`, never `.Result`/`.Wait()`)
- [`Titanium.Web.Proxy`](https://www.nuget.org/packages/Titanium.Web.Proxy) — `ProxyServer`, `ExplicitProxyEndPoint`, `BeforeRequest`/`BeforeResponse` events, `CertificateManager`
- NUnit 4.x + `Selenium.WebDriver` (or Appium .NET client) as the **client under test**; a bare `HttpClient` through a `WebProxy` also works
- Proxy helpers under `Tests/Support/Proxy/`, recorded archives under `Tests/Artifacts/Har/`
- These tests run in CI under `qa/dotnet/skills/ci-pipelines`: the job starts/stops the proxy and the client must **trust the per-run root certificate** (no long-lived secret — generated/trusted fresh each run)

## When to use

- Capturing or asserting the HTTP(S) calls a **Selenium / Appium / `HttpClient`** test makes, where `RouteAsync` is unavailable
- **Asserting** a request fired with the expected method / URL / payload / headers from a non-Playwright client
- **Fault-injecting** from outside the browser: abort the session, rewrite a `200` to a `500`, or serve a canned body
- **Recording** the traffic of a multi-process flow for debugging or determinism
- Driving the **same** capture/assert/fault logic across Chrome, Firefox, Edge, or a mobile app — one proxy, every client

## When NOT to use

- In-Playwright request routing → `qa/dotnet/skills/network-monitoring` (reach for it first **if** you have an `IPage`)
- Raw CDP hooks (real throttling, cache disable, `securityDetails`, `Performance` metrics) → `qa/dotnet/skills/network-monitoring`
- The TypeScript / Java proxy stacks → `qa/{typescript,java}/skills/network-monitoring`
- Writing the page objects / test classes themselves → the relevant `qa/dotnet/skills/ui-test-author/*` sibling

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Which client** — Selenium WebDriver (which browser?), Appium, or `HttpClient`? This decides how you point it at the proxy endpoint.
2. **Intent** — record/assert a request, or inject a fault (abort / rewrite a status)? And is the target **HTTPS** (→ CA-trust step) or plain HTTP?
3. **The signal** — which captured request (method + URL) or client-visible state proves the flow completed, so the assertion can wait on it instead of sleeping?

## Decision matrix — `Titanium.Web.Proxy` moves used in tests

| Goal | `Titanium.Web.Proxy` call | Notes |
|---|---|---|
| Start the proxy | `new ProxyServer()` → `AddEndPoint(new ExplicitProxyEndPoint(IPAddress.Loopback, 0, decryptSsl: true))` → `Start()` | `decryptSsl: true` is required to read HTTPS; port `0` = OS-assigned |
| Trust the root cert (HTTPS) | `proxy.CertificateManager.EnsureRootCertificate()` + `TrustRootCertificate(userTrusted: true)` | Or pass `proxy.CertificateManager.RootCertificate` to the client |
| Capture a request | `proxy.BeforeRequest += OnRequestAsync` | `e.HttpClient.Request.Url`/`.Method`/`.Headers`; `await e.GetRequestBodyAsString()` |
| Capture / rewrite a response | `proxy.BeforeResponse += OnResponseAsync` | `e.HttpClient.Response.StatusCode`; `await e.GetResponseBodyAsString()` / `e.SetResponseBodyString(...)` |
| Canned response / fault | in `BeforeRequest`: `e.Ok(json)` / `e.GenericResponse(body, HttpStatusCode.InternalServerError)` / `e.Respond(new Response(...))` | Short-circuits before hitting the network |
| Abort the session | `e.TerminateSession()` | Simulate a dropped/refused connection |
| Find the proxy address | `endPoint.Port` after `Start()` | `http://127.0.0.1:{endPoint.Port}` is what the client points at |
| Stop the proxy | `proxy.Stop()` | In `[TearDown]`; unhooks events and releases the port |

## Patterns

### The proxy helper — `Tests/Support/Proxy/ProxyControls.cs`

One helper owns the proxy lifecycle, the root cert, the captured traffic, and the intent-named capture/fault handlers. Tests call `Proxy.RecordAll()`, `Proxy.FailPostWith(url, 500)`, `Proxy.WaitForRequestAsync(...)` — never raw `Titanium` event wiring.

```csharp
using System.Collections.Concurrent;
using System.Net;
using Titanium.Web.Proxy;
using Titanium.Web.Proxy.EventArguments;
using Titanium.Web.Proxy.Models;

namespace Example.Tests.Support.Proxy;

/// <summary>A request captured off the wire in BeforeRequest, normalized for assertions.</summary>
public sealed record SeenRequest(string Method, string Url, IReadOnlyDictionary<string, string> Headers, string Body);

public sealed class ProxyControls : IAsyncDisposable
{
    private readonly ProxyServer _proxy;
    private readonly ExplicitProxyEndPoint _endPoint;
    private readonly ConcurrentBag<SeenRequest> _captured = [];
    private readonly ConcurrentDictionary<Func<SeenRequest, bool>, TaskCompletionSource<SeenRequest>> _waiters = new();
    private readonly Dictionary<string, int> _faults = new(StringComparer.OrdinalIgnoreCase);

    private ProxyControls()
    {
        _proxy = new ProxyServer();
        _endPoint = new ExplicitProxyEndPoint(IPAddress.Loopback, 0, decryptSsl: true);
        _proxy.AddEndPoint(_endPoint);
        _proxy.BeforeRequest += OnRequestAsync;
    }

    /// <summary>Start an HTTPS-intercepting proxy and ensure its root cert exists/trusted.</summary>
    public static ProxyControls Start()
    {
        var controls = new ProxyControls();
        // Generate + trust the per-run CA so intercepted HTTPS decrypts. Fresh, ephemeral.
        controls._proxy.CertificateManager.EnsureRootCertificate();
        controls._proxy.CertificateManager.TrustRootCertificate(userTrusted: true);
        controls._proxy.Start();
        return controls;
    }

    /// <summary>The address to hand to the client's proxy settings.</summary>
    public string Url => $"http://127.0.0.1:{_endPoint.Port}";

    /// <summary>PEM of the root cert the client must trust to decrypt HTTPS.</summary>
    public string RootCertPem =>
        new string(System.Security.Cryptography.X509Certificates.PemEncoding.Write(
            "CERTIFICATE", _proxy.CertificateManager.RootCertificate!.RawData));

    /// <summary>Force the matching POST to fail so the client's error path runs (fault injection).</summary>
    public void FailPostWith(string urlSubstring, int status) => _faults[urlSubstring] = status;

    /// <summary>Resolve when a request matching the predicate is first seen, or reject on deadline.</summary>
    public Task<SeenRequest> WaitForRequestAsync(Func<SeenRequest, bool> predicate, TimeSpan? timeout = null)
    {
        var already = _captured.FirstOrDefault(predicate);
        if (already is not null) return Task.FromResult(already);

        var tcs = new TaskCompletionSource<SeenRequest>(TaskCreationOptions.RunContinuationsAsynchronously);
        _waiters[predicate] = tcs;
        return tcs.Task.WaitAsync(timeout ?? TimeSpan.FromSeconds(10)); // deadline, NOT a sleep
    }

    public IReadOnlyCollection<SeenRequest> SeenRequests => _captured.ToArray();

    private async Task OnRequestAsync(object sender, SessionEventArgs e)
    {
        var request = e.HttpClient.Request;
        var headers = request.Headers.ToDictionary(h => h.Name, h => h.Value, StringComparer.OrdinalIgnoreCase);
        var body = request.HasBody ? await e.GetRequestBodyAsString() : string.Empty;
        var seen = new SeenRequest(request.Method, request.Url, headers, body);

        _captured.Add(seen);
        foreach (var (predicate, tcs) in _waiters)
            if (predicate(seen)) tcs.TrySetResult(seen);

        // Fault injection: short-circuit before the network when a rule matches.
        var fault = _faults.FirstOrDefault(f => request.Url.Contains(f.Key, StringComparison.OrdinalIgnoreCase));
        if (fault.Key is not null)
            e.GenericResponse("{\"error\":\"simulated\"}", (HttpStatusCode)fault.Value,
                [new HttpHeader("content-type", "application/json")]);
    }

    public async ValueTask DisposeAsync()
    {
        _proxy.BeforeRequest -= OnRequestAsync;
        _proxy.Stop();
        await ValueTask.CompletedTask;
    }
}
```

Expose it on `BaseTest` so test classes get `Proxy` ready in `[SetUp]`:

```csharp
public abstract class ProxyBaseTest
{
    protected ProxyControls Proxy { get; private set; } = default!;

    [SetUp]
    public void StartProxy() => Proxy = ProxyControls.Start();

    [TearDown]
    public async Task StopProxy() => await Proxy.DisposeAsync();
}
```

### Point the client at the proxy — Selenium WebDriver

The whole reason this node exists: there is no `IPage`, so you wire the proxy into the **client's** settings. For a browser via Selenium, set the proxy **and trust the root cert** so HTTPS decrypts.

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;

namespace Example.Tests.Support.Proxy;

public static class SeleniumClient
{
    public static IWebDriver ChromeThroughProxy(ProxyControls proxy)
    {
        var options = new ChromeOptions();
        options.AddArgument($"--proxy-server={proxy.Url}");
        // Trust the proxy root cert so intercepted HTTPS doesn't error. Prefer importing
        // proxy.RootCertPem into the OS store in CI; this flag is the test-only shortcut.
        options.AddArgument("--ignore-certificate-errors");
        return new ChromeDriver(options);
    }
}
```

```csharp
// A bare HttpClient through the proxy (no browser at all)
public static HttpClient ClientThroughProxy(ProxyControls proxy) =>
    new(new HttpClientHandler
    {
        Proxy = new WebProxy(proxy.Url),
        UseProxy = true,
        // Trust the proxy root cert cleanly (preferred over a blanket accept-all).
        ServerCertificateCustomValidationCallback = (_, cert, _, _) =>
            cert is not null && proxy.RootCertPem.Contains(
                Convert.ToBase64String(cert.GetCertHash())[..8]), // illustrative; pin to the proxy CA in real code
    });
```

For **Appium**, set the device/driver proxy capabilities (`appium:proxy` / device Wi-Fi proxy) and import `proxy.RootCertPem` into the device trust store — the identical capture/fault helpers then apply unchanged.

### Assert a request fired — method + payload + headers

```csharp
[TestFixture]
public class CheckoutProxyTests : ProxyBaseTest
{
    [Test]
    public async Task Should_Post_The_Cart_Total_When_The_User_Places_The_Order()
    {
        // Start the wait BEFORE driving the client.
        var seen = Proxy.WaitForRequestAsync(r => r.Method == "POST" && r.Url.Contains("/api/checkout"));

        using var driver = SeleniumClient.ChromeThroughProxy(Proxy);
        driver.Navigate().GoToUrl("https://shop.example.com/cart");
        driver.FindElement(By.CssSelector("[data-test='place-order']")).Click();

        var request = await seen; // resolves when the POST is observed; throws on deadline
        var body = System.Text.Json.JsonDocument.Parse(request.Body).RootElement;
        Assert.Multiple(() =>
        {
            Assert.That(body.GetProperty("totalMinor").GetInt32(), Is.EqualTo(15_000));
            Assert.That(body.GetProperty("currency").GetString(), Is.EqualTo("EUR"));
            Assert.That(request.Headers["x-tenant"], Is.EqualTo("tenant-42"));
        });
    }
}
```

`WaitForRequestAsync` completes on a real wire event and times out on a deadline — it is **not** a sleep. The `Assert.Multiple` is **one logical assertion** ("the checkout POST carried the right cart").

### Asserting a request was **not** sent

There is no negative wait. Drive the flow to a **client-visible completion signal**, then assert the captured list holds none matching.

```csharp
[Test]
public void Should_Not_Call_The_Legacy_Pricing_Endpoint_When_Recalculating()
{
    using var driver = SeleniumClient.ChromeThroughProxy(Proxy);
    driver.Navigate().GoToUrl("https://shop.example.com/cart");
    driver.FindElement(By.CssSelector("[data-test='recalculate']")).Click();

    // A real signal the flow finished — never a fixed sleep.
    new OpenQA.Selenium.Support.UI.WebDriverWait(driver, TimeSpan.FromSeconds(10))
        .Until(d => d.FindElements(By.CssSelector("[data-test='cart-total']")).Count > 0);

    Assert.That(Proxy.SeenRequests.Any(r => r.Url.Contains("/api/legacy-pricing")), Is.False,
        "legacy pricing endpoint should be retired");
}
```

### Inject a fault — rewrite, abort

```csharp
[Test]
public void Should_Show_The_Error_Banner_When_The_Orders_API_Returns_500()
{
    Proxy.FailPostWith("/api/orders", 500); // BeforeRequest short-circuits with a 500

    using var driver = SeleniumClient.ChromeThroughProxy(Proxy);
    driver.Navigate().GoToUrl("https://shop.example.com/orders");
    driver.FindElement(By.CssSelector("[data-test='refresh']")).Click();

    new OpenQA.Selenium.Support.UI.WebDriverWait(driver, TimeSpan.FromSeconds(10))
        .Until(d => d.FindElements(By.CssSelector("[role='alert']")).Count > 0);
}
```

To **abort** instead of rewrite, call `e.TerminateSession()` in `BeforeRequest` (expose a `Proxy.Abort(url)` rule mirroring `FailPostWith`) — it drops the connection so the client's dropped-socket path runs.

### Record traffic for debugging / determinism

`SeenRequests` is the assertable artifact; for a reviewable archive, accumulate request+response pairs in `BeforeResponse` and serialize a minimal HAR. **Scrub auth headers** before writing.

```csharp
// In ProxyControls: subscribe BeforeResponse, push { method, url, status, safeHeaders } into a list,
// then await File.WriteAllTextAsync(path, JsonSerializer.Serialize(new { log = new { version = "1.2", entries } })).
// Never persist Authorization / Cookie headers.
```

## Rules

### Proxy lifecycle
- One proxy per test owned by `BaseTest`: `ProxyServer` → `AddEndPoint` → `Start()` → **`Stop()` + unsubscribe events in `[TearDown]`** (here via `IAsyncDisposable`). A leaked proxy holds its port and keeps intercepting.
- Subscribe `BeforeRequest`/`BeforeResponse` **before** the client action that fires the request.
- Generate/trust the root cert per run; never reuse a static cert across machines as a long-lived secret.

### TLS interception (the caveat that bites everyone)
- **HTTPS interception requires the client to trust the proxy root cert.** Use `ExplicitProxyEndPoint(..., decryptSsl: true)` + `CertificateManager.EnsureRootCertificate()` + `TrustRootCertificate(userTrusted: true)`, then trust `proxy.RootCertPem` on the client (import to the OS store in CI, pin it in the `HttpClient` validation callback, or — test-only — `--ignore-certificate-errors` for a throwaway browser).
- Plain-HTTP targets need no CA step; state per test which scheme the target uses.

### Pointing the client
- The proxy is useless until the **client** routes through it: Selenium `--proxy-server={proxy.Url}`, `HttpClientHandler.Proxy = new WebProxy(proxy.Url)`, or Appium proxy capabilities. This is the whole point — make it explicit.
- Capture/fault on the **narrowest** URL match that works so unrelated traffic still passes through and recordings stay readable.

### Assertions & waits
- **No `Thread.Sleep` / `Task.Delay`-as-a-wait.** Wait on `WaitForRequestAsync(pred)` (completes on a wire event, throws on a deadline) or a real client-visible signal (`WebDriverWait`). A longer deadline is a *deadline*, not a sleep.
- **Listener before action**: start `WaitForRequestAsync` *before* driving the client; awaiting after races the request.
- Read the payload with `await e.GetRequestBodyAsString()` (captured into `SeenRequest.Body`) and the headers map — don't re-parse raw bytes.
- A "not called" assertion checks `SeenRequests` **after** a client-visible completion signal — never after a sleep.
- Never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` on a proxy or Selenium call — async all the way.

### Hygiene
- Wrap all `Titanium` event wiring in the `ProxyControls` helper with intent names — no raw `proxy.BeforeRequest += …` in `[Test]` methods.
- Never persist auth headers / tokens / PII into a recorded HAR — scrub before writing.
- Don't reach for the proxy when you actually have a Playwright `IPage` — `RouteAsync` is simpler and needs no CA. Justify the choice (non-Playwright client / multi-process).

### What NOT to do
- No proxy without pointing a client at `proxy.Url` — it intercepts nothing.
- No HTTPS interception without `decryptSsl: true` **and** a trusted root cert — the client errors on every TLS handshake.
- No `Thread.Sleep`/`Task.Delay` to "wait for the request" — use `WaitForRequestAsync` or a client signal.
- No raw `Titanium` event wiring scattered through tests — wrap it in `ProxyControls`.
- No static/committed root cert reused as a secret — generate per run.
- No blanket accept-all TLS in a real client — pin to the proxy CA / scope to the test.
- No auth headers or secrets persisted in a HAR.
- No `.Result`/`.Wait()` on a proxy or Selenium call.
- No proxy where a Playwright `RouteAsync` (no CA, in-process) expresses the test just as well.

## Generation steps

1. Confirm **which client** (Selenium / Appium / `HttpClient`), **intent** (record/assert vs fault), and whether the target is **HTTPS** (→ CA-trust step).
2. Add or extend `Tests/Support/Proxy/ProxyControls.cs` — `Start()` with `decryptSsl: true` + root-cert ensure/trust, `BeforeRequest` capture + fault short-circuit, `WaitForRequestAsync`/`SeenRequests`, `Stop()` + unsubscribe in `DisposeAsync`. Expose it on `ProxyBaseTest`.
3. Point the client at `proxy.Url` (`ChromeThroughProxy` / `WebProxy` / Appium caps) and **trust `proxy.RootCertPem`** for HTTPS.
4. Subscribe before the action; assert via `WaitForRequestAsync` (payload from `request.Body`) or `SeenRequests`, waiting only on wire events / client signals.
5. For determinism/debugging, record a scrubbed HAR from `BeforeResponse` under `Tests/Artifacts/Har/`.
6. Run `dotnet test`; build with nullable warnings as errors. In CI, ensure the job trusts the per-run root cert before the client starts.

## Cross-references

- **`qa/dotnet/skills/network-monitoring`** — in-Playwright routing; reach for it first **if** you have an `IPage`. The proxy is for when you don't.
- **`qa/dotnet/skills/network-monitoring`** — raw CDP hooks below routing (Playwright + Chromium only); the proxy covers the cross-client case CDP can't.
- **`qa/typescript/skills/network-monitoring`** — the **canonical** skill this ports the *structure* from (`mockttp`); consult it for the conceptual model and the three-way pick.
- **`qa/java/skills/network-monitoring`** — the sibling Java port (`BrowserUp Proxy` + Selenium, native HAR).
- **`qa/dotnet/skills/ci-pipelines`** — runs these tests; the job starts/stops the proxy and trusts the per-run root cert before the client launches (no long-lived secret).
