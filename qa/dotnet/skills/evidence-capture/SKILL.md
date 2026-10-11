---
name: qa-evidence-capture-dotnet
description: Use when a Playwright .NET (NUnit) suite or agent session must keep evidence — failure screenshots, video, screencast receipts, traces, HAR — or a failure's trace must be read before a fix. Triggers "keep trace and video on failure", "record a screencast of this flow", "open the trace for this failing test", "capture evidence via Playwright MCP". Do NOT use for writing tests or BaseTest (ui-test-author/playwright), Allure wiring (test-reports) or visual baselines (visual-regression).
---

# QA — Evidence Capture (.NET / Playwright 1.63 + NUnit)

Decides **what evidence a run keeps, where it lands, and how it is read back**: the failure evidence every
test carries, the deliberate recordings a test or an agent makes on purpose, and the exploratory capture an
agent takes while it drives a browser. The mechanics for every capture API, in .NET spellings, are in
[`references/playwright.md`](references/playwright.md).

Native mobile (Appium 3): [`references/appium.md`](references/appium.md) — `BaseMobileTest` keeps a screenshot, page source, device log and recording on failure in `<WorkDirectory>/appium-artifacts/`.

## Versions

This skill pins nothing. `Microsoft.Playwright.NUnit` `1.63.0`, the
`mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` image and `Allure.NUnit` `2.15.0` are the **Versions**
table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md`. Each API below carries the version it shipped
in; on an older project, check the tag before teaching it.

The playwright.dev .NET pages already list 1.64 options that the 1.63 binding does not have. From 1.64:
`ScreencastStartOptions.Fps`, `ScreencastShowActionsOptions.Style` and
`BrowserNewContextOptions.RecordVideoFps`. Do not teach them until the project's Playwright is 1.64.

## Who owns what

| Concern | Owner |
|---|---|
| The failure-evidence defaults (trace, video, screenshot on failure); tests, page objects, the runsettings | `qa/dotnet/skills/ui-test-author/playwright` — `assets/BaseTest.cs` (`ContextOptions()`, `[SetUp] StartTracing`, `[TearDown] KeepEvidenceOnFailure`), explained in its `references/lifecycle.md` §6. This skill explains them and never adds a second hook for the same evidence |
| Capture options, deliberate recordings, exploratory capture, reading a trace, PII | **this skill** |
| The Reqnroll `[AfterScenario]` hook that keeps the same evidence for `qa-bdd-dotnet` | `qa/dotnet/skills/bdd-project-scaffold` |
| Mapping the evidence into Allure (adapter, history, categories, publish) | `qa/reporting/dotnet/skills/test-reports` |
| Uploading and retaining the evidence in CI | `qa/cicd/dotnet/skills/ci-pipelines` and `qa/cicd/ci-conventions` |
| Screenshot comparison against baselines | `qa/dotnet/skills/visual-regression` |
| HAR replay (`RouteFromHARAsync`) | `qa/dotnet/skills/network-mocking` |

## When to use

- A suite needs failure evidence, or its evidence is missing, too heavy or in the wrong place.
- A test or a demo needs a deliberate recording: a bug repro, a walkthrough, an agent's "receipt".
- An agent drives Playwright MCP or `playwright-cli` and must leave screenshots, a video or a trace behind.
- A test failed and its trace must be read before anything changes.

## When NOT to use

Writing tests or `BaseTest`, Allure wiring, baselines, network replay or pipeline YAML — the owners in the
table above.

## The three kinds of capture

| Kind | Who starts it | API | Lands in |
|---|---|---|---|
| **Failure evidence** | `BaseTest`, on every test | `Context.Tracing.StartAsync(...)`, `RecordVideoDir`, `Page.ScreenshotAsync(...)` on failure | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}`, each attached to the TRX and to Allure |
| **Deliberate recording** | the test class's own `[SetUp]` / `[TearDown]`, on purpose | `Page.Screencast` [1.59], `Context.Tracing.StartHarAsync(...)` [1.60], a screenshot helper | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.<kind>.<ext>`, attached the same way |
| **Exploratory capture** | an agent, live | Playwright MCP capture tools, or `playwright-cli` | `evidence/<YYYY-MM-DD>-<topic>/` (explicit filenames); `.playwright-mcp/` for auto-named MCP output |

`Microsoft.Playwright.NUnit` has no trace or video *modes*, no `error-context.md` and no `test-results/`
folder; `BaseTest` builds the same behaviour by hand.

## Failure evidence: the defaults (R7)

`BaseTest` sets these, and the CI references upload exactly this folder:

| Evidence | Recorded | Kept | File |
|---|---|---|---|
| Trace — screenshots, DOM snapshots, sources | every test (`StartTracing`, titled with the test's full name) | failed tests (`StopAsync(new() { Path })`); a pass calls `StopAsync()` with no path, which discards it | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.zip` |
| Video | every test (`RecordVideoDir = <WorkDirectory>/playwright-videos`) | failed tests (`SaveAsAsync` after `Context.CloseAsync()`); `DeleteAsync()` always | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.webm` |
| Full-page screenshot | on failure only | failed tests | `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.png` |
| Retries | — | — | none. Retries follow `qa/cicd/ci-conventions`: none, except a documented hotspot |

That is the R7 `retain-on-failure` behaviour: recorded always, kept only on failure, so it works with zero
retries.

- **`WorkDirectory` is NUnit's `TestContext.CurrentContext.WorkDirectory`**, the test assembly's folder,
  `bin/<cfg>/net10.0`. CI uploads `UiTests/bin/<cfg>/net10.0/playwright-artifacts/`.
- **"Failed" is `TestStatus.Failed`**, which includes errors and a failed `[SetUp]`.
- **`<Class>.<Test>` is the class name and NUnit's test name**, with every character outside
  `[A-Za-z0-9._-]` replaced by `_`. A `[TestCase]` row's name carries its arguments, so each failing row keeps
  its own files.
- **`<WorkDirectory>/playwright-videos/` is scratch**, emptied after every test; never uploaded or read.
- **Each kept file is attached twice**: `TestContext.AddTestAttachment(path, name)` (the TRX and the IDE) and
  `AllureApi.AddAttachment(name, type, path)`; the trace's type is `application/vnd.allure.playwright-trace`,
  which Allure opens in the trace viewer.
- **Teardown order is fixed** (lifecycle.md §6): read `Page.Video`; on failure stop the trace to a path,
  then take the full-page screenshot; `Context.CloseAsync()`; on failure `SaveAsAsync`; always
  `DeleteAsync()`. The derived teardown closes the context itself, because `BrowserTearDown` closes contexts
  only after a pass.
- **There is no catch** (plan D31). A screenshot of a crashed page throws; NUnit records a teardown error on
  that test, still runs the base teardowns, and the next test gets a fresh browser. The trace is already
  saved; only that test's video is lost. Never add a catch to keep the video.
- **Changing a default means editing `BaseTest`, in one place** — for example `AriaSnapshots = true` [1.63]
  in `StartTracing` so the viewer's **Display Aria** mode has data. Never a second `[TearDown]`, base class or
  action attribute for the same evidence. A video size is the exception: a class's `ContextOptions()`
  override amends `base.ContextOptions()` with `RecordVideoSize`, and keeps the folder `BaseTest` set.
- **Raw tracing does not record assertions.** `Context.Tracing` captures the actions, not the `Expect(...)`
  calls; the assertion failure is in the NUnit result, the TRX and Allure. Name locators with
  `Locator.Describe("…")` [1.53] and group a page-object method's actions with `Tracing.GroupAsync(...)`
  [1.49] so the trace reads as the journey.
- **Launch flags are not per class** (plan D32): a recording that needs one gets its own `.runsettings` and
  `dotnet test` run.

**Reqnroll scenarios** (`qa-bdd-dotnet`) keep the same three files in the same folder, named
`<Feature>.<Scenario>` with every character outside `[A-Za-z0-9._-]` replaced by `_`, from the scaffold's
`[AfterScenario]` hook when `ScenarioContext.TestError` is set. The hook code is `bdd-project-scaffold`'s;
this skill's rules (teardown order, no catch, no upload of raw videos) apply to it unchanged.

## Deliberate recordings

A deliberate recording runs in the **test class's own `[SetUp]` and `[TearDown]`**. NUnit runs a derived
`[SetUp]` after `BaseTest.StartTracing` and a derived `[TearDown]` before `BaseTest.KeepEvidenceOnFailure`,
so the page is open in both. The test body never calls `Page` directly; it calls a page object or the class's
helper. Code for each is in `references/playwright.md`.

- **Names and attachments come from `BaseTest`.** Its protected `EvidenceName()`, `Artifact(name, ext)` and
  `Attach(name, type, path)` (plan D42) give a recording the failure evidence's name, folder and double
  attachment: `Artifact(EvidenceName(), "receipt.webm")`.
- **Receipt video** — `Page.Screencast.StartAsync(...)` [1.59] records exactly the span you choose, with
  action annotations (`AnnotatePosition.TopRight` — an enum; the 1.59 release-note samples pass a
  `"top-right"` string, which does not compile in C#), chapter cards and overlays. **Stop it before the page
  closes**: the recording is lost when the page closes first (Playwright issue #41608). The class's
  `[TearDown]` runs before `BaseTest` closes the context, so `StopAsync()` belongs there. A receipt is kept
  whether the test passed or failed.
- **Network log** — `Context.Tracing.StartHarAsync(path, options)` [1.60] in `[SetUp]`, `StopHarAsync()` in
  `[TearDown]`, then attach. A `RecordHarPath` HAR is written on `Context.CloseAsync()`, after the class's
  teardown, so the class cannot attach it.
- **One screenshot at a point in the flow** — an `Evidence` helper built with the page objects, whose
  `ScreenshotAsync(name)` attaches `Page.ScreenshotAsync(...)` with `FullPage`, `ScreenshotAnimations.Disabled`,
  `ScreenshotCaret.Hide` and `ScreenshotScale.Css`.
- **A recording that fails to stop fails the teardown loudly** — no catch, as in `BaseTest`; NUnit still runs
  `KeepEvidenceOnFailure`.

## Exploratory capture (agents)

An agent exploring a live page takes evidence with the Playwright MCP capture tools. The video and trace
tools need the server registered with `--caps=devtools`:
`claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=testing,storage,devtools --isolated --output-dir=.playwright-mcp`.
When MCP is not connected, or a long session would flood the context, the same capture runs through
`playwright-cli` (`npm i -g @playwright/cli@latest`) from `Bash`. MCP stays the primary route. Both need
Node; the .NET project does not.

| Capture | Playwright MCP | `playwright-cli` |
|---|---|---|
| Screenshot | `mcp__playwright__browser_take_screenshot` `{ filename: "evidence/2026-10-10-login/error.png", fullPage: true, type: "png", scale: "css" }` | `playwright-cli screenshot --filename=evidence/2026-10-10-login/error.png --full-page` |
| Video start | `mcp__playwright__browser_start_video` `{ filename: "evidence/2026-10-10-login/flow.webm", size: { width: 1280, height: 720 }, fps: 25 }` | `playwright-cli video-start evidence/2026-10-10-login/flow.webm --size=1280x720 --fps=25` |
| Video stop | `mcp__playwright__browser_stop_video` | `playwright-cli video-stop` |
| Trace start | `mcp__playwright__browser_start_tracing` | `playwright-cli tracing-start` |
| Trace stop | `mcp__playwright__browser_stop_tracing` (returns the trace file links) | `playwright-cli tracing-stop` (traces under `.playwright-cli/traces/`) |

- With `filename` set, the screenshot goes to disk (relative to the workspace root), not into the context.
  Act on `browser_snapshot`, not on screenshots.
- Chapter cards and action overlays on an exploratory video are `playwright-cli video-chapter <title>` and
  `video-show-actions`. Their MCP twins are not in the qa agents' allowlist.
- The MCP and CLI browser is Playwright's own, not the suite's 1.63 binding; its video `fps` is not an API
  the .NET tests may use. The removed `--save-trace` / `--save-video` server flags are never suggested.

## Reading a failure (agents read before they change code)

A failing test is diagnosed from its evidence before any edit. In order:

1. The failure itself: the assertion message and stack in the `dotnet test` output, the TRX or Allure.
2. `bin/<cfg>/net10.0/playwright-artifacts/<Class>.<Test>.png` — the page at the moment of failure.
3. The trace, with the trace analysis CLI [1.59]:
   - with Node: `npx playwright@1.63.0 trace open bin/Debug/net10.0/playwright-artifacts/<Class>.<Test>.zip`;
   - without Node, through the .NET driver: `pwsh bin/Debug/net10.0/playwright.ps1 trace open <zip>`, and
     the same prefix for every command below (built into the 1.63 driver's CLI; not yet run in this
     library — plan D43).
4. `trace errors`, then `trace actions --errors-only` (or `--grep <text>`), then `trace action <id>` on the
   failing step; `trace snapshot <id> --name before` (or `after`) for the DOM at that moment; `trace requests`
   / `trace console` when the network or the page log is the suspect.
5. `trace close`. The extracted data sits in `.playwright-cli/trace/` until then.
6. The video, when the sequence of events still is not clear.

From CI: download the shard's `playwright-artifacts-<n>` artifact. A human opens a trace with
`pwsh bin/Debug/net10.0/playwright.ps1 show-trace <zip>`, on https://trace.playwright.dev (nothing is
uploaded), or from Allure's attachment.

## PII and retention

- Traces, HAR files and videos carry cookies, tokens and form input. They are **never committed**:
  `.gitignore` holds `bin/`, `obj/`, `evidence/`, `.playwright-mcp/` and `.playwright-cli/`. The signed-in
  state (`<WorkDirectory>/auth-user.json`) is under `bin/` for the same reason.
- Mask what a screenshot must not show (`Mask`, or `Style` to hide it); record HAR with
  `HarContentPolicy.Omit` unless bodies are the point. A trace cannot be redacted: test users are disposable.
- MCP's `--secrets <dotenv>` masks values in tool responses; it is "not a security feature" and never
  replaces disposable credentials.
- Retention follows `qa/cicd/ci-conventions`: traces, videos and HAR 14 days, uploaded on failure only.

## Rules

- The failure-evidence defaults live in `BaseTest` only; no second `[TearDown]`, base class, action attribute
  or event handler for the same evidence. A changed default is an edit to `BaseTest`.
- Evidence lands in `<WorkDirectory>/playwright-artifacts/` and nowhere else; `playwright-videos/` is never
  uploaded or referenced.
- Deliberate recordings run in the test class's own `[SetUp]` / `[TearDown]`, are named with
  `Artifact(EvidenceName(), "<kind>.<ext>")` and are attached with `Attach(...)`.
- A screencast is stopped in the class's `[TearDown]`, before `BaseTest` closes its page. No catch around it.
- `AnnotatePosition` and every other option value is the binding's enum, never a string.
- No 1.64-only option on the 1.63 binding.
- Exploratory evidence uses explicit filenames under `evidence/<YYYY-MM-DD>-<topic>/`, never `bin/`.
- A failure is read from its message, screenshot and trace before code changes.
- Nothing captured is committed; nothing real is recorded.

## Handoffs

- `BaseTest`, the project, the runsettings and the show-trace / codegen commands → `qa/dotnet/skills/ui-test-author/playwright`
- Reqnroll scenario hooks → `qa/dotnet/skills/bdd-project-scaffold`
- Allure mapping of the evidence → `qa/reporting/dotnet/skills/test-reports`
- Upload paths and retention → `qa/cicd/dotnet/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- Screenshot comparison and `AllureApi.AddScreenDiff` → `qa/dotnet/skills/visual-regression`
- HAR replay → `qa/dotnet/skills/network-mocking`
