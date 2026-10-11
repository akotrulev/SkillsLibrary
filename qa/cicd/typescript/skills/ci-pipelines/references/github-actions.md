# QA — GitHub Actions for TypeScript Test Suites

Authors `.github/workflows/*.yml` that run Vitest / Jest / Playwright / Testcontainers-backed integration tests on GitHub-hosted `ubuntu-latest` runners using Node 24 + TypeScript (strict), shard for speed via `strategy.matrix`, publish Allure (and Playwright's own HTML report) to GitHub Pages with history, fail on real failures, and pull secrets via OIDC federated credentials rather than PATs or stored cloud secrets.

This is a port across two axes: the .NET GitHub Actions reference (`qa/cicd/dotnet/skills/ci-pipelines`, GitHub Actions idioms) and this skill's Azure Pipelines reference (`references/azure-pipelines.md`, Node/TS tooling). Same patterns — shard, OIDC, Allure history, JUnit upload, retry policy, perf gate — re-expressed for the Actions runtime. **TypeScript is the most Actions-native of the three stacks**: Playwright ships first-class `--shard=i/N` and an official `blob` reporter → `merge-reports` flow, so the UI job replaces the per-shard Allure-merge dance with a single merge step. k6 stays the perf tool (JS-native here, same exit-99 gate as the dotnet sibling).

**The Playwright config is not written here.** `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts` owns it: on CI it writes `blob` (to `blob-report/`), `junit` (to `test-results/junit.xml`) and `allure-playwright` (to `allure-results/`), with `retries: 0`, trace and video `retain-on-failure`, and `updateSnapshots: 'none'`. The workflow runs that config as is; it never overrides `--reporter` or the evidence modes on the command line. What the evidence is and how to read it is `qa/typescript/skills/evidence-capture`.

## When to use

- New QA workflow for a TS test project (`api-tests`, `integration`, `e2e`, `perf`)
- Adding `strategy.matrix` sharding to an existing serial workflow
- Merging Playwright `blob` reports from N shards into one HTML report
- Wiring Allure publish + history to GitHub Pages (or an artifact)
- Replacing stored cloud secrets / PATs with OIDC federated credentials
- Adding a perf gate (k6) that breaks the build on SLO regression

## When NOT to use

- Azure Pipelines equivalent → `references/azure-pipelines.md` in this skill
- GitLab CI equivalent → `references/gitlab-ci.md` in this skill
- App build / deploy workflows unrelated to tests → `devops/github-actions`
- Non-TS stacks — use the `dotnet` or `java` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test runners? (Vitest, Jest, Playwright, k6 — and which package dirs)
2. Sharding fan-out? (default: 4 runners for Playwright UI, 2 for Vitest API/integration, 1 for perf)
3. Report destination? (default: Playwright HTML for UI + Allure on GitHub Pages via `gh-pages`; artifact-only when Pages is unavailable)

Infer everything else from `package.json`, `playwright.config.ts`, `vitest.config.ts`, the lockfile (`pnpm-lock.yaml` / `package-lock.json` / `yarn.lock`), and any existing workflows under `.github/workflows/`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `ubuntu-latest` (Docker pre-installed) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| Node | 24 (22 maintenance) via `actions/setup-node@v6` with `node-version-file: .nvmrc` | Newer LTS only after 3 mo GA |
| Browsers | `pnpm exec playwright install --with-deps chromium` | Run the job in `mcr.microsoft.com/playwright:v1.64.0-noble` when visual baselines are compared (the tag equals the `@playwright/test` version). Never the archived `microsoft/playwright-github-action` |
| Package manager / cache | Detect from lockfile; `actions/setup-node@v6` with `cache: 'pnpm'` (or `npm`/`yarn`) + `pnpm install --frozen-lockfile` (or `npm ci`) | Match whatever the repo already uses — never switch managers in a CI PR |
| Triggers | `pull_request: [main]` + nightly `schedule` cron | `push` on main only when the suite is < 5 min |
| Test reporter | Vitest/Jest: JUnit XML (`vitest --reporter=junit` / `jest-junit`) + Allure adapter. Playwright: the config's `blob` + `junit` + `allure-playwright` on CI | Never a `--reporter` override for Playwright — it drops the config's reporters |
| Sharding | `strategy.matrix` with `fail-fast: false`; Playwright `--shard=i/N`, Vitest `--shard=i/N` (≥1.4) | Pre-computed bin file via an upstream `setup` job for uneven fixtures |
| Auth to Azure / AWS / Key Vault | OIDC federated credential (`id-token: write`) | Never PATs, never stored long-lived cloud secrets |
| Retry on failure | **Off at the workflow level**; `retries: 0` in the Playwright config (`ci-conventions`) | A documented hotspot `describe` per `flaky-test-quarantine` — never blanket retry |
| Concurrency | `concurrency` group per ref, `cancel-in-progress: true` for PRs | Keep nightly runs un-cancelled (`cancel-in-progress: false`) |
| Artifact retention | Failure evidence (`test-results/`, merged `playwright-report/`) 14 days; blobs 1 day; JUnit + Allure results 30 days; Allure history on `gh-pages` | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | k6 thresholds → script exit code 99 → step fails | Soft gate (`continue-on-error`) only while a baseline is being established |

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

- The `schedule` cron is the nightly full suite; `concurrency` cancels superseded PR runs and never a nightly.
- `checks: write` lets `dorny/test-reporter` publish a Checks summary; `id-token: write` grants an OIDC token for `azure/login`, not repo write.
- `if: ${{ !cancelled() }}` is the Actions equivalent of Azure's `condition: always()` minus the cancelled case — you want the report on red, but not on a user-cancelled run. The `ui-tests` reusable workflow merges its own Playwright blob reports (see below); `publish-allure` aggregates the Allure results from every job.
- Reusable workflows do not inherit the caller's `env`, so every job reads the Node version from `.nvmrc`.

### Sharded Vitest job — `.github/workflows/_api-tests.yml`

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
      fail-fast: false
      matrix:
        shard-index: [1, 2]
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 1 }

      - uses: actions/setup-node@v6
        with:
          node-version-file: .nvmrc
          cache: 'pnpm'

      - run: pnpm install --frozen-lockfile

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
          pnpm vitest run \
            --shard=${{ matrix.shard-index }}/${{ inputs.shard-total }} \
            --reporter=default \
            --reporter=junit \
            --outputFile.junit=reports/junit-api-${{ matrix.shard-index }}.xml

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: API shard ${{ matrix.shard-index }}
          path: 'reports/junit-api-*.xml'
          reporter: jest-junit
          fail-on-error: true

      - name: Upload JUnit results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: junit-api-${{ matrix.shard-index }}
          path: reports
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-api-${{ matrix.shard-index }}
          path: allure-results
          retention-days: 30
```

`vitest run --shard=i/N` (Vitest ≥1.4) splits the suite deterministically across runners — the `matrix.shard-index` array length **must equal** `shard-total`; GitHub Actions has no `strategy: parallel: N` shorthand like Azure, so the array is the source of truth. `fail-fast: false` keeps one failing shard from killing the others. The secrets come from Key Vault through OIDC, with no stored secret, and each fetched value is masked before it reaches `$GITHUB_ENV`. `jest-junit` is the `dorny/test-reporter` parser for Vitest/Jest JUnit XML, and `fail-on-error: true` reds the check on real failures. For Jest, swap to `jest --shard=${{ matrix.shard-index }}/${{ inputs.shard-total }}` and configure the `jest-junit` reporter in `jest.config.ts`. For dynamic/uneven sharding, compute the matrix JSON in an upstream `setup` job and pass it via `fromJSON(needs.setup.outputs.matrix)` — never re-discover tests at runtime per shard.

> Vitest's JUnit XML occasionally omits a `time` attribute that `dorny/test-reporter`'s `jest-junit` parser expects; if the check errors on a `time` undefined, pin `vitest` ≥1.6 or post-process the XML, rather than switching the reporter off.

### Integration tests with Testcontainers — `.github/workflows/_integration-tests.yml`

GitHub-hosted Ubuntu runners have Docker pre-installed and the runner user is in the `docker` group — no DinD service or `--privileged` setup needed. `@testcontainers/*` and its Ryuk reaper work out of the box.

```yaml
on:
  workflow_call:

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version-file: .nvmrc
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile

      - name: Verify Docker daemon (Testcontainers prereq)
        run: docker info

      - name: Run integration tests (Testcontainers)
        env:
          TESTCONTAINERS_RYUK_DISABLED: "false"
        run: |
          pnpm vitest run --config vitest.integration.config.ts \
            --reporter=default \
            --reporter=junit \
            --outputFile.junit=reports/junit-integration.xml

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: Integration tests
          path: 'reports/junit-integration.xml'
          reporter: jest-junit
          fail-on-error: true
```

### Playwright UI shard with blob merge — `.github/workflows/_ui-tests.yml`

Playwright's **native** sharding + `blob` reporter is the TS-native path: each shard writes `blob-report/`, `test-results/` (the per-test failure evidence and `junit.xml`) and `allure-results/`; a final `merge-reports` job stitches the blobs into one HTML report with every trace, video and screenshot inside. This replaces the per-shard Allure-merge dance the dotnet/java siblings need.

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
        shard-index: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version-file: .nvmrc
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile

      - name: Install Playwright browsers + OS deps
        run: pnpm exec playwright install --with-deps chromium

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
          pnpm exec playwright test --grep-invert @flaky \
            --shard=${{ matrix.shard-index }}/${{ inputs.shard-total }}

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: UI shard ${{ matrix.shard-index }}
          path: test-results/junit.xml
          reporter: java-junit
          fail-on-error: true

      - name: Upload blob report
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: blob-report-${{ matrix.shard-index }}
          path: blob-report
          retention-days: 1

      - name: Upload failure evidence
        uses: actions/upload-artifact@v5
        if: failure()
        with:
          name: test-results-${{ matrix.shard-index }}
          path: test-results
          retention-days: 14

      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-ui-${{ matrix.shard-index }}
          path: allure-results
          retention-days: 30

  merge-reports:
    needs: ui-tests
    if: ${{ !cancelled() }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version-file: .nvmrc
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile

      - name: Download all blob reports
        uses: actions/download-artifact@v5
        with:
          pattern: blob-report-*
          path: all-blob-reports
          merge-multiple: true

      - name: Merge into one HTML report
        run: pnpm exec playwright merge-reports --reporter html ./all-blob-reports

      - name: Upload merged HTML report
        uses: actions/upload-artifact@v5
        with:
          name: playwright-report
          path: playwright-report
          retention-days: 14
```

- The `junit.xml` the check publishes is the one the config writes on CI (`test-results/junit.xml`); the workflow never passes `--reporter`, which would replace the config's reporters and drop the blob and Allure output.
- `test-results/` is uploaded **on failure only**: under `retain-on-failure` it holds the trace, video, screenshot and `error-context.md` of each failed test. The merged `playwright-report/` holds the same evidence for every shard and is uploaded whenever the merge runs; on a green run it carries no traces.
- Blob names already carry the shard number, so `merge-multiple: true` collapses the per-shard artifacts into one folder without clashes.
- `--grep-invert @flaky` keeps quarantined tests off the gate. They run in a separate, non-gating job (`pnpm exec playwright test --grep @flaky` with `continue-on-error: true`), per `qa/reporting/typescript/skills/flaky-test-quarantine` — a separate job, because each run cleans `test-results/` at its start.
- **Running in the pinned image** instead of installing browsers: give the job `container: { image: mcr.microsoft.com/playwright:v1.64.0-noble, options: --user 1001 }` and drop the install step. The tag must equal the `@playwright/test` version. Visual baselines are only compared inside that image (`qa/typescript/skills/visual-regression`).
- On a UI-only repo you can stop here and skip Allure entirely — the merged HTML report with traces is a complete deliverable. Keep the `allure-results-ui-*` upload when the org standardizes on Allure across all suites.

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

`contents: write` is scoped to this job, which pushes the report. `continue-on-error: true` on the history checkout covers the first-ever run, which has no `gh-pages` branch — it is not a test step. When GitHub Pages is unavailable (private repo without Pages, policy restriction), drop the last step and upload `allure-report` as an artifact with `retention-days: 90` instead — you lose the hosted browse, not the report.

### k6 perf gate — `.github/workflows/_k6-perf.yml`

k6 returns exit code 99 when thresholds break. The step inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met). k6 is the JS-native perf tool here — keep it (do not swap to Gatling/NBomber in the TS stack).

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
- PR runs stay under 15 min by skipping perf and visual-regression (`if: github.event_name == 'schedule'`). The schedule-gated visual step runs `npx playwright test --project=visual` (the `visual` project has `default: false`, so a plain `npx playwright test` skips it) in `mcr.microsoft.com/playwright:v1.64.0-noble`.
- A `schedule` cron only fires on the **default branch** — don't expect it on PR branches.

### Concurrency
- One `concurrency` group per ref. `cancel-in-progress: true` for PRs (kill superseded runs), `false` for nightly (let the full suite finish).

### Package manager
- **Detect the manager from the lockfile and match it** — `pnpm-lock.yaml` → pnpm, `package-lock.json` → npm, `yarn.lock` → yarn. Never switch managers in a CI PR.
- Use `actions/setup-node@v6` with `cache: 'pnpm'` (or `npm`/`yarn`) — do not hand-roll `actions/cache` for `node_modules`/the store.
- **Frozen, reproducible installs only**: `pnpm install --frozen-lockfile` / `npm ci` / `yarn install --immutable`. Never bare `npm install` in CI.

### Sharding
- Default: 4 shards for UI (Playwright `--shard`), 2 for API (Vitest `--shard`), 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- `strategy.matrix` with **`fail-fast: false`** — one shard failing must not cancel the rest, or you lose the other shards' reports (and break the blob merge).
- The `shard-index` array length **must equal** `shard-total`. GitHub Actions has no `strategy: parallel: N` shorthand — the array is the source of truth. For uneven suites, compute the matrix JSON in an upstream `setup` job and consume it with `fromJSON(needs.setup.outputs.matrix)` — never re-discover tests at runtime per shard.

### Reporters
- Always emit a **JUnit-shaped XML** for `dorny/test-reporter` (a Checks summary on the PR) **plus** the human-facing report (Allure adapter, or Playwright's own HTML). Vitest/Jest: `vitest --reporter=junit` / `jest-junit`. Playwright: the config already writes `test-results/junit.xml` on CI — publish that file.
- For Playwright, the config's **`blob` reporter** feeds `npx playwright merge-reports` — the native sharded-report path. Never override the reporters with `--reporter` in the workflow.
- `fail-on-error: true` on every `test-reporter` step. The build must red on real failures. Vitest/Playwright already exit non-zero on failure — do not swallow it with `continue-on-error`.

### Secrets
- **OIDC only** via `permissions: id-token: write` + `azure/login@v2` (or `aws-actions/configure-aws-credentials` with `role-to-assume`). No PATs, no stored cloud secrets in repo/org settings.
- Store the federated identity's `client-id` / `tenant-id` / `subscription-id` as **`vars`** (non-sensitive), not `secrets` — they are identifiers, not credentials.
- Mask any secret value fetched at runtime with `echo "::add-mask::$SECRET"` **before** writing it to `$GITHUB_ENV`. Never `echo` a secret to the log, and never write it to a path an `upload-artifact` step picks up.
- `id-token: write` grants the run an OIDC token only — it does **not** grant repo write. Keep `contents: read` unless a step genuinely pushes (e.g. Allure → `gh-pages` needs `contents: write` in that job only).

### Retry policy
- **No workflow-level retry** of failed tests (no `nick-fields/retry` wrapping the test step, no re-run-failed automation). Retry hides bugs.
- `retries: 0` in the Playwright config (`qa/cicd/ci-conventions`). A documented network-flake hotspot opts in with `test.describe.configure({ retries: 1 })` on its own `describe`, carrying an `issue` annotation with the link and the date.
- For genuinely flaky tests, quarantine via `qa/reporting/typescript/skills/flaky-test-quarantine` — do not auto-retry.

### Artifacts
- Failure evidence: `test-results/` per shard **only on failure** (`if: failure()`), and the merged `playwright-report/` — 14 days.
- Blob reports: 1 day; they only feed `merge-reports`.
- JUnit results and Allure results: 30 days. Allure report + history persisted on `gh-pages` (or a 90-day artifact when Pages is off).
- `actions/upload-artifact` requires **unique artifact names** per job — suffix with `${{ matrix.shard-index }}` (e.g. `blob-report-${{ matrix.shard-index }}`), or the second upload fails. The `merge-reports` job recombines them with `download-artifact` + `merge-multiple: true`.
- Container logs (Testcontainers): attach to Allure/Playwright via the test reporter, not as a separate artifact.

### Perf gate
- k6 thresholds live inline in the script (`thresholds: { http_req_duration: ['p(95)<500'] }`). The workflow does not interpret metrics.
- k6 returns exit code 99 on threshold breach — the step fails automatically. Do not add `if`/`continue-on-error` guards.
- Pin the k6 version (`v0.52.0`); upgrade in a dedicated PR.

### What NOT to do
- No `runs-on: windows-latest` for Linux-container tests (Docker on the Windows runner defaults to Windows containers → Testcontainers Linux modules fail).
- No PATs / `GITHUB_TOKEN` for cross-cloud auth — use OIDC federation.
- No `continue-on-error: true` on a test step to "make it green". Fix the test or quarantine it.
- No bare `npm install` in CI — use `npm ci` / `pnpm install --frozen-lockfile` / `yarn --immutable` for reproducible installs.
- No `playwright install` without `--with-deps` (missing system libs → silent browser crashes), and no `microsoft/playwright-github-action` (archived).
- No `--reporter`, `--trace` or `--update-snapshots` on the Playwright command line in CI — the config owns all three.
- No reusing a static artifact name across matrix shards — it errors and breaks the blob merge.
- No `actions/*@main` or floating major-tag for **security-relevant** actions (`azure/login`, `actions-gh-pages`) — pin to a full SHA in regulated repos.
- No printing of `$AUTH0_M2M_SECRET` (or any fetched secret) in any step, even with `|| true`.

## Generation steps

1. Read any existing workflows under `.github/workflows/` to learn reusable-workflow conventions, `vars`/`secrets`, and the OIDC app already wired.
2. Inventory test projects: read `package.json` scripts, `playwright.config.ts`, `vitest.config.ts` / `jest.config.ts`, and the lockfile (decides the package manager + `cache:` key). Group them into API / integration / UI / perf.
3. Generate:
   - `.github/workflows/qa-tests.yml` (top-level orchestrator) if missing.
   - `.github/workflows/_{api,integration,ui}-tests.yml`, `_allure-publish.yml`, `_k6-perf.yml` as reusable workflows (`on: workflow_call`).
   - The Playwright config comes from `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts` (blob + junit + Allure on CI, `retries: 0`, evidence `retain-on-failure`); configure the JUnit reporter in `vitest.config.ts` / `jest.config.ts`.
4. Configure one federated identity credential on the Azure AD app (or AWS IAM role) trusting `repo:ORG/REPO:ref:refs/heads/main` and `:pull_request`. Record the subject claim in the repo's CI README. Store `client-id` / `tenant-id` / `subscription-id` as repo `vars`.
5. Validate locally with `actionlint` (and optionally `act` for a dry run), then open a draft PR and confirm every expected job, the merged Playwright report, and the Checks summary appear.

## Cross-references

- **`qa/cicd/dotnet/skills/ci-pipelines`** + **`qa/cicd/java/skills/ci-pipelines`** — the same-CI siblings; consult for the NUnit/TRX and TestNG/JUnit variants (both need a per-shard Allure merge the Playwright `blob` flow avoids).
- **`references/azure-pipelines.md`** — the Azure sibling this ports from; consult it for the variable-group / service-connection variant of the same Vitest/Playwright patterns.
- **`qa/typescript/skills/ui-test-author/playwright`** — owns `assets/playwright.config.ts`, the config this workflow runs.
- **`qa/typescript/skills/evidence-capture`** — what lands in `test-results/` and `playwright-report/`, and how to read a downloaded trace.
- **`qa/typescript/skills/db-testing/testcontainers`** — the integration-tests job runs these.
- **`qa/typescript/skills/email-testing`** — pair Mailpit as a `services:` container or inline Testcontainers run.
- **`qa/reporting/typescript/skills/test-reports`** — adapter wiring inside the test project that produces `allure-results/`.
- **`qa/reporting/typescript/skills/flaky-test-quarantine`** — the `@flaky` tag the gate excludes, and the non-gating quarantine job.
- **`qa/typescript/skills/load-testing`** — perf-job scripts; SLO contract in `qa/_shared/performance`.
- **`devops/github-actions`** — non-QA workflow patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) this skill enforces.
