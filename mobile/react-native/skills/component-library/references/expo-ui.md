# Expo UI — SwiftUI and Jetpack Compose primitives

Expo UI (`@expo/ui`) renders **real SwiftUI views on iOS and real Jetpack Compose views on Android** from React. It is the default source for controls the operating system already provides — switches, pickers, date pickers, menus, sheets — so they look, animate and behave like the platform without a third-party kit. It has been stable since SDK 56; this reference targets the SDK 57 docs.

**Version:** SDK 57 primary (`@expo/ui` 57.x). `[SDK58]` — re-check the component list in the SDK 58 docs after upgrade. Needs a development build (it contains native code): decide in [`project-setup`](../../project-setup/SKILL.md).

## Packages

| Import | Platform |
|---|---|
| `@expo/ui/swift-ui` | iOS and other Apple platforms only |
| `@expo/ui/jetpack-compose` | Android only |
| universal components | One tree across Android, iOS and web |

```bash
npx expo install @expo/ui
```

## The `Host` rule

Every Expo UI tree sits inside a **`Host`**, the bridge between React Native layout and the native toolkit. Flexbox styles apply to the `Host` itself. Inside it Yoga does not run: lay out with the toolkit's containers — `HStack` / `VStack` on iOS, `Row` / `Column` on Android. React Native components may be children of a native component; to return to the native toolkit from there, open a new `Host`.

## Usage

Split by platform file so each bundle carries one toolkit:

```tsx
import { Button, Host } from '@expo/ui/swift-ui';

export function SaveButton({ onPress }: { onPress: () => void }) {
  return (
    <Host matchContents>
      <Button label="Save" onPress={onPress} testID="Profile.Save" />
    </Host>
  );
}
```

`SaveButton.ios.tsx` carries the SwiftUI version and `SaveButton.android.tsx` the Compose version of the same props; screens import `SaveButton` and never branch on `Platform.OS` for it. Confirm the exact component names and props for the installed SDK in `docs.expo.dev/versions/v57.0.0/sdk/ui` before writing — the surface grows each SDK.

## When Expo UI, when an atom

| Use Expo UI | Use your own atom |
|---|---|
| Switch, picker, slider, date and time pickers | Brand-shaped buttons, cards, rows |
| Context menus, native sheets | Layout containers |
| A control that must follow the OS's accessibility and motion behaviour | Anything pure `View` + `Text` expresses |

## Rules

- One `Host` per island; do not nest layout engines inside one another without a new `Host`.
- Native-only components are guarded by platform files, not `Platform.OS` ternaries inside render.
- `testID` inline on the Expo UI control; confirm it lands on the native view in [`test-ids`](../../test-ids/SKILL.md).
- Expo UI is not a theme system: colours still come from [`styling`](../../styling/SKILL.md) tokens passed as props.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Content has zero size | `Host` has no size and `matchContents` is off | Size the `Host` or set `matchContents` |
| Flex props ignored inside | Yoga does not run in the native tree | `HStack` / `VStack` / `Row` / `Column` |
| Works in dev build, absent in Expo Go | Native code outside Go's bundle | Use a development build |
| iOS import crashes Android bundle | Wrong-platform import in a shared file | Split into `.ios.tsx` and `.android.tsx` |

## Validation

- Builds as a development build on iOS and Android; `npx expo-doctor` clean.
- Each control renders from its own platform file; no `Platform.OS` branch around an Expo UI import.
- Dark mode and Dynamic Type / font scale follow the OS with no per-control override.
- `testID` reaches the native view.
