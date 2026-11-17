---
paths:
  - "**/e2e/**/*.ts"
  - "**/tests/{ui,e2e,pages,flows,mobile,desktop}/**/*.ts"
  - "**/{ui-tests,e2e-tests,mobile-tests,desktop-tests,.maestro}/**"
  - "**/test/specs/**/*.ts"
  - "**/src/pages/{web,mobile}/**/*.ts"
  - "**/src/windows/**/*.ts"
  - "**/playwright.config.ts"
  - "**/wdio*.conf.ts"
---

<!-- qa-typescript rules v2 (2026-11-17): page, component and flow objects. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its UI suites. -->

# Page, component and flow objects

Severity tags as in the core rules. The codebase wins where it consistently does otherwise. Screens and windows are pages.

- Four kinds, named for their role: a page per route or screen; a region component (form, card, row) once it repeats or reaches a second page; a control for a design-system widget (date picker, dropdown, combobox, data grid, pagination, modal, toast, tabs, file upload) at first use, whatever its callers, kept in `components/controls/`, exposed as intent (`checkout.deliveryDate.select(date)`); a flow for a sequence across pages. *major*
- A component takes its root in the constructor, builds every child from it; its methods are intent with domain-typed arguments; no URL, assertion, page knowledge or page base class. *major*
- Two markups, two classes (`Dropdown` for `<select>`, `Combobox` for a custom listbox), never one branching class. `DataGrid.row(key)` returns a `GridRow` found by content, never index, exposing cells by column and row actions. *major*
- A flow is a Playwright fixture or a `<Name>Flow` class constructed from its pages, never a free function or static class; no assertion, no state beyond its pages. *major*
- A locator or element an action uses is `private readonly`. Playwright may expose a `readonly`, described locator only as an assertion target, never to act on; WebdriverIO exposes no element, queries return text, a boolean or count. BDD: see `bdd.md`. *major*
- A page owns its URL in `goto()`; its one assertion is the landmark (`expectLoaded`, `verify*Loaded`); no business logic, no API call. *blocker for an assertion, else major*
- An object method is one user action, top to bottom: no `if`, `switch` or ternary on role, platform or state; no boolean or enum parameter picking behaviour; no "if visible" (use the overlay handler or setup). A loop only maps a query or repeats one action over its items. *major*
- Names state the action (`signIn`), never the outcome (`successfulLogin`). *minor*
