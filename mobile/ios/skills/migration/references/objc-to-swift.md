# Objective-C → Swift — annotate, then convert a leaf

Objective-C is not a defect; the move is for code a team is already changing, or for a module blocking Swift 6. Mixed targets are a supported steady state.

## Order

1. **Inventory.** `fd -e m -e mm -e h` and count lines per file; `rg -n "#import" -g '*.m'` to draw who imports whom. `.mm` (Objective-C++) files are last or stay.
2. **Annotate the headers first** — this makes the Swift call sites better *before* any file converts:
   - `NS_ASSUME_NONNULL_BEGIN` / `END` around every header, then `nullable` where it is
   - lightweight generics on collections (`NSArray<Order *> *`)
   - `NS_SWIFT_NAME` where the imported name reads badly; `NS_ENUM` / `NS_OPTIONS` for enums
   - concurrency annotations on completion handlers and delegates (`NS_SWIFT_SENDABLE`, `NS_SWIFT_NONISOLATED`, `NS_SWIFT_UI_ACTOR` for UI types) — these are what make a Swift 6 module's dynamic isolation checks correct ([`swift6-modules`](swift6-modules.md))
3. **Convert a leaf file** — a model, a formatter, a utility with no inbound Objective-C subclassing. Bridging header (`<Target>-Bridging-Header.h`) exposes Objective-C to Swift; the generated `<Target>-Swift.h` exposes Swift to Objective-C — `@objc` / `@objcMembers` only on what Objective-C still calls.
4. **One file per commit, behaviour-identical.** The Swift file is a translation: same method order, same semantics (nil messaging, `NSCopying`, KVO observers, `+load` side effects are the traps). Idiomatic redesign is a second commit.
5. **Delete the Objective-C file and remove it from the bridging header** only when no `.m` still imports it; clean the `@class` forward declarations.
6. **Value types where the code was a bag of properties.** An `NSObject` subclass with no identity becomes a `struct`; one that Objective-C still holds stays a `class` with `@objc`.

## Per-file traps

| Objective-C | Swift trap |
|---|---|
| Nil messaging | A nil receiver returns zero/nil silently; Swift optional chaining does the same, a force unwrap crashes — convert to `?.` / `guard`, never `!` |
| `NSError **` out-parameters | Imported as `throws`; callers change shape |
| Blocks called on arbitrary queues | Annotate (step 2) or the Swift 6 callback crashes at runtime |
| `NSNotificationCenter` selectors | `@objc` selector methods, or the block / async API — pick one per file |
| `NSKeyedArchiver` classes | Class names are stored — `@objc(OldName)` on the Swift class keeps old archives readable; **a store-compatibility test first** ([`offline-and-storage`](../../offline-and-storage/SKILL.md)) |
| Categories | Swift extensions; a category overriding a method has no Swift equivalent |
| Exceptions | `@try/@catch` has no Swift equivalent; the tests that cover Objective-C exceptions stay XCTest ([`unit-testing`](../../unit-testing/SKILL.md)) |

## Done

Per commit: the target builds with warnings as errors; the file's tests pass unchanged; audit rows B1, B2, B13 pass for the new Swift.
