---
paths:
  - "**/{uitests,ui-tests,mobiletests,mobile-tests,desktop-tests,e2e,e2e-tests}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/{pages,pageobjects,screens,windows,components,flows}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/{*Page,*Screen,*Window,*Dialog,DesktopDriverFactory}.java"
  - "**/src/main/java/**/windows/**/*.java"
  - "**/pom/**/*.java"
---

<!-- qa-java rules v2 (2026-11-17): page, component and flow objects. Installed by /qa-java:rules; fit the paths above to the project. -->

# Java page, component and flow objects

Severity tags as in the core rules; the codebase wins. A screen or window is a page.

- Four kinds: a page per route, screen or window; a region component (form, card, row) when it repeats or is on a second page; a control component (date picker, dropdown, combobox, data grid and row, pagination, modal, toast, tabs, file upload); a `<Name>Flow` when setup crosses pages. *major*
- A control is extracted at first use if it comes from a design system or UI library or needs over one driver call, never by caller count. The page exposes it as intent; it sits in `components.controls`. *major*
- A component takes its root (`Locator`, element or re-resolved row key) and builds children from it. Its methods are intent with domain-typed arguments; no URL, assertion or page knowledge. *major*
- Two markups are two classes (`Dropdown` for `<select>`, `Combobox` for a listbox), never one that branches. `DataGrid.row(key)` returns a `GridRow` picked by content, never index: cells by column, row actions. *major*
- A component never extends the page base class. A flow takes its pages in the constructor: instance methods, no static flow, assertion or other state. *major*
- A locator an action uses is private; Playwright may expose one only as a described assertion target. Selenium, Appium and desktop expose no element: queries return text, booleans or counts. BDD steps: `qa-java-bdd.md`. *major*
- A method is one user action: no boolean or enum parameter picking behaviour, no "if visible", no `switch` on role, platform or state. A loop only maps a query or repeats one action over its input. *major*
- Names state the action (`signIn`), never the outcome (`successfulLogin`). *minor*
- Navigation returns the next page; the page owns its URL; its only assertion is a landmark (`expectLoaded()`); no business logic or API call. *major*
- No god page or locator file; no base page until three pages share behaviour. *major*
