---
name: devops-container-runtime-security
description: Use to test the RUNNING cluster's attack surface and runtime behaviour. kube-hunter probes a live cluster from an attacker's viewpoint (authorization-gated `--active` mode); Falco detects container escape at syscall level. Triggers "probe our running cluster", "is our cluster exploitable from a pod", "deploy Falco". Not for static image/IaC scanning (`qa-security-image-infra-scan`), CIS scoring of manifests (`devops-k8s-security`), or app exploitation (`qa-security`).
---

# DevOps — Container & Runtime Security (kube-hunter · Falco)

Two tools, two halves of the **running-cluster** security question that static scanners cannot answer.
**kube-hunter** (Aqua Security) probes a **live cluster from an attacker's viewpoint** — it enumerates the
reachable attack surface (open kubelet, exposed API server, dashboard, etcd, service-account token access)
and, in **`--active` mode, attempts the exploit** to prove the exposure is real, not theoretical.
**Falco** (CNCF-graduated) is the **blue/detection half**: an eBPF DaemonSet that watches kernel syscalls on
every node and fires a rule the moment a container escapes to the host, a shell spawns inside a container, or
a sensitive host path is read — and this skill's discipline is to then **assert the rule actually fired**
(detection validation), not merely deploy it.

> **⚠️ Authorized-lab self-testing only — LOUDER here than any other infra skill, because one mode
> exploits.** kube-hunter's **`--active` mode performs exploitation-style probes that can be disruptive**
> (it will, e.g., try to run a pod, read a token, or hit an exposed kubelet's `/run` endpoint). Running it is
> a **defensive act against your own cluster** — the point is to find the hole before an attacker does. It is
> therefore gated exactly like the offensive lanes: a **recorded, per-run, target-scoped authorization line
> that expires**, against a cluster **you own or a throwaway**, **never a third party's**, **never cached**
> in the orientation cache (it is `#volatile`). Passive kube-hunter (remote/internal discovery), Falco
> deployment, and detection assertion are lower-risk and need no such gate. **The `--active` gate is the loud
> one.** Lead every active run with the authorization line below; if it is absent or expired, **do not run
> `--active`** — run passive discovery and report the surface instead.

```
Authorization: cluster=<owned/lab cluster id or context>  scope=<in-scope namespaces/nodes>
               authorized-by=<name>  window=<start>..<expiry>  mode=active
```

This skill is **language-agnostic** (both tools are Go/CLI binaries + a DaemonSet — no per-stack split, per
the library's anti-triplication rule) and sits in the **Stage-1 infra-security lane**, orchestrated by the
**`infra-security-tester`** agent. It owns the **runtime + probing** surface; it does **not** score manifests
(that is `devops-k8s-security`) or scan shipped artifacts (that is `qa-security-image-infra-scan`). See the
fences below — they are the whole reason three skills exist.

> **Two spines, stated per finding.** A kube-hunter probe finding and a Falco detection map to the **MITRE
> ATT&CK Containers matrix** (technique IDs — `T1610` Deploy Container, `T1611` Escape to Host, `T1613`
> Container & Resource Discovery, `T1552.007` Container API creds) because the surface is runtime. A pure
> **config exposure** kube-hunter reports (dashboard exposed, anonymous API auth) additionally maps to
> **OWASP** (A01 Broken Access Control / A05 Misconfiguration). State both where they apply — ATT&CK for the
> runtime/probe technique, OWASP for the config exposure.

## The fences — three runtime-adjacent skills, three surfaces

| Skill | Surface | Question it answers | State |
|-------|---------|---------------------|-------|
| **`qa-security-image-infra-scan`** (Trivy) | **Static** — image layers, IaC templates, SBOM | "Is the artifact we *ship* clean?" | **Shipped** — pre-deploy |
| **`devops-k8s-security`** (kube-bench · Kubescape · Polaris) | **Static config** — manifests + cluster config vs CIS/NSA benchmark | "Is the cluster *configured* to a benchmark?" | **Declared** — posture score |
| **this skill** (kube-hunter · Falco) | **Runtime** — the *running* cluster's reachable surface + live syscall behaviour | "Is the running cluster *exploitable*, and does it *notice* when attacked?" | **Live** — actual behaviour |

- **vs `qa-security-image-infra-scan` (Trivy):** Trivy reads the image and IaC **as files, statically, before
  deploy** — CVEs in the base OS, a `USER root` in the Dockerfile, a bad Terraform setting. This skill probes
  the **running cluster** (kube-hunter) and watches **live syscalls** (Falco). A clean Trivy scan says nothing
  about a kubelet you left open on `:10250` or a pod that just spawned `/bin/bash` — **different surface**
  (runtime vs static). Run both.
- **vs `devops-k8s-security` (sibling):** that runs **CIS/benchmark/best-practice posture *scoring*** of
  manifests + cluster config (kube-bench, Kubescape, Polaris) — a *declared* state graded against a standard.
  This skill is **runtime threat detection + active exploitation probing** — kube-hunter proves the exposure
  is reachable and firing, Falco proves the cluster *detects* the attack. A field set correctly in a manifest
  (benchmark: pass) can still be exploitable at runtime, and a benchmark cannot tell you whether your
  detection fired. **Static score vs live behaviour.**
- **vs `qa-security` (app layer):** owns app-layer exploitation (BOLA/IDOR, injection, the HTTP surface). This
  skill owns the **cluster/runtime** layer beneath the app.

> **Green ≠ safe; state the handoff.** A clean kube-hunter passive run means *no exposed surface was reachable
> from where you scanned* — it says nothing about an insider with a pod, an app-layer bug (`qa-security`), or
> a CVE in the image (Trivy). A Falco rule that *deploys* is not a Falco rule that *fires* — until you assert
> it on a triggering event, you have a DaemonSet, not a detection. Every report names what it did **not**
> cover and hands it off.

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

## kube-hunter — honest status & the probe modes

> **kube-hunter is no longer under active development.** Aqua archived it and now points CVE-scanning users at
> Trivy. **It remains the reference tool for *attack-surface probing from an attacker's viewpoint*** — Trivy
> does not do the active reachability/exploit probe kube-hunter does, so it is still the right tool for this
> specific question. State this honestly to the user. **Successors / alternatives for the runtime-probe
> surface:** for enforcement-grade runtime, **Tetragon** (Cilium, in-kernel LSM block/kill) or **KubeArmor**;
> for benchmark posture, **Kubescape** (`devops-k8s-security`). Because kube-hunter is archived, **pin the
> last published image digest** and treat it as frozen — no upstream fixes are coming.

```bash
# Passive, from outside — enumerate a node's reachable surface (report-only).
kube-hunter --remote 10.0.0.5
kube-hunter --cidr 10.0.0.0/24 --quick        # cap the sweep to /24

# Passive, as an insider — what a compromised pod can reach. Run in-cluster as a Job (below).
kube-hunter --pod

# ACTIVE — attempts exploits. REQUIRES the authorization line. Owned/lab cluster only.
kube-hunter --pod --active

# Utility
kube-hunter --list                            # show every hunter/test that would run
kube-hunter --mapping                          # node network map only, no hunting
kube-hunter --pod --active --log DEBUG        # verbose, for reproducing a finding
```

| Flag | Effect |
|------|--------|
| `--remote <ip>` | Probe a specific node/API address from where the binary runs (external viewpoint) |
| `--cidr <range>` | Sweep a CIDR — pair with `--quick` to hardlimit to a /24 so you don't scan the world |
| `--interface` | Scan all local network interfaces (the node the binary runs on) |
| `--pod` | Run **as a pod inside the cluster** — the insider/compromised-pod viewpoint; enumerates SA-token, kubelet, internal API |
| `--active` | **Enable active hunting — attempts the exploit.** Disruptive. **The loud gate: authorization line required.** Default is passive |
| `--quick` | Hardlimit subnet scanning to a /24 CIDR (fast, bounded) |
| `--mapping` | Print the node network map only — no hunting |
| `--list` | List every test/hunter (dry-run of what would execute) |
| `--k8s-auto-discover-nodes` | Query the K8s API for all nodes and scan them (needs `--kubeconfig` or in-cluster SA) |
| `--service-account-token <jwt>` | Supply a bearer token explicitly instead of the mounted one |
| `--dispatch stdout\|http` | Where the report goes (`http` posts JSON to `KUBEHUNTER_HTTP_DISPATCH_URL`) |
| `--log DEBUG\|INFO\|WARNING` | Log level |

**The defining trait:** a bare `kube-hunter --pod` **only reports** — it finds the open kubelet but does not
touch it. **`--active` is what turns "there is an exposed kubelet" into "I read a secret through it"** — which
is the proof the fix is worth doing, and exactly why it needs the authorization gate.

### Running kube-hunter as an authorized in-cluster Job

The insider viewpoint (`--pod`) means running kube-hunter *inside* the cluster as a Job — deliberately, with
a scoped ServiceAccount, on an owned cluster. This is **runtime deployment, not a build gate.**

```yaml
# kube-hunter-job.yaml — the authorized insider probe. Owned/lab cluster only.
apiVersion: batch/v1
kind: Job
metadata:
  name: kube-hunter
  namespace: security-testing          # a dedicated, in-scope namespace
spec:
  backoffLimit: 0                       # a probe run should not silently retry
  template:
    spec:
      restartPolicy: Never
      # A pinned digest — kube-hunter is archived, so freeze it deliberately.
      containers:
        - name: kube-hunter
          image: aquasec/kube-hunter@sha256:<pinned-digest>
          command: ["kube-hunter"]
          args: ["--pod", "--quick"]    # add "--active" ONLY with the authorization line
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            capabilities: { drop: ["ALL"] }
      # No hostNetwork/hostPID — the probe runs as an ordinary pod, the insider it simulates.
```

```bash
kubectl apply -f kube-hunter-job.yaml
kubectl wait --for=condition=complete job/kube-hunter -n security-testing --timeout=300s
kubectl logs job/kube-hunter -n security-testing        # the findings
kubectl delete -f kube-hunter-job.yaml                  # clean up the Job when done
```

> **The active-mode escalation.** `--active` grants kube-hunter the ability to *act* on what it finds. That is
> a second, per-act decision on top of the deployment: it is on when the authorization line is present, scoped,
> and unexpired — and off otherwise. Never bake `--active` into a scheduled/recurring Job; it is a
> witnessed, one-off, authorized run.

## Falco — the blue half: detect, then ASSERT it fired

Falco (current line: **0.44.0**, May 2026 — `falco-rules 5.1.0`) runs as a **DaemonSet on every node** and
watches syscalls via **modern eBPF (CO-RE, the default driver since 0.40; the legacy eBPF probe and gVisor
were removed in 0.44)**. It ships a curated rule set and fires when a container does something a container
should not: spawns a shell, escapes to the host, reads `/etc/shadow`, opens an outbound connection to a
non-allowlisted host.

### Deploy Falco as owned infra (DaemonSet via Helm)

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

# Modern eBPF driver (no kernel headers, no privileged init container — the K8s-recommended path).
# falcosidekick fans alerts out to the telemetry backend (Loki/Alertmanager) — the blue half needs a sink.
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf \
  --set tty=true \
  --set falcosidekick.enabled=true \
  --set falcosidekick.config.loki.hostport=http://loki.observability:3100 \
  --version <pinned-chart-version>
```

- **`driver.kind=modern_ebpf`** — CO-RE eBPF, works on kernels 5.8+, needs no kernel headers or module
  compilation. The recommended K8s driver.
- **`falcosidekick.enabled=true`** — Falco's alerts must **land somewhere queryable** for the assertion step
  to work. falcosidekick forwards to **Loki / Alertmanager / others** — this is the handoff to the
  **`observability-engineer-*`** domain (see cross-refs). **No telemetry backend = no place to assert a
  detection fired** — say so honestly rather than deploying a mute detector.
- **Rules ship independently of the chart** via **falcoctl** — `falcoctl artifact install falco-rules:latest`
  pulls the latest rules without a Helm upgrade or pod restart. Pin the rules version you validated against.

### Custom rules — YAML shape

Falco rules are YAML. The engine fields (**verbatim**): `rule`, `desc`, `condition`, `output`, `priority`,
`tags`, `source`, `enabled`; plus reusable `macro` and `list` objects. **Priority levels:** `EMERGENCY`,
`ALERT`, `CRITICAL`, `ERROR`, `WARNING`, `NOTICE`, `INFORMATIONAL`, `DEBUG`.

```yaml
# custom-rules.yaml — mounted via the chart's customRules value. Tag with the ATT&CK technique.
- macro: container
  condition: (container.id != host)

- list: sensitive_host_paths
  items: ["/etc/shadow", "/etc/kubernetes/admin.conf", "/var/run/docker.sock"]

- rule: Shell spawned in container
  desc: An interactive shell was executed inside a container (T1059 — Command & Scripting).
  condition: >
    spawned_process and container
    and proc.name in (bash, sh, zsh, ash)
    and evt.type in (execve, execveat)
  output: >
    Shell in container (user=%user.name container=%container.name
    image=%container.image.repository proc=%proc.cmdline pod=%k8s.pod.name)
  priority: WARNING
  tags: [container, mitre_execution, T1059]

- rule: Read of sensitive host path
  desc: A container read a host path that should never be mounted (T1611 — Escape to Host).
  condition: >
    open_read and container and fd.name in (sensitive_host_paths)
  output: >
    Sensitive host path read (file=%fd.name container=%container.name
    image=%container.image.repository pod=%k8s.pod.name)
  priority: CRITICAL
  tags: [container, mitre_privilege_escalation, T1611]
```

> **Never edit the shipped `falco_rules.yaml`** — an upstream rules bump overwrites it. Put custom rules in a
> **separate file** (the chart's `customRules` value, or `/etc/falco/rules.d/`) so upgrades don't clobber them,
> and override a shipped rule by re-declaring the same `rule:` name in your file with a higher `priority`.

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
- This is the seam the **forthcoming `purple-team-engineer` agent + its `detection-validation` skill** own at
  scale (run every ATT&CK technique on a schedule, assert each detection still fires, catch "security drift").
  This skill does the **single-rule** version inline; name that lane as the partner.

## Trivy at runtime (brief — the boundary partner)

Trivy also has a **runtime/cluster mode** (`trivy k8s`) that scans running workloads' images and configs from
the K8s API. **That is still static scanning of what is deployed** (image CVEs, manifest misconfig read live)
— it is **not** attack-surface probing or syscall detection. It belongs to **`qa-security-image-infra-scan`**,
not here. Use `trivy k8s` to answer "what CVEs are in the images currently running"; use **kube-hunter** for
"is the running cluster reachable/exploitable" and **Falco** for "does the cluster detect an attack in
progress." Different questions — run all three; do not fold Trivy's static k8s scan into this skill.

## Anti-patterns

- **Running `--active` without the authorization line, or on someone else's cluster.** `--active` sends
  exploit attempts and can be disruptive — doing it unauthorized is not testing, it is an attack. *Fix:*
  passive discovery always; `--active` only with a recorded, scoped, unexpired authorization line against an
  owned/lab cluster; never cached, never scheduled.
- **Deploying Falco and calling the cluster "monitored."** A DaemonSet that no one has triggered a test event
  against is an unproven detector. *Fix:* validate each relied-on rule — trigger the event, assert the alert
  reached the sink; treat a non-firing rule as a detection gap.
- **Asserting only on Falco's stdout, never on the sink.** A rule that fires locally but whose alert dies
  before Loki/Alertmanager is invisible to on-call. *Fix:* assert at the sink the responder actually watches.
- **Editing the shipped `falco_rules.yaml` in place.** The next rules bump (via falcoctl or a chart upgrade)
  silently overwrites your change. *Fix:* custom rules in a separate `customRules` file / `rules.d/`; override
  by re-declaring the rule name.
- **Deploying Falco with no telemetry backend.** Alerts fire into a pod log no one reads; the assertion step
  has nowhere to query. *Fix:* wire falcosidekick → Loki/Alertmanager (the `observability-engineer-*`
  handoff) before relying on detection; if there is no backend, report "no detection surface to assert
  against" honestly.
- **Treating kube-hunter as a CVE scanner.** It is archived for that purpose and Aqua points to Trivy. *Fix:*
  use it only for attack-surface/reachability probing; use Trivy (`qa-security-image-infra-scan`) for CVEs.
- **Caching the authorization in the orientation cache.** Authorization is `#volatile` — it expires with the
  window. *Fix:* re-confirm per run; never persist it to `docs/agent-context/`.
- **Confusing this with the benchmark sibling.** Running kube-bench/Polaris and thinking you tested runtime.
  *Fix:* a benchmark grades *config*; kube-hunter probes *reachability* and Falco watches *behaviour* — run
  `devops-k8s-security` for the score, this skill for the live surface.
- **The legacy eBPF probe on Falco 0.44+.** It was removed. *Fix:* `driver.kind=modern_ebpf` (or the kernel
  module) — the modern driver is the K8s-recommended default.

## Rules (hard constraints)

- **`--active` is the loud gate.** It runs only with a recorded, target-scoped **authorization line** that
  **expires**, against a cluster **you own or a throwaway** — never a third party's, never cached (it is
  `#volatile`), never in a scheduled/recurring Job. Absent/expired authorization → run **passive** discovery
  and report the surface, do not exploit.
- **Passive kube-hunter (`--remote`/`--pod` without `--active`) and Falco deployment are report/deploy acts** —
  lower-risk, no exploit gate — but still owned-cluster-only.
- **Deploy Falco, then ASSERT it fired.** A rule is not a detection until a triggering event proves it fires
  **and reaches the sink**. A non-firing relied-on rule is a detection gap, not a pass.
- **Wire Falco to a telemetry backend** (falcosidekick → Loki/Alertmanager — the `observability-engineer-*`
  handoff) before relying on detection. No backend = report "no detection surface," do not pass silently.
- **Custom rules live in a separate file**, never edited into the shipped `falco_rules.yaml`; use
  `driver.kind=modern_ebpf` on 0.44+ (legacy eBPF/gVisor removed).
- **Two spines per finding:** runtime probe/detection → **MITRE ATT&CK Containers** technique ID; config
  exposure → **OWASP** (A01/A05) as well. Tag every custom rule with its ATT&CK technique.
- **Own the boundary:** this skill = **running-cluster probing (kube-hunter) + runtime detection (Falco)**;
  Trivy/`qa-security-image-infra-scan` = **static image/IaC**; `devops-k8s-security` = **benchmark posture
  scoring**. Run all three — orthogonal surfaces. Do not fold `trivy k8s` in here.
- **kube-hunter is archived** — say so honestly, **pin the last published image digest**, and name the
  enforcement-grade successors (Tetragon / KubeArmor) where the user needs blocking, not just detection.
- **Read-only on infra; the fix is someone else's.** This skill probes and detects; **`devops-engineer`**
  applies remediation. No secrets in scan/rule config; harvested findings redact secret contents (report the
  blast radius, never the value); nothing sensitive committed under `docs/`.
- A clean run ≠ "secure" — it means the **runtime probe found no reachable surface / the detection fired**.
  Run the full infra lane (`infra-security-tester`) + the app lane (`qa-security`).

## Cross-references

- **`infra-security-tester`** (`devops/agents/infra-security-tester.md`) — the phased orchestrator that runs
  this skill in its **K8s & runtime** phase; owns the scope/authorization gate this skill enforces.
- **`devops-k8s-security`** (sibling, Stage 1) — CIS/NSA **benchmark posture scoring** of manifests + cluster
  config (kube-bench · Kubescape · Polaris). The static-config sibling: it grades the *declared* state; this
  skill probes the *running* one. Run both.
- **`qa-security-image-infra-scan`** (Trivy) — **static** image/IaC/SBOM scanning of the shipped artifact,
  incl. `trivy k8s`. The static-vs-runtime boundary partner: it owns everything read as a file; this skill
  owns the live cluster. Run both.
- **`devops-iac-security`** · **`devops-cloud-posture`** · **`devops-supply-chain-security`** ·
  **`devops-threat-modeling`** · **`devops-infra-controls-validation`** (Stage-1 siblings) — the rest of the
  infra-security lane; `threat-modeling` feeds the scope this skill probes within.
- **`observability-engineer-{dotnet,java,node}`** + `observability/{queries,dashboards}` — **where Falco
  alerts land.** The blue half needs a telemetry backend (Loki/Alertmanager) to assert against; wire
  falcosidekick to their stack. No backend = no detection surface.
- **`purple-team-engineer`** + **`detection-validation`** (*forthcoming*, Stage 4) — the **detection-assertion
  partner** at scale: run every ATT&CK technique on a schedule and assert each detection still fires. This
  skill does the single-rule inline version and hands the continuous version to that lane.
- **`qa-security`** (`qa/_shared/agents/qa-security.md`) — the **app-layer** security lane beneath which this
  cluster/runtime layer sits; orthogonal surface.
- **`devops-engineer`** — applies the remediation for every finding this skill reports (the standard
  auditor↔engineer handshake); this skill is read-only on infrastructure.
- Deep dives: **`references/kube-hunter.md`** (full probe-mode + Job + active-gate reference) ·
  **`references/falco.md`** (deployment, rule authoring, detection-validation recipes).
