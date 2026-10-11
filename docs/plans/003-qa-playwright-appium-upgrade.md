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
canonical config (D35–D37). J2 landed 2026-10-10: `qa/java/skills/evidence-capture` (SKILL.md +
`references/playwright.md`), loaded by `qa-ui-java` Step 1 / Mode A and `qa-bdd-java` Step 4; Java
`test-reports` on allure-java 3.0 deferring to `BaseTest`, `flaky-test-quarantine` on D7, and the three Java CI
references with a Playwright UI job uploading `build/playwright-artifacts/` (Azure gained one). The one Allure
CLI pin holds for Java, and J1's build now pins it (D38–D41). N2 landed 2026-10-10:
`qa/dotnet/skills/evidence-capture` (SKILL.md + `references/playwright.md`), loaded by `qa-ui-dotnet` Step 1 /
Mode A (its Step 0 gate now names the `BaseTest` asset) and `qa-bdd-dotnet` Step 4; .NET `test-reports`
deferring to `BaseTest` with the byte-array `AttachBody` fix, `flaky-test-quarantine` on D7, and the three .NET
CI references sharding by NUnit class filters from one `ci/nunit-shards.sh` (no `Playwright.Shard`), uploading
`UiTests/bin/<cfg>/net10.0/playwright-artifacts/` on failure, GitLab in the v1.63.0-noble image (D42–D46;
`BaseTest`'s three helpers are now protected). A1 landed 2026-10-10: the six `qa-ui-*` / `qa-bdd-*` agents
grant exactly §5.2's 33 Playwright MCP tools; each `qa-ui-*` live-page workflow states §5.4's registration,
names the `playwright-cli` fallback and follows R2; `page-objects-from-url` ×3 run on the current tools with a
`playwright-cli` route; and `qa/_shared/webmcp-testing` (`qa-webmcp-testing-shared`: SKILL.md, three references,
seven assets incl. a `ProductPage` per stack and `webmcp.runsettings`, D47–D48) ships in all three qa plugins
and loads in every `qa-ui-*` Step 3. T3 landed 2026-10-10: TS `visual-regression`, `accessibility-testing` and
`network-mocking` (three routers, eight references) on 1.64 — a nightly `visual` project, `page.clock` frozen
time, WebP with the Allure caveat, fixtures for Percy, Eyes, axe (WCAG 2.2 AA) and Lighthouse, annotated
no-assertion tests, headers/TLS at the routing layer, `page.requests()` for "not called", and a Vitest-fixture
proxy (D49–D52). J3 landed 2026-10-11: Java `visual-regression`, `accessibility-testing` and `network-mocking`
(three routers, eight references) on 1.63 — `locator.screenshot` plus `com.github.romankh3:image-comparison:4.4.0`
against `src/test/resources/baselines/<os>-<browser>/`, with baselines and the nightly job in the v1.63.0-noble
image through `docker run` (D53); every sample on `BaseTest`; axe 4.13.0 at WCAG 2.2 AA with attached
incompletes; Lighthouse for public pages on `BaseTest`'s Chromium and a free port (D55); a held route instead of a
handler sleep (D54); headers/TLS at the routing layer; per-class Applitools runners (D56); the archived BrowserUp
kept with a warning (D57). N3 landed 2026-10-11: .NET `visual-regression`, `accessibility-testing` and
`network-mocking` (three routers, eight references) on 1.63 — `Locator.ScreenshotAsync` plus
`Codeuctivity.ImageSharpCompare` 4.1.390 (D58) against `UiTests/Baselines/<os>-<browser>/` found through
`ProjectPaths.Root` (D59), shown with `AllureApi.AddScreenDiff`, baselines and the nightly job in the v1.63.0-noble
image through `docker run` (D60); Percy linked with `AddLink`, a synchronous Eyes API gated in `[OneTimeTearDown]`
with `AddGlobalAttachment`; axe on `RunAxe` (the .NET package has no `AxeBuilder`) at WCAG 2.2 AA; Lighthouse from a
`PlaywrightTest` fixture on a persistent context and a free port, signed-in pages included (D61); a held route,
headers/TLS at the routing layer, `PostDataJSON()` records, and a Titanium 7.0.22 proxy that never touches the OS
trust store; §6.1's package check narrowed to the package id (D62). T4 landed 2026-10-11: the twelve remaining
Playwright-bearing TS skills on 1.64 — responsive rows with `test.use({ viewport })` and a measuring `Layout`
fixture (D63), realtime owning WebSocket mocking and browser SSE as a fixed event set plus `204` (D64), grid runs on
`use.connectOptions` or a worker-scoped `browser` marking one verdict per session (D65), a token-seeding setup
project on `context.setStorageState`, a frozen `page.clock` for locale formats, one generated test per data row,
uptime probes keeping trace/video/screenshot on failure (D66) and loaded by `qa-api-typescript` Step 3, locator
actions, a Mailpit suite with no global wipe, the 1.64 request-context options, and playwright-bdd 9.2.1 on 1.64.0.
J4 landed 2026-10-11: the twelve remaining Java skills on `BaseTest` and 1.63 — a `newBrowser(Playwright)` hook added
to J1's `BaseTest` for grid connects (D67), `@Factory` rows for responsive widths and locales (D68), one BrowserStack
session per class marked once with the installed client version (D69), `WebSocketFrame.text()` and the fixed-event-set
SSE mock, a token `AuthSetup` per lifecycle.md §6, an uptime probe that catches `AssertionError` and keeps
trace/video/screenshot (D70) loaded by `qa-api-java` Step 3, locator actions, Awaitility mail polls, exact statuses
without HttpComponents (`BaseApiTest` kept, D71), page objects on `Page` in the step glue, and a Cucumber 1.63
scaffold with one discovery mechanism and `BaseTest`-shaped evidence hooks (D72); `qa/_shared/python-web-testing`
rewritten to web-first waits on `playwright==1.63.0`; the six D12 files on allure-java 3.0.
N4 landed 2026-10-11: the twelve remaining .NET skills on `BaseTest` and 1.63 — responsive widths and locales as
NUnit fixture parameters amending `ContextOptions()` (D73), WebSocket frames through `Page.WebSocket` +
`FrameReceived` + a `TaskCompletionSource` and the fixed-event-set SSE mock, grid fixtures overriding
`BrowserTest.ConnectOptionsAsync()` in their own `TestCategory=grid` run (D74), a token body for `AuthSetup` at
`BASE_URL`'s origin (D77), a `PlaywrightTest`-based API base with per-test contexts and a § Review that
`qa-api-dotnet` Step 4 now loads (D75), an uptime probe catching only `PlaywrightException` and keeping
trace/video/screenshot, run from the pinned image and loaded by `qa-api-dotnet` Step 3 (D76), locator actions and a
`Regex` URL assertion, a `Given` that only acts, a Reqnroll scaffold on `Microsoft.Playwright.NUnit` 1.63.0 with
`BaseTest`-shaped `[AfterScenario]` evidence (D78), the C-07 BDD review rows, and a conformance checklist whose E11
matches R8 (D79) with fifteen new or reworded rows (A9, A10, E16, E17, F10, F11, I11–I13, K9, L4, L9, L14, M15, M16).
M1 landed 2026-10-11: the TS mobile lane on Appium 3 / WebdriverIO 10 / Mocha — `qa-mobile-typescript` on §5.3's 28
tools with the appium-mcp prerequisites and the evidence skill at Step 1; `ui-test-author/appium` with ten compilable
assets (a `wdio.conf.ts`, a `BaseTest.ts` whose `afterTest` keeps a screenshot, page source, device log and a recording
only on failure, a scoped `OrderRow`) and a per-platform test-id ladder with the id-prefix setting (D80); gestures,
WebView and app state on WDIO 10's helpers and `mobile:` extensions; the farm through a second `wdio.conf.ts`
(BrowserStack without a WDIO 10 service, D81; AWS `APPIUM_NODE`); Appium reference in `evidence-capture` (D82); and
the screen, crawler, native-feature, review, BDD-scaffold and Cucumber files cleaned (D83).
M2 landed 2026-10-11: the Java mobile lane on java-client 11 / Appium 3 / TestNG — `qa-mobile-java` on §5.3's 28
tools with the appium-mcp prerequisites and the evidence skill at Step 1; `ui-test-author/appium` with eleven
compilable assets (a `BaseMobileTest` whose `@AfterMethod` keeps a screenshot, page source, device log and a
recording only on failure on allure-java 3.0, an `AppiumDriverFactory`, a scoped `OrderRow`, `testng.xml` on
`parallel="classes"`) and the per-platform test-id ladder with the id-prefix setting (D84); W3C `PointerInput`
gestures, WebView contexts and app state without `resetApp`; `NativeFeatures` on `mobile:` commands in
`support.nativefeatures`; the farm with a presigned `PUT` that throws (D85) and a mobile Cucumber hook (D86);
Appium reference in `evidence-capture`; and the screen, crawler, review, `browser-cloud-setup` and glue files
cleaned. Next: M3. Built but unverified (M2): nothing compiled or ran — the Java Appium assets (an `AppiumDriver`
`switch` on `AndroidDriver` / `IOSDriver`, `UiAutomator2Options.amend`, `Allure.attachment` with a stream,
`AndroidStartScreenRecordingOptions` / `IOSStartScreenRecordingOptions` spellings) are G1's. Built but unverified: no asset, workflow or pipeline has been
compiled or run (G1 does that; D24's TS config import, the Java build on Allure Gradle plugin 4.3.0, the .NET
build on NUnit3TestAdapter 6.3.1 / Test SDK 18.10.1, `dorny/test-reporter`'s `java-junit` parse, the trace CLI
through the Java driver (D39) and through `playwright.ps1` (D43), the .NET shard script against a real
`--list-tests` (D44), and the WebMCP assets' typings and the D48 scripts are the open risks; N2 had no web
access, so its .NET spellings rest on the committed research; no WebMCP test has run against a site that
registers tools; T3 had no web access either, so its Percy, Applitools, playwright-lighthouse, mockttp and
Vitest-fixture spellings rest on the research and the old skill text, and the TS CI references do not yet run
`--project=visual` — G1 reconciles that; J3 read its pins from Maven Central and npm and its spellings from the
libraries' sources, but nothing ran: the comparator flow, the `docker run` visual job, Lighthouse attached to
Playwright's Chromium, Applitools `BatchInfo.setId` / `getAllTestResults(boolean)` (no published sources) and
BrowserUp on Java 21 are open, and J2's Java CI references still describe the visual container job — G1
reconciles that too; N3 read its pins from NuGet and npm and its spellings from sources (the Eyes API from the
assembly metadata, since it publishes none), but nothing ran: `VisualCheck`, the Eyes calls, `RunAxe` with an
exclusion context, Lighthouse seeing a persistent context's sign-in, the `docker run` visual job and the Titanium
proxy with Selenium are open, and N2's .NET CI references neither exclude the `visual` / `lighthouse` categories
from the gate nor point at the `docker run` job — G1 reconciles that; T4 had no web access, so its `APIResponse.timing()` / cookie spellings, `npx checkly runtimes`,
BrowserStack's `getSessionDetails`, Checkly honouring a spec's `test.use` evidence modes (D66) and `EventSource`
stopping on a routed `204` (D64) rest on the research and memory — none of them is in a compiled asset; J4 had no
web access either, so TestNG's per-instance `@BeforeClass` under `@Factory` (D68), the `IAlterSuiteListener`
thread-count override and BrowserStack's `getSessionDetails` (D69), the Playwright jar's `pom.properties`,
`StorageStateOptions.setIndexedDB`, Cucumber's `@After(order = 0)` running last and `Allure.attachment(String,
String)` rest on sources read from memory — of J4's files only `BaseTest.java` is a compiled asset; N4 had no web
access either, so `BrowserTest.ConnectOptionsAsync()`'s signature (D74), `IPage.WebSocket` firing before a socket's
first frame, `IWebSocketRoute.Send` being synchronous, `SseItem<T>.EventId`, every .NET `Expect` failure being a
`PlaywrightException` (D76), `TelemetryClient.FlushAsync(CancellationToken)`, Reqnroll's after-hook order, the
`Allure.Reqnroll` package and `Allure.ReqnrollPlugin` assembly names (D78), Reqnroll 3.3.4 being current and
`Assert.MultipleAsync` rest on memory — none of N4's files is a compiled asset, and the .NET UI gate filter does not
yet exclude `TestCategory=grid` — G1 reconciles that with the `visual` / `lighthouse` exclusions); M1 read WDIO 10 types and commands from the packed 10.0.2 tarballs and its pins from npm, but nothing
ran: the TS Appium assets are not type-checked, §6.3's TS Appium install line is too short (use
`assets/package.json`), the `appium:settings[disableIdLocatorAutocompletion]` need for React Native ids and the
device-farm facts (BrowserStack/Sauce Appium 3, Device Farm `APPIUM_NODE`) rest on READMEs and the research, and
`browser-cloud-setup` still says a BrowserStack service sets the status).
Planned 2026-10-10. The research behind it is committed with this plan:
`docs/research/003-qa-playwright-appium/` (5 files). So is the read-only audit:
`docs/audits/003-qa-playwright-appium/` (4 files). All open questions were answered on 2026-10-10:
- Java moves to allure-java 3.0.
- Java and TS get `mobile-project-setup` (S1).
- `playwright-cli` is documented alongside MCP.
- NUnit stays 4.x.
- A Maestro lane is added (X1).
- The newest Appium client majors are primary.

Next: M3 (H1, the user's, blocks no task). The cost is 19 agent sessions on the subscription, each started by the user
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
   "nonexistent package": r'Include="Applitools\.Playwright"|add package Applitools\.Playwright\b',
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

**D38 — Java keeps the one Allure report generator, allure2 `allure-commandline` 2.46.1, and J1's build pins it
as `allure.version` (J2, 2026-10-10).** Allure's *Migrating to Allure Java 3* guide says allure-java 3 results
open in Allure Report 2 and 3 with an unchanged file format, and allure2 2.46.0 renders the run-level errors
3.0 writes, so no per-stack split is needed and `ci-conventions` is unchanged. But Allure Gradle plugin 4.3.0
provisions Allure Report 3 by default. Readings: leave `allure.version` at the plugin default (a local
`./gradlew allureReport` and the CI report then come from two generators), switch Java to Allure Report 3 with
a per-stack pin, or set `version.set("2.46.1")` in the build (chosen). **Cost:** J2 edited two J1 files — one
line in `assets/build.gradle.kts` and one Versions row in `ui-test-author/playwright/SKILL.md`; the Gradle report
task downloads the `allure-commandline` zip from Maven Central instead of a Node runtime.

**D39 — Java agents read a failure's trace with the trace analysis CLI, through Node
(`npx playwright@1.63.0 trace …`) or the Java driver (`./gradlew playwright --args="trace …"`) (J2, 2026-10-10).**
J1's lifecycle.md §8 called that CLI Node-only. playwright-core v1.63.0 registers the `trace` commands in the
same program the Java driver's `com.microsoft.playwright.CLI` runs (`addTraceCommands` in
`packages/playwright-core/src/cli/program.ts`), and the open trace is kept in `.playwright-cli/trace/` under the
working directory, which J1's `JavaExec` task keeps stable. Readings: Node-only (an agent on a JVM-only machine
reads nothing but the screenshot), or both routes (chosen), with lifecycle.md §8's sentence replaced by a link.
**Cost:** the Gradle route is inferred from source, not run; G1's Java evidence smoke runs it once, and if it
fails, `evidence-capture` and `qa-ui-java` Mode A fall back to Node only.

**D40 — Java CI installs the browsers on the runner with `installPlaywrightBrowsers`; the pinned image is the
visual-baseline variant (J2, 2026-10-10).** The `mcr.microsoft.com/playwright/java:v1.63.0-noble` image ships
OpenJDK 25 and Maven, no JDK 21, no Gradle and no cloud CLI (its v1.63.0 Dockerfile), J1's build pins a Java 21
toolchain with no resolver, and a GitHub container job runs `azure/login` inside the container, where the
Azure CLI it needs is missing. Readings: the image as every UI job's default (JDK 21 provisioning per CI, and
the OIDC credential fetch breaks), or the runner install as default with the image documented per CI as the
variant for visual baselines (chosen; J2's task allows either). **Cost:** a UI screenshot from the runner is
not a visual baseline; J3's visual job inherits the JDK and credential constraints, which its prompt now names.

**D41 — Java quarantine filters the project's one `testng.xml` with Gradle groups, and its Allure category
matches `"flaky": true` (J2, 2026-10-10).** The old skill retried every test through a suite-wide listener (cap
1 on the gate, 3 in quarantine), kept two extra suite files, and filed every `TimeoutException` as "Known
flaky". Readings: two suite files (each repeating J1's `parallel="classes"` and packages) or
`excludeGroups("flaky")` / `includeGroups("flaky")` on the one suite (chosen; lifecycle.md §2 already relies on
Gradle group filters with `alwaysRun` hooks); a category on an exception regex or on Allure's `flaky` matcher
(chosen). A retry exists only as a per-test `RetryOnce` on a documented hotspot. **Cost:** detection waits for
five launches of history, restarted once by allure-java 3's new TestNG identifiers; Java gets no nightly repeat
lane (D7 names history and the quarantine category only).

**D42 — The .NET `BaseTest`'s `EvidenceName()`, `Artifact(name, ext)` and `Attach(name, type, path)` are
protected, so a deliberate recording is named, placed and attached exactly like the failure evidence (N2,
2026-10-10).** A receipt or HAR made in a test class's own `[SetUp]`/`[TearDown]` needs the sanitized
`<Class>.<Test>` name, the `playwright-artifacts/` folder CI uploads, and both attachments. Readings: repeat
the regex and the double attach in every recording class (the copies drift from `BaseTest`), a public static
helper in `Support/` (a second owner of the naming), or widen the three private members (chosen). **Cost:** N2
edited N1's asset (three access modifiers) and lifecycle.md §6; `BaseTest`'s protected surface grows by three
members. G1's .NET build compiles it.

**D43 — .NET agents read a failure's trace with the trace analysis CLI through Node
(`npx playwright@1.63.0 trace …`) or the .NET driver (`pwsh bin/<cfg>/net10.0/playwright.ps1 trace …`) (N2,
2026-10-10).** N1's lifecycle.md §9 called that CLI Node-only. `playwright.ps1` runs the 1.63 driver's
`cli.js`, the same playwright-core program in which D39 found `addTraceCommands`. Readings: Node-only (an
agent on a machine without Node reads nothing but the screenshot), or both routes (chosen), with lifecycle.md
§9's sentence replaced by a link. **Cost:** inferred from D39's source reading, not run; G1 runs it without
`pwsh` by calling the driver's node and `cli.js` directly, and if it fails, `evidence-capture` and
`qa-ui-dotnet` Mode A fall back to Node only.

**D44 — .NET CI shards by NUnit class filters computed once: one script, `ci/nunit-shards.sh`, defined in
`qa/cicd/dotnet/skills/ci-pipelines/SKILL.md`; a shards job per sharded suite publishes `<i>.filter` files as
an artifact; each shard job reads the file for its index (N2, 2026-10-10).** The script lists the tests with
`dotnet test --list-tests -- NUnit.DisplayName=FullName`, reduces each to its class, deals the classes
round-robin in name order, and writes one `FullyQualifiedName~` term per class joined by `|`, as the plan
asked. Two additions: each term ends in `.` (or an escaped `\(` for a parameterized fixture) so `LoginTests`
does not also match `LoginTestsMobile`, and fewer classes than shards fails the shards job. The API shards use
it too: their `NUnit.Where="… test % N == i"` stand-in is not valid NUnit syntax. Readings: per-CI dynamic
matrices carrying the filters in JSON (three encodings, each escaping `\(` and quotes inside YAML), the script
copied into each of the three references, or one script plus filter files (chosen; GitHub's matrix is built
from the same `shard-total`, Azure's `parallel:` from the same parameter, and GitLab — which takes no variable
in `parallel:` — repeats the number and checks the file count against `CI_NODE_TOTAL`). **Cost:** one more job
per sharded suite; balance is by class count, not duration; `NUnit.DisplayName` in `--list-tests` and the
`\(` escape are unverified until G1 runs the script against its .NET scratch project.

**D45 — .NET CI installs the browsers on the hosted agent in GitHub Actions and Azure Pipelines
(`pwsh … playwright.ps1 install --with-deps chromium`), and runs the GitLab UI job in
`mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`; on GitHub and Azure the image is the visual-baseline
variant (N2, 2026-10-10).** The UI jobs fetch `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` through OIDC with
`azure/login` / `AzureCLI@2`, which run inside a container job, where the image has no Azure CLI (as D40
found for Java). A GitLab Docker-executor job runs in an image anyway, and this one carries the .NET 10 SDK
and the browsers, so no install step and no `pwsh` call. Whether `pwsh` is in the image could not be checked
(web access was denied in N2's session), so no CI step relies on it. Readings: the image everywhere (the OIDC
fetch breaks on GitHub and Azure), the runner install everywhere (GitLab's SDK image would then need `pwsh`,
equally unverified), or the split (chosen). **Cost:** a runner screenshot is not a visual baseline; GitLab's UI
job, like every GitLab job here, assumes an AWS CLI the image lacks — stated in the reference.

**D46 — The .NET quarantine bucket in `categories.json` matches Allure's `"flaky": true` flag, which Allure
sets from history, and the quarantined set is the report's `Flaky` tag; no teardown marks a result flaky (N2,
2026-10-10).** The plan and audit D-13 said "match the quarantine category". Allure 2 categories match a
status, a message, a trace or the flaky flag — never a label — and Allure.NUnit has no flaky attribute.
Readings: the old base-class `[TearDown]` that sets the flag (`FlakyMarkBase`: its `tc.flaky` is not an
Allure.NUnit `TestResult` member — the flag lives in `statusDetails` — it cannot sit beside `BaseTest` under
single inheritance, and whether a flag set in a teardown survives Allure.NUnit's stop could not be checked);
the old `TimeoutException` trace regex (D-13's defect); or the flaky matcher plus the category as a tag
(chosen, as D41 for Java). **Cost:** a quarantined test's failures land in the bucket only once history has
marked it flaky; until then it is found by its tag. That Allure.NUnit reports NUnit categories as tags is
unverified.

**D47 — Each stack's WebMCP assets add a `ProductPage` page object (A1, 2026-10-10).** §3.3 and A1's prompt
name one test file per stack (`webmcp.spec.ts`, `WebMcpTest.java`, `WebMcpTests.cs`) that uses the base test's
`page` directly. But T1, J1 and N1 landed the writers' rule that a spec or test class calls no raw `page`
method — the page object owns its URL in `goto()`. Readings: one file per stack with `page.goto`, `getByTestId` and `evaluate` in the
test class or a spec-local fixture (breaks that rule in the asset meant to show it), or a `ProductPage` per stack
that owns the URL, the `Cart.Badge` locator and the tool surface — `page.webmcp` in TS, the two `evaluate`
scripts in Java/.NET (chosen). The assertion-side helpers (`registeredTool`, which fails with the tools it saw)
stay in the test class, since page objects do not assert. **Cost:** one more asset per stack for G1 to copy and
compile (`ProductPage.ts` flat beside the spec, `ProductPage.java` under `com/example/uitests/pages/`,
`ProductPage.cs` beside the other `.cs` assets); the scripts live in one page, so a second WebMCP page moves them
to a shared helper on that second need.

**D48 — The Java/.NET 1.63 route is two in-page scripts, not webmcp.md §4.4's one (A1, 2026-10-10).**
`SETTLED_TOOLS_JS` / `SettledToolsJs` lists the frame's tools (`tool.window === window`, string schemas
parsed) and resolves once a named tool is present or absent, re-checking on every `toolchange` event, or when
its timeout passes. `CALL_TOOL_JS` / `CallToolJs` is §4.4's call — object input, retried as a JSON string on
`Failed to parse input` — raced against a timeout. Both read `document.modelContext` only: no
`navigator.modelContext` fallback and no Firefox `invokeTool` branch, since `BaseTest` launches Chromium.
Readings: §4.4 verbatim with registration polled from Java/C# (a sleep between reads, banned), polled with
`waitForFunction` (it does not await an async predicate — a `Promise` is truthy, so it returns at once), or an
event-driven wait inside the page (chosen); a call with no timeout (`evaluate` has none, so a declarative tool
without `toolautosubmit` hangs the test) or the race (chosen). **Cost:** the wait and the race are this plan's
code, not the research's; like the rest of the route they are unverified until a suite runs against a site that
registers tools.

**D49 — TS visual and Lighthouse specs run in their own `default: false` projects, taught as additions to
the canonical config, not added to T1's asset (T3, 2026-10-10).** `qa/cicd/ci-conventions` gates visual
regression to the schedule, and a plain `npx playwright test` must not run it. Readings: a `@visual` tag
filtered with `--grep-invert` in every PR command (a second filter beside D35's `@flaky` in all three CI
references), the two projects added to `assets/playwright.config.ts` (T1's asset, outside T3's paths, and
every project would carry suites most never run), or a `visual` project (`testMatch: /.*\.visual\.spec\.ts/`,
`default: false` [1.64]) and a `lighthouse` project (`workers: 1`, `default: false`) shown as config
additions in the references, with a matching `testIgnore` on `chromium` (chosen). **Cost:** the nightly job
must name `--project=visual` (a plain run, even nightly, skips it), which T2's CI references do not yet do —
G1 reconciles; the snippets are not compiled by G1, since the asset does not contain them.

**D50 — A test whose verdict is made outside it (Percy, Applitools, `playAudit`) records that with an
annotation (T3, 2026-10-10).** The plan asked only to "record the Percy no-assertion exception". Readings: a
sentence in the reference (the test itself still reads as a forgotten assertion), an artificial `expect`
after the upload (asserts nothing), or a `{ type: 'no-assertion', description }` annotation constant per tool
— `percyReview`, the Eyes spec's inline annotation, `lighthouseGate` — passed in the test's details, so the
report and Allure show why (chosen, for all three, since Applitools and `playAudit` have the same shape).
**Cost:** one more constant per fixture file, and a reviewer must accept the annotation as the record the
house rule asks for.

**D51 — TS a11y and Lighthouse evidence is attached with awaited `testInfo.attach`; no direct Allure call
(T3, 2026-10-10).** The plan said "awaited Allure calls" for a11y. T2's `test-reports` says to prefer
`testInfo.attach` (it reaches the HTML report and Allure) and to call `allure-js-commons` only for
Allure-only data. Readings: `await allure.attachment(...)` in the helpers (Allure-only, and the HTML report
loses the violations), or `testInfo.attach` inside the `a11y` and `lighthouse` fixtures (chosen). The one
Allure-only call left in T3's files is the Percy build link, `await allure.link(...)` from `allure-js-commons`.
**Cost:** none beyond the reading.

**D52 — The TS proxy reference waits on client-visible signals and reads `MockedEndpoint.getSeenRequests()`;
its HAR writer became a scrubbed JSON traffic log (T3, 2026-10-10).** The old reference resolved a promise
from an un-awaited `server.on('request')` subscription with a deadline timer, and wrote a HAR from
`server.on('response')` using `res.request.method`, a field this session could not confirm on mockttp's
completed response. Readings: keep both and await the subscriptions (two event races and an unconfirmed
field), or register a pass-through endpoint before the action and read its seen requests after the page
object's completion signal, logging the unmatched pass-through requests without `authorization` / `cookie`
headers (chosen). **Cost:** the proxy lane writes no HAR and logs no response status or headers; a HAR of a
non-Playwright client needs another tool.

**D53 — The Java visual job and the baseline-update command run `mcr.microsoft.com/playwright/java:v1.63.0-noble`
with `docker run` from a runner step, not as a container job (J3, 2026-10-11).** D40 left the visual job three
limits: the image has no JDK 21 (J1's toolchain), no Gradle and no cloud CLI, and Azure container jobs have no
`sudo`. Readings: a container job per CI as J2's references describe it (GitHub keeps `setup-java` inside, but
`azure/login` cannot run there, so signed-in pages are out; Azure cannot `apt-get` JDK 21), or one `docker run`
command, run as the image's root user, that installs `openjdk-21-jdk-headless` and runs `./gradlew visualTest`,
with the credentials fetched on the runner first and passed in with `-e` (chosen; GitLab, whose job already runs
in an image, takes them from masked CI/CD variables). The same command with `UPDATE_BASELINES=1` and
`--platform linux/amd64` is the local baseline update. **Cost:** an `apt-get` of JDK 21 on every visual run and
no Gradle cache unless one is mounted; root-owned files on a Linux host; J2's three CI references still describe
the container-job variant — G1's prompt carries the one-line reconciliation.

**D54 — A Java test shows a loading state by holding the route, not by delaying it (J3, 2026-10-11).** The plan
said "no `Thread.sleep` in route handlers (CDP throttling or a server-side delay)". Readings: CDP throttling only
(Chromium-only, slows every request, and timing-dependent), a server-side delay only (needs a test endpoint for
every loading state), or a handler that stores the `Route` and returns — playwright-java's `Router.handle`
reports that as `PendingHandler` and the request waits until the test calls `resume()` (chosen, as
`MockApi.holdOrders()` / `HeldRequests.release()`), keeping CDP for real bandwidth and the server for client
timeouts. **Cost:** a held request shows "not yet", never "slowly"; the deferred-handling path is read from
v1.63.0 source, not run.

**D55 — Java Lighthouse audits public pages only, through `lhci autorun` or a TestNG test attached to
`BaseTest`'s own Chromium on a free debugging port; JSON in these skills is read with Gson (J3, 2026-10-11).**
`aJ` D13 found the old test audited a different context on a fixed port. Readings: drop the TestNG audit and keep
only `lhci` (no score in the test report), keep a private `Playwright.create()` with `--remote-debugging-port=9222`
(a review blocker, and parallel classes collide), or `launchOptions()` adding a port chosen with
`new ServerSocket(0)` in the class constructor (chosen). Gson is Playwright for Java's own compile-scope
dependency (2.14.0 in 1.63), so the Lighthouse report, mocked payloads and CDP payloads add no JSON library;
Jackson (a new pin) was the other reading. **Cost:** a signed-in page has no Lighthouse score in the Java lane; a
short race between choosing the port and Chromium binding it; Lighthouse attaching to a Playwright-launched
headless Chromium is unverified from Java.

**D56 — Each Applitools class owns its `VisualGridRunner` and gates in its own `@AfterClass` (J3, 2026-10-11).**
The plan asked for `@AfterMethod` instead of `try`/`finally`. Readings: one `static` runner gated in
`@AfterSuite` (the old shape: static mutable state shared by parallel class threads), `eyes.close(false)` plus an
assertion per test (serializes the grid, and its multi-environment result is unclear), or a runner instance field
from `@BeforeClass`, `eyes.closeAsync()` in `@AfterMethod(alwaysRun = true)` and `runner.getAllTestResults(true)` in
`@AfterClass(alwaysRun = true)` (chosen), with one `APPLITOOLS_BATCH_ID` per run so the classes share a dashboard
batch. **Cost:** a visual difference fails a configuration method of the class, not the test; `testConcurrency`
applies per class.

**D57 — `network-mocking/references/proxy.md` keeps BrowserUp Proxy, pinned at its last release, with the
archive stated (J3, 2026-10-11).** `com.browserup:browserup-proxy-core` 2.1.2 (December 2020) is the latest on
Central, and its repository is archived. Readings: move the reference to a maintained proxy (mitmproxy or
WireMock 3 — a new tool taught without a verified API), drop the reference (the Selenium and Appium agents lose
their traffic layer), or keep it with the warning and fix its samples (chosen). **Cost:** the Java lane's
non-Playwright traffic capture rests on an unmaintained library that was not run on Java 21.

**D58 — The .NET comparer is `Codeuctivity.ImageSharpCompare` 4.1.390, not `Verify.Playwright` (N3, 2026-10-11).**
D9 asked for a comparer verified on NuGet and named two candidates. `Verify.Playwright` 3.1.1 (needs
`Microsoft.Playwright` ≥ 1.61 and Verify 31.20) is a snapshot framework: received/verified files beside the source
file, DiffEngine, a byte comparison unless another comparer package is added, and its own accept workflow.
`Codeuctivity.ImageSharpCompare` 4.1.390 (2026-05-13; net8/9/10; Apache-2.0) is a function over two PNGs with a
per-pixel colour tolerance, a differing-pixel percentage and a diff image. Readings: Verify (it would replace the
committed `<os>-<browser>` store, `UPDATE_BASELINES=1` and the pinned-image rule that the Java and TS lanes share),
or ImageSharpCompare under a small `VisualCheck` helper (chosen). **Cost:** `VisualCheck` is this library's code,
not a vendor's; the comparer pulls `SixLabors.ImageSharp` 3.1.12, which the Six Labors Split License grants under
Apache-2.0 only as a transitive dependency (or for open source / companies under USD 1M revenue), so a project must
not reference it directly; the comparer remains a recommendation (D9).

**D59 — .NET tests find committed files through one `ProjectDirectory` assembly-metadata item read by
`Support/ProjectPaths.Root` (N3, 2026-10-11).** `dotnet test` runs from `bin/<cfg>/net10.0/`, so visual baselines
and the replayed HAR need the project folder, and an update must write back to it. Readings: paths relative to
`TestContext.WorkDirectory` (reads copies in `bin/`, updates never reach the repo), `[CallerFilePath]` (rewritten by
`PathMap` / deterministic CI builds), a required environment variable (one more thing every run must set), or an
`AssemblyMetadataAttribute` written from `$(MSBuildProjectDirectory)` by the csproj (chosen; one helper, two users —
visual-regression's baselines and network-mocking's HAR). **Cost:** two csproj lines a project adds (shown in the
references, not in N1's asset); the recorded path is the build machine's, so a host build run inside a container
breaks — the visual commands build inside the container.

**D60 — The .NET nightly visual job and the baseline update run `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`
with `docker run` from a runner step (N3, 2026-10-11).** As D53 found for Java, a GitHub or Azure container job runs
`azure/login` / `AzureCLI@2` inside an image with no cloud CLI (D45), so it can only test pages that need no fetched
credentials. Readings: the container job N2's CI references describe as the visual variant, or the credential fetch
on the runner and `docker run … dotnet test UiTests -c Release --filter TestCategory=visual` with `-e` (chosen;
GitLab, whose job already runs in the image, takes masked CI/CD variables). Unlike Java the image already carries
the .NET 10 SDK, so nothing is installed. **Cost:** a NuGet restore on every run unless a cache is mounted;
root-owned files on a Linux host; N2's GitHub and Azure "Running in the pinned image" bullets still describe the
container job, and the .NET UI gate filters do not yet exclude `TestCategory=visual` / `lighthouse` — G1's prompt
carries both reconciliations.

**D61 — The .NET Lighthouse fixture derives from `PlaywrightTest`, not `BaseTest`, and launches a persistent
Chromium context on a free port (N3, 2026-10-11).** N3's deliverable says every sample derives from `BaseTest`.
Lighthouse audits in its own tab in the browser's **default** context, through a remote-debugging port. `BaseTest`'s
browser is `BrowserTest`'s per-worker service launched from the runsettings (D32) — at best one fixed port per
worker, colliding across parallel workers — and its context is a non-default, per-test one, so a signed-in state
there never reaches Lighthouse. Readings: `BaseTest` plus a runsettings `--remote-debugging-port` (wrong context,
fixed port), J3's public-pages-only lane (D55; impossible on .NET's shared browser), or a `PlaywrightTest` fixture
calling `Playwright.Chromium.LaunchPersistentContextAsync("", …)` with a `TcpListener`-chosen port and
`SetStorageStateAsync(AuthSetup.UserState)` [1.59] for signed-in pages (chosen; no `Playwright.CreateAsync()`).
Lighthouse 13.5.0 clears only file systems, shader cache, service workers and cache storage before a run
(`core/config/constants.js`), so cookies and local storage survive. **Cost:** the one .NET sample outside
`BaseTest`; no trace, screenshot or video for a Lighthouse test — its JSON report and log are the evidence;
Chromium only; `SetStorageStateAsync` on a persistent context reaching Lighthouse's tab is unverified.

**D62 — §6.1's "nonexistent package" check matches the package id, not the namespace (N3, 2026-10-11).** The
`Eyes.Playwright` 1.37.49 assembly's public types live in `Applitools.Playwright` and `Applitools.Playwright.Fluent`
(read from its metadata), so `r"Applitools\.Playwright"` would fail every correct `using` line. Readings: keep the
pattern and write the Eyes sample without `using` lines (fully qualified names still contain the string), or match
the package id only — `Include="Applitools.Playwright"` in a `PackageReference` / `PackageVersion`, or
`add package Applitools.Playwright` (chosen). **Cost:** a prose mention of the wrong package name in a code block is
no longer caught; the references name the real package in prose.

**D63 — `responsive-testing` gains a `references/fixtures.md` (T4, 2026-10-11).** §3 names no reference for it, and
the skill had none. Moving the samples onto page objects and a measuring `Layout` fixture (R6, `aTS` C13) put the
SKILL.md at 18,916 chars. Readings: keep the fixture code inline and exceed §6.5's 16,000 for a skill this plan
rewrote, cut the geometry helpers to stay under it, or move `responsive.fixtures.ts` into a reference and keep a
summary in SKILL.md (chosen; 15,918 chars). **Cost:** one more file G1's checks read; the fixtures are one click away
from the samples that use them.

**D64 — Browser SSE is mocked as a fixed event set followed by `204`, never as a "stream" (T4, 2026-10-11).** `aTS`
D13 said to state the caveat or prefer the protocol-client test. `route.fulfill` ends the response after one body, so
`EventSource` reads every event at once and reconnects, fetching them again. Readings: the caveat alone, sending
every SSE scenario to a real server (a page that merely renders three notifications then needs one), or
`MockStreams.serveNotifications`: a `{ times: 1 }` route with the events registered over a route answering `204`,
which the SSE spec defines as "stop reconnecting" (chosen), with timing, reconnect and `Last-Event-ID` left to a real
SSE server. **Cost:** the mock proves rendering only; that `EventSource` stops on a routed `204` in all three
browsers is unverified until a suite runs it.

**D65 — A cloud grid holds one session per worker, and the session's verdict is marked once, in the worker
teardown (T4, 2026-10-11).** `aTS` C9 asked for `use.connectOptions` or a worker-scoped `browser`; the old fixture
marked status per test on a per-test session. Readings: keep a session per test (the billable shape C9 removes), mark
per test on a shared session (each test overwrites the last verdict), or collect failed titles in a worker fixture
and mark the session `failed` with them — or `passed` — before closing it, while an auto test fixture attaches the
session URL to each failed test (chosen; route 2). `use.connectOptions` (route 1) stays the zero-code route for a
suite that does not mark status. **Cost:** the dashboard shows one verdict per worker session, not per test; the
per-test link is the attachment; `getSessionDetails` / `hashed_id` are BrowserStack spellings carried from the old
skill and memory, unverified in this session.

**D66 — A Checkly browser-check spec states the R7 evidence modes itself with `test.use` (T4, 2026-10-11).**
`qa-evidence-capture-typescript` says the failure-evidence defaults live in the config asset only. Checkly runs the
spec under its own runner configuration, not the suite's `playwright.config.ts`, so the config's `trace`, `video` and
`screenshot` never reach a probe. Readings: leave probes on Checkly's defaults (what a failed run keeps is then
whatever the account does), a Checkly-side project setting (not verified in this session), or a file-level
`test.use({ trace: 'retain-on-failure', video: 'retain-on-failure', screenshot: { mode: 'only-on-failure', fullPage:
true } })` in each browser-check spec (chosen: plain Playwright semantics). **Cost:** a second place that states the
R7 values, scoped to `monitoring/src/__checks__/`; that Checkly keeps and shows what `test.use` asked for is
unverified, so the skill tells the reader to check one failed run before relying on it.

**D67 — J1's `BaseTest` gains a third hook, `protected Browser newBrowser(Playwright playwright)`, whose default is
the old local launch with the `HEADED` stamp (J4, 2026-10-11).** `browser-cloud-setup` must `connect(wsEndpoint)`,
and `BaseTest` launched Chromium inline in `@BeforeClass` into a private field. Readings: a second base class for
grid runs (the nine-lifecycles problem, `aJ` D22), a `BASE_URL`-style environment switch inside `BaseTest` that
builds vendor caps (vendor code in the one lifecycle), or one overridable method the `@BeforeClass` calls after
setting the test-id attribute (chosen; `lifecycle.md` §3 now tables the three hooks). A grid class subclasses the
test class it reruns and overrides `newBrowser`, as a device class overrides `contextOptions()`. **Cost:** an
override replaces the launch, so `launchOptions()` and `HEADED` no longer apply to that class; one more protected
member for G1's Java build to compile.

**D68 — A Java row matrix whose rows need different context options is a TestNG `@Factory`: one instance per row,
each instance's `contextOptions()` reading its row (J4, 2026-10-11).** Responsive widths and supported locales are
rows, but `BaseTest` builds the context from a per-class hook, and `aJ` D46 bans `setViewportSize` per test outside
live-resize specs. Readings: one subclass per width or locale (a file per row), a `@DataProvider` row plus
`page.setViewportSize` / a second context in the test (the live-resize path, and a raw `page` call in the test), or a
`@Factory` with a static, sequential data provider (chosen). TestNG runs `@BeforeClass` once per instance, so each row
gets its own browser on the class's one thread, and `parallel="classes"` holds. **Cost:** every row reports the same
method name and shares `<Class>.<method>` evidence files (the data-provider caveat `evidence-capture` already
states); a browser launch per row; the per-instance `@BeforeClass` is TestNG behaviour read from memory, not run.

**D69 — A Playwright grid class is one vendor session: its verdict is marked once in `@AfterClass` from the
failures TestNG recorded for that instance, and the session cap is set on a separate `testng-grid.xml` by an
`IAlterSuiteListener` reading `GRID_CONCURRENCY` (J4, 2026-10-11).** The old `GridWebTestBase` connected per method
and marked per method under `parallel="methods"` (`aJ` D3). With `BaseTest` a class holds one browser. Readings: mark
per test (the last test overwrites the verdict, as T4's D65 found), or once per class (chosen), with the dashboard link
attached at class level; Gradle's `threadCount` (a suite file's `thread-count` overrides it) or the listener
(chosen), on a suite file of its own so a local `./gradlew test` never connects to the grid. **Cost:** the dashboard
shows one verdict per class, not per test; the link sits in each test's tear-down, not on the failing step; a second
suite file and a `gridTest` task; the listener override and `getSessionDetails` / `browser_url` are unverified.

**D70 — The Java-native uptime probe keeps a failed run's trace, video and full-page screenshot under
`SYNTHETIC_EVIDENCE_DIR` through a `ProbeEvidence` component, in `BaseTest`'s hook order (J4, 2026-10-11).** The plan
asked to "catch the assertion error type and capture evidence". A Spring `@Scheduled` probe has no test runner, no
`build/` folder and no Allure report. Readings: a screenshot on failure only (no trace to read the cause from), the
probe writing into the app's working directory (lost on a pod restart, and a trace carries the synthetic user's
session), or recording every run and keeping it only on failure on a private volume with a 14-day lifecycle, named
`<check>.<UTC timestamp>` and announced in the warning log (chosen). The journey catches `AssertionError |
PlaywrightException` and records the result in `finally`, so a probe that cannot launch reads as a failed check.
**Cost:** a video and a trace recorded on every run; the volume and its lifecycle are the deployment's to provide;
the evidence is found through the log line and the alert annotation, not a report.

**D71 — `api-test-author/playwright` keeps its own `BaseApiTest` instead of extending J1's `BaseTest` (J4,
2026-10-11).** J4's deliverable says these skills extend `BaseTest`. `BaseTest` launches Chromium in `@BeforeClass` and
opens a context and page per test; an API-only class needs neither, only a `Playwright` and one `APIRequestContext`
per identity. Readings: extend `BaseTest` and use `page.request()` (a browser per API class, and one identity per
context), or keep `BaseApiTest` on the same lifecycle rules — instance fields, `alwaysRun` hooks,
`parallel="classes"`, no parallel data providers (chosen; a UI test still seeds through `page.request()`, lifecycle.md
§7). **Cost:** two base classes in the Java lane, one per kind of suite; a hybrid class that needs both a browser and
several API identities extends `BaseTest` and builds its extra request contexts itself.

**D72 — A Cucumber scenario's evidence name is `<feature file name>.<scenario name>` (J4, 2026-10-11).**
`evidence-capture` (J2) names the files `<Feature>.<Scenario>`. Cucumber-JVM's `Scenario` exposes the feature
file's URI, not the `Feature:` title. Readings: parse the title out of the `.feature` file in the hook (file I/O
and a Gherkin parse in teardown), or take the file name without `.feature` (chosen): `login.feature` +
`Sign in with a wrong password` → `login.Sign_in_with_a_wrong_password.{png,zip,webm}`. **Cost:** a feature file
named differently from its `Feature:` title shows the file name in the evidence; Scenario Outline rows share one
name, so two failing rows overwrite each other's files on disk (Allure keeps each).

**D73 — A .NET row matrix whose rows need different context options is a set of NUnit fixture parameters
(N4, 2026-10-11).** Responsive widths and supported locales are rows, but `BaseTest` builds the context from
`ContextOptions()`, and `aN` C-11 bans `SetViewportSizeAsync` per test outside live-resize specs. Readings: a
`[TestCase]` per width that reads `TestContext.CurrentContext.Test.Arguments` inside `ContextOptions()` (implicit
coupling to argument positions), a `[TestCase]` plus `SetViewportSizeAsync` in the test (the live-resize path and a
raw `Page` call), a subclass per row (a file per width), or `[TestFixture(width, …)]` / `[TestFixtureSource]` rows
passed to a primary constructor that `ContextOptions()` reads (chosen — the same shape the plan prescribed for
locales). Each row is its own fixture, so the rows run in parallel under `ParallelScope.Self`. **Cost:**
`BaseTest.EvidenceName()` is `<Class>.<Test>`, the same for every row, so two rows failing in one run write the same
files in `playwright-artifacts/` (and may race); the NUnit result, TRX and Allure keep the rows apart. Putting the
fixture arguments into `EvidenceName()` is an edit to N1's asset, outside N4's paths — a later plan's call.

**D74 — A .NET cloud-grid run overrides `BrowserTest.ConnectOptionsAsync()` on a grid fixture derived from the test
class it reruns, in its own `TestCategory=grid` run (N4, 2026-10-11).** `BrowserTest` registers the browser per
worker, and the first fixture on a worker decides launch-or-connect for every later one (D32). Readings: a `GRID`
environment switch inside `BaseTest` (vendor code in the one lifecycle, and N1's asset), a separate `UiTests.Grid`
project (no filter, but the root `AuthSetup` would not cover it), or a `[Category("grid")]` subclass in
`Example.UiTests.Grid` whose `ConnectOptionsAsync()` returns BrowserStack's flat-caps endpoint, run with
`--filter TestCategory=grid -- NUnit.NumberOfTestWorkers=$GRID_CONCURRENCY` (chosen). The session cap is the worker
count (one session per worker). The verdict is marked per test from the grid fixture's `[TearDown]`: a failed test
makes the worker dispose its browser, so a session's only failure is always its last mark. The tunnel's
`[SetUpFixture]` sits in the grid namespace, so a local run never opens it. **Cost:** the local/PR UI filter must
exclude `TestCategory!=grid` (G1's D60 seam line now names it); `ConnectOptionsAsync()`'s signature
`Task<(string, BrowserTypeConnectOptions?)?>` is from memory of the v1.63 sources — N4 had no web access — and no
asset compiles it; `getSessionDetails` / `browser_url` remain BrowserStack spellings from T4/J4.

**D75 — The .NET Playwright API base derives from `PlaywrightTest` and opens its identity contexts per test (N4,
2026-10-11).** The old `BasePlaywrightApiTest` called `Playwright.CreateAsync()` in `[OneTimeSetUp]` — E11's
blocker shape. Readings: keep a per-fixture `IPlaywright` as Java's D71 does (E11 would fire on the library's own
recipe), or `BasePlaywrightApiTest : PlaywrightTest` — the driver from `PlaywrightTest`'s `[SetUp]`, contexts built in
the fixture's `[SetUp]` from a cached token and disposed in the base `[TearDown]`, `ParallelScope.Self` (chosen; the
playwright.dev .NET API-testing sample has the same shape). **Cost:** a context per test instead of per fixture
(cheap — no browser), and the .NET and Java API bases now differ in lifecycle; the fixture moved to a new
`references/templates.md` to keep SKILL.md ≤ 16,000 chars. The skill's test names moved to `Should_X_When_Y` (R4),
so it no longer shares the RestSharp writer's `[Action]_[Condition]_[ExpectedOutcome]` shape.

**D76 — The .NET uptime probe catches only `PlaywrightException`, keeps evidence through `ProbeEvidence`, and runs
as a scheduled container from the pinned image (N4, 2026-10-11).** `aN` D-20 found a blanket `catch (Exception)`, no
evidence, `ct` unused, no `BaseURL` and no word on installing browsers. Readings: catch `Exception` and log (what
D-20 rejects), no catch (a failed assertion would skip recording its message), or catch the one named exception
every Playwright action timeout and `Expect` failure throws in .NET, record the verdict in `finally`, and keep trace,
screenshot and video on failure in `BaseTest`'s order under `SYNTHETIC_EVIDENCE_DIR` (chosen, as J4's D70). Host:
a Timer Function on Consumption (cannot launch Chromium), or an Azure Container Apps job on a cron trigger built
`FROM mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`, with a Premium/Dedicated custom container as the
alternative (chosen). **Cost:** a trace and video recorded on every run; the volume and its 14-day lifecycle are the
deployment's to provide; that every .NET `Expect` failure is a `PlaywrightException` is read from memory of the
assertion implementation, not run.

**D77 — The token-seeded signed-in state is a second body of N1's `AuthSetup`, not a new class (N4, 2026-10-11).**
`aN` D-21 found a product URL, a second path convention and no storage-state limits. Readings: a separate
`TokenAuthSetup` writing its own file (two state paths, and fixtures would have to choose), or the same root-namespace
`AuthSetup` class with the same `UserState` (`<WorkDirectory>/auth-user.json`), its body minting a token, building
the context with `StorageState` at `BASE_URL`'s origin, checking the greeting, then saving (chosen). **Cost:** a
project picks one body; the storage key is the app's and must be looked up; the device-code poll moved from a
catch-and-continue on `ErrorApiException` to reading the JSON `error` field over `HttpClient`.

**D78 — The Reqnroll scaffold references `Microsoft.Playwright.NUnit`, shares the UI runsettings, and closes after
every other hook (N4, 2026-10-11).** Readings for the package: `Microsoft.Playwright` directly (a new
`PackageVersion` line, and the hook would hardcode the browser), or `Microsoft.Playwright.NUnit` 1.63.0, already
pinned by N1, bringing `PlaywrightSettingsProvider` (chosen; `RunSettingsFilePath` points at
`../UiTests/ui.runsettings`). Readings for the browser's lifetime: per test run (a static field or a container
lifetime the hooks cannot see) or per scenario (chosen, as J4's Cucumber hooks). The closing hook is
`[AfterScenario(Order = 20_000)]` so cleanup hooks at the default 10,000 run first; `using` / `await using` close the
driver and browser without a `try`/`finally`. Reporting is `Allure.Reqnroll` 2.15.0 with `Allure.ReqnrollPlugin`
in `reqnroll.json`'s `bindingAssemblies`. **Cost:** a browser launch per scenario; Reqnroll's ascending order for
after-hooks, the `Allure.Reqnroll` package id, its plugin assembly name and Reqnroll 3.3.4 being current are from
memory, unverified (no web access); none of these files is an asset G1 compiles.

**D79 — The checklist's E11 keeps one exception and lists the documented owners it does not reach (N4,
2026-10-11).** E11 flags `Playwright.CreateAsync()` in a `[Test]`, `[SetUp]` or a fixture's `[OneTimeSetUp]`, with
the root `AuthSetup` as the one exception (review/SKILL.md). Five recipes in the library own their lifecycle without
that call or outside a test fixture: the Reqnroll hook (D78), the Lighthouse `PlaywrightTest` fixture (D61), the
API base (D75), a grid fixture (D74) and the uptime probe (D76). Readings: widen the exception list inside E11's
row (it stops reading as one rule), or keep E11 as review/SKILL.md words it and add a note under section E naming
those five as not E11 findings (chosen). **Cost:** an auditor must read the note; a new lifecycle owner elsewhere
needs a line there.

**D80 — The Android test-id rung needs the id-prefix setting, and one `byTestId` helper picks the rung per
platform (M1, 2026-10-11).** The plan's ladder (D6, plan 002 §8.5) says a React Native `testID` is the iOS `name`
and the Android `resource-id`. UiAutomator2 prefixes every `id` lookup with `<package>:id/` unless the setting
`disableIdLocatorAutocompletion` is on, and a React Native or Compose id carries no prefix (UiAutomator2 README,
Settings API). Readings: write `$('id=Login.Submit')` and leave the prefix to the reader; or set
`'appium:settings[disableIdLocatorAutocompletion]': true` in the asset capabilities, explain when to leave it off
(a Views app whose ids carry the package), and give `BasePage` one `byTestId` (`~id` on iOS, `id=id` on Android)
plus `testIdSelector` for components (chosen). **Cost:** a Views app flips the setting; the mapping and the
setting are from the driver README and secondary sources, not a device run (G1, and the user's first device run,
settle it). M2 and M3 write the same ladder and setting.

**D81 — On WDIO 10 BrowserStack connects without a vendor service, and the status is set in the config's
`afterTest` (M1, 2026-10-11).** The plan says the farm runs through `wdio.conf.ts` plus a service (`aM` L6).
`@wdio/browserstack-service` was at 9.39.4 on 2026-10-11 with a peer of `@wdio/cli` ≤ 9, so it does not install on
WDIO 10; `@wdio/sauce-service` has a 10.0.2. Readings: stay on WDIO 9 for every BrowserStack project; or connect
through `hostname` / `user` / `key` and `bstack:options` in a second config that imports the local one, and mark the
session with the `setSessionStatus` executor (chosen, with the service named where one exists). **Cost:** a hand-rolled
status call, and `browser-cloud-setup` (T4) still describes the service doing it; `device-cloud` states how to check
the vendor's Appium version before bumping, and the supported lane stays WDIO 9.

**D82 — The asset recording uses `startRecordingScreen`, and the `mobile:` recorders are a documented swap
(M1, 2026-10-11).** §3.2 allows either. `startRecordingScreen` works on every supported OS and API level;
`mobile: startMediaProjectionRecording` needs Android 10+ and `mobile: startXCTestScreenRecording` iOS 17+. Readings:
default to the native recorders and branch on the platform version in the hook; or default to
`startRecordingScreen` with `timeLimit: 180` and `forceRestart`, and show the swap in `references/appium.md` §4.1
(chosen). **Cost:** Android tests over 180 s need ffmpeg on the Appium host, and iOS needs ffmpeg always; the
reference states both.

**D83 — The TS Appium assets include `package.json`, `tsconfig.json` and `env.ts`, and `device-cloud` gained a
reference file (M1, 2026-10-11).** §3.4 lists a config, a base test, a screen object and a test. A compiled asset
set needs exact pins and a strict config, and the config, the spec and the scaffold share one `requiredEnv`, so
they are assets too (the page objects and the component are four files, not one). `device-cloud/SKILL.md` was
28.1k chars and had to come under 16,000, so the AWS orchestration class moved to
`references/aws-device-farm.md`. **Cost:** ten asset files and a G1 install line that must come from
`assets/package.json`.

**D84 — The Java Appium assets add `Env.java`, `settings.gradle.kts`, `testng.xml` and split the page objects into
four files, and one `AppiumDriver` is built per class (M2, 2026-10-11).** §3.4 lists a base test, a driver
factory, a screen object and a test, plus the build file. The factory, the base test and the test share one
`required(name)`, so it is a file; a compiled Gradle project needs its settings and a suite file for
`parallel="classes"` (D8); and the scoped component is its own class (`OrderRow`), as in M1. Readings for the lifetime:
a driver per method (a fresh app state per test, a session start per test), or a driver per class (chosen,
R8, with `terminateApp` / `mobile: clearApp` for a cold state). **Cost:** tests in one class share app state, and a
class never runs on two devices at once. `testng.xml` keeps `thread-count="1"`: parallel classes need one device and
unique ports each, which the skill states.

**D85 — `putBytesToPresignedUrl` is implemented with the JDK's `HttpClient`, and the AWS orchestrator moved to
`references/aws-device-farm.md` (M2, 2026-10-11).** `aM` C4 offers an implementation or a throw. Readings: throw
`UnsupportedOperationException`; or implement the `PUT` (chosen), throwing `IllegalStateException` with the file name
and status on anything but `200`, so a failed upload is never a five-minute poll timeout. **Cost:** a `PUT` that rests
on memory of Device Farm's presigned URLs (no `Content-Type` header), and an `IOException` /
`InterruptedException` that `uploadAndAwait` declares instead of catching. `device-cloud/SKILL.md` was 17.8k chars,
so as in D83 the class left it; its device matrix is a `@Factory` fed by a sequential `@DataProvider` (D8 bans
`@DataProvider(parallel = true)` with Appium), and the farm test's driver is quit in `@AfterClass`.

**D86 — The mobile Cucumber hook lives in `bdd-project-scaffold/references/hooks.md`, captures a screenshot and
the page source only, and quits the driver in a lower-order `@After` (M2, 2026-10-11).** J4's `Hooks` is the web
hook. Readings: extend `Hooks` with `@mobile` branches; or a second `MobileHooks` class (chosen, per `@Before("@mobile")`
in the file's own note). It keeps D72's `<feature file>.<scenario>` names under `build/appium-artifacts/`, runs
evidence at `order = 1` and `quitDriver` at `order = 0` (Cucumber runs `@After` from the highest order down), and
leaves the recording to `BaseMobileTest`'s pattern. **Cost:** a scenario has no device log or recording; one driver per
scenario is the slow shape.

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
- **As built (2026-10-10):**
  - Landed: `evidence-capture/SKILL.md` (15,745 chars; description 489) and `references/playwright.md`
    (§1 screenshots … §11 size and CI). Both agents wired. `test-reports` rewritten on allure-java 3.0 (15,964
    chars; the Playwright failure attacher is gone), `flaky-test-quarantine` (14,698) and its `details.md`
    rewritten to D7, and all three Java CI references rewritten: Playwright UI job with the
    `installPlaywrightBrowsers` step, no `-Pheadless`, `build/playwright-artifacts/` on failure, the pinned
    Allure CLI, and a new Azure `playwright-ui.yml` template. Marketplace entry added; T2's catalog row now
    reads "— java · typescript (dotnet next)". `ci-conventions` is unchanged: no per-stack split.
  - Checked live today: the allure-java 3.0.0 release notes and Allure's *Migrating to Allure Java 3* guide
    (allurereport.org/docs/guides/allure-java-3-migration): "Results produced by Allure Java 3 can be viewed in
    both Allure Report 3 and Allure Report 2", "The format of the result files written to disk is unchanged",
    TestNG/JUnit 4 history restarts once, attachments shown as steps, results-dir cleanup removed. allure2
    2.46.0 (2026-08-28) "Support run-level errors and attachments" pairs with allure-java PR #1372
    (`{uuid}-globals.json`). allure-gradle 4.3.0 README: "By default `allure-gradle` provisions Allure 3";
    `allure.version` 2.x switches to `allure-commandline`; `autoconfigure` and `aspectjWeaver` default true;
    TestNG ≥ 7.10 for SDK 3; mixed 2.x/3.x adapters rejected. Maven Central: `allure-commandline` 2.46.1;
    `allure-testng`, `allure-rest-assured`, `allure-jupiter`, `allure-cucumber7-jvm`, `allure-bom` 3.0.0. npm
    `allure-commandline` 2.46.1. Allure categories file: `flaky (boolean)` matcher. playwright-java v1.63.0
    sources: `Screencast.start` → `AutoCloseable` (`StartOptions` path/size/quality/onFrame; no `setFps`),
    `ShowActionsOptions` position/cursor/duration/fontSize (no `setStyle`), `showOverlay`/`showActions` →
    `AutoCloseable`; `AnnotatePosition` `TOP_LEFT…BOTTOM_RIGHT`; `Tracing.StartOptions`
    `setAriaSnapshots`/`setScreenSnapshots`/`setLive`, `startHar` and `group` → `AutoCloseable`;
    `Page.ScreenshotOptions` setters; `NewContextOptions.setRecordHar*`/`setRecordVideo*`; `HarContentPolicy`
    `OMIT/EMBED/ATTACH`; `Locator.describe`; `Page.AriaSnapshotOptions` + `AriaSnapshotMode.AI`. playwright
    v1.63.0 `packages/playwright-core/src/cli/program.ts` calls `addTraceCommands`; `traceUtils.ts` keeps the
    open trace in `.playwright-cli/trace`. playwright-java v1.63.0 `utils/docker/Dockerfile.noble`: OpenJDK 25 +
    Maven 3.9.12, no JDK 21, no Gradle. Playwright v1.63.0 `docs/src/ci.md`: the Java GitHub container example
    uses `--user 1001` + `actions/setup-java@v5`.
  - Differed from the plan: the report generator stays allure2 2.46.1 and J1's build pins it as
    `allure.version` (D38); the trace analysis CLI is documented through Node and the Java driver, correcting
    J1's lifecycle.md §8 (D39); CI installs browsers on the runner, the pinned image is the visual-baseline
    variant (D40); quarantine filters the one `testng.xml` and the category matches `"flaky": true` (D41).
    `test-reports` keeps only the GitHub publish snippet (Azure/GitLab publish live in the CI references) to
    stay ≤ 16,000 chars. `BaseTest.java` and lifecycle.md §5 are unchanged: no default had to change.
  - Names assigned: deliberate recordings `build/playwright-artifacts/<Class>.<method>.<kind>.<ext>`
    (`receipt.webm`, `.har`); helper `com.example.uitests.support.Evidence.screenshot(name)`; Cucumber
    scenario evidence `<Feature>.<Scenario>` with characters outside `[A-Za-z0-9._-]` replaced by `_` (J4
    writes the hook); exploratory evidence `evidence/<YYYY-MM-DD>-<topic>/`; hotspot analyzer
    `support.RetryOnce`; Gradle task `flakyQuarantine`; CI artifacts `playwright-artifacts-<n>` (failure, 14
    days), `allure-results-ui-<n>` / `allure-results-api-<n>` (30 days); Azure template
    `pipelines/templates/playwright-ui.yml`, job `PlaywrightUi`; shards 1-based (`shard-<i>-of-<N>`).
  - Built, unverified (Gate: none): nothing compiled or ran. Open points: the trace CLI through
    `./gradlew playwright --args="trace …"` (D39); whether a screencast's path is written while `BaseTest`'s video
    runs; `tracing().startHar` beside `BaseTest`'s trace; Gradle `excludeGroups`/`includeGroups` applied to a suite
    XML (TestNG's command-line groups override the suite's); the plugin's `copyCategories` running without an
    explicit call; the GitLab jobs' `aws` CLI in `eclipse-temurin:21-jdk` (a pre-existing assumption, now stated
    in the reference); `dorny/test-reporter` on TestNG's JUnit XML.
  - Proof: `name: qa-evidence-capture-java` and the Appium placeholder at
    `qa/java/skills/evidence-capture/SKILL.md:2,13`; R7 defaults `:64`; raw tracing and assertions `:98`; Cucumber
    `:104`; exploratory MCP ↔ CLI `:132`; reading a failure `:157,166`; PII `:179`. Reference: enum position
    `references/playwright.md:161`, helper catch `:176,183`, `setAriaSnapshots` `:216`, `group` `:238`, `startHar`
    `:267`. Agents: Mode A `qa/java/agents/qa-ui-java.md:85`, Step 1 `:113`, BDD Step 4
    `qa/java/agents/qa-bdd-java.md:105`. `test-reports/SKILL.md`: pins `:34`, live check `:39`, Gradle `:68,70`,
    migration table `:86`, defer to `BaseTest` `:162`. `flaky-test-quarantine/SKILL.md`: retries `:13`, `RetryOnce`
    `:101`, gate `:154`, quarantine task `:159`, category `:201`. CI: install `github-actions.md:267`,
    `gitlab-ci.md:205`, `azure-pipelines.md:225`; failure upload `github-actions.md:304`, `gitlab-ci.md:222`,
    `azure-pipelines.md:261`; Azure UI template `azure-pipelines.md:85,205,214`; Allure pin
    `github-actions.md:358`, `gitlab-ci.md:256`, `azure-pipelines.md:309`. J1 edits:
    `assets/build.gradle.kts:24`, `ui-test-author/playwright/SKILL.md:23`, `references/lifecycle.md:202`.
    Marketplace `.claude-plugin/marketplace.json:75`; catalog `docs/skills-catalog.md:60`.

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
- **As built (2026-10-10):**
  - Landed: `evidence-capture/SKILL.md` (15,620 chars, ~380 left for M3's Appium line; description 488) and
    `references/playwright.md` (§1 screenshots … §11 size and CI). Both agents wired (Step 0 gate → the
    `BaseTest` asset, Step 1, Mode A trace reading; BDD Step 4). `test-reports` rewritten (13.7k): defers to
    `BaseTest`, `AttachBody` passes UTF-8 bytes with `".json"`, the overload table, `[AllureNUnit]` required,
    `categories.json` copied into the results by the publish job, the CI YAML moved out to the CI references.
    `flaky-test-quarantine` rewritten to D7 (14.5k). `ci-pipelines/SKILL.md` gained the shared
    `ci/nunit-shards.sh` and its rules; all three CI references rewritten with a shards job per sharded suite,
    the class filter per shard (API too), `playwright-artifacts-<n>` on failure, the pinned Allure CLI, and no
    YAML comments (R5). Marketplace entry added; T2's catalog row now ends "— dotnet · java · typescript".
  - Checked today: nothing live. WebFetch, WebSearch and reads outside the repo were denied in this
    unattended session, so every API spelling comes from `playwright-evidence.md` (§1.1, §3, §4.1, §4.3,
    §5.2, §6, §10, §11.3) and from N1's As-built facts. Not verifiable here and not taught as fact beyond
    them: whether `pwsh` is in `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` (no CI step relies on it,
    D45); NUnit adapter's `NUnit.DisplayName=FullName` in `--list-tests`, and the VSTest filter's `\(` escape
    (D44); `TracingStartHarOptions.Mode`; `AllureApi.AddScreenDiff`'s parameter order; that Allure.NUnit
    turns NUnit categories into tags (D46); NUnit 4.6.1's `[Retry]` behaviour on exceptions (the skill
    quotes the documentation and tells the reader to check).
  - Differed from the plan: `BaseTest`'s `EvidenceName()`, `Artifact()` and `Attach()` became protected
    (D42); the trace analysis CLI is documented through Node and `playwright.ps1`, replacing lifecycle.md
    §9's "Node-only" sentence (D43); the sharding mechanics (D44); runner-installed browsers on GitHub and
    Azure, the image on GitLab (D45); the quarantine bucket matches the history flag, not the NUnit category
    (D46). Beyond the plan: the API shards also use the class filters (their `NUnit.Where` modulo stand-in
    was not valid NUnit syntax); the GitHub reusable workflows declare their own `env:` (a called workflow
    does not inherit the caller's, so `${{ env.DOTNET_VERSION }}` and `$BUILD_CONFIGURATION` were empty);
    `actions/checkout@v6` and `upload/download-artifact@v5` as T2 verified, `setup-dotnet` kept at `@v4`
    (v5 not verifiable today); every Allure results path is `<Project>/bin/<cfg>/net10.0/allure-results`
    (the three files disagreed); `simple-elf/allure-report-action` and the allure2 2.27.0 / npm 2.30.0
    pins replaced by `allure-commandline@2.46.1`; `[Retry(1)]` (one attempt, no retry) replaced by
    `[Retry(2)]`; the custom `RetryOnFailure` attribute, the TRX-rerun step and `FlakyMarkBase` (whose
    `tc.flaky` is not an Allure.NUnit member) removed; test-reports' "Flaky timeouts" bucket renamed
    "Timeouts".
  - Names assigned: `ci/nunit-shards.sh <project> <shards> <dir>` writing `<dir>/<i>.filter` (1-based);
    GitHub job `plan` (output `shards`), Azure jobs `ApiShards` / `UiShards`, GitLab jobs `api-shards` /
    `ui-shards` writing `shards/{api,ui}/`; shard-file artifacts `api-shards` / `ui-shards` (1 day); CI
    artifacts `playwright-artifacts-<n>` (failure, 14 days), `allure-results-ui-<n>` / `allure-results-api-<n>`
    (30 days); helper `Example.UiTests.Support.Evidence.ScreenshotAsync(name)`; deliberate recordings
    `<Class>.<Test>.receipt.webm` and `<Class>.<Test>.har` via `Artifact(EvidenceName(), "<kind>.<ext>")`;
    Reqnroll scenario evidence `<Feature>.<Scenario>` (sanitized), kept when `ScenarioContext.TestError` is
    set (N4 writes the hook); exploratory evidence `evidence/<YYYY-MM-DD>-<topic>/`; the categories bucket
    "Known flaky (quarantined)" first with `"flaky": true`.
  - Built, unverified (Gate: none): nothing compiled or ran. Open points: `ci/nunit-shards.sh` against a
    real `--list-tests` output (D44); the trace CLI through `playwright.ps1` (D43); the protected helpers
    compile (G1's .NET build); a screencast's path while `BaseTest`'s video runs; `StartHarAsync` beside
    `BaseTest`'s trace; the GitLab jobs' `aws` CLI in the SDK and Playwright images (a pre-existing
    assumption, now stated). One check did run: `python3 -m json.tool .claude-plugin/marketplace.json`
    (exit 0) after the marketplace edit — G1's §6.1 step 1, run early, as T2 did.
  - Proof: `name: qa-evidence-capture-dotnet` and the Appium placeholder at
    `qa/dotnet/skills/evidence-capture/SKILL.md:2,13`; R7 defaults `:61`; Reqnroll naming `:105`; deliberate
    recordings and D42 `:108,116`; exploratory MCP ↔ CLI `:133`; reading a failure and D43 `:157,167`; PII
    `:178`. Reference: receipt start/stop `references/playwright.md:148,166`; `AriaSnapshots` `:192`;
    `StartHarAsync` `:245`; `AddScreenDiff` and the three-string trap `:275,277`; trace CLI `:301`. `BaseTest`
    helpers `ui-test-author/playwright/assets/BaseTest.cs:93,96,99`; lifecycle.md `:157,234`. Agents: Mode A
    `qa/dotnet/agents/qa-ui-dotnet.md:75`, Step 0/1 `:97,98`, BDD Step 4 `qa/dotnet/agents/qa-bdd-dotnet.md:87`.
    `test-reports/SKILL.md`: pin `:34`, bytes `:147`, `BaseTest` owns it `:155`, CLI `:209`, bucket `:230`.
    `flaky-test-quarantine/SKILL.md`: hotspot `:92,103`, gate filter `:133`, bucket `:162`. Script
    `qa/cicd/dotnet/skills/ci-pipelines/SKILL.md:52,59`. CI: shards job `github-actions.md:135,295`,
    `azure-pipelines.md:127,259`, `gitlab-ci.md:122,131`; shard filter `github-actions.md:347`,
    `azure-pipelines.md:302`, `gitlab-ci.md:235`; failure upload `github-actions.md:365`,
    `azure-pipelines.md:322`, `gitlab-ci.md:242`; GitLab image `gitlab-ci.md:217`; runner install
    `github-actions.md:326`, `azure-pipelines.md:284`; Allure pin `github-actions.md:422`,
    `azure-pipelines.md:374`, `gitlab-ci.md:275`. Marketplace `.claude-plugin/marketplace.json:224`; catalog
    `docs/skills-catalog.md:60`.

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
- **As built (2026-10-10):**
  - **Grants.** The six agents' `tools:` line (`:4` in each of `qa/{typescript,java,dotnet}/agents/qa-{ui,bdd}-<stack>.md`)
    is `Read, Write, Edit, Bash, Glob, Grep, WebSearch` plus §5.2's 33 names in §5.2's order;
    `grep -rhoE 'mcp__playwright__[a-z_]+' qa/ | sort -u` prints exactly those 33.
  - **`qa-ui-*` live-page workflow** (TS/Java `:39`, .NET `:38`): the two-sentence prerequisite (§5.4's registration;
    `webmcp_*` not granted, on purpose), step 2 names the `playwright-cli` fallback through `Bash` and stops only
    when neither route is available, and step 3 is R2 (the `missing-testids.md` row names page, element and
    fallback; no marker). The loading protocol names `qa/_shared/webmcp-testing/` (TS/Java `:18`, .NET `:18` as
    a full path beside the shorthand), and Step 3 loads its SKILL.md + `references/<stack>.md` (.NET notes the
    separate `webmcp.runsettings` run).
  - **`page-objects-from-url` ×3** (15.1k / 15.3k / 15.4k chars): §5.4's registration, `--codegen=java|csharp`
    (Java/.NET) and `--test-id-attribute`, `--no-webmcp`; `browser_verify_element_visible` to confirm the page;
    `browser_find` for one element; hover / press-key / tabs / back for dynamic states; `browser_generate_locator`
    per ref; a harvest with a `const attribute` first line, and the shadow-root / iframe blind spots; the attribute
    in code (TS config `testIdAttribute`, Java `BaseTest.TEST_ID_ATTRIBUTE` → `setTestIdAttribute`, .NET runsettings
    `TestIdAttribute`, which overwrites a code call); R2 and R3 (`Login.Submit`, `Login.PasswordReveal`, static row
    ids); a "`playwright-cli` route" section with a step → MCP tool → CLI command table (§5, §7a–§7d).
  - **`qa/_shared/webmcp-testing`** (`qa-webmcp-testing-shared`): SKILL.md 15,831 chars with frontmatter
    (body ≈ 15.3k), description 483 chars;
    `references/{typescript,java,dotnet}.md`; assets `webmcp.spec.ts` + `ProductPage.ts`, `WebMcpTest.java` +
    `ProductPage.java`, `WebMcpTests.cs` + `ProductPage.cs` + `webmcp.runsettings` — five `Should_X_When_Y` tests per
    stack on one example contract (`/products/sku-123`, `add_to_cart`, `Cart.Badge`). The `ProductPage` files and
    the two-script evaluate route are D47 and D48. The SKILL.md names the removed early-2026 members once, as stale
    material that is a finding, and teaches none of them.
  - **TS launch flag:** the file-level `test.use({ launchOptions: { args: ['--enable-features=WebMCP'] } })`;
    `playwright.config.ts` is unchanged, so the spec runs in `chromium` (signed in, after `setup`), tagged
    `@webmcp`. The dedicated-project form is in `references/typescript.md` §1. Java tests are group `webmcp`;
    .NET's fixture is `[Category("webmcp")]`.
  - **Wiring:** `./qa/_shared/webmcp-testing` in all three qa plugins (`grep -c` → 3); one catalog row under
    "Cross-stack"; one cross-reference line at the end of each `ai-feature-testing` "Cross-references".
  - **Built but unverified:** nothing compiled or ran (G1). Open risks: `Page['webmcp']` and the 1.64 `tools()`
    typing under strict TS; `asInstanceOf(InstanceOfAssertFactories.MAP)` with AssertJ 3.27.7; the C# raw-string
    scripts; and — beyond G1's reach — whether Chromium 153's `getTools()` / `executeTool()` behave as webmcp.md §3
    says, since no test ran against a site that registers tools.

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
- **As built (2026-10-10):**
  - Landed: all eleven files rewritten — three routers (`visual-regression` 4.7k, `accessibility-testing` 3.8k,
    `network-mocking` 4.2k chars; descriptions 484 / 460 / 492, all saying "Playwright Test") and eight
    references (`playwright-snapshots` 13.6k, `percy` 9.0k, `applitools` 9.8k, `axe-playwright` 10.4k,
    `lighthouse-ci` 10.1k, `playwright-routes` 18.9k, `cdp` 12.1k, `proxy` 14.9k). Every sample extends the
    writer's `fixtures.ts`; no spec constructs a page object or calls `page`; PascalCase test ids; no
    comments, `try`/`finally` or `allure-playwright` import in any code block (scripted scan of every fence).
    `qa-ui-typescript.md` Step 3's a11y item is the router only.
  - Differed from the plan: the nightly lane is a `visual` project with `default: false` (and a
    `lighthouse` one with `workers: 1`), taught as config additions, not added to T1's asset (D49); the
    no-assertion exception is recorded per test with an annotation on Percy, Applitools and `playAudit` tests
    (D50); a11y and Lighthouse evidence go through awaited `testInfo.attach`, and the only direct Allure call
    left is the Percy build link (D51); the proxy reference uses Vitest fixtures and endpoint
    `getSeenRequests()`, and its HAR writer became a scrubbed JSON traffic log (D52). Beyond the plan:
    security headers and TLS moved from `cdp.md` to `playwright-routes.md` §5 (D9 of `aTS`), so CDP lost its
    `responseFor` audit and its `Offline` preset (routing owns offline); `cdp.md` captures `fromDiskCache` and
    reads the **last** match; Lighthouse drops the PWA category (removed in Lighthouse 12); Chrome's
    `--proxy-bypass-list=<-loopback>` added for localhost targets; the Applitools region calls are
    `layoutRegions` / `ignoreRegions` (the old `.layout(selector)` / `.floating(...)` spellings are gone).
  - Names assigned: fixture files `visual.fixtures.ts` (`frozenClock` auto, `visualNow`), `percy.fixtures.ts`
    (`percy`, `percyBuildLink` auto, `percyReview`, `byTestId`), `eyes.fixtures.ts` (`eyesRunner` worker,
    `eyes`), `a11y.fixtures.ts` (`a11y.scanPage` / `scanWithin(testId)`, `wcag22aa`, `knownViolations`,
    `falsePositives`, `newViolations`, `blockingViolations`), `lighthouse.fixtures.ts` (`browser` worker
    override, `lighthouse.audit`, `lighthouseGate`), `network.fixtures.ts` (`MockApi`, `Traffic`),
    `cdp.fixtures.ts` (`CdpControls`), `proxy.fixtures.ts` (`ProxyControls`, `ShopPages`); env
    `HAR_UPDATE=1` re-records the payments HAR; spec suffixes `.visual.spec.ts`, `.lighthouse.spec.ts`.
  - Built, unverified (Gate: none): nothing compiled or ran. **This session had no web access**
    (WebFetch was denied), so every vendor spelling rests on the committed research or the existing skill
    text: `PERCY_BUILD_URL` set by `percy exec`; `Parameters<typeof percySnapshot>[2]`; Applitools
    `layoutRegions` / `ignoreRegions` and its gate error naming the dashboard link; the `playAudit` report
    being written before its threshold throw (the teardown attach depends on it) and Lighthouse's tab seeing
    the test context's sign-in (the reference tells the reader to check the report); overriding the built-in
    `browser` worker fixture typing cleanly; mockttp relative-path matchers and `thenJson`; Vitest
    `test.extend` with `({}, use)`. `page.requests()` is described as a capped buffer without a number. The
    TS CI references (T2's) have no step that runs `--project=visual`, so with `default: false` a nightly
    plain run skips the visual specs — G1's prompt now carries that reconciliation.
  - Proof: `qa/typescript/skills/visual-regression/references/playwright-snapshots.md` image + `--ipc=host` +
    in-container `npm ci` `:212-216`, `default: false` `:51`, `pathTemplate` `:35`, `setFixedTime` `:121`,
    WebP `:187`, PDF `:177`, modes `:199-201`, no re-attach `:233`; `percy.md` annotation `:89,134`, awaited
    `allure.link` `:105`; `applitools.md` worker runner `:92-94`, teardown close `:101`; `axe-playwright.md`
    `wcag22aa` `:58`, incompletes attached `:93`, assertions link `:43`; `lighthouse-ci.md` worker browser
    `:127`, `workers: 1` `:90`, attach `:143`; `playwright-routes.md` 1.52 `:345`, `recordHar` via
    `contextOptions` / `startHar` `:308-309`, `page.requests()` `:136`, `allHeaders()` `:265`,
    `securityDetails()` `:276`, `context().route` `:106`, `updateContent` `:114`, URLPattern `:344`, awaited
    `continue` `:94,101`, typed payload `:212`, realtime link `:23`; `cdp.md` last match `:124,202`;
    `proxy.md` teardown `:157,167`, fault assertion `:291`; `qa/typescript/agents/qa-ui-typescript.md:117`.

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
- **As built (2026-10-11):**
  - Landed: all eleven files rewritten — three routers (`visual-regression` 6.2k, `accessibility-testing` 4.4k,
    `network-mocking` 4.4k chars; descriptions 499 / 461 / 496) and eight references (`playwright-snapshots`
    23.5k, `percy` 9.1k, `applitools` 11.5k, `axe-playwright` 12.9k, `lighthouse-ci` 12.9k, `playwright-routes`
    21.5k, `cdp` 15.1k, `proxy` 14.5k). Every Playwright sample extends `com.example.uitests.support.BaseTest`,
    changes the context only through `contextOptions()` and the launch only through `launchOptions()`, and builds
    its helpers and page objects in its own `@BeforeMethod(alwaysRun = true)`; no `Playwright.create()`, no
    `try`/`finally`, no `Thread.sleep`, no comment and no `Allure.addAttachment` in any code block; PascalCase
    test ids; `Should_X_When_Y` names (scripted scan of every fence; the only hits were the `/*` inside globs).
  - **The comparator, checked on Maven Central today:** `com.github.romankh3:image-comparison:4.4.0` — the
    latest on Central (metadata `lastUpdated` 2021-03-28; a `v4.5.0` git tag was never published), pure JDK/AWT,
    Java 8+. Its API was read at the `v4.4.0` tag: `new ImageComparison(BufferedImage, BufferedImage)`,
    `setAllowingPercentOfDifferentPixels`, `setPixelToleranceLevel`, `setExcludedAreas`, `compareImages()` →
    `ImageComparisonResult` with `getImageComparisonState()` (`MATCH` / `MISMATCH` / `SIZE_MISMATCH`), `getResult()`
    and `getDifferencePercent()` (mean colour difference, `0` on a match — so the gate is the state).
  - Also checked today: Maven Central — `io.percy:percy-playwright-java` 1.2.1, `com.applitools:eyes-playwright-java5`
    5.86.9, `com.deque.html.axe-core:playwright` 4.13.0, `com.browserup:browserup-proxy-core` 2.1.2 (Dec 2020; the
    GitHub repo is archived), `org.seleniumhq.selenium:selenium-java` 4.51.0; Playwright 1.63.0's pom brings Gson
    2.14.0 at compile scope. npm — `@percy/cli` 1.32.11, `@lhci/cli` 0.15.1, `lighthouse` 13.5.0. Sources —
    percy-playwright-java v1.2.1 (`snapshot(String, Map<String,Object>)`, a no-op returning `null` when the agent's
    healthcheck fails); the eyes-playwright-java5 5.86.9 sources jar (`com.applitools.eyes.playwright.visualgrid.VisualGridRunner`,
    `Target.region(Locator)`, `layout/ignore/strict/content(Locator)`, `floating(Locator, up, down, left, right)`,
    `Eyes.open(Page, String, String, RectangleSize)`, `closeAsync()`) and eyes-common-java5 5.71.4
    (`com.applitools.eyes.visualgrid.BrowserType`, `DeviceName.Pixel_2`); axe-core-maven-html v4.13.0
    (`AxeBuilder.include/exclude(String)`, `withTags/disableRules(List)`, `Node.getTarget()` returns `Object`);
    playwright-java v1.63.0 (`Page.requests()`, `pageErrors()`, `consoleMessages(options)`, `Response.allHeaders()`,
    `securityDetails()` → `SecurityDetails` public fields, `RouteFromHAROptions` setters, and `Router.handle`
    returning `PendingHandler` when a handler returns without handling the route); playwright v1.63.0
    `screenshotter.ts` awaits `document.fonts.ready` before every screenshot; BrowserUp v2.1.2
    (`HarRequest.getMethod()` returns the `HttpMethod` enum, `Har.writeTo(File)`, `waitForQuiescence` returns
    `boolean`).
  - Differed from the plan: the visual job and the baseline-update command run the pinned image with `docker run`
    from a runner step, not a container job (D53); a loading state is shown by holding the route, not by a delay
    (D54); the Java Lighthouse test attaches to `BaseTest`'s own Chromium on a free debugging port and audits public
    pages only, with Gson for every JSON read in these skills (D55); each Applitools class owns its runner and gates
    in `@AfterClass` (D56); `proxy.md` keeps the archived BrowserUp with a warning (D57). Beyond the plan:
    security headers and TLS moved from `cdp.md` to `playwright-routes.md` §5 (as T3 did), so CDP lost its
    `responseFor` audit, its `CdpBaseTest` and its detach hook (the session ends with the context `BaseTest`
    closes); the old proxy sample compared the `HttpMethod` enum to `"POST"` and could never pass — fixed; its
    `ClientUtil` placeholder method returning `null` is gone; the PDF example is dropped with the reason (§9);
    the Percy build link (`PERCY_BUILD_URL`, unverified) is dropped — the status check carries it.
  - Names assigned: helpers `support.VisualCheck` (`compare(target, masked, baselineName)`), `support.EyesConfig.forGrid()`,
    `support.A11yScan` (`scanPage`, `scanWithin(testId)`, `WCAG_22_AA`, `FALSE_POSITIVES`, `KNOWN_VIOLATIONS`,
    `newViolations`, `blockingViolations`), `support.Lighthouse` (`freePort`, `audit`, `GATED_CATEGORIES`),
    `support.MockApi` (+ `MockApi.HeldRequests.release()`), `support.Traffic` (`requestedUrls`, `pageErrors`,
    `jsonBody`), `support.CdpControls` (+ `CapturedResponse`), `support.NetworkPresets`, `support.proxy.ProxyControls`,
    `support.proxy.ProxyTest`; page objects `PricingPage`, `SignupPage`, `OrdersPage` (`navigate()` vs `open()`),
    `CartPage`, `AppShellPage`, `ProfilePage`, `DashboardPage`; TestNG groups `visual`, `a11y`, `lighthouse`; Gradle
    task `visualTest`; env `UPDATE_BASELINES=1`, `HAR_UPDATE=1`, `APPLITOOLS_BATCH_ID`; baselines
    `src/test/resources/baselines/<os>-<browser>/<Subject>.png`; kept files
    `build/playwright-artifacts/<Class>.<method>.{actual,diff}.png`, `.lighthouse.{json,log}`, `.har` (proxy).
  - Built, unverified (Gate: none): nothing compiled or ran. Open points: `BatchInfo.setId` and
    `getAllTestResults(boolean)` live in an Applitools jar whose sources were not published, so they rest on the
    old skill text and the SDK's long-standing API; Lighthouse attaching to a Playwright-launched headless Chromium
    through `--remote-debugging-port` (the `playwright-lighthouse` pattern) was not run from Java; the
    `docker run` visual job and JDK 21 install were not run; BrowserUp 2.1.2 was not run on Java 21 or beside
    Selenium 4.51; the comparator remains a recommendation (D9).
  - Proof: no screenshot assertion `visual-regression/SKILL.md:12`; comparator pin and gate exclusion
    `references/playwright-snapshots.md:36,42`; masks and style `:158-159`; Allure 3 attach `:191`; update command
    in the pinned image `:350-351`; nightly `docker run` job `:394-396`; PDF dropped `:419`; Percy pins and
    no-assertion description `references/percy.md:32,37,107`; Eyes pin, hooks and description
    `references/applitools.md:31,127,138,143`; axe pin and WCAG 2.2 tags `accessibility-testing/references/axe-playwright.md:17,72`,
    incompletes attached `:113`, native assertion `:198`; Lighthouse public-pages limitation, pins, free port,
    launch hook, one assertion `references/lighthouse-ci.md:13,27,112,174,187`; no handler sleep
    `network-mocking/SKILL.md:42`; routes — hold `references/playwright-routes.md:50,129,389`, `mockApi` declared
    `:216`, `page.requests()` `:183,307`, headers/TLS `:323,331`, `startHar` link `:361`, glob 1.52 `:409`; CDP
    `browserName` gate `references/cdp.md:87-89`, last match `:244`; proxy pin and enum `references/proxy.md:22,236`.

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
- **As built (2026-10-11):**
  - Landed: all eleven files rewritten — three routers (`visual-regression` 7.0k, `accessibility-testing` 4.9k,
    `network-mocking` 4.6k chars; descriptions 492 / 478 / 496) and eight references (`playwright-snapshots` 24.6k,
    `percy` 11.2k, `applitools` 14.7k, `axe-playwright` 14.9k, `lighthouse-ci` 15.4k, `playwright-routes` 23.5k,
    `cdp` 14.6k, `proxy` 19.1k). Every Playwright sample derives from `Example.UiTests.Support.BaseTest` and amends
    `base.ContextOptions()` (the Lighthouse fixture is the one exception, D61; the proxy samples drive Selenium, so
    they own their driver in `[SetUp]`/`[TearDown]`); page objects own `GotoAsync` and `Describe()`d locators; no
    `try`/`finally`, `Task.Delay`, `Thread.Sleep`, `WaitForTimeoutAsync`, comment, floating version or `Version=`
    on a `PackageReference` in any code block; PascalCase test ids; `Should_X_When_Y` names; every title says .NET 10.
    Scripted scan of the eleven files: no fabricated screenshot API, no `Playwright.Shard`, no `since … 1.43`.
  - **The comparer, checked on NuGet today:** `Codeuctivity.ImageSharpCompare` **4.1.390** (published 2026-05-13;
    net8.0/net9.0/net10.0; Apache-2.0; depends on `SixLabors.ImageSharp` 3.1.12, Six Labors Split License).
    API read at its release commit `7f3d2a0`: `ImagesHaveEqualSize(path, path)`, `CalcDiff(actual, expected,
    ResizeOption, pixelColorShiftTolerance)` → `ICompareResult` (`MeanError`, `AbsoluteError`, `PixelErrorCount`,
    `PixelErrorPercentage` 0–100), `CalcDiffMaskImage(...)` → ImageSharp `Image`; `DontResize` throws
    `ImageSharpCompareException("Size of images differ.")`. The other candidate, `Verify.Playwright`, is 3.1.1 (D58).
  - Also checked today: Allure.NUnit 2.15.0 source — `AddScreenDiff(expectedPngPath, actualPngPath, diffPngPath)`
    (expected first; the doc comments swap the words, the parameters and the JSON do not) plus a `byte[]` overload;
    `AddLink` / `AddAttachment` do nothing without a running test (`HasTest` / `HasTestOrFixture`), so
    `[OneTimeTearDown]` uses `AddGlobalAttachment`. `@percy/cli` 1.32.11 `exec.js` exports `PERCY_BUILD_URL`;
    `PercyIO.Playwright` 1.0.4 (`Percy.cs`): static, synchronous `Percy.Snapshot(IPage, string, object|options)`
    returning `JObject?`, swallowing every error, no-op when the healthcheck fails. `Eyes.Playwright` 1.37.49
    (2026-10-01; no published sources — its public API read from the assembly metadata, with `Eyes.Images` 3.68.9):
    `Applitools.Playwright.Eyes.Open(IPage, app, test, RectangleSize)` → `IPage`, `Check(...)` void,
    `CloseAsync()` / `AbortAsync()` return **void**, `Applitools.VisualGrid.VisualGridRunner`,
    `GetAllTestResults(bool)` → `TestResultsSummary`, `Target.Region(ILocator)`, `.Layout/.Ignore/.Floating/…`,
    `BrowserType.CHROME`, `DeviceName.Pixel_5`, `ScreenOrientation.Portrait`, `TestResultsStatus.Passed`.
    `Deque.AxeCore.Playwright` 4.13.0 (latest stable; sources at the release commit): **no `AxeBuilder`** — the API is
    `page.RunAxe(AxeRunOptions?)`, `page.RunAxe(AxeRunContext, AxeRunOptions?)`, `locator.RunAxe(AxeRunOptions?)`,
    `RunOnlyOptions.Tags(...)`, `AxeResultNode.Target` an `AxeSelector`. npm: `lighthouse` 13.5.0 (Node ≥ 22.19),
    `@lhci/cli` 0.15.1; Lighthouse's `clearStorageTypes` (D61). playwright-dotnet v1.63.0: `IRequest.PostDataJSON()`
    is a **method**; `RouteFulfillOptions.Json` is serialized with default `JsonSerializer` options (PascalCase
    records); `ICDPSessionEvent.OnEvent` is `EventHandler<JsonElement?>`; `IPage.RequestsAsync()` (100),
    `ConsoleMessagesAsync()`, `PageErrorsAsync()` (200); `IResponse.AllHeadersAsync()`, `SecurityDetailsAsync()` →
    `ResponseSecurityDetailsResult`; `LaunchPersistentContextAsync("")` makes a temporary profile;
    `IBrowserContext.SetStorageStateAsync(path)`; `PlaywrightSettingsProvider.LaunchOptions`; routes dispatched with
    `_ = OnRouteAsync(route)` and `RouteHandler` awaiting the route's handling. `Titanium.Web.Proxy` 7.0.22
    (2026-10-10, net10.0 only) at its release commit: `new ProxyServer()` defaults `userTrustRootCertificate: true`,
    `Start(bool changeSystemProxySettings = true)`, `TrustRootCertificate(bool machineTrusted)` (the old sample's
    `userTrusted:` did not compile), port 0 written back to `endPoint.Port`. `Selenium.WebDriver` / `.Support` 4.51.0.
  - Differed from the plan: the comparer (D58); the `ProjectDirectory` metadata and `ProjectPaths.Root` (D59); the
    nightly visual job as `docker run` (D60); the Lighthouse fixture on `PlaywrightTest` (D61); §6.1's package check
    narrowed (D62). Beyond the plan: the axe reference rebuilt on `RunAxe` (the old `AxeBuilder` does not exist in
    .NET — the audit missed it); the Eyes reference made synchronous (the old `OpenAsync`/`CheckAsync`/awaited
    `CloseAsync(false)` do not exist); security headers and TLS moved from `cdp.md` to `playwright-routes.md` §5, so
    CDP lost `ResponseFor`, `SecurityHeaders` and `CdpBaseTest`; the `Task.Delay` latency handler became a held
    route (`MockApi.HoldOrdersAsync()` / `HeldRequests.Release()`, as J3's D54); `PostDataJSON` used as a method,
    payloads compared as records (D-18); `Json =` replaced by `JsonSerializerOptions.Web` bodies; the proxy keeps the
    root CA out of the OS store and pins it in `HttpClient`, its predicate-waiter machinery became reads after a
    client-visible signal (as T3's D52), its fault test gained an assertion, and its HAR pseudo-code became a scrubbed
    JSON traffic log; Percy's build link is `AllureApi.AddLink` during the test.
  - Names assigned: `Support/VisualCheck` (`CompareAsync(target, masked, subject)`, `AllowedDifferentPixelsPercent`
    0.05, tolerance 12) + `VisualDiff`; `Support/ProjectPaths.Root`; `Support/PercySnapshots.Capture(name, options)`;
    `Support/EyesConfig` (`ForGrid()`, `Unresolved(summary)`); `Support/A11yScan` (`ScanPageAsync`, `ScanAsync(ILocator)`,
    `FalsePositives`, `KnownViolations`, `NewViolations`, `BlockingViolations`); `Support/Lighthouse` (`FreePort`,
    `AuditAsync`, `GatedCategories`); `Support/MockApi` (+ `HeldRequests`), `Support/Traffic`, records `Order`,
    `CheckoutRequest`; `Support/CdpControls` (`NextResponseAsync`), `CapturedResponse`, `NetworkPreset`;
    `Support/Proxy/ProxyControls`, `ProxiedClients`, `SeenRequest`; page objects `PricingPage`, `SignupPage`,
    `AccountPage`, `OrdersPage`, `CartPage`, `AppShellPage`, `ProfilePage`, `DashboardPage`, `Pages/Selenium/CartScreen`;
    NUnit categories `visual`, `lighthouse`, `a11y`, `proxy`; env `UPDATE_BASELINES=1`, `HAR_UPDATE=1`,
    `APPLITOOLS_BATCH_ID`; baselines `UiTests/Baselines/<os>-<browser>/<Subject>.png`; HAR
    `UiTests/Fixtures/Har/payments.har`; kept files `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{actual,diff}.png`,
    `.lighthouse.{json,log}`, `.traffic.json`.
  - Built, unverified (Gate: none): nothing compiled or ran. Open points: `VisualCheck` and the ImageSharpCompare
    calls; `Percy.Snapshot` with an anonymous options object; the Eyes API read from metadata, not run (and its
    `APPLITOOLS_API_KEY` environment read rests on the SDK's convention); `RunAxe` with an `AxeRunContext` exclusion;
    `SetStorageStateAsync` on a persistent context reaching Lighthouse's tab, and `Process.Kill` from the deadline
    registration; a held route under parallel fixtures; the `docker run` visual job and the in-container
    `ProjectDirectory`; Titanium 7.0.22's `ProxyServer(userTrustRootCertificate: false)` with Selenium 4.51 and
    `--ignore-certificate-errors`. Observation for J3's lane (not edited, R12): Lighthouse does not clear cookies or
    local storage, so the Java reference's "Lighthouse resets the origin's storage" is only partly right; its
    public-pages limit still holds because the audited tab is in a different context.
  - Proof: no screenshot assertion `visual-regression/SKILL.md:12`; comparer pin `:28` and
    `references/playwright-snapshots.md:25,41`; `ProjectDirectory` `:51`; `AddScreenDiff(baseline, actual, diff)`
    `:171`; evidence paths `:277`; `[Category("visual")]` `:257`; pinned-image update `:333`; nightly `docker run`
    `:382`. Percy `AddLink` and no-assertion description `references/percy.md:109,137`. Eyes sync `Open`,
    `CloseAsync()` in `[TearDown]`, global attachment, gate `references/applitools.md:146,161,92,166`. axe — no
    builder `accessibility-testing/references/axe-playwright.md:32`, `RunAxe` `:102,109`, WCAG 2.2 AA tags `:122`.
    Lighthouse free port, persistent context, storage state, no PWA `references/lighthouse-ci.md:103,205,211,24`,
    `clearStorageTypes` `:244`. Routes — held route `network-mocking/references/playwright-routes.md:132`,
    `PostDataJSON()` `:156`, headers/TLS `:324,334`, glob 1.52 `:428`, cross-references `:487-488`; CDP
    `JsonElement?` `references/cdp.md:17,117`; proxy trust `references/proxy.md:90,104`.

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
- **As built (2026-10-11):** the twelve skills landed on 1.64 with every Playwright version deferred to the
  writer's Versions table ("this skill pins nothing"), except `bdd-project-scaffold`, whose web `package.json`
  pins `@playwright/test` 1.64.0, `playwright-bdd` 9.2.1 and `allure-playwright` / `allure-js-commons` 3.13.0
  exactly. Every touched sample is `Should_X_When_Y`, comment-free, and reaches the page through page objects and
  fixtures; the only code-block comments left in the touched files are the mobile templates of
  `bdd-project-scaffold` (M1's, prompt updated). What differed from the plan:
  - `responsive-testing`: rows carry `shown`/`hidden`/`columns`; one `describe` + `test.use({ viewport })` per row;
    a `Layout` fixture measures and the test asserts (`expect.poll`). The fixture code moved to a new
    `responsive-testing/references/fixtures.md` to keep SKILL.md ≤ 16,000 chars (D63). Cross-reference is now
    `frontend/react/skills/responsive-design` (`Nav.Desktop` / `Nav.Hamburger`).
  - `realtime-stream-testing`: claims WebSocket mocking and browser SSE and links back to `network-mocking` for
    plain HTTP; the SSE mock is a fixed event set plus `204` (D64). `WsHarness`, the browser fixtures and the
    gotchas list moved to `references/details.md` (SKILL.md 22,783 → ~15,950 chars); socket.io moved there as
    Protocol-client 2; cleanup is `onTestFinished`.
  - `browser-cloud-setup`: route 1 `use.connectOptions`, route 2 a worker-scoped `browser` override that marks the
    session once per worker (D65); `playwrightVersion` read with `createRequire` from the project root; `globalSetup`
    returns `tunnel.stop`; the session URL is an awaited `testInfo.attach` (the old `allure-playwright` import is
    gone). The mobile Stack line now defers WebdriverIO/Appium versions to `ui-test-author/appium`.
  - `test-login-tokens`: a `token.setup.ts` in the writer's `setup` project — `context.setStorageState` [1.59] at
    the `baseURL` origin, the greeting checked, then `storageState({ path: authFile })` — plus a storage-state
    table (cookies/localStorage yes; IndexedDB with `indexedDB: true`; never `sessionStorage`; never an in-memory
    auth0-spa-js cache).
  - `language-testing`: the old fixture overrode Playwright's `locale` with a catalog key; it is now a separate
    `lng` option beside `locale`/`timezoneId`, and the fixture freezes time with `page.clock.setFixedTime` before the
    page loads (a `RelativeTimeFormat` sample). RTL and pseudo specs are selected by tags with
    `grep`/`grepInvert`, not `test.skip`. Fixed `IntlMessageFormat` being called as a function. ICU plurals and the
    locale matrix moved to `references/details.md` (SKILL.md 18,920 → 14,105 chars).
  - `data-driven-testing`: Vitest rows are typed objects; Playwright generates one test per row through a fixture;
    streaming collects at module scope instead of asserting inside one test; titles must be unique. SKILL.md is
    19,423 chars (was 19,174) — a size violation that predates this plan and that T4 did not rewrite.
  - `production-uptime-checks`: browser-check specs set the R7 evidence with `test.use` and run on the writer's
    fixtures (D66); `runtimeId: '2024.02'` is gone from the sample, replaced by prose pinning the newest id from
    `npx checkly runtimes`; the missing `RetryStrategyBuilder` import is fixed; secrets and the CI workflow moved to
    `references/details.md` (SKILL.md 21,416 → 15,993 chars). Wired into `qa-api-typescript.md` Step 3 with the exit
    gate `npx checkly test --record` → green.
  - `inhouse-framework-conventions`: `PageBase.locator(key)` actions and `errorMessage: Locator`; PascalCase test
    ids in the screen JSON; the anti-example block became a table. `mailpit.md`: `deleteAll()` and the `beforeEach`
    wipe are gone; isolation is `uniqueRecipient(flow)` or the writer's `seededUser`.
  - `api-test-author/playwright`: a `createdUsers` fixture deletes in teardown and asserts every status; TC-IDs
    moved from titles into `{ tag }`; a context-options table for `failOnStatusCode` [1.51] (stays `false`),
    `maxRedirects` [1.52], `addCookies`/`cookies`/`clearCookies` [1.64], `timing()` [1.62] and
    `securityDetails()` [1.61].
  - `playwright-bdd.md`: Node 24/22; `seededOrder` asserts `201` with the body before parsing, deletes with `204`;
    steps read credentials from a `testUser` fixture; page objects never assert.
  - **Unverified** (no web access in this session; nothing compiled or run): `APIResponse.timing()`'s field names
    and whether `timing()` / `securityDetails()` return promises (the samples `await` them); the
    `apiRequestContext` cookie method signatures (read from the research's names only); `npx checkly runtimes`;
    BrowserStack's `getSessionDetails` executor and its `hashed_id`; Checkly honouring a spec's `test.use` trace
    and video modes; `DataTable` exported by `playwright-bdd`; Vitest `onTestFinished` and `it.for`. None of these
    files is an asset G1 compiles.
  - Proof: `qa/typescript/agents/qa-api-typescript.md:139` (Step 3 row);
    `qa/typescript/skills/realtime-stream-testing/SKILL.md` § Browser surface 3;
    `qa/typescript/skills/browser-cloud-setup/references/details.md` § Web — route 1 / route 2;
    `qa/typescript/skills/bdd-project-scaffold/SKILL.md` § `package.json` (deps).

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
- **As built (2026-10-11):** the twelve Java skills teach Playwright 1.63 on J1's `BaseTest` with every Playwright
  version deferred to the writer's Versions table ("this skill pins nothing"), except `bdd-project-scaffold`, which
  pins `playwright:1.63.0`, `allure-cucumber7-jvm:3.0.0` (on Central per J2's live check, plan line 1515), Allure
  Gradle plugin 4.3.0 with `allureJavaVersion` 3.0.0 and `allure-commandline` 2.46.1 like J1's build. Every touched
  sample is `Should_X_When_Y`, comment-free, and reaches the page through page objects; the one code comment left
  in a touched file is the commented-out `io.appium:java-client:10.1.1` line in `bdd-project-scaffold`'s
  `build.gradle.kts` (M2's; its prompt now names it). What differed from the plan:
  - **J1 edits (the two allowed paths):** `BaseTest` gained `protected Browser newBrowser(Playwright)` — the
    default is today's local launch with the `HEADED` stamp — and `lifecycle.md` §3 became "The hooks", a
    three-row table (D67). §2's `launchBrowser` row and the intro line follow it.
  - `responsive-testing`: rows are a TestNG `@Factory` (one instance per width, its `contextOptions()` setting the
    viewport) instead of per-test `setViewportSize` (D68); page objects and a measuring `Layout` moved to a new
    `references/page-objects-and-layout.md` (SKILL.md 15,984 chars); test ids `Nav.Desktop` / `Nav.Hamburger` /
    `ProductGrid.Card`; the FE cross-reference is `frontend/react/skills/responsive-design` (Blazor's still says
    kebab-case `nav-desktop`, not this plan's file).
  - `realtime-stream-testing`: `WebSocketFrame.text()` in a `MockStreams` helper; browser SSE is a `setTimes(1)`
    event-stream route over a `204` route (the T4/D64 shape); probes open/close in `@BeforeMethod`/`@AfterMethod`;
    STOMP, the gotchas and the browser page objects moved to `references/details.md` (SKILL.md 22,191 → 15,831).
  - `browser-cloud-setup`: `GridWebTestBase` is gone; a grid class subclasses a test class and overrides
    `newBrowser` (D67), one session per class with its verdict marked once in `@AfterClass` from `ITestContext`, the
    concurrency cap set on a `testng-grid.xml` suite by an `IAlterSuiteListener`, run by a `gridTest` task (D69);
    `client.playwrightVersion` read from the jar's `META-INF/maven/.../pom.properties`; the session URL attached
    with `Allure.attachment(name, content)`; `SAUCE_REGION` and `BUILD_NAME` required instead of defaulted.
  - `language-testing`: `I18nBaseTest` is gone; a `LocaleUnderTest` record feeds each class's `contextOptions()`,
    the matrix is a `@Factory` (D68); `page.clock().setFixedTime` before load; the vacuous `hasCSS(".+")` became a
    measured RTL position test; the hardcoded-currency data provider was dropped (D35); plural test without a loop
    (`PluralRules.getKeywords()`); pseudo-loc, coverage, plurals and the matrix moved to `references/details.md`
    (SKILL.md 19,051 → 15,741).
  - `data-driven-testing`: the parallel-rows section and the rules exclude Playwright/Appium classes; its samples
    were renamed and de-commented. SKILL.md is 21,967 chars (was 21,232) — a size violation that predates this
    plan; J4 did not rewrite the file.
  - `test-login-tokens`: a `TokenAuthSetup` `@BeforeSuite` (lifecycle.md §6's shape) writes
    `build/.auth/test-user.json` from a minted token at the `BASE_URL` origin and checks the greeting first; classes
    pick the role in `contextOptions()`; the device-code helper logs through `System.Logger`.
  - `production-uptime-checks`: the probe catches `AssertionError | PlaywrightException`, records the result in
    `finally`, treats over-budget as failure, and keeps trace/video/screenshot through a new `ProbeEvidence` under
    `SYNTHETIC_EVIDENCE_DIR` (D70); alerting HCL, secrets and a worked example moved to a new
    `references/details.md` (SKILL.md 21,140 → 15,925). Wired into `qa-api-java.md` Step 3 with the exit gate
    `terraform plan` → no unexpected diff.
  - `inhouse-framework-conventions`: `PageBase.locator(key)` actions, `errorMessage()` returns a `Locator`,
    PascalCase test ids in the screen JSON, the test class extends `BaseTest`, evidence from `BaseTest` instead of a
    second `ITestListener`, the anti-example block became a table.
  - Email: Mailpit's `waitFor` and IMAP's `awaitEmail` poll with Awaitility (`org.awaitility:awaitility:4.2.2`,
    the lane's existing pin from `failure-injection-testing`; IMAP adds `pollInSameThread()`); Mailpit lost its
    global `deleteAll()` wipe (parallel classes share the container); IMAP cleanup moved to an
    `@AfterMethod(alwaysRun = true)` in `ImapTestBase`; the attachment test's in-lambda `try/catch` became
    `MimeBodies.firstAttachment`; AssertJ pins 3.26.3 → 3.27.7 (§2.2).
  - `api-test-author/playwright`: exact status with AssertJ and the body as description, plain `int` status codes
    (no HttpComponents), records compared with one `isEqualTo` instead of `SoftAssert`; `BaseApiTest` stays its own
    base class (D71); the 1.64 request-context cookie line.
  - `gherkin-step-code`: page objects take the `Page` (J1's `LoginPage`, `HomePage`, `Credentials`), never
    `TestContext`; `expectLoaded()` is gone — `Then` steps assert on exposed locators.
  - `bdd-project-scaffold`: Playwright 1.63.0; the `@Suite`'s `@SelectClasspathResource` is the one discovery
    mechanism (no `cucumber.features`); reports under `build/`; `HEADED=1` instead of `-Dplaywright.headless`; an
    `installPlaywrightBrowsers` task; the `Hooks` class per `evidence-capture` § Cucumber scenarios, moved to a new
    `references/hooks.md` to keep SKILL.md at 15,293 chars; `<Feature>` is the feature **file** name (D72).
  - `python-web-testing`: `expect(...).to_be_visible()` replaces `networkidle` / `wait_for_timeout` /
    `wait_for_selector`; locator APIs; outputs under `evidence/`; `playwright==1.63.0`, `pytest-playwright==0.10.0`,
    Python ≥ 3.10; a pytest section on 0.10.0's evidence flags; `with_server.py` writes server output to
    `evidence/servers/server-<n>.log` instead of an unread `PIPE`. `.DS_Store` deleted (it was untracked).
  - Allure 3.0 sweep: `deepeval.md`, `dependency-scan`, `passive-scan` call `Allure.attachment(...)` (+
    `AttachmentOptions` for streams); `db-testing/testcontainers` prose names the 3.0 call; `failure-injection-testing`
    and `feature-flag-testing` pin `allure-testng:3.0.0`.
  - **Unverified** (no web access in this session — WebFetch and WebSearch were denied; nothing compiled or run):
    `pom.properties` inside the Playwright jar; BrowserStack's `getSessionDetails` / `browser_url`; TestNG running
    `@BeforeClass` per `@Factory` instance (read from TestNG's `invokeBeforeClassMethods`, from memory);
    `IAlterSuiteListener` overriding a suite's `thread-count`; `StorageStateOptions.setIndexedDB` as the Java
    spelling; Cucumber running `@After(order = 0)` last; `Allure.attachment(String, String)` and allure-testng
    showing a class-level attachment in each test's tear-down; `EventSource` stopping on a routed `204` from Java.
    None of these files is an asset G1 compiles, except `BaseTest.java`.
  - Proof: seam `ui-test-author/playwright/assets/BaseTest.java:51,60`, `references/lifecycle.md:54,79`; Step 3
    `qa/java/agents/qa-api-java.md:139` (production probes); `browser-cloud-setup/references/details.md:112,118,176,223,380`;
    `realtime-stream-testing/references/details.md:266,282,298`; `responsive-testing/SKILL.md:56`;
    `language-testing/SKILL.md:100,120`; `data-driven-testing/SKILL.md:287`;
    `test-login-tokens/references/details.md:212`; `production-uptime-checks/SKILL.md:142,154`,
    `references/details.md:54`; `inhouse-framework-conventions/SKILL.md:108`; `email-testing/references/mailpit.md:129`,
    `gmail-imap.md:205`; `api-test-author/playwright/SKILL.md:167`; `gherkin-step-code/SKILL.md:54`;
    `bdd-project-scaffold/SKILL.md:78,82,147`, `references/hooks.md:69`. `grep -rn "addAttachment\|allure-testng:2\|allure-cucumber7-jvm:2" qa/java qa/reporting/java`
    → prose only (`accessibility-testing/references/axe-playwright.md:247`, `ui-test-author/playwright/references/lifecycle.md:124`,
    `ui-test-author/review/SKILL.md:79`, `evidence-capture/SKILL.md:129`, `evidence-capture/references/playwright.md:301`,
    `test-reports/SKILL.md:90,91,286`) plus one code pin in M2's `mobile-native-features/SKILL.md:77`.

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
- **As built (2026-10-11):** the twelve .NET skills teach Microsoft.Playwright 1.63 on N1's `BaseTest` (or, where a
  fixture cannot be one, on a documented owner — D75, D78, D76) with every Playwright version deferred to the
  writer's Versions table ("this skill pins nothing"), except `bdd-project-scaffold`, which names
  `Microsoft.Playwright.NUnit` 1.63.0 under CPM. Every touched sample is `Should_X_When_Y`, comment-free, reaches the
  page through page objects or helpers built in `[SetUp]`, and carries no `try`/`catch`/`finally` in a test; the
  remaining catches are named-exception helpers (`AwaitFrame`, the probe's `PlaywrightException`), and the one
  `try`/`finally` releases a semaphore in `CachedTokenProvider`. Every title says .NET 10; the two ".NET 8" hits left
  are version notes (realtime's .NET 8 SSE line parser). What differed from the plan:
  - `responsive-testing`: rows are `[TestFixture(width, shown, hidden)]` parameters with the viewport amended in
    `ContextOptions()` (D73); `Breakpoints` (const, `Viewport(width)`), `AppShellPage`/`NavVariant`, `ProductsPage`
    and a measuring `Layout` moved to a new `references/page-objects-and-layout.md` (SKILL.md 15,957 chars);
    `Nav.Desktop` / `Nav.Hamburger` / `ProductGrid.Card`. The Blazor FE peer still writes kebab-case ids (not this
    plan's file).
  - `realtime-stream-testing`: OBSERVE is `SocketWatch` — `Page.WebSocket` subscribed before the action, each
    matching socket's `FrameReceived` completing a `TaskCompletionSource`, awaited with `WaitAsync(timeout)`; a
    `ClosedAsync` twin and an `IsClosed` property assertion. MOCK is `MockStreams` (`frame.Text == "subscribe"`), and
    browser SSE a `Times = 1` event-set route over a `204` route (T4's D64). `AwaitFrame`, the probes, SignalR,
    the gotchas, the page objects and the layout moved to `references/details.md` (SKILL.md 25,170 bytes → 15,963
    chars); the probes' empty catches became channel completion with the pump's exception; `SseItem<T>.EventId`
    replaced the nonexistent `ReconnectionId`.
  - `browser-cloud-setup`: D74 — `GridConnection` / `GridSession` / `CheckoutTestsOnBrowserStack`, the worker
    count as the session cap (the old `LevelOfParallelism(5)` and a guard that guarded nothing are gone), the
    tunnel `[SetUpFixture]` scoped to `Example.UiTests.Grid`, `BUILD_NAME` and `SAUCE_REGION` required,
    `client.playwrightVersion` from the loaded assembly; the Appium half defers its pin to `ui-test-author/appium`.
  - `test-login-tokens`: D77 — `AuthSetup`'s token body at `BASE_URL`'s origin and `AuthSetup.UserState`; a
    storage-state table (cookies, localStorage, IndexedDB with `IndexedDB = true` [1.51], never `sessionStorage`,
    never the Auth0 SPA SDK's in-memory cache); `AUTH0_DOMAIN`/`AUTH0_AUDIENCE` required (no product defaults);
    the device-code poll reads the JSON error over `HttpClient`.
  - `language-testing`: `[TestFixture("de-DE", "Europe/Berlin")]` / `[TestFixtureSource(SupportedLocales.All)]` on
    `BaseTest` with `Locale` and `TimezoneId` amended (D73); `Page.Clock.SetFixedTimeAsync` before load; the RTL
    test measures `AppShellPage.NavigationSideAsync()` instead of a vacuous `ToHaveCSSAsync(".+")`; the
    literal-asserting `NumberFormatInfo` test was dropped (it contradicted idea #2). Page objects, pseudo-loc,
    coverage, ICU and the matrix moved to `references/details.md` (SKILL.md 20,046 bytes → 14,906 chars).
  - `data-driven-testing`: the parallel-rows section and the rules exclude Playwright/Appium fixtures and send
    context-per-row matrices to fixture parameters; samples renamed and de-commented. SKILL.md is 19,630 chars — a
    size violation that predates this plan; N4 did not rewrite the file.
  - `production-uptime-checks`: D76 — `CheckoutJourneyProbe` reusing N1's `LoginPage` with `BaseURL` from
    `SYNTHETIC_BASE_URL`, `ProbeEvidence`, `ProbeSettings`, a Container Apps job `Program.cs` and a
    `v1.63.0-noble` Dockerfile; Bicep (now with a `healthUrl` param), alerts, secrets and a worked example moved to a
    new `references/details.md` (SKILL.md 21,567 bytes → 15,345 chars). Wired into `qa-api-dotnet.md` Step 3 with the
    exit gate `az deployment group what-if` → no unexpected change; Step 4 now also loads
    `api-test-author/playwright` § Review when Step 2 used it (C-15).
  - `inhouse-framework-conventions`: `PageBase.Locator(key)` fields built in the constructor, `ILocator
    ErrorMessage`, `ToHaveURLAsync(new Regex("/dashboard$"))`, tests on `BaseTest`, PascalCase ids in the screen
    JSON, evidence from `BaseTest`, the anti-example block a table; the builder rule now matches its code.
  - `api-test-author/playwright`: D75; cleanup is `[TearDown]` only with `Assert.MultipleAsync` over the recorded
    ids (C-06); a § Review table (C-15); a request-context options table (`FailOnStatusCode` off [1.51],
    `MaxRedirects` [1.52], the 1.64 cookie line); fixture + create/round-trip test in a new `references/templates.md`.
  - `gherkin-step-code`: `Given` only navigates (C-13); steps take N1's `LoginPage` / `HomePage` /
    `LoginPage.Credentials` through `ScenarioState`; credentials through `BaseTest.RequiredEnv`; namespace
    `Example.BddTests`.
  - `bdd-project-scaffold`: D78 — CPM additions (Reqnroll 3.3.4 ×2, `Allure.Reqnroll` 2.15.0), a versionless
    `Bdd.Tests.csproj` on the UI runsettings, `ScenarioState.Open(page)`, and `BrowserHooks` per
    `evidence-capture` § Reqnroll scenarios in a new `references/hooks.md`.
  - `bdd-reviewer`: C-07 rows — one expected condition, no `try`/`catch` in steps or hooks, no `NetworkIdle` /
    `Force` / deprecated waits / page-level selector APIs / URL globs, runsettings browser + `BASE_URL`, failure
    evidence; severities follow.
  - `standards-audit`: E11 reworded to R8 (D79, with the non-finding note under section E); L4 now trace +
    screenshot + video in `playwright-artifacts/`; L9 matches D7 (`[Retry(2)]` on a documented hotspot,
    `[Retry(1)]` a no-op). New rows: **A9** nonexistent APIs (the fabricated screenshot API, `GetPathAsync`, 1.64-only
    calls, `AxeBuilder`, `AddTestAttachment`, async Eyes, `PostDataJSON` as a property, `WaitForEventAsync`,
    `IsClosed()`), **A10** package/image version mismatch, **E16** `ContextOptions()` + `ParallelScope.Self` +
    runsettings launch options, **E17** root-namespace `AuthSetup`, **F10** the TODO marker, **F11** PascalCase ids,
    **I11** `ToHaveURLAsync` glob, **I12** visual = screenshot + comparer (`ProjectPaths.Root`, pinned image,
    `Eyes.Playwright`), **I13** `RunAxe` at WCAG 2.2 AA (no `pwa`), **K9** missing `BaseURL`, **L14** Allure calls
    where a result exists, **M15** `Playwright.Shard` / `NUnit.Where` instead of class filters, **M16**
    `visual`/`lighthouse`/`grid` out of the PR gate. SKILL.md's scope table lists every tagged row per scope.
  - Names assigned: `Breakpoints`, `NavVariant`, `AppShellPage`, `ProductsPage`, `Layout`; `SocketWatch`,
    `MockStreams`, `DashboardPage`, `StatusPage`, `NotificationsPage`, `WebSocketProbe.CloseAsync`, `SseEvent`;
    `GridCredentials`, `GridConnection`, `GridSession`, `DriverSessionStatus`, `GridTunnel`, `GridTunnelSetup`,
    category `grid`; `SupportedLocales`, `LandingPage`, `CartPage`, `OrderPage`, `CheckoutPage`, `ScreenSide`;
    `CheckoutJourneyProbe`, `ProbeEvidence`, `ProbeSettings`, env `SYNTHETIC_BASE_URL` / `SYNTHETIC_USER` /
    `SYNTHETIC_PASSWORD` / `SYNTHETIC_EVIDENCE_DIR` / `REGION_NAME`; `Example.BddTests`, `ScenarioState.Open`,
    `BrowserHooks`; `AUTH0_DEVICE_CLIENT_ID`.
  - **Unverified** (no web access — WebFetch was denied; nothing compiled or run): `BrowserTest.ConnectOptionsAsync()`'s
    exact signature; `IPage.WebSocket` firing before the socket's first frame and `IWebSocket.Close` being an
    `EventHandler<IWebSocket>`; `IWebSocketRoute.Send` being synchronous; `EventSource` stopping on a routed `204`
    (T4's D64 risk); `SseItem<T>.EventId` (.NET 10); every .NET `Expect` failure being a `PlaywrightException`;
    `TelemetryClient.FlushAsync(CancellationToken)`; Reqnroll's after-hook order, `Allure.Reqnroll` /
    `Allure.ReqnrollPlugin` and Reqnroll 3.3.4 being current; `Assert.MultipleAsync`; ICU4N's `PluralRules.Select`;
    BrowserStack's `getSessionDetails`. None of N4's files is an asset G1 compiles.
  - Self-check (author hygiene, not the gate): a scripted scan of the 23 touched files' code blocks finds no
    fabricated screenshot API, `Playwright.Shard`, TODO marker, floating Playwright version, inline comment or glob
    `ToHaveURLAsync`; every backticked skill name resolves and every relative `.md` link exists.
  - Proof: `responsive-testing/SKILL.md:93`; `realtime-stream-testing/SKILL.md:110,186,214,228`;
    `browser-cloud-setup/references/details.md:104,107,317`; `test-login-tokens/references/details.md:207,234,235`;
    `language-testing/SKILL.md:54,107,118,239`; `data-driven-testing/SKILL.md:251,266`;
    `production-uptime-checks/SKILL.md:112,128,142`; `qa/dotnet/agents/qa-api-dotnet.md:76,77`;
    `inhouse-framework-conventions/SKILL.md:111,150`; `api-test-author/playwright/SKILL.md:80,159,178,193`;
    `gherkin-step-code/SKILL.md:86`; `bdd-project-scaffold/SKILL.md:27,81`, `references/hooks.md:56,61`;
    `bdd-reviewer/SKILL.md:49,53,55`; `standards-audit/references/conformance-checklist.md:35,36,114,119,120,122,146,147,204-206,245,257,262,267,290,291`.

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

**As built (2026-10-11):**
- **Built.** The TS mobile lane is on §2.4's primary lane. `qa-mobile-typescript` has §5.3's 28 tools
  (`tools:` = the 7 core tools plus the list, in §5.3's order), a 634-char description naming Appium 3 and the
  supported lane, the five appium-mcp prerequisites, and Step 1 loading `evidence-capture/SKILL.md` and its
  Appium reference. `ui-test-author/appium` has a Versions table, `assets/` (10 files: `wdio.conf.ts`,
  `BaseTest.ts`, `BasePage.ts`, `LoginPage.ts`, `OrdersPage.ts`, `OrderRow.ts`, `orders.spec.ts`, `env.ts`,
  `package.json`, `tsconfig.json`), a per-platform ladder, scoped components, gestures, WebView and app-state
  sections. `mobile-native-features` (+ `references/details.md`), `mobile-screen-explorer`,
  `mobile-screen-objects`, `mobile-app-crawler` (the three `</content>` leftovers, `SCREENSHOTS_DIR`, the id
  grouping), `device-cloud` (+ new `references/aws-device-farm.md`), the review skill's Appium rows, the mobile
  half of `bdd-project-scaffold` (exact pins, no comments, a `Before`/`After` pair that attaches the failure
  screenshot and page source) and `cucumberjs-appium.md` (`this.attach`) are rewritten.
  `evidence-capture/references/appium.md` exists (10.1k chars); its SKILL.md lost the placeholder line, gained an
  Appium row in both tables and an "Appium: native app evidence" section, and its description is 448 chars.
  Sizes in bytes (`wc -c`, so an upper bound on chars): `evidence-capture/SKILL.md` 13.9k, `ui-test-author/appium`
  14.6k, `mobile-native-features` 14.8k, `device-cloud` 15.9k; `mobile-screen-explorer/SKILL.md` is 17.5k (it was
  16.7k; it was edited, not rewritten).
- **Left to plan 002.** Line 10 of `mobile-screen-explorer/SKILL.md` and the agent's "Related agents" section were
  already corrected by plan 002 W1 (`docs/plans/implemented/002-mobile-plugins.md`); M1 kept that wording.
- **Pins read from npm on 2026-10-11:** `webdriverio`, `@wdio/cli`, `@wdio/appium-service`, `@wdio/globals` 10.0.2;
  `@wdio/mocha-framework`, `@wdio/types`, `@wdio/allure-reporter`, `@wdio/cucumber-framework` 10.0.1; `appium`
  3.8.0; `appium-uiautomator2-driver` 8.7.0; `appium-xcuitest-driver` **12.17.1** (§2.4 says 12.x; the research
  table's 12.16.0 is one release old); `@cucumber/cucumber` 13.3.0; `@types/node` 24.19.2; `@types/mocha`
  10.0.10; `typescript` **5.9.3** (the registry's latest is 7.0.2; WDIO's types were not checked against it).
  WDIO 10 types and the WDIO 10 command sources (`mobile:` wrappers, `ElementArray`, `findSeries`, `strict`)
  were read from the packed 10.0.2 tarballs; nothing was run.
- **Built but unverified.** No asset was type-checked or run (G1 does it). Open risks for G1:
  - **§6.3's TS Appium install line is short.** The assets import `@wdio/allure-reporter` and `@wdio/logger`
    (hoisted from `webdriverio`) and need `@types/mocha` and `@types/node`; `ui-test-author/appium/assets/package.json`
    holds the exact set, and `tsconfig.json` the strict config (`types`: `node`, `mocha`, `@wdio/globals/types`,
    `@wdio/mocha-framework`). Use them for the scratch project.
  - The `appium:settings[disableIdLocatorAutocompletion]` capability key's type in `Options.Testrunner`, the
    `reporters` option `disableWebdriverScreenshotsReporting` type, and `.js` import suffixes under NodeNext.
  - `cucumberOpts.import` (the scaffold used `require`; the project is ESM), the `Before` hook's `mobile: clearApp`
    on a real device, and `afterScenario` being the Cucumber twin of `afterTest`.
  - `browser.execute<number, [Record<string, string>]>` generics, `$$().findSeries` returning `undefined` on no
    match (the type says `Element`), and `stopRecordingScreen` positional arguments on WDIO 9.
  - The RN `testID` → Android `resource-id` mapping and the need for `disableIdLocatorAutocompletion` rest on the
    UiAutomator2 README and secondary sources (D80); nothing ran on a device.
  - `device-cloud`: BrowserStack's `appiumVersion` capability and Appium 3 availability, Sauce's, and the Device
    Farm `APPIUM_NODE` package/spec contents (no web access to those docs; the types come from the research and
    the audit); `GET <hub>/status` through a vendor hub.
- **For G1, files M1 does not own.**
  - `qa/reporting/typescript/skills/test-reports` line 101 still fits: the hook is `BaseTest.ts`'s `afterTest`.
    Under Cucumber the same capture runs in `afterScenario`, which `evidence-capture/references/appium.md` §5 says.
  - `qa/typescript/skills/browser-cloud-setup` (`references/details.md:203,234,286`) still says the vendor service
    sets the status and manages the tunnel. `@wdio/browserstack-service` has no WDIO 10 build (D81).
  - The review checklist rows and the .NET/Java siblings keep their own wording until M2/M3.

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

**As built (2026-10-11):**
- **Built.** The Java mobile lane is on §2.4's primary lane. `qa-mobile-java` has §5.3's 28 tools (`tools:` = the 7
  core tools plus the list, in §5.3's order), a description naming java-client 11 on Appium 3 and the supported
  lane, the five appium-mcp prerequisites, and Step 1 loading `evidence-capture/SKILL.md` and its Appium
  reference; "scaffold" stays for S1. `ui-test-author/appium` has a Versions table, `assets/` (11 files:
  `build.gradle.kts`, `settings.gradle.kts`, `testng.xml`, `Env.java`, `AppiumDriverFactory.java`,
  `BaseMobileTest.java`, `BaseAppiumPage.java`, `LoginPage.java`, `OrdersPage.java`, `OrderRow.java`,
  `OrdersTest.java`, package `com.example.mobiletests.{support,pages,tests}`), a per-platform ladder, scoped
  components, gestures, WebView and app-state sections, and the `MigrateToV11` note. `mobile-native-features`
  (+ `references/details.md`; `support.nativefeatures`, `rejectFingerprint`, `mobile: setGeolocation`),
  `mobile-screen-explorer` (line 10 untouched), `mobile-screen-objects`, `mobile-app-crawler` (the three
  `</content>` leftovers, kebab ids in the template to PascalCase), `device-cloud` (+ `references/details.md`,
  new `references/aws-device-farm.md`), the review skill's Appium rows, the mobile lines of `bdd-project-scaffold`
  (Stack line, build line, a `MobileHooks` section in `references/hooks.md`), `gherkin-step-code`'s mobile
  variant (`new LoginPage(context.driver())`), `page-object-design`, and the Appium half of
  `browser-cloud-setup` are rewritten. `evidence-capture/references/appium.md` exists (nine sections, 11.4k
  chars); its SKILL.md lost the placeholder line, gained a one-line route and a `BaseMobileTest` row in "Who owns
  what".
- **Sizes in chars.** `evidence-capture/SKILL.md` 15,957 (was 15,745); `ui-test-author/review/SKILL.md` 15,992
  (was 15,636); `ui-test-author/appium/SKILL.md` 15,962; `device-cloud/SKILL.md` 15,953 (was 17.8k);
  `mobile-native-features/SKILL.md` 16,881 (was 26.6k; still over 16,000, which §6.5 counts).
- **Pins.** The asset build pins java-client 11.0.0, `selenium-support` **4.51.0** (§2.4 says ≥ 4.50; 4.51.0 is the
  newest in the research), TestNG 7.12.0, AssertJ 3.27.7, `allure-testng` 3.0.0, the Allure Gradle plugin 4.3.0 and
  CLI 2.46.1 (J1's). The D12 pin `allure-testng:2.29.0` in `mobile-native-features` is gone.
- **Left to plan 002.** Line 10 of `mobile-screen-explorer/SKILL.md` and the agent's "Related agents" section were
  already corrected by plan 002 W1; M2 kept that wording.
- **Built but unverified.** Nothing was compiled or run (G1 does it). Open risks for G1:
  - `AppiumDriverFactory`: `UiAutomator2Options.amend(String, Object)` carrying `appium:settings[...]` and
    `bstack:options`, `setAutoGrantPermissions` / `setAutoAcceptAlerts`, `new AndroidDriver(URL, Capabilities)`.
  - `BaseMobileTest`: a pattern `switch` on `AndroidDriver` / `IOSDriver` (an `AppiumDriver` is not a
    `CanRecordScreen`), `new IOSStartScreenRecordingOptions().withTimeLimit(Duration)`, `Allure.attachment(String,
    String, InputStream, AttachmentOptions)`, `driver.manage().logs()` on java-client 11, and the order of Allure's
    failure listener against the `@AfterMethod` (§9.1 left it unverified).
  - `BaseAppiumPage` / `OrderRow`: `WebDriverWait(driver, Duration)` with an `AppiumDriver` as the `WebDriver`,
    `.ignoring(StaleElementReferenceException.class)` before `.withMessage`, and `visibilityOfElementLocated`.
  - `NativeFeatures` (a code block, not an asset): `SupportsRotation` and `InteractsWithApps` import paths on
    java-client 11, `mobile: openNotifications` / `mobile: fingerprint` argument names, and `mobile: getClipboard`
    returning a base64 `String`.
  - `device-cloud/references/aws-device-farm.md`: the JDK `HttpClient` `PUT` to a presigned URL, and Device
    Farm's Appium version for a java-client 11 suite (no web access; read from the research and the audit).
  - The RN `testID` → Android `resource-id` mapping and the need for `disableIdLocatorAutocompletion` rest on the
    UiAutomator2 README and secondary sources (D80); nothing ran on a device.
- **For G1, files M2 does not own.**
  - `qa/cicd/java/skills/ci-pipelines` references upload `build/playwright-artifacts/` only. `evidence-capture/
    references/appium.md` §9 states `build/appium-artifacts/` as the Appium CI path (R7); a Java mobile job would
    upload it, and none exists yet.
  - `qa/reporting/java/skills/test-reports` names Appium in its description and defers to `BaseTest` for
    Playwright; the Appium hook is `BaseMobileTest`, which only `evidence-capture` names.

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

Landed: T1, J1, N1, T2, J2, N2, A1, T3 (2026-10-10), J3, N3, T4, J4, N4, M1, M2 (2026-10-11). Every other block is live.

---

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
- Checklist: only the mobile rows. Replace the removed APIs, and add an evidence-on-failure row. N4 reworded E11,
  L4 and L9 and appended A9, A10, E16, E17, F10, F11, I11–I13, K9, L14, M15 and M16 (all **[PW]**/[NUnit] or
  untagged); the mobile rows it left you are C4, D12, E14 and K6. A new row takes the next free number in its
  section (E18, L15, …), carries **[Appium]**, and is added to standards-audit/SKILL.md's scope table, which now
  lists every tagged row per scope (`mobile` keeps **[Appium]** rows; `api` and `ui` skip them).
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
- qa/dotnet/skills/evidence-capture/SKILL.md is 15,620 chars after N2. Replace its line 13 placeholder
  ("Appium: `references/appium.md`, written by M3") with one link line and keep the file ≤ 16,000; the
  Appium detail goes in references/appium.md. Mirror the Playwright side: Appium evidence in
  `<WorkDirectory>/appium-artifacts/<Class>.<Test>.<ext>` (R7), the name sanitized to `[A-Za-z0-9._-]`,
  attached with `TestContext.AddTestAttachment` and `AllureApi.AddAttachment(name, type, path)` (or the
  byte[] overload with its extension — three strings is a path, N2's references/playwright.md §6), no catch
  in the teardown (D31's reasoning applies to NUnit).

- T4 edited only the web half of bdd-project-scaffold (and its mobile Node line, now Node 24 / 22). The mobile
  templates are M1's as T4 found them: the mobile `package.json` (`^` ranges, a `jsonc` comment), `wdio.conf.ts`,
  `support/world.ts` (a `require` inside a getter) and `support/hooks.ts` (inline comments, `browser.reset?.()`, a
  failure screenshot taken but never attached) — R1, R5 and R6 apply. T4's browser-cloud-setup now defers the
  WebdriverIO/Appium versions to ui-test-author/appium and its mobile `wdio.conf.ts` excerpt has no comments; it is
  not M1's file.
- Leave two things to plan 002 W1, per D21: line 10 of mobile-screen-explorer/SKILL.md (the React Native
  testID mapping) and the agent's "Related agents" section. Plan 002 has landed them
  (docs/plans/implemented/002-mobile-plugins.md); keep its wording.

- M1 (qa/typescript, as built) settled things the .NET lane shares — read its D80–D82 and apply them:
  - The per-platform ladder: UiAutomator2 prefixes every `id` lookup with `<package>:id/`, and a React Native or
    Compose id has none, so the asset capabilities set `appium:settings[disableIdLocatorAutocompletion]` true
    (`AddAdditionalAppiumOption`, D80). One finder per element picks `AccessibilityId` on iOS and `Id` on Android.
  - The UiAutomator2 README warns that Google is deprecating `UiSelector`; it is the secondary rung.
  - Recording defaults to `StartRecordingScreen` with the 180 s Android cap and the iOS ffmpeg need; the
    `mobile:` recorders are the documented swap (D82).
  - Appium 3 availability on a farm is checked before the client bump (qa/typescript/skills/device-cloud, § Does the
    farm run Appium 3?).

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
   qa/typescript/skills/ui-test-author/appium/assets/* and its SKILL.md Versions table (M1).
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
- M1 left the TS assets as ten files: wdio.conf.ts, BaseTest.ts (the evidence hooks), BasePage.ts, LoginPage.ts,
  OrdersPage.ts, OrderRow.ts, orders.spec.ts, env.ts, package.json (every exact pin) and tsconfig.json. The TS setup
  skill points at them and copies none; its layout is that flat set under `src/pages/mobile/` and `test/specs/`
  in the project. The env vars are PLATFORM, DEVICE_NAME, APP_PATH, PLATFORM_VERSION (iOS), E2E_USER,
  E2E_PASSWORD, E2E_ORDER_NUMBER, E2E_ORDER_TITLE, and DEVICE_FARM (skips local recording). The pins are
  appium-uiautomator2-driver 8.7.0 and appium-xcuitest-driver 12.17.1; the Android capability
  `appium:settings[disableIdLocatorAutocompletion]` is set (D80). `.gitignore` takes test-results/,
  allure-results/ and evidence/. qa-mobile-typescript.md already has the Step 1 evidence row (M1); add only
  Step 0.
- M2 left the Java assets as eleven files: build.gradle.kts, settings.gradle.kts, testng.xml
  (`parallel="classes"`, `thread-count="1"`), Env.java, AppiumDriverFactory.java, BaseMobileTest.java (the evidence
  hooks), BaseAppiumPage.java, LoginPage.java, OrdersPage.java, OrderRow.java and OrdersTest.java, in package
  `com.example.mobiletests.{support,pages,tests}`. The Java setup skill points at them and copies none. The env
  vars are PLATFORM, DEVICE_NAME, APP_PATH, PLATFORM_VERSION (iOS), APPIUM_URL (default `http://127.0.0.1:4723`),
  E2E_USER, E2E_PASSWORD, E2E_ORDER_NUMBER, E2E_ORDER_TITLE and DEVICE_FARM (skips local recording). The Android
  capability `appium:settings[disableIdLocatorAutocompletion]` is set (D80, D84). Evidence lands in
  `build/appium-artifacts/` (R7); `.gitignore` takes build/, allure-results/ and evidence/.
  qa-mobile-java.md already has the Step 1 evidence row and the prerequisites (M2); add only Step 0.

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
3. docs/plans/implemented/002-mobile-plugins.md §8.5 (the test-id contract your selectors must follow).
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
- M1 left qa-mobile-typescript.md's description at 634 of 650 chars, so naming Maestro means cutting words
  elsewhere in it; S1 adds Step 0 before you. M1 also rewrote the Appium rows of ui-test-author/review (the
  Appium table is yours to leave; add a separate Maestro table) and gave evidence-capture/SKILL.md an
  "Appium: native app evidence" section and an Appium row in both tables; your route line goes beside them. Its
  body is 14.0k of 16,000 chars.
- M1's D80: a React Native testID is the Android resource-id with no package prefix. Check which identifier
  Maestro's `id:` matches before writing selectors.
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
- §6.3's Java Appium row: build the scratch project from qa/java/skills/ui-test-author/appium/assets/
  (build.gradle.kts, settings.gradle.kts, testng.xml at the root; the .java files under src/test/java, packages
  from their `package` lines; M2, D84). `gradle compileTestJava` succeeds; M2's As built lists its open typing
  risks (the `amend` calls, the recorder `switch`, `Allure.attachment`). The NativeFeatures class in
  mobile-native-features/SKILL.md and DeviceFarmRunner in device-cloud/references/aws-device-farm.md are code
  blocks, not assets; compile them in the same scratch project when the check can.
- §6.3's TS Appium row installs too little. Build the scratch project from
  qa/typescript/skills/ui-test-author/appium/assets/package.json and tsconfig.json (M1, D83): the assets
  import @wdio/allure-reporter and need @types/mocha and @types/node. M1's As built lists its open typing risks
  (the settings capability key, the reporter option, `.js` suffixes under NodeNext).
- README.md: the qa rows for the 3 evidence-capture skills, webmcp-testing, the 2 new
  mobile-project-setup skills and ui-test-author/maestro, and the counts.
- CLAUDE.md version policy: one Playwright line (Node 1.64 / Java·.NET·Python 1.63; a 1.64-only API is
  never taught on a 1.63 lane) and one Appium line (3 primary / 2 supported; java-client 11 /
  Appium.WebDriver 9 / WebdriverIO 10).
- docs/skills-catalog.md: ui-test-author/reviewer → review, bdd-project-setup → bdd-project-scaffold,
  the inhouse row; check the rows T2, J2, N2, A1, S1 and X1 added. Its "Known orphans" line (:31) still lists
  `production-uptime-checks-{dotnet,java,typescript}`: T4, J4 and N4 wire each into its `qa-api-<stack>` Step 3,
  so drop the stacks whose agent now loads it (grep the three agents).
- D34 leftovers no task owns: in qa/dotnet/skills/api-project-setup/SKILL.md (:193) and
  performance-project-setup/SKILL.md (:136) the UI sibling is `UiTests`, not `PlaywrightTests`; drop
  `dotnet tool install allure` from api-project-setup (:39, :107) — NuGet has no such tool — and point at
  qa/reporting/dotnet/skills/test-reports for the Allure CLI. Skip whatever M3 or an earlier task already fixed.
- D49 seam: T3's TS visual specs live in a `visual` project with `default: false`, so a nightly plain
  `npx playwright test` skips them. In each of qa/cicd/typescript/skills/ci-pipelines/references/
  {github-actions,gitlab-ci,azure-pipelines}.md, the schedule-gated visual step runs
  `npx playwright test --project=visual` in mcr.microsoft.com/playwright:v1.64.0-noble (the minimum, one
  step or one line each); skip whatever is already there.
- D53 seam: the Java visual job is J3's `docker run` step (qa/java/skills/visual-regression/references/
  playwright-snapshots.md §8), but the "Running in the pinned image" bullet of each
  qa/cicd/java/skills/ci-pipelines/references/{github-actions,gitlab-ci,azure-pipelines}.md still describes a
  container job. Point each bullet at §8 for the visual job (one line each); keep its description of the image.
  Also: the Java `test` task in J1's assets/build.gradle.kts does not exclude the `visual` group; the visual
  reference shows `excludeGroups("visual")` and a `visualTest` task as additions a project makes, so leave the
  asset alone unless a check needs it.
- D60 seam: the .NET visual job is N3's `docker run` step (qa/dotnet/skills/visual-regression/references/
  playwright-snapshots.md §8). In qa/cicd/dotnet/skills/ci-pipelines/references/{github-actions,azure-pipelines}.md
  the "Running in the pinned image" bullet still describes a container job; point each at that §8 for the visual
  job (one line each; GitLab's job already runs in the image — leave it). In all three .NET CI references the UI
  gate filter `($SHARD_FILTER)&TestCategory!=Flaky` becomes `…&TestCategory!=Flaky&TestCategory!=visual&TestCategory!=lighthouse&TestCategory!=grid`,
  so the nightly-only categories N3 introduced and N4's cloud-grid fixtures (D74, their own `TestCategory=grid` run)
  stay out of the PR gate.
- J4 seams: J1's `BaseTest.java` now has `protected Browser newBrowser(Playwright)` (D67) — the Java build
  compiles it with the rest. `qa/java/skills/ui-test-author/playwright/SKILL.md:83` still says "the two hooks";
  lifecycle.md §3 now has three — make it "the hooks" (J4 could edit only `BaseTest.java` and lifecycle.md). `data-driven-testing/SKILL.md` is 21,967 chars, a pre-existing size violation J4 did
  not rewrite (§6.5's 16,000 applies to files this plan rewrote; count it among the body violations). The D12 grep
  left one code pin, `allure-testng:2.29.0` in `qa/java/skills/mobile-native-features/SKILL.md`; M2 removed it. `qa/_shared/python-web-testing` pins `playwright==1.63.0` (§6.2's
  `python` stack).
- The final Status names what is unverified: no Appium flow ran on a device or emulator; no Maestro flow
  ran; no WebMCP test ran against a site that registers tools; the D9 comparators are recommendations. Then git mv the plan
  to docs/plans/implemented/.

Traps:
- No pwsh on this machine. Install the browsers the 1.63 Java/.NET bindings need with
  `npx playwright@1.63.0 install chromium`, which uses the same shared browser cache.
- No gradle or mvn on this machine. Download a Gradle distribution into the scratch dir. Never add a
  wrapper or build files to the repo.
- WebMCP assets (A1, D47): each stack has a `ProductPage` beside its WebMCP test. TS: copy
  qa/_shared/webmcp-testing/assets/webmcp.spec.ts and ProductPage.ts flat beside the writer's TS assets (the
  spec imports ./fixtures and ./ProductPage, and needs no extra npm package); `npx playwright test --list`
  shows its five tests under `chromium`. Leave both WebMCP test files out of every evidence-smoke run: they
  need an app that registers tools (.NET: `--filter TestCategory!=webmcp`).
- Java Playwright scratch project: build.gradle.kts, settings.gradle.kts and testng.xml go at the project
  root (the build calls useTestNG { suites("testng.xml") }); each .java asset goes under src/test/java at
  its package path (com/example/uitests/{support,pages,tests}/), WebMcpTest.java and the WebMCP
  ProductPage.java (pages/) included. J1's
  `installPlaywrightBrowsers` passes --with-deps, which needs sudo on Linux; the npx install above is
  enough.
- Java evidence smoke: BaseTest throws when BASE_URL is unset, so export one (http://localhost is enough
  for data: pages). Put the two smoke tests in com.example.uitests.tests extending BaseTest, and remove
  LoginTest and WebMcpTest from that scratch project (they need a real app). Pass condition: the failing
  test leaves build/playwright-artifacts/<Class>.<method>.{png,zip,webm}, the passing test leaves nothing,
  and build/playwright-videos/ is empty afterwards.
- Settle D39 in the same scratch project: `gradle playwright --args="trace open build/playwright-artifacts/<Class>.<method>.zip"`,
  then `--args="trace errors"` and `--args="trace close"`. If they fail, make the trace CLI Node-only in
  qa/java/skills/evidence-capture (SKILL.md "Reading a failure", references/playwright.md §8) and in
  qa/java/agents/qa-ui-java.md Mode A step 1, and record the reversal as a dated decision.
- J1's build.gradle.kts sets `allure { version.set("2.46.1") }` (D38). `compileTestJava` does not download a
  report runtime; do not run `allureReport`.
- .NET Playwright scratch project: Directory.Packages.props, UiTests.csproj and ui.runsettings (the csproj's
  RunSettingsFilePath points at it) in one folder, with all eight .cs assets (BaseTest, AuthSetup, LoginPage,
  HomePage, LoginTests and the rest) plus WebMcpTests.cs, ProductPage.cs and webmcp.runsettings from
  qa/_shared/webmcp-testing/assets/ beside them.
  `dotnet build` → 0 errors.
- .NET evidence smoke: BaseTest throws when BASE_URL is unset (http://localhost is enough for data: pages).
  AuthSetup is a [SetUpFixture] in the root namespace Example.UiTests: it signs in against a real app before
  every fixture under that namespace, and its failure fails them all. So declare the two smoke tests in a
  namespace outside Example.UiTests (e.g. `Smoke`), deriving from Example.UiTests.Support.BaseTest, or
  leave AuthSetup.cs, LoginTests.cs and WebMcpTests.cs out of the smoke project. Pass condition: the failing
  test leaves bin/Debug/net10.0/playwright-artifacts/<Class>.<Test>.{zip,png,webm}, the passing test leaves
  nothing, and bin/Debug/net10.0/playwright-videos/ is empty afterwards.
- Settle D43 in the .NET scratch project without pwsh: `playwright.ps1` runs the node binary and
  `package/cli.js` under bin/Debug/net10.0/.playwright/; call them directly with
  `trace open bin/Debug/net10.0/playwright-artifacts/<Class>.<Test>.zip`, then `trace errors` and
  `trace close`. If they fail, make the trace CLI Node-only in qa/dotnet/skills/evidence-capture (SKILL.md
  "Reading a failure", references/playwright.md §8), the last bullet of
  qa/dotnet/skills/ui-test-author/playwright/references/lifecycle.md §9 and qa/dotnet/agents/qa-ui-dotnet.md
  Mode A, and record the reversal as a dated decision.
- Settle D44 in the same project: save the `ci/nunit-shards.sh` block from
  qa/cicd/dotnet/skills/ci-pipelines/SKILL.md under $TMPDIR, run it as
  `bash nunit-shards.sh <scratch>/UiTests.csproj 2 <scratch>/shards` (the project needs two test classes; the
  two smoke classes are enough), and check each `<i>.filter` holds `FullyQualifiedName~<Namespace>.<Class>.`
  terms; then `dotnet test --no-build --filter "(<shard 1 filter>)"` runs only that shard's class. If
  `NUnit.DisplayName=FullName` or the parsing misbehaves, fix the script in that SKILL.md (the three CI
  references only call it). Running the script is part of this gate; nothing from it is committed.
- tools/token-audit.py exits non-zero while any size violation exists. Read the counts (≤ 160 total, 0
  description violations), not the exit code.
- Scratch projects live under $TMPDIR and are deleted afterwards. Nothing from them is committed.

Gate (this is the last task, so it carries the plan's only gate, in run order):
  §6.1 → §6.2 (write, then run) → §6.3 → §6.4 → §6.5
Fix what it finds — a failure may belong to any task above.

Commit: `chore(qa): 003 gate — version checker, asset builds, evidence smoke, docs reconciled (003 G1)`.
Close out per the plan's "Close-out — every task" before you stop.
````
