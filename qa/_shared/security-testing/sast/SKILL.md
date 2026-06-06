---
name: qa-security-testing-sast
description: >-
  SAST (Static Application Security Testing) — scan **YOUR source code** for insecure code patterns and
  taint flows as a CI gate, language-agnostic (the tool/invocation is identical regardless of test stack;
  the rulesets target the **language of the codebase being scanned**, not the test framework). Lead with
  **Opengrep** (the LGPL-2.1 Semgrep fork — truly-OSS SAST default for 2025/2026; CLI is
  invocation-compatible with `semgrep`) running the OWASP/security registry packs, gating on
  `--error`/`semgrep ci`, with diff-aware `--baseline-commit` scanning, `.semgrepignore`/`nosemgrep`
  ticketed triage, brief YAML custom rules, and SARIF → code-scanning + Allure reporting. Use when a
  pipeline must catch source-pattern flaws (injection sinks, hardcoded crypto, unsafe deserialization,
  SSRF/insecure-design patterns) on every PR. Do NOT use for: scanning the **dependency tree** for known
  CVEs (see qa-security-testing-dependency-scanning-{java,dotnet,typescript} — SCA reads your build graph,
  not your source), probing a **running app** over HTTP (see qa-security-testing-zap-automation-framework —
  DAST; SAST never runs the app), finding **leaked credentials** in source/git history (see
  qa-security-testing-secrets-scanning), or the OWASP map / triage discipline / scan-authorization rules
  themselves (see qa-security-shared — load it alongside this skill).
---

# Security Testing — SAST (Static Application Security Testing, shared)

**SAST** answers: **"does my own source code contain insecure patterns?"** It parses your code into an AST
(and, with inter-procedural/taint analysis, follows data from untrusted *source* to dangerous *sink*),
matches it against a security ruleset for **the language the code is written in**, and **fails the build**
on a match. It needs **no running app** (contrast DAST) and **no dependency feed** (contrast SCA): it reads
the source tree directly, fast, every PR. This is a **single `qa/_shared/` skill** because the tool and its
invocation are identical from any test stack — a Java, .NET, or TypeScript test suite all shell out to the
same binary; only the `--config` ruleset changes to match the scanned codebase's language.

> **Load `qa-security-shared` alongside this skill.** The OWASP Top-10 map, the
> automatable-vs-manual boundary, the **ticketed-suppression triage discipline**, and the SARIF →
> code-scanning consolidation live there — this skill references them rather than duplicating, and carries
> only the SAST-specific tool, invocation, gating flags, and rules.

## ⚠️ The OSS situation: Semgrep → Opengrep (read this before choosing a tool)

The de-facto OSS SAST engine for a decade was **Semgrep**. In **December 2024**, Semgrep's license changed:
the **Community/Registry rules** and several **engine features** (cross-file / inter-procedural **taint
analysis**, finding **fingerprinting**, and others) moved behind the **commercial license**, clamping what
the OSS Community Edition can do. A consortium (Aikido, Arnica, Endor Labs, Jit, Kodem, Mobb, and others)
responded by launching **Opengrep in February 2025** — an **LGPL-2.1 fork** of the last open engine that
**restores taint / inter-procedural analysis, fingerprinting, and Windows support**, keeps the
**Semgrep-compatible JSON + SARIF** output, and keeps the rule syntax. Its CLI is **invocation-compatible**
with `semgrep` (same `scan`/`--config`/`--sarif`/`--error` surface), so everything in this skill runs under
either binary — substitute `opengrep` for `semgrep` in the commands.

> **Recommendation (2025/2026): Opengrep is the truly-OSS SAST default.** Use it when you want a real
> open-source gate with taint analysis and no per-finding licensing trajectory. **Semgrep proper** is now an
> **AppSec-platform play** (the hosted Semgrep AppSec Platform, `semgrep ci` with org policies + cross-file
> analysis) — reach for it only when the org has bought into that platform. Pin your CI to whichever you
> choose and **track the OSS license trajectory** as a known risk (the anti-patterns call this out).

## Decision matrix — SAST vs SCA vs DAST vs secrets

| Need | Use | Reads | OWASP |
|------|-----|-------|-------|
| Catch **insecure code patterns / taint flows in your source** (injection sinks, unsafe deser, hardcoded crypto) | **this skill (SAST)** | your **source code** | A05/A06/A02 |
| Catch **known CVEs in your dependency tree** (direct + transitive) | dependency-scanning-{java,dotnet,typescript} (SCA) | your **build graph / lockfile** | A03 |
| Probe the **running app's HTTP surface** (headers, injection over the wire, info leaks) | zap-automation-framework / zap-baseline (DAST) | the **running app** | A02/A05/API8 |
| Find **leaked secrets / credentials** in source + git history | secrets-scanning | source + **git history** | A02/A07 |
| Verify **access control** (BOLA/IDOR/BFLA) | access-control-testing (functional) | your API, multi-user | A01/API1/3/5 |

**Rule of thumb:** SAST reads **your source** for *how you wrote it*; SCA reads your **dependency tree** for
*what you pulled in*; DAST reads the **running app** for *how it behaves over HTTP*. They are orthogonal —
a clean SAST run says nothing about a Log4Shell in a transitive dep or a missing CSP header at runtime.
**Run all four layers** (see `qa-security-shared` § the layer map).

## Setup — CLI or Docker, and the opengrep-vs-semgrep choice

```bash
# --- Opengrep (the OSS default) ---
# Install script (Linux/macOS):
curl -fsSL https://raw.githubusercontent.com/opengrep/opengrep/main/install.sh | bash
opengrep --version

# Or pinned in a container (CI):
docker run --rm -v "${PWD}:/src" ghcr.io/opengrep/opengrep:latest \
  opengrep scan --config p/owasp-top-ten --error --sarif -o /src/results.sarif /src

# --- Semgrep (platform play — same CLI surface) ---
pipx install semgrep            # or: brew install semgrep
docker run --rm -v "${PWD}:/src" semgrep/semgrep semgrep scan --config p/owasp-top-ten /src
```

- **Pick the binary deliberately** (see the OSS-situation callout): `opengrep` for a truly-OSS gate with
  taint analysis; `semgrep` only when the org runs the Semgrep AppSec Platform. Every command below is
  written with `semgrep` for familiarity — **`opengrep` is a drop-in substitute** (same flags, exit codes,
  JSON/SARIF).
- **Pin the version** (image tag or installed version) in CI — ruleset/engine behaviour changes between
  releases; an unpinned scanner makes the gate non-reproducible.
- **No secrets in the scan config.** The OSS engine + local rulesets need no token. A `SEMGREP_APP_TOKEN`
  (only for `semgrep ci` against the platform) is read **lazily from env**, never committed (global rule).

## Invocation + gating — the `--error` and `semgrep ci` distinction (the key gotcha)

```bash
# Local / generic-CI scan with the registry packs. p/owasp-top-ten maps DIRECTLY to the OWASP Top 10.
semgrep scan \
  --config p/owasp-top-ten \
  --config p/security-audit \
  --error \
  --sarif -o results.sarif
```

> **⚠️ `semgrep scan` does NOT fail on findings by default.** Without `--error`, it prints findings and
> **still exits 0** — a silent gate that never blocks a PR. **You must add `--error`** to make findings
> return a non-zero exit code. This is the single most common SAST mis-wiring. In contrast, **`semgrep ci`**
> (the PR-aware mode — uses org policies + cross-file analysis when connected to the platform) **DOES return
> a failing exit code on blocking findings by default.** Opengrep mirrors both behaviours.

- **`--config p/owasp-top-ten`** — the registry pack that maps directly to the OWASP Top 10; **`p/security-audit`**
  adds broader security patterns. Stack the language pack(s) for the scanned codebase (`p/java`, `p/csharp`,
  `p/typescript`, `p/python`) — the rulesets target the **code's** language, not your test framework.
- **`semgrep scan` + `--error`** = the explicit, platform-agnostic gate (works under plain CI / Opengrep).
- **`semgrep ci`** = the PR-aware gate; fails on blocking findings by default, but couples you to the
  Semgrep platform for org policies. For an OSS Opengrep gate, prefer `opengrep scan --error`.

### Exit-code gate table (Semgrep and Opengrep are identical)

| Exit code | Meaning | Gate action |
|-----------|---------|-------------|
| **0** | No findings — **or** findings *without* `--error` | pass |
| **1** | Findings reported **with `--error`** (or blocking findings under `semgrep ci`) | **fail the build** |
| **2** | Fatal error (target unreadable, crash) | fail — investigate, don't treat as clean |
| **3** | Syntax error in a target file under `--strict` | fail — fix the source/exclusion |
| **4** | Invalid pattern | fail — fix the rule |
| **5** | Bad / unparseable YAML config | fail — fix the config |
| **7** | Invalid rule | fail — fix the rule |

The gate is the **process exit code**: `1` (findings + `--error`) blocks the merge; `2`–`7` are scanner/config
faults that must **also** block — never let a crashed scan masquerade as a clean pass (use `--strict` so
config/rule problems surface as a failure, not a silent skip).

## Diff-aware / baseline scanning — gate NEW, don't drown in legacy

A real codebase's first SAST run lights up. The discipline (defer the full framing to
`qa-security-shared` § the triage gate) is: **baseline the existing findings once, then gate only NEW
findings.** Semgrep/Opengrep do this with a baseline commit:

```bash
# Scan only what changed since the baseline — fails on findings INTRODUCED by this PR/branch.
semgrep scan --config p/owasp-top-ten --error \
  --baseline-commit "$(git merge-base origin/main HEAD)"
```

- **`--baseline-commit <sha>`** diffs against that commit: findings already present at the baseline are
  **not** reported, so a PR fails only on flaws *it introduces*. This is the practical way to turn the gate
  on over a legacy codebase without a red wall on day one.
- Pair it with the per-finding suppressions below for the handful of pre-existing findings you must
  explicitly accept.

## Triage — `.semgrepignore` (paths) + inline `// nosemgrep` (lines), ticketed

```gitignore
# .semgrepignore — paths the scanner should never read (NOT a finding allow-list)
node_modules/
**/generated/**
**/*.min.js
build/
dist/
vendor/
test/fixtures/**     # intentionally-vulnerable test fixtures
```

```java
// Inline, line-scoped suppression — ALWAYS carry the rule-id + a ticket (qa-security-shared discipline).
String q = "SELECT * FROM users WHERE id = " + id; // nosemgrep: java.lang.security.audit.sqli — JIRA-5120 false positive: id is an int bound upstream, re-review 2026-Q4
```

- **`.semgrepignore`** excludes **paths** from scanning (vendored, generated, minified, fixtures) — it
  reduces noise and scan time but is **not** a finding allow-list; don't dump real source dirs in it to go
  green.
- **`// nosemgrep: <rule-id>`** suppresses a **specific rule on a specific line**. **Always name the
  rule-id** (a bare `// nosemgrep` mutes *every* rule on that line — too broad) and **always add a ticket +
  reason** (and ideally a re-review date). A suppression with no ticket is a silent hole.
- **Baseline + gate-NEW** via `--baseline-commit` (above) is the primary mechanism for existing findings;
  reserve inline `nosemgrep` for documented false-positives / accepted-risk. **Shrink the set over time** —
  never grow it to make a real finding disappear (the same allow-list discipline as the SCA suppression file
  and the axe baselines; see `qa-security-shared`).

## Custom rules (brief) — org-specific anti-patterns

The OWASP/security packs cover the standard flaw classes — **point at the registry** (`p/owasp-top-ten`,
`p/security-audit`, language packs) for those. Write a **custom YAML rule** only for an org-specific
anti-pattern the packs don't know (e.g. "never call our legacy `Crypto.legacyEncrypt`", "don't log a
`Customer` object"):

```yaml
# .semgrep/rules/no-legacy-crypto.yml — run with --config .semgrep/rules/
rules:
  - id: no-legacy-crypto
    languages: [java]
    severity: ERROR
    message: >-
      Crypto.legacyEncrypt uses ECB/DES — banned (A02). Use AesGcmEncryptor. See SEC-RULES-12.
    metadata: { owasp: "A02:2025", cwe: "CWE-327" }
    patterns:
      - pattern-either:
          - pattern: Crypto.legacyEncrypt(...)
          - pattern: new DESKeySpec(...)
      - metavariable-regex:            # narrow with a metavariable constraint when needed
          metavariable: $X
          regex: '.*'
```

- **`pattern:`** matches one shape; **`pattern-either:`** ORs several; **`metavariable-regex:`** constrains a
  captured metavariable to cut false positives. Tag every custom rule with its `owasp`/`cwe` metadata so it
  consolidates with the pack findings in the OWASP map.
- Keep custom rules few and reviewed — they're real code. The registry packs are the bulk of coverage.

## Reporting → SARIF (code-scanning) + JSON (Allure / CI artifact)

```bash
semgrep scan --config p/owasp-top-ten --error \
  --sarif -o results.sarif \      # → github/codeql-action/upload-sarif → inline PR findings
  --json  -o results.json         # → parse a summary into Allure + upload as a CI artifact
```

- **SARIF → code-scanning** — `github/codeql-action/upload-sarif` surfaces each finding **inline on the PR
  diff**, de-duplicates run-over-run, and tracks new/fixed state. Standardize on SARIF across the whole
  security family (see `qa-security-shared` § consolidate findings).
- **JSON → Allure + artifact** — attach a parsed finding summary to **Allure** (cross-link
  `qa-allure-reporting-{stack}`) and upload `results.{sarif,json}` as a CI artifact so a failing run names
  the findings without re-scanning.

```yaml
# .github/workflows/sast.yml — cross-link qa-ci-pipelines-github-actions-{stack}, qa-_shared/ci-conventions
name: SAST
on: [pull_request]

permissions:
  contents: read
  security-events: write          # required for upload-sarif

jobs:
  semgrep:
    runs-on: ubuntu-latest
    container: { image: semgrep/semgrep }   # or ghcr.io/opengrep/opengrep:latest for the OSS gate
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }            # full history so --baseline-commit can diff
      - run: |
          semgrep scan \
            --config p/owasp-top-ten --config p/security-audit \
            --error \
            --baseline-commit "$(git merge-base origin/main HEAD)" \
            --sarif -o results.sarif --json -o results.json
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: results.sarif }
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: sast-report, path: results.* }
```

> The official `semgrep/semgrep-action` is **deprecated** in favour of running the `semgrep/semgrep` image
> (or `semgrep ci`) directly. For an OSS gate, swap the container for `ghcr.io/opengrep/opengrep:latest` and
> the command for `opengrep scan …` — same flags. **No `SEMGREP_APP_TOKEN` is needed** for the local-ruleset
> OSS path; if you use `semgrep ci` against the platform, pass it via `env` from a secret, never inline.

## OWASP mapping — and the SAST blind spot

SAST maps primarily to the **source-pattern** Top-10 items: **A05 Injection** (SQLi/cmd/XSS sinks reachable
from tainted input via taint analysis), **A06 Insecure Design** patterns (unsafe deserialization, dangerous
defaults), and **A02 Security Misconfiguration / Cryptographic** code patterns (ECB/DES, disabled TLS
verification, weak hashing). Tag each finding with its `owasp`/`cwe` metadata and consolidate via the OWASP
map in `qa-security-shared`.

> **The blind spot — SAST finds *source-pattern* flaws and is blind to *runtime / logic* flaws.** It cannot
> know that invoice `42` belongs to another user (**A01 Broken Access Control** — that's a functional
> `access-control-testing` matrix), nor whether a missing security header ships at runtime (**DAST**), nor
> whether a transitive dep has a CVE (**SCA**). **A SAST-clean codebase is not "secure"** — it means the
> automatable source-pattern layer passed. Pair SAST with **DAST + functional access-control + a manual
> pentest** for business-logic abuse. Say so in every report (see `qa-security-shared`).

## Anti-patterns

- **Forgetting `--error` so the gate never fails.** `semgrep scan` prints findings and **still exits 0**
  without it — the PR merges green over real flaws. *Fix:* add `--error` (or use `semgrep ci`, which fails
  by default); verify the gate actually returns exit 1 on a seeded finding.
- **Gating on every finding from day one.** A legacy codebase lights up; the team mutes or bypasses the
  gate. *Fix:* **baseline + `--baseline-commit`** — gate only findings the PR *introduces*; burn down the
  backlog over time.
- **Blanket-ignoring to go green.** A bare `// nosemgrep` (mutes *all* rules on the line) or dumping source
  dirs into `.semgrepignore` hides future flaws. *Fix:* scope `// nosemgrep: <rule-id>` to one rule + a
  ticket; keep `.semgrepignore` to vendored/generated/fixture paths only.
- **Treating SAST-clean as "secure."** SAST is blind to access control, runtime config, and dependency
  CVEs. *Fix:* run **DAST + SCA + functional access-control**; reserve business-logic abuse for a manual
  pentest. A green SAST gate is one orthogonal layer.
- **Scanning generated / vendored / minified code.** Floods the report with un-actionable noise and slows
  the scan. *Fix:* exclude `generated/`, `vendor/`, `dist/`, `*.min.js` via `.semgrepignore`.
- **Secrets in the CI scan config.** Hard-coding a `SEMGREP_APP_TOKEN` (or any token) in the workflow or a
  config file leaks it. *Fix:* read it lazily from `env` / a CI secret; the OSS local-ruleset path needs no
  token at all (global rule: no secrets in code/config).
- **Ignoring the OSS license trajectory.** Wiring the gate to Semgrep CE while it keeps moving features
  (taint, fingerprinting) behind the commercial license risks a future capability/licensing surprise. *Fix:*
  prefer **Opengrep** for a truly-OSS gate; if you stay on Semgrep, **track the license trajectory** as a
  known risk and confirm which engine features your gate depends on are still OSS.
- **Treating a non-zero exit 2–7 as a pass.** A crashed/mis-configured scan that exits 2 isn't "clean."
  *Fix:* fail the build on any non-zero exit; use `--strict` so config/rule faults surface.

## Rules (hard constraints)

- The gate is the **process exit code**. `semgrep scan` needs **`--error`** to fail on findings (it exits 0
  without it); `semgrep ci` fails on blocking findings by default. Fail on **any** non-zero exit (2–7 are
  scanner/config faults, not passes); use `--strict`.
- Rulesets target the **language of the scanned codebase**, not the test framework — stack the relevant
  registry packs (`p/owasp-top-ten` for the Top-10 map, `p/security-audit`, the language pack).
- **Baseline existing findings and gate NEW ones** (`--baseline-commit`); inline `// nosemgrep: <rule-id>`
  and `.semgrepignore` carry a **ticket + reason**; scope every suppression to one rule/path; shrink the set
  over time (the `qa-security-shared` triage discipline).
- **No secrets in scan config** — any platform token via env, lazily; the OSS local-ruleset path needs none.
- Emit **SARIF** → code-scanning (inline PR findings) **and** JSON → Allure + CI artifact.
- **Prefer Opengrep** as the truly-OSS default (taint/inter-procedural restored, LGPL-2.1, Semgrep-compatible
  JSON/SARIF); reach for Semgrep proper only on its AppSec platform. **Track the OSS license trajectory.**
- **SAST-clean ≠ secure** — it's the source-pattern layer only. Run **DAST + SCA + functional
  access-control**; reserve business-logic abuse for a manual pentest. Map every finding to an OWASP item.

## Cross-references

- `qa-security-shared` — **load alongside**: the OWASP Top-10 map, the automatable-vs-manual boundary, the
  ticketed-suppression triage discipline, SARIF → code-scanning consolidation, and the scan-authorization
  rules this skill defers to.
- `qa-security-testing-dependency-scanning-{java,dotnet,typescript}` — **SCA**: scans the **dependency tree**
  for known CVEs (build graph, not source). Orthogonal layer — run both.
- `qa-security-testing-zap-automation-framework` / `qa-security-testing-zap-baseline-{stack}` — **DAST**:
  probes the **running app** over HTTP. SAST never runs the app; orthogonal — run both.
- `qa-security-testing-secrets-scanning` — finds **leaked credentials** in source + git history (a different
  source concern from insecure-code-pattern SAST).
- `qa/<stack>/skills/security-testing/access-control-testing` — the **functional** BOLA/IDOR/BFLA matrix for
  A01, the access-control flaw SAST is blind to.
- `qa/<stack>/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` + `qa/_shared/ci-conventions` —
  wire the gate step, SARIF upload, and artifact.
- `qa/<stack>/skills/allure-reporting` — attach the parsed JSON finding summary to the run.
- `qa/_shared/agents/qa-security.md` — the phased orchestrator that runs SAST in the per-PR static-gates
  phase (Phase 2) alongside secrets + SCA.
