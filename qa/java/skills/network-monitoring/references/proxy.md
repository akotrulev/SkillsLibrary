# QA — Out-of-Browser MITM Proxy (Java, `BrowserUp Proxy` + Selenium)

Stands up an **out-of-process MITM HTTP(S) proxy** with [`BrowserUp Proxy`](https://github.com/browserup/browserup-proxy) (`com.browserup:browserup-proxy-core`, the maintained BrowserMob successor) on Java 21 + TestNG to capture, assert, and fault-inject traffic when **there is no Playwright in the picture** — the client under test is a Selenium WebDriver, an Appium driver, or a multi-process system. The proxy sits between the client and the network; you wire it into the WebDriver via `ClientUtil.createSeleniumProxy(...)`, then **record** to a HAR, **assert** a specific request fired, and **inject faults** (rewrite a response, delay, short-circuit). Cross-browser and cross-client by construction — the cost is **TLS interception**: the client must trust the proxy's CA certificate.

This is the **Java port of the canonical** `qa/typescript/skills/network-monitoring`. ⚠ Unlike the `playwright-routes`/`cdp` siblings (which all drive the *same* Playwright API), the three proxy stacks use **genuinely different libraries** — there is no line-by-line port. What carries over is the **structure and the five moves**: start proxy → point client at it → record/assert → fault-inject → trust CA. The binding difference here: `BrowserUp` is **HAR-native** — recording is `newHar`/`getHar` and assertions read `har.getLog().getEntries()`; capture/fault hooks are `addRequestFilter` / `addResponseFilter` lambdas; and Selenium wiring goes through `ClientUtil.createSeleniumProxy(proxy)`.

Built on the same wrapper discipline as `qa/java/skills/network-monitoring` and `cdp/java`: the proxy and every record/filter rule are wrapped in one intent-revealing `ProxyControls` helper exposed through `BaseTest`, never raw `proxy.addResponseFilter(...)` scattered across `@Test` methods. Every wait is conditional on `waitForQuiescence` or a real client signal; there is **no `Thread.sleep`-as-a-wait** anywhere in this skill.

> **Why this skill exists.** `playwright-routes` and `cdp` both require a Playwright `Page`. The moment your stack is Selenium / Appium / multiple processes, neither applies. An external MITM proxy works for **any** client that honors proxy settings, across **any** browser. You pay with CA-trust setup and an extra process to start/stop.

## Stack

- Java 21 + Gradle (Kotlin DSL)
- [`com.browserup:browserup-proxy-core`](https://central.sonatype.com/artifact/com.browserup/browserup-proxy-core) — `BrowserUpProxyServer`, `newHar`/`getHar`/`enableHarCaptureTypes`, `addRequestFilter`/`addResponseFilter`, `setLatency`, `waitForQuiescence`, `ClientUtil.createSeleniumProxy`
- TestNG 7.x + `org.seleniumhq.selenium:selenium-java` (or the Appium Java client) as the **client under test**
- AssertJ for non-locator assertions; `Har` model from the BrowserUp dependency
- Proxy helpers under `src/test/java/<pkg>/support/proxy/`, recorded HARs under `build/artifacts/har/`
- These tests run in CI under `qa/cicd/java/skills/ci-pipelines`: the job starts/stops the proxy and the client must **trust the per-run CA** (no long-lived secret — generated/trusted fresh each run)

## When to use

- Capturing or asserting the HTTP(S) calls a **Selenium / Appium** test makes, where `page.route` is unavailable
- **Asserting** a request fired with the expected method / URL / payload / headers from a non-Playwright client
- **Fault-injecting** from outside the browser: rewrite a `200` to a `500`, add latency, or short-circuit a request
- **Recording a HAR** of a multi-process flow for debugging, perf inspection, or determinism
- Driving the **same** capture/assert/fault logic across Chrome, Firefox, Edge, or a mobile app — one proxy, every client

## When NOT to use

- In-Playwright request routing → `qa/java/skills/network-monitoring` (reach for it first **if** you have a `Page`)
- Raw CDP hooks (real throttling, cache disable, `securityDetails`, `Performance` metrics) → `qa/java/skills/network-monitoring`
- The TypeScript / .NET proxy stacks → `qa/{typescript,dotnet}/skills/network-monitoring`
- Writing the page objects / tests themselves → the relevant `qa/java/skills/ui-test-author/*` sibling

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Which client** — Selenium WebDriver (which browser?) or Appium? This decides how you wire the proxy in (`createSeleniumProxy` vs device caps).
2. **Intent** — record/assert a request (HAR), or inject a fault (rewrite a status / latency / short-circuit)? And is the target **HTTPS** (→ CA-trust step) or plain HTTP?
3. **The signal** — which HAR entry (method + URL) or client-visible state proves the flow completed, so the assertion can wait on `waitForQuiescence` / a locator instead of sleeping?

## Decision matrix — `BrowserUp Proxy` moves used in tests

| Goal | `BrowserUp` call | Notes |
|---|---|---|
| Start the proxy | `BrowserUpProxy proxy = new BrowserUpProxyServer(); proxy.start()` | `proxy.getPort()` after start = the address to point the client at |
| Trust the CA (HTTPS) | install BrowserUp's `ca-certificate-rsa.cer` in the client trust store; in Selenium `options.setAcceptInsecureCerts(true)` | Required to **decrypt** HTTPS |
| Wire into Selenium | `Proxy seleniumProxy = ClientUtil.createSeleniumProxy(proxy); options.setProxy(seleniumProxy)` | The bridge from proxy → WebDriver |
| Enable rich capture | `proxy.enableHarCaptureTypes(REQUEST_CONTENT, RESPONSE_CONTENT, REQUEST_HEADERS, RESPONSE_HEADERS)` | Bodies/headers only captured when enabled |
| Start recording | `proxy.newHar("page-label")` | Begins a fresh HAR page |
| Read the recording | `Har har = proxy.getHar(); har.getLog().getEntries()` | Each entry: `getRequest().getMethod()`/`getUrl()`/`getPostData()`, `getResponse().getStatus()` |
| Capture / short-circuit a request | `proxy.addRequestFilter((request, contents, info) -> { … return null; })` | Return a non-null `HttpResponse` to short-circuit (fault) |
| Rewrite a response | `proxy.addResponseFilter((response, contents, info) -> { … })` | Mutate status/body via `contents.setTextContents(...)` |
| Add latency | `proxy.setLatency(2, TimeUnit.SECONDS)` | Real delay on every request — not a test sleep |
| Wait for the network to settle | `proxy.waitForQuiescence(quietMs, timeoutMs, MILLISECONDS)` | The sanctioned wait — never a fixed sleep |
| Stop the proxy | `proxy.stop()` | In `@AfterMethod`; releases the port |

## Patterns

### The proxy helper — `support/proxy/ProxyControls.java`

One helper owns the proxy lifecycle, the HAR, and the intent-named record/filter rules. Tests call `proxy.recordPage("checkout")`, `proxy.failPostWith(url, 500)`, `proxy.awaitRequest(...)` — never raw `BrowserUp` filter wiring.

```java
package com.example.support.proxy;

import com.browserup.bup.BrowserUpProxy;
import com.browserup.bup.BrowserUpProxyServer;
import com.browserup.bup.filters.RequestFilter;
import com.browserup.bup.proxy.CaptureType;
import com.browserup.harreader.model.Har;
import com.browserup.harreader.model.HarEntry;
import io.netty.handler.codec.http.DefaultFullHttpResponse;
import io.netty.handler.codec.http.HttpResponse;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.netty.handler.codec.http.HttpVersion;

import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.function.Predicate;

public final class ProxyControls {
    private final BrowserUpProxy proxy;

    private ProxyControls(BrowserUpProxy proxy) {
        this.proxy = proxy;
    }

    /** Start an HTTPS-intercepting proxy with rich capture enabled. */
    public static ProxyControls start() {
        BrowserUpProxy proxy = new BrowserUpProxyServer();
        proxy.setTrustAllServers(true); // trust upstream servers; the BROWSER still trusts the proxy CA
        proxy.start();
        proxy.enableHarCaptureTypes(
                CaptureType.REQUEST_CONTENT, CaptureType.RESPONSE_CONTENT,
                CaptureType.REQUEST_HEADERS, CaptureType.RESPONSE_HEADERS);
        return new ProxyControls(proxy);
    }

    /** The Selenium proxy object to attach to ChromeOptions. */
    public com.browserup.bup.client.ClientUtil clientUtil() {
        return null; // placeholder so callers use the static below
    }

    public BrowserUpProxy raw() {
        return proxy;
    }

    /** Begin a fresh HAR page — call before the action that should be recorded. */
    public void recordPage(String label) {
        proxy.newHar(label);
    }

    /** Force the matching POST to fail so the client's error path runs (fault injection). */
    public void failPostWith(String urlSubstring, int status) {
        proxy.addRequestFilter((request, contents, info) -> {
            if (request.method().name().equals("POST") && info.getUrl().contains(urlSubstring)) {
                // Returning a non-null response short-circuits before the network.
                return new DefaultFullHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.valueOf(status));
            }
            return null;
        });
    }

    /** Block on the network settling, then return the matching HAR entry — never a fixed sleep. */
    public Optional<HarEntry> awaitRequest(Predicate<HarEntry> match, long timeoutMs) {
        proxy.waitForQuiescence(500, timeoutMs, TimeUnit.MILLISECONDS); // quiet period, deadline
        return entries().stream().filter(match).findFirst();
    }

    public List<HarEntry> entries() {
        Har har = proxy.getHar();
        return har == null ? List.of() : har.getLog().getEntries();
    }

    public Har har() {
        return proxy.getHar();
    }

    public void stop() {
        proxy.stop();
    }
}
```

> The `ClientUtil.createSeleniumProxy(...)` call lives in the Selenium client helper below (it returns a `org.openqa.selenium.Proxy`), keeping the WebDriver dependency out of `ProxyControls`.

Expose it on `BaseTest` so tests get `proxy` ready:

```java
public abstract class ProxyBaseTest {
    protected ProxyControls proxy;

    @BeforeMethod(alwaysRun = true)
    public void startProxy() {
        proxy = ProxyControls.start();
    }

    @AfterMethod(alwaysRun = true)
    public void stopProxy() {
        if (proxy != null) proxy.stop();
    }
}
```

### Point the client at the proxy — Selenium WebDriver

The whole reason this node exists: there is no `Page`, so you wire the proxy into the **client's** settings via `ClientUtil.createSeleniumProxy` and **trust the CA** so HTTPS decrypts.

```java
package com.example.support.proxy;

import com.browserup.bup.client.ClientUtil;
import org.openqa.selenium.Proxy;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

public final class SeleniumClient {
    private SeleniumClient() {}

    public static WebDriver chromeThroughProxy(ProxyControls controls) {
        Proxy seleniumProxy = ClientUtil.createSeleniumProxy(controls.raw());
        ChromeOptions options = new ChromeOptions();
        options.setProxy(seleniumProxy);
        // Trust the proxy CA so intercepted HTTPS doesn't error. Prefer importing BrowserUp's
        // ca-certificate-rsa.cer into the OS/NSS store in CI; setAcceptInsecureCerts is the test-only shortcut.
        options.setAcceptInsecureCerts(true);
        return new ChromeDriver(options);
    }
}
```

For **Appium**, attach the same `ClientUtil.createSeleniumProxy(...)` (or device Wi-Fi proxy capabilities) to the Appium options and install BrowserUp's CA into the device trust store — the identical record/assert/fault helpers then apply unchanged.

### Assert a request fired — method + payload + headers

```java
package com.example.tests;

import com.example.support.proxy.ProxyBaseTest;
import com.example.support.proxy.SeleniumClient;
import com.browserup.harreader.model.HarEntry;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.testng.annotations.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

public class CheckoutProxyTest extends ProxyBaseTest {

    @Test
    public void shouldPostTheCartTotalWhenTheUserPlacesTheOrder() {
        proxy.recordPage("checkout"); // start recording BEFORE driving the client

        WebDriver driver = SeleniumClient.chromeThroughProxy(proxy);
        try {
            driver.get("https://shop.example.com/cart");
            driver.findElement(By.cssSelector("[data-test='place-order']")).click();

            // waitForQuiescence is the real wait; the entry is the assertion.
            Optional<HarEntry> checkout = proxy.awaitRequest(
                    e -> "POST".equals(e.getRequest().getMethod()) && e.getRequest().getUrl().contains("/api/checkout"),
                    10_000);

            assertThat(checkout).as("checkout POST should fire").isPresent();
            String body = checkout.get().getRequest().getPostData().getText();
            assertThat(body).contains("\"totalMinor\":15000").contains("\"currency\":\"EUR\"");
        } finally {
            driver.quit();
        }
    }
}
```

`awaitRequest` blocks on `waitForQuiescence` (the network settling) and then reads the HAR — it is **not** a fixed sleep.

### Asserting a request was **not** sent

There is no negative wait. Drive the flow to a **client-visible completion signal**, then assert the HAR holds no matching entry.

```java
@Test
public void shouldNotCallTheLegacyPricingEndpointWhenRecalculating() {
    proxy.recordPage("recalculate");
    WebDriver driver = SeleniumClient.chromeThroughProxy(proxy);
    try {
        driver.get("https://shop.example.com/cart");
        driver.findElement(By.cssSelector("[data-test='recalculate']")).click();

        // A real signal the flow finished — never a fixed sleep.
        new org.openqa.selenium.support.ui.WebDriverWait(driver, java.time.Duration.ofSeconds(10))
                .until(d -> !d.findElements(By.cssSelector("[data-test='cart-total']")).isEmpty());

        assertThat(proxy.entries())
                .as("legacy pricing endpoint should be retired")
                .noneMatch(e -> e.getRequest().getUrl().contains("/api/legacy-pricing"));
    } finally {
        driver.quit();
    }
}
```

### Inject a fault — rewrite, latency, short-circuit

```java
@Test
public void shouldShowTheErrorBannerWhenTheOrdersApiReturns500() {
    proxy.failPostWith("/api/orders", 500); // request filter short-circuits with a 500
    proxy.recordPage("orders-error");

    WebDriver driver = SeleniumClient.chromeThroughProxy(proxy);
    try {
        driver.get("https://shop.example.com/orders");
        driver.findElement(By.cssSelector("[data-test='refresh']")).click();

        new org.openqa.selenium.support.ui.WebDriverWait(driver, java.time.Duration.ofSeconds(10))
                .until(d -> !d.findElements(By.cssSelector("[role='alert']")).isEmpty());
    } finally {
        driver.quit();
    }
}
```

To **add latency** instead, call `proxy.raw().setLatency(2, TimeUnit.SECONDS)` (a *real* network delay, not a test sleep); to **rewrite a body** in flight, use `addResponseFilter((response, contents, info) -> contents.setTextContents(...))`.

### Record to a HAR — the native artifact

Recording is built in: `recordPage(...)` then persist `proxy.har()`. **Scrub auth headers** before writing to disk.

```java
// After the flow:
com.browserup.harreader.model.Har har = proxy.har();
har.getLog().getEntries().forEach(e ->
    e.getRequest().getHeaders().removeIf(h ->
        h.getName().equalsIgnoreCase("Authorization") || h.getName().equalsIgnoreCase("Cookie")));
har.writeTo(new java.io.File("build/artifacts/har/checkout.har"));
```

## Rules

### Proxy lifecycle
- One proxy per test owned by `BaseTest`: `new BrowserUpProxyServer()` → `start()` → `enableHarCaptureTypes(...)` → **`stop()` in `@AfterMethod`**. A leaked proxy holds its port and keeps intercepting.
- Call `newHar(label)` / register filters **before** the client action that fires the request.
- The CA is generated/trusted per run; never reuse a static CA across machines as a long-lived secret.

### TLS interception (the caveat that bites everyone)
- **HTTPS interception requires the client to trust the proxy CA.** Install BrowserUp's `ca-certificate-rsa.cer` into the client/OS trust store (CI), or — test-only — `options.setAcceptInsecureCerts(true)` for a throwaway browser. `proxy.setTrustAllServers(true)` only makes the *proxy* trust *upstream* servers; it does **not** make the browser trust the proxy.
- Plain-HTTP targets need no CA step; state per test which scheme the target uses.

### Pointing the client
- The proxy is useless until the **client** routes through it: `ClientUtil.createSeleniumProxy(proxy)` → `options.setProxy(...)`, or Appium proxy capabilities. This is the whole point — make it explicit.
- Enable only the `CaptureType`s you assert on, and filter on the **narrowest** URL match, so recordings stay readable and unrelated traffic passes through.

### Assertions & waits
- **No `Thread.sleep`-as-a-wait.** Wait on `proxy.waitForQuiescence(quiet, timeout, unit)` (the network settling) or a real client-visible signal (`WebDriverWait`). A longer timeout is a *deadline*, not a sleep. `setLatency` is a *real* injected delay, not a wait.
- **Listener before action**: call `recordPage`/register filters *before* driving the client; doing it after misses the request.
- Read the payload with `entry.getRequest().getPostData().getText()` and headers from `getRequest().getHeaders()` — don't re-parse raw bytes.
- A "not called" assertion checks the HAR entries **after** a client-visible completion signal — never after a sleep.

### Hygiene
- Wrap all `BrowserUp` filter/HAR wiring in the `ProxyControls` helper with intent names — no raw `proxy.addResponseFilter(...)` in `@Test` methods.
- Never persist auth headers / tokens / PII into a recorded HAR — scrub before writing.
- Don't reach for the proxy when you actually have a Playwright `Page` — `page.route` is simpler and needs no CA. Justify the choice (non-Playwright client / multi-process).

### What NOT to do
- No proxy without wiring it into the client via `createSeleniumProxy` (or Appium caps) — it intercepts nothing.
- No HTTPS interception without trusting the proxy CA — the client errors on every TLS handshake (`setTrustAllServers` is not enough).
- No `Thread.sleep` to "wait for the request" — use `waitForQuiescence` or a client signal.
- No raw `BrowserUp` filter/HAR wiring scattered through tests — wrap it in `ProxyControls`.
- No static/committed CA reused as a secret — generate/trust per run.
- No auth headers or secrets persisted in a HAR.
- No proxy where a Playwright `page.route` (no CA, in-process) expresses the test just as well.

## Generation steps

1. Confirm **which client** (Selenium / Appium), **intent** (record/assert via HAR vs fault), and whether the target is **HTTPS** (→ CA-trust step).
2. Add or extend `support/proxy/ProxyControls.java` — `start()` + `enableHarCaptureTypes`, `recordPage`, `failPostWith` (request-filter short-circuit), `awaitRequest` (`waitForQuiescence` + HAR), `stop()`. Expose it on `ProxyBaseTest`.
3. Wire the proxy into the WebDriver via `SeleniumClient.chromeThroughProxy` (`ClientUtil.createSeleniumProxy`) and **trust the CA** for HTTPS.
4. `recordPage`/register filters before the action; assert via `awaitRequest` (payload from `getPostData().getText()`) or the HAR entries, waiting only on `waitForQuiescence` / client signals.
5. For determinism/debugging, persist a scrubbed `proxy.har()` under `build/artifacts/har/`.
6. Run `./gradlew test`. In CI, ensure the job trusts the per-run CA before the client starts.

## Cross-references

- **`qa/java/skills/network-monitoring`** — in-Playwright routing; reach for it first **if** you have a `Page`. The proxy is for when you don't.
- **`qa/java/skills/network-monitoring`** — raw CDP hooks below routing (Playwright + Chromium only); the proxy covers the cross-client case CDP can't.
- **`qa/typescript/skills/network-monitoring`** — the **canonical** skill this ports the *structure* from (`mockttp`); consult it for the conceptual model and the three-way pick.
- **`qa/dotnet/skills/network-monitoring`** — the sibling .NET port (`Titanium.Web.Proxy`, `BeforeRequest`/`BeforeResponse`).
- **`qa/cicd/java/skills/ci-pipelines`** — runs these tests; the job starts/stops the proxy and trusts the per-run CA before the client launches (no long-lived secret).
