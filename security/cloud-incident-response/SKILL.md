---
name: cloud-incident-response
description: Use when responding to a cloud security incident on AWS, Azure or GCP (triage, forensics, containment, recovery, BCDR). Triggers "we got a GuardDuty alert". Not for detections (detection-engineering).
disable-model-invocation: true
---

# Security Governance — Cloud Incident Response (runbook · forensics · BCDR)

Cloud incident response starts where detection ends: an alert has already fired (a GuardDuty finding, an Entra risky sign-in, an SCC Event Threat Detection) and the question is *"is it real, how far does it reach, and how do we get the attacker out without destroying the evidence or the business?"* This skill is the **operational runbook**: triage the alert, **acquire forensic evidence before any destructive step**, contain by identity and network, eradicate the foothold, recover from clean backups, and feed the gaps back to the lanes that close them. It is keyed to AWS/Azure/GCP because the goals are identical across clouds but the mechanics (which API isolates a principal, which command snapshots a disk) are not.

This skill **owns RESPOND and RECOVER and does not detect.** It assumes the alert exists. Writing the detection logic is `security-governance:detection-engineering`; proving it fires is `purple-team-engineer`'s `detection-validation`; the telemetry substrate (OTel → Grafana/Loki/Tempo) is `observability`; benchmarking whether the account is *configured* securely is `devops:cloud-posture`. When a step depends on a rule that should exist and does not, name the handoff.

> **Defensive, on owned environments only.** This skill reads logs, snapshots disks, and flips config on **your own** account/subscription/project (or a designated lab); it touches no third party, so it carries no per-run authorization line. Its one hard precondition is **telemetry that already exists**: control-plane logs (CloudTrail / Azure Activity + Entra audit / Cloud Audit Logs), the detection service (GuardDuty / Defender + Sentinel / SCC), and an **immutable, out-of-band log store** the attacker cannot reach, under WORM retention with legal hold (AWS org trail → central log-archive account; Azure diagnostic settings → central Log Analytics workspace; GCP aggregated sinks → central logging project). Without durable, attacker-inaccessible logs the work is reconstruction from memory, not incident response: say so and route the gap to `observability` / `detection-engineering`.

## The two framework anchors — NIST SP 800-61r3 and PICERL

Name both; neither alone is enough.

- **NIST SP 800-61r3** (final **2025-04-03**) — *Incident Response Recommendations… A CSF 2.0 Community Profile*. It **supersedes 800-61r2** and **drops r2's five-stage cycle**, mapping IR instead onto the six **CSF 2.0 functions**: **Govern, Identify, Protect, Detect, Respond, Recover**. This skill lives in **Respond + Recover**, with Govern/Identify/Protect as the standing precondition (the guardrails, the logging, the plan) and Detect owned upstream. Cite r3 — a reference to the retired r2 five-phase model as the current standard is a dated finding.
- **SANS PICERL** — **P**reparation, **I**dentification, **C**ontainment, **E**radication, **R**ecovery, **L**essons-learned. r3 reframes the *governance* of IR; PICERL still shapes the *runbook*.

| This skill's step | NIST SP 800-61r3 (CSF 2.0) | SANS PICERL |
|---|---|---|
| Detect (consumed from `detection-engineering`) | DETECT | Identification |
| Triage | RESPOND (RS.MA / RS.AN) | Identification |
| Contain | RESPOND (RS.MI) | Containment |
| Eradicate | RESPOND (RS.MI) | Eradication |
| Recover | RECOVER (RC.RP / RC.CO) | Recovery |
| Lessons-learned / close-out | RECOVER + GOVERN | Lessons-learned |

## The one thing cloud changes — acquire before you destroy

The single rule that reorders every cloud runbook: **cloud evidence is ephemeral, so acquisition precedes any destructive containment step.** A terminated instance's instance-store, un-snapshotted state, and RAM are gone; auto-scaling may replace the box; spot reclamation can delete it out from under you. Containment-by-termination without a prior snapshot destroys the evidence the whole incident turns on. The cloud-native corollary: **containing the *identity* often beats containing the *host***. A stolen credential works from anywhere, so revoking the principal stops the attacker while the compromised box stays running for acquisition.

**Order of volatility (cloud-adapted, RFC 3227 lineage)** — capture most-perishable first:

1. **RAM** — capture **before** any network isolation or process termination; both destroy it. No tenant hypervisor dump exists — you capture from **inside** the guest.
2. **Network state** — active connections, listening sockets, routing (grabbed with the memory image via live tools).
3. **Running/ephemeral state** — instance-store, tmpfs, container-writable layer.
4. **Disk / persistent volume** — snapshot (durable; take *after* memory, because heavy disk I/O can evict in-memory evidence).
5. **Cloud logs / config** — most durable, but **preserve early anyway**: retention windows expire and attackers delete. In cloud, logs frequently **outlive the host**, so log preservation is not "last because least volatile" — it is "early because perishable for a different reason."

## Know your telemetry

The cloud under response is `<cloud>`: read `references/<cloud>-ir.md`: "Telemetry to read first", "Containment" and "Forensic acquisition" (`aws-ir.md`, `azure-ir.md`, `gcp-ir.md`). They hold the per-plane log sources (control, identity, network, data-access, detection), the isolate commands and the per-cloud runbooks A, B and C. The responder confirms the three planes are logged and routes the gap when one is not. On Azure, give every step both paths, the Log Analytics query and the Defender-portal action: the Sentinel-to-Defender migration is not complete (`references/azure-ir.md` "Both-paths note").

## The runbook — detect → triage → contain → eradicate → recover

Each step below ends on a **Done when**; the next step starts only when it is true.

### Detect (consumed)
Confirm the alert is real and pull first-order context: the finding, the triggering control-plane events, the identity involved, and the resource graph (Detective / Sentinel investigation graph + Defender incident / SCC finding → asset). A false positive is closed and fed to `detection-engineering` as tuning input; containment never runs on a benign event.
**Done when** the alert is confirmed real or closed as false positive, and the finding, its triggering events, the identity and the affected resource are written down.

### Triage — scope before you touch
Answer, before any action: which **identities**, which **resources**, which **data**, and what **blast radius** (what else that principal, role or service account can reach). Build the **timeline from control-plane logs**. Classify the incident as **credential/identity compromise**, **workload/instance compromise**, or **public exposure**; that selects runbook A, B or C. Triage decides snapshot order; it does not terminate.
**Done when** identities, resources, data and blast radius are each listed, the timeline exists, and the incident has one class.

### Contain — where cloud differs most
Containment is **API-driven and near-instant** and does not need the host. Per-cloud commands are in the reference for the cloud under response.
- **Isolate by network** — swap the instance's security group / NSG / firewall tags for a forensic quarantine group that allows only the analyst path.
- **Isolate by IAM** — revoke the compromised principal, not the box: deny-all policy, key deactivation, live-session revocation.
- **Snapshot before anything destructive** — memory from inside the guest, then disk, then logs, before stop or terminate.
- **Detach from orchestration** — out of the Auto Scaling group / scale set / MIG, the load balancer and the mesh, so no replacement is spun up and the evidence host is not recycled.
- **Preserve, don't power off** — `stop`, never `terminate`; termination protection on; `DeleteOnTermination` off.

**Done when** the principal has no live session or key, the host is quarantined and detached, and each evidence copy is hashed.

### Eradicate — remove the foothold
Rotate **all** potentially exposed secrets, not only the one seen used. Delete attacker-created IAM users, roles, keys and service accounts, malicious functions, backdoor images, scheduled tasks and persistence (new OAuth app registrations, federated IdP trust, resource-policy grants to external accounts). Check whether the **IaC/pipeline** was the entry. **Rebuild from known-good images rather than cleaning in place.**
**Done when** every exposed secret is rotated, every attacker-created principal and resource is deleted, and each is listed with its id.

### Recover
Restore from clean snapshots or images **predating** the compromise, rebuilding via IaC into a clean account where feasible. Re-enable traffic **in stages with heightened monitoring**, and watch for re-compromise from any credential left unrotated. For RTO/RPO targets, multi-region failover and restore drills, see `references/cloud-resilience.md` (BCDR): an untested backup is a hope until a drill proves it.
**Done when** services run from restored or rebuilt assets, each traffic stage passed its monitoring window, and the detection that fired is tuned or covered (handoff to `detection-engineering` / `detection-validation`).

### Lessons-learned / close-out
Record the **timeline, root cause and dwell time**, which detection gap existed and which containment step was slow. Feed dwell time, MTTR and containment latency to `observability`, and detection gaps to `detection-engineering`; update the runbooks.
**Done when** the record exists, each gap is routed to its owning lane, and each metric is handed to `observability`.

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

## Rules

The standards an incident-response runbook must meet are the security-governance rule files, not a list here: `runbooks.md` (NIST SP 800-61r3 and PICERL, acquire before destroy, contain the identity, chain of custody, rebuild not clean, the telemetry precondition, both Azure paths, route detection gaps) and `security-governance.md` (redaction). Read the project's copy in `.claude/rules/security-governance/`, or the plugin's in `security/rules-security-governance/` when the project has not installed them (`/security-governance:rules` does). They hold during a live response too, not only when a runbook file is edited. Where they and this skill's recipes disagree, the rule files win.

## Cross-references

- **`security-architect`** (`security/agents/security-architect.md`) — the roll-up agent that loads this skill: an incident's root cause and dwell time become risk-register and coverage items in the posture picture; a recurring incident class is a control gap to prioritize.
- **`security-governance:detection-engineering`** (`security/detection-engineering/`) — authors the detection this skill assumes fired; a close-out detection gap is routed back here.
- **`detection-validation`** (`security/detection-validation/`, run by `purple-team-engineer`) — proves the detection fires; this skill trusts a validated detection. Author → validate → respond is the loop.
- **`observability`** (`observability/` domain; `observability-engineer-*`, `be-<stack>:queries` — named, not loaded) — owns the telemetry substrate (OTel → Grafana/Loki/Tempo) and the immutable log retention this response depends on; post-incident metrics (dwell time, MTTR, containment latency) flow back here, and a missing/mutable log store is a handoff to this lane.
- **`devops:cloud-posture`** (`devops/cloud-posture/`) — the **pre-incident** half: its public-exposure and over-broad-IAM findings are the posture runbooks C and A remediate against.
- **`security-governance:compliance-evidence-mapping`** (`security/compliance-evidence-mapping/`) — consumes `references/cloud-resilience.md`: the **BCDR crosswalk row** (SOC 2 A1.2/A1.3 · ISO 27001:2022 A.5.29–A.5.30 · NIST CSF 2.0 RECOVER · 800-53 CP) lives there and points at this skill's resilience reference as the control-to-cloud-evidence detail.
- **`penetration-tester`** / the cloud-attack lane (`security/cloud-attack-aws|azure|gcp/`) — the offensive sibling: the privesc, metadata-credential-theft and storage-abuse paths it proves reachable are the attack shapes runbooks A, B and C respond to.
- **`security-governance:security-hardening`** / **`secrets-hardening`** — the preventive siblings: eradication and recovery reference the guardrails (SCP / Azure Policy / Org Policy) and rotation runbooks they own, and do not author them.
