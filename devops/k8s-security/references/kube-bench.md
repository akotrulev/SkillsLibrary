# kube-bench — the CIS Kubernetes Benchmark, control by control

**kube-bench** (Aqua Security) runs the **CIS Kubernetes Benchmark** against a cluster and returns a
control-by-control PASS / FAIL / WARN / INFO result. It is a Go binary that reads the **node filesystem and
the control-plane process arguments and config files** — it does not talk to the workload API for scoring, so
it must run **where the node's files live**: on the node itself, or as a Job in the cluster with the host
paths mounted. Pin it — `aquasec/kube-bench:v0.16.0`.

The output maps 1:1 to the CIS benchmark's numbered controls (`1.2.6 Ensure that the --kubelet-certificate-authority argument is set as appropriate`), which is what makes a kube-bench score **auditable and trend-able** run over run.

## Choosing the benchmark — this is the load-bearing decision

kube-bench auto-detects the running Kubernetes version and picks a benchmark, but on a **managed cluster** the
autodetect is wrong more often than right, because the CIS master/control-plane controls do not apply to a
control plane you do not run. Select explicitly with `--benchmark`:

| Cluster | Benchmark | Why |
|---|---|---|
| Self-managed (kubeadm, on-prem) | `cis-1.10` (or the version matching your K8s) | You own master + node; all sections apply |
| **EKS** | `eks-1.5.0` | AWS owns the control plane; only node + policy controls are yours |
| **AKS** | `aks-1.7` | Azure owns the control plane |
| **GKE** | `gke-1.6.0` | Google owns the control plane; GKE Autopilot narrows it further |
| RKE / OpenShift / etc. | the vendor's CIS profile | Each distro ships its own benchmark id |

```bash
kube-bench version                              # list bundled benchmarks
kube-bench --benchmark eks-1.5.0                # explicit, the managed-cluster default
kube-bench run --targets node,policies          # only the sections a managed cluster owns
```

On a managed cluster, running the full `master` section produces a wall of FAILs for controls you **cannot
action** (you do not have the API server flags) — that trains the team to ignore the report. Scope to
`--targets node,policies` (and `etcd`, `controlplane` only where you run them).

## Running it — node vs in-cluster Job

```bash
# On a node directly (SSH / DaemonSet debugging) — reads /etc, /var, the kubelet config.
kube-bench --benchmark cis-1.10

# In-cluster as a Job — the CI-friendly form. Aqua ships job manifests per platform:
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/v0.16.0/job-eks.yaml
kubectl logs job/kube-bench
```

Running against a **live cluster is authorization-gated** in this library — it needs node access / a Job
apply, which is a change to owned infrastructure. Confirm the target and record the `#volatile` authorization
per the `infra-security-tester` gate. There is no static-manifest mode: kube-bench scores a *running node*,
not a YAML file (that is Polaris / kube-score / Kubescape's job).

## Gating in CI — JSON + the fail threshold

```bash
# JSON for programmatic gating; --check / --skip to scope; exit non-zero on FAIL.
kube-bench --benchmark eks-1.5.0 --targets node,policies \
  --json --outputfile kube-bench.json

# There is no built-in --exit-code-on-fail across all versions; gate on the JSON:
FAILS=$(jq '[.Controls[].tests[].results[] | select(.status=="FAIL")] | length' kube-bench.json)
test "$FAILS" -eq 0            # fail the step on any FAIL (ratchet: start with a baseline count)
```

The JSON shape: `Controls[]` (one per benchmark section) → `tests[]` (a numbered group) → `results[]`
(`test_number`, `test_desc`, `status`, `remediation`). The `remediation` string is the exact fix text from
the CIS PDF — quote it into the finding so `devops-engineer` has the change without opening the benchmark.

## Triage — WARN is not PASS, and `--check`/`--skip`

- **FAIL** — a control the tool could verify is not met. Action or ticket it.
- **WARN** — the control is **manual** (kube-bench cannot verify it automatically) or needs a human decision.
  A WARN is *unassessed*, not passed — the most common misread of a kube-bench report is treating the WARN
  count as safe. Sample the WARNs and resolve each to a real PASS/FAIL by hand.
- **INFO** — informational, no action.
- Scope with `--check 1.2.6,1.2.7` (only these) or `--skip 1.2.6` (accepted-risk, ticketed). Every skip
  carries a ticket + reason, exactly like the `.trivyignore` discipline in `qa-<stack>:image-infra-scan`.

## Spines

CIS Kubernetes Benchmark control numbers are the primary spine; map the class to **OWASP A02 Security
Misconfiguration** and, for RBAC/privilege controls, note the ATT&CK **Containers** technique the control
mitigates (`T1611` Escape to Host for privileged-pod controls, `T1078.003` for RBAC controls).

## Cross-references

- `../SKILL.md` — the posture-scanner router; kube-bench answers the "what is our CIS score, control by
  control" row.
- `kubescape.md` — Kubescape also scores CIS (`scan framework cis-eks`) **from the API**, and adds NSA/CISA +
  MITRE framework mapping; use kube-bench for the node-level control-plane/kubelet controls it reads off the
  filesystem, Kubescape for the API-visible posture and the extra frameworks. Run both; they see different
  surfaces.
- `polaris.md` — best-practice *manifest* validation (static, pre-merge); kube-bench scores the *running node*.
- `qa-<stack>:image-infra-scan` — Trivy for image/IaC CVEs (`trivy k8s` for cluster CVEs) — a different
  surface from benchmark scoring.
