---
name: appkit
description: Use when a Mac codebase uses AppKit or mixes it with SwiftUI (NSViewController, NSHostingView, Observation). Triggers "embed SwiftUI in AppKit". Not for a new SwiftUI window (ui-components).
disable-model-invocation: true
---

# macOS — AppKit

The lane for apps where AppKit **is** the codebase. **An AppKit codebase is not a defect**: extend it in its own idiom, bridge to SwiftUI where a view earns it, never propose a rewrite. AppKit → SwiftUI screen by screen is `migration`, on request only. Apple's stance: no app needs to be entirely SwiftUI. Audit rows are the `[AppKit]` rows of section D.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| Observation in AppKit | Reads of `@Observable` properties in `draw(_:)`, `updateConstraints()`, `layout()`, `updateLayer()` and the `NSViewController` equivalents are tracked, on by default in the 2026 releases | Back-deploy to macOS 15 with `NSObservationTrackingEnabled` in `Info.plist`; below 15 observe by hand (`withObservationTracking`, or the codebase's own binding) |
| Hosting | `NSHostingView`, `NSHostingController`, `NSViewRepresentable` | macOS 11+ |
| `NSGestureRecognizerRepresentable` | SwiftUI gesture over an AppKit view | Check the availability in the SDK before use |
| `NSHostingMenu` | SwiftUI-built `NSMenu` | macOS 14.4+ |
| `NSHostingSceneRepresentation` | SwiftUI scenes (a `Settings` scene) from an AppKit delegate | macOS 26+ |
| Menu symbols **[mac27SDK]** | Hidden by default: `NSMenuItem.preferredImageVisibility` | — |
| Deployment target | Detected, never raised | Below 13 is this lane only, flagged |

Detect first: storyboards and XIBs, `NSApplicationDelegate`, Objective-C, the existing navigation owner (window controllers, a coordinator), third-party binding libraries. **Match what is there.**

## When to use

- Adding or changing a view or window controller in an AppKit app
- Embedding SwiftUI in AppKit, or an AppKit view in SwiftUI
- Input handling, key-view loop, menus, state restoration in AppKit
- Observation in AppKit views

## When NOT to use

- A new SwiftUI window in a mostly-SwiftUI app → [`windows-and-scenes`](../windows-and-scenes/SKILL.md), [`ui-components`](../ui-components/SKILL.md)
- Rewrites, Catalyst → native, Objective-C → Swift → `migration`
- State ownership → [`architecture`](../architecture/SKILL.md)
- Colour, glass → `styling`
- iOS UIKit → `mobile-ios:uikit`; Windows → `desktop-windows:wpf`

## View controllers — small, owned, cancelled

```swift
final class AlbumsViewController: NSViewController {
    private let model: LibraryModel
    private var loadTask: Task<Void, Never>?

    init(model: LibraryModel) {
        self.model = model
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { nil }

    override func viewDidAppear() {
        super.viewDidAppear()
        loadTask = Task { await model.load() }
    }

    override func viewDidDisappear() {
        super.viewDidDisappear()
        loadTask?.cancel()
    }
}
```

Initializer injection; no service locator, no `NSApp.delegate as! AppDelegate` reach-through. An `@IBOutlet` is the one force-unwrap the house rules allow. Loads run in a stored `Task` cancelled when the view goes; nothing blocks the main thread.

## Observation in AppKit

```swift
override func layout() {
    super.layout()
    titleField.stringValue = model.title
}
```

With tracking on, the read of `model.title` inside `layout()` schedules a new layout when it changes: no manual `needsLayout` or `needsDisplay`. Reads outside the listed methods are not tracked. A target below the 2026 releases and below macOS 15 observes by hand.

## Hosting SwiftUI in AppKit

```swift
let host = NSHostingController(rootView: InspectorView().environment(model))
addChild(host)
view.addSubview(host.view)
host.view.translatesAutoresizingMaskIntoConstraints = false
NSLayoutConstraint.activate([
    host.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
    host.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
    host.view.topAnchor.constraint(equalTo: view.topAnchor),
    host.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
])
```

- A hosting controller is **added as a child** (`addChild`) or `NSHostingView` is constrained; an unconstrained host has no size. Set `sizingOptions` where the SwiftUI view should drive the window.
- Pass the model by `environment`, once; do not copy state into the host.
- An app already driven by an AppKit delegate adds a `Settings` scene with `NSHostingSceneRepresentation` (macOS 26+) instead of a hand-built preferences window.

## AppKit inside SwiftUI — `NSViewRepresentable`

`makeNSView` creates the view once; `updateNSView` applies new inputs and must be idempotent; a `Coordinator` owns delegates and target-action; `dismantleNSView` cancels work. Never create state in `updateNSView`. Interop is a last resort for a control SwiftUI lacks.

## Input

- **Gesture recognizers and control events** (`addTarget(_:action:for: .trackingEndedOutside)`) over `mouseDown:` and tracking loops; view-based selection, menu and drag APIs.
- **27 SDK**: only the initially hit-tested hierarchy activates recognizers (`exclusiveGestureBehavior`; opt out with `NSViewGestureRecognizerIsExclusive`); stuck gestures auto-cancel; a custom `NSGestureRecognizer` overrides `location(in:)` because the base returns zero.
- `NSTextSelectionManager` (27) gives text selection to a custom view; `NSRefreshController` adds pull-to-refresh to an `NSScrollView`.
- Touch Macs ship since 2026-11-06: no hover-only control.

## Menus and the responder chain

Commands are `@IBAction` on the responder chain, enabled through `validateMenuItem(_:)` / `NSUserInterfaceValidations` — **disabled, never hidden** (`menus-and-commands`). Standard menu order and shortcuts hold. A SwiftUI-built menu in AppKit is an `NSHostingMenu`. Show a menu image on the 27 SDK with `preferredImageVisibility`.

## Windows, keyboard, restoration, quit

| Rule | How |
|---|---|
| Key-view loop | `window.autorecalculatesKeyViewLoop = true` |
| Restoration | Window identifier, `isRestorable`, `restorationClass`; encode in `encodeRestorableState(with:)`, call `invalidateRestorableState()` on change; **never encode document or database data**; always call the restoration completion handler |
| Graceful quit | `preventsApplicationTerminationWhenModal = false` on non-critical sheets; `applicationShouldTerminate` asks about unsaved work |
| Titlebar accessories | May draw outside their bounds on the 27 SDK (glass shadows) |
| Concentric corners | `NSView.cornerConfiguration = .containerConcentric(minimum:)` (27) |

## Common gotchas

- **`mouseDown:` for a click**: use a recognizer or control action.
- **An unconstrained `NSHostingView`**: zero size.
- **A hosting controller never added as a child**: lifecycle and focus break.
- **Observation read in an unlisted method**: never tracked.
- **Encoding records in restoration state**: stale or huge; ids only.
- **A force-unwrapped delegate or window**: guard it; outlets are the exception.
- **Menu item hidden in `validateMenuItem`**: disable it.

## Handoffs

- AppKit → SwiftUI, Catalyst → native → `migration`
- State and injection → [`architecture`](../architecture/SKILL.md)
- Windows and scenes → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- Menus → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- iOS counterpart → `mobile-ios:uikit`
