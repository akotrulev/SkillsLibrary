---
name: qa-ui-test-writer-maestro-typescript
description: Use when a project runs Maestro for mobile E2E (typically Expo / React Native) and a flow, subflow or `.maestro/` workspace must be written, tagged, run in CI or reviewed. Triggers "write a Maestro flow for X", "add a subflow", "run Maestro in EAS Workflows", "Maestro JUnit report". Do NOT use for Appium/WebdriverIO tests (`qa-ui-test-writer-appium-typescript`), web UI (`qa-ui-test-writer-playwright-typescript`) or live-screen discovery (`qa-mobile-screen-explorer-typescript`).
---

# QA — Maestro Flow Author (TypeScript lane)

Writes Maestro flows: declarative YAML that drives a native or React Native app through its accessibility layer, one file per journey, with subflows as the page-object analogue. There is no TypeScript in a flow; the lane lives in `qa-mobile-typescript` beside Appium because the same agent, test ids and evidence rules apply. Every fact here comes from `docs/research/003-qa-playwright-appium/maestro.md`; anything it marks UNVERIFIED is not taught.

## Versions

| Artifact | Primary | Notes |
|---|---|---|
| Maestro CLI | **2.11.0** | Needs Java 17+ (`JAVA_HOME` set). Install: `curl -fsSL "https://get.maestro.mobile.dev" \| bash`, or Homebrew `mobile-dev-inc/tap/maestro` |
| EAS Workflows `maestro` job | alpha | Expo's docs mark it alpha; `maestro_version` pins the CLI there |

- Detect first: `maestro --version`, a `.maestro/` folder, `type: maestro` in `.eas/workflows/`. Keep what the project has.

## Maestro or Appium

| | Maestro | Appium + WebdriverIO |
|---|---|---|
| A test is | A YAML flow | A Mocha spec over screen objects |
| One selector for both platforms | Yes: `id:` is the Android resource-id and the iOS `accessibilityIdentifier` | No: `~id` on iOS, `id=` on Android |
| Waiting | Assertions poll for 7 s; `extendedWaitUntil` for longer | `waitForDisplayed`, `waitUntil` |
| Logic | `when:`, `evalScript`, `runScript`, `retry`, `repeat` | Full TypeScript |
| Reuse | Subflows, `runFlow` | Classes, components |
| Choose it when | The project already has `.maestro/`, or an Expo team runs EAS Workflows | The suite needs code, WebView context switching, a device farm or Allure through WDIO |

One tool per project. Never mix both runners in one suite; a project that needs both keeps two folders and two pipelines.

## When to use

- A flow, a subflow, a `config.yaml` or a tag change under `.maestro/`
- A Maestro step in EAS Workflows or a CI job, and its JUnit report
- Reviewing a Maestro workspace

## When NOT to use

- Appium / WebdriverIO → `qa/typescript/skills/ui-test-author/appium`
- Web UI → `qa/typescript/skills/ui-test-author/playwright`
- Finding the ids on a live screen → `qa/typescript/skills/mobile-screen-explorer`
- Adding `testID` to the app → the `mobile-react-native-test-ids` dev skill, through `missing-testids.md`

## The layout

```
.maestro/
  config.yaml
  Should_ShowOrderTitle_When_OrderIsInHistory.yaml
  subflows/
    SignIn.yaml
```

`assets/.maestro/` is the compilable reference; copy it, do not retype it.

- **One flow per journey**, named `Should_X_When_Y.yaml`. The file name is the flow's name in the report.
- **Flows sit at the workspace root; subflows sit in `subflows/`.** `maestro test .maestro` runs only top-level flows, and subfolders are ignored "to prevent accidental execution of nested or utility Flows". `config.yaml` `flows:` defaults to `*` (the root only). Never add `**` without a `!subflows/**` line.
- **A subflow is a screen's actions.** `SignIn.yaml` is the page-object analogue: it opens with an assertion on a landmark (`Login.Submit`), runs the actions, and ends on the next screen's landmark (`Orders.List`). Flows call it with `runFlow`, so a UI change is one edit.
- **A subflow takes its values explicitly**: `runFlow: { file, env }`. Do not rely on a subflow reading the caller's variables (UNVERIFIED).
- **The header** (above `---`) holds `appId`, `tags`, `env`. Each file repeats `appId`; the value comes from the build (`com.example.shop` is a placeholder).
- Inline `commands:` under `runFlow` is for a short conditional block; a repeated sequence is a subflow file.

## Selectors

Maestro matches the accessibility layer, so the plan 002 test-id contract holds: React Native `testID` is the Android `resource-id` and the iOS `accessibilityIdentifier`, and `id:` matches both. Ids are PascalCase and dot-separated (`Login.Submit`, `OrderRow.Title`), static, and never the accessibility label.

| Rung | Syntax | Use |
|---|---|---|
| 1 — the test id | `id: Login.Submit` | Everything the app tags |
| 2 — visible text | `text: "Continue"` or the shorthand `"Continue"` | A system dialog, a third-party screen, an element the app has not tagged yet |
| 3 — a coordinate | `point: "50%,50%"` | Never |

- **`id` and `text` are regular expressions.** A `.` in `Login.Submit` matches itself (and any character), so the id still finds its element. Escape `$` and `[` with a backslash; PascalCase ids carry neither.
- **Repeating rows share one static id.** Pick the row by combining properties, `id: OrderRow.Title` with `text: ${ORDER_TITLE}`; never an id with the data in it. `index:` is 0-based and positional: allowed only for a list whose order the test sets up and the name says so.
- Every rung-2 selector where a test id should exist is a row in `missing-testids.md` (flow, element, text in use). The flow carries no marker.
- Prefer `id` for localized apps. A text selector breaks when copy or language changes.
- Expo Go has no custom `appId`: reach the app with `openLink: exp://…`. A development or EAS build uses `launchApp`.
- An iOS tap swallowed by a nested React Native wrapper is an app fix (`accessible={false}` on the wrapper); record it, never use a coordinate.
- Discover ids with `maestro hierarchy` or the MCP `inspect_screen`, never by guessing.

## Waits

- **Never a fixed pause.** The 48 commands have no sleep, and a flow does not simulate one.
- `assertVisible` and `assertNotVisible` retry up to **7 s**. Put the assertion right after the action: `- tapOn: { id: Login.Submit }`, then `- assertVisible: { id: Orders.List }`.
- A slow operation: `extendedWaitUntil` with `visible:` or `notVisible:` and a `timeout` in **milliseconds**. Maestro moves on the moment the element appears. Do not give every wait 60 s.
- A moving screen: `waitForAnimationToEnd` with a `timeout`.
- A list item below the fold: `scrollUntilVisible` with `element:` (an object selector), `direction` (default `DOWN`), `timeout` (default 20000 ms).
- An optional element (a banner that may or may not show): `runFlow` with `when: { visible: … }`. The condition is the wait; do not guess with a sleep.

## Test data, env and tags

- **Values from the CLI**: `maestro test -e E2E_USER=… -e E2E_PASSWORD=… .maestro`. They arrive as strings and are read as `${E2E_USER}`; names are case-sensitive. Shell variables that start with `MAESTRO_` are readable in flows with the CLI.
- **Never a credential or a real account in a flow or in `config.yaml`**: pass it with `-e` or the CI secret store, and use a disposable test user.
- **Defaults in the header**: `env:` with `${NAME || "default"}` for a non-secret value a flow can run without.
- **Data the flow needs is created by the test, not assumed**: seed through the API (`runScript` with a JavaScript file, or the project's seeding script before the run), and name the seeded value in `env`. A `runScript` returns values through `output.x`, read as `${output.x}`.
- **Reset between flows.** A journey that depends on logged-out state starts with `launchApp` and `clearState: true` (Android clears app data; iOS reinstalls). A flow never relies on the flow before it. Flows are independent and runnable alone, in any order.
- **Tags** go in the header: `tags: [smoke, orders]`. `--include-tags` and `--exclude-tags` take lists: tags inside one flag are OR, and include-then-exclude is AND. Every flow carries at least one tag (`smoke`, `regression`) and a flaky one is `quarantine`, which `config.yaml` excludes (`excludeTags`).
- **`config.yaml`**: `flows` (globs, `!` excludes), `includeTags`, `excludeTags`, `executionOrder` (only when a suite must run in a fixed order, and then it needs a written reason), `testOutputDir`.
- **Hooks**: `onFlowStart` / `onFlowComplete` run a `runFlow` before and after the body; a failed start still runs the complete hook. A hook never calls a flow that carries the same hook.

## Evidence

| What | How | Lands in |
|---|---|---|
| A screenshot of the failing step | Automatic, with the step's view-hierarchy JSON | `<testOutputDir>/<session>/<flow>/screenshots/`, `screen-hierarchy/` |
| Step status, duration, errors | Automatic | `commands.json` and `manifest.json` in the flow folder; `maestro.log` per session |
| Device log | Automatic | `logs/device-logcat.txt` (Android); `device-simulator.log`, `device-xctest.log` (iOS); `crash-report.txt`; `anr-report.txt` on Android |
| A deliberate screenshot | `- takeScreenshot: orders/OrderHistory` (a name without extension, saved as PNG) | `takeScreenshot/` in the flow folder |
| A recording | `- startRecording: orders` … `- stopRecording` | `startRecording/` in the flow folder, as `.mp4` |
| The JUnit report | `--format junit --output <file>` | the file; **not** in the test-output dir |

- The default output dir is `~/.maestro/tests`. Set `--test-output-dir test-results/maestro` on the command line (it wins over `testOutputDir` in `config.yaml`), so CI uploads one folder. `--debug-output` moves only `maestro.log`.
- A passing flow has no `screenshots/` folder. A recording exists only where the flow runs `startRecording`; keep it for a journey that is being debugged, and end it with `stopRecording` or the file is not finalized.
- `takeScreenshot` and `startRecording` paths must name a file and never contain `..`. An undefined variable in a path writes `undefined.png`, not an error.
- **Read a failure in this order**: the flow's `commands.json` (the failed step and its error), the failure screenshot, `screen-hierarchy/` (is the id on screen?), then `logs/`.
- Nothing captured is committed: `.gitignore` holds `test-results/`. A recording shows real screens, so the account is disposable.

## Running and CI

```bash
mkdir -p test-results
maestro test --format junit --output test-results/maestro-report.xml --test-output-dir test-results/maestro -e E2E_USER="$E2E_USER" -e E2E_PASSWORD="$E2E_PASSWORD" --include-tags smoke .maestro
maestro check-syntax .maestro/Should_ShowOrderTitle_When_OrderIsInHistory.yaml
```

`maestro check-syntax <file>` prints `OK` on valid syntax. It is absent from the docs' CLI reference, so confirm it in `maestro --help` on the installed version.

**EAS Workflows** (Expo; the `maestro` job is alpha). Build a simulator or emulator app first: an `eas.json` profile with `withoutCredentials: true`, `ios.simulator: true` and `android.buildType: "apk"`.

```yaml
jobs:
  maestro_android:
    needs: [build_android]
    type: maestro
    params:
      build_id: ${{ needs.build_android.outputs.build_id }}
      flow_path: ['.maestro/Should_ShowOrderTitle_When_OrderIsInHistory.yaml']
      include_tags: smoke
      output_format: junit
```

`build_android` is Expo's build job with that profile (`docs.expo.dev/eas/workflows/examples/e2e-tests`).

- `flow_path` takes a file, a list or a directory. `retries` defaults to 0 and `retry_failed_only` to true; follow `qa/cicd/ci-conventions` (0, except a documented hotspot). `record_screen` defaults to false because it costs emulator performance.
- An Android job sets `runs_on` to a `linux-*-nested-virtualization` worker; check the name against the project's images.
- Run by hand: `eas workflow:run .eas/workflows/<file>.yml`.

**GitHub Actions, Android emulator.** Maestro's docs describe Maestro Cloud for Actions, not a local emulator. This job joins two documented pieces (the emulator runner's KVM step and `script:`, and Maestro's install line); it has not been run in this library, so run it once before trusting it.

```yaml
jobs:
  e2e_android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - name: Enable KVM
        run: |
          echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
          sudo udevadm control --reload-rules
          sudo udevadm trigger --name-match=kvm
      - name: Install Maestro
        run: |
          curl -fsSL "https://get.maestro.mobile.dev" | bash
          echo "$HOME/.maestro/bin" >> "$GITHUB_PATH"
      - uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          arch: x86_64
          script: |
            adb install app-e2e.apk
            mkdir -p test-results
            maestro test --format junit --output test-results/maestro-report.xml --test-output-dir test-results/maestro --include-tags smoke .maestro
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: maestro-results
          path: test-results/
          retention-days: 14
```

- **The JUnit file feeds the CI's native test report** (the `--format junit` file is the input to a publish-test-results step; the wiring is `qa/cicd/typescript/skills/ci-pipelines`). Upload `test-results/` always, so a failed run keeps its screenshots, hierarchy and logs. Retention follows `qa/cicd/ci-conventions` (14 days).
- **Maestro Cloud**: `maestro cloud --api-key … --project-id … --app-file <apk or app> --flows .maestro`, or the `mobile-dev-inc/action-maestro-cloud@v2.0.2` action. Pass the workspace folder, not one file, so subflows and `config.yaml` upload. The API key is a CI secret.
- A runner that cannot start the driver in time: raise `MAESTRO_DRIVER_STARTUP_TIMEOUT` (ms; defaults 15000 Android, 120000 iOS).

## Maestro Studio and the MCP server

- **Maestro Studio** is the desktop app for writing flows visually (right-click an element to add YAML, run step by step). Its output is a flow that still follows this skill.
- **The Maestro MCP server** ships in the CLI: `claude mcp add maestro -- maestro mcp` (stdio). The agent may call `mcp__maestro__list_devices`, `inspect_screen` (the view hierarchy as JSON, for ids), `take_screenshot`, `run` and `cheat_sheet`. `run` takes exactly one of `{ yaml }`, `{ files }` or `{ dir, include_tags, exclude_tags }` and validates syntax as part of the call. Save a working inline flow as a file under `.maestro/`, with a tag. The cloud tools are not granted: they need a login and spend a cloud run.

## Review rows

| Check | Bad sign | Severity |
|---|---|---|
| No fixed waits | A script, a repeated `tapOn`, or a long `timeout` standing in for a condition; every `timeout` at 60000 | blocker |
| Test id first | `text:` where the app tags an id; a `point:` coordinate | major |
| Repeated steps are a subflow | The same sign-in block pasted into several flows | major |
| Every flow is tagged | No `tags:` header | minor |
| Reset between flows | A flow with no `launchApp` / `clearState`, or one that needs the previous flow's state | blocker |
| No credentials in a flow | A literal email or password, or a real account | blocker |
| Subflows stay out of discovery | `flows: ["**"]` with no `!subflows/**` | major |

The `ui-test-author/review` skill carries these rows for a review run.

## Handoffs

- Selectors on the live app → `qa/typescript/skills/mobile-screen-explorer` (`maestro hierarchy` for a Maestro project)
- Failure evidence rules → `qa/typescript/skills/evidence-capture`
- Pipelines and retention → `qa/cicd/typescript/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- Device farms → `qa/typescript/skills/device-cloud`
- Test ids in the app → the matching `mobile-*` dev agent, through `missing-testids.md`
- Review → `qa/typescript/skills/ui-test-author/review`
