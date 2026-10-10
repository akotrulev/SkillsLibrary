# SwiftData migrations — versioned schemas and stages

SwiftData needs **iOS 17**. On iOS 16 the lanes are Core Data or GRDB; do not apply this file.

## 1. Version the schema before the first change

The first shipped schema is already a `VersionedSchema`, so the second one has something to migrate from.

```swift
enum NotesSchemaV1: VersionedSchema {
    static let versionIdentifier = Schema.Version(1, 0, 0)
    static var models: [any PersistentModel.Type] { [Note.self] }

    @Model
    final class Note {
        @Attribute(.unique) var id: UUID
        var title: String
        var body: String

        init(id: UUID = UUID(), title: String, body: String) {
            self.id = id
            self.title = title
            self.body = body
        }
    }
}
```

## 2. Add V2 — the model is a nested type per version

```swift
enum NotesSchemaV2: VersionedSchema {
    static let versionIdentifier = Schema.Version(2, 0, 0)
    static var models: [any PersistentModel.Type] { [Note.self] }

    @Model
    final class Note {
        @Attribute(.unique) var id: UUID
        @Attribute(originalName: "title") var heading: String
        var body: String
        var updatedAt: Date

        init(id: UUID = UUID(), heading: String, body: String, updatedAt: Date = .now) {
            self.id = id
            self.heading = heading
            self.body = body
            self.updatedAt = updatedAt
        }
    }
}
```

`@Attribute(originalName:)` makes a rename lightweight. The app code refers to the **current** version through a typealias (`typealias Note = NotesSchemaV2.Note`).

## 3. The plan — lightweight where it can be, custom where data must change

```swift
enum NotesMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] { [NotesSchemaV1.self, NotesSchemaV2.self] }
    static var stages: [MigrationStage] { [v1ToV2] }

    static let v1ToV2 = MigrationStage.custom(
        fromVersion: NotesSchemaV1.self,
        toVersion: NotesSchemaV2.self,
        willMigrate: nil,
        didMigrate: { context in
            let notes = try context.fetch(FetchDescriptor<NotesSchemaV2.Note>())
            for note in notes where note.updatedAt == .distantPast {
                note.updatedAt = .now
            }
            try context.save()
        }
    )
}
```

| Change | Stage |
|---|---|
| Add an attribute with a default / optional | `MigrationStage.lightweight(fromVersion:toVersion:)` |
| Rename an attribute or model | Lightweight with `originalName:` |
| Remove an attribute | Lightweight |
| Change a type, split / merge, derive a value, de-duplicate before a new `.unique` | **Custom**; `willMigrate` runs on the old schema (de-duplicate here), `didMigrate` on the new |

- **The container is created with the plan**: `ModelContainer(for: schema, migrationPlan: NotesMigrationPlan.self)`.
- **One stage per consecutive pair**; a V1 install updating to V3 runs V1→V2→V3.
- A custom stage touching many rows batches its saves; it runs before the UI shows and **counts against the launch budget** — measure with Instruments (`mobile-ios-performance`).

## 4. Test it

Write the V1 store on disk, open it with the plan, assert the V2 result:

```swift
@Suite struct NotesMigrationTests {
    @Test func Should_KeepNotesAndSetUpdatedAt_When_MigratingV1ToV2() throws {
        let url = URL.temporaryDirectory.appending(path: "\(UUID().uuidString).store")
        let v1 = try ModelContainer(
            for: Schema(versionedSchema: NotesSchemaV1.self),
            configurations: ModelConfiguration(url: url)
        )
        v1.mainContext.insert(NotesSchemaV1.Note(title: "Milk", body: "2 litres"))
        try v1.mainContext.save()

        let v2 = try ModelContainer(
            for: Schema(versionedSchema: NotesSchemaV2.self),
            migrationPlan: NotesMigrationPlan.self,
            configurations: ModelConfiguration(url: url)
        )
        let notes = try v2.mainContext.fetch(FetchDescriptor<NotesSchemaV2.Note>())

        #expect(notes.map(\.heading) == ["Milk"])
    }
}
```

The test deletes its file in the suite's teardown (`deinit` of a struct is unavailable — use a class suite or a `Trait` that removes `url`).

## 5. Traps

- Editing a shipped `@Model` in place without a new `VersionedSchema` crashes every existing install on launch.
- Adding a `.unique` attribute to existing duplicate rows fails the migration — de-duplicate in `willMigrate`.
- `@Model` classes cannot be shared across two schema versions: each version declares its own.
- CloudKit-backed stores need optional or defaulted attributes and no `.unique` — adding sync later is a schema change, planned as one.
- A migration that fails leaves the user with a store that will not open: the degraded path (`SKILL.md` § Storage failures) must exist before the first migration ships.
