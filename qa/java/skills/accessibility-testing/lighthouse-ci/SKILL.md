---
name: qa-accessibility-testing-lighthouse-ci-java
description: >-
  Full-page Lighthouse audits (accessibility **+** performance + SEO + PWA + best-practices) gated on a
  numeric **score threshold** from a Java / TestNG pipeline. Lighthouse is a Node tool with **no native
  Java SDK**, so this skill invokes the CLI — `npx lhci autorun` (driven by `lighthouserc`) as a pipeline
  step for URL-list page audits, and `npx lighthouse <url> --output=json` shelled out from a test via
  `ProcessBuilder` (then parse `categories.*.score` with Jackson and `assertThat(score).isGreaterThanOrEqualTo(0.9)`)
  to audit a page a Playwright Java test already drove to a state. Use when a build must fail because
  `categories.accessibility` (or seo / best-practices / performance) dropped below a threshold, to trend a
  whole-page a11y score, or to run a broad audit alongside the per-component axe gate. Covers
  `ci.collect`/`ci.assert`/`ci.upload`, `minScore`, `numberOfRuns` + median for perf variance,
  `temporary-public-storage` (no API key), and the report-into-Allure attachment. Do NOT use for:
  per-component rule-based WCAG `getViolations()` assertions inside the E2E run (see
  qa-accessibility-testing-axe-playwright-java), the page objects/specs the audit reuses (see
  qa-ui-test-author-playwright-java), TypeScript (see qa-accessibility-testing-lighthouse-ci-typescript),
  or .NET (see qa-accessibility-testing-lighthouse-ci-dotnet).
---

# Accessibility Testing — Lighthouse CI (Java / TestNG)

The Java port of the canonical `qa-accessibility-testing-lighthouse-ci-typescript`. Same Lighthouse
auditing model, same score-threshold gate, same perf-variance discipline — re-expressed for a JVM shop,
which forces the honest shape of this node.

Lighthouse is Google's headless-Chrome auditing tool; **Lighthouse CI** runs it as a gated step that
produces a **category score** (0–1) for `performance`, `accessibility`, `best-practices`, `seo`, and
`pwa`, and **fails the build when a score drops below a threshold**. This is the **broad-audit +
score-trend** sibling of `qa-accessibility-testing-axe-playwright-java`: where axe gives you
per-component `getViolations()` to assert empty **inside** your functional E2E run, Lighthouse runs a
**separate full-page pass** and gives you one number per category to gate and trend. Run both.

> **Lighthouse a11y is axe-powered — but reported as a *score*, not as `getViolations()`.** Under the
> hood Lighthouse's accessibility category runs axe-core, yet it surfaces the result as
> `categories.accessibility.score` (a 0–1 number derived from weighted audit pass/fail), **not** as an
> assertable list of failing nodes. That is exactly why you run both: axe-playwright (#20) gives you the
> per-element rule id + selector to *fix*; Lighthouse CI gives you the whole-page *trend* and the
> perf/SEO/PWA context axe doesn't cover. A Lighthouse a11y score is still the automated **floor**
> (~30–40% of WCAG) — pair with manual + assistive-tech testing (`qa-exploratory-charter-writer`).

> **⚠️ Node-only tool — the defining nuance of this node.** Lighthouse is a **Node** tool. **There is no
> native Java Lighthouse SDK and no Maven/Gradle artifact.** So unlike axe-playwright (#20), where
> `com.deque.html.axe-core:playwright` was a first-class Java binding, here Java is a **thinner,
> CLI-driven** stack: you **invoke the Lighthouse/lhci CLI as a subprocess** (`ProcessBuilder` →
> `npx lhci autorun` / `npx lighthouse <url> --output=json`) and **parse the JSON report**
> (`categories.*.score`, with Jackson) to gate the pipeline. The structure (collect → assert on score →
> report) ports from the TS canonical; the *invocation* is a `Process`, not an SDK call. Say this plainly
> to anyone reaching for a dependency — there isn't one.

## Decision matrix — Lighthouse CI vs axe-playwright

The inverse of the matrix in `qa-accessibility-testing-axe-playwright-java`:

| Need | Use | Why |
|------|-----|-----|
| A full-page audit (a11y **+** performance + SEO + PWA + best-practices) gated on a numeric **score** | **this skill** | One score per category; one threshold per category; trends over time; covers more than a11y |
| Rule-based DOM a11y **assertions** (gate on `getViolations()` empty), per component, **inside** the E2E run | axe-playwright (#20) | Names the exact rule id + failing selector + fix; fails fast in the same job; free, deterministic |
| One number to **trend** accessibility (and perf/SEO) over time across whole pages | **this skill** | The category score is a trend metric; axe is binary pass/fail |
| Per-element WCAG conformance evidence (rule id + selector + helpUrl) to hand a dev | axe-playwright (#20) | Lighthouse reports a score, not assertable per-node failures |
| Catch a **performance / SEO / PWA** regression, not just a11y | **this skill** | axe is a11y-only; Lighthouse audits five categories in one pass |

**Rule of thumb:** axe-playwright is your **per-component assertion gate inside the E2E run**; Lighthouse
CI is your **broad full-page audit + numeric score gate + trend**. Many teams run both.

## Setup

There is no Maven/Gradle Lighthouse artifact — Lighthouse runs via Node. Your CI image needs Node +
Chrome; install the CLI once per job:

```bash
npm install --save-dev @lhci/cli      # the CI runner: collect → assert → upload (language-agnostic)
# stateful-page audits shell out to: npx lighthouse <url> --output=json
```

Your test project just needs Playwright + TestNG + AssertJ + a JSON parser (Jackson):

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("com.microsoft.playwright:playwright:1.50.0")
    testImplementation("org.testng:testng:7.+")
    testImplementation("org.assertj:assertj-core:3.+")
    testImplementation("com.fasterxml.jackson.core:jackson-databind:2.+")
}
```

`@lhci/cli` needs no API key for the default `temporary-public-storage` upload target. The only optional
secret is an **LHCI-server token** (`LHCI_TOKEN`) — read it lazily from the environment, never commit it.

## The Lighthouse model — category scores, not a violations list

A Lighthouse run loads a URL in headless Chrome and produces five **category scores** in `[0, 1]`:
`categories.performance.score`, `categories.accessibility.score`, `categories.best-practices.score`,
`categories.seo.score`, `categories.pwa.score`. Each is a **weighted aggregate of individual `audits`**
(e.g. `color-contrast`, `image-alt`, `first-contentful-paint`). The **gate is a threshold per category**
(`minScore`) — **not** a pass/fail list of DOM violations (that's #20's axe).

Two ways to run it from a Java pipeline — cover both:

1. **`lhci autorun` + `lighthouserc`** — a **language-agnostic** CI step that audits a list of URLs and
   gates on score. The same `lighthouserc` as the TS canonical; Java doesn't change it.
2. **Shell out to `npx lighthouse` from a test** — drive a **stateful page** with Playwright Java, then
   run Lighthouse against the page's debugging port, parse the JSON, and assert the score in TestNG.

## `lhci autorun` + `lighthouserc` — the URL-list CI gate (language-agnostic)

`lhci autorun` does **collect** (run Lighthouse N times per URL, keep the median), **assert** (apply your
score thresholds — the build-fail mechanism), and **upload** (store the report), all from one CLI command
your Gradle/CI pipeline calls. The config is identical to the TS canonical — Java doesn't own it, the CLI
does:

```js
// lighthouserc.cjs
module.exports = {
  ci: {
    collect: {
      startServerCommand: './gradlew bootRun',          // boot YOUR app (any stack)
      url: ['http://localhost:8080/', 'http://localhost:8080/checkout'],
      numberOfRuns: 3,                 // ≥3 and take the median — fights Lighthouse perf variance
    },
    assert: {
      assertions: {
        'categories:accessibility':   ['error', { minScore: 0.9 }],   // deterministic → fail build
        'categories:seo':             ['error', { minScore: 0.9 }],
        'categories:best-practices':  ['error', { minScore: 0.9 }],
        'categories:performance':     ['warn',  { minScore: 0.8 }],    // noisy → report only
        'color-contrast':             ['error', { minScore: 1 }],      // per-audit assertion
      },
    },
    upload: {
      target: 'temporary-public-storage',   // free, no API key — public link, kept a few days
      // target: 'lhci', serverBaseUrl: process.env.LHCI_SERVER_URL, token: process.env.LHCI_TOKEN,
    },
  },
};
```

```bash
npx lhci autorun --config=lighthouserc.cjs
```

`'categories:<name>': [level, { minScore }]` where `level` is `'error'` (fail build) or `'warn'` (report
only). This is the same gate as the TS canonical — reach for it whenever you're auditing public URLs.

## Shelling out to `npx lighthouse` — auditing a stateful page driven by Playwright Java

For authenticated/stateful pages, drive the app with the page objects the
`qa-ui-test-author-playwright-java` skill already authored, then run Lighthouse against the page's
**remote-debugging port** and assert the parsed score. Launch Chromium with the port, drive to state,
then shell out via `ProcessBuilder`:

```java
// support/Lighthouse.java — the CLI-port helper: subprocess + JSON parse (no SDK exists)
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.nio.file.Files;
import java.util.concurrent.TimeUnit;

public final class Lighthouse {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private Lighthouse() {}

    /** Runs `npx lighthouse` against an already-open Chrome on {@code port}, parses the JSON report. */
    public static LighthouseReport audit(String url, int port) throws Exception {
        File out = File.createTempFile("lh-", ".json");
        Process proc = new ProcessBuilder(
                "npx", "lighthouse", url,
                "--output=json", "--output-path=" + out.getAbsolutePath(),
                "--port=" + port, "--quiet",
                "--only-categories=accessibility,seo,best-practices,performance")
            .redirectErrorStream(true)
            .start();
        boolean finished = proc.waitFor(120, TimeUnit.SECONDS);   // bounded wait, not Thread.sleep
        if (!finished) { proc.destroyForcibly(); throw new IllegalStateException("lighthouse timed out"); }
        if (proc.exitValue() != 0)
            throw new IllegalStateException("lighthouse exited " + proc.exitValue()
                + ": " + new String(proc.getInputStream().readAllBytes()));

        JsonNode root = MAPPER.readTree(Files.readAllBytes(out.toPath()));
        return new LighthouseReport(root);
    }

    public record LighthouseReport(JsonNode root) {
        /** The 0–1 score for a category, e.g. "accessibility", "performance", "seo". */
        public double categoryScore(String category) {
            return root.path("categories").path(category).path("score").asDouble();
        }
    }
}
```

```java
// tests/DashboardLighthouseTest.java
import com.microsoft.playwright.*;
import java.util.List;
import org.testng.annotations.Test;
import static org.assertj.core.api.Assertions.assertThat;

public class DashboardLighthouseTest {
    private static final int PORT = 9222;

    @Test
    public void Should_meet_a11y_score_When_dashboard_loaded_for_signed_in_user() throws Exception {
        try (Playwright pw = Playwright.create()) {
            // The debugging port Lighthouse attaches to.
            Browser browser = pw.chromium().launch(new BrowserType.LaunchOptions()
                .setArgs(List.of("--remote-debugging-port=" + PORT)));
            Page page = browser.newPage();

            DashboardPage dashboard = new DashboardPage(page);
            dashboard.gotoAsSignedInUser();            // page-object intent reused from #20's skill
            dashboard.waitUntilReady();                // stabilize on a CONDITION, never Thread.sleep/waitForTimeout

            var report = Lighthouse.audit("http://localhost:8080/dashboard", PORT);

            assertThat(report.categoryScore("accessibility")).isGreaterThanOrEqualTo(0.9);  // the gate
            browser.close();
        }
    }
}
```

> **Scale note:** Lighthouse JSON `categories.*.score` is **0–1** (assert `>= 0.9`). The TS
> `playwright-lighthouse` `thresholds` are 0–100; you're parsing raw Lighthouse JSON here, so it's 0–1.

## Perf variance discipline — median the noise, gate the deterministic categories

Lighthouse **performance** scores are **noisy** (CPU contention, network jitter, cold caches). The a11y,
SEO, and best-practices categories are **deterministic** (a11y is axe-powered rule checks). So:

- **`numberOfRuns: 3`+ and median** in `lighthouserc`; for the shell-out path, audit a stable page and
  don't hard-gate a single cold run's perf number — assert perf with a margin or trend it instead.
- **`'error'` on a11y / SEO / best-practices** (deterministic — a regression is real); **`'warn'` on
  performance** (noisy — a hard-fail on a flaky number trains the team to ignore the gate).
- Stabilize the page on a **condition** before auditing (`Locator.waitFor`, spinner hidden), never a
  fixed `Thread.sleep` / `page.waitForTimeout` — a half-loaded page tanks the score for the wrong reason.

## Reporting the gate — Lighthouse report into Allure + CI artifact

`lhci autorun` writes reports under `.lighthouseci/` (HTML + JSON + `manifest.json` naming the median
run) and prints a public report URL with `temporary-public-storage`. The shell-out path writes the JSON
you parsed. Attach it to Allure so a failing gate names the dropped category without re-running
(cross-link `qa-allure-reporting-java`):

```java
// support/LighthouseReportAttachment.java
import io.qameta.allure.Allure;
import java.io.ByteArrayInputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public final class LighthouseReportAttachment {
    private LighthouseReportAttachment() {}

    public static void attach(Path jsonPath) throws Exception {
        Allure.addAttachment("lighthouse-report.json", "application/json",
            new ByteArrayInputStream(Files.readAllBytes(jsonPath)), ".json");
    }
}
```

- **Allure** — attach the HTML + JSON report so a failing gate names the dropped category and failing
  audits without anyone re-running locally.
- **CI artifact** — upload `.lighthouseci/` as a build artifact (cross-link
  `qa-ci-pipelines-github-actions-java`); the Java pipeline calls the same Node CLI.
- **Status check** — the LHCI GitHub App posts a status check linking the report; with
  `temporary-public-storage` the report URL is in the job log.

**No API key required** for `temporary-public-storage` — same "no secret" theme as #20 (axe). The only
secret is an optional `LHCI_TOKEN` for a private LHCI server, read lazily from the environment, never
logged or committed.

## Anti-patterns

- **Looking for a Maven/Gradle Lighthouse SDK.** There isn't one — Lighthouse is Node-only. *Fix:* shell
  out via `ProcessBuilder` to `npx lighthouse` / `npx lhci autorun` and parse the JSON with Jackson.
- **Hard-`error` gating the performance score.** Perf is noisy. *Fix:* `'warn'` on performance, `'error'`
  on the deterministic categories; trend perf.
- **`numberOfRuns: 1`.** A single run rides the variance. *Fix:* `numberOfRuns: 3`+ and median.
- **`Thread.sleep` / `page.waitForTimeout` before the audit.** Violates the global rules and races the
  DOM. *Fix:* `proc.waitFor(timeout, unit)` for the subprocess; stabilize on a condition
  (`Locator.waitFor`) for the page.
- **Running multiple audits concurrently on one debugging port.** They collide. *Fix:* keep the
  Lighthouse tests in a single thread group (TestNG `@Test(singleThreaded = true)` / a non-parallel
  suite) or use distinct ports.
- **Treating a 1.0 a11y score as "accessible."** Lighthouse a11y is axe-powered → ~30–40% automated
  floor. *Fix:* pair with manual + assistive-tech testing; run axe-playwright (#20) for assertable
  per-node fixes.
- **Committing an `LHCI_TOKEN`.** *Fix:* env var, read lazily; `temporary-public-storage` needs no key.

## Examples

**End-to-end: `lhci autorun` gating public pages, plus a Playwright Java shell-out for an authenticated
page.**

```js
// lighthouserc.cjs — the public-pages CI gate (language-agnostic; the Java pipeline calls the CLI)
module.exports = {
  ci: {
    collect: { startServerCommand: './gradlew bootRun', url: ['http://localhost:8080/', 'http://localhost:8080/pricing'], numberOfRuns: 3 },
    assert: { assertions: {
      'categories:accessibility':  ['error', { minScore: 0.9 }],
      'categories:seo':            ['error', { minScore: 0.9 }],
      'categories:best-practices': ['error', { minScore: 0.9 }],
      'categories:performance':    ['warn',  { minScore: 0.8 }],
    } },
    upload: { target: 'temporary-public-storage' },
  },
};
```

```java
// tests/AccountLighthouseTest.java — the authenticated-page gate (reuses #20's page objects)
import com.microsoft.playwright.*;
import java.util.List;
import org.testng.annotations.Test;
import static org.assertj.core.api.Assertions.assertThat;

public class AccountLighthouseTest {
    private static final int PORT = 9222;

    @Test
    public void Should_meet_a11y_and_seo_scores_When_account_page_loaded() throws Exception {
        try (Playwright pw = Playwright.create()) {
            Browser browser = pw.chromium().launch(new BrowserType.LaunchOptions()
                .setArgs(List.of("--remote-debugging-port=" + PORT)));
            Page page = browser.newPage();

            AccountPage account = new AccountPage(page);
            account.gotoAsSignedInUser();              // intent, not selectors
            account.waitUntilReady();                  // condition, not sleep

            var report = Lighthouse.audit("http://localhost:8080/account", PORT);

            assertThat(report.categoryScore("accessibility")).isGreaterThanOrEqualTo(0.9);
            assertThat(report.categoryScore("seo")).isGreaterThanOrEqualTo(0.9);   // one logical gate: scores meet thresholds
            browser.close();
        }
    }
}
```

Lifecycle for this gate:
1. A dev ships a redesign that drops color contrast on the pricing page and removes a `<main>` landmark.
2. CI runs `lhci autorun`; Lighthouse audits each URL 3× and medians the result.
3. `categories.accessibility.score` falls below `0.9` → the assertion fails → **the build fails**, with
   the dropped category and failing audits in the uploaded report (linked from the status check / job
   log, and attached to Allure).
4. The dev fixes contrast + the landmark; the score climbs back over the threshold; the gate goes green.
   Perf stays a `warn` and is trended rather than hard-failing the PR.

## Rules (hard constraints)

- **No native Java SDK** — invoke the Lighthouse/lhci CLI via `ProcessBuilder` and parse
  `categories.*.score` from the JSON with Jackson. The gate is a **score threshold per category**
  (`minScore` / `isGreaterThanOrEqualTo`), one logical assertion per category under test. Test names
  `Should_X_When_Y`.
- `'error'` (hard-fail) on the **deterministic** categories (accessibility / SEO / best-practices);
  `'warn'` on the **noisy** performance category — trend perf, don't hard-gate a flaky run.
- `numberOfRuns` ≥ 3 and take the **median**.
- Shell-out audits reuse existing page objects (intent, not selectors); stabilize on a **condition**
  before auditing, never `Thread.sleep`/`waitForTimeout`; bound the subprocess wait (`proc.waitFor`);
  single-thread tests sharing a debugging port.
- Lighthouse JSON `categories.*.score` is **0–1** (assert `>= 0.9`).
- **No API key** for `temporary-public-storage` (contrast #18 `PERCY_TOKEN` / #19 `APPLITOOLS_API_KEY`);
  an optional `LHCI_TOKEN` for a private server is the only secret — env, lazy, never logged.
- A Lighthouse a11y score is axe-powered = the automated **floor** (~30–40% of WCAG), not proof. Pair
  with manual + assistive-tech testing, and run axe-playwright (#20) for assertable per-node fixes.

## Cross-references

- `qa-accessibility-testing-lighthouse-ci-typescript` — the **canonical** skill, TS (first-class
  `@lhci/cli` + `playwright-lighthouse`). This Java sibling is the CLI-driven port of it.
- `qa-accessibility-testing-lighthouse-ci-dotnet` — same skill, .NET / NUnit. Same CLI-port shape
  (`Process` + `System.Text.Json`).
- `qa-accessibility-testing-axe-playwright-java` (#20) — the **per-component assertion** sibling: gate on
  `getViolations()` empty **inside** the E2E run (`com.deque.html.axe-core:playwright`, a real artifact).
  Run both — axe to *fix* nodes, Lighthouse to *trend* whole-page scores + gate perf/SEO/PWA.
- `qa-ui-test-author-playwright-java` — the page objects the shell-out audit reuses to reach a stateful
  page. Author the flow there; add the audit here.
- `qa-ci-pipelines-github-actions-java` — the `lhci autorun` job (the Java pipeline calls the Node CLI),
  artifact upload, and LHCI status check.
- `qa-allure-reporting-java` — attach the Lighthouse HTML + JSON report to the run.
- `qa-exploratory-charter-writer` — the manual/assistive-tech testing that covers the ~60% no automated
  a11y score can.
