---
name: cloud-attack-gcp
description: Use to exploit an authorized GCP project after `cloud-recon-enumeration` has mapped its surface — IAM/resource enumeration, service-account impersonation & key abuse, privilege-escalation chains via the IAM Credentials API, and Cloud Storage bucket attacks. Triggers "escalate privileges in this GCP project", "what can this service account become", "test our GCS buckets for public exposure". Not for GCP recon (`cloud-recon-enumeration`), AWS (`cloud-attack-aws`) or Azure (`cloud-attack-azure`) exploitation, or defensive GCP posture scanning (`devops:cloud-posture`). Owned/lab GCP projects only, under a committed cloud scope file.
---

# Penetration Testing — GCP Exploitation (IAM privesc · service-account impersonation · GCS buckets)

GCP exploitation is **overwhelmingly an identity problem, not a host problem**: the resource hierarchy
(Organization → Folder → Project → Resource) inherits IAM bindings downward, so a principal's real power
is the **union of every allow binding from the resource up to the org** — never what a single
`getIamPolicy` on one project shows. Most real privilege escalation in GCP is "become a more powerful
service account" via the **IAM Credentials API**, not a kernel exploit or a lateral host hop. This skill
picks up where `cloud-recon-enumeration` leaves off — a credential, a principal, a permission map — and
chains it into impersonation, privilege escalation, and service-specific abuse (Cloud Storage, Compute
Engine metadata, Secret Manager, deploy-as-SA).

> **⚠️ Authorized self-testing only — owned/lab GCP projects, under a committed cloud scope file.** This
> skill exploits **your own** GCP project(s) — or a designated training lab (**GCPGoat**) — to prove what
> `cloud-recon-enumeration` or `devops:cloud-posture` found is actually reachable. Every run is gated by
> the same committed **cloud scope file** and `#volatile` authorization line as the rest of the lane:
> never cached as durable, re-confirmed each engagement. Only the scope file's in-scope project/org ids
> are touched; its hard exclusions (shared-services projects, production data stores, other orgs) are
> never touched even if reachable. Production is a separate, louder sign-off than a lab target.

```
Authorization: cloud-scope=<org/folder/project ids>  regions=<in-scope regions>
               exclusions=<never-touch projects/orgs>  authorized-by=<name>
               window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (every tool here is a Python CLI or the `gcloud` CLI against the GCP
API — no per-stack split, per the library's anti-triplication rule) and is loaded by the
**`penetration-tester`** agent as its GCP exploitation step. It fences against `cloud-attack-aws` and
`cloud-attack-azure` (same role, different provider) and against `devops:cloud-posture`, which already
*reads* GCP defensively (Prowler/ScoutSuite, read-only CSPM) — **this is the first skill in the library
that *attacks* GCP.** Name that handoff explicitly: a `cloud-posture` finding ("default Compute SA still
holds Editor", "bucket X allows `allUsers`") is a lead here; this skill proves it is reachable and chains
it, then reports the confirmed exploitability back as validated posture.

> **The spine is MITRE ATT&CK Cloud**, not Enterprise: `T1580` Cloud Infrastructure Discovery, `T1078.004`
> Valid Accounts: Cloud Accounts, `T1098`/`T1098.001` Account Manipulation (Additional Cloud
> Credentials), `T1548` Abuse Elevation Control Mechanism, `T1619` Cloud Storage Object Discovery,
> `T1530` Data from Cloud Storage, `T1552.005` Unsecured Credentials: Cloud Instance Metadata API.
> Severity is scored **CVSS** in the final report (`penetration-testing:reporting`), not the
> blocker/major/minor/nit table.

## GCP target model: hierarchy, IAM, service accounts, the metadata server

- **Resource hierarchy**: `Organization → Folder(s) → Project → Resource` (bucket, VM, function, secret).
  IAM bindings attach at any node and are **inherited downward**; effective permission is the union over
  the whole ancestry. A modest role on a *folder* can out-rank a big role on one project.
- **Roles**: **basic/primitive** (`roles/owner`, `roles/editor`, `roles/viewer` — org-wide blunt
  instruments; **Editor is the silent danger**, bundling `*.create`/`*.update` across nearly all
  services), **predefined** (service-scoped, e.g. `roles/iam.serviceAccountTokenCreator`), **custom**
  (tenant-defined — `iam.roles.update` on a role you hold is itself a privesc: add any permission to your
  own role).
- **Service accounts (SAs) are the center of GCP offense.** An SA is **both a principal and a resource**:
  it has its own IAM policy (who can impersonate/`actAs`/manage its keys) *and* it appears in other
  resources' policies (what it can do). Compute Engine VMs, Cloud Functions/Cloud Run (now unified under
  **Cloud Run functions**), GKE nodes, Cloud Build, and Deployment Manager all run **as** an SA.
- **Detect the default-SA posture — never assume it.** The **Compute Engine default SA**
  (`PROJECTNUM-compute@developer.gserviceaccount.com`) historically shipped with **Editor** on the
  project and broad OAuth scopes attached by default — the single most common GCP blast-radius
  multiplier. **Google now defaults new orgs/projects away from auto-granting Editor and to a restricted
  scope**, but brownfield projects overwhelmingly still carry the old default. Check the live binding
  (`gcloud projects get-iam-policy` + the VM's attached SA and scopes) before reporting a finding either
  way — this is the one fact in this skill most likely to be wrong by assumption.
- **The metadata server** — `169.254.169.254` / `metadata.google.internal`, root
  `/computeMetadata/v1/`. Requires header **`Metadata-Flavor: Google`** — there is no AWS-IMDSv2-style
  token handshake, so **any SSRF that can set one header reaches it**. `.../service-accounts/default/token`
  returns an OAuth2 token for the attached SA; `.../default/scopes` shows whether it carries
  `cloud-platform` (unrestricted). GKE nuance: without **Workload Identity**, a pod reaches the node's
  metadata server and steals the **node SA**; Workload Identity intercepts the path and scopes pods to
  their bound KSA identity — the mitigation to flag when present.

## Step 1 — IAM / resource enumeration (`T1580`, `T1526`)

Consumes the credential and principal leads `cloud-recon-enumeration` already produced; this step goes
deeper, provider-side:

- **Identity of the credential**: `gcloud auth list`; decode a JSON key's `client_email`; `tokeninfo` for
  an OAuth access token's scopes.
- **Resource discovery**: `gcloud projects list` / `organizations list` / `resource-manager folders list`;
  `gcloud asset search-all-resources` (Cloud Asset Inventory) when `cloudasset.*` is reachable — the
  fastest full-tree inventory; otherwise per-service listers (`compute instances list`,
  `storage buckets list`, `functions list`, `run services list`, `secrets list`,
  `iam service-accounts list`).
- **Principal/binding discovery**: `gcloud projects get-iam-policy PROJECT_ID` (and the folder/org
  equivalents) — enumerate up the ancestry to resolve inherited power, never read one node and stop.
- **`testIamPermissions` brute enumeration — the core "what can I do" primitive.** Every resource type
  exposes `testIamPermissions(resource, permissions[])`, returning the subset of a submitted permission
  list the caller actually holds — and it **does not require holding the permission to call it**, so it
  is a low-noise self-assessment. Submit a service's full permission catalog in batches and read back the
  granted set.
- **Impersonation reconnaissance**: for every SA found, `testIamPermissions` against the SA resource for
  `iam.serviceAccounts.getAccessToken` / `getOpenIdToken` / `implicitDelegation` / `signBlob` /
  `signJwt` / `actAs` — those edges **are** the privilege-escalation graph Step 2 walks.

Full recipes, batching, and the reverse "what can principal P do" direction (`gcloud asset
analyze-iam-policy`): `references/gcp-enum.md`.

## Step 2 — Service-account impersonation & privilege escalation (`T1078.004`, `T1098`/`T1098.001`, `T1548`)

**This is the spine of GCP offense.** The impersonation primitives are all exposed by the **IAM
Credentials API**, gated by a permission held *on the target SA*:

| Primitive | Permission | What it yields |
|---|---|---|
| `generateAccessToken` | `iam.serviceAccounts.getAccessToken` | Short-lived OAuth2 token **as the target SA** — `gcloud --impersonate-service-account=SA` uses this. |
| `generateIdToken` | `iam.serviceAccounts.getOpenIdToken` | OIDC ID token as the target (IAP, Cloud Run auth). |
| `signBlob` | `iam.serviceAccounts.signBlob` | Signs arbitrary bytes as the target — forge tokens, sign GCS signed URLs. |
| `signJwt` | `iam.serviceAccounts.signJwt` | Signs a well-formed JWT as the target — exchange for an access token. |
| Implicit delegation | `iam.serviceAccounts.implicitDelegation` | Chain: `getAccessToken` on SA B plus `implicitDelegation` on B, where B has `getAccessToken` on C, mints a token for C through B. |
| Key creation | `iam.serviceAccountKeys.create` | A **long-lived** JSON key for the target — persistent, offline impersonation. |
| `actAs` | `iam.serviceAccounts.actAs` | Not a token verb — the **"attach this SA to a resource I'm creating"** gate; combine with a deploy permission to run code as the SA. |

`gcloud --impersonate-service-account` does single-hop `generateAccessToken` cleanly; a **multi-hop**
delegation chain needs the `generateAccessToken` REST endpoint called directly with an ordered
`delegates[]` list.

**`actAs` + a deploy permission is the dominant privesc pattern** — launch a workload bound to a more
powerful SA, then read its token from the metadata server. Rhino Security Labs' two-part research (~20
methods, IAM and non-IAM) is the reference catalog — each one is a **configuration weakness, not a GCP
vulnerability**, and every method is permission → escalation, never a CVE. Full table, each method's
exact permission, and the `actAs`+deploy walkthroughs (Deployment Manager, Cloud Functions/Cloud Run
functions, Compute Engine, Cloud Scheduler, Cloud Build, `setIamPolicy`, org-policy and API-key methods):
`references/gcp-privesc.md`.

## Step 3 — Service exploitation

- **Cloud Storage bucket attacks (`T1619`, `T1530`)** — GCS has a **global flat namespace**, so bucket
  names are brute-forceable; a response distinguishes doesn't-exist from exists-but-protected from
  exists-and-public, same three-way split as the recon skill's storage discovery. `allUsers` is anonymous
  public access; **`allAuthenticatedUsers` is *not* public** — it is any Google account, a common misread
  to correct in a report. Full tool and read/write/privesc reachability reporting:
  `references/gcp-bucket-brute.md`.
- **Compute Engine metadata / SA-token theft (`T1552.005`)** — from a foothold or SSRF:
  `curl -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token`;
  check the scope for `cloud-platform` (unrestricted); harvest `attributes/startup-script` and SSH-key
  metadata as config-exposure findings, never dumped as text in the report.
- **Secret Manager** — `secretmanager.versions.access` → `gcloud secrets versions access latest
  --secret=NAME` returns the payload; report **which secrets a principal can reach and what systems they
  unlock, never the secret material.**
- **GKE** — pod → node metadata SA (no Workload Identity) → often-broad node SA token; `container.*`
  permissions reach the cluster via `gcloud container clusters get-credentials`, then in-cluster RBAC
  pivots to workload SAs.

## Step 4 — Security Command Center detection-surface awareness (`T1562.008`, awareness not evasion)

Per **D5**, this skill teaches what an authorized action emits — never how to evade it against a real
target:

- **Cloud Audit Logs** split in two: **Admin Activity** is always-on, non-disableable, free — every
  `setIamPolicy`, key creation, impersonation call, and deploy lands here regardless of what the operator
  does. **Data Access** logs are **off by default** (except BigQuery) and cost-bearing — most enumeration
  (`testIamPermissions`, reads) is invisible unless a defender has turned it on, which is reported as a
  defender-coverage gap, not exploited as a stealth feature.
- **Security Command Center (SCC)** is GCP's findings plane: **Event Threat Detection** flags anomalous
  IAM grants, SA key abuse, and ties findings to MITRE ATT&CK; **Security Health Analytics** flags
  misconfig (public buckets, default-SA-with-Editor, over-broad roles). Confirming an authorized action
  surfaced as an SCC finding is purple-team value — it closes the detection loop the lab exists to teach.
- Key signals a defender keys on (teach them so the report names what should have fired):
  `GenerateAccessToken`/`SignJwt`/`SignBlob` calls, `serviceAccountKeys.create`, `SetIamPolicy`,
  Deployment Manager / Cloud Build deploys, tokens used from non-GCE IP ranges, new API keys.

## Decision matrix — which tool, which step, which reference

| Need | Tool | Step | ATT&CK Cloud | Reference |
|------|------|------|--------------|-----------|
| "Given this credential, what can it reach across the project/org?" | `gcp_scanner` / `hayat` / `gcloud` + `testIamPermissions` | 1 — enumeration | T1580 / T1526 | `references/gcp-enum.md` |
| "What is the shortest privesc chain to Owner?" | `gcloud` impersonation recipes / PurplePanda (graph) | 2 — privesc | T1078.004 / T1098 / T1548 | `references/gcp-privesc.md` |
| "Which buckets exist for this keyword, and what can I do to each?" | GCPBucketBrute | 3 — service exploitation | T1619 / T1530 | `references/gcp-bucket-brute.md` |
| Stand up the owned practice lab | Terraform + `gcloud` | — | — | `references/lab-setup.md` |

## Anti-patterns

- **Reporting the default Compute SA as "Editor by default" without checking the live binding.** Google
  no longer auto-grants Editor on new orgs/projects; a report that assumes the old default on a
  recently-created project is simply wrong. *Fix:* read `gcloud projects get-iam-policy` and the VM's
  attached SA/scopes before writing the finding either way.
- **Treating `allAuthenticatedUsers` as equivalent to `allUsers`.** It grants access to any Google
  account, not the public. *Fix:* state the exact binding and who it actually admits.
- **Dumping a Secret Manager payload, a signed JWT, or a minted SA key into the report.** *Fix:* report
  that a credential was recovered and its blast-radius — what it reaches — never the value (§2.5 loot
  redaction).
- **Chasing a multi-hop delegation through `gcloud --impersonate-service-account` alone.** It only does a
  clean single hop. *Fix:* call `generateAccessToken` directly with an ordered `delegates[]` list for a
  chain.
- **Treating Data Access logging as off everywhere.** It is on by default for BigQuery. *Fix:* check the
  specific service's logging config before reporting an enumeration pass as invisible.
- **Running `testIamPermissions` or impersonation probes against a project outside the scope file.**
  Every call is attributable in Cloud Audit Logs regardless of intent. *Fix:* confirm the project id is
  in-scope before the first call.

## Rules (hard constraints)

- **The cloud scope file gates every act.** Only in-scope org/folder/project ids and regions are touched;
  hard exclusions are never touched even if reachable. Re-read the scope file before each act; halt and
  report if the next act would exceed it.
- **No DoS, ever. Destructive acts are per-act opt-in and demonstrated-then-reverted** — an SA key minted
  for a privesc demo is deleted in cleanup; a resource created to prove `actAs`+deploy is torn down.
- **Detect, don't assume, the default-SA posture.** Google's current default no longer auto-grants Editor
  on new projects; state what the live binding actually is.
- **Loot/secret redaction.** A recovered key, token, or Secret Manager payload is reported as *that it
  was recovered and its blast radius*, never its value.
- **Detection-surface awareness, never evasion-for-stealth.** Teach what Cloud Audit Logs and SCC
  observe so a tester knows their footprint and a defender knows what to tune — never a technique whose
  purpose is evading detection on a real target (D5).
- **Two-class reporting:** every finding carries its ATT&CK **Cloud** technique id and is scored **CVSS**
  in the final report (`penetration-testing:reporting`), never the blocker/major/minor/nit table.
- **Log every act** — command, target, timestamp, ATT&CK Cloud id — into the engagement action log as it
  runs, per `penetration-testing:reporting`.
- **Production is a separate, louder gate than lab.** Default target is **GCPGoat** or a non-production
  owned project; production needs the second sign-off.

## Cross-references

- **`penetration-testing:cloud-recon-enumeration`** — the upstream step: produces the credential,
  principal/permission map, and reachable-SA leads this skill consumes. This skill never does its job
  (anonymous/public discovery, OIDC-federation trust review).
- **`devops:cloud-posture`** — the **defensive** sibling: Prowler/ScoutSuite already read GCP posture
  (`roles/viewer`/`roles/cloudasset.viewer`, read-only). **This is the first skill that attacks GCP** — a
  `cloud-posture` finding ("default Compute SA holds Editor", "bucket allows `allUsers`") is a lead here;
  this skill proves it is reachable and chains it, then reports confirmed exploitability back as
  validated posture. The handoff runs both ways.
- **`cloud-attack-aws`** / **`cloud-attack-azure`** — the sibling provider skills under the same
  `penetration-tester` step; same role, different provider, no shared files.
- **`security/atomic-simulation`** — the purple-team sibling that *detonates* cloud ATT&CK techniques
  (Stratus Red Team) against a lab to test whether SCC/Event Threat Detection fires; this skill performs
  the exploitation those detonations model, but the two never substitute for each other.
- **`penetration-testing:reporting`** — where every act is logged (action log) and every finding is
  scored (CVSS) and mapped (ATT&CK Cloud).
- **`security/cloud-incident-response`** — the defensive response peer: a confirmed GCP finding here
  implies the GCP IR runbook (`references/gcp-ir.md`) that skill owns.
