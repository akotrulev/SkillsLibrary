# Azure Incident Response & Forensics — Sentinel/Defender triage · managed-disk snapshot · Entra session revoke

The Azure half of the runbook. The load-bearing Azure specific: **the Sentinel → unified Defender portal migration is not complete in 2026**, so every step names **both** the Log-Analytics (KQL) path and the Defender-portal path — which one an operator has depends on where their tenant is in the migration. This skill consumes the detection (Defender/Sentinel); it does not author it.

## Telemetry to read first

| Question | Source | Path note |
|---|---|---|
| Who called which control-plane API | **Azure Activity Log** (Authorization/Compute/Storage categories) | Route to a central **Log Analytics workspace** via diagnostic settings. |
| Directory / identity changes | **Entra ID audit logs** | Users/groups/apps/role changes. |
| Who authenticated, from where, at what risk | **Entra sign-in logs** (interactive + non-interactive + service-principal + managed-identity) + Identity Protection risk | **Needs Entra ID P1/P2** to ingest. As of 2026 `SigninLogs` still live in the **Log Analytics workspace**, not fully in the Defender portal. |
| What traffic moved | **NSG / VNet Flow Logs** + **Network Watcher** (packet capture) | — |
| Is this malicious (consumed) | **Microsoft Defender for Cloud** (CSPM + workload protection) + **Defender XDR** (endpoint/identity/cloud-app) | Triage the incident in **Sentinel** (or the Defender portal's unified incident view), pivot to **Defender XDR** for deep investigation. |
| Correlate / investigate / automate | **Microsoft Sentinel** (SIEM/SOAR on Log Analytics; KQL, UEBA, analytics rules, Logic App playbooks) | Migrating into the Defender portal; workbooks/connectors still partly in Log Analytics. |

Centralize via diagnostic settings → a central Log Analytics workspace with Sentinel on it (multi-workspace / Azure Lighthouse for a central SOC), under **immutable storage with legal hold**.

## Containment

- **Network isolation** — replace the VM's **NSG** with a forensic quarantine NSG (analyst path only); detach from the **VM scale set**; deregister from the **load balancer / Front Door backend**.
- **Identity isolation** —
  - **Disable the Entra user** (`az ad user update --account-enabled false`).
  - **Revoke sessions / refresh tokens** (`az ad user revoke-sign-in-sessions` / `Revoke-MgUserSignInSession`) — this is the token-level kill a stolen session needs.
  - **Remove role assignments** (`az role assignment delete`); rotate **app / client secrets** of a compromised service principal; for a **managed identity**, remove its role assignments (you cannot rotate an MI credential — the identity is the control point).
- **Preserve, don't power off** — prefer `stop` (deallocate only when necessary; deallocation releases the ephemeral OS disk on some SKUs — check first); snapshot before any destructive change.

## Forensic acquisition

1. **Metadata** — record VM id, resource group, subscription, region, managed disks, NICs, attached identities.
2. **Memory — before isolation** — OS-native memory dump **from inside the guest**; **Network Watcher** packet capture for live network state. No tenant hypervisor dump exists.
3. **Disk** — `az snapshot create` on the managed OS/data disk; **copy the snapshot to an isolated forensics resource group / subscription**, generate a disk from it for analysis. Prefer snapshot-before-remediation.
4. **Logs / config** — export Activity Log, Entra logs, resource diagnostic logs, and **Azure Resource Graph** state to **immutable storage with legal hold**; **hash** evidence for chain of custody. The **Microsoft Cloud Security Benchmark** IR controls name VM disk snapshot + OS memory dump + network flow logs as the evidence set.

A **Sentinel playbook** (Logic App) can automate snapshot + immutable export + hashing + evidence-record creation — prefer the automated, logged path over interactive RDP/SSH.

## Tools

| Tool | Invocation | What it answers |
|---|---|---|
| **Azure native snapshot** | `az snapshot create` → copy to forensics RG/sub → disk for analysis | "block image of the managed disk" |
| **Network Watcher** | Packet-capture session on the NIC | "what traffic the VM sent/received" |
| **Microsoft Sentinel** | KQL hunting; Logic App playbook (snapshot + export + hash) | "correlate, investigate, and automate response" |
| **Defender for Cloud / Defender XDR** | Triage in Sentinel/Defender portal → pivot to Defender XDR | "what the alert means across endpoint/identity/cloud" |
| **libcloudforensics / cloud-forensics-utils** (PyPI `libcloudforensics`, latest 2024-10-18) | `cloudforensics az <verb>` (az compute/network/storage modules) | "acquire this disk and isolate it, reproducibly and logged" |

## Both-paths note (do not assume the migration is finished)
- **Log-Analytics path:** KQL over `SigninLogs`, `AzureActivity`, `AuditLogs` in the workspace; Sentinel analytics rules + Logic App playbooks.
- **Defender-portal path:** unified incident view, Defender XDR advanced hunting (KQL over `DeviceEvents`/`IdentityLogonEvents`/`CloudAppEvents`), Defender-portal response actions.
- Author runbook steps to **both**; state which tables/views are expected where, because an operator may only have one.

## Runbook A — compromised Entra identity
Trigger: Entra risky sign-in / Defender identity alert.
1. **Triage** — timeline from Entra sign-in + Activity Log (both paths); enumerate the principal's role assignments and reach.
2. **Contain** — disable the user, **revoke sessions/refresh tokens**, remove role assignments, rotate SP client secrets.
3. **Eradicate** — delete attacker-created app registrations / OAuth consents / federated trust; rotate **all** related secrets and Key Vault access.
4. **Recover** — reissue least-privilege access; enforce MFA / Conditional Access; monitor for reuse.
5. **Close-out** — root cause; detection gap → `detection-engineering`.

## Runbook B — compromised Azure VM
Trigger: Defender for Servers alert / SCC-equivalent VM finding.
1. **Preserve first** — guest memory dump + Network Watcher capture **before** isolation; then `az snapshot create` the disk.
2. **Protect the evidence** — copy to forensics RG/sub, SHA-256 hash, legal-hold.
3. **Contain** — quarantine NSG, detach from scale set, deregister from LB, `stop`.
4. **Eradicate** — rebuild from a known-good image; find persistence (scheduled tasks, startup scripts, backdoor images).
5. **Recover** — redeploy clean via IaC; stage traffic; heightened monitoring.

## Runbook C — public Azure exposure
Trigger: open NSG `0.0.0.0/0` / public Blob container / Defender posture finding.
1. **Triage** — confirm exposure and access (Storage analytics, Flow Logs); assess data sensitivity.
2. **Preserve the current config first** (export NSG ruleset / storage access config), then remove public access immediately.
3. **Preserve** — snapshot access logs + Resource Graph state to immutable storage; hash.
4. **Eradicate** — fix the IaC/pipeline; add an **Azure Policy** `deny` guardrail at the management group.
5. **Recover / notify** — assess breach-notification obligations if data was accessed.

## Handoffs
- **← `detection-engineering`** — authors the Sentinel/Defender/Sigma logic; a close-out gap routes back here.
- **← `detection-validation`** — proves those detections fire.
- **→ `observability`** — dwell time / MTTR / containment latency; immutable log retention shared precondition.
- **↔ `devops:cloud-posture`** — its posture findings are what runbooks A/C remediate against.
- **BCDR** — RTO/RPO and Azure Site Recovery / Azure Backup restore in `cloud-resilience.md`.
