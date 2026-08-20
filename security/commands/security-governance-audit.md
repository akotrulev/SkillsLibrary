---
description: Audit this repo's defensive-security artifacts against the security-governance plugin conventions — read-only, saves a findings report to docs/audits/
argument-hint: [optional: path or sections to limit the sweep to]
---

Run a **security-governance conformance audit** on this repository: sweep the defensive-security artifacts — Sigma detections, CSP/headers/WAF policy, secret-store wiring and rotation runbooks, the compliance evidence register, the posture reports — against the conventions this plugin defines, and save a findings report.

1. `Read` the engine at `${CLAUDE_PLUGIN_ROOT}/engineering-practices/standards-audit-engine/SKILL.md` (fall back to `engineering-practices/standards-audit-engine/SKILL.md` inside the SkillsLibrary repo) — it owns Mode A/B, the artifact contract, evidence rules, severity, and the report templates.
2. `Read` the stack skill at `${CLAUDE_PLUGIN_ROOT}/security/standards-audit/SKILL.md` (fall back to `security/standards-audit/SKILL.md`), then its `references/conformance-checklist.md` **end-to-end**.
3. Follow them exactly — the standards-pin gate, the applicability matrix, the section-by-section sweep (A–N), the evidence rules, the report template, and the hostile self-review all apply.
4. Check `docs/audits/` first: a prior `…-security-governance-conformance-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.
5. Load the owning `security/<skill>/SKILL.md` whenever a check is ambiguous, version-keyed, or you are about to write its fix direction.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and nothing else — never fix, rotate, reformat, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning skill; `security-architect` applies them in a separate run.

**This audits artifacts, not the system.** Sigma rules, policy, runbooks, registers, posture reports — not the application, not the infrastructure, and not the vulnerabilities in either. Running a scan or an exploit is another lane's job (`qa-security`, `infra-security-tester`, `penetration-tester`), and this command never invokes one.

**Absence is a coverage note, not a finding.** A control the repo has never adopted — no detection repo, no CSP, no WAF, no runbook, no compliance scope — makes its section **N/A**, recorded in the applicability matrix with the probe that decided it and routed to `security-architect` as a posture question. Only *partial* adoption of a defined baseline is a finding.

**Evidence is static-first.** Read files, cite `file:line`, tag `#confirmed` / `#inferred`, and name the search behind every negative claim. Only run `sigma check` / `sigma convert`, a YAML parse, or a live SIEM/endpoint query if the user explicitly opts in for this audit — and let execution corroborate a read, never replace it.

**Pin gate first.** Detect what the repo pins — ATT&CK version, Sigma tooling, CRS line and WAF engine, OWASP Top 10 edition, ASVS/PCI/ISO/SOC 2 editions — before judging anything. An older-but-supported pin is a **deviation**; a withdrawn edition or an unpinned/silently-mixed one is a **finding**. Re-verify the checklist's current-version table against the sources before citing it; those versions move fast.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, audit the whole repository: detect the pin lane, build the applicability matrix, and sweep every applicable section A–N.

When done, report the engine's output contract (detected lane · applicability · coverage · report path · finding counts by severity · highest-leverage item) and the path to the saved report.
