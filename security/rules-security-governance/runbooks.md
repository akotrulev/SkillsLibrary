---
paths:
  - "docs/security/runbooks/**"
---

<!-- security-governance rules v1 (2026-11-03): runbooks. Installed by /security-governance:rules; edit to fit this project. -->

# Rotation and incident-response runbook standards

Severity tags as in the core security-governance rules. The repo wins where it consistently does otherwise.

## Credential rotation

- One runbook per credential type, not per incident. *major*
- Two-slot: create, roll consumers, verify, revoke; never an in-place overwrite. *blocker*
- A verify step (traffic on the new credential) gates revocation. *blocker*
- On a leak, rotate at source first and purge history second, if at all. *blocker*
- Emergency and scheduled paths are distinct; the scheduled one uses the platform's managed rotation where it exists. *major*
- A named owner and an RTO per credential type, and every consumer of the credential listed. *major*
- The log records who, when and why, never the value; no step echoes or stores the new secret. *blocker*

## Cloud incident response

- Anchored to NIST SP 800-61r3 and PICERL, both named. *major*
- Acquire before destroying: memory, then disk, then logs, before any isolation; `stop`, never `terminate`, with deletion-on-termination off. *blocker*
- Contain the identity as well as the host: deny the principal, deactivate keys, revoke live sessions. *blocker*
- Chain of custody on every artifact: SHA-256 at acquisition and after copy, a forensics-owned key, object lock or legal hold. *major*
- Rebuild from known-good images, never clean in place; rotate every secret that may be exposed. *major*
- The precondition is stated: durable, out-of-band logs. Without them the runbook says reconstruction, not response. *major*
- Azure steps cover both Log Analytics (KQL) and the Defender portal. *minor*
- A detection gap found here is routed to detection engineering, never authored in the runbook. *minor*
