---
paths:
  - "**/*.razor"
---

<!-- fe-blazor rules v1 (2026-11-03): markup. Installed by /fe-blazor:rules; edit to fit this project. -->

# Blazor markup standards: accessibility, links, test ids

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Semantic element first, ARIA only for the gap: no `<div @onclick>` where a `<button>` or `<a>` fits. *major*
- One `<h1>` per page with `FocusOnNavigate` kept; focus moves deliberately after a context change; a dialog traps focus and restores it. *major*
- Every icon-only button has an accessible name, fixed once on a shared renderer; state is never shown by colour or icon alone. *major*
- A custom widget follows the APG key map; no `tabindex` above 0. *major*
- One persistent polite live region for async results; `role="alert"` for errors only. *minor*
- Landmark elements (`<nav>`, `<main>`, `<footer>`), with `aria-label` on a repeated `<nav>`. *minor*
- In-app navigation is a real `<a href>` or `NavLink`, never a click handler calling `NavigateTo`; the active item carries `aria-current="page"`. *major*
- Links open in the same tab; a deliberate `target="_blank"` carries `rel="noopener"`, a visible cue and an "(opens in new tab)" label suffix. *major*
- Every page has a `<PageTitle>`. *minor*
- Every interactive element, list or grid container, and read anchor (status, total, error, empty state) carries a `data-testid`. *minor*
- Test ids are PascalCase dot-separated `Page.ElementType[.Qualifier]`, unique per screen; a collision blocks completion. *major; nit for casing*
- Row locators are a static `const` in the row component: never an id, GUID, index or state value. *major*
- Ids derive from data in scope, never a hand-kept `Dictionary<TEnum, string>`. *minor*
- `data-testid` goes inline on a library control (no wrapper component to carry it) and is never mirrored into `aria-label`. *minor*
