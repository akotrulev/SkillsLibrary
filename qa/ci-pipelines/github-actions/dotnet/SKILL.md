---
name: qa-ci-pipelines-github-actions-dotnet
description: Use when the user asks to author or fix a GitHub Actions workflow for running .NET QA suites — sharded NUnit / Playwright runs via `strategy.matrix`, Testcontainers integration tests, Allure publish to GitHub Pages with history, TRX / coverage upload + check summary, OIDC-based secret retrieval (`permissions: id-token: write`, no PATs), perf gate against k6 thresholds, artifact retention for videos / traces / HAR. Triggers: "GitHub Actions workflow for the API tests", "shard our UI tests across N runners", "add Allure to the Actions pipeline", "wire OIDC to Azure for the test workflow", "publish the test report to GitHub Pages", "fail the build when k6 thresholds break". Do NOT use for Azure Pipelines (`qa/ci-pipelines/azure-pipelines/dotnet`), GitLab CI (`qa/ci-pipelines/gitlab-ci/dotnet`), deployment-only workflows (`devops/github-actions`), or non-QA app builds. For Java / TypeScript test suites use the `java` or `typescript` sibling under this skill.
---

# QA — GitHub Actions for .NET Test Suites

Authors `.github/workflows/*.yml` that run NUnit / Playwright / Testcontainers-backed integration tests on GitHub-hosted `ubuntu-latest` runners, shard for speed via `strategy.matrix`, publish Allure to GitHub Pages with history, fail on real failures (not flakes), and pull secrets via OIDC federated credentials rather than PATs or stored cloud secrets.

This is a port of `qa/ci-pipelines/azure-pipelines/dotnet` to GitHub Actions idioms — same patterns (shard, OIDC, Allure history, TRX upload, retry policy, perf gate), re-expressed for the Actions runtime.

## When to use

- New QA workflow for a .NET test project (`ApiTests`, `UiTests`, `IntegrationTests`)
- Adding `strategy.matrix` sharding to an existing serial workflow
- Wiring Allure publish + history to GitHub Pages (or an artifact)
- Replacing stored cloud secrets / PATs with OIDC federated credentials
- Adding a perf gate (k6 / NBomber) that breaks the build on SLO regression

## When NOT to use

- Azure Pipelines equivalent → `qa/ci-pipelines/azure-pipelines/dotnet`
- GitLab CI equivalent → `qa/ci-pipelines/gitlab-ci/dotnet`
- App build / deploy workflows unrelated to tests → `devops/github-actions`
- Non-.NET stacks — use the `java` or `typescript` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test projects? (`ApiTests`, `IntegrationTests`, `UiTests`, multiple)
2. Sharding fan-out? (default: 4 runners for UI, 2 for API/integration, 1 for perf)
3. Allure history destination? (default: GitHub Pages via `gh-pages` branch with `keep_files`; artifact-only when Pages is unavailable)

Infer everything else from `.csproj` files and any existing workflows under `.github/workflows/`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `ubuntu-latest` (Docker pre-installed) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| Triggers | `pull_request: [main]` + nightly `schedule` cron | `push` on main only when the suite is < 5 min |
| Test framework reporter | `--logger "trx"` + Allure NUnit adapter | Always both — TRX feeds `dorny/test-reporter`, Allure feeds humans |
| Sharding | `strategy.matrix` with `fail-fast: false` | Playwright uses `--shard=i/N`; raw category split via `NUnit.Where` for NUnit |
| Auth to Azure / AWS / Key Vault | OIDC federated credential (`id-token: write`) | Never PATs, never stored long-lived cloud secrets |
| Retry on failure | **Off at the workflow level** (no `nick-fields/retry` on the test step) | Per-test `[Retry(2)]` only for documented network-flake hotspots — never blanket retry |
| Concurrency | `concurrency` group per ref, `cancel-in-progress: true` for PRs | Keep nightly runs un-cancelled (`cancel-in-progress: false`) |
| Artifact retention | 14 days for traces/videos/HAR, 30 days for TRX, Allure history persisted on `gh-pages` | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | k6 thresholds → script exit code → step fails | Soft gate (`continue-on-error`) only while a baseline is being established |

## Templates

### Top-level workflow — `.github/workflows/qa-tests.yml`

```yaml
name: QA Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 2 * * *"   # nightly full suite
  workflow_dispatch:

# Cancel superseded PR runs; never cancel nightly.
concurrency:
  group: qa-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

permissions:
  contents: read
  checks: write          # dorny/test-reporter publishes a Checks summary
  id-token: write        # OIDC token for azure/login — NOT repo write

env:
  DOTNET_VERSION: '8.0.x'
  BUILD_CONFIGURATION: Release
  DOTNET_NOLOGO: 'true'
  DOTNET_CLI_TELEMETRY_OPTOUT: 'true'

jobs:
  api-tests:
    uses: ./.github/workflows/_api-tests.yml
    with:
      shard-total: 2
    secrets: inherit

  integration-tests:
    uses: ./.github/workflows/_integration-tests.yml
    secrets: inherit

  ui-tests:
    uses: ./.github/workflows/_ui-tests.yml
    with:
      shard-total: 4
    secrets: inherit

  perf:
    needs: api-tests
    if: github.event_name == 'schedule'
    uses: ./.github/workflows/_k6-perf.yml
    secrets: inherit

  publish-allure:
    needs: [api-tests, integration-tests, ui-tests]
    if: ${{ !cancelled() }}     # publish even when a test job failed
    uses: ./.github/workflows/_allure-publish.yml
```

`if: ${{ !cancelled() }}` is the Actions equivalent of `condition: always()` minus the cancelled case — you want the report on red, but not on a user-cancelled run.

### Sharded NUnit job — `.github/workflows/_api-tests.yml`

```yaml
on:
  workflow_call:
    inputs:
      shard-total:
        type: number
        default: 2

jobs:
  api-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false       # one shard failing must not kill the others
      matrix:
        shard-index: [1, 2]  # length MUST equal shard-total
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }

      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      # OIDC → Azure, then pull secrets from Key Vault. No stored secrets.
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Fetch test secrets from Key Vault
        run: |
          echo "API_BASE_URL=$(az keyvault secret show --vault-name kv-qa --name api-base-url --query value -o tsv)" >> "$GITHUB_ENV"
          SECRET=$(az keyvault secret show --vault-name kv-qa --name auth0-m2m --query value -o tsv)
          echo "::add-mask::$SECRET"
          echo "AUTH0_M2M_SECRET=$SECRET" >> "$GITHUB_ENV"

      - name: Run API tests (shard ${{ matrix.shard-index }}/${{ inputs.shard-total }})
        run: |
          dotnet test ApiTests/ApiTests.csproj \
            --configuration "$BUILD_CONFIGURATION" \
            --logger "trx;LogFileName=api-shard-${{ matrix.shard-index }}.trx" \
            --logger "console;verbosity=minimal" \
            --results-directory "$RUNNER_TEMP/TestResults" \
            --collect:"XPlat Code Coverage" \
            -- NUnit.NumberOfTestWorkers=1 \
               NUnit.Where="cat != Slow and cat != Perf and (test % ${{ inputs.shard-total }} == ${{ matrix.shard-index }} - 1)"

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: API shard ${{ matrix.shard-index }}
          path: ${{ runner.temp }}/TestResults/*.trx
          reporter: dotnet-trx
          fail-on-error: true        # red the check on real test failures

      - name: Upload TRX + coverage
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: api-trx-${{ matrix.shard-index }}
          path: ${{ runner.temp }}/TestResults
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: allure-results-api-${{ matrix.shard-index }}
          path: ApiTests/allure-results
          retention-days: 30
```

`NUnit.Where="test % N == i"` is a stand-in — replace with your real shard predicate (category split, fixture-name hash, or a pre-computed bin file). The `matrix.shard-index` array length **must equal** `shard-total`; GitHub Actions has no `parallel: N` shorthand, so the array is the source of truth. For dynamic sharding, compute the matrix in an upstream job and pass it via `fromJSON(needs.setup.outputs.matrix)`.

### Integration tests with Testcontainers — `.github/workflows/_integration-tests.yml`

GitHub-hosted Ubuntu runners have Docker pre-installed and the runner user is in the `docker` group — no DinD service or `--privileged` setup needed. Testcontainers and its Ryuk reaper work out of the box.

```yaml
on:
  workflow_call:

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - name: Verify Docker daemon (Testcontainers prereq)
        run: docker info

      - name: Run integration tests (Testcontainers)
        env:
          TESTCONTAINERS_RYUK_DISABLED: "false"
        run: |
          dotnet test IntegrationTests/IntegrationTests.csproj \
            --configuration "$BUILD_CONFIGURATION" \
            --logger "trx;LogFileName=integration.trx" \
            --results-directory "$RUNNER_TEMP/TestResults"

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: Integration tests
          path: ${{ runner.temp }}/TestResults/*.trx
          reporter: dotnet-trx
          fail-on-error: true
```

### Playwright UI shard — `.github/workflows/_ui-tests.yml`

```yaml
on:
  workflow_call:
    inputs:
      shard-total:
        type: number
        default: 4

jobs:
  ui-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    strategy:
      fail-fast: false
      matrix:
        shard-index: [1, 2, 3, 4]   # length MUST equal shard-total
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - name: Build + install Playwright browsers
        run: |
          dotnet build UiTests/UiTests.csproj -c "$BUILD_CONFIGURATION"
          pwsh UiTests/bin/$BUILD_CONFIGURATION/net8.0/playwright.ps1 install --with-deps chromium

      - name: Run UI tests (shard ${{ matrix.shard-index }}/${{ inputs.shard-total }})
        run: |
          dotnet test UiTests/UiTests.csproj \
            --no-build -c "$BUILD_CONFIGURATION" \
            --logger "trx;LogFileName=ui-shard-${{ matrix.shard-index }}.trx" \
            --results-directory "$RUNNER_TEMP/TestResults" \
            -- Playwright.Shard=${{ matrix.shard-index }}/${{ inputs.shard-total }}

      - name: Upload Playwright traces (on failure only)
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-traces-shard-${{ matrix.shard-index }}
          path: UiTests/bin/${{ env.BUILD_CONFIGURATION }}/net8.0/playwright-traces
          retention-days: 14

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: UI shard ${{ matrix.shard-index }}
          path: ${{ runner.temp }}/TestResults/*.trx
          reporter: dotnet-trx
          fail-on-error: true

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: allure-results-ui-${{ matrix.shard-index }}
          path: UiTests/allure-results
          retention-days: 30
```

### Allure publish with history — `.github/workflows/_allure-publish.yml`

History lives on a `gh-pages` branch. `peaceiris/actions-gh-pages` with `keep_files: true` preserves the prior report's `history/` folder; `simple-elf/allure-report-action` reads it back in so trend charts survive across runs. This is the Pages-native equivalent of the Azure-Blob history dance in the sibling skill.

```yaml
on:
  workflow_call:

permissions:
  contents: write    # push the generated report to gh-pages

jobs:
  publish-allure:
    runs-on: ubuntu-latest
    steps:
      - name: Download all Allure results
        uses: actions/download-artifact@v4
        with:
          pattern: allure-results-*
          path: allure-results
          merge-multiple: true

      - name: Restore prior Allure history from gh-pages
        uses: actions/checkout@v4
        with:
          ref: gh-pages
          path: gh-pages-prior
        continue-on-error: true     # first-ever run has no gh-pages branch

      - name: Generate Allure report with history
        uses: simple-elf/allure-report-action@v1.9
        with:
          allure_results: allure-results
          allure_history: allure-history
          gh_pages: gh-pages-prior
          keep_reports: 30

      - name: Publish report to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_branch: gh-pages
          publish_dir: allure-history
          keep_files: true          # preserve history/ across runs
```

When GitHub Pages is unavailable (private repo without Pages, policy restriction), drop the last two steps and upload `allure-history` as an artifact with `retention-days: 90` instead — you lose the hosted browse, not the report.

### k6 perf gate — `.github/workflows/_k6-perf.yml`

k6 returns exit code 99 when thresholds break. The step inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/performance/_shared` (tests **fail the build** when SLOs aren't met).

```yaml
on:
  workflow_call:

jobs:
  k6-perf:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Resolve target URL
        run: echo "K6_BASE_URL=$(az keyvault secret show --vault-name kv-qa --name api-base-url --query value -o tsv)" >> "$GITHUB_ENV"

      - name: Install k6 0.52.0 (pinned)
        run: |
          curl -fsSL https://github.com/grafana/k6/releases/download/v0.52.0/k6-v0.52.0-linux-amd64.tar.gz \
            | tar -xz --strip-components=1 -C /tmp/
          sudo mv /tmp/k6 /usr/local/bin/

      - name: Run k6 (thresholds enforce SLOs; exit 99 on breach)
        run: k6 run --out json=k6-summary.json perf/scenarios/checkout.js

      - name: Upload k6 summary
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: k6-summary
          path: k6-summary.json
          retention-days: 30
```

## Rules

### Triggers
- `pull_request: [main]` + nightly `schedule`. Add `workflow_dispatch` so a human can re-run on demand.
- PR runs stay under 15 min by skipping perf and visual-regression (`if: github.event_name == 'schedule'`).
- A `schedule` cron only fires on the **default branch** — don't expect it on PR branches.

### Concurrency
- One `concurrency` group per ref. `cancel-in-progress: true` for PRs (kill superseded runs), `false` for nightly (let the full suite finish).

### Sharding
- Default: 4 shards for UI, 2 for API, 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- `strategy.matrix` with **`fail-fast: false`** — one shard failing must not cancel the rest, or you lose the other shards' reports.
- The `shard-index` array length **must equal** `shard-total`. For uneven suites, compute the matrix JSON in an upstream `setup` job and consume it with `fromJSON(needs.setup.outputs.matrix)` — never re-discover tests at runtime per shard.

### Secrets
- **OIDC only** via `permissions: id-token: write` + `azure/login@v2` (or `aws-actions/configure-aws-credentials` with `role-to-assume`). No PATs, no stored cloud secrets in repo/org settings.
- Store the federated identity's `client-id` / `tenant-id` / `subscription-id` as **`vars`** (non-sensitive), not `secrets` — they are identifiers, not credentials.
- Mask any secret value fetched at runtime with `echo "::add-mask::$SECRET"` **before** writing it to `$GITHUB_ENV`. Never `echo` a secret to the log.
- `id-token: write` grants the run an OIDC token only — it does **not** grant repo write. Keep `contents: read` unless a step genuinely pushes (e.g. Allure → `gh-pages` needs `contents: write` in that job only).

### Reporters
- Always emit **both** TRX and Allure. TRX feeds `dorny/test-reporter` (a Checks summary on the PR); Allure feeds humans with history.
- `fail-on-error: true` on every `test-reporter` step. The build must red on real failures even if a runner exit code is masked. `dotnet test` already exits non-zero on failure — do not swallow it with `continue-on-error`.

### Retry policy
- **No workflow-level retry** of failed tests (no `nick-fields/retry` wrapping the test step, no re-run-failed automation). Retry hides bugs.
- Per-test `[Retry(2)]` is allowed only for documented network-flake hotspots (third-party sandboxes, infra warm-up). Document each one in the test's XML comment with a date and an issue link.
- For genuinely flaky tests, quarantine via `qa/flaky-test-quarantine/dotnet` — do not auto-retry.

### Artifacts
- TRX + coverage: 30 days (`retention-days: 30`).
- Playwright traces / videos / HAR: 14 days, **only on failure** (`if: failure()`) to keep storage bounded.
- Allure: report + history persisted on `gh-pages` (or 90-day artifact when Pages is off).
- `actions/upload-artifact@v4` requires **unique artifact names** per job — suffix with `${{ matrix.shard-index }}`, or v4 fails the second upload. (This changed from v3's auto-merge behavior.)
- Container logs (Testcontainers): attach to Allure via the test runner, not as a separate artifact.

### Perf gate
- k6 / NBomber thresholds live inline in the script (`thresholds: { http_req_duration: ['p(95)<500'] }`). The workflow does not interpret metrics.
- The runner returns a non-zero exit code on threshold breach (k6: 99) — the step fails automatically. Do not add `if`/`continue-on-error` guards.
- Pin the perf tool version (`k6 v0.52.0`); upgrade in a dedicated PR.

### What NOT to do
- No `runs-on: windows-latest` for Linux-container tests (Docker on the Windows runner defaults to Windows containers → Testcontainers Linux modules fail).
- No PATs / `GITHUB_TOKEN` for cross-cloud auth — use OIDC federation.
- No `continue-on-error: true` on a test step to "make it green". Fix the test or quarantine it.
- No `--blame` flag in production runs (slow); enable only for the targeted re-run of a hang.
- No mixing of NUnit `[Parallelizable]` with `LevelOfParallelism > 1` in a fixture that owns a Testcontainer — instant flake.
- No `actions/*@main` or `@v4`-floating on a moving tag for **security-relevant** actions (`azure/login`, `actions-gh-pages`) — pin to a full SHA in regulated repos.
- No reusing a static artifact name across matrix shards with v4 — it errors.
- No printing a fetched secret in any step, even with `|| true`.

## Generation steps

1. Read any existing workflows under `.github/workflows/` to learn reusable-workflow conventions, `vars`/`secrets`, and the OIDC app already wired.
2. Inventory test projects: `find . -name '*Tests.csproj' -not -path '*/bin/*'`. Group them into API / integration / UI / perf.
3. Generate:
   - `.github/workflows/qa-tests.yml` (top-level orchestrator) if missing.
   - `.github/workflows/_{api,integration,ui}-tests.yml`, `_allure-publish.yml`, `_k6-perf.yml` as reusable workflows (`on: workflow_call`).
4. Configure one federated identity credential on the Azure AD app (or AWS IAM role) trusting `repo:ORG/REPO:ref:refs/heads/main` and `:pull_request`. Document the subject claim in the workflow header comment. Store `client-id` / `tenant-id` / `subscription-id` as repo `vars`.
5. Validate locally with `actionlint` (and optionally `act` for a dry run), then open a draft PR and confirm every expected job and the Checks summary appear.

## Cross-references

- **`qa/ci-pipelines/azure-pipelines/dotnet`** — the canonical sibling this ports from; consult it for the variable-group / service-connection variant.
- **`qa/db-testing/testcontainers/dotnet`** — the integration-tests job runs these.
- **`qa/email-testing/mailpit/dotnet`** — pair Mailpit as a `services:` container or inline Testcontainers run.
- **`qa/allure-reporting/dotnet`** — adapter wiring inside the test project that produces `allure-results/`.
- **`qa/performance/nbomber/dotnet`** + **`qa/performance/k6/typescript`** — perf-job scripts; SLO contract in `qa/performance/_shared`.
- **`devops/github-actions`** — non-QA workflow patterns (deploy, infra) live here.
- **`qa/_shared/ci-conventions`** — cross-stack rules (artifact retention, OIDC) this skill enforces.

## Sources synthesized (research-first per CLAUDE.md)

- [Playwright — Sharding](https://playwright.dev/docs/test-sharding) — `--shard=i/N` semantics and merging blob reports across shards.
- [Tim Deschryver — Playwright test shards + GitHub Actions job matrix](https://timdeschryver.dev/blog/using-playwright-test-shards-in-combination-with-a-job-matrix-to-improve-your-ci-speed) — `strategy.matrix` shard fan-out with `fail-fast: false`.
- [Gor Grigoryan — Optimizing .NET Test Runs in GitHub Actions with Test Sharding](https://gor-grigoryan.medium.com/optimizing-net-test-runs-in-github-actions-with-test-sharding-for-faster-ci-cd-315e610cf560) — `dotnet test` shard filter via NUnit `--where` in a matrix.
- [Microsoft Learn — Authenticate to Azure from GitHub Actions by OpenID Connect](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect) — `permissions: id-token: write`, `azure/login@v2`, federated credential subject claims.
- [GitHub Docs — Configuring OpenID Connect in Azure](https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure) — `id-token: write` grants only an OIDC token, not repo write.
- Allure publish via `simple-elf/allure-report-action` + `peaceiris/actions-gh-pages` (`keep_files: true`) — gh-pages history persistence pattern.

## Changelog

- 2026-05-31: Authored as the GitHub Actions / .NET port of `qa/ci-pipelines/azure-pipelines/dotnet` (QA Skills Library Phase 1, `qa/GAP-ANALYSIS.md` row 11). Re-expressed all sibling patterns in Actions idioms: `strategy.matrix` + `fail-fast: false` sharding, OIDC via `id-token: write` + `azure/login`, Allure history on `gh-pages` with `keep_files`, `dorny/test-reporter` for TRX, `upload-artifact@v4` unique-name requirement, k6 exit-99 perf gate. Java + TypeScript siblings still pending.
