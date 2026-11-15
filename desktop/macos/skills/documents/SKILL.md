---
name: documents
description: Use when a Mac app opens, edits or saves user files (DocumentGroup, Document, packages, autosave). Triggers "make it a document app". Not for app databases (offline-and-storage).
---

# macOS — Documents

A document app gets New, Open, Open Recent, Save, Duplicate, Revert, the edited dot, autosave, versions and a window per document from `DocumentGroup`. **New code uses `Document` (27 SDK); `FileDocument` is deprecated there.** Audit rows are in section I of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| `DocumentGroup`, `FileDocument`, `ReferenceFileDocument`, `fileImporter`, `fileExporter` | macOS 11+ | `FileDocument` is **deprecated on the 27 SDK**; keep it only in existing code and in a project that must build on older SDKs |
| `ReadableDocument`, `WritableDocument`, `Document` **[mac27SDK]** | macOS 27 SDK, async read/write, progress, direct URL access | New document code on a 27 SDK. Deployment target below 27: gate with `#available` or keep `FileDocument` and record why |
| `ReferenceFileDocument` | "Remains available" on 27 | `Document` is preferred |
| `\.newDocument` with an in-memory document → "New from Template"; `DocumentGroupLaunchScene` + `NewDocumentButton(source:)` **[mac27SDK]** | 27 SDK | — |

The 27 changes that break conformers: `DocumentReader.read` and `DocumentWriter.write` are `@concurrent` (a `nonisolated` conformer must switch; under default MainActor isolation they would otherwise run on the main actor); `makeDocument` closures are `@MainActor`; `URLDocumentConfiguration` is `@MainActor @Observable`, no longer `Sendable`; `FileWrapperDocumentWriter.makeFileWrapper` gets `previous:` — mutate it to write only the changed package children. Detect the SDK and deployment target before writing; never raise either for these APIs.

## When to use

- A document-based app, or opening/saving one user file kind
- A bundle (file package) with many parts
- Autosave, versions, Revert, edited indicator, unsaved-work prompts
- iCloud documents, open from Finder, Recent documents

## When NOT to use

- App-owned databases, caches → `offline-and-storage`
- Panels, security-scoped bookmarks, entitlements → `sandbox-and-permissions`
- Window placement → [`windows-and-scenes`](../windows-and-scenes/SKILL.md); Save/Revert menu items → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- UIKit document browser → `mobile-ios`; Windows → `desktop-windows:offline-and-storage`

## Declare the document type

Declare the UTI (`UTExportedTypeDeclarations`, `CFBundleDocumentTypes`) in the app's `Info.plist`: a stable reverse-DNS identifier, `conformsTo` `public.data` or `com.apple.package`, one extension. The `UTType` constant lives next to the document type. A type the app only reads is declared as Viewer, not Editor.

## `Document` (27 SDK)

```swift
struct SketchDocument: Document {
    static let readableContentTypes: [UTType] = [.sketch]
    var layers: [Layer]

    init(layers: [Layer] = []) { self.layers = layers }

    init(reading source: DocumentReader) async throws {
        layers = try JSONDecoder().decode([Layer].self, from: try await source.data())
    }

    func write(to destination: DocumentWriter) async throws {
        try await destination.write(JSONEncoder().encode(layers))
    }
}
```

Signatures follow the 27 SDK documentation; check them in the SDK before copying — they are the part of this skill that changed most recently. Rules that do not depend on spelling: reading and writing are `async`, run off the main actor, and touch no UI; the document is a value; a failed read throws with the evidence (the type, the part that failed), which `DocumentGroup` shows as the open error.

```swift
@main
struct SketchApp: App {
    var body: some Scene {
        DocumentGroup(newDocument: { SketchDocument() }) { file in
            SketchWindow(document: file.$document)
        }
    }
}
```

### `FileDocument` (existing code, pre-27 SDK)

Same shape with `init(configuration: ReadConfiguration)` and `fileWrapper(configuration:)`. Do not start new code on it when the 27 SDK is in use; migrating is `migration`'s (`FileDocument` → `Document`). `ReferenceFileDocument` (a class document with snapshot, for undo-heavy editors) stays valid and is not migrated for its own sake.

## File packages

A bundle document (`com.apple.package`) is a directory of parts. Write only what changed: on the 27 SDK use the `previous:` file wrapper and mutate it; on older code keep the wrapper and replace children by name. A package's internal layout is versioned (a `version` file) so an older app refuses cleanly.

## Autosave, versions, undo, revert

- Autosave and versions are on by default; **do not add a Save-on-timer of your own** and do not write to the document URL outside the document API.
- The edited indicator follows the undo manager: register every user edit with `@Environment(\.undoManager)`; a change with no undo registration leaves the document looking clean.
- Revert To, Duplicate and Rename come from `DocumentGroup`; never replace them with Save As (HIG prefers Duplicate).
- Quitting or closing with unsaved work asks first, and relaunch restores the open documents; do not suppress either.
- Records the document holds never go into `@SceneStorage`; only selection and layout do.

## iCloud documents

Turn on the iCloud container and the `ubiquity` document capability; coordinated reads and writes are `DocumentGroup`'s. Conflicts show the system conflict UI; never pick a winner silently. A not-yet-downloaded file reads as a loading state, not an error.

## Drag and drop and pasteboard

`Transferable` types for the document's content; `.draggable` and `.dropDestination(for:)` for in-document items. The status of a possible `dropDestination(for:action:isTargeted:)` deprecation at macOS 27.3 is **not verified** (the docs metadata shows 13.0 – 27.3 and no replacement was found): use it, and re-check the SDK headers before writing a rule that forbids or requires it. The 27 SDK `List` accepts drops into reorderable content and `.reorderable()`. AppKit: `NSFilePromiseReceiver.receivePromisedFiles` throws if called outside the drag callbacks.

## Common gotchas

- **New code on `FileDocument`** with a 27 SDK build.
- **A `nonisolated` conformer** after the `@concurrent` change.
- **Writing the whole package** on every edit.
- **No undo registration**: no edited dot, no dirty prompt.
- **A custom autosave timer** fighting the system's.
- **`Save As` menu** instead of Duplicate.
- **Reading on the main actor** in a `FileDocument` reader.

## Handoffs

- Panels and bookmarks → `sandbox-and-permissions`
- Window and launch scene → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- Menu items → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- `FileDocument` → `Document` → `migration`
- App databases → `offline-and-storage`
