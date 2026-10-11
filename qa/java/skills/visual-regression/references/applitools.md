# Visual Regression — Applitools Eyes (Java / Playwright 1.63 + TestNG)

Applitools Eyes uploads the page to the **Ultrafast Grid**, re-renders it server-side across a configured
browser, viewport and device matrix, and compares each render with **visual AI** that ignores anti-aliasing
and sub-pixel noise. **Match levels** (Strict, Layout, Content) decide how strictly a region is compared.
That control is what Percy's pixel diff and the comparator lane lack. Baselines live in the Applitools
dashboard; a person accepts or rejects differences there.

The Java SDK is `com.applitools:eyes-playwright-java5`. An Eyes class extends
`com.example.uitests.support.BaseTest` (`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`) and
adds `eyes.check(...)` to a flow the page objects drive.

## Why graduate from Percy to Applitools

| | Percy | **Applitools Eyes** |
|---|---|---|
| What leaves the test | A DOM snapshot, through the `percy exec` agent | The page, uploaded by the **SDK itself** — no agent |
| How the diff is judged | Server-side **pixel** diff | Server-side **visual AI** |
| Tolerance lever | `percyCSS` hide and `scope` | **Match levels** per region, plus ignore and floating regions |
| Dynamic content | Hide it | **`layout(locator)`** — the structure must match, the text may change |
| Browsers and devices | Re-rendered at configured widths | **Ultrafast Grid** — a real browser/viewport/device matrix from one run |
| Gate | A status check | The runner's results fail the run; the dashboard holds the review |
| Cost | Paid | Paid, usually the most expensive |

## 1. Setup

Checked on Maven Central on 2026-10-11:

```kotlin
dependencies {
    testImplementation("com.applitools:eyes-playwright-java5:5.86.9")
}
```

No agent to launch. `APPLITOOLS_API_KEY` is the **only** secret; the SDK reads it from the environment. It
comes from the CI secret store and is never committed or logged.

## 2. The model

- **`VisualGridRunner`** (`com.applitools.eyes.playwright.visualgrid`) ships checkpoints to the Ultrafast
  Grid: `new VisualGridRunner(new RunnerOptions().testConcurrency(5))`. Its sibling `ClassicRunner` renders
  locally in one environment — use the grid, which is the reason to choose Applitools.
- **`Eyes`** (`com.applitools.eyes.playwright`) is one visual test, bound to a runner:
  `eyes.open(page, appName, testName, new RectangleSize(w, h))`, then `eyes.check(name, settings)` per
  checkpoint, then `eyes.closeAsync()`.
- **`runner.getAllTestResults(true)`** blocks until every checkpoint of every `Eyes` on that runner has been
  rendered and compared, then **throws** if any of them has a difference. That call is the gate.

## 3. The render matrix — `support/EyesConfig.java`

```java
package com.example.uitests.support;

import com.applitools.eyes.BatchInfo;
import com.applitools.eyes.config.Configuration;
import com.applitools.eyes.visualgrid.BrowserType;
import com.applitools.eyes.visualgrid.model.DeviceName;
import com.applitools.eyes.visualgrid.model.ScreenOrientation;

public final class EyesConfig {
    private EyesConfig() {
    }

    public static Configuration forGrid() {
        BatchInfo batch = new BatchInfo("Shop Web — Visual");
        batch.setId(BaseTest.requiredEnv("APPLITOOLS_BATCH_ID"));
        Configuration config = new Configuration();
        config.setBatch(batch);
        config.addBrowser(1280, 800, BrowserType.CHROME);
        config.addBrowser(1280, 800, BrowserType.FIREFOX);
        config.addBrowser(1280, 800, BrowserType.SAFARI);
        config.addDeviceEmulation(DeviceName.Pixel_2, ScreenOrientation.PORTRAIT);
        return config;
    }
}
```

- Every `addBrowser` / `addDeviceEmulation` is one more render of every checkpoint — one `eyes.check` here
  produces four comparisons.
- **One batch per run.** Each test class has its own runner (§4), so the classes share a batch only through a
  stable id. CI sets `APPLITOOLS_BATCH_ID` to the run id (GitHub: `${{ github.run_id }}-${{ github.run_attempt }}`);
  locally, export any value. `requiredEnv` is `BaseTest`'s, reachable because `EyesConfig` sits in the same
  `support` package.
- The matrix is code in the repository, not a secret; only the API key is.

## 4. The core pattern

```java
package com.example.uitests.tests;

import com.applitools.eyes.RectangleSize;
import com.applitools.eyes.playwright.Eyes;
import com.applitools.eyes.playwright.fluent.Target;
import com.applitools.eyes.playwright.visualgrid.VisualGridRunner;
import com.applitools.eyes.visualgrid.services.RunnerOptions;
import com.example.uitests.pages.PricingPage;
import com.example.uitests.support.BaseTest;
import com.example.uitests.support.EyesConfig;
import org.testng.annotations.AfterClass;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.lang.reflect.Method;

public class PricingEyesTest extends BaseTest {
    private VisualGridRunner runner;
    private Eyes eyes;
    private PricingPage pricingPage;

    @BeforeClass(alwaysRun = true)
    public void createRunner() {
        runner = new VisualGridRunner(new RunnerOptions().testConcurrency(5));
    }

    @BeforeMethod(alwaysRun = true)
    public void openEyes(Method method) {
        page.clock().setFixedTime("2026-10-10T09:00:00Z");
        pricingPage = new PricingPage(page);
        eyes = new Eyes(runner);
        eyes.setConfiguration(EyesConfig.forGrid());
        eyes.open(page, "Shop Web", getClass().getSimpleName() + "." + method.getName(), new RectangleSize(1280, 800));
    }

    @Test(groups = "visual",
          description = "No assertion: the Ultrafast Grid compares this checkpoint; this class's @AfterClass getAllTestResults(true) fails the run on any difference, reviewed in the Applitools dashboard.")
    public void Should_MatchApprovedPlanTable_When_PlansLoad() {
        pricingPage.open();

        eyes.check("Pricing.PlanTable", Target.region(pricingPage.planTable())
                .layout(pricingPage.promoPrice())
                .ignore(pricingPage.promoBadge()));
    }

    @AfterMethod(alwaysRun = true)
    public void closeEyes() {
        eyes.closeAsync();
    }

    @AfterClass(alwaysRun = true)
    public void gateOnEyesResults() {
        runner.getAllTestResults(true);
    }
}
```

- `PricingPage` is the page object from `references/playwright-snapshots.md` §5. Eyes captures **at
  `check` time**, so `open()` returning on the visible table is what makes the checkpoint stable.
- **Cleanup lives in the hooks**, never in a `try`/`finally` in the test: `closeAsync()` in the class's
  `@AfterMethod(alwaysRun = true)` ends the Eyes test whether the test passed or threw, and TestNG runs it
  before `BaseTest` closes the context.
- **The runner is an instance field built in `@BeforeClass`**, so under `parallel="classes"` each class owns
  one, on its own thread — no static runner shared across threads. The cost: the gate fires once per class,
  and `testConcurrency` applies per class, so size it to the account's limit divided by `thread-count`.
- **The gate is `gateOnEyesResults`.** `getAllTestResults(true)` throws when a checkpoint differs; TestNG
  reports it as a failed configuration method of this class, and its message carries the dashboard link. Never
  `eyes.close(true)` per test: it waits for that test alone and serializes the grid.
- **The test has no assertion, and says so** in `@Test(description = …)` — the TestNG form of the TS lane's
  `no-assertion` annotation (plan D50).

## 5. Match levels — the real differentiator

`Target.window()` (the viewport; `.fully()` for the whole page) or `Target.region(locator)` starts the check
settings. Each of these takes a `Locator`, a CSS selector string, or a `Region`:

| Call | Effect |
|---|---|
| (default) Strict | Visual AI: "would a person call these the same?" — the right default for stable UI |
| `.layout(locator)` / `.layout()` | Only the structure and position must match; text, numbers and images may change |
| `.content(locator)` / `.content()` | Structure and text must match; colours and exact pixels may not |
| `.strict(locator)` | A Strict region inside a looser check |
| `.ignore(locator)` | Not compared at all |
| `.floating(locator, up, down, left, right)` | May move by that many pixels in each direction |
| `.withName(name)` | Names the checkpoint when `check(settings)` is called without a tag |

**There is no pixel-ratio knob.** Reach for `layout` before `ignore`: an ignored region drops coverage, a
Layout region keeps its structure under test while its data changes.

## 6. CI and the review

The SDK talks to the cloud, so the nightly job runs `./gradlew --no-daemon :e2e:visualTest` with
`APPLITOOLS_API_KEY` and `APPLITOOLS_BATCH_ID` set — on the UI job's runner, with its JDK 21 and
`installPlaywrightBrowsers` step (`qa/cicd/java/skills/ci-pipelines`). Rendering happens on the grid, so it
does not need the pinned image.

1. The run uploads each checkpoint; the grid renders every configured environment and compares each with
   its baseline.
2. A class with a difference fails its `gateOnEyesResults`, and the run fails.
3. A reviewer accepts or rejects in the dashboard — once for all environments of a checkpoint. Accepting
   updates the baseline.
4. On merge, the accepted renders are the branch baseline for the next run.

A functional failure in an Eyes class still gets `BaseTest`'s screenshot, trace and video.

## Anti-patterns

- **`try { … } finally { eyes.close(false); }` in a test.** *Fix:* `closeAsync()` in the class's
  `@AfterMethod(alwaysRun = true)`.
- **A `static` runner shared by every class.** Static mutable state across parallel threads. *Fix:* one runner
  per class, built in `@BeforeClass`, gated in `@AfterClass`.
- **`eyes.close(true)` per test as the gate.** *Fix:* `getAllTestResults(true)` once per class.
- **`ClassicRunner` and expecting a cross-browser grid.** *Fix:* `VisualGridRunner` and the `Configuration`
  matrix.
- **`Thread.sleep` or `waitForTimeout` before `eyes.check`.** *Fix:* the page object's ready signal.
- **`ignore` where `layout` would do.** *Fix:* Layout keeps the structure asserted.
- **A new batch per class or shard.** *Fix:* one `APPLITOOLS_BATCH_ID` per run.
- **An Eyes test without the `description`.** It reads as a forgotten assertion.
- **A Maven `+` range.** *Fix:* `5.86.9`, exact.

## Rules

- Extend `BaseTest`; reach the state through page objects; freeze the clock in `@BeforeMethod`.
- `VisualGridRunner` per class in `@BeforeClass`; `Eyes` per test in `@BeforeMethod`; `closeAsync()` in
  `@AfterMethod(alwaysRun = true)`; `getAllTestResults(true)` in `@AfterClass(alwaysRun = true)`.
- Prefer a match level (`layout`) over hiding a region; there is no pixel budget.
- `APPLITOOLS_API_KEY` from the secret store only; one batch id per run.
- The test states its missing assertion in `@Test(description = "No assertion: …")`.
- `com.applitools:eyes-playwright-java5:5.86.9`, exact.

## Cross-references

- `references/playwright-snapshots.md` — the free sibling, and `PricingPage`.
- `references/percy.md` — the hosted pixel-diff sibling.
- `qa/java/skills/ui-test-author/playwright` — `BaseTest` and page objects.
- `qa/cicd/java/skills/ci-pipelines` — the schedule gate and the secret store.
- `qa-typescript:visual-regression` (`@applitools/eyes-playwright`), `qa-dotnet:visual-regression`
  (`Eyes.Playwright`).
