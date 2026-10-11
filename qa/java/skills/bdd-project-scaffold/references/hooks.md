# `Hooks.java` — `qa-bdd-project-setup-java`

The per-scenario Playwright lifecycle and failure evidence for a Cucumber-JVM web project. The contract it
implements is in `SKILL.md` § `support/Hooks.java`; the evidence rules are `qa/java/skills/evidence-capture`'s
(§ Cucumber scenarios), the same ones J1's `BaseTest` follows for TestNG
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`).

`src/test/java/com/example/support/Hooks.java`:

```java
package com.example.support;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.Tracing;
import com.microsoft.playwright.Video;
import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.Scenario;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class Hooks {
    private static final Path ARTIFACTS = Path.of("build", "playwright-artifacts");
    private static final Path RAW_VIDEOS = Path.of("build", "playwright-videos");
    private static final System.Logger LOG = System.getLogger(Hooks.class.getName());

    private final TestContext context;
    private Playwright playwright;
    private BrowserContext browserContext;

    public Hooks(TestContext context) {
        this.context = context;
    }

    static String requiredEnv(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Environment variable " + name + " is not set");
        }
        return value;
    }

    @Before(order = 0)
    public void openBrowser() {
        playwright = Playwright.create();
        playwright.selectors().setTestIdAttribute("data-testid");
        boolean headed = "1".equals(System.getenv("HEADED"));
        Browser browser = playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(!headed));
        browserContext = browser.newContext(new Browser.NewContextOptions()
                .setBaseURL(requiredEnv("BASE_URL"))
                .setRecordVideoDir(RAW_VIDEOS));
        browserContext.tracing().start(new Tracing.StartOptions()
                .setScreenshots(true)
                .setSnapshots(true)
                .setSources(true));
        context.setPage(browserContext.newPage());
    }

    @After(order = 0)
    public void closeBrowser(Scenario scenario) throws IOException {
        boolean failed = scenario.isFailed();
        String name = evidenceName(scenario);
        Page page = context.page();
        Video video = page.video();
        if (failed) {
            keepScreenshot(page, name);
            keepTrace(name);
        } else {
            browserContext.tracing().stop();
        }
        browserContext.close();
        if (failed) {
            keepVideo(video, name);
        }
        video.delete();
        playwright.close();
    }

    private static String evidenceName(Scenario scenario) {
        String uri = scenario.getUri().toString();
        String feature = uri.substring(uri.lastIndexOf('/') + 1).replaceFirst("\\.feature$", "");
        return (feature + "." + scenario.getName()).replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private void keepScreenshot(Page page, String name) throws IOException {
        Path file = artifact(name, "png");
        try {
            page.screenshot(new Page.ScreenshotOptions().setPath(file).setFullPage(true));
        } catch (PlaywrightException e) {
            LOG.log(System.Logger.Level.WARNING, "Screenshot not captured for {0}: {1}", name, e.getMessage());
            return;
        }
        attach("screenshot", "image/png", file, "png");
    }

    private void keepTrace(String name) throws IOException {
        Path file = artifact(name, "zip");
        browserContext.tracing().stop(new Tracing.StopOptions().setPath(file));
        attach("trace", "application/vnd.allure.playwright-trace", file, "zip");
    }

    private static void keepVideo(Video video, String name) throws IOException {
        Path file = artifact(name, "webm");
        video.saveAs(file);
        attach("video", "video/webm", file, "webm");
    }

    private static Path artifact(String name, String extension) {
        return ARTIFACTS.resolve(name + "." + extension);
    }

    private static void attach(String name, String type, Path file, String extension) throws IOException {
        try (InputStream content = Files.newInputStream(file)) {
            Allure.attachment(name, type, content, AttachmentOptions.withFileExtension(extension));
        }
    }
}
```

- `<Feature>` is the feature **file** name without `.feature` (`login.feature` → `login`): Cucumber-JVM's
  `Scenario` exposes the file's URI, not the `Feature:` title. A scenario named `Sign in with a wrong password`
  in `login.feature` keeps `build/playwright-artifacts/login.Sign_in_with_a_wrong_password.{png,zip,webm}`.
- Every row of a Scenario Outline shares one scenario name, so when two rows fail the files on disk hold the last
  failing row; Allure keeps each row's own attachments.
- `build/playwright-videos/` is scratch — emptied after every scenario, never uploaded.
- Tagged hooks scope setup to platform: `@Before("@web")` / `@Before("@mobile")` let one project carry both a web
  and a mobile hook class without clashing.
- A `Playwright` per scenario, created and closed on the scenario's thread, is the simplest shape that keeps
  Playwright's thread rule — including if `cucumber.execution.parallel.enabled` is turned on later.

## Mobile hook

`@Before("@mobile")` / `@After("@mobile")` for a scenario tagged `@mobile`, next to the web `Hooks`. It sits beside the project's existing `AppiumDriverFactory` (`qa/java/skills/ui-test-author/appium/assets/`), keeps the same R7 evidence as `BaseMobileTest` under `build/appium-artifacts/`, and names files the same way as the web hook (`evidenceName`). The recording (`startRecordingScreen` per scenario, kept only on failure) is added the way `BaseMobileTest` does it; `qa/java/skills/evidence-capture/references/appium.md` § 4 has the limits.

```java
package com.example.support;

import io.appium.java_client.AppiumDriver;
import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.Scenario;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.WebDriverException;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.net.MalformedURLException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.function.Supplier;

public class MobileHooks {
    private static final Path ARTIFACTS = Path.of("build", "appium-artifacts");
    private static final System.Logger LOG = System.getLogger(MobileHooks.class.getName());

    private final TestContext context;

    public MobileHooks(TestContext context) {
        this.context = context;
    }

    @Before(value = "@mobile", order = 0)
    public void startDriver() throws MalformedURLException {
        context.setDriver(AppiumDriverFactory.create());
    }

    @After(value = "@mobile", order = 1)
    public void captureEvidence(Scenario scenario) throws IOException {
        if (!scenario.isFailed()) {
            return;
        }
        AppiumDriver driver = context.driver();
        String name = evidenceName(scenario);
        Optional<byte[]> screenshot = fromDevice("screenshot", () -> driver.getScreenshotAs(OutputType.BYTES));
        Optional<String> pageSource = fromDevice("page source", driver::getPageSource);
        if (screenshot.isPresent()) {
            keep(name, "png", "image/png", screenshot.get());
        }
        if (pageSource.isPresent()) {
            keep(name, "xml", "application/xml", pageSource.get().getBytes(StandardCharsets.UTF_8));
        }
    }

    @After(value = "@mobile", order = 0)
    public void quitDriver() {
        context.driver().quit();
    }

    private static String evidenceName(Scenario scenario) {
        String uri = scenario.getUri().toString();
        String feature = uri.substring(uri.lastIndexOf('/') + 1).replaceFirst("\\.feature$", "");
        return (feature + "." + scenario.getName()).replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private static <T> Optional<T> fromDevice(String what, Supplier<T> capture) {
        try {
            return Optional.ofNullable(capture.get());
        } catch (WebDriverException e) {
            LOG.log(System.Logger.Level.WARNING, "Could not capture {0}: {1}", what, e.getMessage());
            return Optional.empty();
        }
    }

    private static void keep(String name, String extension, String type, byte[] content) throws IOException {
        Files.createDirectories(ARTIFACTS);
        Files.write(ARTIFACTS.resolve(name + "." + extension), content);
        Allure.attachment(name, type, new ByteArrayInputStream(content), AttachmentOptions.withFileExtension(extension));
    }
}
```

- Cucumber runs `@After` hooks from the highest `order` down, so the evidence is captured (order 1) before the driver quits (order 0), and a failed capture still ends in `quitDriver`.
- A scenario's page objects take `context.driver()`, so a step reads `new LoginPage(context.driver()).signIn(email, password)`.
- `TestContext` carries `setDriver(AppiumDriver)` and `driver()` for a mobile project, as the web one carries `setPage` and `page`.

