---
paths:
  - "**/Cargo.toml"
  - "**/rust-toolchain{,.toml}"
  - "**/{clippy,.clippy}.toml"
  - "**/.cargo/config{,.toml}"
---

<!-- be-rust rules v1 (2026-11-03): Cargo manifests and toolchain. Installed by /be-rust:rules; edit to fit this project. -->

# Cargo manifest and toolchain standards

Severity tags as in the core Rust rules: **blocker**, **major**, **minor**, **nit**.

- Never raise the edition, `rust-version`, the toolchain channel or a dependency's major as a side effect of a change. *major*
- A service pins `rust-toolchain.toml` to one stable and sets `rust-version` to it; a library sets `rust-version` to the oldest toolchain it tests. *minor*
- `Cargo.lock` is committed for every binary. *major*
- Lints live once, in `[lints]` or `[workspace.lints]` with `[lints] workspace = true` in members; groups get `priority = -1`; never the whole `restriction` group. *minor*
- The lint table denies `unwrap_used` and `undocumented_unsafe_blocks` and forbids `unsafe_code` in application crates. No lint is loosened to `allow` to make a change pass, and no `#![allow(clippy::all)]` / `#![allow(warnings)]`. *major*
- Shared versions sit in `[workspace.dependencies]`. A dependency is earned: not for what std has, `default-features = false` on heavy crates, nothing unmaintained (`async-std` is discontinued). *minor*
- The `opentelemetry*` crates and `tracing-opentelemetry` stay on one release train. *major*
- `panic = "abort"` breaks `CatchPanicLayer` and tokio's per-task panic isolation, and `target-cpu=native` breaks images run on other CPUs: neither without the caveat accepted in writing. *major*
- An LTO, `codegen-units`, allocator or PGO change comes with a before/after measurement. A profiling profile inherits `release` with `debug = "line-tables-only"` and is never stripped. *major; minor for the profile*
