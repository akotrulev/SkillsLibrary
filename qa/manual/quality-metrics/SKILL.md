---
name: qa-quality-metrics
description: Use when the user asks how to measure QA effectiveness or delivery quality — DORA metrics, defect escape rate, flake rate, MTTR, SLOs / SLIs, coverage as a signal (not a target). Triggers: "measure QA effectiveness", "DORA metrics", "track flaky tests".
---

# QA — Quality Metrics

Names the metrics worth tracking, defines each precisely, and prescribes a dashboard / alerting shape that turns them into decisions. The framing: **measure outcomes (delivery + reliability), use coverage and flake as diagnostic signals, never as goals**.

## When to use

- Setting up the team's quality dashboard for the first time
- Auditing existing metrics — which are useful, which are vanity
- Designing SLOs / SLIs for a service
- Diagnosing why "tests are green but bugs keep escaping"
- Reporting quality to leadership

## When NOT to use

- Writing tests → `qa/<topic>` generators
- Strategy / what-to-test → `qa/manual/test-strategy`
- Building the panels themselves → `observability/dashboards`
- LogQL / PromQL syntax for the queries → `observability/queries`
- Stakeholder narrative around metrics → `communication/stakeholder-updates`

## The metric pyramid

| Tier | Question | Examples |
|---|---|---|
| **Outcomes** | Are we delivering quality? | DORA, escape rate, MTTR, SLO attainment |
| **Symptoms** | Where is quality leaking? | Bug counts by severity, alert volume, on-call pages |
| **Diagnostics** | Why are we leaking quality? | Test coverage, flake rate, CI duration, review latency |

**Always start at the top**. A team obsessed with diagnostics (coverage %) and indifferent to outcomes (escape rate) ships bugs with great metrics.

## DORA — the four

The Accelerate / DORA metrics remain the best single set for delivery health:

| Metric | Definition | Target tiers (rough) |
|---|---|---|
| **Deployment frequency** | How often we ship to prod | Daily+ = elite, weekly = high, monthly = medium |
| **Lead time for changes** | Commit → prod | < 1 day = elite, 1d–1w = high, 1w–1m = medium |
| **Change failure rate** | % of deploys causing incident / rollback / hotfix | < 5% = elite, 5–10% = high |
| **Mean time to restore** (MTTR) | Incident detected → resolved | < 1 hour = elite, hours = high |

How we instrument these:

- **Deployment frequency**: count successful prod deploys per service per week — `record-deployment` (Pact) or pipeline annotations
- **Lead time**: first commit on the PR branch → prod deploy timestamp — joined via Git + deploy log
- **Change failure rate**: # deploys followed by an incident / rollback within 24h ÷ total deploys
- **MTTR**: incident open → resolved (from incident tool: PagerDuty, Opsgenie, Statuspage)

DORA's the only quality metric that survives leadership scrutiny across years. Get it on the dashboard first.

## SLOs / SLIs

For each user-facing service, define a small number of **SLIs** (Service Level Indicators — measurable proxies for what users feel) and **SLOs** (targets on those indicators over a window):

| Service | SLI | SLO |
|---|---|---|
| Orders API | % requests returning 2xx/3xx | 99.9% over 30 days |
| Orders API | % requests with p95 latency ≤ 300ms | 99% over 30 days |
| Checkout flow | % completed checkouts that don't error in the next 1h | 99.5% over 30 days |
| Background worker | % jobs completed in ≤ 5 min | 99% over 30 days |

Each SLO has an **error budget** (1 − SLO over the window). Burn-rate alerts fire when the budget consumes faster than expected (see `observability/queries` for burn-rate query recipes).

Rules:
- Pick **SLIs that reflect user pain**, not internal mechanics. "Request error rate < X" is user-pain; "GC pause < Y" is mechanics.
- **3–5 SLIs per service** max. More dilutes attention.
- **One SLO per SLI**. Avoid layered "perfect / good / acceptable" targets — too much room to debate.

## Quality outcome metrics (the symptoms layer)

| Metric | Definition | Signal |
|---|---|---|
| **Defect escape rate** | Bugs found in prod ÷ (bugs found in prod + bugs found in test) | Rises = testing is under-covering reality |
| **Critical / blocker bug count (open + new)** | Self-explanatory; track open over time | Rising open = pipeline shipping; rising new = quality slipping |
| **Mean time to detect** (MTTD) | Issue starts in prod → first alert / report | Long = observability gap |
| **Hotfix rate** | Hotfix deploys ÷ regular deploys | Rising = release process or pre-prod gates failing |
| **Time-to-merge a fix** | Bug discovered → fix in prod | Long for a `blocker` = bigger problem than the bug |

Compute weekly, plot over rolling 12 weeks. **Trends matter more than absolute values.**

## Diagnostic metrics

These are useful as **signals**, never as goals:

| Metric | What it tells you | Pitfall as a goal |
|---|---|---|
| **Test coverage %** | Lines exercised by tests; a *floor* on tested area | Game-able with assert-less tests; high coverage ≠ tested behavior |
| **Branch coverage on new code** | More useful than line coverage | Still game-able |
| **Test flake rate** | Tests that pass sometimes and fail sometimes on `main` | "Reduce flakes" can mean "delete flaky tests"; require root-cause fixes |
| **Mean test duration** | How long the suite takes | Optimizing this can mean dropping slow valuable tests |
| **CI duration p95** | PR feedback time | Pressure to skip checks |
| **PR review latency** | Time to first review + time to merge | Pressure to merge without thoughtful review |
| **Change-failure linked to test gap** | When a regression escaped, did a test exist for that path? | Requires post-incident discipline |

**Coverage rule of thumb:** track it, alert on regression on *changed lines*, never set a global percentage target. 80% coverage of trivial getters is worse than 60% coverage of real behavior.

**Flake rule of thumb:** every flaky test gets a root-cause fix or a deletion with explicit retire-reason. "Quarantine indefinitely" is a graveyard, not a strategy.

## Vanity / harmful metrics (avoid)

- **Number of test cases written** — incentivizes test count over test value
- **Bug count "closed"** (as a goal) — incentivizes closing dupes / "won't fix"
- **Test execution count** — re-running the same test 1000 times = "1000 tests run"
- **Coverage % as a hard floor for PR merge** — produces meaningless tests
- **"Zero bugs"** — the only project with zero bugs is the project with no users

Drop these from dashboards; they survive in many corporate templates and actively make decisions worse.

## Dashboard shape

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ DORA header: deploys / week, lead time p50, change failure % 30d, MTTR p50  │
├─────────────────────────────────────────────────────────────────────────────┤
│ SLO row per service: error budget remaining % + burn rate                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Quality outcomes (12w trend): escape rate, open blocker/critical, hotfix %  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Diagnostics: flake rate, coverage on changed lines, CI p95, review latency   │
└─────────────────────────────────────────────────────────────────────────────┘
```

Build with `observability/dashboards` patterns. Use the **trend** view as the primary lens — week-over-week change beats absolute values for decisions.

## Per-stack instrumentation pointers

| Metric | Source |
|---|---|
| Deploys | pipeline → annotation in Grafana / Statuspage |
| Lead time | Git provider API + deploy log |
| Change failure | Incident system + pipeline deploy log |
| MTTR / MTTD | Incident system (PagerDuty / Opsgenie) |
| Escape rate | Bug tracker labels (`found-in: prod` vs `found-in: test`) |
| Flake rate | Test runner with retries enabled — count tests that pass on retry, alert when flake-rate > X% |
| Coverage on changed lines | Codecov / Coveralls / built-in (`dotnet test --collect:"XPlat Code Coverage"`, JaCoCo, c8) configured per PR |
| CI duration | Pipeline metrics endpoint or annotation |
| Review latency | Git provider API |

## Reporting cadence

| Audience | Cadence | Surface |
|---|---|---|
| Engineers / squad | Daily-ish glance + per-PR feedback | Grafana dashboard + PR comments |
| Engineering leadership | Weekly trend review | DORA / SLO summary + top regressions |
| Product / stakeholders | Bi-weekly or monthly | DORA-on-one-slide + SLO attainment + open critical bugs (see `communication/stakeholder-updates`) |
| Executives | Quarterly | Year-trend on DORA + outcomes; no diagnostics |

## Rules

- DORA + SLOs as the headline metrics
- Quality outcomes (escape, hotfix, MTTD) as the middle layer
- Diagnostics (coverage, flake, CI duration) as signals, not goals
- Every flaky test gets a root-cause fix or a retire-reason; no indefinite quarantine
- Coverage tracked on **changed lines**, not global
- SLOs per service, ≤ 5; aligned with user pain
- Burn-rate alerts on SLOs (multi-window) — see `observability/queries`
- Trend lens dominates absolute values
- Dashboards built from outcome-down, not metric-up
- Vanity metrics dropped from dashboards

## What NOT to do

- No global coverage % as a hard PR gate
- No "number of tests written" reward
- No "zero bugs" target
- No closing duplicates / wontfixes to game bug count
- No SLO at 100% (you can't deploy)
- No "more is better" dashboards (60 panels nobody reads)
- No bug-tracker label drift between teams (`found-in: prod` vs `escaped: yes` vs `prod-incident: true`) — unify across teams
- No flake quarantine list with no retirement criteria
- No metric without a dashboard owner
- No quality report to leadership that's a screenshot dump — name the trend and the action

## Generation steps

1. Confirm services in scope and the incident / Git / bug-tracker tools
2. Define DORA pipeline: deploys, lead time, change failure, MTTR
3. Define 3–5 SLIs + SLOs per service with the team
4. Pick the quality outcomes (escape, hotfix, MTTD) and label conventions in the bug tracker
5. Pick the diagnostics (flake, coverage on changed lines, CI p95) and instrument
6. Build the dashboard via `observability/dashboards` (or extend the existing one)
7. Add burn-rate alerts on the SLOs
8. Establish the reporting cadence; align to `communication/stakeholder-updates`
9. Iterate after one release; drop metrics that didn't drive a decision

## Handoffs

- Dashboards → `observability/dashboards`
- Queries → `observability/queries`
- Test strategy that the metrics inform → `qa/manual/test-strategy`
- Stakeholder narrative → `communication/stakeholder-updates`
- SLO-tied alerts (Prometheus rules) → `observability/queries`
