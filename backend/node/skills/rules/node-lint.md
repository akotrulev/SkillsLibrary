---
paths:
  - "**/eslint.config.{js,mjs,cjs,ts,mts,cts}"
  - "**/tsconfig*.json"
---

<!-- be-node rules v1 (2026-11-21): lint. Ids checked against the tools' documentation on 2026-11-21 (ESLint 9 and 10, typescript-eslint 8, TypeScript 6, eslint-plugin-eslint-comments 4). Installed by /be-node:rules; edit the paths above to where this project keeps its ESLint config, re-run to compare with the plugin's copy. -->

# Node backend lint standards

Severity tags as in the core be-node rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `node.md`, `node-persistence.md`, `node-tests.md` or `node-config.md` that ESLint or `tsc` detects, so the build catches it before a review does. Rules no stock rule detects stay in those files and get no row: constructor injection, mutable module-level state, a `catch` that swallows, a `Promise<T> | T` signature, independent awaits that belong in `Promise.all`, `req.body as Dto`.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `any` or `as any` (`node.md`, Types) | typescript-eslint | `@typescript-eslint/no-explicit-any` | error |
| An `any` value never flows into a typed one (`node.md`, Types) | typescript-eslint | `@typescript-eslint/no-unsafe-assignment`, `no-unsafe-argument`, `no-unsafe-call`, `no-unsafe-member-access`, `no-unsafe-return` | error |
| No `as unknown as X` (`node.md`, Types; `node-tests.md`) | ESLint core | `no-restricted-syntax`, the `as unknown as` selector | error |
| No `!` non-null assertion (`node.md`, Types) | typescript-eslint | `@typescript-eslint/no-non-null-assertion` | error |
| A `switch` over a closed set covers every case and has no fallback `default` (`node.md`, Types) | typescript-eslint | `@typescript-eslint/switch-exhaustiveness-check`, `allowDefaultCaseForExhaustiveSwitch: false` | error |
| No floating promise: every promise is awaited or given an error path (`node.md`, Errors and async; `node-tests.md`) | typescript-eslint | `@typescript-eslint/no-floating-promises` | error |
| No promise where nothing handles it: an `async` callback to `forEach` or an event handler, a promise in an `if` (`node.md`, Errors and async) | typescript-eslint | `@typescript-eslint/no-misused-promises` | error |
| `@ts-expect-error` states its reason and `@ts-ignore` is never used (`node.md`, Comments; `node-tests.md`) | typescript-eslint | `@typescript-eslint/ban-ts-comment`, `ts-expect-error: 'allow-with-description'`, `ts-ignore: true` | error |
| `eslint-disable` states its reason (`node.md`, Comments) | `@eslint-community/eslint-plugin-eslint-comments` | `@eslint-community/eslint-comments/require-description` | error |
| No `console.log`: one logger (`node.md`, Logging, telemetry and secrets) | ESLint core | `no-console` | error |
| No `process.env` outside `loadConfig()` (`node.md`, Boundaries, DI and state) | ESLint core | `no-restricted-properties`, `process.env`, with the config folder exempt | error |
| Raw SQL is a tagged template, never `$queryRawUnsafe` or `$executeRawUnsafe` (`node-persistence.md`) | ESLint core | `no-restricted-properties`, `$queryRawUnsafe` and `$executeRawUnsafe` | error |
| A test body is linear: no `try`, `if`, `switch`, loop or ternary (`node-tests.md`) | ESLint core | `no-restricted-syntax`, the control-flow selectors, in test files | error |
| A test never waits on `setTimeout` (`node-tests.md`) | ESLint core | `no-restricted-globals`, `setTimeout`, in test files | error |
| `strict`, `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` are on (`node-config.md`) | `tsc` | those three options in `tsconfig.json` | setting |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `'<id>': 'error'` in `eslint.config.*`, under `files: ['**/*.ts']`. The config below lists the rows alone. `strictTypeChecked` sets every `@typescript-eslint` row to `error` except `switch-exhaustiveness-check`, which no preset turns on, but it also adds rules no row asks for.
- `no-unsafe-*`, `no-floating-promises`, `no-misused-promises` and `switch-exhaustiveness-check` read types, so they need `languageOptions.parserOptions.projectService: true`. A file outside every `tsconfig` `include` fails with a parsing error instead of skipping the rule, so test files belong in the `include`. In a monorepo set `tsconfigRootDir` to the package.
- typescript-eslint 8.73 declares TypeScript from 4.8.4 up to but not including 6.1 as its peer range, so the typed rows run on TypeScript 5 and 6, and a project on TypeScript 7 waits for a plugin release that widens it.
- `no-restricted-syntax`, `no-restricted-properties` and `no-restricted-globals` take one options array per file, and a later config object replaces an earlier one's array. The test block repeats the production selector, and the config-folder block repeats the Prisma entries without `process.env`. Swap `src/config/**` for the folder that holds `loadConfig()`.
- ESLint does not skip generated code: it lints every file that `ignores` does not name, and `node_modules` and `.git` are the only default ignores. A Prisma client generated into `src/generated/` reports `no-explicit-any` until the folder is in `ignores`, so the config lists it.
- `no-explicit-any` and the suppression rows leave one way out: a third-party typing that returns `any` is suppressed with the reason after `--`, which `require-description` demands (`// eslint-disable-next-line @typescript-eslint/no-explicit-any -- the SDK types its response as any`).
- The `tsc` row is read from `tsconfig.json`, and the `typecheck` script runs `tsc --noEmit` in CI, since ESLint does not report type errors.

`eslint.config.mjs` (ESLint 9.22 or later):

```js
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import eslintComments from '@eslint-community/eslint-plugin-eslint-comments';

const doubleCast = {
  selector: "TSAsExpression[expression.type='TSAsExpression'][expression.typeAnnotation.type='TSUnknownKeyword']",
  message: 'No as unknown as X: narrow the value or fix the type',
};

const linearTest = [
  doubleCast,
  ...['TryStatement', 'IfStatement', 'SwitchStatement', 'ForStatement', 'ForInStatement', 'ForOfStatement', 'WhileStatement', 'DoWhileStatement', 'ConditionalExpression'].map(
    (selector) => ({ selector, message: 'A test body is linear: no branch, loop or try' }),
  ),
];

const prismaUnsafe = [
  { property: '$queryRawUnsafe', message: 'Use the $queryRaw tagged template with bound parameters' },
  { property: '$executeRawUnsafe', message: 'Use the $executeRaw tagged template with bound parameters' },
];

export default defineConfig(
  { ignores: ['dist/**', 'src/generated/**'] },
  {
    files: ['**/*.ts'],
    languageOptions: { parser: tseslint.parser, parserOptions: { projectService: true } },
    plugins: { '@typescript-eslint': tseslint.plugin, '@eslint-community/eslint-comments': eslintComments },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'error',
      '@typescript-eslint/no-unsafe-argument': 'error',
      '@typescript-eslint/no-unsafe-call': 'error',
      '@typescript-eslint/no-unsafe-member-access': 'error',
      '@typescript-eslint/no-unsafe-return': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': ['error', { allowDefaultCaseForExhaustiveSwitch: false }],
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/ban-ts-comment': ['error', { 'ts-expect-error': 'allow-with-description', 'ts-ignore': true, 'ts-nocheck': true, minimumDescriptionLength: 10 }],
      '@eslint-community/eslint-comments/require-description': 'error',
      'no-console': 'error',
      'no-restricted-properties': ['error', { object: 'process', property: 'env', message: 'Read configuration through loadConfig()' }, ...prismaUnsafe],
      'no-restricted-syntax': ['error', doubleCast],
    },
  },
  {
    files: ['src/config/**/*.ts'],
    rules: { 'no-restricted-properties': ['error', ...prismaUnsafe] },
  },
  {
    files: ['**/*.{test,spec}.ts'],
    rules: {
      'no-restricted-syntax': ['error', ...linearTest],
      'no-restricted-globals': ['error', { name: 'setTimeout', message: 'Inject the clock or advance fake timers' }],
    },
  },
);
```
