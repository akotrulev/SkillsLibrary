---
name: qa-cloud-grid-config-java
description: Use when the user needs to run Java Playwright (web) or Appium java-client (mobile) tests on a **hosted cloud grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — instead of local browsers/emulators. Covers: Playwright Java cloud connect (`playwright.chromium().connect(wsEndpoint)` to `cdp.browserstack.com/playwright`), Appium java-client remote driver (`new AndroidDriver(new URL(hubUrl), UiAutomator2Options)` with `.setCapability("bstack:options", map)`), vendor capability blocks (`bstack:options` / `sauce:options` / `LT:Options`), build/session/project tagging, **parallelism caps** mapped onto TestNG `thread-count` / `data-provider-thread-count`, **artifacts** (video, network/console logs, the session dashboard URL surfaced on failure), **secret handling** (user + access key via env/OIDC, never committed), **local tunnels** (BrowserStackLocal `Local` / Sauce Connect 5 / LambdaTest Tunnel start-stop), and **marking the session pass/fail** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`). Triggers: "run our Playwright Java tests on BrowserStack", "wire Appium java-client to Sauce Labs", "set up LambdaTest caps for our TestNG Appium tests", "connect Playwright Java to a cloud grid", "add a BrowserStackLocal tunnel to our Java suite". Do NOT use for the TypeScript grid stack (use `qa/cloud-grid-config/typescript`), the .NET grid stack (use `qa/cloud-grid-config/dotnet`), writing the page objects / tests themselves (use `qa/ui-test-author/playwright/java` or `qa/ui-test-author/appium/java`), CI shard mechanics (use `qa/ci-pipelines/*`), or deep mobile-farm device-pool specifics (use `qa/mobile-device-farm`).
---

# QA — Cloud Grid Config (Java: Playwright + Appium java-client)

Wires Java tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web tests and Appium java-client mobile tests that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/ui-test-author/{playwright,appium}/java` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or tests.

> **Why this skill exists.** A local Playwright/Appium suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the driver/browser is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those five things right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- Java 21, Gradle (Kotlin DSL)
- **Web**: `com.microsoft.playwright:playwright` connected to a cloud grid via `BrowserType.connect(wsEndpoint)`
- **Mobile**: `io.appium:java-client` 9.x (`UiAutomator2Options` / `XCUITestOptions`, `AndroidDriver`/`IOSDriver`) pointed at the vendor's remote hub
- TestNG as the runner; parallelism via `thread-count` / `data-provider-thread-count` in `testng.xml`
- Tunnels: `com.browserstack:browserstack-local-java` (`Local` class), Sauce Connect 5 (`sc` binary), LambdaTest Tunnel (`LT` binary)
- Grid config under `src/test/java/.../support/grid/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY`, `LT_USERNAME` / `LT_ACCESS_KEY`)
- These suites run in CI under `qa/ci-pipelines/github-actions/java` — secrets injected via the runner's secret store / OIDC, sharding driven by the runner (see § Parallelism)

## When to use

- Running existing Playwright Java web tests on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing Appium java-client mobile tests on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`) for a Java stack
- Capping concurrent sessions to the plan and mapping that onto TestNG `thread-count`
- Surfacing the **session dashboard URL** + video/logs on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The TypeScript / .NET grid stacks → `qa/cloud-grid-config/{typescript,dotnet}`
- Writing the page objects / tests → `qa/ui-test-author/playwright/java`, `qa/ui-test-author/appium/java`
- CI shard/worker mechanics (matrix, sharding props, artifact upload) → `qa/ci-pipelines/*` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/mobile-device-farm` (row #40); this node covers the wiring, that one the farm specifics

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

## Patterns

### Secrets first — never in code or committed config

Credentials are a username + an access key per vendor. They are read from **env vars only** and never logged. A leaked access key is a billable, exfiltratable secret (CLAUDE.md hard rule).

```java
// src/test/java/.../support/grid/GridCredentials.java
package support.grid;

public final class GridCredentials {
    private GridCredentials() {}

    /** Read a required env var or fail loudly — never default a credential to a literal. */
    private static String required(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(
                "Missing required env var " + name + " — set it in your shell or CI secret store.");
        }
        return value;
    }

    public record BrowserStack(String userName, String accessKey) {}
    public record Sauce(String username, String accessKey, String region) {}
    public record LambdaTest(String username, String accessKey) {}

    public static BrowserStack browserStack() {
        return new BrowserStack(required("BROWSERSTACK_USERNAME"), required("BROWSERSTACK_ACCESS_KEY"));
    }
    public static Sauce sauce() {
        String region = System.getenv().getOrDefault("SAUCE_REGION", "us-west-1"); // explicit — no implicit default
        return new Sauce(required("SAUCE_USERNAME"), required("SAUCE_ACCESS_KEY"), region);
    }
    public static LambdaTest lambdaTest() {
        return new LambdaTest(required("LT_USERNAME"), required("LT_ACCESS_KEY"));
    }
}
```

In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/ci-pipelines/github-actions/java`.

### Web — Playwright Java on BrowserStack via `connect`

The only thing that changes vs a local run is the **connection**: instead of `launch()`, connect to the grid's WebSocket endpoint with caps embedded as a URL-encoded JSON `caps` query param. **Flat caps** for BrowserStack Playwright direct-connect (not `bstack:options`). Use constructor injection / a factory, never a service locator.

```java
// src/test/java/.../support/grid/PlaywrightGridConnector.java
package support.grid;

import com.google.gson.Gson;
import com.microsoft.playwright.*;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

public final class PlaywrightGridConnector {
    private static final Gson GSON = new Gson();

    public record GridTarget(String browser, String os, String osVersion,
                             String buildName, String sessionName, String projectName) {}

    /** Connect Playwright to BrowserStack. Caller owns the returned Browser. */
    public Browser connectBrowserStack(Playwright playwright, GridTarget target) {
        GridCredentials.BrowserStack creds = GridCredentials.browserStack();
        // FLAT caps for Playwright direct-connect — NOT bstack:options.
        Map<String, String> caps = new LinkedHashMap<>();
        caps.put("browser", target.browser());
        caps.put("os", target.os());
        caps.put("os_version", target.osVersion());
        caps.put("name", target.sessionName());
        caps.put("build", target.buildName());
        caps.put("project", target.projectName());
        caps.put("browserstack.username", creds.userName());
        caps.put("browserstack.accessKey", creds.accessKey());
        caps.put("browserstack.networkLogs", "true");
        caps.put("browserstack.console", "errors");
        caps.put("client.playwrightVersion", "1.x"); // pin to the installed Playwright in real config

        String encoded = URLEncoder.encode(GSON.toJson(caps), StandardCharsets.UTF_8);
        String wsEndpoint = "wss://cdp.browserstack.com/playwright?caps=" + encoded;
        return playwright.chromium().connect(wsEndpoint);
    }
}
```

Wire it behind a TestNG base class so tests stay grid-agnostic — they use a `Page`, never the grid plumbing:

```java
// src/test/java/.../support/grid/GridWebTestBase.java
package support.grid;

import com.microsoft.playwright.*;
import org.testng.ITestResult;
import org.testng.annotations.*;

public abstract class GridWebTestBase {
    private Playwright playwright;
    private Browser browser;
    protected Page page;

    @BeforeMethod
    public void connect(java.lang.reflect.Method method) {
        playwright = Playwright.create();
        browser = new PlaywrightGridConnector().connectBrowserStack(playwright,
            new PlaywrightGridConnector.GridTarget("chrome", "Windows", "11",
                System.getenv().getOrDefault("BUILD_NAME", "local-build"),
                method.getName(), "checkout-web"));
        page = browser.newPage();
    }

    @AfterMethod
    public void reportAndClose(ITestResult result) {
        boolean passed = result.isSuccess();
        SessionStatus.markBrowserStack(page, passed ? "passed" : "failed", result.getName());
        browser.close();
        playwright.close();
    }
}
```

> The `browserstack-node-sdk` zero-config wrapper is JS-only; the Java path is the explicit `connect` above. LambdaTest mirrors it via `wss://cdp.lambdatest.com/playwright?capabilities=<encoded LT:Options + browser caps>`. Sauce has **no** Playwright `connect` — use `saucectl` (see below).

### Web — Sauce Labs (`saucectl`)

**Sauce has no public ad-hoc Playwright `connect`** — you drive it with `saucectl` and a `.sauce/config.yml`, which uploads and runs the project in Sauce's cloud. `region` is mandatory and explicit. (Sauce's Playwright runner targets the Node Playwright project; for a pure-Java Playwright suite, BrowserStack or LambdaTest are the connect-based options.)

```yaml
# .sauce/config.yml — Sauce runs Playwright via saucectl (no connect())
apiVersion: v1alpha
kind: playwright
sauce:
  region: us-west-1          # explicit — no implicit default
  concurrency: 5             # respect the plan's session cap (see § Parallelism)
suites:
  - name: checkout-web
    platformName: "Windows 11"
    params: { browserName: chromium }
```

### Mobile — Appium java-client on a grid

For mobile the change is also one place — the **driver construction**. Build a `UiAutomator2Options` (Android) / `XCUITestOptions` (iOS), attach the vendor block via `setCapability`, and point a `new AndroidDriver(new URL(hubUrl), options)` at the vendor hub. The page objects from `qa/ui-test-author/appium/java` run unchanged.

```java
// src/test/java/.../support/grid/AppiumGridDriverFactory.java
package support.grid;

import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

public final class AppiumGridDriverFactory {

    public AndroidDriver createBrowserStackAndroid(String sessionName) throws Exception {
        GridCredentials.BrowserStack creds = GridCredentials.browserStack();
        UiAutomator2Options options = new UiAutomator2Options();
        // Appium uses the W3C nested block — bstack:options (NOT the flat Playwright caps).
        Map<String, Object> bstack = new HashMap<>();
        bstack.put("userName", creds.userName());
        bstack.put("accessKey", creds.accessKey());
        bstack.put("deviceName", "Google Pixel 8");
        bstack.put("osVersion", "14.0");
        bstack.put("buildName", System.getenv().getOrDefault("BUILD_NAME", "local-build"));
        bstack.put("sessionName", sessionName);
        bstack.put("projectName", "checkout-mobile");
        bstack.put("networkLogs", true);
        bstack.put("debug", true);   // visual logs / screenshots
        bstack.put("local", true);   // route through the tunnel
        options.setCapability("bstack:options", bstack);
        // App referenced by the uploaded id, never a local path.
        options.setCapability("appium:app", System.getenv("BS_APP_URL"));

        return new AndroidDriver(new URL("https://hub-cloud.browserstack.com/wd/hub"), options);
    }
}
```

For Sauce the hub is `https://ondemand.<region>.saucelabs.com/wd/hub` and the block is `sauce:options`; for LambdaTest `https://mobile-hub.lambdatest.com/wd/hub` with `LT:Options`. The driver-lifecycle/factory discipline is the same one `qa/ui-test-author/appium/java` already uses for local sessions — only the URL and the cap block change.

### Capability blocks — the three schemas

Pinning the right keys matters — vendors renamed them off the legacy JSON-Wire names. All three nest vendor-specifics under one object; standard W3C keys (`platformName`, `browserName`) stay on the options directly.

```java
// src/test/java/.../support/grid/Capabilities.java — the per-vendor blocks, side by side
package support.grid;

import java.util.List;
import java.util.Map;

public final class Capabilities {
    private Capabilities() {}

    public static Map<String, Object> bstack(String build, String session) {
        GridCredentials.BrowserStack c = GridCredentials.browserStack();
        return Map.of(
            "userName", c.userName(), "accessKey", c.accessKey(),
            "buildName", build, "sessionName", session, "projectName", "checkout",
            "os", "Windows", "osVersion", "11",
            "networkLogs", true, "consoleLogs", "errors", "video", true, "debug", true);
    }

    public static Map<String, Object> sauce(String build, String name) {
        GridCredentials.Sauce c = GridCredentials.sauce();
        return Map.of(
            "username", c.username(), "accessKey", c.accessKey(),
            "build", build, "name", name, "tags", List.of("regression"),
            "screenResolution", "1920x1080", "extendedDebugging", true);
    }

    public static Map<String, Object> lt(String build, String name) {
        GridCredentials.LambdaTest c = GridCredentials.lambdaTest();
        return Map.of(
            "username", c.username(), "accessKey", c.accessKey(),
            "build", build, "name", name, "project", "checkout",
            "platformName", "Windows 11", "network", true, "video", true, "console", true, "w3c", true);
    }
}
```

| Concept | BrowserStack (`bstack:options`) | Sauce (`sauce:options`) | LambdaTest (`LT:Options`) |
|---|---|---|---|
| Credentials | `userName` / `accessKey` | `username` / `accessKey` | `username` / `accessKey` |
| Build group | `buildName` | `build` | `build` |
| Session label | `sessionName` | `name` | `name` |
| Project tag | `projectName` | (via `tags`) | `project` |
| Network logs | `networkLogs` | (always on) | `network` |
| Console logs | `consoleLogs` | (always on) | `console` |
| Video | `video` | (always on) | `video` |
| Tunnel | `local` + `localIdentifier` | `tunnelName` | `tunnel` + `tunnelName` |

### Parallelism — respect the plan's session cap

The grid plan has a hard **concurrent-session limit**. Exceeding it queues or rejects sessions; mismatching it to the runner wastes paid slots. Map the cap onto TestNG's `thread-count` — never hard-code a number, read it from one env var (passed in as a system property) so CI and local agree.

```xml
<!-- testng.xml — thread-count must be ≤ the plan's concurrent-session cap -->
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="grid-web" parallel="methods" thread-count="5">
  <test name="checkout">
    <classes>
      <class name="tests.CheckoutGridTest"/>
    </classes>
  </test>
</suite>
```

To drive `thread-count` from the plan cap rather than a hard-coded literal, override it from a Gradle property at runtime:

```kotlin
// build.gradle.kts — map GRID_CONCURRENCY onto TestNG's thread count
tasks.test {
    useTestNG {
        // Plan cap from env, default 5. Never exceed the plan silently.
        parallel = "methods"
        threadCount = (System.getenv("GRID_CONCURRENCY") ?: "5").toInt()
    }
}
```

The **sharding mechanics** (matrix fan-out, `-PshardIndex`/`-PshardTotal`, merging Allure results) belong to `qa/ci-pipelines/github-actions/java` — cross-link it; don't re-derive it here. The rule: `total runner shards × thread-count ≤ plan session cap`.

### Artifacts — surface the session URL on failure

The grid records video, network, and console logs server-side; the value is surfacing the **dashboard session URL** in test output and Allure so a failure is one click from the replay. The session id is the driver's `getSessionId()` (Appium) or the Playwright session id.

```java
// src/test/java/.../support/grid/Artifacts.java
package support.grid;

import io.qameta.allure.Allure;

public final class Artifacts {
    private Artifacts() {}

    /** Attach the vendor session URL so a failing test links straight to the replay. */
    public static void attachSessionUrl(String sessionId) {
        String url = "https://automate.browserstack.com/dashboard/v2/sessions/" + sessionId;
        Allure.link("BrowserStack session", url);
    }
}
```

Call this in `@AfterMethod` (especially on failure). Combined with marking the session status (below), a failed run is fully diagnosable from the report without re-running locally.

### Session status — tell the vendor the verdict

The grid doesn't know your assertions passed; you tell it, so the dashboard reflects reality and analytics stay accurate. **Each vendor's syntax differs and is not interchangeable.**

```java
// src/test/java/.../support/grid/SessionStatus.java
package support.grid;

import com.google.gson.Gson;
import com.microsoft.playwright.Page;
import java.util.Map;
import org.openqa.selenium.JavascriptExecutor;

public final class SessionStatus {
    private static final Gson GSON = new Gson();
    private SessionStatus() {}

    /** BrowserStack via Playwright: a JS-executor command through page.evaluate. */
    public static void markBrowserStack(Page page, String status, String reason) {
        String payload = GSON.toJson(Map.of(
            "action", "setSessionStatus",
            "arguments", Map.of("status", status, "reason", reason)));
        page.evaluate("() => {}", "browserstack_executor: " + payload);
    }

    /** For Appium/Selenium drivers — vendor-specific executor scripts. */
    public static void markBrowserStack(JavascriptExecutor driver, String status, String reason) {
        String payload = GSON.toJson(Map.of(
            "action", "setSessionStatus", "arguments", Map.of("status", status, "reason", reason)));
        driver.executeScript("browserstack_executor: " + payload);
    }

    public static void markSauce(JavascriptExecutor driver, boolean passed) {
        driver.executeScript("sauce:job-result=" + (passed ? "passed" : "failed"));
    }

    public static void markLambdaTest(JavascriptExecutor driver, boolean passed) {
        driver.executeScript("lambda-status=" + (passed ? "passed" : "failed"));
    }
}
```

### Local tunnel — reach private/staging URLs from the grid

When the app under test is on a private/staging host the grid can't reach, start a **tunnel** before the suite and stop it after. The tunnel binds the grid sessions to your network; tie sessions to it via the cap (`local`+`localIdentifier` / `tunnelName`).

```java
// src/test/java/.../support/grid/GridTunnel.java — BrowserStackLocal lifecycle (browserstack-local-java)
package support.grid;

import com.browserstack.local.Local;
import java.util.HashMap;
import java.util.Map;

public final class GridTunnel {
    private final Local local = new Local();
    private final String localIdentifier;

    public GridTunnel(String localIdentifier) { this.localIdentifier = localIdentifier; }

    public void start() throws Exception {
        GridCredentials.BrowserStack creds = GridCredentials.browserStack();
        Map<String, String> options = new HashMap<>();
        options.put("key", creds.accessKey());          // from env, never a literal
        options.put("localIdentifier", localIdentifier);
        options.put("forcelocal", "true");
        local.start(options);
    }

    public void stop() throws Exception { local.stop(); }
}
```

```java
// A TestNG @BeforeSuite / @AfterSuite starts it once per run and stops it in teardown.
@BeforeSuite
public void startTunnel() throws Exception {
    tunnel = new GridTunnel(System.getenv().getOrDefault("BUILD_NAME", "local-build"));
    tunnel.start();
}

@AfterSuite
public void stopTunnel() throws Exception { tunnel.stop(); }
```

Match the `localIdentifier` to the cap (`bstack:options.localIdentifier`). For **Sauce** the binary is **Sauce Connect 5** (`sc run --region us-west-1 --tunnel-name my-tunnel`), tied via `sauce:options.tunnelName`. For **LambdaTest** it's `LT --user … --key … --tunnelName …`, tied via `LT:Options.tunnel`+`tunnelName`. Never pass the key as a literal — read it from env.

### AWS Device Farm — the different paradigm

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package (e.g. `APPIUM_JAVA_TESTNG_TEST_PACKAGE`) to a **project ARN**, then schedule a run against a **device-pool ARN** via the AWS SDK for Java (`DeviceFarmClient.scheduleRun`). For live/client-side Appium, create a remote-access session and read the `remoteDriverEndpoint` from `getRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a `RemoteWebDriver`. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/mobile-device-farm`; this node covers only the connection shape.

## Rules

### Connection
- **Web**: connect, don't launch. Playwright Java → BrowserStack `chromium().connect(wsEndpoint)` with **flat caps**; Sauce → `saucectl`; LambdaTest → its connect endpoint with `LT:Options`.
- **Mobile**: build `UiAutomator2Options`/`XCUITestOptions`, attach the vendor block via `setCapability`, point `new AndroidDriver(new URL(hubUrl), options)` at the hub; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting — they apply to different connection paths.
- Pin the Playwright/Appium version cap to your installed version; a version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`). Vendors renamed them off JSON-Wire.
- Always set `buildName`/`build`, `sessionName`/`name`, and a project tag so runs are findable on the dashboard.
- App under test is referenced by the vendor's uploaded id (`bs://…`), **never a local file path** in the cap.

### Parallelism
- Read the concurrent-session cap from **one env var** (`GRID_CONCURRENCY`) and map it onto TestNG `thread-count`. Never hard-code silently.
- `total CI shards × thread-count ≤ plan session cap`. Sharding mechanics live in `qa/ci-pipelines/*` — cross-link, don't duplicate.

### Secrets
- Username + access key via **env vars only** (`required(...)` helper). Never a literal, never in a committed config file.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- Surface the **session dashboard URL** in output / Allure on failure — a failed grid run should be one click from the replay.
- **Mark the session pass/fail** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`) in `@AfterMethod`. The dashboard must reflect reality.

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
3. **Web**: add `PlaywrightGridConnector` (BrowserStack flat-cap `connect`) + a `GridWebTestBase` that yields a `Page` and marks status in `@AfterMethod`; or scaffold `.sauce/config.yml` (Sauce) / the LambdaTest connect. **Mobile**: add `AppiumGridDriverFactory` — `UiAutomator2Options` + `setCapability("bstack:options", map)` + `new AndroidDriver(new URL(hubUrl), options)`.
4. Map the session cap onto TestNG `thread-count` from `GRID_CONCURRENCY`; note the `shards × thread-count ≤ cap` rule and cross-link `qa/ci-pipelines/*`.
5. Wire artifacts (`Artifacts.attachSessionUrl`) + session status (`SessionStatus.mark…`) into `@AfterMethod`.
6. If the target is private, add the tunnel lifecycle (`GridTunnel` in `@BeforeSuite`/`@AfterSuite`) and tie sessions via the cap.
7. Run a single test against the grid first (one thread) to confirm the connection + caps before fanning out. Confirm the session appears on the dashboard with the right build/project tags.

## Cross-references

- **`qa/cloud-grid-config/typescript`** + **`qa/cloud-grid-config/dotnet`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`chromium.connect`/`@wdio/*-service`; Playwright .NET `ConnectAsync`/`AppiumOptions`). Structure ported, not code.
- **`qa/ui-test-author/playwright/java`** — writes the web tests/page objects this skill runs on a grid (connection patterns to extend).
- **`qa/ui-test-author/appium/java`** — writes the mobile tests/page objects; this skill swaps the local Appium session for a grid one (same driver-factory discipline).
- **`qa/ci-pipelines/github-actions/java`** — sharding/`-PshardIndex` + OIDC secret injection; this skill maps the plan cap onto those shards (don't duplicate the mechanics).
- **`qa/mobile-device-farm`** (row #40, Phase 3) — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/network-monitoring/proxy/java`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).

## Sources synthesized (research-first per CLAUDE.md)

- [BrowserStack — Playwright: set browser options / capabilities](https://www.browserstack.com/docs/automate/playwright/set-browser-options) + [playwright-browserstack/playwright-java](https://github.com/browserstack/playwright-browserstack/tree/main/playwright-java) — `wss://cdp.browserstack.com/playwright` flat-cap connect for Playwright Java `chromium().connect(...)`.
- [BrowserStack — App Automate / Appium 2 migration](https://www.browserstack.com/docs/app-automate/appium/references/appium-2-migration-doc) + [App Automate capabilities](https://www.browserstack.com/docs/app-automate/capabilities) — `UiAutomator2Options`/`XCUITestOptions` + `setCapability("bstack:options", map)`, `new AndroidDriver(new URL(hub), options)`.
- [Sauce Labs — Playwright via saucectl](https://docs.saucelabs.com/web-apps/automated-testing/playwright/) + [test-config options](https://docs.saucelabs.com/dev/test-configuration-options/) + [data-center endpoints](https://docs.saucelabs.com/basics/data-center-endpoints/) — `saucectl`, `sauce:options`, regional hubs, `sauce:job-result`.
- [LambdaTest — Appium Java docs](https://www.lambdatest.com/support/docs/appium-java/) — `LT:Options` schema, `mobile-hub.lambdatest.com`, `lambda-status`.
- [BrowserStack — set name and status of test](https://www.browserstack.com/docs/automate/selenium/set-name-and-status-of-test) — `browserstack_executor: setSessionStatus`.
- [browserstack-local-java README](https://github.com/browserstack/browserstack-local-java) + [Sauce Connect 5 FAQ](https://docs.saucelabs.com/secure-connections/sauce-connect-5/faq/) — `Local` start/stop, Sauce Connect 5.
- [AWS Device Farm — schedule run](https://docs.aws.amazon.com/devicefarm/latest/developerguide/how-to-create-test-run.html) — the ARN/upload paradigm and `scheduleRun`.

## Changelog

- 2026-05-31: Authored as the **java** sibling of the new `qa/cloud-grid-config/` node (QA Skills Library Phase 2, `qa/GAP-ANALYSIS.md` row 15), **ported from the canonical `typescript` stack** (translate, not redesign). Same five moves re-expressed in Java idioms: **connect** (Playwright Java `chromium().connect(wsEndpoint)` to `cdp.browserstack.com/playwright` with **flat** caps; Appium `new AndroidDriver(new URL(hub), UiAutomator2Options)` + `setCapability("bstack:options", map)`; Sauce via `saucectl`), **capability blocks** (`bstack:options`/`sauce:options`/`LT:Options` `Map<String,Object>` builders + side-by-side table), **parallelism** (plan cap → TestNG `thread-count` via `GRID_CONCURRENCY` Gradle override; `shards × thread-count ≤ cap`, mechanics cross-linked to `ci-pipelines`), **artifacts + session status** (dashboard URL into Allure on failure; `browserstack_executor`/`sauce:job-result`/`lambda-status` via `JavascriptExecutor`/`Page.evaluate`), and **tunnels** (`browserstack-local-java` `Local` start/stop in `@BeforeSuite`/`@AfterSuite`, Sauce Connect 5, LambdaTest Tunnel; key from env). Same gotchas flagged: BrowserStack Playwright direct-connect uses **legacy flat caps not `bstack:options`**, and **Sauce has no public Playwright connect** (saucectl only). Constructor-injection/factory discipline, secrets via env only, no `Thread.sleep`. Mirrors the TS file's section order exactly. **Closes the `qa/cloud-grid-config` node (all 3 stacks) and row #15.**
