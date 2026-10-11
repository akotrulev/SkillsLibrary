# Maestro research: CLI, flow syntax, selectors, outputs, CI, MCP (as of 2026-10-11)

Method: pages fetched on 2026-10-11 from the official docs (`docs.maestro.dev`, which serves each page as `.md`), the `mobile-dev-inc/Maestro` GitHub releases page, `CHANGELOG.md` and one source file, and the Expo docs. A claim without a primary source is marked **UNVERIFIED**. Plan 003's earlier research did not cover Maestro; this file is the only fact source for `ui-test-author/maestro`.

---

## 0. Headline findings

- **Current CLI is 2.11.0** (marked Latest on the releases page; listed as 29 Sep, the page shows no year, so the year is UNVERIFIED, though 2.10.0 is 31 Aug and 2.9.0 is 26 Aug).
- **`id:` is the Android resource id and the iOS `accessibilityIdentifier`.** Maestro's own React Native page says "the best practice is to use the `testID` property, which Maestro maps to a unique `id`." That agrees with plan 002 §8.5 and M1's D80 (an RN `testID` is the bare Android resource-id). `text` and `id` are **regex-based**.
- **An official MCP server ships in the CLI**: `maestro mcp`, stdio, nine tools (§9).
- **`maestro check-syntax <file>` exists** in the source and changelog but is **not in the docs' CLI reference**. It prints `OK` on success. This is the syntax check G1 §6.3 may use (§10).
- **`assertVisible` and `assertNotVisible` already wait up to 7 s.** A fixed sleep is never needed; `extendedWaitUntil` covers longer waits.
- **EAS Workflows has a `maestro` job type**, marked alpha in Expo's docs. The Android emulator needs a `linux-*-nested-virtualization` worker.
- Maestro's docs have **no GitHub Actions recipe for a local emulator**: the GitHub Actions page covers Maestro Cloud only. The emulator job in the skill is assembled from two primary sources (§8).

---

## 1. Version and install

| Fact | Value | Source |
|---|---|---|
| Latest CLI | 2.11.0 (Latest), then 2.10.0, 2.9.0, 2.8.0, 2.7.0 | https://github.com/mobile-dev-inc/Maestro/releases |
| Changelog carries no dates | `## 2.11.0`, `## 2.10.0` headings only | https://raw.githubusercontent.com/mobile-dev-inc/Maestro/main/CHANGELOG.md |
| Java | "Java version 17 or higher"; `JAVA_HOME` must point at it | https://docs.maestro.dev/maestro-cli/how-to-install-maestro-cli.md |
| macOS / Linux install | `curl -fsSL "https://get.maestro.mobile.dev" \| bash` | same |
| macOS Homebrew | `brew tap mobile-dev-inc/tap`, `brew trust --formula mobile-dev-inc/tap/maestro`, `brew install mobile-dev-inc/tap/maestro` | same |
| Windows | download `maestro.zip` from the GitHub release, extract, add `bin` to `PATH` | same |
| Version check | the install page says `maestro --help`; the CLI reference lists `-v`, `--version` | same; https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options.md |
| Pin a version / upgrade | not on the install page; it links "Update the Maestro CLI" | https://docs.maestro.dev/maestro-cli/how-to-install-maestro-cli/update-the-maestro-cli.md (not read; version pinning in a script is UNVERIFIED) |
| Env vars the CLI reads | `MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED`, `MAESTRO_CLI_LOG_PATTERN_CONSOLE`, `MAESTRO_CLI_LOG_PATTERN_FILE`, `MAESTRO_CLI_NO_ANALYTICS`, `MAESTRO_CLOUD_API_KEY`, `MAESTRO_DISABLE_UPDATE_CHECK`, `MAESTRO_DRIVER_STARTUP_TIMEOUT` | https://docs.maestro.dev/maestro-cli/environment-variables.md |
| Driver startup timeout defaults | 15000 ms Android, 120000 ms iOS | https://docs.maestro.dev/maestro-cloud/ci-cd-integration/generic-ci-platform.md |

CLI subcommands: `bugreport`, `cloud`, `download-samples`, `driver-setup`, `list-cloud-devices`, `list-devices`, `login`, `logout`, `mcp`, `record`, `start-device`, `test`. Global options: `--udid`/`--device`, `-p`/`--platform`, `--verbose`, `--[no-]ansi`. Source: https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options.md. The CLI page also names `maestro hierarchy` (prints the view hierarchy): https://docs.maestro.dev/maestro-cli/

`maestro test` options: `--config`, `-c`/`--continuous`, `--debug-output`, `-e`/`--env`, `--exclude-tags`, `--include-tags`, `--flatten-debug-output`, `--format` (`JUNIT`, `HTML`, `NOOP`; default `NOOP`), `--output`, `-s`/`--shards`, `--shard-all`, `--shard-split`, `--test-output-dir`, `--test-suite-name`, `--analyze` (beta), and `<flowFiles>...` ("one or more flow files or folders"). Source: the CLI reference above.

---

## 2. Flow syntax and the core commands

A flow file is YAML in two parts: a configuration block, `---`, then the commands. The header holds `appId`, `tags`, `env`, `onFlowStart`, `onFlowComplete` (sources in §5, §6, §7 below). The 48 commands are listed at https://docs.maestro.dev/reference/commands-available.md; each of the twelve the plan names exists there.

| Command | Verified syntax and behaviour | Source |
|---|---|---|
| `launchApp` | `- launchApp`, or a map with `appId`, `clearState` (clears state before launch), `clearKeychain` (iOS), `stopApp` (default `true`), `permissions` (all allowed by default; `all: deny`), `arguments` (string, boolean, double, integer). `appId` omitted means the header's `appId` | https://docs.maestro.dev/reference/commands-available/launchapp.md |
| `tapOn` | `- tapOn: "text"`; map with `id`, `point` (`"50%,50%"` or `"100,200"`), `repeat` + `delay` (ms, default 100), `retryTapIfNoChange`, `waitToSettleTimeoutMs`. `longPressOn` takes the same selectors | https://docs.maestro.dev/reference/commands-available/tapon.md |
| `inputText` | `- inputText: "John"`, shown after tapping the field. Focused-field behaviour is not stated on the page: UNVERIFIED | same page |
| `assertVisible` | A string is shorthand for `text`; a map takes `text`, `id`, `enabled`, `checked`, `focused`, `selected`. **Retries up to 7 s** before failing | https://docs.maestro.dev/reference/commands-available/assertvisible.md |
| `assertNotVisible` | "Confirms an element is absent or hidden"; the same 7 s default timeout | https://docs.maestro.dev/reference/commands-available/extendedwaituntil.md |
| `scrollUntilVisible` | `element` (string or selector; required), `direction` (`DOWN` default), `timeout` (ms, default 20000), `speed` (0-100, default 40), `visibilityPercentage` (default 100), `centerElement` (default false) | https://docs.maestro.dev/reference/commands-available/scrolluntilvisible.md |
| `extendedWaitUntil` | `visible:` or `notVisible:` plus `timeout` in **milliseconds** | https://docs.maestro.dev/reference/commands-available/extendedwaituntil.md |
| `runFlow` | `- runFlow: Login.yaml`, or `file:` + `env:`, or inline `commands:` (also with `env:`), plus `label`, plus `when:` (§6). Path is "relative to the Flow file" | https://docs.maestro.dev/reference/commands-available/runflow.md |
| `runScript` | `- runScript: myScript.js`, or `file:` + `env:`; the script sets `output.x`, a later command reads `${output.x}`; the path "can be absolute or relative to the flow file" | https://docs.maestro.dev/reference/commands-available/runscript.md |
| `evalScript` | Inline JavaScript: `- evalScript: ${output.apiKey = MAESTRO_API_KEY}` | https://docs.maestro.dev/maestro-flows/flow-control-and-logic/parameters-and-constants.md |
| `takeScreenshot` | `- takeScreenshot: MainScreen` or `path`, `cropOn`, `label`. Saved as PNG, so `LoginScreen` becomes `LoginScreen.png`, in the `takeScreenshot` folder of the flow's artifact bundle; the path cannot contain `..` | https://docs.maestro.dev/reference/commands-available/takescreenshot.md |
| `startRecording` / `stopRecording` | `- startRecording: recording` writes `recording.mp4`; `stopRecording` has no parameters and "must be called to finalize the video". Output lands in the `startRecording` folder of the artifact bundle | https://docs.maestro.dev/reference/commands-available/startrecording.md |
| `clearState` | `- clearState` or `- clearState: app.id`. Android is `adb shell pm clear <package>`; iOS reinstalls the app; web clears the origin's cookies and local storage. Simulator-only and keychain behaviour are not on the page: UNVERIFIED | https://docs.maestro.dev/reference/commands-available/clearstate.md |
| `waitForAnimationToEnd` | `timeout` in ms | https://docs.maestro.dev/maestro-flows/flow-control-and-logic/wait-commands.md |
| `openLink` | Opens a URL or deep link. With Expo Go use `- openLink: exp://127.0.0.1:19000`, not `launchApp` | https://docs.maestro.dev/reference/commands-available.md; https://docs.maestro.dev/get-started/supported-platform/react-native.md |
| `retry`, `repeat`, `back`, `pressKey`, `hideKeyboard`, `setPermissions`, `setLocation`, `addMedia` | Exist; parameters not read | https://docs.maestro.dev/reference/commands-available.md |

Hooks, in the header above `---`: `onFlowStart: { runFlow: subflows/login.yaml }` and `onFlowComplete: { runFlow: ... }`. If `onFlowStart` fails the flow is Failed, the body is skipped, and `onFlowComplete` still runs. A hook that calls a flow triggering the same hook can loop forever. Source: https://docs.maestro.dev/maestro-flows/flow-control-and-logic/hooks.md

---

## 3. How `id:` reaches a React Native `testID`

| Fact | Source |
|---|---|
| `id` on Android "Maps to the Resource ID"; on iOS "Maps to the `accessibilityIdentifier`" | https://docs.maestro.dev/reference/selectors/core-selectors.md |
| "`text` and `id` are regex-based"; escape `$` and `[` with a backslash. A `.` in an id is a regex wildcard that also matches itself, so `Login.Submit` matches the literal id | same page |
| `index` is 0-based and picks among several matches | same page |
| React Native: "the best practice is to use the `testID` property, which Maestro maps to a unique `id`"; example `<TextInput testID="username_input" />` with `- tapOn: { id: "username_input" }` | https://docs.maestro.dev/get-started/supported-platform/react-native.md |
| Compose needs `Modifier.semantics { testTagsAsResourceId = true }` for tags to be ids | core-selectors page |
| `id` suits "dynamic content, icons without text, or localized apps" | core-selectors page |
| Expo Go: no `launchApp` with a custom `appId`; EAS builds and standalone apps use `launchApp` with the bundle id or package name | react-native page |
| iOS: nested React Native components can swallow touches; set `accessible={false}` on the wrapper and `accessible={true}` on the inner control | react-native page |

Reading against plan 002 §8.5 and M1's D80: an RN `testID` is the bare `resource-id` on Android and the `accessibilityIdentifier` on iOS, and Maestro's `id:` matches those same two attributes, so **one `id: Login.Submit` serves both platforms** and the PascalCase dot-separated ids from `mobile-react-native-test-ids` work unchanged. Whether Maestro's Android `id` also matches a package-prefixed resource-id such as `com.app:id/x`: UNVERIFIED; the contract never needs it because RN ids carry no prefix. The accessibility label is a different attribute and is never an id.

---

## 4. Waiting without sleeps

- "If you expect an element to appear or disappear within a short period, use an assertion." Assertions "poll the UI continuously until the element appears or the timer expires" (default 7 s).
- `extendedWaitUntil` is for slow operations; "Maestro moves on immediately if the element appears faster than the timeout." Example: `visible: "Payment Confirmed"`, `timeout: 30000`.
- `waitForAnimationToEnd` with `timeout: 5000` prevents missed taps.
- "Avoid setting every timeout to 60 seconds."
- No fixed-sleep command appears in the 48-command list. A sleep through `evalScript` or JavaScript is UNVERIFIED and not taught.

Source for the four points: https://docs.maestro.dev/maestro-flows/flow-control-and-logic/wait-commands.md; the command list is https://docs.maestro.dev/reference/commands-available.md

---

## 5. Env, parameters and constants

- `maestro test -e USERNAME=user@example.com -e PASSWORD=secret flow.yaml`; "CLI parameters are passed as strings".
- `${VARIABLE_NAME}` in the flow; names are case-sensitive.
- A header `env:` block holds constants. `${USERNAME || "guest"}` gives a default, and a subflow header can say `USER_ID: ${USER_ID || "test_user_1"}`.
- Shell variables with the `MAESTRO_` prefix are readable in flows with the CLI (not Studio): `export MAESTRO_API_KEY=...`, then `${output.apiKey = MAESTRO_API_KEY}` in `evalScript`.
- `runFlow` `env:` and `runScript` `env:` pass values down.

Source: https://docs.maestro.dev/maestro-flows/flow-control-and-logic/parameters-and-constants.md

---

## 6. Tags, discovery, `config.yaml`, conditions

| Fact | Source |
|---|---|
| Tags: a `tags:` list in the header, above `---` | https://docs.maestro.dev/maestro-flows/workspace-management/test-discovery-and-tags.md |
| Within one flag the tags are OR; `--include-tags` AND `--exclude-tags` applies include, then removes excluded | same |
| `maestro test .` runs only flows at the folder's top level; subfolders are ignored "to prevent accidental execution of nested or utility Flows" | same |
| `config.yaml` `flows:` globs: default `*` (root only), `**` recursive, `!` excludes, at least one positive pattern required | same; https://docs.maestro.dev/reference/workspace-configuration.md |
| `config.yaml` keys: `flows`, `includeTags`, `excludeTags`, `executionOrder` (`continueOnFailure` default true, `flowsOrder`), `testOutputDir` (default `~/.maestro/tests/`), `platform.ios.snapshotKeyHonorModalViews`, `platform.{ios,android}.disableAnimations` (Cloud only), `baselineBranch` and `notifications` (Cloud only) | https://docs.maestro.dev/reference/workspace-configuration.md |
| `maestro record` reads `config.yaml` from the root directory by default | https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options.md |
| `when:` on `runFlow`: `visible`, `notVisible`, `platform` (`Android`, `iOS`, `Web`), `true: ${js}`; several keys are AND | https://docs.maestro.dev/maestro-flows/flow-control-and-logic/conditions.md |
| Whether a top-level `appId` in `config.yaml` applies to every flow: the example shows it but the keys page does not describe it, so UNVERIFIED | the two pages above |

---

## 7. Outputs

| Fact | Source |
|---|---|
| JUnit: `maestro test --format junit`; `--output <path>` sets the file, default `report.xml` in the current directory. HTML: `--format html` (failed-step screenshots) or `html-detailed` | https://docs.maestro.dev/maestro-flows/workspace-management/test-reports-and-artifacts.md |
| Reports come only from the CLI flags, not from `config.yaml`; JUnit is **not** written into `--test-output-dir` or `--debug-output` | same |
| Default output: `~/.maestro/tests` (macOS, Linux). Overridden by `--test-output-dir` (wins) or `testOutputDir` | same |
| Per session: a timestamped folder with `maestro.log`; per flow: a subfolder with `manifest.json`, `commands.json`, `logs/`, and when present `screenshots/`, `screen-hierarchy/`, `takeScreenshot/`, `startRecording/`, `ai-analysis/` | same |
| On failure: a screenshot of the failing step plus its view-hierarchy JSON; a passing flow has no `screenshots/` folder | same |
| `logs/` holds `device-logcat.txt` on Android, `device-simulator.log` and `device-xctest.log` on iOS, `crash-report.txt` on a crash, `anr-report.txt` on an Android ANR | same |
| A recording exists only when the flow runs `startRecording` | same |
| `--debug-output` alone moves only `maestro.log`; `--test-output-dir` alone moves screenshots, video and `commands.json` | same |
| `--flatten-debug-output` is documented in the CLI reference ("without subfolders or timestamps for each run"); its behaviour beyond that is UNVERIFIED | CLI reference |
| JUnit attributes: a `file` attribute (2.6.0), configurable `id` and `classname` (2.6.0), `timestamp` truncated to whole seconds (2.8.0), tags and custom properties in reports (2.1.0, 2.2.0) | https://raw.githubusercontent.com/mobile-dev-inc/Maestro/main/CHANGELOG.md |
| `maestro record` stitches screen recordings and test output into an MP4 | https://docs.maestro.dev/maestro-cli/ |

---

## 8. CI

| Route | Facts | Source |
|---|---|---|
| **EAS Workflows** | `type: maestro`, marked **alpha**. `params`: `build_id` (required), `flow_path` (string or list, required), `shards`, `retries` (default 0), `retry_failed_only` (default true), `record_screen` (default false), `include_tags`, `exclude_tags`, `maestro_version`, `android_system_image_package` (an `x86_64` variant), `device_identifier`, `output_format` (default `junit`), `skip_build_check`. Top level: `environment` (default `preview`), `image`, `runs_on` (a `linux-*-nested-virtualization` worker for Android). Hooks `after_checkout`, `before_maestro_tests`, `after_maestro_tests`. No outputs | https://raw.githubusercontent.com/expo/expo/refs/heads/main/docs/pages/eas/workflows/pre-packaged-jobs.mdx |
| EAS example | `.maestro/` beside `eas.json`; an `e2e-test` build profile with `withoutCredentials: true`, `ios.simulator: true`, `android.buildType: "apk"`; a build job, then a `maestro` job that `needs` it with `build_id` from the build's outputs and `flow_path` as a list of flow files; run by hand with `eas workflow:run .eas/workflows/e2e-test-android.yml` | https://docs.expo.dev/eas/workflows/examples/e2e-tests/ |
| **Maestro Cloud** | `maestro cloud --api-key ... --project-id ... --app-file <apk or app> --flows ./e2e`; pass the workspace folder, not one file. GitHub Action `mobile-dev-inc/action-maestro-cloud@v2.0.2` with `api-key`, `project-id`, `app-file` | https://docs.maestro.dev/maestro-cloud/ci-cd-integration/generic-ci-platform.md; https://docs.maestro.dev/maestro-cloud/ci-cd-integration/github-actions.md; https://docs.maestro.dev/reference/commands-available/runflow.md (the workspace-folder note) |
| **GitHub Actions emulator job** | Not documented by Maestro. Assembled from: the KVM udev step and `reactivecircus/android-emulator-runner@v2` with `api-level`, `arch: x86_64`, `script` (README example), and Maestro's own install line. The assembled job is **UNVERIFIED as a whole**; no source runs `maestro test` inside it | https://github.com/ReactiveCircus/android-emulator-runner; https://docs.maestro.dev/maestro-cli/how-to-install-maestro-cli.md |
| iOS on GitHub Actions | A macOS runner is needed for a Simulator. One third-party guide says so; no primary source: UNVERIFIED | |

---

## 9. Maestro Studio and the MCP server

**Studio.** "The desktop app for writing, running, and debugging mobile UI tests visually": right-clicking an element on a connected device adds YAML commands, every run is recorded, flows run step by step. The overview page gives no launch command and no save-flow detail. https://docs.maestro.dev/maestro-studio/maestro-studio-overview.md · "Run Locally" pastes YAML into the editor: https://docs.maestro.dev/get-started/quickstart.md

**MCP: official, ships in the CLI.** https://docs.maestro.dev/get-started/maestro-mcp.md

- Start: `maestro mcp`, stdio. Register: `claude mcp add maestro -- maestro mcp` (Claude Code); the JSON form is `{"mcpServers":{"maestro":{"command":"maestro","args":["mcp"]}}}`. The page never uses the word "official", but it is Maestro's own documentation and the server is a CLI subcommand (the changelog 1.41.0: "Added Maestro MCP server implementation to cli").
- Tools: `list_devices`, `inspect_screen` (the view hierarchy as compact JSON), `take_screenshot`, `run`, `cheat_sheet`, `list_cloud_devices`, `run_on_cloud`, `get_cloud_run_status`, `open_maestro_viewer`.
- `run` "validates syntax as part of the call" and takes **exactly one** of `{ yaml }`, `{ files }` or `{ dir, include_tags, exclude_tags }`.
- The three cloud tools need `maestro login` or `MAESTRO_CLOUD_API_KEY`.
- The changelog names a tenth tool, `describe_cloud_run` (2.7.0), that the docs page does not list. Not granted. Source: https://raw.githubusercontent.com/mobile-dev-inc/Maestro/main/CHANGELOG.md
- Parameter lists beyond `run` are not on the page: UNVERIFIED.

---

## 10. Syntax check

- **`maestro check-syntax <flow file>`** exists. Changelog 1.40.0: "Introduced `maestro check-syntax` command for validating flow syntax"; 2.2.0: "Show `maestro hierarchy` and `maestro check-syntax` commands in `maestro --help`". Source (`CheckSyntaxCommand.kt`): one positional flow path, `-` reads stdin; a missing file or empty input is an error; success prints `OK`, a syntax error becomes a CLI error with the message. Exit codes for the error case are not defined in the file: UNVERIFIED. https://raw.githubusercontent.com/mobile-dev-inc/Maestro/main/maestro-cli/src/main/java/maestro/cli/command/CheckSyntaxCommand.kt
- It is **absent from the docs' CLI reference** (https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options.md), so `maestro --help` is the way to confirm it on an installed version.
- No dry-run flag on `maestro test` appears in the CLI reference. The MCP `run` tool validates syntax but runs the flow, so it is not a dry run.
- A flow with a `---` header is a multi-document YAML file; whether `check-syntax` accepts a subflow that has no `appId`: UNVERIFIED.

---

## 11. Unverified, and not taught

- The 2.11.0 release year; pinning a CLI version in CI.
- `inputText` focus behaviour; `clearState` on a physical iOS device and the keychain.
- Whether `id` matches a package-prefixed Android resource id.
- Whether `appId` in `config.yaml` applies to every flow.
- A working end-to-end `android-emulator-runner` + `maestro test` job; an iOS Simulator job on GitHub Actions.
- A sleep or fixed-wait command.
