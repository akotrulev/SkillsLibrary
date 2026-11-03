---
paths:
  - "**/*.razor"
---

<!-- fe-blazor rules v1 (2026-11-03): data-driven UI. Installed by /fe-blazor:rules; edit to fit this project. -->

# Blazor data-driven UI standards

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- No raw enum int, bare GUID or `.ToString()` fallthrough shown to a user: enums are humanized by one helper derived from the enum, in every render path. *minor*
- One format per data type from shared helpers, flowing from `CurrentCulture`; timezones labelled. *minor*
- Every list has a deterministic server-side default sort with a unique tiebreaker, and pages on the server. *minor*
- An action the backend's state would reject is disabled with a reason, never shown then refused. *major*
- A destructive action confirms by naming the object, with a verb-labelled, danger-styled button. *major*
- Bulk selection is scoped to the filtered page and shows the selected count. *minor*
- One name per concept and one verb per operation across pages; no dead or duplicate routes. *minor*
- Navigation marks the current location by more than colour; top-level nav stays visible on desktop. *minor*
- A semantic `<footer>` with explicitly labelled columns. *minor*
- A modal only when the interruption is the point and the user triggered it; a long or multi-step flow is a page. *major*
- Under localization, no hardcoded UI string: `.resx` keyed to the component, `dir` from the culture. *major*
- Public pages: static SSR with prerender, a unique title and meta description, one absolute canonical, a real 404 status and `noindex` on error pages. *major*
- A defect is a class: fix it on the shared renderer and sweep its siblings. *major*
