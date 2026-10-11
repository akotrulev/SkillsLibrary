---
name: evidence-capture
description: Use when a Playwright Java (TestNG) suite or agent session must keep evidence — failure screenshots, video, screencast receipts, traces, HAR — or a failure's trace must be read before a fix. Triggers "keep trace and video on failure", "record a screencast of this flow", "open the trace for this failing test", "capture evidence via Playwright MCP". Do NOT use for writing tests or BaseTest (ui-test-author/playwright), Allure wiring (test-reports) or visual baselines (visual-regression).
---

# QA — Evidence Capture (Java / Playwright 1.63 + TestNG)

Decides **what evidence a run keeps, where it lands, and how it is read back**: the failure evidence every
test carries, the deliberate recordings a test or an agent makes on purpose, and the exploratory capture an
agent takes while it drives a browser. The mechanics for every capture API, in Java spellings, are in
[`references/playwright.md`](references/playwright.md).

Native mobile (Appium): [`references/appium.md`](references/appium.md).

## Versions

This skill pins nothing. Playwright `1.63.0`, the `mcr.microsoft.com/playwright/java:v1.63.0-noble` image and
allure-testng `3.0.0` are the **Versions** table of `qa/java/skills/ui-test-author/playwright/SKILL.md`. Each
API below carries the version it shipped in; on an older project, check the tag before teaching it.

The playwright.dev Java pages already list 1.64 options that the 1.63 binding does not have. From 1.64:
`Screencast.StartOptions.setFps`, `Screencast.ShowActionsOptions.setStyle` and
`Browser.NewContextOptions.setRecordVideoFps`. Do not teach them until the project's Playwright is 1.64.

## Who owns what

| Concern | Owner |
|---|---|
| The failure-evidence defaults (trace, video, screenshot on failure) | `qa/java/skills/ui-test-author/playwright/assets/BaseTest.java` — its `closeContext` hook and private `keep*` helpers, explained in that skill's `references/lifecycle.md` §5. This skill explains them and never adds a second hook for the same evidence |
| The Appium failure evidence (screenshot, page source, device log, recording) | `qa/java/skills/ui-test-author/appium/assets/BaseMobileTest.java`, explained in `references/appium.md` |
| Capture options, deliberate recordings, exploratory capture, reading a trace, PII | **this skill** |
| The Cucumber scenario hook that keeps the same evidence for `qa-bdd-java` | `qa/java/skills/bdd-project-scaffold` (its `Hooks` class) |
| Mapping the evidence into Allure (adapter, history, categories, publish) | `qa/reporting/java/skills/test-reports` |
| Uploading and retaining the evidence in CI | `qa/cicd/java/skills/ci-pipelines` and `qa/cicd/ci-conventions` |
| Screenshot comparison against baselines | `qa/java/skills/visual-regression` |
| HAR replay (`routeFromHAR`) | `qa/java/skills/network-mocking` |

## When to use

- A suite needs failure evidence, or its evidence is missing, too heavy or in the wrong place.
- A test or a demo needs a deliberate recording: a bug repro, a walkthrough, an agent's "receipt" of what it
  did.
- An agent drives Playwright MCP or `playwright-cli` and must leave screenshots, a video or a trace behind.
- A test failed and its trace must be read before anything changes.

## When NOT to use

- Writing tests, page objects, `BaseTest` or the build → `qa/java/skills/ui-test-author/playwright`
- Allure adapter, steps, history, publish → `qa/reporting/java/skills/test-reports`
- Screenshot baselines and diffs → `qa/java/skills/visual-regression`
- Mocking or replaying network → `qa/java/skills/network-mocking`
- Pipeline YAML → `qa/cicd/java/skills/ci-pipelines`

## The three kinds of capture

| Kind | Who starts it | API | Lands in |
|---|---|---|---|
| **Failure evidence** | `BaseTest`, on every test | `context.tracing().start(...)`, `setRecordVideoDir`, `page.screenshot(...)` on failure | `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`, each also attached to Allure |
| **Deliberate recording** | the test class's own `@BeforeMethod` / `@AfterMethod`, on purpose | `page.screencast()` [1.59], `tracing().startHar(...)` [1.60], a screenshot helper | `build/playwright-artifacts/<Class>.<method>.<kind>.<ext>`, attached to Allure |
| **Exploratory capture** | an agent, live | Playwright MCP capture tools, or `playwright-cli` | `evidence/<YYYY-MM-DD>-<topic>/` (explicit filenames); `.playwright-mcp/` for auto-named MCP output |

Java has no test runner that manages evidence: there are no trace or video *modes*, no `error-context.md`
and no `test-results/` folder. `BaseTest` builds the same behaviour by hand.

## Failure evidence: the defaults (R7)

`BaseTest` sets these, and the CI references upload exactly this folder:

| Evidence | Recorded | Kept | File |
|---|---|---|---|
| Trace — screenshots, DOM snapshots, sources | every test (`tracing().start` in `openContext`) | failed tests (`stop(setPath)`); a pass calls `stop()` with no path, which discards it | `build/playwright-artifacts/<Class>.<method>.zip` |
| Video | every test (`setRecordVideoDir(build/playwright-videos)`) | failed tests (`saveAs` after `context.close()`); `delete()` always | `build/playwright-artifacts/<Class>.<method>.webm` |
| Full-page screenshot | on failure only | failed tests | `build/playwright-artifacts/<Class>.<method>.png` |
| Retries | — | — | `0`. Retries follow `qa/cicd/ci-conventions`: none, except a documented hotspot |

That is the R7 `retain-on-failure` behaviour: recorded always, kept only on failure, so it works with zero
retries.

- **`build/playwright-videos/` is scratch.** It holds the raw recording of the running test and is emptied
  after every test. It is never uploaded, never read, never a path in a report.
- **Paths are relative to the Gradle test task's working directory**, the module folder. In a multi-module
  build the folder is `<module>/build/playwright-artifacts/`, and that is what CI uploads.
- **`<Class>.<method>` is the simple class name and the method name.** Every row of a data provider shares
  it, so when two rows fail the files on disk hold the last failing row; Allure keeps each row's own
  attachments.
- **Hook order is fixed** (lifecycle.md §5): read `page.video()`, then on failure the screenshot and
  `tracing().stop(setPath)`, then `context.close()`, then `video.saveAs(...)`, then `video.delete()`.
  Java's `saveAs` throws until the context is closed.
- **The one catch** is `keepScreenshot`'s narrow `PlaywrightException` catch, logged with a message
  template, so a crashed page still keeps its trace and video. Any capture that runs from a hook and
  touches a page that may have crashed follows the same pattern (plan D29): the catch sits in a private
  helper, never in the hook body or a test. A failing `@AfterMethod` would otherwise skip every remaining
  test in the class under TestNG's default `configfailurepolicy=skip`.
- **Changing a default means editing `BaseTest`, in one place** — for example adding
  `setAriaSnapshots(true)` [1.63] to the trace's `StartOptions` so the viewer's **Display Aria** mode has
  data. Never a second `@AfterMethod`, listener or base class for the same evidence. A video size is the
  exception: `setRecordVideoSize(w, h)` in a class's `contextOptions()` override survives, because
  `BaseTest` sets only the base URL and the video folder after calling the hook.
- **Raw tracing does not record assertions.** Unlike the Node runner, `context.tracing()` captures the
  Playwright actions but not the `assertThat(...)` calls, and Java has no runner tracing. The assertion
  failure lives in the TestNG result and in Allure; the trace shows what the page did up to it. Name
  locators with `locator.describe("…")` [1.53] and group a page-object method's actions with
  `tracing().group(...)` [1.49] so the trace reads as the journey.

**Cucumber scenarios** (`qa-bdd-java`) keep the same three files in the same folder, named
`<Feature>.<Scenario>` with every character outside `[A-Za-z0-9._-]` replaced by `_`, from the scaffold's
`@After` hook with `Scenario.isFailed()`. The hook code is `bdd-project-scaffold`'s; this skill's rules
(hook order, the one catch, no upload of raw videos) apply to it unchanged.

## Deliberate recordings

A deliberate recording runs in the **test class's own `@BeforeMethod` / `@AfterMethod(alwaysRun = true)`**.
TestNG runs those inside `BaseTest`'s hooks, so the page is open in both. The test body never calls `page`
directly; it calls a page object or the class's helper. Code for each is in `references/playwright.md`.

- **Receipt video** — `page.screencast().start(...)` [1.59] records exactly the span you choose, with action
  annotations (`AnnotatePosition.TOP_RIGHT` — an enum; the 1.59 release-note samples pass a `"top-right"`
  string, which does not compile in Java), chapter cards and overlays. **Stop it before the page closes**:
  the recording is lost when the page closes first (Playwright issue #41608). The class's `@AfterMethod`
  runs before `BaseTest.closeContext`, so `stop()` belongs there, through a helper that holds the D29
  catch. A receipt is kept whether the test passed or failed.
- **Network log** — `page.context().tracing().startHar(path, options)` [1.60] in `@BeforeMethod`,
  `stopHar()` in `@AfterMethod`, then attach. `setRecordHarPath` in `contextOptions()` also works, but it
  writes on `context.close()` and its path is fixed per class.
- **One screenshot at a point in the flow** — an `Evidence` helper built with the page objects, whose
  `screenshot(name)` attaches `page.screenshot(...)` with `setFullPage(true)`, `ScreenshotAnimations.DISABLED`,
  `ScreenshotCaret.HIDE` and `ScreenshotScale.CSS`.
- **Every attachment uses the allure-java 3.0 API** —
  `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`. The 2.x
  `Allure.addAttachment(...)` no longer exists. A trace attached by hand uses type
  `application/vnd.allure.playwright-trace`.

## Exploratory capture (agents)

An agent exploring a live page takes evidence with the Playwright MCP capture tools. The video and trace
tools need the server registered with `--caps=devtools`:
`claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=testing,storage,devtools --isolated --output-dir=.playwright-mcp`.
When MCP is not connected, or a long session would flood the context, the same capture runs through
`playwright-cli` (`npm i -g @playwright/cli@latest`) from `Bash`. MCP stays the primary route. Both need
Node; the Java project does not.

| Capture | Playwright MCP | `playwright-cli` |
|---|---|---|
| Screenshot | `mcp__playwright__browser_take_screenshot` `{ filename: "evidence/2026-10-10-login/error.png", fullPage: true, type: "png", scale: "css" }` | `playwright-cli screenshot --filename=evidence/2026-10-10-login/error.png --full-page` |
| Video start | `mcp__playwright__browser_start_video` `{ filename: "evidence/2026-10-10-login/flow.webm", size: { width: 1280, height: 720 }, fps: 25 }` | `playwright-cli video-start evidence/2026-10-10-login/flow.webm --size=1280x720 --fps=25` |
| Video stop | `mcp__playwright__browser_stop_video` | `playwright-cli video-stop` |
| Trace start | `mcp__playwright__browser_start_tracing` | `playwright-cli tracing-start` |
| Trace stop | `mcp__playwright__browser_stop_tracing` (returns the trace file links) | `playwright-cli tracing-stop` (traces under `.playwright-cli/traces/`) |

- With `filename` set, the screenshot is written to disk and not returned as an image, and the path
  resolves against the workspace root. Act on `browser_snapshot`, not on screenshots.
- Chapter cards and action overlays on an exploratory video are `playwright-cli video-chapter <title>` and
  `video-show-actions`. Their MCP twins are not in the qa agents' allowlist.
- The MCP and CLI browser is Playwright's own, not the suite's 1.63 binding; the video `fps` there is fine,
  and it is not an API the Java tests may use.
- The removed `--save-trace` and `--save-video` server flags (MCP 0.0.69) are never suggested.

## Reading a failure (agents read before they change code)

A failing test is diagnosed from its evidence before any edit. In order:

1. The failure itself: the assertion message and stack in Allure, or in
   `build/test-results/test/TEST-<class>.xml` (`build/reports/tests/test/index.html` for a human).
2. `build/playwright-artifacts/<Class>.<method>.png` — the page at the moment of failure.
3. The trace, with the trace analysis CLI [1.59]:
   - with Node: `npx playwright@1.63.0 trace open build/playwright-artifacts/<Class>.<method>.zip`;
   - without Node, through the Java driver: `./gradlew playwright --args="trace open build/playwright-artifacts/<Class>.<method>.zip"`,
     and the same `--args` form for every command below (built into the 1.63 driver's CLI; not yet run in
     this library — plan D39).
4. `trace errors`, then `trace actions --errors-only` (or `--grep <text>`), then `trace action <id>` on the
   failing step; `trace snapshot <id> --name before` (or `after`) for the DOM at that moment; `trace requests`
   / `trace console` when the network or the page log is the suspect.
5. `trace close`. The extracted data sits in `.playwright-cli/trace/` until then.
6. The video, when the sequence of events still is not clear.

From CI: download the shard's `playwright-artifacts-<n>` artifact. A human opens a trace with
`./gradlew playwright --args="show-trace <zip>"` or drops it on https://trace.playwright.dev, which loads it
in the browser without uploading it; Allure also opens the attached trace in the trace viewer.

## PII and retention

- Traces, HAR files and videos carry cookies, tokens and form input. They are **never committed**:
  `.gitignore` holds `build/`, `evidence/`, `.playwright-mcp/` and `.playwright-cli/`. The signed-in state
  (`build/.auth/user.json`) is under `build/` for the same reason.
- Mask what a screenshot must not show (`setMask(List.of(locator))`, or `setStyle(...)` to hide it). Record
  HAR with `HarContentPolicy.OMIT` and a URL filter unless bodies are the point. A trace cannot be redacted,
  so tests run as disposable test users, never real accounts.
- MCP's `--secrets <dotenv>` replaces secret values in tool responses; Playwright calls it "not a security
  feature", so it never replaces disposable credentials.
- Retention follows `qa/cicd/ci-conventions`: traces, videos and HAR 14 days, uploaded on failure only.

## Rules

- The failure-evidence defaults live in `BaseTest` only; no second `@AfterMethod`, `ITestListener`, base
  class or reporter for the same evidence. A changed default is an edit to `BaseTest`.
- Evidence lands in `build/playwright-artifacts/` and nowhere else; `build/playwright-videos/` is never
  uploaded or referenced.
- Deliberate recordings run in the test class's own hooks, write next to the failure evidence with a
  `.<kind>` suffix, and are attached with `Allure.attachment(..., AttachmentOptions.withFileExtension(ext))`.
- A screencast is stopped before its page closes, through a helper with a narrow, logged
  `PlaywrightException` catch.
- `AnnotatePosition` and every other option value is the binding's enum, never a string.
- No 1.64-only option on the 1.63 binding.
- Exploratory evidence uses explicit filenames under `evidence/<YYYY-MM-DD>-<topic>/`, never `build/`.
- A failure is read from its message, screenshot and trace before code changes.
- Nothing captured is committed; nothing real is recorded.

## Handoffs

- `BaseTest`, the build and the show-trace / codegen commands → `qa/java/skills/ui-test-author/playwright`
- Cucumber scenario hooks → `qa/java/skills/bdd-project-scaffold`
- Allure mapping of the evidence → `qa/reporting/java/skills/test-reports`
- Upload paths and retention → `qa/cicd/java/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- Screenshot comparison → `qa/java/skills/visual-regression`
- HAR replay → `qa/java/skills/network-mocking`
