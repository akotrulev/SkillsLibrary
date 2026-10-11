# QA — Chrome DevTools Protocol Hooks (Java / Playwright 1.63 + TestNG)

Drives the raw **Chrome DevTools Protocol** from a Playwright for Java test through
`page.context().newCDPSession(page)`, for the hooks that live **below the routing layer**: real bandwidth and
latency throttling, HTTP-cache disable, CPU throttling and `Performance` metrics. The session and every
command and event are wrapped in one `CdpControls` helper with intent names (`throttle`, `disableCache`,
`cpuThrottle`, `metrics`, `responsesFor`) — never `client.send("Domain.method", …)` in a test. Every sample
extends `com.example.uitests.support.BaseTest`; there is no `Thread.sleep` and no `waitForTimeout` in this file.

Java sends commands with `client.send(String method, JsonObject params)`, which returns a Gson `JsonObject`,
and subscribes with `client.on(String event, Consumer<JsonObject>)` — parameters and payloads are Gson trees,
not typed records.

> **Chromium only.** `newCDPSession` throws on Firefox and WebKit. That is the price of dropping below
> routing. Anything that must run cross-browser stays in `references/playwright-routes.md` — including
> security headers and TLS details, which `response.allHeaders()` and `response.securityDetails()` cover
> there.

## When to use

- A **real** slow connection (Slow or Fast 3G throughput and latency) to test loading, skeleton and timeout
  states — when the page must load *slowly*, not merely *not yet* (a held request covers that,
  `references/playwright-routes.md` §8).
- Every request must **miss the HTTP cache** (`Network.setCacheDisabled`) so the cold-cache path is
  deterministic.
- **CPU throttling** (4×, 6×) to surface jank and long tasks on low-end devices.
- **Performance metrics** (`Performance.getMetrics` — `JSHeapUsedSize`, `LayoutCount`, `TaskDuration`) with a
  budget.

## When NOT to use

- Mock, abort, modify, hold, assert, HAR replay, offline, security headers, TLS → `references/playwright-routes.md`
- A client with no Playwright `Page`, or cross-browser capture → `references/proxy.md`
- TypeScript and .NET CDP → `qa-typescript:network-mocking`, `qa-dotnet:network-mocking`

## Inputs needed

1. **Which hook** — a throttle preset, cache disable, a CPU rate, or metrics.
2. **Chromium-only is acceptable** for this class.
3. **The signal** — the loading or ready state to assert.

## Decision matrix — the CDP calls

| Goal | Call | Notes |
|---|---|---|
| Network events on | `client.send("Network.enable")` | Before `responseReceived` fires or a throttle applies |
| Real bandwidth and latency | `client.send("Network.emulateNetworkConditions", params)` | Throughput in **bytes per second**, latency in **ms** |
| No HTTP cache | `client.send("Network.setCacheDisabled", params)` with `cacheDisabled = true` | Every request goes to the network |
| CPU slowdown | `client.send("Emulation.setCPUThrottlingRate", params)` with `rate` | `1` = none, `4` / `6` = low-end device |
| Response metadata | `client.on("Network.responseReceived", json -> …)` | `response.url`, `.status`, `.fromDiskCache` |
| Metrics | `Performance.enable`, then `Performance.getMetrics` | `{ metrics: [{ name, value }] }` |

DevTools' own profiles, encoded in `NetworkPresets` below:

| Preset | Download | Upload | Latency |
|---|---|---|---|
| Slow 3G | ~50 KB/s (500 kbit/s × 0.8 ÷ 8) | ~50 KB/s | 2000 ms (400 × 5) |
| Fast 3G | ~180 KB/s (1.6 Mbit/s × 0.9 ÷ 8) | ~84 KB/s (750 kbit/s × 0.9 ÷ 8) | ~562 ms (150 × 3.75) |

## 1. The helper — `support/CdpControls.java`

```java
package com.example.uitests.support;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.microsoft.playwright.CDPSession;
import com.microsoft.playwright.Page;
import org.testng.SkipException;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;
import java.util.stream.Collectors;

public final class CdpControls {
    private final CDPSession client;
    private final List<CapturedResponse> captured = new ArrayList<>();

    private CdpControls(CDPSession client) {
        this.client = client;
        client.on("Network.responseReceived", event -> captured.add(CapturedResponse.from(event.getAsJsonObject("response"))));
    }

    public static CdpControls attach(Page page) {
        String browserName = page.context().browser().browserType().name();
        if (!"chromium".equals(browserName)) {
            throw new SkipException("CDP is Chromium-only; this run uses " + browserName);
        }
        CDPSession client = page.context().newCDPSession(page);
        client.send("Network.enable");
        return new CdpControls(client);
    }

    public void throttle(JsonObject preset) {
        client.send("Network.emulateNetworkConditions", preset);
    }

    public void disableCache() {
        JsonObject params = new JsonObject();
        params.addProperty("cacheDisabled", true);
        client.send("Network.setCacheDisabled", params);
    }

    public void cpuThrottle(int rate) {
        JsonObject params = new JsonObject();
        params.addProperty("rate", rate);
        client.send("Emulation.setCPUThrottlingRate", params);
    }

    public Map<String, Double> metrics() {
        client.send("Performance.enable");
        JsonObject result = client.send("Performance.getMetrics");
        return result.getAsJsonArray("metrics").asList().stream()
                .map(JsonElement::getAsJsonObject)
                .collect(Collectors.toMap(
                        metric -> metric.get("name").getAsString(),
                        metric -> metric.get("value").getAsDouble()));
    }

    public List<CapturedResponse> responsesFor(Predicate<String> url) {
        return captured.stream().filter(response -> url.test(response.url())).toList();
    }

    public record CapturedResponse(String url, int status, boolean fromDiskCache) {
        static CapturedResponse from(JsonObject response) {
            return new CapturedResponse(
                    response.get("url").getAsString(),
                    response.get("status").getAsInt(),
                    response.has("fromDiskCache") && response.get("fromDiskCache").getAsBoolean());
        }
    }
}
```

- **`browserName` is read from the page** — `page.context().browser().browserType().name()` — so the gate
  needs no field from `BaseTest`. `BaseTest` launches Chromium today; the gate keeps a CDP class honest
  if a project later runs the suite on another engine: TestNG reports it as skipped, with the reason.
- The listener is registered right after `Network.enable`, before the test navigates, so no response is
  missed.
- **Events arrive only while Playwright is dispatching** — during a Playwright call on the class's thread.
  A list fed by `client.on` is read after a Playwright wait (`page.waitForCondition`, a web-first assertion),
  never in a busy loop.
- **No detach hook.** The session belongs to the test's page; `BaseTest` closes the context after every test,
  which ends the session with it.

The presets, throughput in **bytes per second** and latency in **ms**:

```java
package com.example.uitests.support;

import com.google.gson.JsonObject;

public final class NetworkPresets {
    private NetworkPresets() {
    }

    public static JsonObject slow3G() {
        return profile(500 * 1000 * 0.8 / 8, 500 * 1000 * 0.8 / 8, 400 * 5);
    }

    public static JsonObject fast3G() {
        return profile(1.6 * 1000 * 1000 * 0.9 / 8, 750 * 1000 * 0.9 / 8, 150 * 3.75);
    }

    private static JsonObject profile(double download, double upload, double latency) {
        JsonObject preset = new JsonObject();
        preset.addProperty("offline", false);
        preset.addProperty("downloadThroughput", download);
        preset.addProperty("uploadThroughput", upload);
        preset.addProperty("latency", latency);
        return preset;
    }
}
```

Offline is `page.context().setOffline(true)` at the routing layer, so there is no offline preset here.

## 2. Real throttling — Slow 3G

```java
package com.example.uitests.tests;

import com.example.uitests.pages.DashboardPage;
import com.example.uitests.pages.OrdersPage;
import com.example.uitests.pages.ProfilePage;
import com.example.uitests.support.BaseTest;
import com.example.uitests.support.CdpControls;
import com.example.uitests.support.NetworkPresets;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.assertions.LocatorAssertions;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class NetworkConditionsTest extends BaseTest {
    private CdpControls cdp;
    private OrdersPage ordersPage;
    private ProfilePage profilePage;
    private DashboardPage dashboardPage;

    @BeforeMethod(alwaysRun = true)
    public void attachCdp() {
        cdp = CdpControls.attach(page);
        ordersPage = new OrdersPage(page);
        profilePage = new ProfilePage(page);
        dashboardPage = new DashboardPage(page);
    }

    @Test
    public void Should_ShowSkeletonUntilOrdersArrive_When_NetworkIsSlow3G() {
        cdp.throttle(NetworkPresets.slow3G());

        ordersPage.navigate();

        assertThat(ordersPage.skeleton()).isVisible();
        assertThat(ordersPage.list()).isVisible(new LocatorAssertions.IsVisibleOptions().setTimeout(30_000));
    }
}
```

Apply the profile **before** the navigation that should feel it. `ordersPage.navigate()` only navigates, so
the loading state is still observable. The longer timeout is a deadline for a web-first assertion, not a
sleep. The two assertions are one behaviour: the skeleton holds until the slow list arrives.

§3–§5 are further methods of `NetworkConditionsTest`. They add `java.util.Map`,
`org.assertj.core.api.SoftAssertions` and AssertJ's static `assertThat` to its imports; Java picks between
AssertJ's and Playwright's `assertThat` by argument type.

## 3. Cache disabled — the reload goes to the network

```java
@Test
public void Should_RefetchAvatarFromNetwork_When_CacheIsDisabled() {
    cdp.disableCache();
    profilePage.open();

    profilePage.reloadProfile();

    page.waitForCondition(() -> cdp.responsesFor(url -> url.contains("/avatars/")).size() == 2,
            new Page.WaitForConditionOptions().setTimeout(10_000));
    assertThat(cdp.responsesFor(url -> url.contains("/avatars/")).getLast().fromDiskCache())
            .as("reloaded avatar served from the disk cache").isFalse();
}
```

- `page.waitForCondition` blocks until the reload's avatar response has arrived, while Playwright keeps
  dispatching the CDP events that fill the list ([1.32], `ui-test-author/playwright/references/assertions.md` §5).
- The assertion reads the **last** avatar response — the one the reload produced. `findFirst()` would read
  the response from before the reload, and the test could never fail.
- `getLast()` is `List.getLast()` (Java 21, sequenced collections). The assertion is AssertJ's.

## 4. CPU throttling

```java
@Test
public void Should_RenderDashboardWithinDeadline_When_CpuIsThrottled4x() {
    cdp.cpuThrottle(4);

    dashboardPage.navigate();

    assertThat(dashboardPage.ready()).isVisible(new LocatorAssertions.IsVisibleOptions().setTimeout(15_000));
}
```

Each test gets a fresh session on a fresh page, so the rate never needs resetting.

## 5. Performance budget

```java
@Test
public void Should_StayWithinLayoutAndHeapBudget_When_DashboardRenders() {
    dashboardPage.open();

    Map<String, Double> metrics = cdp.metrics();

    SoftAssertions budget = new SoftAssertions();
    budget.assertThat(metrics.get("LayoutCount")).as("layout count").isLessThan(60.0);
    budget.assertThat(metrics.get("JSHeapUsedSize")).as("JS heap bytes").isLessThan(50.0 * 1024 * 1024);
    budget.assertAll();
}
```

`dashboardPage.open()` returns once the dashboard's ready marker is visible; sampling before that passes only
because the page had not finished rendering. The two soft assertions are one behaviour, "renders within
budget", and both report. A missing metric is `null`, which AssertJ reports as a failure.

## Rules

### Session lifecycle

- `CdpControls.attach(page)` in the class's own `@BeforeMethod(alwaysRun = true)` — one session per test's
  page. It ends with the context `BaseTest` closes.
- `Network.enable` before subscribing to `Network.responseReceived` or throttling; `Performance.enable`
  before `getMetrics`.

### Chromium only

- `attach` reads the engine from `page.context().browser().browserType().name()` and throws
  `SkipException` for anything but `chromium`.
- A test that must run cross-browser does not belong here — `references/playwright-routes.md` or
  `references/proxy.md`.

### Throttling and emulation

- Throughput is **bytes per second**, latency **milliseconds** — use `NetworkPresets`, not raw numbers per
  test.
- Apply throttle, cache disable and CPU rate **before** the navigation or action that should feel them.

### Assertions and waits

- Every wait is a web-first assertion with a deadline on a real loading or ready signal, or
  `page.waitForCondition` on a CDP-fed list.
- A check after a reload reads the **last** matching response.
- Sample metrics after a user-visible ready signal.

### Hygiene

- Protocol method and event names are strings — a typo fails at runtime. Keep every `send` and `on` inside
  `CdpControls`.
- Read a payload with `getAsJsonObject` / `get(...).getAsString()`, and guard optional fields with `has(...)`.

## What NOT to do

- No `client.send(...)` or `client.on(...)` in a `@Test` method.
- No CDP class without the Chromium gate.
- No `Thread.sleep`, `waitForTimeout` or busy loop to "wait for the slow load".
- No `emulateNetworkConditions` before `Network.enable`; no `getMetrics` before `Performance.enable`.
- No raw throughput numbers per test.
- No `findFirst()` on captured responses after a reload.
- No security-header or TLS audit here — routing covers both, cross-browser.
- No CDP where `page.route` expresses the test just as well.

## Generation steps

1. Confirm the hook, that Chromium-only is acceptable, and the signal.
2. Extend `CdpControls` with an intent method; build it and the page objects in the class's `@BeforeMethod`.
3. Apply the hook before the navigation; assert on a real loading or ready signal with a deadline.
4. For captured responses, wait with `page.waitForCondition`, then read the last match.
5. Read a failure's trace (`qa/java/skills/evidence-capture`): the Network tab shows the throttled timings.

## Cross-references

- `references/playwright-routes.md` — the layer above; reach for it first.
- `references/proxy.md` — capture for a client with no Playwright `Page`.
- `qa/java/skills/ui-test-author/playwright` — `BaseTest`, page objects, `references/assertions.md` §5.
- `qa/java/skills/evidence-capture` — traces and reading a failure.
- `qa/cicd/java/skills/ci-pipelines` — the UI job (Chromium).
- `qa-typescript:network-mocking`, `qa-dotnet:network-mocking` — the sibling lanes.
