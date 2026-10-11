# QA — Out-of-Browser MITM Proxy (.NET 10 / `Titanium.Web.Proxy` + NUnit)

Stands up an **out-of-process MITM HTTP(S) proxy** with `Titanium.Web.Proxy` to capture, assert and
fault-inject traffic when **there is no Playwright in the picture** — the client under test is Selenium
WebDriver, an Appium driver, an `HttpClient`, or several processes. The proxy sits between the client and the
network: point the client at it, then **read** what it sent, **assert** on it, and **inject faults** (a forced
status, a dropped connection). Cross-browser and cross-client by construction; the cost is **TLS
interception** — the client must trust the proxy's root certificate.

The proxy and every capture and fault rule live in one `ProxyControls` helper with intent names, built in the
class's `[SetUp]` and stopped in its `[TearDown]` — never `proxy.BeforeRequest += …` in a test. Every wait is
a client-visible signal; there is no `Thread.Sleep` and no `Task.Delay` in this file.

> **Why this reference exists.** `references/playwright-routes.md` and `references/cdp.md` both need a
> Playwright `IPage`. The moment the client is Selenium, Appium or `HttpClient`, neither applies. With an
> `IPage`, routing is simpler and needs no certificate — use it.

## Stack

| Package | Version | Facts (NuGet, 2026-10-11) |
|---|---|---|
| `Titanium.Web.Proxy` | **7.0.22** | Published 2026-10-10; targets net10.0 only (a net8/net9 project stays on its current 3.x and checks its API); brings `Titanium.Web.Proxy.Abstractions` and `BouncyCastle.Cryptography` |
| `Selenium.WebDriver` + `Selenium.Support` | **4.51.0** | The client in the samples; `Selenium.Support` holds `WebDriverWait` |

```xml
<PackageVersion Include="Titanium.Web.Proxy" Version="7.0.22" />
<PackageVersion Include="Selenium.WebDriver" Version="4.51.0" />
<PackageVersion Include="Selenium.Support" Version="4.51.0" />
```

`Directory.Packages.props` carries the versions; the project's `PackageReference` lines carry none. The API
below was read from the `Titanium.Web.Proxy` sources at the 7.0.22 release commit.

## When to use

- Capture or assert the HTTP(S) calls a **Selenium / Appium / `HttpClient`** test makes, where routing is
  unavailable.
- Assert a request fired with the expected method and payload — or did **not** fire.
- **Fault-inject** from outside the client: force a `500`, or drop the connection.
- Record the traffic of a failing multi-process flow as evidence.

## When NOT to use

- A Playwright `IPage` exists → `references/playwright-routes.md` (no certificate, in-process)
- Real throttling, cache disable, performance metrics → `references/cdp.md`
- The TypeScript and Java proxy stacks → `qa-typescript:network-mocking` (mockttp), `qa-java:network-mocking`
  (BrowserUp)
- Writing the Selenium or Appium page objects themselves → `qa/dotnet/skills/ui-test-author/selenium`,
  `qa/dotnet/skills/ui-test-author/appium`

## Inputs needed

1. **Which client** — Selenium (which browser?), Appium, or `HttpClient`. It decides how the client is pointed
   at the proxy.
2. **Intent** — read and assert, or inject a fault; and is the target **HTTPS** (the certificate step)?
3. **The signal** — which client-visible state proves the flow finished, so the assertion reads the captured
   traffic after it.

## Decision matrix — the `Titanium.Web.Proxy` moves

| Goal | Call | Notes |
|---|---|---|
| Create the proxy | `new ProxyServer(userTrustRootCertificate: false)` | The parameterless constructor defaults to `true`, and `Start()` then installs the root CA in the current user's trust store |
| Listen | `AddEndPoint(new ExplicitProxyEndPoint(IPAddress.Loopback, 0, decryptSsl: true))` | Port `0` = OS-assigned; `endPoint.Port` holds the real port after `Start` |
| Start | `Start(changeSystemProxySettings: false)` | Leaves the machine's proxy settings alone; creates the root certificate when an endpoint decrypts |
| Capture a request | `BeforeRequest += OnRequestAsync` | `e.HttpClient.Request.Method` / `.Url` / `.Headers` / `.HasBody`; `await e.GetRequestBodyAsString()` |
| Canned response or fault | `e.GenericResponse(body, HttpStatusCode, headers)` / `e.Ok(body)` | Short-circuits before the network |
| Drop the connection | `e.TerminateSession()` | The client's dropped-socket path |
| Trust in the client | `CertificateManager.RootCertificate` | Pin it in the client; never install it in the OS store from a test |
| Stop | `BeforeRequest -= …`, `await StopAsync()`, `Dispose()` | In `[TearDown]` |

## 1. The helper — `Support/Proxy/ProxyControls.cs`

```csharp
using System.Collections.Concurrent;
using System.Net;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Titanium.Web.Proxy;
using Titanium.Web.Proxy.EventArguments;
using Titanium.Web.Proxy.Models;

namespace Example.UiTests.Support.Proxy;

public sealed record SeenRequest(string Method, string Url, ILookup<string, string> Headers, string Body);

public sealed class ProxyControls : IAsyncDisposable
{
    private static readonly IReadOnlySet<string> SecretHeaders = new HashSet<string>(["authorization", "cookie"], StringComparer.OrdinalIgnoreCase);
    private readonly ProxyServer _proxy = new(userTrustRootCertificate: false);
    private readonly ExplicitProxyEndPoint _endPoint = new(IPAddress.Loopback, 0, decryptSsl: true);
    private readonly ConcurrentQueue<SeenRequest> _seen = new();
    private readonly ConcurrentDictionary<string, HttpStatusCode> _faults = new();

    private ProxyControls()
    {
        _proxy.AddEndPoint(_endPoint);
        _proxy.BeforeRequest += OnRequestAsync;
    }

    public static ProxyControls Start()
    {
        var controls = new ProxyControls();
        controls._proxy.Start(changeSystemProxySettings: false);
        return controls;
    }

    public string Url => $"http://127.0.0.1:{_endPoint.Port}";

    public IReadOnlyList<SeenRequest> SeenRequests => _seen.ToArray();

    public void FailRequestsTo(string urlPart, HttpStatusCode status) => _faults[urlPart] = status;

    public bool IssuedByProxy(X509Certificate2? certificate)
    {
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        chain.ChainPolicy.CustomTrustStore.Add(_proxy.CertificateManager.RootCertificate!);
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        return certificate is not null && chain.Build(certificate);
    }

    public async Task WriteTrafficLogAsync(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var log = _seen.Select(request => new
        {
            request.Method,
            request.Url,
            Headers = request.Headers
                .Where(header => !SecretHeaders.Contains(header.Key))
                .ToDictionary(header => header.Key, header => string.Join(", ", header)),
        });
        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(log, new JsonSerializerOptions { WriteIndented = true }));
    }

    private async Task OnRequestAsync(object sender, SessionEventArgs e)
    {
        var request = e.HttpClient.Request;
        var body = request.HasBody ? await e.GetRequestBodyAsString() : string.Empty;
        _seen.Enqueue(new SeenRequest(request.Method, request.Url, request.Headers.ToLookup(header => header.Name, header => header.Value, StringComparer.OrdinalIgnoreCase), body));
        var fault = _faults.FirstOrDefault(rule => request.Url.Contains(rule.Key, StringComparison.OrdinalIgnoreCase));
        if (fault.Key is not null)
        {
            e.GenericResponse("""{"title":"Simulated failure"}""", fault.Value, new[] { new HttpHeader("content-type", "application/problem+json") });
        }
    }

    public async ValueTask DisposeAsync()
    {
        _proxy.BeforeRequest -= OnRequestAsync;
        await _proxy.StopAsync();
        _proxy.Dispose();
    }
}
```

- **The root certificate never reaches the OS trust store.** `userTrustRootCertificate: false` stops `Start()`
  from installing it in the current user's store, and `changeSystemProxySettings: false` leaves the machine's
  proxy settings alone — a test run changes nothing outside itself. The client trusts the per-run root
  explicitly (§2).
- **`IssuedByProxy`** validates a server certificate against the proxy's root only (`CustomRootTrust`), so an
  `HttpClient` accepts exactly the proxy's certificates and nothing else — never an accept-all callback.
- **Captured requests are thread-safe.** `BeforeRequest` runs on the proxy's threads, so the requests go into a
  `ConcurrentQueue` and the fault rules into a `ConcurrentDictionary`; a test reads a snapshot.
- **Headers are a lookup**: a name can repeat, and the lookup is case-insensitive, so
  `request.Headers["x-tenant"]` is the sequence of values (empty when absent).
- **The traffic log is scrubbed** of `Authorization` and `Cookie` before it is written; bodies are left out.
- The one `if` and the fault lookup live in the helper; tests stay straight lines.

## 2. Point the client at the proxy

The proxy is useless until the **client** routes through it.

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;

namespace Example.UiTests.Support.Proxy;

public static class ProxiedClients
{
    public static IWebDriver Chrome(ProxyControls proxy)
    {
        var options = new ChromeOptions();
        options.AddArgument("--headless=new");
        options.AddArgument($"--proxy-server={proxy.Url}");
        options.AddArgument("--proxy-bypass-list=<-loopback>");
        options.AddArgument("--ignore-certificate-errors");
        return new ChromeDriver(options);
    }

    public static HttpClient Http(ProxyControls proxy) =>
        new(new HttpClientHandler
        {
            Proxy = new WebProxy(proxy.Url),
            UseProxy = true,
            ServerCertificateCustomValidationCallback = (_, certificate, _, _) => proxy.IssuedByProxy(certificate),
        });
}
```

- **Chrome** routes through `--proxy-server`. Chrome never proxies `localhost` unless the bypass list removes
  the implicit loopback rule (`<-loopback>`). `--ignore-certificate-errors` is acceptable only in a throwaway
  test browser; it is what lets the proxy's per-run certificates through without touching the OS store.
- **`HttpClient`** pins the proxy's root through `IssuedByProxy` (§1).
- **Appium** sets the device's proxy (Wi-Fi proxy or the driver's proxy capability) and installs the
  certificate from `CertificateManager.RootCertificate` on the device or emulator; the helper is unchanged.

## 3. The page object, the hooks and the tests

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Support.UI;

namespace Example.UiTests.Pages.Selenium;

public sealed class CartScreen(IWebDriver driver, string baseUrl)
{
    private static readonly By Total = By.CssSelector("[data-testid='Cart.Total']");
    private static readonly By Status = By.CssSelector("[data-testid='Cart.Status']");
    private static readonly By PlaceOrderButton = By.CssSelector("[data-testid='Cart.PlaceOrder']");
    private static readonly By RecalculateButton = By.CssSelector("[data-testid='Cart.Recalculate']");
    private static readonly By Outcome = By.CssSelector("[data-testid='Order.Confirmation'], [role='alert']");
    private readonly WebDriverWait _wait = new(driver, TimeSpan.FromSeconds(10));

    public void Open()
    {
        driver.Navigate().GoToUrl($"{baseUrl}/cart");
        _wait.Until(d => d.FindElement(Total).Displayed);
    }

    public string PlaceOrder()
    {
        driver.FindElement(PlaceOrderButton).Click();
        return _wait.Until(d => d.FindElements(Outcome).FirstOrDefault(element => element.Displayed)?.Text);
    }

    public void Recalculate()
    {
        driver.FindElement(RecalculateButton).Click();
        _wait.Until(d => d.FindElement(Status).Text == "Total updated");
    }
}
```

```csharp
using System.Net;
using System.Text.Json;
using Example.UiTests.Pages.Selenium;
using Example.UiTests.Support;
using Example.UiTests.Support.Proxy;
using NUnit.Framework;
using NUnit.Framework.Interfaces;
using OpenQA.Selenium;

namespace Example.UiTests.Tests;

[Category("proxy")]
public class CheckoutProxyTests
{
    private ProxyControls _proxy = null!;
    private IWebDriver _driver = null!;
    private CartScreen _cart = null!;

    [SetUp]
    public void StartProxyAndBrowser()
    {
        _proxy = ProxyControls.Start();
        _driver = ProxiedClients.Chrome(_proxy);
        _cart = new CartScreen(_driver, BaseTest.RequiredEnv("BASE_URL"));
    }

    [TearDown]
    public async Task StopBrowserAndProxy()
    {
        if (TestContext.CurrentContext.Result.Outcome.Status == TestStatus.Failed)
        {
            var log = Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-artifacts", $"{GetType().Name}.{TestContext.CurrentContext.Test.Name}.traffic.json");
            await _proxy.WriteTrafficLogAsync(log);
            TestContext.AddTestAttachment(log, "proxy traffic");
        }
        _driver.Quit();
        await _proxy.DisposeAsync();
    }

    [Test]
    public void Should_PostCartTotal_When_OrderIsPlaced()
    {
        _cart.Open();

        _cart.PlaceOrder();

        var checkouts = _proxy.SeenRequests
            .Where(request => request.Method == "POST" && request.Url.EndsWith("/api/checkout"))
            .Select(request => JsonSerializer.Deserialize<CheckoutRequest>(request.Body, JsonSerializerOptions.Web))
            .ToList();
        Assert.That(checkouts, Is.EqualTo(new[] { new CheckoutRequest(15_000, "EUR") }), "checkout POSTs seen by the proxy");
    }

    [Test]
    public void Should_NotCallLegacyPricing_When_CartIsRecalculated()
    {
        _cart.Open();

        _cart.Recalculate();

        Assert.That(_proxy.SeenRequests.Select(request => request.Url).Where(url => url.Contains("/api/legacy-pricing")), Is.Empty, "legacy pricing calls seen by the proxy");
    }

    [Test]
    public void Should_ShowOrderError_When_CheckoutReturns500()
    {
        _proxy.FailRequestsTo("/api/checkout", HttpStatusCode.InternalServerError);
        _cart.Open();

        var outcome = _cart.PlaceOrder();

        Assert.That(outcome, Is.EqualTo("We couldn't place your order"), "message shown when checkout fails with 500");
    }
}
```

- **No Playwright here, so no `BaseTest`.** The class owns the proxy and the driver through its own
  `[SetUp]` / `[TearDown]`; the cleanup is in the hook, never a `using var` or `try`/`finally` in a test.
  `BaseTest.RequiredEnv` is public and static, so `BASE_URL` is read the same way as in the Playwright lane.
- **Every read comes after a client-visible signal.** `PlaceOrder()` returns once the confirmation or the error
  is displayed, `Recalculate()` once the status says so; the captured list is read after that. A "not called"
  check read before the signal passes only because the request had not fired yet.
- **The checkout assertion is one comparison**: the list of deserialized checkout bodies equals exactly one
  expected record. No checkout, two checkouts or a different total all fail, and NUnit prints the list.
- **On failure the scrubbed traffic log** lands in `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.traffic.json`
  — the folder the UI job already uploads on failure — and is attached to the TRX.
- `CheckoutRequest` is the payload record from `references/playwright-routes.md` §1; `JsonSerializerOptions.Web`
  reads camelCase bodies.
- `[Category("proxy")]` lets a run without Chrome or without network access leave the class out.
- To **drop** the connection instead of answering, add a rule that calls `e.TerminateSession()` in
  `OnRequestAsync`, mirroring `FailRequestsTo`.

## Rules

### Proxy lifecycle

- One proxy per test, started in `[SetUp]` and stopped in `[TearDown]` (`BeforeRequest -=`, `StopAsync()`,
  `Dispose()`). A leaked proxy holds its port and keeps intercepting.
- Register the capture before the client action that fires the request — `ProxyControls` does it in its
  constructor.
- `new ProxyServer(userTrustRootCertificate: false)` and `Start(changeSystemProxySettings: false)` — a test
  never changes the machine's trust store or proxy settings.

### TLS interception

- HTTPS needs `decryptSsl: true` on the endpoint **and** a client that trusts the per-run root: pinned in an
  `HttpClient` callback, installed on an Appium device, or `--ignore-certificate-errors` in a throwaway browser.
- Plain-HTTP targets need no certificate step; state per class which scheme the target uses.

### Assertions and waits

- No `Thread.Sleep` and no `Task.Delay` as a wait. Read `SeenRequests` after a client-visible signal.
- Assert the payload as a deserialized record against one expected value; never a boolean predicate that
  drops the body.
- `.Result` / `.Wait()` never appear; the proxy's async calls are awaited in the hooks.

### Hygiene

- All `Titanium.Web.Proxy` wiring stays inside `ProxyControls`.
- Never write `Authorization`, `Cookie`, tokens or personal data into a traffic log or a fixture.
- With a Playwright `IPage`, use routing instead — justify the proxy (non-Playwright client, several
  processes).

## What NOT to do

- No `new ProxyServer()` with its defaults in a test — it installs the root CA in the user's trust store.
- No `TrustRootCertificate(...)` / `TrustRootCertificateAsAdmin(...)` from a test run.
- No proxy without pointing a client at `proxy.Url`.
- No HTTPS interception without `decryptSsl: true` and a client that trusts the root.
- No accept-all certificate callback in an `HttpClient` — pin the proxy's root.
- No `Thread.Sleep` or `Task.Delay` to "wait for the request".
- No `using var driver` or `try`/`finally` in a test — the hooks own the driver and the proxy.
- No raw `BeforeRequest +=` in a test.
- No `request.Headers.ToDictionary(...)` — a repeated header name throws; use the lookup.
- No secrets in the traffic log.

## Generation steps

1. Confirm the **client**, the **intent** and whether the target is **HTTPS**.
2. Add or extend `ProxyControls` — capture in `BeforeRequest`, one intent method per fault, the scrubbed log.
3. Point the client at `proxy.Url` (`ProxiedClients.Chrome` / `.Http`, or Appium capabilities) and make it
   trust the per-run root.
4. Drive the flow through the page object to its completion signal, then assert on `SeenRequests` or the
   client-visible outcome.
5. On failure, read the traffic log beside the other evidence.

## Cross-references

- `references/playwright-routes.md` — in-Playwright routing; reach for it first **if** you have an `IPage`.
- `references/cdp.md` — raw CDP hooks below routing (Playwright and Chromium only).
- `qa/dotnet/skills/ui-test-author/selenium`, `qa/dotnet/skills/ui-test-author/appium` — the page objects of
  non-Playwright clients.
- `qa/cicd/dotnet/skills/ci-pipelines` — the job that runs these tests and uploads `playwright-artifacts/`.
- `qa-typescript:network-mocking` (mockttp), `qa-java:network-mocking` (BrowserUp) — the sibling proxy stacks.
