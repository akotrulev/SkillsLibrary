# Falco — runtime threat detection + detection validation (deep dive)

The blue half of `devops:container-runtime-security`: an eBPF DaemonSet that watches kernel syscalls on every
node and fires the moment a container misbehaves — **then the discipline of asserting the rule actually
fired.** This file is the full deployment / rule-authoring / validation reference; the SKILL.md holds the
decision matrix.

> **Current line: Falco 0.44.0 (May 2026), `falco-rules 5.1.0`.** 0.44 **removed** the legacy eBPF probe, the
> gVisor engine, and the gRPC output/server (deprecation cycle started in 0.42). Use **modern eBPF** (default
> driver since 0.40) or the kernel module; migrate any gRPC output to **HTTP output / falcosidekick**. Pin the
> chart and rules versions you validate against.

## Why Falco, and its one honest limit

Falco is **CNCF-graduated**, the mature default for runtime **detection & alerting**, with a large
falcosidekick integration ecosystem. Its limit: **it is detection-only** — it emits an alert, it does not
block. When you need **in-kernel enforcement** (terminate the offending process, override the syscall), reach
for **Tetragon** (Cilium, LSM hooks) or **KubeArmor**. For this skill's question — *does the cluster notice
when attacked* — detection is the right tool; note the enforcement handoff where the user needs blocking.

## Deploy as owned infra (DaemonSet via Helm)

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf \                         # CO-RE eBPF; no kernel headers, no module build
  --set tty=true \                                        # unbuffered output, for timely alerts
  --set falcosidekick.enabled=true \                      # fan alerts to the telemetry backend
  --set falcosidekick.config.loki.hostport=http://loki.observability:3100 \
  --version <pinned-chart-version>
```

- **`driver.kind=modern_ebpf`** — the K8s-recommended driver: works on kernels 5.8+, no privileged init
  container compiling a module. (The legacy eBPF probe is gone in 0.44.)
- **`falcosidekick.enabled=true`** — the **load-bearing** flag for this skill. Falco's alerts must land in a
  **queryable sink** so the validation step can assert them. falcosidekick forwards to **Loki / Alertmanager /
  Slack / many more** — this is the handoff to the **`observability-engineer-*`** domain. **No sink = no place
  to assert a detection fired.**

### Rule delivery via falcoctl (decoupled from the chart)

Rules ship **independently** of the Falco binary/chart, managed by **falcoctl**:

```bash
falcoctl artifact install falco-rules:latest       # pull latest rules, no Helm upgrade / pod restart
falcoctl artifact list                             # what's installed
falcoctl index update                              # refresh the artifact index
```

Pin the rules version you validated against — a silent rules bump can change what fires (or stops firing).
`falcoctl`'s `tls` subcommand and legacy-probe references were removed in the 0.44 line.

## Custom rules — YAML shape

Rules are YAML objects. Engine fields (**verbatim**): `rule`, `desc`, `condition`, `output`, `priority`,
`tags`, `source`, `enabled`; plus reusable `macro` and `list`. Also `required_engine_version` and
`required_plugin_versions` at the file top when a rule needs a minimum engine/plugin.

**Priority levels** (highest → lowest): `EMERGENCY`, `ALERT`, `CRITICAL`, `ERROR`, `WARNING`, `NOTICE`,
`INFORMATIONAL`, `DEBUG`. Conventions: file modification → `ERROR`; unauthorized read → `WARNING`; unexpected
behaviour → `NOTICE`; poor practice → `INFORMATIONAL`.

Output fields interpolate with `%` (`%container.name`, `%proc.cmdline`, `%k8s.pod.name`, `%fd.name`,
`%user.name`); an unset field renders `<NA>`. **Macros/lists must be defined before they are referenced**
within the same kind (macro→macro, list→list); a rule may reference any macro, a macro any list, regardless
of order.

```yaml
# custom-rules.yaml — mounted via the chart's customRules value. Tag every rule with its ATT&CK technique.
- required_engine_version: 0.44.0

- macro: container
  condition: (container.id != host)

- macro: spawned_process
  condition: (evt.type in (execve, execveat) and evt.dir=<)

- list: sensitive_host_paths
  items: ["/etc/shadow", "/etc/kubernetes/admin.conf", "/var/run/docker.sock", "/root/.ssh"]

- rule: Shell spawned in container
  desc: An interactive shell was executed inside a container (T1059 — Command & Scripting Interpreter).
  condition: >
    spawned_process and container
    and proc.name in (bash, sh, zsh, ash, dash)
  output: >
    Shell in container (user=%user.name container=%container.name
    image=%container.image.repository proc=%proc.cmdline pod=%k8s.pod.name ns=%k8s.ns.name)
  priority: WARNING
  tags: [container, shell, mitre_execution, T1059]

- rule: Read of sensitive host path
  desc: A container read a host path that should never be mounted (T1611 — Escape to Host).
  condition: >
    open_read and container and fd.name in (sensitive_host_paths)
  output: >
    Sensitive host path read (file=%fd.name container=%container.name
    image=%container.image.repository pod=%k8s.pod.name)
  priority: CRITICAL
  tags: [container, filesystem, mitre_privilege_escalation, T1611]

- rule: Outbound connection to non-allowlisted host
  desc: A container opened an unexpected outbound connection (T1071 — Application Layer Protocol / C2).
  condition: >
    outbound and container
    and not fd.sip in (allowed_egress_ips)
  output: >
    Unexpected egress (conn=%fd.name container=%container.name pod=%k8s.pod.name)
  priority: NOTICE
  tags: [network, mitre_command_and_control, T1071]
```

> **Never edit the shipped `falco_rules.yaml`.** A falcoctl/chart rules bump overwrites it. Put custom rules in
> a **separate file** (the chart's `customRules` value, or a file under `/etc/falco/rules.d/`). To override a
> shipped rule, re-declare the same `rule:` name in your file — the last definition wins; raise the `priority`
> or tighten the `condition` there.

### ATT&CK Containers mapping — tag the rule with the technique

| Behaviour the rule watches | ATT&CK (Containers) technique |
|---|---|
| Shell / interpreter spawned in a container | `T1059` Command & Scripting Interpreter |
| Read of sensitive host path / mounted socket | `T1611` Escape to Host |
| New privileged / hostPath pod created | `T1610` Deploy Container |
| Service-account token / secret file read | `T1552.007` Credentials in Container API |
| Namespace/resource enumeration from a pod | `T1613` Container & Resource Discovery |
| Unexpected outbound connection (C2) | `T1071` Application Layer Protocol |

## Detection validation — the step that makes it real

**A deployed rule is not a detection until a triggering event proves it fires and reaches the sink.** This is
the discipline separating a real blue capability from a checkbox. For each rule you rely on:

```bash
# --- Rule: "Shell spawned in container" (T1059) ---

# 1. TRIGGER — do the exact thing the condition watches for, on an authorized target.
kubectl run canary --image=busybox --restart=Never -n security-testing -- sleep 3600
kubectl exec -it canary -n security-testing -- /bin/sh -c "echo triggered"

# 2. ASSERT it fired locally — Falco's own output.
kubectl logs -l app.kubernetes.io/name=falco -n falco --since=1m | grep "Shell in container"

# 3. ASSERT it reached the SINK — the alert an on-call would actually see (Loki via falcosidekick).
logcli query '{app="falcosidekick"} |= "Shell in container"' --since=2m     # gate: >=1 hit
# (Alertmanager sink instead: query the Alertmanager API for an active alert with the rule's label.)

# 4. CLEAN UP the canary.
kubectl delete pod canary -n security-testing
```

- **Binary per ATT&CK technique:** did the `T1059` rule fire on the triggering event — yes/no. A "no" is a
  **detection gap**, reported as such. Diagnose it: rule disabled, `condition` too narrow, driver not loaded
  on that node, or the sink hop broken.
- **Assert at the sink, not only Falco stdout.** A rule that fires locally but whose alert never reaches
  Loki/Alertmanager is invisible to the responder — the detection is only as real as its last hop.
- **This is the single-rule version.** The **`purple-team-engineer` agent + its `detection-validation`
  skill** own the continuous version — run every ATT&CK technique on a schedule (Atomic Red Team / Caldera),
  assert each detection still fires, catch "security drift." Name that lane as the partner and hand the
  scheduled form to it.

## Where alerts land — the observability handoff

The blue half is only useful if alerts reach a place humans watch. falcosidekick is the fan-out:

- **Loki** — Falco alerts as queryable logs (the validation step's `logcli` target). Configure with
  `falcosidekick.config.loki.hostport`.
- **Alertmanager** — page on `CRITICAL`/`ERROR` priority; `customseveritymap` maps Falco priority → AM
  severity.
- **Prometheus** — falcosidekick exposes metrics (alert counts by rule/priority) for dashboards and SLOs.

This is the **`observability-engineer-{dotnet,java,node}`** + `observability/{queries,dashboards}` domain.
**Gate the validation step on a backend being present** — if there is none, report *"no detection surface to
assert against"* honestly rather than deploying a mute detector and calling the cluster monitored.

## Tuning to keep the gate trustworthy

- **False positives train people to mute the gate** — the same failure mode as an over-broad Trivy gate. Tune
  noisy rules with `exceptions` (per-rule allowlists) or a tightened `condition`, not by disabling the rule.
- **Start with the shipped rule set**, add custom rules for your threat model, and validate each before you
  rely on it. A rule you have never triggered is a rule you do not know works.
- **Version-pin rules** (falcoctl) so a silent bump does not change what fires under you; re-validate after a
  deliberate bump.

## The report — required elements

- **What was deployed** (Falco version, driver, chart/rules versions, sink).
- **Per-rule validation table:** rule → ATT&CK technique → triggered? → fired locally? → reached sink? — a
  "no" anywhere is a detection gap.
- **Detection gaps** as findings, with the diagnosis and the fix direction (owner: **`devops-engineer`** for
  infra wiring; the rule author for `condition` fixes).
- **Handoff:** enforcement (blocking) → Tetragon/KubeArmor; continuous validation → `purple-team-engineer`;
  where alerts land → `observability-engineer-*`. Falco detects; it does not block or fix.
