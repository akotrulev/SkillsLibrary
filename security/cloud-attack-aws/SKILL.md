---
name: cloud-attack-aws
description: Use when exploiting an authorized AWS account after recon (IAM privesc, EC2 metadata credentials, S3, RDS). Triggers "what can this access key become". Not for recon (cloud-recon-enumeration).
---

# Penetration Testing — AWS Exploitation (IAM privesc · EC2/S3/RDS · Pacu/CloudFox/PMapper)

AWS exploitation starts from one load-bearing fact: **everything is an API call authorized by IAM, and
the credential that signs the call is the prize.** There is no network perimeter around the control plane
— services answer over HTTPS endpoints (`<service>.<region>.amazonaws.com`) and the only gate is the
principal's effective permission set. So AWS offense is overwhelmingly an **identity problem**: recover a
credential, map what it can do, and chain `iam:*`/`sts:*`/`iam:PassRole` edges into a more powerful
principal — rather than a host-exploitation problem. This skill picks up where `cloud-recon-enumeration`
leaves off — a credential, a principal, a permission map — and chains it into IAM privilege escalation,
EC2 credential theft, and service-specific abuse (S3, RDS, Lambda, Secrets Manager/SSM).

> **⚠️ Authorized self-testing only — owned/lab AWS accounts, under a committed cloud scope file.** This
> skill exploits **your own** AWS account(s) — or a designated training lab (**CloudGoat**,
> **flaws.cloud**, **IAM Vulnerable**) — to prove what `cloud-recon-enumeration` or `devops:cloud-posture`
> found is actually reachable. Every run is gated by the same committed **cloud scope file** and
> `#volatile` authorization line as the rest of the lane: never cached as durable, re-confirmed each
> engagement. Only the scope file's in-scope account ids and regions are touched; its hard exclusions
> (shared-services accounts, production data stores, other accounts) are never touched even if reachable.
> Production is a separate, louder sign-off than a lab target.

```
Authorization: cloud-scope=<account ids>  regions=<in-scope regions>
               exclusions=<never-touch accounts/data-stores>  authorized-by=<name>
               window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (every tool here is a Python/Go CLI or the `aws` CLI against the AWS
API — no per-stack split, per the library's anti-triplication rule) and is loaded by the
**`penetration-tester`** agent as its AWS exploitation step. It fences against `cloud-attack-azure` and
`cloud-attack-gcp` (same role, different provider), against `devops:cloud-posture` (which already *reads*
AWS defensively — Prowler/ScoutSuite, read-only CSPM), against `initial-access` (network/application
foothold, not cloud-API abuse), and against `atomic-simulation` (which *detonates* a technique with
Stratus Red Team to test detection, rather than exploiting a real misconfiguration). Name the
posture handoff explicitly: a `cloud-posture` finding ("bucket X is public", "instance Y allows IMDSv1",
"role Z trusts `*`") is a lead here; this skill proves it is reachable and chains it, then reports the
confirmed exploitability back as validated posture.

> **The spine is MITRE ATT&CK Cloud** (IaaS matrix), **not Enterprise** — a cloud finding tagged with a
> host-centric Enterprise id is mis-mapped. Every technique below carries its Cloud id: `T1078.004` Valid
> Accounts: Cloud Accounts, `T1098`/`T1098.001` Account Manipulation (+ Additional Cloud Credentials),
> `T1548` Abuse Elevation Control Mechanism, `T1552.005` Unsecured Credentials: Cloud Instance Metadata
> API, `T1552.001`/`.007` Credentials in Files / env, `T1526` Cloud Service Discovery, `T1580` Cloud
> Infrastructure Discovery, `T1619` Cloud Storage Object Discovery, `T1530` Data from Cloud Storage,
> `T1537` Transfer Data to Cloud Account, `T1578.001`/`.002` Modify Cloud Compute Infrastructure
> (snapshot), `T1562.008` Impair Defenses: Disable Cloud Logs (named for *awareness only*, never taught as
> a technique). Severity is scored **CVSS** in the final report (`penetration-testing:reporting`), not the
> blocker/major/minor/nit table.

## AWS target model: IAM is the perimeter

- **Principals & credentials.** **Users** are long-lived identities carrying **access keys** — `AKIA…`
  (long-term) and `ASIA…` (temporary/STS, with a session token). Keys are what leak in code, CI logs, and
  laptops; an account id is derivable **offline** from an `AKIA`/`ASIA` id, so a leaked key is attributable
  without an API call. **Roles** have no long-term credentials — assuming one yields temporary `ASIA…`
  creds; services (EC2 instance profiles, Lambda exec roles) and cross-account access run on roles.
- **Policies & the effective set.** Permissions are the **union** of identity policies (**managed** —
  versioned, up to 5 versions, with one default — and **inline**), bounded above by explicit `Deny`, SCPs,
  permission boundaries, and session policies. A role's **trust policy** (`AssumeRolePolicyDocument`) is the
  resource policy naming who may `sts:AssumeRole` it — rewriting it (`iam:UpdateAssumeRolePolicy`) adds an
  attacker as a trusted principal.
- **`iam:PassRole` is the pivot.** It does nothing alone; it authorizes handing a role to a **service**
  (EC2, Lambda, Glue, CloudFormation, SageMaker, Data Pipeline) that then runs attacker-controlled code
  **as** that role. Almost every service-based privesc is `PassRole` + one service `Create`/`Run` action.
- **STS is the lateral graph.** `sts:AssumeRole` chains (A→B→C) along existing trust edges are the
  movement graph PMapper computes; `sts:GetCallerIdentity` is the innocuous "who am I" first call.
- **The instance metadata service (IMDS)** exposes an EC2 instance profile's temporary creds on a
  link-local address the workload itself can reach — the single richest credential-theft target, detailed
  below.

## Step 1 — enumeration: who am I → what can I do → what is here → where can I pivot

Consumes the credential and principal leads `cloud-recon-enumeration` already produced; this step goes
deeper, provider-side:

- **Identity, always first:** `aws sts get-caller-identity` returns the account id, the principal ARN
  (user vs assumed-role), and the user id — innocuous, but logged to CloudTrail.
- **Permission enumeration — the core "what can I do" primitive.** When `iam:` reads are denied (the usual
  case for a scoped test principal), **`enumerate-iam`** brute-forces read-only `get*`/`list*`/`describe*`
  calls and records which succeed vs `AccessDenied` — the success set **is** the permission map, inferred
  without ever calling `iam:GetPolicy`, and non-destructive by construction. When `iam:List*`/`Get*` *are*
  held, Pacu's `iam__enum_permissions` pulls the attached/inline/group policies into its DB, and
  `iam:SimulatePrincipalPolicy` (if allowed) lists effective permissions authoritatively.
- **Resource discovery:** **CloudFox** (`cloudfox aws all-checks`) is the fastest single-command inventory
  — `inventory`, `endpoints` (internet-reachable), `instances`, `permissions`, `principals`, `secrets`
  (Secrets Manager + SSM), `buckets`, `role-trusts`, `access-keys`, `databases`, `env-vars`, and `cape`
  (cross-account privesc paths, needs PMapper data). Read-only (Describe/List/Get). `aws` CLI recipes
  (`aws iam get-account-authorization-details`, `aws ec2 describe-instances`, `aws s3 ls`,
  `aws secretsmanager list-secrets`, `aws ssm describe-parameters`) are the ground-truth behind the frameworks.

Full recipes: `references/pacu.md` (Pacu + enumerate-iam), `references/cloudfox.md` (CloudFox + ScoutSuite).

## Step 2 — IAM privilege escalation (`T1098`/`T1098.001`, `T1548`, `T1078.004`)

**This is the spine of AWS offense.** The canonical corpus is **Rhino Security Labs' 21 IAM
privilege-escalation methods** (secondary sources inflate the count to 41 — Rhino's own is **21**),
automated by **Pacu `iam__privesc_scan`** and modeled graph-wise by **PMapper**. Each is a *configuration
weakness, not a CVE*: `permission(s) held → action → more powerful principal`. The four families:

| Family | Representative permissions | Escalation |
|---|---|---|
| **A. Direct policy/permission grant to self** | `iam:CreatePolicyVersion`, `iam:SetDefaultPolicyVersion`, `iam:Attach{User,Group,Role}Policy`, `iam:Put{User,Group,Role}Policy`, `iam:AddUserToGroup` | Grant yourself (or a group/role you reach) `Action:*`/`Resource:*` — e.g. `CreatePolicyVersion --set-as-default` bypasses needing attach rights; `SetDefaultPolicyVersion` rolls back to an older, more permissive version. |
| **B. New credential / identity** | `iam:CreateAccessKey` (on another user), `iam:CreateLoginProfile`, `iam:UpdateLoginProfile`, `iam:CreateUser`+policy | Mint a second access key for a higher-priv user, set/reset a console password, or create a fresh admin user (privesc + persistence). `T1098.001`. |
| **C. Trust-policy / assume-role abuse** | `iam:UpdateAssumeRolePolicy` (+ `sts:AssumeRole`), `sts:AssumeRole` chains | Rewrite a privileged role's trust policy to trust your principal, then assume it; or follow existing A→B→C trust edges to a more-privileged role (PMapper reachability; CloudFox `cape` surfaces cross-account hops). |
| **D. `iam:PassRole` + a service that runs code** | `PassRole` + `ec2:RunInstances` / `lambda:CreateFunction`+`InvokeFunction` (or `CreateEventSourceMapping`) / Glue `CreateDevEndpoint` / `cloudformation:CreateStack` / `datapipeline:CreatePipeline` / `sagemaker:CreateNotebookInstance` | Hand a more-privileged role to a service that runs your code as it, then read the role's STS creds (from the metadata service, the function's own call, or the resource). The largest family. |

Teach each as a **permission → consequence** pair, and always pair it with its detection footprint
(Step 4). In a lab, run `iam__privesc_scan` to enumerate the held set against the 21 paths, read the
**finding**, then exploit a single path by hand to understand the CloudTrail trail it leaves — never
blind-fire the scan's auto-exploit against anything you have not scoped. Full method table with exact
permissions: `references/pmapper.md` (the reachability edges) and `references/pacu.md`
(`iam__privesc_scan` + `iam__enum_action_query`).

## Step 3 — service exploitation

- **EC2 — credential theft via IMDS (`T1552.005`), the highest-value path.**
  `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` returns the instance profile's
  temporary STS creds; the classic chain is an **SSRF in an app on the instance** reaching IMDS from
  inside. **IMDSv1** is a bare unauthenticated `GET` — any SSRF that forces a GET harvests the keys.
  **IMDSv2** requires a session: `PUT /latest/api/token` (with `X-aws-ec2-metadata-token-ttl-seconds`)
  returns a token that every subsequent `GET` must carry, and a **hop limit** (default 1) stops the token
  leaving the instance — which defeats most SSRF, except a container adds a hop, so reaching IMDS from a
  container needs hop limit 2, re-widening the path. **Detect, don't assume, the posture:** IMDSv2 has been
  the EC2-console default since Nov 2023, but plenty of brownfield instances still run v1-optional
  (**dual-accept**), and v1 is a **live risk** — F5 Labs reported an active SSRF→IMDSv1 credential-theft
  campaign in March 2025. Also read **user-data** (`GET /latest/user-data` or `ec2:DescribeInstanceAttribute
  --attribute userData`), which often carries bootstrap secrets. Report as blast-radius: "instance-profile
  creds for role X recovered; role X grants <scope>" — never the key material.
- **EC2/EBS snapshot theft (`T1578.001`/`.002`, `T1537`).** `CreateSnapshot` of a volume →
  `ModifySnapshotAttribute createVolumePermission=all` (or share to a specific account) → restore a volume
  elsewhere and read its filesystem for credentials/keys. Same pattern for AMIs. Read-only exfil of your
  own lab volumes; no DoS.
- **S3 — data exposure & exfil (`T1619`, `T1530`).** Anonymous `ListBucket`/`GetObject` from a public ACL
  or bucket policy; `s3:GetBucketPolicy`/`GetBucketAcl` to read the grant; `s3:PutBucketPolicy`/`PutBucketAcl`
  to grant yourself or `*` access; object discovery across discovered buckets then `GetObject` on interesting
  keys (`.env`, tfstate, DB dumps). Full tool and read/write/privesc reachability reporting:
  `references/s3-attacks.md`.
- **RDS — snapshot & access testing (`T1537`).** `rds:CreateDBSnapshot` → `rds:ModifyDBSnapshotAttribute`
  (or `ModifyDBClusterSnapshotAttribute`) adding another account or `all` to `restore` → restore under
  attacker control, outside the victim's monitoring boundary. `rds:ModifyDBInstance --publicly-accessible`
  + an open SG exposes the DB to the internet. Test recovered/guessed DB creds against a reachable instance
  — **no brute-force that risks lockout or DoS, no load testing.**
- **Lambda / Secrets Manager / SSM.** `lambda:GetFunction` + env vars often hold secrets;
  `lambda:UpdateFunctionCode` injects exfil of the exec role's creds (privesc family D). `secretsmanager:
  GetSecretValue` and `ssm:GetParameter(s) --with-decryption` frequently unlock DB creds/API keys → pivot.
  `ssm:SendCommand`/`StartSession` against a managed instance is **RCE on EC2 without SSH/SG ingress** (as
  the instance's SSM role) — a potent lateral primitive. Report every recovered secret as blast-radius,
  never its value.

## Step 4 — CloudTrail / GuardDuty detection-surface awareness (`T1562.008`, awareness not evasion)

Per **D5**, this skill teaches what an authorized action **emits** — so a tester knows their footprint and
a defender knows what to tune — and **never** how to evade detection against a real target:

- **CloudTrail** splits in two. **Management events** (control-plane: IAM changes, `RunInstances`,
  `ModifyDBSnapshotAttribute`, `PutBucketPolicy`, `AssumeRole`, `CreateAccessKey`) are **on by default**
  where a trail is configured, recorded with `eventName`, `userIdentity` (`IAMUser` vs `AssumedRole` vs
  `Root`), `sourceIPAddress`, and `userAgent` (`aws-cli`, `Boto3`, `pacu` — the attribution fields). Nearly
  every privesc action is a management event. **Data events** (S3 `GetObject`/`PutObject`, Lambda `Invoke`,
  DynamoDB item ops) are **off by default** — so S3 object reads are often *not* logged; check
  `cloudtrail:GetEventSelectors` to know whether they are, and report "object reads unlogged" as a
  **defender-coverage gap**, never exploit it as a stealth feature.
- **GuardDuty** fires findings off CloudTrail, VPC Flow Logs, and DNS logs. Name the finding each technique
  tends to trip so the report states what *should* have fired:
  `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS` (instance creds used off the
  instance — the EC2 IMDS-theft signature), `.InsideAWS` (used from another account),
  `PrivilegeEscalation:IAMUser/AnomalousBehavior` and `Persistence:IAMUser/AnomalousBehavior` (anomalous
  IAM mutation), `CredentialAccess:IAMUser/AnomalousBehavior`, `Policy:S3/BucketPublicAccessGranted`, and
  the tamper indicators `Stealth:IAMUser/CloudTrailLoggingDisabled` / `PasswordPolicyChange` (named so a
  tester knows these *would* fire — the skill never teaches disabling logging).

**Pairing rule:** every attack technique above is reported with its CloudTrail `eventName` and the
GuardDuty finding it tends to trigger, so the learner reasons about footprint. Confirming an authorized
action surfaced as a GuardDuty finding is purple-team value — it closes the detection loop the lab exists
to teach.

## Decision matrix — which tool, which step, which reference

| Need | Tool | Step | ATT&CK Cloud | Reference |
|------|------|------|--------------|-----------|
| "With only these keys and no self-read, what actions are permitted?" | enumerate-iam / Pacu `iam__enum_permissions` | 1 — enumeration | T1087.004 / T1526 | `references/pacu.md` |
| "What's here, what's internet-reachable, where are the secrets, what cross-account privesc exists?" | CloudFox (`all-checks`, `cape`) / ScoutSuite | 1 — enumeration | T1580 / T1526 | `references/cloudfox.md` |
| "Who can escalate to admin, and by what edge chain?" | PMapper (`preset privesc`) / Pacu `iam__privesc_scan` | 2 — privesc | T1098 / T1548 / T1078.004 | `references/pmapper.md` |
| "Which buckets exist for this keyword, and what can I do to each?" | S3 brute/CLI recipes | 3 — service exploitation | T1619 / T1530 | `references/s3-attacks.md` |
| Stand up the owned practice lab | CloudGoat / flaws.cloud / IAM Vulnerable | — | — | `references/lab-setup.md` |

## Anti-patterns

- **Reporting IMDSv1 exposure, or its absence, without checking the live instance config.** IMDSv2 is the
  console default since Nov 2023, but brownfield instances still run v1-optional. *Fix:* read the instance's
  `MetadataOptions` (`HttpTokens`) before writing the finding either way; exercise the SSRF→IMDS chain only
  against a lab instance you set up for it.
- **Blind-firing Pacu `iam__privesc_scan`'s auto-exploit.** The scan can escalate automatically; against
  anything not scoped, that is an unauthorized mutation. *Fix:* run the scan read-only for its *finding*,
  then exploit one path by hand against an in-scope lab target.
- **Dumping a recovered secret, STS credential, or snapshot filesystem into the report.** *Fix:* report
  that a credential was recovered and its blast-radius — what it reaches — never the value (§2.5 loot
  redaction).
- **Treating a CloudTrail data-event gap as a stealth technique.** Object-level reads being unlogged is a
  defender-coverage gap to *report*, not a quiet path to *use*. *Fix:* report it under detection-surface
  awareness (D5); never build an evasion recipe on it.
- **Any action that risks a DoS** — RDS credential brute-force that could lock an account, load-testing a
  reachable instance, or an uncapped IMDS probe against a fragile live workload. *Fix:* read the control-plane
  config; exercise destructive chains only against a disposable lab, and revert them.
- **Running enumerate-iam or a privesc probe against a principal outside the scope file.** Every call
  (including each `AccessDenied`) is attributable in CloudTrail. *Fix:* confirm the credential belongs to an
  in-scope account before the first call.

## Rules (hard constraints)

- **The cloud scope file gates every act.** Only in-scope account ids and regions are touched; hard
  exclusions (shared-services accounts, production data stores, other accounts) are never touched even if
  reachable; the blast-radius cap bounds every pass. Re-read the scope file before each act; halt and report
  if the next act would exceed it.
- **No DoS, ever. Destructive acts are per-act opt-in and demonstrated-then-reverted** — a snapshot shared
  for a demo is unshared and deleted; an IAM principal or access key minted for a privesc demo is deleted in
  cleanup; a persistence demo is removed.
- **Detect, don't assume, the IMDS and policy posture.** State what the live `MetadataOptions` and effective
  permissions actually are, not the current AWS default.
- **Loot/secret redaction.** A recovered key, token, STS credential, or Secrets Manager/SSM payload is
  reported as *that it was recovered and its blast radius*, never its value. Harvested data follows the
  scope file's data-handling rules.
- **Detection-surface awareness, never evasion-for-stealth.** Teach what CloudTrail and GuardDuty observe so
  a tester knows their footprint and a defender knows what to tune — never a technique whose purpose is
  evading detection on a real target (D5).
- **Two-class reporting:** every finding carries its ATT&CK **Cloud** technique id and is scored **CVSS** in
  the final report (`penetration-testing:reporting`), never the blocker/major/minor/nit table.
- **Log every act** — command, target, timestamp, ATT&CK Cloud id — into the engagement action log as it
  runs, per `penetration-testing:reporting`.
- **Production is a separate, louder gate than lab.** Default target is **CloudGoat** / **flaws.cloud** /
  **IAM Vulnerable** or a non-production owned account; production needs the second sign-off.

## Cross-references

- **`penetration-testing:cloud-recon-enumeration`** — the upstream step: produces the credential,
  principal/permission map, metadata-service leads, and OIDC-trust findings this skill consumes. This skill
  never does its job (anonymous/public discovery, OIDC-federation trust review).
- **`devops:cloud-posture`** — the **defensive** sibling: Prowler/ScoutSuite already read AWS posture
  (read-only CSPM). A `cloud-posture` finding ("bucket public", "role trusts `*`", "IMDSv1 allowed") is a
  lead here; this skill proves it is reachable and chains it, then reports confirmed exploitability back as
  validated posture. The handoff runs both ways.
- **`cloud-attack-azure`** / **`cloud-attack-gcp`** — the sibling provider skills under the same
  `penetration-tester` step; same role, different provider, no shared files.
- **`penetration-testing:initial-access`** — the network/application-foothold sibling; it lands the foothold
  (e.g. an SSRF) that this skill chains into IMDS credential theft, but does not itself abuse the cloud API.
- **`security/atomic-simulation`** — the purple-team sibling that *detonates* cloud ATT&CK techniques
  (Stratus Red Team) against a lab to test whether CloudTrail/GuardDuty fires; this skill performs the
  exploitation those detonations model, but the two never substitute for each other.
- **`penetration-testing:reporting`** — where every act is logged (action log) and every finding is scored
  (CVSS) and mapped (ATT&CK Cloud).
- **`security/cloud-incident-response`** — the defensive response peer: a confirmed AWS finding here implies
  the AWS IR runbook (`references/aws-ir.md`) and detection authoring (`security/detection-engineering`)
  that respond to it — each finding carries the detection it should have tripped.
