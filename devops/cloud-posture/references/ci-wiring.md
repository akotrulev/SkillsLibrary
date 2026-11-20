# CI wiring — scheduled, OIDC-authed, in the DEPLOY pipeline

Cloud-posture scans run as a **scheduled/authorized job in the deploy pipeline** (`devops/github-actions` / `gitlab-ci` / `azure-pipelines`), **not** the `qa/cicd/*` test lane — the account credentials belong to the deploy context, and posture drift is a nightly concern, not a per-PR one.

```yaml
# .github/workflows/cloud-posture.yml — scheduled CSPM gate. Cross-link devops/github-actions.
name: Cloud Posture (Prowler)
on:
  schedule: [{ cron: "0 6 * * *" }]     # nightly — posture drifts continuously, not per-PR
  workflow_dispatch:                    # on-demand, with the run's authorization recorded in the trigger

permissions:
  id-token: write                       # OIDC — assume the read-only role, NO static keys (blocker if violated)
  contents: read

jobs:
  prowler-aws:
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/prowler-security-audit   # read-only
          aws-region: eu-west-1
      - run: pip install prowler==5.38.0
      # Pass 1 — informational: full HTML + OCSF, archived by date, never fails.
      - run: prowler aws --output-formats html json-ocsf --output-directory "reports/$(date +%F)"
      # Pass 2 — gating: Critical/High failures against CIS; fail the job on exit 3.
      - run: |
          prowler aws --severity critical high --status FAIL --compliance cis_3.0_aws \
            --output-formats json-ocsf --output-directory "reports/$(date +%F)/gate" || \
            { [ $? -eq 3 ] && echo "::error::Critical/High cloud-posture findings" && exit 1; }
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: prowler-report, path: reports/ }
```

- **OIDC only** — `id-token: write` + an assumed read-only role. A long-lived `AWS_ACCESS_KEY_ID` in CI is a **blocker** (the library's no-static-cloud-credentials invariant).
- Archive `reports/` as an artifact so a failing run names the findings without re-scanning; the dated dir gives a drift trail.
- Azure/GCP run the identical two-pass with Workload Identity Federation instead of the AWS OIDC role (see the references).
