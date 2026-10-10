# Expo Modules API — a local module

Loaded by [`SKILL.md`](../SKILL.md). Verify exact API names against `docs.expo.dev/modules` for the project's SDK before relying on a signature here (§10 rule 3). The Swift sample follows [`mobile-ios-basics`](../../../../ios/skills/basics/SKILL.md), the Kotlin sample [`mobile-android-basics`](../../../../android/skills/basics/SKILL.md). Samples carry no inline comments.

## `expo-module.config.json`

```json
{
  "platforms": ["apple", "android"],
  "apple": { "modules": ["HapticPatternModule"] },
  "android": { "modules": ["expo.modules.hapticpattern.HapticPatternModule"] }
}
```

## Swift

```swift
import ExpoModulesCore
import CoreHaptics

public final class HapticPatternModule: Module {
    private var engine: CHHapticEngine?

    public func definition() -> ModuleDefinition {
        Name("HapticPattern")

        Events("onEngineStopped")

        AsyncFunction("play") { (pattern: [HapticEvent]) async throws in
            let engine = try self.ensureEngine()
            try await engine.start()
            try engine.makePlayer(with: try CHHapticPattern(events: pattern.map(\.coreHapticEvent), parameters: [])).start(atTime: 0)
        }

        OnDestroy {
            self.engine?.stop()
            self.engine = nil
        }
    }

    private func ensureEngine() throws -> CHHapticEngine {
        if let engine { return engine }
        guard CHHapticEngine.capabilitiesForHardware().supportsHaptics else {
            throw HapticsUnavailableException()
        }
        let created = try CHHapticEngine()
        created.stoppedHandler = { [weak self] _ in
            self?.sendEvent("onEngineStopped", [:])
        }
        engine = created
        return created
    }
}

struct HapticEvent: Record {
    @Field var intensity: Double = 1
    @Field var time: Double = 0
}

final class HapticsUnavailableException: Exception {
    override var reason: String { "This device does not support Core Haptics" }
}
```

Notes: `Record` is the typed argument struct; an `Exception` subclass carries the typed error the JS wrapper maps. Keep platform-API glue in the module; extract logic into a plain `struct` a unit test can call.

## Kotlin

```kotlin
package expo.modules.hapticpattern

import android.os.VibrationEffect
import android.os.Vibrator
import expo.modules.kotlin.exception.CodedException
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class HapticPatternModule : Module() {
    private val vibrator: Vibrator
        get() = appContext.reactContext?.getSystemService(Vibrator::class.java)
            ?: throw HapticsUnavailableException()

    override fun definition() = ModuleDefinition {
        Name("HapticPattern")

        AsyncFunction("play") { timings: List<Long> ->
            vibrator.vibrate(VibrationEffect.createWaveform(timings.toLongArray(), -1))
        }

        OnDestroy {
            vibrator.cancel()
        }
    }
}

class HapticsUnavailableException : CodedException("This device cannot vibrate")
```

Notes: `AsyncFunction` runs off the main thread by default on Android; a coroutine form (`AsyncFunction("x") Coroutine { … }`) takes injected dispatchers per the Kotlin standard — never `GlobalScope`. `CodedException` is the typed error.

## TypeScript wrapper — the only public API

```ts
import { requireOptionalNativeModule } from 'expo-modules-core';

type HapticEvent = { intensity: number; time: number };

type HapticPatternNative = {
  play(pattern: HapticEvent[]): Promise<void>;
};

const native = requireOptionalNativeModule<HapticPatternNative>('HapticPattern');

export async function playPattern(pattern: HapticEvent[]): Promise<boolean> {
  if (!native) return false;
  await native.play(pattern);
  return true;
}
```

Return `false` (or a typed unavailable result) when the module is missing — never a fake success. In tests the module is replaced with a fake object through `jest.mock`.

## Native views, events, shared objects

- **View**: `View(MyView.self) { Prop("color") { (view, value: String) in … }; Events("onChange") }` (Swift) / `View(MyView::class) { Prop(...) ; Events(...) }` (Kotlin), wrapped with `requireNativeViewManager`. Give a native view a `testID` / accessibility identifier passthrough ([`test-ids`](../../test-ids/SKILL.md)).
- **Events**: declared with `Events(...)`, sent with `sendEvent`; a listener is added in JS with `addListener` and **removed on unmount**; start native observation in `OnStartObserving`, stop in `OnStopObserving`.
- **Shared objects**: a native object with a JS lifetime (a player, a session) — release in `deallocate`; do not keep a JS reference per row.
- **Lifecycle hooks**: `OnCreate`, `OnDestroy`, `OnActivityEntersForeground` / `OnActivityEntersBackground` — pause hardware in the background.

## Autolinking and builds

A change to a local module needs a rebuild of the development client (`npx expo run:ios` / `run:android`, or an EAS development build); JS-only edits hot-reload. Never ship a changed native module through an OTA update.
