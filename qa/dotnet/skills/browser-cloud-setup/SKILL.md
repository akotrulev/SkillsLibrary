---
name: qa-browser-cloud-setup-dotnet
description: Use when the user needs to run .NET Playwright (web) or Appium.WebDriver (mobile) tests on a **hosted cloud grid**. Triggers: "run our Playwright .NET tests on BrowserStack", "wire Appium .NET to Sauce Labs", "set up LambdaTest caps for our NUnit Appium tests". Not for real-device app upload and device matrices (`device-cloud`) or local runs (`ui-project-setup`).
---

# QA — Cloud Grid Config (.NET: Playwright + Appium.WebDriver)

Wires .NET tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web tests and Appium.WebDriver mobile tests that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/dotnet/skills/ui-test-author/{playwright,appium}/dotnet` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or tests.

> **Why this skill exists.** A local Playwright/Appium suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the driver/browser is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those five things right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- .NET 8, C# (nullable reference types enabled)
- **Web**: `Microsoft.Playwright` connected to a cloud grid via `BrowserType.ConnectAsync(wsEndpoint)`
- **Mobile**: `Appium.WebDriver` 8.x (`AppiumOptions`, `AndroidDriver`/`IOSDriver`) pointed at the vendor's remote hub
- NUnit as the runner; parallelism via `[Parallelizable]` + `LevelOfParallelism`
- Tunnels: `BrowserStackLocal` (NuGet `BrowserStack.Local` `Local` class), Sauce Connect 5 (`sc` binary), LambdaTest Tunnel (`LT` binary)
- Grid config under `Tests/Support/Grid/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY`, `LT_USERNAME` / `LT_ACCESS_KEY`)
- These suites run in CI under `qa/cicd/dotnet/skills/ci-pipelines` — secrets injected via the runner's secret store / OIDC, sharding driven by the runner (see § Parallelism)

## When to use

- Running existing Playwright .NET web tests on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing Appium.WebDriver mobile tests on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`) for a .NET stack
- Capping concurrent sessions to the plan and mapping that onto NUnit parallelism
- Surfacing the **session dashboard URL** + video/logs on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The TypeScript / Java grid stacks → `qa/{typescript,java}/skills/browser-cloud-setup`
- Writing the page objects / tests → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix, `--shard`, artifact upload) → `qa/cicd/dotnet/skills/ci-pipelines/*` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/dotnet/skills/device-cloud`; this node covers the wiring, that one the farm specifics

## Pick a vendor — quick orientation

| Vendor | Web (Playwright .NET) connect | Mobile (Appium) hub | Vendor cap block | Tunnel binary |
|---|---|---|---|---|
| **BrowserStack** | `wss://cdp.browserstack.com/playwright` (flat caps) | `hub-cloud.browserstack.com/wd/hub` | `bstack:options` (W3C, Appium); **flat `browserstack.*` for Playwright direct-connect** | `BrowserStack.Local` (`Local`) |
| **Sauce Labs** | **`saucectl` only** (no public ad-hoc `ConnectAsync`) | `ondemand.<region>.saucelabs.com/wd/hub` | `sauce:options` | Sauce Connect 5 (`sc run`) |
| **LambdaTest** | `wss://cdp.lambdatest.com/playwright` | `mobile-hub.lambdatest.com/wd/hub` | `LT:Options` | LambdaTest Tunnel (`LT`) |
| **AWS Device Farm** | signed TestGrid Selenium URL (not a Playwright ws endpoint) | managed run (project ARN + device-pool ARN) or `remoteDriverEndpoint` | none — ARN/upload model | VPC/endpoint config, not a CLI tunnel |

**Decision rule.** *Mostly web on a broad browser/OS matrix? Any of BrowserStack / Sauce / LambdaTest — pick on price/plan.* *Real-device mobile depth or app-management?* BrowserStack and Sauce are strongest; LambdaTest is the cheapest broad option. *Already deep in AWS and need private-VPC devices?* Device Farm — but it's an **ARN/upload paradigm, not a caps-on-a-hub grid**, so the wiring differs most there (see § AWS Device Farm). Don't over-engineer multi-vendor abstraction; wire one vendor cleanly behind the grid helper and add a second only when a real need appears.

> **The one gotcha that bites everyone (Playwright + BrowserStack).** BrowserStack's Playwright **direct-connect still uses LEGACY FLAT caps** (`browser`, `os`, `os_version`, `browserstack.username`, `browserstack.accessKey`, …) — **not** the W3C `bstack:options` nesting used by Appium. The nested block is for Appium and the SDK. Don't mix them. Sauce has **no public Playwright `ConnectAsync` endpoint at all** — it's `saucectl`-driven, the biggest cross-vendor divergence.

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Web or mobile** — Playwright web, or Appium mobile? This decides the connection idiom entirely.
2. **Which vendor** — BrowserStack / Sauce / LambdaTest / Device Farm? (And, for Sauce/Device Farm, **which region**, since there is no implicit default.)
3. **Private target?** — does the grid need to reach a staging/localhost URL (→ tunnel), and what's the **concurrent-session cap** on the plan (→ NUnit `LevelOfParallelism`)?

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Patterns**.

## Rules

### Connection
- **Web**: connect, don't launch. Playwright .NET → BrowserStack `Chromium.ConnectAsync(wsEndpoint)` with **flat caps**; Sauce → `saucectl`; LambdaTest → its connect endpoint with `LT:Options`.
- **Mobile**: build `AppiumOptions`, attach the vendor block via `AddAdditionalAppiumOption`, point `new AndroidDriver(new Uri(hubUrl), options)` at the hub; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting — they apply to different connection paths.
- Pin the Playwright/Appium version cap to your installed version; a version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`). Vendors renamed them off JSON-Wire.
- Always set `buildName`/`build`, `sessionName`/`name`, and a project tag so runs are findable on the dashboard.
- App under test is referenced by the vendor's uploaded id (`bs://…`), **never a local file path** in the cap.

### Parallelism
- Read the concurrent-session cap from **one env var** (`GRID_CONCURRENCY`) and map it onto `LevelOfParallelism`. Never hard-code silently.
- `total CI shards × LevelOfParallelism ≤ plan session cap`. Sharding mechanics live in `qa/cicd/dotnet/skills/ci-pipelines/*` — cross-link, don't duplicate.

### Secrets
- Username + access key via **env vars only** (`Required(...)` helper). Never a literal, never in a committed config file.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- Surface the **session dashboard URL** in output / Allure on failure — a failed grid run should be one click from the replay.
- **Mark the session pass/fail** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`) in `[TearDown]`. The dashboard must reflect reality.

### Tunnels
- Start the tunnel **before** the suite (`[OneTimeSetUp]` in a `SetUpFixture`), stop it in teardown; tie sessions via `local`+`localIdentifier` / `tunnelName`.
- Tunnel key from env, never a literal. One tunnel identifier per run so parallel runs don't collide.

### Waits
- **No `Thread.Sleep`** anywhere — grid latency is higher than local, which makes fixed sleeps both flakier and slower. Use Playwright auto-wait / `WebDriverWait` / explicit conditions, exactly as the local suite does.

### What NOT to do
- No launching a local browser when the intent is a grid run — connect to the grid.
- No `bstack:options` on a BrowserStack Playwright **direct-connect** — it's flat caps there.
- No hard-coded session/parallelism count — read the plan cap from env and map it.
- No credential literals in code or committed config — env vars only.
- No grid run that doesn't **report status** to the vendor and **surface the session URL** on failure.
- No tunnel without a stop in teardown, and no tunnel key as a literal.
- No `Thread.Sleep` to paper over grid latency.

## Generation steps

1. Confirm **web vs mobile**, **vendor** (+ region for Sauce/Device Farm), **private target?** (tunnel), and the **session cap**.
2. Add `Tests/Support/Grid/GridCredentials.cs` with the `Required(...)` env reads — no literals.
3. **Web**: add `PlaywrightGridConnector` (BrowserStack flat-cap `ConnectAsync`) + a `GridWebTestBase` that yields an `IPage` and marks status in `[TearDown]`; or scaffold `.sauce/config.yml` (Sauce) / the LambdaTest connect. **Mobile**: add `AppiumGridDriverFactory` — `AppiumOptions` + `AddAdditionalAppiumOption("bstack:options", …)` + `new AndroidDriver(new Uri(hubUrl), options)`.
4. Map the session cap onto `LevelOfParallelism` from `GRID_CONCURRENCY`; note the `shards × parallelism ≤ cap` rule and cross-link `qa/cicd/dotnet/skills/ci-pipelines/*`.
5. Wire artifacts (`Artifacts.AttachSessionUrl`) + session status (`SessionStatus.Mark…`) into `[TearDown]`.
6. If the target is private, add the tunnel lifecycle (`GridTunnel` in a `SetUpFixture`) and tie sessions via the cap.
7. Run a single test against the grid first (one worker) to confirm the connection + caps before fanning out. Confirm the session appears on the dashboard with the right build/project tags.

## Cross-references

- **`qa/typescript/skills/browser-cloud-setup`** + **`qa/java/skills/browser-cloud-setup`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`chromium.connect`/`@wdio/*-service`; Playwright Java `connect`/`UiAutomator2Options`). Structure ported, not code.
- **`qa/dotnet/skills/ui-test-author/playwright`** — writes the web tests/page objects this skill runs on a grid (connection patterns to extend).
- **`qa/dotnet/skills/ui-test-author/appium`** — writes the mobile tests/page objects; this skill swaps the local Appium session for a grid one (same `AppiumDriverFactory` discipline).
- **`qa/cicd/dotnet/skills/ci-pipelines`** — sharding/`--where`-modulo + OIDC secret injection; this skill maps the plan cap onto those shards (don't duplicate the mechanics).
- **`qa/dotnet/skills/device-cloud`** — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/dotnet/skills/network-mocking`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).
