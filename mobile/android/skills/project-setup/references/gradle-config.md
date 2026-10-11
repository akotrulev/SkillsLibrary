# Gradle configuration — AGP 9 reference

Detail for [`mobile-android:project-setup`](../SKILL.md). Check each version against developer.android.com/build/releases/gradle-plugin before writing it.

## `settings.gradle.kts`

```kotlin
pluginManagement {
    repositories {
        google { content { includeGroupByRegex("com\\.android.*|com\\.google.*|androidx.*") } }
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

dependencyResolutionManagement {
    repositoriesMode = RepositoriesMode.FAIL_ON_PROJECT_REPOS
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "MyApp"
include(":app")
```

`FAIL_ON_PROJECT_REPOS` keeps repositories in one place; a module declaring its own is a finding. The foojay version is the one the Gradle docs list for Gradle 9.

## Root `build.gradle.kts`

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
}
```

No `kotlin.android` entry. A KMP or Android library module adds `android.library` (or `com.android.kotlin.multiplatform.library` in [`kotlin-multiplatform`](../../kotlin-multiplatform/SKILL.md)).

## Migrating a module off the old plugin (AGP 8 → 9)

| Old | New |
|---|---|
| `alias(libs.plugins.kotlin.android)` | removed |
| `android { kotlinOptions { jvmTarget = "17" } }` | `kotlin { jvmToolchain(21) }` / `kotlin { compilerOptions { … } }` |
| `kotlin.sourceSets["main"].kotlin.srcDir(…)` | `android.sourceSets.named("main") { kotlin.directories += … }` |
| `kapt(libs.x.compiler)` | `ksp(libs.x.compiler)` |
| `composeOptions { kotlinCompilerExtensionVersion }` | `kotlin.compose` plugin |
| `android.builtInKotlin=false`, `android.newDsl=false` | delete (AGP 10 removes them) |

A module-by-module migration may set the two flags globally and apply `com.android.built-in-kotlin` per module; every such flag carries a dated removal task. The full path is [`migration`](../../migration/SKILL.md).

## Convention plugin (earned on the second module)

```
build-logic/
  settings.gradle.kts            versionCatalogs { create("libs") { from(files("../gradle/libs.versions.toml")) } }
  convention/
    build.gradle.kts             plugins { `kotlin-dsl` }; compileOnly(libs.android.gradlePlugin)
    src/main/kotlin/AndroidLibraryConventionPlugin.kt
```

```kotlin
class AndroidLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        pluginManager.apply("com.android.library")
        extensions.configure<LibraryExtension> {
            compileSdk = 37
            defaultConfig.minSdk = 24
        }
    }
}
```

Register it in `settings.gradle.kts` with `pluginManagement { includeBuild("build-logic") }`. One plugin per repeated block (`android.library`, `android.compose`), never one "god" plugin. `targetSdk` is an app-module setting — a library does not set it.

## R8 keep rules

- Prefer an annotation or a narrow `-keep class com.example.Model { <fields>; }`.
- Every rule in `proguard-rules.pro` has the symptom it fixed in the line above (a `#` comment is the file format's own, not a source comment).
- Library consumer rules go in `consumer-rules.pro` of the module that needs them.
- Verify with the minified release build and a smoke run; an R8 crash on `ClassNotFoundException` / `NoSuchMethodError` means a missing rule, not a reason to disable shrinking.
