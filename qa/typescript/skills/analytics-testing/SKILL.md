---
name: analytics-testing
description: Use when TS Playwright tests must assert analytics beacons, dataLayer or consent gating (GA4, pixels, Consent Mode v2, GPC). Triggers "test our GA4 events". Not for mocks (network-mocking).
---

# QA — Analytics, Tracking and Consent Testing (TypeScript / Playwright 1.64)

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

This skill pins nothing; `@playwright/test` is in the **Versions** table of
`qa/typescript/skills/ui-test-author/playwright/SKILL.md`.

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
| No tracking before a choice | `Tracker.hits()` after the banner is visible and a second page has loaded | `[]` |
| Tracking starts after *accept* | `Tracker.nextEvent('page_view', accept)` | `en`, `tid` = the test ID |
| Nothing after *reject* | the consent `update` in the `dataLayer`, then `Tracker.hits()` after the next page | `[]` |
| Consent Mode v2 default / update | `DataLayer.consentCommands()` | the `default` and `update` states, all four v2 types |
| Advanced mode sends cookieless pings | the hit's `gcs` | the value recorded from your own tag for denied / granted |
| An event and its parameters | `Tracker.nextEvent(name, action)` | `en` plus the parameters the tracking plan names |
| The `dataLayer` payload | `DataLayer.eventsNamed(name)` polled | the typed object from the tracking plan |
| GPC honoured | `PrivacySignals.sendGlobalPrivacyControl()`, then the hits | no ad pixel; ad consent types stay `denied` |

## Rules

- **Capture, then fulfil.** Every GA4 `/g/collect` and Meta Pixel `/tr` request is recorded and answered with
  `204` at the **context** level, so popups are covered and no hit reaches a real property. Never `abort` a beacon
  you assert on, and never let one through with `route.continue()`.
- **Assert the test property.** Every GA4 hit's `tid` equals the measurement ID the test environment is configured
  with (an env var). A hit to any other ID fails the test.
- **The wire format is observed, not published.** Google documents `gcs` and `gcd` as consent parameters but
  publishes no contract for `/g/collect` keys (`en`, `ep.*`, `epn.*`). Record one real hit from your own tag
  version, pin the keys your tests read, and re-record when the tag changes. The `dataLayer` is the documented
  interface: put payload detail there.
- **Absence needs a completion signal.** "No hit" is read after a user-visible signal **and** a following page
  load, never after a sleep and never straight after the click.
- **Consent tests start clean**: a fresh context with no consent cookie, and **without** the writer's auto
  `dismissConsent` fixture (`ui-test-author/playwright` `references/config-and-fixtures.md`) — it clicks the
  banner for you.
- Interception and `dataLayer` reads live in fixtures with intent names (`tracker`, `dataLayer`, `consentBanner`,
  `privacySignals`); a spec never calls `page.route` or `page.evaluate`.
- Expected payloads come from the tracking plan as typed builders (`test-data-builder`), never inline literals
  repeated across specs.

## Handoffs

- Fixtures, page objects, config → `qa/typescript/skills/ui-test-author/playwright`
- Routing details (`context.route`, `fulfill`, `page.requests()`) → `qa/typescript/skills/network-mocking`
- Payload builders → `qa/typescript/skills/test-data-builder`
- A tracking defect → `qa/manual/bug-report-writer`, with the captured hit attached
- Java and .NET → `qa-java:analytics-testing`, `qa-dotnet:analytics-testing`
