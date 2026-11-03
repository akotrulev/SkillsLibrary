---
paths:
  - "**/*.{test,spec}.{tsx,jsx}"
  - "**/__tests__/**/*.{tsx,jsx}"
---

<!-- fe-react rules v1 (2026-11-03): component and logic tests. Installed by /fe-react:rules; add this app's *.test.ts paths above, scoped to the web app. -->

# React component and logic test standards

Severity tags as in the core React rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Vitest + React Testing Library for what renders; plain Vitest on the function for what does not. Never `render()` to test a formatter, schema or store. *major*
- Query by role or label first, `getByTestId` last; never by CSS class, tag or `container.querySelector`. *major*
- Interactions go through `userEvent.setup()` and are awaited; `fireEvent` only for events a user cannot cause. *major*
- Assert with `jest-dom` matchers; no snapshot of a markup-only component. *minor*
- One behaviour per test, named for it; no `if` / `for` driving assertions, use `it.each`. *major*
- Wait with `findBy*` / `waitFor`, never a timer or sleep. *major*
- Fakes over mock-everything: mock at the module boundary, MSW for the network, mocks reset between tests. *major*
- A Zod error is asserted on `issues[].path` / `code`, never the message. *major*
- Never render an async Server Component: extract and test its fetch; the page is an E2E test. Real navigation is not faked by mocking `next/navigation`. *major*
- Assert through the DOM, not `result.current` of a rendered component; do not test React, the form library or the component library. *minor*
- New code ships with tests covering at least 80% of the branches it wrote; only an asserting test counts. *major*
