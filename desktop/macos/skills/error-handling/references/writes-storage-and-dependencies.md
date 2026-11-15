# macOS: Write failures, storage failures and dependencies that die

Three surfaces where the failure is **not a read**: a write that costs work and may have half-happened, storage that stops accepting data or access, and a helper, service or embedded view that fails on its own schedule.

*Deep dive for [`desktop-macos:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Mutation failures: quitting mid-write is routine

A failed read costs information; a failed **write** costs work and may have succeeded anyway. On a Mac the indeterminate outcome comes from **quit, sleep and a dropped network** between request and response, not from a suspended process.

- **Pending is the double-submit guard.** Disable the control while the write is in flight and guard the keyboard route too (`.onSubmit`, the menu command, ⌘S). A menu item is disabled, never hidden, while a write runs ([`menus-and-commands`](../../menus-and-commands/SKILL.md)).
- **One idempotency key per user intent, not per attempt**, created when the user starts the action and persisted with a queued write so it survives a relaunch (`networking`, `offline-and-storage`).
- **An unknown outcome is its own state.** A timeout, or a write cut off by quit or sleep, renders "We couldn't confirm whether this saved", then refetches the resource or replays with the same key. Never a definite failure and never a definite success.
- **Autosave and relaunch.** A document-based app autosaves (`documents`); a queued write is persisted before the request leaves. On relaunch the app **reconciles first**: replay queued writes with their keys, then show the window as current. A write found half-done is reported, never silently dropped.
- **Quit with unsaved work asks first**; quit during an in-flight write waits for the response or persists the intent, then quits.
- **A rolled-back optimistic update is announced.** The row reverts and the banner says what did not happen. The form keeps what the user typed.
- **409 / 412 is a decision, not a retry**: "Updated elsewhere", *Reload theirs* or *Overwrite* with a re-issued `If-Match`. Never auto-retry a conflict.
- **422 belongs on the fields** ([`forms`](../../forms/SKILL.md)), not in the banner. **Bulk writes report per item**: "12 of 15 archived", the three named and retryable.

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

    func archive(_ ids: [Album.ID]) async {
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
            notifications.raise(appError, region: "Albums")
        }
    }
}
```

The command is `.disabled(model.state.isSaving)` with `.accessibilityIdentifier("Albums.Archive")`; `.unconfirmed` shows the "couldn't confirm" body and a **Check again** action that refetches.

## Storage failures degrade: full disk, revoked bookmark, denied container

`offline-and-storage` makes a failed write throw a typed error at one storage boundary. This skill owns what happens next.

| Failure | Typed at the boundary as | The window does |
|---|---|---|
| Disk full (`CocoaError.fileWriteOutOfSpace`) | `StorageFullError` | Keep the data in memory for the session, one notice (dedupe key `storage.full`) saying it is not saved, an action that opens **Choose Folder…** or Storage settings |
| **Security-scoped bookmark stale or revoked** | `AccessLostError(url)` | The region that needs the folder shows a failed body with **Choose Folder…**; the rest of the window works; never a crash and never an empty list |
| File moved or deleted under an open document | `FileMissingError` | The document window offers *Save As…* and keeps the in-memory content |
| **Another team's container or app-group denied (macOS 27, no prompt)** | `AccessLostError` | Same as a revoked bookmark: explain, offer the panel |
| Read-only volume, permission denied on write | `AccessLostError` | Offer *Save As…* to a place the sandbox allows |

```swift
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

- **The boundary converts platform errors to the typed ones; only a typed error degrades.** Anything else rethrows to the crash reporter. No blanket catch.
- **Never degrade a secret into a weaker store.** A failed Keychain write keeps the token in memory and the next launch signs in again; it never lands in `UserDefaults` or a file.
- **Caches are disposable.** A missing cache file is a refetch, not a banner.
- **`startAccessingSecurityScopedResource()` returning `false` is a failure to handle**, not to ignore; the matching `stop…` still runs in a `defer` (`sandbox-and-permissions`).

## Dependencies that die: helper, XPC service, extension, embedded web view

Each of these fails independently, and the window must not die with them.

| Dependency | If it fails | User-visible? |
|---|---|---|
| Analytics, attribution | Nothing | **No.** Log it; no banner |
| Feature-flag provider | Evaluate to deliberate defaults and render | **No**; the team is alarmed, not the user |
| **XPC service or login-item helper** exits or is invalidated | The region it feeds shows a failed body with *Reconnect* | **Yes**, scoped to that region |
| `WKWebView` content process terminates | Show the failed body and reload on request; never a white pane | **Yes**, scoped |
| Sign-in provider, payment sheet | The flow cannot complete | **Yes**, with a stated fallback |
| A required framework or plug-in that fails to load | A crash at launch, not a degraded region | Prevented, not handled: weak-link and check availability |

- **A dead XPC session is state, not a trap.** Handle the session's cancellation handler by moving the region to `.failed`, and re-establish on the user's action or with backoff; never `try!` on a send ([`background-and-helpers`](../../background-and-helpers/SKILL.md)).
- **Each third party gets its own region and its own timeout.** A call that never returns must not leave a spinner: race it against a deadline.
- **Optional SDKs initialise after the first frame and behind one adapter** that reports once and returns an `unavailable` result.
- **A permission denied is not a failure**: it is the working denied screen ([`sandbox-and-permissions`](../../sandbox-and-permissions/SKILL.md)).
- **A third party's 401 or 5xx never starts the 401 ladder.**
- A failure report goes through the same redaction as any telemetry ([`desktop/_shared/observability`](../../../../_shared/observability/SKILL.md)).
