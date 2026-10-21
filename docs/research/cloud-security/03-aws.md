# AWS cloud attack — research knowledge base (M6–M8)

Scope: **authorized self-testing and lab training only** (owned AWS accounts, committed scope file, expiring authorization). Teaches **detection-surface awareness** (what trips CloudTrail/GuardDuty) — never evasion-for-stealth against a live target. Recovered keys/secrets are reported as **blast-radius, never values**. **No DoS, ever.** This document is the knowledge base feeding authoring of `security/cloud-attack-aws` and covers course modules **M6 AWS Security Fundamentals**, **M7 AWS Penetration Testing**, and **M8 Advanced AWS Attacks & Exploitation**.

---

## AWS fundamentals as attack context

The attacker's mental model of AWS is: *everything is an API call authorized by IAM, and the credential that signs the call is the prize.* Services are reached over HTTPS endpoints (`<service>.<region>.amazonaws.com`); there is no network perimeter around the control plane — only IAM.

### Core services an attacker cares about
- **IAM / STS** — the authorization substrate. Owning a principal with the right `iam:*` or `sts:*` action is game over (see privesc).
- **EC2** — compute that carries an **instance profile** (a role) reachable from inside via the metadata service. The single richest credential-theft target.
- **S3** — object storage; the classic data-exfil and public-exposure target.
- **Lambda** — functions run with an execution role; `PassRole` + create/invoke is a privesc primitive.
- **RDS** — databases; snapshots are the exfil seam, public/shared snapshots the misconfiguration.
- **Secrets Manager / SSM Parameter Store** — where applications stash DB creds, API keys, tokens. A read permission here is often a pivot to everything else.
- **KMS** — encryption keys; grants and key policies gate access to encrypted S3/EBS/RDS.

### IAM model (the spine)
- **Users** — long-lived identities with **access keys** (`AKIA...` long-term, `ASIA...` temporary/STS). Keys are what leak in code, CI logs, laptops.
- **Roles** — assumable identities with **no long-term credentials**; assumption yields temporary STS creds (`ASIA...` + session token). Used by services (instance profiles, Lambda exec roles) and for cross-account access.
- **Policies** — JSON documents (`Effect`/`Action`/`Resource`/`Condition`). **Managed** (versioned, up to 5 versions, a default) vs **inline** (embedded in one principal). Permissions are the **union** of identity policies, with explicit `Deny` and SCP/permission-boundary/session-policy as ceilings.
- **Trust policy** (a.k.a. `AssumeRolePolicyDocument`) — the resource policy *on a role* naming who may `sts:AssumeRole` it. An attacker who can rewrite a trust policy (`iam:UpdateAssumeRolePolicy`) can add themselves as a trusted principal.
- **STS** — `AssumeRole`, `AssumeRoleWithWebIdentity`, `GetSessionToken`, `GetCallerIdentity`. `sts:AssumeRole` chains (A→B→C) are the lateral-movement graph; PMapper exists to compute exactly these reachability edges.
- **`iam:PassRole`** — the pivot permission: it does not act by itself but authorizes handing a role to a *service* (EC2, Lambda, Glue, CloudFormation, SageMaker, Data Pipeline) that will then run attacker-controlled code *as* that role. Almost every service-based privesc is `PassRole` + one service `Create/Run` action.

### Networking (VPC / SG / NACL)
- **Security Groups** — stateful, allow-only, instance-level. An open `0.0.0.0/0` on 22/3389/3306/5432 is the reconnaissance beacon and the ingress.
- **NACLs** — stateless, allow+deny, subnet-level. Rarely the exploited layer but shapes what's reachable.
- **Public subnets / IGW / Elastic IPs** — mark internet-reachable attack surface; CloudFox's `endpoints` and `instances` enumerate it.
- **VPC endpoints** — let instances reach AWS APIs without egress; relevant to detection (traffic stays in-VPC) and to `InsideAWS` GuardDuty variants.

### Storage (S3 / EBS / snapshots)
- **S3** — bucket ACLs (legacy), bucket policies, **Block Public Access** (account+bucket toggles), object ownership. Misconfig = public read/write/list, or a bucket policy trusting `*`/a wrong account.
- **EBS volumes & snapshots** — a snapshot can be shared to another account or made public (`ModifySnapshotAttribute` with `createVolumePermission=all`), then volume-restored under attacker control to read its filesystem (credentials, keys). Same pattern for **RDS snapshots** (`ModifyDBSnapshotAttribute` / `ModifyDBClusterSnapshotAttribute` with `all`).
- **AMIs** — can also be shared/public and may bake in secrets or user-data.

---

## Reconnaissance & enumeration

Order of operations: *who am I → what can I do → what is here → where can I pivot.*

### Account / identity enumeration
- `aws sts get-caller-identity` — the first call; returns the account id, the principal ARN (user vs assumed-role), and the user id. Unauthenticated-safe, logs to CloudTrail but is innocuous.
- **Account-id-from-key** — the account id is derivable offline from an `AKIA`/`ASIA` key id (no API call), useful to attribute a leaked key.
- **Unauthenticated enumeration of a trust boundary** — `iam:UpdateAssumeRolePolicy`-style principal-existence probing: a trust policy referencing a non-existent principal fails, so a role's trust document can be used to confirm whether external account/user/role ARNs exist. Known reconnaissance trick; noisy.
- **S3 bucket-name enumeration** — buckets are a **global namespace**; names are brute-forceable/predictable (`<company>-backups`, `-logs`, `-dev`). Public `ListBucket`/`GetObject` needs no credentials.

### Permission enumeration (what can this principal do?)
- **`enumerate-iam`** (andresriancho) — brute-forces `get*`/`list*`/`describe*` API calls with a set of keys to discover allowed actions **without** needing `iam:` read permission. Non-destructive by design (read-only verbs only). The go-to when you have keys but cannot read your own policy.
- **`iam:SimulatePrincipalPolicy`** — if allowed, authoritatively lists effective permissions.
- **Pacu `iam__enum_permissions`** — pulls the principal's attached/inline/group policies when `iam:List*`/`Get*` are available, and stores them in the Pacu DB for `iam__privesc_scan` to reason over.
- **`iam__enum_action_query`** (Rhino/Pacu) — queries the collected permission set to answer "which principals can do action X", used to triage privesc_scan output.

### Resource discovery
- **CloudFox `aws all-checks`** — the fastest single-command inventory: `inventory`, `endpoints` (internet-reachable), `instances`, `iam-simulator`/`permissions`, `principals`, `secrets` (Secrets Manager + SSM), `buckets`, `role-trusts`, `access-keys`, `route53`, `ecr`, `lambda`, `env-vars`, `databases` (RDS connection strings as loot), and `cape` (cross-account privesc paths — requires PMapper data). Read-only (Describe/List/Get); writes CSV/TXT + loot files with ready-made follow-up commands.
- **ScoutSuite** (`scout aws`) — multi-service posture snapshot as a browsable HTML report; good for a whole-account misconfig map (public S3, open SGs, weak IAM, missing encryption).
- **Pacu enum modules** — `ec2__enum`, `s3__enum` (plus bucket download), `lambda__enum`, `rds__enum`, `secrets__enum`, etc.
- **`aws` CLI recipes** — `aws iam list-users/list-roles/get-account-authorization-details`, `aws ec2 describe-instances`, `aws s3 ls`, `aws secretsmanager list-secrets`, `aws ssm describe-parameters`.

---

## IAM privilege escalation

**The spine of the skill.** The canonical corpus is **Rhino Security Labs' "21 IAM privilege-escalation methods"** (repo: `rhinosecuritylabs/aws-iam-privilege-escalation`), automated by **Pacu `iam__privesc_scan`** and modeled graph-wise by **PMapper**. Maps to **MITRE ATT&CK T1098 Account Manipulation** (and `T1098.001 Additional Cloud Credentials`, `T1548 Abuse Elevation Control Mechanism`, `T1078.004 Valid Accounts: Cloud`). Each path below is: *permission(s) held → action → result.*

### A. Direct policy / permission grants to self
1. **`iam:CreatePolicyVersion`** — create a new **default** version of a managed policy you can touch (`--set-as-default`), with `Action:*`/`Resource:*`. Bypasses needing attach rights. *(Rhino method #1.)*
2. **`iam:SetDefaultPolicyVersion`** — roll the default to an **existing** older version that was more permissive (CloudGoat `iam_privesc_by_rollback`).
3. **`iam:AttachUserPolicy`** — attach `AdministratorAccess` (or any managed policy) to yourself.
4. **`iam:AttachGroupPolicy`** — attach admin to a group you belong to.
5. **`iam:AttachRolePolicy`** — attach admin to a role you can assume.
6. **`iam:PutUserPolicy`** — write an inline admin policy onto yourself.
7. **`iam:PutGroupPolicy`** — inline admin onto your group.
8. **`iam:PutRolePolicy`** — inline admin onto an assumable role.
9. **`iam:AddUserToGroup`** — add yourself to a more-privileged group.

### B. New-credential / new-identity creation
10. **`iam:CreateAccessKey`** (on another user) — mint a second access key for a higher-privileged user and use it.
11. **`iam:CreateLoginProfile`** — set a console password on a user that has none (incl. higher-priv users).
12. **`iam:UpdateLoginProfile`** — reset another user's console password.
13. **`iam:CreateUser` + attach/put policy** — create a fresh admin user (persistence + privesc).

### C. Trust-policy / assume-role abuse
14. **`iam:UpdateAssumeRolePolicy` (+ `sts:AssumeRole`)** — rewrite a privileged role's **trust policy** to trust your principal, then assume it. (ATT&CK T1098.)
15. **`sts:AssumeRole` chains** — follow existing trust edges A→B→C to a more-privileged role (the reachability graph PMapper computes; CloudFox `cape` surfaces cross-account hops).

### D. `iam:PassRole` + a service that runs code (the big family)
Each needs **`iam:PassRole`** plus the service action, and a target role more privileged than you:
16. **`iam:PassRole` + `ec2:RunInstances`** — launch an instance with a privileged instance profile; read its creds from the metadata service (or via user-data/SSH).
17. **`iam:PassRole` + `lambda:CreateFunction` + `lambda:InvokeFunction`** — deploy a function assuming a privileged exec role; the code calls AWS as that role and exfils the STS creds.
18. **`iam:PassRole` + `lambda:CreateFunction` + `lambda:CreateEventSourceMapping`** — same, triggered by an event source instead of direct invoke (when `InvokeFunction` is denied).
19. **`iam:PassRole` + Glue (`glue:CreateDevEndpoint`/`UpdateDevEndpoint`)** — run code on a Glue dev endpoint as a passed role.
20. **`iam:PassRole` + CloudFormation (`cloudformation:CreateStack`)** — a stack template that creates privileged resources/roles under a passed role.
21. **`iam:PassRole` + Data Pipeline / SageMaker (`datapipeline:CreatePipeline`, `sagemaker:CreateNotebookInstance`/`CreateTrainingJob`)** — same primitive via other code-running services.

> **Authoring note:** teach these as *permission → consequence* pairs and always pair with the detection footprint (below). `iam__privesc_scan` enumerates the held set against this list and can auto-exploit; in a lab, run the scan, read the *finding*, and exploit a single path manually to understand the CloudTrail trail it leaves.

---

## Service exploitation

### EC2 — credential theft (highest value)
- **Instance Metadata Service (IMDS)** — `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` returns the instance profile's **temporary STS creds** (`ASIA...` + token). The classic path is an **SSRF in an app on the instance** reaching IMDS from inside.
  - **IMDSv1** — unauthenticated `GET`; any SSRF leaks creds. The exposed version.
  - **IMDSv2** — session-oriented: a `PUT` to `/latest/api/token` (with `X-aws-ec2-metadata-token-ttl-seconds`) returns a token required on subsequent `GET`s; a `hop-limit` of 1 stops the token hop from leaving the instance, defeating most SSRF. **F5 Labs observed active SSRF→IMDSv1 credential-theft campaigns in March 2025** — v1 is still the live risk where not enforced.
  - **Detection/awareness:** stolen instance creds used *off* the instance fire GuardDuty `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS`; used from another AWS account, `.InsideAWS`. Report as blast-radius: *"instance-profile creds for role X recovered; role X grants <scope>."*
- **User-data** — `GET /latest/user-data` (or `ec2:DescribeInstanceAttribute --attribute userData`) often contains bootstrap secrets, hardcoded creds, bootstrap scripts.
- **Snapshot/EBS theft** — `CreateSnapshot` of a volume → `ModifySnapshotAttribute createVolumePermission=all` (or share to attacker account) → restore a volume elsewhere and mount it to read credentials/keys from the filesystem. No DoS; read-only exfil of your own lab volumes.

### S3 — data exposure & exfil (ATT&CK T1619 Cloud Storage Object Discovery, T1530 Data from Cloud Storage)
- **Public/misconfigured access** — anonymous `ListBucket`/`GetObject` from a public ACL or bucket policy; `s3:GetBucketPolicy`/`GetBucketAcl` to read the grant; Block-Public-Access bypasses.
- **Policy/ACL abuse** — `s3:PutBucketPolicy`/`PutBucketAcl` to grant yourself or `*` access; `PutObject` to plant content (e.g., overwrite a config/JS served to users).
- **Object discovery** — `s3:ListBucket` across discovered buckets (T1619), then `GetObject` on interesting keys (backups, `.env`, tfstate, DB dumps).
- **Detection:** object-level `GetObject`/`PutObject` are **CloudTrail data events, off by default** — enumerate the trail config (`cloudtrail:GetEventSelectors`) to know whether object reads are even logged. Bucket-level actions (`PutBucketPolicy`) are management events, always logged.

### RDS — snapshot & access testing
- **Snapshot exfil** — `rds:CreateDBSnapshot` → `rds:ModifyDBSnapshotAttribute` (or `ModifyDBClusterSnapshotAttribute`) adding another account or `all` to `restore` → restore the snapshot under attacker control, *outside the victim's monitoring boundary*. ATT&CK **T1537 Transfer Data to Cloud Account**. Elastic/Datadog detections key on `ModifyDBSnapshotAttribute` with added accounts or `valuesToAdd` containing `all`.
- **Public accessibility** — `rds:ModifyDBInstance --publicly-accessible` + an open SG exposes the DB to the internet.
- **Credential testing** — against a reachable instance, test recovered/guessed DB creds (from Secrets Manager, user-data, or app config). **No brute-force that risks lockout/DoS; no load testing.**

### Lambda
- **Read code & env** — `lambda:GetFunction` (download the deployment package), `lambda:ListFunctions` + env vars often hold secrets/endpoints (CloudFox `env-vars`).
- **Exec-role theft** — if you can invoke or modify a function, its code runs as the exec role; `lambda:UpdateFunctionCode` to inject exfil of the role's STS creds (privesc paths 17–18).

### Secrets Manager / SSM Parameter Store
- **Secrets Manager** — `secretsmanager:ListSecrets` + `GetSecretValue`; a single read permission frequently unlocks DB creds, third-party API keys, OAuth tokens → pivot. Report as blast-radius, never the value.
- **SSM Parameter Store** — `ssm:DescribeParameters` + `GetParameter(s)`; `--with-decryption` on `SecureString` params (needs KMS `Decrypt`). CloudFox `secrets` pulls both.
- **SSM Run Command / Session** — `ssm:SendCommand` / `StartSession` against a managed instance = RCE on EC2 *without SSH/SG ingress* (as the instance's SSM role). A potent lateral-movement primitive.

---

## Detection surface (awareness, not evasion)

Purpose: a tester knows their footprint; a defender knows what to tune. **This section never teaches how to avoid logging** — it teaches what logging exists.

### CloudTrail (the API audit log)
- **Management events** — control-plane calls (IAM changes, `RunInstances`, `ModifyDBSnapshotAttribute`, `PutBucketPolicy`, `AssumeRole`, `CreateAccessKey`). **On by default**, logged in all regions when a trail is configured. Nearly every privesc action above is a management event and is recorded with `eventName`, `userIdentity`, `sourceIPAddress`, `userAgent`, request parameters.
- **Data events** — object/data-plane calls: S3 `GetObject`/`PutObject`, Lambda `Invoke`, DynamoDB item ops. **Off by default**, must be enabled per trail/selector → S3 object reads are often *not* logged. Knowing this is footprint-awareness, not evasion.
- **`userIdentity`** distinguishes `IAMUser` vs `AssumedRole` vs `Root`; `sourceIPAddress` + `userAgent` (e.g., `aws-cli`, `Boto3`, `pacu`) are the attribution fields. Using tooling default user-agents against your *own lab* is fine; the point is understanding what the defender sees.
- **`sts:GetCallerIdentity`, `s3:ListBucket`** etc. all log — recon is not invisible.

### GuardDuty (managed threat detection)
Fires findings off CloudTrail (management + S3 data events), VPC Flow Logs, and DNS logs. Relevant finding types to the techniques above:
- **`UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS`** (High) — instance-profile creds used from an IP outside AWS. The signature of EC2 metadata credential theft.
- **`UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.InsideAWS`** (High) — instance creds used from a *different* AWS account.
- **`CredentialAccess:IAMUser/AnomalousBehavior`** — unusual IAM/credential API activity vs the learned baseline.
- **`Persistence:IAMUser/AnomalousBehavior`**, **`PrivilegeEscalation:IAMUser/AnomalousBehavior`** — anomalous IAM mutation (e.g., attaching admin, creating users/keys) relative to baseline.
- **`UnauthorizedAccess:IAMUser/MaliciousIPCaller` / `TorIPCaller` / `ConsoleLoginSuccess.B`** — calls from known-bad or Tor IPs, console login anomalies.
- **`Exfiltration:S3/AnomalousBehavior`**, **`Impact:S3/*`** — unusual S3 access/exfil patterns (needs S3 protection).
- **`Policy:S3/BucketAnonymousAccessGranted`**, **`Policy:S3/BucketPublicAccessGranted`** — a bucket just made public.
- **`Stealth:IAMUser/CloudTrailLoggingDisabled`**, **`Stealth:IAMUser/PasswordPolicyChange`** — tamper indicators (named here so a tester understands these *would* fire; the skill does not teach disabling logging).

**Authoring rule:** every attack technique in the skill is paired with its CloudTrail `eventName` and the GuardDuty finding it tends to trigger, so the learner reasons about footprint. The skill never includes a "how to stay quiet" recipe against a non-owned target.

---

## Tools

| Tool | Purpose | Invocation (lab) | What it answers | Reference file |
|---|---|---|---|---|
| **Pacu** (`rhinosecuritylabs/pacu`) | AWS exploitation framework, 50+ modules (enum/privesc/persistence/exfil) | `pacu` → `set_keys` → `run iam__enum_permissions` → `run iam__privesc_scan`; `run ec2__enum`, `run s3__enum`, `run secrets__enum` | "Given these keys, which of the 21 privesc paths are open, and what does the account contain?" | `references/pacu.md` |
| **CloudFox** (`BishopFox/cloudfox`) | Read-only offensive enumeration; surfaces leads + follow-up commands | `cloudfox aws --profile <p> all-checks`; targeted: `... instances`, `... secrets`, `... endpoints`, `... cape` | "What's here, what's internet-reachable, where are the secrets, what cross-account privesc exists?" | `references/cloudfox.md` |
| **PMapper** (`nccgroup/PMapper`, pip `principalmapper`) | Graphs IAM principals/edges; computes privesc & reachability incl. SCP/boundaries | `pmapper graph create`; `pmapper query 'preset privesc *'`; `pmapper query 'who can do iam:CreateUser'`; `pmapper visualize` | "Who can escalate to admin, and by what edge chain?" | `references/pmapper.md` |
| **enumerate-iam** (`andresriancho/enumerate-iam`) | Brute-forces allowed `get*/list*/describe*` with no IAM read perm | `enumerate-iam.py --access-key ... --secret-key ...` | "With only these keys and no self-read, what actions are permitted?" | `references/pacu.md` (grouped) |
| **ScoutSuite** (`nccgroup/ScoutSuite`) | Multi-service posture audit → HTML report | `scout aws --profile <p>` | "Where are the account-wide misconfigs (public S3, open SGs, weak IAM, no encryption)?" | `references/cloudfox.md` (grouped) |
| **aws CLI recipes** | Primitive enumeration & targeted actions | `aws sts get-caller-identity`; `aws iam get-account-authorization-details`; `aws s3 ls`; `aws secretsmanager list-secrets`; `aws ssm describe-parameters` | "Ground-truth single calls behind the frameworks" | `references/s3-attacks.md` + inline |

Planned reference files: `references/pacu.md`, `references/cloudfox.md`, `references/pmapper.md`, `references/s3-attacks.md`, `references/lab-setup.md`.

---

## MITRE ATT&CK Cloud mappings (IaaS matrix)

| Technique | ID | Where it shows up here |
|---|---|---|
| Valid Accounts: Cloud Accounts | T1078.004 | Leaked/stolen access keys; assumed-role sessions |
| Account Manipulation | T1098 | IAM privesc spine (attach/put policy, trust rewrite) |
| Account Manipulation: Additional Cloud Credentials | T1098.001 | `CreateAccessKey`, `CreateLoginProfile` |
| Abuse Elevation Control Mechanism | T1548 | PassRole + service code execution |
| Unsecured Credentials: Cloud Instance Metadata API | T1552.005 | EC2 IMDS credential theft via SSRF |
| Unsecured Credentials: Credentials in Files / env | T1552.001 / .007 | user-data, Lambda env vars, SSM/Secrets |
| Cloud Service Discovery | T1526 | Service/resource enumeration |
| Cloud Infrastructure Discovery | T1580 | `describe-instances`, inventory |
| Cloud Storage Object Discovery | T1619 | S3 `ListBucket` sweeps |
| Data from Cloud Storage | T1530 | S3 `GetObject` exfil |
| Transfer Data to Cloud Account | T1537 | RDS/EBS snapshot shared to attacker account |
| Modify Cloud Compute Infrastructure (snapshot) | T1578.001/.002 | `CreateSnapshot` / `ModifySnapshotAttribute` |
| Impair Defenses: Disable Cloud Logs | T1562.008 | CloudTrail-disable (named for *detection awareness* only) |

---

## Owned-lab targets

All deployed into **owned accounts**, scope-filed, torn down after use.

### CloudGoat (`RhinoSecurityLabs/cloudgoat`) — Terraform, "vulnerable by design"
Scenario-based; deploys intentionally-vulnerable infra, then teardown. Scenarios to map (roster grows — verify against the repo's `scenarios/` dir at deploy time):
- **`iam_privesc_by_rollback`** (easy) — restricted user restores a prior permissive policy version (`SetDefaultPolicyVersion`).
- **`iam_privesc_by_attachment`** — privesc via attaching a role/policy to an instance.
- **`iam_privesc_by_key_rotation`** — privesc via minting access keys.
- **`ec2_ssrf`** — SSRF in a web app → EC2 metadata → keys.
- **`cloud_breach_s3`** — Capital-One-style SSRF→metadata→S3 exfil.
- **`lambda_privesc`** — PassRole + Lambda to escalate.
- **`rce_web_app`**, **`codebuild_secrets`**, **`ecs_takeover`**, **`ecs_efs_attack`**, **`sns_secrets`**, **`vulnerable_cognito`**, **`detection_evasion`** (lab-only), among others.
- `lab-setup.md` sketch — **prereqs:** Terraform, AWS CLI with an owned profile, Python 3; **deploy:** `./cloudgoat.py create <scenario>` (emits start creds + `start.txt`); **teardown:** `./cloudgoat.py destroy <scenario>` (always, to stop spend and remove exposure).

### flaws.cloud / flaws2.cloud (Scott Piper) — hosted CTF, no deploy
- **flaws.cloud** — 6 levels on S3 misconfig, IAM, and metadata (public bucket listing, over-permissive policy, instance-metadata key theft). Hosted by the author; nothing to deploy.
- **flaws2.cloud** — two tracks: **attacker** (container/ECS metadata, Cognito) and **defender** (log analysis). Teaches both the exploit and the CloudTrail/GuardDuty side — directly feeds the detection-surface section.
- `lab-setup.md` sketch — **prereqs:** AWS CLI, a browser; **deploy:** none (navigate the DNS chain / hosted site); **teardown:** none. These are read-only external targets the author authorizes for learning.

### IAM Vulnerable (`BishopFox/iam-vulnerable`) — Terraform IAM lab
- Deploys **250+ IAM resources** with **31 supported privesc paths** into your own account — the hands-on companion to the Rhino privesc list and to PMapper/`iam__privesc_scan`. Author Seth Art; **CloudFoxable** is the CTF-style successor.
- `lab-setup.md` sketch — **prereqs:** Terraform, an owned account/profile, `admin` to apply; **deploy:** `terraform init && terraform apply` (creates the vulnerable principals + a low-priv entry user); **exercise:** assume the entry user, run `pmapper graph create` / `pacu iam__privesc_scan`, walk each path; **teardown:** `terraform destroy` (removes all 250+ resources — mandatory; these are live privesc paths).

---

## How it feeds our skill (`security/cloud-attack-aws`)

| Research section here | Feeds `SKILL.md` / reference |
|---|---|
| AWS fundamentals as attack context | `SKILL.md` "Model: IAM-is-the-perimeter" framing + glossary |
| Reconnaissance & enumeration | `SKILL.md` "Recon" workflow → `references/cloudfox.md`, `references/pacu.md` |
| IAM privilege escalation (21 paths) | `SKILL.md` **core** "Privesc" section → `references/pmapper.md` (edges) + `references/pacu.md` (`iam__privesc_scan`) |
| Service exploitation (EC2/S3/RDS/Lambda/secrets) | `SKILL.md` "Service abuse" → `references/s3-attacks.md` (S3/exfil); EC2-IMDS & RDS-snapshot sub-sections |
| Detection surface (CloudTrail/GuardDuty) | `SKILL.md` "Footprint & detection awareness" — the always-paired column on every technique |
| Tools table | `references/{pacu,cloudfox,pmapper,s3-attacks}.md` one-per-tool |
| Owned-lab targets | `references/lab-setup.md` (CloudGoat / flaws / IAM-Vulnerable deploy+teardown) |
| ATT&CK mappings | `SKILL.md` technique-id tags on each procedure |

The skill's **five reference files**: `pacu.md`, `cloudfox.md`, `pmapper.md`, `s3-attacks.md`, `lab-setup.md`. Hard guardrails to carry into `SKILL.md`: authorized-owned-scope-only gate, detection-awareness-not-evasion, secrets-as-blast-radius-never-values, no-DoS.

---

## Sources

- Rhino Security Labs — 21 IAM privilege-escalation methods: https://rhinosecuritylabs.com/aws/aws-privilege-escalation-methods-mitigation/ and repo https://github.com/rhinosecuritylabs/aws-iam-privilege-escalation
- Pacu (framework + `iam__privesc_scan`, `iam__enum_action_query`): https://github.com/RhinoSecurityLabs/pacu ; Rhino action-query post https://rhinosecuritylabs.com/aws/iamactionhunter-aws-iam-permissions/
- CloudFox (Bishop Fox) + AWS Commands wiki: https://github.com/BishopFox/cloudfox ; https://github.com/BishopFox/CloudFox/wiki/AWS-Commands ; launch https://www.securityweek.com/bishop-fox-releases-open-source-cloud-hacking-tool-cloudfox
- PMapper (NCC Group): https://github.com/nccgroup/PMapper ; PyPI https://pypi.org/project/principalmapper/ ; DEF CON submission https://forum.defcon.org/node/237245
- ScoutSuite (NCC Group): https://github.com/nccgroup/ScoutSuite ; PyPI https://pypi.org/project/ScoutSuite/
- enumerate-iam (andresriancho): https://github.com/andresriancho/enumerate-iam
- IMDS / IMDSv2 & SSRF: Datadog https://securitylabs.datadoghq.com/articles/misconfiguration-spotlight-imds/ ; Christophe Tafani-Dereeper https://blog.christophetd.fr/imdsv2-enforcement/ ; F5-Labs 2025 SSRF campaign (via CSO) https://www.csoonline.com/article/3959148/
- GuardDuty IAM finding types: https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-iam.html ; all types https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-active.html
- CloudTrail management vs data events + RDS snapshot detections: Elastic https://www.elastic.co/guide/en/security/current/aws-rds-db-snapshot-shared-with-another-account.html ; Datadog https://docs.datadoghq.com/security/default_rules/cloudtrail-aws-rds-snapshot-exfiltration/
- CloudGoat (scenarios): https://github.com/RhinoSecurityLabs/cloudgoat ; CloudGoat 2 intro https://rhinosecuritylabs.com/aws/introducing-cloudgoat-2/
- IAM Vulnerable (Bishop Fox / Seth Art): https://bishopfox.com/tools/iam-vulnerable ; repo https://github.com/BishopFox/iam-vulnerable
- flaws.cloud / flaws2.cloud (Scott Piper): http://flaws.cloud/ ; http://flaws2.cloud/
- MITRE ATT&CK Cloud / IaaS matrix: https://attack.mitre.org/matrices/enterprise/cloud/iaas/
- Cloudsplaining privesc category reference: https://cloudsplaining.readthedocs.io/en/latest/glossary/privilege-escalation/
