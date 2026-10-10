# KMP module and Gradle — AGP 9

Applies to a shared library module on AGP 9.4 / Kotlin 2.4. On AGP 8.x the Android target is `com.android.library` — see [`migration`](../../migration/references/agp8-to-9.md).

## Catalog and root

```toml
[versions]
agp = "9.4.0"
kotlin = "2.4.21"

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
android-kotlin-multiplatform-library = { id = "com.android.kotlin.multiplatform.library", version.ref = "agp" }
kotlin-multiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
```

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.kotlin.multiplatform.library) apply false
    alias(libs.plugins.kotlin.multiplatform) apply false
}
```

## The shared module

```kotlin
plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.kotlin.multiplatform.library)
}

kotlin {
    android {
        namespace = "com.example.shared"
        compileSdk = 37
        minSdk = 24
        withHostTest { isIncludeAndroidResources = true }
    }

    listOf(iosArm64(), iosSimulatorArm64()).forEach {
        it.binaries.framework {
            baseName = "Shared"
            isStatic = true
        }
    }

    sourceSets {
        commonMain.dependencies { }
        commonTest.dependencies { implementation(libs.kotlin.test) }
    }
}
```

- The block is **`android { }` inside `kotlin { }`** — not a top-level `android { }` extension. `androidLibrary { }` is the pre-8.12 name, deprecated since AGP 9.1, to be removed.
- `compileSdk` / `minSdk` follow [`project-setup`](../../project-setup/SKILL.md) (37 / 24). A library module has **no `targetSdk`**.
- The JDK 21 toolchain is set once at the root convention or per module: `kotlin { jvmToolchain(21) }`.
- The default hierarchy template creates `iosMain` over the two iOS targets; do not hand-wire `dependsOn` for it.
- The KMP Gradle plugin and AGP must agree: KGP 2.4 needs AGP ≥ 8.5.2; the library plugin itself needs AGP ≥ 8.10.

## What the library plugin does not do

| Missing | Do instead |
|---|---|
| Build types, product flavors (single variant) | Put variant-dependent code in a standalone `com.android.library` module the `androidMain` source set depends on |
| ViewBinding, data binding | Compose, or a standalone Android library module |
| `externalNativeBuild` (CMake / ndk-build) | KMP C-interop for native targets, or a standalone Android library module |
| `BuildConfig` | A generated Kotlin constants source (BuildKonfig-style), or inject the values |
| Java compilation | `withJava()` if Java sources exist |
| Android resources (`res/`) | `androidResources { enable = true }`; resources in `src/androidMain/res` |
| Unit / instrumented tests | `withHostTest { }` and `withDeviceTest { instrumentationRunner = "…" }` — opt-in; source sets `androidHostTest` / `androidDeviceTest` |
| Consumer R8 rules | `optimization { consumerKeepRules.publish = true; consumerKeepRules.file("consumer-proguard-rules.pro") }` |
| An application | A separate `com.android.application` module |

## The Android app module

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.example.app"
    compileSdk = 37
    defaultConfig {
        minSdk = 24
        targetSdk = 36
    }
}

dependencies {
    implementation(projects.shared)
}
```

Built-in Kotlin means **no `kotlin-android` plugin** in the app module. The Hilt plugin, if the app uses Hilt for its own UI-layer classes, applies here and nowhere under `shared`.

## KSP in a multiplatform module

KSP is configured **per target**, not once:

```kotlin
dependencies {
    add("kspAndroid", libs.androidx.room3.compiler)
    add("kspIosArm64", libs.androidx.room3.compiler)
    add("kspIosSimulatorArm64", libs.androidx.room3.compiler)
}
```

`kapt` does not exist in a multiplatform module. Room's schema directory is `room3 { schemaDirectory("$projectDir/schemas") }` — committed.

## Verify

- `rg -n "com.android.library|com.android.application|kotlin.android|androidLibrary" shared -g '*.kts'` finds none in the shared module.
- The module builds for the host test and `linkDebugFrameworkIosSimulatorArm64` — outside a `Gate: none` task.
