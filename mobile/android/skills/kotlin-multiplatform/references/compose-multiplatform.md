# Compose Multiplatform — the opt-in shared-UI lane

Compose Multiplatform (CMP) **1.12.1**; iOS target stable since 1.8. It shares the UI with iOS. That is **not** the default of this lane — shared logic with native UI is.

## Choose it only when

| Condition | Why |
|---|---|
| The product accepts one visual language on both platforms | CMP renders its own pixels on iOS (Skia/Skiko); it is not SwiftUI and does not adopt iOS system controls |
| The team is Kotlin / Compose-first, with little iOS UI skill | The saving is real only if nobody is writing SwiftUI anyway |
| The screens are content / forms / dashboards | System-heavy screens (camera, maps, share sheets, widgets) stay native regardless |
| Accessibility on iOS has been tested with VoiceOver on the real screens | Compose semantics map to iOS accessibility; the result must be proven, not assumed |

If the answer to the first row is "no" — the project follows "platform conventions first" literally — stay with shared logic and SwiftUI over shared ViewModels. The audit does not penalise that choice; it penalises CMP with no recorded decision.

## Setup

```kotlin
plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.kotlin.multiplatform.library)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.compose.multiplatform)
}

kotlin {
    sourceSets {
        commonMain.dependencies {
            implementation(compose.runtime)
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.components.resources)
            implementation(libs.androidx.lifecycle.viewmodel.compose)
        }
    }
}
```

- Two Compose plugins: the Kotlin plugin `org.jetbrains.kotlin.plugin.compose` (compiler) and `org.jetbrains.compose` (the Multiplatform runtime and resources). The Android-only Compose BOM does not govern CMP artifacts; **CMP pins its own Compose version** — align them or the Android side and the shared side drift.
- The iOS entry is `ComposeUIViewController { App() }` in `iosMain`, hosted by the Swift app (`mobile-ios` writes the host).
- **Resources** use the CMP resources library (`Res.string.*`, `Res.drawable.*` in `composeResources/`); Android `R` is not available in `commonMain`. String and plural rules follow [`languages`](../../languages/SKILL.md).

## What CMP changes in the house rules

| Rule | In CMP |
|---|---|
| State: one `uiState`, no ViewModel-to-UI events | Unchanged — KMP ViewModel + `collectAsStateWithLifecycle` (lifecycle-runtime-compose is multiplatform) |
| Test ids | `Modifier.testTag` is shared; `testTagsAsResourceId` is Android-only — on iOS the tag surfaces as an accessibility identifier only where the CMP version maps it. **Verify with a UI test on the simulator**; coordinate with `qa-mobile-*` |
| Accessibility | Semantics are shared; text scaling follows each platform's setting — verify at the largest setting on both |
| Navigation | Use a navigation library that has multiplatform artifacts at the version in use — confirm Navigation 3 / Navigation Compose KMP availability against the CMP release notes before choosing; do not hand-roll |
| Predictive back / edge-to-edge | Android behaviours; the iOS back gesture is the host's. Handle insets through the shared `WindowInsets` APIs, tested on a notched device |
| Previews | Android Studio / IDE previews work in `commonMain` with the preview annotation the version supports |

## Platform seams

A composable that needs a platform widget (a native map, a video player, a date picker) hosts it through `UIKitView` on iOS and `AndroidView` on Android behind an interface — the same shape as [`views-interop`](../../views-interop/SKILL.md), in the other direction. Keep the number of these small; each one is a place the shared UI stops being shared.

## Rules

- A recorded decision precedes CMP; its absence is a finding.
- `commonMain` UI imports no Android `R`, `Context` or `Activity`.
- Platform widgets are hosted behind an interface, not scattered `expect` composables.
- The CMP and the Compose Android versions are verified together in the catalog.

## Verify

- `rg -n "import android\." shared/src/commonMain -g '*.kt'` is empty.
- The app runs on an iOS simulator at the largest text size with VoiceOver on one screen of each type.
