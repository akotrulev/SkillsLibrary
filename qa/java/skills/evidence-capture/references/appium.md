# Evidence capture — Appium 3 / java-client 11 (Java)

Every capture API for a native mobile run, with its limits. `SKILL.md` decides what a run keeps and where it lands; this file is how. The hook is `qa/java/skills/ui-test-author/appium/assets/BaseMobileTest.java`: its `@BeforeMethod` starts the recording and its `@AfterMethod(alwaysRun = true)` keeps the evidence, and no test adds another failure hook. `qa/reporting/java/skills/test-reports` defers to it for Appium. Every Allure call is allure-java 3.0: `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`. `Allure.addAttachment` is the 2.x API and does not exist in 3.0.

## 1. What a failed test keeps

| Evidence | API | File in `build/appium-artifacts/` | Allure type |
|---|---|---|---|
| Screenshot | `driver.getScreenshotAs(OutputType.BYTES)` | `<Class>.<method>.png` | `image/png` |
| Page source | `driver.getPageSource()` | `<Class>.<method>.xml` | `application/xml` |
| Device log tail (last 200 lines) | `driver.manage().logs().get("logcat").getAll()` on Android, `"syslog"` on iOS | `<Class>.<method>.log` | `text/plain` |
| Screen recording, kept only on failure | `startRecordingScreen` in `@BeforeMethod`, `stopRecordingScreen` in `@AfterMethod` | `<Class>.<method>.mp4` | `video/mp4` |

- A passing test keeps nothing; the recording is stopped and dropped.
- The status comes from `ITestResult.getStatus() == ITestResult.FAILURE`, read in the `@AfterMethod`. The relative order of Allure's own failure listener and the TestNG `@AfterMethod` is unverified; the hook attaches from the `@AfterMethod`, where allure-java 3.0 files the attachments under the test's tear-down fixture.
- Evidence must never mask the failure it documents. Each driver call runs through `fromDevice`, which catches one thing, a `WebDriverException` from the capture itself, logs `Could not capture <what>: <message>` with `System.Logger` and a message template, and goes on. File writes stay outside it, so an `IOException` fails the hook loudly. Anything else reaches TestNG untouched.
- The page source is the mobile twin of a DOM snapshot and the best locator-debugging artifact: a missing node there is an accessibility, app-state or context problem before it is a selector problem.
- A secure window (`FLAG_SECURE`) renders black in a screenshot or recording. That is the app, not the hook.

## 2. Screenshots

| Need | java-client 11 |
|---|---|
| The screen | `driver.getScreenshotAs(OutputType.BYTES)` (`AppiumRemoteWebDriver` is `TakesScreenshot`) |
| One element | `element.getScreenshotAs(OutputType.BYTES)` (`AppiumWebElement` is `TakesScreenshot`) |
| Every display, Android 10+ | `driver.executeScript("mobile: screenshots", Map.of())` → a map of `{ id, name, isDefault, payload }`; narrow with `displayId` from `mobile: listDisplays` |
| The iOS viewport without the status bar | `mobile: viewportScreenshot`; the driver docs mark it unreliable, so prefer `getScreenshotAs` |

The element route is `GET /element/:id/screenshot`; the old `/screenshot/:id` was removed in Appium 3. On iOS, coordinates read off a screenshot are pixels, and a tap takes points: divide by the device pixel ratio (2 or 3). The allure-testng listener takes no screenshots of its own, so the hook's attachment is the only one.

## 3. Page source and device logs

- `driver.manage().logs().getAvailableLogTypes()` lists what the device offers. Android: `logcat`, `bugreport`, `server`. iOS: `syslog`, `crashlog`, `performance`, `safariConsole`, `safariNetwork`, `server`.
- UiAutomator2 captures logcat by default. `appium:skipLogcatCapture` set to `true` turns that off and leaves nothing to read.
- `server` logs need the insecure feature on the Appium server, scoped in Appium 3: `--allow-insecure=uiautomator2:get_server_logs` (or `*:get_server_logs`). The unscoped form throws. The log routes moved from `/log` to `/se/log`; `manage().logs()` still works on java-client 11.
- A log is a list of `LogEntry` (`timestamp`, `level`, `message`); the hook keeps the tail, because a full logcat is large.
- Streaming is `startLogcatBroadcast()` with `addLogcatMessagesListener(Consumer<String>)` on `AndroidDriver`, and `startSyslogBroadcast()` on `IOSDriver`. The hook pulls the log instead.

## 4. Screen recording

### 4.1 Mechanisms and limits

| Mechanism | Platform | Limits |
|---|---|---|
| `startRecordingScreen(options)` / `stopRecordingScreen()` (`CanRecordScreen`) | Android (adb `screenrecord`) | **180 s per chunk.** `withTimeLimit` accepts 1–1800 s; above 180 s the driver records successive chunks and merges them with **ffmpeg on the Appium host**. Without ffmpeg on `PATH` the stop call fails with "ffmpeg utility is not available in PATH". `enableBugReport` needs API 27+ |
| `startRecordingScreen(options)` / `stopRecordingScreen()` | iOS | Needs **ffmpeg** on the Appium host (`brew install ffmpeg`), no audio. Simulator since Xcode 9, real device since iOS 11. The time limit defaults to 180 s, maximum 4200 s. A start while a recording runs force-stops it and starts a new one |
| `mobile: startMediaProjectionRecording` / `stopMediaProjectionRecording` | Android **10+** | Needs the Appium Settings helper; records video and audio; no ffmpeg. `maxDurationSec` default 900; `resolution` one of `1920x1080`, `1280x720`, `720x480`, `320x240`, `176x144`; returns `false` if one is already running |
| `mobile: startXCTestScreenRecording` / `stopXCTestScreenRecording` | iOS **17+** (Xcode 15) | Native XCTest recording, the best quality at the lowest cost, no ffmpeg; `fps` default 24; the stop returns a base64 `.mov` in `payload`. On a real device, deleting the recording needs iOS 18+ and `appium-ios-remotexpc` 0.44+, or the `xctest_screen_record` insecure feature |

- The options classes are `AndroidStartScreenRecordingOptions` (`withTimeLimit(Duration)`, `withBitRate`, `withVideoSize`, `enableBugReport`, `enableForcedRestart`, `withUploadOptions`) and `IOSStartScreenRecordingOptions` (`withVideoType`, `withVideoQuality`, `withFps`, `withVideoScale`, `withTimeLimit`). The stop options are `AndroidStopScreenRecordingOptions` and `IOSStopScreenRecordingOptions`, which carry the upload target (`remotePath`, `user`, `pass`, `method`).
- The stop call returns base64 as a `String`. A recording too large for the server's memory throws on stop; for long runs upload with `remotePath` instead.
- Parallel recordings need a unique `appium:mjpegServerPort` per session, which `parallel="classes"` makes a rule: one device and one set of ports per class.
- `startRecordingScreen` is the asset's default because it works on every supported OS. `BaseMobileTest` branches on the driver type with a pattern `switch`, since `AppiumDriver` itself is not a `CanRecordScreen`. Moving a project to a native mechanism is a change inside `startRecording` and `captureEvidence`, and only there:

```java
driver.executeScript("mobile: startMediaProjectionRecording", Map.of("resolution", "1280x720", "maxDurationSec", 600));
String video = (String) driver.executeScript("mobile: stopMediaProjectionRecording", Map.of());
```

```java
driver.executeScript("mobile: startXCTestScreenRecording", Map.of("fps", 24));
Map<?, ?> stopped = (Map<?, ?>) driver.executeScript("mobile: stopXCTestScreenRecording", Map.of());
String video = (String) stopped.get("payload");
```

### 4.2 The pattern

1. **Start in the per-test setup** with forced restart (Android `enableForcedRestart()`; iOS restarts on its own), so a recording left by a crashed test never leaks into this one.
2. **Stop in the teardown, always.** An unreleased recording blocks the next start.
3. **Keep the video only if the test failed.** Attach it to Allure and write it under `build/appium-artifacts/`; drop it otherwise.
4. Keep an Android test at or under 180 s unless ffmpeg is on the Appium host, or switch to `mobile: startMediaProjectionRecording`.
5. **On a device farm, do not record locally** (`DEVICE_FARM` set). The asset skips both calls.

## 5. Under Cucumber

A Cucumber run has no TestNG `@AfterMethod`. The scaffold's mobile hook (`qa/java/skills/bdd-project-scaffold/references/hooks.md` § Mobile hook) runs the same capture in `@After("@mobile")` and names the files `<feature file>.<scenario>` (D72), under the same `build/appium-artifacts/`.

## 6. Device farms

The vendor records the session, so the evidence is the **session URL and the pass/fail mark**, not a local file.

| Vendor | Video and logs | Mark the result |
|---|---|---|
| BrowserStack App Automate | Video on by default; disable with `bstack:options` `video` set to `"false"` | `((JavascriptExecutor) driver).executeScript("browserstack_executor: {\"action\":\"setSessionStatus\",\"arguments\":{\"status\":\"failed\",\"reason\":\"…\"}}")`, or REST `PUT https://api-cloud.browserstack.com/app-automate/sessions/<id>.json`; the reason is at most 256 characters |
| Sauce Labs | `sauce:options` `recordScreenshots`, `recordLogs` | `executeScript("sauce:job-result=failed")`, plus `sauce:job-name=…` |
| LambdaTest | Device log and network are capabilities | `executeScript("lambda-status=failed")` (also `passed`, `skipped`, `ignored`, `unknown`, `error`) |
| AWS Device Farm | Artifacts per job, fetched with `listArtifacts` | The run result |

`qa/java/skills/browser-cloud-setup` (`SessionStatus`) owns the three executor calls and attaches the dashboard URL with `Allure.attachment` in the same teardown. The farm's capability names for device and network logs are unverified here.

## 7. Exploratory capture by an agent (appium-mcp)

`qa-mobile-java` captures through the Appium MCP tools while it explores:

| Capture | Tool |
|---|---|
| Screenshot | `mcp__appium-mcp__appium_screenshot` — written to `SCREENSHOTS_DIR` |
| Page source | `mcp__appium-mcp__appium_get_page_source` |
| Recording | `mcp__appium-mcp__appium_screen_recording` — `action: start` then `stop`; the stop returns the MP4 path |

- `SCREENSHOTS_DIR` is an environment variable of the server registration. Without it the server writes to `os.tmpdir()`, so set it to `docs/app-map/screenshots` and the crawler's screenshots land in the repo.
- iOS recording needs ffmpeg on the machine running `appium-mcp`, the same limit as §4.1.
- Treat the returned recording path as the source: copy the file into `evidence/<YYYY-MM-DD>-<topic>/` when it is a receipt of what the agent did, and never into `build/`, which a clean removes.
- The screen-map screenshots under `docs/app-map/screenshots/` document the app and are committed only with the map; recordings are not.

## 8. Reading a failure

Before any edit, in this order:

1. `<Class>.<method>.png` — what the device showed.
2. `<Class>.<method>.xml` — whether the element existed, under which attributes, in which context.
3. The log tail — a crash, an ANR, a permission denial or a native exception that the screen does not show.
4. `<Class>.<method>.mp4` — what happened leading up to it.

Then rerun the one test on the same device profile.

## 9. PII and retention

- A screenshot, page source, log or recording carries whatever the app showed: names, addresses, tokens in a log line. Tests run as disposable test users, never real accounts.
- `.gitignore` holds `build/`, `allure-results/` and `evidence/`.
- Retention follows `qa/cicd/ci-conventions`: 14 days, uploaded on failure only. The CI path is `build/appium-artifacts/`.
