# iOS — Write failures, third-party failures and a full disk

Three surfaces where the failure is **not a read**: a write that costs work (and may have half-happened), a third-party SDK that fails on its own schedule, and the device running out of room.

*Deep dive for [`mobile-ios:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Mutation failures — backgrounding mid-write is routine

A failed read costs information; a failed **write** costs work and may have succeeded anyway. On a phone the **indeterminate outcome is the common case**: the user switches app, the OS suspends the process, the link drops between request and response.

- **Pending is the double-submit guard.** Disable the control while the write is in flight and guard the keyboard's submit (`.onSubmit`) too. A second tap on "Pay" is a duplicate charge, not a wrinkle.
- **Idempotency key per user intent, not per attempt** — generated once when the user starts the action (a `@State` `UUID` created with the draft), kept across retries and across a process restart if the write is queued (`networking`; `offline-and-storage`). It is what makes a timed-out write safe to replay.
- **An unknown outcome is its own state.** A timeout, or a write interrupted by backgrounding or reconnect, renders "We couldn't confirm whether this saved", then **refetches the resource or replays with the same key** — never a definite failure and never a definite success. Reconcile on resume before showing the screen as current.
- **A rolled-back optimistic update is announced.** The row reverts and a banner says what did not happen ("Couldn't move the ticket — it's back in Review"). The form keeps what the user typed; never clear it on a failed submit.
- **409 / 412 is a decision, not a retry.** "This was updated elsewhere" with *Reload theirs* or *Overwrite* (a re-issued `If-Match`). Never auto-retry a conflict.
- **422 belongs on the fields** (`forms`), not in the banner.
- **Bulk writes report per item** — "12 of 15 archived", the three named and retryable.
- **Mutations never auto-retry from the client** without a key (`networking`); replay is the offline queue's decision, in order, with its keys.

```swift
enum WriteState: Sendable {
    case idle
    case saving
    case failed(AppError)
    case unconfirmed
}

@MainActor
@Observable
final class ArchiveModel {
    private(set) var state: WriteState = .idle
    private let idempotencyKey = UUID()
    private let api: APIClient
    private let notifications: Notifications

    init(api: APIClient, notifications: Notifications) {
        self.api = api
        self.notifications = notifications
    }

    func archive(_ ids: [Order.ID]) async {
        guard case .idle = state else { return }
        state = .saving
        do {
            try await api.send(.archive(ids, key: idempotencyKey))
            state = .idle
        } catch is CancellationError {
            state = .unconfirmed
        } catch let error as URLError where error.code == .timedOut {
            state = .unconfirmed
        } catch {
            let appError = AppError(error)
            state = .failed(appError)
            notifications.raise(appError, region: "Orders")
        }
    }
}
```

The button is `.disabled(model.state.isSaving)` with `.accessibilityIdentifier("Orders.Archive")`; `.unconfirmed` shows the "couldn't confirm" body and a **Check again** action that refetches. `notifications.raise` is the **one** raise-point for this mutation.

## Third-party dependencies — fail without taking the screen with them

Maps, payment sheets, push, analytics, crash reporters, feature flags, chat widgets and web views each ship someone else's code and fail independently. The split teams get backwards is **which failures the user hears about**.

| Dependency | If it fails | User-visible? |
|---|---|---|
| Analytics, attribution | Nothing — the app is unaffected | **No.** Log it; no banner for a failed beacon |
| Feature-flag provider | Evaluate to **defaults** and render | **No**, but the defaults are deliberate and the failure alarms the team |
| Map, chart, rich embed, `WKWebView` | That region shows its failed body | **Yes**, scoped to the region |
| Payment sheet, sign-in provider, push registration | The flow cannot complete | **Yes**, prominently, with a stated fallback |
| A **dynamic framework or extension** that fails to load or an SDK that throws at launch | **A crash at start, not a degraded region** | Prevented, not handled — see below |

- **Each third party gets its own region and its own timeout.** A widget with a failed load degrades its region; an SDK call that never returns must not leave the region on a spinner — wrap it in a deadline (`withThrowingTaskGroup` racing `Task.sleep`, or the SDK's own timeout).
- **A flag provider never blocks first render.** Start from bootstrapped or cached values; decide fail-open or fail-closed per flag (a kill-switch fails closed, a rollout flag fails to its default).
- **Initialise optional SDKs after the first frame and behind one adapter** that reports once and returns an `unavailable` result; a feature depending on it renders a failed body, never traps. A weak-linked framework is checked with `#available` / `canImport`, not assumed.
- **A permission denied is not a failure** — it is the working denied screen (`device-features`).
- **A third party's 401 or 5xx is never your session's problem** — it never starts the 401 ladder.
- **Load heavy embeds lazily** (a static map snapshot that mounts the live `Map` on interaction) so the failure is cheap and launch is faster ([`performance`](../../performance/SKILL.md)).
- **Privacy**: a third-party failure report goes through the same redaction as any telemetry (`mobile-<stack>:observability`).

## Storage is full — degrade to memory, say it once

`offline-and-storage` makes a write that cannot complete (disk full, a cache the OS purged under pressure) **throw a typed error at one storage boundary**. This skill owns what happens next.

```swift
struct StorageFullError: Error {}

actor GuardedStore {
    private var memory: [String: Data] = [:]
    private let write: @Sendable (String, Data) throws -> Void
    private let notify: @Sendable () async -> Void
    private var hasNotified = false

    init(write: @escaping @Sendable (String, Data) throws -> Void, notify: @escaping @Sendable () async -> Void) {
        self.write = write
        self.notify = notify
    }

    func save(_ data: Data, for key: String) async throws {
        do {
            try write(key, data)
        } catch is StorageFullError {
            memory[key] = data
            guard !hasNotified else { return }
            hasNotified = true
            await notify()
        }
    }
}
```

- **The storage boundary converts the platform error to the typed one** — `CocoaError.fileWriteOutOfSpace` (`NSFileWriteOutOfSpaceError`), a SwiftData / Core Data `save()` that throws on a full volume. **Only the typed error degrades**; anything else rethrows to the crash reporter. No blanket catch that swallows a bug.
- **Fall back to memory for the session**, so the app keeps working; the value is lost on process death, and the notice says so.
- **One notice per session** (dedupe key `storage.full`) — a banner entry with a close control, not one per failed write.
- **Never degrade a secret into a weaker store.** A failed Keychain write for a token keeps it in memory only and the next launch signs in again; it never falls back to `UserDefaults` or a file.
- **Caches are disposable.** The OS purges `Library/Caches` and `tmp` under pressure; a missing cached file or row is a refetch, not an error banner.
- **Persisted drafts and the write queue** that cannot be written tell the user their changes are not safe to leave behind, and stay in memory while the screen is open.
