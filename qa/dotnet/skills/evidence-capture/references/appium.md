# Evidence capture — Appium 3 / Appium.WebDriver 9 (.NET / NUnit)

Every capture API for a native mobile run, in .NET spellings, with its limits. `SKILL.md` decides what a run keeps and where it lands; this file is how. The hook is `qa/dotnet/skills/ui-test-author/appium/assets/BaseMobileTest.cs`: its `[SetUp]` starts the recording and its `[TearDown]` keeps the evidence, and no test adds another failure hook. Attachments are the NUnit and Allure calls the Playwright side uses (`playwright.md` § 6): `TestContext.AddTestAttachment(path, name)` for the TRX and the IDE, and `AllureApi.AddAttachment(name, type, byte[] content, ".ext")` for Allure. **Three strings is a path**: `AllureApi.AddAttachment("page-source", "application/xml", xml)` treats `xml` as a file path and attaches nothing, so text goes in as bytes with its extension.

## 1. What a failed test keeps

| Evidence | API | File in `<WorkDirectory>/appium-artifacts/` | Allure type |
|---|---|---|---|
| Screenshot | `Driver.GetScreenshot().AsByteArray` | `<Class>.<Test>.png` | `image/png` |
| Page source | `Driver.PageSource` | `<Class>.<Test>.xml` | `application/xml` |
| Device log tail (last 200 lines) | `Driver.Manage().Logs.GetLog("logcat")` on Android, `"syslog"` on iOS | `<Class>.<Test>.log` | `text/plain` |
| Screen recording, kept only on failure | `StartRecordingScreen` in `[SetUp]`, `StopRecordingScreen` in `[TearDown]` | `<Class>.<Test>.mp4` | `video/mp4` |

- A passing test keeps nothing; the recording is stopped and dropped.
- `WorkDirectory` is NUnit's `TestContext.CurrentContext.WorkDirectory`, the test assembly's folder (`bin/<cfg>/net10.0`). CI uploads `AppiumTests/bin/<cfg>/net10.0/appium-artifacts/` (R7). The name is `<Class>.<Test>` with every character outside `[A-Za-z0-9._-]` replaced by `_`, so each `[TestCase]` row keeps its own files.
- "Failed" is `TestStatus.Failed`, read in the `[TearDown]`; it includes a failed `[SetUp]`.
- **There is no catch in the teardown**, the reasoning of plan D31 applied to NUnit: an unexpected exception in a capture reaches NUnit, which records a teardown error on that test only and runs the remaining teardowns. The hook stops the recording first and writes each file as soon as it is captured, so what was captured before a failure stays. The cost is that a dead session loses the evidence it could not give, and a host that cannot stop a recording (no `ffmpeg`, § 4.1) fails the teardown on every test, which is loud and is fixed on the host.
- The page source is the mobile twin of a DOM snapshot and the best locator-debugging artifact: a missing node there is an accessibility, app-state or context problem before it is a selector problem.
- A secure window (`FLAG_SECURE`) renders black in a screenshot or recording. That is the app, not the hook.

## 2. Screenshots

| Need | Appium.WebDriver 9 |
|---|---|
| The screen | `Driver.GetScreenshot()` → `.AsByteArray`, or `.SaveAsFile(path)` |
| One element | `((ITakesScreenshot)element).GetScreenshot()` |
| Every display, Android 10+ | `Driver.ExecuteScript("mobile: screenshots", new Dictionary<string, object>())` → `{ id, name, isDefault, payload }` per display; narrow with `displayId` from `mobile: listDisplays` |
| The iOS viewport without the status bar | `mobile: viewportScreenshot`; the driver docs mark it unreliable, so prefer `GetScreenshot` |

The element route is `GET /element/:id/screenshot`; the old `/screenshot/:id` was removed in Appium 3. On iOS, coordinates read off a screenshot are pixels and a tap takes points: divide by the device pixel ratio (2 or 3). `Allure.NUnit` takes no screenshots of its own, so the hook's attachment is the only one.

## 3. Page source and device logs

- `Driver.Manage().Logs.AvailableLogTypes` lists what the device offers. Android: `logcat`, `bugreport`, `server`. iOS: `syslog`, `crashlog`, `performance`, `safariConsole`, `safariNetwork`, `server`.
- UiAutomator2 captures logcat by default. `appium:skipLogcatCapture` set to `true` turns that off and leaves nothing to read.
- `server` logs need the insecure feature on the Appium server, scoped in Appium 3: `--allow-insecure=uiautomator2:get_server_logs` (or `*:get_server_logs`). The unscoped form throws. The log routes moved from `/log` to `/se/log`; the client's `Logs.GetLog` is the call, and whether it follows the new route on 9.0.0 is unverified here.
- A log is a list of `LogEntry` (`Timestamp`, `Level`, `Message`); the hook keeps the tail, because a full logcat is large.
- Streaming is `await androidDriver.StartLogcatBroadcast()` with `AddLogcatMessagesListener(Action<string>)` on `AndroidDriver`, and `await iosDriver.StartSyslogBroadcast()` with `AddSyslogMessagesListener` on `IOSDriver`. The hook pulls the log instead.

## 4. Screen recording

### 4.1 Mechanisms and limits

| Mechanism | Platform | Limits |
|---|---|---|
| `Driver.StartRecordingScreen(options)` / `StopRecordingScreen()` | Android (adb `screenrecord`) | **180 s per chunk.** `WithTimeLimit` accepts 1–1800 s; above 180 s the driver records successive chunks and merges them with **ffmpeg on the Appium host**. Without ffmpeg on `PATH` the stop call fails with "ffmpeg utility is not available in PATH". `EnableBugReport` needs API 27+ |
| `Driver.StartRecordingScreen(options)` / `StopRecordingScreen()` | iOS | Needs **ffmpeg** on the Appium host (`brew install ffmpeg`), no audio. Simulator since Xcode 9, real device since iOS 11. The time limit defaults to 180 s, maximum 4200 s. A start while a recording runs force-stops it and starts a new one |
| `mobile: startMediaProjectionRecording` / `stopMediaProjectionRecording` | Android **10+** | Needs the Appium Settings helper; records video and audio; no ffmpeg. `maxDurationSec` default 900; `resolution` one of `1920x1080`, `1280x720`, `720x480`, `320x240`, `176x144`; returns `false` if one is already running |
| `mobile: startXCTestScreenRecording` / `stopXCTestScreenRecording` | iOS **17+** (Xcode 15) | Native XCTest recording, the best quality at the lowest cost, no ffmpeg; `fps` default 24; the stop returns a base64 `.mov` in `payload`. On a real device, deleting the recording needs iOS 18+ and `appium-ios-remotexpc` 0.44+, or the `xctest_screen_record` insecure feature |

- The options classes are `AndroidStartScreenRecordingOptions.GetAndroidStartScreenRecordingOptions()` (`WithTimeLimit(TimeSpan)`, `WithBitRate`, `WithVideoSize`, `EnableBugReport`, `EnableForcedRestart`, `WithUploadOptions`) and `IOSStartScreenRecordingOptions.GetIosStartScreenRecordingOptions()` (`WithVideoType`, `WithVideoQuality`, `WithVideoFps(string)`, `WithVideoScale`, `WithPixelFormat`, `WithVideoFilter`, `WithTimeLimit`). `Android…` has `EnableForcedRestart()` and **no** `DisableForcedRestart()`. The stop options are `AndroidStopScreenRecordingOptions` and `IOSStopScreenRecordingOptions`, which carry the upload target.
- The stop call returns base64 as a `string`. A recording too large for the server's memory throws on stop; for long runs upload with a remote path instead.
- Parallel recordings need a unique `appium:mjpegServerPort` per session, which `ParallelScope.Self` makes a rule: one device and one set of ports per fixture.
- `StartRecordingScreen` is the asset's default because it works on every supported OS. `BaseMobileTest` branches on the driver type with a `switch`. Moving to a native mechanism is a change inside `BeginRecording` and `CaptureEvidence`, and only there:

```csharp
Driver.ExecuteScript("mobile: startMediaProjectionRecording", new Dictionary<string, object>
{
    ["resolution"] = "1280x720",
    ["maxDurationSec"] = 600,
});
var video = (string)Driver.ExecuteScript("mobile: stopMediaProjectionRecording", new Dictionary<string, object>());
```

```csharp
Driver.ExecuteScript("mobile: startXCTestScreenRecording", new Dictionary<string, object> { ["fps"] = 24 });
var stopped = (Dictionary<string, object>)Driver.ExecuteScript("mobile: stopXCTestScreenRecording", new Dictionary<string, object>());
var video = (string)stopped["payload"];
```

The return shape of the second call as the .NET client deserializes it is unverified here.

### 4.2 The pattern

1. **Start in the per-test setup** with forced restart (Android `EnableForcedRestart()`; iOS restarts on its own), so a recording left by a crashed test never leaks into this one.
2. **Stop in the teardown, always.** An unreleased recording blocks the next start. The hook stops it before it reads the test's outcome.
3. **Keep the video only if the test failed.** Attach it and write it under `appium-artifacts/`; drop it otherwise.
4. Keep an Android test at or under 180 s unless ffmpeg is on the Appium host, or switch to `mobile: startMediaProjectionRecording`.
5. **On a device farm, do not record locally** (`DEVICE_FARM` set). The hook skips both calls.

## 5. Under Reqnroll

A Reqnroll run has no NUnit `[TearDown]` on a binding. The scaffold's `[AfterScenario]` hook keeps the same files from `ScenarioContext.TestError`, named `<Feature>.<Scenario>` with the same character rule, under the same `appium-artifacts/` folder. Its code is `bdd-project-scaffold`'s; the teardown order and the no-catch rule apply to it unchanged.

## 6. Device farms

The vendor records the session, so the evidence is the **session URL and the pass/fail mark**, not a local file.

| Vendor | Video and logs | Mark the result |
|---|---|---|
| BrowserStack App Automate | Video on by default; disable with `bstack:options` `video` set to `"false"` | `((IJavaScriptExecutor)driver).ExecuteScript("browserstack_executor: {\"action\":\"setSessionStatus\",\"arguments\":{\"status\":\"failed\",\"reason\":\"…\"}}")`, or REST `PUT https://api-cloud.browserstack.com/app-automate/sessions/<id>.json`; the reason is at most 256 characters |
| Sauce Labs | `sauce:options` `recordScreenshots`, `recordLogs` | `ExecuteScript("sauce:job-result=failed")`, plus `sauce:job-name=…` |
| LambdaTest | Device log and network are capabilities | `ExecuteScript("lambda-status=failed")` (also `passed`, `skipped`, `ignored`, `unknown`, `error`) |

`qa/dotnet/skills/browser-cloud-setup` owns the executor calls and attaches the dashboard URL in the same teardown. The farms' capability names for device and network logs are unverified here. AWS Device Farm has no .NET Appium run type (`qa/dotnet/skills/device-cloud`), so it has no row.

## 7. Exploratory capture by an agent (appium-mcp)

`qa-mobile-dotnet` captures through the Appium MCP tools while it explores:

| Capture | Tool |
|---|---|
| Screenshot | `mcp__appium-mcp__appium_screenshot` — written to `SCREENSHOTS_DIR` |
| Page source | `mcp__appium-mcp__appium_get_page_source` |
| Recording | `mcp__appium-mcp__appium_screen_recording` — `action: start` then `stop`; the stop returns the MP4 path |

- `SCREENSHOTS_DIR` is an environment variable of the server registration. Without it the server writes to `os.tmpdir()`, so set it to `docs/app-map/screenshots` and the crawler's screenshots land in the repo.
- iOS recording needs ffmpeg on the machine running `appium-mcp`, the same limit as § 4.1.
- Treat the returned recording path as the source: copy the file into `evidence/<YYYY-MM-DD>-<topic>/` when it is a receipt of what the agent did, and never into `bin/`, which a clean removes.
- The screen-map screenshots under `docs/app-map/screenshots/` document the app and are committed only with the map; recordings are not.

## 8. Reading a failure

Before any edit, in this order:

1. The assertion message and stack in the `dotnet test` output, the TRX or Allure.
2. `<Class>.<Test>.png` — what the device showed.
3. `<Class>.<Test>.xml` — whether the element existed, under which attributes, in which context.
4. The log tail — a crash, an ANR, a permission denial or a native exception that the screen does not show.
5. `<Class>.<Test>.mp4` — what happened leading up to it.

Then rerun the one test on the same device profile.

## 9. PII and retention

- A screenshot, page source, log or recording carries whatever the app showed: names, addresses, tokens in a log line. Tests run as disposable test users, never real accounts.
- `.gitignore` holds `bin/`, `obj/`, `allure-results/` and `evidence/`.
- Retention follows `qa/cicd/ci-conventions`: 14 days, uploaded on failure only. The CI path is `AppiumTests/bin/<cfg>/net10.0/appium-artifacts/`.
