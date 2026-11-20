# Sentinel / Defender detection-surface awareness (awareness not evasion, D5)

Feeds Step 5 of `../SKILL.md`. Per **D5**, this teaches what an authorized action **emits** — so a tester
knows their footprint and a defender knows what to tune — and **never** how to evade detection against a
real target.

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
