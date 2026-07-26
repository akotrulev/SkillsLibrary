# Deep-dive details — `qa-device-cloud-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Live-session farm — BrowserStack App Automate (the canonical path)

### 1. App lifecycle — get the build onto the farm, reference it by id

The farm runs *an uploaded build*, never a local file path. Upload the `.apk`/`.aab`/`.ipa` once to the App Automate REST endpoint; you get back a `bs://…` id you put in the `app` capability. Give it a **`custom_id`** so re-uploads under the same id let the `app` cap always pick the latest build — the CI-friendly pattern (build → upload under `custom_id` → tests reference the `custom_id`, no id-plumbing between jobs).

```java
// src/test/java/.../support/farm/AppUploader.java
package support.farm;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import okhttp3.*;
import java.io.File;
import java.io.IOException;

/** Uploads a build to BrowserStack App Automate and returns the bs:// app id. */
public final class AppUploader {
    private static final String UPLOAD_URL = "https://api-cloud.browserstack.com/app-automate/upload";
    private static final Gson GSON = new Gson();
    private final OkHttpClient http = new OkHttpClient();
    private final FarmCredentials.BrowserStack creds;

    public AppUploader(FarmCredentials.BrowserStack creds) { this.creds = creds; }

    public record UploadedApp(String appUrl, String customId) {}

    /** Upload a local build under a custom_id. Re-uploading the same custom_id rotates "latest". */
    public UploadedApp upload(File build, String customId) throws IOException {
        RequestBody body = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", build.getName(),
                RequestBody.create(build, MediaType.parse("application/octet-stream")))
            .addFormDataPart("custom_id", customId)
            .build();
        Request request = new Request.Builder()
            .url(UPLOAD_URL)
            .header("Authorization", Credentials.basic(creds.userName(), creds.accessKey())) // env-sourced, never logged
            .post(body)
            .build();
        try (Response response = http.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("App upload failed: HTTP " + response.code());
            }
            JsonObject json = GSON.fromJson(response.body().string(), JsonObject.class);
            return new UploadedApp(json.get("app_url").getAsString(), customId); // {"app_url":"bs://...","custom_id":...}
        }
    }
}
```

> **Reference the app three ways, in order of CI-friendliness:** (1) `custom_id` — `options.setCapability("appium:app", "MyApp")` always picks the **last build uploaded under that id** (best for CI: no id passed between jobs); (2) the raw `bs://…` id from a one-off upload; (3) a **public URL** (`-F "url=https://…"` on upload). Apps are **deleted 30 days after last use** — never assume an id is permanent; re-upload in the build job. Don't commit a `bs://…` id as if it were stable.

### 2. Device selection — pin a device, or fan out a matrix

On App Automate every session is a **real device** by default (no emulator flag needed). You pick it with `deviceName` + `osVersion` in `bstack:options`. To run a test across a **device matrix**, drive the device list from a TestNG `@DataProvider` — one independent parameterized case per device, so a failure names the device. (The data-driven mechanics themselves belong to `qa/java/skills/data-driven-testing`; here it's the farm's device list.)

```java
// src/test/java/.../support/farm/DeviceMatrix.java
package support.farm;

import org.testng.annotations.DataProvider;

public final class DeviceMatrix {
    private DeviceMatrix() {}

    /** The real-device matrix this suite targets. Keep it small and meaningful, not every device. */
    @DataProvider(name = "devices", parallel = true) // parallel honours the plan cap via thread-count (see browser-cloud-setup)
    public static Object[][] devices() {
        return new Object[][] {
            { "Samsung Galaxy S23", "13.0" },
            { "Google Pixel 8",     "14.0" },
            { "Samsung Galaxy S21", "12.0" },
        };
    }
}
```

> **Pick devices by intent, not "all of them."** A device matrix is for covering the segments that actually differ (a vendor skin, an old OS, a screen size that breaks layout) — not for running 200 devices on every PR. Reserve the broad sweep for nightly. The cap on how many run at once is the **plan's session cap → TestNG `thread-count`**, which `browser-cloud-setup` owns; don't set a thread count here that exceeds it. A **private/dedicated device pool** (a plan add-on) is selected the same way — the device is just reserved to your org.

### 3. Real-device-only capabilities — the reason a farm exists

These are the features you *cannot* exercise on a local emulator and the core value of a real-device farm. Set the static ones as caps at session start; flip the dynamic ones **mid-session** via the `browserstack_executor` JS hook. Build the driver behind a factory (constructor injection, never a service locator), exactly as `qa/java/skills/ui-test-author/appium` does for local sessions — only the cap block and hub URL change.

```java
// src/test/java/.../support/farm/RealDeviceDriverFactory.java
package support.farm;

import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

public final class RealDeviceDriverFactory {
    private static final String HUB = "https://hub-cloud.browserstack.com/wd/hub";
    private final FarmCredentials.BrowserStack creds;

    public RealDeviceDriverFactory(FarmCredentials.BrowserStack creds) { this.creds = creds; }

    /** A real-device Android session with device-only features set up front. */
    public AndroidDriver create(String deviceName, String osVersion, String appRef, String sessionName) throws Exception {
        UiAutomator2Options options = new UiAutomator2Options();
        Map<String, Object> bstack = new HashMap<>();
        bstack.put("userName", creds.userName());
        bstack.put("accessKey", creds.accessKey());
        bstack.put("deviceName", deviceName);          // a REAL device on App Automate
        bstack.put("osVersion", osVersion);
        bstack.put("projectName", "checkout-mobile");
        bstack.put("buildName", System.getenv().getOrDefault("BUILD_NAME", "local-build"));
        bstack.put("sessionName", sessionName);
        // --- real-device-only features ---
        bstack.put("gpsLocation", "40.730610,-73.935242"); // "lat,long" — initial device location
        bstack.put("networkProfile", "4g-lte-advanced-good"); // simulate a network condition
        bstack.put("language", "fr");                   // localized-build testing
        bstack.put("locale", "fr_FR");
        bstack.put("timezone", "Europe/Paris");
        bstack.put("deviceOrientation", "portrait");
        bstack.put("enableBiometric", true);            // sensor instrumentation for biometric prompts
        options.setCapability("bstack:options", bstack);

        options.setCapability("appium:app", appRef);    // bs://… or a custom_id
        options.setCapability("appium:autoGrantPermissions", true); // grant manifest permissions on install

        return new AndroidDriver(new URL(HUB), options);
    }
}
```

Then drive the **dynamic** device features in the test through a small helper. Each is a `browserstack_executor` command (biometric / network) or a standard Appium location call (GPS) — and each must be **awaited on the app's reaction**, never followed by a sleep.

```java
// src/test/java/.../support/farm/DeviceFeatures.java
package support.farm;

import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.html5.Location;
import org.openqa.selenium.remote.RemoteWebDriver;

public final class DeviceFeatures {
    private DeviceFeatures() {}

    /** Answer the next biometric prompt: match=true approves, false rejects. */
    public static void respondToBiometric(JavascriptExecutor driver, boolean match) {
        driver.executeScript(
            "browserstack_executor: {\"action\":\"performBiometric\",\"arguments\":{\"match\":" + match + "}}");
    }

    /** Flip the network condition mid-session (e.g. drop to 2G to test a slow-network path). */
    public static void switchNetworkProfile(JavascriptExecutor driver, String profile) {
        driver.executeScript(
            "browserstack_executor: {\"action\":\"updateNetworkProfile\",\"arguments\":{\"networkProfile\":\"" + profile + "\"}}");
    }

    /** Move the device GPS mid-session via the standard Appium location API. */
    public static void setLocation(RemoteWebDriver driver, double lat, double lon) {
        ((org.openqa.selenium.html5.LocationContext) driver).setLocation(new Location(lat, lon, 0));
    }
}
```

> **The full real-device feature set** (App Automate): `gpsLocation` + mid-session `setLocation`; `networkProfile` (presets like `2g-gprs-good`, `4g-lte-advanced-good`, or a custom bandwidth/latency/loss profile) + mid-session `updateNetworkProfile`; **biometric** via `enableBiometric` (sensor instrumentation injects a mock into the app) + `performBiometric`; `appium:autoGrantPermissions`; `language`/`locale`/`timezone`; `deviceOrientation`; plus camera-image injection, OTP/SIM workflows, and file upload-to-device for richer flows. **iOS** uses `XCUITestOptions` with the same `bstack:options` block (biometric = Touch/Face ID injection). Set static features as caps; flip dynamic ones mid-session.

### 4. Put it together — a real-device test

The test reads like any Appium test from `qa/java/skills/ui-test-author/appium`; only setup wires the farm. Note the assertion **waits on the app's reaction** to the biometric injection (an explicit `WebDriverWait` condition), never a `Thread.sleep`.

```java
// src/test/java/tests/BiometricLoginTest.java
package tests;

import io.appium.java_client.android.AndroidDriver;
import org.openqa.selenium.JavascriptExecutor;
import org.testng.annotations.*;
import support.farm.*;
// page objects from qa/java/skills/ui-test-author/appium

public class BiometricLoginTest {

    @Test(dataProvider = "devices", dataProviderClass = DeviceMatrix.class)
    public void Should_log_in_When_biometric_is_approved(String deviceName, String osVersion) throws Exception {
        AndroidDriver driver = new RealDeviceDriverFactory(FarmCredentials.browserStack())
            .create(deviceName, osVersion, "checkout-app", "biometric-login@" + deviceName); // custom_id app ref
        try {
            LoginPage login = new LoginPage(driver);     // intent-expressing page object, farm-agnostic
            login.tapBiometricSignIn();
            DeviceFeatures.respondToBiometric((JavascriptExecutor) driver, true); // approve the prompt
            DashboardPage dashboard = login.awaitDashboard(); // explicit wait inside the page object — no sleep
            org.testng.Assert.assertTrue(dashboard.isLoaded(), "biometric login should reach the dashboard");
        } finally {
            // session status + dashboard URL are owned by browser-cloud-setup's teardown; reuse it
            driver.quit();
        }
    }
}
```

> **Reuse `browser-cloud-setup`'s teardown**, don't re-invent it: marking the session pass/fail (`browserstack_executor setSessionStatus`) and attaching the dashboard URL to Allure are that skill's job. This skill adds the *app/device/feature* setup; the session-result reporting is shared.

---
