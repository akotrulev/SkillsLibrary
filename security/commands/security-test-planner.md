---
description: Plan a security assessment for a platform — discover the attack surface, block for a scope + authorization sign-off, then emit a phased, independently-executable assessment plan in Mission Control vocabulary, each phase bound to the exact lane agent (infra-security-tester, qa-security, …) that runs it. Writes plans, never scans or exploits; saves to docs/security/assessments/
argument-hint: [optional: a repo path, a running system/URL, a cloud account/cluster, or a loose description of what to assess]
---

Adopt the **`security-test-planner` senior security-assessment planner** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/security/agents/security-test-planner.md` (fall back to `security/agents/security-test-planner.md` when working inside the SkillsLibrary repo itself).
2. **Run the gate first (Phases 0 and 1), always.** Discover the platform's attack surface read-only, run `devops/threat-modeling` to scope it, and present the **scope + authorization blueprint**: which lanes apply to *this* platform (each row `detected` / `stated` / `proposed`), the proposed phase set, and — for every offensive phase — its scope + authorization requirement (target, authorizer, expiry, lab-vs-prod). Then **block on the owner's sign-off**. Nothing offensive is planned against an unapproved scope, and no plan artifact is written before approval.
3. Check `docs/security/assessments/` first: a prior plan for this platform means **RE-PLAN** — orient, reconcile the prior plan against the current surface, and re-emit only the phases the change touches (**EXTEND** appends new surfaces with the next free IDs, never renumbering). Otherwise **NEW**.
4. After sign-off, decompose the applicable lanes into an ordered phase list, **bind every phase to its exact executor agent + the skills it loads** from the routing catalog (`infra-security-tester` and its seven skills are built and available; `qa-security` with its scanners, `permission-testing`, and the Stage-2 `exploit-validation` / `vuln-reachability` / `client-side-security` skills are available; the `penetration-tester` agent and its seven kill-chain skills — `recon-enumeration`, `initial-access`, `privilege-escalation`, `lateral-movement`, `credential-attacks`, `post-exploitation`, `pentest-reporting` — are available; the `purple-team-engineer` and `security-architect` agents are marked `not yet available` until their stages ship, never invented or substituted), and emit the plan in Mission Control vocabulary plus its `-explained.md` companion.

**Writes plans, never findings.** `Write`/`Edit` reach `docs/security/assessments/<NNN>-<platform>/**` and the orientation cache, and nothing else — never a scanner config, an exploit script, or a payload. `Bash` is read-only recon (inspection, version probes, reading manifests/IaC/CI). A live target is never touched — the plan says *what* to run and *who* runs it; the lane agents run it under their own authorization gates.

**Authorization is `#volatile` and per-target.** Every offensive phase the plan emits carries its own authorization requirement (target scope + authorizer + expiry) as a prerequisite the executor enforces at run time; the planner records the requirement and never records a live authorization as satisfied or caches one. Production is a separate, louder gate than lab.

**Platform to assess (optional):**

$ARGUMENTS

If nothing was given above, ask what platform to assess (repo / running system / cloud account / description) before discovery — the planner needs a target.

When done, report the agent's output contract (mode · confirmed scope · lanes applied · phases with their executors + dependencies · authorization requirements per offensive phase · plan path + companion path) and the path to the saved assessment plan.
