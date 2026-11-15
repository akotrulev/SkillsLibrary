---
name: desktop-project-setup
description: Use when starting a desktop E2E project in Java (TestNG, java-client 11, Appium 3, Mac2, WinCore). Triggers "scaffold a desktop test project". Not for writing tests (desktop-window-objects).
---

# Desktop Test Project Scaffold (Java 21)

Stands up a **runnable Appium 3 desktop test project from zero**: the Gradle layout, exact versions, the Appium server, the pinned Mac2 and WinCore drivers, OS prerequisites, the env-driven options and a first smoke run. It owns the **project shell and the environment**. The shared rules (drivers, the test-id contract, CI hosts) are `qa/_shared/desktop-testing`; load it first. The mobile twin is `qa/java/skills/mobile-project-setup`, whose assets (`build.gradle.kts`, `settings.gradle.kts`, `Env.java`, `testng.xml`) in `qa/java/skills/ui-test-author/appium/assets/` this skill reuses rather than copies.

**Version rule:** Java 21 (17 minimum), Gradle Kotlin DSL for new projects; an existing Maven project stays on Maven with the same coordinates. Electron and Tauri apps are out of scope.

## When to use

- A fresh repo with no Java desktop test project and a native macOS or Windows app to cover.
- The user asks which versions, drivers or OS setup a Java desktop suite needs.

## When NOT to use

- The project exists → `qa/java/skills/desktop-window-objects`, and `qa/java/skills/ui-test-author/appium` for the TestNG conventions.
- Mobile apps → `qa/java/skills/mobile-project-setup`. Browser UI → `qa/java/skills/ui-test-author`.
- A device cloud for desktop: none exists, see `qa/_shared/desktop-testing`.
- TypeScript / .NET → `qa/typescript/skills/desktop-project-setup` / `qa/dotnet/skills/desktop-project-setup`.

## Versions

Verified 2026-11-15; the Java pins are those of `mobile-project-setup` and `tools/qa-version-check.py`.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Language | Java toolchain | **21** | 17 minimum on a down-level repo |
| Appium client | `io.appium:java-client` | **11.0.0** | Needs Appium 3. `Mac2Driver` and `Mac2Options` in `io.appium.java_client.mac`; `WindowsDriver` and `WindowsOptions` in `io.appium.java_client.windows` |
| Selenium | `org.seleniumhq.selenium:selenium-support` | **4.51.0** | Declared explicitly: java-client 11 no longer pulls it in |
| Test runner | `org.testng:testng` | **7.12.0** | |
| Assertions | `org.assertj:assertj-core` | **3.27.7** | |
| Reporting | `io.qameta.allure:allure-testng` | **3.0.0** | Gradle plugin `io.qameta.allure` 4.3.0 |
| Appium server | `appium` (npm) | **3.8.0** | Latest is 3.9.1; not moved here. Node 24 (22 maintenance) |
| macOS driver | `appium-mac2-driver` | **4.6.1** | Peer `appium ^3.0.0-rc.2`: includes 3.8.0. 5.x needs Appium 4 |
| Windows driver | `appium-wincore-driver` | **3.3.2** | Peer `appium ^3.0.0-rc.2`: includes 3.8.0. 4.x needs Appium 4 |
| Windows fallback | `appium-novawindows-driver` | **1.5.0** | Same `AutomationId` contract |

**From 4.0 GA:** Appium 4 with Mac2 5.x and WinCore 4.x. Appium 4 is in beta with no GA date; do not scaffold on it.

## Prerequisites

| Host | Need | Check |
|---|---|---|
| Both | JDK 21, Node 24 (22) and npm | `java --version` · `node --version` |
| macOS | macOS 11.3+, **Xcode 13+** with command-line tools, the app built and installed | `xcodebuild -version` |
| macOS | **Xcode Helper** granted the Accessibility permission (System Settings → Privacy & Security → Accessibility) | a human step |
| macOS | `sudo automationmodetool enable-automationmode-without-authentication`, to silence the automation-mode prompt | a human step; `sudo` cannot run unattended |
| macOS | `WebDriverAgentRunner-Runner.app` granted Accessibility, **only** for moving or resizing windows. The grant is lost on every ad-hoc WDA rebuild unless WDA is signed with a stable identity | `appium driver run mac2 setup-accessibility` may script it |
| Windows | Windows 10 or later, the app built or installed (exe path or UWP AUMID) | |
| Windows | An **interactive session with autologon**: the runner is a process, not a service | see `qa/_shared/desktop-testing` § CI and hosts |

A headless Mac or a disconnected RDP session is the commonest reason a desktop session never starts or clicks land nowhere. Both permissions are human steps: report them, never skip them.

## Appium 3 server and drivers

Install **only the driver for the host**, with an explicit version, once per machine:

```bash
npm install -g appium@3.8.0
appium driver install mac2@4.6.1
appium driver install --source=npm appium-wincore-driver@3.3.2
appium driver list --installed
appium driver doctor mac2
appium
```

- Run the second line on a Mac, the third on Windows. **Never an unpinned `appium driver install mac2`**: it may resolve to a major that needs Appium 4.
- `appium driver list --installed` must show `mac2@4.6.1` or `wincore@3.3.2`. Anything else is a mismatch; `appium driver update` is the wrong fix because it can cross a major.
- `appium driver doctor mac2` must come back clean before the first run. WinCore has no doctor check; its proof is the smoke run.
- Fallback when WinCore misbehaves on a legacy app: `appium driver install --source=npm appium-novawindows-driver@1.5.0` and `automationName` `NovaWindows`. Locators do not change. Record why in the README.
- The legacy Appium Windows driver and WinAppDriver are never installed (D9).
- Feature flags are scoped, `--allow-insecure=mac2:<feature>`; add one only for the feature a test needs.
- `appium` serves on `:4723`. Nothing starts it for the run: start it first, or let the CI job do so.

## Project layout

```
<product>-desktop-tests/
├── build.gradle.kts                 # ui-test-author/appium/assets/build.gradle.kts
├── settings.gradle.kts              # assets/settings.gradle.kts
├── testng.xml                       # assets/testng.xml, renamed: parallel="classes", thread-count="1"
├── .gitignore
├── .env.example
├── README.md
└── src/test/java/com/example/desktoptests/
    ├── support/
    │   ├── Env.java                 # assets/Env.java: the one required-variable reader
    │   ├── DesktopDriverFactory.java# Mac2Driver / WindowsDriver from env
    │   └── BaseDesktopTest.java     # driver per class, evidence hooks
    ├── windows/
    │   ├── BaseWindow.java          # waits and the test-id finders
    │   ├── LibraryWindow.java       # the landing window the smoke verifies
    │   └── AlbumRow.java            # scoped component
    └── tests/
        └── SmokeTest.java
```

Copy `build.gradle.kts`, `settings.gradle.kts`, `Env.java` and `testng.xml` from the mobile assets, rename the package root `com.example.mobiletests` to `com.example.desktoptests` (or the project's group) and the `<package name>` entry in `testng.xml` to match. The window classes are written with `desktop-window-objects`. A repo that keeps window objects under `src/main/java` keeps them there. Add the `gradle wrapper` output.

## Options and configuration

**One mechanism:** environment variables read by `DesktopDriverFactory` through `Env.required`. `PLATFORM` picks the driver; there are no per-platform properties files and a test never branches on platform: the window object's locator map does.

| Variable | Used for |
|---|---|
| `PLATFORM` | `macos` or `windows`; anything else fails naming the value |
| `APP_ID` | macOS: the bundle id. Windows: the exe path or the UWP AUMID |
| `APP_ARGUMENTS` | Optional launch arguments (a test data folder, a feature flag) |
| `APPIUM_URL` | Optional; defaults to `http://127.0.0.1:4723` |
| `E2E_USER`, `E2E_PASSWORD` | The test account the example flow signs in with |

```java
package com.example.desktoptests.support;

import io.appium.java_client.AppiumDriver;
import io.appium.java_client.mac.Mac2Driver;
import io.appium.java_client.mac.options.Mac2Options;
import io.appium.java_client.windows.WindowsDriver;
import io.appium.java_client.windows.options.WindowsOptions;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URL;
import java.util.List;
import java.util.Optional;

public final class DesktopDriverFactory {
    private static final String DEFAULT_SERVER_URL = "http://127.0.0.1:4723";
    private static final String WINCORE = "Wincore";
    private static final int APP_LAUNCH_WAIT_SECONDS = 30;

    private DesktopDriverFactory() {
    }

    public static AppiumDriver create() throws MalformedURLException {
        URL server = URI.create(System.getenv().getOrDefault("APPIUM_URL", DEFAULT_SERVER_URL)).toURL();
        String platform = Env.required("PLATFORM");
        return switch (platform) {
            case "macos" -> new Mac2Driver(server, macOptions());
            case "windows" -> new WindowsDriver(server, windowsOptions());
            default -> throw new IllegalArgumentException("PLATFORM must be macos or windows, got " + platform);
        };
    }

    private static Mac2Options macOptions() {
        Mac2Options options = new Mac2Options().setBundleId(Env.required("APP_ID"));
        launchArguments().ifPresent(options::setArguments);
        return options;
    }

    private static WindowsOptions windowsOptions() {
        WindowsOptions options = new WindowsOptions().setApp(Env.required("APP_ID"));
        options.setAutomationName(WINCORE);
        options.amend("appium:ms:waitForAppLaunch", APP_LAUNCH_WAIT_SECONDS);
        launchArguments().ifPresent(args -> options.amend("appium:appArguments", String.join(" ", args)));
        return options;
    }

    private static Optional<List<String>> launchArguments() {
        String raw = System.getenv("APP_ARGUMENTS");
        return raw == null || raw.isBlank() ? Optional.empty() : Optional.of(List.of(raw.split(" ")));
    }
}
```

- **`WindowsOptions` hard-sets `automationName` to `Windows`**, the legacy driver this library never uses. The factory overrides it to `Wincore` (`NovaWindows` for the fallback); `BaseOptions` with `setPlatformName("Windows")` works too. Check the session's returned capabilities in the smoke run.
- `setBundleId` is mandatory on Mac2: the default app is Finder. Capability keys carry the `appium:` prefix except `platformName`; `amend` takes the prefixed name.
- **Not compiled here:** the `Mac2Options` setter names (`setBundleId`, `setArguments`) and `WindowsOptions.setApp` come from the java-client package layout, not from a build. A compile error is the signal to read the class in the IDE and fix the setter, not to fall back to string keys everywhere.
- A session starts a fresh app by default. Keep state only deliberately: `appium:noReset` `true` (Mac2) or `appium:shouldCloseApp` `false` (WinCore), via `amend`.
- **`thread-count="1"` and `parallel="classes"`.** Mac2 runs one session at a time and a new session ends the old one; Windows focus is exclusive. Parallelism is more machines, never more threads.
- `BaseDesktopTest` creates the driver in `@BeforeClass` and quits it in `@AfterClass` (instance fields, no `ThreadLocal`, no static mutable state). Evidence on failure (screenshot and page source into `build/appium-artifacts/<test>/`) comes from one `@AfterMethod` that takes `driver.getScreenshotAs` and `driver.getPageSource()`; model it on `BaseMobileTest` and drop the device-log and recording parts.

`.env.example`, committed, with no real values:

```
PLATFORM=macos
APP_ID=com.example.Library
APP_ARGUMENTS=
APPIUM_URL=http://127.0.0.1:4723
E2E_USER=
E2E_PASSWORD=
```

Load a local copy with `set -a; source .env; set +a`; CI injects the same names from its secret store. Credentials and the app path never go into source or `build.gradle.kts`.

## `.gitignore`

```
build/
.gradle/
allure-results/
.env
```

## First smoke

The smoke proves the chain (server, driver, permissions, app launch, a window object) before any real test is written.

```java
package com.example.desktoptests.tests;

import com.example.desktoptests.support.BaseDesktopTest;
import com.example.desktoptests.windows.LibraryWindow;
import org.testng.annotations.Test;

public class SmokeTest extends BaseDesktopTest {

    @Test(groups = "smoke")
    public void Should_ShowLibraryWindow_When_AppLaunches() {
        new LibraryWindow(driver).verifyWindowLoaded();
    }
}
```

`verifyWindowLoaded` checks one landmark container id and names the window in its failure message. Run it with the app installed and `appium` serving:

```bash
PLATFORM=macos APP_ID=com.example.Library ./gradlew test --tests '*SmokeTest'
PLATFORM=windows APP_ID='C:\Apps\Library\Library.exe' ./gradlew test --tests '*SmokeTest'
./gradlew allureReport
```

The exit gate: it compiles, the driver is listed at its pinned version, `appium driver doctor mac2` is clean (macOS), and the smoke is green on one host.

## CI

Desktop E2E runs on **owned hardware**: a self-hosted Windows agent in an interactive autologon session (Microsoft-hosted Azure agents do not support visible UI tests), and a Mac with Xcode and the permissions above. No device cloud runs native desktop apps. The pipeline is `qa/cicd/java/skills/ci-pipelines`; this skill does not write CI.

## Setup checklist

- [ ] JDK 21, Node 24 (22); Xcode and the two Accessibility grants on macOS, an interactive autologon session on Windows
- [ ] `build.gradle.kts` pins `java-client` 11.0.0, TestNG 7.12.0; `appium` 3.8.0 installed
- [ ] `appium driver list --installed` shows `mac2@4.6.1` or `wincore@3.3.2`; no unpinned install
- [ ] `DesktopDriverFactory` reads `PLATFORM` and `APP_ID` from the environment; `WindowsOptions` automation name overridden; `thread-count="1"`
- [ ] `.env.example` committed, `.env` ignored
- [ ] `SmokeTest` launches the app and verifies the landing window
- [ ] `./gradlew compileTestJava` clean; the smoke green on the host

## Handoffs

- Window discovery → `qa/java/skills/desktop-screen-explorer`; the window object classes → `qa/java/skills/desktop-window-objects`
- TestNG spec conventions → `qa/java/skills/ui-test-author/appium`
- Shared rules and CI facts → `qa/_shared/desktop-testing`
- TypeScript / .NET siblings → `qa/typescript/skills/desktop-project-setup` / `qa/dotnet/skills/desktop-project-setup`
