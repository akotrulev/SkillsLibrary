---
name: mobile-shared-observability
description: Use when a mobile app needs crash reporting, traces, logs or metrics — choosing the crash reporter, OpenTelemetry on device, the ingest path to Grafana, sampling, resource attributes, PII scrubbing. Triggers "add crash reporting", "send app telemetry to Grafana", "which OTel SDK for React Native". Do NOT use for the Collector, Loki, Tempo or Mimir setup (`observability-engineer-<stack>`), release symbols (`mobile-shared-release`), or secure storage (`mobile-shared-security`).
---

# Mobile — Observability

What a mobile app emits, how it leaves the device, and what it must never carry. The backend half — Collector, Loki, Tempo, Prometheus / Mimir, dashboards — is the `observability-engineer-<stack>` agents' (be-* plugins; see `observability/logs-traces-setup`). This skill ends at the **public ingest gateway**.

**The mobile difference.** The client is untrusted, intermittently offline, battery- and data-metered, and its binary is public. So: batch and sample on device, send through a gateway you control, put **no backend credential in the app**, and scrub PII before anything is written, not after.

## When to use

- Adding or reviewing crash reporting, tracing, logging or app-performance metrics
- Wiring the app to the Grafana stack, or choosing an OTel SDK per stack
- Deciding sampling, batching, resource attributes, or what may be logged
- Release-health signals that gate a rollout (crash-free users, ANR / hang rate)

## When NOT to use

- Collector pipelines, Loki / Tempo / Mimir storage, dashboards, LogQL → `observability-engineer-<stack>` and `observability/{logs-traces-setup,metrics-setup,queries,dashboards}`
- Symbol and source-map upload, rollout halting → `mobile-shared-release`
- Where tokens and secrets are stored → `mobile-shared-security`
- Store privacy declarations for the SDKs you add → `mobile-shared-store-compliance`

## Version lane (verified 2026-10-10)

| Stack | Fact | Re-verify after |
|---|---|---|
| iOS | OTel Swift 2.5.1; MetricKit + `os.Logger` are platform | 2027-01-15 |
| Android | OTel Android agent 1.7.0 — **the agent API is stable; the instrumentations are alpha.** Sources report maturity both ways (BOM shown as `1.7.0` and `1.7.0-alpha`; instrumentation modules on `1.0.x-alpha`), so pin exact versions and re-read the release notes before upgrading | 2026-12-31 |
| React Native | **No official OTel RN SDK.** Options: `expo-observe` OTel export, Embrace RN 7.2, Grafana Faro RN (**experimental**), Sentry RN 8.30 | 2026-12-31 |
| Crash reporters | Sentry (RN 8.30) or Firebase Crashlytics | 2027-01-15 |

Source: github.com/open-telemetry (opentelemetry-swift, opentelemetry-android), docs.expo.dev, docs.sentry.io. Detect the project's SDKs first; never add a second reporter beside an existing one.

## Procedure

1. **Pick one crash reporter.** Sentry *or* Crashlytics — one per app. Two reporters double the startup cost, double the privacy declarations, and split the crash-free number the rollout depends on. Sentry for cross-platform parity and source-map handling; Crashlytics where the app is already on Firebase.
2. **Draw the path.** `app → public ingest gateway → OTel Collector / Alloy (otlp or faro.receiver) → Tempo (traces) / Loki (logs) / Prometheus-Mimir (metrics)`.
   - The **gateway** is an HTTPS endpoint you own, in front of the Collector: TLS, per-app ingest token or none, rate limiting, size caps, drop-unknown-attributes. It is the only address the app knows.
   - **No backend credential in the app.** Tempo / Loki / Mimir tokens never ship; the app's only secret-ish value is a revocable ingest key, treated as public. A Grafana Cloud API token in `EXPO_PUBLIC_*`, `Info.plist` or `BuildConfig` is a blocker.
   - `otlp` (OTLP/HTTP) for OTel SDKs; `faro.receiver` for Grafana Faro. The Collector / Alloy config behind the gateway is **handed to `observability-engineer-<stack>`** — state the receiver and the expected attributes, write no config.
3. **Set the resource attributes** on every signal:

   | Attribute | Value |
   |---|---|
   | `service.name` | the app id, stable (`shop-mobile`) — one per platform build variant only if dashboards need it |
   | `service.version` | `version+build` exactly as the store build reports it; the join key to symbols |
   | `deployment.environment.name` | `production` / `staging` |
   | `os.name`, `os.version` | platform and OS version |
   | `device.model.identifier` | model id (`iPhone17,1`), **not** a device name or serial |
   | `session.id` | a per-launch random id; rotates on a new session; **never** the user id or a device id |

   Never put `user.email`, a name, a phone number, an advertising id or a raw device id in a resource attribute. A user id, if needed, is an opaque internal id attached to the crash report only.
4. **Batch and sample on device.** Batch spans / logs (size and a ≤ 30 s timer), export on a background queue, persist the batch to disk across a kill, and flush on backgrounding. Do not export per event. Head-sample traces (start at 1–10 % in production, 100 % in staging); **always keep crashes and error spans**. Send on Wi-Fi-or-metered-aware rules the product allows; drop, never block, when the queue is full. Exporting is off the UI thread (`CLAUDE.md` § Mobile code rules).
5. **Scrub PII before write.** Redact in the SDK's `beforeSend` / span processor / log filter: tokens, `Authorization` headers, query strings, request and response bodies, form fields, push tokens, email, phone, precise location. Allow-list HTTP attributes (`http.request.method`, `url.template`, `http.response.status_code`); log the **route template**, not the URL. Breadcrumbs follow the same filter. No `console.log` / `NSLog` / `Log.d` of a sensitive value — logs are telemetry.
6. **Log structurally.** Message templates + named fields, never string interpolation of values into the message; platform loggers per the reference (`os.Logger`, `android.util.Log` / Timber behind a release tree, a JS logger). Levels: `debug` stays off the wire in release.
7. **Declare it.** Every SDK added is a privacy-manifest and Data-safety item — hand the list to `mobile-shared-store-compliance`. Consent gating for non-essential analytics follows the same skill.
8. **Define the release-health signals** the rollout uses: crash-free users and sessions, ANR rate (Android vitals), hang rate (≥ 250 ms main-thread block, iOS), cold-start time — plus the threshold that halts a rollout (`mobile-shared-release`).

## What stays out of the app

A Collector config, Loki / Tempo / Mimir endpoint credentials, tail-sampling rules, retention, dashboards, alert rules. They are server-side, owned by `observability-engineer-<stack>`; the app contract is the gateway URL, the attribute set, and the sampling rate.

## Output

An observability setup or review: reporter, SDK per stack with pinned versions, gateway path, attribute set, batching / sampling values, scrubbing rules, declared SDKs, release-health thresholds, and the hand-off to `observability-engineer-<stack>` naming the receiver (`otlp` / `faro.receiver`). Findings use ids from [`references/audit-checks.md`](references/audit-checks.md) (`U1…`).

## References

- [`references/react-native.md`](references/react-native.md) — `expo-observe`, Embrace, Faro RN, Sentry, JS logging
- [`references/ios.md`](references/ios.md) — OTel Swift, MetricKit, `os.Logger`, crash reporter
- [`references/android.md`](references/android.md) — OTel Android agent, Crashlytics / Sentry, Timber, vitals
- [`references/audit-checks.md`](references/audit-checks.md) — fragment rows `U1…`
