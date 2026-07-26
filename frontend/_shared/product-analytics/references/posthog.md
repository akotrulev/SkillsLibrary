# PostHog — reference

The **default** of the family. One vendor covering product analytics, session replay, heatmaps, feature flags, and experiments — which is why it answers both halves of the usual request ("where do they click" *and* "how long do they stay") without a second contract. Open-source and self-hostable; EU cloud region available.

Read this only after choosing PostHog in [`SKILL.md`](../SKILL.md)'s decision tree. Everything in that file's **Cross-cutting rules** still applies — this file is SDK mechanics, not doctrine. In particular: the vendor calls below belong in **one** `analytics/track.ts` module (Rule 3), never at call sites.

**Versions.** `posthog-js` (browser) + `posthog-node` (server) are the stable lane and what this file uses. **`@posthog/next`** is a newer Next-specific package (synchronised client/server identity, server-side flag bootstrapping, built-in proxy) that removes much of the manual wiring below — check its current stability before adopting; if it has stabilised in your Next major, prefer it and skip the manual `PostHogPageView` step. Pin the major and re-read the changelog on upgrade: the pageview/pageleave defaults have changed shape more than once.

## Setup — Next.js App Router

```bash
pnpm add posthog-js posthog-node
```

```
# .env.local
NEXT_PUBLIC_POSTHOG_KEY=phc_xxx
NEXT_PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com   # EU region — see Residency below
```

### The provider (a `'use client'` island, mounted once)

```tsx
// app/providers.tsx
'use client';
import posthog from 'posthog-js';
import { PostHogProvider } from 'posthog-js/react';
import { useEffect } from 'react';

export function PHProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: '/ingest',                    // reverse proxy — see below
      ui_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      capture_pageview: false,                // we fire these ourselves — see next section
      capture_pageleave: true,                // needed for engagement time
      person_profiles: 'identified_only',     // don't bill/store profiles for anonymous traffic
      autocapture: true,                      // exploration layer only (SKILL.md Rule 4)
      disable_session_recording: true,        // opt in explicitly, after consent
      opt_out_capturing_by_default: true,     // consent gate — SKILL.md Rule 7
    });
  }, []);

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>;
}
```

Mount it once from `app/layout.tsx`, wrapping `{children}`. It is a client island — the root layout itself stays a Server Component.

### Pageviews on client navigation — the step everyone misses

`capture_pageview: true` fires **once**, at SDK init. Every subsequent App Router navigation is a client-side transition with no page load, so it is invisible. This is the SPA rule from `SKILL.md`'s Version rule, in its concrete form:

```tsx
// app/posthog-page-view.tsx
'use client';
import { usePathname, useSearchParams } from 'next/navigation';
import { usePostHog } from 'posthog-js/react';
import { useEffect } from 'react';

function PageView() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const posthog = usePostHog();

  useEffect(() => {
    if (!pathname || !posthog) return;
    let url = window.origin + pathname;
    const qs = searchParams?.toString();
    if (qs) url += `?${qs}`;
    posthog.capture('$pageview', { $current_url: url });
  }, [pathname, searchParams, posthog]);

  return null;
}

// useSearchParams() opts the subtree into client-side rendering — the Suspense
// boundary keeps that from deopting the whole route to dynamic rendering.
export function PostHogPageView() {
  return <Suspense fallback={null}><PageView /></Suspense>;
}
```

Render `<PostHogPageView />` inside the provider. **The `Suspense` wrapper is not optional** — without it, `useSearchParams()` forces the entire route into client-side rendering, which quietly costs you static generation on every page in the app.

**Verify:** navigate between three routes via in-app links and confirm exactly three `$pageview` events — not one (subscription missing) and not six (provider mounted twice, usually from being placed in both a layout and a template).

### Vite SPA + React Router

Same provider, no `Suspense` concern; subscribe with `useLocation()` from React Router instead of `usePathname`/`useSearchParams`, capturing `$pageview` on `location.key` change.

### Blazor

No first-party .NET SDK. Load `posthog-js` via a collocated `.razor.js` module behind an injected `IAnalytics` service (constructor injection, `IAsyncDisposable`, per the stack's `javascript-calls` rules), and subscribe to `NavigationManager.LocationChanged` for the pageview. Prefer `posthog-node` from the server for anything the server already knows.

## Reverse proxy

Route ingestion through your own domain so a first-party path serves the SDK and receives events. It meaningfully reduces (never eliminates — `SKILL.md` Rule 9) ad-blocker loss. In `next.config.ts`:

```ts
async rewrites() {
  return [
    { source: '/ingest/static/:path*', destination: 'https://eu-assets.i.posthog.com/static/:path*' },
    { source: '/ingest/:path*',        destination: 'https://eu.i.posthog.com/:path*' },
  ];
}
```

Set `api_host: '/ingest'` (as above) and keep `ui_host` pointed at the real host so in-app links to the PostHog UI still resolve. Match the asset/ingest hostnames to your region.

## Identity

```ts
posthog.identify(user.id, { email: user.email, plan_tier: user.planTier }); // on login
posthog.reset();                                                            // on logout — critical
```

- **Identify with an opaque stable id**, never an email as the distinct id.
- **`reset()` on logout is mandatory.** Skipping it merges the next anonymous session — and on a shared machine, the next *user* — into the previous identity. This is both a data-quality bug and a privacy incident.
- `person_profiles: 'identified_only'` keeps anonymous traffic out of person storage; leave it on unless you have a specific reason.
- Setting `email` as a person property is a deliberate PII decision — take it consciously against your DPA, and note that `SKILL.md` Rule 7 bars PII from event names and property *keys*, not from an intentional person profile.

## Consent gating

`opt_out_capturing_by_default: true` in `init` means nothing is sent until you say so. Wire the banner to the emitter, not to scattered call sites:

```ts
export function grantAnalyticsConsent() {
  posthog.opt_in_capturing();
  posthog.startSessionRecording();     // only if replay is in scope and disclosed
}

export function revokeAnalyticsConsent() {
  posthog.stopSessionRecording();
  posthog.opt_out_capturing();
  posthog.reset();                     // drop the id so a new anonymous session starts clean
}
```

Check `navigator.globalPrivacyControl` and DNT at startup and treat either as a denial. **Test the revoke path** — it is the one an audit exercises and the one that is usually never wired.

## Session replay + heatmaps

Enable **after** consent (`disable_session_recording: true` at init, then `startSessionRecording()`). Masking config, with the posture `SKILL.md` Rule 7 requires:

```ts
session_recording: {
  maskAllInputs: true,                       // PostHog's default — keep it
  maskInputOptions: { password: true, email: true, text: true, textarea: true, select: true },
  maskTextSelector: '[data-ph-mask]',        // opt specific rendered text out
}
```

- **Inputs are masked by default; general rendered *text* is not.** That gap is where PII actually leaks — an order confirmation, an account page, a support thread rendered as text is captured verbatim. Mark those regions with `maskTextSelector` or the `ph-no-capture` class.
- **Masking happens in the browser — masked data never reaches PostHog's servers.** That is what makes this a real control rather than a retention setting.
- Do **not** flip `maskAllInputs: false` to "see more"; opt out per field via `maskInputOptions`/`maskInputFn`.
- **Heatmaps** ride on autocapture + the toolbar and need no extra instrumentation — but per `SKILL.md` Rule 4 they are an exploration surface, not a KPI source.
- Verify on staging with synthetic PII in every form, and re-verify after form refactors.

## Server-side events

For revenue, signup completion, and anything billed or reported (`SKILL.md` Rule 9):

```ts
import { PostHog } from 'posthog-node';

const posthogServer = new PostHog(process.env.POSTHOG_KEY!, { host: process.env.POSTHOG_HOST });

posthogServer.capture({
  distinctId: user.id,                  // the SAME id the client identifies with
  event: 'subscription_activated',
  properties: { plan_tier: 'pro', amount_cents: 4900, currency: 'EUR' },
});

await posthogServer.shutdown();         // serverless: flush before the function exits
```

- **The `distinctId` must match the client's identify id**, or the user splits into two people and every funnel spanning the boundary breaks.
- In serverless, `shutdown()` (or `flush()`) before the invocation ends — the node SDK batches, and an un-flushed batch is a silently dropped event. Next 15: `after()` is the right place for it.

## Feature flags

PostHog ships flags, so the flag provider and the analytics provider are one SDK. Two notes: bootstrap flag values server-side to avoid a flash of the control variant on first paint, and remember that **testing** flagged code is QA's lane — `qa/<stack>/skills/feature-flag-testing` pins flag state in-process and requires both sides of every flag covered. Never point a test suite at live flag evaluation.

## Data residency

Choose the region at project creation — `eu.i.posthog.com` vs `us.i.posthog.com`. **It cannot be changed later without a migration**, so this is a `SKILL.md` Workflow step 2 decision, not a config detail. Self-hosting is the third option and the only one that keeps event data entirely in your infrastructure.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Pageviews only on hard reload | `capture_pageview: true` fires once at init | The `PostHogPageView` subscription above |
| Every route renders dynamically; static generation lost | `useSearchParams()` without a `Suspense` boundary | Wrap it (as shown) |
| Duplicate pageviews | Provider mounted in both a layout and a template | Mount once, at the root |
| Anonymous and logged-in sessions are separate users | `identify()` never called, or called with a different id than the server's | One opaque id, used identically client and server |
| A logged-out visitor inherits the previous user's identity | `reset()` missing on logout | Call it on every logout path |
| Engagement time missing or zero | `capture_pageleave: false` | Enable it; pair with the visibility accumulator (`SKILL.md` Rule 5) |
| Events vanish in production, fine locally | Ad blockers | Reverse proxy; move business-critical events server-side |
| Server events silently dropped in serverless | Batch never flushed | `await posthogServer.shutdown()` before exit |
| Replay shows a customer's address in plain text | Only inputs are masked by default | `maskTextSelector` / `ph-no-capture` on rendered PII regions |
| A KPI flatlines after a UI refactor | It was built on an autocaptured selector | Promote it to an explicit planned event |
