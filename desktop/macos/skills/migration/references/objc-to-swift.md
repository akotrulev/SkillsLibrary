# Objective-C → Swift

Per file, leaves first, never converting and redesigning in the same commit. An Objective-C island that works is not a defect: convert only on request or when a feature must touch it ([`basics`](../../basics/SKILL.md) covers calling Objective-C from Swift; [`appkit`](../../appkit/SKILL.md) covers the AppKit classes most islands subclass).

## 0. Inventory

```bash
git ls-files | rg -c '\.(m|mm)$'
rg -ln "NSObject|NSViewController|NSWindowController|NSDocument" -g '*.m' -g '*.h'
rg -n "SWIFT_OBJC_BRIDGING_HEADER|DEFINES_MODULE|SWIFT_OBJC_INTERFACE_HEADER_NAME" -g '*.pbxproj' -g '*.xcconfig'
```

`*.mm` (Objective-C++) files stay: they are a C++ interop question, not a conversion. Helper tools and XPC services are separate targets: convert them one at a time with their own entitlements file untouched.

## 1. Order

1. **Annotate the headers first**: `NS_ASSUME_NONNULL_BEGIN`, `nullable` where it is, lightweight generics on collections, `NS_SWIFT_NAME`, `NS_ERROR_ENUM`, `NS_ENUM` / `NS_OPTIONS`. Swift then sees the right optionality and the conversion has no `!`.
2. **Pick a leaf**: a file nothing else imports (a model, a value transformer, a formatter, a category). Convert it to Swift with the same public surface; Swift callers see the type, the remaining Objective-C callers see it through the generated `-Swift.h` (`@objc` only on what they call).
3. **Move tests first**: a test that pins the behaviour of the Objective-C file passes before and after. A file with no test gets one before it is converted ([`unit-testing`](../../unit-testing/SKILL.md)).
4. **Controllers and delegates last**; a converted AppKit class keeps its selector names for Interface Builder and bindings until the `.xib` is gone.
5. **Delete the bridging header only when the last Objective-C file that Swift needs is gone.** A framework target uses an umbrella header, not a bridging header.

## Concurrency while converting

Objective-C callbacks have no isolation. A converted `@MainActor` class that an Objective-C caller invokes from a background queue is the classic Swift 6 runtime crash: annotate the call sites or hop explicitly ([`swift6-modules`](swift6-modules.md) § dynamic isolation).

## Verify

Build and test clean; the app launches; `nm` / the generated `-Swift.h` shows only the symbols Objective-C callers still use; the converted file has no `!`, `as!` or `try!`.

## Do not

- Convert a file you cannot test or run.
- Rewrite an `NSDocument` or a delegate-heavy controller into SwiftUI in the same commit.
- Add `@objc` and `NSObject` to a type no Objective-C code touches.
