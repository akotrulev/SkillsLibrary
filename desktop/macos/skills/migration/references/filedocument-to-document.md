# `FileDocument` → `Document` (macOS 27 SDK)

**[mac27SDK].** `FileDocument` is deprecated on the 27 SDK; new document code uses `Document`. Existing `FileDocument` code keeps working and is **not** migrated for its own sake, unless the project builds on the 27 SDK and wants the warnings gone. `ReferenceFileDocument` (a class document with snapshots, for undo-heavy editors) "remains available" and is not migrated either. [`documents`](../../documents/SKILL.md) owns the API shape; the signatures change fastest of anything in that skill, so read them in the installed SDK before copying.

## Preconditions

- The project builds on the macOS 27 SDK. Below it, `Document` does not exist: keep `FileDocument`, record why, and gate any new code with `#available`.
- A deployment target below 27 means either an `#available` branch or keeping `FileDocument`; raising the target is a separate move ([`sdk-and-targets`](sdk-and-targets.md)).

## Steps, one document type per commit

1. **Pin the behaviour first**: a test that reads a fixture file, writes it back and compares, per document type and per content type ([`unit-testing`](../../unit-testing/SKILL.md)). A file package gets a test per part.
2. **Convert the type**: `FileDocument` → `Document` with the reader and writer. The shape that changes:
   - reading and writing are `async` and run **off the main actor** (`DocumentReader.read` and `DocumentWriter.write` are `@concurrent`); a `nonisolated` conformer written for the old API must switch, because under default MainActor isolation the work would otherwise run on the main actor and hang the window;
   - the document stays a value;
   - a failed read throws with the evidence (the type, the part that failed), which `DocumentGroup` shows as the open error.
3. **Move the `fileWrapper` logic** of a package document to the new writer, writing only the parts that changed rather than the whole package on every edit.
4. **Keep the `UTType` declarations** and `Info.plist` document types unchanged: the files on disk do not change.
5. **Check the scene**: `DocumentGroup(newDocument:)` closures are `@MainActor` on the 27 SDK; `URLDocumentConfiguration` is `@MainActor @Observable` and no longer `Sendable`.
6. **Autosave, versions, undo, revert** behave as before: edit, wait for autosave, quit, relaunch, open Versions; undo registration still sets the edited dot.

## Verify

The round-trip test passes on every fixture, including a large one (the window stays responsive while it reads); the app opens a file written by the previous release and the previous release opens one written by this one, when both ship.

## Do not

- Migrate a `ReferenceFileDocument`, or an `NSDocument` (that port is [`appkit-to-swiftui`](appkit-to-swiftui.md)), as part of this move.
- Change the file format in the same commit.
- Add a custom autosave timer to "fix" a perceived delay.
