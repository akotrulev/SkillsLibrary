---
name: network-mocking
description: Use when .NET/NUnit UI tests must intercept, mock, hold, throttle or assert browser network traffic — Playwright routes, CDP throttling, or an out-of-browser MITM proxy for Selenium/Appium. Triggers "mock this XHR in the UI test", "simulate slow 3G/offline", "replay a HAR", "assert the page called X", "check the security headers". Do NOT use for API tests without a browser (qa-dotnet:api-tests), load (qa-dotnet:load-testing) or WebSocket/SSE streams (qa-dotnet:realtime-stream-testing).
---

# QA — Network Mocking (.NET 10 / Playwright 1.63)

One registered skill, three tools. Identify the layer the test needs, then **read the matching
`references/<tool>.md` end to end before writing any code**. This file routes and holds the rules every tool
shares. The Playwright pin is in the **Versions** table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md`.

## Tools in this family

| Read | Use when |
|---|---|
| `references/playwright-routes.md` | Mock, abort, modify, hold, assert, HAR replay, offline, security headers and TLS — inside a Playwright test. **The default** |
| `references/cdp.md` | Chrome DevTools Protocol — real bandwidth throttling, cache disable, CPU throttling, performance metrics. Chromium only |
| `references/proxy.md` | An out-of-process MITM proxy (`Titanium.Web.Proxy`) for clients with no Playwright `IPage` — Selenium, Appium, `HttpClient`, several processes |

## Decision matrix — pick the layer

| Layer | Tool | What it does | Browsers |
|---|---|---|---|
| **Request routing** | `Page.RouteAsync` / `Context.RouteAsync` → `references/playwright-routes.md` | Fulfill, abort, modify in flight, **hold a request and release it**, assert a call happened or did not (`Page.RequestsAsync()`), HAR replay, offline, `AllHeadersAsync()` and `SecurityDetailsAsync()` | Chromium, Firefox, WebKit |
| **DevTools Protocol** | `Context.NewCDPSessionAsync(Page)` → `references/cdp.md` | **Real** throughput and latency, HTTP-cache disable, CPU throttling, `Performance` metrics | Chromium only |
| **External MITM proxy** | `Titanium.Web.Proxy` → `references/proxy.md` | Capture and fault-inject for a client that is not Playwright | Any client that honours a proxy |

**Decision rule:** reach for routing first — it is cross-browser, typed and covers mocking, assertions,
offline, security headers and TLS. Drop to CDP only for what routing cannot express: real bandwidth, cache
disable, CPU throttling, performance metrics. CDP is stringly typed (`"Network.emulateNetworkConditions"`)
and Chromium-only. The proxy is for when there is no `IPage` at all.

## Shared rules (every tool)

- **Every Playwright sample derives from `Example.UiTests.Support.BaseTest`**, which owns the browser, a
  context and page per test, and the failure evidence. A class changes the context only by amending
  `base.ContextOptions()` (`ServiceWorkers`, `Offline`) — never `new()`, which drops `BaseURL` and the video
  folder — and never adds `Playwright.CreateAsync()`, a browser or a failure hook.
- Route, CDP and proxy calls live in a helper with intent names (`MockApi`, `Traffic`, `CdpControls`,
  `ProxyControls`) built in the class's own `[SetUp]`; a test never calls `Page.RouteAsync(...)` or
  `SendAsync(...)`, and reaches pages through page objects.
- **No `Task.Delay` in a route handler as a "slow response", and never `Thread.Sleep`.** Hold the request
  and release it (`references/playwright-routes.md` §8), use CDP throttling, or slow the server.
- Wait on request and response predicates or a page object's completion signal — never a sleep, never a
  listener registered after the action.
- Every assertion states one expected value and carries the evidence in its message — the payload, the
  header set, the URL list. Never a bare boolean.
- Mocked payloads come from records, builders or fixture files, not inline blobs repeated across tests.
- Recording a HAR as evidence (`Context.Tracing.StartHarAsync(...)` [1.60], `RecordHarPath`) is
  `qa/dotnet/skills/evidence-capture` §5; this skill replays one.

## Handoffs

- `BaseTest`, page objects, `Directory.Packages.props` → `qa/dotnet/skills/ui-test-author/playwright`
- HAR recording and other evidence → `qa/dotnet/skills/evidence-capture`
- WebSocket and SSE → `qa/dotnet/skills/realtime-stream-testing`
- API tests without a browser → `qa/dotnet/skills/api-test-author`
- Payload builders → `qa/dotnet/skills/test-data-builder`
- The CI job → `qa/cicd/dotnet/skills/ci-pipelines`
- TypeScript and Java → `qa-typescript:network-mocking`, `qa-java:network-mocking`
