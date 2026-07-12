---
name: observability-prometheus-mimir-setup
description: Use when the user asks to set up the metrics backend of the Grafana stack — Prometheus (single-cluster) or Grafana Mimir (multi-cluster / long-retention / HA) — ingest metrics from the OTel Collector (remote-write or OTLP), enable exemplar storage, deploy recording/alerting rules, and tune retention + cardinality. Triggers: "set up Prometheus", "deploy Mimir", "long-term metrics storage", "remote-write metrics to Mimir", "enable exemplars", "where do my OTLP metrics go", "how do I store metrics". Do NOT use for query/rule syntax (use `observability/logql-promql`), dashboards/panels (use `observability/grafana-dashboards`), logs + traces (use `observability/loki-tempo-setup`), or code instrumentation (use `observability/opentelemetry-{stack}`).
---

# Observability — Prometheus / Mimir Setup

Wires the **metrics** backend of the Grafana stack. This library's default ingest path is **OTel SDK → OTel Collector → metrics backend** (the same Collector that `observability/loki-tempo-setup` stands up), so the metrics store is a sink for the Collector's `prometheusremotewrite` / OTLP exporter — not a scraper you bolt on separately. Choose **Prometheus** for a single cluster with operational (days-to-weeks) retention, or **Grafana Mimir** when you need multi-cluster aggregation, HA, multi-tenancy, or long-term retention on object storage. Both speak PromQL, both store exemplars, both load the same rule files.

## When to use

- New cluster / environment needs a metrics backend
- Wiring the OTel Collector's metrics pipeline to a store (remote-write or OTLP)
- Enabling **exemplar storage** so latency histograms link to traces in Tempo
- Deploying recording / alerting **rules** (the rules themselves come from `observability/logql-promql`)
- Wiring **Alertmanager** — routing tree, grouping, inhibition, dead-man's-switch, on-call receivers
- Outgrowing single-node Prometheus — retention, HA, or multi-cluster forces Mimir
- Setting retention + per-tenant cardinality limits

## When NOT to use

- PromQL queries / recording-rule / alert expressions → `observability/logql-promql`
- Dashboard layout, panel exemplar config → `observability/grafana-dashboards`
- Logs (Loki) + traces (Tempo) + the shared OTel Collector → `observability/loki-tempo-setup`
- App-side metric emission (`Meter` / `Counter` / `Histogram`) → `observability/opentelemetry-{dotnet,java,node}`
- Alert rule *expressions* (the health-alert pack, burn rates) → `observability/logql-promql`; this skill owns rule *deployment* + Alertmanager *routing*

## Inputs needed

1. **Cluster**: AKS / EKS / GKE / VMs / managed (Grafana Cloud)
2. **Scale**: active series count, samples/sec, number of clusters feeding in
3. **Retention**: 15d / 30d / 90d / 1y+ by class — the single biggest driver of Prometheus-vs-Mimir
4. **HA / multi-tenant**: single Prometheus, HA pair, or Mimir multi-tenant
5. **Object storage** (Mimir): S3 / GCS / Azure Blob — pick by cloud
6. **Ingest protocol**: `prometheusremotewrite` (default, matches `loki-tempo-setup`) or native OTLP

## Prometheus vs Mimir

| Need | Prometheus | Grafana Mimir |
|---|---|---|
| Single cluster, days–weeks retention | ✅ default | overkill |
| Local disk (TSDB) storage | ✅ | ❌ (object storage only) |
| Long-term retention (months–years) | ❌ (disk-bound) | ✅ (S3 / GCS / Blob, ~20× cheaper/GB) |
| Multi-cluster aggregation (one query surface) | ❌ | ✅ |
| Horizontal scale / HA / dedup | limited (HA pairs) | ✅ (distributed) |
| Multi-tenant (`X-Scope-OrgID`) | ❌ | ✅ |
| Query language | PromQL | PromQL (compatible) |

**Rule of thumb:** start with Prometheus. Move to Mimir when retention, multi-cluster, or HA/multi-tenancy forces it — not before. Mimir is remote storage *behind* Prometheus-compatible senders (Prometheus, Alloy, or the OTel Collector); it does not scrape. Thanos and VictoriaMetrics solve the same scaling problem; this library standardizes on Mimir for parity with the rest of the Grafana stack.

## Architecture

```
App (OTel SDK) ──► OTel Collector ──► metrics backend ──► (Mimir only) Object Storage (S3 / GCS / Blob)
                   (the hub from                │
                    loki-tempo-setup)           ├─ Prometheus: local TSDB, remote-write or OTLP receiver
                                                └─ Mimir:     distributor → ingester → object storage

Rules (recording + alerting, from logql-promql, in Git) ──► loaded via Helm / rule sidecar
Grafana queries the backend with PromQL; exemplars link metrics → traces in Tempo
```

The Collector is the seam (see `observability/loki-tempo-setup`). Swapping Prometheus for Mimir changes only the exporter endpoint — apps never know.

## Ingest: how metrics get in

### Remote-write from the Collector (default)

Matches the `prometheusremotewrite` exporter already configured in `observability/loki-tempo-setup`. Point it at the backend:

```yaml
# otel-collector-config.yaml (metrics exporter)
exporters:
  prometheusremotewrite:
    endpoint: http://prometheus.observability:9090/api/v1/write   # Prometheus
    # endpoint: http://mimir-nginx.observability/api/v1/push      # Mimir gateway
    # headers: { X-Scope-OrgID: team-orders }                     # Mimir multi-tenant
```

Prometheus must be started with `--web.enable-remote-write-receiver` to accept remote-write. Mimir's distributor accepts it out of the box.

### Native OTLP (alternative)

Prometheus 3.x ships a native OTLP receiver; Mimir supports OTLP over HTTP (Grafana **recommends OTLP** for Mimir). Use the Collector's `otlphttp` exporter instead:

```yaml
exporters:
  otlphttp/metrics:
    metrics_endpoint: http://prometheus.observability:9090/api/v1/otlp/v1/metrics   # Prometheus 3.x
    # metrics_endpoint: http://mimir-nginx.observability/otlp/v1/metrics            # Mimir
```

Enable the receiver on Prometheus with `--web.enable-otlp-receiver`.

### Scrape (only when something can't push)

Pull-based scraping still fits third-party `/metrics` exporters (node-exporter, kube-state-metrics, DB exporters) that don't push through the Collector. `kube-prometheus-stack` sets these up via `ServiceMonitor` / `PodMonitor` CRDs. For your own app metrics, prefer the Collector push path so sampling/routing stays in one place.

## Exemplar storage

Required by the exemplar wiring `observability/grafana-dashboards` depends on (dots on latency histograms that jump to the trace in Tempo).

- **Prometheus**: start with `--enable-feature=exemplar-storage --web.enable-otlp-receiver`. Exemplar storage is an in-memory circular buffer — size it with `storage.exemplars.max_exemplars`.
- **Mimir**: enable per-tenant via the `max_global_exemplars_per_user` limit; the Tempo `metrics_generator` (see `loki-tempo-setup`) must set `send_exemplars: true` so span-derived RED metrics carry `trace_id`.

Without exemplar storage the histograms still render — they just have no clickable trace links.

## Rule deployment

Recording rules (pre-compute expensive queries) and alerting rules are **authored** in `observability/logql-promql`; this skill only **deploys** them. Keep rule files in Git and load them declaratively — never hand-edit rules on a running server.

- **Prometheus (`kube-prometheus-stack`)**: rules as `PrometheusRule` CRDs, reconciled by the Prometheus Operator. One CRD per rule group, reviewed in PR.
- **Mimir**: rules loaded via the ruler component from object storage, synced with `mimirtool rules load` from a Git-tracked directory in CI.

```yaml
# PrometheusRule CRD (kube-prometheus-stack) — expression body owned by logql-promql
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: app-slo-rules
  labels: { release: kube-prometheus-stack }
spec:
  groups:
    - name: app.recording
      rules:
        - record: job:http_request_duration_seconds:p95
          expr: histogram_quantile(0.95, sum by (le, job) (rate(http_server_request_duration_seconds_bucket[5m])))
```

## Alertmanager (routing the alerts)

Rules only *fire*; **Alertmanager** decides who hears about it. `kube-prometheus-stack` deploys it alongside Prometheus; Mimir ships a built-in multi-tenant Alertmanager (configs loaded per tenant with `mimirtool alertmanager load`). The alert *expressions* (service-health pack, burn rates) live in `observability/logql-promql`; this section owns the routing.

```yaml
# alertmanager.yaml (kube-prometheus-stack: alertmanager.config)
route:
  group_by: [alertname, service]        # one notification per incident, not per instance
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: slack-warnings              # default catch-all
  routes:
    - matchers: [severity = page]
      receiver: pagerduty-oncall
    - matchers: [alertname = Watchdog]
      receiver: deadmans-switch         # see below
      repeat_interval: 1m

inhibit_rules:
  # A critical alert on a service silences its own warnings — no double noise
  - source_matchers: [severity = page]
    target_matchers: [severity = warn]
    equal: [service, env]

receivers:
  - name: pagerduty-oncall
    pagerduty_configs: [{ routing_key_file: /etc/am/pd-key }]
  - name: slack-warnings
    slack_configs: [{ channel: "#alerts", api_url_file: /etc/am/slack-url }]
  - name: deadmans-switch
    webhook_configs: [{ url: https://deadmanssnitch-or-healthchecks-io/... }]
```

**Dead-man's-switch (non-negotiable):** `kube-prometheus-stack` ships a `Watchdog` alert that fires *always*. Route it to an external heartbeat service (Healthchecks.io / Dead Man's Snitch / PagerDuty heartbeat) that pages when the signal **stops** — the only thing that catches "Prometheus/Alertmanager itself is down", which no internal alert can.

Routing keys off the `severity` + `service` labels — which is why every rule in the health-alert pack carries them. `severity: page` → on-call; `severity: warn` → chat/ticket. Config lives in Git like everything else (Helm values / `mimirtool`), secrets via `*_file` references — never inline.

## Retention + cardinality

- **Retention** is the top cost knob. Prometheus: `--storage.tsdb.retention.time=30d` (disk-bound — this is what pushes you to Mimir). Mimir: `compactor.blocks_retention_period` per tenant, cheap on object storage.
- **Cardinality** is the top perf/cost killer. Every unique label-value combination is a new time series; high-cardinality labels (`user_id`, `order_id`, `trace_id`) as metric labels explode the series count and OOM the ingesters. Keep them off metrics — they belong on spans (see `observability/opentelemetry-{stack}`).
- **Mimir limits** cap the blast radius per tenant: `max_global_series_per_user`, `max_global_series_per_metric`, `ingestion_rate`. Set them; an unbounded tenant takes down shared ingesters.

## Helm samples

### Prometheus — `prometheus-community/kube-prometheus-stack`

```yaml
# values.yaml
prometheus:
  prometheusSpec:
    retention: 30d
    enableFeatures: [exemplar-storage]
    enableRemoteWriteReceiver: true          # accept Collector remote-write
    enableOTLPReceiver: true                  # accept Collector OTLP (Prometheus 3.x)
    resources:
      requests: { cpu: "1", memory: 4Gi }
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources: { requests: { storage: 100Gi } }
```

### Mimir — `grafana/mimir-distributed`

```yaml
# values.yaml
mimir:
  structuredConfig:
    limits:
      max_global_series_per_user: 1500000
      max_global_exemplars_per_user: 100000    # exemplar storage per tenant
    compactor:
      blocks_retention_period: 1y
    common:
      storage:
        backend: s3
        s3:
          bucket_name: mimir-metrics-prod
          endpoint: s3.eu-west-1.amazonaws.com
          # IRSA / Workload Identity for auth
```

## Grafana Cloud as a managed alternative

Grafana Cloud Metrics is hosted Mimir — same PromQL, same remote-write / OTLP ingest, less ops. The recipes here work against self-hosted or Grafana Cloud; only the endpoint and auth token differ. Pay for it if the time saved beats the ops cost.

## Rules

- Start with Prometheus; adopt Mimir only when retention, multi-cluster, or HA/multi-tenant forces it — state the reason explicitly
- Ingest through the OTel Collector (remote-write default, OTLP alternative); scrape only third-party `/metrics` the Collector can't push
- **Exemplar storage enabled** on the backend, and `send_exemplars: true` on Tempo's `metrics_generator` — cross-store nav depends on it
- Rule files in Git, deployed declaratively (`PrometheusRule` CRD / `mimirtool rules load`); expression bodies owned by `observability/logql-promql`
- Retention set explicitly per class; Mimir for anything beyond disk-bound Prometheus retention
- Metric labels are low-cardinality only; per-record ids belong on spans, never on metrics
- Mimir per-tenant limits set (`max_global_series_per_user`, `ingestion_rate`) — never run a tenant unbounded
- Object storage on the cloud's native service; IRSA / Workload Identity for auth
- No `:latest` image tags for Prometheus / Mimir
- Alertmanager routes on `severity` + `service`; inhibition wired; `Watchdog` dead-man's-switch to an external heartbeat — silence itself must page

## What NOT to do

- No `user_id` / `order_id` / `trace_id` as a metric label — that's a cardinality bomb; it's a span attribute
- No bypassing the Collector (apps remote-writing directly to the backend) — kills the ability to change routing/sampling without redeploys
- No Mimir on local disk — it is object-storage-only by design; "Mimir without S3/GCS/Blob" is a misconfiguration
- No reaching for Mimir on day one for a single small cluster — Prometheus is simpler and sufficient
- No hand-editing rules on a running server — they must live in Git and deploy declaratively
- No skipping exemplar storage if you wired exemplars in `grafana-dashboards` — the trace links silently do nothing
- No unbounded Mimir tenant — one noisy tenant OOMs the shared ingesters
- No keeping full-fidelity metrics for a year on Prometheus local disk — that is exactly what Mimir + object storage is for

## Generation steps

1. Confirm cluster, scale, retention by class, HA/multi-tenant Y/N, and ingest protocol.
2. Decide **Prometheus vs Mimir** using the decision table; state the reason if Mimir.
3. Deploy the backend: `kube-prometheus-stack` (Prometheus) or `grafana/mimir-distributed` (Mimir) with the Helm values above; point Mimir at object storage.
4. Enable **exemplar storage** and the remote-write / OTLP receiver on the backend.
5. Point the OTel Collector's metrics exporter at the backend endpoint (add `X-Scope-OrgID` for Mimir multi-tenant).
6. Set **retention** and (Mimir) **per-tenant limits**.
7. Deploy **rules** from the Git-tracked directory (`PrometheusRule` CRDs / `mimirtool rules load`); expressions come from `observability/logql-promql`.
7a. Configure **Alertmanager**: routing by `severity`/`service`, inhibition, receivers, and the `Watchdog` dead-man's-switch to an external heartbeat.
8. Wire the **Grafana data source** (Prometheus/Mimir) declaratively; confirm exemplars link to Tempo (see `observability/grafana-dashboards`).
9. Smoke: emit a metric from an app, confirm it lands via PromQL, confirm a histogram shows exemplar dots that jump to a trace.

## Handoffs

- Query / recording-rule / alert syntax → `observability/logql-promql`
- Dashboards, panel + data-source exemplar config → `observability/grafana-dashboards`
- Shared OTel Collector + logs (Loki) + traces (Tempo) → `observability/loki-tempo-setup`
- App metric emission → `observability/opentelemetry-{dotnet,java,node}`
- Kubernetes manifests for the metrics stack → `devops/kubernetes`
- Object-storage buckets + IAM (Mimir) → `devops/iac-bicep-terraform`
