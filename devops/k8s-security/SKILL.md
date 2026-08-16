---
name: devops-k8s-security
description: Use when benchmarking or probing the security posture of Kubernetes — CIS scoring with kube-bench, NSA/CISA + MITRE + CIS framework mapping with Kubescape, best-practice config validation with Polaris / kube-score, and active validation that RBAC, NetworkPolicy, Pod Security Standards, and secrets-at-rest actually hold. Language-agnostic, any cluster (AKS / EKS / GKE / self-managed). Triggers "run CIS benchmark on our cluster", "kube-bench / Kubescape / Polaris", "audit our K8s RBAC", "are our network policies actually enforcing", "score these manifests before merge", "is our pod security admission working". Do NOT use for authoring manifests (use `devops/kubernetes`), image or IaC CVEs (use `qa-security-image-infra-scan` — Trivy), or static conformance against the plugin's own rules (use `devops-auditor`).
---

# DevOps — Kubernetes Security Posture (kube-bench · Kubescape · Polaris · kube-score)

Kubernetes ships **insecure-by-default in the places that matter**: no NetworkPolicy means every pod can
reach every pod, an unlabelled namespace runs privileged pods, a `ClusterRoleBinding` to `cluster-admin`
looks identical to any other binding in `kubectl get`, and `Secret` objects are base64 — not encrypted —
at rest unless someone explicitly configured an `EncryptionConfiguration`. This skill owns the tools that
**score that posture against a published benchmark** and the procedures that **prove the isolation controls
actually fire**, rather than that a manifest field is set.

Four tools, one job each: **kube-bench** scores a cluster against the **CIS Kubernetes Benchmark** (the
number an auditor asks for) · **Kubescape** maps findings to **NSA/CISA Hardening Guidance, MITRE ATT&CK
(Containers), and CIS** and runs against *both* manifests and a live cluster · **Polaris** validates
workload config against a **best-practice check catalog** (CLI audit, dashboard, or admission webhook) ·
**kube-score** scores raw manifests in a pre-merge shift-left pass with no cluster at all. All four are
single Go binaries / container images — **language-agnostic**, one skill, no per-stack split (the library's
anti-triplication rule).

> **⚠️ The Trivy boundary — be precise; this is the whole reason both skills exist.**
> **`qa-security-image-infra-scan` (Trivy) owns CVE matching and raw IaC misconfig**: base-OS packages
> inside an image, the container as shipped, SBOM generation/provenance (A03), `trivy config` over
> Terraform/Helm/K8s templates, and `trivy k8s` cluster **vulnerability** scanning. **This skill owns what
> Trivy does not produce: a benchmark score, a framework mapping, and a validated control.** A CIS 1.10
> compliance percentage, an NSA/CISA control table, an ATT&CK-Containers technique map, a Polaris
> danger/warning catalog, and a `kubectl auth can-i` / NetworkPolicy reachability probe are all outside
> Trivy's model — it matches known vulnerabilities and rule IDs, it does not *score a benchmark* or *prove
> a policy blocks traffic*. **Run both**: a clean Trivy image scan says nothing about a `cluster-admin`
> binding, and a 92% CIS score says nothing about a Critical CVE in the base image's `openssl`.
> Where the two genuinely overlap (K8s manifest misconfig — `trivy config` vs Polaris/kube-score), **let
> one own the pre-merge manifest gate** so the same finding does not fail two pipelines with two
> suppression files; the rule of thumb is Trivy for the whole IaC tree, Polaris/kube-score for the
> workload-shape checks Trivy's AVD policies do not cover (probes, PDBs, resource requests, image-tag
> hygiene).

> **⚠️ Authorization to probe a live cluster — `#volatile`, per run, target-scoped, expiring.**
> The **static half** of this skill (Polaris/kube-score/Kubescape over manifest files) reads files and is
> safe on every PR. The **live half** — `kube-bench` on a node, `kubescape scan` against a kubecontext,
> `kubectl auth can-i --list`, the NetworkPolicy reachability probe — reads (and, for the probe, briefly
> *runs a pod on*) a real cluster. Before the first live command:
> - Record an authorization line in the run's output: **`Authorization: <cluster/context + namespaces in
>   scope> · authorized by <name> · expires <date>`**. It is **`#volatile`** — never written to
>   `docs/agent-context/`, never carried over from a previous run, re-confirmed every run
>   (`ep-agent-orientation-cache` treats live-resource facts this way by rule).
> - **Owned or throwaway clusters only.** Never a third party's cluster, never a shared cluster you do not
>   administer. Prefer a dedicated security-test cluster or an ephemeral kind/k3d clone of production's
>   manifests; **production is a separate, louder sign-off** than a lab, not the same one.
> - Scope is namespaces + context, and it is honoured: `--kube-context` and
>   `--exclude-namespaces`/`--include-namespaces` are set explicitly, never left to whatever `kubectl
>   config current-context` happens to be.
> - The **NetworkPolicy reachability probe is the only act that creates anything** — one short-lived
>   `curl`/`netshoot` pod. It is named, namespaced, and deleted in the same run; its creation and removal
>   are both logged.

## Decision matrix — which tool answers which question

| The question | Tool | Reads | Needs a cluster? | Spine |
|---|---|---|---|---|
| "What is our **CIS Kubernetes Benchmark** score, control by control?" | **kube-bench** → `references/kube-bench.md` | node filesystem + control-plane process args & config files | **yes** (or a Job in-cluster) | CIS · OWASP **A02** |
| "How do we score against **NSA/CISA hardening guidance**?" | **Kubescape** `scan framework nsa` → `references/kubescape.md` | the K8s API (or manifests) | either | NSA/CISA · **A01/A02** |
| "Which **MITRE ATT&CK (Containers)** techniques is this cluster exposed to?" | **Kubescape** `scan framework mitre` | the K8s API (or manifests) | either | **ATT&CK Containers** |
| "Is this **workload config** sane — probes, resources, root, capabilities, image tags?" | **Polaris** → `references/polaris.md` | manifests, a Helm chart, or live workloads | either | OWASP **A02** |
| "Score these **manifests pre-merge**, no cluster available" | **kube-score** (see below) | YAML on stdin or on disk | **no** | OWASP **A02** |
| "**Block** a non-conforming workload at apply time" | **Polaris admission webhook** (or Pod Security Admission / Kyverno / Gatekeeper) | admission requests | **yes** | A01/A02 |
| "Does **RBAC** actually deny what we think it denies?" | `kubectl auth can-i` matrix + Kubescape RBAC controls (see *Validating the four controls*) | the K8s API | **yes** | **A01** · ATT&CK **T1078.004** |
| "Do **NetworkPolicies** actually block the traffic?" | live reachability probe (see *Validating the four controls*) | the pod network | **yes** | A01 · ATT&CK **T1210** |
| "Are **Secrets encrypted at rest**?" | `EncryptionConfiguration` check + provider KMS (see *Validating the four controls*) | apiserver config / managed-cluster settings | **yes** | OWASP **A02/A04** |
| **CVEs** in the image / OS packages / SBOM / raw IaC | **Trivy** → `qa-security-image-infra-scan` | image layers, lockfiles, IaC templates | no | A03/A02 |

**Rule of thumb:** **kube-score** in the PR (fast, no cluster) → **Polaris** on the chart/overlay
(catalogued severities, same checks the webhook will enforce) → **Kubescape** for the framework picture →
**kube-bench** for the CIS number and the control-plane/node half nothing else can see → **the four
validation procedures** for the part no scanner proves.

## Setup — pin every version

```bash
# kube-bench — one binary that reads node + control-plane state. Run it ON a node, or as a Job in-cluster.
# --pid=host is required (it inspects component processes); the host mounts are read-only.
docker run --rm --pid=host \
  -v /etc:/etc:ro -v /var:/var:ro \
  -v $(which kubectl):/usr/local/mount-from-host/bin/kubectl \
  -v ~/.kube:/.kube -e KUBECONFIG=/.kube/config \
  -t docker.io/aquasec/kube-bench:v0.16.0 run --targets node,policies

# Kubescape — CLI for manifests and live clusters.
brew install kubescape
# or: curl -s https://raw.githubusercontent.com/kubescape/kubescape/master/install.sh | /bin/bash
# or as a kubectl plugin: kubectl krew install kubescape

# Polaris — CLI + dashboard + admission webhook, one binary.
brew tap FairwindsOps/tap && brew install FairwindsOps/tap/polaris
# Registry MOVED at v10.2.0 — it is no longer quay.io.
docker run --rm -v "$PWD:/workdir" \
  us-docker.pkg.dev/fairwinds-ops/oss/polaris:10.2.2 polaris audit --audit-path /workdir

# kube-score — manifest scoring, no cluster.
brew install kube-score          # or: kubectl krew install score
docker run --rm -v "$PWD:/project" zegl/kube-score:v1.20.0 score /project/manifests/*.yaml
```

> **Pin the version in CI** (`aquasec/kube-bench:v0.16.0`,
> `us-docker.pkg.dev/fairwinds-ops/oss/polaris:10.2.2`, `zegl/kube-score:v1.20.0`) — a scanner upgrade that
> adds a check and turns a green pipeline red must be a deliberate, reviewable bump, or the gate gets
> disabled within a week. Same discipline as the Trivy pin.
>
> **Pin the benchmark, not just the binary.** kube-bench auto-detects the cluster version and maps it to a
> CIS benchmark (k8s 1.29–1.31 → `cis-1.11`, 1.32–1.34 → `cis-1.12`); Kubescape's `cis-v1.10.0` is a
> versioned framework. **State the benchmark version in the report** — "84% CIS" is meaningless without
> which CIS, which targets, and which namespaces.
>
> **Two maintenance facts worth knowing before you standardize:** Polaris moved its image registry from
> `quay.io` to `us-docker.pkg.dev/fairwinds-ops/oss/polaris` at **v10.2.0** (an old pipeline pinned to
> `quay.io` silently keeps running a stale binary), and **kube-score's last tagged release is v1.20.0
> (April 2025)** — `master` still moves, but treat the release cadence as a risk and keep kube-score as the
> cheap pre-merge pass rather than the only gate.
>
## kube-bench — the CIS score (control plane, nodes, policies)

```bash
# Auto-detect the Kubernetes version, map it to a CIS benchmark, and run every applicable target.
kube-bench run

# Pin the benchmark explicitly rather than trusting auto-detection. Self-managed target set:
kube-bench run --benchmark cis-1.12 --targets master,controlplane,node,etcd,policies

# MANAGED clusters: the control plane is the provider's — master/etcd checks DO NOT APPLY.
kube-bench run --benchmark eks-1.5.0 --targets node,policies,managedservices,controlplane
kube-bench run --benchmark gke-1.2.0 --targets node,policies,managedservices
kube-bench run --benchmark aks-1.7   --targets node

# Machine-readable + the CI gate: exit non-zero when any check FAILs (WARN does not trip it).
kube-bench run --benchmark cis-1.12 --json --outputfile kube-bench.json --exit-code 1

# One control, while remediating — --include-test-output prints the value that actually failed.
kube-bench run --check "1.2.5,4.2.6" --include-test-output
```

Output is `[PASS]`/`[FAIL]`/`[WARN]`/`[INFO]` per numbered control, then a remediations block, then a
`== Summary <target> ==` count per section. Four things decide whether this gate is trustworthy:

- **`--exit-code 1` is the gate; without it kube-bench exits 0 even with FAILs** — same report-only default
  as a bare `trivy image`. The exit code fires when **any control has `Fail > 0`**.
- **`[WARN]` is the manual half.** CIS controls a machine cannot check (a human must confirm a policy
  exists, that audit logs are reviewed) come back `WARN`, not `FAIL`, and `--exit-code` deliberately
  ignores them. **A WARN is not a pass** — every WARN is a row a human answers in the report, and burying
  them is the most common way a CIS score becomes fiction.
- **`--version` is the *Kubernetes* version, not kube-bench's** (`kube-bench version` is the subcommand for
  that), and **passing `--version` together with `--benchmark` is an error** — pick one.
- **`--outputfile` only writes alongside `--json` or `--junit`**, and the stdout-shaping flags
  (`--noresults`, `--noremediations`, `--include-test-output`) do **not** change the JSON. Parse the JSON;
  read the text. Full walkthrough, benchmark map, and JSON shape in `references/kube-bench.md`.

## Kubescape — the framework mapping (NSA/CISA · MITRE ATT&CK Containers · CIS)

```bash
# List what is installable before naming a framework — the catalog moves.
kubescape list frameworks

# Live cluster, the two hardening frameworks, JSON for the report.
kubescape scan framework nsa,mitre --format json --output kubescape.json --keep-local

# CIS via Kubescape (a second opinion on kube-bench's workload half; it cannot see node filesystems).
kubescape scan framework cis-v1.10.0 --exclude-namespaces kube-system,kube-public,kube-node-lease

# STATIC — manifests, a Helm chart, or a directory. No cluster, safe in any PR.
kubescape scan framework nsa ./charts/orders-api --format sarif --output kubescape.sarif

# The CI gate: fail when the risk score exceeds the threshold, or on any High+ control.
kubescape scan framework nsa --severity-threshold high --format junit --output kubescape.xml
```

- **`nsa`** is the NSA/CISA *Kubernetes Hardening Guidance* — non-root, immutable filesystem, network
  separation, RBAC least privilege, secrets management, audit logging.
- **`mitre`** maps controls to **ATT&CK Containers** technique IDs — the right matrix for this surface
  (`T1611` Escape to Host, `T1610` Deploy Container, `T1613` Container and Resource Discovery,
  `T1078.004` Valid Accounts: Cloud Accounts). **Never map a cluster finding to the enterprise matrix**;
  the surface picks the matrix.
- **Kubescape overlaps kube-bench on the workload half and cannot replace it on the node half.** It reads
  the API; it does not read `/etc/kubernetes/manifests` or kubelet flags on a node. Run both, and say in
  the report which produced which control.
- **`--keep-local`** keeps results off the hosted backend; use it unless the team has deliberately adopted
  the SaaS. Full flag surface and the framework/control catalog in `references/kubescape.md`.

## Polaris & kube-score — workload-config validation

```bash
# Polaris — audit a directory of manifests or a chart. Default --format is json; ask for pretty.
polaris audit --audit-path ./manifests --format pretty
polaris audit --helm-chart ./charts/orders-api --helm-values ./charts/orders-api/values-prod.yaml

# The gate: exit 3 on any danger-severity check, exit 4 when the score falls below the ratchet.
polaris audit --audit-path ./manifests --set-exit-code-on-danger --only-show-failed-tests
polaris audit --audit-path ./manifests --set-exit-code-below-score 90 --format score

# Live workloads (no --audit-path = read the current kube context), and the browsable dashboard.
polaris audit --format json --output-file polaris.json
polaris dashboard --port 8080

# kube-score — pre-merge, no cluster, reads rendered YAML on stdin.
helm template ./charts/orders-api | kube-score score -
kube-score score manifests/*.yaml --output-format ci --exit-one-on-warning \
  --kubernetes-version v1.31 --ignore-test container-image-pull-policy
```

- **Polaris' catalog is severity-graded** (`danger` / `warning` / `ignore`, per check, overridable in a
  config file) — that grading is what makes `--set-exit-code-on-danger` a usable gate rather than an
  all-or-nothing switch. The danger-by-default security checks: `hostIPCSet`, `hostPIDSet`,
  `hostNetworkSet`, `runAsRootAllowed`, `runAsPrivileged`, `privilegeEscalationAllowed`,
  `dangerousCapabilities`, `sensitiveContainerEnvVar`, `sensitiveConfigmapContent`, plus the **RBAC
  family nothing else in this set checks statically** — `clusterrolebindingClusterAdmin`,
  `rolebindingClusterAdminRole`, `clusterrolePodExecAttach`, `rolePodExecAttach`. Warnings include
  `automountServiceAccountToken`, `hostPathSet`, `hostProcess`, `linuxHardening`, `missingNetworkPolicy`,
  `notReadOnlyRootFilesystem`, `procMount`, `insecureCapabilities`, `hostPortSet`, `tlsSettingsMissing`.
  **Read severities from the shipped `default.yaml`, not the docs site** — the two disagree on
  `runAsRootAllowed`, `hostNetworkSet`, and `linuxHardening`. Catalog, config schema, exemptions, and the
  `polaris fix` / webhook modes are in `references/polaris.md`.
- **kube-score renders first.** It scores *YAML*, so a Helm chart or Kustomize overlay is piped through
  `helm template` / `kubectl kustomize` — scoring the un-rendered template scores nothing real. Its unique
  value is the cross-object checks a per-manifest linter misses: `pod-networkpolicy` (a pod no
  NetworkPolicy selects), `networkpolicy-targets-pod` (a policy selecting nothing — the silently-useless
  case), `service-targets-pod`, `deployment-has-poddisruptionbudget`, and `stable-version` (deprecated
  `apiVersion`, keyed by `--kubernetes-version`).
- **Same finding, two tools = one gate.** Polaris and kube-score both flag missing resource requests and
  missing probes. Pick one as the pre-merge gate and run the other report-only, or the team maintains two
  exception files for one fix.

## Validating the four controls — the half no scanner scores

A benchmark scores *configuration*. These four procedures prove the *control*. This is the line between
this skill and `devops-auditor`: the auditor confirms a `NetworkPolicy` resource exists; this confirms the
packet is dropped.

**1 — RBAC least privilege (A01 · ATT&CK T1078.004).** Scanners flag `cluster-admin` bindings; they do not
tell you what a given workload's ServiceAccount can actually do:

```bash
# What can this workload's identity do — the answer, not the binding.
kubectl auth can-i --list \
  --as=system:serviceaccount:orders:orders-api --namespace orders

# The specific escalations worth a named check, each expected to answer "no".
kubectl auth can-i create pods --as=system:serviceaccount:orders:orders-api -n kube-system
kubectl auth can-i get secrets --as=system:serviceaccount:orders:orders-api --all-namespaces
kubectl auth can-i '*' '*' --as=system:serviceaccount:orders:orders-api

# Every binding that grants cluster-admin, and to whom.
kubectl get clusterrolebindings -o json \
  | jq -r '.items[] | select(.roleRef.name=="cluster-admin")
           | "\(.metadata.name)\t\(.subjects[]?.kind):\(.subjects[]?.name)"'
```

Assert an **expected answer per row** (`no` for every escalation above) — a matrix of subject × verb ×
resource with one expected value each, which is the same discipline
`qa-security-testing-permission-testing` applies to an API's BOLA/BFLA matrix, one layer down.

**2 — NetworkPolicy actually enforces (A01 · ATT&CK T1210).** The two failure modes are invisible in YAML:
a namespace with **no default-deny**, and a **CNI that does not implement NetworkPolicy at all** (a plain
kubenet cluster silently accepts every policy and enforces none — the manifest is perfect and the network
is flat).

```bash
# Is there a default-deny per namespace at all? Absence is the finding.
kubectl get networkpolicy -A -o json \
  | jq -r '.items[] | select(.spec.policyTypes|index("Ingress"))
           | select(.spec.podSelector == {}) | .metadata.namespace' | sort -u

# The probe: one short-lived pod, one expected result, deleted in the same run.
kubectl run netpol-probe -n orders --rm -i --restart=Never \
  --image=curlimages/curl:8.11.1 -- \
  curl -sS --max-time 5 http://payments-api.payments.svc.cluster.local:80/health
# EXPECTED: timeout / connection refused. A 200 means the policy is not enforced.
```

Probe **both directions of each expectation** — one call that must succeed and one that must be blocked.
A probe that only tests the blocked path cannot distinguish "policy works" from "the service was down".

**3 — Pod Security Admission actually rejects (A01/A02 · ATT&CK T1611).** PSA is opt-in per namespace via
labels, and a namespace with no label runs `privileged` silently:

```bash
# Which namespaces are unlabelled — i.e. accept a privileged pod today.
kubectl get ns -o json | jq -r '.items[]
  | select(.metadata.labels["pod-security.kubernetes.io/enforce"] == null)
  | .metadata.name'

# Prove enforcement rather than reading the label: a dry-run apply that MUST be rejected.
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
# EXPECTED: rejected by the admission webhook. Created/accepted is the finding.
```

`--dry-run=server` runs the full admission chain **without persisting the object** — it is the safe way to
prove an admission control (PSA, Polaris webhook, Kyverno, Gatekeeper) actually blocks.

**4 — Secrets at rest (A02/A04).** `Secret` is base64, not encryption. On a self-managed cluster, the
apiserver needs `--encryption-provider-config` pointing at an `EncryptionConfiguration` whose **first
provider is not `identity`** (kube-bench control **1.2.31**-family covers this); on a managed cluster the
equivalent is the provider's KMS setting — **EKS** envelope encryption with a KMS key, **AKS** KMS etcd
encryption, **GKE** application-layer secrets encryption with Cloud KMS. Report which of the two paths the
cluster is on, and whether the workload uses `Secret` objects at all versus a CSI-mounted external store
(`devops/kubernetes` owns that authoring choice).

## The two spines — OWASP posture, ATT&CK Containers exposure

Every finding carries **both** a posture spine and, where the finding describes something an attacker
*does*, an ATT&CK technique. **The matrix is keyed to the surface: use ATT&CK Containers, not enterprise.**

| Finding | OWASP Top 10:2025 | ATT&CK (Containers) |
|---|---|---|
| Namespace with no default-deny NetworkPolicy | A01 Broken Access Control | **T1210** Exploitation of Remote Services |
| ServiceAccount bound to `cluster-admin` | **A01** | **T1078.004** Valid Accounts: Cloud Accounts |
| `automountServiceAccountToken: true` on a workload that needs no API access | A01 / A02 | **T1552.001** Unsecured Credentials: Files |
| Privileged container / `hostPID` / `hostPath` mount of `/` | A02 Security Misconfiguration | **T1611** Escape to Host |
| Unauthenticated kubelet read-write port / exposed API server | A02 / A05 | **T1610** Deploy Container · **T1613** Discovery |
| Anonymous auth enabled on the API server | A01 / A02 | **T1078** Valid Accounts |
| No `EncryptionConfiguration` / KMS — Secrets stored plaintext in etcd | A02 / **A04** Cryptographic Failures | **T1552.007** Container API |
| Audit logging disabled on the API server | A09 Logging & Monitoring Failures | *(detection gap — no technique)* |
| `:latest` / unpinned image tags | A03 Supply Chain Failures | **T1525** Implant Internal Image |
| Missing resource limits (noisy-neighbour / resource-exhaustion) | A02 | **T1496** Resource Hijacking |

Findings that are pure CVE matches (a vulnerable package inside the image) are **not** this skill's rows —
they belong to Trivy and `qa-security-image-infra-scan`, mapped to A03.

## Green ≠ safe — state coverage and the handoff

A 92% CIS score and a clean Polaris run mean **the configuration surface these tools model passed**.
Every report closes with what was **not** covered and who owns it:

| Not covered here | Owner |
|---|---|
| CVEs in images, base OS packages, SBOM/provenance | `qa-security-image-infra-scan` (Trivy) |
| Application-layer authz — BOLA/IDOR/BFLA against the API | `qa-security` → `permission-testing` (per stack) |
| Cross-tenant data leakage at the database layer | `data-architect` (owns that leak test) |
| Terraform/Bicep/ARM misconfig scoring | `devops-iac-security` |
| Cloud-account posture — IAM, exposed storage, encryption, logging | `devops-cloud-posture` |
| Runtime threat detection, escape probing, live behavioural alerts | `devops-container-runtime-security` |
| Artifact signing, SLSA provenance, build-pipeline integrity | `devops-supply-chain-security` |
| Whether a detection actually **fired** for any of the above | `observability-engineer-*` (the telemetry backend) |
| Applying every fix | **`devops-engineer`** — this skill finds and retests, it does not edit infrastructure |

A control validated in the lab is validated **for the lab's configuration**. Re-run against the target
environment; do not carry a lab result forward as a production claim.

## Exceptions & triage — ticketed, scoped, expiring

Same discipline as the Trivy `.trivyignore` and the SCA suppression file — defer the full model to
`qa/_shared/security` and apply it here per tool:

```yaml
# polaris-config.yaml (passed with -c/--config) — grade a check, or exempt one named controller.
checks:
  hostIPCSet: danger
  runAsRootAllowed: danger
  automountServiceAccountToken: danger   # PLAT-903: ratcheted up from warning once the backlog cleared
  pullPolicyNotAlways: ignore            # PLAT-812: images are SHA-pinned, so Always is a wasted pull
exemptions:
  - namespace: observability
    controllerNames: ["log-collector"]
    rules: ["hostPathSet", "notReadOnlyRootFilesystem"]
    # PLAT-661: the node log agent legitimately needs /var/log; accepted risk, re-review 2026-11-01.
```

```bash
# kube-bench — skip a control by ID only, never a whole section.
kube-bench run --benchmark cis-1.12 --skip 4.2.6 --exit-code 1

# kube-score — ignore a named test, never lower the whole gate.
kube-score score manifests/*.yaml --ignore-test container-image-pull-policy --exit-one-on-warning
```

- Scope every exception to a **specific control/check ID** with a **ticket + reason + re-review date** in a
  comment beside it. Never "skip section 4", never `--set-exit-code-below-score 0`.
- **Ratchet the score, don't freeze it.** Start `--set-exit-code-below-score` at today's number, raise it
  each sprint. A threshold that never moves is a threshold nobody owns.
- **Prefer the fix.** Almost every Polaris/kube-score finding is a three-line manifest change
  (`devops/kubernetes` has the shape); a suppression is for the genuinely-earned exception only.

## CI wiring — the **deploy** pipeline, not the test lane

> **Ownership fence:** infra posture scans that gate a build belong to the **deploy pipeline**
> (`devops/github-actions` · `devops/gitlab-ci` · `devops/azure-pipelines`), **not** the `qa/cicd/*` test
> lane. That lane owns the test-suite pipeline (shard matrix, Allure publish, perf gate). Wire these gates
> beside the image build, and hand raw results off as artifacts.

```yaml
# .github/workflows/k8s-posture.yml — cross-link devops/github-actions
name: K8s Security Posture
on: [pull_request]

permissions:
  contents: read
  security-events: write        # SARIF upload only; no cloud credentials needed for the static jobs

jobs:
  # STATIC — manifests only, no cluster, safe on every PR.
  manifest-posture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Render the chart (kube-score and Polaris score real YAML, not templates)
        run: helm template ./charts/orders-api -f ./charts/orders-api/values-prod.yaml > rendered.yaml
      - name: kube-score — pre-merge gate
        run: |
          docker run --rm -v "$PWD:/project" zegl/kube-score:v1.20.0 \
            score /project/rendered.yaml --output-format ci --exit-one-on-warning
      - name: Polaris — danger-severity gate (exit 3) and the score ratchet (exit 4)
        run: |
          docker run --rm -v "$PWD:/workdir" \
            us-docker.pkg.dev/fairwinds-ops/oss/polaris:10.2.2 \
            polaris audit --audit-path /workdir/rendered.yaml \
              --set-exit-code-on-danger --set-exit-code-below-score 90 --only-show-failed-tests
      - name: Kubescape — NSA + MITRE mapping, SARIF to code-scanning
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

  # LIVE — scheduled, against a cluster we own, with a recorded authorization line. Never on a PR from a fork.
  cluster-benchmark:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    environment: security-lab          # the approval gate that carries the authorization record
    steps:
      - uses: azure/setup-kubectl@v4
      - name: kube-bench as an in-cluster Job (managed cluster — no master/etcd checks)
        run: |
          kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/v0.16.0/job-eks.yaml
          kubectl wait --for=condition=complete job/kube-bench --timeout=300s
          kubectl logs job/kube-bench > kube-bench.txt
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: k8s-posture, path: "*.txt" }
```

Static jobs gate the PR; the live benchmark is **scheduled and environment-gated**, because it needs
cluster credentials and a live target — exactly the two things a fork PR must never get.

## Anti-patterns

- **Running kube-bench's `master`/`etcd` targets against a managed cluster.** EKS/AKS/GKE do not expose the
  control plane; every check FAILs on a missing file and the score is fiction. *Fix:* `--targets
  node,policies,managedservices` with the provider benchmark (`eks-1.5.0`, `aks-1.0`, `gke-1.6.0`).
- **Reporting a CIS percentage with no benchmark version.** "We're at 84% CIS" is unfalsifiable and
  incomparable run-over-run. *Fix:* state benchmark + tool version + targets + scope on every report.
- **Treating `[WARN]` as a pass.** WARNs are the controls a machine *cannot* check — often the most
  important ones (audit-log review, policy existence). *Fix:* every WARN is a row a human answers; count
  them separately from PASS.
- **Scoring an un-rendered Helm chart or Kustomize base.** `{{ .Values.x }}` is not YAML; the tool either
  errors or silently scores nothing. *Fix:* `helm template` / `kubectl kustomize` first, then score.
- **Gating on both Polaris and kube-score for the same check.** One fix, two red builds, two exception
  files, and the team mutes whichever is noisier. *Fix:* one pre-merge gate; the other runs report-only.
- **Confusing "a NetworkPolicy exists" with "traffic is blocked."** A CNI that does not implement
  NetworkPolicy accepts every policy and enforces none. *Fix:* run the reachability probe — both a
  must-succeed and a must-be-blocked call.
- **Auditing RBAC by reading Role YAML.** Bindings compose; the effective permission set is not visible in
  any one file. *Fix:* `kubectl auth can-i --list --as=system:serviceaccount:...` with an expected answer
  per row.
- **Reading a namespace's PSA label instead of proving admission rejects.** A label with no admission
  plugin enabled, or a `warn`-only level, reads identically to enforcement. *Fix:* `--dry-run=server` apply
  of a deliberately-violating pod; it must be rejected.
- **Probing a live cluster without a recorded, expiring authorization line** — or reusing last week's.
  *Fix:* per-run, target-scoped, `#volatile`, never cached in the orientation file.
- **Leaving the probe pod behind.** *Fix:* `--rm --restart=Never`, one namespace, and log both the creation
  and the deletion.
- **Treating a clean posture scan as "the cluster is secure."** These tools are blind to image CVEs,
  application authz, runtime behaviour, and cloud-account IAM. *Fix:* run the sibling lanes and publish the
  coverage table above.
- **Fixing findings from inside this skill.** *Fix:* hand every finding to `devops-engineer` with the
  control ID; this lane finds and **retests**.

## Rules (hard constraints)

- **Probing a live cluster requires a recorded, per-run, target-scoped authorization line that expires**
  (`Authorization: <context+namespaces> · by <name> · expires <date>`). It is **`#volatile`** — never
  cached in `docs/agent-context/`, never carried between runs. **Owned/throwaway clusters only**;
  production is a separate, louder sign-off than a lab.
- **Pin every tool version and state the benchmark version** in the report. A score without its benchmark,
  targets, and scope is not a result.
- **Use the provider benchmark and drop control-plane targets on managed clusters** (`eks-*`/`aks-*`/`gke-*`
  with `--targets node,policies,managedservices`).
- **`--exit-code 1` (kube-bench) / `--set-exit-code-on-danger` (Polaris) / `--exit-one-on-warning`
  (kube-score) / `--severity-threshold` (Kubescape) are the gates** — every one of these tools is
  report-only by default.
- **Render before you score.** Helm/Kustomize sources go through `helm template` / `kubectl kustomize`.
- **Every finding carries both spines**: OWASP Top 10:2025 for posture, **ATT&CK Containers** technique IDs
  for anything an attacker does. **Never the enterprise matrix for a cluster finding.**
- **Validate the control, don't just read the field**: RBAC via `kubectl auth can-i` with an expected
  answer per row; NetworkPolicy via a reachability probe testing **both** directions; admission via
  `--dry-run=server` on a deliberately-violating object; secrets-at-rest via the `EncryptionConfiguration`
  / provider-KMS setting.
- **The probe pod is the only thing this skill creates** — named, namespaced, short-lived, deleted in the
  same run, with creation and removal both logged. Nothing else is written to the cluster.
- **Own the boundary:** benchmark scoring · framework mapping · best-practice validation · control
  validation. **CVEs, SBOM, and raw IaC template scanning belong to Trivy**
  (`qa-security-image-infra-scan`) — run both, and do not double-gate the same manifest check.
- **Exceptions are ticketed and scoped to one control/check ID with a re-review date.** No blanket section
  skips, no score threshold of zero. **Ratchet the threshold upward.**
- **Read-only on infrastructure.** This skill finds, scores, and **retests**; `devops-engineer` applies
  every fix.
- **Infra posture gates live in the deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`),
  not the `qa/cicd/*` test lane. Live-cluster jobs are scheduled and environment-gated, never fork-PR.
- **Green ≠ safe.** Every report states its coverage and names the handoff for what it did not cover.

## Cross-references

- `references/kube-bench.md` — CIS targets and benchmark selection, the managed-cluster story, the in-cluster
  Job pattern, JSON output shape, WARN handling, and control-by-control remediation reading.
- `references/kubescape.md` — the framework catalog (`nsa` / `mitre` / `cis-*`), control IDs, the
  ATT&CK-Containers mapping, static vs live scanning, gating thresholds, and the operator/continuous mode.
- `references/polaris.md` — the check catalog by category and severity, `polaris-config.yaml` (grading,
  exemptions, custom JSON-schema checks), the dashboard and admission-webhook modes, **plus the kube-score
  test catalog** and the pick-one-gate rule between them.
- **`qa-security-image-infra-scan`** — the **boundary partner**: Trivy owns image/OS **CVEs**, SBOM (A03),
  `trivy config` IaC scanning, and `trivy k8s` cluster CVE scanning. This skill owns **benchmark scoring,
  framework mapping, and control validation**. Run both; do not double-gate the same manifest check.
- **`devops-auditor`** — the **static-conformance sibling**. It sweeps the repo against *this plugin's own
  rules* (section C Kubernetes workloads, G identity & credentials) read-only and produces
  `docs/audits/<NNN>-devops-conformance-r<N>.md`. **The fence: it confirms the field is set; this runs the
  benchmark and proves the control fires.** A pure static manifest misconfig stays with the auditor.
- `devops-iac-security` · `devops-cloud-posture` · `devops-container-runtime-security` ·
  `devops-supply-chain-security` · `devops-threat-modeling` · `devops-infra-controls-validation` — the
  sibling infra-security lanes: Terraform/Bicep misconfig scoring, CSPM/IAM, runtime detection and escape
  probing, artifact signing and provenance, the STRIDE model that scopes the assessment, and the
  secrets/encryption/monitoring control checks.
- **`infra-security-tester`** — the phased orchestrator that runs this skill (Phase 3, K8s & runtime).
  Read-heavy and **retest-capable**: it re-runs after remediation and reports the delta.
- `devops-engineer` — **applies every fix**; the remediation half of the pair.
- `devops/kubernetes` — the authoring skill whose output this scores (securityContext, NetworkPolicy,
  probes, Workload Identity / IRSA, PDB/HPA). A finding here is usually a three-line change there.
- `qa-security` + `qa/_shared/security` — the app-layer OWASP backbone, the authorization-to-scan rule this
  skill's live gate inherits, and the ticketed-triage discipline.
- `qa-security-testing-permission-testing-{java,dotnet,typescript}` — the **application** authz matrix
  (BOLA/IDOR/BFLA). The RBAC matrix above is the same discipline one layer down, at the cluster.
- `data-architect` — owns the **cross-tenant leak test** that proves data isolation; cluster-level isolation
  is not database-level isolation.
- `observability-engineer-{dotnet,java,node}` — whether the audit logging this skill flags as missing is
  actually wired, and whether anything would alert.
