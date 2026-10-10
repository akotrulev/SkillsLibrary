---
name: qa-visual-regression-typescript
description: Use when a Playwright Test (TypeScript) suite must catch unintended visual change — built-in toHaveScreenshot baselines, Percy, or Applitools Eyes. Triggers "add visual regression tests", "screenshot diff this page", "update the visual baselines", "the layout broke and no functional test caught it". Do NOT use for breakpoint layout (qa-responsive-testing-typescript), accessibility scans (qa-accessibility-testing-typescript) or failure screenshots (qa-evidence-capture-typescript).
---

# QA — Visual Regression (TypeScript / Playwright 1.64)

One registered skill, three tools — a project uses exactly one. Identify the project's tool (dependencies,
CI config; ask one question if it is ambiguous), then **read the matching `references/<tool>.md` end to end
before writing any code**. This file routes and holds the rules every tool shares.

This skill pins nothing. The Playwright version and the Docker image are the **Versions** table of
`qa/typescript/skills/ui-test-author/playwright/SKILL.md`; the image tag always equals the installed
`@playwright/test` version.

## Tools in this family

| Read | Use when |
|---|---|
| `references/playwright-snapshots.md` | Built-in `toHaveScreenshot` — free, baselines committed in the repo, start here |
| `references/percy.md` | Hosted pixel diff with a team review workflow; baselines live in Percy |
| `references/applitools.md` | Visual AI (Eyes) — match levels and the Ultrafast Grid browser/device matrix |

## Decision matrix — pick the tool

| Need | Use | Why |
|---|---|---|
| Free, baselines in your repo, you own the pinned-image discipline | `references/playwright-snapshots.md` | No SaaS, no per-snapshot cost |
| Hosted baselines, a human review UI, server-side **pixel** diff | `references/percy.md` | Removes the platform-rendering problem; review workflow |
| **Visual AI** with **match levels** for dynamic content and a real cross-browser/device grid | `references/applitools.md` | Layout-level matching; most expensive |

**Graduation path:** start with built-in snapshots; move to Percy when in-repo baselines and the pinned
image become the bottleneck and the team wants a review workflow; move to Applitools when pixel diffs across
many browsers stay noisy, or a page whose *content* changes must keep its *structure*.

## Shared rules (every tool)

- **Stabilize before the capture.** Data loaded — the page object waits on a condition. **Time frozen** —
  an auto fixture calls `page.clock.setFixedTime(date)` before the page loads (clock API:
  `qa/typescript/skills/ui-test-author/playwright/references/emulation-and-mobile-web.md` §6). Dynamic
  regions masked or hidden. No `waitForTimeout`.
- **Reach the state through fixtures and page objects.** A spec never constructs a page object or calls
  `page` directly; the capture is the only new line in the test.
- **Visual specs run in the nightly lane**, never on every PR (`qa/cicd/ci-conventions`): a `visual`
  project with `default: false` [1.64] that the schedule runs with `--project=visual`.
- **Baselines are reviewed, never regenerated in CI.** Built-in: the canonical config sets
  `updateSnapshots: 'none'` on CI and baselines are written in the pinned image by a person. Hosted: a
  person approves the diff in the vendor's UI.
- **Failure evidence comes from the canonical config** (`trace`, `video` and `screenshot` on
  `retain-on-failure` / `only-on-failure`) and `allure-playwright` — no `afterEach` that re-attaches
  diffs. WebP baselines get no Allure diff widget (`qa/reporting/typescript/skills/test-reports`).
- **Allure calls use `import * as allure from 'allure-js-commons'` and are awaited.** Prefer
  `testInfo.attach`, which reaches both the HTML report and Allure.
- **A hosted-tool test has no `expect`.** The vendor's review is the assertion. That exception is recorded
  in the test as an annotation (`references/percy.md` shows it), so a reader never mistakes it for a
  forgotten assertion.

## Handoffs

- Page objects, fixtures and the canonical config → `qa/typescript/skills/ui-test-author/playwright`
- Aria snapshots and the other web-first assertions →
  `qa/typescript/skills/ui-test-author/playwright/references/assertions.md`
- Failure evidence and reading a trace → `qa/typescript/skills/evidence-capture`
- Allure mapping of diffs → `qa/reporting/typescript/skills/test-reports`
- The nightly job and artifact upload → `qa/cicd/typescript/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- Java and .NET → `qa-visual-regression-java`, `qa-visual-regression-dotnet` (no screenshot assertion in
  those bindings; they compare `screenshot()` output)
