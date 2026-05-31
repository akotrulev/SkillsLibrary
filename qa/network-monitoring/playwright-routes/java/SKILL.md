---
name: qa-network-monitoring-playwright-routes-java
description: Use when the user asks to intercept, mock, assert, or shape HTTP traffic in Playwright Java tests — `Page.route` / `BrowserContext.route` handlers (`route.fulfill` / `abort` / `resume` / `fallback` / `fetch`), request assertions (was endpoint X called, with what method/payload/headers) via `page.waitForRequest` / `page.waitForResponse`, stubbing JSON responses and error codes, modify-in-flight, HAR record-then-replay (`setRecordHar*` + `routeFromHAR`), offline mode (`setOffline`), and latency/network-condition simulation. Triggers: "mock the /api/orders response in our Playwright Java test", "assert the checkout endpoint was called with this payload in Java", "stub a 500 from the payments API in Playwright TestNG", "record a HAR and replay it offline", "intercept network requests in Playwright Java". Do NOT use for Playwright TypeScript network interception (use `qa/network-monitoring/playwright-routes/typescript`), Playwright .NET (use `qa/network-monitoring/playwright-routes/dotnet`), raw CDP scripting (use `qa/network-monitoring/cdp`), writing the page objects / tests themselves (use `qa/ui-test-author/playwright/java`), or API-only contract tests with no browser (use `qa/api-test-author/generator/java`).
---

# QA — Playwright Network Monitoring & Interception (Java)

Intercepts, mocks, asserts, and shapes HTTP traffic in Playwright `com.microsoft.playwright` (sync API) + TestNG tests on Java 21. Built on the **base-test class** model from `qa/ui-test-author/playwright/java`: route handlers and request-assertion helpers are wrapped in intent-revealing helper classes exposed through `BaseTest`, never raw `page.route(...)` calls scattered across `@Test` methods. Every wait is conditional on a request/response predicate; there is **no `page.waitForTimeout`** as a wait anywhere in this skill.

This is the **Java port of the canonical** `qa/network-monitoring/playwright-routes/typescript` — same patterns (mock / assert / modify-in-flight / HAR / offline / latency), re-expressed in the `com.microsoft.playwright` sync idioms. Two binding differences drive most of the porting: Java uses **`route.resume()`** (not `continue()`, a reserved word), and Java's `Route`/`Request`/`Response` have **no JSON helpers** (`setJson`/`postDataJSON`/`json()`) — you parse with Jackson/Gson.

## Stack

- Java 21 + Gradle (Kotlin DSL)
- TestNG 7.x + `com.microsoft.playwright:playwright` (sync API, Playwright ≥ 1.49)
- AssertJ for non-locator assertions; Jackson (`com.fasterxml.jackson`) for JSON payload parsing
- Network helpers under `src/test/java/<pkg>/support/network/`, HAR archives under `src/test/resources/har/`
- Page objects under `src/test/java/<pkg>/pages/`, tests under `src/test/java/<pkg>/tests/` (see the UI sibling)
- These tests run sharded in CI under `qa/ci-pipelines/github-actions/java`

## When to use

- Mocking a backend or third-party response so a UI test is deterministic (stub JSON, force a `500`/`403`)
- **Asserting** an endpoint was (or was not) called, with the expected method / payload / headers
- Modifying a real response in flight (inject a flag, corrupt one field) to exercise an edge case
- Recording a HAR of a flaky third-party dependency, then replaying it offline for determinism
- Simulating offline / slow-network conditions to test loading and error states
- Blocking noisy resources (analytics, fonts, images) to speed up or stabilize a suite

## When NOT to use

- Playwright TypeScript / .NET interception → `qa/network-monitoring/playwright-routes/{typescript,dotnet}`
- Low-level CDP (`Network.*`, real bandwidth throttling, protocol tracing) → `qa/network-monitoring/cdp`
- An HTTP proxy in front of the browser (mitmproxy, system-level capture) → `qa/network-monitoring/proxy`
- Writing the page objects / tests themselves → `qa/ui-test-author/playwright/java`
- Pure API contract/integration tests with no browser → `qa/api-test-author/generator/java`

## Inputs needed

Ask at most 3 questions; infer the rest from the test project and existing tests.

1. **What traffic** — exact endpoint(s) or URL glob/regex (`**/api/orders/**`), and is it first-party or a third-party dependency?
2. **Intent** — mock a response, assert a call happened, modify in flight, replay a HAR, or simulate offline/latency?
3. **Scope** — one page (`page.route`) or every page in the context including popups (`context.route`)?

## Decision matrix

| Goal | Tool | Notes |
|---|---|---|
| Return canned data, never hit the network | `route.fulfill(new FulfillOptions().setContentType("application/json").setBody(json))` | Java has **no `setJson`** — set content type + body |
| Force an error status | `route.fulfill(new FulfillOptions().setStatus(500).setContentType("application/json").setBody(...))` | The app's error path is now deterministic |
| Block a resource (analytics, images) | `route.abort()` | `route.abort("blockedbyclient")` to be explicit |
| Let it through unchanged | `route.resume()` | **`resume`, not `continue`**; goes to network, **skips** remaining handlers |
| Let an **earlier-registered** handler also run | `route.fallback()` | Chains to the next matching handler instead of the network |
| Modify a real response | `route.fetch()` → parse `text()` → mutate → `route.fulfill(setResponse(r).setBody(...))` | Preserves original status/headers unless overridden |
| Tweak the outgoing request | `route.resume(new ResumeOptions().setHeaders(...).setPostData(...))` | Header tampering, payload rewrite |
| Assert a call happened | `page.waitForRequest(url, Runnable)` / `page.waitForResponse(pred, Runnable)` | The `Runnable` runs inside the wait — the API shape removes the listener-ordering pitfall |
| Deterministic third-party dep | `page.routeFromHAR(har, new RouteFromHAROptions().setUrl(...).setNotFound(HarNotFound.ABORT))` | Record once with `setUpdate(true)`, commit, replay |
| Whole-context offline | `context.setOffline(true)` | Cross-browser |
| Latency simulation | `Thread.sleep(ms)` inside the handler, then `route.resume()` | Sync API has no async delay; no built-in `route` throttle; real bandwidth = CDP (Chromium-only) → `qa/network-monitoring/cdp` |

## Patterns

### Route-mocking helper — `support/network/MockApi.java`

Wrap interception in a helper with intent-revealing methods. Tests call `mockApi.stubOrders(...)`, not `page.route("**/api/orders", ...)`.

```java
package com.example.support.network;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Route;

import java.util.List;
import java.util.regex.Pattern;

public final class MockApi {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private final Page page;

    public MockApi(Page page) {
        this.page = page;
    }

    /** Serve canned orders; the real backend is never hit. */
    public void stubOrders(List<?> orders) {
        page.route("**/api/orders", route -> route.fulfill(new Route.FulfillOptions()
                .setContentType("application/json")
                .setBody(writeJson(orders))));
    }

    /** Force the orders endpoint to fail so the UI's error path runs. */
    public void failOrdersWith(int status) {
        page.route("**/api/orders", route -> route.fulfill(new Route.FulfillOptions()
                .setStatus(status)
                .setContentType("application/json")
                .setBody("{\"error\":\"simulated failure\"}")));
    }

    /** Drop noisy third-party traffic to stabilize and speed up the run. */
    public void blockAnalytics() {
        page.route(Pattern.compile("google-analytics\\.com|segment\\.io"),
                route -> route.abort("blockedbyclient"));
    }

    private static String writeJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalStateException("failed to serialize mock body", e);
        }
    }
}
```

Expose it on `BaseTest` so tests get `mockApi` ready (mirrors how the UI sibling wires page objects):

```java
public abstract class NetworkBaseTest extends BaseTest {
    protected MockApi mockApi;

    @BeforeMethod(alwaysRun = true, dependsOnMethods = "createContext")
    public void initNetwork() {
        mockApi = new MockApi(page);
    }
}
```

```java
// tests/OrdersTest.java
public class OrdersTest extends NetworkBaseTest {

    @Test
    public void rendersEmptyStateWhenThereAreNoOrders() {
        mockApi.stubOrders(List.of());
        page.navigate("/orders");

        assertThat(page.getByTestId("orders-empty")).isVisible();
    }

    @Test
    public void showsErrorBannerWhenOrdersApiFails() {
        mockApi.failOrdersWith(500);
        page.navigate("/orders");

        assertThat(page.getByRole(AriaRole.ALERT))
                .containsText(Pattern.compile("couldn’t load orders", Pattern.CASE_INSENSITIVE));
    }
}
```

Register routes **before** the navigation/action that triggers them — a route registered after the request has fired won't catch it.

### Request-assertion helper — fail fast on a missing/mismatched call

`page.waitForRequest(url, Runnable)` runs the `Runnable` **inside** the wait — the API shape arms the listener before the action runs, so the listener-before-action ordering pitfall (a footgun in the TS sibling) cannot happen here.

```java
package com.example.support.network;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Request;

import java.util.function.Predicate;

import static org.assertj.core.api.Assertions.assertThat;

public final class RequestAssertions {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private RequestAssertions() {}

    /**
     * Assert a request matching {@code urlGlob} fires while {@code action} runs,
     * optionally matching method and JSON payload. Fails fast on timeout.
     */
    public static Request expectRequest(Page page, String urlGlob, Runnable action,
                                        String method, Predicate<JsonNode> bodyMatches) {
        Request request = page.waitForRequest(urlGlob, action);

        if (method != null) {
            assertThat(request.method()).as("request method").isEqualTo(method);
        }
        if (bodyMatches != null) {
            JsonNode body = parse(request.postData());
            assertThat(bodyMatches.test(body)).as("request payload").isTrue();
        }
        return request;
    }

    private static JsonNode parse(String postData) {
        try {
            return MAPPER.readTree(postData);
        } catch (Exception e) {
            throw new IllegalStateException("request had no JSON body", e);
        }
    }
}
```

```java
@Test
public void submitsTheCheckoutWithTheCartTotal() {
    page.navigate("/cart");

    RequestAssertions.expectRequest(
            page,
            "**/api/checkout",
            () -> page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Place order")).click(),
            "POST",
            body -> body.get("totalMinor").asInt() == 15_000
                 && "EUR".equals(body.get("currency").asText()));
}
```

Java's `Request` has **no `postDataJSON()`** — parse `request.postData()` with Jackson. For a plain "was it called", `page.waitForResponse("**/api/checkout", action)` is enough.

### Asserting an endpoint was **not** called

There is no negative wait. Collect matching requests over the window of the action via `page.onRequest`, then assert the list is empty.

```java
@Test
public void doesNotCallTheLegacyPricingEndpoint() {
    List<String> calls = new ArrayList<>();
    page.onRequest(req -> {
        if (req.url().contains("/api/legacy-pricing")) calls.add(req.url());
    });

    page.navigate("/cart");
    page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Recalculate")).click();
    assertThat(page.getByTestId("cart-total")).isVisible(); // real signal the flow finished

    org.assertj.core.api.Assertions.assertThat(calls).as("legacy pricing should be retired").isEmpty();
}
```

Gate the assertion on a **user-visible signal** that the flow completed (`isVisible()` on the result), never on a fixed sleep — otherwise the negative check passes simply because the request hadn't fired yet.

### Modify a real response in flight

Fetch the live response, mutate the body, re-serve. Passing the original `response` keeps its status and headers; Jackson's `ObjectNode` gives a mutable tree.

```java
page.route("**/api/feature-flags", route -> {
    APIResponse response = route.fetch();
    try {
        ObjectNode flags = (ObjectNode) MAPPER.readTree(response.text());
        flags.put("betaCheckout", true);                 // force the variant under test
        route.fulfill(new Route.FulfillOptions()
                .setResponse(response)
                .setBody(MAPPER.writeValueAsString(flags)));
    } catch (Exception e) {
        throw new IllegalStateException("failed to rewrite feature-flags body", e);
    }
});
```

### Header / payload tampering on the outbound request

```java
page.route("**/api/**", route -> {
    Map<String, String> headers = new HashMap<>(route.request().headers());
    headers.put("x-test-tenant", "tenant-42");
    route.resume(new Route.ResumeOptions().setHeaders(headers));
});
```

### HAR record-then-replay for deterministic third-party deps

Record once against the live dependency, commit the archive, then replay offline on every run. Use `HarContentPolicy.ATTACH` so bodies live as separate files (reviewable diffs).

```java
// One-off recording run — setUpdate(true), then commit src/test/resources/har/payments.har
page.routeFromHAR(Path.of("src/test/resources/har/payments.har"), new Page.RouteFromHAROptions()
        .setUrl("**/api.stripe.com/**")
        .setUpdate(true)
        .setUpdateMode(HarMode.MINIMAL)
        .setUpdateContent(RouteFromHarUpdateContentPolicy.ATTACH));
```

```java
// Every CI run — replay. NotFound.ABORT makes any un-recorded call a hard failure
// (so a new dependency can't silently slip through to the real network).
@BeforeMethod(alwaysRun = true, dependsOnMethods = "createContext")
public void replayPaymentsHar() {
    page.routeFromHAR(Path.of("src/test/resources/har/payments.har"), new Page.RouteFromHAROptions()
            .setUrl("**/api.stripe.com/**")
            .setNotFound(HarNotFound.ABORT));
}
```

`new Browser.NewContextOptions().setRecordHarPath(...)` on the context captures the **whole** context's traffic for debugging; `routeFromHAR` is the scoped record/replay you want for a specific dependency.

### Offline and latency simulation

```java
@Test
public void showsTheOfflineBannerWhenTheNetworkDrops() {
    page.navigate("/dashboard");
    assertThat(page.getByTestId("live-feed")).isVisible();

    context.setOffline(true);
    page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Refresh")).click();

    assertThat(page.getByRole(AriaRole.ALERT))
            .containsText(Pattern.compile("you’re offline", Pattern.CASE_INSENSITIVE));
}
```

Latency injection has **no built-in `route` throttle**, and the sync handler has no async delay — `Thread.sleep` inside the handler is the documented idiom. This is the one sanctioned `Thread.sleep` in this skill: it is a *simulated fault-injection delay inside an interception handler*, **not** a test-body wait (which the global rules forbid). It belongs in a helper, not a test:

```java
static void withLatency(Page page, String urlGlob, long ms) {
    page.route(urlGlob, route -> {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        route.resume();
    });
}

// Test the loading spinner stays up while /api/orders is slow.
withLatency(page, "**/api/orders", 1_500);
page.navigate("/orders");
assertThat(page.getByTestId("orders-spinner")).isVisible();
```

For real bandwidth/latency emulation (not just per-request delay) use CDP `Network.emulateNetworkConditions` — Chromium-only — covered in `qa/network-monitoring/cdp`.

## Rules

### Matching
- URL patterns are a **glob** (`*` = any char except `/`; `**` spans `/`; `{a,b}` alternation), a **`Pattern`**, or a `Predicate<String>`. Prefer a glob for path shape, a `Pattern` for ids/query specifics.
- **Glob `?` and `[]` (character classes) are not supported** since Playwright 1.43 — use a `Pattern` for those.
- **`baseURL` gotcha:** a string pattern that does **not** start with `*` is resolved against the context base URL; a pattern starting with `*`/`**` is treated as a raw glob and is **not** joined to it. Don't write `"/api/orders"` expecting a glob — write `"**/api/orders"`.

### Handler discipline
- A route handler **must call exactly one** of `fulfill` / `abort` / `resume` / `fallback`. Calling none hangs the request; calling two throws.
- **Java uses `route.resume()`, not `continue()`** (`continue` is a reserved word). Continuation options ride on `Route.ResumeOptions`.
- **Handlers run last-registered-first.** The most recent `page.route(...)` wins; use `route.fallback()` to defer to an earlier handler. `route.resume()` goes straight to the network and **skips** the remaining handlers.
- Java's `Route.FulfillOptions` has **no `setJson`** — `setContentType("application/json").setBody(json)`; byte bodies use the separate `setBodyBytes(byte[])`.
- Serve large mock payloads from a file via `route.fulfill(new FulfillOptions().setPath(Path.of("src/test/resources/responses/orders.json")))`, not a giant inline literal.

### Scope
- `page.route` for one page (handles its popups); `context.route` for **every** page in the context. Page-level routes take precedence over context-level for the same request.
- Mock at the **narrowest** scope that works — context routes that leak across tests are a common source of cross-test contamination. `BaseTest` gives a fresh context per `@BeforeMethod`, so prefer `page.route`.

### Assertions & waits
- Use `page.waitForRequest(url, Runnable)` / `page.waitForResponse(pred, Runnable)` — the `Runnable` runs **inside** the wait, so the listener is always armed before the action. Never wire a manual `onResponse` listener *after* the click.
- Use **predicates** to assert method/status/url together: `r -> r.url().contains("/api/x") && r.status() == 200`.
- Read payloads with `request.postData()` (parse with Jackson — there is no `postDataJSON()`) / `request.headers()`, and `response.text()` (parse — there is no `json()`) / `response.status()`.
- **Negative assertions** ("endpoint not called") collect from `page.onRequest` and assert the list `isEmpty()` **after** a user-visible completion signal — never after a sleep.
- **No `page.waitForTimeout(ms)` as a wait.** The only `Thread.sleep` allowed is inside a latency-injection route handler, and only there.

### HAR
- Record with `setUpdate(true)` once, commit, then replay with no update. Re-record in a dedicated PR, never silently in CI.
- Use `RouteFromHarUpdateContentPolicy.ATTACH` (bodies as files) for reviewable diffs; `HarMode.MINIMAL` unless you need timings.
- Set `setNotFound(HarNotFound.ABORT)` on replay so an un-recorded request is a hard failure, not a silent hit to the real third party.

### Determinism & hygiene
- If `page.route` mocks are being bypassed, set `new Browser.NewContextOptions().setServiceWorkers(ServiceWorkerPolicy.BLOCK)` — a Service Worker can intercept before your route does.
- A route handler is only invoked for the **first** URL of a redirect chain — assert on the final response, not the 30x hop.
- Never put real secrets/tokens in committed mock responses or HAR files — scrub auth headers (use `setRecordHarContent(HarContentPolicy.OMIT)` or a redaction step).

### What NOT to do
- No `page.waitForTimeout(ms)` to "wait for the request" — use `waitForRequest`/`waitForResponse` with a predicate.
- No raw `page.route("**/api/...", ...)` scattered through `@Test` methods — wrap it in a `MockApi`-style helper with an intent name.
- No handler that calls neither `fulfill`/`abort`/`resume`/`fallback` (hangs) or two of them (throws).
- No `route.resume()` when you meant `route.fallback()` — `resume` skips your other handlers.
- No reaching for `route.continue()` — it does not exist in Java; the method is `route.resume()`.
- No `"/api/orders"` string pattern expecting glob behavior — it gets baseURL-resolved; write `"**/api/orders"`.
- No glob `?`/`[abc]` since 1.43 — switch to a `Pattern`.
- No giant inline JSON literal as a mock — `route.fulfill(... setPath(...))` from a fixture file.
- No silent HAR re-record in CI (`setUpdate(true)` left on) — recordings drift and tests stop testing anything.
- No `HarNotFound.FALLBACK` on a third-party HAR replay you intend to be hermetic — it lets un-recorded calls hit the live service.
- No secrets/PII committed inside a mock response or HAR archive.
- No `context.route` for something one page needs — it leaks the mock into every page in the context.
- No asserting "not called" after a fixed sleep — gate on a user-visible completion signal.
- No `Thread.sleep` anywhere except inside a latency-injection route handler — never as a test-body wait.

## Generation steps

1. Confirm **traffic** (endpoints + glob/regex), **intent** (mock / assert / modify / HAR / offline), and **scope** (page vs context).
2. Add or extend `support/network/MockApi.java` with one intent-named method per scenario (`stubOrders`, `failOrdersWith`, `blockAnalytics`). Expose it on `NetworkBaseTest` via `@BeforeMethod`.
3. For call assertions, use `RequestAssertions.expectRequest` (or a direct `page.waitForResponse` predicate); parse the payload from `postData()` with Jackson.
4. For third-party determinism, record a HAR with `setUpdate(true)`, commit it under `src/test/resources/har/` with `ATTACH` content, then replay with `setNotFound(HarNotFound.ABORT)`.
5. For offline/latency states, use `context.setOffline(true)` and a `Thread.sleep` latency helper inside a route handler — never `page.waitForTimeout`.
6. Run `./gradlew test`; verify with the trace viewer's Network tab (which requests were routed vs hit the network).

## Cross-references

- **`qa/network-monitoring/playwright-routes/typescript`** — the canonical skill this ports from; consult it for the conceptual model and the glob/Service-Worker notes.
- **`qa/network-monitoring/playwright-routes/dotnet`** — the sibling .NET port (`route.ContinueAsync`, `RouteFulfillOptions.Json`, `PostDataJSON`).
- **`qa/ui-test-author/playwright/java`** — the base-test / page-object model these network helpers layer on; `waitForResponse` ordering and the no-`waitForTimeout` discipline originate there.
- **`qa/network-monitoring/cdp`** — low-level CDP (`Network.emulateNetworkConditions` for real throttling) when `page.route` isn't enough.
- **`qa/network-monitoring/proxy`** — out-of-browser HTTP capture for multi-process or non-browser traffic.
- **`qa/ci-pipelines/github-actions/java`** — runs these tests sharded; HAR archives and traces are uploaded as artifacts there.
- **`qa/test-data-builder/java`** — builds the shapes you serialize into `route.fulfill(...setBody(...))`.
- **`qa/api-test-author/generator/java`** — when the test needs no browser, assert against the API directly.

## Sources synthesized (research-first per CLAUDE.md)

- [Playwright Java — Network](https://playwright.dev/java/docs/network) — `Page.route`, `abort`/`resume`/`fulfill`, `setOffline`, glob/regex/predicate matching.
- [Playwright Java — class Route](https://playwright.dev/java/docs/api/class-route) — `fulfill(FulfillOptions)` (`setStatus`/`setContentType`/`setBody`/`setPath`/`setResponse`; **no `setJson`**), `resume()` (not `continue`) vs `fallback()`, last-registered-first ordering, `fetch()` → `APIResponse`.
- [Playwright Java — class Page](https://playwright.dev/java/docs/api/class-page) — `waitForRequest(url, Runnable)`/`waitForResponse(pred, Runnable)`, `onRequest`/`onResponse`, `routeFromHAR(Path, RouteFromHAROptions{setUrl,setUpdate,setUpdateMode,setUpdateContent,setNotFound})`.
- [Playwright Java — class Request](https://playwright.dev/java/docs/api/class-request) / [class Response](https://playwright.dev/java/docs/api/class-response) — `postData()` (**no `postDataJSON`**), `headers()`/`method()`; `text()` (**no `json`**), `status()`/`ok()`.
- [Playwright Java — class Browser](https://playwright.dev/java/docs/api/class-browser) — `NewContextOptions.setRecordHar*` (`HarMode`, `HarContentPolicy`), `setServiceWorkers(ServiceWorkerPolicy.BLOCK)`.

## Changelog

- 2026-05-31: Authored as the **Java port** of the canonical `qa/network-monitoring/playwright-routes/typescript` (QA Skills Library Phase 1, `qa/GAP-ANALYSIS.md` row 8; closes the node — all 3 stacks). Mirrors the canonical section-for-section in the `com.microsoft.playwright` sync API: `MockApi` helper exposed via a `BaseTest` subclass, `RequestAssertions.expectRequest` using `waitForRequest(url, Runnable)` (Runnable-inside-wait removes the listener-ordering pitfall), negative-assertion via `page.onRequest` + completion signal, modify-in-flight via `fetch()` → Jackson `ObjectNode` mutate → `fulfill(setResponse, setBody)`, header tampering via `resume(ResumeOptions)`, HAR record (`setUpdate(true)`, `ATTACH`) → replay (`HarNotFound.ABORT`), `setOffline`, `Thread.sleep` latency handler (the only sanctioned sleep). Documents the binding-specific gotchas the .NET/TS siblings don't have: **`route.resume()` not `continue()`**, **no `setJson`/`postDataJSON()`/`json()`** (Jackson parsing throughout). Notes the 1.43+ glob change, baseURL resolution, last-registered-first order, and `ServiceWorkerPolicy.BLOCK`.
