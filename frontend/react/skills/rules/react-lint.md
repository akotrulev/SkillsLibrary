---
paths:
  - "**/eslint.config.{js,mjs,cjs,ts,mts,cts}"
  - "**/tsconfig*.json"
---

<!-- fe-react rules v1 (2026-11-21): lint. Ids checked against the tools' documentation on 2026-11-21 (ESLint 9, typescript-eslint 8, TypeScript 6, eslint-plugin-react-hooks 7, eslint-plugin-react 7, eslint-plugin-jsx-a11y 6, eslint-config-next 15 and 16). Installed by /fe-react:rules; edit the paths above to where this app keeps its ESLint config, re-run to compare with the plugin's copy. -->

# React lint standards

Severity tags as in the core React rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `react.md` or `react-tests.md` that ESLint or `tsc` detects, so the build catches it before a review does. Rules no stock rule detects stay in those files and get no row: no fetch started in the render body, effect cleanup, `window` or `Date.now()` read during render, `router.push` on a `div`, server data copied into a store, the three-state region.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| Hooks at the top level only (`react.md`, Hooks and effects) | `eslint-plugin-react-hooks` | `react-hooks/rules-of-hooks` | error |
| Exhaustive effect deps (`react.md`, Hooks and effects) | `eslint-plugin-react-hooks` | `react-hooks/exhaustive-deps` | error |
| No effect to derive state or copy props into state (`react.md`, Hooks and effects) | `eslint-plugin-react-hooks` 7 | `react-hooks/set-state-in-effect` | error |
| No component defined inside another (`react.md`, Rendering and state) | `eslint-plugin-react-hooks` 7 | `react-hooks/static-components` | error |
| `key` is a stable domain id, never the array index (`react.md`, Rendering and state) | `eslint-plugin-react` | `react/no-array-index-key` | error |
| A Context `value` is memoized (`react.md`, Rendering and state) | `eslint-plugin-react` | `react/jsx-no-constructed-context-values` | error |
| `target="_blank"` only with `rel="noopener"` (`react.md`, Markup, accessibility and navigation) | `eslint-plugin-react` | `react/jsx-no-target-blank`, `allowReferrer: true` | error |
| `<button>` for actions, never `<div onClick>` (`react.md`, Markup, accessibility and navigation) | `eslint-plugin-jsx-a11y` | `jsx-a11y/no-static-element-interactions`, `jsx-a11y/click-events-have-key-events` | error |
| Every image has `alt` (`react.md`, Markup, accessibility and navigation) | `eslint-plugin-jsx-a11y` | `jsx-a11y/alt-text` | error |
| Every input has a label (`react.md`, Markup, accessibility and navigation) | `eslint-plugin-jsx-a11y` | `jsx-a11y/label-has-associated-control` | error |
| No `tabIndex` above 0 (`react.md`, Markup, accessibility and navigation) | `eslint-plugin-jsx-a11y` | `jsx-a11y/tabindex-no-positive` | error |
| A destructive action never uses `window.confirm` (`react.md`, Data regions and UI correctness) | ESLint core | `no-alert` | error |
| No `any` or `as any` (`react.md`, Components and types) | typescript-eslint | `@typescript-eslint/no-explicit-any` | error |
| An `any` value never flows into a typed one (`react.md`, Components and types) | typescript-eslint | `@typescript-eslint/no-unsafe-assignment`, `no-unsafe-argument`, `no-unsafe-call`, `no-unsafe-member-access`, `no-unsafe-return` | error |
| No `as unknown as X` (`react.md`, Components and types) | ESLint core | `no-restricted-syntax`, the `as unknown as` selector | error |
| `@ts-expect-error` states its reason and `@ts-ignore` is never used (`react.md`, Components and types) | typescript-eslint | `@typescript-eslint/ban-ts-comment`, `ts-expect-error: 'allow-with-description'`, `ts-ignore: true` | error |
| `eslint-disable` states its reason (`react.md`, Hooks and effects) | `@eslint-community/eslint-plugin-eslint-comments` | `@eslint-community/eslint-comments/require-description` | error |
| A test body is linear: no `try`, `if`, `switch`, loop or ternary (`react-tests.md`) | ESLint core | `no-restricted-syntax`, the control-flow selectors, in test files | error |
| A test queries by role or label, never `container.querySelector` (`react-tests.md`) | ESLint core | `no-restricted-syntax`, the `querySelector` selector, in test files | error |
| A test waits with `findBy*` or `waitFor`, never a timer (`react-tests.md`) | ESLint core | `no-restricted-globals`, `setTimeout`, in test files | error |
| Every `userEvent` call is awaited (`react-tests.md`) | typescript-eslint | `@typescript-eslint/no-floating-promises` | error |
| `strict` is on (`react.md`, Components and types) | `tsc` | `"strict": true` in `tsconfig.json` | setting |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `'<id>': 'error'` in `eslint.config.*`, under `files: ['**/*.{ts,tsx}']`. The config below lists the rows alone.
- **Next.js 16** — `eslint-config-next/core-web-vitals` registers `react`, `react-hooks`, `jsx-a11y` and `@next/next`, sets `rules-of-hooks`, `set-state-in-effect` and `static-components` to `error`, and ignores `.next/**`, `out/**`, `build/**` and `next-env.d.ts`. It sets `exhaustive-deps` and `alt-text` to `warn` and `jsx-no-target-blank` to `off`, so those three rows are the ones the project must raise. Checked with 16.4.6.
- **Next.js 15** — `eslint-config-next@15` extends through `FlatCompat` (`compat.extends('next/core-web-vitals')`) and ships `eslint-plugin-react-hooks` 5, which has neither `set-state-in-effect` nor `static-components`. The project adds `eslint-plugin-react-hooks` 7 and registers it in a config object after the compat entries (`plugins: { 'react-hooks': reactHooks }`). Checked with 15.5.29 and plugin 7.1.1.
- **Vite lane** — nothing registers the plugins. Replace `...nextVitals` with `reactHooks.configs.flat.recommended`, and add `react`, `jsx-a11y` and `@typescript-eslint: tseslint.plugin` to `plugins` and `parser: tseslint.parser` to `languageOptions`. All rows fire on that setup.
- ESLint 9, not 10: `eslint-plugin-react` and `eslint-plugin-jsx-a11y` declare ESLint 9 as their highest peer, and `npm install` refused ESLint 10 beside them on 2026-11-21.
- `recommended` also turns on the compiler rules `purity`, `refs`, `immutability` and the rest of the plugin's set. They are not rows: no house rule names them.
- `no-unsafe-*`, `no-floating-promises` and the other typed rules need `languageOptions.parserOptions.projectService: true`. A file outside every `tsconfig` `include` fails with a parsing error instead of skipping the rule, so test files belong in the `include`. In a monorepo set `tsconfigRootDir` to the app.
- typescript-eslint 8.73 declares TypeScript from 4.8.4 up to but not including 6.1 as its peer range, so the typed rows run on TypeScript 5 and 6, and a project on TypeScript 7 waits for a plugin release that widens it.
- `no-restricted-syntax` and `no-restricted-globals` take one options array per file, and the later config object replaces the earlier one's array, so the test block repeats the production selector.
- ESLint does not skip generated code beyond what the preset ignores: a generated API client under `src/generated/` reports `no-explicit-any` until the folder is in `ignores`, so the config lists it.
- A suppression leaves one way out: the reason after `--` (`// eslint-disable-next-line react-hooks/exhaustive-deps -- the effect must run once on mount`).

`eslint.config.mjs` (Next.js 16; ESLint 9.22 or later):

```js
import { defineConfig } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import eslintComments from '@eslint-community/eslint-plugin-eslint-comments';

const doubleCast = {
  selector: "TSAsExpression[expression.type='TSAsExpression'][expression.typeAnnotation.type='TSUnknownKeyword']",
  message: 'No as unknown as X: narrow the value or fix the type',
};

const linearTest = [
  doubleCast,
  { selector: 'CallExpression[callee.property.name=/^querySelector(All)?$/]', message: 'Query by role or label, never by selector' },
  ...['TryStatement', 'IfStatement', 'SwitchStatement', 'ForStatement', 'ForInStatement', 'ForOfStatement', 'WhileStatement', 'DoWhileStatement', 'ConditionalExpression'].map(
    (selector) => ({ selector, message: 'A test body is linear: no branch, loop or try' }),
  ),
];

export default defineConfig(
  { ignores: ['src/generated/**'] },
  ...nextVitals,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { parserOptions: { projectService: true } },
    plugins: { '@eslint-community/eslint-comments': eslintComments },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
      'react-hooks/set-state-in-effect': 'error',
      'react-hooks/static-components': 'error',
      'react/no-array-index-key': 'error',
      'react/jsx-no-constructed-context-values': 'error',
      'react/jsx-no-target-blank': ['error', { allowReferrer: true }],
      'jsx-a11y/no-static-element-interactions': 'error',
      'jsx-a11y/click-events-have-key-events': 'error',
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/label-has-associated-control': 'error',
      'jsx-a11y/tabindex-no-positive': 'error',
      'no-alert': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'error',
      '@typescript-eslint/no-unsafe-argument': 'error',
      '@typescript-eslint/no-unsafe-call': 'error',
      '@typescript-eslint/no-unsafe-member-access': 'error',
      '@typescript-eslint/no-unsafe-return': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/ban-ts-comment': ['error', { 'ts-expect-error': 'allow-with-description', 'ts-ignore': true, 'ts-nocheck': true, minimumDescriptionLength: 10 }],
      '@eslint-community/eslint-comments/require-description': 'error',
      'no-restricted-syntax': ['error', doubleCast],
    },
  },
  {
    files: ['**/*.{test,spec}.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': ['error', ...linearTest],
      'no-restricted-globals': ['error', { name: 'setTimeout', message: 'Wait with findBy or waitFor' }],
    },
  },
);
```
