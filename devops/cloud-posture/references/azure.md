# Cloud Posture — Azure (Prowler / ScoutSuite)

Azure is authored second — it matches the library's Azure DevOps / Container Apps defaults. Prowler covers subscription-scoped resources (Storage, SQL, Key Vault, Network, Monitor, Defender) plus Entra ID (via Microsoft Graph) for identity checks.

> **Authorization-first.** These commands read a live Azure tenant/subscription. Record `Authorization: <subscription/tenant scope + who authorized + expiry>` before running, treat it as `#volatile`, own the tenant, and grant only read.

## The read-only identity

Azure posture needs two distinct read grants — subscription RBAC **and** Graph (directory) permissions:

- **`Reader`** (built-in RBAC role) at subscription scope — read-only over Azure resources.
- **The custom `ProwlerRole`** — a minimal read role Prowler ships that adds the handful of read actions `Reader` omits (a few Function App checks need them). Create it from Prowler's JSON and assign it alongside `Reader`.
- **Microsoft Graph application permissions** (for Entra ID / identity checks — optional for resource-only scans, required for identity posture):
  - `Directory.Read.All` (or `Domain.Read.All` for the restrictive variant)
  - `Policy.Read.All`
  - `AuditLog.Read.All`

  Grant these on the app registration under **API permissions → Microsoft Graph → Application permissions**, then admin-consent them.

## Authenticating

Prowler supports four Azure auth modes:

```bash
# Service principal via env vars (preferred for CI — pair with Workload Identity Federation, not a stored secret).
export AZURE_CLIENT_ID=<app-id>
export AZURE_TENANT_ID=<tenant-id>
export AZURE_CLIENT_SECRET=<secret>          # in CI, prefer federated OIDC over a stored secret
prowler azure --sp-env-auth

# Stored Azure CLI credentials (local, after `az login`).
prowler azure --az-cli-auth

# Managed identity (when running on an Azure VM / container with a read-only MI assigned).
prowler azure --managed-identity-auth

# Interactive browser (one-off local, needs the tenant).
prowler azure --browser-auth --tenant-id <tenant-id>

# Scope to specific subscriptions (default is all the identity can read).
prowler azure --az-cli-auth --subscription-ids <sub-id-1> <sub-id-2>
```

**In CI: Workload Identity Federation**, not a stored `AZURE_CLIENT_SECRET`. Configure a federated credential on the app registration trusting the pipeline's OIDC token — a long-lived client secret in CI is a blocker finding.

## The scan — headline checks

```bash
# Subscription scan, CIS 2.0 Azure, HTML + OCSF.
prowler azure --az-cli-auth --compliance cis_2.0_azure \
  --output-formats html json-ocsf --output-directory "reports/$(date +%F)"

# The gate.
prowler azure --az-cli-auth --severity critical high --status FAIL --compliance cis_2.0_azure --output-formats json-ocsf
```

What the headline Azure checks catch (each → a CIS control + an ATT&CK Cloud technique):

- **Entra ID / IAM** — MFA for privileged users, guest-access restrictions, legacy auth blocked, over-privileged role assignments → T1078.004 / T1098.
- **Storage** — public blob containers / anonymous access (`storage_public_access`), secure-transfer-required, minimum TLS version → T1530, A02.
- **Encryption at rest** — Storage/SQL/Disk encryption, Key Vault soft-delete + purge protection, key rotation → CIS crypto controls.
- **Encryption in transit** — App Service HTTPS-only + min TLS, SQL `Enforce TLS`, secure-transfer on storage → pairs with `qa-security-certificate-scan`.
- **Logging/audit** — Activity Log retention + diagnostic settings, SQL auditing, Key Vault logging, Defender for Cloud plans on → T1562.008, A09.
- **Network exposure** — NSGs allowing `*`/Internet on RDP/SSH/DB ports, public SQL/Storage endpoints, missing Private Endpoints → T1580.

## ScoutSuite on Azure

```bash
scout azure --cli --report-dir "reports/scout/$(date +%F)"
# Or service principal:
scout azure --service-principal --tenant <tenant-id> --subscription-ids <sub-id>
```

One offline HTML report, browse by service. Prowler gates; ScoutSuite reads.

## Commercial tools (references only)

- **Microsoft Defender for Cloud** — Azure's native CSPM + CWPP. Its Secure Score and regulatory-compliance dashboard map to the same CIS/benchmark controls Prowler checks. Where a subscription already runs Defender for Cloud (the checks above verify its plans are *on*), Prowler is the OSS CI gate / second opinion, and its findings can be exported to Defender.
- **Wiz / Prisma Cloud** — agentless multi-cloud CNAPP; if the org already runs one across AWS+Azure+GCP, it is the primary posture platform and Prowler is the OSS gate in the pipeline.
- **Prowler Pro / Prowler App** — the hosted SaaS of the same engine (scheduled scans, dashboards, ticketing) for the Azure estate.

The OSS path runs with nothing but the `Reader`+`ProwlerRole` identity and (for identity checks) the Graph read grants — no paid license required.
