---
name: container-runtime-security
description: Use when testing a running Kubernetes cluster's attack surface (kube-hunter, Falco), authorization-gated. Triggers "probe our running cluster". Not for CIS scoring (kubernetes-security).
disable-model-invocation: true
---

# DevOps — Container & Runtime Security (kube-hunter · Falco)

Two tools, two halves of the **running-cluster** security question that static scanners cannot answer.
**kube-hunter** probes a **live cluster from an attacker's viewpoint**: it enumerates the reachable surface (open
kubelet, exposed API server, dashboard, etcd, service-account token access) and, in **`--active` mode, attempts
the exploit** to prove the exposure is real. **Falco** (CNCF-graduated) is the **detection half**: an eBPF
DaemonSet that fires a rule when a container escapes to the host, a shell spawns inside a container, or a
sensitive host path is read. This skill then **asserts the rule actually fired**, not merely that it was deployed.

This skill is **language-agnostic**, sits in the infra-security lane under the **`infra-security-tester`** agent,
and owns the **runtime + probing** surface. It does not score manifests (`devops:kubernetes-security`) or scan
shipped artifacts (`qa-<stack>:image-infra-scan`).

> **Authorized-lab self-testing only.** kube-hunter's **`--active` mode performs exploitation-style probes that can
> be disruptive** (it tries to run a pod, read a token, hit an exposed kubelet's `/run` endpoint). It needs a
> **recorded, per-run, target-scoped authorization line that expires**, against a cluster **you own or a
> throwaway**, never cached in the orientation cache (`#volatile`). Lead every active run with the line below; if
> it is absent or expired, run passive discovery and report the surface instead. Passive kube-hunter, Falco
> deployment and detection assertion need no such gate, but stay owned-cluster-only.

```
Authorization: cluster=<owned/lab cluster id or context>  scope=<in-scope namespaces/nodes>
               authorized-by=<name>  window=<start>..<expiry>  mode=active
```

**Two spines per finding.** A runtime probe or detection maps to a **MITRE ATT&CK Containers** technique (`T1610`
Deploy Container, `T1611` Escape to Host, `T1613` Container & Resource Discovery, `T1552.007` Container API
creds); a config exposure kube-hunter reports (dashboard exposed, anonymous API auth) also maps to **OWASP**
(A01 / A05). Tag every custom Falco rule with its ATT&CK technique.

## The fences — three runtime-adjacent skills, three surfaces

| Skill | Surface | Question it answers | State |
|-------|---------|---------------------|-------|
| **`qa-<stack>:image-infra-scan`** (Trivy) | **Static** — image layers, IaC templates, SBOM | "Is the artifact we *ship* clean?" | **Shipped** — pre-deploy |
| **`devops:kubernetes-security`** (kube-bench · Kubescape · Polaris) | **Static config** — manifests + cluster config vs CIS/NSA benchmark | "Is the cluster *configured* to a benchmark?" | **Declared** — posture score |
| **this skill** (kube-hunter · Falco) | **Runtime** — the *running* cluster's reachable surface + live syscall behaviour | "Is the running cluster *exploitable*, and does it *notice* when attacked?" | **Live** — actual behaviour |


A clean Trivy scan says nothing about a kubelet left open on `:10250`; a benchmark pass says nothing about a
detection that fired. `qa-security` owns the app layer (BOLA/IDOR, injection); this skill owns the cluster
beneath it. Run all three.

> **Green ≠ safe.** A clean passive kube-hunter run means no exposed surface was reachable from where you scanned.
> A Falco rule that *deploys* is not a rule that *fires*. Every report names what it did not cover and hands it off.

## Decision matrix — which tool, which mode, which gate

| Need | Tool + mode | Reads / does | Gate | Spine |
|------|-------------|--------------|------|-------|
| Enumerate the cluster's surface **from outside** (a node's IP / CIDR) | `kube-hunter --remote <ip>` / `--cidr` | probes reachable ports/services; **reports only** | none (passive) | ATT&CK `T1613` / OWASP A05 |
| Enumerate the surface **as an insider** (what a compromised pod sees) | `kube-hunter --pod` (run *as* a Job in-cluster) | SA-token access, kubelet, internal API | none (passive) | ATT&CK `T1613` / `T1552.007` |
| **Prove** a found exposure is exploitable | `kube-hunter --active` | **attempts the exploit** (disruptive) | **authorization line (loud)** | ATT&CK `T1610` / `T1611` |
| Scan the whole node subnet, capped | `kube-hunter --pod --quick` (hardlimits to /24) | fast internal sweep | none (passive) | ATT&CK `T1613` |
| **Detect** escape / shell / sensitive-mount at runtime | **Falco** DaemonSet + rules | watches kernel syscalls on every node | deploy to owned cluster | ATT&CK `T1611` / `T1059` |
| **Assert** a detection actually fired | trigger the event → query Falco output | proves the rule works, not just exists | none (blue) | ATT&CK (per rule's tag) |

**Rule of thumb:** **kube-hunter answers "can I get in / how far"** (red, point-in-time probe);
**Falco answers "will I notice when someone does"** (blue, continuous). Run passive kube-hunter freely; gate
`--active` loudly; deploy Falco as owned infra; **and always assert Falco fired** — a deployed-but-unproven
detection is the most common false comfort in this lane.

## kube-hunter — the probe modes

kube-hunter is **archived**: Aqua points CVE-scanning users at Trivy, and no upstream fixes are coming. It
remains the reference tool for attack-surface probing from an attacker's viewpoint. Say so to the user, **pin the
last published image digest**, and name **Tetragon** or **KubeArmor** where the user needs blocking.

```bash
kube-hunter --remote 10.0.0.5                 # passive, from outside
kube-hunter --cidr 10.0.0.0/24 --quick        # passive, sweep capped to /24
kube-hunter --pod                             # passive, as an insider: run in-cluster as a Job
kube-hunter --pod --active                    # ACTIVE: attempts exploits, REQUIRES the authorization line
```

A bare `kube-hunter --pod` **only reports**; `--active` turns "there is an exposed kubelet" into "I read a secret
through it", which is why it carries the gate. Never bake `--active` into a scheduled or recurring Job.

The flag table, the in-cluster Job manifest, reading findings and the report template are in
**`references/kube-hunter.md`**; read it before running kube-hunter.

## Falco — detect, then ASSERT it fired

Falco runs as a **DaemonSet on every node** and watches syscalls via **modern eBPF** (the default driver; the
legacy eBPF probe and gVisor were removed in 0.44). Install it with `driver.kind=modern_ebpf` and
**`falcosidekick.enabled=true`**: its alerts must land in a queryable sink (Loki / Alertmanager, the
`observability-engineer-*` handoff) or there is nowhere to assert a detection. Custom rules live in a separate
`customRules` file, never in the shipped `falco_rules.yaml`. The Helm install, falcoctl rule delivery, custom-rule
YAML, sink wiring and tuning are in **`references/falco.md`**; read it before deploying Falco or writing a rule.

### Detection validation — the step that makes it real

**Deploying Falco is not detecting anything until you prove a rule fires.** This is the discipline that
separates a real blue capability from a checkbox: for each rule you rely on, **trigger the event on an
authorized target and assert the alert landed** in the sink.

```bash
# 1. Trigger the behaviour the "Shell spawned in container" rule watches for.
kubectl run canary --image=busybox --restart=Never -n security-testing -- sleep 3600
kubectl exec -it canary -n security-testing -- /bin/sh -c "echo triggered"

# 2. ASSERT the rule fired. Read Falco's own output first...
kubectl logs -l app.kubernetes.io/name=falco -n falco --since=1m | grep "Shell in container"

# 3. ...then assert it reached the SINK (Loki) — the alert an on-call would actually see.
logcli query '{app="falcosidekick"} |= "Shell in container"' --since=2m   # gate: >=1 hit

# 4. Clean up the canary.
kubectl delete pod canary -n security-testing
```

- The assertion is **binary per ATT&CK technique**: did the rule for `T1059` fire on the triggering event —
  yes/no. A "no" is a **detection gap**, reported as such (the rule is disabled, mis-scoped, the driver isn't
  loaded, or the sink is broken) — not a passing run.
- **Assert at the sink, not just Falco's stdout.** A rule that fires locally but whose alert never reaches
  Loki/Alertmanager is invisible to the responder — the detection is only as real as its last hop.
- This is the seam the **`purple-team-engineer` agent + its `detection-validation` skill** own at
  scale (run every ATT&CK technique on a schedule, assert each detection still fires, catch "security drift").
  This skill does the **single-rule** version inline; name that lane as the partner.

## Trivy at runtime

`trivy k8s` scans running workloads' images and configs from the K8s API. That is still **static** scanning of
what is deployed: it belongs to `qa-<stack>:image-infra-scan`, not here. Do not fold it into this skill.

## Rules (hard constraints)

- **`--active` is the loud gate.** It runs only with a recorded, target-scoped, **expiring** authorization line,
  against a cluster **you own or a throwaway**, never cached, never in a scheduled Job. Absent or expired →
  passive discovery only.
- **Deploy Falco, then ASSERT it fired.** A rule is not a detection until a triggering event proves it fires
  **and reaches the sink**. A non-firing relied-on rule is a detection gap, not a pass.
- **Wire Falco to a telemetry backend** before relying on detection. No backend → report "no detection
  surface", never a silent pass.
- **Read-only on infra; the fix is someone else's.** `devops-engineer` applies remediation. No secrets in
  scan or rule config; findings redact secret contents (report the blast radius, never the value); nothing
  sensitive is committed under `docs/`.
- A clean run ≠ "secure": it means the probe found no reachable surface, or the detection fired. Run the full
  infra lane (`infra-security-tester`) and the app lane (`qa-security`).
