# UIKit → SwiftUI — screen by screen, root last

A working UIKit app is not a defect, and a UIKit codebase is **extended in UIKit** unless the task is this migration (D20). Run it only when the user asks for it; it is the slowest move and the one most likely to turn into a redesign.

Floor: SwiftUI `NavigationStack` needs **iOS 16**; `@Observable` and SwiftData need 17. Below 16 the lane is UIKit only ([`uikit`](../../uikit/SKILL.md)).

## Order

1. **Scene lifecycle first** — mandatory against the iOS 27 SDK and a prerequisite for hosting SwiftUI cleanly: [`uikit/references/uiscene-migration.md`](../../uikit/references/uiscene-migration.md) (TN3187). Do not mix the two moves.
2. **Pick leaf screens** — a screen nothing pushes onward from (a detail, a settings page, a form), with the least shared UIKit state.
3. **Host, don't replace.** The new SwiftUI view is a child of the existing flow: `UIHostingController` pushed onto the existing `UINavigationController`, or `UIHostingConfiguration` inside a cell. No `NavigationStack` inside a pushed host (D17). The seams both ways are in [`uikit/references/interop-seams.md`](../../uikit/references/interop-seams.md).
4. **Port one screen per commit, behaviour-identical.** Same data source, same service, same analytics events. Redesign is a later change.
5. **Move shared state out of the controller first.** A screen whose logic lives in a view controller gets that logic into an `@Observable` model or service (with its test) before the view is written; the controller then calls the model, and the SwiftUI view reads it ([`architecture`](../../architecture/SKILL.md)).
6. **Navigation moves last.** Once most screens are SwiftUI, replace the coordinator or `UINavigationController` flow with a `NavigationStack(path:)` of typed routes ([`navigation`](../../navigation/SKILL.md)); deep links and `onOpenURL` go through the one validated function (F14).
7. **Root last.** The window's root becomes a SwiftUI `App` + `WindowGroup` only when no UIKit screen remains that needs the old root. Leaving a UIKit root with SwiftUI children is a valid permanent state.

## Per-screen checklist

| Concern | Carry across |
|---|---|
| Data states | Loading / loaded / empty / failed / stale / offline in one `LoadState` ([`ui-components`](../../ui-components/SKILL.md), [`error-handling`](../../error-handling/SKILL.md)) — a port that drops a state is a regression |
| Lifecycle | `viewDidLoad` / `viewWillAppear` work → `.task` / `.task(id:)`; observers and timers disappear with the view |
| Accessibility | Labels, traits, identifiers and focus order re-applied by hand — SwiftUI does not inherit them |
| `accessibilityIdentifier` | Same strings as the UIKit screen — the QA suite locates by them; renaming is a QA hand-off ([`test-ids`](../../test-ids/SKILL.md)) |
| Dynamic Type, Dark Mode, iPad size classes | Re-verified on the new screen with a screenshot pass |
| Table / collection | `List` / `LazyVStack` with stable domain ids; the diffable snapshot's ids carry over (D6) |
| Custom `UIView` | `UIViewRepresentable` with a `Coordinator`, only until a SwiftUI equivalent is worth writing (D18) |

## Traps

- **Conversion plus redesign in one PR** — unreviewable; port first.
- **`UIHostingController` added without `addChild` / `didMove(toParent:)`** — appearance callbacks and safe areas break.
- **A `NavigationStack` inside a hosted screen pushed on a `UINavigationController`** — two back buttons, two stacks.
- **A `@State` initial value computed from a parameter** — evaluated once ([`observation`](observation.md)).
- **Deleting the storyboard before the last screen that segues from it moves.**

## Done

Per screen: the UIKit controller and its test seam removed or reduced to a host; audit rows D12–D20 (UIKit lane) and D1–D11 (SwiftUI) pass for the ported screen.
