# CI wiring — the deploy pipeline, not the test lane

These checks gate **the deployment**, so they live in `devops/{github-actions,gitlab-ci,azure-pipelines}`
alongside the deploy job — **not** in `qa/cicd/*`, which owns the test-suite lane (shard matrix, Allure,
perf gate, flake quarantine). The split is the library's standing fence; state it in the PR that adds them.

```yaml
# .github/workflows/deploy.yml — a post-deploy controls gate. Cross-link devops:github-actions.
  controls-validation:
    needs: deploy
    runs-on: ubuntu-latest
    environment: staging                     # the reviewed environment, so live reads are scoped
    permissions:
      id-token: write                        # OIDC only — no static key reaches this job
      contents: read
    steps:
      - uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8   # v5.0.0 — SHA-pinned
      - uses: aws-actions/configure-aws-credentials@v5
        with:
          role-to-assume: arn:aws:iam::123456789012:role/controls-validation-readonly
          aws-region: eu-west-1
      # Static families first — they need no credentials and fail fast.
      - run: ./controls/check-pipeline.sh
      # Live families next, scoped to the deployed staging endpoints.
      - run: ./controls/check-secrets.sh && ./controls/check-tls.sh && ./controls/check-monitoring.sh
        env: { TARGET_HOST: staging.example.com }
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: controls-report, path: controls-*.txt }
```

Run the **static** families (pipeline hardening, committed-secret shapes, IaC vars) on **every PR** — they
are free and need no credentials. Run the **live** families **post-deploy per environment**, because they
assert something about a running system that only exists after the deploy.
