# Playwright 1.50 → 1.64 delta (researched 2026-10-10)

Purpose: upgrade a skills library pinned at Playwright 1.47–1.60 to 1.64.

## How this was researched

- The release notes were read from the raw Markdown that generates playwright.dev, not from memory or a summarizer:
  `docs/src/release-notes-{js,java,csharp,python}.md` on `microsoft/playwright@main` (the top section is 1.64, and there is no 1.65 section yet).
  The rendered pages are https://playwright.dev/docs/release-notes, https://playwright.dev/java/docs/release-notes, https://playwright.dev/dotnet/docs/release-notes and https://playwright.dev/python/docs/release-notes. Each version has its own anchor, for example `#version-164`.
- The GitHub release bodies were pulled with `gh api` for `microsoft/playwright`, `playwright-java`, `playwright-dotnet`, `playwright-python` and `playwright-pytest`. They contain binding-only items that the docs pages leave out (for example Python 1.60 and .NET 1.60).
- Binding coverage comes from the `* since:` and `* langs:` metadata in the API docs at tag `v1.64.0`: https://github.com/microsoft/playwright/tree/v1.64.0/docs/src/api (plus `test-api/` and `test-reporter-api/`).
  `langs: js` means the API is Node-only. A missing `langs` line means every binding has it.
- Versions were checked against the live registries on 2026-10-10: npm, Maven Central `maven-metadata.xml`, NuGet flat-container and registration APIs, the PyPI JSON API, and the MCR `v2/.../tags/list` endpoints.
- Shorthand used in this file: `RN-JS 1.xx` = https://playwright.dev/docs/release-notes#version-1xx. `RN-JAVA`, `RN-NET` and `RN-PY` are the same anchors on the `/java/`, `/dotnet/` and `/python/` sites. `GH-x vN` = https://github.com/microsoft/playwright-x/releases/tag/vN.
- **UNVERIFIED** marks anything that is not backed by a primary source.

---

## (a) Version-pin table (as of 2026-10-10)

> **Headline:** Node `@playwright/test` **1.64.0** shipped on **2026-10-07**. The **Java, .NET and Python 1.64 packages are not published yet**: Maven, NuGet and PyPI are all at **1.63.0**. Each binding repo's `main` has already rolled to the 1.64 driver (python `DRIVER_VERSION`=1.64.0; dotnet `DriverVersion`=1.64.0; java `DRIVER_VERSION`=1.64.0-beta-1791325510000), so 1.64 releases are imminent but not available. Pin non-Node stacks to 1.63.0 until they land.

| Artifact | Latest | Released | Source |
|---|---|---|---|
| npm `@playwright/test` | **1.64.0** (`next` = 1.65.0-alpha-2026-10-10; `beta` = 1.64.0-beta-1791568591000) | 2026-10-07 | https://registry.npmjs.org/@playwright/test |
| npm `playwright` / `playwright-core` | **1.64.0**, `engines.node` = `>=20` | 2026-10-07 | https://registry.npmjs.org/playwright |
| npm `@playwright/mcp` (standalone MCP server) | 0.0.83 (`engines.node >=18`) | 2026-09-28 | https://registry.npmjs.org/@playwright/mcp |
| npm `@playwright/cli` (standalone `playwright-cli`) | 0.1.22 | 2026-09-28 | https://registry.npmjs.org/@playwright/cli |
| npm `@playwright/experimental-ct-react` / `-vue` / `-react17` | **1.62.1, final**. Frozen in 1.63; the v1.64 docs say "removed and no longer published" | 2026-07-30 | https://registry.npmjs.org/@playwright/experimental-ct-react ; https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/test-components-js.md |
| npm `@playwright/experimental-ct-svelte` | 1.58.2, final (package removed in 1.59) | 2026-02-06 | registry + RN-JS 1.59 |
| Maven `com.microsoft.playwright:playwright` | **1.63.0** (1.64 not published) | GH release 2026-09-14 | https://repo1.maven.org/maven2/com/microsoft/playwright/playwright/maven-metadata.xml (`<release>1.63.0</release>`, lastUpdated 20260914) |
| NuGet `Microsoft.Playwright` | **1.63.0**, target netstandard2.0 | 2026-09-23 | https://api.nuget.org/v3-flatcontainer/microsoft.playwright/index.json |
| NuGet `Microsoft.Playwright.NUnit` | 1.63.0 (net462 / netcoreapp3.1 groups; NUnit >= 3.13.2) | 2026-09-23 | nuget registration API |
| NuGet `Microsoft.Playwright.MSTest` / `.MSTest.v4` | 1.63.0 / 1.63.0 | 2026-09-23 | nuget |
| NuGet `Microsoft.Playwright.Xunit` / `.Xunit.v3` | 1.63.0 / 1.63.0 (xunit 2.8+ / xunit.v3 1.0.1+) | 2026-09-23 | nuget |
| NuGet `Microsoft.Playwright.TestAdapter` | 1.63.0 | 2026-09-23 | nuget |
| PyPI `playwright` | **1.63.0**, `requires_python >=3.10` | 2026-09-15 | https://pypi.org/pypi/playwright/json |
| PyPI `pytest-playwright` | **0.10.0** (py >=3.10, pytest >=7,<10; `pytest-base-url` now an optional extra) | 2026-10-08 | https://pypi.org/pypi/pytest-playwright/json ; https://github.com/microsoft/playwright-pytest/releases/tag/v0.10.0 |
| PyPI `pytest-playwright-asyncio` | 0.10.0 (pytest >=8.2, pytest-asyncio >=0.24) | 2026-10-08 | https://pypi.org/pypi/pytest-playwright-asyncio/json |
| Docker `mcr.microsoft.com/playwright` | **`v1.64.0-noble`** (Ubuntu 24.04). Also `v1.64.0` (= noble), `v1.64.0-jammy` (22.04) and `v1.64.0-resolute` (26.04), each with `-amd64`/`-arm64` variants. Image ships Node 24 | 2026-10-07 | https://mcr.microsoft.com/v2/playwright/tags/list ; https://github.com/microsoft/playwright/blob/v1.64.0/utils/docker/Dockerfile.noble (`NODE_VERSION=24`) |
| Docker `mcr.microsoft.com/playwright/java` | `v1.63.0-noble` / `-jammy` / `-resolute` (no 1.64 yet). Image uses openjdk-25 | 2026-09-14 | https://mcr.microsoft.com/v2/playwright/java/tags/list |
| Docker `mcr.microsoft.com/playwright/dotnet` | `v1.63.0-noble` / `-resolute` (**no jammy since 1.60**). Base is `dotnet/sdk:10.0-noble` | 2026-09-21 | https://mcr.microsoft.com/v2/playwright/dotnet/tags/list ; GH-dotnet v1.60.0 |
| Docker `mcr.microsoft.com/playwright/python` | `v1.63.0-noble` / `-jammy` / `-resolute` | 2026-09-15 | https://mcr.microsoft.com/v2/playwright/python/tags/list |
| GitHub Action `microsoft/playwright-github-action` | **Deprecated and archived** (`isArchived: true`). The README says "You don't need this GitHub Action… use the Playwright CLI" | — | https://github.com/microsoft/playwright-github-action |
| Recommended CI install | `npx playwright install --with-deps` (Python `python -m playwright install --with-deps`; Java `mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install --with-deps"`; .NET `pwsh bin/Debug/net8.0/playwright.ps1 install --with-deps`). The docs workflow uses `actions/checkout@v6`, `actions/setup-node@v6` with `node-version: lts/*`, and `actions/upload-artifact@v4`. Container alternative: `mcr.microsoft.com/playwright:v<ver>-noble` with `options: --user 1001`. Add `--only-shell` on headless-only CI, or `--no-shell` with `channel: 'chromium'` | — | https://github.com/microsoft/playwright/blob/main/docs/src/ci-intro.md ; https://github.com/microsoft/playwright/blob/main/docs/src/ci.md ; https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/browsers.md |
| Browsers in 1.64.0 | Chromium 156.0.8078.4, Firefox 157.0, WebKit 27.2; also tested on Chrome 155 and Edge 155 | — | RN-JS 1.64 |
| 1.64.x patches | None released. `release-1.64` is 3 cherry-picks ahead of `v1.64.0`: dotnet async-suffix/`WebMCPToolAnnotations` alias, chromium `AvoidCorsURLLoaderRestartOnRedirect`, electron windows fix. A 1.64.1 is likely; contents are **UNVERIFIED** until released | — | `gh api repos/microsoft/playwright/compare/v1.64.0...release-1.64` |
| 1.65 alpha notes | None. `main` release notes start at 1.64; npm `next` = 1.65.0-alpha-2026-10-10 | — | registry + raw release-notes-js.md@main |

**Runtime minimums (current):**
- **Node**: `engines >=20` since **1.62.0** (npm metadata for 1.61.1 says `>=18`; 1.62.0 says `>=20`). The release notes never announce this. They only say Node 16 was removed and Node 18 deprecated in 1.54 (RN-JS 1.54). The docs System requirements (main) say "Node.js: latest 22.x, 24.x or 26.x" (https://github.com/microsoft/playwright/blob/main/docs/src/intro-js.md). Node 20 is EOL, so target 22/24.
- **Python**: `>=3.10` since **1.61.0** (PyPI metadata: 1.60.0 `>=3.9`, 1.61.0 `>=3.10`). Not in the release notes. The docs page still says "Python 3.8 or higher", which is stale (https://github.com/microsoft/playwright/blob/main/docs/src/intro-python.md). pytest-playwright dropped 3.9 in 0.7.2.
- **Java**: "Java 8 or higher" (intro-java.md). The official Docker image moved openjdk-21 → **openjdk-25 in 1.59** (playwright-java `utils/docker/Dockerfile.noble` at v1.58.0 vs v1.59.0). Not in the release notes.
- **.NET**: netstandard2.0 library, ".NET 8 recommended" (intro-csharp.md). The Docker image moved to **.NET SDK 10 in 1.60** (GH-dotnet v1.60.0).
- **OS** (intro-*.md on main): Windows 11+ / Server 2019+ / WSL; macOS 14+ (but WebKit needs macOS 15+, see 1.58/1.59); Debian 12/13; Ubuntu 22.04 / 24.04 / 26.04 (x86-64 or arm64).

---

## (b) Per-version delta, 1.51 → 1.64

Binding tags: **[all]** = Node + Java + .NET + Python. **[Node]** = `@playwright/test` / JS only. **[Java/NET/Py]** = everything except JS. **[Py]**, **[NET]**, **[Java]** = that binding only.
Release dates: npm, plus binding GitHub release dates (Java / .NET / Python).

### 1.50 (baseline, for skills pinned at 1.47–1.49): npm 2025-01-23; J 02-04 / N 02-03 / P 02-03
1. New APIs
   - `test.step(..., { timeout })` and `test.step.skip()` **[Node]**. RN-JS 1.50
   - `toMatchAriaSnapshot` can store snapshots in separate YAML files; `pathTemplate` for `toHaveScreenshot`/`toMatchAriaSnapshot` in `expect` config **[Node]**. RN-JS 1.50
   - `LocatorAssertions.toHaveAccessibleErrorMessage` **[all]**. RN-JS / RN-JAVA / RN-NET / RN-PY 1.50
   - `updateSnapshots: 'changed'`; `updateSourceMethod` (`patch` / `3-way` / `overwrite`); `webServer.gracefulShutdown`; `TestStep.attachments` **[Node]**. RN-JS 1.50
   - .NET: new `Microsoft.Playwright.Xunit` (xUnit 2.8+) **[NET]**. RN-NET 1.50
   - Python: pytest plugin supports async fixtures (`pytest-playwright-asyncio`) **[Py]**. RN-PY 1.50
2. Bindings: as tagged above. Test-runner items are Node-only.
3. Breaking: `toBeEditable()` / `isEditable()` throw on non-editable elements **[all]**. `updateSnapshots: 'all'` now updates all snapshots, not only changed ones **[Node]**. Canvas content in traces is hidden by default. RN-JS 1.50
4. Browsers: Chromium 133.0.6943.16, Firefox 134.0, WebKit 18.2 (Chrome/Edge 132). Node `>=18`. RN-JS 1.50

### 1.51: npm 2025-03-06 (1.51.1 03-17); J 03-17 / N 03-18 / P 03-18
1. New APIs
   - `browserContext.storageState({ indexedDB: true })` saves and restores IndexedDB **[all]**. RN-JS / RN-JAVA 1.51
   - `locator.filter({ visible: true | false })` **[all]**. RN-JS / RN-JAVA 1.51
   - `contrast` option on `page.emulateMedia` / `browser.newContext` (`prefers-contrast`) **[all]**. RN-JS / RN-JAVA 1.51
   - `apiRequest.newContext({ failOnStatusCode })` **[all]**. RN-JS / RN-JAVA 1.51
   - `expect(page).toHaveURL(predicate)` **[Node]** (the `url` param with predicate/URLPattern is `langs: js`; other bindings take `urlOrRegExp`). RN-JS 1.51 ; `docs/src/api/class-pageassertions.md@v1.64.0`
   - `TestStepInfo` object in `test.step(title, async step => …)`, with `step.skip()` and `step.attach()` **[Node]**. RN-JS 1.51
   - `TestConfig.captureGitInfo: { commit, diff }` puts git info in the HTML report **[Node]**. RN-JS 1.51
   - "Copy prompt" button on errors in the HTML report, trace viewer and UI mode **[Node tooling]**. RN-JS 1.51
2. Bindings: storageState, filter-visible, contrast and failOnStatusCode are all-binding. The rest is Node.
3. Breaking: none listed. 1.51.1 fixed a `TimeoutOverflowWarning` regression. GH v1.51.1
4. Browsers: Chromium 134.0.6998.35, Firefox 135.0, WebKit 18.4 (Chrome/Edge 133). RN-JS 1.51

### 1.52: npm 2025-04-17; J 05-02 / N 05-05 / P 04-30
1. New APIs
   - `expect(locator).toContainClass('done')` **[all]** (Java `containsClass`, .NET `ToContainClassAsync`, Python `to_contain_class`). RN-JS / RN-JAVA / RN-NET 1.52
   - Aria snapshot properties `/children: equal` (strict matching) and `/url:` for links **[all]**. RN-JS 1.52
   - `apiRequest.newContext({ maxRedirects })` **[all]**. RN-JS 1.52
   - `TestProject.workers`, `TestConfig.failOnFlakyTests`, `TestResult.annotations` **[Node]**. RN-JS 1.52
   - HTML report NOT-filters (`!@tag`, `!file`, `!p:project`) **[Node]**. RN-JS 1.52
2. Bindings: as tagged.
3. Breaking **[all]**: URL **glob patterns no longer support `?` and `[]`**; use RegExp. `route.continue()` **can no longer override the `Cookie` header** (use `context.addCookies`). macOS 13 deprecated for WebKit. RN-JS 1.52
4. Browsers: Chromium 136.0.7103.25, Firefox 137.0, WebKit 18.4 (Chrome/Edge 135). RN-JS 1.52

### 1.53: npm 2025-06-10 (1.53.1 06-18, 1.53.2 06-30); J 06-24 / N 06-25 / P 06-25
1. New APIs
   - `locator.describe('Subscribe button')` labels a locator in traces and reports **[all]**. RN-JS / RN-JAVA 1.53
   - `testInfo.snapshotPath(..., { kind })` **[Node]**. HTML reporter `title` option **[Node]**. RN-JS 1.53
   - `npx playwright install --list` lists installed browsers **[all CLIs]**. RN-JS 1.53
   - New Steps view in the Trace Viewer and HTML report. RN-JS 1.53
2. Bindings: `describe` is all-binding.
3. Breaking: none listed. Patches fixed a click/scroll regression, Chromium textarea fill, and pre-1.53 blob-report merge losing attachments (GH v1.53.1, v1.53.2).
4. Browsers: Chromium 138.0.7204.4 (1.53.1+: 138.0.7204.23), Firefox 139.0, WebKit 18.5 (Chrome/Edge 137). RN-JS 1.53 ; GH v1.53.1

### 1.54: npm 2025-07-10 (1.54.1 07-11, 1.54.2 08-01); J 07-21 / N 07-22 / P 07-22
1. New APIs
   - Cookie `partitionKey` in `context.cookies()` / `addCookies()` (CHIPS) **[all]**. RN-JS / RN-JAVA 1.54
   - HTML reporter `noSnippets` **[Node]**. Annotation `location` on `TestResult/TestInfo.annotations` **[Node]**. RN-JS 1.54
   - `--user-data-dir` on CLI commands such as `codegen` **[all CLIs]**. RN-JS 1.54
2. Bindings: partitionKey is all-binding.
3. Breaking: **`-gv` removed** from `npx playwright test` (use `--grep-invert`; 1.61 adds `-G`) **[Node]**. `playwright open` no longer opens the recorder (use `codegen`) **[all CLIs]**. **Node 16 removed, Node 18 deprecated** **[Node]**. RN-JS 1.54
4. Browsers: Chromium 139.0.7258.5, Firefox 140.0.2, WebKit 26.0 (Chrome/Edge 140). 1.54.1 fixed browser download behind HTTP(S) proxy. RN-JS 1.54 ; GH v1.54.1

### 1.55: npm 2025-08-20 (1.55.1 09-23); J 08-27 / N 09-04 / P 08-28
1. New APIs
   - `testStepInfo.titlePath` **[Node]**. RN-JS 1.55
   - Codegen can auto-generate `toBeVisible()` assertions (setting) **[all codegen targets]**. RN-JS / RN-JAVA 1.55
   - .NET: `Microsoft.Playwright.Xunit.v3` and `Microsoft.Playwright.MSTest.v4` packages **[NET]**. RN-NET 1.55
2. Bindings: as tagged.
3. Breaking: **Chromium extension Manifest V2 dropped** **[all]**. RN-JS 1.55
4. Browsers: Chromium 140.0.7339.16 (1.55.1: 140.0.7339.186), Firefox 141.0, WebKit 26.0 (Chrome/Edge 139). Debian 13 "Trixie" added. RN-JS 1.55 ; GH v1.55.1

### 1.56: npm 2025-10-06 (1.56.1 10-17); J 10-17 / N 11-10 / P 11-11
1. New APIs
   - **Playwright Test Agents**: planner / generator / healer, generated with `npx playwright init-agents --loop=vscode|claude|opencode` **[Node]**. The v1.64 docs also list `--loop=codex`. Regenerate the definitions after every Playwright upgrade. RN-JS 1.56 ; https://github.com/microsoft/playwright/blob/v1.64.0/docs/src/test-agents-js.md
   - `page.consoleMessages()`, `page.pageErrors()`, `page.requests()` return the most recent buffered items **[all]**. RN-JS / RN-JAVA / RN-NET / RN-PY 1.56
   - `--test-list` / `--test-list-invert` **[Node]**. HTML reporter option to disable "Copy prompt" (`noCopyPrompt`). HTML and UI "merge files". UI mode `--update-snapshots` options and single-worker mode **[Node]**. RN-JS 1.56
   - `PLAYWRIGHT_TEST` env var set in worker processes **[Node]**. Aria snapshots render and compare `input` `placeholder` **[all]**. RN-JS 1.56
2. Bindings: the agents are Node-only. The page buffers are all-binding.
3. Breaking / deprecation: the `BrowserContext.backgroundPage` event is **deprecated and never emitted**, and `backgroundPages()` returns `[]` **[all]**. RN-JS 1.56
4. Browsers: Chromium 141.0.7390.37, Firefox 142.0.1, WebKit 26.0. 1.56.1 renamed the agents to "test agents". RN-JS 1.56 ; GH v1.56.1

### 1.57: npm 2025-11-25; J 12-04 / N 12-04 / P 12-09
1. New APIs
   - **Chrome for Testing**: Playwright's Chromium now uses CfT builds. Headed mode uses `chrome`; headless uses `chrome-headless-shell`. Linux arm64 still used Chromium (changed in 1.63) **[all]**. RN-JS 1.57
   - `webServer.wait: { stdout|stderr: /regex/ }`. Named capture groups become env vars (`MY_SERVER_PORT`) **[Node]**. RN-JS 1.57
   - `Worker.console` event and `worker.waitForEvent('console')` (Java `waitForConsoleMessage`) **[all]**. RN-JS / RN-JAVA 1.57
   - `locator.description()` **[all]**. `locator.toString()` uses the description **[Node]**. RN-JS / RN-JAVA 1.57
   - `steps` option on `click` / `dragTo` (number of `mousemove`s) **[all]**. RN-JS 1.57
   - `TestConfig.tag` **[Node]**. "Speedboard" tab in the HTML report **[Node]**. RN-JS 1.57
   - Service-worker network requests are reported and routable through BrowserContext in **Chromium** (opt out: `PLAYWRIGHT_DISABLE_SERVICE_WORKER_NETWORK`). SW console goes to `Worker.console` (opt out: `PLAYWRIGHT_DISABLE_SERVICE_WORKER_CONSOLE`). Listed in the Node notes only; the guide is `service-workers-js-python.md`. RN-JS 1.57
2. Bindings: CfT, Worker.console, description and steps are all-binding.
3. Breaking: **`page.accessibility` removed** **[all]**; use axe. Docker images moved Node 22 → **Node 24**. RN-JS / RN-JAVA 1.57
4. Browsers: Chromium 143.0.7499.4, Firefox 144.0.2, WebKit 26.0. RN-JS 1.57

### 1.58: npm 2026-01-23 (1.58.1 01-30, 1.58.2 02-06); J 01-28 / N 02-02 / P 01-30
1. New APIs
   - `connectOverCDP(..., { isLocal: true })` **[all]**. RN-JS 1.58
   - UI Mode / Trace Viewer: 'system' theme, Cmd/Ctrl+F in code editors, reorganized network panel, auto-formatted JSON. HTML report Speedboard Timeline for merged reports **[Node]**. RN-JS 1.58
2. Bindings: as tagged.
3. Breaking **[all]**: **`_react` and `_vue` selector engines removed**. **`:light` selector suffix removed**. **`devtools` launch option removed** (use `args: ['--auto-open-devtools-for-tabs']`). **WebKit on macOS 13 removed**. RN-JS / RN-JAVA 1.58
4. Browsers: Chromium 145.0.7632.6, Firefox 146.0.1, WebKit 26.0 (Chrome/Edge 144). RN-JS 1.58

### 1.59: npm 2026-04-01 (1.59.1 same day); J 04-09 / N 04-09 / P 04-29
1. New APIs
   - **`page.screencast`** (`Screencast` class): `start({ path, size, quality, onFrame })`, `stop()`, `showActions({ position, duration, fontSize })` / `hideActions()`, `showChapter(title, { description, duration })`, `showOverlay(html)`, `showOverlays()` / `hideOverlays()`. Covers video with start/stop control, action annotations, overlays, real-time JPEG frames, and "agentic video receipts" **[all]**. RN-JS / RN-JAVA / RN-NET 1.59
   - `video: { mode, show: { actions: {...}, test: {...} } }` annotations in test fixtures **[Node]**. RN-JS 1.59
   - **`browser.bind(name, { workspaceDir, host, port })` / `browser.unbind()`** expose a launched browser to `playwright-cli`, `@playwright/mcp` (`--endpoint=<name>`) or `chromium.connect(endpoint)` **[all]** (the `metadata` option is Node-only). `playwright-cli show` opens a dashboard; `PLAYWRIGHT_DASHBOARD=1` shows test browsers there. RN-JS / RN-JAVA 1.59 ; `class-browser.md@v1.64.0`
   - **`npx playwright test --debug=cli`** lets an agent attach over `playwright-cli` **[Node]**. Python equivalent: `pytest --playwright-debug=cli` in pytest-playwright 0.9.0. RN-JS 1.59 ; GH-pytest v0.9.0
   - **`npx playwright trace open|actions|action|snapshot|close`** for CLI trace analysis **[Node CLI]**. RN-JS 1.59
   - `await using` (async disposables) for page, route, init script and others **[Node]**. RN-JS 1.59
   - `page.ariaSnapshot()`. `ariaSnapshot({ depth, mode: 'ai' | 'default' })`. `locator.normalize()` rewrites a locator to best-practice form. `page.pickLocator()` / `cancelPickLocator()` **[all]**. RN-JS 1.59 ; `class-locator.md@v1.64.0`
   - `context.setStorageState(state)` resets storage without a new context **[all]**. `page.clearConsoleMessages()` / `clearPageErrors()`. `filter` option on `consoleMessages()` / `pageErrors()`. `ConsoleMessage.timestamp()` **[all]**. RN-JS 1.59
   - `context.debugger` (`Debugger` class: `requestPause`, `resume`, `next`, `runTo`, `pausedDetails`). `context.isClosed()`. `request.existingResponse()`. `response.httpVersion()`. `tracing.start({ live })`. `launch({ artifactsDir })` **[all]**. `CDPSession.event` **[Node]**. RN-JS 1.59 ; `class-debugger.md@v1.64.0`
   - Trace mode `'retain-on-failure-and-retries'` **[Node]**. UI Mode "only tests affected by source changes" **[Node]**. RN-JS 1.59
   - **URLPattern** accepted wherever JS takes a URL matcher (`page.route`, `routeWebSocket`, `unroute`, `waitForURL`, `toHaveURL`, `frame({url})`) **[Node]**. Only the API docs show this (first in `docs/src/api/params.md@v1.59.0`, `langs: js`); not in the release notes, so treat the exact version as docs evidence only.
2. Bindings: Screencast, bind, debugger, ariaSnapshot options, normalize, pickLocator and setStorageState are all-binding. Trace CLI, `--debug=cli`, `await using` and video show are Node.
3. Breaking: **WebKit on macOS 14 removed** **[all]**. **`@playwright/experimental-ct-svelte` removed** **[Node]**. The **`junit` reporter now emits `<error>` vs `<failure>`** by error type **[Node]**. Java Docker image now openjdk-25 (Dockerfile diff, not in the notes). RN-JS 1.59
4. Browsers: Chromium 147.0.7727.15, Firefox 148.0.2, WebKit 26.4 (Chrome/Edge 146). 1.59.1 reverted the Windows hidden-console change that broke `codegen`, `--ui` and `show`. RN-JS 1.59 ; GH v1.59.1

### 1.60: npm 2026-05-11; J 05-18 / N 05-21 / P 05-18
1. New APIs
   - **`tracing.startHar(path, { content, mode, urlFilter })` / `tracing.stopHar()`** **[all]** (`resourcesDir` is Node-only; Node returns a Disposable for `await using`). Also `APIRequestContext.tracing` **[all]**. RN-JS / RN-JAVA 1.60 ; `class-tracing.md@v1.64.0`
   - **`locator.drop({ files } | { data })`** simulates an external drag-and-drop (dragenter / dragover / drop with a synthetic DataTransfer) **[all]**. RN-JS / RN-JAVA / RN-NET / RN-PY 1.60
   - **`expect(page).toMatchAriaSnapshot()`** works on Page **[all]**. `boxes` option on `ariaSnapshot` appends `[box=x,y,w,h]` **[all]**. RN-JS 1.60
   - **`test.abort(message)`** fails the running test from a fixture, hook or route handler **[Node]**. RN-JS 1.60
   - `Browser` `'context'` event. BrowserContext mirrors page events: `download`, `frameAttached`, `frameDetached`, `frameNavigated`, `pageClose`, `pageLoad` **[all]**. RN-JS 1.60
   - `getByRole(..., { description })` matches the accessible description **[all]**. `toHaveCSS(..., { pseudo: '::before' | '::after' })` **[all]**. `locator.highlight({ style })` plus `page.hideHighlight()` / `locator.hideHighlight()` **[all]**. RN-JS 1.60
   - `webSocketRoute.protocols()`. `connectOverCDP({ noDefaults })`. `WebError.location()` **[all]**. RN-JS 1.60
   - `ConsoleMessage.location()` gains `line` / `column`; `lineNumber` / `columnNumber` deprecated (Node, Python). RN-JS / RN-PY 1.60
   - `TestInfoError.errorContext` (e.g. the aria snapshot at assertion failure). `Reporter.onError(error, workerInfo)`. `{testFileBaseName}` in `snapshotPathTemplate` **[Node]**. `show-report` accepts `.zip` **[Node]**. RN-JS 1.60
   - **Python only:** `FormData` class for multipart. **`expect.soft(...)`** (needs pytest-playwright >= 0.8.0). All `timeout` params accept `datetime.timedelta`. More async context managers. Async predicates in `expect_request` / `expect_response`. Typed `expect_event` / `wait_for_event` overloads. GH-python v1.60.0 ; GH-pytest v0.8.0
   - **.NET only:** `Expect(locator, "custom message")` overloads prefix the failure message. GH-dotnet v1.60.0
2. Bindings: as tagged. The binding-only items appear only in the GitHub release bodies.
3. Breaking / removals: **`Locator.ariaRef()` removed** (Node). **`handle` option on `exposeBinding` removed** **[all]**. **`logger` option on `connect` / `connectOverCDP` removed** (Node). **`videosPath` / `videoSize` context options removed** (Node; use `recordVideo`). Runner now **errors when config overrides a non-option fixture** and **rejects `workers: 0` or negative** **[Node]**. .NET Docker → **SDK 10, no more jammy images** **[NET]**. RN-JS 1.60 ; RN-JAVA 1.60 ; GH-dotnet v1.60.0
4. Browsers: Chromium 148.0.7778.96, Firefox 150.0.2, WebKit 26.4 (Chrome/Edge 147). RN-JS 1.60

### 1.61: npm 2026-06-15 (1.61.1 06-23); J 06-29 / N 06-23 / P 06-29
1. New APIs
   - **WebAuthn passkeys:** `context.credentials` (`Credentials`: `create`, `get`, `delete`, `install`) is a virtual authenticator for `navigator.credentials.create()` / `get()` in all browsers **[all]**. RN-JS / RN-JAVA / RN-NET / RN-PY 1.61
   - **`page.localStorage` / `page.sessionStorage`** (`WebStorage`: `getItem`, `setItem`, `removeItem`, `clear`, `items`) **[all]** (Python `page.local_storage`; .NET `page.LocalStorage`). RN-JS 1.61
   - `apiResponse.securityDetails()` / `serverAddr()` **[all]**. `connectOverCDP({ artifactsDir })`. `screencast.showActions({ cursor })`. `onFrame` receives a `timestamp` **[all]**. RN-JS 1.61
   - **`video` gets the same modes as `trace`:** new `'on-all-retries'`, `'retain-on-first-failure'`, `'retain-on-failure-and-retries'` **[Node]**. RN-JS 1.61 ; `test-use-options-js.md@v1.64.0#video-modes`
   - `expect.soft.poll(...)`. `FullConfig.argv`. `FullConfig.failOnFlakyTests`. `TestInfo.errors` splits `AggregateError`. **`-G` = `--grep-invert`** **[Node]**. RN-JS 1.61
   - **HAR and trace recordings include WebSocket requests** **[all]**. RN-JS 1.61
2. Bindings: Credentials, WebStorage and WS-in-HAR are all-binding. Video modes and the CLI items are Node.
3. Breaking: none in the notes. **Python now requires >= 3.10** (PyPI `requires_python`; not in the notes). 1.61.1 fixed a regression where `expect.extend` overrode built-in matchers. RN-JS 1.61 ; PyPI ; GH v1.61.1
4. Browsers: Chromium 149.0.7827.55, Firefox 151.0, WebKit 26.5 (Chrome/Edge 149). **Ubuntu 26.04 supported** (`-resolute` Docker tags start at v1.61.0). RN-JS 1.61 ; MCR tags

### 1.62: npm 2026-07-24 (1.62.1 07-30); J 08-03 / N 08-11 / P 07-31
1. New APIs
   - **New component testing model:** stories and galleries. The built-in `mount(storyId)` fixture of `@playwright/test` returns a Locator with `update(props)` / `unmount()`. `TestOptions.reuseContext` (experimental, discouraged outside CT) **[Node]**. RN-JS 1.62 ; `test-components-js.md@v1.64.0`
   - **`signal: AbortSignal`** on most actions, navigations, waits and web-first assertions. It does not disable the timeout **[Node]** (`input-signal` template is `langs: js`). RN-JS 1.62 ; `params.md@v1.64.0`
   - **WebP**: `page.screenshot({ type: 'webp' })` or a `.webp` path; quality 100 is lossless **[all]**. **`toHaveScreenshot('x.webp')`** stores lossless WebP goldens **[Node]**. RN-JS / RN-JAVA 1.62
   - `Reporter.preprocess({ config, suite, testRun })` with `TestRun.skip`, `exclude`, `fixme`, `fail` and `skipSharding` **[Node]**. RN-JS 1.62
   - **`retryStrategy: 'immediate' | 'isolated'`** **[Node]**. RN-JS 1.62
   - `storageState({ credentials: true })` persists passkeys **[all]** (the API doc says `since: v1.61`). RN-JS 1.62 ; `class-browsercontext.md@v1.64.0`
   - **`scroll: 'auto' | 'none'`** action option opts out of auto scroll-into-view **[all]**. RN-JS / RN-JAVA 1.62
   - `apiResponse.timing()` **[all]**. **`locator.waitForFunction(fn)`** **[all]**. RN-JS / RN-JAVA 1.62
   - Functions as `evaluate` / `addInitScript` arguments (`exposeFunctions` option) **[Node]**. RN-JS 1.62 ; `params.md@v1.64.0` (`langs: js`)
   - **`npx playwright mcp` and `npx playwright cli`** are bundled in the `playwright` package **[Node]**. HTML reporter `mergeFiles` option **[Node]**. RN-JS 1.62
2. Bindings: WebP screenshot, scroll, timing and waitForFunction are all-binding. CT, signal, preprocess, retryStrategy and function args are Node.
3. Breaking / defaults: **headless clipboard is isolated from the OS** **[all]**. **Debian 11 unsupported** **[all]**. **Node `engines` → `>=20`** (npm metadata, not in the notes). 1.62.0 regressed tsconfig `extends` bare-specifier and directory-form project references (fixed in **1.62.1**; use 1.62.1+). RN-JS 1.62 ; GH v1.62.1
4. Browsers: Chromium 151.0.7922.34, Firefox 153.0, WebKit 26.5 (Chrome/Edge 151). RN-JS 1.62

### 1.63: npm 2026-09-04; J 09-14 / N 09-21 / P 09-15
1. New APIs
   - **Test locks:** `test('…', { lock: 'user-settings' }, …)`. Tests sharing a lock name never run concurrently, across files, workers and projects. `test.describe` accepts `lock` **[Node]**. RN-JS 1.63
   - **`page.frameLocator()` / `frame.frameLocator()` with no selector** searches every frame in the subtree; it errors if matches span several frames **[all]**. RN-JS / RN-JAVA / RN-NET / RN-PY 1.63
   - **`locator.visible()`** matches only visible elements; the recommended replacement for `:visible` **[all]** (**Python `locator.visible` and .NET `Locator.Visible` are properties**; Java/JS are methods). RN-JS / RN-PY / RN-NET 1.63 ; `class-locator.md@v1.64.0`
   - `test.step(title, body, { subtitle, params })`. `TestStep.subtitle` / `params`. API steps report the locator and URL as subtitle **[Node]**. RN-JS 1.63
   - **Aria and screen snapshots in traces:** Node `trace: { mode, snapshots: { dom, aria, screen } }`; Java/.NET/Python `tracing.start(snapshots, ariaSnapshots, screenSnapshots)` booleans. New "Display Aria" trace-viewer mode. RN-JS / RN-JAVA 1.63 ; `class-tracing.md@v1.64.0`
   - `httpCredentials` accepts an **array** (first origin match wins) **[all]**. `storageState({ opfs: true })` **[all]**. `Page` / `BrowserContext` `'dialogclosed'` events **[all]**. RN-JS / RN-JAVA 1.63
   - `locator.ariaSnapshotJSON()` / `page.ariaSnapshotJSON()` **[Node]** (`langs: js`; absent from the binding notes). Typed `request.get<User>()` JSON **[Node]**. RN-JS 1.63 ; `class-locator.md@v1.64.0`
   - Standalone `TestOptions.reducedMotion`, `forcedColors` and `contrast`. **`--add-reporter`**. `omitTags` for list, line, dot, github and junit. Built-in **`perfetto`** reporter. HTML step duration waterfall **[Node]**. RN-JS 1.63
   - `install --no-remove`. `codegen --http-credentials` **[all CLIs]**. RN-JS 1.63
   - **Java:** the public API is annotated with **JSpecify** `@NullMarked` / `@Nullable` **[Java]**. RN-JAVA 1.63
2. Bindings: as tagged.
3. Breaking / announcements: **`@playwright/experimental-ct-react`, `-react17` and `-vue` no longer updated** (last 1.62.1; migrate to the 1.62 stories model). **Ubuntu 20.04 unsupported**. **Linux arm64 now downloads Chrome for Testing** (was Chromium). RN-JS 1.63
4. Browsers: Chromium 153.0.8010.12, Firefox 155.0, WebKit 26.6 (Chrome/Edge 153). RN-JS 1.63

### 1.64: npm 2026-10-07; Java / .NET / Python **not yet released** (docs and binding `main` branches already describe them)
1. New APIs
   - **WebMCP:** `page.webmcp` / `frame.webmcp` (`WebMCP.tools()` returns `{ name, description, inputSchema }`; `WebMCP.callTool(name, input)`). Tests tools a page registers via the experimental `navigator.modelContext`. Needs Chromium `--enable-features=WebMCP`, or Firefox prefs `dom.modelcontext.enabled` + `dom.modelcontext.testing.enabled`. **WebKit does not implement it.** Tool metadata is untrusted input **[all]**. Playwright MCP exposes page tools as `webmcp_<tool>` by default (`--no-webmcp` opts out). `playwright-cli webmcp-list` / `webmcp-call`. RN-JS 1.64 ; `class-webmcp.md@v1.64.0`
   - **Videos:** `fps` (default 25; Firefox and WebKit capture up to 25 fps) on `video` **[Node]**, `recordVideo` (`recordVideoFps` in Java/.NET/Python) **[all]** and `screencast.start({ fps })` **[all]**. **`showActions({ style: { point, highlight, title } })`** CSS replaces `fontSize` (deprecated) **[all]**. Cursor persists across navigations and moves along an eased path. **Encoding switched VP8 → VP9**. RN-JS 1.64 ; `class-screencast.md@v1.64.0` ; `params.md` `context-option-recordvideo-fps`
   - **`TestProject.default: false`** keeps a project out of a plain run (`--project="*"` runs all; dependencies still run) **[Node]**. RN-JS 1.64 ; `test-api/class-testproject.md@v1.64.0`
   - **`--shuffle [seed]`** randomizes order; seed printed for replay **[Node]**. RN-JS 1.64 ; `test-cli-js.md@v1.64.0`
   - `test.describe.configure({ lock })` **[Node]**. `expect: { toHaveScreenshot: { type: 'webp' } }` stores unnamed screenshots as WebP **[Node]**. `FullConfig.filteredProjects` **[Node]**. `TestOptions.screen` (new standalone option) **[Node]**. RN-JS 1.64
   - **`locator.within(parent)`** **[all]**. See section (c). RN-JS 1.64 ; `class-locator.md@v1.64.0`
   - **`page.getByRef('e2')`** locates by an aria ref from `ariaSnapshot({ mode: 'ai' })` **[all]** (Python `get_by_ref`). RN-JS 1.64 ; `class-page.md@v1.64.0`
   - `page.content({ includeShadow: true })` / `frame.content(...)` serialize open shadow roots as declarative shadow DOM **[all]**. RN-JS 1.64
   - `credentials.create(..., { signCount })`; `create` / `get` return `signCount`; persisted in storage state **[all]**. RN-JS 1.64
   - **`apiRequestContext.addCookies()` / `cookies()` / `clearCookies()`** **[all]**. RN-JS 1.64
   - Undocumented CLI flag `--run-agents <missing|all|none>` "to generate the code for `page.perform`". `page.perform` is **not** in the public `types.d.ts` or API docs at v1.64.0, so **UNVERIFIED / experimental; do not teach it**. `test-cli-js.md@v1.64.0` ; `packages/playwright/src/program.ts@v1.64.0`
2. Bindings: WebMCP, `within`, `getByRef`, `includeShadow`, `signCount`, request cookies, `recordVideoFps` and screencast `fps`/`style` are all-binding per API `langs`. Java/.NET/Python ship them only when their 1.64 packages publish (`main` already has `Locator within(Locator)` (Java), `ILocator Within(ILocator)` (.NET) and `def within(self, locator)` (Python)). Everything in the test-runner bullet is Node.
3. Breaking **(Node test runner unless noted)**:
   - **Device descriptors now forward `screen`**. `...devices['Desktop Chrome']` changes `window.screen` and screen media queries. Opt out with `screen: undefined`. That this affects only Node is **UNVERIFIED**: library-mode `newContext(devices[...])` in other bindings already passed `screen`, and the new `TestOptions.screen` explains the Node-only change.
   - **JSX in test files follows `tsconfig.json`** (`jsx`, `jsxFactory`, `jsxFragmentFactory`, `jsxImportSource`). Default is the automatic runtime from `react/jsx-runtime`.
   - **`--update-snapshots=missing` now passes the run.** The no-flag mode is now named `'default'` (writes missing snapshots and fails, as before).
   - **Elements inside hidden iframes count as hidden** for actions, `isVisible()` and `toBeVisible()`. Core behaviour, so expected in **all bindings** once they ship 1.64.
   - VP9 video encoding (consumers that assumed VP8 WebM should re-check). `showActions.fontSize` / `video.show.actions.fontSize` **deprecated**.
   - v1.64 docs: the experimental CT packages are "removed and no longer published"; stay on 1.62 if you still depend on them. `test-components-js.md@v1.64.0`
   - RN-JS 1.64
4. Browsers: **Chromium 156.0.8078.4, Firefox 157.0, WebKit 27.2** (Chrome/Edge 155). Node `>=20`. Docker images `v1.64.0-{noble,jammy,resolute}` ship Node 24. RN-JS 1.64 ; MCR tags

### Pre-range notes for libraries pinned at 1.47 (brief)
- **1.48:** `page.routeWebSocket()` / `context.routeWebSocket()` **[all]**. `page.requestGC()`. `test.step({ location })`. FormData for `fetch.form`. RN-JS 1.48
- **1.49:** **aria snapshots** (`toMatchAriaSnapshot`, `locator.ariaSnapshot`). **`chrome` / `msedge` channels switched to new headless**. Default headless Chromium is `chromium-headless-shell`; `channel: 'chromium'` opts into new headless. `TestConfig.tsconfig`. `test.fail.only`. Multiple globalSetup / globalTeardown. Screenshot `'on-first-failure'`. `tracing.group()`. Docker Node 22. WebKit updates stopped for Ubuntu 20.04 and Debian 11. ct-vue2 and ct-solid frozen. RN-JS 1.49

### Topic index (the "pay attention" list)
| Topic | Where |
|---|---|
| Screenshots / WebP | 1.62 (page.screenshot webp all; toHaveScreenshot `.webp` Node); 1.64 (`expect.toHaveScreenshot.type: 'webp'`) |
| Video / screencast | 1.59 Screencast API; 1.61 video modes and cursor; 1.64 fps, style, VP9; 1.60 removed `videosPath`/`videoSize` |
| Tracing / trace viewer | 1.53 Steps view; 1.59 `live`, trace CLI, `retain-on-failure-and-retries`; 1.60 startHar/stopHar, JSON pretty-print; 1.61 WebSocket in traces; 1.63 aria/screen snapshots plus Display Aria |
| HAR | 1.60 `tracing.startHar`; 1.61 WebSocket entries |
| Aria snapshots | 1.52 `/children`, `/url`; 1.56 placeholder; 1.59 page.ariaSnapshot, mode `ai`, depth; 1.60 page-level `toMatchAriaSnapshot`, boxes; 1.63 ariaSnapshotJSON (Node); 1.64 getByRef |
| Locators | 1.51 `filter({visible})`; 1.53 `describe`; 1.57 `description`; 1.59 `normalize`, `pickLocator`; 1.60 `getByRole({description})`, `drop`; 1.62 `waitForFunction`, `scroll`; 1.63 `visible()`, selector-less `frameLocator()`; 1.64 `within`, `getByRef` |
| Assertions | 1.50 toHaveAccessibleErrorMessage; 1.51 toHaveURL predicate (Node); 1.52 toContainClass; 1.60 toHaveCSS `pseudo`, page toMatchAriaSnapshot, Py `expect.soft`, .NET custom message; 1.61 `expect.soft.poll` (Node); 1.62 `signal` (Node) |
| Clock | No changes 1.51–1.64 (no `since: v1.5x/1.6x` entries in `class-clock.md@v1.64.0`) |
| Network | 1.52 glob `?`/`[]` removed, Cookie override removed; 1.56 page.requests(); 1.57 SW routing (Chromium); 1.60 WebSocketRoute.protocols; 1.61 APIResponse.securityDetails/serverAddr; 1.62 APIResponse.timing; 1.63 httpCredentials array; 1.64 APIRequestContext cookies |
| Console / errors | 1.56 consoleMessages/pageErrors; 1.57 Worker.console; 1.59 filter, clear, timestamp; 1.60 WebError.location, line/column |
| Storage state | 1.51 indexedDB; 1.59 setStorageState; 1.61/1.62 credentials; 1.61 WebStorage; 1.63 opfs; 1.64 signCount |
| Test agents / MCP / CLI | 1.56 init-agents; 1.59 bind, dashboard, `--debug=cli`, trace CLI; 1.62 bundled `npx playwright mcp`/`cli`; 1.64 WebMCP in MCP/CLI, `init-agents --loop=codex` (docs) |
| WebMCP | 1.64 |
| CLI flags | 1.54 `-gv` removed; 1.56 `--test-list(-invert)`; 1.59 `--debug=cli`; 1.61 `-G`; 1.63 `--add-reporter`, `install --no-remove`; 1.64 `--shuffle`. `--only-changed`, `--last-failed`, `--fail-on-flaky-tests` predate 1.50 and are still present (`--last-failed-file` documented at v1.64.0) |
| Reporters | html: 1.53 `title`, 1.54 `noSnippets`, 1.56 `noCopyPrompt`, 1.62 `mergeFiles`; `doNotInlineAssets` in v1.64 docs; 1.57 Speedboard; 1.58 Timeline; 1.59 junit error/failure split; 1.62 `preprocess`; 1.63 perfetto, `omitTags` |
| test.step | 1.50 timeout, skip; 1.51 TestStepInfo; 1.55 titlePath; 1.63 subtitle, params |
| Fixtures | 1.60 overriding a non-option fixture in config is an error; 1.62 `mount`; fixture `box`/`title` predate the range |
| webServer | 1.50 gracefulShutdown; 1.57 wait (stdout/stderr regex, named groups to env) |
| CfT / headless | 1.49 new-headless channels; 1.57 Chrome for Testing; 1.63 linux-arm64 CfT; `--only-shell` / `--no-shell` |
| Firefox / WebKit | WebKit macOS 13 dropped in 1.58, macOS 14 dropped in 1.59; WebKit 18.x → 26.x in 1.54 → 27.2 in 1.64; Firefox/WebKit video max 25 fps; WebKit lacks WebMCP |
| Android / Electron | Still experimental, Node-only (`_android`, `_electron`). Docs moved to `docs/src/mobile-api` and `docs/src/electron-api` (out of `docs/src/api`) after v1.59.0. A move of Electron to `@playwright/electron` (#40184) was **reverted** (#40733, 2026-05-08), so `_electron` stays on `playwright`; npm `@playwright/electron` is only a 0.0.1 placeholder plus 1.60 alphas. No release-note entries in the range. https://github.com/microsoft/playwright/pull/40733 |

---

## (c) `locator.within()`: it exists, added in **v1.64**

**Source:** `docs/src/api/class-locator.md@v1.64.0` (`## method: Locator.within`, `* since: v1.64`, no `langs`, so all bindings). Live docs: https://playwright.dev/docs/api/class-locator#locator-within (the Java site https://playwright.dev/java/docs/api/class-locator also shows "Added in: v1.64"). Release note: RN-JS 1.64 "🪆 Locator.within()".

**Semantics (doc text):** "Returns a locator that matches this locator's elements inside each element matched by `locator`." "Relative locators, such as `nth` or `first`, are resolved separately inside each matched parent."

**Implementation (v1.64.0 client):**
```ts
// packages/playwright-core/src/client/locator.ts@v1.64.0
within(locator: Locator): Locator {
  return locator.locator(this);
}
```
So `child.within(parent)` is **exactly** `parent.locator(child)`, which builds the selector `parent >> internal:chain=<child>`. It is reversed-order sugar ("this button, within that dialog") for when both locators already exist, for example as page-object fields. It takes no filter options. Both locators must be in the same frame, or you get the `Locators must belong to the same frame.` error from `locator()`. Like any locator it is strict for actions.

**Signatures**
| Lang | Signature | Status 2026-10-10 |
|---|---|---|
| Node/TS | `locator.within(locator: Locator): Locator` | released in 1.64.0 |
| Java | `Locator within(Locator locator)` | in `playwright-java@main` `Locator.java` (`@since v1.64`); **not on Maven yet** (latest 1.63.0) |
| .NET | `ILocator Within(ILocator locator)` | in `playwright-dotnet@main` `ILocator.cs`; **not on NuGet yet** (latest 1.63.0) |
| Python | `def within(self, locator: "Locator") -> "Locator"` (a method, unlike the `visible` property) | in `playwright-python@main` `_generated.py`; **not on PyPI yet** (latest 1.63.0) |

**How it differs from the neighbours**
| API | Returns | Use when |
|---|---|---|
| `child.within(parent)` (1.64) | **child** elements inside each parent; `nth`/`first`/`last` inside `child` resolve **per parent** | you hold both locators and want "X within Y", or column-style queries |
| `parent.locator(child)` (1.14) | identical result to `child.within(parent)`; accepts `has`/`hasText`/`hasNot`/`hasNotText` options too | chaining from the container; a string selector child |
| `parent.getByRole(...).nth(2)` (plain chain) | `nth` applies to the **flattened** result (e.g. the third cell of the whole table) | "the Nth match overall" |
| `parent.filter({ has: child })` (1.22) | **parent** elements that contain a child; inner locator must be relative and have no FrameLocator | picking the container (row/card) by its content |
| `a.and(b)` (1.34) | elements matching **both** a and b (same element, intersection) | combining role plus title/test-id on one element |
| `a.or(b)` (1.33) | elements matching either | alternative UIs |
| `locator.visible()` (1.63) / `filter({ visible })` (1.51) | same elements, filtered by visibility | replacing `:visible` |

Note: `parent.locator(childLocatorWithNth)` gives the same per-parent `nth` resolution in 1.64, because `within` delegates to it. Whether that held before 1.64 is **UNVERIFIED**, so rely on it only at 1.64+.

**Examples.** The column examples are verbatim from the v1.64.0 API doc. The dialog examples in Java/.NET/Python are adapted from the JS release note.

```ts
// Node/TS
const saveButton = page.getByRole('button', { name: 'Save' });
const dialog = page.getByTestId('settings-dialog');
await saveButton.within(dialog).click();

const thirdColumn = page.getByRole('cell').nth(2).within(page.getByRole('row'));
await expect(thirdColumn).toHaveText(['Apple', 'Banana', 'Cherry']);
```
```java
// Java
Locator saveButton = page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName("Save"));
Locator dialog = page.getByTestId("settings-dialog");
saveButton.within(dialog).click();

Locator thirdColumn = page.getByRole(AriaRole.CELL).nth(2).within(page.getByRole(AriaRole.ROW));
assertThat(thirdColumn).hasText(new String[] {"Apple", "Banana", "Cherry"});
```
```csharp
// .NET
var saveButton = page.GetByRole(AriaRole.Button, new() { Name = "Save" });
var dialog = page.GetByTestId("settings-dialog");
await saveButton.Within(dialog).ClickAsync();

var thirdColumn = page.GetByRole(AriaRole.Cell).Nth(2).Within(page.GetByRole(AriaRole.Row));
await Expect(thirdColumn).ToHaveTextAsync(new[] { "Apple", "Banana", "Cherry" });
```
```python
# Python (sync)
save_button = page.get_by_role("button", name="Save")
dialog = page.get_by_test_id("settings-dialog")
save_button.within(dialog).click()

third_column = page.get_by_role("cell").nth(2).within(page.get_by_role("row"))
expect(third_column).to_have_text(["Apple", "Banana", "Cherry"])
```

---

## (d) Breaking / must-fix when upgrading from 1.47–1.60 to 1.64

Ordered by the version that introduced each item. Fix only what is newer than your pin.

1. **(1.49)** `chrome` / `msedge` channels run new headless. Default headless Chromium is `chromium-headless-shell`. Opt into new headless with `channel: 'chromium'`. On CI use `install --only-shell` (default) or `--no-shell` (with `channel:'chromium'`). RN-JS 1.49 ; browsers.md
2. **(1.50)** `toBeEditable()` / `isEditable()` throw on non-editable elements. `--update-snapshots=all` now rewrites everything; use `changed` for the old behaviour. RN-JS 1.50
3. **(1.52)** URL globs: **`?` and `[]` no longer supported**, so rewrite to RegExp. `route.continue({ headers: { cookie } })` is ignored; use `context.addCookies`. RN-JS 1.52
4. **(1.54)** `-gv` removed; use `--grep-invert` / `-G` (1.61+). `playwright open` no longer records; use `codegen`. Node 16 gone. RN-JS 1.54
5. **(1.55)** Chromium Manifest V2 extensions unsupported. RN-JS 1.55
6. **(1.56)** `backgroundPage` event / `backgroundPages()` are dead (deprecated, empty). RN-JS 1.56
7. **(1.57)** **`page.accessibility` removed** (all bindings); use axe-core (`@axe-core/playwright`, `axe-core-maven-html`, `Deque.AxeCore.Playwright`, `axe-playwright-python`). Chromium is now Chrome for Testing. Docker images ship Node 24. Chromium service-worker requests now go through context routing (`PLAYWRIGHT_DISABLE_SERVICE_WORKER_NETWORK=1` to opt out). RN-JS 1.57
8. **(1.58)** **`_react=` / `_vue=` selectors removed**; use `getByRole`/`getByTestId`. **`:light` suffix removed**. **`launch({ devtools })` removed**; use `args: ['--auto-open-devtools-for-tabs']`. WebKit on macOS 13 gone. RN-JS 1.58
9. **(1.59)** WebKit on macOS 14 gone (WebKit needs macOS 15+). `experimental-ct-svelte` removed. **junit reporter now distinguishes `<error>` from `<failure>`**, so CI parsers that count failures may change. Java Docker image is JDK 25. RN-JS 1.59 ; playwright-java Dockerfile
10. **(1.60)** Removed: `locator.ariaRef()`; `exposeBinding(..., { handle })`; `logger` on `connect` / `connectOverCDP`; **context `videosPath` / `videoSize`** (use `recordVideo: { dir, size }`). Config that overrides a **non-option fixture now errors**. **`workers: 0` rejected**. `ConsoleMessage.location().lineNumber/columnNumber` deprecated; use `line`/`column`. .NET Docker on SDK 10 with **no jammy .NET images**. RN-JS 1.60 ; GH-dotnet v1.60.0
11. **(1.61)** **Python >= 3.10 required** (PyPI metadata). RN-PY / PyPI
12. **(1.62)** **Node >= 20** (`engines`); target 22/24 per docs. **Debian 11 unsupported**. Headless clipboard isolated from the OS: tests that read the host clipboard break. Use 1.62.1+, not 1.62.0, because of the tsconfig `extends` / references regressions. RN-JS 1.62 ; GH v1.62.1 ; npm
13. **(1.63)** **Experimental CT packages frozen at 1.62.1** (the 1.64 docs say removed). Migrate to the `mount()` stories model or stay on 1.62. **Ubuntu 20.04 unsupported**. Linux arm64 Chromium is now CfT. Prefer `locator.visible()` over `:visible` (not removed). RN-JS 1.63
14. **(1.64)** `devices[...]` now applies **`screen`** (opt out `screen: undefined`). **JSX compiled per tsconfig** (automatic runtime by default). **`--update-snapshots=missing` passes** (new `'default'` mode keeps the old fail behaviour). **Hidden-iframe elements are hidden**, which can flip `toBeVisible`/actions. **Videos are VP9**. `showActions`/`video.show.actions` **`fontSize` deprecated** in favour of `style.title`. RN-JS 1.64
15. **Cross-stack pinning:** do not bump Java/.NET/Python skills to 1.64 until Maven/NuGet/PyPI publish it (all 1.63.0 on 2026-10-10). A 1.64-only API (`within`, `getByRef`, `webmcp`, request cookies, `fps`/`style`, `includeShadow`, `signCount`) will not compile or import on 1.63.
16. **CI:** stop using `microsoft/playwright-github-action` (archived). Use `npx playwright install --with-deps` or the `mcr.microsoft.com/playwright:v1.64.0-noble` container, and pin the image tag to the package version.
17. **Agents:** if a repo uses Playwright Test Agents, **re-run `npx playwright init-agents --loop=<client>` after the upgrade**; the definitions are versioned with Playwright. test-agents-js.md

---

## (e) Node-only vs all-bindings matrix (most important features)

✅ = available; — = not available; ⏳ = API documented and present in the binding's `main`, but that binding's 1.64 package is not published as of 2026-10-10.

| Feature (since) | Node | Java | .NET | Python | Source |
|---|---|---|---|---|---|
| `locator.within()` (1.64) | ✅ | ⏳ | ⏳ | ⏳ | class-locator.md@v1.64.0 |
| `page.getByRef()` (1.64) | ✅ | ⏳ | ⏳ | ⏳ | class-page.md@v1.64.0 |
| `page.webmcp` / `frame.webmcp` (1.64) | ✅ | ⏳ | ⏳ | ⏳ | class-webmcp.md@v1.64.0 |
| `APIRequestContext` add/clear/get cookies (1.64) | ✅ | ⏳ | ⏳ | ⏳ | class-apirequestcontext.md@v1.64.0 |
| Video `fps` / screencast `style` (1.64) | ✅ | ⏳ (`recordVideoFps`) | ⏳ | ⏳ | params.md / class-screencast.md@v1.64.0 |
| `TestProject.default`, `--shuffle`, `describe.configure({lock})`, `toHaveScreenshot.type:'webp'` (1.64) | ✅ | — | — | — | RN-JS 1.64 |
| `locator.visible()` (1.63) | ✅ method | ✅ method | ✅ `Visible` property | ✅ `visible` property | RN-* 1.63 |
| Selector-less `frameLocator()` (1.63) | ✅ | ✅ | ✅ | ✅ | RN-* 1.63 |
| Trace aria/screen snapshots (1.63) | ✅ `snapshots:{dom,aria,screen}` | ✅ `setAriaSnapshots/ScreenSnapshots` | ✅ | ✅ | class-tracing.md@v1.64.0 |
| `ariaSnapshotJSON()` (1.63) | ✅ | — | — | — | class-locator.md (`langs: js`) |
| Test locks, step `subtitle`/`params`, `--add-reporter`, perfetto (1.63) | ✅ | — | — | — | RN-JS 1.63 |
| httpCredentials array, storageState `opfs`, `dialogclosed` (1.63) | ✅ | ✅ | ✅ | ✅ | RN-* 1.63 |
| `AbortSignal` `signal` option (1.62) | ✅ | — | — | — | params.md `input-signal` (`langs: js`) |
| Functions as evaluate/init-script args (1.62) | ✅ | — | — | — | params.md (`langs: js`) |
| WebP `page.screenshot` (1.62) | ✅ | ✅ | ✅ | ✅ | RN-* 1.62 |
| `scroll:'none'`, `locator.waitForFunction`, `APIResponse.timing` (1.62) | ✅ | ✅ | ✅ | ✅ | RN-* 1.62 |
| Component testing `mount()` stories, `retryStrategy`, `Reporter.preprocess` (1.62) | ✅ | — | — | — | RN-JS 1.62 |
| Bundled `npx playwright mcp` / `cli` (1.62) | ✅ | — | — | — | RN-JS 1.62 (pytest uses `python -m playwright cli …` per GH-pytest v0.9.0) |
| WebAuthn `context.credentials` (1.61) | ✅ | ✅ | ✅ | ✅ | RN-* 1.61 |
| `page.localStorage` / `sessionStorage` (1.61) | ✅ | ✅ | ✅ | ✅ | RN-* 1.61 |
| WebSocket in HAR/trace (1.61) | ✅ | ✅ | ✅ | ✅ | RN-* 1.61 |
| Video modes `on-all-retries` etc. (1.61), `expect.soft.poll`, `-G` | ✅ | — | — | — | RN-JS 1.61 |
| `tracing.startHar/stopHar` (1.60) | ✅ (+`await using`) | ✅ | ✅ | ✅ | RN-* 1.60 |
| `locator.drop()` (1.60) | ✅ | ✅ | ✅ | ✅ | RN-* 1.60 |
| Page-level `toMatchAriaSnapshot`, `boxes` (1.60) | ✅ | ✅ | ✅ | ✅ | RN-* 1.60 |
| `getByRole({description})`, `toHaveCSS({pseudo})` (1.60) | ✅ | ✅ | ✅ | ✅ | RN-* 1.60 |
| `test.abort()` (1.60) | ✅ | — | — | — | RN-JS 1.60 |
| Soft assertions | ✅ `expect.soft` (pre-1.50) | — (UNVERIFIED: no Java soft-assert in notes) | — (custom message only, 1.60) | ✅ `expect.soft` (1.60, pytest-playwright >= 0.8.0) | GH-python v1.60.0 ; GH-dotnet v1.60.0 |
| `page.screencast` (1.59) | ✅ | ✅ | ✅ | ✅ | RN-* 1.59 |
| `browser.bind()` / `unbind()` (1.59) | ✅ | ✅ | ✅ | ✅ | RN-* 1.59 |
| `context.setStorageState`, `consoleMessages({filter})`, `clear*` (1.59) | ✅ | ✅ | ✅ | ✅ | RN-* 1.59 |
| `ariaSnapshot({mode:'ai', depth})`, `locator.normalize()`, `page.pickLocator()` (1.59) | ✅ | ✅ | ✅ | ✅ | RN-* 1.59 |
| `--debug=cli`, `npx playwright trace …` CLI (1.59) | ✅ | — | — | ✅ via `pytest --playwright-debug=cli` (pytest-playwright 0.9.0) | RN-JS 1.59 ; GH-pytest v0.9.0 |
| URLPattern URL matchers (docs since 1.59) | ✅ | — | — | — | params.md (`langs: js`) |
| `page.requests()` / `consoleMessages()` / `pageErrors()` (1.56) | ✅ | ✅ | ✅ | ✅ | RN-* 1.56 |
| Test Agents `init-agents` (1.56) | ✅ | — | — | — | RN-JS 1.56 |
| `Worker.console`, `locator.description()`, click `steps` (1.57) | ✅ | ✅ | ✅ | ✅ | RN-* 1.57 |
| `webServer.wait`, `TestConfig.tag`, Speedboard (1.57) | ✅ | — | — | — | RN-JS 1.57 |
| `locator.describe()` (1.53) | ✅ | ✅ | ✅ | ✅ | RN-* 1.53 |
| `toContainClass` (1.52) | ✅ | ✅ `containsClass` | ✅ | ✅ | RN-* 1.52 |
| `failOnFlakyTests` config, `TestProject.workers` (1.52) | ✅ | — | — | — | RN-JS 1.52 |
| storageState `indexedDB`, `filter({visible})`, `contrast`, `failOnStatusCode` (1.51) | ✅ | ✅ | ✅ | ✅ | RN-* 1.51 |
| `toHaveURL(predicate)` (1.51) | ✅ | — | — | — | class-pageassertions.md (`langs: js`) |
| TestStepInfo, `captureGitInfo`, "Copy prompt" (1.51) | ✅ | — | — | — | RN-JS 1.51 |
| Android / Electron (experimental) | ✅ `_android`/`_electron` | — | — | — | docs/src/mobile-api, docs/src/electron-api @v1.64.0 |
| Binding-only extras | `await using` | JSpecify nullability (1.63) | Xunit (1.50), Xunit.v3 / MSTest.v4 (1.55), `Expect(..., message)` (1.60) | async pytest fixtures (1.50), FormData / timedelta / async CMs (1.60) | RN-*/GH-* as cited |

---

## Unverified / caveats (collected)
- Java, .NET and Python 1.64 release contents and dates: **UNVERIFIED** (not published). Their API surface is inferred from the v1.64.0 API docs `langs` metadata and the binding `main` branches.
- That the 1.64 `screen`-from-device-descriptors break is Node test-runner only: **UNVERIFIED** (inferred from the new `TestOptions.screen`).
- `page.perform` / `--run-agents`: present only as a CLI flag at v1.64.0; the API is not public. **UNVERIFIED**.
- The exact version URLPattern support was introduced: docs evidence only (first seen in `params.md@v1.59.0`).
- Whether pre-1.64 `parent.locator(childWithNth)` resolved `nth` per parent: **UNVERIFIED**.
- Node `>=20` (1.62) and Python `>=3.10` (1.61) come from package metadata; neither appears in the release notes.
- 1.64.1 contents: 3 cherry-picks pending on `release-1.64`; **UNVERIFIED** until tagged.
