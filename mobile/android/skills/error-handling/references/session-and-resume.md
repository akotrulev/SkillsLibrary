# Android — Session expiry, version skew, app resume and process death

The failures where **the app changed underneath the user**: the session ended, the server no longer supports this build, the app slept for an hour, or the system killed the process while it sat in the background. All four recover in place; all four destroy unsaved work when handled with a sign-out reflex.

*Deep dive for [`mobile-android:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Session expiry — recover in place, never discard work

`networking` owns the mechanics (the locked `TokenAuthenticator`, single-flight refresh, replay once — `networking/references/request-policy.md`); this file owns **what the UI does when that fails**. The default — navigating to the login destination — pops the screen the user is typing into.

```
401 → 1. Silent refresh (one shared, locked)  → ok → 2. Replay once → user saw nothing
                                              → fail → 3. Re-authenticate IN PLACE (dialog / biometric) → replay → done
                                                       → declined → 4. Scoped failed state + banner
                                                                       (sign out only from a surface with nothing to lose)
```

1. **One refresh for N concurrent 401s.** The authenticator's lock makes the first caller refresh and the rest replay with the new token; parallel refreshes revoke a rotated token family.
2. **Replay exactly once.** `responseCount() >= 2` returns `null` → `ApiError.Unauthorized`, which goes straight to rung 3 — never back into the ladder.
3. **Re-auth in place is a dialog, not a redirect.** Show sign-in as a `Dialog` / `ModalBottomSheet` over the mounted screen so the form, filters and scroll position survive. **Biometric re-auth is often the right rung 3** when a refresh credential sits in a Keystore key that requires user authentication (`BiometricPrompt` with a `CryptoObject`): one prompt, then replay ([`device-features`](../../device-features/SKILL.md)). Credential Manager is the sign-in provider for the dialog (`mobile-android:auth0`). On success dismiss and replay the pending calls.
4. **Sign out only from a clean surface.** A dirty form, a pending mutation or an editor with content ⇒ do not navigate; keep the dialog affordance. For long forms persist a draft through the guarded store — it may be unavailable ([`writes-and-dependencies.md`](writes-and-dependencies.md)).

```kotlin
@Singleton
class SessionGate @Inject constructor() {
    private val waiter = MutableStateFlow<CompletableDeferred<Boolean>?>(null)
    val isReauthenticating: Flow<Boolean> = waiter.map { it != null }

    suspend fun reauthenticate(): Boolean {
        val mine = CompletableDeferred<Boolean>()
        waiter.compareAndSet(null, mine)
        return waiter.filterNotNull().first().await()
    }

    fun finish(succeeded: Boolean) {
        waiter.getAndUpdate { null }?.complete(succeeded)
    }
}
```

The root composable collects `isReauthenticating` and shows the dialog while it is true; the dialog calls `finish(succeeded)` once. Concurrent callers share the one waiter. The ladder awaits `reauthenticate()` and replays or falls to rung 4. The gate is a Hilt singleton — injected, not a static. Tokens stay in the Keystore-backed store; the dialog never logs them.

- **`403` is not `401`.** Permission-denied renders in the scoped region with **no retry**, no refresh and no re-auth. Conflating them signs the user out for tapping an admin control.
- **Only your own API triggers the ladder.** A `401` from a third-party host never signs the user out.
- **Warn before the deadline.** With a hard session limit, surface "signing out in 2 minutes — stay signed in?" from the session's real expiry, not from idleness.
- **Return the user to where they were.** After a sign-out, route back to the exact destination, not the start; treat the return target as untrusted input and validate it against the route table ([`navigation`](../../navigation/SKILL.md)).
- **Sign-out clears every store** — Keystore keys, OkHttp `Cache`, Room / DataStore user data, in-memory models — so the next user never sees the last user's data ([`offline-and-storage`](../../offline-and-storage/SKILL.md)).

## Version skew — the build the server no longer supports

The binary changes only through the store, so **skew is a server decision**. The backend publishes a minimum supported version (and optionally a recommended one); the app compares it with its own `versionName` / `versionCode` from `PackageInfo`. This is the **forced-update path** (OWASP MASVS-CODE-2).

| Server says | App does |
|---|---|
| Current ≥ minimum, ≥ recommended | Nothing |
| Current ≥ minimum, < recommended | A **dismissible** banner entry keyed `update.available` with a store link; never blocks |
| **Current < minimum** | The **forced-update screen**: full-screen, one action (open the Play listing), nothing else reachable |
| The check itself fails or times out | **Fail open** — let the user in; log it. A broken version endpoint must not lock everyone out |

```kotlin
@Serializable
data class VersionPolicy(val minimum: String, val recommended: String) {

    fun verdict(current: String): VersionVerdict = when {
        compareVersions(current, minimum) < 0 -> VersionVerdict.MustUpdate
        compareVersions(current, recommended) < 0 -> VersionVerdict.CanUpdate
        else -> VersionVerdict.Current
    }
}

fun compareVersions(left: String, right: String): Int {
    val a = left.split('.').map { it.toIntOrNull() ?: 0 }
    val b = right.split('.').map { it.toIntOrNull() ?: 0 }
    return (0 until maxOf(a.size, b.size))
        .map { a.getOrElse(it) { 0 }.compareTo(b.getOrElse(it) { 0 }) }
        .firstOrNull { it != 0 } ?: 0
}
```

- **Compare numerically**, never as strings — `"1.10"` is above `"1.9"`; or compare `versionCode` (a `Long`) when the server publishes it.
- **Check on launch and on every resume** (below), not on a timer; cache the last verdict so a cold offline start still shows a required update.
- **The blocking screen sits at the root**, above navigation, so no deep link or restored back stack can route around it; it carries `Update.Required` and `Update.Required.Open` tags and is announced when it appears.
- **The store link is a fixed constant** (`market://details?id=<applicationId>` with an `https://play.google.com/store/apps/details?id=` fallback) — never a URL taken from the server response, which would be an open redirect ([`mobile-<stack>:security`](../../../../_shared/security/SKILL.md)). Play **In-App Updates** (`AppUpdateManager`, immediate flow) is an alternative for a forced update on a Play-installed build; it does not exist off Play, so keep the store-link path.
- **Contract skew inside a supported version**: an unknown enum value or a missing optional field decodes to a safe default or a typed `Drifted` failure, never a crash — `Json { coerceInputValues = true }` with a default, or an `Unknown` case, so a newer server does not break an older client.
- **Server-driven `426 Upgrade Required` or a `min-client` header** takes the same path as the policy check.
- **Never forced for a cosmetic change**; a mandatory update is for a breaking contract, a security fix or a retired API, and the server owner sets it.
- **Report it**: the screen shown and the update opened are events for the crash reporter, tagged with the build number ([`mobile-<stack>:observability`](../../../../_shared/observability/SKILL.md)).

## App resume — revalidate, never show yesterday as current

The web's stale-tab restore becomes **foreground resume**: the OS may have paused the app for hours, dropped sockets, or killed and relaunched it.

```kotlin
LifecycleResumeEffect(Unit) {
    onRevalidate()
    onPauseOrDispose { }
}

val isOnline by connectivity.isOnline.collectAsStateWithLifecycle()
LaunchedEffect(isOnline) {
    if (isOnline) onRevalidate()
}
```

`onRevalidate` is the same `refresh()` the screen already has — one path, so foreground, reconnect and pull-to-refresh behave identically. In a ViewModel with no composable at hand, `repeatOnLifecycle(STARTED)` in the collecting layer drives the same call.

- **A resumed screen with data older than its `staleAfter` renders the stale marker until the refetch lands**, never the old numbers as current. A failed revalidation keeps the data and the marker.
- **Session and version first.** On resume the version check and the token check run before regions revalidate; the user returns to a working screen, the in-place dialog or the forced-update screen — not a wall of failed regions.
- **Debounce**: `ON_RESUME` fires after every permission dialog, share sheet and notification-shade pull; skip revalidation when the last success is within a few seconds.
- **A resumed socket** reconnects with jitter and revalidates what it feeds; its status ("reconnecting…") is legible and live data is dimmed, never shown as current ([`networking`](../../networking/SKILL.md)).
- **A deep link or notification intent on resume** is untrusted input; validate it before it routes, and never let it skip the ladder or the forced-update gate.

## Process death — restore small, reload the rest

The system kills a backgrounded app's process to reclaim memory with **no callback**; the user returns to what looks like the same app. The ViewModel, every `remember` and the in-memory cache are gone; the back stack and what was saved are restored.

| What the user had | Survives by | After restore |
|---|---|---|
| Which destination, which record id, the active filter and query, the selected tab, a wizard step | `SavedStateHandle` in the ViewModel (small, serializable values — ids and strings, never lists or models); navigation arguments | Restored as it was |
| Scroll position, a text field mid-typing, an expanded section | `rememberSaveable` / `rememberLazyListState` (saveable by default) | Restored as it was |
| The data on screen | A reload from the repository — or Room / the HTTP cache, rendered **stale** until the refetch lands | `Stale(asOf)`, then `Loaded`; never a blank region, never `Loading` over data the disk holds |
| A form draft too large for the saved-state `Bundle` | The guarded draft store ([`offline-and-storage`](../../offline-and-storage/SKILL.md)) keyed by the draft id held in `SavedStateHandle` | The draft is back, with a "draft restored" notice |
| An in-flight write | Nothing in memory — the **indeterminate outcome** ([`writes-and-dependencies.md`](writes-and-dependencies.md)) | Reconciled before the screen is shown as current |

- **The saved-state `Bundle` is small** (the transaction limit is about 1 MB across the process) — a `TransactionTooLargeException` on `onSaveInstanceState` is a crash. Hold ids, not objects.
- **Restore the version and session gates too**: the restored back stack passes through the forced-update gate and the token check before any region revalidates, exactly like a resume.
- **A restored deep destination whose record is gone** renders "gone, not broken" ([`SKILL.md`](../SKILL.md)), with a way back — never a crash on a missing id.
- **Prove it**: *Don't keep activities* in developer options, and `adb shell am kill <applicationId>` from the home screen; do it on every screen with state the user would hate to lose. A test that rotates the device proves configuration change, **not** process death.
- Hilt `@HiltViewModel` receives the restored `SavedStateHandle` by itself; a manual factory passes `createSavedStateHandle()` ([`architecture`](../../architecture/SKILL.md)).
