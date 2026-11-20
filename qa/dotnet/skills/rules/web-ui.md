---
paths:
  - "**/*{UiTests,E2ETests}/**/*.cs"
---

<!-- qa-dotnet rules v2 (2026-11-17): web UI. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its browser suites. -->

# .NET web UI test standards (Playwright, Selenium)

Severity tags as in the core rules.

- Every class derives from one `BaseTest`; `Playwright.CreateAsync()` only in `AuthSetup`. A role, device or locale amends `base.ContextOptions()`, never returns `new()`. *blocker*
- `BaseURL` comes from `BASE_URL`; a page owns its URL in `GoToAsync()`. *blocker*
- `ParallelScope.Self` once on `BaseTest`, never `All`, `Children` or `Fixtures`. *blocker*
- Sign in once per role in `AuthSetup` (root namespace) and reuse its storage state. *major*
- Failure evidence comes only from `BaseTest`'s `[TearDown]`. *major*
- Locator ladder: test id, role, label, placeholder, text, alt or title, CSS. Test ids are static, PascalCase dot-separated (`Login.Submit`); a fallback is a `missing-testids.md` row. *major*
- Narrow by scope or `Filter`, not `First` or `Nth()` unless order is the behaviour; never assert on `Or()`. *major*
- Web-first assertions with `Describe()`; no one-shot read (`IsVisibleAsync()`, `TextContentAsync()`) compared later. *major*
- `ToHaveURLAsync` takes a `Regex`; a glob string never matches. An ambiguous `GetByText` sets `Exact = true`. *major; minor for `Exact`*
- No page-level selector API (`Page.ClickAsync(selector)`), `WaitForNavigationAsync`, `NetworkIdle`, `Force = true`, or `WaitForAsync()` before an action (the hydration wait is not one); wait for a response with `RunAndWaitForResponseAsync`. *major*
- On a server-rendered page the page object waits for `data-hydrated="true"` (on `<body>` or the island's root) before the first interaction, never visibility, a sleep or `NetworkIdle`; no signal is a `missing-testids.md` row. *major*
- Server-rendered content and `Cache-Control` are asserted on raw HTML from a `PageHtmlClient`, per `rendering_plan` route, never `APIRequest.GetAsync`. *major*
- Records are made via `Page.APIRequest` in `[SetUp]`, deleted in `[TearDown]`, never seeded in `[OneTimeSetUp]`. *major*
- Pages are built in the class's `[SetUp]`, never as `BaseTest` properties. *minor*
- Selenium: the driver comes from the `AsyncLocal` factory. `FindElement(By)` runs only in `BasePage` and a component's own root, test id first and XPath last; no `PageFactory`, implicit wait or JavaScript `click()`; one `WebDriverWait`. *major*
