---
name: cloud-posture
description: Use when scanning a live, owned AWS/Azure/GCP account for misconfiguration (CSPM) with Prowler or ScoutSuite. Triggers "scan our AWS account for misconfigurations". Not for IaC (iac-security).
disable-model-invocation: true
---

# DevOps — Cloud Security Posture (Prowler / ScoutSuite)

**Cloud Security Posture Management (CSPM)** reads a **live, deployed cloud account** through its API and scores the *running* configuration against security benchmarks — the misconfigurations that only exist once resources are provisioned: an S3 bucket someone made public last week, a root account with no MFA, an unused IAM key that should have been rotated, a storage account whose encryption was disabled by a console click, a subscription with Activity Log turned off. This is the surface **IaC scanning cannot see** — a clean Terraform plan says nothing about drift, console changes, or resources created outside IaC entirely.

**Prowler** (v5, `prowler-cloud/prowler`) is the primary scanner: one Python CLI, all three clouds (`prowler aws` / `prowler azure` / `prowler gcp`), hundreds of read-only checks mapped to **CIS benchmarks** and dozens of other frameworks, gated by severity and status. **ScoutSuite** (NCC Group) is the companion for a **single self-contained HTML report** an engineer or auditor browses by service. Both are OSS; commercial CSPM (Wiz, Prisma Cloud, Prowler Pro, Defender for Cloud) is noted per provider in `references/`.

This skill is **language-agnostic** (a cloud account has no stack) and owns the **Prowler/ScoutSuite invocation, the read-only credential model, the CIS/OWASP + MITRE ATT&CK Cloud mapping, and the scheduled-scan CI wiring**. It is loaded by the **`infra-security-tester`** agent as its Step-4 cloud-posture pass.

> **Authorization first.** Every command here authenticates to a real cloud account, which is legitimate only as a **read-only self-test of an account you own**, never a third party's. Before any live scan, record who authorized it, the exact account/subscription/project or org scope, and an expiry. It is `#volatile`: never cached in the orientation cache, re-confirmed each engagement. Every posture report carries `Authorization: <cloud scope + who authorized + expiry>` as its first line.

## Decision matrix — Prowler vs ScoutSuite, and what this skill is NOT

| Need | Use | Reads | Spine |
|------|-----|-------|-------|
| **Gate** a CI/scheduled job on cloud misconfig (severity + status filtered, machine output) | `prowler <provider>` | the live cloud API (read-only) | CIS / OWASP |
| Score an account against a **named benchmark** (CIS 3.0, NIST, PCI, SOC2, ISO) | `prowler <provider> --compliance <fw>` | the live cloud API | CIS + compliance |
| A **browsable HTML posture picture** for an engineer/auditor to read by service | `scout <provider>` | the live cloud API | ScoutSuite ruleset |
| **Multi-cloud in one report** (AWS + Azure + GCP side by side) | ScoutSuite per provider, or Prowler per provider + aggregate | the live cloud APIs | — |
| Map a finding to an **adversary technique** | Prowler output → MITRE ATT&CK **Cloud/IaaS** matrix | (post-processing) | ATT&CK Cloud |
| **IaC template** misconfig BEFORE deploy (Terraform/Bicep/ARM/Helm) | **`devops:iac-security`** (Checkov/tfsec) | files on disk | CIS |
| **Running K8s** workloads, RBAC, network policy, pod security | **`devops:kubernetes-security`** (kube-bench/Kubescape) | the K8s API | CIS-K8s |
| **Image / OS-package CVEs**, IaC template CVEs, SBOM | **`qa-<stack>:image-infra-scan`** (Trivy) | the built image / files | A03/A02 |
| Whether a delivery **gate exists in the repo** (static conformance) | **`devops-auditor`** | repo files (read-only) | plugin rules |

Both hit the **live account**, which is the fence against `devops:iac-security` (templates on disk), `qa-<stack>:image-infra-scan` (the image), and `devops-auditor` (repo files, never the account).

## Setup — pin the version, use a venv

```bash
# Prowler v5 — Python CLI. Use Python 3.13 when the pinned release's `requires-python` allows it; Prowler
# lags new Pythons, so otherwise take the newest version it does allow (5.x has capped at 3.12).
python3 -m venv .prowler && source .prowler/bin/activate
pip install prowler==5.38.0          # pin the version — a scanner bump is a reviewable change, not a silent one
prowler --version

# Docker — no install; mount an output dir. Pin the tag, never :stable/:latest.
docker run --rm -v "$PWD/output:/output" prowlercloud/prowler:5.38.0 aws --output-directory /output

# ScoutSuite — separate venv (it pins its own dependency set).
python3 -m venv .scout && source .scout/bin/activate
pip install scoutsuite==5.14.0
scout --help
```

Pin every version (never `:stable` / `:latest`): a new check turning a green run red is then a reviewed bump, not a surprise that gets the scan disabled.

## The read-only credential model — non-negotiable

A posture scan **never needs write access**. Grant the narrowest read-only identity each cloud offers, and in CI reach it via **OIDC / Workload Identity Federation — never a long-lived key** (the library's first infra invariant; a static cloud credential is a blocker finding).

| Cloud | Read-only identity | How Prowler/ScoutSuite reach it |
|-------|-------------------|--------------------------------|
| **AWS** | `SecurityAudit` + `ViewOnlyAccess` managed policies + a small supplementary read policy | Profile / assumed role (`--role`, `-R`); OIDC role in CI |
| **Azure** | `Reader` RBAC + the custom `ProwlerRole` + Graph API `Directory.Read.All`/`Policy.Read.All`/`AuditLog.Read.All` | Service principal env / `--az-cli-auth` / `--managed-identity-auth` |
| **GCP** | `roles/viewer` (project) or `roles/cloudasset.viewer` (org) | Application Default Credentials / service-account key |

Per-provider setup, exact flags, org-wide scanning, and the commercial-tool note live in the references — **read the matching one end-to-end before scanning**:
- `references/aws.md` — Prowler/ScoutSuite on AWS, the `SecurityAudit`+supplementary policy, org-wide role assumption, Defender/Wiz/Prisma notes
- `references/azure.md` — service principal + `ProwlerRole` + Graph permissions, subscription vs tenant scope, Microsoft Defender for Cloud
- `references/gcp.md` — ADC vs service account, project vs org scope, `roles/cloudasset.viewer`, Security Command Center

## The scan commands + gating flags (Prowler)

```bash
# Full posture scan of the default account/subscription/project — every check, all severities.
prowler aws
prowler azure --subscription-ids <sub-id>
prowler gcp --project-ids <project-id>

# Scope to a benchmark — prints the framework breakdown + a dedicated CSV under compliance/.
prowler aws --compliance cis_3.0_aws
prowler azure --compliance cis_2.0_azure
prowler gcp --compliance cis_3.0_gcp

# Discover what's available first.
prowler aws --list-compliance
prowler aws --list-compliance-requirements cis_3.0_aws

# Narrow the run — specific services or checks (faster, targeted retest).
prowler aws --services s3 iam cloudtrail kms
prowler aws --checks s3_bucket_public_access iam_root_mfa_enabled
```

| Flag | Effect |
|------|--------|
| `--compliance <fw>` | Score against a named framework (`cis_3.0_aws`, `cis_2.0_azure`, `cis_3.0_gcp`, `nist_800_53_...`, `pci_4.0_...`, `soc2_aws`) — emits a per-framework CSV under `compliance/` |
| `--severity critical high [medium low]` | Restrict findings to these severities. **Pair with `--status FAIL`** for the gate |
| `--status FAIL` | Report only failing checks (`PASS`/`FAIL`/`MANUAL`) — the actionable set |
| `-M`/`--output-formats csv json-ocsf html` | Output formats. **Native `json` is deprecated → use `json-ocsf`** (OCSF v1.1) for machine consumption; `html` for humans |
| `--output-directory <dir>` / `--output-filename` | Where results land (stamp the date in the dir for a scan trail) |
| `--services` / `--checks` / `--excluded-checks` | Scope the run — a service subset, named checks, or exclusions |
| `-R`/`--role <arn>` · `-O`/`--organizations-role <arn>` | (AWS) assume a role in a member account / the Organizations mgmt account — org-wide scanning |
| `--mutelist-file <yaml>` | The ticketed suppression file (see Triage) |

**The defining trait: Prowler is report-first.** A bare `prowler aws` exits `0` and prints everything. The **gate** is `--severity critical high --status FAIL` plus a wrapper that fails the job when failing findings exist (Prowler's exit codes: `0` = no fails, `3` = failed findings present — gate on `[ $? -eq 3 ]`).

## The two-pass pattern — informational + gating

Same shape as the Trivy gate: one pass that shows everything (never fails), one that gates on what's actionable.

```bash
# Pass 1 — INFORMATIONAL. Every check, HTML + OCSF for the record. Never fails the job.
prowler aws \
  --output-formats html json-ocsf \
  --output-directory "reports/$(date +%F)"

# Pass 2 — GATING. Only Critical/High failures, machine output, fail the job on findings.
prowler aws \
  --severity critical high --status FAIL \
  --compliance cis_3.0_aws \
  --output-formats json-ocsf --output-directory "reports/$(date +%F)/gate"
[ $? -eq 3 ] && { echo "Critical/High cloud-posture findings — see report"; exit 1; }
```

- **Pass 1** is the posture of record — the full picture archived per scan date, so drift is visible run-over-run.
- **Pass 2** is the gate: `--severity critical high --status FAIL` fails only on actionable findings. **Start lenient and ratchet** — `--severity critical` on a legacy account → clear the backlog → tighten to `critical high` (same ratchet as Trivy's `HIGH,CRITICAL` and SCA's CVSS floor).
- **`--compliance`** on the gate pins the run to a named benchmark so the CSV is audit-ready evidence, not just a finding list.

## ScoutSuite — the browsable report

ScoutSuite produces **one self-contained offline HTML report** (`scoutsuite-report/scoutsuite-results/...`), organized by service, colour-coded by severity — the artifact you hand an auditor or browse to understand *shape* rather than gate.

```bash
scout aws --profile security-audit --report-dir "reports/scout/$(date +%F)"
scout azure --cli --report-dir "reports/scout/$(date +%F)"
scout gcp --user-account --project-id my-project --report-dir "reports/scout/$(date +%F)"
```

ScoutSuite has no CI exit-code gate worth building on; use it for the human review and the auditor handoff, and Prowler for pass/fail. The same authorization line covers both.

## The two spines — CIS/OWASP + MITRE ATT&CK Cloud

Every posture finding maps to **two** spines, stated per finding (the library's offensive-lane rule):

1. **CIS cloud benchmarks + OWASP** — the primary CSPM spine. Prowler's `--compliance cis_3.0_aws` / `cis_2.0_azure` / `cis_3.0_gcp` is the canonical mapping; findings also line up with OWASP **A01 Broken Access Control** (over-permissive IAM), **A02 Security Misconfiguration** (public storage, disabled encryption), **A09 Security Logging Failures** (audit logging off).
2. **MITRE ATT&CK — the Cloud/IaaS matrix, NOT enterprise.** The *matrix is keyed to the surface*: a posture weakness maps to the technique it enables in a cloud attack.

| Posture finding | ATT&CK Cloud technique |
|-----------------|------------------------|
| Root/admin without MFA, weak IAM | **T1078.004** Valid Accounts: Cloud Accounts |
| Over-permissive role / privilege path | **T1098** Account Manipulation |
| Public bucket / blob / readable storage | **T1530** Data from Cloud Storage |
| Credentials in metadata / env / unrotated keys | **T1552** Unsecured Credentials |
| Broad describe/list permissions | **T1580** Cloud Infrastructure Discovery · **T1526** Cloud Service Discovery |
| CloudTrail / Activity Log / Audit Logs disabled | **T1562.008** Impair Defenses: Disable/Modify Cloud Logs |

## Triage — ticketed mutelist, gate NEW

Defer the full discipline to the `infra-security-tester` agent (baseline once → gate NEW hard → every suppression carries a ticket + reason + expiry → shrink over time). Prowler's mechanism is a **mutelist** YAML:

```yaml
# mutelist.yaml — scope each entry to a specific check + resource, with a ticket and a re-review date.
Mutelist:
  Accounts:
    "*":
      Checks:
        "s3_bucket_public_access":
          Regions: ["*"]
          Resources: ["public-docs-site-bucket"]   # JIRA-6120: intentional public static site, re-review 2026-11
```

```bash
prowler aws --mutelist-file mutelist.yaml --severity critical high --status FAIL
```

- Scope each entry to a **specific check + resource** — never a blanket "mute all Highs."
- **Prefer the real fix** (make the bucket private, enable MFA, turn on the log) over a suppression. Suppress only documented, ticketed accepted-risk or false-positives, with a re-review date.

## CI wiring

Posture scans run as a **scheduled job in the deploy pipeline** (`devops/github-actions` / `gitlab-ci` / `azure-pipelines`), never the `qa/cicd/*` test lane: the account credentials belong to the deploy context, and posture drifts nightly, not per PR. Read `references/ci-wiring.md` before writing the workflow: the OIDC job, the two passes and the exit-3 gate.

## Rules (hard constraints)

- **Authorization first, owned accounts only**; the report's first line is the `Authorization:` line (blockquote above).
- **Read-only credentials, reached via OIDC / Workload Identity Federation in CI.** A static cloud key or a write-capable scan identity is a **blocker**.
- **Prowler is the gate, ScoutSuite is the read.** Gate on `--severity critical high --status FAIL` plus exit code `3`, pinned to a benchmark with `--compliance cis_3.0_{aws,azure,gcp}`; run the two passes.
- **Triage with a ticketed mutelist** scoped to a specific check + resource, with a re-review date: never a blanket "mute all Highs". Gate NEW findings hard, shrink the file, and prefer the real fix over a suppression.
- **Find and retest; never fix.** `devops-engineer` applies remediation.
- A clean CSPM run ≠ "secure": it means the **account configuration** layer passed (not K8s workloads, image CVEs, app access control, or whether a control fires). Run the full infra layer set.

## Cross-references

- `references/aws.md` · `references/azure.md` · `references/gcp.md` — per-provider invocation, read-only IAM, org-wide scanning and the commercial-tool note. **Read the matching one before scanning.**
- `devops:iac-security` — IaC templates before deploy (the *intended* state); this skill scans the **deployed account** (the *actual* state, incl. drift). Run both.
- `devops:kubernetes-security` — inside the cluster; cloud posture covers the account around it. `devops:container-runtime-security` is the runtime sibling.
- `devops:supply-chain-security` · `devops:threat-modeling` · `devops:controls-validation` — the other infra-security skills `infra-security-tester` orchestrates.
- `qa-<stack>:image-infra-scan` — Trivy for image/OS-package CVEs, IaC-template CVEs and SBOM: the artifact, not the account.
- `security/cloud-recon-enumeration` + `security/cloud-attack-{aws,azure,gcp}` — the **offensive** counterpart: a CSPM finding here (over-permissive role, public bucket, disabled log) is the starting point an engagement enumerates and chains.
- `devops-auditor` — static conformance on repo files; it never authenticates to the account, and this skill never opens the repo's conformance rule set.
- `infra-security-tester` (agent) — runs this as its **Step-4 cloud-posture & IAM** pass. `devops-engineer` applies every fix.
- `data-architect` — owns the cross-tenant leak test that proves data isolation, which the CSPM scan cannot see.
- `observability-engineer-{dotnet,java,node}` — whether the logging controls this scan reports as *enabled* are wired to a backend (a CloudTrail logging to a bucket nobody queries is a posture pass and a detection gap).
