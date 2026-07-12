---
name: observability-logql-promql
description: Use when the user asks to write LogQL (Loki) or PromQL (Prometheus / Mimir) queries for dashboards, alerts, or ad-hoc investigation. Triggers: "write a LogQL for error logs in service X", "PromQL for p95 latency", "rate vs irate", "histogram_quantile recipe", "filter logs by trace id", "join metrics with labels". Do NOT use for dashboard layout (use `observability/grafana-dashboards`) or code instrumentation (use `observability/opentelemetry-{dotnet,java,node}`).
---

# Observability — LogQL & PromQL

The query layer of the Loki + Prometheus + Tempo stack. Covers PromQL for metrics, LogQL for logs, common idioms, and the cross-store pattern (log → trace via `trace_id`, metric → trace via exemplars). Targets dashboards (`observability/grafana-dashboards`), alert rules, and on-call investigation.

## When to use

- Authoring panel queries for a Grafana dashboard
- Authoring Prometheus / Mimir alert rules
- Ad-hoc on-call investigation (`{service="orders",level="error"} |~ "timeout"`)
- Tuning a slow query (cardinality issues, missing label, wrong function)

## When NOT to use

- Dashboard layout / panel design → `observability/grafana-dashboards`
- Generating metrics in code → `observability/opentelemetry-{dotnet,java,node}`
- Designing SLI/SLO targets (the math, not the query) → `qa/_shared/quality-metrics`

## Inputs needed

1. **Data source** (Prometheus / Mimir / Loki / Tempo)
2. **Service** + **label set** available (what's emitted by the OTel pipelines)
3. **Time window** (instant, last 5m, last 24h)
4. **Use case** — alert (single-value), dashboard panel (time series), investigation (log search)

## Standard label set

Match `observability/opentelemetry-{stack}` + `observability/structured-logging-{stack}`. Available everywhere:

| Label | Metrics | Logs | Cardinality |
|---|---|---|---|
| `service` (or `service_name`) | ✓ | ✓ | low |
| `env` (or `deployment_environment`) | ✓ | ✓ | low |
| `instance` (pod / task id) | ✓ | ✓ | medium |
| `http_route` | ✓ | ✓ | low (normalized to `/orders/{id}` not `/orders/42`) |
| `http_method` | ✓ | ✓ | low |
| `http_status_code` | ✓ | ✓ | low |
| `level` | — | ✓ | low |
| `trace_id` (exemplars only) | ✓ (as sample annotation) | ✓ (as field) | very high — never in label set, never in `by` |

Per-request IDs (`order_id`, `user_id`, `trace_id`) are **fields** on the log line and **exemplars** on the metric; never labels you group by.

## PromQL — the workhorse functions

### `rate` vs `irate`

```promql
# Average rate over the window — for graphs over time and alerts
sum by (service) (rate(http_server_requests_total[5m]))

# Instantaneous rate from the last two samples — for current value displays only
sum by (service) (irate(http_server_requests_total[1m]))
```

`rate` is the default. `irate` is sensitive to scrape gaps; use only for spiky workloads where you specifically want the latest interval.

**Always pair with `sum by (...)`** for counters when querying across instances — otherwise you graph per-instance rates and double-count.

### Error rate (the most-used PromQL)

```promql
sum by (service) (rate(http_server_requests_total{status=~"5..|4.."}[5m]))
/
sum by (service) (rate(http_server_requests_total[5m]))
* 100
```

Read: `rate(error count) / rate(total count) * 100` = error percentage.

For 5xx-only:

```promql
sum by (service) (rate(http_server_requests_total{status=~"5.."}[5m]))
/
sum by (service) (rate(http_server_requests_total[5m]))
```

### Latency histograms — `histogram_quantile`

OTel histograms are exposed as `<name>_bucket` + `<name>_count` + `<name>_sum`. Quantile from buckets:

```promql
histogram_quantile(0.95,
  sum by (le, service, http_route) (rate(http_server_request_duration_seconds_bucket[5m]))
)
```

Rules:
- **Sum `_bucket` first**, **then** apply `histogram_quantile` — order matters
- Use `le` in `by (...)` — it's the bucket label
- Native histograms (Prometheus 2.40+) use `histogram_quantile` slightly differently — check the Prometheus docs

### Top-N

```promql
topk(10, sum by (http_route) (rate(http_server_requests_total{service="$service"}[5m])))
```

`topk` / `bottomk` for "slowest 10 routes", "noisiest 10 hosts".

### Counters reset / running totals

`increase(counter[24h])` for "total events in the last 24h". Don't just take the difference — `rate` / `increase` handle resets when a pod restarts.

### Resource utilization (USE)

```promql
# CPU usage % per pod
100 * sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="prod"}[5m]))
  / sum by (pod) (kube_pod_container_resource_limits_cpu_cores{namespace="prod"})

# Memory usage % per pod
100 * sum by (pod) (container_memory_working_set_bytes{namespace="prod"})
  / sum by (pod) (kube_pod_container_resource_limits_memory_bytes{namespace="prod"})
```

### Alerts — recording vs alerting rules

```yaml
groups:
  - name: orders
    interval: 30s
    rules:
      - record: orders:http_5xx_rate
        expr: sum by (service, http_route) (rate(http_server_requests_total{service="orders",status=~"5.."}[5m]))

      - alert: OrdersHigh5xxRate
        expr: orders:http_5xx_rate > 1               # > 1 req/s of 5xx
        for: 5m
        labels: { severity: page }
        annotations:
          summary: "Orders 5xx rate is {{ $value }} req/s on {{ $labels.http_route }}"
          runbook: https://runbooks.yourco.com/orders-5xx
```

**Use recording rules** for expensive queries used in multiple panels / alerts — they pre-compute on every scrape interval. Alerts then become cheap (`orders:http_5xx_rate > 1`).

### Burn-rate alerts (SLO)

For a 99.9% SLO with a 30-day budget, a "fast burn" alert (consume 5% of budget in 1 hour):

```promql
(
  sum by (service) (rate(http_server_requests_total{service="orders",status=~"5.."}[1h]))
  /
  sum by (service) (rate(http_server_requests_total{service="orders"}[1h]))
) > (14.4 * (1 - 0.999))
```

`14.4 * (1 - SLO)` is the fast-burn threshold from Google's SRE workbook for 1h windows. Use multi-window alerts for noise reduction.

## LogQL — log queries

LogQL syntax: **label selector** `{...}` → **filter** `|=` `|~` `!=` `!~` → **parser** `| json` `| logfmt` → **operations** `| line_format ...` / `count_over_time(...)`.

### Selector + filter

```logql
{service="orders", env="prod"} |= "error" |~ "(?i)timeout"
```

- `|=` substring filter (fastest, fully indexed)
- `|~` regex filter (slower)
- `!=` / `!~` negation

Always start with a tight `{...}` selector. Loki streams are cheap when scoped to one service.

### Structured logs (`| json`)

```logql
{service="orders", env="prod"}
  | json
  | level="error"
  | line_format "{{.timestamp}} {{.message}} traceId={{.trace_id}}"
```

`| json` parses the JSON body and exposes keys as filterable labels for the rest of the query. `line_format` reshapes the output for the panel.

### Metric queries from logs

LogQL can compute metric-style aggregates:

```logql
# Errors per minute, per route, last 5m
sum by (http_route) (count_over_time({service="orders", env="prod"} | json | level="error" [5m]))
```

Useful when no metric exists for the thing you want to count, **but** consider emitting a real metric (`observability/opentelemetry-{stack}`) if you'll graph it frequently — metrics are cheaper to query.

### Cross-store: log → trace

When a log line has `trace_id`, the dashboard's derived field (set in `observability/grafana-dashboards`) turns it into a Tempo link. The LogQL itself doesn't need anything special — just emit `trace_id` in the structured log (which `observability/structured-logging-{stack}` already does).

### Filtering noisy patterns

```logql
{service="orders"} != "GET /health" != "GET /metrics" |~ "(?i)error"
```

Negation filters early to keep the line count down. Health / metrics endpoints generate most of the noise.

## Common patterns

### "What's broken right now?"

```promql
sum by (service) (rate(http_server_requests_total{status=~"5..",env="$env"}[5m])) > 0
```

```logql
{env="$env"} | json | level="error" | line_format "{{.service}} {{.message}}"
```

### "p99 latency spike — where?"

```promql
topk(10,
  histogram_quantile(0.99,
    sum by (le, service, http_route) (rate(http_server_request_duration_seconds_bucket{env="$env"}[5m]))
  )
)
```

Then click an exemplar to jump into the trace.

### "Database connection pool saturated?"

```promql
db_client_connections_usage{state="used", env="$env"}
  / on(service, instance) db_client_connections_max{env="$env"}
  * 100
```

### "Which routes are getting hammered?"

```promql
topk(10, sum by (service, http_route) (rate(http_server_requests_total{env="$env"}[5m])))
```

### "Trace id from log → which user?"

The log itself carries `user_id`, `tenant_id`, etc. as JSON fields:

```logql
{service="orders"} | json | trace_id="abc123" | line_format "{{.user_id}} {{.tenant_id}} {{.message}}"
```

## Rules

- **Always pair counters with `rate` / `irate` / `increase`** — never query raw counters
- **`sum by (...)` to aggregate across instances** before final functions
- **`histogram_quantile` after summing buckets**, not before
- **Use recording rules** for expensive expressions reused across panels / alerts
- **Tight `{...}` selector** in every LogQL query — scope to service + env
- **Filter early** in LogQL (`|=` before `| json`) to keep the line count manageable
- **Per-request IDs in fields, not labels** — never `by (trace_id)` / `by (user_id)`
- **Variables** in queries (`$service`, `$env`, `$route`) so they work across dashboards
- **Recording rules + alerts in Git** as YAML — review changes in PR

## What NOT to do

- No `rate(...)` on a gauge — gauges don't have a rate (they have a value)
- No `irate(...)` for graphs — use `rate` over a window
- No `histogram_quantile(0.95, foo_bucket)` without summing buckets first — wrong answer
- No `by (trace_id)` / `by (user_id)` / `by (request_id)` — cardinality explosion
- No `{service=~".*"}` selectors in production queries — pin the service
- No `| json` before a `|=` filter — filter the raw line first if you can
- No PromQL alerts without `for:` — instant alerts spike on transient blips
- No alert without a `summary` + `runbook` annotation
- No "alert on every metric"; alert on what users feel
- No queries on the dashboard that take > 30s — recording-rule them or rescope
- No mixing `level="error"` casing — `error` / `ERROR` / `Error` — match the structured-logging skill's convention

## Generation steps

1. Confirm the data source, label set, time window, and use case.
2. Start with the tightest label selector.
3. For metrics: pick the right primitive (`rate` / `histogram_quantile` / `topk` / `count_over_time`).
4. For logs: filter first, parse second, format / aggregate third.
5. Add a `by (...)` clause with **only low-cardinality** labels.
6. For frequent queries, promote to a recording rule (Prometheus rule file).
7. For alerts, add `for:`, `severity`, `summary`, `runbook`.
8. Validate by running against the live time series; sanity-check the magnitude.

## Handoffs

- Dashboard layout → `observability/grafana-dashboards`
- What's in the metrics / log streams → `observability/opentelemetry-{stack}` + `observability/structured-logging-{stack}`
- SLO math / KPI definitions → `qa/_shared/quality-metrics`
- Adding new metrics / fields needed for a query → instrumentation skill for the stack
