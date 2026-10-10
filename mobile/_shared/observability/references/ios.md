# iOS telemetry

## Signals

| Signal | Source | Notes |
|---|---|---|
| Crashes, hangs | **MetricKit** (`MXMetricManager`, `MXCrashDiagnostic`, `MXHangDiagnostic`) and the crash reporter (Sentry or Crashlytics) | MetricKit delivers aggregated payloads at most daily — good for trends, not for a live rollout gate. A hang is the main thread blocked ≥ 250 ms |
| Traces, metrics | **OTel Swift 2.5.1** (`opentelemetry-swift`) — verified 2026-10-10, re-verify 2027-01-15 | Swift 6 mode: keep exporters off `@MainActor`; export on a background executor |
| Logs | **`os.Logger`** (subsystem + category) for on-device; forward selected records through the OTel log exporter | `os.Logger` is the only logger (`CLAUDE.md` § Mobile); `print` / `NSLog` are not |
| Xcode Organizer | crash and energy reports, hang rate | App Store Connect side; console-only evidence |

## Rules

- **One crash reporter** (Sentry or Crashlytics). MetricKit is a platform source, not a second reporter; subscribe once, forward the payload to the same pipeline.
- Initialise once in the `App` initializer; a single `Telemetry` value injected, no singleton with mutable state.
- **Resource attributes** from `ProcessInfo` / `UIDevice`: `os.name = "iOS"`, `os.version`, `device.model.identifier` (the `utsname` machine string, e.g. `iPhone17,1`), `service.version = "<short>+<build>"`, `session.id` random per launch.
- **`os.Logger` privacy:** interpolated values are redacted by default (`<private>`); never mark `.public` on a token, email or identifier. Telemetry forwarded off-device is filtered separately — `os.Logger` redaction does not apply once the value is exported.
- Batch with `BatchSpanProcessor` / `BatchLogRecordProcessor`; persist to disk where the exporter supports it (OTel Swift persistence exporter); flush on `scenePhase == .background`, with `beginBackgroundTask` bounding the flush.
- URLSession instrumentation: allow-list attributes, drop query strings and bodies; name spans by route template.
- Privacy manifest: add the Required Reason API entries these SDKs trigger (`UserDefaults`, file timestamp, boot time); list the collected data types; ATT only when tracking, which telemetry normally is not (`mobile-shared-store-compliance`).
- Symbols: dSYM upload per archive (`mobile-shared-release`, `references/fastlane.md` / `xcode-cloud.md`).
