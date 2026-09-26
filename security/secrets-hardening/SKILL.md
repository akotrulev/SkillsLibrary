---
name: secgov-secrets-hardening
description: Use to fix the secret after it is found — rotation runbooks, wiring the app to a secret store (Vault / cloud secret manager / SOPS / ESO), and preventing recurrence (pre-commit + CI gates, dynamic credentials). The defensive complement to secrets-scan, which only detects. Triggers "rotate this leaked credential", "wire the app to a secret store". Not for detecting secrets (`secrets-scan`), typed app config (`devops-environment-config`), or exploiting a recovered secret (`penetration-tester`).
---

# Security Governance — Secrets Hardening (rotation runbooks · secret-store wiring · recurrence prevention)

`secrets-scan` (Gitleaks + TruffleHog) answers *"is there a secret in the code/history?"* and stops at **"rotate it."** This skill owns the **rotate-it and never-again**: the rotation runbook that revokes the leaked credential at its source without an outage, the secret store the app should read from instead of a `.env`, and the gates + dynamic-credential patterns that stop the next leak from happening. It is the **defensive complement to detection**: `secrets-scan` detects, this hardens.

This skill is **language-agnostic** (Vault, the cloud secret managers, SOPS, ESO are all CLI/API-driven; the app-side is a typed client) and homes in the **`security-governance`** plugin, loaded by the **`security-architect`** agent when the posture roll-up finds a secrets gap. Deep app-side wiring (the typed config binding, the DI registration) hands off to `devops-environment-config` / `be-*` / `fe-*`; this skill owns the **store choice, the rotation runbook, and the recurrence gate**.

> **The load-bearing rule inherited from `secrets-scan`: rotate first, purge second.** A secret committed and then "deleted" is **still in the git history** and is compromised the moment it lands on a remote — assume it is public. **Rotate the credential at its source before anything else**; only then purge history (`git filter-repo` / BFG) if required. Deleting the line without rotating is theatre.

## Two spines, stated per finding

- **OWASP** — leaked/weakly-managed secrets map to **A02:2025 Security Misconfiguration** (hardcoded/plaintext secrets) and **A07:2025 Authentication Failures** (static, long-lived, un-rotated credentials — the 2021 list called this "Identification & Authentication Failures"). A leaked credential that grants access is also the **initial-access feedstock** the offensive lane consumes — which is exactly why rotation is urgent.
- **Compliance** — secret rotation and access control are explicit controls in every framework: **PCI DSS 8.3.9 / 3.x** (key management, credential rotation), **SOC 2 CC6.1** (logical access), **ISO 27001:2022 A.5.17 / A.8.24** (authentication information, cryptographic key management), **NIST CSF 2.0 PR.AA**. `secgov-compliance-evidence-mapping` maps a working rotation control to these.

Severity on the library's **blocker/major/minor/nit** table (a live leaked credential granting production access is a **blocker**).

## Decision matrix — where should the secret live?

| Situation | Store | Why |
|---|---|---|
| Kubernetes workloads, one platform team | **External Secrets Operator (ESO)** syncing from a backend → native K8s `Secret` | apps read a standard `Secret`; ESO owns the sync + refresh; the backend owns the truth |
| Centralized, multi-app, want **dynamic short-lived** creds | **HashiCorp Vault** | dynamic secrets (DB/cloud creds minted per-request, auto-expiring), leasing, central audit; ESO or Vault Secrets Operator (VSO) bridges to K8s |
| AWS-native app, scheduled DB-credential rotation | **AWS Secrets Manager** | Lambda-based **managed rotation** with templates for RDS/Redshift/DocumentDB — the strongest native scheduled-rotation story |
| Azure-native | **Azure Key Vault** | rotation configured per object type (secrets/keys/certs); event-driven rotation via Event Grid; certs rotate natively |
| GCP-native | **GCP Secret Manager** | notification/Pub-Sub-driven rotation (you wire the rotation handler); versioned secrets |
| Encrypted secrets **in Git** (small teams, GitOps) | **SOPS** (age / cloud-KMS keys) | files stay in Git, encrypted at rest; **caveat below** |

**Prefer dynamic/short-lived over static-and-rotated.** The best-hardened secret is one that does not persist: Vault dynamic DB credentials or a cloud role assumed via **OIDC/Workload Identity Federation** (the `devops` two-invariant — *no static cloud keys*) expire on their own, so a leak is bounded to minutes. Reach for rotation of a static secret only when a dynamic credential is not available for that dependency.

> **SOPS caveat — state it.** SOPS keeps secrets in Git encrypted, but **access to the repo plus access to the decryption key equals access to every secret** — and key material is the hard part. SOPS suits small teams with strict KMS-key governance; it is **not** a substitute for a real secret store with per-secret access control, leasing, and audit at scale.

## The rotation runbook — the deliverable

A rotation runbook is a repeatable, ordered procedure (author it once per credential *type*, not per incident) that rotates without an outage. The core is the **two-slot / dual-secret pattern** — never a single in-place overwrite, which races every running instance:

1. **Create the new credential** alongside the old (both valid) — a second API key, a new DB user, a new key version.
2. **Roll consumers** onto the new credential (store update → app refresh / rolling restart / ESO resync) — the old one still works, so nothing breaks mid-roll.
3. **Verify** every consumer is on the new credential (traffic on the new key, none on the old).
4. **Revoke the old credential** at its source — only after step 3 confirms nothing depends on it.
5. **Log** the rotation (who, when, why — leak vs scheduled) to the audit trail; **never log the value.**

Runbook rules: a **defined RTO** ("rotated within N hours of detection"); an **emergency path** (leaked-now: create-roll-revoke on the fastest safe timeline, accept a brief dual-validity) distinct from the **scheduled path** (every N days, hands-off); and an **owner** named per credential type. Automate the scheduled path (AWS managed rotation / a Vault rotation policy / an ESO refresh); keep the emergency path a documented human procedure because judgement (blast radius, which consumers) is involved.

## Recurrence prevention — the gate

Rotation cleans up; the gate stops the next leak:

- **Pre-commit hook** — Gitleaks (`gitleaks protect --staged`) or `git-secrets` blocks the commit *before* the secret enters history. The cheapest possible fix: it never reaches the remote, never needs rotating.
- **CI gate** — `secrets-scan` (Gitleaks + TruffleHog full-history) fails the build on a new finding. The backstop when the local hook is missing.
- **Kill the source of leaks** — inject secrets from the store at runtime (env var from ESO/Vault agent, or the app's typed client reading the store), so there is no `.env`/`appsettings.json`/`application.yml` secret to commit in the first place. A leak you made structurally impossible needs no rotation.
- **Least privilege + short TTL** on every issued credential, so even an undetected leak is bounded.

## App-side wiring — own the seam, hand off the plumbing

This skill decides the store and the pattern; the language-specific binding is the owning stack's:

- **`devops-environment-config`** — the typed config classes, the layering (defaults → per-env → secrets-from-store), startup schema validation, and the K8s/deploy wiring (ESO manifests, Vault agent sidecar).
- **`be-*` / `fe-*`** — the DI registration of the typed secret client, the `IHttpClientFactory`/SDK credential provider reading the store.
- This skill states *"read `DB_PASSWORD` from Vault path `secret/data/app/db`, TTL 1h, dynamic"* — they write the code that does it.

## Anti-patterns

- **Deleting the committed line without rotating.** The secret is still in history and already compromised. *Fix:* rotate at source first (the inherited hard rule), then purge history if required.
- **Single in-place overwrite rotation.** Overwriting the one live secret races every running instance — some hit the old, some the new, requests fail mid-rotation. *Fix:* the two-slot dual-secret pattern (create → roll → verify → revoke).
- **Rotating a static key when a dynamic credential exists.** You keep the long-lived-secret risk and add rotation toil. *Fix:* Vault dynamic secrets / OIDC-assumed cloud roles — no persistent secret to rotate.
- **SOPS as the enterprise answer.** Repo access + key access = all secrets; key governance is the unsolved hard part. *Fix:* a real store with per-secret access control, leasing, and audit at scale; SOPS only for small teams with strict KMS governance.
- **A rotation runbook with no verify step.** Revoking the old credential before confirming consumers moved causes the outage you were avoiding. *Fix:* step 3 (verify traffic on the new credential) gates step 4 (revoke).
- **Logging the rotated value "for debugging."** The rotation log is an audit trail, not a secret store. *Fix:* log who/when/why, never the value; loot-redaction applies to your own runbooks too.
- **Hardening the store but leaving the leak channel open.** A perfect Vault setup plus a committed `.env` is not hardened. *Fix:* the pre-commit + CI gate + runtime injection close the channel.

## Hard rules

- **Rotate first, purge second** (inherited from `secrets-scan`) — a committed secret is compromised; rotate at source before deleting/purging history.
- **Two-slot rotation, never in-place overwrite** — create → roll consumers → verify → revoke; a verify step gates revocation.
- **Prefer dynamic/short-lived over static-and-rotated** — Vault dynamic secrets / OIDC-assumed roles bound a leak to minutes; rotate a static secret only when no dynamic credential is available. **No static cloud keys** (the `devops` invariant).
- **Close the leak channel** — inject from the store at runtime so there is no committed secret; back it with a pre-commit hook + the `secrets-scan` CI gate.
- **Least privilege + a TTL** on every issued credential; a named owner and a defined RTO per credential type.
- **Never log the value** — the rotation/audit log records who/when/why; the report states blast radius, never contents (loot redaction).
- **This skill decides the store + runbook; the app-side binding hands off** to `devops-environment-config` / `be-*` / `fe-*`.

## Cross-references

- **`qa-security-secrets-scan`** (`qa/_shared/security-testing/secrets-scan/`) — the **detection** half and the trigger for this skill: it finds the secret and says "rotate"; this owns the rotation, the store, and the gate that stops recurrence. Its rotate-not-delete rule is inherited here.
- **`security-architect`** (`security/agents/security-architect.md`) — the roll-up agent that loads this skill when the posture picture shows static/long-lived credentials or a leaked secret.
- **`devops-environment-config`** (`devops/environment-config/`) — owns the typed config classes, secret-store deploy wiring (ESO/Vault agent), layering, and startup validation; this skill hands the store choice + rotation contract to it.
- **`devops-infra-controls-validation`** (`devops/infra-controls-validation/`) — validates the secrets/encryption control is not just present but **effective**; a rotation runbook this skill authors is what it retests.
- **`penetration-tester`** (`security/agents/penetration-tester.md`) — the offensive consumer: an un-rotated leaked credential is its `initial-access` / `credential-attacks` feedstock. Rotation urgency is measured against how fast that lane could use it.
- **`secgov-compliance-evidence-mapping`** — maps a working rotation control to PCI 8.3.9 / SOC 2 CC6.1 / ISO A.5.17 / A.8.24 evidence.
- **`secgov-detection-engineering`** — the tripwire counterpart: author a detection for *use* of a credential from an unexpected source, so a leak that slips the gate is still caught in the logs.
