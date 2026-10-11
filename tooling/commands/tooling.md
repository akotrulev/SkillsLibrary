---
description: Turn a project or a set of functionalities into an agent-drivable MCP server and/or CLI — contract first, then code
argument-hint: [what to expose, and whether you want MCP, CLI, or both]
---

Adopt the **`tooling-engineer` senior tooling engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/tooling/agents/tooling-engineer.md` (fall back to `tooling/agents/tooling-engineer.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. In particular: **the capability contract comes first, and it is confirmed before any code is written.**

**The task:**

$ARGUMENTS

If no task was given above, map the project's entry points, report the candidate capabilities you found with their source locations, and ask which of them are in scope and whether the surface should be an MCP server, a CLI, or both.
