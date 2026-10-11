# Deep-dive details — `qa-device-cloud-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Live-session farm — BrowserStack App Automate (the canonical path)

### 1. App lifecycle — get the build onto the farm, reference it by id

The farm runs *an uploaded build*, never a local file path. Upload the `.apk`/`.aab`/`.ipa` once to the App Automate REST endpoint; you get back a `bs://…` id you put in the `app` capability. Give it a **`custom_id`** so re-uploads under the same id let the `app` cap always pick the latest build — the CI-friendly pattern (build → upload under `custom_id` → tests reference the `custom_id`, no id-plumbing between jobs).

```java
package support.farm;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import okhttp3.*;
import java.io.File;
import java.io.IOException;

public final class AppUploader {
    private static final String UPLOAD_URL = "https://api-cloud.browserstack.com/app-automate/upload";
    private static final Gson GSON = new Gson();
    private final OkHttpClient http = new OkHttpClient();
    private final FarmCredentials.BrowserStack creds;

    public AppUploader(FarmCredentials.BrowserStack creds) { this.creds = creds; }

    public record UploadedApp(String appUrl, String customId) {}

    public UploadedApp upload(File build, String customId) throws IOException {
        RequestBody body = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", build.getName(),
                RequestBody.create(build, MediaType.parse("application/octet-stream")))
            .addFormDataPart("custom_id", customId)
            .build();
        Request request = new Request.Builder()
            .url(UPLOAD_URL)
            .header("Authorization", Credentials.basic(creds.userName(), creds.accessKey()))
            .post(body)
            .build();
        try (Response response = http.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("App upload failed: HTTP " + response.code());
            }
            JsonObject json = GSON.fromJson(response.body().string(), JsonObject.class);
            return new UploadedApp(json.get("app_url").getAsString(), customId);
        }
    }
}
```

> **Reference the app three ways, in order of CI-friendliness:** (1) `custom_id` — `options.setApp("MyApp")` always picks the **last build uploaded under that id** (best for CI: no id passed between jobs); (2) the raw `bs://…` id from a one-off upload; (3) a **public URL** (`-F "url=https://…"` on upload). Apps are **deleted 30 days after last use** — never assume an id is permanent; re-upload in the build job. Don't commit a `bs://…` id as if it were stable.

### 2. Device selection — pin a device, or fan out a matrix

On App Automate every session is a **real device** by default (no emulator flag needed). You pick it with `deviceName` + `osVersion` in `bstack:options`. To run a test across a **device matrix**, drive the device list from a TestNG `@Factory` and a sequential `@DataProvider` — one test-class instance per device, so a failure names the device. (The data-driven mechanics themselves belong to `qa/java/skills/data-driven-testing`; here it's the farm's device list.)

```java
package support.farm;

import org.testng.annotations.DataProvider;

public final class DeviceMatrix {
    private DeviceMatrix() {}

    @DataProvider(name = "devices")
    public static Object[][] devices() {
        return new Object[][] {
            { "Samsung Galaxy S23", "13.0" },
            { "Google Pixel 8",     "14.0" },
            { "Samsung Galaxy S21", "12.0" },
        };
    }
}
```

The provider is **sequential** and feeds a `@Factory`, so each device is one test-class instance with its own fields (D8). A `@DataProvider(parallel = true)` with Appium is banned: it would share one driver field across threads. Fan devices out across CI jobs instead, one device per job (`ci-pipelines`).

> **Pick devices by intent, not "all of them."** A device matrix is for covering the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout) — not for running 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the **plan's session cap**, which `browser-cloud-setup` owns; never fan out past it. A **private/dedicated device pool** (a plan add-on) is selected the same way — the device is just reserved to your org.

### 3. Real-device-only capabilities — the reason a farm exists

These are the features you *cannot* exercise on a local emulator and the core value of a real-device farm. Set the static ones as caps at session start; flip the dynamic ones **mid-session** via the `browserstack_executor` JS hook. Build the driver behind a factory (constructor injection, never a service locator), exactly as `qa/java/skills/ui-test-author/appium` does for local sessions — only the cap block and hub URL change.

```java
package support.farm;

import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;

import java.net.MalformedURLException;
import java.net.URI;
import java.util.HashMap;
import java.util.Map;

public final class RealDeviceDriverFactory {
    private static final String HUB = "https://hub-cloud.browserstack.com/wd/hub";
    private final FarmCredentials.BrowserStack creds;

    public RealDeviceDriverFactory(FarmCredentials.BrowserStack creds) {
        this.creds = creds;
    }

    public AndroidDriver create(String deviceName, String osVersion, String appRef, String sessionName)
            throws MalformedURLException {
        Map<String, Object> bstack = new HashMap<>();
        bstack.put("userName", creds.userName());
        bstack.put("accessKey", creds.accessKey());
        bstack.put("deviceName", deviceName);
        bstack.put("osVersion", osVersion);
        bstack.put("projectName", "checkout-mobile");
        bstack.put("buildName", System.getenv().getOrDefault("BUILD_NAME", "local-build"));
        bstack.put("sessionName", sessionName);
        bstack.put("gpsLocation", "40.730610,-73.935242");
        bstack.put("networkProfile", "4g-lte-advanced-good");
        bstack.put("language", "fr");
        bstack.put("locale", "fr_FR");
        bstack.put("timezone", "Europe/Paris");
        bstack.put("deviceOrientation", "portrait");
        bstack.put("enableBiometric", true);

        UiAutomator2Options options = new UiAutomator2Options()
                .setApp(appRef)
                .setAutoGrantPermissions(true)
                .amend("bstack:options", bstack)
                .amend("appium:settings[disableIdLocatorAutocompletion]", true);

        return new AndroidDriver(URI.create(HUB).toURL(), options);
    }
}
```

On App Automate the device is real by default. `deviceName` and `osVersion` pick it; `gpsLocation` (`"lat,long"`), `networkProfile`, `language`/`locale`/`timezone`, `deviceOrientation` and `enableBiometric` (sensor instrumentation for biometric prompts) are the real-device-only features, set at session start. The app reference is a `bs://…` id or a `custom_id`. The id-prefix setting is for a React Native or Compose app; a Views app whose ids carry the package leaves it off (`ui-test-author/appium`).

Then drive the **dynamic** device features in the test through a small helper. Each is a `browserstack_executor` command (biometric / network) or a standard Appium location call (GPS) — and each must be **awaited on the app's reaction**, never followed by a sleep.

```java
package support.farm;

import com.google.gson.Gson;
import org.openqa.selenium.JavascriptExecutor;

import java.util.Map;

public final class DeviceFeatures {
    private static final Gson GSON = new Gson();

    private DeviceFeatures() {}

    public static void respondToBiometric(JavascriptExecutor driver, boolean match) {
        executor(driver, "performBiometric", Map.of("match", match));
    }

    public static void switchNetworkProfile(JavascriptExecutor driver, String profile) {
        executor(driver, "updateNetworkProfile", Map.of("networkProfile", profile));
    }

    public static void setAndroidLocation(JavascriptExecutor driver, double latitude, double longitude) {
        driver.executeScript("mobile: setGeolocation", Map.of("latitude", latitude, "longitude", longitude));
    }

    public static void setIosLocation(JavascriptExecutor driver, double latitude, double longitude) {
        driver.executeScript("mobile: setSimulatedLocation", Map.of("latitude", latitude, "longitude", longitude));
    }

    private static void executor(JavascriptExecutor driver, String action, Map<String, Object> arguments) {
        driver.executeScript("browserstack_executor: " + GSON.toJson(Map.of("action", action, "arguments", arguments)));
    }
}
```

Biometric and network are `browserstack_executor` commands; GPS is a `mobile:` command with one intent method per platform (Android `mobile: setGeolocation`, iOS `mobile: setSimulatedLocation`). `org.openqa.selenium.html5.Location` and `LocationContext` were removed in Selenium 4.35 and java-client 10 dropped its own location APIs, and in java-client 11 the driver is not a `RemoteWebDriver`, so the helpers take `JavascriptExecutor`. Each call is **awaited on the app's reaction**, never followed by a sleep.

> **The full real-device feature set** (App Automate): `gpsLocation` + mid-session `setLocation`; `networkProfile` (presets like `2g-gprs-good`, `4g-lte-advanced-good`, or a custom bandwidth/latency/loss profile) + mid-session `updateNetworkProfile`; **biometric** via `enableBiometric` (sensor instrumentation injects a mock into the app) + `performBiometric`; `appium:autoGrantPermissions`; `language`/`locale`/`timezone`; `deviceOrientation`; plus camera-image injection, OTP/SIM workflows, and file upload-to-device for richer flows. **iOS** uses `XCUITestOptions` with the same `bstack:options` block (biometric = Touch/Face ID injection). Set static features as caps; flip dynamic ones mid-session.

### 4. Put it together — a real-device test

The test reads like any Appium test from `qa/java/skills/ui-test-author/appium`; only setup wires the farm. Note the assertion **waits on the app's reaction** to the biometric injection (an explicit `WebDriverWait` condition), never a `Thread.sleep`.

```java
package tests;

import io.appium.java_client.android.AndroidDriver;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Factory;
import org.testng.annotations.Test;
import support.farm.DeviceFeatures;
import support.farm.DeviceMatrix;
import support.farm.FarmCredentials;
import support.farm.RealDeviceDriverFactory;

import java.net.MalformedURLException;

import static org.assertj.core.api.Assertions.assertThat;

public class BiometricLoginTest {
    private final String deviceName;
    private final String osVersion;
    private AndroidDriver driver;

    @Factory(dataProvider = "devices", dataProviderClass = DeviceMatrix.class)
    public BiometricLoginTest(String deviceName, String osVersion) {
        this.deviceName = deviceName;
        this.osVersion = osVersion;
    }

    @BeforeClass(alwaysRun = true)
    public void connect() throws MalformedURLException {
        driver = new RealDeviceDriverFactory(FarmCredentials.browserStack())
                .create(deviceName, osVersion, "checkout-app", "biometric-login@" + deviceName);
    }

    @AfterClass(alwaysRun = true)
    public void disconnect() {
        if (driver != null) {
            driver.quit();
        }
    }

    @Test
    public void Should_LogIn_When_BiometricIsApproved() {
        LoginPage login = new LoginPage(driver);
        login.tapBiometricSignIn();
        DeviceFeatures.respondToBiometric(driver, true);

        DashboardPage dashboard = login.awaitDashboard();

        assertThat(dashboard.isLoaded()).as("dashboard shown after approved biometric on %s", deviceName).isTrue();
    }
}
```

> **The driver is per class and quit in `@AfterClass(alwaysRun = true)`; no `try`/`finally` in a test body.** Marking the session pass/fail (`browserstack_executor setSessionStatus`) and attaching the dashboard URL to Allure are `browser-cloud-setup`'s `SessionStatus`; the farm's own video and logs are described in `qa/java/skills/evidence-capture/references/appium.md`. This skill adds the *app/device/feature* setup; the session-result reporting is shared.

---
