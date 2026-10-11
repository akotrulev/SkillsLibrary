# QA — GitHub Actions for .NET Test Suites

Authors `.github/workflows/*.yml` that run NUnit / Playwright / Testcontainers-backed integration tests on GitHub-hosted `ubuntu-latest` runners, shard for speed via `strategy.matrix` and NUnit class filters, upload the Playwright failure evidence, publish Allure to GitHub Pages with history, fail on real failures (not flakes), and pull secrets via OIDC federated credentials rather than PATs or stored cloud secrets.

**The UI lifecycle is not written here.** `qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs` owns it: it reads `BASE_URL` (required), runs headless unless `HEADED=1`, and on a failed test keeps a full-page screenshot, the trace and the video in `UiTests/bin/<cfg>/net10.0/playwright-artifacts/<Class>.<Test>.{png,zip,webm}`. The workflow runs that as is and uploads exactly that folder. `playwright-videos/` holds raw recordings `BaseTest` deletes after every test; it is never uploaded. What the evidence is and how to read it is `qa/dotnet/skills/evidence-capture`. The shard filters come from `ci/nunit-shards.sh`, defined once in this skill's `SKILL.md`.

This is a port of this skill's Azure Pipelines reference (`references/azure-pipelines.md`) to GitHub Actions idioms — same patterns (shard, OIDC, Allure history, TRX upload, retry policy, perf gate), re-expressed for the Actions runtime.

## When to use

- New QA workflow for a .NET test project (`ApiTests`, `UiTests`, `IntegrationTests`)
- Adding `strategy.matrix` sharding to an existing serial workflow
- Wiring Allure publish + history to GitHub Pages (or an artifact)
- Replacing stored cloud secrets / PATs with OIDC federated credentials
- Adding a perf gate (k6 / NBomber) that breaks the build on SLO regression

## When NOT to use

- Azure Pipelines equivalent → `references/azure-pipelines.md` in this skill
- GitLab CI equivalent → `references/gitlab-ci.md` in this skill
- App build / deploy workflows unrelated to tests → `devops/github-actions`
- Non-.NET stacks — use the `java` or `typescript` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test projects? (`ApiTests`, `IntegrationTests`, `UiTests`, multiple)
2. Sharding fan-out? (default: 4 runners for UI, 2 for API/integration, 1 for perf)
3. Allure history destination? (default: GitHub Pages via a `gh-pages` branch; artifact-only when Pages is unavailable)

Infer everything else from `.csproj` files and any existing workflows under `.github/workflows/`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `ubuntu-latest` (Docker and PowerShell 7 pre-installed, passwordless `sudo`) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| Triggers | `pull_request: [main]` + nightly `schedule` cron | `push` on main only when the suite is < 5 min |
| Test framework reporter | `--logger "trx"` + Allure NUnit adapter | Always both — TRX feeds `dorny/test-reporter`, Allure feeds humans |
| Sharding | A `plan` job runs `ci/nunit-shards.sh` once; `strategy.matrix` (`fail-fast: false`) runs one class filter per shard | Shard by namespace when a shard's filter grows past a few thousand characters |
| Playwright browsers | `pwsh UiTests/bin/<cfg>/net10.0/playwright.ps1 install --with-deps chromium` on the runner | The pinned image `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` for visual baselines (see the UI job) |
| Auth to Azure / AWS / Key Vault | OIDC federated credential (`id-token: write`) | Never PATs, never stored long-lived cloud secrets |
| Retry on failure | **Off at the workflow level** (no `nick-fields/retry` on the test step) | Per-test `[Retry(2)]` only for documented network-flake hotspots — never blanket retry |
| Concurrency | `concurrency` group per ref, `cancel-in-progress: true` for PRs | Keep nightly runs un-cancelled (`cancel-in-progress: false`) |
| Artifact retention | 14 days for `playwright-artifacts/` (on failure only), 30 days for TRX and Allure results, Allure history on `gh-pages` | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | k6 thresholds → script exit code → step fails | Soft gate (`continue-on-error`) only while a baseline is being established |

## Templates

### Top-level workflow — `.github/workflows/qa-tests.yml`

```yaml
name: QA Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 2 * * *"
  workflow_dispatch:

concurrency:
  group: qa-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

permissions:
  contents: read
  checks: write
  id-token: write

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
    if: ${{ !cancelled() }}
    uses: ./.github/workflows/_allure-publish.yml
```

- `checks: write` lets `dorny/test-reporter` publish a Checks summary; `id-token: write` gives the run an OIDC token for `azure/login` — it does **not** grant repo write.
- `if: ${{ !cancelled() }}` is the Actions equivalent of `condition: always()` minus the cancelled case — you want the report on red, but not on a user-cancelled run.
- **A called workflow does not inherit the caller's `env:`.** Each reusable workflow declares its own block; `_api-tests.yml` shows it, and every other reusable workflow below starts with the same one.

### Sharded NUnit job — `.github/workflows/_api-tests.yml`

```yaml
on:
  workflow_call:
    inputs:
      shard-total:
        type: number
        default: 2

env:
  DOTNET_VERSION: '10.0.x'
  BUILD_CONFIGURATION: Release
  DOTNET_NOLOGO: 'true'
  DOTNET_CLI_TELEMETRY_OPTOUT: 'true'

jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      shards: ${{ steps.split.outputs.shards }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - name: Split test classes into ${{ inputs.shard-total }} shards
        id: split
        run: |
          bash ci/nunit-shards.sh ApiTests/ApiTests.csproj ${{ inputs.shard-total }} shards
          echo "shards=[$(seq -s, 1 ${{ inputs.shard-total }})]" >> "$GITHUB_OUTPUT"

      - uses: actions/upload-artifact@v5
        with:
          name: api-shards
          path: shards
          retention-days: 1

  api-tests:
    needs: plan
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        shard-index: ${{ fromJSON(needs.plan.outputs.shards) }}
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 1 }

      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - uses: actions/download-artifact@v5
        with:
          name: api-shards
          path: shards

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
          read -r SHARD_FILTER < "shards/${{ matrix.shard-index }}.filter"
          dotnet test ApiTests/ApiTests.csproj \
            --configuration "$BUILD_CONFIGURATION" \
            --filter "($SHARD_FILTER)&TestCategory!=Slow&TestCategory!=Perf" \
            --logger "trx;LogFileName=api-shard-${{ matrix.shard-index }}.trx" \
            --logger "console;verbosity=minimal" \
            --results-directory "$RUNNER_TEMP/TestResults" \
            --collect:"XPlat Code Coverage"

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: API shard ${{ matrix.shard-index }}
          path: ${{ runner.temp }}/TestResults/*.trx
          reporter: dotnet-trx
          fail-on-error: true

      - name: Upload TRX + coverage
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: api-trx-${{ matrix.shard-index }}
          path: ${{ runner.temp }}/TestResults
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-api-${{ matrix.shard-index }}
          path: ApiTests/bin/${{ env.BUILD_CONFIGURATION }}/net10.0/allure-results
          retention-days: 30
```

- The `plan` job lists the tests once and writes `shards/<i>.filter`; each shard reads its own file. The matrix comes from the same `shard-total`, so the two cannot drift. Fewer test classes than shards fails the `plan` job — lower `shard-total`.
- `read -r` keeps the filter's escaped `\(` intact. The filter joins the shard's classes with `|` and the category exclusions with `&`.
- `fail-fast: false` — one shard failing must not kill the others, or you lose their reports.
- `fail-on-error: true` reds the check on real test failures.
- Allure.NUnit writes `allure-results/` into the test host's working directory, the build output folder.

### Integration tests with Testcontainers — `.github/workflows/_integration-tests.yml`

GitHub-hosted Ubuntu runners have Docker pre-installed and the runner user is in the `docker` group — no DinD service or `--privileged` setup needed. Testcontainers and its Ryuk reaper work out of the box.

```yaml
on:
  workflow_call:

env:
  DOTNET_VERSION: '10.0.x'
  BUILD_CONFIGURATION: Release

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v6
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

env:
  DOTNET_VERSION: '10.0.x'
  BUILD_CONFIGURATION: Release
  DOTNET_NOLOGO: 'true'
  DOTNET_CLI_TELEMETRY_OPTOUT: 'true'

jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      shards: ${{ steps.split.outputs.shards }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - name: Split test classes into ${{ inputs.shard-total }} shards
        id: split
        run: |
          bash ci/nunit-shards.sh UiTests/UiTests.csproj ${{ inputs.shard-total }} shards
          echo "shards=[$(seq -s, 1 ${{ inputs.shard-total }})]" >> "$GITHUB_OUTPUT"

      - uses: actions/upload-artifact@v5
        with:
          name: ui-shards
          path: shards
          retention-days: 1

  ui-tests:
    needs: plan
    runs-on: ubuntu-latest
    timeout-minutes: 45
    strategy:
      fail-fast: false
      matrix:
        shard-index: ${{ fromJSON(needs.plan.outputs.shards) }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - uses: actions/download-artifact@v5
        with:
          name: ui-shards
          path: shards

      - name: Build + install Playwright browsers
        run: |
          dotnet build UiTests/UiTests.csproj -c "$BUILD_CONFIGURATION"
          pwsh UiTests/bin/$BUILD_CONFIGURATION/net10.0/playwright.ps1 install --with-deps chromium

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Fetch test credentials from Key Vault
        run: |
          echo "BASE_URL=$(az keyvault secret show --vault-name kv-qa --name base-url --query value -o tsv)" >> "$GITHUB_ENV"
          echo "E2E_USER=$(az keyvault secret show --vault-name kv-qa --name e2e-user --query value -o tsv)" >> "$GITHUB_ENV"
          PASSWORD=$(az keyvault secret show --vault-name kv-qa --name e2e-password --query value -o tsv)
          echo "::add-mask::$PASSWORD"
          echo "E2E_PASSWORD=$PASSWORD" >> "$GITHUB_ENV"

      - name: Run UI tests (shard ${{ matrix.shard-index }}/${{ inputs.shard-total }})
        run: |
          read -r SHARD_FILTER < "shards/${{ matrix.shard-index }}.filter"
          dotnet test UiTests/UiTests.csproj \
            --no-build -c "$BUILD_CONFIGURATION" \
            --filter "($SHARD_FILTER)&TestCategory!=Flaky&TestCategory!=visual&TestCategory!=lighthouse&TestCategory!=grid" \
            --logger "trx;LogFileName=ui-shard-${{ matrix.shard-index }}.trx" \
            --results-directory "$RUNNER_TEMP/TestResults"

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: UI shard ${{ matrix.shard-index }}
          path: ${{ runner.temp }}/TestResults/*.trx
          reporter: dotnet-trx
          fail-on-error: true

      - name: Upload failure evidence
        uses: actions/upload-artifact@v5
        if: failure()
        with:
          name: playwright-artifacts-${{ matrix.shard-index }}
          path: UiTests/bin/${{ env.BUILD_CONFIGURATION }}/net10.0/playwright-artifacts
          retention-days: 14

      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-ui-${{ matrix.shard-index }}
          path: UiTests/bin/${{ env.BUILD_CONFIGURATION }}/net10.0/allure-results
          retention-days: 30
```

- **No `-- Playwright.Shard=i/N`.** `Microsoft.Playwright.NUnit` ignores it ("Playwright>Shard is not implemented") and every shard would run the whole suite; the class filter is the shard. `BaseTest`'s `[Parallelizable(ParallelScope.Self)]` keeps a class on one worker, so a class is the unit.
- **No headless flag.** `BaseTest` is headless unless `HEADED=1` (the runsettings set `Headless`), which only a local run sets.
- `--with-deps` installs OS packages through `sudo` on the runner. Browsers are pinned per Playwright version, so the 1.63.0 binding installs its own Chromium build; do not cache them (restore time is about the same as a download).
- `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come through OIDC: `BaseTest` throws without `BASE_URL`, and the root-namespace `AuthSetup` signs in once per shard before any fixture runs.
- `playwright-artifacts` is uploaded **on failure only**: it holds the screenshot, trace and video of each failed test plus any deliberate recording. A green run leaves it empty.
- The quarantine lane is a second, non-gating job in this workflow — the same steps without the `plan` job and the matrix, running `--filter "TestCategory=Flaky"` with `continue-on-error: true`, per `qa/reporting/dotnet/skills/flaky-test-quarantine`.
- **Selenium** suites drop the install step; `ubuntu-latest` ships Chrome and its driver.
- **Running in the pinned image** instead of installing browsers — what visual baselines need (`qa/dotnet/skills/visual-regression`): give the job `container: { image: mcr.microsoft.com/playwright/dotnet:v1.63.0-noble, options: --user 1001 }` and drop the install step; the image carries the .NET 10 SDK and the browsers. The tag must equal the Playwright version, and there is no `-jammy` .NET image since 1.60. `azure/login` needs the Azure CLI, which the image does not carry, so a container job tests only pages that need no fetched credentials. The visual job is not a container job: it is the `docker run` step in `qa/dotnet/skills/visual-regression/references/playwright-snapshots.md` §8.

### Allure publish with history — `.github/workflows/_allure-publish.yml`

History lives on a `gh-pages` branch: the published report's `history/` folder is copied into the new results before `allure generate`, so trend charts survive across runs. The report is generated with the one Allure CLI pin, `allure-commandline@2.46.1` (`qa/cicd/ci-conventions`), which needs a Java runtime.

```yaml
on:
  workflow_call:

permissions:
  contents: write

jobs:
  publish-allure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Download all Allure results
        uses: actions/download-artifact@v5
        with:
          pattern: allure-results-*
          path: allure-results
          merge-multiple: true

      - name: Restore prior Allure history from gh-pages
        uses: actions/checkout@v6
        with:
          ref: gh-pages
          path: gh-pages-prior
        continue-on-error: true

      - uses: actions/setup-java@v5
        with: { distribution: temurin, java-version: '21' }

      - name: Generate Allure report with history
        run: |
          npm i -g allure-commandline@2.46.1
          cp UiTests/categories.json allure-results/
          mkdir -p allure-results/history
          cp -r gh-pages-prior/history/. allure-results/history/ 2>/dev/null || true
          allure generate allure-results -o allure-report --clean

      - name: Publish report to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_branch: gh-pages
          publish_dir: allure-report
```

`contents: write` is scoped to this job, which pushes the report. `continue-on-error: true` on the history checkout covers the first-ever run, which has no `gh-pages` branch — it is not a test step. `categories.json` is read from the results folder, so it is copied in from the test project first. When GitHub Pages is unavailable (private repo without Pages, policy restriction), drop the last step and upload `allure-report` as an artifact with `retention-days: 90` instead — you lose the hosted browse, not the report.

### k6 perf gate — `.github/workflows/_k6-perf.yml`

k6 returns exit code 99 when thresholds break. The step inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met).

```yaml
on:
  workflow_call:

jobs:
  k6-perf:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v6

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
        uses: actions/upload-artifact@v5
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
- Membership is computed **once**, in the `plan` job, by `ci/nunit-shards.sh` (this skill's `SKILL.md`): test classes, round-robin, one `FullyQualifiedName~` term per class. Never re-discover tests in a shard, never filter by individual test names, and never pass `Playwright.Shard`.
- The matrix is `fromJSON(needs.plan.outputs.shards)`, built from the same `shard-total` the plan used.

### Secrets
- **OIDC only** via `permissions: id-token: write` + `azure/login@v2` (or `aws-actions/configure-aws-credentials` with `role-to-assume`). No PATs, no stored cloud secrets in repo/org settings.
- Store the federated identity's `client-id` / `tenant-id` / `subscription-id` as **`vars`** (non-sensitive), not `secrets` — they are identifiers, not credentials.
- Mask any secret value fetched at runtime with `echo "::add-mask::$SECRET"` **before** writing it to `$GITHUB_ENV`. Never `echo` a secret to the log.
- `id-token: write` grants the run an OIDC token only — it does **not** grant repo write. Keep `contents: read` unless a step genuinely pushes (e.g. Allure → `gh-pages` needs `contents: write` in that job only).

### Reporters
- Always emit **both** TRX and Allure. TRX feeds `dorny/test-reporter` (a Checks summary on the PR); Allure feeds humans with history.
- `fail-on-error: true` on every `test-reporter` step. The build must red on real failures even if a runner exit code is masked. `dotnet test` already exits non-zero on failure — do not swallow it with `continue-on-error`.
- The Allure report is generated with `allure-commandline@2.46.1` and a Java runtime — no action that bundles its own Allure.

### Retry policy
- **No workflow-level retry** of failed tests (no `nick-fields/retry` wrapping the test step, no re-run-failed automation). Retry hides bugs.
- Per-test `[Retry(2)]` (two attempts) is allowed only for documented network-flake hotspots (third-party sandboxes, infra warm-up), each with a date and an issue link at the test.
- For genuinely flaky tests, quarantine via `qa/reporting/dotnet/skills/flaky-test-quarantine` — `TestCategory!=Flaky` on the gate, a non-gating `TestCategory=Flaky` job.

### Artifacts
- TRX + coverage: 30 days (`retention-days: 30`).
- `UiTests/bin/<cfg>/net10.0/playwright-artifacts/` (trace, video, screenshot of failed tests): 14 days, **only on failure** (`if: failure()`). Never `playwright-videos/`.
- Allure: results 30 days; report + history persisted on `gh-pages` (or a 90-day artifact when Pages is off).
- `actions/upload-artifact@v5` requires **unique artifact names** per job — suffix with `${{ matrix.shard-index }}`, or the second upload fails.
- Container logs (Testcontainers): attach to Allure via the test runner, not as a separate artifact.

### Perf gate
- k6 / NBomber thresholds live inline in the script (`thresholds: { http_req_duration: ['p(95)<500'] }`). The workflow does not interpret metrics.
- The runner returns a non-zero exit code on threshold breach (k6: 99) — the step fails automatically. Do not add `if`/`continue-on-error` guards.
- Pin the perf tool version (`k6 v0.52.0`); upgrade in a dedicated PR.

### What NOT to do
- No `runs-on: windows-latest` for Linux-container tests (Docker on the Windows runner defaults to Windows containers → Testcontainers Linux modules fail).
- No PATs / `GITHUB_TOKEN` for cross-cloud auth — use OIDC federation.
- No `continue-on-error: true` on a gating test step to "make it green". Fix the test or quarantine it.
- No `-- Playwright.Shard=i/N` and no `NUnit.Where` modulo predicate — neither shards anything.
- No `${{ env.X }}` in a reusable workflow that does not declare `X` itself.
- No `--blame` flag in production runs (slow); enable only for the targeted re-run of a hang.
- No mixing of NUnit `[Parallelizable]` with `LevelOfParallelism > 1` in a fixture that owns a Testcontainer — instant flake.
- No `actions/*@main` or a floating tag for **security-relevant** actions (`azure/login`, `actions-gh-pages`) — pin to a full SHA in regulated repos.
- No reusing a static artifact name across matrix shards — it errors.
- No printing a fetched secret in any step, even with `|| true`.

## Generation steps

1. Read any existing workflows under `.github/workflows/` to learn reusable-workflow conventions, `vars`/`secrets`, and the OIDC app already wired.
2. Inventory test projects: `find . -name '*Tests.csproj' -not -path '*/bin/*'`. Group them into API / integration / UI / perf.
3. Generate:
   - `ci/nunit-shards.sh` from this skill's `SKILL.md`.
   - `.github/workflows/qa-tests.yml` (top-level orchestrator) if missing.
   - `.github/workflows/_{api,integration,ui}-tests.yml`, `_allure-publish.yml`, `_k6-perf.yml` as reusable workflows (`on: workflow_call`), each with its own `env:` block.
4. Configure one federated identity credential on the Azure AD app (or AWS IAM role) trusting `repo:ORG/REPO:ref:refs/heads/main` and `:pull_request`. Store `client-id` / `tenant-id` / `subscription-id` as repo `vars`, and the Key Vault secrets `base-url`, `e2e-user` and `e2e-password` the UI job reads.
5. Validate locally with `actionlint` (and optionally `act` for a dry run), then open a draft PR and confirm every expected job, one UI job per shard, and the Checks summary appear.

## Cross-references

- **`references/azure-pipelines.md`** — the canonical sibling this ports from; consult it for the variable-group / service-connection variant.
- **`qa/dotnet/skills/ui-test-author/playwright`** — `BaseTest`, `ui.runsettings` and the `UiTests` project the UI job runs.
- **`qa/dotnet/skills/evidence-capture`** — what `playwright-artifacts/` holds and how to read a failed shard's trace.
- **`qa/dotnet/skills/db-testing/testcontainers`** — the integration-tests job runs these.
- **`qa/dotnet/skills/email-testing`** — pair Mailpit as a `services:` container or inline Testcontainers run.
- **`qa/reporting/dotnet/skills/test-reports`** — adapter wiring inside the test project that produces `allure-results/`, and `categories.json`.
- **`qa/reporting/dotnet/skills/flaky-test-quarantine`** — the `Flaky` category and the non-gating lane.
- **`qa/dotnet/skills/load-testing`** + **`qa/typescript/skills/load-testing`** — perf-job scripts; SLO contract in `qa/_shared/performance`.
- **`devops/github-actions`** — non-QA workflow patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) this skill enforces.
