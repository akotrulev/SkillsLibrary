# QA — GitLab CI/CD for Java Test Suites

Authors `.gitlab-ci.yml` that runs TestNG / Selenium / RestAssured / Testcontainers-backed integration tests on GitLab runners using Java 21 + Gradle (Kotlin DSL), shards for speed via `parallel:`, publishes Allure to GitLab Pages with history, fails on real failures (not flakes), and pulls secrets via `id_tokens:` cloud OIDC rather than long-lived CI/CD variables.

This is a **true port** of this skill's GitHub Actions reference (`references/github-actions.md`) — the *same* pipeline (same stages, same shard strategy, same artifacts, same gates), re-keyed to GitLab's `.gitlab-ci.yml` vocabulary, and the Java sibling of the canonical `qa/cicd/typescript/skills/ci-pipelines`. **Translate, don't redesign.** Only the YAML schema and a few primitives differ:

| Capability | GitHub Actions | GitLab CI (this skill) |
|---|---|---|
| Shard fan-out | `strategy.matrix` (array == `shard-total`) | `parallel: N` → `CI_NODE_INDEX`/`CI_NODE_TOTAL` |
| DAG / ordering | `needs:` between jobs | `needs:` (DAG) + `dependencies:` (artifact scope) |
| Cache | `gradle/actions/setup-gradle` | `cache:key:files:[build.gradle.kts]` (`~/.gradle/caches`) + `policy:` |
| JUnit summary | `dorny/test-reporter` (`java-junit`) | native `artifacts:reports:junit:` (`build/test-results`) |
| Cloud auth | `permissions: id-token: write` + `azure/login` | `id_tokens:` + `aud:` → assume role |
| Cancel superseded | `concurrency: cancel-in-progress` | `interruptible: true` + project auto-cancel |
| Gating | `if: github.event_name == 'schedule'` | `rules: - if: $CI_PIPELINE_SOURCE == "schedule"` |

The canonical TS sibling uses Playwright's native `blob` → `merge-reports` flow; Java has no blob reporter, so — exactly as in `github-actions` — each TestNG shard emits its own JUnit XML and Allure results, and the `pages` job merges the Allure results into one report. Gatling stays the perf tool (matching the `github-actions` java sibling's assertion gate).

## When to use

- New QA pipeline for a Java test module (`api-tests`, `integration-tests`, `e2e`, `perf`)
- Adding `parallel:` sharding to an existing serial pipeline
- Wiring Allure publish + history to GitLab Pages (or an artifact)
- Replacing long-lived cloud CI/CD variables with `id_tokens:` OIDC
- Adding a perf gate (Gatling) that breaks the pipeline on SLO regression

## When NOT to use

- GitHub Actions equivalent → `references/github-actions.md` in this skill
- Azure Pipelines equivalent → `references/azure-pipelines.md` in this skill
- App build / deploy pipelines unrelated to tests → `devops/gitlab-ci`
- Non-Java stacks — use the `dotnet` or `typescript` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which Gradle modules? (`api-tests`, `integration-tests`, `e2e`, multiple)
2. Sharding fan-out? (default: `parallel: 4` for Selenium UI, `parallel: 2` for API/integration, 1 for perf)
3. Allure history destination? (default: GitLab Pages with history in cache; artifact-only when Pages is disabled)

Infer everything else from `settings.gradle.kts` / `build.gradle.kts` and any existing `.gitlab-ci.yml`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `image: eclipse-temurin:21-jdk` on a `docker` runner | Self-hosted/shell runner only for proprietary hardware (mobile farm, GPU) |
| JDK | Temurin 21 (via the image) | Newer LTS only after 3 mo GA |
| Build tool | **Gradle Kotlin DSL** via the wrapper (`./gradlew`), `--no-daemon`, `GRADLE_USER_HOME` cached | Maven only for legacy modules |
| Cache | `cache:key:files:[build.gradle.kts, gradle/wrapper/gradle-wrapper.properties]` → `.gradle/caches`, `.gradle/wrapper` + `policy:` | — |
| Triggers | `merge_request_event` + nightly `schedule` (set via `workflow:rules`) | `push` on the default branch only when the suite is < 5 min |
| Test reporter | TestNG JUnit XML (`build/test-results/test/`) → `artifacts:reports:junit` + Allure-TestNG adapter | Always both — JUnit feeds the MR widget, Allure feeds humans |
| Sharding | `parallel: N`; runner reads `CI_NODE_INDEX`/`CI_NODE_TOTAL` into `-PshardIndex`/`-PshardTotal` Gradle props | Pre-computed group split via `@Test(groups="shard-i-of-N")` for uneven suites |
| Auth to AWS / Azure / Vault | `id_tokens:` + `aud:` → assume role (OIDC) | Never long-lived cloud keys; masked+protected CI/CD variables only for unavoidable tokens |
| Retry on failure | **Off at the pipeline level** (no `retry:` on the test job) | Per-test `IRetryAnalyzer` only for documented flake hotspots — never blanket `retry:` |
| Cancel superseded | `interruptible: true` + project "auto-cancel redundant pipelines" | Keep nightly un-interruptible |
| Artifact retention | `expire_in: 14 days` for screenshots/traces/HAR, `30 days` for test-results; Allure history in cache | Bump only with a stated reason |
| Perf gate | Gatling assertions → non-zero exit → job fails | Soft gate (`allow_failure: true`) only while a baseline is being established |

## Templates

### Top-level pipeline — `.gitlab-ci.yml`

```yaml
# Same pipeline as the github-actions sibling — GitLab vocabulary.
stages: [install, test, merge, perf, publish]

default:
  image: eclipse-temurin:21-jdk
  tags: [docker]              # a runner with the Docker executor
  interruptible: true         # GitLab analogue of cancel-in-progress for superseded MR pipelines

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

variables:
  # Keep Gradle's home inside the workspace so it can be cached, and never run the daemon in CI.
  GRADLE_USER_HOME: "$CI_PROJECT_DIR/.gradle"
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"

# Reusable Gradle cache anchor — keyed on the build script + wrapper so a dependency/version change busts it.
.gradle-cache: &gradle-cache
  cache:
    key:
      files: [build.gradle.kts, gradle/wrapper/gradle-wrapper.properties]
    paths: [.gradle/caches/, .gradle/wrapper/]
    policy: pull               # test jobs read; the install job writes (below)
```

The five stages map 1:1 onto the github-actions reusable workflows: `install` primes the Gradle cache, `test` fans out the sharded suites, `merge` is unused for Java (kept for family symmetry; the Allure merge happens in `publish`), `perf` runs the gated Gatling job, `publish` builds Allure on GitLab Pages. `GRADLE_USER_HOME` inside the workspace is what makes the Gradle cache cacheable — the default `~/.gradle` is outside GitLab's cacheable paths.

### Prime the Gradle cache — `install` stage

```yaml
install:
  stage: install
  cache:
    key:
      files: [build.gradle.kts, gradle/wrapper/gradle-wrapper.properties]
    paths: [.gradle/caches/, .gradle/wrapper/]
    policy: pull-push           # THIS job populates the cache; downstream jobs pull
  script:
    - ./gradlew dependencies --no-daemon   # resolve + warm the cache without running tests
```

One job owns `policy: pull-push`; every test job uses `<<: *gradle-cache` (`policy: pull`) so they never race to write the same key. **Always `--no-daemon` in CI** — the daemon can survive between jobs on a warm runner and leak state; a cold, deterministic invocation is what you want (it is also redundant with `GRADLE_OPTS=-Dorg.gradle.daemon=false`, but be explicit on the command line too).

### Sharded TestNG job — `test` stage

```yaml
api-tests:
  stage: test
  <<: *gradle-cache
  parallel: 2                   # GitLab sets CI_NODE_INDEX (1-based) and CI_NODE_TOTAL
  # OIDC token for the cloud — no stored secret. `aud` must match the role's trust policy.
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"
    - echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export API_BASE_URL="$(aws ssm get-parameter --name /qa/api-base-url --with-decryption --query Parameter.Value --output text)"
    # Gradle reads the shard props; the Test task includes only this shard's slice.
    - >
      ./gradlew :api-tests:test
      -PshardIndex=$CI_NODE_INDEX
      -PshardTotal=$CI_NODE_TOTAL
      --no-daemon
  artifacts:
    when: always                # collect reports even when tests fail
    expire_in: 30 days
    paths: [api-tests/build/allure-results/]
    reports:
      junit: api-tests/build/test-results/test/TEST-*.xml   # native MR test widget
```

Wire the shard props in `build.gradle.kts` so each runner executes a disjoint slice:

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
    // CLAUDE.md: no Thread.Sleep — rely on TestNG parallelism, not wall-clock waits.
    systemProperty("shardIndex", index)
    systemProperty("shardTotal", total)
}
```

`parallel: N` injects `CI_NODE_INDEX` (1-based) / `CI_NODE_TOTAL`, which feed `-PshardIndex`/`-PshardTotal` — the GitLab analogue of the github-actions `-PshardIndex=${{ matrix.shard-index }}` matrix slice, minus the array you'd otherwise keep in sync with the count. Commit a `api-tests/shards.txt` map (test → shard index) rather than re-discovering tests per shard at runtime.

> GitLab's native test widget parses the `artifacts:reports:junit` XML directly — it is the GitLab equivalent of `dorny/test-reporter` reading `java-junit`. `./gradlew test` exits non-zero on failure, which reds the pipeline; the widget just surfaces *which* tests failed. Do not add `allow_failure: true`.

### Integration tests with Testcontainers — `test` stage

Unlike GitHub-hosted runners (Docker pre-installed, socket mounted), a GitLab Docker-executor job has **no Docker daemon by default**. Add the `docker:dind` service and point Testcontainers at it. This is the one genuinely GitLab-specific wrinkle in the port.

```yaml
integration-tests:
  stage: test
  <<: *gradle-cache
  services:
    - name: docker:27-dind
      alias: docker
  variables:
    GRADLE_USER_HOME: "$CI_PROJECT_DIR/.gradle"
    GRADLE_OPTS: "-Dorg.gradle.daemon=false"
    DOCKER_HOST: "tcp://docker:2376"
    DOCKER_TLS_CERTDIR: "/certs"
    DOCKER_TLS_VERIFY: "1"
    DOCKER_CERT_PATH: "/certs/client"
    # Testcontainers must reach published ports at the dind host, not localhost.
    TESTCONTAINERS_HOST_OVERRIDE: "docker"
    TESTCONTAINERS_RYUK_DISABLED: "false"
  script:
    - docker info                       # fail fast if dind didn't come up
    - ./gradlew :integration-tests:test --no-daemon
  artifacts:
    when: always
    expire_in: 30 days
    reports:
      junit: integration-tests/build/test-results/test/TEST-*.xml
```

`TESTCONTAINERS_HOST_OVERRIDE: docker` is the critical line: with dind, containers' mapped ports are reachable at the `docker` service alias, not `localhost`. Keep Ryuk **enabled** — it reaps leaked containers between jobs on a warm runner. (Note: `<<: *gradle-cache` doesn't merge into a job's own `variables:`, so the Gradle vars are repeated here.) On a runner with a mounted host Docker socket, drop the `services:`/`DOCKER_*` block.

### Selenium / Playwright-for-Java UI shard — `test` stage

```yaml
ui-tests:
  stage: test
  <<: *gradle-cache
  parallel: 4
  script:
    # Playwright-for-Java: install browsers via the Gradle task. Selenium uses a browser image instead.
    - ./gradlew :e2e:installPlaywrightBrowsers --no-daemon   # wraps: playwright install --with-deps chromium
    - >
      ./gradlew :e2e:test
      -PshardIndex=$CI_NODE_INDEX
      -PshardTotal=$CI_NODE_TOTAL
      -Pheadless=true
      --no-daemon
  artifacts:
    # One artifacts block per job, one expire_in — screenshots/traces ride with the
    # results here. Have the listener write screenshots on failure only so the 14-day
    # bucket stays small; a separate `needs:`-download job would collect nothing new.
    when: always
    expire_in: 14 days
    paths:
      - e2e/build/allure-results/
      - e2e/build/screenshots/
      - e2e/build/playwright-traces/
    reports:
      junit: e2e/build/test-results/test/TEST-*.xml
```

For Selenium on a headless runner, run against a `selenium/standalone-chrome` service (`services:` + `alias`) or the browser preinstalled in a custom image, rather than installing Chrome inline.

### Allure publish with history — `publish` stage (GitLab Pages)

GitLab has no `gh-pages` branch. The native deliverable is **GitLab Pages**: a job literally named `pages` that publishes a `public/` directory. Allure trend history (the `history/` folder) is carried across pipelines in a **dedicated cache with a stable key** — the GitLab analogue of `keep_files: true` on `gh-pages`. The `pages` job collects the per-shard `allure-results/` and generates one report (the Java analogue of `github-actions`'s gh-pages publish, since there is no Playwright blob to merge).

```yaml
pages:
  stage: publish
  image: eclipse-temurin:21-jdk        # allure-commandline needs a JRE; Node for the CLI install
  needs:
    - job: api-tests
      artifacts: true
    - job: ui-tests
      artifacts: true
  when: always                         # publish even when a test job failed
  cache:
    key: allure-history                # stable key — NOT the build script — so history persists
    paths: [allure-history/]
    policy: pull-push
  before_script:
    - apt-get update && apt-get install -y npm
  script:
    - npm i -g allure-commandline@2.30.0
    # Gather every module's results.
    - mkdir -p allure-results && find . -type d -name allure-results -path '*/build/*' -exec cp -r {}/. allure-results/ \;
    # Re-seed history from the prior run before generating.
    - mkdir -p allure-results/history && cp -r allure-history/* allure-results/history/ 2>/dev/null || true
    - allure generate allure-results --clean -o public
    - rm -rf allure-history && cp -r public/history allure-history
  artifacts:
    paths: [public/]
    expire_in: 30 days
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

When GitLab Pages is disabled, drop the `pages` name and the Pages `rules`, keep the same script, and publish `public/` as a plain artifact with `expire_in: 90 days`.

### Gatling perf gate — `perf` stage

Gatling assertions in the simulation return a non-zero exit code when an SLO assertion fails; the job inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met). Gatling is the JVM-native perf tool and matches the `github-actions` java sibling's assertion gate; keep k6 only if the org already standardized on it (then mirror the dotnet sibling's exit-99 gate). Gate it to the nightly schedule so MRs stay fast.

```yaml
gatling-perf:
  stage: perf
  <<: *gradle-cache
  needs: ["api-tests"]
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"; echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export GATLING_BASE_URL="$(aws ssm get-parameter --name /qa/api-base-url --query Parameter.Value --output text)"
    - ./gradlew :perf:gatlingRun --no-daemon
  artifacts:
    when: always
    expire_in: 30 days
    paths: [perf/build/reports/gatling/]
```

## Rules

### Triggers
- `workflow:rules` allowing `merge_request_event` + default branch + `schedule`. Create the nightly run in **CI/CD → Schedules** (it runs on the default branch).
- MR pipelines stay under 15 min by gating perf to `schedule`.
- Avoid duplicate pipelines by not also matching `push` for branches with an open MR.

### Cancel superseded
- `interruptible: true` + project **"Auto-cancel redundant pipelines"** — the GitLab analogue of `concurrency: cancel-in-progress`. Leave nightly un-interruptible.

### Build tool
- **Always `--no-daemon` in CI** (and `GRADLE_OPTS=-Dorg.gradle.daemon=false`). The daemon survives between jobs on a warm runner unpredictably.
- Cache `.gradle/caches` + `.gradle/wrapper` via `GRADLE_USER_HOME=$CI_PROJECT_DIR/.gradle` and `cache:key:files:[build.gradle.kts, gradle-wrapper.properties]` — the default `~/.gradle` is outside GitLab's cacheable paths.
- **One `install` job with `policy: pull-push`** populates the cache; every other job uses `<<: *gradle-cache` (`policy: pull`). Two jobs writing the same key race.
- Never mix Maven and Gradle in the same module.

### Sharding
- Default: `parallel: 4` for UI, `parallel: 2` for API, 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- The runner reads **`CI_NODE_INDEX`** (1-based) / **`CI_NODE_TOTAL`** — GitLab injects both from `parallel: N`. Feed them into `-PshardIndex`/`-PshardTotal`; pre-assign TestNG groups (`@Test(groups="shard-1-of-4")`) or commit a `shards.txt` map. Never re-discover tests per shard at runtime.

### Reporters
- Always emit **both** TestNG's JUnit XML (`build/test-results/test/`) into **`artifacts:reports:junit`** and Allure-TestNG results. JUnit feeds GitLab's native MR widget (the `dorny/test-reporter` equivalent); Allure feeds humans with history.
- `./gradlew test` exits non-zero on failure → the pipeline reds automatically. Do not mask it with `allow_failure: true`.

### Secrets
- **`id_tokens:` OIDC only** — declare the block with the cloud's `aud:`, exchange for short-lived creds, then read secrets. No long-lived AWS keys / Azure secrets in CI/CD variables.
- The unavoidable token (third-party SaaS key with no OIDC) → **masked + protected** CI/CD variable scoped to protected branches.
- The `aud:` value **must match** the cloud role's trust-policy condition, or `AssumeRoleWithWebIdentity` is rejected.
- Never `echo` a fetched secret; never write it to an `artifacts:paths:` location.

### Retry policy
- **No pipeline-level retry** of failed tests (no `retry:` on the test job). Retry hides bugs.
- Per-test `IRetryAnalyzer` only for documented network-flake hotspots — document each with a date + JIRA link in the annotation.
- `retry:` in GitLab is for **infrastructure** failures only (`when: runner_system_failure`), never assertions. For chronic flakes, quarantine via `qa/reporting/java/skills/flaky-test-quarantine`.

### Artifacts
- JUnit results: `expire_in: 30 days` (on the `api-tests` / `integration-tests` jobs).
- Screenshots / Playwright traces / HAR: `expire_in: 14 days` on the `ui-tests` job — one `artifacts:` block per job, one `expire_in`, so they ride with the results there. Have the TestNG listener write screenshots on failure only rather than a `needs:`-download-then-reupload job.
- Allure history: carried in a **dedicated cache** keyed on a stable string (`allure-history`), **not** the build script.
- Don't double-declare the same files under `paths:` and `reports:`.

### Perf gate
- Gatling assertions live inline in the simulation (`.assertions(global.responseTime.percentile3.lt(500))`). The pipeline does not interpret metrics.
- Gatling returns a non-zero exit code on assertion breach — the job fails automatically. Do not add guards that swallow it.
- Pin the Gatling version in `build.gradle.kts`; upgrade in a dedicated MR.

### What NOT to do
- No Testcontainers without `docker:dind` (+ `TESTCONTAINERS_HOST_OVERRIDE: docker`) or a mounted host socket.
- No long-lived cloud keys in CI/CD variables — use `id_tokens:` OIDC.
- No `allow_failure: true` on a test job to "make it green".
- No `./gradlew test` without `--no-daemon` in CI.
- No `--rerun-tasks` to "fix" failures.
- No mixing TestNG `parallel="methods"` with a fixture that owns a single Testcontainer — instant flake.
- No two jobs writing the same `cache:key` (`policy: pull-push`) — one `install` job writes, the rest pull.
- No `retry:` on test assertions — reserve it for `runner_system_failure`.
- No printing of a fetched secret, even with `|| true`.

## Generation steps

1. Read any existing `.gitlab-ci.yml` to learn runner tags, `image:`, existing `id_tokens:`/variables, and stage conventions.
2. Inventory Gradle modules: `./gradlew projects` (or read `settings.gradle.kts`). Group into API / integration / UI / perf (`api-tests`, `integration-tests`, `e2e`, `perf`).
3. Generate `.gitlab-ci.yml` with `stages: [install, test, merge, perf, publish]`, the `.gradle-cache` anchor, one `install` job (`policy: pull-push`), the sharded `api-tests` / `ui-tests` jobs, the dind `integration-tests` job, the `pages` Allure job, and the gated `gatling-perf` job. Add the `-PshardIndex`/`-PshardTotal` wiring in each module's `build.gradle.kts`.
4. Configure cloud OIDC: register GitLab as an OIDC provider, create the role with a trust policy keyed on the project/ref claims, set `id_tokens:` `aud:` to match. Document the subject claim in a header comment.
5. Validate with **CI Lint** (Pipelines → CI Lint) or `glab ci lint`, then open a draft MR and confirm every expected job and the MR test widget appear.

## Cross-references

- **`qa/cicd/typescript/skills/ci-pipelines`** (canonical) + **`qa/cicd/dotnet/skills/ci-pipelines`** — the same-CI siblings; the TS one shows the Playwright `blob`/`merge-reports` flow this stack replaces with a per-shard Allure merge.
- **`references/github-actions.md`** — the structural template this ports from; the `strategy.matrix` / `dorny/test-reporter` (`java-junit`) variant.
- **`references/azure-pipelines.md`** — the Azure sibling; the `strategy: parallel` / service-connection variant.
- **`qa/java/skills/db-testing/testcontainers`** — the integration-tests job runs these (needs the `docker:dind` service shown above).
- **`qa/java/skills/network-mocking`** — runs an **external MITM proxy** (BrowserUp) the job must start/stop, whose **CA the client must trust** (per-run — no stored secret); the in-process `playwright-routes`/`cdp` specs need no extra plumbing.
- **`qa/java/skills/network-mocking`** — in-process CDP specs the `ui-tests` job runs directly.
- **`qa/reporting/java/skills/test-reports`** — Allure-TestNG adapter wiring that produces `build/allure-results/`.
- **`qa/java/skills/load-testing`** — perf-job simulations; SLO contract in `qa/_shared/performance`.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC) this skill enforces.
