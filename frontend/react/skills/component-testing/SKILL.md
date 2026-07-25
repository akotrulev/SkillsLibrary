---
name: fe-react-component-testing
description: Use when a component or custom hook needs a dev-side test — Vitest + React Testing Library: config, role/label queries over testids, `userEvent`, async `findBy*`/`waitFor`, `vi.mock`/MSW, `renderHook`, and the limit that Vitest can't render async Server Components (extract the fetch, E2E the rest). Triggers "unit-test this component", "test my custom hook", "an update was not wrapped in act". Not for E2E journeys (the `qa-ui-typescript` peer).
---

# React — Component Testing (Vitest + React Testing Library)

Owns **dev-side component tests**: render a React component in isolation, drive it as a user would, and assert on the rendered output and behavior. This is the unit layer under the component — it runs headless in a simulated DOM (jsdom/happy-dom), with no real browser and no real backend. **Boundary:** end-to-end user journeys, real navigation, real network, and cross-page flows belong to the peer agent [`qa-ui-typescript`](../../../../qa/typescript/agents/qa-ui-typescript.md) (Playwright). If a test needs a running app and a real browser, it is not a Vitest component test.

**Guiding principle (RTL):** test components **the way users interact with them** — query by role and accessible name, drive with `userEvent`, assert on visible behavior — **not** implementation details (state internals, instance methods, class names). If a refactor that preserves behavior breaks the test, the test was coupled to implementation.

## Version applicability

React 19 idioms are primary; React 18 equivalents are tagged fallbacks (not obsolete — correct for that version). Detect the installed React major from `package.json`. The testing stack itself is version-agnostic across 18/19; only the component APIs differ.

| Concern | React 19 (primary) | React 18 (fallback) |
|---|---|---|
| Testing library | `@testing-library/react` v16+ (React 19 support) | `@testing-library/react` v14/15 |
| `act` import | from `react` | from `react-dom/test-utils` |
| Component under test | `ref` as a prop, Actions, `use()` | `forwardRef`, controlled `onSubmit` |

**Runner:** Vitest is the house default for React (Vite-native, ESM-first, `vi` mock API). Jest works too if the project already standardizes on it (`@testing-library/jest-dom` supports both) — don't fight an existing Jest setup. New projects use Vitest.

## When to use

- A component has **logic**: conditional rendering, computed/formatted display, an event handler that mutates state, validation, a derived enabled/disabled state, a reducer.
- You want to prove a component reacts correctly to prop changes, context values, an injected service/fetch result, or a hook's return.
- A **custom hook** with real logic (a reducer, a derived value, a subscription) — test it with `renderHook`.
- Regression-locking a fixed component bug at the unit level (far cheaper than an E2E).

## When NOT to use

- **Markup-only components** (a static card, a layout shell with no branching) — asserting hand-written markup is a tautology. Test *logic-bearing* components only.
- **Async Server Components** (an `async function` component that `await`s data) — **Vitest cannot render them** (React's RSC runtime isn't available in the test runner; the render throws the moment you `await`). Pull the data fetch into a plain async function and unit-test *that*; render the resulting **synchronous** presentational component with RTL; hand the assembled async page to the `qa-ui-typescript` peer (E2E). This is the official Next.js guidance.
- **End-to-end journeys / real navigation / real backend** → `qa-ui-typescript` (peer). RTL fakes nothing about routing — there is no route.
- **Pure TS logic** with no rendering (a Zod schema, a formatter, a mapper) → a plain Vitest test on the function, no RTL.
- **Authoring `data-testid`s** → [`testability`](../testability/SKILL.md). Tests here *consume* testids as a last-resort selector — prefer role/label.

## Test what has behavior — the selection matrix

| Component / unit shape | Test with Vitest+RTL? | What to assert |
|---|---|---|
| Conditional render (`{x && …}`, ternary, `switch`) | Yes | Correct branch renders per prop/state |
| Event handler mutates state | Yes | User action → state change → re-render reflects it |
| Computed / formatted display | Yes | Raw value in → humanized value out |
| Form + validation (RHF+Zod) | Yes | Invalid input → error message shown; submit callback not fired |
| Consumes a context / injected service | Yes | Provided value drives the rendered output |
| Custom hook with logic | Yes (`renderHook`) | Actions on the hook → returned value changes |
| Calls `fetch` / a client (client component) | Yes | Mocked result drives output; error path renders the error state |
| **Sync** Server Component (no `await` in body) | Yes | Renders expected markup from props |
| **Async** Server Component (`await` in body) | **No** | Extract the fetch → test the function; E2E the page |
| Static markup, no branches | No | Nothing — skip it |
| Real navigation / real HTTP / full journey | No | Belongs to `qa-ui-typescript` |

## Setup (project)

Install: `vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom` (or `happy-dom` — faster, lighter in CI). Add `@vitejs/plugin-react`.

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',        // or 'happy-dom'
    globals: true,               // describe/it/expect without imports
    setupFiles: './vitest.setup.ts',
  },
});
```

```ts
// vitest.setup.ts
import '@testing-library/jest-dom/vitest';  // toBeInTheDocument, toBeDisabled, …
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
afterEach(cleanup);                // RTL auto-cleanup if globals; explicit is safe
```

- **Next.js note:** the official Next Vitest guide wires the same config; `next/navigation` (`useRouter`, `usePathname`) must be **mocked** in tests (`vi.mock('next/navigation', …)`) — there is no router in jsdom.
- **`tsconfig`:** ensure `types` includes `vitest/globals` (or import explicitly). `strict: true` per the house rules.

## Core API

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Counter } from './Counter';

describe('Counter', () => {
  it('increments the count when the button is clicked', async () => {
    const user = userEvent.setup();          // ALWAYS setup(), then await every interaction
    render(<Counter />);

    await user.click(screen.getByRole('button', { name: /increment/i }));

    expect(screen.getByRole('status')).toHaveTextContent('1');
  });
});
```

- **Query priority (RTL):** `getByRole` (with `name`) → `getByLabelText` → `getByPlaceholderText` → `getByText` → **`getByTestId` last**. Role/label queries assert accessibility *for free*; a test that can only find an element by testid is a hint the element isn't accessible.
- **`get*` vs `query*` vs `find*`:** `getBy*` throws if absent (assert presence), `queryBy*` returns null (assert **absence** — `expect(screen.queryByText(…)).not.toBeInTheDocument()`), `findBy*` is async and retries (assert something that appears **later**).
- **Render with props / re-render:** `const { rerender } = render(<Card title="a" />); rerender(<Card title="b" />);`.
- **Providers:** wrap with the real provider, or a custom `render` helper. `render(<ThemeProvider><Widget/></ThemeProvider>)`, or `render(<Widget/>, { wrapper: AllProviders })`. For TanStack Query, wrap in a fresh `QueryClientProvider` per test (new `QueryClient`, retries off).

## Async — never sleep

Renders, effects, and data resolution are async. Assert on a **condition**, never a delay (global rule: no `waitForTimeout`/`setTimeout`).

- **`findBy*`** — the first choice for "it appears after an async step": `expect(await screen.findByRole('row')).toBeInTheDocument();`.
- **`waitFor(() => …)`** — retry an arbitrary assertion until it passes or times out. Keep the callback a pure assertion; don't put side effects in it.
- **`waitForElementToBeRemoved`** — for a spinner/loader disappearing.
- `userEvent` interactions are already async — `await` each; that flushes the effects they trigger.

## Mocking (`vi`)

```tsx
vi.mock('@/lib/orders', () => ({ fetchOrders: vi.fn() }));
import { fetchOrders } from '@/lib/orders';

beforeEach(() => vi.clearAllMocks());          // reset call history between tests

it('renders the failed state when the fetch rejects', async () => {
  vi.mocked(fetchOrders).mockRejectedValueOnce(new Error('boom'));
  render(<OrdersPanel />, { wrapper: QueryWrapper });
  expect(await screen.findByRole('alert')).toHaveTextContent(/couldn.t load/i);
});
```

- **Mock the module boundary**, not React internals. Fake the client/service/fetch the component depends on — don't reconstruct the whole app graph.
- **Network:** for anything beyond a trivial mock, prefer **MSW** (Mock Service Worker) — it intercepts at the network layer so the component's real fetch code runs. Reserve `vi.fn()` stubs for a single call.
- `vi.clearAllMocks()` in `beforeEach` (or `restoreMocks: true` in config). Reset timers with `vi.useRealTimers()` if a test faked them.

## Custom hooks

```tsx
import { renderHook, act } from '@testing-library/react';

it('toggles open state', () => {
  const { result } = renderHook(() => useDisclosure());
  expect(result.current.isOpen).toBe(false);
  act(() => result.current.open());
  expect(result.current.isOpen).toBe(true);
});
```

Wrap state-mutating calls in `act(...)`; pass a `wrapper` for hooks that read context. Test the hook's *contract* (returned values react to actions), not its internals.

## Rules

- **Query by role/label first, `getByTestId` last** — testids are the E2E contract ([`testability`](../testability/SKILL.md)); in unit tests they're a fallback when no accessible query fits.
- **`userEvent.setup()` + `await`** every interaction — never `fireEvent` for user actions (it skips the real event sequence). `fireEvent` only for events users can't do (a raw `scroll`, a synthetic `change` on a non-input).
- **Semantic assertions** via `jest-dom` matchers (`toBeInTheDocument`, `toBeDisabled`, `toHaveAccessibleName`) — never snapshot a whole component's markup.
- **One behavior per test**, `Should_X_When_Y` / `renders X when Y` naming; no `if`/`for` driving assertions — parameterize with `it.each`.
- **Fakes/stubs over mock-everything**; mock at the module boundary; MSW for network.
- **Async via `findBy*`/`waitFor`**, never a timer.
- Test **logic**, not markup: if deleting the assertion leaves a tautology, delete the test.

## Anti-patterns to avoid

- **Rendering an async Server Component** — it throws; Vitest has no RSC runtime. Extract the fetch; E2E the page.
- **Snapshot-testing a markup-only component** — locks layout churn, proves no behavior. (Pixel/visual regression is the peer `qa/typescript/skills/visual-regression`.)
- **`fireEvent.click` for user actions** — use `userEvent`; `fireEvent` bypasses focus/pointer/keyboard sequencing.
- **`waitForTimeout` / `setTimeout` to wait for a render** — use `findBy*` / `waitFor`.
- **Querying by CSS class / tag / `container.querySelector`** — couples to styling; use role/label, then testid.
- **Asserting on state via `result.current` for a rendered component** — reach through the DOM, not the instance.
- **Testing the framework / library** — that `useState` updates, that RHF validates, that MUI renders a button. Test *your* logic.
- **Re-implementing E2E in RTL** — mocking `next/navigation` and pretending it's a journey test. Hand real navigation to `qa-ui-typescript`.
- **Not resetting mocks** — leaked call history across tests → order-dependent flakiness.

## Handoffs

- `data-testid` authoring/audit → [`testability`](../testability/SKILL.md)
- End-to-end / real-browser journeys, POM → **peer** `qa-ui-typescript`
- Visual/pixel regression → **peer** `qa/typescript/skills/visual-regression`
- Component code smells / rewrites → [`reviewer`](../reviewer/SKILL.md) / [`generator`](../generator/SKILL.md)
- What a component *should* do (behavior spec) → the test-case suite from **peer** `qa-manual-test-designer`
- Async data fetch to extract & test → [`data-access`](../data-access/SKILL.md)
