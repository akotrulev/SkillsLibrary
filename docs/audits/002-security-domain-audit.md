# Security-Domain Audit — `security/`

**Date:** 2026-08-20 · **Auditor:** senior cyber-security officer (read-only) · **Scope:** the `security/` tree (13 skills + 4 agents + 4 commands), the two plugins it packages (`penetration-testing`, `security-governance`), and every outbound cross-reference into `qa/`, `devops/`, `observability/`, `engineering-practices/`.

**Method:** read all 13 `SKILL.md` and all 4 agent/command files end to end; verified every peer-skill path referenced by `security/` resolves on disk; verified marketplace registration; checked frontmatter-name consistency, description limits, and the offensive-safety controls against professional norms (PTES / OWASP-WSTG / MITRE ATT&CK, CIS, the framework version pins). Read-only — nothing changed.

---

## Verdict

**The domain is in strong shape and safe to ship.** The load-bearing safety model — the nine-control §5 authorization gate, "no DoS ever," loot redaction, cleanup verification, production-as-a-second-gate, and the "never fixes / find-and-retest" fence — is applied *consistently and identically* across every offensive skill and both offensive agents, not just asserted once. Tool version pinning is unusually disciplined and current, including honest tracking of upstream renames/relocations that stale tutorials get wrong. The purple-team lane's telemetry-backend honesty gate and four-tier outcome model are a genuinely well-designed piece of blue-team engineering. The defensive/governance lane correctly *maps* rather than *certifies* and routes wiring rather than editing code.

**Findings: 0 blocker · 0 major · 2 minor · 1 nit (adjacent, out-of-tree).** No security-content defect, no unsafe guidance, no broken authorization control. The two minors are documentation-drift issues in the planner, one of which trips the plugin family's own stated quality bar and is worth a one-line fix.

---

## Findings

| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| minor | `security/agents/security-test-planner.md:37` | The routing catalog's "Loads (for reference)" cell for the mobile phase names **`mobile-security`**, which is **not a real skill**. The actual skills are `mobile-app-scan` (`qa-security-mobile-app-scan`) and `mobile-runtime-testing` (`qa-security-mobile-runtime-testing`). Every other cell in that table resolves to a real skill folder — this is the sole exception. It matters because this is the exact table the planner uses to populate an emitted phase's `skills[]`, and the plugin family's own doctrine (CLAUDE.md, `be-planner`/MC contract) calls an invented skill name "the single most damaging defect in the pack" since Mission Control binds on that string. | Replace the cell with `mobile-app-scan` · `mobile-runtime-testing` (MobSF / MASVS-MASTG). |
| minor | `security/commands/security-test-planner.md:` step 2 vs `security/agents/security-test-planner.md` | **Command↔agent drift.** The command instructs the planner to "run `devops/threat-modeling` to scope it" during the gate, but the agent definition never loads it: `threat-modeling` appears only in the infra-security-tester routing row ("for reference"), the "loaded when the input warrants it" list omits it, and phases 0–5 don't invoke it. This also sits at the edge of the planner's own "writes plans, never findings / `Bash` is read-only recon" fence, since `threat-modeling` produces a threat-register artifact (it is `infra-security-tester`'s Phase-0 job). | Pick one: either add `threat-modeling` to the agent's "loaded when the input warrants it" section as an explicit planning aid (and state its artifact stays advisory to the plan), or drop the "run devops/threat-modeling" instruction from the command and let the surface ledger do the scoping. |
| nit (out-of-tree) | root `CLAUDE.md` QA catalog | Adjacent observation, **not a defect in `security/`:** the root catalog text still lists the qa scanner gates as `sast` and `nuclei`, but the folders are `code-scan` (`qa-security-code-scan`) and `known-vuln-scan`. The `security/` skills themselves reference the **current** names correctly (e.g. `compliance-evidence-mapping` cites `qa-security-code-scan`), so the security domain is internally consistent — the drift is only in the CLAUDE.md prose. Flagged for hygiene; fix belongs to the QA-catalog owner, not this audit. | Refresh the CLAUDE.md scanner-gate list to `code-scan`/`known-vuln-scan` when the QA catalog is next touched. |

---

## What was verified clean

- **All outbound cross-references resolve.** Every peer skill named by `security/` exists on disk: `devops/{infra-controls-validation, threat-modeling, k8s-security, iac-security, cloud-posture, container-runtime-security, supply-chain-security}`, `observability/{queries, dashboards}`, `engineering-practices/{agent-orientation-cache, code-comments}`, `qa/_shared/security-testing/{exploit-validation, vuln-reachability, client-side-security, code-scan, secrets-scan, mobile-app-scan, mobile-runtime-testing}`, `qa/_shared/agents/qa-security`. The planner's full routing catalog resolves except the one `mobile-security` cell above.
- **Marketplace registration matches the tree.** `penetration-testing` = 7 kill-chain + 2 purple skills + 2 always-on `ep-*` + 3 agents/commands; `security-governance` = 4 `secgov-*` skills + 2 always-on `ep-*` + `security-architect`. Consistent with CLAUDE.md.
- **Frontmatter names are consistent** with the three lane prefixes (`pentest-*`, `purpleteam-*`, `secgov-*`) and the four agent names match their commands. All skill descriptions are 468–778 chars — well within limits, all carrying explicit "not for…" negative-scope clauses.
- **The purple-team placement decision holds.** Homing `atomic-simulation`/`detection-validation` in `penetration-testing` (because the red half executes live techniques under §5) rather than `security-governance` is correctly reasoned and consistently wired; the author→validate→roll-up loop closes across plugins by named handoff.

## Posture strengths worth preserving (security-officer lens)

1. **The §5 gate is real, not boilerplate, and self-consistent.** The scope file cannot be self-authored into a green light — Phase 0 requires re-confirming `#volatile` authorization *with the owner* live each run, authorization is never cached (`ep-agent-orientation-cache` is explicitly barred from holding it), and the mid-run abort re-reads the scope file before every phase/technique. `Write` is scoped so the agent can *help author* a scope file but cannot treat its own draft as authorization.
2. **"No DoS, ever" is enforced at the tool level, not just stated** — masscan `--rate` + `--excludefile`, hydra low `-t` + spray-over-guess + agreed lockout threshold, Responder `-A` passive default, kernel exploits as version-matched lab-first disruptive acts, NetExec spray production-excluded.
3. **Loot redaction is absolute and uniform** — every skill reports *that* a secret was recovered + blast radius, never contents; the credential-attacks skill even frames a crack result as a *policy signal* ("cracked in 40s under best64"), which is exactly the defensive output an owner needs.
4. **Version pinning + honest rename tracking is best-in-class** — CrackMapExec→NetExec (`nxc`), BloodHound CE vs legacy, `mitre/caldera`→`apache/caldera`, `sigmac`→`sigma-cli`, IMDSv1→v2, ATT&CK v19's Stealth/Defense-Impairment split. Stale-tutorial traps are called out inline.
5. **The blue-half telemetry gate prevents the classic purple-team lie** — "no detection surface" is a distinct outcome from "not detected," and the logged-only (rule gap) vs no-signal (telemetry gap) split routes fixes to the right owner. Detection-engineering's "authored ≠ validated" and the true-AND-benign unit-test merge gate are the right disciplines.
6. **Governance stays in its lane** — compliance-evidence-mapping *maps, never certifies* (SCF/OSCAL as the crosswalk authority, `#present`/`#partial`/`#gap` tiers read from artifacts); security-architect *consumes and authors*, never scans or edits code; a proven kill-chain path is explicitly ranked above a merely-detected weakness in risk normalization.

---

## Recommendation

Ship as-is; apply the two minor planner corrections at convenience. The `mobile-security` cell is the higher-priority of the two because it can propagate a non-resolving `skills[]` entry into an emitted assessment plan, which the family's own contract treats as its most damaging defect class. Neither finding blocks release.
