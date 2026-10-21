# 05 — Google Cloud Platform (GCP) Security (offensive deep dive)

Scope: course module **M11 — GCP Security (deep dive)**. This file is the knowledge base that feeds authoring of the skill **`security/cloud-attack-gcp`**. Our library already *reads* GCP posture (the cloud-posture / defensive lane); this is the first skill that *attacks* it. All techniques are for **AUTHORIZED self-testing and lab training only** — owned GCP projects/organizations, a committed scope file, expiring authorization. Teach **detection-surface awareness** (Security Command Center, Cloud Audit Logs), never evasion-for-stealth against a real target. Recovered secrets/keys are reported as **blast-radius, never values**. **No DoS, ever.**

---

## GCP fundamentals as attack context

### Resource hierarchy and IAM inheritance
GCP resources form a strict tree: **Organization → Folder(s) → Project → Resource** (a bucket, VM, function, secret). The Organization is the root node, tied to a Cloud Identity / Google Workspace domain.

- **IAM policies attach at any node** and are **inherited downward**. A policy binding set on the org or a folder applies to every project and resource beneath it. There is no "deny by descendant" except via explicit **IAM Deny policies** (newer, allow-list override) and **Org Policy constraints** (guardrails, not IAM).
- **Effective permission = union of every allow binding from the resource up to the org.** This is the attacker's most important mental model: a modest role on a *folder* can out-rank a big role on a single project, and a principal's real power is the sum over the whole ancestry, not what any one `getIamPolicy` shows.
- **The project is the billing/ API/ quota boundary** and where most workloads and most misconfigurations live. `project number` (immutable int) vs `project id` (immutable string) vs `project name` (mutable) — enumeration keys off id/number.

### Core services the skill will attack
- **Compute Engine (GCE)** — VMs. Each VM runs as an **attached service account** with configured **OAuth scopes**. Metadata server exposes that SA's token. Primary pivot surface.
- **Cloud Storage (GCS)** — buckets/objects. Global flat namespace → name-guessable; IAM + legacy ACLs + `allUsers`/`allAuthenticatedUsers` public bindings.
- **Cloud Functions / Cloud Run** — serverless; each runs *as a service account*. Deploy-as-SA is a core privesc primitive.
- **GKE** — Kubernetes. Nodes run as a node SA; pods reach the node's metadata SA unless **Workload Identity** is enabled. Container escape → node SA → cluster.
- **Secret Manager, Cloud SQL, BigQuery, Pub/Sub, KMS, Cloud Build, Deployment Manager, Cloud Scheduler** — all run or act as SAs and all appear in privesc chains.

### Roles model
- **Basic (primitive) roles** — `roles/owner`, `roles/editor`, `roles/viewer`. Org-wide blunt instruments. **Editor is the silent danger**: it holds `*.create`/`*.update`/`actAs`-adjacent permissions across nearly all services and is the default on several Google-managed SAs.
- **Predefined roles** — service-scoped, Google-curated (e.g. `roles/compute.admin`, `roles/iam.serviceAccountTokenCreator`, `roles/storage.objectViewer`). Hundreds of them; each bundles a fixed permission set.
- **Custom roles** — tenant-defined permission bundles at org or project level. `iam.roles.update` on a role you hold is itself a privesc (add any permission to your own role).

### Service accounts (SAs) — the center of GCP offense
- **Identity = `name@project-id.iam.gserviceaccount.com`** (user-managed) or Google-managed defaults.
- **Default SAs, the recurring foothold:**
  - **Compute Engine default SA** `PROJECTNUM-compute@developer.gserviceaccount.com` — historically granted **Editor** on the project and attached to VMs by default. A VM compromise with broad scopes → Editor-equivalent token. This is the single most common GCP blast-radius multiplier. (Google began defaulting new orgs to *not* auto-grant Editor and to a restricted default scope, but brownfield projects overwhelmingly still carry it — detect, never assume.)
  - **App Engine / Cloud Build / Cloud Services (`PROJECTNUM@cloudservices.gserviceaccount.com`)** default SAs — Cloud Services SA is Editor and is what **Deployment Manager** deploys as.
- **A SA is both a principal and a resource**: it has its own IAM policy (who can impersonate / actAs / manage keys it) *and* it appears in other resources' policies (what it can do). Both directions matter.
- **Keys**: user-managed JSON keys are long-lived credentials; `iam.serviceAccountKeys.create` mints one for any SA you can reach → persistent full impersonation.

### The metadata server
- Reachable from inside any GCE/GKE/Cloud Run/Functions workload at **`169.254.169.254`** and **`metadata.google.internal`**, path root `/computeMetadata/v1/`.
- Requires header **`Metadata-Flavor: Google`** (there is no AWS-IMDSv2-style token; the header is the only gate — which is why **SSRF that can set a header, or any SSRF at all on older setups, reaches it**).
- Token: `GET /computeMetadata/v1/instance/service-accounts/default/token` → OAuth2 access token for the attached SA.
- Scopes: `.../default/scopes` — `cloud-platform` scope = unrestricted across APIs; narrower scopes (e.g. read-only) require a privesc to widen effective power.
- Also exposes: project id/number, SSH keys, startup/shutdown scripts (`attributes/startup-script` — often holds secrets), custom attributes, and (recursive) `?recursive=true&alt=json`.
- **GKE nuance**: without Workload Identity, a pod can hit the node metadata server and steal the **node SA** token. With Workload Identity enabled, the metadata path is intercepted and pods get only their bound KSA identity — a primary mitigation to flag.

---

## IAM enumeration (MITRE T1580 Cloud Infrastructure Discovery; T1526 Cloud Service Discovery)

Goal: given a stolen credential (VM token, SA key, OAuth refresh token, user creds), establish **who am I, what can I touch, and what can I become.**

- **Identity of the credential**: `gcloud auth list`, decode a JSON key's `client_email`, or `GET tokeninfo` for an access token's scopes. For OAuth tokens, `https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=...`.
- **Project / resource discovery**:
  - `gcloud projects list`, `gcloud organizations list`, `gcloud resource-manager folders list`.
  - `gcloud asset search-all-resources` / Cloud Asset Inventory (needs `cloudasset.*`) — fastest full-tree inventory when available.
  - Per-service listers: `gcloud compute instances list`, `gcloud storage buckets list`, `gcloud functions list`, `gcloud run services list`, `gcloud secrets list`, `gcloud iam service-accounts list`.
- **Principal discovery**: `gcloud projects get-iam-policy PROJECT_ID` (and the folder/org equivalents) returns every binding — members and roles. Enumerate up the ancestry to resolve inherited power.
- **`testIamPermissions` brute enumeration** — the core "what can I do" primitive. Every resource type exposes a `testIamPermissions(resource, permissions[])` call that returns **the subset of a submitted permission list that the caller actually holds** — and it does **not require the permission to call it**, so it is a low-noise self-assessment. Submit the full catalog of a service's permissions in batches (≤ ~100/ call) and read back the granted set. This is what `gcp_scanner`, `enumerate-iam`-style tools, and HackTricks recipes automate. Examples: `projects.testIamPermissions`, `serviceAccounts.testIamPermissions`, `buckets.testIamPermissions`.
- **Listing what a *principal* can do (reverse)**: Policy Analyzer / `gcloud asset analyze-iam-policy` (needs `policyanalyzer`/`cloudasset` perms) answers "who can do X on Y" and "what can principal P do" — strong when you have enough rights; otherwise fall back to per-resource `testIamPermissions`.
- **Impersonation reconnaissance**: for every SA found, check whether your principal holds `iam.serviceAccounts.getAccessToken` / `getOpenIdToken` / `implicitDelegation` / `signBlob` / `signJwt` / `actAs` on it (via `testIamPermissions` against the SA resource). Those edges are the privesc graph.

---

## Service-account impersonation & privilege escalation

**This is the spine of GCP offense.** Lateral/vertical movement in GCP is overwhelmingly "become a more powerful service account," not kernel exploits. MITRE: **T1078.004 Valid Accounts: Cloud Accounts**, **T1098 / T1098.001 Account Manipulation (Additional Cloud Credentials)**, **T1548 Abuse Elevation Control Mechanism**.

### Impersonation primitives (the token-minting verbs)
All exposed by the **IAM Credentials API** (`iamcredentials.googleapis.com`), gated by permissions *on the target SA*:

| Primitive | Permission | What it yields |
|---|---|---|
| `generateAccessToken` | `iam.serviceAccounts.getAccessToken` | A short-lived OAuth2 access token **as the target SA** → run any API as it. `gcloud --impersonate-service-account=SA` uses this. |
| `generateIdToken` | `iam.serviceAccounts.getOpenIdToken` | An OIDC ID token as the target (for IAP, Cloud Run auth, etc.). |
| `signBlob` | `iam.serviceAccounts.signBlob` | Signs **arbitrary bytes** as the target → forge tokens, sign GCS signed URLs to read/write private objects. |
| `signJwt` | `iam.serviceAccounts.signJwt` | Signs a well-formed JWT as the target → exchange for an access token. |
| Implicit delegation | `iam.serviceAccounts.implicitDelegation` | Chain: if you have implicitDelegation on SA **B** and **B** has getAccessToken on SA **C**, you mint a token for **C** through B. |
| Key creation | `iam.serviceAccountKeys.create` | Mints a **long-lived JSON key** for the target SA → persistent, offline impersonation (also T1098.001). |
| `actAs` | `iam.serviceAccounts.actAs` | Not a token verb — the **"attach this SA to a resource I'm creating"** gate. Combine with a deploy permission to run code as the SA. |

**Delegation-chain note:** `gcloud --impersonate-service-account` performs single-hop `generateAccessToken` cleanly; **multi-hop delegation** (a `delegates[]` list) is reliable only by calling the `generateAccessToken` REST endpoint directly with the ordered delegate chain.

### The `actAs` + deploy pattern
`iam.serviceAccounts.actAs` on a SA, plus permission to create a compute/serverless resource, lets you **launch a workload that runs as that SA** and read its token from the metadata server (or exfil it). This is the mechanism behind the Compute/Functions/Run/Scheduler methods below.

### Canonical GCP privilege-escalation methods (Rhino Security Labs research)
Rhino's two-part research is the reference catalog (~20 methods across IAM and non-IAM). Each is a **weakness of configuration, not a GCP vulnerability.** Permission → escalation:

**IAM-based (Part 1):**
1. `deploymentmanager.deployments.create` — deploy resources via Deployment Manager, which **runs them as the Cloud Services SA (Editor)**; `actAs` **not** required. Simplest high-impact method.
2. `iam.roles.update` — add any permission (e.g. `iam.serviceAccountKeys.create`) to a custom role **you already hold**.
3. `iam.serviceAccounts.getAccessToken` — mint an access token for a more-privileged SA.
4. `iam.serviceAccountKeys.create` — mint a persistent key for a more-privileged SA.
5. `iam.serviceAccounts.implicitDelegation` (+ getAccessToken on a 3rd SA) — chain to a token for the third SA.
6. `iam.serviceAccounts.signBlob` — sign arbitrary payloads → token for the target SA (and GCS signed URLs).
7. `iam.serviceAccounts.signJwt` — sign a JWT → exchange for the target SA's access token.
8. `cloudfunctions.functions.create` (+ `...sourceCodeSet` + `...call`/`...setIamPolicy`, + `iam.serviceAccounts.actAs`) — deploy a function bound to a privileged SA, invoke it, read the SA token from metadata.
9. `cloudfunctions.functions.update` (+ `...sourceCodeSet`, + `actAs`) — overwrite an existing function's code / swap its SA, invoke, harvest token.
10. `compute.instances.create` (+ `compute.disks.create`, `...setMetadata`, `...setServiceAccount`, `compute.subnetworks.use`/`useExternalIp`, + `actAs`) — launch a VM with a privileged SA; startup script exfils its token.
11. `run.services.create` (+ `run.services.setIamPolicy`/`run.routes.invoke`, + `actAs`) — deploy a Cloud Run service that returns its attached SA token when called.
12. `cloudscheduler.jobs.create` (+ `cloudscheduler.locations.list`, + `actAs`) — scheduled HTTP job that calls Google APIs as a privileged SA.

**Non-IAM (Part 2):**
13. `orgpolicy.policy.set` — disable an Org Policy constraint (e.g. `appengine.disableCodeDownload`) to unblock otherwise-denied actions.
14. `storage.hmacKeys.create` — create HMAC keys for a higher-privileged SA → access GCS as that SA (interop/S3-style auth).
15. `serviceusage.apiKeys.create` — create a new, **unrestricted-by-default** API key with project-wide reach (undocumented API).
16. `serviceusage.apiKeys.list` — list existing API keys **including their values**, reuse a more-privileged one (undocumented API).
17. **`*.setIamPolicy` family** — modify a resource's IAM policy to grant yourself a role. Covers `resourcemanager.organizations/folders/projects.setIamPolicy`, `iam.serviceAccounts.setIamPolicy`, `cloudfunctions.functions.setIamPolicy`, `storage.buckets.setIamPolicy`, `compute.instances.setIamPolicy`, `secretmanager.secrets.setIamPolicy`, and more. The broadest, most direct escalation when you hold it.

**Adjacent, widely-cited:** `cloudbuild.builds.create` — Cloud Build runs as the Cloud Build SA (often Editor); submit a build that exfils that SA's token. Treat as an actAs-free deploy-as-SA path alongside Deployment Manager.

---

## Service exploitation

### Cloud Storage bucket attacks (T1619 Cloud Storage Object Discovery; T1530 Data from Cloud Storage)
- **Name-guessing**: global flat namespace → brute permutations of a keyword (company, project, env) and probe existence/ACLs **unauthenticated and authenticated** (`GCPBucketBrute`). Reports read/write/privesc (`setIamPolicy`) reachability per bucket.
- **Public exposure**: `allUsers` / `allAuthenticatedEmails` bindings or legacy object ACLs → anonymous or any-Google-account read (and sometimes write). `allAuthenticatedUsers` is *not* public — it is *any* Google account, a common misread.
- **Writable buckets**: supply-chain risk — overwrite served objects, Terraform state, function source zips, startup scripts.
- **Blast-radius reporting**: enumerate object names and sensitivity classes (keys, `.tfstate`, dumps, `credentials.json`) and **report the exposure and reach, never dump or exfil the secret values.**

### Compute Engine — metadata / SA-token theft (T1552.005 Unsecured Credentials: Cloud Instance Metadata API)
- From a foothold or SSRF: `curl -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token`.
- Read scopes; if `cloud-platform`, the token is unrestricted. Harvest `attributes/startup-script`, `attributes/ssh-keys`, project metadata.
- **OS Login / SSH abuse**: project- or instance-level SSH keys in metadata grant shell; `compute.instances.setMetadata` + `compute.instances.osLogin`/`roles/compute.osAdminLogin` → add a key or OS Login profile for interactive access as a privileged principal. `compute.instances.setMetadata` alone can inject an authorized SSH key into a running VM's metadata.
- **Serial-port / startup-script injection**: `setMetadata` with a new `startup-script` runs code as the VM's SA on next boot.

### Cloud Functions / Cloud Run — deploy-as-SA (T1648 Execute API; T1525 Implant Internal Image-adjacent)
- Deploy or update a function/service **bound to a target SA** (needs `actAs` + the create/update perms above). The deployed code reads its own metadata token and returns/exfils it → you now hold the target SA.
- Update-in-place (`functions.update`, `run.services.update`) is quieter and can swap the SA on an existing resource.

### Secret Manager (T1555 Credentials from Password Stores-adjacent; T1552 Unsecured Credentials)
- `secretmanager.versions.access` on a secret → `gcloud secrets versions access latest --secret=NAME` returns the payload. `secretmanager.secrets.setIamPolicy` → grant yourself access (privesc #17).
- List then target: `gcloud secrets list`; report **which secrets a principal can reach and what systems they unlock (blast-radius), never the secret material.**

### GKE
- Pod → node metadata SA (no Workload Identity) → node SA token (often broad).
- `container.*` perms → `kubectl` via `gcloud container clusters get-credentials`; RBAC-in-cluster then pivots to workload SAs and mounted KSA tokens.

---

## Detection surface (awareness, not evasion)

Taught so the operator **understands what their authorized testing emits and what defenders see** — never to defeat it against a real target.

### Cloud Audit Logs
- **Admin Activity logs** — always on, non-disableable, no cost. Record every write / config change (create instance, setIamPolicy, create key, deploy function). **Impersonation, key creation, IAM changes, and deploys all land here.**
- **Data Access logs** — **off by default** (except BigQuery), must be enabled per service. Record reads (GCS object reads, Secret Manager accesses, `getIamPolicy`). Much enumeration (`testIamPermissions`, reads) is **invisible unless Data Access logging is turned on** — relevant to a lab's realism, taught as defender-coverage context, not as a stealth recipe.
- **System Event** and **Policy Denied** logs round out the set. Logs flow to Cloud Logging → can route to SCC/SIEM.
- Key signals a defender keys on: `GenerateAccessToken`/`SignJwt`/`SignBlob` calls, `serviceAccountKeys.create`, `SetIamPolicy`, Deployment Manager / Cloud Build deploys, tokens used from **non-GCE IP ranges**, new API keys.

### Security Command Center (SCC)
- GCP's central findings plane. **Event Threat Detection** flags things like anomalous IAM grants, SA key abuse, cryptomining, and **ties findings to MITRE ATT&CK techniques**. **Security Health Analytics** flags misconfig (public buckets, default-SA-with-Editor, over-broad roles, open firewall). **SCC premium/enterprise** adds attack-path simulation.
- The skill teaches: *what a finding looks like for each technique*, so an operator can confirm their authorized action was detected (purple-team value) and so the lab's detection story is complete.

---

## Tools

| Tool | Purpose | Invocation (illustrative) | What it answers | Reference file |
|---|---|---|---|---|
| **gcp_scanner** (`github.com/google/gcp_scanner`) | Blast-radius enumeration from a stolen credential; crawls GCE/GCS/GKE/BigQuery/Cloud SQL/Pub-Sub/Functions/KMS, supports SA impersonation; no gcloud dependency (runs on a bare pod/VM) | `python3 -m gcp_scanner -m METADATA` / `-k SA_KEY.json` / `-g gcloud_profile` / `-t OAUTH_TOKEN -o out/` | "Given this credential, what can it reach across the project/org?" | `references/gcp-enum.md` |
| **GCPBucketBrute** (`github.com/RhinoSecurityLabs/GCPBucketBrute`) | GCS bucket name brute + access check (unauth + authed); reports read/write/privesc per bucket | `python3 gcpbucketbrute.py -k KEYWORD -u` (unauth) or with creds | "Which buckets exist for this keyword and what can I do to each?" | `references/gcp-bucket-brute.md` |
| **hayat** (`github.com/DenizParlak/hayat`) | GCP audit/recon collector — gathers IAM, compute, storage, network/firewall, logging config into a report | `./hayat.sh` against an authed gcloud session | "Snapshot of this project's IAM + exposed surface" | `references/gcp-enum.md` |
| **gcloud CLI recipes** | Native enumeration + impersonation + privesc execution | `gcloud projects get-iam-policy`, `gcloud iam service-accounts list`, `gcloud --impersonate-service-account=SA ...`, `gcloud secrets versions access`, `gcloud compute instances add-metadata` | All manual enumeration, impersonation, and privesc steps | `references/gcp-enum.md` + `references/gcp-privesc.md` |
| **PurplePanda / GCP IAM Privesc Scanner** (adjacent) | Graph the IAM-edge privesc paths across principals/SAs | per-tool | "What is the shortest privesc chain to Owner?" | `references/gcp-privesc.md` |

Planned reference files: **`gcp-enum.md`**, **`gcp-privesc.md`**, **`gcp-bucket-brute.md`**, **`lab-setup.md`**.

---

## MITRE ATT&CK Cloud mappings (GCP-relevant)

| Technique | ID | Where it appears above |
|---|---|---|
| Cloud Infrastructure Discovery | **T1580** | IAM/resource enumeration |
| Cloud Service Discovery | **T1526** | service enumeration |
| Cloud Storage Object Discovery | **T1619** | GCS bucket/object recon |
| Data from Cloud Storage | **T1530** | bucket exfil (lab only) |
| Unsecured Credentials: Cloud Instance Metadata API | **T1552.005** | metadata-server token theft |
| Unsecured Credentials (general) | **T1552** | Secret Manager, startup scripts, keys |
| Valid Accounts: Cloud Accounts | **T1078.004** | SA impersonation, stolen creds |
| Account Manipulation: Additional Cloud Credentials | **T1098 / T1098.001** | `serviceAccountKeys.create`, HMAC/API keys |
| Abuse Elevation Control Mechanism | **T1548** | privesc via actAs/setIamPolicy |
| Cloud Administration / Execute API | **T1648** | deploy-as-SA, API-driven execution |
| Create Cloud Instance | **T1578.002** | compute.instances.create privesc |
| Impair Defenses: Disable Cloud Logs | **T1562.008** | audit-log tampering (defender-awareness) |
| Transfer Data to Cloud Account | **T1537** | exfil to attacker-owned bucket (lab only) |
| Remote Services: Cloud Services | **T1021.007** | gcloud/API lateral movement |

(Align to the current ATT&CK version at authoring time — Cloud identity/CI-CD coverage expanded in the late-2025 v18 release.)

---

## Owned-lab targets

### GCPGoat (`github.com/ine-labs/GCPGoat`)
Deliberately-vulnerable, Terraform-deployed GCP environment (INE Labs). Deploy **only in a new, disposable project you own.** Covers OWASP Top 10 (2021) web risks **plus** misconfig across **IAM, Storage Buckets, Cloud Functions, and Compute Engine**. Documented attack-path scenarios include:
- **Compute Engine SSRF → metadata SA token theft** — web app SSRF reaches `169.254.169.254`, steals the VM's SA token.
- **Privilege escalation via default/over-privileged SA** — a VM with a default/editor SA, pivot to owner-level access.
- **Cloud Storage** — public/misconfigured bucket enumeration and data exposure.
- **Cloud Functions** — vulnerable function + deploy/invoke-as-SA.
- **Cloud SQL / data-store** exposure and **privilege escalation within Compute Engine**.
Learning goals the repo states: cloud pentest/red-team, IaC auditing, secure coding, detection & mitigation.

Complementary targets to name in the skill: **CNAPPgoat** (multi-cloud, INE/Ermetic) and **thunder-ctf** style challenges for isolated privesc practice.

### `lab-setup.md` sketch
- **Prereqs**: a dedicated throwaway **GCP project in an org you control**; billing enabled; `gcloud` + Terraform installed; an authorized **scope file** committed and an **expiry date** on the authorization; a budget alert; org policy allowing the needed APIs.
- **Deploy**: clone GCPGoat → set project/region vars → `terraform init && terraform plan && terraform apply`; enable required APIs; record the created resources/SAs for the scope file.
- **Guardrails**: isolated project only (never shared/prod); **no DoS**; enable Admin Activity logging review; set a billing cap; snapshot the created IAM so you can confirm detections in SCC/audit logs.
- **Teardown**: `terraform destroy`; delete any out-of-band SA keys you minted; **delete or disable the project** after the exercise; revoke authorization at expiry; scrub any harvested-secret notes (blast-radius descriptions only — no values retained).

---

## How it feeds our skill (`security/cloud-attack-gcp`)

| This file's section | Maps to in `SKILL.md` / references |
|---|---|
| GCP fundamentals as attack context | `SKILL.md` — "Target model: hierarchy, IAM inheritance, SAs, metadata server" overview |
| IAM enumeration | `SKILL.md` recon step → **`references/gcp-enum.md`** (gcp_scanner, hayat, gcloud + `testIamPermissions` recipes) |
| SA impersonation & privilege escalation | `SKILL.md` core offense step → **`references/gcp-privesc.md`** (the ~20 methods, each with its permission; impersonation primitives; actAs+deploy; delegation chains) |
| Service exploitation | `SKILL.md` exploitation step; GCS split into **`references/gcp-bucket-brute.md`**; metadata/Functions/Run/Secrets in `gcp-privesc.md`/`gcp-enum.md` |
| Detection surface | `SKILL.md` "what your authorized testing emits" section (Audit Logs, SCC) — awareness framing, no evasion |
| Tools | the four `references/*.md` files, one tool-family each |
| MITRE mappings | `SKILL.md` technique-id table, cross-referenced per step |
| Owned-lab targets | **`references/lab-setup.md`** (GCPGoat deploy/teardown) + the authorization/scope-file preamble |

**Authoring guardrails to carry into the skill**: authorized/owned scope + expiring authorization in the preamble; secrets/keys reported as **blast-radius, never values**; detection taught as **awareness, not stealth-evasion**; **no DoS** anywhere; every technique tagged with its MITRE id and the **exact permission** it requires.

---

## Sources

- Rhino Security Labs — *Privilege Escalation in GCP, Part 1 (IAM)*: https://rhinosecuritylabs.com/gcp/privilege-escalation-google-cloud-platform-part-1
- Rhino Security Labs — *Privilege Escalation in GCP, Part 2 (Non-IAM)*: https://rhinosecuritylabs.com/gcp/privilege-escalation-google-cloud-platform-part-2/
- Rhino Security Labs — *GCS Bucket Enumeration / GCPBucketBrute*: https://rhinosecuritylabs.com/gcp/google-cloud-platform-gcp-bucket-enumeration/ and https://github.com/RhinoSecurityLabs/GCPBucketBrute
- Google — `gcp_scanner`: https://github.com/google/gcp_scanner (PyPI `gcp-scanner`)
- Deniz Parlak — `hayat`: https://github.com/DenizParlak/hayat
- INE Labs — `GCPGoat`: https://github.com/ine-labs/GCPGoat ; HackingTheCloud GCPGoat CTF: https://hackingthe.cloud/gcp/capture_the_flag/gcp-goat
- HackingTheCloud — metadata in GCP instances & enumerate SA permissions: https://hackingthe.cloud/gcp/general-knowledge/metadata_in_google_cloud_instances/ , https://hackingthe.cloud/gcp/enumeration/enumerate_service_account_permissions/
- HackTricks Cloud — GCP IAM Privesc / interesting permissions: https://cloud.hacktricks.wiki/en/pentesting-cloud/gcp-security/gcp-privilege-escalation/gcp-iam-privesc.html
- Vaadata — *GCP Penetration Testing: Methodology and Use Cases*: https://www.vaadata.com/blog/gcp-penetration-testing-methodology-and-use-cases/
- MITRE ATT&CK Cloud Matrix: https://attack.mitre.org/matrices/enterprise/cloud/ ; CTID GCP security-stack mappings: https://ctid.mitre.org/projects/security-stack-mappings-google-cloud-platform/
- Google Cloud docs — Cloud Audit Logs (Admin Activity vs Data Access), IAM Credentials API (`generateAccessToken`/`signJwt`/`signBlob`), Security Command Center (verify version-current specifics against official docs at authoring time).
