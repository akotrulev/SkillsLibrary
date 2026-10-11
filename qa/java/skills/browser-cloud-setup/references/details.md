# Deep-dive details — `qa-browser-cloud-setup-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Patterns

### Secrets first — never in code or committed config

Credentials are a username + an access key per vendor. They are read from **env vars only** and never logged. A leaked access key is a billable, exfiltratable secret (CLAUDE.md hard rule). An unset variable fails loudly; no credential defaults to a literal.

`support/grid/GridCredentials.java`:

```java
package com.example.uitests.support.grid;

public final class GridCredentials {
    private GridCredentials() {}

    public static String required(String name) {
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
        return new Sauce(required("SAUCE_USERNAME"), required("SAUCE_ACCESS_KEY"), required("SAUCE_REGION"));
    }

    public static LambdaTest lambdaTest() {
        return new LambdaTest(required("LT_USERNAME"), required("LT_ACCESS_KEY"));
    }

    public static String buildName() {
        return required("BUILD_NAME");
    }
}
```

`SAUCE_REGION` is required rather than defaulted: Sauce has no implicit region, and a silent `us-west-1` sends an EU account's sessions to the wrong data centre. In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/cicd/java/skills/ci-pipelines`.

### Web — Playwright Java on BrowserStack via `connect`

The only thing that changes vs a local run is **where the browser comes from**. J1's `BaseTest`
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`) launches it in `newBrowser(playwright)`; a grid
class overrides that one hook to `connect` to the grid's WebSocket endpoint instead. Context per test, failure
evidence, `BASE_URL`, the test-id attribute and `parallel="classes"` stay exactly as they are locally
(`lifecycle.md` §3).

BrowserStack's Playwright direct-connect takes **flat caps** (not `bstack:options`) as a URL-encoded JSON `caps`
query parameter. `client.playwrightVersion` is the **installed** client version, read from the jar's Maven
metadata — a typed `"1.x"` or a stale literal makes BrowserStack pick a different server-side Playwright, and the
skew fails remotely with a protocol error.

`support/grid/GridTarget.java` and `support/grid/BrowserStackGrid.java`:

```java
package com.example.uitests.support.grid;

public record GridTarget(String browser, String os, String osVersion, String project) {
    public static final GridTarget CHROME_WINDOWS_11 = new GridTarget("chrome", "Windows", "11", "checkout-web");
    public static final GridTarget EDGE_WINDOWS_11 = new GridTarget("edge", "Windows", "11", "checkout-web");
}
```

```java
package com.example.uitests.support.grid;

import com.google.gson.Gson;
import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Playwright;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;

public final class BrowserStackGrid {
    private static final Gson GSON = new Gson();
    private static final String PLAYWRIGHT_POM = "/META-INF/maven/com.microsoft.playwright/playwright/pom.properties";

    private BrowserStackGrid() {}

    public static GridSession connect(Playwright playwright, GridTarget target, String sessionName) {
        GridCredentials.BrowserStack credentials = GridCredentials.browserStack();
        Map<String, String> caps = new LinkedHashMap<>();
        caps.put("browser", target.browser());
        caps.put("os", target.os());
        caps.put("os_version", target.osVersion());
        caps.put("name", sessionName);
        caps.put("build", GridCredentials.buildName());
        caps.put("project", target.project());
        caps.put("browserstack.username", credentials.userName());
        caps.put("browserstack.accessKey", credentials.accessKey());
        caps.put("browserstack.networkLogs", "true");
        caps.put("browserstack.console", "errors");
        caps.put("client.playwrightVersion", installedPlaywrightVersion());
        String endpoint = "wss://cdp.browserstack.com/playwright?caps="
                + URLEncoder.encode(GSON.toJson(caps), StandardCharsets.UTF_8);
        return new GridSession(playwright.chromium().connect(endpoint));
    }

    static String installedPlaywrightVersion() {
        try (InputStream pom = Playwright.class.getResourceAsStream(PLAYWRIGHT_POM)) {
            Properties properties = new Properties();
            properties.load(Objects.requireNonNull(pom, PLAYWRIGHT_POM + " is not on the classpath"));
            return properties.getProperty("version");
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot read the installed Playwright version from " + PLAYWRIGHT_POM, e);
        }
    }
}
```

- `chrome` and `edge` connect through `playwright.chromium()`; a `playwright-firefox` or `playwright-webkit`
  target connects through `firefox()` / `webkit()`.
- Gson is Playwright for Java's own dependency, so the caps add no JSON library.
- The version comes from the Playwright jar's `pom.properties`, which Maven writes into every artifact it builds;
  it equals the pin in the writer's **Versions** table (`ui-test-author/playwright/SKILL.md`). Not yet run in this
  library — if the resource is missing, the `requireNonNull` message says so and the fallback is the same pin read
  from a build property.

### One session per class, one verdict per session

`parallel="classes"` gives each class one `BaseTest` instance and one browser (`lifecycle.md` §1), so on a grid
**a class is one vendor session**: its tests run in that session one after another, each in its own context.
Marking the verdict per test would overwrite it with whichever test ran last, so the class marks it **once**, in
`@AfterClass`, from the failures TestNG recorded for that instance — before `BaseTest.closeBrowser` releases
the browser (subclass `@After…` methods run first). The dashboard link is attached at the same point; allure-testng
shows a class-level attachment in every test's tear-down.

`support/grid/GridSession.java`:

```java
package com.example.uitests.support.grid;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Page;
import io.qameta.allure.Allure;
import org.testng.ITestContext;
import org.testng.ITestResult;

import java.util.List;
import java.util.Map;

public final class GridSession {
    private static final Gson GSON = new Gson();

    private final Browser browser;

    GridSession(Browser browser) {
        this.browser = browser;
    }

    public Browser browser() {
        return browser;
    }

    public void markOutcome(ITestContext run, Object testInstance) {
        List<String> failed = run.getFailedTests().getAllResults().stream()
                .filter(result -> result.getInstance() == testInstance)
                .map(ITestResult::getName)
                .sorted()
                .toList();
        String status = failed.isEmpty() ? "passed" : "failed";
        String reason = failed.isEmpty() ? "all tests passed" : "failed: " + String.join(", ", failed);
        Page page = browser.newPage();
        String details = execute(page, Map.of("action", "getSessionDetails"));
        execute(page, Map.of("action", "setSessionStatus", "arguments", Map.of("status", status, "reason", reason)));
        page.close();
        Allure.attachment("BrowserStack session", GSON.fromJson(details, JsonObject.class).get("browser_url").getAsString());
    }

    private static String execute(Page page, Map<String, Object> command) {
        return String.valueOf(page.evaluate("_ => {}", "browserstack_executor: " + GSON.toJson(command)));
    }
}
```

`browserstack_executor` commands run through `page.evaluate`, which is why the verdict opens one short-lived page
on the session's browser. `getSessionDetails` and its `browser_url` field are BrowserStack's documented spelling
as this library carried it; they are not yet run here, so check one session's JSON before relying on the link.

### The grid class — the same tests, a different browser

A grid target is an override on the class that needs it (`lifecycle.md` §3). To run an existing test class on
a target, subclass it — TestNG runs the inherited tests again in the subclass, exactly as a device class does in
`emulation-and-mobile-web.md` §1:

```java
package com.example.uitests.grid;

import com.example.uitests.support.grid.BrowserStackGrid;
import com.example.uitests.support.grid.GridSession;
import com.example.uitests.support.grid.GridTarget;
import com.example.uitests.tests.LoginTest;
import com.microsoft.playwright.Browser;
import com.microsoft.playwright.Playwright;
import org.testng.ITestContext;
import org.testng.annotations.AfterClass;

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

- One grid class per target per test class. The session name is the class name, so the dashboard reads as the
  matrix (`LoginOnEdgeTest`, `LoginOnChromeTest`).
- The grid classes live in their own package, run by their own suite file; the local suite's `testng.xml`
  lists only `com.example.uitests.tests`, so a local run never connects to the grid.
- No `@DataProvider(parallel = true)` and no `parallel="methods"`: either puts two threads on one Playwright
  instance (`lifecycle.md` §1).

> The `browserstack-node-sdk` zero-config wrapper is JS-only; the Java path is the explicit `connect` above. LambdaTest mirrors it via `wss://cdp.lambdatest.com/playwright?capabilities=<encoded LT:Options + browser caps>` and its own `lambdatest_executor` status command. Sauce has **no** Playwright `connect` — use `saucectl` (see below).

### Web — Sauce Labs (`saucectl`)

**Sauce has no public ad-hoc Playwright `connect`** — you drive it with `saucectl` and a `.sauce/config.yml`, which uploads and runs the project in Sauce's cloud. `region` is mandatory and explicit. Sauce's Playwright runner targets the Node Playwright project; for a pure-Java Playwright suite, BrowserStack or LambdaTest are the connect-based options. `concurrency` is the plan's session cap (§ Parallelism).

```yaml
apiVersion: v1alpha
kind: playwright
sauce:
  region: us-west-1
  concurrency: 5
suites:
  - name: checkout-web
    platformName: "Windows 11"
    params: { browserName: chromium }
```

### Mobile — Appium java-client on a grid

For mobile the change is also one place — the **driver construction**. Build a `UiAutomator2Options` (Android) / `XCUITestOptions` (iOS), attach the vendor block via `setCapability`, and point a `new AndroidDriver(new URL(hubUrl), options)` at the vendor hub. The page objects from `qa/java/skills/ui-test-author/appium` run unchanged. In java-client 11 an `AndroidDriver` is a `WebDriver` and a `JavascriptExecutor` but **not** a `RemoteWebDriver`, so helpers take `JavascriptExecutor` or `WebDriver`, never `RemoteWebDriver`. Appium uses the W3C nested `bstack:options` block (not the flat Playwright caps); `debug` turns on visual logs, `local` routes through the tunnel, and the app is the uploaded `bs://…` id, never a local path.

```java
package com.example.uitests.support.grid;

import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import java.net.MalformedURLException;
import java.net.URI;
import java.util.HashMap;
import java.util.Map;

public final class AppiumGridDriverFactory {

    public AndroidDriver createBrowserStackAndroid(String sessionName) throws MalformedURLException {
        GridCredentials.BrowserStack creds = GridCredentials.browserStack();
        UiAutomator2Options options = new UiAutomator2Options();
        Map<String, Object> bstack = new HashMap<>();
        bstack.put("userName", creds.userName());
        bstack.put("accessKey", creds.accessKey());
        bstack.put("deviceName", "Google Pixel 8");
        bstack.put("osVersion", "14.0");
        bstack.put("buildName", GridCredentials.buildName());
        bstack.put("sessionName", sessionName);
        bstack.put("projectName", "checkout-mobile");
        bstack.put("networkLogs", true);
        bstack.put("debug", true);
        bstack.put("local", true);
        options.setCapability("bstack:options", bstack);
        options.setCapability("appium:app", GridCredentials.required("BS_APP_URL"));

        return new AndroidDriver(URI.create("https://hub-cloud.browserstack.com/wd/hub").toURL(), options);
    }
}
```

For Sauce the hub is `https://ondemand.<region>.saucelabs.com/wd/hub` and the block is `sauce:options`; for LambdaTest `https://mobile-hub.lambdatest.com/wd/hub` with `LT:Options`. The driver-lifecycle/factory discipline is the same one `qa/java/skills/ui-test-author/appium` already uses for local sessions — only the URL and the cap block change.

### Capability blocks — the three schemas

Pinning the right keys matters — vendors renamed them off the legacy JSON-Wire names. All three nest vendor-specifics under one object; standard W3C keys (`platformName`, `browserName`) stay on the options directly.

```java
package com.example.uitests.support.grid;

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

The grid plan has a hard **concurrent-session limit**. Exceeding it queues or rejects sessions; mismatching it to the runner wastes paid slots. With `parallel="classes"` each running class holds one session, so **`thread-count` is the number of concurrent sessions**. It is read from one env var, `GRID_CONCURRENCY`, so CI and local agree.

A suite file's `thread-count` beats a command-line or Gradle `threadCount`, so the value is set on the suite itself by an `IAlterSuiteListener`, which TestNG applies before any suite runs. It must be declared in the suite file (or through `ServiceLoader`) — a `@Listeners` annotation is read too late.

`testng-grid.xml` at the project root, beside J1's `testng.xml`:

```xml
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="Grid" parallel="classes">
    <listeners>
        <listener class-name="com.example.uitests.support.grid.GridConcurrency"/>
    </listeners>
    <test name="BrowserStack">
        <packages>
            <package name="com.example.uitests.grid"/>
        </packages>
    </test>
</suite>
```

```java
package com.example.uitests.support.grid;

import org.testng.IAlterSuiteListener;
import org.testng.xml.XmlSuite;

import java.util.List;

public final class GridConcurrency implements IAlterSuiteListener {
    @Override
    public void alter(List<XmlSuite> suites) {
        int sessions = Integer.parseInt(GridCredentials.required("GRID_CONCURRENCY"));
        suites.forEach(suite -> suite.setThreadCount(sessions));
    }
}
```

A second Gradle test task runs it, beside J1's `test` task (`assets/build.gradle.kts`):

```kotlin
tasks.register<Test>("gridTest") {
    testClassesDirs = sourceSets["test"].output.classesDirs
    classpath = sourceSets["test"].runtimeClasspath
    useTestNG {
        suites("testng-grid.xml")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
}
```

`GRID_CONCURRENCY=5 BUILD_NAME=nightly-42 BASE_URL=https://staging.example.test ./gradlew gridTest`. The **sharding mechanics** (matrix fan-out, `-PshardIndex`/`-PshardTotal`, merging Allure results) belong to `qa/cicd/java/skills/ci-pipelines` — cross-link it; don't re-derive it here. The rule: `total runner shards × GRID_CONCURRENCY ≤ plan session cap`.

### Session status — Appium and Selenium drivers

A Playwright grid class marks its session through `GridSession.markOutcome` (above). An Appium or Selenium session
marks it through the driver's executor (`JavascriptExecutor`, which `AppiumDriver` implements in java-client 11); each vendor's syntax differs and is not interchangeable.

```java
package com.example.uitests.support.grid;

import com.google.gson.Gson;
import java.util.Map;
import org.openqa.selenium.JavascriptExecutor;

public final class SessionStatus {
    private static final Gson GSON = new Gson();
    private SessionStatus() {}

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

The session dashboard URL for an Appium session is built from the driver's `getSessionId()` and attached with
`Allure.attachment("BrowserStack session", url)` (allure-java 3.0) in the same teardown that marks the status.

### Local tunnel — reach private/staging URLs from the grid

When the app under test is on a private/staging host the grid can't reach, start a **tunnel** before the suite and stop it after. The tunnel binds the grid sessions to your network; tie sessions to it via the cap (`local`+`localIdentifier` / `tunnelName`). The key comes from env, never a literal.

`support/grid/GridTunnel.java` — BrowserStackLocal lifecycle (`browserstack-local-java`):

```java
package com.example.uitests.support.grid;

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
        options.put("key", creds.accessKey());
        options.put("localIdentifier", localIdentifier);
        options.put("forcelocal", "true");
        local.start(options);
    }

    public void stop() throws Exception { local.stop(); }
}
```

A suite-level class, listed in `testng-grid.xml` as a `<class>` beside the `<packages>` entry, starts it once per run and stops it in teardown:

```java
public class GridTunnelSetup {
    private GridTunnel tunnel;

    @BeforeSuite(alwaysRun = true)
    public void startTunnel() throws Exception {
        tunnel = new GridTunnel(GridCredentials.buildName());
        tunnel.start();
    }

    @AfterSuite(alwaysRun = true)
    public void stopTunnel() throws Exception {
        tunnel.stop();
    }
}
```

Match the `localIdentifier` to the cap (`bstack:options.localIdentifier`, or `browserstack.localIdentifier` with `browserstack.local` in the flat Playwright caps). For **Sauce** the binary is **Sauce Connect 5** (`sc run --region us-west-1 --tunnel-name my-tunnel`), tied via `sauce:options.tunnelName`. For **LambdaTest** it's `LT --user … --key … --tunnelName …`, tied via `LT:Options.tunnel`+`tunnelName`. Never pass the key as a literal — read it from env.

### AWS Device Farm — the different paradigm

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package (e.g. `APPIUM_JAVA_TESTNG_TEST_PACKAGE`) to a **project ARN**, then schedule a run against a **device-pool ARN** via the AWS SDK for Java (`DeviceFarmClient.scheduleRun`). For live/client-side Appium, create a remote-access session and read the `remoteDriverEndpoint` from `getRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a `RemoteWebDriver`. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/java/skills/device-cloud`; this node covers only the connection shape.
