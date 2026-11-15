# The macOS 27 SDK's forced changes, CocoaPods → SPM, and deployment-target raises

Three moves that share one rule: **none happens as a side effect.** Facts are plan §4.1's; re-read the Xcode 27 release notes and developer.apple.com/news/upcoming-requirements before a run, because Apple's dates move.

## A. Linking the macOS 27 SDK

Xcode 27.x builds against the macOS 27 SDK (macOS 27 "Golden Gate" shipped 2026-09-14). There is **no published macOS SDK upload deadline** for the Mac App Store, so unlike iOS the move has no date: do it when the project wants the SDK, as its own run.

| Change | What to do |
|---|---|
| **Liquid Glass cannot be opted out of** | Remove any compatibility opt-out; re-screenshot every window; delete custom toolbar and sidebar backgrounds that fight the system bars ([`styling`](../../styling/SKILL.md)) |
| **Menu icons are hidden by default** | Set the icon visibility explicitly where the icon carries meaning; a command is never identified by its icon alone ([`menus-and-commands`](../../menus-and-commands/SKILL.md)) |
| **`FileDocument` is deprecated** | New document code uses `Document`; existing code is moved on request ([`filedocument-to-document`](filedocument-to-document.md)) |
| **`PreviewProvider` is deprecated** | `#Preview` in new code (audit A9) |
| **Sheet controls reset control size** | Re-apply `controlSize` inside the sheet |
| **Xcode 27.2 accepts a `27.1` deployment target by mistake** | Never set it (audit A3) |
| **Linker flag `-ld_classic` is gone** | Remove it (audit A5) |

Linking the SDK does not change the deployment target. Architectures follow the target, not the SDK ([`apple-silicon-and-developer-id`](apple-silicon-and-developer-id.md)).

## B. CocoaPods → SPM (dated: trunk read-only 2026-12-02)

1. **Inventory the pods**: `rg --files -g 'Podfile*' -g '*.podspec'`; list each pod, its version and whether it has an SPM product, a binary xcframework or neither.
2. **Replace one pod at a time**: add the Swift package, change the imports, build and test, remove the pod from the `Podfile`, commit. Sparkle dropped CocoaPods in 2.10.1, which is already SPM-only.
3. **A pod with no SPM replacement** is vendored as an xcframework or a local package, with the licence and the version beside it, or replaced by SDK API.
4. **Remove `Pods/`, the `Podfile`, `Podfile.lock` and the workspace's Pods project last**, once every pod is gone; a committed `Pods/` is a finding (A8).
5. Build scripts and CI that ran `pod install` are updated in the same commit as the last pod.

Verify: a clean clone builds with `xcodebuild -resolvePackageDependencies` then the scheme build; the test plan matches the baseline.

## C. Deployment-target raises

One macOS version per raise, each its own run:

1. State why: an API the feature needs, a Xcode floor (macOS 12 is Xcode 27's hard floor), a dropped version in the support policy.
2. Check the architecture decision in the same run: a raise to 27 drops x86_64 from `ARCHS_STANDARD` ([`apple-silicon-and-developer-id`](apple-silicon-and-developer-id.md)).
3. Delete the `#available` branches the new floor makes dead, and nothing else.
4. Update the places that repeat the target: the xcconfig, every package's `platforms:`, the Sparkle appcast's `minimumSystemVersion`, the store listing.

Never raise the target to use one API: gate it with `#available` until the raise is its own run.
