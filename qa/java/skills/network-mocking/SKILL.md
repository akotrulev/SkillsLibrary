---
name: qa-network-mocking-java
description: Use when Java 21 / TestNG UI tests must intercept, mock, throttle, or assert browser network traffic — Playwright routes, raw CDP, or an out-of-browser MITM proxy. Triggers "mock this XHR in the UI test", "simulate slow 3G/offline", "capture a HAR", "assert the page called endpoint X". Do NOT use for direct API testing without a browser (use `qa-api-test-writer-java`), for load throttling (`qa-load-testing-java`), or for WebSocket/SSE streams (use `qa-realtime-stream-testing-java`).
---

# QA — Network Monitoring (Java 21)

One registered skill, 3 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/playwright-routes.md` | Intercept/mock/assert requests inside Playwright tests — the default; stay here when possible |
| `references/cdp.md` | Chrome DevTools Protocol — network throttling, offline mode, low-level events Playwright routes can't reach |
| `references/proxy.md` | Out-of-browser MITM proxy — HAR capture and interception for Selenium/Appium/non-CDP browsers |

## Decision matrix — pick the tool

| Layer | Tool | What it does | Browser support |
|---|---|---|---|
| **Request routing** (high level) | `page.route` → `references/playwright-routes.md` | Intercept/mock/abort/fulfill, assert it fired, modify in flight, HAR replay, **approximate** offline (`context.setOffline`), **per-request `Thread.sleep`** | All (Chromium/Firefox/WebKit) |
| **DevTools Protocol** (below routing) | `newCDPSession` → **`references/cdp.md`** | **Real** bandwidth+latency throttling, **HTTP-cache disable**, **CPU throttling**, security-header/`securityDetails` audit, `Performance` metrics | **Chromium-only** |
| **External MITM proxy** | mitmproxy / system proxy → `references/proxy.md` | Out-of-browser capture for multi-process or non-Playwright stacks | Any client through the proxy |

**Decision rule:** reach for `page.route` **first** — cross-browser, typed, covers mocking/asserting/offline. Drop to **CDP only when routing genuinely can't express the test**: real throughput-based throttling, cache-disable, CPU throttling, TLS/`securityDetails` inspection, or `Performance` metrics. CDP is more brittle — **stringly-typed** protocol method names (`"Network.emulateNetworkConditions"`), no compile-time check — and **Chromium-only**.

## Shared rules (every tool in this family)

- Intercept at the closest layer to the test runner — don't run a proxy when routes suffice.
- Assert traffic via explicit waits on request/response predicates — never sleeps or listener races.
- Mocked payloads come from fixtures/builders, not inline blobs duplicated across tests.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
