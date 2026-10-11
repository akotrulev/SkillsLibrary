# iOS — Session expiry, version skew and app resume

The failures where **the app changed underneath the user**: the session ended, the server no longer supports this build, or the app slept for an hour. All three recover in place; all three destroy unsaved work when handled with a sign-out reflex.

*Deep dive for [`mobile-ios:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Session expiry — recover in place, never discard work

`networking` owns the mechanics (the `TokenStore` actor, single-flight refresh, replay once — `networking/references/request-policy.md`); this file owns **what the UI does when that fails**. The default — a coordinator that pops to the login screen — unmounts the form the user is typing into.

```
401 → 1. Silent refresh (single-flight actor)  → ok → 2. Replay once → user saw nothing
                                               → fail → 3. Re-authenticate IN PLACE (sheet) → replay → done
                                                        → declined → 4. Scoped failed state + banner
                                                                        (sign out only from a surface with nothing to lose)
```

1. **One refresh for N concurrent 401s.** Ten failing calls await one `Task` held by the actor; parallel refreshes revoke a rotated token family.
2. **Replay exactly once**, marked. A replay that 401s again goes straight to rung 3 — never back into the ladder.
3. **Re-auth in place is a sheet, not a redirect.** Present sign-in as `.sheet` over the mounted screen so the form, filters and scroll position survive. **Biometric re-auth is often the right rung 3** when a refresh credential sits in the Keychain behind `.biometryCurrentSet` / `LAContext`: one Face ID prompt, then replay. On success dismiss and replay the pending requests.
4. **Sign out only from a clean surface.** A dirty form, a pending mutation or an editor with content ⇒ do not navigate; keep the sheet affordance. For long forms persist a draft through the guarded storage wrapper — it may be unavailable ([`writes-and-dependencies.md`](writes-and-dependencies.md)).

```swift
@Observable
final class SessionGate {
    var isReauthenticating = false
    private var waiters: [CheckedContinuation<Bool, Never>] = []

    func reauthenticate() async -> Bool {
        isReauthenticating = true
        return await withCheckedContinuation { waiters.append($0) }
    }

    func finish(succeeded: Bool) {
        isReauthenticating = false
        waiters.forEach { $0.resume(returning: succeeded) }
        waiters.removeAll()
    }
}
```

The root view presents `.sheet(isPresented: $gate.isReauthenticating)`; the sheet calls `finish(succeeded:)` once. The ladder awaits `reauthenticate()` and replays or falls to rung 4. Tokens stay in the Keychain only; the sheet never logs them.

- **403 is not 401.** Permission-denied renders in the scoped region with **no retry**, no refresh and no re-auth. Conflating them signs the user out for tapping an admin control.
- **Only your own API triggers the ladder.** A 401 from a third-party host never signs the user out.
- **Warn before the deadline.** With a hard session limit, surface "signing out in 2 minutes — stay signed in?" from the session's real expiry, not from idleness.
- **Return the user to where they were.** After a sign-out, route back to the exact `NavigationPath` / route, not the root tab. Treat the return target as untrusted input and validate it against the route table.
- **Sign-out clears every store** — Keychain items, `URLCache`, SwiftData / caches, in-memory models — so the next user never sees the last user's data (`offline-and-storage`).

## Version skew — the build the server no longer supports

There is no OTA bundle on native iOS: the binary changes only through the App Store, so **skew is a server decision**. The backend publishes a minimum supported version (and optionally a recommended one); the app compares it with its own `CFBundleShortVersionString` / build. This is the **forced-update path** (OWASP MASVS-CODE-2).

| Server says | App does |
|---|---|
| Current ≥ minimum, ≥ recommended | Nothing |
| Current ≥ minimum, < recommended | A **dismissible** banner entry keyed `update.available` with a store link; never blocks |
| **Current < minimum** | The **forced-update screen**: full-screen, one action (open the App Store page), nothing else reachable |
| The check itself fails or times out | **Fail open** — let the user in; log it. A broken version endpoint must not lock everyone out |

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

- **Compare numerically** (`.numeric`), never as strings — `"1.10"` is above `"1.9"`.
- **Check on launch and on every resume** (below), not on a timer; cache the last verdict so a cold offline start still shows a required update.
- **The blocking screen sits at the root**, above navigation, so no deep link or restored state can route around it; it carries `Update.Required` and `Update.Required.Open` identifiers and is announced when it appears.
- **The store link is a fixed `itms-apps://` / `https://apps.apple.com/app/id…` constant** — never a URL taken from the server response, which would be an open redirect. (`mobile-<stack>:security`.)
- **Contract skew inside a supported version**: an unknown enum case or a missing optional field must decode to a safe default or a typed `drifted` failure, never a crash — decode enums with an `unknown` fallback case so a newer server does not break an older client.
- **Server-driven `426 Upgrade Required` or a `min-client` header** takes the same path as the policy check.
- **Never forced for a cosmetic change**; a mandatory update is for a breaking contract, a security fix or a retired API, and the server owner sets it.
- **Report it**: the screen shown and the update opened are events for the crash reporter, tagged with the build number (`mobile-<stack>:observability`).

## App resume — revalidate, never show yesterday as current

The web's stale-tab restore becomes **foreground resume**: the OS may have suspended the process for hours, dropped sockets, or relaunched it cold.

```swift
.onChange(of: scenePhase) { _, phase in
    if phase == .active { Task { await model.revalidate() } }
}
.onChange(of: connectivity.isOnline) { _, online in
    if online { Task { await model.revalidate() } }
}
```

`revalidate()` is the same `load()` the screen already has — one path, so foreground, reconnect and pull-to-refresh behave identically.

- **A resumed screen with data older than its `staleAfter` renders the stale marker until the refetch lands**, never the old numbers as current. A failed revalidation keeps the data and the marker.
- **Session and version first.** On resume the version check and the token check run before regions revalidate; the user returns to a working screen, the in-place sheet or the forced-update screen — not a wall of failed regions.
- **Debounce**: `.active` fires on every Control Centre pull and notification-shade dismissal; skip revalidation when the last success is within a few seconds.
- **Process death and cold relaunch** restore navigation state and drafts (`@SceneStorage`, `NavigationPath` codable representation); a region restoring from a persisted cache renders stale until it revalidates.
- **A resumed connection** (`URLSessionWebSocketTask`) reconnects with jitter and revalidates what it feeds; its status ("reconnecting…") is legible and live data is dimmed, never shown as current.
- **A deep link on resume** is untrusted input; validate it before it routes, and never let it skip the ladder or the forced-update gate.
