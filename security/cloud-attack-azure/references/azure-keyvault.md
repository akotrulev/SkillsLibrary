# Azure Key Vault — data-plane access testing + the Contributor privesc misconfig

Feeds Step 3 (Key Vault access testing) of `../SKILL.md`. Azure Key Vault holds **secrets + keys + certs in
one service** (an asymmetry with AWS/GCP, which split KMS from a secrets manager) across two planes, and its
data-plane authorization comes in two models — getting those two distinctions right is the whole of
Key Vault offense. Touches only in-scope vaults named in the cloud scope file; every data-plane read is
logged with the caller identity.

## Two planes, two data-plane models

- **Control plane** (Azure RBAC) — manage the vault *resource*: create, configure, set the auth model, edit
  access policies. `Microsoft.KeyVault/vaults/*`.
- **Data plane** (`*.vault.azure.net`) — read/write the *secrets, keys, certs*. Authorized by one of:

| Model | How data access is granted | Key risks |
|---|---|---|
| **Access policies** (legacy) | Per-vault list of (principal → permitted operations). Data-plane only. | No PIM; the **Contributor privesc** below; IaC can silently wipe other apps' policies with an empty array. |
| **Azure RBAC** (recommended) | Standard roles (**Key Vault Secrets User**, **Key Vault Administrator**) scoped management-group→resource; spans both planes. | Simpler to audit; still over-grants if assigned at subscription scope. |

Detect which model a vault uses: `enableRbacAuthorization: true` → RBAC; `false`/absent → access policies.

## The classic misconfig — Key Vault Contributor → read every secret (privesc)

Under the **access-policy** model, the control-plane **Key Vault Contributor** role was meant to manage
vaults *without* reading data — but it can **edit the vault's access policies and grant itself** data-plane
`Get`/`List` on secrets → read every secret in the vault. This is a control-plane → data-plane privilege
escalation (`T1098` → `T1552`). What you flag: **migrate the vault to RBAC** (`enableRbacAuthorization:
true`) and remove unauthorized access-policy entries. Detection rules (Datadog, Defender for Cloud) flag
vaults where `enableRbacAuthorization` is not `true`.

## Read secrets with a compromised identity (data plane)

```bash
az keyvault secret list        --vault-name <v>
az keyvault secret show        --vault-name <v> --name <s>   # value → report as blast-radius, NEVER the value
az keyvault key list           --vault-name <v>
az keyvault certificate list   --vault-name <v>
```

Equivalent via a stolen **managed-identity** token: request a token for `resource=https://vault.azure.net`
from IMDS (`../SKILL.md` Step 2), then call the Key Vault REST API with it. The blast-radius chain to
demonstrate: **compromised web app's MI → `Key Vault Secrets User` → DB connection string → database.**

## Common misconfigs to enumerate

- Access-policy model still in use (`enableRbacAuthorization` not `true`).
- Vault reachable from the public network — no private endpoint, firewall `defaultAction: Allow`.
- Over-broad data-plane grants — an MI/SP holding `Get`/`List` secrets it does not need.
- Soft-delete / purge-protection off (a deleted secret or the whole vault is unrecoverable → availability
  and anti-forensics risk).
- High-value secrets stored that are themselves pivots: SP client secrets, storage account keys, DB
  connection strings — each one chains to a further compromise.

## Detection footprint (awareness, not evasion — D5)

- Every data-plane `SecretGet`/`SecretList`/`KeyList` writes a **Key Vault log** (→ Log Analytics) entry
  with the caller identity — **bulk secret reads stand out** and Sentinel ships a mass-enumeration analytics
  rule. Editing an access policy is an **Azure Activity-log** control-plane event.
- Report the log each action writes so the defender knows what should have fired; never teach suppressing or
  evading it. A ROADrecon-style bulk read is high-signal by design.

## Cleanup

Any access-policy entry or role assignment added to prove the Contributor privesc is **removed in cleanup**;
recovered secrets are scrubbed to blast-radius notes (§2.5), never retained or committed.

## What this feeds

A confirmed Key Vault read / Contributor-privesc path is a headline finding for
`penetration-testing:reporting` (CVSS + ATT&CK Cloud id) and the lead `security/cloud-incident-response`
builds its Azure runbook around — "if this Key Vault log sequence fires, here is the response."
Storage-key and broad secret-sweep loot that often lands *in* these vaults is in `microburst.md`.
