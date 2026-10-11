---
name: visual-regression
description: Use when a .NET/NUnit Playwright suite must catch unintended visual change — screenshots against committed baselines with an image comparer, Percy, or Applitools Eyes. Triggers "add visual regression tests", "screenshot diff this page", "update the visual baselines", "the layout broke and no functional test caught it". Do NOT use for breakpoint layout (qa-dotnet:responsive-testing), accessibility scans (qa-dotnet:accessibility-testing) or failure screenshots (qa-dotnet:evidence-capture).
---

# QA — Visual Regression (.NET 10 / Playwright 1.63)

One registered skill, three tools — a project uses exactly one. Identify the project's tool (package
references, CI config; ask one question if it is ambiguous), then **read the matching `references/<tool>.md`
end to end before writing any code**. This file routes and holds the rules every tool shares.

**Microsoft.Playwright has no screenshot assertion.** `IPageAssertions` in 1.63 holds only
`ToHaveTitleAsync`, `ToHaveURLAsync` and `ToMatchAriaSnapshotAsync`; `toHaveScreenshot` belongs to the Node
test runner, and the .NET port (playwright-dotnet #3112, #1854) is open because it needs the runner's
artifact system. There is no screenshot or snapshot assertion on `Expect(...)` in .NET, no options class
for one, no `*-snapshots/` folder that Playwright fills, and no `--update-snapshots` — never write any of
them. The free lane is therefore `Locator.ScreenshotAsync(...)` compared against a committed baseline by an
image library, and the verdict is an NUnit assertion on that library's result.

## Versions

The Playwright pin and the Docker image are the **Versions** table of
`qa/dotnet/skills/ui-test-author/playwright/SKILL.md`; the image tag always equals the installed
`Microsoft.Playwright.NUnit` version. This skill pins only its tools, each checked on 2026-10-11:

| Package | Version | Used by |
|---|---|---|
| `Codeuctivity.ImageSharpCompare` | 4.1.390 | `references/playwright-snapshots.md` — a recommendation (plan D9), not a Playwright fact |
| `PercyIO.Playwright` + npm `@percy/cli` | 1.0.4 + 1.32.11 | `references/percy.md` |
| `Eyes.Playwright` | 1.37.49 | `references/applitools.md` |

Versions live in `Directory.Packages.props` (central package management); a `PackageReference` carries no
`Version=`. `PercyIO.Playwright` and `Eyes.Playwright` are already in the writer's props asset; the comparer's
`PackageVersion` line is in `references/playwright-snapshots.md` §1. The Applitools package is
`Eyes.Playwright` — a package named after the vendor plus `.Playwright` does not exist on NuGet.

## Tools in this family

| Read | Use when |
|---|---|
| `references/playwright-snapshots.md` | Screenshot plus comparer — free, baselines committed in the repo, start here |
| `references/percy.md` | Hosted pixel diff with a team review workflow; baselines live in Percy |
| `references/applitools.md` | Visual AI (Eyes) — match levels and the Ultrafast Grid browser/device matrix |

## Decision matrix — pick the tool

| Need | Use | Why |
|---|---|---|
| Free, baselines in your repo, you own the comparer and the pinned-image discipline | `references/playwright-snapshots.md` | No SaaS, no per-snapshot cost |
| Hosted baselines, a human review UI, server-side **pixel** diff | `references/percy.md` | Removes the platform-rendering problem; review workflow |
| **Visual AI** with **match levels** for dynamic content and a real cross-browser/device grid | `references/applitools.md` | Layout-level matching; most expensive |

**Graduation path:** start with screenshot plus comparer; move to Percy when in-repo baselines and the
pinned image become the bottleneck and the team wants a review workflow; move to Applitools when pixel
diffs across many browsers stay noisy, or a page whose *content* changes must keep its *structure*.

## Shared rules (every tool)

- **Every sample derives from `Example.UiTests.Support.BaseTest`** (`ui-test-author/playwright/assets/BaseTest.cs`).
  It owns the browser, the context, the page and the failure evidence (trace, screenshot and video on
  failure). A visual class changes the context only by overriding `ContextOptions()` and amending
  `base.ContextOptions()` — viewport, time zone, `ReducedMotion.Reduce`. An override that returns `new()`
  drops `BaseURL` and the video folder, and `BaseTest`'s teardown then throws. A class never adds
  `Playwright.CreateAsync()`, a browser or its own failure hook (`ui-test-author/playwright/references/lifecycle.md` §4).
- **Stabilize before the capture.** Data loaded — the page object returns once its ready signal is
  visible. **Time frozen** — `Page.Clock.SetFixedTimeAsync(...)` in the class's own `[SetUp]`, before the page
  object navigates (`ui-test-author/playwright/references/emulation-and-mobile-web.md` §4, §6). Dynamic
  regions masked or hidden. No `Task.Delay`, no `WaitForTimeoutAsync`.
- **Reach the state through page objects.** The test calls page-object intent methods and the visual
  helper; it never calls `Page` itself. Locators carry `Describe(...)`.
- **Visual tests run in the nightly lane**, never in the PR gate (`qa/cicd/ci-conventions`): the class carries
  `[Category("visual")]`, the gate's filter excludes `TestCategory=visual`, and a scheduled job runs
  `--filter TestCategory=visual`.
- **Baselines are reviewed, never regenerated in CI.** Comparer: baselines are written in the pinned image
  by a person and reviewed in the PR diff. Hosted: a person approves the diff in the vendor's UI.
- **Kept images sit beside the failure evidence.** A comparer test writes its actual and diff PNGs to
  `Artifact(EvidenceName(), "actual.png")` / `"diff.png"` — `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{actual,diff}.png`,
  the folder CI uploads on failure — and shows them with `AllureApi.AddScreenDiff(expected, actual, diff)`
  (`qa/dotnet/skills/evidence-capture`).
- **Non-locator results are NUnit `Assert.That` with a message** that names the subject and carries the
  evidence — the difference measured, the dashboard link.
- **A hosted-tool test has no assertion.** The vendor's review is the verdict. NUnit records that exception
  on the test itself: `[Description("No assertion: …")]`, so a reader never mistakes it for a forgotten
  assertion.
- **No `try`/`catch`/`finally` in a test.** Cleanup and gates live in `[TearDown]` / `[OneTimeTearDown]`.

## Handoffs

- `BaseTest`, page objects, `Directory.Packages.props` → `qa/dotnet/skills/ui-test-author/playwright`
- Aria snapshots and the other web-first assertions → its `references/assertions.md`
- Failure evidence, `AddScreenDiff`, reading a trace → `qa/dotnet/skills/evidence-capture`
- Allure wiring → `qa/reporting/dotnet/skills/test-reports`
- The nightly job and artifact upload → `qa/cicd/dotnet/skills/ci-pipelines`, `qa/cicd/ci-conventions`
- TypeScript and Java → `qa-typescript:visual-regression` (the runner's `toHaveScreenshot`),
  `qa-java:visual-regression` (screenshot plus a comparator, as here)
