# Config and fixtures — Playwright 1.64 (TypeScript)

The canonical `playwright.config.ts` is `assets/playwright.config.ts`. This file explains each setting,
the fixture model, the auth setup project, the CLI and what changed in 1.64. The version in brackets is
where an API first shipped.

## 1. The canonical config, setting by setting

| Setting | Value | Why |
|---|---|---|
| `forbidOnly` | `isCI` | A stray `test.only` fails the CI run instead of silently skipping the suite |
| `fullyParallel` | `true` | Tests inside a file run in parallel too. Tests are independent by rule, so nothing breaks |
| `retries` | `0` | Retry hides bugs (`qa/cicd/ci-conventions`). A documented network-flake hotspot may opt in per `describe` (§6) |
| `reporter` (local) | `html` | The report opens on failure with the trace, screenshot and video attached |
| `reporter` (CI) | `blob` + `junit` + `allure-playwright` | `blob` merges across shards (`npx playwright merge-reports`), `junit` feeds the CI test widget, Allure is the human report. `resultsDir: 'allure-results'` is the allure-playwright 3 option |
| `updateSnapshots` | `'none'` on CI, `'missing'` locally | CI never writes a baseline. Locally a new snapshot is written; a changed one still fails |
| `use.baseURL` | `process.env.BASE_URL` | Every stack reads the app URL from `BASE_URL`. `page.goto('/login')` and `request.post('/api/users')` resolve against it |
| `use.testIdAttribute` | `'data-testid'` | The default, stated so a `data-test` project knows where to change it (`locators.md` §10) |
| `use.trace` / `video` / `screenshot` | `retain-on-failure` / `retain-on-failure` / `{ mode: 'only-on-failure', fullPage: true }` | The failure-evidence defaults. Modes, alternatives and deliberate recordings are owned by `qa/typescript/skills/evidence-capture` |
| `projects[setup]` | `testMatch: /.*\.setup\.ts/` | Runs `auth.setup.ts` once and writes the signed-in state (§3) |
| `projects[chromium]` | `devices['Desktop Chrome']`, `storageState: authFile`, `dependencies: ['setup']` | Starts every test signed in. More browsers or devices are more projects (`emulation-and-mobile-web.md`) |

The asset leaves `testDir` at its default, the config's own folder, so the files work both copied flat and
spread over the layout in `SKILL.md`.

**Allure pairing:** the `allure-playwright` pinned in `SKILL.md` needs `@playwright/test` ≥ 1.62. A project
pinned below 1.62 pins an older `allure-playwright` too. Attach calls come from `allure-js-commons`
(`import * as allure from 'allure-js-commons'`), never the deprecated `allure` export of
`allure-playwright`, and every call is awaited.

## 2. Fixtures

A fixture is set up when a test asks for it by name and torn down after `use()` returns. Everything after
`await use(value)` is teardown, and it runs even when the test fails.

| Kind | Declared as | Use for |
|---|---|---|
| Test-scoped | `name: async ({ page }, use) => { await use(new LoginPage(page)); }` | Page objects, seeded records, anything per test |
| Worker-scoped | `name: [async ({}, use) => { ... }, { scope: 'worker' }]`, typed in the second generic of `extend<Test, Worker>` | Expensive shared setup: an API token, a database connection. Never mutable state a test changes |
| Automatic | `{ auto: true }` | Runs for every test without being named — an overlay handler, a console-error collector |
| Boxed | `{ box: true }` | Hides the fixture's own steps from the report when they are noise |
| Titled | `{ title: 'seed user' }` | A readable step name in the report |
| Option | `name: ['default', { option: true }]` | A value the config sets per project through `use` (a locale, a tenant). Overriding a non-option fixture from the config is an error [1.60] |

`assets/fixtures.ts` holds the page-object fixtures, `testUser` (credentials from `E2E_USER` /
`E2E_PASSWORD`, failing fast when unset) and `seededUser`: it creates a user through the API, asserts the
exact `201` with the body as evidence, yields it, and deletes it in teardown with an exact `204`. A
teardown that fails fails the test loudly; nothing catches it.

```typescript
export const test = base.extend<{ dismissConsent: void }>({
  dismissConsent: [
    async ({ page }, use) => {
      await page.addLocatorHandler(page.getByTestId('Consent.Banner'), async (banner) => {
        await banner.getByRole('button', { name: 'Accept' }).click();
      });
      await use();
    },
    { auto: true },
  ],
});
```

Fixtures compose: one `extend` per concern is fine, merged with `mergeTests(a, b)`.

## 3. Signed-in state: the setup project

- `auth.setup.ts` signs in once through `LoginPage`, checks the landmark, and saves
  `context.storageState({ path: authFile })`. `authFile` is exported by `fixtures.ts`, so the setup and the
  config read one constant.
- Projects that need the session list `dependencies: ['setup']` and set `use.storageState: authFile`.
  Add `playwright/.auth/` to `.gitignore`; the file holds live tokens.
- One setup test and one state file per role (`admin.json`, `member.json`), each feeding its own project.
- A spec that must start signed out sets `test.use({ storageState: { cookies: [], origins: [] } })`, as
  `assets/login.spec.ts` does for the login journeys.
- A setup project can name a cleanup project with `teardown: 'cleanup'`. Prefer a setup project over
  `globalSetup`: it shows in the report, gets fixtures and a trace.
- `storageState({ indexedDB: true })` [1.51] also saves IndexedDB, for apps that keep tokens there.

## 4. Starting the app: `webServer`

When the suite starts the app itself, add `webServer: { command, url, reuseExistingServer: !process.env.CI }`.
`wait: { stdout: /listening on (?<APP_PORT>\d+)/ }` [1.57] waits for a log line instead of polling a URL,
and each named group becomes an environment variable. Against a deployed environment there is no
`webServer`; `BASE_URL` points at it.

## 5. Projects that do not run by default

`default: false` on a project [1.64] keeps it out of a plain `npx playwright test` — a nightly WebKit or
device project. `--project=<name>` runs it, `--project="*"` runs everything, and its `dependencies` still
run.

## 6. Retries, flakes and locks

- `retries: 0`. A known network-flake hotspot opts in for its own `describe` with
  `test.describe.configure({ retries: 1 })`, and its tests carry
  `{ annotation: { type: 'issue', description: '<issue link> (<date>)' } }`.
- Flakes are found by a nightly `--repeat-each` run and the Allure history, then quarantined by
  `qa/reporting/typescript/skills/flaky-test-quarantine` — never by in-run retries, so Playwright's
  "flaky" status and `failOnFlakyTests` are not used.
- `test('…', { lock: 'user-settings' }, …)` [1.63] stops tests that share one external resource from
  running at the same time, across workers and projects. `test.describe.configure({ lock })` [1.64] does it
  for a group. Prefer a separate record per test; a lock is for the resource you cannot duplicate.

## 7. Tags

Tag with the details object, never the title: `test('Should_X_When_Y', { tag: '@smoke' }, …)` or on a
`describe`. Select with `--grep @smoke`, exclude with `--grep-invert @slow` (or `-G`, 1.61). `tag` in the
config [1.57] adds a tag to every test in the run, for example the environment name.

## 8. CLI

| Command | Does |
|---|---|
| `npx playwright test --list` | Lists tests without running them |
| `--last-failed` | Reruns only the tests that failed last time |
| `--only-changed[=<ref>]` | Runs test files changed since the ref, and files that import changed files |
| `--repeat-each=<n>` | Runs each test n times — the flake hunt |
| `--shuffle [seed]` [1.64] | Randomises order and prints the seed; pass it back to replay the order |
| `--project=<name>` / `--grep` / `-G` | Narrows the run |
| `--headed` / `--debug` / `--ui` | A visible browser; the inspector with step-through; UI mode with watch and time travel |
| `--update-snapshots[=all\|changed\|missing\|none]` | Updates snapshots (§9 for `missing`) |
| `npx playwright codegen <url>` | Records actions into locator code to start from; rewrite it against the ladder |
| `npx playwright install --with-deps chromium` | Installs the browser the version needs; on CI use the Docker image from the `SKILL.md` Versions table instead |

## 9. Breaking changes in 1.64

- **Device descriptors now apply `screen`.** `...devices['Desktop Chrome']` changes `window.screen` and
  screen media queries, not only the viewport. Opt out with `screen: undefined` in that project's `use`.
- **JSX in test files follows `tsconfig.json`** (`jsx`, `jsxFactory`, `jsxFragmentFactory`,
  `jsxImportSource`). The default is the automatic runtime from `react/jsx-runtime`.
- **`--update-snapshots=missing` now passes the run.** The no-flag behaviour is named `'default'`: it
  writes missing snapshots and fails.
- **Elements inside a hidden iframe count as hidden** for actions, `isVisible()` and `toBeVisible()`. A
  test that clicked into a collapsed iframe now fails, which is correct.
- Video encoding moved to VP9; see `qa/typescript/skills/evidence-capture`.
- The experimental component-testing packages are gone; component tests use the 1.62 stories model.

Coming from an older pin, also check: URL globs lost `?` and `[]` (1.52, use a RegExp); `-gv` was removed
(1.54); `page.accessibility` was removed (1.57, use axe); `_react` / `_vue` selectors and `:light` were
removed (1.58); `workers: 0` and overriding a non-option fixture from the config are errors (1.60);
Node 20 is the floor (1.62) and Node 24 is the target; the Docker image tag must equal the package version.

## 10. Playwright Test Agents (optional)

`npx playwright init-agents --loop=claude` (also `vscode` and `opencode`) [1.56] generates planner,
generator and healer agent definitions into the repo. They are optional: the `qa-ui-typescript` agent does
not depend on them. A repo that uses them regenerates the definitions after every Playwright upgrade,
because they are versioned with Playwright. Failing tests are diagnosed from the trace through the
`npx playwright trace` CLI [1.59].
