# Polaris — best-practice workload config validation

**Polaris** (Fairwinds) validates Kubernetes **workload configuration** against a catalog of
best-practice checks — probes, resource requests/limits, running as root, image tags, dangerous
capabilities — and grades each workload. Unlike kube-bench (a node/control-plane CIS benchmark) and Kubescape
(framework compliance), Polaris is **opinionated workload hygiene**: the "is this Deployment shaped sanely"
gate. It runs three ways from one binary/image — as a **CLI audit** (static or live), as a **dashboard**, and
as a **validating admission webhook** — pinned at `quay.io/fairwinds/polaris:10.2.2`.

## The three modes

```bash
# 1. AUDIT — static manifests / a Helm chart (safe, pre-merge, no cluster, no authorization).
polaris audit --audit-path ./k8s --format pretty
helm template ./charts/api | polaris audit --audit-path - --format json > polaris.json

# 2. AUDIT — a live cluster (authorization-gated: reads the workload API of owned infra).
polaris audit --format json > polaris.json

# 3. DASHBOARD — browsable score, run in-cluster or locally against the current context.
polaris dashboard --port 8080
```

- **Static audit is the default gate** — it reads YAML, needs no cluster and no authorization, and runs on
  every PR including forks. **Live audit** reads the running workloads and is authorization-gated per the
  `infra-security-tester` gate; confirm the owned target and record the `#volatile` authorization.
- The **admission webhook** (`polaris` in webhook mode) *blocks* non-conforming workloads at apply time. That
  is an enforcement change to a live cluster — it belongs to `devops-engineer` deploying it, not to this
  read-only assessment lane; note it as the remediation, don't stand it up here.

## The check catalog — by category

Polaris checks are grouped; each has a configurable severity (`danger` / `warning` / `ignore`):

| Category | Representative checks | Spine |
|---|---|---|
| **Security** | `runAsNonRoot`, `privilegeEscalationAllowed`, `hostIPCSet`/`hostPIDSet`/`hostNetworkSet`, `dangerousCapabilities`, `readOnlyRootFilesystem`, `insecureCapabilities` | OWASP **A02** · ATT&CK **T1611** |
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
# Fail the step on any danger-severity result.
polaris audit --config polaris-config.yaml --audit-path ./k8s --format json --set-exit-code-on-danger \
  --set-exit-code-below-score 90 > polaris.json
```

- `--set-exit-code-on-danger` exits non-zero on any `danger` finding (the gate).
- `--set-exit-code-below-score 90` gates on the aggregate grade — pair the two so a pile of `warning`s below
  the bar also fails. Parse `polaris.json` (`.results[].PodResult...` with per-check `Success`/`Severity`) for
  a finding list, and quote each check's message into the report.
- Gates land in the **deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), not the
  `qa/cicd/*` test lane.

## Polaris vs kube-score

Both are static workload linters and they overlap heavily. **kube-score** (`kube-score:v1.20.0`) is a single
`kube-score score manifest.yaml` binary with a similar check set and a simple `--exit-one-on-warning` gate —
lighter, no dashboard, no admission mode. Use **kube-score** when you want a zero-config CLI lint in a
pipeline; use **Polaris** when you want the configurable severity policy, the dashboard, or the (engineer-
deployed) admission webhook. Running both adds little; pick one static linter and pair it with a framework
scanner (Kubescape) and the node benchmark (kube-bench).

## Cross-references

- `../SKILL.md` — the router; Polaris answers the "is this workload config sane / score these manifests before
  merge" row.
- `kube-bench.md` — the node/control-plane CIS benchmark (a different surface: the node, not the workload
  spec).
- `kubescape.md` — framework compliance (NSA/MITRE/CIS) with a compliance score; Polaris is opinionated
  workload hygiene, not framework mapping.
- `devops:kubernetes` — the authoring skill whose output Polaris grades; a `danger` finding routes back there
  for `devops-engineer` to fix.
