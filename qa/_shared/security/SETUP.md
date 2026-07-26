# Security Testing — Setup & Prerequisites

How to set up and run the `security-testing` family — the `qa-security` agent, the language-agnostic scanner
skills (`qa/_shared/security-testing/*`), and the stack-native skills
(`qa/<stack>/skills/security-testing/*`). Read `qa/_shared/security/SKILL.md` first for the *why* (the OWASP
map, the automatable-vs-manual boundary, the authorization rule); this file is the *how* (install, configure,
invoke).

> **The golden rules before anything runs** (full detail in `SKILL.md`):
> 1. **Never run an active/attack scan against production or a shared environment.** Active scans (ZAP
>    active/AF, Schemathesis fuzzing, intrusive Nuclei templates, sqlmap) go only against a **throwaway env you
>    own and are authorized to attack**. Passive scans (ZAP baseline, SAST, secrets, SCA, TLS) are safe.
> 2. **No secrets in code or config.** Every token/key/password below comes from an **environment variable**,
>    read lazily — never committed to a plan/context/workflow file.
> 3. **A green pipeline ≠ "secure."** It means the automatable layers passed. Business-logic abuse still needs
>    a manual pentest.

---

## 0. Common prerequisites (almost everything needs these)

| Prerequisite | Why | Install / check |
|---|---|---|
| **Docker** | Most scanners run as a Docker image (no language SDK) | `docker --version` · daemon running on the CI runner |
| **The repo checked out** | SAST / secrets / SCA / IaC read the source & git history | `actions/checkout@v5` **with `fetch-depth: 0`** for full-history secrets scans |
| **CI code-scanning surface** *(recommended)* | SARIF → inline PR findings | GitHub `github/codeql-action/upload-sarif` · GitLab security reports |
| **A secret store** | Tokens/keys for authenticated scans & access-control | CI secrets (`${{ secrets.* }}`) → env vars at runtime |

**Stack detection (the agent does this first):** the stack-native skills live under `qa/typescript`,
`qa/dotnet`, or `qa/java`. Identify the test project's language/build file and use the matching siblings; the
`_shared` scanner skills are stack-independent.

---

## 1. Language-agnostic scanner skills (`qa/_shared/security-testing/`)

Each is a Docker/CLI binary. Install the tool, supply its env vars, point it at its target, gate on its
output. The skill file for each carries the full flag reference, the triage-suppression model, and
anti-patterns.

### SAST — `sast` (Opengrep / Semgrep)
- **Install:** `pip install semgrep` **or** Opengrep (the truly-OSS fork) per opengrep.dev · Docker
  `semgrep/semgrep` · Action `semgrep/semgrep-action`. CLI is invocation-compatible between the two.
- **Target:** your source tree (static — no running app).
- **Run/gate:** `semgrep scan --config p/owasp-top-ten --config p/security-audit --error --sarif -o sast.sarif`
  (the `--error` flag is what makes it fail the build) — or `semgrep ci` (fails on findings by default).
- **Env vars:** none required for the OSS rulesets. `SEMGREP_APP_TOKEN` only if using the hosted platform.
- **Config files:** `.semgrepignore` (ticketed), inline `// nosemgrep: <rule>` with a ticket.

### Secrets — `secrets-scan` (Gitleaks + TruffleHog)
- **Install:** Gitleaks — binary / `brew install gitleaks` / Docker `zricethezav/gitleaks` / `gitleaks/gitleaks-action`.
  TruffleHog — `trufflesecurity/trufflehog` Docker / action.
- **Target:** the repo **including git history** (checkout with `fetch-depth: 0`).
- **Run/gate:** `gitleaks detect --report-format sarif --report-path gitleaks.sarif` (exit 1 on findings);
  `trufflehog git file://. --results=verified` (live-verified secrets only → low noise).
- **Env vars:** none to scan. A **verified** true-positive means **rotate the credential** (deleting the line
  isn't enough — it's in history).
- **Config files:** `.gitleaks.toml` (allowlist) + `--baseline-path`. Add a pre-commit hook for Gitleaks.

### SCA — `dependency-scan` *(stack-native — §2)*

### Container / IaC — `image-infra-scan` (Trivy)
- **Install:** `brew install trivy` / Docker `aquasecurity/trivy` / Action `aquasecurity/trivy-action`.
- **Target:** a **built image** (`trivy image myorg/app:tag`), the filesystem (`trivy fs .`), or IaC
  (`trivy config ./infra`).
- **Run/gate:** `trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed myorg/app:tag`;
  SBOM `trivy image --format cyclonedx -o sbom.json myorg/app:tag` (A03 supply chain).
- **Env vars:** none required. `GITHUB_TOKEN` raises the DB rate limit on busy runners.
- **Config files:** `.trivyignore` (CVE/check IDs, ticketed, with expiry).

### DAST (active) — `active-scan` (ZAP by Checkmarx)
- **Install:** `docker pull ghcr.io/zaproxy/zaproxy:stable` · Action `zaproxy/action-af`.
- **⚠️ Target:** a **running app on an authorized throwaway env only** — it injects attack payloads.
- **Run/gate:** write a YAML automation plan, then
  `docker run -v $(pwd):/zap/wrk ghcr.io/zaproxy/zaproxy:stable zap.sh -cmd -autorun /zap/wrk/plan.yaml`
  (exit 0/1/2; set the exit on alert thresholds in the plan). API scan: `zap-api-scan.py -t <openapi-url> -f openapi -U`.
- **Env vars:** auth tokens injected via the plan's `replacer` job from env (e.g. `ZAP_AUTH_TOKEN`) — never in
  the committed plan/context.
- **Reachability:** container → target on Linux CI uses `--network host`; on Mac/Windows `host.docker.internal`.

### API fuzzing — `api-fuzzing` (Schemathesis)
- **Install:** `pip install schemathesis` / Docker `schemathesis/schemathesis` / Action `schemathesis/action@v3`.
- **⚠️ Target:** a **running app on a safe env** + its OpenAPI/GraphQL schema (it sends generated requests).
- **Run/gate:** `schemathesis run http://localhost:8080/openapi.json --report junit` (non-zero exit on failure).
- **Env vars:** `--header "Authorization: Bearer $API_TOKEN"` with `API_TOKEN` from env. Use a seeded test
  tenant; clean up after.

### Templates / CVE — `nuclei` (ProjectDiscovery)
- **Install:** `go install …/nuclei/v3/cmd/nuclei@latest` / Docker `projectdiscovery/nuclei` / Action
  `projectdiscovery/nuclei-action`.
- **Target:** a URL/host (`-u https://app`). Intrusive templates → safe env only.
- **Run/gate:** `nuclei -u http://localhost:8080 -t cves/ -t exposures/ -s critical,high -je nuclei.json`,
  then **fail the job if the output is non-empty** (Nuclei has no reliable native fail-on-match exit — gate by
  parsing `-jsonl`/`-je`/`-se`). **Pin the template version** for a stable gate (`nuclei -update-templates` is
  non-deterministic run-over-run).
- **Env vars:** none required.

### TLS — `certificate-scan` (sslyze + testssl.sh)
- **Install:** `pip install sslyze` · testssl.sh — clone / Docker `drwetter/testssl.sh`.
- **Target:** a TLS endpoint — **prod-safe** (a read-only handshake probe), good as a pre-release/scheduled gate.
- **Run/gate:** `sslyze --mozilla_config=intermediate --json_out tls.json example.com:443` (non-zero exit on
  Mozilla non-compliance — the cleaner native gate). testssl.sh: parse the JSON and fail on `severity >= HIGH`.
- **Env vars:** none required.

---

## 2. Stack-native skills (`qa/<stack>/skills/security-testing/`)

These are real test code in your project, so they need the project's test stack wired up.

### `permission-testing` — the BOLA/IDOR/BFLA authorization matrix (the centerpiece)

This is the highest-setup, highest-value skill. It needs:

1. **The project's API client + DTO layer** — reuses `{resource}Client` (raw + typed overloads) and DTOs from
   `qa/<stack>/skills/api-client-writer` + `api-models`. Build those first if absent.
2. **Multiple seeded test identities** — at minimum **two peer users** (same role, different ownership — for
   horizontal/BOLA) **+ one elevated role** (admin — for vertical/BFLA). Seed them in the target env.
3. **Per-actor tokens via `qa/<stack>/skills/test-login-tokens`** — typically ROPG to mint a token *as a
   specific seeded user*. Requires these env vars (never committed):

   | Env var | Purpose |
   |---|---|
   | `AUTH0_DOMAIN` | tenant domain |
   | `AUTH0_CLIENT_ID` / `AUTH0_CLIENT_SECRET` | the test app's credentials |
   | `AUTH0_AUDIENCE` | the API audience |
   | `ALICE_USERNAME` / `ALICE_PASSWORD`, `BOB_*`, `ADMIN_*` | the seeded test users (ROPG) |

   (ROPG must be explicitly enabled on the tenant — see the `test-login-tokens` skill's security caveat.)
4. **The project's 403-vs-404 leak policy decided** — does cross-tenant access return `403` (confirms
   existence) or `404` (hides it)? The `expectDenied(status)` helper codifies whichever you choose.
5. **Run:** it's just your test runner — `npx vitest` / `dotnet test` / `./gradlew test`. No external service.

### `dependency-scan` — SCA (per package manager)
- **TypeScript:** `npm audit` (+ the skill's gating wrapper). **.NET:** `dotnet list package --vulnerable`.
  **Java:** OWASP Dependency-Check Gradle/Maven plugin (`dependencyCheckAnalyze`, `failBuildOnCVSS`).
- **Env vars:** Dependency-Check benefits from an `NVD_API_KEY` to avoid NVD rate limits.
- **Config:** a ticketed suppression file per tool.

### `passive-scan` — passive DAST (already in the library)
- Same `ghcr.io/zaproxy/zaproxy:stable` image; passive only (safe every PR). See its per-stack skill for the
  `ProcessBuilder`/`Process`/`child_process` wrapper.

---

## 3. Invoking the agent vs a single skill

**To run the whole orchestrated flow** — invoke the **`qa-security`** agent (`qa/_shared/agents/qa-security.md`).
Give it: the **target app/API**, the **environment + written authorization** for any active scan, the project
**stack**, and the **OWASP scope / ASVS level** if known. It runs the six phases (threat-model → static gates →
access-control → dynamic gates → container/IaC → review + CI + OWASP coverage report), loading each skill as it
goes, and asks before any active scan.

**To run one layer** — load just that skill's `SKILL.md` and follow it. E.g. "set up a secrets-scan gate" →
`qa/_shared/security-testing/secrets-scan`; "test for IDOR" → `qa/<stack>/skills/security-testing/permission-testing`
(+ `qa/_shared/security` alongside).

**Minimal every-PR baseline** (cheap + safe, no authorization needed): SAST + secrets + SCA + access-control +
ZAP **baseline**. Add the active layers (ZAP-AF, fuzzing, Nuclei) on a safe env at a slower cadence.

---

## 4. Pre-flight checklist

- [ ] Docker available on the runner; repo checked out with `fetch-depth: 0` for secrets.
- [ ] Stack identified; `api-client-writer`/`api-models`/`test-login-tokens` present for access-control.
- [ ] All tokens/keys/passwords in the secret store → env vars (nothing committed).
- [ ] For **any active scan**: target is a disposable env you own, **authorization confirmed** (in writing for
      a hosted target), app is **ready** (wait strategy, not `sleep`).
- [ ] Triage baselines created (`.semgrepignore`, `.gitleaks.toml`, `.trivyignore`, ZAP `rules`/alertFilter) —
      gate **NEW** findings, every suppression ticketed.
- [ ] SARIF uploaded to code-scanning; human reports attached to Allure + CI artifact.
- [ ] Nuclei templates pinned; TLS Mozilla profile pinned.
- [ ] Report states what was covered **and** what was left to a manual pentest.

---

## Cross-references

- `qa/_shared/security/SKILL.md` — the OWASP backbone & rationale (read first).
- `qa/_shared/security-testing/*/SKILL.md` — per-scanner full flag/gating/triage detail.
- `qa/<stack>/skills/security-testing/{permission-testing,dependency-scan,passive-scan}` — stack-native.
- `qa/_shared/agents/qa-security.md` — the orchestrator.
- `qa/<stack>/skills/{test-login-tokens,api-client-writer,api-models,ci-pipelines/*,test-reports}` + `qa/cicd/ci-conventions` — the supporting setup.
</content>
