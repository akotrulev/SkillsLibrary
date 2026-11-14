# Analytics and consent with Playwright .NET (Microsoft.Playwright 1.63 + NUnit)

Every sample derives from `Example.UiTests.Support.BaseTest`
(`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`). Verified against Playwright 1.63 on Chromium and
WebKit: a `navigator.sendBeacon` to `/g/collect` is caught by a context route as a `POST` whose `PostData` holds
the beacon body, request waits resolve for routed requests, `SetExtraHTTPHeadersAsync` delivers `Sec-GPC: 1` to
the server, and gtag's `arguments` entries in the `dataLayer` read back by index.

## 1. The helpers

```csharp
using System.Collections.Concurrent;
using System.Text.RegularExpressions;
using System.Web;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed record Hit(string Destination, string EventName, IReadOnlyDictionary<string, string> Params);

public sealed class Tracker(IPage page)
{
    public const string Ga4 = "ga4";
    public const string MetaPixel = "meta-pixel";

    private static readonly Regex Ga4Collect = new(@"/g/collect(\?|$)");
    private static readonly Regex MetaPixelCollect = new(@"^https://www\.facebook\.com/tr/?(\?|$)");
    private readonly ConcurrentQueue<Hit> _captured = new();

    public async Task CaptureAsync()
    {
        await page.Context.RouteAsync(Ga4Collect, RecordAndFulfillAsync);
        await page.Context.RouteAsync(MetaPixelCollect, RecordAndFulfillAsync);
    }

    public IReadOnlyList<Hit> Hits() => _captured.ToList();

    public IReadOnlyList<Hit> HitsTo(string destination) =>
        _captured.Where(hit => hit.Destination == destination).ToList();

    public async Task<Hit> NextEventAsync(string eventName, Func<Task> action)
    {
        var request = await page.RunAndWaitForRequestAsync(action, sent => HitsOf(sent).Any(hit => hit.EventName == eventName));
        return HitsOf(request).FirstOrDefault(hit => hit.EventName == eventName)
            ?? throw new InvalidOperationException($"No {eventName} event in {request.Method} {request.Url}; body: {request.PostData}");
    }

    private async Task RecordAndFulfillAsync(IRoute route)
    {
        foreach (var hit in HitsOf(route.Request))
        {
            _captured.Enqueue(hit);
        }
        await route.FulfillAsync(new() { Status = 204 });
    }

    private static IReadOnlyList<Hit> HitsOf(IRequest request) =>
        Ga4Collect.IsMatch(request.Url) ? Ga4Hits(request) : [PixelHit(request)];

    private static IReadOnlyList<Hit> Ga4Hits(IRequest request)
    {
        var shared = ParamsOf(new Uri(request.Url).Query);
        var lines = (request.PostData ?? "").Split('\n', StringSplitOptions.RemoveEmptyEntries);
        IEnumerable<IReadOnlyDictionary<string, string>> events = lines.Length == 0
            ? [shared]
            : lines.Select(line => Merge(shared, ParamsOf(line)));
        return events.Select(parameters => new Hit(Ga4, parameters.GetValueOrDefault("en", ""), parameters)).ToList();
    }

    private static Hit PixelHit(IRequest request)
    {
        var parameters = Merge(ParamsOf(new Uri(request.Url).Query), ParamsOf(request.PostData ?? ""));
        return new Hit(MetaPixel, parameters.GetValueOrDefault("ev", ""), parameters);
    }

    private static IReadOnlyDictionary<string, string> ParamsOf(string encoded)
    {
        var query = HttpUtility.ParseQueryString(encoded);
        return query.AllKeys.OfType<string>().ToDictionary(key => key, key => query[key] ?? "");
    }

    private static IReadOnlyDictionary<string, string> Merge(IReadOnlyDictionary<string, string> shared, IReadOnlyDictionary<string, string> own) =>
        own.Concat(shared.Where(pair => !own.ContainsKey(pair.Key))).ToDictionary(pair => pair.Key, pair => pair.Value);
}
```

```csharp
using System.Text.Json;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class DataLayer(IPage page)
{
    private static readonly JsonSerializerOptions SnakeCase = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    public async Task<IReadOnlyDictionary<string, string>> ConsentStateAsync(string command)
    {
        await page.WaitForFunctionAsync(
            "command => (window.dataLayer ?? []).some(e => e[0] === 'consent' && e[1] === command)", command);
        var json = await page.EvaluateAsync<string>(
            "command => JSON.stringify(Object.fromEntries(Object.entries((window.dataLayer ?? [])"
            + ".filter(e => e[0] === 'consent' && e[1] === command).at(-1)[2]).map(([k, v]) => [k, String(v)])))",
            command);
        return JsonSerializer.Deserialize<Dictionary<string, string>>(json)
            ?? throw new InvalidOperationException($"Consent {command} state did not deserialize: {json}");
    }

    public async Task<IReadOnlyList<T>> EventsNamedAsync<T>(string eventName)
    {
        await page.WaitForFunctionAsync("name => (window.dataLayer ?? []).some(e => e.event === name)", eventName);
        var json = await page.EvaluateAsync<string>(
            "name => JSON.stringify((window.dataLayer ?? []).filter(e => e.event === name))", eventName);
        return JsonSerializer.Deserialize<List<T>>(json, SnakeCase)
            ?? throw new InvalidOperationException($"dataLayer '{eventName}' entries did not deserialize: {json}");
    }
}

public sealed class PrivacySignals(IPage page)
{
    public async Task SendGlobalPrivacyControlAsync()
    {
        await page.Context.SetExtraHTTPHeadersAsync(new Dictionary<string, string> { ["Sec-GPC"] = "1" });
        await page.Context.AddInitScriptAsync(
            "Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', { get: () => true, configurable: true })");
    }
}
```

- **`Tracker.CaptureAsync()` runs in every analytics class's `[SetUp]`**, before the first navigation. A class that
  forgets it lets hits through to the network.
- **A GA4 request can carry several events.** Shared parameters sit in the URL; with a body, each line is one
  event's parameters, and `Merge` lays each line over the shared set. That shape is observed from gtag.js, not a
  published contract (SKILL.md, *Rules*).
- **The Meta Pixel** is read from its query string (`id`, `ev`, `cd[...]` custom data — the image-pixel format
  Meta documents) and any form body.
- **`gtag()` pushes an `arguments` object**, so a consent command reads as `e[0..2]`; a GTM-style
  `dataLayer.push({ event })` reads as `e.event`. Values are stringified in the page (`wait_for_update` is a
  number) so the state comes back as `Dictionary<string, string>`.
- **The `WaitForFunctionAsync` calls are the waits** (`ui-test-author/playwright/references/assertions.md` §5):
  page state no locator matcher can see. If the push never happens they time out and fail the test.
- **A JSON deserialization failure names the payload** — the raw JSON is in the exception message.
- **The GPC init script stands in for a browser setting.** The header plus the property is what a GPC browser
  sends. Call `SendGlobalPrivacyControlAsync()` **before** the first navigation.

## 2. Consent gating

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class ConsentGatingTests : BaseTest
{
    private Tracker _tracker = null!;
    private DataLayer _dataLayer = null!;
    private ShopPage _shopPage = null!;
    private ConsentBanner _consentBanner = null!;

    [SetUp]
    public async Task CreateHelpers()
    {
        _tracker = new Tracker(Page);
        await _tracker.CaptureAsync();
        _dataLayer = new DataLayer(Page);
        _shopPage = new ShopPage(Page);
        _consentBanner = new ConsentBanner(Page);
    }

    [Test]
    public async Task Should_SendNoTrackingRequest_When_VisitorHasNotChosen()
    {
        await _shopPage.OpenHomeAsync();
        await Expect(_consentBanner.Root, "consent banner").ToBeVisibleAsync();

        await _shopPage.OpenPricingAsync();

        Assert.That(_tracker.Hits(), Is.Empty, "tracking hits before any consent choice");
    }

    [Test]
    public async Task Should_SendPageViewToTestProperty_When_VisitorAcceptsAll()
    {
        await _shopPage.OpenHomeAsync();

        var pageView = await _tracker.NextEventAsync("page_view", _consentBanner.AcceptAllAsync);

        Assert.That(pageView.Params, Does.ContainKey("tid").WithValue(RequiredEnv("GA4_TEST_MEASUREMENT_ID")),
            $"page_view hit parameters: {string.Join("&", pageView.Params)}");
    }

    [Test]
    public async Task Should_SendNoTrackingRequest_When_VisitorRejectsAll()
    {
        await _shopPage.OpenHomeAsync();
        await _consentBanner.RejectAllAsync();
        Assert.That(await _dataLayer.ConsentStateAsync("update"), Does.ContainKey("analytics_storage").WithValue("denied"),
            "consent update after reject");

        await _shopPage.OpenPricingAsync();

        Assert.That(_tracker.Hits(), Is.Empty, "tracking hits after reject");
    }

    [Test]
    public async Task Should_DefaultEveryConsentModeV2TypeToDenied_When_PageLoads()
    {
        await _shopPage.OpenHomeAsync();

        var defaults = await _dataLayer.ConsentStateAsync("default");

        Assert.That(defaults, Is.SupersetOf(new Dictionary<string, string>
        {
            ["ad_storage"] = "denied",
            ["ad_user_data"] = "denied",
            ["ad_personalization"] = "denied",
            ["analytics_storage"] = "denied",
        }), "consent default");
    }
}
```

- `ShopPage.OpenPricingAsync()` navigates and returns once the pricing landmark is visible: the second page load is
  the completion signal that gives a late tag time to fire, so the empty list means something.
- The reject test asserts the precondition (the update was pushed) before the act — it is part of one behaviour,
  "after reject nothing is sent", and without it an empty list could mean the click never registered.
- In **basic** Consent Mode no Google tag loads before the choice, so the first test's empty list is the whole
  assertion. In **advanced** mode tags load denied and send cookieless pings: replace it with §3.
- §3 and §4 are further tests of classes shaped like this one; `_checkoutPage = new CheckoutPage(Page)` is a field
  built in the same `[SetUp]`.

## 3. Advanced Consent Mode — the `gcs` value

Google documents `gcs` as carrying the `ad_storage` and `analytics_storage` choice; its encoding is not published.
Record it from your own tag in each state and pin the values as constants.

```csharp
private const string GcsAllDenied = "G100";
private const string GcsAllGranted = "G111";

[Test]
public async Task Should_SendCookielessPing_When_ConsentIsDenied()
{
    var pageView = await _tracker.NextEventAsync("page_view", _shopPage.OpenHomeAsync);

    Assert.That(pageView.Params, Does.ContainKey("gcs").WithValue(GcsAllDenied), $"page_view hit: {string.Join("&", pageView.Params)}");
}

[Test]
public async Task Should_SendGrantedPing_When_VisitorAcceptsAll()
{
    await _shopPage.OpenHomeAsync();

    var engagement = await _tracker.NextEventAsync("user_engagement", _consentBanner.AcceptAllAsync);

    Assert.That(engagement.Params, Does.ContainKey("gcs").WithValue(GcsAllGranted), $"hit after accept: {string.Join("&", engagement.Params)}");
}
```

The constants are what a gtag.js build was observed to send (`G1<ad_storage><analytics_storage>`, 1 = granted);
confirm them against a hit you recorded. Use the event your tag really sends after an update.

## 4. An event and its parameters

```csharp
public sealed record PurchasePush(string Event, Ecommerce Ecommerce);

public sealed record Ecommerce(string TransactionId, decimal Value, string Currency);
```

```csharp
[Test]
public async Task Should_SendPurchaseWithOrderTotal_When_OrderIsPlaced()
{
    await _checkoutPage.OpenAsync();
    await _consentBanner.AcceptAllAsync();

    var purchase = await _tracker.NextEventAsync("purchase", _checkoutPage.PlaceOrderAsync);

    Assert.That(purchase.Params, Is.SupersetOf(new Dictionary<string, string>
    {
        ["en"] = "purchase",
        ["cu"] = "EUR",
        ["ep.transaction_id"] = "ORD-1001",
    }), $"purchase hit: {string.Join("&", purchase.Params)}");
}

[Test]
public async Task Should_PushPurchaseToDataLayer_When_OrderIsPlaced()
{
    await _checkoutPage.OpenAsync();
    await _consentBanner.AcceptAllAsync();

    await _checkoutPage.PlaceOrderAsync();

    Assert.That(await _dataLayer.EventsNamedAsync<PurchasePush>("purchase"),
        Is.EqualTo(new[] { new PurchasePush("purchase", new Ecommerce("ORD-1001", 68.00m, "EUR")) }), "dataLayer purchase pushes");
}
```

- The beacon test pins the wire keys **you recorded** from your own tag — `cu` and `ep.transaction_id` stand in for
  them here. The `dataLayer` test pins the payload against the tracking plan.
- `Is.EqualTo(new[] { ... })` also catches a **double push**: two purchases for one order fail the test.
- A real GA4 `ecommerce` object carries an `items` array; a record holding a list does not compare by value, so
  assert the items in their own test against a builder (`test-data-builder`).

## 5. Global Privacy Control

```csharp
public class GlobalPrivacyControlTests : BaseTest
{
    private Tracker _tracker = null!;
    private DataLayer _dataLayer = null!;
    private ShopPage _shopPage = null!;
    private ConsentBanner _consentBanner = null!;

    [SetUp]
    public async Task CreateHelpers()
    {
        _tracker = new Tracker(Page);
        await _tracker.CaptureAsync();
        await new PrivacySignals(Page).SendGlobalPrivacyControlAsync();
        _dataLayer = new DataLayer(Page);
        _shopPage = new ShopPage(Page);
        _consentBanner = new ConsentBanner(Page);
    }

    [Test]
    public async Task Should_SendNoAdPixel_When_GlobalPrivacyControlIsOn()
    {
        await _shopPage.OpenHomeAsync();
        await _consentBanner.AcceptAllAsync();

        await _shopPage.OpenPricingAsync();

        Assert.That(_tracker.HitsTo(Tracker.MetaPixel), Is.Empty, "Meta Pixel hits with GPC on");
    }

    [Test]
    public async Task Should_KeepAdConsentDenied_When_GlobalPrivacyControlIsOn()
    {
        await _shopPage.OpenHomeAsync();

        await _consentBanner.AcceptAllAsync();

        Assert.That(await _dataLayer.ConsentStateAsync("update"), Does.ContainKey("ad_user_data").WithValue("denied"),
            "ad_user_data after accept with GPC on");
    }
}
```

What GPC must switch off is a legal and product decision (an opt-out of sale or sharing under the applicable law):
take the expected outcome from the privacy requirements, never from the current behaviour.

## Anti-patterns

- `ContinueAsync()` on a collect request — the hit reaches the real property. Fulfil it.
- `AbortAsync()` on a beacon you assert on — some tags retry or fall back, and the test reads the retry.
- Asserting only that `gtag.js` or `fbevents.js` loaded — it proves nothing was sent correctly.
- `Task.Delay` before reading `Hits()` — wait on a page signal, then read.
- Reading the hit list straight after a click that should *not* send anything — load the next page first.
- A consent class that loads a saved storage state with a consent cookie.
