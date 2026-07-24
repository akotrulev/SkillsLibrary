---
name: qa-performance-shared
description: Cross-stack reference for performance / load testing — workload models (smoke / average / stress / spike / soak / capacity), SLO-shaped thresholds, test data seeding & cleanup, environment policy, observability correlation, CI integration patterns, reporting, and the perf-suite review checklist. Load alongside one of `qa/<stack>/skills/performance/{k6/typescript,nbomber/dotnet,gatling/java}` when designing or authoring perf tests. Triggers (always alongside the tool sibling) "design a load test", "which workload model do we need", "set performance thresholds from our SLO", "review our perf suite". Do NOT load standalone to write tool-specific code — pair it with the tool sibling.
---

# QA — Performance Testing (Shared)

Cross-stack concepts shared by `qa/<stack>/skills/performance/{k6/typescript,nbomber/dotnet,gatling/java}`. The tool siblings carry the per-tool DSL and recipes; this skill carries the workload modelling, SLO-tied thresholds, environment policy, and reporting habits that apply regardless of tool.

## Pick the tool

| Tool | Sibling | When |
|---|---|---|
| **k6** (Grafana k6) | `qa/typescript/skills/performance/k6` | Default for new perf work. JS scripts, single binary, great OSS + Grafana Cloud story. |
| **NBomber** | `qa/dotnet/skills/performance/nbomber` | .NET-only teams that prefer to write tests in C#. |
| **Gatling** | `qa/java/skills/performance/gatling` | JVM-heavy teams that want a Scala / Java DSL. |
| Apache JMeter | — | Legacy. Avoid for new work. |

For this library, **k6 is the default**. Reach for NBomber when the team strongly prefers C# and the test is .NET-resident; Gatling for JVM-heavy teams.

## Workload models — more important than tool choice

| Model | Asks | Typical config |
|---|---|---|
| **Smoke** | "Does it work at all under any load?" | 1–5 VUs, 1 minute, after every deploy |
| **Average load** | "Does it meet SLOs at expected steady-state traffic?" | Real peak RPS, 5–30 min |
| **Stress** | "Where does it break?" | Ramp past peak until errors / latency cross threshold |
| **Spike** | "What happens on a sudden 10x?" | Step from low to high in seconds, hold briefly, drop back |
| **Soak / endurance** | "Are there leaks / degradation under prolonged load?" | Peak load held for 2–24 hours |
| **Capacity** | "What's the max sustainable RPS at this footprint?" | Closed-loop or stepped ramp, find the knee |

**Name the model in every test and every report.** "I ran a load test" without saying which model is useless to read.

## Designing a test

1. **Pick the model** above.
2. **Pick the SLO to validate**: latency p95 / p99, error %, throughput. Source: `qa/manual/quality-metrics`.
3. **Workload mix** — what % of traffic is each endpoint? (Prod analytics tell you. Synthetic 100% on the slowest endpoint is a worst-case stress, not "load".)
4. **Test data shape** — seeded users / tenants / orders that the test reads / writes; cleaned up afterward.
5. **Ramp profile** — never start at full load; warm up JIT / connection pool / cache.
6. **Thresholds** — pass/fail gates. Tests **fail the build** when SLOs aren't met. Tool-specific syntax in the sibling skills.

## SLO-shaped thresholds (the most important habit)

The point of perf tests is **to fail the build when an SLO is at risk**. Every test has a thresholds block — those thresholds match the SLOs defined in `qa/manual/quality-metrics`. Per-route, not aggregated.

| SLO | Threshold concept |
|---|---|
| 99.9% availability | `error_rate < 0.001` |
| p95 latency ≤ 300ms | `http_req_duration p95 < 300` |
| p99 latency ≤ 800ms | `http_req_duration p99 < 800` |

A test with no thresholds is a "draw graphs" test — useful in dev; not a CI gate.

**Per-route tags.** Aggregating across endpoints averages a fast endpoint with a slow one and hides regressions. Tag every request (`GET /orders/{id}`, `POST /checkout`) and assert per-tag.

## Open-loop vs closed-loop

| Mode | When | k6 executor | NBomber | Gatling |
|---|---|---|---|---|
| **Open-loop** (arrival-rate) | "We want N RPS regardless of VU performance" | `constant-arrival-rate` / `ramping-arrival-rate` | `Simulation.Inject` / `RampingInject` | `constantUsersPerSec` / `rampUsersPerSec` |
| **Closed-loop** (VUs) | "We want N concurrent users; system gets what it can" | `constant-vus` / `ramping-vus` | `Simulation.KeepConstant` / `RampingConstant` | `atOnceUsers` / `rampUsers` |

For RPS-target tests, **always open-loop** — closed-loop hides backpressure (slower service → fewer iterations → lower realised load).

## Test data & cleanup

- Use **seeded users and resources** specifically marked as perf-fixture (`tenant=perf`, `customer=perf-XXX`).
- The setup phase creates fixtures; the teardown phase drops them — never leak fixtures into prod-style data.
- Don't share fixtures across concurrent test runs — they collide; namespace by run id.
- **Never run write-heavy tests against production**; perf tests live in dedicated environments (staging, perf).

## Environment policy

| Environment | When |
|---|---|
| **Perf-dedicated** (clone of prod sized to prod) | The right answer. Best signal-to-noise. |
| **Staging** | Acceptable for low-volume regression runs; signals are noisier (shared with feature work). |
| **Prod** | **Read-only smoke** OK with explicit permission; never write-heavy or beyond peak. |

Document **which environment** every test targets. A "load test passed" without that context is meaningless.

## CI integration patterns

Two viable flows (combine both):

1. **Smoke on every PR** — 1-minute smoke against staging, verifies SLO threshold on a happy-path endpoint; fast feedback, low cost.
2. **Full average / spike / soak on release** — scheduled or release-triggered; results published as artifacts + dashboard.

Wire perf gates into the same `qa/cicd/<stack>/skills/ci-pipelines/<ci>` pipelines as functional tests.

## Observability during the test

The perf test by itself only knows what the **caller** sees. To diagnose, correlate with server-side metrics:

- **Pre-test:** snapshot baseline metrics (CPU, memory, DB pool, GC).
- **During-test:** watch the service's RED dashboard (`observability/grafana-dashboards`).
- **Post-test:** capture the time-window in the dashboard for the report.

If client p95 says 800ms and server p95 says 50ms, the bottleneck is the network / proxy / client setup — not the service. Always capture both sides.

## Reporting

Every release run produces a report with:

1. **Workload model + duration + environment**
2. **SLO target** + actual measurement (per route)
3. **Threshold pass / fail**
4. **Latency histogram + RPS chart** screenshots (or link to Grafana)
5. **Server-side resource view** (CPU, memory, DB, queue depth)
6. **Notable deltas** vs prior run

For SLO regression, attach the **diff vs baseline** — leadership reads deltas, not absolutes.

## Global rules (all tools)

- One **workload model** named per test; smoke / average / stress / spike / soak / capacity.
- **Thresholds tied to SLOs**, not "looks reasonable" numbers.
- **Per-route tagging** and per-route thresholds; never aggregate across endpoints.
- Test data **seeded + cleaned up**, namespaced per run.
- Tests run against a **dedicated perf or staging** environment, not prod (read-only smoke excepted).
- **Pin tool versions** (`grafana/k6:0.49.0` not `:latest`; `NBomber 6.x`; `gatling-charts-highcharts-bundle:3.11.x`).
- Auth via env vars / pipeline secrets, never hardcoded.
- CI integration: smoke on PR, full on release / schedule.
- Capture **both client and server side** for diagnosis.
- Each release run produces a report attached to the release notes.

## What NOT to do (all tools)

- No load tests without thresholds — that's just a graph.
- No averaging latency across endpoints — tag and threshold per route.
- No closed-loop VU tests when you want a target RPS — open-loop (`arrival-rate`) is right.
- No tests against prod that write data.
- No skipping warm-up / ramp — cold-start latency contaminates the average.
- No infinite ramps "until it breaks" without an exit condition — bound max VUs and duration.
- No hardcoded auth tokens / URLs.
- No reusing the same fixture id across parallel runs.
- No `--vus 10000` "to be safe" — preallocated VUs cost memory and bias results.
- No leaving the perf test in a separate repo no one reviews — keep it next to the service.

## Reviewing a performance suite

Review checklist for an authored perf suite (any tool). Report findings in the library's standard review table (severity / location / issue / suggested fix); point to the fix, don't rewrite.

**Blockers** — the suite's numbers cannot be trusted:
- A scenario without a named workload model, or closed-loop VUs where the question is "does it hold at N RPS" (open-loop / arrival-rate is required for RPS targets).
- No thresholds, or thresholds not traceable to an SLO — a script that prints numbers is not a test.
- Sync-over-async (or any blocking call) in the measured path — it corrupts the latency it reports.
- Token/auth acquisition, data generation, or connection setup **inside** the measured step instead of before it.
- Shared mutable test data across virtual users (same row contended by every VU).
- Targets an environment not authorized/sized for load, or a test that writes to prod.

**Majors** — results are misleading or the suite won't survive CI:
- Warm-up/ramp not excluded from the measured window.
- Latency aggregated across routes instead of tagged + thresholded per route.
- No smoke profile, or the full profile wired into the PR lane (smoke on PR, full on schedule/release).
- Unbounded ramps with no max-VU/duration exit condition.
- No baseline recorded, or no client-vs-server correlation captured (can't tell service from network).
- Seeded data not namespaced per run / not cleaned up.

**Minors** — quality drift:
- Unpinned tool versions; hardcoded URLs or tokens; magic numbers for rates/durations with no comment tying them to the traffic profile; report missing the deltas-vs-baseline section.

A clean review = no blocker or major rows after fixes, plus a per-scenario PASS/FAIL table against the phase-1 thresholds.

## When NOT to use any of these tools

- Functional behavior tests → `qa/<stack>/skills/api-test-author/generator/<stack>` / `qa/<stack>/skills/ui-test-author/<stack>`
- Unit / microbenchmarks (loop bodies, parsing speed) → BenchmarkDotNet (.NET) / JMH (Java) / Vitest bench (TS)
- Production-side observability → `observability/grafana-dashboards`
- Defining the SLO itself → `qa/manual/quality-metrics`

## Handoffs

- k6 / TypeScript recipes → `qa/typescript/skills/performance/k6`
- NBomber / .NET recipes → `qa/dotnet/skills/performance/nbomber`
- Gatling / Java recipes → `qa/java/skills/performance/gatling`
- SLO targets the test validates → `qa/manual/quality-metrics`
- Grafana dashboards for server-side correlation → `observability/grafana-dashboards`
- LogQL / PromQL for queries during the test → `observability/logql-promql`
- Test strategy that calls out where perf testing fits → `qa/manual/test-strategy`
- Pipeline integration → `qa/cicd/<stack>/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for perf reports → `qa/reporting/<stack>/skills/allure-reporting/<stack>`
- Bug filings discovered during perf → `qa/manual/bug-report-writer`
