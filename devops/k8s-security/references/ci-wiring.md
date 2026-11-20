# CI wiring — the deploy pipeline, not the test lane

Infra posture scans that gate a build belong to the **deploy pipeline** (`devops/github-actions`, `devops/gitlab-ci`, `devops/azure-pipelines`), not the `qa/cicd/*` test lane, which owns the test-suite pipeline (shard matrix, Allure publish, perf gate). Wire these gates beside the image build and hand raw results off as artifacts.

Static jobs gate the PR. The live benchmark is scheduled and environment-gated, because it needs cluster credentials and a live target, the two things a fork PR must never get. Image tags below are placeholders for the pins in `../SKILL.md` Setup, so a bump is made in one place.

```yaml
name: K8s Security Posture
on: [pull_request]

permissions:
  contents: read
  security-events: write

jobs:
  manifest-posture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Render the chart
        run: helm template ./charts/orders-api -f ./charts/orders-api/values-prod.yaml > rendered.yaml
      - name: kube-score, pre-merge gate
        run: |
          docker run --rm -v "$PWD:/project" <kube-score image from Setup> \
            score /project/rendered.yaml --output-format ci --exit-one-on-warning
      - name: Polaris, danger gate (exit 3) and score ratchet (exit 4)
        run: |
          docker run --rm -v "$PWD:/workdir" <polaris image from Setup> \
            polaris audit --audit-path /workdir/rendered.yaml \
              --set-exit-code-on-danger --set-exit-code-below-score 90 --only-show-failed-tests
      - name: Kubescape, NSA and MITRE mapping as SARIF
        uses: kubescape/github-action@v0.1.0
        with:
          files: rendered.yaml
          frameworks: nsa,mitre
          format: sarif
          outputFile: kubescape.sarif
          severityThreshold: high
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: kubescape.sarif }

  cluster-benchmark:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    environment: security-lab
    steps:
      - uses: azure/setup-kubectl@v4
      - name: kube-bench as an in-cluster Job on a managed cluster
        run: |
          kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/<pinned tag from Setup>/job-eks.yaml
          kubectl wait --for=condition=complete job/kube-bench --timeout=300s
          kubectl logs job/kube-bench > kube-bench.txt
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: k8s-posture, path: "*.txt" }
```

The `security-lab` environment is the approval gate that carries the authorization record from `../SKILL.md`.
