---
paths:
  - ".github/workflows/*{test,tests,allure,gatling,perf}*.{yml,yaml}"
  - "**/pipelines/templates/*{test,tests,allure,gatling,perf}*.{yml,yaml}"
  - "**/azure-pipelines*.{yml,yaml}"
  - "**/.gitlab-ci.yml"
---

<!-- qa-java rules v1 (2026-11-03): CI for test suites. Installed by /qa-java:rules; edit the paths above to the pipelines that run this project's test suites. -->

# Test pipeline standards (GitHub Actions, Azure Pipelines, GitLab CI)

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. These apply to the jobs that build, run and report the test suites. The codebase wins where it consistently does otherwise.

- The pipeline runs the commands developers run locally; no CI-only magic. Gradle runs with `--no-daemon`. *minor*
- A PR lane and a nightly lane; perf and visual suites run nightly only. *minor*
- Shards run with fail-fast off, so one red shard keeps the others' reports; artifact names carry the shard index. *major*
- The test step fails the build: no `continue-on-error`, `|| true` or `--rerun-tasks`. Only the quarantine job is non-gating. *blocker*
- No pipeline-level retry of failed tests. *major*
- JUnit XML and Allure results are both published on every run, failed runs included; the reporter step fails on test errors. *major*
- Cloud access through OIDC federation; no PAT or stored cloud secret; identifiers as variables, not secrets. *blocker*
- No secret echoed to the log or written where an artifact upload picks it up; a fetched secret is masked first. *blocker*
- Failure evidence (screenshots, traces, video) is uploaded only on failure, with a retention period. *minor*
- The perf gate is the simulation's own assertions and exit code; the pipeline adds no guard around it. *major*
- Linux-container suites never run on a Windows runner. Actions and templates are pinned; security-relevant ones to a full SHA. *major*
