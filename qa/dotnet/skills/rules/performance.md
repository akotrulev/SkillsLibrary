---
paths:
  - "**/*{PerfTests,PerformanceTests,LoadTests}/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): performance. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its NBomber suites. -->

# NBomber load-test standards

The tag after a rule is the severity a review reports: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. A load suite is a console app, so the core NUnit rules do not load here.

- A console app, one scenario per file under `Scenarios/`, `Program.cs` only registers and runs; no NUnit `[Test]` wrapper and no NUnit or test-SDK package. *major*
- Open-loop `Inject` / `RampingInject` by default; `KeepConstant` only to model a fixed concurrency cap, never for an RPS target. *major*
- One `HttpClient` per scenario from `HttpClientFactory.Create()`, sent with `Http.CreateRequest` + `Http.Send` so metrics land; never `new HttpClient()` per iteration, never a second HTTP stack. Reuse the API suite's typed clients when composing with it. *major*
- `Step.Run` only to time each hop of a multi-hop scenario. *minor*
- Every scenario has SLA-derived thresholds (p95/p99 latency, error rate), enforced with `WithThresholds` and a non-zero exit on breach; a run with none is unasserted. *major*
- Load profile, base URL and tokens come from `appsettings.<env>.json` and environment variables, never hardcoded or logged. *blocker for a secret*
- Never against production; state-changing load only on staging or a dedicated environment, with ids namespaced per run. *blocker*
- Keep the default warm-up for production-shape runs. *minor*
- `DataFeed.Constant` for per-user identity, with at least as many items as copies; `ctx.Random`, never `Random.Shared`, for reproducible data. *minor*
- Async all the way in scenario bodies, no `.Result` or `.Wait()`; no `Console.WriteLine` on the hot path. *blocker; minor for logging*
- Reports go to a report folder published as a CI artifact, never the repo root. *minor*
