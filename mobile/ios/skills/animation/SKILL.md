---
name: animation
description: Use when a SwiftUI (or UIKit) app needs motion or gestures — withAnimation, animation(_:value:), transitions, matchedGeometryEffect and zoom navigation transitions, PhaseAnimator, keyframeAnimator, DragGesture, and the Reduce Motion floor. Triggers "animate this", "swipe to dismiss", "drag", "hero transition", "respect reduce motion". Do NOT use for whether to animate (`design:motion`), screen navigation (`mobile-ios:navigation`) or jank profiling (`-performance`).
---

# iOS — Animation and Gestures

Motion on iOS is **state-driven**: the view is a function of state, and an animation is the system interpolating between two states. This skill owns SwiftUI animation, transitions, gestures, the UIKit equivalents for a UIKit lane, and the **Reduce Motion floor**. Whether and where to animate is design's call ([`design:motion`](../../../../design/motion/SKILL.md)). Design facts: `design/ui-ux-pro-max` `--stack swiftui` rows 33 (`withAnimation`), 34 (`.animation` modifier) and 35 (respect reduced motion, High).

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` |
|---|---|---|
| Spring presets | `.smooth`, `.snappy`, `.bouncy` | `.spring(response:dampingFraction:)` |
| Multi-step | `PhaseAnimator`, `keyframeAnimator` (iOS 17) | Chain with `Task` + `withAnimation`, or a `UIViewPropertyAnimator` |
| Completion | `withAnimation(_:completionCriteria:_:completion:)` | A `Task.sleep` is **not** a substitute — use a `UIKit` completion or a transition |
| Symbols | `.symbolEffect` (iOS 17) | Swap the symbol with a transition |
| Hero transition | `matchedTransitionSource` + `.navigationTransition(.zoom)` (iOS 18) | `matchedGeometryEffect` inside one view tree |
| Numbers | `.contentTransition(.numericText())` | Plain crossfade |
| Reduce Motion | `@Environment(\.accessibilityReduceMotion)` | Same |
| `[Swift6]` | Animation closures are `@MainActor`; shared animation state is a value, not a global | Same |

An API newer than the deployment target needs `#available`; never raise the target for a flourish ([`project-setup`](../project-setup/SKILL.md)). Facts are from long-standing APIs, not re-confirmed against Apple pages this session (plan D23).

## When to use

- Animating a state change: expand, reveal, toggle, loading → loaded
- Entrance and exit of a view; a hero or zoom transition between two screens
- A drag, swipe-to-dismiss, long-press or pinch
- A multi-step or looping effect; a number or symbol that changes
- Honouring Reduce Motion everywhere motion exists

## When NOT to use

- Where motion belongs in the product, durations, restraint → [`design:motion`](../../../../design/motion/SKILL.md)
- Pushing, presenting and tab changes → [`navigation`](../navigation/SKILL.md)
- Hitches, dropped frames, Instruments → `mobile-ios:performance`
- Roles, labels, focus as an accessibility requirement → `mobile-ios:accessibility`
- Another stack → `mobile-react-native:animation`, `mobile-android:animation`

## Rules

1. **State changes, not animation calls.** Mutate state inside `withAnimation { }`; the view's difference between two states is what animates. Never drive a frame loop from a `Timer`.
2. **Animate `offset`, `scale`, `opacity`, `rotationEffect` and colour** — they are composited, not re-laid-out. An animated `frame`, `padding` or a changing text length re-runs layout every frame; for a collapsing panel animate `opacity` and a transition, and let layout settle once.
3. **`.animation(_:value:)` always carries `value:`.** The value-less `.animation(_:)` is deprecated and animates every change under it, including ones you did not mean. Apply it as close to the changed property as possible, not on a root container.
4. **A transition needs a conditional.** `.transition(_:)` only runs when the view is inserted or removed inside `withAnimation` or `.animation(_:value:)`; `if show { Card().transition(.opacity) }`. Pair `.move(edge:)` with `.opacity` (`.asymmetric` when entry and exit differ).
5. **Work in `body` is a performance bug, doubly so while animating.** No formatting, sorting or allocation inside a view that re-evaluates every frame — derive it outside ([`ui-components`](../ui-components/SKILL.md)).
6. **Keep ids stable.** `ForEach(items)` over `Identifiable` models with stable domain ids; an index or `UUID()` per render restarts every row's identity and animates a flash instead of a move.
7. **Reduce Motion replaces movement, it does not remove feedback.** Under the setting a slide becomes a fade (or nothing), a looping effect stops, parallax goes — and the state change itself still happens, visibly. This is the High-severity corpus rule.
8. **Springs for physical responses, short ease for state.** A system `.smooth` / `.snappy` spring for gesture-driven or interruptible motion; `.easeInOut(duration: 0.2)`-class for a plain reveal. Durations come from the project's motion tokens when it has them.
9. **A gesture-only action has an accessible alternative.** Swipe-to-delete also appears as a `.swipeActions` button or an `accessibilityAction`; a drag handle is reachable by VoiceOver adjustments ([`accessibility`](../accessibility/SKILL.md)).
10. **Test ids and labels survive animation.** A view that is a tap target and moves still carries `accessibilityIdentifier` and a label ([`test-ids`](../test-ids/SKILL.md)).

## State-driven animation and the Reduce Motion floor

```swift
struct ExpandableCard: View {
    let title: LocalizedStringKey
    let details: LocalizedStringKey
    @State private var isExpanded = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                withAnimation(reduceMotion ? nil : .snappy) { isExpanded.toggle() }
            } label: {
                Label(title, systemImage: "chevron.right")
                    .rotationEffect(.degrees(isExpanded ? 90 : 0), anchor: .center)
            }
            .accessibilityIdentifier("Faq.Card.Toggle")
            if isExpanded {
                Text(details)
                    .transition(reduceMotion ? .opacity : .opacity.combined(with: .move(edge: .top)))
            }
        }
    }
}
```

- `withAnimation(nil)` applies the change immediately — the cleanest Reduce Motion path. For a view that animates in several places, one small helper (`func animation(_ animation: Animation?) -> Animation?` that returns `nil` under Reduce Motion) is earned the **second** time it is needed, not the first.
- Reduce Motion affects **your** animation; the system already tones down its own (navigation, sheets). Read it for custom transitions, `matchedGeometryEffect` hero moves, `PhaseAnimator` loops, parallax and auto-playing effects.
- **Prefer cross-fade to remove**, and keep `Differentiate Without Color` in mind — a state shown only by a colour animation is not shown.

## Transitions, hero moves and symbols

- **`matchedGeometryEffect(id:in:)`** needs a shared `@Namespace` and **exactly one source view per id at a time**; two on screen together flicker. It moves a view within one view tree (an expanding card), not across a navigation push.
- **Across a push (iOS 18)**: `matchedTransitionSource(id:in:)` on the origin and `.navigationTransition(.zoom(sourceID:in:))` on the destination — the system owns the morph and the interactive swipe-back. On iOS 17 a plain push is correct; do not hand-build a fake hero.
- **Symbols**: `.symbolEffect(.bounce, value: count)` for a one-shot, `.symbolEffect(.pulse, isActive: isLoading)` for a state — and stop it when `isActive` goes false. `.contentTransition(.numericText())` for a counter, `.contentTransition(.symbolEffect)` for an icon swap.
- **Liquid Glass** (forced by the iOS 27 SDK) morphs between glass elements through `GlassEffectContainer` and `glassEffectID` where used — let the system material animate; never layer a custom blur animation over it ([`styling`](../styling/SKILL.md)).
- `Animatable` / `animatableData` for a custom shape or modifier that animates a number; keep `animatableData` to the few values that change.

## Multi-step and keyframes (iOS 17)

```swift
Image(systemName: "bell.fill")
    .phaseAnimator([false, true], trigger: unreadCount) { icon, ring in
        icon.rotationEffect(.degrees(ring ? 12 : 0))
    } animation: { _ in .bouncy(duration: 0.25) }
```

- `phaseAnimator` runs a **fixed sequence of states**, once per trigger — `trigger:` makes it one-shot; without it the sequence loops forever, which Reduce Motion must stop and which is almost never wanted.
- `keyframeAnimator(initialValue:trigger:)` for a curve over time on several properties (a shake, a pop); keep the value type a small `struct`. Gate it: `reduceMotion ? static view : animated view`.
- Anything looping or longer than ~1 s has a **stop condition** (a `trigger`, `isActive`, view disappearance) — `.task`-driven loops are cancelled with the view; a `Timer.publish` is not unless you cancel it.

## Gestures

```swift
struct DismissibleCard<Content: View>: View {
    @ViewBuilder let content: Content
    let onDismiss: () -> Void
    @GestureState private var drag: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        content
            .offset(y: max(drag, 0))
            .gesture(
                DragGesture(minimumDistance: 12)
                    .updating($drag) { value, state, _ in state = value.translation.height }
                    .onEnded { value in
                        if value.translation.height > 120 { onDismiss() }
                    }
            )
            .animation(reduceMotion ? nil : .snappy, value: drag)
            .accessibilityAction(named: "Dismiss", onDismiss)
    }
}
```

- **`@GestureState`** resets itself when the gesture ends or is cancelled — no manual cleanup and no stuck offset. Use `@State` only for what must persist.
- **Gesture priority**: `.gesture` is the default; `.highPriorityGesture` wins over the child's; `.simultaneousGesture` runs both. A drag inside a `ScrollView` needs a `minimumDistance`, or a vertical-only check on `value.translation`, so it does not eat the scroll. Compose with `SequenceGesture` / `ExclusiveGesture` instead of flags.
- **Interruptible**: a spring started by a gesture continues from the gesture's velocity when it ends — read `value.velocity` (iOS 17) / `predictedEndTranslation` for the throw.
- Touch targets stay ≥ 44 pt during and after movement; a draggable element's hit area does not shrink with its scale.
- Haptics follow a user-initiated result, not each tick ([`device-features`](../device-features/SKILL.md)).
- `[UIKit]` `UIViewPropertyAnimator` (interruptible, scrubbable) over `UIView.animate` for a gesture-driven move; read `UIAccessibility.isReduceMotionEnabled` and observe `UIAccessibility.reduceMotionStatusDidChangeNotification`; `UIPanGestureRecognizer` delegates arbitrate with `gestureRecognizer(_:shouldRecognizeSimultaneouslyWith:)`.

## Procedure

1. Detect the deployment target, SwiftUI vs UIKit for the screen, and existing motion tokens or helpers.
2. Pick the technique: system control (already animated) → `withAnimation` on state → transition on insert/remove → `phaseAnimator` / `keyframeAnimator` → gesture + `@GestureState`.
3. Write the Reduce Motion variant in the same edit.
4. Confirm no animated property is a layout property, every `.animation` carries `value:`, ids are stable.
5. Add test ids to every animated tap target; add an accessibility action for every gesture-only action.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Reduce Motion on (Settings → Accessibility → Motion): entrances become fades or disappear, loops stop, a drag still follows the finger and the state still changes.
- Instruments (SwiftUI template, Animation Hitches) on a device: the interaction holds the frame budget with no hitch in the animation; no per-frame view-body work in the update count.
- `rg "\.animation\([^,)]*\)$"` for value-less modifiers → none (Q2).
- A list insert / remove animates and reflows with stable ids; nothing flashes.
- Dev-side: the pure parts — a drag-distance-to-dismiss decision, a phase sequence — as functions in Swift Testing; the motion itself is a device and snapshot concern, not a unit test.

## Handoffs

- Where / whether, durations, restraint → [`design:motion`](../../../../design/motion/SKILL.md)
- Push, present, tab transitions → [`navigation`](../navigation/SKILL.md)
- Hitches, Instruments, `body` cost → `mobile-ios:performance`
- VoiceOver actions, Reduce Motion as accessibility, Differentiate Without Color → `mobile-ios:accessibility`
- Liquid Glass, materials → [`styling`](../styling/SKILL.md)
- Test ids on animated targets → [`test-ids`](../test-ids/SKILL.md)
- Haptic feedback on gesture end → [`device-features`](../device-features/SKILL.md)
