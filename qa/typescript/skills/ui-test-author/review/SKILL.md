---
name: ui-tests-review
description: Use when reviewing existing TypeScript UI test code or page objects (Playwright, Selenium, Appium). Triggers "review this Playwright spec". Not for writing new tests (ui-tests-playwright).
---

# QA — UI Test & Page Object Reviewer (TypeScript)

Reviews TypeScript UI test code (Playwright Test, Selenium WebDriverJS / WebdriverIO, Appium with
WebdriverIO, Maestro flows) against the qa-typescript rule files. Produces a findings table in the
`CLAUDE.md` format. **Does not rewrite the code** — it points to the fix and lets the human apply it.

The Playwright know-how behind those rules is `qa/typescript/skills/ui-test-author/playwright`:
locators in `references/locators.md`, assertions in `references/assertions.md`, the config in
`references/config-and-fixtures.md`.

## When to use

- A diff or file (page object, `.spec.ts`, fixture, config, base class) is submitted for review
- Pre-merge gate on a PR touching `tests/`, `e2e/`, `pages/` or `pageObjects/`

## When NOT to use

- Generating new code → `qa/typescript/skills/ui-test-author/playwright`, `…/selenium`, `…/appium`, `…/maestro`
- Architecting the POM → `qa/typescript/skills/page-object-design`
- API tests → `qa/typescript/skills/api-test-author/review`
- .NET or Java UI code → `qa/dotnet/skills/ui-test-author/review`, `qa/java/skills/ui-test-author/review`

## Inputs needed

1. **Stack** — Playwright TS, Selenium WebDriverJS / WebdriverIO, WebdriverIO + Appium, or Maestro
2. **Files** — page objects, `*.spec.ts`, fixtures, `playwright.config.ts`, base classes, or a `.maestro/` workspace
3. **Context** — new feature, refactor or bug fix
4. **Project conventions** that override the stack defaults (a different test-id attribute, a mandated lint plugin)

## Output format

```
| Severity | Location                    | Issue                                              | Suggested fix                                         |
|----------|-----------------------------|----------------------------------------------------|-------------------------------------------------------|
| blocker  | tests/specs/cart.spec.ts:42 | `page.waitForTimeout(2000)` — arbitrary sleep      | Assert the state: `await expect(cart.total).toHaveText('€40.00')` |
| blocker  | pages/LoginPage.ts:18       | `expect` inside a page-object method               | Expose the locator; assert in the spec                |
| major    | pages/ProductPage.ts:31     | `page.locator('.btn-primary')` on an element with a test id | `page.getByTestId('Product.AddToCart')`       |
| minor    | pages/CartPage.ts:55        | The same locator re-typed in three methods         | Promote to a `readonly cartBadge: Locator` field      |
```

Severities (from `CLAUDE.md`):

- **blocker** — ships a bug, breaks the build, or violates a hard rule (`waitForTimeout`, `expect` in page objects, shared driver, raw credentials, floating promises)
- **major** — a design or correctness issue that will hurt soon (brittle or unscoped locators, `force: true`, `networkidle`, one-shot reads)
- **minor** — style or a small inconsistency (naming, a missing constant)
- **nit** — optional preference

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator.

End with one line: `Rules: project .claude/rules/qa-typescript/ | plugin copy (not installed)`.

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the qa-typescript rule files `qa-typescript.md` (core), plus `ui-tests.md` for Playwright, Selenium and WebdriverIO web suites, `mobile-tests.md` for Appium screens and Maestro flows, and `bdd.md` when step definitions are in the diff.

1. **The project's copies first**: `.claude/rules/qa-typescript/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/typescript/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-typescript:rules` installs them.

Read `qa-typescript.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version policy

Detect the stack from imports and config files, and the versions from `package.json`: `@playwright/test` (1.64 on this lane), WebdriverIO and Appium majors, Maestro CLI. Do not flag a suite for lacking an API its pinned version does not have (`locator.within()` needs 1.64; a device cloud on Appium 2 stays on WebdriverIO 9). The rule files' "the codebase wins" line applies: a convention the suite follows consistently (a different test-id attribute, a mandated lint plugin) is not a finding.

## Good signals (TypeScript)

The shape of `ui-test-author/playwright/assets/`: intent-revealing page methods, scoped `readonly`
locators on the highest ladder rung, `Should_X_When_Y` tests on fixtures with `{ tag }`, web-first
assertions with a subject, an auth setup project, seeded data deleted in fixture teardown.

## The locator corollary

A comment explaining a locator (`// the third span is the price`) is evidence the locator is **positional and brittle**, not a comment finding. File it under the locator rules: request a test id and record it in `missing-testids.md`.

## Procedure

1. Identify the **stack** from imports and config files, and the Playwright version from `package.json`.
2. Read each file end to end before writing findings — context sets severity.
3. Walk the rules: waits, async and assertions in page objects first, where most blockers live, then locators, then the rest.
4. For each finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
5. **Do not rewrite the code.** Hand off to the generator if the user asks for a rewrite.

## Handoffs

- Rewrite → `qa/typescript/skills/ui-test-author/playwright`, `…/selenium`, `…/appium` or `…/maestro`
- Architecture is the real problem → `qa/typescript/skills/page-object-design`
- Test data shape → `qa/typescript/skills/test-data-builder`
- API tests in the same PR → `qa/typescript/skills/api-test-author/review`
- Evidence settings beyond the config defaults → `qa/typescript/skills/evidence-capture`
- Allure reporting → `qa/reporting/typescript/skills/test-reports`
- A rule is missing or wrong → edit the project's `.claude/rules/qa-typescript/`; for every project, the plugin's `qa/typescript/skills/rules/`
