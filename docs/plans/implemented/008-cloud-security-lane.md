# 008 — Cloud security lane: offensive cloud pentest + cloud IR/forensics + BCDR — plan (2026-10-21)

**Goal:** Give the `penetration-testing` and `security-governance` plugins full coverage of a cloud
security / cloud-pentest curriculum (AWS · Azure · GCP), so every module of the course that prompted
this has an owning skill or a wired cross-reference. Four new offensive skills (cloud recon, then
AWS/Azure/GCP exploitation), one new defensive skill (cloud incident response + forensics + BCDR
references), and a wiring + cross-reference pass that teaches the existing agents and skills the new
lane exists.

**Status:** DONE (2026-10-31) — all tasks landed and the plan is filed. **Delivered end to end:** the
cloud security lane is complete and self-consistent. Five new skills exist on disk — `security/cloud-recon-enumeration`
(C1) + the three `security/cloud-attack-{aws,azure,gcp}` provider skills (A1/A2/A3) + `security/cloud-incident-response`
(B1) with its four references incl. `cloud-resilience.md` (BCDR); all are registered in `.claude-plugin/marketplace.json`,
named in both plugin descriptions, and routed by the `penetration-tester` / `security-architect` /
`security-test-planner` agents (W1); and the §4 cross-references are wired into the five existing skills —
`devops/cloud-posture`, `devops/threat-modeling`, `devops/iac-security`, `security/detection-engineering`,
`security/compliance-evidence-mapping` (incl. the BCDR crosswalk rows → `cloud-resilience.md`) (G1). The
single §5a gate ran and is **green**: marketplace parses, all five skills carry `---` frontmatter, both
descriptions name the lane, every intra-repo cross-ref resolves, catalog + `CLAUDE.md` reconcile with disk,
command count still **65**. **Unverified:** nothing beyond the §5a docs/conformance gate — these are authored
skills, never executed, so no skill was run against a live cloud account (by design; each carries its own
`#volatile` authorization gate for when it is). No new commands ship (65-command surface unchanged).

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

**As built (2026-10-21):** Landed exactly as planned — no divergence. `security/cloud-recon-enumeration/SKILL.md`
(`file:1`) carries the frontmatter (`name: cloud-recon-enumeration`, triggers + "Not for …" fences vs
`recon-enumeration`/`cloud-posture`/the three provider skills), the §2 safety gate (cloud scope file +
`#volatile` authorization line, owned/lab-only, loot redaction), and the teaching body: enumeration
posture (anonymous→authenticated), public-asset/storage discovery, the full IMDSv1/v2 + hop-limit +
dual-accept detail (`T1552.005`), IAM/principal/permission enumeration (`T1087.004`), and OIDC/federation
trust enumeration (incl. the cross-tenant "Sub:jugation" red line) — each mapped to its ATT&CK **Cloud**
id (T1580/T1526/T1619/T1552.005/T1087.004), confirmed not Enterprise. Four references written exactly as
named: `references/scoutsuite.md`, `references/cloud-enum.md`, `references/metadata-service.md`,
`references/enumerate-iam.md` — each one tool family, invocation, what it answers, and an explicit "how
it feeds the provider skills" section for A1–A3 to bind against. The posture↔exploitation handoff with
`devops:cloud-posture` is named in both the SKILL.md body and its cross-references section. No prompt
below (A1/A2/A3/B1/W1/G1) needed rewriting — every name/path this task produced (`cloud-recon-enumeration`,
the four reference filenames, the ATT&CK Cloud ids) matches what those prompts already assumed. Verified
by reading the written files back; no gate run (per `Gate: none`).

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

**As built (2026-10-31):** Landed exactly as planned — no divergence. `security/cloud-attack-aws/SKILL.md`
(`file:1`) carries the frontmatter (`name: cloud-attack-aws`, triggers + "Not for …" fences vs
`cloud-recon-enumeration`/`cloud-attack-azure`/`cloud-attack-gcp`/`devops:cloud-posture`/`initial-access`/
`atomic-simulation`), the §2 safety gate (cloud scope file + `#volatile` authorization line, owned/lab-only,
loot redaction), and the teaching body: AWS target model (IAM-is-the-perimeter, PassRole pivot, STS graph),
Step 1 enumeration (enumerate-iam/Pacu/CloudFox), Step 2 IAM privesc (the four families of the 21 Rhino
paths, `T1098`/`T1098.001`/`T1548`/`T1078.004`), Step 3 service exploitation (EC2 IMDSv1/v2 + hop-limit +
dual-accept + user-data + snapshot `T1552.005`/`T1578`/`T1537`, S3 `T1619`/`T1530`, RDS, Lambda/Secrets/SSM),
and Step 4 CloudTrail/GuardDuty detection-surface awareness (D5 — what trips an alert, never evasion), each
mapped to its ATT&CK **Cloud** (IaaS) id. Five references written exactly as named:
`references/pacu.md` (Pacu + enumerate-iam), `references/cloudfox.md` (CloudFox + ScoutSuite),
`references/pmapper.md` (the full 21-path table + graph queries), `references/s3-attacks.md`, and
`references/lab-setup.md` (CloudGoat / flaws.cloud / IAM Vulnerable deploy+teardown in an owned account).
Heeded the research corpus's verify-against-repo notes (Rhino count stated as **21**, not 41; roster
"confirm against the repo at authoring time"), the IMDSv1-live-risk note (F5 March-2025 campaign, dual-accept,
detect-don't-assume), and §2.5 loot redaction throughout. Handoffs named: `penetration-testing:reporting`
(CVSS + ATT&CK-Cloud id), `cloud-incident-response`, `detection-engineering`, and the `cloud-posture`
posture↔exploitation handoff both ways. No prompt below (A2/B1/W1/G1) needed rewriting — every name/path
A2 binds to (`security/cloud-attack-aws/SKILL.md` as the just-landed sibling) matches what its prompt
already assumes. Verified by reading the written files back; no gate run (per `Gate: none`).

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

**As built (2026-10-31):** Landed exactly as planned — no divergence. A1 had already landed in this
worktree, so `security/cloud-attack-azure/SKILL.md` (`file:1`) was patterned against
`security/cloud-attack-aws/SKILL.md` as the just-landed sibling exactly as the prompt directed — same shape:
frontmatter (`name: cloud-attack-azure`, triggers + "Not for …" fences vs `cloud-recon-enumeration`/
`cloud-attack-aws`/`cloud-attack-gcp`/`devops:cloud-posture`/`initial-access`/`atomic-simulation`), the §2
safety gate (cloud scope file + `#volatile` authorization line, owned/lab-only, loot redaction), ATT&CK
**Cloud** framing, and the decision-matrix/anti-patterns/rules/cross-references sections. Teaching body:
Azure target model (the **two-plane** Entra-ID↔Azure-RBAC model + the GA elevate-access bridge + the
app-registration/SP/MI vocabulary), Step 1 Entra enumeration (`T1087.004`/`T1069.003`/`T1526`, ROADrecon +
AzureHound), Step 2 identity abuse & token theft (MI IMDS `169.254.169.254` + `Metadata: true`,
`T1552.005`→`T1078.004`; SP credential abuse; consent/credential-add `T1098.001`/`.003`; device-code/PRT
awareness-only), Step 3 Key Vault data-plane testing (access-policy vs RBAC, the Key Vault Contributor
privesc, `T1552`), Step 4 Azure RBAC privesc & service attacks (role-assignment abuse `T1098`, storage-key
`listKeys` theft `T1552`/`T1537`, Run Command `T1651`, Automation/Hybrid-Worker), and Step 5
Sentinel/Defender detection-surface awareness (D5 — table of log sources, both Log-Analytics and
Defender-portal paths). Five references written exactly as named: `references/roadtools.md` (ROADrecon +
GraphRunner), `references/azurehound.md` (AzureHound → BloodHound Azure edges), `references/microburst.md`,
`references/azure-keyvault.md`, `references/lab-setup.md` (AzureGoat deploy+teardown in an owned
subscription). Heeded every corpus currency note: **"Entra ID" used throughout, old "Azure AD" named once**;
**ROADrecon `gather` broken → msgraph community fork**; **Stormspotter dormant → AzureHound+BloodHound
primary** (Stormspotter named only as an anti-pattern); **Hybrid-Worker `ListKeys` partly mitigated →
version-check, detect-don't-assume**; **Sentinel→Defender migration incomplete in 2026 → both paths**; D5
awareness-not-evasion and §2.5 loot redaction throughout. Handoffs named: `cloud-recon-enumeration`
(upstream), `devops:cloud-posture` (both ways), `initial-access`, `lateral-movement` (cloud pivot),
`atomic-simulation`, `penetration-testing:reporting`, `cloud-incident-response`. No prompt below A2
(B1/W1/G1) needed rewriting — every name/path they assume (`security/cloud-attack-azure/SKILL.md`, the five
reference names) matches what this task produced. Verified by reading the written files back; no gate run
(per `Gate: none`). Deliverable proof: `security/cloud-attack-azure/SKILL.md:1` plus the five
`security/cloud-attack-azure/references/*.md`.

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

**As built (2026-10-31):** Landed with one divergence (see D7): A1/A2 had not yet landed when this task
ran (plan order lets A1/A2/A3/B1 run in any order after C1), so `security/cloud-attack-gcp/SKILL.md`
(`file:1`) was patterned against `security/cloud-recon-enumeration/SKILL.md` (C1 — frontmatter shape,
`#volatile` authorization block, ATT&CK-Cloud framing, decision-matrix/anti-patterns/rules/cross-references
sections) rather than A2's sibling file, which does not exist yet. Everything else landed exactly as
planned: the §2 gate, lab target **GCPGoat**, and the full teaching body — GCP resource hierarchy + IAM
inheritance + service-account model + metadata server (target-model section), IAM/resource enumeration
(`T1580`/`T1526`), service-account impersonation & privilege escalation via the IAM Credentials API verbs
(`T1078.004`/`T1098`/`T1098.001`/`T1548`, the Rhino ~20-method catalog split IAM/non-IAM with exact
permissions), Cloud Storage bucket attacks (`T1619`/`T1530`), and Security Command Center detection-surface
awareness framed as D5 (awareness, not evasion). The posture↔exploitation handoff with `devops:cloud-posture`
is named explicitly in both the SKILL.md intro and its cross-references section, including the "this is the
first skill that attacks GCP" framing the task required. The default-Compute-SA currency note (no longer
auto-Editor on new projects — detect, don't assume) is carried into the target-model section and into a
named anti-pattern. Four references written exactly as named: `references/gcp-enum.md`,
`references/gcp-privesc.md`, `references/gcp-bucket-brute.md`, `references/lab-setup.md` (GCPGoat deploy +
teardown in a throwaway owned project). No prompt below A3 needed rewriting — A1/A2/B1/W1's assumptions
(file names, reference names, ATT&CK ids) all match what this task produced. Verified by reading the
written files back; no gate run (per `Gate: none`).

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

**As built (2026-10-31):** Landed exactly as planned — no divergence. `security/cloud-incident-response/SKILL.md`
(`file:1`) carries the frontmatter (`name: cloud-incident-response`, triggers + "Not for …" fences vs
`detection-engineering` (authors the rule) / `detection-validation` (asserts it fired) / `observability`
(app telemetry) / `cloud-posture` (posture), and the explicit "owns RESPOND + RECOVER, not detect" line).
Teaching body: the two framework anchors — **NIST SP 800-61r3** (final 2025-04-03, supersedes r2, CSF-2.0
functions) **and SANS PICERL** — with a step→r3-function→PICERL-phase table; the "acquire before you destroy"
rule + cloud-adapted order of volatility (RFC 3227); a "know your telemetry" per-cloud three-plane precondition
table with the immutable/out-of-band retention requirement; the runbook (detect→triage→contain→eradicate→
recover) with the identity-vs-host containment distinction; the three runbook skeletons (A credential / B
instance / C exposure); a cloud-forensics chain-of-custody section; anti-patterns and hard rules. Both the
**Sentinel/Log-Analytics (KQL)** and **Defender-portal** paths are named (migration-incomplete-in-2026 note).
Four references written exactly as named: `references/aws-ir.md` (CloudTrail triage, EBS snapshot, SSM+LiME/
WinPmem memory, Detective/Security Hub/Security Lake, libcloudforensics), `references/azure-ir.md` (Sentinel+
Defender both paths, `az snapshot create`, Entra session/token revoke, Network Watcher), `references/gcp-ir.md`
(SCC, `gcloud compute disks snapshot`, GRR, cloud-forensics-utils, the SA-as-identity-and-resource twist +
default-Compute-SA detect-don't-assume note), and `references/cloud-resilience.md` (BCDR: RTO/RPO + BIA, the
four DR patterns with the "same RPO, different RTO" rule, AZ-vs-region, 3-2-1-1-0 backup + immutability,
multi-region failover, restore/DR drills, per-cloud service table, and the full BCDR→compliance crosswalk the
G1 row will cite). Heeded the corpus currency notes: 800-61r3 anchored (r2 five-phase named only as an
anti-pattern), CSF 2.0 RECOVER as RC.RP+RC.CO (two categories), ISO A.5.29/A.5.30 both new-in-2022,
libcloudforensics 2024-10-18 + "verify verbs against the repo" caveats, Sentinel→Defender both paths,
GCP global-VPC + SA-as-resource asymmetries not flattened, and loot redaction throughout. Fenced cleanly vs
detection-engineering/detection-validation/observability/cloud-posture — this skill consumes the detection
half and authors none. The BCDR crosswalk ROW into `compliance-evidence-mapping` is left for G1 (per the
task's "Not in B1"); `cloud-resilience.md` holds the detail that row cites. No prompt block below B1 needed
rewriting — W1 binds to `./security/cloud-incident-response` and the `cloud-incident-response` frontmatter
name, and G1 points at `cloud-incident-response/references/cloud-resilience.md`; all three match what this
task produced. Deliverable proof: `security/cloud-incident-response/SKILL.md:1` plus the four
`security/cloud-incident-response/references/*.md`. Verified by reading the written files back; no gate run
(per `Gate: none`).

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

**As built (2026-10-31):** all registrations landed as planned; no divergence worth a `D<n>` (the plan's
"four cloud-attack skills" for `penetration-tester` is read, per §5's own wording, as the four *offensive
cloud* skills — `cloud-recon-enumeration` + the three `cloud-attack-*` — matching the four paths added to
`penetration-testing`'s `skills[]`). Edited files/blocks:
- `.claude-plugin/marketplace.json` — `penetration-testing.skills[]` now lists the four offensive cloud
  paths (`.claude-plugin/marketplace.json:1208-1211`), `security-governance.skills[]` adds
  `./security/cloud-incident-response` (`.claude-plugin/marketplace.json:1248`); both plugin
  **descriptions** extended with one dense cloud clause each (pen-test cloud lane at line 1182;
  sec-gov "Five language-agnostic skills" + cloud-IR clause at line 1226). JSON validates.
- `security/agents/penetration-tester.md` — cloud lane added to the skill-loading protocol (`:49`) and the
  ATT&CK spine note keyed to Enterprise-vs-Cloud by surface (`:39`).
- `security/agents/security-architect.md` — `cloud-incident-response` added to the governance skills
  bullet ("Five governance skills", `:38`) and to Step 4's loads (`:63`).
- `security/agents/security-test-planner.md` — routing catalog gains a "Cloud control-plane pentest" row
  (executor `penetration-tester`, the four offensive cloud skills) and a "Cloud incident response" row
  (executor `security-architect`, `cloud-incident-response`), and `cloud-incident-response` added to the
  governance roll-up row (`:40-42`). All five names verified to resolve to on-disk skill dirs.
- `docs/skills-catalog.md` — new "cloud offensive lane — 4 skills" paragraph after the 7-skills list,
  penetration-tester "Loads" line updated, and `security-governance` paragraph bumped to "Five … a sixth"
  with the `cloud-incident-response` clause.
- `CLAUDE.md` — `security/` repository-map row now names the cloud-pentest + cloud-IR/BCDR lanes (`:257`).
- Command count unchanged at 65 (no commands added); catalog's "65 command files, 73 registrations" line
  left as-is. G1's prompt block needed no rewrite — its gate reads this note for the registered names and
  all its assumptions (descriptions name the skills, catalog/CLAUDE.md reconcile with disk, count 65) hold.

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

**As built (2026-10-31):** the five §4 cross-references are wired into the existing skills, each in that skill's own Cross-references voice:
- `devops/cloud-posture/SKILL.md:245` — bullet pointing at `cloud-recon-enumeration` + `cloud-attack-{aws,azure,gcp}` as the offensive counterpart (posture↔exploitation handoff).
- `devops/threat-modeling/SKILL.md:142` — bullet routing a high IaaS threat to `cloud-recon-enumeration` + the provider skills, as the exploitation counterpart to the posture pass.
- `devops/iac-security/SKILL.md:480` — "Cloud application security (M12)" note (per research `06-devsecops-appsec.md` §6): this is the cloud-app-security IaC/config lane; image→`qa-*:image-infra-scan`, signing/SBOM/SLSA→`supply-chain-security`, SAST/DAST/SCA→`qa-*` lanes.
- `security/detection-engineering/SKILL.md:128` — bullet naming `cloud-incident-response` as the consumer of this authoring half (cloud detections authored/tested here, validated by `purple-team-engineer`).
- `security/compliance-evidence-mapping/SKILL.md:44-45` (two BCDR register rows) + `:84` (cross-ref pointer) — SOC 2 **A1.2/A1.3** · ISO 27001:2022 **A.5.29/A.5.30** · NIST CSF 2.0 **RECOVER (RC.RP/RC.CO)** → `security/cloud-incident-response/references/cloud-resilience.md`, wording from research `08-grc-bcdr.md` §"BCDR → compliance crosswalk".

Gate (§5a) run and **green**: `marketplace.json` parses; all five skills have `SKILL.md` with `---` frontmatter; both plugin descriptions name the new skills; command count still **65**; all intra-repo cross-ref targets (incl. `cloud-resilience.md`) resolve; `CLAUDE.md:257` + `docs/skills-catalog.md` reconcile with the five `security/cloud-*` dirs on disk. **Nothing needed fixing** — all of C1–W1 landed consistent with the gate. One tooling note: the §5a loop's `grep -qx '---'` is rejected by BSD/macOS grep (reads `---` as flags); re-run with `grep -qxe '---'` it passes — a portability quirk in the gate snippet, not a skill defect.

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

**D7 — A3 patterned against C1, not A2, because A2 had not landed yet (2026-10-31).** A1/A2/A3/B1 are
independent of each other by design (each depends only on C1), so the queue is free to run them in any
order; A3 ran before A1/A2. Its prompt named A2's SKILL.md as the sibling pattern to read, but that file
did not exist at run time. A3 used `security/cloud-recon-enumeration/SKILL.md` (C1 — the one skill in the
lane that had actually landed) as the sibling pattern instead, which already carries the frontmatter
shape, the `#volatile` authorization block, and the ATT&CK-Cloud framing every provider skill shares.
Cost: A3's prose was not cross-checked against A1/A2's actual phrasing for provider-specific idiom
(e.g. how each skill names its own "Not in <task>" fence); accepted because the shared shape comes from
C1 either way, and G1's §5a gate is the first point the three provider skills are cross-checked against
each other regardless of authoring order.

**D8 — BCDR crosswalk entered as two register rows, not one (2026-10-31).** §4 named "a BCDR crosswalk
row"; G1 added **two** rows to `compliance-evidence-mapping`'s evidence register — A1.2 (recovery
capability built) and A1.3 (recovery proved by drill). Reading: the research corpus (`08-grc-bcdr.md`
§"BCDR → compliance crosswalk" and its notes) is explicit that A1.2/A1.3 stay two rows because "A1.2 =
you built the recovery capability; A1.3 = you proved it works" and the drill (A1.3) is the row that
generates audit exceptions — collapsing them would hide the gap the whole crosswalk exists to surface.
Cost: one extra register row; accepted because it matches the research the §4 line summarized and keeps
the `#partial`/`#gap` status tiering honest. ISO A.5.29/A.5.30 and NIST CSF RECOVER are carried across
those two rows as §4 specified.

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

