# kube-hunter — cluster attack-surface probing (deep dive)

The red half of `devops-container-runtime-security`: probe a **running** Kubernetes cluster from an
**attacker's viewpoint**, enumerate the reachable surface, and — under the loud authorization gate — **prove
the exposure is exploitable**. This file is the full command/mode/gate reference; the SKILL.md holds the
decision matrix and the one-line active gate.

> **Honest status (say this to the user).** kube-hunter is **archived / no longer under active development**.
> The upstream notice: *"kube-hunter is not under active development anymore. If you're interested in scanning
> Kubernetes clusters for known vulnerabilities, we recommend using Trivy."* It remains the **reference tool
> for attack-surface *probing*** because Trivy does not do the active reachability/exploit probe kube-hunter
> does — but treat it as **frozen**: pin the last published image digest, expect no fixes.
> **Enforcement-grade successors** for the runtime surface: **Tetragon** (Cilium — in-kernel LSM block/kill)
> and **KubeArmor**; for benchmark posture, **Kubescape** (`devops-k8s-security`).

## The authorization gate — restated, because one mode exploits

kube-hunter has two postures:

| Posture | Flag | What it does | Gate |
|---------|------|--------------|------|
| **Passive** (default) | *(none)* / `--remote` / `--pod` | **Reports** the surface — finds the open kubelet, does not touch it | owned-cluster-only, no per-run line |
| **Active** | `--active` | **Attempts the exploit** — reads the token through the kubelet, tries to run a pod; disruptive | **recorded, scoped, expiring authorization line** |

```
Authorization: cluster=<owned/lab cluster id or context>  scope=<in-scope namespaces/nodes>
               authorized-by=<name>  window=<start>..<expiry>  mode=active
```

Rules for the gate (from the security-expansion safety model, applied to this one disruptive mode):

- **`#volatile`** — never written to the orientation cache (`docs/agent-context/`); it expires with the
  window and is re-confirmed every run.
- **Owned / throwaway cluster only** — never a third party's. This is authorized self-testing of your own
  systems.
- **Not scheduled** — `--active` is a witnessed, one-off run, never baked into a recurring Job.
- **Absent or expired → do not run `--active`.** Run passive discovery, report the surface, and note that
  active confirmation was skipped for lack of authorization.

## Scanning modes

### Remote (external attacker viewpoint)

Probe a node/API address from where the binary runs — what an attacker outside the cluster can reach.

```bash
kube-hunter --remote 10.0.0.5
kube-hunter --remote api.mycluster.internal
kube-hunter --cidr 10.0.0.0/24 --quick        # sweep a subnet, capped to /24
```

Finds: exposed API server (anonymous auth), open kubelet (`:10250` read/write, `/pods`, `/run`), exposed
dashboard, etcd on `:2379`, cAdvisor, and other services reachable from that vantage point.

### Pod / internal (compromised-insider viewpoint)

Run kube-hunter **as a pod inside the cluster** — what an attacker who already popped one pod can reach. This
is the highest-signal mode for most engagements because most real breaches start from an insider foothold.

```bash
kube-hunter --pod                              # passive insider probe
kube-hunter --pod --quick                      # bounded internal sweep
kube-hunter --pod --active                     # ACTIVE — authorization line required
```

Finds: the **mounted service-account token** and what it can do (list secrets, create pods), reachable
kubelet, internal API access, access to other namespaces.

### Interface / auto-discover

```bash
kube-hunter --interface                                    # scan all local NICs
kube-hunter --k8s-auto-discover-nodes --kubeconfig ~/.kube/config   # enumerate + scan every node
```

### Utility / dry-run

```bash
kube-hunter --list                             # list every hunter/test (dry-run of what runs)
kube-hunter --mapping                          # print the node network map only, no hunting
kube-hunter --raw-hunter-names                 # class names, for --custom whitelisting
kube-hunter --custom <HunterName>              # run only named hunters
```

## Flag reference

| Flag | Effect |
|------|--------|
| `--remote <ip/host>` | Probe a specific address (external viewpoint) |
| `--cidr <range>` | Sweep a CIDR range |
| `--quick` | Hardlimit subnet scanning to a /24 (fast, bounded) |
| `--interface` | Scan all network interfaces of the host the binary runs on |
| `--pod` | Run as a pod inside the cluster (insider viewpoint) |
| `--active` | **Active hunting — attempts exploits. Authorization line required. Disruptive.** |
| `--k8s-auto-discover-nodes` | Query the K8s API for all nodes and scan them |
| `--kubeconfig <path>` | Explicit kubeconfig (for out-of-cluster auto-discovery) |
| `--service-account-token <jwt>` | Supply a bearer token explicitly instead of the mounted one |
| `--mapping` | Node network map only |
| `--list` | List available tests |
| `--custom <names>` | Whitelist specific hunters |
| `--raw-hunter-names` | Print hunter class names |
| `--dispatch stdout\|http` | Report output method (`http` posts JSON to `KUBEHUNTER_HTTP_DISPATCH_URL`) |
| `--log DEBUG\|INFO\|WARNING` | Log level |

## Running it as an authorized in-cluster Job

The insider viewpoint means running kube-hunter *inside* the cluster — deliberately, scoped, on an owned
cluster. **This is runtime deployment, not a build gate** (it probes a live cluster; it does not gate a
pipeline).

```yaml
# kube-hunter-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kube-hunter
  namespace: security-testing          # dedicated, in-scope namespace
spec:
  backoffLimit: 0                       # a probe should not silently retry
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: kube-hunter
          # Archived tool — pin the last published digest and freeze it.
          image: aquasec/kube-hunter@sha256:<pinned-digest>
          command: ["kube-hunter"]
          args: ["--pod", "--quick"]    # add "--active" ONLY with the authorization line
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            capabilities: { drop: ["ALL"] }
```

```bash
kubectl apply -f kube-hunter-job.yaml
kubectl wait --for=condition=complete job/kube-hunter -n security-testing --timeout=300s
kubectl logs job/kube-hunter -n security-testing
kubectl delete -f kube-hunter-job.yaml         # remove the Job when done (cleanup discipline)
```

The Job's ServiceAccount defines what the insider probe *can* reach — scope it to the engagement (a
default-namespace SA to simulate a low-priv pod, or a broader one to test blast radius from a privileged pod).

## Reading findings — the two spines

kube-hunter reports **vulnerabilities** (actively confirmed under `--active`) and **services** (surface it
found). Map each:

| Finding | ATT&CK (Containers) | OWASP |
|---------|---------------------|-------|
| Accessible service-account token → list/create resources | `T1552.007` Container API creds | A01 Broken Access Control |
| Exposed / writable kubelet (`/run`, `/exec`) → run commands in pods | `T1610` Deploy Container / `T1609` Container Admin Command | A05 Misconfiguration |
| Anonymous API-server auth | `T1613` Container & Resource Discovery | A01 / A05 |
| Privileged pod → host filesystem | `T1611` Escape to Host | A05 |
| Exposed dashboard / etcd | `T1613` | A05 |

- **State both** where they apply: ATT&CK for the runtime technique, OWASP for the config exposure.
- A `--active`-confirmed finding is **proof-of-exploit** — it outranks a passive "service exposed" because it
  demonstrated the reach. Note in the report which findings were actively confirmed vs surface-only.

## Fences (restated)

- **vs Trivy (`qa-security-image-infra-scan`):** Trivy reads images/IaC/SBOM **as files, statically**;
  kube-hunter probes the **running cluster's reachability**. Trivy for CVEs, kube-hunter for exploitable
  surface. Aqua itself points CVE users to Trivy — do not use kube-hunter as a CVE scanner.
- **vs `devops-k8s-security`:** benchmark scoring (kube-bench/Kubescape/Polaris) grades the *declared* config
  against CIS/NSA; kube-hunter proves the *running* surface is reachable. A benchmark pass ≠ not exploitable.
- **vs the exploit-validation lane (Stage 2 `qa-security`):** that proves a single **app-layer** vuln fires;
  kube-hunter proves **cluster/infra** surface is reachable. Different layer.

## The report — required elements

- **Authorization line** verbatim at the top of any `--active` run (target, authorizer, window, mode).
- **Action log** for active runs: what was attempted, against what, when — the accountability trail.
- **Findings** with the two-spine mapping and active-confirmed vs surface-only marked.
- **Handoff:** what was not covered (app layer → `qa-security`; CVEs → Trivy; detection → Falco), and the
  remediation owner (**`devops-engineer`**). kube-hunter finds and retests; it does not edit the cluster.
- **Secrets redacted:** if the probe recovered a token/secret, report *that* it did and its blast radius,
  never the contents; nothing sensitive committed under `docs/`.
