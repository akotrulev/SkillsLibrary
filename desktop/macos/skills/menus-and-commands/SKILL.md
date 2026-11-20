---
name: menus-and-commands
description: Use when adding Mac menu bar commands, shortcuts or context menus (CommandMenu, FocusedValue). Triggers "add a menu item". Not for windows or toolbars (windows-and-scenes).
disable-model-invocation: true
---

# macOS — Menus and Commands

**Every command lives in the menu bar**, in the standard order, with its standard shortcut. Toolbars and context menus are shortcuts to it. Audit rows are section F of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| `commands`, `CommandMenu`, `CommandGroup`, `.keyboardShortcut`, `@FocusedValue`, `focusedSceneValue` | macOS 12+ | `focusedSceneObject` macOS 13+ |
| `openSettings`, `onKeyPress`, `InspectorCommands` | macOS 14+ | — |
| `NSHostingMenu` (SwiftUI-built `NSMenu`) | macOS 14.4+ | AppKit apps (`appkit`) |
| **Menu symbols hidden by default [mac27SDK]** | Linking the 27 SDK hides symbol images in the menu bar and context menus; Settings, Share and Print keep theirs | Show one with `.labelStyle(.titleAndIcon)` (SwiftUI) or `NSMenuItem.preferredImageVisibility` (AppKit) |
| `LabeledContent` in a `Menu` becomes the item subtitle **[mac27SDK]** | 27 SDK | — |
| `Picker`/`Menu` no longer backed by `NSPopUpButton` **[mac27SDK]** | 27 SDK | Do not reach into the AppKit control |

Design facts: HIG "The menu bar" via `design/ui-ux-pro-max` `--stack swiftui`. The corpus wins.

## When to use

- A new command, shortcut or menu; renaming or moving one
- Replacing a standard group (New, Undo, Pasteboard)
- A command that acts on the focused window's selection
- A context menu; a menu item that vanishes

## When NOT to use

- Scenes and `openWindow` → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- Document commands (Save, Revert) → [`documents`](../documents/SKILL.md)
- Shared state ownership → [`architecture`](../architecture/SKILL.md)
- Keyboard accessibility of controls → `accessibility`
- AppKit `NSMenu` / responder chain → [`appkit`](../appkit/SKILL.md); Windows → `desktop-windows:windows-and-navigation`

## The standard menu order

App · File · Edit · Format · View · *app-specific menus* · Window · Help.

| Menu | Holds |
|---|---|
| App | About (own group), Settings… (⌘,), Services, Hide / Hide Others / Show All, Quit |
| File | New, Open…, Open Recent, Close, Save, Duplicate (prefer over Save As), Rename…, Move To…, Export As…, Revert To, Print… |
| Edit | Undo / Redo, Cut / Copy / Paste, Select All, Find |
| View | Sidebar, toolbar, inspector, full screen |
| Window | Minimize, Zoom, window list |

Keep the system menus and their order. Standard items keep standard shortcuts; a custom shortcut only when no standard one fits. An item that needs more input ends with an ellipsis (`Open…`). Custom menus sit between View and Window.

## Declare commands

```swift
struct AlbumCommands: Commands {
    @FocusedValue(\.selectedAlbum) private var album

    var body: some Commands {
        CommandGroup(replacing: .newItem) {
            Button("New Album…") { /* post to the focused window */ }
                .keyboardShortcut("n")
        }
        CommandMenu("Album") {
            Button("Rename…") { album?.beginRename() }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(album == nil)
            Button("Delete") { album?.delete() }
                .keyboardShortcut(.delete)
                .disabled(album == nil)
        }
    }
}
```

`WindowGroup { … }.commands { AlbumCommands() }`.

### Focused values: how a command finds its target

A command never holds the model. The focused window **publishes** what it can act on; the command reads it.

```swift
extension FocusedValues {
    @Entry var selectedAlbum: AlbumActions?
}

struct AlbumWindow: View {
    @State private var selection: Album.ID?
    @Environment(LibraryModel.self) private var library

    var body: some View {
        AlbumList(selection: $selection)
            .focusedSceneValue(\.selectedAlbum, actions)
    }
}
```

- `focusedSceneValue` (whole window) over `focusedValue` (only while a view in the hierarchy is focused) for window-level commands.
- The value is **nil when no window is focused**, and the item is then `.disabled`, not removed.
- `@Entry` has no default instance with behavior (see `architecture`): the default is `nil`.
- `UtilityWindow` sees the focused main window's values, so a palette acts on the document behind it.

## Disabled, never hidden

HIG: "always show the same set of menu items … disable the action instead of hiding it." A menu whose items appear and disappear teaches users nothing and breaks muscle memory.

```swift
Button("Export…") { export() }.disabled(!canExport)
```

Never `if canExport { Button(…) }` inside `commands`. A whole `CommandMenu` stays present too. (The one legitimate swap is a toggle title — "Show Inspector" / "Hide Inspector" — which is one item with two titles.)

## Menu icons on the 27 SDK

Menus hide symbol images by default. Keep the default — text-only menus are the new look. Add `.labelStyle(.titleAndIcon)` only where the icon carries meaning the title does not (a status colour, a tool glyph). Never rely on an icon to tell two items apart. Context menus behave the same.

## Context menus

`.contextMenu { … }` holds the **same commands** the menu bar has, scoped to the clicked item. A context-menu-only action is a defect: it is unreachable from the keyboard and on touch Macs it needs a long press. Selection stays when the menu opens.

## Keyboard

- Every menu item has a shortcut where it is frequent; none collides with a system shortcut (⌘Q, ⌘H, ⌘W, ⌘,).
- `onKeyPress` handles keys inside a focusable view; it does not replace a menu command.
- The key-view loop and Full Keyboard Access belong to `forms` and `accessibility`.

## Common gotchas

- **`if` around a command**: hidden item; use `.disabled`.
- **A command holding the model**: acts on the wrong window; read `@FocusedValue`.
- **`focusedValue` on a leaf for a window command**: nil when focus is elsewhere; use `focusedSceneValue`.
- **Custom shortcut on a standard action**: removes the user's habit.
- **A toolbar button with no menu item**: add the command.
- **Icons expected on the 27 SDK**: set `.titleAndIcon` explicitly.
- **A second Settings entry**: `Settings` already adds it.

## Handoffs

- Window opening → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- Document menu items → [`documents`](../documents/SKILL.md)
- `NSMenu`, `NSHostingMenu`, responder chain → [`appkit`](../appkit/SKILL.md)
- Test ids on menu items → `test-ids`
