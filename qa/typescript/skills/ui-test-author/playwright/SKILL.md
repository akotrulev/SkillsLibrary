---
name: ui-tests-playwright
description: Use when the user asks to scaffold Playwright UI tests in TypeScript — specs, page objects, fixtures, playwright.config.ts, auth setup, locator scoping with within(), web-first assertions, or device and mobile-web emulation. Triggers "write a Playwright test for X in TypeScript", "add a Playwright page object for screen Y", "set up playwright.config.ts". Do NOT use for API tests on the Playwright runner (`qa-typescript:api-tests-playwright`) or reviewing specs (`qa-typescript:ui-tests-review`).
---

# QA — Playwright Test & Page Object Generator (TypeScript)

Scaffolds `@playwright/test` specs, page objects and fixtures in strict TypeScript. Page objects reach
tests as **fixtures**, locators climb **one ladder** with `data-testid` first, and every check is a
**web-first assertion**. The code lives in `assets/`; the mechanics live in `references/`.

## Versions

These are the only Playwright pins in this skill. Every other file links here.

| Artifact | Version | Note |
|---|---|---|
| `@playwright/test` | **1.64.0** | Node ≥ 20 (1.62); target Node 24, 22 maintenance |
| Docker image | `mcr.microsoft.com/playwright:v1.64.0-noble` | The tag always equals the package version |
| `allure-playwright`, `allure-js-commons` | 3.13.0 | Needs `@playwright/test` ≥ 1.62 |
| `@axe-core/playwright` | 4.13.0 | Owned by `accessibility-testing` |
| `playwright-bdd` | 9.2.1 | Owned by the BDD skills |

**Version lane.** Detect the project's `@playwright/test` version first and keep it — never up-level a
project as a side effect. A 1.64-only API has a down-level form: `child.within(parent)` →
`parent.locator(child)`; `TestProject.default`, `--shuffle` and `describe.configure({ lock })` have none.
Each reference tags an API with the version it shipped in.

## Stack and layout

- Node 24 + TypeScript (`strict: true`), Playwright Test runner, `eslint-plugin-playwright`
  (`flat/recommended`), Allure through `allure-playwright` where the project uses Allure.

```
e2e/
├── playwright.config.ts
├── tests/
│   ├── auth.setup.ts
│   ├── fixtures.ts
│   ├── pages/          LoginPage.ts, HomePage.ts, components shared by several pages
│   └── specs/          login.spec.ts — one spec file per feature
└── playwright/.auth/   signed-in state, git-ignored
```

The assets are flat so they compile as one folder; spread over this layout, only their relative imports
change. The config leaves `testDir` at its default, so it finds the specs either way.

## When to use

- A new `*.spec.ts`, page object, component object or fixture.
- A new or rewritten `playwright.config.ts`, setup project or signed-in state.
- Scoping or fixing locators, replacing one-shot reads with web-first assertions.
- Running the suite per device, viewport, colour scheme, locale or time.

## When NOT to use

- Native mobile apps → `qa/typescript/skills/ui-test-author/appium`
- Selenium WebDriverJS → `qa/typescript/skills/ui-test-author/selenium`
- Reviewing Playwright code → `qa/typescript/skills/ui-test-author/review`
- Designing the page-object hierarchy → `qa/typescript/skills/page-object-design`
- Extracting page objects and test ids from a live URL → `qa/typescript/skills/page-objects-from-url`
- Screenshots, video, traces and HAR beyond the config defaults → `qa/typescript/skills/evidence-capture`
- Visual regression, accessibility scans, network mocking → `visual-regression`, `accessibility-testing`,
  `network-mocking`

## Inputs needed

1. **Feature or page** under test (`Login`, `CheckoutCart`).
2. **User journey** — the steps and the one user-visible outcome to assert.
3. **Locators** — the test id for each element, or the fallback rung and a `missing-testids.md` row.
4. **Auth** — signed out, or signed in as which role.
5. **Test data** — seeded through the API in a fixture, or a builder.
6. **Devices and media** — which projects the journey runs on.

## What ships with this skill

| File | Holds |
|---|---|
| [`references/locators.md`](references/locators.md) | The ladder, `getBy*`, `filter` / `and` / `or`, chaining from a component root, `within()` and its neighbours, `visible()`, frames, strictness and positional picks, `describe()`, `addLocatorHandler`, the test-id attribute, agent-facing locators |
| [`references/assertions.md`](references/assertions.md) | The web-first set (accessible name, description and error, role, classes, value, URL forms, aria snapshots), one expected condition, the one-shot-read ban, `expect.poll` / `toPass` / `expect.soft`, failure messages |
| [`references/config-and-fixtures.md`](references/config-and-fixtures.md) | The canonical config setting by setting, fixture kinds, the setup project, `webServer`, `TestProject.default`, retries and locks, tags, the CLI, the 1.64 breaking changes, Test Agents |
| [`references/emulation-and-mobile-web.md`](references/emulation-and-mobile-web.md) | Device projects, touch, `screen`, viewport, media features, locale and geolocation, `page.clock`, offline, and why emulation is not a device |
| [`assets/playwright.config.ts`](assets/playwright.config.ts) | The canonical config |
| [`assets/fixtures.ts`](assets/fixtures.ts) | Page-object fixtures, `testUser`, and `seededUser` (API-seeded, deleted in teardown) |
| [`assets/auth.setup.ts`](assets/auth.setup.ts) | The setup project's sign-in, saving the storage state |
| [`assets/LoginPage.ts`](assets/LoginPage.ts) | A page with intent methods and a `SignInForm` component; the form error scoped with `within()` |
| [`assets/HomePage.ts`](assets/HomePage.ts) | The landing page the journeys assert on |
| [`assets/login.spec.ts`](assets/login.spec.ts) | Specs with `Should_X_When_Y` names and `{ tag }` |

Start from the assets: copy them, rename, and keep their shape.

## Rules

### Locators

1. **The ladder:** `getByTestId` → `getByRole` → `getByLabel` → `getByPlaceholder` → `getByText` →
   `getByAltText` / `getByTitle` → CSS. The first rung the element supports wins.
2. **Test ids are PascalCase dot-separated and static** — `Login.Submit`, `OrderRow`, `OrderRow.Title` —
   the format `fe-react` and `fe-blazor` generate. A row is picked by its content, never by an id that
   embeds a key, an index or a state.
3. **A fallback carries no marker in the code.** Record it in `missing-testids.md` (page, element,
   suggested id, fallback in use). The report is the contract; no `TODO`, no comment on the locator.
4. **Scope instead of picking.** A locator that matches many is narrowed by its component root,
   `within()`, or `filter({ has, hasText })`. `nth()` / `first()` only where order is the behaviour, and
   then the field name says so (`newestNotification`).
5. `visible()` (1.63) instead of `:visible`; `frameLocator` / `contentFrame()` for iframes;
   `addLocatorHandler` for overlays that may appear; `describe()` on composed locators.
6. **Never assert on an `or()` locator** — it passes on either state.

### Page objects

- Locators are `readonly Locator` fields built in the constructor, never functions that re-query.
- A page takes `(page: Page)`. A **component** (a region reused across pages — a form, a row, a menu)
  takes its root `Locator` and builds its children from it, as `SignInForm` does.
- Methods name user intent (`signIn`, `addToCart`), never the widget (`clickButton`). They are `async`
  and return `Promise<void>`; an action that always lands on another page may return that page object.
- The page owns its URL in `goto()`. Specs never call `page.goto`, `page.locator` or any other raw
  `page.` method.
- **No assertions in page objects.** They expose locators; tests assert. An optional `expectLoaded()`
  that asserts one landmark is the only exception.
- No shared base class until three pages share real behaviour (`page-object-design`).

### Tests

- **Names are `Should_X_When_Y`** (`Should_ShowInvalidCredentialsError_When_PasswordIsWrong`), grouped by
  one `test.describe` per feature.
- **Tags go in the details object:** `test('Should_…', { tag: '@smoke' }, …)` or on the `describe`;
  never in the title.
- One logical behaviour per test; every test asserts. Multiple `expect` calls are fine when they check one
  behaviour.
- **Web-first assertions only** (`references/assertions.md`). No one-shot read compared later
  (`expect(await loc.textContent())…`), no boolean dance (`expect(res.ok()).toBeTruthy()`).
- **One expected condition per assertion — never an `OR`**, and a regex alternation is an `OR`. Split the
  outcomes, or generate one test per row.
- **Failures name the subject:** ``await expect(banner, `success banner for order ${orderId}`).toHaveText('Saved')``.
- **Data-driven tests generate one `test()` per row** from a case array outside the body. No `if` or
  `for` inside a test drives assertions.
- **No `try` / `catch` / `finally` in a test.** An expected rejection is `await expect(...).rejects`;
  cleanup is fixture teardown.
- **Every promise is awaited** — actions, assertions, Allure calls.
- Tests are independent: no `test.describe.serial`, no shared mutable state. One long journey is one test
  with `test.step` labels.
- API responses in fixtures assert the exact status with the body: `expect(res.status(), await res.text()).toBe(201)`.
- No hardcoded credentials, URLs or hostnames — `BASE_URL`, `E2E_USER`, `E2E_PASSWORD`.
- No `console.log`; use `test.step` and the trace.

### Waiting

- No `page.waitForTimeout`. Wait on a web-first assertion, `expect.poll` or `toPass`, never a sleep.
- No `{ waitUntil: 'networkidle' }`. Navigate, then assert a landmark.
- No `locator.waitFor()` before an action that already auto-waits.
- No `{ force: true }`; fix the flow (close the overlay with `addLocatorHandler`, scroll, wait for the
  state).
- No `waitForNavigation` (deprecated); `waitForURL` or `toHaveURL`.
- `waitForResponse`: start the promise without `await`, perform the action, then `await` the promise.
- No hand-rolled retry loops; `toPass({ timeout })` with short inner timeouts.

### Auth and data

- Sign in **once per role** in a setup project (`assets/auth.setup.ts`) and reuse the storage state
  through `dependencies` — never sign in inside every test. A signed-out spec clears the state with
  `test.use({ storageState: { cookies: [], origins: [] } })`.
- Records a test needs are created through the API in a **fixture**, with a unique value per test, and
  deleted in its teardown (`seededUser`).
- Builders for any record with four or more fields (`qa/typescript/skills/test-data-builder`).

### Config

The canonical config is `assets/playwright.config.ts`, explained in `references/config-and-fixtures.md`:
`retries: 0` (`ci-conventions`), `forbidOnly` on CI, `fullyParallel`, `html` locally and `blob` + `junit` +
`allure-playwright` on CI, `baseURL` from `BASE_URL`, `testIdAttribute`, the failure-evidence defaults,
`updateSnapshots: 'none'` on CI and `'missing'` locally, and a setup project. Extend that file; never
start a second one.

## Generation steps

1. Detect the installed `@playwright/test` version and the project layout; match them.
2. Confirm the feature, scenarios, locators, auth, data and devices with the user.
3. For each screen, write or extend `tests/pages/<Name>Page.ts` from `assets/LoginPage.ts`: one
   `readonly Locator` per element on the highest ladder rung, components for reused regions, `goto()`,
   intent methods. Add a `missing-testids.md` row for every fallback.
4. Register each page object, and any seeded record, as a fixture in `tests/fixtures.ts`.
5. Write `tests/specs/<feature>.spec.ts` from `assets/login.spec.ts`: one `test()` per scenario with a
   `Should_X_When_Y` name, page objects from fixtures, `{ tag }`, `test.step` for long journeys.
6. For signed-in flows, make sure the setup project exists and the spec's project depends on it.
7. Run `npx playwright test` (0 failures) and check new locators in `npx playwright test --ui` before
   committing. In a `Gate: none` plan task, run neither; report the files as "written, not run".

## Handoffs

- Page-object hierarchy → `qa/typescript/skills/page-object-design`
- Page objects and test ids from a live URL → `qa/typescript/skills/page-objects-from-url`
- Reviewing Playwright tests → `qa/typescript/skills/ui-test-author/review`
- Screenshots, video, screencast, trace, HAR → `qa/typescript/skills/evidence-capture`
- Test data builders → `qa/typescript/skills/test-data-builder`
- Breakpoint matrices → `qa/typescript/skills/responsive-testing`
- Real-device mobile web → `qa/typescript/skills/device-cloud`
- Allure reporting and CI → `qa/reporting/typescript/skills/test-reports`, `qa/cicd/typescript/skills/ci-pipelines`
