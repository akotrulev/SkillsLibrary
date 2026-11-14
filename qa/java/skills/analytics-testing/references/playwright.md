# Analytics and consent with Playwright Java (Playwright 1.63 + TestNG)

Every sample extends `com.example.uitests.support.BaseTest`
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`). Verified against Playwright 1.63 on Chromium and
WebKit: a `navigator.sendBeacon` to `/g/collect` is caught by a context route as a `POST` whose `postData()` holds
the beacon body, request waits resolve for routed requests, `setExtraHTTPHeaders` delivers `Sec-GPC: 1` to the
server, and gtag's `arguments` entries in the `dataLayer` read back by index. JSON goes through Gson, which
Playwright for Java already depends on.

## 1. The helpers

```java
package com.example.uitests.support;

import com.microsoft.playwright.Page;
import com.microsoft.playwright.Request;
import com.microsoft.playwright.Route;

import java.net.URI;
import java.net.URLDecoder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import static java.nio.charset.StandardCharsets.UTF_8;

public final class Tracker {
    public static final String GA4 = "ga4";
    public static final String META_PIXEL = "meta-pixel";

    private static final Pattern GA4_COLLECT = Pattern.compile("/g/collect(\\?|$)");
    private static final Pattern META_PIXEL_COLLECT = Pattern.compile("^https://www\\.facebook\\.com/tr/?(\\?|$)");

    private final Page page;
    private final List<Hit> captured = new ArrayList<>();

    public Tracker(Page page) {
        this.page = page;
    }

    public record Hit(String destination, String eventName, Map<String, String> params) {
    }

    public void capture() {
        page.context().route(GA4_COLLECT, this::recordAndFulfill);
        page.context().route(META_PIXEL_COLLECT, this::recordAndFulfill);
    }

    public List<Hit> hits() {
        return List.copyOf(captured);
    }

    public List<Hit> hitsTo(String destination) {
        return captured.stream().filter(hit -> hit.destination().equals(destination)).toList();
    }

    public Hit nextEvent(String eventName, Runnable action) {
        Request request = page.waitForRequest(sent -> hitsOf(sent).stream().anyMatch(hit -> hit.eventName().equals(eventName)), action);
        return hitsOf(request).stream()
                .filter(hit -> hit.eventName().equals(eventName))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException(
                        "No " + eventName + " event in " + request.method() + " " + request.url() + "; body: " + request.postData()));
    }

    private void recordAndFulfill(Route route) {
        captured.addAll(hitsOf(route.request()));
        route.fulfill(new Route.FulfillOptions().setStatus(204));
    }

    private static List<Hit> hitsOf(Request request) {
        return GA4_COLLECT.matcher(request.url()).find() ? ga4Hits(request) : List.of(pixelHit(request));
    }

    private static List<Hit> ga4Hits(Request request) {
        Map<String, String> shared = paramsOf(URI.create(request.url()).getRawQuery());
        List<String> lines = Arrays.stream(Objects.requireNonNullElse(request.postData(), "").split("\n"))
                .filter(line -> !line.isEmpty())
                .toList();
        List<Map<String, String>> events = lines.isEmpty()
                ? List.of(shared)
                : lines.stream().map(line -> merge(shared, paramsOf(line))).toList();
        return events.stream().map(params -> new Hit(GA4, params.getOrDefault("en", ""), params)).toList();
    }

    private static Hit pixelHit(Request request) {
        Map<String, String> params = merge(paramsOf(URI.create(request.url()).getRawQuery()), paramsOf(request.postData()));
        return new Hit(META_PIXEL, params.getOrDefault("ev", ""), params);
    }

    private static Map<String, String> paramsOf(String encoded) {
        return Arrays.stream(Objects.requireNonNullElse(encoded, "").split("&"))
                .filter(pair -> !pair.isEmpty())
                .map(pair -> pair.split("=", 2))
                .collect(Collectors.toMap(
                        pair -> URLDecoder.decode(pair[0], UTF_8),
                        pair -> pair.length == 2 ? URLDecoder.decode(pair[1], UTF_8) : "",
                        (first, second) -> second,
                        LinkedHashMap::new));
    }

    private static Map<String, String> merge(Map<String, String> shared, Map<String, String> own) {
        Map<String, String> merged = new LinkedHashMap<>(shared);
        merged.putAll(own);
        return Map.copyOf(merged);
    }
}
```

```java
package com.example.uitests.support;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.microsoft.playwright.Page;

import java.util.List;
import java.util.Map;
import java.util.Objects;

public final class DataLayer {
    private static final Gson GSON = new Gson();
    private static final Gson SNAKE_CASE = new GsonBuilder()
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
            .create();

    private final Page page;

    public DataLayer(Page page) {
        this.page = page;
    }

    public Map<String, String> consentState(String command) {
        page.waitForFunction("command => (window.dataLayer ?? []).some(e => e[0] === 'consent' && e[1] === command)", command);
        String json = (String) page.evaluate(
                "command => JSON.stringify(Object.fromEntries(Object.entries((window.dataLayer ?? [])"
                        + ".filter(e => e[0] === 'consent' && e[1] === command).at(-1)[2]).map(([k, v]) => [k, String(v)])))",
                command);
        return Objects.requireNonNull(GSON.fromJson(json, new TypeToken<Map<String, String>>() { }.getType()),
                () -> "Consent " + command + " state did not deserialize: " + json);
    }

    public <T> List<T> eventsNamed(String eventName, Class<T> type) {
        page.waitForFunction("name => (window.dataLayer ?? []).some(e => e.event === name)", eventName);
        String json = (String) page.evaluate("name => JSON.stringify((window.dataLayer ?? []).filter(e => e.event === name))", eventName);
        return Objects.requireNonNull(SNAKE_CASE.fromJson(json, TypeToken.getParameterized(List.class, type).getType()),
                () -> "dataLayer '" + eventName + "' entries did not deserialize: " + json);
    }
}
```

```java
package com.example.uitests.support;

import com.microsoft.playwright.Page;

import java.util.Map;

public final class PrivacySignals {
    private final Page page;

    public PrivacySignals(Page page) {
        this.page = page;
    }

    public void sendGlobalPrivacyControl() {
        page.context().setExtraHTTPHeaders(Map.of("Sec-GPC", "1"));
        page.context().addInitScript(
                "Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', { get: () => true, configurable: true })");
    }
}
```

- **`tracker.capture()` runs in every analytics class's `@BeforeMethod`**, before the first navigation. A class
  that forgets it lets hits through to the network.
- **A GA4 request can carry several events.** Shared parameters sit in the URL; with a body, each line is one
  event's parameters, and `merge` lays each line over the shared set. That shape is observed from gtag.js, not a
  published contract (SKILL.md, *Rules*).
- **The Meta Pixel** is read from its query string (`id`, `ev`, `cd[...]` custom data — the image-pixel format
  Meta documents) and any form body.
- **`gtag()` pushes an `arguments` object**, so a consent command reads as `e[0..2]`; a GTM-style
  `dataLayer.push({ event })` reads as `e.event`. Values are stringified in the page (`wait_for_update` is a
  number) so the state comes back as `Map<String, String>`.
- **The `waitForFunction` calls are the waits** (`ui-test-author/playwright/references/assertions.md` §5): page
  state no locator matcher can see. If the push never happens they time out and fail the test.
- Route handlers in the Java sync API run on the test's thread while Playwright dispatches events, so the plain
  `ArrayList` is safe here.
- **The GPC init script stands in for a browser setting.** The header plus the property is what a GPC browser
  sends. Call `sendGlobalPrivacyControl()` **before** the first navigation.

## 2. Consent gating

```java
package com.example.uitests.tests;

import com.example.uitests.pages.ConsentBanner;
import com.example.uitests.pages.ShopPage;
import com.example.uitests.support.BaseTest;
import com.example.uitests.support.DataLayer;
import com.example.uitests.support.Tracker;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.Map;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.assertj.core.api.Assertions.assertThat;

public class ConsentGatingTest extends BaseTest {
    private Tracker tracker;
    private DataLayer dataLayer;
    private ShopPage shopPage;
    private ConsentBanner consentBanner;

    @BeforeMethod(alwaysRun = true)
    public void createHelpers() {
        tracker = new Tracker(page);
        tracker.capture();
        dataLayer = new DataLayer(page);
        shopPage = new ShopPage(page);
        consentBanner = new ConsentBanner(page);
    }

    @Test
    public void Should_SendNoTrackingRequest_When_VisitorHasNotChosen() {
        shopPage.openHome();
        assertThat(consentBanner.root()).isVisible();

        shopPage.openPricing();

        assertThat(tracker.hits()).as("tracking hits before any consent choice").isEmpty();
    }

    @Test
    public void Should_SendPageViewToTestProperty_When_VisitorAcceptsAll() {
        shopPage.openHome();

        Tracker.Hit pageView = tracker.nextEvent("page_view", consentBanner::acceptAll);

        assertThat(pageView.params()).as("page_view hit parameters")
                .containsEntry("tid", requiredEnv("GA4_TEST_MEASUREMENT_ID"));
    }

    @Test
    public void Should_SendNoTrackingRequest_When_VisitorRejectsAll() {
        shopPage.openHome();
        consentBanner.rejectAll();
        assertThat(dataLayer.consentState("update")).as("consent update after reject")
                .containsEntry("analytics_storage", "denied");

        shopPage.openPricing();

        assertThat(tracker.hits()).as("tracking hits after reject").isEmpty();
    }

    @Test
    public void Should_DefaultEveryConsentModeV2TypeToDenied_When_PageLoads() {
        shopPage.openHome();

        Map<String, String> defaults = dataLayer.consentState("default");

        assertThat(defaults).as("consent default").containsAllEntriesOf(Map.of(
                "ad_storage", "denied",
                "ad_user_data", "denied",
                "ad_personalization", "denied",
                "analytics_storage", "denied"));
    }
}
```

- `ShopPage.openPricing()` navigates and returns once the pricing landmark is visible: the second page load is the
  completion signal that gives a late tag time to fire, so the empty list means something.
- The reject test asserts the precondition (the update was pushed) before the act — part of one behaviour, "after
  reject nothing is sent"; without it an empty list could mean the click never registered.
- AssertJ's `.as(...)` names the subject, and its failure prints the whole map or list — the evidence.
- In **basic** Consent Mode no Google tag loads before the choice, so the first test's empty list is the whole
  assertion. In **advanced** mode tags load denied and send cookieless pings: replace it with §3.
- §3 and §4 are further tests of classes shaped like this one; `checkoutPage = new CheckoutPage(page)` is a field
  built in the same `@BeforeMethod`.

## 3. Advanced Consent Mode — the `gcs` value

Google documents `gcs` as carrying the `ad_storage` and `analytics_storage` choice; its encoding is not published.
Record it from your own tag in each state and pin the values as constants.

```java
private static final String GCS_ALL_DENIED = "G100";
private static final String GCS_ALL_GRANTED = "G111";

@Test
public void Should_SendCookielessPing_When_ConsentIsDenied() {
    Tracker.Hit pageView = tracker.nextEvent("page_view", shopPage::openHome);

    assertThat(pageView.params()).as("page_view hit").containsEntry("gcs", GCS_ALL_DENIED);
}

@Test
public void Should_SendGrantedPing_When_VisitorAcceptsAll() {
    shopPage.openHome();

    Tracker.Hit engagement = tracker.nextEvent("user_engagement", consentBanner::acceptAll);

    assertThat(engagement.params()).as("hit after accept").containsEntry("gcs", GCS_ALL_GRANTED);
}
```

The constants are what a gtag.js build was observed to send (`G1<ad_storage><analytics_storage>`, 1 = granted);
confirm them against a hit you recorded. Use the event your tag really sends after an update.

## 4. An event and its parameters

```java
public record PurchasePush(String event, Ecommerce ecommerce) {
}

public record Ecommerce(String transactionId, BigDecimal value, String currency) {
}
```

```java
@Test
public void Should_SendPurchaseWithOrderTotal_When_OrderIsPlaced() {
    checkoutPage.open();
    consentBanner.acceptAll();

    Tracker.Hit purchase = tracker.nextEvent("purchase", checkoutPage::placeOrder);

    assertThat(purchase.params()).as("purchase hit").containsAllEntriesOf(Map.of(
            "en", "purchase",
            "cu", "EUR",
            "ep.transaction_id", "ORD-1001"));
}

@Test
public void Should_PushPurchaseToDataLayer_When_OrderIsPlaced() {
    checkoutPage.open();
    consentBanner.acceptAll();

    checkoutPage.placeOrder();

    assertThat(dataLayer.eventsNamed("purchase", PurchasePush.class)).as("dataLayer purchase pushes")
            .containsExactly(new PurchasePush("purchase", new Ecommerce("ORD-1001", new BigDecimal("68"), "EUR")));
}
```

- The beacon test pins the wire keys **you recorded** from your own tag — `cu` and `ep.transaction_id` stand in for
  them here. The `dataLayer` test pins the payload against the tracking plan.
- `containsExactly` also catches a **double push**: two purchases for one order fail the test.
- `JSON.stringify` writes `68.00` as `68`, and `BigDecimal.equals` compares scale, so the expected value is
  `new BigDecimal("68")`. Record equality then compares every field and AssertJ prints both lists on a mismatch.
- A real GA4 `ecommerce` object carries an `items` array; assert it in its own test against a builder
  (`test-data-builder`).

## 5. Global Privacy Control

```java
public class GlobalPrivacyControlTest extends BaseTest {
    private Tracker tracker;
    private DataLayer dataLayer;
    private ShopPage shopPage;
    private ConsentBanner consentBanner;

    @BeforeMethod(alwaysRun = true)
    public void createHelpers() {
        tracker = new Tracker(page);
        tracker.capture();
        new PrivacySignals(page).sendGlobalPrivacyControl();
        dataLayer = new DataLayer(page);
        shopPage = new ShopPage(page);
        consentBanner = new ConsentBanner(page);
    }

    @Test
    public void Should_SendNoAdPixel_When_GlobalPrivacyControlIsOn() {
        shopPage.openHome();
        consentBanner.acceptAll();

        shopPage.openPricing();

        assertThat(tracker.hitsTo(Tracker.META_PIXEL)).as("Meta Pixel hits with GPC on").isEmpty();
    }

    @Test
    public void Should_KeepAdConsentDenied_When_GlobalPrivacyControlIsOn() {
        shopPage.openHome();

        consentBanner.acceptAll();

        assertThat(dataLayer.consentState("update")).as("consent update with GPC on")
                .containsEntry("ad_user_data", "denied");
    }
}
```

What GPC must switch off is a legal and product decision (an opt-out of sale or sharing under the applicable law):
take the expected outcome from the privacy requirements, never from the current behaviour.

## Anti-patterns

- `route.resume()` on a collect request — the hit reaches the real property. Fulfil it.
- `route.abort()` on a beacon you assert on — some tags retry or fall back, and the test reads the retry.
- Asserting only that `gtag.js` or `fbevents.js` loaded — it proves nothing was sent correctly.
- `Thread.sleep` before reading `hits()` — wait on a page signal, then read.
- Reading the hit list straight after a click that should *not* send anything — load the next page first.
- A consent class that loads a saved storage state with a consent cookie.
