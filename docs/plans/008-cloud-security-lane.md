# 008 — Cloud security lane: offensive cloud pentest + cloud IR/forensics + BCDR — plan (2026-10-21)

**Goal:** Give the `penetration-testing` and `security-governance` plugins full coverage of a cloud
security / cloud-pentest curriculum (AWS · Azure · GCP), so every module of the course that prompted
this has an owning skill or a wired cross-reference. Four new offensive skills (cloud recon, then
AWS/Azure/GCP exploitation), one new defensive skill (cloud incident response + forensics + BCDR
references), and a wiring + cross-reference pass that teaches the existing agents and skills the new
lane exists.

**Status:** Not started. Next: C1 (the shared cloud-recon entry skill the three provider skills bind
to). Built but unverified: nothing yet. No new commands ship — every new skill is agent-reached, so the
catalog's 65-command surface is unchanged; the skill inventory and two plugin descriptions do change.

---

## 1. What already exists, and what is missing

Grounded in a survey of `security/*`, `devops/*`, and the two security plugins' marketplace blocks. Each
row is one course module (or theme) the lane must cover; every task below traces to a row.

| Need (course module) | Today | Gap |
|---|---|---|
| Cloud concepts, service models, shared-responsibility, cloud threats (M1) | `devops/threat-modeling`, `devops/cloud-posture` SKILL intros | Cross-reference only — no new skill (W1, G1) |
| Cloud architecture & infra security (M2) | `devops/aws-deployment`, `devops/azure-deployment`, `devops/cloud-posture` | Cross-reference only (G1) |
| IAM: authn/authz, users/roles/policies, PAM, IAM misconfig (M3) | `cloud-posture` reads IAM as *posture*; no offensive IAM path testing | IAM privesc-path testing lives in the new provider skills (A1–A3) |
| Cloud network & data security: VPC, SGs, storage, encryption, KMS, secrets (M4) | `security/secrets-hardening`, `devops/environment-config`, `cloud-posture` (defensive) | Cross-reference; offensive storage/secret enum in C1 + A1–A3 |
| Intro to cloud pentest: methodology, recon/enum, misconfig attack surface, tooling (M5) | **Nothing.** The seven kill-chain skills are network/host/app-shaped; `recon-enumeration` is DNS/port/web, not cloud-control-plane | **New skill `cloud-recon-enumeration`** (C1) |
| AWS fundamentals: architecture, IAM, networking/storage, best practices (M6) | `aws-deployment` (build, not attack); `cloud-posture` (posture) | Fundamentals ride as context in A1; no standalone skill |
| AWS pentest: recon/enum, IAM testing, EC2/S3/other services, common vulns/misconfigs (M7) | **Nothing offensive** | **New skill `cloud-attack-aws`** (A1) |
| Advanced AWS: privesc, CloudTrail/GuardDuty, RDS testing, Pacu & ScoutSuite (M8) | ScoutSuite named in `cloud-posture` for *posture* only; Pacu named nowhere; `atomic-simulation` names Stratus Red Team (purple detonation, not exploitation) | Folded into A1 (one AWS skill owns fundamentals→advanced) |
| Azure fundamentals + pentest: Entra ID, Key Vault, IAM misconfig, attacking Azure services (M9, M10) | `azure-deployment` (build); `cloud-posture` (posture) | **New skill `cloud-attack-azure`** (A2) |
| GCP security: architecture, IAM, recon/enum, security-testing fundamentals (M11) | `cloud-posture` *reads* GCP; nothing attacks it; no `gcp-deployment` either | **New skill `cloud-attack-gcp`** (A3) |
| Cloud app security & DevSecOps: CI/CD security, SAST/DAST/SCA/IaC (M12) | `qa-*:*-security` scanners, `devops/iac-security`, `supply-chain-security`, the pipeline skills | **Fully covered** — cross-reference only (G1) |
| Cloud SecOps & IR: monitoring/logging, threat detection, cloud IR, cloud forensics (M13) | `security/detection-engineering`, `detection-validation`, `observability` cover detection; **no IR runbook, no cloud forensics** | **New skill `cloud-incident-response`** (B1) |
| Cloud governance, risk & compliance, BCDR, case studies (M14) | `security/compliance-evidence-mapping`, `standards-audit` cover GRC; **BCDR has no home** | BCDR as `references/cloud-resilience.md` under B1 + a crosswalk row in `compliance-evidence-mapping` (G1) |

**The shape of the gap:** the library can already *audit* a live cloud account (`cloud-posture`), *build*
on three clouds, *detonate* cloud ATT&CK techniques for purple-team drift (`atomic-simulation` →
Stratus), and *author/validate* detections. What it cannot do is **actively test a cloud control plane
as an attacker would** (enumerate the metadata service, walk an IAM privesc path, abuse a managed
identity, pivot through a storage misconfig) or **respond to a cloud incident** (triage, acquire a
forensic snapshot, recover). This plan adds exactly those two capabilities and wires them in.

---

## 2. Design principles carried into every new skill

Inherited verbatim from plan `SECURITY-EXPANSION-PLAN` §2, because the new offensive skills are dual-use
and only trustworthy under the same fence:

1. **Authorization-first, `#volatile`.** No offensive act without a recorded, per-run, target-scoped
   authorization line that *expires*. Every cloud-attack report carries
   `Authorization: <account/subscription/project ids + who authorized + expiry>`. Never cached as
   durable. This is the load-bearing control (SECURITY-EXPANSION-PLAN §5).
2. **Owned/lab accounts only.** Never a third party's tenant. The cloud-attack skills add a **cloud
   scope file**: in-scope account ids / subscription ids / project ids, in-scope regions, hard
   exclusions (shared-services accounts, production data stores), a blast-radius cap, and rules of
   engagement. Production is a separate, louder sign-off. The course's practice targets (CloudGoat,
   AzureGoat, GCPGoat, flaws.cloud, IAM Vulnerable) are the reference owned-lab environments.
3. **One tool family = one skill routing to `references/<tool>.md`** — the anti-triplication rule. Cloud
   tools are CLI/Docker binaries, so each skill is **language-agnostic and single**, never
   stack-triplicated.
4. **The ATT&CK matrix is keyed to the surface.** Cloud findings map to the **MITRE ATT&CK Cloud**
   matrix (IaaS · Identity Provider · SaaS), not Enterprise — e.g. `T1552.005` (Cloud Instance Metadata
   API), `T1580` (Cloud Infrastructure Discovery), `T1619` (Cloud Storage Object Discovery), `T1078.004`
   (Valid Accounts: Cloud Accounts), `T1098` (Account Manipulation). The reporting skill
   (`pentest-reporting`) already scores CVSS + ATT&CK; the provider skills name the Cloud-matrix id per
   finding.
5. **Loot never lands in the repo.** A recovered key, token, or secret is reported as *that it was
   recovered and its blast radius*, never its value. Harvested data follows the cloud scope file's
   data-handling rules.
6. **Posture ≠ exploitation; the two lanes hand off.** `cloud-posture` (Prowler/ScoutSuite, defensive,
   read-only) *finds* the misconfiguration; a cloud-attack skill *proves* it is reachable and chains it.
   Each new skill names the handoff in both directions.
7. **No DoS, ever. Destructive acts are per-act opt-in** and demonstrated-then-reverted (persistence
   demo removed; a created IAM principal deleted in cleanup), exactly as `post-exploitation` requires.

**Bookkeeping every plan closes with (library convention, in W1 + G1):** (a)
`.claude-plugin/marketplace.json` registers each new skill under the right plugin; (b) the two plugin
**descriptions** gain the new skills; (c) root `CLAUDE.md` and `docs/skills-catalog.md` gain the lane in
the scope list / skill inventory (command count unchanged — no new commands); (d) each new skill opens
by loading the two always-on `ep-*` skills its plugin already bundles.

---

## 3. The skills this plan adds

> **Research corpus:** every skill below is backed by a web-verified deep-dive in
> [`docs/research/cloud-security/`](../research/cloud-security/) (one file per course module group, index
> + currency ledger in its `README.md`). Each task's prompt cites its file; authors lift facts from it
> rather than re-deriving them.

### 3.1 Offensive — `penetration-testing` plugin (runtime agent: `penetration-tester`)

| Skill | Owns | Key references (`references/<tool>.md`) |
|---|---|---|
| `cloud-recon-enumeration` (C1) | Cloud pentest **methodology** + provider-agnostic recon: anonymous/authenticated enumeration, public storage discovery, the instance **metadata service** (IMDSv1/v2, `169.254.169.254`), OIDC/federation and role enumeration, principal/permission enumeration. The entry skill the three provider skills bind to | `scoutsuite.md` (multi-cloud audit as recon), `cloud-enum.md` (cross-cloud public-asset discovery), `metadata-service.md` (SSRF→creds), `enumerate-iam.md` |
| `cloud-attack-aws` (A1) | AWS fundamentals-as-context → exploitation: IAM privilege-escalation paths, EC2 (metadata, user-data, snapshots), S3 abuse, RDS testing, CloudTrail/GuardDuty awareness | `pacu.md` (AWS exploitation framework), `cloudfox.md` (situational awareness), `pmapper.md` (IAM privesc paths), `s3-attacks.md` |
| `cloud-attack-azure` (A2) | Entra ID (formerly Azure AD) enumeration & abuse, managed-identity abuse, Key Vault access testing, Azure RBAC misconfig, attacking Azure services | `roadtools.md` (ROADrecon Entra enum), `azurehound.md` (BloodHound for Azure), `microburst.md`, `azure-keyvault.md` |
| `cloud-attack-gcp` (A3) | GCP IAM enumeration, service-account impersonation/key abuse, storage-bucket attacks, GCP recon/testing fundamentals | `gcp-enum.md` (gcp_scanner / enumeration), `gcp-privesc.md` (service-account impersonation chains), `gcp-bucket-brute.md` |

### 3.2 Defensive — `security-governance` plugin (runtime agent: `security-architect`)

| Skill | Owns | Key references |
|---|---|---|
| `cloud-incident-response` (B1) | Cloud **IR runbook** (detect → triage → contain → eradicate → recover) keyed to AWS/Azure/GCP, cloud **forensics** (volatile-data & snapshot acquisition, log-store triage), and **BCDR** references | `aws-ir.md` (CloudTrail triage, EC2 snapshot acquisition, `libcloudforensics`), `azure-ir.md` (Sentinel/Defender, disk snapshot), `gcp-ir.md` (SCC, cloud-forensics-utils), `cloud-resilience.md` (BCDR: RTO/RPO, multi-region failover, backup-restore drills) |

---

## 4. What stays a cross-reference, not a new skill

Full curriculum parity means every module has an **owner**, not that every module needs a **new** skill.
These modules are already owned; G1 wires the cloud-specific cross-reference so a reader lands on the
existing owner:

| Module theme | Existing owner | Cross-ref G1 adds |
|---|---|---|
| Shared-responsibility, cloud threats (M1), cloud architecture (M2) | `devops/threat-modeling`, `devops/cloud-posture` | "for offensive testing of these, see `cloud-recon-enumeration` + the provider skills" |
| Encryption / KMS / secrets (M4, defensive) | `security/secrets-hardening`, `devops/environment-config` | handoff to the cloud-attack storage/secret-enum sections |
| DevSecOps / CI-CD / SAST-DAST-SCA-IaC (M12) | `qa-*:*-security`, `devops/iac-security`, `supply-chain-security` | a one-line "this is the cloud-app-security lane" note; no behaviour change |
| Monitoring / detection (M13, detection half) | `security/detection-engineering`, `detection-validation`, `observability` | `cloud-incident-response` names them as the detection authoring/validation it consumes |
| GRC (M14) | `security/compliance-evidence-mapping`, `standards-audit` | a BCDR crosswalk row (SOC 2 A1.2/A1.3 · ISO 27001:2022 A.5.29–A.5.30 · NIST CSF RC) → `cloud-resilience.md` |

---

## 5. Tasks

All tasks are `docs` (skill/agent authoring — markdown, no application code), so **the coverage floor
does not apply**; the single gate (G1) is a docs/conformance gate (§5a). Order: the shared entry skill
first (C1), the three provider skills and the defensive skill next (A1–A3, B1 — independent of each
other), then wiring (W1), then cross-references + gate + filing last (G1).

### 5a. The gate (runs once, in G1)

Because no application code is written, the gate is:

```bash
python3 -c "import json;json.load(open('.claude-plugin/marketplace.json'))"   # marketplace.json parses
# every registered skill path exists and has YAML frontmatter with name + description:
for s in security/cloud-recon-enumeration security/cloud-attack-aws security/cloud-attack-azure \
         security/cloud-attack-gcp security/cloud-incident-response; do
  test -f "$s/SKILL.md" && head -1 "$s/SKILL.md" | grep -qx '---' || echo "MISSING/BAD: $s"
done
```

Plus, by reading: no broken intra-repo cross-reference link added by this plan; the two plugin
descriptions name the new skills; `CLAUDE.md` + `docs/skills-catalog.md` scope list reconciles with the
skills on disk; command count still 65. G1 **fixes what it finds** rather than handing it back.

---

### C1 — `cloud-recon-enumeration`: the shared cloud-pentest entry skill

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `security/cloud-recon-enumeration/SKILL.md` exists with the standard frontmatter and the
§2 safety gate, teaches provider-agnostic cloud recon (methodology, public-asset + storage enum,
metadata service, IAM/principal/permission enumeration, OIDC/federation), and routes to its four
`references/*.md`. The three provider skills (A1–A3) bind to it by name.
**Depends on:** —
**Budget:** ~95k — CLAUDE.md 25k, this plan §2/§3.1/§5a 10k, `security/recon-enumeration/SKILL.md` as the
format pattern ~8k, `security/atomic-simulation/SKILL.md` for the cloud/ATT&CK-Cloud idiom ~6k,
`devops/cloud-posture/SKILL.md` for the posture↔exploitation handoff ~6k, writes (SKILL.md + 4
references) ~30k.
**Gate: none** — this plan gates once, in G1. Do not run any build, lint, link-check or the §5a gate.

- Frontmatter `name: cloud-recon-enumeration`, description in the house idiom (triggers + "Not for …"
  fences vs `recon-enumeration` (network/host), `cloud-posture` (defensive CSPM), the provider skills).
- Open with the §2 safety gate (committed **cloud scope file**, `#volatile` expiring authorization,
  owned/lab accounts only, loot redaction) — copied in shape from `recon-enumeration`.
- Teach: enumeration posture (anonymous vs authenticated), public-asset discovery, **instance metadata
  service** (IMDSv1 vs IMDSv2, SSRF→temporary credentials, `T1552.005`), IAM/principal/permission
  enumeration, OIDC/workload-identity-federation enumeration. Map each to its ATT&CK-Cloud id.
- `references/`: `scoutsuite.md`, `cloud-enum.md`, `metadata-service.md`, `enumerate-iam.md` — one tool
  family each, invocation + what it answers + how it feeds A1–A3.
- Name the handoff: consumes `cloud-posture` findings as leads; hands enumerated reachability to the
  provider skills.
- **Not in C1:** provider-specific exploitation (A1–A3); marketplace registration + agent routing (W1).

---

### A1 — `cloud-attack-aws`: AWS exploitation (IAM privesc · EC2/S3/RDS · Pacu/ScoutSuite)

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `security/cloud-attack-aws/SKILL.md` exists with the §2 gate; teaches AWS
fundamentals-as-attack-context then exploitation — IAM privilege-escalation paths, EC2 (metadata,
user-data, snapshot), S3 abuse, RDS testing, CloudTrail/GuardDuty awareness, plus a `lab-setup.md` that bootstraps the owned
practice lab — routing to its references.
**Depends on:** C1 (binds to it for recon feedstock).
**Budget:** ~110k — CLAUDE.md 25k, this plan §2/§3.1 8k, C1's SKILL.md as the sibling pattern ~8k,
`privilege-escalation/SKILL.md` for the privesc-chain idiom ~8k, `devops/aws-deployment/SKILL.md` +
`cloud-posture` for AWS-service + handoff context ~10k, writes (SKILL.md + 5 references) ~45k.
**Gate: none** — gates in G1. Do not run the build, lint, link-check or the §5a gate.

- Frontmatter fences vs C1 (recon), `cloud-posture` (posture), `initial-access` (network foothold),
  `atomic-simulation` (Stratus detonation, not exploitation).
- Reference lab targets: **CloudGoat**, **flaws.cloud**, **IAM Vulnerable** (owned-lab only).
- Teach: IAM privesc path discovery (`pmapper`/policy analysis → ATT&CK `T1098`), EC2 metadata/user-data
  credential theft, S3 object/ACL/policy abuse (`T1619`), RDS snapshot/public-access testing,
  CloudTrail/GuardDuty detection-surface awareness (what trips an alert, never evasion-for-stealth).
- `references/`: `pacu.md`, `cloudfox.md`, `pmapper.md`, `s3-attacks.md`, `lab-setup.md` (stand up
  **CloudGoat** / **flaws.cloud** / **IAM Vulnerable** in an owned account: prerequisites, deploy,
  teardown — the owned-lab the rest of the skill practises against).
- Name the handoff to `pentest-reporting` (CVSS + ATT&CK-Cloud id per finding) and to
  `cloud-incident-response` / `detection-engineering` (each finding implies a detection).
- **Not in A1:** Azure (A2), GCP (A3), registration/routing (W1).

---

### A2 — `cloud-attack-azure`: Entra ID + managed identity + Key Vault

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `security/cloud-attack-azure/SKILL.md` exists with the §2 gate; teaches Entra ID
enumeration & abuse, managed-identity abuse, Key Vault access testing, Azure RBAC misconfig and
attacking Azure services, plus a `lab-setup.md` that bootstraps the owned practice lab — routing to its
references.
**Depends on:** C1.
**Budget:** ~105k — CLAUDE.md 25k, this plan §2/§3.1 8k, A1's SKILL.md as the just-landed sibling ~9k,
`devops/azure-deployment/SKILL.md` for service context ~7k, `lateral-movement/SKILL.md` for the
cloud-pivot idiom ~7k, writes (SKILL.md + 5 references) ~45k.
**Gate: none** — gates in G1.

- Frontmatter fences vs A1/A3 and the defensive lanes. Lab target: **AzureGoat**.
- Teach: Entra ID enumeration (users/groups/apps/service-principals, `T1087`), managed-identity &
  service-principal abuse (`T1078.004`), Key Vault access testing, Azure RBAC privesc, Azure Sentinel /
  Defender detection-surface awareness.
- `references/`: `roadtools.md`, `azurehound.md`, `microburst.md`, `azure-keyvault.md`, `lab-setup.md`
  (stand up **AzureGoat** in an owned tenant: prerequisites, deploy, teardown).
- **Not in A2:** AWS (A1), GCP (A3), registration/routing (W1).

---

### A3 — `cloud-attack-gcp`: GCP IAM + service-account chains + storage

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `security/cloud-attack-gcp/SKILL.md` exists with the §2 gate; teaches GCP IAM
enumeration, service-account impersonation/key abuse, storage-bucket attacks and GCP recon/testing
fundamentals, plus a `lab-setup.md` that bootstraps the owned practice lab — routing to its references.
**Depends on:** C1.
**Budget:** ~100k — CLAUDE.md 25k, this plan §2/§3.1 8k, A2's SKILL.md as the sibling pattern ~9k,
`cloud-posture` for the GCP-posture handoff ~6k, writes (SKILL.md + 4 references) ~40k, slack ~12k.
**Gate: none** — gates in G1.

- Frontmatter fences vs A1/A2. Lab target: **GCPGoat**. Note: `cloud-posture` already *reads* GCP; this
  is the first skill that *attacks* it — name that handoff explicitly.
- Teach: GCP IAM/resource enumeration (`T1580`), service-account impersonation & key abuse (`T1078.004`,
  privesc via `iam.serviceAccounts.*` chains), Cloud Storage bucket attacks (`T1619`), Security Command
  Center detection-surface awareness.
- `references/`: `gcp-enum.md`, `gcp-privesc.md`, `gcp-bucket-brute.md`, `lab-setup.md` (stand up
  **GCPGoat** in an owned project: prerequisites, deploy, teardown).
- **Not in A3:** AWS (A1), Azure (A2), registration/routing (W1).

---

### B1 — `cloud-incident-response`: cloud IR runbook + forensics + BCDR references

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `security/cloud-incident-response/SKILL.md` exists with the standard frontmatter;
teaches a cloud IR runbook (detect→triage→contain→eradicate→recover) keyed to AWS/Azure/GCP, cloud
forensics (snapshot/volatile acquisition, log-store triage), and routes to four references including
`cloud-resilience.md` (BCDR).
**Depends on:** — (defensive; independent of C1/A1–A3, references them as the attacks it responds to).
**Budget:** ~100k — CLAUDE.md 25k, this plan §2/§3.2/§4 10k, `security/detection-engineering/SKILL.md` +
`detection-validation/SKILL.md` as the consumed detection half ~12k,
`security/compliance-evidence-mapping/SKILL.md` for the BCDR crosswalk idiom ~8k, writes (SKILL.md + 4
references) ~35k.
**Gate: none** — gates in G1.

- Frontmatter `name: cloud-incident-response`; fences vs `detection-engineering` (authors the rule),
  `detection-validation` (asserts it fired), `observability` (app telemetry), `cloud-posture` (posture).
  This skill owns **respond + recover**, not detect.
- Teach the IR lifecycle per cloud, forensic acquisition (EC2/Azure-disk/GCP-disk snapshot, log-store
  pulls via CloudTrail/Activity Log/Cloud Audit Logs, chain-of-custody notes), and the detection it
  consumes (`detection-engineering` authors, this responds).
- `references/`: `aws-ir.md`, `azure-ir.md`, `gcp-ir.md`, `cloud-resilience.md` (BCDR — RTO/RPO,
  multi-region failover, backup-restore drills, framed for an increasing-threat environment).
- **Not in B1:** the compliance crosswalk *row* into `compliance-evidence-mapping` (G1); registration /
  routing (W1).

---

### W1 — Register the five skills and teach the agents the lane exists

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `.claude-plugin/marketplace.json` registers the four offensive skills under
`penetration-testing` and `cloud-incident-response` under `security-governance`; both plugin
**descriptions** name the new skills; `penetration-tester`, `security-architect`, and
`security-test-planner` agents list/route to the new skills; `docs/skills-catalog.md` + `CLAUDE.md`
scope list include the lane. Command count unchanged (65).
**Depends on:** C1, A1, A2, A3, B1 (every skill path must exist before it is registered and routed).
**Budget:** ~115k — CLAUDE.md 25k, this plan §3/§4/the bookkeeping note 8k, `marketplace.json` pen-test +
sec-gov blocks ~12k, the three agent files ~18k, `docs/skills-catalog.md` relevant sections ~15k, writes
(edits across ~6 files) ~25k, slack ~12k.
**Gate: none** — gates in G1. Do not run the §5a gate here; G1 carries it.

- `marketplace.json`: add the four `./security/cloud-*` offensive skill paths to `penetration-testing`'s
  `skills[]`, and `./security/cloud-incident-response` to `security-governance`'s `skills[]`. Extend both
  plugin **descriptions** with the new skills (one clause each, matching the existing dense style).
- `security/agents/penetration-tester.md`: add the four cloud-attack skills to its loadable set /
  kill-chain narrative (cloud lane alongside the network lane).
- `security/agents/security-architect.md`: add `cloud-incident-response` to the lanes it rolls up.
- `security/agents/security-test-planner.md`: add the cloud skills to its **routing catalog** (exact
  names) so an assessment of a cloud platform routes a cloud-pentest + cloud-IR phase; verify every name
  resolves (the self-review rule the agent already enforces).
- `docs/skills-catalog.md` + `CLAUDE.md`: add the lane to the scope list / `security/` inventory; leave
  the command count at 65 (no new commands).
- **Not in W1:** cross-reference edits into the existing *skills* (G1); the gate (G1).

---

### G1 — Cross-references into existing skills, the gate, and file the plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the §4 cross-references are wired into the existing skills; the §5a gate passes; the
plan is filed to `docs/plans/implemented/`.
**Depends on:** W1 (routing must be in place before the cross-refs point at it).
**Budget:** ~120k — CLAUDE.md 25k, this plan whole ~14k, the five existing skills that gain a cross-ref
(`cloud-posture`, `threat-modeling`, `iac-security`, `detection-engineering`, `compliance-evidence-mapping`)
~30k, writes (small edits across them) ~15k, the gate commands + reading-based checks ~20k, close-out
~16k.
**Gate (last task — carries the plan's only gate, §5a):** run the `marketplace.json`-parse + skill-path +
frontmatter checks; then by reading, confirm no broken cross-reference link, both plugin descriptions
name the new skills, `CLAUDE.md`/`docs/skills-catalog.md` reconcile with disk, command count still 65.
**Fix what it finds** — a failure may belong to any task above.

- Add the §4 cross-reference lines: `cloud-posture` → the offensive provider skills (posture↔exploitation
  handoff); `threat-modeling` → cloud recon; `iac-security` + the DevSecOps lane → "cloud-app-security"
  note; `detection-engineering`/`detection-validation` → named by `cloud-incident-response`;
  `compliance-evidence-mapping` → the BCDR crosswalk row (SOC 2 A1.2/A1.3 · ISO 27001:2022
  A.5.29–A.5.30 · NIST CSF RC) pointing at `cloud-resilience.md`.
- Run the gate; fix anything it surfaces (a mis-registered path, a dangling link, a stale count).
- Close out per "Close-out — every task": `As built`, delete prompts, rewrite `Status:`, `git mv` the
  plan to `docs/plans/implemented/008-cloud-security-lane.md`, one commit.
- **Not in G1:** any new skill (C1–B1); registration/routing (W1).

---

## Decisions

**D1 — The offensive cloud lane is four skills, not one per course module.** M5–M11 are eight course
modules but three attack surfaces plus a shared recon discipline. One skill per provider (plus the
shared entry skill) merges "fundamentals" and "advanced/exploitation" into the provider that owns the
surface, matching the one-tool-family idiom and the fewest-sessions rule. Cost: a single AWS skill is
large; mitigated by routing depth to `references/*.md`.

| Option | Verdict | Why |
|---|---|---|
| One skill per course module (8+) | rejected | triplicates the safety gate, re-reads the same account model 8×, and splits one surface across sessions |
| One skill per provider + shared recon (4) | **chosen** | one surface = one skill = one session; recon shared so providers don't repeat it |
| One monolithic "cloud-pentest" skill | rejected | 3 clouds in one file blows the authoring budget and the reader's load |

**D2 — BCDR is a reference file, not a skill.** M14's BCDR has few callers and sits beside IR
operationally (recover-from-incident vs recover-from-disaster). It lives as `references/cloud-resilience.md`
under `cloud-incident-response`, plus a crosswalk row in `compliance-evidence-mapping`. Cost: BCDR is not
independently discoverable as a top-level skill; accepted because a one-caller skill violates KISS.

**D3 — The new offensive skills reuse the existing `penetration-tester` runtime agent, not a new
`cloud-pentester` agent.** The kill-chain agent already carries the §5 authorization gate and the
reporting handoff; a cloud lane is a new surface for it, not a new persona. Cost: the agent's loadable
skill set grows; accepted — it is still one authorization discipline.

**D4 — No new commands.** Every new skill is agent-reached (loaded by `penetration-tester` /
`security-architect` / routed by `security-test-planner`), exactly as the existing defensive/governance
skills are. The 65-command surface is unchanged. Cost: none — matches the plugins' existing shape.

**D5 — Detection-surface awareness, never evasion-for-stealth.** The AWS/Azure/GCP skills teach what
CloudTrail/GuardDuty, Sentinel/Defender, and SCC *detect* (so a tester knows their footprint and a
defender knows what to tune), never techniques whose purpose is to evade detection on a real target.
This keeps the lane inside the authorized-self-testing / lab-training frame (SECURITY-EXPANSION-PLAN §2).

**D6 — Practice-lab bootstrap is a `references/lab-setup.md` per provider skill, not a standalone skill
(Q1 → b, 2026-10-21).** Each provider skill (A1/A2/A3) ships a `lab-setup.md` that stands up its owned
lab — CloudGoat/flaws.cloud/IAM Vulnerable (AWS), AzureGoat (Azure), GCPGoat (GCP): prerequisites,
deploy, teardown. The skill the lab belongs to owns its bootstrap; a standalone lab-setup skill would be
one caller per provider (KISS, same reasoning as D2). Cost: bootstrap is discoverable only from inside
the provider skill, not as a top-level skill; accepted.

## Answered questions (2026-10-21)

**O1 — How much of the curriculum? :** full parity — every one of the 14 modules has an owning skill or
a wired cross-reference (user, 2026-10-21).

**O2 — New skills vs cross-references? :** five new skills (M5, M7+M8, M9+M10, M11, M13+M14-IR); the rest
(M1, M2, M4, M12, M14-GRC) are already owned and get cross-references only (§4).

**O3 — Which plugin? :** offensive skills into `penetration-testing`; the IR/forensics/BCDR skill into
`security-governance` — matching the existing offensive/defensive split.

**O4 — Practice-lab bootstrap? :** yes — as a `references/lab-setup.md` per provider skill (Q1 → b);
see D6 (user, 2026-10-21).

## Open questions

None — Q1 resolved to O4 / D6.

---

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed reference name, a moved handoff), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number.
7. **Commit** — the skill files and these plan edits together, in one commit.

---

## Prompts — one per task

Run them in order, one session each; each block is complete on its own. **No prompt runs the gate
except G1** — C1, A1, A2, A3, B1 and W1 each carry `Gate: none`. No prompt stands up a real cloud
account or runs any tool; these skills are authored, not executed. All prompts are live (nothing has
landed yet).

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| C1 | `docs` | `general-purpose` | — | ~95k |
| A1 | `docs` | `general-purpose` | C1 | ~110k |
| A2 | `docs` | `general-purpose` | C1 | ~105k |
| A3 | `docs` | `general-purpose` | C1 | ~100k |
| B1 | `docs` | `general-purpose` | — | ~100k |
| W1 | `docs` | `general-purpose` | C1, A1, A2, A3, B1 | ~115k |
| G1 | `docs` | `general-purpose` | W1 | ~120k |

---

### C1 — `cloud-recon-enumeration` (general-purpose, docs)

````
You are authoring a skill (docs). Task C1 of docs/plans/008-cloud-security-lane.md: write
`security/cloud-recon-enumeration/SKILL.md` + its four references — the shared cloud-pentest entry skill
the AWS/Azure/GCP exploitation skills will bind to.

Read, in this order:
1. CLAUDE.md (global rules — comments, simplicity, version policy).
2. The plan: §2 (design principles — the safety gate you must open with), §3.1 (the skill table),
   §5a (the gate — you do NOT run it), task C1, and "Close-out — every task".
3. `security/recon-enumeration/SKILL.md` — the FORMAT pattern (frontmatter idiom, the opening
   authorization gate, references routing). Yours is the cloud analogue of this.
4. `security/atomic-simulation/SKILL.md` — for the cloud + MITRE ATT&CK-Cloud idiom already in the repo
   (Stratus, cloud matrix).
5. `devops/cloud-posture/SKILL.md` §intro — so you name the posture↔exploitation handoff correctly.
6. `docs/research/cloud-security/02-pentest-methodology-recon.md` — the research corpus for THIS skill
   (methodology, metadata-service detail, the multi-cloud tools table → your four reference files). Lift
   facts from it; also skim `docs/research/cloud-security/README.md` currency ledger (IMDSv2 hop-limit,
   OIDC "Sub:jugation", lab attributions).

Write:
- `security/cloud-recon-enumeration/SKILL.md`: frontmatter (`name: cloud-recon-enumeration`, a
  description with triggers + "Not for …" fences vs recon-enumeration/cloud-posture/the provider skills);
  then the §2 safety gate (committed cloud scope file, #volatile expiring authorization, owned/lab
  accounts only, loot redaction); then the teaching body — enumeration posture, public-asset + storage
  discovery, the instance metadata service (IMDSv1/v2, SSRF→creds, T1552.005),
  IAM/principal/permission + OIDC/federation enumeration — each mapped to its ATT&CK-Cloud id.
- `references/scoutsuite.md`, `references/cloud-enum.md`, `references/metadata-service.md`,
  `references/enumerate-iam.md` — one tool family each: invocation, what it answers, how it feeds A1–A3.

Traps:
- ATT&CK matrix is **Cloud** (IaaS/Identity Provider/SaaS), not Enterprise.
- This skill is recon ONLY — no exploitation (that's A1–A3). State the handoff, don't do their job.
- Comments rule: SKILL.md prose is fine; do not add code-comment noise to any example blocks.

Gate: none — this plan gates once, in G1. Do not run the build, any linter, the §5a gate, or any tool.

Commit: `feat(penetration-testing): cloud-recon-enumeration skill (cloud lane C1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A1 — `cloud-attack-aws` (general-purpose, docs)

````
You are authoring a skill (docs). Task A1 of docs/plans/008-cloud-security-lane.md: write
`security/cloud-attack-aws/SKILL.md` + its four references — AWS exploitation (IAM privesc, EC2/S3/RDS,
Pacu/ScoutSuite), binding to cloud-recon-enumeration for recon feedstock.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3.1, task A1, "Close-out — every task".
3. `security/cloud-recon-enumeration/SKILL.md` as C1 left it — the sibling pattern + the recon handoff
   you consume. Match its frontmatter and safety-gate shape.
4. `security/privilege-escalation/SKILL.md` — the privesc-chain idiom (enumerate → identify → exploit
   least-risky path).
5. `devops/aws-deployment/SKILL.md` + `devops/cloud-posture/SKILL.md` §intro — AWS-service context and
   the posture handoff.
6. `docs/research/cloud-security/03-aws.md` — the research corpus for THIS skill (the 21 Rhino privesc
   paths with exact permissions, Pacu/CloudFox/PMapper, service exploitation, GuardDuty finding ids,
   CloudGoat scenarios). Lift facts from it; heed its verify-against-repo and IMDSv1-live-risk notes, and
   the README currency ledger.

Write:
- `security/cloud-attack-aws/SKILL.md`: frontmatter fenced vs C1/cloud-posture/initial-access/
  atomic-simulation; the §2 gate; lab targets CloudGoat / flaws.cloud / IAM Vulnerable (owned-lab only);
  teaching body — IAM privesc paths (T1098), EC2 metadata/user-data/snapshot, S3 abuse (T1619), RDS
  testing, CloudTrail/GuardDuty detection-surface awareness (what trips an alert — NOT evasion, see D5).
- `references/pacu.md`, `references/cloudfox.md`, `references/pmapper.md`, `references/s3-attacks.md`,
  `references/lab-setup.md` (stand up CloudGoat / flaws.cloud / IAM Vulnerable in an OWNED account:
  prerequisites, deploy, teardown — the owned-lab the skill practises against).

Traps:
- D5: teach detection *awareness*, never stealth/evasion-for-a-real-target.
- Loot redaction (§2.5): a recovered key is reported as blast radius, never its value.
- Name the handoff to pentest-reporting (CVSS + ATT&CK-Cloud id) and to cloud-incident-response.

Gate: none — gates in G1. Do not run the build, any linter, the §5a gate, or any tool.

Commit: `feat(penetration-testing): cloud-attack-aws skill (cloud lane A1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A2 — `cloud-attack-azure` (general-purpose, docs)

````
You are authoring a skill (docs). Task A2 of docs/plans/008-cloud-security-lane.md: write
`security/cloud-attack-azure/SKILL.md` + its four references — Entra ID / managed-identity / Key Vault /
Azure RBAC exploitation.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3.1, task A2, "Close-out — every task".
3. `security/cloud-attack-aws/SKILL.md` as A1 left it — the just-landed sibling; match its shape.
4. `devops/azure-deployment/SKILL.md` §intro — Azure-service context.
5. `security/lateral-movement/SKILL.md` — the cloud-pivot idiom.
6. `docs/research/cloud-security/04-azure.md` — the research corpus for THIS skill (two-plane model,
   Entra enumeration, managed-identity/Key Vault/RBAC privesc, detection surface). Heed its tooling
   currency: ROADrecon `gather` is broken (needs the msgraph fork), Stormspotter is dormant (use
   AzureHound+BloodHound), Hybrid-Worker ListKeys is partly mitigated — version-check before teaching.
   Also the README currency ledger.

Write:
- `security/cloud-attack-azure/SKILL.md`: frontmatter fenced vs A1/A3/defensive lanes; §2 gate; lab
  target AzureGoat; teaching body — Entra ID enumeration (T1087), managed-identity/service-principal
  abuse (T1078.004), Key Vault access testing, Azure RBAC privesc, Sentinel/Defender detection-surface
  awareness (D5).
- `references/roadtools.md`, `references/azurehound.md`, `references/microburst.md`,
  `references/azure-keyvault.md`, `references/lab-setup.md` (stand up AzureGoat in an OWNED tenant:
  prerequisites, deploy, teardown).

Traps:
- "Azure AD" is now "Entra ID" — use the current name, note the old one once.
- D5 (awareness not evasion); §2.5 loot redaction.

Gate: none — gates in G1. Do not run the build, any linter, the §5a gate, or any tool.

Commit: `feat(penetration-testing): cloud-attack-azure skill (cloud lane A2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A3 — `cloud-attack-gcp` (general-purpose, docs)

````
You are authoring a skill (docs). Task A3 of docs/plans/008-cloud-security-lane.md: write
`security/cloud-attack-gcp/SKILL.md` + its three references — GCP IAM / service-account / storage
exploitation. This is the first skill that ATTACKS GCP (cloud-posture only reads it).

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3.1, task A3, "Close-out — every task".
3. `security/cloud-attack-azure/SKILL.md` as A2 left it — the sibling pattern.
4. `devops/cloud-posture/SKILL.md` — name the GCP posture↔exploitation handoff.
5. `docs/research/cloud-security/05-gcp.md` — the research corpus for THIS skill (SA-impersonation spine
   via the IAM Credentials API verbs, the ~20 privesc methods split IAM/non-IAM with exact permissions,
   GCS/metadata/Secret Manager, GCPGoat). Critical currency note it carries: the Compute default SA no
   longer auto-gets Editor on new projects — DETECT, don't assume. Also the README currency ledger.

Write:
- `security/cloud-attack-gcp/SKILL.md`: frontmatter fenced vs A1/A2; §2 gate; lab target GCPGoat;
  teaching body — GCP IAM/resource enumeration (T1580), service-account impersonation & key abuse
  (T1078.004, privesc via iam.serviceAccounts.* chains), Cloud Storage bucket attacks (T1619), Security
  Command Center detection-surface awareness (D5).
- `references/gcp-enum.md`, `references/gcp-privesc.md`, `references/gcp-bucket-brute.md`,
  `references/lab-setup.md` (stand up GCPGoat in an OWNED project: prerequisites, deploy, teardown).

Traps:
- GCP privesc is dominated by service-account impersonation chains — make that the spine.
- D5 (awareness not evasion); §2.5 loot redaction.

Gate: none — gates in G1. Do not run the build, any linter, the §5a gate, or any tool.

Commit: `feat(penetration-testing): cloud-attack-gcp skill (cloud lane A3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### B1 — `cloud-incident-response` (general-purpose, docs)

````
You are authoring a skill (docs). Task B1 of docs/plans/008-cloud-security-lane.md: write
`security/cloud-incident-response/SKILL.md` + its four references — cloud IR runbook, cloud forensics,
and BCDR (as cloud-resilience.md). Defensive, for the security-governance plugin.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3.2, §4 (the BCDR crosswalk you set up here for G1 to wire), task B1,
   "Close-out — every task".
3. `security/detection-engineering/SKILL.md` + `security/detection-validation/SKILL.md` — the detection
   half this skill CONSUMES (author → validate → respond). Fence against them cleanly.
4. `security/compliance-evidence-mapping/SKILL.md` — for the BCDR crosswalk idiom (SOC 2 / ISO / NIST).
5. `docs/research/cloud-security/07-secops-ir-forensics.md` (IR lifecycle, three-cloud log map, forensic
   acquisition, runbooks) and `docs/research/cloud-security/08-grc-bcdr.md` §BCDR (→ your
   `cloud-resilience.md`). Anchor to NIST SP 800-61r3 (CSF-2.0-aligned, 2025) AND PICERL; cover both the
   Sentinel Log-Analytics and Defender-portal paths. Also the README currency ledger.

Write:
- `security/cloud-incident-response/SKILL.md`: frontmatter `name: cloud-incident-response`, fenced vs
  detection-engineering (authors) / detection-validation (asserts fired) / observability (app telemetry)
  / cloud-posture (posture). This skill owns RESPOND + RECOVER, not detect. Teaching body — the IR
  lifecycle per cloud (detect→triage→contain→eradicate→recover), cloud forensic acquisition
  (EC2/Azure-disk/GCP-disk snapshot, log-store pulls, chain-of-custody).
- `references/aws-ir.md`, `references/azure-ir.md`, `references/gcp-ir.md`,
  `references/cloud-resilience.md` (BCDR: RTO/RPO, multi-region failover, backup-restore drills).

Traps:
- Do NOT author or validate detections here — that's detection-engineering/detection-validation. You
  consume their output and respond.
- The BCDR crosswalk ROW into compliance-evidence-mapping is G1's job; here you just write
  cloud-resilience.md so G1 can point at it.

Gate: none — gates in G1. Do not run the build, any linter, the §5a gate, or any tool.

Commit: `feat(security-governance): cloud-incident-response skill (cloud lane B1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W1 — register the skills + teach the agents (general-purpose, docs)

````
You are wiring the lane in (docs). Task W1 of docs/plans/008-cloud-security-lane.md: register the five
new skills in marketplace.json, extend both plugin descriptions, teach three agents the lane, and update
the catalog. No new commands.

Read, in this order:
1. CLAUDE.md.
2. The plan: §3 (the skill tables), §4, the bookkeeping note at the end of §2, task W1,
   "Close-out — every task".
3. `.claude-plugin/marketplace.json` — the `penetration-testing` and `security-governance` blocks
   (skills[], description).
4. `security/agents/penetration-tester.md`, `security/agents/security-architect.md`,
   `security/agents/security-test-planner.md` — where each lists/routes skills.
5. The five new skills' frontmatter (C1, A1, A2, A3, B1) — for exact names.
6. `docs/skills-catalog.md` — the `security/` inventory + scope list sections.

Do:
- marketplace.json: add the four `./security/cloud-*` offensive skill paths to penetration-testing's
  `skills[]`; add `./security/cloud-incident-response` to security-governance's `skills[]`. Extend both
  plugin descriptions with one dense clause each naming the new skills (match the existing style).
- penetration-tester.md: add the four cloud-attack skills to its kill-chain / loadable set (cloud lane).
- security-architect.md: add cloud-incident-response to the lanes it rolls up.
- security-test-planner.md: add all five to its routing catalog by EXACT name; a cloud platform now
  routes a cloud-pentest + cloud-IR phase. Verify every name resolves.
- docs/skills-catalog.md + CLAUDE.md: add the lane to the security inventory / scope list. Command count
  STAYS 65 (no new commands — D4).

Traps:
- An invented agent/skill name is the most damaging defect — copy names from the files, don't retype.
- Do NOT edit the existing *skills'* bodies for cross-refs — that's G1. You touch marketplace.json, the
  3 agents, and the 2 catalog files only.

Gate: none — gates in G1. Do not run the §5a gate here.

Commit: `feat(security): register cloud lane in marketplace + agents + catalog (cloud lane W1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — cross-references, the gate, and file the plan (general-purpose, docs)

````
You are closing the plan out (docs). Task G1 of docs/plans/008-cloud-security-lane.md, the LAST task:
wire the §4 cross-references into the existing skills, run the plan's only gate, and file the plan.

Read, in this order:
1. CLAUDE.md.
2. The plan: §4 (the cross-reference table — exactly what to add where), §5a (the gate), task G1,
   "Close-out — every task", and §8-equivalent filing in the close-out.
3. The five existing skills that gain a cross-ref: `devops/cloud-posture/SKILL.md`,
   `devops/threat-modeling/SKILL.md`, `devops/iac-security/SKILL.md`,
   `security/detection-engineering/SKILL.md`, `security/compliance-evidence-mapping/SKILL.md`.
4. W1's "As built" note in the plan — so you cross-ref the names W1 actually registered.
5. `docs/research/cloud-security/06-devsecops-appsec.md` §6 (paste-ready cross-reference wording for the
   DevSecOps/IaC lane) and `docs/research/cloud-security/08-grc-bcdr.md` §"BCDR → compliance crosswalk"
   (the exact SOC 2 A1.2/A1.3 · ISO A.5.29/A.5.30 · NIST CSF RECOVER rows).

Do:
- Add the §4 cross-reference lines (one or two sentences each, in the existing voice):
  cloud-posture → the offensive provider skills (posture↔exploitation handoff); threat-modeling →
  cloud-recon-enumeration; iac-security + the DevSecOps lane → a "cloud-app-security" note;
  detection-engineering → named as the authoring half cloud-incident-response consumes;
  compliance-evidence-mapping → the BCDR crosswalk row (SOC 2 A1.2/A1.3 · ISO 27001:2022
  A.5.29–A.5.30 · NIST CSF RC) pointing at cloud-incident-response/references/cloud-resilience.md.

Gate (this is the last task — the plan's only gate, §5a):
  python3 -c "import json;json.load(open('.claude-plugin/marketplace.json'))"
  for s in security/cloud-recon-enumeration security/cloud-attack-aws security/cloud-attack-azure \
           security/cloud-attack-gcp security/cloud-incident-response; do
    test -f "$s/SKILL.md" && head -1 "$s/SKILL.md" | grep -qx '---' || echo "MISSING/BAD: $s"; done
  Then by reading: no broken cross-ref link; both plugin descriptions name the new skills;
  CLAUDE.md + docs/skills-catalog.md reconcile with the skills on disk; command count still 65.
  Fix what it finds — a failure may belong to any task above (C1–W1), not only to you.

Then file: rewrite Status: one final time, `git mv docs/plans/008-cloud-security-lane.md
docs/plans/implemented/`, delete your prompt block (leaving none).

Commit: `feat(security): cloud lane cross-references + gate; file plan 008 (cloud lane G1)`.
Close out per the plan's "Close-out — every task" before you stop.
````
