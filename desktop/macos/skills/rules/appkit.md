---
paths:
  - "**/*{Controller,Cell,Delegate,Representable,Window,ViewController}.swift"
  - "**/{Controllers,ViewControllers,WindowControllers,AppKit}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): AppKit. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its AppKit code. -->

# AppKit standards

Severity tags as in the core Swift rules. The codebase wins where it consistently does otherwise. Recipe: `appkit`.

- Extend AppKit in AppKit: no "this should be SwiftUI" finding, no unrequested rewrite, no `@Observable` drive-by into a KVO or Combine codebase. *minor*
- Controllers take dependencies in `init`, never through a singleton or a later-set optional. *major*
- Delegates and data sources are `weak`; no retain cycle through a stored closure, `Timer` or notification token. *major*
- A `Task` or observer a controller starts is cancelled when its window or view goes. *major*
- No synchronous disk, network or database work in `viewDidLoad`, `awakeFromNib` or an action. *blocker*
- Menus are validated through `NSMenuItemValidation` or `validateUserInterfaceItem`; an unavailable item is disabled, not removed. *major*
- Auto Layout with layout guides; no frame math for adaptive layout, no `asyncAfter` to fix layout timing. *major*
- Actions go to `nil` targets so the responder chain finds them; no `mouseDown:` override where a recognizer does it. *minor*
- The key-view loop is complete and visible; custom controls are focusable and answer Space, Return, arrows and Escape. *major*
- SwiftUI is hosted as a proper child (`NSHostingController`, `NSHostingView` pinned with constraints); an `NSViewRepresentable` builds in `make`, applies state idempotently in `update`, keeps delegates in the `Coordinator` and cleans up in `dismantle`. *major*
- `@Observable` reads inside `draw(_:)` and `layout()` back-deployed below macOS 15 need `NSObservationTrackingEnabled` or `withObservationTracking`. *major*
- `NSDocument` keeps autosave, versions and undo registration; no hand-rolled autosave timer. *major*
