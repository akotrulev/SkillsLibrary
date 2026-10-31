---
name: conventions-review
description: Use when reviewing Rust service or library code for panics in production paths, error-type leaks, needless clones, locks held across .await, blocking on the runtime, unbounded channels, unchecked casts and overflow, undocumented unsafe, secret-leaking Debug, and missing tests. Triggers "review this Rust module", "is this idiomatic Rust", "check this axum handler". Do NOT use for explanations (`pattern-guide`), generating the fix (`pattern-writer`), or profiling (`performance`).
---

# Rust — Reviewer

Reviews Rust code against `pattern-writer`, `async-concurrency`, `database-code`, `performance`, `unit-testing` and the global rules in `CLAUDE.md`. Produces the findings table; does not rewrite. Loads `backend/_shared/code-review` for pattern-stacking and architecture-altitude concerns.

**Let the tools find what tools find.** Before reading a line, run (outside a `Gate: none` plan task) `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, and the tests. A clippy finding is reported by its lint name; the review's value is everything clippy cannot see — ownership design, error modelling, cancellation, the test gaps.

## When to use

- A diff, crate or module submitted for review
- Pre-merge gate on anything under `src/`, `tests/`, `benches/`, `Cargo.toml`
- "Is this safe to run in production", "why is this slow / deadlocking"

## When NOT to use

- Conceptual questions → `pattern-guide`
- Writing the fix → `pattern-writer` / `async-concurrency` / `database-code`
- Measuring a performance claim → `performance` (a review flags the suspicion; a profile proves it)
- Dependency CVEs, SAST, DAST → `qa-security`

## Review checklist

### Panics and errors

| Check | Bad sign | Severity |
|---|---|---|
| No panics on input-reachable paths | `unwrap()`, `expect()` without an invariant message, `[i]` indexing with an input-derived index, `.parse().unwrap()`, `Duration::from_secs_f64` on input | blocker in a request path, major elsewhere |
| Library errors are typed | `Box<dyn Error>` / `anyhow::Error` in a `pub` signature of a library crate | major |
| Errors carry context, not secrets | `.map_err(\|_\| Error::Internal)` dropping the source; a DB URL or token in an error `Display` | major |
| No swallowed errors | `let _ = fallible();`, `.ok();` discarding a `Result`, `if let Ok(x)` with no `else` on a path that must not fail silently | blocker |
| Internal errors do not leak to clients | `IntoResponse` that formats `sqlx::Error` into the body | major |
| `?` across a boundary converts deliberately | a blanket `impl From<anyhow::Error> for ApiError` that maps everything to 500 and hides 4xx cases | major |

### Ownership and API shape

| Check | Bad sign | Severity |
|---|---|---|
| Borrow what is only read | `fn f(s: String)` that never stores `s`; `&String`, `&Vec<T>` parameters (clippy `ptr_arg`) | minor |
| Clones are earned | `.clone()` on a `Vec`/`String`/struct to satisfy the borrow checker; `.to_string()` on a `&str` passed straight to a `&str` parameter | major on a hot path, minor elsewhere |
| No needless `Rc<RefCell<T>>` / `Arc<Mutex<T>>` | shared mutability where single ownership + message passing or a `&mut` would do | major |
| Lifetimes only where they earn their place | a lifetime parameter on a long-lived domain struct | minor |
| Newtypes at boundaries | raw `Uuid`/`String`/`i64` ids passed between modules; money as `f64` | major |
| Exhaustive matches on owned enums | `_ =>` arm on an enum this crate defines | major |
| Public enums that grow are `#[non_exhaustive]` | a published library enum without it | minor |
| Unearned abstraction | a trait with one implementer and no fake; a generic with one instantiation; a `*Service` that forwards to a `*Repository` that forwards to sqlx | major — inline it |

### Async and concurrency (`async-concurrency`)

| Check | Bad sign | Severity |
|---|---|---|
| No lock guard across `.await` | a `std::sync::MutexGuard` or `RwLock` guard alive at an `.await` (clippy `await_holding_lock`) | blocker |
| No blocking on the runtime | `std::fs`, `std::thread::sleep`, sync HTTP, CPU work over ~100 µs, `bcrypt`/`argon2` hashing inside `async fn` without `spawn_blocking` | major |
| Cancellation-safe `select!` | a `select!` branch that is not cancel-safe (`read_exact`, a half-written frame, a `recv` that already took a message into a local) | major |
| Backpressure | `unbounded_channel` on a path fed by external input; `tokio::spawn` per request with no limit | major |
| Spawned work is owned | `tokio::spawn` whose `JoinHandle` is dropped and whose error is never observed; no shutdown path | major |
| Timeouts on every outbound call | `reqwest` / DB / gRPC call without a timeout budget | major |
| No `block_on` inside async | `futures::executor::block_on` or `Handle::block_on` from a runtime thread | blocker |
| `Span::enter` not held across `.await` | `let _e = span.enter(); x.await;` | major — `.instrument(span)` |

### Numbers, casts, text

| Check | Bad sign | Severity |
|---|---|---|
| Overflow handled on input-derived arithmetic | `a + b` / `a * qty` on amounts or sizes from a request | major |
| No truncating casts | `as u32`, `as usize` on a value that can exceed the target (clippy `cast_possible_truncation`) | major |
| UTF-8 boundaries respected | `&s[..n]` byte slicing on user text | major — `char_indices` / `get(..n)` |
| Float equality | `==` on `f64` | minor |

### Persistence (`database-code`)

| Check | Bad sign | Severity |
|---|---|---|
| Parameterized queries | `format!` building SQL with a value | blocker |
| Compile-checked queries where the project uses them | `sqlx::query(...)` with hand-bound args where `query!`/`query_as!` fits | minor |
| Transactions scoped and committed | multi-statement write without a `Transaction`; `tx` passed around and never `commit()`ed | major |
| N+1 | a query inside a loop over rows | major |
| Pool sized and timed out | default pool with no `acquire_timeout` | minor |

### Security and secrets

| Check | Bad sign | Severity |
|---|---|---|
| No secrets in code or `Debug` | a key literal; `#[derive(Debug)]` on a config holding a password | blocker / major |
| Secrets typed | `String` for a token where `secrecy::SecretString` fits | minor |
| Paths confined | a request-supplied path joined without canonicalising and checking the prefix | blocker |
| No `unsafe` without a `// SAFETY:` justification | an `unsafe` block with no comment, or one that does not state the invariant (clippy `undocumented_unsafe_blocks`) | blocker |
| `unsafe` earned | `unsafe` in application code; `transmute`; `get_unchecked` without a benchmark proving it | major |
| Untrusted deserialisation bounded | no body size limit on the router; recursive `serde_json` input with no depth or size cap | major |

### Performance (`performance`)

| Check | Bad sign | Severity |
|---|---|---|
| Allocation in hot loops | `format!`/`to_string`/`collect` inside a loop that could push into one buffer; `Vec::new()` in a loop where it could be reused or `with_capacity` | minor (major on a measured hot path) |
| Intermediate collections | `.collect::<Vec<_>>()` only to iterate again | minor |
| Unbuffered I/O | `File` read/written in small pieces without `BufReader`/`BufWriter`; `println!` in a loop | minor |
| Large enum variants | one variant much bigger than the rest (clippy `large_enum_variant`) | minor |
| Performance claim without a measurement | a change justified as "faster" with no benchmark or profile | major |

### Project hygiene

| Check | Bad sign | Severity |
|---|---|---|
| Lints configured once | lint attributes scattered per file instead of `[lints]` / `[workspace.lints]` in `Cargo.toml`; `#[allow]` without a reason | minor |
| `#[expect]` over `#[allow]` for a deliberate exception | `#[allow(clippy::x)]` that silently outlives its cause | nit |
| `Cargo.lock` committed for binaries | missing lockfile in a service repo | major |
| Dependencies earned | a crate added for one function std already has; default features pulled when one is needed | minor |
| Toolchain and MSRV unchanged | edition or `rust-version` raised as a side effect of a feature | major |
| Comments per `engineering-practices/code-comments` | inline narration, commented-out code, a doc comment restating the signature | minor; wrong or covering-for-unclear-code → major |

### Tests (`unit-testing`)

| Check | Bad sign | Severity |
|---|---|---|
| One expected condition | `assert!(status == 200 \|\| status == 204)`; `matches!(r, A \| B)` in an assertion | major |
| No `if`/`for`/`match` driving assertions | a loop of `assert_eq!` over a table | major — `rstest` cases |
| Both arms of every `Result` tested | only the `Ok` path asserted | major |
| No real sleeps | `tokio::time::sleep` / `thread::sleep` waiting for a condition | major — `start_paused` or a signal |
| No mocking of types the crate does not own | `mockall` on `sqlx::PgPool` / `reqwest::Client` | major — wrap in a port |
| Tests independent | a `static` shared between tests; reliance on test order | major |
| Branch coverage of the change ≥ 80% | the measure missing from the report | major |

## Output

The standard table from `CLAUDE.md`:

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker | src/orders/handler.rs:41 | `MutexGuard` from `state.cache.lock()` held across `repo.save(..).await` | Copy the value out and drop the guard before the await (`async-concurrency` → Locks) |
| major | src/orders/place.rs:18 | `qty * unit_price` on request input wraps in release | `checked_mul` returning `PlaceOrderError::AmountOverflow` |
```

Each fix names the skill section that has the recipe rather than restating it. Blockers first. Clippy findings are grouped by lint name with a count rather than one row each.

## Handoffs

- Fixes → `pattern-writer` / `async-concurrency` / `database-code`
- A suspected hot spot → `performance` (profile before changing)
- Missing tests → `unit-testing`
- Cross-stack pattern concerns → `backend/_shared/code-review`
- Dependency audit, SAST → `qa-security`
