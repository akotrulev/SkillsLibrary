---
name: performance
description: Use when Rust code is slow, allocates too much, or builds slowly — benchmark (criterion, divan, gungraun), profile (samply, perf, heaptrack, tokio-console), fix allocations, clones, hashing, buffering, async stalls; tune release profiles, PGO, allocators and compile times. Triggers "this endpoint is slow", "profile my Rust", "builds take forever". Do NOT use for SQL tuning (`database-code`, `data/*`) or correctness reviews (`code-review`).
---

# Rust — Performance

Rust is fast by default, and most slow Rust is slow for one of a handful of reasons: it allocates in a loop, it clones what it could borrow, it hashes with SipHash on a hot map, it writes unbuffered, it blocks the async runtime, or it waits on the database. **Measure, find the frame that costs, change one thing, measure again.** A change justified as "faster" with no number is a review finding (`code-review`).

## Version policy

Detect the toolchain and the existing bench setup (`benches/`, `[[bench]]`, `criterion`/`divan`/`gungraun` in `[dev-dependencies]`). The repo's harness wins. The facts below hold on stable as of Rust 1.99 (2026-10). Cranelift, `-Zthreads` and branch coverage are nightly-only; never make a project depend on them.

## When to use

- A request, a job, or a loop is slower than its budget
- Memory grows or allocations dominate a profile
- Choosing release-profile settings or a global allocator
- Async latency spikes with an idle CPU (runtime starvation)
- Build or CI times are too long

## When NOT to use

- The time is in the database → `database-code` (N+1, bulk) and `data/_shared/slow-query-fixes`
- Correctness or locking bugs → `async-concurrency`, `code-review`
- Load-testing the deployed service → the `qa-*` performance peers

## The loop

1. **State the budget and reproduce it**: a benchmark for a function, `hyperfine` for a CLI, a load test for an endpoint (`oha` / `k6`) at a fixed rate.
2. **Profile a release build with symbols** (see *Profiling profile*). Never profile a debug build — it is often 10–100× slower, and in different places.
3. **Fix the top frame only.** The second-hottest frame often moves once the first is fixed.
4. **Re-run the same benchmark** and record before/after in the commit message or plan note.
5. **Keep the benchmark** in `benches/` if the path is hot enough to regress.

## Profiling

| Question | Tool | Platform |
|---|---|---|
| Where does CPU time go? | **`samply record ./target/profiling/app`** (Firefox Profiler UI) — the cross-platform default | macOS, Linux, Windows |
| | `perf record -g` + Hotspot; `cargo flamegraph` (perf / DTrace) | Linux; flamegraph also macOS |
| | Instruments (Time Profiler) | macOS |
| Where do allocations come from? | `heaptrack` (no code change) | Linux |
| | `dhat-rs` (`#[global_allocator]` swap behind a feature; counts and sites) | All |
| Why are async tasks slow with an idle CPU? | `tokio-console` + `console-subscriber` (needs `RUSTFLAGS="--cfg tokio_unstable"`): tasks busy too long between `.await`s, tasks waking constantly, never-dropped tasks | All |
| Where does a request spend wall time across I/O? | The trace in Tempo (`observability/opentelemetry-rust`) — spans show waiting, not CPU | All |
| Why is the binary big / the build slow? | `cargo bloat --release --crates`, `cargo llvm-lines`, `cargo build --timings` | All |

### Profiling profile

```toml
[profile.profiling]
inherits = "release"
debug = "line-tables-only"
```

```bash
RUSTFLAGS="-C force-frame-pointers=yes" cargo build --profile profiling
samply record ./target/profiling/orders-service
```

`line-tables-only` keeps file:line for stacks at a small size cost. Frame pointers make the unwinding reliable. Keep `strip = "symbols"` out of any profile you profile.

## Benchmarking

| Tool | Use for |
|---|---|
| **criterion** 0.8 (now `criterion-rs/criterion.rs`) | Statistical wall-clock micro-benchmarks with regression detection; the default |
| **divan** 0.1 | Lighter syntax, allocation counting; usable, but little release activity since 2025 |
| **gungraun** 0.20 (formerly `iai-callgrind`, renamed at 0.17) | Instruction counts under Valgrind — deterministic, so CI can gate on it; Linux |
| **hyperfine** 2.0 | Whole-binary timings for CLIs |

```toml
[dev-dependencies]
criterion = "0.8"

[[bench]]
name = "pricing"
harness = false
```

```rust
use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

fn pricing(c: &mut Criterion) {
    let cart = a_cart_with_lines(200);
    c.bench_function("total/200_lines", |b| b.iter(|| total(black_box(&cart.lines))));
}

criterion_group!(benches, pricing);
criterion_main!(benches);
```

Wrap inputs (and the results the optimizer could discard) in `std::hint::black_box`, which is best-effort. Benchmark realistic sizes, never a single tiny input. Wall-clock benchmarks on shared CI runners are noisy: gate CI on gungraun instruction counts, or compare criterion runs on dedicated hardware.

## Code-level fixes — in rough order of how often they matter

| Smell | Fix | Clippy |
|---|---|---|
| `.clone()` / `.to_string()` / `.to_owned()` of data only read | Borrow (`&str`, `&[T]`); `Cow` when only some paths modify; `Arc<str>` / `Arc<[T]>` for shared immutable data | `unnecessary_to_owned`, `redundant_clone` (nursery), `implicit_clone` (pedantic) |
| `Vec`/`String` grown element by element when the size is known | `Vec::with_capacity(n)`, `String::with_capacity`, `extend` from an iterator | `vec_init_then_push`, `slow_vector_initialization` |
| `.collect::<Vec<_>>()` only to iterate again | Keep the iterator chain | `needless_collect` (nursery) |
| `format!` in a loop / `push_str(&format!(…))` | `write!(buf, …)` into one reused `String` | `format_push_string`, `format_collect` (pedantic) |
| A buffer allocated per iteration | Allocate once outside the loop, `clear()` per iteration | — |
| `HashMap` with short keys on a hot path | `rustc_hash::FxHashMap` or `foldhash` — **only for keys not controlled by an attacker** (they drop HashDoS resistance); std keeps SipHash 1-3. Ban the std type with `disallowed_types` if a crate standardizes on one | — |
| Unbuffered I/O, `println!` in a loop | `BufReader` / `BufWriter`; `let mut out = io::stdout().lock();` | `unbuffered_bytes` |
| Index loops with bounds checks in a hot kernel | Iterators, `chunks_exact`, slicing once (`let s = &v[..n];`) so checks hoist | `needless_range_loop` |
| One huge enum variant | `Box` the large payload so every value isn't the size of the largest | `large_enum_variant`, `result_large_err` |
| Many small heap objects | `SmallVec` / `ArrayVec` for small bounded collections; struct-of-arrays for scans over one field; indices into a `Vec` over `Rc` graphs | `box_collection`, `vec_box` |
| `Regex::new` per call | Build once (`LazyLock<Regex>` or in state) | `regex_creation_in_loops` |
| Lock contention | Shorter critical sections; shard the map; `ArcSwap` for read-mostly data; per-thread accumulation merged at the end. std `Mutex` is futex-based on Linux and Windows — swap to `parking_lot` only on a measured win | — |
| `dyn Trait` call in the innermost loop | A generic or an enum — only after the profile shows dispatch | — |
| `#[inline]` sprinkled everywhere | Small non-generic functions are inlined across crates automatically since 1.75. Use `#[inline]` only on a measured cross-crate hot call; mark cold error paths `#[cold]` / `#[inline(never)]` | — |

### Async-specific

- CPU work over ~100 µs inside a task → `spawn_blocking` or `rayon` (`async-concurrency`). It shows up as p99 latency on unrelated requests, and the CPU profile looks innocent.
- `serde_json::from_slice` into borrowed `&str` fields (`#[serde(borrow)]`) avoids per-field allocation for large payloads; `bytes::Bytes` passes bodies without copying.
- Unbounded concurrency hurts throughput: a `Semaphore` or `buffer_unordered(n)` sized to the downstream's capacity beats spawning everything.
- Pool waits look like slowness: watch `acquire_timeout` errors and pool-wait spans before tuning Rust code.

## Release profile

```toml
[profile.release]
lto = "thin"
codegen-units = 1
debug = "line-tables-only"
```

| Knob | Effect | Cost / caveat |
|---|---|---|
| `lto = "thin"` / `"fat"` | Often 10–20% faster across crate boundaries | Longer link; fat is slower to build and not always faster than thin |
| `codegen-units = 1` | Better optimization than the default 16 | Slower release builds |
| `panic = "abort"` | Slightly smaller and faster | **No unwinding:** `catch_unwind`, tower-http's `CatchPanicLayer` and tokio's per-task panic isolation stop working — one task's panic kills the process. Not for servers unless that is intended |
| `opt-level = "s"` / `"z"` | Smaller binaries | Usually slower; for size-constrained targets |
| `overflow-checks = true` | Integer overflow panics in release too | Small cost; worth it on money paths if not using `checked_*` everywhere |
| `-C target-cpu=native` | Uses the build host's instructions (AVX2, …) | The binary may crash on other CPUs — never for images built in CI and run elsewhere; name an explicit `target-cpu` level instead |
| PGO (`cargo-pgo` 0.3) | Often 10%+ on branchy code | A profiling run with a representative workload in the build; BOLT support is experimental |

### Global allocator

The system allocator is fine on glibc. On **musl** (static Alpine / scratch images) its malloc is a known bottleneck under multithreaded allocation. Use `mimalloc` (0.1) or `tikv-jemallocator` (0.7; Linux and macOS) there, or on glibc when the profile shows allocator time:

```rust
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

Measure it — allocator wins are workload-specific, and jemalloc can raise RSS.

## Compile times

| Lever | Effect |
|---|---|
| lld | The default linker on `x86_64-unknown-linux-gnu` since **1.90**. On other Linux targets, `mold` (or the newer, less mature `wild`); macOS's system linker is already fast |
| `debug = "line-tables-only"` or `false` in `[profile.dev]` | Debug info is a large share of dev build time |
| `cargo check` in the edit loop; `cargo clippy` in CI | No codegen |
| `sccache` (0.19) | Shared compilation cache for CI |
| Split a large crate into workspace members | Parallel and incremental builds; the crate-per-module layout (`pattern-writer`) gets this for free |
| Fewer generic instantiations in the API surface | `cargo llvm-lines` shows which generics expand most; move the body into a non-generic inner function |
| Trim default features of heavy dependencies | `default-features = false` and only what is used |
| `cargo build --timings` | Shows the crate graph's critical path |

## Rules

- No optimization without a before/after number from the same benchmark or load test
- Profile release builds with `line-tables-only` debug info and frame pointers
- Fix the top frame, then re-measure
- Hot-path allocation, cloning, hashing and buffering are the first suspects; `unsafe` is the last resort and needs a benchmark plus a `// SAFETY:` comment (`pattern-guide` → `unsafe`)
- `panic = "abort"` and `target-cpu=native` only with their caveats accepted in writing
- Keep the regression benchmark once a hot path is fixed

## What NOT to do

- No `get_unchecked` / `unsafe` to remove a bounds check the optimizer could hoist with a slice
- No `FxHashMap` on attacker-controlled keys
- No profiling a debug build; no benchmarking with a single tiny input
- No `#[inline(always)]` on large functions to "help" the compiler
- No allocator swap or LTO change without a measurement
- No replacing readable code with clever code for a frame that is under 1% of the profile

## Handoffs

- The time is SQL → `database-code`, `data/_shared/slow-query-fixes`
- Runtime starvation, locks, backpressure → `async-concurrency`
- Tracing the request path → `observability/opentelemetry-rust`
- Reviewing the change → `code-review`
- Load-testing the deployed service → the `qa-*` performance peer of the stack driving the load
