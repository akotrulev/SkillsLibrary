---
description: Provision the Metasploit toolchain for an authorized engagement before any recon/exploitation — install the Docker image pinned by digest, stand up the engagement-named msfdb workspace, and register the official Metasploit MCP server (msfmcpd) with the agent, read-only by default (the 4 dangerous tools stay off until the exploitation window). Requires a committed engagement scope file; aims the toolchain only at in-scope infrastructure. Touches no target.
argument-hint: [optional: the engagement id / scope-file path, or the owned/lab target to provision for — a committed scope file is still required before wiring anything]
disable-model-invocation: true
---

Adopt the **`penetration-tester` senior offensive-security engineer** role, scoped to its **provisioning** step for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/security/agents/penetration-tester.md` (fall back to `security/agents/penetration-tester.md` when working inside the SkillsLibrary repo itself).
2. Run its **every-run gate before any act**: orient, validate the committed engagement scope file against the nine controls, re-confirm the `#volatile` authorization for this run, and announce the gate result. With no committed, unexpired scope file and a live authorization, **wire nothing** — present the scope-file shape and offer to help write it.
3. Then load `${CLAUDE_PLUGIN_ROOT}/security/metasploit-setup/SKILL.md` (fall back to `security/metasploit-setup/SKILL.md` in this repo) and follow it to provision the toolchain: the Docker image **pinned by digest**, an engagement-named `msfdb` workspace, and the Metasploit MCP server registered **read-only** (its 4 dangerous tools off — they are enabled later, only for the exploitation step, under control 3). Record the pinned digest and the MCP registration in `docs/security/engagement-<NNN>.md`.

**Setup, not an attack.** This provisions the attacker-side toolchain and aims it only at the scope file's in-scope infrastructure; it touches no target. The first target-touching act is Recon's, under `/penetration-testing:pentest`.

**Engagement / target (optional):**

$ARGUMENTS

If nothing was given above, ask for the engagement id or scope-file path (or offer to help author the scope file) before provisioning anything.
