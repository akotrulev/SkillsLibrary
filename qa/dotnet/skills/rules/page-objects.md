---
paths:
  - "**/*{UiTests,E2ETests,AppiumTests,MobileTests,DesktopTests}/**/*.cs"
---

<!-- qa-dotnet rules v2 (2026-11-17): page objects. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its UI suites. -->

# .NET page, component and flow standards

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Four kinds: a page (screen, window) per screen; a region component (form, card, row) when it repeats or reaches a second page; a control component; a `<Something>Flow` when setup crosses pages. *major*
- A control (date picker, dropdown, combobox, data grid, pagination, modal, toast, tabs, file upload) is extracted at first use when it comes from the design system or needs more than one driver call; caller count is not the test. It lives in `Components/Controls/`; the page exposes it: `checkout.DeliveryDate.SelectAsync(date)`. *major*
- A component takes its root in the constructor and builds every child from it; its public methods are intent with domain-typed arguments (a date, option text, row key, column). No URL, assertion, knowledge of its host page or page base class. *major*
- Two markups are two classes (`Dropdown` over `<select>`, `Combobox` over a custom listbox), never one with a branch. A `DataGrid`'s `Row(key)` returns a `GridRow` picked by content, never index, with cells by column and the row's actions. *major*
- A flow takes its pages in the constructor; instance methods, never static, no assertion, no state beyond its pages. *major*
- A locator or element an action uses is private. Playwright exposes a described, read-only `ILocator` only as an assertion target; Selenium, Appium and desktop expose only queries returning values. Tests never act on an exposed locator; BDD steps may (`bdd.md`). *major*
- A page, component or flow method is one user action, top to bottom: no flag or enum parameter selecting behaviour, no "if it is visible", no `switch` on role, platform or state (write two methods); a loop only maps a query's results or repeats one action over given items. *major*
- Methods name the action (`SignInAsync`), never the outcome (`SuccessfulLogin`); an action landing on another screen returns its object. *minor*
- A page asserts only its landmark; no business logic or API call; tests reach the app only through these objects. *major*
- No Playwright base page until three pages share real behaviour; Selenium, Appium and desktop keep a thin finder base. *minor*
