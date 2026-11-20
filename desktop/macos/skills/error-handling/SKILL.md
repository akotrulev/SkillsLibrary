---
name: error-handling
description: Use when a failure must not blank a Mac window (failed/stale/offline regions, inline banner, wake-from-sleep revalidation). Triggers "table empty when API fails". Not for retries (networking).
disable-model-invocation: true
---

# macOS — Error Resilience

Owns **failing safely and recovering** in a Mac window: rendering failure, staleness and offline so a broken region never looks like an empty one, and recovering in place from a dead session, a sleeping Mac, a write cut off by quit, a dead helper or a revoked file permission. Web analog: [`fe-react:error-handling`](../../../../frontend/react/skills/error-handling/SKILL.md): every rule carries over with the desktop deltas below; `error.tsx`, hydration and chunk-load errors do not exist here. Sibling: [`mobile-ios:error-handling`](../../../../mobile/ios/skills/error-handling/SKILL.md) (the same region and banner rules; this skill swaps the safe-area banner for a window-content banner and resume for wake and reactivation). Audit rows are section O of `desktop-macos:standards-audit`.

Division of labour with [`networking`](../networking/SKILL.md): it **produces** the categorised `APIError` (kind, status, correlation id, `retryAfter`, retryable), the timeout budget and bounded retries. This skill **renders** it.

## Version lane

| Concern | Primary (Swift 6, macOS 14+) | Notes |
|---|---|---|
| Region state | One `LoadState<Value>` enum in an `@Observable` model | One enum, never four booleans |
| Failed / empty body | `ContentUnavailableView` (macOS 14) | `[mac13]` a plain `VStack` with the same content |
| Reactivation | `@Environment(\.scenePhase)` + `.onChange(of:)` | `[AppKit]` `NSApplication.didBecomeActiveNotification` |
| Wake from sleep | `NSWorkspace.didWakeNotification` (also `willSleepNotification`) | Held connections are dead on wake |
| Offline signal | `NWPathMonitor` (`networking`'s `Connectivity`) | Never a ping |
| Inline banner | One `@Observable` `Notifications` host at the window root | Not `NSAlert`, not a system notification |
| Crash reporting | One reporter, plus MetricKit (macOS 12+) | [`desktop/_shared/observability`](../../../_shared/observability/SKILL.md). A Swift trap is **not catchable**: prevent it |
| `[mac27SDK]` | No change to these rules | Re-check `ContentUnavailableView` styling under the 27 SDK |

Detect first: the existing banner host, `LoadState` / `AppError` types, the wired crash reporter, whether the app is multi-window. Extend them, never add a second.

## When to use

- Rendering a region's loading / loaded / failed / stale / offline states and the three empty kinds
- The persistent inline banner, a timeout, a 401 mid-session, a forced update
- Wake from sleep, reactivation, a second window on the same data
- A write cut off by quit or sleep, a dead helper or XPC service, a full disk, a revoked bookmark

## When NOT to use

- Producing the error, retries, `Retry-After`, token-refresh mechanics → [`networking`](../networking/SKILL.md)
- Persisting data, the write queue, conflicts → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Field validation messages → [`forms`](../forms/SKILL.md)
- Permission denied screens → [`sandbox-and-permissions`](../sandbox-and-permissions/SKILL.md)
- Crash-reporter setup, symbols → [`desktop/_shared/observability`](../../../_shared/observability/SKILL.md)
- Windows → `desktop-windows:error-handling`

## The failure surfaces

```
Programmer error (trap)          → prevented: no try!, no force unwrap, no unchecked index
Fetch FAILED / never answers     → APIError → LoadState.failed (timeout is its own body)
SESSION expired (401)            → refresh → replay → re-auth in place (sheet on the window)
Mac WOKE / window reactivated    → one revalidate; stale marker until it lands
Server REJECTS this app version  → blocking prompt, one action
Write interrupted (quit, sleep)  → indeterminate outcome, reconcile on relaunch
Helper / XPC / bookmark / disk   → scoped failed region with a recovery action
```

SwiftUI has **no error boundary**: a thrown error is caught where it is thrown and becomes state. Every `async throws` call in a view or model sits in a `do`/`catch` that lands in a `LoadState`; no error escapes `body`.

## Data regions: loading / loaded / failed, plus stale and offline

```swift
enum LoadState<Value: Sendable>: Sendable {
    case loading
    case loaded(Value)
    case failed(AppError)
    case stale(Value, AppError, asOf: Date)
}
```

```swift
struct AlbumsRegion: View {
    let state: LoadState<[Album]>
    let isOnline: Bool
    let retry: () async -> Void

    var body: some View {
        switch state {
        case .loading:
            ProgressView().accessibilityIdentifier("Albums.Loading")
        case .failed(let error):
            RegionFailure(error: error, isOffline: !isOnline, retry: retry)
                .accessibilityIdentifier("Albums.Error")
        case .loaded(let rows):
            AlbumTable(rows: rows)
        case .stale(let rows, _, let asOf):
            AlbumTable(rows: rows).safeAreaInset(edge: .top) {
                StaleMarker(asOf: asOf, retry: retry).accessibilityIdentifier("Albums.Stale")
            }
        }
    }
}
```

- **A response the app can't read is a failure, not an empty list.** A drifted body throws `APIError.drifted` and lands in `.failed`; never `try?` into `[]`.
- **Render a friendly message and the correlation id only.** The UI never prints `localizedDescription`, a stack or a body.
- **Offline is its own body**, driven by `Connectivity`, not by a failed request. Offline with cached data is `.stale`; no retry control spins while offline: reconnect refetches.
- **Stale (refetch failed, data held)**: keep the rows, show their age, keep the retry, notify once. A failed refresh (toolbar button, ⌘R) keeps the table and becomes `.stale`.
- **Timeout renders its own body**, retry leading, with a soft "still loading…" tier at about 6 s inside the budget. `CancellationError` / `URLError.cancelled` (the window closed) is not a failure: no state change, no banner.
- **Gone, not broken.** A `404` renders "This album no longer exists" with a way back and no retry.
- **Empty is three states**: no records yet (offer *create*), no filter yet (focus the filter), filter matched nothing (offer *clear filters*).

### Scope the failure to the response-dependent subtree

A Mac window has a sidebar, a toolbar and often an inspector. When the content pane fails, **all three keep working**. An early `if case .failed … return` at the top of the window loses them; render the chrome unconditionally and put the `switch` where the rows go.

```swift
var body: some View {
    NavigationSplitView {
        SidebarView(selection: $selection)
    } detail: {
        AlbumsRegion(state: model.state, isOnline: connectivity.isOnline, retry: model.reload)
            .toolbar { LibraryToolbar(query: $query) }
    }
    .safeAreaInset(edge: .top) { NotificationsBanner() }
}
```

Filter state lives above the failing region (in the model or the window's scene storage) so "fix the filter and retry" works. A failed body is never identical to the empty one.

## The inline banner: persistent, in the window, user-dismissed

The region says *this data is missing*; the banner says *why, and how to report it*. Both, always. **There is no modal `NSAlert`** for a failure the user did not cause, and **no system notification** for a foreground failure.

| Property | Value |
|---|---|
| Position | Top of the **window content**, `.safeAreaInset(edge: .top)` on the window's root view, below the toolbar. Never an overlay over the table, never a sheet |
| Dismissal | A close control only (≥ 20 × 20 pt, 28 pt by default), keyboard-reachable; **no auto-dismiss for an error**, ever |
| Content | Friendly message, copyable correlation id, optional retry |
| Semantics | Announced on appearance with `AccessibilityNotification.Announcement(_:).post()`; focus stays where the user is typing |
| Dedupe | Key `correlationId ?? code + region`; a repeat updates one entry with a count |
| Host | One `@Observable` `Notifications` model per window, fed by the shared app model; features never mount their own |
| Ids | `Notifications.Banner`, `Notifications.Banner.Close`, `Notifications.Banner.CorrelationId` |

Raise it from **one place per failure path**: the model that owns the load, a mutation's `catch`, the version gate. Roll up by cause (six regions on one 503 is one message), cap the stack at 3 and let a retry circuit quiet repeats. **No banner** for field validation, an expected empty result, a cancelled request, a failure absorbed by retry or a failed analytics call.

A **background** failure (a sync, a helper, a scheduled refresh with no window focused) raises no modal alert: it is recorded on the app model and the banner shows in each window the next time it is active.

## The desktop deltas, in one place

| Rule | What it means in a Mac app | Where |
|---|---|---|
| **Multi-window consistency** | One `@Observable` model for the data, every window observes it. A write in one window never leaves another showing old data. A per-window copy of fetched data is a defect | [`references/windows-wake-and-versions.md`](references/windows-wake-and-versions.md) |
| **Wake and reactivation revalidate** | `didWakeNotification`, `scenePhase == .active` and a network change feed one `revalidate()` at the root; stale marker until it lands | same |
| **Version skew** | Sparkle (or the Mac App Store) never restarts the app over unsaved work; a forced minimum is a server-driven prompt that fails open | same |
| **Quit mid-write is routine** | Autosave; on relaunch the indeterminate outcome is reconciled, never silently dropped | [`references/writes-storage-and-dependencies.md`](references/writes-storage-and-dependencies.md) |
| **Storage failures degrade** | Full disk or a revoked security-scoped bookmark is an explained, recoverable state | same |
| **Helper / XPC / extension dies** | The region it feeds shows a failed body; the window and the rest keep working | same |

## Situational surfaces: read the file when it applies

| Situation | Where |
|---|---|
| **401 mid-session**: refresh → replay → in-place re-auth sheet; 403 is not 401 | [`references/windows-wake-and-versions.md`](references/windows-wake-and-versions.md) |
| **Wake, reactivation, network change**; several windows on one model | same |
| **Version skew** and the updater (Sparkle, Mac App Store) | same |
| **A write fails** (double submit, idempotency, 409, 422, bulk, quit mid-write) | [`references/writes-storage-and-dependencies.md`](references/writes-storage-and-dependencies.md) |
| **A third party, helper or `WKWebView` fails** | same |
| **Disk full, revoked bookmark, container denied** | same |

## Rules

Standards come from the desktop-macos rule files `swiftui-mac.md`, `swift-networking.md` and `swift.md` in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them), or the plugin's copies when the project has none; CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Read the existing `LoadState` / `AppError`, banner host, `Connectivity` and crash reporter; match them.
2. Give each region one `LoadState` and one body bound where its rows render; keep sidebar, toolbar and inspector outside it.
3. Mount the `Notifications` host once per window and raise from the owning model only; add the wake and reactivation revalidate and the version gate from the references; tag every state.

## Validation

- Fail the content load with search text typed and an inspector open → sidebar, toolbar, search and inspector stay interactive; only the rows carry the error; the banner stays until its close control is used.
- Open two windows on one library, edit in one → the other shows the change without a manual refresh.
- Sleep the Mac, wake it with an expired token → one refresh, the window current or the re-auth sheet shown, not a wall of failed regions.
- Fail a refresh after a load → rows remain, stale marker with an age, one banner. System Settings → Network off → offline or stale, never "failed".
- Dev-side tests of the state transitions: [`unit-testing`](../unit-testing/SKILL.md); end-to-end failure journeys → `qa-desktop-<lang>` (peer).

## Handoffs

- The categorised error, timeouts, retries, token refresh → [`networking`](../networking/SKILL.md)
- Persistence and the write queue → [`offline-and-storage`](../offline-and-storage/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- Ids → [`test-ids`](../test-ids/SKILL.md) · announcements → [`accessibility`](../accessibility/SKILL.md)
- Window state shared across windows → [`architecture`](../architecture/SKILL.md) · reactivation at the root → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- Crash reporter, symbols → [`desktop/_shared/observability`](../../../_shared/observability/SKILL.md) · updater and signing → [`desktop/_shared/distribution`](../../../_shared/distribution/SKILL.md)
