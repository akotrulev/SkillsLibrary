# Cloud Storage bucket attacks — GCPBucketBrute

One tool family: GCS bucket name discovery and per-bucket access-reachability testing. Feeds Step 3 of
`../SKILL.md` (`T1619` Cloud Storage Object Discovery, `T1530` Data from Cloud Storage).

## Why GCS bucket names are discoverable at all

GCS uses a **single global flat namespace** shared across every GCP customer — unlike a provider where a
bucket lives inside an account-scoped namespace, a GCS bucket name is a DNS-adjacent global string. That
means an org's naming convention (`company-prod`, `company-dev`, `company-backups`, `company-logs`,
`company-assets`) is brute-forceable by permutation, exactly as `cloud-recon-enumeration`'s public-storage
discovery already teaches for the anonymous pass — this reference is the authenticated, per-bucket
follow-through once a candidate name is found.

## GCPBucketBrute

```bash
git clone https://github.com/RhinoSecurityLabs/GCPBucketBrute
cd GCPBucketBrute

# Unauthenticated — existence + public-ACL check only, no credential needed.
python3 gcpbucketbrute.py -k acme -u

# Authenticated — also tests the *held credential's* reachability per bucket
# (uses Application Default Credentials or an explicit key).
python3 gcpbucketbrute.py -k acme -k acme-prod -k acme-backups
```

For each candidate bucket, GCPBucketBrute reports the **three-way split** that is the entire technique:

| Result | Meaning |
|---|---|
| Doesn't exist (404) | No bucket by that name — move to the next permutation |
| Exists, protected (403) | Bucket exists, the calling identity (or anonymous) cannot read it |
| Exists, reachable (200 / listing) | Bucket exists and the calling identity (or `allUsers`/`allAuthenticatedUsers`) can read — or, when the credential is authenticated, the tool additionally reports **write** and **`setIamPolicy`** reachability |

The authenticated pass is the one that matters for impact: a bucket reachable to `allUsers` is a public
exposure finding regardless of what the held credential can do; a bucket reachable to the **held
credential specifically** (via IAM, not a public binding) is the lead that chains into the privesc work
in `gcp-privesc.md` if the bucket holds Terraform state, service-account keys, or deployment artifacts.

## `allUsers` vs `allAuthenticatedUsers` — the recurring misread

- **`allUsers`** — anonymous, unauthenticated public access. No Google account required.
- **`allAuthenticatedUsers`** — **not public**. It admits *any* Google account on Earth, which is still a
  severe exposure (effectively "the entire internet, modulo a free sign-up"), but it is a different
  finding from `allUsers` and must be reported as such — conflating the two overstates or understates the
  exposure depending on which direction the error runs.
- Legacy **object ACLs** (pre-dating uniform bucket-level access) can grant either binding at the
  **object** level even when the bucket's own IAM policy looks locked down — a bucket-level
  `getIamPolicy` that shows no public binding does not rule out a public object ACL; check both.

## Writable buckets — supply-chain blast radius

A bucket reachable for **write** (not just read) by an over-broad binding is a supply-chain risk, not
just a data-exposure one:

- Served static content (a website bucket, a CDN origin) — overwrite served objects.
- Terraform remote state (`*.tfstate`) — overwrite state to redirect what the next `apply` manages.
- Cloud Function / Cloud Run function source zips — overwrite source so the **next deploy** runs attacker
  code as whatever SA the function is bound to (chains directly into `gcp-privesc.md`'s deploy-as-SA
  methods, but via tampering with an *existing* deployment rather than creating a new one).
- VM startup scripts staged in a bucket — overwrite to run code as the VM's attached SA on next boot.

Report writability as a finding on its own, separate from readability — the two have different fixes
(bucket IAM for read, bucket IAM *and* a supply-chain integrity control for write).

## Object-name and sensitivity-class enumeration — report exposure, never contents

Once a bucket is confirmed reachable, enumerate object names (`gsutil ls -r gs://bucket/` or the REST
`objects.list`) and classify by name pattern — `.tfstate`, `credentials.json`, `*.pem`, `*-key.json`,
database dump extensions, backup archive extensions. **Report the exposure and the reach (what the
object's contents would plausibly unlock) — never the object's actual contents.** Downloading a flagged
object to confirm sensitivity is a judgment call bounded by the scope file's data-handling rules; where
the name pattern alone is unambiguous (a service-account key's filename convention), prefer reporting
from the name and metadata (size, last-modified) without opening it.

## What this feeds

A confirmed public or over-broadly-IAM'd bucket, and any writable-bucket finding, is reported with its
ATT&CK ids (`T1619`/`T1530`) and CVSS score in the engagement report
(`penetration-testing:reporting`). A bucket holding deployment artifacts or SA keys is also a lead back
into `gcp-privesc.md` — read access to a bucket can be the first link in an escalation chain, not just a
standalone finding.
