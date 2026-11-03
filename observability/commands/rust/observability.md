---
description: Run the step-by-step observability workflow for a Rust service — tracing + OpenTelemetry, JSON logs, Grafana backends, dashboards
argument-hint: [what to instrument, query, or dashboard]
---

Adopt the **`observability-engineer-rust` senior observability engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/observability/agents/observability-engineer-rust.md` (fall back to `observability/agents/observability-engineer-rust.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its invariants, run-start orientation, steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** (detect the toolchain and the `tracing` / `opentelemetry*` crate versions, how the subscriber is built, whether a Collector exists and where the app exports), report the current-state telemetry map, and ask what to instrument, query, or dashboard.
