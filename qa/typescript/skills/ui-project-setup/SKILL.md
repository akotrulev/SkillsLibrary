---
name: ui-project-setup
description: Use when starting a web-UI test project from zero in TypeScript (Playwright Test, pins, config, Docker image). Triggers "scaffold a UI test project". Not for writing tests (ui-tests-playwright).
---

# UI Test Project Scaffold (TypeScript, Playwright Test 1.64)

This skill stands up a **runnable, empty web-UI test project from zero**: the layout, exact versions, the config loader, the signed-in setup project, one smoke test that proves the wiring, a container image and the run commands. It owns the **project shell**. The Playwright files themselves (`playwright.config.ts`, `fixtures.ts`, `auth.setup.ts`, the pages and the control components) are the assets of [`ui-test-author/playwright`](../ui-test-author/playwright/SKILL.md); copy them, never re-type them here. This skill's own `assets/` add only what the author skill does not ship: `package.json`, `tsconfig.json`, `env.ts`, the smoke spec and the `Dockerfile`.

**Version rule:** new projects use Node 24 (22 maintenance), TypeScript strict mode and `@playwright/test` 1.64.0. Node 20 is end-of-life: never target it. In an existing repo keep its `@playwright/test` version and take the down-level forms from the author skill's version lane.

Default driver is **Playwright Test** (auto-waiting, trace viewer, one runner for UI and API specs). Use **Selenium WebDriverJS** only when the project mandates it (an existing grid, an org standard): keep this layout and the config loader, and follow `qa/typescript/skills/ui-test-author/selenium` for the driver factory, pages and runner.

## When to use

- A fresh repo with no TypeScript UI test project, and the user wants browser coverage.
- The user asks which versions, layout, config or container a Playwright TypeScript suite should use.

## When NOT to use

- The project exists → author into it with `qa/typescript/skills/ui-test-author/playwright`.
- API-only coverage with no Playwright → `qa/typescript/skills/api-project-setup`; API specs in this suite → `qa/typescript/skills/api-test-author/playwright`.
- Native mobile or desktop apps → `mobile-project-setup` / `desktop-project-setup`.
- A Gherkin suite → `qa/typescript/skills/bdd-project-scaffold`.
- .NET / Java → `qa/dotnet/skills/ui-project-setup` / `qa/java/skills/ui-project-setup`.

## Tooling & versions

The Playwright, Allure and image rows are the **Versions** table of `ui-test-author/playwright/SKILL.md`; `assets/package.json` holds the same exact pins, all dev dependencies.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Runtime | Node | **24** | 22 maintenance; `engines.node` is `>=22.12.0` |
| Language | `typescript` | **5.9.3** | `strict: true`, `noUncheckedIndexedAccess`, `moduleResolution: Bundler` (the assets import without extensions) |
| Types | `@types/node` | **24.19.2** | |
| Runner + driver | `@playwright/test` | **1.64.0** | Install it alone; never `playwright` beside it |
| Reporting | `allure-playwright`, `allure-js-commons` | **3.13.0** | Needs `@playwright/test` ≥ 1.62; wiring owned by `qa/reporting/typescript/skills/test-reports` |
| Allure CLI | `allure-commandline` | **2.46.1** | Installed and pinned by `test-reports`; this scaffold installs none |
| Container | `mcr.microsoft.com/playwright` | **v1.64.0-noble** | Ubuntu 24.04, Node 24 and the 1.64.0 browsers preinstalled; the tag always equals the package version |
| Driver (alt) | `selenium-webdriver` | 4.x | Only when mandated; pin per `ui-test-author/selenium` |

## Prerequisites & local setup

```bash
node --version
npx playwright install --with-deps chromium
```

- `node --version` prints v24.x (or v22.12+).
- **Browsers are required** after `npm ci`: without them every test errors with "Executable doesn't exist". `--with-deps` installs OS packages and needs root or sudo; on macOS plain `install chromium` is enough. Inside the container the browsers are already present.

## Project layout (standalone)

```
<product>-ui-tests/
├── package.json · package-lock.json   # assets/package.json; commit the lock
├── tsconfig.json · env.ts             # assets/
├── playwright.config.ts               # ui-test-author/playwright/assets
├── Dockerfile · .dockerignore         # assets/Dockerfile; .dockerignore below
├── .env.example · .gitignore · README.md
├── playwright/.auth/                  # signed-in state, git-ignored
└── tests/
    ├── auth.setup.ts · fixtures.ts    # ui-test-author/playwright/assets
    ├── pages/                         # LoginPage, HomePage, OrdersPage
    ├── components/controls/           # DatePicker, Dropdown, Combobox, DataGrid, GridRow
    └── specs/smoke.spec.ts            # assets/tests/specs/
```

Inside an application repo the same tree lives under `e2e/`. The folder name ends in `-ui-tests` (or is `e2e/`) so the installed rule files' default globs match it.

## Create from zero

```bash
mkdir <product>-ui-tests && cd <product>-ui-tests
git init
cp -R <skills>/qa/typescript/skills/ui-project-setup/assets/. .
```

`<skills>` is this library's root (`${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Then copy the author skill's assets from `qa/typescript/skills/ui-test-author/playwright/assets/`:

| Asset | Goes to | Edit after copying |
|---|---|---|
| `playwright.config.ts` | the root | import `authFile` from `./tests/fixtures`; add `import { requiredEnv } from './env'` and set `baseURL: requiredEnv('BASE_URL')` |
| `fixtures.ts`, `auth.setup.ts` | `tests/` | `fixtures.ts`: delete its local `requiredEnv` function, add `import { requiredEnv } from '../env'`, import the pages from `./pages/<Page>` |
| `LoginPage.ts`, `HomePage.ts`, `OrdersPage.ts` | `tests/pages/` | `OrdersPage.ts`: import the controls from `../components/controls/<Control>` |
| `DatePicker.ts`, `Dropdown.ts`, `Combobox.ts`, `DataGrid.ts`, `GridRow.ts` | `tests/components/controls/` | none |

`login.spec.ts` and `orders.spec.ts` are the author skill's worked examples: read them there, do not copy them into an empty suite. `OrdersPage` and the `seededUser` / `seededOrder` fixtures are examples too: replace them with the app's own screens and endpoints, or delete them. Then:

```bash
npm install
npm run typecheck
npx playwright install chromium
npx playwright test --list
BASE_URL=https://staging.example.test E2E_USER=qa@example.test E2E_PASSWORD="$E2E_PASSWORD" npx playwright test tests/specs/smoke.spec.ts
```

Rename `"name"` in `package.json`, write `.env.example`, `.gitignore`, `.dockerignore` and `README.md` from this page, and commit `package-lock.json`. The smoke against a reachable app is the exit gate: green. `--list` must show the `setup` test and the smoke.

## Configuration

**One loader, one precedence.** `env.ts` exports `requiredEnv(name)`: `process.env` wins (the shell, a sourced local `.env`, or the CI secret store), then the committed non-secret default in its `DEFAULTS`; a key with neither throws naming the key. `playwright.config.ts` and `fixtures.ts` both read through it; no other file reads `process.env` except the config's `CI` switch.

| Key | Default | Read by |
|---|---|---|
| `BASE_URL` | `http://localhost:3000` | `playwright.config.ts` → `use.baseURL` |
| `E2E_USER`, `E2E_PASSWORD` | none: secrets | the `testUser` fixture, read when a test asks for it |

Secrets have no default and never sit in a committed file. A key is declared when the first code reads it. `.env.example`, committed, with no real values:

```
BASE_URL=
E2E_USER=
E2E_PASSWORD=
```

Load a local copy with `set -a; source .env; set +a`. `.gitignore`:

```
node_modules/
test-results/
playwright-report/
blob-report/
allure-results/
allure-report/
playwright/.auth/
.env
```

## The smoke test

```ts
import { expect, test } from '../fixtures';

test.describe('Smoke', { tag: '@smoke' }, () => {
  test('Should_GreetUser_When_SignedInUserOpensHome', async ({ homePage, testUser }) => {
    await homePage.goto();

    await expect(homePage.greeting, `greeting for ${testUser.email}`).toHaveText(`Welcome, ${testUser.email}`);
  });
});
```

It proves the chain: the config loader resolves `BASE_URL`, the `setup` project signs in through `LoginPage` and saves the state, the `chromium` project starts from it, the page arrives as a fixture, and a web-first assertion checks the landmark. It creates nothing and reads only the configured test account. Change the greeting text and test ids to the app's own in `HomePage` and `LoginPage`, not in the spec. An app with no sign-in deletes `auth.setup.ts`, the `setup` project and `storageState` from the config, and asserts its landing page's landmark instead.

## Container

`assets/Dockerfile` runs the suite in the official image, built from the working tree:

```dockerfile
FROM mcr.microsoft.com/playwright:v1.64.0-noble
WORKDIR /work
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV CI=true
ENTRYPOINT ["npx", "playwright", "test"]
```

`.dockerignore`:

```
node_modules
test-results
playwright-report
blob-report
allure-results
allure-report
playwright/.auth
.env
.git
```

```bash
docker build -t ui-tests .
docker run --rm --init --ipc=host -e BASE_URL -e E2E_USER -e E2E_PASSWORD \
  -v "$PWD/allure-results:/work/allure-results" -v "$PWD/test-results:/work/test-results" ui-tests
echo $?
```

- **Built from the checkout** (`COPY`), never by cloning the repository inside the image, so a pull-request build tests the pull request.
- **Pinned**: the base tag equals `@playwright/test` (bump both together, or the run fails with "Executable doesn't exist"); `npm ci` installs exactly the lockfile. The image already holds the browsers and Node 24, so there is no install step.
- **The exit code is the run's.** The exec-form `ENTRYPOINT` makes the Playwright process the container's, so `docker run` returns its code; no `|| true`, and the CI step that runs it has no `continue-on-error`.
- **No secret in the image.** `-e NAME` passes the host's value at run time; nothing is `ENV` or `ARG` in the Dockerfile except `CI=true`, which switches the config to its CI reporters.
- **The report is on the volumes**: `allure-results/` (Allure input), `test-results/` (JUnit XML and the failed tests' trace, screenshot and video). Mount `/work/blob-report` too when shards are merged.
- `--ipc=host` keeps Chromium from running out of shared memory; `--init` reaps child processes (Playwright's Docker guide recommends both). The image runs as root, fine for the team's own app; for untrusted sites use `--user pwuser` and a seccomp profile per that guide.
- An app on the host is reached at `host.docker.internal` (Docker Desktop) or with `--network host` (Linux), set through `BASE_URL`.

The CI hosts run these two commands as steps (`qa/cicd/typescript/skills/ci-pipelines`).

## Run

```bash
npm test
npx playwright test --grep @smoke
npx playwright test --headed
npx playwright test --ui
npx playwright show-report
npx playwright show-trace test-results/<test>/trace.zip
```

The CLI, projects, tags and the 1.64 changes are `ui-test-author/playwright/references/config-and-fixtures.md`; the evidence modes are `evidence-capture`; the Allure report, also as one HTML file, is `qa/reporting/typescript/skills/test-reports`.

## Conventions (the shell only)

The standards the shell must meet are the qa-typescript rule files, not a list here: `qa-typescript.md`, `page-objects.md`, `ui-tests.md` and `test-data.md`. Tell the user to install them with the shell (`/qa-typescript:rules` copies them into `.claude/rules/qa-typescript/`); until then read the plugin's copies in `qa/typescript/skills/rules/`. Where they and this skill's recipes disagree, the rule files win.

- **One config** (`playwright.config.ts` from the author skill); extend it, never start a second.
- **Auth**: one setup project per role, the state under `playwright/.auth/`; token seeding instead of the form is `test-login-tokens`.

Page objects, controls, fixtures, locators and test bodies are owned by `page-object-design`, `page-objects-from-url` and `ui-test-author/*`. Defer to them.

## Setup checklist

- [ ] Node 24 (22.12+); `@playwright/test` 1.64.0 alone, exact pins, all dev dependencies; `package-lock.json` committed
- [ ] The author skill's config, fixtures, setup and pages copied, with the import edits above
- [ ] `env.ts` is the one loader; precedence env → committed default → fail naming the key; no secret committed
- [ ] `.gitignore` takes `playwright/.auth/`, `.env` and every report folder
- [ ] Browsers installed, or the run uses `mcr.microsoft.com/playwright:v1.64.0-noble`
- [ ] `Dockerfile` builds from the checkout; `docker run` returns the test run's exit code; report on mounted volumes
- [ ] `npm run typecheck` clean; `npx playwright test --list` shows setup + smoke; the smoke green.
