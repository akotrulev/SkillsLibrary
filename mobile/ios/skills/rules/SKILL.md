---
name: rules
description: Use when installing or updating the mobile-ios coding standards as path-scoped rules in .claude/rules/mobile-ios/. Triggers "install the iOS rules". Not for reviewing code (conventions-review).
disable-model-invocation: true
---

# Install the mobile-ios rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a view never pays for the view rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `swift.md`: simplicity, safety, concurrency, state and DI, errors, logging, secrets, permissions, launch, comments | any `*.swift` |
| `swiftui.md`: `body`, `.task`, region states, lists, navigation, forms, previews | `*View` / `*Screen` / `*Row` / `*Sheet` / `*Form` files, `Views/`, `Screens/`, `Components/`, `UI/` |
| `ios-accessibility.md`: accessibility, test ids | the SwiftUI paths plus `*Controller` / `*Cell` files, `Controllers/`, `ViewControllers/` |
| `ios-styling.md`: Liquid Glass, colour, type, adaptive layout, motion | the same UI paths plus `Theme/`, `DesignSystem/` |
| `ios-localization.md`: String Catalogs, plurals, RTL, `FormatStyle` | the `ios-accessibility.md` paths plus `*.xcstrings` |
| `uikit.md` | `*Controller` / `*Cell` / `*Delegate` / `*Representable` files, `Controllers/`, `ViewControllers/`, `UIKit/` |
| `swift-networking.md` | `*Client` / `*API` / `*Endpoint(s)` / `*Socket` files, `Networking/`, `Network/`, `API/` |
| `swift-persistence.md`: SwiftData, Core Data, GRDB, Keychain, files | `*Store` / `*Storage` / `*Keychain` / `*Database` / `*Persistence` / `*Schema` / `*Migration` files, `Persistence/`, `Storage/`, `Database/`, `Store/`, `.xcdatamodeld` |
| `swift-tests.md` | `*Tests/` folders (SPM `Tests/` included), `*Tests` / `*Test` files |
| `xcode-config.md`: secrets, ATS, usage strings, privacy manifest, language mode, isolation, packages | `*.xcconfig`, `*Info.plist`, `*.entitlements`, `*.xcprivacy`, `Package.swift`, `Project.swift`, `project.pbxproj`, `Podfile` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/mobile-ios/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all ten `.md` rule files above exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/mobile-ios` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to this project.** The default globs follow common file naming; a feature-folder layout (`Features/Orders/OrderDetail.swift`) often matches none of them. Find where each kind of file actually lives, leaving test files out of the first four:
   - views: `git grep -l -e ': View {' -e 'some View' -- '*.swift'` (`swiftui.md`, `ios-accessibility.md`, `ios-styling.md`, `ios-localization.md`)
   - UIKit: `git grep -l -e 'UIViewController' -e 'UIViewRepresentable' -e 'UITableViewCell' -e 'UICollectionViewCell' -- '*.swift'` (`uikit.md`, `ios-accessibility.md`, `ios-styling.md`, `ios-localization.md`)
   - networking: `git grep -l -e 'URLSession' -e 'URLRequest' -e 'URLSessionWebSocketTask' -- '*.swift'` (`swift-networking.md`)
   - persistence: `git grep -l -e '@Model' -e '@ModelActor' -e 'ModelContainer' -e 'NSManagedObject' -e 'SecItem' -e 'DatabaseQueue' -e 'DatabasePool' -- '*.swift'` (`swift-persistence.md`)
   - tests: `git grep -l -e 'import Testing' -e 'import XCTest' -- '*.swift'` (`swift-tests.md`)

   For each file a search lists that its rule file's globs miss, propose the narrowest directory globs that cover them (for example `"**/Features/*/Views/**/*.swift"` or `"**/Sources/OrdersKit/Networking/**/*.swift"`) and add them to the installed copy with the user's agreement. Prefer a folder glob to `**/*.swift`, which would load every view rule into model and service work.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/mobile-ios/swift.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Swift or iOS rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
mobile-ios rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/mobile-ios/
Paths: default | widened: <file> += <globs>   (one line per widened file)
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
