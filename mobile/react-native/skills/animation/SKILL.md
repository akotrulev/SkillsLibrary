---
name: mobile-react-native-animation
description: Use when an Expo SDK 57 app needs motion or gestures — Reanimated 4 + react-native-worklets, Gesture Handler 2.32 on SDK 57 vs 3.x on SDK 58 (different APIs), layout and entering/exiting animations, UI-thread-only props, Reduce Motion. Triggers "animate this", "swipe to dismiss", "drag", "press feedback janks", "gesture callback renamed". Do NOT use for whether to animate (`design-motion`), navigation transitions (`-navigation`), or list performance (`-performance`).
---

# React Native — Animation and Gestures

Motion on a phone runs on the **UI thread** or it janks. This skill owns Reanimated 4 (worklets), the gesture layer, layout animations and the **Reduce Motion floor**. Whether and where to animate is design's call ([`design-motion`](../../../../design/motion/SKILL.md)); a web CSS transition does not exist here. Web analog: [`fe-react-animation`](../../../../frontend/react/skills/animation/SKILL.md) — the "reduced motion is a hard floor" and "transform and opacity only" rules carry over; CSS keyframes, `AnimatePresence` and View Transitions do not.

## Version lane

| Concern | SDK 57 (primary) | SDK 58 `[SDK58]` |
|---|---|---|
| Reanimated | 4.x, needs `react-native-worklets` and its Babel plugin (Expo's preset adds it) | 4.7 + worklets 0.13 |
| Gesture Handler | **2.32** — `Gesture.Pan()` builder chain, `GestureDetector`, callbacks `onStart` / `onUpdate` / `onEnd` | **3.x (bundled 3.2.1; 3.3 current)** — hooks `usePanGesture()` etc., callbacks `onActivate` / `onUpdate` / `onDeactivate` |
| Reduce Motion | `useReducedMotion()` (read once at start); per-animation `reduceMotion` | same |
| Compiler | React Compiler on: use `.get()` / `.set()` on shared values | same |
| Floor SDK 54 | Reanimated 3 / 4 legacy-arch bridge — migrate, do not author | — |

**Detect the Gesture Handler major from `package.json` before writing a gesture.** A 2.x snippet in a 3.x project (or the reverse) compiles to a dead gesture. Never up-level the library as a side effect ([`migration`](../migration/SKILL.md)).

## When to use

- Press feedback, entrances, exits, springs, shared values and derived values
- Drag, swipe-to-delete, pinch, pan-to-dismiss, bottom-sheet-like interactions
- Layout animation when items insert, remove or reorder
- A scroll-linked header or parallax
- Honouring the system Reduce Motion setting

## When NOT to use

- Where motion belongs in the product, durations, restraint → [`design-motion`](../../../../design/motion/SKILL.md)
- Screen transitions, native stack and tab animations → [`navigation`](../navigation/SKILL.md)
- Jank from list rendering → [`performance`](../performance/SKILL.md)
- Native menus, sheets, system modals (already animated by the OS) → [`ui-components`](../ui-components/SKILL.md)

## Rules that hold on both lanes

1. **Animate `transform` and `opacity` only.** `width`, `height`, `top`, `left`, `margin`, `padding` force layout every frame: `rules/animation-gpu-properties.md`. For a collapsing panel, animate `scaleY` + `opacity`, or use a layout animation for the height change.
2. **Drive it from a shared value on the UI thread.** The worklet runs on the UI thread; JS `setState` per frame does not. Call JS from a worklet with `scheduleOnRN` (worklets 0.5+) — `runOnJS` is the older name in Reanimated 3 / early 4 docs; detect which the installed version exports.
3. **Derive, do not react.** `useDerivedValue` for a value computed from another; `useAnimatedReaction` only for side effects (haptics, logging): `rules/animation-derived-value.md`.
4. **Store the state, derive the visual.** A press is `pressed: 0 | 1`, scale is `interpolate(pressed, [0, 1], [1, 0.95])`: `rules/animation-gesture-detector-press.md`.
5. **React Compiler is on — use `.get()` and `.set()`**, never `.value`, in components the compiler touches: `rules/react-compiler-reanimated-shared-values.md`. A worklet that mutates a shared value read from a captured object breaks under the compiler; keep shared values as locals or refs-of-shared.
6. **No shared value in React state, no animation in `useState`.** A shared value is not a render trigger; to show it as text use `useAnimatedProps` with a `TextInput`, not state per frame.
7. **No `setTimeout` choreography** — `withDelay`, `withSequence`, `withRepeat`; cancel on unmount (`cancelAnimation`) — Reanimated cancels on unmount for hook-owned values, but a manual timer leaks.
8. **Key by stable id.** An animated list keyed by index breaks entering / exiting / layout tracking.
9. **Prefer a native control to a hand-built one** — a native modal, sheet, menu or `Switch` is already smooth ([`ui-components`](../ui-components/SKILL.md)).
10. **Test ids and labels survive animation** — an `Animated.View` that is a tap target still carries `testID` and an accessible role ([`test-ids`](../test-ids/SKILL.md), [`accessibility`](../accessibility/SKILL.md)).

```tsx
import Animated, { useAnimatedStyle, withSpring } from 'react-native-reanimated';

export function Card({ raised, children }: { raised: boolean; children: React.ReactNode }) {
  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: withSpring(raised ? -4 : 0) }],
    opacity: withSpring(raised ? 1 : 0.9),
  }));
  return <Animated.View style={style} testID="Card.Root">{children}</Animated.View>;
}
```

## Reduce Motion — the hard floor

Both platforms expose "Reduce Motion" (iOS) / "Remove animations" (Android). Every animation degrades to **none, or a short opacity change**; a large slide, zoom, parallax or looping motion is removed, not shortened.

- **Reanimated honours it by default**: every animation is configured with `ReduceMotion.System`. `ReduceMotion.Always` disables regardless; `ReduceMotion.Never` keeps it running — **never set `Never`** on decorative motion. Pass it in the options: `withTiming(1, { reduceMotion: ReduceMotion.System })`; on a layout animation chain `.reduceMotion(ReduceMotion.System)`.
- `useReducedMotion()` returns a **boolean read at app start** and does not re-render when the setting changes. Use it to choose a variant (no parallax, no looping), not to track the live setting. For a live read, `AccessibilityInfo.isReduceMotionEnabled()` plus the `reduceMotionChanged` listener, removed on cleanup.
- A **gesture-following** interaction (drag, pinch) is user-driven and stays; the decorative **settle** after release shortens.
- **Looping and auto-playing** motion (`withRepeat(…, -1)`, a Lottie) pauses under Reduce Motion and has a user control to stop it (WCAG 2.2.2).
- No state conveyed by motion alone — a shake for "error" also has text and an icon.

## Layout, entering and exiting

- `Animated.View` `entering={FadeIn}` / `exiting={FadeOut}` / `layout={LinearTransition}` cover insert, remove and reorder; chain `.duration(200)` and `.reduceMotion(ReduceMotion.System)`. They run on the UI thread; keep them off a list **row** that recycles heavily in FlashList — animate the content inside, or use the list's own item layout animation support (read the FlashList 2 docs for the installed version).
- An exit animation only plays if the component is unmounted by React; a hidden-by-style node never exits.
- Animating a **height** change is the one layout case that is acceptable via `LinearTransition` — it is measured once, not per frame.
- Shared-element transitions between screens are navigation's concern, and experimental — flag them, do not build a feature on one.
- `useAnimatedScrollHandler` / `useScrollViewOffset` for scroll-linked motion; no `setState` in `onScroll` (`rules/scroll-position-no-state.md`).

## Gestures — lane A: Gesture Handler 2.32 (SDK 57)

`GestureHandlerRootView` once at the root (Expo Router's root layout); gestures are builders passed to `GestureDetector`:

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

export function Draggable({ children }: { children: React.ReactNode }) {
  const x = useSharedValue(0);
  const start = useSharedValue(0);

  const pan = Gesture.Pan()
    .onStart(() => {
      start.set(x.get());
    })
    .onUpdate((event) => {
      x.set(start.get() + event.translationX);
    })
    .onEnd(() => {
      x.set(withSpring(0));
    });

  const style = useAnimatedStyle(() => ({ transform: [{ translateX: x.get() }] }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={style} testID="Draggable.Handle">{children}</Animated.View>
    </GestureDetector>
  );
}
```

- Callbacks are **worklets** on the UI thread; call JS with `scheduleOnRN` / `runOnJS`.
- Compose with `Gesture.Race`, `Gesture.Simultaneous`, `Gesture.Exclusive`; `.requireExternalGestureToFail(other)` and `.simultaneousWithExternalGesture(other)` relate gestures across components.
- `.onChange` gives the delta; `.minDistance`, `.activeOffsetX`, `.failOffsetY` decide when a pan claims the touch — a horizontal swipe inside a vertical list needs `activeOffsetX` and `failOffsetY`.
- Swipeable rows: `ReanimatedSwipeable`.

## Gestures — lane B: Gesture Handler 3.x `[SDK58]`

The builder chain becomes **hooks with a config object**, and the callbacks are **renamed**. A 2.x callback name in a 3.x project is silently never called.

| 2.32 (SDK 57) | 3.x (SDK 58) |
|---|---|
| `Gesture.Pan()` / `Tap()` / `LongPress()` / `Pinch()` / `Rotation()` / `Fling()` / `Hover()` / `Native()` / `Manual()` | `usePanGesture()` / `useTapGesture()` / `useLongPressGesture()` / `usePinchGesture()` / `useRotationGesture()` / `useFlingGesture()` / `useHoverGesture()` / `useNativeGesture()` / `useManualGesture()` |
| `.onStart` / `.onEnd` | **`onActivate` / `onDeactivate`** |
| `.onTouchesCancelled` | `onTouchesCancel` |
| `.onChange` | removed — read the `change*` fields in `onUpdate` |
| `state` / `oldState` on the event; `success` flag | removed; `event.canceled` (the inverse of `success`) |
| `Gesture.Race` / `Simultaneous` / `Exclusive` | `useCompetingGestures` / `useSimultaneousGestures` / `useExclusiveGestures` |
| `requireExternalGestureToFail` / `simultaneousWithExternalGesture` / `blocksExternalGesture` | `requireToFail` / `simultaneousWith` / `block` |
| `stateManager` in touch callbacks | global `GestureStateManager` |
| `BaseButton`, `RectButton`, `BorderlessButton` | `Touchable`; the old ones survive with a `Legacy` prefix |
| `GestureDetector` (SVG-hostile wrapper) | unchanged name; use `InterceptingGestureDetector` outside and `VirtualGestureDetector` inside for SVG-like hierarchies |
| `Gesture.ForceTouch()` | no hook equivalent |

```tsx
import { GestureDetector, usePanGesture } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

export function Draggable({ children }: { children: React.ReactNode }) {
  const x = useSharedValue(0);
  const start = useSharedValue(0);

  const pan = usePanGesture({
    onActivate: () => {
      start.set(x.get());
    },
    onUpdate: (event) => {
      x.set(start.get() + event.translationX);
    },
    onDeactivate: () => {
      x.set(withSpring(0));
    },
  });

  const style = useAnimatedStyle(() => ({ transform: [{ translateX: x.get() }] }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={style} testID="Draggable.Handle">{children}</Animated.View>
    </GestureDetector>
  );
}
```

- **Relations cannot cross APIs**: a hook-based gesture cannot be related to a `Gesture.*` builder one. Migrate a screen's gestures together.
- Hook-based code and builder code coexist in one app during a migration; do not mix them on one view.
- Verify the exact option names and the `runOnJS` replacement against the 3.x docs for the installed minor (`docs.swmansion.com/react-native-gesture-handler`); the upgrade guide is the source for the table above.

## Procedure

1. Detect Expo SDK, Reanimated and Gesture Handler majors, whether the React Compiler is on, and any existing motion tokens (durations, springs).
2. Pick the technique: native control → layout / entering / exiting → shared value + `useAnimatedStyle` → gesture + shared value.
3. Write on the detected lane only; add the Reduce Motion variant in the same edit.
4. Confirm no animated property is a layout property, no shared value is read as `.value` under the compiler.
5. Add a test id to every animated tap target; ensure an accessible role / label.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Reduce Motion on (iOS) / Remove animations on (Android): entrances, parallax and loops are gone; a drag still follows the finger.
- A release build on a mid-range Android device: press feedback and a drag hold 60 fps with no JS-thread work per frame (React Native DevTools / Perf Monitor).
- `rg "\.value\b"` over components under the compiler → none; `rg "onStart|onEnd"` on an SDK 58 project → none in gesture config (Q3, Q4).
- A list with insert / remove: rows animate and reflow; none is keyed by index.
- A swipe inside a vertical scroller does not scroll at the same time.

## Handoffs

- Where / whether, durations, restraint → [`design-motion`](../../../../design/motion/SKILL.md)
- Screen transitions, native stack / tabs → [`navigation`](../navigation/SKILL.md)
- Jank, list rendering, profiling → [`performance`](../performance/SKILL.md)
- Roles, labels, focus and Reduce Motion as an accessibility requirement → [`accessibility`](../accessibility/SKILL.md)
- Upgrading Reanimated or Gesture Handler → [`migration`](../migration/SKILL.md)
- Test ids on animated targets → [`test-ids`](../test-ids/SKILL.md)
