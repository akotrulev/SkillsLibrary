---
name: mobile-react-native-navigation
description: Use when adding or fixing routes in an Expo Router app on SDK 57 — file routes, typed routes, dynamic params, protected routes, modals and sheets, native tabs, linking config; also the React Navigation 7.5 lane for bare RN. Triggers "add a screen", "protect these routes", "make this a modal", "native tabs", "typed href". Do NOT use for links from push or the system (`mobile-react-native-notifications-and-links`), project setup (`-project-setup`) or fetching (`-networking`).
---

# React Native — Navigation (Expo Router)

Owns the **route tree**: which file makes a screen, how screens nest and share chrome, typed params, who may reach what, modals and sheets, native tabs, and the linking config. Incoming links from notifications and the system are [`notifications-and-links`](../notifications-and-links/SKILL.md)'s; this skill owns the files and the navigation between them. Web analog: [`fe-react-routing`](../../../../frontend/react/skills/routing/SKILL.md) — the file-convention idea carries over, RSC and middleware do not.

## Version lane

| Lane | Expo SDK | Router | Native tabs | Protected routes |
|---|---|---|---|---|
| **Primary** | **57** | `expo-router@57.x` | `expo-router/unstable-native-tabs` | `Stack.Protected guard` |
| `[SDK58]` | 58 beta | core reworked | **`expo-router/native-tabs`** (stable path) | adds `redirectTo` |
| Supported | 55–56 | SDK-versioned | `unstable-native-tabs` (compound API from 55; SDK 54 uses standalone `Icon`/`Label`/`Badge` exports) | `Stack.Protected` |
| Floor | 54 | on React Navigation | `unstable-native-tabs`, standalone exports | `Stack.Protected` |
| `[bare]` | any | **React Navigation 7.5** (8.0 alpha) | `@bottom-tabs/react-navigation` | conditional screens |

**Hard rule: never import `@react-navigation/*` in an Expo Router app.** Expo Router forked the React Navigation core in SDK 56; mixed imports resolve two navigation contexts. Migrate with `npx expo-codemod sdk-56-expo-router-react-navigation-replace`. React Navigation 7.5 is only the bare-RN lane below.

Detect: `expo-router` in `package.json` → this lane; `@react-navigation/native` without it → bare `[bare]`.

## When to use

- Adding a screen, a group, shared layout chrome, a tab bar
- Reading typed params; navigating programmatically
- Gating routes behind sign-in; modals and sheets
- Configuring `scheme` and the linking surface
- Diagnosing "layout remounts", "params are strings", "tab bar not native"

## When NOT to use

- Handling a push tap or system link payload → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Scaffold, `app.config.ts` → [`project-setup`](../project-setup/SKILL.md)
- What a route fetches → [`networking`](../networking/SKILL.md)
- What an error route looks like → [`error-handling`](../error-handling/SKILL.md)
- Auth provider wiring → `auth0-react-native`
- Next.js routing → `fe-react-routing`

## File conventions

Inside `src/app/`, **the file is the route**:

| File | Role |
|---|---|
| `index.tsx` | `/` of its folder |
| `_layout.tsx` | Navigator for the folder (`Stack`, `Tabs`, `NativeTabs`); persists across child navigation |
| `[id].tsx` | Dynamic segment → param `id` (a string) |
| `[...rest].tsx` | Catch-all |
| `(group)/` | Group: organises files and shares a layout, adds nothing to the URL |
| `+not-found.tsx` | Unmatched route |
| `+native-intent.tsx` | Rewrites an incoming link before routing ([`notifications-and-links`](../notifications-and-links/SKILL.md)) |

Anchor a group with `unstable_settings = { anchor: '(tabs)' }` so a deep link into a child still has the right back stack.

```tsx
import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="orders/[id]" options={{ title: 'Order' }} />
      <Stack.Screen name="filters" options={{ presentation: 'formSheet' }} />
    </Stack>
  );
}
```

`Stack` is a **native stack** — keep it: `vendor/react-native-guidelines/rules/navigation-native-navigators.md`. Prefer native header options over custom header components.

## Typed routes

`experiments.typedRoutes: true` (template default) generates types into `.expo/types`; `href` is then compile-checked.

```tsx
import { Link, useLocalSearchParams, router } from 'expo-router';

export function OrderRow({ id, title }: { id: string; title: string }) {
  return (
    <Link href={{ pathname: '/orders/[id]', params: { id } }} testID="Orders.Row">
      <Text>{title}</Text>
    </Link>
  );
}

export default function OrderScreen() {
  const { id } = useLocalSearchParams<'/orders/[id]'>();
  return <OrderDetail id={id} />;
}

router.push({ pathname: '/orders/[id]', params: { id: '42' } });
```

- **Params are strings** (or string arrays). Parse and validate numbers, enums and ids with Zod at the screen boundary; a param is untrusted input.
- **In-app navigation is a real `<Link href>`** (an accessible link), not an `onPress` that calls `router.push` on a `View`. `router.push` is for results of logic — after a mutation succeeds.
- `useLocalSearchParams` re-renders this screen only; `useGlobalSearchParams` re-renders on every route change — avoid it in list items.
- Screen-scoped state travels as a param ([`architecture`](../architecture/SKILL.md)); keep payloads small ids, never objects or tokens.

## Protected routes

```tsx
import { Stack } from 'expo-router';
import { useSession } from '@/features/auth/useSession';

export default function RootLayout() {
  const { status } = useSession();
  return (
    <Stack>
      <Stack.Protected guard={status === 'signedIn'}>
        <Stack.Screen name="(tabs)" />
      </Stack.Protected>
      <Stack.Protected guard={status === 'signedOut'}>
        <Stack.Screen name="sign-in" />
      </Stack.Protected>
    </Stack>
  );
}
```

- A `false` guard makes the screens unreachable to client navigation; the navigator falls back to its anchor or first screen. `[SDK58]` `redirectTo="/sign-in"` sends the user explicitly.
- **Protected routes are a client concern, not access control** — the server enforces authorisation on every request.
- Keep the splash screen up until the session status is known (`SplashScreen.preventAutoHideAsync()`), so a signed-in user never flashes the sign-in screen.
- The guard reads a `status` of `loading | signedIn | signedOut`; never treat "loading" as signed out.

## Modals and sheets

```tsx
<Stack.Screen name="filters" options={{ presentation: 'modal' }} />
<Stack.Screen name="pick-date" options={{ presentation: 'formSheet', sheetAllowedDetents: [0.5, 1] }} />
```

A modal or sheet is a **route**, so it survives a link, restores after process death and closes with the system back gesture. Use `presentation: 'modal'` or `'formSheet'` before a JS bottom-sheet library; native modal and menu patterns are [`ui-components`](../ui-components/SKILL.md)'s (`vendor/.../rules/ui-native-modals.md`).

## Native tabs

```tsx
import { NativeTabs } from 'expo-router/unstable-native-tabs';

export default function TabLayout() {
  return (
    <NativeTabs>
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Home</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="house.fill" md="home" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="settings">
        <NativeTabs.Trigger.Label>Settings</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="gear" md="settings" />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
```

**Import path is the lane:** `expo-router/unstable-native-tabs` on ≤ 57, `expo-router/native-tabs` on 58 `[SDK58]`. Facts:

- Each tab needs a `Trigger`; tabs are not added automatically. Icons: `sf` (SF Symbols), `md` (Material Symbols), `src` for an image.
- iOS 26 renders Liquid Glass; background props do not apply. `minimizeBehavior="onScrollDown"` minimises the bar.
- Android allows **at most 5 tabs**; native tabs cannot nest in native tabs; tabs cannot be added at runtime; **all tab screens render eagerly** — defer heavy work with `useFocusEffect`.
- iOS auto-insets the root `ScrollView`; `FlatList` support is limited — prefer FlashList / `ScrollView` roots ([`ui-components`](../ui-components/SKILL.md)). Disable with `disableAutomaticContentInsets` only when handling insets yourself.
- Web has no system tab bar; add `_layout.web.tsx` with `expo-router/ui` headless tabs if web is in scope.
- JS `Tabs` (`expo-router`) is the fallback when a limit above blocks you; record why.

## Linking configuration

- `scheme` in `app.config.ts` is the custom-scheme prefix. **Universal links / App Links** need `ios.associatedDomains` and an Android intent filter with `autoVerify`; the association files live on your domain. Configuration is the plugin's; routing a payload is [`notifications-and-links`](../notifications-and-links/SKILL.md)'s.
- Every deep link is untrusted input: the route's params are validated before use, and a link never grants access a guard would deny.
- Prefer one route per link target; do not build link-only duplicate screens.

## Bare lane — React Navigation 7.5 `[bare]`

Only where Expo Router is not installed: `@react-navigation/native` + `@react-navigation/native-stack`, `createNativeStackNavigator` (never `@react-navigation/stack`), conditional screens for auth, a `linking` config object with `prefixes` and `screens`, `@bottom-tabs/react-navigation` for native tabs. Moving to Expo Router is a [`migration`](../migration/SKILL.md) task.

## Rules

- No `@react-navigation/*` import in an Expo Router app.
- Native navigators only: `Stack` and native tabs; no JS stack.
- Params validated at the screen boundary; payloads are ids.
- `<Link href>` for in-app navigation; `router.*` for logic results.
- Guards are client UX, never authorisation.
- Native-tabs import path matches the SDK.
- Modals and sheets are routes.

## What NOT to do

- No `onPress` + `router.push` on a `View` for navigation.
- No objects, tokens or PII in params.
- No `unstable-native-tabs` import on SDK 58, no `native-tabs` import on 57.
- No guard treating `loading` as signed out.
- No more than 5 native tabs on Android.
- No custom JS header when native header options cover it.

## Handoffs

- Push and system links → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Screens and native patterns → [`ui-components`](../ui-components/SKILL.md)
- Route-scoped state → [`architecture`](../architecture/SKILL.md)
- Failure and not-found UI → [`error-handling`](../error-handling/SKILL.md)
- `scheme`, plugins → [`project-setup`](../project-setup/SKILL.md)
- `testID` on links and tabs → [`test-ids`](../test-ids/SKILL.md)
- Router upgrade, bare → Expo → [`migration`](../migration/SKILL.md)
