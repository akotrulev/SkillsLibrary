---
paths:
  - "docs/security/posture/**"
---

<!-- security-governance rules v1 (2026-11-03): posture reports. Installed by /security-governance:rules; edit to fit this project. -->

# Security posture report standards

Severity tags as in the core security-governance rules. The repo wins where it consistently does otherwise.

- Named `docs/security/posture/<NNN>-security-posture-r<N>.md`. *minor*
- `<NNN>` is minted once per system and reused every round. *major*
- A round is added, never rewritten; `RISK-nnn` ids are permanent. *major*
- Every register item carries its ATT&CK id, risk band, NIST CSF 2.0 function and owning lane. *major*
- `Resolved` cites lane evidence re-read that round. *major*
- A lane that never ran is a reported, routed gap, never treated as clean. *major*
- One weakness found by two lanes is one item with two evidences. *minor*
- The mapping from CVSS and blocker/major/minor/nit onto the risk band is stated; a proven path outranks a detected one, and scores are never averaged. *major*
- Posture is organized by the CSF 2.0 functions, Govern included. *minor*
- The executive summary is plain language: no tool names, ATT&CK ids or CVSS vectors. *minor*
