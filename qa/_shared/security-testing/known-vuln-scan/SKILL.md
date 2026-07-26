---
name: qa-security-known-vuln-scan
description: Use when matching a running app or host list against known signatures — CVEs, exposures (leaked `.env`, exposed `/.git`), misconfigurations, and default credentials — using Nuclei's community YAML templates as a fast CI gate. Language-agnostic, any stack. Triggers "scan for known CVEs", "add Nuclei to CI", "check for an exposed .git or .env", "default-credentials scan". Nuclei never spiders or injects — for that use `active-scan`, `api-fuzzing`, or `permission-testing`.
---

# Security Testing — Nuclei (template-based scanner, shared)

**Load `qa-security-shared` alongside this skill.** That master ref carries the OWASP map (Top 10:2025 / API
10:2023 / WSTG / ASVS), the **authorization-to-scan** rule (never run intrusive scans against prod or a
shared env), the **ticketed-triage / suppression** discipline, and **SARIF → code-scanning** consolidation.
This skill carries only the Nuclei-specific invocation, **the honest gating story**, custom-template basics,
template pinning, and reporting.

**Nuclei** (ProjectDiscovery) is a fast, open-source (MIT) **template-matching engine**. You point it at a
target (or a list of targets) and a set of **YAML templates**; for each template it sends the requests the
template declares and applies the template's **matchers** to the responses. The community
`nuclei-templates` repo ships **7,000+** templates (released roughly monthly through late 2025) covering
known **CVEs**, **exposures** (leaked `.env`, exposed `/.git`, open dashboards), **misconfigurations**,
**default-credentials** checks, and **technology/version detection**. Single shared skill — the Go binary,
the `projectdiscovery/nuclei` Docker image, and the Go SDK are all language-agnostic; wrapping it gains
nothing from a three-language split (see `qa-security-shared`'s "one architectural fact").

> **⚠️ Nuclei is a MATCHER, not a crawler — this is the defining fact.** Nuclei does **not** spider the app,
> **does not discover** endpoints, parameters, forms, or cookies, and **does not inject** payloads into
> discovered inputs. It checks the **exact URLs/hosts you give it** against **known signatures** — "is this
> *known-bad thing* present here?" It will happily report a clean run for an app riddled with custom IDOR or
> reflected-XSS-in-an-undiscovered-param, because it was never pointed at those inputs and has no template
> for app-specific logic. That is **not** Nuclei's job. A DAST **crawler** (ZAP) spiders the app and injects
> into discovered params; **API fuzzing** drives the OpenAPI/GraphQL surface. Run Nuclei **alongside** them
> as the fast "known-CVE / known-exposure" layer — complementary, not a replacement. Treating a clean Nuclei
> run as coverage is the #1 misuse.

## Decision matrix — where Nuclei fits

| Need | Use | Why |
|------|-----|-----|
| Fast check for **known** CVEs / exposures / misconfig / default creds / tech-version at given URLs/hosts | **this skill (Nuclei)** | Template matcher — signature-based, fast, huge community template set; no crawl |
| **Spider** a running app, discover params/forms, **inject** SQLi/XSS/traversal into them | `qa-security-active-scan` (DAST crawler) | Nuclei does **not** crawl or discover inputs — a crawler finds what Nuclei can't be pointed at |
| Property-level / schema-aware fuzzing of an **OpenAPI / GraphQL** surface | `qa-security-testing-api-fuzzing` | Spec-driven fuzzing of every operation; Nuclei has no spec model |
| Passive header / cookie-flag / info-leak gate on a running app | `qa/<stack>/skills/security-testing/passive-scan` | ZAP baseline passive rules; overlaps lightly with Nuclei's `misconfiguration/`/`http/` exposure templates |
| Dependency / library CVEs from your **build graph** | `qa/<stack>/skills/security-testing/dependency-scan` | SCA reads the dependency tree; Nuclei detects an *exposed/running* vulnerable component at the HTTP layer — orthogonal |

**Rule of thumb:** Nuclei answers "is a **known** bad thing present at these addresses?" — fast, broad,
signature-based. It is **not** a discovery tool. Always pair it with a crawler (ZAP) and, for APIs,
spec-fuzzing — they cover what a matcher structurally cannot.

## Setup — Go binary, Docker, or the GitHub Action

Language-agnostic; pick one delivery:

```bash
# Go binary (Go 1.21+):
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
nuclei -version

# Docker image:
docker pull projectdiscovery/nuclei:latest        # pin a tag in CI, e.g. :v3.x.y

# First run fetches the community templates to ~/.local/nuclei-templates (or set -update-templates).
nuclei -update-templates
```

There is also a **Go SDK** (`github.com/projectdiscovery/nuclei/v3/lib`) for native embedding inside a Go
service/test — same engine, programmatic results. For CI gating the binary/Docker/Action path is simpler;
reach for the SDK only when you genuinely need in-process integration.

## Invocation — targets, template selection, severity filter

```bash
# Single target, selected template directories:
nuclei -u https://app.example.com \
       -t cves/ -t exposures/ -t misconfiguration/ \
       -s critical,high \
       -jsonl -je results.json -se report.sarif

# A list of targets (one URL/host per line) — Nuclei matches each; it does NOT crawl from them:
nuclei -l targets.txt -t cves/ -t exposures/ -s critical,high -je results.json
```

| Flag | Meaning |
|------|---------|
| `-u <url>` / `-target` | a single target |
| `-l <file>` | a **list** of targets (one per line) — each matched independently, **not** crawled |
| `-t <dir-or-file>` | templates by **directory** (`cves/`, `exposures/`, `misconfiguration/`, `default-logins/`, `technologies/`) or a **single YAML** (repeatable) |
| `-tags <tags>` | select by template tag (e.g. `cve`, `exposure`, `tech`); `-etags` excludes |
| `-s / -severity <list>` | **severity filter**: `info,low,medium,high,critical,unknown` (e.g. `-s critical,high`) |
| `-jsonl` | stream results as **JSON Lines** to stdout (one finding per line) — the gate-parse format |
| `-je <file>` | **JSON export** — write all results to a JSON file |
| `-se <file>` | **SARIF export** — for code-scanning |
| `-o <file>` | plain-text output |
| `-rl / -c` | rate-limit / concurrency (be polite; bound load on the target) |
| `-update-templates` | fetch/refresh the community templates |

**Severity filter** is your first noise control: gate on `critical,high` (and maybe `medium`), never on
`info` (tech-detection / version banners are informational, not findings — see anti-patterns).

## ⚠️ Gating via parsed output — the key gotcha (front and center)

**Be honest: Nuclei's docs do not document a clean, reliable built-in "fail CI on match" exit code** the way
ZAP baseline maps alerts to `0/1/2/3`. A run that finds critical issues can still exit `0`. **Do not gate on
Nuclei's exit code.** Instead, **gate by parsing the output file** — fail the job when it contains any
finding at/above your severity:

```bash
set -euo pipefail
# 1) Run, exporting JSON (and SARIF for code-scanning). Filter severity at scan time.
nuclei -l targets.txt -t cves/ -t exposures/ -t misconfiguration/ \
       -s critical,high \
       -je results.json -se report.sarif || true   # don't trust the exit code — see below

# 2) Gate on the parsed export: fail if any high/critical finding exists.
#    -je writes a JSON array of result objects; each has .info.severity.
count=$(jq '[.[] | select(.info.severity == "critical" or .info.severity == "high")] | length' results.json)
echo "nuclei high/critical findings: $count"
if [ "$count" -gt 0 ]; then
  echo "::error::Nuclei found $count high/critical issue(s) — failing the build"
  jq -r '.[] | select(.info.severity=="critical" or .info.severity=="high")
              | "[\(.info.severity)] \(.["template-id"]) @ \(.host // .matched-at)"' results.json
  exit 1
fi
```

- With **`-jsonl`** (JSON Lines, one object per line) the gate is `jq -s 'length'` over the stream, or count
  non-empty lines; with **`-je`** (a JSON array) use `jq 'length'` / a `select(...)` filter as above.
- The principle: **the export file being non-empty at/above your gating severity is the fail condition** —
  you own the gate in the pipeline, not in Nuclei's exit status.
- Some versions expose an **`-exit-on-match`-style** flag (the project has added match-aware exit behavior
  over time). **Verify it exists and behaves as expected on your *installed/pinned* version before relying on
  it** — and even then, keep the parsed-export gate as the source of truth so the gate is reproducible and
  version-independent. Do not assume the flag from memory.

This parsed-export gate is the same shape across the Go binary, Docker, and the Action.

## Custom templates (brief)

A Nuclei template is a YAML file declaring an `id`, `info` (with **`severity`**), the requests to send, and
the **matchers** that decide a hit. Add org-specific exposure/misconfig checks alongside the community set
and select them with `-t ./my-templates/`:

```yaml
# my-templates/exposed-internal-actuator.yaml
id: exposed-internal-actuator-env
info:
  name: Spring Boot Actuator /env exposed publicly
  author: platform-sec
  severity: high                       # drives the -s filter and the gate
  tags: exposure,misconfig,actuator
http:
  - method: GET
    path:
      - "{{BaseURL}}/actuator/env"
    matchers-condition: and
    matchers:
      - type: status
        status: [200]
      - type: word
        part: body
        words: ["activeProfiles", "propertySources"]
```

Keep custom templates in your repo, version them with your code, and contribute generic ones upstream where
sensible. The community templates and the template syntax reference live in the
[`nuclei-templates`](https://github.com/projectdiscovery/nuclei-templates) repo and the
[templating docs](https://docs.projectdiscovery.io/templates/introduction).

## Template pinning — reproducible CI gates

`nuclei -update-templates` pulls the **latest** community templates. In CI that means **the gate changes
run-over-run without a code change** — a new template release can light up a previously-green build (or
silently drop a check). **Pin the template version** for reproducibility:

- Pin the **template release tag** (`-tv / -template-version` or a checked-out `nuclei-templates` ref via
  `-update-template-dir` / `-t <pinned-path>`) and bump it deliberately in a PR, the same way you bump a
  dependency. Treat a template bump as a reviewable change, not an invisible auto-pull.
- Pin the **Nuclei engine** too — a fixed Docker tag (`projectdiscovery/nuclei:v3.x.y`), not `:latest`.
- The point mirrors the SCA discipline: a security gate must be **deterministic** so a red build means a real
  regression, not a template-set drift.

## ⚠️ Intrusive templates — run only against a safe env you own

Most community templates are **passive detection / CVE-match** checks (lighter, low-impact). But some are
**active/intrusive**: templates tagged `dast`/`fuzz`, and **`default-logins/`** checks that *attempt a real
login* with default credentials, send payloads or mutate state. Those are **attack traffic**.

> **Defer to `qa-security-shared`'s authorization-to-scan rule:** intrusive templates (`-tags dast,fuzz`,
> default-cred attempts, anything that sends payloads) **must never run against production or a shared
> environment** — only against a throwaway env you own and are authorized to attack.
> For a per-PR gate, prefer the **passive detection / CVE-match**
> template set (e.g. `cves/`, `exposures/`, `misconfiguration/`, `technologies/`) and exclude intrusive tags
> (`-etags dast,fuzz`). Get authorization in writing for any hosted target.

## Reporting — SARIF → code-scanning, JSON → Allure + CI artifact

- **`-se report.sarif`** → upload to the platform's **code-scanning** surface
  (`github/codeql-action/upload-sarif`) so findings appear inline on the PR diff and de-duplicate
  run-over-run (see `qa-security-shared`'s SARIF consolidation).
- **`-je results.json`** → attach to **Allure** (`qa/reporting/<stack>/skills/test-reports`) and upload as a CI
  artifact so a failing run names the findings (template id, severity, matched-at) without re-scanning.

```yaml
# .github/workflows/nuclei.yml — Action + jq gate
name: Nuclei Scan
on: [pull_request]
jobs:
  nuclei:
    runs-on: ubuntu-latest
    permissions:
      security-events: write          # to upload SARIF
    steps:
      - uses: actions/checkout@v5     # so the Action can read ./my-templates and targets.txt
      - name: Start the app (safe, throwaway env)
        run: docker compose up -d --wait      # --wait blocks on healthchecks, never a sleep
      - name: Nuclei scan
        uses: projectdiscovery/nuclei-action@v3
        with:
          target: 'http://localhost:8080'
          # passive/CVE-match set; exclude intrusive tags for a PR gate:
          flags: "-t cves/ -t exposures/ -t misconfiguration/ -etags dast,fuzz -s critical,high -je results.json -se report.sarif"
      - name: Gate on parsed export (do NOT trust the exit code)
        run: |
          count=$(jq '[.[] | select(.info.severity=="critical" or .info.severity=="high")] | length' results.json)
          echo "high/critical: $count"
          [ "$count" -eq 0 ] || { jq -r '.[] | "[\(.info.severity)] \(.["template-id"]) @ \(.host // .matched-at)"' results.json; exit 1; }
      - name: Upload SARIF to code scanning
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: report.sarif }
      - name: Upload report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with: { name: nuclei-report, path: results.json }
```

(The `projectdiscovery/nuclei-action` wraps the image; the plain `projectdiscovery/nuclei` Docker image with
the same flags works identically — the language-agnostic point.)

## OWASP mapping

| Nuclei finds | OWASP (Top 10:2025) | Note |
|--------------|---------------------|------|
| Exposures, default panels, missing controls, info leaks | **A02 Security Misconfiguration** | `exposures/`, `misconfiguration/`, `default-logins/` |
| Known **CVEs** at the HTTP layer | **A05 Injection / known-vuln** & **A06 Insecure Design** surfacing of a known flaw | `cves/` — matches a *known* signature, not a discovered injection point |
| Outdated / **known-vulnerable component** detected as exposed/running | **A03 Software Supply Chain Failures** | HTTP-layer detection of a vulnerable component; complements **SCA** (build-graph), doesn't replace it |

Map each gating template/tag to its OWASP item per `qa-security-shared` so coverage is auditable. Nuclei
covers the **known-signature** slice of A02/A03/A05 — never the access-control (A01) or business-logic
(API6) slices a matcher is structurally blind to.

## Anti-patterns

- **Assuming a native fail-on-match exit code.** Nuclei docs don't document a reliable one; a critical
  finding can still exit `0`. *Fix:* gate by **parsing `-je`/`-jsonl`** — non-empty at/above your severity →
  `exit 1`. Verify any `-exit-on-match`-style flag per installed version, and keep the parse-gate anyway.
- **Relying on a matcher for a crawler's coverage.** Nuclei doesn't spider, discover params/forms, or inject
  — a clean run says nothing about custom IDOR/XSS in undiscovered inputs. *Fix:* pair with
  `qa-security-active-scan` (crawl + inject) and `qa-security-testing-api-fuzzing`.
- **Unpinned templates changing the gate.** `-update-templates` pulls latest → a green build goes red (or a
  check vanishes) with no code change. *Fix:* pin the template release tag and bump it in a reviewable PR;
  pin the engine tag too (no `:latest`).
- **Gating on info-severity noise.** Tech-detection / version banners are `info` — gating on them makes the
  gate red forever and gets it muted. *Fix:* `-s critical,high` (maybe `medium`); treat `info` as inventory,
  not a finding.
- **Running intrusive templates against prod/shared.** `default-logins/` (attempts real logins),
  `-tags dast,fuzz` send attack traffic / mutate state. *Fix:* run those only against a throwaway env you
  own and are authorized to attack; for a PR gate use the passive/CVE-match set + `-etags dast,fuzz`.
- **Treating a clean Nuclei run as "secure."** It means *no known signature matched at the URLs you gave it*
  — nothing about access control, business logic, or undiscovered inputs. *Fix:* run the full layer set
  (`qa-security-shared`'s layer map); never imply green = secure.
- **Not pinning the template version (reproducibility).** Even without `-update-templates`, an unpinned
  `nuclei-templates` checkout drifts. *Fix:* pin a template ref; the gate must be deterministic so red = real
  regression.
- **Scanning before the app is ready** (sleep-then-scan). Races startup → false-clean. *Fix:* `compose up
  --wait` / a Testcontainers wait strategy — never a fixed sleep (global rule).
- **Committing target auth tokens / API keys in flags or templates.** *Fix:* env vars read lazily; no secrets
  in scan config (`qa-security-shared`).

## Rules (hard constraints)

- **The gate is a parsed-output assertion, not the exit code.** Run with `-je`/`-jsonl`, then fail the job
  when the export is non-empty at/above your gating severity (`jq` count). Verify any `-exit-on-match`-style
  flag per installed version before trusting it; keep the parse-gate as the source of truth.
- **Nuclei is a matcher, not a crawler** — it doesn't discover params/forms or inject. Pair it with a DAST
  crawler (`active-scan`) and API fuzzing; a clean run is not coverage.
- **Filter severity** (`-s critical,high`); never gate on `info`.
- **Pin the template release and the engine version** so the gate is deterministic run-over-run; bump in a
  reviewable PR.
- **Intrusive templates** (`-tags dast,fuzz`, `default-logins/` login attempts) run **only** against a
  throwaway env you own and are authorized to attack — never prod/shared (defer to `qa-security-shared`).
- The app must be **ready** before scanning — wait on a **condition** (`compose up --wait` / a wait
  strategy), never a fixed sleep.
- **No secrets in scan config** — auth tokens/keys via env vars, read lazily.
- Emit **SARIF → code-scanning** + attach the JSON report to **Allure** and CI artifact. Map gating templates
  to their OWASP item. A clean Nuclei run ≠ "secure" — run the full layer set and reserve business-logic /
  access-control to functional tests + manual pentest.

## Cross-references

- `qa-security-shared` — **load alongside.** OWASP map, authorization-to-scan rule, ticketed-triage
  discipline, SARIF → code-scanning consolidation, the layer map placing Nuclei as the "Templates/CVE" row.
- `qa-security-active-scan` — the DAST **crawler** Nuclei is **not**: spiders + injects
  into discovered params/forms. Run both — a matcher can't find what it isn't pointed at.
- `qa-security-testing-api-fuzzing` — spec-driven OpenAPI/GraphQL property-level fuzzing; the other layer a
  matcher can't reach.
- `qa/<stack>/skills/security-testing/passive-scan` — passive header/cookie/info-leak gate (lightly overlaps
  Nuclei's `misconfiguration/` exposure templates; different engine).
- `qa/<stack>/skills/security-testing/dependency-scan` — **SCA** (build-graph CVEs); Nuclei detects an
  *exposed/running* vulnerable component at the HTTP layer. Orthogonal — run both.
- `qa/cicd/<stack>/skills/ci-pipelines/*` + `qa/cicd/ci-conventions` — wire the job, the jq gate, and the SARIF
  upload.
- `qa/reporting/<stack>/skills/test-reports` — attach the JSON report and a finding summary.
- `qa/manual/bug-report-writer` — write up a confirmed Nuclei finding for the dev team.
