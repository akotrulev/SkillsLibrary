---
name: compliance-evidence-mapping
description: Use to map the library's security controls and tests (scanners, gates, ASVS, ATT&CK coverage, hardening, detections) to compliance-framework evidence — SOC 2, PCI DSS 4.0.1, GDPR, ISO 27001:2022 — as an evidence register plus a gap list. Triggers "map our controls to SOC 2 / PCI / ISO", "compliance gap analysis". Not for running the controls (the scan/test lanes), authoring them (`hardening`/`detection-engineering`), or certifying compliance (a human auditor/QSA).
---

# Security Governance — Compliance Evidence Mapping (SOC 2 · PCI DSS · GDPR · ISO 27001 · ASVS)

The library already *runs* the controls a compliance auditor asks about — SAST/DAST/SCA gates, secrets scanning, functional-authz matrices, TLS scans, security headers, secret rotation, detections, infra benchmarks. What it lacks is the **crosswalk**: which of those controls and tests constitutes **evidence** for **SOC 2 CC6.1** or **PCI DSS 6.4.3** or **ISO 27001:2022 A.8.8**, where that evidence lives, and — the part that matters most — **which framework requirements have no control behind them yet.** This skill produces that mapping: an **evidence register** (control → framework requirement → evidence artifact → status) and a **gap list**.

This skill is **language-agnostic** (it maps controls to standards; it runs nothing) and homes in the **`security-governance`** plugin, loaded by the **`security-architect`** agent as the compliance layer of the posture picture. It **maps and identifies gaps**; it does **not** certify. Certification is a human auditor's / QSA's / lead-implementer's act — this skill produces the evidence pack they assess and the gap list the org closes.

> **The load-bearing rule: this maps evidence, it does not attest to it.** A control being *mapped* to a requirement is not the control being *effective*. Evidence status is tiered — **`#present`** (the control exists and its output is an artifact you can point to), **`#partial`** (exists but incomplete/untested), **`#gap`** (no control) — and effectiveness is `devops:controls-validation`'s / the test lanes' job, not this skill's. Never mark a requirement "met" from the existence of a config file; mark it `#present` with the artifact, and let validation prove it works.

## The frameworks — pinned to current versions (2026-08)

| Framework | Current version | Shape you map to |
|---|---|---|
| **SOC 2** | AICPA **2017 Trust Services Criteria, with Revised Points of Focus — 2022** | 5 categories (Security/Availability/Processing-Integrity/Confidentiality/Privacy); Security (Common Criteria **CC1–CC9**) is mandatory. Map to the **criterion** + point of focus. |
| **PCI DSS** | **v4.0.1** (every requirement mandatory since 2025-03-31; assessed in full for 2026) | 12 requirements, 400+ sub-requirements. Watch **6.4.3** (payment-page script inventory + integrity) and **11.6.1** (payment-page header/script-tamper monitoring) — the two most under-prepared. |
| **ISO/IEC 27001** | **:2022** (only valid edition — 2013→2022 transition ended 2025-10-31) | **93 Annex A controls** in 4 themes (Organizational A.5 / People A.6 / Physical A.7 / Technological A.8). Map to the Annex A control id. |
| **GDPR** | Regulation (EU) 2016/679 (the procedural Regulation entered force 2026-01-01; EDPB 2026 enforcement focus on transparency) | Principles + articles — esp. **Art. 32** (security of processing), **Art. 25** (data protection by design/default), **Art. 33/34** (breach notification), **Art. 30** (records of processing). Map technical controls to Art. 32/25. |

**ASVS is the connective tissue, not a fifth framework here.** The **OWASP ASVS 5.0.0** (2025-05-30; ~350 requirements, 17 chapters, levels **L1/L2/L3**) is the application-security *verification* standard the library's test lanes already implicitly target. This skill's job includes stating **which ASVS level the app is verified at** and mapping ASVS chapters (V6 auth, V13 config, V14 data protection, …) *onto* the compliance frameworks — ASVS is the bridge between "we tested X" and "that satisfies PCI/SOC2/ISO control Y."

## The mapping backbone — do not hand-roll the crosswalk

The N-frameworks-to-N-controls crosswalk is an O(N²) problem solved once, publicly — reuse it:

- **Secure Controls Framework (SCF)** — a free metaframework: **1,400+ controls pre-mapped to 200+ laws/regulations/frameworks** (SOC 2, PCI, ISO 27001, GDPR, NIST CSF, HIPAA, …). Use its crosswalk tabs as the authority for "SCF control X ↔ PCI 6.x ↔ ISO A.8.y ↔ SOC 2 CCz" rather than inventing the mapping — an invented crosswalk is a silent compliance error.
- **OSCAL** (NIST; **v1.2.1 Mapping Model**, March 2026) — the machine-readable form: express the mappings as computable OSCAL so gap analysis, evidence reuse, and change-impact (when a source control evolves) are automatable rather than a spreadsheet. FedRAMP mandates OSCAL for new packages by 2026-09-30, so machine-readable is the direction of travel. Produce the register in narrative Markdown for humans **and** OSCAL where the org consumes it.
- **NIST CSF 2.0** (Feb 2024; the **Govern** function added — 6 functions, 106 subcategories) is the governance spine `security-architect` frames the whole posture in; map the technical controls up to CSF subcategories for the CISO view.

## The evidence register — the deliverable

One row per (control → requirement), the control mapped once and fanned out to every framework via the SCF crosswalk:

| Control (library) | Evidence artifact | ASVS | SOC 2 | PCI 4.0.1 | ISO 27001:2022 | GDPR | Status |
|---|---|---|---|---|---|---|---|
| SAST gate (`qa-<stack>:code-scan`) | CI SARIF + gate config | V1/V5 | CC7.1, CC8.1 | 6.2.4, 6.3.1 | A.8.28, A.8.25 | Art.32 | `#present` |
| Secret rotation runbook (`security-governance:secrets-hardening`) | runbook + rotation logs | V6 | CC6.1 | 8.3.9, 3.x | A.5.17, A.8.24 | Art.32 | `#partial` (emergency path untested) |
| Strict CSP + headers (`security-governance:hardening`) | policy + `client-side-security` block-proof | V13/V14 | CC6.6 | 6.4.3, 11.6.1 | A.8.26 | Art.25, Art.32 | `#present` |
| Detection coverage (`security-governance:detection-engineering`) | ATT&CK coverage map + validation | — | CC7.2, CC7.3 | 10.x, 11.5.x | A.8.15, A.8.16 | Art.33 | `#gap` (authored, not validated) |
| Cross-tenant isolation (`qa-security` BOLA/IDOR) | permission-matrix test results | V4/V8 | CC6.1, CC6.3 | 7.x | A.5.15, A.8.3 | Art.25, Art.32 | `#present` |

Every row carries the **evidence artifact path** (the SARIF, the test report, the runbook, the policy — the thing an auditor points at), the **status tier**, and — for `#partial`/`#gap` — the **owning lane** to close it (`security-hardening` to author, `infra-controls-validation` to prove effective, a test lane to run). The register's most valuable output is the **gap list**: requirements with `#gap` status, prioritized, each routed to the lane that closes it.

## How to build it

1. **Scope** — which frameworks are in play (a fintech taking cards → PCI mandatory; an EU-data SaaS → GDPR + SOC 2; ISO for enterprise sales). Do not map to a framework the org is not pursuing — noise.
2. **Inventory the controls that already run** — read the repo for the gates/tests/hardening/detections that exist and their output artifacts (this is where `engineering-practices/agent-orientation-cache`'s seam inventory + the other lanes' reports feed in). Evidence status is read from the artifact, this session — a green pipeline is a lead, the SARIF is the evidence.
3. **Map via the SCF crosswalk** — control → requirement across every in-scope framework; state the ASVS level the app is verified at.
4. **Tier the evidence** `#present`/`#partial`/`#gap` from the artifact, not the intent.
5. **Emit the register** (Markdown for humans; OSCAL where consumed) + the prioritized **gap list**, each gap routed to its closing lane.
6. **Hand to `security-architect`** — the register + gaps are a layer of the posture picture; the CISO view frames it in NIST CSF 2.0.

## Anti-patterns

- **Inventing the crosswalk.** Hand-mapping "PCI 6.x ↔ ISO A.8.y" without the SCF authority produces silent, confident compliance errors. *Fix:* use the SCF (or OSCAL-published) mapping as the authority.
- **Marking a requirement "met" from a config file's existence.** Mapped ≠ effective. *Fix:* tier `#present` with the artifact; effectiveness is `infra-controls-validation`'s / the test lane's proof.
- **Mapping to a framework the org isn't pursuing.** A GDPR column for a US-only, no-EU-data product is noise that dilutes the real gaps. *Fix:* scope to the frameworks in play.
- **Mapping to a stale framework version.** ISO 27001:2013 (114 controls) is invalid; PCI 3.2.1 is retired; SOC 2 without the 2022 revised points of focus. *Fix:* pin the current versions in the table above.
- **Certifying.** This skill produces the evidence pack; it is not an attestation. *Fix:* a human auditor/QSA/lead-implementer certifies — state that the output is *evidence for* their assessment, not a pass.
- **A register with no artifact paths.** "We have SAST" is a claim; the SARIF at `path:line` is evidence. *Fix:* every row points at the artifact an auditor can open.
- **Treating ASVS as a compliance framework to certify against.** ASVS is a verification standard and the bridge; the certifiable frameworks are SOC 2/PCI/ISO. *Fix:* use ASVS to say *what was verified and at which level*, then map that onto the certifiable requirement.

## Hard rules

- **Map, don't certify** — the output is an evidence pack + gap list for a human auditor; it is never a compliance attestation.
- **Evidence is tiered from the artifact** `#present`/`#partial`/`#gap`, read this session — mapped ≠ effective; a green pipeline is a lead, the artifact is evidence.
- **Use the SCF/OSCAL crosswalk as the authority** — never hand-invent a framework-to-framework mapping.
- **Pin current framework versions** — SOC 2 (2017 TSC + 2022 points of focus) · PCI **4.0.1** · ISO **27001:2022** (93 controls) · GDPR (2016/679) · ASVS **5.0** (as the bridge, with the verified level stated).
- **Scope to the frameworks in play** — no speculative columns.
- **Every row names the evidence artifact and, for gaps, the closing lane** — the gap list is the point; each gap is routed, not just recorded.
- **Emit human (Markdown) + machine (OSCAL where consumed)** — machine-readable mapping is the direction of travel (FedRAMP OSCAL mandate 2026-09-30).

## Cross-references

- **`security-architect`** (`security/agents/security-architect.md`) — the roll-up agent that loads this skill; the evidence register + gap list are a layer of its CISO posture picture, framed in NIST CSF 2.0.
- **`devops:controls-validation`** (`devops/infra-controls-validation/`) — proves a mapped control is **effective**, not just present; it converts a `#present` row into a validated one and a `#partial` into a `#gap` when the control fails its test.
- **`qa-security`** (`qa/_shared/agents/qa-security.md`) + its scanners — the app-layer controls (SAST/DAST/SCA/secrets/authz/TLS) that populate most register rows; their reports are the evidence artifacts.
- **`infra-security-tester`** (`devops/agents/infra-security-tester.md`) — the infra/cloud/K8s controls (CIS benchmarks, CSPM, RBAC/network-policy) that populate the infra rows.
- **`security-governance:hardening`** / **`security-governance:secrets-hardening`** / **`security-governance:detection-engineering`** — the defensive controls whose *existence* this skill maps to evidence and whose *absence* becomes a gap routed back to them.
- **`business-analysis:knowledge-base`** *(named, not loaded)* — where data-processing/PII facts about the system live; GDPR Art.30 records-of-processing evidence draws on the business model.
