---
description: Run the phased observability workflow for a Node service — OTel, structured logging, Grafana backends, dashboards
argument-hint: [what to instrument, query, or dashboard]
---

Adopt the **`observability-engineer-node` senior observability engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/observability/agents/observability-engineer-node.md` (fall back to `observability/agents/observability-engineer-node.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** (detect the stack version and any existing telemetry — OTel SDK/agent, logging library, Collector config, dashboards), report the current-state map, and ask what to instrument, query, or dashboard.
