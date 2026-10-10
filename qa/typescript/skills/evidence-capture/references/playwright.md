# Evidence capture — Playwright 1.64 (TypeScript)

Every capture API, with the version it shipped in. `SKILL.md` decides what to capture and where it lands;
this file is how. The fixtures below extend the `test` exported by
`qa/typescript/skills/ui-test-author/playwright/assets/fixtures.ts`, so a spec imports `test` and `expect`
from the evidence fixture file instead.

## 1. Screenshots

### 1.1 The API — `page.screenshot`, `locator.screenshot`

| Option | Values | Note |
|---|---|---|
| `path` | file path | Format from the extension; relative to the working directory. In a test, use `testInfo.outputPath(...)` |
| `fullPage` | `false` | The whole scrollable page. Page only |
| `clip` | `{ x, y, width, height }` | Page only |
| `type` | `'png'` · `'jpeg'` · `'webp'` [1.62] | `quality` 0–100: jpeg default 80; webp default 100 is lossless |
| `mask` | `Locator[]` | Covers each match with a box, invisible matches included; `maskColor` (default `#FF00FF`) [1.35] |
| `animations` | `'allow'` · `'disabled'` | Disabled fast-forwards finite animations and resets infinite ones |
| `caret` | `'hide'` · `'initial'` | Default `'hide'` |
| `scale` | `'device'` · `'css'` | `'css'` keeps HiDPI images small |
| `style` | CSS text [1.41] | Applied during capture; pierces shadow DOM and iframes — hides a clock, an avatar, a token |
| `omitBackground` | `true` | Transparent background; not for jpeg |
| `timeout` | ms | |

- `locator.screenshot()` takes the same options except `fullPage` and `clip`. It waits for actionability,
  scrolls the element into view and clips to it; anything covering the element shows in the image.
- `elementHandle.screenshot()` is discouraged; use the locator form.
- A one-off from the shell: `npx playwright screenshot --full-page <url> <file>`.

### 1.2 Runner screenshots

`use.screenshot` is `'off'` (default), `'on'`, `'only-on-failure'` or `'on-first-failure'` [1.49], or the
object `{ mode, fullPage, omitBackground }` [1.29]. At the end of a test the runner screenshots every open
page with `caret: 'initial'` and writes `test-failed-N.png` (or `test-finished-N.png`) into the test's
output folder, attached as `screenshot`. Pages closed mid-test are captured just before their context
closes.

### 1.3 A screenshot at a chosen point

```typescript
import { test as base } from './fixtures';

type Evidence = { screenshot: (name: string) => Promise<void> };

export const test = base.extend<{ evidence: Evidence }>({
  evidence: async ({ page }, use, testInfo) => {
    await use({
      screenshot: async (name) => {
        const body = await page.screenshot({ fullPage: true, animations: 'disabled', caret: 'hide', scale: 'css' });
        await testInfo.attach(name, { body, contentType: 'image/png' });
      },
    });
  },
});

export { expect } from './fixtures';
```

A test calls `await evidence.screenshot('Cart.BeforeCheckout')`. A screenshot is evidence, not an
assertion: comparing it to a baseline is `visual-regression`'s `toHaveScreenshot`.

## 2. Video

### 2.1 Runner video

| Mode | Records | Keeps |
|---|---|---|
| `'off'` | nothing | — |
| `'on'` | every test | every test |
| `'retain-on-failure'` | every test | failed tests — **the default** |
| `'on-first-retry'` | the first retry | that retry — nothing under `retries: 0` |
| `'on-all-retries'` | every retry | the retries — nothing under `retries: 0` |
| `'retain-on-first-failure'` | the first attempt [1.61] | the first attempt, if it failed |
| `'retain-on-failure-and-retries'` | every attempt [1.61] | failing attempts and every retry |

The last three arrived for video in 1.61; video now has exactly the trace modes. The object form:

```typescript
video: {
  mode: 'retain-on-failure',
  size: { width: 1280, height: 720 },
  fps: 25,
  show: { actions: { position: 'top-right' }, test: { level: 'step' } },
},
```

- `size` defaults to the viewport scaled to fit 800×800 (800×450 with no explicit viewport).
- `fps` [1.64] defaults to 25. Firefox and WebKit capture at most 25 fps.
- `show` [1.59] burns action annotations and the test title (`level: 'file' | 'title' | 'step'`) into the
  video; `actions.style: { point, highlight, title }` [1.64] replaces the deprecated `fontSize`.
- Output: `video.webm`, or `video-N.webm` for several pages, attached as `video`. Encoding is VP9 since
  1.64 (smaller, less CPU); the cursor stays visible on an eased path.
- `reuseContext: true` [1.62, experimental] is ignored while video is on.

### 2.2 Library video (outside the runner)

```typescript
const context = await browser.newContext({
  baseURL: process.env.BASE_URL,
  recordVideo: { dir: 'evidence/2026-10-10-checkout', size: { width: 1280, height: 720 } },
});
const page = await context.newPage();
await page.goto('/checkout');
await context.close();
await page.video()?.saveAs('evidence/2026-10-10-checkout/checkout.webm');
```

- `recordVideo: { dir, size, fps [1.64], showActions }` — `dir` is optional and defaults to the launch
  option `artifactsDir` [1.59].
- The file is complete only after `context.close()` is awaited. In TypeScript `saveAs()` may be called
  before close and waits for it; `path()` throws when the browser is remote (Docker `run-server`, a grid),
  so use `saveAs()` there. `delete()` removes it.
- The old `videosPath` / `videoSize` context options were removed in 1.60.

## 3. Screencast — a recording you start and stop [1.59]

`page.screencast` records the span you choose and annotates it — the Playwright team's "agentic video
receipt".

| Call | Does |
|---|---|
| `start({ path, size, quality, fps [1.64], onFrame })` | Starts recording; `path` gets a `.webm` on `stop()`. `onFrame({ data, timestamp [1.61], viewportWidth, viewportHeight })` streams JPEG frames. Returns a `Disposable` |
| `stop()` | Ends the recording and writes `path` |
| `showActions({ position, duration, cursor, style [1.64] })` / `hideActions()` | Annotates each action (`duration` default 500 ms, `cursor: 'pointer' \| 'none'` [1.61]) |
| `showChapter(title, { description, duration })` | A centred chapter card over a blurred page (`duration` default 2000 ms) |
| `showOverlay(html, { duration })` / `showOverlays()` / `hideOverlays()` | Custom HTML over the page; `showOverlay` returns a `Disposable` |

Known issues, all open or regressed on 2026-10-10:

- **The video is lost if the page closes before `stop()`** (issue #41608). Stop first, always.
- When `video` or tracing has already started a screencast on the page, the existing configuration wins
  over the options passed to `start()`.
- Tracing clamps the capture size and pads with grey (#42274).
- There is no `saveAs()`; `path` is local to the client process even against a remote browser (#42392).

The receipt fixture stops the screencast after `use()`. A fixture that depends on `page` is torn down
before `page`, so the page is still open when `stop()` runs:

```typescript
import { test as base } from './fixtures';

type Receipt = { chapter: (title: string) => Promise<void> };

export const test = base.extend<{ receipt: Receipt }>({
  receipt: async ({ page }, use, testInfo) => {
    const path = testInfo.outputPath('receipt.webm');
    await page.screencast.start({ path });
    await page.screencast.showActions({ position: 'top-right' });
    await use({
      chapter: async (title) => {
        await page.screencast.showChapter(title);
      },
    });
    await page.screencast.stop();
    await testInfo.attach('receipt', { path, contentType: 'video/webm' });
  },
});

export { expect } from './fixtures';
```

A test that names `receipt` is recorded and calls `await receipt.chapter('Sign in')` between journeys.
Teardown runs whether the test passed or failed, so the receipt exists for both.

## 4. Trace

### 4.1 Runner trace

Modes are the seven in §2.1, with the same meaning; `retain-on-failure` is the default. The docs call
`'on'` performance-heavy. The object form:

```typescript
trace: {
  mode: 'retain-on-failure',
  snapshots: { dom: true, aria: true, screen: true },
  screenshots: true,
  sources: true,
  attachments: true,
},
```

- `snapshots` as an object [1.63] adds aria snapshots per action, shown in the viewer's **Display Aria**
  mode; `true` is the DOM snapshot alone.
- Output: `trace.zip` in the test's output folder, attached as `trace`. The runner traces each context and
  uses one chunk per test.
- **Runner tracing records `expect` calls and `test.step`s; the raw `context.tracing` API does not.**
  Inside Playwright Test, the `trace` option is the tracer.
- `npx playwright test --trace <mode>` overrides the mode for one run and accepts all seven.
- UI mode (`--ui`) traces every test on its own.

### 4.2 Making a trace readable

- `test.step(title, body, { box, location, timeout [1.50] })` groups actions in the trace and the report;
  1.63 shows step `subtitle` and `params`, and Playwright API steps get the locator or URL as subtitle.
- `locator.describe('Checkout button')` [1.53] names a locator in traces and reports.
- Page-object methods wrap their actions in `test.step` with the user intent as the title, so a trace reads
  as the journey, not as clicks.

### 4.3 Library tracing (code the runner does not manage)

```typescript
await context.tracing.start({ title: 'checkout', screenshots: true, snapshots: true, sources: true });
await context.tracing.stop({ path: 'evidence/2026-10-10-checkout/trace.zip' });
```

- `stop()` without `path` discards the trace. In TypeScript `start()` returns a `Disposable` that stops
  without saving.
- `start({ live: true })` [1.59] writes an unarchived trace that updates in real time.
- `startChunk({ name, title })` / `stopChunk({ path })` [1.15] cut several traces from one `start()`.
- `tracing.group(name)` / `groupEnd()` [1.49] group actions; under the runner, `test.step` is the
  equivalent and is preferred.

## 5. HAR

- **Per test, on purpose** — `context.tracing.startHar(path, { content, mode, urlFilter })` [1.60] /
  `stopHar()`. One HAR per tracing at a time:

```typescript
import { test as base } from './fixtures';

export const test = base.extend<{ networkHar: void }>({
  networkHar: [
    async ({ context }, use, testInfo) => {
      const path = testInfo.outputPath('network.har');
      await context.tracing.startHar(path, { content: 'omit', urlFilter: '**/api/**' });
      await use();
      await context.tracing.stopHar();
      await testInfo.attach('network.har', { path, contentType: 'application/json' });
    },
    { auto: true },
  ],
});

export { expect } from './fixtures';
```

- **For every context in a project** — `use: { contextOptions: { recordHar: { path, content, mode, urlFilter } } }`.
  The HAR is written on `context.close()`, and one fixed `path` collides across parallel tests, so prefer
  the fixture. `recordHar` is not a test option: `test.use({ recordHar })` is wrong. It is not supported
  with `reuseContext`.
- `content`: `'omit'` (no bodies — the PII-safe default), `'embed'`, or `'attach'` (default for `.zip`).
  `mode: 'minimal'` keeps only what replay needs.
- HAR and traces include WebSocket traffic since 1.61.
- From the shell: `npx playwright open --save-har=evidence/app.har --save-har-glob="**/api/**" <url>`.
- Replaying or updating a HAR (`routeFromHAR`) is `qa/typescript/skills/network-mocking`.

## 6. Attachments

- `await testInfo.attach(name, { body | path, contentType })` — the file is copied into the results, so
  the original may be deleted. Always awaited.
- `testInfo.outputPath('file.ext')` is the per-test output folder; writing there keeps evidence with its
  test and inside the CI upload.
- Inside a step [1.51]:

```typescript
await test.step('Submit the order', async (step) => {
  await checkoutPage.submit();
  await step.attach('confirmation', { body: await checkoutPage.confirmationText(), contentType: 'text/plain' });
});
```

- `allure-playwright` turns every attachment into an Allure attachment and re-types `trace` as
  `application/vnd.allure.playwright-trace`. That mapping is `qa/reporting/typescript/skills/test-reports`.

## 7. `error-context.md` [1.53]

On any test error the runner writes `error-context.md` (`text/markdown`) with the errors and an AI-mode
aria snapshot of the page (`page.ariaSnapshot({ mode: 'ai' })`). It is the cheapest evidence there is and
the first file an agent reads. `testInfoError.errorContext` [1.60] exposes the same snapshot to a reporter.
The HTML report's **Copy prompt** button is built from it; `html` reporter `noCopyPrompt` [1.56] hides it.

## 8. Viewing and reading evidence

| Command | Does |
|---|---|
| `npx playwright show-report [folder]` | Opens the HTML report; a downloaded `playwright-report.zip` opens directly [1.60] |
| `npx playwright show-trace <zip or URL>` | The trace viewer; `-p 0` picks a free port |
| https://trace.playwright.dev | Loads a trace in the browser without uploading it; `?trace=<url>` opens a hosted one (CORS applies) |
| `npx playwright trace open <zip>` [1.59] | Opens a trace for the analysis commands below — the agent route |
| `npx playwright trace errors` · `console` · `requests` · `request <id>` | Errors, page log, network |
| `npx playwright trace actions [--grep <text>]` · `action <id>` | The action list and one action's detail |
| `npx playwright trace snapshot <id> --name before\|after` · `screenshot <id>` | The DOM or the screen at an action |
| `npx playwright trace attachments` · `attachment <n>` · `close` | Attachments in the trace; close the session |
| VS Code **Show Trace Viewer** | Opens the trace after each run from the Playwright sidebar |

`npx playwright trace install-skill` installs Microsoft's trace skill for agents; this skill already
documents the commands, so it is optional.

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
- The CLI keeps an in-memory profile by default and closes a headless session after an hour. It is
  bundled as `npx playwright cli` since 1.62.
- Exploratory videos are WebM, VP9 since 1.64. Open traces with §8.

## 10. Codegen's recorder

`npx playwright codegen [url]` records actions into code (`--target playwright-test` by default;
`--test-id-attribute`, `--save-har`, `--save-storage`, `--device`, `--viewport-size`). The 1.64 toolbar has
**Pick locator**, **Assert visibility**, **Assert text**, **Assert value** and **Assert snapshot** (an aria
snapshot assertion), and the setting "Automatically generate assertions while recording" [1.55].
Recorded code is a draft: every locator is rewritten against the ladder in
`qa/typescript/skills/ui-test-author/playwright/references/locators.md` before it lands.

## 11. Size and CI

- The blob reporter carries every attachment, so `merge-reports` rebuilds one HTML report with all the
  traces, videos and screenshots of every shard.
- Size levers: video VP9 [1.64]; `scale: 'css'` for HiDPI screenshots; jpeg or webp with `quality < 100`
  for ad-hoc screenshots; `preserveOutput: 'failures-only'` prunes passing tests from `test-results/`.
- `test-results/` is the config's `outputDir` default and is cleaned at the start of every run.
- Upload paths and retention: `qa/cicd/typescript/skills/ci-pipelines` and `qa/cicd/ci-conventions`.
