# Reaching iOS — framework, Swift export (Alpha), SKIE

This file owns the **Gradle and Kotlin side**. The Xcode project, the Swift Package wiring and every line of Swift calling the framework are `mobile-ios`'s.

## Three ways out

| Mechanism | Status (Kotlin 2.4) | Use |
|---|---|---|
| **Objective-C export framework** | Stable, the default | Shipping apps. `suspend` surfaces as completion handlers / `async` through the Objective-C bridge; `Flow` is a Kotlin type Swift cannot iterate without help |
| **Swift export** | **Alpha** — breaking changes expected | Opt-in per module, retested each Kotlin release. Not the default of any shipping app |
| **SKIE** (Touchlab) | Third party; Kotlin 2.4 support **unconfirmed** at the time of writing | Smooths the Objective-C export (`Flow` → `AsyncSequence`, sealed → enum). Check its changelog against the project's Kotlin before adopting |

## Static framework

```kotlin
kotlin {
    listOf(iosArm64(), iosSimulatorArm64()).forEach {
        it.binaries.framework {
            baseName = "Shared"
            isStatic = true
        }
    }
}
```

- A **static** framework avoids embedding and signing it separately; Xcode's direct integration runs `embedAndSignAppleFrameworkForXcode` as a build phase.
- For distribution to a separate repo or team, an **XCFramework** (`XCFramework("Shared")` in Gradle) is zipped and consumed as a binary Swift Package target. Who owns the `Package.swift` is a decision for the iOS team; this skill produces the artifact.
- Kotlin 2.4 raises the Kotlin/Native minimum to **iOS 15**. A lower deployment target needs `-Xoverride-konan-properties=minVersion.ios=14.0` in the binary's `freeCompilerArgs` — and `mobile-ios` agreeing.
- Kotlin 2.4 can also **import** Swift packages into Gradle (`swiftPMDependencies { swiftPackage(url = …, version = from("…"), products = …) }`) — the inverse direction, for a Kotlin module calling an iOS SDK. Record it as new and check the Kotlin docs for the version used.

## Swift export (Alpha)

```kotlin
kotlin {
    iosArm64()
    iosSimulatorArm64()

    swiftExport {
        moduleName = "Shared"
        flattenPackage = "com.example.shared"
    }
}
```

The Xcode build phase then runs `./gradlew :shared:embedSwiftExportForXcode` instead of `embedAndSignAppleFrameworkForXcode`.

What Kotlin 2.4 documents:

- `suspend` functions export as Swift `async`; `Flow` exports as `AsyncSequence` (default on), consumed with `asAsyncSequence()`.
- Nullability maps directly — no `KotlinInt` boxing.

Known gaps (the page's own list): types inheriting `List` / `Set` / `Map` are ignored on export; generic type parameters erase to their upper bounds; classes must be `final` and inherit from `Any`; `operator` support is limited; direct integration only (not CocoaPods); declarations needing opt-in need a module-level `optIn`.

**Adoption rule.** A decision record names the Kotlin version it was verified on and the owner who retests on each Kotlin bump. An app that cannot afford a release-blocking regression stays on the Objective-C framework.

## The exposed surface

- Expose ViewModels, models, one entry-point factory. Everything else is `internal`.
- Prefer **sealed types and plain data classes** over generics in the exported surface — erased generics and `Flow<T>` element types are where the bridge loses information.
- A `StateFlow` exposed to Swift is observed on the main thread; the iOS side collects it into `@Observable` state ([`mobile-ios-architecture`](../../../../ios/skills/architecture/SKILL.md)).
- Kotlin `Throwable`s do not cross as Swift errors by default; a `@Throws` annotation (Objective-C export) or the repository's `Result` / sealed failure type is how the iOS side sees a failure. Prefer the sealed failure type — the same one [`error-handling`](../../error-handling/SKILL.md) renders on Android.
- Kotlin/Native memory: the default GC in 2.4 is the concurrent mark-and-sweep collector (`kotlin.native.binary.gc=pmcs` switches back); no threading rule is left for application code except the usual one — platform callbacks hop to the right dispatcher.

## Verify

- The framework links for `iosSimulatorArm64`.
- A small Swift test in `iosApp` (owned by `mobile-ios`) calls the exported surface once.
- `rg -n "swiftExport" -g '*.kts'` hits only modules named in the decision record.
