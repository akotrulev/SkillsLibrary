# Mapping each finding to its spines

**Two spines, per finding.** Control gaps map to **OWASP Top 10:2025** — **A02 Security Misconfiguration**
(families 2, 4), **A04 Insecure Design** (a control with no rotation or no enforcement path was designed
inert), **A09 Logging & Alerting Failures** (family 3), **A03 Software Supply Chain Failures** (family 4
pinning), **A07 Identification & Authentication Failures** (a static cloud key). Where a control's absence is
the *mitigation* for a technique, name the **MITRE ATT&CK** id too — Cloud/Containers matrices, not
Enterprise: `T1552.001/.007` Unsecured Credentials in files and cloud config (family 1), `T1557` /
`T1040` adversary-in-the-middle and sniffing (family 2), `T1562.008` Impair Defenses — Disable Cloud Logs
(family 3), `T1195.002` Compromise Software Supply Chain and `T1078.004` Valid Accounts — Cloud (family 4).
CIS Benchmarks supply the numbered row where one exists; cite it rather than re-deriving the rule.
