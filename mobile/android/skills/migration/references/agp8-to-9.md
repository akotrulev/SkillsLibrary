# AGP 8 → 9

Source: developer.android.com/build/migrate-to-built-in-kotlin and the AGP release notes. Target: AGP 9.4, Gradle 9.6, Kotlin 2.4, JDK 21.

## Temporary escape hatches — all gone in AGP 10

| Hatch | Where | Allowed only as |
|---|---|---|
| `android.builtInKotlin=false` | `gradle.properties` | A dated bridge while modules migrate one by one |
| `android.newDsl=false` | `gradle.properties` | Required beside the one above (`kotlin-android` is incompatible with the new DSL) — same removal date |
| `com.android.built-in-kotlin` | Module plugin | The per-module opt-in during a module-by-module migration; removed at the end |
| `com.android.legacy-kapt` | Module plugin, same version as AGP | A brownfield module whose processor has no KSP version, with an issue id |

Each use has an issue id and a removal task, and appears in the migration's closing list. The build prints a warning for them; a warning is the reminder, not permission.

## Order inside the move

1. Upgrade Gradle to 9.6 and the JDK toolchain to 21 first; green baseline.
2. Upgrade AGP; read the failures — do not set a hatch yet.
3. Per module, leaves first:
   1. Remove `kotlin-android` (`org.jetbrains.kotlin.android`) from the module, the root `apply false` line and the catalog entry.
   2. Replace `kotlin-kapt` with KSP; `legacy-kapt` only if no KSP processor exists.
   3. Move `android { kotlinOptions { … } }` to `kotlin { compilerOptions { … } }`.
   4. Fix extra Kotlin source dirs.
   5. Set `targetSdk` explicitly.
4. When every module is done, **delete every hatch**. A hatch left in the tree is audit row A6.

## Module-by-module bridge (only when the project is large)

```properties
android.builtInKotlin=false
android.newDsl=false
```

Apply `com.android.built-in-kotlin` (same version as AGP) to the module being migrated, finish it, repeat; after the last module remove both properties and the plugin.

## The edits

`kotlinOptions` to `compilerOptions`:

```kotlin
kotlin {
    compilerOptions {
        languageVersion = org.jetbrains.kotlin.gradle.dsl.KotlinVersion.KOTLIN_2_4
        jvmToolchain(21)
    }
}
```

`jvmTarget` is optional — it defaults to `android.compileOptions.targetCompatibility`. Do not raise `languageVersion` as part of this move unless the project's Kotlin is already there.

Extra Kotlin source directories — one supported form:

```kotlin
android.sourceSets.named("main") {
    kotlin.directories += "additionalSourceDirectory/kotlin"
}
```

`kotlin.sourceSets.named("main") { kotlin.srcDir(…) }` and `java.directories += …` for Kotlin files are **not supported**. A generated directory uses the variant API:

```kotlin
androidComponents.onVariants { variant ->
    variant.sources.kotlin!!.addGeneratedSourceDirectory(taskProvider, OutputProducer::outputDir)
}
```

A module with no Kotlin sources: `android { enableKotlin = false }` removes the Kotlin task and the stdlib dependency.

## Errors you will meet

| Error | Cause | Fix |
|---|---|---|
| `Cannot add extension with name 'kotlin'` | `kotlin-android` still applied | Remove it (step 3.1) |
| `The 'org.jetbrains.kotlin.android' plugin is no longer required` | Same | Same |
| kapt task fails / `kotlin-kapt` incompatible | Built-in Kotlin | KSP, or `legacy-kapt` with a task |
| `Unresolved reference` on `variant.outputs` / `applicationVariants` | Old variant API removed | `androidComponents.onVariants` |
| A release-only crash, missing class | AGP 9's R8 is stricter about keep rules | A **narrow** `-keep` with its reason; never `-keep class ** { *; }` |
| Behaviour change at runtime | `targetSdk` defaulted to `compileSdk` | Set it explicitly (36) — [`target-sdk-behaviour`](target-sdk-behaviour.md) |

## KMP modules

Built-in Kotlin replaces only `kotlin-android`. A shared module moves to `org.jetbrains.kotlin.multiplatform` + **`com.android.kotlin.multiplatform.library`**, with the `android { }` block inside `kotlin { }`; the Android app becomes its own `com.android.application` module — `kotlin.multiplatform` beside `com.android.library` / `com.android.application` is not allowed. Detail: [`kotlin-multiplatform`](../../kotlin-multiplatform/references/module-and-gradle.md).

## Hilt and Room on AGP 9

Hilt Gradle plugin **2.59+** requires AGP 9; Hilt ≤ 2.58 stays on AGP 8. Both Hilt and Room run on KSP. Do not move Hilt to 2.59 and Room to 3 in the same change.

## Verify

- `rg -n "kotlin.android|kotlin-kapt|builtInKotlin|newDsl|legacy-kapt|kotlinOptions" -g '*.kts' -g '*.gradle' -g 'libs.versions.toml' gradle.properties` returns only the dated hatches on the closing list, or nothing.
- `assembleRelease` passes; a release build runs the primary flow.
