# macOS: Several windows, wake from sleep, session expiry and version skew

The failures where **the app changed underneath the user**: a second window changed the data, the Mac slept for an hour, the session ended or the server no longer supports this build. All recover in place; all destroy unsaved work when handled with a sign-out reflex.

*Deep dive for [`desktop-macos:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Several windows, one model

The web's multi-tab consistency becomes **multi-window**. Fetched data lives in one app-wide `@Observable` model injected through `@Environment`; each window holds only its own selection, scroll position and filters (`architecture`).

- A write in window A updates the model; window B re-renders from the same source. Two `@State` copies of one fetch are a defect: the second window shows old data after the first one saves.
- A failure on the shared model shows in **every** window that renders the region, but the banner dedupes by cause per window, so the user sees one entry per window, not one per call.
- Closing a window cancels the work only that window started (`.task` does it); the shared model's own refresh is cancelled only when the app quits.
- Window restoration reopens windows before the first load lands: each restored window renders `.loading`, or `.stale` when the persisted cache has data (`offline-and-storage`).

## Wake, reactivation and network change: one revalidate

A Mac sleeps with the lid shut and the app open. Every held connection is dead on wake and every cached read may be stale.

```swift
.onChange(of: scenePhase) { _, phase in
    if phase == .active { Task { await model.revalidate() } }
}
.onChange(of: connectivity.isOnline) { _, online in
    if online { Task { await model.revalidate() } }
}
.onReceive(NSWorkspace.shared.notificationCenter.publisher(for: NSWorkspace.didWakeNotification)) { _ in
    Task { await model.revalidate() }
}
```

`revalidate()` is the same `load()` the region already has: one path, so wake, reconnect, reactivation and the refresh button behave identically. Put the three triggers at the window root, never in each leaf.

- **Data older than its `staleAfter` renders the stale marker until the refetch lands**, never the old numbers as current. A failed revalidation keeps the data and the marker.
- **Session and version first.** On wake the token check and the version check run before regions revalidate, so the user returns to a working window, the in-place sheet or the blocking prompt, not a wall of failed regions.
- **Debounce.** `.active` fires on every Cmd-Tab; skip when the last success is within a few seconds. Wake usually arrives before the network: wait for `isOnline` rather than failing the first request.
- **Cancel on `willSleepNotification`** for sockets and long polls; reconnect with jitter after wake, and revalidate what the stream feeds ([`networking`](../../networking/SKILL.md)).
- **A deep link or URL scheme on reactivation** is untrusted input; validate it before it routes, and never let it skip the ladder or the version gate.

## Session expiry: recover in place, never discard work

`networking` owns the mechanics (the token actor, single-flight refresh, replay once). This file owns **what the window does when that fails**.

```
401 → 1. Silent refresh (single-flight actor)  → ok → 2. Replay once → user saw nothing
                                               → fail → 3. Re-authenticate IN PLACE (sheet on the window) → replay
                                                        → declined → 4. Scoped failed state + banner
                                                                        (sign out only from a surface with nothing to lose)
```

1. **One refresh for N concurrent 401s.** Parallel refreshes revoke a rotated token family.
2. **Replay exactly once**, marked. A replay that 401s again goes straight to rung 3.
3. **Re-auth in place is a sheet on the window**, not a redirect: the form, filters and selection survive. Present it with `.sheet(isPresented:)` bound to a `SessionGate`; the sign-in uses `ASWebAuthenticationSession` (`auth/auth0-macos`). Touch ID is a convenience only when the refresh credential sits in the data-protection Keychain behind an access-control flag.
4. **Sign out only from a clean surface.** A dirty document, a pending write or an editor with content ⇒ keep the sheet affordance; autosave first.

- **403 is not 401.** Permission-denied renders in the scoped region with no retry, no refresh and no re-auth.
- **Only your own API triggers the ladder.** A 401 from a third-party host never signs the user out.
- **Sign-out clears every store**: Keychain items, `URLCache`, the SwiftData / cache files in the container, in-memory models, and **every window**, so the next user never sees the last user's data. Close or reset all windows, not only the key one.
- **Return the user to where they were**: route back to the window and selection, treating the target as untrusted input validated against the route table.

## Version skew and the updater

The binary changes through **Sparkle** (Developer ID builds) or the **Mac App Store** (store builds have no self-updater; guideline 2.4.5). Skew is two things: the updater shipping a new build, and a server that no longer supports an old one.

| Situation | App does |
|---|---|
| Update available, nothing unsaved | Sparkle's standard UI; the user chooses when |
| **Update ready, unsaved work exists** | **Never restart over it.** Defer the relaunch until documents are saved or the user confirms; Sparkle's "install on quit" is the default-safe path |
| Server minimum above the running build | A **blocking prompt** over the window: one action ("Check for Updates…", or open the store page), nothing else reachable |
| Server recommended above the running build | A dismissible banner entry keyed `update.available`; never blocks |
| The version check fails or times out | **Fail open**: let the user in, log it |

```swift
struct VersionPolicy: Decodable, Sendable {
    let minimum: String
    let recommended: String

    func verdict(for current: String) -> VersionVerdict {
        if current.compare(minimum, options: .numeric) == .orderedAscending { return .mustUpdate }
        if current.compare(recommended, options: .numeric) == .orderedAscending { return .canUpdate }
        return .current
    }
}
```

- **Compare numerically**; `"1.10"` is above `"1.9"`. Check on launch and on every wake, and cache the last verdict so a cold offline start still shows a required update.
- **The blocking prompt sits at the root of every window**, so a restored window or a second window cannot route around it, and it carries `Update.Required` and `Update.Required.Open` ids.
- **The update URL is a fixed constant or Sparkle's own feed**, never a URL taken from the server response.
- **Contract skew inside a supported build**: an unknown enum case or a missing optional field decodes to a safe default or a typed `drifted` failure, never a crash.
- **Never forced for a cosmetic change.** A mandatory update is for a breaking contract, a security fix or a retired API, and the server owner sets it.
- Signed feeds and the update channel itself: [`desktop/_shared/distribution`](../../../../_shared/distribution/SKILL.md), [`desktop/_shared/security`](../../../../_shared/security/SKILL.md).
