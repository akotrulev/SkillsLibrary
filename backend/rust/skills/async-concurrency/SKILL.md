---
name: async-concurrency
description: Use when writing or fixing async Rust on tokio (cancellation, shutdown, select! safety, locks vs channels). Triggers "future is not Send", "tokio Mutex or std Mutex". Not for profiling (performance).
---

# Rust — Async and Concurrency on Tokio

Owns the rules that keep async Rust correct under load: who owns a task, how it stops, what may run on a runtime thread, and how shared state is mutated. The async bugs that reach production are rarely type errors — they are a lock held across an `.await`, a blocking call starving the runtime, a `select!` that drops half a message, or a task nobody waits for. Every rule below closes one of those.

## Version policy

Detect the runtime from `Cargo.lock`: **tokio 1.x** — 1.54 current as of 2026-10; the LTS lines are **1.51.x (to March 2027)** and **1.53.x (to September 2027)**, which suit services that upgrade slowly (1.47.x reached end of support in September 2026). Keep the project's minor; never bump it as a side effect. Use `tokio-util` 0.7 for `CancellationToken` / `TaskTracker`. A project on `async-std` or `smol` keeps its runtime — `async-std` is discontinued, so flag it and recommend migrating, but never migrate as a side effect. Native `async fn` in traits needs Rust 1.75; async closures need 1.85.

## When to use

- Spawning background work, a worker loop, a consumer, a scheduled job
- Graceful shutdown of a server and its background tasks
- A compile error about `Send`, `'static`, or a future that "cannot be sent between threads"
- Choosing a lock, a channel, or an actor for shared state
- A hang, a deadlock, a latency spike, a runtime that stops accepting connections
- Calling blocking or CPU-heavy code from async code

## When NOT to use

- Ownership and type design in general → `pattern-guide`
- The router, handlers, `AppState` wiring → `pattern-writer`
- sqlx pools and transactions → `database-code`
- "It's slow" without a known cause → `performance` (measure first)

## The runtime rule — never block a worker thread

A tokio worker thread runs many tasks by switching between them only at `.await` points. Code that does not yield stalls every other task on that thread. As a rule of thumb, a task should not go more than **10–100 µs** between `.await`s.

| Work | Where it runs |
|---|---|
| Async I/O (sockets, `tokio::fs`, sqlx, reqwest) | Directly in the task |
| Blocking I/O or a sync library (`std::fs`, a sync SDK, `rusqlite`) | `tokio::task::spawn_blocking(move \|\| …).await?` |
| Short CPU work (password hashing, image resize, compression, a big JSON parse) | `spawn_blocking` |
| Sustained CPU parallelism (batch transforms) | `rayon` on its own pool, results returned through a `oneshot` |
| A long-lived blocking loop | `std::thread::spawn` — never a `spawn_blocking` that never returns (it pins a pool thread forever) |

```rust
let hash = tokio::task::spawn_blocking(move || argon2_hash(&password)).await??;
```

`block_in_place` exists for the multi-threaded runtime only and panics on the current-thread runtime — prefer `spawn_blocking`. **Never call `Runtime::block_on`, `Handle::block_on` or `futures::executor::block_on` from inside async code** — it panics or deadlocks.

## Tasks have owners

`tokio::spawn` detaches: dropping the `JoinHandle` does **not** cancel the task, and a panic or an error inside it vanishes unless something awaits the handle.

| Shape | Use |
|---|---|
| A fixed set of background loops started in `main` | `tokio_util::task::TaskTracker` + one `CancellationToken`; `tracker.close(); tracker.wait().await` on shutdown |
| A dynamic group whose results you need (fan-out) | `tokio::task::JoinSet` — `join_next().await` collects results and surfaces panics; dropping the set aborts the remainder |
| Bounded concurrent work over a collection | `futures::stream::iter(items).map(work).buffer_unordered(n)` — no spawn needed |
| Fire-and-forget | Not allowed. Name the owner, or log and count the error inside the task |

```rust
let mut set = JoinSet::new();
for id in ids {
    let client = client.clone();
    set.spawn(async move { client.fetch(id).await });
}
while let Some(joined) = set.join_next().await {
    let item = joined??;
    results.push(item);
}
```

## `Send` and `'static` errors — what they mean

`tokio::spawn` requires the future to be `Send + 'static`: it may move between threads and outlive the caller.

| Error | Cause | Fix |
|---|---|---|
| "future cannot be sent between threads safely" | A `!Send` value (`Rc`, `RefCell` borrow, `std::sync::MutexGuard`, `*mut T`) is alive across an `.await` | Scope it: put the non-`Send` use in a block that ends before the `.await`, or switch `Rc` → `Arc` |
| "borrowed value does not live long enough" / `'static` required | The future borrows a local | `move` the owned value in (clone the `Arc` first) |
| `async fn` in a trait not `Send` | Native `async fn` in traits gives no `Send` bound to callers | Declare `fn run(&self) -> impl Future<Output = …> + Send;` or use `trait_variant::make` for a `Send` variant |

## Locks — the decision

| Shared state | Use |
|---|---|
| Data touched briefly, never across `.await` | `std::sync::Mutex` / `RwLock` (tokio's own guidance — it is faster than the async mutex) |
| A resource that must be held across `.await` (a connection, a file being written) | `tokio::sync::Mutex` — or better, an actor that owns it |
| Many readers, rare writes, readers must never block | `arc_swap::ArcSwap`, or `tokio::sync::watch` for a value that changes and is observed |
| Complex state with invariants across several fields | An **actor**: one task owns the state, an `mpsc` channel brings commands, `oneshot` returns replies |

**The rule clippy enforces (`await_holding_lock`): no `std::sync` guard is alive at an `.await`.** Copy out what you need and drop the guard first:

```rust
let snapshot = {
    let cache = state.cache.lock().expect("cache mutex poisoned");
    cache.get(&key).cloned()
};
let fresh = repo.load(key).await?;
```

Lock ordering: when two locks must be held together, every code path acquires them in the same order, documented once on the type. Calling a method that locks a mutex you already hold deadlocks — `std::sync::Mutex` is not re-entrant.

**Poisoning.** `std::sync::Mutex::lock()` returns `Err` if a holder panicked. `expect("<name> mutex poisoned")` is the accepted form (a poisoned lock means a bug already happened); `parking_lot::Mutex` has no poisoning if the project uses it.

## Channels and backpressure

| Channel | Use |
|---|---|
| `mpsc::channel(n)` (bounded) | Default for work queues; `send().await` waits when full — that wait **is** the backpressure |
| `mpsc::unbounded_channel` | Only when the producer is provably bounded (a fixed set of internal events). Never on a path fed by requests or a broker |
| `oneshot` | A single reply (actor request/response) |
| `broadcast` | Fan-out where every subscriber sees every message; a slow subscriber gets `Lagged` and must handle it |
| `watch` | The latest value of something (config, health state); intermediate values may be skipped |

Limit concurrent work against a scarce resource with `tokio::sync::Semaphore` (`acquire_owned` moved into the task), and limit request concurrency at the edge with `tower`'s `ConcurrencyLimitLayer` / `LoadShedLayer` — not by spawning unbounded tasks.

## Cancellation — every `.await` is a place your future may stop

A future is cancelled by being dropped: a `select!` branch that lost, a `timeout` that fired, a client that disconnected from an axum handler. Code after the `.await` never runs. Design for it:

- **`select!` in a loop needs cancel-safe branches.** The `tokio::select!` docs list three groups:
  - **Cancel-safe:** `mpsc` / `broadcast` `recv`, `watch::Receiver::changed`, `TcpListener::accept`, `Signal::recv`, `read` / `read_buf`, `write` / `write_buf`, `StreamExt::next`, `CancellationToken::cancelled`, `JoinSet::join_next`.
  - **Not cancel-safe, can lose data:** `read_exact`, `read_to_end`, `read_to_string`, `write_all`, and any future you wrote that does several steps.
  - **Not cancel-safe, loses its place in the queue:** `Mutex::lock`, `RwLock::read` / `write`, `Semaphore::acquire`, `Notify::notified`. This is acceptable for one-off use, but in a loop it means unfair starvation.

  To make an unsafe future safe, create it **once, outside the loop**, pin it, and poll `&mut fut` in each iteration.
- **Multi-step writes that must complete** (charge then record) do not run inside a cancellable request future. Move them into a spawned task the handler awaits, or make them idempotent and resumable.
- **`Drop` cannot await.** Async cleanup is an explicit `shutdown().await` called on the normal path.

```rust
loop {
    tokio::select! {
        _ = token.cancelled() => break,
        Some(job) = rx.recv() => handle(job).await?,
    }
}
```

## Timeouts — every outbound call has a budget

```rust
let reply = tokio::time::timeout(Duration::from_secs(2), client.get_quote(id))
    .await
    .map_err(|_| QuoteError::Timeout)??;
```

Configure timeouts on the client too (`reqwest::ClientBuilder::timeout`, sqlx `acquire_timeout`), and at the HTTP edge with `TimeoutLayer::with_status_code(StatusCode::REQUEST_TIMEOUT, budget)`. `TimeoutLayer::new` has been deprecated since tower-http 0.6.7. Without an edge timeout, a stuck request blocks graceful shutdown forever. A retry loop has a bounded attempt count, exponential backoff with jitter, and retries only idempotent operations.

## Graceful shutdown

```rust
pub async fn shutdown_signal(token: CancellationToken) {
    let ctrl_c = async { tokio::signal::ctrl_c().await.expect("ctrl-c handler") };
    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("SIGTERM handler")
            .recv()
            .await;
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();
    tokio::select! {
        () = ctrl_c => {},
        () = terminate => {},
    }
    token.cancel();
}
```

```rust
let token = CancellationToken::new();
let tracker = TaskTracker::new();
tracker.spawn(outbox_relay(state.clone(), token.child_token()));

axum::serve(listener, app)
    .with_graceful_shutdown(shutdown_signal(token.clone()))
    .await?;

tracker.close();
tracker.wait().await;
telemetry.shutdown()?;
```

Order: stop accepting → drain in-flight requests (axum does this) → cancel and await background tasks → flush telemetry → close the pool. Kubernetes sends `SIGTERM` and waits `terminationGracePeriodSeconds`; the drain must finish inside it.

## Async traits and closures

- **`async fn` in traits** (1.75): use it for static dispatch. As of late 2026 it is still **not dyn-compatible**, and stable Rust has no way to require that the returned future is `Send`; native dyn async traits are a 2026–27 project goal. For `Arc<dyn Trait>`, keep `#[async_trait]` (0.1.x) or return `Pin<Box<dyn Future + Send + '_>>`. For a `Send` variant used generically, use `trait_variant::make`.
- **Async closures** (`async |x| …`, `AsyncFn*` traits, 1.85): prefer them over `|x| async move { … }` when the closure borrows from its captures.
- **Recursion** in `async fn` needs `Box::pin`.

## Testing async code

`#[tokio::test]` builds a current-thread runtime per test. Time-dependent logic uses `#[tokio::test(start_paused = true)]` — time auto-advances when every task is idle, so a 30-second timeout test runs instantly and deterministically. Never `sleep` to wait for a condition; await the signal (a `oneshot`, `Notify`, the `JoinHandle`). Details in `unit-testing`.

## Rules

The standards this skill's output must meet are the be-rust rule file `rust.md` (Async on tokio), not a list here. Read the project's copy in `.claude/rules/be-rust/`, or the plugin's in `backend/rust/skills/rules/` when the project has not installed them (`/be-rust:rules` does). Where it and this skill's recipes disagree, the rule file wins.

## Handoffs

- Wiring the shutdown into `main` and the router → `pattern-writer`
- Pool timeouts and transactions → `database-code`
- Latency or throughput that needs a profile → `performance` (`tokio-console` for task-level stalls)
- Testing the timing logic → `unit-testing`
- Reviewing → `code-review`
