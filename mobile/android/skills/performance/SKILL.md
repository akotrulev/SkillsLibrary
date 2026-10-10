---
name: mobile-android-performance
description: Use when an Android app janks, hangs, launches slowly, hits ANRs or leaks — Baseline and Startup Profiles, Macrobenchmark, AGP 9 R8 keep-rule strictness, App Startup, Android vitals thresholds, Compose recomposition tracing, Perfetto, StrictMode. Triggers "scroll jank", "slow cold start", "ANR rate", "R8 broke release". Do NOT use for crash-reporter setup (`mobile-shared-observability`) or animation design (`-animation`).
---

# Android — Performance

Owns **frames, startup, ANRs, memory and shrinking**. The main thread has a frame budget (16.7 ms at 60 Hz, 8.3 ms at 120 Hz) and Play measures the result: a user-perceived ANR or a slow start lowers store visibility, so a budget is a correctness rule (CLAUDE.md § Mobile: the UI thread never blocks). Web analog: [`fe-react-performance`](../../../../frontend/react/skills/performance/SKILL.md) — measure-first and budgets carry over; Core Web Vitals, bundles and RSC do not. Sibling: [`mobile-ios-performance`](../../../ios/skills/performance/SKILL.md).

## Version lane

| Concern | Primary (AGP 9.4 · Kotlin 2.4 · Compose BOM 2026.09) | Notes |
|---|---|---|
| Profiles | **Baseline Profile** (on-device AOT hints) + **Startup Profile** (`startup-prof.txt`, D8/R8 dex layout) | Plugin `androidx.baselineprofile`; ship both |
| Benchmark | **Macrobenchmark** in a `com.android.test` module (`MacrobenchmarkRule.measureRepeated`) | Needs a profileable, non-debuggable, minified `benchmark` build type; a **real mid-range device**, never an emulator |
| Shrinker | R8 **full mode** (default since AGP 8); **AGP 9 filters global options out of library consumer rules** and is stricter about keep rules | `[AGP8]` same shape; `android.enableR8.fullMode=false` is a finding, not a fix |
| Keep-rule files | `[AGP9.3+]` `src/<variant>/keepRules/*.keep` and the `optimization { enable = true }` DSL | `[AGP9.0–9.2]` / `[AGP8]` `proguard-rules.pro` — match what the project has |
| Tracing | Perfetto / System Trace, `androidx.tracing` sections, Compose tracing (`androidx.compose.runtime:runtime-tracing`) | Debug builds lie; trace the benchmark variant |
| Field metrics | Play Console **Android vitals** (§ Budgets) + Play's startup reporting | Console evidence, not repo-provable |
| `[API35+]` | Edge-to-edge is enforced; large-screen windows resize — re-profile on a tablet | [`styling`](../styling/SKILL.md) |

Detect first: whether a `baselineprofile` / `macrobenchmark` module exists, the shrinker config (`isMinifyEnabled`, keep files), the crash reporter, and any `Application.onCreate` initialisation — extend, never duplicate.

## When to use

- A freeze, an ANR, a scroll hitch, a slow cold start, rising memory, a release build that crashes only when minified
- Setting budgets; adding a Baseline Profile or a Macrobenchmark; trimming APK / AAB size
- "Why does this composable recompose?", "is this `Application.onCreate` too heavy?"

## When NOT to use

- Crash-reporter and OTel setup, release-health thresholds → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md)
- Animation design and the animator duration scale → [`animation`](../animation/SKILL.md)
- Request timing, retries, caching → [`networking`](../networking/SKILL.md)
- Lazy-list authoring, stability, side effects → [`ui-components`](../ui-components/SKILL.md)
- Gradle and R8 baseline setup → [`project-setup`](../project-setup/SKILL.md)
- Other stacks → `mobile-react-native-performance`, `mobile-ios-performance`

## Budgets — set them before measuring

| Budget | Target | Measured with |
|---|---|---|
| Main-thread work | Input answered inside a frame; **no disk, network, database or heavy compute on it** | StrictMode in debug, Perfetto, Macrobenchmark `FrameTimingMetric` |
| **User-perceived ANR** | **0.47 %** of daily sessions (8 % per phone model) — over it lowers store visibility | Android vitals |
| **Crash** | **1.09 %** (8 % per model) | Android vitals; [`mobile-shared-observability`](../../../_shared/observability/SKILL.md) |
| **Slow start** | Bad when cold **≥ 5 s**, warm **≥ 2 s**, hot **≥ 1.5 s** to initial display | Android vitals; `StartupTimingMetric` |
| **Excessive partial wake locks** | **5 %** (enforced since 2026-03-01) | Android vitals; [`system-integration`](../system-integration/SKILL.md) |
| Memory | Memory vitals affect visibility from **Feb 2027**; no unbounded growth across a navigate-and-back loop | Memory Profiler, LeakCanary in debug |
| Size | The Play-reported download size per device, tracked per release | Play Console, `bundletool` |

The thresholds are Google's *bad-behaviour* lines, not goals — set your own tighter budget per screen. A budget with no measurement point is a wish. **No optimisation lands without a before-and-after figure.**

## Keep the main thread free

```kotlin
class ThumbnailsRepository @Inject constructor(
    private val decoder: ThumbnailDecoder,
    @IoDispatcher private val io: CoroutineDispatcher,
) {
    suspend fun load(sources: List<Uri>): List<Thumbnail> = withContext(io) {
        sources.map { source ->
            ensureActive()
            decoder.decode(source)
        }
    }
}
```

- **Disk, decoding, parsing, JSON of any size, database reads on a large store** run on an injected `IoDispatcher`; CPU-heavy work on an injected `DefaultDispatcher`. The function stays **main-safe** — callers never need to know ([`basics`](../basics/SKILL.md)).
- **`runBlocking`, `Thread.sleep`, `Future.get()`, a synchronous `SharedPreferences.commit()` or a `DataStore` `first()` on the main thread is an ANR** the day the disk is slow.
- A long synchronous loop inside a `suspend` function on `Dispatchers.Main` blocks regardless of `suspend`; check `ensureActive()` in long loops so the screen's scope cancels them.
- **A broadcast receiver, `Service.onCreate` or `ContentProvider.onCreate` that does I/O is a startup ANR.** Hand off to WorkManager or a coroutine ([`system-integration`](../system-integration/SKILL.md)).
- **StrictMode in debug builds only**, `penaltyLog()` first and `penaltyDeath()` once clean: `detectDiskReads`, `detectDiskWrites`, `detectNetwork`, `detectLeakedClosableObjects`. Never a permissive policy to silence a violation.

## Compose cost

- **Strong skipping is default** (Kotlin 2.4's Compose compiler): unstable parameters no longer defeat skipping, but a lambda or object created inline each time still changes identity. Check the compiler's stability report before adding `@Stable` / `@Immutable` — a wrong annotation is a stale-UI bug.
- **Read state as late as possible**: pass a lambda (`Modifier.offset { … }`, `graphicsLayer { }`) so scroll or animation state is read in layout/draw, not composition.
- **`derivedStateOf` only for a value that changes less often than its inputs** (a "scrolled past header" boolean), never as a general cache.
- **`remember` the expensive result**, never format a collection, sort or build a `DateFormat` in the composable body; compute in the ViewModel or `produceState`.
- **Lazy lists**: `LazyColumn` with a stable domain `key` and a `contentType` ([`ui-components`](../ui-components/SKILL.md)); a `Column(Modifier.verticalScroll)` over unbounded data composes every row.
- **Find recomposition with Layout Inspector's recomposition counts** and a Perfetto trace with Compose tracing on; count before changing.

## Startup

```kotlin
@get:Rule
val benchmarkRule = MacrobenchmarkRule()

@Test
fun coldStartup() = benchmarkRule.measureRepeated(
    packageName = TARGET_PACKAGE,
    metrics = listOf(StartupTimingMetric()),
    iterations = 10,
    startupMode = StartupMode.COLD,
    compilationMode = CompilationMode.Partial(),
) {
    pressHome()
    startActivityAndWait()
}
```

- **Initialise lazily.** Nothing in `Application.onCreate` that the first frame does not need; move SDKs behind the first frame or a lazy Hilt provider. **Replace `ContentProvider`-based auto-initialisation with App Startup** (`androidx.startup.Initializer`) and give each initialiser a dependency list, or defer it with `tools:node="remove"` plus a manual call.
- **Report full drawing**: `ReportDrawnWhen { state is Loaded }` (or `ReportDrawnAfter`) in Compose, `reportFullyDrawn()` / `FullyDrawnReporter` for background work — it is the only way TTFD exists in the Play and Macrobenchmark data. Never call it before the first frame.
- **Use the `SplashScreen` API** (`androidx.core:core-splashscreen`) — no custom splash `Activity`, which adds a whole activity start to every launch.
- **Cold start is the one to optimise**; it carries warm and hot with it.

### Baseline and Startup Profiles

- **Baseline Profile**: a `BaselineProfileRule().collect(packageName) { … }` generator drives the critical journeys (start, first scroll, the main navigation) with UiAutomator; the Gradle plugin `androidx.baselineprofile` generates it on an unobfuscated, unoptimised variant and R8 rewrites the rules to match the minified release (AGP 8.2+). Output lives in `src/<variant>/generated/baselineProfiles/`. Add `androidx.profileinstaller:profileinstaller` to the app so the profile installs on sideloaded and non-Play builds. **Regenerate on a schedule or per release** — a stale profile still compiles code that no longer matters.
- **Startup Profile** (`startup-prof.txt`): D8 / R8 use it at compile time to lay startup classes into the primary DEX. It needs the obfuscated, optimised release build; mark only the scenarios essential to first display.
- **Macrobenchmark is the proof**: compare `CompilationMode.None()` against `CompilationMode.Partial()` with the profile and record the delta. No profile ships without it.
- Libraries ship their own profiles (plugin 1.2.3+ or AGP 8.3+); an app does not need to profile library code itself.

## R8 in AGP 9 — the release build is a different program

| Rule | Why |
|---|---|
| Test the **minified release build** (or the `benchmark` type) before every release, never only debug | Reflection users — kotlinx.serialization, Retrofit, Room's generated code, Hilt entry points — ship consumer rules; an app's own reflective code needs its own |
| Narrow `-keep` over blanket rules; **never `-keep class ** { *; }`** | Defeats shrinking and obfuscation and hides the real gap |
| Global options (`-dontobfuscate`, `-dontoptimize`, `-allowaccessmodification`) belong in the **app's** rules, not a library's consumer file | AGP 9 filters global options out of library consumer rules |
| Keep an annotated member set (`-keepclassmembers class * { @pkg.Keep *; }`) rather than a package | Survives refactors; `-keepclassmembers` alone does not keep the owning class — pair it with `-keep` or `-keepclasseswithmembers` (**built but unverified** against the R8 pages for the AGP in use) |
| Upload the **mapping file** with every release | Obfuscated crashes need retracing — [`mobile-shared-release`](../../../_shared/release/SKILL.md) |
| `[AGP9.3+]` Use the R8 Configuration Analyzer to find the broadest rules that block optimisation | Narrow them one at a time |

`isMinifyEnabled = true` and `isShrinkResources = true` on release, `proguard-android-optimize.txt` as the default file; a release with `isMinifyEnabled = false` is a size and startup finding.

## Memory and size

- Leaks: a `Context` / `Activity` held by a singleton, a `ViewModel` or a coroutine launched in an unowned scope; an unremoved listener; a `Bitmap` held past its screen. **LeakCanary in debug builds**; the Memory Profiler heap dump after a repeated navigate-and-back loop is the proof.
- Images: a loader with downsampling (Coil) at the displayed size, never a full-resolution bitmap in a list.
- Size: AAB with R8 + resource shrinking, `resourceConfigurations` / language splits, WebP or vector assets, no unused ABIs; **16 KB page size** alignment is a Play requirement ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)).
- Wake locks and background work are measured by vitals: prefer WorkManager, release every `WakeLock`, and use a timeout on `acquire`.

## Rules

- Budgets stated with their measurement point; a before-and-after figure for every optimisation.
- Nothing blocking on the main thread; dispatchers injected; long loops check cancellation.
- Compose state read late; `remember` for expensive results; lazy lists with `key` / `contentType`.
- Lazy initialisation; App Startup instead of provider initialisation; `reportFullyDrawn` wired.
- Baseline + Startup Profiles generated by the plugin and proven by a Macrobenchmark on a real device.
- Release is minified and shrunk with narrow keep rules; the minified build is exercised before release; the mapping file is uploaded.

## What NOT to do

- No profiling on an emulator or a debug build; no optimisation without a number.
- No `runBlocking`, `Thread.sleep` or synchronous I/O on the main thread; no permissive StrictMode.
- No `@Stable` / `@Immutable` to silence a report without checking the type is stable.
- No `-keep class ** { *; }`; no `android.enableR8.fullMode=false` as a fix.
- No work in `Application.onCreate` the first frame does not need; no custom splash activity.
- No hand-edited `baseline-prof.txt` for generated rules; no stale profile shipped across a large refactor.

## Generation steps

1. Read the existing build types, shrinker files, `Application` class, profile and benchmark modules; match them.
2. Record the baseline: cold-start and frame timing from a Macrobenchmark on a real device, vitals from the console.
3. Move blocking work off the main thread; defer initialisation; wire `ReportDrawn*`.
4. Add the Baseline / Startup Profile generator and the benchmark module only if absent; measure the delta.
5. Run the minified build; fix R8 gaps with the narrowest keep rule.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- `./gradlew :macrobenchmark:connectedCheck` on a physical device: cold start and `FrameTimingMetric` before and after; the profile variant is faster than `CompilationMode.None()`.
- Debug run with StrictMode penalties on: no disk, network or leaked-closable violation on the launch path.
- The minified release (or `benchmark`) build: launch, sign in, one list, one write — no `ClassNotFoundException`, no missing-serializer crash.
- A navigate-and-back loop in the Memory Profiler: heap returns to a plateau; LeakCanary is silent.
- Dev-side tests of any logic split out for speed: [`unit-testing`](../unit-testing/SKILL.md).

## Handoffs

- Crash reporter, vitals thresholds that halt a rollout → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md) · [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- Gradle, R8 baseline, version catalog → [`project-setup`](../project-setup/SKILL.md) · lazy lists, stability → [`ui-components`](../ui-components/SKILL.md)
- Wake locks, foreground services → [`system-integration`](../system-integration/SKILL.md) · jank in animation → [`animation`](../animation/SKILL.md)
- Device journeys under load → `qa-mobile-<stack>` (peer)
