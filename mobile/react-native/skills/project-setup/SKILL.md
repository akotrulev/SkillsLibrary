---
name: mobile-react-native-project-setup
description: Use when standing up or configuring an Expo SDK 57 app — `create-expo-app` default template, development builds over Expo Go, CNG and `prebuild --clean`, config plugins, `src/app` layout, strict TS, flat ESLint, `expo-doctor`, EAS Build/Submit/Update/Workflows, pnpm monorepos. Triggers "new Expo app", "add a config plugin", "dev build vs Expo Go". Do NOT use for signing and rollout (`mobile-shared-release`), routes (`-navigation`), screens (`-ui-components`) or kits (`-component-library`).
---

# React Native / Expo — Project Setup

Stands up an **Expo-managed React Native app** on the SDK 57 lane: the default template, the development-build decision, continuous native generation (CNG), config plugins, folder layout and the quality gates every project ships with. EAS tool detail lives in [`mobile/_shared/release`](../../../_shared/release/references/eas.md).

## Version lane

Detect the Expo SDK / RN / React majors (`package.json`, `app.json`) first.

| Lane | SDK | Setup consequences |
|---|---|---|
| **Primary** | **57** (RN 0.86, React 19.2) | Template: `src/app`, `@/*` alias, `@expo/ui`, `expo-image`, `reactCompiler: true`, `typedRoutes: true`, TS `strict` (~6.0). `expo prebuild` **cleans by default** |
| `[SDK58]` | 58 beta | Becomes primary on stable: AGP 9, scene lifecycle default (iOS 27), native tabs at `expo-router/native-tabs` |
| Supported | 55–56 | Same flow; SDK 56 + Hermes V1 + Reanimated has a memory regression fixed in `expo@57.0.9` — recommend 57 |
| Floor | 54 | Migration bridge only; hand to [`migration`](../migration/SKILL.md) |

Never up-level a project's SDK as a side effect of setup work. The New Architecture is on; never scaffold the legacy one.

## When to use

- Creating an Expo app; deciding Expo Go vs development build vs bare
- Adding or fixing a config plugin, `app.config.ts`, a custom font, a permission string
- Setting up strict TS, flat ESLint, `expo-doctor`, env handling
- A pnpm / Turborepo monorepo that contains an Expo app

## When NOT to use

- Versioning, signing, store tracks, OTA policy → `mobile-shared-release`
- Pipeline YAML → `devops-engineer`
- Route tree, deep links → [`navigation`](../navigation/SKILL.md)
- Component kit or theme → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- Concepts (threads, primitives) → [`basics`](../basics/SKILL.md)
- Auth → `auth0-react-native`

## Inputs needed

1. **SDK** — 57 unless the project says otherwise.
2. **Workflow** — development build (default) / Expo Go prototype / bare `[bare]`.
3. **Targets** — iOS, Android, web (web through react-native-web; say if in scope).
4. **Backend and auth** — drives env and secret handling, not scaffold shape.
5. **Component kit** — StyleSheet + Expo UI by default ([`component-library`](../component-library/SKILL.md)).

## Create the app

```bash
pnpm create expo-app@latest my-app
cd my-app
pnpm expo install expo-dev-client
```

Use `pnpm expo install <pkg>` — never `pnpm add` — for anything native, so the version matches the SDK. Pin the manager with the `packageManager` field. pnpm uses isolated installs.

| Decision | Choice | Why |
|---|---|---|
| Router | Expo Router (file-based, typed routes) | Primary navigation lane; **never install `@react-navigation/*` beside it** — SDK 56 forked the core ([`navigation`](../navigation/SKILL.md)) |
| Language | TypeScript `strict: true`, no `any` | House rule; the template already extends `expo/tsconfig.base` |
| Workflow | **Development build** | Expo Go cannot load custom native code and diverges from production |
| Native changes | Config plugins + CNG | `ios/` and `android/` are generated and gitignored; never hand-edited |

## Expo Go vs development build vs bare

- **Expo Go** — zero-build prototype; Expo SDK modules only. Leave it the moment a custom native dependency, a push entitlement or Expo UI beyond Go's bundle is needed.
- **Development build** (`expo-dev-client` + `eas build --profile development`, or `npx expo run:ios|android`) — the default for a real app.
- **Bare** `[bare]` — `ios/` and `android/` checked in. Brownfield or a team that edits native projects; `npx install-expo-modules` adopts Expo modules, [`migration`](../migration/SKILL.md) owns the move.

## Config: `app.config.ts` and plugins

Native configuration is `app.json` / `app.config.ts` plus **config plugins** that run at `prebuild`:

```ts
import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: 'My App',
  slug: 'my-app',
  scheme: 'myapp',
  newArchEnabled: true,
  experiments: { typedRoutes: true, reactCompiler: true },
  plugins: [
    'expo-router',
    ['expo-font', { fonts: ['./assets/fonts/Inter.ttf'] }],
    ['expo-splash-screen', { image: './assets/splash.png', resizeMode: 'contain' }],
  ],
};

export default config;
```

- Permission strings, entitlements and fonts are plugin options, not `Info.plist` edits. Fonts load through the `expo-font` plugin: `vendor/react-native-guidelines/rules/fonts-config-plugin.md`.
- **CNG:** `npx expo prebuild --clean` regenerates `ios/` and `android/` from config (clean is the default on SDK 57). A hand edit to a generated folder is lost on the next prebuild — put it in a plugin.
- `scheme` is the deep-link prefix; links are [`navigation`](../navigation/SKILL.md)'s.

## Layout

```
src/
  app/                 Expo Router routes — the only routing source
    _layout.tsx        root layout: providers, Stack
    (tabs)/_layout.tsx
    (tabs)/index.tsx
    [id].tsx
    +not-found.tsx
  components/          shared atoms and molecules
  features/<feature>/  components, hooks, api for one feature
  lib/                 api client, env, storage
  theme/               tokens
assets/
```

Route files are thin: they compose feature organisms from `src/features/*`; business logic never lives in a route file. Import third-party UI through one design-system folder: `vendor/react-native-guidelines/rules/imports-design-system-folder.md`. The `@/*` alias maps to `src/*`.

## Quality gates every project ships with

- **Strict TS** and `typedRoutes: true` for compile-checked `<Link href>`.
- **ESLint flat config** — `eslint-config-expo/flat` in `eslint.config.js`; `pnpm expo lint` runs it. Keep `react-hooks` exhaustive-deps on.
- **`npx expo-doctor`** clean — it checks versions, config and React Native Directory compatibility.
- **Prettier** shared config.
- **Env:** `EXPO_PUBLIC_*` is inlined into the bundle in plain text — public only. A real secret never ships in the bundle (`mobile-shared-security`); tokens live in `expo-secure-store` at runtime.
- **Lockfile + `packageManager`** committed.

## EAS in one view

```bash
eas build:configure
eas build --profile development --platform ios
eas build --profile production --platform all
eas submit --platform ios
```

`development` builds the dev client, `preview` is internal distribution, `production` is store-ready. EAS Update ships JS and asset changes only; EAS Workflows is EAS's own pipeline config. Profiles, secrets, build numbers, rollout and halt are in `mobile-shared-release`.

## Monorepo

Keep **native dependencies in the app package** (`vendor/.../rules/monorepo-native-deps-in-app.md`) and **one version of each dependency across packages** (`monorepo-single-dependency-versions.md`). SDK 57 resolves workspaces by default; do not hand-edit Metro for a pnpm workspace unless `expo-doctor` asks.

## Rules

- Detect the lane; never up-level; development build over Expo Go for a real app.
- `expo install` for native packages; config plugins for native change; CNG folders never hand-edited.
- No `@react-navigation/*` in an Expo Router app.
- `EXPO_PUBLIC_*` is public; secrets never in the bundle.
- Strict TS, flat ESLint and `expo-doctor` are part of the scaffold, not follow-ups.

## What NOT to do

- No `ios/` / `android/` hand edits in a CNG project.
- No old-architecture flags.
- No Expo Go as the team's only runtime for an app with native dependencies.
- No `pnpm add react-native-*` for native packages.

## Handoffs

- Routes and links → [`navigation`](../navigation/SKILL.md)
- Kit and theme → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- State layout → [`architecture`](../architecture/SKILL.md)
- Native modules, Expo Modules API → [`native-modules`](../native-modules/SKILL.md)
- Signing, tracks, OTA → `mobile-shared-release`
- SDK upgrade, bare → Expo → [`migration`](../migration/SKILL.md)
- `testID` hand-off → [`test-ids`](../test-ids/SKILL.md)
