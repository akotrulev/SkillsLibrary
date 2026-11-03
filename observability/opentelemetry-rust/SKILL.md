---
name: opentelemetry
description: Use when instrumenting a Rust axum service with OpenTelemetry (traces, metrics, log correlation, OTLP). Triggers "spans missing in Tempo". Not for log shaping (structured-logging).
---

# Observability — OpenTelemetry (Rust, tokio + axum)

Instruments a Rust service with OpenTelemetry **through the `tracing` ecosystem**: code emits `tracing` spans and events, and the `tracing-subscriber` registry fans them out — to a JSON format layer for stdout, to `tracing-opentelemetry` for OTel traces, and to `opentelemetry-appender-tracing` for OTel logs. Metrics use the OTel meter API directly. All three signals export OTLP to a Collector that forwards to Tempo / Prometheus / Loki.

Rust has no auto-instrumentation agent: **what is not wrapped in a span does not exist in Tempo.** The HTTP edge comes from `tower_http::trace::TraceLayer`, sqlx and reqwest calls get spans because you instrument the functions that make them, and everything else is `#[tracing::instrument]` on the operations that matter.

## Version detection

First act: read `Cargo.lock` for `opentelemetry`, `opentelemetry_sdk`, `opentelemetry-otlp`, `opentelemetry-appender-tracing`, `opentelemetry-http` and `tracing-opentelemetry`. **They are one release train and must match:** as of 2026-10 the train is **`opentelemetry*` 0.33** with **`tracing-opentelemetry` 0.34** (that crate's version runs one ahead). Mixed minors fail to compile with confusing trait errors ("`SdkTracer` does not implement `PreSampledTracer`"). The 0.2x → 0.3x releases renamed most of the SDK (`TracerProvider` → `SdkTracerProvider`, `new_pipeline()` → exporter builders, `Resource::new` → `Resource::builder()`); **an existing project keeps its train** — never port it to a newer one as a side effect of adding a span.

Stability (opentelemetry-rust README, 2026-10): **metrics and logs are Stable; traces (API, SDK, OTLP) are still Beta**; there is no 1.0 and no stated date. Expect breaking changes between minors on the trace side.

## Stack

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-opentelemetry = "0.34"
opentelemetry = "0.33"
opentelemetry_sdk = "0.33"
opentelemetry-otlp = { version = "0.33", features = ["grpc-tonic"] }
opentelemetry-appender-tracing = "0.33"
opentelemetry-http = "0.33"
tower-http = { version = "0.7", features = ["trace"] }
```

`grpc-tonic` exports over gRPC on 4317. Without it, the exporters use HTTP/protobuf on 4318 (`.with_http()`). Pick the one the Collector exposes, and use one transport for all three signals.

## When to use

- A Rust service with no telemetry, or with `println!`/`env_logger` only
- Spans missing, detached from their parent, or not continuing an incoming trace
- Adding a counter or histogram for a business event
- Logs that reach stdout but not Loki, or reach Loki without `trace_id`
- The last spans before shutdown never arrive

## When NOT to use

- Event and field conventions, `EnvFilter`, redaction → `observability/structured-logging-rust`
- Collector / Loki / Tempo / Prometheus setup → `observability/logs-traces-setup`, `observability/metrics-setup`
- Dashboards and queries → `observability/dashboards`, `observability/queries`
- .NET / Java / Node → their `opentelemetry-*` siblings

## Inputs needed

1. **Service name, version, environment** — from `OTEL_SERVICE_NAME`, `CARGO_PKG_VERSION`, `OTEL_RESOURCE_ATTRIBUTES=deployment.environment.name=…`
2. **Collector endpoint** — `OTEL_EXPORTER_OTLP_ENDPOINT` (the exporter builders read it)
3. **Sampling** — `OTEL_TRACES_SAMPLER=parentbased_traceidratio`, `OTEL_TRACES_SAMPLER_ARG=0.1` in production
4. **The operations worth a span** — handlers come free from `TraceLayer`; name the domain operations, outbound calls, and background jobs

## The telemetry module — `src/telemetry.rs`

```rust
use opentelemetry::{KeyValue, global, trace::TracerProvider as _};
use opentelemetry_appender_tracing::layer::OpenTelemetryTracingBridge;
use opentelemetry_otlp::{LogExporter, MetricExporter, SpanExporter, WithExportConfig as _};
use opentelemetry_sdk::{
    Resource, logs::SdkLoggerProvider, metrics::SdkMeterProvider,
    propagation::TraceContextPropagator, trace::SdkTracerProvider,
};
use tracing_subscriber::{EnvFilter, Layer as _, layer::SubscriberExt as _, util::SubscriberInitExt as _};

pub struct Telemetry {
    tracer_provider: SdkTracerProvider,
    logger_provider: SdkLoggerProvider,
    meter_provider: SdkMeterProvider,
}

#[derive(Debug, thiserror::Error)]
pub enum TelemetryError {
    #[error("building an OTLP exporter")]
    Exporter(#[from] opentelemetry_otlp::ExporterBuildError),
    #[error("parsing a log filter directive")]
    Filter(#[from] tracing_subscriber::filter::ParseError),
    #[error("installing the global subscriber")]
    Subscriber(#[from] tracing_subscriber::util::TryInitError),
}

pub fn init() -> Result<Telemetry, TelemetryError> {
    let resource = Resource::builder()
        .with_attribute(KeyValue::new("service.version", env!("CARGO_PKG_VERSION")))
        .build();

    let meter_provider = SdkMeterProvider::builder()
        .with_resource(resource.clone())
        .with_periodic_exporter(MetricExporter::builder().with_tonic().build()?)
        .build();
    global::set_meter_provider(meter_provider.clone());

    let logger_provider = SdkLoggerProvider::builder()
        .with_resource(resource.clone())
        .with_batch_exporter(LogExporter::builder().with_tonic().build()?)
        .build();

    let tracer_provider = SdkTracerProvider::builder()
        .with_resource(resource)
        .with_batch_exporter(SpanExporter::builder().with_tonic().build()?)
        .build();
    global::set_tracer_provider(tracer_provider.clone());
    global::set_text_map_propagator(TraceContextPropagator::new());

    let exporter_transport_off = EnvFilter::new("info")
        .add_directive("hyper=off".parse()?)
        .add_directive("tonic=off".parse()?)
        .add_directive("h2=off".parse()?)
        .add_directive("reqwest=off".parse()?);

    tracing_subscriber::registry()
        .with(crate::logging::stdout_layer())
        .with(
            tracing_opentelemetry::layer()
                .with_tracer(tracer_provider.tracer(env!("CARGO_PKG_NAME")))
                .with_filter(EnvFilter::new("info")),
        )
        .with(OpenTelemetryTracingBridge::new(&logger_provider).with_filter(exporter_transport_off))
        .try_init()?;

    Ok(Telemetry { tracer_provider, logger_provider, meter_provider })
}

impl Telemetry {
    pub fn shutdown(self) {
        let results = [
            ("tracer", self.tracer_provider.shutdown()),
            ("logger", self.logger_provider.shutdown()),
            ("meter", self.meter_provider.shutdown()),
        ];
        for (provider, result) in results {
            if let Err(error) = result {
                eprintln!("{provider} provider shutdown failed: {error}");
            }
        }
    }
}
```

What each choice is for:

- **`Resource::builder()`** includes the default detectors, so `OTEL_SERVICE_NAME` and `OTEL_RESOURCE_ATTRIBUTES` are read from the environment; only the version comes from the build.
- **The meter provider is built first** so the batch processors built after it can report their own metrics.
- **The transport crates are switched off on the log bridge** — otherwise the exporter's own `hyper`/`tonic` logs are exported, which produces more logs, in a loop (opentelemetry-rust issue #2877).
- **`init()` runs inside the tokio runtime** (`#[tokio::main]`), because the tonic exporters need it.
- **Shutdown order is tracer → logger → meter** (the official example's order: the log processor may emit metrics while shutting down). `shutdown` is the one place `eprintln!` is right — the subscriber may already be gone.
- `crate::logging::stdout_layer()` is the JSON format layer from `structured-logging-rust`.

### Wiring in `main`

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let telemetry = telemetry::init()?;
    let config = Config::from_env()?;
    let result = run(config).await;
    telemetry.shutdown();
    result
}
```

`run` owns the server and its graceful shutdown (`async-concurrency` → Graceful shutdown). Telemetry is shut down **after** `run` returns on both the success and the error path — `?` inside `main` before `shutdown()` would lose the last batch exactly when it matters.

## Inbound HTTP — `TraceLayer` that continues the caller's trace

```rust
use std::time::Duration;

use axum::{body::Body, extract::MatchedPath, http::Request, response::Response};
use opentelemetry::trace::TraceContextExt as _;
use opentelemetry_http::HeaderExtractor;
use tracing::Span;
use tracing_opentelemetry::OpenTelemetrySpanExt as _;

pub fn request_span(request: &Request<Body>) -> Span {
    let route = request
        .extensions()
        .get::<MatchedPath>()
        .map_or("unmatched", MatchedPath::as_str);
    let span = tracing::info_span!(
        "http.request",
        otel.name = %format!("{} {route}", request.method()),
        otel.kind = "server",
        otel.status_code = tracing::field::Empty,
        http.request.method = %request.method(),
        http.route = route,
        http.response.status_code = tracing::field::Empty,
        trace_id = tracing::field::Empty,
    );
    let parent = opentelemetry::global::get_text_map_propagator(|propagator| {
        propagator.extract(&HeaderExtractor(request.headers()))
    });
    if let Err(error) = span.set_parent(parent) {
        tracing::debug!(%error, "incoming trace context ignored");
    }
    let trace_id = span.context().span().span_context().trace_id();
    span.record("trace_id", tracing::field::display(trace_id));
    span
}

pub fn record_response(response: &Response, _latency: Duration, span: &Span) {
    let status = response.status();
    span.record("http.response.status_code", status.as_u16());
    if status.is_server_error() {
        span.record("otel.status_code", "ERROR");
    }
}
```

```rust
let app = Router::new()
    .route("/orders/{id}", get(get_order))
    .layer(TraceLayer::new_for_http().make_span_with(request_span).on_response(record_response))
    .with_state(state);
```

- **`otel.name` uses the route template** (`GET /orders/{id}`), never the URL — a span name per order id is unbounded.
- `otel.kind = "server"` makes Tempo's service graph work. `otel.status_code = "ERROR"` marks the span failed, and only 5xx does that: a 4xx is the client's error, not the server's.
- Recording `trace_id` as a **span field** puts it on every JSON log line inside the request (`structured-logging-rust` emits the current span's fields), which is what Loki's derived field links on.
- `MatchedPath` is available because `Router::layer` wraps each route after routing. A request that matches no route gets `unmatched`.
- `set_parent` returns `Result` from `tracing-opentelemetry` 0.32.1 onwards. An invalid incoming `traceparent` starts a new trace — log it at `debug`, never fail the request.

## Custom spans — operations, not functions

```rust
#[tracing::instrument(name = "order.place", skip_all, fields(customer.id = %command.customer_id, order.id = tracing::field::Empty))]
pub async fn place_order(state: &AppState, command: PlaceOrder) -> Result<OrderId, PlaceOrderError> {
    let order_id = OrderId::new();
    tracing::Span::current().record("order.id", tracing::field::display(order_id));
    ...
}
```

- **`skip_all`** and name the fields you want. The default records every argument with `Debug` — a request body, a pool, or a secret lands in Tempo.
- `#[instrument(err)]` records the returned error as an event at `ERROR`; use it on operations whose error is not already logged by the caller, never on both.
- A future spawned onto the runtime keeps its parent only if instrumented: `tokio::spawn(work.instrument(tracing::Span::current()))`. Never `let _guard = span.enter();` across an `.await` (`async-concurrency`).
- Background jobs start a **new root span per unit of work** (`info_span!(parent: None, "outbox.relay.batch")`), not one span for the life of the loop.

## Outbound propagation

```rust
use opentelemetry_http::HeaderInjector;

let mut headers = reqwest::header::HeaderMap::new();
opentelemetry::global::get_text_map_propagator(|propagator| {
    propagator.inject_context(&tracing::Span::current().context(), &mut HeaderInjector(&mut headers));
});
let response = client.get(url).headers(headers).send().await?;
```

For a message broker, inject into the message headers the same way and extract on the consumer with `HeaderExtractor`-style adapters for the broker's header type.

## Metrics

```rust
use opentelemetry::{KeyValue, global, metrics::{Counter, Histogram}};

#[derive(Clone)]
pub struct OrderMetrics {
    placed: Counter<u64>,
    value: Histogram<u64>,
}

impl OrderMetrics {
    pub fn new() -> Self {
        let meter = global::meter("orders");
        Self {
            placed: meter.u64_counter("orders.placed").with_unit("{order}").build(),
            value: meter.u64_histogram("orders.value").with_unit("{minor_unit}").build(),
        }
    }

    pub fn record_placed(&self, channel: Channel, value_minor: u64) {
        let attributes = [KeyValue::new("channel", channel.as_str())];
        self.placed.add(1, &attributes);
        self.value.record(value_minor, &attributes);
    }
}
```

- Instruments are created **once** (in `AppState` construction) and cloned — creating one per request re-registers it.
- Attribute values come from a closed set (`channel`, `outcome`, `http.route`), never ids.
- **HTTP RED metrics** are not produced by `TraceLayer`. Add one `axum::middleware::from_fn` that times the inner call and records `http.server.request.duration` (seconds, histogram) with `http.request.method`, `http.route` (from `MatchedPath`) and `http.response.status_code` — exactly those three attributes.

## Sampling

- Dev: the SDK default (parent-based always-on).
- Prod: `OTEL_TRACES_SAMPLER=parentbased_traceidratio` + `OTEL_TRACES_SAMPLER_ARG=0.1`, set in the deployment, not in code.
- Tail sampling (keep errors and slow traces) belongs in the Collector.

## Rules

- One telemetry init, called first in `main`, inside the runtime; libraries never install a subscriber
- The `opentelemetry*` crates and `tracing-opentelemetry` on one train
- Every signal exports OTLP to the Collector; endpoint, service name and sampler from `OTEL_*` env vars
- Span names are operation names or route templates, never values
- `#[instrument(skip_all, fields(...))]` — never record arguments wholesale
- Futures carry spans with `.instrument()`; no `enter()` guard across `.await`
- Metric attributes are bounded; ids go on spans
- Providers shut down tracer → logger → meter after the server drains, on every exit path

## What NOT to do

- No exporter pointed straight at Tempo / Prometheus / Loki — go through a Collector
- No `std::process::exit` after init — it skips the flush; return from `main`
- No `opentelemetry-prometheus` scrape endpoint alongside OTLP metrics — pick OTLP
- No log bridge without the transport filter — the exporter's logs feed back into themselves
- No span per small function — instrument operations (request, query batch, outbound call, job)
- No `#[instrument]` without `skip_all` on a function taking a body, a config, or a client
- No upgrading the OTel train to add one span

## Generation steps

1. Detect the train in `Cargo.lock`; on a new project, add the stack above.
2. Write `src/telemetry.rs`; call `init()` first in `main` and `shutdown()` after `run` returns.
3. Add `TraceLayer::new_for_http().make_span_with(request_span).on_response(record_response)` to the router, plus the RED-metrics middleware.
4. Add `#[instrument(skip_all, fields(...))]` to 3–5 domain operations and every background job's unit of work; propagate on outbound calls.
5. Add the counter/histogram for the service's core business event.
6. Local smoke against `deploy/local/` (Collector + Tempo + Loki + Prometheus + Grafana): one request shows a trace in Tempo with a `GET /orders/{id}` root span, a log line in Loki with the same `trace_id`, and a series for `http_server_request_duration_seconds`.

## Handoffs

- JSON log layer, fields, redaction → `observability/structured-logging-rust`
- Collector and backends → `observability/logs-traces-setup`, `observability/metrics-setup`
- Queries and dashboards → `observability/queries`, `observability/dashboards`
- The service code being instrumented → `be-rust`
- .NET / Java / Node equivalents → `observability/opentelemetry-{dotnet,java,node}`
