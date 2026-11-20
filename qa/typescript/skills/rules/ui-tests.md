---
paths:
  - "**/e2e/**/*.ts"
  - "**/tests/{ui,e2e,pages,flows}/**/*.ts"
  - "**/{ui-tests,e2e-tests}/**/*.ts"
  - "**/src/pages/web/**/*.ts"
  - "**/playwright.config.ts"
---

<!-- qa-typescript rules v2 (2026-11-17): web UI tests. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its Playwright or Selenium suite. -->

# Web UI test standards (Playwright Test; Selenium / WebdriverIO where used)

Severity tags and the codebase-wins rule as in `qa-typescript.md`. Page, component and flow objects: `page-objects.md`.

- Locator ladder: test id, role, label, placeholder, text, alt/title, CSS; XPath last. Test ids are static PascalCase dot ids (`Login.Submit`). *major; id format minor*
- A fallback gets a `missing-testids.md` row, no code marker; never invent a test id the DOM lacks. *minor*
- Scope a locator that matches many; `nth()`/`first()` only where order is the behaviour; `exact: true` on ambiguous names; `visible()` over `:visible`; no assertion on an `or()` locator. *major; minor for the last two*
- Specs get pages from fixtures, never raw `page.*`; no `BasePage` before three pages share behaviour. *major*
- Web-first assertions only: no one-shot read compared later (`textContent()`, `isVisible()`, `page.url()`) or `expect.poll` where a locator assertion works. *major*
- No `networkidle`, `force: true`, `waitForNavigation`, redundant `waitFor()` before an action or hand-rolled retry loop; `toPass` is bounded. `waitForResponse` starts before the action and is awaited after. *major*
- A server-rendered page object waits for `data-hydrated="true"` (on `<body>` or the island root) before the first interaction, never for visibility or a sleep; no signal is a `missing-testids.md` row for `fe-*`. *major*
- Server-rendered content and `Cache-Control` are asserted on raw HTML from a page-HTML client per `rendering_plan` route, never `request.get` in a spec. *major*
- Overlays use `addLocatorHandler`, never `if (await x.isVisible())`. *major*
- Sign in once per role in a setup project; a fixture creates records through the API and deletes them in teardown. *major*
- Tags go in the details object (`{ tag: '@smoke' }`), not the title. *nit*
- One `playwright.config.ts`: `forbidOnly` on CI, `baseURL` from env, trace and video `retain-on-failure`; HAR via `contextOptions`. *minor*
- Selenium/WebdriverIO: the driver comes from the factory, finds live in page objects, async API only, no `browser.execute` click. *major; blocker: sync API*
