---
name: performance
description: Use when a Mac app hangs (beach ball), drops frames, launches slowly or leaks (Instruments, MetricKit). Triggers "beach ball on big Table". Not for crash reporting (observability).
---

# macOS: Performance

Owns **hangs, hitches, launch, memory, large data and energy** on the Mac. The main thread has a frame budget (16.7 ms at 60 Hz, 8.3 ms at 120 Hz on ProMotion displays) and a **hang threshold: the main run loop busy for more than 250 ms**, where macOS shows the spinning wait cursor. A hang is a correctness failure, not polish (CLAUDE.md § Desktop code rules: the UI thread never blocks). Web analog: [`fe-react:performance`](../../../../frontend/react/skills/performance/SKILL.md): measure-first and budgets carry over; Core Web Vitals and bundle splitting do not. Sibling: [`mobile-ios:performance`](../../../../mobile/ios/skills/performance/SKILL.md) (the same main-actor and `body` rules; the Mac adds big tables, several windows, background apps and Activity Monitor). Audit rows are section N of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary (Xcode 27 · macOS 14+) | Notes |
|---|---|---|
| Profiler | Instruments: **SwiftUI**, Time Profiler, **Hangs**, **Animation Hitches**, Allocations, Leaks, **App Launch**, **Swift Tasks / Executors** (Xcode 27: Main Actor and the cooperative pool), **Energy Log**, unified **System Trace** | Profile a **release build on Apple silicon at the lowest supported spec**; debug builds lie. `xctrace record` drives it from a script |
| Production metrics | **MetricKit exists on macOS 12+**; diagnostics arrive immediately on macOS 12+ (metric payloads at most about daily). `[mac27SDK]` the Swift-first `MetricManager` with async `metricReports` / `diagnosticReports`; `[mac ≤ 26]` `MXMetricManager` + `MXMetricManagerSubscriber` | Checked 2026-11-15: Apple's hang-diagnostics page lists macOS 12.0 as the minimum (metadata "12.0 - 27.2.0", meaning unconfirmed). Compile against the 27 SDK before relying on the new member names; keep the legacy branch while the deployment target is below 27 |
| Field dashboards | Xcode Organizer: crashes, hangs, disk writes, launch (Developer ID builds report only where the user shares analytics) | Per version, aggregated |
| Custom intervals | `OSSignposter`, one subsystem, stable names | A lane in Instruments |
| Isolation | `@MainActor` default in app modules; `@concurrent` for CPU work; `nonisolated` in packages | [`basics`](../basics/SKILL.md) |
| `[mac13]` / Swift 5 mode | `Task.detached` or a background actor where `@concurrent` is unavailable | Never raise the language mode for performance |

Detect first: the deployment target (decides the MetricKit branch), whether a crash reporter already forwards hangs, and any signposts or performance test plan; extend, never duplicate. Sentry on macOS has **no automatic app-start or screen-load transactions**: launch is measured with Instruments and signposts, not assumed from the reporter.

## When to use

- A beach ball, a scroll hitch, a slow window open, a slow cold start, rising memory, high energy impact
- A `Table` or `List` with thousands of rows
- Setting budgets; wiring MetricKit; trimming app size
- "Why does this view re-render?", "is this `body` too heavy?"

## When NOT to use

- Crash-reporter and OTel setup → [`desktop/_shared/observability`](../../../_shared/observability/SKILL.md)
- Animation design and Reduce Motion → [`styling`](../styling/SKILL.md)
- Request timing, retries, cache policy → [`networking`](../networking/SKILL.md)
- View and table authoring → [`ui-components`](../ui-components/SKILL.md)
- Windows apps → `desktop-windows:performance`; iOS → `mobile-ios:performance`

## Budgets: set them before measuring

| Budget | Target | Measured with |
|---|---|---|
| Main-thread block | **Under 250 ms always; at or above it is a hang**; an interaction feels slow from about 100 ms | Instruments Hangs; Organizer hang rate; MetricKit hang diagnostics |
| Frame | 16.7 ms (60 Hz) / 8.3 ms (120 Hz); a missed deadline is a hitch | Animation Hitches |
| Cold launch | First window rendered fast enough that the Dock bounce ends early; record the figure and hold it per release (no verified Apple number) | App Launch template; Organizer launch time |
| Window open | A new window shows its shell at once and its data via `.task` | Signposts around open → first render |
| Large table | 100,000 rows scroll and sort without a main-thread stall | Instruments Hangs and Time Profiler |
| Memory | No unbounded growth across a repeated open-and-close-window loop | Allocations, Leaks, Memory Graph |
| Energy | Idle (no window active) near zero CPU wakeups; background work deferrable | Instruments Energy Log; Activity Monitor Energy tab |
| Size | The download and installed size per release | The notarized artifact's size; App Store Connect for store builds |

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

- **Disk, decoding, parsing, image resizing, JSON of any size, large `SwiftData` / Core Data fetches** run off the main actor: `@concurrent`, a background `@ModelActor`, or a non-isolated async function.
- **A `DispatchSemaphore`, `Thread.sleep`, synchronous `Data(contentsOf:)`, `FileManager` enumeration of a big folder or `.wait()` on the main actor is a hang** the day the disk, a network volume or iCloud Drive is slow. A **network volume** or a file provider can block for seconds.
- **`await` points are not hangs; a long synchronous stretch between them is.** A loop over 100,000 items inside a `@MainActor` method blocks regardless of `async`.
- Check cancellation in long loops (`try Task.checkCancellation()`); the window's `.task` cancels it on close.
- **`NSOpenPanel` / `NSSavePanel` and file coordination** (`NSFileCoordinator`) are asynchronous: never coordinate reads on the main thread.

## Large data: `Table` and `List`

- **A `Table` / `List` is virtualized by the framework**: do not wrap it in a `ScrollView`; a `ForEach` in a `ScrollView` over thousands of rows builds every row.
- **Sort and filter in the model, off the main actor**, and publish the result; never sort a 100,000-row array in `body` or in the `Table`'s `sortOrder` handler on the main actor. Keep a cheap row view: no formatter creation, no image decode, no network call per row.
- **Stable identity**: `Identifiable` with a domain id; never `id: \.self` on non-unique values or an index. Changing identity destroys the row and its state, and loses selection.
- **Selection by id** (`Set<Album.ID>`), never by row object, so a reload does not drop it.
- Column customization and sort order persist with `TableColumnCustomization` and `@SceneStorage`, not by reloading the data.
- For data that does not fit in memory, page it from the store (`FetchDescriptor` with `fetchLimit` / offset, or a GRDB cursor) and show a `.loading` row at the edge; never load the whole set to show the first screen.
- `[AppKit]` an `NSTableView` is view-based and reuses cells: implement `tableView(_:viewFor:row:)` cheaply, never `reloadData()` for one changed row (`reloadData(forRowIndexes:columnIndexes:)` or `NSDiffableDataSource`).

## SwiftUI cost: what `body` may do

- **`body` is pure and cheap**: no sorting, no decoding, no `DateFormatter()` creation. Compute in the model, cache, or use `FormatStyle`.
- **Observation tracks per property**: split a view whose `body` reads many properties of one model into small children, each reading what it shows. **Several windows on one model** widen the blast radius: an update re-evaluates every window that read the property.
- **Avoid `AnyView`**; prefer `@ViewBuilder` and generics. Avoid a `GeometryReader` per row.
- Find a re-render with the **SwiftUI instrument** (View Body, View Properties, cause-and-effect) before changing code; the cause is usually one widely shared value.
- Images: downsample at load (`CGImageSourceCreateThumbnailAtIndex`) and size to the displayed points times the display scale; never decode a full-resolution photo for a 40 pt thumbnail.
- **Hover and pointer tracking** (`onHover`, `onContinuousHover`) that mutates state per mouse move re-renders at pointer rate: update only what changed, or move it to a layer.

## Launch

- **Do nothing before the first window that the first window does not need.** The crash reporter starts first; analytics, feature flags and update checks follow in a `.task` on the root after the first render.
- **No synchronous network, file or database work in `App.init` or the root `body`**; load from `.task` and render a skeleton.
- **Restoration is not free.** Several restored windows each load: stagger or defer non-key windows until they are visible.
- Keep dynamic libraries and static initialisers few; global initialisation runs before `main`. Measure with the **App Launch** template and watch the Organizer's launch time per version.
- A Sparkle update check or a login-item helper start never blocks the first window.

## Memory

- **Retain cycles in closures**: `[weak self]` for a stored closure on a class; a `Task` stored in a property captures `self`: cancel it in `deinit` or on window close.
- **Open and close a window ten times** in Allocations (generations) and the Memory Graph: leftover instances of the window's model are the leak. A window's observation tokens, `NotificationCenter` observers, `NSEvent` monitors and timers are removed on close.
- Caches use `NSCache` (evicts under pressure), never an unbounded dictionary.
- A document app releases a closed document's buffers; file packages load lazily (`documents`).

## Energy and background

- A Mac app with no active window should use **near-zero CPU wakeups**. No repeating `Timer` for polling: use a push, a file-system event, or `NSBackgroundActivityScheduler` with a tolerance, so the system can coalesce it ([`background-and-helpers`](../background-and-helpers/SKILL.md)).
- Pause animation, polling and live updates when the window is occluded or the app is hidden (`scenePhase`, `NSWindow.occlusionState`).
- Check **Energy Log** on battery with the lid open and shut; **App Nap** should engage when idle, and an `ProcessInfo.beginActivity` is paired with an end.
- Heavy work uses `@concurrent` with a `.utility` or `.background` priority; the UI-driven work keeps `.userInitiated`.

## MetricKit: production hangs, launches and diagnostics

Subscribe **once**, at app start, and forward to the **same pipeline as the crash reporter** ([`desktop/_shared/observability`](../../../_shared/observability/SKILL.md)):

```swift
@available(macOS 27, *)
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

- The macOS 27 form is tagged `[mac27SDK]`; the `MXMetricManager` form is tagged `[mac ≤ 26]` and is the only branch while the deployment target is below 27. The exact `MetricManager` member names are unconfirmed against Apple's page: compile against the Xcode 27 SDK first.
- **MetricKit delivers metrics at most about daily and diagnostics promptly**: good for trends and per-version regressions, **not a live rollout gate**. Hang diagnostics carry call-stack trees; symbolicate with the archive's dSYMs. Hang-diagnostic delivery on a quick test hang is reported unreliable: use Instruments for the reproduction and MetricKit for the field.
- Payloads are telemetry: strip identifiers before forwarding off the Mac.

## App size

- Track the notarized artifact (`.dmg` / `.pkg` / `.app`) size per release; a jump over the release checklist's threshold blocks the build.
- **Universal vs arm64-only is a deployment-target decision** (at the 27 deployment target the build is arm64-only): a Universal binary roughly doubles executable size; `lipo -info` shows what shipped.
- Asset catalogs, compressed formats, no duplicate resources across targets, strip debug symbols from the shipped binary (they live in dSYMs). Audit third-party packages for size before adding.

## Rules

Standards come from the desktop-macos rule files `swift.md` and `swiftui-mac.md` in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them), or the plugin's copies when the project has none; CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Reproduce and measure: Instruments on a release build; record the number and the budget it breaks.
2. Find the cause in the right instrument (Hangs → Time Profiler; hitches → SwiftUI; growth → Allocations; idle drain → Energy Log).
3. Move work off the main actor or narrow the dependency; fix identity; make the container lazy; coalesce timers.
4. Re-measure; keep the figure in the change description.
5. Add or confirm the MetricKit forwarding for the deployment target.

## Validation

- Hangs instrument on the changed flow shows no event of 250 ms or more; Animation Hitches shows no new hitches.
- A 100,000-row `Table` scrolls, sorts and filters without a hang.
- Ten open-and-close cycles of a window leave no extra instances in the Memory Graph.
- A before-and-after launch figure from the App Launch template; an idle app with no window shows near-zero wakeups in Energy Log.
- Dev-side tests for the logic moved off the main actor use injected seams: [`unit-testing`](../unit-testing/SKILL.md); XCTest `measure` and launch metrics belong to the XCTest lane named there.

## Handoffs

- Crash reporter, OTel, symbols → [`desktop/_shared/observability`](../../../_shared/observability/SKILL.md) · signing and size of the artifact → [`desktop/_shared/distribution`](../../../_shared/distribution/SKILL.md)
- Views and tables → [`ui-components`](../ui-components/SKILL.md) · state ownership → [`architecture`](../architecture/SKILL.md)
- Background scheduling, helpers → [`background-and-helpers`](../background-and-helpers/SKILL.md) · persistence cost → [`offline-and-storage`](../offline-and-storage/SKILL.md)
