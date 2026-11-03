---
paths:
  - "**/*{Controller,Cell,Delegate,Representable}.swift"
  - "**/{Controllers,ViewControllers,UIKit}/**/*.swift"
---

<!-- mobile-ios rules v1 (2026-11-03): UIKit. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its UIKit code. -->

# UIKit standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Extend UIKit in UIKit. No "this should be SwiftUI" finding, no unrequested rewrite, no storyboard-removal side quest; `@Observable` is not introduced into a Combine or KVO codebase as a drive-by. *minor*
- A scene delegate owns the window; the app delegate does not. *major*
- Controllers take dependencies in `init`, never through a singleton or a later-set optional. *major*
- Delegates are `weak`; no retain cycle through a stored closure, delegate or `Timer`. *major*
- A `Task` or observer a controller starts is cancelled when the screen goes. *major*
- Collections use diffable data sources with stable ids, compositional layout for new ones; no `reloadData()` for an ordinary update. *minor*
- Auto Layout with the safe-area and keyboard layout guides, Dynamic Type through `UIFontMetrics`. No `UIScreen.main.bounds` or frame math for adaptive layout, no `DispatchQueue.main.asyncAfter` to fix layout timing, no `layoutIfNeeded()` sprinkled to hide an ordering bug, no `UIWebView`. *major*
- SwiftUI is hosted as a proper child (`UIHostingController`, `UIHostingConfiguration` for cells); no second navigation stack inside a pushed host; one owner of navigation per stack. *major*
- `UIViewRepresentable`: build in `make`, apply state idempotently in `update`, delegates in the `Coordinator`, cleanup in `dismantle`; never mutate SwiftUI state from `updateUIView`; no representable for what `TextField`, `Map` or `PhotosPicker` already does. *major*
