# Playwright audit — TypeScript QA lane

**Date:** 2026-10-10 · **Mode:** read-only, nothing in the repo was edited · **Repo:** `/Users/aleksandarkotrulev/RiderProjects/SkillsLibrary` @ `2bec288`

**Scope read:** `qa/typescript/agents/{qa-ui,qa-api,qa-bdd,qa-mobile,qa-llm}-typescript.md`, `qa/typescript/commands/*`, all 48 files under `qa/typescript` that mention Playwright, `qa/reporting/typescript/**`, `qa/cicd/typescript/**`, `qa/cicd/ci-conventions/SKILL.md`, the related `docs/skills-catalog.md` rows, and the `qa-reporting-typescript` / `qa-cicd-typescript` agents.

## 0. Baseline: current upstream facts these findings are judged against

These were checked live on 2026-10-10, against the npm registry, playwright.dev, the Playwright MCP README, and the published allure-playwright package.

| Package / artifact | Current | Released | Note |
|---|---|---|---|
| `@playwright/test` | **1.64.0** | 2026-10-07 | 1.57 2025-11-25 · 1.58 2026-01-23 · 1.59 04-01 · 1.60 05-11 · 1.61 06-15 · 1.62 07-24 · 1.63 09-04 |
| `playwright-bdd` | **9.2.1** | — | peer `@playwright/test >=1.44`, which the library already states correctly |
| `allure-playwright` / `allure-js-commons` | **3.13.0** | — | peer `@playwright/test >=1.62.0`. The `allure` export from `allure-playwright` is `@deprecated for removal` (`dist/types/index.d.ts:62-64`) |
| `@axe-core/playwright` | **4.13.0** | — | — |
| `@playwright/mcp` | **0.0.83** | 2026-09-28 | WebMCP tools are exposed by default as `webmcp_<tool>`. `--no-webmcp` turns this off |
| Docker | `mcr.microsoft.com/playwright:v1.64.0-noble` | — | Noble has been the default since 1.47. The images moved to Node 24 in 1.57 |

These version facts are used in the findings below:

| Version | Facts |
|---|---|
| 1.42 | `tag` |
| 1.43 | `contentFrame` |
| 1.44 | `toHaveAccessibleName`, `toHaveAccessibleDescription`, `toHaveRole`, `--last-failed` |
| 1.45 | `page.clock` |
| 1.46 | `--only-changed`, fixture `box` |
| 1.48 | `routeWebSocket` |
| 1.49 | `toMatchAriaSnapshot`, `tracing.group` |
| 1.50 | `toHaveAccessibleErrorMessage`, `--update-snapshots` modes (`changed` and `all`) |
| 1.51 | `filter({visible})`, `step.attach` |
| 1.52 | `toContainClass`, `failOnFlakyTests`, `testProject.workers`. **Glob `?` and `[]` removed** |
| 1.53 | `locator.describe()` |
| 1.56 | Playwright Test Agents (planner, generator, healer) via `npx playwright init-agents`. `page.consoleMessages()`, `page.pageErrors()`, `page.requests()` |
| 1.57 | Chrome for Testing, `webServer.wait` |
| 1.60 | `tracing.startHar()`. Context options `videoSize` and `videosPath` removed |
| 1.61 | New video modes, `expect.soft.poll` |
| 1.62 | `retryStrategy`, WebP snapshots |
| 1.63 | `locator.visible()`, trace `snapshots` object, `frameLocator()` with no selector |
| 1.64 | **WebMCP** (`page.webmcp.tools()` and `callTool()`, needs Chromium `--enable-features=WebMCP`), **`locator.within()`**, `--update-snapshots=missing` now passes |

Severities follow the house table: blocker / major / minor / nit. Findings are split into three classes: **Data issue** (a stale or missing fact), **Code issue** (wrong example code) and **Logical conflict** (two sources disagree).

---

## 1. Version-pin inventory

**There are 17 version strings.** 16 are in the Playwright family. The 17th is a version claim for allure-js-commons. Six more pins are adjacent to Playwright and listed separately. The agents, the commands and `docs/skills-catalog.md` contain no pins.

| # | file:line | Exact string | Verdict |
|---|---|---|---|
| P1 | `qa/typescript/skills/realtime-stream-testing/SKILL.md:71` | `` `@playwright/test` (≥ **1.48** for `routeWebSocket`) `` | Correct floor for `routeWebSocket` |
| P2 | `qa/typescript/skills/realtime-stream-testing/SKILL.md:215` | `` (Playwright `routeWebSocket`, ≥ 1.48) `` | Correct |
| P3 | `qa/typescript/skills/realtime-stream-testing/SKILL.md:217` | `` `page.routeWebSocket` (Playwright **1.48**) `` | Correct |
| P4 | `qa/typescript/skills/network-mocking/references/playwright-routes.md:8` | `` `@playwright/test` (Playwright ≥ 1.48 — `routeWebSocket`, the post-1.43 glob semantics, `routeFromHAR` update modes) `` | **Wrong**: the glob change landed in 1.52, not 1.43. A 1.48 floor does not give the stated semantics |
| P5 | `qa/typescript/skills/network-mocking/references/playwright-routes.md:53` | `` `page.routeWebSocket(url, ws => …)` \| ≥ 1.48 `` | Correct |
| P6 | `qa/typescript/skills/network-mocking/references/playwright-routes.md:275` | `` Glob `?` and `[]` (character classes) are not supported** since Playwright 1.43 `` | **Wrong**, should say 1.52 |
| P7 | `qa/typescript/skills/network-mocking/references/playwright-routes.md:312` | `` No glob `?`/`[abc]` since 1.43 `` | **Wrong**, should say 1.52 |
| P8 | `qa/typescript/skills/network-mocking/references/cdp.md:10` | `` `@playwright/test` (Playwright ≥ 1.49) `` | Arbitrary: `newCDPSession` predates 1.0 |
| P9 | `qa/typescript/skills/bdd-project-scaffold/SKILL.md:27` | `` `playwright-bdd` (latest line **9.2.x**), peer `@playwright/test` **≥ 1.44** `` | Correct (9.2.1, peer `>=1.44`) |
| P10 | `qa/typescript/skills/bdd-project-scaffold/SKILL.md:78` | `"@playwright/test": "^1.49.0",` | Stale floor. Caret resolves to 1.64, but pairing with allure-playwright 3.13 needs `>=1.62` |
| P11 | `qa/typescript/skills/bdd-project-scaffold/SKILL.md:79` | `"playwright-bdd": "^9.2.0",` | Correct |
| P12 | `qa/typescript/skills/gherkin-step-code/references/playwright-bdd.md:9` | `` `playwright-bdd` 9.2.x on `@playwright/test` ≥ 1.44, Node ≥ 20 `` | The Playwright half is correct. **Node ≥ 20 conflicts with CLAUDE.md** (Node 20 has been EOL since April 2026) |
| P13 | `qa/typescript/skills/visual-regression/references/playwright-snapshots.md:213` | `mcr.microsoft.com/playwright:v1.50.0-noble \` | **Stale by 14 minors.** Line 211 itself says the tag must match the installed version. It should be `v1.64.0-noble`, or better, derived from the lockfile |
| P14 | `qa/reporting/typescript/skills/flaky-test-quarantine/SKILL.md:101` | `` (`{ tag: '@flaky' }`, Playwright 1.42+) `` | Correct |
| P15 | `qa/typescript/skills/page-objects-from-url/SKILL.md:31` | `claude mcp add playwright npx @playwright/mcp@latest -- --caps=testing,storage` | Floating `@latest`. That is acceptable for a dev tool (ci-conventions:77 bans floating tags only in CI). The flags are valid: the README lists `testing` and `storage` as opt-in caps |
| P16 | `qa/typescript/skills/browser-cloud-setup/references/details.md:70` | `'client.playwrightVersion': '1.x', // pin to your installed Playwright in real config` | Placeholder. It should be derived from `@playwright/test/package.json` |
| P17 | `qa/reporting/typescript/skills/test-reports/SKILL.md:102` | `` In `allure-js-commons` v2 (used by all three adapters) `` | **Stale**: current is v3. The v2-era `import { allure }` is deprecated |

**Adjacent pins.** These are not Playwright-family, but they live in the same files:

| # | file:line | String | Note |
|---|---|---|---|
| A1 | `qa/reporting/typescript/skills/test-reports/SKILL.md:247` and `:248` | `allure-2.27.0.tgz` / `./allure-2.27.0/bin/allure` | Conflicts with A3 |
| A2 | `qa/reporting/typescript/skills/test-reports/SKILL.md:284` and `:288` | `allure-2.27.0.tgz` / `./allure-2.27.0/bin/allure` | Conflicts with A3 |
| A3 | `qa/cicd/ci-conventions/SKILL.md:77` | `` `allure-commandline@2.30.0` `` | — |
| A4 | `qa/typescript/skills/bdd-project-scaffold/SKILL.md:80` | `"typescript": "^5.6.0"` | — |
| A5 | `qa/typescript/skills/browser-cloud-setup/references/details.md:117` | `version: package.json      # match the installed Playwright` | Good: it indirects to the installed version |
| A6 | `qa/cicd/dotnet/skills/ci-pipelines/references/gitlab-ci.md:189` (out of scope) | `mcr.microsoft.com/playwright/dotnet:v1.47.0-jammy` | The sibling lane has the same staleness |

**Unversioned installs.** These are fine as long as the lockfile governs: `test-reports/SKILL.md:57` (`pnpm add -D allure-playwright allure-commandline`), `axe-playwright.md:23` (`npm install --save-dev @axe-core/playwright axe-core`), and the CI `playwright install --with-deps chromium` steps (`github-actions.md:259`, `gitlab-ci.md:194`, `azure-pipelines.md:119`).

**Structural gap: no Playwright version lane.** The floors are scattered across files (1.42, 1.44, 1.48, 1.49, 1.50). No skill keys its guidance to the detected Playwright minor version, which the CLAUDE.md "Version policy" asks every skill to do. The agent caches a "runner + browser-automation tool and its major" (`qa-ui-typescript.md:74`), but a major version is useless for Playwright, which is still on 1.x.

---

## 2. Capability coverage matrix

Status legend:

| Status | Meaning |
|---|---|
| ✅ | Correct and current |
| ⚠ | Present but partial, outdated or contradicted |
| ❌ | Wrong |
| ⬜ | Missing: 0 hits across the scope |

### 2.1 Locators

| Capability | Taught at | Status |
|---|---|---|
| `getByRole` | `ui-test-author/playwright/SKILL.md:59,174`; `page-objects-from-url/SKILL.md:115` | ✅ |
| `getByLabel` | `ui-test-author/playwright/SKILL.md:57,175` | ✅ |
| `getByTestId` | `ui-test-author/playwright/SKILL.md:60,173`; `page-objects-from-url/SKILL.md:114,136` | ✅ (testid-first is the house policy) |
| `getByText` (+ `exact`) | `ui-test-author/playwright/SKILL.md:177,215` | ✅ |
| `getByPlaceholder` | `ui-test-author/playwright/SKILL.md:176`; `page-objects-from-url/SKILL.md:115` | ✅ |
| `getByAltText` / `getByTitle` | — | ⬜ |
| `filter({ has, hasNot, hasText, hasNotText, visible })` | — | ⬜ (0 hits) |
| `and()` / `or()` | — | ⬜ |
| Chaining (`row.getByRole(...)`) | `page-object-design/SKILL.md:45,91,166` gives the component-scoped-to-parent idea in prose only | ⚠ No Playwright chaining example |
| Scoping or "within" pattern | `page-object-design/SKILL.md:91` (`parent.locator(...)`) | ⚠ Design-level only. `locator.within()` (1.64) is absent |
| `locator.describe()` (1.53) / `locator.visible()` (1.63) | — | ⬜ |
| `frameLocator` / `contentFrame` (1.43) | — | ⬜ |
| Strictness | `ui-test-author/playwright/SKILL.md:215` (one sentence about strict-mode violations) | ⚠ |
| `nth` / `first` misuse | Not a rule anywhere; review has no row for it | ⬜ |
| CSS / XPath fallback | `ui-test-author/playwright/SKILL.md:178`; `page-objects-from-url/SKILL.md:115` | ⚠ The rule is right but mandates a `// TODO` comment (see L1) |
| `testIdAttribute` | `page-objects-from-url/SKILL.md:36` (via `test.use` / `selectors.setTestIdAttribute`) | ⚠ Absent from the ui-test-author config. Also missing that TestOptions accepts a comma-separated list, which would bridge `data-test` (Selenium) and `data-testid` |
| `page.addLocatorHandler` (overlays) | — | ⬜ `ui-test-author/playwright/SKILL.md:203` says "close the overlay" but never teaches the handler |

### 2.2 Web-first assertions

| Capability | Taught at | Status |
|---|---|---|
| `toBeVisible` / `toBeHidden` | `ui-test-author/playwright/SKILL.md:74,119,195-196` | ✅ |
| `toHaveText` | `ui-test-author/playwright/SKILL.md:120,195,197` | ✅ |
| `toHaveValue` | Only WDIO (`mobile-native-features`) | ⬜ for Playwright |
| `toHaveAccessibleName` / `Description` / `ErrorMessage`, `toHaveRole` | — | ⬜ The a11y skill teaches only axe |
| `toContainClass` / `toHaveClass` | — | ⬜ |
| `toHaveCount` | `ui-test-author/playwright/SKILL.md:195,197` | ✅ |
| `toHaveURL` | `ui-test-author/playwright/SKILL.md:195,204`; `inhouse-framework-conventions/SKILL.md:137` | ✅ The predicate form (1.51) is not mentioned |
| `toMatchAriaSnapshot` / aria snapshots | — | ⬜ |
| `expect.poll` | `ui-test-author/playwright/SKILL.md:212-213`; `api-test-author/playwright/SKILL.md:185` | ✅ |
| `toPass` | `ui-test-author/playwright/SKILL.md:200,212` | ✅ Includes good inner-timeout advice |
| `expect.soft` | `ui-test-author/playwright/SKILL.md:216`; `api-test-author/playwright/SKILL.md:159,179,209`; `cdp.md:225,260` | ✅ `expect.soft.poll` (1.61) is absent |
| `expect.configure` | — | ⬜ |
| `expect.extend` (custom matchers) | — | ⬜ |
| Custom message argument | `playwright-routes.md:185` | ✅ |
| Custom message argument | `ui-test-author/playwright/SKILL.md:199` | ❌ Wrong API (C1) |

### 2.3 Fixtures

| Capability | Taught at | Status |
|---|---|---|
| `test.extend` | `ui-test-author/playwright/SKILL.md:83-99`; `api-test-author/playwright/SKILL.md:78-112`; `playwright-routes.md:91-95`; `cdp.md:142-148`; `axe-playwright.md:133-140` | ✅ |
| Worker scope | Prose only (`api-test-author/playwright/SKILL.md:24`). Every example is test-scoped, and `browser-cloud-setup/references/details.md:85` connects a whole grid browser per test | ⬜ |
| `auto` / `box` fixtures | — | ⬜ |
| Option fixtures | `language-testing/references/details.md:21` | ✅ |
| Setup projects + `dependencies` for `storageState` | `ui-test-author/playwright/SKILL.md:144-151,223-225` | ✅ Contradicted by test-login-tokens (L7) |
| `globalSetup` / `globalTeardown` | `test-login-tokens/references/details.md:150-174`; `browser-cloud-setup/references/details.md:284-290` | ⚠ The teardown is defective (C19) |

### 2.4 Config

| Capability | Taught at | Status |
|---|---|---|
| `retries` | `flaky-test-quarantine/SKILL.md:74`, which conflicts with CI refs `github-actions.md:44`, `gitlab-ci.md:57`, `azure-pipelines.md:301` | ⚠ Conflict (L3) |
| `workers` | `browser-cloud-setup/references/details.md:212`; `lighthouse-ci.md:121` (project-level workers need ≥1.52, not stated) | ✅ / ⚠ |
| `fullyParallel` | — | ⬜ |
| `forbidOnly` | `playwright-snapshots.md:46` only | ⚠ |
| `failOnFlakyTests` / `--fail-on-flaky-tests` | — | ⬜ |
| `webServer` (incl. 1.57 `wait`) | — | ⬜ |
| Reporters: html, blob, merge-reports | `github-actions.md:232-320`; `gitlab-ci.md:186-224` | ✅ |
| Reporters: junit | `azure-pipelines.md:133-140` only | ⚠ |
| Reporters: allure | `test-reports/SKILL.md:65-68` | ⚠ Three different reporter arrays across skills (L5) |
| `snapshotPathTemplate` / `pathTemplate` | — | ⬜ Relevant once baselines are Docker-generated (`playwright-snapshots.md:72-79`) |
| projects / `devices` | `ui-test-author/playwright/SKILL.md:147-150`; `playwright-snapshots.md:59`; `responsive-testing/SKILL.md:48,64` | ✅ |
| Canonical full `playwright.config.ts` | Nowhere in the UI lane. CI refs claim ui-test-author owns it (L5) | ⬜ |

### 2.5 Evidence capture

| Capability | Taught at | Status |
|---|---|---|
| `screenshot` option | `test-reports/SKILL.md:71,130` (`'only-on-failure'`) | ⚠ Object form (`fullPage`, `omitBackground`) and `'on-first-failure'` are absent |
| `toHaveScreenshot` options (mask, maskColor, animations, caret, stylePath, fullPage, clip, threshold, maxDiffPixels / Ratio, scale) | `playwright-snapshots.md:140-183` | ✅ Missing `style`, `omitBackground`, `timeout`, `type:'webp'` (1.62) |
| `video` modes and size | `test-reports/SKILL.md:72`; `ui-test-author/review/SKILL.md:147` (`retain-on-failure`) | ⚠ No mode list, no `{mode,size,fps}` object, no 1.61 modes. Good news: the removed `videoSize` / `videosPath` options are not used anywhere |
| `trace` modes | `test-reports/SKILL.md:70,77`; `ui-test-author/review/SKILL.md:99,147` | ⚠ Conflict (L4). The trace object form (`snapshots` / `screenshots` / `sources` / `attachments`) is absent |
| Trace viewer | `ui-test-author/playwright/SKILL.md:242`; `playwright-routes.md:328`; `cdp.md:310` (via `--ui`) | ⚠ No `npx playwright show-trace` / `show-report`, no trace.playwright.dev |
| `test.step` | `ui-test-author/playwright/SKILL.md:217-218,262`; `test-reports/SKILL.md:193` | ✅ `box`, `timeout`, `step.skip`, `step.attach` (1.50/1.51) are absent |
| `tracing.group` (1.49) | — | ⬜ |
| HAR (`routeFromHAR`) | `playwright-routes.md:213-236` | ✅ |
| HAR (`recordHar`) | `playwright-routes.md:238` | ❌ Invalid `test.use({ recordHar })` (C3). `tracing.startHar()` (1.60) is absent |
| `testInfo.attach` | — | ⬜ Only the deprecated `allure.attachment` is taught |
| Allure attachments | `test-reports/SKILL.md:125-165`; `axe-playwright.md:234-250`; `lighthouse-ci.md:193-201`; `playwright-snapshots.md:244-257`; `browser-cloud-setup/references/details.md:223-232` | ⚠ Deprecated import (D3) and floating promises (C8) |

### 2.6 Network, clock, emulation

| Capability | Taught at | Status |
|---|---|---|
| `page.route` / `context.route` | `playwright-routes.md:40-50,57-117,285-287` | ✅ The popup claim at `:286` is wrong (C16) |
| `routeFromHAR` | `playwright-routes.md:213-236` | ✅ |
| `routeWebSocket` | `realtime-stream-testing/SKILL.md:215-250`; `playwright-routes.md:53` | ✅ Duplicated ownership (L22) |
| `request` fixture / `APIRequestContext` | `api-test-author/playwright/SKILL.md:78-112`; `ui-test-author/playwright/SKILL.md:158-166` | ✅ |
| `waitForResponse` | `ui-test-author/playwright/SKILL.md:205-211`; `playwright-routes.md:49,290` | ✅ |
| `page.requests()` / `consoleMessages()` / `pageErrors()` (1.56) | — | ⬜ They would simplify the "not called" pattern at `playwright-routes.md:170-189` |
| `page.clock` (1.45) | — | ⬜ **Even though `visual-regression/SKILL.md:38` mandates "freeze … clocks"**, and `language-testing/SKILL.md:24-29` relies on time-sensitive formatting |
| `devices` | `ui-test-author/playwright/SKILL.md:149`; `responsive-testing/SKILL.md:48,187` | ✅ |
| `viewport` | `responsive-testing/SKILL.md:64,87` | ⚠ Self-contradiction (L20) |
| `colorScheme` / `reducedMotion` / `forcedColors` / `contrast` | — | ⬜ |
| `locale` / `timezoneId` | `language-testing/SKILL.md:58,64`; `language-testing/references/details.md:21` | ✅ |
| `geolocation` / `permissions` (web) | — | ⬜ Only covered for WDIO mobile |
| Offline | `playwright-routes.md:240-251` (`context.setOffline`) | ✅ |

### 2.7 Tooling, CLI, MCP, agents

| Capability | Taught at | Status |
|---|---|---|
| UI mode (`--ui`) | `ui-test-author/playwright/SKILL.md:264`; `playwright-routes.md:328`; `cdp.md:310` | ✅ |
| codegen | — (only for gRPC / GraphQL / mobile codegen) | ⬜ |
| `--debug` / `PWDEBUG` / `page.pause()` | — | ⬜ |
| `--last-failed` (1.44) / `--only-changed` (1.46) | — | ⬜ |
| `--grep` / `--grep-invert` / `grepInvert` | `flaky-test-quarantine/SKILL.md:38,101,122,133` | ✅ |
| Tags via `{ tag }` | `qa-ui-typescript.md:47`; `flaky-test-quarantine/SKILL.md:108` | ⚠ Conflict with title tags (L11) |
| `--shard` | `github-actions.md:263-264`; `gitlab-ci.md:197`; `azure-pipelines.md:133-134` | ✅ |
| `--update-snapshots` | `playwright-snapshots.md:214,217-219,306` | ⚠ No modes (1.50) and no CI `updateSnapshots:'none'`. The 1.64 behaviour change is not mentioned (D14) |
| `--repeat-each` (flake hunting) | — | ⬜ |
| Playwright MCP tool names | See §2.8 | ✅ All valid in 0.0.83 |
| Playwright Test Agents (planner / generator / healer, `init-agents --loop=claude`) | — (0 hits repo-wide) | ⬜ |
| **WebMCP** | — (0 hits repo-wide) | ⬜ |

### 2.8 Playwright MCP tool names

The tools named in agent frontmatter are identical in `qa/typescript/agents/qa-ui-typescript.md:4` and `qa/typescript/agents/qa-bdd-typescript.md:4`. Validity was checked against the `@playwright/mcp` README (0.0.83).

| Tool | Cap needed | Referenced in a skill body |
|---|---|---|
| `mcp__playwright__browser_navigate` | core | `page-objects-from-url/SKILL.md:28,61` |
| `mcp__playwright__browser_snapshot` | core | `page-objects-from-url/SKILL.md:28,67` |
| `mcp__playwright__browser_evaluate` | core | `page-objects-from-url/SKILL.md:28,69,84`; `qa-ui-typescript.md:44` |
| `mcp__playwright__browser_click` | core | `page-objects-from-url/SKILL.md:62,85` |
| `mcp__playwright__browser_type` | core | `page-objects-from-url/SKILL.md:62` |
| `mcp__playwright__browser_handle_dialog` | core | `page-objects-from-url/SKILL.md:62` |
| `mcp__playwright__browser_fill_form` | core | never referenced |
| `mcp__playwright__browser_select_option` | core | never referenced |
| `mcp__playwright__browser_wait_for` | core | never referenced |
| `mcp__playwright__browser_take_screenshot` | core | never referenced |
| `mcp__playwright__browser_generate_locator` | `--caps=testing` | `page-objects-from-url/SKILL.md:34,86` |
| `mcp__playwright__browser_set_storage_state` | `--caps=storage` | `page-objects-from-url/SKILL.md:35,62` |
| `mcp__playwright__browser_storage_state` | `--caps=storage` | `page-objects-from-url/SKILL.md:35` |

Gaps in the granted set:

- **Not granted but needed** by `page-objects-from-url`'s "dynamic states" step (`page-objects-from-url/SKILL.md:49,85`): `browser_hover`, `browser_press_key`, `browser_tabs`, `browser_navigate_back`, `browser_close`, `browser_resize` and `browser_find`.
- **Never used:** the `browser_verify_*` tools behind `--caps=testing`.
- **Dynamic tools never mentioned:** the `webmcp_<tool>` tools that MCP 0.0.83 exposes by default.

The `page-objects-from-url/SKILL.md:37` claim about the `target` vs `ref` parameter is accurate for 0.0.83, and so is the `--test-id-attribute` option at `:36`.

**Clean results.** These anti-patterns were searched for and found nowhere in example code:

- `page.$` / `$$`
- `elementHandle`
- `waitForSelector`
- `page.type` / `pressSequentially`
- `waitForNavigation`, except where it is banned (`ui-test-author/playwright/SKILL.md:204`)
- `networkidle`, except where it is banned (`ui-test-author/playwright/SKILL.md:201`)
- `isVisible()` used as an assertion, except where it is flagged (`ui-test-author/review/SKILL.md:78`)
- the removed `page.accessibility`

`waitForTimeout` appears only as a labelled counter-example (`inhouse-framework-conventions/SKILL.md:236`, and in the anti-pattern lists).

---

## 3. Anti-patterns and defects

### 3.1 Data issues (stale or missing facts)

| ID | Severity | Location | Issue | Suggested fix |
|---|---|---|---|---|
| D1 | major | `visual-regression/references/playwright-snapshots.md:213` | Docker image `v1.50.0-noble` (Jan 2025). Current is 1.64.0, and `:211` says the tag must match `@playwright/test` | Use `v1.64.0-noble`, or tell the reader to read the version from the lockfile. Add `--ipc=host` and an in-container `npm ci` |
| D2 | minor | `network-mocking/references/playwright-routes.md:8,275,312` | Glob `?` / `[]` removal is dated to 1.43. It was a **1.52** breaking change | Change to 1.52 and state the floor accordingly |
| D3 | major | `qa/reporting/typescript/skills/test-reports/SKILL.md:102,105-106,157,186`; `playwright-snapshots.md:246`; `percy.md:220`; `applitools.md:232`; `axe-playwright.md:237`; `lighthouse-ci.md:194`; `browser-cloud-setup/references/details.md:225` | `import { allure } from 'allure-playwright'` is `@deprecated for removal` in 3.13.0. `test-reports:102` still calls the API "allure-js-commons v2" | Use `import * as allure from 'allure-js-commons'` everywhere, as `flaky-test-quarantine/SKILL.md:106,219` already does |
| D4 | minor | `test-reports/SKILL.md:67` | `outputFolder` is not an allure-playwright v3 option. The v3 config is `resultsDir` plus `detail` and `suiteTitle`, so the value is silently ignored | Use `resultsDir: 'allure-results'` |
| D5 | minor | `bdd-project-scaffold/SKILL.md:78`; `test-reports/SKILL.md:57` | allure-playwright 3.13 requires `@playwright/test >=1.62`. No skill mentions the pairing, and the scaffold floor is `^1.49.0` | Add a version-lane note: older Playwright pins an older allure-playwright |
| D6 | minor | `network-mocking/SKILL.md:3`; `visual-regression/SKILL.md:3`; `accessibility-testing/SKILL.md:3` | The descriptions say "Vitest test suite" or "Vitest UI tests" for Playwright-Test skills. This misroutes auto-triggering | Say "Playwright Test" |
| D7 | minor | `bdd-project-scaffold/SKILL.md:26,32`; `gherkin-step-code/references/playwright-bdd.md:9` | `Node ≥ 20` | Node 24 / 22, and flag 20 per CLAUDE.md |
| D8 | minor | `browser-cloud-setup/references/details.md:70` | `'client.playwrightVersion': '1.x'` placeholder | Read the version from `@playwright/test/package.json` |
| D9 | minor | `network-mocking/SKILL.md:27,30`; `cdp.md:3,20` | Claims security-header and TLS `securityDetails` auditing needs CDP and is Chromium-only. Playwright's own `response.allHeaders()` and `response.securityDetails()` cover it at the routing layer | Route the header / TLS audit to `page.waitForResponse` and keep CDP for throttling and metrics |
| D10 | minor | `visual-regression/references/playwright-snapshots.md:45-46,214,217-219` | `--update-snapshots` is shown with no mode. The comment at `:45` promises "never write/update baselines implicitly on CI" but the config only sets `forbidOnly`. As of 1.64, `missing` passes | Add `updateSnapshots: process.env.CI ? 'none' : 'missing'` and document the `changed` / `all` / `missing` / `none` modes |
| D11 | minor | `accessibility-testing/references/axe-playwright.md:91,117,137` | The gate tag set stops at WCAG 2.1 AA, although `:115` lists `wcag22aa` and the library claims WCAG 2.2 (`docs/skills-catalog.md:174`) | Add `wcag22aa` to the shared fixture |
| D12 | minor | `docs/skills-catalog.md:51,58,70` | `:51` lists inhouse-framework-conventions as "dotnet (java sibling…)" and omits the TS skill (`:30` lists it). `:58` names `ui-test-author/reviewer` but the folder is `review`. `:70` names `bdd-project-setup` but the folder is `bdd-project-scaffold` | Correct the rows |
| D13 | minor | `realtime-stream-testing/SKILL.md:256` | Says to mock SSE via `page.route` "returning a chunked text/event-stream body". `route.fulfill` delivers the body at once, so EventSource reads all events then reconnects | Say so, or prefer the protocol-client SSE test |
| G1 | major | Visual (`visual-regression/SKILL.md:38`), i18n (`language-testing/SKILL.md:24-29`) | **`page.clock` is never taught**, yet "freeze clocks" is a shared rule | Add `page.clock.setFixedTime` / `install` to the visual and i18n skills |
| G2 | major | `ui-test-author/playwright` | No locator scoping or filtering: `filter`, `and`, `or`, `within()`, frames, `nth` policy, `describe()` | See §4.3 |
| G3 | major | Lane-wide | No canonical `playwright.config.ts` or evidence-capture section (`testInfo.attach`, the trace / video / screenshot object forms, `tracing.group`, `show-trace`) | See §4.2 |
| G4 | minor | Lane-wide | Missing Playwright-native a11y assertions (`toHaveAccessibleName` / `Description` / `ErrorMessage`, `toHaveRole`) and `toMatchAriaSnapshot` | Add them to `axe-playwright.md` or ui-test-author |
| G5 | minor | Lane-wide | Missing `failOnFlakyTests`, `webServer`, `fullyParallel`, worker / auto / box fixtures, `expect.configure` / `extend`, `--last-failed` / `--only-changed` / `--repeat-each`, `page.requests()` / `consoleMessages()`, `colorScheme` / `reducedMotion`, Test Agents | Add each to the owning skill |
| G6 | minor | Lane-wide | **WebMCP** (1.64) is absent repo-wide | See §4.4 |

### 3.2 Code issues (wrong example code)

| ID | Severity | Location | Issue | Suggested fix |
|---|---|---|---|---|
| C1 | major | `ui-test-author/playwright/SKILL.md:199` | ``expect(await banner.getText(), `…`).toBe('Saved')``. `getText()` is a WebdriverIO API, not a Playwright Locator method, and the one-shot check is the exact pattern `:195` bans | ``await expect(banner, `success banner after saving order ${orderId}`).toHaveText('Saved')`` |
| C2 | major | `ui-test-author/review/SKILL.md:68-69,146` | Recommends `test.each` for Playwright and flags `for` loops as major. Playwright Test has no `test.each`. The house pattern is a loop that generates `test()` calls (`ui-test-author/playwright/SKILL.md:244`, `data-driven-testing/SKILL.md:230-252`) | Rewrite the row: "one generated `test()` per row; no loop inside one test" |
| C3 | major | `network-mocking/references/playwright-routes.md:238` | `test.use({ recordHar: {...} })`. `recordHar` is not a TestOptions property, so this is a type error under strict | `test.use({ contextOptions: { recordHar: {...} } })`, or `context.tracing.startHar()` on 1.60+ |
| C4 | major | `responsive-testing/SKILL.md:92-98,148` | `if/else` picks assertions inside a test, and a ternary computes the expected value. This violates CLAUDE.md "No conditional logic in tests" | Rows carry `{ width, visible, hidden, expectedCols }`; one generated test per row |
| C5 | major | `visual-regression/references/applitools.md:139-146,296-305` | `try { … } finally { eyes.close(false) }` inside the test body. CLAUDE.md forbids inline try/finally; cleanup belongs in teardown | Use the Applitools Playwright fixture (`:252`) or an `eyes` fixture with teardown |
| C6 | major | `playwright-snapshots.md:49`; `bdd-project-scaffold/SKILL.md:104` | `trace: 'on-first-retry'` with no `retries` set, while CI mandates `retries: 0` (`github-actions.md:44`). **No trace is ever recorded** | `trace: 'retain-on-failure'`, per `test-reports/SKILL.md:70` |
| C7 | major (not executed) | `playwright-snapshots.md:191-194` | `page.pdf()` plus `toMatchSnapshot('invoice.pdf')` as a raw byte comparison. Chromium PDFs embed creation-date metadata, so the comparison will not be stable. `page.pdf` is also Chromium-only | Assert on extracted text or structure, or rasterize then `toHaveScreenshot` |
| C8 | major | `axe-playwright.md:239-249`; `lighthouse-ci.md:198-201`; `browser-cloud-setup/references/details.md:228-231`; `playwright-snapshots.md:253` | `allure.attachment` / `allure.link` are called un-awaited inside sync `void` helpers. These are floating promises, which `ui-test-author/review/SKILL.md:70` grades as **blocker** and `test-reports/SKILL.md:325` forbids | Make the helpers `async` and `await` them, or use `testInfo.attach` |
| C9 | major | `browser-cloud-setup/references/details.md:85-98` | The `gridBrowser` fixture creates a `page`, yields the `browser`, then marks status on that unused page. This contradicts `:77` ("specs … receive a `page`"). It is also test-scoped, so it opens one grid session per test. The built-in `use.connectOptions` is never mentioned | Override the worker-scoped `browser` fixture, or set `use: { connectOptions: { wsEndpoint } }` |
| C10 | major | `inhouse-framework-conventions/SKILL.md:101-107` | `page.fill(selector)`, `page.click(selector)` and `page.innerText(selector)`. Playwright marks these page-level selector methods as discouraged. `getErrorMessage(): Promise<string>` invites one-shot assertions | Use Locator-based actions and expose a `Locator` for assertions |
| C11 | minor | `cdp.md:131-133,181-191` | `responseFor` returns the **first** match, which is the pre-reload 200 response, so the cache-disable test can never fail | Capture after the click with `waitForResponse`, or take the last match |
| C12 | minor | `ui-test-author/playwright/SKILL.md:161` | `expect(res.ok()).toBeTruthy()`. This is a boolean dance (banned at `:247`) and carries no evidence | ``expect(res.status(), await res.text()).toBe(201)`` |
| C13 | minor | `playwright-routes.md:149`; `responsive-testing/SKILL.md:113,135`; `cdp.md:224-226` | `expect(bool).toBe(true)` and `for` loops of assertions in helpers. Evidence is lost and assertions run in a loop | Use `toMatchObject`, or compare whole arrays and objects |
| C14 | minor | `playwright-routes.md:207-210` | `route.continue({ headers })` is neither awaited nor returned: a floating promise | `return route.continue({ headers })` |
| C15 | minor | `playwright-routes.md:137,141` | `(json: any)` under strict mode, and a glob-to-substring hack `urlGlob.replace(/\*/g,'')` | Type the payload; use the glob or predicate overload |
| C16 | minor | `playwright-routes.md:286` | "`page.route` for one page (handles its popups)". The Playwright docs say `page.route` does not intercept a popup's first request; use `context.route` | Correct the sentence |
| C17 | minor | `playwright-routes.md:215,298,326` vs `:223` | The prose says `content: 'attach'` but the `routeFromHAR` option is `updateContent` (`content` belongs to `recordHar`) | Name both options correctly |
| C18 | minor | `axe-playwright.md:193-196` | `if (incomplete.length) console.warn(...)`: conditional logic plus console output in a test, and the incompletes are effectively silent in CI | `test.info().attach('axe-incomplete', …)` or an annotation |
| C19 | minor | `browser-cloud-setup/references/details.md:284-290` | `globalSetup` and `globalTeardown` each construct their own `GridTunnel`, so teardown stops an instance that was never started | Return the teardown function from `globalSetup` |
| C20 | minor | `lighthouse-ci.md:125-161,263-279` | Manual `chromium.launch` in `beforeAll` with a module-level `let browser`. This is static mutable state, bypasses fixtures (no trace or screenshot), never closes the page, and the test has no `expect` | Use a worker fixture that owns the debug-port browser |
| C21 | minor | `email-testing/references/mailpit.md:176,203-206` | `deleteAll()` per test on a shared inbox wipes other workers' mail under parallel runs. This contradicts `:255` (unique recipient) | Filter by a unique recipient; no global wipe |
| C22 | minor | `page-objects-from-url/SKILL.md:72-79` | The testid harvest hardcodes `[data-testid]`, ignoring the custom `--test-id-attribute` at `:36`, and misses shadow DOM and iframes | Parameterize the attribute and note the blind spots |
| C23 | minor | Azure `azure-pipelines.md:133-135,149-153`; GitLab `gitlab-ci.md:209-210`; GitHub `github-actions.md:41,433` | Azure: the CLI `--reporter=junit,line,allure-playwright` drops `html`, yet `playwright-report` is published. GitLab: `reports:junit: blob-report/junit-*.xml` while the configured reporters emit no junit. GitHub: a JUnit file is required for dorny but the UI job emits none | Add the junit reporter consistently and only publish what is produced |
| C24 | minor | `playwright-snapshots.md:249-257` | An `afterEach` with `if`/`for` re-attaches diff images that allure-playwright already reports from `testInfo.attachments` | Delete it |
| C25 | minor | `network-mocking/references/proxy.md:211,239,260,251-261` | try/finally in test bodies; the fault-injection test has no assertion | Fixture teardown, plus assert on the error state |
| C26 | minor | **Systemic**, ~120 lines | **Inline comments in code samples** violate CLAUDE.md Comments ("No inline comments"), and agents copy samples verbatim. Sites include: `api-test-author/playwright/SKILL.md:84-86,107,146-147,154`; `playwright-routes.md:183,199,218,228-229,263`; `cdp.md:90-91,103,156,166,170,188,198,236,246,255,259`; `playwright-snapshots.md:45,53-56,118,120,136-151,193,291-295`; `axe-playwright.md:88-94,105-107,138,168-172,186,204,218-219,241,243,256`; `flaky-test-quarantine/SKILL.md:74,109-111,122-123,220-236`; `bdd-project-scaffold/SKILL.md:94,108,123-124`; `responsive-testing/SKILL.md:88,94,109,163-167`; `production-uptime-checks/SKILL.md:178-192`; `lighthouse-ci.md:135,143-160`; `test-reports/SKILL.md:112,117` (an AAA banner) | Strip them; move rationale into the prose |
| C27 | nit | `playwright-snapshots.md:55-56,150-151` | Sets `animations:'disabled'`, `caret:'hide'` and `scale:'css'`, which are already the `toHaveScreenshot` defaults. This is KISS noise | Remove them |
| C28 | nit | `ui-test-author/playwright/SKILL.md:127,134,149` | Says "global setup" but shows a setup project; `STATE` is used in the config snippet without being imported | Fix the wording and the import |
| C29 | nit | `gherkin-step-code/references/playwright-bdd.md:117-121` | The `seededOrder` fixture reads `res.json()` without checking the status | Check the status before parsing |

### 3.3 Logical conflicts (two sources disagree)

| ID | Severity | Location | Issue | Suggested fix |
|---|---|---|---|---|
| L1 | major | `page-objects-from-url/SKILL.md:8,96,115,122,138`; `ui-test-author/playwright/SKILL.md:173,178`; `qa-ui-typescript.md:45`; `ui-test-author/selenium/SKILL.md:181` vs CLAUDE.md Comments, `ui-test-author/review/SKILL.md:165,178` | A `// TODO: missing data-testid` marker is **mandated as a contract**. CLAUDE.md bans TODO and inline comments, and the review skill files any inline or locator comment as a finding | Track fallback status only in `missing-testids.md`, keyed by page and element, and drop the in-code marker |
| L2 | major | Kebab-case suggestions at `page-objects-from-url/SKILL.md:106`; kebab examples at `ui-test-author/playwright/SKILL.md:60`, `responsive-testing/SKILL.md:90-91,161-168`, `playwright-routes.md:108` vs CLAUDE.md FE rules, `frontend/react/skills/test-ids/SKILL.md:29,59,252` and `frontend/react/skills/responsive-design/SKILL.md:141` | **Testid format.** QA suggests `<page>-<element>` kebab-case. The FE rule ("PascalCase dot-separated") and the `fe-react` consumer of `missing-testids.md` ("no kebab-case") disagree, and React's responsive-design uses `Nav.Desktop` / `Nav.Hamburger`. `responsive-testing/SKILL.md:221-223` cross-links the Blazor peer, not React. QA locators won't match what FE generates | Adopt the FE convention in all QA examples and suggestions |
| L3 | major | `flaky-test-quarantine/SKILL.md:37,74,119,211,246` (relies on native "flaky" status, `:10-12,160-162`) vs `ci-conventions/SKILL.md:52-54` (and `:8`: "the reference is wrong") and `github-actions.md:44,232,445,477`, `gitlab-ci.md:57,186,318,348`, `azure-pipelines.md:301` | **Retries.** The reporting skill says `retries: CI ? 1 : 0`. ci-conventions and all three CI references say `retries: 0`. With 0 retries, Playwright never emits "flaky", so the reporting skill's detection layer is dead. Nobody mentions `failOnFlakyTests` | Decide once in ci-conventions. If retry is 1, pair it with `failOnFlakyTests` on the gate |
| L4 | major | `test-reports/SKILL.md:70,320,334` and `ui-test-author/review/SKILL.md:99,147` vs `playwright-snapshots.md:49` and `bdd-project-scaffold/SKILL.md:104` | **Trace mode**: `retain-on-failure` vs `on-first-retry`. Given L3 (retries 0), the latter captures nothing | Standardize on `retain-on-failure` |
| L5 | major | `github-actions.md:485`, `gitlab-ci.md:357` vs `ui-test-author/playwright/SKILL.md:146-151`; reporter arrays at `test-reports:65-68`, `flaky:75`, CI `github-actions.md:232` | The CI references say `ui-test-author/playwright` owns "the `playwright.config.ts` (`blob`/`allure-playwright` reporters, `--shard`, traces)". **That skill has only a `projects` snippet.** Three different reporter arrays exist: `[['list'],['allure-playwright',{…}]]`, `[['line'],['allure-playwright']]` and `CI ? [['blob'],['allure-playwright']] : 'html'` | Add one canonical config to the UI lane (§4.2) and make the others link to it |
| L6 | major | `flaky-test-quarantine/SKILL.md:106,219` vs `test-reports/SKILL.md:105-106,157,186` (+6 more sites) | The Allure import differs between the two sibling reporting skills | Use `allure-js-commons` (D3) |
| L7 | major | `ui-test-author/playwright/SKILL.md:125-151,223-225` vs `test-login-tokens/SKILL.md:97,111` and `test-login-tokens/references/details.md:150-174` | Auth seeding: setup project + `dependencies` vs `globalSetup`. The tokens skill even says "see ui-test-author/playwright", which teaches the opposite. `test-login-tokens/references/details.md:158` also hardcodes a URL | Move test-login-tokens to a token-seeding **setup project** that uses `baseURL` |
| L8 | major | `qa-ui-typescript.md:123` vs `qa-api-typescript.md:135-140` and `docs/skills-catalog.md:30` | qa-ui hands "production probes (synthetic monitoring)" to `qa-api-typescript`, but qa-api's step table never loads `production-uptime-checks`, and the catalog lists it as an orphan | Wire it into a step (qa-api Step 3, or a qa-ui Step 3 option) |
| L9 | major | `ui-test-author/review/SKILL.md:105,121` vs CLAUDE.md "Composition over inheritance, always", `qa-ui-typescript.md:29`, `page-object-design/SKILL.md:67,217,221` | The review grades a missing `BasePage` / `BaseMobilePage` as **major**. Everything else says composition, and BasePage only with 3+ real sharers | Invert the rows: flag unearned base classes |
| L10 | minor | Testid-first at `ui-test-author/playwright/SKILL.md:171-178` and `page-objects-from-url/SKILL.md:114,136` vs `page-object-design/SKILL.md:92` and `ui-test-author/review/SKILL.md:79,144`; `ui-test-author/selenium/SKILL.md:38,181` and `ui-test-author/review/SKILL.md:57,106` | Locator order: testid-first vs role-first. The ui-test-author sample at `:57-60` itself uses role/label. Selenium uses `data-test` while Playwright `getByTestId` defaults to `data-testid` | Use one order everywhere. If Selenium keeps `data-test`, configure `testIdAttribute` as a list |
| L11 | minor | `qa-ui-typescript.md:47` vs `ui-test-author/playwright/SKILL.md:219` | Tags: `{ tag: [...] }` option vs title tags (`test('@smoke logs in')`) "or annotations" | Use the `{ tag }` option (1.42+) |
| L12 | minor | `ui-test-author/playwright/SKILL.md:192` vs `axe-playwright.md:332-333` and the `Should_X_When_Y` titles in snapshots, applitools, cdp and lighthouse | Test-title style: lowercase imperative vs `Should_X_When_Y` (axe mandates the latter) | Pick one per lane |
| L13 | minor | `api-test-author/playwright/SKILL.md:201-203,225` vs `ui-test-author/playwright/SKILL.md:161` | `toBeOK()` is banned in the API skill; the UI skill uses the even weaker `res.ok()` truthiness check | Align on exact status checks (C12) |
| L14 | minor | `api-test-author/playwright/SKILL.md:210` vs its own `:146-147` and CLAUDE.md | "Cleanup in `finally` (or `afterEach`)" | Remove `finally` |
| L15 | minor | Many examples (sites below) vs the fixture rule at `ui-test-author/playwright/SKILL.md:81`, `ui-test-author/review/SKILL.md:96` and `page-object-design/SKILL.md:223` | Specs call `new XPage(page)` directly. Sites: `playwright-snapshots.md:116,289`; `axe-playwright.md:86,216,298,308`; `applitools.md:140,297`; `percy.md:141,267`; `data-driven-testing/SKILL.md:246`; `flaky-test-quarantine/SKILL.md:224,233`; `production-uptime-checks/SKILL.md:184,189`; `lighthouse-ci.md:142` | Use fixtures in the examples |
| L16 | minor | `lighthouse-ci.md:157-161`; `proxy.md:251-261` vs `ui-test-author/playwright/SKILL.md:194,248` and `ui-test-author/review/SKILL.md:77` (blocker) | Tests that assert nothing | Add an explicit assertion |
| L17 | minor | `playwright-snapshots.md:308` vs `ci-conventions/SKILL.md:25-26` | Visual regression "on every PR" vs gated to the nightly schedule | Align with ci-conventions |
| L18 | minor | `test-reports/SKILL.md:247-248,284,288` vs `ci-conventions/SKILL.md:77` | Allure CLI 2.27.0 vs 2.30.0 | Single pin |
| L19 | minor | `responsive-testing/SKILL.md:64-65,204-205` vs `:87,144` | "Never `setViewportSize` per test", but the core pattern does exactly that | Use `test.use({ viewport })` per row in a `describe` |
| L20 | minor | `playwright-snapshots.md:124-126` vs `:136-137,292` | "`toHaveScreenshot` waits for fonts", then explicit `document.fonts.ready` waits anyway | Remove the redundant waits |
| L21 | minor | `network-mocking/SKILL.md:3` vs `playwright-routes.md:53` and `realtime-stream-testing/SKILL.md:215-250` | WebSocket mocking has two owners | Make realtime the owner; routes links to it |
| L22 | minor | `qa-ui-typescript.md:114` vs `accessibility-testing/SKILL.md:30` | Step 3 loads a11y `references/lighthouse-ci.md` but not `axe-playwright.md`, which the a11y skill calls "the gate" | List both, or just the SKILL.md router |
| L23 | minor | `playwright-routes.md:25-26,52,269,334-335`; `cdp.md:25,27,314,316`; `proxy.md:5`; `github-actions.md:324`; `flaky-test-quarantine/SKILL.md:268,270` | Self-referential or stale cross-refs: `qa/typescript/skills/network-mocking` used to mean cdp.md / proxy.md; `` `cdp/typescript` ``; `` `azure-pipelines/typescript` ``; `qa-_shared-quality-metrics` (real name `qa-quality-metrics`); "(#?)" | Point at `references/<tool>.md` and the real names |
| L24 | minor | `qa-api-typescript.md:139` | A dangling "(Toxiproxy …)" parenthetical is attached to the feature-flag item instead of resilience | Move it |
| L25 | nit | `qa-ui-typescript.md:145` | The brownfield example lists ".NET8 / Java21" stacks (copied from siblings) | Fix the example |
| L26 | nit | `ui-test-author/review/SKILL.md:198` | The cleanup rule ("none in cleanup hook") is stricter than CLAUDE.md, which allows try/catch in teardown I/O helpers | Note the deviation once |

---

## 4. Structural observations

### 4.1 Guidance that needs one owner

1. **Locator policy is stated in five places, in three orders:**
   - `ui-test-author/playwright/SKILL.md:171-178`
   - `page-objects-from-url/SKILL.md:112-115,134-138`
   - `page-object-design/SKILL.md:87-92`
   - `ui-test-author/review/SKILL.md:57,79,144`
   - `ui-test-author/selenium/SKILL.md:38,181`

   Owner: `ui-test-author/playwright` for the mechanics; everything else should link to it.
2. **The `playwright.config.ts` and evidence settings are split across five skills** (test-reports, review, snapshots, bdd-scaffold, the CI references) with no owner in the UI lane (L4, L5).
3. **Allure attach helpers are re-implemented six times:** axe, lighthouse, snapshots, percy, applitools and browser-cloud. They should collapse to one helper in `test-reports`, plus `testInfo.attach` for native evidence.
4. **Retry and flake policy is spread over `flaky-test-quarantine`, the three CI references and `ci-conventions`** (L3). `ci-conventions` already declares itself the authority; the reporting skill must defer to it.
5. **Auth seeding is in two places:** ui-test-author (setup project) and test-login-tokens (globalSetup) (L7).
6. **WebSocket mocking is in two places:** network-mocking and realtime (L21).
7. **The no-`waitForTimeout` / web-first rules are restated in about 12 references.** That is fine as reinforcement but drifts easily: C1 and C10 contradict them inside the same lane.

### 4.2 Owner for a new "evidence capture" topic (screenshots, video, trace)

**Recommendation:** add `qa/typescript/skills/ui-test-author/playwright/references/config-and-evidence.md`, and give it one canonical `playwright.config.ts`. The config should cover:

- `retries` per L3, `forbidOnly`, `fullyParallel` and `workers`
- `reporter` per environment
- `trace` / `video` / `screenshot` as modes and as object forms (`{mode,size,fps}`, `{mode,snapshots,screenshots,sources}`, `{mode,fullPage}`)
- `snapshotPathTemplate`, `updateSnapshots` for CI, `testIdAttribute`, `webServer` and `failOnFlakyTests`

It should also cover:

- `testInfo.attach` and `step.attach`
- `test.step` options (`box`, `timeout`)
- `tracing.group`
- trace viewer use (`npx playwright show-trace`, `show-report`, UI mode)
- HAR via `recordHar` in `contextOptions`, or `tracing.startHar()` on 1.60+

Why this skill should own it:

- **The CI references already point there for the config** (`github-actions.md:485`, `gitlab-ci.md:357`).
- **qa-ui Step 2 and qa-bdd Step 4 already load that skill.**
- **qa-ui may not load `qa/reporting/*`** (`qa-ui-typescript.md:18`), so the native evidence config cannot live in `test-reports`.

`test-reports` keeps only the Allure mapping and links back. `ui-test-author/review` gains matching rows for each setting.

### 4.3 Owner for a "locator scoping" topic

**Recommendation:** add a "Locators: scope, filter, chain" section to `ui-test-author/playwright` as the single mechanics owner. It should cover:

- `filter({ has, hasNot, hasText, hasNotText, visible })`
- `and()` / `or()`
- chaining from a component root
- `locator.within()`: needs 1.64+; below that use `parent.locator(child)` or `filter({ has })`
- `frameLocator` / `contentFrame`
- strictness, and a ban on positional `nth()` / `first()`
- `describe()`
- `addLocatorHandler` for overlays

The other skills keep narrower roles:

- `page-object-design:91` keeps the *design* rule (a component takes its parent `Locator`) and links to the mechanics.
- `page-objects-from-url` keeps extraction.
- `ui-test-author/review` adds rows for unscoped `getByText` hitting multiple elements, positional `nth`, and missing `filter`.

### 4.4 Owner for a "WebMCP testing" topic

**Recommendation:** a new skill, `qa/typescript/skills/webmcp-testing/SKILL.md` (frontmatter `name: qa-webmcp-testing-typescript`), loaded by **qa-ui-typescript Step 3 (specialized layers)**.

Why a new skill:

- It is a **deterministic, browser-hosted tool-contract test.** It checks the tool list, names, `inputSchema` and annotations via `page.webmcp.tools()`, and the behaviour of `page.webmcp.callTool()`, including errors.
- **It is not an LLM eval.** That keeps it out of qa-llm.
- **It needs its own setup:**
  - a dedicated Chromium project with `launchOptions.args: ['--enable-features=WebMCP']`
  - Firefox needs the `dom.modelcontext.*` prefs; WebKit is unsupported
  - a ≥ 1.64 version floor
  - an "experimental API" caveat

Cross-links:

- `tooling/_shared/capability-contract` (`tool-capability-contract`), the source of the expected contract
- `ai-feature-testing`, for agent-in-the-loop evals
- `qa-security`, because tool descriptions are untrusted input (prompt injection)

`page-objects-from-url` should also note that Playwright MCP 0.0.83 exposes page WebMCP tools as `webmcp_<tool>` by default. Run extraction with `--no-webmcp` or treat those tools as untrusted.

### 4.5 How agents load skills, and the checklist for wiring a new one

**How loading works:**

1. A command only tells the session to `Read` the agent and follow it (`qa/typescript/commands/qa-ui-typescript.md:8-10`).
2. The agent's skill-loading protocol (`qa-ui-typescript.md:16-25`) says:
   - before step N, `Read` every `SKILL.md` in that step's "Skills to load" cell;
   - the skills root is `qa/typescript/skills/`;
   - `qa/manual|reporting|cicd|security` are off-limits;
   - `ep-agent-orientation-cache` and `ep-code-comments` are always loaded.
3. The Steps table is at `qa-ui-typescript.md:110-115`:
   - Step 1, Foundations: `:112`
   - Step 2, Author: `:113`
   - Step 3, Specialized layers: `:114`
   - Step 4, Review: `:115`
4. qa-bdd uses its own table (`qa-bdd-typescript.md:104-107`).
5. Paths abbreviated with `…/` still resolve, e.g. `…/ui-test-author/selenium/SKILL.md` at `:113`.

**To wire a new skill:**

1. Create `qa/typescript/skills/<name>/SKILL.md` with frontmatter `name: qa-<name>-typescript` and a trigger-rich `description`.
2. Add its path to the right row of `qa-ui-typescript.md:112-115`, and to `qa-bdd-typescript.md:104-107` if BDD needs it.
3. Add `./qa/typescript/skills/<name>` to the qa-typescript `skills` list in `.claude-plugin/marketplace.json:328-406`. Skills are enumerated explicitly there.
4. Add or extend the row in `docs/skills-catalog.md` (around `:58-111`, using the "— java · dotnet · typescript" convention).
5. Add matching review rows in `ui-test-author/review/SKILL.md`.
6. Decide on java/dotnet sibling parity, per the catalog convention.

**Orphans today:**

- `inhouse-framework-conventions` and `production-uptime-checks`: confirmed by `docs/skills-catalog.md:30`.
- `security-testing/{passive-scan,permission-testing}`: reached only via `qa-security`'s `<stack>:` notation (`qa/_shared/agents/qa-security.md:28,98-99`).

---

## 5. Totals

| Class | blocker | major | minor | nit |
|---|---|---|---|---|
| Data issues (D1–D13, G1–G6) | 0 | 5 | 14 | 0 |
| Code issues (C1–C29) | 0 | 10 | 16 | 3 |
| Logical conflicts (L1–L26) | 0 | 9 | 15 | 2 |
| **Total** | **0** | **24** | **45** | **5** |

There are no blockers in the skills themselves. C8 would produce blocker-graded code in a consuming suite, because agents copy the floating-promise helpers verbatim.
