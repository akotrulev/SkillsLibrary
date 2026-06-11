# Deep-dive details — `qa-cloud-grid-config-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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

In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/java/skills/ci-pipelines`.

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

For mobile the change is also one place — the **driver construction**. Build a `UiAutomator2Options` (Android) / `XCUITestOptions` (iOS), attach the vendor block via `setCapability`, and point a `new AndroidDriver(new URL(hubUrl), options)` at the vendor hub. The page objects from `qa/java/skills/ui-test-author/appium` run unchanged.

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

For Sauce the hub is `https://ondemand.<region>.saucelabs.com/wd/hub` and the block is `sauce:options`; for LambdaTest `https://mobile-hub.lambdatest.com/wd/hub` with `LT:Options`. The driver-lifecycle/factory discipline is the same one `qa/java/skills/ui-test-author/appium` already uses for local sessions — only the URL and the cap block change.

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

The **sharding mechanics** (matrix fan-out, `-PshardIndex`/`-PshardTotal`, merging Allure results) belong to `qa/java/skills/ci-pipelines` — cross-link it; don't re-derive it here. The rule: `total runner shards × thread-count ≤ plan session cap`.

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

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package (e.g. `APPIUM_JAVA_TESTNG_TEST_PACKAGE`) to a **project ARN**, then schedule a run against a **device-pool ARN** via the AWS SDK for Java (`DeviceFarmClient.scheduleRun`). For live/client-side Appium, create a remote-access session and read the `remoteDriverEndpoint` from `getRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a `RemoteWebDriver`. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/java/skills/mobile-device-farm`; this node covers only the connection shape.
