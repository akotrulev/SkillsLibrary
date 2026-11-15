# Observability — macOS reference

Facts from `docs/research/012-desktop-plugins/macos.md` §7 (verified 2026-11-15). Package APIs below are the documented shapes of the pinned versions; re-read each library's README before pinning, since Swift OTel configuration has moved between minors.

## OpenTelemetry Swift 2.6.0

Add `opentelemetry-swift` through SPM (floor `.macOS(.v12)`); import only the products used (`OpenTelemetryApi`, `OpenTelemetrySdk`, `OpenTelemetryProtocolExporterHttp`, `StdoutExporter` for Debug). Export is **OTLP/HTTP** to the gateway, never gRPC to a backend.

```swift
enum Telemetry {
    static func start(gateway: URL, ingestKey: String, version: String) {
        let resource = Resource(attributes: [
            "service.name": .string("shop-desktop-macos"),
            "service.version": .string(version),
            "deployment.environment.name": .string("production"),
            "session.id": .string(UUID().uuidString)
        ])
        let exporter = OtlpHttpTraceExporter(
            endpoint: gateway.appendingPathComponent("v1/traces"),
            config: OtlpConfiguration(headers: [("x-ingest-key", ingestKey)])
        )
        let processor = BatchSpanProcessor(spanExporter: exporter, scheduleDelay: 5, maxQueueSize: 2048)
        let provider = TracerProviderBuilder()
            .with(resource: resource)
            .with(sampler: ParentBasedSampler(root: TraceIdRatioBasedSampler(ratio: 0.05)))
            .add(spanProcessor: processor)
            .build()
        OpenTelemetry.registerTracerProvider(tracerProvider: provider)
    }
}
```

- `start` runs from `App.init` on a background `Task`, never blocking the main actor; the processor exports on its own queue.
- The `x-ingest-key` header is the revocable ingest key (public by nature); a Grafana or Tempo token never appears.
- Sampling is a ratio sampler under `ParentBased`; crash and error spans are kept by the reporter, not by this sampler.
- Flush on `NSApplication.willTerminateNotification` and `NSWorkspace.willSleepNotification` (`provider.forceFlush()`); a long-lived app also flushes when the last window closes if it keeps running.
- Network changes (`NWPathMonitor`): export fails quietly and retries; a dropped batch is counted, not shown.
- Metrics: one counter or histogram per business event, named in the task's `As built` note; the metrics reader exports on an interval, delta temporality when the gateway side asks for it.
- Span names are operation names (`document.save`), never URLs with ids; attributes use `url.template`.

## `os.Logger`

```swift
extension Logger {
    static let sync = Logger(subsystem: "com.example.app", category: "sync")
}

Logger.sync.info("Sync finished: \(count, privacy: .public) items")
Logger.sync.error("Sync failed for account \(accountId, privacy: .private): \(error.localizedDescription)")
```

- Subsystem is the bundle id, category the feature. Interpolations default to private; `.public` is for counts, enums and ids that are not personal, never for a token, email or path.
- `os.Logger` stays on-device (unified logging, Console.app). What reaches Loki is a **deliberate** export through the OTel logs bridge or Sentry breadcrumbs, filtered by the same scrubbing rules.
- No `print`, `NSLog` or `dump` of a value in release code.

## MetricKit

MetricKit works on macOS 12+; diagnostics arrive immediately there. macOS 27 adds `MetricManager` delivering `MetricReport` / `DiagnosticReport` as async sequences, with `HangDiagnostic`, `CrashDiagnostic` and `HangTimeMetric`.

- On macOS 12–26 subscribe with `MXMetricManagerSubscriber`; on 27 consume the async sequences. The deployment target decides the branch (no up-levelling).
- Forward diagnostics to the reporter or the OTel logs pipeline **after** the scrub step: call-stack trees carry no user data, but attached metadata may.
- A hang is the main run loop busy longer than 250 ms (Apple's tools' default); the spinning wait cursor is the user-visible symptom. Hang rate is a release-health signal.

## Sentry Cocoa 9.34.0

```swift
SentrySDK.start { options in
    options.dsn = Self.dsn
    options.releaseName = "shop-desktop-macos@\(version)+\(build)"
    options.sendDefaultPii = false
    options.tracesSampleRate = 0.05
    options.enableUncaughtNSExceptionReporting = true
    options.beforeSend = Scrubber.scrub
}
```

- `enableUncaughtNSExceptionReporting = true` is required on macOS or an uncaught `NSException` from AppKit is lost.
- No Session Replay and no automatic app-start or screen-load transactions on macOS (macOS 12+ from 9.25.0): do not promise either in a plan; add manual spans for startup.
- Upload dSYMs from the notarized build in CI (`sentry-cli`); the auth token for the upload lives in the CI secret store, never the repo. Release steps belong to `desktop/_shared/distribution`.
- The DSN is public by design but the project enforces an allowed-domains rule on the Sentry side.
- Crashlytics on macOS (Firebase Apple SDK 13.2.0) is the alternative when the app is already on Firebase; Performance Monitoring is not listed for macOS.

## Not in the app

The Collector, the gateway's rate limits, retention and dashboards: `observability-engineer-<stack>`.
