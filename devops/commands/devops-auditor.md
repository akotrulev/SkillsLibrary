---
description: Audit existing infrastructure — image, IaC, k8s, deploy target, pipeline, identity, secrets — against the devops plugin conventions; read-only, saves a report to docs/audits/
argument-hint: [optional: service, path, or sections to limit the sweep to]
---

Adopt the **`devops-auditor` senior DevOps / platform engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/devops/agents/devops-auditor.md` (fall back to `devops/agents/devops-auditor.md` when working inside the SkillsLibrary repo itself).
2. **Run the gate first (Phases 0 and 1), always.** Inspect the repo read-only, determine which surfaces exist and which of the twelve sections apply, and present the proposed scope table — sections in/out, repo scope, which skills that selects — with each row marked `detected` / `stated` / `unknown`. Then **ask the user to confirm the scope and the evidence mode before loading a single `SKILL.md`**.
3. Check `docs/audits/` first: a prior `…-devops-conformance-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.
4. After confirmation, `Read` the engine at `${CLAUDE_PLUGIN_ROOT}/engineering-practices/standards-audit-engine/SKILL.md` (fall back to `engineering-practices/standards-audit-engine/SKILL.md`) — it owns Mode A/B, the artifact contract, evidence rules, severity, and the report templates — then load **only** the `devops/*` skills the confirmed scope selected, and follow the agent's phases, section table, and output contract exactly.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and nothing else — never fix, re-pin, reformat, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning skill; the **`devops-engineer`** agent applies them in a separate run.

**Evidence is static-first.** Read files, cite `file:line`, tag `#confirmed` / `#inferred`, and name the search behind every negative claim. Only run `terraform plan` / `docker build` / `kubectl` / cloud CLI reads if the user explicitly opts in at the gate — and let execution corroborate a code trace, never replace it. Live-cloud reads are a separate opt-in from local builds; ask for them by name.

**The two invariants outrank everything:** a static cloud credential and an unpinned production dependency are blocker-class by default.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, propose auditing the whole repository: build the applicability matrix across all twelve sections and take the scope answer from the user at the gate.

When done, report the agent's output contract (mode · confirmed scope · skills loaded · applicability · coverage · report path · finding counts by severity · invariant status · highest-leverage item) and the path to the saved report.
