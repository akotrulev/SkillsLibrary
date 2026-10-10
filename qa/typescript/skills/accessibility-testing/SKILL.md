---
name: qa-accessibility-testing-typescript
description: Use when a Playwright Test (TypeScript) suite must scan for accessibility violations — axe-core inside UI flows, or Lighthouse CI scores. Triggers "add a11y tests", "scan for WCAG 2.2 violations", "fail CI on accessibility regressions", "set an accessibility budget". Do NOT use for the app's own accessibility implementation (the fe-* accessibility skill), pixel diffs (qa-visual-regression-typescript) or breakpoint layout (qa-responsive-testing-typescript).
---

# QA — Accessibility Testing (TypeScript / Playwright 1.64)

One registered skill, two tools; many projects run both. Identify which the project needs, then **read the
matching `references/<tool>.md` end to end before writing any code**. This file routes and holds the rules
both share.

This skill pins nothing; `@axe-core/playwright` and `@playwright/test` are in the **Versions** table of
`qa/typescript/skills/ui-test-author/playwright/SKILL.md`.

## Tools in this family

| Read | Use when |
|---|---|
| `references/axe-playwright.md` | axe-core scans inside the functional run — per-state WCAG 2.2 AA gating. **The gate** |
| `references/lighthouse-ci.md` | Lighthouse CI — page-level accessibility, best-practices, SEO and performance scores as budgets. **The trend** |

## Decision matrix

| Need | Use | Why |
|---|---|---|
| Rule-based a11y assertions **inside** the Playwright run, gated on `violations` | `references/axe-playwright.md` | Free, deterministic, scoped to a component, fails in the same job |
| A full-page audit with a numeric **score** threshold | `references/lighthouse-ci.md` | A separate Lighthouse pass; coarser, not assertion-level |
| The exact rule, selector and fix for a failing component | `references/axe-playwright.md` | `violations[].nodes[]` names them |
| One number to trend across whole pages | `references/lighthouse-ci.md` | A score is a trend metric |

## The native assertions come first

Before a scan, assert what the feature promises with Playwright's own web-first assertions —
`toHaveAccessibleName`, `toHaveAccessibleDescription`, `toHaveAccessibleErrorMessage` [1.50], `toHaveRole`,
and `toMatchAriaSnapshot` for a region's roles, names and states. They state the *expected* name or role;
axe finds *rule* violations nobody wrote a test for. The matchers and the aria-snapshot grammar are in
`qa/typescript/skills/ui-test-author/playwright/references/assertions.md` §1–§2; this skill does not repeat
them. `page.accessibility` was removed in 1.57 — never teach it.

## Shared rules (both tools)

- The conformance target is **WCAG 2.2 AA**: axe tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`,
  set once in a shared fixture.
- Scan per state, not per page — open menus, dialogs and validation errors are where violations hide.
- Gate on new violations; known debt sits in a ticketed allow-list that only shrinks.
- Scans and audits ride on fixtures and page objects; a spec never builds a scanner or calls `page`.
- Evidence is attached with an awaited `testInfo.attach`, which reaches the HTML report and Allure; an
  Allure-only call uses `import * as allure from 'allure-js-commons'` and is awaited.
- Automation is the floor (roughly a third of WCAG). Keyboard, focus order and screen-reader behaviour still
  need manual testing (`qa-exploratory-charter-writer`).

## Handoffs

- Page objects, fixtures, the canonical config → `qa/typescript/skills/ui-test-author/playwright`
- Accessible-name, role and aria-snapshot assertions → its `references/assertions.md`
- Failure evidence and traces → `qa/typescript/skills/evidence-capture`
- The CI job and artifact upload → `qa/cicd/typescript/skills/ci-pipelines`
- Java and .NET → `qa-accessibility-testing-java`, `qa-accessibility-testing-dotnet`
