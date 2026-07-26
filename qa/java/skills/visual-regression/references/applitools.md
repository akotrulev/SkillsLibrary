# Visual Regression — Applitools Eyes (Java / TestNG)

The Java port of the canonical `qa-visual-regression-typescript`. Same visual-AI model, same
Ultrafast Grid matrix, same dashboard review workflow — re-expressed in
`com.applitools:eyes-playwright-java5` + Playwright-Java + TestNG idioms. Applitools Eyes uploads the
rendered page to the **Ultrafast Grid**, re-renders it server-side across a configured
browser/viewport/device matrix, and diffs with **AI-based matching** that ignores anti-aliasing /
sub-pixel noise — plus **match levels** (Strict / Layout / Content / Ignore-colors). That match-level
control is the real differentiator versus Percy's server-side **pixel** diff and the built-in
**byte/pixel** diff.

This is an **assertion layer** on top of the page objects and specs `qa-ui-test-writer-playwright-java`
already authored. You do not write new page objects here — you add `eyes.open` / `eyes.check` /
`eyes.close` around an existing flow.

## Why graduate from Percy (pixel) to Applitools (visual-AI)

Percy already solved the cross-platform rendering problem by rendering server-side. Applitools
goes further on **how the diff is judged** and **how many environments render at once**:

| | Percy | **Applitools Eyes (this skill)** |
|---|---|---|
| What leaves the test | A DOM snapshot, uploaded by the `percy exec` agent | The rendered page, uploaded by the **SDK directly** (no agent) |
| How the diff is judged | Server-side **pixel** diff | Server-side **AI** match — ignores anti-aliasing / sub-pixel noise |
| Tolerance lever | `percyCSS` hide + `scope` (no pixel knob) | **Match levels** (Strict / Layout / Content / Ignore-colors) + region ignores |
| Dynamic content | Hide it with `percyCSS` | **`Target.layout(region)`** — structure matches, text may differ |
| Cross-browser/device | Re-renders at configured widths | **Ultrafast Grid** — a real browser/viewport/device **matrix** from one run |
| Process model | Local `percy exec` agent wraps the run | **None** — SDK calls the cloud; just `APPLITOOLS_API_KEY` in env |
| Baselines | Percy cloud, keyed by git branch, review UI | **Applitools dashboard**, keyed by app/test/branch, review UI |
| Gate | GitHub/GitLab status check | Runner's **aggregated results** fail the build; dashboard link |
| Cost | Paid | Paid (typically the most expensive of the three) |

State the contrast plainly: **Applitools is AI match (not pixel), match levels (not just hide-or-fail),
and a real cross-browser grid (not just widths)** — and there's **no agent process** to wrap the run.

## Setup

There is **no agent to launch** (the difference from Percy's Node `@percy/cli`): the Java SDK talks to
the Applitools cloud directly, so the only dependency is the Maven/Gradle artifact.

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("com.microsoft.playwright:playwright:1.50.0")
    testImplementation("com.applitools:eyes-playwright-java5:5.+")
    testImplementation("org.testng:testng:7.+")
}
```

```xml
<!-- or Maven -->
<dependency>
  <groupId>com.applitools</groupId>
  <artifactId>eyes-playwright-java5</artifactId>
  <version>5.+</version>
  <scope>test</scope>
</dependency>
```

`APPLITOOLS_API_KEY` is the **only secret** — the SDK reads it from the environment automatically (or set
it explicitly with `eyes.setApiKey(System.getenv("APPLITOOLS_API_KEY"))`). In CI it comes from the secret
store (see the ci-pipelines cross-link), never committed. Locally `export APPLITOOLS_API_KEY=<key>`.

## The Eyes model + the Ultrafast Grid

Three objects, one lifecycle:

- **`VisualGridRunner`** — the runner that ships checkpoints to the **Ultrafast Grid**, which renders
  them server-side across your configured browser/viewport/device matrix. Construct it with a
  concurrency cap: `new VisualGridRunner(new RunnerOptions().testConcurrency(5))`. (Its sibling
  `ClassicRunner` renders locally with one environment — use `VisualGridRunner` to get the grid, the
  whole point of Applitools over `playwright-snapshots`/`percy`.)
- **`Eyes`** — one visual test session, bound to a runner: `new Eyes(runner)`. `eyes.open(page, app,
  test, viewport)` starts it; `eyes.check(...)` adds a checkpoint; `eyes.close(false)` ends it
  **without throwing inline**.
- **`runner.getAllTestResults(true)`** — called **once at suite end**, it blocks until every checkpoint
  across every `Eyes` has rendered + diffed on the grid, aggregates the results, and (with `true`)
  throws if any test had a mismatch or error. **This is the gate** — not `eyes.close`.

A `Configuration` with `addBrowser(width, height, BrowserType)` / `addDeviceEmulation(...)` is what
makes **one local run fan out to a cross-browser/device render matrix** server-side — the thing neither
`playwright-snapshots` nor `percy` does natively.

## Configuration — the render matrix

```java
// support/EyesConfig.java
import com.applitools.eyes.BatchInfo;
import com.applitools.eyes.config.Configuration;
import com.applitools.eyes.selenium.BrowserType;
import com.applitools.eyes.visualgrid.model.DeviceName;
import com.applitools.eyes.visualgrid.model.ScreenOrientation;

public final class EyesConfig {
    public static Configuration build() {
        Configuration config = new Configuration();
        // One batch groups every test in this run in the dashboard (see "Batching" below).
        config.setBatch(new BatchInfo("FlexInvest Web — Visual"));

        // Each addBrowser/addDeviceEmulation adds an environment the Ultrafast Grid renders + diffs.
        // One eyes.check() therefore produces N checkpoints — the cross-browser/device matrix.
        config.addBrowser(1280, 800, BrowserType.CHROME);
        config.addBrowser(1280, 800, BrowserType.FIREFOX);
        config.addBrowser(1280, 800, BrowserType.SAFARI);
        config.addBrowser(375, 812, BrowserType.EDGE_CHROMIUM);
        config.addDeviceEmulation(DeviceName.iPhone_11, ScreenOrientation.PORTRAIT);
        config.addDeviceEmulation(DeviceName.Pixel_5, ScreenOrientation.PORTRAIT);
        return config;
    }
}
```

`eyes.setConfiguration(EyesConfig.build())` before `eyes.open` applies it. The matrix lives in code, in
the repo — it's not a secret; only the API key is.

## Core pattern — `open` / `check` / `close` + `getAllTestResults`

The page object exposes intent; the test stabilizes **application** state on a condition, then checks.
No selectors in the test, no fixed waits. `eyes.close(false)` per test; the runner gates at suite end.
Share **one runner** across the suite via `@AfterSuite`.

```java
// pages/DashboardPage.java
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.AriaRole;
import com.microsoft.playwright.options.WaitForSelectorState;

public final class DashboardPage {
    private final Page page;
    public final Locator revenueCard;

    public DashboardPage(Page page) {
        this.page = page;
        this.revenueCard = page.getByTestId("revenue-card");
    }

    public void goto_() {
        page.navigate("/dashboard");
    }

    /** Returns once the card's data has rendered — a condition, never a fixed wait. */
    public void waitUntilLoaded() {
        revenueCard.getByRole(AriaRole.STATUS)
            .waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.HIDDEN));
    }
}
```

```java
// DashboardTest.java
import com.applitools.eyes.RectangleSize;
import com.applitools.eyes.playwright.Eyes;
import com.applitools.eyes.playwright.fluent.Target;
import com.applitools.eyes.visualgrid.services.RunnerOptions;
import com.applitools.eyes.visualgrid.services.VisualGridRunner;
import com.microsoft.playwright.*;
import org.testng.annotations.*;

public class DashboardTest {
    // One runner for the whole suite (cap concurrency on the grid).
    private static final VisualGridRunner RUNNER =
        new VisualGridRunner(new RunnerOptions().testConcurrency(5));

    private Playwright playwright;
    private Browser browser;
    private Page page;

    @BeforeMethod
    public void setUp() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
        page = browser.newContext(new Browser.NewContextOptions()
            .setBaseURL("http://localhost:3000")).newPage();
    }

    @AfterMethod
    public void tearDown() { browser.close(); playwright.close(); }

    @Test
    public void Should_Match_Dashboard_When_Loaded() {
        Eyes eyes = new Eyes(RUNNER);
        eyes.setConfiguration(EyesConfig.build());      // API key read from env automatically
        eyes.open(page, "FlexInvest Web", "Dashboard — revenue card", new RectangleSize(1280, 800));

        try {
            DashboardPage dashboard = new DashboardPage(page);
            dashboard.goto_();
            dashboard.waitUntilLoaded();                // stabilize on a condition first…

            eyes.check("Dashboard", Target.window().fully());  // …then capture the checkpoint
        } finally {
            eyes.close(false);                          // end session WITHOUT throwing inline
        }
    }

    @AfterSuite
    public void gateOnVisualResults() {
        // Blocks until the grid finishes; `true` throws if any test mismatched — THE GATE.
        RUNNER.getAllTestResults(true);
    }
}
```

Why `eyes.close(false)` then `getAllTestResults(true)`: `close(true)` would throw the *first* time any
single test mismatches, aborting the rest before they render on the grid. Passing `false` lets every
test finish; the runner then aggregates **all** results and fails the build once, at suite end, with a
complete picture. Eyes captures **at `check` time**, like Percy — so stabilize before each `check`.

## Match levels — the real differentiator

A match level tells the AI *how* to compare a checkpoint against its baseline. Set it per-check via the
`Target` fluent API; this is the analogue of Percy's `percyCSS`-hide, but richer — prefer a **region
match level** over hiding the region entirely:

```java
eyes.check("Account summary", Target.window().fully()
    // Whole-page level: Strict is the default ("looks the same to a human").
    .layout("[data-testid=\"balance-figures\"]")    // structure must match; the NUMBERS may change
    .ignore("[data-testid=\"last-login\"]")         // ignore entirely (timestamp)
    .floating("[data-testid=\"toast\"]", 5, 5, 5, 5)); // may shift up to 5px in any direction
```

The levels, precisely:

- **Strict** (default) — AI match: "would a human call these the same?" Ignores anti-aliasing /
  rendering noise but catches real visual changes. The right default for stable UI.
- **Layout** — only the **structure/position** of elements must match; their **content** (text,
  numbers, images) may differ. *The killer feature for dynamic data* — baseline a populated page once
  and it stays green as the data changes, while a broken layout still fails.
- **Content** — like Layout but also compares text content (structure + text, not exact pixels/colors).
- **Ignore-colors** — match structure + content but ignore color (theme/branding churn).

Region levels are the surgical version: `Target.window().fully().layout(locator)` keeps the page Strict
but treats one region as Layout. Region ignores — `.ignore(locator)` (drop entirely), `.layout(locator)`,
`.floating(locator, ...)` (element may shift within a pixel margin), `.accessibility(locator,
AccessibilityRegionType.LargeText)` — are the analogue of masking, but expressed as intent.

**There is no per-call pixel-ratio knob** (no `setMaxDiffPixelRatio` like `playwright-snapshots`). The AI plus the match
level *is* the tolerance lever. Reach for **Layout** before you reach for ignore.

## Batching + the dashboard

`BatchInfo` groups one run's tests under a single entry in the **Applitools dashboard** (set it on the
`Configuration`, as above). The dashboard is the hosted **baseline store + review UI** — the analogue of
Percy's. Baselines are keyed by **app / test / branch**; you accept or reject diffs there, and an accept
updates the baseline. Same "no in-repo baselines, no `-{platform}` naming" story as Percy: the repo
holds no PNGs.

To group a sharded CI run into one dashboard batch, set a stable batch id across shards:

```java
BatchInfo batch = new BatchInfo("FlexInvest Web — Visual");
String batchId = System.getenv("APPLITOOLS_BATCH_ID");
if (batchId != null && !batchId.isEmpty()) batch.setId(batchId);   // same value across shards → one batch
config.setBatch(batch);
```

## CI integration + the gate

There's **no agent to wrap the command** (the difference from Percy's `percy exec`): the SDK talks to
the cloud directly, so CI just runs `./gradlew test` (or `mvn test`) with `APPLITOOLS_API_KEY` in env.
The build fails when `runner.getAllTestResults(true)` throws because an **unresolved diff** exists in
the dashboard.

```yaml
# inside your test job — see qa-ci-pipelines-java for the full pipeline
- name: Visual tests (Applitools)
  env:
    APPLITOOLS_API_KEY: ${{ secrets.APPLITOOLS_API_KEY }}   # from the secret store; never inline
    APPLITOOLS_BATCH_ID: ${{ github.run_id }}-${{ github.run_attempt }}  # one batch across shards
  run: ./gradlew test
```

Link the dashboard batch URL into Allure so reviewers jump straight to it (cross-link
`qa-test-reports-java`):

```java
import com.applitools.eyes.TestResultsSummary;
import com.applitools.eyes.TestResultContainer;
import com.applitools.eyes.TestResultsStatus;
import io.qameta.allure.Allure;

@AfterSuite
public void linkAndGate() {
    TestResultsSummary summary = RUNNER.getAllTestResults(false);   // false: collect without throwing here…
    boolean unresolved = false;
    for (TestResultContainer c : summary.getAllResults()) {
        if (c.getTestResults() != null && c.getTestResults().getAppUrls() != null) {
            Allure.link("Applitools dashboard", c.getTestResults().getAppUrls().getBatch());
        }
        if (c.getException() != null ||
            (c.getTestResults() != null && c.getTestResults().getStatus() == TestResultsStatus.Unresolved)) {
            unresolved = true;
        }
    }
    if (unresolved) {
        throw new AssertionError("Applitools: unresolved visual diffs — review the dashboard batch."); // …gate
    }
}
```

The review-UI workflow, concretely:
1. PR runs `./gradlew test`; the SDK uploads to the Ultrafast Grid, which renders + diffs against the
   branch baseline.
2. `getAllTestResults(true)` fails the build if any environment is **Unresolved** (new diff).
3. A reviewer accepts/rejects in the Applitools dashboard. Accepting updates the baseline.
4. On merge, the accepted checkpoints become the branch baseline for the next PR.

## Anti-patterns

- **`eyes.close(true)` (or `eyes.close()`) per test as the gate.** It throws on the first mismatch and
  aborts the rest before they render. *Fix:* `eyes.close(false)` per test; gate once at suite end with
  `runner.getAllTestResults(true)`.
- **Using `ClassicRunner` and expecting a cross-browser grid.** ClassicRunner renders one local
  environment. *Fix:* `VisualGridRunner` + `Configuration.addBrowser`/`addDeviceEmulation`.
- **`page.waitForTimeout(500)` before `eyes.check`.** Eyes captures at call time; a sleep is flaky and
  slow. *Fix:* wait on a condition (`document.fonts.ready` via `page.evaluate`, spinner hidden,
  `Locator.waitFor`).
- **Hiding a dynamic region when Layout would do.** Ignoring drops coverage. *Fix:* `Target.layout(
  region)` — structure stays asserted, only content is allowed to vary.
- **Committing `*-snapshots/` PNGs alongside Applitools.** Baselines live in the dashboard. *Fix:*
  delete them; rely on the dashboard baseline.
- **Hardcoding / logging `APPLITOOLS_API_KEY`.** It's a write credential. *Fix:* env only, from the CI
  secret store, read lazily by the SDK, never echoed.
- **A new `BatchInfo` per shard.** Splits one run across many dashboard batches. *Fix:* one stable
  `APPLITOOLS_BATCH_ID` env var shared across shards.
- **Full-page Strict checks on a page full of live data.** Chatty reviews. *Fix:* `Target.region(
  locator)` for the stable part, `layout`/`ignore` regions for the live bits.

## Examples

**End-to-end: a pricing-table visual gate across a browser/device grid, reviewed in the dashboard.**

```java
import com.applitools.eyes.RectangleSize;
import com.applitools.eyes.playwright.Eyes;
import com.applitools.eyes.playwright.fluent.Target;
import com.applitools.eyes.visualgrid.services.RunnerOptions;
import com.applitools.eyes.visualgrid.services.VisualGridRunner;
import com.microsoft.playwright.*;
import org.testng.annotations.*;

public class PricingTest {
    private static final VisualGridRunner RUNNER =
        new VisualGridRunner(new RunnerOptions().testConcurrency(5));

    private Playwright playwright;
    private Browser browser;
    private Page page;

    @BeforeMethod
    public void setUp() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
        page = browser.newContext(new Browser.NewContextOptions()
            .setBaseURL("http://localhost:3000")).newPage();
    }

    @AfterMethod
    public void tearDown() { browser.close(); playwright.close(); }

    @Test
    public void Should_Match_PricingTable_When_PlansLoaded() {
        Eyes eyes = new Eyes(RUNNER);
        eyes.setConfiguration(EyesConfig.build());
        eyes.open(page, "FlexInvest Web", "Pricing — plan table", new RectangleSize(1280, 800));

        try {
            PricingPage pricing = new PricingPage(page);
            pricing.goto_();
            pricing.waitUntilPlansRendered();             // condition, not sleep
            page.evaluate("document.fonts.ready");         // fonts settled before capture

            eyes.check("Pricing table",
                Target.region("[data-testid=\"pricing-table\"]")  // element, not full page
                    .layout("[data-testid=\"promo-price\"]")      // price A/B-tests → Layout, not ignore
                    .ignore("[data-testid=\"promo-banner\"]"));   // rotates daily → ignore entirely
        } finally {
            eyes.close(false);                            // don't throw inline
        }
    }

    @AfterSuite
    public void gateOnVisualResults() {
        RUNNER.getAllTestResults(true);                   // grid finishes → gate the build
    }
}
```

Lifecycle for this test:
1. Dev makes an intended CSS change to the pricing table.
2. CI runs `./gradlew test`; the SDK ships one checkpoint per configured browser/device to the grid,
   which renders + AI-diffs each vs the branch baseline.
3. `getAllTestResults(true)` fails the build; the dev reviews + accepts the diff in the dashboard
   (accepting it on **all** environments at once).
4. On merge, the accepted renders become the branch baseline — the next PR diffs against them.

## Rules (hard constraints)

- Visual regression is an assertion layer on existing page objects/specs — add `eyes.check`, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- `VisualGridRunner` (not `ClassicRunner`) + `Configuration.addBrowser`/`addDeviceEmulation` — the grid
  is the reason to choose Applitools.
- `eyes.close(false)` per test (never inline-throw); gate **once** at suite end with
  `runner.getAllTestResults(true)`.
- Stabilize **application** state on a condition before `eyes.check`; never `waitForTimeout` — Eyes
  captures at call time.
- Prefer a **match level** (especially `Target.layout(region)`) over hiding dynamic content; there is
  **no per-call pixel-ratio knob** — the AI + match level is the lever.
- `APPLITOOLS_API_KEY` is the **only** secret: env-only, from the CI secret store, read lazily by the
  SDK, never logged or committed. No agent process to launch (unlike Percy's `percy exec`).
- No in-repo `*-snapshots/` baselines — baselines live in the **dashboard**, keyed by app/test/branch,
  managed via the review UI. One stable `BatchInfo` id across shards.
- The gate is the runner's **aggregated results**; link the dashboard batch URL into Allure.

## Cross-references

- `qa-visual-regression-typescript` — the **canonical** skill this ports
  (`@applitools/eyes-playwright`, `eyes.check(Target.window().fully())`, `runner.getAllTestResults`).
- `qa-visual-regression-dotnet` — the .NET / NUnit sibling (`Applitools.Playwright`,
  `Eyes.Check(Target.Window().Fully())`, `runner.GetAllTestResults(false)`).
- `references/percy.md` — the **hosted pixel-diff** sibling: DOM-upload agent +
  server-side pixel diff + review UI. Applitools is the "graduate to visual-AI + match levels + grid" step.
- `references/playwright-snapshots.md` — the **free** sibling: in-repo baselines you
  diff yourself, with the CI-container discipline both Percy and Applitools remove.
- `qa-ui-test-writer-playwright-java` — the page objects/specs `eyes.check` is called inside.
- `qa-ci-pipelines-java` — where `APPLITOOLS_API_KEY` is sourced; no agent wrapper needed.
- `qa-test-reports-java` — link the Applitools dashboard batch URL into the report.
