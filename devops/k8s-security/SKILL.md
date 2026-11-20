---
name: kubernetes-security
description: Use when benchmarking or validating Kubernetes security (CIS, RBAC, NetworkPolicy, Pod Security). Triggers "run CIS benchmark on our cluster". Not for manifests (kubernetes).
disable-model-invocation: true
---

# DevOps — Kubernetes Security Posture (kube-bench · Kubescape · Polaris · kube-score)

Kubernetes ships **insecure-by-default in the places that matter**: no NetworkPolicy means every pod can reach every pod, an unlabelled namespace runs privileged pods, a `ClusterRoleBinding` to `cluster-admin` looks identical to any other binding in `kubectl get`, and `Secret` objects are base64, not encrypted, at rest unless someone configured an `EncryptionConfiguration`. This skill owns the tools that **score that posture against a published benchmark** and the procedures that **prove the isolation controls fire**, rather than that a manifest field is set.

> **The Trivy boundary.** `qa-<stack>:image-infra-scan` (Trivy) owns CVE matching and raw IaC misconfig: base-OS packages, the container as shipped, SBOM and provenance (A03), `trivy config` over Terraform, Helm and K8s templates, and `trivy k8s` cluster vulnerability scanning. This skill owns what Trivy does not produce: a benchmark score, a framework mapping and a validated control. Run both: a clean Trivy scan says nothing about a `cluster-admin` binding, and a 92% CIS score says nothing about a Critical CVE in the base image. Where they overlap (K8s manifest misconfig), one owns the pre-merge manifest gate: Trivy for the IaC tree, Polaris or kube-score for the workload-shape checks its policies do not cover (probes, PDBs, resource requests, image-tag hygiene).

> **Authorization to probe a live cluster. `#volatile`, per run, target-scoped, expiring.** The static half (Polaris, kube-score, Kubescape over manifest files) reads files and is safe on every PR. The live half (`kube-bench` on a node, `kubescape scan` against a kubecontext, `kubectl auth can-i --list`, the NetworkPolicy probe) reads a real cluster, and the probe briefly runs a pod on it. Before the first live command:
> - Record `Authorization: <cluster/context + namespaces in scope> · authorized by <name> · expires <date>` in the run's output. Never write it to `docs/agent-context/`, never carry it from a previous run; `engineering/agent-orientation-cache` treats live-resource facts this way.
> - Owned or throwaway clusters only, never a third party's or a shared one you do not administer. Prefer a dedicated security-test cluster or an ephemeral kind/k3d clone of production's manifests. Production is a separate, louder sign-off than a lab.
> - Set `--kube-context` and `--include-namespaces` or `--exclude-namespaces` explicitly, never whatever `kubectl config current-context` happens to be.
> - The NetworkPolicy probe is the only act that creates anything: one named, namespaced `curl` pod, run with `--rm --restart=Never`, with creation and removal both logged. Nothing else is written to the cluster; `devops-engineer` applies every fix.

## Decision matrix — which tool answers which question

| The question | Tool | Reads | Needs a cluster? | Spine |
|---|---|---|---|---|
| **CIS Kubernetes Benchmark** score, control by control | **kube-bench** → `references/kube-bench.md` | node filesystem, control-plane args and config | **yes** (or a Job in-cluster) | CIS · OWASP **A02** |
| **NSA/CISA hardening guidance** score | **Kubescape** `scan framework nsa` → `references/kubescape.md` | the K8s API or manifests | either | NSA/CISA · **A01/A02** |
| **MITRE ATT&CK (Containers)** exposure | **Kubescape** `scan framework mitre` | the K8s API or manifests | either | **ATT&CK Containers** |
| **Workload config** sanity: probes, resources, root, capabilities, image tags | **Polaris** → `references/polaris.md` | manifests, a chart, or live workloads | either | OWASP **A02** |
| **Manifests pre-merge**, no cluster | **kube-score** → `references/polaris.md` | YAML on stdin or disk | **no** | OWASP **A02** |
| **Block** a non-conforming workload at apply time | Polaris admission webhook, Pod Security Admission, Kyverno or Gatekeeper | admission requests | **yes** | A01/A02 |
| Does **RBAC** deny what we think? | `kubectl auth can-i` matrix (control 1) | the K8s API | **yes** | **A01** · **T1078.004** |
| Do **NetworkPolicies** block the traffic? | reachability probe (control 2) | the pod network | **yes** | A01 · **T1210** |
| Does **admission** reject a privileged pod? | `--dry-run=server` apply (control 3) | the admission chain | **yes** | A01/A02 · **T1611** |
| Are **Secrets encrypted at rest**? | `EncryptionConfiguration` or provider KMS (control 4) | apiserver config or managed-cluster settings | **yes** | A02/**A04** |
| **CVEs**, OS packages, SBOM, raw IaC | **Trivy** → `qa-<stack>:image-infra-scan` | image layers, lockfiles, IaC | no | A03/A02 |

Order of use: kube-score in the PR, Polaris on the chart or overlay, Kubescape for the framework picture, kube-bench for the CIS number and the node half nothing else sees, then the four controls for the part no scanner proves.

## Setup — pin every version once, here

```bash
docker run --rm --pid=host \
  -v /etc:/etc:ro -v /var:/var:ro \
  -v $(which kubectl):/usr/local/mount-from-host/bin/kubectl \
  -v ~/.kube:/.kube -e KUBECONFIG=/.kube/config \
  -t docker.io/aquasec/kube-bench:v0.16.0 run --targets node,policies

brew install kubescape
brew tap FairwindsOps/tap && brew install FairwindsOps/tap/polaris
docker run --rm -v "$PWD:/workdir" \
  us-docker.pkg.dev/fairwinds-ops/oss/polaris:10.2.2 polaris audit --audit-path /workdir
brew install kube-score
docker run --rm -v "$PWD:/project" zegl/kube-score:v1.20.0 score /project/manifests/*.yaml
```

- **Pin the image in CI.** A scanner upgrade that adds a check and turns a green pipeline red must be a reviewable bump, or the gate is disabled within a week. Same discipline as the Trivy pin. kube-bench needs `--pid=host` (it inspects component processes) with read-only host mounts.
- **Polaris moved its registry** from `quay.io` to `us-docker.pkg.dev/fairwinds-ops/oss/polaris` at v10.2.0; a pipeline still on `quay.io` silently runs a stale binary.
- **Pin the benchmark, not just the binary.** kube-bench auto-detects the cluster version and picks a CIS benchmark, which is wrong on managed clusters; the ids, the version map and the managed-cluster targets are in `references/kube-bench.md`. Kubescape's `cis-v1.10.0` is a versioned framework. Every report states the benchmark version, tool version, targets and namespaces: "84% CIS" is meaningless without them.

## Running a tool

Load the reference for the tool you run: **kube-bench** → `references/kube-bench.md`, **Kubescape** → `references/kubescape.md`, **Polaris or kube-score** → `references/polaris.md`. Each holds its commands, flags and output shape. These facts hold for every run:

| Tool | The gate (report-only without it) | Read before trusting it |
|---|---|---|
| kube-bench | `--exit-code 1` | A **WARN is the manual half, not a pass**: every WARN is a row a human answers in the report, counted apart from PASS. On a managed cluster use the provider benchmark with `--targets node,policies,managedservices`; `master` and `etcd` FAIL on a missing file and the score is fiction |
| Kubescape | `--severity-threshold high` or `--compliance-threshold` | It reads the API, not `/etc/kubernetes/manifests` or kubelet flags; run it with kube-bench and say which produced which control. `--keep-local` keeps results off the hosted backend |
| Polaris | `--set-exit-code-on-danger` (exit 3), `--set-exit-code-below-score` (exit 4) | Severities come from the shipped `default.yaml`, not the docs site |
| kube-score | `--exit-one-on-warning` | It scores YAML: a Helm chart or Kustomize overlay goes through `helm template` or `kubectl kustomize` first |

**One pre-merge gate per check.** Polaris and kube-score both flag missing requests and probes; one gates and the other runs report-only, or the team keeps two exception files for one fix. To wire the gates into a pipeline, read `references/ci-wiring.md`: static jobs on the PR, the live benchmark scheduled and environment-gated, never on a fork PR.

## Validating the four controls — the half no scanner scores

A benchmark scores *configuration*; these procedures prove the *control*. The line to `devops-auditor`: it confirms a `NetworkPolicy` resource exists, this confirms the packet is dropped.

**1 — RBAC least privilege (A01 · T1078.004).** Scanners flag `cluster-admin` bindings; they do not say what a workload's ServiceAccount can do:

```bash
kubectl auth can-i --list \
  --as=system:serviceaccount:orders:orders-api --namespace orders

kubectl auth can-i create pods --as=system:serviceaccount:orders:orders-api -n kube-system
kubectl auth can-i get secrets --as=system:serviceaccount:orders:orders-api --all-namespaces
kubectl auth can-i '*' '*' --as=system:serviceaccount:orders:orders-api

kubectl get clusterrolebindings -o json \
  | jq -r '.items[] | select(.roleRef.name=="cluster-admin")
           | "\(.metadata.name)\t\(.subjects[]?.kind):\(.subjects[]?.name)"'
```

Assert one expected answer per row (`no` for each escalation above): a matrix of subject × verb × resource, the discipline the `qa-<stack>:permission-testing` skills apply to an API's BOLA/BFLA matrix, one layer down. Bindings compose, so the effective permission set is not visible in any one Role file.

**2 — NetworkPolicy enforces (A01 · T1210).** Two failures are invisible in YAML: a namespace with no default-deny, and a CNI that does not implement NetworkPolicy (a plain kubenet cluster accepts every policy and enforces none).

```bash
kubectl get networkpolicy -A -o json \
  | jq -r '.items[] | select(.spec.policyTypes|index("Ingress"))
           | select(.spec.podSelector == {}) | .metadata.namespace' | sort -u

kubectl run netpol-probe -n orders --rm -i --restart=Never \
  --image=curlimages/curl:8.11.1 -- \
  curl -sS --max-time 5 http://payments-api.payments.svc.cluster.local:80/health
# EXPECTED: timeout or connection refused. A 200 means the policy is not enforced.
```

A namespace missing from the first query's output has no default-deny; absence is the finding. Probe **both directions**: one call that must succeed and one that must be blocked, because a blocked-only probe cannot tell "policy works" from "the service was down".

**3 — Pod Security Admission rejects (A01/A02 · T1611).** PSA is opt-in per namespace by label, and an unlabelled namespace runs `privileged`:

```bash
kubectl get ns -o json | jq -r '.items[]
  | select(.metadata.labels["pod-security.kubernetes.io/enforce"] == null)
  | .metadata.name'

kubectl apply -n orders --dry-run=server -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: psa-probe }
spec:
  containers:
    - name: probe
      image: busybox:1.37
      securityContext: { privileged: true }
EOF
# EXPECTED: rejected by the admission webhook. Created or accepted is the finding.
```

The first query lists namespaces that accept a privileged pod today. A label with no admission plugin enabled, or a `warn`-only level, reads identically to enforcement, so prove it with the dry-run: `--dry-run=server` runs the full admission chain (PSA, Polaris webhook, Kyverno, Gatekeeper) without persisting the object.

**4 — Secrets at rest (A02/A04).** On a self-managed cluster the apiserver needs `--encryption-provider-config` pointing at an `EncryptionConfiguration` whose first provider is not `identity` (the kube-bench control family around 1.2.31 covers it). On a managed cluster the equivalent is the provider's KMS setting: **EKS** envelope encryption with a KMS key, **AKS** KMS etcd encryption, **GKE** application-layer secrets encryption with Cloud KMS. Report which path the cluster is on, and whether the workload uses `Secret` objects or a CSI-mounted external store (`devops/kubernetes` owns that authoring choice).

## The two spines — OWASP posture, ATT&CK Containers exposure

Every finding carries the posture spine and, where it describes something an attacker does, an ATT&CK technique. The surface picks the matrix: **ATT&CK Containers**, never enterprise.

| Finding | OWASP Top 10:2025 | ATT&CK (Containers) |
|---|---|---|
| Namespace with no default-deny NetworkPolicy | A01 | **T1210** Exploitation of Remote Services |
| ServiceAccount bound to `cluster-admin` | **A01** | **T1078.004** Valid Accounts: Cloud Accounts |
| `automountServiceAccountToken: true` on a workload that needs no API access | A01 / A02 | **T1552.001** Unsecured Credentials: Files |
| Privileged container, `hostPID`, `hostPath` mount of `/` | A02 | **T1611** Escape to Host |
| Unauthenticated kubelet read-write port, exposed API server | A02 / A05 | **T1610** Deploy Container · **T1613** Discovery |
| Anonymous auth on the API server | A01 / A02 | **T1078** Valid Accounts |
| No `EncryptionConfiguration` or KMS, Secrets plaintext in etcd | A02 / **A04** | **T1552.007** Container API |
| Audit logging disabled on the API server | A09 | *(detection gap, no technique)* |
| `:latest` or unpinned image tags | A03 | **T1525** Implant Internal Image |
| Missing resource limits | A02 | **T1496** Resource Hijacking |

Pure CVE matches belong to Trivy and `qa-<stack>:image-infra-scan`, mapped to A03.

## Green ≠ safe — state coverage and the handoff

A 92% CIS score and a clean Polaris run mean the configuration surface these tools model passed. Every report closes with what was not covered and who owns it:

| Not covered here | Owner |
|---|---|
| CVEs in images, base OS packages, SBOM and provenance | `qa-<stack>:image-infra-scan` (Trivy) |
| Application-layer authz: BOLA, IDOR, BFLA against the API | `qa-security` → `permission-testing` (per stack) |
| Cross-tenant data leakage at the database layer | `data-architect` |
| Terraform, Bicep and ARM misconfig scoring | `devops:iac-security` |
| Cloud-account posture: IAM, exposed storage, encryption, logging | `devops:cloud-posture` |
| Runtime threat detection, escape probing, live alerts | `devops:container-runtime-security` |
| Artifact signing, SLSA provenance, build-pipeline integrity | `devops:supply-chain-security` |
| Whether a detection actually fired | `observability-engineer-*` |
| Applying every fix | `devops-engineer`; this skill finds and retests |

A control validated in the lab is validated for the lab's configuration. Re-run against the target environment; a lab result is never a production claim.

## Exceptions & triage — ticketed, scoped, expiring

- Scope each exception to one control or check id, with a ticket, reason and re-review date beside it. Skip a control by id, never a section; never set `--set-exit-code-below-score 0`.
- **Ratchet the score, don't freeze it.** Start the threshold at today's number and raise it each sprint.
- **Prefer the fix.** Almost every Polaris or kube-score finding is a three-line manifest change (`devops/kubernetes` has the shape); a suppression is for the earned exception only.

To write an exemption, read `references/exceptions.md` (the Polaris config, the kube-bench and kube-score skips). The full model is in `qa/_shared/security`.

## Cross-references

- `qa-<stack>:image-infra-scan`: the boundary partner (Trivy). Run both; never double-gate the same manifest check.
- `devops-auditor`: the static-conformance sibling, read-only. It confirms the field is set; this runs the benchmark and proves the control fires.
- `devops:threat-modeling` · `devops:controls-validation`: the STRIDE model that scopes the assessment, and the secrets, encryption and monitoring control checks. The other sibling lanes are in the coverage table above.
- **`infra-security-tester`**: the orchestrator that runs this skill (step 4, Kubernetes and runtime); it re-runs after remediation and reports the delta.
- `devops/kubernetes`: the authoring skill whose output this scores. `qa/_shared/security`: the authorization-to-scan rule this skill's live gate inherits.
