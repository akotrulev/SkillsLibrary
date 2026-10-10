---
name: mobile-ios-performance
description: Use when an iOS app hangs, drops frames, launches slowly, leaks memory or ships heavy — Instruments (SwiftUI, Time Profiler, Hangs, Hitches, Allocations, App Launch, Swift Tasks), hang and launch budgets, work off the main actor, SwiftUI body cost, MetricKit by version, app size. Triggers "UI freezes", "scroll jank", "slow cold start". Do NOT use for crash-reporter setup (`mobile-shared-observability`) or animation design (`-animation`).
---

# iOS — Performance

Owns **hangs, hitches, launch, memory and size**. The main thread has a frame budget (16.7 ms at 60 Hz, 8.3 ms at 120 Hz ProMotion) and a **hang threshold: the main thread blocked ≥ 250 ms** — a hang is a correctness failure, not polish (CLAUDE.md § Mobile: the UI thread never blocks). Web analog: [`fe-react-performance`](../../../../frontend/react/skills/performance/SKILL.md) — measure-first and budgets carry over; Core Web Vitals, bundle splitting and RSC do not. Sibling: [`mobile-react-native-performance`](../../../react-native/skills/performance/SKILL.md).

## Version lane

| Concern | Primary (Xcode 27 · iOS 17+) | Notes |
|---|---|---|
| Profiler | Instruments: **SwiftUI**, Time Profiler, **Hangs**, **Animation Hitches**, Allocations, Leaks, **App Launch**, Swift Tasks / Actors | Profile a **release configuration on a real mid-range device**; simulator and debug builds lie |
| Production metrics | **MetricKit** — `[iOS27]` the Swift-first `MetricManager` API with async `metricReports` / `diagnosticReports`; `[iOS ≤ 26]` `MXMetricManager` + `MXMetricManagerSubscriber` | `MXMetricManager` is deprecated at iOS 27.2 (plan §4.2; Apple's wording is unconfirmed — D24). Gate with `#available(iOS 27, *)` and keep the legacy branch while the deployment target is below 27 |
| Field dashboards | Xcode Organizer — launch time, hang rate, memory, disk writes, battery | Per-version, aggregated; console-only evidence |
| Custom intervals | `OSSignposter` (`os.signpost`) | Shows as a lane in Instruments; one subsystem, stable names |
| Isolation | `@MainActor` default in app modules; `@concurrent` for CPU work; `nonisolated` in packages | [`basics`](../basics/SKILL.md) |
| `[iOS16]` / Swift 5 mode | `Task.detached` or a background actor for CPU work where `@concurrent` is unavailable | Never raise the language mode for performance |

Detect first: the deployment target (decides the MetricKit branch), whether a crash reporter already forwards hangs, and any existing signposts or performance test plan — extend, never duplicate.

## When to use

- A freeze, a scroll hitch, a slow screen transition, a slow cold start, rising memory
- Setting budgets; wiring MetricKit; trimming app size
- "Why does this view re-render?", "is this `body` too heavy?"

## When NOT to use

- Crash-reporter and OTel setup, release-health thresholds → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md)
- Animation design and Reduce Motion → [`animation`](../animation/SKILL.md)
- Request timing, retries, cache policy → [`networking`](../networking/SKILL.md)
- List and view authoring → [`ui-components`](../ui-components/SKILL.md)
- Other stacks → `mobile-react-native-performance`, `mobile-android-performance`

## Budgets — set them before measuring

| Budget | Target | Measured with |
|---|---|---|
| Main-thread block | **Under 250 ms always — at or above it is a hang**; interactions feel slow from ~100 ms | Instruments Hangs; Organizer hang rate; MetricKit hang diagnostics |
| Frame | 16.7 ms (60 Hz) / 8.3 ms (120 Hz); a missed deadline is a hitch | Animation Hitches |
| Cold launch | First frame as fast as the product allows; Apple's guidance is under about 400 ms to the first frame — treat as a starting target, not a verified fact | App Launch; Organizer launch time |
| Memory | No unbounded growth across a repeated navigate-and-back loop | Allocations, Leaks, Memory Graph |
| Size | The App Store download size per device, tracked per release | App Store Connect size report |

A budget with no measurement point is a wish. Record the number before and after every change; **no optimisation lands without a before-and-after figure.**

## Keep the main actor free

```swift
@MainActor
@Observable
final class ThumbnailsModel {
    private(set) var images: [Thumbnail] = []

    func load(_ sources: [URL]) async {
        images = await Thumbnailer.render(sources)
    }
}

enum Thumbnailer {
    @concurrent
    static func render(_ sources: [URL]) async -> [Thumbnail] {
        sources.compactMap { Thumbnail(contentsOf: $0) }
    }
}
```

- **Disk, decoding, parsing, image resizing, JSON of any size, Core Data / SwiftData fetches on a large store** run off the main actor — `@concurrent` (Swift 6.2+), a background `@ModelActor`, or a non-isolated async function; results hop back by isolation.
- **A `DispatchSemaphore`, `Thread.sleep`, synchronous `Data(contentsOf:)` or `.wait()` on the main actor is a hang** the day the disk or network is slow.
- **`await` points are not hangs; a long synchronous stretch between them is.** A `for` loop over 10,000 items inside a `@MainActor` method blocks regardless of `async`.
- Check cancellation in long loops (`try Task.checkCancellation()`); the owning view's `.task` cancels it.

## SwiftUI cost — what `body` may do

- **`body` is pure and cheap**: no formatting a large collection, no sorting, no decoding, no `DateFormatter()` creation. Compute in the model, cache the result, or use `FormatStyle` (cached by the system).
- **Observation tracks per property** — a view re-evaluates only for the properties its `body` read. Split a view whose `body` reads many properties of one model into small child views, each reading what it shows. Passing the whole model into every child widens the dependency.
- **Stable identity**: `ForEach(items)` over `Identifiable` with a domain id — never `id: \.self` on non-unique values, never an index. Changing identity destroys and recreates the view and its state.
- **Lazy containers for unbounded data**: `List`, `LazyVStack`, `LazyVGrid`; a `VStack` inside a `ScrollView` over unknown-size data builds every row.
- **Avoid `AnyView`** (defeats diffing) and prefer `@ViewBuilder` / generics; avoid a `GeometryReader` per row.
- Find a re-render with the **SwiftUI instrument** (View Body, View Properties and the cause-and-effect view) before changing code — the cause is usually one widely shared value.
- Images: downsample at load (`CGImageSourceCreateThumbnailAtIndex`, or `AsyncImage` with a sized target); never decode a full-resolution photo to show a 60 pt avatar.

## Launch

- **Do nothing before the first frame that the first frame does not need.** Defer SDK initialisation (analytics, crash reporter beyond the minimum, feature flags) to after the first render; the crash reporter starts first, the rest follow in a `.task` on the root.
- **No synchronous network, file or database work in `App.init` or the root `body`**; load from `.task` and render a skeleton.
- Keep dynamic libraries and static initialisers few; a large `+load`-style static or global initialisation runs before `main`.
- Measure with the **App Launch** template (pre-main vs post-main) and watch the Organizer's launch time per version; a regression is a release-blocker candidate in the review (`mobile-shared-release`).

## Memory

- **Retain cycles in closures**: `[weak self]` for a stored closure on a class; a `Task` stored in a property captures `self` — cancel in `deinit` / `onDisappear`, or capture weakly. Structured `.task` needs no such care.
- Navigate in and out of a screen ten times in Instruments' Allocations (generations) and Memory Graph: leftover instances of the screen's model are the leak.
- Caches use `NSCache` (evicts under pressure), never an unbounded dictionary; respond to `UIApplication.didReceiveMemoryWarningNotification` only for caches you own.
- Memory warnings and **jetsam** kill silently — background work that holds large buffers (video, image batches) streams or chunks.

## MetricKit — production hangs, launches and diagnostics

Subscribe **once**, at app start, and forward to the **same pipeline as the crash reporter** (one reporter — [`mobile-shared-observability`](../../../_shared/observability/references/ios.md)):

```swift
@available(iOS 27, *)
func forwardReports(to telemetry: Telemetry) async {
    for await report in MetricManager.shared.diagnosticReports {
        telemetry.record(diagnostics: report)
    }
}

final class LegacyMetricsSubscriber: NSObject, MXMetricManagerSubscriber {
    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        payloads.forEach { Telemetry.shared.record(legacy: $0) }
    }
}
```

- The iOS 27 form is **tagged `[iOS27]`**; the `MXMetricManager` form is tagged `[iOS ≤ 26]` and is the only branch while the deployment target is below 27. The exact `MetricManager` member names are unconfirmed against Apple's page (D24) — compile against the Xcode 27 SDK before relying on them.
- MetricKit delivers aggregated payloads at most about daily — good for trends and per-version regressions, **not a live rollout gate**. Hang diagnostics carry call-stack trees; symbolicate with the archive's dSYMs (`mobile-shared-release`).
- Payloads are telemetry: strip identifiers before forwarding off-device (`mobile-shared-observability`).

## App size

- Track the per-device download size from App Store Connect for each build; a jump over a threshold set in the release checklist blocks the build.
- Asset catalogs (App Thinning slices per device), compressed image formats, **no duplicate resources across targets**, on-demand resources for rarely used large content, strip debug symbols from the shipped binary (they live in dSYMs).
- Audit third-party SDKs for size before adding; a package that adds megabytes for one helper is a finding. Release builds use whole-module optimisation (the default for Release).

## Rules

- A hang (main thread blocked ≥ 250 ms) is a defect; heavy work runs off the main actor; nothing blocks on a semaphore or a synchronous read.
- `body` is pure and cheap; identity is stable and domain-based; unbounded data sits in a lazy container.
- Nothing needless before the first frame; SDK initialisation deferred except the crash reporter.
- Measure on a release build on a real device before and after; keep the numbers.
- One MetricKit subscription, forwarded to the single crash-reporter pipeline, tagged by version.

## What NOT to do

- No optimisation without a number; no profiling a debug build or a simulator.
- No `DispatchQueue.main.sync`, `Thread.sleep` or `DispatchSemaphore` on the main thread.
- No `AnyView` to silence a type error; no `id: \.self` on non-unique data; no index as identity.
- No second crash or metrics SDK beside MetricKit plus the one reporter.
- No unbounded in-memory cache; no full-resolution decode for a thumbnail.

## Generation steps

1. Reproduce and measure: Instruments on a release build; record the number and the budget it breaks.
2. Find the cause in the right instrument (Hangs → Time Profiler; hitches → SwiftUI; growth → Allocations).
3. Move work off the main actor or narrow the dependency; fix identity; make the container lazy.
4. Re-measure; keep the figure in the change description.
5. Add or confirm the MetricKit forwarding for the deployment target.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Hangs instrument on the changed flow shows no event ≥ 250 ms; Animation Hitches shows no new hitches.
- Ten navigate-and-back cycles leave no extra instances in the Memory Graph.
- A before-and-after launch figure from the App Launch template.
- Dev-side tests for the logic moved off the main actor use injected seams: [`unit-testing`](../unit-testing/SKILL.md); XCTest `measure` / `XCTApplicationLaunchMetric` belong to the XCTest lane named there.

## Handoffs

- Crash reporter, OTel, symbols → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md) · release gates → [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- Views and lists → [`ui-components`](../ui-components/SKILL.md) · state ownership → [`architecture`](../architecture/SKILL.md)
- Background transfers → [`system-integration`](../system-integration/SKILL.md) · persistence cost → [`offline-and-storage`](../offline-and-storage/SKILL.md)
