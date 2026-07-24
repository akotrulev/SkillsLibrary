---
name: qa-security-shared
description: Cross-stack security-testing backbone — maps OWASP Top 10 (2025) and API Security Top 10 (2023) risks to this library's scanner gates and stack-native security skills, with severity/gating policy, the authorization-to-scan rule, ticketed-triage discipline, and SARIF consolidation. Load when planning security coverage or choosing which security skill applies; the `qa-security` agent drives it phase by phase. Triggers (as the planning layer, normally alongside a scanner sibling) "what security testing do we need", "map our coverage to OWASP", "which security skill applies here", "set the security gating policy", "triage these scanner findings". Do NOT load standalone to run a scan — pair it with the gate that does the work (`qa-security-testing-{sast,secrets-scanning,api-fuzzing,nuclei,tls-scanning,container-iac-scanning,zap-automation-framework}` or the stack's `security-testing/*`).
---

# QA — Security Testing (Shared / OWASP backbone)

Cross-stack concepts shared by every skill in the `security-testing` family. The tool siblings carry the
per-tool invocation, gating flags, and report parsing; **this skill carries the OWASP map, the
automatable-vs-manual boundary, the triage discipline, and the scan-authorization rules** that apply
regardless of tool or stack.

> **The one architectural fact that shapes this whole family.** Most security *scanners* are
> **language-agnostic binaries / Docker images** (ZAP, Nuclei, Trivy, Opengrep, Gitleaks, TruffleHog,
> Schemathesis, sslyze). Wrapping them does not gain anything from a three-language split — so they live as
> **single skills in `qa/_shared/security-testing/`**, invoked the same way from any pipeline. The work that
> *is* genuinely stack-bound is **functional access-control testing** (real tests in your API framework
> reusing your clients/DTOs/tokens) and **SCA / dependency-scanning** (different package managers per stack) —
> those keep per-stack siblings. Don't triplicate a `docker run`.

## The OWASP backbone (pin to these versions)

Security testing without a target standard is just "run some tools." Map every finding and every test to an
OWASP item so coverage is auditable.

### OWASP Top 10:2025 (web — latest; verify on owasp.org/Top10/2025)

| ID | Category | Note |
|----|----------|------|
| **A01:2025** | Broken Access Control | stays #1; **SSRF folded in here** |
| **A02:2025** | Security Misconfiguration | up from #5 |
| **A03:2025** | **Software Supply Chain Failures** | **NEW** — expands the old "Vulnerable & Outdated Components" |
| **A04:2025** | Cryptographic Failures | |
| **A05:2025** | Injection | |
| **A06:2025** | Insecure Design | |
| **A07:2025** | Authentication Failures | |
| **A08:2025** | Software or Data Integrity Failures | |
| **A09:2025** | Security Logging and Alerting Failures | |
| **A10:2025** | **Mishandling of Exceptional Conditions** | **NEW** |

(The 2021 edition is the prior stable; if a project pins to it, A06 = Vulnerable & Outdated Components, A10 =
SSRF — note the edition explicitly.)

### OWASP API Security Top 10:2023 (the API surface — current)

| ID | Category | Scanner-coverable? |
|----|----------|--------------------|
| **API1:2023** | Broken Object Level Authorization (BOLA / IDOR) | ❌ functional test |
| **API2:2023** | Broken Authentication | partial |
| **API3:2023** | Broken Object Property Level Authorization | ❌ functional test |
| **API4:2023** | Unrestricted Resource Consumption | partial (rate/limit tests) |
| **API5:2023** | Broken Function Level Authorization (BFLA) | ❌ functional test |
| **API6:2023** | Unrestricted Access to Sensitive Business Flows | ❌ business-logic / manual |
| **API7:2023** | Server Side Request Forgery | partial (DAST + design) |
| **API8:2023** | Security Misconfiguration | ✅ DAST / config |
| **API9:2023** | Improper Inventory Management | ✅ spec inventory |
| **API10:2023** | Unsafe Consumption of APIs | partial |

### WSTG v4.2 (the test-ID scheme) & ASVS 5.0 (the verification bar)

- **WSTG** test-IDs: `WSTG-<CAT>-<NN>` (e.g. `WSTG-ATHZ-01`). 12 categories: `INFO CONF IDNT ATHN ATHZ SESS
  INPV ERRH CRYP BLGC CLNT APIT`. Tag manual/exploratory security charters and access-control cases with the
  WSTG ID they cover.
- **ASVS 5.0.0** (May 2025) is the **verification checklist**: pick a target **level** — **L1** (baseline,
  mostly black-box), **L2** (default for apps handling sensitive data), **L3** (high-assurance / regulated) —
  and map each requirement to a test (automated where possible, manual where not), tracking pass/fail per
  requirement ID. ASVS requirements cross-map to WSTG test-IDs. Pin citations to the **5.0.0** numbering (the
  chapter structure changed from 4.0.3).

> **Naming:** ZAP **left OWASP** in 2023 (→ Software Security Project) and is now **"ZAP by Checkmarx"**
> (core devs joined Checkmarx, Sept 2024). It remains free/open-source (Apache 2.0). Refer to it as
> **"ZAP by Checkmarx (formerly OWASP ZAP)"** — it is no longer an OWASP project.

### OWASP Top 10 for LLM Applications:2025 — *if and only if the app has an LLM feature*

A chatbot / RAG answer / summarizer / tool-using agent has an attack surface the web/API Top 10 above does **not**
describe: prompt injection, system-prompt leakage, excessive agency, PII disclosure under attack. That surface is
the **OWASP Top 10 for LLM Applications:2025** (genai.owasp.org): LLM01 Prompt Injection · LLM02 Sensitive
Information Disclosure · LLM03 Supply Chain · LLM04 Data & Model Poisoning · LLM05 Improper Output Handling ·
LLM06 Excessive Agency · LLM07 System Prompt Leakage · LLM08 Vector & Embedding Weaknesses · LLM09 Misinformation
· LLM10 Unbounded Consumption.

> **This agent does not own model-behavior red-teaming — the `qa-llm-{stack}` agents do.** The scanner gates here
> are blind to model behavior exactly as they are blind to BOLA: a jailbreak is well-formed HTTP. **LLM red-
> teaming lives in `qa/<stack>/skills/llm-app-testing/references/red-teaming.md`** (promptfoo `redteam` with the
> `owasp:llm` preset, or DeepTeam), owned by the `qa-llm-{stack}` agents — generate adversarial variants and
> assert an attack-success **rate** per LLM-Top-10 item. The seam is two-way: a few LLM items still route back
> *here* — **LLM03** supply chain → this agent's `dependency-scanning` (SCA); **LLM05** improper output handling →
> SAST/DAST on the downstream sink; **LLM10** resource consumption → rate-limit tests. Run an LLM app's security
> as **both** agents in parallel; map each finding to its own framework (web/API Top 10 *and* LLM Top 10).

## What is automatable in CI vs what needs a human

This is the single most important judgement in security testing. **Scanners find syntax flaws; they are
blind to logic flaws.**

| Concern | OWASP | How to cover | In CI? |
|---------|-------|--------------|--------|
| Injection (SQLi/XSS/cmd/traversal) | A05 / API8 | DAST active scan, API fuzzing | ✅ (against a safe env) |
| Security misconfig, missing headers, cookie flags, info leaks | A02 / API8 | DAST passive baseline | ✅ every PR |
| Vulnerable/outdated components, transitive CVEs | A03 | **SCA** (dependency-scanning) | ✅ every PR |
| Hardcoded secrets / leaked credentials | A02 / A07 | secrets-scanning | ✅ every PR (+ pre-commit) |
| Insecure code patterns, taint flows | A05 / A06 | **SAST** | ✅ every PR |
| Container/base-image CVEs, IaC misconfig | A02 / A03 | container/IaC scanning | ✅ every build |
| TLS/crypto configuration | A04 | TLS scanning | ✅ scheduled / pre-release |
| **Broken access control: BOLA / IDOR / BFLA** | **A01 / API1 / API3 / API5** | **functional authz-matrix tests** | ✅ **but in your test suite, not a scanner** |
| Business-logic abuse, chained-authz, sensitive-flow abuse | A01 / API6 | **manual penetration testing** | ❌ human |
| **Model-behavior attacks: jailbreak, prompt injection, system-prompt/PII leakage, excessive agency** | **LLM01/02/06/07** | **LLM red-teaming** — `llm-app-testing` `red-teaming.md`, owned by `qa-llm-{stack}` | ✅ **but in the LLM eval suite (nightly), not this agent's scanners** |

> **⚠️ The scanner blind spot — own access control as a functional test.** A scanner authenticated as User A
> has no way to know that invoice `42` belongs to User B; the malicious request is *perfectly well-formed
> HTTP*. DAST tools find IDOR/BOLA only when hand-configured with multi-user accounts and cross-user object
> maps — which is exactly what a functional **access-control test matrix** already does, written in your
> normal API framework (multi-user × object-ID × endpoint → assert **403/404**), reusing the project's API
> clients, DTOs, and `auth0-test-tokens`. See `qa/<stack>/skills/security-testing/access-control-testing`.
> This is the highest-value security testing most teams are missing. Deep business-logic abuse still needs a
> manual pentest — say so; never imply a green pipeline means "secure."

## The layer map — run all of them; they don't overlap

| Layer | Skill | Reads | OWASP |
|-------|-------|-------|-------|
| **SAST** | `_shared/security-testing/sast` | your source | A05/A06 |
| **Secrets** | `_shared/security-testing/secrets-scanning` | source + git history | A02/A07 |
| **SCA** | `<stack>/skills/security-testing/dependency-scanning` | dependency tree | **A03** |
| **DAST (passive)** | `<stack>/skills/security-testing/zap-baseline` | running app, no payloads | A02/A08 |
| **DAST (active/API)** | `_shared/security-testing/zap-automation-framework` | running app, **payloads** | A05/API8 |
| **API fuzzing** | `_shared/security-testing/api-fuzzing` | running app + OpenAPI/GraphQL | A05/API4 |
| **Templates/CVE** | `_shared/security-testing/nuclei` | running app / hosts | A02/A05 |
| **Container/IaC** | `_shared/security-testing/container-iac-scanning` | images, fs, Terraform/K8s | A02/A03 |
| **TLS** | `_shared/security-testing/tls-scanning` | the TLS endpoint | A04 |
| **Access control** | `<stack>/skills/security-testing/access-control-testing` | your API, multi-user | **A01/API1/3/5** |

A clean run in one layer says **nothing** about the others. A passing ZAP baseline does not mean your
dependencies are clean; a clean SCA does not mean your access control works. Run the full set.

## Authorization to scan — the hard safety rule

> **Active/attack scans mutate state and must never run against production or a shared environment.** This is
> non-negotiable and applies to: ZAP **full/active** scan, Nuclei with intrusive templates, Schemathesis
> fuzzing, sqlmap, any payload-sending tool.

- **Passive** scans (ZAP baseline, SCA, SAST, secrets, TLS read-only) are **safe** — they observe, they don't
  attack. Right for every PR.
- **Active** scans go only against a **throwaway environment you own and are authorized to attack**
  (Testcontainers/compose-spun ephemeral env, or a dedicated security-test environment). Confirm authorization
  and target before the first active run — get it in writing for a hosted target.
- **sqlmap** is an interactive *exploitation* tool: runnable non-interactively with `--batch`, but it is **not
  a per-PR CI gate** — keep it as a scheduled/manual pentest step against a safe target. ZAP active + API
  fuzzing cover injection discovery in CI more safely.
- Never point a scanner at a third party's infrastructure without explicit authorization — that is an attack.

## The triage gate — ticketed suppressions, gate NEW findings

Every scanner's first run on a real app lights up. Gating on *every* finding mutes the gate; gating on
*nothing* is theatre. The discipline (identical across SAST, SCA, DAST, secrets, container):

1. **Baseline the current state once** — record existing findings as a ticketed allow-list (suppression
   file / `.gitleaks.toml` / `rules.tsv` / Trivy `.trivyignore` / Semgrep `.semgrepignore`).
2. **Gate NEW findings hard** — anything not in the baseline fails the build. Regressions can't sneak in.
3. **Every suppression carries a ticket + reason + (ideally) an expiry.** `// IGNORE rule-x — JIRA-1234,
   accepted risk, re-review 2026-Q4`. A suppression with no ticket is a silent hole.
4. **Shrink the allow-list over time.** Never grow it to make a red build green — that's how a real finding
   gets buried. Track allow-list size as a metric.

This is the same allow-list discipline the accessibility skills use for axe baselines — reuse the framing.

## Consolidate findings — SARIF → code scanning

Most modern tools emit **SARIF** (Static Analysis Results Interchange Format). Standardize on it:

- Have each tool write SARIF (`--sarif` / `-se` / `--format sarif`) **and** a human report (HTML/JSON).
- Upload SARIF to the platform's code-scanning surface (GitHub `github/codeql-action/upload-sarif`, GitLab
  security reports) so findings show **inline on the PR diff**, de-duplicate run-over-run, and track
  fixed/new state automatically.
- Attach the human report to **Allure** + as a CI artifact so a failing run names the findings without
  re-scanning. Cross-link `qa/reporting/<stack>/skills/allure-reporting`.

## The phased model (what the `qa-security` agent runs)

| # | Phase | Layers | When |
|---|-------|--------|------|
| 1 | **Threat model & OWASP scope** | pick Top-10/API-10 items + ASVS level in scope; confirm authorization & target env | before anything runs |
| 2 | **Static gates** (fast, every PR) | SAST · secrets · SCA | per-PR |
| 3 | **Functional access control** | the BOLA/IDOR/BFLA authz matrix in the API suite | per-PR (it's just tests) |
| 4 | **Dynamic gates** (safe env) | DAST passive baseline → active/AF · API fuzzing · TLS · nuclei | per-PR passive; active on a safe env |
| 5 | **Build-artifact gates** | container image · IaC | per-build / pre-release |
| 6 | **Review, gate & report** | triage, SARIF consolidation, CI wiring, ASVS coverage report | the gate |

Phases 2/3 are cheap and safe — run on every PR. Phase 4-active and Phase 5 need a safe target and may run on
a slower cadence. **A clean pipeline ≠ "secure"** — it means the *automatable* layers passed; business-logic
abuse still needs a manual pentest. State that in every report.

## Rules (hard constraints)

- **Map every finding/test to an OWASP item** (Top 10:2025 / API 10:2023) and tag access-control/manual cases
  with their **WSTG** ID; track ASVS-level coverage where the project sets a target level.
- **Never run an active/attack scan against prod or a shared env.** Active scans → a throwaway env you own and
  are authorized to attack. Passive scans are safe for every PR.
- **Own access control (BOLA/IDOR/BFLA) as a functional test matrix**, not a scanner — scanners are blind to
  it. Reserve **manual pentest** for business-logic abuse; never imply green = secure.
- **Triage with ticketed suppressions**: baseline existing findings, **gate NEW ones hard**, every suppression
  has a ticket + reason, shrink the list over time.
- **Standardize on SARIF** → code-scanning for inline PR findings; attach human reports to Allure + CI
  artifact.
- **No secrets in scan config** (auth tokens, API keys) — env vars read lazily, never committed.
- Run **all layers** — they cover orthogonal concerns; a clean run in one says nothing about the others.

## Cross-references

- `qa/_shared/security/SETUP.md` — **setup & prerequisites** (per-tool install, env vars, target requirements,
  how to invoke the agent vs a single skill, the pre-flight checklist). The *how* to this skill's *why*.
- `qa/_shared/security-testing/{zap-automation-framework,sast,secrets-scanning,container-iac-scanning,api-fuzzing,nuclei,tls-scanning}`
  — the language-agnostic scanner skills this reference frames.
- `qa/<stack>/skills/security-testing/access-control-testing` — the **stack-native** functional authz-matrix
  skill (the scanner blind spot; TS canonical).
- `qa/<stack>/skills/security-testing/{zap-baseline,dependency-scanning}` — the existing passive-DAST and SCA
  per-stack skills this family already shipped.
- `qa/_shared/agents/qa-security.md` — the phased orchestrator that loads this reference + the tool skills.
- `qa/<stack>/skills/auth0-test-tokens` — multi-user/role token acquisition the access-control matrix needs.
- `qa/cicd/<stack>/skills/ci-pipelines/*` + `qa/cicd/ci-conventions` — wire the gates and SARIF upload.
- `qa/reporting/<stack>/skills/allure-reporting` — attach the human reports.
- `qa/manual/{bug-report-writer,exploratory-charter-writer}` — write up a confirmed vuln / charter a manual
  security exploration for the layers CI can't reach.
