---
paths:
  - "detections/**"
  - "sigma/**"
---

<!-- security-governance rules v1 (2026-11-03): detections. Installed by /security-governance:rules; edit to fit this project. -->

# Detection-as-code standards (Sigma, alert-as-code)

Severity tags as in the core security-governance rules: **blocker**, **major**, **minor**, **nit**. The repo wins where it consistently does otherwise.

## The rule file

- One rule per file, and the filename matches the `title`. *minor*
- `id` is a UUID, unique across the ruleset, never regenerated on edit. A duplicate is a *blocker*; a missing or changed one is *major*.
- `tags` carry at least one well-formed ATT&CK technique (`attack.t1021.001`) that resolves under the pinned version. *major*
- `logsource` names the product and a service or category. It is the telemetry contract: a rule over a log the stack never ships is a documented gap, not coverage. *major*
- `falsepositives` names a specific benign case; `Unknown` is not a tuning contract. *major*
- `references` names the hypothesis behind the rule: a threat-model entry, a pentest finding, an incident. *minor*
- `title` and `description` say what is detected and why it matters; `level` is honest, not every rule critical. *minor*
- `status` earns its way from experimental through test to stable. *minor*
- Rates, sequences and joins are Sigma Correlations that reference existing base rules by `id`, never a hand-written SPL or KQL blob. Logic a backend cannot compile is documented, not dropped. *major*

## Tests, pipeline and tuning

- Every rule has a true-event sample it fires on and a benign sample it stays quiet on, in `tests/` beside it, and CI runs them as a merge gate. *major*
- CI lints with `sigma check` and converts with `sigma convert -t <backend> -p <pipeline>`; the field-mapping pipeline is never omitted, and no hand-maintained query sits beside the YAML. *major*
- Detections are code: a rule clicked into a SIEM console, or a non-Sigma analytic missing from the repo, is a finding; rollback is a reverted commit. *major*
- The SigmaHQ community ruleset is a baseline to select from and tune, never imported whole. *major*
- Tune in the rule (an exclusion, a refined selection), never by muting the alert channel. *major*
