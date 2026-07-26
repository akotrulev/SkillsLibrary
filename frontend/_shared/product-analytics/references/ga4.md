# GA4 (Google Analytics 4) — reference

Free, ubiquitous, and the right answer to **acquisition** questions — which channel, campaign, and keyword brought the user, and what did the ad spend return. It integrates with Google Ads and Search Console in a way nothing else does, and that integration is the entire reason to pick it.

It is a **weak product-analytics tool**, and this file will keep saying so. Custom events are second-class citizens, cardinality limits silently corrupt reports, and there is no session replay or heatmap. Per [`SKILL.md`](../SKILL.md)'s decision matrix, the common correct configuration is **GA4 for acquisition alongside a product tool** — that is the one two-tool setup worth running.

Everything in `SKILL.md`'s **Cross-cutting rules** still applies. GA4 fights several of them, and the workarounds are below.

**Versions.** GA4 is evergreen — no SDK major to pin, but the *consent* surface changes on Google's schedule and has hard compliance dates. Use `@next/third-parties/google` on Next.js rather than hand-rolling the `gtag` snippet.

## Setup — Next.js App Router

```bash
pnpm add @next/third-parties
```

```tsx
// app/layout.tsx
import { GoogleAnalytics } from '@next/third-parties/google';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
      <GoogleAnalytics gaId={process.env.NEXT_PUBLIC_GA_ID!} />
    </html>
  );
}
```

This loads the tag `afterInteractive` (the deferred posture `SKILL.md` Rule 8 requires). **Load it only after consent** — see the Consent Mode section, which is not optional in the EEA.

### Pageviews on client navigation

GA4's *enhanced measurement* has a "page changes based on browser history events" toggle that catches many SPA navigations automatically. Do not assume it is correct — it is the single most common source of wrong GA4 numbers in an App Router app, producing **either** misses (the History API pattern isn't detected) **or** duplicates (the toggle fires *and* you send a manual `page_view`).

Pick one owner, explicitly:

- **Option A (preferred): disable** the enhanced-measurement page-change toggle in the GA4 admin, and send `page_view` yourself from a `usePathname()`/`useSearchParams()` subscription — the same shape as the PostHog reference, `Suspense`-wrapped for the same reason (`useSearchParams()` without a boundary deopts the route to client-side rendering).
- **Option B: leave it on and never send a manual `page_view`.** Verify in DebugView that every in-app navigation produces exactly one.

Whichever you choose, **verify by navigating three routes and counting three `page_view` events in DebugView.** Six means both owners are firing.

### Custom events

```ts
import { sendGAEvent } from '@next/third-parties/google';

sendGAEvent('event', 'checkout_payment_submitted', {
  plan_tier: 'pro',
  amount_cents: 4900,
  currency: 'EUR',
});
```

This call belongs in the single `analytics/track.ts` module (`SKILL.md` Rule 3), never at a call site.

## Consent Mode v2 — mandatory, and the part with legal deadlines

For EEA/UK/Swiss traffic on any site using Google advertising products, **Consent Mode v2 is required** (mandatory since 6 March 2024), and Google began **actively disabling conversion tracking and audience creation for non-compliant accounts from 21 July 2025**. This is not a best practice; non-compliance degrades the product you are paying for.

Four parameters must be sent, defaulting to **denied**, **before any Google tag loads**:

```html
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('consent', 'default', {
    ad_storage:          'denied',
    analytics_storage:   'denied',
    ad_user_data:        'denied',   // added in v2
    ad_personalization:  'denied',   // added in v2
    wait_for_update: 500,            // ms for the CMP to resolve asynchronously
  });
</script>
```

Then, on the banner's accept:

```ts
gtag('consent', 'update', {
  ad_storage: 'granted',
  analytics_storage: 'granted',
  ad_user_data: 'granted',
  ad_personalization: 'granted',
});
```

Notes that decide whether this actually works:

- **Order is everything.** The `default` call must execute before the GA tag. In Next.js that means a `beforeInteractive` script (or an inline script in the document head) — the one deliberate exception to `SKILL.md` Rule 8's defer-everything posture, because a consent default arriving late is worse than a few milliseconds of script.
- **`wait_for_update`** gives an async CMP time to answer; without it, tags may fire against the default before the real state resolves.
- **Google requires a Google-certified CMP** for EEA ad serving. Rolling your own banner does not satisfy this even if the parameter values are right.
- **June 2026 change:** `ad_storage` became the **sole authority** for advertising data on linked Ads accounts (Google Signals is now Analytics-only), `ad_personalization` governs whether Analytics data feeds personalised advertising, and Analytics encrypts IP addresses before forwarding to Ads. Net effect: **your CMP configuration is now the single control point** for Google ad-data flow — so a misconfigured banner is a bigger blast radius than it used to be. Re-verify after this date if the implementation predates it.

## The limits that will bite you

These are structural, not tuning problems. Read them before choosing GA4 as a product tool, because none has a good workaround:

- **Custom dimensions must be registered in the GA4 admin** before an event parameter is usable in reports. An unregistered parameter is collected and *invisible* — the classic "the event is in DebugView but I can't report on it". There is a hard cap (50 event-scoped custom dimensions), and registration is **not retroactive**: data before registration stays unreportable forever.
- **Cardinality → `(other)`.** High-cardinality dimensions get collapsed into an `(other)` bucket once row limits are hit, silently. Your `page_name` breakdown becomes 40 rows and one giant `(other)` — and there is no warning that it happened.
- **Data thresholding.** Reports suppress rows when they might identify individuals, especially with Signals enabled. Numbers change depending on who is looking and over what range — a support nightmare when a stakeholder cannot reproduce your figure.
- **Sampling** kicks in on large or complex explorations. The number moves between sessions.
- **`engagement_time_msec` is opaque.** GA4 has its own definition of engagement and does not expose the raw accumulation. If engagement time matters, implement `SKILL.md` Rule 5 yourself and send it as your own event parameter rather than trusting the built-in metric.
- **Naming collides with `SKILL.md` Rule 2.** GA4 reserves names (`page_view`, `session_start`, `purchase`, …) and prescribes an e-commerce schema. **Follow GA4's schema for the events GA4 has one for** — you gain the built-in reports — and apply the house `object_action` convention to everything else. Note the deviation once in the tracking plan, per the global "skill wins for its domain" rule.
- **Limits:** event names ≤ 40 chars, ≤ 25 parameters per event, parameter values ≤ 100 chars.
- **Ad blockers hit GA4 hardest** of any tool here — it is the most-blocked domain on the web. `SKILL.md` Rule 9 (server-side for money) is not optional with GA4.

## BigQuery export — the real escape hatch

The free BigQuery export is GA4's best feature and the answer to most of the limits above: raw, unsampled, un-thresholded event rows, queryable in SQL. **Turn it on at setup**, before you need it — the export is **not backfilled**, so any delay is permanently lost data.

If your analysis is going to be serious, plan to answer questions in BigQuery and treat the GA4 UI as an acquisition dashboard. That is the honest shape of a mature GA4 deployment.

## Server-side events

Use the **Measurement Protocol** for money/auth-critical events (`SKILL.md` Rule 9): send to Google's collection endpoint with `api_secret` + `measurement_id`, carrying the **same `client_id`** the browser tag uses (read it from the `_ga` cookie) or the `user_id`. A mismatched `client_id` creates a second user and breaks every funnel spanning the boundary.

Measurement Protocol events do not appear in real-time reports and are easy to get silently wrong — validate against the debug endpoint first.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| No pageviews after the first load | SPA navigation not detected | Own it explicitly — Option A or B above |
| Exactly double the pageviews | Enhanced measurement **and** a manual `page_view` | One owner only |
| Event visible in DebugView, absent from reports | Parameter not registered as a custom dimension | Register it; accept that prior data is lost |
| A dimension breakdown shows a huge `(other)` row | Cardinality collapse | Reduce cardinality, or query BigQuery |
| Two people get different numbers for one report | Thresholding / sampling | BigQuery for anything authoritative |
| Conversions stopped importing into Google Ads | Consent Mode v2 non-compliance enforcement | Certified CMP + all four parameters, defaults before the tag |
| Consent granted but tags still behave as denied | `default` call fired after the GA tag | Move it to `beforeInteractive` / inline in head |
| Traffic looks 30% lower than server logs | Ad blockers | Measurement Protocol server-side for critical events |
| `page_view` fires but `page_location` is wrong | Manual send without the resolved URL | Build the URL from `pathname` + `searchParams`, as in Option A |
