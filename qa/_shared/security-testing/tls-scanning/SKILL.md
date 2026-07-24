---
name: qa-security-testing-tls-scanning
description: Use when gating an endpoint's TLS/SSL handshake in CI — deprecated protocols (SSLv2/3, TLS 1.0/1.1), weak or insecure cipher suites (RC4, 3DES, EXPORT), broken forward secrecy, certificate validity/chain/expiry, and known issues (ROBOT, Heartbleed) — with sslyze as the lead tool (ships a native Mozilla-policy gate) or testssl.sh as the zero-dependency Bash alternative. Read-only and the one scan that is safe against production. Language-agnostic (CLI / Docker), any stack. Triggers "scan our TLS configuration", "check for weak ciphers", "is our certificate chain valid / when does it expire", "fail CI on deprecated TLS versions", "prove we are TLS 1.2+ only". Do NOT use for HTTP-layer security headers or cookie flags (use `qa-security-testing-zap-baseline-*`), for application CVEs (use `qa-security-testing-sast` or the stack's `security-testing/dependency-scanning`), or for active injection testing (use `qa-security-testing-zap-automation-framework`).
---

# Security Testing — TLS / SSL Configuration Scanning (shared)

Transport-layer crypto scanning: does the endpoint's **TLS handshake** meet a known-good bar? Below the
HTTP headers ZAP inspects sits the handshake itself — the protocol versions offered, the cipher suites
negotiated, the certificate chain presented, the forward-secrecy and known-vulnerability posture. This
skill gates **that layer** in CI, with **sslyze** as the lead tool (it ships a native Mozilla-policy gate)
and **testssl.sh** as the zero-dependency Bash alternative.

This is a **single language-agnostic skill** under `qa/_shared/security-testing/` — both tools are CLIs /
Docker images invoked identically from any pipeline. There is nothing to gain from a per-stack split (the
backbone's leaner-shape principle — don't triplicate a `docker run`). Load **`qa-security-shared`**
alongside for the OWASP map, the ticketed-triage discipline, and SARIF consolidation.

> **🟢 A TLS scan is passive and prod-safe — the one scan that is safe against production by nature.** A
> TLS scan is a **handshake probe**: it opens connections, reads what the server offers, inspects the
> presented certificate, and closes — **no payloads, no state mutation, no exploitation**. Unlike an
> *active* DAST scan (ZAP full / API fuzzing — which inject payloads and **must never touch prod or a
> shared env**, per `qa-security-shared`), a TLS scan is **read-only**, so it is **safe to run against a
> production endpoint** and is a natural **pre-release / scheduled** gate as well as a per-PR gate against
> an ephemeral env. The single caveat: a scan opens many short connections, so **do not hammer a
> rate-limited or WAF-fronted prod endpoint** in a tight loop — schedule it, and respect rate limits.

## Decision matrix — which tool, and where this layer fits

| Need | Use | Why |
|------|-----|-----|
| TLS gate with an **explicit, enforced policy** + native non-zero exit | **sslyze `--mozilla_config`** (LEAD) | Checks against **Mozilla intermediate/old/modern** and **exits non-zero on non-compliance** — the cleanest native CI gate; no custom parsing |
| TLS scan on a runner with **no Python / no Docker pull**, or you want CSV/HTML too | **testssl.sh** | Pure Bash, zero deps; machine-readable CSV + two JSON shapes + HTML — but you **gate by parsing JSON severity** (no built-in Mozilla policy) |
| HTTP **security headers** incl. **HSTS**, cookie flags, CSP, info leaks | `qa-security-testing-zap-baseline-{stack}` | Header layer is **ZAP's** — adjacent but distinct; this skill probes the handshake *below* the headers. (TLS tools surface HSTS presence too, but the header gate is ZAP's.) |
| App-layer **active** attack scan (SQLi/XSS/traversal payloads) | `qa-security-testing-zap-automation-framework` | Sends payloads, mutates state — **never prod**. TLS scan never sends a payload. |
| The OWASP map, triage discipline, scan-authorization rules, SARIF | `qa-security-shared` | The spine; load it alongside this tool skill. |

**Rule of thumb:** prefer **sslyze** as the gate (its native Mozilla-profile exit code *is* the policy —
no parsing, the bar is in one flag). Reach for **testssl.sh** when you can't run sslyze, want the HTML
report, or want CSV; then gate by **parsing JSON severity** (`severity >= HIGH`). Both are prod-safe.

## What a TLS scan checks (both tools, OWASP A04 / A02)

A handshake probe enumerates and flags, against every cert/protocol/cipher the endpoint offers:

| Check | Flag when… | OWASP |
|-------|-----------|-------|
| **Protocol versions** | SSLv2 / SSLv3 / **TLS 1.0 / TLS 1.1** offered (deprecated) | A02 / A04 |
| **Cipher suites** | weak/insecure: **RC4**, **3DES**, **EXPORT**, **NULL**, anon, CBC weak | A04 |
| **Forward secrecy** | no ECDHE/DHE (no PFS) | A04 |
| **Certificate** | expired / not-yet-valid, **near expiry**, wrong CN/SAN, self-signed, broken/incomplete chain, weak sig (SHA-1), short key | A04 |
| **Known vulnerabilities** | **ROBOT**, **Heartbleed**, CCS-injection, **POODLE**, **BEAST**, **CRIME**, **DROWN**, **FREAK**, **Logjam**, Lucky13, Ticketbleed, Sweet32 | A04 |
| **HSTS presence** | `Strict-Transport-Security` missing/short max-age (surfaced — but the **header gate is ZAP's**) | A02 |

This maps squarely to **A04 Cryptographic Failures** (transport crypto) and **A02 Security
Misconfiguration** (protocol/cipher config). It is also a recurring **compliance** bar: **PCI-DSS**
requires disabling early-TLS (TLS 1.0, and 1.1 in practice) and weak ciphers — a pinned Mozilla
`intermediate` profile satisfies it cleanly; cite the profile in the audit trail.

## Setup — pip / Docker / Action (no per-stack artifact)

**sslyze** (Python lib + CLI — runs anywhere Python 3 runs, or via Docker):

```bash
pip install --upgrade sslyze            # Python 3.10+; ships the `sslyze` CLI and a library API
# or Dockerised (no local Python):
docker run --rm nablac0d3/sslyze:latest --mozilla_config=intermediate example.com:443
```

**testssl.sh** (pure Bash, OpenSSL bundled — no language runtime, no deps):

```bash
git clone --depth 1 https://github.com/testssl/testssl.sh.git
# or the maintained image:
docker run --rm drwetter/testssl.sh:latest --severity HIGH https://example.com
```

No Maven/Gradle/npm artifact and no per-stack wrapper — these are CLIs. Any stack's pipeline calls them
the same way; gate on the **process exit code** (sslyze) or the **parsed JSON** (testssl.sh).

## Invocation — and the Mozilla-profile concept (sslyze's native gate)

**sslyze** — `--mozilla_config` is the headline. Mozilla publishes three **recommended TLS
configurations**; sslyze checks the endpoint against the chosen one and **exits non-zero if it doesn't
comply** — the gate is the flag, not a parse:

```bash
# Gate against the Mozilla "intermediate" profile (the recommended default for general-purpose servers).
# Non-zero exit if the endpoint does NOT meet the profile → fails the build natively.
sslyze --mozilla_config=intermediate --json_out results.json example.com:443
```

| `--mozilla_config` | Bar | Use |
|--------------------|-----|-----|
| `modern` | TLS 1.3 only, strictest | TLS1.3-only services; tightest gate |
| `intermediate` (**default**) | TLS 1.2+ , strong ciphers, PFS — **recommended** | general-purpose servers; the default gate |
| `old` | back-compat (allows TLS 1.0/1.1) | legacy clients only — a **documented exception**, never the default |
| `disable` | run scan plugins, **no policy gate** | report-only; gate then comes from parsing `results.json` |

`--json_out results.json` always writes the full machine-readable result (the report). Other plugins run
by default (cert info, cipher suites, ROBOT/Heartbleed/etc.); `--mozilla_config` adds the **compliance
verdict + exit code** on top.

**testssl.sh** — runs the full battery and writes machine-readable output; **`--severity` sets the
floor** for what's emitted, but it does **not** enforce a Mozilla policy — you gate by parsing:

```bash
# JSON + HTML; only emit findings at HIGH or above. Exit code is NOT a Mozilla verdict — parse the JSON.
testssl.sh --jsonfile out.json --htmlfile out.html --severity HIGH https://example.com
```

testssl.sh emits **CSV** (`--csvfile`), **two JSON shapes** (`--jsonfile` flat / `--jsonfile-pretty`
nested), and **HTML** (`--htmlfile`). `--severity <LOW|MEDIUM|HIGH|CRITICAL>` filters output; `--quiet`,
`--color 0`, and `--parallel` suit CI.

## The gate — sslyze native exit (preferred) vs testssl.sh JSON-parse

**Preferred — sslyze native non-zero exit on Mozilla non-compliance.** The policy lives in one pinned
flag; the exit code is the gate. No parsing, no severity heuristics:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Pin the profile explicitly so the bar is auditable and cannot silently drift (see Anti-patterns).
sslyze --mozilla_config=intermediate --json_out results.json "${TARGET}:443"
# sslyze exited non-zero ⇒ the endpoint failed the pinned Mozilla profile ⇒ the build fails here.
echo "TLS endpoint meets the Mozilla 'intermediate' profile."
```

**Alternative — testssl.sh: parse the JSON, fail on `severity >= HIGH`.** testssl.sh's exit code is not a
policy verdict, so gate the JSON severity yourself (use the structured findings, **never read the HTML by
eye**):

```bash
#!/usr/bin/env bash
set -euo pipefail
testssl.sh --jsonfile out.json --htmlfile out.html --severity HIGH --quiet "https://${TARGET}"
# Count findings at HIGH or CRITICAL; any → fail. (jq over the structured report, not eyeballing HTML.)
high=$(jq '[.[] | select(.severity == "HIGH" or .severity == "CRITICAL")] | length' out.json)
if [ "${high}" -gt 0 ]; then
  echo "::error::testssl.sh found ${high} HIGH/CRITICAL TLS finding(s) — see out.html"
  jq -r '.[] | select(.severity=="HIGH" or .severity=="CRITICAL") | "[\(.severity)] \(.id): \(.finding)"' out.json
  exit 1
fi
echo "No HIGH/CRITICAL TLS findings."
```

Same triage discipline as the rest of the family (`qa-security-shared`): **gate NEW regressions hard**;
known, documented exceptions are tracked with a ticket (see Triage), not by quietly lowering the bar.

## Prod-safe note (it bears repeating)

Because the scan is a **read-only handshake probe** with no payloads, it is the **one security scan you
may point at production** — useful as a scheduled posture check and a pre-release gate against the real
cert/config. It still **must not hammer** a rate-limited or WAF-fronted endpoint: schedule it (not on
every push against prod), keep `--parallel`/concurrency modest, and prefer an ephemeral or staging
endpoint for per-PR runs where the cert/config matches prod.

## Triage — documented exceptions, gate the new regressions

Defer the full discipline to `qa-security-shared` (baseline once · gate NEW hard · every suppression
carries a ticket + reason + expiry · shrink the list). For TLS specifically:

- **Pin the Mozilla profile** so the bar is explicit and auditable (`--mozilla_config=intermediate`, in
  config, not ad-hoc). Bumping `intermediate`→`modern` is a deliberate, reviewed change.
- **A legacy exception is a ticket, not a downgrade.** If a partner endpoint must allow **TLS 1.2-only**
  (no 1.3) or a specific cipher for a legacy client, track it as a **documented, ticketed accepted risk
  with an expiry** — e.g. scan that host with `--mozilla_config=old` *and* a `JIRA-XXXX` comment, while
  every other host stays on `intermediate`. Never relax the global profile to make one host pass.
- **A cert nearing expiry is not "low."** Treat near-expiry as a gating finding (it becomes an outage),
  not an informational note — alert before it lapses.

## Reporting — JSON → Allure + CI artifact; testssl HTML; no native SARIF

- **sslyze** → `--json_out results.json`: attach to **Allure** + upload as a CI artifact so a failing run
  names the offending protocol/cipher/cert without re-scanning.
- **testssl.sh** → attach the **`--htmlfile` HTML report** (human-readable) + the JSON; keep CSV if your
  pipeline ingests it.
- **⚠️ Neither tool emits SARIF natively.** Unlike the SAST/SCA/container tools in this family, you
  **cannot** feed sslyze/testssl.sh straight into the code-scanning SARIF surface. Either **attach the
  JSON/HTML** as a CI artifact + Allure attachment (simplest), or **convert** the JSON to SARIF with a
  small transform if you want the findings inline on the PR. State this plainly — don't assume
  `upload-sarif` will accept the raw output.

Cross-link `qa/reporting/<stack>/skills/allure-reporting` for the attachment mechanics.

```yaml
# .github/workflows/tls-scan.yml — sslyze native gate (preferred), schedulable + prod-safe
name: TLS Scan
on:
  pull_request:
  schedule:
    - cron: '0 6 * * 1'        # weekly posture check (prod-safe: read-only handshake probe)
jobs:
  sslyze:
    runs-on: ubuntu-latest
    steps:
      - name: sslyze (Mozilla intermediate gate)
        run: |
          pip install --upgrade sslyze
          # Non-zero exit on non-compliance fails the job natively — the policy is the pinned flag.
          sslyze --mozilla_config=intermediate --json_out results.json "${TARGET}:443"
        env:
          TARGET: ${{ vars.TLS_TARGET }}          # host only; no secrets in scan config
      - name: Upload report (no native SARIF — attach JSON)
        if: always()                              # attach even on failure, so the finding is named
        uses: actions/upload-artifact@v4
        with:
          name: sslyze-report
          path: results.json
  # testssl.sh alternative: `uses: drwetter/testssl.sh` image or the testssl action, then jq-gate the JSON.
```

## Anti-patterns

- **No pinned Mozilla profile** — running `sslyze` without `--mozilla_config` (or testssl.sh with no
  severity gate) so "the bar" drifts with the tool's defaults. *Fix:* pin `--mozilla_config=intermediate`
  (or your chosen profile) explicitly in config; treat a profile bump as a reviewed change.
- **Parsing testssl.sh by eye** — reading the HTML/terminal output and deciding "looks fine" instead of a
  programmatic gate. *Fix:* gate the **JSON severity** (`jq` on `severity >= HIGH`); the HTML is for
  humans *after* a failure, not the gate.
- **Treating a cert-expiry warning as low** — letting a near-expiry cert through as informational. *Fix:*
  near-expiry is a **gating** finding (it becomes a prod outage); alert and fail before it lapses.
- **Ignoring HSTS** — dismissing a missing/short `Strict-Transport-Security` because "TLS itself is fine."
  *Fix:* track HSTS — but remember the **header gate is ZAP's** (`zap-baseline`); coordinate, don't drop
  it between the two skills.
- **Hammering a rate-limited prod endpoint** — looping the scan on every push against a WAF/rate-limited
  prod host and getting throttled/blocked (or false-clean). *Fix:* schedule it, modest concurrency; run
  per-PR against an ephemeral/staging endpoint matching prod.
- **Accepting TLS 1.0 / 1.1** (or RC4/3DES/EXPORT ciphers) as "still works." Deprecated and a PCI-DSS
  fail. *Fix:* the `intermediate` profile rejects them — keep them rejected; legacy needs a ticketed
  exception, not a global downgrade.
- **No ticket on a documented exception** — silently scanning a legacy host with `--mozilla_config=old`
  (or excluding it) with no record. *Fix:* every relaxation is a **ticketed, expiring** accepted risk
  (`qa-security-shared` triage); the global profile stays strict.
- **Assuming SARIF works** — wiring `upload-sarif` against sslyze/testssl.sh output. Neither emits SARIF.
  *Fix:* attach JSON/HTML as an artifact + Allure, or convert JSON→SARIF deliberately.
- **Secrets in scan config** — putting an API key / auth token in the scan command to reach a gated
  endpoint. *Fix:* env vars read lazily; the target host is config, not a secret.

## Rules (hard constraints)

- **A TLS scan is a passive, read-only handshake probe — prod-safe by nature.** It is the one scan you may
  point at production. Never hammer a rate-limited endpoint; schedule it.
- **Prefer sslyze's native Mozilla gate**: `sslyze --mozilla_config=<profile> --json_out out.json
  host:443` — the **non-zero exit on non-compliance is the gate**. For testssl.sh, **parse the JSON** and
  fail on `severity >= HIGH` (its exit code is not a policy verdict).
- **Pin the Mozilla profile** (`intermediate` default) explicitly so the bar is auditable and can't drift.
- **Gate NEW regressions hard; documented exceptions are ticketed** (with reason + expiry) — never relax
  the global profile to pass one legacy host. Defer the full triage discipline to `qa-security-shared`.
- **Map findings to OWASP A04 (transport crypto) / A02 (protocol-cipher config)**; a pinned `intermediate`
  profile also satisfies the **PCI-DSS** early-TLS/weak-cipher bar — cite the profile.
- **Neither tool emits SARIF** — attach JSON/HTML to Allure + CI artifact, or convert JSON→SARIF
  deliberately; don't assume `upload-sarif` accepts raw output.
- **No secrets in scan config** — env vars read lazily; the target host is config, not a secret.
- A clean TLS scan covers **only** the transport layer — pair with the ZAP header baseline, DAST, SCA,
  and the rest of the layer map (`qa-security-shared`). Green TLS ≠ "secure."

## Cross-references

- `qa-security-shared` — the spine: OWASP map (A04/A02), the ticketed-triage discipline, SARIF
  consolidation, the layer map. **Load alongside this skill.**
- `qa-security-testing-zap-baseline-{java,dotnet,typescript}` — the **HTTP security-header** gate
  (HSTS, CSP, cookie flags) — the **adjacent** layer *above* the handshake; ZAP owns headers, this owns
  the TLS handshake/cipher layer. Coordinate on HSTS.
- `qa-security-testing-zap-automation-framework` — the app-layer **active** DAST scan (payloads, never
  prod). Contrast: the TLS scan never sends a payload and is prod-safe.
- `qa/<stack>/skills/security-testing/dependency-scanning` — SCA (A03); orthogonal layer.
- `qa/reporting/<stack>/skills/allure-reporting` — attach the sslyze JSON / testssl.sh HTML report.
- `qa/cicd/<stack>/skills/ci-pipelines/*` + `qa/cicd/ci-conventions` — wire the scheduled/PR job and
  artifact upload.
