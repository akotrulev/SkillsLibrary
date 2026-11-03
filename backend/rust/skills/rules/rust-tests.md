---
paths:
  - "**/tests/**/*.rs"
  - "**/benches/**/*.rs"
  - "**/{tests,test_support,test_utils}.rs"
  - "**/*_{test,tests}.rs"
---

<!-- be-rust rules v1 (2026-11-03): tests. Installed by /be-rust:rules; edit to fit this project. An inline #[cfg(test)] module matches no glob: the core file and the be-rust skills point here. -->

# Rust test standards

Severity tags as in the core Rust rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. They hold for inline `#[cfg(test)] mod tests` too.

- Unit tests are in-process, in `mod tests` beside the code: no socket, real pool, `axum::serve`, container or wall clock. Router `oneshot` and `#[sqlx::test]` tests are integration, in `tests/`, outside the unit coverage. *major*
- Names state behaviour: `should_<outcome>_when_<condition>`. *minor*
- One expected condition per assertion: never `||` or `matches!(r, A | B)`. Assert the error variant, never its text; an `Ok` asserts its value, not `is_ok()`. *major*
- No `if` / `for` / `match` driving assertions: `#[rstest] #[case]`. No `?` in a test body: `.expect("what was being done")`. *major; minor for `?`*
- Both arms of every `Result`; every error variant reached by a test. *major*
- No sleep to wait: `start_paused` and `advance`, or await the `JoinHandle` / `oneshot` / `Notify`. *major*
- Time, ids, randomness and config are passed in; never `set_var`. *major*
- Hand-written fakes before `mockall`; never mock a type the crate does not own (`PgPool`, `reqwest::Client`); no expectations pinning a call order that is not the contract. *major; minor for order*
- No SQLite or mocked pool standing in for Postgres. *major*
- Tests are independent: no shared `static`, no order dependence. *major*
- No `#[cfg(test)]` branch in production code that changes behaviour. *major*
- `#[ignore]` names a linked issue; an `insta` snapshot is never the only assertion on a business value, nor accepted blind. *minor*
- Test data with four or more fields comes from a builder; `proptest-regressions/` is committed. *minor*
- New code ships with unit tests covering ≥ 80% of the branches it wrote (`cargo +nightly llvm-cov --branch`; 80% of lines on stable, stated). Only an asserting test counts; no `#[coverage(off)]` on code with behaviour. *major*
- A fixed hot path keeps its benchmark, with realistic sizes and `std::hint::black_box`; CI gates on instruction counts, not shared-runner wall clock. *minor*
