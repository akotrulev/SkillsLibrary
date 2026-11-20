# Azure RBAC privilege escalation & service attacks

Feeds Step 4 of `../SKILL.md`. Four escalation paths once a foothold holds an Azure RBAC role.

## Role-assignment abuse (control plane, `T1098`)

**Owner**, **User Access Administrator**, and **Role Based Access Control Administrator** hold
`Microsoft.Authorization/roleAssignments/write` — they can grant roles, including granting a controlled
principal **Owner**. Owner/UAA at a high scope (management group / subscription) is **game over for that
scope**. Holders of `roleDefinitions/write` can also **edit a custom role** to add `Actions`, silently
raising everyone assigned it.

## Storage account key theft (`T1552`, `T1537`/`T1530`)

`Microsoft.Storage/storageAccounts/listKeys/action` (held by **Contributor**, Owner, Storage Account
Contributor) returns the **account key** = full control of all blobs/files/queues/tables, **bypassing
data-plane RBAC**; `az storage account keys list -n <acct> -g <rg>` (report the key as blast-radius, never
the value). Minting **SAS** tokens gives scoped, time-boxed exfil access. Full enumeration recipe:
`microburst.md`.

## VM command execution without creds (`T1651`)

With the right RBAC action you run commands as SYSTEM/root on a VM: **Run Command**
(`Microsoft.Compute/virtualMachines/runCommand/action`, in Contributor/VM Contributor — `az vm run-command
invoke -g <rg> -n <vm> --command-id RunShellScript --scripts "<cmd>"`), then read the VM's **MI token from
IMDS** (`identity-token-theft.md`) to pivot; or push a **Custom Script Extension** for the same outcome.

## Automation Accounts & Runbooks

Create/edit a Runbook and run it on an Azure sandbox or a **Hybrid Worker** → code execution with the
Automation Account's identity (historically a Run As account with subscription Contributor, or a
user-assigned MI). Hybrid Workers run on-prem/VM boxes where local admin can harvest the worker's
credentials/MI. **Microsoft has since removed `ListKeys` from the Reader role and pushes the
extension-based Hybrid Worker with Entra auth — version-check the tenant before asserting the old path.**
Full enumeration + loot recipes: `microburst.md`.

## What this feeds

A confirmed RBAC escalation, storage-key theft, or Run-Command/runbook execution is a headline finding for
`penetration-testing:reporting` (CVSS + ATT&CK Cloud id). Every mint/run/edit above is removed in cleanup.
