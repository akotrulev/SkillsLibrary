---
name: mobile-android-animation
description: Use when a Compose app needs motion or gestures — AnimatedVisibility, animate*AsState, Transition, AnimatedContent, shared-element transitions, predictive-back animation, drag and swipe gestures — and the Reduce Motion floor (animator duration scale). Triggers "animate this", "hero transition", "swipe to dismiss", "respect remove animations". Do NOT use for route structure (`mobile-android-navigation`), Views animators (`-views-interop`), or what to animate (design).
---

# Android — Animation and Gestures

Motion in Compose is **state-driven**: the UI is a function of state, and an animation is a value that moves between two states. This skill owns the Compose animation APIs, shared-element and predictive-back motion, gestures, and the **Reduce Motion floor**. Whether and where to animate is design's call (query the `design/ui-ux-pro-max` corpus with `--stack jetpack-compose` and cite the row); this skill makes it correct, cheap and respectful.

## Version lane

| Concern | Compose (primary) | Lane |
|---|---|---|
| Show / hide | `AnimatedVisibility`; size changes `Modifier.animateContentSize()`; swap content `AnimatedContent` / `Crossfade` | Same |
| One value | `animate*AsState` (spring default) | Same |
| Several values, one state | `updateTransition` / `Transition` | Same |
| Imperative, interruptible, gesture-driven | `Animatable` in a coroutine | Same |
| Looping | `rememberInfiniteTransition` | Same |
| Shared elements | `SharedTransitionLayout` + `Modifier.sharedElement` / `sharedBounds` | **Not verified:** stability and opt-in annotation — the docs page does not state it; read the compose-animation release notes for the BOM in use |
| Back | `NavDisplay` / `NavHost` animate the system gesture; `BackHandler`; `PredictiveBackHandler` for custom progress | **Not verified:** whether `PredictiveBackHandler` has been superseded by a navigation-event API — read the "Access progress manually" page for the BOM in use |
| Reduce Motion | The system **animator duration scale** | Same |
| `[Views]` | `ObjectAnimator`, `MotionLayout`, `TransitionManager` — [`views-interop`](../views-interop/SKILL.md) | — |

Sources read 2026-10-10: developer.android.com/develop/ui/compose/animation/{introduction,shared-elements}, /develop/ui/compose/system/predictive-back (overview only). An animation API newer than the project's Compose BOM is not used; never raise the BOM for a flourish ([`project-setup`](../project-setup/SKILL.md)).

## When to use

- Animating a state change: expand, reveal, toggle, loading → loaded
- A list item moving, appearing or disappearing; a number or content swap
- A hero / container-transform transition between two screens; a custom back animation
- A drag, swipe-to-dismiss, long-press or pinch
- Respecting the user's "Remove animations"

## When NOT to use

- Which screens exist and how back works → [`navigation`](../navigation/SKILL.md)
- Choosing a motion style or timing language → design (`design/ui-ux-pro-max`)
- Spinners and skeletons as a loading state → [`error-handling`](../error-handling/SKILL.md) (the region states) and [`ui-components`](../ui-components/SKILL.md)
- XML animators → [`views-interop`](../views-interop/SKILL.md)
- Another stack → `mobile-ios-animation`, `mobile-react-native-animation`

## Choosing the API

| Need | Use |
|---|---|
| An element enters or leaves | `AnimatedVisibility(visible, enter, exit)` |
| One property follows a state | `val alpha by animateFloatAsState(if (enabled) 1f else 0.5f, label = "alpha")` |
| Several properties change together | `val transition = updateTransition(state, label = "card")` + `transition.animate…` |
| Content replaced by different content | `AnimatedContent(targetState, label = …)`; `Crossfade` for a plain swap |
| A container resizes | `Modifier.animateContentSize()` |
| The value follows a finger, can be interrupted | `Animatable` + `animateTo` / `snapTo` inside `rememberCoroutineScope` or `LaunchedEffect` |
| A repeating indicator | `rememberInfiniteTransition` — only while visible, and only for a loading or live state |

- **Always give `label`** — it names the animation in Layout Inspector and tracing.
- **Springs by default, `tween` when a duration is a requirement.** A spring is interruptible and keeps velocity; a `tween` restarts. Pick durations from the design row (typically 150–300 ms for small transitions), never invent per-screen numbers — one `MotionTokens` object holds the specs the app uses.
- **Animate the thing that changed**, not the whole screen. A state flips, `AnimatedContent` or the value animates; never `Thread.sleep` / `delay` to sequence frames.

## Performance: read late

An animated value read in composition recomposes the subtree **every frame**. Defer the read to layout or draw:

```kotlin
@Composable
fun PulsingBadge(selected: Boolean, modifier: Modifier = Modifier) {
    val scale by animateFloatAsState(if (selected) 1.2f else 1f, label = "badgeScale")
    Badge(
        modifier = modifier.graphicsLayer {
            scaleX = scale
            scaleY = scale
        },
    )
}
```

- **`graphicsLayer { }` for alpha, scale, rotation and translation** (draw phase); `Modifier.offset { IntOffset(…) }` (layout phase). Not `Modifier.alpha(value)`, `Modifier.padding(value)` or `Modifier.offset(x = value)`, which recompose per frame.
- **Animate transform and opacity.** Animating width / height / padding forces a layout pass per frame — `animateContentSize` is the allowed exception; a list that reflows each frame is a jank source.
- **Stable keys in lazy lists** (`key = { it.id }`) so `Modifier.animateItem()` animates insert, remove and reorder instead of re-creating rows; no animated heights inside a `LazyColumn` item.
- **Never start animation work in `onCreate` or before the first frame** — it competes with startup ([`performance`](../performance/SKILL.md)); decorative motion waits until the content is shown.
- Check a janky one with a Macrobenchmark `FrameTimingMetric` and a Perfetto trace, not by eye ([`performance`](../performance/SKILL.md)).

## Shared elements

```kotlin
@Composable
fun OrderThumbnail(
    orderId: String,
    sharedScope: SharedTransitionScope,
    visibilityScope: AnimatedVisibilityScope,
    modifier: Modifier = Modifier,
) {
    with(sharedScope) {
        AsyncImage(
            model = orderId.thumbnailUrl(),
            contentDescription = null,
            modifier = modifier.sharedElement(
                rememberSharedContentState(key = OrderImageKey(orderId)),
                animatedVisibilityScope = visibilityScope,
            ),
        )
    }
}

data class OrderImageKey(val orderId: String)
```

- **`SharedTransitionLayout` is the outermost layout**; shared modifiers live inside it and inside an `AnimatedVisibilityScope` (`AnimatedContent`, `AnimatedVisibility`, `NavHost`, or Navigation 3 entries via scene metadata — read the "With navigation" page for the lane in use).
- **`sharedElement` when the content is the same in both states; `sharedBounds` when it differs** (container transform, text whose font or colour changes), with `enter` / `exit` and `Modifier.animateEnterExit()` for the extras.
- **Keys are unique data classes**, not bare strings — `OrderImageKey(orderId)`; in a list, include the item id. A duplicate key silently produces no match; `rememberSharedContentState(...).isMatchFound` checks it.
- **Modifier order matters**: modifiers before the shared modifier set the start and end bounds; put size modifiers after it, and keep the order identical on both ends.
- Not supported: `AndroidView` interop, `Dialog` and `ModalBottomSheet` content; no shape morph and `ContentScale` snaps. Fall back to `sharedBounds` plus an enter / exit, or a plain crossfade.
- Pass the scopes as parameters; use a `CompositionLocal` only for deep trees where threading them is the larger cost.

## Back — predictive

- The system back gesture previews the destination; **`NavDisplay` / `NavHost` and Material 3 components (bottom sheet, search bar, side sheet, drawer) already animate it** — enable `android:enableOnBackInvokedCallback="true"` and do not rebuild it ([`navigation`](../navigation/SKILL.md)).
- **Custom progress** only when a screen owns its own transition (a drawer you built, a media player collapse): `PredictiveBackHandler(enabled = isOpen) { progress -> … }` collecting `BackEventCompat.progress` to drive an `Animatable`, committing on completion and resetting on `CancellationException`. Enabled **only while the condition holds**; verify the API name against the BOM in use (version lane).
- A back press never silently discards input — confirm-discard first ([`navigation`](../navigation/SKILL.md)).

## Gestures

- **Prefer the built-ins**: `SwipeToDismissBox`, `Modifier.draggable`, `transformable`, `combinedClickable` for long-press; `anchoredDraggable` for snap points. Custom `pointerInput` only when none fits.
- **A gesture has a visible, accessible alternative** — swipe-to-delete also has an overflow-menu action with `customActions` semantics, so TalkBack and switch users can do it ([`accessibility`](../accessibility/SKILL.md)). Touch targets stay ≥ 48 dp.
- Gesture state is `Animatable` plus `snapTo` while dragging and `animateTo` with the fling velocity on release; a drag that can be cancelled resets cleanly.
- **Do not fight scrolling**: nested scroll and edge gestures (the system back swipe from the screen edge) take priority; keep horizontal swipe zones off the first 16 dp of each edge.
- Haptics through `LocalHapticFeedback` on commit, not on every pixel.

## Reduce Motion — the floor

Android has no single "Reduce motion" switch. **"Remove animations"** (Settings → Accessibility) sets the system animator duration scale to 0. Compose's `MotionDurationScale` observes that scale: a factor of 0 finishes finite animations in the next frame, so `animate*AsState`, `AnimatedVisibility`, `Transition` and `Animatable` **snap** with no code from you. **Scroll fling is intentionally not scaled.**

- **Do not override the scale** (never `ValueAnimator.setDurationScale`, never a custom `MotionDurationScale` in production) and **do not disable it in a debug build** — a developer who set the scale to 0 should see the app obey it.
- **Not verified:** how `rememberInfiniteTransition` / `infiniteRepeatable` behave at scale 0 — the docs do not say. Treat looping motion as the app's responsibility: read the setting and render the static state.

```kotlin
@Composable
fun rememberAnimationsEnabled(): Boolean {
    val resolver = LocalContext.current.contentResolver
    return remember(resolver) {
        Settings.Global.getFloat(resolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) != 0f
    }
}
```

- Use it to **skip decorative loops, parallax, auto-playing carousels and large movement** — keep essential state changes as an instant swap or a crossfade. Re-read on resume (the user can change it while the app is open).
- **Essential feedback survives**: a progress indicator, a selection state, a focus ring. Reduce motion removes travel, not information; state is never conveyed by motion alone.
- Test it: set the scale to 0 (`adb shell settings put global animator_duration_scale 0`) and walk the main journeys; add `MotionDurationScale` with factor 0 to Compose tests where the test must not wait.

## Procedure

1. Detect the Compose BOM, the navigation lane and whether shared-element or predictive-back APIs are in the version in use.
2. Take the design row for the motion (cite the query); map it to one API from the table.
3. Write it with deferred reads (`graphicsLayer`, lambda offset), a `label`, tokens from one `MotionTokens` object.
4. Add the Reduce Motion path for any loop or large movement; give each gesture an accessible alternative.
5. Add test ids on animated controls ([`test-ids`](../test-ids/SKILL.md)); tests per [`unit-testing`](../unit-testing/SKILL.md) with Compose test v2 (animations run on the test clock).

## Validation (exit gate)

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- [ ] No animated value is read in composition for a transform or opacity (`graphicsLayer` / lambda modifiers)
- [ ] With `animator_duration_scale` 0 every main journey works and nothing loops
- [ ] Each gesture has a non-gesture alternative reachable by TalkBack
- [ ] Back previews and completes; no `onBackPressed` override
- [ ] Shared-element keys are unique data classes; the transition degrades to a crossfade where unsupported
- [ ] Macrobenchmark `FrameTimingMetric` shows no new jank on the animated screen

## Handoffs

- Route, back stack, scene transitions → [`navigation`](../navigation/SKILL.md)
- Frame budget, tracing, Macrobenchmark → [`performance`](../performance/SKILL.md)
- Semantics, custom actions, touch targets → [`accessibility`](../accessibility/SKILL.md)
- Motion styles and timing rows → design (`design/ui-ux-pro-max`)
- Loading, failed and offline regions → [`error-handling`](../error-handling/SKILL.md)
- Tests of animated state → [`unit-testing`](../unit-testing/SKILL.md)
