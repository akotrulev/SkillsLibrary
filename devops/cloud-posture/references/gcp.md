# Cloud Posture — GCP (Prowler / ScoutSuite)

GCP is authored third. Prowler covers project- and organization-scoped resources — IAM, Cloud Storage, Compute, Cloud SQL, KMS, Logging, and the org policy surface.

> **Authorization-first.** These commands read a live GCP project/org. Record `Authorization: <project/org scope + who authorized + expiry>` before running, treat it as `#volatile`, own the project, and grant only read.

## The read-only identity

- **Project scope:** `roles/viewer` on the project for the identity Prowler uses (some checks may need an added specific read role, e.g. `roles/iam.securityReviewer`).
- **Organization scope:** `roles/cloudasset.viewer` (Cloud Asset Viewer) at the org level for org-wide asset enumeration; `roles/iam.securityReviewer` for IAM-policy read across the org.

Never grant an editor/owner role — a posture scan reads only.

## Authenticating

Prowler uses the standard Google credential chain — Application Default Credentials (a user account via `gcloud`) or a service-account key.

```bash
# Application Default Credentials (local, after `gcloud auth application-default login`).
prowler gcp --project-ids my-project

# Service account key file.
prowler gcp --credentials-file ./prowler-sa.json --project-ids my-project

# Organization-wide (needs roles/cloudasset.viewer at the org).
prowler gcp --organization-id <org-id>
```

**In CI: Workload Identity Federation**, not a downloaded service-account key JSON. Configure a WIF pool trusting the pipeline's OIDC token and impersonate the read-only service account — a committed or stored SA-key file is a blocker finding (the library's no-static-cloud-credentials invariant).

## The scan — headline checks

```bash
# Project scan, CIS 3.0 GCP, HTML + OCSF.
prowler gcp --project-ids my-project --compliance cis_3.0_gcp \
  --output-formats html json-ocsf --output-directory "reports/$(date +%F)"

# The gate.
prowler gcp --project-ids my-project --severity critical high --status FAIL --compliance cis_3.0_gcp --output-formats json-ocsf
```

What the headline GCP checks catch (each → a CIS control + an ATT&CK Cloud technique):

- **IAM** — over-broad primitive roles (`roles/owner`/`editor` on users), service-account key age/rotation, user-managed SA keys, `allUsers`/`allAuthenticatedUsers` bindings → T1078.004 / T1098.
- **Cloud Storage** — buckets public to `allUsers`/`allAuthenticatedUsers`, uniform bucket-level access off → T1530, A02.
- **Encryption at rest** — CMEK on storage/SQL/disks where required, KMS key rotation period → CIS crypto controls.
- **Encryption in transit** — Load Balancer TLS policy, Cloud SQL `require SSL` → pairs with `qa-<stack>:certificate-scan`.
- **Logging/audit** — Cloud Audit Logs (Admin/Data Access) enabled, log sinks + retention, no disabled logging → T1562.008, A09.
- **Network exposure** — firewall rules allowing `0.0.0.0/0` on SSH/RDP/DB ports, default network use, public Compute/SQL instances → T1580.

## ScoutSuite on GCP

```bash
scout gcp --user-account --project-id my-project --report-dir "reports/scout/$(date +%F)"
# Or service account:
scout gcp --service-account ./scout-sa.json --project-id my-project
```

One offline HTML report, browse by service. Prowler gates; ScoutSuite reads.

## Commercial tools (references only)

- **Google Security Command Center (SCC)** — GCP's native CSPM + threat detection; the Premium/Enterprise tier maps findings to CIS/PCI/etc. and runs Security Health Analytics continuously. Where a project already runs SCC, Prowler is the OSS CI gate / second opinion; the checks above also verify SCC and its detectors are enabled.
- **Wiz / Prisma Cloud** — agentless multi-cloud CNAPP; if the org runs one across AWS+Azure+GCP it is the primary posture platform and Prowler is the OSS pipeline gate.
- **Prowler Pro / Prowler App** — the hosted SaaS of the same engine for the GCP estate.

The OSS path runs with nothing but the `roles/viewer` (or `roles/cloudasset.viewer` for org) identity — no paid license required.
