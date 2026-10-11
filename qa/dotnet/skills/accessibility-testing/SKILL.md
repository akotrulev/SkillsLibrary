---
name: accessibility-testing
description: Use when a .NET/NUnit Playwright suite must scan for accessibility violations — axe-core per UI state at WCAG 2.2 AA (Deque.AxeCore.Playwright) or Lighthouse category scores. Triggers "add a11y tests", "scan for WCAG violations", "fail CI on accessibility regressions", "set an accessibility budget". Do NOT use for the app's own a11y implementation (the fe-* stack's accessibility skill), pixel diffs (qa-dotnet:visual-regression) or breakpoints (qa-dotnet:responsive-testing).
---

# QA — Accessibility Testing (.NET 10 / Playwright 1.63)

One registered skill, two tools. Identify what the project needs (an assertion gate inside the UI run, a
score to trend, or both), then **read the matching `references/<tool>.md` end to end before writing any
code**. This file routes and holds the rules every tool shares.

## Versions

The Playwright pin is the **Versions** table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md`. This
skill's tools, each checked on 2026-10-11:

| Package | Version | Used by |
|---|---|---|
| `Deque.AxeCore.Playwright` | **4.13.0**, exact (already in the writer's `Directory.Packages.props`) | `references/axe-playwright.md` |
| npm `@lhci/cli` + `lighthouse` | 0.15.1 + 13.5.0, exact dev dependencies; Node 24 | `references/lighthouse-ci.md` |

Never a floating `4.*` or a `Version=` on the `PackageReference` — central package management pins it once.

## Tools in this family

| Read | Use when |
|---|---|
| `references/axe-playwright.md` | axe-core scans inside the UI flows — per-state WCAG 2.2 AA violation gate. **The default** |
| `references/lighthouse-ci.md` | Lighthouse — whole-page category scores (accessibility, best-practices, SEO) gated and trended |

## Decision matrix — pick the tool

| Need | Use | Why |
|---|---|---|
| Rule-level assertions **inside** the functional Playwright run, failing on `Violations` | `references/axe-playwright.md` | Free, deterministic, scoped to a component, fails in the same job |
| Per-element evidence (rule id, impact, selector, help link) for a component | `references/axe-playwright.md` | Each `AxeResultItem.Nodes[]` names the failing selector |
| A whole-page **score** per category with a threshold, and a trend over time | `references/lighthouse-ci.md` | A separate pass; broader but coarser — a number, not a rule list |
| A score for a **signed-in** page | `references/lighthouse-ci.md` §4 | A persistent Chromium context the fixture owns, sharing the sign-in with Lighthouse's tab |

**Rule of thumb:** axe is the **gate** — no new violations, per component, in the existing run. Lighthouse is
the **broad audit and trend**. They are complementary; many teams run both.

## Shared rules (every tool)

- **The native assertions come first.** axe finds rule violations; it does not know what a control *should*
  be called. Assert the intended contract with `ToHaveAccessibleNameAsync`, `ToHaveAccessibleDescriptionAsync`,
  `ToHaveAccessibleErrorMessageAsync`, `ToHaveRoleAsync` and `ToMatchAriaSnapshotAsync` from
  `qa/dotnet/skills/ui-test-author/playwright/references/assertions.md` §1–§2.
- **The conformance target is WCAG 2.2 AA**, set once in a helper: `wcag2a`, `wcag2aa`, `wcag21a`,
  `wcag21aa`, `wcag22aa`.
- **Scan per state, not per page** — an open menu, a modal and a form showing errors are different DOMs.
  The page object drives the state and waits on a condition; never `Task.Delay` or `WaitForTimeoutAsync`.
- **The axe samples derive from `Example.UiTests.Support.BaseTest`** and reach pages through page objects;
  the test never calls `Page`. The Lighthouse fixture is the one exception, and its reference says why: it
  needs a Chromium it launches itself, on a debugging port, as a persistent context.
- **Gate on new violations; triage existing ones** into a ticketed allow-list that only shrinks. Disable a
  rule only for a documented false positive.
- **Evidence is attached before the assertion** — violations and incompletes on every scan, as
  `AllureApi.AddAttachment(name, type, bytes, extension)`; the Lighthouse report and log on every audit, as
  files, also through `TestContext.AddTestAttachment`.
- **No `try`/`catch`/`finally` in a test; no `if` or `Console.WriteLine` deciding what a test reports.**
- An automated scan is the **floor, not proof**: keyboard traps, focus order and screen-reader comprehension
  need manual and assistive-technology testing (`qa-<stack>:exploratory-charter-writer`).

## Handoffs

- `BaseTest`, page objects, `Directory.Packages.props` → `qa/dotnet/skills/ui-test-author/playwright`
- Accessible-name, role and aria-snapshot assertions → its `references/assertions.md`
- Failure evidence beside the scans → `qa/dotnet/skills/evidence-capture`
- The UI job and the Lighthouse step → `qa/cicd/dotnet/skills/ci-pipelines`
- TypeScript and Java → `qa-typescript:accessibility-testing`, `qa-java:accessibility-testing`
