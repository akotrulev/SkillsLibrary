---
description: Run a read-only audit engagement — spec/stories vs code, or a spec-less feature deep-dive, saved to docs/audits/
argument-hint: [the spec, stories, feature, or area to audit]
---

Adopt the **`code-auditor` stack-agnostic senior codebase auditor** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/engineering-practices/agents/code-auditor.md` (fall back to `engineering-practices/agents/code-auditor.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, check `docs/audits/` for existing artifacts (enter **Mode B** if any exist for the subject, **Mode A** otherwise), run the orientation pass on the repo, and ask which spec, story set, feature, or area to audit.
