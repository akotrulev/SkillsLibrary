---
paths:
  - ".github/workflows/*.{yml,yaml}"
  - "**/azure-pipelines*.{yml,yaml}"
  - "**/.azure-pipelines/**/*.{yml,yaml}"
  - "**/.gitlab-ci.yml"
---

<!-- qa-typescript rules v1 (2026-11-03): test pipelines. Installed by /qa-typescript:rules; these apply to the jobs that run test suites, not to build or deploy jobs. -->

# Test pipeline standards (GitHub Actions, Azure Pipelines, GitLab CI)

Severity tags as in the core rules. These apply to jobs that run a test suite; deploy jobs belong to the devops rules. The codebase wins where it consistently does otherwise.

- The pipeline runs the same commands developers run locally; no CI-only magic. *major*
- Secrets come from OIDC or the platform's secret store, never static credentials in YAML. *blocker*
- The test step fails the build: no `continue-on-error`, `continueOnError` or `|| true` on the gating lane, and no pipeline-level retry. Retries stay 0; quarantine is the suite's tag plus a separate non-gating job. *major*
- The gate and the quarantine lane run as separate jobs so neither wipes the other's evidence. *major*
- Shards run with fail-fast off. *major*
- JUnit XML and `allure-results/` are uploaded on every run, failures included (`if: always()`, `succeededOrFailed()`, `when: always`); `allure-results/` is never committed. *major*
- One pinned Allure CLI; history kept across runs; publish from `main`, PR builds to a PR-scoped URL or not at all. *minor*
- A reusable template, anchor or matrix dimension with one consumer or one value is inlined; a reader sees what a job runs without opening a second file. *minor*
- A step's command comes from its owner: the Allure command from reporting, the scan gate from security, the perf thresholds from the k6 suite. *major*
