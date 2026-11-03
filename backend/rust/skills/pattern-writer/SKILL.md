---
name: patterns-apply
description: Use when scaffolding Rust backend code (axum + tokio skeleton, typed config, thiserror errors, handlers). Triggers "scaffold a Rust service". Not for explanations (patterns).
---

# Rust — Generator

Scaffolds Rust service and library code into the active repo: **axum 0.8 on tokio 1.x**, `thiserror` errors at module boundaries and `anyhow` only in `main`, newtypes at every boundary, one `AppState` built in `main`, and lints configured once in `Cargo.toml`. Prefers the language feature (enum, newtype, function) over a trait, and a concrete type over a generic, until a second real need exists.

## Version policy

Detect before writing: `rust-toolchain.toml`, `Cargo.toml` `edition` + `rust-version`, `Cargo.lock` for tokio / axum / sqlx / tower-http. **Current stable is 1.99 (2026-10); edition 2024 primary, 2021 supported.** Match what the project declares — never raise the edition, `rust-version`, or a dependency's major as a side effect.

| Crate | Current (2026-10) | Notes that change code |
|---|---|---|
| axum | 0.8 | Paths are `/{id}` and `/{*rest}` (0.7 used `/:id`); custom extractors use native `async fn`, no `#[async_trait]`; `Option<T>` extractors need `OptionalFromRequestParts` |
| tower-http | 0.7 | `TimeoutLayer::with_status_code` (`::new` deprecated since 0.6.7); unacceptable `Accept-Encoding` gets 406 |
| tokio | 1.54 (LTS 1.51.x, 1.53.x) | — |
| thiserror | 2 | — |
| sqlx | 0.9 (needs Rust 1.94) | see `database-code` |

A **new service** pins `rust-toolchain.toml` to a specific stable and sets `rust-version` to the same value. A **library** sets `rust-version` to the oldest toolchain it supports and tests it in CI — edition 2024's resolver 3 then prefers dependency versions that build on it.

## When to use

- A new Rust service or crate
- Adding an endpoint, an extractor, an error variant, a newtype, a module
- Replacing `String`/`Uuid`/`i64` ids, `unwrap()`s, or scattered `std::env::var` reads
- Splitting a growing crate along module boundaries

## When NOT to use

- Explaining a pattern → `pattern-guide`
- Queries, migrations, transactions → `database-code`
- Spawning, cancellation, locks, shutdown internals → `async-concurrency`
- Telemetry wiring → `observability/opentelemetry-rust` (via `observability-engineer-rust`)
- Tests → `unit-testing`

## Inputs needed

1. Service or library; binary name
2. The endpoints or operations to add, with their failure cases
3. Persistence (sqlx + Postgres by default — `database-code`)
4. Whether the codebase is one crate or a workspace of module crates

## Project skeleton

```
Cargo.toml
Cargo.lock                 # committed for every binary
rust-toolchain.toml
clippy.toml
migrations/
src/
  main.rs                  # wiring only: telemetry, config, pool, state, serve
  lib.rs                   # module declarations + `pub fn app(state) -> Router`
  config.rs
  error.rs                 # ApiError + IntoResponse
  state.rs                 # AppState
  telemetry.rs  logging.rs # observability/opentelemetry-rust, structured-logging-rust
  orders.rs                # module root: the public surface of the orders module
  orders/
    http.rs                # handlers + request/response DTOs
    domain.rs              # newtypes, rules, PlaceOrderError
    store.rs               # sqlx queries
```

`main.rs` stays thin and everything else lives in the library target, so `tests/` and benches can build the router without the binary. Modules are by **feature** (`orders/`), not by layer (`handlers/`, `services/`).

### `Cargo.toml`

```toml
[package]
name = "orders-service"
version = "0.1.0"
edition = "2024"
rust-version = "1.99"
publish = false

[dependencies]
anyhow = "1"
axum = "0.8"
secrecy = "0.10"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
time = { version = "0.3", features = ["serde"] }
tokio = { version = "1", features = ["macros", "rt-multi-thread", "signal"] }
tokio-util = { version = "0.7", features = ["rt"] }
tower-http = { version = "0.7", features = ["trace", "timeout", "limit", "catch-panic"] }
tracing = "0.1"
uuid = { version = "1", features = ["v7", "serde"] }

[dev-dependencies]
rstest = "0.28"
tokio = { version = "1", features = ["macros", "rt", "test-util"] }

[lints.rust]
unsafe_code = "forbid"

[lints.clippy]
pedantic = { level = "warn", priority = -1 }
missing_errors_doc = "allow"
missing_panics_doc = "allow"
unwrap_used = "deny"
panic = "warn"
todo = "warn"
unimplemented = "warn"
dbg_macro = "warn"
print_stdout = "warn"
print_stderr = "warn"
allow_attributes_without_reason = "warn"
undocumented_unsafe_blocks = "deny"

[profile.release]
debug = "line-tables-only"
```

- **Lints live here, once** — `[workspace.lints]` in a workspace root, with `[lints] workspace = true` in each member. Groups get `priority = -1` so single lints override them. Never pick the whole `restriction` group (clippy itself lints that); pick lints from it by name.
- A justified exception is `#[expect(clippy::lint_name, reason = "…")]` on the item, never a crate-wide `#![allow]`. `#[expect]` warns when the exception stops being needed.
- Libraries keep `missing_errors_doc` / `missing_panics_doc` on and drop `unsafe_code = "forbid"` only for the module that needs it.
- Telemetry and sqlx dependencies are added by their skills.

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.99"
components = ["rustfmt", "clippy"]
```

```toml
# clippy.toml
allow-unwrap-in-tests = true
allow-expect-in-tests = true
```

## Config — read once, typed, secrets wrapped

```rust
use std::{net::SocketAddr, str::FromStr};

use secrecy::SecretString;

#[derive(Debug, Clone)]
pub struct Config {
    pub listen_addr: SocketAddr,
    pub database_url: SecretString,
    pub db_max_connections: u32,
    pub request_timeout_secs: u64,
}

#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("environment variable {0} is required")]
    Missing(&'static str),
    #[error("environment variable {name} is invalid: {reason}")]
    Invalid { name: &'static str, reason: String },
}

impl Config {
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            listen_addr: parsed("LISTEN_ADDR", "0.0.0.0:8080")?,
            database_url: SecretString::from(required("DATABASE_URL")?),
            db_max_connections: parsed("DB_MAX_CONNECTIONS", "10")?,
            request_timeout_secs: parsed("REQUEST_TIMEOUT_SECS", "10")?,
        })
    }
}

fn required(name: &'static str) -> Result<String, ConfigError> {
    std::env::var(name).map_err(|_| ConfigError::Missing(name))
}

fn parsed<T>(name: &'static str, default: &str) -> Result<T, ConfigError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    let raw = std::env::var(name).unwrap_or_else(|_| default.to_owned());
    raw.parse().map_err(|error: T::Err| ConfigError::Invalid { name, reason: error.to_string() })
}
```

`std::env::var` is read here and nowhere else; everything downstream receives `Config` or the part it needs. A handful of variables does not earn a config crate. When the project needs layered files plus env, use `config` 0.15 (maintained). `figment` and `envy` have had no release since 2024 and 2021.

## Newtypes and domain errors

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(transparent)]
pub struct OrderId(uuid::Uuid);

impl OrderId {
    pub fn new() -> Self {
        Self(uuid::Uuid::now_v7())
    }
}

impl std::fmt::Display for OrderId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        std::fmt::Display::fmt(&self.0, f)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Quantity(u32);

impl TryFrom<u32> for Quantity {
    type Error = PlaceOrderError;

    fn try_from(raw: u32) -> Result<Self, Self::Error> {
        if (1..=1_000).contains(&raw) {
            Ok(Self(raw))
        } else {
            Err(PlaceOrderError::QuantityOutOfRange(raw))
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub enum PlaceOrderError {
    #[error("the order has no lines")]
    EmptyOrder,
    #[error("quantity {0} is outside 1..=1000")]
    QuantityOutOfRange(u32),
    #[error("sku {0} is out of stock")]
    OutOfStock(Sku),
    #[error("order total overflowed")]
    TotalOverflow,
    #[error(transparent)]
    Database(#[from] sqlx::Error),
}
```

One error enum per operation or module, each variant a case the caller handles differently. `Database(#[from] sqlx::Error)` is the one infrastructure variant; it maps to 500.

## `ApiError` — the one place errors become HTTP

```rust
use axum::{Json, http::StatusCode, response::{IntoResponse, Response}};
use serde::Serialize;

#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("request body is invalid")]
    InvalidBody(#[from] axum::extract::rejection::JsonRejection),
    #[error("{0}")]
    Unprocessable(String),
    #[error("resource not found")]
    NotFound,
    #[error("the resource was changed by another request")]
    Conflict,
    #[error("internal error")]
    Internal(#[source] Box<dyn std::error::Error + Send + Sync>),
}

#[derive(Serialize)]
struct Problem {
    #[serde(rename = "type")]
    kind: &'static str,
    title: &'static str,
    status: u16,
    detail: String,
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, title) = match &self {
            ApiError::InvalidBody(rejection) => (rejection.status(), "Invalid request body"),
            ApiError::Unprocessable(_) => (StatusCode::UNPROCESSABLE_ENTITY, "Validation failed"),
            ApiError::NotFound => (StatusCode::NOT_FOUND, "Not found"),
            ApiError::Conflict => (StatusCode::CONFLICT, "Conflict"),
            ApiError::Internal(source) => {
                tracing::error!(error = source.as_ref() as &dyn std::error::Error, "request failed");
                (StatusCode::INTERNAL_SERVER_ERROR, "Internal error")
            }
        };
        let problem = Problem { kind: "about:blank", title, status: status.as_u16(), detail: self.to_string() };
        let mut response = (status, Json(problem)).into_response();
        response.headers_mut().insert(
            axum::http::header::CONTENT_TYPE,
            axum::http::HeaderValue::from_static("application/problem+json"),
        );
        response
    }
}

impl From<PlaceOrderError> for ApiError {
    fn from(error: PlaceOrderError) -> Self {
        match error {
            PlaceOrderError::EmptyOrder
            | PlaceOrderError::QuantityOutOfRange(_)
            | PlaceOrderError::OutOfStock(_)
            | PlaceOrderError::TotalOverflow => ApiError::Unprocessable(error.to_string()),
            PlaceOrderError::Database(source) => ApiError::Internal(Box::new(source)),
        }
    }
}
```

- The `From<DomainError>` impl is an **exhaustive match**, so a new domain variant forces a decision about its status code. Never use a blanket `From<anyhow::Error>` that sends every failure to 500.
- The 500 body says "internal error". The source is logged once, here, and never sent to the client.
- The shape follows the plan's `api-surface.md` validation catalog when one exists. That catalog wins over this sketch: field-level `errors[]`, the `type` URIs, 401/403 handling.

### Body rejections as problems

axum's built-in `Json` rejection replies in `text/plain`. Wrap it so every 4xx has the same shape:

```rust
#[derive(axum::extract::FromRequest)]
#[from_request(via(axum::Json), rejection(ApiError))]
pub struct AppJson<T>(pub T);

impl<T: Serialize> IntoResponse for AppJson<T> {
    fn into_response(self) -> Response {
        Json(self.0).into_response()
    }
}
```

The derive needs axum's `macros` feature. Handlers take `AppJson<T>` instead of `Json<T>`.

## `AppState` — the composition root

```rust
#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::PgPool,
    pub order_metrics: OrderMetrics,
}
```

Built once in `main` and cloned per request: every field is cheap to clone (`PgPool` and the OTel instruments are `Arc` inside). Handlers extract `State<AppState>`. A field that is not `Clone` gets wrapped in `Arc`. A collaborator becomes `Arc<dyn Trait>` only when a second implementation or a test fake of an outbound seam exists (`pattern-guide` → Traits as ports). Native `async fn` traits are not dyn-compatible: such a trait keeps `#[async_trait]`.

## Handler

```rust
#[derive(serde::Deserialize)]
pub struct PlaceOrderRequest {
    pub lines: Vec<LineRequest>,
}

#[derive(serde::Serialize)]
pub struct PlaceOrderResponse {
    pub id: OrderId,
}

pub async fn place_order(
    State(state): State<AppState>,
    AppJson(body): AppJson<PlaceOrderRequest>,
) -> Result<(StatusCode, AppJson<PlaceOrderResponse>), ApiError> {
    let command = PlaceOrder::try_from(body)?;
    let placed = orders::place(&state.db, command, time::OffsetDateTime::now_utc()).await?;
    state.order_metrics.record_placed(placed.channel, placed.total_minor);
    Ok((StatusCode::CREATED, AppJson(PlaceOrderResponse { id: placed.id })))
}
```

- A handler is transport only: extract, convert the DTO into a domain command (`TryFrom`), call the module, map the result. A business rule in a handler is a finding.
- **Time is a parameter.** The handler reads the clock once and passes `now` down, so domain functions are pure and tests pass a fixed instant without a `Clock` trait. Ids work the same way when a test needs a known value.
- DTOs (`*Request`/`*Response`) are separate from domain types. A domain type never derives `Deserialize` from client input; it is built through its fallible constructor.

## Router and layers

```rust
pub fn app(state: AppState, config: &Config) -> Router {
    Router::new()
        .route("/orders", post(orders::http::place_order))
        .route("/orders/{id}", get(orders::http::get_order))
        .route("/health/live", get(|| async { StatusCode::NO_CONTENT }))
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http().make_span_with(request_span).on_response(record_response))
                .layer(CatchPanicLayer::new())
                .layer(TimeoutLayer::with_status_code(
                    StatusCode::REQUEST_TIMEOUT,
                    Duration::from_secs(config.request_timeout_secs),
                ))
                .layer(RequestBodyLimitLayer::new(1024 * 1024)),
        )
        .with_state(state)
}
```

`ServiceBuilder` applies layers top to bottom, so tracing sees everything, including a timeout or a panic. Every service has an edge timeout, because without one graceful shutdown waits forever on a stuck request. It also has a body limit; axum's default is 2 MB, and the limit should be set on purpose. `request_span` / `record_response` come from `observability/opentelemetry-rust`.

## `main`

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let telemetry = telemetry::init()?;
    let result = run().await;
    telemetry.shutdown();
    result
}

async fn run() -> anyhow::Result<()> {
    let config = Config::from_env()?;
    let db = store::connect(&config).await?;
    let state = AppState { db: db.clone(), order_metrics: OrderMetrics::new() };
    let listener = tokio::net::TcpListener::bind(config.listen_addr).await?;
    tracing::info!(addr = %config.listen_addr, "listening");

    let token = CancellationToken::new();
    axum::serve(listener, app(state, &config))
        .with_graceful_shutdown(shutdown_signal(token.clone()))
        .await?;

    db.close().await;
    Ok(())
}
```

`anyhow` lives here and nowhere below it. `shutdown_signal` and the background-task tracker come from `async-concurrency` → Graceful shutdown. `store::connect` comes from `database-code`.

## Module boundaries — crate per module

A modular monolith that will be split later (blueprint `Modules:` line) is a **Cargo workspace with one library crate per module** plus one binary crate that composes them:

```
Cargo.toml                 # [workspace] members, [workspace.dependencies], [workspace.lints]
crates/app/                # the binary: config, telemetry, router composition
crates/orders/             # lib: pub fn router() -> Router<AppState>, pub commands, pub events
crates/billing/            # lib
```

- **The compiler is the architecture test.** `billing` can reach `orders` only if `crates/billing/Cargo.toml` lists it, and then only its `pub` items. Keep internals `pub(crate)` and re-export the module's surface from `lib.rs`. No dependency-cruiser equivalent is needed.
- **One schema per module.** Each module crate owns a `migrations/` folder whose tables live in its own Postgres schema (`orders.orders`). It holds another module's id as a plain column, with no foreign key into that schema (`database-code`).
- Shared versions and lints are declared once in `[workspace.dependencies]` / `[workspace.lints]`, with `dep = { workspace = true }` in members.
- **A call between modules** is a plain function on the other crate's public surface, taking the pool or the state it needs. **An event** is a type exported by the publisher, delivered in-process through a `tokio::sync::broadcast` or an outbox. Add one only when a second consumer, or "must not fail the publisher", earns it.
- A single-crate service does not become a workspace in anticipation. Split when the blueprint names modules or a second binary appears.

## Rules

The standards this skill's output must meet are the be-rust rule files, not a list here: `rust.md`, and `cargo.md` for the manifest and toolchain. Read the project's copy in `.claude/rules/be-rust/`, or the plugin's in `backend/rust/skills/rules/` when the project has not installed them (`/be-rust:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Generation outputs

1. The types (`domain.rs`), the handlers and DTOs (`http.rs`), the module root's public surface
2. The `ApiError` mapping for every new domain variant
3. Route registration in `app()` and any new `AppState` field, built in `main`
4. Unit tests for every logic-bearing unit — conventions in `unit-testing` (both arms of every `Result`, `rstest` cases, time passed in)
5. In a workspace: the crate's `Cargo.toml` with `workspace = true` lints, its `lib.rs` surface, its migrations folder

## Validation

Run:

- `cargo fmt --check`
- `cargo clippy --all-targets --all-features --locked` with warnings as errors. Use `CARGO_BUILD_WARNINGS=deny` on 1.97+: it does not invalidate the build cache the way `-D warnings` in `RUSTFLAGS` does. On older toolchains, use `-- -D warnings`.
- `cargo nextest run` (or `cargo test`) plus `cargo test --doc` — nextest does not run doctests
- Sweep the old call sites the new type replaces

## Handoffs

- Concepts → `pattern-guide`
- Queries, pool, migrations → `database-code`
- Tasks, shutdown, locks → `async-concurrency`
- Telemetry init, `TraceLayer` span functions, metrics → `observability/opentelemetry-rust`
- Tests → `unit-testing`
- Review → `code-review`
