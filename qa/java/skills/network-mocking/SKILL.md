---
name: network-mocking
description: Use when Java/TestNG UI tests must intercept, mock, slow down or assert browser network traffic — Playwright routes, CDP throttling, or an out-of-browser MITM proxy for Selenium/Appium. Triggers "mock this XHR in the UI test", "simulate slow 3G/offline", "replay a HAR", "assert the page called endpoint X", "check the security headers". Do NOT use for API tests without a browser (qa-java:api-tests), load (qa-java:load-testing) or WebSocket/SSE streams (qa-java:realtime-stream-testing).
---

# QA — Network Mocking (Java / Playwright 1.63)

One registered skill, three tools. Identify the layer the test needs, then **read the matching
`references/<tool>.md` end to end before writing any code**. This file routes and holds the rules every tool
shares. The Playwright pin is in the **Versions** table of `qa/java/skills/ui-test-author/playwright/SKILL.md`.

## Tools in this family

| Read | Use when |
|---|---|
| `references/playwright-routes.md` | Mock, abort, modify, hold, assert, HAR replay, offline, security headers and TLS — inside a Playwright test. **The default** |
| `references/cdp.md` | Chrome DevTools Protocol — real bandwidth throttling, cache disable, CPU throttling, performance metrics. Chromium only |
| `references/proxy.md` | An out-of-process MITM proxy for clients with no Playwright `Page` — Selenium, Appium, several processes |

## Decision matrix — pick the layer

| Layer | Tool | What it does | Browsers |
|---|---|---|---|
| **Request routing** | `page.route` / `page.context().route` → `references/playwright-routes.md` | Fulfill, abort, modify in flight, **hold a request and release it**, assert a call happened or did not (`page.requests()` [1.56]), HAR replay, offline, `allHeaders()` and `securityDetails()` | Chromium, Firefox, WebKit |
| **DevTools Protocol** | `page.context().newCDPSession(page)` → `references/cdp.md` | **Real** throughput and latency, HTTP-cache disable, CPU throttling, `Performance` metrics | Chromium only |
| **External MITM proxy** | BrowserUp Proxy → `references/proxy.md` | Capture and fault-inject for a client that is not Playwright | Any client that honours a proxy |

**Decision rule:** reach for routing first — it is cross-browser, typed and covers mocking, assertions,
offline, security headers and TLS. Drop to CDP only for what routing cannot express: real bandwidth, cache
disable, CPU throttling, performance metrics. CDP is stringly typed (`"Network.emulateNetworkConditions"`)
and Chromium-only. The proxy is for when there is no `Page` at all.

## Shared rules (every tool)

- **Every Playwright sample extends `com.example.uitests.support.BaseTest`**, which owns Playwright, the
  browser, a context and page per test, and the failure evidence. A class changes the context only through
  `contextOptions()` (`setServiceWorkers`, `setRecordHarPath`, `setOffline`) and never adds its own
  `Playwright.create()`, browser or failure hook.
- Route, CDP and proxy calls live in a helper with intent names (`MockApi`, `Traffic`, `CdpControls`,
  `ProxyControls`) built in the class's own `@BeforeMethod`; a test never calls `page.route(...)` or
  `client.send(...)`.
- **No `Thread.sleep` in a route handler, ever.** Java runs route handlers on the thread that is inside a
  Playwright call, which also dispatches every other event of that Playwright instance — a sleep there stalls
  all of them, not one request. Hold the request and release it (`references/playwright-routes.md` §8), use
  CDP throttling, or slow the server.
- Wait on request and response predicates or a page object's completion signal — never a sleep or a
  listener registered after the action.
- Mocked payloads come from records, builders or fixture files, not inline blobs repeated across tests.
- Recording a HAR as evidence (`tracing().startHar(...)` [1.60], `setRecordHarPath`) is
  `qa/java/skills/evidence-capture` §5; this skill replays one.

## Handoffs

- `BaseTest`, page objects and the build → `qa/java/skills/ui-test-author/playwright`
- HAR recording and other evidence → `qa/java/skills/evidence-capture`
- WebSocket and SSE → `qa/java/skills/realtime-stream-testing`
- API tests without a browser → `qa/java/skills/api-test-author`
- The CI job → `qa/cicd/java/skills/ci-pipelines`
- TypeScript and .NET → `qa-typescript:network-mocking`, `qa-dotnet:network-mocking`
