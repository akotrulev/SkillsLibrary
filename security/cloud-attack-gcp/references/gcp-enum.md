# GCP IAM / resource enumeration — `gcp_scanner` · `hayat` · `gcloud` + `testIamPermissions`

One tool family: credential-driven enumeration of what a GCP principal is and what it can reach,
provider-side. Feeds Step 1 of `../SKILL.md`. Every call here is authenticated and lands in Cloud Audit
Logs against the principal that made it (Admin Activity if it writes, Data Access if it reads and that
service has Data Access logging enabled) — this is attributable by construction, not a reason to avoid
testing under authorization.

## Identity first — "who am I"

```bash
gcloud auth list                                   # which identities gcloud currently holds
gcloud config list                                 # active account/project

# A JSON service-account key's identity, without importing it:
python3 -c "import json;print(json.load(open('key.json'))['client_email'])"

# An OAuth access token's scopes and expiry (no gcloud needed):
curl -s "https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=$TOKEN"
```

## Resource discovery — the full tree, fastest path first

```bash
gcloud organizations list
gcloud resource-manager folders list --organization=ORG_ID
gcloud projects list

# Fastest full-tree inventory — needs cloudasset.* on the credential:
gcloud asset search-all-resources --scope=organizations/ORG_ID
gcloud asset search-all-resources --scope=projects/PROJECT_ID

# Per-service listers when Cloud Asset Inventory isn't reachable:
gcloud compute instances list
gcloud storage buckets list
gcloud functions list            # includes Cloud Run functions (1st/2nd gen)
gcloud run services list
gcloud secrets list
gcloud iam service-accounts list
```

Try Cloud Asset Inventory first — one call replaces a dozen per-service listers. Fall back to the
per-service list when `cloudasset.*` is denied; the absence of that permission is itself worth recording
(it shapes how much enumeration cost the rest of the engagement carries).

## Principal / binding discovery — walk the ancestry, never stop at one node

```bash
gcloud projects get-iam-policy PROJECT_ID
gcloud resource-manager folders get-iam-policy FOLDER_ID
gcloud organizations get-iam-policy ORG_ID
```

**Effective permission is the union of every allow binding from the resource up to the org.** A policy
read at the project level alone under-reports power inherited from a folder or org binding — always walk
the ancestry before concluding a principal's reach.

## `testIamPermissions` — the core "what can I do" primitive

Every GCP resource type exposes `testIamPermissions(resource, permissions[])`: submit a permission list,
get back the subset the calling principal actually holds. **Calling it does not require already holding
any of the submitted permissions** — it is a self-assessment, not a privileged read, and it is low-noise
(a `testIamPermissions` call is far quieter than a failed mutating call that throws `PERMISSION_DENIED`
into the logs repeatedly).

```bash
gcloud projects test-iam-permissions PROJECT_ID \
  --permissions=iam.serviceAccounts.getAccessToken,iam.serviceAccounts.actAs,resourcemanager.projects.setIamPolicy

# Direct REST form (batches ≤ ~100 permissions per call):
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://cloudresourcemanager.googleapis.com/v1/projects/PROJECT_ID:testIamPermissions" \
  -d '{"permissions": ["iam.serviceAccounts.getAccessToken", "iam.serviceAccountKeys.create"]}'
```

The pattern generalizes to any resource type's `testIamPermissions` endpoint — `serviceAccounts`
(`iamcredentials` / `iam` API), `buckets` (`storage` API), `secrets` (`secretmanager` API). Submitting a
service's **full** permission catalog in batches and reading back the granted set is what `gcp_scanner`,
`enumerate-iam`-style tooling, and documented HackTricks recipes automate — this reference is the manual
form behind that automation.

## Impersonation reconnaissance — the privesc graph's edges

For every service account discovered, test for the permissions that gate the IAM Credentials API
primitives (`../SKILL.md` Step 2 table) **on that SA as the resource**, not on the project:

```bash
gcloud iam service-accounts test-iam-permissions SA_EMAIL \
  --permissions=iam.serviceAccounts.getAccessToken,iam.serviceAccounts.getOpenIdToken,iam.serviceAccounts.implicitDelegation,iam.serviceAccounts.signBlob,iam.serviceAccounts.signJwt,iam.serviceAccounts.actAs
```

Each permission returned is one edge in the escalation graph `references/gcp-privesc.md` walks. Record
the edge (holder → target SA → permission), not just the end state — the chain is the finding, and a
reviewer needs the path to retest it.

## Reverse direction — "what can principal P do"

```bash
gcloud asset analyze-iam-policy --organization=ORG_ID \
  --identity="user:someone@example.com"
```

Needs `policyanalyzer`/`cloudasset` permissions on the calling credential; strong when available (answers
"who can do X on Y" and "what can P do" directly), falls back to the per-resource `testIamPermissions`
loop above when it isn't.

## Tools

| Tool | What it does | Invocation | Needs |
|---|---|---|---|
| `gcp_scanner` (`github.com/google/gcp_scanner`) | Blast-radius crawl from a stolen credential — GCE/GCS/GKE/BigQuery/Cloud SQL/Pub-Sub/Functions/KMS, with built-in SA impersonation; no `gcloud` dependency | `python3 -m gcp_scanner -m METADATA` (from inside a GCE/GKE workload) / `-k SA_KEY.json` / `-g GCLOUD_PROFILE` / `-t OAUTH_TOKEN -o out/` | The held credential only |
| `hayat` (`github.com/DenizParlak/hayat`) | Authed-session audit/recon collector — IAM, compute, storage, network/firewall, logging config into one report | `./hayat.sh` against an active `gcloud` session | An authenticated `gcloud` session |

Confirm the tool's current flag surface against its repo before an engagement — both move faster than
this reference.

## What this feeds

The credential's identity, the resource inventory, the ancestry-resolved binding set, and the
impersonation-edge map from this step are the inputs `references/gcp-privesc.md` chains into an
escalation path, and the bucket/secret/metadata findings `../SKILL.md` Step 3 exploits.
