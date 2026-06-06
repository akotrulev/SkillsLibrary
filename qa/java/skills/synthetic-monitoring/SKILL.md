---
name: qa-synthetic-monitoring-java
description: >-
  Author **synthetic monitoring as code** in the JVM stack — scripted checks that run on a schedule against a
  LIVE environment (staging/prod) to catch outages and regressions in production, the "is it up and working
  *right now*" layer, distinct from CI pre-merge tests. **JVM/observability-native tool: Grafana Cloud
  Synthetic Monitoring** (because Checkly — the family's canonical — has **no Java SDK**, and Grafana matches
  this library's observability default of Loki/Prometheus/Tempo). Covers the **two check types** (cheap
  **HTTP/ping/DNS/TCP probe checks** = uptime + SLA, declared as config-as-code via the Grafana Terraform
  provider `grafana_synthetic_monitoring_check`; and **scripted/browser checks** — either k6 scripts run by
  Grafana Synthetic Monitoring, or the **Java-native** route: a Spring Boot `@Scheduled` Playwright-Java probe
  that reuses the page objects from `qa/java/skills/ui-test-author/playwright` and publishes a success/duration gauge
  via Micrometer → Prometheus); **monitoring-as-code** (Terraform + a scheduled probe, deployed by a pipeline);
  **alerting + SLA/latency thresholds** (Grafana alert rules / Prometheus Alertmanager on `probe_success` +
  duration, contact points → email/Slack/PagerDuty); **wait on a condition, never a sleep**; and **secrets
  from env, never logged** (Grafana SM token / target creds from env, read lazily). Triggers: "set up
  synthetic monitoring for our JVM app", "add a Grafana synthetic check as code", "monitor our login journey
  on a schedule with Playwright-Java and alert via Prometheus", "Terraform grafana_synthetic_monitoring_check",
  "assert an SLA on a live endpoint with Grafana". Do NOT use for: the TypeScript/Checkly stack (use
  qa-synthetic-monitoring-typescript — the canonical), the .NET stack (use qa-synthetic-monitoring-dotnet —
  Azure App Insights availability tests), pre-merge CI tests against an ephemeral env (use qa-ci-pipelines-* —
  synthetics run *post-deploy* against a live target), load testing (use qa-performance-gatling/k6 — synthetics
  check uptime, not throughput), authoring the Playwright journey itself (use qa-ui-test-author-playwright-java
  — this skill *reuses* those page objects), or full Allure result wiring (use qa-allure-reporting-java).
---

# Synthetic Monitoring as Code (Grafana Cloud Synthetic Monitoring · Java 21) — **ported from the TypeScript/Checkly canonical**

This is the **java** sibling of the `qa/java/skills/synthetic-monitoring/` family. The canonical stack is
`qa-synthetic-monitoring-typescript` (**Checkly `@checkly/cli`**). This file **ports the discipline, not the
code** — and the port has an honest divergence: **Checkly has no official Java SDK** (it's TS/JS-only; browser
checks are Playwright-JS). The JVM/observability-native tool is **Grafana Cloud Synthetic Monitoring**, chosen
because it **matches the library's observability default** (OpenTelemetry → Grafana / Loki / Prometheus /
Tempo) — synthetics feed the same dashboards and Alertmanager you already run. The four ideas are identical to
the canonical — two check types, monitoring-as-code, alerting + SLA thresholds, wait-on-a-condition — only the
tool changes.

> **An honest note on "JVM-native".** Grafana Synthetic Monitoring's *scripted/browser* checks are **k6
> scripts (JavaScript)** — same reality as Checkly's Playwright-JS browser checks: there's no JVM scripting
> surface. So this file gives you **two routes for the rich journey layer**: (1) k6 scripts in Grafana SM
> (cross-link `qa-performance-k6` — JS, but managed alongside everything else), or (2) the **truly Java-native
> route** — a Spring Boot `@Scheduled` **Playwright-Java** probe that reuses your `qa-ui-test-author-playwright-java`
> page objects and publishes metrics to Prometheus (the parallel to the .NET sibling's `TrackAvailability`).
> The cheap HTTP/ping/TCP layer needs no scripting in either route — it's pure Terraform config-as-code.

## What synthetic monitoring is (and what it is not)

**Synthetic monitoring** = scripted checks that run **on a schedule against a deployed, live target**
(staging/prod), continuously, alerting a human when the target is down or degraded. A synthetic check is a
**continuously-running assertion**: you don't watch the result, you alert on its *failure*.

It is **not**:

- a **CI test** — CI tests run **once, pre-merge, against an ephemeral env** to gate a change
  (`qa-ci-pipelines-*`). A synthetic runs **forever, post-deploy, against the real thing**.
- a **load test** — `qa-performance-gatling` / `qa-performance-k6` drive throughput to find the breaking
  point; a synthetic fires one scripted journey every N minutes to answer "is it working *right now*".
- a **journey author** — this skill *reuses* the page objects authored by
  `qa-ui-test-author-playwright-java`; it is the **assertion + scheduling + alerting layer**, not a new author.

> **The discipline this skill encodes** (identical to the canonical):
>
> 1. **Two check types, both as code** — cheap **HTTP/ping/TCP probe checks** for the "is the endpoint up +
>    within SLA" layer, and **scripted/browser checks** for "can a user actually do the thing". Both declared
>    as code (Terraform + a scheduled probe), reviewed and deployed by a pipeline — never clicked together in
>    the Grafana UI.
> 2. **Assert an SLA, not just pass/fail** — a 200 that takes 8 seconds is a regression. Probe checks emit a
>    **`probe_http_duration_seconds`** metric; gate on it + the body, not just `probe_success`.
> 3. **Alert on the failure** — a Grafana alert rule + a contact point page on-call. A check no one is paged
>    on does nothing.
> 4. **Wait on a condition, never a sleep** — Playwright-Java auto-waits; never `Thread.sleep` to "let it settle".

## Decision matrix — which check for which job

| You want to know… | Check type | Mechanism | Gate on |
|---|---|---|---|
| Is the API/health endpoint up and fast? | **HTTP probe check** | `grafana_synthetic_monitoring_check` (`http`) | status + content match + `probe_http_duration_seconds` (the SLA) |
| Is a host/port reachable? | **ping / tcp / dns check** | `grafana_synthetic_monitoring_check` (`ping`/`tcp`/`dns`) | `probe_success` + duration |
| A multi-call API flow? | **multihttp / scripted (k6)** | `grafana_synthetic_monitoring_check` (`multihttp`/`scripted`) | each step's status + chained checks |
| Can a user log in / check out (real browser)? | **k6 browser check** *or* **Java-native probe** | k6 `browser` script, **or** a `@Scheduled` Playwright-Java probe → Micrometer | the journey completes + `Duration` budget |

**Rule of thumb:** *every endpoint* gets a cheap HTTP/ping probe check (config-only, runs from Grafana's
global probes). *Every business-critical journey* gets a scripted/browser check or a Java-native probe. Don't
script-check what an HTTP probe can prove.

## Stack

- Java 21, Spring Boot 3.x, TestNG (for any local verification of the probe logic) — **no `Thread.sleep`-as-wait**
- Grafana Cloud Synthetic Monitoring — runs probe checks from global locations; metrics → Prometheus, logs → Loki
- Terraform `grafana/grafana` provider — `grafana_synthetic_monitoring_check` as **config-as-code**
- `com.microsoft.playwright:playwright` — the Java-native journey probe; **reuse** the page objects from
  `qa-ui-test-author-playwright-java` (cross-link — this skill does not author them)
- `io.micrometer:micrometer-registry-prometheus` — the probe publishes a `synthetic_check` gauge for Grafana to alert on
- Gradle (Kotlin DSL) for the probe app; secrets via env, read lazily, never logged (`GRAFANA_SM_ACCESS_TOKEN`, target creds)

```
monitoring/
├── infra/
│   └── checks.tf                     ← HTTP/ping/tcp probe checks + alert rules (config-as-code)
└── probe-app/                        ← (Java-native route) a Spring Boot scheduled probe
    └── src/main/java/com/acme/monitoring/
        ├── CheckoutJourneyProbe.java ← @Scheduled Playwright-Java journey, REUSES pages/*, → Micrometer gauge
        └── SyntheticMetrics.java     ← the Prometheus gauge Grafana alerts on
```

## Monitoring-as-code — Terraform for the cheap layer, a scheduled probe for the rich layer

Nothing is hand-clicked in Grafana. The cheap probe layer is **declarative Terraform**; the rich journey layer
is **a scheduled probe** deployed by the same pipeline.

**HTTP probe check as config-as-code:**

```hcl
# monitoring/infra/checks.tf
resource "grafana_synthetic_monitoring_check" "storefront_health" {
  job     = "storefront-health"
  target  = "https://staging.acme.example/api/health"
  enabled = true
  probes  = [data.grafana_synthetic_monitoring_probes.main.probes["Amsterdam"],
             data.grafana_synthetic_monitoring_probes.main.probes["Atlanta"]]   # multiple regions
  labels  = { env = "staging", team = "storefront" }

  settings {
    http {
      method            = "GET"
      ip_version        = "V4"
      no_follow_redirects = false
      fail_if_not_ssl   = true                                  # also covers the TLS layer
      valid_status_codes = [200]                                # status assertion
      fail_if_body_not_matches_regexp = ["\"status\":\"healthy\""]   # body SHAPE, not just 2xx
    }
  }
}
```

The check's **`frequency`** (set on the check / inherited) is the cadence; the emitted
**`probe_http_duration_seconds`** metric is the latency the alert gates on (the SLA). Deploy from the pipeline
(`terraform apply`) — cross-link `qa-ci-pipelines-gitlab-ci`. This is the synthetic-vs-CI boundary: this check
runs **forever, against the live target**, not as a pre-merge gate.

## Check type 1 — HTTP/ping/TCP probe checks (status + latency + content)

The Terraform above *is* the API/uptime layer. The key SLA controls: `valid_status_codes` +
`fail_if_body_not_matches_regexp` assert status **and** body shape; multiple `probes` (regions) distinguish a
regional blip from a real outage; and the **`probe_http_duration_seconds`** metric is what the alert rule gates
on. **Assert the SLA, not just `probe_success`** — that's what makes it a monitor and not a ping. For non-HTTP
reachability use the `ping`, `tcp`, or `dns` settings block; for a chained API flow use `multihttp`.

## Check type 2 — the journey layer (k6, or the Java-native probe)

**Route A — k6 (in Grafana SM).** Grafana Synthetic Monitoring runs **k6 scripts** as `scripted` checks (and
k6 `browser` scripts as browser checks). This reuses `qa-performance-k6` muscle — honest caveat: it's
JavaScript, not Java. Good when the journey is API-shaped or the team already writes k6.

**Route B — the Java-native probe (author the journey in Java end-to-end).** A Spring Boot `@Scheduled`
**Playwright-Java** probe runs the journey (**reusing the page objects** from
`qa-ui-test-author-playwright-java`) and publishes a **success/duration gauge** via Micrometer; Grafana alerts
on the Prometheus metric. This is the parallel to the .NET sibling's `TrackAvailability` — the way to keep the
probe in Java, co-located with your services.

```java
// monitoring/probe-app/.../CheckoutJourneyProbe.java
@Component
public final class CheckoutJourneyProbe {

    private static final Logger log = LoggerFactory.getLogger(CheckoutJourneyProbe.class);
    private final SyntheticMetrics metrics;          // constructor injection — no service locator

    public CheckoutJourneyProbe(SyntheticMetrics metrics) { this.metrics = metrics; }

    @Scheduled(fixedRateString = "PT15M")            // every 15 min — the schedule, like Checkly's scheduler
    public void runCheckoutJourney() {
        var started = Instant.now();
        boolean success = false;
        try (var playwright = Playwright.create()) {
            var browser = playwright.chromium().launch();
            var page = browser.newPage();

            // REUSE the SAME page objects the CI suite uses — intent, not selectors
            var login = new LoginPage(page);
            login.goTo();
            // creds from env, read lazily, NEVER logged — set via Spring config / secret store
            login.signInAs(System.getenv("SYNTHETIC_USER"), System.getenv("SYNTHETIC_PASSWORD"));

            var cart = new CartPage(page);
            cart.addFirstFeaturedItem();
            // Playwright auto-waits on the condition — NO Thread.sleep to "let the cart update"
            assertThat(cart.itemCount()).hasText("1");

            var elapsed = Duration.between(started, Instant.now());
            success = elapsed.compareTo(Duration.ofSeconds(15)) <= 0;   // SLA: also fail if too slow
            metrics.recordDuration("checkout-journey", elapsed);
        } catch (Exception ex) {
            log.warn("Synthetic checkout journey failed: {}", ex.getMessage());   // structured, no string interp
        } finally {
            metrics.recordResult("checkout-journey", success);          // ← the gauge Grafana alerts on
        }
    }
}
```

```java
// monitoring/probe-app/.../SyntheticMetrics.java — the Prometheus gauges
@Component
public final class SyntheticMetrics {

    private final MeterRegistry registry;
    private final Map<String, AtomicInteger> success = new ConcurrentHashMap<>();

    public SyntheticMetrics(MeterRegistry registry) { this.registry = registry; }

    public void recordResult(String check, boolean ok) {
        success.computeIfAbsent(check, c -> registry.gauge(
            "synthetic_check_success", Tags.of("check", c), new AtomicInteger())).set(ok ? 1 : 0);
    }

    public void recordDuration(String check, Duration d) {
        registry.timer("synthetic_check_duration", "check", check).record(d);   // the latency Grafana gates on
    }
}
```

## Alerting + SLA thresholds — the part that makes it a monitor

Both routes surface metrics into Prometheus (`probe_success` / `probe_http_duration_seconds` from Grafana SM;
`synthetic_check_success` / `synthetic_check_duration` from the Java probe). **Alert on them** with a Grafana
alert rule + a contact point — declared as code (Terraform `grafana_rule_group` / provisioned alerting) so the
alert is reviewed and versioned like everything else.

```hcl
# monitoring/infra/checks.tf — alert when the storefront synthetic fails, page via the contact point
resource "grafana_rule_group" "synthetic_alerts" {
  name             = "synthetic-monitoring"
  folder_uid       = grafana_folder.monitoring.uid
  interval_seconds = 60

  rule {
    name      = "Storefront synthetic down or slow"
    condition = "C"
    # A: probe_success == 0 OR duration over budget; reduce + threshold in B/C (abbreviated)
    data { ref_id = "A"  /* PromQL: min_over_time(probe_success{job="storefront-health"}[5m]) */ }
    data { ref_id = "C"  /* threshold: A < 1 -> firing */ }
    for          = "5m"                  # sustained 5 min before paging — absorbs a single transient blip
    annotations  = { summary = "storefront synthetic failing" }
    labels       = { severity = "critical" }
  }
}
```

Route the firing alert with a **contact point** (email / Slack / PagerDuty) — `grafana_contact_point` +
`grafana_notification_policy`, also as Terraform. A second rule on `probe_http_duration_seconds` >
your-latency-budget catches **slow-but-up** (the canonical's `degradedResponseTime` signal). The `for = "5m"`
window absorbs a single transient blip without paging — the canonical's bounded-retry idea expressed as a
"sustained failure" requirement, **not** a knob to widen just to silence a real flake.

## Secrets from env, never logged

The Grafana SM access token, target URLs, and test-user creds come from env / a secret store — read lazily,
never committed, never logged:

```hcl
provider "grafana" {
  sm_access_token = var.grafana_sm_access_token   # from TF_VAR_grafana_sm_access_token in the CI secret store
}
```

```java
// the probe reads creds lazily from the environment — never hard-coded, never logged
login.signInAs(System.getenv("SYNTHETIC_USER"), System.getenv("SYNTHETIC_PASSWORD"));
```

## The boundary — a synthetic monitor vs a CI gate

Same distinction as the canonical, expressed in the Grafana world:

| | CI test (`qa-ci-pipelines-*`) | Synthetic monitor (this skill) |
|---|---|---|
| **When** | Pre-merge / pre-promote, once | On a schedule, forever |
| **Against** | An ephemeral env | The live prod/staging target |
| **Host** | The CI runner | Grafana SM probes / a `@Scheduled` probe app |
| **Alerts?** | No — green/red gate | Yes — Grafana alert rule + contact point pages on-call |

A Playwright-Java journey can serve **both**: run it as a TestNG test in CI against the preview env (the gate),
**and** run the same page objects from the `@Scheduled` probe against the live env (the monitor). One set of
page objects, two execution models.

## Anti-patterns

- **Asserting only `probe_success`.** A 200 that takes 9 seconds is a regression. *Fix:* alert on
  `probe_http_duration_seconds` / `synthetic_check_duration` (the latency budget) and the body
  (`fail_if_body_not_matches_regexp`), not just up/down.
- **A check with no alert rule.** It runs, the metric goes red, no one is paged. *Fix:* a `grafana_rule_group`
  on `probe_success` + a contact point; a synthetic *is* its alert.
- **`Thread.sleep(3000)` to "let it settle".** Flaky and slow, banned across the library. *Fix:* Playwright-Java
  auto-waits; `assertThat(locator).hasText(...)`. (Cross-link `qa-flaky-test-quarantine-java`.)
- **Hand-clicking checks/alerts in the Grafana UI.** Unversioned, unreviewed, lost on tenant churn. *Fix:*
  Terraform `grafana_synthetic_monitoring_check` + provisioned alert rules; a deployed `@Scheduled` probe app.
- **Running the synthetic as the merge gate against an ephemeral env.** That's a CI test, wrong tool. *Fix:*
  the gate is a TestNG run in CI; the monitor is the Grafana SM check / `@Scheduled` probe against the live target.
- **Re-authoring the journey inside the probe.** Duplicated selectors that drift from the CI suite. *Fix:* the
  probe **imports the same page objects** from `qa-ui-test-author-playwright-java`.
- **Widening `for` just to stop the alerts.** That's the flaky-quarantine masking knob — it delays the page
  while users suffer. *Fix:* keep `for` matched to "sustained real failure" and fix the root flakiness.
- **The SM token / creds in `checks.tf` or `application.yml`.** Committed secrets. *Fix:* `TF_VAR_*` from the CI
  secret store + `System.getenv` read lazily; never logged.

## Examples

**End-to-end: a cheap HTTP probe check + a Java-native journey probe, both alerting through one contact point.**

`checks.tf` declares the `storefront_health` HTTP check (multi-region, status + content match, emitting
`probe_http_duration_seconds`); the `CheckoutJourneyProbe` runs every 15 min via `@Scheduled` (Playwright-Java,
reusing `pages/*`) and publishes `synthetic_check_success`/`synthetic_check_duration`; one `grafana_rule_group`
alerts on both metrics (`for = "5m"`) and routes to the on-call contact point. The HTTP check pages if the API
is down or slow; the journey probe pages if a user can't check out — and the same `LoginPage`/`CartPage` page
objects are exercised by the CI TestNG suite (the gate) and the probe (the monitor).

## Rules (hard constraints)

- **Synthetics run against a LIVE target, post-deploy, on a schedule — never as the merge gate.** Grafana SM
  checks + the `@Scheduled` probe monitor the live env; the pre-merge gate is a TestNG run in CI
  (`qa-ci-pipelines-*`).
- **Assert an SLA, not just up/down.** Alert on `probe_http_duration_seconds` / `synthetic_check_duration`
  (latency budget) + the body match, not only `probe_success`.
- **Every check has an alert rule.** A `grafana_rule_group` on `probe_success`/duration + a contact point. A
  synthetic *is* its alert.
- **Absorb transients without masking.** Use `for = "5m"` (sustained failure) rather than retrying-to-green;
  never widen the window just to silence a real flake (`qa-flaky-test-quarantine-java`).
- **Wait on a condition, never a sleep.** Playwright-Java auto-waits; `assertThat(...).hasText`. No `Thread.sleep`-as-wait.
- **Monitoring-as-code.** Checks + alert rules in Terraform, the journey probe in a deployed `@Scheduled` app —
  reviewed and pipeline-deployed, never hand-clicked in Grafana.
- **The journey probe REUSES the page objects** from `qa-ui-test-author-playwright-java` — intent, not
  selectors; this skill is the assertion/scheduling/alerting layer, not a journey author.
- **Secrets from env, never logged.** `GRAFANA_SM_ACCESS_TOKEN` via `TF_VAR_*` + creds from `System.getenv`,
  read lazily. Constructor injection only; structured logging (message templates, never string interpolation);
  test names `Should_X_When_Y`; one logical assertion.

## Cross-references

- `qa-synthetic-monitoring-typescript` — the **canonical** stack (Checkly `@checkly/cli`), the richest
  monitoring-as-code experience; this java file ports its four ideas. **If your team will write TS for
  monitoring, prefer Checkly even in a JVM shop** (small `monitoring/` TS sub-project run from the pipeline).
- `qa-synthetic-monitoring-dotnet` — same four ideas, the .NET/Azure-native tool: **Azure App Insights
  availability tests**. Honest divergence: no Checkly .NET SDK either. The Java-native `@Scheduled` probe here
  is the parallel to its custom `TrackAvailability` probe.
- `qa-ui-test-author-playwright-java` — authors the page objects + journeys that the **Java-native probe reuses**.
  This skill schedules and alerts on them; it does not author them. Mirror its intent-not-selectors discipline.
- `qa-performance-k6` (#?) — the k6 muscle Grafana SM's **scripted/browser checks** reuse (Route A), and the
  load-vs-uptime overlap: k6 *can* run as a synthetic via Grafana SM. Synthetics check "is it working"; k6 checks
  "how much can it take". `qa-performance-gatling` is the JVM load tool (also not a synthetic).
- `qa-ci-pipelines-gitlab-ci` (#13) / `-github-actions` / `-azure-pipelines` — the **pre-merge gate against
  ephemeral envs** boundary; also where `terraform apply` for the checks + the probe-app deploy are wired.
- `qa-auth0-test-tokens-java` (#16) — M2M / test-user tokens for checks hitting an **authenticated** live
  endpoint (mint in the probe / multihttp setup; creds from env, lazily).
- `qa-flaky-test-quarantine-java` (#36) — a check that needs `for` widened to stay green is *flaky*; fix the
  root cause rather than masking the alert.
- `qa-allure-reporting-java` — surfacing probe-verification runs; and `observability` (the Grafana / Loki /
  Prometheus / Tempo stack) the synthetic metrics natively feed.
