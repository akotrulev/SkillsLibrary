# QA — GitHub Actions for Java Test Suites

Authors `.github/workflows/*.yml` that run TestNG / Selenium / RestAssured / Testcontainers-backed integration tests on GitHub-hosted `ubuntu-latest` runners using Java 21 + Gradle (Kotlin DSL), shard for speed via `strategy.matrix`, publish Allure to GitHub Pages with history, fail on real failures (not flakes), and pull secrets via OIDC federated credentials rather than PATs or stored cloud secrets.

This is a port across two axes: the .NET GitHub Actions reference (`qa/cicd/dotnet/skills/ci-pipelines`, GitHub Actions idioms) and this skill's Azure Pipelines reference (`references/azure-pipelines.md`, JVM tooling). Same patterns — shard, OIDC, Allure history, JUnit upload, retry policy, perf gate — re-expressed for the Actions runtime in Gradle/TestNG terms.

## When to use

- New QA workflow for a Java test module (`api-tests`, `integration-tests`, `e2e`, `perf`)
- Adding `strategy.matrix` sharding to an existing serial workflow
- Wiring Allure publish + history to GitHub Pages (or an artifact)
- Replacing stored cloud secrets / PATs with OIDC federated credentials
- Adding a perf gate (Gatling) that breaks the build on SLO regression

## When NOT to use

- Azure Pipelines equivalent → `references/azure-pipelines.md` in this skill
- GitLab CI equivalent → `references/gitlab-ci.md` in this skill
- App build / deploy workflows unrelated to tests → `devops/github-actions`
- Non-Java stacks — use the `dotnet` or `typescript` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which Gradle modules? (`api-tests`, `integration-tests`, `e2e`, multiple)
2. Sharding fan-out? (default: 4 runners for Selenium UI, 2 for API/integration, 1 for perf)
3. Allure history destination? (default: GitHub Pages via `gh-pages` branch with `keep_files`; artifact-only when Pages is unavailable)

Infer everything else from `settings.gradle.kts` / `build.gradle.kts` and any existing workflows under `.github/workflows/`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `ubuntu-latest` (Docker pre-installed) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| JDK | Temurin 21 via `actions/setup-java@v4` (`distribution: temurin`) | Newer LTS only after 3 mo GA |
| Build tool | **Gradle Kotlin DSL** via `gradle/actions/setup-gradle@v4` (cache on) | Maven only for legacy modules |
| Triggers | `pull_request: [main]` + nightly `schedule` cron | `push` on main only when the suite is < 5 min |
| Test framework reporter | JUnit-XML from TestNG (`build/test-results/test/`) + Allure-TestNG adapter | Always both — JUnit feeds `dorny/test-reporter`, Allure feeds humans |
| Sharding | `strategy.matrix` with `fail-fast: false`; `-PshardIndex/-PshardTotal` Gradle props | Pre-computed group split via `@Test(groups="shard-i-of-N")` for uneven suites |
| Auth to Azure / AWS / Key Vault | OIDC federated credential (`id-token: write`) | Never PATs, never stored long-lived cloud secrets |
| Retry on failure | **Off at the workflow level** (no `nick-fields/retry` on the test step) | Per-test `IRetryAnalyzer` only for documented network-flake hotspots — never blanket retry |
| Concurrency | `concurrency` group per ref, `cancel-in-progress: true` for PRs | Keep nightly runs un-cancelled (`cancel-in-progress: false`) |
| Artifact retention | 14 days for screenshots/traces/HAR, 30 days for test-results, Allure history persisted on `gh-pages` | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | Gatling assertions → non-zero exit → step fails | Soft gate (`continue-on-error`) only while a baseline is being established |

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
    uses: ./.github/workflows/_gatling-perf.yml
    secrets: inherit

  publish-allure:
    needs: [api-tests, integration-tests, ui-tests]
    if: ${{ !cancelled() }}     # publish even when a test job failed
    uses: ./.github/workflows/_allure-publish.yml
```

`if: ${{ !cancelled() }}` is the Actions equivalent of Azure's `condition: always()` minus the cancelled case — you want the report on red, but not on a user-cancelled run.

### Sharded TestNG job — `.github/workflows/_api-tests.yml`

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
        shard-index: [1, 2]  # length must equal shard-total
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 1 }

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'

      - uses: gradle/actions/setup-gradle@v4   # restores + saves the Gradle/dep cache

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
          ./gradlew :api-tests:test \
            -PshardIndex=${{ matrix.shard-index }} \
            -PshardTotal=${{ inputs.shard-total }} \
            --no-daemon

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: API shard ${{ matrix.shard-index }}
          path: 'api-tests/build/test-results/test/TEST-*.xml'
          reporter: java-junit
          fail-on-error: true        # red the check on real test failures

      - name: Upload JUnit results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: junit-api-${{ matrix.shard-index }}
          path: api-tests/build/test-results/test
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: allure-results-api-${{ matrix.shard-index }}
          path: api-tests/build/allure-results
          retention-days: 30
```

Wire the shard params in `build.gradle.kts` so each runner executes a disjoint slice:

```kotlin
tasks.named<Test>("test") {
    useTestNG {
        val total = (project.findProperty("shardTotal") as String?)?.toIntOrNull() ?: 1
        val index = (project.findProperty("shardIndex") as String?)?.toIntOrNull() ?: 1
        if (total > 1) {
            // Pre-computed group list is the most predictable; a name-hash modulo works for even suites.
            includeGroups = setOf("shard-$index-of-$total")
        }
    }
    // CLAUDE.md: no Thread.Sleep equivalents — rely on TestNG parallelism, not wall-clock waits.
    systemProperty("shardIndex", index)
    systemProperty("shardTotal", total)
}
```

The `matrix.shard-index` array length **must equal** `shard-total`; GitHub Actions has no `strategy: parallel: N` shorthand like Azure — the array is the source of truth. For dynamic/uneven sharding, compute the matrix JSON in an upstream `setup` job and pass it via `fromJSON(needs.setup.outputs.matrix)`. Commit a `api-tests/shards.txt` map (test → shard index) rather than re-discovering tests per shard at runtime.

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
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'
      - uses: gradle/actions/setup-gradle@v4

      - name: Verify Docker daemon (Testcontainers prereq)
        run: docker info

      - name: Run integration tests (Testcontainers)
        env:
          TESTCONTAINERS_RYUK_DISABLED: "false"
        run: ./gradlew :integration-tests:test --no-daemon

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: Integration tests
          path: 'integration-tests/build/test-results/test/TEST-*.xml'
          reporter: java-junit
          fail-on-error: true
```

### Selenium / Playwright-for-Java UI shard — `.github/workflows/_ui-tests.yml`

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
        shard-index: [1, 2, 3, 4]   # length must equal shard-total
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'
      - uses: gradle/actions/setup-gradle@v4

      # Playwright-for-Java only: install the browsers via the Gradle task.
      # (Selenium on ubuntu-latest uses the pre-installed Chrome — skip this step.)
      - name: Install Playwright browsers
        run: ./gradlew :e2e:installPlaywrightBrowsers --no-daemon
        # task wraps: com.microsoft.playwright.CLI install --with-deps chromium

      - name: Run UI tests (shard ${{ matrix.shard-index }}/${{ inputs.shard-total }})
        run: |
          ./gradlew :e2e:test \
            -PshardIndex=${{ matrix.shard-index }} \
            -PshardTotal=${{ inputs.shard-total }} \
            -Pheadless=true \
            --no-daemon

      - name: Upload UI failure artifacts (screenshots / traces, on failure only)
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: ui-failures-shard-${{ matrix.shard-index }}
          path: |
            e2e/build/screenshots
            e2e/build/playwright-traces
          retention-days: 14

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: UI shard ${{ matrix.shard-index }}
          path: 'e2e/build/test-results/test/TEST-*.xml'
          reporter: java-junit
          fail-on-error: true

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: allure-results-ui-${{ matrix.shard-index }}
          path: e2e/build/allure-results
          retention-days: 30
```

### Allure publish with history — `.github/workflows/_allure-publish.yml`

History lives on a `gh-pages` branch. `peaceiris/actions-gh-pages` with `keep_files: true` preserves the prior report's `history/` folder; `simple-elf/allure-report-action` reads it back in so trend charts survive across runs. This is the Pages-native equivalent of the Azure-Blob history dance in the `azure-pipelines/java` sibling — no `allure-commandline` install needed.

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

### Gatling perf gate — `.github/workflows/_gatling-perf.yml`

Gatling assertions in the simulation return a non-zero exit code when an SLO assertion fails. The step inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met). Gatling is the JVM-native perf tool here; keep k6 only if the org already standardized on it (then mirror the dotnet sibling's exit-99 gate).

```yaml
on:
  workflow_call:

jobs:
  gatling-perf:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'
      - uses: gradle/actions/setup-gradle@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Resolve target URL
        run: echo "GATLING_BASE_URL=$(az keyvault secret show --vault-name kv-qa --name api-base-url --query value -o tsv)" >> "$GITHUB_ENV"

      - name: Run Gatling (assertions enforce SLOs; non-zero exit on breach)
        run: ./gradlew :perf:gatlingRun --no-daemon

      - name: Upload Gatling report
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: gatling-report
          path: perf/build/reports/gatling
          retention-days: 30
```

## Rules

### Triggers
- `pull_request: [main]` + nightly `schedule`. Add `workflow_dispatch` so a human can re-run on demand.
- PR runs stay under 15 min by skipping perf and visual-regression (`if: github.event_name == 'schedule'`).
- A `schedule` cron only fires on the **default branch** — don't expect it on PR branches.

### Concurrency
- One `concurrency` group per ref. `cancel-in-progress: true` for PRs (kill superseded runs), `false` for nightly (let the full suite finish).

### Build tool
- **Always `gradle/actions/setup-gradle@v4`** — it restores and saves the Gradle dependency + build cache automatically; do not hand-roll `actions/cache` for `~/.gradle`.
- **Always `--no-daemon` in CI.** The Gradle daemon can survive between jobs on a warm runner and leak state; a cold, deterministic invocation is what you want in CI.
- Never mix Maven and Gradle in the same module.

### Sharding
- Default: 4 shards for UI, 2 for API, 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- `strategy.matrix` with **`fail-fast: false`** — one shard failing must not cancel the rest, or you lose the other shards' reports.
- The `shard-index` array length **must equal** `shard-total`. GitHub Actions has no `strategy: parallel: N` shorthand — the array is the source of truth. For uneven suites, pre-assign TestNG groups in code (`@Test(groups = "shard-1-of-4")`) or commit a `shards.txt` map; compute the matrix JSON in an upstream `setup` job and consume it with `fromJSON(needs.setup.outputs.matrix)` — never re-discover tests at runtime per shard.

### Secrets
- **OIDC only** via `permissions: id-token: write` + `azure/login@v2` (or `aws-actions/configure-aws-credentials` with `role-to-assume`). No PATs, no stored cloud secrets in repo/org settings.
- Store the federated identity's `client-id` / `tenant-id` / `subscription-id` as **`vars`** (non-sensitive), not `secrets` — they are identifiers, not credentials.
- Mask any secret value fetched at runtime with `echo "::add-mask::$SECRET"` **before** writing it to `$GITHUB_ENV`. Never `echo` a secret to the log, and never write it to a path an `upload-artifact` step picks up.
- `id-token: write` grants the run an OIDC token only — it does **not** grant repo write. Keep `contents: read` unless a step genuinely pushes (e.g. Allure → `gh-pages` needs `contents: write` in that job only).

### Reporters
- Always emit **both** JUnit-XML and Allure. TestNG's `useTestNG()` Gradle config writes JUnit XML under `build/test-results/test/`, which feeds `dorny/test-reporter` (`reporter: java-junit`, a Checks summary on the PR); the Allure-TestNG adapter writes `build/allure-results/` for humans with history.
- `fail-on-error: true` on every `test-reporter` step. The build must red on real failures. `./gradlew test` already exits non-zero on failure — do not swallow it with `continue-on-error`.

### Retry policy
- **No workflow-level retry** of failed tests (no `nick-fields/retry` wrapping the test step, no re-run-failed automation). Retry hides bugs.
- Per-test `IRetryAnalyzer` (`@Test(retryAnalyzer = ...)`) is allowed only for documented network-flake hotspots (third-party sandboxes, infra warm-up). Document each one in the annotation with a date and a JIRA link.
- For genuinely flaky tests, quarantine via `qa/reporting/java/skills/flaky-test-quarantine` — do not auto-retry.

### Artifacts
- JUnit results: 30 days (`retention-days: 30`).
- Screenshots / Playwright traces / HAR: 14 days, **only on failure** (`if: failure()`) to keep storage bounded.
- Allure: report + history persisted on `gh-pages` (or 90-day artifact when Pages is off).
- `actions/upload-artifact@v4` requires **unique artifact names** per job — suffix with `${{ matrix.shard-index }}`, or v4 fails the second upload. (This changed from v3's auto-merge behavior.)
- Container logs (Testcontainers): attach to Allure via the test listener, not as a separate artifact.

### Perf gate
- Gatling assertions live inline in the simulation (`.assertions(global.responseTime.percentile3.lt(500))`). The workflow does not interpret metrics.
- Gatling returns a non-zero exit code on assertion breach — the step fails automatically. Do not add `if`/`continue-on-error` guards.
- Pin the Gatling version in `build.gradle.kts`; upgrade in a dedicated PR.

### What NOT to do
- No `runs-on: windows-latest` for Linux-container tests (Docker on the Windows runner defaults to Windows containers → Testcontainers Linux modules fail).
- No PATs / `GITHUB_TOKEN` for cross-cloud auth — use OIDC federation.
- No `continue-on-error: true` on a test step to "make it green". Fix the test or quarantine it.
- No `./gradlew test` without `--no-daemon` in CI (the daemon survives between jobs unpredictably).
- No `--rerun-tasks` on Gradle to "fix" failures.
- No mixing of TestNG `parallel="methods"` with a fixture that owns a single Testcontainer instance — instant flake.
- No `actions/*@main` or `@v4`-floating on a moving tag for **security-relevant** actions (`azure/login`, `actions-gh-pages`) — pin to a full SHA in regulated repos.
- No reusing a static artifact name across matrix shards with v4 — it errors.
- No printing of `$AUTH0_M2M_SECRET` (or any fetched secret) in any step, even with `|| true`.

## Generation steps

1. Read any existing workflows under `.github/workflows/` to learn reusable-workflow conventions, `vars`/`secrets`, and the OIDC app already wired.
2. Inventory Gradle modules: `./gradlew projects` (or read `settings.gradle.kts`). Group them into API / integration / UI / perf (`api-tests`, `integration-tests`, `e2e`, `perf`).
3. Generate:
   - `.github/workflows/qa-tests.yml` (top-level orchestrator) if missing.
   - `.github/workflows/_{api,integration,ui}-tests.yml`, `_allure-publish.yml`, `_gatling-perf.yml` as reusable workflows (`on: workflow_call`).
   - Shard wiring in each module's `build.gradle.kts` (`-PshardIndex` / `-PshardTotal`).
4. Configure one federated identity credential on the Azure AD app (or AWS IAM role) trusting `repo:ORG/REPO:ref:refs/heads/main` and `:pull_request`. Document the subject claim in the workflow header comment. Store `client-id` / `tenant-id` / `subscription-id` as repo `vars`.
5. Validate locally with `actionlint` (and optionally `act` for a dry run), then open a draft PR and confirm every expected job and the Checks summary appear.

## Cross-references

- **`qa/cicd/dotnet/skills/ci-pipelines`** — the same-CI sibling this mirrors; consult it for the .NET / NUnit / TRX variant.
- **`references/azure-pipelines.md`** — the Azure sibling this ports from; consult it for the variable-group / service-connection variant of the same Gradle/TestNG patterns.
- **`qa/java/skills/db-testing/testcontainers`** — the integration-tests job runs these.
- **`qa/java/skills/email-testing`** — pair Mailpit as a `services:` container or inline Testcontainers run.
- **`qa/reporting/java/skills/test-reports`** — Allure-TestNG adapter wiring inside the test module that produces `build/allure-results/`.
- **`qa/java/skills/load-testing`** — perf-job simulations; SLO contract in `qa/_shared/performance`.
- **`devops/github-actions`** — non-QA workflow patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC) this skill enforces.
