---
name: observability-grafana-dashboards
description: Use when the user asks to design or build a Grafana dashboard — panel layout, queries, alerts, RED / USE / Four-Golden-Signals methods, exemplars (logs ↔ traces), variables / templating. Triggers: "build a dashboard for service X", "what panels should service Y have", "RED dashboard", "wire log → trace navigation", "design alerting rules". Do NOT use for instrumenting code (use `observability/opentelemetry-{dotnet,java,node}`) or for the underlying query syntax (use `observability/logql-promql`).
---

# Observability — Grafana Dashboards

Designs and builds Grafana dashboards on top of the library's standard stack (Loki for logs, Prometheus / Mimir for metrics, Tempo for traces) plus the OTel pipelines wired up in `observability/opentelemetry-{stack}`. Standardizes on **RED for services**, **USE for resources**, and **Four Golden Signals for SRE-style overviews**. Exemplars make every panel jump to the underlying trace.

## When to use

- New service needs a default dashboard
- Existing dashboard sprawls into 80 panels and no one knows which to look at
- Adding alerts on key metrics
- Wiring trace exemplars / log links
- Designing a per-team or per-environment overview dashboard

## When NOT to use

- Instrumenting code → `observability/opentelemetry-{dotnet,java,node}`
- Writing the LogQL / PromQL itself → `observability/logql-promql`
- Designing the SLO / SLI math → `qa/_shared/quality-metrics` for product-side SLIs; this skill for the panel

## Inputs needed

1. **Service(s)** the dashboard covers
2. **Data sources** available — Prometheus / Mimir, Loki, Tempo, and which are wired with **exemplars** + **derived fields**
3. **Audience** — engineers on-call, product leads, executives — drives detail
4. **SLO targets** if any (e.g., 99.9% availability, p95 < 200ms)

## Pick the method

| Method | When | Top panels |
|---|---|---|
| **RED** (Rate, Errors, Duration) | Service-level dashboards | Requests/sec, error %, latency (p50/p95/p99) |
| **USE** (Utilization, Saturation, Errors) | Resources (CPU, memory, queues, connection pools) | Utilization %, queue depth, error count |
| **Four Golden Signals** (Latency, Traffic, Errors, Saturation) | SRE overview / on-call | Same as RED + Saturation row |

RED is the default for the service dashboards in this library. Add USE rows when the service has known resource bottlenecks (DB pool, message queue).

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Header row: stat panels (current request rate, current error %, p99, alerts) │
├──────────────────────────────────────────────────────────────────────────────┤
│ Rate (RPS by route)        │ Errors (% by route)                              │
├────────────────────────────┼──────────────────────────────────────────────────┤
│ Duration (p50/p95/p99)     │ Slow routes (top-N table)                        │
├────────────────────────────┴──────────────────────────────────────────────────┤
│ USE row: CPU / memory / DB pool / message queue depth                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Logs panel: error-level logs filtered by service, with link to trace          │
├──────────────────────────────────────────────────────────────────────────────┤
│ Trace exemplars: link from latency histogram to a trace in Tempo              │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Top row stat panels show current state — answer "is anything on fire" in 2 seconds
- Time-series panels for trends
- Tables for top-N (slowest routes, noisiest log lines)
- Logs panel filtered down at the row level

## Variables / templating

Make every dashboard usable across environments and services with variables:

```
$env       → dev / staging / prod         (label_values(env))
$service   → orders / payments / ...      (label_values(service))
$instance  → individual pod / task        (label_values({service="$service"}, instance))
$route     → /orders/{id}, ...            (label_values(http_route))
```

Variables let one dashboard JSON serve every team. Hardcoded `service="orders-api"` in queries is an anti-pattern.

## Exemplars: link metrics → traces

When Prometheus / Mimir is fed with exemplars from OTel (it is, in the pipelines from `observability/opentelemetry-{stack}`), latency histograms attach a `trace_id` per sample. Grafana renders dots on the histogram; clicking jumps to the trace in Tempo.

To enable:

1. Prometheus data source has `Exemplars` configured with a query template using `trace_id`
2. Tempo data source linked via the exemplar config
3. Panel uses a histogram query (`histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket[5m])))`) — exemplars surface automatically

Without exemplars, latency spikes are observable but not investigable. Always wire them.

## Logs → traces via derived fields

In the Loki data source config, define **derived fields** that turn `traceId="..."` (or `trace_id`) in a log line into a clickable link:

```
Field name: trace_id
Regex:      "traceId":"(\w+)"
URL:        ${__value.raw}
Datasource: Tempo
```

Now every error log → one click → the failing trace. This is the single biggest force-multiplier in the stack.

## Standard RED dashboard (template)

For every service, generate a dashboard with these panels (queries here are illustrative; see `observability/logql-promql` for the canonical query syntax):

| Panel | Query (conceptual) | Type |
|---|---|---|
| Requests / sec (by route) | `sum by (http_route) (rate(http_server_requests_total{service="$service",env="$env"}[5m]))` | Time-series |
| Error rate % (by route) | `sum by (http_route) (rate(http_server_requests_total{status=~"5.."}[5m])) / sum by (http_route) (rate(http_server_requests_total[5m])) * 100` | Time-series |
| Latency p95 / p99 | `histogram_quantile(0.95, ...)`, `histogram_quantile(0.99, ...)` | Time-series |
| Top slow routes | sort by p95 desc, limit 10 | Table |
| Active alerts | `ALERTS{service="$service",env="$env"}` | Stat |
| Recent errors (logs) | `{service="$service",env="$env"} \|= "ERROR"` | Logs |

Save the JSON model in source control under `observability/dashboards/<service>.json` — dashboards are code.

## Alerts

Two flavors:

1. **Grafana-managed alerts** — defined in dashboard JSON or unified alerting; ride with the dashboard
2. **Prometheus / Mimir rules** — defined in YAML, evaluated by the rule engine; survives dashboard changes; preferred for SLO-tied alerts

Recommendation: **SLO-tied alerts as Prometheus rules** (review-able as YAML in Git); **threshold-tied tactical alerts as Grafana-managed** so the on-call team can adjust them quickly.

### Alert design

| Symptom | Alert |
|---|---|
| **Error budget burn** | Burn-rate alerts (fast burn over 1h, slow burn over 6h — per Google's SRE workbook) |
| **High-latency** | p95 > threshold for 5m+ |
| **Drop in traffic** | Rate falls > X% YoY at this time-of-day — anomaly detection |
| **Specific resource exhaustion** | DB pool saturation, queue depth above threshold |

Avoid:
- **Alerts on individual symptoms** of a known root cause (e.g., one alert per dependent service when the upstream alert fires anyway)
- **Alerts that don't pass an action test** — if there's no action a human can take, it's noise

## Annotations

Annotate deploys, incidents, and feature-flag flips on dashboards. Sources:

- Deploy webhook from the pipeline → Grafana annotation API
- Incident creation in PagerDuty / Opsgenie → annotation
- Feature flag service → annotation

A dashboard that shows "p99 spike at 14:32, deploy at 14:30" is a one-glance root-cause hint.

## Cardinality budget

Loki labels and Prometheus labels share the same trap: high-cardinality labels (per-request IDs, free-form text) tank the store. The OTel pipeline already excludes these; the dashboard's queries must not reintroduce them in `by (...)` clauses.

Safe `by`/`group by` dimensions: `service`, `env`, `http_route`, `http_method`, `status`, `instance` (when small N). Unsafe: `user_id`, `order_id`, `trace_id`, `url` (raw).

## Rules

- **One method per dashboard** — RED for services, USE for resources, Four-Golden-Signals for SRE overviews
- **Header row stat panels** answer "is it on fire" at a glance
- **Variables** for env / service / route so one dashboard serves all
- **Exemplars wired** → click latency to jump to trace
- **Loki derived fields** → click log to jump to trace
- **Dashboards in source control** as JSON; reviewed in PRs
- **Alerts in source control** as Prometheus / Mimir YAML rules where they're SLO-tied
- **Annotations** for deploys, incidents, flags
- **Cardinality budget** respected — no per-request IDs in `by` clauses
- **Naming consistent** — service, route, status as label names match the OTel semantic conventions

## What NOT to do

- No "everything" dashboard — split per service / per team
- No hardcoded `service="..."` in queries — use `$service` variable
- No alerts on every metric — alert on **symptoms users feel**, not internal counters
- No `by (user_id)` / `by (order_id)` / `by (trace_id)` — cardinality explosion
- No 80-panel page — readers won't read past the fold
- No screenshots committed to docs instead of dashboard JSON — JSON is the source of truth
- No alerts without runbooks linked
- No alerts that fire continuously below threshold ("warning, p99 is sometimes above 200ms") — page on actionable conditions
- No dashboards built by clicking through the UI and never exported — they die when someone deletes them

## Generation steps

1. Confirm service, audience, method (RED default), and SLO targets.
2. Create variables: `$env`, `$service`, optional `$instance` / `$route`.
3. Add the standard RED panel set (rate / errors / latency / top slow / alerts / logs).
4. Wire exemplars on the latency histogram → Tempo.
5. Wire Loki derived fields on `trace_id` → Tempo.
6. Add annotations from deploys + incidents.
7. Add alerts — SLO-tied as Prometheus rules (Git), threshold-tactical as Grafana-managed.
8. Export the dashboard JSON, commit to `observability/dashboards/`.

## Handoffs

- LogQL / PromQL queries → `observability/logql-promql`
- Instrumentation (what shapes the data) → `observability/opentelemetry-{dotnet,java,node}`
- Structured logging fields → `observability/structured-logging-{dotnet,java,node}`
- Pipeline-side deploy annotations → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- SLO math / quality KPIs → `qa/_shared/quality-metrics`
