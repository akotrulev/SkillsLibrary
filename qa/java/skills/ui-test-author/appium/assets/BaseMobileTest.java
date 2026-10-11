package com.example.mobiletests.support;

import io.appium.java_client.AppiumDriver;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.AndroidStartScreenRecordingOptions;
import io.appium.java_client.ios.IOSDriver;
import io.appium.java_client.ios.IOSStartScreenRecordingOptions;
import io.appium.java_client.screenrecording.CanRecordScreen;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.WebDriverException;
import org.openqa.selenium.logging.LogEntry;
import org.testng.ITestResult;
import org.testng.annotations.AfterClass;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.net.MalformedURLException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Base64;
import java.util.List;
import java.util.Optional;
import java.util.function.Supplier;
import java.util.stream.Collectors;

public abstract class BaseMobileTest {
    private static final Path ARTIFACTS = Path.of("build", "appium-artifacts");
    private static final Duration RECORDING_LIMIT = Duration.ofSeconds(180);
    private static final int LOG_TAIL_LINES = 200;
    private static final System.Logger LOG = System.getLogger(BaseMobileTest.class.getName());

    private final boolean recordLocally = System.getenv("DEVICE_FARM") == null;
    protected AppiumDriver driver;

    @BeforeClass(alwaysRun = true)
    public void startDriver() throws MalformedURLException {
        driver = AppiumDriverFactory.create();
    }

    @AfterClass(alwaysRun = true)
    public void quitDriver() {
        if (driver != null) {
            driver.quit();
        }
    }

    @BeforeMethod(alwaysRun = true)
    public void startRecording() {
        if (recordLocally) {
            onDevice("recording start", this::beginRecording);
        }
    }

    @AfterMethod(alwaysRun = true)
    public void captureEvidence(ITestResult result) throws IOException {
        boolean failed = result.getStatus() == ITestResult.FAILURE;
        Optional<String> recording = recordLocally
                ? fromDevice("recording stop", () -> ((CanRecordScreen) driver).stopRecordingScreen())
                : Optional.empty();
        if (!failed) {
            return;
        }
        String name = result.getTestClass().getRealClass().getSimpleName() + "." + result.getMethod().getMethodName();
        Optional<byte[]> screenshot = fromDevice("screenshot", () -> driver.getScreenshotAs(OutputType.BYTES));
        Optional<String> pageSource = fromDevice("page source", driver::getPageSource);
        Optional<String> deviceLog = fromDevice("device log", this::deviceLogTail);
        if (screenshot.isPresent()) {
            keep(name, "png", "image/png", screenshot.get());
        }
        if (pageSource.isPresent()) {
            keep(name, "xml", "application/xml", pageSource.get().getBytes(StandardCharsets.UTF_8));
        }
        if (deviceLog.isPresent()) {
            keep(name, "log", "text/plain", deviceLog.get().getBytes(StandardCharsets.UTF_8));
        }
        if (recording.isPresent()) {
            keep(name, "mp4", "video/mp4", Base64.getDecoder().decode(recording.get()));
        }
    }

    private void beginRecording() {
        switch (driver) {
            case AndroidDriver android -> android.startRecordingScreen(new AndroidStartScreenRecordingOptions()
                    .withTimeLimit(RECORDING_LIMIT)
                    .enableForcedRestart());
            case IOSDriver ios -> ios.startRecordingScreen(new IOSStartScreenRecordingOptions()
                    .withTimeLimit(RECORDING_LIMIT));
            default -> throw new IllegalStateException("No recorder for " + driver.getClass().getName());
        }
    }

    private String deviceLogTail() {
        String logType = driver instanceof AndroidDriver ? "logcat" : "syslog";
        List<LogEntry> entries = driver.manage().logs().get(logType).getAll();
        return entries.subList(Math.max(0, entries.size() - LOG_TAIL_LINES), entries.size()).stream()
                .map(LogEntry::toString)
                .collect(Collectors.joining("\n"));
    }

    private void onDevice(String what, Runnable action) {
        fromDevice(what, () -> {
            action.run();
            return Boolean.TRUE;
        });
    }

    private <T> Optional<T> fromDevice(String what, Supplier<T> capture) {
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
