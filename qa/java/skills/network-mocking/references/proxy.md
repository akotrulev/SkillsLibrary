# QA — Out-of-Browser MITM Proxy (Java, BrowserUp Proxy + Selenium)

An **out-of-process MITM HTTP(S) proxy** for tests whose client is **not Playwright** — a Selenium
WebDriver, an Appium driver, or several processes — on Java 21 + TestNG. The proxy sits between the client
and the network: the test points the client at it, records a HAR, asserts a request fired, or injects a fault.
It works for any client that honours a proxy, in any browser. The cost is **TLS interception**: the client
must trust the proxy's CA.

When the test has a Playwright `Page`, this file is the wrong tool: `references/playwright-routes.md` does
the same in-process, with no CA and no extra port.

> **The library is archived.** `com.browserup:browserup-proxy-core` (the BrowserMob successor) had its last
> release, **2.1.2**, in December 2020 (Maven Central, checked 2026-10-11), and its GitHub repository is
> archived. It still runs the moves below, but it gets no fixes and was not exercised on Java 21 by this
> skill. Keep it where a suite already uses it; for a new suite, weigh a maintained external proxy
> (mitmproxy, or WireMock 3 in proxy mode) — neither is taught here.

## Stack

| Artifact | Version | Note |
|---|---|---|
| `com.browserup:browserup-proxy-core` | 2.1.2 | Exact; the last release |
| `org.seleniumhq.selenium:selenium-java` | 4.51.0 | The client under test (Maven Central, 2026-10-11) |
| `org.testng:testng` / `org.assertj:assertj-core` | 7.12.0 / 3.27.7 | As in the Playwright lane |

Helpers live in `src/test/java/<pkg>/support/proxy/`. A recorded HAR lands in
`build/playwright-artifacts/<Class>.<method>.har` — the folder the Java CI references already upload on
failure, so a proxy run's evidence travels with the rest.

## When to use

- Capture or assert the HTTP(S) calls a **Selenium or Appium** test makes.
- **Fault-inject** from outside the browser: short-circuit a request with a `500`, or add latency.
- Record a HAR of a multi-process flow.
- Drive the same capture logic across Chrome, Firefox, Edge or a mobile app — one proxy, every client.

## When NOT to use

- A Playwright test → `references/playwright-routes.md` (and `references/cdp.md` for throttling)
- Writing the Selenium page objects themselves → `qa/java/skills/ui-test-author/selenium`
- TypeScript and .NET proxy lanes → `qa-network-mocking-typescript` (mockttp), `qa-network-mocking-dotnet`
  (Titanium.Web.Proxy)

## Inputs needed

1. **Which client** — Selenium (which browser?) or Appium. It decides how the proxy is wired in.
2. **Intent** — record and assert, or inject a fault; and is the target **HTTPS** (then the CA step applies)?
3. **The signal** — the HAR entry or client-visible state that proves the flow finished.

## Decision matrix — the BrowserUp moves

| Goal | Call | Note |
|---|---|---|
| Start | `new BrowserUpProxyServer()` → `start()` | `getPort()` afterwards is the address to point the client at |
| Rich capture | `enableHarCaptureTypes(CaptureType.REQUEST_CONTENT, …)` | Bodies and headers are captured only when enabled |
| Start recording | `newHar(label)` | Before the action |
| Read the recording | `getHar().getLog().getEntries()` | `entry.getRequest().getMethod()` is a `HttpMethod` **enum**; `getUrl()`, `getPostData().getText()`, `getHeaders()` |
| Short-circuit a request | `addRequestFilter((request, contents, messageInfo) -> response)` | A non-null `HttpResponse` answers without reaching the network |
| Add latency | `setLatency(ms, TimeUnit.MILLISECONDS)` | A real delay on every request, inside the proxy — not a test sleep |
| Wait for the network to settle | `waitForQuiescence(quietMs, timeoutMs, TimeUnit.MILLISECONDS)` | Returns `false` on timeout |
| Stop | `stop()` | In `@AfterMethod(alwaysRun = true)` |

## 1. The helper — `support/proxy/ProxyControls.java`

```java
package com.example.uitests.support.proxy;

import com.browserup.bup.BrowserUpProxy;
import com.browserup.bup.BrowserUpProxyServer;
import com.browserup.bup.proxy.CaptureType;
import com.browserup.harreader.model.Har;
import com.browserup.harreader.model.HarEntry;
import io.netty.handler.codec.http.DefaultFullHttpResponse;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.netty.handler.codec.http.HttpVersion;
import org.openqa.selenium.Proxy;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.TimeUnit;

public final class ProxyControls {
    private static final long QUIET_PERIOD_MS = 500;
    private static final Path ARTIFACTS = Path.of("build", "playwright-artifacts");

    private final BrowserUpProxy proxy;

    private ProxyControls(BrowserUpProxy proxy) {
        this.proxy = proxy;
    }

    public static ProxyControls start() {
        BrowserUpProxy proxy = new BrowserUpProxyServer();
        proxy.setTrustAllServers(true);
        proxy.start();
        proxy.enableHarCaptureTypes(CaptureType.REQUEST_CONTENT, CaptureType.REQUEST_HEADERS, CaptureType.RESPONSE_HEADERS);
        return new ProxyControls(proxy);
    }

    public Proxy seleniumProxy() {
        String address = "localhost:" + proxy.getPort();
        return new Proxy().setHttpProxy(address).setSslProxy(address);
    }

    public void recordPage(String label) {
        proxy.newHar(label);
    }

    public void failPostWith(String urlPart, int status) {
        proxy.addRequestFilter((request, contents, messageInfo) ->
                "POST".equals(request.method().name()) && messageInfo.getUrl().contains(urlPart)
                        ? new DefaultFullHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.valueOf(status))
                        : null);
    }

    public void addLatency(long millis) {
        proxy.setLatency(millis, TimeUnit.MILLISECONDS);
    }

    public List<HarEntry> settledEntries(long timeoutMs) {
        if (!proxy.waitForQuiescence(QUIET_PERIOD_MS, timeoutMs, TimeUnit.MILLISECONDS)) {
            throw new IllegalStateException("Network traffic did not settle within " + timeoutMs + " ms");
        }
        return proxy.getHar().getLog().getEntries();
    }

    public void keepScrubbedHar(String evidenceName) throws IOException {
        Har har = proxy.getHar();
        har.getLog().getEntries().forEach(entry -> entry.getRequest().getHeaders().removeIf(header ->
                header.getName().equalsIgnoreCase("Authorization") || header.getName().equalsIgnoreCase("Cookie")));
        Files.createDirectories(ARTIFACTS);
        har.writeTo(ARTIFACTS.resolve(evidenceName + ".har").toFile());
    }

    public void stop() {
        proxy.stop();
    }
}
```

- `seleniumProxy()` builds Selenium's own `Proxy` from the port; it avoids BrowserUp's `ClientUtil`, which was
  compiled against Selenium 3.
- `setTrustAllServers(true)` makes the **proxy** trust upstream servers. It does **not** make the browser
  trust the proxy — that is the CA step (§2).
- `settledEntries` waits on `waitForQuiescence` — the network quiet for 500 ms, within a deadline — and fails
  loudly when the deadline passes, instead of returning a half-recorded HAR.
- The HAR is scrubbed of `Authorization` and `Cookie` request headers before it is written.

## 2. The lifecycle and the client

The proxy and the driver are created and stopped in the class's own hooks; a test never starts or quits
anything, and has no `try`/`finally`. In a project built on `qa/java/skills/ui-test-author/selenium`, put the
two proxy lines into that skill's base class where it creates the driver, instead of a second base class.

```java
package com.example.uitests.support.proxy;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;

import java.io.IOException;
import java.lang.reflect.Method;

public abstract class ProxyTest {
    protected ProxyControls proxy;
    protected WebDriver driver;
    private String evidenceName;

    @BeforeMethod(alwaysRun = true)
    public void startProxyAndBrowser(Method method) {
        evidenceName = getClass().getSimpleName() + "." + method.getName();
        proxy = ProxyControls.start();
        ChromeOptions options = new ChromeOptions();
        options.setProxy(proxy.seleniumProxy());
        options.setAcceptInsecureCerts(true);
        options.addArguments("--headless=new", "--proxy-bypass-list=<-loopback>");
        driver = new ChromeDriver(options);
    }

    @AfterMethod(alwaysRun = true)
    public void stopBrowserAndProxy() throws IOException {
        proxy.keepScrubbedHar(evidenceName);
        driver.quit();
        proxy.stop();
    }
}
```

- **HTTPS needs the CA.** `setAcceptInsecureCerts(true)` is the test-only shortcut for a throwaway browser.
  In CI, prefer importing BrowserUp's `ca-certificate-rsa.cer` into the browser's trust store (NSS on Linux)
  before the browser starts. A plain-HTTP target needs neither.
- `--proxy-bypass-list=<-loopback>` makes Chrome proxy `localhost` targets too; by default it sends loopback
  traffic around the proxy.
- `BASE_URL` is read by the page objects, exactly as in the Playwright lane.
- **Appium:** set the device's Wi-Fi proxy (or the Appium proxy capabilities) to the proxy's host and port and
  install the CA in the device trust store; the helpers apply unchanged. The Appium driver lifecycle belongs to
  `qa/java/skills/ui-test-author/appium`.

## 3. Assert a request fired — method and payload

```java
package com.example.uitests.tests;

import com.browserup.harreader.model.HarEntry;
import com.browserup.harreader.model.HttpMethod;
import com.example.uitests.pages.CartPage;
import com.example.uitests.support.proxy.ProxyTest;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

public class CheckoutProxyTest extends ProxyTest {
    private CartPage cartPage;

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        cartPage = new CartPage(driver);
    }

    @Test
    public void Should_PostCartTotal_When_OrderIsPlaced() {
        proxy.recordPage("Checkout");
        cartPage.open();

        cartPage.placeOrder();

        assertThat(proxy.settledEntries(10_000))
                .filteredOn(entry -> entry.getRequest().getMethod() == HttpMethod.POST
                        && entry.getRequest().getUrl().endsWith("/api/checkout"))
                .extracting(entry -> entry.getRequest().getPostData().getText())
                .as("checkout POST bodies")
                .containsExactly("{\"totalMinor\":15000,\"currency\":\"EUR\"}");
    }

    @Test
    public void Should_NotCallLegacyPricing_When_CartIsRecalculated() {
        proxy.recordPage("Recalculate");
        cartPage.open();

        cartPage.recalculate();

        assertThat(proxy.settledEntries(10_000))
                .extracting(entry -> entry.getRequest().getUrl())
                .as("legacy pricing calls")
                .noneMatch(url -> Pattern.compile("/api/legacy-pricing").matcher(url).find());
    }

    @Test
    public void Should_ShowErrorBanner_When_CheckoutReturns500() {
        proxy.failPostWith("/api/checkout", 500);
        cartPage.open();

        cartPage.placeOrder();

        assertThat(cartPage.errorBannerText()).as("error banner").isEqualTo("We couldn't place your order");
    }
}
```

- `recordPage` (and any filter) goes **before** the action; registered afterwards, it misses the request.
- `getMethod()` is BrowserUp's `HttpMethod` enum — a `String` comparison is always false and would make the
  first test impossible to pass.
- `containsExactly` on the bodies is one expected value: exactly one checkout POST, with this body. The body
  string is compared as sent; a client that reorders fields needs a parsed comparison instead.
- `CartPage` is a Selenium page object over `data-testid` locators (`Cart.PlaceOrder`, `Cart.Recalculate`,
  `Cart.Total`, `Cart.ErrorBanner`). `placeOrder()` and `recalculate()` return once the client shows the result,
  with a `WebDriverWait` on the element — so "not called" is read after a real completion signal.
- To add latency instead of a fault, `proxy.addLatency(2_000)` before the action: a real delay inside the proxy,
  never a `Thread.sleep` in the test.

## Rules

- One proxy and one client per test, created in `@BeforeMethod(alwaysRun = true)` and stopped in
  `@AfterMethod(alwaysRun = true)`; no `try`/`finally` in a test.
- `recordPage` and filters before the action; read the HAR through `settledEntries`, which fails when the
  network does not settle.
- Compare `getMethod()` to `HttpMethod` constants, never to a `String`.
- HTTPS interception needs the client to trust the proxy CA; `setTrustAllServers` is about the upstream side
  only.
- Locators are `data-testid`, PascalCase dot-separated, inside page objects.
- Scrub `Authorization` and `Cookie` before a HAR is written; never commit one.
- Pin `browserup-proxy-core:2.1.2` exactly, and know it is archived.

## What NOT to do

- No proxy that the client is not pointed at — it intercepts nothing.
- No HTTPS interception without the CA step.
- No `Thread.sleep` to "wait for the request" — `settledEntries` or a client signal.
- No raw `addRequestFilter(...)` in a test — a `ProxyControls` method with an intent name.
- No proxy where a Playwright `page.route` would do.

## Generation steps

1. Confirm the client, the intent and whether the target is HTTPS.
2. Add an intent method to `ProxyControls`; extend `ProxyTest` (or add its two lines to the Selenium base).
3. Register recording or filters before the action; assert on `settledEntries` or a client-visible state.
4. Run `./gradlew test`. In CI, trust the CA before the browser starts; a failed run's HAR is uploaded with
   `build/playwright-artifacts/`.

## Cross-references

- `references/playwright-routes.md` — in-process routing when there is a Playwright `Page`.
- `references/cdp.md` — real throttling, Chromium only, Playwright only.
- `qa/java/skills/ui-test-author/selenium` — Selenium page objects and the driver base class.
- `qa/java/skills/ui-test-author/appium` — the Appium driver lifecycle.
- `qa/cicd/java/skills/ci-pipelines` — the job that starts the browser and uploads the evidence.
- `qa-network-mocking-typescript`, `qa-network-mocking-dotnet` — the sibling lanes.
