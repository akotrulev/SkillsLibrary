---
name: chaos-experiments
description: Use when running cluster or cloud chaos (Chaos Mesh, Litmus, AWS FIS, Chaos Studio) with SLO steady state and aborts. Triggers "run a chaos experiment". Not for Toxiproxy (failure-injection-testing).
---

# QA — Chaos Experiments (Shared)

An environment-level chaos experiment breaks part of a **running deployment** — kills pods, adds network latency
between services, stresses a node, stops a managed resource — and checks a written hypothesis against the
service's real telemetry. It answers a different question from the in-process fault-injection tests in
`qa/<stack>/skills/failure-injection-testing`:

| | `failure-injection-testing` (per lane) | `chaos-experiments` (this skill) | `security/cloud-incident-response` (`references/cloud-resilience.md`) |
|---|---|---|---|
| Where the fault lands | A Toxiproxy between the app and one Testcontainers dependency | A deployed environment: pods, nodes, network, managed cloud resources | A whole region, account or backup chain |
| Asserted by | The test runner (NUnit / TestNG / Vitest) on the app's resilience code | Prometheus SLO queries, before / during / after | Measured RTO / RPO against the agreed target |
| Runs | Every CI build, deterministic | Scheduled, time-boxed, with an owner watching | A declared DR drill or game day |
| Question | "Does my retry / breaker / timeout code do its job?" | "Does the system hold its SLO when this part fails?" | "Can we recover the business inside RTO / RPO?" |

If the request is "prove the circuit breaker opens", that is the per-lane skill. If it is "fail over the region",
that is the DR drill. Everything between — "what happens to checkout when one of three `payments` pods dies" — is here.

## When to use

- Design, run or review a chaos experiment against a Kubernetes cluster, AWS or Azure environment
- Write the steady-state hypothesis and abort conditions as Prometheus queries
- Choose between Chaos Mesh, LitmusChaos, AWS FIS and Azure Chaos Studio
- Write up an experiment's record and its follow-ups

## When NOT to use

- A deterministic fault in a test → `qa-<stack>:failure-injection-testing`
- Load generation or SLO thresholds for a load test → `performance-foundations` (`qa/_shared/performance`); a chaos
  experiment may run *under* a smoke-level load from that skill, never a stress test
- Region failover, backup restore, ransomware recovery drills → `security/cloud-incident-response`
- Writing the SLO itself → `qa/manual/quality-metrics`; PromQL idioms → `observability/queries`

## Hard rules

1. **Never in production without an approved, reversible plan.** Production needs: a written experiment record
   (below) approved by the service owner and the on-call lead; the same experiment already run clean in a
   non-production environment; a tested abort that restores the fault in under a minute; a time box; a named
   person watching the dashboards for the whole run; and a window outside peak and outside a release freeze.
   Missing any one, the answer is "not in production" — run it in staging.
2. **Non-production first, always.** The order is a scratch namespace → staging (sized like production) →
   production. An experiment moves up only after a clean run at the level below.
3. **No hypothesis, no experiment.** A fault with no written expected outcome is an outage you caused, not a test.
4. **Every experiment has an automatic abort and a time box.** The abort reads the same SLO queries as the
   hypothesis. The time box is the tool's own `duration`, never "until someone stops it".
5. **The fault is reversible by the tool.** Prefer faults the tool removes on stop (latency, stress, pod-failure)
   over ones it cannot undo (deleting data, rotating a key). A one-way fault needs its manual restore step
   written and rehearsed before the run.

## Procedure

1. **Steady state.** Pick the service and the 2–4 SLIs a user would notice (availability, p95 latency of the
   critical route, queue age, error ratio). Write each as a Prometheus query with its SLO threshold. Run them for
   the last hour and the same hour last week: if steady state is not met *before* the fault, stop — the experiment
   cannot tell you anything.
2. **Hypothesis.** One sentence per SLI, in the form *"When <fault> on <blast radius> for <duration>, <SLI query>
   stays <comparator> <threshold>, and recovers to steady state within <recovery budget> after the fault ends."*
3. **Blast radius.** One service, the smallest share of its replicas that tests the hypothesis (one pod, or a
   percentage), one namespace, one environment. Write the radius as tool configuration, not intent (*Blast-radius
   controls* below).
4. **Abort conditions.** For each SLI a second, *worse* threshold that ends the run early (the SLO is the
   hypothesis; the abort is the point past which users are hurt). Wire it to the tool's native stop mechanism
   (*Tool choice* below). Test the abort once before the real run: trip it with a deliberately tight threshold.
5. **Method.** The fault, its parameters, the tool manifest or template, the start time and the duration. Run
   under representative traffic: the real traffic of the environment, or a smoke-level load from
   `performance-foundations`.
6. **Run and observe.** Evaluate the SLI queries **before** (steady state), **during** (hypothesis and abort), and
   **after** (recovery). Record the query results with timestamps and a dashboard link for the run window.
7. **Record and follow up.** Fill the experiment record (`references/experiment-record.md`). A disproved hypothesis
   becomes a bug (`qa/manual/bug-report-writer`) with the record attached, and a per-lane
   `failure-injection-testing` test where the gap is in one service's resilience code.

## Steady state and aborts as Prometheus queries

The metric names follow the OpenTelemetry HTTP semantic conventions as exported to Prometheus
(`observability/queries`); use the project's real names.

```promql
# SLI 1 — error ratio of checkout over the last minute (SLO: < 0.1 %, abort: > 2 %)
sum(rate(http_server_request_duration_seconds_count{service="checkout", http_response_status_code=~"5.."}[1m]))
/
sum(rate(http_server_request_duration_seconds_count{service="checkout"}[1m]))

# SLI 2 — p95 latency of the critical route (SLO: < 0.300 s, abort: > 1.5 s)
histogram_quantile(0.95,
  sum by (le) (rate(http_server_request_duration_seconds_bucket{service="checkout", http_route="/api/checkout"}[1m])))

# SLI 3 — the fault took effect (expected: ready replicas = desired − 1 during a one-pod pod-failure)
kube_deployment_status_replicas_available{namespace="shop", deployment="payments"}
```

- A **short window** (`[1m]`) for during-run checks, so the abort reacts in time; the steady-state baseline uses
  the SLO's own window.
- Always include a query that proves **the fault landed** (SLI 3). An experiment whose fault never took effect
  "passes" every hypothesis.
- `kube_deployment_status_replicas_available` comes from kube-state-metrics; check it is scraped.

## Blast-radius controls

| Control | Chaos Mesh | LitmusChaos | AWS FIS | Azure Chaos Studio |
|---|---|---|---|---|
| One service | `selector.labelSelectors` + `selector.namespaces` | `appinfo.applabel` + `appinfo.appns` | Target `resourceTags`, `filters`, or `aws:eks:pod` `parameters` | The experiment's `selectors` (resource list or query) |
| Share of replicas | `mode: one` · `fixed` · `fixed-percent` · `random-max-percent` + `value` | `PODS_AFFECTED_PERC` / `TARGET_PODS` | `selectionMode: COUNT(n)` · `PERCENT(n)` | The fault's own parameters (the Chaos Mesh `jsonSpec` for AKS) |
| Time box | `duration` | `TOTAL_CHAOS_DURATION` (seconds) | Action `duration` (ISO 8601, `PT5M`) | Step / branch action `duration` |
| Namespace opt-in | Helm `controllerManager.enableFilterNamespace=true` + `chaos-mesh.org/inject=enabled` on each allowed namespace | A namespace-scoped service account (`chaosServiceAccount`) | IAM role scoped to the targets | Only resources onboarded as Chaos Studio targets can be faulted |

Enable the namespace opt-in on every cluster that also runs anything you are not testing: it turns "a typo in the
selector" from an outage into a no-op.

## Tool choice

| Environment | Default tool | Native abort wired to SLO queries |
|---|---|---|
| Any Kubernetes cluster, in-cluster faults | **Chaos Mesh** | Workflow `StatusCheck` with `abortWithStatusCheck: true` — its HTTP criteria match a **status code** only, so it watches a health endpoint; a Prometheus breach needs the guard (`references/tools.md` §5) |
| Kubernetes, where probes in the experiment definition are wanted | **LitmusChaos** | A `promProbe` in `Continuous` mode with `stopOnFailure: true` reads the PromQL directly |
| AWS (EC2, ECS, EKS, RDS, …) | **AWS FIS** | `stopConditions` on a CloudWatch alarm — mirror the abort SLI as an alarm, or run the guard calling `aws fis stop-experiment` |
| Azure (VMs, AKS via Chaos Mesh, Cosmos DB, Key Vault, …) | **Azure Chaos Studio** | No documented metric stop condition on classic experiments — run the guard calling the experiment's `/cancel` endpoint |

Pick the one tool that already reaches the target: an EKS cluster with Chaos Mesh installed runs pod faults in
Chaos Mesh, and FIS only for AWS-level faults (an AZ's subnets, an RDS failover). One experiment uses one tool.

Manifests, templates and the guard are in **`references/tools.md`**. Read it end to end before writing one.

## Output

Every run produces one record from `references/experiment-record.md`, saved where the project keeps test
evidence (default `docs/chaos/<NNN>-<service>-<fault>.md`), with: the hypothesis, method, blast radius, abort, the
before / during / after query results, the verdict (`HELD` · `DISPROVED` · `ABORTED` · `INCONCLUSIVE`), and the
follow-ups with owners. A run with no record did not happen.

## Review checklist

Report findings in the library's review table; point to the fix.

- **blocker** — a production run without an approved record, a non-production clean run, a tested abort or a
  time box; a fault with no automatic abort; a selector that can match more than the named service.
- **major** — no query proving the fault landed; the steady state not checked before the run; an abort
  threshold equal to the SLO (it aborts every run) or absent; a one-way fault with no rehearsed restore; a stress
  load run alongside the fault (two variables at once).
- **minor** — no recovery budget; no dashboard link for the run window; follow-ups with no owner.

## Handoffs

- In-test fault injection → `qa-dotnet:failure-injection-testing`, `qa-java:failure-injection-testing`, `qa-typescript:failure-injection-testing`
- Background load during the run → `qa/_shared/performance` and the lane's `load-testing`
- SLO definitions → `qa/manual/quality-metrics`; PromQL → `observability/queries`; dashboards → `observability/dashboards`
- DR drills and region failover → `security/cloud-incident-response` (`references/cloud-resilience.md`)
- A disproved hypothesis → `qa/manual/bug-report-writer`
