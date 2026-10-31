# GCP Incident Response & Forensics — SCC/Audit-Log triage · persistent-disk snapshot · GRR memory · cloud-forensics-utils

The GCP half of the runbook: what to read, what to snapshot, how to contain. This skill consumes the detection (Security Command Center); it does not author it. **Acquisition precedes any destructive step.**

## Telemetry to read first

| Question | Source | Note |
|---|---|---|
| Who called which API | **Cloud Audit Logs — Admin Activity** | **Always on, cannot be disabled or excluded** — the one plane you can always count on. Plus **System Event** (Google-initiated config) and **Policy Denied** (VPC-SC / Org Policy denials). |
| Who read/wrote data | **Cloud Audit Logs — Data Access** | **Off by default, cost-bearing** — enable Data Read/Write per API (e.g. IAM, STS, SCC). Often not enabled, so object/data access may be invisible; state that gap. |
| Who authenticated | Cloud Audit Logs + **Cloud Identity** logs | — |
| What traffic moved | **VPC Flow Logs** + **Firewall Rules Logging** + Cloud DNS logging | **GCP VPCs are global** (subnets regional) — segmentation differs from AWS/Azure; account for it in scoping. |
| Is this malicious (consumed) | **Security Command Center** (Standard/Premium/**Enterprise**) — Event Threat Detection, Container Threat Detection, Security Health Analytics, VM Threat Detection | Enterprise tier adds SIEM/SOAR (Chronicle-backed) + case management. |
| Preserved, queryable logs | **Aggregated log sink** at org/folder level → central logging project | BigQuery for analytics, **immutable GCS** for cold retention, Pub/Sub for streaming to an external SIEM. |

Centralize via **org-level aggregated sinks** → a central logging project the attacker does not control, under **immutable (bucket retention lock) + legal hold**; SCC at org scope.

> **Service-account twist.** A GCP service account is **both an identity and a resource**, so `iam.serviceAccounts.actAs` / impersonation is itself an escalation lever with no AWS analog — a compromised SA's blast radius includes everything it can impersonate. Enumerate that in triage. Also: on **new** orgs/projects the default Compute SA **no longer auto-gets Editor + broad scope** — brownfield still carries the old broad default, so **detect the SA's actual bindings, don't assume**.

## Containment

- **Network isolation** — swap the VM's **network tags** and apply **deny-all firewall rules** (leave an analyst-IP exemption); detach from the **managed instance group (MIG)**; remove from the backend service / load balancer.
- **Identity isolation** —
  - **Remove IAM bindings** on the compromised principal (`gcloud projects remove-iam-policy-binding`).
  - **Disable the service account** (`gcloud iam service-accounts disable`) and **disable/rotate SA keys** (`gcloud iam service-accounts keys ...`).
  - For a user principal, revoke sessions via the Google Workspace / Cloud Identity admin controls.
- **Preserve, don't delete** — snapshot before stopping; do not delete the instance.

## Forensic acquisition

1. **Metadata** — record instance id, project, zone/region, attached persistent disks, service accounts, network tags.
2. **Memory / live — before isolation** — **GRR Rapid Response** for remote live forensics including memory retrieval, or **LiME** inside the guest. No tenant hypervisor dump exists.
3. **Disk** — `gcloud compute disks snapshot` on the attached persistent disk → create a new disk from the snapshot → attach to a **forensic workstation in an isolated VPC** (dedicated project).
4. **Logs / config** — export **Cloud Audit Logs** to a sink (immutable GCS bucket / BigQuery) and capture **Cloud Asset Inventory** config state; **hash (SHA-256)** and record snapshot id, source disk id, project, region, and KMS key.

Prefer the automated, logged path (`cloudforensics` CLI, GRR flows) over interactive SSH.

## Tools

| Tool | Invocation | What it answers |
|---|---|---|
| **GCP native snapshot** | `gcloud compute disks snapshot` → new disk → isolated VPC | "block image of the persistent disk" |
| **GRR Rapid Response** | GRR agent / flow | "live memory and artifacts off a running GCE VM" |
| **libcloudforensics / cloud-forensics-utils** (Google; PyPI `libcloudforensics`, latest 2024-10-18; ships a **GCP network-quarantine function**) | `cloudforensics gcp <verb>` — e.g. make-volume-copy, quarantine (deny-all FW + analyst-IP exempt) | "acquire this disk and isolate it, reproducibly and logged" |
| **Security Command Center** (Standard/Premium/Enterprise) | SCC console; findings → Pub/Sub → runbook | "what's exposed and what threats fired in this org" |
| **Cloud Audit Logs + aggregated sink** | Org sink → immutable GCS / BigQuery | "who did what, preserved and queryable" |

> Verify the `cloudforensics` GCP verbs and SCC finding categories against the current repo/docs — both grow. Note Google renamed **"Cloud Functions" → "Cloud Run functions"** (1st/2nd-gen folded into Cloud Run); look for malicious functions under the Cloud Run surface.

## Runbook A — compromised GCP identity / service account
Trigger: SCC Event Threat Detection anomalous IAM grant / SA-key anomaly.
1. **Triage** — enumerate the principal's bindings **and** everything it can `actAs`/impersonate (the SA-as-resource blast radius); timeline from Admin Activity logs.
2. **Contain** — remove IAM bindings; `gcloud iam service-accounts disable`; disable/rotate SA keys.
3. **Eradicate** — delete attacker-created SAs/keys/bindings and external trust/grants; rotate **all** related secrets (assume lateral exposure).
4. **Recover** — reissue least-privilege; enforce MFA / context-aware access; monitor for reuse.
5. **Close-out** — root cause (leaked SA key? impersonation chain? SSRF→metadata?); detection gap → `detection-engineering`.

## Runbook B — compromised GCE instance
Trigger: SCC VM Threat Detection / Container Threat Detection.
1. **Preserve first** — GRR/LiME memory **before** isolation; then `gcloud compute disks snapshot` the PD.
2. **Protect the evidence** — snapshot → new disk in the isolated forensics project, SHA-256 hash, retention-lock.
3. **Contain** — swap network tags + deny-all firewall (analyst exemption), detach from MIG, remove from LB; stop (don't delete).
4. **Eradicate** — rebuild from a known-good image; find persistence (startup scripts, cron, backdoor images, malicious Cloud Run functions).
5. **Recover** — redeploy clean via IaC; stage traffic; heightened monitoring.

## Runbook C — public GCP exposure
Trigger: public GCS bucket / open firewall `0.0.0.0/0` / SCC posture finding.
1. **Triage** — confirm exposure and access (Data Access logs if enabled, Flow Logs); assess data sensitivity.
2. **Preserve the current config first** (export the IAM policy / firewall ruleset), then remove public access immediately.
3. **Preserve** — snapshot access logs + Cloud Asset Inventory state to immutable storage; hash.
4. **Eradicate** — fix the IaC/pipeline; add an **Organization Policy** constraint guardrail to prevent recurrence.
5. **Recover / notify** — assess breach-notification obligations if data was accessed.

## Handoffs
- **← `detection-engineering`** — authors the SCC/Sigma logic; a close-out gap routes back here.
- **← `detection-validation`** — proves those detections fire.
- **→ `observability`** — dwell time / MTTR / containment latency; immutable log retention shared precondition.
- **↔ `devops:cloud-posture`** — its posture findings are what runbooks A/C remediate against.
- **BCDR** — RTO/RPO and GCP Backup-and-DR restore in `cloud-resilience.md`.
