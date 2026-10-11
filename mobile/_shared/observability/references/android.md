# Android telemetry

## Signals

| Signal | Source | Notes |
|---|---|---|
| Crashes, ANRs | **Firebase Crashlytics** or **Sentry Android** — one | Crashlytics needs the Gradle plugin for mapping upload |
| Traces, metrics, logs | **OpenTelemetry Android agent 1.7.0** (`io.opentelemetry.android`) | **Maturity, both readings:** the *agent API is stable*; the *instrumentations (activity, fragment, ANR, crash, network, slow-render) are alpha.* The BOM is shown as `1.7.0` in one official page and `1.7.0-alpha` in another; modules carry their own `1.0.x-alpha` versions. Pin exact versions, read release notes before every bump. Verified 2026-10-10; re-verify 2026-12-31 |
| Platform vitals | Play Console Android vitals: crash 1.09 % (8 % per model), user-perceived ANR 0.47 % (8 % per model), excessive partial wake locks 5 % (enforced 2026-03-01); slow start: cold ≥ 5 s, warm ≥ 2 s, hot ≥ 1.5 s | Console-side evidence, not repo-provable |
| On-device log | `android.util.Log` behind **Timber** (re-verify current) or a thin logger; a release tree that forwards `warn` / `error` only | `Log.d` of a sensitive value is a leak on a debuggable device |

## Rules

- **One crash reporter.** The OTel agent's crash instrumentation is alpha — it is not the crash reporter of record; keep Crashlytics or Sentry as that, and let OTel carry traces, metrics and non-fatal logs.
- Install the agent in `Application.onCreate` through `OpenTelemetryRum.builder(...)`, once, with dispatchers injected where exporters are built; no `GlobalScope`.
- **Resource attributes:** `os.name = "Android"`, `os.version`, `os.description`, `device.model.identifier` (`Build.MODEL`), `service.version = "versionName+versionCode"`, `session.id` — the agent's session id; do not substitute `ANDROID_ID`.
- Batching: the agent's batch exporters persist to disk (disk buffering) and respect `Doze`; configure size and timer, flush on `ProcessLifecycleOwner` background. Sampling: head-sample production traces 1–10 %, keep errors.
- Network instrumentation: allow-list attributes, route templates only, no bodies or query strings; add the `OkHttp` interceptor, not a hand-written one.
- Disable instrumentations you do not use — each alpha module is startup cost and an upgrade risk.
- Scrub before write: crash `setCustomKey` / OTel attributes carry no PII; Crashlytics collection is opt-in where the product needs consent (`setCrashlyticsCollectionEnabled`).
- Compose / Views: name screen spans by route, not by Activity class when the app is single-activity.
- Data safety form: each SDK adds declarations — hand off to `mobile-<stack>:store-compliance`.
- Mapping upload per `versionCode`: `mobile-<stack>:release`, `references/gradle-play.md`.
- Hand off to `observability-engineer-<stack>`: receiver `otlp`, attributes, sampling. No Collector config here.
