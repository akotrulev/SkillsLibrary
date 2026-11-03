---
name: unit-testing
description: Use when Rust logic needs a unit test with cargo test or nextest (seams, proptest, paused tokio time, coverage floor). Triggers "unit-test this Rust module". Not for sqlx tests (persistence).
---

# Rust — Unit Testing (`cargo test` / nextest)

Owns **dev-side unit tests of Rust logic**: call a function or method directly, pass fakes in, and assert on the return value or on the effect on a fake. **In-process only** — no socket, no real database, no filesystem outside a `tempfile` dir, no wall clock.

**The boundary, one sentence:** a test that needs a database, a running router (`tower::ServiceExt::oneshot` on the app), or a container is an integration test. It lives in `tests/` under a different command, and it does not count toward this skill's coverage floor. See *The integration lane* for who writes those while no `qa-*-rust` plugin exists.

## Version policy

Detect the toolchain and the test tooling already present: `cargo-nextest` (0.9.x), `rstest`, `proptest`, `mockall`, `insta` in `[dev-dependencies]`. **The repo's choice wins.** `assert_matches!` is stable from Rust 1.96 (`use std::assert_matches::assert_matches;` — it is not in the prelude). Below 1.96, use `matches!` inside `assert!` with a message.

## When to use

- A function or type `pattern-writer` produced has behaviour: a constructor that validates, a strategy `match`, a state transition, a calculation, a mapper, the `From<DomainError> for ApiError` mapping
- Pinning a rule before a refactor
- Reproducing a bug at unit level before fixing it (`dev:debugging`)
- Time-dependent async logic (retry, timeout, debounce) under paused time

## When NOT to use

- Queries, migrations, transactions → integration lane (`database-code` → Testing the queries)
- The router, extractors, middleware, status codes → integration lane / `qa-api-typescript` (black-box)
- Benchmarks → `performance`
- Types with no behaviour (DTOs, `Config` fields, derived impls) → don't test them

## Stack

| Concern | Tool | Notes |
|---|---|---|
| Harness | built-in `#[test]` | Colocated `#[cfg(test)] mod tests` in the file under test |
| Runner | `cargo nextest run` (if the repo uses it), otherwise `cargo test` | nextest runs each test in its own process and does **not** run doctests — add `cargo test --doc` |
| Cases | `rstest` 0.28 | `#[rstest] #[case(…)]` — the escape hatch for "no loops driving assertions" |
| Invariants | `proptest` 1.x | For parsers, round-trips, arithmetic rules |
| Async | `#[tokio::test]` | `start_paused = true` needs tokio's `test-util` feature in `[dev-dependencies]` |
| Doubles | hand-written fakes first; `mockall` 0.15 last | `mockall` works with native `async fn` in traits |
| Snapshots | `insta` 1.x — only for large, reviewed outputs | Never the only assertion on a value with business meaning |

## What deserves a unit test — the selection matrix

| Unit | Test it? | Assert |
|---|---|---|
| Fallible constructor / `TryFrom` / `FromStr` | **Yes** | Valid → value; each invalid class → its error variant |
| Strategy `match` / state transition | **Yes** | Each variant's outcome; each refused transition's error |
| `Result`-returning operation | **Yes** | **Both** arms — every error variant reachable from its inputs |
| Calculation (money in minor units, rounding, dates) | **Yes** | Boundaries, the rounding rule, overflow → error |
| `From<DomainError> for ApiError` | **Yes** | Each domain variant → its status |
| Retry / timeout / backoff logic | **Yes** | Under `start_paused`: attempt count, the delay sequence, the give-up |
| Serde with custom attributes (`rename`, `tag`, `deserialize_with`) | **Yes** | The wire shape both ways; the rejected input |
| Plain DTO, derived `Serialize` with no attributes | **No** | — |
| Handler that only extracts and maps | **No** | Integration lane |
| sqlx query | **No** | Integration lane |

**The tautology test:** if deleting the assertion leaves the test passing, delete the test.

## Layout and naming

```rust
pub fn total(lines: &[Line]) -> Result<Money, PricingError> { ... }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn should_reject_the_order_when_the_total_overflows() {
        let lines = [a_line().unit_price_minor(i64::MAX).quantity(2).build()];

        let result = total(&lines);

        assert_matches!(result, Err(PricingError::Overflow));
    }
}
```

- Unit tests live in the file they test, in `mod tests`, so they can reach private items. `tests/` is for the integration lane.
- Names state the behaviour: `should_x_when_y` (snake case, per `CLAUDE.md`'s `Should_X_When_Y`).
- Arrange / act / assert separated by blank lines. No comments.

## Assertions — one expected condition

- `assert_eq!(actual, expected)` for values. The types derive `PartialEq + Debug`, so a failure prints both sides.
- `assert_matches!(result, Err(PlaceOrderError::OutOfStock(sku)) if sku == expected_sku)` for an enum variant. **Never `matches!(r, A | B)`** — that is an `OR` in an assertion.
- For `Ok`, assert the value, not just `is_ok()`: `assert_eq!(result.expect("pricing succeeds for a valid cart"), Money::eur(1_250))`.
- Assert the error **variant**, never its `Display` text.
- **No `if` / `for` / `match` deciding what to assert.** Tables go into `#[rstest] #[case]`.
- **No `?` in a test body.** A test returning `Result` reports the error without saying which line failed. Use `.expect("what was being done")`, which names the failed step and prints the error (allowed in tests via `clippy.toml`).
- `#[should_panic(expected = "…")]` only for a function whose contract is to panic on a broken invariant.

## The seams — what makes logic untestable

Fix the seam in production code first (a `pattern-writer` edit), then write the test.

| Seam | Untestable | Testable | In the test |
|---|---|---|---|
| **Time** | `OffsetDateTime::now_utc()` / `Instant::now()` inside logic | `now` passed as a parameter. For async timing, tokio's clock (`tokio::time::Instant`, `sleep`) | A fixed `datetime!(2026-10-31 12:00 UTC)`; `start_paused` + `tokio::time::advance` |
| **Identity** | `Uuid::now_v7()` inside logic | The id passed in, or generated by the caller | A literal `uuid!(…)` |
| **Randomness** | `rand::rng()` inside logic | An `&mut impl Rng` parameter | `StdRng::seed_from_u64(7)` |
| **Config** | `std::env::var` inside logic | The `Config` field passed in | A struct literal. Never `set_var` in a test — it is `unsafe` in edition 2024 and races with other tests |
| **Outbound I/O** | `reqwest` / an SDK client called directly | A trait the module owns, sized to what it calls | A hand-written fake struct |

```rust
struct RecordingMailer {
    sent: std::sync::Mutex<Vec<Email>>,
}

impl Mailer for RecordingMailer {
    async fn send(&self, email: Email) -> Result<(), MailError> {
        self.sent.lock().expect("mailer mutex").push(email);
        Ok(())
    }
}
```

**Preference order: real value → hand-written fake → `mockall`.** A fake is a few lines in Rust and survives refactors. Use `mockall` for call-count or argument expectations a fake would make awkward. With `#[async_trait]`, `#[automock]` must come **before** it. **Never mock a type you do not own** (`PgPool`, `reqwest::Client`): wrap it in your port and fake the port.

## Async tests and paused time

```rust
#[tokio::test(start_paused = true)]
async fn should_give_up_after_three_attempts_when_the_quote_service_keeps_failing() {
    let quotes = FailingQuotes::default();

    let result = fetch_quote_with_retry(&quotes, RetryPolicy::default()).await;

    assert_matches!(result, Err(QuoteError::Exhausted { attempts: 3 }));
}
```

- With paused time, the clock jumps forward whenever every task is idle, so seconds of backoff run instantly and deterministically. `tokio::time::advance(d)` moves it by hand.
- Only tokio's time is paused. Code that reads `std::time::Instant` or `SystemTime` is not, which is another reason to pass `now` in.
- Never `sleep` to wait for a spawned task. Await its `JoinHandle`, a `oneshot`, or a `Notify`.

## Parameterized cases and properties

```rust
#[rstest]
#[case(0, Err(QuantityError::Zero))]
#[case(1, Ok(1))]
#[case(1_000, Ok(1_000))]
#[case(1_001, Err(QuantityError::TooLarge))]
fn should_validate_the_quantity_boundaries(#[case] raw: u32, #[case] expected: Result<u32, QuantityError>) {
    assert_eq!(Quantity::try_from(raw).map(Quantity::get), expected);
}
```

```rust
proptest! {
    #[test]
    fn should_round_trip_any_valid_sku(raw in "[A-Z]{3}-[0-9]{4}") {
        let sku: Sku = raw.parse().expect("generated SKUs are valid");
        prop_assert_eq!(sku.to_string(), raw);
    }
}
```

Use properties for parsers, encoders and arithmetic. Commit the `proptest-regressions/` files they write — those are failures that were found once and must stay fixed.

## Test data

- 1–3 fields: a struct literal.
- **4+ fields: a builder** (`CLAUDE.md`), `fn a_line() -> LineBuilder` with defaults, so each test sets only its subject. Keep it in `#[cfg(test)]` code, or in a `test-support` feature when other crates need it.
- No shared `static` mutable state between tests; nextest's process-per-test hides that bug and `cargo test`'s threads expose it.

## The integration lane (not this skill's coverage)

Router tests through `tower::ServiceExt::oneshot`, and `#[sqlx::test]` query tests, are in-process but cross the framework or database boundary. **No `qa-*-rust` plugin exists yet**, so `be-rust` writes them in `tests/` **only when the task asks**. They run under their own command (`cargo nextest run --test api`), and they are excluded from the unit coverage measure. Black-box HTTP contract tests stay with `qa-api-typescript`.

## Coverage floor — ≥ 80% of the branches you wrote

The tests cover **at least 80% of the branches in the code the change wrote**: every file it created, whole, and the functions it changed in files that already existed. The scope is the change, never the repo.

- **Design for every branch; 80% is what gets measured.** Before writing tests, list the branch outcomes in the code you wrote: each `if`/`else`, `match` arm (including a guard's false case), `?` early return, `if let … else`, `&&`/`||` operand, `unwrap_or`/`ok_or` fallback, loop run zero and many times, and **both arms of every `Result`**. Give each one a test or an `rstest` case that asserts its effect.
- **Only an asserting test counts.** A test that runs a branch without asserting what it did is a **major** finding. `cargo-mutants` (27.x, works with nextest) is the tool that catches hollow tests: run `cargo mutants --file <changed file>` when the floor is met suspiciously fast.
- **Leave out by name** what the matrix says not to test (DTO modules, `main.rs`, generated code) and list each one in the report. Never reach 80% with `#[coverage(off)]` on code that has behaviour, or by lowering the number.
- **Measure — branch coverage needs nightly.** As of Rust 1.99 / cargo-llvm-cov 0.9, `--branch` is unstable. The measurement runs on nightly; the shipped build stays on the project's stable toolchain, so this is not an up-level:

  ```bash
  rustup toolchain install nightly --component llvm-tools-preview
  cargo +nightly llvm-cov nextest --branch --lib --summary-only
  ```

  Read the **Branches** cover column on the rows of the files the change wrote, and sum covered / total across them. Every file in the crate is compiled into the test binary, so an untested new file shows up at 0%, not as a missing row. cargo-llvm-cov has no `--fail-under-branches`; the gate reads the number. Uncovered regions (`--show-missing-lines`, or `--html`) list the misses.
- **No nightly available** (an air-gapped CI, a pinned image): measure lines on stable (`cargo llvm-cov nextest --lib --summary-only`). The floor becomes **80% of lines**, the same fallback `CLAUDE.md` applies to Swift, and the report says which measure was used.
- **Below 80%, write the missing tests.** The uncovered lines are the list.

## Rules

- One logical assertion per test; the variant or value, never the message
- No `if`/`for`/`match` driving assertions; no `?` in test bodies; no `sleep`
- Both arms of every `Result`; each error variant reachable from a test
- Time, ids, randomness and config passed in; outbound I/O behind a port the module owns
- Fakes before `mockall`; never mock `PgPool` or `reqwest::Client`
- Tests independent; no `set_var`; no shared statics
- ≥ 80% branch coverage of the change, measured on nightly or stated as the line fallback

## What NOT to do

- No `#[ignore]` without a linked issue
- No `insta` snapshot as the only assertion on a business value; no blind `cargo insta accept`
- No test that only checks `is_ok()` / `is_err()`
- No unit test spinning up `axum::serve`, a Testcontainer, or a real pool
- No `#[cfg(test)]` branches in production code that change behaviour under test
- No `mockall` expectations so strict they pin the implementation's call order when the order is not the contract

## Generation steps

1. **Detect** the runner and the dev-dependencies; the repo's choice wins.
2. **Pick the units** from the matrix; say why each excluded unit is excluded. **List each tested unit's branch outcomes** — that list is the test plan.
3. **Fix the seams** in production code (pass `now`, ids and rngs in; put outbound I/O behind a trait).
4. **Write the failing test**, watch it fail for the right reason (a `Gate: own tests` task may make that run), then make it pass.
5. **Add the boundary cases** with `rstest`: zero, one, max, overflow, empty, every error variant.
6. **Verify:** the tests pass, `cargo clippy --all-targets` is clean, and branch coverage of the change is ≥ 80%; report the counts and the figure. In a plan, `Gate: own tests` runs this task's tests and the coverage measure over its files; the last runnable task runs everything else.

## Handoffs

- A seam or type change → `pattern-writer`
- Query and router tests → `database-code` → Testing the queries; black-box HTTP → `qa-api-typescript`
- Timing semantics → `async-concurrency`
- Benchmarks → `performance`
- Review → `code-review`
- .NET / Java / Node equivalents → `backend/{dotnet,java,node}/skills/unit-testing`
