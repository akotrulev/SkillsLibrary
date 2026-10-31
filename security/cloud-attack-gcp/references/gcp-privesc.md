# GCP service-account impersonation & privilege escalation — the IAM Credentials API chains

Feeds Step 2 of `../SKILL.md`. **This is the spine of GCP offense**: lateral/vertical movement in GCP is
overwhelmingly "become a more powerful service account," not a kernel exploit. Every method below is a
**weakness of configuration, not a GCP vulnerability** — a permission the checked-in IAM policy grants,
chained into a token for a more powerful identity. Rhino Security Labs' two-part research (Part 1: IAM;
Part 2: non-IAM) is the reference catalog this table is built from.

## Impersonation primitives — the token-minting verbs

All exposed by the **IAM Credentials API** (`iamcredentials.googleapis.com`), gated by a permission held
*on the target SA* (not on the project):

| Primitive | Permission | What it yields |
|---|---|---|
| `generateAccessToken` | `iam.serviceAccounts.getAccessToken` | Short-lived OAuth2 access token **as the target SA** — run any API call the SA can make. `gcloud --impersonate-service-account=SA` uses this. |
| `generateIdToken` | `iam.serviceAccounts.getOpenIdToken` | OIDC ID token as the target (Identity-Aware Proxy, Cloud Run authenticated invocation). |
| `signBlob` | `iam.serviceAccounts.signBlob` | Signs arbitrary bytes as the target — forge application-level tokens, sign GCS signed URLs to read/write objects the target SA can reach. |
| `signJwt` | `iam.serviceAccounts.signJwt` | Signs a well-formed JWT as the target — exchange it for an access token. |
| Implicit delegation | `iam.serviceAccounts.implicitDelegation` | Chain: holding `implicitDelegation` on SA **B**, where B holds `getAccessToken` on SA **C**, mints a token for C *through* B without ever holding a direct permission on C. |
| Key creation | `iam.serviceAccountKeys.create` | A **long-lived** JSON key for the target SA — persistent, offline impersonation; also `T1098.001` (new credential material, not a token that expires). |
| `actAs` | `iam.serviceAccounts.actAs` | Not a token-minting verb — the **"attach this SA to a resource I'm creating"** gate. Combined with a deploy permission, it runs *your* code *as* the SA. |

```bash
# Single-hop impersonation — the common case.
gcloud auth print-access-token --impersonate-service-account=TARGET_SA@PROJECT.iam.gserviceaccount.com

# Mint a persistent key instead (only when the demo requires it — delete it in cleanup, §2.5/no-DoS rule).
gcloud iam service-accounts keys create out.json \
  --iam-account=TARGET_SA@PROJECT.iam.gserviceaccount.com
```

**Multi-hop delegation note:** `gcloud --impersonate-service-account` only performs a clean **single**
hop. A chain through an intermediate SA (`delegates[]`) needs the `generateAccessToken` REST endpoint
called directly with the ordered delegate list — `gcloud`'s flag does not express a chain.

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/FINAL_SA@PROJECT.iam.gserviceaccount.com:generateAccessToken" \
  -d '{"delegates": ["intermediate-SA@PROJECT.iam.gserviceaccount.com"], "scope": ["https://www.googleapis.com/auth/cloud-platform"]}'
```

## The `actAs` + deploy pattern

`iam.serviceAccounts.actAs` on a target SA, plus a permission to create a compute or serverless resource,
lets a principal **launch a workload that runs as the target SA** and read its token off the metadata
server (or exfiltrate it directly from the deployed code). This single pattern is the mechanism behind
the Compute, Cloud Functions/Cloud Run, and Cloud Scheduler methods in the table below.

## Canonical escalation methods — permission → escalation

Each row names the permission(s) that enable it. None of these is a CVE; each is a configuration state to
detect and report, with the exact permission chain as the evidence.

### IAM-based

| # | Permission(s) | Escalation |
|---|---|---|
| 1 | `deploymentmanager.deployments.create` | Deploy a resource via Deployment Manager, which **runs as the Cloud Services SA** (Editor by default) — `actAs` is **not** required. The simplest high-impact method when available. |
| 2 | `iam.roles.update` | Add any permission (e.g. `iam.serviceAccountKeys.create`) to a custom role **you already hold a binding to**. |
| 3 | `iam.serviceAccounts.getAccessToken` | Mint an access token for a more-privileged SA directly. |
| 4 | `iam.serviceAccountKeys.create` | Mint a persistent key for a more-privileged SA. |
| 5 | `iam.serviceAccounts.implicitDelegation` (+ `getAccessToken` on a third SA) | Chain through an intermediate SA to a token for the third. |
| 6 | `iam.serviceAccounts.signBlob` | Sign arbitrary payloads as the target — forge a token or a GCS signed URL. |
| 7 | `iam.serviceAccounts.signJwt` | Sign a JWT as the target, exchange it for an access token. |
| 8 | `cloudfunctions.functions.create` (+ `...sourceCodeSet`, `...call`/`...setIamPolicy`, + `actAs`) | Deploy a function bound to a privileged SA, invoke it, read the token the function's own metadata call returns. |
| 9 | `cloudfunctions.functions.update` (+ `...sourceCodeSet`, + `actAs`) | Overwrite an existing function's code or swap its bound SA in place — quieter than a fresh deploy. |
| 10 | `compute.instances.create` (+ `compute.disks.create`, `...setMetadata`, `...setServiceAccount`, `compute.subnetworks.use`/`useExternalIp`, + `actAs`) | Launch a VM bound to a privileged SA; a startup script exfiltrates its metadata token. |
| 11 | `run.services.create` (+ `run.services.setIamPolicy`/`run.routes.invoke`, + `actAs`) | Deploy a Cloud Run service bound to a privileged SA that returns its token when invoked. |
| 12 | `cloudscheduler.jobs.create` (+ `cloudscheduler.locations.list`, + `actAs`) | A scheduled HTTP job that calls Google APIs as the privileged SA on its own cadence. |

### Non-IAM

| # | Permission(s) | Escalation |
|---|---|---|
| 13 | `orgpolicy.policy.set` | Disable an Org Policy constraint (e.g. `appengine.disableCodeDownload`) to unblock an action an IAM-only review would miss. |
| 14 | `storage.hmacKeys.create` | Create HMAC keys for a higher-privileged SA — access GCS through the S3-interop auth path as that SA. |
| 15 | `serviceusage.apiKeys.create` | Create a new API key — **unrestricted by default**, project-wide reach, via an undocumented API. |
| 16 | `serviceusage.apiKeys.list` | List existing API keys **including their values** — reuse a more-privileged one, via the same undocumented API. |
| 17 | `*.setIamPolicy` family | Modify a resource's own IAM policy to grant yourself a role directly. Covers `resourcemanager.{organizations,folders,projects}.setIamPolicy`, `iam.serviceAccounts.setIamPolicy`, `cloudfunctions.functions.setIamPolicy`, `storage.buckets.setIamPolicy`, `compute.instances.setIamPolicy`, `secretmanager.secrets.setIamPolicy`, and others — the broadest, most direct escalation whenever held. |

**Adjacent, widely cited:** `cloudbuild.builds.create` — Cloud Build runs as the **Cloud Build SA**
(often Editor); submitting a build whose steps exfiltrate that SA's token is an `actAs`-free deploy-as-SA
path alongside Deployment Manager (method 1) — check for it even when method 1 is blocked.

## Working the chain end to end

1. Enumerate every SA the project exposes (`references/gcp-enum.md`).
2. For each, test the impersonation-primitive permissions **on the SA as resource**.
3. Cross-reference the result against the table above: does any combination (a primitive + a deploy
   permission + `actAs`) land on a more powerful SA than the one currently held?
4. Walk the chain by hand (or with a graph tool — PurplePanda / a GCP IAM privesc scanner — for a project
   large enough that manual tracing is impractical) until it terminates at the most powerful reachable SA.
5. Report the **path**, not just the destination: holder → permission → intermediate SA → permission →
   target SA, with every permission named exactly as GCP names it — a reviewer retests by re-running the
   same `testIamPermissions` calls, not by re-deriving the chain from a vague description.
6. If a demo step is destructive (a minted key, a deployed function, a created VM), **tear it down in
   cleanup** — per the no-DoS / demonstrated-then-reverted rule. A persistence demo is removed; a created
   principal or key is deleted.

## What this feeds

A confirmed chain is the headline finding for the engagement report (`penetration-testing:reporting`),
tagged `T1078.004`/`T1098`/`T1098.001`/`T1548` as appropriate, and is the lead `cloud-incident-response`
builds its GCP IR runbook response around — "if this chain fires, here is what to look for in Cloud Audit
Logs" (`../SKILL.md` Step 4).
