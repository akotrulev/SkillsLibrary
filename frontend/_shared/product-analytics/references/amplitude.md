# Amplitude — reference

The strongest **analysis engine** of the family. Where PostHog is the broadest toolkit and GA4 is an acquisition dashboard, Amplitude is what you choose when the hard questions are behavioural: multi-step funnels with custom attribution windows, retention curves segmented by cohort, pathfinding across sessions, and cohort definitions that feed back into the product. Pick it when a data/product-analytics team will genuinely use that depth — it is wasted otherwise.

Read this only after choosing Amplitude in [`SKILL.md`](../SKILL.md)'s decision tree. Everything in that file's **Cross-cutting rules** still applies; the SDK calls below belong in one `analytics/track.ts` module (Rule 3).

**Versions.** **Browser SDK 2** (`@amplitude/analytics-browser`) is the current lane; SDK 1 and the legacy `amplitude-js` "Javascript SDK" are both superseded and have migration guides. Two behavioural changes matter when reading older tutorials: **`defaultTracking` was replaced by `autocapture`**, and **from 2.10.0 autocapture is on by default**. A guide predating that will leave you with events you did not plan for.

**Cost.** There is a real free tier with unlimited seats, but published figures for its event and MTU caps **conflict across sources** — check [amplitude.com/pricing](https://amplitude.com/pricing) directly before committing, and note that Amplitude bills on **MTUs** (monthly tracked users) as well as events, so a low-event/high-user product prices very differently from the reverse. Session replay quota is a separate line. If free-and-uncapped is the requirement, `SKILL.md`'s free-lane note points at PostHog instead.

## Setup

```bash
pnpm add @amplitude/analytics-browser
```

```ts
import * as amplitude from '@amplitude/analytics-browser';

amplitude.init(process.env.NEXT_PUBLIC_AMPLITUDE_KEY!, {
  serverZone: 'EU',                  // EU residency — decide before you instrument
  autocapture: {
    pageViews: true,                 // handles SPA navigation — see below
    sessions: true,
    attribution: true,
    elementInteractions: true,       // the exploration layer (SKILL.md Rule 4)
    formInteractions: false,
    fileDownloads: false,
  },
  identityStorage: 'localStorage',   // avoid AMP_ cookies; see Consent below
  trackingOptions: { ipAddress: false },
  optOut: true,                      // consent gate — flip on grant
});
```

Note the init signature is `init(apiKey, optionalUserId?, options?)` — passing options as the **second** argument silently treats them as a user id. Pass `undefined` explicitly if you need the three-argument form.

### Pageviews on client navigation

`autocapture.pageViews` handles SPA route changes, so unlike PostHog and GA4 there is usually **no manual subscription to write**. Verify it anyway — navigate three routes and count three page-view events. If your router does something unusual (hash routing, or a shell that rewrites the URL without a History API call), fall back to `autocapture.pageViews: false` plus a manual `amplitude.track('[Amplitude] Page Viewed', …)` from the router subscription.

### Autocapture is on by default — decide, don't inherit

From 2.10.0, `elementInteractions`, `sessions`, `attribution`, `pageViews`, `formInteractions`, `fileDownloads` and others default on. That is a lot of unplanned event volume against an MTU/event-priced plan, and it collides with `SKILL.md` Rule 1 (every event names a metric).

**Set the `autocapture` object explicitly, every key you care about.** Enable `elementInteractions` deliberately as the exploration layer, and remember Rule 4: nothing autocaptured backs a KPI. `autocapture: false` opts out entirely.

## Events

```ts
amplitude.track('checkout_payment_submitted', {
  plan_tier: 'pro',
  amount_cents: 4900,
  currency: 'EUR',
  is_retry: false,
});
```

Amplitude imposes no naming scheme, so `SKILL.md` Rule 2 applies unmodified — `object_action`, snake_case, string literals. **Amplitude is case-sensitive and treats `Song Played` and `song played` as two distinct events**, which is exactly the fragmentation Rule 2 exists to prevent; a single inconsistent call site permanently splits a metric.

Amplitude's **Govern** feature (plan-dependent) can block unplanned events server-side. Where available, wire it to the tracking plan — it is the vendor-side enforcement that pairs with Rule 3's compile-time enforcement, and the two together are what actually keeps a taxonomy clean.

## Identity

```ts
amplitude.setUserId(user.id);                       // on login — opaque stable id
amplitude.reset();                                  // on logout — MANDATORY

const identify = new amplitude.Identify();
identify.set('plan_tier', 'pro').setOnce('signup_date', signupDate).add('login_count', 1);
amplitude.identify(identify);
```

- `reset()` clears the user id **and generates a new device id** — skip it and the next anonymous visitor on a shared machine inherits the previous identity.
- The `Identify` class carries operations (`set`, `setOnce`, `add`, `append`, `unset`, `remove`, `clearAll`); `setOnce` for immutable facts like signup date, `add` for counters.
- **`minIdLength`**: Amplitude rejects user/device ids below a minimum length by default. Short numeric database ids get silently dropped — set `minIdLength` to match your id scheme, or use an opaque longer id.

## Consent

```ts
amplitude.setOptOut(true);   // deny — no events sent
amplitude.setOptOut(false);  // grant
```

Gate this in the emitter, not at call sites (`SKILL.md` Rule 7). Two Amplitude specifics:

- The SDK writes `AMP_` and `AMP_MKTG_` **cookies** by default. `identityStorage: 'localStorage'` avoids them — which changes, but does **not** remove, your consent obligation: localStorage used for analytics is still terminal-equipment access under ePrivacy in most readings. Do not treat the flag as a banner exemption.
- `trackingOptions: { ipAddress: false }` suppresses IP collection; combine with `serverZone: 'EU'` for an EU-residency posture. **`serverZone` is a creation-time decision for the project** — moving data between zones later is a migration, not a setting.

## Session replay

Session replay ships as a separate plugin rather than being built in, and is quota-limited by plan:

```ts
import { sessionReplayPlugin } from '@amplitude/plugin-session-replay-browser';

amplitude.add(sessionReplayPlugin({ sampleRate: 0.1 }));   // sample — quota is finite
```

- **Sample deliberately.** Unlike PostHog's bundled replay, you are metering a paid quota; 100% capture on a high-traffic app burns it in days.
- **Verify the masking posture yourself** against `SKILL.md` Rule 7 — do not assume mask-all-inputs is the default here the way it is in PostHog. Configure masking, then confirm on staging with synthetic PII in every form.
- **There are no heatmaps.** If heatmaps are a requirement, Amplitude is the wrong pick — that is a decision-tree question, not something to bolt on with a second vendor.

## Server-side events

Use `@amplitude/analytics-node` for money/auth-critical events (`SKILL.md` Rule 9). The `user_id` must match the browser's `setUserId` value exactly, or the user splits in two and cross-boundary funnels break. In serverless, flush before the invocation exits — the node SDK batches, and an un-flushed batch is a dropped event.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Events with no user id are dropped | `minIdLength` rejects short ids | Raise/lower `minIdLength` or use opaque longer ids |
| Options ignored; a userId appears as `[object Object]` | Options passed as the 2nd positional arg | `init(key, undefined, options)` |
| Unplanned event volume after an SDK upgrade | Autocapture defaults on from 2.10.0 | Set the `autocapture` object explicitly |
| One metric splits into two lines | Case drift — Amplitude is case-sensitive | snake_case literals from the typed union (Rule 2) |
| A logged-out visitor inherits the last user | `reset()` missing on logout | Call it on every logout path |
| MTU bill higher than expected on low traffic | Anonymous visitors count toward MTUs | Reduce autocapture; consider identified-only strategy |
| Replay quota exhausted mid-month | `sampleRate: 1` on high traffic | Sample down |
| EU customers' data landing in the US | `serverZone` not set at init | Set it; a later change requires migration |
| Funnel breaks between web and server steps | `user_id` mismatch across SDKs | One opaque id used identically |
| Tutorial code uses `defaultTracking` | Pre-2.x guide | `autocapture` is the SDK 2 name |
