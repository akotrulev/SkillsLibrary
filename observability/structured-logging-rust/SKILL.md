---
name: structured-logging
description: Use when setting up structured logging in a Rust service with tracing (JSON, correlation IDs, Loki, redaction). Triggers "my Rust logs are not JSON". Not for traces or metrics (opentelemetry).
---

# Observability — Structured Logging (Rust, `tracing`)

In Rust, **`tracing` is the logging API**: an event (`info!`, `warn!`, `error!`) is a log line, and the spans it sits inside give it context. This skill owns what events say and how they are formatted on stdout. `opentelemetry-rust` owns the subscriber registry those layers plug into and the OTLP export of the same events. The `log` crate's macros still work: `tracing-subscriber` (feature `tracing-log`, on by default) forwards `log` records from dependencies into the same pipeline.

## Version detection

Read `Cargo.lock`: `tracing` 0.1 and `tracing-subscriber` 0.3 have had a stable API for years (0.1.44 / 0.3.23 as of 2026-10). A project on `env_logger`, `slog` or `log4rs` keeps it unless the task is the migration. Flag it, because none of those carry span context to OpenTelemetry.

## When to use

- A service printing with `println!` or logging unstructured text
- Choosing fields, levels, and messages for new code
- Logs reaching Loki without `trace_id`, or with secrets in them
- Configuring verbosity per module with `RUST_LOG`
- Panics that vanish without a log line

## When NOT to use

- Spans, metrics, OTLP export, the registry → `observability/opentelemetry-rust`
- Loki, Collector pipelines → `observability/logs-traces-setup`
- LogQL → `observability/queries`

## The stdout layer — `src/logging.rs`

```rust
use tracing::Subscriber;
use tracing_subscriber::{EnvFilter, Layer, registry::LookupSpan};

pub fn stdout_layer<S>() -> impl Layer<S>
where
    S: Subscriber + for<'span> LookupSpan<'span>,
{
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    tracing_subscriber::fmt::layer()
        .json()
        .flatten_event(true)
        .with_current_span(false)
        .with_span_list(true)
        .with_target(true)
        .with_filter(filter)
}
```

What each choice is for:

- **`json()`** — one JSON object per line on stdout, which the Collector or Alloy ships to Loki. The container runtime owns rotation; the service never writes log files.
- **`flatten_event(true)`** — event fields sit at the top level (`"order_id":"…"`), so LogQL can `| json | order_id="…"` without nesting.
- **`with_span_list(true)`** — every enclosing span's fields are emitted, including the root request span's `trace_id` recorded by `opentelemetry-rust`'s `request_span`. Emitting the current span alone loses `trace_id` as soon as a nested `#[instrument]` span is current.
- **`EnvFilter` from `RUST_LOG`** — per-module verbosity without a rebuild: `RUST_LOG=info,orders=debug,sqlx=warn,hyper=warn`. The default is `info`.

The layer is added to the registry in `telemetry::init()` (`opentelemetry-rust`). Tests do not install it — see *Tests*.

## Events — fields carry the data, the message names the event

```rust
tracing::info!(order.id = %order_id, customer.id = %customer_id, total_minor = total.minor(), "order placed");
tracing::warn!(sku = %sku, requested = qty, available, "stock short");
```

- The **message is a constant** that names what happened ("order placed"). Values go in fields so they are queryable and the message is greppable. `info!("order {order_id} placed")` puts the id in the message string, where it is neither — the `tracing` equivalent of string interpolation in a log template (`CLAUDE.md`).
- **`%` records with `Display`, `?` with `Debug`, bare for primitives.** Prefer `%` for ids and enums; `?` on a struct dumps every field, including the ones that should not be logged.
- **Field names are stable and dotted** where they mirror OTel semantic conventions (`http.route`, `db.system`, `order.id`). Renaming a field breaks every saved query and alert.
- Context that applies to many events belongs on the **span** (`#[instrument(fields(order.id = %id))]`), not repeated on each event.

## Levels

| Level | Use for | Production volume |
|---|---|---|
| `error!` | A failure the service could not handle and a human must look at: an unhandled 5xx, a background job that gave up | Rare; each one is alertable |
| `warn!` | A degraded but handled path: retry exhausted on an optional dependency, a fallback taken, input rejected for a reason worth watching | Low |
| `info!` | Business events and lifecycle: order placed, job finished, server listening, shutdown started | Moderate |
| `debug!` | Diagnostic detail for a developer: branch taken, intermediate values | Off in production |
| `trace!` | Very fine detail | Off |

A client's 4xx is **not** an `error!` — it is the client's mistake. Log it at `info!`/`warn!` or not at all; `TraceLayer` already records the status.

## Errors — log once, with the cause chain

```rust
match place_order(&state, command).await {
    Ok(order_id) => ...,
    Err(error) => {
        tracing::error!(error = &error as &dyn std::error::Error, "placing the order failed");
        ...
    }
}
```

- Record the error as `&dyn Error`. That marks the field as an error, and subscribers that understand errors (the OTel log bridge, the default text format) render its `source()` chain. `%error` prints only the top message, and `?error` prints `Debug` noise.
- **Log at the boundary that handles the error, once.** A function that returns `Err` does not also log it. Logging and returning produces the same failure three times in Loki.
- An `anyhow::Error` is logged with `error = ?error` — its `Debug` form includes the context chain.

## Secrets and personal data

- No `?` on a config, a request body, a token, or a struct whose `Debug` was derived over a secret. Hold secrets in `secrecy::SecretString`, whose `Debug` prints `[REDACTED]`.
- `#[instrument]` always gets `skip_all` (or an explicit `skip(...)`) — its default records every argument.
- Emails, names, addresses and IPs are personal data: log an id instead. Where the policy allows the value, hash it.
- Never log a full SQL query with its bound values, an `Authorization` header, or a cookie.

## Panics

A panic in a spawned task is reported to its `JoinHandle`; a panic on the main path prints to stderr outside the JSON stream. Install a hook in `main` right after telemetry init, so a panic becomes one structured line with a backtrace:

```rust
std::panic::set_hook(Box::new(|info| {
    let backtrace = std::backtrace::Backtrace::force_capture();
    tracing::error!(panic = %info, %backtrace, "panic");
}));
```

## Tests

Tests do not assert on logs (`unit-testing`). To see logs while debugging a test, use `tracing-subscriber`'s test writer behind an opt-in helper (`let _guard = tracing::subscriber::set_default(fmt().with_test_writer().finish());`). Never install a global subscriber in a test — the second test to do it panics.

## Rules

- Events carry data in fields; the message is a constant phrase
- `%` for ids and enums, `?` only on types whose `Debug` is safe to log
- JSON on stdout, span list included, filter from `RUST_LOG`
- `error!` only for what a human must act on; client 4xx is not an error
- Errors are logged once, where they are handled, with the source chain
- Secrets in `SecretString`; `#[instrument(skip_all)]`; no personal data in fields
- A panic hook emits panics as structured events

## What NOT to do

- No `println!` / `eprintln!` / `dbg!` in service code (clippy `print_stdout`, `print_stderr`, `dbg_macro`) — `eprintln!` in the telemetry shutdown path is the one exception
- No `format!` building the message from values
- No log files written by the service; no log rotation in-process
- No global subscriber installed by a library crate or a test
- No `?request` / `?config` / `?headers`
- No logging an error and returning it

## Generation steps

1. Write `src/logging.rs` with `stdout_layer()`; confirm `telemetry::init()` adds it.
2. Replace `println!`/`log` calls in service code with `tracing` events, moving values into fields.
3. Add `skip_all` to every existing `#[instrument]` and name the fields.
4. Install the panic hook in `main`.
5. Check one request's log lines in Loki carry `trace_id`, and that no secret appears in a sample of lines.

## Handoffs

- Registry, spans, OTLP export → `observability/opentelemetry-rust`
- Shipping logs to Loki → `observability/logs-traces-setup`
- LogQL → `observability/queries`
- .NET / Java / Node equivalents → `observability/structured-logging-{dotnet,java,node}`
