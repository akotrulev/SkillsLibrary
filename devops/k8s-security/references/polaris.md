# Polaris — best-practice workload config validation

**Polaris** (Fairwinds) validates Kubernetes **workload configuration** against a catalog of
best-practice checks — probes, resource requests/limits, running as root, image tags, dangerous
capabilities — and grades each workload. Unlike kube-bench (a node/control-plane CIS benchmark) and Kubescape
(framework compliance), Polaris is **opinionated workload hygiene**: the "is this Deployment shaped sanely"
gate. It runs three ways from one binary/image — as a **CLI audit** (static or live), as a **dashboard**, and
as a **validating admission webhook**. The pinned image and its registry are in `../SKILL.md` Setup.

## The three modes

```bash
polaris audit --audit-path ./manifests --format pretty
polaris audit --helm-chart ./charts/orders-api --helm-values ./charts/orders-api/values-prod.yaml
polaris audit --format json --output-file polaris.json
polaris dashboard --port 8080
```

- **Static audit is the default gate**: it reads YAML, needs no cluster, and runs on every PR including forks. The default `--format` is json; ask for `pretty`. **Live audit** (no `--audit-path`: it reads the current kube context) needs the authorization line in `../SKILL.md`.
- The **admission webhook** (`polaris` in webhook mode) *blocks* non-conforming workloads at apply time. That
  is an enforcement change to a live cluster — it belongs to `devops-engineer` deploying it, not to this
  read-only assessment lane; note it as the remediation, don't stand it up here.

## The check catalog — by category

Polaris checks are grouped; each has a configurable severity (`danger` / `warning` / `ignore`). **Read severities from the shipped `default.yaml`, not the docs site**: the two disagree on `runAsRootAllowed`, `hostNetworkSet` and `linuxHardening`.

| Category | Representative checks | Spine |
|---|---|---|
| **Security**, danger by default | `hostIPCSet`, `hostPIDSet`, `hostNetworkSet`, `runAsRootAllowed`, `runAsPrivileged`, `privilegeEscalationAllowed`, `dangerousCapabilities`, `sensitiveContainerEnvVar`, `sensitiveConfigmapContent` | OWASP **A02** · ATT&CK **T1611** |
| **RBAC**, danger by default; nothing else in this set checks it statically | `clusterrolebindingClusterAdmin`, `rolebindingClusterAdminRole`, `clusterrolePodExecAttach`, `rolePodExecAttach` | **A01** · **T1078.004** |
| **Security**, warning by default | `automountServiceAccountToken`, `hostPathSet`, `hostProcess`, `linuxHardening`, `notReadOnlyRootFilesystem`, `procMount`, `insecureCapabilities`, `missingNetworkPolicy` | A02 |
| **Reliability** | `livenessProbeMissing`, `readinessProbeMissing`, `pullPolicyNotAlways`, `tagNotSpecified` (`:latest`), `priorityClassNotSet` | A02 · reliability |
| **Efficiency / Resources** | `cpuRequestsMissing`, `cpuLimitsMissing`, `memoryRequestsMissing`, `memoryLimitsMissing` | availability (`T1499`) |
| **Networking** | `hostPortSet`, `tlsSettingsMissing` (Ingress) | A02 |

The security and resource checks overlap with what the parent SKILL.md validates as **isolation** — a missing
`runAsNonRoot` or an unbounded resource limit is both a Polaris `danger` and a real isolation/availability
gap. Polaris is the fast static pre-merge net; the parent skill's live RBAC/NetworkPolicy validation is what
proves isolation *holds* at runtime.

## Configuration — `polaris-config.yaml` (grading + severity)

```yaml
# polaris-config.yaml — tune which checks run and at what severity.
checks:
  runAsNonRoot: danger
  readOnlyRootFilesystem: warning
  cpuLimitsMissing: warning
  tagNotSpecified: danger
  livenessProbeMissing: danger
  hostNetworkSet: danger
exemptions:
  - controllerNames: [log-collector]        # a daemon that legitimately needs hostNetwork
    rules: [hostNetworkSet]
```

```bash
polaris audit --config polaris-config.yaml --audit-path ./k8s --format json > polaris.json
```

- **Severity is a policy decision:** `danger` fails the gate, `warning` surfaces without blocking, `ignore`
  drops the check. Start with the security checks at `danger` and ratchet the reliability/efficiency ones up
  from `warning` as the backlog clears — the same ratchet as the SCA/Trivy gates.
- **`exemptions`** are the ticketed-suppression equivalent: scope each to a specific controller **and** rule,
  with a ticket/reason, never a blanket ignore. The daemon that genuinely needs `hostNetwork` is an
  exemption; "turn off `hostNetworkSet` everywhere" buries the next real one.

## Gating in CI

```bash
polaris audit --config polaris-config.yaml --audit-path ./manifests --set-exit-code-on-danger \
  --set-exit-code-below-score 90 --only-show-failed-tests
```

- `--set-exit-code-on-danger` exits 3 on any `danger` finding (the gate).
- `--set-exit-code-below-score 90` exits 4 on the aggregate grade; start it at today's number and raise it each sprint. Pair the two so a pile of `warning`s below
  the bar also fails. Parse the JSON (`.results[].PodResult...` with per-check `Success`/`Severity`) for a finding list, and quote each check's message into the report.
- Gates land in the **deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), not the
  `qa/cicd/*` test lane.

## kube-score — the pre-merge pass with no cluster

```bash
helm template ./charts/orders-api | kube-score score -
kube-score score manifests/*.yaml --output-format ci --exit-one-on-warning \
  --kubernetes-version v1.31 --ignore-test container-image-pull-policy
```

- **kube-score scores rendered YAML.** A Helm chart or Kustomize overlay goes through `helm template` or `kubectl kustomize` first; scoring the un-rendered template scores nothing real.
- **Its unique value is the cross-object checks** a per-manifest linter misses: `pod-networkpolicy` (a pod no NetworkPolicy selects), `networkpolicy-targets-pod` (a policy selecting nothing, the silently-useless case), `service-targets-pod`, `deployment-has-poddisruptionbudget`, and `stable-version` (deprecated `apiVersion`, keyed by `--kubernetes-version`).
- **`--exit-one-on-warning` is the gate**; ignore a test by name, never lower the whole gate.
- Its last tagged release is the pin in `../SKILL.md` Setup (April 2025); `master` still moves. Keep it as the cheap pre-merge pass, not the only gate.

## Polaris vs kube-score — one pre-merge gate

Both are static workload linters, and both flag missing resource requests and probes. Pick one as the pre-merge gate and run the other report-only, or the team maintains two exception files for one fix. **kube-score** is zero-config with a simple gate. **Polaris** has the severity policy, the dashboard and the admission webhook. Pair the chosen linter with Kubescape for frameworks and kube-bench for the node.

## Cross-references

- `../SKILL.md`: the router; Polaris answers the "is this workload config sane / score these manifests before
  merge" row.
- `kube-bench.md` — the node/control-plane CIS benchmark (a different surface: the node, not the workload
  spec).
- `kubescape.md` — framework compliance (NSA/MITRE/CIS) with a compliance score; Polaris is opinionated
  workload hygiene, not framework mapping.
- `devops:kubernetes` — the authoring skill whose output Polaris grades; a `danger` finding routes back there
  for `devops-engineer` to fix.
