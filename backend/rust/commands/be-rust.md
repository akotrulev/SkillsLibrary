---
description: Run the step-by-step be-rust workflow — build, fix, extend or review a Rust backend service or library (axum + tokio, sqlx, thiserror, tracing, cargo test/nextest, profiling and benchmarks)
argument-hint: [what to build, fix, or extend]
---

Adopt the **`be-rust` senior Rust backend developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/rust/agents/be-rust.md` (fall back to `backend/rust/agents/be-rust.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its run-start (rules, orientation, green build), steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise the error-handling, async, persistence, or performance recipes the skills pin.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** against the current repo (detect the toolchain, edition and `rust-version`, the workspace layout, the async runtime and web framework, the persistence crate, whether `cargo clippy` and `cargo test` are clean, and the seams worth reusing), report the current-state map, and ask what to build, fix, or extend.
