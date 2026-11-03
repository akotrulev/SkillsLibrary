---
paths:
  - "**/*-test.{ts,tsx}"
  - "**/*.{native,ios,android}.test.{ts,tsx}"
---

<!-- mobile-react-native rules v1 (2026-11-03): tests. Installed by /mobile-react-native:rules; widen the paths above to this project's Jest test files. -->

# React Native test standards (Jest + RNTL)

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Jest with `jest-expo` and RNTL; never Vitest, `vi.mock`, jsdom or the DOM `@testing-library/react`. *major*
- On RNTL 14 every call is awaited: `render`, `renderHook`, `rerender`, `unmount`, `fireEvent.*`, `userEvent.*`, `act`. No `UNSAFE_*`, `update`, `concurrentRoot` or `createNodeMock`. *major*
- Query by role or label before `testID`; `userEvent` for a user action, not `fireEvent`. *minor*
- Names state behaviour: `Should_<Outcome>_When_<Condition>`; one behaviour per test. *minor*
- Each assertion expects one value, never "this or that"; a parse failure is asserted on `issues[].path` and `code`, not the message. *major*
- No `try` / `catch` in a test (use `rejects.toThrow`, clean up in `afterEach`), no `if` / `for` driving assertions (use `it.each`). *major*
- Wait on a condition (`findBy*`, `waitFor`) or fake timers; never a `setTimeout` wait. *major*
- No real network, secure store or timers in a unit test; native modules faked at the boundary; fakes over mocks of your own code. *major*
- A fresh `QueryClient` per test; every test runs alone and in any order. *major*
- No whole-screen snapshot, no query by style or host type, no testing the library. *minor*
- Test data with four or more fields comes from a builder. *minor*
- Test logic, not markup: `*.test.ts` for logic that does not render. Device journeys belong to `qa-mobile-typescript`; no router mocked into a fake journey. *minor*
- New code ships with tests covering at least 80% of the branches it wrote (`jest --coverage`); only an asserting test counts. *major*
