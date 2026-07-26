# Visual Regression — Playwright Snapshots (Java / TestNG)

The Java port of the canonical `qa-visual-regression-typescript`. Same concepts,
same flake-control discipline, same CI-container baseline rule — re-expressed in
`com.microsoft.playwright` + `PlaywrightAssertions` + TestNG idioms. **One key difference from the TS
runner:** Java has **no `--update-snapshots` CLI flag** — you regenerate a baseline by deleting it and
re-running (inside the CI container). That distinction is called out throughout.

## When to use this skill

Use when a Playwright **Java / TestNG** test must detect **unintended visual change** — a CSS
regression, a broken layout, a shifted component — by comparing a fresh screenshot against a
committed baseline. This is the **built-in, free** layer: Playwright does the capture and the pixel
diff, baselines live in your repo, you own the flakiness budget. Reach for Percy or Applitools
(`applitools`) only for hosted baseline management, a review UI, or visual-AI diffing — see the matrix.

Visual regression is an **assertion layer** on top of your existing page objects and specs. You do
not author new page objects here — you add a screenshot assertion to a flow
`qa-ui-test-writer-playwright-java` already built.

## Decision matrix — which assertion, which tool

| Need | Use | Why |
|------|-----|-----|
| Visual diff of a page/element, auto-retried + stabilized | `assertThat(page).hasScreenshot()` | Waits for the page to settle; retries until match or timeout |
| Visual diff of an element only | `assertThat(locator).hasScreenshot()` | Scopes the capture; far less flaky than full page |
| Compare an arbitrary buffer you produced | `assertThat(page).hasScreenshot(bytes, options)` *(or store via your own helper)* | Raw byte snapshot you control |
| Free, baselines in your repo, you own diffing | **this skill** | No SaaS, no per-screenshot cost, full control |
| Hosted baselines + PR review UI | Percy | Offloads baseline mgmt + review; paid |
| Visual-AI diffing + cross-browser grid | Applitools | Ignores anti-aliasing noise via AI; paid |

**Rule of thumb:** `assertThat(...).hasScreenshot()` for anything rendered in the browser (it
stabilizes and retries). Prefer **element** screenshots over **full-page** — they are dramatically
less flaky.

## Setup

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("com.microsoft.playwright:playwright:1.50.0")
    testImplementation("org.testng:testng:7.10.2")
}
```

```bash
# Install browsers (matches the dependency version)
mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install --with-deps chromium"
# or via the Gradle equivalent task
```

There is no `playwright.config.ts` equivalent — screenshot defaults are passed **per assertion** via
the options object, or centralized in a base test class. The expect timeout (how long
`hasScreenshot()` auto-retries) is set globally:

```java
// BaseVisualTest.java — centralize lifecycle + screenshot policy so individual tests stay clean.
import com.microsoft.playwright.*;
import com.microsoft.playwright.assertions.PlaywrightAssertions;
import org.testng.annotations.*;

public abstract class BaseVisualTest {
    protected Playwright playwright;
    protected Browser browser;
    protected BrowserContext context;
    protected Page page;

    @BeforeClass
    void launch() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
        // Global retry budget for hasScreenshot() — a condition, not a sleep.
        PlaywrightAssertions.setDefaultAssertionTimeout(10_000);
    }

    @BeforeMethod
    void newContext() {
        context = browser.newContext(new Browser.NewContextOptions().setBaseURL("http://localhost:3000"));
        page = context.newPage();
    }

    @AfterMethod
    void closeContext() { context.close(); }

    @AfterClass
    void shutdown() { browser.close(); playwright.close(); }
}
```

## Where baselines live & how they're named

On first run Playwright writes a baseline; on later runs it compares against it. The naming carries a
platform suffix (`linux` / `darwin` / `windows`):

```
src/test/java/.../DashboardTest.java
DashboardTest.java-snapshots/
  revenue-card-chromium-linux.png      ← {name}-{browser}-{platform}.png
```

The `-{platform}` suffix is the crux of the **cross-platform rendering problem**: a baseline
generated on a dev Mac (`...-darwin.png`) will not match — and is not even looked up — on a Linux
runner. The fix is in "The CI baseline discipline". Commit the `*-snapshots/` directories:
**baselines are versioned build artifacts, not secrets.**

## Core pattern 1 — element screenshot on a page-object-driven flow

The page object exposes intent and the locator; the test adds the visual assertion. No selectors in
the test.

```java
// pages/DashboardPage.java
import com.microsoft.playwright.*;
import com.microsoft.playwright.options.*;

public final class DashboardPage {
    private final Page page;
    public final Locator revenueCard;

    public DashboardPage(Page page) {
        this.page = page;
        this.revenueCard = page.getByTestId("revenue-card");
    }

    public void goto_() { page.navigate("/dashboard"); }

    /** Resolves once the card's data has rendered — a condition, never a fixed wait. */
    public void waitUntilLoaded() {
        revenueCard.getByRole(AriaRole.STATUS)
            .waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.HIDDEN));
    }
}
```

```java
// DashboardTest.java
import com.microsoft.playwright.assertions.PageAssertions.HasScreenshotOptions;
import com.microsoft.playwright.options.ScreenshotAnimations;
import org.testng.annotations.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static java.util.Arrays.asList;

public final class DashboardTest extends BaseVisualTest {

    @Test
    public void Should_match_revenue_card_baseline_When_dashboard_loads() {
        DashboardPage dashboard = new DashboardPage(page);
        dashboard.goto_();
        dashboard.waitUntilLoaded();   // stabilize on a condition first…

        assertThat(dashboard.revenueCard).hasScreenshot("revenue-card.png",
            new com.microsoft.playwright.assertions.LocatorAssertions.HasScreenshotOptions()
                .setMaxDiffPixelRatio(0.01)
                .setAnimations(ScreenshotAnimations.DISABLED)); // …then assert (auto-retries)
    }
}
```

`hasScreenshot()` auto-retries the capture+compare until it matches or the assertion timeout elapses,
and waits for fonts/animations to settle. You still stabilize *application* state (data loaded,
spinners gone) yourself — Playwright cannot know your spinner is "done".

## Core pattern 2 — taming flakiness

The four sources of false diffs and the deterministic fix for each:

```java
import com.microsoft.playwright.assertions.PageAssertions;
import com.microsoft.playwright.options.ScreenshotAnimations;
import com.microsoft.playwright.options.ScreenshotCaret;

@Test
public void Should_match_profile_page_When_dynamic_regions_neutralized() {
    page.navigate("/profile");

    // 1) Fonts not yet rendered → wait on the condition, not a timeout.
    page.evaluate("document.fonts.ready");

    assertThat(page).hasScreenshot("profile.png", new PageAssertions.HasScreenshotOptions()
        // 2) Dynamic content (timestamps, avatars) → mask it (painted as a solid box).
        .setMask(asList(page.getByTestId("last-seen"), page.locator("img.gravatar")))
        .setMaskColor("#FF00FF")

        // 3) Anti-aliasing / sub-pixel noise → small tolerance. Prefer ratio over absolute.
        .setMaxDiffPixelRatio(0.02)
        .setThreshold(0.2)   // per-pixel color sensitivity (0 strict … 1 loose); default 0.2

        // 4) Animations / carets → freeze them.
        .setAnimations(ScreenshotAnimations.DISABLED)
        .setCaret(ScreenshotCaret.HIDE));
}
```

Knobs, precisely:

- **`setMaxDiffPixels`** — absolute number of differing pixels allowed. Brittle across viewport sizes.
- **`setMaxDiffPixelRatio`** — fraction (0–1) of differing pixels allowed. **Prefer this** — scales
  with image size.
- **`setThreshold`** — per-pixel YIQ color-distance sensitivity (0 exact … 1 anything). Decides
  whether a pixel counts as different *at all* before the ratio is applied. Default `0.2`.
- **`setMask` / `setMaskColor`** — overpaint dynamic regions so they can never diff.
- **`setAnimations(ScreenshotAnimations.DISABLED)`** — sets CSS animations/transitions to end state.
- **`setCaret(ScreenshotCaret.HIDE)`** — hides the text caret (a classic 1px flake).
- **`setStylePath`** — inject a CSS file to neutralize elements (carets, live widgets) across shots.
- **`setFullPage(true)`** — whole scrollable page (flakier; mask aggressively).
- **`setClip`** — capture a fixed rectangle.

`setStylePath` for repo-wide stabilization:

```css
/* snapshot.css */
*, *::before, *::after { transition: none !important; animation: none !important; }
[data-testid="live-clock"], .chat-widget { visibility: hidden !important; }
```

```java
assertThat(page).hasScreenshot("home.png", new PageAssertions.HasScreenshotOptions()
    .setStylePath(Paths.get("snapshot.css"))
    .setAnimations(ScreenshotAnimations.DISABLED)
    .setMaxDiffPixelRatio(0.01));
```

## Core pattern 3 — raw byte snapshots for content you produced

For a buffer you generated yourself (e.g. a PDF), compare against a committed baseline you manage. For
anything the **browser renders live**, use `hasScreenshot()` so it stabilizes and retries — don't
hand-roll a byte compare for live pages.

```java
@Test
public void Should_match_generated_invoice_pdf_baseline() {
    byte[] pdf = page.pdf(new Page.PdfOptions().setFormat("A4"));
    // Compare bytes against src/test/resources/baselines/invoice.pdf via your own assert helper.
    assertThat(pdf).isEqualTo(Baselines.read("invoice.pdf")); // AssertJ; manage the baseline in-repo
}
```

## The CI baseline discipline (the part everyone gets wrong)

Baselines are platform-specific. The only reliable workflow:

1. **Never commit baselines generated on your dev box.** A `...-darwin.png` baseline is useless to a
   Linux runner.
2. **Generate/update baselines inside the same container CI uses.** Run CI's image locally, or a
   dedicated update step in CI. **Java has no `--update-snapshots` flag** — you regenerate by
   **deleting the baseline PNG and re-running** (a missing baseline is auto-created on the next run):

   ```bash
   # Reproduce CI's exact rendering via the official Java image (tag must match your playwright version):
   docker run --rm -v "$(pwd):/work" -w /work mcr.microsoft.com/playwright/java:v1.50.0-noble bash -c '
     find . -path "*-snapshots/*-linux.png" -delete   # drop stale baselines
     mvn -B test                                       # missing baselines are regenerated, then compared
   '
   ```

3. **Regeneration discipline.** Delete-and-rerun deliberately when a change is *intended*, review the
   regenerated PNGs in the diff, and commit them in the same PR as the UI change. Never automate
   blanket baseline deletion in the normal test run — that makes every run "pass".
4. **Gate regeneration behind a manual/labelled CI job**, not a local push. See the github-actions
   cross-link for the gated `update-baselines` job pattern.

On a normal failure Playwright writes `*-actual.png`, `*-expected.png`, `*-diff.png` into the test
output. Upload them as artifacts and attach to the report:

```yaml
# inside your test job (see qa-ci-pipelines-java for the full pipeline)
- name: Upload visual diff artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-visual-diffs
    path: '**/test-results/**/*-{actual,expected,diff}.png'
    retention-days: 7
```

Attach the diff into Allure so reviewers see it inline (cross-link `qa-test-reports-java`):

```java
@AfterMethod
void attachVisualDiff(ITestResult result) throws IOException {
    if (result.getStatus() != ITestResult.FAILURE) return;
    try (var paths = Files.walk(Paths.get("target/test-results"))) {
        paths.filter(p -> p.toString().endsWith("-diff.png")).forEach(p -> {
            try { Allure.addAttachment("visual-diff", "image/png",
                    new ByteArrayInputStream(Files.readAllBytes(p)), "png"); }
            catch (IOException ignored) { }
        });
    }
}
```

## Anti-patterns

- **Committing dev-box baselines.** `...-darwin.png` fails/flakes on Linux CI. *Fix:* the Docker
  delete-and-rerun workflow above.
- **`page.waitForTimeout(500)` before the screenshot.** Flaky and slow. *Fix:* wait on a condition
  (`document.fonts.ready`, spinner hidden, `locator.waitFor`), then assert — `hasScreenshot()`
  auto-retries the rest.
- **Full-page screenshots of a page full of dynamic data.** Guaranteed flake. *Fix:* screenshot the
  **element**; `setMask` the dynamic bits; `setStylePath` to neutralize globally.
- **Cranking `setMaxDiffPixelRatio` to 0.2 to "make it pass".** Blinds the test to real regressions.
  *Fix:* `setMask` the specific flaky region; keep the ratio tight (≤0.02).
- **Auto-deleting baselines in the default test run.** Every run silently regenerates, so nothing is
  caught. *Fix:* delete only via a deliberate, gated step.
- **Hand-rolling a byte compare for a live page.** No stabilization, no retry → flaky. *Fix:*
  `hasScreenshot()` for anything the browser renders.
- **`.gitignore`-ing `*-snapshots/`.** Then CI has nothing to compare against. *Fix:* commit
  baselines; they are versioned artifacts.

## Examples

**End-to-end: a component visual gate that survives CI.**

```java
public final class PricingTest extends BaseVisualTest {

    @Test
    public void Should_match_pricing_table_baseline_When_plans_loaded() {
        PricingPage pricing = new PricingPage(page);
        pricing.goto_();
        pricing.waitUntilPlansRendered();        // condition, not sleep
        page.evaluate("document.fonts.ready");    // fonts settled

        assertThat(pricing.table).hasScreenshot("pricing-table.png",
            new com.microsoft.playwright.assertions.LocatorAssertions.HasScreenshotOptions()
                .setMask(asList(pricing.promoBanner))   // rotates daily — never diff it
                .setMaxDiffPixelRatio(0.01)
                .setAnimations(ScreenshotAnimations.DISABLED)
                .setCaret(ScreenshotCaret.HIDE));
    }
}
```

Baseline lifecycle for this test:
1. Dev makes an intended CSS change.
2. In the CI image, delete the stale `pricing-table-chromium-linux.png` and `mvn test` to regenerate.
3. Reviews the regenerated PNG in the diff, commits it with the CSS change.
4. CI compares against it on every PR; an *unintended* change now fails with a `-diff.png` artifact.

## Rules (hard constraints)

- Stabilize **application** state on a condition before asserting; never `page.waitForTimeout`. Let
  `hasScreenshot()` auto-retry the rendering settle.
- Prefer **element** screenshots over full-page; `setMask` every dynamic region.
- Prefer `setMaxDiffPixelRatio` over `setMaxDiffPixels`; keep tolerance tight and mask noise rather
  than loosening the budget.
- **Generate baselines inside the CI container**, never on the dev box. Baselines are committed,
  versioned build artifacts — not secrets, not `.gitignore`-d.
- **Java has no `--update-snapshots`** — regenerate by deleting the baseline and re-running, as a
  deliberate, reviewed, gated action; never blanket-delete in the default test run.
- On failure, upload `*-actual/-expected/-diff.png` as artifacts and attach the diff to the report.
- `hasScreenshot()` for browser-rendered content; manage raw-byte baselines yourself only for content
  you produced.
- Page objects expose intent + locators; the test owns the visual assertion. No selectors in tests.

## Cross-references

- `qa-visual-regression-typescript` — the **canonical** skill this ports
  (`@playwright/test` `toHaveScreenshot()`, `--update-snapshots`, `playwright.config.ts` defaults).
- `qa-visual-regression-dotnet` — the .NET / NUnit sibling
  (`Expect(...).ToHaveScreenshotAsync()`).
- `qa-ui-test-writer-playwright-java` — the page objects/specs these assertions layer on top of.
- `references/percy.md` (`percy`, next) — hosted baseline management + PR review UI.
- `references/applitools.md` — visual-AI diffing + cross-browser grid.
- `qa-ci-pipelines-java` — artifact upload, the container-baseline discipline, the
  gated `update-baselines` job.
- `qa-test-reports-java` — attach `-diff.png` images to the test report.
