# AzureHound + BloodHound — Entra/Azure attack-path graph

Feeds Step 1 (Entra enumeration) of `../SKILL.md`. **AzureHound** (SpecterOps, Go) is the collector that
feeds **BloodHound Community Edition** the Entra ID and Azure RBAC edges; BloodHound renders the graph so
you can query the shortest abusable path to **Global Administrator** or **Owner**. Touches only in-scope
tenants named in the cloud scope file; collection is read-only Graph/ARM but **logged** in Entra
sign-in/audit.

> **Use AzureHound + BloodHound as the primary Azure attack-path graph — not Stormspotter.** Stormspotter
> (the Azure org's Neo4j visualizer) is **dormant** (last push ~Jan 2024, no maintained release); do not
> make it the primary tool. AzureHound v3.x is current and collects straight into BloodHound CE.

## Collect

```bash
# Collect Entra + Azure RBAC relationships into a single JSON for BloodHound CE import.
azurehound -u user@tenant -p '<password>' list --tenant <tenant-id> -o out.json
# then import out.json via the BloodHound CE UI (Settings → file ingest) or bloodhound-cli.
```

- Read-only **Microsoft Graph + ARM** calls, but every one lands in the Entra sign-in log (non-interactive
  if an SP/MI token is used) and resource reads land in the Azure Activity log — the collection is not
  invisible.
- BloodHound CE is a Docker-compose stack (app/API + PostgreSQL + Neo4j). Import `out.json`, then query.

## Query — shortest path to tenant/subscription takeover

- Built-in pathfinding and Cypher answer **"who can reach Global Admin / Owner, and by what edges?"** The
  Azure edges that matter in this lane:
  - **`AZOwns` / `AZUserAccessAdministrator`** → grant any role (the Owner/UAA "game over" edges, Step 4).
  - **`AZAddSecret` / `AZAddOwner`** on an app/SP → add a credential and impersonate the SP (Step 2).
  - **`AZManagedIdentity` / `AZRunsAs`** → a VM/Automation resource runs as an MI whose roles you inherit
    (Step 2 IMDS theft, Step 4 Run Command / runbook).
  - **`AZGlobalAdmin`** + the **elevate-access bridge** → root-scope User Access Administrator over every
    subscription (the canonical GA→owns-all-of-Azure pivot in `../SKILL.md` Step 4).
- Report the **path** (holder → edge → target principal/scope), not just the destination, so the finding is
  actionable and the defender can cut a specific edge.

## Detection footprint (awareness, not evasion — D5)

- AzureHound collection is a **burst of Graph/ARM reads** under one identity — Entra sign-in logs record the
  client app id and the volume; Defender/Sentinel analytics flag anomalous enumeration. Report the footprint.
- The **edges** AzureHound surfaces are not themselves actions — exercising one (adding a secret, assigning a
  role) is the loud, audited mutation (Entra audit log / Azure Activity log), covered in Steps 2 and 4.

## Cleanup

The collected graph (every user, role, SP relationship) is **loot** — segregate the Neo4j DB and `out.json`
per the scope file's data-handling, report blast-radius not contents, never commit them. Any secret or role
assignment added while proving a path is deleted in cleanup.

## What this feeds

The shortest-path finding is the headline for `penetration-testing:reporting` (CVSS + ATT&CK Cloud id,
typically `T1098`/`T1078.004`) and the lead `security/cloud-incident-response` builds its Azure runbook
around — "if this edge is exercised, here is the Entra audit / Activity-log response."
