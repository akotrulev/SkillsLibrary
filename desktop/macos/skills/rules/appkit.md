---
paths:
  - "**/*{Controller,Cell,Delegate,Representable,Window,ViewController}.swift"
  - "**/{Controllers,ViewControllers,WindowControllers,AppKit}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): AppKit. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its AppKit code. -->

# AppKit standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Extend AppKit in AppKit. No "this should be SwiftUI" finding, no unrequested rewrite, no `.xib` removal side quest; `@Observable` is not introduced into a KVO or Combine codebase as a drive-by. *minor*
- Controllers take dependencies in `init`, never through a singleton or a later-set optional. *major*
- Delegates and data sources are `weak`; no retain cycle through a stored closure, delegate, `Timer` or notification token. *major*
- A `Task` or observer a controller starts is cancelled when its window or view goes. *major*
- Nothing blocks the main thread: no synchronous disk, network or database work in `viewDidLoad`, `awakeFromNib` or an action. *blocker*
- Menus are validated through `NSMenuItemValidation` or `validateUserInterfaceItem`; an unavailable item is disabled, not removed. *major*
- Auto Layout with the safe-area and layout guides; no frame math for adaptive layout, no `DispatchQueue.main.asyncAfter` to fix layout timing, no `needsLayout` sprinkled to hide an ordering bug. *major*
- Input is handled by gesture recognizers and the responder chain: actions go to `nil` targets so the chain finds them; no `mouseDown:` override where a recognizer does it. *minor*
- The key-view loop is complete and visible; custom controls are focusable and answer Space, Return, arrows and Escape. *major*
- SwiftUI is hosted as a proper child (`NSHostingController`, `NSHostingView` pinned with constraints); one owner of navigation per window; `NSViewRepresentable`: build in `make`, apply state idempotently in `update`, delegates in the `Coordinator`, cleanup in `dismantle`; never mutate SwiftUI state from `updateNSView`; no representable for what `TextField`, `Table` or `Map` already does. *major*
- `@Observable` reads inside `draw(_:)`, `layout()` and `updateConstraints()` are tracked on current SDKs; back-deployed below macOS 15 they need `NSObservationTrackingEnabled` or explicit `withObservationTracking`. *major*
- Documents: `NSDocument` keeps autosave, versions and undo registration; no hand-rolled autosave timer. *major*
