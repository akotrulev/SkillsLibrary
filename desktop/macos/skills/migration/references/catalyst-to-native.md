# Mac Catalyst → native macOS

Only on request, and only when the Catalyst app is a Mac product that has outgrown "the iPad app on a Mac": the platform-conventions rule says a Mac app looks and behaves like a Mac app, and a Catalyst app with the iPad idiom (touch-sized controls, `UIKit` navigation, no real menu bar) usually does not. A Catalyst app that meets the desktop rules is not a defect.

## 0. Inventory

```bash
rg -n "SUPPORTS_MACCATALYST|DERIVE_MACCATALYST_PRODUCT_BUNDLE_IDENTIFIER|TARGETED_DEVICE_FAMILY" -g '*.pbxproj' -g '*.xcconfig'
rg -ln "targetEnvironment\(macCatalyst\)" -g '*.swift'
rg -ln "UIViewController|UIKit" -g '*.swift' | wc -l
rg -ln "import SwiftUI" -g '*.swift' | wc -l
```

Record: scenes and their `UIWindowSceneDelegate`s, the `UIMenuBuilder` menu code, the toolbar (`NSToolbar` bridged), the Mac-only branches under `targetEnvironment(macCatalyst)`, and the UIKit-only dependencies. The share of SwiftUI against UIKit decides the size of the job: SwiftUI screens carry over, UIKit view controllers are each an AppKit or SwiftUI rewrite ([`appkit-to-swiftui`](appkit-to-swiftui.md)).

## 1. Order

1. **Extract the shared code into local packages** (models, networking, persistence, formatting) that build for both macOS and the Catalyst target. This is the leaf work and ships on the Catalyst app unchanged.
2. **Add a native macOS app target** beside the Catalyst one, with its own bundle identifier decision, sandbox entitlements and `Info.plist` ([`project-setup`](../../project-setup/SKILL.md)). The Catalyst target keeps shipping until the native one reaches parity.
3. **Move scene by scene**: SwiftUI scenes (`WindowGroup`, `Settings`, `MenuBarExtra`) are rebuilt with Mac conventions; a UIKit screen is re-implemented in SwiftUI.
4. **Rebuild the menu bar and toolbar natively** (`commands`, `.toolbar`); the `UIMenuBuilder` code is deleted, not translated ([`menus-and-commands`](../../menus-and-commands/SKILL.md)).
5. **Cut over the distribution**: same product, new binary. Decide the bundle identifier early: keeping it lets the update replace the Catalyst app; a new one is a new product. Keychain access groups, App Group containers and the sandbox container differ between the two binaries, so storage and credentials need a migration step that reads the old container once ([`offline-and-storage`](../../offline-and-storage/SKILL.md), [`sandbox-and-permissions`](../../sandbox-and-permissions/SKILL.md)).
6. **Delete the Catalyst target last**, and its `targetEnvironment(macCatalyst)` branches.

## Verify

- The native app opens the Catalyst app's documents and data, signed in, on an upgrade install; test it on a machine that still has the Catalyst build installed.
- Notarization and the entitlements file pass for the new target ([`desktop/_shared/distribution`](../../../../_shared/distribution/SKILL.md)).
- Keyboard-first pass, menu bar order, window restoration, VoiceOver, `accessibilityIdentifier`s kept stable for the QA suite.

## Do not

- Convert and redesign in one step.
- Ship two binaries under one bundle identifier.
- Delete the Catalyst target before an upgrade-install test has passed.
