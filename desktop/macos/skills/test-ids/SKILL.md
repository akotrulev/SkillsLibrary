---
name: test-ids
description: Use when adding accessibilityIdentifier so Appium Mac2 can target a SwiftUI or AppKit Mac app. Triggers "E2E can't find this element". Not for writing desktop tests (qa-desktop-typescript).
disable-model-invocation: true
---

# macOS: Testability (`accessibilityIdentifier` writer)

Adds and audits `accessibilityIdentifier` on SwiftUI and AppKit views so desktop suites locate elements by one stable id. It is the dev-side half of a loop QA owns: `qa-desktop-<lang>`'s explorer reads the live page source and files a `missing-testids.md`; this skill consumes that report. Sibling and contract source: [`mobile-ios:test-ids`](../../../../mobile/ios/skills/test-ids/SKILL.md): the naming, static-row and "one attribute only" rules carry over unchanged. Windows peer: `desktop-windows:test-ids` (`AutomationId`). Audit rows are section R of `desktop-macos:standards-audit`.

## Version lane

| Concern | Detail |
|---|---|
| SwiftUI | `.accessibilityIdentifier(_:)`, macOS 11+, the same on 14, 15, 26 and the 27 SDK |
| AppKit | `NSAccessibilityProtocol`: `setAccessibilityIdentifier(_:)` / `accessibilityIdentifier()` (macOS 10.10+) on any `NSView`, `NSCell`, `NSToolbarItem` view |
| Driver | Appium **Mac2 4.6.1** on Appium 3 (Mac2 5.x needs Appium 4, still beta on 2026-11-15). Host macOS 11.3+, Xcode 13+ |
| Cost | A string per element; an id on every decorative view is still noise in the page source |
| `[mac27SDK]` | A SwiftUI `Menu` with a plain or custom button style now exposes `AXTitle`, not `AXDescription`: re-read the page source of such a menu after upgrading |

## The contract: one id, what Mac2 reads (verified 2026-11-15)

Verified against the Mac2 driver's locator-strategies and element-attributes pages: the `accessibility id`, `id` and `name` strategies are **all aliases** of the element's XCTest **`identifier`** attribute (`accessibilityIdentifier`); `className` maps to `elementType`; `predicate string` and `class chain` are native XCTest locators and can reference `identifier`; `xpath` is slow and runs over the driver's page source.

| Element kind | Identifier you set | What Mac2 reads | Locator for `Library.SearchField` |
|---|---|---|---|
| `Button`, `Toggle`, `TextField`, `SecureField`, `Picker`, `Stepper`, `Slider`, `Link` | `.accessibilityIdentifier("Library.SearchField")` on the control | `identifier` | `accessibility id` `Library.SearchField` (or `id` / `name`, the same) |
| `Table`, `List`, `OutlineGroup`, sidebar `List` | The id on the **container** | `identifier` of the table / outline | `accessibility id` `Library.AlbumTable`; rows found inside it |
| A row (`Table` row, `List` row) | One static id on the row content: `Library.Row`; children `Library.Row.Title` | `identifier` of each | `class chain` / `predicate string` `identifier == "Library.Row"` inside the container, addressed by index |
| Sidebar item, tab, segmented control segment | The id on the item's content | `identifier` | `accessibility id` `Sidebar.Albums` |
| Toolbar item (`ToolbarItem`, `NSToolbarItem`) | The id on the item's control | `identifier` | `accessibility id` `Library.Toolbar.Add` |
| Region state, banner, close button | `Albums.Loading`, `Albums.Error`, `Albums.Stale`, `Notifications.Banner`, `Notifications.Banner.Close` | `identifier` | `accessibility id` for each |
| Sheet or `Settings` window root and its controls | The id on each control, and one on the root container | `identifier` | `accessibility id` after switching to the window |
| `NSOpenPanel`, `NSSavePanel`, `NSAlert`, system permission prompts | **Not taggable** | the system's own labels | `predicate string` on `label` / `title`; keep the app's own pre-prompt controls tagged |
| Menu bar items | **Not verified here** (a SwiftUI command's identifier may not reach the menu item) | `title` | `predicate string` on `title`; confirm in a real page source |
| Decorative image, spacer, layout stack | **None** | n/a | n/a |

The accessibility **label** (`accessibilityLabel`) is for people: translated, spoken by VoiceOver, edited with copy. It is never an identifier, and an identifier is never copied into a label. Mac2's `label` attribute is the label and `identifier` is the id: a locator on `label` is a label locator.

Facts QA needs from the same pages: Mac2 runs **one session at a time** (parallel Mac2 instances are highly discouraged); finding, clicking and typing need no Accessibility permission, but moving or resizing windows does; `useDomIdAsAccessibilityId` maps `WKWebView` DOM ids and needs that permission. The page source of the **same build** is the final authority; the explorer records both `identifier` and `label`.

## Output format

One modifier only: `.accessibilityIdentifier("…")` (`setAccessibilityIdentifier` in AppKit). **Never `accessibilityLabel` as the identifier, and never label text copied into the id.** PascalCase, dot-separated segments.

## The rules

### 1. Where the modifier goes

| Element | How |
|---|---|
| Control | On the control: `Button("Add") { … }.accessibilityIdentifier("Library.AddButton")` |
| `Table` / `List` | On the **container**: `Table(...) { … }.accessibilityIdentifier("Library.AlbumTable")` |
| `NavigationSplitView` sidebar | On the sidebar `List`, and on each item's content |
| Toolbar item | On the control inside the `ToolbarItem` |
| Custom view you own | Takes a `testIdPrefix: String` and composes its own suffix (rule 4) |
| `[AppKit]` | `button.setAccessibilityIdentifier("Library.AddButton")` in the view's setup; a cell view sets it on its subviews |
| System panels and alerts | Not taggable: QA locates them by system label (and the OS language) |

Prefer inline. Do **not** add `AppButton` / `AppField` wrappers just to carry ids (CLAUDE.md § Simplicity).

### 2. Naming: `Window.ElementType[.Qualifier]`

PascalCase, dot-separated; no spaces, kebab-case, numeric ids, GUIDs, indexes or state values.

- **Window / component**: from the view or controller name. `LibraryView.swift` → `Library`; `AlbumInspector.swift` → `Library.Inspector`; `SettingsView` → `Settings`. Drop the `View` / `Window` / `ViewController` suffix.
- **ElementType**: the role: `SearchField`, `AddButton`, `AlbumTable`, `Row`, `Banner`.
- **Qualifier**: a semantic name (enum case, field name, action), never an id.

```
Library.SearchField       Library.AddButton       Library.AlbumTable
Library.Row               Library.Row.Title       Library.Row.Status
Sidebar.Albums            Settings.General.LaunchAtLogin
Notifications.Banner.Close
```

### 3. Constants for repeated ids

A static id used more than once is a `static let` in a nested `enum` per window; three or more sites sharing a prefix extract it:

```swift
private enum TestID {
    static let prefix = "Library"
    static let search = "\(prefix).SearchField"
    static let add = "\(prefix).AddButton"
}

TextField("Search", text: $query).accessibilityIdentifier(TestID.search)
Button("Add", action: addAlbum).accessibilityIdentifier(TestID.add)
```

A single-use id stays an inline literal.

### 4. Components compose their suffix

```swift
struct StatusBadge: View {
    let status: AlbumStatus
    var testIdPrefix = ""

    var body: some View {
        Text(status.title)
            .accessibilityIdentifier("\(testIdPrefix).StatusBadge")
    }
}
```

The caller passes the **prefix only**: `StatusBadge(status: album.status, testIdPrefix: "Library.Inspector")` → `Library.Inspector.StatusBadge`. Only the terminal view appends.

### 5. Which elements get one

Tag every interactive element (button, toggle, field, picker, sidebar item, toolbar item, sheet action), **every list / table / outline container**, and the read anchors a test asserts: totals, status text, banners, empty states. Tag the **states of every data region and the banner** (`<Region>.Loading`, `.Error`, `.Retry`, `.Empty`, `.Stale`, `Notifications.Banner`, `Notifications.Banner.Close`) so a test tells a **failed** region from an **empty** one ([`error-handling`](../error-handling/SKILL.md)). Tag the permission pre-prompt and denied screens ([`sandbox-and-permissions`](../sandbox-and-permissions/SKILL.md)).

Skip layout stacks, spacers, decorative images (`Image(decorative:)`) and wrappers.

### 6. Rows: one static locator, addressed by index

A row view **must not** take a per-row id for its identifier. The parent locator is a hard-coded constant; children namespace under it; tests address a row **by index** over the shared locator.

```swift
struct AlbumRow: View {
    let album: Album
    private static let id = "Library.Row"

    var body: some View {
        HStack {
            Text(album.title).accessibilityIdentifier("\(Self.id).Title")
            Text(album.status.title).accessibilityIdentifier("\(Self.id).Status")
        }
    }
}
```

`Table` / `ForEach` identity still uses the **stable domain id** (`Identifiable`): identity is unique per row, the test id is static so the set is selectable. Identical ids across rows are intended; `findElements` plus an index selects one. A role that appears twice in a row sub-namespaces (`Library.Row.Total`, `Library.Row.Refund.Total`). In a `Table`, put the id on each column's cell content; **confirm in the page source** that cell ids reach the cell elements.

### 7. Derive from data in scope, not lookup tables

```swift
ForEach(SidebarItem.allCases) { item in
    Label(item.title, systemImage: item.symbol)
        .accessibilityIdentifier("Sidebar.\(item.rawValue.capitalized)")
}
```

No hand-maintained `[Enum: String]` dictionary of ids: it drifts when a case is renamed.

### 8. Multi-window: ids repeat across windows, so the window is the scope

Two document windows carry the same ids. Mac2 sees them under **separate window elements**, so a test selects the window first, then the id inside it. Never encode a window or document number into an id; a window-level container id (`Library.Window`) on the root view gives the test an anchor.

### 9. Grouping changes what is reachable

- **`.accessibilityElement(children: .combine)`** merges children into one accessibility element: child identifiers are not exposed, so `Library.Row.Title` inside a combined row is unreachable while the row's own id is. Assert on the row, or use `.accessibilityElement(children: .contain)` where children must be addressed, and weigh it against VoiceOver's reading ([`accessibility`](../accessibility/SKILL.md)).
- **An identifier on a container can be applied to unlabelled elements inside it** (varies by container type and SDK): tag the leaves explicitly and **confirm in the page source** that a container id did not replace a child's.
- `.accessibilityElement(children: .ignore)` plus an explicit label makes one element with the identifier you gave: the right form for a custom control drawn from many views.
- (From XCUITest experience; not re-verified against Apple documentation. Check the page source of a real build.)

## Consuming a `missing-testids.md`

QA's explorer writes, per window, a table of `Element | Type | Visible text / label | Suggested id | Fallback locator in use`.

1. Treat each row as a rule 5 candidate and derive its id by rules 2 to 7. **The "Suggested" column is a hint**, not the id: this library's convention is PascalCase dot-separated.
2. Rows with a brittle fallback (an index XPath, a class chain) first.
3. A row rule 5 calls decorative: do not tag; list it back so QA re-anchors.
4. Reply with `Element → assigned id → file:line`, plus counts and **collisions** (the same id on two distinct, non-row elements; these block completion).
5. A fallback on `label` or `title` is a **label**, not an identifier: assign the identifier anyway and tell QA the label is no longer a locator.

## Procedure

1. Confirm scope (a file, a feature folder or a `missing-testids.md`); do not rewrite the whole tree unasked.
2. For each target file, derive the window name; walk the view body; apply rules 1 to 7; skip decoratives and list them.
3. For a grouped element, decide the reachable level (rule 9) and say which.
4. Report per file: ids added, decoratives skipped, collisions, grouping that hides children.
5. Build the target; where a Mac2 session is available, read one window's page source and confirm `identifier` matches each assigned id.

## Rule file

The review form of these rules, with severities, is the desktop-macos rule file `mac-accessibility.md` (Test ids) in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs it), or the plugin's copy when the project has none. Where it and this skill disagree, the rule file wins.
