---
paths:
  - "**/*.rs"
---

<!-- be-rust rules v1 (2026-11-03): core. Installed by /be-rust:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Rust / axum / tokio code standards

Apply these to every Rust file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Persistence, test and Cargo rules are separate files that load with those files; an inline `#[cfg(test)]` module matches no test glob, so Read `rust-tests.md` before writing one.

**The codebase wins.** Where this project consistently does something another way, follow it and do not flag it. Detect the toolchain (`rust-toolchain.toml`, `edition` and `rust-version`, the crate versions in `Cargo.lock`): never use an API newer than `rust-version` (`async fn` in traits 1.75, `LazyLock` 1.80, async closures 1.85), and never flag a 2021-edition crate for lacking a 2024-only form.

## Simplicity

- Simplest thing that meets the requirement. No trait with one implementer and no fake, no generic with one instantiation, no `*Service` → `*Repository` → sqlx forwarding, no builder under four optional fields. An abstraction is earned on the second real need. *major, fix by inlining*
- `enum` + `match` before a trait; `Arc<dyn Trait>` only for open implementations or a fake of an outbound seam. One pattern per problem. *major*
- Cut structure, never correctness: validation, errors, timeouts, cancellation, shutdown and tests stay.
- Modules by feature, not layer; private by default. *minor*

## Ownership and types

- Borrow what is only read (`&str`, `&[T]`, never `&String` / `&Vec<T>`); own what is stored. *minor*
- A `.clone()` of a `Vec`, `String` or struct to quiet the borrow checker is a redesign signal. *major on a hot path, minor elsewhere*
- No `Rc<RefCell<T>>` / `Arc<Mutex<T>>` where single ownership or a channel would do, nor for data the database owns. *major*
- Ids, quantities and money are newtypes built only through a fallible `TryFrom` / `FromStr`; money is integer minor units, never `f64`; request DTOs are separate types. *major*
- No `_ =>` arm on an enum this crate owns; a growing public enum is `#[non_exhaustive]`. *major; minor for non_exhaustive*
- `let _ = guard;` drops it at once: bind `_guard`. *major*
- No global mutable state; no `lazy_static!` / `once_cell` in new code, `LazyLock` for immutable data. *major*

## Panics and errors

- No `unwrap()` outside tests; `expect("…")` only where the message states the invariant; no input-derived `[i]`. *blocker in a request path, major elsewhere*
- `thiserror` enums, one variant per case the caller handles; `anyhow` only in `main`. Never `Box<dyn Error>` / `anyhow::Error` in a library's `pub` signature. *major*
- One exhaustive `From<DomainError> for ApiError` → `application/problem+json`; no blanket `From<anyhow::Error>`. A 500 body never carries the source; it is logged once, there. *major*
- No swallowed error: `let _ = fallible();`, a discarding `.ok()`, `if let Ok` with no `else` where failure matters. *blocker*
- `.map_err(|_| …)` keeps the source; error `Display` holds no secret. *major*
- No `std::process::exit` in service code: destructors and the telemetry flush would not run. *major*

## Numbers and text

- Input-derived arithmetic uses `checked_*`; narrowing casts use `try_from`, never `as`; no byte slicing of user text. *major*

## Async on tokio

- No `std::sync` guard alive at an `.await`; no `block_on` or nested runtime inside async code. *blocker*
- No blocking I/O, `thread::sleep` or CPU work over ~100 µs on a runtime thread: `spawn_blocking` or `rayon`. *major*
- Every spawned task has an owner (`JoinSet` / `TaskTracker`) and a cancellation path. *major*
- A channel fed from outside is bounded; a cache has a capacity and TTL (`moka`). *major*
- Every outbound call has a timeout; retries are bounded, with backoff and jitter, idempotent only. *major*
- Every `select!` branch in a loop is cancel-safe; `biased;` only with its starvation stated. *major*
- Shutdown: stop accepting → drain → cancel tasks → flush telemetry → close the pool. *major*

## HTTP, config and state

- Handlers are transport: extract, convert the DTO, call the module, map the result. `now` and new ids are passed into domain functions. *major*
- `std::env::var` only in `config.rs`; secrets in `SecretString`; one `AppState` built in `main`. *major*
- Every router has a trace layer, a timeout and a body limit. *major*
- axum 0.8 paths are `/{id}`; `/:id` silently matches nothing. *blocker*

## Logging, secrets and `unsafe`

- `tracing` events with fields, never a `format!`-built message or `println!`. *major*
- A new operation, outbound call or job gets `#[tracing::instrument(skip_all, fields(…))]` and events at its decisions; a business event gets a metric. Futures take `.instrument(span)`, never `span.enter()` across `.await`. *major*
- Per-record ids are span fields, never metric attributes; libraries never install a subscriber. *major*
- No secret in code, in a derived `Debug`, or in a log or span field. *blocker*
- A request-supplied path is canonicalised and prefix-checked. *blocker*
- No `unsafe` in application code; every `unsafe` block has a `// SAFETY:` comment. *blocker*

## Performance

- No change called faster without a before/after number from one benchmark on a release build. Never trade readability for a frame under 1% of a profile. *major*
- No allocation per loop iteration on a hot path; no `FxHashMap` on attacker-controlled keys. *minor; major for FxHashMap*

## Lints and comments

- A lint exception is `#[expect(lint, reason = "…")]` on the item, never a crate-wide `#![allow]`. *minor*
- No comments inside bodies except `// SAFETY:`; a `///` doc only where the name cannot carry a rule, a caller constraint or a contract. *minor; major when wrong*
