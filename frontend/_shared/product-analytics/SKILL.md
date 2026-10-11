---
name: fe-shared-product-analytics
description: Use when instrumenting a frontend for product analytics — what users click, how far they get through a funnel, how long they actually engage — including choosing the tool (PostHog · GA4 · Amplitude · Plausible), writing the tracking plan, building the typed event emitter, and gating on consent. Triggers "add analytics", "track button clicks", "how long do users spend on this page", "set up PostHog/GA4/Amplitude", "add a funnel", "session replay / heatmaps". Not for server telemetry (`observability/*`), Core Web Vitals (the stack's `performance`), or engineering/DORA metrics (`qa/manual/quality-metrics`).
---

# Frontend — Product Analytics (one-of-N family)

Instruments a frontend so you can answer *what did users do* — clicks, funnels, drop-off, engagement time — as opposed to *is the service healthy* (that is `observability/*`, server-side, and a different question with a different audience). This SKILL.md is the **decision matrix + the doctrine that holds regardless of vendor**; per-tool SDK wiring, SPA pageview handling, replay/heatmap config, and consent APIs live in `references/<tool>.md` — read exactly one, after you've chosen.

The doctrine matters more than the vendor here. Analytics projects fail on **taxonomy rot and unusable data**, not on SDK integration — a swapped vendor costs a week, a fragmented event namespace costs the dataset. So the plan comes before the code, and it is enforced in TypeScript rather than in a wiki.

**Version rule:** detect the framework lane first (React/Next major from `package.json`, or the .NET TFM + render mode for Blazor). The client-navigation model is what breaks analytics, and it is framework-version-bound: **a client-side route change is not a page load**, so every SDK's default "capture pageview on init" fires once and then goes silent. Next.js App Router, React Router, and Blazor's `NavigationManager` each need an explicit route-change subscription. Pin the SDK major to the framework line and read the reference's version notes; PostHog's `@posthog/next` and GA4's consent-mode v2 both changed shape recently.

## When to use

- Adding product analytics to a frontend that has none
- Choosing between analytics tools (or justifying a change)
- Writing or auditing the tracking plan / event taxonomy
- Instrumenting a funnel, a click target, or engagement/dwell time
- Wiring session replay or heatmaps, and their masking rules
- Diagnosing wrong numbers: missing pageviews on client nav, inflated time-on-page, ad-blocker gaps, duplicate events

## When NOT to use

- Server-side traces/metrics/logs, OTel, Grafana → `observability/*` (external; the fence is below)
- Core Web Vitals, LCP/INP/CLS, bundle budgets → the stack's `performance` skill
- DORA, defect escape rate, flake rate → `qa/manual/quality-metrics`
- Designing the dashboard that *displays* this data → `design/charts`
- Feature-flag **testing** → `qa/<stack>/skills/feature-flag-testing` (PostHog ships flags; testing them is QA's lane)
- A/B test statistics and experiment design → out of scope; this skill emits the events an experiment reads

## The decision

```
Is a cookie banner a hard "no" (marketing site, EU-first, privacy as a feature)?
  YES → Plausible      (cookieless, no consent banner, pageview-level only)   → references/plausible.md
  NO  ↓
Is the primary question ACQUISITION (ad spend, channel attribution, SEO)?
  YES → GA4            (free, ads/Search Console integration; weak on product) → references/ga4.md
  NO  ↓
Do you need deep cohort / retention / behavioural-path analysis at enterprise scale?
  YES → Amplitude      (strongest analysis engine; paid, event-volume priced)  → references/amplitude.md
  NO  → PostHog        (DEFAULT — analytics + replay + heatmaps + flags in one) → references/posthog.md
```

| Tool | Cost | Answers "where they click" | Answers "how long they stay" | Session replay / heatmaps | Consent reality | Reference |
|---|---|---|---|---|---|---|
| **PostHog** | **Free tier** (1M events/mo) + **MIT self-host** | ✅ autocapture + explicit events | ✅ engagement time, `$pageleave` | ✅ both, built in; **masks inputs by default** | Cookie-based → banner needed; EU cloud + DPA available | [`posthog`](references/posthog.md) |
| **GA4** | Free (360 is paid) | ⚠️ enhanced measurement is shallow; custom events are second-class | ⚠️ `engagement_time_msec` is opaque and hard to trust | ❌ neither | Consent Mode v2 **mandatory** in the EEA | [`ga4`](references/ga4.md) |
| **Amplitude** | Paid; capped free tier | ✅ explicit events; autocapture on by default | ✅ strongest session/duration analysis | ⚠️ replay is a plugin/add-on; no heatmaps | Cookie-based → banner needed; EU `serverZone` | [`amplitude`](references/amplitude.md) |
| **Plausible** | Paid cloud; **AGPL self-host free** | ❌ pageviews + tagged goals only | ❌ page-level dwell only, no element detail | ❌ neither | **Cookieless — no banner required** | [`plausible`](references/plausible.md) |

**Default = PostHog** unless a row above clearly fits better. It is the only option that answers the click question *and* the dwell question *and* ships replay/heatmaps without a second vendor — which is why it is the default for the exact request that usually brings people to this skill. Take **Plausible** only when you accept that "where they click" becomes unanswerable; that is a real trade, not a lesser version of the same tool.

### The free lane

**The default is also the free answer** — this is not a coincidence to be re-litigated per project. PostHog's free tier ([pricing](https://posthog.com/pricing)) covers **1M events, 5K session replays, and 1M feature-flag requests per month**, resetting monthly, with one project and one-year retention. For most pre-scale products that is the whole bill, indefinitely, and it includes the replay + heatmaps that answer the click/dwell question.

Two honest caveats, because "free" gets oversold in both directions:

- **Self-hosting is free of licence cost, not free of work.** The core is MIT and the entire platform can run on your infrastructure, but the documented open-source path is a **Docker Compose "hobby" deploy targeting roughly 100K events/month with no vendor support**, and the `ee/` directory (SSO enforcement, advanced permissions, audit logs) sits under a separate enterprise licence. Self-host for data-residency or sovereignty reasons; do **not** self-host to dodge a bill you have not yet received — the cloud free tier is an order of magnitude more headroom than the hobby deploy.
- **Free tiers move.** Mixpanel cut its free tier from 20M to 1M events in late 2025. Check current limits at commit time rather than trusting this table, and prefer a tool whose *self-host* escape hatch is real — that is what actually caps your downside.

If the job is genuinely website analytics rather than product analytics, **Umami** and **Matomo** are the free/self-hostable options in that adjacent lane (Matomo being the closest GA replacement, though its heatmap/recording plugins are paid). Neither is written up here: they do not answer the element-level click and engagement questions this skill exists for, and adding a tool that fails the core use case would make the decision tree worse, not more generous.

**Two tools is a legitimate configuration** — and the only one worth running: **GA4 for acquisition + one product tool**. They answer different questions to different audiences. Do not run two *product* tools; that is the same events paid for twice, drifting apart.

## Cross-cutting rules (every tool)

### 1. The tracking plan is the deliverable; the code is downstream

Write `docs/analytics/tracking-plan.md` **before any SDK call**. One row per event:

| Event | Fires when | Properties | Metric / decision it serves | Owner |
|---|---|---|---|---|
| `checkout_payment_submitted` | User submits the payment step | `plan_tier`, `amount_cents`, `currency`, `is_retry` | Checkout conversion (step 4→5) | Growth |

**The hard gate: no event ships without a named metric or decision in that column.** "Might be useful later" is how a namespace rots into 400 events nobody trusts. An event you cannot name a consumer for is not instrumentation, it is exhaust.

The metrics in that column should trace to the initiative's measurable success metrics — `business-analysis/skills/ba-scoping-writeup` produces exactly that list, and is the correct upstream source when one exists.

### 2. Naming: `object_action`, snake_case, fixed strings

The industry-converged convention, and the one every tool's docs land on ([PostHog](https://posthog.com/docs/product-analytics/best-practices), [Segment](https://segment.com/academy/collecting-data/naming-conventions-for-clean-data/), [Amplitude](https://www.optizent.com/blog/a-practical-guide-to-designing-your-amplitude-event-taxonomy/)):

- **`object_action`**, past-tense-as-fact, lowercase `snake_case` — `signup_completed`, `invite_sent`, `export_failed`. Snake_case survives warehouse export and dodges case-sensitivity fragmentation (Amplitude treats `Song Played` and `song played` as two events — casing drift alone splits a metric in half).
- **Namespace with a prefix** on anything non-trivial: `checkout_payment_submitted`, `onboarding_profile_skipped`.
- **A curated verb list**, written into the plan: `viewed · clicked · submitted · created · updated · deleted · started · completed · cancelled · failed · sent · invited`. New verb = a plan change, not an ad-hoc call.
- **Events are the *what*; properties are the who/where/why/how.** One `page_viewed` with a `page_name` property, never `page_viewed_pricing` / `page_viewed_docs`.
- **Never build a name dynamically.** `` track(`${section}_clicked`) `` is the single most destructive line in analytics code — it defeats autocomplete, the plan, the CI gate, and every schema tool. Names are string literals. Always.
- **Properties are `object_adjective`**: `item_price`, `is_subscribed`, `has_seen_upsell`, `member_count`.

### 3. One typed emitter — the vendor SDK never appears at a call site

This is the rule that turns the plan from a document into a constraint. Define the event map once and let the compiler enforce the taxonomy:

```ts
// analytics/events.ts — the tracking plan, in code
export type AnalyticsEvent =
  | { name: 'checkout_payment_submitted'; props: { plan_tier: PlanTier; amount_cents: number; currency: string; is_retry: boolean } }
  | { name: 'onboarding_profile_skipped';  props: { step_index: number } };

// analytics/track.ts — the ONLY module that imports the vendor SDK
export function track<E extends AnalyticsEvent>(name: E['name'], props: E['props']): void { /* consent gate → scrub → vendor */ }
```

Four things fall out of one wrapper, and none of them are available without it:

1. **The compiler rejects an off-plan event or a missing property** — the taxonomy is enforced at build time, not in review, not in a quarterly cleanup.
2. **One place to gate consent** (Rule 7) — so consent cannot be missed at a call site.
3. **One place to scrub PII** before anything leaves the browser.
4. **The vendor is swappable** — a migration edits one file instead of 300 call sites. Treat this as the default expectation, not a hypothetical: analytics vendors get switched.

Blazor: the same shape as a `IAnalytics` service injected per the constructor-injection rule, with a single collocated `.razor.js` module doing the interop hop (per the stack's `javascript-calls` rules — this is one of the few genuine "no C# equivalent" cases).

### 4. Autocapture explores; explicit events decide

Autocapture (PostHog, Amplitude) records every click/DOM interaction with no code. It is genuinely valuable — for **retrospective exploration**, answering questions you did not know to ask, and for finding the dead zones on a page.

But **anything a dashboard, alert, funnel, or decision depends on is an explicit event in the plan.** Autocapture keys on DOM structure and CSS selectors, so a refactor that changes markup silently breaks the metric — no error, no failed build, just a line that flattens. Use autocapture as a discovery layer; promote anything that matters into an explicit event.

### 5. Engagement time is measured, not assumed

"How long do users spend here" is where naive instrumentation produces confidently wrong numbers. The failure is standard: timestamp on mount, timestamp on unmount, subtract. That counts a backgrounded tab, so a laptop left open overnight reports eight hours of rapt engagement, and your mean time-on-page becomes fiction.

The rules:

- **Accumulate only while visible.** Use the Page Visibility API — sum the intervals where `document.visibilityState === 'visible'`, pausing on `visibilitychange`. Never one wall-clock subtraction.
- **Distinguish *active* from *visible*.** Active time resets an idle timer (~30s) on input/scroll/keypress; visible time does not. Both are legitimate; the plan must say **which one the metric means**, because they differ by multiples on long pages.
- **Flush with `navigator.sendBeacon()` on `visibilitychange`→hidden and on `pagehide`.** Do **not** rely on `unload`/`beforeunload` — they are unreliable on mobile and are skipped entirely by the bfcache, which is precisely the population you are trying to measure.
- **A route change is not an unload.** In an SPA the emitter closes the current interval itself on navigation (the same subscription that fixes pageviews — Version rule). Otherwise time-on-page silently accrues to whichever page happened to be last.
- **Report percentiles, never the mean.** Dwell time is long-tailed and the mean is dominated by abandoned tabs. p50/p75/p90, and cap the recorded value at a sane ceiling.

### 6. One element, one canonical name — reuse the `data-testid` identity

The app already has a stable, refactor-surviving name for every interactive element: its `data-testid` (`test-ids` / `testability`, PascalCase dot-separated). Do not invent a second, drifting scheme for analytics.

**Derive, don't duplicate:** `Operations.ScheduledJobs.AddButton` → `scheduled_jobs_add_clicked`. The testid stays the element's identity; the event name is its taxonomy rendering. When one is renamed the other is mechanically derivable, so the pair is auditable — and QA's suites and the analytics dashboard end up describing the same element with the same word, which is worth more than either convention alone.

### 7. Consent and PII are blocker-class, not a later ticket

Getting this wrong is a regulatory finding and a rip-out, not a bug:

- **No cookie-setting SDK initialises before consent** in an ePrivacy jurisdiction. Consent-gate the emitter (Rule 3), don't scatter checks. Genuinely cookieless tools (Plausible) are the exception — that is most of what you buy from them.
- **Honour Global Privacy Control (`navigator.globalPrivacyControl`) and DNT**, and **stop recording on withdrawal** — many deployments never wire the revoke path, which is exactly the one an audit tests.
- **No PII in event names or property *keys*.** Emails, names, and free-text go in neither. Identify users by an opaque stable id; `identify()` links the pre-auth anonymous id to it once, at login.
- **Session replay masks all inputs by default — masking is opt-out per field, never opt-in.** PostHog masks inputs by default; several tools do not. An allow-list posture means the one field nobody thought about is the one that leaks a card number to a vendor's servers.
- **Verify masking on staging with synthetic PII before production**, and re-verify after any form refactor. This is a QA handshake (`qa-security`), not a self-certification.
- **Data residency**: EU cloud region + a signed DPA, or self-host. Decide this *before* instrumenting — it is not a config flip afterwards.

### 8. Analytics never blocks the UI, and never breaks it

- Load the SDK **after hydration** (`next/script` `afterInteractive`/`lazyOnload`, or a deferred import) — never render-blocking. This is the same rule the stack's `performance` skill states for all third-party scripts.
- **Never `await` a track call** in an event handler, and never put one in a render path. Fire and forget.
- **A failing analytics call must not surface to the user.** The emitter swallows and (at most) logs. An SDK outage is not an application outage.
- Expect the SDK to be **blocked outright** for a meaningful share of users. Which leads to:

### 9. Anything money- or security-relevant is emitted server-side

Ad blockers and tracking protection eat a large, *non-random* fraction of client-side events — technical and privacy-conscious users are over-represented, so the bias is systematic, not noise. Client-side numbers are directionally useful and quantitatively unreliable.

So: **revenue, signup completion, subscription state, and anything reported to the business or used for billing is emitted server-side** (or reconciled against the database), while UI interaction detail stays client-side. Route client events through a first-party reverse proxy (every tool supports it) to reduce, *not* eliminate, blocking — and never report a blocked-client number as the truth.

## The fence: this skill vs `observability/*`

Both are "telemetry", and the boundary trips people constantly:

| | This skill | `observability/*` |
|---|---|---|
| Question | *What did users do?* | *Is the service healthy?* |
| Emitted from | The browser | The server |
| Audience | Product, growth, design | Engineering, on-call |
| Grain | User + session | Request + trace |
| Backend | PostHog / GA4 / Amplitude | Loki / Prometheus / Tempo |

They meet in exactly one place: a user-facing failure should be traceable from a `*_failed` product event to the server trace that caused it — carry the `trace_id` as an event property when one is available. Do **not** push product events into the OTel pipeline to "unify" them: metric-label cardinality is bounded there, and `user_id` as a metric label is the exact violation that domain's invariants forbid.

## Anti-patterns

| Smell | Fix |
|---|---|
| Dynamic event names — `` track(`${x}_clicked`) `` | String literals from the typed union; the variable becomes a property |
| Vendor SDK imported at call sites across the app | One `track()` wrapper; the SDK appears in exactly one module |
| Instrumenting first, defining metrics later | Tracking plan with a metric per row, before the first SDK call |
| `page_viewed_pricing`, `page_viewed_docs`, … | One `page_viewed` + a `page_name` property |
| Time-on-page as unmount − mount | Page Visibility accumulation; flush via `sendBeacon` on hide/pagehide |
| Pageviews only fire on hard load | Subscribe to the router's route-change event (the SPA rule) |
| A dashboard KPI built on an autocaptured selector | Promote it to an explicit planned event |
| Session replay with opt-in masking | Mask-all-inputs by default; opt out per field, verified on staging |
| SDK initialised before consent; no revoke path | Consent-gate the emitter; wire withdrawal + GPC |
| Revenue reported from client-side events | Server-side emit or DB reconciliation |
| Two product analytics tools running | One product tool (+ GA4 for acquisition, if needed) |
| `await track(...)` in a click handler | Fire and forget; never block the interaction |
| Mean time-on-page in a report | p50/p75/p90 with a capped ceiling |

## Workflow

1. **Write the tracking plan first** — `docs/analytics/tracking-plan.md`, one row per event, each with a named metric/decision. Source the metrics from `business-analysis:scoping` output when it exists. **Do not open an SDK doc yet.**
2. **Choose the tool** via the decision tree; record the reason in one line. Settle **data residency + consent posture now** — both are architectural.
3. **Read the one `references/<tool>.md`** — packages, provider wiring, the route-change subscription, identify/alias, replay + masking config, proxy setup.
4. **Build the typed emitter** (`analytics/events.ts` + `analytics/track.ts`): the event union, the consent gate, the PII scrub, the single vendor import.
5. **Wire consent** — banner/preference centre → emitter gate → SDK init, plus the revoke path and GPC check.
6. **Instrument** against the plan, deriving names from `data-testid` identities. Explicit events for everything the plan names; leave autocapture for exploration.
7. **Instrument engagement time** via the visibility accumulator, declaring active-vs-visible in the plan.
8. **Move money/auth-critical events server-side.**
9. **Verify** (below), then build the dashboard/funnel — `design/charts` owns how it looks.

## Validation

- Tracking plan exists, every row names a metric/decision, and every shipped event appears in it (and vice versa — orphan events in the vendor UI mean the plan drifted).
- TypeScript **rejects** an unplanned event name and a missing required property. Test this deliberately — it is the whole point of Rule 3.
- Client-side route changes produce exactly **one** pageview each — no misses, no duplicates on back/forward.
- **No network request to the analytics host before consent is granted.** Check the Network tab with consent denied; then confirm withdrawal stops in-flight collection.
- Session replay of a form containing synthetic PII shows **masked** fields — verified on staging, after the most recent form change.
- A page left backgrounded for 10 minutes reports **seconds** of engagement, not 10 minutes.
- Blocking the analytics domain (uBlock / DNS) leaves the app fully functional — no console errors, no broken handlers, no blocked render.
- Lighthouse: the SDK is not render-blocking; no regression against the `performance` skill's budgets.
- Revenue events reconcile against the database within an accepted margin.

## Handoffs

- Server traces/metrics/logs, OTel, Grafana → `observability/*` (see the fence above)
- Deferring third-party scripts, Core Web Vitals budgets → the stack's `performance` skill
- `data-testid` naming and placement (the identity source for Rule 6) → the stack's `test-ids` / `testability` skill
- Consent-banner UX, microcopy, preference-centre IA → `design/ux-writing` + the stack's `ui-rules`
- Dashboards, funnels, charts built on this data → `design/charts` (product) — **not** `observability/dashboards` (ops)
- Success metrics that populate the plan's metric column → `business-analysis/skills/ba-scoping-writeup`
- Verifying masking, consent gating, and third-party data flow → `qa-security` (peer, invoked separately)
- Feature-flag testing when the tool doubles as a flag provider (PostHog) → `qa/<stack>/skills/feature-flag-testing`
- Engineering/delivery metrics (DORA, escape rate) → `qa/manual/quality-metrics`
