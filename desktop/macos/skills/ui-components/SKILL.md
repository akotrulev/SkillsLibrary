---
name: ui-components
description: Use when writing Mac SwiftUI views (Table, List selection, inspector, sidebar, context menus, hover and touch, .task loads). Triggers "build this window". Not for state (architecture).
disable-model-invocation: true
---

# macOS — SwiftUI Views

Writes Mac SwiftUI that is small, previewable, cancels its own work, renders every state of its data, and treats the pointer, the keyboard and touch as equals. State is [`architecture`](../architecture/SKILL.md); colour, materials and Liquid Glass are [`styling`](../styling/SKILL.md); the Swift is [`basics`](../basics/SKILL.md). Design facts come from `design/ui-ux-pro-max`: `search.py "<query>" --stack swiftui` (views, lists, async, preview, performance rows) and the HIG pages "Designing for macOS" and "Pointing devices".

## Version lane

| Concern | macOS 14+ (primary) | `[mac13]` | `[mac27SDK]` |
|---|---|---|---|
| `Table`, `List` selection | `Table` (macOS 12): columns, sort, multi-select | Same | Same |
| Sidebar-detail | `NavigationSplitView` (13) | Same | Sidebars extend to window edges and select semibold, automatically |
| Inspector | `.inspector(isPresented:)` (14); trailing column restores its state; `InspectorCommands` adds the shortcut | Not available: a trailing split pane or `HSplitView` | Same |
| Model in a view | `@State` / `@Bindable` / `@Environment(Type.self)` | `@StateObject` / `@ObservedObject` | Same |
| Key handling | `onKeyPress` (14) | `.keyboardShortcut` only | Same |
| Previews | `#Preview`; `PreviewProvider` is deprecated by the 27 SDK | `#Preview` works on any target | Same |
| Menu and context-menu icons | Shown | Shown | **Symbol images hidden by default**; show one with `.labelStyle(.titleAndIcon)` |
| Drag and drop | `Transferable`, `.draggable`, `.dropDestination` | Same | `List` accepts drops into reorderable content; `.reorderable()`; a possible 27.3 `dropDestination` deprecation is **not verified**: re-check before writing a drop rule |
| Text-field border | `.roundedBorder` / `.squareBorder` | Same | Soft-deprecated: `.bordered` + `textInputBorderShape(_:)` |

A `[mac13]` project is not flagged for lacking an inspector. `[AppKit]` codebases host SwiftUI through `NSHostingView`: [`appkit`](../appkit/SKILL.md).

## When to use

- Building a window's content, a row, a sidebar, an inspector, an empty or error state
- A multi-column data list, selection, sorting
- Context menus, hover effects, a control that must work by touch
- A view that re-renders too much, or a `#Preview`

## When NOT to use

- Where state lives → [`architecture`](../architecture/SKILL.md)
- Colour, type, density, glass, materials → [`styling`](../styling/SKILL.md)
- Scenes, window placement, toolbars at window level → `windows-and-scenes`; the menu bar → `menus-and-commands`
- `Form` in Settings and inspectors → `forms`
- VoiceOver and Full Keyboard Access → `accessibility`
- AppKit controllers → [`appkit`](../appkit/SKILL.md)
- iPhone screens → `mobile-ios:ui-components`

## Inputs needed

- The data and its states: loading, loaded, empty, failed, stale, offline
- Deployment target; SwiftUI or AppKit host; document-based or not
- The closest existing view to copy the shape of

## Small views

- A view is a `struct` with a `body` and nothing heavy. Rows, headers and states are their own views.
- Extract a subview, not a `@ViewBuilder` method, once it has its own inputs.
- Inputs are values or bindings: a row takes `Album`, not the store. A display-only view is previewable without a model.
- Modifier order matters; reusable chains become a `ViewModifier` or `ButtonStyle`.
- **Window and view words:** the UI says "window", "pane", "sidebar", never "scene" or "screen".

```swift
struct AlbumRow: View {
    let album: Album

    var body: some View {
        HStack {
            Label(album.title, systemImage: "music.note.list")
            Spacer()
            Text(album.trackCount, format: .number)
                .foregroundStyle(.secondary)
        }
    }
}
```

## `Table` — the Mac list type

`Table` is multi-column, sortable and selectable; a `List` is for one column of rows or a sidebar.

```swift
struct AlbumTable: View {
    let albums: [Album]
    @Binding var selection: Set<Album.ID>
    @State private var sortOrder = [KeyPathComparator(\Album.title)]

    var body: some View {
        Table(albums.sorted(using: sortOrder), selection: $selection, sortOrder: $sortOrder) {
            TableColumn("Title", value: \.title)
            TableColumn("Artist", value: \.artist)
            TableColumn("Tracks") { Text($0.trackCount, format: .number) }
        }
        .accessibilityIdentifier("Library.AlbumTable")
        .contextMenu(forSelectionType: Album.ID.self) { ids in
            Button("Show in Finder") { }.disabled(ids.isEmpty)
        } primaryAction: { ids in
            open(ids)
        }
    }
}
```

- **Selection is a `Set` of stable ids**, never row indexes; the window keeps it (`@SceneStorage` for ids). Double-click or Return is the `primaryAction`.
- Sort with `KeyPathComparator`; sort a large data set off the main actor (`@concurrent`), not in `body`.
- Rows are keyed by `Identifiable` ids; **a large `Table` is virtualized by the framework: do not wrap it in a `ScrollView`.** A `ForEach` in a `ScrollView` of thousands of rows is not virtualized.
- Columns are user-resizable and reorderable; persist with `TableColumnCustomization` where the user benefits.

## `List`, sidebars and selection

```swift
List(selection: $sidebarSelection) {
    Section("Library") {
        ForEach(SidebarItem.allCases) { item in
            NavigationLink(value: item) { Label(item.title, systemImage: item.symbol) }
        }
    }
}
.listStyle(.sidebar)
```

- `NavigationSplitView { sidebar } detail: { }` is the default window shape; `.listStyle(.sidebar)` gives the vibrant material and (27 SDK) edge-to-edge look automatically.
- **In-app navigation is a real `NavigationLink(value:)` or `Button` with a destination**, never a tap gesture on a `Text`.
- Selection drives the detail; an empty selection shows a `ContentUnavailableView`.

## Inspector

```swift
.inspector(isPresented: $showsInspector) {
    AlbumInspector(albumID: selectedAlbumID)
        .inspectorColumnWidth(min: 220, ideal: 280, max: 400)
}
.toolbar {
    ToolbarItem { Button("Inspector", systemImage: "sidebar.trailing") { showsInspector.toggle() } }
}
```

- The trailing inspector restores its presentation state; add `InspectorCommands()` in `.commands` for the standard View-menu item and shortcut so the control is reachable from the keyboard.
- An inspector shows **the selection**, with `ContentUnavailableView("No Selection")` when empty. A floating panel that follows the selection is a `UtilityWindow` (macOS 15, `windows-and-scenes`).

## Context menus, hover and touch

- **Every context-menu action also exists in the menu bar or a toolbar.** A context menu is a shortcut, never the only path (`menus-and-commands`).
- **Hover reveals are never the only way to a control.** Touch-screen Macs ship since 2026-11-06 and the HIG gained touch guidance on 2026-10-28: a hover-only control also gets a click path and a context-menu path, and keeps the selection when it is revealed. Touch is for brief, intentional interactions; controls may grow on touch without changing density.
- `onHover` and `.hoverEffect` for feedback only; `.help("…")` for the tooltip, kept short and localised.
- A custom control reachable by pointer is reachable by keyboard: `.focusable()` with `onKeyPress`, and a visible focus ring.

## `.task` — loads that cancel with the window

`.task { }` is the only way a view starts async work: SwiftUI cancels it when the view disappears.

```swift
.task { await store.reload() }
.task(id: searchText) { await results.search(searchText) }
```

- `.task(id:)` cancels the previous run on change. A cancelled load is not a failure (`catch is CancellationError`).
- **Reactivation revalidates:** `@Environment(\.scenePhase)` for `.active`, wake from sleep and a network change feed the same reload ([`architecture`](../architecture/SKILL.md)).
- Nothing in `body` or `init` does I/O; no browser-style `onAppear { Task { } }`.

## Every data region has states

A region that depends on a response renders **loading, loaded, empty, failed**, plus **stale** and **offline** where data is cached. The failure is scoped to the response-dependent subtree: the toolbar, search field and window title keep rendering.

```swift
struct AlbumsContent: View {
    let state: LoadState<[Album]>
    @Binding var selection: Set<Album.ID>
    let retry: () -> Void

    var body: some View {
        switch state {
        case .loading:
            ProgressView().accessibilityIdentifier("Library.Loading")
        case .loaded(let albums) where albums.isEmpty:
            ContentUnavailableView("No albums", systemImage: "music.note.list")
        case .loaded(let albums):
            AlbumTable(albums: albums, selection: $selection)
        case .failed:
            ContentUnavailableView {
                Label("Couldn't load albums", systemImage: "exclamationmark.triangle")
            } actions: {
                Button("Try Again", action: retry)
                    .accessibilityIdentifier("Library.RetryButton")
            }
        }
    }
}
```

- A drifted or undecodable response is `failed`, never empty. The view shows a message you wrote, never `error.localizedDescription`.
- **Every failure also raises one persistent inline banner inside the window content**, closed only by the user; a background failure never raises a modal alert. Mechanics: `error-handling`.
- Test ids (`accessibilityIdentifier`, PascalCase, dot-separated, static) on every interactive element and container, never the label: `test-ids`.

## Previews

`#Preview("Loaded") { AlbumsContent(state: .loaded(.sample), selection: .constant([]), retry: {}) }` per state: loading, loaded, empty, failed, plus a wide and a narrow window and Dark. Previews build the real view with sample values; no protocol exists just for a preview.

## Performance in views

- Stable ids on every `ForEach`; never `id: \.self` on non-unique values and never an array index.
- Keep `body` cheap: no sorting, formatting setup or `DateFormatter()` inside it; use `FormatStyle`.
- `Table` and `List` for long data; a `LazyVStack` in a `ScrollView` only for non-tabular content. Depth: `performance`.

## Common gotchas

- **A phone layout in a window**: a centred narrow column. Use the sidebar-detail shape and let content use the width.
- **A `Table` inside a `ScrollView`**: it stops virtualizing.
- **A hover-only delete button**: unreachable by touch and keyboard.
- **A context menu with the only copy of an action**: add the menu-bar command.
- **Hiding menu icons by accident**: the 27 SDK hides them; set `.labelStyle(.titleAndIcon)` where an icon carries meaning.
- **`@Environment(\.scenePhase)` read in a leaf** and reloading there: reload in the store, once.

## Validation (exit gate)

- [ ] Every data region renders loading, loaded, empty and failed, and the failure is scoped
- [ ] Selection is a set of stable ids; double-click or Return opens
- [ ] No action exists only in a context menu or on hover
- [ ] Loads are `.task`; nothing does I/O in `body` or `init`
- [ ] Every interactive element and container has a static `accessibilityIdentifier`
- [ ] A `#Preview` per state

## Handoffs

- State, injection, `@FocusedValue` → [`architecture`](../architecture/SKILL.md)
- Colour, density, glass → [`styling`](../styling/SKILL.md)
- Window declaration, utility windows → `windows-and-scenes`; menus → `menus-and-commands`
- Forms → `forms`; accessibility → `accessibility`; test ids → `test-ids`
- AppKit hosting → [`appkit`](../appkit/SKILL.md)
