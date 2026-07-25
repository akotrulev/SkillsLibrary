---
name: qa-security-testing-dependency-scanning-typescript
description: Use when wiring SCA (dependency-vulnerability scanning) as a CI gate for a TypeScript build — `npm audit` (lockfile-driven) as the native gate over the direct + transitive tree, failing above a severity threshold, with a ticketed suppression path. Triggers: "fail the build on vulnerable dependencies", "add dependency scanning", "gate new CVEs". Not for runtime DAST → `security-testing/zap-baseline`. For end-to-end suite work prefer the phased agent `qa-performance-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# Security Testing — Dependency Scanning / SCA (TypeScript)

**Software Composition Analysis (SCA)** answers a different security question from DAST: not "is the
running app exploitable over HTTP?" (that's ZAP, `zap-baseline`) but **"does my dependency tree contain package
versions with known CVEs?"** It reads your **`package-lock.json`** — direct *and* **transitive**
dependencies — matches each package+version against a vulnerability feed (the **GitHub Advisory Database**
that backs `npm audit`, plus OSV / NVD), and **fails the build** when a finding crosses a severity
threshold. It needs **no running app** (contrast DAST): it's a static, fast, every-PR pipeline gate.

> **⚠️ SCA vs DAST — two orthogonal layers, run both.** ZAP scans the **running app's HTTP
> surface** (missing headers, cookie flags, info leaks). SCA scans your **dependency tree** (a
> vulnerable `lodash`, a transitive `minimist`…). A clean ZAP baseline says nothing about a prototype
> pollution in a transitive package; a clean SCA says nothing about a missing CSP header. **Together they
> close Phase 2's `security-testing` family — wire both gates.**

> **Stack-native first.** Unlike `zap-baseline` (one language-agnostic Docker tool), SCA is **stack-native**: each
> ecosystem has its own first-class auditor. TypeScript's is **`npm audit`** — built in, no install, reads
> the lockfile, exit-code gate — so this skill leads with it. **OWASP Dependency-Check** is the cross-stack
> common denominator (its richest form is the Gradle plugin — the Java sibling is canonical for this node);
> reach for it (or **OSV-Scanner**) only when you need parity with a JVM/.NET monorepo. The **discipline**
> — severity-gate, ticketed-suppress, fail-the-build, report→Allure — is identical across all three; only
> the tool differs.

## Decision matrix — where SCA fits

| Need | Use | Why |
|------|-----|-----|
| Gate the **dependency tree** (direct + transitive CVEs) in every PR | **this skill** (`npm audit`) | Built in, static, fast, no running app; exits non-zero above `--audit-level` |
| Scan the **running app's HTTP surface** (headers, cookies, info leaks) | zap-baseline | DAST probes live traffic — orthogonal layer; run both |
| **Remediate** vulnerable deps automatically | `npm audit fix` / Dependabot / Renovate | They *bump*; `npm audit` *gates*. Complementary — gate + auto-fix |
| Gate only the deps a PR **adds/changes** (diff-scoped) | `dependency-review-action` | PR-diff gate on GitHub; pairs with the full-tree audit |
| **Cross-stack** parity in a polyglot monorepo | OWASP Dependency-Check / OSV-Scanner | One tool over npm + Maven + NuGet; otherwise `npm audit` is simpler for pure-TS |

**Rule of thumb:** SCA is your **dependency-tree CVE gate**; it complements — does not replace — DAST
(`zap-baseline`). Pair the gate with a *remediation* tool (`npm audit fix` / Dependabot / Renovate) so findings get
fixed, not just flagged.

## Setup — nothing to install

`npm audit` ships with npm. The lockfile (`package-lock.json`) is the input — commit it. There's no SDK and
no separate server (contrast `zap-baseline`'s Docker image).

```bash
npm audit                                   # human-readable report of the whole tree
npm audit --audit-level=high                # ❌ exit non-zero if any vuln is High or Critical (the gate)
npm audit --json                            # machine-readable report → parse / attach to Allure
npm audit --omit=dev                        # production deps only (skip devDependencies)
npm audit fix                               # auto-bump within semver range; `--force` allows major bumps
```

> **`pnpm` / `yarn` variants.** `pnpm audit --audit-level=high` is the same shape. Yarn Berry uses `yarn
> npm audit --severity high` (Yarn Classic: `yarn audit --level high` — note: no exit-code gate flag, parse
> the output). Pick the one matching your package manager; the gate semantics are equivalent.

## The SCA model — scan direct + transitive deps against a CVE feed

`npm audit` submits the resolved dependency set from `package-lock.json` to the registry's advisory
endpoint and gets back known vulnerabilities — for **every** package in the tree, **including transitive
ones you never declared**. Each is graded **info / low / moderate / high / critical**. The defining traits:

- **Transitive coverage is the whole point.** You declared `express`; it dragged in dozens of transitive
  packages. SCA flags a CVE in a transitive `qs` or `minimist` you never typed. (Contrast eyeballing
  `package.json` — that misses exactly the deps you didn't choose.)
- **No running app.** Lockfile-driven; runs in seconds. Contrast DAST, which needs a deployed target.
- **The gate is a severity threshold** — `--audit-level=high` exits non-zero on High+ findings. Pick it
  deliberately: start at `critical`, ratchet to `high` as you clear the backlog.

## The build-fail gate — `--audit-level` + the exit code

The gate is the **process exit code** — same build-fail mechanism as `zap-baseline`'s ZAP exit code. `npm audit
--audit-level=<level>` exits **non-zero** if any vulnerability is **at or above** that level, **zero**
otherwise:

| `--audit-level` | Fails on | npm severity | Typical use |
|-----------------|----------|--------------|-------------|
| `low` | low+ | maps to GHSA/CVSS Low+ | only once the tree is clean; usually too strict to start |
| `moderate` | moderate+ | CVSS ~4.0–6.9 | mid gate |
| `high` | **high+** | CVSS ~7.0–10.0 | **common starting gate** |
| `critical` | **critical only** | CVSS ~9.0–10.0 | initial gate on a legacy tree with a backlog |

```bash
# CI gate — the exit code fails the job:
npm audit --audit-level=high --omit=dev
```

The npm severity map mirrors the Java sibling's CVSS thresholds (`failBuildOnCVSS`) and the .NET sibling's
`NuGetAuditLevel`. Start at `critical`, clear the backlog, ratchet down to `high`.

## The triage gate — ticketed `overrides` / `.nsprc` (like `axe-playwright` / `zap-baseline`)

A real project's first audit lights up — including findings you **cannot fix today** because they're in a
**transitive** package or are false positives. Gating on *everything* with no triage trains the team to
mute the gate. The disciplined approach is the **ticketed allow-list** — same discipline as
`qa-accessibility-testing-typescript` and `zap-baseline`'s `rules.tsv`, ported to SCA.

`npm audit` itself has no native suppression file; the two real options:

**1. `overrides` — the *fix*, not a mute (preferred).** Force the transitive package to a patched version:

```jsonc
// package.json — force a patched transitive version (the real fix; cross-link the transitive reality)
{
  "overrides": {
    // JIRA-4210: CVE-2023-XXXX in transitive 'minimist' via 'mkdirp'; upstream slow → force the fix.
    "minimist": "1.2.8",
    // Scope to a path when only one parent's copy is vulnerable:
    "express > qs": "6.11.0"
  }
}
```

**2. `.nsprc` / `audit-ci` allow-list — the *ticketed deferral*.** When you genuinely cannot bump yet
(no patched version exists), use a CI-audit wrapper (`audit-ci` or `better-npm-audit`) with a documented,
ticketed allow-list:

```jsonc
// .nsprc — better-npm-audit allow-list: every entry is a documented, ticketed accepted-risk
{
  "exceptions": [
    // JIRA-4211: GHSA-xxxx-xxxx (moderate) in transitive 'tough-cookie'; no patch yet, re-review 2026-09-01.
    "GHSA-xxxx-xxxx-xxxx"
  ]
}
```

```bash
# audit-ci reads the allow-list and fails the build above the threshold otherwise:
npx audit-ci --high --config audit-ci.jsonc
```

- **Discipline (reuse `axe-playwright` / `zap-baseline`):** gate **new** CVEs; allow-list only *documented, ticketed*
  accepted-risk; **shrink** the list over time, never grow it to silence a real finding. Every entry names
  a ticket; prefer an **`override` (the real fix)** over an allow-list entry (a tracked deferral).

### The transitive-dep reality

The hard part of SCA: the vulnerable package is often **transitive** — you didn't declare it and can't just
bump its line. Three honest responses, in order of preference:

1. **`overrides`** — pin the transitive package to a patched version (shown above). The real fix.
2. **Bump the direct parent** that pulls it in, if a patched line resolves the transitive.
3. **Allow-list with a ticket** (`.nsprc` / `audit-ci`) *only* when neither works yet (no upstream fix) —
   and revisit at the recorded date. (The Java sibling uses Dependency-Check's `until=` expiry; the .NET
   sibling uses `NuGetAuditSuppress`. Same idea: a tracked, time-boxed deferral, not a permanent mute.)

## Report → Allure + SARIF / GitHub code-scanning

`npm audit --json` emits the full advisory set. Attach it (plus a readable summary) to Allure so a failing
run names the CVEs without re-auditing; feed SARIF to GitHub code-scanning so findings show inline on the
PR (cross-link `qa-allure-reporting-typescript`):

```ts
// support/npm-audit-report.ts — run the audit, attach JSON + summary to Allure, return the gate verdict
import { spawnSync } from 'node:child_process';
import { allure } from 'allure-js-commons';

export interface AuditResult {
  exitCode: number;                 // non-zero = at/above --audit-level (the gate)
  vulnerabilities: Record<string, { severity: string; via: unknown[] }>;
}

export function runNpmAudit(level: 'low' | 'moderate' | 'high' | 'critical' = 'high'): AuditResult {
  const proc = spawnSync('npm', ['audit', `--audit-level=${level}`, '--json', '--omit=dev'],
    { encoding: 'utf-8' });
  const report = JSON.parse(proc.stdout || '{}');
  allure.attachment('npm-audit.json', proc.stdout, 'application/json');
  const vulns: AuditResult['vulnerabilities'] = report.vulnerabilities ?? {};
  const summary = Object.entries(vulns)
    .map(([name, v]) => `[${v.severity}] ${name}`)
    .join('\n');
  allure.attachment('npm-audit-summary.txt', summary || 'no vulnerabilities', 'text/plain');
  return { exitCode: proc.status ?? 1, vulnerabilities: vulns };
}
```

- **Allure** — attach the JSON + a readable summary (cross-link `qa-allure-reporting-typescript`).
- **SARIF → GitHub code-scanning** — convert `npm audit --json` to SARIF (e.g. a converter step) and feed
  `github/codeql-action/upload-sarif` so each CVE shows inline on the PR diff. OSV-Scanner emits SARIF
  natively if you prefer.
- **CI artifact** — upload the JSON (cross-link `qa-ci-pipelines-typescript`).

## Optional parse-and-assert test (the programmatic path)

SCA is primarily a **CI gate** (`npm audit --audit-level=high`). When you want a test-level assertion — a
custom threshold, or to surface the count in your test report — parse the JSON (Vitest, mirroring `zap-baseline`'s
parsed-report gate):

```ts
// tests/dependency-scan.spec.ts
import { describe, it, expect } from 'vitest';
import { runNpmAudit } from '../support/npm-audit-report';

describe('Dependency scan (SCA) gate', () => {
  it('Should_have_no_high_severity_cves_When_dependencies_scanned', () => {
    const result = runNpmAudit('high');     // attaches the JSON report to Allure before returning
    const high = Object.entries(result.vulnerabilities)
      .filter(([, v]) => v.severity === 'high' || v.severity === 'critical')
      .map(([name]) => name);
    expect(high).toEqual([]);                // one logical assertion = the gate
  });
});
```

The Java/.NET siblings parse their own tool's JSON (`dependency-check-report.json` / `dotnet list package
--vulnerable --format json`) the same way. Test name `Should_X_When_Y`.

## CI wiring — the gate, the remediation complement

```yaml
# .github/workflows/sca.yml — cross-link qa-ci-pipelines-typescript
name: Dependency Scan (SCA)
on: [pull_request]

jobs:
  dependency-review:                     # PR-diff gate: fails on vulnerable deps the PR ADDS
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/dependency-review-action@v4
        with: { fail-on-severity: high }

  npm-audit:                             # full-tree SCA gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm audit --audit-level=high --omit=dev   # exit code fails the job
      - if: always()
        run: npm audit --json > npm-audit.json || true # capture report even on failure
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: npm-audit-report, path: npm-audit.json }
```

- **`dependency-review-action`** — the **PR-diff** gate (fails on deps the PR *adds* above
  `fail-on-severity`); pairs with the full-tree `npm audit`.
- **Remediation complement** — **`npm audit fix`** / **Dependabot** / **Renovate** *raise PRs to bump*
  vulnerable deps; `npm audit` *gates*. Wire both: the gate stops new CVEs landing, the bot fixes the
  backlog.
- **No NVD cache needed** for `npm audit` (it queries the registry advisory endpoint live) — but if you use
  OWASP Dependency-Check for cross-stack parity, **cache its NVD DB** (slow cold download — see the Java
  sibling).

## Anti-patterns

- **Treating SCA as a substitute for DAST (or vice-versa).** A clean dependency tree says nothing about a
  missing security header; a clean ZAP baseline says nothing about a vulnerable transitive package. *Fix:*
  run **both** `zap-baseline` + `dependency-scanning` — orthogonal layers.
- **`npm audit fix --force` blindly in CI.** Major bumps can break the build / change behavior unreviewed.
  *Fix:* `--force` is for a reviewed PR, not the gate; let Dependabot raise reviewable bumps.
- **Auditing only `package.json` by eye.** Most real CVEs are **transitive**. *Fix:* `npm audit` reads the
  full lockfile — don't substitute manual inspection.
- **Suppressing a whole package to go green.** Hides every future CVE in it. *Fix:* a scoped, **ticketed**
  `.nsprc`/`audit-ci` exception for the specific advisory, with a re-review date.
- **Permanent allow-list entries with no ticket/date.** They rot. *Fix:* every exception names a ticket and
  a re-review date; prefer an `override` (the real fix) over a deferral.
- **Gating without remediating.** The build stays red and the team disables the gate. *Fix:* pair the gate
  with `npm audit fix` / Dependabot / Renovate.
- **Not committing `package-lock.json`.** Without it the audit can't resolve the exact tree. *Fix:* commit
  the lockfile; `npm ci` in CI.
- **`--audit-level=low` on day one of a legacy tree.** Everything fails; the gate gets bypassed. *Fix:*
  start at `critical`, clear the backlog, ratchet to `high`.

## Examples

**End-to-end: a PR SCA gate that fails on a new High CVE, fixes the fixable transitive one with an
`override`, and defers the unfixable one with a ticketed allow-list.**

```jsonc
// package.json
{
  "scripts": { "audit:ci": "audit-ci --high --config audit-ci.jsonc" },
  "overrides": {
    // Real fix: force the patched transitive version (preferred response).
    "minimist": "1.2.8"
  }
}
```

```jsonc
// audit-ci.jsonc — the ticketed allow-list for the not-yet-fixable one
{
  "high": true,
  "allowlist": [
    // JIRA-4211: GHSA-xxxx (high) in transitive 'tough-cookie'; no upstream patch, re-review 2026-09-01.
    "GHSA-xxxx-xxxx-xxxx"
  ]
}
```

Lifecycle for this gate:
1. A dev adds a package; it pulls in a transitive `minimist` with a **High** CVE.
2. The PR runs `npm audit --audit-level=high` → exits non-zero → **the job fails**, with the advisory in the
   uploaded JSON report.
3. The dev adds an `overrides` entry forcing patched `minimist` (the real fix) → the audit passes. A
   *second*, currently-unfixable transitive CVE is allow-listed in `audit-ci.jsonc` with a JIRA ticket and a
   re-review date — tracked, not silently muted.
4. Dependabot later raises the parent bump that removes the deferred CVE; the allow-list entry is deleted at
   its review — the list shrinks, never grows.

## Rules (hard constraints)

- The gate is the **process exit code** of `npm audit --audit-level=<level>`, optionally plus a
  **parsed-report** assertion. One logical assertion per test; test names `Should_X_When_Y`.
- Scan **direct + transitive** deps against a CVE feed — transitive coverage is the point. SCA reads the
  **lockfile** (no running app — contrast DAST). Commit `package-lock.json`; `npm ci` in CI.
- Triage with a **ticketed allow-list** (`overrides` for the real fix; `.nsprc`/`audit-ci` for a deferral):
  scope to the specific advisory, name a ticket + re-review date. Gate **new** CVEs; shrink the list, never
  grow it (the `axe-playwright`/`zap-baseline` discipline). Prefer **`overrides` (the fix)** over an allow-list (a deferral).
- Emit **JSON**: attach to **Allure**, upload as a CI artifact, optionally convert to **SARIF** for GitHub
  code-scanning.
- Pair the **gate** with **remediation** (`npm audit fix` / Dependabot / Renovate) and the
  **`dependency-review-action`** PR-diff gate. A clean SCA ≠ "secure" — **run DAST too**: orthogonal
  layers.

## Cross-references

- `qa-security-testing-dependency-scanning-java` — same skill, Java / **OWASP Dependency-Check Gradle
  plugin** (`failBuildOnCVSS`, suppression XML with `until=`); the **canonical** sibling and the cross-stack
  throughline.
- `qa-security-testing-dependency-scanning-dotnet` — same skill, .NET / `dotnet list package --vulnerable
  --include-transitive` + NuGet audit (`<NuGetAudit>`, `NuGetAuditLevel`).
- `qa-security-testing-zap-baseline-typescript` — the **DAST** sibling that opened the
  `security-testing` family: ZAP probes the **running app's HTTP surface**; SCA reads your **lockfile**.
  Orthogonal layers — **run both** (together they close Phase 2).
- `qa-accessibility-testing-typescript` — the **ticketed-baseline triage** discipline
  reused here for the allow-list (gate new findings, document every suppression with a ticket).
- `qa-ci-pipelines-typescript` — the gate step, `dependency-review-action`, artifact upload.
- `qa-allure-reporting-typescript` — attach the `npm audit --json` report and summary to the run.
