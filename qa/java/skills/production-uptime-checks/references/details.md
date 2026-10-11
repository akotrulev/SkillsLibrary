# Deep-dive details — `qa-java:production-uptime-checks`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## `ProbeEvidence` — keep a failed run's trace, video and screenshot

`monitoring/probe-app/src/main/java/com/acme/monitoring/ProbeEvidence.java`. It applies
`qa/java/skills/evidence-capture`'s failure-evidence rules to a scheduled probe instead of a TestNG test:
`recordedPage` starts the recording on every run, `keep` saves it only when the run failed. The hook order is
`BaseTest.closeContext`'s (`ui-test-author/playwright/references/lifecycle.md` §5), and the screenshot's narrow,
logged `PlaywrightException` catch is the same one (plan D29): a crashed page cannot be photographed, and the
trace and video must still be kept.

```java
package com.acme.monitoring;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.Tracing;
import com.microsoft.playwright.Video;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.nio.file.Path;
import java.time.Clock;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

@Component
public final class ProbeEvidence {
    private static final DateTimeFormatter STAMP =
            DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC);
    private static final Logger log = LoggerFactory.getLogger(ProbeEvidence.class);

    private final Path directory;
    private final Clock clock;

    public ProbeEvidence(ProbeSettings settings, Clock clock) {
        this.directory = settings.evidenceDir();
        this.clock = clock;
    }

    public Page recordedPage(Browser browser, String baseUrl) {
        BrowserContext context = browser.newContext(new Browser.NewContextOptions()
                .setBaseURL(baseUrl)
                .setRecordVideoDir(directory.resolve("raw-videos")));
        context.tracing().start(new Tracing.StartOptions().setScreenshots(true).setSnapshots(true));
        return context.newPage();
    }

    public void keep(String check, boolean passed, Page page) {
        String name = check + "." + STAMP.format(clock.instant());
        BrowserContext context = page.context();
        Video video = page.video();
        if (passed) {
            context.tracing().stop();
        } else {
            keepScreenshot(page, name);
            context.tracing().stop(new Tracing.StopOptions().setPath(file(name, "zip")));
        }
        context.close();
        if (!passed) {
            video.saveAs(file(name, "webm"));
            log.warn("Synthetic {} failed; evidence kept as {}.png, .zip and .webm in {}", check, name, directory);
        }
        video.delete();
    }

    private void keepScreenshot(Page page, String name) {
        try {
            page.screenshot(new Page.ScreenshotOptions().setPath(file(name, "png")).setFullPage(true));
        } catch (PlaywrightException e) {
            log.warn("Screenshot not captured for {}: {}", name, e.getMessage());
        }
    }

    private Path file(String name, String extension) {
        return directory.resolve(name + "." + extension);
    }
}
```

- `directory` comes from `ProbeSettings.evidenceDir()`, bound from `SYNTHETIC_EVIDENCE_DIR`: a private volume
  with a 14-day lifecycle (`qa/cicd/ci-conventions`' evidence retention). Never a public bucket and never the
  image's writable layer — a restarted pod loses it.
- `raw-videos/` is scratch: every run's recording lands there and `video.delete()` removes it.
- `context.close()` writes the video; Java's `saveAs` throws until it has (`lifecycle.md` §5).
- A probe keeps no Allure attachment — there is no report. The log line and the alert annotation are how
  on-call finds the files; the trace opens with `npx playwright@1.63.0 trace open <zip>` or at
  trace.playwright.dev, which loads it in the browser without uploading it.
- `ProbeSettings` is the probe's `@ConfigurationProperties` record: `baseUrl`, `syntheticUser` (a `Credentials`
  record read from env), `evidenceDir`.

## `SyntheticMetrics` — the Prometheus metrics Grafana alerts on

```java
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
        registry.timer("synthetic_check_duration", "check", check).record(d);
    }
}
```

`synthetic_check_success` is the gauge the alert fires on; `synthetic_check_duration` is the latency it gates on.

## Alert rules

`monitoring/infra/checks.tf` — alert when the storefront synthetic fails, page via the contact point. `A` is the
query (`min_over_time(probe_success{job="storefront-health"}[5m])`), `C` the threshold (`A < 1` fires); the
reduce step is abbreviated. `for = "5m"` requires a sustained failure before paging.

```hcl
resource "grafana_rule_group" "synthetic_alerts" {
  name             = "production-uptime-checks"
  folder_uid       = grafana_folder.monitoring.uid
  interval_seconds = 60

  rule {
    name        = "Storefront synthetic down or slow"
    condition   = "C"
    data { ref_id = "A" }
    data { ref_id = "C" }
    for         = "5m"
    annotations = { summary = "storefront synthetic failing" }
    labels      = { severity = "critical" }
  }
}
```

Route the firing alert with a **contact point** (email / Slack / PagerDuty) — `grafana_contact_point` +
`grafana_notification_policy`, also as Terraform. A second rule on `probe_http_duration_seconds` /
`synthetic_check_duration` over the latency budget catches **slow-but-up** (the canonical's
`degradedResponseTime`). For the Java probe, add `absent_over_time(synthetic_check_success{check="checkout-journey"}[30m])`
so a probe app that stopped scheduling pages too.

## Secrets from env, never logged

The Grafana SM access token, target URLs and test-user credentials come from env / a secret store — read
lazily, never committed, never logged. Terraform reads the token from `TF_VAR_grafana_sm_access_token` in the CI
secret store:

```hcl
provider "grafana" {
  sm_access_token = var.grafana_sm_access_token
}
```

The probe's `ProbeSettings.syntheticUser()` reads `SYNTHETIC_USER` / `SYNTHETIC_PASSWORD` when the journey runs,
not at startup, and never logs them. The trace and video the probe keeps contain that user's session, which is
why the user is a dedicated synthetic account and the evidence volume is private.

## Worked example

**A cheap HTTP probe check + a Java-native journey probe, both alerting through one contact point.**
`checks.tf` declares the `storefront_health` HTTP check (multi-region, status + content match, emitting
`probe_http_duration_seconds`). `CheckoutJourneyProbe` runs every 15 minutes, reusing the CI suite's `LoginPage`
and `CartPage`, and publishes `synthetic_check_success` / `synthetic_check_duration`. One `grafana_rule_group`
alerts on both (`for = "5m"`) and routes to the on-call contact point.

At 03:10 the cart badge stops updating. The 03:15 run's `assertThat(cart.itemCount()).hasText("1")` times out
with an `AssertionFailedError`; the probe logs it, records `0`, and keeps
`checkout-journey.20261011T031500Z.{png,zip,webm}`. By 03:20 the rule has seen five minutes of failure and pages
on-call, who opens the trace: the add-to-cart request returned `503`. No rerun was needed to see it.
