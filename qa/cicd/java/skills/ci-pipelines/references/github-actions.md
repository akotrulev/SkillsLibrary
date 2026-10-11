# QA — GitHub Actions for Java Test Suites

Authors `.github/workflows/*.yml` that run TestNG suites — RestAssured API tests, Testcontainers-backed integration tests and Playwright-for-Java (or Selenium) UI tests — on GitHub-hosted `ubuntu-latest` runners using Java 21 + Gradle (Kotlin DSL). It shards via `strategy.matrix`, uploads the Playwright failure evidence, publishes Allure to GitHub Pages with history, fails on real failures (not flakes), and pulls secrets via OIDC federated credentials rather than PATs or stored cloud secrets.

**The UI lifecycle is not written here.** `qa/java/skills/ui-test-author/playwright/assets/BaseTest.java` owns it: it reads `BASE_URL` (required), runs headless unless `HEADED=1`, and on a failed test keeps a full-page screenshot, the trace and the video in `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`. The workflow runs that as is and uploads exactly that folder. `build/playwright-videos/` holds raw recordings `BaseTest` deletes after every test; it is never uploaded. What the evidence is and how to read it is `qa/java/skills/evidence-capture`.

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
2. Sharding fan-out? (default: 4 runners for UI, 2 for API/integration, 1 for perf)
3. Allure history destination? (default: GitHub Pages via a `gh-pages` branch; artifact-only when Pages is unavailable)

Infer everything else from `settings.gradle.kts` / `build.gradle.kts` and any existing workflows under `.github/workflows/`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `ubuntu-latest` (Docker pre-installed, passwordless `sudo`) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| JDK | Temurin 21 via `actions/setup-java@v5` (`distribution: temurin`) | Newer LTS only after 3 mo GA |
| Build tool | **Gradle Kotlin DSL** via `gradle/actions/setup-gradle@v4` (cache on) | Maven only for legacy modules |
| Playwright browsers | `./gradlew :e2e:installPlaywrightBrowsers` (J1's `JavaExec` task: `install --with-deps chromium`) | The pinned image `mcr.microsoft.com/playwright/java:v1.63.0-noble` for visual baselines (see the UI job) |
| Triggers | `pull_request: [main]` + nightly `schedule` cron | `push` on main only when the suite is < 5 min |
| Test framework reporter | JUnit-XML from TestNG (`build/test-results/test/`) + Allure-TestNG adapter | Always both — JUnit feeds `dorny/test-reporter`, Allure feeds humans |
| Sharding | `strategy.matrix` with `fail-fast: false`; `-PshardIndex/-PshardTotal` Gradle props | A committed shard map for uneven suites |
| Auth to Azure / AWS / Key Vault | OIDC federated credential (`id-token: write`) | Never PATs, never stored long-lived cloud secrets |
| Retry on failure | **Off at the workflow level** (no `nick-fields/retry` on the test step) | `@Test(retryAnalyzer = RetryOnce.class)` only on a documented network-flake hotspot — never blanket retry |
| Concurrency | `concurrency` group per ref, `cancel-in-progress: true` for PRs | Keep nightly runs un-cancelled (`cancel-in-progress: false`) |
| Artifact retention | 14 days for `build/playwright-artifacts/` (on failure only), 30 days for test results and Allure results, Allure history on `gh-pages` | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | Gatling assertions → non-zero exit → step fails | Soft gate (`continue-on-error`) only while a baseline is being established |

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
    uses: ./.github/workflows/_gatling-perf.yml
    secrets: inherit

  publish-allure:
    needs: [api-tests, integration-tests, ui-tests]
    if: ${{ !cancelled() }}
    uses: ./.github/workflows/_allure-publish.yml
```

- `if: ${{ !cancelled() }}` is the Actions equivalent of Azure's `condition: always()` minus the cancelled case — you want the report on red, but not on a user-cancelled run.
- `checks: write` lets `dorny/test-reporter` publish a Checks summary; `id-token: write` grants an OIDC token, not repo write. The nightly cron runs the full suite.

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
      fail-fast: false
      matrix:
        shard-index: [1, 2]
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 1 }

      - uses: actions/setup-java@v5
        with:
          distribution: temurin
          java-version: '21'

      - uses: gradle/actions/setup-gradle@v4

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
          fail-on-error: true

      - name: Upload JUnit results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: junit-api-${{ matrix.shard-index }}
          path: api-tests/build/test-results/test
          retention-days: 30

      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-api-${{ matrix.shard-index }}
          path: api-tests/build/allure-results
          retention-days: 30
```

- `fail-fast: false` — one shard failing must not cancel the others. The `shard-index` array length **must equal** `shard-total`.
- `fail-on-error: true` reds the check on real test failures.

Wire the shard params in the module's `build.gradle.kts` so each runner executes a disjoint slice:

```kotlin
tasks.test {
    val total = (project.findProperty("shardTotal") as String?)?.toInt() ?: 1
    val index = (project.findProperty("shardIndex") as String?)?.toInt() ?: 1
    useTestNG {
        suites("testng.xml")
        excludeGroups("flaky")
        if (total > 1) {
            includeGroups("shard-$index-of-$total")
        }
    }
}
```

Shards are 1-based. Each test class carries its pre-assigned `shard-<i>-of-<N>` group, so membership is decided once, in code; a committed `shards.txt` map works too. GitHub Actions has no `strategy: parallel: N` shorthand — the array is the source of truth. For a dynamic split, compute the matrix JSON in an upstream `setup` job and pass it via `fromJSON(needs.setup.outputs.matrix)`; never re-discover tests per shard at runtime. `excludeGroups("flaky")` keeps quarantined tests off the gate (`qa/reporting/java/skills/flaky-test-quarantine`).

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
      - uses: actions/checkout@v6
      - uses: actions/setup-java@v5
        with:
          distribution: temurin
          java-version: '21'
      - uses: gradle/actions/setup-gradle@v4

      - name: Verify Docker daemon
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

### Playwright-for-Java UI shard — `.github/workflows/_ui-tests.yml`

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
      - uses: actions/setup-java@v5
        with:
          distribution: temurin
          java-version: '21'
      - uses: gradle/actions/setup-gradle@v4

      - name: Install Playwright browsers + OS deps
        run: ./gradlew :e2e:installPlaywrightBrowsers --no-daemon

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
          ./gradlew :e2e:test \
            -PshardIndex=${{ matrix.shard-index }} \
            -PshardTotal=${{ inputs.shard-total }} \
            --no-daemon

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: ${{ !cancelled() }}
        with:
          name: UI shard ${{ matrix.shard-index }}
          path: 'e2e/build/test-results/test/TEST-*.xml'
          reporter: java-junit
          fail-on-error: true

      - name: Upload failure evidence
        uses: actions/upload-artifact@v5
        if: failure()
        with:
          name: playwright-artifacts-${{ matrix.shard-index }}
          path: e2e/build/playwright-artifacts
          retention-days: 14

      - name: Upload Allure results
        uses: actions/upload-artifact@v5
        if: ${{ !cancelled() }}
        with:
          name: allure-results-ui-${{ matrix.shard-index }}
          path: e2e/build/allure-results
          retention-days: 30
```

- **No headless flag.** `BaseTest` is headless unless `HEADED=1`, which only a local run sets; a `-Pheadless` or `-Dplaywright.headless` property is read by nothing.
- `installPlaywrightBrowsers` passes `--with-deps`, which installs OS packages through `sudo` on the runner. Browsers are pinned per Playwright version, so the 1.63.0 binding installs its own Chromium build; do not cache them (restore time is about the same as a download).
- `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come through OIDC: `BaseTest` throws without `BASE_URL`, and the sign-in `@BeforeSuite` (`AuthSetup`) needs the account.
- `e2e/build/playwright-artifacts` is uploaded **on failure only**: it holds the screenshot, trace and video of each failed test (`<Class>.<method>.{png,zip,webm}`) plus any deliberate recording. A green run leaves it empty.
- The quarantine lane is a second, non-gating job in this workflow — `./gradlew :e2e:flakyQuarantine --no-daemon` with `continue-on-error: true` and the same steps — per `qa/reporting/java/skills/flaky-test-quarantine`.
- **Selenium** suites drop the install step; `ubuntu-latest` ships Chrome and its driver.
- **Running in the pinned image** instead of installing browsers — what visual baselines need (`qa/java/skills/visual-regression`): give the job `container: { image: mcr.microsoft.com/playwright/java:v1.63.0-noble, options: --user 1001 }` and drop the install step. The tag must equal the Playwright version. The image ships OpenJDK 25, Maven and the browsers, but no JDK 21 and no Azure CLI: keep `actions/setup-java@v5` with Java 21 (the build's toolchain), and since `azure/login` needs the Azure CLI, a container job tests only pages that need no fetched credentials. The visual job is not a container job: it is the `docker run` step in `qa/java/skills/visual-regression/references/playwright-snapshots.md` §8.

### Allure publish with history — `.github/workflows/_allure-publish.yml`

History lives on a `gh-pages` branch: the published report's `history/` folder is copied into the new results before `allure generate`, so trend charts survive across runs. The report is generated with the one Allure CLI pin, `allure-commandline@2.46.1` (`qa/cicd/ci-conventions`), which reads allure-java 3.0 results and needs a Java runtime.

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
      - uses: actions/checkout@v6
      - uses: actions/setup-java@v5
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
        uses: actions/upload-artifact@v5
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
- The `shard-index` array length **must equal** `shard-total`. Shard membership is decided once (pre-assigned groups, a committed map, or an upstream `setup` job) — never re-discovered per shard at runtime.
- UI test classes run in parallel inside a shard through `testng.xml`'s `parallel="classes"` (J1's asset); never `parallel="methods"` with Playwright.

### Secrets
- **OIDC only** via `permissions: id-token: write` + `azure/login@v2` (or `aws-actions/configure-aws-credentials` with `role-to-assume`). No PATs, no stored cloud secrets in repo/org settings.
- Store the federated identity's `client-id` / `tenant-id` / `subscription-id` as **`vars`** (non-sensitive), not `secrets` — they are identifiers, not credentials.
- Mask any secret value fetched at runtime with `echo "::add-mask::$SECRET"` **before** writing it to `$GITHUB_ENV`. Never `echo` a secret to the log, and never write it to a path an `upload-artifact` step picks up. Traces and videos record what the page shows, so tests run as a disposable test user.
- `id-token: write` grants the run an OIDC token only — it does **not** grant repo write. Keep `contents: read` unless a step genuinely pushes (Allure → `gh-pages` needs `contents: write` in that job only).

### Reporters
- Always emit **both** JUnit-XML and Allure. TestNG's `useTestNG()` Gradle config writes JUnit XML under `build/test-results/test/`, which feeds `dorny/test-reporter` (`reporter: java-junit`, a Checks summary on the PR); the Allure-TestNG adapter writes `build/allure-results/` for humans with history.
- `fail-on-error: true` on every `test-reporter` step. The build must red on real failures. `./gradlew test` already exits non-zero on failure — do not swallow it with `continue-on-error`.

### Retry policy
- **No workflow-level retry** of failed tests (no `nick-fields/retry` wrapping the test step, no re-run-failed automation). Retry hides bugs.
- `@Test(retryAnalyzer = RetryOnce.class)` is allowed only on a documented network-flake hotspot (third-party sandboxes, infra warm-up), dated and linked to an issue at the test.
- For genuinely flaky tests, quarantine via `qa/reporting/java/skills/flaky-test-quarantine` — do not auto-retry.

### Artifacts
- JUnit and Allure results: 30 days (`retention-days: 30`), every run.
- `build/playwright-artifacts/` (screenshots, traces, videos, deliberate recordings): 14 days, **only on failure** (`if: failure()`). Never `build/playwright-videos/`.
- Allure: report + history persisted on `gh-pages` (or a 90-day artifact when Pages is off).
- `actions/upload-artifact` requires **unique artifact names** per job — suffix with `${{ matrix.shard-index }}`, or the second upload fails.
- Container logs (Testcontainers): attach to Allure via the test listener, not as a separate artifact.

### Perf gate
- Gatling assertions live inline in the simulation (`.assertions(global.responseTime.percentile3.lt(500))`). The workflow does not interpret metrics.
- Gatling returns a non-zero exit code on assertion breach — the step fails automatically. Do not add `if`/`continue-on-error` guards.
- Pin the Gatling version in `build.gradle.kts`; upgrade in a dedicated PR.

### What NOT to do
- No `runs-on: windows-latest` for Linux-container tests (Docker on the Windows runner defaults to Windows containers → Testcontainers Linux modules fail).
- No PATs / `GITHUB_TOKEN` for cross-cloud auth — use OIDC federation.
- No `continue-on-error: true` on a gating test step to "make it green". Fix the test or quarantine it (the quarantine job is the one non-gating exception).
- No `./gradlew test` without `--no-daemon` in CI (the daemon survives between jobs unpredictably).
- No `--rerun-tasks` on Gradle to "fix" failures.
- No `-Pheadless` / `-Dplaywright.headless` — nothing reads them.
- No upload of `build/playwright-videos/`, `build/screenshots/` or `build/playwright-traces/` — no skill writes the last two, and the first is scratch.
- No mixing of TestNG `parallel="methods"` with Playwright or with a fixture that owns a single Testcontainer instance — instant flake.
- No `actions/*@main`, and no floating major on **security-relevant** actions (`azure/login`, `actions-gh-pages`) in regulated repos — pin to a full SHA.
- No printing of `$AUTH0_M2M_SECRET`, `$E2E_PASSWORD` (or any fetched secret) in any step, even with `|| true`.

## Generation steps

1. Read any existing workflows under `.github/workflows/` to learn reusable-workflow conventions, `vars`/`secrets`, and the OIDC app already wired.
2. Inventory Gradle modules: `./gradlew projects` (or read `settings.gradle.kts`). Group them into API / integration / UI / perf (`api-tests`, `integration-tests`, `e2e`, `perf`). Confirm the UI module builds on J1's `build.gradle.kts` (the `installPlaywrightBrowsers` task) and `BaseTest`.
3. Generate:
   - `.github/workflows/qa-tests.yml` (top-level orchestrator) if missing.
   - `.github/workflows/_{api,integration,ui}-tests.yml`, `_allure-publish.yml`, `_gatling-perf.yml` as reusable workflows (`on: workflow_call`).
   - Shard wiring in each module's `build.gradle.kts` (`-PshardIndex` / `-PshardTotal`).
4. Configure one federated identity credential on the Azure AD app (or AWS IAM role) trusting `repo:ORG/REPO:ref:refs/heads/main` and `:pull_request`. Store `client-id` / `tenant-id` / `subscription-id` as repo `vars`.
5. Validate locally with `actionlint` (and optionally `act` for a dry run), then open a draft PR and confirm every expected job and the Checks summary appear.

## Cross-references

- **`qa/java/skills/ui-test-author/playwright`** — `BaseTest`, `build.gradle.kts` (`installPlaywrightBrowsers`, `playwright`) and `testng.xml` the UI job runs.
- **`qa/java/skills/evidence-capture`** — what `build/playwright-artifacts/` holds and how to read a failure's trace.
- **`qa/cicd/dotnet/skills/ci-pipelines`** — the same-CI sibling this mirrors; consult it for the .NET / NUnit / TRX variant.
- **`references/azure-pipelines.md`** — the Azure sibling this ports from; consult it for the variable-group / service-connection variant of the same Gradle/TestNG patterns.
- **`qa/java/skills/db-testing/testcontainers`** — the integration-tests job runs these.
- **`qa/java/skills/email-testing`** — pair Mailpit as a `services:` container or inline Testcontainers run.
- **`qa/reporting/java/skills/test-reports`** — Allure-TestNG adapter wiring inside the test module that produces `build/allure-results/`.
- **`qa/reporting/java/skills/flaky-test-quarantine`** — the `flaky` group the gate excludes and the quarantine task.
- **`qa/java/skills/load-testing`** — perf-job simulations; SLO contract in `qa/_shared/performance`.
- **`devops/github-actions`** — non-QA workflow patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) this skill enforces.
