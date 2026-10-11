---
name: forms
description: Use when building or fixing a form in an Expo SDK 57 app — React Hook Form 7 + Zod 4, keyboard avoidance, input modes and autofill, secure fields, double-submit guard, ProblemDetails errors mapped with setError. Triggers "build a sign-up form", "keyboard covers the input", "server errors aren't on the fields", "autofill password". Do NOT use for fetch mechanics (`mobile-react-native:networking`), state placement (`-architecture`) or the failure banner (`-error-handling`).
---

# React Native — Forms

Owns **input**: the schema, the form state, the keyboard, native input affordances, and mapping the server's errors back to fields. Web analog: [`fe-react:forms`](../../../../frontend/react/skills/forms/SKILL.md) — RHF + Zod carries over; Server Actions, `<form>`, `<label htmlFor>` and ARIA attributes do not.

## Version lane

| Concern | Primary (SDK 57 · React 19.2) | Notes |
|---|---|---|
| React Hook Form | 7.89 | `Controller` for every `TextInput` — RN inputs are not uncontrolled DOM nodes |
| Zod | 4.6 | `issues[].path` / `code` are the stable error surface; never assert on `message` |
| `@hookform/resolvers` | the Zod 4-compatible release | Detect: `zod` major in `package.json` — v3 projects use the v3 import path, never flag them |
| Keyboard | `react-native-keyboard-controller` (in Expo Go and dev builds) | RN's `KeyboardAvoidingView` is the dependency-free fallback |
| `[SDK58]` | React 19.3 | No form change |
| Floor SDK 54 | React 19.1 | Same recipes |

There is no `useActionState` lane — there is no server action in a native app. A submit is an async function that calls the API client ([`networking`](../networking/SKILL.md)).

## When to use

- Building or fixing a form: sign-in, sign-up, checkout, edit profile, search with filters
- Keyboard covers an input; `Done` / `Next` do not move focus
- Autofill, password managers, one-time codes
- Server validation errors landing on the wrong place
- Multi-step wizards

## When NOT to use

- The request itself, retries, token refresh → [`networking`](../networking/SKILL.md)
- Where draft state lives across screens → [`architecture`](../architecture/SKILL.md); persisting a draft → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- The persistent error banner, mutation-failure UX → [`error-handling`](../error-handling/SKILL.md)
- Camera, photo picker, file picking → [`device-features`](../device-features/SKILL.md)
- Labels, hints, focus order in depth → [`accessibility`](../accessibility/SKILL.md)
- Next.js forms → `fe-react:forms`

## The schema — one per form

```ts
import { z } from 'zod';

export const signUpSchema = z.object({
  email: z.email('Enter a valid email'),
  password: z.string().min(12, 'At least 12 characters'),
  displayName: z.string().trim().min(1, 'Required').max(60),
});

export type SignUpValues = z.infer<typeof signUpSchema>;
```

The schema is the single source of rules; the server revalidates with its own. No validation logic repeated in handlers.

## The form — RHF + `Controller`

```tsx
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Pressable, Text, TextInput } from 'react-native';

export function SignUpForm({ onSubmit }: { onSubmit: (values: SignUpValues) => Promise<void> }) {
  const { control, handleSubmit, setFocus, formState: { isSubmitting } } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    mode: 'onBlur',
    defaultValues: { email: '', password: '', displayName: '' },
  });

  return (
    <>
      <Controller
        control={control}
        name="email"
        render={({ field, fieldState }) => (
          <>
            <TextInput
              testID="SignUp.Email"
              accessibilityLabel="Email"
              value={field.value}
              onChangeText={field.onChange}
              onBlur={field.onBlur}
              inputMode="email"
              autoCapitalize="none"
              autoComplete="email"
              textContentType="emailAddress"
              returnKeyType="next"
              onSubmitEditing={() => setFocus('password')}
            />
            {fieldState.error ? <Text accessibilityRole="alert" testID="SignUp.Email.Error">{fieldState.error.message}</Text> : null}
          </>
        )}
      />
      <Pressable
        testID="SignUp.Submit"
        accessibilityRole="button"
        accessibilityState={{ disabled: isSubmitting, busy: isSubmitting }}
        disabled={isSubmitting}
        onPress={handleSubmit(onSubmit)}
      >
        <Text>Create account</Text>
      </Pressable>
    </>
  );
}
```

Fields follow the same `Controller` shape; `password` and `displayName` are omitted for length. Rules the sample shows:

- **`mode: 'onBlur'`** — feedback without per-keystroke noise; an async rule (is the username taken) is debounced and cancels its request ([`networking`](../networking/SKILL.md)).
- **`isSubmitting` disables the control** — a double tap is a duplicate write. A mutation that must be safe to replay also carries an idempotency key ([`networking`](../networking/SKILL.md)).
- **Error text next to the field**, `accessibilityRole="alert"` so a screen reader announces it, and a label on the input (`accessibilityLabel`); placeholder is not a label.
- **`setFocus` chains fields** from `returnKeyType="next"`; the last field uses `returnKeyType="done"` and submits.
- **Focus the first invalid field** on a failed submit via `shouldFocusError` (default) or `setFocus`.
- **No `useState` per field**; no form state in Zustand or Context.

## Input affordances

| Field | Props |
|---|---|
| Email | `inputMode="email"`, `autoCapitalize="none"`, `autoComplete="email"`, `textContentType="emailAddress"` |
| Password (sign-in) | `secureTextEntry`, `autoComplete="current-password"`, `textContentType="password"` |
| Password (new) | `secureTextEntry`, `autoComplete="new-password"`, `textContentType="newPassword"` |
| One-time code | `inputMode="numeric"`, `autoComplete="one-time-code"`, `textContentType="oneTimeCode"` (iOS and Android SMS autofill) |
| Phone | `inputMode="tel"`, `autoComplete="tel"` |
| Amount | `inputMode="decimal"`; parse with the locale ([`languages`](../languages/SKILL.md)) |
| Free text | `autoCapitalize="sentences"`, `multiline` only when intended |

- `inputMode` is the current prop; `keyboardType` is the legacy equivalent kept only on a project that uses it.
- **A secure field never leaks**: `secureTextEntry` on, no logging of `field.value`, no value in a route param, no persistence of the draft to MMKV or AsyncStorage ([`mobile-<stack>:security`](../../../_shared/security/SKILL.md)). Disable autocorrect and suggestions on it.
- A **show / hide password** toggle is a labelled `Pressable` flipping `secureTextEntry`.
- Pickers (date, select) use native components or `@expo/ui` ([`ui-components`](../ui-components/SKILL.md)), wired through `Controller`.

## Keyboard handling

The keyboard must not cover the focused input, and the submit control must stay reachable.

```tsx
import { KeyboardAwareScrollView } from 'react-native-keyboard-controller';

<KeyboardAwareScrollView
  bottomOffset={24}
  keyboardShouldPersistTaps="handled"
  contentInsetAdjustmentBehavior="automatic"
>
  {children}
</KeyboardAwareScrollView>
```

- **A form is a scroll view** with `keyboardShouldPersistTaps="handled"` — otherwise the first tap on a button only dismisses the keyboard.
- **Prefer `KeyboardAwareScrollView`** (keyboard-controller) or `KeyboardAvoidingView` with `behavior="padding"` on iOS and the manifest's `adjustResize` on Android (the Expo default); do not hand-pad with `Keyboard.addListener` and state — it re-renders per frame.
- **`contentInset`** is the cheap way to add keyboard space to a scroller (`vendor/react-native-guidelines/rules/ui-scrollview-content-inset.md`).
- **Sticky submit** above the keyboard uses keyboard-controller's `KeyboardStickyView`; a modal sheet form follows the sheet's own insets.
- **Dismiss** on scroll (`keyboardDismissMode="interactive"` on iOS, `"on-drag"` on Android) — never trap the keyboard open.
- Test on a small iPhone, a tall Android and with the hardware keyboard attached.

## Server errors → fields

```ts
import type { UseFormSetError } from 'react-hook-form';

export function applyProblemDetails<T extends Record<string, unknown>>(
  problem: ProblemDetails,
  setError: UseFormSetError<T>,
): boolean {
  const fieldErrors = Object.entries(problem.errors ?? {});
  fieldErrors.forEach(([name, messages]) =>
    setError(name as Path<T>, { type: 'server', message: messages[0] }),
  );
  if (fieldErrors.length === 0) setError('root.server', { type: 'server', message: problem.title });
  return fieldErrors.length > 0;
}
```

- A `400` with `errors` maps **per field** (`setError`); a non-field failure goes to `root.server` and the persistent banner ([`error-handling`](../error-handling/SKILL.md)). Never a generic "Something went wrong" over per-field errors.
- **A `409` / stale-version conflict** keeps the user's input and tells them what changed — never silently overwrites.
- **The response is parsed** (Zod) before it is read; an unparseable error body is a root error, not a crash. The `ProblemDetails` type and the client that produces it are [`networking`](../networking/SKILL.md)'s.
- A network failure on submit keeps every typed value; the draft is **not** cleared on error.

## Wizards

One schema per step plus a merged final schema; the accumulated values live in a parent component or a small Zustand store scoped to the flow (never persisted if it holds a secret). Each step is a route ([`navigation`](../navigation/SKILL.md)); validate the step with `trigger(fieldsOfStep)` before advancing; the back gesture returns to the previous step with values intact.

## Rules

- RHF + Zod by default; one Zod schema per form, type inferred, mirrored by the server.
- `Controller` for every input; no `useState`-per-field; no form state in a store.
- `mode: 'onBlur'`; async rules debounced and cancellable.
- Submit control disabled while submitting; replayable writes carry an idempotency key.
- Inputs carry `inputMode`, `autoComplete`, `textContentType`, `returnKeyType` and an accessible label.
- Keyboard: scroll container, `keyboardShouldPersistTaps="handled"`, a keyboard-aware wrapper.
- Server errors mapped to fields with `setError`; non-field errors to `root` and the banner.
- Secrets in a form never logged, never persisted, never put in a route param.
- Every input, error line and submit control carries a `testID` ([`test-ids`](../test-ids/SKILL.md)).

## What NOT to do

- No `TextInput` without a label and `inputMode` / `autoComplete`; no placeholder standing in for a label.
- No `secureTextEntry` password with `autoComplete="off"` that blocks the password manager.
- No `KeyboardAvoidingView` nested inside a scroll view alongside a second keyboard handler.
- No validate-on-every-keystroke; no async rule per keystroke.
- No submit without a disabled / pending guard; no clearing the form on a failed submit.
- No `useFormState`, `useActionState` or `<form action>` — none exist in React Native.
- No Zod assertion on `message` in tests — assert `issues[].path` and `code`.
- No password or token in `AsyncStorage`, MMKV, a route param or a log line.

## Generation steps

1. Confirm the fields, rules and the server error shape (ProblemDetails) and the Zod major.
2. Write the schema and export the inferred type.
3. Build the form: `useForm` + `zodResolver`, one `Controller` per field with the right input props and `testID`s.
4. Wire the keyboard wrapper, `returnKeyType` chain and the submit guard.
5. Wire submit through the API client; map `ProblemDetails` with `setError`; route non-field errors to the banner.
6. Multi-step: schema per step, `trigger` before advancing.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Typecheck and lint with the project's scripts clean.
- Simulator and emulator: open the keyboard on the last field — it is visible and the submit control reachable; chain fields with `Next`; autofill a password.
- Submit invalid → first invalid field focused, errors announced; submit with a `400 errors` body → errors on the right fields; submit twice quickly → one request.
- Dev-side tests (RNTL 14, async `render` / `fireEvent`): `mobile-react-native:component-testing`; assert schema errors on `issues[].path` and `code`.

## Handoffs

- Client, retries, idempotency → [`networking`](../networking/SKILL.md) · banner, conflicts → [`error-handling`](../error-handling/SKILL.md)
- Components inside the form → [`ui-components`](../ui-components/SKILL.md) · labels → [`accessibility`](../accessibility/SKILL.md)
- Locale numbers and dates → [`languages`](../languages/SKILL.md) · ids → [`test-ids`](../test-ids/SKILL.md)
- Secrets and storage → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)
