---
name: offline-and-storage
description: Use when a Mac app persists data (SwiftData, Core Data, GRDB, Keychain, UserDefaults, sandbox container paths, offline queue). Triggers "where does this file go". Not for documents (documents).
disable-model-invocation: true
---

# macOS — Offline and Storage

Where data lives on a Mac, in what, and what happens when the disk is full, the store will not open or the network is gone. The Mac differences from iOS: the **sandbox container** decides every path, the **data protection keychain** must be asked for by name, `UserDefaults` is per bundle id (and per suite), several windows share one store, and a user can move, back up or delete the files. Document-based persistence is [`documents`](../documents/SKILL.md). Audit rows are section I of `desktop-macos:standards-audit` (rows I1–I9 belong to `documents`; this skill's rows follow them).

## Version lane

| Concern | Primary | Supported / notes |
|---|---|---|
| SwiftData | macOS 14+ (`@Model`, `ModelContainer`, `@Query`, `VersionedSchema`) | macOS 27 fixed a `@Query` deadlock with background `ModelActor` saves; on 14–26 keep writes on one actor |
| Core Data | brownfield lane: keep it, add `NSPersistentCloudKitContainer` only where already used | — |
| GRDB 7.12 / SQLiteData 1.13 | the SQL lane, macOS 12+ | `DatabasePool` (WAL) for a multi-window reader |
| Keychain | `kSecUseDataProtectionKeychain: true` | the legacy file keychain is the default on macOS without it |
| `UserDefaults` | `UserDefaults.standard` for the app; a suite for an app group | — |
| Sandbox container | `~/Library/Containers/<bundle id>/Data` | **[MAS]** and any sandboxed build |

macOS 27: access to **other teams'** app containers and app-group containers is denied by default with no prompt. Never read another app's container; share through an app group the team owns, or through XPC.

Detect the existing persistence first (SwiftData, Core Data, GRDB, a JSON file). **Match it; never add a second store.**

## Where does it go?

| Data | Home | Why |
|---|---|---|
| Tokens, API keys, passwords, keys | **Keychain**, data protection keychain | Never `UserDefaults`, a plist or a log |
| User preferences (small, per user) | `UserDefaults` via `@AppStorage` / `@SceneStorage` for per-window state | Apply on change; no Save button |
| Structured app data | SwiftData / Core Data / GRDB in `Application Support` | Backed up with the user's Time Machine |
| Re-creatable data (thumbnails, response cache) | `Caches` (`FileManager.urls(for: .cachesDirectory)`) | The system and the user may delete it |
| Scratch files | `FileManager.default.temporaryDirectory` | Cleaned by the system |
| Data shared with a helper or an extension | An **app group** container | Group id prefixed with the team id; otherwise the user is prompted |
| Files the user owns | A panel or a security-scoped bookmark | → `sandbox-and-permissions` |

Resolve every directory through `FileManager`, never a hard-coded `~/Library/...` string: in the sandbox `~` is the container, outside it is not. Create `Application Support/<bundle id>` on first launch; it does not exist.

## One store, many windows

All windows observe **one** model container, created once at the `App` level and injected (`.modelContainer(_:)` on the scene, or an `@Observable` store through the environment). A window never opens its own copy of the database: a write in one window would not reach another until relaunch. With GRDB use one `DatabasePool` for the app; readers in windows see committed writes through `ValueObservation`.

## SwiftData

```swift
@Model
final class Order {
    @Attribute(.unique) var id: UUID
    var title: String
    var placedAt: Date

    init(id: UUID = UUID(), title: String, placedAt: Date) {
        self.id = id
        self.title = title
        self.placedAt = placedAt
    }
}

@main
struct OrdersApp: App {
    private let container: ModelContainer

    init() {
        container = ModelContainer.orders()
    }

    var body: some Scene {
        WindowGroup { OrdersWindow() }
            .modelContainer(container)
    }
}
```

- `@Query` in views for reads; writes through `modelContext` on the main actor, or a `@ModelActor` for bulk work. **Never** hand a `@Model` instance across actors; pass `PersistentIdentifier` or a value snapshot.
- A schema change is a **plan written before the first field change**: `VersionedSchema` per released shape and a `SchemaMigrationPlan` with a stage per step. The store of an installed Mac app is the user's data; there is no "reinstall to fix it". Test the migration from a fixture store of each released version.
- `ModelContainer(for:)` throws. A thrown container is a **failed state**, not `fatalError`: fall back to an in-memory container, show the inline banner and offer **Reveal in Finder** on the store folder (see Storage failures degrade).

## Core Data and GRDB — the lanes

**Core Data** (brownfield): keep the stack; set `NSPersistentStoreDescription.shouldMigrateStoreAutomatically` and `shouldInferMappingModelAutomatically` and test the lightweight path; `viewContext` on the main actor, `newBackgroundContext()` for work; `automaticallyMergesChangesFromParent = true` so every window sees saves.

**GRDB**: `DatabaseMigrator` with named, never-edited migrations (`registerMigration("v2-add-status")`); `DatabasePool` in WAL mode; `eraseDatabaseOnSchemaChange` in Debug only.

## Keychain on the Mac

The Mac has two keychains. Without `kSecUseDataProtectionKeychain: true` an item lands in the **legacy file-based keychain**, which behaves differently (ACLs per app, prompts, no iCloud sync) and is what surprises teams ported from iOS.

```swift
struct KeychainStore {
    func save(_ data: Data, account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Bundle.main.bundleIdentifier!,
            kSecAttrAccount as String: account,
            kSecUseDataProtectionKeychain as String: true,
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        guard status == errSecItemNotFound else { return try check(status) }
        try check(SecItemAdd(query.merging(attributes) { $1 } as CFDictionary, nil))
    }
}
```

- The data protection keychain needs the app signed with a team id (a keychain-access-groups entitlement is derived from it). An unsigned Debug build fails with `errSecMissingEntitlement`: sign Debug with the development team.
- Sharing with a helper or extension uses `kSecAttrAccessGroup` with the group in `keychain-access-groups`.
- A token in `UserDefaults`, a plist, a file or a log is a **blocker**.
- `kSecAttrSynchronizable` only for a secret the user expects on their other devices.

## `UserDefaults`

Preferences only: window-independent, small, non-secret. `@AppStorage` for a view; a typed wrapper for non-view code; a suite (`UserDefaults(suiteName: "<team>.<group>")`) for an app group. Per-window UI state is `@SceneStorage`, which the system restores at relaunch. A removed key is migrated once at launch, then deleted.

## Offline-first writes — the queue

A write the user expects to survive offline or a quit goes into a durable queue (one table), then the network:

1. The user saves: write the change and a queue row (`id`, `kind`, `payload`, `idempotencyKey`, `attempts`, `state`) in **one transaction**. The UI shows the result at once.
2. A drainer task runs in the app-wide model on launch, on reconnect (`Connectivity`) and on wake; it sends oldest first with the row's `idempotencyKey` (`networking`).
3. Success deletes the row; a `4xx` marks it `rejected` and raises the inline banner with the reason; a network failure leaves it `pending`.
4. **Quitting mid-write is routine.** On relaunch a row left `sending` is `indeterminate`: ask the server by idempotency key and reconcile; never drop it silently and never replay it blindly.
5. Conflicts: last-writer-wins only for fields the user never edits in two places; otherwise show both versions.

## Storage failures degrade

A full disk, a store that will not open, a corrupt file or a revoked file permission is a **recoverable, explained state**, never a crash and never a blank window:

- Disk full (`NSFileWriteOutOfSpaceError`, `SQLITE_FULL`): keep the unsaved value in memory, show the inline banner "Not enough disk space — changes are kept until you quit", retry on the next edit.
- Store will not open: quarantine the file (rename with a timestamp, do not delete), start a fresh in-memory or empty store, banner with **Reveal in Finder** and a link to the support page.
- Keychain read fails (`errSecInteractionNotAllowed`, locked): treat as signed out for now, retry on the next activation; never wipe the item.
- The user deleted the container's contents: first launch logic runs again; it is idempotent.

## Rules

Standards come from `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them); CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Detect the store, the sandbox state and the deployment target; read the entitlements file.
2. Pick each datum's home from the table; resolve paths through `FileManager`.
3. Create the container once at the `App` level; inject it; give each model its migration plan.
4. Put secrets in the data protection keychain through one `KeychainStore`.
5. Add the write queue where the product needs offline writes; wire the drainer to launch, reconnect and wake.
6. Write the degraded path for each storage failure above, with a test that triggers it.

## Validation

- A fresh launch creates the folders it needs; deleting the container's `Application Support` and relaunching recovers.
- Open the app with a store from each released version: migrates, data intact.
- Fill a small disk image and save: banner appears, nothing crashes, the value survives until quit.
- Edit in window A: window B updates without a reload.
- `rg -n "kSecClass" -g '*.swift'` shows every query sets `kSecUseDataProtectionKeychain`.
- Dev-side tests (in-memory container, fake keychain, clock seam): `unit-testing`.

## Common gotchas

- **Keychain item "disappears" between builds**: a different signing identity; sign consistently.
- **A second database per window**: writes invisible elsewhere.
- **`~/Library/...` hard-coded**: wrong inside the sandbox.
- **`try!` on `ModelContainer`**: a corrupt store crashes the app at launch every time.
- **A `@Model` passed to a background actor**: use identifiers.
- **A token "temporarily" in `UserDefaults`**: it ships.
- **Reading another app's container on 27**: denied with no prompt; use an app group.
