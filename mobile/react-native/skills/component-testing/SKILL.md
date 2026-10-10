---
name: mobile-react-native-component-testing
description: Use when a React Native component, hook or logic needs a dev-side test — Jest + jest-expo + React Native Testing Library 14 (async render/fireEvent/act) for anything that renders, plain Jest for anything that doesn't, native modules faked at the boundary. Triggers "unit-test this screen", "test my hook", "RNTL v14 migration", "jest can't find native module". Do NOT use for device journeys (`qa-mobile-typescript`) or Vitest (not viable in RN).
---

# React Native — Component & Pure-Logic Testing (Jest + RNTL 14)

Owns **every dev-side test in an Expo app**, at two altitudes: **component tests** (it renders → RNTL) and **pure-logic tests** (it doesn't → plain Jest, no renderer). The split is mechanical — *does the unit need a renderer?* Web analog: [`fe-react-component-testing`](../../../../frontend/react/skills/component-testing/SKILL.md) — query-by-role-first, behaviour-over-implementation, logic-not-markup carry over; **jsdom, Vitest, `vi.*` and async Server Components do not exist here.**

**Boundary.** Real devices, real navigation, real network and cross-screen journeys are `qa-mobile-typescript`'s — **Appium**, or its **Maestro** lane on Expo projects (plan 003). A component test fakes the native layer, so it can never prove a gesture, a permission dialog or a deep link on a device.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86 · React 19.2) | Notes |
|---|---|---|
| Runner | **Jest only** — `jest-expo` preset | **Vitest is not viable for React Native** (no Metro transform, no RN preset); never propose it |
| `@react-native/jest-preset` | from RN 0.87 | The RN-core preset moved out of `react-native`; `jest-expo` wraps the right one for the SDK |
| RNTL | **14** (`@testing-library/react-native`) | Needs React 19+, RN 0.78+, Node `^22.13 \|\| >=24`; uses `test-renderer` 1.x (pick the line matching your React 19 minor), not `react-test-renderer` |
| RNTL async API | `render`, `renderHook`, `rerender`, `unmount`, `fireEvent` (+ `press`, `changeText`, `scroll`), `act` all return Promises | **`await` every one** — an un-awaited `render` is a wrong test |
| `[RNTL 13]` | Sync `render`; `renderAsync` / `fireEventAsync` from 13.3 | React 18 projects stay on 13 — correct for them; say a v14 move is a migration |
| `[SDK58]` | RN 0.88 · React 19.3 | Pick the `test-renderer` line for 19.3 |

**v13 → v14 codemods:** `npx codemod@latest rntl-v14-update-deps --target .` (swaps the renderer dependencies — reinstall after), then `npx codemod@latest rntl-v14-async-functions --target ./src`; add `--param customRenderFunctions="renderWithProviders"` for custom render helpers. Both are rerun-safe, skip namespace imports and helpers inside test files — **read the diff**. v14 also removes `update` (use `rerender`), `getQueriesForElement` (use `within`), `UNSAFE_*` queries, `concurrentRoot`, `createNodeMock` and `renderAsync`/`fireEventAsync`/`renderHookAsync` (rename to the plain names).

Detect first: RNTL major in `package.json`, the preset (`jest-expo`), React major, and any existing `renderWithProviders` helper — extend it.

## When to use

- A component has **logic**: conditional render, formatted display, a handler that changes state, a derived disabled state, a reducer
- A hook with real logic (reducer, derived value, subscription, `AppState` handling)
- The region states from [`error-handling`](../error-handling/SKILL.md): failed keeps the filters, stale keeps the rows, offline is not failed
- A Zod schema, formatter, mapper, `parseRetryAfter`, store, query-key builder — plain Jest

## When NOT to use

- Device journeys, gestures, permission dialogs, deep links, push → `qa-mobile-typescript` (peer: Appium, or Maestro on Expo — plan 003)
- Markup-only components with no branches — a snapshot of hand-written markup is a tautology
- Writing `testID`s → [`test-ids`](../test-ids/SKILL.md); tests here **consume** them as the last-resort query
- Request behaviour against a real API → `qa-api-typescript`
- Native Swift / Kotlin → `mobile-ios-unit-testing` / `mobile-android-unit-testing`

## Test what has behaviour

| Unit | Test? | Assert |
|---|---|---|
| Conditional render, formatted display, handler → state | Yes (RNTL) | Right branch per prop; action → visible change |
| Region states (loading / failed / stale / offline / empty) | Yes (RNTL) | Each renders its own body; chrome survives failure; failed is never empty |
| Form + Zod + RHF | Yes (RNTL) | Invalid input → field error by role; submit not called |
| Hook with logic | Yes (`renderHook`) | Action → returned value changes |
| Zod schema, formatter, mapper, `AppError` helpers, store | **Yes (plain Jest)** | Accept and reject by `issues[].path` / `code`; boundaries; the empty input |
| Navigation structure, deep-link behaviour | Partly | `renderRouter` from `expo-router/testing-library` for route resolution; the device is QA's |
| Type-only modules, barrels, constants, a wrapper that only forwards | No | Nothing |

`*.test.ts` for pure logic, `*.test.tsx` for components — the extension is the signal the audit greps rely on.

## Setup

Install `jest-expo jest @testing-library/react-native test-renderer` (and `@types/jest`); `npx expo install` picks versions the SDK ships.

```json
{
  "jest": {
    "preset": "jest-expo",
    "setupFilesAfterEnv": ["<rootDir>/jest.setup.ts"],
    "transformIgnorePatterns": [
      "node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@sentry/react-native|native-base|react-native-svg)"
    ]
  }
}
```

Register RNTL's built-in matchers (`toBeOnTheScreen`, `toBeDisabled`, `toHaveTextContent`) once in `jest.setup.ts` through the extend-expect entry of the installed version — confirm its path in the v14 docs — and reset mocks with `restoreMocks: true`. Use the preset's own `transformIgnorePatterns` unless a package fails to parse; extend it, don't replace it.

## Core API — everything awaited

```tsx
import { render, screen, userEvent } from '@testing-library/react-native';
import { Counter } from './Counter';

describe('Counter', () => {
  it('Should_ShowOne_When_IncrementPressed', async () => {
    const user = userEvent.setup();
    await render(<Counter />);

    await user.press(screen.getByRole('button', { name: 'Increment' }));

    expect(screen.getByRole('text', { name: 'Count' })).toHaveTextContent('1');
  });
});
```

- **Query priority:** `getByRole` (with `name`) → `getByLabelText` → `getByText` → `getByPlaceholderText` → **`getByTestId` last**. A test that can only find a control by `testID` is a hint it has no role or label ([`accessibility`](../accessibility/SKILL.md)).
- **`get*` throws, `query*` returns null (assert absence), `find*` is async and retries** (assert what appears later).
- **`userEvent` for user actions** (`press`, `type`, `clear`, `longPress`, `scrollTo`); `fireEvent` only for events a user cannot produce. Both are awaited.
- **`await act(async () => …)`** — `act` always returns a Promise in v14; never call it bare.
- **`rerender`**: `await screen.rerender(<Card title="b" />)` — not `update`.
- **Providers:** one `renderWithProviders(ui)` wrapping a **fresh `QueryClient` per test** (`retry: false`, `gcTime: Infinity`), the safe-area provider with fixed insets, and a stub theme — never a shared client.

```tsx
export async function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  return render(ui, {
    wrapper: ({ children }) => (
      <SafeAreaProvider initialMetrics={{ frame: { x: 0, y: 0, width: 390, height: 844 }, insets: { top: 47, left: 0, right: 0, bottom: 34 } }}>
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </SafeAreaProvider>
    ),
  });
}
```

## Async — never sleep

Assert on a **condition**, never a delay: `await screen.findByRole(...)`, `await waitFor(() => expect(...))` (pure assertions in the callback), `await waitForElementToBeRemoved(...)`. For timers (a "still loading" tier, a debounce, a retry delay) use **fake timers**: `jest.useFakeTimers()` and `await act(async () => { await jest.advanceTimersByTimeAsync(6000); })`. No `setTimeout` waits in a test.

## Fake the native layer at the boundary

Native modules have no native side in Jest. **Fake the module at the adapter or the package boundary**, not React internals, and fake only what the unit uses.

| Module | Fake with |
|---|---|
| `expo-secure-store`, `expo-haptics`, `expo-notifications`, `expo-location` | `jest.mock('<module>', () => ({ … }))` with the 1–3 functions the unit calls; assert on the call, not the module |
| `@react-native-community/netinfo` | the package's own `jest/netinfo-mock.js`, or a hand-driven listener to test offline → online |
| `AppState` | `jest.spyOn(AppState, 'addEventListener')` capturing the listener; call it to simulate foreground |
| `expo-router` hooks | `renderRouter` (real route tree in memory) before `jest.mock('expo-router')` |
| `fetch` | `jest.spyOn(globalThis, 'fetch')` returning a `Response`; for several endpoints MSW (`msw/native`) so the real client code runs |
| Reanimated | the library's Jest setup; assert the end state, not frames |
| `Date` / time | `jest.setSystemTime` under fake timers; inject the clock |

- **Prefer fakes over mocks of your own code**: inject `getAccessToken` / `refreshAccessToken` (`networking`) and pass a fake; don't `jest.mock` your own module to dodge an import.
- **The adapter is the place that catches a missing module** ([`error-handling`](../error-handling/SKILL.md)); a test asserts the adapter's *unavailable* result, with no `try/catch` in the test.
- `jest.clearAllMocks()` is not needed with `restoreMocks: true`; never let call history leak across tests.

## Samples that follow the house test rules

```tsx
it('Should_KeepFiltersAndShowFailure_When_OrdersQueryFails', async () => {
  const user = userEvent.setup();
  jest.spyOn(globalThis, 'fetch').mockResolvedValue(problemResponse(503));
  await renderWithProviders(<OrdersScreen />);

  await user.type(screen.getByLabelText('Search orders'), 'shoes');

  expect(await screen.findByTestId('Orders.Error')).toBeOnTheScreen();
  expect(screen.getByLabelText('Search orders')).toHaveDisplayValue('shoes');
});

it.each([
  ['5', 5000],
  ['0', 0],
])('Should_ParseDeltaSeconds_When_RetryAfterIs_%s', (header, expected) => {
  expect(parseRetryAfter(header)).toBe(expected);
});
```

- One behaviour per test, `Should_X_When_Y`; `it.each` for variants — no `if` / `for` driving assertions.
- **No `try`/`catch` in a test body.** An expected rejection is `await expect(promise).rejects.toThrow(...)`; cleanup is `afterEach`.
- **One expected value per assertion** — never `200 or 204`; a failed parse names the field path and payload (assert on `issues[].path` / `code`, not the message).
- Test data from a builder (`anOrder({ status: 'shipped' })`) once a shape has four or more fields.
- **No snapshot of a whole screen**; no querying by style or host-element type; no assertions on `result.current` for a rendered component.

## Hooks

```tsx
it('Should_OpenSheet_When_OpenCalled', async () => {
  const { result } = await renderHook(() => useDisclosure());

  await act(async () => result.current.open());

  expect(result.current.isOpen).toBe(true);
});
```

Pass a `wrapper` for hooks that read context; test the hook's contract, not its internals.

## Rules

- Jest + `jest-expo` + RNTL 14; **never Vitest**.
- **Every RNTL call is awaited** — `render`, `renderHook`, `rerender`, `unmount`, `fireEvent.*`, `userEvent.*`, `act`.
- Role / label before `testID`; `userEvent` for user actions; matchers over snapshots.
- Native modules faked at the boundary, fakes over mocks of your own code, a fresh `QueryClient` per test.
- Fake timers, not sleeps; no `try` / `catch` and no `if` in a test body; one expected value per assertion.
- Plain `*.test.ts` for logic that doesn't render; logic, not markup.
- Device journeys go to `qa-mobile-typescript`.

## What NOT to do

- No `render(...)` without `await` on RNTL 14; no `act(() => …)` bare; no `fireEvent` for a user press.
- No Vitest, `vi.mock`, jsdom or `@testing-library/react` (the DOM one) in an RN project.
- No `UNSAFE_getByType`, `update`, `concurrentRoot` or `createNodeMock` — removed in v14.
- No real network, real secure store or real timers in a unit test; no `setTimeout` waits.
- No snapshot of a whole screen; no testing the library (that `useState` updates, that FlashList scrolls).
- No shared `QueryClient` across tests; no test that only passes in file order.
- No re-implementing E2E by mocking the router and calling it a journey.

## Generation steps

1. Detect RNTL, React and the preset; match the project's helper and matchers.
2. Classify each unit: renders → RNTL; doesn't → plain Jest.
3. Add or extend `renderWithProviders` and the module fakes the unit needs.
4. Write behaviour-named, awaited tests; one per behaviour.
5. On a v13 project asked to move to 14, run the two codemods and read the diff.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Every `render` / `fireEvent` / `act` / `renderHook` in the diff is preceded by `await`.
- `npx jest` is green, with no "not wrapped in act" warnings and no open-handle warning.
- Break the implementation (flip a branch) → exactly the test for that behaviour fails.
- No test imports `vitest`, `vi`, or touches the network.

## Handoffs

- Device journeys, gestures, permission dialogs → `qa-mobile-typescript` (peer)
- Ids to query → [`test-ids`](../test-ids/SKILL.md) · roles and labels → [`accessibility`](../accessibility/SKILL.md)
- States under test → [`error-handling`](../error-handling/SKILL.md) · client under test → [`networking`](../networking/SKILL.md)
- RNTL / SDK upgrade → [`migration`](../migration/SKILL.md)
