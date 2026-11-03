---
paths:
  - "**/e2e/**/*.ts"
  - "**/tests/{ui,e2e,pages,flows}/**/*.ts"
  - "**/{ui-tests,e2e-tests}/**/*.ts"
  - "**/src/pages/web/**/*.ts"
  - "**/playwright.config.ts"
---

<!-- qa-typescript rules v1 (2026-11-03): web UI tests. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its Playwright or Selenium suite. -->

# Web UI test standards (Playwright Test; Selenium / WebdriverIO where used)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Locator ladder: test id, role, label, placeholder, text, alt/title, CSS; XPath last. Test ids are static PascalCase dot ids (`Login.Submit`). *major; minor for the id format*
- A fallback carries no code marker; it gets a `missing-testids.md` row. Never invent a test id the DOM lacks. *minor*
- Scope a locator that matches many; `nth()`/`first()` only where order is the behaviour; `exact: true` on ambiguous names; `visible()` over `:visible`. Never assert on an `or()` locator. *major; minor for the last two*
- Page objects hold `readonly` locator fields, name user intent, own their URL in `goto()`, and hold no assertions (an `expectLoaded()` landmark excepted) or business logic. *blocker for an assertion, else major*
- Specs get pages from fixtures and never call raw `page.*`. No `BasePage` until three pages share real behaviour. *major*
- Web-first assertions only; no one-shot read compared later (`textContent()`, `isVisible()`, `page.url()`), no `expect.poll` where a locator assertion works. *major*
- No `networkidle`, `force: true`, `waitForNavigation`, redundant `waitFor()` before an action, or hand-rolled retry loop; `toPass` is bounded. Start `waitForResponse` before the action, await it after. *major*
- Overlays use `addLocatorHandler`, not `if (await x.isVisible())`. *major*
- Sign in once per role in a setup project; records come from the API in a fixture and are deleted in its teardown. *major*
- Tags go in the details object (`{ tag: '@smoke' }`), never the title. *nit*
- One canonical `playwright.config.ts`: `retries: 0`, `forbidOnly` on CI, `baseURL` from env, trace and video `retain-on-failure`; HAR through `contextOptions`. *minor*
- Selenium/WebdriverIO: the driver comes from the factory, finds live in page objects, async API only, no `browser.execute` click. *major; blocker for the sync API*
