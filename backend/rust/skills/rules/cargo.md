---
paths:
  - "**/Cargo.toml"
  - "**/rust-toolchain{,.toml}"
  - "**/{clippy,.clippy}.toml"
  - "**/.cargo/config{,.toml}"
---

<!-- be-rust rules v2 (2026-11-21): Cargo manifests, toolchain and lint. Ids checked against the clippy documentation and `rustc` lint list on 2026-11-21 (Rust 1.100, clippy 0.1.100). Installed by /be-rust:rules; edit to fit this project. -->

# Cargo manifest and toolchain standards

Severity tags as in the core Rust rules: **blocker**, **major**, **minor**, **nit**.

- Never raise the edition, `rust-version`, the toolchain channel or a dependency's major as a side effect of a change. *major*
- A service pins `rust-toolchain.toml` to one stable and sets `rust-version` to it; a library sets `rust-version` to the oldest toolchain it tests. *minor*
- `Cargo.lock` is committed for every binary. *major*
- Lints live once, in `[lints]` or `[workspace.lints]` with `[lints] workspace = true` in members; groups get `priority = -1`; never the whole `restriction` group. *minor*
- Shared versions sit in `[workspace.dependencies]`. A dependency is earned: not for what std has, `default-features = false` on heavy crates, nothing unmaintained (`async-std` is discontinued). *minor*
- The `opentelemetry*` crates and `tracing-opentelemetry` stay on one release train. *major*
- `panic = "abort"` breaks `CatchPanicLayer` and tokio's per-task panic isolation, and `target-cpu=native` breaks images run on other CPUs: neither without the caveat accepted in writing. *major*
- An LTO, `codegen-units`, allocator or PGO change comes with a before/after measurement. A profiling profile inherits `release` with `debug = "line-tables-only"` and is never stripped. *major; minor for the profile*

Each row below is a rule of `rust.md` or `rust-tests.md` that rustc or clippy detects, so the build catches it before a review does. Rules no lint detects stay in those files and get no row: `indexing_slicing` and `arithmetic_side_effects` flag every index and every sum, not the input-derived ones, and `wildcard_enum_match_arm` flags enums the crate does not own.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| Lints live once, in `[workspace.lints]`, and every member inherits them (`cargo.md`) | Cargo | `[workspace.lints]` with `[lints] workspace = true` in each member | setting |
| No `unsafe` in application code (`rust.md`, Logging, secrets and `unsafe`) | rustc | `unsafe_code = "forbid"` | error |
| Every `unsafe` block has a `// SAFETY:` comment (`rust.md`, Logging, secrets and `unsafe`) | clippy | `undocumented_unsafe_blocks` | error |
| No `unwrap()` outside tests (`rust.md`, Panics and errors) | clippy | `unwrap_used`, with `allow-unwrap-in-tests = true` in `clippy.toml` | error |
| No `let _ = fallible();` (`rust.md`, Panics and errors) | clippy | `let_underscore_must_use` | error |
| No discarding `.ok()` (`rust.md`, Panics and errors) | clippy | `unused_result_ok`, from 1.82 | error |
| `let _ = guard;` drops it at once: bind `_guard` (`rust.md`, Ownership and types) | clippy | `let_underscore_lock` | error |
| `.map_err(\|_\| …)` keeps the source (`rust.md`, Panics and errors) | clippy | `map_err_ignore` | error |
| No `std::process::exit` in service code (`rust.md`, Panics and errors) | clippy | `exit` | error |
| Narrowing casts use `try_from`, never `as` (`rust.md`, Numbers and text) | clippy | `cast_possible_truncation` | error |
| No byte slicing of text (`rust.md`, Numbers and text) | clippy | `string_slice` | error |
| No `std::sync` guard alive at an `.await` (`rust.md`, Async on tokio) | clippy | `await_holding_lock` | error |
| No `thread::sleep` on a runtime thread, in a test either (`rust.md`, Async on tokio; `rust-tests.md`) | clippy | `disallowed_methods`, `std::thread::sleep` in `clippy.toml` | error |
| `std::env::var` is read in `config.rs` only (`rust.md`, HTTP, config and state) | clippy | `disallowed_methods`, `std::env::var` and `std::env::var_os` in `clippy.toml` | error |
| A test never calls `set_var` (`rust-tests.md`) | clippy | `disallowed_methods`, `std::env::set_var` in `clippy.toml` | error |
| No `lazy_static!` and no `once_cell` in new code (`rust.md`, Ownership and types) | clippy | `disallowed_macros`, `lazy_static::lazy_static`; `disallowed_types`, the four `once_cell` types, in `clippy.toml` | error |
| `tracing` events, never `println!` (`rust.md`, Logging, secrets and `unsafe`) | clippy | `print_stdout`, `print_stderr` | error |
| A lint exception is `#[expect(lint, reason = "…")]`, never `#[allow]` or a crate-wide `#![allow]` (`rust.md`, Lints and comments) | clippy | `allow_attributes`, `allow_attributes_without_reason` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each clippy row is `<lint> = "deny"` in `[workspace.lints.clippy]`, which is an error. Pick `restriction` lints by name, never the whole group, and give a group like `pedantic` `priority = -1` so the named lints win. `cargo clippy --workspace --all-targets --keep-going` reads the table; a member without `[lints] workspace = true` gets none of it and no warning says so.
- The `disallowed_*` rows are entries in `clippy.toml`, each with a `reason`. They are the one place the stack names a symbol; the rows above do not repeat the list.
- A build script that must read `OUT_DIR` carries `#[expect(clippy::disallowed_methods, reason = "…")]`. The composition root that builds the config does the same for `std::env::var`, and the clock seam for any time source a project bans.
- `allow-unwrap-in-tests = true` exempts `#[cfg(test)]` code and `tests/`; `rust-tests.md` still asks for `.expect("what was being done")` there. `expect_used` is not a row.
- `unused_result_ok` suggests `let _ = …`, which `let_underscore_must_use` forbids, so the two together leave only handling the error. A project whose `rust-version` is below 1.82 leaves `unused_result_ok` out and lists the row as unenforced.
- In edition 2024 `std::env::set_var` is `unsafe`, so `unsafe_code = "forbid"` already stops it. The `disallowed_methods` row covers edition 2021.
- Clippy lints an `include!`d generated file with the crate's own table, so a generated `unwrap()` is an error. Put `#[expect(clippy::lint, reason = "generated by build.rs")]` on the module that includes it; code expanded by an external macro is skipped by most lints.
- A scaffold from `pattern-writer` is a starting point, and this table wins where they differ: its `print_stdout`, `print_stderr` and `allow_attributes_without_reason` at `warn` become `deny`.

`Cargo.toml`, at the workspace root:

```toml
[workspace.lints.rust]
unsafe_code = "forbid"

[workspace.lints.clippy]
unwrap_used = "deny"
let_underscore_must_use = "deny"
unused_result_ok = "deny"
let_underscore_lock = "deny"
map_err_ignore = "deny"
exit = "deny"
cast_possible_truncation = "deny"
string_slice = "deny"
await_holding_lock = "deny"
print_stdout = "deny"
print_stderr = "deny"
undocumented_unsafe_blocks = "deny"
allow_attributes = "deny"
allow_attributes_without_reason = "deny"
disallowed_methods = "deny"
disallowed_macros = "deny"
disallowed_types = "deny"
```

`clippy.toml`:

```toml
allow-unwrap-in-tests = true
disallowed-methods = [
    { path = "std::thread::sleep", reason = "Never block a runtime thread" },
    { path = "std::env::var", reason = "Read the environment in config.rs only" },
    { path = "std::env::var_os", reason = "Read the environment in config.rs only" },
    { path = "std::env::set_var", reason = "Pass configuration in" },
]
disallowed-macros = [
    { path = "lazy_static::lazy_static", reason = "Use LazyLock for immutable data" },
]
disallowed-types = [
    { path = "once_cell::sync::Lazy", reason = "Use LazyLock" },
    { path = "once_cell::sync::OnceCell", reason = "Use OnceLock" },
    { path = "once_cell::unsync::Lazy", reason = "Use LazyCell" },
    { path = "once_cell::unsync::OnceCell", reason = "Use OnceCell" },
]
```
