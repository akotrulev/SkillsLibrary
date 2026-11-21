---
paths:
  - "**/eslint.config.{js,mjs,cjs,ts,mts,cts}"
  - "**/tsconfig*.json"
---

<!-- qa-typescript rules v1 (2026-11-21): lint. Ids checked against the tools' documentation on 2026-11-21 (ESLint 9, typescript-eslint 8, TypeScript 6, eslint-plugin-playwright 2.12 for Playwright 1.64, eslint-plugin-eslint-comments 4). Installed by /qa-typescript:rules; edit the paths above to where this project keeps its ESLint config, re-run to compare with the plugin's copy. -->

# TypeScript test lint standards

Severity tags as in the core qa-typescript rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `qa-typescript.md` or `ui-tests.md` that ESLint or `tsc` detects, so the build catches it before a review does. Rules no stock rule detects stay in those files and get no row: one expected value per assertion (`expect(a || b)` passes `no-conditional-in-test`), a page object that exposes intent, a skip's ticket, a data variant written as a loop in a fixture.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `waitForTimeout` (`qa-typescript.md`, Waiting and async) | eslint-plugin-playwright | `playwright/no-wait-for-timeout` | error |
| No `setTimeout` promise, `browser.pause` or `timers/promises` sleep (`qa-typescript.md`, Waiting and async) | ESLint core | `no-restricted-globals` (`setTimeout`), `no-restricted-properties` (`browser.pause`), `no-restricted-imports` (`timers/promises`), in spec files | error |
| A test body has no `if`, `switch` or ternary (`qa-typescript.md`, Tests) | eslint-plugin-playwright | `playwright/no-conditional-in-test` | error |
| No `expect` inside a conditional or a `catch` (`qa-typescript.md`, Tests) | eslint-plugin-playwright | `playwright/no-conditional-expect` | error |
| A test body has no loop and no `try` (`qa-typescript.md`, Tests) | ESLint core | `no-restricted-syntax`, the loop and `TryStatement` selectors, in spec files | error |
| No `.only` (`ui-tests.md`, `forbidOnly`) | eslint-plugin-playwright | `playwright/no-focused-test` | error |
| A skip is conditional and carries its reason; `fixme` is never a quarantine (`qa-typescript.md`, Flakes and reporting) | eslint-plugin-playwright | `playwright/no-skipped-test`, `allowConditional: true`, `disallowFixme: true`; `playwright/require-annotation-reason` | error |
| Every test asserts (`qa-typescript.md`, Tests) | eslint-plugin-playwright | `playwright/expect-expect` | error |
| No `networkidle`, `force: true` or `waitForNavigation` (`ui-tests.md`) | eslint-plugin-playwright | `playwright/no-networkidle`, `playwright/no-force-option`, `playwright/no-wait-for-navigation` | error |
| Web-first assertions: no one-shot read compared later (`ui-tests.md`) | eslint-plugin-playwright, ESLint core | `playwright/prefer-web-first-assertions`, `playwright/prefer-to-have-count`; `no-restricted-syntax`, the `expect(page.url())` selector | error |
| Every Playwright matcher, `test.step` and `waitFor*` is awaited (`qa-typescript.md`, Waiting and async) | eslint-plugin-playwright | `playwright/missing-playwright-await` | error |
| Every promise is awaited (`qa-typescript.md`, Waiting and async) | typescript-eslint | `@typescript-eslint/no-floating-promises` | error |
| No `any` (`qa-typescript.md`, Waiting and async) | typescript-eslint | `@typescript-eslint/no-explicit-any` | error |
| No `@ts-ignore`; `@ts-expect-error` states its reason (`qa-typescript.md`, Waiting and async) | typescript-eslint | `@typescript-eslint/ban-ts-comment`, `ts-expect-error: 'allow-with-description'`, `ts-ignore: true` | error |
| `eslint-disable` states its reason (`qa-typescript.md`, Waiting and async) | `@eslint-community/eslint-plugin-eslint-comments` | `@eslint-community/eslint-comments/require-description` | error |
| No `as unknown as X` (`qa-typescript.md`, Waiting and async) | ESLint core | `no-restricted-syntax`, the `as unknown as` selector | error |
| No empty `catch` block and no `.catch(() => {})` (`qa-typescript.md`, Errors) | ESLint core | `no-empty`; `no-restricted-syntax`, the empty `.catch` selector | error |
| `strict` is on (`qa-typescript.md`, Waiting and async) | `tsc` | `strict: true` in `tsconfig.json` | setting |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `'<id>': 'error'` in `eslint.config.*`, under `files: ['**/*.ts']` for the typescript-eslint, comments and empty-`catch` rows and under `files: ['**/*.spec.ts']` for the Playwright and test-body rows. The config below lists the rows alone. The plugin's `flat/recommended` preset turns on every Playwright row except `require-annotation-reason`, with `no-skipped-test` on its defaults (it then flags every skip, conditional ones too), and adds rules no row asks for.
- `no-floating-promises` reads types, so it needs `languageOptions.parserOptions.projectService: true`, and a file outside every `tsconfig` `include` fails with a parsing error instead of skipping the rule. The Playwright rules read names only: `test`, `expect`, `page`. An assertion helper a spec calls instead of `expect` goes in `expect-expect`'s `assertFunctionNames`.
- `no-restricted-syntax`, `-globals`, `-properties` and `-imports` take one options array per config object, and a later object replaces an earlier one's array. The spec block repeats the `.ts` block's two selectors.
- A loop, a `try` and a sleep are banned only in `*.spec.ts`. A fixture, page object, client, probe or teardown registry loops, branches and catches by the house rules. The empty `.catch` and `as unknown as` selectors apply to every `.ts` file.
- `no-conditional-in-test` flags `if`, `switch` and the ternary, not `||` or `&&` inside an `expect` argument. `no-skipped-test` with `allowConditional: true` passes `test.skip(isMobile, 'WET-204 layout')` and flags a bare `test.skip()`, `test.skip('title', fn)` and `test.fixme(…)`; `require-annotation-reason` fails the conditional form without its reason. The ticket in the reason is a review check.
- `no-floating-promises` flags an un-awaited `page.click()`, and `missing-playwright-await` flags an un-awaited matcher; both report an un-awaited `expect(…).toHaveURL(…)`, once each.
- The `tsc` row is read from `tsconfig.json`, and the `typecheck` script runs `tsc --noEmit` in CI, since ESLint does not report type errors.
- ESLint does not skip generated code: it lints every file `ignores` does not name. A generated client under `src/generated/` reports `no-explicit-any` until the folder is in `ignores`, so the config lists it with the `playwright-bdd` output folder.
- The rule ids exist in `eslint-plugin-playwright` 2.12, which asks only for ESLint 8.40 or later and does not depend on the Playwright version; the rows hold for the 1.64 lane and for a Selenium or WebdriverIO suite that uses the non-Playwright rows.

`eslint.config.mjs` (ESLint 9.22 or later):

```js
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import playwright from 'eslint-plugin-playwright';
import eslintComments from '@eslint-community/eslint-plugin-eslint-comments';

const emptyCatch = {
  selector: "CallExpression[callee.property.name='catch'] > :matches(ArrowFunctionExpression, FunctionExpression)[body.body.length=0]",
  message: 'A caught error is handled or reaches the runner, never swallowed',
};
const doubleCast = {
  selector: "TSAsExpression[expression.type='TSAsExpression'][expression.typeAnnotation.type='TSUnknownKeyword']",
  message: 'No as unknown as X: narrow the value or fix the type',
};
const urlRead = {
  selector: "CallExpression[callee.name='expect'] > CallExpression[callee.property.name='url']",
  message: 'Assert the URL with await expect(page).toHaveURL()',
};
const linearBody = ['TryStatement', 'ForStatement', 'ForInStatement', 'ForOfStatement', 'WhileStatement', 'DoWhileStatement'].map(
  (selector) => ({ selector, message: 'A test body is linear: no loop or try' }),
);
const sleepImports = ['timers/promises', 'node:timers/promises'].map((name) => ({ name, message: 'Wait on a condition, never sleep' }));

export default defineConfig(
  { ignores: ['src/generated/**', '.features-gen/**'] },
  {
    files: ['**/*.ts'],
    languageOptions: { parser: tseslint.parser, parserOptions: { projectService: true } },
    plugins: { '@typescript-eslint': tseslint.plugin, '@eslint-community/eslint-comments': eslintComments },
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/ban-ts-comment': ['error', { 'ts-expect-error': 'allow-with-description', 'ts-ignore': true, 'ts-nocheck': true, minimumDescriptionLength: 10 }],
      '@eslint-community/eslint-comments/require-description': 'error',
      'no-empty': 'error',
      'no-restricted-syntax': ['error', emptyCatch, doubleCast],
    },
  },
  {
    files: ['**/*.spec.ts'],
    plugins: { playwright },
    rules: {
      'playwright/expect-expect': 'error',
      'playwright/no-wait-for-timeout': 'error',
      'playwright/no-conditional-in-test': 'error',
      'playwright/no-conditional-expect': 'error',
      'playwright/no-focused-test': 'error',
      'playwright/no-skipped-test': ['error', { allowConditional: true, disallowFixme: true }],
      'playwright/require-annotation-reason': 'error',
      'playwright/no-networkidle': 'error',
      'playwright/no-force-option': 'error',
      'playwright/no-wait-for-navigation': 'error',
      'playwright/prefer-web-first-assertions': 'error',
      'playwright/prefer-to-have-count': 'error',
      'playwright/missing-playwright-await': 'error',
      'no-restricted-syntax': ['error', emptyCatch, doubleCast, urlRead, ...linearBody],
      'no-restricted-globals': ['error', { name: 'setTimeout', message: 'Wait on a condition, never sleep' }],
      'no-restricted-properties': ['error', { object: 'browser', property: 'pause', message: 'Wait on a condition, never sleep' }],
      'no-restricted-imports': ['error', ...sleepImports],
    },
  },
);
```
