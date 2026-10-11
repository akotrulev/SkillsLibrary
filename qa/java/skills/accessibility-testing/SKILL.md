---
name: accessibility-testing
description: Use when a Java 21 / TestNG Playwright suite must scan for accessibility violations — axe-core inside UI flows, or Lighthouse scores for public pages. Triggers "add a11y tests", "scan for WCAG 2.2 violations", "fail CI on accessibility regressions", "set an accessibility budget". Do NOT use for the app's own accessibility implementation (the fe-* accessibility skill), pixel diffs (qa-java:visual-regression) or breakpoint layout (qa-java:responsive-testing).
---

# QA — Accessibility Testing (Java / Playwright 1.63)

One registered skill, two tools; many projects run both. Identify which the project needs, then **read the
matching `references/<tool>.md` end to end before writing any code**. This file routes and holds the rules
both share.

The Playwright pin is in the **Versions** table of `qa/java/skills/ui-test-author/playwright/SKILL.md`, which
lists `com.deque.html.axe-core:playwright` **4.13.0** as owned here — exact, never `4.+`.

## Tools in this family

| Read | Use when |
|---|---|
| `references/axe-playwright.md` | axe-core scans inside the functional run — per-state WCAG 2.2 AA gating. **The gate** |
| `references/lighthouse-ci.md` | Lighthouse — page-level accessibility, best-practices and SEO scores as budgets, **public pages only** in this lane. **The trend** |

## Decision matrix

| Need | Use | Why |
|---|---|---|
| Rule-based a11y assertions **inside** the Playwright run, gated on `getViolations()` | `references/axe-playwright.md` | Free, deterministic, scoped to a component, fails in the same job |
| A full-page audit with a numeric **score** threshold | `references/lighthouse-ci.md` | A separate Lighthouse pass; coarser, not assertion-level |
| The exact rule, selector and fix for a failing component | `references/axe-playwright.md` | Each `Rule`'s nodes name them |
| One number to trend across whole public pages | `references/lighthouse-ci.md` | A score is a trend metric |
| A score for a **signed-in** page | `references/axe-playwright.md` here; a Lighthouse audit of it needs the TypeScript lane | Lighthouse audits in its own tab, outside the test's signed-in context |

## The native assertions come first

Before a scan, assert what the feature promises with Playwright's own web-first assertions —
`hasAccessibleName`, `hasAccessibleDescription`, `hasAccessibleErrorMessage` [1.50], `hasRole` [1.44], and
`matchesAriaSnapshot` for a region's roles, names and states. They state the *expected* name or role; axe
finds *rule* violations nobody wrote a test for. The matchers and the aria-snapshot grammar are in
`qa/java/skills/ui-test-author/playwright/references/assertions.md` §1–§2; this skill does not repeat them.

## Shared rules (both tools)

- The conformance target is **WCAG 2.2 AA**: axe tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`,
  set once in a shared helper.
- **Every sample extends `com.example.uitests.support.BaseTest`**, which owns Playwright, the browser, the
  context, the page and the failure evidence. A class changes the launch only through `launchOptions()` and
  the context only through `contextOptions()`; it never adds its own `Playwright.create()` or failure hook.
- Scan per state, not per page — open menus, dialogs and validation errors are where violations hide.
- Gate on new violations; known debt sits in a ticketed allow-list that only shrinks.
- Scans ride on page objects and one helper built in the class's own `@BeforeMethod`; a test never builds an
  `AxeBuilder` or calls `page`.
- Evidence is an attachment, never a `println`: `Allure.attachment(name, type, stream,
  AttachmentOptions.withFileExtension(ext))` (allure-java 3.0), made before the assertion runs.
- Results that are not locators — a violation list, a score — are asserted with AssertJ and `.as(...)`.
- Automation is the floor (roughly a third of WCAG). Keyboard, focus order and screen-reader behaviour still
  need manual testing (`qa-<stack>:exploratory-charter-writer`).

## Handoffs

- `BaseTest`, page objects, the build → `qa/java/skills/ui-test-author/playwright`
- Accessible-name, role and aria-snapshot assertions → its `references/assertions.md`
- Failure evidence and traces → `qa/java/skills/evidence-capture`
- The CI job and artifact upload → `qa/cicd/java/skills/ci-pipelines`
- TypeScript and .NET → `qa-typescript:accessibility-testing`, `qa-dotnet:accessibility-testing`
