---
name: qa-security-testing-zap-automation-framework
description: Use when running an ACTIVE / full DAST scan against a running app you own — injecting SQLi/XSS/path-traversal payloads — driven by ZAP's YAML Automation Framework. Never run against production or a shared environment. Triggers "run an active DAST scan", "set up a ZAP full scan", "attack our API from its OpenAPI spec", "add a pre-release DAST gate". Not for the passive PR gate (`zap-baseline`), known CVEs (`nuclei`), or authz (`access-control-testing`).
---

# Security Testing — ZAP Automation Framework (active / full DAST, shared)

The **active-scan** sibling of the passive `qa-security-testing-zap-baseline-*` skills. Where baseline
*observes* a running app and flags what it can see (headers, cookie flags, info leaks) with **no
payloads**, this skill drives the **active scanner** that *injects* SQLi / XSS / path-traversal payloads
to confirm injection-class vulnerabilities — via the modern **YAML Automation Framework (AF)**, the
recommended replacement for the legacy packaged scripts.

This is **language-agnostic** — a `docker run` over a declarative `plan.yaml`, no Java/.NET/TS SDK in the
gate. That is *why* it is one shared skill, not triplicated: there is nothing per-stack to wrap. Load
**`qa-security-shared` alongside it** for the OWASP map, the authorization-to-scan rule, the ticketed-triage
discipline, and SARIF → code-scanning consolidation — this skill does not repeat those tables.

> **Naming / governance.** Refer to it as **"ZAP by Checkmarx (formerly OWASP ZAP)"**. ZAP **left OWASP**
> in 2023 (→ the Software Security Project) and its core developers **joined Checkmarx in Sept 2024**; it
> is **no longer an OWASP project** but remains **free and open-source under Apache-2.0**. The image is
> `ghcr.io/zaproxy/zaproxy:stable`; the binary is `zap.sh`.

## Decision matrix — where the AF active scan fits

| Need | Use | Why |
|------|-----|-----|
| **Active** DAST — inject SQLi/XSS/traversal payloads, confirm injection on a **throwaway env you own** | **this skill (AF `activeScan`)** | The active scanner mutates state; the AF is the modern declarative way to drive it |
| Passive header/cookie/info-leak gate on **every PR** (no payloads, safe, ~1 min) | `qa-security-testing-zap-baseline-{java,dotnet,typescript}` | Passive only — observes, never attacks; right for the per-PR gate |
| Authenticated **API** DAST from an OpenAPI/GraphQL/SOAP/Postman spec | **this skill** (AF importers / `zap-api-scan.py -t … -f openapi -U`) | AF imports the spec, seeds URLs, auto-tunes the active scan for APIs |
| **Schema-driven property fuzzing** (generate cases from the spec, assert 5xx/contract breaks) | `qa-security-testing-api-fuzzing` (Schemathesis) | Property-based fuzzing of the spec, not ZAP's attack rules |
| **Template / known-CVE** scanning of hosts/services | `qa-security-testing-nuclei` | Community CVE/misconfig templates, not a spider+active-rule DAST |
| The OWASP map, scan-authorization rule, triage discipline, SARIF consolidation | `qa-security-shared` | The backbone every security skill hangs off — load it alongside |

**Rule of thumb:** active DAST is **slow, attack-bearing, and unsafe against prod/shared** — it is *not* a
per-PR gate. Run it against an **ephemeral, authorized** environment on a slower cadence (nightly /
pre-release). The passive `zap-baseline` is the every-PR shift-left gate. They are different layers — run
both.

## Setup — Docker only, no language SDK (be honest)

The AF gate is a `docker run` over your `plan.yaml`. There is **no Maven/Gradle/NuGet/npm artifact** that
embeds the active scanner for CI — wrapping a `docker run` gains nothing per stack, which is the whole
reason this is one shared skill. (`org.zaproxy:zap-clientapi` and the language client APIs drive a
*long-running ZAP daemon* — a heavier, different model, not this gate.)

```bash
docker pull ghcr.io/zaproxy/zaproxy:stable     # carries zap.sh + the Automation Framework + legacy scripts

# Run an Automation Framework plan (the modern, recommended path):
docker run --rm -v "$(pwd):/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap.sh -cmd -autorun /zap/wrk/plan.yaml
```

The `/zap/wrk` mount is the work dir ZAP reads the plan from and writes reports to. **Process exit codes**
gate the build: **`0`** success, **`1`** an error occurred, **`2`** at least one job reported a warning.
The fine-grained "fail if there are ≥ N High alerts" gate is a separate concern — see *Exit status &
thresholds* below.

> **Legacy scripts still work, but the AF is the recommended path.** `zap-baseline.py`,
> `zap-full-scan.py`, and `zap-api-scan.py` remain in the image and are fully supported; the AF supersedes
> them with one declarative, version-controllable, composable plan. Prefer the AF for anything beyond the
> simplest one-shot scan (the passive `zap-baseline` skills still use `zap-baseline.py` because that script
> *is* the minimal passive gate). Reach for the API-scan script when you only need its one-line
> spec-import-and-active-scan convenience (see *The API-scan path*).

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The `plan.yaml` walkthrough — AF jobs, top to bottom**.

## ⚠️ Active scan SENDS ATTACK PAYLOADS and MUTATES STATE — authorization is mandatory

> **The `activeScan` job *injects* SQLi / XSS / path-traversal / command-injection payloads and will
> create, mutate, and delete data. It must NEVER run against production or any shared environment.** This is
> the hard `qa-security-shared` authorization-to-scan rule — deferred there, restated loud here because this
> is the skill that actually fires the payloads.

- Active → a **throwaway environment you own and are explicitly authorized to attack**: a
  Testcontainers/docker-compose ephemeral stack, or a dedicated, isolated security-test environment. Spin it
  on a **readiness condition** (compose `--wait` / a Testcontainers wait strategy / an HTTP-health poll loop)
  — **never a fixed sleep** (global rule).
- Confirm the target and authorization **before the first active run**; get it in writing for any hosted
  target. Pointing an active scan at a third party's infrastructure is an attack.
- Exclude destructive paths (logout, account-delete, payment-capture) via `excludePaths` so the spider and
  active scanner don't wreck the session or burn real side effects.
- Contrast the **passive** `zap-baseline` skills: passive-only, no payloads, safe — that is the every-PR
  gate. This skill is the slower, authorized-env-only active layer.

## The API-scan path — `zap-api-scan.py` (the legacy convenience for APIs)

When you only need *import a spec, then active-scan it for APIs*, the packaged API-scan script is a
one-liner that auto-tunes the active scan for API surfaces (it imports the spec, seeds every operation, and
applies an API-appropriate policy). It still ships in the image and is the quickest path for a pure API
target:

```bash
docker run --rm -v "$(pwd):/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py \
    -t https://app.test.internal/openapi.json \   # the spec URL (or local file under /zap/wrk)
    -f openapi \                                   # format: openapi | graphql | soap
    -U \                                           # AUTHENTICATED — auth defined in the context file (-n)
    -n /zap/wrk/api.context \                      # ZAP context (auth, scope) — secrets via env, not committed
    -J zap-api.json -r zap-api.html                # JSON + HTML reports
  # add -S for SAFE mode (passive-only, no attack payloads) when you want a non-mutating API pass
```

- `-f openapi|graphql|soap` selects the importer; `-U` runs **authenticated** (auth comes from the context
  file `-n`); `-S` forces **safe mode** (no active attack — useful for a non-mutating API smoke).
- For anything richer (multiple importers, a custom policy, `replacer` token injection, `alertFilter`
  triage, SARIF) prefer the **AF `plan.yaml`** with the `openapi`/`graphql`/`soap`/`postman` jobs above — the
  API-scan script is the convenience wrapper, the AF is the composable path.

## Authentication — context auth + bearer-token injection, secrets from env

The AF context supports the full range: **form**, **JSON**, **HTTP/NTLM**, **script-based**, and
**browser-based auto-detection** authentication, plus **session management** and **verification** (how ZAP
confirms it is still logged in). The `env.contexts[].authentication` block in the plan above shows the
browser-based path; pick the method that matches the app.

- **Bearer / API tokens**: use the **`replacer`** job (shown above) to inject `Authorization: Bearer …` on
  every request — the simplest path for token-auth APIs. Acquire the token however the project does (see
  `qa-auth0-test-tokens-{java,dotnet,typescript}`).
- **Secrets via env vars, read lazily — never in the committed plan/context.** Reference them as `${ZAP_USER}`
  / `${ZAP_PASS}` / `${ZAP_BEARER}` placeholders; ZAP resolves them from the process environment at run time.
  No credentials in `plan.yaml`, `*.context`, or `cmd_options` (global rule: no secrets in config).
- Always set `verification` (`loggedInRegex`/`loggedOutRegex`) so the scanner re-authenticates instead of
  silently scanning logged-out pages and reporting a false-clean.

## Running it — GitHub Action + raw Docker

CI is the natural home. The official **`zaproxy/action-af`** Action runs an AF plan, uploads the report, and
can open a tracking issue (cross-link `qa-ci-pipelines-{java,dotnet,typescript}` +
`qa-security-shared` for the SARIF upload step):

```yaml
# .github/workflows/zap-active.yml — active DAST on a slower cadence, NOT every PR
name: ZAP Active DAST (Automation Framework)
on:
  schedule: [{ cron: "0 2 * * *" }]      # nightly — active scan is slow + attack-bearing
  workflow_dispatch:
permissions:
  contents: read
  security-events: write                 # required to upload SARIF to code scanning
  issues: write
jobs:
  zap_active:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5          # so the Action can read plan.yaml
      - name: Spin the throwaway target
        run: docker compose -f compose.security.yml up -d --wait   # --wait = readiness, NOT a sleep
      - name: ZAP Automation Framework scan
        uses: zaproxy/action-af@v0.1.0
        with:
          plan: 'plan.yaml'                # the AF plan above (active scan against the ephemeral env)
          token: ${{ secrets.GITHUB_TOKEN }}
          allow_issue_writing: true
          artifact_name: zap-active-report
        env:                               # secrets injected as env — resolved by the ${...} placeholders
          ZAP_USER:   ${{ secrets.ZAP_USER }}
          ZAP_PASS:   ${{ secrets.ZAP_PASS }}
          ZAP_BEARER: ${{ secrets.ZAP_BEARER }}
      - name: Upload SARIF to code scanning
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: zap-active.sarif }
```

Raw Docker (any CI, or local against your own throwaway env):

```bash
docker run --rm \
  --network host \                                  # reach a localhost target on Linux CI; see anti-patterns
  -e ZAP_USER -e ZAP_PASS -e ZAP_BEARER \           # pass secrets through; never bake into the plan
  -v "$(pwd):/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable \
  zap.sh -cmd -autorun /zap/wrk/plan.yaml
echo "exit=$?"     # 0 success · 1 error · 2 warning(s); fine-grained gate from the parsed SARIF/summary
```

> **Reachability is the #1 gotcha.** A `localhost` target *inside* the ZAP container points at the
> container, not your host. On Linux CI use `--network host`; on Mac/Windows use
> `http://host.docker.internal:<port>`; or put ZAP and the SUT on a shared Docker network and target the
> service name. See anti-patterns.

## Reporting / SARIF — code scanning + Allure + artifact

Emit **two** reports from the AF `report` jobs (shown in the plan): a **SARIF** report
(`template: "sarif-json"`) for the machine gate, and a **human** HTML/JSON report.

- **SARIF** → upload to the platform's code-scanning surface (`github/codeql-action/upload-sarif`) so
  findings show **inline on the PR/commit**, de-duplicate run-over-run, and track fixed/new state — the same
  consolidation `qa-security-shared` mandates across every tool.
- **HTML/JSON** → attach to **Allure** + upload as a CI artifact so a failing run names the alerts without
  re-scanning. Cross-link `qa-allure-reporting-{java,dotnet,typescript}`.
- Bake known-noise triage into the **`alertFilter`** job (FPs → "False Positive", must-fix rules raised),
  then gate on **new** High/Medium alerts.

## OWASP mapping

| AF finding class | OWASP | Notes |
|------------------|-------|-------|
| SQLi / XSS / command / path-traversal injection (active rules) | **A05:2025 Injection** / **API8:2023** | the active scanner's core value — confirmed by payload |
| Missing/weak security headers, cookie flags, verbose errors, info leaks | **A02:2025 Misconfiguration** / **API8:2023** | mostly surfaced passively; raise via `alertFilter` |
| Authentication weaknesses on the probed surface | **A07:2025 Authentication Failures** | partial — confirm with functional auth tests |

> The active scan **complements, does not replace** SCA / dependency-scanning (A03), **functional
> access-control testing** (A01 / API1 / API3 / API5 — BOLA/IDOR/BFLA, which scanners are blind to; see
> `qa-security-shared` and the stack-native `access-control-testing`), and **manual penetration testing**
> for business-logic abuse. A clean active scan does **not** mean "secure" — it means the injection-class
> automatable layer passed. State that in every report.

## Anti-patterns

- **Running the active scan against prod or a shared env.** It injects payloads and mutates/destroys data.
  *Fix:* an authorized, **throwaway env you own** (Testcontainers/compose), spun on a readiness condition;
  confirm authorization first. (The hard `qa-security-shared` rule.)
- **Scanning before the app is ready** (sleep-then-scan). Races startup → false-clean / connection errors.
  *Fix:* wait on a **condition** (`compose up --wait` / a Testcontainers wait strategy / an HTTP-health poll
  loop) — never a fixed sleep.
- **Container can't reach the target.** A `localhost` URL inside the ZAP container points at the *container*.
  *Fix:* `--network host` on Linux CI / `http://host.docker.internal:<port>` on Mac/Windows / a shared Docker
  network with the service name.
- **Gating on every alert (or on the raw `2` exit) with no triage.** Every real app lights up; the gate gets
  muted or flaps. *Fix:* `alertFilter` to flip ticketed FPs and raise must-fix rules, then gate on **new**
  High/Medium from the parsed SARIF.
- **Blanket-flipping alerts to "False Positive" to make it green.** Buries real findings. *Fix:* every
  `alertFilter` FP carries a ticket + reason; shrink the list over time (the `qa-security-shared` discipline).
- **Putting credentials/tokens in the committed `plan.yaml` / `*.context`.** *Fix:* `${ENV}` placeholders
  resolved from process env, read lazily; pass secrets via CI secrets → container env.
- **Treating a clean active scan as "secure."** It covers injection-class flaws on the crawled surface only —
  blind to BOLA/IDOR/BFLA and business-logic abuse. *Fix:* pair with SCA, functional access-control tests,
  and a manual pentest.
- **Reaching for the legacy `zap-full-scan.py` when the AF fits.** The packaged scripts are legacy
  (still supported); a `plan.yaml` is version-controllable, composable, and the recommended path. *Fix:* use
  the AF unless you genuinely only need a one-shot script (then `zap-api-scan.py` for APIs).
- **Letting the active scan run unbounded.** It can run for hours. *Fix:* set `maxScanDurationInMins` /
  `maxRuleDurationInMins` and bound the spider durations.

## Rules (hard constraints)

- **Active scan = attack payloads + state mutation.** NEVER against prod or a shared env — only a throwaway
  env you own and are **authorized** to attack, spun on a readiness condition (never a fixed sleep). Defer
  the rule to `qa-security-shared`; obey it here.
- **Prefer the YAML Automation Framework** (`zap.sh -cmd -autorun plan.yaml`) over the legacy packaged
  scripts; reach for `zap-api-scan.py` only for the one-shot API convenience.
- **No language SDK for the gate** — it is a `docker run` over a declarative plan; that is why this is one
  shared skill. (`zap-clientapi` drives a long-running daemon — a different, heavier model.)
- **Bound every duration** (`maxScanDurationInMins`, spider `maxDuration`); solve **container→target
  reachability** explicitly (`--network host` / `host.docker.internal` / shared network).
- **Triage with `alertFilter`** (FP/raise/lower), gate on **new** High/Medium from the **parsed SARIF/summary**
  — the raw exit code (`0`/`1`/`2`) is too coarse on its own (issue #6928).
- **No secrets in the plan/context** — `${ENV}` placeholders, read lazily; secrets via CI → container env.
- **SARIF → code scanning**; HTML/JSON → Allure + CI artifact. A clean active scan ≠ "secure" — pair with
  SCA, functional access-control tests, and manual pentest. Map findings to OWASP (A05/A02/A07 · API8).

## Cross-references

- `qa-security-shared` — **load alongside**: the OWASP map, the authorization-to-scan rule, the ticketed
  triage discipline, and SARIF → code-scanning consolidation this skill defers to (does not repeat).
- `qa-security-testing-zap-baseline-{java,dotnet,typescript}` — the **passive**, every-PR sibling
  (`zap-baseline.py`, no payloads, safe). This skill is the active/AF counterpart; run both, different layers.
- `qa-security-testing-api-fuzzing` — Schemathesis schema-driven property fuzzing (generate cases from the
  spec) — complementary to ZAP's attack-rule DAST.
- `qa-security-testing-nuclei` — template/known-CVE host scanning — a different layer again.
- `qa-auth0-test-tokens-{java,dotnet,typescript}` — acquire the bearer/user tokens the `replacer` job injects.
- `qa-ci-pipelines-{java,dotnet,typescript}` + `qa-security-shared` — the `zaproxy/action-af`
  job, SARIF upload, artifact, slower cadence (nightly/pre-release, not per-PR).
- `qa-allure-reporting-{java,dotnet,typescript}` — attach the HTML/JSON report + alert summary.
