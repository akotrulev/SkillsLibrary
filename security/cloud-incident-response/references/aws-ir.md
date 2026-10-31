# AWS Incident Response & Forensics — CloudTrail triage · EBS snapshot · SSM memory · libcloudforensics

The AWS half of the runbook: what to read, what to snapshot, and how to contain — following the **AWS Security IR User Guide acquisition order (metadata → protections/tags → EBS snapshot → memory)** and the cross-cutting rule that **acquisition precedes any destructive step**. This skill consumes the detection (GuardDuty/Security Hub); it does not author it.

## Telemetry to read first

| Question | Source | Note |
|---|---|---|
| Who called which API | **CloudTrail** management events | On by default, 90-day Event History; durable retention needs a **trail → S3** (or **CloudTrail Lake**). Each event carries caller identity, API, source IP, params, UTC time. |
| Who read/wrote data | CloudTrail **data events** (S3 object, DynamoDB, Lambda) | **Opt-in**, high-volume — often *not* enabled, so object-level access may be invisible. State that gap when it is. |
| What traffic moved | **VPC Flow Logs** + **Route 53 Resolver DNS logs** | The "logging trifecta" with CloudTrail. |
| Is this malicious (consumed) | **GuardDuty** (ML + threat intel over CloudTrail/Flow/DNS; reads its own copy — does not touch your config) → **Security Hub** (ASFF aggregation) | Feb 2025 added an IAM finding type for restricted-credential misuse and **attack-sequence** findings that correlate multiple actions. |
| Blast radius / timeline | **Amazon Detective** behavior graph (CloudTrail + Flow + GuardDuty + Security Lake + EKS audit) | An **investigation** tool, not a detector; Feb 2025 added timeline playback + severity filter. |
| One normalized view | **Security Lake** (OCSF in S3) | Query cross-source with Athena/OpenSearch. |

Centralize to a separate **log-archive / security-tooling account** (Control Tower pattern), under **immutable/WORM + legal hold**, reachable by the forensics account via cross-account roles — never only in the compromised account.

## Containment

- **Network isolation** — replace the instance's security group with a **forensic quarantine SG** that allows only the analyst/collection path; detach from the **Auto Scaling group**; deregister from the **load balancer/target group**. No host login.
- **Identity isolation** (often the stronger move) —
  - Attach an explicit **deny-all inline policy** to the compromised user/role (`aws iam put-user-policy` / `put-role-policy`).
  - **Deactivate/delete** access keys (`aws iam update-access-key --status Inactive`, `delete-access-key`).
  - **Kill live STS sessions** — apply a policy denying actions where `aws:TokenIssueTime` is older than now (revoking a role's active sessions); IAM Identity Center sessions are revoked separately.
- **Preserve, don't power off** — enable **termination protection**, set **shutdown behavior = stop**, disable **`DeleteOnTermination`** on attached volumes, then `stop` (not `terminate`) only if you must halt execution.

## Forensic acquisition — the AWS order

1. **Metadata** — record instance id, AMI, IAM role, ENIs, attached volumes, tags, region, account.
2. **Protections / tags** — termination protection on; shutdown = stop; `DeleteOnTermination` off; tag `quarantine` + ticket id (a tag can trigger isolation automation).
3. **Memory — before isolation** — avoid interactive SSH (it destroys volatile artifacts). Use **SSM Run Command** to run **LiME** (Linux) / **WinPmem** (Windows) and write the image to S3, no interactive session.
4. **Disk** — `aws ec2 create-snapshot` (or `create-snapshots` for a crash-consistent multi-volume set). **Copy the snapshot into the forensics account and re-encrypt with a forensics-account KMS CMK**; create a volume from the copy and attach it to a hardened analysis instance. Snapshots capture only what is written to the volume — they **miss RAM-cached data**, which is why memory is a separate, earlier step.
5. **Logs / config** — export CloudTrail, Flow Logs, and **AWS Config** resource history to the immutable store with legal hold before any retention window lapses.

## Tools

| Tool | Invocation | What it answers |
|---|---|---|
| **AWS native snapshot APIs** | `aws ec2 create-snapshot(s)`; copy + re-encrypt with the forensics CMK | "point-in-time block image of the volume" |
| **SSM Run Command + LiME/WinPmem** | SSM document runs the collector → S3 | "what was in RAM without an interactive login" |
| **libcloudforensics / cloud-forensics-utils** (Google; PyPI `libcloudforensics`, latest release 2024-10-18) | `cloudforensics aws <verb>` — e.g. make-volume-copy, cross-account snapshot copy, quarantine | "acquire this disk/instance and isolate it, reproducibly and logged" |
| **GuardDuty** (consumed) | Findings → EventBridge → Lambda/runbook | "is this host/account doing something malicious" |
| **Amazon Detective** | Pivot from a GuardDuty finding | "what's the blast radius and timeline of this principal/resource" |
| **Security Hub / Security Lake** | Delegated-admin aggregation; Athena over Security Lake (OCSF) | "one normalized view across sources" |

> Verify the `cloudforensics` CLI verbs and the GuardDuty finding-type roster against the current repo/docs at use time — both grow.

## Runbook A — compromised AWS credential / identity
Trigger: GuardDuty IAM finding (e.g. anomalous API from a restricted credential) / `ConsoleLogin` anomaly.
1. **Triage** — enumerate the principal's reach (attached policies, assumable roles, resource access) from CloudTrail; build the timeline.
2. **Contain the identity fast** — deny-all inline policy + deactivate keys + revoke-older-than-now session policy to kill live STS sessions.
3. **Eradicate** — delete attacker-created users/roles/keys, external trust grants, OAuth consents; rotate **all** related secrets (assume lateral exposure).
4. **Recover** — reissue least-privilege credentials; enforce MFA; monitor for key reuse.
5. **Close-out** — root cause (leaked key in repo? SSRF→IMDS? phished console?); detection gap → `detection-engineering`.

## Runbook B — compromised AWS instance / workload
Trigger: GuardDuty EC2/Runtime finding.
1. **Preserve first** — SSM+LiME/WinPmem memory capture **before** isolation; then `create-snapshot` the disk.
2. **Protect the evidence** — copy snapshot to the forensics account, re-encrypt with the forensics CMK, SHA-256 hash, legal-hold.
3. **Contain** — quarantine SG, detach from ASG, deregister from LB, `stop` with termination protection on.
4. **Eradicate** — do not clean in place; rebuild from a known-good AMI; find persistence (cron/systemd/startup scripts, backdoor AMIs, injected packages).
5. **Recover** — redeploy clean via IaC; stage traffic back; heightened monitoring.

## Runbook C — public AWS exposure
Trigger: public S3 bucket / open SG `0.0.0.0/0` / Security Hub posture finding.
1. **Triage** — confirm exposure and whether it was accessed (S3 data events/access logs, Flow Logs); assess data sensitivity.
2. **Preserve the current config as evidence first** (export the bucket policy / SG ruleset), then **remove public access immediately** (bucket policy / S3 Block Public Access; tighten the SG; revoke public ACL/IAM grants).
3. **Preserve** — snapshot access logs + AWS Config state to immutable storage; hash.
4. **Eradicate** — fix the IaC/pipeline that produced the exposure; add an **SCP** guardrail to prevent recurrence.
5. **Recover / notify** — assess breach-notification obligations if data was accessed.

## Handoffs
- **← `detection-engineering`** — authors the GuardDuty/Sigma logic; a close-out gap routes back here.
- **← `detection-validation`** — proves those detections fire; not re-proven here.
- **→ `observability`** — dwell time / MTTR / containment latency; immutable log retention is a shared precondition.
- **↔ `devops:cloud-posture`** — its public-exposure / over-broad-IAM findings are what runbooks A/C remediate against.
- **BCDR** — recovery targets and multi-region restore in `cloud-resilience.md`.
