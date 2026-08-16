# Security expansion — staged plan of action

**Date:** 2026-08-16
**Goal:** grow the library's security domain from a **defensive vulnerability-discovery** toolkit into a **full-spectrum security capability** — infrastructure-security testing (the cloud-native infra-tester role), a **live full-kill-chain penetration-testing lane** that proves our guardrails actually stop attacks, and the defensive/governance half a CISO-altitude program needs — without losing the authorization discipline and OWASP spine that make the current lane trustworthy.
**Status:** proposed. Nothing built yet. This document sequences the work; each stage ships independently and is separately approvable.
**Scope:** new lanes across `qa/` (extend `qa-security`), `devops/` (extend), and a new top-level `security/` offensive domain — fronted by a **`security-test-planner`** orchestration agent (§2a) that, given a platform, emits a phased assessment plan whose phases are independently executable. **Out of scope of this plan:** LLM red-teaming (already shipped in `qa-llm-*`), and the `react-native`/`cognito-*` under-construction folders.
**Decision taken with the user (2026-08-16):** the pen-testing lane goes **full kill chain** (recon → exploitation → privilege escalation → lateral movement → post-exploitation), authorization-gated — not validation-only.

---

## 1. Where we are today (grounded in a full survey of the repo)

The `qa-security` agent + `qa/_shared/security-testing/` are a **mature, honestly-fenced defensive lane** with a strong OWASP spine:

| Have | Skill | Tool |
|---|---|---|
| SAST | `code-scan` | Opengrep / Semgrep |
| Secrets | `secrets-scan` | Gitleaks + TruffleHog |
| SCA (per-stack) | `dependency-scan` | npm audit · OWASP DC · `dotnet list --vulnerable` |
| DAST | `active-scan` · `passive-scan` | ZAP (Automation Framework + baseline) |
| API fuzzing | `api-fuzzing` | Schemathesis |
| Image + IaC scan | `image-infra-scan` | Trivy (+ SBOM) |
| TLS | `certificate-scan` | sslyze + testssl.sh |
| Known-CVE match | `known-vuln-scan` | Nuclei |
| **Functional authz** | `permission-testing` (×3 stacks) | BOLA/IDOR/BFLA matrix |
| LLM red-team | `ai-feature-testing/references/red-teaming.md` | promptfoo / DeepTeam |

**The ceiling is "detect-and-report."** There is **no capability that actively exploits anything and no live penetration testing.** sqlmap is named four times, only ever to be *excluded*. Missing entirely: recon/attack-surface enumeration, exploitation & proof-of-exploit, privilege-escalation chaining, lateral movement, post-exploitation, credential attacks, and the whole blue-team/detection half. Every offensive act is deferred to "a human pentest."

**Against the infra-security-tester role** (the JD the user shared — cloud/K8s/container/IaC/CI-CD/IAM/secrets/encryption/monitoring), infra coverage today is essentially *Trivy IaC scanning* + the read-only `devops-auditor`. Missing: kube-bench, Kubescape, Polaris, kube-hunter, Checkov, tfsec, Terrascan, Prowler, ScoutSuite, Falco, and any RBAC/network-policy/runtime validation.

### 1a. Two live bugs found during the survey (fold into Stage 0) — **both confirmed 2026-08-16**

1. **Broken scanner paths.** `qa-security.md` references the scanners as `sast` and `nuclei` (confirmed at **lines 23, 93, 95**), and `qa/_shared/security/SKILL.md` does the same. The folders on disk are **`code-scan`** and **`known-vuln-scan`**. By the agent's own "report missing on disk and fall back" rule, it flags **two of its six shared scanners missing on every run.**
2. **Mis-routed frontmatter.** `qa/typescript/.../dependency-scan` and `qa/java/.../dependency-scan` frontmatter say "prefer the phased agent `qa-performance-*`" — should be `qa-security` (confirmed; both files carry the `qa-performance-*` line). (.NET's is correct.)

---

## 2. Design principles carried into every new lane

Non-negotiable, inherited from the existing lane so the new capability is trustworthy:

1. **Authorization-first, and it is `#volatile`.** No offensive act without a recorded, per-run, target-scoped authorization line that *expires* — never cached as durable. Every offensive report carries `Authorization: <target scope + who authorized + expiry>`. This is the load-bearing control for the full-kill-chain lane (see §5).
2. **Owned/throwaway targets only.** Never a third party's infra. Full-kill-chain skills add an explicit **scope file** (in-scope CIDRs/hosts/accounts, hard exclusions, blast-radius cap, rules of engagement).
3. **One tool family = one skill routing to `references/<tool>.md`** — the library's anti-triplication rule. Most offensive/infra tools are Docker/CLI binaries, so they are **language-agnostic single skills**, not stack-triplicated (mirrors why `active-scan`/`nuclei` aren't triplicated).
4. **Two spines, stated per finding.** Defensive/vuln findings map to **OWASP** (Top 10:2025, API Top 10:2023, WSTG, ASVS). Offensive/detection findings map to **MITRE ATT&CK** (technique IDs) — the language purple-teaming and detection validation share.
5. **Green ≠ safe; every report names its handoff.** Preserve the existing rule that a report states OWASP/ATT&CK coverage and what was left to a human.
6. **Read-only auditors stay read-only.** Posture/audit skills touch only their report; exploitation skills are the only ones that send payloads, and only under §5's gates.
7. **The right ATT&CK matrix per lane.** Enterprise for host/app kill chain; **Cloud** and **Containers** matrices for the infra lane (Stage 1) — the offensive spine is ATT&CK, but the *matrix* is keyed to the surface, so an infra finding maps to Cloud/Containers technique IDs, not the enterprise set.
8. **Loot never lands in the repo.** Any skill that harvests credentials, tokens, or PII (Stage 2/3 credential + post-exploitation) redacts by default — reports reference *that a secret was recovered and its blast radius*, never the secret's contents. Harvested data is handled per the scope file's data-handling rules and never committed under `docs/security/`.

**Bookkeeping every stage closes with (library convention, easy to forget).** A new plugin or command is not "done" until: (a) `.claude-plugin/marketplace.json` registers the plugin; (b) the root `CLAUDE.md` catalog gains the domain paragraph + updates the **command count** and scope fence; (c) the new plugin bundles the two always-on skills **`ep-agent-orientation-cache`** + **`ep-code-comments`** (all plugins carry both, no exceptions), and any code-writing skill loads `ep-code-comments`. Each stage's deliverable list below ends with this closeout.

---

## 2a. The orchestration layer — `security-test-planner` *(owner request, 2026-08-16)*

Because a full security assessment spans many lanes (infra posture, exploit validation, kill chain, purple-team, mobile, client-side, governance), the owner wants **one planner agent that, given a platform, produces a phased assessment plan whose phases are independently executable.** This is the security counterpart to the existing **`be-planner`** — same pattern, same discipline, security-specific rule set — and it is the **entry point to the whole domain**: a human (or Mission Control) points it at a system, it emits the plan, then each phase is dispatched to the lane agent that owns it.

**Home:** the new `security/` domain (`security/agents/security-test-planner.md` — **first draft written 2026-08-16**), bundled into the `penetration-testing` plugin (and cross-listed wherever the lanes live). **Command:** `/security-test-planner`. **Writes plans, never executes** — its write reach is `docs/security/assessments/<NNN>-<platform>/**`; `Bash` is read-only recon. This keeps the planner clean of the §5 offensive gates (it never sends a payload) while every *task* it emits carries the authorization requirement its executor will enforce.

> **Status: SHIPPED (Stage 1.5, applied 2026-08-16).** The agent (`security/agents/security-test-planner.md`) gracefully degrades — routes to lane agents by exact name, marks any not-yet-built executor `not yet available`. Its routing catalog was verified against Stage 1: it names `infra-security-tester` + its exact seven skills, all now built. **Command** `security/commands/security-test-planner.md` (`/security-test-planner`) authored. **Interim home = `devops` plugin** (registered in marketplace agents+commands; version bumped 2.19.0 → **2.20.0**), chosen because `infra-security-tester` — its only currently-built executor — lives there; **it relocates to the `penetration-testing` plugin when the `security/` domain ships at Stage 3.** Root `CLAUDE.md` gained the planner paragraph, the devops agents-row entry (flagged interim), and the command count (74 → **75**). Loads the two always-on `ep-*` skills devops already bundles; loads no domain skills of its own. Nothing in the agent needed editing — its runtime build-status handling was already correct.

**Input = a platform.** Four entry shapes (mirroring `be-planner`'s modes): a **repo/codebase**, a **running system/URL**, a **cloud account/cluster**, or a **loose description** ("assess our payments service"). Phase 0 discovery classifies which.

**Phases (of the planner's own run):**
- **0 Discover & orient** — read-only surface mapping: stack + version lane, cloud/K8s/IaC/CI present, exposed entry points, data sensitivity, existing security wiring (which of the library's scanners/gates already run). Reuses `ep-agent-orientation-cache` (`#volatile` for anything live).
- **1 Scope & authorization blueprint *(blocking gate)*** — present the assessment blueprint: which lanes apply to *this* platform, the proposed phase set, and the **authorization + scope requirements per offensive phase**, then **block** on owner sign-off. Nothing offensive is planned against an unapproved scope. Open questions get 2–4 concrete options each (be-planner's gate discipline).
- **2 Phase decomposition** — turn the applicable lanes into an ordered phase list. Each phase is **defended as independently executable** in one concrete sentence, or explicitly marked as dependent (e.g. kill-chain exploitation depends on exploit-validation feedstock). Phases that share no data run in parallel.
- **3 Executor binding** — every phase names its **exact executor agent + the skills it loads**, from the library catalog: `infra-security-tester` (Stage 1) · `qa-security` + its scanners (Stage 2 / mobile) · `penetration-tester` (Stage 3) · `purple-team-engineer` (Stage 4) · `security-architect` (Stage 5 roll-up). An invented agent/skill name is the single most damaging defect — a self-review phase verifies every name resolves (same rule be-planner enforces).
- **4 Emit the assessment plan** — one artifact per platform under `docs/security/assessments/`, in the **Mission Control vocabulary** (run-level `streams[]`, per-task `id · phaseId · streamId · order · title · intent · acceptanceCriteria[] · agent · skills[] · dependsOn[]`, per-phase `parallelSafe` + `parallelRationale`) so the plan pastes straight into MC and fans out. Plus a plain-language companion (`-explained.md`) for the non-technical approver, per the library's `plain-language-companion` convention.
- **5 Self-review** — lane-coverage (did we skip a surface the platform has), executor-name resolution, dependency sanity, authorization-completeness (every offensive phase carries its scope+expiry requirement), question closure.

**The independence contract is the deliverable's point.** Each emitted phase is either (a) genuinely standalone — runnable now, in any order, against the platform — or (b) carries an explicit `dependsOn`. The planner's job is to maximize (a): a platform with a K8s cluster + a public API + a mobile app yields infra-posture, API-exploit-validation, and mobile-security phases that share nothing and run concurrently, while the kill-chain phase is sequenced after exploit-validation because it consumes its output.

**Fences.** vs `be-planner` — that plans *build* work; this plans *assessment* work, and its tasks bind to security lane agents, not `be-*`. vs the lane agents themselves — the planner routes and sequences; it never scans, exploits, or reports findings (the lanes do). vs `security-architect` (Stage 5) — the planner runs **before** the work to sequence it; the architect runs **after** to roll findings into a posture picture. Two ends of the same program.

**Placement in the roadmap:** author it **early — right after Stage 1** — so it can route to the lanes as they land (it references lane agents by name and degrades gracefully when one isn't built yet, reporting the phase as "executor not yet available" rather than inventing it). Effort ~L. **Depends on:** Stage 0 (needs the catalog clean) + at least Stage 1 existing to route to.

---

## 3. The staged roadmap

Ordered by value + risk: infra-security first (concrete JD, lowest risk, extends `devops`), then sharpen existing gates, then the offensive kill chain, then prove-the-guardrails, then the governance half.

### Stage 0 — Fix & clean the existing lane *(small; do first, unblocks everything)* — **APPLIED 2026-08-16**
- ✅ Fixed the `sast`→`code-scan` / `nuclei`→`known-vuln-scan` skill-path references in `qa-security.md` (lines 23, 93, 95) and `qa/_shared/security/SKILL.md` (lines 123, 129, 213). The uppercase `SAST` concept and `Nuclei` tool-name prose (SKILL.md:186) were deliberately left — they are not loadable paths.
- ✅ Fixed the two `dependency-scan` frontmatter mis-routes (`qa/typescript` + `qa/java`: `qa-performance-*` → `qa-security`).
- ✅ Reconciled the `qa-security` persona: kept the "penetration-testing / application-security QA engineer" label, added a **scope-boundary paragraph** stating this agent detects-and-reports while live offensive execution lives in the `penetration-testing` plugin, with a hand-off under that plugin's gates.
- **Correction to the earlier claim:** `qa-security` Phase 1 does *not* reference a missing `threat-modeling` skill path — it builds the threat model inline from `qa/_shared/security` + `qa/manual/test-strategy` + `exploratory-charter-writer`. So this is **not** a dangling-path bug; it is a **forward-wire**: when `threat-modeling` lands in Stage 1, hook it into Phase 1 as the dedicated skill. No Stage-0 code change was needed for it.
- **Deliverable (met):** the agent no longer self-reports two missing scanners, and its routing/persona are consistent. No new plugin surface; no marketplace/catalog change.

### Stage 1 — Infrastructure-security testing lane *(matches the JD)* — **APPLIED 2026-08-16**
- ✅ **7 skills authored** (all language-agnostic, `references/<tool>.md` per family): `devops/threat-modeling` (SKILL + `stride.md` + `attack-trees.md`) · `devops/iac-security` (SKILL + `checkov.md` + `opa-conftest.md` + `other-scanners.md`) · `devops/k8s-security` (SKILL + `kube-bench.md` + `kubescape.md` + `polaris.md`) · `devops/container-runtime-security` (SKILL + `kube-hunter.md` + `falco.md`) · `devops/cloud-posture` (SKILL + `aws.md`/`azure.md`/`gcp.md`) · `devops/supply-chain-security` (SKILL + `cosign-sigstore.md` + `slsa-provenance.md` + `dependency-integrity.md`) · `devops/infra-controls-validation` (SKILL + `secrets-and-encryption.md` + `monitoring-and-pipeline.md`).
- ✅ **Agent** `devops/agents/infra-security-tester.md` (7 phases: 0 Discover & threat-model → 1 Confirm scope & authorization gate → 2 IaC & image posture → 3 K8s & runtime → 4 Cloud posture & IAM → 5 Controls validation & retest → 6 Findings + remediation handshake). Read-heavy, retest-capable, never fixes; two spines (CIS/OWASP · ATT&CK Containers/Cloud); the §5 authorization model is the load-bearing gate (static posture runs free; live probes need a `#volatile`, owned-target, expiring authorization line; `kube-hunter --active` and production each a separate louder sign-off).
- ✅ **Command** `/infra-security-tester` (`devops/commands/infra-security-tester.md`).
- ✅ **Closeout (§2 bookkeeping):** marketplace.json registers all 7 skills + the command + the agent under `devops` (version bumped 2.18.0 → **2.19.0**); root `CLAUDE.md` gained the infra-security lane paragraph, the agents-header/table/setup-line updates, and the command count (73 → **74**). The always-on `ep-agent-orientation-cache` + `ep-code-comments` were already bundled in `devops`; the agent loads both.
- **Notes for the record:** research reshaped two tool families — **tfsec is EOL** (merged into Trivy) and **Terrascan was archived (Tenable, Nov 2025)**, so `iac-security` centers on **Checkov + OPA/Conftest** (KICS as scoped fallback); **kube-hunter is archived** by Aqua but kept as the reference active-probing tool (Tetragon/KubeArmor named as enforcement successors). Fences drawn crisply against `qa-security-image-infra-scan` (Trivy = CVE/SBOM/static IaC; Stage 1 = benchmark scoring, policy-as-code, runtime probing, integrity/attestation) and `devops-auditor` (static conformance vs live benchmark/probe). Four reference deep-dives (k8s `polaris`, all 3 supply-chain, both controls-validation) + the `threat-modeling` SKILL.md were authored inline after subagent runs were interrupted by a network drop then the account spend limit; all verified for reference-integrity and packaging.

**Home:** extend `devops/` (the infra domain already there) with a new offensive-leaning sibling to `devops-auditor`.
**New skills** (language-agnostic, `references/<tool>.md` per family):
| Skill | Family / tools | Covers |
|---|---|---|
| `k8s-security` | kube-bench (CIS) · Kubescape (NSA/CISA, MITRE, CIS) · Polaris · kube-score · Trivy-K8s | Workload isolation, RBAC, network policies, pod security, admission |
| `iac-security` | Checkov · tfsec · Terrascan · KICS · OPA/Conftest | Terraform/Bicep/ARM/Helm/K8s-manifest misconfig |
| `cloud-posture` | Prowler · ScoutSuite (+ `references/` notes on Wiz/Prisma/Defender as commercial) | CSPM: IAM, exposed storage, encryption-at-rest, logging enabled. **All three clouds; author order AWS → Azure → GCP** (§8.3), one `references/<provider>.md` each |
| `container-runtime-security` | kube-hunter · Falco · Trivy runtime | Runtime threat detection, escape/exposure probing |
| `supply-chain-security` | cosign/sigstore · SLSA provenance · dependency-confusion/typosquat checks · build-integrity | OWASP A08 — artifact signing, provenance, build-pipeline integrity (§7.2; sits beside `iac-security`) |
| `threat-modeling` | STRIDE · attack-trees · data-flow diagrams | Pulled forward from Stage 5 (§8.6) — closes the live `qa-security` Phase-1 dangling reference. Feeds every downstream lane's scope |
| `infra-controls-validation` | scripted checks | Secrets management, encryption-in-transit, monitoring/telemetry controls present + effective, CI/CD pipeline hardening |
**New agent:** `devops/agents/infra-security-tester.md` — phased (0 Discover cluster/cloud/IaC/CI + version lane → 1 Confirm scope & authorization gate → 2 IaC & image posture → 3 K8s & runtime → 4 Cloud posture & IAM → 5 Controls validation & retest → 6 Evidence-based findings + remediation). Loads only the Stage-1 skills + `ep-*`. **Read-heavy, retest-capable** (the JD's "retest remediated findings").
**Command:** `/infra-security-tester`. **Marketplace:** into `devops` (bundle `ep-agent-orientation-cache` + `ep-code-comments` per the §2 closeout).

**Fence against `devops-auditor` (must be drawn — real overlap).** `devops-auditor` already owns twelve read-only conformance sections including container image (B), K8s workloads (C), IaC (D), identity & credentials (G); `image-infra-scan` already runs Trivy. Stage 1's kube-bench/Checkov/tfsec/Trivy-K8s re-touch that ground. The split: **`devops-auditor` = static conformance against the plugin's own rules; `infra-security-tester` = active/benchmark posture testing** — CIS scoring (kube-bench/Kubescape), runtime probing (kube-hunter/Falco), and RBAC/network-policy *validation* that proves isolation holds, not just that a manifest field is set. Where a finding is pure static IaC misconfig, it stays with `devops-auditor`; where it requires running a benchmark or probing a live cluster, it's Stage 1.

**Remediation handshake.** Like every auditor↔engineer pair in the library: `infra-security-tester` finds and retests; **`devops-engineer` applies the fix.** "Retest-capable" means re-run after the engineer remediates — the tester does not edit infrastructure. **Peers named (not loaded):** `devops-engineer` (fixes), `devops-auditor` (static sibling), `qa-security` (app-layer), `data-architect` (owns the cross-tenant leak test), `observability-engineer-*` (whether monitoring controls are actually wired).

**CI-wiring owner.** Infra scans that gate a build run in the **deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), not the `qa/cicd/*` test lane — same fence the library already draws. State which in the agent so the gate lands unambiguously.
**Depends on:** Stage 0.

### Stage 2 — Exploit-validation & reachability layer *(sharpen what we already detect)* — **APPLIED 2026-08-16**
**Home:** extended `qa-security` (no new plugin) — 3 `_shared` skills bundled into all three `qa-*` plugins.
- ✅ **3 skills authored** (all language-agnostic, `references/<family>.md` per skill, pinned to fresh 2026-08 research):
  - `qa/_shared/security-testing/exploit-validation` (SKILL + `references/{sqlmap,scripted-dast,exploit-playbooks}.md`) — sqlmap 1.10.8 (finally a skill, not just an exclusion) · scripted Burp REST/Montoya + ZAP 2.17.0 Automation Framework · per-class playbooks (SSRF/SSTI/insecure-deserialization/XXE/path-traversal) with self-hosted interactsh v1.3.1 OOB, SSTImap v1.3, ysoserial.net v1.36. Output = **proof-of-exploit + blast radius** (redacted), both spines OWASP/WSTG + ATT&CK. The `#volatile` authorization line is the load-bearing gate; **never a CI gate**.
  - `qa/_shared/security-testing/vuln-reachability` (SKILL + `references/{epss-kev,vex-reachability,enrichment-gate}.md`) — EPSS **v5** (`model_version v2026.06.15`) + **CISA KEV** (BOD 26-04, not the revoked 22-01) + **OpenVEX** reachability + CISA Vulnrichment SSVC. Read-only post-processing of existing SCA/SAST output (join on CVE id, no re-scan), **safe every PR**. Precedence **KEV→VEX→CVSS∧EPSS→TRACK**; the hard rule *never multiply EPSS×CVSS*; a ~60-line enrichment stage proven against live feeds.
  - `qa/_shared/security-testing/client-side-security` (SKILL + `references/{dom-xss,csp-validation,spa-dast}.md`) — Dalfox **v3.2.1** (Rust; no headless engine) + Burp DOM Invader source→sink · Google CSP Evaluator (`csp_evaluator` 1.1.8, no CLI) + MDN HTTP Observatory (1.6.3) + the dynamic `securitypolicyviolation` **block-proof** (parses-clean ≠ blocks) · ZAP **Client Spider** (the AJAX Spider is deprecated) + the Playwright→proxy pattern + Nuclei 3.11.1 headless. The **test half** of the `fe-*` handshake (authoring half = Stage-5 `security-hardening`).
- ✅ **Agent wiring** (`qa/_shared/agents/qa-security.md`): new **Phase 4b** (dynamic exploitation & client-side, authorized-env only, never a per-PR gate) + a **reachability-weighting step inside Phase 2** (`vuln-reachability` de-noises the SCA/SAST output before the gate decision). Skill-loading protocol, authorization rule (extended to exploitation acts + loot-redaction), output contract (both spines + blast-radius + action/cleanup logs on a 4b proof), and the scope-boundary paragraph reconciled (single-vuln proof in-scope; kill chain still out → `penetration-testing`). Peers added: `penetration-testing` (initial-access feedstock), `security-test-planner`, `fe-<stack>`+`security-hardening`.
- ✅ **Closeout (§2 bookkeeping):** marketplace.json registers all 3 skills under `qa-java`/`qa-dotnet`/`qa-typescript` (version bumped 2.20.0 → **2.21.0**); root `CLAUDE.md` gained the Stage-2 exploit-validation & weighting catalog sub-bullet. **No new command** (agent-reached skills per the "code-touching skills have no command" rule → command count stays **75**). All 3 skills already ride the always-on `ep-*` the `qa-*` plugins bundle. All marketplace paths + reference links verified resolving; the one sibling-name reference (`api-fuzzing` → `qa-security-testing-api-fuzzing`) corrected.
- **Notes for the record:** research corrected several premises — EPSS is **v5** (not v4/2025) and generated by Empirical Security; CISA **BOD 26-04** superseded BOD 22-01 (June 2026); **Dalfox v3 dropped its headless browser** (Rust rewrite, AST source→sink only); ZAP's **AJAX Spider is no longer recommended** (→ Client Spider); CSP Evaluator ships **no CLI**; Mozilla Observatory **moved to MDN**. The honest-tooling myth-busters are encoded (Grype consumes VEX but computes no reachability; **Falco/Tetragon are not SCA de-noisers**; Semgrep SC is proprietary + no transitive reachability; Snyk Runtime Sensor archived; Kubescape is the only OSS runtime option).

**Boundary vs Stage 3 (drawn — sqlmap appears in both).** `exploit-validation` = **single-vuln proof-of-exploit + blast radius on one app** (does this detected finding actually fire, and how far does it reach). Stage 3's `initial-access` = **gaining a foothold/session at network altitude** (chaining a validated vuln into access). exploit-validation feeds initial-access; it does not itself pivot or escalate.
**Handshake:** the existing `permission-testing` (BOLA/IDOR/BFLA matrix, ×3 stacks) is the functional-authz feedstock for exploit-validation — an IDOR the matrix finds is a validated-vuln candidate, named as a peer.
**Depends on:** Stage 0. Independent of Stage 1.

### Stage 3 — Full offensive kill chain *(the "live pen testing" ask)* — **APPLIED 2026-08-16**

> **§5 rules-of-engagement model: SIGNED OFF by the owner 2026-08-16** — the load-bearing gate is approved; the offensive skills were authored against it, not ahead of it. Detailed build log in `docs/plans/STAGE3-PROGRESS.md`. **All authoring, packaging, relocation, catalog updates, and path/link verification are complete; only the git commit + merge to `master` remain** (a delivery step — Claude's real-time cyber safeguards blocked `Bash` git operations for the authoring session, so the commit runs from a fresh session or by the owner).

**DONE so far:**
- ✅ **New agent** `security/agents/penetration-tester.md` — the red-team orchestrator, phased strictly (0 Rules-of-engagement & scope file *(blocking gate)* → 1 Recon → 2 Exploitation → 3 Priv-esc → 4 Lateral movement → 5 Post-exploitation *(capped at proof)* → 6 Report + cleanup verification); the full §5 safety model built in (committed scope file `docs/security/engagement-<NNN>.md`, `#volatile` authorization, per-act destructive opt-in, cleanup verification, owned-infra-only, production second gate, loot redaction, full action log, defined mid-run abort — rule 9); two spines (ATT&CK **Enterprise** + CVSS); loads only the Stage-3 skills + always-on `ep-*`; fences drawn vs `qa-security` (single-vuln-proof feedstock), `infra-security-tester` (posture/Cloud-Containers), `security-test-planner` (routes, doesn't exploit); routing vocabulary matches what `security-test-planner` already references.
- ✅ **All 7 skills authored** (language-agnostic, `security/<skill>/SKILL.md`, frontmatter prefix `pentest-*`, each opening with the §5 authorization + scope-file gate, ATT&CK Enterprise, anti-patterns, hard-rules, cross-refs — self-contained inline tool content, no `references/` split, mirroring `image-infra-scan`'s single-file shape so there are no dangling links): `recon-enumeration` · `initial-access` · `privilege-escalation` · `lateral-movement` · `credential-attacks` · `post-exploitation` · `pentest-reporting`.
- ✅ **Research pinned to fresh 2026-08-16 sources**, folded into the skills: amass **v5.1.1** (past v4 — v5 asset-db; v3→v4 removed `viz`/`db`) · subfinder **v2.15.0** · httpx **v1.10.0** (ProjectDiscovery — Python-lib name-collision flagged) · masscan **1.3.2** · nmap (pin from `nmap.org/changelog`) · sqlmap **1.10.7** · Metasploit (rolling — pin the image/package) · PEASS-ng **20260801** · GTFOBins/LOLBAS (reference sites) · **NetExec (nxc) v1.5.1 — CrackMapExec is dead/renamed** · impacket **0.13.1** · **BloodHound CE v9.5.1 — legacy 4.x superseded**, SharpHound **v2.14.0** (still C#, no official Rust rewrite), AzureHound **v3.0.0** · ligolo-ng **v0.9.1** · chisel **v1.11.8** · sshuttle **v1.3.2** · peirates **v1.1.28** · hashcat **7.1.2** (v7 rewrite; 6.2.x superseded) · hydra **v9.7** · Responder **v3.2.2.0** (`-A` passive default) · mimikatz **2.2.0-20220919** (stale, flagged) · LaZagne **v2.4.7** · Sliver **v1.7.3** · **Mythic v3.4.0.5 — canonical repo `its-a-feature/Mythic`** (the plan's `its0reo` 404s). Dual-use lead framing designed into `credential-attacks` + `post-exploitation` (+ credential dumping); persistence demo-then-remove-then-log; C2 authorized-env-only; no DoS; the CVSS+ATT&CK-vs-severity-table divergence stated **once** in `pentest-reporting`.

**CLOSEOUT — COMPLETE (§2 bookkeeping + §2a/§8.1 relocation):**
- ✅ **Command** `security/commands/penetration-tester.md` (`/penetration-tester`), modelled on `security/commands/security-test-planner.md` — gate-first, scope-file-required, CVSS+ATT&CK, no-fix.
- ✅ **Marketplace** `.claude-plugin/marketplace.json`: new **`penetration-testing`** plugin registered (7 skills + `penetration-tester` + `security-test-planner` agents + `/penetration-tester` + `/security-test-planner` commands + the two always-on `ep-agent-orientation-cache` + `ep-code-comments`); **version bumped 2.21.0 → 2.22.0**; JSON validated well-formed.
- ✅ **Relocated `security-test-planner`** out of its interim `devops` home into `penetration-testing` (§2a / §8.1): its agent + command registration moved between the two plugin blocks; the stale line in `security/commands/security-test-planner.md` corrected (Stage-2 skills + `penetration-tester` + its seven skills now marked built/available; only `purple-team-engineer`/`security-architect` remain `not yet available`).
- ✅ **Root `CLAUDE.md`**: new top-level **`## Security catalog`** section added (domain intro, §5 safety model, the 7 skills, the `penetration-tester` agent phases, the planner now homed here, fences vs `qa-security`/`infra-security-tester`/`exploit-validation`, new-project setup); `penetration-testing` added to the published-plugins list; the `devops` published-list entry refreshed to include its Stage-1 infra-security skills + `infra-security-tester`; command count **75 → 76**; the always-on `ep-*` "all eleven" → "all twelve" (×3); the slash-command table gained a `penetration-testing` row and lost the planner's interim-home devops entry; the planner catalog paragraph's interim-home flag removed.
- ✅ **Verified** all new marketplace paths resolve (7 SKILL.md + 2 agents + 2 commands + the 2 pre-existing `ep-*`) and the JSON closes correctly; skills are self-contained (no `references/` split → no dangling links). **Environment note:** Claude's real-time cyber safeguards flagged the offensive context mid-session and blocked `Bash`/`WebFetch` (Write + read-only tools unaffected — all authoring/edits/verification completed); the git **commit + merge to `master`** is the one remaining step, to be run from a fresh session or by the owner (commands below in `docs/plans/STAGE3-PROGRESS.md`).

**Home:** **new top-level `security/` domain**, shipped as a new **`penetration-testing`** plugin (offensive execution is heavy enough — authorization machinery, scope files, ATT&CK mapping — that it wants its own plugin and its own hard fences, not a fold into QA).
**New skills** (language-agnostic; each opens with the §5 authorization + scope gate):
| Skill | Kill-chain stage | Tools / techniques |
|---|---|---|
| `recon-enumeration` | Recon / attack-surface | amass · subfinder · nmap · masscan · httpx · Shodan/Censys reads |
| `initial-access` | Exploitation | Metasploit · sqlmap · custom exploit, from Stage-2 validated vulns |
| `privilege-escalation` | Post-exploit | linPEAS/winPEAS · GTFOBins · kernel/sudo/SUID chains |
| `lateral-movement` | Post-exploit | credential reuse · pivoting · BloodHound (AD) · SSH/kube pivots |
| `credential-attacks` | Access | hashcat · hydra · responder · secrets harvesting |
| `post-exploitation` | Impact | data-access proof · persistence demo (removed) · C2 (Sliver/Mythic) |
| `pentest-reporting` | Report | executive + technical, CVSS + ATT&CK, remediation, proof, cleanup log |
**New agent:** `security/agents/penetration-tester.md` — the red-team orchestrator. Phased strictly: **0 Rules-of-engagement & scope file (blocking gate) → 1 Recon → 2 Exploitation → 3 Priv-esc → 4 Lateral movement → 5 Post-exploitation (capped at proof) → 6 Report + cleanup verification.** Each phase re-checks the scope file and cannot act outside it.
**Command:** `/penetration-tester`. **Marketplace:** new `penetration-testing` plugin entry + new top-level `security/` domain paragraph in root `CLAUDE.md` + command-count bump + bundle the two always-on `ep-*` skills (§2 closeout).

**Authoring-framing note (practical).** `credential-attacks` (hashcat/responder/secrets harvesting), `post-exploitation` (C2 via Sliver/Mythic, persistence demo), and credential dumping sit on the dual-use line. Each skill leads with the same authorized-lab-only + defensive-intent framing the current lane already uses, so the framing is designed in, not bolted on — otherwise these skills may hit authoring-time refusals. Persistence is *demonstrated then removed and logged*; C2 never reaches beyond the authorized env; no DoS, ever.
**Reporting-format divergence (state it deliberately).** Offensive reports use **CVSS + ATT&CK**, not the library's blocker/major/minor/nit severity table. This is a legitimate divergence — document it once in the skill the way `be-java` documents its JUnit-vs-TestNG deviation, so it reads as a decision, not drift.
**Depends on:** Stage 2 (validated vulns are the exploitation feedstock). **This is the highest-risk stage — see §5.**

### Stage 4 — Purple-team continuous validation *(prove the guardrails fire)*
**Home:** `security/` domain (pairs with Stage 3).
**New skills:**
- `atomic-simulation` — Atomic Red Team + Caldera: run individual MITRE ATT&CK techniques and *scenario chains* against an authorized env on a schedule to prove detections still fire (catches "security drift").
- `detection-validation` — the blue half of purple: for each simulated technique, assert the guardrail/SIEM/alert **actually triggered** (query the log/alert store, gate on detected-yes/no per ATT&CK ID). This is the direct answer to "make sure our guardrails are working."
**Agent:** extend the `penetration-tester` agent with a purple-team mode, **or** a dedicated `security/agents/purple-team-engineer.md` (recommend the latter — different cadence, different audience, pairs red simulation with blue assertion).
**Command:** `/purple-team-engineer`.
**Hard dependency on the observability domain (added from evaluation).** `detection-validation` "queries the log/alert store" — that store *is* the Loki/Prometheus/Tempo stack the `observability/` domain owns. This is a real prerequisite, not a nice-to-have: **a target with no SIEM/observability cannot assert a detection fired.** Name `observability-engineer-*` + the `queries`/`dashboards` skills as peers, and gate the assertion phase on a telemetry backend being present (report "no detection surface to assert against" honestly rather than passing silently).
**Depends on:** Stage 3 (shares ATT&CK mapping + authorization machinery) **and a live telemetry backend** for the blue half.

### Stage 5 — Defensive / governance half *(CISO-altitude, "increasing threat")*
**Home:** split between `qa-security` (technical) and a possible new `security/` governance skills.
*(`threat-modeling` moved to Stage 1 per §8.6 — it closed a live dangling reference and no longer waits for the governance stage.)*
**New skills:**
- `detection-engineering` — author + test detections (Sigma rules, alert-as-code), the standing counterpart to Stage 4's validation.
- `secrets-hardening` — rotation runbooks, secret-store wiring, the defensive complement to `secrets-scan`.
- `security-hardening` — CSP authoring, security headers-as-code, WAF rules — turn A05 findings into fixes. **Its authored CSP is the counterpart to the client-side CSP *validation* added to Stage 2 (§7.3)** — author here, test there.
- `compliance-evidence-mapping` — map controls/tests to SOC 2 / PCI / GDPR / ISO 27001 evidence (ASVS levels are already invoked but never mapped to a framework).
**Agent → confirmed (§8.5):** `security/agents/security-architect.md` — a governance-altitude agent that consumes findings from all lanes (infra / exploit / pentest / purple / defensive) and produces one risk/posture picture for the CISO "increasing threat" framing. **Command:** `/security-architect`. **Depends on:** nothing hard; can interleave with Stages 1–4, but the roll-up is most useful once ≥2 lanes emit findings.

---

## 4. Packaging decisions (recommended, open to change)

| Question | Recommendation | Why |
|---|---|---|
| Where does infra-security live? | Extend **`devops`** plugin | Cluster/cloud/IaC/CI is already the devops domain; `infra-security-tester` is the offensive sibling of `devops-auditor`. |
| Where does the kill chain live? | **New `security/` domain + `penetration-testing` plugin** | Offensive execution needs its own hard fences, scope-file machinery, and ATT&CK spine — folding it into `qa-security` would dilute the QA plugin and blur the authorization gate. |
| Stack-triplicate the new skills? | **No** — language-agnostic single skills | Every new tool is a Docker/CLI binary; triplicating a `docker run` is the exact anti-pattern the library already rejects. |
| Reuse the audit-engine? | Infra-security **posture** audits can ride `ep-standards-audit-engine`; offensive lanes do **not** (they produce proof, not conformance findings) | Keep the conformance lane and the offensive lane distinct. |
| A `standards-audit` self-audit for the new plugins? | **Explicit non-goal for now** — state it rather than leave it silent. Every stack plugin carries one; the security/pentest plugins defer it until the rule set stabilizes. | Avoid authoring conformance rules for lanes still being designed. |
| Bundle the always-on `ep-*`? | **Yes, mandatory** — every new plugin ships `ep-agent-orientation-cache` + `ep-code-comments`; code-writing skills load the latter. | Library-wide invariant (all plugins carry both). |

---

## 5. The full-kill-chain safety model (Stage 3–4 gate — the load-bearing part)

Because the user chose full kill chain, the authorization machinery is not boilerplate — it *is* the design. Every offensive skill and both offensive agents enforce:

1. **A committed scope file** (`docs/security/engagement-<NNN>.md`): in-scope hosts/CIDRs/cloud-accounts, hard exclusions, allowed techniques, blast-radius cap, data-handling rules, start/stop window, named authorizer. The agent **refuses to start** without it and re-reads it before every phase.
2. **`#volatile` authorization** — never cached in the orientation cache; expires with the window; re-confirmed each run. The `ep-agent-orientation-cache` skill already treats live authorization as `#volatile` — extend that here.
3. **Destructive/irreversible acts are opt-in per act**, never default: no data destruction, no persistence left behind (post-exploitation demos persistence then **removes** it and logs the removal), no DoS, no targeting outside scope, no C2 beyond the authorized env.
4. **Cleanup verification is a required report section** — every artifact planted is enumerated and confirmed removed.
5. **Owned-infra-only, restated per skill.** These are authorized self-tests of the user's own systems; the skills refuse third-party targets and say so.
6. **Production is a separate, louder gate than lab (added from evaluation).** "Owned infra" is not enough — a live kill chain pointed at production requires an *explicit second sign-off* distinct from the lab authorization, mirroring the existing `mobile-app-crawler` "test-account-on-non-production" precedent. Default posture: lab/throwaway target only; production is opt-in per engagement with its own recorded authorizer. (This promotes Open Question 4 into a rule.)
7. **Loot never lands in the repo (added from evaluation).** Skills that harvest credentials/tokens/PII redact by default: the report states *that* a secret was recovered and its blast radius, never the contents, and nothing sensitive is committed under `docs/security/`. Handling of collected data follows the scope file's data-handling rules. (This is §2 principle 8, enforced at the skill level.)
8. **A full action log is a required report section (added from evaluation).** Beyond the cleanup log, every offensive run records *what payload/command was sent, against what target, when* — the accountability trail that proves the run stayed in scope and lets the retest reproduce. Cleanup log answers "did we leave anything behind"; the action log answers "what did we do."
9. **Defined mid-run abort (added from evaluation).** Each phase re-reads the scope file; if the next act would fall outside it, the agent **halts the run and reports**, rather than skipping the act and continuing. A live kill chain needs an explicit kill switch, not silent scope-narrowing.

This keeps the lane squarely in authorized-security-testing territory (the legitimate dual-use frame) rather than drifting toward unbounded offensive tooling.

---

## 6. Suggested sequence & rough effort

| Stage | Deliverable | Effort | Gate before starting |
|---|---|---|---|
| 0 | Bug fixes (3) + persona note + threat-model pointer | XS | — |
| 1 | Infra-security lane (**7 skills** — +`supply-chain-security` +`threat-modeling` — + agent + command) | XL | Stage 0 |
| 1.5 | **`security-test-planner`** (planner agent + command, §2a) | L | Stage 0 + Stage 1 (routes to lanes) |
| 2 | Exploit-validation + reachability + client-side dynamic testing (3 skills + agent Phase 4b + Phase-2 weighting) — **APPLIED 2026-08-16** | M | Stage 0 |
| 3 | Full kill chain (7 skills + agent + new `penetration-testing` plugin + `security/` domain) — **APPLIED 2026-08-16** (§5 signed off; agent + 7 skills + `/penetration-tester` + marketplace 2.22.0 + planner relocation + root `CLAUDE.md` Security catalog all done; only the git commit + merge remain) | XL | Stage 2 + §5 sign-off ✅ |
| 4 | Purple-team validation (2 skills + agent) | L | Stage 3 + live telemetry backend |
| 5 | Governance/blue-team (4 skills + **confirmed `security-architect` agent**) | L | — (interleavable) |
| 6 | Mobile app security (MobSF + MASVS/MASTG, ~2 skills + `qa-security` phase) | M | Stage 0 |

**Recommended first build:** Stage 0 then Stage 1 — lowest risk, matches the concrete JD, and immediately useful — while §5's rules-of-engagement model is reviewed before any Stage-3 offensive code is written. Stage 6 (mobile) and Stage 2 are both independent of the offensive stages and can run in parallel with Stage 1 if there's capacity.

**Current position (2026-08-16).** Stages **0, 1, 1.5, 2, and 3 are APPLIED**. Stage 3's authoring, packaging (marketplace 2.22.0), planner relocation, root-`CLAUDE.md` Security catalog, and verification are complete; the **git commit + merge to `master`** is the only remaining step (blocked by the session's cyber-safeguard classifier on `Bash` git — runs from a fresh session or by the owner; commands in `docs/plans/STAGE3-PROGRESS.md`).

**Suggested next sequence** (all independent of the offensive stages, none blocked):
1. **Commit + merge Stage 3** to `master` (the one open delivery step).
2. **Stage 6 — mobile app security** (MobSF + MASVS/MASTG, ~2 skills + a `qa-security` phase) — unblocked, effort ~M.
3. **Stage 5 — governance/blue-team** (`detection-engineering`, `secrets-hardening`, `security-hardening`, `compliance-evidence-mapping` + the confirmed `security-architect` agent) — interleavable, most useful once ≥2 lanes emit findings.
4. **Stage 4 — purple-team continuous validation** (`atomic-simulation` + `detection-validation` + `purple-team-engineer`) — gated on Stage 3 (done) **and** a live telemetry backend for the blue half.

Detailed live tracking in `docs/plans/STAGE3-PROGRESS.md`.

---

## 7. Added coverage lanes (all three in scope per §8 decision 7)

These were flagged as gaps in evaluation and the owner brought all three into the program. Placement:

1. **Mobile app security testing → new Stage 6.** MobSF + mobile SAST/DAST + OWASP MASVS/MASTG. Home: extend `qa-security` (it's app-layer security testing, sibling to the existing scanners), named peer to the `qa-mobile-*` and `mobile-app-crawler` lanes it reuses. Effort ~M. **Depends on:** Stage 0. Independent of the offensive stages.
2. **Software supply-chain security → fold into Stage 1.** Artifact signing (cosign/sigstore), SLSA provenance, dependency-confusion/typosquat detection, build-integrity — the OWASP A08 surface. Sits next to `iac-security` as a new `supply-chain-security` skill in the infra lane (it's build/artifact posture, and the infra agent already owns the CI/CD-hardening story). **Added to Stage 1's skill table below.**
3. **Client-side/frontend security → split across Stage 2 + Stage 5.** Dynamic testing (DOM XSS, CSP *validation*, SPA-specific DAST) joins Stage 2's dynamic lane; CSP/header *authoring* stays in Stage 5 `security-hardening`. Named `fe-*` handshake so the authored CSP and the tested CSP are the two halves of one control.

Explicitly **still out of scope**: LLM red-teaming (shipped in `qa-llm-*`), social-engineering/phishing/physical, and the under-construction `react-native`/`cognito-*` folders.

---

## 8. Decisions resolved (owner sign-off, 2026-08-16)

All seven open questions are now settled. These are load-bearing — the stages above are updated to match.

1. **Plugin split → devops + standalone pentest.** `infra-security-tester` folds into the existing `devops` plugin; the kill chain gets its own new top-level `security/` domain + `penetration-testing` plugin with its own hard fences. (Confirms the plan's working assumption.)
2. **Commercial tools → named as `references/` deep-dives.** OSS is the default runnable path (nothing depends on a paid license to run a lane); Wiz/Prisma Cloud/Prowler Pro/Burp Pro/Defender each get a short `references/<tool>.md` note so a licensed team knows where it fits.
3. **Cloud targets → AWS + Azure + GCP, all three.** `cloud-posture` documents all three providers. **Suggested authoring order: AWS first** (Prowler's strongest coverage), **Azure second** (matches the library's Azure DevOps / Container Apps defaults), **GCP third.** Drives the `references/<provider>.md` layout.
4. **Stage-3 environment → lab-only default, prod opt-in.** The kill-chain agent defaults to a designated throwaway/lab target; production requires the separate louder §5 sign-off per engagement. (Already codified as §5 rule 6.)
5. **CISO reporting → yes, add `security-architect`.** A governance-altitude agent (Stage 5) consumes findings from all lanes and produces one risk/posture picture. Confirmed as a Stage-5 deliverable.
6. **Threat-modeling → pulled forward into Stage 1.** Closes the live dangling reference (`qa-security` Phase 1 requires a threat model with no skill behind it) early rather than waiting for Stage 5. (Stage 1 and Stage 5 updated.)
7. **Deferred coverage → all three join the program.** Mobile app security, supply-chain security, and client-side/frontend security are **in scope**, added as new stages/skills (see §7 for placement). Only LLM red-teaming (shipped) and social-eng/physical remain explicitly out.
