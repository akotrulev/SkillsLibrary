# QA — GitHub Actions for TypeScript Test Suites

Authors `.github/workflows/*.yml` that run Vitest / Jest / Playwright / Testcontainers-backed integration tests on GitHub-hosted `ubuntu-latest` runners using Node 20 + TypeScript (strict), shard for speed via `strategy.matrix`, publish Allure (and/or Playwright's own HTML report) to GitHub Pages with history, fail on real failures (not flakes), and pull secrets via OIDC federated credentials rather than PATs or stored cloud secrets.

This is a port across two axes: the `qa/cicd/dotnet/skills/ci-pipelines` sibling (GitHub Actions idioms) and the `qa/cicd/typescript/skills/ci-pipelines` sibling (Node/TS tooling). Same patterns — shard, OIDC, Allure history, JUnit upload, retry policy, perf gate — re-expressed for the Actions runtime. **TypeScript is the most Actions-native of the three stacks**: Playwright ships first-class `--shard=i/N` and an official `blob` reporter → `merge-reports` flow, so the UI job replaces the per-shard Allure-merge dance with a single merge step. k6 stays the perf tool (JS-native here, same exit-99 gate as the dotnet sibling).

## When to use

- New QA workflow for a TS test project (`api-tests`, `integration`, `e2e`, `perf`)
- Adding `strategy.matrix` sharding to an existing serial workflow
- Merging Playwright `blob` reports from N shards into one HTML report
- Wiring Allure publish + history to GitHub Pages (or an artifact)
- Replacing stored cloud secrets / PATs with OIDC federated credentials
- Adding a perf gate (k6) that breaks the build on SLO regression

## When NOT to use

- Azure Pipelines equivalent → `qa/cicd/typescript/skills/ci-pipelines`
- GitLab CI equivalent → `qa/cicd/typescript/skills/ci-pipelines`
- App build / deploy workflows unrelated to tests → `devops/github-actions`
- Non-TS stacks — use the `dotnet` or `java` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test runners? (Vitest, Jest, Playwright, k6 — and which package dirs)
2. Sharding fan-out? (default: 4 runners for Playwright UI, 2 for Vitest API/integration, 1 for perf)
3. Report destination? (default: Playwright HTML for UI + Allure on GitHub Pages via `gh-pages` with `keep_files`; artifact-only when Pages is unavailable)

Infer everything else from `package.json`, `playwright.config.ts`, `vitest.config.ts`, the lockfile (`pnpm-lock.yaml` / `package-lock.json` / `yarn.lock`), and any existing workflows under `.github/workflows/`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `ubuntu-latest` (Docker pre-installed) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| Node | 20 LTS via `actions/setup-node@v4`, version pinned by `.nvmrc` | Newer LTS only after 3 mo GA |
| Package manager / cache | Detect from lockfile; `actions/setup-node@v4` with `cache: 'pnpm'` (or `npm`/`yarn`) + `pnpm install --frozen-lockfile` (or `npm ci`) | Match whatever the repo already uses — never switch managers in a CI PR |
| Triggers | `pull_request: [main]` + nightly `schedule` cron | `push` on main only when the suite is < 5 min |
| Test reporter | Vitest/Jest: JUnit XML (`vitest --reporter=junit` / `jest-junit`) + Allure adapter. Playwright: `blob` in CI + `allure-playwright` | Always emit a JUnit-shaped XML for `dorny/test-reporter`; Playwright's HTML can stand in for Allure on UI-only repos |
| Sharding | `strategy.matrix` with `fail-fast: false`; Playwright `--shard=i/N`, Vitest `--shard=i/N` (≥1.4) | Pre-computed bin file via an upstream `setup` job for uneven fixtures |
| Auth to Azure / AWS / Key Vault | OIDC federated credential (`id-token: write`) | Never PATs, never stored long-lived cloud secrets |
| Retry on failure | **Off at the workflow level**; `playwright.config.ts → retries: 0` in CI | Per-project `retries` / `test.fixme` only for documented flake hotspots — never blanket retry |
| Concurrency | `concurrency` group per ref, `cancel-in-progress: true` for PRs | Keep nightly runs un-cancelled (`cancel-in-progress: false`) |
| Artifact retention | 14 days for traces/videos/HAR, 30 days for JUnit + blob reports, Allure history persisted on `gh-pages` | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | k6 thresholds → script exit code 99 → step fails | Soft gate (`continue-on-error`) only while a baseline is being established |

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
  NODE_VERSION: '20'

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

`if: ${{ !cancelled() }}` is the Actions equivalent of Azure's `condition: always()` minus the cancelled case — you want the report on red, but not on a user-cancelled run. The `ui-tests` reusable workflow merges its own Playwright blob reports internally (see below); `publish-allure` aggregates the Allure results from every job.

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
      fail-fast: false       # one shard failing must not kill the others
      matrix:
        shard-index: [1, 2]  # length MUST equal shard-total
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'      # match the repo's lockfile: 'pnpm' | 'npm' | 'yarn'

      - run: pnpm install --frozen-lockfile

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
          reporter: jest-junit       # parses Vitest/Jest JUnit XML
          fail-on-error: true        # red the check on real test failures

      - name: Upload JUnit results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: junit-api-${{ matrix.shard-index }}
          path: reports
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: allure-results-api-${{ matrix.shard-index }}
          path: allure-results
          retention-days: 30
```

`vitest run --shard=i/N` (Vitest ≥1.4) splits the suite deterministically across runners — the `matrix.shard-index` array length **must equal** `shard-total`; GitHub Actions has no `strategy: parallel: N` shorthand like Azure, so the array is the source of truth. For Jest, swap to `jest --shard=${{ matrix.shard-index }}/${{ inputs.shard-total }}` and configure the `jest-junit` reporter in `jest.config.ts`. For dynamic/uneven sharding, compute the matrix JSON in an upstream `setup` job and pass it via `fromJSON(needs.setup.outputs.matrix)` — never re-discover tests at runtime per shard.

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
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
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

Playwright's **native** sharding + `blob` reporter is the TS-native path: each shard writes a `blob-report/`, and a final `merge-reports` job stitches them into one HTML report (and one Allure result set). This replaces the per-shard Allure-merge dance the dotnet/java siblings need. Set `reporter: process.env.CI ? [['blob'], ['allure-playwright']] : 'html'` in `playwright.config.ts`, and `retries: 0` in CI.

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
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile

      - name: Install Playwright browsers + OS deps
        run: pnpm exec playwright install --with-deps chromium

      - name: Run UI tests (shard ${{ matrix.shard-index }}/${{ inputs.shard-total }})
        run: |
          pnpm exec playwright test \
            --shard=${{ matrix.shard-index }}/${{ inputs.shard-total }}

      - name: Upload blob report
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: blob-report-${{ matrix.shard-index }}   # unique per shard (v4 requirement)
          path: blob-report
          retention-days: 30

      - name: Upload traces (on failure only)
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-traces-shard-${{ matrix.shard-index }}
          path: test-results
          retention-days: 14

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
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
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile

      - name: Download all blob reports
        uses: actions/download-artifact@v4
        with:
          pattern: blob-report-*
          path: all-blob-reports
          merge-multiple: true

      - name: Merge into one HTML report
        run: pnpm exec playwright merge-reports --reporter html ./all-blob-reports

      - name: Upload merged HTML report
        uses: actions/upload-artifact@v4
        with:
          name: playwright-html-report
          path: playwright-report
          retention-days: 30
```

`download-artifact@v4` with `merge-multiple: true` collapses the per-shard `blob-report-*` artifacts into one folder; `merge-reports --reporter html` produces a single browsable report. On a UI-only repo you can stop here and skip Allure entirely — Playwright's HTML report with traces is a complete, lighter-weight deliverable. Keep the `allure-results-ui-*` upload only when the org standardizes on Allure across all suites.

### Allure publish with history — `.github/workflows/_allure-publish.yml`

History lives on a `gh-pages` branch. `peaceiris/actions-gh-pages` with `keep_files: true` preserves the prior report's `history/` folder; `simple-elf/allure-report-action` reads it back in so trend charts survive across runs. This is the Pages-native equivalent of the Azure-Blob history dance in the `azure-pipelines/typescript` sibling — no `allure-commandline` install needed.

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

k6 returns exit code 99 when thresholds break. The step inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met). k6 is the JS-native perf tool here — keep it (do not swap to Gatling/NBomber in the TS stack).

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

### Package manager
- **Detect the manager from the lockfile and match it** — `pnpm-lock.yaml` → pnpm, `package-lock.json` → npm, `yarn.lock` → yarn. Never switch managers in a CI PR.
- Use `actions/setup-node@v4` with `cache: 'pnpm'` (or `npm`/`yarn`) — do not hand-roll `actions/cache` for `node_modules`/the store.
- **Frozen, reproducible installs only**: `pnpm install --frozen-lockfile` / `npm ci` / `yarn install --immutable`. Never bare `npm install` in CI.

### Sharding
- Default: 4 shards for UI (Playwright `--shard`), 2 for API (Vitest `--shard`), 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- `strategy.matrix` with **`fail-fast: false`** — one shard failing must not cancel the rest, or you lose the other shards' reports (and break the blob merge).
- The `shard-index` array length **must equal** `shard-total`. GitHub Actions has no `strategy: parallel: N` shorthand — the array is the source of truth. For uneven suites, compute the matrix JSON in an upstream `setup` job and consume it with `fromJSON(needs.setup.outputs.matrix)` — never re-discover tests at runtime per shard.

### Reporters
- Always emit a **JUnit-shaped XML** (`vitest --reporter=junit` / `jest-junit`) for `dorny/test-reporter` (`reporter: jest-junit`, a Checks summary on the PR) **plus** the human-facing report (Allure adapter, or Playwright's own HTML).
- For Playwright, use the **`blob` reporter in CI** and merge with `npx playwright merge-reports` — this is the native sharded-report path and avoids the per-shard Allure merge.
- `fail-on-error: true` on every `test-reporter` step. The build must red on real failures. Vitest/Playwright already exit non-zero on failure — do not swallow it with `continue-on-error`.

### Secrets
- **OIDC only** via `permissions: id-token: write` + `azure/login@v2` (or `aws-actions/configure-aws-credentials` with `role-to-assume`). No PATs, no stored cloud secrets in repo/org settings.
- Store the federated identity's `client-id` / `tenant-id` / `subscription-id` as **`vars`** (non-sensitive), not `secrets` — they are identifiers, not credentials.
- Mask any secret value fetched at runtime with `echo "::add-mask::$SECRET"` **before** writing it to `$GITHUB_ENV`. Never `echo` a secret to the log, and never write it to a path an `upload-artifact` step picks up.
- `id-token: write` grants the run an OIDC token only — it does **not** grant repo write. Keep `contents: read` unless a step genuinely pushes (e.g. Allure → `gh-pages` needs `contents: write` in that job only).

### Retry policy
- **No workflow-level retry** of failed tests (no `nick-fields/retry` wrapping the test step, no re-run-failed automation). Retry hides bugs.
- `playwright.config.ts → retries: 0` in CI. Per-project `retries` (or Vitest `test.retry`) is allowed only for documented network-flake hotspots (third-party sandboxes, infra warm-up). Document each one in a code comment with a date and an issue link.
- For genuinely flaky tests, quarantine via `qa/reporting/typescript/skills/flaky-test-quarantine` — do not auto-retry.

### Artifacts
- JUnit results + Playwright blob/HTML reports: 30 days (`retention-days: 30`).
- Playwright traces / videos / HAR: 14 days, **only on failure** (`if: failure()`) to keep storage bounded.
- Allure: report + history persisted on `gh-pages` (or 90-day artifact when Pages is off).
- `actions/upload-artifact@v4` requires **unique artifact names** per job — suffix with `${{ matrix.shard-index }}` (e.g. `blob-report-${{ matrix.shard-index }}`), or v4 fails the second upload. (This changed from v3's auto-merge behavior; the `merge-reports` job recombines them with `download-artifact@v4` + `merge-multiple: true`.)
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
- No `playwright install` without `--with-deps` (missing system libs → silent browser crashes).
- No reusing a static artifact name across matrix shards with v4 — it errors and breaks the blob merge.
- No `actions/*@main` or floating major-tag for **security-relevant** actions (`azure/login`, `actions-gh-pages`) — pin to a full SHA in regulated repos.
- No printing of `$AUTH0_M2M_SECRET` (or any fetched secret) in any step, even with `|| true`.

## Generation steps

1. Read any existing workflows under `.github/workflows/` to learn reusable-workflow conventions, `vars`/`secrets`, and the OIDC app already wired.
2. Inventory test projects: read `package.json` scripts, `playwright.config.ts`, `vitest.config.ts` / `jest.config.ts`, and the lockfile (decides the package manager + `cache:` key). Group them into API / integration / UI / perf.
3. Generate:
   - `.github/workflows/qa-tests.yml` (top-level orchestrator) if missing.
   - `.github/workflows/_{api,integration,ui}-tests.yml`, `_allure-publish.yml`, `_k6-perf.yml` as reusable workflows (`on: workflow_call`).
   - Set `reporter: process.env.CI ? [['blob'], ['allure-playwright']] : 'html'` and `retries: 0` in `playwright.config.ts`; configure the JUnit reporter in `vitest.config.ts` / `jest.config.ts`.
4. Configure one federated identity credential on the Azure AD app (or AWS IAM role) trusting `repo:ORG/REPO:ref:refs/heads/main` and `:pull_request`. Document the subject claim in the workflow header comment. Store `client-id` / `tenant-id` / `subscription-id` as repo `vars`.
5. Validate locally with `actionlint` (and optionally `act` for a dry run), then open a draft PR and confirm every expected job, the merged Playwright report, and the Checks summary appear.

## Cross-references

- **`qa/cicd/dotnet/skills/ci-pipelines`** + **`qa/cicd/java/skills/ci-pipelines`** — the same-CI siblings; consult for the NUnit/TRX and TestNG/JUnit variants (both need a per-shard Allure merge the Playwright `blob` flow avoids).
- **`qa/cicd/typescript/skills/ci-pipelines`** — the Azure sibling this ports from; consult it for the variable-group / service-connection variant of the same Vitest/Playwright patterns.
- **`qa/typescript/skills/ui-test-author/playwright`** — the `playwright.config.ts` (`blob`/`allure-playwright` reporters, `--shard`, traces) this workflow runs.
- **`qa/typescript/skills/db-testing/testcontainers`** — the integration-tests job runs these.
- **`qa/typescript/skills/email-testing`** — pair Mailpit as a `services:` container or inline Testcontainers run.
- **`qa/reporting/typescript/skills/test-reports`** — adapter wiring inside the test project that produces `allure-results/`.
- **`qa/typescript/skills/load-testing`** — perf-job scripts; SLO contract in `qa/_shared/performance`.
- **`devops/github-actions`** — non-QA workflow patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC) this skill enforces.
