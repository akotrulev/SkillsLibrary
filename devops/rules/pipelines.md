---
paths:
  - ".github/workflows/*.{yml,yaml}"
  - ".github/actions/**/action.{yml,yaml}"
  - "**/.gitlab-ci.yml"
  - "**/.gitlab/ci/**/*.{yml,yaml}"
  - "**/azure-pipelines*.{yml,yaml}"
  - "**/{.azure-pipelines,.azuredevops}/**/*.{yml,yaml}"
---

<!-- devops rules v1 (2026-11-03): build and deploy pipelines. Installed by /devops:rules; add the folders this project keeps pipeline templates in. -->

# Build and deploy pipeline standards

Severity tags as in the core devops rules. These govern build, deploy and infrastructure-gate jobs; test-suite jobs (shards, Allure, perf gate, quarantine) follow the qa rules, which may load on the same file and agree.

- GitHub `permissions:` is read-only at the top and widened per job; `id-token: write` only on the job that federates. *major*
- A third-party action, and any action in a job holding cloud credentials or write permissions, is pinned to a full commit SHA; others to a current major at least. *major*
- A deploy job runs only from the default branch or a tag, never a PR or fork PR, and targets a named environment; production waits for required reviewers on that environment. *blocker*
- Production deploys run on a named, isolated runner or pool, never a shared default one. *major*
- Secrets are platform secrets, protected masked variables or Key Vault-linked groups, scoped to the job or step that uses them; never in workflow-level `env:` or top-level `variables:`. *major*
- No `continue-on-error`, `allow_failure` or `continueOnError` to hide a failing step, and no `always()` condition on a deploy step. *major*
- Test results are uploaded as artifacts on every run (`if: always()`, `when: always`, `succeededOrFailed()`); publishing a report is the test lane's job. *minor*
- An image build sets `--platform` explicitly, emits provenance and an SBOM, and is scanned before push; critical CVEs fail it. *major*
- An IaC pipeline validates, lints and scans every PR, keeps the plan as a private artifact, applies to production only after approval (never from a laptop), and runs a scheduled drift plan. *major*
- Infrastructure-security gates (IaC, cluster and cloud posture, signature verification) run in the deploy pipeline; a job touching a live cluster or account is scheduled and environment-gated. *major*
- One workflow per purpose, one job per responsibility, real dependencies declared (`needs:`, `dependsOn:`), every step named, caches keyed on the lockfile; a `script:` over ten lines moves to `scripts/`. *minor*
