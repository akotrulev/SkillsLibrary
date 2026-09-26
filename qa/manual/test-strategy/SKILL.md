---
name: qa-test-strategy
description: Use when the user asks for help building a test strategy, risk-based test plan, coverage matrix, test-pyramid sizing, or release quality gates. Triggers: "build a test strategy for X", "what tests should we have for this release", "risk-based plan for the migration". Not for one feature's test plan (test-plan-writer) or step-by-step cases (test-case-writer).
---

# QA — Test Strategy

Produces a stack-agnostic test strategy for a feature, release, or whole service. Outputs: a **risk register**, a **test pyramid sized to the risk**, a **coverage matrix**, **quality gates**, and **handoffs** to the generator skills that actually scaffold the tests. Does **not** write individual tests; that's the per-topic skills.

## When to use

- New feature or service — sizing the test investment before building it
- Release-level test plan ("what must be green to ship")
- Migration / refactor — picking which tests retire, which earn an upgrade
- A team-level question: "are we testing the right things at the right level"
- Building the QA section of a PR description or RFC

## When NOT to use

- A full feature **test plan** — harness & tooling looked up from the repo, environments, artifacts, a gap-analyzed case inventory → `qa/manual/test-plan-writer` / the `qa-test-planner` agent (which *embeds* this skill's risk register and scope call)
- Writing the actual tests → `qa/<stack>/skills/api-test-author/writer` / `qa/<stack>/skills/ui-test-author/<tool>` / `qa/manual/test-case-writer`
- Reviewing existing tests → `qa/<stack>/skills/api-test-author/review` / `qa/<stack>/skills/ui-test-author/review`
- Bug reports → `qa/manual/bug-report-writer`
- Quality metrics dashboard → `qa/manual/quality-metrics`
- Performance plan → `qa/<stack>/skills/load-testing` + `qa/_shared/performance`

## Inputs needed

1. **Scope** — feature / release / service; what's in and what's out
2. **Stakeholders** — product, engineering, QA, support, legal, security
3. **Risk profile** — what does failure look like? customer impact? regulatory? data loss?
4. **Stacks involved** — backend(s), frontend(s), mobile, integrations
5. **Existing coverage** — what tests already exist; what's the gap
6. **Constraints** — deadline, budget, team size, infra access

## Method — risk-first, not coverage-first

A strategy that says "we'll have 80% unit test coverage" is not a strategy. A strategy that says "the payment refund flow is the top risk because reversal is irreversible in production; we'll cover it with contract tests, end-to-end happy path, and one chaos test for the gateway timeout" is.

### Step 1 — Risk register

Surface and rank risks. Each risk has:

| Field | Example |
|---|---|
| ID | R-01 |
| Description | Refund flow leaves the order in a half-paid state on gateway timeout |
| Likelihood | Medium |
| Impact | High (customer & finance) |
| Detection difficulty | High (slow tail, only visible via reconciliation) |
| Mitigation | Contract test against gateway sandbox; idempotent retries; reconciliation job |
| Owner | Payments squad |

Rank by Likelihood × Impact × Detection-difficulty. The top 5 risks drive the bulk of the test plan.

### Step 2 — Test pyramid sized to risk

The standard pyramid is a **default**, not a doctrine. Tilt it based on what the risks tell you:

| Layer | What it answers | Default weight | Tilt toward more when |
|---|---|---|---|
| **Unit** | Does each piece do what it claims? | Many | Domain logic dense, calculation-heavy, regulatory math |
| **Integration / Component** | Do pieces compose correctly with their adapters? | Some | New persistence layer, message bus integration, library upgrade |
| **Contract / API** | Does the service uphold its contract for consumers? | Some | Multiple consumers, public API, partner integration |
| **E2E / Acceptance** | Does the user journey work? | Few | Multi-service flows, regulated workflows, payment / login |
| **Exploratory** | What did we miss? | Always | New feature, complex UI, anything human-judgment-heavy |
| **Performance** | Does it scale? | Project-specific | Public-facing, high-traffic, latency-sensitive |
| **Security** | Can it be misused? | Project-specific | Auth, payment, PII, public endpoints |

Push tests **down** the pyramid whenever possible — a contract test is cheaper than an E2E that exercises the same contract.

### Step 3 — Coverage matrix

Risks × layers. For each top risk, mark which layers will cover it:

| Risk | Unit | Integration | Contract | E2E | Exploratory | Perf | Sec |
|---|---|---|---|---|---|---|---|
| R-01 Refund half-paid state | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| R-02 Auth0 token leakage | ✅ | — | ✅ | — | ✅ | — | ✅ |
| R-03 Slow reports endpoint | — | — | — | — | — | ✅ | — |
| R-04 Mobile crash on offline | ✅ | ✅ | — | — | ✅ | — | — |

A risk with no ✅ anywhere is unmitigated — flag explicitly. A risk with ✅ everywhere is over-tested or your layering is wrong (likely you're stacking E2E on top of robust contract tests).

### Step 4 — Quality gates

Concrete, automated, fail-the-pipeline criteria. **Numbers, not adjectives.**

| Gate | Threshold | Stage |
|---|---|---|
| Unit + integration tests pass | 100% | PR / CI |
| Coverage on changed lines | ≥ 80% line, ≥ 60% branch | PR |
| API contract tests pass | 100% | PR |
| E2E happy path | green | Pre-merge to `main` |
| Performance smoke (k6 / NBomber) | p95 latency ≤ baseline + 10%, error rate ≤ 0.5% | Pre-deploy to prod |
| Security: dependency scan | 0 high / critical CVEs | PR |
| Security: SAST | 0 new high findings | PR |
| Accessibility | 0 new axe critical findings on touched pages | PR |

**Coverage on changed lines** beats global coverage as a gate — legacy code doesn't suddenly become safer because you added tests elsewhere.

### Step 5 — Exit criteria for the release

A release is "done" when **all** of:

- Every Gate above is green
- All top-5 risks have at least one ✅ in the coverage matrix
- Exploratory test charters for the new feature have been executed (`qa/manual/exploratory-charter-writer`)
- The bug backlog has no open `blocker` or `major` linked to the release scope
- The deployment runbook is reviewed; rollback path tested at least in staging

If you don't write exit criteria down, the release ships when the calendar runs out, not when the work is done.

## Multi-stack considerations

When the change spans backend + frontend + mobile, the strategy has to assign tests to the right side of the contract:

| Contract surface | Owns the test |
|---|---|
| HTTP API → consumer | API contract tests (Pact / OpenAPI) on the consumer; integration tests on the producer |
| UI component → user | E2E on the consumer (Playwright / Appium); component tests on the producer |
| Message bus → consumer | Contract tests on both producer and consumer using fixed message schemas |

Avoid testing the *same* thing at three layers — that's not safety, that's tax.

## Deliverable shape

```markdown
# Test Strategy — <scope>

## Overview
<one paragraph: what's being shipped, why testing matters, the risk in one line>

## Risk register
| ID | Risk | L | I | Detect | Mitigation | Owner |
|----|------|---|---|--------|-----------|-------|

## Test pyramid (sized)
- Unit: <areas, why, ~test count>
- Integration: <areas>
- Contract: <consumers, tooling>
- E2E: <happy paths only>
- Exploratory: <charters, time-boxed>
- Performance: <scope or "N/A this release">
- Security: <scope>

## Coverage matrix
| Risk | Unit | Int | Contract | E2E | Explore | Perf | Sec |

## Quality gates
| Gate | Threshold | Stage |

## Exit criteria
- [ ] ...

## Out of scope / deferred
- <thing> — deferred because <reason>; revisit on <date / signal>

## Handoffs
- API tests → qa/<stack>/skills/api-test-author/writer
- UI tests → qa/<stack>/skills/ui-test-author/<tool>
- Test data → qa/<stack>/skills/test-data-builder
- Contract testing → qa/<stack>/skills/api-contract-testing
- Allure reporting → qa/reporting/<stack>/skills/test-reports
- Bug intake → qa/manual/bug-report-writer
```

## Rules

- **Risk-first**. Coverage targets follow from risk, not the other way around.
- Quality gates are quantitative — "good test coverage" is not a gate
- Push tests down the pyramid when behavior is exercisable lower — every E2E test on a CI run is a tax someone pays for years
- Out-of-scope is part of the strategy. Document what's not being tested and why.
- Strategy is short. Aim for a 2-page document, not a 12-page one no one reads.
- Re-run the strategy after each release retro — what missed, what was over-tested, what shifted in risk profile
- Pair test strategy with a deploy strategy. The blast radius of a bad deploy informs how much testing is enough.

## What NOT to do

- No "we'll write 80% test coverage" as the strategy
- No "TBD" in the risk register on the day of the kickoff
- No coverage matrix where every risk has every layer ticked — that's not a strategy, that's wishful thinking
- No quality gates with no owner — every gate has a tool and a name
- No exit criteria that depend on a human judgement call ("looks good") — explicit checks only
- No same-test-thrice (unit + integration + E2E covering the same path) — pick the right layer
- No "regression testing" as a step — regression coverage is a property of the suite, not a step
- No "test everything" — bound the scope by risk; deferred items belong in the doc

## Generation steps

1. Get the inputs above; refuse to start without a risk profile (or surface that as your first finding)
2. Run a quick brainstorm with stakeholders to surface risks; rank them
3. Draft the pyramid sized to the risks (heaviest layers where the top risks land)
4. Build the coverage matrix; mark unmitigated rows in red
5. Define quantitative quality gates and exit criteria
6. List deferred items with rationale
7. Hand off to per-topic skills (`qa/<stack>/skills/api-test-author/...`, `qa/<stack>/skills/ui-test-author/...`, `qa/<stack>/skills/test-data-builder`, `qa/manual/exploratory-charter-writer`) for the actual scaffolding

## Handoffs

- API test generation → `qa/<stack>/skills/api-test-author/writer`
- UI test generation → `qa/<stack>/skills/ui-test-author/<tool>`
- Test data → `qa/<stack>/skills/test-data-builder`
- Contract testing → `qa/<stack>/skills/api-contract-testing`
- Exploratory charters → `qa/manual/exploratory-charter-writer`
- Bug intake → `qa/manual/bug-report-writer`
- Allure reporting → `qa/reporting/<stack>/skills/test-reports`
- Metrics & dashboards → `qa/manual/quality-metrics`
