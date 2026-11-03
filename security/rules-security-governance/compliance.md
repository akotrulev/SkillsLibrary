---
paths:
  - "docs/security/compliance/**"
---

<!-- security-governance rules v1 (2026-11-03): compliance. Installed by /security-governance:rules; edit to fit this project. -->

# Compliance evidence register standards

Severity tags as in the core security-governance rules. The register is evidence for an assessor, never an attestation.

- Only the frameworks in scope are mapped; no speculative column. *minor*
- The crosswalk cites the SCF or a published OSCAL mapping as its authority; never a hand-invented framework-to-framework mapping. *major*
- ASVS 5.0 is the bridge, with the verified level (L1, L2, L3) stated; never a fifth certifiable framework. *minor*
- Never claim certification ("SOC 2 compliant", "certified"); a QSA or auditor certifies. *major*
- Every row names its evidence artifact by a path that exists. *major*
- Status is `#present`, `#partial` or `#gap`, read from the artifact; never "met" or "yes". *major*
- `#present` never means effective without a validation artifact behind it, and a green pipeline is never the evidence. *major*
- Every `#partial` and `#gap` names the lane that closes it. *major*
- The gap list is ordered by leverage, not just listed. *minor*
- One control maps once and fans out to every framework. *minor*
- With card data in scope, PCI DSS 6.4.3 and 11.6.1 are addressed. *major*
- A machine-readable form (OSCAL) where the org consumes one, or a stated deviation. *nit*
