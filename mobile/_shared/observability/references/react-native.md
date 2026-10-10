# React Native / Expo telemetry

There is **no official OpenTelemetry React Native SDK** (verified 2026-10-10; re-verify 2026-12-31). Pick one lane, and keep the crash reporter singular.

| Option | What it is | Maturity | Use when |
|---|---|---|---|
| **Sentry RN** 8.30 (`@sentry/react-native`) | Crashes (JS + native), performance, breadcrumbs, source-map upload via its Expo plugin / `sentry-cli` | Stable, widely used | Default crash reporter for RN |
| **`expo-observe` OTel export** | Expo's observability package exporting OTel signals from an Expo app | Verify current status at docs.expo.dev before adopting | Expo-managed app that wants OTLP without a vendor SDK |
| **Embrace RN** 7.2 | Mobile-specific observability SDK (sessions, ANR / hangs, network) with OTel-based export | Stable vendor SDK | Session-centric analysis; accepts a vendor SDK |
| **Grafana Faro RN** | Faro web SDK port for RN, ships to Alloy `faro.receiver` | **Experimental** — never the only crash reporter | Teams already on Grafana who accept experimental status |

## Rules

- **One crash reporter.** Sentry *or* an alternative that reports crashes; not Sentry plus Embrace plus Faro all capturing.
- Native crashes need the native SDK initialised in the native entry (Expo config plugin) **and** Hermes source maps uploaded per release (`mobile-shared-release`, `references/eas.md`). `service.version` / `release` = `version+build`; `dist` = the build number or OTA update id, so an OTA's JS errors symbolicate against the right map.
- Initialise telemetry **once**, first thing in the root layout / `index`, outside any component; no module-level mutable state beyond that single client (`CLAUDE.md` § Backend code rules applies in spirit: construct once, inject).
- Endpoint is the **ingest gateway URL** — a public, non-secret value. It may be an `EXPO_PUBLIC_*` var; a backend token never may (`mobile-shared-security`).
- Scrub in `beforeSend` / `beforeBreadcrumb` (Sentry) or the span / log processor: drop `Authorization`, cookies, request and response bodies, form values; replace URLs with route templates; disable automatic capture of console arguments in production.
- Sample: `tracesSampleRate` 0.05–0.1 production; errors always 1.0; `replaysSessionSampleRate` (session replay) **off** unless privacy review passes — replay records the screen.
- Navigation tracing: Expo Router instrumentation (`Sentry.reactNavigationIntegration`) to name transactions by route template.
- Logging: a small logger wrapper over the reporter's breadcrumb / log API; `console.*` stripped in production builds (Babel `transform-remove-console`) so nothing sensitive reaches logcat / Console.app.
- Offline: the SDKs queue to disk; do not build a second queue.
- Privacy: each SDK is a privacy-manifest and Data-safety entry (`mobile-shared-store-compliance`).

## Handing off

State to `observability-engineer-<stack>`: receiver (`otlp` HTTP or `faro.receiver`), expected resource attributes, sampling, ingest path. Write no Collector config.
