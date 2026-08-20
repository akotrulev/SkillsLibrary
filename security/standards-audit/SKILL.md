---
name: secgov-standards-audit
description: Use to audit a repo's defensive-security artifacts against the security-governance plugin's conventions — Sigma detections, CSP/headers/WAF policy, secret-store wiring and rotation runbooks, the compliance evidence register — as a saved, re-runnable findings report in `docs/audits/`. Read-only; never fixes. Triggers "audit our detections against the conventions", "conformance audit of our security hardening". Do NOT use to run a scan or exploit, or to audit application code.
---

# security-governance Conformance Audit

Audit an existing repo's **defensive-security artifacts** against the conventions this plugin defines — the hard rules each `secgov-*` skill owns, plus the artifact contract the `security-architect` agent holds itself to — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis.** The audit points; `security-architect` fixes.

**Announce at start:** "I'm using the `secgov-standards-audit` skill in Mode A (baseline) / Mode B (re-audit) on `<repo/path>`."

## Read before sweeping

1. **[`ep-standards-audit-engine`](../../engineering-practices/standards-audit-engine/SKILL.md)** — the engine: Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping/coverage policy, the 5 phases, the hostile self-review. **Read it first.**
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — the 14 lettered sections (A–N), 127 checks, the **absence rule**, and the pinned-standards table. **Read end-to-end** before Phase 2.
3. `engineering-practices/standards-audit-engine/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Phase 3.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree on a *rule*, **the skill wins** — and report the disagreement. The one exception, stated in the checklist's version-lane block: where a skill cites a **standard version or identifier that the pinned table contradicts**, the table wins and the skill text becomes an open question for the maintainer.

Report path: `docs/audits/<NNN>-security-governance-conformance-r<N>.md`.

## What this audits — and the absence rule

The object is the **governance artifact**: a Sigma rule and its test fixtures, a CSP string and the header set around it, a WAF ruleset and its exclusions, a secret-store wiring and a rotation runbook, an evidence register, a posture report. Not the application, not the infrastructure, not the vulnerabilities in either.

**A control the repo has never adopted produces no finding.** No detection repo, no CSP, no WAF, no runbook, no compliance scope → the section is **N/A**, and the absence goes in the applicability matrix as a **coverage note routed to `security-architect`**. Conformance audits an artifact against the rules it must follow; *whether a control should exist at all* is a posture question, and posture is the architect's lane. The one edge: **partial adoption of a defined baseline is a finding** — a header block with HSTS and `nosniff` but no CSP violates the plugin's "full baseline" rule, because the artifact exists and is incomplete.

## The fence — what this is not

| Job | Owner |
|---|---|
| Reviewing one diff, inline, no artifact | the stack plugin's own `code-review` skill — this plugin has no per-diff sibling, because a policy or a detection is reviewed as a whole artifact, not as a hunk |
| Code vs a written spec / stories / ACs | `ep-spec-vs-code-audit` (or the `code-auditor` agent) |
| "How does feature X actually work / where is it defective" | `ep-feature-audit` |
| **Detecting** a vulnerability or a committed secret | **peer** `qa-security` (SAST/DAST/SCA/`secrets-scan`) — section H audits the *hardening*, it is not a scanner |
| **Proving** a weakness is exploitable, or running a kill chain | **peer** `penetration-tester` — the offensive lane produces proof, not conformance findings |
| **Proving** an authored detection actually fires | **peer** `purple-team-engineer` — section D9 reports *authored vs validated*; it never validates |
| Delivery infrastructure conformance (image, IaC, pipeline, identity) | **peer** `devops-auditor` — its section G owns the static-credential invariant at infra altitude |
| Application-code conformance | **peer** `be-*` / `fe-*` standards audits |
| Deciding **whether** a control should exist, and the risk it carries | **peer** `security-architect` — posture, not conformance |
| Applying any fix found here | `security-architect` (see Handoffs) |

**Why the `penetration-testing` plugin has no audit of its own.** Its outputs are per-engagement reports and scope files — point-in-time records, not standing artifacts that drift. Its rules are enforced as **blocking pre-conditions** by the §5 safety gates and the mandatory `pentest-reporting` sections, so a post-hoc sweep finds only what the gates already refused to allow, and mostly finds it too late to fix. The one residual the gates cannot cover — sensitive material that reached a **committed** file — is **section M** of this checklist, which sweeps `docs/security/**` and `detections/**` whoever authored them. Only the redaction rule crosses that boundary; the offensive findings themselves are never re-verdicted here.

## Phase 0 — the standards & tooling pin lane *(never skip)*

```bash
ls -d detections rules sigma waf crs docs/security 2>/dev/null
ls -d docs/security/{posture,runbooks,hardening,compliance} 2>/dev/null
rg -ni "attack.?version|ATT&CK v1[89]|enterprise-attack-1[89]" detections rules docs/security 2>/dev/null
rg -ni "sigma-cli|sigmac\b|pysigma" -g '!*.lock' .
rg -ni "coreruleset|owasp.?crs|modsecurity|coraza" -g '*.conf' -g '*.yml' -g '*.yaml' -g 'Dockerfile*'
rg -n "27001:20(13|22)|PCI DSS 4\.0|ASVS|SOC 2|CSF" docs/security 2>/dev/null
rg -n "Content-Security-Policy|Strict-Transport-Security"
git log --oneline -10 -- detections docs/security 2>/dev/null
```

Record: **ATT&CK pin** · **Sigma tooling version** (and whether `sigmac` survives) · **SIEM backend(s)** and the conversion pipeline · **CRS version + engine** (Coraza / ModSecurity / CrowdSec) and paranoia level · **where headers are emitted** (app / proxy / CDN) · **secret store** · **compliance frameworks in scope** and their editions · **which lanes have reported into `docs/security/`**.

**The version rule binds every finding, and it inverts here.** There is no TFM — the lane is the set of standards the repo *pins*. Pinned-and-current conforms; pinned to an older-but-supported edition (ATT&CK v19.0, CRS **4.25.x LTS**, ASVS 4.0.3) is a **deviation**, not a finding, unless something in the repo is invalid under that pin; a **withdrawn** edition (ISO 27001:**2013**, PCI **3.2.1**/**4.0**, `sigmac`, CRS 3.x) or an **unpinned/silently-mixed** one is a finding. The checklist's version-lane table carries the verified-current values and the date they were checked — **re-verify before citing**, these move faster than any language runtime.

Then read 2–3 representative artifacts (one Sigma rule with its fixtures, the header/CSP config, one runbook) to calibrate what "normal here" looks like.

## Phase 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| B, C, D (detections) | A detection repo exists | `ls -d detections rules sigma 2>/dev/null` |
| E (CSP) | A CSP is emitted anywhere | `rg -l "Content-Security-Policy"` |
| F (headers) | The repo emits response headers it controls | `rg -l "Strict-Transport-Security\|X-Content-Type-Options\|add_header\|Headers.Add"` |
| G (WAF) | A WAF config exists | `rg -l "SecRule\|coreruleset\|coraza"` |
| I (rotation) | A runbook exists **or** static long-lived credentials are in use | `ls docs/security/runbooks 2>/dev/null`; the H6/H7 recipes |
| J, K (compliance) | A compliance scope is stated or a register exists | `ls docs/security/compliance 2>/dev/null` |
| L (posture) | A posture report exists | `ls docs/security/posture 2>/dev/null` |
| M (redaction) | Anything exists under `docs/security/` or `detections/` | `ls -d docs/security detections 2>/dev/null` |

A and H apply to every repo — A is the gate, and every repo has a config surface. N applies whenever any of B–M does. **A section marked N/A names the probe that decided it**, and its absence is recorded as a coverage note per the absence rule, never as a finding.

## Handoffs

- **Apply the fixes** → the **`security-architect`** agent. The artifacts this audit sweeps are exactly the ones inside its write fence (`docs/security/**`, `detections/**`), so a nonconforming rule, policy, runbook, or register is fixed there — loading the owning `secgov-*` skill for the rule. The priority table is the handoff artifact.
- **App / infra wiring** (per-request nonce emission, framework middleware, ESO manifests, edge WAF deploy, the pre-commit hook and CI secret gate) → `fe-*` / `be-*` / `devops-engineer`. This audit reports the policy defect; they wire the fix.
- **A `logsource` the stack never ships (D2)** → `observability-engineer-*` own the telemetry substrate. A rule with no data behind it is a telemetry gap, not a rule gap.
- **"Authored but never validated" (D9)** → `purple-team-engineer` runs the validation. That is a missing proof, not a defect to fix.
- **A vulnerability or committed secret found while reading (H2, H7)** → report it here at its severity **and** name `qa-security` for the scan lane and `secgov-secrets-hardening` for the rotation. Do not start rotating.
- **Whether a control should exist at all, and what risk its absence carries** → `security-architect`'s posture picture. That is the coverage note, not a finding.
- **The maintainer, not the audited repo** → any place a `secgov-*` skill's own cited standard version conflicts with the checklist's verified table. An open question, never a finding against the user's code.
