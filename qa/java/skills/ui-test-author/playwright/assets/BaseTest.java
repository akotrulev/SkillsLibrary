package com.example.uitests.support;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.PlaywrightException;
import com.microsoft.playwright.Tracing;
import com.microsoft.playwright.Video;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import org.testng.ITestResult;
import org.testng.annotations.AfterClass;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

public abstract class BaseTest {
    private static final Path ARTIFACTS = Path.of("build", "playwright-artifacts");
    private static final Path RAW_VIDEOS = Path.of("build", "playwright-videos");
    private static final String TEST_ID_ATTRIBUTE = "data-testid";
    private static final System.Logger LOG = System.getLogger(BaseTest.class.getName());

    private Playwright playwright;
    private Browser browser;
    private BrowserContext context;
    protected Page page;

    protected BrowserType.LaunchOptions launchOptions() {
        return new BrowserType.LaunchOptions();
    }

    protected Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions();
    }

    protected static String requiredEnv(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Environment variable " + name + " is not set");
        }
        return value;
    }

    protected Browser newBrowser(Playwright playwright) {
        boolean headed = "1".equals(System.getenv("HEADED"));
        return playwright.chromium().launch(launchOptions().setHeadless(!headed));
    }

    @BeforeClass(alwaysRun = true)
    public void launchBrowser() {
        playwright = Playwright.create();
        playwright.selectors().setTestIdAttribute(TEST_ID_ATTRIBUTE);
        browser = newBrowser(playwright);
    }

    @BeforeMethod(alwaysRun = true)
    public void openContext() {
        context = browser.newContext(contextOptions()
                .setBaseURL(requiredEnv("BASE_URL"))
                .setRecordVideoDir(RAW_VIDEOS));
        context.tracing().start(new Tracing.StartOptions()
                .setScreenshots(true)
                .setSnapshots(true)
                .setSources(true));
        page = context.newPage();
    }

    @AfterMethod(alwaysRun = true)
    public void closeContext(ITestResult result) throws IOException {
        boolean failed = result.getStatus() == ITestResult.FAILURE;
        String name = result.getTestClass().getRealClass().getSimpleName() + "." + result.getMethod().getMethodName();
        Video video = page.video();
        if (failed) {
            keepScreenshot(name);
            keepTrace(name);
        } else {
            context.tracing().stop();
        }
        context.close();
        if (failed) {
            keepVideo(video, name);
        }
        video.delete();
    }

    @AfterClass(alwaysRun = true)
    public void closeBrowser() {
        playwright.close();
    }

    private void keepScreenshot(String name) throws IOException {
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
        context.tracing().stop(new Tracing.StopOptions().setPath(file));
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
