---
name: mobile-project-setup
description: Use when starting a mobile (iOS/Android) test project from zero in Java 21 — Gradle layout, exact pins, Appium 3 server + drivers + emulator setup, capabilities from environment variables, a first smoke run on TestNG + java-client 11. Triggers "scaffold a mobile test project", "set up a Java Appium suite from scratch". Do NOT use for authoring screens or tests (`ui-test-author/appium`) or for device clouds (`device-cloud`).
---

# Mobile Test Project Scaffold (Java 21)

This skill stands up a **runnable Appium 3 test project from zero**: the Gradle layout, exact versions, the local Appium server, drivers and emulator, the capability configuration, and a first smoke run. It owns the **project shell and the environment**. Screen-object and test conventions belong to `ui-test-author/appium`; the compilable project that drops into the layout below is `qa/java/skills/ui-test-author/appium/assets/`, and this skill points at it instead of copying it.

**Version rule:** new projects use Java 21 (17 is the minimum) and Gradle with the Kotlin DSL. An existing Maven project stays on Maven: put the same coordinates in the `pom.xml` and keep the package layout.

## When to use

- A fresh repo with no Java mobile test project, and the user wants iOS or Android coverage.
- The user asks which versions, layout or Appium setup a Java mobile framework should use.

## When NOT to use

- The project exists → author into it with `qa/java/skills/ui-test-author/appium`.
- Real-device clouds (BrowserStack, Sauce, AWS Device Farm) → `qa/java/skills/device-cloud`.
- Web-UI or API scaffolding → the matching `*-project-setup` skill.

## Versions

The table is the **Versions** table of `ui-test-author/appium/SKILL.md`, and `assets/build.gradle.kts` there holds the same pins.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Language | Java toolchain | **21** | `languageVersion.set(JavaLanguageVersion.of(21))`; 17 minimum on a down-level repo |
| Appium client | `io.appium:java-client` | **11.0.0** | Needs Appium 3. W3C `UiAutomator2Options` and `XCUITestOptions` |
| Selenium | `org.seleniumhq.selenium:selenium-support` | **4.51.0** | java-client 11 no longer pulls it in; `WebDriverWait` needs it declared |
| Test runner | `org.testng:testng` | **7.12.0** | |
| Assertions | `org.assertj:assertj-core` | **3.27.7** | |
| Reporting | `io.qameta.allure:allure-testng` | **3.0.0** | The Gradle plugin `io.qameta.allure` 4.3.0 pins the Allure CLI 2.46.1 |
| Appium server | `appium` (npm) | **3.8.0** | Needs Node ^20.19 \|\| ^22.12 \|\| ≥ 24; use **Node 24** (22 is the maintenance lane) |
| Android driver | `appium-uiautomator2-driver` | **8.x** | `appium driver install uiautomator2`. Majors ≥ 5 need Appium 3 |
| iOS driver | `appium-xcuitest-driver` | **12.x** | `appium driver install xcuitest` (macOS + Xcode only). Majors ≥ 10 need Appium 3 |

## Prerequisites

| Need | Check |
|---|---|
| Node 24 (22 supported) and npm | `node --version` |
| JDK 21 | `java --version` |
| Android SDK, with `ANDROID_HOME` pointing at it and `platform-tools` on `PATH` | `echo $ANDROID_HOME` · `adb version` |
| An Android emulator image (a system image plus an AVD) | `avdmanager list avd` |
| Xcode and a simulator runtime, macOS only | `xcrun simctl list devices` |

A **real iOS device** also needs WebDriverAgent signed with a development team. That is a human step in Xcode: Appium cannot do it, and an unsigned WDA is the commonest reason a real-device session never starts. Simulators need none of it.

## Appium 3 server and drivers

```bash
npm install -g appium@3.8.0
appium setup
appium driver list --installed
appium driver doctor uiautomator2
appium driver doctor xcuitest
appium
```

- `appium setup` with no argument is the `mobile` preset: `uiautomator2`, `xcuitest` (on macOS) and `espresso`, plus the `images` and `inspector` plugins. To install only what the suite uses, run `appium driver install uiautomator2` and `appium driver install xcuitest` instead.
- Confirm the installed majors with `appium driver list --installed`: UiAutomator2 **8.x** and XCUITest **12.x** pair with Appium 3.8.0. An older driver in `~/.appium` after an upgrade is a mismatch, not a quirk: run `appium driver update installed`.
- `appium driver doctor <driver>` must come back clean before the first run. Fix what it names (the Android SDK path, `adb`, Xcode command-line tools) rather than skipping it.
- Server feature flags are **scoped** to a driver: `appium --allow-insecure=uiautomator2:adb_shell` or `--allow-insecure=*:session_discovery`. The unscoped form throws on Appium 3. Add a flag only for the feature a test needs; Android WebView tests need `uiautomator2:chromedriver_autodownload`.
- `appium` serves on `:4723`. A test run needs the server and a booted device first; nothing starts them. `appium-mcp` for live exploration carries its own drivers and needs no server, but it does need Node ≥ 22.
- Screen recording needs `ffmpeg` on the Appium host (always on iOS; on Android only for recordings above 180 s). See `qa/java/skills/evidence-capture/references/appium.md`.

## Project layout

```
<product>-mobile-tests/
├── build.gradle.kts                 # assets/build.gradle.kts
├── settings.gradle.kts              # assets/settings.gradle.kts
├── testng.xml                       # assets/testng.xml: parallel="classes", thread-count="1"
├── .gitignore
├── .env.example
├── README.md
└── src/test/java/com/example/mobiletests/
    ├── support/
    │   ├── Env.java                 # the one required-variable reader
    │   ├── AppiumDriverFactory.java # AndroidDriver / IOSDriver from env
    │   └── BaseMobileTest.java      # driver per class, evidence hooks
    ├── pages/
    │   ├── BaseAppiumPage.java      # waits and the test-id finders
    │   ├── LoginPage.java           # the landing screen the smoke verifies
    │   ├── OrdersPage.java
    │   └── OrderRow.java            # scoped component
    └── tests/
        └── OrdersTest.java
```

Copy the eleven asset files into those places, rename the package root `com.example.mobiletests` to the project's group, and update the `<package name>` entry in `testng.xml` to match. `LoginPage`, `OrdersPage`, `OrderRow` and `OrdersTest` are the worked example: replace them with the app's own screens, or delete them and keep the base classes. The Gradle project is a test-only one, so screens live under `src/test/java` beside the tests; a repo that already keeps page objects under `src/main/java` keeps them there. Add `gradle wrapper` output (`gradlew`, `gradle/`) to the repo.

## Capabilities and configuration

**One mechanism:** environment variables, read by `AppiumDriverFactory` through `Env.required`. There are no per-platform properties files, no TestNG parameters for the device and no `-D` flags, and a test never branches on platform: the page's finder does.

| Variable | Used for |
|---|---|
| `PLATFORM` | `android` or `ios`; anything else fails with a message naming the value |
| `DEVICE_NAME` | The emulator AVD / simulator / device name |
| `APP_PATH` | Absolute path to the `.apk`, `.app` or `.ipa` |
| `PLATFORM_VERSION` | iOS only: the simulator or device OS version |
| `APPIUM_URL` | Optional; defaults to `http://127.0.0.1:4723`; a grid or cloud hub URL |
| `E2E_USER`, `E2E_PASSWORD` | The test account the example flow signs in with |
| `E2E_ORDER_NUMBER`, `E2E_ORDER_TITLE` | The seeded data the example test asserts |
| `DEVICE_FARM` | Set on a device cloud: skips the local screen recording |

`.env.example`, committed, with no real values:

```
PLATFORM=android
DEVICE_NAME=Pixel_7_API_34
APP_PATH=/absolute/path/to/app.apk
PLATFORM_VERSION=
APPIUM_URL=http://127.0.0.1:4723
E2E_USER=
E2E_PASSWORD=
E2E_ORDER_NUMBER=
E2E_ORDER_TITLE=
```

Load a local copy with `set -a; source .env; set +a`; CI injects the same names from its secret store. Credentials and the app path never go into source or `build.gradle.kts`.

The Android capabilities set `appium:settings[disableIdLocatorAutocompletion]` to `true`, because Android prefixes every `id` lookup with `<package>:id/` and a React Native or Compose test id has no prefix. A Views app whose ids carry the package turns it off. Check the live page source before choosing (`ui-test-author/appium`, locator ladder).

## `.gitignore`

```
build/
.gradle/
allure-results/
evidence/
.env
```

`build/` covers `build/appium-artifacts/`, where a failed test leaves its screenshot, page source, device log and recording. `allure-results/` and `evidence/` are the report input and any hand-collected captures; none of the three is committed.

## First smoke

The smoke proves the whole chain (server, driver, device, app install, a screen object) before any real test is written. It launches the app and verifies the landing screen.

```java
package com.example.mobiletests.tests;

import com.example.mobiletests.pages.LoginPage;
import com.example.mobiletests.support.BaseMobileTest;
import org.testng.annotations.Test;

public class SmokeTest extends BaseMobileTest {

    @Test(groups = "smoke")
    public void Should_ShowLandingScreen_When_AppLaunches() {
        new LoginPage(driver).verifyPageLoaded();
    }
}
```

`verifyPageLoaded` is the screen object's one assertion: it checks the landing screen's landmark element and names the screen in its failure message, so the smoke needs no assertion of its own. For an app whose landing screen is not a login, replace `LoginPage` with that screen's page object.

## Create and run

```bash
mkdir <product>-mobile-tests && cd <product>-mobile-tests
git init
gradle wrapper --gradle-version 9.6
./gradlew compileTestJava
```

Then, with `appium` running and a device booted (`adb devices` or `xcrun simctl list devices booted` shows it):

```bash
PLATFORM=android DEVICE_NAME=Pixel_7_API_34 APP_PATH=/abs/app.apk ./gradlew test --tests '*SmokeTest'
PLATFORM=ios DEVICE_NAME="iPhone 15" PLATFORM_VERSION=17.4 APP_PATH=/abs/App.app ./gradlew test --tests '*SmokeTest'
./gradlew allureReport
```

The exit gate for the project: it compiles, `appium driver doctor` is clean for each driver in use, and the smoke runs green on one device. The reporting wiring beyond the base test (history, publishing) is `qa-reporting-java`'s.

## Conventions (the shell only)

- **No `Thread.sleep`.** Waits live in `BaseAppiumPage` (`WebDriverWait`); add a new wait there, never inline.
- **Parallelism** is `parallel="classes"` with one driver per test class created in `BaseMobileTest`; the lifecycle uses instance fields, no static mutable state and no `ThreadLocal`. One emulator serves one class at a time, so `thread-count` stays 1 until the suite has more than one device or a cloud grid.
- **Screen objects expose intent, not selectors**; the test id first; the only assertion inside one is `verifyPageLoaded()`.
- **Driver lifecycle** belongs to `AppiumDriverFactory` and `BaseMobileTest`; a test never builds a driver.

## Device clouds, CI and the supported lane

- A device cloud replaces the local server and emulator: set `APPIUM_URL` to the hub, set `DEVICE_FARM`, and follow `qa/java/skills/device-cloud` for the vendor capability block. Confirm the farm runs Appium 3 first.
- The pipeline (emulator job, artifact upload of `build/appium-artifacts/`, Allure publish) is `qa/cicd/java/skills/ci-pipelines`; this skill does not write CI.
- **Supported lane — Appium 2:** a device cloud that still runs Appium 2 needs java-client 10.x, UiAutomator2 4.x and XCUITest 9.x, because java-client 11 and driver majors ≥ 5 / ≥ 10 refuse an Appium 2 server. Keep the Gradle layout and the environment variables; only the coordinates change, and the migration notes live in `ui-test-author/appium`.

## Setup checklist

- [ ] Node 24 (22 supported), JDK 21, `ANDROID_HOME` and an emulator image present; Xcode and a simulator on macOS
- [ ] `appium@3.8.0` installed; UiAutomator2 8.x and XCUITest 12.x listed by `appium driver list --installed`; `appium driver doctor` clean
- [ ] `build.gradle.kts`, `settings.gradle.kts` and `testng.xml` from the assets; `parallel="classes"`
- [ ] `support/`, `pages/`, `tests/` under `src/test/java`; package root renamed in code and in `testng.xml`
- [ ] `AppiumDriverFactory` reads `PLATFORM`, `DEVICE_NAME`, `APP_PATH` (and `PLATFORM_VERSION` on iOS) from the environment — nothing hard-coded
- [ ] `.env.example` committed, `.env` ignored; `.gitignore` takes `build/`, `allure-results/` and `evidence/`
- [ ] `SmokeTest` launches the app and verifies the landing screen
- [ ] `./gradlew compileTestJava` clean; the smoke green on a booted device. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
