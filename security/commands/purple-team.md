---
description: Run authorization-gated purple-team continuous validation against an owned/lab target — detonate known MITRE ATT&CK techniques (red) and assert the SIEM/guardrail/alert actually fired (blue), one technique at a time, to prove detections still work and catch security drift. Refuses to simulate without a committed engagement scope file, gates every assertion on a telemetry backend being present, scores each technique detected/not-detected (not CVSS), cleans up every atomic, and saves a coverage matrix + drift delta + action log + cleanup verification to docs/security/.
argument-hint: [optional: the engagement id / scope-file path, the owned/lab target, or the ATT&CK technique set to validate — the agent still requires a committed scope file and a telemetry backend before it can validate]
---

Adopt the **`purple-team-engineer` purple-team engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/security/agents/purple-team-engineer.md` (fall back to `security/agents/purple-team-engineer.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its invariants (the engagement safety model and the telemetry gate), the gate it runs before any detonation, its steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise techniques the skills own.

**The scope-file gate is not optional.** With no committed, unexpired engagement scope file and a live authorization re-confirmed this run, simulate nothing. With no telemetry backend, report "no detection surface" rather than scoring techniques not-detected.

**Target / engagement / technique set (optional):**

$ARGUMENTS

If nothing was given above, ask for the engagement id or scope-file path (or offer to help author the scope file) before anything else; the agent detonates only against a committed, in-scope, authorized target.
