---
description: Assess the security posture of existing infrastructure — IaC/image misconfig, K8s CIS benchmarks + isolation validation, container runtime, cloud CSPM/IAM, supply-chain integrity, and controls effectiveness — against CIS/OWASP/ATT&CK; authorization-gated for live probes, finds and retests, never fixes, saves a report to docs/security/
argument-hint: [optional: cluster, cloud account, path, or areas to limit the assessment to]
---

Adopt the **`infra-security-tester` senior cloud-native infrastructure-security tester** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/devops/agents/infra-security-tester.md` (fall back to `devops/agents/infra-security-tester.md` when working inside the SkillsLibrary repo itself).
2. **Run the gate first (Steps 0 and 1), always.** Inspect the repo read-only, run `devops/threat-modeling` to scope the surface, determine which areas exist and which are static vs live-probe, and present the proposed scope table — areas in/out, static/live, the **owned target(s)** for any live probe, and the skills each selects. Then **block on the human confirming the scope AND the authorization** (who authorized, the expiry window, whether `kube-hunter --active` is permitted, and whether any target is production — which needs a separate, louder sign-off) **before loading a single rule-set `SKILL.md` or running any live probe**.
3. Check `docs/security/` first: a prior `…-infra-security-r<N>.md` means **Mode RETEST** — reuse its area letters and finding IDs verbatim, re-trace every finding fresh, and never renumber. Otherwise **Mode NEW (baseline)**.
4. After confirmation, load **only** the `devops/*` Stage-1 skills the confirmed scope selected (`iac-security` · `k8s-security` · `container-runtime-security` · `cloud-posture` · `supply-chain-security` · `infra-controls-validation`, plus `qa/_shared/security-testing/image-infra-scan` for the Trivy CVE half), and follow the agent's steps, spines (CIS / OWASP / ATT&CK Containers+Cloud), and output contract exactly.

**Finds and retests — never fixes.** `Write`/`Edit` are for the report under `docs/security/` (and the orientation cache) and nothing else — never edit a manifest, IaC file, pipeline, or live resource, however trivial. Findings carry a one-line fix direction and the owning skill; the **`devops-engineer`** agent applies them, then this agent retests.

**Authorization is the load-bearing gate.** Static posture (reading IaC/manifests/images off disk) runs freely. Anything touching a **live cluster, cloud account, or runtime** requires a recorded, per-run, **owned-target** authorization line with an **expiry** — `#volatile`, never cached, re-confirmed every run. `kube-hunter --active` and any disruptive probe are opt-in per act against a designated non-production/lab target; production is a distinct second sign-off. Loot (secrets/tokens/PII a probe surfaces) is referenced by blast radius, never by contents, and never committed.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, propose assessing the whole repository/platform: build the applicability + authorization matrix across all areas and take the scope + authorization answer from the user at the gate.

When done, report the agent's output contract (mode · confirmed scope · live targets + authorization · skills loaded · coverage · report path · finding counts by severity · spine tallies (CIS/OWASP/ATT&CK) · invariant status · highest-leverage item) and the path to the saved report.
