# Chaos experiment record — template and worked example

One record per run. Fill it **before** the run down to *Approval*; fill *Result* and *Follow-ups* after. Save it
where the project keeps test evidence (default `docs/chaos/<NNN>-<service>-<fault>.md`).

## Template

```markdown
# <NNN> — <service>: <fault> (<environment>)

**Date:** <YYYY-MM-DD> · **Owner:** <name> · **Observer on dashboards:** <name> · **Status:** planned | run

## Steady state
| SLI | Query | SLO | Value before the run (window) |
|---|---|---|---|
| <name> | `<PromQL>` | <comparator threshold> | <value> (<from>–<to> UTC) |
| Fault landed | `<PromQL>` | <expected during the fault> | <value> |

## Hypothesis
When <fault> on <blast radius> for <duration>, <SLI> stays <comparator> <threshold>, and every SLI is back to
steady state within <recovery budget> after the fault ends.

## Method
- **Tool and version:** <Chaos Mesh 2.x | LitmusChaos 3.x | AWS FIS | Azure Chaos Studio>
- **Fault:** <kind / action / URN> with <parameters>
- **Blast radius:** <namespace>, <selector>, <mode/selectionMode + value>; namespace opt-in <on | n/a>
- **Time box:** <duration>
- **Traffic during the run:** <real environment traffic | smoke load from performance-foundations, N RPS>
- **Manifest / template:** <path in repo>

## Abort
| SLI | Abort when | Wired to | Abort tested on <date> by tripping it with <threshold> |
|---|---|---|---|
| <name> | <comparator threshold> | <promProbe stopOnFailure | StatusCheck abortWithStatusCheck | FIS stop condition alarm | guard script> | <yes / no> |

Manual stop: `<the exact command>`. One-way effects and their restore: <none | step, rehearsed on date>.

## Approval (production only)
Service owner: <name, date> · On-call lead: <name, date> · Clean non-production run: <record id> · Window: <from–to, outside peak and freeze>

## Result
| SLI | Before | During (worst) | After (recovered at) | Hypothesis |
|---|---|---|---|---|
| <name> | <value> | <value at time> | <value at time> | held | disproved |

**Verdict:** HELD | DISPROVED | ABORTED (<which abort, when>) | INCONCLUSIVE (<why: fault did not land, steady state not met>)
**Evidence:** dashboard link for <from–to>, guard log, tool status output, events (`kubectl get events` / FIS experiment log)

## Follow-ups
| # | Finding | Action | Owner | Tracked in |
|---|---|---|---|---|
| 1 | <what the run showed> | <fix, test, runbook change> | <name> | <issue id> |
```

## Worked example (abridged)

```markdown
# 004 — payments: one pod unavailable (staging)

## Steady state
| SLI | Query | SLO | Value before the run |
|---|---|---|---|
| Checkout error ratio | `sum(rate(http_server_request_duration_seconds_count{service="checkout",http_response_status_code=~"5.."}[1m])) / sum(rate(http_server_request_duration_seconds_count{service="checkout"}[1m]))` | < 0.001 | 0.0002 (10:00–11:00 UTC) |
| Checkout p95 | `histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{service="checkout",http_route="/api/checkout"}[1m])))` | < 0.300 s | 0.180 s |
| Fault landed | `kube_deployment_status_replicas_available{namespace="shop",deployment="payments"}` | 2 of 3 during the fault | 3 |

## Hypothesis
When one of three payments pods is unavailable for 5 minutes, the checkout error ratio stays below 0.1 % and p95
below 300 ms, and both are back to steady state within 2 minutes after the fault ends.

## Abort
Error ratio > 2 % or p95 > 1.5 s for three consecutive probe intervals → LitmusChaos `promProbe`, `Continuous`,
`stopOnFailure: true`. Tested 2026-11-10 with a 0.0001 threshold: the run stopped in 15 s.

## Result
| SLI | Before | During (worst) | After | Hypothesis |
|---|---|---|---|---|
| Error ratio | 0.0002 | 0.0140 at 11:02:30 | 0.0002 at 11:06:10 | disproved |
| p95 | 0.180 s | 0.410 s | 0.185 s | disproved |
| Fault landed | 3 | 2 | 3 | — |

**Verdict:** DISPROVED. In-flight requests to the failed pod were not retried: the checkout client retries only on
connection errors, not on `503` from the service mesh.

## Follow-ups
| # | Finding | Action | Owner | Tracked in |
|---|---|---|---|---|
| 1 | No retry on a 503 from a draining pod | Add an idempotent retry on 503 for `POST /payments/authorize` with an idempotency key | payments team | PAY-812 |
| 2 | The gap is not pinned by any test | A `failure-injection-testing` test: upstream returns 503 once, the call succeeds | QA | PAY-813 |
```
