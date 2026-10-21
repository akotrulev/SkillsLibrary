# Cloud Security Foundations (M1–M4)

**Scope:** Teachable, act-on-able facts from course modules **M1** (Intro to Cloud Computing & Cloud Security), **M2** (Cloud Architecture & Infrastructure Security), **M3** (Identity & Access Management), and **M4** (Cloud Network & Data Security). This is the base-layer knowledge base that feeds the cloud-security plan's cross-references and supplies the real-world context for `security/recon-enumeration` (the cloud-recon lane) and the provider deployment skills. Facts are verified against current (2026) vendor naming; naming changes are flagged inline.

Lab/defensive framing: everything here is for authorized self-testing, lab training, and defensive engineering on **owned accounts** only. The offensive facts (privilege-escalation paths, metadata abuse) are included so authored skills can **detect and prevent** them, not to target third parties.

---

## Core concepts

**Cloud computing** = on-demand, self-service, network-delivered, elastically-pooled, measured compute. The five NIST essential characteristics (on-demand self-service, broad network access, resource pooling, rapid elasticity, measured service) still frame every exam and every vendor's "what is cloud" page.

**Service models — who runs what:**

| Model | You get | Provider runs | You run | Security unit of work |
|---|---|---|---|---|
| **IaaS** | Raw VMs, disks, virtual networks | Hypervisor, physical host, network fabric | OS, runtime, app, data, patching | Harden the guest OS, patch, configure the network |
| **PaaS** | Managed runtime / DB / app platform | OS, runtime, patching, scaling | App code, data, access config | Secure the app, its identities, its data |
| **FaaS** (a PaaS sub-model) | Event-driven functions | Everything up to the function handler | Function code, its IAM role, event-source config | Least-privilege the execution role; validate event input |
| **SaaS** | Finished application | The whole stack | Your data, users, and tenant config | Identity, sharing settings, data governance |

**FaaS** (serverless functions): AWS Lambda · Azure Functions · Google Cloud Run functions (formerly "Cloud Functions"; Google folded 1st/2nd-gen Cloud Functions into Cloud Run functions). Billed per-invocation/per-ms; no server to patch; the **execution role is the whole attack surface you own**.

**Three-cloud equivalence map (key primitives):**

| Primitive | AWS | Azure | GCP |
|---|---|---|---|
| **VM / compute** | EC2 | Virtual Machines (VM) | Compute Engine |
| **Autoscale group** | EC2 Auto Scaling Group | Virtual Machine Scale Sets (VMSS) | Managed Instance Group (MIG) |
| **Serverless functions** | Lambda | Azure Functions | Cloud Run functions |
| **Managed Kubernetes** | EKS | AKS | GKE |
| **Object storage** | S3 | Blob Storage (in a Storage Account) | Cloud Storage |
| **Block storage** | EBS | Managed Disks | Persistent Disk / Hyperdisk |
| **File storage** | EFS | Azure Files | Filestore |
| **Virtual network** | VPC (**per-region**, subnets per-AZ) | VNet (per-region) | VPC (**global**, subnets per-region) |
| **Stateful firewall on a workload** | Security Group (allow-only, stateful) | Network Security Group (NSG — allow **and** deny, priority-ordered) | VPC firewall rules (allow **and** deny, priority-ordered) |
| **Subnet-level ACL** | Network ACL (stateless) | NSG at subnet scope | VPC firewall rules / Hierarchical firewall policies |
| **Identity principal — human** | IAM User / Identity Center (SSO) user | Entra ID user (**formerly Azure AD**) | Cloud Identity / Workspace user |
| **Identity principal — workload** | IAM Role (via instance profile / execution role) | Managed Identity (system- or user-assigned) | Service Account (an identity **and** a resource) |
| **Permission grant** | IAM Policy (JSON, attached to principal or resource) | Role assignment (role definition + scope) | IAM binding (member → role → resource) |
| **Key management (KMS)** | AWS KMS | Azure Key Vault (keys) / Managed HSM | Cloud KMS |
| **Secrets store** | AWS Secrets Manager (also SSM Parameter Store SecureString) | Azure Key Vault (secrets) | Secret Manager |
| **Audit / activity log** | CloudTrail (API audit) + CloudWatch (metrics/logs) | Azure Monitor + Entra sign-in/audit logs + Activity Log | Cloud Logging (Cloud Audit Logs) + Cloud Monitoring |
| **Posture / CSPM native** | Security Hub + Config + GuardDuty | Microsoft Defender for Cloud | Security Command Center |

**Naming facts worth pinning (verified 2026):**
- **Microsoft Entra ID** is the current name for what was **Azure Active Directory / Azure AD** (renamed 2023; no 2026 re-rename). Entra ID Free/P1/P2 are the editions. **Not renamed:** Windows Server AD, AD FS/AD DS, Azure AD B2C, Microsoft Graph, MSAL. Expect "Azure AD" in older docs and in some API/field names.
- **Azure Key Vault holds keys AND secrets AND certificates in one service** — unlike AWS/GCP, which split keys (KMS) from secrets (Secrets Manager / Secret Manager).
- **GCP VPCs are global**; AWS and Azure virtual networks are regional. This changes segmentation design: a GCP subnet is regional inside a global VPC.
- **GCP service accounts are both an identity and a resource** — you can grant others permission *on* a service account (e.g. `iam.serviceAccounts.actAs`), which is itself a privilege-escalation lever.

---

## Shared Responsibility Model

The constant: **the provider secures the cloud; the customer secures what they put in the cloud.** The line moves left (more on the customer) for IaaS and right (more on the provider) for SaaS. **Three things are ALWAYS the customer's, in every model:** your **data**, your **identities/access config**, and (almost always) **client-side/endpoint** and account/tenant configuration.

| Layer | IaaS | PaaS | FaaS | SaaS |
|---|---|---|---|---|
| Physical datacenter, hardware, hypervisor | Provider | Provider | Provider | Provider |
| Network infrastructure / host OS | Provider | Provider | Provider | Provider |
| Guest OS + patching | **Customer** | Provider | Provider | Provider |
| Runtime / middleware | **Customer** | Provider | Provider | Provider |
| Application code | **Customer** | **Customer** | **Customer** (handler only) | Provider |
| Identity & access management | **Customer** | **Customer** | **Customer** | **Customer** |
| Network / firewall config (SG/NSG) | **Customer** | **Customer** (where exposed) | **Customer** (where exposed) | n/a (vendor) |
| Data (classification, encryption choice, retention) | **Customer** | **Customer** | **Customer** | **Customer** |
| Data residency / tenant config / sharing | **Customer** | **Customer** | **Customer** | **Customer** |

**Concrete examples (useful in a SKILL.md):**
- **IaaS:** You launch an EC2 instance. AWS guarantees the hypervisor isolates you from other tenants. **You** must patch the OS, close the SSH port in the Security Group, enforce IMDSv2, and encrypt the EBS volume. An unpatched Log4Shell on that box is 100% on you.
- **PaaS:** You deploy to Azure App Service. Microsoft patches the OS and runtime. **You** still own the app's auth, the connection string in Key Vault (not in code), and whether the app is public.
- **FaaS:** A Lambda's provider surface is nil for OS/patching. The customer surface collapses to **the execution role** (over-permission it and a code-injection bug becomes account takeover) and **event input validation**.
- **SaaS:** Microsoft 365 / Salesforce. The provider runs everything. Breaches here are nearly always **customer misconfiguration**: public sharing links, no MFA, over-broad OAuth app consent, admin accounts without conditional access.

**The misconfiguration corollary:** because identity, network exposure, and data config are customer-owned at *every* model, the dominant cause of cloud incidents is customer misconfiguration, not provider compromise. Authored skills should assume the vulnerability is in the customer's config, not the provider's stack.

---

## IAM deep dive

**Authentication (authn) vs Authorization (authz):**
- **Authn = who are you** — proving identity (password + MFA, certificate, federated token, workload identity). Failure mode: credential theft, phishing, no MFA.
- **Authz = what may you do** — evaluating a policy against a request. Failure mode: over-permissive policy, wildcard actions, privilege escalation.
- They are separate layers: a valid token (authn passed) with an over-broad policy (authz failed) is the classic breach path. **MFA fixes authn; least privilege fixes authz.** You need both.

**Principals, roles, policies, permissions — per cloud:**

- **AWS:** An **IAM Policy** is a JSON document (`Effect` Allow/Deny, `Action`, `Resource`, `Condition`) attached to a **principal** (user/group/role) or to a **resource** (bucket policy, KMS key policy, role trust policy). Evaluation: a request is denied by default, allowed only if explicitly allowed and not explicitly denied across **all** layers — identity policy, resource policy, SCP (Service Control Policy at the org), permission boundary, and session policy. **Roles are assumed** (temporary STS credentials); workloads get roles via **instance profiles** (EC2) or **execution roles** (Lambda/ECS). There is no distinct "service account" object.
- **Azure:** **RBAC** separates the **role definition** (a set of `Actions`/`NotActions`/`DataActions`) from the **role assignment** (principal + role + **scope**). Scopes nest: management group → subscription → resource group → resource, and assignments **inherit downward**. The model is **additive with no general Deny** — permissions only add up (limited **deny assignments** exist, mostly via Azure Blueprints/managed apps). Workload identities are **managed identities** (system-assigned, tied to a resource lifecycle; or user-assigned, standalone and reusable).
- **GCP:** An **IAM binding** maps a **member** (user, group, service account, or domain) to a **role** on a **resource**, inheriting down the resource hierarchy (organization → folder → project → resource). Roles are **basic** (Owner/Editor/Viewer — avoid), **predefined** (per-service, least-privilege), or **custom**. **Service accounts are first-class resources** — you grant roles *to* them and *on* them. **Organization Policies** (and VPC Service Controls) act as guardrails above IAM.

**Privileged Access Management (PAM):** controls for the high-blast-radius identities (admins, break-glass, root/owner). Core practices: **just-in-time (JIT) elevation** (Entra **Privileged Identity Management / PIM**; AWS via permission sets + short STS sessions; GCP **Privileged Access Manager**), **time-bound/approval-gated** role activation, **separation of duties**, **no standing admin**, hardware MFA on break-glass accounts, and **full session audit**. Lock down the account root/owner: AWS root with hardware MFA and no access keys; GCP avoid basic `Owner`; Azure limit Global Admins and require PIM activation.

**Top IAM misconfigurations (the detection/prevention targets):**

| Misconfiguration | Why it's dangerous | What a skill should flag |
|---|---|---|
| **Overly-permissive policy** | Grants far beyond the task; blast radius on compromise | `Action: "*"` / `Resource: "*"`; AWS managed `AdministratorAccess` on a workload role; GCP basic `Owner`/`Editor`; Azure `Owner`/`Contributor` at subscription scope |
| **Wildcard actions** | `s3:*`, `iam:*` grant unknown future actions too | Any `*` in an action segment on a non-admin principal |
| **`iam:PassRole` + wildcard resource** | Lets a principal pass **any** role to a service (Lambda/EC2) and inherit its privileges → escalation to admin | `iam:PassRole` with `Resource: "*"`; isolate PassRole in its own statement with a tight resource |
| **Unused / long-lived credentials** | Stale access keys and accounts widen the attack surface; keys don't rotate | Access keys older than ~90 days, never-used users, inactive roles; prefer temporary STS / workload identity |
| **Missing MFA** | Authn collapses to a single stolen secret | Any console user without MFA; root/owner without hardware MFA |
| **Trust-policy flaws** | A role's `AssumeRole` trust with no `Condition` (principal ARN, `ExternalId`, MFA) lets any in-account (or cross-account) principal assume it | `Principal: "*"` or over-broad account trust; missing `sts:ExternalId`/`aws:PrincipalArn` condition; the "confused deputy" cross-account case |
| **Privilege-escalation-enabling permissions** | A low-priv identity holding one of these can reach admin | `iam:CreatePolicyVersion` / `iam:SetDefaultPolicyVersion`, `iam:AttachUserPolicy`, `iam:PutUserPolicy`, `iam:CreateAccessKey` (on others), `lambda:CreateFunction`+`iam:PassRole`, `iam:UpdateAssumeRolePolicy`, GCP `iam.serviceAccounts.actAs`/`getAccessToken`/`setIamPolicy`, Azure write on role assignments. Rhino Security Labs documented **21 AWS escalation methods**; map paths with PMapper / Cloudsplaining / Prowler. |

---

## Network & data security

**Segmentation:**
- **VPC/VNet** is the isolation boundary. Split workloads across **public** (has a route to an Internet Gateway) and **private** (no inbound internet; egress via NAT) subnets. Put databases and app tiers in private subnets; only load balancers / bastions in public ones.
- **AWS VPC = per-region**, subnets pinned to an AZ. **Azure VNet = per-region**. **GCP VPC = global**, subnets regional. Peer/transit to connect (VPC Peering, AWS Transit Gateway, Azure VNet peering/Virtual WAN, GCP VPC Peering/Network Connectivity Center).
- **Micro-segmentation:** tie Security Groups/NSGs to roles so tiers only talk to the tiers they must (web → app → db), never flat east-west reachability.

**Firewall / SG / NSG model — the key distinctions:**
- **AWS Security Group:** instance/ENI-level, **stateful**, **allow-rules only** (no deny), implicit deny-all. Can reference **other security groups** as source (identity-based microsegmentation).
- **AWS Network ACL (NACL):** subnet-level, **stateless** (must allow return traffic explicitly), supports allow **and** deny, numbered/ordered.
- **Azure NSG:** attachable to subnet **or** NIC, **stateful**, supports allow **and** deny, **priority-ordered** (lowest number wins), with default rules you can't delete.
- **GCP VPC firewall rules:** network-level, **stateful**, allow **and** deny, **priority-ordered**, target by network tag or service account — plus **hierarchical firewall policies** at org/folder scope.
- Rule of thumb for skills: SG = "who can talk to this workload" (allow-list, stateful); NACL = coarse stateless subnet guard; NSG/GCP rules combine both and need deny + priority reasoning.

**Instance metadata — a cloud-specific network/data risk (teach prominently):**
- The metadata endpoint `169.254.169.254` hands out the workload's **IAM credentials**. An SSRF or proxy bug that reaches it = credential theft = the identity's full privileges. This is the mechanism behind the 2019 Capital One breach.
- **AWS IMDSv2** mitigates it: session-token-based, requires a `PUT` to get a token then the token on `GET`, blocks the simple SSRF `GET`, and defaults to a low hop limit so containers/SSRF can't trivially reach it. **Enforce IMDSv2** (set `HttpTokens: required`): Amazon Linux 2023 AMIs ship `ImdsSupport=v2.0`; enforce account-wide via IMDS defaults and Organizations **declarative policies**; the `ec2:RoleDelivery=2.0` condition key rejects IMDSv1-sourced credentials. Detect residual IMDSv1 via the CloudWatch `MetadataNoToken` metric.
- Azure (IMDS) and GCP (metadata server) have analogous endpoints; GCP mitigates with required `Metadata-Flavor: Google` header. Treat all three as "never reachable from user-controllable request paths."

**Cloud storage exposure (the #1 headline-breach class):**
- **Public object storage** — S3 buckets, Azure Blob containers, GCS buckets accidentally world-readable — is the canonical cloud data leak. Controls: **S3 Block Public Access** (account + bucket level, on by default for new buckets), **bucket owner enforced / ACLs disabled**, Azure **"Allow Blob public access" = disabled** on the storage account + private containers, GCS **Public Access Prevention** (org-policy enforceable) + **uniform bucket-level access** (disable legacy per-object ACLs).
- Beyond public: enable access logging, versioning, object-lock/immutability for ransomware resilience, and VPC-private access (S3 Gateway Endpoints, Azure Private Endpoints, GCP VPC Service Controls) so data never traverses the public internet.

**Encryption:**
- **At rest:** on by default on all three for managed storage (S3 SSE, EBS, Azure Storage Service Encryption, GCS/Persistent Disk) with provider-managed keys. Upgrade to **customer-managed keys (CMK)** for control, rotation, and revocation (crypto-shredding). Key choice ladder: provider-owned → provider-managed → **customer-managed (CMK)** → customer-supplied/HSM.
- **In transit:** TLS everywhere; enforce with bucket/policy conditions (`aws:SecureTransport`), HTTPS-only app gateways, and no cleartext internal hops.

**KMS & key policies:**
- **AWS KMS:** keys are gated by a **key policy** (resource policy on the key) **plus** IAM — a principal needs allow in both (unless the key policy delegates to IAM). Enable **automatic annual rotation**; use **grants** for scoped temporary access; keys are regional. **Azure Key Vault / Managed HSM:** access via RBAC (data-plane roles) or legacy access policies; keys, secrets, certs together; enable purge protection + soft delete. **GCP Cloud KMS:** key rings → crypto keys with IAM bindings and rotation schedules; CMEK integrates into most services.
- Key-policy pitfalls to flag: a KMS key policy that grants `kms:*` to the whole account / `Principal: "*"`, no rotation, no separation between key admins and key users.

**Secrets management:**
- **Never** hardcode secrets in code, `appsettings.json`, `application.yml`, container images, env-var manifests, or CI logs. Use **AWS Secrets Manager** (native rotation via Lambda) or SSM Parameter Store SecureString · **Azure Key Vault secrets** (referenced from App Service/AKS via managed identity) · **GCP Secret Manager** (versioned, IAM-gated).
- Best practice chain: app authenticates with a **workload identity** (instance role / managed identity / service account) → fetches the secret at runtime from the secrets store → secret is **rotated** automatically → access is **audited**. No secret ever lands in source control or an image layer.

---

## Common threats & risks

The canonical cloud risk list (aligns with CSA **Top Threats** — misconfiguration ranked **#1** in the 2024 edition — and OWASP **A05 Security Misconfiguration** / Cloud-Native guidance):

1. **Misconfiguration & inadequate change control** — the #1 cloud threat. Public buckets, open security groups, default-open NSGs, logging disabled. Root cause: human error, speed, no guardrails.
2. **Identity & access failures** — over-permissioned identities, wildcard policies, no MFA, standing admin, stale credentials. The most-exploited post-initial-access lever.
3. **Insecure interfaces & APIs** — exposed management APIs, unauthenticated endpoints, over-broad OAuth app consent (SaaS).
4. **Exposed instance metadata / SSRF → credential theft** — the IMDSv1 class; cloud-specific and high-impact.
5. **Credential & secret leakage** — keys in Git, in images, in CI logs, in client bundles; long-lived access keys.
6. **Public data exposure** — world-readable object storage, public snapshots/AMIs, public databases (unauthenticated Mongo/Elastic/Redis).
7. **Account / tenant hijacking** — phished admin, no conditional access, token theft.
8. **Insufficient logging & monitoring / limited cloud visibility** — CloudTrail/Activity Log/Audit Logs off or unreviewed; no way to detect or investigate.
9. **Insecure control plane & "metastructure" failures** — weaknesses in the management plane and its APIs; the control-plane is the keys-to-the-kingdom.
10. **Privilege escalation & lateral movement** — the IAM-permission chains (PassRole, policy-version swaps, `actAs`) that turn a foothold into admin; cross-account trust abuse.
11. **Shared-technology / tenant-isolation & supply-chain risks** — vulnerable images, compromised third-party dependencies, and the rare multi-tenant isolation failure.

**Framing for skills:** items 1, 2, 5, 6 cause the overwhelming majority of real cloud breaches and are **all customer-owned config** per the Shared Responsibility Model. Prioritize detection/prevention there over exotic provider-stack attacks.

---

## How it feeds our skills

| Fact set here | Lands in | As |
|---|---|---|
| Equivalence map, service models, shared-responsibility matrix | `devops/cloud-posture`, `devops/aws-deployment`, `devops/azure-deployment` | The baseline "what exists / who owns what" every posture check and deployment recipe assumes |
| Storage-exposure controls (Block Public Access, Public Access Prevention, uniform access), SG/NSG/firewall models, IMDSv2 enforcement | `devops/cloud-posture`, `devops/iac-security` | Concrete misconfiguration checks and IaC guardrails to author/scan for |
| IAM principal/policy models per cloud, PAM, top IAM misconfigurations, privilege-escalation permission list | `devops/cloud-posture` (least-privilege review) + `devops/threat-modeling` (identity attack paths) | The IAM-finding catalog and the trust boundaries a threat model draws |
| Canonical threat & risk list, metadata abuse, credential leakage | `devops/threat-modeling` | The STRIDE/attack-path seed list for cloud assets |
| Metadata endpoints, privilege-escalation chains, public-exposure signatures, trust-policy flaws | `security/recon-enumeration` (cloud-recon lane) | Real-world context for what to enumerate and why (owned-account, authorized only) — and what the matching defensive skills must detect |
| KMS/key-policy pitfalls, secrets-management chain | `devops/cloud-posture`, `security/secrets-hardening` | Encryption/secrets review items; "no secret in code/image/CI" rule |
| Entra ID / Cloud Run functions / Key Vault naming facts | All provider-touching skills | Keeps generated content on current product names (and aware of legacy "Azure AD" field names) |

**Boundary note:** this file is foundations only. Per-service hardening recipes, IaC rule syntax, and enumeration tooling live in the respective skills — this is the shared fact base they cite, not a replacement for them.

---

## Sources

- [Azure Active Directory is now Microsoft Entra ID (rename, editions, what stayed)](https://kb.filewave.com/books/identity-provider-idp-integration/page/azure-active-directory-is-now-microsoft-entra-id)
- [Microsoft Entra ID — the new name for Azure Active Directory](https://getnerdio.com/blog/microsoft-entra-id-the-new-name-for-azure-active-directory/)
- [AWS — Transition to using Instance Metadata Service Version 2 (IMDSv2)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-transition-to-version-2.html)
- [EC2 instances should enforce IMDSv2 (ImdsSupport, account enforcement, declarative policy, MetadataNoToken)](https://docs.datadoghq.com/security/default_rules/aws-ec2-instance-ec2-instances-should-enforce-imdsv2)
- [AWS KMS vs Azure Key Vault vs GCP Cloud KMS](https://www.encryptionconsulting.com/aws-kms-vs-azure-key-vault-vs-gcp-kms/)
- [AWS ↔ Azure ↔ GCP — Service Equivalents (mind map)](https://www.aguidetocloud.com/mind-maps/aws-azure-gcp-equivalents/)
- [How to map AWS services to GCP equivalents (compute/storage/network scope differences)](https://oneuptime.com/blog/post/2026-02-17-how-to-map-aws-services-to-gcp-equivalents-during-cloud-migration/markdown)
- [Tenable — AWS, Azure and GCP: the ultimate IAM comparison](https://www.tenable.com/blog/aws-azure-and-gcp-the-ultimate-iam-comparison)
- [Access Control in Cloud Security Across AWS, Azure & GCP](https://securityboulevard.com/2026/02/access-control-in-cloud-security-across-aws-azure-gcp/)
- [AWS Security Blog — How to use the PassRole permission with IAM roles](https://aws.amazon.com/blogs/security/how-to-use-the-passrole-permission-with-iam-roles/)
- [Rhino Security Labs — AWS IAM Privilege Escalation (21 methods)](https://rhinosecuritylabs.com/aws/aws-privilege-escalation/)
- [Cloudsplaining — Privilege Escalation glossary](https://cloudsplaining.readthedocs.io/en/latest/glossary/privilege-escalation/)
- [Prowler — IAM inline policy allows privilege escalation](https://hub.prowler.com/check/iam_inline_policy_allows_privilege_escalation)
- [CSA — Top Threat #1: Misconfiguration (2024 Top Threats series)](https://cloudsecurityalliance.org/blog/2024/08/20/top-threat-1-misconfig-misadventures-taming-the-change-control-chaos)
- [CSA Top Threats to Cloud Computing "Pandemic 11" (summary)](https://vmblog.com/news/cloud-security-alliances-top-threats-to-cloud-computing-pandemic-11-report-finds-traditional-cloud-security-issues-becoming-less-concerning/)
