---
name: qa-browser-cloud-setup-dotnet
description: Use when the user needs to run .NET Playwright (web) or Appium.WebDriver (mobile) tests on a **hosted cloud grid**. Triggers: "run our Playwright .NET tests on BrowserStack", "wire Appium .NET to Sauce Labs", "set up LambdaTest caps for our NUnit Appium tests". Not for real-device app upload and device matrices (`device-cloud`) or local runs (`ui-project-setup`).
---

# QA — Cloud Grid Config (.NET 10: Playwright + Appium.WebDriver)

Wires .NET tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web tests and Appium.WebDriver mobile tests that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/dotnet/skills/ui-test-author/{playwright,appium}` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or tests.

> **Why this skill exists.** A local suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the browser/driver is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- .NET 10 (8/9 supported — match the project's TFM), C# with nullable enabled, NUnit 4
- **Web**: Microsoft.Playwright.NUnit at the pins in the **Versions** table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing). A grid fixture derives from a test class built on that skill's `BaseTest` and overrides **`BrowserTest.ConnectOptionsAsync()`** — `BrowserTest` then connects instead of launching
- **Mobile**: Appium.WebDriver at the pin in `qa/dotnet/skills/ui-test-author/appium` (`AppiumOptions`, `AndroidDriver`/`IOSDriver`) pointed at the vendor's remote hub
- Tunnels: `BrowserStackLocal` (NuGet `BrowserStack.Local`, class `Local`), Sauce Connect 5 (`sc`), LambdaTest Tunnel (`LT`)
- Grid code under `Support/Grid/`, grid fixtures in their own namespace (`Example.UiTests.Grid`); credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY` / `SAUCE_REGION`, `LT_USERNAME` / `LT_ACCESS_KEY`, `BUILD_NAME`)
- These suites run in CI under `qa/cicd/dotnet/skills/ci-pipelines` — secrets via the runner's secret store / OIDC

## When to use

- Running existing Playwright .NET web tests on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing Appium.WebDriver mobile tests on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`)
- Capping concurrent sessions to the plan and mapping that onto NUnit's worker count
- Surfacing the **session dashboard URL** on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The TypeScript / Java grid stacks → `qa/{typescript,java}/skills/browser-cloud-setup`
- Writing the page objects / tests → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/appium`
- CI shard/worker mechanics (class filters, artifact upload) → `qa/cicd/dotnet/skills/ci-pipelines` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/dotnet/skills/device-cloud`

## Pick a vendor — quick orientation

| Vendor | Web (Playwright .NET) connect | Mobile (Appium) hub | Vendor cap block | Tunnel binary |
|---|---|---|---|---|
| **BrowserStack** | `wss://cdp.browserstack.com/playwright` (flat caps) | `hub-cloud.browserstack.com/wd/hub` | `bstack:options` (W3C, Appium); **flat `browserstack.*` for Playwright direct-connect** | `BrowserStack.Local` (`Local`) |
| **Sauce Labs** | **`saucectl` only** (no public ad-hoc connect endpoint) | `ondemand.<region>.saucelabs.com/wd/hub` | `sauce:options` | Sauce Connect 5 (`sc run`) |
| **LambdaTest** | `wss://cdp.lambdatest.com/playwright` | `mobile-hub.lambdatest.com/wd/hub` | `LT:Options` | LambdaTest Tunnel (`LT`) |
| **AWS Device Farm** | signed TestGrid Selenium URL (not a Playwright ws endpoint) | managed run (project ARN + device-pool ARN) or `remoteDriverEndpoint` | none — ARN/upload model | VPC/endpoint config, not a CLI tunnel |

**Decision rule.** *Mostly web on a broad browser/OS matrix?* Any of BrowserStack / Sauce / LambdaTest — pick on price/plan. *Real-device mobile depth?* BrowserStack and Sauce are strongest; LambdaTest is the cheapest broad option. *Deep in AWS and need private-VPC devices?* Device Farm — an **ARN/upload paradigm, not caps on a hub**. Wire one vendor cleanly behind the grid helper; add a second only when a real need appears.

> **The gotcha that bites everyone (Playwright + BrowserStack).** BrowserStack's Playwright **direct-connect uses LEGACY FLAT caps** (`browser`, `os`, `os_version`, `browserstack.username`, `browserstack.accessKey`, …) — **not** the W3C `bstack:options` nesting Appium uses. Don't mix them. Sauce has **no public Playwright connect endpoint** — it's `saucectl`-driven.

## How a Playwright .NET suite reaches a grid

`BrowserTest` (under `PageTest` and `BaseTest`) registers the browser as a **per-worker service**: the first
fixture on an NUnit worker creates it — launched from the runsettings, or **connected** when the fixture's
`ConnectOptionsAsync()` returns `(wsEndpoint, options)` — and every later fixture on that worker reuses it,
whatever its own override says. Three consequences shape the wiring:

1. **A grid run is its own `dotnet test` run.** Grid fixtures carry `[Category("grid")]`; the grid run is
   `--filter TestCategory=grid`, and the local/PR run filters `TestCategory!=grid`. Mixing local and grid
   fixtures in one run lets whichever fixture a worker meets first decide the browser for all of them.
2. **One vendor session per worker.** The session spans the worker's tests, so the plan's session cap is the
   worker count: `-- NUnit.NumberOfTestWorkers=$GRID_CONCURRENCY`.
3. **A failed test ends its session.** After a failure the worker disposes its browser and the next test
   connects afresh. So marking each test's verdict on the session leaves the right final verdict: a session's
   only failure, if it has one, is its last test.

A `LaunchOptionsAsync()` override is unreliable for the same per-worker reason (`ui-test-author/playwright`,
`lifecycle.md` §4).

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Web or mobile** — Playwright web, or Appium mobile? This decides the connection idiom entirely.
2. **Which vendor** — BrowserStack / Sauce / LambdaTest / Device Farm? (For Sauce/Device Farm, **which region** — there is no implicit default.)
3. **Private target?** — does the grid need to reach a staging/localhost URL (→ tunnel), and what's the **concurrent-session cap** on the plan (→ the worker count)?

---

## Deep-dive reference

[`references/details.md`](references/details.md) holds the code — **secrets**, **web on BrowserStack**
(`GridConnection`, a grid fixture, `GridSession`), **Sauce `saucectl`**, **mobile on a grid**, the **capability
blocks**, **parallelism**, the **tunnel**, and **AWS Device Farm**. Read it when the task touches them.

## Rules

### Connection
- **Web**: connect, don't launch. A grid fixture **derives from the test class it reruns** and overrides `ConnectOptionsAsync()` → BrowserStack's flat-caps endpoint or LambdaTest's `LT:Options` endpoint. Sauce → `saucectl`. The test classes, page objects and `BaseTest` do not change.
- **Never `Playwright.CreateAsync()` in a `[SetUp]`** and never a second base class for the grid: `BrowserTest` owns the connection, `BaseTest` still owns `BASE_URL`, tracing and failure evidence.
- **Mobile**: build `AppiumOptions`, attach the vendor block via `AddAdditionalAppiumOption`, point `new AndroidDriver(new Uri(hubUrl), options)` at the hub; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting.
- Send the **installed** client version (`client.playwrightVersion` read from the loaded `Microsoft.Playwright` assembly); a version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`).
- Always set the build, a session name and a project tag so runs are findable on the dashboard; the build comes from `BUILD_NAME`, required, never defaulted.
- App under test is referenced by the vendor's uploaded id (`bs://…`), **never a local file path** in the cap.

### Parallelism
- The plan's concurrent-session cap is **one env var** (`GRID_CONCURRENCY`), passed as `NUnit.NumberOfTestWorkers`. Never hard-coded, never an assembly `LevelOfParallelism` attribute that cannot read it.
- `total CI shards × workers ≤ plan session cap`. Sharding mechanics live in `qa/cicd/dotnet/skills/ci-pipelines` — cross-link, don't duplicate.
- Fixtures stay `ParallelScope.Self` (from `BaseTest`); never `ParallelScope.All`/`Fixtures` to "use more sessions".

### Secrets
- Username + access key via **env vars only** (`GridCredentials`). Never a literal, never in a committed config file.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- **Mark the session verdict** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`) in the grid fixture's `[TearDown]`, which runs before `BaseTest` closes the context.
- On failure, **attach the session dashboard URL** (`AllureApi.AddLink` + the test output) — a failed grid run is one click from the vendor's replay. `BaseTest`'s own trace, screenshot and video still land in `playwright-artifacts/`.

### Tunnels
- Start the tunnel **before** the grid fixtures: a `[SetUpFixture]` in the grid fixtures' namespace (`Example.UiTests.Grid`), which NUnit runs only for that namespace — the local run never starts it. Stop it in `[OneTimeTearDown]`; tie sessions via `local` + `localIdentifier` / `tunnelName`.
- Tunnel key from env, never a literal. One tunnel identifier per run (`BUILD_NAME`) so parallel runs don't collide.

### Waits
- **No `Thread.Sleep`/`Task.Delay`** anywhere — grid latency makes fixed sleeps both flakier and slower. Playwright auto-wait / `WebDriverWait`, exactly as the local suite does.

### What NOT to do
- No launching a local browser when the intent is a grid run — and no grid fixture in the local run.
- No `bstack:options` on a BrowserStack Playwright **direct-connect** — it's flat caps there.
- No hard-coded session/parallelism count; no credential literals; no `BUILD_NAME` default.
- No grid run that doesn't **report status** to the vendor and **surface the session URL** on failure.
- No tunnel without a stop in teardown, and no tunnel key as a literal.

## Generation steps

1. Confirm **web vs mobile**, **vendor** (+ region for Sauce/Device Farm), **private target?** (tunnel), and the **session cap**.
2. Add `Support/Grid/GridCredentials.cs` — required env reads, no literals.
3. **Web**: add `Support/Grid/GridConnection.cs` (the vendor endpoint as `ConnectOptionsAsync()`'s tuple) and `Support/Grid/GridSession.cs` (verdict + session link). For each test class to rerun, add `Grid/<Class>OnBrowserStack.cs`: `[Category("grid")]`, derives from the test class, overrides `ConnectOptionsAsync()`, reports in `[TearDown]`. Sauce: scaffold `.sauce/config.yml`. **Mobile**: add `AppiumGridDriverFactory`.
4. Wire the run: `dotnet test --filter TestCategory=grid -- NUnit.NumberOfTestWorkers=$GRID_CONCURRENCY`, and `TestCategory!=grid` on the local/PR run; note `shards × workers ≤ cap` and cross-link `qa/cicd/dotnet/skills/ci-pipelines`.
5. If the target is private, add `GridTunnel` and its `[SetUpFixture]` in `Example.UiTests.Grid`.
6. Run a single grid fixture first (`NUnit.NumberOfTestWorkers=1`) to confirm the connection + caps before fanning out; confirm the session appears on the dashboard with the right build/project tags. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- **`qa/typescript/skills/browser-cloud-setup`** + **`qa/java/skills/browser-cloud-setup`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`use.connectOptions` / a worker-scoped `browser`; Java's `BaseTest.newBrowser` override). Structure ported, not code.
- **`qa/dotnet/skills/ui-test-author/playwright`** — `BaseTest`, the per-worker browser (`references/lifecycle.md` §2–§4) and the test classes a grid fixture reruns.
- **`qa/dotnet/skills/ui-test-author/appium`** — writes the mobile tests/page objects; this skill swaps the local Appium session for a grid one.
- **`qa/cicd/dotnet/skills/ci-pipelines`** — class-filter sharding + OIDC secret injection; this skill maps the plan cap onto those shards.
- **`qa/dotnet/skills/device-cloud`** — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/dotnet/skills/network-mocking`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).
