# QA — Playwright Routing, Mocking and Traffic Assertions (Java / Playwright 1.63 + TestNG)

Intercepts, mocks, holds, asserts and shapes HTTP traffic in Playwright for Java (sync API) with TestNG.
Every sample extends `com.example.uitests.support.BaseTest`
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`), which owns Playwright, the browser, a
context and page per test, and the failure evidence. Route handlers and traffic reads live in two helpers,
`MockApi` and `Traffic`, built in the class's own `@BeforeMethod`; a test calls intent methods, never
`page.route(...)`. Every wait is a request or response predicate or a page object's completion signal.

Two binding differences drive the Java shape: the method is **`route.resume()`** (`continue` is a reserved
word), and Java's `Route`, `Request` and `Response` have **no JSON helpers** (`setJson`, `postDataJSON`,
`json()`). JSON goes through Gson — Playwright for Java already depends on it (2.14.0 in 1.63) and exposes it
in its API — so no JSON library is added. Gson reads and writes Java records.

## When to use

- Mock a backend or third-party response so a UI test is deterministic — canned JSON, a forced `500`.
- **Assert** an endpoint was called, with the expected method and payload — or was **not** called.
- Assert the app shell's **security headers** and **TLS** details.
- Modify a real response in flight (force a feature flag) or tag an outgoing request.
- Replay a committed HAR of a third-party dependency.
- Show the loading state while a request is **held**, or the offline state.

## When NOT to use

- Real bandwidth and latency, cache disable, CPU throttling, performance metrics → `references/cdp.md`
- A client with no Playwright `Page` (Selenium, Appium) → `references/proxy.md`
- Recording a HAR as evidence → `qa/java/skills/evidence-capture` §5
- WebSocket and SSE → `qa/java/skills/realtime-stream-testing`
- No browser at all → `qa/java/skills/api-test-author`

## Inputs needed

1. **What traffic** — the endpoint(s) as a glob or `Pattern`, first-party or third-party.
2. **Intent** — mock, hold, assert called / not called, modify, HAR replay, offline, headers or TLS.
3. **Scope** — the test's page (`page.route`) or every page of the context including popups
   (`page.context().route`).

## Decision matrix

| Goal | Call | Note |
|---|---|---|
| Canned data, never hit the network | `route.fulfill(new Route.FulfillOptions().setStatus(200).setContentType("application/json").setBody(json))` | No `setJson` in Java; `setPath(Path)` serves a fixture file |
| A forced error | `route.fulfill(...setStatus(500)...)` | The app's error path becomes deterministic |
| Block a resource | `route.abort("blockedbyclient")` | Analytics, ads, fonts |
| Let it through unchanged | `route.resume()` | Goes to the network and **skips** the remaining handlers |
| Defer to an earlier handler | `route.fallback()` | Chains to the next matching handler |
| Modify a real response | `route.fetch()` → edit `text()` → `route.fulfill(...setResponse(response).setBody(...))` | Keeps the real status and headers |
| Tag the outgoing request | `route.resume(new Route.ResumeOptions().setHeaders(headers))` | A `Cookie` header set here is ignored since 1.52 |
| Hold a request, release it later | keep the `Route`, call `resume()` from the test | The Java router treats an unhandled return as a pending handler |
| Assert a call happened | `page.waitForRequest(glob, action)` / `page.waitForResponse(predicate, action)` | The action runs **inside** the wait |
| Assert a call did not happen | `page.requests()` [1.56] after the completion signal | The page's recent requests; no listener |
| Security headers, TLS | `response.allHeaders()`, `response.securityDetails()` | Cross-browser; no CDP |
| Deterministic third party | `page.routeFromHAR(har, new Page.RouteFromHAROptions().setUrl(...).setNotFound(HarNotFound.ABORT))` | Update deliberately (§7) |
| Offline | `page.context().setOffline(true)` | Cross-browser |

## 1. The helpers

`MockApi` owns every route; `Traffic` reads what the page sent. Both wrap the `page` `BaseTest` opened and own
no lifecycle — the context, and with it every route, is closed after each test.

```java
package com.example.uitests.support;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.microsoft.playwright.APIResponse;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Route;
import com.microsoft.playwright.options.HarMode;
import com.microsoft.playwright.options.HarNotFound;
import com.microsoft.playwright.options.RouteFromHarUpdateContentPolicy;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public final class MockApi {
    private static final Gson GSON = new Gson();
    private static final Path PAYMENTS_HAR = Path.of("src", "test", "resources", "har", "payments.har");
    private static final boolean HAR_UPDATE = "1".equals(System.getenv("HAR_UPDATE"));

    private final Page page;

    public MockApi(Page page) {
        this.page = page;
    }

    public void stubOrders(List<Order> orders) {
        String body = GSON.toJson(orders);
        page.route("**/api/orders", route -> route.fulfill(new Route.FulfillOptions()
                .setStatus(200)
                .setContentType("application/json")
                .setBody(body)));
    }

    public void failOrdersWith(int status) {
        page.route("**/api/orders", route -> route.fulfill(new Route.FulfillOptions()
                .setStatus(status)
                .setContentType("application/problem+json")
                .setBody("{\"title\":\"Simulated failure\",\"status\":" + status + "}")));
    }

    public void blockAnalytics() {
        page.context().route(Pattern.compile("google-analytics\\.com|segment\\.io"), route -> route.abort("blockedbyclient"));
    }

    public void enableFlag(String flag) {
        page.route("**/api/feature-flags", route -> {
            APIResponse response = route.fetch();
            JsonObject flags = JsonParser.parseString(response.text()).getAsJsonObject();
            flags.addProperty(flag, true);
            route.fulfill(new Route.FulfillOptions().setResponse(response).setBody(flags.toString()));
        });
    }

    public void tagTenant(String tenantId) {
        page.route("**/api/**", route -> {
            Map<String, String> headers = new HashMap<>(route.request().headers());
            headers.put("x-test-tenant", tenantId);
            route.resume(new Route.ResumeOptions().setHeaders(headers));
        });
    }

    public HeldRequests holdOrders() {
        HeldRequests held = new HeldRequests();
        page.route("**/api/orders", held::hold);
        return held;
    }

    public void replayPayments() {
        page.routeFromHAR(PAYMENTS_HAR, new Page.RouteFromHAROptions()
                .setUrl("https://api.stripe.com/**")
                .setNotFound(HarNotFound.ABORT)
                .setUpdate(HAR_UPDATE)
                .setUpdateContent(RouteFromHarUpdateContentPolicy.ATTACH)
                .setUpdateMode(HarMode.MINIMAL));
    }

    public void goOffline() {
        page.context().setOffline(true);
    }

    public static final class HeldRequests {
        private final List<Route> held = new ArrayList<>();

        private void hold(Route route) {
            held.add(route);
        }

        public void release() {
            held.forEach(Route::resume);
            held.clear();
        }
    }
}
```

```java
package com.example.uitests.support;

import com.google.gson.Gson;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Request;

import java.util.List;
import java.util.regex.Pattern;

public final class Traffic {
    private static final Gson GSON = new Gson();

    private final Page page;

    public Traffic(Page page) {
        this.page = page;
    }

    public List<String> requestedUrls(Pattern url) {
        return page.requests().stream().map(Request::url).filter(seen -> url.matcher(seen).find()).toList();
    }

    public List<String> pageErrors() {
        return page.pageErrors();
    }

    public static <T> T jsonBody(Request request, Class<T> type) {
        return GSON.fromJson(request.postData(), type);
    }
}
```

The payloads are records next to the helpers — `record Order(String id, String status, long totalMinor)`,
`record CheckoutRequest(long totalMinor, String currency)` — and a payload with four or more fields gets a
builder (`qa/java/skills/test-data-builder`).

## 2. Mocking a response

```java
package com.example.uitests.tests;

import com.example.uitests.pages.OrdersPage;
import com.example.uitests.support.BaseTest;
import com.example.uitests.support.MockApi;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.List;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class OrdersNetworkTest extends BaseTest {
    private MockApi mockApi;
    private OrdersPage ordersPage;

    @BeforeMethod(alwaysRun = true)
    public void createHelpers() {
        mockApi = new MockApi(page);
        ordersPage = new OrdersPage(page);
    }

    @Test
    public void Should_ShowEmptyState_When_ThereAreNoOrders() {
        mockApi.stubOrders(List.of());

        ordersPage.navigate();

        assertThat(ordersPage.emptyState()).isVisible();
    }

    @Test
    public void Should_ShowErrorBanner_When_OrdersApiFails() {
        mockApi.failOrdersWith(500);

        ordersPage.navigate();

        assertThat(ordersPage.errorBanner()).hasText("We couldn't load your orders");
    }
}
```

- `mockApi` is a field built in `@BeforeMethod`, so every test has it. Register the route **before** the
  navigation or action that fires the request; a route added afterwards catches nothing.
- `OrdersPage.navigate()` only navigates; `open()` navigates and returns once the list is visible. The
  difference matters in §8, where the list never arrives while a request is held.
- Every locator the page object returns carries `describe(...)`, which names it in a failure.
- §3–§8 are further tests of classes shaped like this one: `cartPage`, `appShellPage` and
  `traffic = new Traffic(page)` are fields built in the same `@BeforeMethod`, and the class adds AssertJ's
  static `assertThat` beside Playwright's — Java picks by argument type.

## 3. Asserting a call — method and typed payload

The page object starts the wait and performs the action in one call, so the request cannot fire first:

```java
public Request placeOrder() {
    return page.waitForRequest("**/api/checkout", placeOrderButton::click);
}
```

```java
@Test
public void Should_PostCartTotal_When_OrderIsPlaced() {
    cartPage.open();

    Request checkout = cartPage.placeOrder();

    assertThat(checkout.method()).as("checkout request method").isEqualTo("POST");
    assertThat(Traffic.jsonBody(checkout, CheckoutRequest.class)).as("checkout request body")
            .isEqualTo(new CheckoutRequest(15_000, "EUR"));
}
```

- Java's `Request` has no `postDataJSON()`; `Traffic.jsonBody` parses `postData()` into the record, and
  record equality compares every field, so the failure prints both records.
- The two assertions are one behaviour — "the order is posted with the cart total". These assertions are
  AssertJ's (`org.assertj.core.api.Assertions.assertThat`), with `.as(...)` naming the subject.
- For "it was called and answered", `page.waitForResponse(response -> …, action)` returns the `Response`;
  assert its exact `status()` with the body as the description
  (`ui-test-author/playwright/references/assertions.md` §7).

## 4. Asserting a call did NOT happen, and that the page raised no errors

```java
@Test
public void Should_NotCallLegacyPricing_When_CartIsRecalculated() {
    cartPage.open();

    cartPage.recalculate();

    assertThat(traffic.requestedUrls(Pattern.compile("/api/legacy-pricing"))).as("legacy pricing calls").isEmpty();
}

@Test
public void Should_RaiseNoPageErrors_When_CartOpens() {
    cartPage.open();

    assertThat(traffic.pageErrors()).as("uncaught errors on the cart page").isEmpty();
}
```

- `recalculate()` returns once the new total is visible. The list is read **after** that signal, or the
  check passes only because the request had not fired yet.
- `page.requests()`, `page.consoleMessages()` and `page.pageErrors()` [1.56] return the page's most recent
  buffered items — no listener to register, no list to manage. The buffer is capped, so for a long flow
  register `page.onRequest(...)` in the class's `@BeforeMethod` instead. `clearConsoleMessages()` /
  `clearPageErrors()` reset them.
- Each page has its own buffer: a popup's traffic is read from the popup's `Page`.

## 5. Security headers and TLS — at the routing layer

The page object's `open()` returns the `Response` that `page.navigate` gave it — the document, after any
redirects:

```java
@Test
public void Should_SendSecurityHeaders_When_AppShellLoads() {
    Response shell = appShellPage.open();

    assertThat(shell.allHeaders().keySet()).as("security headers on the app shell")
            .contains("content-security-policy", "strict-transport-security", "x-frame-options");
}

@Test
public void Should_NegotiateTls13_When_AppShellLoads() {
    Response shell = appShellPage.open();

    assertThat(shell.securityDetails()).as("TLS details of the app shell")
            .extracting(details -> details.protocol).isEqualTo("TLS 1.3");
}
```

- `allHeaders()` returns every response header with **lower-cased** names, including the ones `headers()`
  omits; `headerValue(name)` reads one case-insensitively.
- `securityDetails()` returns a `SecurityDetails` with public fields `protocol`, `issuer`, `subjectName`,
  `validFrom`, `validTo` — or `null` over plain HTTP, which AssertJ reports as "expecting actual not to be
  null" instead of a `NullPointerException`.
- Both checks are cross-browser. CDP is not needed for either.

## 6. Modifying traffic in flight

- **The response:** `mockApi.enableFlag("betaCheckout")` fetches the real flags and re-serves them with one
  flag forced. Passing the `APIResponse` to `setResponse` keeps the real status and headers.
- **The request:** `mockApi.tagTenant("tenant-42")` adds a header. A `Cookie` header set through
  `route.resume` is ignored since 1.52 — add the cookie with `page.context().addCookies(...)` in the class's
  `@BeforeMethod`.

## 7. HAR replay and update

- `mockApi.replayPayments()` serves `https://api.stripe.com/**` from the committed HAR.
  `HarNotFound.ABORT` turns any request the HAR does not hold into a failure, so a new dependency cannot slip
  through to the live service; `HarNotFound.FALLBACK` would let it.
- **Updating** is a deliberate, local run against the real dependency: `HAR_UPDATE=1 ./gradlew test --tests
  '*PaymentsTest'`. With `setUpdate(true)` the requests reach the network and the HAR is written when the
  context closes — which `BaseTest` does after the test. Commit it in a dedicated PR; never update in CI.
- `setUpdateContent(RouteFromHarUpdateContentPolicy.ATTACH)` stores bodies as separate files (reviewable
  diffs); `setUpdateMode(HarMode.MINIMAL)` keeps only what replay needs. The **recording** options —
  `tracing().startHar(path, options)` [1.60] per test, or `setRecordHarPath(...)` in the class's
  `contextOptions()` — are evidence, owned by `qa/java/skills/evidence-capture` §5.
- Scrub tokens, cookies and personal data from a committed HAR; record against disposable test accounts.

## 8. Offline, and a request held in flight

```java
@Test
public void Should_ShowOfflineBanner_When_NetworkDrops() {
    ordersPage.open();

    mockApi.goOffline();
    ordersPage.refresh();

    assertThat(ordersPage.offlineBanner()).hasText("You are offline");
}

@Test
public void Should_KeepSpinnerVisible_When_OrdersAreStillInFlight() {
    mockApi.holdOrders();

    ordersPage.navigate();

    assertThat(ordersPage.spinner()).isVisible();
}
```

- **Holding is how Java simulates a slow response.** The handler stores the `Route` and returns without
  fulfilling it; playwright-java's router (`Router.java`, v1.63.0) treats that as a pending handler, so the
  request waits until something calls `resume()`, `fulfill()` or `abort()` on it. The loading state is then
  observable for as long as the test needs, with no timing in the test at all.
- A test that goes on past the loading state releases the request: `MockApi.HeldRequests orders =
  mockApi.holdOrders();` … `orders.release();` then asserts the list. A held request that is never released
  ends with the context, which `BaseTest` closes after the test.
- **Never `Thread.sleep` in a handler.** Java runs a route handler on the thread that is inside a
  Playwright call, the same thread that dispatches every other event of that Playwright instance — the
  sleep freezes them all, not one request, and the review treats it as a blocker.
- **Real bandwidth and latency** — a page that must load *slowly* rather than *not yet* — is CDP's
  `Network.emulateNetworkConditions`, Chromium-only, in `references/cdp.md`.
- **A delay the client must time out on** (a request that answers after the app's 10-second timeout)
  belongs to the server: a test endpoint or a stub server that delays on purpose.

## Rules

### Matching

- A URL matcher is a **glob** (`*` matches any character except `/`; `**` spans `/`; `{a,b}` alternates), a
  `java.util.regex.Pattern`, or a `Predicate<String>`.
- **Glob `?` and `[]` are not supported since Playwright 1.52** — use a `Pattern` for a single-character
  wildcard or a character class.
- **The base URL gotcha:** a string that does not start with `*` is resolved against the context's base URL;
  one that starts with `*` / `**` is a raw glob. Write `"**/api/orders"`, not `"/api/orders"` expecting a glob.

### Handlers

- A handler calls **exactly one** of `fulfill`, `abort`, `resume`, `fallback` — now, or later on a held
  route. None, and the request waits forever; two, and the second throws.
- Handlers run **last registered first**. `fallback()` defers to the next matching handler; `resume()` goes
  straight to the network and skips them.
- A handler runs on the Playwright dispatch thread: no `Thread.sleep`, no blocking wait, no latch.
- Serve large payloads from a fixture file with `setPath(Path.of("src/test/resources/responses/orders.json"))`.

### Scope

- `page.route` covers that page only. A popup is a new page, so a mock it needs is
  `page.context().route(...)`. `BaseTest` gives each test a fresh context, so a context route cannot leak into
  the next test.
- A service worker can answer before a route does: `setServiceWorkers(ServiceWorkerPolicy.BLOCK)` in the
  class's `contextOptions()` when mocks are bypassed.
- A route sees only the first request of a redirect chain — assert on the final response.

### Assertions and waits

- `page.waitForRequest(matcher, action)` / `page.waitForResponse(matcher, action)` in a page object — the
  action runs inside the wait. Never a listener registered after the click.
- "Not called" reads `page.requests()` after a user-visible completion signal.
- Non-locator values — a method, a parsed body, a header set — are AssertJ with `.as(...)`, one expected
  value each.

## What NOT to do

- No `Thread.sleep` in a route handler or a test — hold the request, throttle with CDP, or delay the server.
- No `page.route(...)` in a `@Test` method — a `MockApi` method with an intent name.
- No `mockApi` used without being built in `@BeforeMethod`.
- No `route.continue()` — the Java method is `route.resume()`.
- No glob `?` or `[abc]` — a `Pattern`.
- No `"/api/orders"` string expecting glob behaviour.
- No giant inline JSON literal — a record through Gson, or a fixture file.
- No `setUpdate(true)` left on in CI; no `HarNotFound.FALLBACK` on a replay meant to be hermetic.
- No security-header or TLS audit through CDP — `allHeaders()` and `securityDetails()` cover it.
- No secrets in a mock or a committed HAR.

## Generation steps

1. Confirm the **traffic**, the **intent** and the **scope**.
2. Add one intent-named method per scenario to `MockApi`; read requests through `Traffic` or a page-object
   method that wraps `waitForRequest` / `waitForResponse`.
3. Build both helpers and the page objects in the test class's `@BeforeMethod(alwaysRun = true)`.
4. For a third party, replay a committed HAR with `HarNotFound.ABORT`; update it with `HAR_UPDATE=1`, locally.
5. For loading and offline states, hold the request or go offline — never a sleep.
6. Read a failure's trace (`qa/java/skills/evidence-capture`): its Network tab shows which requests were
   routed and which reached the network.

## Cross-references

- `references/cdp.md` — real throttling, cache disable, CPU throttling, metrics (Chromium only).
- `references/proxy.md` — a client with no Playwright `Page`.
- `qa/java/skills/ui-test-author/playwright` — `BaseTest`, page objects, `references/assertions.md` §7.
- `qa/java/skills/evidence-capture` — HAR recording, traces.
- `qa/java/skills/realtime-stream-testing` — WebSocket and SSE.
- `qa/java/skills/test-data-builder` — builders for the payloads the mocks serve.
- `qa/cicd/java/skills/ci-pipelines` — the UI job and its artifact upload.
- `qa-network-mocking-typescript`, `qa-network-mocking-dotnet` — the sibling lanes.
