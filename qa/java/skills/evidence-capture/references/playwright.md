# Evidence capture — Playwright for Java 1.63

Every capture API in its Java spelling, with the version it shipped in. `SKILL.md` decides what to capture
and where it lands; this file is how. The samples extend
`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java` (`com.example.uitests.support.BaseTest`),
which owns the browser, the context, the page and the failure evidence. A sample adds its own
`@BeforeMethod` / `@AfterMethod(alwaysRun = true)`; TestNG runs a subclass's `@BeforeMethod` after
`BaseTest.openContext` and its `@AfterMethod` before `BaseTest.closeContext`, so the page is open in both.

## 1. Screenshots

### 1.1 The API — `page.screenshot`, `locator.screenshot`

`page.screenshot(new Page.ScreenshotOptions()...)` returns `byte[]`; `setPath(...)` also writes the file.

| Setter | Values | Note |
|---|---|---|
| `setPath(Path)` | file path | Format from the extension; relative to the working directory (the Gradle module) |
| `setFullPage(boolean)` | `false` | The whole scrollable page. Page only |
| `setClip(x, y, width, height)` | doubles | Page only |
| `setType(ScreenshotType)` | `PNG` · `JPEG` · `WEBP` [1.62] | `setQuality(0–100)`: jpeg default 80; webp default 100 is lossless |
| `setMask(List<Locator>)` | locators | Covers each match with a box, invisible matches included; `setMaskColor("#00FF00")` [1.35] |
| `setAnimations(ScreenshotAnimations)` | `ALLOW` · `DISABLED` | Disabled fast-forwards finite animations and resets infinite ones |
| `setCaret(ScreenshotCaret)` | `HIDE` · `INITIAL` | Default `HIDE` |
| `setScale(ScreenshotScale)` | `DEVICE` · `CSS` | `CSS` keeps HiDPI images small |
| `setStyle(String)` | CSS text [1.41] | Applied during capture; pierces shadow DOM and iframes — hides a clock, an avatar, a token. There is no `setStylePath` in Java |
| `setOmitBackground(boolean)` | `true` | Transparent background; not for jpeg |
| `setTimeout(double)` | ms | |

- `locator.screenshot(new Locator.ScreenshotOptions()...)` takes the same setters except `setFullPage` and
  `setClip`. It waits for actionability, scrolls the element into view and clips to it; anything covering
  the element shows in the image.
- `ElementHandle.screenshot` is discouraged; use the locator form.
- A one-off from the shell: `./gradlew playwright --args="screenshot --full-page <url> <file>"`.

### 1.2 The failure screenshot

`BaseTest.keepScreenshot` takes `setPath(build/playwright-artifacts/<Class>.<method>.png).setFullPage(true)`
on failure, before the trace stops and the context closes, and attaches it. Its narrow
`PlaywrightException` catch is the one catch in `BaseTest` (plan D29).

### 1.3 A screenshot at a chosen point

An `Evidence` helper sits beside the page objects and is built in the test class's own `@BeforeMethod`. The
test calls it; it never calls `page`.

```java
package com.example.uitests.support;

import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.ScreenshotAnimations;
import com.microsoft.playwright.options.ScreenshotCaret;
import com.microsoft.playwright.options.ScreenshotScale;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;

import java.io.ByteArrayInputStream;

public final class Evidence {
    private final Page page;

    public Evidence(Page page) {
        this.page = page;
    }

    public void screenshot(String name) {
        byte[] png = page.screenshot(new Page.ScreenshotOptions()
                .setFullPage(true)
                .setAnimations(ScreenshotAnimations.DISABLED)
                .setCaret(ScreenshotCaret.HIDE)
                .setScale(ScreenshotScale.CSS));
        Allure.attachment(name, "image/png", new ByteArrayInputStream(png), AttachmentOptions.withFileExtension("png"));
    }
}
```

A test calls `evidence.screenshot("Cart.BeforeCheckout")`. A screenshot is evidence, not an assertion:
Java has no screenshot assertion, and comparing one to a baseline is `qa/java/skills/visual-regression`.

## 2. Video

- **Recording** is a context option: `new Browser.NewContextOptions().setRecordVideoDir(Path)` and
  `setRecordVideoSize(width, height)`. `BaseTest` sets the folder (`build/playwright-videos/`) after calling
  `contextOptions()`, so a class sets only the size, in its override. The size defaults to the viewport
  scaled to fit 800×800.
- **The file is complete only after `context.close()`.** `page.video()` returns `@Nullable Video`; read it
  before the close, while the page exists.
- **Java's `video.saveAs(path)` throws until the page or context is closed** — unlike Node, where it waits.
  `video.path()` throws against a remote browser (Docker `run-server`, a grid); `saveAs` works there.
  `video.delete()` removes the raw file.
- `BaseTest.closeContext` therefore reads `page.video()`, closes the context, `saveAs`-es the video only on
  failure and always calls `delete()`, so `build/playwright-videos/` is empty after every test.
- `videosPath` / `videoSize` were removed in 1.60. Video in 1.63 is VP8 WebM (VP9 arrives in 1.64). There
  are no video modes in Java; "keep on failure" is the `saveAs`-on-failure above. From 1.64:
  `setRecordVideoFps`.

## 3. Screencast — a recording you start and stop [1.59]

`page.screencast()` records the span you choose and annotates it — the Playwright team's "agentic video
receipt".

| Call | Does |
|---|---|
| `start(new Screencast.StartOptions().setPath(p).setSize(w, h).setQuality(q).setOnFrame(f -> …))` | Starts recording; `setPath` gets a `.webm` on `stop()`; `setOnFrame` streams JPEG frames (`ScreencastFrame`). Returns `AutoCloseable` |
| `stop()` | Ends the recording and writes the path |
| `showActions(new Screencast.ShowActionsOptions().setPosition(AnnotatePosition.TOP_RIGHT).setCursor(ScreencastCursor.POINTER).setDuration(500))` / `hideActions()` | Annotates each action. Returns `AutoCloseable` |
| `showChapter(title, new Screencast.ShowChapterOptions().setDescription(d).setDuration(2000))` | A centred chapter card over a blurred page |
| `showOverlay(html, new Screencast.ShowOverlayOptions().setDuration(ms))` / `showOverlays()` / `hideOverlays()` | Custom HTML over the page; `showOverlay` returns `AutoCloseable` |

- `AnnotatePosition` is an enum — `TOP_LEFT`, `TOP`, `TOP_RIGHT`, `BOTTOM_LEFT`, `BOTTOM`, `BOTTOM_RIGHT`. The
  1.59 release-note samples pass `"top-right"`, which does not compile in Java.
- `AutoCloseable.close()` declares `Exception`, so the samples call `stop()` and `hideActions()` directly
  instead of try-with-resources.
- `setFontSize` is deprecated from 1.64. From 1.64: `StartOptions.setFps`, `ShowActionsOptions.setStyle`.

Known issues, open or regressed on 2026-10-10:

- **The video is lost if the page closes before `stop()`** (issue #41608). Stop first, always.
- `BaseTest`'s own video and trace already run a screencast on every page. When one is running, its
  configuration wins over the size passed to `start()`; whether the receipt's path is still written beside
  the running video has not been run in this library.
- Tracing clamps the capture size and pads with grey (#42274).
- There is no `saveAs`; the path is local to the client process even against a remote browser (#42392).

A receipt starts in the class's `@BeforeMethod` and stops in its `@AfterMethod`, which runs before
`BaseTest` closes the context. The stop follows the D29 pattern, because a crashed page cannot stop its
screencast and a failing `@AfterMethod` would skip the rest of the class:

```java
package com.example.uitests.tests;

import com.example.uitests.pages.CheckoutPage;
import com.example.uitests.support.BaseTest;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.Screencast;
import com.microsoft.playwright.options.AnnotatePosition;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class CheckoutReceiptTest extends BaseTest {
    private static final System.Logger LOG = System.getLogger(CheckoutReceiptTest.class.getName());

    private Path receipt;
    private CheckoutPage checkoutPage;

    @BeforeMethod(alwaysRun = true)
    public void startReceipt(Method method) {
        receipt = Path.of("build", "playwright-artifacts", getClass().getSimpleName() + "." + method.getName() + ".receipt.webm");
        page.screencast().start(new Screencast.StartOptions().setPath(receipt));
        page.screencast().showActions(new Screencast.ShowActionsOptions().setPosition(AnnotatePosition.TOP_RIGHT));
        checkoutPage = new CheckoutPage(page);
    }

    @Test
    public void Should_ConfirmOrder_When_CartHasOneItem() {
        checkoutPage.open();
        chapter("Pay");
        checkoutPage.payWithSavedCard();

        assertThat(checkoutPage.confirmation()).hasText("Order confirmed");
    }

    @AfterMethod(alwaysRun = true)
    public void keepReceipt() throws IOException {
        if (screencastStopped()) {
            try (InputStream content = Files.newInputStream(receipt)) {
                Allure.attachment("receipt", "video/webm", content, AttachmentOptions.withFileExtension("webm"));
            }
        }
    }

    private boolean screencastStopped() {
        try {
            page.screencast().stop();
            return true;
        } catch (PlaywrightException e) {
            LOG.log(System.Logger.Level.WARNING, "Receipt not saved to {0}: {1}", receipt, e.getMessage());
            return false;
        }
    }

    private void chapter(String title) {
        page.screencast().showChapter(title);
    }
}
```

The catch sits in a helper that turns one named exception into a boolean and logs it, never in the hook
body — the same rule the writer applies to `BaseTest.keepScreenshot`. The receipt is kept for a passing and
a failing test alike; it sits beside the failure evidence, so CI
uploads it with a failed run's artifacts and Allure carries it on every run.

## 4. Trace

### 4.1 The failure trace

`BaseTest.openContext` starts the trace on every context; `keepTrace` stops it with a path on failure, and
a pass calls `stop()` with no path, which discards it.

| `Tracing.StartOptions` setter | Records | Since |
|---|---|---|
| `setScreenshots(true)` | Screenshots for the timeline filmstrip | 1.12 |
| `setSnapshots(true)` | A DOM snapshot and the network on every action | 1.12 |
| `setSources(true)` | The test source beside each action; needs `PLAYWRIGHT_JAVA_SRC` (`:`-separated, `;` on Windows), which J1's `build.gradle.kts` sets to `src/test/java` on the `test` task | 1.17 |
| `setAriaSnapshots(true)` | An aria snapshot on every action — the viewer's **Display Aria** mode | 1.63 |
| `setScreenSnapshots(true)` | A screenshot on every action | 1.63 |
| `setTitle(String)` / `setName(String)` | The viewer title / the intermediate file prefix | 1.17 |
| `setLive(true)` | An unarchived trace updated in real time | 1.59 |

`BaseTest` sets the first three. Adding the 1.63 pair is an edit to `BaseTest.openContext`, never a second
tracer; they make the zip larger.

**Raw tracing does not record assertions.** The Node runner's `trace` option records `expect` calls and
`test.step`s; `context.tracing()` does not, and Java has no runner tracing. The trace shows the actions up to
the failure; the assertion message is in the TestNG result and in Allure.

### 4.2 Making a trace readable

- `locator.describe("Checkout button")` [1.53] names a locator in traces and reports; the writer requires it
  on every page-object locator whose role and name do not identify it.
- `tracing().group(name)` [1.49] / `groupEnd()` groups actions in the viewer — the Java stand-in for
  `test.step`. `group` returns `AutoCloseable`; call `groupEnd()` instead of try-with-resources. A page-object
  method wraps its actions so the trace reads as the journey:

```java
public void checkOut() {
    page.context().tracing().group("Check out");
    reviewButton.click();
    payButton.click();
    page.context().tracing().groupEnd();
}
```

- Allure's `@Step` on the same method names it in the report; the two coexist.

### 4.3 Chunks

`tracing().startChunk(new Tracing.StartChunkOptions().setTitle(t))` / `stopChunk(new Tracing.StopChunkOptions().setPath(p))`
[1.15] cut several traces from one `start()` — for a context that outlives one test, which `BaseTest`'s
context per test does not. Inside `BaseTest` there is nothing to chunk.

## 5. HAR

- **Per test, on purpose** — `tracing().startHar(path, options)` [1.60] / `stopHar()`. One HAR per tracing at
  a time; it records alongside `BaseTest`'s trace. The imports are those of §3 plus
  `com.microsoft.playwright.Tracing` and `com.microsoft.playwright.options.HarContentPolicy`; the class's
  tests and page objects are left out.

```java
public class OrdersNetworkTest extends BaseTest {
    private Path har;

    @BeforeMethod(alwaysRun = true)
    public void startHar(Method method) {
        har = Path.of("build", "playwright-artifacts", getClass().getSimpleName() + "." + method.getName() + ".har");
        page.context().tracing().startHar(har, new Tracing.StartHarOptions()
                .setContent(HarContentPolicy.OMIT)
                .setUrlFilter("**/api/**"));
    }

    @AfterMethod(alwaysRun = true)
    public void keepHar() throws IOException {
        page.context().tracing().stopHar();
        try (InputStream content = Files.newInputStream(har)) {
            Allure.attachment("network.har", "application/json", content, AttachmentOptions.withFileExtension("har"));
        }
    }
}
```

- **For every test of a class** — `setRecordHarPath(...)`, `setRecordHarContent(...)`, `setRecordHarMode(...)`
  and `setRecordHarUrlFilter(...)` in the class's `contextOptions()`. The HAR is written on `context.close()`
  and the path is the same for every test of the class, so prefer the per-test form.
- `HarContentPolicy`: `OMIT` (no bodies — the PII-safe default), `EMBED`, or `ATTACH` (the default for a
  `.zip` path). `HarMode.MINIMAL` keeps only what replay needs.
- HAR and traces include WebSocket traffic since 1.61.
- From the shell: `./gradlew playwright --args="open --save-har=evidence/app.har --save-har-glob=**/api/** <url>"`.
- Replaying or updating a HAR (`routeFromHAR`) is `qa/java/skills/network-mocking`.

## 6. Attachments (allure-java 3.0)

| Call | Use |
|---|---|
| `Allure.attachment(name, type, InputStream, AttachmentOptions.withFileExtension(ext))` | A file or bytes with a type and an extension — every sample above |
| `Allure.attachment(name, String content)` | Short text |
| `@Attachment(value = "…", type = "…")` on a method returning `byte[]` or `String` | Needs the AspectJ weaver the Allure Gradle plugin enables |

- The trace type is `application/vnd.allure.playwright-trace`, which Allure opens in the trace viewer.
- allure-java 3.0 shows each runtime attachment as a step with the attachment's name, in creation order.
- `Allure.addAttachment(...)` is the removed 2.x API. Adapter wiring, history and publishing are
  `qa/reporting/java/skills/test-reports`.

## 7. No `error-context.md` in Java

The Node runner writes `error-context.md` (the error plus an AI-mode aria snapshot) on every failure. Java
does not. The nearest Java evidence is the screenshot, the trace with `setAriaSnapshots(true)` read through
`trace snapshot`, or an explicit capture:
`page.ariaSnapshot(new Page.AriaSnapshotOptions().setMode(AriaSnapshotMode.AI))` [1.59], attached as
`text/plain` from a helper. Adding it to every failure is a `BaseTest` change, under the D29 catch.

## 8. Viewing and reading evidence

| Command | Does |
|---|---|
| `./gradlew playwright --args="show-trace <zip>"` | The trace viewer, through J1's `playwright` `JavaExec` task (`com.microsoft.playwright.CLI`) |
| https://trace.playwright.dev | Loads a trace in the browser without uploading it; `?trace=<url>` opens a hosted one (CORS applies) |
| `npx playwright@1.63.0 trace open <zip>` | Opens a trace for the analysis commands below — the agent route [1.59]. Without Node: `./gradlew playwright --args="trace open <zip>"` (plan D39) |
| `trace errors` · `console` · `requests` · `request <id>` | Errors, page log, network |
| `trace actions [--grep <text>] [--errors-only]` · `action <id>` | The action list and one action's detail |
| `trace snapshot <id> --name before\|after` · `screenshot <id>` | The DOM or the screen at an action |
| `trace attachments` · `attachment <n>` · `close` | Attachments in the trace; close removes the extracted data in `.playwright-cli/trace/` |
| Allure | Opens an attached `application/vnd.allure.playwright-trace` in the trace viewer; the viewer page needs internet access, the trace bytes are not uploaded |

Prefix each analysis command with `npx playwright@1.63.0` or wrap it in `./gradlew playwright --args="…"`;
the open trace is remembered in the working directory between calls. `trace install-skill` installs
Microsoft's trace skill for agents; this skill already documents the commands, so it is optional.

## 9. Exploratory capture: Playwright MCP and `playwright-cli`

| Capture | Playwright MCP (`--caps=devtools` for video and trace) | `playwright-cli` |
|---|---|---|
| Screenshot | `mcp__playwright__browser_take_screenshot` `{ filename, fullPage, type: "png", scale: "css" }` — with `filename` no image is returned and the path resolves against the workspace root [MCP 0.0.74] | `screenshot [ref] --filename=<f> --full-page` (`--type png\|jpeg\|webp`, `--hires`) |
| Start video | `mcp__playwright__browser_start_video` `{ filename, size: { width, height }, fps, cursor }` (fps default 25) | `video-start <f.webm> --size=1280x720 --fps=25 --cursor` |
| Stop video | `mcp__playwright__browser_stop_video` | `video-stop` |
| Chapters and action overlays | not granted to the qa agents | `video-chapter <title>`, `video-show-actions`, `video-hide-actions` |
| Start trace | `mcp__playwright__browser_start_tracing` | `tracing-start` |
| Stop trace | `mcp__playwright__browser_stop_tracing` — returns links to the trace files | `tracing-stop` — traces under `.playwright-cli/traces/` |
| Page state as text | `mcp__playwright__browser_snapshot` `{ filename }` | `snapshot --filename=<f>` (snapshots go to `.playwright-cli/page-*.yml`, not into the context) |

- MCP output without an explicit `filename` goes to the server's `--output-dir` (`.playwright-mcp/`);
  videos under its `videos/` folder.
- The CLI is `npm i -g @playwright/cli@latest`. It keeps an in-memory profile by default and closes a
  headless session after an hour.
- Both run their own Playwright on Node, independent of the suite's 1.63 binding. Open their traces with §8.

## 10. Codegen's recorder

`./gradlew playwright --args="codegen --target java --test-id-attribute data-testid -o build/codegen/Recorded.java <url>"`
records actions into code (`--target java` or `java-junit`; there is no TestNG target). `--save-har`,
`--save-storage`, `--device` and `--viewport-size` also apply. The toolbar has **Pick locator**, **Assert
visibility**, **Assert text**, **Assert value** and **Assert snapshot** (emits `matchesAriaSnapshot`). The
recording is a draft: every locator is rewritten against the ladder in
`qa/java/skills/ui-test-author/playwright/references/locators.md`, and it is never committed.

## 11. Size and CI

- Java has no blob reporter: each shard uploads its own `build/playwright-artifacts/` on failure and its
  own `build/allure-results/` on every run; the Allure publish job merges the results.
- Never upload `build/playwright-videos/` — it is empty after a run, and mid-run it holds only the running
  test's raw recording.
- Size levers: `ScreenshotScale.CSS` for HiDPI screenshots; `JPEG` or `WEBP` with `setQuality(< 100)` for
  ad-hoc screenshots; a smaller `setRecordVideoSize`; `HarContentPolicy.OMIT`.
- Upload paths and retention: `qa/cicd/java/skills/ci-pipelines` and `qa/cicd/ci-conventions`.
