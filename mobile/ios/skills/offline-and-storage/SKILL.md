---
name: mobile-ios-offline-and-storage
description: Use when an iOS app must persist data — SwiftData (iOS 17+) with VersionedSchema migrations, Core Data / GRDB where present, Keychain accessibility classes, UserDefaults and its Required Reason, file protection, caches vs backup, an offline write queue. Triggers "where do I store this", "migrate the schema", "token storage", "works offline". Do NOT use for fetch mechanics (`mobile-ios-networking`) or the offline UI (`-error-handling`).
---

# iOS — Offline and Storage

Decides **where each kind of data lives, how it survives an app update, and how it degrades** — plus the offline write queue. The request is [`networking`](../networking/SKILL.md); the offline banner and stale marker are `mobile-ios-error-handling`. Web analog: the persistence half of `fe-react-installable-offline-app`.

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` | Already present |
|---|---|---|---|
| Structured local data | **SwiftData** (`@Model`, `ModelContainer`, `@Query`) | Not available — Core Data or GRDB; do not recommend SwiftData | **Core Data** and **GRDB** (7.x) are lanes: extend them, never rewrite on a side effect |
| Migrations | `VersionedSchema` + `SchemaMigrationPlan` | Core Data lightweight / staged migration | GRDB `DatabaseMigrator` |
| Background writes | `@ModelActor` | `NSManagedObjectContext.perform` on a background context | GRDB `DatabasePool` |
| Secrets | Keychain, `…ThisDeviceOnly` ([`references/keychain.md`](references/keychain.md)) | Same | Same |
| Preferences | `UserDefaults` / `@AppStorage` (**a Required Reason API**) | Same | Same |
| `Observations` | iOS 26+ | n/a | n/a |

Detect first: `import SwiftData`, `.xcdatamodeld`, `GRDB` in `Package.resolved`. **Never add a second store beside the one in use.** CloudKit sync (`ModelConfiguration(cloudKitDatabase:)`) adds constraints (no unique attributes, all properties optional or defaulted) — read them before enabling.

## When to use

- Choosing storage for a new piece of data; adding a model or a field
- A schema change that must migrate existing installs
- Storing a token, key or credential
- Caching responses, images or files; clearing on logout
- "Works offline", an offline write queue, sync and conflicts
- A full disk, a failed store open, or a corrupted database

## When NOT to use

- The request, retry, cache headers → [`networking`](../networking/SKILL.md)
- The offline indicator, stale marker, banner → `mobile-ios-error-handling`
- Where state lives in the view tree → [`architecture`](../architecture/SKILL.md)
- Keychain misuse as a security finding, backup rules → [`mobile-shared-security`](../../../_shared/security/SKILL.md) (this skill writes the correct code; that one audits it)
- Privacy manifest declarations → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Widgets and extensions reading shared data → `mobile-ios-system-integration`
- Another stack → `mobile-react-native-offline-and-storage`, `mobile-android-offline-and-storage`

## Where does it go?

```
A secret (token, refresh token, key, PII a user would not want read off a backup)?
  -> Keychain, a ...ThisDeviceOnly class.
A small user preference or flag (theme, last tab, onboarding done)?
  -> UserDefaults / @AppStorage. Never a token.
Structured, queryable, relational app data?
  -> SwiftData (17+), or the project's Core Data / GRDB.
Re-downloadable data (images, responses)?
  -> URLCache or the Caches directory — the OS may delete it.
A user's file or a large blob?
  -> Application Support (kept, excluded from backup if regenerable) or Documents (user-visible), with file protection.
Shared with an extension or widget?
  -> An App Group container; no tokens in it; a Keychain access group for secrets.
```

## SwiftData

```swift
@Model
final class Note {
    @Attribute(.unique) var id: UUID
    var title: String
    var body: String
    var updatedAt: Date
    var isPendingSync: Bool

    init(id: UUID = UUID(), title: String, body: String, updatedAt: Date = .now) {
        self.id = id
        self.title = title
        self.body = body
        self.updatedAt = updatedAt
        self.isPendingSync = false
    }
}

@main
struct NotesApp: App {
    let container: ModelContainer

    init() {
        do { container = try ModelContainer(for: Note.self, migrationPlan: NotesMigrationPlan.self) }
        catch { fatalError("ModelContainer failed: \(error)") }
    }

    var body: some Scene {
        WindowGroup { NotesList() }
            .modelContainer(container)
    }
}

struct NotesList: View {
    @Query(sort: \Note.updatedAt, order: .reverse) private var notes: [Note]
    @Environment(\.modelContext) private var context

    var body: some View {
        List(notes) { note in
            NavigationLink(value: note.id) { Text(note.title) }
        }
    }
}
```

- **`@Query` is for views; a model object is never passed across actors** — pass its `PersistentIdentifier`, or a `Sendable` value snapshot.
- **Background work uses `@ModelActor`**; the main `ModelContext` is `@MainActor` and used for UI-bound edits only. A fetch of thousands of rows never runs on the main context.
- **`@Attribute(.unique)` is an upsert key** — inserting a duplicate id replaces, it does not throw; do not rely on it for a "does it exist" check.
- **A failed `ModelContainer` open is handled, not `fatalError`'d, in a shipping app** — the sample's `fatalError` is the *first-run* shape only; the degraded path is in "Storage failures degrade" below.
- Fetch with a `FetchDescriptor` (predicate, sort, `fetchLimit`) — never fetch everything then `filter`.
- **Delete on logout**: remove the store files (or `context.container.deleteAllData()`) and the Keychain items; a signed-out device keeps no previous user's rows.

### Migrations are a plan, written before the first field change

Every schema that ships is a `VersionedSchema`; a change adds a version and a stage. Lightweight stages cover add / remove / rename (`originalName:`) of attributes; anything that rewrites data is a custom stage. The step-by-step, with a custom stage and its test, is in [`references/swiftdata-migrations.md`](references/swiftdata-migrations.md). **A model change without a new `VersionedSchema` is a crash on update for every existing install** — the audit row for it is a blocker.

## Core Data and GRDB — the lanes

Where the codebase already has them, **extend, do not rewrite.**

| Lane | Rules |
|---|---|
| **Core Data** | One `NSPersistentContainer`; UI reads `viewContext` on the main actor; writes use `performBackgroundTask` / a background context with a merge policy stated (`NSMergeByPropertyObjectTrumpMergePolicy`); schema changes via a new model version + lightweight mapping or a staged migration; `automaticallyMergesChangesFromParent = true` on `viewContext` |
| **GRDB** | A `DatabasePool` for files (WAL, concurrent readers), `DatabaseQueue` for in-memory tests; `DatabaseMigrator` with `eraseDatabaseOnSchemaChange` **off** in release; `ValueObservation` into the view layer; statements use arguments, never string-built SQL |

Moving Core Data → SwiftData is [`mobile-ios-migration`](../migration/SKILL.md)'s, on request.

## Keychain

Tokens, refresh tokens and keys live in the Keychain, **always a `…ThisDeviceOnly` accessibility class** (`WhenUnlockedThisDeviceOnly` default; `AfterFirstUnlockThisDeviceOnly` where a background task or extension must read it). The add-or-update wrapper, biometric gating with `SecAccessControl`, access groups and the logout wipe are in [`references/keychain.md`](references/keychain.md). The rules behind them are [`mobile-shared-security`](../../../_shared/security/SKILL.md) § 2.

- **Nothing sensitive in `UserDefaults`, a plist, a file, `@AppStorage`, `@SceneStorage` or a SwiftData column.**
- **Keychain items survive app deletion** on some OS versions — a fresh-install check (`UserDefaults` flag absent → clear the Keychain on first launch) prevents a previous user's session reappearing.
- The Keychain call is synchronous disk and IPC: **never on the main actor in a hot path** — read once at launch into the `TokenStore` actor ([`networking`](../networking/SKILL.md)).

## `UserDefaults` is a Required Reason API

`UserDefaults`, `@AppStorage` and any SDK that uses them require a `NSPrivacyAccessedAPICategoryUserDefaults` entry in the app's `PrivacyInfo.xcprivacy`, with reason `CA92.1` for app-only data (`1C8F.1` for an App Group suite). A missing declaration is an App Store Connect rejection — [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md) owns the code table and the Archive → Generate Privacy Report check.

Keys are constants in one place; stored values are plain types or `RawRepresentable`; **no secret, no PII, no server data cache.** File-timestamp APIs (`creationDate`, `modificationDate`) are a second Required Reason category (`C617.1`) — a cache that evicts by age triggers it.

## Files, caches and backup

| Directory | For | Backup | Notes |
|---|---|---|---|
| `Documents` | Files the user created and should see in Files | Yes | Never regenerable junk |
| `Application Support` | App data a user would lose | Yes | Create it; set `isExcludedFromBackup` on regenerable subfolders |
| `Caches` | Re-downloadable data | No | The OS purges it under disk pressure — read a miss as normal |
| `tmp` | Scratch | No | Delete when done |

- **File protection**: private files are written with `.completeFileProtection` (or `.completeUntilFirstUserAuthentication` / `completeUnlessOpen` where background writes continue while locked); `Data.write(to:options:)` states it explicitly.
- **Exclude regenerable or sensitive files from backup** with `URLResourceValues.isExcludedFromBackup = true` on the file or folder.
- Disk-space probes (`volumeAvailableCapacityForImportantUsageKey`) are a Required Reason API (`E174.1`) — check before a large write; do not poll.

## Offline-first writes — the queue

A write made offline is stored locally first, shown immediately as *pending*, and replayed when the network returns. The smallest correct shape:

```swift
@Model
final class PendingMutation {
    var id: UUID
    var endpointName: String
    var body: Data
    var idempotencyKey: String
    var attempts: Int
    var createdAt: Date

    init(endpointName: String, body: Data, idempotencyKey: String = UUID().uuidString) {
        self.id = UUID()
        self.endpointName = endpointName
        self.body = body
        self.idempotencyKey = idempotencyKey
        self.attempts = 0
        self.createdAt = .now
    }
}
```

- **One `idempotencyKey` per user intent, stored with the row** — replay after an indeterminate outcome (killed mid-request) cannot create twice.
- **Replay in order per resource**, on `scenePhase == .active` and on reconnect, one at a time through the same `APIClient` (so retry, budgets and refresh apply once). A `4xx` other than `408` / `429` marks the row *failed* and surfaces it; it is never retried silently.
- **Conflicts have a stated rule per entity** — last-write-wins with server timestamps, or a `409` that returns the server copy and asks the user. Choose per entity and write it down; "sync" is not a rule.
- **Show pending and failed rows** — an offline write that vanished into a queue the user cannot see is data loss by design.
- A write that must complete after the app is suspended is a background `URLSession` / `BGTaskScheduler` job (`mobile-ios-system-integration`), not a held `Task`.

## Storage failures degrade to memory

A full disk is common and caches are wiped under pressure; none of these is a crash.

- `ModelContainer` or `NSPersistentContainer` fails to open → log the error with `os.Logger`, fall back to `ModelConfiguration(isStoredInMemoryOnly: true)`, show a persistent notice that changes will not be saved, and offer "reset local data" when the store is corrupt. `fatalError` on open is a finding.
- A Keychain read returns `errSecItemNotFound` → signed out, not an error; `errSecInteractionNotAllowed` (device locked) → retry after unlock, not sign-out.
- A cache write fails → serve from memory for this session; never block the screen on it.
- The UI half (banner, copy, retry) is `mobile-ios-error-handling`'s.

## Rules

- One store per concern; match the project's; SwiftData only on iOS 17+.
- Secrets in the Keychain with a `…ThisDeviceOnly` class; never in `UserDefaults`, plists or model columns.
- Every shipped schema is versioned and has a migration stage; every migration has a test.
- `UserDefaults` / file-timestamp / disk-space use has a matching privacy-manifest entry.
- Model objects do not cross actors; background work is `@ModelActor` / a background context.
- Private files carry file protection; regenerable files are excluded from backup.
- Offline writes carry an idempotency key, replay in order through the one client, and show pending / failed.
- A store that fails to open degrades to memory with a notice, never a crash.
- Logout clears the store, the caches and the Keychain items.

## What NOT to do

- No `kSecAttrAccessibleAlways*`, no non-`ThisDeviceOnly` class without a documented restore requirement.
- No token in `@AppStorage`, a plist, `@SceneStorage` or Core Data.
- No SwiftData recommendation for an iOS 16 target; no rewrite of an existing Core Data / GRDB store.
- No string-built SQL in GRDB; no `eraseDatabaseOnSchemaChange` in a release build.
- No `@Query` over an unbounded table into a list that renders all rows.

## Generation steps

1. Detect store, deployment target, existing Keychain wrapper and privacy manifest.
2. Place each piece of data with the decision tree; write the model and its first `VersionedSchema`.
3. Add the container, the migration plan and a migration test; add the Keychain wrapper if absent.
4. Add the `PrivacyInfo.xcprivacy` entries for `UserDefaults` and any file-timestamp use.
5. If offline writes are required: the queue, the replay on foreground / reconnect, the conflict rule, the pending / failed rows.
6. Add the degraded-store path and the logout wipe.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build with warnings as errors; the project's formatter and linter pass.
- Install the previous build, create data, install the new build: the data is intact and the migration stage ran.
- Archive → Generate Privacy Report lists `UserDefaults` with the declared reason.
- Airplane mode: a write shows pending, survives a force-quit, and replays once on reconnect.
- Dev-side tests: in-memory `ModelContainer` / `DatabaseQueue`, migration test, queue replay with a fake client — [`mobile-ios-unit-testing`](../unit-testing/SKILL.md). Whether the Keychain item is really protected → **requires dynamic test → `qa-security`**.

## Handoffs

- Requests, retry, token refresh → [`networking`](../networking/SKILL.md)
- Offline UI and degraded notice → `mobile-ios-error-handling`
- Keychain / backup audit rules → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Required Reason declarations → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Core Data → SwiftData, Realm exits → [`mobile-ios-migration`](../migration/SKILL.md)
- Background transfers and tasks → `mobile-ios-system-integration`
