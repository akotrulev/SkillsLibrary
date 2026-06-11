---
name: qa-api-mocking-java
description: Use when tests must stub or mock an HTTP dependency the SUT calls — WireMock, MSW, Prism (OpenAPI-driven), or Mountebank (multi-protocol). Triggers: "stub the third-party API", "force the payment provider to return 500", "mock the downstream service in integration tests". Pick the mock server in the decision matrix, then read its reference file.
---

# QA — API Mocking (Java 21)

One registered skill, 4 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/wiremock.md` | HTTP stub server with request journal, scenarios (state machine), fault injection |
| `references/msw.md` | TypeScript-native handlers; sidecar pattern when the SUT isn't TS |
| `references/prism.md` | OpenAPI-spec-driven mock + contract-validation proxy — spec is the source of truth |
| `references/mountebank.md` | Multi-protocol imposters (HTTP/TCP/SMTP) when the dependency isn't plain HTTP |

## Decision matrix — pick the tool

| Need | Use | Why |
|------|-----|-----|
| A **standalone HTTP server** that fakes a downstream dependency; rich request matching + stateful scenarios + `verify`; first-class in **every** stack | **`references/wiremock.md`** | JVM-born, full-featured stub server; mature clients in Java / .NET / Node |
| Intercept **browser** requests inside a Playwright test, no separate server | `qa-network-monitoring-java` | `page.route` lives in the browser; no server to point at |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-java` | Proxy sits on the wire to the *real* service; WireMock replaces it |
| Mock `fetch`/XHR in a **browser or Node** app via the Service Worker / request layer | MSW (`references/msw.md`) | Request-interception in the app's own runtime, not a separate server |
| **Protocol-agnostic** over-the-wire imposters (TCP/HTTP/SMTP), language-neutral | Mountebank | Multi-protocol; heavier than an HTTP-only stub server |
| Mock derived **from an OpenAPI spec** automatically | Prism | Spec-driven; the contract *is* the mock |

**Rule of thumb:** *Need a fake HTTP dependency you fully control and assert against, from any stack?*
→ WireMock. *Need to touch a real browser's or real service's traffic?* → the network-monitoring family.
*Spec-first or browser-runtime mocking?* → Prism / MSW.

## Shared rules (every tool in this family)

- Mock only external/third-party dependencies — never the SUT itself.
- Every stub is verified: assert the SUT actually called it (journal/verification API).
- Reset stub state between tests; tests stay independent.
- Prefer spec-driven stubs (Prism / OpenAPI importers) where a contract exists.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
