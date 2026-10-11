# Android — Write failures, third-party failures and a full disk

Three surfaces where the failure is **not a read**: a write that costs work (and may have half-happened), a third-party SDK that fails on its own schedule, and the device running out of room.

*Deep dive for [`mobile-android:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Mutation failures — backgrounding mid-write is routine

A failed read costs information; a failed **write** costs work and may have succeeded anyway. On a phone the **indeterminate outcome is the common case**: the user switches app, the system freezes or kills the process, the link drops between request and response.

- **Pending is the double-submit guard.** Disable the control while the write is in flight, guard the IME action (`KeyboardActions(onDone = …)`) the same way, and make the ViewModel method itself a no-op while saving. A second tap on "Pay" is a duplicate charge, not a wrinkle.
- **Idempotency key per user intent, not per attempt** — generated once when the user starts the action, held in `SavedStateHandle` so a restored process reuses it, and persisted with the queued write ([`networking`](../../networking/SKILL.md); [`offline-and-storage`](../../offline-and-storage/SKILL.md)). It is what makes a timed-out write safe to replay.
- **An unknown outcome is its own state.** A timeout, or a write interrupted by backgrounding, process death or reconnect, renders "We couldn't confirm whether this saved", then **refetches the resource or replays with the same key** — never a definite failure and never a definite success. Reconcile on resume before showing the screen as current.
- **A rolled-back optimistic update is announced.** The row reverts and the banner says what did not happen ("Couldn't move the ticket — it's back in Review"). The form keeps what the user typed; never clear it on a failed submit.
- **`409` / `412` is a decision, not a retry.** "This was updated elsewhere" with *Reload theirs* or *Overwrite* (a re-issued `If-Match`). Never auto-retry a conflict.
- **`422` belongs on the fields** ([`forms`](../../forms/SKILL.md)), not in the banner.
- **Bulk writes report per item** — "12 of 15 archived", the three named and retryable.
- **Work that must survive the process** — a queued write or an upload — is a WorkManager job with a unique name and the idempotency key as input data ([`system-integration`](../../system-integration/SKILL.md)); a coroutine in `viewModelScope` dies with the screen.
- **Mutations never auto-retry from the client** without a key (`networking`); replay is the offline queue's decision, in order, with its keys.

```kotlin
sealed interface WriteState {
    data object Idle : WriteState
    data object Saving : WriteState
    data class Failed(val error: ApiError) : WriteState
    data object Unconfirmed : WriteState
}

@HiltViewModel
class ArchiveViewModel @Inject constructor(
    private val orders: OrdersRepository,
    private val notifications: NotificationsHost,
    savedState: SavedStateHandle,
) : ViewModel() {

    private val idempotencyKey: String = savedState.getOrPut(KEY) { UUID.randomUUID().toString() }

    val writeState: StateFlow<WriteState>
        field = MutableStateFlow<WriteState>(WriteState.Idle)

    fun archive(ids: List<OrderId>) {
        if (writeState.value != WriteState.Idle) return
        writeState.value = WriteState.Saving
        viewModelScope.launch {
            writeState.value = orders.archive(ids, idempotencyKey).fold(
                onSuccess = { WriteState.Idle },
                onFailure = { error -> error.toWriteState().also { raiseIfFailed(it) } },
            )
        }
    }

    private fun raiseIfFailed(state: WriteState) {
        if (state is WriteState.Failed) notifications.raise(state.error, region = "Orders")
    }

    private companion object {
        const val KEY = "archive.idempotencyKey"
    }
}

fun Throwable.toWriteState(): WriteState = when (val error = toApiError()) {
    ApiError.TimedOut, ApiError.Offline -> WriteState.Unconfirmed
    else -> WriteState.Failed(error)
}

private inline fun <T> SavedStateHandle.getOrPut(key: String, create: () -> T): T =
    get<T>(key) ?: create().also { set(key, it) }
```

`orders.archive` returns a `Result` built with `suspendRunCatching`, which rethrows `CancellationException`. The button is `enabled = state != WriteState.Saving` with `Modifier.testTag("Orders.Archive")`; `Unconfirmed` shows the "couldn't confirm" body and a **Check again** action that refetches. `notifications.raise` is the **one** raise-point for this mutation. (`Offline` before the request left the device is a definite failure that never started — the repository returns it before sending, and the key is reused on the next try either way.)

## Third-party dependencies — fail without taking the screen with them

Maps, payment sheets, push, analytics, crash reporters, feature flags, chat widgets and web views each ship someone else's code and fail independently. The split teams get backwards is **which failures the user hears about**.

| Dependency | If it fails | User-visible? |
|---|---|---|
| Analytics, attribution | Nothing — the app is unaffected | **No.** Log it; no banner for a failed beacon |
| Feature-flag provider | Evaluate to **defaults** and render | **No**, but the defaults are deliberate and the failure alarms the team |
| Map, chart, rich embed, `WebView` | That region shows its failed body | **Yes**, scoped to the region |
| Payment sheet, Credential Manager / sign-in provider, FCM registration | The flow cannot complete | **Yes**, prominently, with a stated fallback |
| **Google Play services unavailable or outdated** (a de-Googled or old device; `GoogleApiAvailability`) | Maps, FCM, Credential Manager with Google, Play Integrity and Play Billing degrade | **Yes**, per feature, with the resolution dialog where one exists |
| An **SDK that throws at launch** — a `ContentProvider` initialiser, `Application.onCreate`, a native library that fails `System.loadLibrary` | **A crash at start, not a degraded region** | Prevented, not handled — see below |

- **Each third party gets its own region and its own timeout.** A widget with a failed load degrades its region; an SDK call that never returns must not leave the region on a spinner — wrap it in `withTimeout` / `withTimeoutOrNull`, or the SDK's own deadline.
- **A flag provider never blocks first render.** Start from bootstrapped or cached values; decide fail-open or fail-closed per flag (a kill-switch fails closed, a rollout flag fails to its default).
- **Initialise optional SDKs after the first frame and behind one adapter** (App Startup initialiser, or a lazy Hilt provider) that reports once and returns an `Unavailable` result; a feature depending on it renders a failed body, never throws. A SDK that registers a `ContentProvider` initialises before `Application.onCreate` — disable it with `tools:node="remove"` and start it yourself so a failure is catchable. `System.loadLibrary` sits inside the adapter in a `try` that catches `UnsatisfiedLinkError` by name — the one `Error` the app catches — and reports it.
- **A permission denied is not a failure** — it is the working denied screen ([`device-features`](../../device-features/SKILL.md)).
- **A third party's `401` or `5xx` is never your session's problem** — it never starts the `401` ladder.
- **Load heavy embeds lazily** (a static map snapshot that mounts the live `MapView` on interaction) so the failure is cheap and launch is faster ([`performance`](../../performance/SKILL.md)).
- **Privacy**: a third-party failure report goes through the same redaction as any telemetry ([`mobile-<stack>:observability`](../../../../_shared/observability/SKILL.md)).

## Storage is full — degrade to memory, say it once

`offline-and-storage` makes a write that cannot complete (disk full, a cache the system trimmed) **throw a typed error at one storage boundary**. This skill owns what happens next.

```kotlin
class StorageFullException(cause: Throwable) : IOException("storage full", cause)

class GuardedStore(
    private val write: suspend (String, ByteArray) -> Unit,
    private val notify: () -> Unit,
) {
    private val memory = ConcurrentHashMap<String, ByteArray>()
    private val hasNotified = AtomicBoolean(false)

    suspend fun save(key: String, data: ByteArray) {
        try {
            write(key, data)
        } catch (full: StorageFullException) {
            memory[key] = data
            if (hasNotified.compareAndSet(false, true)) notify()
        }
    }
}
```

- **The storage boundary converts the platform error to the typed one** — `SQLiteFullException`, `IOException` whose message or `errno` is `ENOSPC` ("No space left on device"), a Room `save` that throws on a full volume. **Only the typed error degrades**; anything else rethrows to the crash reporter. No blanket `catch (e: Exception)` that swallows a bug — and never one that swallows `CancellationException`.
- **Fall back to memory for the session**, so the app keeps working; the value is lost on process death, and the notice says so.
- **One notice per session** (dedupe key `storage.full`) — a banner entry with a close control, not one per failed write. Offer the system **storage settings** action only as a user-chosen link in that notice.
- **Never degrade a secret into a weaker store.** A failed Keystore-backed write for a token keeps it in memory only and the next launch signs in again; it never falls back to `SharedPreferences` or a plain file ([`offline-and-storage`](../../offline-and-storage/SKILL.md)).
- **Caches are disposable.** The system trims `cacheDir` under pressure; a missing cached file or row is a refetch, not an error banner. A cache database that fails to open is rebuilt; a user-data database is kept and reported, never auto-wiped.
- **Persisted drafts and the write queue** that cannot be written tell the user their changes are not safe to leave behind, and stay in memory while the screen is open.
