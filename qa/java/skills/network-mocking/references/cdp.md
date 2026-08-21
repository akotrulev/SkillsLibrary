# QA — Raw CDP Network & Performance Hooks (Java)

Drives the raw **Chrome DevTools Protocol** from a Playwright `com.microsoft.playwright` (sync API) + TestNG test on Java 21 via `page.context().newCDPSession(page)`, for the hooks that live **below the `page.route` routing layer**: real bandwidth/latency throttling, HTTP-cache disable, CPU throttling, security-header/`securityDetails` auditing, and `Performance` metrics. Built on the **base-test class** model from `qa/java/skills/network-mocking`: the CDP session and every command/event are wrapped in an intent-revealing `CdpControls` helper exposed through `BaseTest`, never raw `client.send("Domain.method", …)` scattered across `@Test` methods. Every wait is conditional on a Playwright condition or a CDP event; there is **no `page.waitForTimeout`** as a wait anywhere in this skill.

This is the **Java port of the canonical** `qa/typescript/skills/network-mocking` — same patterns (throttle / cache-disable / CPU-throttle / security audit / perf budget), re-expressed in the `com.microsoft.playwright` sync idioms. The binding difference that drives the porting: Java sends commands with **`client.send(String method, com.google.gson.JsonObject params)`** (returning a `JsonObject`) and subscribes to events with **`client.on("Network.responseReceived", (JsonObject json) -> …)`** — params **and** event payloads are Gson `JsonObject`s, not typed records.

> **Chromium-only.** CDP exists only in Chromium-based browsers. On Firefox/WebKit `newCDPSession` throws. That is the price of dropping below the routing layer — guard the suite to the Chromium engine. For anything that must run cross-browser, stay at the `page.route` layer (`playwright-routes`).

## Stack

- Java 21 + Gradle (Kotlin DSL)
- TestNG 7.x + `com.microsoft.playwright:playwright` (sync API, Playwright ≥ 1.49)
- Gson (`com.google.gson`) for CDP params and event payloads; AssertJ for non-locator assertions
- CDP helpers under `src/test/java/<pkg>/support/cdp/`
- Page objects under `src/test/java/<pkg>/pages/`, tests under `src/test/java/<pkg>/tests/` (see the UI sibling)
- These tests run **only against Chromium**, sharded in CI under `qa/cicd/java/skills/ci-pipelines`. No new secrets — CDP needs none.

## When to use

- Emulating a **real** slow connection (Slow/Fast 3G with actual throughput + latency numbers) to test loading/timeout/skeleton states — not the per-request `Thread.sleep` `page.route` can fake
- Forcing every request to **miss the HTTP cache** (`Network.setCacheDisabled`) for deterministic cold-cache behavior
- **CPU-throttling** the main thread (4×/6×) to surface jank, long tasks, and slow renders on low-end devices
- **Auditing security headers** — assert the document carries CSP / HSTS / `X-Frame-Options`, or inspect TLS `securityDetails`
- Capturing **performance metrics** (`Performance.getMetrics` — `JSHeapUsedSize`, `LayoutCount`, `TaskDuration`, …) and asserting a budget

## When NOT to use

- High-level request **mock / abort / fulfill / modify-in-flight**, HAR replay, or approximate offline (`context.setOffline`) → `qa/java/skills/network-mocking` (the layer above; reach for it first)
- Playwright TypeScript / .NET CDP → `qa/{typescript,dotnet}/skills/network-mocking`
- **Cross-browser** throttling/auditing, or capture for a non-Playwright / multi-process stack → `qa/java/skills/network-mocking`
- Writing the page objects / tests themselves → `qa/java/skills/ui-test-author/playwright`

## Inputs needed

Ask at most 3 questions; infer the rest from the test project and existing tests.

1. **Which hook** — network throttle (which preset?), cache disable, CPU throttle (which rate?), security-header audit, or perf metrics?
2. **Confirm Chromium-only is acceptable** — is this suite allowed to run only against the Chromium engine?
3. **The signal** — for throttle/CPU: which loading/jank state to assert? For audit: which headers, on which URL?

## Decision matrix — CDP domains used in tests

| Goal | CDP call | Notes |
|---|---|---|
| Enable network events | `client.send("Network.enable")` | Required **before** `responseReceived`/`emulateNetworkConditions` |
| Real bandwidth + latency | `client.send("Network.emulateNetworkConditions", params)` | `params` is a Gson `JsonObject`; throughput in **bytes/s**, latency in **ms** |
| Disable the HTTP cache | `client.send("Network.setCacheDisabled", params)` with `cacheDisabled = true` | Every request misses cache |
| Throttle the CPU | `client.send("Emulation.setCPUThrottlingRate", params)` with `rate` | `rate` = slowdown multiplier; `1` = none |
| Capture response metadata | `client.on("Network.responseReceived", json -> …)` | `json` is a `JsonObject`; read `response.url`/`status`/`headers`/`securityDetails` |
| Perf metrics | `client.send("Performance.enable")` then `client.send("Performance.getMetrics")` | Returns a `JsonObject` `{ metrics: [{ name, value }] }` |
| Close the session | `client.detach()` | Do it in `@AfterMethod`; a detached session emits no events |

Realistic throttling numbers (Chrome DevTools' own Slow/Fast 3G profiles — encoded in `NetworkPresets` below):

| Preset | download | upload | latency |
|---|---|---|---|
| Slow 3G | ~50 KB/s (`500 kbit/s × 0.8 ÷ 8`) | ~50 KB/s | 2000 ms (`400 × 5`) |
| Fast 3G | ~180 KB/s (`1.6 Mbit/s × 0.9 ÷ 8`) | ~84 KB/s (`750 kbit/s × 0.9 ÷ 8`) | ~562 ms (`150 × 3.75`) |

## Patterns

### The CDP helper — `support/cdp/CdpControls.java`

One helper owns the session: it opens it, enables `Network`, captures every `responseReceived` for later auditing, exposes intent-named methods, and detaches in teardown. Tests call `cdp.throttle(NetworkPresets.slow3G())`, never `client.send("Network.emulateNetworkConditions", …)`.

```java
package com.example.support.cdp;

import com.google.gson.JsonObject;
import com.microsoft.playwright.CDPSession;
import com.microsoft.playwright.Page;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.function.Predicate;

public final class CdpControls {
    private final CDPSession client;
    private final List<CapturedResponse> captured = new ArrayList<>();

    private CdpControls(CDPSession client) {
        this.client = client;
        // Registered immediately after Network.enable, before any navigation — so no response is missed.
        client.on("Network.responseReceived", json -> {
            JsonObject response = json.getAsJsonObject("response");
            JsonObject securityDetails = response.has("securityDetails")
                    ? response.getAsJsonObject("securityDetails") : null;
            captured.add(new CapturedResponse(
                    response.get("url").getAsString(),
                    response.get("status").getAsInt(),
                    response.getAsJsonObject("headers"),
                    securityDetails));
        });
    }

    public static CdpControls attach(Page page) {
        CDPSession client = page.context().newCDPSession(page); // Chromium-only — throws on FF/WebKit
        client.send("Network.enable");
        return new CdpControls(client);
    }

    /** Apply a real bandwidth + latency profile (e.g. NetworkPresets.slow3G()). */
    public void throttle(JsonObject preset) {
        client.send("Network.emulateNetworkConditions", preset);
    }

    /** Force every request to miss the HTTP cache — cold-cache path becomes deterministic. */
    public void disableCache() {
        JsonObject params = new JsonObject();
        params.addProperty("cacheDisabled", true);
        client.send("Network.setCacheDisabled", params);
    }

    /** Slow the main thread by {@code rate}× (1 = none, 4/6 = low-end device). */
    public void cpuThrottle(int rate) {
        JsonObject params = new JsonObject();
        params.addProperty("rate", rate);
        client.send("Emulation.setCPUThrottlingRate", params);
    }

    /** Performance.getMetrics as a name→value map for budget assertions. */
    public java.util.Map<String, Double> metrics() {
        client.send("Performance.enable");
        JsonObject result = client.send("Performance.getMetrics");
        java.util.Map<String, Double> map = new java.util.HashMap<>();
        result.getAsJsonArray("metrics").forEach(m -> {
            JsonObject metric = m.getAsJsonObject();
            map.put(metric.get("name").getAsString(), metric.get("value").getAsDouble());
        });
        return map;
    }

    /** The captured response whose URL matches — for the security-header audit. */
    public Optional<CapturedResponse> responseFor(Predicate<String> urlMatches) {
        return captured.stream().filter(r -> urlMatches.test(r.url())).findFirst();
    }

    public void detach() {
        client.detach();
    }
}
```

```java
package com.example.support.cdp;

import com.google.gson.JsonObject;

/** A response captured off the wire via Network.responseReceived. */
public record CapturedResponse(String url, int status, JsonObject headers, JsonObject securityDetails) {}
```

The throttling presets (throughput in **bytes/second**, latency in **ms** — DevTools' own Slow/Fast 3G formulas):

```java
package com.example.support.cdp;

import com.google.gson.JsonObject;

public final class NetworkPresets {
    private NetworkPresets() {}

    public static JsonObject slow3G() {
        return profile(false, 500 * 1000 * 0.8 / 8, 500 * 1000 * 0.8 / 8, 400 * 5);
    }

    public static JsonObject fast3G() {
        return profile(false, 1.6 * 1000 * 1000 * 0.9 / 8, 750 * 1000 * 0.9 / 8, 150 * 3.75);
    }

    private static JsonObject profile(boolean offline, double down, double up, double latency) {
        JsonObject p = new JsonObject();
        p.addProperty("offline", offline);
        p.addProperty("downloadThroughput", down);
        p.addProperty("uploadThroughput", up);
        p.addProperty("latency", latency);
        return p;
    }
}
```

Expose it on `BaseTest` so tests get `cdp` ready, and gate the engine to Chromium:

```java
public abstract class CdpBaseTest extends BaseTest {
    protected CdpControls cdp;

    @BeforeMethod(alwaysRun = true, dependsOnMethods = "createContext")
    public void initCdp() {
        // CDP is Chromium-only — declare the dependency loudly.
        skipUnlessChromium();
        cdp = CdpControls.attach(page);
    }

    @AfterMethod(alwaysRun = true)
    public void detachCdp() {
        if (cdp != null) cdp.detach();
    }

    private void skipUnlessChromium() {
        if (!"chromium".equals(browserName)) {
            throw new SkipException("CDP is Chromium-only");
        }
    }
}
```

### Real network throttling — Slow 3G

```java
public class ThrottleTest extends CdpBaseTest {

    @Test
    public void shouldKeepTheSkeletonVisibleWhenOrdersLoadOverSlow3G() {
        cdp.throttle(NetworkPresets.slow3G()); // apply BEFORE navigating

        page.navigate("/orders");

        // The skeleton is the genuine loading signal — assert on it, never on a fixed sleep.
        assertThat(page.getByTestId("orders-skeleton")).isVisible();
        assertThat(page.getByTestId("orders-list"))
                .isVisible(new LocatorAssertions.IsVisibleOptions().setTimeout(30_000));
    }
}
```

`assertThat(...).isVisible(...)` retries until the slow load completes, so the longer timeout is a deadline, **not** a `page.waitForTimeout`.

### Disable the HTTP cache

```java
@Test
public void shouldRefetchTheAvatarWhenTheCacheIsDisabled() {
    cdp.disableCache();

    page.navigate("/profile");
    assertThat(page.getByTestId("avatar")).isVisible();
    page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Reload profile")).click();

    Optional<CapturedResponse> avatar = cdp.responseFor(u -> u.contains("/avatars/"));
    org.assertj.core.api.Assertions.assertThat(avatar)
            .as("avatar should be re-fetched, not served from cache")
            .hasValueSatisfying(r -> org.assertj.core.api.Assertions.assertThat(r.status()).isEqualTo(200));
}
```

### CPU throttling — surface jank

```java
@Test
public void shouldRenderTheDashboardWithinBudgetWhenTheCpuIsThrottled4x() {
    cdp.cpuThrottle(4); // 4× slowdown ≈ a mid-tier mobile device

    page.navigate("/dashboard");

    assertThat(page.getByTestId("dashboard-ready"))
            .isVisible(new LocatorAssertions.IsVisibleOptions().setTimeout(15_000));
}
```

### Security-header audit from captured `Network.responseReceived`

Assert the document response carries the expected security headers. CDP header keys are **lowercased** by the protocol, so normalize the lookup. This is **one logical assertion** ("the response is securely configured") expressed as an AssertJ soft-assertion block so a run reports *every* missing header at once.

```java
// support/cdp/SecurityHeaders.java
package com.example.support.cdp;

import com.google.gson.JsonObject;
import org.assertj.core.api.SoftAssertions;

import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

public final class SecurityHeaders {
    private static final List<String> REQUIRED =
            List.of("content-security-policy", "strict-transport-security", "x-frame-options");

    private SecurityHeaders() {}

    public static void assertPresent(Optional<CapturedResponse> response) {
        org.assertj.core.api.Assertions.assertThat(response)
                .as("no response was captured for that URL").isPresent();

        JsonObject headers = response.get().headers();
        Set<String> present = headers.keySet().stream()
                .map(k -> k.toLowerCase(Locale.ROOT)).collect(Collectors.toSet());

        SoftAssertions soft = new SoftAssertions();
        for (String name : REQUIRED) {
            soft.assertThat(present).as("%s header is missing", name).contains(name);
        }
        soft.assertAll();
    }
}
```

```java
@Test
public void shouldSendCspHstsAndXFrameOptionsWhenTheAppShellLoads() {
    page.navigate("/");
    assertThat(page.getByRole(AriaRole.NAVIGATION)).isVisible(); // shell loaded → its response was captured

    SecurityHeaders.assertPresent(cdp.responseFor(u -> u.equals(page.url())));
}

@Test
public void shouldNegotiateTls13ForTheDocumentWhenLoadedOverHttps() {
    page.navigate("/");
    assertThat(page.getByRole(AriaRole.NAVIGATION)).isVisible();

    Optional<CapturedResponse> doc = cdp.responseFor(u -> u.startsWith("https://"));
    String protocol = doc.map(r -> r.securityDetails().get("protocol").getAsString()).orElse(null);
    org.assertj.core.api.Assertions.assertThat(protocol).isEqualTo("TLS 1.3"); // protocol, issuer, validFrom/To, sanList
}
```

### Performance budget from `Performance.getMetrics`

```java
@Test
public void shouldStayUnderTheLayoutAndHeapBudgetWhenTheDashboardRenders() {
    page.navigate("/dashboard");
    assertThat(page.getByTestId("dashboard-ready")).isVisible(); // a real "done" signal before sampling

    java.util.Map<String, Double> metrics = cdp.metrics();

    // One behavior — "the dashboard renders within budget" — verified by related metrics.
    SoftAssertions soft = new SoftAssertions();
    soft.assertThat(metrics.get("LayoutCount")).as("too many layouts").isLessThan(60);
    soft.assertThat(metrics.get("JSHeapUsedSize")).as("JS heap too large").isLessThan(50.0 * 1024 * 1024);
    soft.assertAll();
}
```

Sample metrics **after** a user-visible "ready" signal, never after a sleep.

## Rules

### Session lifecycle
- Open with `page.context().newCDPSession(page)` and **`detach()` in `@AfterMethod`** — a leaked session keeps emitting events and can outlive the page.
- Call `Network.enable` **before** subscribing to `Network.responseReceived` or applying `emulateNetworkConditions`; call `Performance.enable` before `getMetrics`.
- One session per page in the helper; don't sprinkle extra `newCDPSession` calls through `@Test` methods.

### Chromium-only
- `newCDPSession` **throws on Firefox/WebKit.** Gate with `throw new SkipException("CDP is Chromium-only")` when `browserName` isn't `"chromium"` (or run only the Chromium engine). State the limitation in the base test, not just in your head.
- If a test must be cross-browser, it does not belong here — use `page.route` (`playwright-routes`) or an external `proxy`.

### Throttling & emulation
- `emulateNetworkConditions` throughput is **bytes/second**, latency is **milliseconds** — use the `NetworkPresets` factory, don't hand-roll raw numbers per test.
- Apply throttle / cache-disable / CPU-throttle **before** the navigation or action that should feel it.
- `Emulation.setCPUThrottlingRate` `rate` is a **slowdown multiplier** (`1` = none); reset to `1` only if you reuse one session across phases.

### Assertions & waits
- **No `page.waitForTimeout(ms)`.** Every wait is a web-first `assertThat(locator).isVisible(setTimeout(…))` on a real loading/ready signal, or driven by a captured CDP event. A longer timeout under throttling is a deadline, not a sleep. The only `Thread.sleep` that exists in `playwright-routes` (a latency-injection route handler) is **not needed here** — CDP throttling is real, so there is no sanctioned `Thread.sleep` in this skill at all.
- CDP response **header keys are lowercased** — normalize with `toLowerCase(Locale.ROOT)` before lookup.
- A security-header / perf-budget check is **one logical assertion**; group its related checks in an AssertJ `SoftAssertions` so the report lists every failure at once.
- Sample `Performance.getMetrics` (and read captured responses) **after** a user-visible completion signal, never after a fixed sleep.

### Hygiene
- Protocol method/event names are **strings** — a typo (`"Network.emulateNetworkCondition"`) fails at runtime, not compile time. Keep every `send`/`on` inside the typed `CdpControls` wrapper.
- `send` returns a Gson `JsonObject` — read it with `getAsJsonObject`/`get(...).getAsString()`, guard optional fields with `has(...)` (as the `securityDetails` capture does).
- Don't reach for CDP when `page.route` would do — it's the more brittle, Chromium-only layer.

### What NOT to do
- No `client.send("Domain.method", …)` / `client.on(...)` scattered through `@Test` methods — wrap it in the `CdpControls` helper with an intent name.
- No CDP test running on Firefox/WebKit — it throws; gate to Chromium with `SkipException`.
- No `page.waitForTimeout(ms)` / `Thread.sleep` to "wait for the slow load" — assert on the loading/ready element with a `setTimeout` deadline. (Unlike `playwright-routes`, this skill has **no** sanctioned `Thread.sleep`.)
- No `emulateNetworkConditions` before `Network.enable`, no `getMetrics` before `Performance.enable`.
- No raw throughput numbers per test — use `NetworkPresets`.
- No `Content-Security-Policy` cased lookup against CDP headers — they're lowercased.
- No leaked session — `detach()` in `@AfterMethod`.
- No CDP where `page.route` (cross-browser, typed) expresses the test just as well.

## Generation steps

1. Confirm **which hook** (throttle / cache / CPU / security audit / perf), that **Chromium-only is acceptable**, and **the signal** to assert.
2. Add or extend `support/cdp/CdpControls.java` — open the session, `Network.enable`, capture `responseReceived`, expose intent methods (`throttle`, `disableCache`, `cpuThrottle`, `metrics`, `responseFor`), `detach()` in `@AfterMethod`. Expose it on `CdpBaseTest` with the `SkipException` Chromium gate.
3. Apply the hook **before** the navigation/action; assert on a real loading/ready signal with a `setTimeout` deadline — never `page.waitForTimeout`.
4. For audits, normalize header case and use `SecurityHeaders.assertPresent`; for budgets, sample `metrics()` after a ready signal.
5. Run `./gradlew test` (Chromium engine); verify with the trace viewer's Network tab (throttled timings).

## Cross-references

- **`qa/java/skills/network-mocking`** — the **layer above**; reach for it first (cross-browser mock/abort/fulfill/assert, HAR, approximate offline). Drop to CDP only when routing can't express the test.
- **`qa/typescript/skills/network-mocking`** — the canonical skill this ports from; consult it for the conceptual model and the three-way pick.
- **`qa/dotnet/skills/network-mocking`** — the sibling .NET port (`ICDPSession.SendAsync`, `JsonElement`, `session.Event(...).OnEvent +=`).
- **`qa/java/skills/network-mocking`** — out-of-browser MITM capture for cross-browser or non-Playwright stacks.
- **`qa/java/skills/ui-test-author/playwright`** — the base-test / page-object model these CDP helpers layer on; the no-`waitForTimeout` discipline originates there.
- **`qa/cicd/java/skills/ci-pipelines`** — runs these tests (Chromium only) sharded; traces on failure show throttled timings.
