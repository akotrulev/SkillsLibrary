---
name: qa-security-testing-container-iac-scanning
description: Trivy (Aqua) as a CI build gate for the layers application-SCA can't see: **container images** (OS packages + app deps + secrets + misconfig in a built image.
---

# Security Testing — Container & IaC Scanning (Trivy)

**Trivy** (Aqua Security) is one language-agnostic Go binary that scans the layers your **application SCA
gate cannot see**: the **base OS image** (`apt`/`apk`/`yum` packages baked into `node:20-slim`,
`mcr.microsoft.com/dotnet/aspnet`, etc.), the **container image as shipped** (every layer, plus embedded
secrets and a misconfigured `USER root`), and **Infrastructure-as-Code** (Terraform, CloudFormation,
Kubernetes manifests, Helm charts, Dockerfiles). It also **generates and scans SBOMs**. It needs **no
running app** and **no per-language split** — a single `docker run` / binary invocation works from any
pipeline, which is why it lives as one shared skill (see `qa-security-shared` on the
language-agnostic-binary shape).

This skill is **lang-agnostic** and pairs with `qa-security-shared` (the OWASP backbone). It owns the
**Trivy invocation, gating flags, SBOM, IaC config scanning, and report parsing**; the master ref owns the
**OWASP map** (esp. **A03 Software Supply Chain Failures**, **A02 Security Misconfiguration**), the
**ticketed-triage discipline**, and **SARIF → code-scanning consolidation** — load it alongside, don't
re-derive it here.

> **⚠️ The SCA boundary — be precise; this is the whole reason both skills exist.** Application
> `dependency-scanning` (`qa-security-testing-dependency-scanning-{java,dotnet,typescript}`) owns
> **application dependency CVEs from the build graph / lockfile** (npm / Gradle / NuGet — direct +
> transitive, gated on a CVSS threshold by the native tool). **This skill owns the three layers SCA is
> blind to:** the **base OS image packages**, the **container image as shipped** (filesystem, embedded
> secrets, image config), and **IaC misconfig**. Trivy `fs`/`image` *can also* read app lockfiles
> (`package-lock.json`, `*.csproj`, `build.gradle`) — that's **real overlap**. The rule: **let one tool own
> app-deps** to avoid double-gating the same CVE in two pipelines (noise, conflicting suppressions, two red
> builds for one fix). Trivy's **unique** value is image / OS / IaC. **Run both layers** — they cover
> orthogonal surfaces; a clean SCA says nothing about a Log4Shell-class CVE in the base image's `openssl`,
> and a clean Trivy image scan says nothing about a header your DAST gate catches.

## Decision matrix — which Trivy target, and Trivy vs dependency-scanning

| Need | Use | Reads | OWASP |
|------|-----|-------|-------|
| Gate a **built container image** (OS packages + secrets + image config + app deps) | `trivy image <ref>` | the built image's layers | A03 / A02 |
| Scan the **working tree / source dir** before a build | `trivy fs .` | filesystem (lockfiles, Dockerfile, IaC, secrets) | A03 / A02 |
| Scan a **remote repo** without cloning | `trivy repo <url>` | the repo's files | A03 / A02 |
| Gate **IaC misconfig** (Terraform / CFN / K8s / Helm / Dockerfile) | `trivy config <dir>` | IaC templates only (no CVEs) | **A02** |
| Audit a **live cluster** | `trivy k8s` | the K8s API + running workloads | A02 / A03 |
| Scan an **existing SBOM** (e.g. a vendor's) | `trivy sbom <file>` | a CycloneDX / SPDX document | A03 |
| **Application** dependency CVEs (build-graph / lockfile, CVSS-gated) | **dependency-scanning** (per stack) | npm / Gradle / NuGet graph | A03 |
| Running-app HTTP surface (headers, injection) | zap-automation-framework | the live app | A02 / A05 |

**Rule of thumb:** **`trivy image`** is the headline gate (scan the artifact you actually ship);
**`trivy config`** is the IaC gate; **`trivy fs`** is the shift-left pre-build pass. Let **per-stack SCA**
own app-dep CVEs; Trivy owns **OS / image / IaC**. Run **both layers**.

## Setup — binary, Docker, or the official action

```bash
# macOS / Linux binary (CI runners can pin a version)
brew install trivy
# or: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v0.65.0

# Docker — no install; mount the workdir + the docker socket to scan a local image
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD:/workdir" -w /workdir \
  aquasec/trivy:0.65.0 image myorg/api:1.4.2

trivy --version
```

> **Pin the version** in CI (`aquasec/trivy:0.65.0`, not `:latest`) so a scanner upgrade is a deliberate,
> reviewable bump — a silent new check turning a green build red is exactly the kind of surprise that gets
> the gate disabled.
>
> **DB caching.** Trivy downloads a vulnerability DB (and, separately, a Java-index / checks DB) on first
> run; cache `~/.cache/trivy` (or the OCI registry mirror via `--db-repository`) so cold runs aren't slow
> and rate-limited — the same NVD-cache discipline `dependency-scanning` calls out.

## The scan commands + gating flags

```bash
# Built image — the headline gate. Scans OS packages, app deps, secrets, AND image misconfig.
trivy image myorg/api:1.4.2

# Filesystem / repo — shift-left, before a build artifact exists.
trivy fs .
trivy repo https://github.com/myorg/api

# IaC misconfiguration — Terraform / CloudFormation / K8s / Helm / Dockerfile.
trivy config ./infra

# Existing SBOM — scan a CycloneDX/SPDX doc (yours or a vendor's) for CVEs.
trivy sbom ./sbom.cdx.json

# Live cluster.
trivy k8s --report summary
```

| Flag | Env equivalent | Effect |
|------|----------------|--------|
| `--exit-code 1` | `TRIVY_EXIT_CODE` | **Exit non-zero when findings match** — this is what fails the pipeline. Default `0` = report-only |
| `--severity HIGH,CRITICAL` | `TRIVY_SEVERITY` | Restrict to these severities (`UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL`). **Always pair with `--exit-code`** so you don't fail on every Low |
| `--ignore-unfixed` | `TRIVY_IGNORE_UNFIXED` | Drop CVEs with **no fix available** — there's nothing to action, so don't block the build on them |
| `--exit-on-eol 1` | — | Fail when the **base image OS is End-of-Life** (no more security patches — a supply-chain liability) |
| `--scanners vuln,secret,misconfig` | `TRIVY_SCANNERS` | Which scanners to run (`vuln`, `secret`, `misconfig`, `license`). `trivy config` implies `misconfig` |
| `--format sarif` / `cyclonedx` / `spdx-json` / `json` / `table` | `TRIVY_FORMAT` | Output format (see Reporting + SBOM below) |
| `--ignorefile .trivyignore` | `TRIVY_IGNOREFILE` | The ticketed suppression file (see Triage) |

The defining trait: **a bare `trivy image` exits 0 even with Critical findings** — it's report-only until
you add `--exit-code 1`. The gate is `--exit-code 1` scoped by `--severity`.

## The two-pass pattern — one informational scan + one gating scan

The classic CI shape (matches the master ref's "gate NEW, surface ALL" discipline): run Trivy **twice** —
once to **show everything** (never fails), once to **gate on what's actionable** (fails the build).

```bash
# Pass 1 — INFORMATIONAL. Full table, every severity, never fails the build (exit 0).
#          Its job is to put the complete picture in the logs / artifact.
trivy image --exit-code 0 --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
  --format table myorg/api:1.4.2

# Pass 2 — GATING. Only actionable High/Critical, drop unfixable, fail on match.
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed \
  --exit-on-eol 1 myorg/api:1.4.2
```

- **Pass 1** is observability: developers see the Low/Medium backlog without it blocking merge.
- **Pass 2** is the gate: `--exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed` fails **only** on
  High/Critical CVEs **that have a fix** — the findings someone can actually act on this PR.
- `--ignore-unfixed` is what keeps the gate trustworthy: blocking on a Critical CVE with **no upstream
  patch** gives the team no move except suppress-it, which trains them to mute the gate. Surface it in
  Pass 1, gate it in Pass 2 only once a fix exists.
- Start lenient and **ratchet**: `--severity CRITICAL` on a legacy image → clear the backlog → tighten to
  `HIGH,CRITICAL`. (Same ratchet as `failBuildOnCVSS` 9.0 → 7.0 in SCA.)

## SBOM & software supply chain (A03)

Trivy both **emits** an SBOM and **scans** one — this is the **A03 Software Supply Chain Failures** layer
(the new 2025 Top-10 category; see the master ref's OWASP map).

```bash
# Generate an SBOM from a built image (attach to the release; feed downstream scanners).
trivy image --format cyclonedx  --output sbom.cdx.json   myorg/api:1.4.2
trivy image --format spdx-json   --output sbom.spdx.json  myorg/api:1.4.2

# Scan a previously-generated SBOM for CVEs (no re-pull of the image needed).
trivy sbom --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed sbom.cdx.json
```

- **CycloneDX** and **SPDX** are the two standard formats — pick whichever your release/attestation
  pipeline consumes (CycloneDX is common for security tooling; SPDX for license/compliance).
- An SBOM is **provenance**: a signed, archived inventory of exactly what shipped in the artifact. When a
  new CVE drops, you scan the **stored SBOM** to answer "are we affected?" without rebuilding or re-pulling
  every old image — the supply-chain answer A03 demands.
- **Generate the SBOM as a release artifact**; scanning it is then cheap and repeatable. No SBOM = no
  supply-chain provenance (an anti-pattern below).

## IaC config scanning (A02 Misconfiguration)

`trivy config` runs the **misconfig** scanner over Infrastructure-as-Code — it finds **no CVEs**; it finds
**insecure settings** (this is the **A02 Security Misconfiguration** layer):

```bash
# Scan an infra dir — Terraform, CloudFormation, K8s manifests, Helm charts, Dockerfiles.
trivy config --exit-code 1 --severity HIGH,CRITICAL ./infra
```

Typical findings: an S3 bucket without encryption, a security group open to `0.0.0.0/0`, a K8s pod running
as `root` / privileged / without `readOnlyRootFilesystem`, a Dockerfile with `USER root` or `ADD` of a
remote URL, a CloudFormation resource missing logging. Trivy ships hundreds of built-in checks (the AVD —
Aqua Vulnerability Database — misconfig policies) and accepts custom **Rego** policies via `--config-check`.

> **Two distinct surfaces — scan both.** `trivy config ./infra` checks the **IaC templates** (the
> *intended* state). `trivy image` *also* runs a misconfig scan over the **built image's** Dockerfile-derived
> config (the *shipped* state — e.g. an image that actually runs as root). A clean Dockerfile lint does not
> mean the running image is configured safely; gate the **built image**, not just the source template (an
> anti-pattern below).

## Triage — ticketed `.trivyignore`, gate NEW

Defer the full discipline to `qa-security-shared` (baseline once → gate NEW hard → every suppression
carries a ticket + reason + expiry → shrink over time). Trivy's mechanism is `.trivyignore` (CVE IDs **and**
IaC check IDs) or the richer `.trivyignore.yaml` with **expiry dates**:

```text
# .trivyignore  — one ID per line; comment with the ticket + reason ABOVE it.
# JIRA-5120: CVE in base-image openssl; upstream image fix pending, re-review 2026-09.
CVE-2024-12345
# JIRA-5121: AVD K8s check accepted — sidecar legitimately needs hostPath; tracked.
AVD-KSV-0121
```

```yaml
# .trivyignore.yaml — richer: per-finding expiry + statement, so suppressions can't rot silently.
vulnerabilities:
  - id: CVE-2024-12345
    statement: "JIRA-5120 — base-image openssl; upstream fix pending"
    expired_at: 2026-09-01           # after this date the CVE fails the build again
misconfigurations:
  - id: AVD-KSV-0121
    statement: "JIRA-5121 — sidecar needs hostPath; accepted risk, re-review Q3"
    expired_at: 2026-09-01
```

```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignorefile .trivyignore.yaml myorg/api:1.4.2
```

- Scope each entry to a **specific CVE or AVD check ID** — never a blanket "ignore all Highs."
- **`expired_at`** time-boxes the suppression (the `.yaml` form) — the same `until=` discipline as the SCA
  suppression XML. After the date the finding re-fails, forcing a re-review instead of a permanent mute.
- **Prefer the real fix** over a suppression: bump the base image tag / pin a patched OS package / fix the
  IaC setting. Suppress only documented, ticketed accepted-risk or false-positives.

## Reporting — SARIF → code-scanning, HTML → Allure

Standardize on **SARIF** for inline PR findings (master-ref discipline); attach a human report to Allure +
CI artifact.

```bash
# SARIF → upload to GitHub code-scanning (inline on the PR diff, de-duped run-over-run).
trivy image --format sarif --output trivy-image.sarif myorg/api:1.4.2

# JSON for programmatic parsing; HTML via the bundled template for humans / Allure.
trivy image --format json --output trivy.json myorg/api:1.4.2
trivy image --format template --template "@contrib/html.tpl" --output trivy.html myorg/api:1.4.2
```

- **SARIF** → `github/codeql-action/upload-sarif` so each finding shows inline on the PR (cross-link
  `qa-ci-pipelines-*`).
- **HTML/JSON** → attach to **Allure** + upload as a CI artifact so a failing run names the findings without
  re-scanning (cross-link `qa-allure-reporting-*`).

### CI wiring — the official `aquasecurity/trivy-action`

```yaml
# .github/workflows/container-scan.yml — cross-link qa-ci-pipelines-*
name: Container & IaC Scan
on: [pull_request]

jobs:
  # Gate the BUILT IMAGE — the artifact we actually ship.
  image-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: docker build -t myorg/api:${{ github.sha }} .
      # Pass 1 — informational (table, never fails): full picture in the logs.
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: image
          image-ref: myorg/api:${{ github.sha }}
          exit-code: '0'
          severity: UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL
          format: table
      # Pass 2 — gating (fails on actionable High/Critical) + SARIF for code-scanning.
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: image
          image-ref: myorg/api:${{ github.sha }}
          exit-code: '1'
          severity: HIGH,CRITICAL
          ignore-unfixed: true
          format: sarif
          output: trivy-image.sarif
        env:
          TRIVY_EXIT_ON_EOL: '1'        # fail on an EOL base image
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: trivy-image.sarif }

  # Gate IaC misconfig — orthogonal to the image scan; run both.
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: config
          scan-ref: ./infra
          exit-code: '1'
          severity: HIGH,CRITICAL
          format: sarif
          output: trivy-config.sarif
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: trivy-config.sarif }
```

The action exposes `scan-type` (`image`/`fs`/`repo`/`config`/`sbom`/`k8s`), `exit-code`, `severity`,
`ignore-unfixed`, and `format`/`output` — the same flags as the CLI. **GitLab CI / Azure Pipelines** run the
identical two-pass via `aquasec/trivy` Docker steps (cross-link `qa-ci-pipelines-{gitlab-ci,azure-pipelines}-*`).

## Anti-patterns

- **Gating with `--exit-code 1` but no `--severity`.** Every `LOW`/`UNKNOWN` fails the build — the team
  bypasses the gate within a day. *Fix:* always scope the gating pass with `--severity HIGH,CRITICAL`; show
  the rest in the informational Pass 1.
- **Not using `--ignore-unfixed`, so unactionable CVEs block merge.** A Critical with **no upstream patch**
  gives developers no move but suppress-it. *Fix:* `--ignore-unfixed` on the gating pass; surface the
  unfixable ones in Pass 1.
- **Double-gating app-deps in both Trivy and the per-stack SCA tool.** The same npm/Gradle/NuGet CVE fails
  two pipelines, needs two suppressions, and produces conflicting noise. *Fix:* let **one** tool own
  app-deps (the per-stack `dependency-scanning` skill); restrict Trivy's value to **OS / image / IaC**
  (`--scanners` / scoping it to the layers SCA can't see).
- **Scanning the Dockerfile but never the built image.** A clean `trivy config` on the Dockerfile says
  nothing about CVEs in the **base image** or what the **shipped** image actually runs as. *Fix:* always run
  `trivy image` on the **built artifact**, not just `trivy config` on the source.
- **Ignoring IaC misconfig entirely.** A perfectly clean image deployed by a Terraform plan that opens a
  security group to `0.0.0.0/0` is still a breach. *Fix:* add the `trivy config ./infra` gate (A02).
- **Blanket `.trivyignore` ("ignore all Highs", or a whole-image ignore).** Buries every future finding,
  including a real one. *Fix:* scope each entry to a **specific CVE / AVD check ID**, with a ticket and an
  `expired_at` expiry; shrink the file, never grow it.
- **Treating an image-clean scan as "the app is secure."** Trivy is blind to broken access control, business
  logic, and the running HTTP surface. *Fix:* run the full layer set per `qa-security-shared` — SCA, DAST,
  access-control matrix; a green Trivy run means the **image / OS / IaC** layers passed, nothing more.
- **No SBOM, so no supply-chain provenance.** When the next Log4Shell drops you can't answer "which shipped
  artifacts are affected?" without rebuilding everything. *Fix:* `--format cyclonedx`/`spdx-json` as a
  release artifact; rescan the stored SBOM when new CVEs land (A03).

## Rules (hard constraints)

- The gate is **`--exit-code 1` scoped by `--severity HIGH,CRITICAL`** (a bare scan is report-only). Run the
  **two-pass** shape: informational Pass 1 (exit 0, full table) + gating Pass 2 (`--exit-code 1
  --severity HIGH,CRITICAL --ignore-unfixed`, `--exit-on-eol 1`).
- **Use `--ignore-unfixed`** on the gating pass — never block the build on CVEs with no available fix.
- **Gate the BUILT IMAGE** (`trivy image`), not just the Dockerfile — and **add the IaC gate**
  (`trivy config ./infra`, A02). Run both; they cover orthogonal surfaces.
- **Own the boundary:** Trivy = **base OS image + container-as-shipped + IaC**; let the per-stack
  `dependency-scanning` skill own **application** dependency CVEs. **Do not double-gate app-deps.** Run both
  layers.
- **Emit an SBOM** (`--format cyclonedx`/`spdx-json`) as a release artifact for **A03** supply-chain
  provenance; rescan the stored SBOM (`trivy sbom`) when new CVEs land.
- **Triage with a ticketed `.trivyignore`/`.trivyignore.yaml`**: scope to a specific CVE/AVD ID, with a
  ticket + reason + **`expired_at`** expiry; gate NEW findings hard; shrink the file (defer the full
  discipline to `qa-security-shared`). Prefer the real fix (bump the base image / fix the IaC setting) over
  a suppression.
- **Emit SARIF** → code-scanning for inline PR findings; attach the HTML/JSON to **Allure** + a CI artifact.
- **Pin the Trivy version** and **cache `~/.cache/trivy`** in CI. **No secrets** (registry creds, tokens) in
  scan config — env vars, read lazily.
- A clean Trivy run ≠ "secure" — it means the **image / OS / IaC** layers passed. Run the full layer set
  (`qa-security-shared`).

## Cross-references

- `qa-security-shared` — the OWASP backbone (A03 Software Supply Chain, A02 Misconfiguration), the
  ticketed-triage discipline, SARIF → code-scanning consolidation, the layer map, and the
  authorization-to-scan rules. **Load alongside this skill** — it owns the concepts this one applies.
- `qa-security-testing-dependency-scanning-{java,dotnet,typescript}` — **application** dependency-CVE SCA
  (build graph / lockfile, CVSS-gated by the native tool). The **boundary partner**: SCA owns app-deps,
  Trivy owns OS image + container + IaC. `trivy fs`/`image` overlap on app lockfiles — let SCA own them.
  **Run both layers.**
- `qa-security-testing-zap-automation-framework` — the **DAST** sibling (running-app HTTP surface);
  orthogonal to image/IaC scanning.
- `qa-ci-pipelines-{github-actions,gitlab-ci,azure-pipelines}-*` + `qa/_shared/ci-conventions` — wire the
  two-pass image + IaC gates, `aquasecurity/trivy-action`, the Trivy DB cache, and the SARIF upload.
- `qa-allure-reporting-*` — attach the Trivy HTML/JSON report to the run.
- `qa/_shared/agents/qa-security.md` — the phased orchestrator that runs this as the **build-artifact gate**
  (Phase 5).
