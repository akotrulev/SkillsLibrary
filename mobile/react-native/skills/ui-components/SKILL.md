---
name: mobile-react-native-ui-components
description: Use when writing or fixing a screen or component in an Expo SDK 57 app — Pressable, expo-image, FlashList 2 / Legend List, native menus and modals, text-in-Text, compound components, the loading / loaded / failed region in markup, empty states. Triggers "build this screen", "my list janks", "image flickers", "native menu". Do NOT use for routes (`mobile-react-native-navigation`), animation (`-animation`), theming (`-styling`) or the failure UI (`-error-handling`).
---

# React Native — UI Components

Owns **writing a screen or a component**: composition, the primitive to reach for, lists, images, menus and modals, and the three-state region in markup. Web analog: [`fe-react-component-writer`](../../../../frontend/react/skills/component-writer/SKILL.md) + [`fe-react-ui-rules`](../../../../frontend/react/skills/ui-rules/SKILL.md) — the composition rules carry over; RSC, `'use client'`, `<Link>` and semantic HTML do not.

Design facts (type scale, spacing, touch target, platform convention) come from `design/ui-ux-pro-max` (`--stack react-native`); where the corpus disagrees with this skill, the corpus wins.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86 · React 19.2) | Notes |
|---|---|---|
| React Compiler | On | No `useMemo` / `useCallback` for render cost; keep them where a list item or Reanimated needs identity |
| Lists | FlashList **2.3** or Legend List **3.6** | FlashList 2 is New-Architecture only and **has no `estimatedItemSize`** — samples that pass it are v1 |
| Images | `expo-image` | Not RN `Image` |
| Native UI | Expo UI (`@expo/ui`) stable since SDK 56 | Platform files only — see [`component-library`](../component-library/SKILL.md) |
| `[SDK58]` | React 19.3, native tabs stable | No rule here changes |
| Floor SDK 54 | FlashList 2 still valid | Same recipes |

Detect first: `@shopify/flash-list` major, `@legendapp/list`, `expo-image`, `reactCompiler` in `app.json`. On a project still on FlashList 1, say so and hand to [`migration`](../migration/SKILL.md) — never flag it for lacking v2.

## When to use

- Building a screen, a row, a card, a header or a reusable component
- A list that drops frames, shows blank cells or jumps on update
- Choosing between `Pressable`, native menu, native modal, JS sheet
- Images in lists and avatars; galleries
- Rendering the loading / loaded / failed / empty region

## When NOT to use

- Which file is a route, tabs, modal *routes*, params → [`navigation`](../navigation/SKILL.md)
- Reanimated, gestures, layout animation → [`animation`](../animation/SKILL.md)
- Tokens, dark mode, safe-area policy, breakpoints → [`styling`](../styling/SKILL.md); kit choice → [`component-library`](../component-library/SKILL.md)
- What the failed region shows, the banner, retry, stale marker → [`error-handling`](../error-handling/SKILL.md)
- Inputs and validation → [`forms`](../forms/SKILL.md); test ids → [`test-ids`](../test-ids/SKILL.md); labels and roles → [`accessibility`](../accessibility/SKILL.md)
- Fetching → [`networking`](../networking/SKILL.md)
- Next.js components → `fe-react-component-writer`

## Inputs needed

The screen's data source (a hook that returns `{ data, status }`), its three outcomes (loaded, empty, failed), the primitives the project's component kit already supplies, and whether the Compiler is on.

## Primitives — pick the native one

| Need | Use | Not | Rule file |
|---|---|---|---|
| Tap target | `Pressable` | `TouchableOpacity` / `TouchableHighlight` | `ui-pressable.md` |
| Image | `expo-image` (`contentFit`, `placeholder`, `transition`) | RN `Image` | `ui-expo-image.md` |
| Menu / context menu | native menu (zeego or `@expo/ui`) | a JS dropdown | `ui-menus.md` |
| Sheet / modal | `Modal` with `presentationStyle="formSheet"`, or a route `presentation: 'formSheet'` | a JS bottom-sheet library | `ui-native-modals.md` |
| Gallery / lightbox | `@nandorojo/galeria` | a hand-built `Modal` | `ui-image-gallery.md` |
| Scrolling root | `ScrollView` / list with `contentInsetAdjustmentBehavior="automatic"` | `SafeAreaView` wrapper or manual `insets.top` padding | `ui-safe-area-scroll.md` |
| Dynamic top/bottom space (keyboard, toolbar) | `contentInset` | animated padding | `ui-scrollview-content-inset.md` |
| Measuring | `useLayoutEffect` + `onLayout` | `onLayout` alone | `ui-measure-views.md` |

All rule files are `mobile/react-native/vendor/react-native-guidelines/rules/<file>`. Styling micro-rules (`borderCurve: 'continuous'`, `gap`, `boxShadow`) are `ui-styling.md` and owned by [`styling`](../styling/SKILL.md).

```tsx
import { Pressable, Text } from 'react-native';
import { Link } from 'expo-router';

type OrderRowProps = { id: string; title: string; total: string; onArchive: (id: string) => void };

export function OrderRow({ id, title, total, onArchive }: OrderRowProps) {
  return (
    <Link href={{ pathname: '/orders/[id]', params: { id } }} asChild>
      <Pressable
        testID="Orders.Row"
        accessibilityRole="link"
        onLongPress={() => onArchive(id)}
        style={{ minHeight: 44 }}
      >
        <Text>{title}</Text>
        <Text>{total}</Text>
      </Pressable>
    </Link>
  );
}
```

Row navigation is a real `<Link>` (navigation owns the rule); the hit area is ≥ 44 pt.

## Text lives in `<Text>`

Every string renders inside `<Text>`; a bare string in a `View` crashes. Guard conditionals with a boolean or ternary — `{count && <Badge/>}` renders `0` as raw text and crashes: `rules/rendering-no-falsy-and.md`, `rendering-text-in-text-component.md`. Never lock text scale (`allowFontScaling={false}`) — [`accessibility`](../accessibility/SKILL.md).

## Lists — virtualize everything

An unbounded list is a **virtualized list**, even a short one: `rules/list-performance-virtualize.md`. A `ScrollView` + `.map` is for a fixed, small, known set (a settings page), never fetched data.

```tsx
import { FlashList } from '@shopify/flash-list';

export function OrderList({ orders, onArchive }: { orders: OrderSummary[]; onArchive: (id: string) => void }) {
  return (
    <FlashList
      data={orders}
      keyExtractor={(order) => order.id}
      getItemType={(order) => order.kind}
      renderItem={({ item }) => (
        <OrderRow id={item.id} title={item.title} total={item.total} onArchive={onArchive} />
      )}
      contentInsetAdjustmentBehavior="automatic"
      testID="Orders.List"
    />
  );
}
```

- **FlashList 2 sizes itself** — delete `estimatedItemSize`, `estimatedListSize`, `estimatedFirstItemOffset`, `onBlankArea`; `inverted` becomes `maintainVisibleContentPosition` (on by default; `startRenderingFromBottom` for chat); `MasonryFlashList` becomes the `masonry` prop. Keep `getItemType` for heterogeneous rows: `rules/list-performance-item-types.md`.
- **Stable references** — pass `data` straight through; do not `.map` / `.filter` into new objects in render (`rules/list-performance-function-references.md`). Filter upstream or in a memoized selector.
- **Primitives into rows**, not the whole `item` where a row is memoized (`rules/list-performance-item-memo.md`); no inline object / style literals in `renderItem` (`rules/list-performance-inline-objects.md`).
- **One callback at the list root** that the row calls with its id (`rules/list-performance-callbacks.md`) — shown in `OrderRow` above.
- **Rows are cheap** — no query, no stack of Context reads, no heavy compute in a row (`rules/list-performance-item-expensive.md`); lift data into the parent.
- **Thumbnails, not originals** — request a resized URL (`rules/list-performance-images.md`).
- **Keys are domain ids**, never the index. **Stable header** — search and filters live in `ListHeaderComponent`, and a failure replaces the rows / `ListEmptyComponent`, never the header ([`error-handling`](../error-handling/SKILL.md)).
- **Legend List** (`@legendapp/list`) is the equal alternative; its `recycleItems` and `getItemType` take the place of FlashList's recycling. One list library per app.
- **Pull-to-refresh** (`refreshControl` / `onRefresh`) is the canonical refetch on mobile; wire it to `refetch` ([`networking`](../networking/SKILL.md)).
- Frame-rate measurement and profiling → [`performance`](../performance/SKILL.md).

## The three-state region, in markup

A data region renders **exactly one** of loading, failed, empty, or loaded, and the failure is scoped to the response-dependent subtree.

```tsx
export function OrdersRegion() {
  const orders = useOrders();

  if (orders.status === 'pending') return <OrdersSkeleton testID="Orders.Loading" />;
  if (orders.status === 'error') return <RegionFailure error={orders.error} onRetry={orders.refetch} testID="Orders.Failed" />;
  if (orders.data.length === 0) return <EmptyOrders testID="Orders.Empty" />;
  return <OrderList orders={orders.data} onArchive={archive} />;
}
```

The region sits **under** the screen header, search and filters, which render regardless. A drifted response is *failed*, never empty. The `RegionFailure` body, the persistent banner and the stale marker are [`error-handling`](../error-handling/SKILL.md)'s; this skill places the slot and gives it a `testID`.

## Composition

- **Compound components** over a pile of boolean props: a `Card` with `Card.Header` / `Card.Body` sharing context; the provider throws outside its parent. `rules/design-system-compound-components.md`.
- **Container / presentation split** where logic is real: a hook returns state and handlers, the component renders. A component that only forwards props to a kit control is not a component ([`component-library`](../component-library/SKILL.md) D8).
- **Ref as a prop** on React 19 — no `forwardRef`; `forwardRef` only on a React 18 project.
- **Children for composition**, not render-prop towers; no more than one level of nested conditional rendering — extract it.
- **One import point for design-system pieces**: `rules/imports-design-system-folder.md`.
- **`use client` does not exist** — nothing here is a Server Component; do not emit the directive.

## Rules

- Native primitive over JS imitation: `Pressable`, `expo-image`, native menu, native modal.
- Every data-bearing list is virtualized; FlashList 2 samples carry no `estimatedItemSize`.
- Every data region has loading / loaded / failed / empty slots; failure never replaces the header or filters.
- Strings only inside `<Text>`; conditional rendering with a boolean, never `0 && …`.
- Touch targets ≥ 44 pt; interactive elements carry `testID` ([`test-ids`](../test-ids/SKILL.md)) and an accessible label ([`accessibility`](../accessibility/SKILL.md)).
- Keys are stable ids; callbacks hoisted out of rows; no inline object or style literal in `renderItem`.
- Compound component over boolean-prop sprawl; ref as a prop on React 19.
- No server data copied into a store to feed a list — [`architecture`](../architecture/SKILL.md).

## What NOT to do

- No `TouchableOpacity`; no RN `Image`; no `ScrollView` + `.map` over fetched data.
- No `estimatedItemSize` on FlashList 2; no `inverted`; no `MasonryFlashList`.
- No JS dropdown, JS bottom sheet or hand-built lightbox where a native one exists.
- No `SafeAreaView` around a scroller; no `paddingTop: 44`.
- No `{n && <X/>}` with a number; no raw string in a `View`.
- No query, no `useContext` stack, no inline style literal inside a list row.
- No `router.push` on a `View` for navigation; no animation here (Reanimated is [`animation`](../animation/SKILL.md)'s).
- No early `return <Error/>` above the search and filter header.
- No `forwardRef` on React 19; no `'use client'`.

## Generation steps

1. Detect the lane: list library and major, Compiler on or off, component kit, React major.
2. Name the data hook's states and the screen's empty / failed bodies before writing markup.
3. Build header (stable) → region (one of four slots) → rows (primitive props, hoisted callback).
4. Use the native primitive for tap, image, menu, modal and scroll insets.
5. Add `testID`s and labels on every interactive element and list container.
6. Check the rules above, then hand animation, navigation and failure bodies to their owners.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Typecheck and lint with the project's scripts (`eslint-config-expo/flat`) clean.
- On a simulator and an emulator: scroll the list fast — no blank cells; rotate; turn text size to maximum — nothing clips.
- Throttle the network and force an error: header and filters stay, the rows body swaps to the failed slot.
- Dev-side component tests: `mobile-react-native-component-testing`.

## Handoffs

- Routes, modals as routes → [`navigation`](../navigation/SKILL.md) · motion → [`animation`](../animation/SKILL.md)
- Tokens and theme → [`styling`](../styling/SKILL.md) · kit → [`component-library`](../component-library/SKILL.md)
- Failed region, banner, stale → [`error-handling`](../error-handling/SKILL.md)
- Lists at scale, profiling → [`performance`](../performance/SKILL.md)
- Labels, roles, focus → [`accessibility`](../accessibility/SKILL.md) · ids → [`test-ids`](../test-ids/SKILL.md)
- Data → [`networking`](../networking/SKILL.md) · inputs → [`forms`](../forms/SKILL.md)
