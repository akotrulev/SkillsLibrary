---
name: project-setup
description: Use when creating or hardening an Android app on AGP 9 — built-in Kotlin (no kotlin-android plugin), version catalog, explicit targetSdk, compile 37 / target 36 / min 24, JDK 21 toolchain, KSP not kapt, R8 full mode, detekt + ktlint, edge-to-edge, predictive back. Triggers "new Android app", "set up Gradle", "kapt fails on AGP 9". Do NOT use for signing and CI (`mobile-<stack>:release`), state design (`-architecture`) or screens (`-ui-components`).
---

# Android — Project Setup

Stands up a Compose app on the AGP 9 lane with the strictness every project ships on day one: built-in Kotlin, a version catalog, explicit SDK levels, a JDK 21 toolchain, KSP, R8 full mode, a formatter and a linter, a single activity with edge-to-edge and predictive back. Signing, Play upload and CI live in [`mobile/_shared/release`](../../../_shared/release/references/gradle-play.md); the Kotlin standard is [`basics`](../basics/SKILL.md).

## Version lane — detect first

Read `gradle/libs.versions.toml`, `gradle/wrapper/gradle-wrapper.properties`, every `build.gradle(.kts)`, `gradle.properties` and `settings.gradle(.kts)` **before** writing. Never up-level AGP, Kotlin, `compileSdk`, `targetSdk` or `minSdk` as a side effect of setup work.

| Concern | AGP 9.4 / Gradle 9.6 (primary) | AGP 8.x `[AGP8]` (brownfield) |
|---|---|---|
| Kotlin | **Built in** — never apply `org.jetbrains.kotlin.android` / `kotlin-android` | Apply `org.jetbrains.kotlin.android` |
| Kotlin options | `kotlin { compilerOptions { … } }` | `kotlinOptions {}` is deprecated — same `compilerOptions` block |
| Annotation processing | **KSP only.** `kapt` does not work with built-in Kotlin (`com.android.legacy-kapt` is a stop-gap — a migration finding) | KSP; kapt is a finding |
| DSL | New DSL (`android { }` on the stable interfaces) | Old DSL |
| Escape hatches | `android.builtInKotlin=false` + `android.newDsl=false` — **both removed in AGP 10**; a finding wherever present | n/a |
| `targetSdk` | **Set explicitly** — AGP 9 defaults it to `compileSdk` (37), an unreviewed behaviour change | Set explicitly |
| Compose compiler | Plugin `org.jetbrains.kotlin.plugin.compose` (the Kotlin version); strong skipping is default and its flag is an error in 2.4 | Same plugin since Kotlin 2.0 |
| Hilt | Gradle plugin 2.59+ **requires** AGP 9 | Hilt ≤ 2.58 |
| JDK | 21 toolchain | 17 minimum |

| SDK level | Value | Why |
|---|---|---|
| `compileSdk` | **37** | Newest APIs; compiling against it changes nothing at runtime |
| `targetSdk` | **36** | Play requires new apps **and updates** to target API 36 (since 2026-08-31; extensions to 2026-11-01) |
| `minSdk` | **24** | House floor; raise only for a named API need |

Targeting 36 turns on predictive back and ignores orientation / resizability locks on ≥ sw600dp (no opt-out at 37). An existing app that targets 35 keeps working; raising it is [`mobile-android:migration`](../migration/SKILL.md)'s, one level at a time.

## When to use

- Creating an Android app, or hardening one that has only the template's defaults
- "Kapt fails after the AGP upgrade", "which plugin do I apply?", "set up the version catalog"
- Adding detekt / ktlint, R8 full mode, a second module or a convention plugin
- Making the activity edge-to-edge and the back gesture predictive

## When NOT to use

- Signing, Play track upload, CI YAML → `mobile-<stack>:release`, `devops-engineer`
- State ownership, ViewModels, DI → [`architecture`](../architecture/SKILL.md)
- Composables → [`ui-components`](../ui-components/SKILL.md); routes → [`navigation`](../navigation/SKILL.md)
- AGP 8 → 9, kapt → KSP, targetSdk raises → [`migration`](../migration/SKILL.md)
- Baseline Profiles, Macrobenchmark → [`performance`](../performance/SKILL.md)
- Kotlin Multiplatform modules → [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md)
- iOS or React Native setup → `mobile-ios:project-setup`, `mobile-react-native:project-setup`

## Inputs needed

- Application id, flavors / environments, `minSdk` (default 24)
- Single module or several; whether Hilt is wanted (default: manual DI until the app is complex — [`architecture`](../architecture/SKILL.md))
- Greenfield or existing: AGP, Kotlin, Compose BOM already present

## The project

**Greenfield:** Android Studio → *Empty Activity* (Compose), then the sections below in order. **Brownfield:** apply only what is missing, one change per commit, never rename a module or the application id.

```
gradle/libs.versions.toml     the only place a version is written
settings.gradle.kts           pluginManagement, dependencyResolutionManagement, include(":app")
build.gradle.kts              plugins { … apply false }
gradle.properties
app/
  build.gradle.kts
  src/main/{kotlin,res,AndroidManifest.xml}
  src/test  src/androidTest
config/detekt/detekt.yml
.editorconfig                 ktlint settings
```

## AGP 9 — built-in Kotlin, new DSL

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.example.app"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.example.app"
        minSdk = 24
        targetSdk = 36
    }

    buildFeatures { compose = true }
}

kotlin {
    jvmToolchain(21)
    compilerOptions { allWarningsAsErrors = true }
}
```

- **No `kotlin.android` alias anywhere** — module files, root file, catalog. Delete the `kotlin-android` line from `libs.versions.toml`.
- **`kotlin.compose`** is the Kotlin Gradle plugin at the Kotlin version; the old `composeOptions { kotlinCompilerExtensionVersion }` is gone.
- **`jvmTarget` follows `compileOptions.targetCompatibility`**; set the toolchain once with `kotlin { jvmToolchain(21) }` and add the foojay resolver to `settings.gradle.kts` so CI provisions it.
- **`allWarningsAsErrors = true`** from day one in new modules; a brownfield module turns it on after the warning count is zero.
- **Source sets:** `android.sourceSets.named("main") { kotlin.directories += … }` — never `kotlin.sourceSets`. Generated code goes through the variant API.
- **A module with no Kotlin sources** sets `android { enableKotlin = false }`.
- **Never** set `android.builtInKotlin=false` / `android.newDsl=false` to "fix" a build — find the plugin or script still on the old API. Detail: [`references/gradle-config.md`](references/gradle-config.md).

## Version catalog

One `gradle/libs.versions.toml`; every plugin and library is an alias, **no version string in a build file**.

```toml
[versions]
agp = "9.4.0"
kotlin = "2.4.21"
ksp = "<release that supports kotlin 2.4.21>"
composeBom = "2026.09.00"

[libraries]
androidx-compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
androidx-compose-material3 = { module = "androidx.compose.material3:material3" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
```

- **Compose through the BOM** (`implementation(platform(libs.androidx.compose.bom))`), library entries without versions. A Compose artifact with its own version is a finding unless the BOM does not carry it (alpha artifacts — recorded).
- **KSP must support the Kotlin version in use** — read its release notes (github.com/google/ksp/releases) and bump both together; a mismatch is the commonest build error after a Kotlin bump.
- Check the exact AGP and BOM numbers against developer.android.com/build/releases/gradle-plugin when writing — the figures above are the lane, not a pin.
- Catalog `bundles` only for a set always added together; no `Dependencies.kt` buildSrc object beside the catalog.

## KSP, never kapt

Room, Hilt, Moshi codegen and similar use `ksp(...)`. **`kapt` and `kotlin-kapt` are not applied on AGP 9.** A library that only ships a kapt processor is replaced, not bridged; `com.android.legacy-kapt` is allowed only in a brownfield module with a dated reason and a migration task ([`migration`](../migration/SKILL.md)). Room arguments (`room.schemaLocation`) go through `ksp { arg(…) }`.

## JDK 21 toolchain, Gradle

`kotlin { jvmToolchain(21) }` and `org.gradle.java.installations.auto-download=true` (or the foojay resolver). The Gradle wrapper pins **9.6+**; `distributionSha256Sum` is set. Android Studio's Gradle JDK points at the same 21. Robolectric on SDK 36 targets needs JDK 21 ([`unit-testing`](../unit-testing/SKILL.md)).

`gradle.properties`: `org.gradle.jvmargs=-Xmx4g`, `org.gradle.caching=true`, `org.gradle.parallel=true`, `org.gradle.configuration-cache=true`, `android.useAndroidX=true`. A plugin that breaks the configuration cache is fixed or replaced, not a reason to turn it off.

## R8 full mode and release shape

```kotlin
android {
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
```

- **Full mode is the default**; `android.enableR8.fullMode=false` is a finding. AGP 9's R8 is strict about keep rules — a rule that matched by accident now breaks; fix with a **narrow** `-keep` plus `-keepattributes` and a recorded reason, never `-keep class ** { *; }`.
- Reflection users (kotlinx.serialization, Retrofit) ship consumer rules; verify by running the **minified release build**, not debug ([`performance`](../performance/SKILL.md) owns the Baseline Profile).
- Debug builds are never minified in a way that hides crashes from tests; a `benchmark` build type extends release.

## detekt and ktlint

- **ktlint 1.8** formats (the `ktlint-gradle` plugin or the CLI in CI); `.editorconfig` holds `ktlint_code_style = ktlint_official` and `max_line_length = 120`. Compose function naming is allowed by `ktlint_function_naming_ignore_when_annotated_with = Composable`.
- **detekt 1.23.8** is the last stable (2.0 is alpha; Kotlin 2.4 compatibility unverified — check before adopting 2.0). It lints semantics, not whitespace. Commit `config/detekt/detekt.yml` with `buildUponDefaultConfig = true`; turn on `ForbiddenMethodCall` for `println`, `Log.*` (use the project logger) and `GlobalScope`.
- **Android Lint** runs with `warningsAsErrors = true`, `abortOnError = true`, a committed `lint.xml` and a baseline only for pre-existing findings. Add **compose-lints** (`slack-lints`' Compose rules, or the compose-rules ruleset for detekt) for `modifier` order, unstable parameters and `remember` misuse.
- Formatter, detekt and Lint run on the same tree; none auto-fixes in a build phase.

## Single activity, edge-to-edge, predictive back

- **One `MainActivity : ComponentActivity`** hosts the whole Compose tree; no activity per screen. A second activity needs a recorded reason (a separate process, a share target).
- **Edge-to-edge is enforced at target 35**; call `enableEdgeToEdge()` before `super.onCreate` so system-bar styling follows the theme, and handle **insets in composables** — `Scaffold` content padding, `Modifier.windowInsetsPadding(WindowInsets.safeDrawing)`, `imePadding()`. A manual status-bar height or `fitsSystemWindows` hack is a finding. Detail: [`styling`](../styling/SKILL.md).
- **Predictive back is on at target 36.** Declare `android:enableOnBackInvokedCallback="true"` on `<application>` (`[AGP8]`/targets below 36 need it explicitly), and use `BackHandler` / `PredictiveBackHandler` or Navigation's own back handling. Overriding `onBackPressed()` or `KEYCODE_BACK` is a finding. Animation: [`animation`](../animation/SKILL.md).
- Large-screen: no `android:screenOrientation` lock, no `resizeableActivity="false"`, `configChanges` only with a reason — ignored at 36 on ≥ sw600dp anyway.

## Modules and convention plugins — only when earned

- **One `:app` module until a boundary hurts** (build time, a feature being reused, a layering violation). Splitting is [`architecture`](../architecture/SKILL.md)'s decision; this skill only keeps the build files sane.
- **A convention plugin (`build-logic/` included build) appears when two or more modules repeat the same plugin block.** Not before: one module with an `android { }` block is simpler than an included build with a plugin class. Shape in [`references/gradle-config.md`](references/gradle-config.md).
- No `allprojects { }` / `subprojects { }` configuration injection; no `buildSrc` for versions.

## Rules

- No `org.jetbrains.kotlin.android` on AGP 9; KSP only; `android.builtInKotlin=false` is a finding.
- `compileSdk 37` / `targetSdk 36` / `minSdk 24` written explicitly; never raised as a side effect.
- Every version lives in `libs.versions.toml`; Compose via the BOM.
- JDK 21 toolchain declared in Gradle, not assumed from the IDE.
- Release is minified, R8 full mode, keep rules narrow with reasons.
- ktlint + detekt + Lint (with compose-lints) in CI, none auto-fixing in a build.
- One activity; `enableEdgeToEdge()`; insets in composables; back is predictive.
- A convention plugin or module exists only on its second user.

## What NOT to do

- Apply `kotlin-android` "to be safe", or flip the opt-out flags to get a green build.
- Leave `targetSdk` unset because AGP 9 defaults it.
- Hard-code a version in a `build.gradle.kts` or add a `buildSrc` constants object.
- Add `-keep class ** { *; }` or disable R8 to silence a crash.
- Lock orientation, or override `onBackPressed()`.
- Create `:core:common`, `:core:ui`, `:core:model` modules on day one.
- Raise Kotlin, AGP or `targetSdk` while doing unrelated work.

## Validation (exit gate)

- [ ] `rg -n "kotlin.android|kotlin-kapt|kapt\(" -g '*.kts' -g 'libs.versions.toml'` is empty on AGP 9
- [ ] `compileSdk`, `targetSdk`, `minSdk` literal in the module; `jvmToolchain(21)` present
- [ ] No version string in a `build.gradle.kts`; BOM carries Compose
- [ ] Release type: minify + shrink on, no blanket keep rule
- [ ] `.editorconfig`, `detekt.yml`, `lint.xml` committed
- [ ] `enableEdgeToEdge()` and `enableOnBackInvokedCallback` present; no orientation lock

## Handoffs

- State, ViewModels, DI, modules → [`architecture`](../architecture/SKILL.md)
- Kotlin standard → [`basics`](../basics/SKILL.md)
- Signing, Play, CI → `mobile-<stack>:release`
- AGP 8 → 9, kapt → KSP → [`migration`](../migration/SKILL.md)
- Startup and R8 verification → [`performance`](../performance/SKILL.md)
- Dependency and manifest security → `mobile-<stack>:security`
- Test ids → [`test-ids`](../test-ids/SKILL.md)
