---
name: cloud-recon-enumeration
description: Use to map a cloud account's control-plane attack surface at the start of an authorized cloud pentest — public storage/DNS surface, the instance metadata service, IAM/principal/permission enumeration, OIDC/federation trust — provider-agnostic (AWS/Azure/GCP), under a committed cloud scope file. Triggers "enumerate our AWS account", "recon this authorized cloud tenant", "what can this credential do". Not for network/host recon (`recon-enumeration`), defensive posture benchmarking (`devops:cloud-posture`), or provider-specific exploitation (`cloud-attack-aws` / `cloud-attack-azure` / `cloud-attack-gcp`). Owned/lab accounts only, under a committed cloud scope file.
---

# Penetration Testing — Cloud Recon & Enumeration (ScoutSuite · cloud_enum · metadata service · enumerate-iam)

Cloud recon is the first step of an authorized cloud kill chain, and it differs from a network/host recon in one load-bearing way: **there is no wire to scan — the attack surface is the provider's control-plane API**, and every call you make is an authenticated act attributable to a principal and logged in the provider's own audit trail (CloudTrail, Azure Activity Log + Entra sign-in logs, GCP Cloud Audit Logs). You turn "here is an account/subscription/project in scope" into "here is what is publicly exposed, what the metadata service hands out, and what a held credential can actually reach" — a lead set the provider-specific exploitation skills (`cloud-attack-aws`, `cloud-attack-azure`, `cloud-attack-gcp`) chain into impact. This skill finds; it does not exploit.

> **⚠️ Authorized self-testing only — owned/lab cloud accounts, under a committed cloud scope file.** This skill enumerates **your own** cloud account(s) — or a designated training lab (CloudGoat, AzureGoat, GCPGoat, flaws.cloud, IAM Vulnerable) — to find what an attacker would find before they do. Every run is gated by a committed **cloud scope file** and its `#volatile` authorization line, which **expires**: never cached as durable, re-confirmed each engagement. The scope file's in-scope account/subscription/project ids and regions are the **only** things you may touch; its hard exclusions (shared-services accounts, production data stores, other tenants) are never touched even if reachable; a blast-radius cap bounds every enumeration pass. Production is a separate, louder sign-off than a lab target. **Read the scope file before every act; if the next act would fall outside it, halt the run and report.**

```
Authorization: cloud-scope=<account/subscription/project ids>  regions=<in-scope regions>
               exclusions=<never-touch accounts/tenants>  authorized-by=<name>
               window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (every tool here is a Python CLI or Go/Python script against a provider API — no per-stack split, per the library's anti-triplication rule) and is loaded by the **`penetration-tester`** agent as the cloud analogue of its **Recon** step. It is the **shared entry skill** the three provider skills bind to: `cloud-attack-aws`, `cloud-attack-azure`, and `cloud-attack-gcp` each consume the reachable-credential and principal/permission leads this skill produces, then chain them into provider-specific privilege escalation and service abuse. It owns recon only — it does **not** exploit a finding (that is the provider skills' job), benchmark defensive posture (`devops:cloud-posture`), or enumerate a network/host surface (`penetration-testing:recon-enumeration`).

> **The spine is MITRE ATT&CK Cloud** (IaaS · Identity Provider · SaaS matrices), **not Enterprise** — a cloud finding is mis-mapped if tagged with a host-centric Enterprise id. Every technique below carries its Cloud-matrix id: `T1580` Cloud Infrastructure Discovery, `T1526` Cloud Service Discovery, `T1619` Cloud Storage Object Discovery, `T1552.005` Unsecured Credentials: Cloud Instance Metadata API, `T1087.004` Account Discovery: Cloud Account. Severity is scored **CVSS** in the final report (`penetration-testing:reporting`), not the blocker/major/minor/nit table.

## How a cloud recon differs from a network/host recon

| Network/host recon (`recon-enumeration`) | Cloud recon (this skill) |
|---|---|
| Attack surface = open ports + service fingerprints | Attack surface = the **provider's control-plane API** + IAM policy + resource config |
| Quiet scanning is possible (passive index reads, low-rate sweeps) | **There is no quiet scan** — every authenticated call is logged against a principal in the audit trail |
| "Root" on a box is the objective | **Rooting a workload is a means to its metadata-service credentials**, not the goal |
| Pivot over L3/L4 | Pivot by `AssumeRole` / token exchange / service-account impersonation |
| One shared ATT&CK Enterprise spine | **ATT&CK Cloud** (IaaS/Identity Provider/SaaS) |

**Control plane vs data plane** is the distinction every finding is framed against. The **control plane** is the management API that creates, configures, and describes resources (`ec2:DescribeInstances`, `s3:ListAllMyBuckets`, `iam:ListRoles`, ARM `Microsoft.*/read`, GCP `*.get`/`*.list`) — this is where recon, IAM enumeration, and most privilege escalation live, and it is logged by default. The **data plane** is operations on a resource's *contents* (`s3:GetObject`, a DynamoDB item read, `kms:Decrypt`) — this is where blast-radius is realized, and data-plane events are frequently **not** logged by default (S3 object-level access, GCP Data Access logs are opt-in). Consequence for this skill: **you enumerate on the control plane, and you report impact as the data-plane blast-radius a reachable permission implies** — "principal P can `s3:GetObject` on bucket X, which holds category Y" — never the object contents themselves.

## Enumeration posture: anonymous first, then authenticated

Run recon in two passes, escalating only once the first has nothing left to give:

1. **Anonymous (unauthenticated) enumeration** — no credentials held. Works against the **public** surface: predictable storage endpoints, public DNS/TLS certificates, exposed metadata, unauthenticated APIs, leaked artifacts. Attributable to no principal on the target side (your source IP is still logged by whatever resource you touch). `cloud_enum` lives here.
2. **Authenticated enumeration** — a credential is in hand (a leaked key, an assumed test role, a metadata-service token). The **first call is always "who am I and what can I do"**: `aws sts get-caller-identity`, `az account show` / `az ad signed-in-user show`, `gcloud auth list` + `gcloud config list`. Every subsequent call is logged against that principal — enumeration here is attributable by construction, which is the awareness point for the defensive side, not a reason to avoid it under authorization.

A clean engagement runs anonymous first (cheaper, quieter, maps the external surface), then pivots to authenticated once a foothold credential exists — from a leaked secret, a public resource that discloses one, or the metadata service below.

## Public-asset & storage discovery

Object-storage endpoints are **globally predictable DNS names**, brute-forceable by permuting an org's name against common affixes (`-dev`, `-backups`, `-assets`, `-logs`, `-prod`). The response code distinguishes *doesn't-exist* (404) from *exists-but-protected* (403) from *exists-and-public* (200/listing) — that three-way split is the entire technique:

- **AWS S3** — `<bucket>.s3.amazonaws.com` / `<bucket>.s3.<region>.amazonaws.com`; a public listing returns XML `ListBucketResult`.
- **Azure Blob** — `<account>.blob.core.windows.net/<container>?restype=container&comp=list`; also check `file.`/`queue.`/`table.` endpoints and `<app>.azurewebsites.net`.
- **GCP GCS** — `storage.googleapis.com/<bucket>` / `<bucket>.storage.googleapis.com`.
- **Supporting surface:** certificate-transparency logs (crt.sh) and passive DNS surface subdomains that map to cloud front-ends — `*.cloudfront.net`, `*.azureedge.net`, GCP load-balancer IPs reveal provider footprint even before a direct storage hit.

This is **`T1619` Cloud Storage Object Discovery** (anonymous half) — see `references/cloud-enum.md`.

## The instance metadata service — IMDSv1/v2, SSRF→credentials, T1552.005

The single most important **SSRF-to-credentials** primitive in cloud pentesting: a compute instance with an attached role/identity exposes temporary credentials on a link-local address the workload itself can reach, so any SSRF or RCE landing on that workload reaches the credentials too. This is **`T1552.005` — Unsecured Credentials: Cloud Instance Metadata API**.

- **AWS** `http://169.254.169.254/latest/meta-data/` — role credentials at `.../iam/security-credentials/<role-name>`. **IMDSv1** is a bare unauthenticated `GET` — no header, no token, no handshake; any SSRF that can issue a GET harvests the role's keys outright. **IMDSv2** requires a two-step session: `PUT .../latest/api/token` with `X-aws-ec2-metadata-token-ttl-seconds` returns a token, and every subsequent `GET` must carry `X-aws-ec2-metadata-token: <token>` — this blocks the common SSRF shape because most SSRF primitives can only force a GET and cannot set arbitrary headers or issue a PUT. The response additionally carries a configurable **hop limit** (default 1) that prevents the token/response leaving the instance; a container on the host counts as an extra hop, so reaching IMDS from a container needs hop limit 2 — which re-widens the SSRF path, a deliberate trade-off to flag rather than a default to recommend.
- **Azure** `http://169.254.169.254/metadata/instance?api-version=...` and `.../metadata/identity/oauth2/token?resource=...` — **requires the header `Metadata: true`**, a built-in anti-SSRF guard; a naive GET with no header fails.
- **GCP** `http://metadata.google.internal/computeMetadata/v1/` — **requires header `Metadata-Flavor: Google`**; a service-account token lives at `.../instance/service-accounts/default/token`.

**What to actually check (control-plane read, not endpoint-hammering):** whether an instance's `MetadataOptions` enforce `HttpTokens=required` (v2-only) or still accept v1 (the **dual-accept** finding — IMDSv2 has been the EC2-console default since Nov 2023, but plenty of brownfield instances still launch v1-optional, and v1 is a documented **live risk**: an active SSRF→IMDSv1 credential-theft campaign was reported in the wild in March 2025). Report the finding as the configuration state, and where an SSRF chain is proven, report the **role's blast-radius** (what it can reach) — never the key material. See `references/metadata-service.md`.

## IAM / principal / permission enumeration

Once a credential is in hand — anonymous discovery, metadata service, or a provided test key — map **who it is** and **what it can do**, provider-agnostically: identity → attached/inline policies → effective permissions → reachable roles.

- **Whoami, always first:** `aws sts get-caller-identity`; `az account show` / `az ad signed-in-user show`; `gcloud auth list` + `gcloud config list`.
- **Direct policy read, if permitted:** list attached/inline policies, group memberships, role trust policies — often denied for a deliberately-scoped test principal, which is exactly why the next technique exists.
- **Permission brute-force (non-destructive):** fire read-only `Get*`/`List*`/`Describe*` calls and record which succeed vs return `AccessDenied` — the success set **is** the permission map, inferred without ever calling `iam:GetPolicy`. Non-destructive by construction: only get/list calls, never a mutating one. This is `enumerate-iam`'s lane for AWS; the technique generalizes to GCP's `testIamPermissions` and Azure role-assignment reads.
- **Principal/role enumeration:** enumerate roles and their trust policies to find assumable roles (`sts:AssumeRole`), cross-account trust, and over-broad `Principal: *` — building the escalation graph that a privilege-escalation-graph tool (PMapper, cross-referenced from `cloud-attack-aws`) formalizes.

This is **`T1087.004` — Account Discovery: Cloud Account**. Report as blast-radius: "principal P can perform {actions} on {resources}, and can assume {roles}" — never a secret dump. See `references/enumerate-iam.md`.

## OIDC / workload-identity-federation enumeration

Keyless federation (CI/CD, Kubernetes, cross-cloud) exchanges a short-lived OIDC token from an external issuer for cloud credentials, governed by a trust/condition policy — and the recurring flaw is an **over-broad trust condition**. The cloud verifies the token signature against the issuer's public keys, checks claims against configured conditions, and mints short-lived creds; the decisive claim is **`sub`** (plus `aud` and the `iss` issuer URL).

- **GitHub Actions `sub` format:** `repo:<owner>/<repo>:<qualifier>`, where qualifier is `ref:refs/heads/<branch>`, `environment:<name>`, or `pull_request`. A trust condition matching `repo:org/*`, omitting the branch/environment, or allowing `pull_request` lets a fork- or PR-triggered workflow reach a sensitive role.
- **AWS:** IAM OIDC identity providers + role trust policies with `StringLike`/`StringEquals` on `token.actions.githubusercontent.com:sub` — enumerate by listing OIDC providers and reading each role's trust condition for wildcards or missing scoping.
- **Azure:** **federated identity credentials (FIC)** on an app registration or user-assigned managed identity — issuer + subject + audience; over-broad `subject` scoping is the finding.
- **GCP:** **Workload Identity Federation** pools and providers with attribute mappings/conditions; a loose `attribute.repository` mapping or missing condition over-trusts.
- **Cross-tenant risk ("Sub:jugation" class):** shared **global** OIDC issuers mean a trust policy can inadvertently trust subjects from *other organizations' repos* — assuming such a role crosses a tenant boundary and is a **universal red line, out of scope regardless of what the scope file says**. Enumerate the trust *conditions* only (a control-plane read); never validate a token exchange across that boundary.

This is the federation half of `T1087.004` / adjacent `T1199` Trusted Relationship. Enumeration posture here is **config review** — read OIDC providers, federated credentials, pool/provider conditions, and trust policies, flagging wildcard or missing-scope subjects. Only validate an actual token exchange against an **in-scope, owned** trust relationship.

## Decision matrix — which tool, which question, which reference

| Need | Tool | Posture | ATT&CK Cloud | Reference |
|------|------|---------|--------------|-----------|
| Config audit across the whole account, ranked by risk | ScoutSuite | authenticated, read-only | T1580 / T1526 | `references/scoutsuite.md` |
| Public storage/endpoint discovery by org-name permutation | cloud_enum | anonymous | T1619 | `references/cloud-enum.md` |
| Harvest/assess metadata-service credential exposure | manual IMDS probe + provider CLI | authenticated once a token is obtained | T1552.005 | `references/metadata-service.md` |
| "I have these keys — what can they actually do?" | enumerate-iam (AWS) / `testIamPermissions` (GCP) / role-assignment read (Azure) | authenticated, non-destructive | T1087.004 | `references/enumerate-iam.md` |

## Anti-patterns

- **Treating a public index/scan as authorization to go further.** A publicly listed bucket you found is in scope only if the scope file's account/project ids say so. *Fix:* the scope file decides what is touched, not what you happened to find.
- **Hammering the metadata-service endpoint instead of reading the control-plane config.** Repeated probes against a live instance's IMDS risk destabilizing a fragile workload and add nothing a `DescribeInstances`/`MetadataOptions` read didn't already answer. *Fix:* check the instance's configured metadata options first; only exercise the SSRF chain against a lab target you set up for the purpose.
- **Validating an OIDC token exchange across a trust condition that could span tenants.** This is the universal red line every provider's RoE forbids. *Fix:* enumerate trust conditions as a config read; never execute the exchange unless the subject is unambiguously the in-scope tenant's own.
- **Reporting a recovered key's value.** Loot is never committed, logged, or pasted into a report. *Fix:* report that a credential was recovered and its blast-radius (what it can reach), never the key material.
- **Running a permission brute-force (enumerate-iam) against a principal outside the scope file.** Every call generates `AccessDenied` noise attributable in the audit trail. *Fix:* confirm the credential belongs to an in-scope account before the first call.
- **Skipping the anonymous pass and going straight to authenticated enumeration.** Misses the quieter, cheaper external-surface picture and risks attributing noisy calls to a principal before the public surface is mapped. *Fix:* anonymous first, authenticated once a credential exists.

## Rules (hard constraints)

- **The cloud scope file gates every act.** Only in-scope account/subscription/project ids and regions are touched; hard exclusions (shared-services accounts, production data stores, other tenants) are never touched even if reachable; the blast-radius cap bounds every pass. Re-read the scope file before each act; halt and report if the next act would exceed it.
- **Anonymous before authenticated.** Public-asset discovery and index reads first; authenticated permission/IAM enumeration only once a credential exists.
- **Enumeration is attributable — expect it in the audit trail.** Every authenticated call (including a deliberate `AccessDenied` probe) is logged against the principal that made it. This is not a reason to avoid testing under authorization; it is why the scope file and its expiry exist.
- **No DoS, ever.** No uncapped or repeated metadata-service probing against a live workload; no cross-tenant OIDC token-exchange validation, regardless of what the trust condition appears to allow.
- **Production is a separate, louder gate than lab.** Default target is a designated lab (CloudGoat, AzureGoat, GCPGoat, flaws.cloud, IAM Vulnerable) or a non-production owned account; production needs the second sign-off.
- **Two-class reporting:** every finding carries its **ATT&CK Cloud** technique id (T1580/T1526/T1619/T1552.005/T1087.004) and is scored **CVSS** in the final report (`penetration-testing:reporting`), never the blocker/major/minor/nit table.
- **Loot/secret redaction.** A recovered key, token, or secret is reported as *that it was recovered and its blast radius*, never its value. Harvested data follows the cloud scope file's data-handling rules.
- **Log every act** — command, target, timestamp, ATT&CK Cloud id — into the engagement action log as it runs, per `penetration-testing:reporting`.
- **Recon finds; it does not exploit.** A reachable credential, an over-broad trust policy, an open bucket is a *lead* handed to the matching provider skill (`cloud-attack-aws` / `cloud-attack-azure` / `cloud-attack-gcp`) — this skill never chains a finding into privilege escalation or service abuse itself.

## Cross-references

- **`penetration-tester`** (`security/agents/penetration-tester.md`) — the orchestrator that runs this skill as the cloud analogue of its **Recon** step and owns the cloud scope-file gate this skill enforces.
- **`cloud-attack-aws`** / **`cloud-attack-azure`** / **`cloud-attack-gcp`** — the **next** step per provider: each binds to this skill by name, consuming the reachable credentials, principal/permission maps, and OIDC-trust findings this skill produces and chaining them into IAM privilege escalation and service-specific abuse. This skill never does their job.
- **`devops:cloud-posture`** (`devops/cloud-posture/`) — the **posture** sibling: Prowler/ScoutSuite run there as a defensive, read-only CSPM scan that *finds* a misconfiguration from the outside. This skill *proves* a posture finding is reachable and attributes it to an actual credential — the handoff runs both ways: a `cloud-posture` finding is a recon lead here, and an enumeration result that confirms exploitability is reported back as validated posture.
- **`penetration-testing:recon-enumeration`** — the network/host sibling under the same agent; it enumerates the ATT&CK Enterprise Recon/Discovery surface (subdomains, ports, services). This skill is its cloud-control-plane analogue, keyed to ATT&CK Cloud instead.
- **`security/atomic-simulation`** — the purple-team sibling that *detonates* cloud ATT&CK techniques (Stratus Red Team) against a lab to test whether a detection fires; this skill enumerates the surface those techniques would hit, but never detonates one itself.
- **`penetration-testing:reporting`** — where every recon act is logged (action log) and every surface finding is scored (CVSS) and mapped (ATT&CK Cloud).
