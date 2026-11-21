---
name: rules
description: Use when installing or updating the mobile-ios coding standards in .claude/rules/mobile-ios/. Triggers "install the iOS rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the mobile-ios rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

Rule files beside this SKILL.md, in the order the steps below refer to them:

- `swift.md`
- `swiftui.md`
- `ios-accessibility.md`
- `ios-styling.md`
- `ios-localization.md`
- `uikit.md`
- `swift-networking.md`
- `swift-persistence.md`
- `swift-tests.md`
- `xcode-config.md`

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/mobile-ios/`.

## Run by a model

A model runs this skill itself, as `mobile-ios:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/mobile-ios/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/mobile-ios` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to this project.** The default globs follow common file naming; a feature-folder layout (`Features/Orders/OrderDetail.swift`) often matches none of them. Find where each kind of file actually lives, leaving test files out of the first four:
   - views: `git grep -l -e ': View {' -e 'some View' -- '*.swift'` (`swiftui.md`, `ios-accessibility.md`, `ios-styling.md`, `ios-localization.md`)
   - UIKit: `git grep -l -e 'UIViewController' -e 'UIViewRepresentable' -e 'UITableViewCell' -e 'UICollectionViewCell' -- '*.swift'` (`uikit.md`, `ios-accessibility.md`, `ios-styling.md`, `ios-localization.md`)
   - networking: `git grep -l -e 'URLSession' -e 'URLRequest' -e 'URLSessionWebSocketTask' -- '*.swift'` (`swift-networking.md`)
   - persistence: `git grep -l -e '@Model' -e '@ModelActor' -e 'ModelContainer' -e 'NSManagedObject' -e 'SecItem' -e 'DatabaseQueue' -e 'DatabasePool' -- '*.swift'` (`swift-persistence.md`)
   - tests: `git grep -l -e 'import Testing' -e 'import XCTest' -- '*.swift'` (`swift-tests.md`)
   - lint config: `git ls-files -- '*.swiftlint.yml' '*.xcconfig' '*Package.swift'`. `xcode-config.md` matches `.swiftlint.yml` at any depth, so the root file and each tests folder's child file load it; propose a glob only for a lint config kept under another name.

   For each file a search lists that its rule file's globs miss, propose the narrowest directory globs that cover them (for example `"**/Features/*/Views/**/*.swift"` or `"**/Sources/OrdersKit/Networking/**/*.swift"`) and add them to the installed copy with the user's agreement. Prefer a folder glob to `**/*.swift`, which would load every view rule into model and service work. With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/mobile-ios/swift.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Swift or iOS rules that contradict these files and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/mobile-ios/xcode-config.md`, then the project's `.swiftlint.yml` (and each tests folder's), its `.xcconfig` files and its `Package.swift` manifests. A SwiftLint row is enforced when its id is on at `severity: error` (`force_cast` and `force_try` are errors by default; a `custom_rules` row also needs its regex), and a setting row when the setting is present with the table's value. A module the project keeps in Swift 5 mode is not listed for the `SWIFT_VERSION` row. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
mobile-ios rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/mobile-ios/
Paths: default | widened: <file> += <globs>   (one line per widened file)
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Not enforced by the build: none | <id: house rule>   (one line per row)
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
