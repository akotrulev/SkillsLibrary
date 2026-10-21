# Cloud security knowledge base (2026-10-21)

Research corpus for the cloud security lane — the raw material the skill-authoring tasks of
[`docs/plans/008-cloud-security-lane.md`](../../plans/008-cloud-security-lane.md) draw on. Built from a
14-module cloud-pentest / cloud-security course, grouped into eight areas that map onto the plan's
skills. Every file is web-verified (tool repos, current product names, framework versions) and framed
for authorized self-testing / lab training only: owned accounts, expiring authorization, loot as
blast-radius-never-values, detection-awareness-not-evasion, no DoS.

## Files → modules → the skill they feed

| File | Course modules | Feeds (plan 008) |
|---|---|---|
| [`01-foundations.md`](01-foundations.md) | M1–M4: concepts, shared responsibility, IAM, network/data security | cross-refs + `cloud-recon-enumeration` context |
| [`02-pentest-methodology-recon.md`](02-pentest-methodology-recon.md) | M5: cloud pentest methodology, recon/enum, tooling | **C1** `cloud-recon-enumeration` |
| [`03-aws.md`](03-aws.md) | M6–M8: AWS fundamentals → privesc, RDS, Pacu/ScoutSuite | **A1** `cloud-attack-aws` |
| [`04-azure.md`](04-azure.md) | M9–M10: Entra ID, Key Vault, RBAC, Azure services | **A2** `cloud-attack-azure` |
| [`05-gcp.md`](05-gcp.md) | M11: hierarchy/IAM, SA impersonation, enum, testing | **A3** `cloud-attack-gcp` |
| [`06-devsecops-appsec.md`](06-devsecops-appsec.md) | M12: cloud app security, DevSecOps, CI/CD, SAST/DAST/SCA/IaC | cross-refs (library already owns these) |
| [`07-secops-ir-forensics.md`](07-secops-ir-forensics.md) | M13: monitoring/logging, detection, cloud IR, forensics | **B1** `cloud-incident-response` |
| [`08-grc-bcdr.md`](08-grc-bcdr.md) | M14: governance, risk, compliance, BCDR, case studies | **B1** `references/cloud-resilience.md` + cross-refs |

Each file follows the same shape: scope → core concepts → techniques (or controls) → a tools table
(tool · purpose · invocation · what it answers · which `references/<tool>.md` it becomes) → MITRE
ATT&CK Cloud mappings → misconfig taxonomy → owned-lab targets → "how it feeds our skill" → sources.

## Currency ledger — facts newer or sharper than a Jan-2026 baseline

The research corrected or sharpened these; an author must treat them as the current position and, where
noted, make the skill **detect** rather than **assume**:

**Frameworks & standards**
- **NIST SP 800-61 Rev 3 is final (2025-04-03)** and supersedes r2 — IR reframed onto the CSF 2.0
  functions, dropping r2's five-phase cycle. Anchor B1 to both (operators still speak PICERL).
- **NIST CSF 2.0**: GOVERN is the 6th function and sits *central*, not appended; RECOVER restructured
  to two categories (RC.RP, RC.CO); supply-chain risk now under GV.SC.
- **ISO 27001:2022**: Annex A = 93 controls / 4 themes. A.5.29 and A.5.30 (ICT readiness for business
  continuity) are both new-in-2022, no 2013 equivalent — the BCDR crosswalk anchors.
- **CSA CCM v4** = 17 domains / 197 controls; v4↔FedRAMP Rev 5 interim mapping published 2025.
- **SLSA v1.2** (Build track L1–L3; L4 dropped, Source track added) — supersedes the old L1–L4 framing.
- **MITRE ATT&CK v18** (late 2025) expanded cloud identity / CI-CD / cloud-DB coverage — pin the version
  at authoring time.

**Tools (verify-at-deploy, don't pin counts)**
- **Semgrep → Opengrep** (LGPL community fork, early 2025) after the Semgrep license shift.
- **tfsec folded into Trivy** — prefer `trivy config`; legacy rule IDs map to Trivy AVD.
- **ROADrecon `gather` is broken (2025)** by the Azure AD Graph retirement — the Microsoft-Graph
  community fork is the working path; its aiohttp client is detectable.
- **Stormspotter is dormant** (last push ~Jan 2024) → use AzureHound + BloodHound as the Azure graph path.
- **Pacu / CloudFox / CloudGoat rosters keep growing** — reference files say "confirm against the repo at
  authoring time" rather than pinning a module/scenario count.
- **libcloudforensics / cloud-forensics-utils** latest release 2024-10-18; ships the `cloudforensics` CLI
  (aws/az/gcp) + a GCP network-quarantine function.

**Cloud-provider state (make the skill detect, not assume)**
- **GCP Compute default SA** no longer auto-gets Editor + broad scope on new orgs/projects — brownfield
  still carries the old default. A3 must detect, not assume editor-by-default.
- **IMDSv2** is EC2-console default since Nov 2023, but many instances still run IMDSv1-optional
  (dual-accept). F5 Labs reported an **active March-2025 SSRF→IMDSv1 credential-theft campaign** — v1 is
  the live risk where not enforced. Containers need hop-limit 2, which re-widens the SSRF path.
- **Entra ID** (ex-Azure AD, renamed 2023-07) is still current in 2026 — but legacy "Azure AD" persists
  in API/host names (`graph.windows.net`, tool names, MITRE text).
- **Azure Blueprints is deprecated** (retires Jul 2026) → Template Specs + Deployment Stacks + Azure
  Verified Modules.
- **Microsoft Sentinel** is migrating into the unified Defender portal but *not complete* in 2026 — B1
  runbooks cover both the Log Analytics and Defender-portal paths.
- **Google "Cloud Functions" → "Cloud Run functions"** (1st/2nd-gen folded into Cloud Run).

**Cross-cloud asymmetries authors must not flatten**
- **Azure Key Vault** holds keys + secrets + certs in one service; AWS/GCP split KMS from Secrets
  Manager.
- **GCP VPCs are global** (subnets regional); AWS/Azure networks are regional — changes segmentation.
- **GCP service accounts are both an identity and a resource**, so `iam.serviceAccounts.actAs` is itself
  an escalation lever with no AWS analog.
- **GCP Admin Activity audit logs are always-on and cannot be disabled**; Data Access logs are
  off-by-default and cost-bearing.

**Attributions corrected**
- CloudGoat = Rhino Security Labs; IAM Vulnerable = Bishop Fox / Seth Art (~31 privesc paths, 250+
  resources); CloudFoxable = Bishop Fox's CTF-style successor. Rhino's own count is **21** AWS
  privilege-escalation methods (secondary sources inflate to 41).

## Status & caveats

- Research only — no skills authored yet (that is plan 008, tasks C1/A1–A3/B1). Not committed.
- A few items were characterized from repo/aggregator context where primary sources were thin (hayat;
  the full 21-method Rhino AWS list; GCP CFT landing-zone vehicle) — each file flags these for a
  repo/README cross-check when the matching `references/*.md` is written.
- Compliance wording (SOC 2 / ISO / NIST text) should be confirmed against the primary standard before
  any audit use; `08-grc-bcdr.md` carries that note.
