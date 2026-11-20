# Kubescape — framework scoring (NSA/CISA · MITRE · CIS)

**Kubescape** (a CNCF project) scans **manifests, Helm charts, or a live cluster** against named security
**frameworks** and returns a compliance score plus a per-control finding list with remediation. Its distinct
value over kube-bench is **breadth of framework** and **the ability to score from the API or from static
files** — the same tool grades a PR's manifests and a running cluster. Install the CLI
(`brew install kubescape`, the official install script, or `kubectl krew install kubescape`); the CI action is in `ci-wiring.md`.

## The framework catalog — the reason to reach for it

```bash
kubescape list frameworks
```

| Framework id | What it scores | Spine |
|---|---|---|
| `nsa` | NSA/CISA Kubernetes Hardening Guidance: non-root, immutable filesystem, network separation, RBAC least privilege, secrets management, audit logging | NSA/CISA · OWASP A01/A02 |
| `mitre` | MITRE ATT&CK for Kubernetes (technique-mapped controls) | ATT&CK **Containers** |
| `cis-eks` / `cis-aks` / `cis-v1.10.0` | the CIS benchmark, from the API; a second opinion on kube-bench's workload half | CIS · A02 |
| `allcontrols` | the full control library | mixed |
| `security` | Kubescape's curated high-signal set | mixed |

The **`mitre`** framework is why this skill maps a Kubernetes finding to the ATT&CK **Containers** matrix
directly — each failing control names the technique it fails to mitigate (`T1610` Deploy Container, `T1611`
Escape to Host, `T1613` Container and Resource Discovery, `T1078.004` Valid Accounts: Cloud Accounts,
`T1552.007` Container API creds), so the finding lands on the offensive spine with no manual mapping. The
surface picks the matrix: a cluster finding never maps to the enterprise matrix.

## Running it — static and live

```bash
kubescape scan framework nsa ./charts/orders-api --format sarif --output kubescape.sarif
kubescape scan framework nsa,mitre --format json --output kubescape.json --keep-local
kubescape scan framework cis-v1.10.0 --exclude-namespaces kube-system,kube-public,kube-node-lease
kubescape scan framework nsa --severity-threshold high --format junit --output kubescape.xml
kubescape scan framework nsa,mitre,cis-eks --compliance-threshold 80 --format json --output ks.json --format-version v2
```

- **Static scanning of manifests and charts is file reads**, safe on every PR including forks. A scan against a kubecontext is live and needs the authorization line in `../SKILL.md`; set `--kube-context` and the namespace flags explicitly.
- **`--keep-local`** keeps results off the hosted backend; use it unless the team has deliberately adopted the SaaS.
- **The gate**: `--severity-threshold high` fails on any High+ control; `--compliance-threshold 80` fails the step below an 80% score. Start with a **baseline** score
  and ratchet up rather than demanding 100% on a brownfield cluster (the same ratchet discipline as the SCA
  and Trivy gates).

## Output + gating

```bash
kubescape scan framework nsa . --format json --output ks.json
jq '.summaryDetails.complianceScore' ks.json          # the headline score
jq '[.results[] | select(.controls[]?.status.status=="failed")] | length' ks.json
```

The JSON `summaryDetails` carries the overall `complianceScore` and a per-framework breakdown; each control
result carries an id (`C-0055`), a name, a status, a severity, and a `remediation` string — quote the
remediation into the finding. Emit **SARIF** for inline PR annotation (same consolidation as Trivy).

## The SaaS (Kubescape Cloud / ARMO Platform)

Kubescape has a hosted backend that stores scan history, trend lines, and continuous in-cluster scanning via
an operator. It is **optional** — the CLI is fully functional offline and is the default runnable path here.
Note it as a `references`-level option for a team that wants trend dashboards and image-scanning add-ons, the
same way `cloud-posture` names the commercial CSPMs; nothing in this lane depends on it.

## kube-bench vs Kubescape — run both, they see different surfaces

- **kube-bench** reads the **node filesystem + control-plane process args** — it sees kubelet flags, API
  server config, and etcd file permissions that the API never exposes.
- **Kubescape** reads the **API (or manifests)**: workload posture, RBAC objects, NetworkPolicies and admission config, graded against NSA, MITRE and CIS in one pass. It does not read `/etc/kubernetes/manifests` or kubelet flags on a node. Say in the report which tool produced which control.
- They overlap on the API-visible CIS controls and disagree nowhere that matters; the union is the real CIS
  picture. Use kube-bench for the node/control-plane depth, Kubescape for framework breadth and the ATT&CK
  mapping.

## Cross-references

- `../SKILL.md`: the router; Kubescape answers the NSA/CISA and MITRE framework-scoring rows and the "score
  these manifests before merge" row.
- `kube-bench.md` — the node-level CIS depth Kubescape cannot read from the API; run both.
- `polaris.md` — best-practice config validation with a lighter, opinionated check set; Kubescape is
  framework-compliance-scoped.
- `../../container-runtime-security/references/kube-hunter.md` — the *active-probing* runtime surface;
  Kubescape scores posture, kube-hunter attacks it.
