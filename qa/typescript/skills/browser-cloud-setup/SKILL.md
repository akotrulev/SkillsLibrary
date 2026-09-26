---
name: qa-browser-cloud-setup-typescript
description: Use when the user needs to run TypeScript Playwright (web) or WebdriverIO/Appium (mobile) tests on a **hosted cloud grid**. Triggers: "run our Playwright tests on BrowserStack", "wire WebdriverIO to Sauce Labs", "set up LambdaTest caps for our Appium TS tests". Not for real-device app upload and device matrices (`qa-device-cloud-typescript`) or writing the tests (`qa-ui-test-writer-playwright-typescript`).
---

# QA — Cloud Grid Config (TypeScript: Playwright + WebdriverIO/Appium)

Wires TypeScript tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web specs and WebdriverIO/Appium mobile specs that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/typescript/skills/ui-test-author/{playwright,appium}` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or specs.

> **Why this skill exists.** A local Playwright/Appium suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the driver/browser is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those five things right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- Node 24 + TypeScript (strict mode)
- **Web**: `@playwright/test` connected to a cloud grid via `chromium.connect({ wsEndpoint })`, the `browserstack-node-sdk` wrapper, or `saucectl`
- **Mobile**: WebdriverIO 9.x + Appium 2.x with `@wdio/browserstack-service` / `@wdio/sauce-service` (or raw `bstack:options`/`sauce:options`/`LT:Options` caps)
- Tunnels: `browserstack-local` (npm), Sauce Connect 5 (`sc` binary), LambdaTest Tunnel (`LT` binary)
- Grid config under `tests/support/grid/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY`, `LT_USERNAME` / `LT_ACCESS_KEY`)
- These suites run in CI under `qa/cicd/typescript/skills/ci-pipelines` — secrets injected via the runner's secret store / OIDC, sharding driven by the runner (see § Parallelism)

## When to use

- Running existing Playwright web specs on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing WebdriverIO/Appium mobile specs on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`) for a TS stack
- Capping concurrent sessions to the plan and mapping that onto Playwright `workers` / WDIO `maxInstances`
- Surfacing the **session dashboard URL** + video/logs on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The .NET / Java grid stacks → `qa/{dotnet,java}/skills/browser-cloud-setup`
- Writing the page objects / specs → `qa/typescript/skills/ui-test-author/playwright`, `qa/typescript/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix, `--shard`, artifact upload) → `qa/cicd/typescript/skills/ci-pipelines/*` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/typescript/skills/device-cloud`; this node covers the wiring, that one the farm specifics

## Pick a vendor — quick orientation

| Vendor | Web (Playwright) connect | Mobile (Appium) hub | Vendor cap block | Tunnel binary |
|---|---|---|---|---|
| **BrowserStack** | `wss://cdp.browserstack.com/playwright` (flat caps) **or** `browserstack-node-sdk` | `hub-cloud.browserstack.com/wd/hub` | `bstack:options` (W3C, Selenium/Appium); **flat `browserstack.*` for Playwright direct-connect** | `browserstack-local` (npm `Local`) |
| **Sauce Labs** | **`saucectl` only** (no public ad-hoc `connect`) | `ondemand.<region>.saucelabs.com/wd/hub` | `sauce:options` | Sauce Connect 5 (`sc run`) |
| **LambdaTest** | `wss://cdp.lambdatest.com/playwright` (SDK `lambdatest-setup`) | `mobile-hub.lambdatest.com/wd/hub` | `LT:Options` | LambdaTest Tunnel (`LT`) |
| **AWS Device Farm** | signed TestGrid Selenium URL (not a Playwright ws endpoint) | managed run (project ARN + device-pool ARN) or `remoteDriverEndpoint` | none — ARN/upload model | VPC/endpoint config, not a CLI tunnel |

**Decision rule.** *Mostly web on a broad browser/OS matrix? Any of BrowserStack / Sauce / LambdaTest — pick on price/plan.* *Real-device mobile depth or app-management?* BrowserStack and Sauce are strongest; LambdaTest is the cheapest broad option. *Already deep in AWS and need private-VPC devices?* Device Farm — but it's an **ARN/upload paradigm, not a caps-on-a-hub grid**, so the wiring differs most there (see § AWS Device Farm). Don't over-engineer multi-vendor abstraction; wire one vendor cleanly behind the `gridCaps` helper and add a second only when a real need appears.

> **The one gotcha that bites everyone (Playwright + BrowserStack).** BrowserStack's Playwright **direct-connect still uses LEGACY FLAT caps** (`browser`, `os`, `os_version`, `browserstack.username`, `browserstack.accessKey`, …) — **not** the W3C `bstack:options` nesting used by Selenium/Appium. The nested block is for the `browserstack.yml` SDK and for Appium. Don't mix them. Sauce has **no public Playwright `connect` endpoint at all** — it's `saucectl`-driven, the biggest cross-vendor divergence.

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Web or mobile** — Playwright web, or WebdriverIO/Appium mobile? This decides the connection idiom entirely.
2. **Which vendor** — BrowserStack / Sauce / LambdaTest / Device Farm? (And, for Sauce/Device Farm, **which region**, since there is no implicit default.)
3. **Private target?** — does the grid need to reach a staging/localhost URL (→ tunnel), and what's the **concurrent-session cap** on the plan (→ `workers` / `maxInstances`)?

---

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Patterns**.

## Rules

### Connection
- **Web**: connect, don't launch. Playwright → BrowserStack `chromium.connect({ wsEndpoint })` with **flat caps**; Sauce → `saucectl`; LambdaTest → its connect endpoint with `LT:Options`.
- **Mobile**: set `user`/`key`/`hostname` + the vendor service in `wdio.conf.ts`; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting — they apply to different connection paths.
- Pin the Playwright/Appium version cap to your installed version; a version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`). Vendors renamed them off JSON-Wire.
- Always set `buildName`/`build`, `sessionName`/`name`, and a project tag so runs are findable on the dashboard.
- App under test is referenced by the vendor's uploaded id (`bs://…`, `storage:…`), **never a local file path** in the cap.

### Parallelism
- Read the concurrent-session cap from **one env var** (`GRID_CONCURRENCY`) and map it onto `workers` / `maxInstances`. Never hard-code.
- `total CI shards × workers-per-shard ≤ plan session cap`. Sharding mechanics live in `qa/cicd/typescript/skills/ci-pipelines/*` — cross-link, don't duplicate.

### Secrets
- Username + access key via **env vars only** (`required(...)` helper). Never a literal, never in `wdio.conf.ts`/`browserstack.yml`/`.sauce/config.yml` committed to the repo.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- Surface the **session dashboard URL** in output / Allure on failure — a failed grid run should be one click from the replay.
- **Mark the session pass/fail** back to the vendor (`setSessionStatus` / `sauce:job-result` / `lambda-status`), or let the `@wdio/*-service` do it. The dashboard must reflect reality.

### Tunnels
- Start the tunnel **before** the suite, stop it in teardown; tie sessions via `local`+`localIdentifier` / `tunnelName`.
- Tunnel key from env, never a literal. One tunnel identifier per run so parallel runs don't collide.

### Waits
- **No `setTimeout`-as-a-wait / `page.waitForTimeout` / `browser.pause`** anywhere — grid latency is higher than local, which makes fixed sleeps both flakier and slower. Use Playwright auto-wait / WDIO `waitForDisplayed` / explicit conditions, exactly as the local suite does.

### What NOT to do
- No launching a local browser when the intent is a grid run — connect to the grid.
- No `bstack:options` on a BrowserStack Playwright **direct-connect** — it's flat caps there.
- No hard-coded session/worker count — read the plan cap from env and map it.
- No credential literals in code or committed config — env vars only.
- No grid run that doesn't **report status** to the vendor and **surface the session URL** on failure.
- No tunnel without a stop in teardown, and no tunnel key as a literal.
- No `waitForTimeout`/`pause` to paper over grid latency.

## Generation steps

1. Confirm **web vs mobile**, **vendor** (+ region for Sauce/Device Farm), **private target?** (tunnel), and the **session cap**.
2. Add `tests/support/grid/credentials.ts` with the `required(...)` env reads — no literals.
3. **Web**: add `playwrightConnect.ts` (BrowserStack flat-cap `connect`) + a `gridFixture` that yields a `page` and marks status in teardown; or scaffold `.sauce/config.yml` (Sauce) / the LambdaTest connect. **Mobile**: edit `wdio.conf.ts` — `user`/`key`/`hostname` + vendor service + `bstack:options`/`sauce:options`/`LT:Options` caps.
4. Map the session cap onto `workers` / `maxInstances` from `GRID_CONCURRENCY`; note the `shards × workers ≤ cap` rule and cross-link `qa/cicd/typescript/skills/ci-pipelines/*`.
5. Wire artifacts (`attachSessionUrl`) + session status (`markSessionStatus`) into the fixture teardown.
6. If the target is private, add the tunnel lifecycle (`GridTunnel` start/stop in global setup/teardown) and tie sessions via the cap.
7. Run a single spec against the grid first (one worker) to confirm the connection + caps before fanning out. Confirm the session appears on the dashboard with the right build/project tags. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".

## Cross-references

- **`qa/dotnet/skills/browser-cloud-setup`** + **`qa/java/skills/browser-cloud-setup`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`BrowserType.ConnectAsync`/`AppiumOptions`; Playwright Java `connect`/`UiAutomator2Options`). Structure ported, not code.
- **`qa/typescript/skills/ui-test-author/playwright`** — writes the web specs/page objects this skill runs on a grid (connection patterns to extend).
- **`qa/typescript/skills/ui-test-author/appium`** — writes the mobile specs/page objects; this skill swaps the local Appium session for a grid one.
- **`qa/cicd/typescript/skills/ci-pipelines`** — sharding/`--shard`/blob-merge + OIDC secret injection; this skill maps the plan cap onto those shards (don't duplicate the mechanics).
- **`qa/typescript/skills/device-cloud`** — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/typescript/skills/network-mocking`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).
