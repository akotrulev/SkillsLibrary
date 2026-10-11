# Evidence capture — Appium 3 / WebdriverIO 10 (TypeScript)

Every capture API for a native mobile run, with its limits. `SKILL.md` decides what a run keeps and where it lands; this file is how. The hook is `qa/typescript/skills/ui-test-author/appium/assets/BaseTest.ts`: `wdio.conf.ts` wires its `beforeTest` and `afterTest`, and no spec adds another failure hook. `qa/reporting/typescript/skills/test-reports` defers to it for WebdriverIO and Appium.

## 1. What a failed test keeps

| Evidence | API | File in `test-results/appium/<test title>/` | Allure type |
|---|---|---|---|
| Screenshot | `browser.takeScreenshot()` (base64) | `screenshot.png` | `image/png` |
| Page source | `browser.getPageSource()` | `page-source.xml` | `application/xml` |
| Device log tail (last 200 lines) | `browser.getLogs('logcat')` on Android, `'syslog'` on iOS | `logcat.log` / `syslog.log` | `text/plain` |
| Screen recording, kept only on failure | `startRecordingScreen` in `beforeTest`, `stopRecordingScreen` in `afterTest` | `recording.mp4` | `video/mp4` |

- A passing test keeps nothing; the recording is stopped and dropped.
- Allure's own screenshot reporting is off (`disableWebdriverScreenshotsReporting: true`), so the hook's attachment is the only one. Turning it on would attach a second, differently timed copy.
- Evidence must never mask the failure it documents. Each capture runs through `tolerate`, which catches one thing, an `Error` from the capture itself, logs `Could not capture <what>: <message>` and goes on. Anything that is not an `Error` is rethrown.
- The page source is the mobile twin of a DOM snapshot and the best locator-debugging artifact: a missing node there is an accessibility, app-state or context problem before it is a selector problem.
- A secure window (`FLAG_SECURE`) renders black in a screenshot or recording. That is the app, not the hook.

## 2. Screenshots

| Need | WDIO 10 |
|---|---|
| The screen | `await browser.takeScreenshot()` → base64 · `await browser.saveScreenshot('./shot.png')` → `Buffer` |
| One element | `await $(selector).saveScreenshot('./element.png')` |
| Every display, Android 10+ | `await browser.execute('mobile: screenshots', {})` → a list of `{ id, name, isDefault, payload }`; narrow with `displayId` from `mobile: listDisplays` |
| The iOS viewport without the status bar | `mobile: viewportScreenshot`; the driver docs mark it unreliable, so prefer `takeScreenshot` |

The element route is `GET /element/:id/screenshot`; the old `/screenshot/:id` was removed in Appium 3. On iOS, coordinates read off a screenshot are pixels, and a tap takes points: divide by the device pixel ratio (2 or 3).

## 3. Page source and device logs

- `browser.getLogTypes()` lists what the device offers. Android: `logcat`, `bugreport`, `server`. iOS: `syslog`, `crashlog`, `performance`, `safariConsole`, `safariNetwork`, `server`.
- UiAutomator2 captures logcat by default. `'appium:skipLogcatCapture': true` turns that off and leaves nothing to read.
- `server` logs need the insecure feature on the Appium server, scoped in Appium 3: `--allow-insecure=uiautomator2:get_server_logs` (or `*:get_server_logs`). The unscoped form throws. Log retrieval itself moved from `/log` to `/se/log`, which WDIO 10 handles.
- A log is a list of `{ timestamp, level, message }`; the hook keeps the tail, because a full logcat is large.
- Streaming is `mobile: startLogsBroadcast` and `stopLogsBroadcast`, or BiDi `log.entryAdded`. The exact WDIO BiDi subscription for Appium is unverified, so the hook pulls the log instead.

## 4. Screen recording

### 4.1 Mechanisms and limits

| Mechanism | Platform | Limits |
|---|---|---|
| `browser.startRecordingScreen(options)` / `stopRecordingScreen()` | Android (adb `screenrecord`) | **180 s per chunk.** `timeLimit` accepts 1–1800 s; above 180 s the driver records successive chunks and merges them with **ffmpeg on the Appium host**. Without ffmpeg on `PATH` the stop call fails with "ffmpeg utility is not available in PATH". `bugReport` needs API 27+ |
| `browser.startRecordingScreen(options)` / `stopRecordingScreen()` | iOS | Needs **ffmpeg** on the Appium host (`brew install ffmpeg`), no audio. Simulator since Xcode 9, real device since iOS 11. `timeLimit` default 180 s, maximum 4200 s. A start while a recording runs force-stops it and starts a new one |
| `mobile: startMediaProjectionRecording` / `stopMediaProjectionRecording` | Android **10+** | Needs the Appium Settings helper; records video and audio; no ffmpeg. `maxDurationSec` default 900; `resolution` one of `1920x1080`, `1280x720`, `720x480`, `320x240`, `176x144`; returns `false` if one is already running |
| `mobile: startXCTestScreenRecording` / `stopXCTestScreenRecording` | iOS **17+** (Xcode 15) | Native XCTest recording, the best quality at the lowest cost, no ffmpeg; `fps` default 24; the stop returns a base64 `.mov` in `payload`. On a real device, deleting the recording needs iOS 18+ and `appium-ios-remotexpc` 0.44+, or the `xctest_screen_record` insecure feature |

- WDIO 10's `stopRecordingScreen` takes **one options object** (`{ remotePath, method }` to upload); WDIO 9 took positional arguments.
- The stop call returns base64. A recording too large for the server's memory throws on stop; for long runs upload with `remotePath` instead.
- Parallel recordings need a unique `'appium:mjpegServerPort'` per session.
- `startRecordingScreen` is the asset's default because it works on every supported OS. Moving a project to a native mechanism is a change inside `beforeTest` and `afterTest`, and only there:

```ts
await browser.execute('mobile: startMediaProjectionRecording', { resolution: '1280x720', maxDurationSec: 600 });
const video = await browser.execute<string, [object]>('mobile: stopMediaProjectionRecording', {});
```

```ts
await browser.execute('mobile: startXCTestScreenRecording', { fps: 24 });
const { payload } = await browser.execute<{ payload: string }, [object]>('mobile: stopXCTestScreenRecording', {});
```

### 4.2 The pattern

1. **Start in the per-test setup** with `forceRestart: true`, so a recording left by a crashed test never leaks into this one.
2. **Stop in the teardown, always.** An unreleased recording blocks the next start.
3. **Keep the video only if the test failed.** Attach it to Allure and write it under `test-results/appium/<test title>/`; drop it otherwise.
4. Keep an Android test at or under 180 s unless ffmpeg is on the Appium host, or switch to `mobile: startMediaProjectionRecording`.
5. **On a device farm, do not record locally** (`DEVICE_FARM=1`).

## 5. Under Cucumber

A Cucumber run has no `afterTest`. The same capture runs in `afterScenario(world, result)` (and `beforeScenario` for the start); the scaffold's `After` hook already attaches the screenshot and page source to the scenario with `this.attach`, which is what the Cucumber report and Allure read. See `qa/typescript/skills/gherkin-step-code/references/cucumberjs-appium.md`.

## 6. Device farms

The vendor records the session, so the evidence is the **session URL and the pass/fail mark**, not a local file.

| Vendor | Video and logs | Mark the result |
|---|---|---|
| BrowserStack App Automate | Video on by default; disable with `'bstack:options': { video: 'false' }` | `browser.execute('browserstack_executor: {"action":"setSessionStatus","arguments":{"status":"failed","reason":"…"}}')`, or REST `PUT https://api-cloud.browserstack.com/app-automate/sessions/<id>.json`; the reason is at most 256 characters |
| Sauce Labs | `sauce:options` `recordScreenshots`, `recordLogs` | `browser.execute('sauce:job-result=failed')`, plus `sauce:job-name=…` |
| LambdaTest | Device log and network are capabilities | `browser.execute('lambda-status=failed')` (also `passed`, `skipped`, `ignored`, `unknown`, `error`) |
| AWS Device Farm | Artifacts per job, fetched with `ListArtifacts` | The run result |

The farm's capability names for device and network logs are unverified here. A WDIO vendor service for the project's WDIO major sets the status on its own; where none exists (`@wdio/browserstack-service` has no WDIO 10 build), the farm config's `afterTest` calls the executor, as `qa/typescript/skills/device-cloud` shows.

## 7. Exploratory capture by an agent (appium-mcp)

`qa-mobile-typescript` captures through the Appium MCP tools while it explores:

| Capture | Tool |
|---|---|
| Screenshot | `mcp__appium-mcp__appium_screenshot` — written to `SCREENSHOTS_DIR` |
| Page source | `mcp__appium-mcp__appium_get_page_source` |
| Recording | `mcp__appium-mcp__appium_screen_recording` — `action: start` then `stop`; the stop returns the MP4 path |

- `SCREENSHOTS_DIR` is an environment variable of the server registration. Without it the server writes to `os.tmpdir()`, so set it to `docs/app-map/screenshots` and the crawler's screenshots land in the repo.
- iOS recording needs ffmpeg on the machine running `appium-mcp`, the same limit as §4.1.
- Treat the returned recording path as the source: copy the file into `evidence/<YYYY-MM-DD>-<topic>/` when it is a receipt of what the agent did, and never into `test-results/`, which the next run clears.
- The screen-map screenshots under `docs/app-map/screenshots/` document the app and are committed only with the map; recordings are not.

## 8. Reading a failure

Before any edit, in this order:

1. `screenshot.png` — what the device showed.
2. `page-source.xml` — whether the element existed, under which attributes, in which context.
3. The log tail — a crash, an ANR, a permission denial or a native exception that the screen does not show.
4. `recording.mp4` — what happened leading up to it.

Then rerun the one test on the same device profile.

## 9. PII and retention

- A screenshot, page source, log or recording carries whatever the app showed: names, addresses, tokens in a log line. Tests run as disposable test users, never real accounts.
- `.gitignore` holds `test-results/`, `allure-results/` and `evidence/`.
- Retention follows `qa/cicd/ci-conventions`: 14 days, uploaded on failure only. The CI path is `test-results/appium/`.
