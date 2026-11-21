---
paths:
  - "**/eslint.config.{js,mjs,cjs,ts,mts,cts}"
  - "**/tsconfig*.json"
---

<!-- mobile-react-native rules v1 (2026-11-21): lint. Ids checked against the tools' documentation on 2026-11-21 (ESLint 9, eslint-config-expo 57, typescript-eslint 8, TypeScript 6, eslint-plugin-react 7, eslint-plugin-react-hooks 7, eslint-plugin-react-native 5). Installed by /mobile-react-native:rules; edit the paths above to where this app keeps its ESLint config, re-run to compare with the plugin's copy. -->

# React Native lint standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `react-native.md`, `react-native-ui.md`, `react-native-a11y.md` or `react-native-tests.md` that ESLint or `tsc` detects, so the build catches it before a review does. The two TypeScript rows cite `conformance-checklist.md`, since the rule files carry no TypeScript rule. Rules no stock rule detects stay in those files and get no row: `testID` on every control, the three-state region, effect cleanup, timeouts, the 44 pt target, a role and name on every control. `eslint-plugin-react-native-a11y` has no row: its 3.5.1 release declares ESLint 8 as its highest peer.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| All text sits inside `<Text>` (`react-native.md`, Platform) | `eslint-plugin-react-native` | `react-native/no-raw-text` | error |
| Conditional rendering takes a boolean, never `{count && <X/>}` with a number (`react-native.md`, Platform) | `eslint-plugin-react` | `react/jsx-no-leaked-render`, `validStrategies: ['ternary', 'coerce']` | error |
| No `useEffect` that syncs one state from another (`react-native.md`, State) | `eslint-config-expo/flat`, provided by the preset | `react-hooks/set-state-in-effect` | error |
| No `window` or `document` (`react-native.md`, Platform) | ESLint core | `no-restricted-globals`, `window` and `document` | error |
| No `'use client'` directive (`react-native.md`, Platform) | ESLint core | `no-restricted-syntax`, the `'use client'` directive selector | error |
| No `@react-navigation/*` import in an Expo Router app (`react-native.md`, Platform) | ESLint core | `no-restricted-imports`, the `@react-navigation/*` pattern | error |
| `Pressable`, not `TouchableOpacity`; `expo-image`, not React Native's `Image` (`react-native-ui.md`, Components) | ESLint core | `no-restricted-imports`, `importNames` of `react-native` | error |
| List keys are stable domain ids, never the array index (`react-native-ui.md`, Components) | `eslint-plugin-react` | `react/no-array-index-key` | error |
| Text scales: never `allowFontScaling={false}` (`react-native-a11y.md`) | ESLint core | `no-restricted-syntax`, the `allowFontScaling` selector | error |
| Tests run on Jest and RNTL, never Vitest or the DOM `@testing-library/react` (`react-native-tests.md`) | ESLint core | `no-restricted-imports`, `vitest`, `@testing-library/react`, `@testing-library/dom`; `no-restricted-globals`, `vi`, in test files | error |
| Every RNTL call is awaited (`react-native-tests.md`) | typescript-eslint | `@typescript-eslint/no-floating-promises` | error |
| A test body is linear: no `try`, `if`, `switch`, loop or ternary (`react-native-tests.md`) | ESLint core | `no-restricted-syntax`, the control-flow selectors, in test files | error |
| A test never waits on `setTimeout` (`react-native-tests.md`) | ESLint core | `no-restricted-globals`, `setTimeout`, in test files | error |
| No `any` in app code (`conformance-checklist.md`, B2) | typescript-eslint | `@typescript-eslint/no-explicit-any` | error |
| TypeScript is strict (`conformance-checklist.md`, B1) | `tsc` | `"strict": true` in `tsconfig.json` | setting |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `'<id>': 'error'` in `eslint.config.js`, under `files: ['**/*.{ts,tsx}']`, after `eslint-config-expo/flat`. The preset registers `react`, `react-hooks`, `import` and `expo`, and sets `react-hooks/rules-of-hooks`, `react-hooks/set-state-in-effect` and `react/jsx-key` to `error`. The `set-state-in-effect` row is the preset's, so the config below omits it. The preset does not set `react/no-array-index-key` or `react/jsx-no-leaked-render`, so the project adds those two rows. It sets `react-hooks/exhaustive-deps` to `warn`, and no row asks for more. Checked with `eslint-config-expo` 57.0.2.
- `react-native/no-raw-text` comes from `eslint-plugin-react-native`, which the preset does not register. Its last release is 5.0.0 (December 2024) and it declares ESLint 9 as its highest peer. A project that cannot take that plugin keeps the rule as a prose rule and the audit reports the row.
- `@typescript-eslint/no-floating-promises` reads types, so it needs `languageOptions.parserOptions.projectService: true`. A file outside every `tsconfig` `include` fails with a parsing error instead of skipping the rule. RNTL 14 returns promises from `render`, `renderHook`, `fireEvent.*`, `userEvent.*` and `act`, so an unawaited call is the finding. In a monorepo set `tsconfigRootDir` to the app.
- typescript-eslint 8.73 declares TypeScript from 4.8.4 up to but not including 6.1 as its peer range, so the typed rows run on TypeScript 5 and 6, and a project on TypeScript 7 waits for a plugin release that widens it.
- `no-restricted-syntax` and `no-restricted-globals` take one options array per file, and the later config object replaces the earlier one's array, so the test block repeats the production entries. `no-restricted-imports` is one block for every file, since the test-only imports never appear in app code. The `@react-navigation/*` pattern is dropped in a project that has not moved to Expo Router.
- ESLint does not skip generated code: the preset ignores only `android/app/build`. `.expo/types/*.d.ts`, `expo-env.d.ts` and a generated client under `src/generated/` are all linted, so the config lists them in `ignores`. A `.d.ts` that the `tsconfig` `include` leaves out fails with a parsing error, and the client reports `no-explicit-any`.
- ESLint 9, not 10: `eslint-plugin-react` declares ESLint 9.7 as its highest peer.

`eslint.config.js` (ESLint 9.22 or later, as Expo's own template):

```js
const expoConfig = require('eslint-config-expo/flat');
const { defineConfig } = require('eslint/config');
const reactNative = require('eslint-plugin-react-native');

const baseSyntax = [
  { selector: "JSXAttribute[name.name='allowFontScaling'][value.expression.value=false]", message: 'Text scales with the system setting; never lock it' },
  { selector: "ExpressionStatement[directive='use client']", message: "'use client' is a web directive" },
];

const linearTest = [
  ...baseSyntax,
  ...['TryStatement', 'IfStatement', 'SwitchStatement', 'ForStatement', 'ForInStatement', 'ForOfStatement', 'WhileStatement', 'DoWhileStatement', 'ConditionalExpression'].map(
    (selector) => ({ selector, message: 'A test body is linear: no branch, loop or try' }),
  ),
];

const noDom = [
  { name: 'window', message: 'No DOM in React Native' },
  { name: 'document', message: 'No DOM in React Native' },
];

module.exports = defineConfig([
  { ignores: ['.expo/**', 'expo-env.d.ts', 'src/generated/**'] },
  expoConfig,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { parserOptions: { projectService: true } },
    plugins: { 'react-native': reactNative },
    rules: {
      'react-native/no-raw-text': 'error',
      'react/jsx-no-leaked-render': ['error', { validStrategies: ['ternary', 'coerce'] }],
      'react/no-array-index-key': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      'no-restricted-imports': ['error', {
        patterns: [{ group: ['@react-navigation/*'], message: 'Expo Router owns navigation' }],
        paths: [
          { name: 'react-native', importNames: ['TouchableOpacity'], message: 'Use Pressable' },
          { name: 'react-native', importNames: ['Image'], message: 'Use expo-image' },
          { name: 'vitest', message: 'Tests run on Jest' },
          { name: '@testing-library/react', message: 'Use @testing-library/react-native' },
          { name: '@testing-library/dom', message: 'Use @testing-library/react-native' },
        ],
      }],
      'no-restricted-globals': ['error', ...noDom],
      'no-restricted-syntax': ['error', ...baseSyntax],
    },
  },
  {
    files: ['**/*.test.{ts,tsx}', '**/__tests__/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': ['error', ...linearTest],
      'no-restricted-globals': ['error', ...noDom,
        { name: 'setTimeout', message: 'Wait with findBy or waitFor, or fake timers' },
        { name: 'vi', message: 'Tests run on Jest' },
      ],
    },
  },
]);
```
