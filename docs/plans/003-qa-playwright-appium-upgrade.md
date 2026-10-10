# 003 — QA Playwright 1.64 and Appium 3 upgrade — plan (2026-10-10)

**Goal:** Move the three qa plugins (`qa-typescript`, `qa-java`, `qa-dotnet`) onto current Playwright and
current Appium, and make them use what the tools now offer. TypeScript pins Playwright 1.64. Java, .NET
and Python pin 1.63 until their 1.64 packages publish. Appium moves to 3. The plan fixes every defect the
2026-10-10 audit found. It adds a per-stack `evidence-capture` skill (screenshots, video, screencast,
trace, HAR — Playwright and Appium) and a shared `webmcp-testing` skill. It teaches locator scoping with
`locator.within()`, and wires all of it into the `qa-ui-*`, `qa-bdd-*` and `qa-mobile-*` agents.

**Status:** T1, J1, N1 and T2 landed 2026-10-10: the TypeScript Playwright 1.64 writer (SKILL.md, four
references, six assets), the Java Playwright 1.63 writer (SKILL.md, four references, nine assets around one
parallel-safe `BaseTest` on allure-java 3.0) and the .NET Playwright 1.63 writer (SKILL.md, four references,
eight assets: CPM props, a versionless `UiTests.csproj`, `ui.runsettings`, `BaseTest : PageTest`, a
root-namespace `AuthSetup`), each with its stack's `ui-test-author/review` and `page-object-design` aligned;
.NET `ui-project-setup` now scaffolds from those assets with a v1.63.0-noble Dockerfile. T2 added
`qa/typescript/skills/evidence-capture` (SKILL.md + `references/playwright.md`), loaded by `qa-ui-typescript`
Step 1 / Mode A and `qa-bdd-typescript` Step 4, and put TS `test-reports`, `flaky-test-quarantine`,
`ci-conventions` (one Allure CLI pin, `allure-commandline@2.46.1`) and the three TS CI references on the
canonical config (D35–D37). Next: J2. Built but unverified: no asset, workflow or pipeline has been compiled
or run (G1 does that; D24's TS config import, the Java build on Allure Gradle plugin 4.3.0, the .NET build on
NUnit3TestAdapter 6.3.1 / Test SDK 18.10.1, and T2's `dorny/test-reporter` `java-junit` parse of Playwright's
junit are the open risks).
Planned 2026-10-10. The research behind it is committed with this plan:
`docs/research/003-qa-playwright-appium/` (5 files). So is the read-only audit:
`docs/audits/003-qa-playwright-appium/` (4 files). All open questions were answered on 2026-10-10:
- Java moves to allure-java 3.0.
- Java and TS get `mobile-project-setup` (S1).
- `playwright-cli` is documented alongside MCP.
- NUnit stays 4.x.
- A Maestro lane is added (X1).
- The newest Appium client majors are primary.

Next: J2 (H1, the user's, blocks no task). The cost is 19 agent sessions on the subscription, each started by the user
from Plan Queue. Nothing else is metered.

## 1. What already exists, and what is missing

Audit files are cited as `aTS` / `aJ` / `aN` / `aM` = `docs/audits/003-qa-playwright-appium/{typescript,java,dotnet,mobile}.md`.

| # | Need | Today | Gap |
|---|---|---|---|
| N1 | One current Playwright version per stack | TS: 17 pins across 1.42–1.50 floors, Docker `v1.50.0-noble` (`aTS` §1). Java: 1.49.0 / 1.50.0 / 1.60.0, plus two invalid Maven `4.+`/`5.+` (`aJ` §1e). .NET: 1.47 / 1.49 / 1.50 / 1.55, plus a non-existent `Applitools.Playwright` package (`aN` §1). Python: unpinned. The glob change is mis-dated "1.43" in all three `playwright-routes.md` | Pin TS 1.64.0 and Java/.NET/Python 1.63.0 (§2). A checker enforces it (§6, D3) |
| N2 | Locator scoping and the modern locator API | `filter`, `and`/`or`, `within`, `frameLocator`, `describe` and `visible()` have 0 hits in all three lanes. Scoping exists only as a prose rule (`page-object-design/SKILL.md:91`). The locator order is stated in 5 places in 3 orders (`aTS` §4.1) | One locator reference per writer skill (§3.1), with `within()` on TS and its 1.63 equivalent on Java/.NET |
| N3 | Modern web-first assertions | `toHaveAccessibleName/Description/ErrorMessage`, `toHaveRole`, `toContainClass` and aria snapshots have 0 hits in all lanes. Java teaches a non-existent `AssertOptions` and a message parameter Java lacks (`aJ` D5, D6) | `references/assertions.md` per stack |
| N4 | Evidence capture (screenshot, video, screencast, trace, HAR) the UI agent can load | It lives only in `qa/reporting/*/test-reports`, which `qa-ui-*` may not load (`qa-ui-typescript.md:18`). Java stops a trace that was never started (`aJ` D15). .NET writes traces to `%TEMP%` while CI uploads an empty folder (`aN` C-05). TS sets `trace: 'on-first-retry'` with `retries: 0`, so no trace is ever recorded (`aTS` C6). Video: 0 hits in Java/.NET. Screencast (1.59): 0 hits | New `evidence-capture` skill per stack (§3.2). Default failure hooks go in each writer's base test/config (D4) |
| N5 | WebMCP testing | 0 hits repo-wide. Playwright 1.64 ships `page.webmcp` (Node). Java/.NET are on 1.63 | New `qa/_shared/webmcp-testing` skill (§3.3) |
| N6 | Visual regression that exists in Java/.NET | The Java default uses a fabricated `assertThat(page).hasScreenshot()` (`aJ` D1). The .NET default uses a fabricated `ToHaveScreenshotAsync` (`aN` T1). Both routers call it "start here" | Rewrite both on `screenshot()` plus a comparator (D9) |
| N7 | A parallel-safe Java lifecycle | `static Playwright`/`Browser` (`aJ` D2), nine competing base classes (`aJ` D22), `parallel="methods"` in `browser-cloud-setup` | One `BaseTest` (instance fields, `parallel="classes"`, D8) that every Java skill extends |
| N8 | A .NET template that runs | `[SetUpFixture]` in the wrong namespace (`aN` T4). No `BaseURL` anywhere (T5). `.runsettings` never taught (T11). CI shards with `Playwright.Shard`, which is a no-op (T2) | `.NET` assets that compile, plus NUnit-filter sharding |
| N9 | Agents reach the tools they are told to use | The Playwright MCP grants lack hover, key-press, tabs, find, network, console, tracing and video. `browser_generate_locator` and the two storage tools need `--caps` that the local server lacks (`playwright-agent-tooling.md` §0). Mobile grants lack `appium_screen_recording`, permissions and geolocation, and name docs tools no agent can call (`aM` D7) | §5 allowlists, plus H1 registers both servers |
| N10 | Appium lane on Appium 3 and current clients | Everything is keyed to Appium 2.x, java-client 9.x, Appium.WebDriver 8.x, and WDIO 9 with Vitest (`aM` §4, D5). Review rows push removed APIs (`aM` D3). `page_template.cs` does not compile (`aM` C1). Java uses `selenium.html5.Location`, which was removed (`aM` C2). TS Device Farm uses the wrong test type (`aM` D4) | Appium 3 lane per stack (§2.4, M1–M3) |
| N11 | Appium failure evidence | No screenshot, recording, page source or logs on failure in any stack (`aM` §2.3, L1) | `evidence-capture/references/appium.md` plus hooks in each `BaseMobileTest` |
| N12 | Mobile web has an owner | `responsive-testing` hands device emulation to `ui-test-author/playwright`, which has none, in all 3 stacks (`aM` L9) | `references/emulation-and-mobile-web.md` per stack |
| N13 | Skills obey the house rules | A `// TODO: missing data-testid` marker is mandated against CLAUDE.md (`aTS` L1, `aJ` D20, `aN` T10, `aM` L3). Kebab-case test ids clash with the FE PascalCase rule (`aTS` L2). Retries 1 vs 0 (`aTS` L3). Six test-naming styles (`aJ` D28). ~120 / 80+ / 70+ / 330 inline-comment lines in TS / Java / .NET / mobile samples. `if`, `try/finally` and loops sit inside tests (`aTS` C4–C5, `aJ` D11–D12, `aN` D-10) | §4 rules R1–R12, applied to every file a task touches |
| N14 | Reporting and CI match the evidence | TS uses the deprecated `import { allure } from 'allure-playwright'` (`aTS` D3). Allure pins drift (`aJ` V5). Docker tags are stale. The CI artifact paths point at folders nothing writes. Java has no Azure Playwright job (`aJ` D18). `./gradlew :e2e:installPlaywrightBrowsers` is defined nowhere (`aJ` D17) | Each stack's evidence task (T2/J2/N2) owns its reporting and CI references |
| N16 | Java on one Allure major, the current one | allure-testng is pinned at 2.27.0 / 2.29.0 / 2.35.3 / `2.+` across 20 Java skill files (`aJ` V5). allure-java 3.0.0 (2026-09-11) renamed `Allure.addAttachment` to `Allure.attachment(..., AttachmentOptions)` (`appium.md` §0) | allure-java 3.0 in every Java skill (D12) |
| N17 | Java and TS mobile projects can be scaffolded | Only .NET has `mobile-project-setup` (`qa-mobile-dotnet.md:85`). The Java and TS agents promise a scaffold step with no skill behind it (`aM` L10) | `mobile-project-setup` for Java and TS, plus Step 0 in both agents (S1) |
| N18 | Expo/React Native teams can use Maestro | `qa-mobile-typescript` is Appium/WebdriverIO only. Plan 002 Q3 asks the same question | A Maestro authoring skill in the TS plugin (X1) |
| N19 | Agents can use `playwright-cli` | Not mentioned anywhere in `qa/`. Microsoft recommends it for coding agents, because snapshots go to files instead of the model's context (`playwright-agent-tooling.md` §0, §5) | Documented alongside MCP (A1, T2/J2/N2, D13) |
| N15 | The docs say what landed | No Playwright or Appium line in CLAUDE.md's version policy. Catalog rows name `ui-test-author/reviewer` and `bdd-project-setup`, neither of which exists (`aTS` D12, `aM` D16) | G1 |

## 2. Versions this plan pins

### 2.1 Playwright

| Stack | Package | Version | Docker image | Source |
|---|---|---|---|---|
| TypeScript | `@playwright/test` | **1.64.0** | `mcr.microsoft.com/playwright:v1.64.0-noble` | `playwright-releases.md` §(a) |
| Java | `com.microsoft.playwright:playwright` | **1.63.0** | `mcr.microsoft.com/playwright/java:v1.63.0-noble` | same |
| .NET | `Microsoft.Playwright.NUnit` (it pulls in `Microsoft.Playwright`; do not reference both) | **1.63.0** | `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` (no `-jammy` since 1.60) | same |
| Python | `playwright` + `pytest-playwright` | **1.63.0** + **0.10.0** | `mcr.microsoft.com/playwright/python:v1.63.0-noble` | same |

### 2.2 Companions

| Stack | Artifact | Version |
|---|---|---|
| TS | `allure-playwright`, `allure-js-commons` | 3.13.0 (needs `@playwright/test` ≥ 1.62) |
| TS | `@axe-core/playwright` / `playwright-bdd` | 4.13.0 / 9.2.1 |
| Java | `com.deque.html.axe-core:playwright` | 4.13.0 (exact; never `4.+` in Maven) |
| Java | `io.qameta.allure:allure-testng` (and every other `allure-*` Java module the skills use) | **3.0.0** (Java 17 baseline). Attachments use `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`. D12 |
| Java | `org.testng:testng` / `org.assertj:assertj-core` | 7.12.0 / 3.27.7 |
| Java | `io.percy:percy-playwright-java` / `com.applitools:eyes-playwright-java5` | 1.2.1 / 5.86.9 |
| .NET | `Deque.AxeCore.Playwright` / `Allure.NUnit` | 4.13.0 / 2.15.0 |
| .NET | `PercyIO.Playwright` / `Eyes.Playwright` | 1.0.4 / 1.37.49 |
| .NET | `NUnit` | the latest **4.x** (4.6.1). Adapter and Test SDK at the latest release that supports NUnit 4. Not NUnit 5 (D18) |
| all | Allure report CLI | one pin in `ci-conventions`, used by every `test-reports`. If allure-java 3.0 results need a different report generator than the TS and .NET results, J2 records the per-stack split as a dated decision |

### 2.3 Version lanes: what a 1.63 binding does instead of a 1.64 API

A 1.64-only API is taught **only** in the TypeScript lane. The Java and .NET skills teach the 1.63 form,
plus one line: "from 1.64: `<native API>`". Source: `playwright-releases.md` §(e).

| 1.64 API (Node now) | Java / .NET on 1.63 |
|---|---|
| `child.within(parent)` | `parent.locator(child)`, which gives the same result. Per-parent `nth` resolution is guaranteed only from 1.64 |
| `page.webmcp.tools()` / `callTool()` | `page.evaluate(...)` against `document.modelContext` (`webmcp.md` §4.4). Chromium 153 takes the input as a JSON string |
| `page.getByRef('e2')` | none. Do not teach it on 1.63 |
| video `fps`, screencast `style`, `recordVideoFps` | none |
| `apiRequestContext.addCookies/cookies/clearCookies` | context cookies via `browserContext.addCookies` |

### 2.4 Appium

**Primary lane: Appium 3 with the newest client majors (D17).** Source: `appium.md` §1–§2.

| Artifact | Primary | Supported (down-level, or a device cloud still on Appium 2) |
|---|---|---|
| Appium server | 3.8.0 | 2.19 (frozen) |
| `appium-uiautomator2-driver` / `appium-xcuitest-driver` | 8.x / 12.x | 4.x / 9.x |
| `io.appium:java-client` | **11.0.0**, plus `org.seleniumhq.selenium:selenium-support` ≥ 4.50 | 10.x |
| `Appium.WebDriver` | **9.0.0** | 8.x |
| `webdriverio` + `@wdio/*` | **10.0.2** (Node ≥ 22.19; Mocha framework) | 9.x |
| `@wdio/allure-reporter` | 10.0.1 | — |
| `appium-mcp` | `@latest` in the dev registration (1.95.8 on 2026-10-10) | — |

Down-level versions are written in prose only ("java-client 10.x"), never as a coordinate. That keeps
§6's checker meaningful.

### 2.5 Bumping Java and .NET to 1.64 later

When Maven and NuGet publish 1.64:
1. Change `EXPECTED` in `tools/qa-version-check.py`.
2. Run the checker. It lists every site to change.
3. Change those sites.
4. Replace each §2.3 "from 1.64" line with the native API.
5. Delete the matching row from §2.3's table in the plan that does the bump.

Write this procedure as the last section of `tools/qa-version-check.py`'s module doc (G1).

## 3. Target shape — the files each lane ends with

### 3.1 `qa/<stack>/skills/ui-test-author/playwright/` (T1, J1, N1)

| File | Holds |
|---|---|
| `SKILL.md` (≤ 16,000 chars) | The stack and a **Versions** table copied from §2. These are the only Playwright pins in the skill. Then: when and when not to use it, inputs, rules (locator ladder, page-object rules, test rules), generation steps, handoffs. It links every reference and asset; code lives in the assets |
| `references/locators.md` | The ladder: `data-testid` → role → label → placeholder → text → alt/title → CSS fallback. Then: `getBy*` (incl. `getByRole({ description })` 1.60); `filter({ has, hasNot, hasText, hasNotText, visible })`; `and()` / `or()`; chaining from a component root; `within()` vs `parent.locator()` vs `filter({ has })` vs `and()` (the table in `playwright-releases.md` §(c)); `visible()` (1.63) instead of `:visible`; frames (`frameLocator`, selector-less `frameLocator()` 1.63, `contentFrame()`); strictness, and positional `nth()/first()` only with a stated reason; `describe()`; `addLocatorHandler` for overlays; the test-id attribute (TS `testIdAttribute`, Java `playwright.selectors().setTestIdAttribute`, .NET runsettings `TestIdAttribute`). Last, the agent-facing locators: `ariaSnapshot({ mode: 'ai' })`, `normalize()`, `pickLocator()`, and `getByRef()` (TS only) |
| `references/assertions.md` | The web-first set, incl. accessible name/description/error message, role, `toContainClass`, value, URL (TS: string is exact, RegExp, predicate), aria snapshot on locator and page (1.60). Then: poll / `toPass` / soft, the one-shot-read ban with its fix, and failure messages per stack (TS message arg; Java has none, so use `describe()`; .NET `Expect(locator, "message")` 1.60) |
| `references/config-and-fixtures.md` (TS) · `references/lifecycle.md` (Java, .NET) | TS: the canonical config explained (§3.1 assets), fixtures (test/worker scope, `auto`, `box`, option fixtures), setup project + `dependencies` for storage state, `webServer.wait`, `TestProject.default`, CLI (`--last-failed`, `--only-changed`, `--repeat-each`, `--shuffle`), tags via `{ tag }`, the 1.64 breaking changes, Test Agents as optional (D14). Java/.NET: the base-test lifecycle (R8), base URL, auth state, browser install, codegen and show-trace commands, headed/debug switches |
| `references/emulation-and-mobile-web.md` | Device profiles (TS `devices[...]`, .NET `Playwright.Devices[...]`, Java explicit options because Java has no registry); `isMobile`, `hasTouch`, `tap()`; `screen` (the 1.64 change); viewport per project or class, never per test except live-resize specs; `colorScheme`, `reducedMotion`, `forcedColors`, `contrast`; locale, time zone, geolocation, permissions; `page.clock` (install, `setFixedTime`, `runFor`, `pauseAt`); offline. Emulation is not a device: real-device mobile web → `device-cloud` |
| `assets/` (compilable, no comments) | TS: `playwright.config.ts`, `fixtures.ts`, `auth.setup.ts`, `LoginPage.ts`, `login.spec.ts` · Java: `build.gradle.kts`, `settings.gradle.kts`, `testng.xml`, `BaseTest.java`, `LoginPage.java`, `LoginTest.java` · .NET: `Directory.Packages.props`, `UiTests.csproj`, `ui.runsettings`, `BaseTest.cs`, `AuthSetup.cs`, `LoginPage.cs`, `LoginTests.cs` |

### 3.2 `qa/<stack>/skills/evidence-capture/` (new — T2, J2, N2; `references/appium.md` by M1, M2, M3)

Skill name `qa-evidence-capture-<stack>`.

| File | Holds |
|---|---|
| `SKILL.md` (≤ 16,000 chars) | When to capture what: failure evidence (the R7 defaults that the base test/config already carries); deliberate recordings (bug repro, demo, an agent's "receipt" of what it did); and exploratory capture while an agent drives Playwright MCP or appium-mcp. Paths and names equal the CI upload paths (R7). Retention follows `ci-conventions`. PII: traces, HAR and video carry tokens, so they are never committed and are masked where possible. It routes to the two references |
| `references/playwright.md` | Screenshots (every option, WebP 1.62, locator screenshots, runner modes and object form); video (`recordVideo`, the 7 runner modes since 1.61, size/fps (fps 1.64), finalize after `context.close()`, `saveAs` order per binding); **screencast** (`page.screencast` start/stop, `showActions`, `showChapter`, `showOverlay`, its known issues); trace (modes, object form with `snapshots: { dom, aria, screen }` 1.63, `test.step` / `tracing.group`, chunks, `live`); HAR (`recordHar`, `tracing.startHar` 1.60, `routeFromHAR` update modes); attachments (TS `testInfo.attach` / `step.attach`; Java/.NET via Allure and `TestContext.AddTestAttachment`); `error-context.md` (1.53); viewing (show-report, show-trace, trace.playwright.dev, and the `npx playwright trace` CLI that agents can read); exploratory capture through MCP (`browser_take_screenshot` with `filename`, `browser_start_video`/`stop_video`, `browser_start_tracing`/`stop_tracing`); codegen's recorder, incl. "Assert snapshot" |
| `references/appium.md` | Screenshot, page source and device logs on failure. Screen recording kept only on failure: `startRecordingScreen` per client, or `mobile: startMediaProjectionRecording` (Android 10+) / `mobile: startXCTestScreenRecording` (iOS 17+), with their limits. `appium_screen_recording` and `SCREENSHOTS_DIR` for agent capture. Farm session video and pass/fail marking |

### 3.3 `qa/_shared/webmcp-testing/` (new — A1)

Skill name `qa-webmcp-testing-shared`.

| File | Holds |
|---|---|
| `SKILL.md` (≤ 16,000 chars) | The API as of 2026-10-10: `document.modelContext`, `registerTool(tool, { signal })` (unregistered by aborting), `getTools()` / `executeTool()`, annotations, events. Browser support and flags. Playwright 1.64 `page.webmcp` and its traps. The test-design checklist (condensed from `webmcp.md` §6). The security stance (tool names, descriptions and results are untrusted; consequential tools are never auto-called against shared environments). UI-path vs tool-path parity. Owners next door: agent evals → `ai-feature-testing`; the tool server side → the `tooling` plugin's `tool-mcp-builder`; prompt-injection attacks → `qa-security` |
| `references/typescript.md` | Native `page.webmcp`: a dedicated Chromium project with `launchOptions.args: ['--enable-features=WebMCP']` (and Firefox prefs), `expect.poll` for registration, schema validity, valid/invalid calls, unregistration, CDP observation (optional) |
| `references/java.md`, `references/dotnet.md` | 1.63: an `evaluate` helper (`webmcp.md` §4.4) plus launch args. From 1.64: `page.webmcp()` / `Page.Webmcp` |
| `assets/` | `webmcp.spec.ts`, `WebMcpTest.java` (extends J1's `BaseTest`), `WebMcpTests.cs` (derives from N1's `BaseTest`) |

### 3.4 `qa/<stack>/skills/ui-test-author/appium/` (M1, M2, M3)

`SKILL.md` on the Appium 3 lane, plus compilable `assets/`. Each asset set holds a base test with the
failure-evidence hooks, the driver factory, one screen object that uses the scoped-component pattern, and
one test. .NET keeps its existing asset names and fixes them. Java and TS gain an `assets/` folder.

### 3.5 `tools/qa-version-check.py` (new — G1)

Specified in §6.2.

### 3.6 `qa/{java,typescript}/skills/mobile-project-setup/` (new — S1)

Skill names `qa-mobile-project-setup-java` and `qa-mobile-project-setup-typescript`. Each mirrors the .NET
`mobile-project-setup` as M3 leaves it: the Appium 3 server and drivers (`appium setup`,
`appium driver install`, `appium driver doctor`), Node 24, the Android SDK/emulator and Xcode/WDA
prerequisites, the project layout that M1's or M2's `ui-test-author/appium/assets/` drop into, the
capability and environment configuration, the first smoke run, and the hand-off to `device-cloud`. The
SKILL.md is ≤ 16,000 chars. It references the `ui-test-author/appium` assets instead of copying them.

### 3.7 `qa/typescript/skills/ui-test-author/maestro/` (new — X1)

Skill name `qa-ui-test-writer-maestro-typescript`, beside `ui-test-author/appium` (the existing names are
`qa-ui-test-writer-<tool>-typescript`). It is owned by `qa-mobile-typescript` as the alternative to
Appium/WebdriverIO for projects that run Maestro (typically Expo).

| File | Holds |
|---|---|
| `SKILL.md` (≤ 16,000 chars) | When Maestro and when Appium. The flow layout (`.maestro/`, subflows as the page-object analogue). Selectors on the plan 002 §8.5 test-id contract. Waits without sleeps. Test data, env and tags. Evidence (screenshots, recordings, the test-output dir). CI (EAS Workflows and a GitHub Actions emulator job), and JUnit output to feed the native report widget. Review rows. Every fact from X1's research file |
| `assets/` | A `.maestro/` sample: one flow, one subflow, `config.yaml`. Valid YAML, no comments |

### 3.8 `playwright-cli` alongside Playwright MCP (A1, T2, J2, N2)

There is no new skill. `page-objects-from-url` ×3 documents the CLI route next to the MCP route: `open`,
`snapshot`, `eval` for test ids, `generate-locator`, `screenshot`, `state-save`/`state-load`,
`tracing-start`/`tracing-stop` and `video-start`/`video-stop` (`playwright-agent-tooling.md` §5). Each
`evidence-capture/references/playwright.md` lists the CLI equivalents of the MCP capture tools. Agents
already hold `Bash`, so no grant changes. MCP stays the primary route (D13).

## 4. Rules every task applies

Apply each rule to every file the task touches. Leave untouched files alone.

- **R1 Pins.** Only §2's versions. "≥ 1.xx" floors only where a feature needs one, with the feature named.
  The glob `?`/`[]` removal is **1.52**. No floating `*` or `+` versions in snippets.
- **R2 No TODO marker on fallback locators.** `missing-testids.md` is the contract. Each row names the
  page, the element and the fallback locator used. The code carries no marker. A review row or a
  checklist row may name the marker in prose or a table; §6.1 bans it only in code blocks and assets.
- **R3 Test ids in examples are PascalCase dot-separated** (`Login.Submit`, `OrderRow.Title`), with
  static row locators. This is the CLAUDE.md frontend rule that `fe-react` and `fe-blazor` generate.
- **R4 Test names** are `Should_X_When_Y` in every sample.
- **R5 No inline comments in samples.** Rationale goes in the prose around the sample.
- **R6 Samples obey the test rules.** No `try`/`catch`/`finally` in a test body. No `if`/`for` driving
  assertions. No OR. Exact status codes. Tests go through page objects or fixtures, never raw `page.`
  calls. Every promise is awaited. Cleanup lives in teardown.
- **R7 Evidence defaults:** trace `retain-on-failure`, video `retain-on-failure`, screenshot
  `only-on-failure` with full page. Retries follow `ci-conventions` (0, except a documented hotspot,
  D7). Paths:

  | Stack | Playwright evidence | Appium evidence |
  |---|---|---|
  | TS | `test-results/` (runner default), `playwright-report/`, `allure-results/` | `test-results/appium/` |
  | Java | `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}` | `build/appium-artifacts/` |
  | .NET | `<TestContext.WorkDirectory>/playwright-artifacts/` | `<TestContext.WorkDirectory>/appium-artifacts/` |
- **R8 Lifecycles.** Java (Playwright and Appium): instance fields; a browser or driver per class in
  `@BeforeClass`; a context/page per test; `parallel="classes"`; no static mutable state and no
  `ThreadLocal` (D8). .NET: `BaseTest : PageTest`; `ContextOptions()` amends `base.ContextOptions()`;
  `ParallelScope.Self`. Every stack reads the app URL from `BASE_URL`. Headed runs use `HEADED=1` (the
  .NET adapter reads it natively; the Java `BaseTest` reads it; TS uses `--headed`). Java's
  `BaseTest` exposes `protected BrowserType.LaunchOptions launchOptions()` so a suite can add launch args
  (A1's WebMCP suite needs this).
- **R9 New skills.** The description is ≤ 500 chars: "Use when…", triggers, and a "Do NOT use for…"
  clause. The body is ≤ 16,000 chars. The creating task adds the skill to its plugin(s) in
  `.claude-plugin/marketplace.json` and adds a row to `docs/skills-catalog.md` (D16).
- **R10 Agent tool grants** are exactly §5's lists.
- **R11 Research is the fact source.** Do not teach anything the research marks UNVERIFIED (for
  example `page.perform`). A fact a task must check live is named in that task's traps.
- **R12 Stay in your lane.** Edit only the paths your task names, plus this plan.

## 5. Agent wiring and tool grants

### 5.1 Where the new skills load

| Agent | Step | Adds | Task |
|---|---|---|---|
| `qa-ui-<stack>` | 1 Foundations | `qa/<stack>/skills/evidence-capture/SKILL.md` + `references/playwright.md` | T2 / J2 / N2 |
| `qa-ui-<stack>` | 3 Specialized layers | WebMCP: `qa/_shared/webmcp-testing/SKILL.md` + `references/<stack>.md` | A1 |
| `qa-ui-<stack>` | brownfield Mode A | Read the failing test's trace (TS: `npx playwright trace open|actions|errors`; Java/.NET: show-trace) before changing code | T2 / J2 / N2 |
| `qa-bdd-<stack>` | the step that loads `ui-test-author/playwright` | `evidence-capture` (Playwright reference) | T2 / J2 / N2 |
| `qa-mobile-<stack>` | 1 Foundations | `evidence-capture/SKILL.md` + `references/appium.md` | M1 / M2 / M3 |
| `qa-mobile-{java,typescript}` | 0 Project scaffold *(new; skip if a project exists)* | `mobile-project-setup` | S1 |
| `qa-mobile-typescript` | 2 Author | `ui-test-author/maestro` *(instead of `ui-test-author/appium` when the project runs Maestro)* | X1 |
| `qa-api-<stack>` | 3 | `production-uptime-checks` (today it is an orphan, `aTS` L8) | T4 / J4 / N4 |

### 5.2 Playwright MCP allowlist (`qa-ui-*` and `qa-bdd-*`, all three stacks)

Source: `playwright-agent-tooling.md` §3 and §8b. Every name exists in `@playwright/mcp` 0.0.83.

```
mcp__playwright__browser_navigate, mcp__playwright__browser_navigate_back, mcp__playwright__browser_snapshot,
mcp__playwright__browser_find, mcp__playwright__browser_click, mcp__playwright__browser_type,
mcp__playwright__browser_fill_form, mcp__playwright__browser_select_option, mcp__playwright__browser_press_key,
mcp__playwright__browser_hover, mcp__playwright__browser_file_upload, mcp__playwright__browser_handle_dialog,
mcp__playwright__browser_wait_for, mcp__playwright__browser_evaluate, mcp__playwright__browser_take_screenshot,
mcp__playwright__browser_resize, mcp__playwright__browser_emulate_media, mcp__playwright__browser_console_messages,
mcp__playwright__browser_network_requests, mcp__playwright__browser_network_request, mcp__playwright__browser_tabs,
mcp__playwright__browser_close,
mcp__playwright__browser_generate_locator, mcp__playwright__browser_verify_element_visible,
mcp__playwright__browser_verify_text_visible, mcp__playwright__browser_verify_value,
mcp__playwright__browser_verify_list_visible,
mcp__playwright__browser_storage_state, mcp__playwright__browser_set_storage_state,
mcp__playwright__browser_start_tracing, mcp__playwright__browser_stop_tracing,
mcp__playwright__browser_start_video, mcp__playwright__browser_stop_video
```

Deliberately left out:
- `browser_run_code_unsafe` (RCE-equivalent).
- The `vision` mouse tools.
- `browser_pdf_save`.
- The dynamic `webmcp_<tool>` tools: the UI path is what is under test, and WebMCP is tested through
  `page.webmcp` instead.

### 5.3 appium-mcp allowlist (`qa-mobile-*`, all three stacks)

Source: `appium.md` §6 ("AI-agent surfaces"). It keeps today's 14 and adds the rest:

```
mcp__appium-mcp__select_device, mcp__appium-mcp__prepare_ios_simulator, mcp__appium-mcp__appium_session_management,
mcp__appium-mcp__appium_mobile_device_control, mcp__appium-mcp__appium_driver_settings, mcp__appium-mcp__appium_context,
mcp__appium-mcp__appium_find_element, mcp__appium-mcp__appium_ai, mcp__appium-mcp__appium_gesture,
mcp__appium-mcp__appium_drag_and_drop, mcp__appium-mcp__appium_perform_actions, mcp__appium-mcp__appium_set_value,
mcp__appium-mcp__appium_mobile_keyboard, mcp__appium-mcp__appium_get_text, mcp__appium-mcp__appium_mobile_clipboard,
mcp__appium-mcp__appium_alert, mcp__appium-mcp__appium_screenshot, mcp__appium-mcp__appium_get_window_size,
mcp__appium-mcp__appium_get_page_source, mcp__appium-mcp__appium_orientation, mcp__appium-mcp__appium_geolocation,
mcp__appium-mcp__appium_screen_recording, mcp__appium-mcp__appium_mobile_device_info,
mcp__appium-mcp__appium_app_lifecycle, mcp__appium-mcp__appium_mobile_permissions,
mcp__appium-mcp__generate_locators, mcp__appium-mcp__appium_documentation_query, mcp__appium-mcp__appium_skills
```

Left out:
- `appium_generate_tests`, which emits Java/TestNG that bypasses the skills.
- `appium_prepare_ios_real_device`, a human device-prep step.

### 5.4 Server registration (H1)

```bash
claude mcp remove playwright
claude mcp add --scope user playwright -- npx @playwright/mcp@latest --caps=testing,storage,devtools --isolated --output-dir=.playwright-mcp
claude mcp add --scope user appium-mcp -e SCREENSHOTS_DIR=docs/app-map/screenshots -e APPIUM_MCP_DOCS_ENABLED=true -- npx -y appium-mcp@latest
npm i -g @playwright/cli@latest
```

Optional: `playwright-cli install --skills -g` installs Microsoft's own `playwright-cli` skill into
`~/.claude/skills`. The qa skills document the commands themselves, so it is not required.

Agents in a plugin cannot set caps on themselves, because plugin subagents ignore an `mcpServers`
frontmatter field (`playwright-agent-tooling.md` §8a). So each `qa-ui-*` and `qa-mobile-*` agent states
the registration it expects.

## 6. The gate (G1 only)

Run these from the repo root, in this order, and fix what fails. A failure may belong to any task above G1.

### 6.1 Repo checks

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. The library check is the script in `docs/plans/implemented/001-library-conformance-sweep.md` §7.
   Save it outside the repo and extend it as below, then run it. It prints `OK`.

   Add these to its `CHECKS` dict. They are evaluated on the whole text of every file:

   ```python
   "glob date": r"since (Playwright )?1\.43",
   "tool markup": r"</content>|</invoke>",
   ```

   Add a second dict, `CODE_CHECKS`. It is evaluated only inside fenced code blocks of `.md` files under
   `qa/`, and on every file under an `assets/` folder in `qa/`. Prose and tables may still name a banned
   API to warn against it; review rows and the conformance checklist do exactly that.

   ```python
   "todo marker": r"// TODO: missing data-testid",
   "fabricated visual api": r"hasScreenshot\(|HasScreenshotOptions|ToHaveScreenshotAsync|ToMatchSnapshotAsync",
   "dotnet shard no-op": r"Playwright\.Shard",
   "nonexistent package": r"Applitools\.Playwright",
   "deprecated allure import": r"import \{ allure \} from 'allure-playwright'",
   "removed appium api": r"AppiumDriver<MobileElement>|\bresetApp\(|\bResetApp\(|selenium\.html5|\bTouchAction\b|\bMultiTouchAction\b",
   "nonexistent capability": r"chromedriverAutodownload",
   "maven plus version": r"<version>[^<]*\+</version>",
   "floating playwright nuget": r'Microsoft\.Playwright[\w.]*" Version="[^"]*\*',
   ```

   Then add three more checks:
   - **Allowlists.** Every `mcp__playwright__<name>` under `qa/` must be in §5.2, and every
     `mcp__appium-mcp__<name>` must be in §5.3.
   - **`test.each`.** A `CODE_CHECKS` entry for `\btest\.each\b`, applied to `qa/typescript/` only.
   - **allure-java 2 API.** A `CODE_CHECKS` entry for `\bAllure\.addAttachment\(`, applied to
     `qa/java/` and `qa/reporting/java/` only (D12).
3. `python3 tools/qa-version-check.py` prints `OK` (§6.2).
4. `find qa -name .DS_Store` prints nothing.

### 6.2 `tools/qa-version-check.py` (G1 writes it)

- `EXPECTED`:
  - `typescript` → Playwright 1.64.0, `webdriverio` 10.0.2, `appium` 3.8.0.
  - `java` → Playwright 1.63.0, `java-client` 11.0.0, `allure-testng` 3.0.0.
  - `dotnet` → Playwright 1.63.0, `Appium.WebDriver` 9.0.0.
  - `python` → Playwright 1.63.0.
- **Stack of a file:**
  - It is `typescript`, `java` or `dotnet` for files under `qa/<stack>/`, `qa/reporting/<stack>/` and `qa/cicd/<stack>/`.
  - It is `python` for files under `qa/_shared/python-web-testing/`.
  - For `qa/_shared/webmcp-testing/references/<stack>.md` and its assets, take the stack from the file
    name or extension.
  - Skip every other `_shared` file unless it contains a pin, and then report it.
- **Pins it reads:**
  - npm: `"@playwright/test": "<v>"`, `@playwright/test@<v>`, `"playwright": "<v>"`, `"webdriverio": "<v>"`, `"appium": "<v>"`.
  - Maven: `com.microsoft.playwright:playwright:<v>`, `io.appium:java-client:<v>`, `io.qameta.allure:allure-testng:<v>`, and the Maven `<artifactId>`/`<version>` pairs for all three.
  - NuGet: `Microsoft.Playwright<suffix>" Version="<v>"`, `Appium.WebDriver" Version="<v>"`, and the matching `PackageVersion` entries.
  - Python: `playwright==<v>`.
  - Docker: `mcr.microsoft.com/playwright(/java|/dotnet|/python)?:v<v>-<distro>`.
  - A leading `^` or `~` is stripped before comparing.
- **Output:** every mismatch as `file:line found X expected Y`, and exit 1 when there are any.
  Otherwise print `OK`.
- The module docstring ends with §2.5's bump procedure.

### 6.3 Compile the assets (scratch directories under `$TMPDIR`, never inside the repo)

| Stack | Build |
|---|---|
| TS Playwright | `npm init -y`, then `npm i -D @playwright/test@1.64.0 typescript @types/node allure-js-commons@3.13.0 allure-playwright@3.13.0` (plus whatever the WebMCP asset imports). Copy `qa/typescript/skills/ui-test-author/playwright/assets/*` and `qa/_shared/webmcp-testing/assets/webmcp.spec.ts`. Use a strict `tsconfig`. `npx tsc --noEmit` → 0 errors. `npx playwright test --list` lists the asset tests |
| Java Playwright | Use J1's `build.gradle.kts` + `settings.gradle.kts` + `testng.xml` at the project root, with the `.java` assets under `src/test/java` (package path from the files) plus `WebMcpTest.java`. Use `gradle` if installed; otherwise download a Gradle distribution into the scratch dir. `gradle compileTestJava` succeeds. `gradle installPlaywrightBrowsers` is defined |
| .NET Playwright | N1's `Directory.Packages.props` + `UiTests.csproj` + the `.cs` assets + `WebMcpTests.cs`. `dotnet build` → 0 errors |
| TS Appium | `npm i -D webdriverio@10.0.2 @wdio/globals @wdio/types @wdio/mocha-framework typescript`. Copy `qa/typescript/skills/ui-test-author/appium/assets/*`. `npx tsc --noEmit` → 0 errors |
| Java Appium | A Gradle project with `io.appium:java-client:11.0.0`, `selenium-support` ≥ 4.50, TestNG and allure-testng 3.0.0, plus `qa/java/skills/ui-test-author/appium/assets/*`. `gradle compileTestJava` succeeds |
| .NET Appium | `dotnet new nunit` + `Appium.WebDriver` 9.0.0 + `qa/dotnet/skills/ui-test-author/appium/assets/*.cs`. `dotnet build` → 0 errors |
| Maestro | Every `.yaml` under `qa/typescript/skills/ui-test-author/maestro/assets/` parses as YAML (multi-document aware). If the `maestro` CLI is installed, also run the syntax or dry-run check that X1's research names. No device run |

### 6.4 Evidence smoke (Playwright, all three stacks)

In each scratch project, add two tests on top of the asset base test or fixture. One deliberately fails
on a `data:text/html,…` page. The other passes.

- **Pass condition:** the R7 artifact location holds a trace `.zip`, a `.webm` video and a `.png`
  screenshot for the failing test, and nothing for the passing one.
- **Browsers (TS):** `npx playwright@1.64.0 install chromium`.
- **Browsers (Java/.NET):** run `npx playwright@1.63.0 install chromium`. Browser builds are shared per
  Playwright version, so this works without `pwsh`. Java can also use `gradle installPlaywrightBrowsers`.

### 6.5 Size and descriptions

`python3 tools/token-audit.py`:
- No skill or agent description violation.
- Body + agent-file violations total ≤ 160. The baseline on 2026-10-10 is 109 + 51. The script exits
  non-zero while any size violation remains, so read the counts, not the exit code.
- Every SKILL.md this plan created or rewrote is ≤ 16,000 chars.

## 7. How the tasks are cut

- **Every task is `docs` work run as `general-purpose`.** That follows the precedent of plan 001 (D1):
  no domain agent maintains the library itself.
- **Tasks are ordered by layer, so each layer can bind to the one before.**
  - First the three authoring cores (T1, J1, N1). They fix the versions table, the base
    test/config and the locator reference that everything else cites.
  - Then the three evidence tasks (T2, J2, N2), which bind to those base tests.
  - Then A1 (MCP grants and WebMCP), which needs the base tests' launch seam.
  - Then the specialized UI skills in two passes (T3/J3/N3, then T4/J4/N4).
  - Then mobile (M1–M3), which binds to the evidence skills.
  - Then S1 (Java/TS mobile setup), which scaffolds the M1/M2 assets and mirrors M3's .NET setup skill.
  - Then X1 (Maestro), which slots into the TS mobile agent after M1 and S1 have edited it.
  - G1 last.
- Within a layer, the TypeScript task goes first and is the canonical shape. The Java and .NET tasks may
  read its output for parity, but §3 already fixes the file set, so they do not need to.
- **Budget target: ≤ 150k per session.** Each task's drivers are itemized in its block.
- **A parallel plan:** plan 002 (mobile dev plugins) touches `qa-mobile-*` and `mobile-screen-explorer`
  too. D21 splits the lines between the two plans. M1–M3 can run before or after plan 002's W1.
- **The cost, accepted and stated once:** intermediate commits are ungated, so the tree is not known to
  pass §6 at any task boundary, and the plan cannot be stopped halfway and trusted. Every capability
  becomes usable only once its skill *and* its agent wiring have landed: evidence capture after T2/J2/N2,
  WebMCP after A1, Appium evidence after M1–M3.

## Decisions

**D1 — Every task runs as `general-purpose` on the `docs` stack.** This matches plan 001 D1. A domain
agent (`qa-ui-typescript`, …) builds target projects: it would load its skill protocol and write an
orientation cache into this repo. **Cost:** there is no skill protocol, so every prompt names its full
reading list.

**D2 — TypeScript pins 1.64.0; Java, .NET and Python pin 1.63.0 until their 1.64 packages publish (the
user, 2026-10-10).** A 1.64-only API is taught only on TS. The other lanes get §2.3's 1.63 form plus a
"from 1.64" line. **Cost:** a second, small pass later (§2.5).

**D3 — One Playwright version per stack, enforced by `tools/qa-version-check.py`.** The user will bump
Java and .NET when 1.64 ships, so the bump needs a mechanical site list. That second need is what earns
the script. **Cost:** one new tool file whose `EXPECTED` dict must match §2.

**D4 — Evidence capture is a new skill per stack, but the default failure hooks live in the writer's base
test or config.**

| Option | Verdict | Why |
|---|---|---|
| New skill that owns policy and every capture API; the base test/config carries the R7 defaults | **chosen** | One lifecycle owner (`ui-test-author/playwright`). The skill is still a loadable, triggerable unit the UI, BDD and mobile agents share. It covers deliberate recordings, MCP capture and Appium too |
| New skill that also owns the hook code | rejected | Two skills would own one base class. This is the Java nine-lifecycles problem again (`aJ` D22) |
| A reference inside `ui-test-author/playwright` only | rejected | Not discoverable, the mobile lane cannot use it, and the user asked for skills |

**Cost:** the evidence skill points at code it does not own, and the two must agree on R7.

**D5 — Locator scoping (incl. `within()`) lives in `ui-test-author/playwright/references/locators.md`,
not a new skill.** Five files already state locator policy (`aTS` §4.1). A sixth owner would make that
worse. **Cost:** `within()` is found by loading the writer skill, not by its own trigger.

**D6 — WebMCP is one shared skill with per-stack references.** The checklist, the security stance and the
browser facts are stack-neutral. Only the calls differ. This follows `qa/_shared/contract-testing-pact`.
**Cost:** each `qa-ui-*` agent must load a `_shared` path, which A1 states in the loading protocol.

**D7 — Retries follow `ci-conventions` (0, except a documented hotspot). Flaky detection never depends on
in-run retries.** `ci-conventions` already declares itself the authority. TS `flaky-test-quarantine`
(`retries: CI ? 1 : 0`) defers to it and detects flakes from Allure history and a nightly `--repeat-each`
(TS). Java and .NET use the history plus their quarantine category. The evidence modes therefore use
`retain-on-failure`, which works with 0 retries. **Cost:** Playwright's native "flaky" status is not used.

**D8 — The Java lifecycle (Playwright and Appium) uses instance fields with TestNG
`parallel="classes"`.** This avoids static state and `ThreadLocal` while meeting Playwright Java's
thread rule (`playwright-evidence.md` §11.2). **Cost:** no method-level parallelism. A
`@DataProvider(parallel = true)` with Playwright or Appium is banned.

**D9 — Java/.NET visual regression = `screenshot()` plus a comparator library verified at authoring
time. Percy and Applitools stay as the hosted options.** Neither binding has a screenshot assertion
(`playwright-evidence.md` §2, §13). **Cost:** the comparator is a recommendation, not a Playwright fact.
The task names the library it checked.

**D10 — The `// TODO: missing data-testid` marker is dropped. `missing-testids.md` is the contract
(R2).** **Cost:** finding fallbacks later means reading the report, not grepping the code.

**D11 — Test ids in QA examples follow the CLAUDE.md frontend rule (PascalCase dot-separated, R3).**
**Cost:** QA's suggestions change shape for teams used to kebab-case.

**D12 — Java moves to allure-java 3.0 in every Java skill; allure-js stays 3.x and Allure.NUnit 2.15 (the
user, 2026-10-10).** Each task writes 3.0 calls in the files it already touches (J1–J4, J2's reporting,
M2). J4 also sweeps the six Java files no other task touches:
- `ai-feature-testing/references/deepeval.md`
- `db-testing/testcontainers/SKILL.md`
- `failure-injection-testing/SKILL.md`
- `feature-flag-testing/SKILL.md`
- `security-testing/dependency-scan/SKILL.md`
- `security-testing/passive-scan/SKILL.md`

This takes the place of a separate Allure session. The attach call is
`Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`. The core API is
enough, so the new allure-java `allure-playwright` module is not adopted. **Cost:** a Java 17 baseline
(the library is on 21). Which report generator reads 3.0 results is checked live in J2.

| Option | Verdict | Why |
|---|---|---|
| Migrate every Java skill in this plan | **chosen** (the user) | The Java lane never mixes majors |
| Migrate only the files this plan touches | rejected | The Java skills would disagree until a later sweep |
| Stay on 2.x | rejected | The user chose to migrate |

**D13 — Playwright MCP stays the primary route, with an explicit allowlist. `playwright-cli` is documented
alongside it (the user, 2026-10-10).** MCP is already wired, and its allowlist keeps RCE and dynamic page
tools out. The CLI is the token-cheaper route: snapshots go to files. Agents use it through `Bash`, which
they already hold, when MCP is not connected or a long extraction would flood the context (§3.8).
**Cost:** two routes to keep current, and the CLI route has no tool-level allowlist.

**D14 — Playwright Test Agents (`init-agents`) are documented in the TS writer as optional. The
`qa-ui-typescript` agent is not rebuilt on them.** Brownfield fix mode reads traces with the
`npx playwright trace` CLI. **Cost:** none beyond one reference paragraph.

**D15 — Flagship templates become compilable `assets/`, and G1 compiles them.** The audit found
non-compiling flagship code in every stack. Moving code into assets also takes the writer skills under
16,000 chars. **Cost:** an agent reads one more file to see the template.

**D16 — The task that creates a skill adds its marketplace entry and catalog row. G1 reconciles README,
CLAUDE.md and the catalog's stale rows.** The plan-format rule puts docs in the last task, but G1 carries
the whole gate and cannot also absorb every catalog row in budget. **Cost:** catalog edits are spread
over six task commits (T2, J2, N2, A1, S1, X1).

**D17 — Appium 3 with the newest client majors is the primary lane; the previous majors are the
supported lane (§2.4) (confirmed by the user, 2026-10-10).** java-client 11 (2026-10-07), WDIO 10 (2026-10-05) and Appium.WebDriver 9
(2026-09-16) are new. A down-level project keeps its lane, per the version policy. A device cloud that
does not yet run Appium 3 is the main risk (`appium.md` §0). `device-cloud` states how to check the
vendor's Appium version and falls back to the supported lane. **Cost:** primary-lane advice may meet a
cloud that cannot run it.

**D18 — .NET stays on NUnit 4.x (confirmed by the user, 2026-10-10).** NUnit 5.0.0 (2026-09-27) changes `Assert.ThrowsAsync`, and Allure.NUnit
2.15's compatibility with it is unverified (`appium.md` §1). **Cost:** one major behind.

**D19 — `qa/_shared/python-web-testing` is rewritten to the house wait rules and pinned, and stays in
`qa-java`.** Removing it from the plugin is a product decision, not an audit fix. **Cost:** a Python skill
keeps shipping inside the Java plugin.

**D20 — Java and TypeScript get `mobile-project-setup`, and their `qa-mobile-*` agents get a Step 0 (the
user, 2026-10-10).** This makes the "scaffold" promise real instead of dropping it (`aM` L10). One task
(S1) writes both, after M1–M3, so it can scaffold their assets and mirror M3's .NET skill. **Cost:** one
more session.

**D21 — Plan 002 (`docs/plans/002-mobile-plugins.md`, the new mobile dev plugins) owns two QA lines,
and M1–M3 leave them alone.** Plan 002 W1 edits line 10 of each `qa/*/skills/mobile-screen-explorer/SKILL.md`
(the React Native `testID` mapping, after its R3 verifies it). It also edits the "Related agents" section
of each `qa-mobile-*` agent, to name the dev agents that consume `missing-testids.md`. Both plans reach
the same mapping (`testID` → `accessibilityIdentifier` on iOS, `resource-id` on Android; plan 002 §8.5)
and the same id format (PascalCase dot-separated). M1–M3 write the ladder everywhere else to match plan
002 §8.5. The `missing-testids.md` column set stays as it is today (it already has "Fallback locator in
use"), so plan 002's `test-ids` skills read it unchanged. **Cost:** if plan 002 never runs, the
explorer's line 10 stays wrong. If both plans run in parallel worktrees, the second to land merges
around the other's lines in the same files.

**D22 — Maestro is a tool-specific authoring skill in the TS plugin, `ui-test-author/maestro`, owned by
`qa-mobile-typescript` (the user, 2026-10-10).** It sits beside `ui-test-author/appium`. The agent picks
Maestro or Appium at Step 2 from what the project uses. E2E stays with the QA peer, which matches plan 002
D7. This answers plan 002's Q3 from the QA side. X1 researches Maestro first, because this plan's
research did not cover it, and writes the facts to `docs/research/003-qa-playwright-appium/maestro.md`.
**Cost:** a research-and-write session, and a second mobile tool to keep current.

**D23 — The TS writer ships a sixth asset, `HomePage.ts` (T1, 2026-10-10).** §3.1 lists five TS assets.
The success journey must assert on the landing page without a raw `page` call in the spec, and a second
class inside `LoginPage.ts` would break one class per file. Readings: five files, with the landing page
folded into `LoginPage.ts` (rejected), or a sixth file (chosen). **Cost:** none for G1, which copies
`assets/*`.

**D24 — The signed-in state path is one constant, `authFile`, exported by `fixtures.ts` and imported by
both `playwright.config.ts` and `auth.setup.ts` (T1, 2026-10-10).** Readings: repeat the literal in the
config and the setup file, as the Playwright docs do (two strings to keep equal), or import one constant
(chosen). The config cannot be imported by a test file, and the setup file cannot be imported by the
config, so `fixtures.ts` is the only shared module. **Cost:** the config loads `fixtures.ts` and the page
objects when Playwright reads it. That is unverified until G1's `npx playwright test --list`; if it fails,
G1 repeats the literal in the config instead.

**D25 — `ui-test-author/selenium` changes only its test-id prose; its SauceDemo samples keep kebab-case
`data-test` values (T1, 2026-10-10).** Readings: R3 applied to every sample in a touched file, or T1's
"only the test-id line" (chosen). The samples locate the real `data-test` attributes saucedemo.com ships,
so renaming them would break them. The prose now says `data-testid` is the default and a `data-test`
project uses its own attribute. **Cost:** that file's samples are the one place R3 does not hold.

**D26 — The Java `BaseTest` takes storage state, device emulation and every other context setting through
one `protected Browser.NewContextOptions contextOptions()` hook, beside R8's `launchOptions()`, and applies
`BASE_URL` and the video folder after calling it (J1, 2026-10-10).** Readings: a dedicated
`storageState()` hook returning a path (the old skill's shape; emulation and locale would each need another
hook later), or one context hook (chosen). The sign-in that writes the state file is a `@BeforeSuite`
`AuthSetup` shown in `lifecycle.md` §6, not an asset. **Cost:** a subclass cannot change the base URL or
the video folder, which is the point; `AuthSetup` is not compiled by G1.

**D27 — The Java writer ships a seventh asset, `HomePage.java`, and `LoginPage.java` holds its component as
a nested `SignInForm` (J1, 2026-10-10).** §3.1 lists six Java assets. As in D23, the success journey needs a
landing page to assert on without a raw `page` call in the test. Readings: fold the landing page into
`LoginPage.java` (rejected: one class per file), or a seventh file (chosen); `SignInForm` as its own file
(an eighth asset) or nested (chosen, since only the sign-in screen mounts it). **Cost:** none for G1, which
places every `.java` asset by its package.

**D28 — `build.gradle.kts` registers a second `JavaExec` task, `playwright`, beside
`installPlaywrightBrowsers` (J1, 2026-10-10).** The plan names only the install task, but `lifecycle.md`
must teach codegen and show-trace through `com.microsoft.playwright.CLI`. Readings: a raw `java -cp …`
command line, overriding the install task's args (misleading), or the generic task from Playwright's own
Gradle docs (chosen): `./gradlew playwright --args="codegen --target java …"`. **Cost:** one more task in
the build file.

**D29 — `BaseTest` has exactly one catch: `keepScreenshot` catches `PlaywrightException`, logs it with
`System.Logger` and a message template, and continues (J1, 2026-10-10).** This settles `aJ` D47. Readings:
the old Java rule "no catch in `@AfterMethod`" (a crashed page then fails the hook, and TestNG's default
`configfailurepolicy=skip` skips every remaining test in the class, losing the trace and video too), or
CLAUDE.md rule. `System.Logger` avoids adding an SLF4J pin. **Cost:** a missing screenshot shows only as a
log line; the test's own failure still reports.

**D30 — The .NET writer ships an eighth asset, `HomePage.cs`, and `LoginPage.cs` nests `SignInForm` and the
`Credentials` record (N1, 2026-10-10).** §3.1 lists seven .NET assets. As in D23 and D27, the success journey
needs a landing page to assert on without a raw `Page` call in the test. Readings: fold the landing page into
`LoginPage.cs` (rejected: one type per file), or an eighth file (chosen); `SignInForm` and `Credentials` as
files of their own (rejected: only the sign-in screen uses them), or nested (chosen). **Cost:** none for G1,
which compiles every `.cs` asset.

**D31 — The .NET `BaseTest` has no catch, and its teardown stops the trace before it takes the screenshot
(N1, 2026-10-10).** Readings: D29's narrow, logged catch around the screenshot (rejected: D29 is earned by
TestNG's `configfailurepolicy=skip`; NUnit records a teardown exception on that test only, still runs the
base teardowns, and gives the next test a fresh browser — and a logged catch would need a logger the
project does not otherwise have), or no catch with the trace saved first (chosen). **Cost:** when the page
has crashed, the screenshot throws and that test's video is lost; its trace is kept.

**D32 — .NET launch arguments live in a `.runsettings`, never in a per-class `LaunchOptionsAsync()` override
(N1, 2026-10-10).** `BrowserTest` registers the browser as a per-worker service under one name, so the
first fixture on a worker launches it and later fixtures reuse it whatever they override (v1.63.0
`BrowserService.cs`, `WorkerAwareTest.cs`). Readings: a `LaunchOptionsAsync()` override on the class that
needs a flag (unreliable under parallel workers), or a dedicated `.runsettings` with
`<LaunchOptions><Args>['--flag']</Args></LaunchOptions>` and its own `dotnet test` run (chosen). This
settles A1's trap for `WebMcpTests.cs`. **Cost:** a WebMCP or other flagged suite is a second run, with a
filter that keeps its tests out of the main run.

**D33 — The .NET signed-in state is `<WorkDirectory>/auth-user.json` (N1, 2026-10-10).** Readings: the old
`playwright/.auth/user.json` relative to the current directory (rejected: `StorageStateAsync` does not create
folders, and the current directory under `dotnet test` is not guaranteed), a `.auth/` folder created first
(one more line in `AuthSetup`), or a file directly in NUnit's work directory, which always exists (chosen).
It sits under `bin/`, so it is never committed. **Cost:** none.

**D34 — `ui-project-setup` names the UI project `UiTests`, builds it from the writer's assets, and drops the
`allure` dotnet tool (N1, 2026-10-10).** The assets are `UiTests.csproj`, and the CI references and
`bdd-project-scaffold` already use `UiTests`; `dotnet new nunit` writes inline versions that fail restore
under CPM (NU1008); and NuGet has no `allure` package (`dotnet tool install allure` fails). Readings: keep
`PlaywrightTests` and `dotnet new nunit` and patch the csproj (two names for one project), or `UiTests`
from the assets (chosen). **Cost:** `api-project-setup`, `performance-project-setup` and
`mobile-project-setup` still say `PlaywrightTests` and two of them install the `allure` tool, until M3
(mobile) and G1 (the other two) reconcile them.

**D35 — TS quarantine is a command-line filter on the canonical config's projects, not two extra projects
(T2, 2026-10-10).** The old `flaky-test-quarantine` added `gate` and `quarantine` projects (with
`retries: 3` on the second). Readings: keep those projects in the config (rejected: the config asset is
T1's, its `setup` dependency would have to be repeated on both, and the quarantine retries break D7), or
run the gate with `--grep-invert @flaky` and the quarantine lane as a separate, non-gating job with
`--grep @flaky` (chosen). It must be a separate job because each Playwright run cleans `test-results/` at
its start. **Cost:** every TS CI reference's UI command carries `--grep-invert @flaky`.

**D36 — The TS GitHub Actions Allure publish generates the report with the pinned CLI instead of
`simple-elf/allure-report-action` (T2, 2026-10-10).** Readings: keep the action (it bundles its own Allure
version, a second, unpinned CLI next to `ci-conventions`' one), or `npm i -g allure-commandline@2.46.1` plus
`actions/setup-java@v5`, then `peaceiris/actions-gh-pages` (chosen). **Cost:** one more step, and the
action's per-run `keep_reports` folders are gone; `gh-pages` holds the latest report with its trend
history.

**D37 — The merged `playwright-report/` is uploaded whenever `merge-reports` runs; `test-results/` is the
failure-only upload (T2, 2026-10-10).** T2's prompt says "on failure, upload `test-results/` and
`playwright-report/`", but on CI the config writes no `html` reporter, so `playwright-report/` exists only
after the merge job. Readings: upload the merged report only when a shard failed (a green run has no HTML
report), or upload it from the merge job on every run (chosen; under `retain-on-failure` a green run's
report carries no traces or videos). GitLab has one `artifacts:` block per job, so its `e2e` job carries
`test-results/` on every run; it only holds evidence for failed tests plus `junit.xml`. **Cost:** a small
HTML artifact on green runs, kept 14 days.

## Answered questions (2026-10-10)

**O1 — Which Playwright version per stack: 1.64 for Node only; Java and .NET follow when their packages
publish (the user).**

**O2 — What "mobile plugin" means: the `qa-mobile-*` lane inside the three qa plugins.** No standalone
mobile plugin exists, and the React Native drafts (now `mobile/react-native/`, plan 002) are out of scope (`aM` §0).

**O3 — Mobile scope: a full Appium-lane audit and upgrade (the user).**

**O4 — allure-java 3.0: migrate in this plan, in every Java skill (the user; D12).**

**O5 — `mobile-project-setup` for Java and TS: in this plan (the user; D20, S1).**

**O6 — `playwright-cli`: document it alongside Playwright MCP; MCP stays primary (the user; D13).**

**O7 — NUnit: stay on 4.x (the user; D18).**

**O8 — Maestro: add a lane to `qa-mobile-typescript` in this plan (the user; D22, X1).** This also answers
plan 002's Q3 from the QA side.

**O9 — Appium primary lane: the newest client majors, with the previous majors as fallback (the user; D17).**

## Open questions

None. All were answered on 2026-10-10 (O4–O9).

## 8. Tasks

### H1 — Register Playwright MCP and appium-mcp the way the agents expect

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** `claude mcp get playwright` shows `--caps=testing,storage,devtools`, and `claude mcp get
appium-mcp` shows `SCREENSHOTS_DIR`. `playwright-cli --version` prints a version. A new session lists
`mcp__playwright__browser_generate_locator` and `mcp__playwright__browser_start_video`.
**Depends on:** —
**Budget:** none (four commands).
**Gate: none** — nothing to build.

- Run §5.4's commands.
- **Not in H1:** anything in the repo. Every task below runs without H1. Only live use of the upgraded
  agents needs it.

### T1 — TypeScript writer: Playwright 1.64, locators with `within()`, assertions, config, mobile web

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/typescript/skills/ui-test-author/playwright` has §3.1's TypeScript file set on
Playwright 1.64, with a SKILL.md ≤ 16,000 chars and compilable assets. `ui-test-author/review` and
`page-object-design` agree with it.
**Depends on:** —
**Budget:** ~130k:
- Floor (system, both CLAUDE.md files) ~28k.
- This plan's §1–§4, Decisions and T1 ~14k.
- The five files it rewrites ~17k.
- Research ~22k: `playwright-releases.md` §(b) 1.51–1.64, §(c), §(d), §(e); `playwright-evidence.md` §1.1 and §11.1.
- Audit `aTS` §2.1–§2.4, §2.6 and §3 ~8k.
- Writes ~28k.
- Tool overhead ~13k.

**Gate: none** — this plan gates once, in G1. Do not run `tsc`, `npx playwright`,
`tools/token-audit.py` or any check script.

- Rewrite `SKILL.md` to §3.1. It holds the §2.1/§2.2 TS versions table and the rules (ladder, page
  objects, tests). Move every code sample into `assets/`.
- Write `references/locators.md`, `references/assertions.md`, `references/config-and-fixtures.md` and
  `references/emulation-and-mobile-web.md` per §3.1.
- Write `assets/` per §3.1:
  - `playwright.config.ts`: retries per D7, `forbidOnly`, `fullyParallel`, reporters (local `html`; CI
    `blob` + `junit` + `allure-playwright` with `resultsDir`), `use.baseURL` from `BASE_URL`,
    `testIdAttribute`, R7 evidence defaults, `updateSnapshots: process.env.CI ? 'none' : 'missing'`, a
    `setup` project with `dependencies`.
  - `fixtures.ts`: page-object fixtures, plus an API-seeded record fixture that deletes the record in
    teardown.
  - `auth.setup.ts` and `LoginPage.ts`. `LoginPage.ts` exposes intent and scopes a component with
    `within()`.
  - `login.spec.ts`, with `Should_X_When_Y` names and `{ tag }`.
- `ui-test-author/review/SKILL.md`:
  - Fix `test.each` (`aTS` C2): the pattern is one generated `test()` per row.
  - Invert the BasePage rows to flag an unearned base class (L9).
  - Add rows for an unscoped text locator that matches many, positional `nth`/`first`, `:visible`,
    page-level selector APIs, one-shot reads, trace/video not `retain-on-failure`, `test.use({ recordHar })`
    and floating Allure promises.
  - Bring it from 16,968 to ≤ 16,000 chars.
- `page-object-design/SKILL.md`:
  - Keep the design rule (a component takes its parent `Locator`) and link the mechanics to
    `references/locators.md`.
  - Align the locator order with the ladder (`aTS` L10).
  - A BasePage only on the third real sharer.
- `ui-test-author/selenium/SKILL.md`: only the test-id line. `data-testid` is the default, and a
  `data-test` project sets the attribute (`aTS` L10).
- Apply R1–R6 to every file touched. Fix `aTS` C1, C12, C28 and L11–L13 where they sit in these files.
- **Not in T1:**
  - the `evidence-capture` skill (T2; T1's config carries R7 values without prose about them);
  - `page-objects-from-url` and agent tool grants (A1);
  - visual, a11y and network (T3);
  - every other TS skill (T4);
  - CI and reporting (T2).
- **As built (2026-10-10):**
  - Landed: `ui-test-author/playwright/SKILL.md` (12,672 chars; the Versions table is the only pin),
    four references (`locators.md` 9,877 · `assertions.md` 6,905 · `config-and-fixtures.md` 10,103 ·
    `emulation-and-mobile-web.md` 5,668) and six assets. `ui-test-author/review/SKILL.md` went from
    17,453 to 14,902 chars, leaving ~1.1k for M1's and X1's rows. `page-object-design/SKILL.md` 12,913.
  - Differed from the plan: a sixth asset `HomePage.ts` (D23); `authFile` is exported by `fixtures.ts`
    and imported by the config at runtime (D24); the Selenium SauceDemo samples keep their kebab
    `data-test` values (D25). `expectLoaded()` is now optional in the writer rules, and the review row
    "`expectLoaded()` exists on every page object" is gone: it contradicted the blocker row for `expect`
    in page objects.
  - Names assigned: test ids `Login.Form`, `Login.Email`, `Login.Password`, `Login.Submit`,
    `Home.Greeting`; fixtures `loginPage`, `homePage`, `testUser` (from `E2E_USER` / `E2E_PASSWORD`,
    throws when unset), `seededUser` (`POST /api/users` → exact 201, teardown `DELETE` → exact 204);
    component `SignInForm`; CI junit at `test-results/junit.xml`. The config leaves `testDir` at its
    default, so the flat copy in §6.3 finds the specs.
  - Left for later tasks: the Appium review rows (`driver.reset()`, "Appium 2.x") for M1. The writer
    and its references already link `qa/typescript/skills/evidence-capture`, which T2 creates.
  - Built, unverified (Gate: none): nothing compiled or ran. The config → `fixtures.ts` runtime import
    is unproven until G1's `npx playwright test --list`.
  - Proof: `within()` at `qa/typescript/skills/ui-test-author/playwright/assets/LoginPage.ts:33`;
    `retries: 0`, junit, `updateSnapshots`, `testIdAttribute`, `dependencies` at
    `assets/playwright.config.ts:9,13,17,20,30`; exact statuses at `assets/fixtures.ts:38,44`; `{ tag }`
    at `assets/login.spec.ts:3,15`. Review rows `test.each` → `review/SKILL.md:77`, unearned base `:79`,
    page-level selector APIs `:90`, `:visible` `:93`, `recordHar` `:110`, Allure promises `:111`.
    Third-sharer rule at `page-object-design/SKILL.md:57`.

### J1 — Java writer: Playwright 1.63, one parallel-safe `BaseTest`, locators, assertions, emulation

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/java/skills/ui-test-author/playwright` has §3.1's Java file set on Playwright 1.63.
One `BaseTest` follows R7/R8, and the assets compile in principle (G1 proves it). `ui-test-author/review`
and `page-object-design` agree with it.
**Depends on:** —
**Budget:** ~135k:
- Floor ~28k; plan §1–§4, Decisions and J1 ~14k.
- The four files it rewrites ~16k.
- Research ~22k: `playwright-releases.md` §(b), §(c), §(d), §(e); `playwright-evidence.md` §1.1, §4.1, §5.2 and §11.2.
- Audit `aJ` §2 and §3 (blockers and majors) ~10k.
- Writes ~30k; overhead ~15k.

**Gate: none** — this plan gates once, in G1. Do not run `gradle`, `mvn`, `javac`,
`tools/token-audit.py` or any check script.

- Rewrite `SKILL.md` to §3.1, with the Java §2 versions table. Gradle Kotlin DSL is primary.
- `assets/`:
  - `build.gradle.kts`: the §2 pins, plus an `installPlaywrightBrowsers` `JavaExec` task
    (`mainClass = "com.microsoft.playwright.CLI"`, `args("install", "--with-deps", "chromium")`). The
    `test` task sets env `PLAYWRIGHT_JAVA_SRC=src/test/java` and uses TestNG with `testng.xml`.
  - `settings.gradle.kts`.
  - `testng.xml`, with `parallel="classes"`.
  - `BaseTest.java`, per R8 and `playwright-evidence.md` §11.2, on allure-testng 3.0:
    `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`. It sets
    `setBaseURL` from `BASE_URL`, reads `HEADED`, exposes `launchOptions()`, and holds the storage-state
    option. Check the Allure Gradle plugin version that supports allure-java 3.0 on the Gradle Plugin
    Portal today.
  - `LoginPage.java` (`private final Locator` fields, intent methods, a scoped component via
    `parent.locator(child)`) and `LoginTest.java`.
- `references/lifecycle.md`:
  - Why instance fields plus `parallel="classes"`: Playwright Java is not thread-safe.
  - Hook order: evidence, then `context.close()`, then `video.saveAs`/`delete`.
  - Data providers are not parallel. Every Java skill extends this `BaseTest` (J3/J4 switch them).
  - Codegen via `com.microsoft.playwright.CLI` with `--target java`. There is no TestNG target, so say so.
  - Show-trace.
- `references/locators.md` (with the §2.3 `within` lane), `references/assertions.md` and
  `references/emulation-and-mobile-web.md`:
  - Assertions: Java has no message parameter, so use `describe()` and AssertJ for non-locator values.
    Per-assertion timeouts use `LocatorAssertions.IsVisibleOptions().setTimeout(...)`. Cover
    `setDefaultAssertionTimeout`, `containsClass`, `matchesAriaSnapshot` and `page.waitForCondition`.
  - Emulation: explicit `NewContextOptions`, because Java has no device registry.
- `ui-test-author/review/SKILL.md`: rows for static Playwright fields, `parallel="methods"` with
  Playwright, a missing base URL, `getText()`, `AssertOptions`, `APIResponse` from `waitForResponse`
  (it returns `Response`), page-level selector APIs, and any sleep in a route handler (it stalls the
  dispatcher).
- `page-object-design/SKILL.md`: the design rule plus a link to the mechanics; align the ladder.
- Apply R1–R6. Fix `aJ` D2, D4–D7, D26, D27, D29, D40, D45, D47, D49 and D51 where they sit in these files.
- **Not in J1:** `evidence-capture` (J2); specialized skills switching to `BaseTest` (J3/J4);
  `page-objects-from-url` and agents (A1); reporting/CI (J2).
- **As built (2026-10-10):**
  - Landed: `ui-test-author/playwright/SKILL.md` (15,473 chars; body 14,925; description 486; the Versions
    table is the only pin), four references (`lifecycle.md` 11.4k · `locators.md` 10.1k · `assertions.md`
    8.1k · `emulation-and-mobile-web.md` 6.4k) and nine assets. `ui-test-author/review/SKILL.md` went from
    16,210 to 15,636 chars, leaving ~360 for M2 (replace Appium rows, do not add). `page-object-design/SKILL.md`
    13,052.
  - Checked live today: Allure Gradle plugin **4.3.0** (Gradle Plugin Portal, 2026-09-17) is the first with
    "Support Allure Java 3"; allure-java 3 is opted into with `allure { adapter { allureJavaVersion.set("3.0.0") } }`
    (the plugin's default stays 2.35.5), and allure-testng 3 needs TestNG ≥ 7.10. testng.org: *"parallel="classes":
    TestNG will run all the methods in the same class in the same thread"*, and `@Before…` run highest superclass
    first, `@After…` in reverse. Every Java API in the assets and references was checked against the
    playwright-java v1.63.0 sources (no `within`, `getByRef` or `setRecordVideoFps` in 1.63) and allure-java
    3.0.0 (`Allure.attachment(String, String, InputStream, AttachmentOptions)`, `io.qameta.allure.AttachmentOptions`).
    The Pixel 5 values in the emulation reference are Playwright's v1.63.0 descriptor
    (`packages/isomorphic/deviceDescriptorsSource.json`).
  - Differed from the plan: storage state and emulation ride on one `contextOptions()` hook (D26); a seventh
    asset `HomePage.java` and a nested `LoginPage.SignInForm` component (D27); a second `JavaExec` task
    `playwright` for codegen and show-trace (D28); one narrow, logged catch in `BaseTest` (D29). `AuthSetup`
    (the `@BeforeSuite` that writes `build/.auth/user.json`) is a `lifecycle.md` §6 snippet, not an asset.
    `testng.xml` sits at the project root (`useTestNG { suites("testng.xml") }`), not under
    `src/test/resources`.
  - Names assigned: packages `com.example.uitests.{support,pages,tests}`; `BaseTest` hooks
    `launchOptions()`, `contextOptions()`, `requiredEnv(name)`, `protected Page page` (context is private;
    `page.context()` reaches it); raw videos in `build/playwright-videos/` (deleted per test), kept evidence
    in `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`; trace attached as
    `application/vnd.allure.playwright-trace`; test ids `Login.Form`, `Login.Email`, `Login.Password`,
    `Login.Submit`, `Home.Greeting` (same as T1); env `BASE_URL` (required), `HEADED`, `E2E_USER`, `E2E_PASSWORD`.
  - Built, unverified (Gate: none): nothing compiled or ran. `BaseTest` throws when `BASE_URL` is unset, so
    G1's evidence smoke must set it.
  - Proof: instance fields and hooks at `assets/BaseTest.java:30,35,39`; test-id attribute and `HEADED` at
    `:54-56`; `setBaseURL` at `:62`; evidence → `context.close()` → `saveAs` → `delete` at `:77,82,113,86`;
    the one catch at `:98`; Allure 3 call at `:123`. `parallel="classes"` at `assets/testng.xml:2`. Pins,
    Allure 3 opt-in, `PLAYWRIGHT_JAVA_SRC`, the two `JavaExec` tasks at `assets/build.gradle.kts:3,17,25,33,36,42`.
    `parent.locator(child)` at `assets/LoginPage.java:16`. Review rows: static fields `review/SKILL.md:73`,
    `parallel="methods"` `:74`, base URL `:77`, `getText()` `:80`, `AssertOptions` `:81`, `Response` `:82`,
    page-level selector APIs `:87`, route-handler sleep `:90`. Third-sharer rule at `page-object-design/SKILL.md:57`.

### N1 — .NET writer and scaffold: Playwright 1.63, `BaseTest : PageTest`, runsettings, a working auth fixture

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/dotnet/skills/ui-test-author/playwright` has §3.1's .NET file set on Microsoft.Playwright
1.63, and `ui-project-setup` scaffolds the same assets. That means a composed `ContextOptions()` with
`BaseURL`, R7 failure evidence, a `.runsettings`, and an auth `[SetUpFixture]` in the root test
namespace. `ui-test-author/review` and `page-object-design` agree with it.
**Depends on:** —
**Budget:** ~140k:
- Floor ~28k; plan §1–§4, Decisions and N1 ~14k.
- Files ~24k: `ui-test-author/playwright`, `review`, `page-object-design`, `ui-project-setup`.
- Research ~22k: `playwright-releases.md` §(b)–§(e); `playwright-evidence.md` §1.1, §4.1, §5.2 and §11.3.
- Audit `aN` §0, §2, §3a–§3c ~12k.
- Writes ~28k; overhead ~12k.

**Gate: none** — this plan gates once, in G1. Do not run `dotnet build`, `dotnet test`,
`tools/token-audit.py` or any check script.

- Rewrite `SKILL.md` to §3.1, with the .NET §2 table.
- `assets/`:
  - `Directory.Packages.props` (CPM with the §2 pins; NUnit 4.x).
  - `UiTests.csproj`: no inline `Version=`, `net10.0`, and only `Microsoft.Playwright.NUnit`.
  - `ui.runsettings`: `BrowserName`, `LaunchOptions` (`Headless`), `ExpectTimeout`, `TestIdAttribute`.
  - `BaseTest.cs`, per R8 and `playwright-evidence.md` §11.3. It sets `BaseURL` from `BASE_URL`, has
    `[AllureNUnit]`, and uses `Page.Video.PathAsync()` (not `GetPathAsync`).
  - `AuthSetup.cs`: a root-namespace `[SetUpFixture]`, `await using` for the browser, the browser taken
    from settings.
  - `LoginPage.cs` and `LoginTests.cs`.
- `references/lifecycle.md`:
  - The base classes: `PageTest`, `ContextTest`, `BrowserTest`, `PlaywrightTest`.
  - NUnit SetUp/TearDown order.
  - `ParallelScope.Self` is the only supported scope.
  - MSTest/xUnit/xUnit.v3 packages exist; this library covers NUnit.
  - Headed and debug switches: `HEADED=1`, `-- Playwright.LaunchOptions.Headless=false`, `PWDEBUG`.
  - Codegen (`--target csharp-nunit`) and show-trace via `pwsh bin/Debug/net10.0/playwright.ps1` or
    trace.playwright.dev.
  - Browser install via `pwsh` or `dotnet tool install --global PowerShell`.
- `references/locators.md` (with the §2.3 `Within` lane), `references/assertions.md` (`Expect(locator,
  "message")` 1.60, the accessible/role/class/aria assertions, `Assert.ThrowsAsync`) and
  `references/emulation-and-mobile-web.md` (`Playwright.Devices[...]`, `Page.Clock`).
- `ui-project-setup/SKILL.md`:
  - The CPM table re-pinned to §2. Drop `Microsoft.Playwright.CLI`, which is legacy.
  - The `.runsettings`, the base fixture and the Dockerfile from `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`.
  - `show-trace` via `pwsh`. Fix the `Applitools.Playwright` name to `Eyes.Playwright` (line 40).
- `ui-test-author/review/SKILL.md`: rows for a missing `BaseURL`, `ContextOptions()` returning `new()`,
  a SetUpFixture outside the tests' namespace, Selenium `.Text`, `Assert.Throws` on async code, inline
  `Version=` under CPM, and `Playwright.CreateAsync` in a test or `[SetUp]`.
- `page-object-design/SKILL.md`: the design rule plus the link; `.runsettings` replaces
  `playwright.config.ts` (`aN` D-26); no seeding in `[OneTimeSetUp]` (D-27).
- Apply R1–R6. Fix `aN` T4, T5, D-01, D-02, D-09, D-14–D-17 and D-29–D-30 where they sit in these files.
- **Not in N1:** the `standards-audit` checklist (N4); `evidence-capture` and CI (N2); agents (A1/N2).
- **As built (2026-10-10):**
  - Landed: `ui-test-author/playwright/SKILL.md` (15,625 chars; description 489; the Versions table is the
    only pin), four references (`lifecycle.md` 14.6k · `locators.md` 10.6k · `assertions.md` 9.8k ·
    `emulation-and-mobile-web.md` 7.0k) and eight assets. `ui-test-author/review/SKILL.md` went from 17,123
    to 15,558 chars, leaving ~440 for M3 (replace the Appium rows, do not add). `page-object-design/SKILL.md`
    13,822; `ui-project-setup/SKILL.md` 14,260.
  - Checked live today, against `microsoft/playwright-dotnet` v1.63.0 sources: `ContextTest.ContextOptions()`
    returns `Locale = "en-US"`, `ColorScheme = Light`; `BrowserTest.BrowserTearDown` closes contexts only when
    `TestOk()`; `WorkerAwareTest.WorkerTeardown` disposes the worker's browser on failure;
    `PlaywrightSettingsXml` reads only `BrowserName`, `LaunchOptions`, `ExpectTimeout`, `TestIdAttribute`
    (a top-level `<Headless>` or `<Shard>` prints "not implemented"; `LaunchOptions` children parse by
    reflection, `Args` as a JSON array); `HEADED=1` and `BROWSER` are read by `PlaywrightSettingsProvider`;
    the browser is a per-worker service registered once under `"Browser"`; `PlaywrightTest` has
    `Expect(ILocator, string)`; `ILocator.Visible`, `ContentFrame` and `IFrameLocator.Owner` are properties;
    `NormalizeAsync()` returns `Task<ILocator>`; `IVideo.PathAsync()`; `StorageStateAsync` does **not**
    create folders (screenshots and artifacts do). NUnit 4.6.1: `[Parallelizable]` is `Inherited = true`
    and fixture attributes are read with `inherit: true`; each inheritance level's teardown catches its own
    exception. Allure.NUnit 2.15.0: `Allure.NUnit.AllureNUnitAttribute`, `Allure.NUnit.Attributes.AllureFeature`,
    `AllureApi.AddAttachment(name, type, path)`. NuGet today: NUnit 4.6.1, NUnit3TestAdapter 6.3.1 (net8+,
    runs NUnit 4), Microsoft.NET.Test.Sdk 18.10.1, Selenium.WebDriver 4.51.0; there is **no** `allure`
    dotnet tool (flat-container 404).
  - Differed from the plan: an eighth asset `HomePage.cs`, and `LoginPage.cs` nests `SignInForm` and the
    `Credentials` record (D30); `BaseTest` has no catch and stops the trace before the screenshot (D31);
    launch arguments live in a `.runsettings`, not a per-class override (D32); the signed-in state is
    `<WorkDirectory>/auth-user.json` (D33); `ui-project-setup` names the project `UiTests`, copies the
    writer's assets instead of `dotnet new nunit`, and drops the nonexistent `allure` dotnet tool (D34).
  - Names assigned: root namespace `Example.UiTests` (`AuthSetup`), `Example.UiTests.Support` (`BaseTest`),
    `.Pages`, `.Tests`; `BaseTest.RequiredEnv(name)` (public static), `[SetUp] StartTracing`,
    `[TearDown] KeepEvidenceOnFailure`; evidence `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}`
    with the name sanitized to `[A-Za-z0-9._-]`; raw videos `<WorkDirectory>/playwright-videos/` (deleted per
    test); trace attached as `application/vnd.allure.playwright-trace`; `AuthSetup.UserState`; test ids
    `Login.Form`, `Login.Email`, `Login.Password`, `Login.Submit`, `Home.Greeting` (same as T1/J1); env
    `BASE_URL` (required), `E2E_USER`, `E2E_PASSWORD`, `HEADED`, `BROWSER`.
  - Left for later tasks: the review's Appium rows (M3); `PlaywrightTests` in `api-project-setup:193`,
    `performance-project-setup:136` and `mobile-project-setup:153`, and `dotnet tool install allure` in
    `api-project-setup:39,107` and `mobile-project-setup:110` (M3 and G1 prompts updated); the
    `// TODO: missing data-testid` mandate in step 3 of all three `qa-ui-*` agents' live-page workflow (A1
    prompt updated).
  - Built, unverified (Gate: none): nothing compiled or ran. `BaseTest` throws when `BASE_URL` is unset, and
    `AuthSetup` (root namespace) signs in before every fixture under `Example.UiTests`, so G1's evidence
    smoke must sit outside that namespace or drop `AuthSetup.cs`.
  - Proof: `[AllureNUnit]`, `ParallelScope.Self` at `assets/BaseTest.cs:11-12`; `base.ContextOptions()`,
    `BaseURL`, video folder at `:31-33`; trace stop → screenshot → `CloseAsync` → `SaveAsAsync` →
    `DeleteAsync` at `:75,82,64,89,69`. Root namespace, `[SetUpFixture]`, `await using`, settings browser at
    `assets/AuthSetup.cs:8,10,19`. `parent.Locator(child)` at `assets/LoginPage.cs:15`. `Expect(locator,
    "message")` at `assets/LoginTests.cs:30,40`. `RunSettingsFilePath` and versionless references at
    `assets/UiTests.csproj:7,10-14`; the four keys at `assets/ui.runsettings:4-8`. Review rows: async
    `Assert.Throws` `review/SKILL.md:58`, inline `Version=` `:65`, `CreateAsync` `:74`, base URL `:75`,
    `ContextOptions()` `new()` `:76`, SetUpFixture namespace `:77`, `ParallelScope` `:78`, `.Text` `:82`.
    Third-sharer rule `page-object-design/SKILL.md:57`, no `[OneTimeSetUp]` seeding `:95`, `.runsettings`
    `:130`. `Eyes.Playwright` `ui-project-setup/SKILL.md:39`, Docker image `:40,136`, `RunSettingsFilePath`
    `:119`, `pwsh` show-trace `:165`.

### T2 — TypeScript evidence capture: the new skill, agent wiring, reporting and CI

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/typescript/skills/evidence-capture` (`qa-evidence-capture-typescript`) exists per
§3.2 (except `references/appium.md`). `qa-ui-typescript` and `qa-bdd-typescript` load it per §5.1. The TS
reporting and CI skills use the same evidence modes, paths and Allure import.
**Depends on:** T1 (the config asset whose evidence keys this skill explains).
**Budget:** ~135k:
- Floor ~28k; plan ~12k.
- `playwright-evidence.md` §0–§9 and §11.1 ~18k; `playwright-agent-tooling.md` §7c ~2k.
- T1's `config-and-fixtures.md` + config asset ~5k.
- Agents `qa-ui-typescript.md`, `qa-bdd-typescript.md` ~12k.
- `qa/reporting/typescript` ~8k; `qa/cicd/typescript` ~17k; `ci-conventions` ~2k.
- Audit `aTS` §2.5, D3–D5, C6, C8, C23, C24 and L3–L6 ~5k.
- Writes ~18k; overhead ~8k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test, lint or check script.

- `evidence-capture/SKILL.md` and `references/playwright.md` per §3.2, from `playwright-evidence.md`. Put
  a placeholder line in SKILL.md for `references/appium.md`: "Appium: `references/appium.md`, written by
  M1". The description follows R9. The exploratory-capture section lists the `playwright-cli`
  equivalents of the MCP tools (§3.8).
- Agents:
  - `qa-ui-typescript.md`: Step 1 loads the skill; brownfield Mode A reads the failure trace with
    `npx playwright trace open <zip>` / `actions` / `errors` before changing code (§5.1).
  - `qa-bdd-typescript.md`: Step 4 loads the skill.
  - Do not touch the tool frontmatter (A1).
- `qa/reporting/typescript/skills/test-reports/SKILL.md`:
  - allure-playwright 3 with `resultsDir`, and `import * as allure from 'allure-js-commons'` everywhere
    (`aTS` D3, D4, L6).
  - Awaited attachments. Native Playwright evidence defers to `evidence-capture`.
  - One Allure CLI pin. Check the latest 2.x live and use the same value in `ci-conventions`.
- `qa/reporting/typescript/skills/flaky-test-quarantine/SKILL.md`: defer to `ci-conventions` on retries
  (D7). Detect flakes from Allure history and a nightly `--repeat-each`.
- `qa/cicd/typescript/skills/ci-pipelines/references/{github-actions,gitlab-ci,azure-pipelines}.md`:
  - Use `mcr.microsoft.com/playwright:v1.64.0-noble`, or `npx playwright install --with-deps`. The
    GitHub Action is archived, so stop using it.
  - Blob per shard, then `merge-reports`.
  - Produce a junit report everywhere a junit file is published (`aTS` C23).
  - On failure, upload `test-results/` and `playwright-report/`.
  - Retries 0; trace `retain-on-failure`.
  - The config owner is `ui-test-author/playwright/assets/playwright.config.ts`.
- `qa/cicd/ci-conventions/SKILL.md`:
  - Playwright `--update-snapshots` never runs in CI (`updateSnapshots: 'none'`).
  - One Allure CLI pin. Keep it otherwise unchanged.
- Add `./qa/typescript/skills/evidence-capture` to the `qa-typescript` plugin and a catalog row (R9).
- **Not in T2:** Appium evidence (M1); MCP grants (A1); visual-diff evidence (T3).
- **As built (2026-10-10):**
  - Landed: `evidence-capture/SKILL.md` (12.0k chars; body 11.4k; description 499) and
    `references/playwright.md` (16.5k; §1 screenshots … §11 size and CI). Both agents wired. `test-reports`
    rewritten (body 15.7k), `flaky-test-quarantine` rewritten to D7, `ci-conventions` gained the
    `--update-snapshots` rule and the one Allure pin, and all three TS CI references were rewritten for the
    canonical config. Marketplace entry and one catalog row added.
  - Checked live today: `allure-commandline` npm latest **2.46.1** = allure2 release 2.46.1 (2026-09-03);
    Allure Report 3 is npm `allure` 3.20.1 (named, not pinned). allure-js 3.13.0 sources: `issue(url, name)`
    takes the URL first; `attachment(name, content, options)` accepts `{ contentType }`; allure-vitest's
    reporter registers its setup module itself. Playwright v1.64.0 docs: `outputDir` "is cleaned at the
    start"; blob names are `report-<hash>-<shard>.zip`; the CI examples use `actions/checkout@v6`,
    `setup-node@v6`, `upload-artifact@v5`, `download-artifact@v5`, `setup-java@v5`, a container job with
    `options: --user 1001`, and Azure steps set `CI: 'true'`.
  - Differed from the plan: quarantine by `--grep-invert @flaky` / `--grep @flaky` in separate jobs, not
    config projects (D35); the GitHub Allure publish uses the pinned CLI, not `simple-elf` (D36); the merged
    `playwright-report/` uploads whenever the merge runs and `test-results/` is the failure-only upload
    (D37). T1's junit path `test-results/junit.xml` is kept; every CI reference publishes it, and the config
    asset is unchanged. The WebdriverIO failure hook in `test-reports` (it took two screenshots) is gone;
    WDIO failure evidence now defers to evidence-capture's Appium reference (M1). Beyond the plan, the
    rewritten CI references fix `${{ env.NODE_VERSION }}` in reusable workflows (callers' `env` is not
    inherited) with `node-version-file: .nvmrc`, bump the GitHub actions to the majors the Playwright 1.64
    docs use, add a Java runtime to the GitLab `pages` job, and fetch `BASE_URL` / `E2E_USER` /
    `E2E_PASSWORD` through OIDC in every UI job (T1's setup project needs them).
  - Names assigned: exploratory evidence goes to `evidence/<YYYY-MM-DD>-<topic>/` (explicit filenames;
    MCP auto-names stay in `.playwright-mcp/`); fixtures in the reference are `evidence` (`screenshot(name)`),
    `receipt` (`chapter(title)`, `receipt.webm`) and `networkHar` (auto, `network.har`); CI artifacts
    `blob-report-<n>` (1 day), `test-results-<n>` (failure, 14 days), `playwright-report` (14 days),
    `allure-results-ui-<n>` / `allure-results-e2e-<n>` (30 days); the Allure CLI pin
    `allure-commandline@2.46.1`.
  - Built, unverified (Gate: none): no workflow, pipeline or sample ran. `dorny/test-reporter` parses
    Playwright's junit with `reporter: java-junit` (not run); the GitLab `e2e` job assumes the AWS CLI in the
    Playwright image, as `api-tests` already did with the Node image; whether a screencast's `path` is still
    written when tracing or video already runs a screencast is untested (research §4.3 says only that the
    existing configuration wins). One check did run: `python3 -m json.tool .claude-plugin/marketplace.json`
    (exit 0) after the marketplace edit — G1's §6.1 step 1, run early.
  - Left for later tasks: `import { allure } from 'allure-playwright'` remains in `visual-regression`
    (`percy.md`, `applitools.md`, `playwright-snapshots.md`), `accessibility-testing` (`axe-playwright.md`,
    `lighthouse-ci.md`) — T3 — and `browser-cloud-setup/references/details.md` — T4 (trap added to T4's
    prompt). J2/N2 extend T2's catalog row rather than adding their own (prompts updated).
  - Proof: `name: qa-evidence-capture-typescript` and the Appium placeholder at
    `qa/typescript/skills/evidence-capture/SKILL.md:2,13`; R7 defaults and paths `:59`; exploratory MCP ↔ CLI
    table `:112`; trace reading order `:134`; PII `:151`; stop-before-close `:100` and
    `references/playwright.md:131,155`. Agents: Step 1 `qa/typescript/agents/qa-ui-typescript.md:113`, Mode A
    trace reading `:85`, BDD Step 4 `qa/typescript/agents/qa-bdd-typescript.md:107`. `allure-js-commons`
    import `qa/reporting/typescript/skills/test-reports/SKILL.md:110,144,167`, `resultsDir` / no
    `outputFolder` `:73`, pin `:52,70`. `flaky-test-quarantine/SKILL.md:12,16`. `ci-conventions/SKILL.md:29,78,90`.
    CI: junit `github-actions.md:286`, `gitlab-ci.md:209`, `azure-pipelines.md:148`; failure upload
    `github-actions.md:303`, `azure-pipelines.md:161`, `gitlab-ci.md:207`; merge `github-actions.md:334`,
    `gitlab-ci.md:217`, `azure-pipelines.md:187`; image `gitlab-ci.md:188`, `github-actions.md:348`,
    `azure-pipelines.md:200`; `CI: 'true'` `azure-pipelines.md:139`. Marketplace `.claude-plugin/marketplace.json:383`;
    catalog `docs/skills-catalog.md:60`.

### J2 — Java evidence capture: the new skill, agent wiring, reporting and CI

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/java/skills/evidence-capture` (`qa-evidence-capture-java`) exists per §3.2 (except
`references/appium.md`). `qa-ui-java` and `qa-bdd-java` load it. Java reporting defers to J1's
`BaseTest`, and every Java CI reference runs Playwright UI tests and uploads `build/playwright-artifacts/`.
**Depends on:** J1 (`BaseTest.java`, `build.gradle.kts`).
**Budget:** ~140k:
- Floor ~28k; plan ~12k.
- `playwright-evidence.md` §0–§9 and §11.2 ~18k; agent-tooling §7c ~2k.
- J1's `BaseTest.java`, `build.gradle.kts` and `lifecycle.md` ~6k.
- Agents ~12k; `qa/reporting/java` ~9k; `qa/cicd/java` ~16k.
- Audit `aJ` §2d, D15, D17–D19, D42, D43 and V5 ~5k.
- Writes ~20k; overhead ~12k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- `evidence-capture/SKILL.md` and `references/playwright.md` with Java spellings:
  - Screenshots: `Page.ScreenshotOptions` (mask, animations, caret, style, fullPage, type).
  - Video: `setRecordVideoDir/Size`, with `video.saveAs` after close.
  - Screencast: `page.screencast().start(...)` is `AutoCloseable`. `AnnotatePosition.TOP_RIGHT` is an
    enum, not a string.
  - Tracing: `tracing().start/stop/startChunk/group/startHar`, `setAriaSnapshots`/`setScreenSnapshots`
    (1.63), and `PLAYWRIGHT_JAVA_SRC`.
  - Allure 3.0 attachments: `Allure.attachment(..., AttachmentOptions.withFileExtension(ext))`; a trace
    uses type `application/vnd.allure.playwright-trace`.
  - Show-trace through `com.microsoft.playwright.CLI`, and the `npx playwright trace` CLI when Node is present.
  - The `playwright-cli` equivalents of the MCP capture tools (§3.8).
  - Add the appium placeholder line.
- Agents: `qa-ui-java.md` Step 1 plus brownfield Mode A (show-trace on the failure's zip);
  `qa-bdd-java.md` in its `ui-test-author/playwright` step.
- `qa/reporting/java/skills/test-reports/SKILL.md`:
  - Delete the broken failure attacher (`aJ` D15) and defer to `BaseTest`.
  - Allure 3.0 for the adapter, `@Step` / `Allure.step` and attachments, with one pin set (V5, D12).
  - Check live which report generator reads allure-java 3.0 results: the allure2 commandline or Allure
    Report 3. Pin that one. If it differs from the TS/.NET pin T2 put in `ci-conventions`, update
    `ci-conventions` to a per-stack pin and record it as a dated decision.
- `flaky-test-quarantine`: D7.
- `qa/cicd/java/skills/ci-pipelines/references/{github-actions,gitlab-ci,azure-pipelines}.md`:
  - Run the UI job in `mcr.microsoft.com/playwright/java:v1.63.0-noble`, since visual baselines need the
    same image (D19). Or use `./gradlew installPlaywrightBrowsers`, as J1 defines it.
  - Drop `-Pheadless`.
  - Upload `build/playwright-artifacts/` on failure.
  - Add a Playwright-for-Java UI job to Azure Pipelines (`aJ` D18).
- Add `./qa/java/skills/evidence-capture` to `qa-java` and a catalog row.
- **Not in J2:** Appium (M2); MCP grants (A1); visual diffs (J3).

### N2 — .NET evidence capture: the new skill, agent wiring, reporting and CI with real sharding

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/dotnet/skills/evidence-capture` (`qa-evidence-capture-dotnet`) exists per §3.2
(except `references/appium.md`). `qa-ui-dotnet` and `qa-bdd-dotnet` load it. .NET reporting defers to
N1's `BaseTest`. The .NET CI references shard with NUnit filters, run in the 1.63 image and upload
`playwright-artifacts/`.
**Depends on:** N1 (`BaseTest.cs`, `ui.runsettings`).
**Budget:** ~140k:
- Floor ~28k; plan ~12k.
- `playwright-evidence.md` §0–§9 and §11.3 ~18k.
- N1's `BaseTest.cs` + `lifecycle.md` ~5k.
- Agents ~10k; `qa/reporting/dotnet` ~8k; `qa/cicd/dotnet` ~17k.
- Audit `aN` T2, T6, C-04, C-05, C-08, D-13, D-31 and §3f ~6k.
- Writes ~22k; overhead ~14k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- `evidence-capture/SKILL.md` and `references/playwright.md` with .NET spellings:
  - Screenshots: `PageScreenshotOptions`.
  - Video: `RecordVideoDir/Size`, `Page.Video.PathAsync()` / `SaveAsAsync` / `DeleteAsync` after close.
  - Screencast: `Page.Screencast.StartAsync` returns `IAsyncDisposable`; `AnnotatePosition.TopRight`.
  - Tracing: `StartAsync`, `GroupAsync`, `StartChunkAsync`, `StartHarAsync`.
  - Attachments: `TestContext.AddTestAttachment`, and `AllureApi.AddAttachment(name, type, path)` /
    `AddScreenDiff`.
  - Show-trace via `pwsh` or trace.playwright.dev.
  - The `playwright-cli` equivalents of the MCP capture tools (§3.8).
  - Add the appium placeholder line.
- Agents: `qa-ui-dotnet.md`:
  - Step 0's gate text points at the `BaseTest` asset.
  - Step 1 loads the skill.
  - Brownfield Mode A reads the trace.

  `qa-bdd-dotnet.md` loads the skill in its `ui-test-author/playwright` step.
- `qa/reporting/dotnet/skills/test-reports/SKILL.md`:
  - The `%TEMP%` trace recipe defers to `BaseTest`.
  - Fix the 3-string `AllureApi.AddAttachment` call that treats the body as a path (`aN` §3f); pass
    bytes with an extension.
- `flaky-test-quarantine` (.NET):
  - Stop filing every `TimeoutException` as known-flaky (`aN` D-13); match on the quarantine category.
  - Retries per D7.
- `qa/cicd/dotnet/skills/ci-pipelines/references/{azure-pipelines,github-actions,gitlab-ci}.md`:
  - Replace `-- Playwright.Shard=i/N` with NUnit filter partitioning. A setup step lists the tests once
    (`dotnet test --list-tests`), splits the classes into N groups, and emits one
    `--filter "FullyQualifiedName~A|FullyQualifiedName~B"` per shard. That follows ci-conventions:
    membership is computed once, upstream.
  - Use the `v1.63.0-noble` image; GitLab's `v1.47.0-jammy` is wrong.
  - Upload `bin/<cfg>/net10.0/playwright-artifacts/` on failure.
- Add `./qa/dotnet/skills/evidence-capture` to `qa-dotnet` and a catalog row.
- **Not in N2:** Appium (M3); MCP grants (A1); the `standards-audit` checklist (N4).

### A1 — Agent tooling: Playwright MCP grants, `page-objects-from-url`, and the shared WebMCP skill

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** In all three stacks, `qa-ui-*` and `qa-bdd-*` grant exactly §5.2's list, and
`page-objects-from-url` uses those tools and §5.4's registration. `qa/_shared/webmcp-testing`
(`qa-webmcp-testing-shared`) exists per §3.3 and is loaded in every `qa-ui-*` Step 3.
**Depends on:** J1 (`BaseTest.launchOptions()`), N1 (`BaseTest.cs`, `ui.runsettings`), T1 (the config asset).
**Budget:** ~140k:
- Floor ~28k; plan §3.3, §3.8, §5 and A1 ~11k.
- `webmcp.md` §0–§4, §6 and §8 ~11k; `playwright-agent-tooling.md` §2a, §3, §3a, §5, §7 and §8 ~10k.
- Six agents' frontmatter, POM-workflow and Steps sections ~12k.
- Three `page-objects-from-url` ~12k; three base-test assets ~4k.
- Writes ~26k; overhead ~26k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- The `tools:` frontmatter of `qa-ui-{typescript,java,dotnet}.md` and `qa-bdd-{typescript,java,dotnet}.md`
  is §5.2's list, plus the existing non-MCP tools.
- Each `qa-ui-*` live-page workflow gets a two-sentence prerequisite: §5.4's Playwright registration;
  dynamic `webmcp_*` tools are not granted on purpose. Each loading protocol names
  `qa/_shared/webmcp-testing/` as in scope.
- `page-objects-from-url` ×3:
  - Fix the registration command to §5.4's form.
  - Use `browser_find` for single elements, and hover/press-key/tabs/back for dynamic states.
  - `browser_generate_locator` per ref.
  - A test-id harvest parameterized by the configured attribute, with a note on shadow DOM and iframe
    blind spots (`aTS` C22).
  - Mirror the attribute into code (TS `testIdAttribute`; Java `playwright.selectors().setTestIdAttribute`;
    .NET runsettings `TestIdAttribute`).
  - R2 (no marker) and R3 (PascalCase suggestions).
  - `--no-webmcp` when an MCP server must not expose page tools.
  - The `playwright-cli` route beside the MCP route (§3.8, D13): when to use it (MCP not connected, or a
    long extraction that would flood the context), and the command for each MCP step
    (`playwright-agent-tooling.md` §5, §7a–§7d).
- Each `qa-ui-*` live-page workflow also names the CLI fallback in one sentence. `Bash` is already
  granted, so the frontmatter does not change for it.
- `qa/_shared/webmcp-testing/` per §3.3, from `webmcp.md`:
  - SKILL.md: facts §1–§3, checklist §6 condensed, risks §8.
  - `references/typescript.md`: §4.1–§4.3.
  - `references/java.md` / `dotnet.md`: §4.4 on 1.63, plus the "from 1.64" native form.
  - `assets/webmcp.spec.ts` / `WebMcpTest.java` / `WebMcpTests.cs`.
- Wire Step 3 of each `qa-ui-*` per §5.1.
- Add `./qa/_shared/webmcp-testing` to all three qa plugins, and one catalog row.
- Add a one-line cross-reference in each `qa/<stack>/skills/ai-feature-testing/SKILL.md` "when not" or
  handoff section.
- **Not in A1:** `qa-mobile-*` agents (M1–M3); `qa-security`, which is named as an owner but not edited;
  the `tooling` plugin (named, not edited); `fe-*` / `design-auditor` MCP grants (another plugin).

### T3 — TypeScript visual regression, accessibility and network mocking on 1.64

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/typescript/skills/{visual-regression,accessibility-testing,network-mocking}` and
every reference under them teach Playwright 1.64 correctly. No stale pin, no invalid API, and no sample
that breaks R1–R6.
**Depends on:** T1 (assertions, emulation, config references to link).
**Budget:** ~125k:
- Floor ~28k; plan ~10k.
- The three skills with all references ~41k.
- Research `playwright-evidence.md` §2–§3 and §6 ~6k; `playwright-releases.md` §(d) ~2k.
- Audit `aTS` rows below ~6k.
- Writes ~18k; overhead ~14k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- **Visual:**
  - Docker `v1.64.0-noble` with `--ipc=host` and an in-container `npm ci` (D1).
  - `updateSnapshots` modes, incl. the 1.64 `missing` change and CI `none` (D10).
  - `snapshotPathTemplate`.
  - WebP, and the caveat that WebP gets no Allure diff widget.
  - `page.clock.setFixedTime` for "freeze clocks" (G1).
  - Delete redundant defaults and font waits (C27, L20).
  - Trace `retain-on-failure` (C6).
  - Replace the PDF byte-compare with text or rasterize (C7).
  - Applitools through a fixture, not `try/finally` (C5).
  - Record the Percy "no assertion" exception.
  - Remove the `afterEach` re-attach (C24).
  - Allure import and awaits (D3, C8).
  - Visual runs in the nightly lane (L17).
  - Fixtures, not `new XPage` (L15).
  - Descriptions say "Playwright Test", not "Vitest" (D6).
- **A11y:**
  - `wcag22aa` (D11).
  - Link the native accessible/aria assertions in T1's `assertions.md`.
  - Awaited Allure calls.
  - Incompletes go to `test.info().attach` (C18).
  - Lighthouse uses a worker fixture (C20).
- **Network:**
  - Glob 1.52 (D2).
  - `recordHar` via `contextOptions` or `tracing.startHar` (C3).
  - Await `route.continue` (C14) and type the payloads (C15).
  - `context.route` for popups (C16); `updateContent` naming (C17).
  - `page.requests()`, `consoleMessages()` and `pageErrors()` for "not called" checks.
  - Header/TLS checks via `response.allHeaders()` / `securityDetails()` (D9).
  - The CDP last match (C11); proxy cleanup and an assertion (C25).
  - Cross-references (L23). WebSocket mocking points at `realtime-stream-testing` (L21). URLPattern on
    TS 1.59+.
- `qa-ui-typescript.md` Step 3: the a11y item lists the router skill only (L22).
- **Not in T3:** responsive, realtime and the rest (T4); Java/.NET (J3/N3).

### J3 — Java visual regression (rewritten), accessibility and network mocking on 1.63

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/java/skills/{visual-regression,accessibility-testing,network-mocking}` teach only
APIs that exist in Playwright Java 1.63. Visual regression is screenshot-plus-comparator (D9), and every
sample extends J1's `BaseTest`.
**Depends on:** J1 (`BaseTest`, references).
**Budget:** ~130k:
- Floor ~28k; plan ~10k.
- The three skills ~45k; J1 `BaseTest.java` + `lifecycle.md` ~4k.
- Research `playwright-evidence.md` §1, §2, §6 and §13 ~5k.
- Audit `aJ` D1, D9, D12, D13, D16, D19, D21, D25, D31–D32, D36–D37 and V2 ~6k.
- Writes ~20k; overhead ~12k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- **Visual:**
  - Rewrite `references/playwright-snapshots.md`: `Locator.ScreenshotOptions` (mask, animations, caret,
    style); a baseline store under `src/test/resources/baselines/<os>-<browser>/`; a comparator library
    you verify on Maven Central today (candidate `com.github.romankh3:image-comparison`); the diff
    attached to Allure; baselines made only in `mcr.microsoft.com/playwright/java:v1.63.0-noble`.
  - `SKILL.md` says Java has no screenshot assertion and stops calling this "built-in".
  - Exact Percy/Applitools versions, never Maven `+` (V2); `@AfterMethod` instead of `try/finally` (D12).
  - Fix or drop the PDF example (D16). Gradle paths (D32).
- **A11y:** axe 4.13.0 exact; `BasePlaywrightTest` → `BaseTest`; `if`/println → an attachment (D36);
  the Lighthouse auth limitation stated, public pages only (D13); `wcag22aa`.
- **Network:**
  - Glob 1.52; declare `mockApi` (D9).
  - No `Thread.sleep` in route handlers; use CDP throttling or a server-side delay (D21).
  - The CDP `findFirst` test (D37); `browserName` defined.
  - Cross-references (D31). `page.requests()`; `tracing().startHar()`.
- Every Allure call in these files uses allure-java 3.0 (D12): `Allure.attachment(...)` with
  `AttachmentOptions`.
- **Not in J3:** the remaining Java skills (J4).

### N3 — .NET visual regression (rewritten), accessibility and network mocking on 1.63

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/dotnet/skills/{visual-regression,accessibility-testing,network-mocking}` teach only
APIs that exist in Microsoft.Playwright 1.63. Visual regression is screenshot-plus-comparator (D9), and
every sample derives from N1's `BaseTest`.
**Depends on:** N1.
**Budget:** ~130k:
- Floor ~28k; plan ~10k.
- The three skills ~44k; N1 `BaseTest.cs` + `lifecycle.md` ~4k.
- Research `playwright-evidence.md` §1, §2, §6 and §13 ~5k.
- Audit `aN` T1, T3, D-03, D-05, D-06, D-11, D-18, D-22, D-23, X-01 and §1 row 49 ~6k.
- Writes ~20k; overhead ~13k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- **Visual:**
  - Rewrite `references/playwright-snapshots.md`: `LocatorScreenshotOptions`; a comparer you verify on
    NuGet today (candidates `Verify.Playwright`, `Codeuctivity.ImageSharpCompare`);
    `AllureApi.AddScreenDiff`; baselines only in `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`.
  - `SKILL.md` stops calling this built-in.
  - `Eyes.Playwright`, not `Applitools.Playwright` (T3).
  - `AllureApi.AddGlobalAttachment` / `AddLink` instead of `AddTestAttachment` (D-06).
  - `BaseURL` from config (D-22).
- **A11y:** Deque 4.13.0 exact; Lighthouse via a persistent context and a free port (D-11); drop the
  `pwa` category (D-23).
- **Network:** glob 1.52; the CDP `JsonElement?` payload (D-05); D-18; cross-references (X-01).
- Change ".NET 8" labels to .NET 10 in these files.
- **Not in N3:** the remaining .NET skills (N4).

### T4 — TypeScript: the remaining Playwright-bearing skills

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** These skills teach Playwright 1.64 without a stale pin or an R1–R6 break:
`responsive-testing`, `realtime-stream-testing`, `browser-cloud-setup`, `test-login-tokens`,
`language-testing`, `data-driven-testing`, `production-uptime-checks` (now loaded by `qa-api-typescript`),
`inhouse-framework-conventions`, `email-testing/references/mailpit.md`, `api-test-author/playwright`,
`gherkin-step-code/references/playwright-bdd.md` and `bdd-project-scaffold` (all under `qa/typescript/skills/`).
**Depends on:** T1 (emulation and config references), T2 (evidence skill for the uptime-probe evidence).
**Budget:** ~130k:
- Floor ~28k; plan ~10k.
- The listed files ~62k.
- Audit `aTS` rows below ~6k; research `playwright-releases.md` §(b) 1.61–1.64 ~4k.
- Writes ~12k; overhead ~8k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- **responsive-testing:** data rows, not `if`/`else` (C4); `test.use({ viewport })` (L19); link
  `emulation-and-mobile-web.md`; the cross-reference to React, not Blazor (L20).
- **realtime-stream-testing:** the SSE mock caveat (D13); it owns WebSocket mocking.
- **browser-cloud-setup:** `use.connectOptions` or a worker-scoped `browser` (C9); the version taken from
  `@playwright/test/package.json` (D8); teardown returned from `globalSetup` (C19).
- **test-login-tokens:**
  - A setup project with `baseURL` (L7).
  - The storage-state limits: no `sessionStorage`; `indexedDB: true` (1.51).
  - `context.setStorageState` (1.59).
- **language-testing:** `page.clock` for time-dependent formats.
- **data-driven-testing:** generated tests, with no loops in a test.
- **production-uptime-checks:** evidence on probe failure (it links `evidence-capture`); wire it into
  `qa-api-typescript.md` Step 3 (L8).
- **inhouse-framework-conventions:** locator-based actions (C10).
- **mailpit:** no global wipe (C21).
- **api-test-author/playwright:** no `finally` (L14); request-context cookies (1.64); `failOnStatusCode`,
  `maxRedirects`; `APIResponse.timing()` / `securityDetails()`.
- **playwright-bdd:** Node 24/22 (D7); check the status before parsing (C29).
- **bdd-project-scaffold:** `@playwright/test` 1.64.0, allure-playwright 3.13.0, trace
  `retain-on-failure`, Node 24/22.
- **Not in T4:** Appium lines in `bdd-project-scaffold` and `cucumberjs-appium.md` (M1).

### J4 — Java: the remaining Playwright-bearing skills, and `python-web-testing`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** These skills extend J1's `BaseTest` and teach Playwright Java 1.63 without an R1–R6
break: `responsive-testing`, `realtime-stream-testing`, `browser-cloud-setup`, `test-login-tokens`,
`language-testing`, `data-driven-testing`, `production-uptime-checks` (loaded by `qa-api-java`),
`inhouse-framework-conventions`, the `email-testing` poll helpers, `api-test-author/playwright`,
`gherkin-step-code` and `bdd-project-scaffold`. `qa/_shared/python-web-testing` follows the house wait
rules on Playwright 1.63.0. No allure-java 2.x call is left anywhere in `qa/java/` or `qa/reporting/java/`
(D12).
**Depends on:** J1, J2.
**Budget:** ~145k:
- Floor ~28k; plan ~10k.
- The listed files ~60k; `python-web-testing` ~3k.
- The Allure call sites in the six D12 files, read ±20 lines around each grep hit, ~6k.
- Audit `aJ` rows below ~6k.
- Writes ~16k; overhead ~16k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- **responsive:** D11, D46, D23; `BaseUiTest` → `BaseTest`.
- **realtime:** `WebSocketFrame.text()` (D8).
- **browser-cloud:** `GridWebTestBase` → `BaseTest` with `parallel="classes"` (D3); the installed client
  version (D33).
- **language:** context per method (D10); D35.
- **data-driven:** no `parallel = true` with Playwright (D8).
- **production-uptime:** catch the assertion error type and capture evidence (D39); wire it into
  `qa-api-java.md` Step 3.
- **inhouse:** locator actions (D14).
- **email** (`gmail-imap.md`, `mailpit.md`): Awaitility instead of `Thread.sleep` in poll helpers (D21).
- **api-test-author/playwright:** exact status, not `isOK()` (D27); no HttpComponents for constants (D52).
- **gherkin-step-code:** page objects take `Page`, not `TestContext` (D44).
- **bdd-project-scaffold:** Playwright 1.63.0; drop `cucumber.features` or the selector (D48); Gradle paths (D32).
- **python-web-testing:**
  - `expect(...).to_be_visible()` instead of `networkidle`, `wait_for_timeout` or `wait_for_selector`.
  - Locator APIs; outputs under the project, not `/mnt/user-data/outputs`.
  - `playwright==1.63.0` and `pytest-playwright==0.10.0`.
  - Delete `.DS_Store` (D24, D19).
- **Allure 3.0 sweep (D12):**
  - Every Allure call in the files above uses allure-java 3.0.
  - Then the six files no other task touches: `qa/java/skills/ai-feature-testing/references/deepeval.md`,
    `db-testing/testcontainers/SKILL.md`, `failure-injection-testing/SKILL.md`,
    `feature-flag-testing/SKILL.md`, `security-testing/dependency-scan/SKILL.md` and
    `security-testing/passive-scan/SKILL.md`. Change only the Allure call sites and pins.
  - Finish with `grep -rn "addAttachment\|allure-testng:2\|allure-cucumber7-jvm:2" qa/java qa/reporting/java`.
    It must find no code use outside M2's mobile files. A prose line naming the 2.x API as removed is fine.
- **Not in J4:** Appium lines in `bdd-project-scaffold` (M2); the mobile skills' Allure calls (M2).

### N4 — .NET: the remaining Playwright-bearing skills and the `standards-audit` checklist

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** These skills derive from N1's `BaseTest` and teach Microsoft.Playwright 1.63 without an
R1–R6 break: `responsive-testing`, `realtime-stream-testing`, `browser-cloud-setup`, `test-login-tokens`,
`language-testing`, `data-driven-testing`, `production-uptime-checks` (loaded by `qa-api-dotnet`),
`inhouse-framework-conventions`, `api-test-author/playwright`, `gherkin-step-code`, `bdd-project-scaffold`
and `bdd-reviewer`. `standards-audit/references/conformance-checklist.md` audits for exactly what N1–N3
teach.
**Depends on:** N1, N2, N3.
**Budget:** ~140k:
- Floor ~28k; plan ~10k.
- The listed files ~58k; `standards-audit` ~15k.
- Audit `aN` rows below ~6k.
- Writes ~13k; overhead ~10k.

**Gate: none** — this plan gates once, in G1. Do not run any build, test or check script.

- **responsive:** D-10, C-11.
- **realtime:** frames via `ws.FrameReceived` + `TaskCompletionSource`; `IsClosed` is a property;
  `frame.Text` (D-04).
- **browser-cloud:** no `Playwright.CreateAsync` in `[SetUp]` (C-03).
- **test-login-tokens:** D-21.
- **language:** `PageTest` + `ContextOptions()` + fixture parameters (D-12).
- **data-driven:** `ParallelScope.All` is not for Playwright.
- **production-uptime:** D-20, evidence on failure; wire it into `qa-api-dotnet.md` Step 3.
- **inhouse:** `ToHaveURLAsync(new Regex(...))` (D-07); locators (D-08).
- **api-test-author/playwright:** no `try/finally` (C-06); the review link (C-15).
- **gherkin-step-code:** C-13.
- **bdd-project-scaffold:** 1.63.0 under CPM; `[AfterScenario]` evidence per the evidence skill (D-28).
- **bdd-reviewer:** the C-07 rows.
- **conformance-checklist:** E11 matches R8. Add rows for a missing `BaseURL`, a `ToHaveURLAsync` glob,
  `Playwright.Shard`, the fabricated screenshot API, a package/image version mismatch, and the TODO
  marker (R2 wording) (C-03).
- Change ".NET 8" labels to .NET 10 in these files.
- **Not in N4:** mobile rows of the checklist (M3).

### M1 — TypeScript mobile: Appium 3, WebdriverIO 10, Appium evidence, scoped components

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The TS mobile lane runs on §2.4's primary lane:
- `qa-mobile-typescript` with §5.3's grants;
- `ui-test-author/appium` with `assets/`, `mobile-native-features`, `mobile-screen-explorer`,
  `mobile-screen-objects`, `mobile-app-crawler` and `device-cloud`;
- the Appium lines of `bdd-project-scaffold` and `gherkin-step-code/references/cucumberjs-appium.md`.

`evidence-capture/references/appium.md` exists, and the agent loads it.
**Depends on:** T2 (the `evidence-capture` skill).
**Budget:** ~140k:
- Floor ~28k; plan §2.4, §3.4, §4, §5.3 and M1 ~10k.
- Mobile skills ~35k; agent ~6k.
- `appium.md` §0–§9 (TS columns) ~16k; audit `aM` §2–§6 ~10k.
- Writes ~22k; overhead ~13k.

**Gate: none** — this plan gates once, in G1. Do not run `tsc`, `wdio`, `appium` or any check script.

- **Versions:** the Appium 3 / WDIO 10 primary lane, with 2.x / WDIO 9 as the supported lane (§2.4).
  Capabilities carry the `appium:` prefix. Strict `$` in WDIO 10.
- **Mocha, not Vitest** (`aM` D5). The farm runs through `wdio.conf.ts` plus a service (L6).
  `APPIUM_NODE` on Device Farm (D4). How to check a vendor's Appium version (D17).
- `mobile:` extensions instead of the removed endpoints. Review rows lose `resetApp`/`reset()` (D3).
- Port gestures and WebView switching: `browser.action('pointer')`, WDIO 10 `tap`/`swipe`, and
  `switchContext({ title | url })` (L5).
- **Scoped components:** a lazy parent locator plus a row key, with element-scoped finds first
  (`appium.md` §5). `UiSelector` is deprecated by Google, so it is secondary.
- **Locator ladder per platform:** a React Native `testID` is the iOS `accessibilityIdentifier` and the
  Android resource-id (D6). Match plan 002 §8.5 everywhere except the lines D21 gives plan 002.
- `isElementVisible` returns false on timeout (C8). `setClipboard` takes base64 (C5).
- Remove the agent's `browser.pause` exception (L2). Leave the agent's "scaffold" wording; S1 adds the
  Step 0 behind it (D20).
- Remove the `</content>` leftovers (D15) and the TODO markers (R2).
- `cucumberjs-appium.md` attaches its screenshot (C17).
- `assets/`: `wdio.conf.ts`, plus a base test with an `afterTest` evidence hook (screenshot, page source,
  logcat/syslog, and a recording kept only on failure), a screen object and one test.
- Write `qa/typescript/skills/evidence-capture/references/appium.md` per §3.2. Replace the SKILL.md
  placeholder line with the real link.
- Agent `qa-mobile-typescript.md`:
  - The `tools:` list is §5.3.
  - The appium-mcp prerequisites: embedded drivers; a server only for `remoteServerUrl`;
    `SCREENSHOTS_DIR`; the AI-vision variables; the docs tools need `APPIUM_MCP_DOCS_ENABLED`.
  - Step 1 loads the evidence skill and its Appium reference (§5.1).
  - The description (≤ 650 chars) says Appium 3.
- **Not in M1:** Java/.NET mobile (M2/M3); the shared mobile security skills (`qa-security`'s); line 10 of
  `mobile-screen-explorer` and the agent's "Related agents" section (plan 002 W1, D21).

### M2 — Java mobile: Appium 3, java-client 11, Appium evidence, scoped components

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The Java mobile lane runs on §2.4's primary lane:
- `qa-mobile-java` with §5.3's grants;
- `ui-test-author/appium` with `assets/`, `mobile-native-features`, `mobile-screen-explorer`,
  `mobile-screen-objects`, `mobile-app-crawler` and `device-cloud` (+ references);
- the Appium lines of `bdd-project-scaffold`.

The skills use instance-field drivers (D8), and `evidence-capture/references/appium.md` exists and is loaded.
**Depends on:** J2.
**Budget:** ~140k:
- Floor ~28k; plan ~10k.
- Mobile skills ~36k; agent ~6k.
- `appium.md` §0–§9 (Java columns), §2.4 ~16k; audit `aM` ~10k.
- Writes ~22k; overhead ~12k.

**Gate: none** — this plan gates once, in G1. Do not run `gradle`, `javac`, `appium` or any check script.

- **Versions:** java-client 11.0.0 plus `selenium-support` ≥ 4.50, with 10.x as the supported lane.
  `AppiumDriver` is no longer a `RemoteWebDriver`. No `TouchAction`, no `PageFactory`. The OpenRewrite
  `MigrateToV11` note goes in the migration paragraph.
- Use `UiAutomator2Options` / `XCUITestOptions`.
- Replace `selenium.html5.Location` with `mobile: setGeolocation` (`aM` C2).
- Teardown, not `try/finally` (C3). The presigned upload is implemented, or it throws (C4).
- Instance fields plus `parallel="classes"`, not a static `ThreadLocal` (L4, D8).
- Port gestures and WebView switching via W3C `PointerInput`, `mobile:` gestures and context switching (L5).
- Package `support/nativefeatures` (C15); no commented-out code (C16).
- Intent accessors, not raw elements (L11). `Should_X_When_Y` (L12). One locator-constant style (L13).
  AssertJ for non-Appium assertions (L18).
- Review rows lose `AppiumDriver<MobileElement>`/`resetApp` (D3). Scoped components, the ladder, R2 and
  `</content>` are handled as in M1.
- `assets/`: `build.gradle.kts`, `BaseMobileTest.java` (evidence hooks per `appium.md` §9.1, on
  allure-testng 3.0 as it shows), `AppiumDriverFactory.java`, a screen object and one test.
- Every Allure call in the mobile Java skills uses allure-java 3.0 (D12).
- Write `qa/java/skills/evidence-capture/references/appium.md` and replace the placeholder line.
- Agent `qa-mobile-java.md`: §5.3 tools; the prerequisites as in M1; Step 1 wiring; keep the "scaffold"
  wording for S1 (D20); the description says Appium 3.
- **Not in M2:** TS/.NET mobile; line 10 of `mobile-screen-explorer` and the agent's "Related agents"
  section (plan 002 W1, D21).

### M3 — .NET mobile: Appium 3, Appium.WebDriver 9, Appium evidence, compiling assets

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The .NET mobile lane runs on §2.4's primary lane:
- `qa-mobile-dotnet` with §5.3's grants;
- `mobile-project-setup`, `ui-test-author/appium` (the existing assets fixed to compile),
  `mobile-native-features`, `mobile-screen-explorer`, `mobile-screen-objects`, `mobile-app-crawler` and
  `device-cloud`;
- the mobile rows of the `standards-audit` checklist.

`evidence-capture/references/appium.md` exists and is loaded.
**Depends on:** N2, N4 (the checklist's other rows).
**Budget:** ~145k:
- Floor ~28k; plan ~10k.
- Mobile skills + assets ~45k; agent ~5k.
- `appium.md` §0–§9 (C# columns) ~14k; audit `aM` ~10k.
- Writes ~20k; overhead ~13k.

**Gate: none** — this plan gates once, in G1. Do not run `dotnet build`, `appium` or any check script.

- **Versions:** Appium.WebDriver 9.0.0, which is strong-named, so the whole solution rebuilds. 8.x is the
  supported lane. Use `AppiumOptions` plus `AddAdditionalAppiumOption`. The major does not track Selenium (D12).
- **mobile-project-setup:** Appium 3, UiAutomator2 8.x, XCUITest 12.x, Node 24/22 (D2). `Pages/`, not
  `Screens/` (L8). One platform-selection mechanism (L15).
- **Make the assets compile:**
  - Fix `page_template.cs` (C1) and the `references/details.md` vs asset drift (C13).
  - Add `BaseMobileTest.cs` with the evidence hooks from `appium.md` §9.2.
- The `chromedriver_autodownload` server flag, not a capability (D9). `mobile: scrollGesture` wording (D17).
- Device Farm has no .NET Appium type, so say so (L7). Teardown, not `try/finally` (C3). The upload is
  implemented, or it throws (C4).
- Hardcoded devices go to configuration (C11). No raw `FindElement` in a page (C12). L22 and L23.
- **Checklist:** the mobile rows only. Replace the removed APIs (`aM` D3) and add an evidence-on-failure row.
- ".NET 8" → .NET 10 labels. R2, scoped components, the ladder and `</content>` are handled as in M1.
- Write `qa/dotnet/skills/evidence-capture/references/appium.md` and replace the placeholder line.
- Agent `qa-mobile-dotnet.md`: §5.3 tools; prerequisites; Step 1 wiring; Step 0 says Appium 3; the
  description says Appium 3.
- **Not in M3:** TS/Java mobile; line 10 of `mobile-screen-explorer` and the agent's "Related agents"
  section (plan 002 W1, D21).

### S1 — `mobile-project-setup` for Java and TypeScript, and Step 0 in both mobile agents

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/java/skills/mobile-project-setup` (`qa-mobile-project-setup-java`) and
`qa/typescript/skills/mobile-project-setup` (`qa-mobile-project-setup-typescript`) exist per §3.6, and
`qa-mobile-java` and `qa-mobile-typescript` run them as Step 0.
**Depends on:** M1 and M2 (the assets the setup scaffolds), M3 (the .NET `mobile-project-setup` they mirror).
**Budget:** ~110k:
- Floor ~28k; plan §2.4, §3.4, §3.6, §4, §5.1, D20 and S1 ~9k.
- `qa/dotnet/skills/mobile-project-setup/SKILL.md` as M3 left it ~4k.
- M1's and M2's `ui-test-author/appium/assets/` plus their SKILL.md stack sections ~12k.
- `appium.md` §1, §2.1 and §2.7 ~8k; both agents' Steps tables and descriptions ~4k.
- Writes ~22k; overhead ~23k.

**Gate: none** — this plan gates once, in G1. Do not run `gradle`, `npm`, `appium` or any check script.

- Two SKILL.md files per §3.6, each ≤ 16,000 chars, with an R9 description:
  - **Prerequisites:** Node 24 (22 maintenance), JDK 21 for Java, `ANDROID_HOME`, an emulator image,
    and Xcode with a simulator. Real iOS devices need WDA signing, which is a human step.
  - **Appium 3:** pin `appium@3.8.0`; `appium setup` or `appium driver install uiautomator2` /
    `xcuitest` at §2.4's majors; `appium driver doctor <driver>`; the scoped
    `--allow-insecure <driver>:<feature>` syntax.
  - **Layout.** Java: a Gradle project around M2's `build.gradle.kts` and `testng.xml`
    (`parallel="classes"`), with `pages/`, `support/` and `tests/`. TS: WDIO 10 with Mocha,
    `@wdio/appium-service` and `@wdio/allure-reporter`, around M1's `wdio.conf.ts`.
  - **Configuration:** capabilities from environment variables (`PLATFORM`, `DEVICE_NAME`, `APP_PATH`),
    with one mechanism only.
  - **First smoke:** launch the app and verify the landing screen.
  - `.gitignore` for the R7 artifact paths.
  - **Pointers:** `device-cloud` and the stack's `ci-pipelines`. The §2.4 supported lane gets one
    paragraph.
- `qa-mobile-java.md` and `qa-mobile-typescript.md`: a Step 0 row ("Project scaffold — skip if a project
  exists", `mobile-project-setup`, exit gate: the project compiles, `appium driver doctor` is clean, the
  smoke runs) mirroring `qa-mobile-dotnet.md`. Their existing "scaffold" wording now has a skill behind
  it.
- Add both to their plugins in `.claude-plugin/marketplace.json`, and catalog rows (R9).
- **Not in S1:** the .NET setup skill (M3); device clouds (`device-cloud`); Maestro (X1).

### X1 — A Maestro lane for `qa-mobile-typescript`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `docs/research/003-qa-playwright-appium/maestro.md` records current Maestro facts, each with
a source. `qa/typescript/skills/ui-test-author/maestro` (`qa-ui-test-writer-maestro-typescript`) teaches
them per §3.7. `qa-mobile-typescript` offers it at Step 2, the TS review skill has Maestro rows, and
`evidence-capture` routes Maestro evidence to it.
**Depends on:** M1 (the TS mobile lane and agent), S1 (the agent's Step 0), T2 (`evidence-capture`).
**Budget:** ~130k:
- Floor ~28k; plan §3.7, §4, §5.1, D21, D22 and X1 ~8k.
- Web research (the official Maestro docs and GitHub releases, Expo EAS Workflows docs) ~35k.
- Plan 002 §8.5 ~1k.
- `qa-mobile-typescript.md` Steps/description ~4k; the TS review skill's mobile rows ~3k;
  `evidence-capture/SKILL.md` ~3k.
- Writes ~20k (research ~8k, skill ~10k, assets ~2k); overhead ~28k.

**Gate: none** — this plan gates once, in G1. Do not run `maestro`, emulators or any check script. Web
research is allowed and expected.

- Research first, into `maestro.md`. Mark anything not from a primary source UNVERIFIED. Cover:
  - The current CLI version and how to install it.
  - Flow syntax: `appId`, the `---` header, the core commands (`launchApp`, `tapOn`, `inputText`,
    `assertVisible`, `assertNotVisible`, `scrollUntilVisible`, `extendedWaitUntil`, `runFlow`,
    `runScript`/`evalScript`, `takeScreenshot`, `startRecording`/`stopRecording`, `clearState`).
  - How the `id` selector maps to a React Native `testID` on Android and iOS, against plan 002 §8.5.
  - Waiting without sleeps; env and params; `includeTags`/`excludeTags`; `config.yaml`.
  - Outputs: JUnit format, the test-output and debug-output dirs, failure screenshots and recordings.
  - CI: Maestro Cloud, EAS Workflows' Maestro job, a GitHub Actions emulator job.
  - Maestro Studio.
  - Whether an official Maestro MCP server exists, and its tool names.
  - Any syntax-check or dry-run command, which G1 §6.3 uses.
- The skill per §3.7, with `assets/.maestro/`: one flow, one subflow, `config.yaml`.
- `qa-mobile-typescript.md`:
  - Step 2 offers `ui-test-author/maestro` when the project runs Maestro (§5.1).
  - The description (≤ 650 chars) names Maestro.
  - Step 4 review covers Maestro.
- `qa/typescript/skills/ui-test-author/review/SKILL.md`: Maestro rows — fixed waits, a text selector
  where a test id exists, duplicated steps that belong in a subflow, untagged flows, no `clearState` /
  `launchApp` reset between flows.
- `qa/typescript/skills/evidence-capture/SKILL.md`: one route line, "Maestro → `ui-test-author/maestro`
  § Evidence".
- A Maestro MCP server whose tool names you verified from the official source: add the registration
  and grants as a dated decision, and extend §5's lists so G1's allowlist check knows them. Otherwise
  grant nothing.
- Add the skill to `qa-typescript` in the marketplace, and a catalog row.
- **Not in X1:** Java/.NET (Maestro is a TS-plugin lane); plan 002's React Native dev skills.

### G1 — The gate, the docs reconciliation, and the close-out

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** §6 passes on the whole plan's output:
- the marketplace parses;
- the library check prints `OK`;
- `tools/qa-version-check.py` (new) prints `OK`;
- every asset in §6.3 compiles;
- §6.4's evidence smoke produces trace, video and screenshot for a failing test in all three stacks;
- `tools/token-audit.py` stays within §6.5's limits.

README, CLAUDE.md and the catalog say what landed.
**Depends on:** every task above.
**Budget:** ~145k:
- Floor ~28k; plan §2, §5, §6, D-list and all As-built notes ~18k.
- The 001 §7 script ~3k; the new checker written ~3k.
- Check and build output ~20k; reading and fixing what fails ~35k.
- README/CLAUDE.md/catalog edits ~12k; overhead ~26k.

If fixes run over, keep this block with a `Picking up from:` line.

**Gate (this is the last task, so it carries the plan's only gate, in run order):** §6.1 → §6.2 (write,
then run) → §6.3 → §6.4 → §6.5. Fix what it finds; a failure may belong to any task above.

- Write `tools/qa-version-check.py` per §6.2.
- Run §6 in order and fix every failure at its source file.
- **README.md:** the qa rows for the 3 `evidence-capture` skills, `webmcp-testing`, the 2 new
  `mobile-project-setup` skills and `ui-test-author/maestro`, and the skill counts.
- **CLAUDE.md** version policy: a Playwright line (Node 1.64 / Java·.NET·Python 1.63, and that a
  1.64-only API is never taught on a 1.63 lane) and an Appium line (3 primary / 2 supported;
  java-client 11 / Appium.WebDriver 9 / WebdriverIO 10).
- **docs/skills-catalog.md:** fix `ui-test-author/reviewer` → `review`, `bdd-project-setup` →
  `bdd-project-scaffold`, and the inhouse-conventions row (`aTS` D12, `aM` D16). Check the rows T2, J2,
  N2, A1, S1 and X1 added.
- Rewrite **Status** for the last time. Name what is unverified, at least: no Appium flow ran on a
  device or emulator; no Maestro flow ran; no WebMCP test ran against a site that registers tools; the
  comparators in D9 are recommendations.
- `git mv` this plan to `docs/plans/implemented/`.
- **Not in G1:** new content. If the gate shows a skill is missing a section, write the minimum, and
  record it as a dated decision.

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one session each, opened from Plan Queue. Each block is complete on its own.

- **Gates:** every block except G1 is `Gate: none`. G1 runs §6 once for everything.
- **What no block may do:** create a branch or worktree, push, edit outside its task's paths (R12), or
  run a check that belongs to G1.
- **H1** is the user's. It blocks no task, only live use of the agents.

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| H1 | `human` | **the user** | — | four commands |
| T1 | `docs` | `general-purpose` | — | ~130k |
| J1 | `docs` | `general-purpose` | — | ~135k |
| N1 | `docs` | `general-purpose` | — | ~140k |
| T2 | `docs` | `general-purpose` | T1 | ~135k |
| J2 | `docs` | `general-purpose` | J1 | ~140k |
| N2 | `docs` | `general-purpose` | N1 | ~140k |
| A1 | `docs` | `general-purpose` | T1, J1, N1 | ~140k |
| T3 | `docs` | `general-purpose` | T1 | ~125k |
| J3 | `docs` | `general-purpose` | J1 | ~130k |
| N3 | `docs` | `general-purpose` | N1 | ~130k |
| T4 | `docs` | `general-purpose` | T1, T2 | ~130k |
| J4 | `docs` | `general-purpose` | J1, J2 | ~145k |
| N4 | `docs` | `general-purpose` | N1, N2, N3 | ~140k |
| M1 | `docs` | `general-purpose` | T2 | ~140k |
| M2 | `docs` | `general-purpose` | J2 | ~140k |
| M3 | `docs` | `general-purpose` | N2, N4 | ~145k |
| S1 | `docs` | `general-purpose` | M1, M2, M3 | ~110k |
| X1 | `docs` | `general-purpose` | M1, S1, T2 | ~130k |
| G1 | `docs` | `general-purpose` | all | ~145k |

Landed: T1, J1, N1, T2 (2026-10-10). Every other block is live.

---

### J2 — Java evidence capture: the new skill, agent wiring, reporting and CI (general-purpose, docs)

````
You are `general-purpose`. Task J2 of docs/plans/003-qa-playwright-appium-upgrade.md: create
qa/java/skills/evidence-capture (qa-evidence-capture-java) per §3.2, wire it into qa-ui-java and
qa-bdd-java, and make Java reporting and CI agree with J1's BaseTest.

Read, in this order:
1. CLAUDE.md.
2. The plan: §3.2, §4 (R7, R8, R9), §5.1, Decisions D4, D7, D12, task J2, "Close-out — every task".
3. J1's output: qa/java/skills/ui-test-author/playwright/assets/BaseTest.java, build.gradle.kts and
   references/lifecycle.md.
4. docs/research/003-qa-playwright-appium/playwright-evidence.md §0–§9 and §11.2;
   playwright-agent-tooling.md §7c.
5. qa/java/agents/qa-ui-java.md and qa-bdd-java.md (loading protocol, brownfield Mode A, Steps).
6. qa/reporting/java/skills/{test-reports,flaky-test-quarantine}/SKILL.md;
   qa/cicd/java/skills/ci-pipelines/references/{github-actions,gitlab-ci,azure-pipelines}.md.
7. docs/audits/003-qa-playwright-appium/java.md §2d and rows D15, D17–D19, D42, D43, V5.
8. Optional, for parity: T2's qa/typescript/skills/evidence-capture/SKILL.md (the section set: Versions,
   Who owns what, the three kinds of capture, failure-evidence defaults + paths, deliberate recordings,
   exploratory capture, reading a failure, PII and retention, Rules, Handoffs; the Appium placeholder
   sits under the intro paragraph).

Build:
- evidence-capture/SKILL.md and references/playwright.md with Java spellings:
  - Page.ScreenshotOptions.
  - setRecordVideoDir/Size; video.saveAs after close.
  - page.screencast() as AutoCloseable, with AnnotatePosition.TOP_RIGHT.
  - tracing start/stop/startChunk/group/startHar; setAriaSnapshots/setScreenSnapshots (1.63);
    PLAYWRIGHT_JAVA_SRC.
  - Allure 3.0 attachments (Allure.attachment + AttachmentOptions.withFileExtension; a trace uses type
    application/vnd.allure.playwright-trace).
  - show-trace via com.microsoft.playwright.CLI; the npx playwright trace CLI when Node is present.
  - The playwright-cli equivalents of the MCP capture tools (plan §3.8).
  - The appium placeholder line ("written by M2").
- qa-ui-java.md: Step 1 loads it; brownfield Mode A opens the failure's trace. qa-bdd-java.md: in its
  ui-test-author/playwright step. Leave tools: frontmatter alone (A1).
- test-reports: delete the broken failure attacher and defer to BaseTest. Allure 3.0 adapter, steps and
  attachments, with one pin set. Check live which report generator reads allure-java 3.0 results
  (allure2 commandline or Allure Report 3) and pin it. T2 set the ci-conventions pin to
  `allure-commandline@2.46.1` (allure2 2.46.1, Allure Report 2, installed with
  `npm i -g allure-commandline@2.46.1` on a runner with a Java runtime). If Java needs a different
  generator, make ci-conventions per-stack and record a dated decision.
- flaky-test-quarantine: D7.
- CI references:
  - UI job in mcr.microsoft.com/playwright/java:v1.63.0-noble, or ./gradlew installPlaywrightBrowsers.
  - Drop -Pheadless.
  - Upload build/playwright-artifacts/ on failure.
  - Add a Playwright-for-Java UI job to Azure Pipelines.
- Add ./qa/java/skills/evidence-capture to qa-java in the marketplace. In docs/skills-catalog.md, extend
  the `evidence-capture` row T2 added under **Authoring** (it ends "— typescript (java · dotnet next)")
  to name java, instead of adding a second row.

Traps:
- Raw context.tracing does not record expect() calls (evidence §12.7). Say so; Java has no runner tracing.
- The 1.59 release-note samples pass "top-right" as a string. Java takes the AnnotatePosition enum.
- allure-testng 3.0 (D12): Allure.addAttachment(...) is the 2.x API and is gone. G1's CODE_CHECKS bans it
  in Java code blocks and assets.
- The paths must equal J1's BaseTest (build/playwright-artifacts/<Class>.<method>.*). CI uploads exactly
  that. build/playwright-videos/ holds raw recordings that BaseTest deletes after every test; never
  upload it.
- J1's shape (com.example.uitests.support.BaseTest): the failure hooks are BaseTest's private keep*
  helpers and closeContext; subclasses only override launchOptions() / contextOptions() (plan D26). The
  skill points at that code and adds no second hook. If a default must change (for example
  setAriaSnapshots(true) on the trace), edit BaseTest.java and lifecycle.md §5 in place and record a
  dated decision. BaseTest's one catch (keepScreenshot, plan D29) is the pattern for any capture helper.
- Show-trace runs through J1's `playwright` JavaExec task: ./gradlew playwright --args="show-trace <zip>"
  (plan D28). Headed runs use HEADED=1, not -Dplaywright.headless or -Pheadless.
- Allure Gradle plugin 4.3.0 is in J1's build.gradle.kts with allure { adapter { allureJavaVersion.set("3.0.0") } }.
  Its allure.version selects the report runtime (3.x = Allure Report 3, 2.x = allure-commandline) and is
  left at the plugin default. If you pin the report generator in Gradle, set allure.version there.

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-java): evidence-capture skill, agent wiring, reporting and CI alignment (003 J2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### N2 — .NET evidence capture: the new skill, agent wiring, reporting and CI with real sharding (general-purpose, docs)

````
You are `general-purpose`. Task N2 of docs/plans/003-qa-playwright-appium-upgrade.md: create
qa/dotnet/skills/evidence-capture (qa-evidence-capture-dotnet) per §3.2, wire it into qa-ui-dotnet and
qa-bdd-dotnet, make .NET reporting defer to N1's BaseTest, and replace the no-op CI sharding.

Read, in this order:
1. CLAUDE.md.
2. The plan: §3.2, §4 (R7, R8, R9), §5.1, Decisions D4, D7, task N2, "Close-out — every task".
3. N1's output: qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs, ui.runsettings and
   references/lifecycle.md.
4. docs/research/003-qa-playwright-appium/playwright-evidence.md §0–§9 and §11.3.
5. qa/dotnet/agents/qa-ui-dotnet.md and qa-bdd-dotnet.md (loading protocol, Step 0, Step 1, brownfield
   Mode A).
6. qa/reporting/dotnet/skills/{test-reports,flaky-test-quarantine}/SKILL.md;
   qa/cicd/dotnet/skills/ci-pipelines/references/{azure-pipelines,github-actions,gitlab-ci}.md.
7. docs/audits/003-qa-playwright-appium/dotnet.md rows T2, T6, C-04, C-05, C-08, D-13, D-31, §3f.
8. Optional, for parity: T2's qa/typescript/skills/evidence-capture/SKILL.md (its section set; the Appium
   placeholder sits under the intro paragraph).

Build:
- evidence-capture/SKILL.md and references/playwright.md with .NET spellings:
  - PageScreenshotOptions.
  - RecordVideoDir/Size; Page.Video.PathAsync / SaveAsAsync / DeleteAsync after close.
  - Page.Screencast.StartAsync returns IAsyncDisposable; AnnotatePosition.TopRight.
  - Tracing StartAsync/GroupAsync/StartChunkAsync/StartHarAsync.
  - TestContext.AddTestAttachment, and AllureApi.AddAttachment(name, type, path) / AddScreenDiff.
  - show-trace via pwsh or trace.playwright.dev.
  - The playwright-cli equivalents of the MCP capture tools (plan §3.8).
  - The appium placeholder line ("written by M3").
- qa-ui-dotnet.md: Step 0's gate text points at the BaseTest asset; Step 1 loads the skill; brownfield
  Mode A reads the trace. qa-bdd-dotnet.md loads it in its ui-test-author/playwright step. Leave tools:
  alone (A1).
- test-reports: the %TEMP% recipe defers to BaseTest. Fix AllureApi.AddAttachment("response.json",
  "application/json", body), which treats the third string as a file path: pass UTF-8 bytes and ".json".
- flaky-test-quarantine: match the quarantine category, not TimeoutException (D-13); D7 retries.
- CI references:
  - Delete every `-- Playwright.Shard=i/N`. A setup step runs `dotnet test --list-tests` once, splits
    the test classes into N groups, and emits one `--filter "FullyQualifiedName~A|FullyQualifiedName~B"`
    per shard.
  - mcr.microsoft.com/playwright/dotnet:v1.63.0-noble (no jammy).
  - Upload bin/<cfg>/net10.0/playwright-artifacts/ on failure.
- Add ./qa/dotnet/skills/evidence-capture to qa-dotnet in the marketplace. In docs/skills-catalog.md, extend
  the `evidence-capture` row T2 added under **Authoring** to name dotnet (once J2 has added java, the
  stack list reads "— java · dotnet · typescript"), instead of adding a second row.
- Any Allure report CLI in .NET test-reports or the .NET CI references uses the ci-conventions pin T2 set,
  `allure-commandline@2.46.1` (needs a Java runtime), unless J2 recorded a per-stack split.

Traps:
- Microsoft.Playwright.NUnit has no sharding. The adapter prints "Playwright>Shard is not implemented".
- Filter strings have length limits on some runners. Group by class, not by test, and say so.
- Verify that pwsh exists in the dotnet Playwright image before a CI step relies on it. In the image,
  browsers are preinstalled, so no install step is needed.
- N1's BaseTest already owns the R7 defaults; the skill explains them and never adds a second hook (D4).
  `[SetUp] StartTracing` (screenshots, snapshots, sources); `[TearDown] KeepEvidenceOnFailure`: on
  `TestStatus.Failed` it stops the trace to a path, takes a full-page screenshot, closes the context, then
  `SaveAsAsync`; always `DeleteAsync`. It has no catch (D31). Kept files:
  `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}` (name sanitized to
  `[A-Za-z0-9._-]`; WorkDirectory defaults to bin/<cfg>/net10.0); raw videos in
  `<WorkDirectory>/playwright-videos/`, deleted per test, never uploaded. Attachments go through
  `TestContext.AddTestAttachment(path, name)` and `AllureApi.AddAttachment(name, type, path)`, the trace as
  `application/vnd.allure.playwright-trace`. A deliberate recording or HAR that needs launch flags goes in a
  .runsettings, not a per-class override (D32).
- The UI project is `UiTests` (D34), so CI paths are `UiTests/bin/<cfg>/net10.0/playwright-artifacts/`.
  `AuthSetup` (root namespace) signs in before every fixture, so CI jobs need BASE_URL, E2E_USER and
  E2E_PASSWORD as secrets. `[Parallelizable(ParallelScope.Self)]` sits on BaseTest, so shard by test class.

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-dotnet): evidence-capture skill, agent wiring, reporting, NUnit-filter sharding (003 N2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A1 — Agent tooling: Playwright MCP grants, `page-objects-from-url`, and the shared WebMCP skill (general-purpose, docs)

````
You are `general-purpose`. Task A1 of docs/plans/003-qa-playwright-appium-upgrade.md: put the six
qa-ui-* / qa-bdd-* agents on §5.2's Playwright MCP allowlist, update page-objects-from-url ×3 to those
tools, and create qa/_shared/webmcp-testing (qa-webmcp-testing-shared), loaded in every qa-ui-* Step 3.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.3, §3.3, §4 (R2, R3, R9, R10), §5, Decisions D6, D13, task A1, "Close-out — every task".
3. docs/research/003-qa-playwright-appium/webmcp.md §0–§4, §6, §8; playwright-agent-tooling.md §2a, §3,
   §3a, §5, §7, §8.
4. The frontmatter, live-page POM workflow, loading protocol and Steps table of
   qa/{typescript,java,dotnet}/agents/qa-ui-*.md, plus the frontmatter of qa/{typescript,java,dotnet}/agents/qa-bdd-*.md.
5. qa/{typescript,java,dotnet}/skills/page-objects-from-url/SKILL.md.
6. The launch seams: qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts,
   qa/java/skills/ui-test-author/playwright/assets/BaseTest.java (launchOptions()),
   qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs and ui.runsettings.

Build:
- tools: in the six agents = the existing non-MCP tools + §5.2's list, verbatim.
- Each qa-ui-* POM workflow: a two-sentence prerequisite (§5.4's registration; webmcp_* tools are not
  granted on purpose). Each loading protocol names qa/_shared/webmcp-testing/ as in scope.
- page-objects-from-url ×3:
  - §5.4's registration form.
  - browser_find for one element; hover/press_key/tabs/navigate_back for dynamic states.
  - browser_generate_locator per ref.
  - The test-id harvest parameterized by the attribute, with shadow-DOM and iframe blind spots noted.
  - The attribute mirrored into code (TS testIdAttribute; Java playwright.selectors().setTestIdAttribute;
    .NET runsettings TestIdAttribute).
  - R2 (no marker) and R3 (PascalCase suggestions); --no-webmcp.
  - The playwright-cli route beside the MCP route (plan §3.8, D13): when to use it, and the command for
    each MCP step (playwright-agent-tooling.md §5, §7a–§7d).
- Each qa-ui-* live-page workflow names the CLI fallback in one sentence (Bash is already granted).
- qa/_shared/webmcp-testing/:
  - SKILL.md: webmcp.md §1–§3 facts, a condensed §6 checklist, §8 risks; ≤ 16,000 chars; R9 description.
  - references/typescript.md: native page.webmcp, §4.1–§4.3.
  - references/java.md and dotnet.md: the §4.4 evaluate helper on 1.63, plus the from-1.64 native form.
  - assets/webmcp.spec.ts; WebMcpTest.java (extends BaseTest, overrides launchOptions() to add
    --enable-features=WebMCP); WebMcpTests.cs.
  - WebMcpTest.java: package com.example.uitests.tests (J1's testng.xml scans that package), import
    com.example.uitests.support.BaseTest, override
    `protected BrowserType.LaunchOptions launchOptions()` returning
    `new BrowserType.LaunchOptions().setArgs(List.of("--enable-features=WebMCP"))` — BaseTest stamps the
    headless flag after the hook. Use the protected `page` field (the context is private;
    `page.context()` reaches it). BaseTest requires BASE_URL; navigate relative to it. Name tests
    Should_X_When_Y.
  - WebMcpTests.cs: namespace Example.UiTests.Tests, `using Example.UiTests.Support;`, derives from
    BaseTest, uses the inherited `Page` and `Expect(...)`. The launch arg cannot be a per-class override
    (D32): ship `assets/webmcp.runsettings` repeating N1's four keys plus
    `<LaunchOptions><Headless>true</Headless><Args>['--enable-features=WebMCP']</Args></LaunchOptions>`
    (the adapter parses Args as a JSON array), tag the fixture `[Category("webmcp")]`, and document the two
    runs: `dotnet test --settings webmcp.runsettings --filter TestCategory=webmcp` and the main run with
    `--filter TestCategory!=webmcp`. `--settings` replaces the csproj's RunSettingsFilePath for that run.
    The root-namespace AuthSetup signs in before this fixture too, so the run needs E2E_USER/E2E_PASSWORD.
- Step 3 of each qa-ui-* loads the skill + references/<stack>.md (§5.1).
- Step 3 of the live-page POM workflow in all three qa-ui-* agents (qa-ui-dotnet.md:44, qa-ui-java.md:45,
  qa-ui-typescript.md:45) still mandates a `// TODO: missing data-testid` marker; replace it with R2 (the
  `missing-testids.md` row is the contract, the code carries no marker).
- Add ./qa/_shared/webmcp-testing to all three qa plugins in the marketplace, and one catalog row.
- A one-line cross-reference in qa/<stack>/skills/ai-feature-testing/SKILL.md (handoffs).

Traps:
- The entry point is document.modelContext, not navigator.modelContext. unregisterTool, provideContext,
  clearContext and requestUserInteraction are gone (webmcp.md §0). Teach none of them.
- Playwright throws unless the browser got the literal --enable-features=WebMCP launch arg, even if an
  origin-trial token exposes the API. page.webmcp covers the main frame only. Always pass a timeout:
  the default differs by language.
- .NET: settled by N1 (D32). runsettings LaunchOptions accepts Args, but the browser is launched once per
  worker, so the WebMCP suite needs its own webmcp.runsettings and its own run.
- TS: T1's config has two projects, `setup` and `chromium` (Desktop Chrome, signed-in storage state,
  depends on setup), a default testDir and default testMatch. G1 copies webmcp.spec.ts flat beside those
  assets, so it runs in `chromium`. Keep the spec self-contained with a file-level
  `test.use({ launchOptions: { args: ['--enable-features=WebMCP'] } })`, or add a `webmcp` project with
  `default: false` to the config asset and say so in your As built. Import `test` / `expect` from
  `./fixtures` if the spec needs the page-object fixtures.
- Use exactly §5.2's names. G1's check fails on any other mcp__playwright__ name under qa/.

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa): Playwright MCP allowlists, page-objects-from-url on current tools, webmcp-testing skill (003 A1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### T3 — TypeScript visual regression, accessibility and network mocking on 1.64 (general-purpose, docs)

````
You are `general-purpose`. Task T3 of docs/plans/003-qa-playwright-appium-upgrade.md: make
qa/typescript/skills/{visual-regression,accessibility-testing,network-mocking}, with every reference
file, teach Playwright 1.64 correctly, with no stale pin, no invalid API and no R1–R6 break.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.1, §2.2, §4, task T3, "Close-out — every task".
3. Every .md under qa/typescript/skills/visual-regression, accessibility-testing and network-mocking.
4. T1's qa/typescript/skills/ui-test-author/playwright/references/assertions.md (to link it, not repeat it).
   T2's qa/typescript/skills/evidence-capture/SKILL.md and references/playwright.md §5–§6: HAR
   recording (`tracing.startHar` fixture, `contextOptions.recordHar`) and `testInfo.attach` live there, so
   network-mocking keeps replay (`routeFromHAR`) and links the recording side. T2's test-reports already
   says WebP baselines get no Allure diff widget; the visual skill links it.
5. docs/research/003-qa-playwright-appium/playwright-evidence.md §2, §3, §6; playwright-releases.md §(d).
6. docs/audits/003-qa-playwright-appium/typescript.md rows D1, D2, D6, D9–D11, G1, C3, C5–C8, C11,
   C14–C18, C20, C24, C25, C27, L15, L17, L20–L23.

Build:
- Visual:
  - v1.64.0-noble with --ipc=host and an in-container npm ci.
  - updateSnapshots modes, incl. the 1.64 missing-passes change and CI 'none'; snapshotPathTemplate.
  - WebP, with the no-Allure-diff caveat.
  - page.clock.setFixedTime for "freeze clocks".
  - No redundant defaults or font waits. Trace retain-on-failure.
  - No PDF byte-compare.
  - Applitools through a fixture. Record the Percy no-assertion exception. No afterEach re-attach.
  - The allure-js-commons import, awaited.
  - Nightly lane. Fixtures, not new XPage. Descriptions say Playwright Test.
- A11y: wcag22aa; link the native accessible/aria assertions; awaited Allure; incompletes via
  test.info().attach; Lighthouse in a worker fixture.
- Network:
  - Glob 1.52.
  - recordHar via contextOptions or tracing.startHar.
  - Awaited route.continue; typed payloads; context.route for popups; updateContent naming.
  - page.requests() / consoleMessages() / pageErrors() for "not called".
  - Headers/TLS via response.allHeaders() / securityDetails().
  - The CDP last match; proxy teardown plus an assertion.
  - Fixed cross-references; WebSocket mocking points at realtime-stream-testing; URLPattern (1.59+).
- qa/typescript/agents/qa-ui-typescript.md Step 3: the a11y item lists only the router SKILL.md.

Traps:
- allure-playwright builds its diff widget only from .png triples (evidence §12.10).
- route.fulfill delivers a body at once, so it is not an SSE stream. Leave SSE to realtime-stream-testing.
- recordHar is a context option, not a TestOptions key: test.use({ contextOptions: { recordHar } }).

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-ts): visual, a11y and network-mocking skills on Playwright 1.64 (003 T3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### J3 — Java visual regression (rewritten), accessibility and network mocking on 1.63 (general-purpose, docs)

````
You are `general-purpose`. Task J3 of docs/plans/003-qa-playwright-appium-upgrade.md: make
qa/java/skills/{visual-regression,accessibility-testing,network-mocking} teach only APIs that exist in
Playwright Java 1.63. Rewrite visual regression as screenshot plus comparator (D9), with every sample
extending J1's BaseTest.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.1, §2.2, §4, Decisions D8, D9, task J3, "Close-out — every task".
3. Every .md under qa/java/skills/visual-regression, accessibility-testing and network-mocking.
4. qa/java/skills/ui-test-author/playwright/assets/BaseTest.java and references/lifecycle.md.
5. docs/research/003-qa-playwright-appium/playwright-evidence.md §1, §2, §6, §13.
6. docs/audits/003-qa-playwright-appium/java.md rows D1, D9, D12, D13, D16, D19, D21, D25, D31, D32,
   D36, D37, V2.

Build:
- Visual:
  - Rewrite references/playwright-snapshots.md: Locator.ScreenshotOptions (mask, animations, caret,
    style); baselines in src/test/resources/baselines/<os>-<browser>/; a comparator you verify on Maven
    Central today (candidate com.github.romankh3:image-comparison); the diff attached to Allure;
    baselines generated only in mcr.microsoft.com/playwright/java:v1.63.0-noble.
  - SKILL.md says Java has no screenshot assertion and stops saying "built-in".
  - Exact Percy/Applitools versions; @AfterMethod, not try/finally; fix or drop the PDF example;
    Gradle paths.
- A11y: axe 4.13.0 exact; BasePlaywrightTest → BaseTest; if/println → an attachment; the Lighthouse
  auth limitation stated (public pages only); wcag22aa.
- Network: glob 1.52; declare mockApi; no Thread.sleep in route handlers (CDP throttling or a server-side
  delay); fix the CDP findFirst test; define browserName; fix cross-references; page.requests();
  tracing().startHar().
- Every Allure call in these files uses allure-java 3.0 (D12): Allure.attachment(...) with
  AttachmentOptions.
- Extending BaseTest (com.example.uitests.support.BaseTest): a sample changes the context only by
  overriding `protected Browser.NewContextOptions contextOptions()` (recordHar, viewport, reduced motion,
  locale) and the launch by `launchOptions()` (plan D26). It never adds its own Playwright, browser or
  failure hook — BaseTest already keeps screenshot, trace and video on failure. Seed and clean up in the
  class's own @BeforeMethod / @AfterMethod(alwaysRun = true) with page.request() (lifecycle.md §7).
  Non-locator results (a comparator's diff ratio, an axe violation count) are AssertJ with .as(...).
  Emulation and media mechanics are in ui-test-author/playwright/references/emulation-and-mobile-web.md.

Traps:
- assertThat(page).hasScreenshot() and HasScreenshotOptions do not exist. G1's CODE_CHECKS fails if
  either survives in a code block or an asset.
- Java route handlers run on the Playwright dispatch thread. A sleep there stalls all events, not one
  request.
- Name the comparator's exact coordinates and version you saw on Maven Central today, in the reference
  and in your As-built note.

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-java): visual (screenshot + comparator), a11y and network skills on Playwright 1.63 (003 J3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### N3 — .NET visual regression (rewritten), accessibility and network mocking on 1.63 (general-purpose, docs)

````
You are `general-purpose`. Task N3 of docs/plans/003-qa-playwright-appium-upgrade.md: make
qa/dotnet/skills/{visual-regression,accessibility-testing,network-mocking} teach only APIs that exist in
Microsoft.Playwright 1.63. Rewrite visual regression as screenshot plus comparator (D9), with every
sample deriving from N1's BaseTest.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.1, §2.2, §4, Decision D9, task N3, "Close-out — every task".
3. Every .md under qa/dotnet/skills/visual-regression, accessibility-testing and network-mocking.
4. qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs and references/lifecycle.md.
5. docs/research/003-qa-playwright-appium/playwright-evidence.md §1, §2, §6, §13.
6. docs/audits/003-qa-playwright-appium/dotnet.md rows T1, T3, D-03, D-05, D-06, D-11, D-18, D-22,
   D-23, X-01, §1 row 49.

Build:
- Visual:
  - Rewrite references/playwright-snapshots.md: LocatorScreenshotOptions; a comparer you verify on NuGet
    today (candidates Verify.Playwright, Codeuctivity.ImageSharpCompare); AllureApi.AddScreenDiff;
    baselines only in mcr.microsoft.com/playwright/dotnet:v1.63.0-noble.
  - SKILL.md stops saying built-in.
  - Eyes.Playwright; AddGlobalAttachment/AddLink instead of AddTestAttachment; BaseURL from config.
- A11y: Deque 4.13.0 exact; Lighthouse via a persistent context and a free port; no pwa category.
- Network: glob 1.52; the CDP JsonElement? payload; D-18; cross-references.
- ".NET 8" labels → .NET 10 in these files.

Traps:
- ToHaveScreenshotAsync, ToMatchSnapshotAsync and LocatorAssertionsToHaveScreenshotOptions do not
  exist. G1's CODE_CHECKS fails if they survive in a code block or an asset.
- Applitools.Playwright is not on NuGet; the package is Eyes.Playwright. G1's CODE_CHECKS bans the old
  name in code.
- Name the comparer's package and version you saw on NuGet today, in the reference and your As-built note.
- N1's BaseTest is `Example.UiTests.Support.BaseTest : PageTest`. Samples derive from it and amend
  `base.ContextOptions()` (BaseURL from BASE_URL is already on it; never a hardcoded BaseURL, D-22); an
  override that returns `new()` drops BaseURL and the video folder, and BaseTest's teardown then throws.
  Locators go through page objects (`Describe()`, `Expect(locator, "message")`), never raw `Page.` calls in a
  test (R6). A package a sample needs is pinned in N1's Directory.Packages.props, so sample .csproj lines
  carry no `Version=` (Deque.AxeCore.Playwright 4.13.0, PercyIO.Playwright 1.0.4 and Eyes.Playwright
  1.37.49 are already there; add the comparer's `PackageVersion` line in the reference).
- Lighthouse needs a persistent context on a fixed debugging port, which BaseTest's per-worker browser
  cannot give, and `Playwright.CreateAsync()` in a test is a review blocker. A fixture deriving from
  `PlaywrightTest` can call `BrowserType.LaunchPersistentContextAsync(...)` without it. Launch flags in
  general belong in a .runsettings (D32).

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-dotnet): visual (screenshot + comparer), a11y and network skills on Playwright 1.63 (003 N3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### T4 — TypeScript: the remaining Playwright-bearing skills (general-purpose, docs)

````
You are `general-purpose`. Task T4 of docs/plans/003-qa-playwright-appium-upgrade.md: bring the remaining
Playwright-bearing TS skills onto 1.64 with no stale pin and no R1–R6 break, and wire
production-uptime-checks into qa-api-typescript.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.1, §2.2, §4, §5.1, Decision D7, task T4, "Close-out — every task".
3. Under qa/typescript/skills/: responsive-testing, realtime-stream-testing, browser-cloud-setup (+ references),
   test-login-tokens (+ references), language-testing (+ references), data-driven-testing,
   production-uptime-checks, inhouse-framework-conventions, email-testing/references/mailpit.md,
   api-test-author/playwright, gherkin-step-code/references/playwright-bdd.md, bdd-project-scaffold.
4. T1's references/emulation-and-mobile-web.md and config-and-fixtures.md (to link, not repeat);
   qa/typescript/skills/evidence-capture/SKILL.md (T2).
5. docs/audits/003-qa-playwright-appium/typescript.md rows C4, C9, C10, C13, C19, C21, C29, D7, D8, D13,
   L7, L8, L14, L19, L20; docs/research/003-qa-playwright-appium/playwright-releases.md §(b) 1.61–1.64.

Build:
- responsive-testing: data rows, not if/else; test.use({ viewport }); link the emulation reference; the
  cross-reference to React.
- realtime-stream-testing: the SSE caveat; it owns WebSocket mocking.
- browser-cloud-setup: use.connectOptions or a worker-scoped browser; the version taken from
  @playwright/test/package.json; teardown returned from globalSetup.
- test-login-tokens: a setup project with baseURL; storage-state limits (no sessionStorage;
  indexedDB: true); context.setStorageState.
- language-testing: page.clock for time-dependent formats.
- data-driven-testing: generated tests, no loops in a test.
- production-uptime-checks: evidence on probe failure (link evidence-capture); add it to Step 3 of
  qa/typescript/agents/qa-api-typescript.md.
- inhouse-framework-conventions: locator-based actions. mailpit.md: no global wipe.
- api-test-author/playwright: no finally; request-context cookies (1.64); failOnStatusCode,
  maxRedirects; APIResponse.timing() / securityDetails().
- playwright-bdd.md: Node 24/22; check status before parsing.
- bdd-project-scaffold: @playwright/test 1.64.0, allure-playwright 3.13.0, trace retain-on-failure,
  Node 24/22. Leave its Appium lines for M1.

Traps:
- Write versions as exact pins ("@playwright/test": "1.64.0"). G1's checker compares them to §2.
- Node 20 is EOL. Write 24 (22 maintenance), never "Node ≥ 20".
- browser-cloud-setup/references/details.md:223-232 still has `import { allure } from 'allure-playwright'`
  and un-awaited `allure.*` calls in a sync helper (aTS D3, C8). Use `import * as allure from
  'allure-js-commons'`, awaited, or `testInfo.attach` (evidence-capture §6), as T2's test-reports does;
  G1's CODE_CHECKS bans the old import in code blocks.

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-ts): remaining Playwright skills on 1.64, uptime probes wired (003 T4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### J4 — Java: the remaining Playwright-bearing skills, and `python-web-testing` (general-purpose, docs)

````
You are `general-purpose`. Task J4 of docs/plans/003-qa-playwright-appium-upgrade.md: move the remaining
Playwright-bearing Java skills onto J1's BaseTest and Playwright 1.63 with no R1–R6 break. Wire
production-uptime-checks into qa-api-java, and rewrite qa/_shared/python-web-testing to the house wait
rules on 1.63.0.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.1, §2.2, §4 (R8), §5.1, Decisions D8, D19, task J4, "Close-out — every task".
3. Under qa/java/skills/: responsive-testing, realtime-stream-testing, browser-cloud-setup (+ references),
   test-login-tokens (+ references), language-testing (+ references), data-driven-testing,
   production-uptime-checks, inhouse-framework-conventions, email-testing/references/{gmail-imap,mailpit}.md,
   api-test-author/playwright, gherkin-step-code, bdd-project-scaffold. Then qa/_shared/python-web-testing
   (SKILL.md, examples/, scripts/).
4. qa/java/skills/ui-test-author/playwright/assets/BaseTest.java; qa/java/skills/evidence-capture/SKILL.md.
5. docs/audits/003-qa-playwright-appium/java.md rows D3, D8, D10, D11, D14, D21, D23, D24, D27, D32,
   D33, D35, D39, D44, D46, D48, D52; plan D12 (the allure-java 3.0 sweep).

Build:
- responsive: D11, D46, D23; BaseUiTest → BaseTest. Viewport per class through contextOptions(); D23's
  broken reference now points at ui-test-author/playwright/references/emulation-and-mobile-web.md.
- realtime: WebSocketFrame.text().
- browser-cloud: GridWebTestBase → BaseTest with parallel="classes"; the installed client version.
  J1's BaseTest only launches a local Chromium (`playwright.chromium().launch(launchOptions()…)` in
  @BeforeClass, private fields), so a cloud run that must `connect(wsEndpoint)` has no seam. Add the
  minimum one to qa/java/skills/ui-test-author/playwright/assets/BaseTest.java (for example a protected
  method returning the Browser, defaulting to today's local launch with the HEADED stamp), update
  lifecycle.md §3, and record a dated decision. Those two files are the only J1 paths J4 may edit.
- language: context per method — setLocale / setTimezoneId in the class's contextOptions() override.
- data-driven: no parallel = true with Playwright (lifecycle.md §1 explains why).
- test-login-tokens: the signed-in state follows lifecycle.md §6 (AuthSetup @BeforeSuite, one state file
  per role, chosen in contextOptions()).
- production-uptime: catch the assertion error type and capture evidence; add it to Step 3 of
  qa/java/agents/qa-api-java.md.
- inhouse: locator actions.
- email gmail-imap.md / mailpit.md: Awaitility instead of Thread.sleep in poll helpers.
- api-test-author/playwright: exact status, not isOK(); no HttpComponents for constants.
- gherkin-step-code: page objects take Page, not TestContext.
- bdd-project-scaffold: Playwright 1.63.0; one discovery mechanism; Gradle paths. Leave Appium lines
  for M2.
- python-web-testing:
  - expect(...).to_be_visible() instead of networkidle, wait_for_timeout or wait_for_selector.
  - Locator APIs; outputs under the project.
  - playwright==1.63.0 and pytest-playwright==0.10.0.
  - Delete .DS_Store.
- Allure 3.0 sweep (D12):
  - Every Allure call in the files above uses Allure.attachment(...) + AttachmentOptions, with pins at 3.0.0.
  - Then only the Allure call sites and pins in these six files, read ±20 lines around each grep hit:
    qa/java/skills/ai-feature-testing/references/deepeval.md, db-testing/testcontainers/SKILL.md,
    failure-injection-testing/SKILL.md, feature-flag-testing/SKILL.md,
    security-testing/dependency-scan/SKILL.md, security-testing/passive-scan/SKILL.md.
  - Finish with `grep -rn "addAttachment\|allure-testng:2\|allure-cucumber7-jvm:2" qa/java qa/reporting/java`.
    It must find no code use outside the mobile skills M2 owns (prose naming the 2.x API as removed is fine).

Traps:
- allure-java 3.0 needs Java 17+ (the library is on 21). Every allure-* Java module moves to 3.0.0
  together; do not mix majors. Check that allure-cucumber7-jvm has a 3.0.0 on Maven Central before
  pinning it.
- Python Playwright needs Python ≥ 3.10 since 1.61. The docs page saying 3.8 is stale (releases §(a)).
- pytest-playwright 0.10.0 supports only on/off/retain-on-failure for --tracing/--video (evidence §11.4).

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-java): remaining Playwright skills on BaseTest/1.63, python-web-testing rewrite (003 J4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### N4 — .NET: the remaining Playwright-bearing skills and the `standards-audit` checklist (general-purpose, docs)

````
You are `general-purpose`. Task N4 of docs/plans/003-qa-playwright-appium-upgrade.md: move the remaining
Playwright-bearing .NET skills onto N1's BaseTest and 1.63 with no R1–R6 break. Wire
production-uptime-checks into qa-api-dotnet, and make the standards-audit checklist audit for exactly
what N1–N3 teach.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.1, §2.2, §4 (R8), §5.1, task N4, "Close-out — every task".
3. Under qa/dotnet/skills/: responsive-testing, realtime-stream-testing, browser-cloud-setup (+ references),
   test-login-tokens (+ references), language-testing (+ references), data-driven-testing,
   production-uptime-checks, inhouse-framework-conventions, api-test-author/playwright, gherkin-step-code,
   bdd-project-scaffold, bdd-reviewer, standards-audit (SKILL.md + references/conformance-checklist.md).
4. qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs and references/lifecycle.md §1–§5, §7;
   qa/dotnet/skills/ui-test-author/review/SKILL.md (the Playwright rows the checklist must agree with);
   qa/dotnet/skills/evidence-capture/SKILL.md.
5. docs/audits/003-qa-playwright-appium/dotnet.md rows C-03, C-06, C-07, C-11, C-13, C-15, D-04, D-07,
   D-08, D-10, D-12, D-20, D-21, D-28, §1 row 49.

Build:
- responsive: D-10, C-11.
- realtime: ws.FrameReceived + TaskCompletionSource; IsClosed is a property; frame.Text.
- browser-cloud: no Playwright.CreateAsync in [SetUp].
- test-login-tokens: D-21.
- language: PageTest + ContextOptions() + fixture parameters.
- data-driven: no ParallelScope.All for Playwright.
- production-uptime: D-20 and evidence on failure; add it to Step 3 of qa/dotnet/agents/qa-api-dotnet.md.
- inhouse: ToHaveURLAsync(new Regex(...)); locators.
- api-test-author/playwright: no try/finally; the review link.
- gherkin-step-code: C-13.
- bdd-project-scaffold: 1.63.0 under CPM; [AfterScenario] evidence per evidence-capture.
- bdd-reviewer: the C-07 rows.
- conformance-checklist: E11 matches R8. Add rows for a missing BaseURL, a ToHaveURLAsync glob,
  Playwright.Shard, the fabricated screenshot API, a package/image version mismatch, and a TODO comment
  on a fallback locator. Table rows may name these; only code blocks are checked. Leave the mobile rows
  for M3.
- ".NET 8" labels → .NET 10 in these files.

Traps:
- ToHaveURLAsync(string) is an exact match after BaseURL resolution. Globs work only in WaitForURLAsync.
- IWebSocket has events plus IsClosed and Url only; there is no WaitForEventAsync.
- N1's BaseTest is `Example.UiTests.Support.BaseTest : PageTest`. A sample derives from it and amends
  `base.ContextOptions()` (which already carries BaseURL from BASE_URL, the video folder, Locale en-US and
  ColorScheme Light); returning `new()` drops all of it. `BaseTest.RequiredEnv(name)` reads a variable.
- Launch options are per worker and come from the .runsettings (D32): a `LaunchOptionsAsync()` override is
  not reliable. A cloud browser (browser-cloud) is `BrowserTest.ConnectOptionsAsync()` — also per worker,
  so a cloud run is its own `dotnet test` run with its own .runsettings or environment.
- E11 (`Playwright.CreateAsync()` in a [Test], a [SetUp] or a fixture's [OneTimeSetUp]) is a blocker with
  one exception: the root-namespace `AuthSetup` [SetUpFixture], as in review/SKILL.md.
- language-testing: `ContextTest` defaults Locale to en-US, so a locale fixture sets `options.Locale` and
  `options.TimezoneId` on the base options, with `[TestFixture("de-DE", "Europe/Berlin")]` parameters.
- N1's Directory.Packages.props pins Microsoft.Playwright.NUnit only. A Reqnroll project that references
  Microsoft.Playwright directly adds `<PackageVersion Include="Microsoft.Playwright" Version="1.63.0" />`;
  bdd-project-scaffold's `..\UiTests\UiTests.csproj` reference already matches N1's project name.

Gate: none. This plan gates once, in G1. Do not run any build, test or check script.

Commit: `docs(qa-dotnet): remaining Playwright skills on BaseTest/1.63, conformance checklist aligned (003 N4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M1 — TypeScript mobile: Appium 3, WebdriverIO 10, Appium evidence, scoped components (general-purpose, docs)

````
You are `general-purpose`. Task M1 of docs/plans/003-qa-playwright-appium-upgrade.md: move the TS mobile
lane to §2.4's primary lane (Appium 3, WebdriverIO 10, Mocha). Fix the mobile audit's TS findings, write
qa/typescript/skills/evidence-capture/references/appium.md, and put qa-mobile-typescript on §5.3's
grants.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.4, §3.2, §3.4, §4, §5.1, §5.3, §5.4, Decisions D10, D17, D20, task M1, "Close-out — every task".
3. qa/typescript/agents/qa-mobile-typescript.md; under qa/typescript/skills/: ui-test-author/appium,
   mobile-native-features, mobile-screen-explorer, mobile-screen-objects, mobile-app-crawler (+ references,
   assets), device-cloud, the review skill's Appium rows, the Appium lines of bdd-project-scaffold, and
   gherkin-step-code/references/cucumberjs-appium.md.
4. qa/typescript/skills/evidence-capture/SKILL.md (T2).
5. docs/research/003-qa-playwright-appium/appium.md §0–§9 (WebdriverIO columns and §9.3).
6. docs/audits/003-qa-playwright-appium/mobile.md §2, §3, §5 (TS rows and cross-stack rows), §6.

Build:
- Versions: Appium 3 / WDIO 10 primary, Appium 2 / WDIO 9 supported. appium:-prefixed capabilities.
  Strict $.
- Mocha, not Vitest. The farm through wdio.conf.ts + a service. APPIUM_NODE on Device Farm. How to check
  a vendor's Appium version.
- mobile: extensions instead of the removed endpoints. Review rows lose resetApp/reset().
- Gestures and WebView ported: browser.action('pointer'), WDIO 10 tap/swipe, switchContext({ title | url }).
- Scoped components: a lazy parent locator plus a row key, with element-scoped finds first. UiSelector is
  secondary, because Google is deprecating it.
- Per-platform ladder: a React Native testID is the iOS accessibilityIdentifier and the Android
  resource-id, matching plan 002 §8.5.
- isElementVisible returns false on timeout. setClipboard takes base64.
- Remove the agent's browser.pause exception; keep its "scaffold" wording (S1 adds Step 0). Remove
  </content> leftovers and TODO markers. cucumberjs-appium.md attaches its screenshot.
- ui-test-author/appium/assets/: wdio.conf.ts, a base test with an afterTest evidence hook (screenshot,
  page source, logcat/syslog, a recording kept only on failure), a screen object, one test.
- evidence-capture/references/appium.md per §3.2; replace the placeholder line in SKILL.md.
- qa-mobile-typescript.md:
  - tools: = core tools + §5.3.
  - The appium-mcp prerequisites (embedded drivers; a server only for remoteServerUrl;
    SCREENSHOTS_DIR; AI-vision variables; docs tools need APPIUM_MCP_DOCS_ENABLED).
  - Step 1 wiring (§5.1).
  - The description (≤ 650 chars) says Appium 3.

Traps:
- WDIO 10's $ throws when a selector matches more than one element, at every step of a chain.
  stopRecordingScreen takes one options object.
- Recording limits: Android startRecordingScreen gives 180 s per chunk. mobile: startMediaProjectionRecording
  needs Android 10+. iOS needs ffmpeg, and mobile: startXCTestScreenRecording needs iOS 17+ (appium.md §4).
- appium-mcp tools: use exactly §5.3's names. G1's check fails on any other.
- T2's evidence-capture/SKILL.md carries the placeholder "Appium: `references/appium.md`, written by M1"
  as its own line under the intro paragraph; replace that line with the link. The SKILL.md has a "Who owns
  what" table and a "three kinds of capture" table; add the Appium rows there rather than a parallel
  section. T2's qa/reporting/typescript/skills/test-reports already defers WebdriverIO/Appium failure
  evidence to "the base test's afterTest hook, explained in evidence-capture (its Appium reference)", so
  the hook M1 writes is that hook. test-reports is not M1's file; if the wording no longer fits, say so in
  As built for G1.

- Leave two things to plan 002 (docs/plans/002-mobile-plugins.md) W1, per D21: line 10 of
  mobile-screen-explorer/SKILL.md (the React Native testID mapping) and the agent's "Related agents"
  section. If plan 002 has already landed them, keep its wording.

Gate: none. This plan gates once, in G1. Do not run tsc, wdio, appium or any check script.

Commit: `docs(qa-ts): mobile lane on Appium 3 / WebdriverIO 10, Appium evidence, scoped components (003 M1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M2 — Java mobile: Appium 3, java-client 11, Appium evidence, scoped components (general-purpose, docs)

````
You are `general-purpose`. Task M2 of docs/plans/003-qa-playwright-appium-upgrade.md: move the Java mobile
lane to §2.4's primary lane (Appium 3, java-client 11). Fix the mobile audit's Java findings, write
qa/java/skills/evidence-capture/references/appium.md, and put qa-mobile-java on §5.3's grants.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.4, §3.2, §3.4, §4 (R8), §5.1, §5.3, §5.4, Decisions D8, D12, D17, D20, task M2,
   "Close-out — every task".
3. qa/java/agents/qa-mobile-java.md; under qa/java/skills/: ui-test-author/appium, mobile-native-features
   (+ references), mobile-screen-explorer, mobile-screen-objects, mobile-app-crawler (+ references,
   assets), device-cloud (+ references), the review skill's Appium rows, the Appium lines of
   bdd-project-scaffold, and page-object-design's mobile lines.
4. qa/java/skills/evidence-capture/SKILL.md (J2).
5. docs/research/003-qa-playwright-appium/appium.md §0–§9 (Java columns, §2.4, §9.1).
6. docs/audits/003-qa-playwright-appium/mobile.md §2, §3, §5 (Java rows and cross-stack rows), §6.

Build:
- Versions: java-client 11.0.0 + selenium-support ≥ 4.50 primary; 10.x supported. AppiumDriver is no
  longer a RemoteWebDriver. No TouchAction, no PageFactory. The OpenRewrite MigrateToV11 note.
  UiAutomator2Options / XCUITestOptions.
- selenium.html5.Location → mobile: setGeolocation. Teardown, not try/finally. The presigned upload
  implemented, or it throws.
- Instance fields + parallel="classes", not a static ThreadLocal (D8).
- Gestures and WebView ported: W3C PointerInput, mobile: gestures, context switching.
- Package support/nativefeatures. No commented-out code. Intent accessors. Should_X_When_Y. One
  locator-constant style. AssertJ for non-Appium assertions.
- Review rows lose AppiumDriver<MobileElement> and resetApp. Scoped components (element-scoped finds
  first), the per-platform ladder, R2, </content> removal. After J1, ui-test-author/review/SKILL.md is
  15,636 chars: replace the Appium rows rather than adding to them, and keep the file ≤ 16,000.
- page-object-design already says Appium uses instance fields + parallel="classes" (J1); keep that line.
  BaseMobileTest can mirror J1's BaseTest shape: instance fields, alwaysRun hooks, requiredEnv(name), and
  one narrow, logged catch per capture helper (plan D29).
- ui-test-author/appium/assets/: build.gradle.kts, BaseMobileTest.java (evidence hooks per appium.md
  §9.1, on allure-testng 3.0), AppiumDriverFactory.java, a screen object, one test.
- Every Allure call in the mobile Java skills uses allure-java 3.0 (D12).
- evidence-capture/references/appium.md; replace the placeholder line.
- qa-mobile-java.md: tools: = core + §5.3; the prerequisites as in M1; Step 1 wiring; keep the
  "scaffold" wording (S1 adds Step 0); the description says Appium 3.

Traps:
- allure-testng 3.0 (D12): use Allure.attachment(...) + AttachmentOptions, as appium.md §9.1 shows.
  Allure.addAttachment is the removed 2.x API; G1's CODE_CHECKS bans it in Java code.
- java-client 11 no longer pulls in selenium-support. WebDriverWait needs it added explicitly.
- No TouchAction or MultiTouchAction in any code block or asset: G1's CODE_CHECKS bans them there.
  Prose and review rows may name them as removed.

- Leave two things to plan 002 (docs/plans/002-mobile-plugins.md) W1, per D21: line 10 of
  mobile-screen-explorer/SKILL.md (the React Native testID mapping) and the agent's "Related agents"
  section. If plan 002 has already landed them, keep its wording.

Gate: none. This plan gates once, in G1. Do not run gradle, javac, appium or any check script.

Commit: `docs(qa-java): mobile lane on Appium 3 / java-client 11, Appium evidence, scoped components (003 M2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### M3 — .NET mobile: Appium 3, Appium.WebDriver 9, Appium evidence, compiling assets (general-purpose, docs)

````
You are `general-purpose`. Task M3 of docs/plans/003-qa-playwright-appium-upgrade.md: move the .NET mobile
lane to §2.4's primary lane (Appium 3, Appium.WebDriver 9). Make its assets compile, write
qa/dotnet/skills/evidence-capture/references/appium.md, put qa-mobile-dotnet on §5.3's grants, and
update the mobile rows of the standards-audit checklist.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.4, §3.2, §3.4, §4, §5.1, §5.3, §5.4, Decisions D17, D18, task M3, "Close-out — every task".
3. qa/dotnet/agents/qa-mobile-dotnet.md; under qa/dotnet/skills/: mobile-project-setup, ui-test-author/appium
   (SKILL.md, references/details.md, assets/*.cs), mobile-native-features (+ references),
   mobile-screen-explorer, mobile-screen-objects, mobile-app-crawler (+ references, assets), device-cloud
   (+ references), the review skill's Appium rows, and the mobile rows of
   standards-audit/references/conformance-checklist.md.
4. qa/dotnet/skills/evidence-capture/SKILL.md (N2).
5. docs/research/003-qa-playwright-appium/appium.md §0–§9 (C# columns, §2.5, §9.2).
6. docs/audits/003-qa-playwright-appium/mobile.md §2, §3, §5 (.NET rows and cross-stack rows), §6.

Build:
- Versions: Appium.WebDriver 9.0.0 primary (strong-named, so the solution rebuilds); 8.x supported.
  AppiumOptions + AddAdditionalAppiumOption. The major does not track Selenium.
- mobile-project-setup: Appium 3, UiAutomator2 8.x, XCUITest 12.x, Node 24/22. Pages/, not Screens/.
  One platform-selection mechanism.
- Assets compile:
  - Fix page_template.cs (the ctor type, override, the Displayed property, .Text).
  - Make references/details.md mirror the assets.
  - Add BaseMobileTest.cs with evidence hooks (appium.md §9.2).
- chromedriver_autodownload is a server flag, not a capability. Fix the scrollGesture wording. Device Farm
  has no .NET Appium type. Teardown, not try/finally. The upload implemented, or it throws. Devices from
  configuration. No raw FindElement in a page. L22, L23.
- Checklist: only the mobile rows. Replace the removed APIs, and add an evidence-on-failure row.
- ".NET 8" → .NET 10. R2, scoped components (element-scoped finds first), the ladder, </content> removal.
- evidence-capture/references/appium.md; replace the placeholder line.
- qa-mobile-dotnet.md: tools: = core + §5.3; prerequisites; Step 1 wiring; Step 0 says Appium 3;
  the description says Appium 3.

Traps:
- Appium.WebDriver 8.0 replaced the old endpoints with mobile: commands and removed ToggleWifi,
  ToggleData, SetConnectionType and StartActivity (appium.md §2.5). Do not keep them in samples.
- NUnit stays 4.x (D18). Under NUnit 5, Assert.ThrowsAsync would have to be awaited. Note it, but do not
  move to NUnit 5. Pin NUnit 4.6.1, NUnit3TestAdapter 6.3.1 and Microsoft.NET.Test.Sdk 18.10.1, the values
  N1 put in qa/dotnet/skills/ui-test-author/playwright/assets/Directory.Packages.props.
- qa/dotnet/skills/ui-test-author/review/SKILL.md is at 15,558 chars after N1: replace its Appium rows in
  place, do not add, and keep the file ≤ 16,000.
- mobile-project-setup (D34): line 153 names the UI sibling `PlaywrightTests`; it is `UiTests`. Line 110
  runs `dotnet tool install allure`, which does not exist on NuGet; point at
  qa/reporting/dotnet/skills/test-reports for the Allure CLI instead.

- Leave two things to plan 002 (docs/plans/002-mobile-plugins.md) W1, per D21: line 10 of
  mobile-screen-explorer/SKILL.md (the React Native testID mapping) and the agent's "Related agents"
  section. If plan 002 has already landed them, keep its wording.

Gate: none. This plan gates once, in G1. Do not run dotnet build, appium or any check script.

Commit: `docs(qa-dotnet): mobile lane on Appium 3 / Appium.WebDriver 9, compiling assets, Appium evidence (003 M3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S1 — `mobile-project-setup` for Java and TypeScript, and Step 0 in both mobile agents (general-purpose, docs)

````
You are `general-purpose`. Task S1 of docs/plans/003-qa-playwright-appium-upgrade.md: write
qa/java/skills/mobile-project-setup (qa-mobile-project-setup-java) and
qa/typescript/skills/mobile-project-setup (qa-mobile-project-setup-typescript) per §3.6, and give
qa-mobile-java and qa-mobile-typescript a Step 0 that runs them.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.4, §3.4, §3.6, §4 (R7, R9), §5.1, Decision D20, task S1, "Close-out — every task".
3. qa/dotnet/skills/mobile-project-setup/SKILL.md (the pattern, as M3 left it) and the Step 0 row of
   qa/dotnet/agents/qa-mobile-dotnet.md.
4. qa/java/skills/ui-test-author/appium/assets/* and its SKILL.md stack section (M2);
   qa/typescript/skills/ui-test-author/appium/assets/* and its SKILL.md stack section (M1).
5. docs/research/003-qa-playwright-appium/appium.md §1, §2.1, §2.7.
6. The Steps tables and descriptions of qa/java/agents/qa-mobile-java.md and
   qa/typescript/agents/qa-mobile-typescript.md.

Build:
- Two SKILL.md files (≤ 16,000 chars each, R9 description):
  - Prerequisites: Node 24/22, JDK 21 for Java, ANDROID_HOME, an emulator image, Xcode + simulator;
    WDA signing for real iOS devices is a human step.
  - Appium 3: appium@3.8.0; appium setup or appium driver install uiautomator2 / xcuitest at §2.4's
    majors; appium driver doctor; the scoped --allow-insecure <driver>:<feature> syntax.
  - Layout. Java: Gradle around M2's build.gradle.kts and testng.xml (parallel="classes") with pages/,
    support/, tests/. TS: WDIO 10 + Mocha + @wdio/appium-service + @wdio/allure-reporter around M1's
    wdio.conf.ts.
  - Capabilities from PLATFORM / DEVICE_NAME / APP_PATH, with one mechanism.
  - First smoke: launch the app, verify the landing screen.
  - .gitignore for the R7 paths.
  - Pointers to device-cloud and ci-pipelines; one paragraph on the §2.4 supported lane.
  - Reference the ui-test-author/appium assets; do not copy them.
- Both agents: a Step 0 row ("Project scaffold — skip if a project exists", mobile-project-setup; exit
  gate: compiles, appium driver doctor clean, smoke runs), mirroring qa-mobile-dotnet.
- Add both skills to their plugins in .claude-plugin/marketplace.json, and catalog rows.

Traps:
- UiAutomator2 ≥ 5 and XCUITest ≥ 10 need Appium 3; Appium 2 needs UiAutomator2 4.x / XCUITest 9.x
  (appium.md §2.3). Get the driver/server pairing right in both lanes.
- WDIO 10 needs Node ≥ 22.19, and appium-mcp needs Node ≥ 22. Node 20 is EOL — never write it.
- Write exact pins (appium 3.8.0, webdriverio 10.0.2, java-client 11.0.0). G1's checker compares them
  to §2.

Gate: none. This plan gates once, in G1. Do not run gradle, npm, appium or any check script.

Commit: `docs(qa): mobile-project-setup for Java and TypeScript, Step 0 in qa-mobile agents (003 S1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### X1 — A Maestro lane for `qa-mobile-typescript` (general-purpose, docs)

````
You are `general-purpose`. Task X1 of docs/plans/003-qa-playwright-appium-upgrade.md: research Maestro into
docs/research/003-qa-playwright-appium/maestro.md, then write qa/typescript/skills/ui-test-author/maestro
(qa-ui-test-writer-maestro-typescript) per §3.7, and wire it into qa-mobile-typescript.

Read, in this order:
1. CLAUDE.md.
2. The plan: §3.7, §4, §5.1, Decisions D21, D22, task X1, "Close-out — every task".
3. docs/plans/002-mobile-plugins.md §8.5 (the test-id contract your selectors must follow).
4. qa/typescript/skills/ui-test-author/appium/SKILL.md (the sibling authoring skill, for shape only).
5. qa/typescript/agents/qa-mobile-typescript.md (description and Steps);
   qa/typescript/skills/ui-test-author/review/SKILL.md (the mobile rows);
   qa/typescript/skills/evidence-capture/SKILL.md.

Build:
- Research first. Use WebSearch/WebFetch on primary sources: maestro.mobile.dev docs, the
  mobile-dev-inc/maestro GitHub releases, Expo EAS Workflows docs. Write maestro.md with a URL on every
  fact and UNVERIFIED on anything else. Cover:
  - The current CLI version and install.
  - Flow syntax and the core commands (launchApp, tapOn, inputText, assertVisible, assertNotVisible,
    scrollUntilVisible, extendedWaitUntil, runFlow, runScript/evalScript, takeScreenshot,
    startRecording/stopRecording, clearState).
  - How id maps to a React Native testID on Android and iOS.
  - Waiting without sleeps; env/params; includeTags/excludeTags; config.yaml.
  - Outputs: JUnit format, test-output/debug-output dirs, failure screenshots and recordings.
  - CI: Maestro Cloud, the EAS Workflows Maestro job, a GitHub Actions emulator job.
  - Maestro Studio.
  - Whether an official Maestro MCP server exists, and its tool names.
  - Any syntax-check or dry-run command.
- The skill per §3.7 (≤ 16,000 chars, R9 description). It covers:
  - Maestro vs Appium.
  - The .maestro/ layout, with subflows as the page-object analogue.
  - Selectors on the plan 002 §8.5 contract.
  - Waits, data, tags.
  - Evidence and CI with JUnit.
  - Review rows.
  - assets/.maestro/: one flow, one subflow, config.yaml (valid YAML, no comments).
- qa-mobile-typescript.md: Step 2 offers ui-test-author/maestro when the project runs Maestro; the
  description (≤ 650 chars) names Maestro; Step 4 covers it.
- ui-test-author/review: Maestro rows — fixed waits, a text selector where a test id exists,
  duplicated steps that belong in a subflow, untagged flows, no clearState/launchApp reset between flows.
- evidence-capture/SKILL.md: one route line, "Maestro → ui-test-author/maestro § Evidence".
- If an official Maestro MCP server exists and you verified its tool names: add the registration and
  grants as a dated decision, and extend the plan's §5 lists so G1's allowlist check knows them.
  Otherwise grant nothing.
- Add the skill to qa-typescript in the marketplace, and a catalog row.

Traps:
- This plan's research did not cover Maestro. Every Maestro fact in the skill must come from your
  maestro.md, not memory.
- E2E stays with the QA peer (plan 002 D7). Do not write into mobile/ or the React Native dev skills.
- Record the syntax-check command you found (or that none exists) in your As-built note. G1 §6.3 uses it.

Gate: none. This plan gates once, in G1. Do not run maestro, emulators or any check script.

Commit: `docs(qa-ts): Maestro lane for qa-mobile-typescript, with research (003 X1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — The gate, the docs reconciliation, and the close-out (general-purpose, docs)

````
You are `general-purpose`. Task G1 of docs/plans/003-qa-playwright-appium-upgrade.md: run the plan's only
gate (§6) over everything T1–M3 landed, and fix what it finds. Write tools/qa-version-check.py, reconcile
README, CLAUDE.md and the catalog, and file the plan.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §5, §6, Decisions (incl. any dated ones tasks appended), every task's As-built notes,
   task G1, "Close-out — every task".
3. docs/plans/implemented/001-library-conformance-sweep.md §7 (the library check script).
4. Only when a check fails, the files it names.

Build:
- tools/qa-version-check.py per §6.2. The module docstring ends with §2.5's bump procedure.
- Run §6, in order, from the repo root:
  - §6.1: marketplace parse; the 001 script plus this plan's CHECKS, CODE_CHECKS (fenced code and
    assets/ only) and allowlists, saved under $TMPDIR; no .DS_Store.
  - §6.2: python3 tools/qa-version-check.py.
  - §6.3: compile every asset set in scratch projects under $TMPDIR.
  - §6.4: the evidence smoke in all three stacks.
  - §6.5: python3 tools/token-audit.py.
- Fix every failure at its source. Any task above may own it.
- README.md: the qa rows for the 3 evidence-capture skills, webmcp-testing, the 2 new
  mobile-project-setup skills and ui-test-author/maestro, and the counts.
- CLAUDE.md version policy: one Playwright line (Node 1.64 / Java·.NET·Python 1.63; a 1.64-only API is
  never taught on a 1.63 lane) and one Appium line (3 primary / 2 supported; java-client 11 /
  Appium.WebDriver 9 / WebdriverIO 10).
- docs/skills-catalog.md: ui-test-author/reviewer → review, bdd-project-setup → bdd-project-scaffold,
  the inhouse row; check the rows T2, J2, N2, A1, S1 and X1 added.
- D34 leftovers no task owns: in qa/dotnet/skills/api-project-setup/SKILL.md (:193) and
  performance-project-setup/SKILL.md (:136) the UI sibling is `UiTests`, not `PlaywrightTests`; drop
  `dotnet tool install allure` from api-project-setup (:39, :107) — NuGet has no such tool — and point at
  qa/reporting/dotnet/skills/test-reports for the Allure CLI. Skip whatever M3 or an earlier task already fixed.
- The final Status names what is unverified: no Appium flow ran on a device or emulator; no Maestro flow
  ran; no WebMCP test ran against a site that registers tools; the D9 comparators are recommendations. Then git mv the plan
  to docs/plans/implemented/.

Traps:
- No pwsh on this machine. Install the browsers the 1.63 Java/.NET bindings need with
  `npx playwright@1.63.0 install chromium`, which uses the same shared browser cache.
- No gradle or mvn on this machine. Download a Gradle distribution into the scratch dir. Never add a
  wrapper or build files to the repo.
- Java Playwright scratch project: build.gradle.kts, settings.gradle.kts and testng.xml go at the project
  root (the build calls useTestNG { suites("testng.xml") }); each .java asset goes under src/test/java at
  its package path (com/example/uitests/{support,pages,tests}/), WebMcpTest.java included. J1's
  `installPlaywrightBrowsers` passes --with-deps, which needs sudo on Linux; the npx install above is
  enough.
- Java evidence smoke: BaseTest throws when BASE_URL is unset, so export one (http://localhost is enough
  for data: pages). Put the two smoke tests in com.example.uitests.tests extending BaseTest, and remove
  LoginTest and WebMcpTest from that scratch project (they need a real app). Pass condition: the failing
  test leaves build/playwright-artifacts/<Class>.<method>.{png,zip,webm}, the passing test leaves nothing,
  and build/playwright-videos/ is empty afterwards.
- .NET Playwright scratch project: Directory.Packages.props, UiTests.csproj and ui.runsettings (the csproj's
  RunSettingsFilePath points at it) in one folder, with all eight .cs assets (BaseTest, AuthSetup, LoginPage,
  HomePage, LoginTests and the rest) plus WebMcpTests.cs and any .runsettings A1 added beside them.
  `dotnet build` → 0 errors.
- .NET evidence smoke: BaseTest throws when BASE_URL is unset (http://localhost is enough for data: pages).
  AuthSetup is a [SetUpFixture] in the root namespace Example.UiTests: it signs in against a real app before
  every fixture under that namespace, and its failure fails them all. So declare the two smoke tests in a
  namespace outside Example.UiTests (e.g. `Smoke`), deriving from Example.UiTests.Support.BaseTest, or
  leave AuthSetup.cs, LoginTests.cs and WebMcpTests.cs out of the smoke project. Pass condition: the failing
  test leaves bin/Debug/net10.0/playwright-artifacts/<Class>.<Test>.{zip,png,webm}, the passing test leaves
  nothing, and bin/Debug/net10.0/playwright-videos/ is empty afterwards.
- tools/token-audit.py exits non-zero while any size violation exists. Read the counts (≤ 160 total, 0
  description violations), not the exit code.
- Scratch projects live under $TMPDIR and are deleted afterwards. Nothing from them is committed.

Gate (this is the last task, so it carries the plan's only gate, in run order):
  §6.1 → §6.2 (write, then run) → §6.3 → §6.4 → §6.5
Fix what it finds — a failure may belong to any task above.

Commit: `chore(qa): 003 gate — version checker, asset builds, evidence smoke, docs reconciled (003 G1)`.
Close out per the plan's "Close-out — every task" before you stop.
````
