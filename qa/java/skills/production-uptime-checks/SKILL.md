---
name: production-uptime-checks
description: Use when authoring synthetic monitoring as code from the JVM stack — scheduled probe checks (HTTP/ping/DNS/TCP) and scripted checks against live staging/prod via Grafana Cloud Synthetic Monitoring + Terraform. The "is it up right now" layer, distinct from CI pre-merge tests. Triggers: "add a prod uptime check", "synthetic monitor for the login flow", "monitoring as code". Not for pre-merge CI gates (`qa-java:ci-pipelines`) or load testing (`qa-java:load-testing`).
---

# Synthetic Monitoring as Code (Grafana Cloud Synthetic Monitoring · Java 21)

The **java** sibling of the family whose canonical stack is `qa-typescript:production-uptime-checks` (**Checkly
`@checkly/cli`**). This file **ports the discipline, not the code** — and the port has an honest divergence:
**Checkly has no official Java SDK** (browser checks are Playwright-JS). The JVM/observability-native tool is
**Grafana Cloud Synthetic Monitoring**, chosen because it **matches the library's observability default**
(OpenTelemetry → Grafana / Loki / Prometheus / Tempo) — synthetics feed the same dashboards and Alertmanager you
already run. The four ideas are the canonical's; only the tool changes.

> **An honest note on "JVM-native".** Grafana Synthetic Monitoring's *scripted/browser* checks are **k6 scripts
> (JavaScript)** — there's no JVM scripting surface. So the rich journey layer has **two routes**: (A) k6 scripts
> in Grafana SM (cross-link `qa-typescript:load-testing`), or (B) the **Java-native route** — a Spring Boot
> `@Scheduled` **Playwright-Java** probe that reuses the `qa-java:ui-tests-playwright` page objects,
> publishes metrics to Prometheus and **keeps a trace, video and screenshot of every failed run**. The cheap
> HTTP/ping/TCP layer needs no scripting in either route — it's pure Terraform config-as-code.

## What synthetic monitoring is (and what it is not)

**Synthetic monitoring** = scripted checks that run **on a schedule against a deployed, live target**
(staging/prod), continuously, alerting a human when the target is down or degraded. A synthetic check is a
**continuously-running assertion**: you don't watch the result, you alert on its *failure*. It is **not** a **CI
test** (once, pre-merge, against an ephemeral env — `qa-java:ci-pipelines`), **not** a **load test**
(`qa-java:load-testing` / `-typescript` find the breaking point), and **not** a **journey author** — it *reuses*
the page objects authored by `qa-java:ui-tests-playwright`.

> **The discipline this skill encodes** (identical to the canonical):
>
> 1. **Two check types, both as code** — cheap **HTTP/ping/TCP probe checks** for "is the endpoint up + within
>    SLA", and **scripted/browser checks** for "can a user actually do the thing". Both declared as code
>    (Terraform + a scheduled probe), deployed by a pipeline — never clicked together in the Grafana UI.
> 2. **Assert an SLA, not just pass/fail** — a 200 that takes 8 seconds is a regression. Gate on
>    `probe_http_duration_seconds` + the body, not just `probe_success`.
> 3. **Alert on the failure — and keep the evidence.** A Grafana alert rule + a contact point page on-call; a
>    failed journey leaves its trace, video and screenshot so the page is diagnosable without a rerun.
> 4. **Wait on a condition, never a sleep** — Playwright-Java auto-waits; never `Thread.sleep` to "let it settle".

## Decision matrix — which check for which job

| You want to know… | Check type | Mechanism | Gate on |
|---|---|---|---|
| Is the API/health endpoint up and fast? | **HTTP probe check** | `grafana_synthetic_monitoring_check` (`http`) | status + content match + `probe_http_duration_seconds` |
| Is a host/port reachable? | **ping / tcp / dns check** | `grafana_synthetic_monitoring_check` (`ping`/`tcp`/`dns`) | `probe_success` + duration |
| A multi-call API flow? | **multihttp / scripted (k6)** | `grafana_synthetic_monitoring_check` (`multihttp`/`scripted`) | each step's status + chained checks |
| Can a user log in / check out (real browser)? | **k6 browser check** *or* **Java-native probe** | k6 `browser` script, **or** a `@Scheduled` Playwright-Java probe → Micrometer | the journey completes + `Duration` budget |

**Rule of thumb:** *every endpoint* gets a cheap HTTP/ping probe check. *Every business-critical journey* gets a
scripted/browser check or a Java-native probe. Don't script-check what an HTTP probe can prove.

## Stack

- Java 21, Spring Boot 3.x, TestNG for local verification of the probe logic — **no `Thread.sleep`-as-wait**
- Grafana Cloud Synthetic Monitoring — probe checks from global locations; metrics → Prometheus, logs → Loki
- Terraform `grafana/grafana` provider — `grafana_synthetic_monitoring_check` as **config-as-code**
- `com.microsoft.playwright:playwright` at the pin in the **Versions** table of
  `qa/java/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing) — the Java-native probe;
  **reuse** the page objects from `qa-java:ui-tests-playwright`
- `io.micrometer:micrometer-registry-prometheus` — the probe's `synthetic_check_*` metrics
- Gradle (Kotlin DSL) for the probe app; secrets via env, read lazily, never logged

```
monitoring/
├── infra/checks.tf                     ← HTTP/ping/tcp probe checks + alert rules (config-as-code)
└── probe-app/src/main/java/com/acme/monitoring/
    ├── CheckoutJourneyProbe.java       ← @Scheduled Playwright-Java journey, REUSES pages/*
    ├── ProbeEvidence.java              ← keeps trace, video, screenshot of a failed run
    └── SyntheticMetrics.java           ← the Prometheus metrics Grafana alerts on
```

## Check type 1 — HTTP/ping/TCP probe checks (status + latency + content)

```hcl
resource "grafana_synthetic_monitoring_check" "storefront_health" {
  job     = "storefront-health"
  target  = "https://staging.acme.example/api/health"
  enabled = true
  probes  = [data.grafana_synthetic_monitoring_probes.main.probes["Amsterdam"],
             data.grafana_synthetic_monitoring_probes.main.probes["Atlanta"]]
  labels  = { env = "staging", team = "storefront" }

  settings {
    http {
      method                          = "GET"
      ip_version                      = "V4"
      no_follow_redirects             = false
      fail_if_not_ssl                 = true
      valid_status_codes              = [200]
      fail_if_body_not_matches_regexp = ["\"status\":\"healthy\""]
    }
  }
}
```

`monitoring/infra/checks.tf`. `valid_status_codes` + `fail_if_body_not_matches_regexp` assert status **and** body
shape; `fail_if_not_ssl` covers the TLS layer; multiple `probes` (regions) tell a regional blip from a real
outage; the check's `frequency` is the cadence, and the emitted **`probe_http_duration_seconds`** is the latency
the alert gates on. For non-HTTP reachability use the `ping`, `tcp` or `dns` block; for a chained API flow,
`multihttp`. Deploy with `terraform apply` from the pipeline (`qa-java:ci-pipelines`).

## Check type 2 — the journey layer (k6, or the Java-native probe)

**Route A — k6 (in Grafana SM).** Grafana SM runs **k6 scripts** as `scripted` checks (and k6 `browser` scripts as
browser checks). Honest caveat: JavaScript, not Java. Good when the journey is API-shaped or the team writes k6.

**Route B — the Java-native probe.** A Spring Boot `@Scheduled` **Playwright-Java** probe runs the journey with
the CI suite's page objects, publishes a success/duration metric via Micrometer, and keeps failure evidence.

```java
@Component
public final class CheckoutJourneyProbe {
    private static final String CHECK = "checkout-journey";
    private static final Duration BUDGET = Duration.ofSeconds(15);
    private static final Logger log = LoggerFactory.getLogger(CheckoutJourneyProbe.class);

    private final SyntheticMetrics metrics;
    private final ProbeEvidence evidence;
    private final ProbeSettings settings;
    private final Clock clock;

    public CheckoutJourneyProbe(SyntheticMetrics metrics, ProbeEvidence evidence, ProbeSettings settings, Clock clock) {
        this.metrics = metrics;
        this.evidence = evidence;
        this.settings = settings;
        this.clock = clock;
    }

    @Scheduled(fixedRateString = "PT15M")
    public void runCheckoutJourney() {
        Instant started = clock.instant();
        boolean passed = false;
        try (Playwright playwright = Playwright.create()) {
            Page page = evidence.recordedPage(playwright.chromium().launch(), settings.baseUrl());
            boolean completed = completesCheckout(page);
            Duration elapsed = Duration.between(started, clock.instant());
            metrics.recordDuration(CHECK, elapsed);
            passed = completed && elapsed.compareTo(BUDGET) <= 0;
            evidence.keep(CHECK, passed, page);
        } finally {
            metrics.recordResult(CHECK, passed);
        }
    }

    private boolean completesCheckout(Page page) {
        try {
            new LoginPage(page).signIn(settings.syntheticUser());
            CartPage cart = new CartPage(page);
            cart.addFirstFeaturedItem();
            assertThat(cart.itemCount()).hasText("1");
            return true;
        } catch (AssertionError | PlaywrightException failure) {
            log.warn("Synthetic {} failed: {}", CHECK, failure.getMessage());
            return false;
        }
    }
}
```

- **The catch names the assertion error type.** `PlaywrightAssertions.assertThat` fails with opentest4j's
  `AssertionFailedError`, an **`AssertionError`** — an `Error`, so `catch (Exception)` lets it escape the
  scheduled method and the run records nothing. A `TimeoutError` from an action is a `PlaywrightException`. These
  two are a failed journey; anything else is a probe defect and propagates.
- **The result is always recorded** — `finally` writes `synthetic_check_success` even when the browser fails to
  launch, so a broken probe reads as a failed check, never as the last green value.
- **Over budget is a failure** — a run that completed in 20 s against a 15 s budget records `0` and keeps its
  evidence like any other failure.
- **The `Playwright` lives and dies inside one run**, on the scheduler's thread, so Playwright's thread rule holds
  (`ui-test-author/playwright/references/lifecycle.md` §1). Never a long-lived `Playwright` bean.
- This is production code, not a test: the catch and the `finally` are the probe's job (CLAUDE.md's test rules
  ban them in test bodies, not in a monitor).

## Failure evidence — what a failed run keeps

`ProbeEvidence` (`references/details.md`) applies `qa/java/skills/evidence-capture`'s failure-evidence rules to the
probe: every run records a trace (screenshots + DOM snapshots) and a video; a **failed** run keeps them, a passed
run discards them.

| Evidence | Kept when | File |
|---|---|---|
| Full-page screenshot | the run failed | `<evidence-dir>/<check>.<UTC timestamp>.png` |
| Trace | the run failed | `<evidence-dir>/<check>.<UTC timestamp>.zip` |
| Video | the run failed | `<evidence-dir>/<check>.<UTC timestamp>.webm` |

- **Hook order is `BaseTest`'s** (`lifecycle.md` §5): read `page.video()`; on failure the screenshot (live page)
  and `tracing().stop(setPath)`; `context.close()`; on failure `video.saveAs`; `video.delete()` always. The
  screenshot sits in a narrow, logged `PlaywrightException` catch, so a crashed page still keeps its trace and
  video.
- **`<evidence-dir>` is `SYNTHETIC_EVIDENCE_DIR`** — a private volume with a 14-day lifecycle, never a public
  bucket: the trace and video carry the synthetic user's session. The warning log line names the files, and the
  alert's annotation links the dashboard; on-call reads the trace with
  `npx playwright@1.63.0 trace open <zip>` (`evidence-capture` § Reading a failure).
- A k6 route keeps Grafana SM's own logs and screenshots; this table is the Java-native route only.

## Alerting + SLA thresholds — the part that makes it a monitor

Both routes surface metrics into Prometheus (`probe_success` / `probe_http_duration_seconds` from Grafana SM;
`synthetic_check_success` / `synthetic_check_duration` from the Java probe). **Alert on them** with a
`grafana_rule_group` + a contact point, declared as Terraform (`references/details.md` § Alert rules). A second
rule on duration over the latency budget catches **slow-but-up**. `for = "5m"` absorbs a single transient blip
without paging — a "sustained failure" requirement, **not** a knob to widen just to silence a real flake.

One set of page objects, two execution models: the TestNG suite in CI against the preview env (the gate), and
the `@Scheduled` probe against the live env (the monitor).

## Deep-dive reference

`references/details.md` — **read it when the task touches them**: **`ProbeEvidence`**; **`SyntheticMetrics`**;
**Alert rules**; **Secrets**; **Worked example**.

## Anti-patterns

- **`catch (Exception)` around the journey.** Misses the `AssertionFailedError` a web-first assertion throws.
  *Fix:* `catch (AssertionError | PlaywrightException ...)`, and record the result in `finally`.
- **A failed run that keeps only a log line.** On-call reruns by hand to see what broke. *Fix:* `ProbeEvidence`.
- **Asserting only `probe_success`.** *Fix:* alert on duration (the latency budget) and the body, not just up/down.
- **Re-authoring the journey inside the probe.** *Fix:* import the same page objects as the CI suite.
- **Widening `for` just to stop the alerts.** *Fix:* keep `for` matched to "sustained real failure"; fix the flake.
- **The SM token / creds in `checks.tf` or `application.yml`.** *Fix:* `TF_VAR_*` + `System.getenv`, never logged.

## Rules (hard constraints)

- **Synthetics run against a LIVE target, post-deploy, on a schedule — never as the merge gate.**
- **Assert an SLA, not just up/down**: duration over budget fails the check.
- **Every check has an alert rule** and a contact point.
- **A failed journey keeps its trace, video and full-page screenshot** under `SYNTHETIC_EVIDENCE_DIR`, in
  `evidence-capture`'s hook order, with the one narrow, logged screenshot catch; a passed run keeps nothing.
- **The journey's catch names `AssertionError` and `PlaywrightException`**; the result is recorded in `finally`.
- **Absorb transients without masking.** `for = "5m"`, never retry-to-green (`qa-java:flaky-test-quarantine`).
- **Wait on a condition, never a sleep.**
- **Monitoring-as-code.** Checks + alert rules in Terraform, the probe in a deployed `@Scheduled` app.
- **The journey probe REUSES the page objects** from `qa-java:ui-tests-playwright`.
- **Secrets from env, never logged.** Constructor injection only; structured logging (message templates).

## Cross-references

- `qa-typescript:production-uptime-checks` — the **canonical** stack (Checkly). **If your team will write TS for
  monitoring, prefer Checkly even in a JVM shop.**
- `qa-dotnet:production-uptime-checks` — **Azure App Insights availability tests**; its `TrackAvailability` probe
  is the parallel to the `@Scheduled` probe here.
- `qa-java:ui-tests-playwright` — authors the page objects the **Java-native probe reuses**.
- `qa-java:evidence-capture` — the failure-evidence rules `ProbeEvidence` applies, and how to read a trace.
- `qa-typescript:load-testing` — the k6 muscle Route A reuses; `qa-java:load-testing` (Gatling) is load, not uptime.
- `qa-java:ci-pipelines` — the pre-merge gate boundary, and where `terraform apply` + the probe deploy are wired.
- `qa-java:test-login-tokens` — tokens for checks hitting an **authenticated** live endpoint.
- `qa-java:flaky-test-quarantine` — a check that needs `for` widened to stay green is *flaky*.
- `observability` (the Grafana / Loki / Prometheus / Tempo stack) — what the synthetic metrics natively feed.
