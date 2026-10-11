# Visual Regression — Screenshot plus Comparator (Java / Playwright 1.63 + TestNG)

Playwright Java has **no screenshot assertion** — `toHaveScreenshot` is a Node test-runner feature, and
`assertThat(page).hasScreenshot()` / `HasScreenshotOptions` do not exist in any Java release. This reference
builds the free lane from three parts that do exist:

1. `locator.screenshot(...)` with the determinism options, taken after the page object has reached a stable
   state;
2. an image comparator, `com.github.romankh3:image-comparison`, against a PNG baseline committed in the
   repo;
3. an AssertJ assertion on the comparator's result, with the actual, expected and diff images kept and
   attached to Allure when they differ.

Baselines are written **only** in `mcr.microsoft.com/playwright/java:v1.63.0-noble`, the image whose tag
equals the Playwright version. The samples extend `com.example.uitests.support.BaseTest`
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`), which already keeps a screenshot, trace and
video for every failed test.

## 1. Setup

The comparator, checked on Maven Central on 2026-10-11:

| Coordinates | Version | Facts |
|---|---|---|
| `com.github.romankh3:image-comparison` | **4.4.0** | The latest release on Central (its metadata was last updated 2021-03-28; a `v4.5.0` git tag exists but was never published). Pure JDK/AWT, no runtime dependencies, Java 8+. Apache 2.0 |

It is a recommendation, not a Playwright fact (plan D9): Playwright names no comparator. It is small and
stable, but unmaintained since 2021 — if a project's dependency policy rejects that, the comparison it
does is ~40 lines over `BufferedImage.getRGB`, and §4's helper is the only file that changes.

Add it beside J1's pins in `build.gradle.kts`, exclude the `visual` group from the gate, and run it from its
own task:

```kotlin
dependencies {
    testImplementation("com.github.romankh3:image-comparison:4.4.0")
}

tasks.test {
    useTestNG {
        suites("testng.xml")
        excludeGroups("visual")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
}

val visualTest by tasks.registering(Test::class) {
    testClassesDirs = sourceSets["test"].output.classesDirs
    classpath = sourceSets["test"].runtimeClasspath
    useTestNG {
        suites("testng.xml")
        includeGroups("visual")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
    systemProperty("java.awt.headless", "true")
}
```

- A custom `Test` task needs its `testClassesDirs` and `classpath`; TestNG applies the group filter to the
  one suite file, and `BaseTest`'s `alwaysRun = true` hooks still run under it.
- A project that also quarantines flaky tests excludes both: `excludeGroups("flaky", "visual")`
  (`qa/reporting/java/skills/flaky-test-quarantine`).
- `java.awt.headless` keeps the comparator's drawing off any display.

## 2. The baseline store

```
src/test/resources/baselines/
└── linux-chromium/
    ├── Pricing.PlanTable.png
    └── Checkout.Summary.png
```

- The folder is `<os>-<browser>`: `<os>` is the first word of `os.name`, lower-cased (`linux`, `mac`,
  `windows`); `<browser>` is `page.context().browser().browserType().name()` (`chromium`).
- Only `linux-chromium/` is ever written, because baselines come only from the pinned image (§7). A test run
  on a Mac looks up `mac-chromium/`, finds nothing and fails with "no baseline" — instead of comparing a
  macOS rendering against a Linux one and failing with a diff nobody can act on.
- File names are the PascalCase dot-separated subject (`Pricing.PlanTable`), the same shape as the test ids.
- Baselines are **committed**: they are versioned test inputs, not secrets and not build output. They are
  read by path, not from the classpath, so an update writes back to the file the next run reads.

## 3. Capture options — `Locator.ScreenshotOptions`

`locator.screenshot(options)` returns `byte[]` (PNG by default). It waits for the element to be visible and
stable, scrolls it into view and clips to it; the screenshotter also waits for web fonts
(`document.fonts.ready`, in playwright-core's `screenshotter.ts`). It does **not** wait for the app's data,
and unlike the Node runner it takes **one** capture — there is no retry-until-two-captures-match. The page
object waits for the ready state first.

| Setter | Use |
|---|---|
| `setAnimations(ScreenshotAnimations.DISABLED)` | Finite animations jump to their end, infinite ones reset |
| `setCaret(ScreenshotCaret.HIDE)` | The text caret, a classic 1-px flake (the default is already `HIDE`) |
| `setScale(ScreenshotScale.CSS)` | One image pixel per CSS pixel, whatever the device scale factor |
| `setMask(List<Locator>)` | Paints each match with a solid box (`#FF00FF`; `setMaskColor` [1.35]) in actual and baseline alike, so the region can never differ |
| `setStyle(String)` [1.41] | CSS applied only during the capture; pierces shadow DOM and iframes. There is no `setStylePath` in Java |
| `setOmitBackground(true)` | A transparent background (not for JPEG) |
| `setType(ScreenshotType.PNG)` | The default. WebP [1.62] works, but a PNG baseline is what a reviewer opens in a PR diff |

- `Locator.ScreenshotOptions` has no `setFullPage` or `setClip`; those are `Page.ScreenshotOptions`. Prefer an
  element: a full-page baseline changes with every unrelated edit and needs masks everywhere.
- Viewport, locale, time zone and reduced motion are context settings: the test class overrides
  `contextOptions()` (§5). The clock is frozen with `page.clock().setFixedTime(...)` in the class's
  `@BeforeMethod`, before the page object navigates (`ui-test-author/playwright/references/emulation-and-mobile-web.md`
  §4, §6).

## 4. The helper — `support/VisualCheck.java`

One helper captures, compares, keeps and attaches. The test builds it in its own `@BeforeMethod` with the
evidence name, calls `compare`, and asserts on the result.

```java
package com.example.uitests.support;

import com.github.romankh3.image.comparison.ImageComparison;
import com.github.romankh3.image.comparison.model.ImageComparisonResult;
import com.github.romankh3.image.comparison.model.ImageComparisonState;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.ScreenshotAnimations;
import com.microsoft.playwright.options.ScreenshotCaret;
import com.microsoft.playwright.options.ScreenshotScale;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;

import javax.imageio.ImageIO;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

public final class VisualCheck {
    private static final Path BASELINES = Path.of("src", "test", "resources", "baselines");
    private static final Path ARTIFACTS = Path.of("build", "playwright-artifacts");
    private static final String HIDE_LIVE_WIDGETS = "[data-testid='Chat.Launcher'] { visibility: hidden !important; }";
    private static final double ALLOWED_DIFFERENT_PIXELS_PERCENT = 0.05;
    private static final boolean UPDATE_BASELINES = "1".equals(System.getenv("UPDATE_BASELINES"));

    private final Path baselineDir;
    private final String evidenceName;

    public VisualCheck(Page page, String evidenceName) {
        String os = System.getProperty("os.name").toLowerCase(Locale.ROOT).split(" ")[0];
        String browser = page.context().browser().browserType().name();
        this.baselineDir = BASELINES.resolve(os + "-" + browser);
        this.evidenceName = evidenceName;
    }

    public ImageComparisonResult compare(Locator target, List<Locator> masked, String baselineName) throws IOException {
        byte[] actual = target.screenshot(new Locator.ScreenshotOptions()
                .setAnimations(ScreenshotAnimations.DISABLED)
                .setCaret(ScreenshotCaret.HIDE)
                .setScale(ScreenshotScale.CSS)
                .setMask(masked)
                .setStyle(HIDE_LIVE_WIDGETS));
        Path baseline = baselineDir.resolve(baselineName + ".png");
        if (UPDATE_BASELINES) {
            Files.createDirectories(baselineDir);
            Files.write(baseline, actual);
        }
        if (Files.notExists(baseline)) {
            Path kept = Files.write(artifact("actual"), actual);
            throw new IllegalStateException("No baseline at " + baseline + "; this run's capture is " + kept
                    + ". Baselines are written in the pinned image (playwright-snapshots.md §7).");
        }
        ImageComparisonResult result = new ImageComparison(
                ImageIO.read(baseline.toFile()),
                ImageIO.read(new ByteArrayInputStream(actual)))
                .setAllowingPercentOfDifferentPixels(ALLOWED_DIFFERENT_PIXELS_PERCENT)
                .compareImages();
        if (result.getImageComparisonState() != ImageComparisonState.MATCH) {
            attach("expected", baseline);
            attach("actual", Files.write(artifact("actual"), actual));
            ImageIO.write(result.getResult(), "png", artifact("diff").toFile());
            attach("diff", artifact("diff"));
        }
        return result;
    }

    private Path artifact(String kind) throws IOException {
        Files.createDirectories(ARTIFACTS);
        return ARTIFACTS.resolve(evidenceName + "." + kind + ".png");
    }

    private static void attach(String name, Path png) throws IOException {
        try (InputStream content = Files.newInputStream(png)) {
            Allure.attachment(name, "image/png", content, AttachmentOptions.withFileExtension("png"));
        }
    }
}
```

- **Kept files** sit beside `BaseTest`'s failure evidence: `build/playwright-artifacts/<Class>.<method>.actual.png`
  and `.diff.png`, which the CI references already upload on failure. The diff is the actual image with a
  red rectangle around every differing region; `SIZE_MISMATCH` keeps the actual unmarked.
- **Allure** gets three plain image attachments — `expected`, `actual`, `diff` — attached **before** the
  test's assertion fails, so the report carries them. The `try` is try-with-resources around a stream in an
  I/O helper; nothing is caught.
- **No baseline is a failure, never a silent pass.** The capture is kept so a reviewer can see what the
  missing baseline would be.
- **`UPDATE_BASELINES=1`** writes every capture as its baseline before comparing, so the run passes and the
  new PNGs show in `git diff`. It is set only by §7's command — never in CI (`qa/cicd/ci-conventions`).
- The two `if`s live in the helper; the test stays a straight line.

## 5. The page object and the test

```java
package com.example.uitests.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

import java.util.List;

public final class PricingPage {
    private final Page page;
    private final Locator planTable;
    private final Locator promoBadge;
    private final Locator promoPrice;

    public PricingPage(Page page) {
        this.page = page;
        this.planTable = page.getByTestId("Pricing.PlanTable").describe("Plan table");
        this.promoBadge = planTable.getByTestId("Pricing.PromoBadge").describe("Promo badge");
        this.promoPrice = planTable.getByTestId("Pricing.PromoPrice").describe("Promo price");
    }

    public void open() {
        page.navigate("/pricing");
        planTable.waitFor();
    }

    public Locator planTable() {
        return planTable;
    }

    public Locator promoPrice() {
        return promoPrice;
    }

    public Locator promoBadge() {
        return promoBadge;
    }

    public List<Locator> rotatingContent() {
        return List.of(promoBadge);
    }
}
```

`open()` returns once the plan table is visible; the app renders it only after the plans arrive (its
skeleton has its own test id). `rotatingContent()` names what changes daily, so the page object — not the
test — owns which regions are masked.

```java
package com.example.uitests.tests;

import com.example.uitests.pages.PricingPage;
import com.example.uitests.support.BaseTest;
import com.example.uitests.support.VisualCheck;
import com.github.romankh3.image.comparison.model.ImageComparisonResult;
import com.github.romankh3.image.comparison.model.ImageComparisonState;
import com.microsoft.playwright.Browser;
import com.microsoft.playwright.options.ReducedMotion;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.io.IOException;
import java.lang.reflect.Method;

import static org.assertj.core.api.Assertions.assertThat;

public class PricingVisualTest extends BaseTest {
    private PricingPage pricingPage;
    private VisualCheck visual;

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions()
                .setViewportSize(1280, 720)
                .setLocale("en-US")
                .setTimezoneId("UTC")
                .setReducedMotion(ReducedMotion.REDUCE);
    }

    @BeforeMethod(alwaysRun = true)
    public void prepareVisualCheck(Method method) {
        page.clock().setFixedTime("2026-10-10T09:00:00Z");
        pricingPage = new PricingPage(page);
        visual = new VisualCheck(page, getClass().getSimpleName() + "." + method.getName());
    }

    @Test(groups = "visual")
    public void Should_MatchApprovedPlanTable_When_PlansLoad() throws IOException {
        pricingPage.open();

        ImageComparisonResult result = visual.compare(
                pricingPage.planTable(), pricingPage.rotatingContent(), "Pricing.PlanTable");

        assertThat(result.getImageComparisonState())
                .as("Pricing.PlanTable against its baseline, %.3f%% mean colour difference", result.getDifferencePercent())
                .isEqualTo(ImageComparisonState.MATCH);
    }
}
```

- `contextOptions()` is the only way the class changes the context; `BaseTest` adds `BASE_URL` and the video
  folder after calling it. A signed-in page adds `setStorageStatePath(AuthSetup.USER_STATE)` here
  (`ui-test-author/playwright/references/lifecycle.md` §6).
- The clock is frozen in the class's `@BeforeMethod`, which TestNG runs after `BaseTest.openContext` and
  before the test, so the app's first `Date.now()` already reads the fixed instant.
- One logical assertion: the comparison state equals `MATCH`. The description carries the difference, and
  the three images are already in Allure.
- One comparison per test, so the evidence name `<Class>.<method>` identifies the images.

## 6. Tolerance — the comparator's knobs

| Setter on `ImageComparison` | Meaning | Default |
|---|---|---|
| `setPixelToleranceLevel(double)` | How far apart two pixels' colours may be and still count as equal, `0.0`–`0.99` | `0.1` |
| `setAllowingPercentOfDifferentPixels(double)` | The share of differing pixels, in percent (`0.0`–`100.0`), still reported as `MATCH` | `0.0` |
| `setExcludedAreas(List<Rectangle>)` | Fixed pixel rectangles skipped by the comparison (`new Rectangle(minX, minY, maxX, maxY)`) | none |
| `setThreshold(int)` | How close differing pixels must be to merge into one rectangle on the diff image — **not** a tolerance | `5` |
| `setMinimalRectangleSize(Integer)` | Drops smaller rectangles from the result | `1` |

- **Gate on `getImageComparisonState()`** — `MATCH`, `MISMATCH` or `SIZE_MISMATCH`. `getDifferencePercent()`
  is the mean colour difference across every pixel (`0` on a `MATCH`), not a count of differing pixels; it
  belongs in the failure message, not in the gate.
- Keep `setAllowingPercentOfDifferentPixels` tight (≤ 0.1). Mask the noisy region instead of loosening the
  whole image.
- Prefer `setMask` over `setExcludedAreas`: a mask follows the element wherever the layout puts it; an
  excluded rectangle is a coordinate that breaks on the next layout change.
- A `SIZE_MISMATCH` means the element's box changed — a real layout change, or a viewport the class forgot
  to fix in `contextOptions()`.

## 7. Generating and updating baselines — only in the pinned image

Rendering differs by OS, fonts, GPU and browser build, so a baseline is valid only where it was made. The
pinned image (`mcr.microsoft.com/playwright/java:v1.63.0-noble`) ships the 1.63 browsers, OpenJDK 25 and
Maven — **no JDK 21, no Gradle, no cloud CLI** — while J1's build pins a Java 21 toolchain. The command
runs as the image's default user, root, so it installs JDK 21 itself; the Gradle wrapper fetches Gradle.

```bash
docker run --rm --platform linux/amd64 --ipc=host \
  -v "$PWD":/work -w /work \
  -e BASE_URL -e E2E_USER -e E2E_PASSWORD -e UPDATE_BASELINES=1 \
  mcr.microsoft.com/playwright/java:v1.63.0-noble \
  bash -c 'apt-get update && apt-get install -y --no-install-recommends openjdk-21-jdk-headless \
    && JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew --no-daemon visualTest'
```

- `--platform linux/amd64` matches the CI runners; on an Apple-silicon Mac it emulates amd64 instead of
  pulling the arm64 image, whose rendering is not guaranteed to match.
- `--ipc=host` is Playwright's Docker recommendation for Chromium.
- `BASE_URL` must be reachable **from inside** the container: a deployed test environment, or
  `host.docker.internal` for an app on the developer's machine. `E2E_USER` / `E2E_PASSWORD` are passed only
  when a visual class is signed in (`AuthSetup`, lifecycle.md §6).
- Then review every changed PNG in `git diff` and commit them in the PR that changed the UI. On a Linux host
  the files come out root-owned; `chown` them before committing.
- Drop `UPDATE_BASELINES=1` and the same command **verifies** in the image — the way to reproduce a nightly
  failure locally.
- In a multi-module build the task is `:e2e:visualTest`, as in the CI references.

## 8. The nightly visual job

The job runs §7's command without `UPDATE_BASELINES`. It is a `docker run` step on the runner, not a
container job, so the credential fetch stays on the runner, where the cloud CLI is:

```yaml
  visual:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v6
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: Fetch test credentials from Key Vault
        run: |
          echo "BASE_URL=$(az keyvault secret show --vault-name kv-qa --name base-url --query value -o tsv)" >> "$GITHUB_ENV"
          echo "E2E_USER=$(az keyvault secret show --vault-name kv-qa --name e2e-user --query value -o tsv)" >> "$GITHUB_ENV"
          PASSWORD=$(az keyvault secret show --vault-name kv-qa --name e2e-password --query value -o tsv)
          echo "::add-mask::$PASSWORD"
          echo "E2E_PASSWORD=$PASSWORD" >> "$GITHUB_ENV"
      - name: Visual tests in the pinned image
        run: |
          docker run --rm --ipc=host -v "$PWD":/work -w /work \
            -e BASE_URL -e E2E_USER -e E2E_PASSWORD \
            mcr.microsoft.com/playwright/java:v1.63.0-noble \
            bash -c 'apt-get update && apt-get install -y --no-install-recommends openjdk-21-jdk-headless \
              && JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew --no-daemon :e2e:visualTest'
      - name: Upload visual evidence
        uses: actions/upload-artifact@v5
        if: failure()
        with:
          name: playwright-artifacts-visual
          path: e2e/build/playwright-artifacts
          retention-days: 14
```

- **GitHub Actions** — as above; the job sits in the workflow `qa-java:ci-pipelines` gates to the schedule.
  A `container:` job would run `azure/login` inside the image, which has no Azure CLI.
- **Azure Pipelines** — the same `docker run` in a `script` step on the Microsoft-hosted `ubuntu-latest`
  agent, after the `AzureCLI@2` fetch; a secret variable reaches the step only through its `env:` mapping
  (`E2E_PASSWORD: $(E2E_PASSWORD)`). A container job cannot install JDK 21 there: it has no `sudo`.
- **GitLab CI** — `image: mcr.microsoft.com/playwright/java:v1.63.0-noble` with `rules: - if:
  $CI_PIPELINE_SOURCE == "schedule"`; the job runs as root, so its `script` is the `apt-get` line and
  `./gradlew :e2e:visualTest`. The image has no cloud CLI, so `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come
  from masked, protected CI/CD variables, not the fetch the other jobs run.
- Allure results upload as in the UI job (`allure-results-ui-<n>`); the three images are in them.

## 9. A generated PDF is not a visual target

`page.pdf()` embeds a creation date and a document ID, so its bytes never equal a baseline, and a byte
comparison is no visual check. Assert the document's text with a PDF library in the suite that owns the
document, or screenshot the HTML that the PDF is printed from — with this reference's helper.

## Anti-patterns

- **`assertThat(page).hasScreenshot()` / `HasScreenshotOptions`.** They do not exist in Java. *Fix:* §4.
- **A baseline made on a dev box or a CI runner without the image.** *Fix:* §7, nowhere else.
- **A missing baseline that silently becomes the new baseline.** Every run then passes. *Fix:* fail on a
  missing baseline; write baselines only with `UPDATE_BASELINES=1` in the image.
- **`Thread.sleep` or `waitForTimeout` before the capture.** *Fix:* the page object's ready signal, the
  frozen clock, masks.
- **A full-page capture of a data-heavy page.** *Fix:* the element, with its rotating regions masked.
- **Raising the allowed percentage until it passes.** *Fix:* mask the noisy region; keep the tolerance tight.
- **A second `Playwright.create()` or browser in a visual class.** *Fix:* extend `BaseTest`; override
  `contextOptions()`.
- **A `try`/`finally` or a re-attaching `@AfterMethod` in the test class.** *Fix:* the helper attaches; `BaseTest`
  keeps the failure evidence.
- **Visual tests in the PR gate.** *Fix:* `groups = "visual"`, the nightly `visualTest` task.

## Rules

- Java has no screenshot assertion: capture with `locator.screenshot`, compare with the comparator, assert
  the state with AssertJ and `.as(...)`.
- Baselines live in `src/test/resources/baselines/<os>-<browser>/`, are committed, and are written only in
  `mcr.microsoft.com/playwright/java:v1.63.0-noble`, by a person, with `UPDATE_BASELINES=1`.
- Stabilize through the page object, the frozen clock, `contextOptions()` and masks — never a sleep.
- Actual and diff images land in `build/playwright-artifacts/<Class>.<method>.{actual,diff}.png` and are attached
  to Allure with `Allure.attachment(..., AttachmentOptions.withFileExtension("png"))`.
- Visual tests carry `groups = "visual"` and run nightly through `visualTest`.

## Cross-references

- `qa/java/skills/ui-test-author/playwright` — `BaseTest`, page objects, the build and its Versions table.
- `qa/java/skills/ui-test-author/playwright/references/emulation-and-mobile-web.md` — viewport, media
  features and `page.clock()`.
- `qa/java/skills/evidence-capture` — screenshot options in full, the failure evidence, deliberate captures.
- `references/percy.md`, `references/applitools.md` — the hosted siblings, which remove the pinned-image
  discipline.
- `qa/cicd/java/skills/ci-pipelines` — the UI job, its artifact upload and the schedule gate.
- `qa/reporting/java/skills/test-reports` — Allure 3 wiring.
- `qa-typescript:visual-regression` — the Node runner's `toHaveScreenshot`, which this lane cannot use.
