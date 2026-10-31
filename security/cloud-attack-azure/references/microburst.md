# MicroBurst — broad Azure enumeration + loot (NetSPI, PowerShell)

Feeds Step 1 (enumeration) and Step 4 (RBAC privesc / loot) of `../SKILL.md`. **MicroBurst** (NetSPI,
PowerShell) is the broad-coverage Azure toolkit: external pre-credential recon (valid storage accounts,
subdomains) and internal loot (storage keys, Key Vault, Automation, app secrets). Touches only in-scope
subscriptions/tenants named in the cloud scope file; every ARM/data-plane call is logged.

> **Roster note:** MicroBurst's module set keeps growing — confirm the exact function names against the
> installed version (`Get-Command -Module MicroBurst`) at engagement time rather than trusting a pinned list
> here.

## External recon (pre-credential)

```powershell
Import-Module .\MicroBurst.psm1
Invoke-EnumerateAzureSubdomains -Base <orgname>   # valid *.azurewebsites.net / *.blob.core.windows.net / … names
Invoke-EnumerateAzureBlobs      -Base <orgname>   # public blob containers for a keyword
```

- Answers **"what Azure surface does this org expose before I have any credential?"** — valid storage
  account / subdomain names (`T1580` Cloud Infrastructure Discovery), feeding the public-asset leads
  `cloud-recon-enumeration` started. No authentication; still run under the scope file.

## Internal loot (authenticated)

```powershell
Get-AzStorageKeysREST -SubscriptionId <sub>        # storage account keys via ARM listKeys (Step 4)
Get-AzKeyVaultKeysREST / Get-AzKeyVaultSecrets     # Key Vault enumeration (pairs with azure-keyvault.md)
Get-AzPasswords                                    # broad secret sweep: Automation, App Service, Key Vault, RunAs certs
```

- `Get-AzPasswords` is the broad secret sweep — Automation Account RunAs certs, App Service config, Key
  Vault secrets, storage keys. **Every recovered secret is reported as blast-radius, never its value**
  (§2.5): "Automation Account RunAs cert recovered → subscription Contributor" names the reach, not the cert.
- Storage-key theft via `listKeys` (`T1552` / `T1537`) **bypasses data-plane RBAC** — the key is full
  control of all blobs/files/queues/tables. Mint SAS for scoped, time-boxed access rather than sharing the
  account key.
- **Version-check the Hybrid-Worker path before asserting it.** MicroBurst historically abused the Automation
  Hybrid Worker `ListKeys` exposure via the Reader role; Microsoft has **removed `ListKeys` from Reader** and
  pushes the extension-based Hybrid Worker with Entra auth — confirm the tenant's configuration before
  claiming the old escalation (detect, don't assume).

## Detection footprint (awareness, not evasion — D5)

- `listKeys`, Key Vault reads, and Automation enumeration are **Azure Activity-log / Key Vault-log** events;
  `Get-AzPasswords` is a high-signal sweep that Defender/Sentinel analytics flag (bulk secret enumeration).
  Report the log each action writes so the defender knows what should have fired; never teach suppressing it.
- Loud actions to flag in the report: `listKeys`, bulk Key Vault reads, RunAs-cert recovery, Automation
  runbook creation.

## Cleanup

Any SAS token, runbook, or extension created to prove a path is **deleted in cleanup**; recovered secrets
are scrubbed to blast-radius notes, never retained or committed.

## What this feeds

Recovered storage keys / Automation identities / Key Vault secrets are the pivots Step 4 chains and the
headline findings for `penetration-testing:reporting` (CVSS + ATT&CK Cloud id). Key Vault specifics —
access-policy vs RBAC, the Contributor-privesc misconfig — are in `azure-keyvault.md`.
