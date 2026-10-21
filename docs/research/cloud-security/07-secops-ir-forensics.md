# 07 — Cloud Security Operations, Incident Response & Forensics

**Scope.** Research corpus for course module **M13 — Cloud Security Operations & Incident Response (deep dive)**. Feeds authoring of the skill `security/cloud-incident-response`. Defensive / blue-team engineering on **owned** environments only.

**Fence (what this skill owns vs. consumes).** `security/cloud-incident-response` owns **RESPOND** and **RECOVER** — triage, containment, eradication, recovery, and the forensic acquisition that supports them. It does **not** author detections: writing detection logic (SIEM rules, GuardDuty/Sentinel/SCC tuning, ATT&CK coverage) is `security/detection-engineering`; proving a detection fires is `security/detection-validation`. This skill **consumes** their output — it assumes the alert already fired and a signal already exists — and hands post-incident telemetry and metrics back to `observability` (OTel → Grafana/Loki/Tempo). When a runbook step depends on a detection, it names the handoff rather than writing the rule.

---

## Cloud monitoring & logging

Three planes to log in every cloud: **control plane** (who called which API), **network plane** (what traffic flowed), **detection plane** (which managed analytics flagged something). Map each cloud's sources to the question it answers, then centralize.

### Log-source map (three clouds)

| Plane / question | AWS | Azure | GCP |
|---|---|---|---|
| **Control plane** — "who did what in the account/tenant" | **CloudTrail** (management events on by default, 90-day Event History; durable retention needs a trail → S3, or **CloudTrail Lake**). Each event carries caller identity, API, source IP, params, time. Data events (S3 object, Lambda) are opt-in and high-volume. | **Azure Activity Log** (subscription-level control-plane ops: Authorization, Compute, Storage categories) + **Entra ID audit logs** (directory/user/group/app changes) | **Cloud Audit Logs — Admin Activity** (always on, cannot be disabled/excluded) + **System Event** (Google-initiated config changes) + **Policy Denied** (VPC-SC / Org Policy denials) |
| **Identity / sign-in** — "who authenticated, from where, under what risk" | CloudTrail `ConsoleLogin` + IAM events; IAM Access Analyzer | **Entra ID sign-in logs** (interactive + non-interactive, service-principal, managed-identity sign-ins; Identity Protection risk events). Sign-in ingestion needs **Entra ID P1/P2** | Cloud Audit Logs + **Cloud Identity** logs |
| **Network plane** — "what traffic moved to/from my resources" | **VPC Flow Logs** (ENI/subnet/VPC level) + **Route 53 Resolver DNS logs**. AWS's "logging trifecta" = CloudTrail + Flow Logs + DNS logs | **NSG Flow Logs / VNet Flow Logs** + **Network Watcher** (packet capture) | **VPC Flow Logs** + **Firewall Rules Logging** + Cloud DNS logging |
| **Data-access plane** — "who read/wrote the data" | CloudTrail **data events** (S3, DynamoDB, Lambda) | Entra ID + resource diagnostic logs; Storage analytics | **Cloud Audit Logs — Data Access** (configurable, off by default, cost-bearing; enable Data Read/Write per API, e.g. IAM, STS, SCC) |
| **Detection plane** — "is this malicious/anomalous" | **GuardDuty** (ML + threat intel over CloudTrail, Flow Logs, DNS; reads its own independent copy — does not touch your config). **Attack-sequence** findings correlate multiple actions. **Security Hub** aggregates findings (ASFF). **Amazon Detective** builds a behavior graph for investigation | **Microsoft Defender for Cloud** (CSPM + workload protection) + **Defender XDR** (endpoint/identity/cloud-app). **Microsoft Sentinel** = cloud-native SIEM/SOAR | **Security Command Center** (SCC — Standard/Premium/**Enterprise**); findings from Event Threat Detection, Container Threat Detection, Security Health Analytics, VM Threat Detection |
| **Metrics / app logs** — "is it healthy, what did the app emit" | **CloudWatch** Logs + Metrics (also the delivery/alerting layer; metric filters → alarms) | **Azure Monitor** + **Log Analytics workspace** (KQL) | **Cloud Monitoring** + **Cloud Logging** (Logs Explorer) |

### What each detection service actually answers
- **GuardDuty** — continuous anomaly/threat findings (crypto-mining, C2 DNS, credential exfil, recon). Feb 2025: IAM finding type for restricted-credential misuse; attack-sequence findings. Foundational sources: CloudTrail, VPC Flow Logs, DNS logs; optional: EKS audit, S3, RDS, Lambda, Runtime Monitoring (eBPF agent).
- **Amazon Detective** — not a detector; an **investigation** tool. Ingests CloudTrail + Flow Logs + GuardDuty findings (and EKS audit, and raw logs from **Security Lake**) into a linked behavior graph; Feb 2025 added timeline layout + playback + severity filter.
- **Microsoft Sentinel** — SIEM/SOAR on a Log Analytics workspace (KQL); UEBA, analytics rules, playbooks (Logic Apps). **Portal transition:** Microsoft is moving Sentinel into the **unified Defender portal** (security operations experience); as of 2026 the migration is not fully complete — SigninLogs and workbooks/connectors still live in the Log Analytics workspace. Author runbooks to both the Azure portal and Defender portal paths.
- **SCC** — posture + threat findings aggregator for GCP; Enterprise tier adds SIEM/SOAR (Chronicle-backed) and case management.

### Centralization (the single pane)
- **AWS** — org-wide CloudTrail → central S3 (separate **log-archive / security-tooling account**, Control Tower pattern); GuardDuty + Security Hub delegated-admin aggregation; **Security Lake** normalizes to OCSF in S3 for cross-source query (Athena/OpenSearch). Cross-account roles for the forensics account.
- **Azure** — diagnostic settings route Activity Log, Entra logs, resource logs → a central **Log Analytics workspace**; Sentinel sits on it; multi-workspace / Azure Lighthouse for MSSP/central SOC.
- **GCP** — **aggregated log sinks** at the org/folder level → central logging project (BigQuery for analytics, GCS for cold/immutable retention, Pub/Sub for streaming to external SIEM); SCC at org scope.
- **Cross-cloud** — ship all three to one SIEM (Sentinel, Splunk, Elastic, Chronicle) normalized to a common schema (OCSF/ECS). Logs that feed IR must be in an account/project the attacker does not control and under **immutable/WORM** retention with legal hold.

---

## Cloud IR lifecycle

NIST frames the phases; cloud changes the mechanics, not the goals.

### Framework anchors
- **NIST SP 800-61r3** (final **2025-04-03**) — *Incident Response Recommendations and Considerations for Cybersecurity Risk Management: A CSF 2.0 Community Profile*. **Supersedes 800-61r2.** Drops the r2 five-stage cycle (Preparation → Detection & Analysis → Containment/Eradication/Recovery → Post-Incident) and maps IR onto the six **CSF 2.0 functions**: **Govern, Identify, Protect, Detect, Respond, Recover**. r2's phased language is still widely used operationally.
- **SANS PICERL** — Preparation, Identification, Containment, Eradication, Recovery, Lessons learned. The operational spine most runbooks still follow.
- This module uses the operational pipeline **detect → triage → contain → eradicate → recover** (with Prepare/Govern as the standing precondition and Lessons-learned as the close-out).

### Detect
Alert already fired (owned by detection-engineering). This skill's job: confirm it's real and pull the first-order context. Pull the GuardDuty/Sentinel/SCC finding, the triggering CloudTrail/Activity/Audit events, the identity involved, and the resource graph (Detective behavior graph / Sentinel investigation graph / SCC finding → asset).

### Triage
Scope and severity before touching anything. Answer: which **identities**, which **resources**, which **data**, what **blast radius** (what else that principal/role can reach). Build the timeline from control-plane logs. Decide: credential compromise, workload compromise, or exposure. **Preserve evidence before any destructive step** — triage is where you decide snapshot order, not where you terminate.

### Contain — *this is where cloud differs most*
Containment is **API-driven and near-instant**, and it can be done without touching the host. Patterns:
- **Isolate by network** — replace the instance's **security group** (AWS) / **NSG** (Azure) / **firewall tags + deny-all rule** (GCP) with a forensic quarantine group that allows only the analyst/collection path. No host login required.
- **Isolate by IAM** — the cloud-native move with no on-prem analog: **revoke/deny the compromised principal** rather than firewalling a box. Attach an explicit **deny-all policy** to the user/role, **rotate or deactivate access keys**, revoke active **STS sessions** (AWS: `aws iam put-user-policy` deny + `DeleteAccessKey` + revoke-older-than session policy; Azure: disable user, **revoke Entra sessions / refresh tokens**, remove role assignments; GCP: lift IAM bindings, disable service-account keys, `gcloud iam service-accounts disable`). Containing the **identity** often beats containing the **host**, because the credential works from anywhere.
- **Snapshot-before-anything-destructive** — take the disk snapshot (and memory) **before** stop/terminate. Evidence in cloud is **ephemeral**: a terminated instance's instance-store and un-snapshotted state is gone, auto-scaling may replace the box, and spot reclamation can delete it out from under you.
- **Disable auto-remediation / disconnect from orchestration** — detach from Auto Scaling group, deregister from the load balancer/target group, remove from the service mesh so a "healthy" replacement isn't spun up and the evidence host isn't recycled.
- **Preserve, don't power off** — `stop` (not `terminate`) when you must halt; enable **termination protection** and set **shutdown behavior = stop**; disable **DeleteOnTermination** on attached volumes so containment doesn't wipe evidence.

What's different vs on-prem, summarized: no physical access and no need for it; containment is a config API call; the unit of containment is often the **credential/role**, not the cable; and the environment is **mutable and ephemeral** — infra may heal or vanish, so acquisition precedes containment-by-termination.

### Eradicate
Remove the foothold: rotate **all** potentially exposed secrets (not just the one seen used — assume lateral key access), delete attacker-created IAM users/roles/keys/service accounts, remove malicious Lambda/Functions/Cloud Functions, inbound rules, backdoor AMIs/images, scheduled tasks, and persistence (new OAuth app registrations, federated IdP trust, resource-policy grants to external accounts). Validate IaC/pipeline wasn't the entry (poisoned Terraform/CI). Rebuild from known-good images rather than cleaning in place.

### Recover
Restore from clean snapshots/images **predating** compromise; rebuild via IaC into a clean account/subscription/project where feasible; re-enable traffic in stages with heightened monitoring; confirm the detection that fired is now tuned/covered (handoff to detection-engineering/validation). Watch for re-compromise from unrotated credentials.

### Lessons learned / close-out
Timeline, root cause, dwell time, what detection gap existed, what containment was slow. Feed metrics to `observability`; feed detection gaps to `detection-engineering`; update runbooks.

---

## Cloud forensics

Goal: defensible, reproducible acquisition of evidence from a mutable, API-driven, multi-tenant environment where you never hold the physical media.

### Evidence types
1. **Disk / volume** — point-in-time block snapshot (most common, well-supported).
2. **Memory (RAM)** — volatile; captures running processes, injected code, open sockets, decrypted secrets, keys. No hypervisor dump available to tenants — you capture from **inside** the guest.
3. **Logs** — control-plane, network, data-access, app; often the *primary* evidence in cloud because the host may be ephemeral.
4. **Cloud metadata / config** — instance metadata, IAM policies, resource config, snapshots-of-config (AWS Config, Azure Resource Graph, GCP asset inventory).
5. **Container/serverless artifacts** — container filesystem layers, running container memory, Lambda/Function invocation logs and deployment packages (no persistent host).

### Order of volatility (cloud-adapted; RFC 3227 lineage)
Capture most-perishable first:
1. **CPU/cache/registers** — effectively uncapturable by tenants (theoretical tier).
2. **RAM** — capture **before** any network isolation or process termination; isolation/termination destroys it.
3. **Network state** — active connections, ARP, routing, listening sockets (grab with the memory image via live tools).
4. **Running process/ephemeral state** — instance-store volumes, tmpfs, container-writable layer.
5. **Disk / persistent volume** — snapshot (durable; take after memory because heavy disk I/O can evict in-memory evidence).
6. **Cloud logs / config** — most durable (already externalized), but still export to an immutable store with legal hold before any retention window lapses.

Cloud twist: **logs may outlive the host**, so log preservation is not "last because least volatile" — it's "preserve early because retention windows expire and attackers delete." And **memory is harder in cloud** (no hypervisor introspection for tenants) while **disk is easier** (one API call).

### Acquisition per cloud

**AWS (EC2/EBS).** AWS Security IR User Guide fixed order: **metadata → protections/tags → EBS snapshot → memory**.
- Protect: enable termination protection, set shutdown = stop, disable DeleteOnTermination.
- Disk: `aws ec2 create-snapshot` (or `create-snapshots` for multi-volume, crash-consistent); copy the snapshot into the **forensics account** and re-encrypt with a **forensics-account KMS CMK**; create a volume from it and attach to a hardened analysis instance. Snapshots capture only what's written to the volume — they **miss RAM-cached data**, hence memory is a separate step.
- Memory: avoid interactive SSH (destroys volatile artifacts); use **SSM Run Command** with **LiME** (Linux) / **WinPmem** (Windows) to capture to S3 without an interactive session.
- Isolation for acquisition: swap to a quarantine SG, detach from ASG, deregister from LB, tag `quarantine` + ticket id (tag can trigger automation).

**Azure (managed disk).** 
- Disk: create a **snapshot of the managed OS/data disk** (`az snapshot create`), copy to an isolated forensics resource group/subscription, generate a disk from it for analysis. Prefer snapshot-before-remediation.
- Memory + packet: OS-native memory dump from inside the guest; **Network Watcher** for packet capture.
- Preserve: export logs to **immutable storage with legal hold**; hash evidence for chain of custody. Microsoft Cloud Security Benchmark IR controls name VM disk snapshot + OS memory dump + network flow logs as the evidence set; Sentinel for case management; a **Sentinel playbook** can automate snapshot + immutable export + hashing + evidence record.
- Investigate: triage in the Sentinel incident, pivot to **Defender XDR** for deep investigation.

**GCP (persistent disk).**
- Disk: `gcloud compute disks snapshot` the attached persistent disk → create a new disk from the snapshot → attach to a **forensic workstation in an isolated VPC** (dedicated project).
- Isolation: swap **network tags** + apply deny-all firewall rules (leave an analyst-IP exemption).
- Memory / live: **GRR Rapid Response** for remote live forensics incl. memory retrieval; LiME inside the guest.
- Preserve: export Cloud Audit Logs to a sink (GCS immutable bucket / BigQuery); SCC + Cloud Audit Logs for situational awareness.

### Chain of custody (cloud specifics)
- Document every acquisition step, operator, timestamp (UTC), and command/API call. Record the **snapshot ID, source volume/disk ID, account/subscription/project, region, and KMS/key used**.
- **Hash** acquired images (SHA-256) at acquisition and verify after copy; store hashes with the evidence record.
- Move evidence to a **dedicated, access-controlled forensics account/subscription/project** separate from production and from the attacker's reach; re-encrypt with a forensics-owned key; apply **object-lock / immutable + legal hold**; restrict access with least-privilege IAM and log all access to the evidence store itself.
- Prefer **automated, logged** acquisition (SSM/playbook/`cloudforensics` CLI) over interactive sessions — it's reproducible and self-documenting, and it avoids polluting volatile state.

---

## IR runbooks

Skeletons an engineer follows under pressure. Each assumes the alert already fired (detection-engineering) and that acquisition precedes any destructive step.

### Runbook A — Compromised credential / identity
**Trigger:** GuardDuty IAM finding / Entra risky sign-in / SCC Event Threat Detection anomalous IAM grant.
1. **Triage** — enumerate what the principal can reach (blast radius): IAM policies, role assumptions, resource access. Build the timeline from CloudTrail / Entra sign-in + Activity / Cloud Audit Logs.
2. **Contain the identity (fast):**
   - AWS: attach explicit **deny-all** inline policy to the user/role; `DeleteAccessKey` / deactivate; apply a revoke-sessions policy (deny `aws:TokenIssueTime` older than now) to kill live STS sessions.
   - Azure: **disable the Entra user**; **revoke sessions / refresh tokens**; remove role assignments; rotate app/client secrets.
   - GCP: remove IAM bindings; `gcloud iam service-accounts disable`; disable/rotate SA keys.
3. **Eradicate** — delete attacker-created principals/keys/roles, external trust grants, OAuth app consents; rotate **all** related secrets (assume lateral exposure).
4. **Recover** — reissue least-privilege credentials; enforce MFA/Conditional Access; monitor for reuse.
5. **Close-out** — root cause (phished? leaked key in repo? SSRF→metadata?), detection gap → detection-engineering.

### Runbook B — Compromised instance / workload
**Trigger:** GuardDuty EC2/Runtime finding / Defender for Servers alert / SCC VM Threat Detection.
1. **Preserve first (order of volatility):** capture **memory** via SSM+LiME / WinPmem (AWS), guest memory dump (Azure), GRR/LiME (GCP) — **before** isolation. Then **snapshot the disk** (EBS / managed disk / persistent disk).
2. **Protect the evidence:** copy snapshot to the forensics account/project, re-encrypt with forensics key, hash, legal-hold.
3. **Contain:** swap to quarantine SG/NSG/firewall-tags (analyst path only); detach from ASG/scale set/MIG; deregister from LB; **stop (not terminate)** with termination protection on.
4. **Eradicate:** do not clean in place — rebuild from known-good image; identify persistence (cron/systemd/startup scripts, backdoor images, injected packages).
5. **Recover:** redeploy clean via IaC; re-enable traffic staged; heightened monitoring.
6. **Close-out:** timeline from disk+memory+logs; was it an exposure (Runbook C) or credential (Runbook A) root cause.

### Runbook C — Public exposure (data / resource)
**Trigger:** public S3 bucket / open NSG 0.0.0.0/0 / public GCS / exposed DB / Security Hub/Defender/SCC posture finding.
1. **Triage** — confirm exposure and whether it was accessed: S3 data events / access logs, Flow Logs, Audit Data-Access logs. Determine data sensitivity and whether exfil occurred.
2. **Contain** — remove public access **immediately** (bucket policy/Block Public Access; tighten NSG/firewall; revoke public IAM/ACL grants) — this is a one-call config change; preserve the prior config first (export the policy/ruleset as evidence).
3. **Preserve** — snapshot access logs and config state (AWS Config / Resource Graph / Asset Inventory) to immutable storage; hash.
4. **Eradicate** — fix the IaC/pipeline that produced the exposure (root cause is usually drift or a bad template); add a guardrail (SCP / Azure Policy / Org Policy) to prevent recurrence.
5. **Recover / notify** — assess breach-notification obligations if data was accessed; close with a preventive control, not just a fix.

---

## Tools

| Tool | Purpose | Invocation | What it answers | Reference file |
|---|---|---|---|---|
| **libcloudforensics / cloud-forensics-utils** (Google; PyPI `libcloudforensics`, latest 2024-10-18) | Cross-cloud forensic acquisition + containment library/CLI; AWS/Azure/GCP modules (EBS/EC2/KMS/S3; az compute/network/storage; gcp compute/storage/logging) | `cloudforensics {aws\|az\|gcp} <verb>` — e.g. make-volume-copy, quarantine (deny-all FW + analyst-IP exempt), copy snapshot cross-account | "acquire this disk/instance and isolate it, reproducibly and logged" | gcp-ir.md / aws-ir.md / azure-ir.md |
| **AWS native snapshot APIs** | Disk acquisition | `aws ec2 create-snapshot(s)`, copy + re-encrypt with forensics CMK | "point-in-time block image of the volume" | aws-ir.md |
| **SSM Run Command + LiME/WinPmem** | Non-interactive memory capture | SSM document runs collector → S3 | "what was in RAM without an interactive login" | aws-ir.md |
| **Amazon GuardDuty** | Managed threat detection (consumed, not authored here) | Findings → EventBridge → Lambda/runbook | "is this host/account doing something malicious" | aws-ir.md |
| **Amazon Detective** | Investigation behavior graph (CloudTrail+Flow+GuardDuty, +Security Lake, +EKS) | Pivot from a GuardDuty finding | "what's the blast radius and timeline of this principal/resource" | aws-ir.md |
| **AWS Security Hub / Security Lake** | Finding aggregation (ASFF) / OCSF log lake | Delegated-admin aggregation; Athena over Security Lake | "one normalized view across sources" | aws-ir.md |
| **Azure native snapshot** | Managed-disk acquisition | `az snapshot create` → copy to forensics RG/sub | "block image of the managed disk" | azure-ir.md |
| **Network Watcher** | Packet capture / flow logs | Capture session on the NIC | "what traffic the VM sent/received" | azure-ir.md |
| **Microsoft Sentinel** | Cloud SIEM/SOAR, case mgmt, playbooks | KQL hunting; Logic App playbook (snapshot+export+hash) | "correlate, investigate, and automate response" | azure-ir.md |
| **Defender for Cloud / Defender XDR** | Posture + workload protection; deep investigation | Triage in Sentinel → pivot to Defender portal | "what the alert means across endpoint/identity/cloud" | azure-ir.md |
| **GCP native snapshot** | Persistent-disk acquisition | `gcloud compute disks snapshot` → new disk → isolated VPC | "block image of the PD" | gcp-ir.md |
| **GRR Rapid Response** | Remote live forensics incl. memory | GRR agent/flow | "live memory and artifacts off a running GCE VM" | gcp-ir.md |
| **Security Command Center** (Standard/Premium/Enterprise) | Posture + threat findings aggregator; Enterprise adds SIEM/SOAR/case mgmt | SCC console; findings → Pub/Sub → runbook | "what's exposed and what threats fired in this org" | gcp-ir.md |
| **Cloud Audit Logs + aggregated sink** | Log preservation | Org sink → immutable GCS / BigQuery | "who did what, preserved and queryable" | gcp-ir.md |

Planned reference files for the skill: **`references/aws-ir.md`**, **`references/azure-ir.md`**, **`references/gcp-ir.md`**.

---

## How it feeds our skill

Target: `security/cloud-incident-response/SKILL.md`.

| Research section | SKILL.md section it seeds | Reference file |
|---|---|---|
| Fence (owns RESPOND+RECOVER; consumes detection) | SKILL front-matter + "When to use / not use" | — |
| Cloud monitoring & logging | "Know your telemetry" preconditions (what must already be logged) | per-cloud files |
| Cloud IR lifecycle | Core procedure: detect→triage→contain→eradicate→recover, cloud-vs-onprem callouts | aws/azure/gcp-ir.md |
| Cloud forensics | "Acquire before you destroy" + order-of-volatility + chain-of-custody checklists | aws/azure/gcp-ir.md |
| IR runbooks | Three runbook skeletons (credential / instance / exposure) as the operational core | aws/azure/gcp-ir.md |
| Tools | Tool table + CLI invocations (`cloudforensics`, native snapshot APIs) | all three |

**Handoffs named in the skill:**
- **← detection-engineering** — the skill assumes the detection exists; when a runbook hits a detection gap at close-out, it files back here (writes no rules itself).
- **← detection-validation** — the skill trusts that fired detections were validated; it does not re-prove them.
- **→ observability** — post-incident metrics (dwell time, MTTR, containment latency) and telemetry flow to the OTel→Grafana/Loki/Tempo lane; immutable log retention is a shared precondition.
- **Boundary with `penetration-testing`/`security-governance`** — red-team produces the attack; governance owns policy/guardrails (SCP/Azure Policy/Org Policy) that eradication/recovery steps reference but do not author.

---

## Sources

- NIST SP 800-61r3 (final 2025-04-03), *Incident Response Recommendations… CSF 2.0 Community Profile* — https://csrc.nist.gov/pubs/sp/800/61/r3/ipd ; https://www.nist.gov/news-events/news/2025/04/nist-revises-sp-800-61-incident-response-recommendations-and-considerations
- libcloudforensics — https://libcloudforensics.readthedocs.io/ ; https://pypi.org/project/libcloudforensics ; GCP quarantine module — https://libcloudforensics.readthedocs.io/en/stable/source/libcloudforensics.providers.gcp.html
- AWS Security Incident Response User Guide (collect artifacts; select/enable log sources) — https://docs.aws.amazon.com/security-ir/latest/userguide/collect-relevant-artifacts.html ; https://docs.aws.amazon.com/security-ir/latest/userguide/select-and-enable-log-sources.html
- AWS Well-Architected Security Pillar SEC04-BP01 (service/app logging) — https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_detect_investigate_events_app_service_logging
- GuardDuty foundational data sources — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_data-sources.html
- Amazon Detective (what is / doc history, Feb 2025 timeline + Security Lake + GuardDuty IAM finding) — https://docs.aws.amazon.com/detective/latest/userguide/what-is-detective ; https://docs.aws.amazon.com/detective/latest/userguide/doc-history.html
- ISC2 — logging the right AWS log sources — https://www.isc2.org/insights/2025/02/logging-the-right-aws-log-sources
- Microsoft Cloud Security Benchmark — Incident Response controls — https://learn.microsoft.com/en-us/security/benchmark/azure/security-controls-v3-incident-response
- Microsoft Learn — Respond to an incident (Zero Trust; Sentinel→Defender XDR) — https://learn.microsoft.com/en-us/security/zero-trust/respond-incident-azure
- Microsoft Entra ID connector for Sentinel (audit + sign-in log types, tables, licensing) — https://learn.microsoft.com/en-us/azure/sentinel/data-connectors/microsoft-entra-id ; UEBA reference (Azure Activity) — https://learn.microsoft.com/en-us/azure/sentinel/ueba-reference
- GCP Cloud Audit Logs overview (Admin Activity always-on; Data Access; System Event; Policy Denied) — https://docs.cloud.google.com/logging/docs/audit
- Cado Security — GCP / Azure incident response & forensics wikis — https://www.cadosecurity.com/blog/updated-guide-incident-response-in-gcp ; https://www.cadosecurity.com/wiki/azure-incident-response-a-comprehensive-guide-for-cloud-security
- OneUptime — GCP cloud forensic investigation & evidence preservation (gcloud snapshot/isolation commands) — https://oneuptime.com/blog/post/2026-02-17-how-to-perform-cloud-forensic-investigation-and-evidence-preservation-on-google-cloud/markdown
- RFC 3227 order-of-volatility guidance (secondary) — AWS Security Specialty forensic acquisition study notes — https://open-exam-prep.com/study-guides/aws-security-specialty-c03/digital-forensics-root-cause/forensic-evidence-acquisition
- GRR Rapid Response in GCP automated IR (Spotify Eng, 2019, historical) — https://engineering.atspotify.com/2019/4/whacking-a-million-moles-automated-incident-response-infrastructure-in-gcp
