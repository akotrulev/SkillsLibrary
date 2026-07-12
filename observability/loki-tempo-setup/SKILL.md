---
name: observability-loki-tempo-setup
description: Use when the user asks to set up Grafana Loki (logs) and Grafana Tempo (traces) — wire OTel Collector to both, choose object storage (S3 / GCS / Azure Blob), retention, log shipping (Grafana Alloy / Vector / Fluent Bit), index labels, exemplar linking, multi-tenant. Triggers: "set up Loki", "ship logs to Loki", "Tempo configuration", "wire OTel Collector to Loki / Tempo", "what storage for Loki", "log retention strategy". Do NOT use for query syntax (use `observability/logql-promql`), dashboards (use `observability/grafana-dashboards`), or code instrumentation (use `observability/opentelemetry-{stack}` + `observability/structured-logging-{stack}`).
---

# Observability — Loki + Tempo Setup

Wires the **log and trace** halves of the Grafana stack — Loki for logs, Tempo for traces. Standardizes on: **stdout JSON from apps → log forwarder (Grafana Alloy / Vector / Fluent Bit) → Loki → object storage**; **OTel SDKs → OTel Collector → Tempo (OTLP gRPC) → object storage**; **exemplars + Loki derived fields** to make navigation between logs, metrics, and traces seamless.

## When to use

- New cluster / environment needs the Grafana stack
- Migrating from a vendor (Datadog / Splunk / New Relic) to self-hosted Grafana
- Designing log retention / cardinality strategy
- Wiring a log forwarder (Grafana Alloy / Vector / Fluent Bit)
- Setting up multi-tenant Loki / Tempo (one cluster, many teams)

## When NOT to use

- LogQL / PromQL queries → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`
- App-side log shape → `observability/structured-logging-{dotnet,java,node}`
- App-side instrumentation → `observability/opentelemetry-{stack}`
- Prometheus / Mimir for metrics → `observability/prometheus-mimir-setup`

## Inputs needed

1. **Cluster**: AKS / EKS / GKE / VMs / managed (Grafana Cloud)
2. **Scale**: rough GB/day of logs, traces/sec
3. **Retention**: 7d / 30d / 90d / 1y by class
4. **Object storage**: S3 / GCS / Azure Blob — pick by cloud
5. **Multi-tenant**: one shared cluster + tenant headers, or one cluster per tenant
6. **Log forwarder**: Grafana Alloy (recommended default), Vector (flexible), Fluent Bit (battle-tested) — pick one

## Architecture

```
App (stdout JSON, OTel SDK)
   │
   ▼
Pod / container runtime
   │
   ├──► Log forwarder (Grafana Alloy / Vector / Fluent Bit) ──► Loki ──► Object Storage (S3 / GCS / Blob)
   │
   └──► OTel Collector (in-cluster sidecar or DaemonSet) ──► Tempo (OTLP gRPC) ──► Object Storage
                                          │
                                          └──► Prometheus / Mimir (metrics)

                Grafana queries Loki + Tempo + Prom/Mimir
                Exemplars + derived fields → cross-store nav
```

Two ingest paths because logs and traces have different ergonomics:
- Logs ride **stdout → forwarder → Loki**, no app code changes for shipping
- Traces ride **OTel SDK → Collector → Tempo**, in-process instrumentation

The **OTel Collector** is the single piece that touches every stack — install it once per cluster, route everything through it.

## Loki

### Mode

| Mode | When |
|---|---|
| **Monolithic** (`single binary`) | < ~100 GB/day, < 10 services; simplest |
| **Simple Scalable** (`-target=read` / `-target=write` / `-target=backend`) | Most production deployments; the right default |
| **Microservices** | Very large scale; complex; only when justified |

Use **Simple Scalable** unless you've measured a reason to do otherwise.

### Object storage

| Cloud | Choice |
|---|---|
| AWS | S3 — `loki.storage.aws.s3` |
| Azure | Blob Storage — `loki.storage.azure` |
| GCP | GCS — `loki.storage.gcs` |
| On-prem | MinIO, or filesystem in single-node setups |

Cheap, infinite-ish capacity, plus lifecycle policies for tiered retention.

### Sample Helm values

```yaml
# loki-values.yaml (Grafana Helm chart `grafana/loki`)
loki:
  schemaConfig:
    configs:
      - from: 2024-01-01
        store: tsdb
        object_store: s3
        schema: v13
        index: { prefix: loki_index_, period: 24h }

  storage:
    type: s3
    bucketNames:
      chunks: loki-chunks-prod
      ruler:  loki-ruler-prod
      admin:  loki-admin-prod
    s3:
      region: eu-west-1
      # OIDC / IRSA — no static keys
      s3ForcePathStyle: false

  limits_config:
    retention_period: 720h               # 30 days; per-tenant overrides via runtime config
    ingestion_rate_mb: 10                # per tenant
    max_streams_per_user: 10000
    max_label_name_length: 1024
    max_label_value_length: 2048
    reject_old_samples: true
    reject_old_samples_max_age: 168h

deploymentMode: SimpleScalable
read:    { replicas: 3 }
write:   { replicas: 3 }
backend: { replicas: 3 }
```

For AKS / EKS: use Workload Identity / IRSA on the Loki ServiceAccounts — no S3 / Blob keys in cluster.

### Retention

`retention_period: 720h` is a sane default (30 days). Per-tenant overrides via the runtime config let you keep `auth` logs 90 days and `nginx access` logs 7 days. Pair with **S3 lifecycle policies** for cold-tier offloading if your retention is long.

### Index labels (cardinality discipline)

Loki indexes on **labels only**, not on log content. The OTel pipeline + log forwarders should emit these labels — and **only these**:

| Label | Cardinality | Why |
|---|---|---|
| `service` | low | The service emitting |
| `environment` | low | dev / staging / prod |
| `level` | low | info / warn / error / debug |
| `namespace` (Kubernetes) | low | for cluster-scoped filtering |

High-cardinality stuff (`trace_id`, `user_id`, `request_id`, `order_id`) lives **inside the log line as fields**, parsed with `| json` at query time. Label explosion kills Loki — this is the lesson.

## Log forwarders

### Grafana Alloy (recommended default)

Alloy is Grafana's OpenTelemetry-based collector distribution and the **successor to Promtail** (Grafana deprecated Promtail in Feb 2025, EOL ~Mar 2026). Deploy it as a DaemonSet via the `grafana/alloy` Helm chart; the pipeline is declared in Alloy's River config — discover pods, tail their logs, parse JSON, attach only the low-cardinality labels, push to Loki.

```yaml
# alloy-values.yaml (Helm chart `grafana/alloy`)
controller:
  type: daemonset            # one Alloy per node, tails that node's pod logs
alloy:
  configMap:
    content: |
      // 1. Discover pods on this node
      discovery.kubernetes "pods" {
        role = "pod"
      }

      // 2. Keep only low-cardinality labels as Loki stream labels
      discovery.relabel "pod_logs" {
        targets = discovery.kubernetes.pods.targets
        rule {
          source_labels = ["__meta_kubernetes_namespace"]
          target_label  = "namespace"
        }
        rule {
          source_labels = ["__meta_kubernetes_pod_label_app"]
          target_label  = "service"
        }
      }

      // 3. Tail the discovered pods' logs
      loki.source.kubernetes "pods" {
        targets    = discovery.relabel.pod_logs.output
        forward_to = [loki.process.parse.receiver]
      }

      // 4. Parse the JSON line; promote ONLY level + service to labels
      loki.process "parse" {
        stage.json {
          expressions = { level = "level", service = "service.name" }
        }
        stage.labels {
          values = { level = "", service = "" }
        }
        forward_to = [loki.write.default.receiver]
      }

      // 5. Push to Loki
      loki.write "default" {
        endpoint {
          url = "http://loki-gateway/loki/api/v1/push"
        }
      }
```

Keep `environment` as a static external label (set once per cluster) rather than relabeling it per stream. Everything high-cardinality (`trace_id`, `user_id`, `request_id`) stays inside the log line and is parsed with `| json` at query time.

### Vector (more flexible)

Vector handles routing, filtering, dropping noisy logs, batching, multiple sinks. Use Vector when you want one tool to ship to Loki + another sink (e.g., archive to S3), or when you need richer transforms.

### Fluent Bit (lightweight, broad community)

CNCF-graduated; less footprint than Fluentd. Solid alternative if your org standardizes on it.

### Promtail (legacy — deprecated)

Promtail was the classic Loki forwarder but is **deprecated by Grafana (announced Feb 2025, EOL ~Mar 2026)** in favor of Grafana Alloy. Do not pick it for new clusters; for existing Promtail setups migrate with `alloy convert --source-format=promtail`.

Pick **one** per cluster and stay consistent. Don't run two.

## Tempo

### Sample Helm values

```yaml
# tempo-values.yaml (Helm chart `grafana/tempo`)
tempo:
  storage:
    trace:
      backend: s3
      s3:
        bucket: tempo-traces-prod
        region: eu-west-1
        # IRSA / Workload Identity
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

  metrics_generator:
    processor:
      service_graphs: {}
      span_metrics: {}                   # auto-generates RED metrics from traces
    storage:
      remote_write_flush_deadline: 1m
      remote_write:
        - url: http://prometheus.observability:9090/api/v1/write
```

The **`metrics_generator`** is the killer Tempo feature for new setups: every span auto-generates RED-style metrics + service graphs in Prometheus, without any code change. Wire it; everything downstream benefits.

### Retention

Trace retention is cheaper than log retention (much smaller volume per span). Default: **30 days**; bump to 90 days for production if budget allows. Sampled-out spans never reach Tempo, so storage is bounded by your sampling rate × ingest rate.

## OTel Collector — the hub

Deploy the Collector as a DaemonSet (or sidecar) per cluster. Receives OTLP from apps; routes traces to Tempo, metrics to Prometheus/Mimir, logs (if enabled) to Loki.

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024
  resource:
    attributes:
      - key: deployment.environment
        from_attribute: env
        action: upsert
  tail_sampling:                         # optional: keep all errors, 1% of OK
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 1000 }
      - name: probabilistic
        type: probabilistic
        probabilistic: { sampling_percentage: 1 }

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }                # in-cluster
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write
  # loki via OTLP only if app emits logs as OTLP (we usually ship via stdout → forwarder)

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [resource, tail_sampling, batch]
      exporters:  [otlp/tempo]
    metrics:
      receivers:  [otlp]
      processors: [resource, batch]
      exporters:  [prometheusremotewrite]
```

The Collector lets you change sampling, batching, and routing **without redeploying every app**. Make it the seam.

## Cross-store navigation

Three wirings turn three independent stores into one investigative loop:

### Exemplars (metrics → traces)

Prometheus stores exemplars (a `trace_id` per histogram sample). Grafana renders dots on latency histograms; clicking jumps to that trace in Tempo. Wire by setting the Tempo data source's exemplar link config (a one-time Grafana config — see `observability/grafana-dashboards`). Requires exemplar storage enabled on the metrics backend (`observability/prometheus-mimir-setup`).

### Loki derived fields (logs → traces)

**The trace-correlation contract.** The three stacks emit the trace id under different JSON field names — the derived-field regex must match all of them, or "jump to trace" silently breaks for the stacks it misses:

| Stack | Emitting library | JSON field |
|---|---|---|
| dotnet | Serilog + `Serilog.Enrichers.Span` | `TraceId` |
| java | OTel `logback-mdc-1.0` (default MDC keys) | `trace_id` |
| node | pino + `@opentelemetry/instrumentation-pino` | `trace_id` |

The **canonical cross-stack regex** (use exactly this in the Loki data source's derived field — one config serves all stacks):

```
Name:  trace_id
Regex: "(?:TraceId|trace_id)"\s*:\s*"([0-9a-f]{32})"
```

W3C trace ids are exactly 32 lowercase hex chars — anchor on that, not `\w+` (which happily captures request ids and other garbage). Configure it as an **internal link**: set `datasourceUid` to the Tempo data source and the query to `${__value.raw}` (in provisioning YAML: `derivedFields: [{ name: trace_id, matcherRegex: ..., datasourceUid: tempo, url: "${__value.raw}" }]`).

Every log line with a trace id becomes a clickable link to the trace. Combined with `observability/structured-logging-{stack}` (which emits the field per the contract table), the experience is: click an error → see the trace → click a span → see the slow DB query.

### Tempo trace → logs (`tracesToLogsV2`)

The third leg — from a span back to the logs that service wrote during that span. Configure on the **Tempo data source**:

```yaml
# grafana datasource provisioning (Helm values / Terraform)
- name: Tempo
  type: tempo
  uid: tempo
  url: http://tempo-query-frontend:3100
  jsonData:
    tracesToLogsV2:
      datasourceUid: loki
      spanStartTimeShift: "-5m"      # pad the window — logs can lag the span
      spanEndTimeShift: "5m"
      tags: [{ key: "service.name", value: "service" }]   # span attr → Loki label
      filterByTraceID: true          # narrow to lines carrying this trace id
    tracesToMetrics:                 # optional: span → that service's RED metrics
      datasourceUid: prometheus
```

`tags` maps the span's `service.name` resource attribute to the Loki `service` stream label — the only join key needed because the label set is low-cardinality by design. With all three legs wired the loop closes in both directions: metric exemplar → trace → logs → (derived field) back to trace.

## Multi-tenant

If you serve multiple teams from one stack, Loki and Tempo both support **tenant headers**:

- Forwarder / Collector sets `X-Scope-OrgID: team-orders`
- Loki keeps streams separate per tenant
- Per-tenant limits + retention via runtime config
- Grafana data source per tenant **or** Grafana with auth pinning the header

Most projects in this library are single-tenant. Skip multi-tenant unless you genuinely need it; it adds operational complexity.

## Grafana Cloud as a managed alternative

For teams that don't want to operate Loki + Tempo themselves, **Grafana Cloud** offers the same APIs, with paid limits. Same query language, same Grafana, less ops — pay for it if the time saved is worth it.

The skill's recipes work against self-hosted or Grafana Cloud — only the endpoint and auth differ.

## Operational concerns

- **Retention** is the #1 cost knob — tune per tier, per environment
- **Cardinality** is the #1 perf/cost killer — audit labels regularly
- **Recording rules** for expensive queries (`observability/logql-promql`) — compute once on ingest, query cheap
- **Compactor** in Loki / Tempo runs continuously — give it enough CPU/memory; without it small files accumulate
- **Object storage cost** can balloon — lifecycle policies for old chunks to cold tier (S3 IA / Glacier / Azure Cool / Archive)

## Rules

- Simple Scalable Loki for production
- Object storage on the cloud's native service (S3 / Blob / GCS); IRSA / Workload Identity for auth
- Retention tuned per tier; 30 days default; 7d for noisy, 90d+ for security/auth
- Index labels low-cardinality only (`service`, `environment`, `level`, `namespace`)
- High-cardinality stuff in the log body, parsed with `| json`
- OTel Collector is the central hub; configurable sampling/batching/routing without app changes
- Tempo `metrics_generator` enabled — free RED metrics + service graphs
- All three cross-store legs wired: exemplars (metrics→traces), Loki derived fields with the canonical cross-stack regex (logs→traces), `tracesToLogsV2` (traces→logs)
- One log forwarder per cluster (Grafana Alloy / Vector / Fluent Bit) — never two
- Grafana data sources defined declaratively via Helm / Terraform — reviewable in PR

## What NOT to do

- No `trace_id` / `user_id` / `request_id` as Loki labels
- No retention longer than 90 days at full fidelity on Loki without lifecycle policies (cost)
- No skipping object storage (Loki on local disk is a toy)
- No bypassing the Collector (apps pointing directly at Tempo / Loki) — kills your ability to evolve sampling/routing without redeploys
- No `:latest` image tags for Loki / Tempo / Collector
- No mixing single-tenant assumptions with a deployment configured for multi-tenant — `X-Scope-OrgID` discipline must be applied everywhere or nowhere
- No Loki without a `compactor` running — small-file death
- No "we'll figure out retention later" — defaults eat budget fast
- No two forwarders per node — pick one
- No keeping the same retention for verbose debug logs and security audit logs — set per-stream limits

## Generation steps

1. Confirm cluster, scale, retention, multi-tenant Y/N, log forwarder choice.
2. Deploy **Loki** (Helm `grafana/loki`) in Simple Scalable mode; point to S3 / Blob / GCS; configure retention.
3. Deploy **Tempo** (Helm `grafana/tempo`); point to object storage; enable `metrics_generator`.
4. Deploy **OTel Collector** with receivers + processors + exporters config; route traces → Tempo, metrics → Prometheus.
5. Deploy the log forwarder; restrict labels to the low-cardinality set; ship stdout JSON to Loki.
6. Wire **Grafana data sources** (Loki, Tempo, Prometheus); set up **exemplars** on Prom→Tempo, **derived fields** (canonical cross-stack regex) on Loki→Tempo, and **`tracesToLogsV2`** on Tempo→Loki.
7. Smoke the full loop: hit an app, find its logs in Loki by `{service=..., env=...}`, click the trace id to jump to Tempo, jump from a span back to its logs, see metrics with exemplars.
8. Add **retention monitoring** + **cardinality monitoring** queries to a "stack health" dashboard.

## Handoffs

- Query syntax → `observability/logql-promql`
- Dashboards → `observability/grafana-dashboards`
- App log shape → `observability/structured-logging-{stack}`
- App instrumentation → `observability/opentelemetry-{stack}`
- IaC for the storage buckets + IAM → `devops/iac-bicep-terraform`
- Kubernetes manifests for the Loki / Tempo / Collector stack → `devops/kubernetes`
