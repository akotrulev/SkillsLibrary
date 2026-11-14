---
name: analytics-testing
description: Use when Java/TestNG Playwright tests must assert analytics beacons, dataLayer or consent gating (GA4, pixels, Consent Mode v2, GPC). Triggers "test our GA4 events". Not for mocks (network-mocking).
---

# QA — Analytics, Tracking and Consent Testing (Java / Playwright 1.63 + TestNG)

Tracking breaks silently: a refactor drops an event, a consent banner lets a pixel fire before the visitor chose,
a currency goes out as a string. Nothing on screen changes, so only a test that reads the **traffic** and the
**`dataLayer`** catches it. This skill tests three things, in this order of risk:

1. **Consent gating** — no tracking request before consent; the right requests after *accept*; none after
   *reject*; Google Consent Mode v2 defaults and updates; the Global Privacy Control signal honoured.
2. **The beacon** — the event left the browser to the right property with the right name and parameters
   (GA4 `/g/collect`, the Meta Pixel `/tr`).
3. **The `dataLayer` push** — the page handed the tag manager the event and its typed payload.

**Never send a real hit to a production analytics property.** Every collect request is captured and answered by
the test (`route.fulfill` with `204`), so nothing reaches Google or Meta, and every GA4 hit is asserted to carry
the **test** measurement ID. Read **`references/playwright.md`** end to end before writing code.

The Playwright pin is in the **Versions** table of `qa/java/skills/ui-test-author/playwright/SKILL.md`; every
sample extends `com.example.uitests.support.BaseTest`.

## When to use

- A tracking plan names events and parameters, and a change must not drop or alter them
- A consent banner, a consent-management platform or Google Consent Mode v2 must gate tags
- The site must honour `Sec-GPC: 1` / `navigator.globalPrivacyControl`
- A suite must stop leaking hits into a production property

## When NOT to use

- Mocking an application API or asserting a first-party call → `network-mocking`
- Blocking analytics only to stabilise an unrelated suite → `network-mocking` (`MockApi.blockAnalytics`)
- Server-side tagging or the Measurement Protocol called from the backend → `api-test-author`
- The consent banner's accessibility → `accessibility-testing`

## Decision matrix

| To prove | Read | Assert |
|---|---|---|
| No tracking before a choice | `Tracker.hits()` after the banner is visible and a second page has loaded | empty |
| Tracking starts after *accept* | `Tracker.nextEvent("page_view", accept)` | `en`, `tid` = the test ID |
| Nothing after *reject* | `DataLayer.consentState("update")`, then `Tracker.hits()` after the next page | empty |
| Consent Mode v2 default / update | `DataLayer.consentState("default" / "update")` | all four v2 types |
| Advanced mode sends cookieless pings | the hit's `gcs` | the value recorded from your own tag for denied / granted |
| An event and its parameters | `Tracker.nextEvent(name, action)` | `en` plus the parameters the tracking plan names |
| The `dataLayer` payload | `DataLayer.eventsNamed(name, type)` | the record from the tracking plan |
| GPC honoured | `PrivacySignals.sendGlobalPrivacyControl()`, then the hits | no ad pixel; ad consent types stay `denied` |

## Rules

- **Capture, then fulfil.** Every GA4 `/g/collect` and Meta Pixel `/tr` request is recorded and answered with
  `204` through `page.context().route`, so popups are covered and no hit reaches a real property. Never `abort`
  a beacon you assert on, and never `resume` one.
- **Assert the test property.** Every GA4 hit's `tid` equals the measurement ID the test environment is configured
  with (`requiredEnv("GA4_TEST_MEASUREMENT_ID")`).
- **The wire format is observed, not published.** Google documents `gcs` and `gcd` as consent parameters but
  publishes no contract for `/g/collect` keys (`en`, `ep.*`, `epn.*`). Record one real hit from your own tag
  version, pin the keys your tests read, and re-record when the tag changes. The `dataLayer` is the documented
  interface: put payload detail there.
- **Absence needs a completion signal.** "No hit" is read after a user-visible signal **and** a following page
  load, never after a `Thread.sleep` and never straight after the click.
- **Consent tests start clean**: `BaseTest` opens a fresh context per test; a consent test class never loads a
  saved storage state that holds a consent cookie.
- Route, `dataLayer` and privacy-signal calls live in helpers with intent names (`Tracker`, `DataLayer`,
  `PrivacySignals`) built in the class's `@BeforeMethod`; a test never calls `page.route` or `page.evaluate`.
- Expected payloads are records from the tracking plan; one with four or more fields gets a builder
  (`test-data-builder`).

## Handoffs

- `BaseTest`, page objects, Gradle → `qa/java/skills/ui-test-author/playwright`
- Routing details (`route`, `fulfill`, `page.requests()`) → `qa/java/skills/network-mocking`
- Payload builders → `qa/java/skills/test-data-builder`
- A tracking defect → `qa/manual/bug-report-writer`, with the captured hit attached
- TypeScript and .NET → `qa-typescript:analytics-testing`, `qa-dotnet:analytics-testing`
