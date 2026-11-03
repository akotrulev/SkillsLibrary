---
name: cloud-incident-response
description: Use when responding to a cloud security incident on AWS, Azure or GCP (triage, forensics, containment, recovery, BCDR). Triggers "we got a GuardDuty alert". Not for detections (detection-engineering).
---

# Security Governance — Cloud Incident Response (runbook · forensics · BCDR)

Cloud incident response starts where detection ends: an alert has already fired — a GuardDuty finding, an Entra risky sign-in, an SCC Event Threat Detection — and the question is no longer *"would we see it?"* but *"is it real, how far does it reach, and how do we get the attacker out without destroying the evidence or the business?"* This skill is the **operational runbook** for that: triage the alert, **acquire forensic evidence before any destructive step**, contain by identity and network, eradicate the foothold, recover from clean backups, and feed the gaps back to the lanes that close them. It is keyed to AWS/Azure/GCP because the goals are identical across clouds but the mechanics — which API isolates a principal, which snapshot command captures a disk — are not.

This skill **owns RESPOND and RECOVER.** It does **not** detect. Writing the detection logic that fires the alert is `security-governance:detection-engineering`; proving that logic actually fires is `purple-team-engineer`'s `detection-validation`; the app-health telemetry substrate (OTel → Grafana/Loki/Tempo) is `observability`; and benchmarking whether the account is *configured* securely before anything happens is `devops:cloud-posture`. This skill **consumes** detection output — it assumes the alert exists and a signal landed — and **hands post-incident metrics back to `observability`** (dwell time, MTTR, containment latency) and **detection gaps back to `detection-engineering`** at close-out. When a runbook step depends on a rule that should exist but doesn't, it names the handoff; it never authors the rule here.

> **Defensive, on owned environments only — no offensive authorization gate, one hard precondition: the telemetry must already exist.** This skill reads logs, snapshots disks, and flips config on **your own** account/subscription/project (or a designated lab). It touches no third party, so unlike the offensive cloud lanes it carries no per-run expiring authorization line. Its load-bearing precondition instead is **the telemetry the response depends on must already be collected and preserved** — control-plane logs (CloudTrail / Azure Activity + Entra audit / Cloud Audit Logs), the detection service (GuardDuty / Defender + Sentinel / SCC), and an **immutable, out-of-band log store** the attacker cannot reach. A response against an account with no durable, attacker-inaccessible logs is reconstruction from memory, not incident response: say so, and route the gap to `observability` / `detection-engineering` rather than pretending coverage.

## The two framework anchors — NIST SP 800-61r3 and PICERL

Both are named deliberately; neither alone is enough.

- **NIST SP 800-61r3** (final **2025-04-03**) — *Incident Response Recommendations… A CSF 2.0 Community Profile*. It **supersedes 800-61r2** and **drops r2's five-stage cycle**, mapping IR instead onto the six **CSF 2.0 functions**: **Govern, Identify, Protect, Detect, Respond, Recover**. This skill lives in **Respond + Recover**, with Govern/Identify/Protect as the standing precondition (the guardrails, the logging, the plan) and Detect owned upstream. Cite r3 — a reference to the retired r2 five-phase model as the current standard is a dated finding.
- **SANS PICERL** — **P**reparation, **I**dentification, **C**ontainment, **E**radication, **R**ecovery, **L**essons-learned. This is the operational spine most runbooks still follow, and the vocabulary responders actually speak under pressure. r3 reframes the *governance* of IR; PICERL still shapes the *runbook*.

This skill uses the operational pipeline **detect → triage → contain → eradicate → recover** (Prepare/Govern as the standing precondition, Lessons-learned as the close-out), and states the r3 function and the PICERL phase each step sits in so both anchors are traceable.

| This skill's step | NIST SP 800-61r3 (CSF 2.0) | SANS PICERL |
|---|---|---|
| Detect (consumed from `detection-engineering`) | DETECT | Identification |
| Triage | RESPOND (RS.MA / RS.AN) | Identification |
| Contain | RESPOND (RS.MI) | Containment |
| Eradicate | RESPOND (RS.MI) | Eradication |
| Recover | RECOVER (RC.RP / RC.CO) | Recovery |
| Lessons-learned / close-out | RECOVER + GOVERN | Lessons-learned |

## The one thing cloud changes — acquire before you destroy

The single rule that reorders every cloud runbook: **cloud evidence is ephemeral, so acquisition precedes any destructive containment step.** A terminated instance's instance-store, un-snapshotted state, and RAM are gone; auto-scaling may replace the box; spot reclamation can delete it out from under you. Containment-by-termination without a prior snapshot destroys the evidence the whole incident turns on. The corollary is the cloud-native containment move with no on-prem analog: **containing the *identity* often beats containing the *host*** — a stolen credential works from anywhere, so revoking the principal (deny-all policy, key deactivation, session revocation) stops the attacker even while the compromised box is left running for acquisition.

**Order of volatility (cloud-adapted, RFC 3227 lineage)** — capture most-perishable first:

1. **RAM** — capture **before** any network isolation or process termination; both destroy it. No tenant hypervisor dump exists — you capture from **inside** the guest.
2. **Network state** — active connections, listening sockets, routing (grabbed with the memory image via live tools).
3. **Running/ephemeral state** — instance-store, tmpfs, container-writable layer.
4. **Disk / persistent volume** — snapshot (durable; take *after* memory, because heavy disk I/O can evict in-memory evidence).
5. **Cloud logs / config** — most durable, but **preserve early anyway**: retention windows expire and attackers delete. In cloud, logs frequently **outlive the host**, so log preservation is not "last because least volatile" — it is "early because perishable for a different reason."

## Know your telemetry — the per-cloud precondition

Before you can triage, the three planes must be logged. This is what the response *reads*; it is `detection-engineering`/`observability`'s job to have wired it, but the responder confirms it exists and routes the gap if it doesn't.

| Plane — the question it answers | AWS | Azure | GCP |
|---|---|---|---|
| **Control plane** — who called which API | **CloudTrail** (mgmt events on by default, 90-day history; durable retention needs a trail → S3 or CloudTrail Lake) | **Azure Activity Log** + **Entra ID audit logs** | **Cloud Audit Logs — Admin Activity** (always on, cannot be disabled) + System Event + Policy Denied |
| **Identity / sign-in** — who authenticated, from where | CloudTrail `ConsoleLogin` + IAM events | **Entra sign-in logs** (needs **P1/P2**) + Identity Protection risk | Cloud Audit Logs + Cloud Identity |
| **Network plane** — what traffic moved | **VPC Flow Logs** + Route 53 Resolver DNS logs | **NSG/VNet Flow Logs** + Network Watcher | **VPC Flow Logs** + Firewall Rules Logging |
| **Data-access plane** — who read/wrote data | CloudTrail **data events** (S3/DynamoDB/Lambda — opt-in) | Entra + resource diagnostic logs | **Cloud Audit Logs — Data Access** (off by default, cost-bearing) |
| **Detection plane** — is this malicious (consumed, not authored) | **GuardDuty** → Security Hub; **Detective** behavior graph; Security Lake (OCSF) | **Defender for Cloud / Defender XDR** + **Sentinel** (SIEM/SOAR) | **Security Command Center** (ETD/Container/VM Threat Detection) |

**Preservation precondition:** the logs that feed IR must live in an account/subscription/project the attacker does **not** control, under **immutable / WORM retention with legal hold** — AWS org-wide trail → central log-archive account; Azure diagnostic settings → central Log Analytics workspace; GCP aggregated sinks → central logging project (immutable GCS / BigQuery). If logs live only in the compromised account, assume they can be tampered or deleted and say so.

> **Azure path note — Log Analytics *and* Defender portal.** Microsoft is migrating Sentinel into the unified **Defender portal**, and as of 2026 that migration is **not complete**: `SigninLogs`, workbooks, and some connectors still live in the **Log Analytics workspace** (KQL), while incident triage and deep investigation increasingly run in the **Defender portal** (Defender XDR). Every Azure runbook step below names **both paths** — the KQL-over-Log-Analytics query and the Defender-portal action — because which one an operator has depends on where their tenant is in the migration. Author to both; never assume the transition is finished.

## The runbook — detect → triage → contain → eradicate → recover

### Detect (consumed)
The alert already fired. This skill's job is to **confirm it's real and pull first-order context**: the GuardDuty/Sentinel/SCC finding, the triggering control-plane events, the identity involved, and the resource graph (Detective behavior graph / Sentinel investigation graph + Defender incident / SCC finding → asset). If the detection is a false positive, close it and feed that back to `detection-engineering` as a tuning input — do not run containment on a benign event.

### Triage — scope before you touch
Answer, before any action: which **identities**, which **resources**, which **data**, and what **blast radius** (what else that principal/role/service-account can reach — this is where the posture picture and the offensive lanes' IAM-reachability leads inform the defensive response). Build the **timeline from control-plane logs**. Classify the incident as **credential/identity compromise**, **workload/instance compromise**, or **public exposure** — that classification selects the runbook. **Triage decides snapshot order; it does not terminate.** Preserve evidence before any destructive step.

### Contain — *this is where cloud differs most*
Containment is **API-driven and near-instant**, and does not require touching the host:
- **Isolate by network** — swap the instance's **security group** (AWS) / **NSG** (Azure) / **firewall tags + deny-all rule** (GCP) for a forensic quarantine group that allows only the analyst/collection path. No host login.
- **Isolate by IAM** (the cloud-native move) — **revoke the compromised principal**, not the box: deny-all policy, deactivate/rotate access keys, revoke live sessions. AWS: inline deny-all + `DeleteAccessKey` + a revoke-older-than-now session policy to kill active STS sessions. Azure: disable the Entra user, **revoke sessions / refresh tokens**, remove role assignments, rotate app/client secrets. GCP: lift IAM bindings, `gcloud iam service-accounts disable`, disable/rotate SA keys. A credential works from anywhere, so containing the identity often beats containing the host.
- **Snapshot before anything destructive** — memory (from inside the guest), then disk, then logs — *before* stop/terminate. See `references/aws-ir.md` / `azure-ir.md` / `gcp-ir.md`.
- **Detach from orchestration** — remove from Auto Scaling group / scale set / MIG, deregister from the load balancer, drop from the mesh, so a "healthy" replacement isn't spun up and the evidence host isn't recycled.
- **Preserve, don't power off** — `stop` (not `terminate`); enable termination protection; set shutdown behavior = stop; disable `DeleteOnTermination` so containment doesn't wipe the evidence volume.

### Eradicate — remove the foothold
Rotate **all** potentially exposed secrets (not only the one seen used — assume lateral key access); delete attacker-created IAM users/roles/keys/service accounts, malicious Lambda/Functions/Cloud Run functions, backdoor images/AMIs, scheduled tasks, and persistence (new OAuth app registrations, federated IdP trust, resource-policy grants to external accounts). Check whether the **IaC/pipeline** was the entry (poisoned Terraform/CI). **Rebuild from known-good images rather than cleaning in place** — a cleaned host is a trusted host you cannot trust.

### Recover
Restore from clean snapshots/images **predating** the compromise; rebuild via IaC into a clean account/subscription/project where feasible; re-enable traffic **in stages with heightened monitoring**; confirm the detection that fired is now tuned/covered (handoff to `detection-engineering`/`detection-validation`); watch for re-compromise from any credential left unrotated. For the planned-outage and declared-disaster variants of recovery — RTO/RPO targets, multi-region failover, restore-from-backup discipline — see **`references/cloud-resilience.md`** (BCDR).

### Lessons-learned / close-out
Record the **timeline, root cause, dwell time**, which detection gap existed, and which containment step was slow. **Feed metrics to `observability`** (dwell time, MTTR, containment latency); **feed detection gaps to `detection-engineering`**; update the runbooks. A close-out that produces no routed gap and no metric is a story, not a control.

## The three runbook skeletons

The three incident classes, each as a skeleton the full per-cloud commands sit under (in the reference files). Each assumes the alert already fired and that **acquisition precedes any destructive step**.

| Runbook | Trigger (consumed detection) | First move | Load-bearing cloud specific |
|---|---|---|---|
| **A — Compromised credential / identity** | GuardDuty IAM finding · Entra risky sign-in · SCC anomalous IAM grant | Triage blast radius from control-plane logs, then **contain the identity fast** (deny-all + key deactivate + session revoke) | The credential works from anywhere — revoke the principal and kill live sessions, don't just firewall a box |
| **B — Compromised instance / workload** | GuardDuty EC2/Runtime · Defender for Servers · SCC VM Threat Detection | **Preserve memory, then disk, before isolation**; then quarantine SG/NSG/firewall + detach from orchestration + `stop` | Memory dies on isolation/termination; snapshot captures disk only — memory is a separate, first step |
| **C — Public exposure (data / resource)** | Public S3/GCS · open NSG 0.0.0.0/0 · exposed DB · Security Hub/Defender/SCC posture finding | **Export the current config as evidence**, then remove public access immediately (one-call config change) | The fix is a single config call; preserve the prior policy/ruleset *first*, then assess whether data was actually accessed |

## Cloud forensics — defensible, reproducible acquisition

You never hold the physical media, so acquisition is API-driven and must be **logged, hashed, and chain-of-custody-tracked**:

- **Prefer automated, logged acquisition** (`cloudforensics` CLI, SSM/Run Command, Sentinel playbook) over interactive SSH — reproducible, self-documenting, and it avoids polluting volatile state.
- **Memory before disk** — from inside the guest (SSM + LiME/WinPmem on AWS; guest dump on Azure; GRR/LiME on GCP), because snapshots capture only what's written to the volume and miss RAM-cached data.
- **Copy evidence out of reach** — snapshot → copy to a dedicated **forensics account/subscription/project**, re-encrypt with a **forensics-owned KMS key** (a key only in the primary region/account breaks the analysis path), apply **object-lock / immutable + legal hold**, restrict with least-privilege IAM, and log access to the evidence store itself.
- **Chain of custody** — record every step, operator, UTC timestamp, and command/API call; record **snapshot ID, source volume/disk ID, account/subscription/project, region, and KMS key**; **hash (SHA-256)** at acquisition and verify after copy; store hashes with the evidence record.

Per-cloud acquisition commands, isolation moves, and the tool invocations live in `references/aws-ir.md`, `references/azure-ir.md`, and `references/gcp-ir.md`.

## Anti-patterns

- **Terminating the compromised instance before acquisition.** The instance-store, un-snapshotted state, and RAM are gone, and auto-scaling may recycle the host. *Fix:* acquire (memory → disk → logs) first; `stop`, never `terminate`; disable `DeleteOnTermination`.
- **Firewalling the box but leaving the stolen credential live.** The attacker reconnects from a new IP with the same key. *Fix:* contain the **identity** — deny-all + key deactivation + **session/token revocation** — alongside network isolation.
- **Capturing memory after network isolation.** Isolation and termination both destroy RAM. *Fix:* memory is the **first** acquisition step, from inside the guest, before any isolation.
- **Trusting logs that live only in the compromised account.** An attacker with control-plane access tampers or deletes them. *Fix:* the telemetry precondition — immutable, out-of-band store with legal hold; if it's absent, say the response is reconstruction, not IR, and route the gap.
- **Authoring the detection here when a gap is found.** Close-out surfaces a missing rule and someone writes a Sigma rule in this runbook. *Fix:* this skill owns respond+recover; route the gap to `detection-engineering` (author) → `detection-validation` (prove it fires).
- **Cleaning the host in place and returning it to service.** A cleaned box is a box you cannot prove is clean. *Fix:* rebuild from known-good images / IaC; restore from a snapshot predating compromise.
- **Rotating only the one key you saw used.** Lateral key/secret access is the norm, not the exception. *Fix:* rotate **all** potentially exposed secrets; assume lateral exposure.
- **Citing NIST 800-61r2's five-phase cycle as current.** r2 is superseded by r3 (2025-04-03). *Fix:* anchor to r3 (CSF 2.0 functions) **and** PICERL; name both.
- **Assuming the Azure Sentinel→Defender migration is finished.** Sign-in logs and some connectors still live in Log Analytics in 2026. *Fix:* author both the Log-Analytics (KQL) and Defender-portal paths.
- **An untested backup treated as a recovery capability.** It is a hope until a drill proves it. *Fix:* see `references/cloud-resilience.md` — the restore/DR drill is the control SOC 2 A1.3 / ISO A.5.30 test for.

## Hard rules

- **This skill owns RESPOND + RECOVER, not detect.** It consumes `detection-engineering`'s rules and `detection-validation`'s proof-of-firing; it authors no detection and re-proves none. A found detection gap is routed, not filled here.
- **Acquire before you destroy.** Memory → disk → logs, in order of volatility, **before** any isolation or termination. Cloud evidence is ephemeral; this reorders the whole runbook.
- **Contain the identity, not just the host.** A credential works from anywhere — deny the principal and revoke live sessions/tokens, in addition to network isolation.
- **Telemetry is the precondition.** Control-plane + identity + network + detection logs, in an **immutable, out-of-band** store the attacker cannot reach. No durable attacker-inaccessible logs → it is reconstruction, not IR; say so and route to `observability` / `detection-engineering`.
- **Anchor to NIST SP 800-61r3 AND PICERL.** r3 (CSF 2.0 Respond/Recover) frames the governance; PICERL frames the runbook. Never cite r2's five-phase cycle as current.
- **Cover both Azure paths** — Log Analytics (KQL) and the Defender portal — because the Sentinel→Defender migration is incomplete in 2026.
- **Preserve, don't power off** — `stop` not `terminate`, termination protection on, `DeleteOnTermination` off, detach from orchestration so nothing recycles the evidence host.
- **Chain of custody on every artifact** — logged acquisition, SHA-256 hash at acquisition and after copy, forensics account + forensics-owned key + object-lock/legal-hold, access to the evidence store itself logged.
- **Rebuild, don't clean** — restore from images/snapshots predating compromise; rotate **all** potentially exposed secrets, not only the one observed.
- **Redaction** — a recovered key, token, secret, or sensitive record captured as evidence is reported as *that it was recovered and its blast radius*, never its value; nothing sensitive committed.

## Cross-references

- **`security-architect`** (`security/agents/security-architect.md`) — the roll-up agent that loads this skill: an incident's root cause and dwell time become risk-register and coverage items in the posture picture; a recurring incident class is a control gap to prioritize.
- **`security-governance:detection-engineering`** (`security/detection-engineering/`) — **authors** the detection this skill assumes fired; a close-out detection gap ("nothing alerted on the privesc") is the exact hypothesis routed back here. This skill responds; that one authors.
- **`detection-validation`** (`security/detection-validation/`, run by `purple-team-engineer`) — **proves** the detection fires; this skill trusts a validated detection and does not re-prove it. Author → validate → respond is the three-step loop.
- **`observability`** (`observability/` domain; `observability-engineer-*`, `be-<stack>:queries` — named, not loaded) — owns the telemetry substrate (OTel → Grafana/Loki/Tempo) and the immutable log retention this response depends on; post-incident metrics (dwell time, MTTR, containment latency) flow back here, and a missing/mutable log store is a handoff to this lane.
- **`devops:cloud-posture`** (`devops/cloud-posture/`) — the **pre-incident** half: it benchmarks whether the account is configured securely (CSPM/Prowler/ScoutSuite) so the incident doesn't happen; its public-exposure and over-broad-IAM findings are the posture the exposure runbook (C) and credential runbook (A) remediate against.
- **`security-governance:compliance-evidence-mapping`** (`security/compliance-evidence-mapping/`) — consumes `references/cloud-resilience.md`: the **BCDR crosswalk row** (SOC 2 A1.2/A1.3 · ISO 27001:2022 A.5.29–A.5.30 · NIST CSF 2.0 RECOVER · 800-53 CP) is added **there** by task G1, pointing at this skill's resilience reference as the control-to-cloud-evidence detail.
- **`penetration-tester`** / the cloud-attack lane (`security/cloud-attack-aws|azure|gcp/`) — the offensive sibling: the IAM privesc paths, metadata-service credential theft, and storage abuse those skills prove reachable are the exact attack shapes runbooks A/B/C respond to; a finding there implies a detection to author and an incident to be ready for.
- **`security-governance:security-hardening`** / **`secrets-hardening`** — the preventive siblings: hardening and secret rotation *prevent* the incident; eradication/recovery reference the guardrails (SCP / Azure Policy / Org Policy) and rotation runbooks they own, and do not author them.
