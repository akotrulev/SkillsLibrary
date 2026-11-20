# kube-bench — the CIS Kubernetes Benchmark, control by control

**kube-bench** (Aqua Security) runs the **CIS Kubernetes Benchmark** and returns a PASS / FAIL / WARN / INFO result per numbered control (`1.2.6 Ensure that the --kubelet-certificate-authority argument is set as appropriate`), which makes a score auditable and trend-able run over run. It reads the **node filesystem and the control-plane process arguments and config files**, so it runs where the node's files live: on the node, or as a Job with the host paths mounted. There is no static-manifest mode; that is Polaris, kube-score and Kubescape. The pinned version is in `../SKILL.md` Setup.

## Choosing the benchmark — the load-bearing decision

Auto-detection maps the Kubernetes version to a CIS benchmark, and on a managed cluster it is wrong more often than right: the master and etcd controls describe a control plane you do not run. Select with `--benchmark`.

| Cluster | `--benchmark` id | Targets |
|---|---|---|
| Self-managed (kubeadm, on-prem) | k8s 1.28 → `cis-1.10` · 1.29–1.31 → `cis-1.11` · 1.32–1.34 → `cis-1.12` | `master,controlplane,node,etcd,policies` |
| EKS | `eks-1.8.0` | `node,policies,managedservices` |
| AKS | `aks-1.8` | `node,policies,managedservices` |
| GKE | `gke-1.9.0` | `node,policies,managedservices` |
| RKE, RKE2, K3s, OpenShift | the distribution's own id: `rke2-cis-1.9`, `k3s-cis-1.9`, `rh-1.9` | per the distribution |

The ids are the folder names under `cfg/` in the pinned release; read the version-to-benchmark map in `cfg/config.yaml` of that tag. Checked against kube-bench v0.16.0 on 2026-11-20 through its `cfg/` tree. The previous ids in this table (`eks-1.5.0`, `aks-1.7`, `gke-1.6.0`) are still bundled, so a cluster whose provider benchmark is the older one keeps it. Run `kube-bench version` for kube-bench's own version; `--version` is the Kubernetes version, and `--version` together with `--benchmark` is an error.

A full `master` section on a managed cluster is a wall of FAILs for controls you cannot action, and it trains the team to ignore the report.

## Running it

```bash
kube-bench run --benchmark cis-1.12 --targets master,controlplane,node,etcd,policies
kube-bench run --benchmark eks-1.8.0 --targets node,policies,managedservices
kube-bench run --check "1.2.5,4.2.6" --include-test-output
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/<pinned tag>/job-eks.yaml
kubectl logs job/kube-bench
```

Aqua ships one Job manifest per platform in the repo root. `--include-test-output` prints the value that actually failed, which is what you want while remediating one control.

## Gating in CI

```bash
kube-bench run --benchmark cis-1.12 --json --outputfile kube-bench.json --exit-code 1
```

- **`--exit-code 1` is the gate**: without it kube-bench exits 0 even with FAILs. It fires when any control has `Fail > 0`; WARN does not trip it.
- **`--outputfile` writes only alongside `--json` or `--junit`.** The stdout-shaping flags (`--noresults`, `--noremediations`, `--include-test-output`) do not change the JSON. Parse the JSON, read the text.
- **The JSON shape**: `Controls[]` (a benchmark section) → `tests[]` (a numbered group) → `results[]` (`test_number`, `test_desc`, `status`, `remediation`). Quote the `remediation` string, the exact fix text from the CIS benchmark, into the finding so `devops-engineer` has the change without opening the benchmark.
- **Count FAILs from the JSON** when the ratchet is a baseline count: `jq '[.Controls[].tests[].results[] | select(.status=="FAIL")] | length' kube-bench.json`.

## Triage — WARN is not PASS

- **FAIL**: a control the tool could verify is not met. Fix it or ticket it.
- **WARN**: the control is manual (a human confirms a policy exists, that audit logs are reviewed) or needs a human decision. It is unassessed, not passed. Resolve each WARN to a PASS or FAIL by hand and count it apart from PASS.
- **INFO**: no action.
- **Skip a control by id** (`--skip 4.2.6`), never a section. The ticket, reason and re-review date sit beside it, as in `../SKILL.md` Exceptions.

## Spines

CIS control numbers are the primary spine. Map the class to OWASP **A02** Security Misconfiguration, and for RBAC and privilege controls name the ATT&CK **Containers** technique the control mitigates (`T1611` Escape to Host for privileged-pod controls, `T1078.004` for RBAC controls).

## Cross-references

- `../SKILL.md`: the router; kube-bench answers the "CIS score, control by control" row.
- `kubescape.md`: scores CIS from the API and adds NSA/CISA and MITRE mapping. kube-bench reads the node controls off the filesystem; run both, they see different surfaces.
- `polaris.md`: static, pre-merge manifest validation; kube-bench scores the running node.
- `qa-<stack>:image-infra-scan`: Trivy for image and IaC CVEs (`trivy k8s` for cluster CVEs), a different surface from benchmark scoring.
