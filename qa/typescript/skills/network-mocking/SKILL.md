---
name: network-mocking
description: Use when Playwright Test (TypeScript) UI tests must intercept, mock, throttle or assert browser network traffic, or a non-Playwright client needs a MITM proxy. Triggers "mock this XHR in the UI test", "replay a HAR", "simulate slow 3G or offline", "assert the page called endpoint X", "check the security headers". Do NOT use for API tests without a browser (qa-typescript:api-tests), load-level throttling (performance) or WebSocket/SSE streams (qa-typescript:realtime-stream-testing).
---

# QA — Network Mocking and Monitoring (TypeScript / Playwright 1.64)

One registered skill, three layers — reach for the highest one that can express the test. Identify the
layer, then **read the matching `references/<tool>.md` end to end before writing any code**. This file
routes and holds the rules every layer shares.

This skill pins nothing; `@playwright/test` is in the **Versions** table of
`qa/typescript/skills/ui-test-author/playwright/SKILL.md`.

## Layers in this family

| Read | Use when |
|---|---|
| `references/playwright-routes.md` | Mock, abort, modify or assert requests inside Playwright; HAR replay; offline; "not called" checks; security headers and TLS details. **The default** |
| `references/cdp.md` | Chromium DevTools Protocol — real bandwidth/latency throttling, HTTP-cache disable, CPU throttling, `Performance` metrics |
| `references/proxy.md` | An out-of-process MITM proxy for clients with no Playwright `page` — Selenium, Appium, a native HTTP client |

## Decision matrix

| Layer | What it does | Browsers |
|---|---|---|
| **Routing** — `page.route` / `context.route` (`references/playwright-routes.md`) | Fulfill, abort, continue, modify in flight; wait for or list requests (`page.requests()` [1.56]); console and page errors; HAR replay; `context.setOffline`; per-request delay; headers via `response.allHeaders()` and TLS via `response.securityDetails()` | Chromium, Firefox, WebKit |
| **DevTools Protocol** — `newCDPSession` (`references/cdp.md`) | Real throughput-based throttling, cache disable, CPU throttling, performance metrics | **Chromium only** |
| **External proxy** — `mockttp` (`references/proxy.md`) | Record, assert and fault-inject for any client that honours a proxy | Any client |

**Decision rule:** routing first — it is cross-browser and typed. Drop to CDP only for what routing cannot
express: real throttling, cache disable, CPU throttling, `Performance` metrics. CDP method names are strings
with no compile-time check, and the layer is Chromium-only. Use the proxy only when there is no `page`.

## Owned next door

- **WebSocket and SSE** — observing or mocking a stream (`routeWebSocket`, `framereceived`, `EventSource`) is
  `qa/typescript/skills/realtime-stream-testing`. `route.fulfill` delivers a whole body at once, so it cannot
  stand in for an SSE stream.
- **HAR recording** — `context.tracing.startHar()` [1.60] in a fixture, or `contextOptions.recordHar`, is
  `qa/typescript/skills/evidence-capture` (`references/playwright.md` §5). This skill replays and updates
  HARs with `routeFromHAR`.

## Shared rules (every layer)

- Intercept at the layer closest to the test runner — never a proxy where routes suffice.
- Register the route or the wait **before** the action that triggers the request.
- Assert traffic with waits on request/response predicates, or with a list read after a user-visible
  completion signal — never after a sleep.
- Interception lives in fixtures with intent names; a spec never calls `page.route`, `client.send` or a
  proxy API directly.
- Mock payloads are typed and come from builders or fixture files (`qa/typescript/skills/test-data-builder`),
  not inline blobs repeated across tests.
- Every handler promise is awaited or returned.

## Handoffs

- Page objects, fixtures and the canonical config → `qa/typescript/skills/ui-test-author/playwright`
- Streams → `qa/typescript/skills/realtime-stream-testing`; HAR recording → `qa/typescript/skills/evidence-capture`
- No browser at all → `qa/typescript/skills/api-test-author/writer`
- Java and .NET → `qa-java:network-mocking`, `qa-dotnet:network-mocking`
