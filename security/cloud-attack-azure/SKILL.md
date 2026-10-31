---
name: cloud-attack-azure
description: Use to exploit an authorized Azure/Entra tenant after `cloud-recon-enumeration` has mapped its surface — Entra ID enumeration & abuse, managed-identity/service-principal token theft, Key Vault data-plane access, Azure RBAC privilege escalation, and Sentinel/Defender detection-surface awareness. Triggers "escalate in this Azure subscription", "what can this managed identity reach", "test our Key Vault and Entra app registrations". Not for Azure recon (`cloud-recon-enumeration`), AWS (`cloud-attack-aws`) or GCP (`cloud-attack-gcp`) exploitation, defensive Azure posture scanning (`devops:cloud-posture`), network foothold (`initial-access`), or purple-team detonation (`atomic-simulation`). Owned/lab Azure tenants only, under a committed cloud scope file.
---

# Penetration Testing — Azure Exploitation (Entra ID · managed identity · Key Vault · Azure RBAC)

Azure exploitation rides on one structural fact that has no AWS or GCP analog: **there are two independent
authorization planes, and neither grants access in the other.** **Entra ID** (the directory — formerly
Azure Active Directory / Azure AD, renamed 2023-07; capabilities and APIs unchanged, only the brand)
governs the tenant: users, groups, app registrations, service principals, directory roles. **Azure RBAC**
governs resources: subscriptions, resource groups, VMs, storage, Key Vault — through Azure Resource
Manager. An Entra **Global Administrator** is not an Azure **Owner** and vice versa; confusing the planes
is the single most common scoping error in an Azure engagement. This skill picks up where
`cloud-recon-enumeration` leaves off — a token, a principal, a role map — and chains it across both planes:
Entra enumeration → managed-identity / service-principal token theft → Key Vault secrets → Azure RBAC
privilege escalation → service-level code execution.

> **⚠️ Authorized self-testing only — owned/lab Azure tenants, under a committed cloud scope file.** This
> skill exploits **your own** tenant/subscription(s) — or a designated training lab (**AzureGoat**) — to
> prove what `cloud-recon-enumeration` or `devops:cloud-posture` found is actually reachable. Every run is
> gated by the same committed **cloud scope file** and `#volatile` authorization line as the rest of the
> lane: never cached as durable, re-confirmed each engagement. Only the scope file's in-scope tenant ids,
> subscription ids and regions are touched; its hard exclusions (shared-services subscriptions, production
> data stores, other tenants) are never touched even if reachable. Production is a separate, louder
> sign-off than a lab target.

```
Authorization: cloud-scope=<tenant id, subscription ids>  regions=<in-scope regions>
               exclusions=<never-touch subscriptions/data-stores/tenants>  authorized-by=<name>
               window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (every tool here is a Python/Go/PowerShell CLI or the `az` CLI / Azure
REST API — no per-stack split, per the library's anti-triplication rule) and is loaded by the
**`penetration-tester`** agent as its Azure exploitation step. It fences against `cloud-attack-aws` and
`cloud-attack-gcp` (same role, different provider), against `devops:cloud-posture` (which already *reads*
Azure defensively — Prowler/ScoutSuite, read-only CSPM), against `initial-access` (network/application
foothold, not cloud-API abuse), and against `atomic-simulation` (which *detonates* a technique with
Stratus Red Team to test detection, rather than exploiting a real misconfiguration). Name the posture
handoff explicitly: a `cloud-posture` finding ("Key Vault X uses access-policy auth, not RBAC",
"storage account Y allows key access", "MI Z holds Contributor at subscription scope") is a lead here;
this skill proves it is reachable and chains it, then reports the confirmed exploitability back as
validated posture.

> **The spine is MITRE ATT&CK Cloud** (Azure AD / IaaS platforms), **not Enterprise host-centric ids** — a
> cloud finding tagged with a host id is mis-mapped. Every technique below carries its Cloud id:
> `T1087.004` Account Discovery: Cloud Account, `T1069.003` Permission Groups Discovery: Cloud Groups,
> `T1526` Cloud Service Discovery, `T1538` Cloud Service Dashboard, `T1078.004` Valid Accounts: Cloud
> Accounts, `T1552.005` Unsecured Credentials: Cloud Instance Metadata API, `T1552.001` Credentials in
> Files, `T1528` Steal Application Access Token, `T1098.001`/`.003` Account Manipulation (Additional Cloud
> Credentials / Roles), `T1136.003` Create Account: Cloud Account, `T1651` Cloud Administration Command,
> `T1580` Cloud Infrastructure Discovery, `T1537`/`T1530` Transfer / Data from Cloud Storage, `T1484.002`
> Tenant Policy Modification: Trust Modification (awareness). Severity is scored **CVSS** in the final
> report (`penetration-testing:reporting`), not the blocker/major/minor/nit table.

## Azure target model: two planes, one bridge

- **Entra ID (directory plane).** Secures the tenant — users, groups, app registrations, service
  principals, directory settings — through **Entra roles** (top role **Global Administrator**), tenant-wide
  and mostly flat. Reached via Microsoft Graph (`graph.microsoft.com`); the legacy Azure AD Graph
  (`graph.windows.net`) is retiring and breaks older tooling.
- **Azure RBAC (resource plane).** Secures subscriptions → resource groups → resources through **Azure
  RBAC roles** (top role **Owner**, plus **User Access Administrator** for grants), via Azure Resource
  Manager (`management.azure.com`). Scope is hierarchical: management group → subscription → resource group
  → resource.
- **The bridge — Global-Administrator elevate-access, the canonical "GA owns all of Azure" pivot.** A
  Global Administrator can toggle *Access management for Azure resources* on, which assigns that user the
  **User Access Administrator** role at **root scope `/`** — role-assignment rights over every subscription
  in the tenant. It is **per-user, not tenant-wide**, and Microsoft advises toggling it back off; look for
  it as the primary cross-plane escalation.
- **Identity objects the chain rides on.** An **app registration** is the application *definition* (holds
  redirect URIs, API permissions, and **client secrets/certificates**); a **service principal (SP)** is its
  *instance* in a tenant (what gets role assignments and signs in non-interactively) — SP credentials are
  long-lived, reusable, and often over-privileged, a top loot target. A **managed identity (MI)** is an
  Azure-managed SP whose credentials Azure rotates and never exposes: **system-assigned** (1:1 with one
  resource) or **user-assigned** (attachable to many resources → larger blast radius).

## Step 1 — Entra ID enumeration (`T1087.004`, `T1069.003`, `T1526`)

Consumes the token and principal leads `cloud-recon-enumeration` already produced; this step goes deeper,
provider-side. Entra enumeration begins **unauthenticated** and deepens once any token is held — a
low-privileged member or **guest** can typically read large parts of the directory by default.

- **Pre-auth / unauthenticated:** tenant discovery via
  `login.microsoftonline.com/<domain>/.well-known/openid-configuration`, `getuserrealm.srf` and
  autodiscover — reveals tenant id, federation (managed vs federated), brand. **Username validity**
  enumeration via auth-endpoint error-code differences. **Password spray is out of scope here — it risks
  lockout/DoS; awareness only.**
- **Authenticated directory enumeration:** read and map users, groups (and **dynamic-group** rules —
  membership you can influence by editing an attribute), directory roles & assignments, administrative
  units; **app registrations & service principals** with their API permissions (`Application` vs
  `Delegated`), credentials present, and **owners** (an owner can add a credential to an app/SP they own →
  impersonate it); **Conditional Access** policies (enumerate *which controls exist* — MFA, device
  compliance, named locations — for blast-radius reasoning, **never to craft a bypass against a live
  tenant**); and **guest / external** access settings.
- **Tools:** **ROADrecon** (directory dump → offline DB/web UI) and **AzureHound** (BloodHound collector
  for Entra attack paths — who reaches Global Admin / Owner); `az`/Az PowerShell for ground truth. Full
  recipes and tooling-currency caveats: `references/roadtools.md`, `references/azurehound.md`.

## Step 2 — identity abuse & token theft (`T1552.005` → `T1078.004`, `T1098.001`)

- **Managed-identity IMDS token theft (`T1552.005` → `T1078.004`), the highest-value path.** The Instance
  Metadata Service at **`169.254.169.254`** issues OAuth bearer tokens for the MI attached to the host; the
  only gate is the **`Metadata: true`** header — a minimal anti-SSRF measure, not an auth control:
  ```
  GET http://169.254.169.254/metadata/identity/oauth2/token
        ?api-version=2018-02-01&resource=https://management.azure.com/   # or ...vault.azure.net / ...graph.microsoft.com
  Header: Metadata: true
  ```
  For a **user-assigned** MI add `&client_id=<miClientId>`; App Service/Functions use `IDENTITY_ENDPOINT` +
  `IDENTITY_HEADER` instead of the link-local IP. Two ways to reach it: code execution on the host, or an
  **SSRF** in an app on the host (the `Metadata: true` header blocks naive URL-fetch SSRF but not SSRF that
  sets custom headers, follows redirects, or proxies; IP-encoding and DNS-rebinding bypasses are documented
  leads). **Impact = the MI's RBAC roles** — report as blast-radius ("MI held Contributor on RG x → could
  read all storage keys / run commands on all VMs"), never the token value.
- **Service-principal credential abuse (`T1078.004`, `T1552.001`).** Loot SP client secrets/certs from
  source control, pipeline variables, `.azure`/`.env` files, App Service config, ARM/Terraform state, or
  Key Vault; authenticate non-interactively
  (`az login --service-principal -u <appId> -p <secret|cert> --tenant <tid>`) to act as the SP with its
  often-broad roles. SP sign-ins frequently **bypass MFA** (no interactive user) — a reason they are prized.
- **Consent & app abuse / credential addition (`T1098.001`/`.003`, `T1528`).** Adding a client secret or
  certificate to an app/SP you can write to grants durable non-interactive access (persistence + privesc);
  illicit OAuth consent to Graph scopes retains delegated access that survives password resets. **Note these
  as persistence mechanisms; never run phishing against third parties.**
- **Device-code & PRT (awareness only).** Device-code phishing (RFC 8628; Storm-2372 active since Aug 2024)
  and Primary-Refresh-Token abuse via the Microsoft Authentication Broker client
  (`29d9ed98-a469-4536-ade2-f981bc1d605e`) are taught for **recognition and detection**, not execution
  against live users — the skill teaches what these trip, and that defenders block device-code flow via
  Conditional Access.

## Step 3 — Key Vault data-plane access testing (`T1552`, `T1078.004`)

Key Vault has a **control plane** (manage the vault resource, via Azure RBAC) and a **data plane**
(read/write secrets, keys, certs). Data-plane authorization uses one of two models, set per vault:

- **Access policies (legacy)** — a per-vault list of (principal → permitted operations). No PIM support;
  the **classic privesc**: the control-plane **Key Vault Contributor** role was meant to manage vaults
  *without* reading data, but it can **edit access policies and grant itself** data-plane access → read
  every secret. Flag it and recommend migration to RBAC.
- **Azure RBAC (recommended)** — standard roles (**Key Vault Secrets User**, **Key Vault Administrator**)
  spanning control + data plane; simpler to audit, still over-grants if assigned at subscription scope.

Read secrets with a compromised identity (`*.vault.azure.net`): `az keyvault secret list --vault-name <v>`,
`az keyvault secret show --vault-name <v> --name <s>`, `az keyvault key list`, `az keyvault certificate
list` — or request an IMDS token for `resource=https://vault.azure.net` and call the Key Vault REST API.
**Common misconfigs to enumerate:** access-policy model still in use (`enableRbacAuthorization` not `true`);
vault reachable from the public network (no private endpoint / firewall `defaultAction: Allow`); over-broad
data-plane grants; soft-delete/purge-protection off; high-value secrets stored that are themselves pivots
(SP secrets, storage keys, DB connection strings). **Blast-radius chain to show:** compromised web app's MI
→ `Key Vault Secrets User` → DB connection string → database. Report secrets as blast-radius, never values.
Full detail: `references/azure-keyvault.md`.

## Step 4 — Azure RBAC privilege escalation & service attacks

- **Role-assignment abuse (control plane, `T1098`).** **Owner**, **User Access Administrator**, and **Role
  Based Access Control Administrator** hold `Microsoft.Authorization/roleAssignments/write` — they can grant
  roles, including granting a controlled principal **Owner**. Owner/UAA at a high scope (management group /
  subscription) is **game over for that scope**. Holders of `roleDefinitions/write` can also **edit a custom
  role** to add `Actions`, silently raising everyone assigned it.
- **Storage account key theft (`T1552`, `T1537`/`T1530`).**
  `Microsoft.Storage/storageAccounts/listKeys/action` (held by **Contributor**, Owner, Storage Account
  Contributor) returns the **account key** = full control of all blobs/files/queues/tables, **bypassing
  data-plane RBAC**; `az storage account keys list -n <acct> -g <rg>` (report the key as blast-radius, never
  the value). Minting **SAS** tokens gives scoped, time-boxed exfil access.
- **VM command execution without creds (`T1651`).** With the right RBAC action you run commands as
  SYSTEM/root on a VM: **Run Command** (`Microsoft.Compute/virtualMachines/runCommand/action`, in
  Contributor/VM Contributor — `az vm run-command invoke -g <rg> -n <vm> --command-id RunShellScript
  --scripts "<cmd>"`), then read the VM's **MI token from IMDS** to pivot; or push a **Custom Script
  Extension** for the same outcome.
- **Automation Accounts & Runbooks.** Create/edit a Runbook and run it on an Azure sandbox or a **Hybrid
  Worker** → code execution with the Automation Account's identity (historically a Run As account with
  subscription Contributor, or a user-assigned MI). Hybrid Workers run on-prem/VM boxes where local admin
  can harvest the worker's credentials/MI. **Microsoft has since removed `ListKeys` from the Reader role and
  pushes the extension-based Hybrid Worker with Entra auth — version-check the tenant before asserting the
  old path.** Full enumeration + loot recipes: `references/microburst.md`.

## Step 5 — Sentinel / Defender detection-surface awareness (awareness not evasion, D5)

Per **D5**, this skill teaches what an authorized action **emits** — so a tester knows their footprint and a
defender knows what to tune — and **never** how to evade detection against a real target:

| Source | What it records / detects |
|---|---|
| **Entra sign-in logs** | Interactive + non-interactive (SP/MI) sign-ins; the **client app id** used (e.g. the broker `29d9ed98-…` flagging device-code/PRT abuse); IP, device, CA result, MFA, risk. |
| **Entra audit logs** | Directory changes: **app credential added**, consent grants, role assignments, group membership, CA edits — the `T1098` trail. |
| **Entra ID Protection** | Risky sign-ins/users: impossible travel, anonymous IP, token anomalies, leaked credentials. |
| **Azure Activity Log** | Control-plane ARM ops: `listKeys`, `roleAssignments/write`, `runCommand`, extension deploys, Key Vault policy edits. |
| **Key Vault logs** (→ Log Analytics) | Every data-plane `SecretGet`/`KeyList` with caller identity — bulk secret reads stand out. |
| **Defender for Cloud** | CSPM posture (vault not-RBAC, public storage, exposed MI) + CWPP threat alerts (anomalous Key Vault access, suspicious Run Command, IMDS-token misuse). |
| **Microsoft Sentinel** | SIEM/SOAR over the above via KQL; analytics rules for mass secret enumeration, impossible travel, device-code sign-ins, suspicious SP credential additions. |

**Sentinel is migrating into the unified Defender portal but the migration is not complete in 2026** —
know both the Log-Analytics and Defender-portal paths. **Pairing rule:** every attack technique above is
reported with the log it writes and the analytics rule it tends to trip (loud, high-signal actions to flag:
`listKeys`, bulk Key Vault reads — ROADrecon-style bursts are detectable by Elastic's prebuilt rule —
`roleAssignments/write`, Run Command, new SP client secret, device-code sign-ins), so the learner reasons
about footprint and the report notes detectability.

## Decision matrix — which tool, which step, which reference

| Need | Tool | Step | ATT&CK Cloud | Reference |
|------|------|------|--------------|-----------|
| "What does this token see across the directory — users, groups, apps, SPs, roles, CA?" | ROADrecon (msgraph fork) | 1 — Entra enum | T1087.004 / T1526 | `references/roadtools.md` |
| "Who can reach Global Admin / Owner, and by what edge chain?" | AzureHound → BloodHound | 1 — Entra enum | T1087.004 / T1098 | `references/azurehound.md` |
| "External storage/subdomain names pre-cred; internal storage keys, KeyVault, Automation, app secrets" | MicroBurst | 1/4 — enum + loot | T1526 / T1552 | `references/microburst.md` |
| "Which secrets can this identity read, and is the vault access-policy or RBAC?" | `az keyvault …` / REST | 3 — Key Vault | T1552 / T1078.004 | `references/azure-keyvault.md` |
| Stand up the owned practice lab | AzureGoat | — | — | `references/lab-setup.md` |

## Anti-patterns

- **Conflating the two planes.** Treating an Entra Global Admin as an Azure Owner (or vice versa) mis-scopes
  the whole engagement. *Fix:* state which plane a finding lives in; test the GA elevate-access bridge
  explicitly rather than assuming it.
- **Password spraying or device-code phishing against a live tenant.** Spray risks lockout/DoS; device-code
  phishing targets real users. *Fix:* both are awareness-only here — enumerate CA to reason about blast
  radius, never to bypass controls on a live target (D5).
- **Asserting the old Hybrid-Worker `ListKeys` path or ROADrecon `gather` without version-checking.**
  Microsoft removed `ListKeys` from Reader and pushes extension-based Hybrid Workers with Entra auth;
  ROADrecon `gather` is **broken** by the Azure AD Graph retirement. *Fix:* use the ROADrecon **msgraph
  community fork**; version-check the tenant before asserting the Hybrid-Worker path.
- **Reaching for Stormspotter as the Azure graph tool.** It is **dormant** (last push ~Jan 2024). *Fix:* use
  **AzureHound + BloodHound** as the primary attack-path graph.
- **Dumping a recovered secret, MI/SP token, or storage key into the report.** *Fix:* report that a
  credential was recovered and its blast-radius — what it reaches — never the value (§2.5 loot redaction).
- **Any action that risks a DoS** — password spray that locks accounts, load-testing a reachable resource,
  deleting a resource without reverting. *Fix:* exercise destructive chains only against a disposable lab,
  and revert them.
- **Running any probe against a principal, subscription, or tenant outside the scope file.** Every call is
  attributable in the Entra sign-in / Azure Activity log. *Fix:* confirm the identity is in-scope before the
  first call.

## Rules (hard constraints)

- **The cloud scope file gates every act.** Only in-scope tenant/subscription ids and regions are touched;
  hard exclusions (shared-services subscriptions, production data stores, other tenants) are never touched
  even if reachable; the blast-radius cap bounds every pass. Re-read the scope file before each act; halt
  and report if the next act would exceed it.
- **No DoS, ever. Destructive acts are per-act opt-in and demonstrated-then-reverted** — an SP credential or
  role assignment minted for a privesc demo is deleted in cleanup; a Run Command / Custom Script Extension /
  runbook is removed; the GA elevate-access toggle is turned back off.
- **Detect, don't assume, the posture.** State what the live vault auth model, MI roles, IMDS reachability,
  and Hybrid-Worker configuration actually are — not the current Azure default or an old research finding.
- **Loot/secret redaction.** A recovered token, SP secret, storage key, or Key Vault payload is reported as
  *that it was recovered and its blast radius*, never its value. Harvested data follows the scope file's
  data-handling rules.
- **Detection-surface awareness, never evasion-for-stealth.** Teach what the Entra logs, Activity Log,
  Defender and Sentinel observe so a tester knows their footprint and a defender knows what to tune — never
  a technique whose purpose is evading detection on a real target (D5). Password spray, device-code
  phishing, and PRT abuse are awareness-only.
- **Use current names and current tools.** "Entra ID", not "Azure AD" (note the old name once); ROADrecon
  **msgraph fork**; AzureHound+BloodHound over Stormspotter; version-check the Hybrid-Worker `ListKeys`
  path.
- **Two-class reporting:** every finding carries its ATT&CK **Cloud** technique id and is scored **CVSS** in
  the final report (`penetration-testing:reporting`), never the blocker/major/minor/nit table.
- **Log every act** — command, target, timestamp, ATT&CK Cloud id — into the engagement action log as it
  runs, per `penetration-testing:reporting`.
- **Production is a separate, louder gate than lab.** Default target is **AzureGoat** or a non-production
  owned tenant; production needs the second sign-off.

## Cross-references

- **`penetration-testing:cloud-recon-enumeration`** — the upstream step: produces the token,
  principal/role map, metadata-service leads, and OIDC/federation findings this skill consumes. This skill
  never does its job (anonymous/public discovery, federation trust review).
- **`devops:cloud-posture`** — the **defensive** sibling: Prowler/ScoutSuite already read Azure posture
  (read-only CSPM). A `cloud-posture` finding ("vault uses access-policy auth", "storage key access
  allowed", "MI Contributor at subscription scope") is a lead here; this skill proves it is reachable and
  chains it, then reports confirmed exploitability back as validated posture. The handoff runs both ways.
- **`cloud-attack-aws`** / **`cloud-attack-gcp`** — the sibling provider skills under the same
  `penetration-tester` step; same role, different provider, no shared files.
- **`penetration-testing:initial-access`** — the network/application-foothold sibling; it lands the foothold
  (e.g. an SSRF in an App Service app) that this skill chains into MI IMDS token theft, but does not itself
  abuse the cloud API.
- **`penetration-testing:lateral-movement`** — the cloud-pivot sibling: once this skill mints a token or SP
  credential, cross-subscription / cross-tenant movement along existing trust and the Azure resource graph
  is lateral movement's concern; this skill produces the identity, that skill reaches the next in-scope
  resource with it.
- **`security/atomic-simulation`** — the purple-team sibling that *detonates* cloud ATT&CK techniques
  (Stratus Red Team) against a lab to test whether Sentinel/Defender fires; this skill performs the
  exploitation those detonations model, but the two never substitute for each other.
- **`penetration-testing:reporting`** — where every act is logged (action log) and every finding is scored
  (CVSS) and mapped (ATT&CK Cloud).
- **`security/cloud-incident-response`** — the defensive response peer: a confirmed Azure finding here
  implies the Azure IR runbook (`references/azure-ir.md`) and detection authoring
  (`security/detection-engineering`) that respond to it — each finding carries the detection it should have
  tripped.
