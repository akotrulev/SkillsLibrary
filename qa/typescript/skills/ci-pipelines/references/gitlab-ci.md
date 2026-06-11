# QA — GitLab CI/CD for TypeScript Test Suites

Authors `.gitlab-ci.yml` that runs Vitest / Jest / Playwright / Testcontainers-backed integration tests on GitLab runners using Node 20 + TypeScript (strict), shards for speed via `parallel:`, publishes Allure (and/or Playwright's own HTML report) to GitLab Pages with history, fails on real failures (not flakes), and pulls secrets via `id_tokens:` cloud OIDC rather than long-lived CI/CD variables.

This is a **true port** of `qa/typescript/skills/ci-pipelines` — the *same* pipeline (same stages, same shard strategy, same artifacts, same gates), re-keyed to GitLab's `.gitlab-ci.yml` vocabulary. **Translate, don't redesign.** The capability set is identical to the two CI siblings; only the YAML schema and a few primitives differ:

| Capability | GitHub Actions | GitLab CI (this skill) |
|---|---|---|
| Shard fan-out | `strategy.matrix` (array == `shard-total`) | `parallel: N` → `CI_NODE_INDEX`/`CI_NODE_TOTAL` |
| DAG / ordering | `needs:` between jobs | `needs:` (DAG) + `dependencies:` (artifact scope) |
| Report merge | `download-artifact merge-multiple` + `merge-reports` job | `needs: [e2e]` pulls all parallel artifacts → `merge-reports` job |
| Cache | `actions/setup-node cache:` | `cache:key:files:[package-lock.json]` + `policy:` |
| JUnit summary | `dorny/test-reporter` | native `artifacts:reports:junit:` |
| Cloud auth | `permissions: id-token: write` + `azure/login` | `id_tokens:` + `aud:` → assume role |
| Cancel superseded | `concurrency: cancel-in-progress` | `interruptible: true` + project auto-cancel |
| Gating | `if: github.event_name == 'schedule'` | `rules: - if: $CI_PIPELINE_SOURCE == "schedule"` |

**TypeScript is canonical for the CI family** (like `github-actions`/`azure-pipelines`): Playwright ships first-class `--shard=i/N` and a `blob` reporter → `merge-reports` flow, so the UI stage is a single merge job rather than the per-shard Allure-merge dance the dotnet/java siblings need. k6 stays the perf tool (JS-native here, same exit-99 gate as the dotnet sibling).

## When to use

- New QA pipeline for a TS test project (`api-tests`, `integration`, `e2e`, `perf`)
- Adding `parallel:` sharding to an existing serial pipeline
- Merging Playwright `blob` reports from N shards into one HTML report
- Wiring Allure publish + history to GitLab Pages (or an artifact)
- Replacing long-lived cloud CI/CD variables with `id_tokens:` OIDC
- Adding a perf gate (k6) that breaks the pipeline on SLO regression

## When NOT to use

- GitHub Actions equivalent → `qa/typescript/skills/ci-pipelines`
- Azure Pipelines equivalent → `qa/typescript/skills/ci-pipelines`
- App build / deploy pipelines unrelated to tests → `devops/gitlab-ci`
- Non-TS stacks — use the `dotnet` or `java` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test runners? (Vitest, Jest, Playwright, k6 — and which package dirs)
2. Sharding fan-out? (default: `parallel: 4` for Playwright UI, `parallel: 2` for Vitest API/integration, 1 for perf)
3. Report destination? (default: Playwright HTML for UI + Allure on GitLab Pages with history in cache; artifact-only when Pages is disabled)

Infer everything else from `package.json`, `playwright.config.ts`, `vitest.config.ts`, the lockfile (`pnpm-lock.yaml` / `package-lock.json` / `yarn.lock`), and any existing `.gitlab-ci.yml`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `image: node:20-bookworm` on a `docker` runner | Self-hosted/shell runner only for proprietary hardware (mobile farm, GPU) |
| Node | 20 LTS via the `node:20` image, version pinned by `.nvmrc` | Newer LTS only after 3 mo GA |
| Package manager / cache | Detect from lockfile; `cache:key:files:[<lockfile>]` + `policy:` + frozen install (`npm ci` / `pnpm install --frozen-lockfile`) | Match whatever the repo already uses — never switch managers in a CI MR |
| Triggers | `merge_request_event` + nightly `schedule` (set via `workflow:rules`) | `push` on the default branch only when the suite is < 5 min |
| Test reporter | Vitest/Jest: `jest-junit` → `artifacts:reports:junit` + Allure adapter. Playwright: `blob` in CI + `allure-playwright` | Always emit JUnit XML for the native MR widget; Playwright's HTML can stand in for Allure on UI-only repos |
| Sharding | `parallel: N`; runner reads `CI_NODE_INDEX`/`CI_NODE_TOTAL` into Vitest/Playwright `--shard=$CI_NODE_INDEX/$CI_NODE_TOTAL` | `parallel:matrix:` for browser × shard fan-out |
| Auth to AWS / Azure / Vault | `id_tokens:` + `aud:` → assume role (OIDC) | Never long-lived cloud keys; masked+protected CI/CD variables only for unavoidable tokens |
| Retry on failure | **Off at the pipeline level** (no `retry:` on the test job); `retries: 0` in CI | Per-project `retries` only for documented flake hotspots — never blanket `retry:` |
| Cancel superseded | `interruptible: true` + project "auto-cancel redundant pipelines" | Keep nightly un-interruptible (omit `interruptible` / set `false`) |
| Artifact retention | `expire_in: 14 days` for traces/videos/HAR, `30 days` for JUnit + blob reports; Allure history carried in cache | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | k6 thresholds → exit code 99 → job fails | Soft gate (`allow_failure: true`) only while a baseline is being established |

## Templates

### Top-level pipeline — `.gitlab-ci.yml`

```yaml
# Same pipeline as the github-actions sibling — GitLab vocabulary.
stages: [install, test, merge, perf, publish]

default:
  image: node:20-bookworm
  tags: [docker]              # a runner with the Docker executor
  interruptible: true         # GitLab analogue of cancel-in-progress for superseded MR pipelines

# Build the pipeline only for MRs, the default branch, and the nightly schedule.
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

variables:
  NODE_VERSION: "20"
  npm_config_cache: "$CI_PROJECT_DIR/.npm"   # cacheable npm store inside the workspace

# Reusable cache anchor — keyed on the lockfile so a dependency change busts it.
.node-cache: &node-cache
  cache:
    key:
      files: [package-lock.json]   # pnpm-lock.yaml / yarn.lock for those managers
    paths: [.npm/, node_modules/]
    policy: pull                    # test jobs read; the install job writes (below)
```

The five stages map 1:1 onto the github-actions reusable workflows: `install` primes the dependency cache, `test` fans out the sharded suites, `merge` stitches the Playwright blobs, `perf` runs the gated k6 job, `publish` builds Allure on GitLab Pages. `workflow:rules` replaces the Actions `on:` block — a nightly `schedule` is created in **CI/CD → Schedules** on the default branch.

### Prime the dependency cache — `install` stage

```yaml
install:
  stage: install
  cache:
    key:
      files: [package-lock.json]
    paths: [.npm/, node_modules/]
    policy: pull-push            # THIS job populates the cache; downstream jobs pull
  script:
    - npm ci --cache .npm --prefer-offline   # frozen, reproducible install — never bare `npm install`
```

One job owns `policy: pull-push`; every test job uses `<<: *node-cache` (`policy: pull`) so they never race to write the same key. For pnpm, swap to `pnpm install --frozen-lockfile --store-dir .pnpm-store` and cache `.pnpm-store/`; for yarn, `yarn install --immutable` and cache `.yarn/cache/`. **Detect the manager from the lockfile and match it — never switch in a CI MR.**

### Sharded Vitest job — `test` stage

```yaml
api-tests:
  stage: test
  <<: *node-cache
  parallel: 2                   # GitLab sets CI_NODE_INDEX (1-based) and CI_NODE_TOTAL
  # OIDC token for the cloud — no stored secret. `aud` must match the role's trust policy.
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    # Exchange the GitLab ID token for short-lived AWS creds, then read secrets.
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"
    - echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export API_BASE_URL="$(aws ssm get-parameter --name /qa/typescript/skills/api-base-url --with-decryption --query Parameter.Value --output text)"
    # Vitest splits the suite deterministically across CI_NODE_TOTAL runners.
    - >
      npx vitest run
      --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL
      --reporter=default
      --reporter=junit
      --outputFile.junit=reports/junit-api-$CI_NODE_INDEX.xml
  artifacts:
    when: always                # collect reports even when tests fail
    expire_in: 30 days
    paths: [allure-results/]
    reports:
      junit: reports/junit-api-*.xml   # native MR test widget — no third-party action
```

`vitest run --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL` (Vitest ≥1.4) is the exact analogue of the github-actions `--shard=${{ matrix.shard-index }}/${{ inputs.shard-total }}` — except GitLab's `parallel: N` *injects* `CI_NODE_INDEX`/`CI_NODE_TOTAL` for you, so there is no array to keep in sync with the count (the `github-actions` footgun). For Jest, swap to `jest --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL` and configure `jest-junit` in `jest.config.ts`. For browser × shard fan-out use `parallel:matrix:` instead of a bare `parallel: N`.

> GitLab's native test widget parses the `artifacts:reports:junit` XML directly — it is the GitLab equivalent of `dorny/test-reporter`. The job's own non-zero exit (Vitest exits non-zero on failure) reds the pipeline; the widget just surfaces *which* tests failed. Do not add `allow_failure: true` to "make it green".

### Integration tests with Testcontainers — `test` stage

Unlike GitHub-hosted runners (Docker pre-installed, socket mounted), a GitLab Docker-executor job has **no Docker daemon by default**. Add the `docker:dind` service and point Testcontainers at it. This is the one genuinely GitLab-specific wrinkle in the port.

```yaml
integration-tests:
  stage: test
  <<: *node-cache
  services:
    - name: docker:27-dind
      alias: docker
  variables:
    DOCKER_HOST: "tcp://docker:2376"
    DOCKER_TLS_CERTDIR: "/certs"
    DOCKER_TLS_VERIFY: "1"
    DOCKER_CERT_PATH: "/certs/client"
    # Testcontainers must reach published ports at the dind host, not localhost.
    TESTCONTAINERS_HOST_OVERRIDE: "docker"
    TESTCONTAINERS_RYUK_DISABLED: "false"
  script:
    - docker info                       # fail fast if dind didn't come up
    - >
      npx vitest run --config vitest.integration.config.ts
      --reporter=default
      --reporter=junit
      --outputFile.junit=reports/junit-integration.xml
  artifacts:
    when: always
    expire_in: 30 days
    reports:
      junit: reports/junit-integration.xml
```

`TESTCONTAINERS_HOST_OVERRIDE: docker` is the critical line: with dind, containers' mapped ports are reachable at the `docker` service alias, not `localhost`. Keep Ryuk **enabled** — it reaps leaked containers between jobs on a warm runner. (On a runner configured with a mounted host Docker socket instead of dind, drop the `services:`/`DOCKER_*` block and this behaves like the github-actions sibling.)

### Playwright UI shard with blob merge — `test` + `merge` stages

Playwright's **native** sharding + `blob` reporter is the TS-native path, exactly as in `github-actions`: each shard writes a blob, and a `merge-reports` job stitches them into one HTML report. The GitLab twist: a `needs: [e2e]` job pulls the artifacts of **every** parallel `e2e` instance into one workspace — but each shard's blob must have a **unique filename** or they overwrite each other on download. Set `PLAYWRIGHT_BLOB_OUTPUT_FILE` per shard. Set `reporter: process.env.CI ? [['blob'], ['allure-playwright']] : 'html'` and `retries: 0` in `playwright.config.ts`.

```yaml
e2e:
  stage: test
  <<: *node-cache
  parallel: 4
  script:
    - npx playwright install --with-deps chromium
    # Unique blob name per shard — else parallel artifacts collide on merge (GitLab gotcha).
    - export PLAYWRIGHT_BLOB_OUTPUT_FILE="blob-report/report-$CI_NODE_INDEX.zip"
    - npx playwright test --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL
  artifacts:
    # A GitLab job has ONE artifacts block with ONE expire_in. Traces ride with the
    # blob here; Playwright's `trace: 'retain-on-failure'` means they only materialize
    # on a failing test, so no separate on_failure gating job is needed (and a
    # `needs:`-download-then-reupload job would be pointless).
    when: always
    expire_in: 14 days                 # heavy traces dominate; keep short
    paths:
      - blob-report/
      - allure-results/
      - test-results/                  # Playwright traces/videos (failure-only via config)
    reports:
      junit: blob-report/junit-*.xml   # if also emitting the junit reporter

merge-reports:
  stage: merge
  <<: *node-cache
  needs: ["e2e"]                       # pulls ALL parallel e2e artifacts into one workspace
  when: always                         # produce the report even on red
  script:
    - npx playwright merge-reports --reporter html ./blob-report
  artifacts:
    when: always
    expire_in: 30 days
    paths: [playwright-report/]
```

`needs: ["e2e"]` against a `parallel:` job downloads the blob artifacts from all four shards into `blob-report/`; the unique per-shard filenames keep them from clobbering one another, and `merge-reports --reporter html` produces a single browsable report. On a UI-only repo you can stop here and skip Allure entirely — Playwright's HTML report with traces is a complete, lighter-weight deliverable.

### Allure publish with history — `publish` stage (GitLab Pages)

GitLab has no `gh-pages` branch. The native deliverable is **GitLab Pages**: a job literally named `pages` that publishes a `public/` directory. Allure trend history (the `history/` folder) is carried across pipelines in a **dedicated cache with a stable key** — the GitLab analogue of `keep_files: true` on `gh-pages`.

```yaml
pages:
  stage: publish
  needs:
    - job: api-tests
      artifacts: true
    - job: e2e
      artifacts: true
  when: always                         # publish even when a test job failed
  cache:
    key: allure-history                # stable key — NOT the lockfile — so history persists
    paths: [allure-history/]
    policy: pull-push
  script:
    - npm i -g allure-commandline@2.30.0
    # Re-seed history from the prior run before generating.
    - mkdir -p allure-results/history && cp -r allure-history/* allure-results/history/ 2>/dev/null || true
    - allure generate allure-results --clean -o public
    # Persist the new history for the next pipeline.
    - rm -rf allure-history && cp -r public/history allure-history
  artifacts:
    paths: [public/]                   # GitLab Pages serves this
    expire_in: 30 days
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH   # publish Pages from the default branch only
```

When GitLab Pages is disabled (policy, self-managed without Pages), drop the `pages` name and the Pages `rules`, keep the same script, and publish `public/` as a plain artifact with `expire_in: 90 days` — you lose the hosted browse, not the report or its history.

### k6 perf gate — `perf` stage

k6 returns exit code 99 when thresholds break; the job inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met). Gate it to the nightly schedule with `rules:` so MRs stay fast. k6 is the JS-native perf tool here — keep it (do not swap to Gatling/NBomber in the TS stack).

```yaml
k6-perf:
  stage: perf
  image: grafana/k6:0.52.0             # pinned; upgrade in a dedicated MR
  needs: ["api-tests"]
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"   # nightly only — keep MRs under 15 min
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"; echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export K6_BASE_URL="$(aws ssm get-parameter --name /qa/typescript/skills/api-base-url --query Parameter.Value --output text)"
    - k6 run --out json=k6-summary.json perf/scenarios/checkout.js
  artifacts:
    when: always
    expire_in: 30 days
    paths: [k6-summary.json]
```

## Rules

### Triggers
- `workflow:rules` allowing `merge_request_event` + default branch + `schedule`. Create the nightly run in **CI/CD → Schedules** (it runs on the default branch).
- MR pipelines stay under 15 min by gating perf and visual-regression to `schedule` (`rules: - if: $CI_PIPELINE_SOURCE == "schedule"`).
- Prefer MR pipelines over branch pipelines; avoid duplicate pipelines by not also matching `push` for branches that have an open MR.

### Cancel superseded
- `interruptible: true` on jobs + enable **"Auto-cancel redundant pipelines"** in project CI/CD settings. This is the GitLab analogue of `concurrency: cancel-in-progress`. Leave nightly jobs un-interruptible if a full run must always finish.

### Package manager
- **Detect the manager from the lockfile and match it** — `pnpm-lock.yaml` → pnpm, `package-lock.json` → npm, `yarn.lock` → yarn. Never switch managers in a CI MR.
- **One `install` job with `policy: pull-push`** populates the cache; every other job uses the `<<: *node-cache` anchor with `policy: pull`. Two jobs writing the same cache key race and corrupt it.
- **Frozen, reproducible installs only**: `npm ci` / `pnpm install --frozen-lockfile` / `yarn install --immutable`. Never bare `npm install` in CI.

### Sharding
- Default: `parallel: 4` for UI (Playwright `--shard`), `parallel: 2` for API (Vitest `--shard`), 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- The runner reads **`CI_NODE_INDEX`** (1-based) and **`CI_NODE_TOTAL`** — GitLab injects both from `parallel: N`, so there is no array to keep in sync with the count (unlike the github-actions matrix).
- For browser × shard fan-out, use `parallel:matrix:` with explicit dimension lists.

### Reporters
- Always emit a **JUnit-shaped XML** (`vitest --reporter=junit` / `jest-junit`) into **`artifacts:reports:junit`** — GitLab's native MR test widget parses it directly (the `dorny/test-reporter` equivalent). Plus the human-facing report (Allure adapter, or Playwright's own HTML).
- For Playwright, use the **`blob` reporter in CI** with a **per-shard `PLAYWRIGHT_BLOB_OUTPUT_FILE`** and merge with `npx playwright merge-reports` in a `needs:`-gated job.
- The job's own non-zero exit reds the pipeline. Vitest/Playwright already exit non-zero on failure — do not mask it with `allow_failure: true`.

### Secrets
- **`id_tokens:` OIDC only** — declare an `id_tokens:` block with the cloud's `aud:`, exchange the token for short-lived creds, then read secrets. No long-lived AWS keys / Azure secrets in CI/CD variables.
- For the unavoidable token (e.g. a third-party SaaS API key with no OIDC), use a **masked + protected** CI/CD variable scoped to protected branches — never a plain variable, never committed to `.gitlab-ci.yml`.
- The `aud:` value **must match** the cloud role's trust-policy condition (e.g. the IAM role's `sub`/`aud` claim check), or the `AssumeRoleWithWebIdentity` call is rejected.
- Never `echo` a fetched secret, and never write it to a path an `artifacts:paths:` picks up. Mask is best-effort — don't rely on it for log hygiene.

### Retry policy
- **No pipeline-level retry** of failed tests (no `retry:` on the test job, no manual re-run-failed habit). Retry hides bugs.
- `playwright.config.ts → retries: 0` in CI. Per-project `retries` (or Vitest `test.retry`) only for documented network-flake hotspots (third-party sandboxes, infra warm-up). Document each with a date and an issue link in a code comment.
- `retry:` in GitLab is for **infrastructure** failures only (`when: runner_system_failure`), never test assertions. For genuinely flaky tests, quarantine via `qa/typescript/skills/flaky-test-quarantine`.

### Artifacts
- JUnit results + merged Playwright HTML report: `expire_in: 30 days` (on the `merge-reports` / `install` jobs).
- Playwright blob + traces / videos: `expire_in: 14 days` on the `e2e` job — a GitLab job has **one** `artifacts:` block with one `expire_in`, so traces ride with the blob there. Keep them small by configuring `trace: 'retain-on-failure'` in `playwright.config.ts` (traces only materialize on a failing test) rather than splitting into a `needs:`-download-then-reupload job, which collects nothing new.
- Allure history: carried across pipelines in a **dedicated cache** keyed on a stable string (`allure-history`), **not** the lockfile.
- `artifacts:reports:junit` paths are **also** uploaded as normal artifacts — don't double-declare the same files under `paths:` and `reports:`.

### Perf gate
- k6 thresholds live inline in the script (`thresholds: { http_req_duration: ['p(95)<500'] }`). The pipeline does not interpret metrics.
- k6 returns exit code 99 on threshold breach — the job fails automatically. Do not add `allow_failure` / `rules` that swallow the failure.
- Pin the k6 image tag (`grafana/k6:0.52.0`); upgrade in a dedicated MR.

### What NOT to do
- No Testcontainers without `docker:dind` (+ `TESTCONTAINERS_HOST_OVERRIDE: docker`) or a mounted host socket — there is no daemon by default on a Docker-executor job.
- No long-lived cloud keys in CI/CD variables — use `id_tokens:` OIDC.
- No `allow_failure: true` on a test job to "make it green". Fix the test or quarantine it.
- No bare `npm install` in CI — use `npm ci` / `pnpm install --frozen-lockfile` / `yarn --immutable`.
- No `playwright install` without `--with-deps` (missing system libs → silent browser crashes).
- No two jobs writing the same `cache:key` (`policy: pull-push`) — they race; one `install` job writes, the rest pull.
- No shared blob filename across `parallel:` shards — they overwrite on merge. Set `PLAYWRIGHT_BLOB_OUTPUT_FILE` per `CI_NODE_INDEX`.
- No `retry:` on test assertions — reserve it for `runner_system_failure`.
- No printing of a fetched secret in any job, even with `|| true`.

## Generation steps

1. Read any existing `.gitlab-ci.yml` to learn the runner tags, `image:`, existing `id_tokens:`/CI-CD variables, and stage conventions.
2. Inventory test projects: read `package.json` scripts, `playwright.config.ts`, `vitest.config.ts` / `jest.config.ts`, and the lockfile (decides the package manager + `cache:key:files:`). Group them into API / integration / UI / perf.
3. Generate `.gitlab-ci.yml` with `stages: [install, test, merge, perf, publish]`, the `.node-cache` anchor, one `install` job (`policy: pull-push`), the sharded `api-tests` / `e2e` jobs, the dind `integration-tests` job, the `merge-reports` job (`needs: [e2e]`), the `pages` Allure job, and the gated `k6-perf` job.
4. Set `reporter: process.env.CI ? [['blob'], ['allure-playwright']] : 'html'` and `retries: 0` in `playwright.config.ts`; configure the JUnit reporter in `vitest.config.ts` / `jest.config.ts`.
5. Configure cloud OIDC: register GitLab as an OIDC identity provider, create the role with a trust policy keyed on the project/ref claims, and set the `id_tokens:` `aud:` to match. Document the subject claim in a comment at the top of the file.
6. Validate locally with the **CI Lint** tool (Pipelines → CI Lint) or `glab ci lint`, then open a draft MR and confirm every expected job, the merged Playwright report, and the MR test widget appear.

## Cross-references

- **`qa/dotnet/skills/ci-pipelines`** + **`qa/java/skills/ci-pipelines`** — the same-CI siblings; consult for the NUnit/JUnit-logger and TestNG/JUnit variants (both need a per-shard Allure merge the Playwright `blob` flow avoids).
- **`qa/typescript/skills/ci-pipelines`** — the structural template this ports from; consult it for the `strategy.matrix` / `dorny/test-reporter` variant of the same Vitest/Playwright patterns.
- **`qa/typescript/skills/ci-pipelines`** — the Azure sibling; the `strategy: parallel` / service-connection variant.
- **`qa/typescript/skills/ui-test-author/playwright`** — the `playwright.config.ts` (`blob`/`allure-playwright` reporters, `--shard`, traces) this pipeline runs.
- **`qa/typescript/skills/db-testing/testcontainers`** — the integration-tests job runs these (needs the `docker:dind` service shown above).
- **`qa/typescript/skills/network-monitoring`** + **`qa/typescript/skills/network-monitoring`** — in-process network specs the `e2e` job runs with no extra pipeline plumbing.
- **`qa/typescript/skills/network-monitoring`** — runs an **external MITM proxy** the job must start/stop, and whose **CA the browser/client must trust** (generated per run — no stored secret). When the suite includes proxy specs, the `e2e` job needs a step to launch the proxy and inject its per-run CA before the tests, unlike the in-process `playwright-routes`/`cdp` specs.
- **`qa/typescript/skills/allure-reporting`** — adapter wiring inside the test project that produces `allure-results/`.
- **`qa/typescript/skills/performance/k6`** — perf-job scripts; SLO contract in `qa/_shared/performance`.
- **`qa/_shared/ci-conventions`** — cross-stack rules (artifact retention, OIDC) this skill enforces.
