# 04 — Microsoft Azure Security (M9–M10)

> **Scope.** Knowledge base for course modules **M9 (Azure Security Fundamentals)** and **M10 (Azure Penetration Testing)**, feeding authoring of the skill `security/cloud-attack-azure`. **Authorized self-testing and lab training only** — owned Azure tenants/subscriptions, committed scope file, expiring written authorization. Teach **detection-surface awareness** (Microsoft Sentinel / Defender for Cloud), never evasion-for-stealth against a live target. Recovered secrets are reported as **blast-radius, never values**. **No DoS, ever.**
>
> **Terminology note (verified 2026-10):** **Azure Active Directory (Azure AD / AAD) was renamed Microsoft Entra ID** — announced 2023-07-11, effective 2023-07-15. Capabilities, APIs, PowerShell cmdlets and sign-in URLs did **not** change; only the brand did. "Azure AD tenant" → "Entra tenant"; "Azure AD Conditional Access" → "Microsoft Entra Conditional Access"; P1/P2 licenses → "Entra ID P1/P2". Older labels (`Azure AD`, `AAD`) still appear in portals, APIs (`graph.windows.net` = legacy Azure AD Graph), tool names (AzureHound, ROADtools), and MITRE text, and mean the same service. This doc uses **Entra ID** for the identity plane and flags legacy names where tools/APIs keep them.

---

## Azure fundamentals as attack context

Azure has **two independent authorization planes**. Confusing them is the single most common source of scoping errors in an engagement; they are secured separately and **neither grants access in the other** (Microsoft: "Entra role assignments do not grant access to Azure resources, and Azure role assignments do not grant access to Entra ID").

| Plane | Secures | Role system | Top role | Scope hierarchy | API / endpoint |
|---|---|---|---|---|---|
| **Entra ID (directory / identity)** | Tenant: users, groups, app registrations, service principals, directory settings | **Entra roles** (directory roles) | **Global Administrator** | Tenant-wide (flat; some admin-unit scoping) | Microsoft Graph (`graph.microsoft.com`); legacy Azure AD Graph (`graph.windows.net`, retiring) |
| **Azure RBAC (resource / subscription)** | Subscriptions, resource groups, resources (VMs, storage, Key Vault…) | **Azure RBAC roles** | **Owner** (+ **User Access Administrator** for grants) | Management group → subscription → resource group → resource | Azure Resource Manager (ARM, `management.azure.com`) |

**The bridge — control-plane escalation across the two planes.** A **Global Administrator** can toggle *Access management for Azure resources* (Entra admin center → Properties). This assigns that user the **User Access Administrator** Azure RBAC role at **root scope `/`**, granting role-assignment rights over **every** subscription and management group in the tenant. It is **per-user, not tenant-wide**, and Microsoft advises toggling it back off after use. This is the canonical "GA → owns all of Azure" pivot and a primary thing to look for.

**Core services an engagement touches**

- **Compute:** Virtual Machines (+ extensions: Run Command, Custom Script Extension), App Service / Functions (serverless), AKS, Azure Automation (Runbooks, Hybrid Workers).
- **Storage & data:** Storage Accounts (Blob/File/Queue/Table; account keys + SAS), Cosmos DB, Azure SQL.
- **Identity & secrets:** Entra ID, **Key Vault** (secrets/keys/certs), Managed Identities.
- **Governance:** Management groups, Subscriptions, Resource Groups, Azure Policy, Blueprints.

**Identity objects to distinguish (the vocabulary the whole attack chain rides on):**

- **App registration** — the *definition* (application object) of an application in the home tenant; holds the app's identity, redirect URIs, API permissions, and **credentials** (client secrets / certificates).
- **Service principal (SP)** — the *instance* of an app in a tenant (enterprise application); what actually gets role assignments and signs in. Non-interactive; authenticates with a client secret, certificate, or federated credential. **SP credentials are reusable, long-lived, and often over-privileged — a top loot target.**
- **Managed Identity (MI)** — an Azure-managed SP whose credentials Azure rotates and never exposes to you:
  - **System-assigned** — 1:1 tied to a single resource's lifecycle; deleted with the resource. Stolen token scoped to that one identity's roles.
  - **User-assigned** — standalone resource; **attachable to many resources**, so compromising any one host that carries it exposes the whole identity's permissions → **larger blast radius**.

---

## Entra ID enumeration & abuse

*(This is a spine section of the skill.)*

Entra ID enumeration begins **unauthenticated** (tenant exists? federation? valid usernames?) and deepens once any token is held. Even a low-privileged member or **guest** can typically read large parts of the directory by default.

**Unauthenticated / pre-auth recon**
- **Tenant discovery:** `login.microsoftonline.com/<domain>/.well-known/openid-configuration`, `getuserrealm.srf`, `autodiscover` — reveals tenant ID, federation (managed vs federated), brand.
- **User/validity enumeration:** error-code differences on auth endpoints (username-valid vs not). **Password spray is explicitly out of scope here as it risks lockout/DoS — awareness only.**

**Authenticated directory enumeration (T1087 Account Discovery: Cloud Account / Cloud Groups)** — read and map:
- Users, groups (and **dynamic group** rules — membership you can influence by editing an attribute), roles & role assignments, administrative units.
- **App registrations & service principals** — their API permissions (`Application` vs `Delegated`), credentials present, owners (an **owner can add a new credential** to an app/SP they own → impersonate it).
- **Conditional Access awareness:** enumerate CA policies to understand *which controls exist* (MFA requirements, device compliance, named locations, device-code restrictions). **Awareness, to reason about blast radius and reporting — not to craft bypass against a live tenant.**
- **Guest / external access:** B2B guests, cross-tenant access settings, and default guest-permission level (how much a guest can read). External identities are a frequent lateral path.

**Consent & app abuse (T1098 Account Manipulation / T1098.003 Additional Cloud Roles; T1528 Steal Application Access Token)**
- **Illicit consent / OAuth app abuse:** register (or inject) an app, induce consent to Graph scopes (`Mail.Read`, `Files.ReadWrite.All`, etc.), and retain delegated/app access that survives password resets. **Persistence** mechanism — note it; do not run phishing against third parties.
- **Credential addition to an existing SP/app:** add a client secret or certificate to an app you can write to → durable non-interactive access as that SP (classic persistence + privesc).
- **Role manipulation:** assign a privileged Entra role (e.g., Privileged Role Administrator, Application Administrator — which can add SP credentials) to a controlled principal.

**PRT / device-code concepts (awareness level only)**
- **Device-code phishing (RFC 8628):** attacker starts a *legitimate* device-code flow and the victim enters the real code at Microsoft's genuine login page; attacker polls for the tokens. Nation-state → commodity (Storm-2372, active since Aug 2024). Mitigation defenders apply: **block device-code flow via Conditional Access** for users with no need.
- **Primary Refresh Token (PRT):** by requesting tokens as the **Microsoft Authentication Broker** client (`29d9ed98-a469-4536-ade2-f981bc1d605e`) an actor can register an attacker-controlled device and obtain a **PRT**, which can bypass device-based CA/MFA. **Concept only for blast-radius reasoning; the skill teaches recognition and detection, not execution against live users.**

---

## Managed identity & service principal abuse

**IMDS token theft (T1552.005 Unsecured Credentials: Cloud Instance Metadata API → T1078.004 Valid Accounts: Cloud Accounts)**

The **Instance Metadata Service (IMDS)** at **`169.254.169.254`** issues OAuth bearer tokens to any process on the host for the **managed identity** attached to it. It requires **no authentication** — the only gate is the header **`Metadata: true`**, a minimal anti-SSRF measure, not an auth control.

Request shape (awareness):
```
GET http://169.254.169.254/metadata/identity/oauth2/token
      ?api-version=2018-02-01
      &resource=https://management.azure.com/     # or ...vault.azure.net, ...graph.microsoft.com
Header: Metadata: true
```
- Returns an access token for the host's MI. For a **user-assigned** MI, add `&client_id=<miClientId>` (or `mi_res_id`). App Service/Functions use `IDENTITY_ENDPOINT` + `IDENTITY_HEADER` instead of the link-local IP.
- **Two ways to reach it:** (a) code execution on the host; (b) **SSRF** in an app running on the host. The `Metadata: true` header blocks naive URL-fetch SSRF but **not** SSRF that can set custom headers, follow redirects, or proxy. IP-filter bypasses (decimal/hex encodings of the IP, DNS rebinding) are documented leads.
- **Impact = the MI's RBAC roles.** Report as blast-radius: "MI held **Contributor** on RG `x` → could read all storage keys / deploy Run Command on all VMs." Never dump token values into the report.

**Service principal credential abuse**
- Loot SP client secrets/certs from: source control, pipeline variables, `.azure`/`.env` files, App Service config, ARM/Terraform state, Key Vault.
- Authenticate non-interactively: `az login --service-principal -u <appId> -p <secret|cert> --tenant <tid>` → act as the SP with its (often broad) roles. SP sign-ins frequently **bypass MFA** (no interactive user) — a reason they're prized.

---

## Key Vault security testing

Key Vault has a **control plane** (manage the vault resource, via Azure RBAC) and a **data plane** (read/write secrets, keys, certs). Data-plane authorization uses **one of two models**, set per vault:

| Model | How data access is granted | Key risks |
|---|---|---|
| **Access policies** (legacy) | Per-vault list of (principal → permitted operations on secrets/keys/certs). Data-plane only. | **No PIM support**; privilege-escalation risk (below); IaC can silently wipe other apps' policies by declaring an empty array. |
| **Azure RBAC** (recommended) | Standard RBAC roles (e.g., **Key Vault Secrets User**, **Key Vault Administrator**) scoped management-group→resource. Spans control + data plane. | Simpler to audit; still over-grant if assigned at subscription scope. |

**The classic misconfig (privilege escalation):** under the **access-policy** model, the **Key Vault Contributor** control-plane role was meant to manage vaults *without* reading data — but it can **edit access policies and grant itself** data-plane access → read every secret. The remediation (and the thing you flag) is **migrate to RBAC** and remove unauthorized policy entries. Detection rules (Datadog, Defender for Cloud) flag vaults where `enableRbacAuthorization` is not `true`.

**Reading secrets with a compromised identity** (data plane, `*.vault.azure.net`):
```
az keyvault secret list   --vault-name <v>
az keyvault secret show    --vault-name <v> --name <s>          # value → report as blast-radius, not the value
az keyvault key list       --vault-name <v>
az keyvault certificate list --vault-name <v>
```
Equivalent via MI token: request a token for `resource=https://vault.azure.net`, then call the Key Vault REST API.

**Common misconfigs to enumerate:** access-policy model still in use; vault reachable from public network (no private endpoint / firewall `defaultAction: Allow`); over-broad data-plane grants (an MI/SP with `Get/List` secrets it doesn't need); soft-delete/purge-protection off; secrets stored that are themselves high-value pivots (SP secrets, storage keys, DB connection strings). **Blast-radius chain to show:** compromised web app's MI → `Key Vault Secrets User` on vault → DB connection string → database.

---

## Azure RBAC privilege escalation & service attacks

**Role-assignment abuse (control plane).** By default **Owner**, **User Access Administrator**, and **Role Based Access Control Administrator** hold `Microsoft.Authorization/roleAssignments/write` — they can **grant roles**, including granting themselves/another principal **Owner**. **Owner / UAA at a high scope (management group / subscription) = game over for that scope.** Also: holders of `roleDefinitions/write` (Owner, UAA, RBAC Admin) can **edit a custom role definition** to add `Actions`, silently raising privileges of everyone assigned it.

**Storage account key theft (T1552 / T1078.004).** `Microsoft.Storage/storageAccounts/listKeys/action` (held by **Contributor**, Owner, Storage Account Contributor) returns the **account key** = full control of all blobs/files/queues/tables, bypassing data-plane RBAC. Also mint **SAS** tokens for scoped, time-boxed exfil-capable access.
```
az storage account keys list -n <acct> -g <rg>     # key → blast-radius, never the value
```

**Attacking VMs — command execution without creds.** With the right RBAC action you run arbitrary commands **as SYSTEM/root** on a VM:
- **Run Command** — `Microsoft.Compute/virtualMachines/runCommand/action` (built into Contributor/VM Contributor): `az vm run-command invoke -g <rg> -n <vm> --command-id RunShellScript --scripts "<cmd>"`. From there, read the VM's **MI token from IMDS** → pivot.
- **Custom Script Extension** — push a script extension to a VM for execution/persistence (NetSPI research). Same outcome, different mechanism.

**Automation Accounts & Runbooks.**
- Create/edit a **Runbook** and run it on an Azure sandbox or a **Hybrid Worker** → code execution with the Automation Account's identity (often a **Run As** account historically with subscription **Contributor**, or a user-assigned MI).
- **Hybrid Workers** run on-prem/VM boxes; local admin there can harvest the worker's credentials/MI (NetSPI Parts 1–2). Microsoft has since removed `ListKeys` from the **Reader** role and pushes the extension-based Hybrid Worker with Entra auth — **version-check the tenant before asserting the old path.**

---

## Detection surface (awareness, not evasion)

The skill teaches operators to **understand what fires**, so findings are realistic and reports note detectability — **not** how to evade on a live target.

| Source | What it records / detects |
|---|---|
| **Entra ID Sign-in logs** | Interactive + non-interactive (SP/MI) sign-ins; the **client app / client ID** used (e.g., the broker `29d9ed98-…` that flags device-code/PRT abuse); IP, device, CA result, MFA, risk. |
| **Entra ID Audit logs** | Directory changes: **app credential added**, consent grants, role assignments, group membership, CA policy edits — the T1098 trail. |
| **Entra ID Protection** | Risky sign-ins/users: impossible travel, anonymous IP, token anomalies, leaked credentials. |
| **Azure Activity Log** | Control-plane ARM operations: `listKeys`, `roleAssignments/write`, `runCommand`, extension deploys, Key Vault policy edits. |
| **Key Vault logs (→ diagnostic / Log Analytics)** | Every data-plane `SecretGet`/`KeyList`/etc. with caller identity — bulk secret reads stand out. |
| **Microsoft Defender for Cloud** | CSPM posture (vault not-RBAC, public storage, exposed MI); CWPP threat alerts (anomalous Key Vault access, suspicious Run Command, IMDS-token misuse patterns). Secure Score. |
| **Microsoft Sentinel** | SIEM/SOAR over the above via KQL; ships analytics rules for mass secret enumeration, impossible travel, device-code sign-ins, suspicious SP credential additions. |
| **Third-party** | Elastic prebuilt rules detect **ROADrecon** (aiohttp Azure AD Graph bursts) and **device-code broker** sign-ins. |

Loud, high-signal actions to flag in a report: `listKeys`, bulk Key Vault reads (ROADrecon-style bursts), `roleAssignments/write`, Run Command, new SP client secret, device-code sign-ins.

---

## Tools

| Tool | Purpose | Invocation (illustrative) | What it answers | Reference |
|---|---|---|---|---|
| **ROADtools / ROADrecon** (Dirk-jan Mollema) | Entra ID directory enumeration + offline graph DB/web UI from a token | `roadrecon auth …` → `roadrecon gather` → `roadrecon gui` | Full directory dump: users, groups, apps, SPs, roles, CA — "what does this token see?" **Caveat:** legacy **Azure AD Graph is retiring**; upstream `msgraph` branch stale since Apr 2025 — use a community Microsoft-Graph fork. aiohttp client is **detectable** (Elastic rule). | `references/roadtools.md` |
| **AzureHound** (SpecterOps) | Collector for **BloodHound** Azure edges | `azurehound -u <user> -p <pass> list -t <tenant> -o out.json` | Attack paths: who can reach **Global Admin / Owner**; role, group, MI, SP, app relationships | `references/azurehound.md` |
| **MicroBurst** (NetSPI, PowerShell) | Broad Azure enumeration + external recon | `Import-Module MicroBurst.psm1`; `Invoke-EnumerateAzureSubdomains`; `Get-AzStorageKeysREST` | External: valid storage/subdomain names (pre-cred); internal: storage keys, KeyVault, Automation, app secrets | `references/microburst.md` |
| **GraphRunner** (Black Hills, PowerShell) | M365/Entra **post-exploitation** over Microsoft Graph | `Import-Module GraphRunner.ps1`; `Get-GraphTokens` (device-code); `Invoke-GraphRecon`; `Invoke-InjectOAuthApp`; `Invoke-SearchMailbox` | Recon (CA, apps, consent), data pull (mail/SharePoint/OneDrive/Teams), persistence (malicious OAuth app, group clone) | `references/roadtools.md` (grouped) |
| **az CLI / Az PowerShell** | First-party enumeration + the actual attack actions | `az account show`; `az role assignment list --all`; `az vm run-command invoke …`; `az keyvault secret list …`; `az storage account keys list …` | Ground-truth of current identity's effective access, and the privesc/loot actions themselves | `references/azure-keyvault.md` + inline recipes |
| **Stormspotter** (Azure org repo) | Azure subscription attack-graph visualizer (Neo4j) | `stormcollector` → `stormspotter` UI | Resource/identity graph of a subscription | *(status: no "archived" banner confirmed; last push ~Jan 2024, effectively dormant — prefer AzureHound+BloodHound as primary; note in lab-setup)* |

**Reference files planned:** `references/roadtools.md`, `references/azurehound.md`, `references/microburst.md`, `references/azure-keyvault.md`, `references/lab-setup.md`.

---

## MITRE ATT&CK Cloud mappings

Azure/Entra-relevant techniques (Enterprise matrix, Cloud platforms: Azure AD / IaaS / Office 365):

| ID | Technique | Where it lands here |
|---|---|---|
| **T1595 / T1590** | Active Scanning / Gather Victim Network Info | Unauth tenant & user discovery |
| **T1087.004** | Account Discovery: Cloud Account | Entra user/group enumeration |
| **T1069.003** | Permission Groups Discovery: Cloud Groups | Role/group enumeration |
| **T1526** | Cloud Service Discovery | Subscription/resource enumeration (MicroBurst, az) |
| **T1538** | Cloud Service Dashboard | Portal/ARM recon |
| **T1078.004** | Valid Accounts: Cloud Accounts | SP creds, MI tokens, stolen user tokens |
| **T1552.005** | Unsecured Credentials: Cloud Instance Metadata API | **IMDS token theft** |
| **T1552.001** | Unsecured Credentials: Credentials in Files | SP secrets in repos/pipelines/state |
| **T1528** | Steal Application Access Token | OAuth/device-code token theft |
| **T1098.001 / .003** | Account Manipulation: Additional Cloud Credentials / Roles | **Add SP credential**; grant Entra/Azure role |
| **T1136.003** | Create Account: Cloud Account | Backdoor user/SP |
| **T1098.001** | Illicit consent / OAuth app | GraphRunner `Invoke-InjectOAuthApp` |
| **T1651** | Cloud Administration Command | **VM Run Command / Custom Script Extension** |
| **T1580** | Cloud Infrastructure Discovery | Resource graph (AzureHound/Stormspotter) |
| **T1537 / T1530** | Transfer to Cloud Account / Data from Cloud Storage | Storage-key + SAS exfil |
| **T1484.002** | Domain/Tenant Policy Modification: Trust Modification | Federation/CA abuse (awareness) |

---

## Owned-lab targets

**AzureGoat** (`github.com/ine-labs/AzureGoat`) — INE's intentionally-vulnerable Azure environment, deployed by **Terraform into your own subscription**. Black-box by design, with escalation paths to full-infra takeover.

Scenarios / surfaces it exercises:
- **Serverless vulnerable blog** on **Azure Functions** → OWASP Top 10 (2021) web flaws.
- **SSRF** on the App Function environment → reach **IMDS** → steal the Function's **managed identity** token.
- **Storage Account** misconfigurations (public/over-permissive access, key exposure).
- **Cosmos DB** backing store.
- **Azure Automation** (runbooks) in the chain.
- **Identities / RBAC** misconfigurations enabling privilege escalation across the above.

**`references/lab-setup.md` sketch**
- **Prereqs:** owned Azure subscription (not shared/corp); `az` CLI + Terraform; a scoped SP or user with Contributor on a *dedicated throwaway RG*; committed **scope file** + unexpired authorization; budget alert set; region chosen.
- **Deploy:** clone official INE repo → `terraform init` → `terraform plan` → `terraform apply`; capture the output app URL and resource IDs into the engagement notes.
- **Guardrails:** isolated subscription, no production peering, tag all resources `purpose=lab`, **no DoS/stress tooling**, secrets reported as blast-radius.
- **Teardown:** `terraform destroy`; verify RG deleted; rotate/remove the lab SP; confirm no orphaned public IPs/storage; note teardown time against authorization expiry.
- **Optional second range:** PurpleCloud / Azure MonkeyCTF-style for Entra-focused drills; keep each in its own subscription.

---

## How it feeds our skill

Maps to `security/cloud-attack-azure/SKILL.md`:

| SKILL.md section | Fed by (this doc) |
|---|---|
| **Orientation / two-plane model + authorization guardrails** | *Azure fundamentals as attack context* + scope banner |
| **Recon & enumeration** | *Entra ID enumeration & abuse* (unauth → authed), Tools (ROADtools/AzureHound/MicroBurst) |
| **Identity abuse & token theft** | *Managed identity & SP abuse* (IMDS), device-code/PRT awareness |
| **Secrets & Key Vault** | *Key Vault security testing* |
| **Privilege escalation & service attacks** | *Azure RBAC privesc* (roles, storage keys, Run Command, Automation) |
| **Detection & reporting** | *Detection surface* + blast-radius reporting convention |

**Five reference files** the skill ships, sourced from the Tools + lab sections:
1. `references/roadtools.md` — ROADrecon/ROADtools (+ GraphRunner), Graph-vs-legacy-Graph caveat, detectability.
2. `references/azurehound.md` — AzureHound collection + BloodHound Azure path queries.
3. `references/microburst.md` — MicroBurst modules (external recon + internal loot).
4. `references/azure-keyvault.md` — access-policy vs RBAC, Contributor-privesc misconfig, data-plane read recipes.
5. `references/lab-setup.md` — AzureGoat deploy/teardown + guardrails.

---

## Sources

- Microsoft Entra ID rename — [Wikipedia](https://en.wikipedia.org/wiki/Microsoft_Entra_ID), [Petri](https://petri.com/azure-ad-rebrand-microsoft-entra-id/)
- Entra roles vs Azure RBAC / Global Admin elevate-access — [Microsoft Learn: Elevate access](https://learn.microsoft.com/en-us/azure/role-based-access-control/elevate-access-global-admin), [KodeKloud AZ-104 notes](https://notes.kodekloud.com/docs/Updated-AZ-104-Microsoft-Azure-Administrator/Administer-Governance-and-Compliance/Azure-RBAC-vs-Microsoft-Entra-ID-Roles/page)
- ROADtools / ROADrecon status & Graph migration — [Unit42: ROADtools cloud attacks](https://unit42.paloaltonetworks.com/roadtools-cloud-attacks/), [Elastic: ROADrecon enumeration rule](https://www.elastic.co/docs/reference/security/prebuilt-rules/rules/integrations/azure/discovery_aad_graph_roadrecon_aiohttp_enumeration), [RedFox: Azure pentesting tools](https://www.redfoxsec.com/blog/azure-pentesting-tools-and-frameworks)
- AzureHound / MicroBurst / Stormspotter — [RedFox](https://www.redfoxsec.com/blog/azure-pentesting-tools-and-frameworks), [Stormspotter repo](https://github.com/Azure/Stormspotter)
- GraphRunner — [Black Hills: Introducing GraphRunner](https://www.blackhillsinfosec.com/introducing-graphrunner/), [GraphRunner Cheatsheet](https://www.blackhillsinfosec.com/?p=34509), repo `github.com/dafthack/GraphRunner`
- Key Vault access policy vs RBAC + Contributor privesc — [Datadog rule](https://docs.datadoghq.com/security/default_rules/azure_key_vault-azure-key-vault-should-not-be-configured-with-access-policy/), [Microsoft Learn: Key Vault RBAC guide](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide), [CyberSecurityNews: KV privilege escalation](https://cybersecuritynews.com/azure-key-vault-let-attackers-escalate-privileges/amp/)
- Managed identity / IMDS token theft — [Guardz: Exploiting Azure MI tokens from IMDS](https://guardz.com/blog/exploiting-azure-managed-identity-tokens-from-imds/), [CyberCX: Azure SSRF & metadata](https://cybercx.com.au/azure-ssrf-metadata)
- Device-code phishing / PRT — [Microsoft: Storm-2372 device code phishing](https://www.microsoft.com/security/blog/2025/02/13/storm-2372-conducts-device-code-phishing-campaign/), [Silverfort: device code attacks](https://www.silverfort.com/?p=17555), [CSA: OAuth device-code surge](https://labs.cloudsecurityalliance.org/research/csa-research-note-oauth-device-code-phishing-surge-20260405/)
- RBAC privesc / Run Command / Automation / Hybrid Workers — [NetSPI: Abusing Azure Hybrid Workers Pt.1](https://www.netspi.com/blog/technical-blog/cloud-pentesting/abusing-azure-hybrid-workers-for-privilege-escalation/), [NetSPI: Custom Script Extensions](https://www.netspi.com/blog/technical-blog/cloud-pentesting/attacking-azure-with-custom-script-extensions/), [Praetorian: Azure RBAC privesc on VMs](https://www.praetorian.com/blog/azure-rbac-privilege-escalations-azure-vm/)
- AzureGoat — [INE repo `github.com/ine-labs/AzureGoat`](https://github.com/ine-labs/AzureGoat), [DEF CON 30 listing](https://infocondb.org/con/def-con/def-con-30/azuregoat-damn-vulnerable-azure-infrastructure)
