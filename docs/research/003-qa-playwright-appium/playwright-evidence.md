# Playwright evidence capture — screenshots, visual/ARIA snapshots, video, screencast, tracing, HAR, codegen, CI artifacts

Researched 2026-10-10 against primary sources fetched the same day. Anything not confirmed from a primary source is marked **UNVERIFIED**. Anything I inferred rather than read is marked **(inference)**.

## 0. Version baseline — read this first

- **Node `@playwright/test` / `playwright` is 1.64.0**, released 2026-10-07 (npm `latest` = 1.64.0). Source: https://github.com/microsoft/playwright/releases/tag/v1.64.0 and https://registry.npmjs.org/@playwright/test/latest
- **Java, .NET and Python are on 1.63.0. None of them has shipped 1.64 yet.** Java v1.63.0 came out 2026-09-14 (Maven `latest` 1.63.0), .NET v1.63.0 on 2026-09-21 (NuGet `Microsoft.Playwright` 1.63.0), Python v1.63.0 on 2026-09-15 (PyPI 1.63.0). Sources: https://github.com/microsoft/playwright-java/releases, https://github.com/microsoft/playwright-dotnet/releases, https://github.com/microsoft/playwright-python/releases, https://repo1.maven.org/maven2/com/microsoft/playwright/playwright/maven-metadata.xml, https://api.nuget.org/v3-flatcontainer/microsoft.playwright/index.json, https://pypi.org/pypi/playwright/json
- **Trap: the playwright.dev docs for Java, .NET and Python already list 1.64-only options as "Added in: v1.64"**, for example `Screencast.StartOptions.setFps` and `ShowActionsOptions.setStyle` on https://playwright.dev/java/docs/api/class-screencast. Those options cannot be called until each binding ships 1.64. Skills must check the installed version, not the docs page. The Java, .NET and Python release-notes pages stop at 1.63: https://playwright.dev/java/docs/release-notes
- Integration package versions current today:
  - `pytest-playwright` 0.10.0 (2026-10-08): https://github.com/microsoft/playwright-pytest/releases/tag/v0.10.0
  - `allure-playwright` (JS) 3.13.0: https://github.com/allure-framework/allure-js/releases
  - `allure-java` 3.0.0 (2026-09-11, Java 17 baseline): https://github.com/allure-framework/allure-java/releases/tag/3.0.0
  - `Allure.NUnit` 2.15.0 stable, 3.0.0-preview.1: https://github.com/allure-framework/allure-csharp/releases
  - `allure-pytest` 2.16.2: https://pypi.org/pypi/allure-pytest/json
  - Allure Report 3 CLI v3.20.1: https://github.com/allure-framework/allure3/releases
- How these were verified:
  - Docs source markdown at tag `v1.64.0`: https://github.com/microsoft/playwright/tree/v1.64.0/docs/src (this is what playwright.dev renders).
  - Generated binding sources at `v1.63.0` for Java, .NET and Python, for exact spellings.
  - `npx playwright <cmd> --help` run locally against an installed `@playwright/test@1.64.0`.
  - Runner source: https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/index.ts

---

## 1. Screenshots

### 1.1 API — `page.screenshot`, `locator.screenshot`, `elementHandle.screenshot`
- `Page.screenshot` (since 1.8) returns a Buffer/bytes. Options: `animations`, `omitBackground`, `quality`, `path`, `scale`, `caret`, `type`, `mask`, `timeout`, `signal` (JS), `fullPage`, `clip`, `maskColor`, `style`. Source: https://playwright.dev/docs/api/class-page#page-screenshot and https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/class-page.md
- `Locator.screenshot` (since 1.14) takes the same options **without `fullPage` and `clip`**. It waits for actionability, scrolls the element into view, and clips to the element. Covering elements show up in the image. A scrollable container shows only its visible part. Source: https://playwright.dev/docs/api/class-locator#locator-screenshot
- `ElementHandle.screenshot` is **discouraged**; use `Locator.screenshot`. Source: https://playwright.dev/docs/api/class-elementhandle#element-handle-screenshot
- Option semantics, all from https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/params.md (rendered at https://playwright.dev/docs/api/class-page#page-screenshot):
  - `fullPage` (bool, default false): captures the full scrollable page.
  - `clip` `{x, y, width, height}` (Java alias class `Clip`).
  - `mask: Locator[]`: masked elements get a `#FF00FF` box. The mask also covers invisible elements.
  - `maskColor` (CSS color, default `#FF00FF`): since **1.35** per release notes and params.md. class-page.md tags it `v1.34` (doc inconsistency).
  - `animations: "disabled" | "allow"`: default `"allow"` for screenshot, `"disabled"` for `toHaveScreenshot`. Finite animations fast-forward; infinite ones reset and replay afterwards.
  - `caret: "hide" | "initial"` (default `"hide"`).
  - `scale: "css" | "device"`: default `"device"` for screenshot, `"css"` for `toHaveScreenshot`. `"css"` keeps HiDPI images small.
  - `style` (string CSS applied during capture; it pierces Shadow DOM and iframes): since **1.41**.
  - `omitBackground` (transparency; not for jpeg).
  - `type: "png" | "jpeg" | "webp"` (default png): **`webp` since 1.62**.
  - `quality` (0–100): jpeg default 80; webp default 100 = lossless, lower values are lossy.
  - `path`: format is inferred from the extension and resolved relative to the CWD.
  - `timeout`.
- Version history:
  - `animations` and `mask`: 1.20.
  - `scale` and `caret`: 1.21. The caret is auto-hidden since 1.19.
  - `style`: 1.41.
  - WebP: 1.62.
  - Source: https://playwright.dev/docs/release-notes (Versions 1.19, 1.20, 1.21, 1.35, 1.41, 1.62)
- Per-binding spellings, verified in generated sources at v1.63.0:
  - **Java**: `page.screenshot(new Page.ScreenshotOptions().setPath(Paths.get("x.png")).setFullPage(true).setMask(List.of(loc)).setMaskColor("#00FF00").setAnimations(ScreenshotAnimations.DISABLED).setCaret(ScreenshotCaret.HIDE).setScale(ScreenshotScale.CSS).setStyle("...").setOmitBackground(true).setType(ScreenshotType.WEBP).setQuality(50).setClip(x,y,w,h).setTimeout(ms))` returns `byte[]`. `ScreenshotType` = `PNG, JPEG, WEBP`. Source: https://github.com/microsoft/playwright-java/blob/v1.63.0/playwright/src/main/java/com/microsoft/playwright/Page.java and https://github.com/microsoft/playwright-java/blob/v1.63.0/playwright/src/main/java/com/microsoft/playwright/options/ScreenshotType.java
  - **.NET**: `await Page.ScreenshotAsync(new() { Path, FullPage, Clip = new Clip{...}, Mask = new[]{ loc }, MaskColor, Animations = ScreenshotAnimations.Disabled, Caret = ScreenshotCaret.Hide, Scale = ScreenshotScale.Css, Style, OmitBackground, Type = ScreenshotType.Webp, Quality, Timeout })` returns `byte[]`. `LocatorScreenshotOptions` is used for locators. Source: https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/Options/PageScreenshotOptions.cs
  - **Python**: `page.screenshot(path=, full_page=, clip=, mask=, mask_color=, animations="disabled", caret="hide", scale="css", style=, omit_background=, type="webp", quality=, timeout=)` returns `bytes`. `timeout` also accepts `datetime.timedelta` in 1.63. Source: https://github.com/microsoft/playwright-python/blob/v1.63.0/playwright/sync_api/_generated.py
- CLI one-off: `npx playwright screenshot [--full-page] [--wait-for-selector s] [--wait-for-timeout ms] <url> <file>`. Source: `npx playwright screenshot --help` (1.64.0).

### 1.2 Test-runner automatic screenshots (Node only)
- `use.screenshot`: `'off' | 'on' | 'only-on-failure' | 'on-first-failure'`, or the object `{ mode, fullPage?, omitBackground? }`. Default `'off'`. Source: https://playwright.dev/docs/api/class-testoptions#test-options-screenshot
  - `'on-first-failure'` was added in **1.49**.
  - The object form with `fullPage` exists since **1.29**.
  - Source: https://playwright.dev/docs/release-notes (1.29, 1.49)
- How capture works, read from runner source: the runner screenshots every open page at test end with `timeout: 5000` and `caret: 'initial'`. Files are `test-failed-N.png` or `test-finished-N.png` in the test output dir, attached as `name: 'screenshot'`, `contentType: 'image/png'`. It also snapshots pages just before their context closes, so pages closed mid-test are still captured. Source: https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/index.ts (`SnapshotRecorder`, `ArtifactsRecorder`)
- **`error-context.md` attachment (since 1.53).** On any test error the runner writes `error-context.md` (`contentType: text/markdown`). It holds the errors plus an **AI-mode aria snapshot** of the page (`page.ariaSnapshot({ mode: 'ai' })`). It is cheap, text-only evidence and is what the HTML report's "Copy prompt" feeds on. Sources: https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/index.ts; the version comes from grepping the v1.52.0 and v1.53.0 sources. `testInfoError.errorContext` (1.60): https://playwright.dev/docs/api/class-testinfoerror
- No `--screenshot` or `--video` CLI flag exists for `npx playwright test`; only `--trace <mode>`. Source: `npx playwright test --help` (1.64.0).
- Manual attach: `await testInfo.attach('name', { body | path, contentType })`. The file is copied, so you may delete the original. `testStepInfo.attach` attaches to a step (1.51). Sources: https://playwright.dev/docs/api/class-testinfo#test-info-attach and https://playwright.dev/docs/api/class-teststepinfo

### 1.3 How screenshots reach reports
- **Playwright HTML report**: shows test attachments, a Traces section and image diffs. Visual-diff attachments get an expected/actual/diff slider (Trace Viewer and UI mode "Attachments" tab). Sources: https://playwright.dev/docs/trace-viewer-intro#opening-the-html-report and https://playwright.dev/docs/trace-viewer#attachments
- **allure-playwright (JS)**: add `reporter: [['allure-playwright', { resultsDir: 'allure-results', detail: true }]]`. Source: https://allurereport.org/docs/playwright/ and https://github.com/allure-framework/allure-js/blob/v3.13.0/packages/allure-playwright/README.md
  - Every `testInfo.attachments` entry (screenshot, video, trace) becomes an Allure attachment.
  - A `trace` zip is re-typed to `application/vnd.allure.playwright-trace`, which Allure opens in Trace Viewer.
  - `*-expected/-actual/-diff.png` triples become one `application/vnd.allure.image.diff` attachment.
  - Source: https://github.com/allure-framework/allure-js/blob/v3.13.0/packages/allure-playwright/src/index.ts and https://allurereport.org/docs/attachments/
  - **Compatibility: `allure-playwright >= 3.12.0` requires `@playwright/test >= 1.62.0`. For 1.53–1.61 use `allure-playwright <= 3.11.1`.** Source: https://github.com/allure-framework/allure-js/blob/v3.13.0/packages/allure-playwright/README.md
  - The diff matcher regex is `/-((expected)|(diff)|(actual))\.png$/`, so **WebP baselines (1.62+) will not get the Allure image-diff widget**. This is read from source and not executed. Source: https://github.com/allure-framework/allure-js/blob/v3.13.0/packages/allure-playwright/src/utils.ts
- **Allure rendering of the trace type.** Allure 3 opens `application/vnd.allure.playwright-trace` in a new tab. Allure 2 embeds Trace Viewer inline. The trace bytes are not uploaded, but the viewer page needs internet access. Source: https://allurereport.org/docs/attachments/
- **allure-java (TestNG/JUnit) 3.0.0**:
  - The generic API was **renamed**. It is `Allure.attachment(name, type, InputStream, AttachmentOptions.withFileExtension("png"))`. 2.x used `Allure.addAttachment(name, type, InputStream, "png")`. Source: https://github.com/allure-framework/allure-java/blob/3.0.0/allure-java-commons/src/main/java/io/qameta/allure/Allure.java (compare with https://github.com/allure-framework/allure-java/blob/2.35.5/allure-java-commons/src/main/java/io/qameta/allure/Allure.java)
  - **New `io.qameta.allure:allure-playwright` module (Java):** `AllurePlaywright.register(page|context)`, `attachScreenshot(name, page)`, `attachPageSource`, `attachConsoleMessages`, `attachPageErrors`, `attachTrace(name, Path)` (uses the playwright-trace type), `attachVideo(name, Path)`, and `startTracing(context)`, which returns an AutoCloseable `TraceSession`.
  - Automatic action steps need the AspectJ weaver. Config properties include `allure.playwright.failure.screenshot` and `allure.playwright.close.trace` / `.close.video`. It is validated against Playwright Java 1.60.0.
  - Sources: https://github.com/allure-framework/allure-java/tree/3.0.0/allure-playwright and https://github.com/allure-framework/allure-java/blob/3.0.0/allure-playwright/src/main/java/io/qameta/allure/playwright/AllurePlaywright.java
- **Allure.NUnit 2.15.0**: `AllureApi.AddAttachment(string name, string type, string path)`, `AddAttachment(name, type, byte[] content, fileExtension)` and `AddAttachment(string path, string? name = null)` (type inferred). Source: https://github.com/allure-framework/allure-csharp/blob/2.15.0/src/Allure.Net.Commons/AllureApi.cs
  - Plain NUnit equivalent: `TestContext.AddTestAttachment(string filePath, string description = null)`. Source: https://docs.nunit.org/articles/nunit/writing-tests/TestContext.html
- **allure-pytest 2.16.2**: `allure.attach.file(source, name=, attachment_type=, extension=)`. `attachment_type` accepts the `allure.attachment_type` enum (`PNG`, `WEBM`, `ZIP`, …) **or a raw MIME string**. The enum has **no** playwright-trace member, so pass `"application/vnd.allure.playwright-trace"` with `extension="zip"`. Sources: https://github.com/allure-framework/allure-python/blob/2.16.2/allure-python-commons/src/allure_commons/types.py and https://github.com/allure-framework/allure-python/blob/2.16.2/allure-python-commons/src/allure_commons/reporter.py

---

## 2. Visual comparison (`toHaveScreenshot`)

- **Node test runner only.** `PageAssertions.toHaveScreenshot` and `LocatorAssertions.toHaveScreenshot` are tagged `langs: js`, and the docs say "screenshot assertions only work with Playwright test runner". Source: https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot-1 and https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/class-pageassertions.md
- **Confirmed absent in Java, .NET and Python 1.63.** Java `PageAssertions` has only `hasTitle`, `hasURL` and `matchesAriaSnapshot`. .NET `IPageAssertions` has only `ToHaveTitleAsync`, `ToHaveURLAsync` and `ToMatchAriaSnapshotAsync`. Python has no `to_have_screenshot`. Sources:
  - https://github.com/microsoft/playwright-java/blob/v1.63.0/playwright/src/main/java/com/microsoft/playwright/assertions/PageAssertions.java
  - https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/IPageAssertions.cs
  - https://github.com/microsoft/playwright-python/blob/v1.63.0/playwright/sync_api/_generated.py
- Status of ports:
  - Python #837 was **closed "not planned"**; on 2026-04-30 a maintainer wrote "No plans to implement this." https://github.com/microsoft/playwright-python/issues/837
  - .NET: a maintainer explains that `toHaveScreenshot` and `toMatchAriaSnapshot`-to-file "require an artifact system that we have built into our Node.js implementation via our test runner". The tracking issue is still open. https://github.com/microsoft/playwright-dotnet/issues/3112 and https://github.com/microsoft/playwright-dotnet/issues/1854
  - Java #1040 is open. A community PR adding `hasScreenshot()` was **closed unmerged** (2026-07). https://github.com/microsoft/playwright-java/issues/1040 and https://github.com/microsoft/playwright-java/pull/1950
  - **What Java/.NET/Python users do instead:** take `screenshot(...)` with the same determinism options (`animations: disabled`, `caret: hide`, `scale: css`, `mask`, `style`) and diff it with a third-party or home-grown image comparer. The Playwright team names no specific library, so any recommendation is **(inference)**.
- How it works: it takes screenshots until two consecutive captures match, then compares with the golden file. The first run writes the golden and **fails**; see the 1.64 change below. Source: https://playwright.dev/docs/test-snapshots
- Options (since 1.23 unless noted):
  - `animations` (default `"disabled"`), `caret`, `clip`, `fullPage`, `mask`, `maskColor` (1.35), `stylePath` (1.41; there is **no inline `style`** for `toHaveScreenshot`), `omitBackground`, `scale` (default `"css"`).
  - `maxDiffPixels`, `maxDiffPixelRatio` (0–1), `threshold` (YIQ, 0 strict to 1 lax, default 0.2), `timeout`, `signal` (1.62).
  - Name: `'x.png'` or **`'x.webp'` (1.62, lossless)**, or an array of path segments.
  - Source: https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot-1
- Config defaults: `expect.toHaveScreenshot: { animations, caret, maxDiffPixels, maxDiffPixelRatio, scale, stylePath, threshold, type: 'png'|'webp' (1.64), pathTemplate (1.50) }`. `TestProject.expect.toHaveScreenshot.timeout` also exists. Sources: https://playwright.dev/docs/api/class-testconfig#test-config-expect and https://playwright.dev/docs/api/class-testproject#test-project-expect
- **`snapshotPathTemplate`** (1.28). Source: https://playwright.dev/docs/api/class-testconfig#test-config-snapshot-path-template
  - Tokens: `{arg} {ext} {platform} {projectName} {snapshotDir} {testDir} {testFileDir} {testFileBaseName} (1.60) {testFileName} {testFilePath} {testName}`. A one-character prefix is emitted only if the token is non-empty, e.g. `{/projectName}`.
  - Runner default for screenshots: `{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}{-projectName}{-snapshotSuffix}{ext}`, where `snapshotSuffix = process.platform`. That gives names like `example-test-1-chromium-darwin.png`.
  - Aria default: `{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}{ext}` (no platform suffix).
  - Source: https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/worker/testInfo.ts (lines ~611–619) and https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/index.ts
- **`--update-snapshots` / `-u [mode]`** — modes `all | changed | missing | none | default`. The bare `-u` preset is `changed`. Sources: `npx playwright test --help` (1.64.0) and https://playwright.dev/docs/api/class-testconfig#test-config-update-snapshots
  - `all` regenerates everything; it has meant "all" since 1.50.
  - `changed` updates mismatches and creates missing snapshots (1.50).
  - **Breaking in 1.64: `missing` now passes** the tests that only create snapshots. The implicit mode is now called **`default`**: it writes missing snapshots and fails, which is the old behaviour. Source: https://github.com/microsoft/playwright/releases/tag/v1.64.0
- `--update-source-method` / `updateSourceMethod` (1.50): `patch` (default; writes a unified diff to apply with `git apply`), `3way` (conflict markers), `overwrite`. It applies to **inline** snapshot templates such as aria. Source: https://playwright.dev/docs/api/class-testconfig#test-config-update-source-method
- `ignoreSnapshots` / `--ignore-snapshots` skips screenshot and snapshot expectations. Source: https://playwright.dev/docs/api/class-testconfig#test-config-ignore-snapshots
- **OS/browser-dependent baselines.** "Browser rendering can vary based on the host OS, version, settings, hardware, power source…, headless mode… run tests in the same environment where the baseline screenshots were generated." That is why teams generate and verify baselines inside the version-pinned image `mcr.microsoft.com/playwright:v1.64.0-noble`, either by running tests in it or via `run-server` + `PW_TEST_CONNECT_WS_ENDPOINT`. Image tags: `:vX`, `-noble` (24.04), `-jammy` (22.04), `-resolute` (26.04). Sources: https://playwright.dev/docs/test-snapshots and https://playwright.dev/docs/docker
- Possible baseline churn **(inference)**:
  - 1.57 switched Chromium to **Chrome for Testing** builds (release notes say "no functional changes"). https://github.com/microsoft/playwright/releases/tag/v1.57.0
  - 1.64 forwards the device `screen` property, so `window.screen` and media queries now see the emulated screen. Opt out with `screen: undefined`. https://github.com/microsoft/playwright/releases/tag/v1.64.0
- Hover effects: move the mouse away before asserting (`page.mouse.move(-1, -1)`). Source: https://playwright.dev/docs/test-snapshots#hover-effects
- Non-image `expect(value).toMatchSnapshot(name)` (JS) for text and binary. Source: https://playwright.dev/docs/test-snapshots#non-image-snapshots

---

## 3. ARIA snapshots

- Assertion, available in **all four bindings**:
  - TS: `await expect(locator|page).toMatchAriaSnapshot(yaml)`. Locator since 1.49, **page since 1.60**.
  - Java: `assertThat(locator|page).matchesAriaSnapshot(yaml)`.
  - .NET: `await Expect(locator|page).ToMatchAriaSnapshotAsync(yaml)`.
  - Python: `expect(locator|page).to_match_aria_snapshot(yaml)`, with `not_to_match_aria_snapshot`.
  - Sources: https://playwright.dev/docs/api/class-locatorassertions#locator-assertions-to-match-aria-snapshot and https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-match-aria-snapshot
- **File-based snapshots `.aria.yml` are JS only (1.50).** Use `toMatchAriaSnapshot()` or `toMatchAriaSnapshot({ name: 'main.aria.yml' })`. Files go to `<file>-snapshots/`, with one shared across browsers. Configure with `expect.toMatchAriaSnapshot.pathTemplate`. `expect.toMatchAriaSnapshot.children: 'contain' | 'equal' | 'deep-equal'` sets the default `/children` mode. Sources: https://playwright.dev/docs/aria-snapshots#snapshots-as-separate-files and https://playwright.dev/docs/api/class-testconfig#test-config-expect
- Updating (JS only):
  - `--update-snapshots` updates aria snapshots too.
  - An empty template `toMatchAriaSnapshot('')` generates one inline, without `-u`, in `default` mode.
  - Inline templates are updated via patch, 3way or overwrite.
  - Source: https://playwright.dev/docs/aria-snapshots#updating-snapshots-with-playwrighttest-and-the---update-snapshots-flag
- Matching grammar additions: `/children: equal` (strict) and `/url:` for links (1.52). Input `placeholder` is compared (1.56). Source: https://playwright.dev/docs/aria-snapshots#strict-matching and https://github.com/microsoft/playwright/releases/tag/v1.56.0
- Capture APIs:
  - `locator.ariaSnapshot({ mode?, depth?, boxes?, timeout? })` (1.49).
  - **`page.ariaSnapshot()` (1.59)**.
  - `mode: 'ai' | 'default'` (1.59). `'ai'` adds `[ref=eN]`, does not wait, throws on no match and includes iframes.
  - `depth` (1.59). `boxes` (1.60) appends `[box=x,y,w,h]`.
  - Source: https://playwright.dev/docs/api/class-locator#locator-aria-snapshot
  - **There is no `ref` option.** Refs come only from `mode: 'ai'`. The old `Locator.ariaRef()` was **removed in 1.60**. Source: https://github.com/microsoft/playwright/releases/tag/v1.60.0
  - `page.getByRef('e2')` (1.64) resolves a ref from the latest AI-mode snapshot. Source: https://playwright.dev/docs/api/class-page#page-get-by-ref
  - `locator.ariaSnapshotJSON()` / `page.ariaSnapshotJSON()` (1.63) are **JS only**. Source: https://playwright.dev/docs/api/class-locator#locator-aria-snapshot-json
  - Spellings: Java `locator.ariaSnapshot(new Locator.AriaSnapshotOptions().setMode(AriaSnapshotMode.AI).setDepth(3).setBoxes(true))`; .NET `AriaSnapshotAsync(new() { Mode = AriaSnapshotMode.Ai, Depth, Boxes })`; Python `aria_snapshot(mode="ai", depth=, boxes=)`. Sources: https://github.com/microsoft/playwright-java/blob/v1.63.0/playwright/src/main/java/com/microsoft/playwright/Locator.java, https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/Options/LocatorAriaSnapshotOptions.cs, https://github.com/microsoft/playwright-python/blob/v1.63.0/playwright/sync_api/_generated.py
- Aria snapshots **inside traces** (1.63):
  - JS: `trace: { mode, snapshots: { dom: true, aria: true, screen: true } }` or `tracing.start({ snapshots: {...} })`.
  - Java/.NET/Python use separate booleans: `setAriaSnapshots(true)` / `setScreenSnapshots(true)`, `AriaSnapshots` / `ScreenSnapshots`, `aria_snapshots=` / `screen_snapshots=`.
  - The trace viewer gets a "Display Aria" mode.
  - Source: https://playwright.dev/docs/api/class-tracing#tracing-start and https://github.com/microsoft/playwright/releases/tag/v1.63.0

---

## 4. Video

### 4.1 Context-level recording (`recordVideo`) — all bindings
- **JS**: `browser.newContext({ recordVideo: { dir?, size?: {width, height}, fps? (1.64), showActions?: { duration, position, fontSize (deprecated), cursor, style: { point, highlight, title } } } })`. Source: https://playwright.dev/docs/api/class-browser#browser-new-context-option-record-video and https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/params.md
  - `dir` is optional now and defaults to `artifactsDir`. `artifactsDir` is a `launch()` option since 1.59.
  - `recordVideo.showActions` is **JS only**.
- **Java**: `new Browser.NewContextOptions().setRecordVideoDir(Path).setRecordVideoSize(w, h)`. **.NET**: `RecordVideoDir`, `RecordVideoSize = new RecordVideoSize{Width, Height}`. **Python**: `record_video_dir=`, `record_video_size={"width":…, "height":…}`. Sources: https://playwright.dev/docs/videos and the binding sources at v1.63.0
  - `recordVideoFps` / `RecordVideoFps` / `record_video_fps` are documented **since 1.64**, so they are not in the released 1.63 bindings. Source: https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/class-browser.md
- Default size is the viewport scaled to fit 800×800. With no explicit viewport it is 800×450. Source: https://playwright.dev/docs/api/class-testoptions#test-options-video
- **Finalization:** "Make sure to await `BrowserContext.close` for videos to be saved." The video is guaranteed on disk only after context close. Sources: https://playwright.dev/docs/videos and https://playwright.dev/docs/api/class-video
- `Video` API (https://playwright.dev/docs/api/class-video):
  - `path()` (1.8): **throws when connected remotely**.
  - `saveAs(path)` (1.11). **Java, and Python sync, must call it after page/context close**, otherwise it throws. JS and Python async can call it any time; it waits.
  - `delete()` (1.11).
  - Spellings:
    - JS `page.video()?.path()`.
    - Java `page.video().path()` (`@Nullable Video`), returning `Path`.
    - .NET `Page.Video` (`IVideo?`) with **`PathAsync()`**, `SaveAsAsync(path)` and `DeleteAsync()`.
    - Python `page.video` (property) with `.path()`, `.save_as()` and `.delete()`.
  - Source: https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/IVideo.cs
- 1.64:
  - **VP9 instead of VP8**: less CPU, smaller files.
  - The cursor stays visible and follows an eased path.
  - Firefox and WebKit capture up to 25 fps.
  - Source: https://github.com/microsoft/playwright/releases/tag/v1.64.0
- 1.60 removed the old `videosPath` / `videoSize` context options. Source: https://github.com/microsoft/playwright/releases/tag/v1.60.0

### 4.2 Test-runner `video` (Node only)
- Modes: `'off' | 'on' | 'retain-on-failure' | 'on-first-retry' | 'on-all-retries' | 'retain-on-first-failure' | 'retain-on-failure-and-retries'`. **The last three were added for video in 1.61**; video now has the same modes as trace. Sources: https://playwright.dev/docs/api/class-testoptions#test-options-video and https://playwright.dev/docs/test-use-options#video-modes
- Object form: `{ mode, size, fps (1.64, default 25), show: { actions: { duration, position, fontSize (deprecated), cursor, style:{point, highlight, title} (1.64) }, test: { level: 'file'|'title'|'step', position, fontSize } } }`. `show` was added in 1.59. Source: https://playwright.dev/docs/api/class-testoptions#test-options-video
- Output: `video.webm`, or `video-N.webm` for several pages, in the test output dir, attached as `name: 'video', contentType: 'video/webm'`. Source: https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/index.ts
- `reuseContext: true` (1.62, experimental) **is ignored when video is enabled**. Source: https://playwright.dev/docs/api/class-testoptions#test-options-reuse-context
- Doc staleness: the summary table on https://playwright.dev/docs/test-use-options#recording-options and https://playwright.dev/docs/videos still lists only 4 modes. The mode tables and TestOptions list all 7.

### 4.3 NEW: Screencast API — `page.screencast` (1.59), all bindings
- `Screencast` class is available in every language. Source: https://playwright.dev/docs/api/class-screencast and https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/class-screencast.md
  - `start({ path?, onFrame?, size?, quality?, fps? (1.64) })` returns a `Disposable`.
    - `path` saves a webm when you call `stop()`.
    - `onFrame({ data /*JPEG*/, timestamp (1.61), viewportWidth, viewportHeight })` streams frames.
    - If tracing or recordVideo already started a screencast, the existing configuration wins.
  - `stop()`.
  - `showActions({ position, duration (default 500), fontSize (deprecated 1.64), cursor: 'pointer'|'none' (1.61), style: { point, highlight, title } (1.64) })` returns a `Disposable`. `hideActions()` reverses it.
  - `showChapter(title, { description, duration (default 2000) })` shows a centred chapter card with a blurred backdrop. These are "chapter markers" as on-video overlays; there are no container-level chapter metadata **(inference from docs wording)**.
  - `showOverlay(html, { duration })` returns a `Disposable`. `showOverlays()` / `hideOverlays()` toggle visibility.
- Per-binding spellings, verified at v1.63.0:
  - **Java**: `page.screencast().start(new Screencast.StartOptions().setPath(p).setSize(w,h).setQuality(q).setOnFrame(f -> ...))` returns `AutoCloseable`. `showActions(new Screencast.ShowActionsOptions().setPosition(AnnotatePosition.TOP_RIGHT).setCursor(ScreencastCursor.POINTER))`. `showChapter(title, new Screencast.ShowChapterOptions().setDescription(..).setDuration(..))`. Source: https://github.com/microsoft/playwright-java/blob/v1.63.0/playwright/src/main/java/com/microsoft/playwright/Screencast.java
  - **.NET**: `await Page.Screencast.StartAsync(new() { Path, Size = new ScreencastSize{...}, Quality, OnFrame = f => ... })` returns `Task<IAsyncDisposable>`. `ShowActionsAsync(new() { Position = AnnotatePosition.TopRight, Cursor = ScreencastCursor.Pointer })`. Also `ShowChapterAsync`, `ShowOverlayAsync` (returns `IAsyncDisposable`), `StopAsync`, `HideActionsAsync`, `ShowOverlaysAsync`, `HideOverlaysAsync`. Source: https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/IScreencast.cs
  - **Python**: `page.screencast.start(path=, on_frame=, quality=, size=)` returns a context manager. Also `show_actions(position="top-right", duration=, font_size=, cursor=)`, `show_chapter(title, description=, duration=)`, `show_overlay(html, duration=)`, `stop()`. Source: https://github.com/microsoft/playwright-python/blob/v1.63.0/playwright/sync_api/_generated.py
  - `fps` and `style` are **1.64**, so they are Node-only until the other bindings ship 1.64.
- Use cases named by the Playwright team: precise start/stop recording as an alternative to `recordVideo`; live frames for vision models; "agentic video receipts". Source: https://github.com/microsoft/playwright/releases/tag/v1.59.0
- Known issues:
  - **The video is lost if the page closes before `screencast.stop()`.** Issue #41608 is open, and the bot confirmed it against source. https://github.com/microsoft/playwright/issues/41608
  - Tracing clamps the screencast capture size and pads with grey. #42274 was closed, but a commenter reports the fix was reverted. https://github.com/microsoft/playwright/issues/42274
  - No `saveAs` exists on screencast. The `path` given to `start()` is local to the client process even when connected remotely (#42392, not planned). https://github.com/microsoft/playwright/issues/42392
- `playwright-cli` equivalents for agents: `video-start [file] [--cursor] [--fps=N]`, `video-chapter <title>`, `video-show-actions [--highlight-style=…]`, `video-hide-actions`, `video-stop`, `screenshot [ref] [--filename] [--hires]`, `snapshot [--depth] [--boxes]`, `tracing-start` / `tracing-stop`. Source: https://github.com/microsoft/playwright-cli (README)

---

## 5. Tracing

### 5.1 Test-runner `trace` (Node only)
- Modes: `'off' | 'on' | 'retain-on-failure' | 'on-first-retry' | 'on-all-retries' | 'retain-on-first-failure' | 'retain-on-failure-and-retries'`. Source: https://playwright.dev/docs/api/class-testoptions#test-options-trace and https://playwright.dev/docs/test-use-options#trace-modes
  - `on-all-retries` has been in the docs since 1.33.
  - `retain-on-first-failure` since 1.43: records the first run only and keeps it if it failed.
  - `retain-on-failure-and-retries` since 1.59: keeps every failing run plus every retry, so a passing retry can be compared with the failed run.
  - Source: https://playwright.dev/docs/release-notes
- Object form: `{ mode, attachments?=true, screenshots?=true, snapshots?: boolean | { dom, aria, screen } (object form 1.63), sources?=true }`. Source: https://playwright.dev/docs/api/class-testoptions#test-options-trace
- CLI override: `npx playwright test --trace <mode>` accepts all 7 modes. Source: `npx playwright test --help` (1.64.0)
- Output: `trace.zip` in the test output dir, attached as `name: 'trace', contentType: 'application/zip'`. The runner starts one trace per context and uses chunks per test. Source: https://github.com/microsoft/playwright/blob/v1.64.0/packages/playwright/src/worker/testTracing.ts
- **Runner tracing records `expect` assertions and `test.step`s; raw `context.tracing` does not.** Source: https://playwright.dev/docs/api/class-tracing
- `test.step(title, body, { box?, location?, timeout? (1.50), subtitle?, params? (1.63) })` shows in the trace viewer and the HTML report. 1.53 redesigned the step UI. 1.63 shows step subtitles and params, and Playwright API steps get the locator or URL as subtitle. Sources: https://playwright.dev/docs/api/class-test#test-step, https://github.com/microsoft/playwright/releases/tag/v1.63.0, https://github.com/microsoft/playwright/releases/tag/v1.53.0
- `locator.describe('Subscribe button')` (1.53, all bindings) puts readable names in traces and reports. Source: https://playwright.dev/docs/api/class-locator#locator-describe
- UI mode traces every test automatically. Use `--trace on` for local runs outside UI mode. Sources: https://playwright.dev/docs/trace-viewer#tracing-locally and https://playwright.dev/docs/test-ui-mode

### 5.2 Library tracing API — all bindings
- `context.tracing.start({ name?, title? (1.17), screenshots?, snapshots?, sources? (1.17), live? (1.59) })`. In JS it returns a `Disposable`; disposing it stops without saving. Then `stop({ path? })`: with no path, the trace is discarded. Source: https://playwright.dev/docs/api/class-tracing#tracing-start
  - JS `snapshots` may be `{ dom, aria, screen }` (1.63). Java/.NET/Python have `ariaSnapshots` and `screenSnapshots` booleans (1.63).
  - **Java `sources` needs the `PLAYWRIGHT_JAVA_SRC` env var** (paths separated by `:`, or `;` on Windows).
  - `live: true` writes an unarchived trace updated in real time.
- `startChunk({ name?, title? })` / `stopChunk({ path? })` (1.15) produce several trace files from one `start()`. Source: https://playwright.dev/docs/api/class-tracing#tracing-start-chunk
- `group(name, { location? })` / `groupEnd()` (1.49) group actions in the viewer. The docs say "Use `test.step` instead when available", so in Java/.NET/Python this is the step equivalent.
  - Java returns `AutoCloseable`, .NET `Task<IAsyncDisposable> GroupAsync`, Python a context manager.
  - Source: https://playwright.dev/docs/api/class-tracing#tracing-group and the binding sources at v1.63.0
- `startHar(path, { content, mode, urlFilter, resourcesDir (JS) })` / `stopHar()` (1.60). See §6.
- Spellings:
  - Java `context.tracing().start(new Tracing.StartOptions().setScreenshots(true).setSnapshots(true).setSources(true).setTitle(..))` and `stop(new Tracing.StopOptions().setPath(p))`.
  - .NET `await Context.Tracing.StartAsync(new() { Title, Screenshots = true, Snapshots = true, Sources = true })` and `StopAsync(new() { Path = failed ? p : null })`.
  - Python `context.tracing.start(title=, screenshots=True, snapshots=True, sources=True)` and `stop(path=)`.
  - Sources: https://playwright.dev/java/docs/api/class-tracing, https://playwright.dev/dotnet/docs/api/class-tracing, https://playwright.dev/python/docs/api/class-tracing
- Patterns for runners that are not Node:
  - .NET docs give an NUnit/MSTest/xUnit "Run trace only on failure" pattern: start in `[SetUp]`, then in `[TearDown]` call `StopAsync(new() { Path = failed ? path : null })`. Source: https://playwright.dev/dotnet/docs/trace-viewer#run-trace-only-on-failure
  - Java docs show only start/stop. A TestNG conditional save is the same pattern with `ITestResult` (see §11). Source: https://playwright.dev/java/docs/trace-viewer-intro
  - pytest-playwright has built-in `--tracing on|off|retain-on-failure`. Source: https://playwright.dev/python/docs/test-runners

### 5.3 Viewing traces
- Local: `npx playwright show-trace [trace]` with `-b/--browser`, `-h/--host`, `-p/--port` (`0` = any port, opens in a tab) and `--stdin`. Remote: `show-trace https://…/trace.zip`. Java: `mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="show-trace trace.zip"`. Python: `playwright show-trace trace.zip`. .NET: `pwsh bin/Debug/netX/playwright.ps1 show-trace trace.zip`. Sources: https://playwright.dev/docs/trace-viewer#opening-trace-viewer and `npx playwright show-trace --help` (1.64.0)
- **https://trace.playwright.dev** loads the trace entirely in the browser, with no upload. `?trace=<url>` opens a CI-hosted trace; CORS rules apply. Source: https://playwright.dev/docs/trace-viewer#using-traceplaywrightdev
- **CLI trace analysis (1.59)**, aimed at agents: `npx playwright trace open <zip>`, then `actions [--grep]`, `action <id>`, `requests`, `request <id>`, `console`, `errors`, `snapshot <id> --name before|after`, `screenshot <id>`, `attachments`, `attachment <n>`, `close` and `install-skill`. Sources: https://github.com/microsoft/playwright/releases/tag/v1.59.0 and `npx playwright trace --help` (1.64.0)
- Viewer improvements since 1.55:
  - System theme and Ctrl/Cmd+F in code (1.58).
  - Better action filtering (1.59).
  - JSON/form body pretty-print (1.60).
  - WebSockets in traces and HAR (1.61).
  - "Display Aria" mode (1.63).
  - Step subtitles and params (1.63).
  - Sources: the corresponding https://github.com/microsoft/playwright/releases tags.
- Display of `canvas` content is off by default (setting "Display canvas content", 1.50). Source: https://github.com/microsoft/playwright/releases/tag/v1.50.0
- VS Code: enable **Show Trace Viewer** in the Playwright sidebar to auto-open the trace after a run. Source: https://playwright.dev/docs/getting-started-vscode

---

## 6. HAR

- Record per context:
  - JS: `recordHar: { path, content?: 'omit'|'embed'|'attach', mode?: 'full'|'minimal', urlFilter?: glob|RegExp, omitContent? (deprecated) }`.
  - Java/.NET/Python: `recordHarPath`, `recordHarContent`, `recordHarMode`, `recordHarUrlFilter`, `recordHarOmitContent`. Python names: `record_har_path` etc. .NET also has `RecordHarUrlFilterRegex` / `RecordHarUrlFilterString`.
  - `content` defaults to `attach` for `.zip` and `embed` otherwise. **The HAR is written on `context.close()`.**
  - Source: https://playwright.dev/docs/api/class-browser#browser-new-context-option-record-har and https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/params.md
- **New first-class `context.tracing.startHar(path, { content, mode, urlFilter, resourcesDir (JS only) })` / `stopHar()` (1.60).** It returns a Disposable (JS `await using`), `AutoCloseable` (Java), `IAsyncDisposable` (.NET) or a context manager (Python). Only one HAR per Tracing at a time. Source: https://playwright.dev/docs/api/class-tracing#tracing-start-har
- Replay and update with `page|context.routeFromHAR(har, { url?, notFound?: 'abort'|'fallback', update?: bool, updateContent?: 'embed'|'attach' (1.32), updateMode?: 'full'|'minimal' (default minimal, 1.32) })`. With `update: true` the file is written on `context.close()`. Sources: https://playwright.dev/docs/api/class-page#page-route-from-har and https://playwright.dev/docs/mock#mocking-with-har-files
- CLI: `npx playwright open --save-har=example.har --save-har-glob="**/api/**" <url>`, also available on `codegen`. Note that `open` no longer opens the recorder (1.54). Sources: https://playwright.dev/docs/mock#recording-har-with-cli and https://github.com/microsoft/playwright/releases/tag/v1.54.0
- In the Node runner, HAR goes through `use.contextOptions.recordHar`. This is **not supported** with `reuseContext`. Source: https://playwright.dev/docs/api/class-testoptions#test-options-reuse-context
- HAR and traces include WebSocket traffic since 1.61. Source: https://github.com/microsoft/playwright/releases/tag/v1.61.0

---

## 7. Codegen / recorder

- `npx playwright codegen [options] [url]` flags in 1.64.0. Source: `npx playwright codegen --help` (1.64.0); https://playwright.dev/docs/codegen
  - Output and targeting: `-o/--output`, `--target`, `--test-id-attribute`.
  - Browser: `-b/--browser`, `--channel`, `--block-service-workers`, `--ignore-https-errors`, `--timeout`.
  - Emulation: `--color-scheme`, `--device`, `--geolocation`, `--lang`, `--timezone`, `--user-agent`, `--viewport-size "1280, 720"`.
  - Network and auth: `--http-credentials "user:pass"` (1.63), `--proxy-server`, `--proxy-bypass`.
  - State and capture: `--load-storage`, `--save-storage`, `--save-har`, `--save-har-glob`, `--user-data-dir` (1.54).
  - `--target` values: `javascript, playwright-test (default), python, python-async, python-pytest, csharp, csharp-mstest, csharp-nunit, csharp-xunit, java, java-junit`. **There is no TestNG target.**
- Recorder toolbar in 1.64: **Pick locator, Assert visibility, Assert text, Assert value, Assert snapshot**, plus the setting "Automatically generate assertions while recording" (auto `toBeVisible()`, 1.55). Source: the 1.64.0 recorder bundle `playwright-core/lib/vite/recorder/assets/index-*.js`; https://github.com/microsoft/playwright/releases/tag/v1.55.0
- **Codegen does emit aria-snapshot assertions** through "Assert snapshot", per language: `toMatchAriaSnapshot` / `matchesAriaSnapshot` / `ToMatchAriaSnapshotAsync` / `to_match_aria_snapshot`. Sources: the 1.64.0 `playwright-core/lib/coreBundle.js`; https://playwright.dev/docs/aria-snapshots#generating-snapshots-with-the-playwright-code-generator; 1.50 added the aria pick button (https://github.com/microsoft/playwright/releases/tag/v1.50.0). https://playwright.dev/docs/codegen still lists only the three classic assertions, which is stale.
- VS Code extension: **Record new** (creates `test-1.spec.ts`), **Record at cursor**, **Pick locator**, **Show browser** and **Show Trace Viewer**. Source: https://playwright.dev/docs/codegen#generate-tests-in-vs-code and https://playwright.dev/docs/getting-started-vscode
- Programmatic: `page.pause()` opens codegen controls inside a custom setup. `page.pickLocator()` / `cancelPickLocator()` (1.59) and `locator.normalize()` (1.59) are in all bindings. Source: https://playwright.dev/docs/codegen#record-using-custom-setup and https://github.com/microsoft/playwright/releases/tag/v1.59.0

---

## 8. CI artifacts — best practice

- Keep artifacts small by choosing modes. Sources: https://playwright.dev/docs/test-use-options#trace-modes and https://playwright.dev/docs/trace-viewer#tracing-on-ci
  - The docs call trace `'on'` "performance heavy".
  - The CI recommendation is `trace: 'on-first-retry'` with `retries`, or `'retain-on-failure'` when there are no retries.
  - The two modes cheapest on a flaky suite are `'retain-on-first-failure'` (records only the first attempt) and `'on-first-retry'`. `'retain-on-failure-and-retries'` is the most diagnostic and the heaviest.
- Size levers:
  - `video` VP9 since 1.64.
  - `scale: 'css'` for HiDPI screenshots.
  - `type: 'jpeg'` with `quality` for ad-hoc screenshots; webp with `quality < 100` since 1.62.
  - `expect.toHaveScreenshot.type: 'webp'` shrinks committed baselines (1.64).
  - `preserveOutput: 'failures-only'` prunes `test-results/` for passing tests.
  - Sources: https://github.com/microsoft/playwright/releases/tag/v1.64.0, https://playwright.dev/docs/api/class-page#page-screenshot, https://playwright.dev/docs/api/class-testconfig#test-config-preserve-output
- Upload artifacts with `if: ${{ !cancelled() }}`. Sources: https://playwright.dev/docs/ci#on-pushpull_request and https://playwright.dev/docs/ci#uploading-playwright-report-folder-with-azure-pipelines
  - Node: upload `playwright-report/` (`actions/upload-artifact@v5`, `retention-days: 30`).
  - Java/.NET/Python: the official Python example uploads `test-results/` after `pytest --tracing=retain-on-failure`.
  - Azure Pipelines: `PublishTestResults@2` (JUnit from `reporter: [['junit', { outputFile: 'test-results/e2e-junit-results.xml' }]]`) plus `PublishPipelineArtifact@1` of `playwright-report`.
- **Sharding with blob merge** (since 1.37). Sources: https://playwright.dev/docs/test-sharding#merging-reports-from-multiple-shards and https://playwright.dev/docs/test-reporters#blob-reporter
  - Use `reporter: process.env.CI ? 'blob' : 'html'`.
  - Each shard runs `--shard=i/n` and uploads `blob-report/` (`retention-days: 1`).
  - A merge job downloads with `pattern: blob-report-*`, `merge-multiple: true`, then runs `npx playwright merge-reports --reporter html ./all-blob-reports` and uploads `playwright-report`.
  - Blobs carry all attachments, including traces and screenshot diffs.
  - Blob options: `outputDir`, `fileName`, `outputFile`, or env `PLAYWRIGHT_BLOB_OUTPUT_DIR|NAME|FILE`.
  - Use `testConfig.tag` (1.57) to tell environments apart in a merged report. `merge-reports --config merge.config.ts` handles cross-OS roots.
- HTML reporter options (https://playwright.dev/docs/test-reporters#html-reporter):
  - `open` (default `on-failure`), `outputFolder`, `host`, `port`.
  - `attachmentsBaseURL`, for when the `data/` folder is hosted elsewhere.
  - `title` (1.53), `noSnippets` (1.54), `noCopyPrompt` (1.56).
  - `doNotInlineAssets` (docs since 1.59), for strict CSP hosting.
  - `mergeFiles` (1.62).
  - Each option has a `PLAYWRIGHT_HTML_*` env var.
- Viewing CI evidence. Sources: https://github.com/microsoft/playwright/releases/tag/v1.60.0, https://playwright.dev/docs/trace-viewer#viewing-remote-traces, https://github.com/microsoft/playwright/releases/tag/v1.57.0, https://github.com/microsoft/playwright/releases/tag/v1.58.0, https://github.com/microsoft/playwright/releases/tag/v1.63.0
  - `npx playwright show-report playwright-report.zip` opens a downloaded zip directly (1.60).
  - The HTML report links each trace into the bundled viewer.
  - `show-trace <url>` or `trace.playwright.dev/?trace=<url>` open single traces.
  - Speedboard tab (1.57), Timeline for merged reports (1.58), duration waterfall (1.63).
- Other reporting additions:
  - `--add-reporter` (1.63) adds a reporter instead of replacing.
  - Built-in `perfetto` reporter (1.63).
  - `captureGitInfo: { commit, diff }` (1.51).
  - Sources: https://github.com/microsoft/playwright/releases/tag/v1.63.0 and https://github.com/microsoft/playwright/releases/tag/v1.51.0
- Do not cache browser binaries; restore time is about the same as download. Source: https://playwright.dev/docs/ci#caching-browsers
- With allure-playwright across shards, copy every shard's `allure-results/` into one directory; "new files will be added to the existing ones". Source: https://allurereport.org/docs/playwright/
- pytest-playwright 0.10.0 (https://github.com/microsoft/playwright-pytest/releases/tag/v0.10.0):
  - Kept artifacts become teardown-report `user_properties` (`playwright_screenshot|video|trace`), so `--junitxml` writes them as `<property>` and pytest-html 4 links or embeds them.
  - With pytest-rerunfailures, each attempt gets its own `test-results/<test>-retryN/` folder.
  - Artifacts survive fixture teardown failures.

---

## 9. New in 1.55–1.64 that a 1.50-era skill would miss (evidence-related)

| Ver | Change | Source |
|---|---|---|
| 1.51 | "Copy prompt" on errors; `testStepInfo.attach`; `captureGitInfo` | https://github.com/microsoft/playwright/releases/tag/v1.51.0 |
| 1.52 | aria `/children` and `/url` | https://github.com/microsoft/playwright/releases/tag/v1.52.0 |
| 1.53 | new Steps UI in trace and HTML; `locator.describe()`; `testInfo.snapshotPath({kind})`; `error-context.md` attachment (from source) | https://github.com/microsoft/playwright/releases/tag/v1.53.0 |
| 1.55 | codegen auto `toBeVisible()` assertions | https://github.com/microsoft/playwright/releases/tag/v1.55.0 |
| 1.56 | `page.consoleMessages()` / `pageErrors()` / `requests()`; aria `placeholder`; UI-mode `--update-snapshots` options; Playwright Agents | https://github.com/microsoft/playwright/releases/tag/v1.56.0 |
| 1.57 | Speedboard; Chrome for Testing builds; `testConfig.tag` | https://github.com/microsoft/playwright/releases/tag/v1.57.0 |
| 1.58 | Timeline in merged HTML; viewer system theme | https://github.com/microsoft/playwright/releases/tag/v1.58.0 |
| 1.59 | **`page.screencast`** (recording, actions, chapters, overlays, frames); video `show`; `page.ariaSnapshot()`, `mode`, `depth`; trace `live`; `retain-on-failure-and-retries`; `npx playwright trace` CLI; `--debug=cli`; Disposable returns | https://github.com/microsoft/playwright/releases/tag/v1.59.0 |
| 1.60 | **`tracing.startHar` / `stopHar`**; `toMatchAriaSnapshot` on Page; aria `boxes`; `{testFileBaseName}`; show-report accepts `.zip`; removed `videosPath` / `videoSize` and `ariaRef()` | https://github.com/microsoft/playwright/releases/tag/v1.60.0 |
| 1.61 | **video gains all 7 trace modes**; screencast `cursor`, frame `timestamp`; WebSockets in HAR and trace | https://github.com/microsoft/playwright/releases/tag/v1.61.0 |
| 1.62 | **WebP** screenshots and baselines; `signal` on actions and assertions; `reuseContext` (ignored with video); `retryStrategy: 'isolated'`; HTML `mergeFiles` | https://github.com/microsoft/playwright/releases/tag/v1.62.0 |
| 1.63 | **aria and screen snapshots in traces** + Display Aria; step `subtitle` / `params`; `ariaSnapshotJSON` (JS); perfetto reporter; `--add-reporter`; HTML duration waterfall; codegen `--http-credentials` | https://github.com/microsoft/playwright/releases/tag/v1.63.0 |
| 1.64 | **video `fps`**, action `style` CSS (deprecates `fontSize`), VP9; `expect.toHaveScreenshot.type: 'webp'`; **`--update-snapshots=missing` now passes, new `default` mode**; `page.getByRef`; device `screen` forwarded | https://github.com/microsoft/playwright/releases/tag/v1.64.0 |

---

## 10. Per-binding API matrix (Node 1.64 / Java·.NET·Python 1.63)

| Feature | TS / Node 1.64 | Java 1.63 | .NET 1.63 | Python 1.63 |
|---|---|---|---|---|
| Page screenshot | `page.screenshot({ path, fullPage, clip, mask, maskColor, animations, caret, scale, style, omitBackground, type, quality, timeout })` | `page.screenshot(new Page.ScreenshotOptions().setPath(..).setFullPage(..)...)` → `byte[]` | `Page.ScreenshotAsync(new() { Path, FullPage, Clip, Mask, MaskColor, Animations, Caret, Scale, Style, OmitBackground, Type, Quality, Timeout })` | `page.screenshot(path=, full_page=, clip=, mask=, mask_color=, animations=, caret=, scale=, style=, omit_background=, type=, quality=, timeout=)` |
| Element screenshot | `locator.screenshot({...})` (no fullPage/clip) | `locator.screenshot(new Locator.ScreenshotOptions()...)` | `Locator.ScreenshotAsync(new LocatorScreenshotOptions{...})` | `locator.screenshot(...)` |
| WebP | `type: 'webp'` (1.62) | `ScreenshotType.WEBP` | `ScreenshotType.Webp` | `type="webp"` |
| Auto screenshot in runner | `use.screenshot: 'off'\|'on'\|'only-on-failure'\|'on-first-failure'\|{mode, fullPage, omitBackground}` | n/a | n/a | pytest-playwright `--screenshot on\|off\|only-on-failure`, `--full-page-screenshot` |
| Visual assertion | `expect(page\|locator).toHaveScreenshot(name?, opts)` | n/a | n/a | n/a |
| Snapshot update CLI | `-u/--update-snapshots [all\|changed\|missing\|none\|default]`, `--update-source-method` | n/a | n/a | n/a |
| ARIA assert (inline) | `expect(x).toMatchAriaSnapshot(yaml)` | `assertThat(x).matchesAriaSnapshot(yaml)` | `Expect(x).ToMatchAriaSnapshotAsync(yaml)` | `expect(x).to_match_aria_snapshot(yaml)` |
| ARIA assert (`.aria.yml` file) | `toMatchAriaSnapshot({ name })` | n/a | n/a | n/a |
| ARIA capture | `locator\|page.ariaSnapshot({ mode:'ai'\|'default', depth, boxes })` | `ariaSnapshot(new Locator.AriaSnapshotOptions().setMode(AriaSnapshotMode.AI))` | `AriaSnapshotAsync(new() { Mode = AriaSnapshotMode.Ai })` | `aria_snapshot(mode="ai", depth=, boxes=)` |
| ARIA JSON | `ariaSnapshotJSON()` (1.63) | n/a | n/a | n/a |
| Ref locator | `page.getByRef('e2')` (1.64) | not yet (1.64) | not yet (1.64) | not yet (1.64) |
| Context video | `recordVideo: { dir, size, fps (1.64), showActions }` | `setRecordVideoDir(p).setRecordVideoSize(w,h)` | `RecordVideoDir`, `RecordVideoSize` | `record_video_dir=`, `record_video_size=` |
| Video object | `page.video()?.path()/saveAs()/delete()` | `page.video().path()/saveAs()/delete()` (saveAs after close) | `Page.Video?.PathAsync()/SaveAsAsync()/DeleteAsync()` | `page.video.path()/save_as()/delete()` (sync: save_as after close) |
| Runner video | `use.video: 7 modes \| { mode, size, fps, show:{actions, test} }` | n/a | n/a | pytest-playwright `--video on\|off\|retain-on-failure` |
| Screencast | `page.screencast.start({path, onFrame, size, quality, fps})/stop()` | `page.screencast().start(new Screencast.StartOptions()...)` → `AutoCloseable` | `Page.Screencast.StartAsync(new() {...})` → `IAsyncDisposable` | `page.screencast.start(path=, on_frame=, size=, quality=)` |
| Action overlay | `screencast.showActions({ position, duration, cursor, style })` | `showActions(new Screencast.ShowActionsOptions().setPosition(AnnotatePosition.TOP_RIGHT))` | `ShowActionsAsync(new() { Position = AnnotatePosition.TopRight })` | `show_actions(position="top-right", cursor=)` |
| Chapter / overlay | `showChapter(title,{description,duration})`, `showOverlay(html,{duration})` | `showChapter(..)`, `showOverlay(..)` | `ShowChapterAsync`, `ShowOverlayAsync` | `show_chapter(..)`, `show_overlay(..)` |
| Runner trace | `use.trace: 7 modes \| { mode, screenshots, snapshots:{dom,aria,screen}, sources, attachments }`, `--trace` | n/a | n/a | pytest-playwright `--tracing on\|off\|retain-on-failure` |
| Tracing start/stop | `context.tracing.start({screenshots, snapshots, sources, title, live})` / `stop({path})` | `context.tracing().start(new Tracing.StartOptions()...)` / `stop(new Tracing.StopOptions().setPath(p))` | `Context.Tracing.StartAsync(new(){...})` / `StopAsync(new(){ Path })` | `context.tracing.start(...)` / `stop(path=)` |
| Aria/screen per action in trace | `snapshots: { aria, screen }` (1.63) | `setAriaSnapshots`, `setScreenSnapshots` | `AriaSnapshots`, `ScreenSnapshots` | `aria_snapshots=`, `screen_snapshots=` |
| Chunks | `startChunk({name,title})` / `stopChunk({path})` | `startChunk()` / `stopChunk(new Tracing.StopChunkOptions().setPath(p))` | `StartChunkAsync` / `StopChunkAsync` | `start_chunk()` / `stop_chunk(path=)` |
| Group ≈ step | `test.step()` (preferred); `tracing.group/groupEnd` | `tracing().group(name)` / `groupEnd()` | `Tracing.GroupAsync(name)` / `GroupEndAsync()` | `tracing.group(name)` / `group_end()` |
| HAR record (context) | `recordHar: { path, content, mode, urlFilter }` | `setRecordHarPath/Content/Mode/UrlFilter` | `RecordHarPath/Content/Mode/UrlFilter` | `record_har_path=, record_har_content=, record_har_mode=, record_har_url_filter=` |
| HAR via tracing | `tracing.startHar(path,{content,mode,urlFilter,resourcesDir})/stopHar()` (1.60) | `tracing().startHar(p)` / `stopHar()` | `Tracing.StartHarAsync(p)` / `StopHarAsync()` | `tracing.start_har(p)` / `stop_har()` |
| HAR replay/update | `routeFromHAR(har,{url,notFound,update,updateContent,updateMode})` | `routeFromHAR(p, new Page.RouteFromHAROptions().setUpdate(true))` | `RouteFromHARAsync(p, new(){ Update = true })` | `route_from_har(p, update=True, update_content=, update_mode=)` |
| Show trace CLI | `npx playwright show-trace` | `mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="show-trace t.zip"` | `pwsh bin/Debug/netX/playwright.ps1 show-trace t.zip` | `playwright show-trace t.zip` |
| Codegen target | `--target playwright-test` | `--target java\|java-junit` | `--target csharp\|csharp-nunit\|csharp-mstest\|csharp-xunit` | `--target python\|python-async\|python-pytest` |

Sources for the matrix: §1–§7 above. Binding spellings come from https://github.com/microsoft/playwright-java/tree/v1.63.0/playwright/src/main/java/com/microsoft/playwright, https://github.com/microsoft/playwright-dotnet/tree/v1.63.0/src/Playwright/API/Generated and https://github.com/microsoft/playwright-python/blob/v1.63.0/playwright/sync_api/_generated.py.

---

## 11. Recommended defaults — trace + video + screenshot on failure only

### 11.1 TypeScript (`playwright.config.ts`, 1.64)
```ts
import { defineConfig } from '@playwright/test';

const isCI = !!process.env.CI;

export default defineConfig({
  retries: isCI ? 2 : 0,
  reporter: isCI
    ? [['blob'], ['allure-playwright', { resultsDir: 'allure-results' }]]
    : [['html', { open: 'on-failure' }], ['allure-playwright', { resultsDir: 'allure-results' }]],
  use: {
    screenshot: { mode: 'only-on-failure', fullPage: true },
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  expect: {
    toHaveScreenshot: { animations: 'disabled', caret: 'hide', scale: 'css' },
  },
});
```
- On flaky-heavy suites, swap `trace` and `video` to `'retain-on-first-failure'`. Only the first attempt is recorded, so retries run without the recording cost. Video supports this since 1.61. Source: https://playwright.dev/docs/test-use-options#trace-modes
- `allure-playwright >= 3.12` needs `@playwright/test >= 1.62`. Source: https://github.com/allure-framework/allure-js/blob/v3.13.0/packages/allure-playwright/README.md

### 11.2 Java + TestNG (Playwright Java 1.63, allure-java 3.0)
Playwright Java is **not thread-safe**. Keep one Playwright per thread and run TestNG with `parallel="classes"` so a class's hooks and tests share a thread. Source: https://playwright.dev/java/docs/multithreading
```java
public abstract class PlaywrightTestBase {
    private static final Path ARTIFACTS = Paths.get("target", "playwright-artifacts");

    private Playwright playwright;
    private Browser browser;
    protected BrowserContext context;
    protected Page page;

    @BeforeClass
    public void launchBrowser() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
    }

    @BeforeMethod
    public void openContext() {
        context = browser.newContext(new Browser.NewContextOptions()
            .setRecordVideoDir(ARTIFACTS.resolve("video-tmp")));
        context.tracing().start(new Tracing.StartOptions()
            .setScreenshots(true)
            .setSnapshots(true)
            .setSources(true));
        page = context.newPage();
    }

    @AfterMethod(alwaysRun = true)
    public void captureEvidenceOnFailure(ITestResult result) throws IOException {
        boolean failed = result.getStatus() == ITestResult.FAILURE;
        String name = result.getTestClass().getRealClass().getSimpleName() + "." + result.getMethod().getMethodName();
        Video video = page.video();

        if (failed) {
            Path screenshot = ARTIFACTS.resolve(name + ".png");
            page.screenshot(new Page.ScreenshotOptions().setPath(screenshot).setFullPage(true));
            attach("screenshot", "image/png", screenshot, "png");

            Path trace = ARTIFACTS.resolve(name + ".zip");
            context.tracing().stop(new Tracing.StopOptions().setPath(trace));
            attach("trace", "application/vnd.allure.playwright-trace", trace, "zip");
        } else {
            context.tracing().stop();
        }

        context.close();

        if (failed) {
            Path videoFile = ARTIFACTS.resolve(name + ".webm");
            video.saveAs(videoFile);
            attach("video", "video/webm", videoFile, "webm");
        }
        video.delete();
    }

    @AfterClass(alwaysRun = true)
    public void closeBrowser() {
        browser.close();
        playwright.close();
    }

    private static void attach(String name, String type, Path file, String extension) throws IOException {
        try (InputStream content = Files.newInputStream(file)) {
            Allure.attachment(name, type, content, AttachmentOptions.withFileExtension(extension));
        }
    }
}
```
- Keep the `Video` reference before `context.close()`. Java `saveAs` **must** run after close. `delete()` removes the temp original. Source: https://playwright.dev/java/docs/api/class-video
- TestNG injects `ITestResult` into `@AfterMethod`. Source: https://testng.org/dependency_injection.html
- allure-java 2.x: replace `Allure.attachment(..., AttachmentOptions.withFileExtension(ext))` with `Allure.addAttachment(name, type, content, ext)`. Alternatively, the 3.0 `allure-playwright` module offers `AllurePlaywright.attachTrace(name, path)` / `attachVideo(name, path)` / `attachScreenshot(name, page)`. Sources: https://github.com/allure-framework/allure-java/blob/3.0.0/allure-java-commons/src/main/java/io/qameta/allure/Allure.java and https://github.com/allure-framework/allure-java/tree/3.0.0/allure-playwright
- Trace `sources` in Java needs `PLAYWRIGHT_JAVA_SRC=src/test/java` in the test JVM env. Source: https://playwright.dev/java/docs/api/class-tracing#tracing-start-option-sources
- Not compiled or run here; the snippet was assembled from verified signatures.

### 11.3 .NET + NUnit (Microsoft.Playwright.NUnit 1.63, Allure.NUnit 2.15)
NUnit runs derived `[SetUp]` after base `[SetUp]` and derived `[TearDown]` **before** base `[TearDown]`. The base `BrowserTest` closes contexts only when the test passed; on failure the worker's browser is disposed. So close the context yourself to finalize the video deterministically. `CloseAsync` is idempotent. Sources: https://docs.nunit.org/articles/nunit/writing-tests/attributes/teardown.html, https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright.NUnit/BrowserTest.cs, https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright.NUnit/WorkerAwareTest.cs, https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/Core/BrowserContext.cs
```csharp
[AllureNUnit]
public abstract class EvidenceOnFailureTest : PageTest
{
    private static string ArtifactsDir => Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-artifacts");

    private static string TestName => $"{TestContext.CurrentContext.Test.ClassName}.{TestContext.CurrentContext.Test.MethodName}";

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.RecordVideoDir = Path.Combine(ArtifactsDir, "video-tmp");
        return options;
    }

    [SetUp]
    public async Task StartTracing()
    {
        await Context.Tracing.StartAsync(new() { Title = TestName, Screenshots = true, Snapshots = true, Sources = true });
    }

    [TearDown]
    public async Task CaptureEvidenceOnFailure()
    {
        var failed = TestContext.CurrentContext.Result.Outcome.Status == TestStatus.Failed;
        var video = Page.Video;

        if (failed)
        {
            var screenshot = Path.Combine(ArtifactsDir, $"{TestName}.png");
            await Page.ScreenshotAsync(new() { Path = screenshot, FullPage = true });
            Attach("screenshot", "image/png", screenshot);
        }

        var trace = failed ? Path.Combine(ArtifactsDir, $"{TestName}.zip") : null;
        await Context.Tracing.StopAsync(new() { Path = trace });
        if (trace is not null)
        {
            Attach("trace", "application/vnd.allure.playwright-trace", trace);
        }

        await Context.CloseAsync();

        if (video is null)
        {
            return;
        }
        if (failed)
        {
            var videoFile = Path.Combine(ArtifactsDir, $"{TestName}.webm");
            await video.SaveAsAsync(videoFile);
            Attach("video", "video/webm", videoFile);
        }
        await video.DeleteAsync();
    }

    private static void Attach(string name, string contentType, string path)
    {
        TestContext.AddTestAttachment(path, name);
        AllureApi.AddAttachment(name, contentType, path);
    }
}
```
- `Status == TestStatus.Failed` covers failures and errors (Error is a label under Failed). Source: https://docs.nunit.org/articles/nunit/writing-tests/TestContext.html
- The video API is **`PathAsync()`**. The C# sample `GetPathAsync()` in class-video.md is a doc bug. Source: https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/IVideo.cs
- Parameterised tests need `TestName` sanitised for file systems. Allure placement of teardown attachments, under the tear-down fixture versus the test body, is **UNVERIFIED**. Not compiled or run here.

### 11.4 pytest (pytest-playwright 0.10.0, allure-pytest 2.16)
`pytest.ini`:
```ini
[pytest]
addopts = --tracing=retain-on-failure --video=retain-on-failure --screenshot=only-on-failure --full-page-screenshot --output=test-results
```
`conftest.py`, forwarding the kept artifacts to Allure. This needs pytest-playwright ≥ 0.10.0, which exposes them as teardown `user_properties`:
```python
from pathlib import Path

import allure

_PLAYWRIGHT_ATTACHMENTS = {
    "playwright_screenshot": ("screenshot", allure.attachment_type.PNG, None),
    "playwright_video": ("video", allure.attachment_type.WEBM, None),
    "playwright_trace": ("trace", "application/vnd.allure.playwright-trace", "zip"),
}


def pytest_runtest_logreport(report):
    if report.when != "teardown":
        return
    for key, path in report.user_properties:
        if key in _PLAYWRIGHT_ATTACHMENTS:
            name, attachment_type, extension = _PLAYWRIGHT_ATTACHMENTS[key]
            allure.attach.file(Path(path).resolve(), name=name, attachment_type=attachment_type, extension=extension)
```
- File names: `trace.zip` / `trace-N.zip`, `video.webm` / `video-N.webm`, `test-failed-N.png`, under `test-results/<slugified-nodeid>[-retryN]/`. Source: https://github.com/microsoft/playwright-pytest/blob/v0.10.0/pytest-playwright/pytest_playwright/pytest_playwright.py
- pytest-playwright supports only `on|off|retain-on-failure` for `--tracing` and `--video`, and `on|off|only-on-failure` for `--screenshot`. The runner's 7 modes are not available. Source: https://playwright.dev/python/docs/test-runners
- allure-pytest closes the test at `pytest_runtest_logfinish`, which comes after `logreport`, so the attachment lands in that test. Source: https://github.com/allure-framework/allure-python/blob/2.16.2/allure-pytest/src/listener.py. Whether it lands in the test body or the teardown section is **UNVERIFIED**; the hook has not been executed.

---

## 12. Doc discrepancies and traps found (verify before teaching)

1. playwright.dev **Java, .NET and Python pages show 1.64 options** (`setFps`, `setStyle`, `recordVideoFps`, `getByRef`) that are absent from the released 1.63 bindings. https://playwright.dev/java/docs/api/class-screencast vs https://github.com/microsoft/playwright-java/blob/v1.63.0/playwright/src/main/java/com/microsoft/playwright/Screencast.java
2. The 1.59 Java and .NET release-note snippets pass `"top-right"` strings. The real types are enums: `AnnotatePosition.TOP_RIGHT` (Java) and `AnnotatePosition.TopRight` (.NET). Python uses literal strings. https://playwright.dev/java/docs/release-notes vs the binding sources
3. class-video.md shows C# `page.Video.GetPathAsync()`; the real API is `PathAsync()`. https://playwright.dev/dotnet/docs/api/class-video vs https://github.com/microsoft/playwright-dotnet/blob/v1.63.0/src/Playwright/API/Generated/IVideo.cs
4. Summary tables in test-use-options, videos and trace-viewer list 3–5 modes. The TestOptions reference lists all modes; `on-first-failure` exists for screenshot and there are 7 modes for trace and video. https://playwright.dev/docs/test-use-options#recording-options
5. `maskColor`: class-page.md says since v1.34, while params.md and the release notes say 1.35. https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/api/class-page.md
6. codegen.md lists 3 assertion tools; the 1.64 recorder also has **Assert snapshot** and auto-assertions. https://playwright.dev/docs/codegen
7. The `context.tracing` API does not capture `expect` calls; runner-config tracing does. https://playwright.dev/docs/api/class-tracing
8. `Video.path()` throws when connected remotely (Docker `run-server` or grid); use `saveAs`. https://playwright.dev/docs/api/class-video
9. A screencast video is lost if the page closes before `stop()` (#41608). https://github.com/microsoft/playwright/issues/41608
10. allure-playwright builds its image diff only from `.png` triples, so WebP baselines get no Allure diff widget (source reading). https://github.com/allure-framework/allure-js/blob/v3.13.0/packages/allure-playwright/src/utils.ts
11. 1.64 changed `--update-snapshots=missing` semantics. CI scripts relying on "missing fails" must switch to `default`. https://github.com/microsoft/playwright/releases/tag/v1.64.0

## 13. UNVERIFIED / not established from a primary source

- Third-party visual diff libraries for Java/.NET/Python. None is endorsed by Playwright; any named library would be a recommendation, not a fact.
- Whether `screencast.showActions()` overlays also appear in `recordVideo` output for Java/.NET/Python, where `recordVideo.showActions` is JS-only. Likely, since overlays render in-page, but untested **(inference)**.
- Exact Allure placement of teardown-time attachments for Allure.NUnit and allure-pytest.
- Behaviour of allure-playwright with `.webp` visual-diff attachments: only the regex was read, nothing was run.
- Exact version that introduced `recordHar.urlFilter`. It predates 1.50 and does not matter for current skills.
- None of the §11 code samples was compiled or executed in this session. Every API name in them was checked against v1.63/v1.64 sources.
