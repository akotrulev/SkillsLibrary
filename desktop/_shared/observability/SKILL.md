---
name: observability
description: Use when a macOS or Windows desktop app needs crash reporting or OpenTelemetry telemetry to Grafana. Triggers "add crash reporting". Not for the Collector, Loki or Tempo backend (logs-traces).
disable-model-invocation: true
---

# Desktop — Observability

What a desktop app emits, how it leaves the machine, and what it must never carry. The backend half — Collector / Alloy, Tempo, Loki, Prometheus / Mimir, dashboards — is the `observability-engineer-<stack>` agents' (be-* plugins; see `observability/logs-traces-setup`). This skill ends at the **public ingest gateway**.

**The desktop difference.** The client is untrusted, often offline (laptops sleep, networks change), long-lived (days of uptime, many windows) and its binary is public. So: batch and sample in process, send through a gateway you control, put **no backend credential in the app**, scrub PII before anything is written, and flush on sleep, window close and quit. A failure to export never blocks or crashes the UI thread (`CLAUDE.md` § Desktop code rules).

## Version lane (verified 2026-11-15)

| Platform | Fact | Re-verify after |
|---|---|---|
| macOS | OTel Swift **2.6.0** (2026-10-01), floor `.macOS(.v12)`; MetricKit on macOS 12+ (27: `MetricManager` async sequences); `os.Logger` is the platform logger | 2027-01-15 |
| macOS crash reporter | Sentry Cocoa **9.34.0** (macOS 12+; `enableUncaughtNSExceptionReporting` needed; **no Session Replay** and no automatic app-start / screen-load transactions on macOS); Crashlytics is fully supported on macOS (Firebase 13.2.0) | 2027-01-15 |
| Windows | `OpenTelemetry` **1.21.0** — Microsoft's testing page recommends OpenTelemetry for new projects; App Insights only when the app is Azure-only. NuGet aggregators disagree on the newest exporter patch: read nuget.org before pinning | 2027-01-15 |
| Windows crash reporter | Sentry .NET **7.0.0** (WinUI and WPF integrations); WER is the platform: Partner Center health reports for Store MSIX, `windows.diagnosticServiceModule` manifest hook (Windows App SDK 2.5.1) | 2027-01-15 |

Source: github.com/open-telemetry (opentelemetry-swift, opentelemetry-dotnet), docs.sentry.io (Apple macOS guide, .NET WinUI / WPF), learn.microsoft.com (Testing WinUI). Detect the project's SDKs first; never add a second reporter beside an existing one. Platform detail: [`references/macos.md`](references/macos.md), [`references/windows.md`](references/windows.md); rows `U1…`: [`references/audit-checks.md`](references/audit-checks.md).

## Procedure

1. **Pick one crash reporter.** Sentry *or* Crashlytics (macOS) / WER-only (Windows LOB) — one per app. Two reporters double the startup cost, split the crash-free number and double the privacy declarations. Sentry is the default for macOS + Windows parity.
2. **Draw the path.** `app → public ingest gateway → OTel Collector / Alloy (otlp receiver) → Tempo (traces) / Loki (logs) / Prometheus-Mimir (metrics)`.
   - The **gateway** is an HTTPS endpoint you own, in front of the Collector: TLS, a revocable per-app ingest key, rate limiting, size caps, drop-unknown-attributes. It is the only address the app knows.
   - **No backend credential in the app.** Tempo / Loki / Mimir tokens never ship — not in `Info.plist`, `appsettings.json`, an `.xcconfig` or an `.resx`. The one secret-ish value is the ingest key, treated as public.
   - The Collector / Alloy config behind the gateway is **handed to `observability-engineer-<stack>`**: state the receiver (OTLP/HTTP) and the expected attributes, write no config.
3. **Set the resource attributes** on every signal:

   | Attribute | Value |
   |---|---|
   | `service.name` | the app id, stable (`shop-desktop-macos`, `shop-desktop-windows`) |
   | `service.version` | `version+build` as the release reports it; the join key to symbols and dSYM / PDB files |
   | `deployment.environment.name` | `production` / `staging` |
   | `os.type`, `os.version` | `darwin` / `windows` and the OS version |
   | `host.arch` | `arm64` / `amd64` |
   | `session.id` | a per-launch random id; **never** the user id, machine name or hardware id |

   Never put `user.email`, a name, a machine name, a Windows account name or a home-folder path in a resource attribute. `host.name` is left unset or a salted hash. A user id, if needed, is an opaque internal id attached to the crash report only.
4. **Batch and sample in process.** Batch spans / logs (size and a ≤ 30 s timer), export on a background queue, persist the batch across a kill, and flush on window close, sleep and quit (`applicationWillTerminate`, `NSWorkspace.willSleepNotification`, `Application.Exit` / `AppWindow.Closing`). Head-sample traces (1–10 % in production, 100 % in staging); **always keep crashes and error spans**. Drop, never block, when the queue is full. A paused network is a normal state, not an error banner.
5. **Scrub PII before write.** Redact in the SDK's `beforeSend` / `SetBeforeSend`, a span processor or a log filter: tokens, `Authorization` headers, query strings, request and response bodies, document contents and **file paths** (they carry the user name), email, phone. Allow-list HTTP attributes (`http.request.method`, `url.template`, `http.response.status_code`); log the **route template**, not the URL. Breadcrumbs follow the same filter.
6. **Log structurally.** `os.Logger` (macOS) and `ILogger` (Windows) with message templates and named fields, never string interpolation into the template; no `print` / `NSLog` / `Console.WriteLine` of a value. Levels: `debug` stays off the wire in release; `privacy: .public` is never put on a secret.
7. **Declare it.** Every SDK added is a privacy-manifest and store-listing item (Mac App Store privacy details, Microsoft Store listing): hand the list to `desktop/_shared/distribution`. Non-essential analytics follow the user's consent and a settings switch.
8. **Define the release-health signals** an update rollout uses: crash-free sessions, hang rate (main thread busy > 250 ms on macOS; UI thread unresponsive on Windows), cold-start time, update-failure rate; plus the threshold that halts rollout (`desktop/_shared/distribution`).

## What stays out of the app

A Collector config, backend endpoint credentials, tail-sampling rules, retention, dashboards, alert rules. They are server-side, owned by `observability-engineer-<stack>`; the app contract is the gateway URL, the attribute set and the sampling rate.

## Output

An observability setup or review: reporter, SDK per platform with pinned versions, gateway path, attribute set, batching / sampling values, scrubbing rules, flush points, declared SDKs, release-health thresholds, and the hand-off to `observability-engineer-<stack>` naming the receiver. Findings use ids from [`references/audit-checks.md`](references/audit-checks.md) (`U1…`).

## References

- [`references/macos.md`](references/macos.md) — OTel Swift, `os.Logger`, MetricKit, Sentry Cocoa, hang detection
- [`references/windows.md`](references/windows.md) — OpenTelemetry .NET in a desktop process, `ILogger`, Sentry .NET, WER
- [`references/audit-checks.md`](references/audit-checks.md) — fragment rows `U1…`
