---
paths:
  - "**/*.razor.js"
  - "**/wwwroot/**/*.js"
---

<!-- fe-blazor rules v1 (2026-11-03): JS modules. Installed by /fe-blazor:rules; edit to fit this project. -->

# Blazor JavaScript module standards

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- JS exists only for a browser API or library with no .NET equivalent, never for what CSS or Blazor already does. *major*
- Code is an ES module of exported functions, imported through `IJSObjectReference`; no `window.*` globals, no inline `<script>`. *major*
- Every observer, listener or timer a module starts has an exported teardown the component calls from `DisposeAsync`. *major*
- A JS animation or DOM library only touches nodes Blazor never re-renders. *major*
- Page transitions use View Transitions in CSS, never a JS shim. *minor*
- Binary data moves through stream references, never base64 through JSON. *minor*
