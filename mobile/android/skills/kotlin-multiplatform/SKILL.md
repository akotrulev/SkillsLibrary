---
name: mobile-android-kotlin-multiplatform
description: Use when Kotlin code must be shared between Android and iOS — shared logic by default (Room, DataStore, Ktor, kotlinx.serialization, KMP ViewModel, Koin or Metro), the com.android.kotlin.multiplatform.library plugin on AGP 9, the iOS framework and Swift export (alpha), Compose Multiplatform as opt-in shared UI. Triggers "share this with iOS", "set up KMP", "Hilt in a shared module". Do NOT use for the Swift consumer code (`mobile-ios-*`) or Android-only work.
---

# Android — Kotlin Multiplatform

Owns the **KMP lane** of the Android plugin: what to share, how a shared module is built on AGP 9, how it reaches iOS, and when shared UI (Compose Multiplatform) is earned. **Shared logic is the default; shared UI is opt-in.** The Swift that *consumes* the shared module — the Xcode project, SwiftUI views, the Swift Package wiring — is [`mobile-ios`](../../../ios/skills/basics/SKILL.md)'s; this skill produces the framework and states what it exposes. Audit rows are section W of `mobile-android-standards-audit`.

## Version lane

| Concern | Primary (Kotlin 2.4, AGP 9.4) | Notes |
|---|---|---|
| KMP | Stable; Kotlin **2.4.21**, Gradle 9.6 | KGP 2.4 needs AGP ≥ 8.5.2 |
| Android target of a shared module | **`com.android.kotlin.multiplatform.library`** with the `android { }` block inside `kotlin { }` | `androidLibrary { }` is the AGP < 8.12 spelling and deprecated since AGP 9.1 |
| Android app | A separate **`com.android.application`** module | `org.jetbrains.kotlin.multiplatform` combined with `com.android.library` / `com.android.application` is **not allowed** under built-in Kotlin |
| DI | **Koin** (compiler plugin or DSL) or **Metro** | **Hilt and Dagger are Android-only — never in a shared module** |
| iOS bridge | Objective-C export framework (the default) | **Swift export is Alpha in Kotlin 2.4** — breaking changes expected; opt-in per module, never the default for a shipping app |
| Shared UI | Compose Multiplatform **1.12.1**, iOS stable since 1.8 | Opt-in — [`compose-multiplatform`](references/compose-multiplatform.md) |
| Native floor | Kotlin/Native 2.4 raises the iOS minimum to **15.0** | Keep an iOS 14 target only with the documented `-Xoverride-konan-properties` override |

Detect first: an existing `shared` module, its Kotlin version and DI choice are matched, not replaced. A project on AGP 8 keeps `com.android.library` + `kotlin("multiplatform")` until [`migration`](../migration/SKILL.md) moves it.

## When to use

- Deciding whether a piece of logic is shared with an iOS app, and how
- Creating or extending a `shared` / `:core:*` KMP module
- Choosing Koin vs Metro, or finding Hilt / Android types in `commonMain`
- Exposing Kotlin to Swift (framework, XCFramework, Swift export)
- Deciding whether to share the UI

## When NOT to use

- Android-only code, no iOS app → the plain skills ([`architecture`](../architecture/SKILL.md), [`offline-and-storage`](../offline-and-storage/SKILL.md))
- The Swift side: calling the framework, SwiftUI, SPM in Xcode → `mobile-ios-*`
- Moving an AGP 8 / Kotlin-only project to AGP 9 → [`migration`](../migration/SKILL.md)
- A React Native project → `mobile-react-native-*`; this skill does not bridge to JS
- A web / desktop KMP target — out of scope; the lane is Android + iOS

## Inputs needed

1. Does an iOS app exist or is planned — if not, this is not a KMP task
2. What is shared today; the iOS team's willingness to consume a Kotlin framework
3. Kotlin and AGP versions; Koin / Metro / none in place
4. Share logic only, or UI too — default **logic only**

## What to share

| Share (`commonMain`) | Keep native |
|---|---|
| Domain models, validation, formatting rules, business rules | UI (SwiftUI / Compose) unless shared UI is chosen |
| Networking: Ktor 3.6 + kotlinx.serialization | Permissions, camera, location, biometrics, push, deep-link entry |
| Persistence: Room 3 (KSP) / DataStore, `BundledSQLiteDriver` | Secret storage — Keystore (Android), Keychain (iOS) behind an interface the shared code calls |
| Repositories and use cases, `Flow`-based state | Background work — WorkManager is Android-only; BGTaskScheduler on iOS |
| KMP ViewModel (`lifecycle-viewmodel`) exposing one `uiState: StateFlow` | Store compliance, signing, release — [`mobile/_shared`](../../../_shared/store-compliance/SKILL.md) |

Rule of thumb: share what is **identical by specification** (rules, protocol, data shape); do not share what each platform does **differently by convention** (navigation, permissions, system UI). Sharing the ViewModel is sound — the architecture rules ([`architecture`](../architecture/SKILL.md): one `uiState`, no ViewModel-to-UI events, repositories own data) apply unchanged in `commonMain`.

## Module shape

```
shared/                 org.jetbrains.kotlin.multiplatform + com.android.kotlin.multiplatform.library
  src/commonMain/       domain, data, ViewModels
  src/androidMain/      actuals: Keystore, Context-needing code
  src/iosMain/          actuals: Keychain, Darwin engine
  src/commonTest/       fakes + runTest
androidApp/             com.android.application — Activity, Compose UI, DI root
iosApp/                 Xcode project — owned by mobile-ios
```

- **The Android app module cannot be the KMP module.** Extract the app into `androidApp`; `shared` is a library. A `shared` module with several consumers may split by feature later — one module until a second consumer needs the split ([`architecture`](../architecture/SKILL.md) § Modules).
- Library-module Gradle, source sets, test builders and the plugin's limits (single variant, no `BuildConfig`, resources off by default) are in [`references/module-and-gradle.md`](references/module-and-gradle.md).
- `expect` / `actual` is the **last** tool: prefer an interface in `commonMain` implemented in each platform source set and injected. `expect` for a class with one actual per platform and no test seam is a smell; a fake needs the interface.

## Dependency injection

| Choice | Fit |
|---|---|
| **Koin** | Largest KMP user base; DSL, or the Koin Compiler Plugin for compile-time graph checks. A runtime-resolved DSL graph is checked by a test (`verify` / `checkModules`) |
| **Metro** | Compile-time graph (`@DependencyGraph`), Dagger-style scopes, `@ContributesBinding` aggregation; no KAPT / KSP needed. Pin the version from Maven Central — it tracks the Kotlin version |
| **Manual** | An `AppContainer` built per platform root — enough for a small shared module |

- **Hilt is Android-only.** `@HiltViewModel`, `@Inject`-with-Hilt-modules and `@InstallIn` never appear in `commonMain`; an Android-only `androidApp` may still use Hilt for its own UI-layer classes **only if shared classes are provided to it by the KMP graph** — mixing two graphs for one feature is a finding.
- Constructor injection only; no service locator (`Koin.get()` inside a class is a locator, `by inject()` in a ViewModel too). The graph is built at the platform root and handed down.
- State no `object` singletons with mutable state; platform services (clock, id, dispatcher, secure storage) are constructor parameters.

## Persistence and networking in `commonMain`

```kotlin
kotlin {
    sourceSets {
        commonMain.dependencies {
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.serialization.kotlinx.json)
            implementation(libs.androidx.room3.runtime)
            implementation(libs.androidx.datastore.preferences)
            implementation(libs.androidx.lifecycle.viewmodel)
        }
        androidMain.dependencies { implementation(libs.ktor.client.okhttp) }
        iosMain.dependencies { implementation(libs.ktor.client.darwin) }
    }
}
```

- **Ktor**: the engine is the only platform-specific line; timeouts, cancellation, retry rules and ProblemDetails mapping follow [`networking`](../networking/SKILL.md) — the policy does not change, the client does.
- **Room 3** needs a `SQLiteDriver`; in a shared module that is `BundledSQLiteDriver` so SQLite behaves the same on both platforms. KSP runs **per target** (`kspAndroid`, `kspIosArm64`, `kspIosSimulatorArm64`); the database is built from a platform `actual` that supplies the file path. Schema rules and migrations: [`offline-and-storage`](../offline-and-storage/SKILL.md). Confirm the exact KMP builder / constructor annotations against the `androidx.room3` KDoc for the version in use.
- **DataStore** is KMP — the file path is the platform actual.
- **Secrets never live in shared storage.** The shared code calls a `SecretStore` interface; Keystore / Keychain implement it ([`mobile-shared-security`](../../../_shared/security/references/android.md)).

## Reaching iOS

The shared module is built as a static framework and handed to Xcode. The Gradle side is here; the Xcode side and every line of Swift calling it are `mobile-ios`'s. Export surface, `suspend` / `Flow` mapping, Swift export (Alpha) and SKIE are in [`references/ios-and-swift-export.md`](references/ios-and-swift-export.md).

- **Default is the Objective-C export framework.** Swift export is **Alpha in Kotlin 2.4** — it maps `suspend` to `async` and `Flow` to `AsyncSequence`, and still has gaps (generics erased, collection subtypes ignored). Adopt it only on a module the team can re-test each Kotlin release; say so in the decision record.
- **SKIE** (Touchlab) smooths the Objective-C export; its Kotlin 2.4 support was **not confirmed** at the time of writing — check the SKIE changelog against the project's Kotlin version before depending on it.
- Expose a **small, deliberate surface**: ViewModels, models, one entry point. Everything else `internal`.

## Shared UI — opt-in

Compose Multiplatform shares the UI as well. It is chosen deliberately, per project, not as a default: it makes iOS look and behave like Compose, which conflicts with "platform conventions first" unless the product accepts that. Decision criteria, setup and the iOS caveats are in [`references/compose-multiplatform.md`](references/compose-multiplatform.md). Absent that decision, the iOS app is SwiftUI over the shared ViewModels.

## Testing

- Shared logic is tested in `commonTest` with **fakes and `runTest`**, running on JVM (`androidHostTest` / `jvmTest`) and on iOS simulator targets. Turbine is multiplatform.
- `androidHostTest` and `androidDeviceTest` are **opt-in** in the library plugin (`withHostTest`, `withDeviceTest`); nothing runs until enabled.
- The iOS-side behaviour of the framework (the Swift calls) is tested by `mobile-ios`; journeys by the `qa-mobile-*` peers.

## Rules

- Share logic by default; shared UI only by an explicit, recorded decision.
- Hilt and Dagger never in a shared module; Koin or Metro, constructor-injected.
- A shared module on AGP 9 uses `com.android.kotlin.multiplatform.library`; the Android app is its own `com.android.application` module.
- Swift export is labelled **Alpha**; the Objective-C export framework is the shipping default.
- No Android type (`Context`, `Activity`, `Uri`) in `commonMain`; no secrets in shared storage.
- The Swift consumer code is `mobile-ios`'s — this skill does not write it.
- Never raise Kotlin, AGP or an iOS deployment target as a side effect.

## What NOT to do

- Put `@HiltViewModel` or `@Inject` Hilt modules in `commonMain`.
- Apply `com.android.library` or `com.android.application` beside `org.jetbrains.kotlin.multiplatform` on AGP 9.
- Use `androidLibrary { }` on AGP 9, or `kotlin-android` in a shared module.
- Turn on Swift export in a shipping app because it is newer.
- Share the UI because "it is less code" without the product accepting non-native iOS.
- Wrap every platform call in `expect` / `actual` instead of an injected interface.
- Share a navigation graph by hand-rolling a router — navigation stays per platform unless Compose Multiplatform owns the UI.

## Validation (exit gate)

- [ ] `rg -n "dagger|hilt|@Inject" shared/src/commonMain -g '*.kt' -g '*.kts'` is empty
- [ ] `rg -n "android.content|android.app|androidx.activity" shared/src/commonMain -g '*.kt'` is empty
- [ ] The shared module applies the library plugin; the Android app is a separate application module
- [ ] Every shared repository has a `commonTest` test with a fake
- [ ] The framework surface is listed and everything else is `internal`
- [ ] Swift export, if on, is recorded as Alpha with the Kotlin version it was tested on

## Handoffs

- State, ViewModel, DI rules → [`architecture`](../architecture/SKILL.md)
- Client policy → [`networking`](../networking/SKILL.md); storage and sync → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Gradle, catalog, SDK levels → [`project-setup`](../project-setup/SKILL.md)
- Moving to AGP 9 / the library plugin → [`migration`](../migration/SKILL.md)
- Consuming the framework in Swift → `mobile-ios-basics` and `mobile-ios-architecture`
- Test seams and fakes → [`unit-testing`](../unit-testing/SKILL.md)
