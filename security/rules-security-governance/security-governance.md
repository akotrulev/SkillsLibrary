---
paths:
  - "docs/security/**"
  - "detections/**"
  - "sigma/**"
  - "waf/**"
  - "crs/**"
---

<!-- security-governance rules v1 (2026-11-03): core. Installed by /security-governance:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Security governance artifact standards

Apply these to every security artifact you write, edit or review: detections, CSP / header / WAF policy, runbooks, compliance registers, posture reports, and the engagement reports other lanes file under `docs/security/`. The tag after a rule is the severity an audit reports: **blocker** leaks sensitive material or breaks a control, **major** makes the artifact wrong or unverifiable, **minor** is structure or style, **nit** is preference. A pentest or purple-team finding keeps its own CVSS or outcome-tier score; these tags judge the artifact, not the finding. Detection, hardening, runbook, compliance and posture rules are separate files that load with those files.

**The repo wins, and its version lane is what it pins.** Where this project consistently does something another way, follow it and do not flag it. Before writing, detect the editions the repo pins (ATT&CK, sigma-cli, the CRS line and WAF engine, OWASP Top 10, ASVS, PCI DSS, ISO 27001, SOC 2, NIST CSF) and stay valid under them. An older but supported pin (ATT&CK v19.0, CRS 4.25.x LTS, ASVS 4.0.3) is a deviation to note, not a finding. Current as of 2026-08-20, re-verify before citing: ATT&CK Enterprise v19.2 · sigma-cli 3.1.0 · CRS 4.29.0 · OWASP Top 10 2025 · ASVS 5.0.0 · PCI DSS 4.0.1 · ISO/IEC 27001:2022 · SOC 2 2017 TSC with the 2022 points of focus · NIST CSF 2.0 · OSCAL 1.2.x.

## Standards and pins

- Every standard is pinned, with one edition across the whole repo; the same standard pinned two ways in two files is a finding. *major*
- No withdrawn edition: ISO/IEC 27001:2013, PCI DSS 3.2.1 or 4.0, the `sigmac` converter, CRS 3.x, NIST SP 800-61r2's cycle presented as current. *major*
- OWASP ids use the 2025 numbering consistently: A02 Security Misconfiguration, A03 Software Supply Chain Failures, A05 Injection, A07 Authentication Failures, A09 Security Logging and Alerting Failures. *major*
- Under ATT&CK v19+ `Defense Evasion` is gone: Stealth keeps `TA0005`, Defense Impairment is `TA0112`. Never tag `attack.defense-evasion` under a v19 pin. *major*
- A version bump re-maps the tags and mappings it invalidates; a commit that only moves the pin is a finding. *major*
- The artifacts have one stated home (`detections/`, `docs/security/{posture,runbooks,hardening,compliance}/`), so a reader can tell adopted from absent. *minor*

## Redaction

- No credential, hash, token, private key or session material in any committed security artifact, test fixtures included. A finding states *that* a secret was recovered and its blast radius, never its value. *blocker*
- No real PII (names, emails, card numbers) in a finding, a log sample or an example. *blocker*
- Authorization is recorded redacted to scope, authorizer, window and lab or production; a scope file never carries a test account's password. *blocker*
- Screenshots and pasted terminal captures are redacted too; grep never sees them. *major*
- Internal host and IP inventories are scoped to what the finding needs, never dumped wholesale. *minor*
- Engagement artifacts live in a repo whose read access matches them, never a public or widely mirrored one. *major*

## Claims and evidence

- Evidence is an artifact you can open by path, read this session. A commit, a ticket, a CI badge or a green pipeline is a lead, never the evidence. *major*
- Say what was proven: authored is not validated, mapped is not effective, a policy that parses is not a policy that blocks. *major*
- No placeholder ("TBD", "various", "assess as appropriate"). An unknown is `[TBD - <who decides, by when>]` with an open-questions entry. *major*
- Ids are permanent and rounds additive: never renumber an id, never overwrite an earlier round. *major*

## Comments

- No commented-out rules or directives shipped (`# SecRule …`, a disabled `detection:` block). *nit*
- No inline comments inside a rule's or a policy's body restating it; Sigma's `description`, `falsepositives` and `references` fields carry the prose. A `sigma convert` separator or a linter directive is not a comment. *minor*
- A comment that survives is true and load-bearing; a stale one is the defect, and deleting it is the fix. *major*
- No secret-shaped placeholder that reads as real (`password: CHANGEME_prod_2026`). *minor*
