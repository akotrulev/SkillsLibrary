---
description: Run an authorization-gated, full-kill-chain penetration test against an owned/lab target — recon → exploitation → privilege escalation → lateral movement → post-exploitation (capped at proof) → report. Refuses to start without a committed engagement scope file, re-reads it before every phase, halts if an act would fall outside it, redacts all loot, and saves an executive+technical report with a full action log and cleanup verification to docs/security/. Consumes a qa-security exploit-validation proof as feedstock.
argument-hint: [optional: the engagement id / scope-file path, or the owned/lab target to test — the agent still requires a committed scope file before any act]
---

Adopt the **`penetration-tester` senior offensive-security engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/security/agents/penetration-tester.md` (fall back to `security/agents/penetration-tester.md` when working inside the SkillsLibrary repo itself).
2. **Run the rules-of-engagement gate first (Phase 0), always, before any offensive act.** Read the committed engagement scope file `docs/security/engagement-<NNN>.md`; confirm every required field is present and the window is **unexpired** — in-scope hosts/CIDRs/accounts, hard exclusions, allowed techniques, blast-radius cap, data-handling, start/stop window, named authorizer, and lab-vs-production (production needs a **separate, louder second sign-off**). If the scope file is **absent, expired, or ambiguous**, present the required shape and **STOP** — help author it, but run nothing. Re-confirm the `#volatile` authorization live this run (never read a live authorization as satisfied from the orientation cache).
3. Check `docs/security/` first: a prior `<NNN>-pentest-r<N>.md` for this engagement means **RETEST** — re-confirm a fresh authorization (the old window has expired), re-attack only the in-scope findings, and prefix each **Resolved** / **Still open** / **Still open (regressed)** / **New** (Resolved only after re-running the attack that round). Otherwise **NEW**.
4. After the gate, run the phases in order — **1 Recon** (`recon-enumeration`) → **2 Exploitation** (`initial-access`, consuming a `qa-security` `exploit-validation` single-vuln proof as feedstock) → **3 Privilege escalation** (`privilege-escalation`) → **4 Lateral movement** (`lateral-movement`, `credential-attacks`) → **5 Post-exploitation, capped at proof** (`post-exploitation`, `credential-attacks`) → **6 Report + cleanup verification** (`pentest-reporting`) — **re-reading the scope file before each phase and halting the run if the next act would fall outside it** (§5 rule 9 — the mid-run abort, an explicit kill switch, never silent scope-narrowing).

**Owned/lab targets only; you never fix.** `Write`/`Edit` reach the report under `docs/security/`, the scope file (to help author it), and the orientation cache — nothing else. Remediation is the owning `be-*` / `fe-*` / `devops-engineer` agent's; you retest after they fix. **No DoS, ever**; persistence is demonstrated then removed and logged; C2 stays inside the authorized environment; all loot is redacted (report *that* a secret was recovered and its blast radius, never the contents — nothing sensitive committed under `docs/security/`).

**Two spines, CVSS + ATT&CK Enterprise.** Offensive findings are scored **CVSS** and mapped to the **MITRE ATT&CK Enterprise** matrix — the deliberate, documented divergence from the library's blocker/major/minor/nit table (stated once in `pentest-reporting`). Every offensive act is written to the engagement **action log** as it runs; every planted artifact is enumerated and confirmed removed in the **cleanup-verification** section.

**Target / engagement (optional):**

$ARGUMENTS

If nothing was given above, ask for the engagement id / scope-file path (or offer to help author the scope file) before Phase 0 — the agent needs a committed, in-scope, authorized target and will not act without one.

When done, report the agent's output contract (mode · engagement id · confirmed scope + authorization · chain result · report path · findings by CVSS band · ATT&CK techniques exercised · loot recovered (redacted) · cleanup confirmed · action-log completeness) and the path to the saved report.
