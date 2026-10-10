# gluestack v5 — accessible components on a Nativewind core

gluestack v5 is a broad, accessible component set (Button, Input, Modal, Actionsheet, Toast, Select, form controls) styled with a **Nativewind/Tailwind** core. It's the successor to **NativeBase** — which is deprecated; never pick NativeBase for new work. Choose gluestack for a large accessible set with utility-style theming, or when migrating off NativeBase. Because its styling core is Nativewind, the **styling authority is Tailwind** ([`styling`](../../styling/SKILL.md)).

**Version:** **gluestack v5**, New-Architecture ready, components are added via its CLI (copy-in-friendly, you can edit them). Install via `npx expo install` for the RN deps; verify with `expo-doctor`. The setup depends on a Nativewind/Tailwind core — confirm the core against the v5 docs at install time, and do that first (see [`nativewind`](nativewind.md)).

## Setup

```bash
# 1. Set up Nativewind first (see nativewind.md), then:
npx gluestack-ui init            # scaffolds the provider, config, and gluestack-ui-provider
npx gluestack-ui add button input modal toast
```

The CLI writes a `components/ui/` folder you own, plus `GluestackUIProvider`. Install any RN peer deps it names via `npx expo install`.

## Provider — once at the root

```tsx
import { useColorScheme } from 'react-native';
import { GluestackUIProvider } from '@/components/ui/gluestack-ui-provider';
import '@/global.css';                                  // Nativewind

export default function RootLayout() {
  const scheme = useColorScheme() ?? 'light';
  return (
    <GluestackUIProvider mode={scheme}>
      {/* <Stack /> */}
    </GluestackUIProvider>
  );
}
```

## Usage

```tsx
import { Button, ButtonText } from '@/components/ui/button';
import { Modal, ModalBackdrop, ModalContent, ModalHeader, ModalBody, ModalFooter } from '@/components/ui/modal';

function ConfirmButton({ onConfirm, testID }: { onConfirm: () => void; testID?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button action="negative" onPress={() => setOpen(true)} testID={testID}>
        <ButtonText>Delete</ButtonText>
      </Button>
      <Modal isOpen={open} onClose={() => setOpen(false)}>
        <ModalBackdrop />
        <ModalContent testID="Orders.DeleteDialog">
          <ModalHeader>Delete this order?</ModalHeader>
          <ModalBody>This cannot be undone.</ModalBody>
          <ModalFooter>
            <Button variant="outline" onPress={() => setOpen(false)}><ButtonText>Cancel</ButtonText></Button>
            <Button action="negative" onPress={() => { onConfirm(); setOpen(false); }}><ButtonText>Delete</ButtonText></Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}
```

## Theme + dark mode

Theming rides on the Nativewind config — semantic colors as tokens, dark mode via the provider `mode` bound to `useColorScheme()`. Map the [`design/visual-identity`](../../../../../design/visual-identity/SKILL.md) palette into the Tailwind/gluestack config once ([`styling`](../../styling/SKILL.md)). Don't scatter per-element `dark:`.

## testID

Pass `testID` inline; it forwards to the underlying primitive. Since components live in `components/ui/` you own, you can route the prop precisely. → [`test-ids`](../../test-ids/SKILL.md).

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Nothing styled | Nativewind not set up first | Complete [`nativewind`](nativewind.md) before `gluestack-ui init` |
| Reaching for NativeBase docs | NativeBase is deprecated | Use gluestack v5 (the successor) |
| Dark mode static | Provider `mode` not bound to scheme | Bind `mode` to `useColorScheme()` |
| Two styling authorities | Competing `StyleSheet` colors | Tailwind is the authority ([`styling`](../../styling/SKILL.md)) |

## Validation

- Nativewind is configured; app builds iOS + Android; `expo-doctor` clean (New-Arch compatible).
- `GluestackUIProvider` mounts once at the root; a Modal + Toast render.
- Dark mode flips via `mode` bound to `useColorScheme()`; colors come from config tokens.
- One styling authority (Tailwind); `testID` inline lands on the rendered native view.
