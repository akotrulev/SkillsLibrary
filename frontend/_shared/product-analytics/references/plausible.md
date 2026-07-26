# Plausible — reference

The **cookieless** option. Plausible collects no cookies and no persistent identifiers, which in most readings removes the ePrivacy consent-banner requirement entirely — and that is the whole product. It is lightweight (a ~1KB script), open-source, EU-hosted, and self-hostable under AGPL.

Read this only after choosing Plausible in [`SKILL.md`](../SKILL.md)'s decision tree — and after accepting what the choice costs, which is more than people expect.

## What you are giving up — read this before wiring anything

Plausible is **not a smaller PostHog**. Its privacy model forbids the thing product analytics is built on: **there is no persistent cross-session user identity, so there is no `identify()`**. That is not a missing feature awaiting a roadmap item; it is the architecture that makes the cookieless claim true. Consequences:

- **No user-level funnels or retention across sessions.** You cannot ask "of the users who signed up in March, how many came back in April" — the tool does not know it is the same person.
- **No cohort analysis, no user paths, no per-user drill-down.**
- **No session replay, no heatmaps.** So "where exactly did they click on this page" is unanswerable at element granularity.
- **Engagement detail is page-level at best.** `SKILL.md` Rule 5's active-vs-visible accumulation has nowhere useful to land.

If the request that brought you here was *"track where users click and where they spend time"* — the request this skill most often serves — **Plausible does not answer it**, and no amount of configuration will change that. Choose it when a banner-free, privacy-as-a-feature posture outranks the behavioural questions, and say so explicitly in the tracking plan so nobody spends a quarter trying to build a retention chart.

**Cost.** Plausible Cloud is **paid** (cheap, no permanent free tier — a trial only). **Plausible CE is AGPL and self-hostable at no licence cost**, which is the free lane here. Note the AGPL implications if you modify it and expose it over a network.

## Setup

Load the script variant you need — variants are **combinable** in the filename:

```html
<script defer
        data-domain="yourdomain.com"
        src="https://plausible.io/js/script.tagged-events.js"></script>
```

| Variant | Adds |
|---|---|
| `script.js` | Baseline pageviews |
| `script.tagged-events.js` | CSS-class-based event tagging **and** the `plausible()` function |
| `script.manual.js` | Suppresses automatic pageviews — you call `plausible('pageview')` yourself |
| `script.hash.js` | Hash-based routing support |
| `script.outbound-links.js` / `script.file-downloads.js` | Automatic outbound-link / download events |
| `script.pageview-props.js` | Custom properties on pageviews |
| `script.revenue.js` | Revenue attribution on events |

Combine as `script.tagged-events.hash.js`. **You need `tagged-events` (or `manual`) for the `plausible()` function to exist at all** — the baseline script does not define it, which is the most common "why is nothing tracking" cause.

### Pageviews on client navigation — this one is genuinely automatic

Unlike every other tool in this family, **Plausible needs no route-change subscription**. The script overrides `history.pushState` and listens for `popstate`, so Next.js App Router, React Router, Vue Router, and Blazor's client navigation all work with zero configuration. `hashchange` is handled only with the `hash` variant.

Verify anyway (three routes → three pageviews), but expect it to be correct. This is a real advantage of the tool and worth noting in the decision record.

### The queue stub

Because the script is `defer`red, `plausible()` may not exist when your code runs. Define the queue stub before any call — put it in `analytics/track.ts` alongside the wrapper (`SKILL.md` Rule 3):

```ts
declare global {
  interface Window { plausible?: { (...args: unknown[]): void; q?: unknown[] } }
}

window.plausible = window.plausible || function (...args: unknown[]) {
  (window.plausible!.q = window.plausible!.q || []).push(args);
};
```

## Events

```ts
plausible('signup_completed', {
  props: { plan_tier: 'pro', source: 'pricing_page' },
  revenue: { amount: 49.0, currency: 'EUR' },
  callback: () => {},          // fires after the event is sent — see below
});
```

Or declaratively, with no JavaScript:

```html
<button class="plausible-event-name=signup_completed plausible-event-plan=pro">Sign up</button>
```

Notes:

- **Goals must be created in the dashboard before conversions appear — and past events are not backfilled.** An event you send without a matching goal configured is *accepted and invisible*. Create the goal at the same time you add the event to the tracking plan, or you lose the data permanently. This is the same trap as GA4's unregistered custom dimensions.
- Class-name spaces use `+` (`plausible-event-name=Button+Click`). Prefer snake_case literals (`SKILL.md` Rule 2) and the problem does not arise.
- Some CMSs rewrite `=` to `-`; the alternative syntax is `plausible-event-name--EventName`.
- Up to **30 properties per event**, and a goal may carry at most **3 property constraints** — so properties filter, but they do not substitute for the dimensional depth of a real product tool.
- The `callback` is for navigating after an event fires (an outbound link that would otherwise cancel the request). Do **not** use it to sequence application logic — `SKILL.md` Rule 8 still holds: analytics never blocks the UI.

## Consent

This is why you chose it. Plausible sets no cookies and stores no persistent identifier, so in most readings **no consent banner is required** and the SDK may load unconditionally.

Two caveats worth stating in the plan rather than assuming:

- **"No banner required" is a legal conclusion, not a vendor setting.** It follows from cookieless operation plus your jurisdiction and lawful basis. Have counsel confirm it for your deployment rather than citing a marketing page — this is the one decision where getting it wrong costs more than the tool saved.
- **Still honour Global Privacy Control** as a matter of posture even where not strictly compelled, and keep the "no PII in event names or property keys" rule (`SKILL.md` Rule 7) — Plausible's privacy model does not stop *you* putting an email in a property.

## Server-side events

The **Events API** accepts events over HTTP with a `User-Agent` and `X-Forwarded-For` header, for money-critical events (`SKILL.md` Rule 9). Because there is no user identity, server events cannot be stitched to a browser session — they stand alone as counts. Plan metrics accordingly; a "server-side signup_completed" is a number, not a step in a user's journey.

## Proxying

Plausible is less blocked than GA4 but not unblocked. Both Cloud and CE support serving the script and receiving events from your own domain via a rewrite — same shape as the PostHog reference. Worth doing; still not a substitute for server-side emission of anything billed.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `plausible is not defined` | Baseline `script.js`; the function ships with `tagged-events`/`manual` | Switch variant **and** add the queue stub |
| Events send, dashboard shows nothing | Goal not created in site settings | Create the goal; prior events are **not** backfilled |
| No pageviews on hash routes | Hash needs the `hash` variant | `script.hash.js` (combinable) |
| Duplicate pageviews | `script.manual.js` plus automatic tracking assumptions | One owner: manual **or** automatic |
| Class-based tagging not firing on a CMS | The CMS rewrote `=` to `-` | `plausible-event-name--EventName` |
| Cannot build a retention or funnel report by user | No persistent identity — by design | Not fixable; wrong tool for the question |
| Event name shows with `+` signs | Spaces encoded in the class syntax | snake_case literals |
| Stakeholder asks "which button did they click" | No replay/heatmap/element capture | Re-open the decision tree — this is a tool change |
