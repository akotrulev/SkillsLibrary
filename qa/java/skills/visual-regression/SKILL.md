---
name: visual-regression
description: Use when a Java/TestNG Playwright suite must catch unintended visual change — screenshots compared against committed baselines with an image comparator, Percy, or Applitools Eyes. Triggers "add visual regression tests", "screenshot diff this page", "update the visual baselines", "the layout broke and no functional test caught it". Do NOT use for breakpoint layout (qa-java:responsive-testing), accessibility scans (qa-java:accessibility-testing) or failure screenshots (qa-java:evidence-capture).
---

# QA — Visual Regression (Java / Playwright 1.63)

One registered skill, three tools — a project uses exactly one. Identify the project's tool (dependencies,
CI config; ask one question if it is ambiguous), then **read the matching `references/<tool>.md` end to end
before writing any code**. This file routes and holds the rules every tool shares.

**Playwright Java has no screenshot assertion.** `PageAssertions` in 1.63 holds only `hasTitle`, `hasURL`
and `matchesAriaSnapshot`; `toHaveScreenshot` belongs to the Node test runner, and the Java port
(playwright-java #1040) is open with its community PR closed unmerged. `assertThat(page).hasScreenshot()`,
`assertThat(locator).hasScreenshot()` and `HasScreenshotOptions` do not exist — never write them. The free
lane is therefore `locator.screenshot(...)` compared against a committed baseline by an image library, and
the verdict is an AssertJ assertion on that library's result.

## Versions

The Playwright pin and the Docker image are the **Versions** table of
`qa/java/skills/ui-test-author/playwright/SKILL.md`; the image tag always equals the installed
`com.microsoft.playwright:playwright` version. This skill pins only its tools, each checked on 2026-10-11:

| Artifact | Version | Used by |
|---|---|---|
| `com.github.romankh3:image-comparison` | 4.4.0 | `references/playwright-snapshots.md` — a recommendation (plan D9), not a Playwright fact |
| `io.percy:percy-playwright-java` + npm `@percy/cli` | 1.2.1 + 1.32.11 | `references/percy.md` |
| `com.applitools:eyes-playwright-java5` | 5.86.9 | `references/applitools.md` |

Exact versions only — never a Maven `+` range or a Gradle `latest.release`.

## Tools in this family

| Read | Use when |
|---|---|
| `references/playwright-snapshots.md` | Screenshot plus comparator — free, baselines committed in the repo, start here |
| `references/percy.md` | Hosted pixel diff with a team review workflow; baselines live in Percy |
| `references/applitools.md` | Visual AI (Eyes) — match levels and the Ultrafast Grid browser/device matrix |

## Decision matrix — pick the tool

| Need | Use | Why |
|---|---|---|
| Free, baselines in your repo, you own the comparator and the pinned-image discipline | `references/playwright-snapshots.md` | No SaaS, no per-snapshot cost |
| Hosted baselines, a human review UI, server-side **pixel** diff | `references/percy.md` | Removes the platform-rendering problem; review workflow |
| **Visual AI** with **match levels** for dynamic content and a real cross-browser/device grid | `references/applitools.md` | Layout-level matching; most expensive |

**Graduation path:** start with screenshot plus comparator; move to Percy when in-repo baselines and the
pinned image become the bottleneck and the team wants a review workflow; move to Applitools when pixel
diffs across many browsers stay noisy, or a page whose *content* changes must keep its *structure*.

## Shared rules (every tool)

- **Every sample extends `com.example.uitests.support.BaseTest`.** It owns Playwright, the browser, the
  context, the page and the failure evidence (screenshot, trace and video on failure). A visual class
  changes the context only by overriding `contextOptions()` — viewport, locale, time zone,
  `setReducedMotion(ReducedMotion.REDUCE)` — and never adds its own `Playwright.create()`, browser or
  failure hook (`ui-test-author/playwright/references/lifecycle.md` §3).
- **Stabilize before the capture.** Data loaded — the page object returns once its ready signal is
  visible. **Time frozen** — `page.clock().setFixedTime(...)` in the class's own `@BeforeMethod`, before the
  page object navigates (`ui-test-author/playwright/references/emulation-and-mobile-web.md` §4, §6).
  Dynamic regions masked or hidden. No `Thread.sleep`, no `waitForTimeout`.
- **Reach the state through page objects.** The test calls page-object intent methods and the visual
  helper; it never calls `page` itself.
- **Visual tests run in the nightly lane**, never on every PR (`qa/cicd/ci-conventions`): they carry
  `groups = "visual"`, the gate `test` task excludes that group, and a `visualTest` Gradle task runs it on
  the schedule.
- **Baselines are reviewed, never regenerated in CI.** Comparator: baselines are written in the pinned
  image by a person and reviewed in the PR diff. Hosted: a person approves the diff in the vendor's UI.
- **Deliberate captures follow `qa/java/skills/evidence-capture`:** the class's own `@BeforeMethod` /
  `@AfterMethod(alwaysRun = true)`, files in `build/playwright-artifacts/<Class>.<method>.<kind>.<ext>`,
  attached with `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`
  (allure-java 3.0), and no `try`/`catch`/`finally` in a test or a hook body.
- **Non-locator results are AssertJ with `.as(...)`** — the comparator's state, with its difference as the
  description.
- **A hosted-tool test has no assertion.** The vendor's review is the verdict. TestNG records that
  exception in the test itself: `@Test(description = "No assertion: …")`, so a reader never mistakes it for a
  forgotten assertion.

## Handoffs

- `BaseTest`, page objects and the build → `qa/java/skills/ui-test-author/playwright`
- Aria snapshots and the other web-first assertions → its `references/assertions.md`
- Failure evidence and reading a trace → `qa/java/skills/evidence-capture`
- Allure wiring → `qa/reporting/java/skills/test-reports`
- The nightly job and artifact upload → `qa/cicd/java/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- TypeScript and .NET → `qa-typescript:visual-regression` (the runner's `toHaveScreenshot`),
  `qa-dotnet:visual-regression` (screenshot plus a comparer, as here)
