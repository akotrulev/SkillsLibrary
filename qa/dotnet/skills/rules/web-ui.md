---
paths:
  - "**/*{UiTests,E2ETests}/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): web UI. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its browser suites. -->

# .NET web UI test standards (Playwright, Selenium)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Every class derives from one `BaseTest`; `Playwright.CreateAsync()` only in `AuthSetup`. A role, device or locale amends `base.ContextOptions()`, never returns `new()`. *blocker*
- `BaseURL` comes from `BASE_URL`; the page owns its URL in `GoToAsync()`. *blocker*
- `ParallelScope.Self`, once on `BaseTest`; never `All`, `Children` or `Fixtures` with Playwright. *blocker*
- Sign in once per role in `AuthSetup`, in the tests' root namespace, and reuse its storage state. *major*
- Failure evidence comes only from `BaseTest`'s `[TearDown]`. *major*
- Locator ladder: test id, role, label, placeholder, text, alt or title, CSS. Test ids are static and PascalCase dot-separated (`Login.Submit`); a fallback is a `missing-testids.md` row, not a code marker. *major*
- Narrow by scope or `Filter`, not `First` or `Nth()` unless order is the behaviour; never assert on an `Or()` locator. *major*
- Web-first assertions with `Describe()`; no one-shot read compared later (`IsVisibleAsync()`, `TextContentAsync()`). *major*
- `ToHaveURLAsync` takes a `Regex`; a glob string never matches. An ambiguous `GetByText` sets `Exact = true`. *major; minor for `Exact`*
- No `Page.ClickAsync(selector)` or other page-level selector API, `WaitForNavigationAsync`, `NetworkIdle`, `Force = true`, or `WaitForAsync()` before an action; wrap a response wait with `RunAndWaitForResponseAsync`. *major*
- Records are made via `Page.APIRequest` in `[SetUp]` and deleted in `[TearDown]`, never seeded in `[OneTimeSetUp]`. *major*
- Pages are built in the class's `[SetUp]`, never as `BaseTest` properties. *minor*
- Selenium: the driver comes from the `AsyncLocal` factory, never `new ChromeDriver()`. `FindElement(By)` runs only in `BasePage`, test id first and XPath last, with no `PageFactory`. One `WebDriverWait`, no implicit wait, no JavaScript `click()`. *major*
