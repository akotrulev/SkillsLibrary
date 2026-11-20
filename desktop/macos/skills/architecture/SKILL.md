---
name: architecture
description: Use when deciding where state and logic live in a Mac SwiftUI app (@Observable models, per-window vs app-wide, @FocusedValue). Triggers "MVVM or not". Not for API calls (networking).
disable-model-invocation: true
---

# macOS — Architecture and State

A SwiftUI view is a function of its state, and `@Observable` models plus value-type state cover what MVVM was invented for. The Mac adds one question a phone never asks: **whose state is it, the window's or the app's?** House order: local `@State` first, `@Binding` to a child, an `@Observable` model when state is shared or has behaviour, `@Environment` for app-wide services, `@FocusedValue` to let a menu command reach the focused window, a view model only where logic must be tested apart from its view. No DI container, no coordinator layer, no protocol per class.

## Version lane

| Concern | macOS 14+ (primary) | `[mac13]` | `[AppKit]` |
|---|---|---|---|
| Observation | `@Observable`; `@State` owns it, `@Bindable` binds it. The Xcode 27 `@State` macro fix back-deploys to macOS 14: a model is no longer re-initialised on every parent update | `ObservableObject` + `@Published` + `@StateObject` is correct for the target | AppKit Observation tracking: reads of `@Observable` properties in `draw(_:)`, `layout()`, `updateLayer()` are tracked; on by default from the 2026 releases, back-deploys to **macOS 15** with `NSObservationTrackingEnabled` |
| Environment | `@Environment(Type.self)`; `.environment(model)` | `@EnvironmentObject` | Initializer injection |
| Scene state | `@FocusedValue`, `focusedSceneValue`, `focusedSceneObject` (macOS 13) | Same | `NSDocument` / responder chain |
| Persistence | SwiftData (macOS 14+) | Core Data, GRDB | Core Data |
| `@Entry` | The 27 SDK warns on a default class instance or closure in the environment: use `nil` or a value | n/a | n/a |
| TCA / swift-dependencies | **Only where the codebase already uses it**: [`references/tca.md`](references/tca.md) (TCA 1.26.2) | Same | Same |

A `[mac13]` project is not flagged for lacking `@Observable`; migration is [`migration`](../migration/SKILL.md)'s. Isolation rules (`MainActor` default in an app module, `nonisolated` in packages) are [`basics`](../basics/SKILL.md).

## Inputs needed

- Deployment target (14+ or 13) and whether the codebase has a view-model or TCA convention
- Whether several windows show the same data, and whether the app is document-based
- What needs a test apart from the view

## Decision tree

```
Purely presentational, owned by one view (a toggle, a text field, a popover flag)?
  yes -> @State in that view.
  no  ->
Does a child only read it or write one value?
  yes -> pass the value, or @Binding for write.
  no  ->
A model with behaviour used by one window's subtree?
  yes -> @Observable model, @State in the window's root view, passed down / @Bindable.
  no  ->
Must several windows show the same data?
  yes -> ONE app-wide @Observable store, built at the composition root, passed by @Environment.
         Each window holds only its own selection and layout state.
  no  ->
App-wide service (session, settings, a client)?
  yes -> @Observable or plain final class built at the root, passed by @Environment.
```

## Per-window versus app-wide state

**Several windows on the same data share one source of truth, never a copy per window.** A second window for the same account that fetches its own list shows stale data the moment the first mutates it.

| State | Lives in | Why |
|---|---|---|
| The selected item, sidebar selection, inspector shown, scroll position, search text | The window: `@State` / `@SceneStorage` in the window's root view | Two windows legitimately differ |
| The domain data (albums, orders, a document's model) | One app-wide `@Observable` store | Every window reads the same instance |
| User settings | `@AppStorage` / a settings model read by the `Settings` scene and the windows | One truth, changes apply live |
| A document's content | The document model of `DocumentGroup` ([`documents`](../documents/SKILL.md)) | One per open document |
| Transient edits not yet committed | The view that edits them | Discarded on cancel |

`@SceneStorage` restores per-window state at relaunch. Never put the data itself there: it holds ids and layout, not records.

```swift
@main
struct MusicApp: App {
    @State private var store = LibraryStore(client: LiveAlbumClient())

    var body: some Scene {
        WindowGroup {
            LibraryWindow()
                .environment(store)
        }
        .commands { LibraryCommands() }
    }
}

struct LibraryWindow: View {
    @Environment(LibraryStore.self) private var store
    @SceneStorage("selectedAlbumID") private var selectedAlbumID: Album.ID?

    var body: some View {
        NavigationSplitView {
            AlbumSidebar(albums: store.albums, selection: $selectedAlbumID)
        } detail: {
            AlbumDetail(albumID: selectedAlbumID)
        }
        .focusedSceneValue(\.selectedAlbumID, $selectedAlbumID)
    }
}
```

The store is `@State` in the `App`, built once; windows read it from the environment.

## `@FocusedValue` plumbing

The Mac-specific state seam: a command in the menu bar acts on **the focused window**, which the command cannot name. The window publishes a value; the command reads it.

```swift
extension FocusedValues {
    @Entry var selectedAlbumID: Binding<Album.ID?>?
}

struct LibraryCommands: Commands {
    @FocusedValue(\.selectedAlbumID) private var selection

    var body: some Commands {
        CommandGroup(after: .newItem) {
            Button("Reveal in Finder") { }
                .keyboardShortcut("r", modifiers: [.command, .shift])
                .disabled(selection?.wrappedValue == nil)
        }
    }
}
```

- The window **publishes with `focusedSceneValue`** (the whole window) or `focusedValue` (the focused subtree); the command **reads with `@FocusedValue`** (a value) or `@FocusedObject` / `focusedSceneObject` (an `@Observable` object).
- **A command with no focused value is disabled, never hidden** (CLAUDE.md § Desktop code rules). That is what `.disabled(selection == nil)` does.
- A `UtilityWindow` (macOS 15) receives the `FocusedValues` of the focused main scene, so an inspector panel follows the selection with no extra wiring.
- Publish the narrowest value that serves: a selection binding, not the whole model. Menu text and shortcuts are [`menus-and-commands`](../menus-and-commands/SKILL.md).

## The model

```swift
@MainActor
@Observable
final class LibraryStore {
    private(set) var state: LoadState<[Album]> = .loading
    private let client: AlbumClient

    init(client: AlbumClient) { self.client = client }

    var albums: [Album] { state.value ?? [] }

    func reload() async {
        do { state = .loaded(try await client.albums()) }
        catch is CancellationError { return }
        catch { state = .failed(error) }
    }
}
```

- **Constructor injection only**, and the client is a concrete type until a second implementation exists. A test supplies a fake `AlbumClient` through the same initializer.
- One `LoadState` enum covers loading / loaded / failed; stale and offline are cases the `networking` skill adds. A failure is scoped to the subtree that needs the response.
- Revalidate on **window reactivation, wake from sleep and a network change**: `scenePhase`, `NSWorkspace.didWakeNotification`, `NWPathMonitor` feed one `reload()`.
- A model for a window's work cancels that work when the window closes (`.task` handles it; stored tasks cancel in `deinit`).

## Services and the composition root

All concrete objects are built once in `App.init` / the `App` struct (the composition root) and passed down. No singleton, no `Container.shared`, no service locator. `@Environment` carries an `@Observable` or a value; **a default instance in `@Entry` is a smell the 27 SDK now warns about**.

## TCA lane

Only where the codebase already uses it, keyed to its version. [`references/tca.md`](references/tca.md) covers reducers, `@FocusedValue` with stores and testing; no new feature adopts TCA unasked.

## Common gotchas

- **A model fetched per window**: two windows, two copies, drift. One store.
- **`@StateObject`-era ownership copied into 14+**: use `@State` for the owner.
- **Stuffing records into `@SceneStorage`**: ids only.
- **A command that hides itself**: disable it.
- **A protocol per model** for previews: a preview builds the real model with a fake client.
- **Observation of a Core Data object** via `@ObservedObject` in new code: wrap it in an `@Observable`.

## Rules

Output must meet the desktop-macos rule files (`swift.md`): `.claude/rules/desktop-macos/`, or `desktop/macos/skills/rules/` when not installed.

## Validation (exit gate)

- [ ] State sits at the lowest level that works; shared domain data has one store
- [ ] No per-window copy of the same records; per-window state is selection and layout only
- [ ] Every menu command that depends on a window reads `@FocusedValue` and is disabled when it is nil
- [ ] Models take dependencies through the initializer; no singleton or locator
- [ ] No view model that only forwards to one service
