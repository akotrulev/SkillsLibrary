---
name: performance
description: Use when an Expo SDK 57 app janks, starts slowly or ships a heavy bundle — the vendored list rules (virtualize, stable references, item types), the React Compiler and manual memoization, startup via expo-observe, Expo Atlas bundle analysis, React Native DevTools, Hermes, images. Triggers "list scrolls slowly", "cold start is slow", "bundle is huge", "do I still need useMemo". Do NOT use for animation (`mobile-react-native:animation`) or failure UI.
---

# React Native — Performance

Owns **frame budget, startup and bundle size**: the list rules, what the React Compiler changes about memoization, how to measure startup in production, and how to find what is in the bundle. The JS thread and the UI thread each have a ~16 ms budget at 60 Hz (~8 ms at 120 Hz); blowing it is a correctness bug under CLAUDE.md § Mobile code rules, not polish. Web analog: [`fe-react:performance`](../../../../frontend/react/skills/performance/SKILL.md) — measure-first and bundle discipline carry over; RSC streaming, Core Web Vitals, `next/script` and `next/image` do not.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86) | Notes |
|---|---|---|
| Engine | Hermes V1 (default since RN 0.84 / SDK 56) | JSC is not an option; SDK 56 + Hermes V1 + Reanimated is the memory regression fixed in `expo@57.0.9` — steer to 57 |
| React Compiler | 1.0, **on** in the default template (`reactCompiler: true`) | Changes memoization advice — [below](#the-react-compiler-and-manual-memoization) |
| Lists | FlashList 2.3 (no `estimatedItemSize`) · Legend List 3.6 | Match what the project has |
| Images | `expo-image` | Disk + memory cache, placeholders, resize |
| Startup metrics | `expo-observe` (**beta**) — time to first render, time to interactive | Not in Expo Go; development or production build, SDK 55+ |
| Bundle | Expo Atlas (**experimental**) | `EXPO_ATLAS=true npx expo export`, then `npx expo-atlas .expo/atlas.jsonl` |
| Profiling | React Native DevTools (Profiler, Network, Memory), Hermes sampling profiler | Built in; no Flipper |
| `[SDK58]` | RN 0.88 | Same rules; Reanimated 4.7 — [`animation`](../animation/SKILL.md) |
| RN 0.87 | strict TS API: deep `react-native/Libraries/*` imports are errors; **`InteractionManager` is removed** | Replace deferred-work patterns with `requestIdleCallback` or a post-render effect |
| Floor 54 | Compiler optional | Detect `reactCompiler` before applying the Compiler section |

Detect first: whether the compiler is on (`app.json` / `babel.config.js`), which list library is installed, whether `expo-observe` or a crash reporter already reports startup, and the Hermes build (release, never a dev build, for any timing).

**Measure on a release build on a real, mid-range device.** Dev mode, a simulator and an M-series laptop all lie. No optimisation lands without a before-and-after number.

## When to use

- A list, feed or grid janks, blanks, or uses too much memory
- Cold-start or time-to-interactive is slow; setting a startup budget
- The bundle or store download is large; finding what is in it
- "Do I still need `useMemo` / `useCallback` / `memo`?"
- A screen re-renders on every keystroke

## When NOT to use

- Reanimated, gestures, UI-thread animation → [`animation`](../animation/SKILL.md)
- Which list library and how rows are authored → [`ui-components`](../ui-components/SKILL.md)
- Request timing, caching → [`networking`](../networking/SKILL.md)
- Crash reporting, release-health thresholds → [`mobile-<stack>:observability`](../../../_shared/observability/SKILL.md)
- Native Swift / Kotlin → `mobile-ios:performance` / `mobile-android:performance`

## List rules — the vendored set

Authority: `mobile/react-native/vendor/react-native-guidelines/rules/`. Skills point in by filename; the vendored tree is never edited.

| File | Rule |
|---|---|
| `list-performance-virtualize.md` | **Virtualize every list**, even a short one — FlashList or Legend List, never `ScrollView` + `.map` |
| `list-performance-function-references.md` | Don't `map` or `filter` data before the list; stable object references let virtualization skip unchanged rows; transform **inside the item**, read dynamic values through a store selector |
| `list-performance-callbacks.md` | One callback at the list root; the item calls it with its id — never a new closure per row |
| `list-performance-inline-objects.md` | No inline object or style in `renderItem`; pass the item or primitives, hoist static styles |
| `list-performance-item-memo.md` | Pass **primitives** to rows so `memo()` can compare; only what the row uses |
| `list-performance-item-expensive.md` | Rows are cheap: no query, no heavy `useMemo`, few contexts — fetch in the parent, use selectors |
| `list-performance-item-types.md` | Heterogeneous lists give each row a `type` and use `getItemType` so recycling pools don't mix layouts |
| `list-performance-images.md` | Compressed, right-sized thumbnails (2× display size) through `expo-image` |

```tsx
const renderOrder = ({ item }: { item: OrderRow }) => <OrderRowView id={item.id} title={item.title} total={item.total} />;

export function OrdersList({ rows }: { rows: OrderRow[] }) {
  return (
    <FlashList
      data={rows}
      renderItem={renderOrder}
      keyExtractor={(row) => row.id}
      getItemType={(row) => row.kind}
      testID="Orders.List"
    />
  );
}
```

- **Keys are stable domain ids**, never the index; `keyExtractor` is set.
- A list that **needs to scroll to a position** reads it from a shared value or ref, not state: `rules/scroll-position-no-state.md`.
- Pagination through `onEndReached` + `fetchNextPage` with a threshold, and an end-reached footer that is a region of its own ([`ui-components`](../ui-components/SKILL.md)).
- Hoist `Intl.*` formatters to module scope, not into render: `rules/js-hoist-intl.md`.
- Keep state minimal and derive the rest: `rules/react-state-minimize.md`, `react-state-dispatcher.md`, `state-ground-truth.md`.
- Images: `rules/ui-expo-image.md`; galleries: `rules/ui-image-gallery.md`.

## The React Compiler and manual memoization

With the compiler on, it memoizes components and hooks at build time. So:

- **Do not hand-write `useMemo`, `useCallback` or `memo` for render cost.** They are noise the compiler already handles, and the vendored rules say so (`list-performance-callbacks.md`, `list-performance-inline-objects.md`: "if you aren't using React Compiler, wrap these with `useCallback`").
- **Keep them where identity is a contract:** an effect dependency that must not change, a value handed to a native or Reanimated worklet boundary, a stable `renderItem` handed to a list on a project **without** the compiler, and `memo()` on a list row on a project where profiling shows the row re-rendering.
- **Write code the compiler can analyse.** Destructure functions at the top of render rather than dotting into an object — `rules/react-compiler-destructure-functions.md`; use `.get()` / `.set()` on Reanimated shared values, never `.value` — `rules/react-compiler-reanimated-shared-values.md` ([`animation`](../animation/SKILL.md)). No mutation of props, state or refs during render; a component the compiler bails out on is reported by `npx react-compiler-healthcheck`.
- **It does not fix data shape.** A parent that rebuilds the data array every render, or a row that fetches, is still slow — the list rules above apply with or without the compiler.
- **A project without the compiler** (a floor lane, or `reactCompiler: false` on purpose) keeps the manual rules; never flag it for lacking the compiler, and never turn it on as a side effect.

## Startup — measure it in production

Cold start has a native phase (process, Hermes, bundle load) and a JS phase (providers, first render, first data). The JS phase is what you control.

```tsx
import { ObserveRoot, markInteractive } from 'expo-observe';

export default function RootLayout() {
  return (
    <ObserveRoot>
      <Providers>
        <Stack />
      </Providers>
    </ObserveRoot>
  );
}
```

- **`expo-observe` (beta)** — `ObserveRoot` around the root layout gives time to first render; `markInteractive()` on the screen where the user can act gives time to interactive (per-route cold and warm times with the Expo Router integration, SDK 56+). It exports OpenTelemetry signals to EAS Observe or your own endpoint, and it does not dispatch from debug builds. It is **not** a crash reporter and has no native crash reporting — keep the one reporter from [`mobile-<stack>:observability`](../../../_shared/observability/SKILL.md). Verify its current status at docs.expo.dev before adopting.
- **Keep the first screen light:** render the shell first; defer heavy libraries to the screen that needs them (a dynamic `import()` or an inline `require` inside the function); no synchronous `JSON.parse` of a large file, no sync storage scan, no SDK `init` that blocks (initialise analytics after first render).
- **Hold the splash until the data the first screen needs is ready**, not until everything is — `expo-splash-screen` `preventAutoHideAsync()` / `hideAsync()` once, from the root.
- **Set a budget and gate on it** (cold start to interactive on a mid-range Android) with the release-health thresholds ([`mobile-<stack>:release`](../../../_shared/release/SKILL.md)); a Baseline Profile is the Android native lane's.
- **Inline requires** are on by default in Metro for Expo — do not disable them.

## Bundle — find it, then cut it

1. `EXPO_ATLAS=true npx expo export --platform all`, then `npx expo-atlas .expo/atlas.jsonl` (experimental — if the flag has no effect on the SDK, check `EXPO_UNSTABLE_ATLAS=true`). Look at the largest modules per platform.
2. **Imports:** a barrel import of a large library (`lodash`, an icon pack) pulls it whole; import the leaf or use a lighter library. Replace `moment` with `Intl` / `date-fns`.
3. **Assets:** compress and size images; subset and limit fonts to the weights used ([`styling`](../styling/SKILL.md)); remove unused Lottie and video from the bundle in favour of remote assets.
4. **Native size:** `expo-doctor`, remove unused config-plugin modules, split ABIs on Android (App Bundle does it per device).
5. Re-run Atlas; record the delta.

## Rendering

- **Don't re-render the world on a keystroke:** keep fast-changing state (search text) local to the input and debounce the query, not the field; read shared state through selectors (`useStore((s) => s.keyword)`).
- **React Native DevTools → Profiler** for re-render causes ("why did this render"), **Network** for timing, **Memory** for leaks (a listener, timer or subscription not cleaned up in the effect return).
- **Never block the JS thread:** no heavy synchronous compute in render or in an event handler; move it to a worklet, a native module, or chunk it; no `console.log` in a hot path in release.
- **`InteractionManager` is gone on RN 0.87** — don't introduce it on a lane that will lose it.
- Text inside `<Text>`, falsy values guarded: a crash is the worst performance (`rules/rendering-no-falsy-and.md`, `rendering-text-in-text-component.md`).

## Rules

- Measure on a release build on a real mid-range device; every change carries before and after numbers.
- Every list is virtualized; rows are cheap, get primitives or stable items, and have stable keys.
- No inline objects, closures or pre-mapped data crossing into a list.
- Compiler on → no memoization for render cost; keep it only where identity is a contract.
- Images are right-sized and go through `expo-image`.
- Startup is measured in production, with a budget; the first screen renders before heavy modules load.
- The bundle is analysed with Atlas before it is trimmed; barrel imports of large libraries are leaf imports.
- No JS-thread blocking work; no leak left in an effect.

## What NOT to do

- No `ScrollView` + `.map` for data of unknown size; no `FlatList` where FlashList or Legend List is already the project's.
- No `useMemo` / `useCallback` / `memo` sprinkled "for performance" on a compiler-on project; no turning the compiler on or off as a side effect.
- No `.value` on a shared value in a compiler-on project; no `props.fn()` / `router.push` dotted calls in a handler the compiler must key.
- No query, heavy `useMemo` or several contexts inside a list row.
- No full-resolution image in a thumbnail; no remote image through `<Image>` without a cache.
- No timing on a dev build or a simulator; no optimisation without a number.
- No analytics or crash SDK `init` that blocks first render; no second crash reporter to measure startup.

## Generation steps

1. Detect the compiler, list library, image component and any startup instrumentation.
2. Profile the slow path on a release build and name the cause (re-render, JS block, bundle, image).
3. Apply the matching rule from the vendored set or the sections above — one cause per change.
4. Re-measure; record before and after in the change description.
5. Add or update a `testID` on any list container touched ([`test-ids`](../test-ids/SKILL.md)).

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Release build, mid-range device: scrolling a 1,000-row list holds the frame rate and shows no blank rows; typing in a search field does not re-render every visible row (DevTools Profiler).
- Atlas export shows no duplicate large module and a delta against the previous export.
- Cold start to interactive is within the recorded budget in `expo-observe`.
- Dev-side: a row component's render count is stable across a parent update (RNTL + a render counter) — [`component-testing`](../component-testing/SKILL.md).

## Handoffs

- Animation and gestures → [`animation`](../animation/SKILL.md) · list authoring → [`ui-components`](../ui-components/SKILL.md)
- Crash reporter, release-health thresholds → [`mobile-<stack>:observability`](../../../_shared/observability/SKILL.md), [`mobile-<stack>:release`](../../../_shared/release/SKILL.md)
- State placement → [`architecture`](../architecture/SKILL.md) · fonts and assets → [`styling`](../styling/SKILL.md)
- Device-level profiling and load → `qa-mobile-typescript` (peer)
