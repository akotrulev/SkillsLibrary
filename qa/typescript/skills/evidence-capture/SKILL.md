---
name: evidence-capture
description: Use when a Playwright or Appium/WebdriverIO TypeScript suite or agent must keep evidence — screenshots, video, traces, HAR, page source, device logs, recordings — or read a failure's evidence before a fix. Triggers "keep trace and video on failure", "record a screencast", "keep a recording when the mobile test fails". Do NOT use for writing tests or config (ui-test-author/*), Allure wiring (test-reports) or visual baselines (visual-regression).
---

# QA — Evidence Capture (TypeScript: Playwright 1.64 and Appium 3)

Decides **what evidence a run keeps, where it lands, and how it is read back**: the failure evidence every
test carries, the deliberate recordings a test or an agent makes on purpose, and the exploratory capture an
agent takes while it drives a browser. The mechanics for every capture API are in
[`references/playwright.md`](references/playwright.md) for a browser, and in
[`references/appium.md`](references/appium.md) for a native mobile app.

## Versions

This skill pins nothing. The Playwright, Docker and `allure-playwright` versions are the **Versions** table
of `qa/typescript/skills/ui-test-author/playwright/SKILL.md`; the WebdriverIO and Appium versions are the
**Versions** table of `qa/typescript/skills/ui-test-author/appium/SKILL.md`. Each API below is tagged with the version it
shipped in; on an older project, check the tag before teaching the API.

## Who owns what

| Concern | Owner |
|---|---|
| The failure-evidence defaults (`trace`, `video`, `screenshot` in `use`) | `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts` — the one config. This skill explains it and never adds a second hook for the same evidence |
| The Appium failure hook (screenshot, page source, device log, a recording kept on failure) | `qa/typescript/skills/ui-test-author/appium/assets/BaseTest.ts`, wired in `wdio.conf.ts`. `references/appium.md` explains it; no spec adds another |
| Capture modes, deliberate recordings, exploratory capture, reading a trace, PII | **this skill** |
| Mapping the evidence into Allure (trace type, diff widget, labels) | `qa/reporting/typescript/skills/test-reports` |
| Uploading and retaining the evidence in CI | `qa/cicd/typescript/skills/ci-pipelines` and `qa/cicd/ci-conventions` |
| Visual baselines and screenshot assertions | `qa/typescript/skills/visual-regression` |
| HAR replay (`routeFromHAR`) | `qa/typescript/skills/network-mocking` |

## When to use

- A suite needs failure evidence, or its evidence is missing, too heavy or in the wrong place.
- A test or a demo needs a deliberate recording: a bug repro, a walkthrough, an agent's "receipt" of what
  it did.
- An agent drives Playwright MCP or `playwright-cli` and must leave screenshots, a video or a trace behind.
- A test failed and its trace must be read before anything changes.

## When NOT to use

- Writing specs, page objects, fixtures or the config → `qa/typescript/skills/ui-test-author/playwright`
- Allure adapter, labels, history, publish → `qa/reporting/typescript/skills/test-reports`
- `toHaveScreenshot` baselines → `qa/typescript/skills/visual-regression`
- Mocking or replaying network → `qa/typescript/skills/network-mocking`
- Pipeline YAML → `qa/cicd/typescript/skills/ci-pipelines`

## The three kinds of capture

| Kind | Who starts it | API | Lands in |
|---|---|---|---|
| **Failure evidence** | the runner, from the config | `use.trace` / `use.video` / `use.screenshot`, plus `error-context.md` [1.53]. Appium: the `afterTest` hook | `test-results/<one folder per test>/` → the HTML report, the blob, `allure-results/`. Appium: `test-results/appium/<test title>/` and Allure |
| **Deliberate recording** | a fixture, on purpose | `page.screencast` [1.59], `context.tracing.startHar()` [1.60], `testInfo.attach()` | the test's `testInfo.outputPath(...)`, then attached |
| **Exploratory capture** | an agent, live | Playwright MCP capture tools, or `playwright-cli`; for a native app the Appium MCP tools | `evidence/<YYYY-MM-DD>-<topic>/` (explicit filenames); `.playwright-mcp/` for auto-named MCP output; `docs/app-map/screenshots/` for Appium screenshots |

`test-results/` is **cleaned at the start of every run**. Nothing that must survive a second run is
written there by hand; exploratory evidence goes to `evidence/`.

## Failure evidence: the defaults (R7)

The config asset sets these, and the CI references upload exactly these paths:

| Setting | Value | File per failed test |
|---|---|---|
| `trace` | `'retain-on-failure'` | `trace.zip` |
| `video` | `'retain-on-failure'` | `video.webm` (`video-N.webm` for several pages) |
| `screenshot` | `{ mode: 'only-on-failure', fullPage: true }` | `test-failed-N.png` |
| *(always on)* | — | `error-context.md`: the errors plus an AI-mode aria snapshot of the page |
| `retries` | `0` | Retries follow `qa/cicd/ci-conventions`: 0, except a documented hotspot |

| Path | Holds | CI |
|---|---|---|
| `test-results/` | per-test evidence above, and `junit.xml` on CI | uploaded on failure |
| `playwright-report/` | the HTML report with every attachment (local, or produced by `merge-reports`) | uploaded from the merge step |
| `blob-report/` | one blob per shard, carrying all attachments | merge input only |
| `allure-results/` | Allure results; trace, video and screenshot attached by `allure-playwright` | uploaded every run |

Choosing a different mode:

- `retain-on-failure` works with zero retries, which is why it is the default.
- `on-first-retry` and `on-all-retries` record only on a retry, so under `retries: 0` they **record
  nothing**. Never use them unless the spec is a documented retry hotspot.
- `retain-on-first-failure` records the first attempt only — the mode for a project that runs with
  retries, so retries run without the recording cost.
- `retain-on-failure-and-retries` [1.59] keeps every failing run and every retry. It is the most
  diagnostic and the heaviest; use it to compare a passing retry with the failed run.
- `'on'` records every test. It is for a local debugging session, never CI.
- Video has the same seven modes as trace since 1.61. Screenshot modes are `off`, `on`,
  `only-on-failure` and `on-first-failure` [1.49]. Older doc tables list fewer; the `TestOptions`
  reference is complete.
- A mode is set in the config asset (per project where a project differs), never inside a spec. A local
  run that needs everything uses `npx playwright test --trace on`; there is no `--video` or `--screenshot`
  flag.

## Appium: native app evidence

The hook keeps, for a failed test only: a screenshot, the page source, the device log tail (`logcat` or
`syslog`) and the screen recording. A passing test keeps nothing; the recording is started per test, stopped in
the teardown always, and dropped unless the test failed. The APIs and their limits are in
`references/appium.md`; the ones that decide a run:

- Android's `startRecordingScreen` gives **180 s per chunk**, and anything longer needs ffmpeg on the Appium host.
  `mobile: startMediaProjectionRecording` needs Android 10+. iOS recording needs **ffmpeg**, and
  `mobile: startXCTestScreenRecording` needs iOS 17+.
- WDIO 10's `stopRecordingScreen` takes one options object.
- On a device farm nothing is recorded locally (`DEVICE_FARM=1`); the vendor's session URL and the pass/fail
  mark are the evidence.
- An agent captures through `mcp__appium-mcp__appium_screenshot` (into `SCREENSHOTS_DIR`) and
  `mcp__appium-mcp__appium_screen_recording`.

**Maestro → `ui-test-author/maestro` § Evidence.**

## Deliberate recordings

A deliberate recording lives in a **fixture**, never inline in a test body, and lands in
`testInfo.outputPath(...)` so it travels with the test's other evidence.

- **Receipt video** — `page.screencast` [1.59] records exactly the span you choose, with action
  annotations [1.59], chapter cards and overlays. **Stop it before the page closes**: a screencast is lost
  when the page closes before `stop()` (Playwright issue #41608). A fixture that depends on `page` is torn
  down before `page` is, so `stop()` after `use()` is the safe place. The fixture is in
  `references/playwright.md` §3.
- **Network log** — `context.tracing.startHar(path)` [1.60] in a fixture, `stopHar()` in its teardown, then
  `testInfo.attach`. Never `test.use({ recordHar })`: it is not a test option.
- **One screenshot at a point in the flow** — a fixture method that attaches
  `page.screenshot({ fullPage: true, animations: 'disabled', caret: 'hide', scale: 'css' })`; the test
  calls the fixture, never `page` directly.
- **Every attachment is awaited** — `await testInfo.attach(name, { body | path, contentType })`; the file
  is copied, so the original may be deleted.

## Exploratory capture (agents)

An agent exploring a live page takes evidence with the Playwright MCP capture tools. The video and trace
tools need the server registered with `--caps=devtools`:
`claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=testing,storage,devtools --isolated --output-dir=.playwright-mcp`.
When MCP is not connected, or a long session would flood the context, the same capture runs through
`playwright-cli` (`npm i -g @playwright/cli@latest`) from `Bash`. MCP stays the primary route.

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
- The removed `--save-trace` and `--save-video` server flags (MCP 0.0.69) are never suggested.

## Reading a failure (agents read before they change code)

A failing test is diagnosed from its evidence before any edit. In order:

1. `test-results/<test folder>/error-context.md` — the error and the aria snapshot of the page at failure.
2. `npx playwright trace open test-results/<test folder>/trace.zip` [1.59].
3. `npx playwright trace errors`, then `npx playwright trace actions` (narrow with `--grep <text>`).
4. `npx playwright trace action <id>` on the failing step; `npx playwright trace snapshot <id> --name before`
   (or `after`) for the DOM at that moment; `trace requests` / `trace console` when the network or the page
   log is the suspect.
5. `npx playwright trace close`.

From CI: download the shard's `test-results` artifact for the zips, or the merged `playwright-report`
and run `npx playwright show-report <folder or .zip>` [1.60]. A human opens a trace with
`npx playwright show-trace <zip or URL>` or drops it on https://trace.playwright.dev, which loads it in
the browser without uploading it.

## PII and retention

- Traces, HAR files and videos carry cookies, tokens and form input. They are **never committed**:
  `.gitignore` holds `test-results/`, `playwright-report/`, `blob-report/`, `allure-results/`, `evidence/`,
  `.playwright-mcp/`, `.playwright-cli/` and `playwright/.auth/`.
- Mask what a screenshot must not show (`mask: [locator]`, or `style` to hide it). Record HAR with
  `content: 'omit'` and a `urlFilter` unless bodies are the point. A trace cannot be redacted, so tests run
  as disposable test users, never real accounts.
- MCP's `--secrets <dotenv>` replaces secret values in tool responses; Playwright calls it "not a security
  feature", so it never replaces disposable credentials.
- Retention follows `qa/cicd/ci-conventions`: traces, videos and HAR 14 days, uploaded on failure only.

## Rules

- The failure-evidence defaults live in the config asset only; this skill never adds a parallel failure
  hook, `afterEach` screenshot or second reporter for the same evidence.
- No mode that depends on a retry (`on-first-retry`, `on-all-retries`) while `retries` is `0`.
- No `trace: 'on'` or `video: 'on'` on CI.
- Deliberate recordings run in fixtures, write to `testInfo.outputPath(...)` and are attached with an
  awaited `testInfo.attach`.
- A screencast is stopped before its page closes.
- Exploratory evidence uses explicit filenames under `evidence/<YYYY-MM-DD>-<topic>/`, never `test-results/`.
- A failure is read from `error-context.md` and the trace before code changes; a mobile failure from its screenshot,
  page source and log tail.
- The Appium evidence lives in `BaseTest.ts` only; a recording is never kept for a passing test or recorded
  locally on a device farm.
- Nothing captured is committed; nothing real is recorded.

## Handoffs

- The config and the base fixtures → `qa/typescript/skills/ui-test-author/playwright`; the mobile base test → `qa/typescript/skills/ui-test-author/appium`
- Allure mapping of the evidence → `qa/reporting/typescript/skills/test-reports`
- Upload paths and retention → `qa/cicd/typescript/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- Visual diffs → `qa/typescript/skills/visual-regression`
- HAR replay → `qa/typescript/skills/network-mocking`
