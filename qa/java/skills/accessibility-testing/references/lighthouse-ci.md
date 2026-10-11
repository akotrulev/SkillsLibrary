# Accessibility Testing — Lighthouse (Java / Playwright 1.63 + TestNG)

Lighthouse is Google's Chrome auditor. It scores a page per **category** — `accessibility`,
`best-practices`, `seo`, `performance` — from 0 to 1, and a gate fails when a score drops below its
threshold. It is the **broad-audit and trend** sibling of `references/axe-playwright.md`: axe asserts the
exact failing rules **inside** the functional run; Lighthouse runs a separate full-page pass and gives one
number per category. Its accessibility category runs axe-core underneath, so a perfect score is still the
automated floor, not proof.

> **Lighthouse is a Node tool.** There is no Maven or Gradle Lighthouse artifact. Java runs it as a
> subprocess (`npx lighthouse`) or as a pipeline step (`lhci autorun`) and parses the JSON report.

> **Public pages only — the limitation of this lane.** Lighthouse audits in **its own tab, in the browser's
> default context**. A Playwright test's page lives in a separate, isolated context (the one `BaseTest`
> opens), so a signed-in state there is not what Lighthouse sees, and Lighthouse resets the origin's storage
> before it audits. A Java test therefore audits only pages an anonymous visitor can open. A signed-in page
> gets an axe scan here (`references/axe-playwright.md`); a Lighthouse score for it needs Lighthouse's own
> authentication (a Puppeteer login script in `lhci`, or `--extra-headers` with a token) or the TypeScript
> lane's `playAudit` on a persistent context — both outside this skill.

## 1. Setup

Node 24 on the runner, plus the two CLIs as exact dev dependencies in the repository's `package.json`
(checked on npm on 2026-10-11):

```bash
npm install --save-dev --save-exact @lhci/cli@0.15.1 lighthouse@13.5.0
```

`@lhci/cli` needs no key for the `temporary-public-storage` upload target. The only optional secret is an
LHCI-server token (`LHCI_TOKEN`) — from the secret store, never committed or logged. The PWA category was
removed in Lighthouse 12; never configure or assert it.

## 2. Two ways to run it

| Way | What it audits | Gate |
|---|---|---|
| `lhci autorun` with `lighthouserc.cjs` (§3) | A list of public URLs, each run three times, median kept | `lhci`'s assertions; a pipeline step |
| A TestNG test that runs `npx lighthouse` against `BaseTest`'s browser (§4) | One public page per test, reported in TestNG and Allure | AssertJ on the parsed scores |

The first is the default: it needs no Java at all. Use the second when the score belongs in the test report
beside the suite's other results.

## 3. `lhci autorun` — the URL-list gate

```js
module.exports = {
  ci: {
    collect: {
      url: [`${process.env.BASE_URL}/`, `${process.env.BASE_URL}/pricing`],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.9 }],
        'categories:performance': ['warn', { minScore: 0.8 }],
        'color-contrast': ['error', { minScore: 1 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
```

```bash
npx lhci autorun --config=lighthouserc.cjs
```

- `'categories:<name>': [level, { minScore }]` — `error` fails the step, `warn` reports only. An audit id
  (`color-contrast`) can be asserted on its own.
- `numberOfRuns: 3` and the median fight Lighthouse's variance.
- `BASE_URL` is the deployed test environment the UI job already uses; `lhci` launches its own Chrome, found
  through `CHROME_PATH` when it is not on the default path.

## 4. A Lighthouse test on `BaseTest`'s browser

Lighthouse attaches to a running Chromium through a remote-debugging port. The test class adds that port
through `launchOptions()` — the one launch hook `BaseTest` offers — so Lighthouse audits with the Playwright
1.63 Chromium the suite already installed, and no second browser is launched.

```java
package com.example.uitests.support;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;

import java.io.IOException;
import java.io.InputStream;
import java.net.ServerSocket;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;
import java.util.stream.Collectors;

public final class Lighthouse {
    public static final List<String> GATED_CATEGORIES = List.of("accessibility", "best-practices", "seo");
    private static final Path ARTIFACTS = Path.of("build", "playwright-artifacts");
    private static final long AUDIT_TIMEOUT_SECONDS = 120;

    private Lighthouse() {
    }

    public static int freePort() throws IOException {
        try (ServerSocket socket = new ServerSocket(0)) {
            return socket.getLocalPort();
        }
    }

    public static Map<String, Double> audit(String url, int port, String evidenceName) throws IOException, InterruptedException {
        Files.createDirectories(ARTIFACTS);
        Path report = ARTIFACTS.resolve(evidenceName + ".lighthouse.json");
        Path log = ARTIFACTS.resolve(evidenceName + ".lighthouse.log");
        Process lighthouse = new ProcessBuilder(
                "npx", "--no-install", "lighthouse", url,
                "--port=" + port,
                "--only-categories=" + String.join(",", GATED_CATEGORIES),
                "--output=json", "--output-path=" + report,
                "--quiet")
                .redirectErrorStream(true)
                .redirectOutput(log.toFile())
                .start();
        if (!lighthouse.waitFor(AUDIT_TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
            lighthouse.destroyForcibly();
            throw new IllegalStateException("Lighthouse did not finish within " + AUDIT_TIMEOUT_SECONDS + " s; log: " + log);
        }
        if (lighthouse.exitValue() != 0) {
            throw new IllegalStateException("Lighthouse exited " + lighthouse.exitValue() + "; log: " + log);
        }
        try (InputStream content = Files.newInputStream(report)) {
            Allure.attachment("lighthouse-report", "application/json", content, AttachmentOptions.withFileExtension("json"));
        }
        JsonObject categories = JsonParser.parseString(Files.readString(report)).getAsJsonObject().getAsJsonObject("categories");
        return GATED_CATEGORIES.stream().collect(Collectors.toMap(
                Function.identity(), category -> categories.getAsJsonObject(category).get("score").getAsDouble()));
    }
}
```

```java
package com.example.uitests.tests;

import com.example.uitests.support.BaseTest;
import com.example.uitests.support.Lighthouse;
import com.microsoft.playwright.BrowserType;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.io.IOException;
import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

public class PricingLighthouseTest extends BaseTest {
    private final int debuggingPort;
    private String evidenceName;

    public PricingLighthouseTest() throws IOException {
        debuggingPort = Lighthouse.freePort();
    }

    @Override
    protected BrowserType.LaunchOptions launchOptions() {
        return new BrowserType.LaunchOptions().setArgs(List.of("--remote-debugging-port=" + debuggingPort));
    }

    @BeforeMethod(alwaysRun = true)
    public void nameEvidence(Method method) {
        evidenceName = getClass().getSimpleName() + "." + method.getName();
    }

    @Test(groups = "lighthouse")
    public void Should_ScoreAtLeast90InEveryGatedCategory_When_PricingIsAudited() throws IOException, InterruptedException {
        Map<String, Double> scores = Lighthouse.audit(requiredEnv("BASE_URL") + "/pricing", debuggingPort, evidenceName);

        assertThat(scores).as("Lighthouse scores of the public pricing page")
                .allSatisfy((category, score) -> assertThat(score).as(category).isGreaterThanOrEqualTo(0.9));
    }
}
```

- **The port is per class.** `freePort()` asks the OS for a free port when TestNG builds the class instance;
  `BaseTest.launchBrowser` then launches the class's Chromium with it. Classes run in parallel on different
  ports — a fixed `9222` makes two classes collide. The OS can hand the port to someone else between the
  check and the launch; the window is short, and a collision fails the launch loudly.
- **The test's own context is unused.** `BaseTest` still opens one per test (and keeps its evidence on
  failure); Lighthouse opens its own tab. That is why this lane audits public pages only.
- **Every gated category is one assertion.** `allSatisfy` checks accessibility, best-practices and SEO
  against 0.9 and reports every category that missed; performance is not gated here (§5). Scores are
  **0–1** in the JSON report (the TS `playwright-lighthouse` thresholds are 0–100).
- **The subprocess has a bounded wait** — `waitFor(timeout)` is a deadline, not a sleep — and its output goes
  to `build/playwright-artifacts/<Class>.<method>.lighthouse.log`, beside the JSON report, so a failure
  names the log. Redirecting the output to a file also keeps a full pipe from blocking the process.
- `npx --no-install` runs the pinned `lighthouse` from `node_modules` and never downloads another version.
- The JSON is parsed with Gson, which Playwright for Java already exposes in its API (`CDPSession` returns
  `JsonObject`), so no JSON library is added.
- Lighthouse classes carry `groups = "lighthouse"` and, like visual tests, run outside the PR gate: exclude
  the group from `test` and give it its own `Test` task, as `qa/java/skills/visual-regression`'s
  `references/playwright-snapshots.md` §1 does for `visual`.

## 5. Performance variance

Performance scores are noisy — CPU contention, network jitter, cold caches — and parallel classes make them
noisier. Accessibility, best-practices and SEO are deterministic rule checks.

- `error` on the deterministic categories, `warn` on performance in `lhci`; the TestNG test does not audit
  performance at all.
- `numberOfRuns: 3` and the median in `lhci`; a single cold run is never a performance gate.
- Audit a page that is fully served, never after a sleep.

## 6. Reporting

- **Allure** — the TestNG test attaches the JSON report (`lighthouse-report`) before it asserts.
- **CI artifact** — `lhci autorun` writes `.lighthouseci/` (HTML, JSON, `manifest.json`); upload it from
  the step (`qa/cicd/java/skills/ci-pipelines`). The TestNG test's report and log are already in
  `build/playwright-artifacts/`, which the UI job uploads on failure.
- **Status check** — the LHCI GitHub App posts one linking the report; with `temporary-public-storage` the
  report URL is in the job log.

## Anti-patterns

- **Looking for a Maven or Gradle Lighthouse SDK.** There is none. *Fix:* `lhci autorun`, or §4's subprocess.
- **Auditing a signed-in page from a Playwright context.** Lighthouse audits its own tab; the score is the
  signed-out page's. *Fix:* public pages only here; axe for the signed-in ones.
- **`try (Playwright playwright = Playwright.create())` in a test, or a second browser.** *Fix:* extend
  `BaseTest`; add the port through `launchOptions()`.
- **A fixed debugging port.** Parallel classes collide. *Fix:* `freePort()` per class.
- **A hard-coded `http://localhost:8080`.** *Fix:* `BASE_URL`.
- **Hard-gating performance.** *Fix:* `warn` and trend it.
- **The `pwa` category.** Removed in Lighthouse 12.
- **`Thread.sleep` before the audit, or an unbounded `waitFor()`.** *Fix:* a fully served page; a deadline.
- **Committing `LHCI_TOKEN`.**

## Rules

- Lighthouse audits public pages only in this lane, and the reference says so.
- `@lhci/cli@0.15.1` and `lighthouse@13.5.0`, exact dev dependencies; Node 24.
- The URL-list gate is `lhci autorun`; a TestNG audit extends `BaseTest`, adds the port through
  `launchOptions()`, and bounds the subprocess.
- Gate accessibility, best-practices and SEO (`≥ 0.9`); warn on performance; no PWA.
- Scores are 0–1; one `allSatisfy` assertion per audited page, with `.as(...)`.
- Reports are attached with `Allure.attachment(..., AttachmentOptions)` and kept in `build/playwright-artifacts/`.

## Cross-references

- `references/axe-playwright.md` — the per-component gate, and the tool for signed-in pages.
- `qa/java/skills/ui-test-author/playwright` — `BaseTest` and its `launchOptions()` hook.
- `qa/cicd/java/skills/ci-pipelines` — the `lhci autorun` step and artifact upload.
- `qa-typescript:accessibility-testing` — `playAudit` on a persistent context, for signed-in pages.
- `qa-dotnet:accessibility-testing` — the .NET sibling.
- `qa-<stack>:exploratory-charter-writer` — the manual and assistive-technology testing no score covers.
