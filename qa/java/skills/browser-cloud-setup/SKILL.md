---
name: qa-browser-cloud-setup-java
description: Use when the user needs to run Java Playwright (web) or Appium java-client (mobile) tests on a **hosted cloud grid**. Triggers: "run our Playwright Java tests on BrowserStack", "wire Appium java-client to Sauce Labs", "set up LambdaTest caps for our TestNG Appium tests". Not for real-device app upload and device matrices (`qa-device-cloud-java`) or writing the tests (`qa-ui-test-writer-playwright-java`).
---

# QA — Cloud Grid Config (Java: Playwright + Appium java-client)

Wires Java tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web tests and Appium java-client mobile tests that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/java/skills/ui-test-author/{playwright,appium}` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or tests.

> **Why this skill exists.** A local Playwright/Appium suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the driver/browser is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those five things right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- Java 21, Gradle (Kotlin DSL)
- **Web**: `com.microsoft.playwright:playwright` at the pin in the **Versions** table of `qa/java/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing). A grid class extends J1's `BaseTest` and overrides its `newBrowser(playwright)` hook to `chromium().connect(wsEndpoint)` (`references/lifecycle.md` §3 of that skill); context per test, failure evidence and `BASE_URL` are unchanged
- **Mobile**: `io.appium:java-client` 9.x (`UiAutomator2Options` / `XCUITestOptions`, `AndroidDriver`/`IOSDriver`) pointed at the vendor's remote hub
- TestNG as the runner with `parallel="classes"`: one class = one browser = one grid session, so the suite's `thread-count` is the number of concurrent sessions, set from `GRID_CONCURRENCY`. Data providers stay sequential
- Tunnels: `com.browserstack:browserstack-local-java` (`Local` class), Sauce Connect 5 (`sc` binary), LambdaTest Tunnel (`LT` binary)
- Grid config under `src/test/java/.../support/grid/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY`, `LT_USERNAME` / `LT_ACCESS_KEY`)
- These suites run in CI under `qa/cicd/java/skills/ci-pipelines` — secrets injected via the runner's secret store / OIDC, sharding driven by the runner (see § Parallelism)

## When to use

- Running existing Playwright Java web tests on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing Appium java-client mobile tests on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`) for a Java stack
- Capping concurrent sessions to the plan and mapping that onto TestNG `thread-count`
- Surfacing the **session dashboard URL** + video/logs on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The TypeScript / .NET grid stacks → `qa/{typescript,dotnet}/skills/browser-cloud-setup`
- Writing the page objects / tests → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix, sharding props, artifact upload) → `qa/cicd/java/skills/ci-pipelines/*` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/java/skills/device-cloud`; this node covers the wiring, that one the farm specifics

## Pick a vendor — quick orientation

| Vendor | Web (Playwright Java) connect | Mobile (Appium) hub | Vendor cap block | Tunnel binary |
|---|---|---|---|---|
| **BrowserStack** | `wss://cdp.browserstack.com/playwright` (flat caps) | `hub-cloud.browserstack.com/wd/hub` | `bstack:options` (W3C, Appium); **flat `browserstack.*` for Playwright direct-connect** | `browserstack-local-java` (`Local`) |
| **Sauce Labs** | **`saucectl` only** (no public ad-hoc `connect`) | `ondemand.<region>.saucelabs.com/wd/hub` | `sauce:options` | Sauce Connect 5 (`sc run`) |
| **LambdaTest** | `wss://cdp.lambdatest.com/playwright` | `mobile-hub.lambdatest.com/wd/hub` | `LT:Options` | LambdaTest Tunnel (`LT`) |
| **AWS Device Farm** | signed TestGrid Selenium URL (not a Playwright ws endpoint) | managed run (project ARN + device-pool ARN) or `remoteDriverEndpoint` | none — ARN/upload model | VPC/endpoint config, not a CLI tunnel |

**Decision rule.** *Mostly web on a broad browser/OS matrix? Any of BrowserStack / Sauce / LambdaTest — pick on price/plan.* *Real-device mobile depth or app-management?* BrowserStack and Sauce are strongest; LambdaTest is the cheapest broad option. *Already deep in AWS and need private-VPC devices?* Device Farm — but it's an **ARN/upload paradigm, not a caps-on-a-hub grid**, so the wiring differs most there (see § AWS Device Farm). Don't over-engineer multi-vendor abstraction; wire one vendor cleanly behind the grid helper and add a second only when a real need appears.

> **The one gotcha that bites everyone (Playwright + BrowserStack).** BrowserStack's Playwright **direct-connect still uses LEGACY FLAT caps** (`browser`, `os`, `os_version`, `browserstack.username`, `browserstack.accessKey`, …) — **not** the W3C `bstack:options` nesting used by Appium. The nested block is for Appium and the SDK. Don't mix them. Sauce has **no public Playwright `connect` endpoint at all** — it's `saucectl`-driven, the biggest cross-vendor divergence.

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Web or mobile** — Playwright web, or Appium mobile? This decides the connection idiom entirely.
2. **Which vendor** — BrowserStack / Sauce / LambdaTest / Device Farm? (And, for Sauce/Device Farm, **which region**, since there is no implicit default.)
3. **Private target?** — does the grid need to reach a staging/localhost URL (→ tunnel), and what's the **concurrent-session cap** on the plan (→ TestNG `thread-count`)?

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Patterns** — secrets, the BrowserStack connect (`BrowserStackGrid`), one session per class (`GridSession`), the grid class, Sauce, Appium, capability blocks, parallelism (`testng-grid.xml` + `GridConcurrency`), session status, tunnels, Device Farm.

## The web grid in one picture

```java
public class LoginOnEdgeTest extends LoginTest {
    private GridSession session;

    @Override
    protected Browser newBrowser(Playwright playwright) {
        session = BrowserStackGrid.connect(playwright, GridTarget.EDGE_WINDOWS_11, getClass().getSimpleName());
        return session.browser();
    }

    @AfterClass(alwaysRun = true)
    public void markSession(ITestContext run) {
        session.markOutcome(run, this);
    }
}
```

The class reruns `LoginTest`'s tests on Edge in one BrowserStack session, marks that session's verdict once
from the failures TestNG recorded for it, and attaches the dashboard link; `testng-grid.xml` runs the grid
package through `./gradlew gridTest`. There is no second base class: the grid target is an override on the class
that needs it.

## Rules

### Connection
- **Web**: connect, don't launch. Playwright Java → override `BaseTest.newBrowser(playwright)` to BrowserStack `chromium().connect(wsEndpoint)` with **flat caps**; Sauce → `saucectl`; LambdaTest → its connect endpoint with `LT:Options`. Never a private `Playwright.create()` or a grid base class beside `BaseTest`.
- **Mobile**: build `UiAutomator2Options`/`XCUITestOptions`, attach the vendor block via `setCapability`, point `new AndroidDriver(new URL(hubUrl), options)` at the hub; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting — they apply to different connection paths.
- `client.playwrightVersion` is the **installed** client version, read from the Playwright jar's Maven metadata (`BrowserStackGrid.installedPlaywrightVersion()`) — never a typed `"1.x"` or a literal that drifts from the build. A version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`). Vendors renamed them off JSON-Wire.
- Always set `buildName`/`build`, `sessionName`/`name`, and a project tag so runs are findable on the dashboard.
- App under test is referenced by the vendor's uploaded id (`bs://…`), **never a local file path** in the cap.

### Parallelism
- `parallel="classes"`, never `parallel="methods"` or `@DataProvider(parallel = true)`: Playwright Java is not thread-safe, and two methods of one class would share one `page` (`lifecycle.md` §1).
- Read the concurrent-session cap from **one env var** (`GRID_CONCURRENCY`) and set it as the grid suite's `thread-count` with an `IAlterSuiteListener` declared in `testng-grid.xml` — a suite file's `thread-count` overrides Gradle's `threadCount`. Never hard-code silently.
- `total CI shards × thread-count ≤ plan session cap`. Sharding mechanics live in `qa/cicd/java/skills/ci-pipelines/*` — cross-link, don't duplicate.

### Secrets
- Username + access key via **env vars only** (`required(...)` helper). Never a literal, never in a committed config file.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- Surface the **session dashboard URL** in Allure (`Allure.attachment("BrowserStack session", url)`, allure-java 3.0) — a failed grid run should be one click from the replay. The local failure evidence (trace, video, screenshot) still comes from `BaseTest`.
- **Mark the session pass/fail once per session** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`). A Playwright class is one session, so it marks in `@AfterClass` from the failures recorded for that instance; marking in `@AfterMethod` lets the last test overwrite the verdict. The dashboard must reflect reality.

### Tunnels
- Start the tunnel **before** the suite (`@BeforeSuite`), stop it in `@AfterSuite`; tie sessions via `local`+`localIdentifier` / `tunnelName`.
- Tunnel key from env, never a literal. One tunnel identifier per run so parallel runs don't collide.

### Waits
- **No `Thread.sleep`** anywhere — grid latency is higher than local, which makes fixed sleeps both flakier and slower. Use Playwright auto-wait / `WebDriverWait` / explicit conditions, exactly as the local suite does.

### What NOT to do
- No launching a local browser when the intent is a grid run — connect to the grid.
- No `bstack:options` on a BrowserStack Playwright **direct-connect** — it's flat caps there.
- No hard-coded session/thread count — read the plan cap from env and map it.
- No credential literals in code or committed config — env vars only.
- No grid run that doesn't **report status** to the vendor and **surface the session URL** on failure.
- No tunnel without a stop in teardown, and no tunnel key as a literal.
- No `Thread.sleep` to paper over grid latency.

## Generation steps

1. Confirm **web vs mobile**, **vendor** (+ region for Sauce/Device Farm), **private target?** (tunnel), and the **session cap**.
2. Add `support/grid/GridCredentials.java` with the `required(...)` env reads — no literals.
3. **Web**: add `GridTarget`, `BrowserStackGrid` (flat-cap `connect`, the installed client version) and `GridSession`; then one grid class per target per test class, extending that test class and overriding `newBrowser(playwright)` (J1's `BaseTest` hook); or scaffold `.sauce/config.yml` (Sauce) / the LambdaTest connect. **Mobile**: add `AppiumGridDriverFactory` — `UiAutomator2Options` + `setCapability("bstack:options", map)` + `new AndroidDriver(new URL(hubUrl), options)`.
4. Add `testng-grid.xml` (`parallel="classes"`, the grid package) with the `GridConcurrency` listener, and the `gridTest` Gradle task; note the `shards × GRID_CONCURRENCY ≤ cap` rule and cross-link `qa/cicd/java/skills/ci-pipelines/*`.
5. Mark each session once and attach its dashboard URL — `GridSession.markOutcome` in the grid class's `@AfterClass` (web), `SessionStatus.mark…` in the driver teardown (mobile).
6. If the target is private, add the tunnel lifecycle (`GridTunnel` in a `@BeforeSuite`/`@AfterSuite` class listed in `testng-grid.xml`) and tie sessions via the cap.
7. Run a single test against the grid first (one thread) to confirm the connection + caps before fanning out. Confirm the session appears on the dashboard with the right build/project tags. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- **`qa/typescript/skills/browser-cloud-setup`** + **`qa/dotnet/skills/browser-cloud-setup`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`chromium.connect`/`@wdio/*-service`; Playwright .NET `ConnectAsync`/`AppiumOptions`). Structure ported, not code.
- **`qa/java/skills/ui-test-author/playwright`** — writes the web tests/page objects this skill runs on a grid, and owns `BaseTest`, whose `newBrowser(playwright)` hook a grid class overrides.
- **`qa/java/skills/ui-test-author/appium`** — writes the mobile tests/page objects; this skill swaps the local Appium session for a grid one (same driver-factory discipline).
- **`qa/cicd/java/skills/ci-pipelines`** — sharding/`-PshardIndex` + OIDC secret injection; this skill maps the plan cap onto those shards (don't duplicate the mechanics).
- **`qa/java/skills/device-cloud`** — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/java/skills/network-mocking`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).
